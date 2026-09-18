"""Tests for DSP engine (Milestone 10-B)."""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.dsp import (
    apply_limiter,
    apply_progressive_mono,
    ensure_2d_audio,
    match_spectral_slope,
    recombine_audio,
    split_bands,
)


def test_ensure_2d_audio():
    """Verify 1D and 2D conversions."""
    mono = np.zeros(100, dtype=np.float32)
    res, was_1d = ensure_2d_audio(mono)
    assert was_1d
    assert res.shape == (1, 100)

    stereo = np.zeros((2, 100), dtype=np.float32)
    res_s, was_1d_s = ensure_2d_audio(stereo)
    assert not was_1d_s
    assert res_s.shape == (2, 100)

    # Transposed stereo (samples, channels)
    transposed = np.zeros((100, 2), dtype=np.float32)
    res_t, was_1d_t = ensure_2d_audio(transposed)
    assert not was_1d_t
    assert res_t.shape == (2, 100)


def test_split_bands_reconstruction_flatness():
    """Verify complementary band splitting sums to original signal."""
    sr = 48000
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Test sweep signal
    signal = np.sin(2 * np.pi * 1000 * t) + 0.5 * np.sin(2 * np.pi * 18000 * t)
    signal = signal.astype(np.float32)

    cutoff = 15000.0
    low, high = split_bands(signal, cutoff_hz=cutoff, sample_rate=sr)

    reconstructed = low + high
    max_diff = np.max(np.abs(signal - reconstructed))
    # Frequency domain complementary filters should reconstruct with < 1e-4 error
    assert max_diff < 1e-4

    # Verify high band has negligible low frequencies
    low_fft = np.abs(np.fft.rfft(low))
    high_fft = np.abs(np.fft.rfft(high))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)

    # High band at 1 kHz should be near zero
    idx_1k = np.argmin(np.abs(freqs - 1000))
    assert high_fft[idx_1k] < 0.05 * low_fft[idx_1k]


def test_apply_progressive_mono():
    """Verify sub-100Hz is mono and >250Hz preserves stereo."""
    sr = 48000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Construct out-of-phase low bass (80 Hz) and in-phase high treble (1000 Hz)
    left = np.sin(2 * np.pi * 80 * t) + np.sin(2 * np.pi * 1000 * t)
    right = -np.sin(2 * np.pi * 80 * t) + 0.5 * np.sin(2 * np.pi * 1000 * t)
    stereo_in = np.stack([left, right], axis=0).astype(np.float32)

    processed = apply_progressive_mono(
        stereo_in, sample_rate=sr, low_cut_hz=100.0, high_cut_hz=250.0
    )

    # Sub-bass: side channel (L - R) at 80 Hz should be 0
    p_left, p_right = processed[0], processed[1]
    side = 0.5 * (p_left - p_right)
    side_fft = np.abs(np.fft.rfft(side))
    freqs = np.fft.rfftfreq(len(t), 1.0 / sr)

    idx_80 = np.argmin(np.abs(freqs - 80))
    idx_1k = np.argmin(np.abs(freqs - 1000))

    # At 80 Hz, side must be completely eliminated
    assert side_fft[idx_80] < 1e-3

    # At 1000 Hz, side energy should match original side energy
    orig_side = 0.5 * (left - right)
    orig_side_fft = np.abs(np.fft.rfft(orig_side))
    assert np.isclose(side_fft[idx_1k], orig_side_fft[idx_1k], rtol=1e-3)


def test_match_spectral_slope():
    """Verify residual energy is scaled to match reference band decay."""
    sr = 48000
    n = 48000
    # Reference band (7.5k to 15k) has moderate energy
    source = np.random.normal(0, 0.1, n).astype(np.float32)
    # Residual band has huge artificial energy
    hot_residual = np.random.normal(0, 2.0, n).astype(np.float32)

    scaled = match_spectral_slope(source, hot_residual, cutoff_hz=15000.0, sample_rate=sr)
    # The scaled residual must be attenuated
    assert np.std(scaled) < np.std(hot_residual)


def test_apply_limiter():
    """Verify peak limiter confines signal to ceiling."""
    hot_audio = np.array([0.5, 1.5, -2.0, 0.8], dtype=np.float32)
    limited = apply_limiter(hot_audio, ceiling_dbfs=-0.1)

    ceiling_linear = 10.0 ** (-0.1 / 20.0)
    assert np.max(np.abs(limited)) <= ceiling_linear + 1e-5


def test_recombine_audio():
    """Verify safe recombination of bands."""
    low = np.ones((2, 1000), dtype=np.float32) * 0.4
    high = np.ones((2, 1000), dtype=np.float32) * 0.3

    out = recombine_audio(low, high)
    assert out.shape == (2, 1000)
    assert np.allclose(out, 0.7, atol=1e-2)
