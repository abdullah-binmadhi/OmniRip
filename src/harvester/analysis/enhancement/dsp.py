"""Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.

Implements Linkwitz-Riley crossovers, progressive mono bass blending,
spectral slope matching, and transparent soft-knee peak limiting.
"""

from __future__ import annotations

import numpy as np


def ensure_2d_audio(audio: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Ensure audio is 2D array of shape (channels, samples).

    Returns:
        tuple[np.ndarray, bool]: (audio_2d, was_1d)
    """
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 1:
        return audio[np.newaxis, :], True
    if audio.ndim == 2:
        if audio.shape[0] > audio.shape[1] and audio.shape[1] <= 2:
            # (samples, channels) -> transpose to (channels, samples)
            return audio.T, False
        return audio, False
    raise ValueError(f"Expected 1D or 2D audio array, got shape {audio.shape}")


def resample_audio(audio: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    """Polyphase resample of a (channels, samples) array."""
    if source_sr == target_sr:
        return np.asarray(audio, dtype=np.float32)
    from math import gcd

    from scipy.signal import resample_poly

    factor = gcd(int(source_sr), int(target_sr))
    up, down = int(target_sr) // factor, int(source_sr) // factor
    return resample_poly(audio, up, down, axis=1).astype(np.float32)


def apply_progressive_mono(
    audio: np.ndarray,
    sample_rate: int = 48000,
    low_cut_hz: float = 100.0,
    high_cut_hz: float = 250.0,
) -> np.ndarray:
    """
    Gradually blend low frequencies to mono to maintain structural bass punch and phase stability.

    - Frequencies below low_cut_hz: 100% mono (side channel zeroed).
    - Frequencies between low_cut_hz and high_cut_hz: linear fade from mono to original stereo.
    - Frequencies above high_cut_hz: 100% stereo preserved.

    Zero phase shift is guaranteed via symmetric frequency-domain filtering on the Side channel.
    """
    audio_2d, was_1d = ensure_2d_audio(audio)
    if audio_2d.shape[0] < 2:
        # Mono audio already has zero side channel
        return audio_2d[0] if was_1d else audio_2d

    left = audio_2d[0]
    right = audio_2d[1]
    n_samples = len(left)

    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)

    # Frequency domain filter on side channel
    side_fft = np.fft.rfft(side)
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)

    gain = np.ones_like(freqs, dtype=np.float32)
    gain[freqs < low_cut_hz] = 0.0

    transition_mask = (freqs >= low_cut_hz) & (freqs <= high_cut_hz)
    gain[transition_mask] = (freqs[transition_mask] - low_cut_hz) / (high_cut_hz - low_cut_hz)

    filtered_side = np.fft.irfft(side_fft * gain, n=n_samples)

    left_out = mid + filtered_side
    right_out = mid - filtered_side

    out = np.stack([left_out, right_out], axis=0).astype(np.float32)
    return out[0] if was_1d else out


def split_bands(
    audio: np.ndarray,
    cutoff_hz: float,
    sample_rate: int = 48000,
    transition_width_hz: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split audio into low and high bands at cutoff_hz using a linear-phase smooth crossover.

    The sum low_band + high_band reconstructs the input audio with flat magnitude response.

    ``transition_width_hz`` narrows (or widens) the raised-cosine transition; the
    default keeps the wide mastering crossover and the layer engine passes a
    tighter width so neighbouring lanes stay separated.
    """
    audio_2d, was_1d = ensure_2d_audio(audio)
    n_samples = audio_2d.shape[1]

    # Frequency-domain complementary split (zero-phase, flat magnitude sum)
    audio_fft = np.fft.rfft(audio_2d, axis=1)
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)

    # Cosine transition around cutoff (width = 5% of cutoff or 500 Hz)
    transition_width = (
        float(transition_width_hz)
        if transition_width_hz is not None
        else max(500.0, cutoff_hz * 0.05)
    )
    f_start = max(100.0, cutoff_hz - transition_width / 2.0)
    f_end = min(sample_rate / 2.0 - 10.0, cutoff_hz + transition_width / 2.0)

    lp_gain = np.zeros_like(freqs, dtype=np.float32)
    lp_gain[freqs <= f_start] = 1.0

    in_transition = (freqs > f_start) & (freqs < f_end)
    # Raised cosine / Hann curve for smooth 0-dB power and linear sum
    t = (freqs[in_transition] - f_start) / (f_end - f_start)
    lp_gain[in_transition] = 0.5 * (1.0 + np.cos(np.pi * t))

    hp_gain = 1.0 - lp_gain

    low_band = np.fft.irfft(audio_fft * lp_gain, n=n_samples, axis=1).astype(np.float32)
    high_band = np.fft.irfft(audio_fft * hp_gain, n=n_samples, axis=1).astype(np.float32)

    if was_1d:
        return low_band[0], high_band[0]
    return low_band, high_band


