"""Non-destructive Enhancement Exporter and FFmpeg Audio I/O for OmniRip M10."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

import mutagen
import numpy as np
from mutagen.id3 import COMM, ID3, TXXX

from harvester.analysis.enhancement.dsp import (
    apply_progressive_mono,
    ensure_2d_audio,
    match_spectral_slope,
    recombine_audio,
    split_bands,
)
from harvester.analysis.enhancement.eq import MasteringEQSettings, apply_mastering_eq
from harvester.analysis.enhancement.presets import EnhancementPreset
from harvester.analysis.enhancement.provider import EnhancementProvider
from harvester.services.enhancement.conservative_provider import ConservativeDSPProvider
from harvester.services.enhancement.flashsr_provider import FlashSRProvider
from harvester.services.enhancement.hybrid_provider import HybridCoOpProvider
from harvester.services.enhancement.nvsr_provider import NVSRProvider

logger = logging.getLogger(__name__)

ENHANCED_SAMPLE_RATE: int = 48000


class EnhancementExporter:
    """Renders enhanced audio and exports MP3 derivatives with explicit provenance tags."""

    def __init__(self, neural_enabled: bool = False) -> None:
        self.neural_enabled = neural_enabled
        self._providers: dict[str, EnhancementProvider] = {
            "conservative": ConservativeDSPProvider(),
            "nvsr": NVSRProvider(neural_enabled=neural_enabled),
            "flashsr": FlashSRProvider(neural_enabled=neural_enabled),
            "hybrid": HybridCoOpProvider(neural_enabled=neural_enabled),
        }

    def set_neural_enabled(self, enabled: bool) -> None:
        """Toggle between Neural Model Acceleration and Eco DSP synthesis."""
        self.neural_enabled = enabled
        for p in self._providers.values():
            if hasattr(p, "neural_enabled"):
                p.neural_enabled = enabled
            if hasattr(p, "set_neural_enabled"):
                p.set_neural_enabled(enabled)

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
            res = subprocess.run(cmd, capture_output=True, check=True)
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
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=interleaved)
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8")
            raise RuntimeError(f"FFmpeg MP3 encoding failed (code {proc.returncode}): {err_msg}")

    def render_audio_buffer(
        self,
        audio: np.ndarray,
        preset: EnhancementPreset,
        cutoff_hz: float = 15500.0,
        sample_rate: int = 48000,
        progress_callback: Callable[[float, str], None] | None = None,
        eq_settings: MasteringEQSettings | None = None,
    ) -> np.ndarray:
        """
        Apply complete enhancement DSP pipeline to in-memory audio array.

        Pipeline:
        1. Progressive mono bass blend (<100 Hz mono, 100-250 Hz fade).
        2. Complementary band split at cutoff_hz.
        3. Provider residual generation.
        4. Preset width / gain / slope scaling.
        5. Recombination with untouched lower band + soft limiter.
        6. 10-Band studio mastering equalizer & tone sculpting.
        """
        audio_2d, _ = ensure_2d_audio(audio)

        if progress_callback:
            progress_callback(
                38.0, "⚡ [AI Core]: Splitting frequency bands & crossover network..."
            )

        # 1. Progressive mono bass
        if preset.progressive_mono:
            base_audio = apply_progressive_mono(audio_2d, sample_rate=sample_rate)
        else:
            base_audio = audio_2d

        # 2. Crossover split at cutoff_hz
        lower_band, _ = split_bands(base_audio, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

        # 3. Resolve provider
        provider = self._providers.get(preset.provider_type) or self._providers["conservative"]
        if progress_callback:
            progress_callback(
                42.0, f"⚡ [AI Engine]: Synthesizing neural residual ({preset.name})..."
            )

        import inspect

        sig = inspect.signature(provider.generate_residual)
        if "progress_callback" in sig.parameters:
            raw_residual = provider.generate_residual(
                base_audio,
                sample_rate=sample_rate,
                cutoff_hz=cutoff_hz,
                progress_callback=progress_callback,
            )
        else:
            raw_residual = provider.generate_residual(
                base_audio, sample_rate=sample_rate, cutoff_hz=cutoff_hz
            )

        if progress_callback:
            progress_callback(
                58.0, "⚡ [Spectral Balancer]: Matching spectral slope & mid/side width..."
            )

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

        if progress_callback:
            progress_callback(
                66.0, "⚡ [Mastering Limiter]: Recombining bands & true-peak limiting..."
            )

        # 6. Recombination (sub-cutoff audio is untouched)
        enhanced = recombine_audio(lower_band, scaled_residual, ceiling_dbfs=preset.ceiling_dbfs)

        # 7. Apply 10-Band Mastering Equalizer & Tone Sculptor if configured
        if eq_settings is not None and (
            eq_settings.enabled or eq_settings.hpf_30hz or eq_settings.output_trim_db != 0.0
        ):
            if progress_callback:
                progress_callback(
                    68.0, f"⚡ [10-Band EQ]: Sculpting tonal balance ({eq_settings.preset_name})..."
                )
            enhanced = apply_mastering_eq(
                enhanced,
                settings=eq_settings,
                sample_rate=sample_rate,
                ceiling_dbfs=preset.ceiling_dbfs,
            )

        return enhanced

    def generate_derivative_path(self, input_path: Path, preset: EnhancementPreset) -> Path:
        """Generate default output path for enhancement derivative."""
        stem = input_path.stem
        if stem.endswith(".enhanced"):
            out_name = f"{stem}.mp3"
        else:
            out_name = f"{stem}.enhanced.mp3"
        return input_path.parent / out_name

    def generate_lossless_path(self, input_path: Path, fmt: str) -> Path:
        """Default output path for a lossless enhanced export."""
        stem = input_path.stem
        base = f"{stem}.{fmt}" if stem.endswith(".enhanced") else f"{stem}.enhanced.{fmt}"
        return input_path.parent / base

    @staticmethod
    def _provenance_flags(
        preset: EnhancementPreset, extra_tags: Mapping[str, str] | None = None
    ) -> dict[str, str]:
        flags = {
            "DERIVED_FROM_LOSSY": "true",
            "LOSSLESS_SOURCE": "false",
            "SYNTHETIC_HIGH_BAND": "true",
            "ENHANCEMENT_PRESET": preset.name,
        }
        if extra_tags:
            flags.update({str(key): str(value) for key, value in extra_tags.items()})
        return flags

    @staticmethod
    def _provenance_comment(preset: EnhancementPreset) -> str:
        return (
            f"OmniRip Enhanced Derivative: preset={preset.name}; "
            "DERIVED_FROM_LOSSY=true; LOSSLESS_SOURCE=false; SYNTHETIC_HIGH_BAND=true"
        )

    def _render_enhanced(
        self,
        input_path: Path,
        preset: EnhancementPreset,
        cutoff_hz: float,
        eq_settings: MasteringEQSettings | None,
        progress_callback: Callable[[float, str], None] | None,
    ) -> np.ndarray:
        """Decode at 48 kHz and run the enhancement chain once, for any output format."""
        if progress_callback:
            progress_callback(10.0, "Decoding audio source stream (FFmpeg)...")
        logger.info("Decoding audio from %s...", input_path.name)
        audio = self.decode_audio_ffmpeg(input_path)

        if progress_callback:
            progress_callback(35.0, "⚡ [AI Core]: Ingesting float32 stereo audio (48kHz)...")
        logger.info("Rendering enhanced audio buffer with preset '%s'...", preset.name)
        return self.render_audio_buffer(
            audio,
            preset=preset,
            cutoff_hz=cutoff_hz,
            progress_callback=progress_callback,
            eq_settings=eq_settings,
        )

    def export_enhanced_derivative(
        self,
        input_path: Path,
        preset: EnhancementPreset,
        output_path: Path | None = None,
        cutoff_hz: float = 15500.0,
        bitrate: str = "320k",
        progress_callback: Callable[[float, str], None] | None = None,
        eq_settings: MasteringEQSettings | None = None,
        extra_tags: Mapping[str, str] | None = None,
    ) -> Path:
        """
        Decode input file, render enhanced audio, write MP3 derivative, and attach ID3 tags.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = self.generate_derivative_path(input_path, preset)
        else:
            output_path = Path(output_path)

        enhanced = self._render_enhanced(
            input_path, preset, cutoff_hz, eq_settings, progress_callback
        )

        if progress_callback:
            progress_callback(72.0, "Encoding 320kbps MP3 derivative (LAME)...")
        logger.info("Encoding MP3 derivative to %s...", output_path.name)
        self.encode_mp3_ffmpeg(enhanced, output_path, bitrate=bitrate)

        if progress_callback:
            progress_callback(90.0, "Attaching ID3v2 provenance tags...")
        # Apply Mutagen ID3 provenance tags
        self._apply_provenance_tags(input_path, output_path, preset, extra_tags=extra_tags)

        if progress_callback:
            progress_callback(100.0, "Download complete.")
        return output_path

    def export_enhanced_lossless(
        self,
        input_path: Path,
        preset: EnhancementPreset,
        output_path: Path | None = None,
        cutoff_hz: float = 15500.0,
        fmt: str = "flac",
        progress_callback: Callable[[float, str], None] | None = None,
        eq_settings: MasteringEQSettings | None = None,
        extra_tags: Mapping[str, str] | None = None,
    ) -> Path:
        """Render the enhanced master and write it lossless (24-bit PCM, 48 kHz).

        The container prevents further generation loss; the content is still
        derived from a lossy source, which the provenance tags record.
        """
        import soundfile as sf

        fmt = fmt.lower().lstrip(".")
        if fmt not in ("flac", "wav"):
            raise ValueError(f"Unsupported lossless format: {fmt!r}")

        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        output_path = (
            Path(output_path)
            if output_path is not None
            else self.generate_lossless_path(input_path, fmt)
        )

        enhanced = self._render_enhanced(
            input_path, preset, cutoff_hz, eq_settings, progress_callback
        )

        if progress_callback:
            progress_callback(72.0, f"Writing {fmt.upper()} 24-bit/48kHz master...")
        logger.info("Writing lossless enhanced master to %s", output_path.name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(
            str(output_path),
            enhanced.T,
            ENHANCED_SAMPLE_RATE,
            format=fmt.upper(),
            subtype="PCM_24",
        )

        if progress_callback:
            progress_callback(90.0, "Attaching provenance tags...")
        self._apply_lossless_provenance(output_path, preset, extra_tags=extra_tags)

        if progress_callback:
            progress_callback(100.0, "Lossless master written.")
        return output_path

    def _apply_lossless_provenance(
        self,
        target_path: Path,
        preset: EnhancementPreset,
        extra_tags: Mapping[str, str] | None = None,
    ) -> None:
        """Write provenance tags: Vorbis comments for FLAC, an ID3 chunk for WAV."""
        flags = self._provenance_flags(preset, extra_tags)
        comment = self._provenance_comment(preset)
        try:
            if target_path.suffix.lower() == ".flac":
                from mutagen.flac import FLAC

                flac = FLAC(target_path)
                for key, value in flags.items():
                    flac[key] = value
                flac["COMMENT"] = comment
                flac.save()
                return
            from mutagen.wave import WAVE

            wave = WAVE(target_path)
            if wave.tags is None:
                wave.add_tags()
            for key, value in flags.items():
                wave.tags.add(TXXX(encoding=3, desc=key, text=[value]))
            wave.tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment]))
            wave.save()
        except Exception as e:
            logger.warning("Failed to apply provenance tags to %s: %s", target_path, e)


    def apply_provenance_tags(
        self,
        source_path: Path,
        target_path: Path,
        preset: EnhancementPreset,
        extra_tags: Mapping[str, str] | None = None,
    ) -> None:
        """Copy metadata tags from source and append strict provenance headers."""
        self._apply_provenance_tags(
            source_path=source_path,
            target_path=target_path,
            preset=preset,
            extra_tags=extra_tags,
        )

    def _apply_provenance_tags(
        self,
        source_path: Path,
        target_path: Path,
        preset: EnhancementPreset,
        extra_tags: Mapping[str, str] | None = None,
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
                    allowed_prefixes = ("TIT2", "TPE1", "TALB", "APIC")
                    for key, val in source_meta.tags.items():
                        if any(key.startswith(p) for p in allowed_prefixes):
                            target_tags[key] = val
            except Exception as e:
                logger.debug("Could not copy original metadata: %s", e)

            # Strict Provenance Flags
            for key, value in self._provenance_flags(preset, extra_tags).items():
                target_tags.add(TXXX(encoding=3, desc=key, text=[value]))
            target_tags.add(
                COMM(encoding=3, lang="eng", desc="", text=[self._provenance_comment(preset)])
            )
            target_tags.save(target_path, v2_version=3)

        except Exception as e:
            logger.warning("Failed to apply full ID3 tags to %s: %s", target_path, e)
