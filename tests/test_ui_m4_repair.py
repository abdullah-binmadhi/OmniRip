"""M4 cache repair, result reuse and metadata visibility (docs/14)."""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.models import Mode, TrackJob
from harvester.ui.operation_state import Operation
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.workbench import WorkbenchWidget


class M4TestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")


def _job(tmp_path: Path, name: str = "repair.mp3") -> TrackJob:
    dummy = tmp_path / name
    dummy.write_bytes(b"mp3-data")
    return TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "src.opus", output_path=dummy)


async def test_rebuild_layers_forces_a_new_timeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """♻ REBUILD drops the cached grid and rebuilds from stems."""
    cache_root = tmp_path / "cache" / "stems"
    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.default_stem_cache_dir",
        lambda: cache_root,
    )
    dummy = tmp_path / "repair.mp3"
    dummy.write_bytes(b"mp3-data")
    stem_dir = cache_root / f"repair_{dummy.stat().st_size}"
    stem_dir.mkdir(parents=True)
    (stem_dir / "repair_neural_vocals.wav").write_bytes(b"v")
    (stem_dir / "repair_neural_instrumental.wav").write_bytes(b"i")

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(
            TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "src.opus", output_path=dummy)
        )
        wb.switch_page("layers")
        await pilot.pause()

        built: list[str] = []

        async def _fake_build(self, *a, **k) -> None:
            built.append("build")

        monkeypatch.setattr(WorkbenchWidget, "_async_build_layers", _fake_build)
        wb.layer_track = object()  # pretend a grid is loaded

        wb._rebuild_layers()
        await pilot.pause()
        assert wb.layer_track is None
        assert built == ["build"]


async def test_rerun_tags_runs_tagging_then_rebuilds(tmp_path: Path, monkeypatch) -> None:
    """🏷 RE-TAGS re-runs CLAP and replans with fresh tags."""

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(_job(tmp_path))
        wb.switch_page("layers")
        await pilot.pause()

        events: list[str] = []

        async def _fake_tagging_pass(self, source_path, stem_dir, *, generation=None):
            events.append("tagged")

        monkeypatch.setattr(WorkbenchWidget, "_run_tagging_pass", _fake_tagging_pass)
        monkeypatch.setattr(
            WorkbenchWidget,
            "_ensure_layers_built",
            lambda self, force=False: events.append("rebuild"),
        )

        wb._rerun_tags()
        for _ in range(5):
            await pilot.pause(0.1)
            if events:
                break
        assert events == ["tagged", "rebuild"]


async def test_clear_cache_requires_confirmation_and_deletes_only_the_stem_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """🗑 CLEAR CACHE asks first, then removes exactly this track's stem dir."""
    cache_root = tmp_path / "cache" / "stems"
    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.default_stem_cache_dir",
        lambda: cache_root,
    )
    dummy = tmp_path / "clearme.mp3"
    dummy.write_bytes(b"mp3-data")
    stem_dir = cache_root / f"clearme_{dummy.stat().st_size}"
    stem_dir.mkdir(parents=True)
    (stem_dir / "clearme_neural_vocals.wav").write_bytes(b"v")
    (stem_dir / "clearme_neural_instrumental.wav").write_bytes(b"i")
    other = cache_root / "other_1"
    other.mkdir(parents=True)
    (other / "keep.wav").write_bytes(b"k")

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(
            TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "src.opus", output_path=dummy)
        )
        wb.switch_page("layers")
        await pilot.pause()
        assert wb.path_voc is not None  # cache adopted

        wb._clear_track_cache()
        await pilot.pause(0.2)
        from harvester.ui.app import CacheClearConfirmScreen

        assert isinstance(app.screen, CacheClearConfirmScreen)
        app.screen.query_one("#cache-clear-confirm", Button).press()
        await pilot.pause(0.3)

        assert not stem_dir.exists()
        assert (other / "keep.wav").exists()  # other tracks untouched
        assert wb.path_voc is None and wb.path_inst is None
        assert wb.layer_stem_dir is None


