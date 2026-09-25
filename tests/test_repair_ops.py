"""Tests for the repair ops: range normalisation, ranged rendering, op effects."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.repair_ops import (
    load_stereo,
    normalise_ranges,
    op_de_bleed,
    op_de_click,
    op_de_ess,
    render_ranges,
    write_pcm32,
)

SR = 48000


def _tone(seconds: float, freq: float, sr: int = SR, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _band_energy(signal: np.ndarray, sr: int, lo: float, hi: float) -> float:
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)
    mask = (freqs >= lo) & (freqs <= hi)
    return float(np.sum(spectrum[mask] ** 2))


def test_normalise_ranges_clamps_sorts_and_merges():
    ranges = [(-1.0, 1.0), (2.0, 3.0), (3.1, 4.0), (8.0, 9.0), (5.0, 5.05)]
    out = normalise_ranges(ranges, duration_s=8.5)
    assert out == [(0.0, 1.0), (2.0, 4.0), (8.0, 8.5)]


def test_render_ranges_whole_track_applies_everywhere():
    audio = np.stack([_tone(1.0, 1000.0), _tone(1.0, 1000.0)])
    seen: list[int] = []

    def fn(segment: np.ndarray, sr: int) -> np.ndarray:
        seen.append(segment.shape[1])
        return segment * 0.5

    out = render_ranges(audio, SR, None, fn)
    assert seen == [audio.shape[1]]
    assert np.allclose(out, audio * 0.5, atol=1e-6)


def test_render_ranges_only_touches_selected_section():
    audio = np.stack([_tone(2.0, 1000.0), _tone(2.0, 1000.0)])
    out = render_ranges(audio, SR, [(1.0, 1.5)], op_de_bleed)
    quiet = int(0.2 * SR)
    assert np.allclose(out[:, :quiet], audio[:, :quiet], atol=1e-6)
    assert np.allclose(out[:, int(1.7 * SR) :], audio[:, int(1.7 * SR) :], atol=1e-6)
    mid = slice(int(1.2 * SR), int(1.3 * SR))
    assert _band_energy(out[0, mid], SR, 300, 3500) < 0.05 * _band_energy(
        audio[0, mid], SR, 300, 3500
    )


def test_op_de_ess_attenuates_sibilance_band_only():
    mixed = _tone(0.5, 7000.0) + _tone(0.5, 1000.0)
    audio = np.stack([mixed, mixed])
    out = op_de_ess(audio, SR)
    assert _band_energy(out[0], SR, 5500, 8500) < 0.1 * _band_energy(audio[0], SR, 5500, 8500)
    assert _band_energy(out[0], SR, 800, 1200) > 0.9 * _band_energy(audio[0], SR, 800, 1200)


def test_op_de_click_removes_impulse():
    audio = np.stack([_tone(0.25, 500.0), _tone(0.25, 500.0)])
    spike_idx = int(0.12 * SR)
    audio[0, spike_idx] = 0.95
    audio[1, spike_idx] = 0.95
    out = op_de_click(audio, SR)
    assert abs(float(out[0, spike_idx])) < abs(float(audio[0, spike_idx])) * 0.5


def test_write_and_load_roundtrip(tmp_path: Path):
    audio = np.stack([_tone(0.25, 440.0), _tone(0.25, 440.0)])
    dest = write_pcm32(audio, tmp_path / "out.wav", SR)
    loaded, sr = load_stereo(dest)
    assert sr == SR
    assert loaded.shape == audio.shape
    assert np.max(np.abs(loaded - audio)) < 1e-4
