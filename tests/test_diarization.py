"""Tests for the pyannote diarization service (docs/13 D27) — no models, no net."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from harvester.services import diarization as dia
from harvester.services.diarization import DiarizationResult, Diarizer, SpeakerTurn

# The optional `diarize`/`restore` extras bring torch; CI runs the base + dev
# extras only, so the tensor-dependent paths skip there and run fully on a
# machine with the extras installed.
_TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(
    not _TORCH_AVAILABLE, reason="torch (restore/diarize extra) not installed"
)


class _Segment:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class _Annotation:
    """Minimal stand-in for a pyannote Annotation."""

    def __init__(self, turns: list[tuple[float, float, str]]) -> None:
        self._turns = turns

    def itertracks(self, yield_label: bool = False):
        for start, end, label in self._turns:
            yield _Segment(start, end), None, label


class _Output:
    def __init__(self, turns: list[tuple[float, float, str]]) -> None:
        self.speaker_diarization = _Annotation(turns)


class _FakePipeline:
    """Records the calls the service makes and returns a canned annotation."""

    def __init__(self, turns: list[tuple[float, float, str]]) -> None:
        self.turns = turns
        self.calls: list[dict] = []
        self.device = "cpu"

    def to(self, device) -> _FakePipeline:
        self.device = str(device)
        return self

    def __call__(self, file, **kwargs) -> _Output:
        self.calls.append({"file": file, **kwargs})
        return _Output(self.turns)


@pytest.fixture()
def fake_audio(monkeypatch):
    def _load(path, target_sr: int = 44100):
        return np.zeros(44100 * 2, dtype=np.float32), 44100

    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.load_audio_numpy", _load
    )
    return _load


def _patch_pipeline(monkeypatch, turns: list[tuple[float, float, str]]) -> _FakePipeline:
    pipeline = _FakePipeline(turns)
    monkeypatch.setattr(
        Diarizer, "_load_pipeline", lambda self: (pipeline, "pyannote/fake-pipeline")
    )
    return pipeline


def test_result_speaker_count_and_description() -> None:
    empty = DiarizationResult()
    assert empty.speaker_count is None
    assert "nothing measured" in empty.describe()

    result = DiarizationResult(
        speakers=("SPEAKER_00", "SPEAKER_01"),
        turns=(SpeakerTurn(0.0, 1.5, "SPEAKER_00"), SpeakerTurn(2.0, 3.0, "SPEAKER_01")),
        model="pyannote/speaker-diarization-community-1",
        elapsed_s=12.4,
    )
    assert result.speaker_count == 2
    assert result.turns[0].duration == 1.5
    assert "2" in result.describe() and "advisory" in result.describe()


def test_pyannote_available_reports_a_bool() -> None:
    assert isinstance(dia.pyannote_available(), bool)


def test_diarize_requires_the_optional_extra(monkeypatch) -> None:
    monkeypatch.setattr(dia, "pyannote_available", lambda: False)
    with pytest.raises(RuntimeError, match="not installed"):
        Diarizer()._load_pipeline()


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Diarizer().diarize(tmp_path / "nope.mp3")


@requires_torch
def test_diarize_reports_turns_and_speakers(tmp_path: Path, monkeypatch, fake_audio) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3")
    pipeline = _patch_pipeline(
        monkeypatch,
        [(0.0, 4.0, "SPEAKER_00"), (4.5, 9.0, "SPEAKER_01"), (9.5, 11.0, "SPEAKER_00")],
    )
    steps: list[tuple[float, str]] = []

    result = Diarizer().diarize(source, progress=lambda pct, step: steps.append((pct, step)))

    assert result.speaker_count == 2
    assert result.speakers == ("SPEAKER_00", "SPEAKER_01")
    assert len(result.turns) == 3
    assert result.speech_s == pytest.approx(4.0 + 4.5 + 1.5)
    assert result.device == "cpu"
    assert pipeline.calls and pipeline.calls[0]["file"]["sample_rate"] == 44100
    assert steps and steps[-1][0] == 100.0
    assert "advisory" in result.describe()


@requires_torch
def test_num_speakers_hint_is_forwarded(tmp_path: Path, monkeypatch, fake_audio) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3")
    pipeline = _patch_pipeline(monkeypatch, [(0.0, 1.0, "SPEAKER_00")])

    Diarizer().diarize(source, num_speakers=3)

    assert pipeline.calls[0]["num_speakers"] == 3


@requires_torch
def test_max_seconds_truncates_the_measurement(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3")
    captured: dict[str, int] = {}

    def _load(path, target_sr: int = 44100):
        audio = np.zeros(44100 * 10, dtype=np.float32)
        captured["samples"] = audio.shape[0]
        return audio, 44100

    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.load_audio_numpy", _load
    )
    pipeline = _patch_pipeline(monkeypatch, [(0.0, 1.0, "SPEAKER_00")])

    Diarizer().diarize(source, max_seconds=3.0)

    waveform = pipeline.calls[0]["file"]["waveform"]
    assert waveform.shape[-1] == 44100 * 3


@requires_torch
def test_component_fallback_when_the_pipeline_repo_is_gated(monkeypatch) -> None:
    """A gated pipeline repo must not disable the feature (docs/13 §8)."""
    import pyannote.audio

    def _denied(*args, **kwargs):
        raise RuntimeError("403 gated")

    monkeypatch.setattr(pyannote.audio.Pipeline, "from_pretrained", _denied)
    sentinel = object()
    monkeypatch.setattr(
        Diarizer,
        "_load_component_pipeline",
        lambda self, token: (sentinel, "pyannote/segmentation-3.0+embedding"),
    )

    pipeline, loaded = Diarizer(allow_component_fallback=True)._load_pipeline()

    assert pipeline is sentinel
    assert loaded.endswith("+embedding")


@requires_torch
def test_component_fallback_can_be_disabled(monkeypatch) -> None:
    import pyannote.audio

    def _denied(*args, **kwargs):
        raise RuntimeError("403 gated")

    monkeypatch.setattr(pyannote.audio.Pipeline, "from_pretrained", _denied)
    with pytest.raises(RuntimeError, match="403 gated"):
        Diarizer(allow_component_fallback=False)._load_pipeline()
