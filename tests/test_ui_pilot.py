"""UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)."""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Button

textual = pytest.importorskip("textual")

from harvester.config import load_config  # noqa: E402
from harvester.models import Mode, State, TrackJob  # noqa: E402
from harvester.ui.app import (  # noqa: E402
    DiscardEditsConfirmScreen,
    HarvesterApp,
    JobTable,
    QuitConfirmScreen,
    QuitDirtyConfirmScreen,
)
from harvester.ui.bridge import FlushPlan  # noqa: E402
from harvester.ui.logconsole import LogConsole  # noqa: E402
from harvester.ui.workbench import WorkbenchWidget  # noqa: E402


class StubOrchestrator:
    """Minimal orchestrator stand-in for UI pilots (no services, no network)."""

    def __init__(self) -> None:
        self.events: asyncio.Queue = asyncio.Queue()
        self.jobs: dict[str, TrackJob] = {}
        self.last_batch_root = None

    async def start(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def cancel(self, job_id: str) -> None:
        return None

    async def cancel_all(self) -> None:
        return None

    async def purge_batch_trash(self) -> int:
        return 0


def _app(tmp_path):
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    return HarvesterApp(config, auto_startup=False)


@pytest.mark.asyncio
async def test_log_level_cycles_on_l_key(tmp_path) -> None:
    app = _app(tmp_path)

    async with app.run_test() as pilot:
        console = app.query_one(LogConsole)
        assert console.mode == "INFO"
        await pilot.press("l")
        assert console.mode == "WARN+ERROR"
        await pilot.press("l")
        assert console.mode == "DEBUG"


@pytest.mark.asyncio
async def test_toggle_mode_switches_select(tmp_path) -> None:
    app = _app(tmp_path)

    async with app.run_test() as pilot:
        select = app.query_one("#mode")
        assert select.value == Mode.SINGLE_URL.value
        await pilot.press("ctrl+p")
        assert select.value == Mode.BATCH_AUDIT.value
        await pilot.press("ctrl+p")
        assert select.value == Mode.SINGLE_URL.value


@pytest.mark.asyncio
async def test_quit_confirms_when_jobs_active(tmp_path) -> None:
    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()
    app.orchestrator.jobs["abc"] = TrackJob(mode=Mode.SINGLE_URL)

    async with app.run_test() as pilot:
        await pilot.press("ctrl+q")
        await pilot.pause()
        assert isinstance(app.screen, QuitConfirmScreen)


@pytest.mark.asyncio
async def test_dirty_edits_confirm_before_switching_tracks(tmp_path) -> None:
    """A dirty layer edit plan requires confirmation before another track loads."""
    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()
    first = TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "one.mp3")
    first.id = "job-a"
    first.state = State.COMPLETED
    second = TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "two.mp3")
    second.id = "job-b"
    second.state = State.COMPLETED
    (tmp_path / "one.mp3").write_bytes(b"a")
    (tmp_path / "two.mp3").write_bytes(b"b")
    app.orchestrator.jobs["job-a"] = first
    app.orchestrator.jobs["job-b"] = second

    async with app.run_test() as pilot:
        wb = app.query_one("#workbench-widget", WorkbenchWidget)
        table = app.query_one(JobTable)
        table.update_job(first)
        table.update_job(second)

        app._load_job_into_workbench(first)
        await pilot.pause()
        assert wb.current_job is first

        wb.mark_layer_dirty()
        assert wb.dirty is True

        table.move_cursor(row=1)  # job-b row
        app._load_selected_into_workbench_and_player()
        await pilot.pause()
        assert isinstance(app.screen, DiscardEditsConfirmScreen)
        assert wb.current_job is first  # not clobbered yet

        confirm = app.screen
        confirm.query_one("#confirm-start", Button).press()
        await pilot.pause()
        assert wb.current_job is second
        assert wb.dirty is False


@pytest.mark.asyncio
async def test_quit_confirms_when_layer_edits_dirty(tmp_path) -> None:
    """Quitting with unsaved layer edits asks for a discard confirmation."""
    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()

    async with app.run_test() as pilot:
        wb = app.query_one("#workbench-widget", WorkbenchWidget)
        wb.mark_layer_dirty()

        await pilot.press("ctrl+q")
        await pilot.pause()
        assert isinstance(app.screen, QuitDirtyConfirmScreen)

        screen = app.screen
        screen.query_one("#confirm-cancel", Button).press()
        await pilot.pause()
        assert not isinstance(app.screen, QuitDirtyConfirmScreen)


@pytest.mark.asyncio
async def test_apply_flush_renders_job_row(tmp_path) -> None:
    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=None)
    job.id = "job-1"
    job.state = State.ANALYZING
    app.orchestrator.jobs[job.id] = job

    async with app.run_test():
        table = app.query_one(JobTable)
        assert not table.has_job("job-1")

        app._apply_flush(FlushPlan(job_ids=["job-1"]))

        assert table.has_job("job-1")
        assert "[DIR]" in table.get_row_at(table.get_row_index("job-1"))[0]
        job.state = State.FALLBACK_DOWNLOADING
        app._apply_flush(FlushPlan(job_ids=["job-1"]))
        assert table.get_row_at(table.get_row_index("job-1"))[3] == "Fallback Downloading"


@pytest.mark.asyncio
async def test_apply_flush_log_lines_reach_console(tmp_path) -> None:
    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()

    async with app.run_test():
        app._apply_flush(FlushPlan(log_lines=[("INFO", "hello from bridge")]))

        console = app.query_one(LogConsole)
        assert ("INFO", "hello from bridge") in console._buffer


@pytest.mark.asyncio
async def test_w_keybinding_opens_workbench_modal(tmp_path) -> None:
    from harvester.ui.screens.curation_workbench import CurationWorkbenchModal

    app = _app(tmp_path)
    app.orchestrator = StubOrchestrator()
    dummy_audio = tmp_path / "song.mp3"
    dummy_audio.write_bytes(b"dummy")

    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=dummy_audio)
    job.id = "job-wb"
    job.state = State.COMPLETED
    job.output_path = dummy_audio
    app.orchestrator.jobs[job.id] = job

    async with app.run_test() as pilot:
        table = app.query_one(JobTable)
        app._apply_flush(FlushPlan(job_ids=["job-wb"]))
        assert table.has_job("job-wb")

        # Focus table and press 'w'
        table.focus()
        await pilot.press("w")
        await pilot.pause()
        assert isinstance(app.screen, CurationWorkbenchModal)
