"""Unit tests for Target Frequency Curves and 1/3-octave Spectrum Analysis."""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.target_curves import (
    TARGET_FREQUENCIES,
    calculate_deviation_delta,
    calculate_smoothed_spectrum,
    diffuse_field_target,
    flat_target,
    get_target_curve,
    harman_target,
    jm1_target,
)

SR = 44100


def test_target_curves_completeness_and_frequency_bins():
    assert len(TARGET_FREQUENCIES) == 31
    for curve in (harman_target(), diffuse_field_target(), jm1_target(), flat_target()):
        assert len(curve) == 31
        for f in TARGET_FREQUENCIES:
            assert f in curve
            assert isinstance(curve[f], float)
            assert np.isfinite(curve[f])
        # 1 kHz is the 0 dB reference
        assert abs(curve[1000.0]) <= 0.05


def test_target_curves_acoustic_profiles():
    harman = harman_target()
    # Harman has heavy sub-bass boost (<100Hz) and pinna peak at 3.15kHz
    assert harman[20.0] > 4.0
    assert harman[3150.0] > 2.0
    assert harman[16000.0] < 0.0

    df = diffuse_field_target()
    # Diffuse Field has uncolored bass (close to 0dB at 50Hz) and upper mid peak
    assert abs(df[50.0]) < 1.0
    assert df[2500.0] > 2.0

    jm1 = jm1_target()
    # JM-1 has moderate sub-bass (~2dB) and tamed pinna
    assert 1.5 < jm1[20.0] < 3.0
    assert 1.0 < jm1[3150.0] < 2.5


def test_calculate_smoothed_spectrum_on_synthetic_signal():
    # 1-second stereo signal: 60 Hz (strong bass) + 1000 Hz (mid) + 10000 Hz (high)
    t = np.linspace(0, 1.0, SR, endpoint=False, dtype=np.float32)
    sig = 0.5 * np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 1000 * t) + 0.1 * np.sin(2 * np.pi * 10000 * t)
    audio = np.stack([sig, sig], axis=0)

    spectrum = calculate_smoothed_spectrum(audio, SR)
    assert len(spectrum) == 31
    for _f, val in spectrum.items():
        assert np.isfinite(val)
        assert -24.0 <= val <= 18.0

    # 60 Hz should have higher energy than 400 Hz
    assert spectrum[63.0] > spectrum[400.0]


def test_calculate_deviation_delta():
    spectrum = {f: 2.0 for f in TARGET_FREQUENCIES}
    target = {f: 1.0 for f in TARGET_FREQUENCIES}
    delta = calculate_deviation_delta(spectrum, target)
    for f in TARGET_FREQUENCIES:
        assert delta[f] == 1.0


def test_get_target_curve_resolver():
    assert get_target_curve("harman") == harman_target()
    assert get_target_curve("diffuse_field") == diffuse_field_target()
    assert get_target_curve("jm1") == jm1_target()
    assert get_target_curve("flat") == flat_target()
