"""
Target Frequency Curves & Spectrum Deviation Engine for OmniRip.

Calculates 1/3-octave smoothed audio spectrums and compares them against
standard acoustic reference curves: Harman Target, Diffuse Field, and JM-1.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

# Standard ISO 266 1/3-Octave Nominal Center Frequencies (Hz) from 20 Hz to 20 kHz
TARGET_FREQUENCIES: tuple[float, ...] = (
    20.0, 25.0, 31.5, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0, 160.0,
    200.0, 250.0, 315.0, 400.0, 500.0, 630.0, 800.0, 1000.0, 1250.0, 1600.0,
    2000.0, 2500.0, 3150.0, 4000.0, 5000.0, 6300.0, 8000.0, 10000.0, 12500.0, 16000.0,
    20000.0,
)

TargetType = Literal["harman", "diffuse_field", "jm1", "flat"]


def harman_target() -> dict[float, float]:
    """Harman Target Reference Curve: Consumer & streaming standard with sub-bass shelf and pinna gain."""
    curve: dict[float, float] = {}
    for f in TARGET_FREQUENCIES:
        val = 0.0
        # Sub-bass shelf: +5.5 dB at 20 Hz descending to 0 dB at 160 Hz
        if f <= 160.0:
            val += 5.5 * (1.0 - (np.log10(f) - np.log10(20.0)) / (np.log10(160.0) - np.log10(20.0)))
        # Pinna ear canal resonance bump peaking around 3.15 kHz
        pinna_dist = np.log10(f / 3150.0)
        val += 2.8 * np.exp(-0.5 * (pinna_dist / 0.18) ** 2)
        # Treble downward tilt above 8 kHz
        if f > 8000.0:
            val -= 1.0 * (np.log2(f / 8000.0))
        curve[f] = round(float(val), 2)
    # Normalize 1 kHz to 0.0 dB
    offset = curve[1000.0]
    return {f: round(v - offset, 2) for f, v in curve.items()}


def diffuse_field_target() -> dict[float, float]:
    """Diffuse Field Target: Classical studio acoustic sound power reference."""
    curve: dict[float, float] = {}
    for f in TARGET_FREQUENCIES:
        val = 0.0
        # Flat bass response up to 250 Hz (0 dB)
        # Upper-mid ear canal diffuse bump peaking at 2.5–3 kHz
        pinna_dist = np.log10(f / 2800.0)
        val += 3.5 * np.exp(-0.5 * (pinna_dist / 0.22) ** 2)
        # Secondary air presence rise around 9 kHz
        air_dist = np.log10(f / 9000.0)
        val += 2.0 * np.exp(-0.5 * (air_dist / 0.16) ** 2)
        # Roll-off above 16 kHz
        if f > 16000.0:
            val -= 2.5 * (np.log2(f / 16000.0))
        curve[f] = round(float(val), 2)
    offset = curve[1000.0]
    return {f: round(v - offset, 2) for f, v in curve.items()}


def jm1_target() -> dict[float, float]:
    """JM-1 Modern Target: Fatigue-free mastering curve with controlled sub-bass and tamed pinna."""
    curve: dict[float, float] = {}
    for f in TARGET_FREQUENCIES:
        val = 0.0
        # Controlled sub-bass shelf (+2.2 dB at 20 Hz descending to 0 dB at 80 Hz)
        if f <= 80.0:
            val += 2.2 * (1.0 - (np.log10(f) - np.log10(20.0)) / (np.log10(80.0) - np.log10(20.0)))
        # Smoothed, fatigue-free pinna gain (+1.8 dB at 3 kHz)
        pinna_dist = np.log10(f / 3000.0)
        val += 1.8 * np.exp(-0.5 * (pinna_dist / 0.25) ** 2)
        # Ultra-smooth treble roll-off
        if f > 10000.0:
            val -= 1.2 * (np.log2(f / 10000.0))
        curve[f] = round(float(val), 2)
    offset = curve[1000.0]
    return {f: round(v - offset, 2) for f, v in curve.items()}


def flat_target() -> dict[float, float]:
    """Flat 0 dB reference curve."""
    return {f: 0.0 for f in TARGET_FREQUENCIES}


def get_target_curve(target_type: TargetType) -> dict[float, float]:
    """Resolve target curve by name."""
    if target_type == "harman":
        return harman_target()
    if target_type == "diffuse_field":
        return diffuse_field_target()
    if target_type == "jm1":
        return jm1_target()
    return flat_target()


def calculate_smoothed_spectrum(
    audio: np.ndarray,
    sr: int,
    n_fft: int = 4096,
) -> dict[float, float]:
    """
    Calculate 1/3-octave smoothed frequency spectrum (in relative dB) from audio.

    Args:
        audio: 1D (mono) or 2D (stereo: [channels, samples]) audio array.
        sr: Sample rate in Hz.
        n_fft: FFT window size.

    Returns:
        dict mapping each ISO 1/3-octave frequency to relative dB (normalized to 1 kHz).
    """
    if audio.ndim == 2:
        # Average channels to mono
        mono = np.mean(audio, axis=0)
    else:
        mono = audio

    if len(mono) == 0:
        return {f: 0.0 for f in TARGET_FREQUENCIES}

    # Use windowed FFT blocks to compute average power spectrum
    hop = n_fft // 2
    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)

    power_sum = np.zeros(len(freqs), dtype=np.float64)
    count = 0

    for start in range(0, len(mono) - n_fft + 1, hop):
        segment = mono[start : start + n_fft] * window
        fft_vals = np.fft.rfft(segment)
        power_sum += np.abs(fft_vals) ** 2
        count += 1

    if count == 0:
        # Signal shorter than n_fft: zero-pad
        padded = np.pad(mono, (0, max(0, n_fft - len(mono))))[:n_fft] * window
        power_sum = np.abs(np.fft.rfft(padded)) ** 2
        count = 1

    avg_power = power_sum / count

    # Integrate power into 1/3-octave fractional bands:
    # Lower band edge = f * 2^(-1/6), Upper band edge = f * 2^(1/6)
    band_powers: dict[float, float] = {}
    factor = 2.0 ** (1.0 / 6.0)

    for f in TARGET_FREQUENCIES:
        f_low = f / factor
        f_high = f * factor
        indices = np.where((freqs >= f_low) & (freqs <= f_high))[0]
        if len(indices) > 0:
            band_energy = float(np.sum(avg_power[indices]))
        else:
            # Interpolate nearest
            idx = int(np.argmin(np.abs(freqs - f)))
            band_energy = float(avg_power[idx])
        band_powers[f] = max(1e-12, band_energy)

    # Convert to dB
    band_db = {f: 10.0 * np.log10(p) for f, p in band_powers.items()}

    # Normalize relative to 1000 Hz (or mean of 500-2000 Hz)
    mid_ref = (band_db.get(800.0, 0.0) + band_db.get(1000.0, 0.0) + band_db.get(1250.0, 0.0)) / 3.0
    normalized_db = {f: round(float(val - mid_ref), 1) for f, val in band_db.items()}

    # Clamp extremes to sensible visualization range (-24 dB to +18 dB)
    return {f: max(-24.0, min(18.0, val)) for f, val in normalized_db.items()}


def calculate_deviation_delta(
    spectrum: dict[float, float],
    target: dict[float, float],
) -> dict[float, float]:
    """Calculate the deviation (delta in dB) of a spectrum relative to a target curve."""
    return {
        f: round(spectrum.get(f, 0.0) - target.get(f, 0.0), 1)
        for f in TARGET_FREQUENCIES
    }
