"""NEURAL FULL extras: 6-source guitar/piano stems become first-class lanes (docs/13)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.analysis.enhancement.stem_separator import StemSeparator


class _FakeSixSourceModel:
    """Stand-in for HTDemucs-6s: same source order, no weights, no download."""

    sources = ("drums", "bass", "other", "vocals", "guitar", "piano")
    samplerate = 44100

    def to(self, device: object) -> _FakeSixSourceModel:
        return self

    def eval(self) -> _FakeSixSourceModel:
        return self


def _write_song(path: Path, seconds: float = 3.0, amplitude: float = 0.3) -> None:
    rng = np.random.default_rng(7)
    samples = int(44100 * seconds)
    audio = (rng.standard_normal((samples, 2)) * amplitude).astype(np.float32)
    sf.write(path, audio, 44100)


def _write_stem(path: Path, seconds: float = 3.0, amplitude: float = 0.3) -> None:
    _write_song(path, seconds=seconds, amplitude=amplitude)


def test_separate_extra_lanes_writes_guitar_and_piano(tmp_path, monkeypatch) -> None:
    """The extras pass persists {stem}_{mode}_raw_guitar/piano.wav for the lane engine."""
    pytest.importorskip("demucs")
    import torch
    from demucs import apply as demucs_apply

    song = tmp_path / "song.wav"
    _write_song(song)

    def _fake_apply_model(model, mix, **kwargs):  # noqa: ANN001, ANN003
        samples = mix.shape[-1]
        stems = torch.zeros((1, 6, 2, samples), dtype=torch.float32)
        stems[:, 4] = 0.30  # guitar
        stems[:, 5] = 0.25  # piano
        return stems

    monkeypatch.setattr(demucs_apply, "apply_model", _fake_apply_model)
    monkeypatch.setattr(
        StemSeparator, "_load_extra_source_model", lambda self: _FakeSixSourceModel()
    )

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    separator = StemSeparator(cache_dir=tmp_path / "cache")
    saved = separator.separate_extra_lanes(song, stem_dir, mode="ensemble")

    assert set(saved) == {"guitar", "piano"}
    for name, path in saved.items():
        assert path.name == f"song_ensemble_raw_{name}.wav"
        assert path.exists() and path.stat().st_size > 44

    # A second call is served from the cache (no model load, no inference).
    monkeypatch.setattr(
        StemSeparator,
        "_load_extra_source_model",
        lambda self: pytest.fail("cached extras must not reload the model"),
    )
    again = separator.separate_extra_lanes(song, stem_dir, mode="ensemble")
    assert set(again) == {"guitar", "piano"}


def test_extra_lanes_degrade_to_empty_without_the_model(tmp_path, monkeypatch) -> None:
    """A missing 6-source model returns {} — extra lanes are never a failure."""
    song = tmp_path / "song.wav"
    _write_song(song)
    monkeypatch.setattr(StemSeparator, "_load_extra_source_model", lambda self: None)

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    separator = StemSeparator(cache_dir=tmp_path / "cache")

    assert separator.separate_extra_lanes(song, stem_dir, mode="ensemble") == {}
    assert not list(stem_dir.glob("*_raw_guitar.wav"))


def test_six_source_stems_become_lanes_with_extra_source_provenance(tmp_path) -> None:
    """Guitar/piano raw stems show up as lanes, labelled 6-source in the plan."""
    from harvester.analysis.enhancement.layers import build_layer_track

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    for name in ("vocals", "bass", "drums", "other", "guitar", "piano"):
        _write_stem(stem_dir / f"{suffix}_raw_{name}.wav")

    track = build_layer_track(
        stem_dir,
        "song",
        "ensemble",
        duration_s=3.0,
        sample_rate=44100,
    )

    lanes = track.active_layers
    assert "guitar" in lanes and "piano" in lanes
    # Known lanes keep their order; the extras come after them.
    assert lanes.index("vocals") < lanes.index("guitar")
    assert lanes.index("other") < lanes.index("piano")

    plan = track.lane_plan
    assert plan is not None
    assert plan.origin_of("guitar") == "extra-source"
    assert plan.confidence_of("guitar") == "low"
    assert plan.origin_of("vocals") == "separator"
    assert "+guitar" in track.lane_summary or "guitar" in track.lane_summary


def test_silent_extra_stems_do_not_create_lanes(tmp_path) -> None:
    """A near-silent guitar stem fails the presence gate — no empty rows."""
    from harvester.analysis.enhancement.layers import build_layer_track

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    for name in ("vocals", "bass", "drums", "other"):
        _write_stem(stem_dir / f"{suffix}_raw_{name}.wav")
    # Silence for guitar (bleed-only level), loud piano.
    _write_stem(stem_dir / f"{suffix}_raw_guitar.wav", amplitude=1e-5)
    _write_stem(stem_dir / f"{suffix}_raw_piano.wav")

    track = build_layer_track(stem_dir, "song", "ensemble", duration_s=3.0, sample_rate=44100)

    assert "piano" in track.active_layers
    assert "guitar" not in track.active_layers