async def test_diarizer_reused_across_runs(tmp_path: Path, monkeypatch) -> None:
    """The pyannote pipeline loads once per session, not once per click."""
    from harvester.services import diarization as dia_mod

    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"wav")

    creations: list[str] = []

    class _FakeDiarizer:
        def __init__(self, **kwargs) -> None:
            creations.append("new")

        def diarize(self, source, *, max_seconds=0.0, progress=None, num_speakers=None):
            return dia_mod.DiarizationResult(
                speakers=("SPEAKER_00",),
                turns=(dia_mod.SpeakerTurn(0.0, 1.0, "SPEAKER_00"),),
                model="pyannote/fake",
                device="cpu",
                elapsed_s=0.5,
            )

    monkeypatch.setattr(dia_mod, "Diarizer", _FakeDiarizer)
    monkeypatch.setattr(dia_mod, "pyannote_available", lambda: True)

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(_job(tmp_path, name="voicey.mp3"))
        await pilot.pause()

        stem_dir = tmp_path / "cache" / "stems" / "voicey_8"
        stem_dir.mkdir(parents=True, exist_ok=True)
        source = wb.path_mp3
        assert source is not None

        first = wb._begin_operation(Operation.DIARIZATION)
        assert first is not None
        wb._diarize_task_running = True
        await wb._async_diarize(source, audio, 0.0, first, stem_dir)

        second = wb._begin_operation(Operation.DIARIZATION)
        assert second is not None
        wb._diarize_task_running = True
        await wb._async_diarize(source, audio, 0.0, second, stem_dir)

        assert creations == ["new"]  # one pipeline load, two measurements


async def test_diarization_result_applies_when_measuring_vocals_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measuring the vocals stem (path != path_mp3) must still apply the count."""
    from harvester.services import diarization as dia_mod

    vocals = tmp_path / "voice.wav"
    vocals.write_bytes(b"wav")

    class _FakeDiarizer:
        def diarize(self, source, *, max_seconds=0.0, progress=None, num_speakers=None):
            return dia_mod.DiarizationResult(
                speakers=("SPEAKER_00",),
                turns=(dia_mod.SpeakerTurn(0.0, 1.0, "SPEAKER_00"),),
                model="pyannote/fake",
                device="cpu",
                elapsed_s=0.5,
            )

    monkeypatch.setattr(dia_mod, "Diarizer", _FakeDiarizer)
    monkeypatch.setattr(dia_mod, "pyannote_available", lambda: True)

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(_job(tmp_path, name="voicey.mp3"))
        await pilot.pause()

        source = wb.path_mp3
        assert source is not None and source != vocals

        stem_dir = tmp_path / "cache" / "stems" / "voicey_8"
        stem_dir.mkdir(parents=True, exist_ok=True)

        token = wb._begin_operation(Operation.DIARIZATION)
        assert token is not None
        wb._diarize_task_running = True
        await wb._async_diarize(source, vocals, 0.0, token, stem_dir)

        # The guard must key on the TRACK (path_mp3), not the analysis file.
        assert wb.measured_speakers == 1


async def test_tags_restore_with_source_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching tags.json surfaces again when the track reloads."""
    from harvester.analysis.enhancement.stem_cache import (
        write_cache_manifest,
        write_stage_meta,
    )

    cache_root = tmp_path / "cache" / "stems"
    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.default_stem_cache_dir",
        lambda: cache_root,
    )
    dummy = tmp_path / "tagged.mp3"
    dummy.write_bytes(b"mp3-data")
    stem_dir = cache_root / f"tagged_{dummy.stat().st_size}"
    stem_dir.mkdir(parents=True)
    (stem_dir / "tagged_neural_vocals.wav").write_bytes(b"v")
    (stem_dir / "tagged_neural_instrumental.wav").write_bytes(b"i")
    write_cache_manifest(stem_dir, dummy)
    write_stage_meta(
        stem_dir,
        "tags",
        {
            "labels": ["strings", "bass"],
            "scores": {"strings": 0.62, "bass": 0.41},
            "windows": 12,
            "model": "laion/clap-htsat-unfused",
            "source_size": dummy.stat().st_size,
        },
    )

    app = M4TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(
            TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "src.opus", output_path=dummy)
        )
        await pilot.pause()

        status = str(wb.query_one("#wb-layer-status", Label).render())
        assert "strings" in status and "bass" in status
