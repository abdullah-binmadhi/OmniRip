"""Tests for per-second issue scanning and "Suggest spots" range merging."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from harvester.analysis.enhancement.segment_analysis import (
    issue_seconds,
    merge_seconds,
    suggest_ranges,
)

SR = 44100


def test_merge_seconds_merges_gap_seconds_and_pads():
    ranges = merge_seconds([5, 6, 10], gap_s=1.0, pad_s=0.5, duration_s=20.0)
    assert ranges == [(4.5, 7.5), (9.5, 11.5)]


def test_merge_seconds_empty_and_clamped():
    assert merge_seconds([]) == []
    assert merge_seconds([19], pad_s=0.5, duration_s=20.0) == [(18.5, 20.0)]


def test_suggest_ranges_finds_hissy_bursts(tmp_path: Path):
    seconds = 6
    n = seconds * SR
    t = np.linspace(0, seconds, n, endpoint=False)
    signal = np.zeros(n, dtype=np.float32)
    for start_s, end_s in ((1.0, 2.0), (4.0, 5.0)):
        mask = (t >= start_s) & (t < end_s)
        signal[mask] = 0.4 * np.sin(2 * np.pi * 7000.0 * t[mask])
    path = tmp_path / "vocals.wav"
    sf.write(path, np.stack([signal, signal], axis=1), SR)

    flagged = issue_seconds(path, "sizzle", "vocals", duration_s=seconds, sample_rate=SR)
    assert flagged == [1, 4]

    ranges = suggest_ranges(path, "sizzle", "vocals", duration_s=seconds, sample_rate=SR)
    assert len(ranges) == 2
    for (lo, hi), (start_s, end_s) in zip(ranges, ((1.0, 2.0), (4.0, 5.0)), strict=True):
        assert lo <= start_s and hi >= end_s


def test_suggest_ranges_silent_track_yields_nothing(tmp_path: Path):
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros((SR, 2), dtype=np.float32), SR)
    assert suggest_ranges(path, "sizzle", "vocals", duration_s=1.0, sample_rate=SR) == []
