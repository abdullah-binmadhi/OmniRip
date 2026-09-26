"""Temporary scaffold for the visualizer audio extractor. Safe to delete."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from harvester.ui.visuals.audio_features import (
    N_LEVELS,
    SAMPLE_RATE,
    build_feature_track,
)


def _write_tone(tmp_path: Path, seconds: float = 0.5, freq: float = 220.0) -> Path:
    path = tmp_path / "tone.wav"
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    samples = (0.5 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SAMPLE_RATE)
        fh.writeframes(samples.tobytes())
    return path


def test_build_feature_track_decodes_a_tone(tmp_path):
    path = _write_tone(tmp_path)
    track = build_feature_track(path)

    assert track, "expected feature frames from a decodable tone"
    for ctx in track:
        assert ctx.is_playing is True
        assert len(ctx.levels_128) == N_LEVELS
        assert len(ctx.waveform_l) > 0
        assert float(np.max(ctx.levels_128)) > 0.0
        assert ctx.spectral_centroid > 0.0


def test_build_feature_track_returns_empty_for_missing_file(tmp_path):
    assert build_feature_track(tmp_path / "nope.wav") == []


def test_build_feature_track_respects_max_frames(tmp_path):
    path = _write_tone(tmp_path, seconds=1.0)
    assert len(build_feature_track(path, max_frames=3)) == 3


def test_feature_track_is_cached_per_file_mtime(tmp_path):
    path = _write_tone(tmp_path)
    assert build_feature_track(path) is build_feature_track(path)
