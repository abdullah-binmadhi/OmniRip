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
        assert "MASTERING DECK" in str(deck_title.render())
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

        # Comprehensive check for all 5 presets: Gain, Trim Bar, Slope, Stereo, Engine
        expected_metrics = {
            "conservative": {
                "gain": "0.0 dB",
                "trim": "-3dB ─── ▲ ─── +3dB",
                "slope": "-5.0 dB/oct",
                "stereo": "100% Stereo (Mono <100Hz)",
                "engine": "Non-Neural DSP Exciter",
            },
            "fast_balanced": {
                "gain": "0.0 dB",
                "trim": "-3dB ─── ▲ ─── +3dB",
                "slope": "-4.5 dB/oct",
                "stereo": "100% Stereo (Mono <100Hz)",
                "engine": "NVSR Multi-Band Residual",
            },
            "de_sizzle": {
                "gain": "-2.5 dB",
                "trim": "-3dB ══▲══ 0dB --",
                "slope": "-6.0 dB/oct",
                "stereo": "85% Stereo (Mono <100Hz)",
                "engine": "NVSR Multi-Band Residual",
            },
            "extended_air": {
                "gain": "+0.8 dB",
                "trim": "-- 0dB ══▲══ +3dB",
                "slope": "-4.0 dB/oct",
                "stereo": "100% Stereo (Mono <100Hz)",
                "engine": "Hybrid (NVSR + FlashSR)",
            },
            "narrow_stereo": {
                "gain": "0.0 dB",
                "trim": "-3dB ─── ▲ ─── +3dB",
                "slope": "-4.5 dB/oct",
                "stereo": "65% Focused (Headphone)",
                "engine": "NVSR Multi-Band Residual",
            },
        }

        select = app.query_one("#wb-preset-select")
        gain_label = app.query_one("#wb-spec-gain")
        trim_label = app.query_one("#wb-spec-trim")
        slope_label = app.query_one("#wb-spec-slope")
        stereo_label = app.query_one("#wb-spec-stereo")
        engine_label = app.query_one("#wb-spec-engine")

        for preset_id, expected in expected_metrics.items():
            select.value = preset_id
            await pilot.pause()
            assert wb.selected_preset_id == preset_id

            assert expected["gain"] in str(gain_label.render())
            assert expected["trim"] in str(trim_label.render())
            assert expected["slope"] in str(slope_label.render())
            assert expected["stereo"] in str(stereo_label.render())
            assert expected["engine"] in str(engine_label.render())

        # Verify Download Enhanced button
        btn_download = app.query_one("#wb-btn-export", Button)
        assert "DOWNLOAD ENHANCED" in str(btn_download.label)


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


async def test_workbench_explicit_download_enhanced_button(tmp_path: Path) -> None:
    """Verify that auditioning does not pollute output dir until button is clicked."""
    from unittest.mock import patch

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        out_dir = tmp_path / "music_output"
        out_dir.mkdir()
        dummy_mp3 = out_dir / "my_track.mp3"
        dummy_mp3.write_bytes(b"mp3-bytes")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.id = "job-explicit-dl"
        job.output_path = dummy_mp3
        job.spectral.cutoff_hz = 15000.0

        target_enhanced = out_dir / "my_track.enhanced.mp3"
        assert not target_enhanced.exists()

        # Load job — should NOT automatically create .enhanced.mp3 in out_dir
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)
        assert not target_enhanced.exists()

        # Press DOWNLOAD ENHANCED button
        btn_dl = app.query_one("#wb-btn-export", Button)
        mock_exported = out_dir / "my_track.enhanced.mp3"
        mock_exported.write_bytes(b"enhanced-mp3-bytes")

        with patch.object(wb.exporter, "export_enhanced_derivative", return_value=mock_exported):
            btn_dl.press()
            await pilot.pause()
            await pilot.pause()

        assert target_enhanced.exists()
        status_label = app.query_one("#wb-status")
        assert "Downloaded" in str(status_label.render())

