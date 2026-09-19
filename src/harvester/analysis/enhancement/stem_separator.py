"""Vocal and Instrumental Stem Separation service for OmniRip.

Provides dual-engine stem separation:
1. Eco DSP Mode: Zero-latency mid-side phase cancellation and bandpass
   filtering. 100% offline, zero network or heavyweight model download required.
2. Neural AI Mode: Source separation powered by torchaudio HDEMUCS (MUSDB-HQ),
   separating full audio into isolated Vocals and Instrumental backing stems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StemResult:
    """Container for separated stem audio file paths and metadata."""

    vocals_path: Path
    instrumental_path: Path
    mode: str
    sample_rate: int
    duration_s: float
    drums_path: Path | None = None
    bass_path: Path | None = None


def load_audio_numpy(audio_path: Path, target_sr: int = 44100) -> tuple[np.ndarray, int]:
    """Load audio file into a 2D float32 numpy array of shape (channels, samples)."""
    try:
        import soundfile as sf

        data, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
        # Transpose from (samples, channels) to (channels, samples)
        audio = data.T
        if sr != target_sr and target_sr > 0:
            # Resample if needed using scipy or torchaudio
            try:
                import torch
                import torchaudio.transforms as T

                resampler = T.Resample(orig_freq=sr, new_freq=target_sr)
                audio_t = torch.from_numpy(audio)
                audio = resampler(audio_t).numpy()
                sr = target_sr
            except Exception:
                pass
        return audio, sr
    except Exception as sf_err:
        logger.debug("soundfile failed to read %s: %s. Trying torchaudio...", audio_path, sf_err)

    try:
        import torchaudio

        wav_t, sr = torchaudio.load(str(audio_path))
        if sr != target_sr and target_sr > 0:
            import torchaudio.transforms as T

            resampler = T.Resample(orig_freq=sr, new_freq=target_sr)
            wav_t = resampler(wav_t)
            sr = target_sr
        return wav_t.numpy(), sr
    except Exception as ta_err:
        logger.error("Failed to load audio from %s: %s", audio_path, ta_err)
        raise RuntimeError(f"Unable to read audio file {audio_path}: {ta_err}") from ta_err


def save_audio_numpy(audio: np.ndarray, path: Path, sample_rate: int) -> Path:
    """Save 2D float32 numpy array (channels, samples) to audio file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Clip to avoid digital clipping distortion
    audio_clipped = np.clip(audio, -1.0, 1.0)

    try:
        import soundfile as sf

        # soundfile expects (samples, channels)
        data_to_write = audio_clipped.T if audio_clipped.ndim == 2 else audio_clipped
        subtype = "PCM_24" if path.suffix == ".flac" else "PCM_16"
        sf.write(str(path), data_to_write, sample_rate, subtype=subtype)
        return path
    except Exception as sf_err:
        logger.debug("soundfile write failed: %s, falling back to torchaudio", sf_err)

    try:
        import torch
        import torchaudio

        audio_t = torch.from_numpy(audio_clipped)
        torchaudio.save(str(path), audio_t, sample_rate)
        return path
    except Exception as ta_err:
        logger.error("Failed to save audio to %s: %s", path, ta_err)
        raise RuntimeError(f"Unable to write audio file {path}: {ta_err}") from ta_err


