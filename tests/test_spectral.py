"""Spectrally honest test fixtures and verdict assertions (docs/04 §10)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.analysis.spectral import analyze
from harvester.models import Verdict

_FS = 44_100


def _sharp_lowpass_mask(
    length: int, fs: int, cutoff: float, transition: float = 500.0
) -> np.ndarray:
    """Encoder-style brick wall: flat passband, cosine ramp, hard zero above.

    Lossy encoders terminate the spectrum: full response below the cutoff, a short
    transition, then numerically zero content above (see docs/04 \u00a710 deviation note
    for why a Butterworth lowpass cannot fake this).
    """

    frequencies = np.fft.rfftfreq(length, 1.0 / fs)
    mask = np.ones_like(frequencies)
    above = frequencies > cutoff + transition
    mask[above] = 0.0
    ramp = (frequencies - cutoff) / transition
    inside = (frequencies > cutoff) & ~above
    mask[inside] = 0.5 * (1.0 + np.cos(np.pi * np.clip(ramp[inside], 0.0, 1.0)))
    return mask


def _content(duration_s: float, fs: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    samples = int(duration_s * fs)
    noise = rng.standard_normal(samples)
    time = np.arange(samples) / fs
    tone = 0.4 * np.sin(2 * np.pi * 220 * time) + 0.2 * np.sin(2 * np.pi * 440 * time)
    return 0.5 * noise + tone


def _write(
    path: Path, data: np.ndarray, fs: int, subtype: str = "PCM_16", *, normalize: bool = True
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = np.max(np.abs(data)) or 1.0
    if normalize:
        scaled = (data / peak * 0.3).astype(np.float32)
    else:
        scaled = data.astype(np.float32)
    sf.write(path, scaled, fs, format="FLAC", subtype=subtype)
    return path


def fixture_fraud_128(path: Path) -> Path:
    signal = _content(90.0, _FS, seed=11)
    mask = _sharp_lowpass_mask(len(signal), _FS, cutoff=16_000.0)
    return _write(path, np.fft.irfft(np.fft.rfft(signal) * mask, len(signal)), _FS)


def fixture_fraud_192(path: Path) -> Path:
    signal = _content(90.0, _FS, seed=12)
    mask = _sharp_lowpass_mask(len(signal), _FS, cutoff=18_000.0)
    return _write(path, np.fft.irfft(np.fft.rfft(signal) * mask, len(signal)), _FS)


def fixture_honest_full(path: Path) -> Path:
    return _write(path, _content(90.0, _FS, seed=13), _FS)


def fixture_honest_rolloff(path: Path) -> Path:
    signal = _content(90.0, _FS, seed=14)
    frequencies = np.fft.rfftfreq(len(signal), 1.0 / _FS)
    gentle = 1.0 / (1.0 + (frequencies / 12_000.0) ** 2)
    return _write(path, np.fft.irfft(np.fft.rfft(signal) * gentle, len(signal)), _FS)


def fixture_near_silent(path: Path) -> Path:
    rng = np.random.default_rng(15)
    return _write(path, rng.standard_normal(int(30.0 * _FS)) * 1e-3, _FS, normalize=False)


def fixture_short(path: Path) -> Path:
    return _write(path, _content(5.0, _FS, seed=16), _FS)


def fixture_up96_void(path: Path) -> Path:
    signal = _content(30.0, _FS, seed=17)
    upsampled = np.fft.irfft(np.fft.rfft(signal, n=2 * len(signal)), 2 * len(signal))
    return _write(path, upsampled, _FS * 2, subtype="PCM_24")


def _read(path: Path) -> tuple[np.ndarray, int]:
    data, fs = sf.read(path, dtype="float32")
    return data.reshape(-1), int(fs)


@pytest.mark.parametrize(
    ("builder", "expected", "claimed"),
    [
        (fixture_fraud_128, Verdict.FRAUD, _FS),
        (fixture_fraud_192, Verdict.FRAUD, _FS),
        (fixture_honest_full, Verdict.PASS, _FS),
        (fixture_honest_rolloff, Verdict.PASS, _FS),
        (fixture_near_silent, Verdict.INCONCLUSIVE, _FS),
        (fixture_short, Verdict.INCONCLUSIVE, _FS),
        (fixture_up96_void, Verdict.INCONCLUSIVE, 96_000),
    ],
)
def test_fixture_verdicts(tmp_path: Path, builder, expected: Verdict, claimed: int) -> None:
    path = builder(tmp_path / f"{builder.__name__}.flac")
    pcm, fs = _read(path)

    result = analyze(pcm, float(fs), claimed_sample_rate=claimed)

    assert result.verdict is expected
    assert result.detail


def test_fraud_128_cutoff_lands_in_expected_band(tmp_path: Path) -> None:
    path = fixture_fraud_128(tmp_path / "fraud.flac")
    pcm, fs = _read(path)

    result = analyze(pcm, float(fs), claimed_sample_rate=_FS)

    assert result.verdict is Verdict.FRAUD
    assert 15_000.0 <= (result.cutoff_hz or 0) <= 17_500.0
    assert (result.steepness_db_per_khz or 0) >= 25.0


def test_excerpt_analysis_runs_under_budget(tmp_path: Path) -> None:
    import time

    path = fixture_honest_full(tmp_path / "honest.flac")
    pcm, fs = _read(path)
    excerpt = pcm[: int(60 * fs)]

    started = time.monotonic()
    analyze(excerpt, float(fs), claimed_sample_rate=_FS)
    elapsed = time.monotonic() - started

    assert elapsed < 5.0
