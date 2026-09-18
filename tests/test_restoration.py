from __future__ import annotations

import numpy as np
import pytest

from harvester.analysis.restoration import (
    RestorationConfig,
    correlation_interlock,
    measure_metrics,
    restore,
)

_FS = 48_000


def _stereo_fixture(*, correlation: float = 0.95) -> np.ndarray:
    time = np.arange(_FS, dtype=np.float64) / _FS
    left = 0.35 * np.sin(2 * np.pi * 220 * time) + 0.08 * np.sin(2 * np.pi * 8_000 * time)
    independent = 0.35 * np.sin(2 * np.pi * 311 * time + 0.7)
    right = correlation * left + np.sqrt(1.0 - correlation**2) * independent
    return np.column_stack((left, right)).astype(np.float32)


def test_transient_and_peak_bounds_are_deterministic() -> None:
    source = np.zeros(4_096, dtype=np.float32)
    source[100] = 1.4
    source[101] = -1.1
    config = RestorationConfig(
        transient_gain=0.25,
        max_transient_gain=0.25,
        peak_limit=0.8,
        crest_limit=12.0,
    )

    first = restore(source, _FS, config=config)
    second = restore(source, _FS, config=config)

    assert first.metrics.peak <= config.peak_limit + 1e-7
    assert first.metrics.crest_factor <= config.crest_limit + 1e-5
    assert np.array_equal(first.audio, second.audio)
    assert first.synthetic_high_band is False
    assert first.provenance["synthetic_high_band"] == "false"


def test_low_frequency_compatibility_blends_side_without_hard_sum() -> None:
    time = np.arange(_FS, dtype=np.float64) / _FS
    low_left = 0.25 * np.sin(2 * np.pi * 60 * time)
    low_right = 0.15 * np.sin(2 * np.pi * 60 * time + 0.2)
    source = np.column_stack((low_left, low_right)).astype(np.float32)
    result = restore(
        source,
        _FS,
        config=RestorationConfig(transient_gain=0.0, mono_compatibility=0.8),
    )

    before_side = np.linalg.norm(source[:, 0] - source[:, 1])
    after_side = np.linalg.norm(result.audio[:, 0] - result.audio[:, 1])
    after_sum = np.linalg.norm(result.audio[:, 0] + result.audio[:, 1])
    assert after_side < before_side
    assert after_sum > 0.0


def test_input_is_not_mutated_and_validation_is_explicit() -> None:
    source = _stereo_fixture()
    original = source.copy()
    restore(source, _FS)
    assert np.array_equal(source, original)

    with pytest.raises(ValueError, match="sample_rate"):
        restore(source, 0.0)
    with pytest.raises(ValueError, match="finite"):
        restore(np.array([np.nan], dtype=np.float32), _FS)
    with pytest.raises(ValueError, match="silent"):
        restore(np.zeros(8, dtype=np.float32), _FS)
    with pytest.raises(TypeError, match="float32 or float64"):
        restore(np.ones(8, dtype=np.int16), _FS)


def test_metrics_report_expected_mono_and_stereo_values() -> None:
    mono = np.array([0.5, -0.5, 0.5, -0.5], dtype=np.float32)
    metrics = measure_metrics(mono)
    assert metrics.peak == pytest.approx(0.5)
    assert metrics.rms == pytest.approx(0.5)
    assert metrics.crest_factor == pytest.approx(1.0)
    assert metrics.stereo_correlation == pytest.approx(1.0)
    assert metrics.clipping is False

    stereo = np.column_stack((mono, -mono))
    assert measure_metrics(stereo).stereo_correlation == pytest.approx(-1.0)


def test_correlation_interlock_tapers_side_gain() -> None:
    assert correlation_interlock(0.1) == pytest.approx(0.0)
    assert correlation_interlock(0.95) == pytest.approx(1.0)
    assert 0.0 < correlation_interlock(0.5) < 1.0

    config = RestorationConfig(
        transient_gain=0.0,
        decorrelate_high_band=True,
        decorrelation_amount=1.0,
        high_band_hz=2_000.0,
    )
    high_corr = restore(_stereo_fixture(correlation=0.95), _FS, config=config)
    low_corr = restore(_stereo_fixture(correlation=0.1), _FS, config=config)
    assert low_corr.metrics.stereo_correlation > low_corr.input_metrics.stereo_correlation
    assert high_corr.provenance["operations"].endswith("opt_in_high_band_decorrelation")
