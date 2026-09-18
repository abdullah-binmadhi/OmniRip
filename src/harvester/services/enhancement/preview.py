"""Headless preview generation and system audio player dispatch for OmniRip M10."""

from __future__ import annotations

import logging
import platform
import subprocess
import wave
from pathlib import Path

import numpy as np
import platformdirs

from harvester.analysis.enhancement.presets import EnhancementPreset
from harvester.services.enhancement.exporter import EnhancementExporter

logger = logging.getLogger(__name__)


class PreviewManager:
    """Manages rendering 15-second A/B comparison audio slices and triggering external players."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        exporter: EnhancementExporter | None = None,
    ) -> None:
        if cache_dir is None:
            self.cache_dir = Path(platformdirs.user_cache_dir("omnirip")) / "previews"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.exporter = exporter or EnhancementExporter()

    @staticmethod
    def find_energetic_slice(
        audio_2d: np.ndarray,
        sample_rate: int = 48000,
        duration_sec: float = 15.0,
    ) -> tuple[int, int]:
        """
        Locate the start and end sample of the most energetic continuous excerpt.

        Avoids slicing into silent intros, long fades, or vinyl needle-drops.
        """
        n_samples = audio_2d.shape[1]
        window_len = int(sample_rate * duration_sec)

        if n_samples <= window_len:
            return 0, n_samples

        # Calculate RMS energy in chunks of 0.5s
        hop = int(sample_rate * 0.5)
        mono_signal = np.mean(audio_2d, axis=0)

        # Vectorized block energy estimation
        n_hops = (n_samples - window_len) // hop
        best_energy = -1.0
        best_start = 0

        for i in range(n_hops + 1):
            start = i * hop
            end = start + window_len
            chunk = mono_signal[start:end]
            energy = float(np.mean(chunk**2))
            if energy > best_energy:
                best_energy = energy
                best_start = start

        return best_start, best_start + window_len

    @staticmethod
    def write_wav(file_path: Path, audio_2d: np.ndarray, sample_rate: int = 48000) -> Path:
        """Write float32 stereo numpy array to 16-bit PCM WAV file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Scale float32 to int16 PCM
        clamped = np.clip(audio_2d, -1.0, 1.0)
        pcm_16 = (clamped * 32767.0).astype(np.int16)

        # Interleave stereo channels
        channels, n_samples = pcm_16.shape
        interleaved = pcm_16.T.flatten().tobytes()

        with wave.open(str(file_path), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(interleaved)

        return file_path

    def generate_preview_pair(
        self,
        input_path: Path,
        preset: EnhancementPreset,
        duration_sec: float = 15.0,
        cutoff_hz: float = 15500.0,
    ) -> tuple[Path, Path]:
        """
        Generate matched 15-second A/B comparison WAV files.

        Returns:
            tuple[Path, Path]: (original_preview_wav, enhanced_preview_wav)
        """
        input_path = Path(input_path)
        stem = input_path.stem
        orig_path = self.cache_dir / f"{stem}_orig_prev.wav"
        enh_path = self.cache_dir / f"{stem}_{preset.id}_prev.wav"

        # Decode full audio
        audio = self.exporter.decode_audio_ffmpeg(input_path)

        # Find energetic 15s excerpt
        start, end = self.find_energetic_slice(audio, sample_rate=48000, duration_sec=duration_sec)
        sliced_original = audio[:, start:end]

        # Render enhanced version of the exact same time slice
        enhanced_slice = self.exporter.render_audio_buffer(
            sliced_original,
            preset=preset,
            cutoff_hz=cutoff_hz,
            sample_rate=48000,
        )

        self.write_wav(orig_path, sliced_original, sample_rate=48000)
        self.write_wav(enh_path, enhanced_slice, sample_rate=48000)

        return orig_path, enh_path

    @staticmethod
    def open_in_system_player(file_path: Path) -> subprocess.Popen:
        """
        Launch audio file in the host operating system's default media player.
        Executes non-blocking subprocess so Textual TUI never hangs.
        """
        file_path = Path(file_path)
        system = platform.system()

        if system == "Darwin":
            cmd = ["open", str(file_path)]
        elif system == "Windows":
            cmd = ["start", str(file_path)]
        else:
            cmd = ["xdg-open", str(file_path)]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(system == "Windows"),
            )
            return proc
        except Exception as e:
            logger.error("Failed to launch system player for %s: %s", file_path, e)
            raise RuntimeError(f"Could not open default system player: {e}") from e