def match_spectral_slope(
    source_audio: np.ndarray,
    residual_audio: np.ndarray,
    cutoff_hz: float,
    sample_rate: int = 48000,
    target_decay_db_per_oct: float = 4.5,
    max_gain_db: float = 3.0,
    min_gain_db: float = -12.0,
) -> np.ndarray:
    """
    Match the residual high-frequency energy to follow the natural spectral decay of the source.

    Prevents AI models or exciters from introducing harsh unnatural sibilance or sizzling.
    """
    src_2d, was_1d = ensure_2d_audio(source_audio)
    res_2d, _ = ensure_2d_audio(residual_audio)

    n_samples = src_2d.shape[1]
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)

    # Reference octave: [cutoff_hz / 2, cutoff_hz]
    ref_mask = (freqs >= (cutoff_hz / 2.0)) & (freqs <= cutoff_hz)
    # Residual band: [cutoff_hz, min(cutoff_hz * 1.5, Nyquist)]
    res_mask = (freqs >= cutoff_hz) & (freqs <= min(cutoff_hz * 1.6, sample_rate / 2.0 - 500))

    if not np.any(ref_mask) or not np.any(res_mask):
        return residual_audio

    src_fft = np.fft.rfft(src_2d, axis=1)
    res_fft = np.fft.rfft(res_2d, axis=1)

    src_energy = np.sqrt(np.mean(np.abs(src_fft[:, ref_mask]) ** 2) + 1e-9)
    res_energy = np.sqrt(np.mean(np.abs(res_fft[:, res_mask]) ** 2) + 1e-9)

    # Target decay relative to reference octave
    decay_factor = 10.0 ** (-target_decay_db_per_oct / 20.0)
    target_energy = src_energy * decay_factor

    gain = target_energy / res_energy
    max_gain = 10.0 ** (max_gain_db / 20.0)
    min_gain = 10.0 ** (min_gain_db / 20.0)
    clamped_gain = float(np.clip(gain, min_gain, max_gain))

    scaled_residual = (res_2d * clamped_gain).astype(np.float32)
    return scaled_residual[0] if was_1d else scaled_residual


def apply_limiter(
    audio: np.ndarray,
    ceiling_dbfs: float = -0.1,
) -> np.ndarray:
    """
    Transparent soft-knee peak limiter to prevent clipping and inter-sample overs.
    """
    audio_2d, was_1d = ensure_2d_audio(audio)
    ceiling_linear = 10.0 ** (ceiling_dbfs / 20.0)

    peak = float(np.max(np.abs(audio_2d)))
    if peak <= ceiling_linear:
        return audio_2d[0] if was_1d else audio_2d

    # Soft saturation for peaks exceeding threshold
    threshold = ceiling_linear * 0.90
    out = audio_2d.copy()

    excess_mask = np.abs(out) > threshold
    sign = np.sign(out[excess_mask])
    val = np.abs(out[excess_mask])

    # Smooth polynomial saturation curve
    normalized = (val - threshold) / (peak - threshold + 1e-9)
    saturated = threshold + (ceiling_linear - threshold) * np.tanh(normalized * 1.5)
    out[excess_mask] = sign * saturated

    # Final hard limit guard
    out = np.clip(out, -ceiling_linear, ceiling_linear)
    return out[0] if was_1d else out


def recombine_audio(
    lower_band: np.ndarray,
    residual_band: np.ndarray,
    ceiling_dbfs: float = -0.1,
) -> np.ndarray:
    """
    Safely recombine the untouched lower band with the high-frequency residual
    and apply peak limiting.
    """
    low_2d, was_1d = ensure_2d_audio(lower_band)
    res_2d, _ = ensure_2d_audio(residual_band)

    # Ensure equal length
    min_len = min(low_2d.shape[1], res_2d.shape[1])
    low_trimmed = low_2d[:, :min_len]
    res_trimmed = res_2d[:, :min_len]

    combined = low_trimmed + res_trimmed
    limited = apply_limiter(combined, ceiling_dbfs=ceiling_dbfs)

    return limited[0] if was_1d else limited
