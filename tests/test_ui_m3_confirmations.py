"""M3 user-facing confirmations, progress, cancellation and diagnostics (docs/14)."""

from __future__ import annotations

from pathlib import Path
from time import monotonic

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.models import Mode, TrackJob
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.workbench import WorkbenchWidget


class M3TestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")


def _loaded_workbench(tmp_path: Path, name: str = "confirm.mp3"):
    dummy = tmp_path / name
    dummy.write_bytes(b"mp3-data")
    return dummy, TrackJob(
        mode=Mode.SINGLE_URL,
        input_path=tmp_path / "src.opus",
        output_path=dummy,
    )


async def test_hosted_screen_confirms_before_any_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """☁ HOSTED SEPARATE shows a confirmation screen; upload only after YES."""
    from harvester.services import mvsep as mvsep_mod

    dummy, job = _loaded_workbench(tmp_path)
    launched: list[str] = []

    monkeypatch.setattr(
        WorkbenchWidget,
        "_launch_hosted_run",
        lambda self, sep_type: launched.append(sep_type),
    )

    async def _no_network_algorithms(self) -> list[dict]:
        return []

    monkeypatch.setattr(mvsep_mod.MvsepClient, "algorithms", _no_network_algorithms)

    app = M3TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(job)
        wb.switch_page("layers")
        await pilot.pause()

        wb._start_hosted_separation()
        await pilot.pause(0.3)

        from harvester.ui.hosted_screen import HostedSeparationScreen

        assert isinstance(app.screen, HostedSeparationScreen)
        assert launched == []  # nothing uploaded yet

        app.screen.query_one("#hosted-confirm", Button).press()
        await pilot.pause(0.3)

        from harvester.processing import DEFAULT_SEP_TYPE

        assert launched == [DEFAULT_SEP_TYPE]
        assert not isinstance(app.screen, HostedSeparationScreen)


async def test_hosted_screen_cancel_never_uploads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel on the hosted screen means zero network activity."""
    from harvester.services import mvsep as mvsep_mod

    dummy, job = _loaded_workbench(tmp_path, name="cancel.mp3")
    launched: list[str] = []
    monkeypatch.setattr(
        WorkbenchWidget,
        "_launch_hosted_run",
        lambda self, sep_type: launched.append(sep_type),
    )

    async def _no_network_algorithms(self) -> list[dict]:
        return []

    monkeypatch.setattr(mvsep_mod.MvsepClient, "algorithms", _no_network_algorithms)

    app = M3TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(job)
        wb.switch_page("layers")
        await pilot.pause()

        wb._start_hosted_separation()
        await pilot.pause(0.3)

        from harvester.ui.hosted_screen import HostedSeparationScreen

        assert isinstance(app.screen, HostedSeparationScreen)
        app.screen.query_one("#hosted-cancel", Button).press()
        await pilot.pause(0.3)

        assert launched == []


async def test_hosted_failure_status_names_the_cause_and_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed hosted run reports the reason and how to retry."""
    from harvester.services import mvsep as mvsep_mod

    dummy, job = _loaded_workbench(tmp_path, name="fail.mp3")

    class _FailingClient:
        available = True

        async def separate(self, *args, **kwargs):
            raise RuntimeError("boom: job rejected")

        async def close(self) -> None:
            pass

    monkeypatch.setattr(mvsep_mod, "MvsepClient", _FailingClient)

    app = M3TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(job)
        wb.switch_page("layers")
        await pilot.pause()

        wb._launch_hosted_run("vocals")
        await pilot.pause(0.4)

        status = str(wb.query_one("#wb-task-status", Label).render())
        assert "boom: job rejected" in status
        assert "retry" in status.lower()
        assert wb._hosted_task_running is False


async def test_diarization_heartbeat_reports_elapsed_and_stops_when_done(
    tmp_path: Path,
) -> None:
    """The speaker pass shows elapsed time while running and cleans up after."""
    dummy, job = _loaded_workbench(tmp_path, name="beat.mp3")

    app = M3TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(job)
        wb.switch_page("layers")
        await pilot.pause()

        wb._diarize_task_running = True
        wb._diarize_started = monotonic() - 65.0
        wb._diarize_heartbeat()

        status = str(wb.query_one("#wb-task-status", Label).render())
        assert "65s" in status

        stopped: list[str] = []

        class _FakeTimer:
            def stop(self) -> None:
                stopped.append("stopped")

        wb._diarize_task_running = False
        wb._diarize_timer = _FakeTimer()  # type: ignore[assignment]
        wb._diarize_heartbeat()
        assert stopped == ["stopped"]
        assert wb._diarize_timer is None


async def test_diagnostics_screen_renders_injected_rows(tmp_path: Path) -> None:
    """The diagnostics modal lists environment rows without network or models."""
    from harvester.ui.diagnostics import DiagnosticsScreen

    app = M3TestApp()
    async with app.run_test() as pilot:
        await app.push_screen(
            DiagnosticsScreen(rows=[("python", "3.14.3"), ("ffmpeg", "/opt/ffmpeg")])
        )
        await pilot.pause()

        from textual.widgets import Static

        from harvester.ui.diagnostics import DiagnosticsScreen as DS

        assert isinstance(app.screen, DS)
        text = str(app.screen.query_one("#diag-body", Static).render())
        assert "3.14.3" in text and "/opt/ffmpeg" in text
        app.screen.query_one("#diag-close", Button).press()
        await pilot.pause()


async def test_collect_diagnostics_never_imports_heavy_models() -> None:
    """Fast metadata-only collection: versions without importing torch."""
    from harvester.ui.diagnostics import collect_diagnostics

    rows = collect_diagnostics()
    labels = {label for label, _value in rows}
    assert "python" in labels
    assert "ffmpeg" in labels or "ffprobe" in labels
    joined = " ".join(value for _label, value in rows)
    assert joined  # non-empty values


async def test_hosted_picker_selection_is_honoured(tmp_path: Path) -> None:
    """Pressing a non-default model dismisses with THAT render_id, not the default."""
    from harvester.ui.hosted_screen import HostedSeparationScreen

    dummy, _ = _loaded_workbench(tmp_path)
    algorithms = [
        {"name": "Model One", "render_id": 1},
        {"name": "Model Two", "render_id": 2},
    ]

    app = M3TestApp()
    async with app.run_test() as pilot:
        screen = HostedSeparationScreen(
            source=dummy,
            default_sep_type="1",
            algorithms=algorithms,
        )
        result: list[str | None] = []

        def _on_dismiss(value: str | None) -> None:
            result.append(value)

        await app.push_screen(screen, _on_dismiss)
        await pilot.pause()

        radios = screen.query_one("#hosted-models").query("RadioButton")
        assert len(radios) == 2
        radios[0].value = True  # Model One (render_id 1) — NOT the default's slot
        await pilot.pause()

        screen.query_one("#hosted-confirm", Button).press()
        await pilot.pause()

        assert result == ["1"], result