class StemSeparator:
    """Dual-engine audio stem separation service."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "omnirip" / "stems"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def separate_file(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        mode: str = "eco",
    ) -> StemResult:
        """
        Separate audio track into isolated vocals and instrumental backing.

        Args:
            input_path: Path to the source audio file.
            output_dir: Destination directory for separated stems. If None,
                uses the cache directory.
            mode: 'eco' (fast DSP phase-matrixing) or 'neural' (HDEMUCS deep learning).
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        stem_dir = output_dir or (self.cache_dir / f"{input_path.stem}_{input_path.stat().st_size}")
        stem_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = stem_dir / f"{input_path.stem}_{mode}_vocals.wav"
        inst_path = stem_dir / f"{input_path.stem}_{mode}_instrumental.wav"

        # Check existing cache
        if (
            vocals_path.exists()
            and inst_path.exists()
            and vocals_path.stat().st_size > 44
            and inst_path.stat().st_size > 44
        ):
            audio, sr = load_audio_numpy(vocals_path)
            duration = audio.shape[1] / max(1, sr)
            return StemResult(
                vocals_path=vocals_path,
                instrumental_path=inst_path,
                mode=mode,
                sample_rate=sr,
                duration_s=duration,
            )

        if mode == "neural":
            try:
                return self._separate_neural(input_path, vocals_path, inst_path)
            except Exception as e:
                logger.warning(
                    "Neural stem separation failed (%s); falling back to Eco DSP mode.",
                    e,
                )
                return self._separate_eco(input_path, vocals_path, inst_path)

        return self._separate_eco(input_path, vocals_path, inst_path)

    def _separate_eco(
        self,
        input_path: Path,
        vocals_path: Path,
        inst_path: Path,
    ) -> StemResult:
        """
        Eco DSP Stem Separation.

        Employs stereo mid-side phase cancellation with frequency-selective vocal
        formant attenuation:
        - Side channel contains stereo panning, reverb, synths, and stereo guitars.
        - Center Mid channel contains lead vocals, kick, and bass.
        - Low frequencies (<140 Hz) are preserved in mono for bass punch.
        - Center vocal band (200 Hz - 4200 Hz) is attenuated in the instrumental
          and isolated for the vocals.
        """
        audio, sr = load_audio_numpy(input_path)
        if audio.shape[0] == 1:
            # Duplicate mono to stereo
            audio = np.repeat(audio, 2, axis=0)

        n_samples = audio.shape[1]
        left = audio[0]
        right = audio[1]

        mid = 0.5 * (left + right)
        side = 0.5 * (left - right)

        # FFT on Mid channel for zero-phase frequency-selective vocal notch
        mid_fft = np.fft.rfft(mid)
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)

        # Build smooth vocal attenuation curve
        # Bass (< 140 Hz): untouched (1.0)
        # Vocal core (250 Hz - 4000 Hz): attenuated to 0.1 (-20 dB)
        # Air (> 6500 Hz): untouched (1.0)
        gain = np.ones_like(freqs, dtype=np.float32)

        vocal_core = (freqs >= 250.0) & (freqs <= 4000.0)
        gain[vocal_core] = 0.12

        # Smooth transition low: 140 Hz to 250 Hz
        trans_low = (freqs >= 140.0) & (freqs < 250.0)
        t_l = (freqs[trans_low] - 140.0) / (250.0 - 140.0)
        gain[trans_low] = 1.0 - 0.88 * 0.5 * (1.0 - np.cos(np.pi * t_l))

        # Smooth transition high: 4000 Hz to 6500 Hz
        trans_high = (freqs > 4000.0) & (freqs <= 6500.0)
        t_h = (freqs[trans_high] - 4000.0) / (6500.0 - 4000.0)
        gain[trans_high] = 0.12 + 0.88 * 0.5 * (1.0 - np.cos(np.pi * t_h))

        # Reconstruct Instrumental Mid
        filtered_mid = np.fft.irfft(mid_fft * gain, n=n_samples).astype(np.float32)

        # Reconstruct Instrumental Stereo
        inst_left = filtered_mid + side
        inst_right = filtered_mid - side
        inst_audio = np.stack([inst_left, inst_right], axis=0)

        # Vocal energy = Original Mid - Filtered Mid
        vocal_diff = mid - filtered_mid
        # Bandpass vocal to eliminate residual extreme sub or air hiss
        vocal_fft = np.fft.rfft(vocal_diff)
        vocal_bp = np.zeros_like(freqs, dtype=np.float32)
        vocal_bp[(freqs >= 180.0) & (freqs <= 5500.0)] = 1.0
        vocal_clean = np.fft.irfft(vocal_fft * vocal_bp, n=n_samples).astype(np.float32)

        # Vocals output as centered stereo
        vocals_audio = np.stack([vocal_clean, vocal_clean], axis=0)

        save_audio_numpy(vocals_audio, vocals_path, sr)
        save_audio_numpy(inst_audio, inst_path, sr)

        duration = n_samples / max(1, sr)
        return StemResult(
            vocals_path=vocals_path,
            instrumental_path=inst_path,
            mode="eco",
            sample_rate=sr,
            duration_s=duration,
        )

    def _separate_neural(
        self,
        input_path: Path,
        vocals_path: Path,
        inst_path: Path,
    ) -> StemResult:
        """
        Neural AI Stem Separation using torchaudio HDEMUCS (MUSDB-HQ).

        Separates audio into 4 stems: drums, bass, other, vocals.
        Mixes drums + bass + other -> instrumental.
        Outputs vocals -> vocals.
        """
        import torch
        import torchaudio

        device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

        # Load torchaudio HDEMUCS bundle
        bundle = torchaudio.pipelines.HDEMUCS_HIGH_MUSDB
        model = bundle.get_model().to(device)
        model.eval()

        audio_np, sr = load_audio_numpy(input_path, target_sr=bundle.sample_rate)
        waveform = torch.from_numpy(audio_np)
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        total_samples = waveform.shape[1]
        chunk_len = int(10 * sr)
        hop_len = int(8 * sr)

        if total_samples <= chunk_len:
            ref = waveform.mean(0)
            norm = (waveform - ref.mean()) / (ref.std() + 1e-8)
            with torch.no_grad():
                srcs = model(norm.unsqueeze(0).to(device))[0].cpu()
                srcs = srcs * (ref.std() + 1e-8) + ref.mean()
            output = srcs
        else:
            output = torch.zeros(4, 2, total_samples)
            weight = torch.zeros(total_samples)
            window = torch.hann_window(chunk_len)

            for start in range(0, total_samples, hop_len):
                end = min(start + chunk_len, total_samples)
                chunk = waveform[:, start:end]
                act_len = chunk.shape[1]
                if act_len < chunk_len:
                    chunk = torch.nn.functional.pad(chunk, (0, chunk_len - act_len))
                ref = chunk.mean(0)
                norm = (chunk - ref.mean()) / (ref.std() + 1e-8)
                with torch.no_grad():
                    srcs = model(norm.unsqueeze(0).to(device))[0].cpu()
                    srcs = srcs * (ref.std() + 1e-8) + ref.mean()
                w = window[:act_len]
                output[:, :, start:end] += srcs[:, :, :act_len] * w
                weight[start:end] += w

            weight[weight == 0] = 1.0
            output = output / weight

        # Sources: [0: drums, 1: bass, 2: other, 3: vocals]
        drums = output[0].numpy()
        bass = output[1].numpy()
        other = output[2].numpy()
        vocals = output[3].numpy()

        instrumental = drums + bass + other

        save_audio_numpy(vocals, vocals_path, sr)
        save_audio_numpy(instrumental, inst_path, sr)

        duration = total_samples / max(1, sr)
        return StemResult(
            vocals_path=vocals_path,
            instrumental_path=inst_path,
            mode="neural",
            sample_rate=sr,
            duration_s=duration,
        )
