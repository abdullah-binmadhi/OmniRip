"""CLAP tagging (docs/13 D25): window planning, thresholds, tags.json, degrade paths."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from harvester.analysis.enhancement.tags import (
    LABEL_PROMPTS,
    TAGS_FILENAME,
    ClapTagger,
    TagResult,
    labels_for_threshold,
    read_tags,
    store_tags,
    tagged_labels,
    window_bounds,
)

# ---------------------------------------------------------------- windows


def test_window_bounds_short_track_is_a_single_window() -> None:
    assert window_bounds(3.0, 5.0, 24) == ((0.0, 3.0),)


def test_window_bounds_caps_long_tracks_and_stays_evenly_spaced() -> None:
    bounds = window_bounds(600.0, 5.0, 24)
    assert len(bounds) == 24
    assert bounds[0][0] == 0.0
    assert bounds[-1][1] == pytest.approx(600.0, abs=1.0)
    hops = [round(b[0] - a[0], 6) for a, b in zip(bounds, bounds[1:], strict=False)]
    assert len(set(hops)) == 1  # uniform hop
    assert hops[0] >= 5.0  # never overlaps windows
    assert all(end - start == pytest.approx(5.0) for start, end in bounds)


def test_window_bounds_rejects_nonsense() -> None:
    assert window_bounds(0.0) == ()
    assert window_bounds(10.0, window_s=0.0) == ()
    assert window_bounds(10.0, max_windows=0) == ()


# ---------------------------------------------------------------- selection


def test_labels_for_threshold_orders_by_score_and_caps() -> None:
    scores = {"drums": 0.9, "bass": 0.5, "strings": 0.2, "flute": 0.4}
    assert labels_for_threshold(scores, 0.3, 8) == ("drums", "bass", "flute")
    assert labels_for_threshold(scores, 0.3, 2) == ("drums", "bass")
    assert labels_for_threshold(scores, 0.95, 8) == ()


# ---------------------------------------------------------------- payload


def test_tag_result_round_trips_through_json() -> None:
    result = TagResult(labels=("strings", "bass"), scores={"strings": 0.61, "bass": 0.33}, windows=12)
    restored = TagResult.from_payload(json.loads(json.dumps(result.to_payload())))
    assert restored is not None
    assert restored.labels == ("strings", "bass")
    assert restored.score_map["strings"] == pytest.approx(0.61)
    assert restored.windows == 12
    assert "strings 0.61" in restored.describe()


def test_tag_result_from_payload_tolerates_junk() -> None:
    assert TagResult.from_payload("nope") is None
    assert TagResult.from_payload({}) is not None  # empty but valid
    tolerant = TagResult.from_payload({"labels": ["bass", ""], "scores": {"bass": "oops"}})
    assert tolerant is not None
    assert tolerant.labels == ("bass",)
    assert tolerant.score_map == {}


def test_tags_json_round_trip_and_missing_dir(tmp_path: Path) -> None:
    result = TagResult(labels=("piano",), scores={"piano": 0.4}, windows=3)
    path = store_tags(tmp_path / "stems", result)
    assert path.name == TAGS_FILENAME
    assert read_tags(tmp_path / "stems") is not None
    assert tagged_labels(tmp_path / "stems") == ("piano",)
    assert read_tags(None) is None
    assert read_tags(tmp_path / "elsewhere") is None

    (tmp_path / "stems" / TAGS_FILENAME).write_text("{not json", encoding="utf-8")
    assert read_tags(tmp_path / "stems") is None


# ---------------------------------------------------------------- tagger


class _FakeOut:
    def __init__(self, logits: object) -> None:
        self.logits_per_audio = logits


class _FakeModel:
    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows

    def eval(self) -> _FakeModel:
        return self

    def __call__(self, **kwargs: object) -> _FakeOut:
        import torch

        features = kwargs.get("input_features")
        batch = len(self.rows)
        if features is not None and hasattr(features, "shape"):
            batch = int(features.shape[0])  # type: ignore[attr-defined]
        rows = [self.rows[index % len(self.rows)] for index in range(batch)]
        return _FakeOut(torch.tensor(rows))


class _FakeProcessor:
    """Mimics ClapProcessor: text → ids, audio → features."""

    def __call__(self, **kwargs: object) -> dict[str, object]:
        import torch

        if "text" in kwargs:
            prompts = list(kwargs["text"])  # type: ignore[arg-type]
            ids = torch.arange(1, len(prompts) + 1).unsqueeze(0)
            return {"input_ids": ids, "attention_mask": torch.ones_like(ids)}
        audios = list(kwargs.get("audio") or kwargs.get("audios") or [])  # type: ignore[arg-type]
        return {
            "input_features": torch.zeros(len(audios), 4, 8),
            "is_longer": torch.zeros(len(audios), 1, dtype=torch.bool),
        }


def _tagger(**kwargs: object) -> ClapTagger:
    return ClapTagger(**kwargs)  # type: ignore[arg-type]


def test_score_windows_maps_logits_to_per_label_probabilities(monkeypatch) -> None:
    labels = [label for label, _ in LABEL_PROMPTS]
    logits = [0.0] * len(labels)
    logits[labels.index("bass")] = 8.0  # sigmoid(8) ≈ 0.9997
    logits[labels.index("flute")] = -8.0  # sigmoid(-8) ≈ 0.0003
    tagger = _tagger()
    rows = tagger._score_windows(
        _FakeModel([logits]), _FakeProcessor(), [np.zeros(240000, dtype=np.float32)], 48000, "cpu"
    )
    assert rows[0]["bass"] > 0.99
    assert rows[0]["flute"] < 0.01
    assert set(rows[0]) == set(labels)


def test_tag_file_reports_only_labels_above_threshold(tmp_path: Path, monkeypatch) -> None:
    audio = (np.random.default_rng(3).standard_normal(48000 * 12) * 0.1).astype(np.float32)
    src = tmp_path / "song.wav"
    import soundfile as sf

    sf.write(src, audio, 48000)

    labels = [label for label, _ in LABEL_PROMPTS]
    logits = [0.0] * len(labels)
    logits[labels.index("drums")] = 4.0  # ≈ 0.57 share
    logits[labels.index("bass")] = 3.5  # ≈ 0.34 share
    logits[labels.index("piano")] = -6.0  # ≈ 0.00 share

    tagger = _tagger(threshold=0.3, max_labels=2)
    monkeypatch.setattr(
        tagger, "_load_model", lambda: (_FakeModel([logits]), _FakeProcessor())
    )
    result = tagger.tag_file(src)
    assert result is not None
    assert result.labels == ("drums", "bass")
    assert result.windows == 3  # 12 s → 3 windows of 5 s
    assert result.score_map["piano"] < 0.3  # scored but not reported


def test_uninformative_logits_report_no_labels(tmp_path: Path, monkeypatch) -> None:
    """An even label spread (the model has no opinion) must not invent tags."""
    audio = (np.random.default_rng(9).standard_normal(48000 * 6) * 0.1).astype(np.float32)
    src = tmp_path / "unknown.wav"
    import soundfile as sf

    sf.write(src, audio, 48000)
    labels = [label for label, _ in LABEL_PROMPTS]
    tagger = _tagger(threshold=0.15)
    monkeypatch.setattr(
        tagger, "_load_model", lambda: (_FakeModel([[0.0] * len(labels)]), _FakeProcessor())
    )
    result = tagger.tag_file(src)
    assert result is not None
    assert result.labels == ()
    assert "no extra instrumentation" in result.describe()


def test_tag_and_store_writes_tags_beside_the_stems(tmp_path: Path, monkeypatch) -> None:
    audio = (np.random.default_rng(4).standard_normal(48000 * 6) * 0.1).astype(np.float32)
    src = tmp_path / "song.wav"
    import soundfile as sf

    sf.write(src, audio, 48000)

    labels = [label for label, _ in LABEL_PROMPTS]
    logits = [0.0] * len(labels)
    logits[labels.index("strings")] = 5.0

    tagger = _tagger(threshold=0.3)
    monkeypatch.setattr(tagger, "_load_model", lambda: (_FakeModel([logits]), _FakeProcessor()))
    result = tagger.tag_and_store(src, tmp_path / "stems")
    assert result is not None
    assert tagged_labels(tmp_path / "stems") == ("strings",)


def test_tag_file_returns_none_without_a_model(tmp_path: Path, monkeypatch) -> None:
    audio = np.zeros(48000 * 8, dtype=np.float32)
    src = tmp_path / "silent.wav"
    import soundfile as sf

    sf.write(src, audio, 48000)
    tagger = _tagger()
    monkeypatch.setattr(tagger, "_load_model", lambda: None)
    assert tagger.tag_file(src) is None
    assert tagger.tag_file(tmp_path / "missing.wav") is None


def test_tag_file_retries_on_cpu_when_the_device_fails(tmp_path: Path, monkeypatch) -> None:
    audio = (np.random.default_rng(5).standard_normal(48000 * 6) * 0.1).astype(np.float32)
    src = tmp_path / "song.wav"
    import soundfile as sf

    sf.write(src, audio, 48000)
    labels = [label for label, _ in LABEL_PROMPTS]
    logits = [0.0] * len(labels)
    logits[labels.index("guitar")] = 6.0
    attempts: list[str] = []

    tagger = _tagger(threshold=0.3, device="mps")
    monkeypatch.setattr(tagger, "_load_model", lambda: (_FakeModel([logits]), _FakeProcessor()))

    real = ClapTagger._score_windows

    def flaky(self: ClapTagger, model, processor, windows, sample_rate, device):  # type: ignore[no-untyped-def]
        attempts.append(device)
        if device != "cpu":
            raise RuntimeError("MPS backend does not support this op")
        return real(self, model, processor, windows, sample_rate, device)

    monkeypatch.setattr(ClapTagger, "_score_windows", flaky)
    result = tagger.tag_file(src)
    assert attempts == ["mps", "cpu"]
    assert result is not None and result.labels == ("guitar",)


def test_tagger_reports_unavailable_without_transformers(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals_: dict[str, object] | None = None,
        locals_: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name.startswith("transformers"):
            raise ImportError("no transformers here")
        return real_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert _tagger().available() is False
    assert _tagger()._load_model() is None
