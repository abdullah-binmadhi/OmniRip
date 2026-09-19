"""Vocal and Instrumental Stem Separation service for OmniRip.

Multi-Stage Studio Pipeline:
1. Deep Neural AI Mode: Source separation powered by torchaudio HDEMUCS (MUSDB-HQ).
2. Adaptive Spectral Gating: Real-time Voice Activity Detection (VAD) and noise-floor
   gating to eliminate inter-phrase bleed and high-frequency cymbal splash.
3. Vocal Harmonic Polish: Suppresses isolated phase-smearing and metallic musical noise.
4. Instrumental Inversion Subtraction: Bit-exact master subtraction (Original - Vocals)
   so the backing instruments have 0% neural or robotic distortion.
5. Eco DSP Fallback: Zero-latency mid-side phase cancellation for offline hardware.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal

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
    engine: str = "unknown"  # "bs_roformer" | "hdemucs" | "eco"


VOCAL_REMEDIATIONS: dict[str, str] = {
    "fix_pumping": "Volume Pumping Fix (Bypass Ducking Gate)",
    "de_robot": "De-Robotize (Phase Polish & Anti-Flange)",
    "de_bleed": "Acoustic Bleed Shield (Synth/Guitar Rejection)",
    "de_reverb": "Room Reverb Stripper (Tail Decay Suppression)",
    "de_ess": "Dynamic De-Esser (5.5k-8.5k Sibilance Tamer)",
    "de_plosive": "Sub-Plosive Cut (80Hz High-Pass Pop Filter)",
    "air_boost": "Silk & Air Exciter (+2.5dB >10kHz Sheen)",
    "warmth_body": "Chest Warmth & Body (280Hz Fundamental)",
    "center_lock": "Phantom Center Pin (Stereo Bleed Collapse)",
    "clarity_exciter": "Presence & Articulation (+2dB 3.2kHz)",
}

INST_REMEDIATIONS: dict[str, str] = {
    "kill_whispers": "Kill Ghost Whispers (Side-Vocal Attenuation)",
    "preserve_drums": "Transient Drum Preserver (Snare/Kick Punch)",
    "restore_center": "Kick & Bass Center Punch (Mono Sub <120Hz)",
    "pure_inversion": "Pure Phase Inversion (Bit-Exact Subtraction)",
    "anti_bleed_synths": "Formant Bleed Notch (1k-2.8k Vocal Masking)",
    "de_mud": "Low-Mid De-Mud (300Hz Boxiness Cut)",
    "sub_bass_clean": "Sub-Bass Tightener (30Hz Subsonic Cut)",
    "stereo_widen": "Spatial Stereo Widener (Immersion Boost)",
    "cymbal_sparkle": "Cymbal & Air Sparkle (+2.5dB >12kHz)",
    "dynamic_leveler": "RMS Leveler & Dip Fix (Smooth Cutouts)",
}


def get_stem_cache_suffix(flags: set[str] | list[str] | str) -> str:
    """Generate a compact, deterministic, collision-free filesystem cache suffix."""
    f_set = {flags} if isinstance(flags, str) else set(flags)
    f_set.discard("natural")
    if not f_set:
        return ""
    sorted_flags = sorted(f_set)
    if len(sorted_flags) <= 2:
        return "_" + "_".join(sorted_flags)
    h = hashlib.sha256("_".join(sorted_flags).encode()).hexdigest()[:8]
    return f"_{len(sorted_flags)}fx_{h}"


def load_audio_numpy(audio_path: Path, target_sr: int = 44100) -> tuple[np.ndarray, int]:
    """Load audio file into a 2D float32 numpy array of shape (channels, samples)."""
    try:
        import soundfile as sf

        data, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
        audio = data.T
        if sr != target_sr and target_sr > 0:
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
    """Save 2D float32 numpy array (channels, samples) to audio file with -1.0 dBFS headroom."""
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0.891:
        audio = audio * (0.891 / peak)
    audio_clipped = np.clip(audio, -1.0, 1.0)

    try:
        import soundfile as sf

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


def apply_adaptive_spectral_gate(
    audio: np.ndarray, sr: int, profile: str = "natural"
) -> np.ndarray:
    """
    Apply natural vocal envelope leveling and gentle inter-phrase silence attenuation.

    - "fix_pumping": Completely bypasses envelope ducking to guarantee 100% transparent linear gain.
    - "natural": Standard gating with 80 ms release smoothing.
    - "kill_reverb": Tighter gating targeting inter-phrase silence.
    """
    if profile == "fix_pumping":
        return audio.astype(np.float32)

    if audio.ndim == 1:
        audio = audio[np.newaxis, :]

    n_samples = audio.shape[1]
    if n_samples < sr // 4:
        return audio.astype(np.float32)

    # 300 ms musical smoothing window
    win_len = int(0.300 * sr)
    if win_len % 2 == 0:
        win_len += 1
    window = np.hanning(win_len).astype(np.float32)
    window /= np.sum(window)

    audio_mono = np.mean(audio, axis=0)
    env = np.sqrt(np.convolve(audio_mono**2, window, mode="same") + 1e-9)
    peak_env = float(np.max(env))

    p8 = float(np.percentile(env, 8))
    if p8 > 0.35 * peak_env:
        return audio.astype(np.float32)

    if profile == "kill_reverb":
        silence_thresh = max(p8 * 1.8, 0.02 * peak_env)
        floor = 0.02
        gain = np.clip((env - silence_thresh * 0.4) / (silence_thresh * 1.6 + 1e-6), floor, 1.0)
    else:  # natural / air_boost / de_robot
        silence_thresh = max(p8 * 1.5, 0.015 * peak_env)
        gain = np.clip((env - silence_thresh * 0.4) / (silence_thresh * 1.6 + 1e-6), 0.05, 1.0)

    # 80 ms release smoothing on gain - eliminates pumping artifact
    smooth_len = int(0.080 * sr)
    if smooth_len % 2 == 0:
        smooth_len += 1
    smooth_win = np.hanning(smooth_len).astype(np.float32)
    smooth_win /= np.sum(smooth_win)
    gain_smooth = np.convolve(gain, smooth_win, mode="same")

    return (audio * gain_smooth[np.newaxis, :]).astype(np.float32)


def apply_vocal_harmonic_polish(audio: np.ndarray, sr: int, profile: str = "natural") -> np.ndarray:
    """
    De-robotize vocals via multi-frame STFT spectral magnitude smoothing.

    - "de_robot": 5-frame weighted STFT magnitude smoothing to completely eliminate
      phase flutter and robotic metallic frame transitions.
    - "air_boost": +2.5 dB high-frequency air shelf above 8 kHz to restore breath sparkle.
    - "natural": Balanced 3-frame STFT magnitude smoothing with +1.5 dB air shelf.
    """
    if audio.ndim == 1:
        audio = audio[np.newaxis, :]

    n_ch, n_samples = audio.shape
    if n_samples < 2048:
        peak = float(np.max(np.abs(audio)))
        if peak > 0.891:
            return (audio * (0.891 / peak)).astype(np.float32)
        return audio.astype(np.float32)

    nperseg = 1024
    noverlap = 768  # 75% overlap for smooth reconstruction
    result_channels = []

    for ch in range(n_ch):
        f, _, Z = signal.stft(audio[ch], fs=sr, nperseg=nperseg, noverlap=noverlap)
        mag = np.abs(Z)
        phase = np.angle(Z)

        if profile == "de_robot" and mag.shape[1] >= 5:
            # 5-frame weighted smoothing: deep de-robotization
            mag_smooth = np.copy(mag)
            mag_smooth[:, 2:-2] = (
                0.10 * mag[:, :-4]
                + 0.20 * mag[:, 1:-3]
                + 0.40 * mag[:, 2:-2]
                + 0.20 * mag[:, 3:-1]
                + 0.10 * mag[:, 4:]
            )
        else:
            # Standard 3-frame magnitude smoothing
            mag_smooth = np.empty_like(mag)
            mag_smooth[:, 0] = 0.5 * mag[:, 0] + 0.5 * mag[:, 1]
            mag_smooth[:, -1] = 0.5 * mag[:, -2] + 0.5 * mag[:, -1]
            mag_smooth[:, 1:-1] = 0.25 * mag[:, :-2] + 0.50 * mag[:, 1:-1] + 0.25 * mag[:, 2:]

        # High-frequency breath/air recovery shelf
        if sr >= 32000:
            air_boost = 1.33 if profile == "air_boost" else 1.19
            air_mask = f >= 8000.0
            mag_smooth[air_mask, :] *= air_boost

        Z_smooth = mag_smooth * np.exp(1j * phase)
        _, ch_out = signal.istft(Z_smooth, fs=sr, nperseg=nperseg, noverlap=noverlap)

        if ch_out.shape[0] > n_samples:
            ch_out = ch_out[:n_samples]
        elif ch_out.shape[0] < n_samples:
            ch_out = np.pad(ch_out, (0, n_samples - ch_out.shape[0]))
        result_channels.append(ch_out)

    polished = np.stack(result_channels, axis=0).astype(np.float32)
    peak = float(np.max(np.abs(polished)))
    if peak > 0.891:
        polished = polished * (0.891 / peak)
    return polished


def apply_mid_side_vocal_suppression(
    instrumental: np.ndarray, sr: int, profile: str = "natural"
) -> np.ndarray:
    """
    Suppress residual vocal bleed from the instrumental stem.

    - "kill_whispers": Notches center-panned vocal fundamentals (-6 dB) AND applies a
      surgical -4.5 dB de-bleed on the Side channel (400–3500 Hz) to kill wide stereo
      reverb tails and backing vocal whispers.
    - "restore_center": Relaxes Mid notch to -2.5 dB to preserve kick and snare punch.
    - "natural": Standard -6 dB Mid channel notch.
    """
    if instrumental.ndim == 1 or instrumental.shape[0] < 2:
        return instrumental.astype(np.float32)

    n_samples = instrumental.shape[1]
    left = instrumental[0]
    right = instrumental[1]

    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)

    nperseg = 2048
    noverlap = 1536
    f, _, Z_mid = signal.stft(mid, fs=sr, nperseg=nperseg, noverlap=noverlap)

    # Mid notch depth
    mid_factor = 0.75 if profile == "restore_center" else 0.50
    vocal_band = (f >= 300.0) & (f <= 3000.0)
    attenuation_mid = np.where(vocal_band, mid_factor, 1.0).astype(np.float32)
    Z_mid_clean = Z_mid * attenuation_mid[:, np.newaxis]

    _, mid_clean = signal.istft(Z_mid_clean, fs=sr, nperseg=nperseg, noverlap=noverlap)
    if mid_clean.shape[0] > n_samples:
        mid_clean = mid_clean[:n_samples]
    elif mid_clean.shape[0] < n_samples:
        mid_clean = np.pad(mid_clean, (0, n_samples - mid_clean.shape[0]))

    # If kill_whispers is active, clean stereo reverb from Side channel as well
    if profile == "kill_whispers":
        _, _, Z_side = signal.stft(side, fs=sr, nperseg=nperseg, noverlap=noverlap)
        side_vocal_band = (f >= 400.0) & (f <= 3500.0)
        attenuation_side = np.where(side_vocal_band, 0.60, 1.0).astype(np.float32)
        Z_side_clean = Z_side * attenuation_side[:, np.newaxis]
        _, side_clean = signal.istft(Z_side_clean, fs=sr, nperseg=nperseg, noverlap=noverlap)
        if side_clean.shape[0] > n_samples:
            side_clean = side_clean[:n_samples]
        elif side_clean.shape[0] < n_samples:
            side_clean = np.pad(side_clean, (0, n_samples - side_clean.shape[0]))
        side_to_use = side_clean
    else:
        side_to_use = side[: len(mid_clean)]

    # Reconstruct stereo from cleaned mid + side
    left_clean = (mid_clean + side_to_use).astype(np.float32)
    right_clean = (mid_clean - side_to_use).astype(np.float32)
    result = np.stack([left_clean, right_clean], axis=0)

    peak = float(np.max(np.abs(result))) if result.size > 0 else 0.0
    if peak > 0.891:
        result = result * (0.891 / peak)
    return result


def apply_wiener_vocal_mask(
    instrumental: np.ndarray,
    vocals: np.ndarray,
    sr: int,
    profile: str = "natural",
    suppression_db: float = 6.0,
) -> np.ndarray:
    """
    Wiener-filter vocal residual suppression on the instrumental.

    - "kill_whispers": Lowers dominance threshold to 0.40 and increases suppression to -9 dB.
    - "preserve_drums": Restricts mask to < 5000 Hz so drum attacks & cymbals are preserved.
    - "natural": Standard 0.60 dominance threshold with -6 dB suppression.
    """
    if instrumental.shape[1] < 2048:
        return instrumental.astype(np.float32)

    nperseg = 2048
    noverlap = 1536
    min_len = min(instrumental.shape[1], vocals.shape[1] if vocals.ndim == 2 else len(vocals))

    inst_mono = np.mean(instrumental[:, :min_len], axis=0)
    voc_mono = np.mean(vocals[:, :min_len], axis=0) if vocals.ndim == 2 else vocals[:min_len]

    f, _, Z_inst = signal.stft(inst_mono, fs=sr, nperseg=nperseg, noverlap=noverlap)
    _, _, Z_voc = signal.stft(voc_mono, fs=sr, nperseg=nperseg, noverlap=noverlap)

    mag_inst = np.abs(Z_inst) + 1e-9
    mag_voc = np.abs(Z_voc) + 1e-9

    actual_db = 9.0 if profile == "kill_whispers" else suppression_db
    suppression_linear = 10 ** (-actual_db / 20.0)
    vocal_dominance = mag_voc / (mag_inst + mag_voc)

    threshold = 0.40 if profile == "kill_whispers" else 0.60
    mask = np.where(vocal_dominance > threshold, suppression_linear, 1.0).astype(np.float32)

    if profile == "preserve_drums":
        drum_preserve_mask = f >= 5000.0
        mask[drum_preserve_mask, :] = 1.0

    result_channels = []
    for ch in range(instrumental.shape[0]):
        ch_data = instrumental[ch, :min_len]
        _, _, Z_ch = signal.stft(ch_data, fs=sr, nperseg=nperseg, noverlap=noverlap)
        Z_masked = Z_ch * mask
        _, ch_out = signal.istft(Z_masked, fs=sr, nperseg=nperseg, noverlap=noverlap)
        if ch_out.shape[0] > min_len:
            ch_out = ch_out[:min_len]
        elif ch_out.shape[0] < min_len:
            ch_out = np.pad(ch_out, (0, min_len - ch_out.shape[0]))
        result_channels.append(ch_out)

    result = np.stack(result_channels, axis=0).astype(np.float32)
    peak = float(np.max(np.abs(result))) if result.size > 0 else 0.0
    if peak > 0.891:
        result = result * (0.891 / peak)
    return result


def apply_inversion_subtraction(
    original: np.ndarray,
    cleaned_vocals: np.ndarray,
    sr: int,
) -> np.ndarray:
    """
    Construct instrumental via phase-inversion subtraction:
    Clean Instrumental = Original Audio - Cleaned Vocals.

    Preserves 100% of original drum transients, bass, synths, and guitars
    with zero neural/robotic distortion.
    """
    if original.ndim == 1:
        original = np.repeat(original[np.newaxis, :], 2, axis=0)
    if cleaned_vocals.ndim == 1:
        cleaned_vocals = np.repeat(cleaned_vocals[np.newaxis, :], 2, axis=0)

    min_len = min(original.shape[1], cleaned_vocals.shape[1])
    orig_trim = original[:, :min_len]
    voc_trim = cleaned_vocals[:, :min_len]

    # Subtraction
    inst_raw = orig_trim - voc_trim

    # Guarantee sub-bass (<140 Hz) is 100% untouched from original audio
    # so kick drum and bassline never suffer any phase cancellation
    nperseg = 2048
    noverlap = 1536
    f, _, Z_orig = signal.stft(orig_trim, fs=sr, nperseg=nperseg, noverlap=noverlap)
    _, _, Z_inst = signal.stft(inst_raw, fs=sr, nperseg=nperseg, noverlap=noverlap)

    sub_mask = (f < 140.0)[:, np.newaxis]
    Z_final = np.where(sub_mask, Z_orig, Z_inst)

    _, inst_out = signal.istft(Z_final, fs=sr, nperseg=nperseg, noverlap=noverlap)
    if inst_out.shape[1] > min_len:
        inst_out = inst_out[:, :min_len]
    elif inst_out.shape[1] < min_len:
        inst_out = np.pad(inst_out, ((0, 0), (0, min_len - inst_out.shape[1])))

    # Normalize to -1.0 dBFS true-peak headroom to eliminate digital clipping
    peak = float(np.max(np.abs(inst_out))) if inst_out.size > 0 else 0.0
    if peak > 0.891:
        inst_out = inst_out * (0.891 / peak)

    return inst_out.astype(np.float32)


def apply_vocal_remediations(
    vocals: np.ndarray,
    sr: int,
    flags: set[str],
    progress_callback: Callable[[float, str], None] | None = None,
) -> np.ndarray:
    """Apply requested vocal defect remediations in optimal acoustic order."""
    if not flags or flags == {"natural"}:
        voc = apply_adaptive_spectral_gate(vocals, sr, profile="natural")
        return apply_vocal_harmonic_polish(voc, sr, profile="natural")

    voc = vocals.copy()
    channels, n_samples = voc.shape
    if n_samples < 64:
        return voc

    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
    safe_freqs = np.maximum(freqs, 1.0)

    # 1. de_plosive: Steep 80 Hz high-pass pop/rumble filter
    if "de_plosive" in flags:
        hp_curve = 1.0 / (1.0 + (80.0 / safe_freqs) ** 4)
        voc = np.fft.irfft(np.fft.rfft(voc, axis=-1) * hp_curve, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 2. de_reverb: Late reverberation & flutter reflection suppression
    if "de_reverb" in flags and n_samples >= 2048:
        nperseg = 2048
        noverlap = 1536
        _, _, Z = signal.stft(voc, fs=sr, nperseg=nperseg, noverlap=noverlap)
        mag = np.abs(Z) + 1e-9
        tail = np.minimum.reduce(
            [np.roll(mag, shift=s, axis=-1) for s in range(min(5, mag.shape[-1]))]
        )
        reverb_suppress = np.clip(1.0 - 0.45 * (tail / mag), 0.25, 1.0)
        _, voc_dereverb = signal.istft(
            Z * reverb_suppress, fs=sr, nperseg=nperseg, noverlap=noverlap
        )
        if voc_dereverb.shape[-1] >= n_samples:
            voc = voc_dereverb[:, :n_samples].astype(np.float32)
        else:
            voc = np.pad(voc_dereverb, ((0, 0), (0, n_samples - voc_dereverb.shape[-1]))).astype(
                np.float32
            )

    # 3. de_bleed: Side-channel synth and guitar rejection
    if "de_bleed" in flags:
        mid = 0.5 * (voc[0] + voc[1])
        side = 0.5 * (voc[0] - voc[1]) * 0.40
        voc = np.stack([mid + side, mid - side], axis=0).astype(np.float32)

    # 4. de_robot: Harmonic phase polish
    polish_prof = "de_robot" if "de_robot" in flags else "natural"
    voc = apply_vocal_harmonic_polish(voc, sr, profile=polish_prof)

    # 5. de_ess: Dynamic sibilance tamer (5.5 kHz - 8.5 kHz)
    if "de_ess" in flags:
        ess_band = (freqs >= 5500.0) & (freqs <= 8500.0)
        fft_v = np.fft.rfft(voc, axis=-1)
        ess_curve = np.where(ess_band, 10 ** (-4.5 / 20.0), 1.0).astype(np.float32)
        voc = np.fft.irfft(fft_v * ess_curve, n=n_samples, axis=-1).astype(np.float32)

    # 6. warmth_body: Chest resonance boost at 280 Hz
    if "warmth_body" in flags:
        dist_w = np.log2(safe_freqs / 280.0)
        bell_w = np.exp(-0.5 * (dist_w / 0.55) ** 2)
        curve_w = (10 ** (2.5 * bell_w / 20.0)).astype(np.float32)
        voc = np.fft.irfft(np.fft.rfft(voc, axis=-1) * curve_w, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 7. clarity_exciter: Intelligibility & speech presence at 3.2 kHz
    if "clarity_exciter" in flags:
        dist_c = np.log2(safe_freqs / 3200.0)
        bell_c = np.exp(-0.5 * (dist_c / 0.50) ** 2)
        curve_c = (10 ** (2.0 * bell_c / 20.0)).astype(np.float32)
        voc = np.fft.irfft(np.fft.rfft(voc, axis=-1) * curve_c, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 8. air_boost: Silk & air shelf above 10 kHz
    if "air_boost" in flags:
        dist_a = np.maximum(0.0, np.log2(safe_freqs / 10000.0))
        curve_a = (10 ** (2.5 * np.clip(dist_a / 1.0, 0.0, 1.0) / 20.0)).astype(np.float32)
        voc = np.fft.irfft(np.fft.rfft(voc, axis=-1) * curve_a, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 9. fix_pumping: Adaptive spectral gate bypass or smooth envelope
    gate_prof = "fix_pumping" if "fix_pumping" in flags else "natural"
    voc = apply_adaptive_spectral_gate(voc, sr, profile=gate_prof)

    # 10. center_lock: Pin vocal stereo image tightly to phantom center
    if "center_lock" in flags:
        mid = 0.5 * (voc[0] + voc[1])
        side = 0.5 * (voc[0] - voc[1]) * 0.15
        voc = np.stack([mid + side, mid - side], axis=0).astype(np.float32)

    peak = float(np.max(np.abs(voc))) if voc.size > 0 else 0.0
    if peak > 0.891:
        voc = voc * (0.891 / peak)
    return voc.astype(np.float32)


def apply_inst_remediations(
    inst_blend: np.ndarray,
    orig_audio: np.ndarray,
    vocals_clean: np.ndarray,
    sr: int,
    flags: set[str],
    blend_weight: float = 0.50,
    progress_callback: Callable[[float, str], None] | None = None,
) -> np.ndarray:
    """Apply requested instrumental defect remediations in optimal acoustic order."""
    inst = inst_blend.copy()
    channels, n_samples = inst.shape
    if n_samples < 64:
        return inst

    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)
    safe_freqs = np.maximum(freqs, 1.0)

    # 1. sub_bass_clean: 30 Hz subsonic filter
    if "sub_bass_clean" in flags:
        hp_sub = 1.0 / (1.0 + (30.0 / safe_freqs) ** 6)
        inst = np.fft.irfft(np.fft.rfft(inst, axis=-1) * hp_sub, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 2. de_mud: 300 Hz boxiness cut
    if "de_mud" in flags:
        dist_m = np.log2(safe_freqs / 300.0)
        bell_m = np.exp(-0.5 * (dist_m / 0.45) ** 2)
        curve_m = (10 ** (-2.5 * bell_m / 20.0)).astype(np.float32)
        inst = np.fft.irfft(np.fft.rfft(inst, axis=-1) * curve_m, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 3. anti_bleed_synths: Formant notch at 1600 Hz and 2400 Hz
    if "anti_bleed_synths" in flags:
        dist_n1 = np.log2(safe_freqs / 1600.0)
        dist_n2 = np.log2(safe_freqs / 2400.0)
        notch = np.exp(-0.5 * (dist_n1 / 0.35) ** 2) + np.exp(-0.5 * (dist_n2 / 0.35) ** 2)
        curve_n = (10 ** (-3.0 * np.clip(notch, 0.0, 1.0) / 20.0)).astype(np.float32)
        inst = np.fft.irfft(np.fft.rfft(inst, axis=-1) * curve_n, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 4. kill_whispers / restore_center mid-side suppression
    ms_prof = (
        "restore_center"
        if "restore_center" in flags
        else ("kill_whispers" if "kill_whispers" in flags else "natural")
    )
    inst = apply_mid_side_vocal_suppression(inst, sr, profile=ms_prof)

    # 5. preserve_drums & Wiener mask
    wiener_prof = (
        "preserve_drums"
        if "preserve_drums" in flags
        else ("kill_whispers" if "kill_whispers" in flags else "natural")
    )
    inst = apply_wiener_vocal_mask(inst, vocals_clean, sr, profile=wiener_prof)

    # 6. restore_center: Monos sub-bass <120 Hz and tightens kick punch
    if "restore_center" in flags:
        mono_factor = np.clip(1.0 - (freqs / 120.0), 0.0, 1.0)
        fft_l = np.fft.rfft(inst[0])
        fft_r = np.fft.rfft(inst[1])
        fft_m = 0.5 * (fft_l + fft_r)
        l_mono = fft_l * (1.0 - mono_factor) + fft_m * mono_factor
        r_mono = fft_r * (1.0 - mono_factor) + fft_m * mono_factor
        inst[0] = np.fft.irfft(l_mono, n=n_samples).astype(np.float32)
        inst[1] = np.fft.irfft(r_mono, n=n_samples).astype(np.float32)

    # 7. cymbal_sparkle: High-shelf boost >12 kHz (+2.5 dB)
    if "cymbal_sparkle" in flags:
        dist_s = np.maximum(0.0, np.log2(safe_freqs / 12000.0))
        curve_s = (10 ** (2.5 * np.clip(dist_s / 0.8, 0.0, 1.0) / 20.0)).astype(np.float32)
        inst = np.fft.irfft(np.fft.rfft(inst, axis=-1) * curve_s, n=n_samples, axis=-1).astype(
            np.float32
        )

    # 8. stereo_widen: Spatial stereo expansion (+1.5 dB on sides)
    if "stereo_widen" in flags:
        mid = 0.5 * (inst[0] + inst[1])
        side = 0.5 * (inst[0] - inst[1]) * 1.25
        inst = np.stack([mid + side, mid - side], axis=0).astype(np.float32)

    # 9. dynamic_leveler: Smooth sudden RMS dropouts when loud vocals cut out
    if "dynamic_leveler" in flags and n_samples >= 1024:
        frame_len = int(0.05 * sr)
        if frame_len > 0:
            n_frames = n_samples // frame_len
            if n_frames > 1:
                chunked = inst[:, : n_frames * frame_len].reshape(2, n_frames, frame_len)
                rms = np.sqrt(np.mean(chunked**2, axis=-1) + 1e-8)
                avg_rms = np.mean(rms, axis=-1, keepdims=True)
                dip_ratio = np.clip(avg_rms / (rms + 1e-8), 1.0, 1.4)
                gain_curve = np.repeat(dip_ratio, frame_len, axis=-1)
                inst[:, : n_frames * frame_len] *= gain_curve

    peak = float(np.max(np.abs(inst))) if inst.size > 0 else 0.0
    if peak > 0.891:
        inst = inst * (0.891 / peak)
    return inst.astype(np.float32)


def postprocess_stems(
    orig_audio: np.ndarray,
    vocals_raw: np.ndarray,
    inst_model: np.ndarray,
    sr: int,
    blend_weight: float = 0.50,
    vocal_flags: set[str] | list[str] | str = "natural",
    inst_flags: set[str] | list[str] | str = "natural",
    progress_callback: Callable[[float, str], None] | None = None,
    vocal_profile: str | None = None,
    inst_profile: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Unified multi-stage DSP post-processing for vocal and instrumental stems."""
    if vocal_profile is not None and vocal_flags == "natural":
        vocal_flags = {vocal_profile}
    if inst_profile is not None and inst_flags == "natural":
        inst_flags = {inst_profile}

    v_set = {vocal_flags} if isinstance(vocal_flags, str) else set(vocal_flags)
    i_set = {inst_flags} if isinstance(inst_flags, str) else set(inst_flags)

    if progress_callback:
        n_v = len([f for f in v_set if f != "natural"])
        progress_callback(80.0, f"Remediation: Applying {n_v} vocal defect filters...")

    vocals_clean = apply_vocal_remediations(
        vocals_raw, sr, v_set, progress_callback=progress_callback
    )

    if progress_callback:
        progress_callback(88.0, "Master Polish: Residual-additive instrumental blend...")

    if "pure_inversion" in i_set:
        inst_base = apply_inversion_subtraction(orig_audio, vocals_clean, sr)
    else:
        inst_inversion = apply_inversion_subtraction(orig_audio, vocals_clean, sr)
        min_len = min(inst_model.shape[1], inst_inversion.shape[1])
        inst_base = inst_inversion[:, :min_len] + blend_weight * (
            inst_model[:, :min_len] - inst_inversion[:, :min_len]
        )

    if progress_callback:
        n_i = len([f for f in i_set if f != "natural"])
        progress_callback(92.0, f"Remediation: Applying {n_i} instrumental defect filters...")

    inst_final = apply_inst_remediations(
        inst_base,
        orig_audio,
        vocals_clean,
        sr,
        i_set,
        blend_weight=blend_weight,
        progress_callback=progress_callback,
    )

    return vocals_clean, inst_final


