"""Tests for 10-Band Studio Equalizer (Milestone 10-EQ)."""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.eq import (
    EQ_FREQUENCIES,
    MasteringEQSettings,
    apply_mastering_eq,
)


def test_eq_settings_defaults_and_presets():
    """Verify default settings and preset switching."""
    settings = MasteringEQSettings()
    assert settings.enabled is True
    assert settings.hpf_30hz is False
    assert settings.output_trim_db == 0.0
    assert settings.preset_name == "Flat"
    for f in EQ_FREQUENCIES:
        assert settings.bands[f] == 0.0

    settings.apply_preset("Club Punch")
    assert settings.preset_name == "Club Punch"
    assert settings.bands[63] == 4.0

    settings.set_band(1000, 5.0)
    assert settings.bands[1000] == 5.0
    assert settings.preset_name == "Custom"

    # Clamping
    settings.set_band(1000, 20.0)
    assert settings.bands[1000] == 12.0
    settings.set_band(1000, -25.0)
    assert settings.bands[1000] == -12.0

    settings.reset_flat()
    assert settings.preset_name == "Flat"
    assert settings.bands[1000] == 0.0


def test_apply_mastering_eq_flat_identity():
    """Verify that flat EQ is a transparent near-identity."""
    sr = 48000
    n = 48000
    t = np.linspace(0, 1.0, n, endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    audio = np.stack([signal, signal], axis=0)

    settings = MasteringEQSettings()
    out = apply_mastering_eq(audio, settings, sample_rate=sr)
    assert out.shape == audio.shape
    # Maximum difference should be negligibly small
    assert np.max(np.abs(out - audio)) < 1e-4


def test_apply_mastering_eq_treble_boost():
    """Verify that boosting 8kHz and 16kHz increases high frequency energy."""
    sr = 48000
    n = 48000
    np.random.seed(42)
    white_noise = np.random.normal(0, 0.1, (2, n)).astype(np.float32)

    settings = MasteringEQSettings()
    settings.set_band(8000, 6.0)
    settings.set_band(16000, 8.0)

    out = apply_mastering_eq(white_noise, settings, sample_rate=sr)

    # Calculate high-frequency energy (> 6000 Hz)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    high_mask = freqs > 6000.0

    orig_energy = np.sum(np.abs(np.fft.rfft(white_noise[0]))[high_mask] ** 2)
    boosted_energy = np.sum(np.abs(np.fft.rfft(out[0]))[high_mask] ** 2)

    assert boosted_energy > orig_energy * 2.0


def test_apply_mastering_eq_hpf_30hz():
    """Verify that 30Hz HPF effectively cuts sub-rumble below 30Hz."""
    sr = 48000
    n = 48000
    t = np.linspace(0, 1.0, n, endpoint=False)
    # Signal with 15 Hz rumble and 1000 Hz tone
    rumble = 0.4 * np.sin(2 * np.pi * 15 * t).astype(np.float32)
    tone = 0.4 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    audio = np.stack([rumble + tone, rumble + tone], axis=0)

    settings = MasteringEQSettings(hpf_30hz=True)
    out = apply_mastering_eq(audio, settings, sample_rate=sr)

    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    rumble_idx = np.argmin(np.abs(freqs - 15.0))
    tone_idx = np.argmin(np.abs(freqs - 1000.0))

    spec_orig = np.abs(np.fft.rfft(audio[0]))
    spec_out = np.abs(np.fft.rfft(out[0]))

    # Rumble attenuated by at least 10 dB
    assert spec_out[rumble_idx] < spec_orig[rumble_idx] * 0.35
    # 1000 Hz tone untouched
    assert np.isclose(spec_out[tone_idx], spec_orig[tone_idx], rtol=0.05)


def test_apply_mastering_eq_limiter_guard():
    """Verify that extreme boosts do not exceed ceiling_dbfs."""
    sr = 48000
    n = 24000
    # High amplitude signal near 0 dBFS
    t = np.linspace(0, 0.5, n, endpoint=False)
    audio = 0.9 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)

    settings = MasteringEQSettings()
    # Extreme boost
    for f in EQ_FREQUENCIES:
        settings.set_band(f, 12.0)
    settings.output_trim_db = 6.0

    ceiling_dbfs = -0.2
    ceiling_linear = 10.0 ** (ceiling_dbfs / 20.0)

    out = apply_mastering_eq(audio, settings, sample_rate=sr, ceiling_dbfs=ceiling_dbfs)
    assert np.max(np.abs(out)) <= ceiling_linear + 1e-4
