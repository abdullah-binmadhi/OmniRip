"""Regression tests for track-scoped Workbench state (docs/14 M1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult

from harvester.models import Mode, TrackJob
from harvester.ui.operation_state import Operation
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.workbench import WorkbenchWidget


class StateTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")


def test_stale_workbench_result_is_rejected_after_track_change() -> None:
    app = StateTestApp()

    async def _run() -> None:
        async with app.run_test():
            wb = app.query_one("#test-workbench", WorkbenchWidget)
            wb._operation_state.load_track("first-job")
            token = wb._operation_state.begin(Operation.HOSTED_SEPARATION)
            wb._operation_state.load_track("second-job")
            assert wb._is_current_operation(token) is False

    import asyncio

    asyncio.run(_run())


async def test_load_job_rejects_stale_cross_track_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stem dir with the right name but wrong source must not be adopted."""
    from harvester.analysis.enhancement.stem_cache import write_cache_manifest

    cache_root = tmp_path / "cache" / "stems"
    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.default_stem_cache_dir",
        lambda: cache_root,
    )
    source = tmp_path / "song.mp3"
    source.write_bytes(b"audio-bytes-here")
    stem_dir = cache_root / f"song_{source.stat().st_size}"
    stem_dir.mkdir(parents=True)
    (stem_dir / f"{source.stem}_neural_vocals.wav").write_bytes(b"vocal")
    (stem_dir / f"{source.stem}_neural_instrumental.wav").write_bytes(b"inst")
    other = tmp_path / "other.mp3"
    other.write_bytes(b"different-audio")
    write_cache_manifest(stem_dir, other)  # belongs to another file

    app = StateTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(
                TrackJob(mode=Mode.SINGLE_URL, input_path=source, output_path=source)
            )
        await pilot.pause()
        assert wb.path_voc is None
        assert wb.path_inst is None
        assert wb.stem_cache_dir is None


async def test_load_job_restores_measured_speakers_from_meta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching diarization.json restores the advisory count on reload.

    The production writer records the file that was actually diarized — the
    vocals stem when one exists (docs/13 D27) — so the restore must check
    that file, not the mp3 (docs/14 M2, review finding).
    """
    from harvester.analysis.enhancement.stem_cache import (
        source_fingerprint,
        write_cache_manifest,
        write_stage_meta,
    )

    cache_root = tmp_path / "cache" / "stems"
    monkeypatch.setattr(
        "harvester.analysis.enhancement.stem_separator.default_stem_cache_dir",
        lambda: cache_root,
    )
    source = tmp_path / "song.mp3"
    source.write_bytes(b"audio-bytes-here")
    stem_dir = cache_root / f"song_{source.stat().st_size}"
    stem_dir.mkdir(parents=True)
    vocals = stem_dir / f"{source.stem}_neural_vocals.wav"
    vocals.write_bytes(b"vocal")
    (stem_dir / f"{source.stem}_neural_instrumental.wav").write_bytes(b"inst")
    write_cache_manifest(stem_dir, source)
    write_stage_meta(
        stem_dir,
        "diarization",
        {
            "speaker_count": 2,
            "model": "speaker-diarization-community-1",
            "device": "cpu",
            "source_path": str(vocals),
            "source_size": vocals.stat().st_size,
            "source_fingerprint": source_fingerprint(vocals),
        },
    )

    app = StateTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(
                TrackJob(mode=Mode.SINGLE_URL, input_path=source, output_path=source)
            )
        await pilot.pause()
        assert wb.measured_speakers == 2
        assert wb.path_voc is not None  # matching cache adopted
