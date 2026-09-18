"""Tests for M10-C Enhancement Providers."""

from __future__ import annotations

import numpy as np

from harvester.services.enhancement import (
    ConservativeDSPProvider,
    FlashSRProvider,
    HybridCoOpProvider,
    NVSRProvider,
)


def test_conservative_dsp_provider():
    """Verify ConservativeDSPProvider is available and generates residual above cutoff."""
    provider = ConservativeDSPProvider()
    assert provider.is_available
    assert provider.name == "Conservative DSP"

    sr = 48000
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 1 kHz + 12 kHz tone
    signal = np.sin(2 * np.pi * 1000 * t) + 0.5 * np.sin(2 * np.pi * 12000 * t)
    signal = signal.astype(np.float32)

    cutoff = 15000.0
    res = provider.generate_residual(signal, sample_rate=sr, cutoff_hz=cutoff)

    assert res.shape == signal.shape
    # Check that residual has minimal energy at 1 kHz (sub-cutoff)
    res_fft = np.abs(np.fft.rfft(res))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)
    idx_1k = np.argmin(np.abs(freqs - 1000))
    assert res_fft[idx_1k] < 0.05 * np.max(res_fft)


def test_nvsr_provider_fallback_generation():
    """Verify NVSRProvider gracefully generates high-pass residual when model weights not cached."""
    provider = NVSRProvider()
    sr = 48000
    n = 24000
    signal = np.random.normal(0, 0.2, (2, n)).astype(np.float32)

    cutoff = 15500.0
    res = provider.generate_residual(signal, sample_rate=sr, cutoff_hz=cutoff)

    assert res.shape == (2, n)
    # Energy in low band (< 10 kHz) must be negligible
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    low_mask = freqs < 10000
    res_fft = np.abs(np.fft.rfft(res[0]))
    assert np.max(res_fft[low_mask]) < 0.1 * np.max(res_fft)


def test_flashsr_provider_air_band():
    """Verify FlashSRProvider produces air-band residual (> 16 kHz)."""
    provider = FlashSRProvider()
    sr = 48000
    n = 24000
    signal = np.random.normal(0, 0.2, (2, n)).astype(np.float32)

    res = provider.generate_residual(signal, sample_rate=sr, cutoff_hz=15000.0)
    assert res.shape == (2, n)

    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    low_mask = freqs < 14000
    res_fft = np.abs(np.fft.rfft(res[0]))
    assert np.max(res_fft[low_mask]) < 0.05 * np.max(res_fft)


def test_hybrid_provider_coop():
    """Verify HybridCoOpProvider correctly merges providers."""
    hybrid = HybridCoOpProvider()
    sr = 48000
    n = 24000
    signal = np.random.normal(0, 0.2, (2, n)).astype(np.float32)

    res = hybrid.generate_residual(signal, sample_rate=sr, cutoff_hz=15000.0)
    assert res.shape == (2, n)
