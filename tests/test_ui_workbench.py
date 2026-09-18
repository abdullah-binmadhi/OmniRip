"""Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player scrubber."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Button

from harvester.models import Mode, State, TrackJob
from harvester.ui.player import AudioPlayerWidget, InteractiveScrubber, StreamMonitorWidget
from harvester.ui.workbench import WorkbenchWidget


class WorkbenchTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")


async def test_workbench_stream_switching_and_metrics(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)
        monitor = app.query_one("#player-monitor", StreamMonitorWidget)
        assert wb.active_stream == "MP3"

        dummy_src = tmp_path / "stream_orig.opus"
        dummy_src.write_bytes(b"opus-data")
        dummy_mp3 = tmp_path / "stream_transcode.mp3"
        dummy_mp3.write_bytes(b"mp3-data")
        dummy_enh = tmp_path / "stream_transcode.enhanced.mp3"
        dummy_enh.write_bytes(b"enh-data")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_src)
        job.id = "job-stream-test"
        job.state = State.COMPLETED
        job.workspace_path = dummy_src
        job.output_path = dummy_mp3
        job.spectral.cutoff_hz = 16000.0

        wb.load_job(job)
        assert wb.cutoff_hz == 16000.0
        assert wb.path_mp3 == dummy_mp3
        assert wb.path_enh == dummy_enh

        # Check mastering deck metrics
        deck_title = app.query_one("#wb-inspector-title")
        assert "RESTORATION MASTERING DECK" in str(deck_title.render())
        spec_cutoff = app.query_one("#wb-spec-cutoff")
        assert "16.00 kHz" in str(spec_cutoff.render())

        # Switch to Stream ENH via button
        btn_enh = app.query_one("#btn-stream-enh", Button)
        btn_enh.press()
        await pilot.pause()
        assert wb.active_stream == "ENH"
        assert player.current_track == dummy_enh
        assert monitor.is_enhanced is True

        # Switch to Stream MP3 via button
        btn_mp3 = app.query_one("#btn-stream-mp3", Button)
        btn_mp3.press()
        await pilot.pause()
        assert wb.active_stream == "MP3"
        assert player.current_track == dummy_mp3
        assert monitor.is_enhanced is False

        # Preset selection change
        select = app.query_one("#wb-preset-select")
        select.value = "fast_balanced"
        await pilot.pause()
        assert wb.selected_preset_id == "fast_balanced"


async def test_player_interactive_scrubber_and_seeking(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        player = app.query_one("#audio-player", AudioPlayerWidget)
        scrubber = app.query_one("#player-scrubber", InteractiveScrubber)

        player.duration_s = 100.0
        player.elapsed_s = 0.0

        # Seek to 45 seconds
        player.seek(45.0)
        assert player.elapsed_s == 45.0
        assert scrubber.progress == 0.45

        # Seek relative +10s
        player.seek_relative(10.0)
        assert player.elapsed_s == 55.0
        assert scrubber.progress == 0.55

        # Seek relative -20s
        player.seek_relative(-20.0)
        assert player.elapsed_s == 35.0
        assert scrubber.progress == 0.35

        # Dispatch Scrubber SeekRequested message (simulating click at 80%)
        scrubber.post_message(InteractiveScrubber.SeekRequested(0.80))
        await pilot.pause()
        assert player.elapsed_s == 80.0
        assert scrubber.progress == 0.80
