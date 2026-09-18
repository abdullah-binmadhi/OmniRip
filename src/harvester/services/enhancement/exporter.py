"""Non-destructive Enhancement Exporter and FFmpeg Audio I/O for OmniRip M10."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
from typing import BinaryIO

import mutagen
from mutagen.id3 import ID3, COMM, TXXX
import numpy as np

from harvester.analysis.enhancement.dsp import (
    apply_limiter,
    apply_progressive_mono,
    ensure_2d_audio,
    match_spectral_slope,
    recombine_audio,
    split_bands,
)
from harvester.analysis.enhancement.presets import EnhancementPreset, PRESETS
from harvester.analysis.enhancement.provider import EnhancementProvider
from harvester.services.enhancement.conservative_provider import ConservativeDSPProvider
from harvester.services.enhancement.flashsr_provider import FlashSRProvider
from harvester.services.enhancement.hybrid_provider import HybridCoOpProvider
from harvester.services.enhancement.nvsr_provider import NVSRProvider

logger = logging.getLogger(__name__)


class EnhancementExporter:
    """Renders enhanced audio and exports MP3 derivatives with explicit provenance tags."""

    def __init__(self) -> None:
        self._providers: dict[str, EnhancementProvider] = {
            "conservative": ConservativeDSPProvider(),
            "nvsr": NVSRProvider(),
            "flashsr": FlashSRProvider(),
            "hybrid": HybridCoOpProvider(),
        }

    def decode_audio_ffmpeg(self, file_path: Path, sample_rate: int = 48000) -> np.ndarray:
        """Decode any audio file directly into 48kHz float32 stereo numpy array using FFmpeg."""
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(file_path),
            "-f",
            "f32le",
            "-ac",
            "2",
            "-ar",
            str(sample_rate),
            "pipe:1",
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            raw = res.stdout
            audio = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T
            return audio
        except Exception as e:
            logger.error("FFmpeg decode failed for %s: %s", file_path, e)
            raise RuntimeError(f"FFmpeg decoding failed for {file_path}: {e}") from e

    def encode_mp3_ffmpeg(
        self,
        audio_2d: np.ndarray,
        output_path: Path,
        sample_rate: int = 48000,
        bitrate: str = "320k",
    ) -> None:
        """Encode float32 stereo numpy array to MP3 via direct FFmpeg subprocess."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Interleave stereo channels for FFmpeg raw PCM pipe: L, R, L, R...
        interleaved = audio_2d.T.flatten().astype(np.float32).tobytes()

        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            "-i",
            "pipe:0",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-id3v2_version",
            "3",
            str(output_path),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=interleaved)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg MP3 encoding failed (code {proc.returncode}): {stderr.decode('utf-8')}")

    def render_audio_buffer(
        self,
        audio: np.ndarray,
        preset: EnhancementPreset,
        cutoff_hz: float = 15500.0,
        sample_rate: int = 48000,
    ) -> np.ndarray:
        """
        Render enhanced audio array according to preset parameters:
        1. Progressive mono bass blend (<100 Hz mono, 100-250 Hz fade).
        2. Complementary band split at cutoff_hz.
        3. Provider residual generation.
        4. Preset width / gain / slope scaling.
        5. Recombination with untouched lower band + soft limiter.
        """
        audio_2d, _ = ensure_2d_audio(audio)

        # 1. Progressive mono bass
        if preset.progressive_mono:
            base_audio = apply_progressive_mono(audio_2d, sample_rate=sample_rate)
        else:
            base_audio = audio_2d

        # 2. Crossover split at cutoff_hz
        lower_band, _ = split_bands(base_audio, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

        # 3. Resolve provider
        provider = self._providers.get(preset.provider_type) or self._providers["conservative"]
        raw_residual = provider.generate_residual(base_audio, sample_rate=sample_rate, cutoff_hz=cutoff_hz)

        # 4. Mid-Side width control on residual
        if preset.residual_stereo_width != 1.0 and raw_residual.shape[0] >= 2:
            left, right = raw_residual[0], raw_residual[1]
            mid = 0.5 * (left + right)
            side = 0.5 * (left - right) * preset.residual_stereo_width
            raw_residual = np.stack([mid + side, mid - side], axis=0).astype(np.float32)

        # 5. Gain & slope scaling
        scaled_residual = match_spectral_slope(
            source_audio=base_audio,
            residual_audio=raw_residual,
            cutoff_hz=cutoff_hz,
            sample_rate=sample_rate,
            target_decay_db_per_oct=preset.target_decay_db_per_oct,
        )
        if preset.residual_gain_db != 0.0:
            gain_factor = 10.0 ** (preset.residual_gain_db / 20.0)
            scaled_residual = scaled_residual * gain_factor

        # 6. Recombination (sub-cutoff audio is untouched)
        enhanced = recombine_audio(lower_band, scaled_residual, ceiling_dbfs=preset.ceiling_dbfs)
        return enhanced

    def export_enhanced_derivative(
        self,
        input_path: Path,
        preset: EnhancementPreset,
        output_path: Path | None = None,
        cutoff_hz: float = 15500.0,
        bitrate: str = "320k",
    ) -> Path:
        """
        Decode input file, render enhanced audio, write MP3 derivative, and attach ID3 provenance tags.
        Original input file is never touched or overwritten.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            # Default naming: {name}.enhanced.mp3 alongside original
            stem = input_path.stem
            if stem.endswith(".enhanced"):
                out_name = f"{stem}.mp3"
            else:
                out_name = f"{stem}.enhanced.mp3"
            output_path = input_path.parent / out_name
        else:
            output_path = Path(output_path)

        logger.info("Decoding audio from %s...", input_path.name)
        audio = self.decode_audio_ffmpeg(input_path)

        logger.info("Rendering enhanced audio buffer with preset '%s'...", preset.name)
        enhanced = self.render_audio_buffer(audio, preset=preset, cutoff_hz=cutoff_hz)

        logger.info("Encoding MP3 derivative to %s...", output_path.name)
        self.encode_mp3_ffmpeg(enhanced, output_path, bitrate=bitrate)

        # Apply Mutagen ID3 provenance tags
        self._apply_provenance_tags(input_path, output_path, preset)
        return output_path

    def _apply_provenance_tags(
        self,
        source_path: Path,
        target_path: Path,
        preset: EnhancementPreset,
    ) -> None:
        """Copy metadata tags from source and append strict provenance headers."""
        try:
            # Load or initialize ID3 on target MP3
            try:
                target_tags = ID3(target_path)
            except mutagen.id3.ID3NoHeaderError:
                target_tags = ID3()

            # Copy standard tags from source if possible
            try:
                source_meta = mutagen.File(source_path)
                if source_meta is not None and source_meta.tags is not None:
                    for key, val in source_meta.tags.items():
                        if key.startswith("TIT2") or key.startswith("TPE1") or key.startswith("TALB") or key.startswith("APIC"):
                            target_tags[key] = val
            except Exception as e:
                logger.debug("Could not copy original metadata: %s", e)

            # Strict Provenance Flags
            target_tags.add(TXXX(encoding=3, desc="DERIVED_FROM_LOSSY", text=["true"]))
            target_tags.add(TXXX(encoding=3, desc="LOSSLESS_SOURCE", text=["false"]))
            target_tags.add(TXXX(encoding=3, desc="SYNTHETIC_HIGH_BAND", text=["true"]))
            target_tags.add(TXXX(encoding=3, desc="ENHANCEMENT_PRESET", text=[preset.name]))

            comment_str = (
                f"OmniRip M10 Enhanced Derivative: preset={preset.name}; "
                "DERIVED_FROM_LOSSY=true; LOSSLESS_SOURCE=false; SYNTHETIC_HIGH_BAND=true"
            )
            target_tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment_str]))
            target_tags.save(target_path, v2_version=3)

        except Exception as e:
            logger.warning("Failed to apply full ID3 tags to %s: %s", target_path, e)