def load_stem_profile(stem_dir: Path) -> dict[str, Any]:
    """
    Load user-selected imperfection profiles and settings for a stem directory.
    Returns a dict with 'vocal_profile', 'inst_profile', 'vocal_flags', 'inst_flags', etc.
    """
    prof_path = stem_dir / "profile.json"
    if prof_path.exists():
        try:
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if "vocal_flags" not in data:
                    v_p = data.get("vocal_profile", "natural")
                    data["vocal_flags"] = [v_p] if v_p != "natural" else []
                if "inst_flags" not in data:
                    i_p = data.get("inst_profile", "natural")
                    data["inst_flags"] = [i_p] if i_p != "natural" else []
                return data
        except Exception as e:
            logger.debug(f"Could not read stem profile {prof_path}: {e}")
    return {
        "vocal_profile": "natural",
        "inst_profile": "natural",
        "vocal_flags": [],
        "inst_flags": [],
        "bs_roformer_weight": 0.70,
        "hdemucs_weight": 0.50,
    }


def save_stem_profile(
    stem_dir: Path,
    profile_data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """
    Save user-selected defect remediation profile to disk so OmniRip remembers
    the chosen fixes whenever this track is auditioned or re-processed.
    """
    prof_path = stem_dir / "profile.json"
    try:
        current = load_stem_profile(stem_dir)
        if profile_data:
            current.update(profile_data)
        if kwargs:
            current.update(kwargs)
        if "vocal_flags" in current and "vocal_profile" not in current:
            vf = current["vocal_flags"]
            current["vocal_profile"] = vf[0] if vf else "natural"
        if "inst_flags" in current and "inst_profile" not in current:
            inf = current["inst_flags"]
            current["inst_profile"] = inf[0] if inf else "natural"
        prof_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to write stem profile {prof_path}: {e}")


class StemSeparator:
    """Multi-stage audio stem separation and de-bleeding service."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "omnirip" / "stems"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def separate_file(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        mode: str = "neural",
        progress_callback: Callable[[float, str], None] | None = None,
        bs_roformer_weight: float = 0.70,
        hdemucs_weight: float = 0.50,
        vocal_flags: set[str] | list[str] | str = "natural",
        inst_flags: set[str] | list[str] | str = "natural",
        vocal_profile: str | None = None,
        inst_profile: str | None = None,
    ) -> StemResult:
        """
        Separate audio track into isolated vocals and instrumental backing using
        the multi-stage clean pipeline.

        Args:
            input_path: Path to the source audio file.
            output_dir: Destination directory for separated stems.
            mode: 'neural' (BS-RoFormer → HDEMUCS) or 'eco' (DSP phase matrixing).
            progress_callback: Callback receiving (percentage, step_description).
            bs_roformer_weight: Neural-vs-inversion blend for BS-RoFormer (0.0–1.0).
            hdemucs_weight: Neural-vs-inversion blend for HDEMUCS (0.0–1.0).
            vocal_flags: Selected vocal defect remediations (flags set/list).
            inst_flags: Selected instrumental defect remediations (flags set/list).
            vocal_profile: Legacy profile name (for backwards compatibility).
            inst_profile: Legacy profile name (for backwards compatibility).
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        stem_dir = output_dir or (self.cache_dir / f"{input_path.stem}_{input_path.stat().st_size}")
        stem_dir.mkdir(parents=True, exist_ok=True)

        if vocal_profile is not None and vocal_flags == "natural":
            vocal_flags = {vocal_profile}
        if inst_profile is not None and inst_flags == "natural":
            inst_flags = {inst_profile}

        v_set = {vocal_flags} if isinstance(vocal_flags, str) else set(vocal_flags)
        i_set = {inst_flags} if isinstance(inst_flags, str) else set(inst_flags)

        v_sfx = get_stem_cache_suffix(v_set)
        i_sfx = get_stem_cache_suffix(i_set)
        vocals_path = stem_dir / f"{input_path.stem}_{mode}_vocals{v_sfx}.wav"
        inst_path = stem_dir / f"{input_path.stem}_{mode}_instrumental{i_sfx}.wav"

        raw_vocals_path = stem_dir / f"{input_path.stem}_{mode}_raw_vocals.wav"
        raw_inst_path = stem_dir / f"{input_path.stem}_{mode}_raw_inst.wav"

        # Check existing final cache
        if (
            vocals_path.exists()
            and inst_path.exists()
            and vocals_path.stat().st_size > 44
            and inst_path.stat().st_size > 44
        ):
            if progress_callback:
                progress_callback(100.0, "Loaded stems from warm cache.")
            audio, sr = load_audio_numpy(vocals_path)
            duration = audio.shape[1] / max(1, sr)
            return StemResult(
                vocals_path=vocals_path,
                instrumental_path=inst_path,
                mode=mode,
                sample_rate=sr,
                duration_s=duration,
                engine="bs_roformer" if mode in ("neural", "bs_roformer") else mode,
            )

        # Fast path: If raw model stems exist, re-postprocess immediately without neural inference!
        if (
            raw_vocals_path.exists()
            and raw_inst_path.exists()
            and raw_vocals_path.stat().st_size > 44
            and raw_inst_path.stat().st_size > 44
        ):
            if progress_callback:
                progress_callback(
                    30.0, "Re-processing cached neural stems with selected profile..."
                )
            orig_audio, sr = load_audio_numpy(input_path)
            raw_voc, _ = load_audio_numpy(raw_vocals_path, target_sr=sr)
            raw_inst, _ = load_audio_numpy(raw_inst_path, target_sr=sr)
            weight = bs_roformer_weight if mode in ("neural", "bs_roformer") else hdemucs_weight
            voc_clean, inst_clean = postprocess_stems(
                orig_audio,
                raw_voc,
                raw_inst,
                sr,
                blend_weight=weight,
                vocal_flags=v_set,
                inst_flags=i_set,
                progress_callback=progress_callback,
            )
            save_audio_numpy(voc_clean, vocals_path, sr)
            save_audio_numpy(inst_clean, inst_path, sr)
            save_stem_profile(
                stem_dir,
                {
                    "vocal_flags": sorted(v_set),
                    "inst_flags": sorted(i_set),
                    "vocal_profile": next(iter(v_set), "natural"),
                    "inst_profile": next(iter(i_set), "natural"),
                    "bs_roformer_weight": bs_roformer_weight,
                    "hdemucs_weight": hdemucs_weight,
                },
            )
            duration = orig_audio.shape[1] / max(1, sr)
            return StemResult(
                vocals_path=vocals_path,
                instrumental_path=inst_path,
                mode=mode,
                sample_rate=sr,
                duration_s=duration,
                engine="bs_roformer" if mode in ("neural", "bs_roformer") else mode,
            )

        if mode in ("neural", "bs_roformer"):
            # Try state-of-the-art BS-RoFormer first (specialized in complex & hyperpop mixes)
            try:
                res = self._separate_bs_roformer(
                    input_path,
                    vocals_path,
                    inst_path,
                    raw_vocals_path=raw_vocals_path,
                    raw_inst_path=raw_inst_path,
                    progress_callback=progress_callback,
                    blend_weight=bs_roformer_weight,
                    vocal_flags=v_set,
                    inst_flags=i_set,
                )
                save_stem_profile(
                    stem_dir,
                    {
                        "vocal_flags": sorted(v_set),
                        "inst_flags": sorted(i_set),
                        "vocal_profile": next(iter(v_set), "natural"),
                        "inst_profile": next(iter(i_set), "natural"),
                        "bs_roformer_weight": bs_roformer_weight,
                        "hdemucs_weight": hdemucs_weight,
                    },
                )
                return res
            except Exception as e_roformer:
                logger.warning(
                    "BS-RoFormer separation unavailable (%s); trying HDEMUCS.",
                    e_roformer,
                )

            # Fallback to HDEMUCS
            try:
                res = self._separate_neural(
                    input_path,
                    vocals_path,
                    inst_path,
                    raw_vocals_path=raw_vocals_path,
                    raw_inst_path=raw_inst_path,
                    progress_callback=progress_callback,
                    blend_weight=hdemucs_weight,
                    vocal_flags=v_set,
                    inst_flags=i_set,
                )
                save_stem_profile(
                    stem_dir,
                    {
                        "vocal_flags": sorted(v_set),
                        "inst_flags": sorted(i_set),
                        "vocal_profile": next(iter(v_set), "natural"),
                        "inst_profile": next(iter(i_set), "natural"),
                        "bs_roformer_weight": bs_roformer_weight,
                        "hdemucs_weight": hdemucs_weight,
                    },
                )
                return res
            except Exception as e_hdemucs:
                logger.error(
                    "HDEMUCS stem separation also failed (%s). Neural AI unavailable.",
                    e_hdemucs,
                )
                raise RuntimeError(
                    "Neural AI stem separation failed: both BS-RoFormer and HDEMUCS are "
                    "unavailable on this system. Install torch and torchaudio to enable AI "
                    "separation."
                ) from e_hdemucs

        eco_res = self._separate_eco(
            input_path,
            vocals_path,
            inst_path,
            progress_callback=progress_callback,
        )
        save_stem_profile(
            stem_dir,
            {
                "vocal_profile": vocal_profile,
                "inst_profile": inst_profile,
                "bs_roformer_weight": bs_roformer_weight,
                "hdemucs_weight": hdemucs_weight,
            },
        )
        return eco_res

    def _separate_eco(
        self,
        input_path: Path,
        vocals_path: Path,
        inst_path: Path,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> StemResult:
        """Eco DSP Stem Separation with adaptive gating and inversion polish."""
        if progress_callback:
            progress_callback(15.0, "Eco DSP: Phase cancellation matrixing...")

        orig_audio, sr = load_audio_numpy(input_path)
        if orig_audio.shape[0] == 1:
            orig_audio = np.repeat(orig_audio, 2, axis=0)

        n_samples = orig_audio.shape[1]
        left = orig_audio[0]
        right = orig_audio[1]

        mid = 0.5 * (left + right)

        mid_fft = np.fft.rfft(mid)
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / sr)

        gain = np.ones_like(freqs, dtype=np.float32)
        vocal_core = (freqs >= 250.0) & (freqs <= 4000.0)
        gain[vocal_core] = 0.10

        filtered_mid = np.fft.irfft(mid_fft * gain, n=n_samples).astype(np.float32)
        vocal_diff = mid - filtered_mid
        vocal_fft = np.fft.rfft(vocal_diff)
        vocal_bp = np.zeros_like(freqs, dtype=np.float32)
        vocal_bp[(freqs >= 180.0) & (freqs <= 5500.0)] = 1.0
        vocal_clean = np.fft.irfft(vocal_fft * vocal_bp, n=n_samples).astype(np.float32)
        vocals_raw = np.stack([vocal_clean, vocal_clean], axis=0)

        if progress_callback:
            progress_callback(55.0, "Eco DSP: Adaptive spectral gating...")
        vocals_gated = apply_adaptive_spectral_gate(vocals_raw, sr)

        if progress_callback:
            progress_callback(80.0, "Eco DSP: Inversion subtraction polish...")
        inst_polished = apply_inversion_subtraction(orig_audio, vocals_gated, sr)

        save_audio_numpy(vocals_gated, vocals_path, sr)
        save_audio_numpy(inst_polished, inst_path, sr)

        if progress_callback:
            progress_callback(100.0, "Eco DSP stems ready.")

        duration = n_samples / max(1, sr)
        return StemResult(
            vocals_path=vocals_path,
            instrumental_path=inst_path,
            mode="eco",
            sample_rate=sr,
            duration_s=duration,
            engine="eco",
        )

    def _separate_bs_roformer(
        self,
        input_path: Path,
        vocals_path: Path,
        inst_path: Path,
        raw_vocals_path: Path | None = None,
        raw_inst_path: Path | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
        blend_weight: float = 0.70,
        vocal_flags: set[str] | list[str] | str = "natural",
        inst_flags: set[str] | list[str] | str = "natural",
        vocal_profile: str | None = None,
        inst_profile: str | None = None,
    ) -> StemResult:  # pragma: no cover
        """
        State-of-the-Art Band-Split Rotary Position Transformer (BS-RoFormer).
        Specialized in complex electronic arrangements, dense synths, and hyperpop.
        """
        import torch
        from transformers import AutoModel
        from transformers.dynamic_module_utils import get_class_from_dynamic_module

        if progress_callback:
            progress_callback(5.0, "Loading BS-RoFormer Rotary Transformer...")

        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

        # Compatibility bridge for transformers 5.x dynamic modules
        try:
            model_cls = get_class_from_dynamic_module(
                "modeling_bs_roformer.BSRoformerForMaskedEstimation",
                "HiDolen/Mini-BS-RoFormer-V2-46.8M",
            )
            model_cls.all_tied_weights_keys = {}
        except Exception:
            pass

        model = (
            AutoModel.from_pretrained(
                "HiDolen/Mini-BS-RoFormer-V2-46.8M",
                trust_remote_code=True,
            )
            .float()
            .to(device)
        )
        model.eval()

        # Re-initialize corrupted STFT buffer windows with clean float32 Hann windows
        model.stft_window = torch.hann_window(
            model.config.stft_n_fft, dtype=torch.float32, device=device
        )
        model.stft_out_window = torch.hann_window(
            model.config.stft_n_fft_out, dtype=torch.float32, device=device
        )

        target_sr = getattr(model.config, "wave_sample_rate", 44100)
        orig_audio, sr = load_audio_numpy(input_path, target_sr=target_sr)
        waveform = torch.from_numpy(orig_audio).float().to(device)
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        total_samples = waveform.shape[1]
        chunk_len = getattr(model.config, "wave_chunk_size", 352800)
        # 50% overlap-add: guaranteed flat partition of unity (sum of Hann == 1.0)
        hop_len = chunk_len // 2

        if progress_callback:
            progress_callback(12.0, "BS-RoFormer: Multi-band attention vocal extraction...")

        if total_samples < chunk_len:
            pad_len = chunk_len - total_samples
            padded_wave = torch.nn.functional.pad(waveform, (0, pad_len))
        else:
            rem = (total_samples - chunk_len) % hop_len
            pad_len = (hop_len - rem) if rem != 0 else 0
            padded_wave = torch.nn.functional.pad(waveform, (0, pad_len + chunk_len))

        padded_len = padded_wave.shape[1]
        output = torch.zeros(4, 2, padded_len, device=device)
        weight = torch.zeros(padded_len, device=device)
        window = torch.hann_window(chunk_len, device=device)

        starts = list(range(0, padded_len - chunk_len + 1, hop_len))
        n_chunks = len(starts)

        with torch.no_grad():
            for idx, start in enumerate(starts):
                end = start + chunk_len
                chunk = padded_wave[:, start:end].unsqueeze(0)
                srcs = model(raw_audio=chunk).squeeze(0)

                output[:, :, start:end] += srcs * window
                weight[start:end] += window

                if progress_callback:
                    pct = 12.0 + 58.0 * ((idx + 1) / max(1, n_chunks))
                    progress_callback(
                        pct,
                        f"BS-RoFormer: Processing chunk {idx + 1}/{n_chunks}...",
                    )

        weight_safe = torch.clamp(weight, min=1e-6)
        output = (output / weight_safe)[:, :, :total_samples].cpu().numpy()

        # Stem mapping: 0=bass, 1=drums, 2=other, 3=vocals
        drums = output[1]
        bass = output[0]
        other = output[2]
        vocals_raw = output[3]
        inst_model = drums + bass + other
        del model, padded_wave, waveform, weight, weight_safe, output
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except Exception:
                pass
        import gc

        gc.collect()

        # Cache raw neural outputs for instant re-processing if user picks another profile later
        if raw_vocals_path:
            save_audio_numpy(vocals_raw, raw_vocals_path, sr)
        if raw_inst_path:
            save_audio_numpy(inst_model, raw_inst_path, sr)

        vocals_clean, inst_final = postprocess_stems(
            orig_audio,
            vocals_raw,
            inst_model,
            sr,
            blend_weight=blend_weight,
            vocal_flags=vocal_flags,
            inst_flags=inst_flags,
            vocal_profile=vocal_profile,
            inst_profile=inst_profile,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(97.0, "Writing isolated stems to disk...")
        save_audio_numpy(vocals_clean, vocals_path, sr)
        save_audio_numpy(inst_final, inst_path, sr)

        if progress_callback:
            progress_callback(100.0, "Stems ready: Vocals & Instrumental (BS-RoFormer)!")

        duration = total_samples / max(1, sr)
        return StemResult(
            vocals_path=vocals_path,
            instrumental_path=inst_path,
            mode="bs_roformer",
            sample_rate=sr,
            duration_s=duration,
            engine="bs_roformer",
        )

    def _separate_neural(
        self,
        input_path: Path,
        vocals_path: Path,
        inst_path: Path,
        raw_vocals_path: Path | None = None,
        raw_inst_path: Path | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
        blend_weight: float = 0.50,
        vocal_flags: set[str] | list[str] | str = "natural",
        inst_flags: set[str] | list[str] | str = "natural",
        vocal_profile: str | None = None,
        inst_profile: str | None = None,
    ) -> StemResult:  # pragma: no cover
        """
        Multi-Stage Neural AI Pipeline:
        1. HDEMUCS Source Separation (Chunked Hann-crossfading)
        2. Adaptive Spectral Noise Gating (VAD + sibilance de-bleed)
        3. Vocal Harmonic Polish (Phase de-robotizing)
        4. Instrumental Inversion Subtraction (Bit-exact acoustic backing)
        """
        import torch
        import torchaudio

        if progress_callback:
            progress_callback(5.0, "Loading Neural HDEMUCS AI Model...")

        device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        bundle = torchaudio.pipelines.HDEMUCS_HIGH_MUSDB
        model = bundle.get_model().to(device)
        model.eval()

        orig_audio, sr = load_audio_numpy(input_path, target_sr=bundle.sample_rate)
        waveform = torch.from_numpy(orig_audio)
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        total_samples = waveform.shape[1]
        chunk_len = int(10 * sr)
        hop_len = int(5 * sr)

        # Stage 1: Chunked Neural Inference
        if progress_callback:
            progress_callback(10.0, "Neural AI: Separating vocal and musical layers...")

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

            n_chunks = len(range(0, total_samples, hop_len))
            chunk_idx = 0

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

                chunk_idx += 1
                if progress_callback:
                    pct = 10.0 + 40.0 * (chunk_idx / max(1, n_chunks))
                    progress_callback(pct, f"Neural AI: Processing chunk {chunk_idx}/{n_chunks}...")

            weight[weight == 0] = 1.0
            output = output / weight

        vocals_raw = output[3].numpy()
        # Reconstruct HDEMUCS instrumental from the three non-vocal stems
        inst_model_np = (
            output[0].numpy() + output[1].numpy() + output[2].numpy()
        )  # bass+drums+other
        del model, waveform, output
        if "weight" in locals():
            del weight
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except Exception:
                pass
        import gc

        gc.collect()

        # Cache raw neural outputs for instant re-processing if user picks another profile later
        if raw_vocals_path:
            save_audio_numpy(vocals_raw, raw_vocals_path, sr)
        if raw_inst_path:
            save_audio_numpy(inst_model_np, raw_inst_path, sr)

        vocals_polished, inst_blended = postprocess_stems(
            orig_audio,
            vocals_raw,
            inst_model_np,
            sr,
            blend_weight=blend_weight,
            vocal_flags=vocal_flags,
            inst_flags=inst_flags,
            vocal_profile=vocal_profile,
            inst_profile=inst_profile,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(97.0, "Writing isolated stems to disk...")
        save_audio_numpy(vocals_polished, vocals_path, sr)
        save_audio_numpy(inst_blended, inst_path, sr)

        if progress_callback:
            progress_callback(100.0, "Stems ready: Vocals & Instrumental!")

        duration = total_samples / max(1, sr)
        return StemResult(
            vocals_path=vocals_path,
            instrumental_path=inst_path,
            mode="neural",
            sample_rate=sr,
            duration_s=duration,
            engine="hdemucs",
        )
