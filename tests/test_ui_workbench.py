"""Unit tests for WorkbenchWidget in-page layout and A/B/C audition switching."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Button

from harvester.models import Mode, State, TrackJob
from harvester.ui.workbench import WorkbenchWidget


class WorkbenchTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield WorkbenchWidget(id="test-workbench")


async def test_workbench_abc_stream_switching(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        assert wb.active_stream == "B"

        dummy_a = tmp_path / "stream_a.opus"
        dummy_a.write_bytes(b"opus-data")
        dummy_b = tmp_path / "stream_b.mp3"
        dummy_b.write_bytes(b"mp3-data")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_a)
        job.id = "job-abc"
        job.state = State.COMPLETED
        job.workspace_path = dummy_a
        job.output_path = dummy_b
        job.spectral.cutoff_hz = 17500.0

        wb.load_job(job)
        assert wb.cutoff_hz == 17500.0
        assert wb.path_a == dummy_a
        assert wb.path_b == dummy_b

        # Switch to Stream A
        btn_a = app.query_one("#btn-stream-a", Button)
        btn_a.press()
        await pilot.pause()
        assert wb.active_stream == "A"

        # Switch to Stream B
        btn_b = app.query_one("#btn-stream-b", Button)
        btn_b.press()
        await pilot.pause()
        assert wb.active_stream == "B"

        # Preset selection change
        select = app.query_one("#wb-preset-select")
        select.value = "fast_balanced"
        await pilot.pause()
        assert wb.selected_preset_id == "fast_balanced"
