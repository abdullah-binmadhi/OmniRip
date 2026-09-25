"""Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player scrubber."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, ProgressBar, Select, SelectionList

from harvester.analysis.enhancement.eq import EQ_PRESET_BANKS
from harvester.models import Mode, State, TrackJob
from harvester.ui.player import AudioPlayerWidget, InteractiveScrubber, StreamMonitorWidget
from harvester.ui.report import ReportPanel
from harvester.ui.visualizer import AudioVisualizer
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
        assert not monitor.is_enhanced

        # Check Eco mode presets (Conservative DSP and Fast Neural)
        eco_metrics = {
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
        }

        select = app.query_one("#wb-preset-select", Select)
        gain_label = app.query_one("#wb-spec-gain")
        trim_label = app.query_one("#wb-spec-trim")
        slope_label = app.query_one("#wb-spec-slope")
        stereo_label = app.query_one("#wb-spec-stereo")
        engine_label = app.query_one("#wb-spec-engine")

        for preset_id, expected in eco_metrics.items():
            select.value = preset_id
            await pilot.pause()
            assert wb.selected_preset_id == preset_id

            assert expected["gain"] in str(gain_label.render())
            assert expected["trim"] in str(trim_label.render())
            assert expected["slope"] in str(slope_label.render())
            assert expected["stereo"] in str(stereo_label.render())
            assert expected["engine"] in str(engine_label.render())

        assert wb.neural_enabled is True
        ai_metrics = {
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

        for preset_id, expected in ai_metrics.items():
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
        assert "SAVE ENHANCED" in str(btn_download.label)


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
            for _ in range(25):
                await pilot.pause(0.05)
                if target_enhanced.exists() and "Downloaded" in str(
                    app.query_one("#wb-status").render()
                ):
                    break

        assert target_enhanced.exists()
        status_label = app.query_one("#wb-status")
        assert "Downloaded" in str(status_label.render())


async def test_workbench_minimal_header_and_track_info_actions() -> None:
    """The header keeps only MP3/ENH; upkeep actions live in the Track Info modal."""
    from harvester.ui.track_info import TrackInfoScreen

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)

        # Header minimisation: legacy buttons are gone, the two streams remain.
        assert len(app.query("#btn-stream-mp3")) == 1
        assert len(app.query("#btn-stream-enh")) == 1
        assert len(app.query("#btn-stream-voc")) == 0
        assert len(app.query("#btn-stream-inst")) == 0
        assert len(app.query("#wb-btn-neural-toggle")) == 0
        assert len(app.query("#wb-btn-models-download")) == 0

        # Track Info modal opens and dispatches upkeep actions.
        wb.open_track_info()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, TrackInfoScreen)
        body = str(screen.query_one("#ti-body").render())
        assert "Models" in body

        with patch.object(wb, "trigger_models_download") as mock_dl:
            screen.query_one("#ti-models", Button).press()
            await pilot.pause()
            mock_dl.assert_called_once()

        # Test trigger_models_download when models are already cached — shows all engines
        with (
            patch("harvester.services.model_manager.ModelManager.is_cached", return_value=True),
            patch("importlib.util.find_spec", return_value=object()),
        ):
            wb.trigger_models_download()
            status_label = app.query_one("#wb-status")
            status_text = str(status_label.render())
            assert "AI Model Registry" in status_text
            assert "BS-RoFormer" in status_text
            assert "HDEMUCS" in status_text
            assert "DeReverb" in status_text
            assert "FlashSR" in status_text

        # Test trigger_models_download when demucs is missing triggers background install worker
        with (
            patch("harvester.services.model_manager.ModelManager.is_cached", return_value=True),
            patch("importlib.util.find_spec", return_value=None),
            patch.object(wb, "run_worker") as mock_worker,
        ):
            wb.trigger_models_download()
            mock_worker.assert_called_once()


async def test_preset_select_offers_all_presets_and_switches_immediately(tmp_path: Path) -> None:
    """Every preset is always selectable; switching routes the pre-rendered ENH file."""
    from textual.widgets import Select

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)
        sel = app.query_one("#wb-preset-select", Select)
        btn_enh = app.query_one("#btn-stream-enh", Button)

        assert wb.neural_enabled is True
        option_ids = [opt[1] for opt in sel._options if opt[1] != Select.NULL]
        assert option_ids == [
            "conservative",
            "fast_balanced",
            "de_sizzle",
            "extended_air",
            "narrow_stereo",
        ]
        assert wb.selected_preset_id == "conservative"

        dummy_mp3 = tmp_path / "track.mp3"
        dummy_mp3.write_bytes(b"base-audio")
        wb.path_mp3 = dummy_mp3

        enh_files = {}
        for pid in ["de_sizzle", "extended_air", "narrow_stereo"]:
            enh_file = wb.audition_cache_dir / f"{dummy_mp3.stem}_{pid}_neural.mp3"
            enh_file.parent.mkdir(parents=True, exist_ok=True)
            enh_file.write_bytes(f"audio-{pid}".encode())
            enh_files[pid] = enh_file

        btn_enh.press()
        await pilot.pause()
        assert wb.active_stream == "ENH"

        for pid in ["de_sizzle", "extended_air", "narrow_stereo"]:
            sel.value = pid
            await pilot.pause()
            assert wb.selected_preset_id == pid
            assert wb.path_enh == enh_files[pid]
            assert player.current_track == enh_files[pid]


async def test_workbench_dead_space_elements_and_cached_download(tmp_path: Path) -> None:
    """Verify that:
    1. The signal chain pipeline and telemetry grid fill the workbench inspector space.
    2. Download button leverages the audition cache for instant atomic export.
    """
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        out_dir = tmp_path / "music_out"
        out_dir.mkdir()
        dummy_mp3 = out_dir / "mysong.mp3"
        dummy_mp3.write_bytes(b"original-mp3-stream")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.id = "job-telemetry-test"
        job.output_path = dummy_mp3
        job.spectral.cutoff_hz = 15800.0

        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        # Verify visualizer is 10-band
        vis = app.query_one("#wb-visualizer", AudioVisualizer)
        assert vis.num_bands == 10

        # Verify download progress bar exists
        pb = app.query_one("#wb-download-progress", ProgressBar)
        assert pb is not None
        assert pb.total == 100.0

        # 1. Verify signal chain pipeline widgets
        chain_title = app.query_one("#wb-chain-title")
        assert "SIGNAL CHAIN PIPELINE" in str(chain_title.render())

        chain_flow = app.query_one("#wb-chain-flow")
        assert "1. Baseband" in str(chain_flow.render())
        assert "5. Limiter" in str(chain_flow.render())

        chain_detail = app.query_one("#wb-chain-detail")
        assert "Engine:" in str(chain_detail.render())
        assert "Status:" in str(chain_detail.render())

        # 2. Verify telemetry grid widgets
        telem_title = app.query_one("#wb-telemetry-title")
        assert "HARMONIC MASTERING TELEMETRY" in str(telem_title.render())

        telem_nyquist = app.query_one("#wb-telem-nyquist")
        assert "22.05 kHz" in str(telem_nyquist.render())

        telem_crossover = app.query_one("#wb-telem-crossover")
        assert "384-tap FIR" in str(telem_crossover.render())

        telem_passthrough = app.query_one("#wb-telem-passthrough")
        assert "Bit-Exact" in str(telem_passthrough.render())

        telem_limiter = app.query_one("#wb-telem-limiter")
        assert "Limiter Ceiling" in str(telem_limiter.render())

        telem_format = app.query_one("#wb-telem-format")
        assert "320 kbps" in str(telem_format.render())

        # 3. Simulate pre-rendered audition cache for fast download
        mode_tag = "neural" if wb.neural_enabled else "eco"
        cache_file = (
            wb.audition_cache_dir / f"{dummy_mp3.stem}_{wb.selected_preset_id}_{mode_tag}.mp3"
        )
        cache_file.write_bytes(b"A" * 2048)  # Valid pre-rendered cache

        target_file = out_dir / f"{dummy_mp3.stem}.enhanced.mp3"
        assert not target_file.exists()

        # Download should perform instant atomic copy from cache without
        # invoking export_enhanced_derivative
        with patch.object(wb.exporter, "export_enhanced_derivative") as mock_render:
            btn_dl = app.query_one("#wb-btn-export", Button)
            btn_dl.press()
            for _ in range(25):
                await pilot.pause(0.05)
                if target_file.exists() and "Downloaded" in str(
                    app.query_one("#wb-status").render()
                ):
                    break

            mock_render.assert_not_called()

        assert target_file.exists()
        assert target_file.read_bytes() == b"A" * 2048
        status = app.query_one("#wb-status")
        assert "Downloaded" in str(status.render())


async def test_workbench_paging_and_10band_eq(tmp_path: Path) -> None:
    """Verify Workbench 2-page system and interactive 10-band equalizer."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "eq_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.id = "job-eq-test"
        job.output_path = dummy_mp3
        job.spectral.cutoff_hz = 15500.0

        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        # 1. Verify initial state is Deck page
        assert wb.active_page == "deck"
        page_deck = app.query_one("#wb-page-deck")
        page_eq = app.query_one("#wb-page-eq")
        assert page_deck.styles.display != "none"
        assert page_eq.styles.display == "none"

        # Inner page-switch buttons removed; navigation is via top nav bar.
        # Verify page visibility state only.

        # 2. Switch to 10-Band EQ page
        wb.switch_page("eq")
        await pilot.pause()

        assert wb.active_page == "eq"
        assert page_deck.styles.display == "none"
        assert page_eq.styles.display != "none"

        # 3. Test EQ Band adjustments (+/-)
        val_16k = app.query_one("#wb-eq-val-16000", Label)
        assert "0.0dB" in str(val_16k.render())

        btn_up_16k = app.query_one("#wb-eq-up-16000", Button)
        with patch.object(wb, "_schedule_eq_render"):
            btn_up_16k.press()
            await pilot.pause()
            assert wb.eq_settings.bands[16000] == 1.0
            assert "+1.0dB" in str(val_16k.render())

            btn_up_16k.press()
            await pilot.pause()
            assert wb.eq_settings.bands[16000] == 2.0
            assert "+2.0dB" in str(val_16k.render())

            btn_dn_16k = app.query_one("#wb-eq-dn-16000", Button)
            btn_dn_16k.press()
            await pilot.pause()
            assert wb.eq_settings.bands[16000] == 1.0
            assert "+1.0dB" in str(val_16k.render())

        # 4. Test HPF toggle
        btn_hpf = app.query_one("#wb-btn-eq-hpf", Button)
        assert "HPF 30Hz: OFF" in str(btn_hpf.label)
        with patch.object(wb, "_schedule_eq_render"):
            btn_hpf.press()
            await pilot.pause()
            assert wb.eq_settings.hpf_30hz is True
            assert "HPF 30Hz: ON" in str(btn_hpf.label)

        # 5. Test Trim cycle
        btn_trim = app.query_one("#wb-btn-eq-trim", Button)
        assert "TRIM: 0.0dB" in str(btn_trim.label)
        with patch.object(wb, "_schedule_eq_render"):
            btn_trim.press()
            await pilot.pause()
            assert wb.eq_settings.output_trim_db == -1.0
            assert "TRIM: -1.0dB" in str(btn_trim.label)

        # 6. Test +3dB Air button
        btn_air = app.query_one("#wb-btn-eq-air", Button)
        with patch.object(wb, "_schedule_eq_render"):
            btn_air.press()
            await pilot.pause()
            assert wb.eq_settings.bands[16000] == 4.0
            assert "+4.0dB" in str(val_16k.render())

        # 7. Test Bypass toggle
        btn_toggle = app.query_one("#wb-btn-eq-toggle", Button)
        assert "EQ: ENGAGED" in str(btn_toggle.label)
        with patch.object(wb, "_schedule_eq_render"):
            btn_toggle.press()
            await pilot.pause()
            assert wb.eq_settings.enabled is False
            assert "EQ: BYPASS" in str(btn_toggle.label)

            btn_toggle.press()
            await pilot.pause()
            assert wb.eq_settings.enabled
            assert "EQ: ENGAGED" in str(btn_toggle.label)

        # 8. Test Reset Flat
        btn_reset = app.query_one("#wb-btn-eq-reset", Button)
        with patch.object(wb, "_schedule_eq_render"):
            btn_reset.press()
            await pilot.pause()
            assert wb.eq_settings.bands[16000] == 0.0
            assert wb.eq_settings.output_trim_db == 0.0
            assert "0.0dB" in str(val_16k.render())

        # 9. Test Preset selection (tasteful master bank)
        sel_preset = app.query_one("#wb-eq-preset-select", Select)
        with patch.object(wb, "_schedule_eq_render"):
            sel_preset.value = "Air"
            await pilot.pause()
            assert wb.eq_settings.preset_name == "Air"
            assert wb.eq_settings.bands[16000] == 2.5
            assert "+2.5dB" in str(val_16k.render())

        # 10. Target switching: bank swap, per-target memory, stem hint
        sel_target = app.query_one("#wb-eq-target-select", Select)
        task_status = app.query_one("#wb-task-status", Label)
        sel_target.value = "vocals"
        await pilot.pause()
        assert wb.eq_target == "vocals"
        assert wb.active_stream not in ("VOC", "INST")
        assert "No separated vocals yet" in str(task_status.render())
        assert "VOCALS" in str(app.query_one("#wb-eq-title", Label).render())
        vocal_options = [opt[1] for opt in sel_preset._options if opt[1] != Select.NULL]
        assert vocal_options == list(EQ_PRESET_BANKS["vocals"])
        with patch.object(wb, "_schedule_eq_render"):
            sel_preset.value = "Tame Sibilance"
            await pilot.pause()
        assert wb.eq_settings_by_target["vocals"].bands[8000] == -2.0

        sel_target.value = "master"
        await pilot.pause()
        assert wb.eq_target == "master"
        assert wb.eq_settings is wb.eq_settings_by_target["master"]
        assert wb.eq_settings.preset_name == "Air"
        assert wb.eq_settings.bands[16000] == 2.5  # master curve remembered

        sel_target.value = "vocals"
        await pilot.pause()
        assert wb.eq_settings.preset_name == "Tame Sibilance"  # vocal curve remembered
        sel_target.value = "master"
        await pilot.pause()

        # 11. Switch back to Deck page
        wb.switch_page("deck")
        await pilot.pause()
        assert wb.active_page == "deck"
        assert page_deck.styles.display != "none"
        assert page_eq.styles.display == "none"


async def test_realtime_eq_player_synchronization(tmp_path: Path) -> None:
    """Verify that EQ adjustments update the player's live audio filter
    across both MP3 and ENH streams.
    """
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)

        dummy_mp3 = tmp_path / "sync_eq_test.mp3"
        dummy_mp3.write_bytes(b"dummy-audio-content")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.id = "job-sync-eq"
        job.output_path = dummy_mp3
        job.spectral.cutoff_hz = 15000.0

        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        # 1. Initially flat on MP3 stream -> no filter
        assert wb.active_stream == "MP3"
        assert player.audio_filter == ""

        # 2. Boost 31Hz and 63Hz bass bands while on MP3
        btn_up_31 = app.query_one("#wb-eq-up-31", Button)
        btn_up_31.press()
        await pilot.pause()
        assert "equalizer=f=31:width_type=o:w=1:g=1.00" in player.audio_filter

        btn_up_63 = app.query_one("#wb-eq-up-63", Button)
        btn_up_63.press()
        await pilot.pause()
        assert "equalizer=f=31:width_type=o:w=1:g=1.00" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=1.00" in player.audio_filter

        # 3. Switch stream to ENH -> active EQ filter must be preserved!
        btn_enh = app.query_one("#btn-stream-enh", Button)
        btn_enh.press()
        await pilot.pause()
        assert wb.active_stream == "ENH"
        assert "equalizer=f=31:width_type=o:w=1:g=1.00" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=1.00" in player.audio_filter

        # 4. Apply the 'Smile' preset while on ENH
        sel_preset = app.query_one("#wb-eq-preset-select", Select)
        sel_preset.value = "Smile"
        await pilot.pause()
        assert "equalizer=f=31:width_type=o:w=1:g=1.00" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=1.50" in player.audio_filter

        # 5. Switch back to MP3 -> active EQ filter must still apply!
        btn_mp3 = app.query_one("#btn-stream-mp3", Button)
        btn_mp3.press()
        await pilot.pause()
        assert wb.active_stream == "MP3"
        assert "equalizer=f=31:width_type=o:w=1:g=1.00" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=1.50" in player.audio_filter

        # 6. Toggle HPF 30Hz
        btn_hpf = app.query_one("#wb-btn-eq-hpf", Button)
        btn_hpf.press()
        await pilot.pause()
        assert "highpass=f=30" in player.audio_filter

        # 7. Reset Flat -> audio filter clears back to empty
        btn_reset = app.query_one("#wb-btn-eq-reset", Button)
        btn_reset.press()
        await pilot.pause()
        assert player.audio_filter == ""


@pytest.mark.asyncio
async def test_workbench_multi_song_stem_isolation(tmp_path: Path) -> None:
    """Verify workbench preserves stem paths per track across job switches."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)

        track_1 = tmp_path / "track_1.mp3"
        track_1.write_bytes(b"TRACK1AUDIO" * 200)
        job_1 = TrackJob(mode=Mode.SINGLE_URL, input_path=track_1)
        job_1.output_path = track_1

        track_2 = tmp_path / "track_2.mp3"
        track_2.write_bytes(b"TRACK2AUDIO" * 200)
        job_2 = TrackJob(mode=Mode.SINGLE_URL, input_path=track_2)
        job_2.output_path = track_2

        # Mock cache directories for track 1 and track 2
        cache_dir_1 = (
            Path.home()
            / ".cache"
            / "omnirip"
            / "stems"
            / f"{track_1.stem}_{track_1.stat().st_size}"
        )
        cache_dir_2 = (
            Path.home()
            / ".cache"
            / "omnirip"
            / "stems"
            / f"{track_2.stem}_{track_2.stat().st_size}"
        )
        cache_dir_1.mkdir(parents=True, exist_ok=True)
        cache_dir_2.mkdir(parents=True, exist_ok=True)

        voc_1 = cache_dir_1 / f"{track_1.stem}_neural_vocals.wav"
        inst_1 = cache_dir_1 / f"{track_1.stem}_neural_instrumental.wav"
        voc_1.write_bytes(b"VOC1")
        inst_1.write_bytes(b"INST1")

        voc_2 = cache_dir_2 / f"{track_2.stem}_neural_vocals.wav"
        inst_2 = cache_dir_2 / f"{track_2.stem}_neural_instrumental.wav"
        voc_2.write_bytes(b"VOC2")
        inst_2.write_bytes(b"INST2")

        # Load Track 1
        wb.load_job(job_1)
        await pilot.pause()
        assert wb.path_voc == voc_1
        assert wb.path_inst == inst_1

        # Switch to Track 2
        wb.load_job(job_2)
        await pilot.pause()
        assert wb.path_voc == voc_2
        assert wb.path_inst == inst_2

        # Switch back to Track 1
        wb.load_job(job_1)
        await pilot.pause()
        assert wb.path_voc == voc_1
        assert wb.path_inst == inst_1


@pytest.mark.asyncio
async def test_workbench_dedicated_visuals_page_and_app_navigation(tmp_path: Path):
    """Verify dedicated visuals page, visualizer isolation, and app navigation."""
    from harvester.config import load_config
    from harvester.ui.app import HarvesterApp

    dummy_mp3 = tmp_path / "nav_test.mp3"
    dummy_mp3.write_bytes(b"\xff\xfb\x90\x44" + b"\x00" * 1024)

    cfg = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    app = HarvesterApp(cfg, auto_startup=False)
    async with app.run_test() as pilot:
        wb = app.query_one(WorkbenchWidget)
        page_vis = app.query_one("#wb-page-vis")
        page_deck = app.query_one("#wb-page-deck")
        # Inner page-switch buttons removed; navigation is via top nav bar.

        # 1. Initially on DECK page, VISUALS page is hidden
        assert wb.active_page == "deck"
        assert page_deck.styles.display != "none"
        assert page_vis.styles.display == "none"

        # 2. Switch to VISUALS page via switch_page
        wb.switch_page("vis")
        await pilot.pause()
        assert wb.active_page == "vis"
        assert page_vis.styles.display != "none"
        assert page_deck.styles.display == "none"

        # 3. Verify all 5 visualizer engines exist inside wb-page-vis
        assert app.query_one("#wb-visualizer", AudioVisualizer) is not None
        assert app.query_one("#wb-vis-osc", AudioVisualizer) is not None
        assert app.query_one("#wb-vis-mir", AudioVisualizer) is not None
        assert app.query_one("#wb-vis-braille", AudioVisualizer) is not None
        assert app.query_one("#wb-vis-vu", AudioVisualizer) is not None

        # 4. Top-level app nav bar tests
        btn_nav_tracks = app.query_one("#btn-nav-tracks", Button)
        btn_nav_vis = app.query_one("#btn-nav-vis", Button)
        tracks_pane = app.query_one("#tracks-pane")
        wb_pane = app.query_one("#workbench-pane")

        # Switch to TRACKS via top nav
        btn_nav_tracks.press()
        await pilot.pause()
        assert tracks_pane.styles.display != "none"
        assert wb_pane.styles.display == "none"
        assert "app-nav-active" in btn_nav_tracks.classes

        # Switch to VISUALIZER via top nav
        btn_nav_vis.press()
        await pilot.pause()
        assert tracks_pane.styles.display == "none"
        assert wb_pane.styles.display != "none"
        assert wb.active_page == "vis"
        assert "app-nav-active" in btn_nav_vis.classes
@pytest.mark.asyncio
async def test_workbench_credits_lookup_chain_and_miss(tmp_path: Path, monkeypatch):
    """The CREDITS button: AcoustID → mb_recording_id → credits → annotated plan."""
    from harvester.services import acoustid as acoustid_mod
    from harvester.services import musicbrainz as mb_mod
    from harvester.services.musicbrainz import Credit, RecordingCredits

    dummy_mp3 = tmp_path / "chain.mp3"
    dummy_mp3.write_bytes(b"mp3-data")

    calls: dict[str, object] = {}

    class _FakeAcoustid:
        configured = True

        def __init__(self, config: object) -> None:
            pass

        async def identify(self, path: Path) -> object:
            return calls.get("meta")

        async def close(self) -> None:
            pass

    class _FakeCoverArt:
        def __init__(self, config: object) -> None:
            pass

        async def fetch_recording_credits(self, mbid: str) -> RecordingCredits:
            calls["mbid"] = mbid
            return RecordingCredits(
                recording_id=mbid,
                title="Headlock",
                instruments=(Credit(name="double bass", artist="Mich Gerber"),),
                vocals=(Credit(name="lead vocals", artist="Imogen Heap"),),
            )

        async def close(self) -> None:
            pass

    monkeypatch.setattr(acoustid_mod, "AcoustidService", _FakeAcoustid)
    monkeypatch.setattr(mb_mod, "CoverArtService", _FakeCoverArt)

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(
                TrackJob(
                    mode=Mode.SINGLE_URL,
                    input_path=tmp_path / "src.opus",
                    output_path=dummy_mp3,
                )
            )
        await pilot.pause()

        # Miss: AcoustID returns nothing → a clear note, no crash.
        calls["meta"] = None
        await wb._async_fetch_credits(dummy_mp3)
        await pilot.pause()
        assert "no MusicBrainz recording id" in str(wb.query_one("#wb-task-status", Label).render())

        # Hit: metadata carries mb_recording_id → credits annotate the plan.
        from types import SimpleNamespace

        calls["meta"] = SimpleNamespace(mb_recording_id="d871b5ab")
        await wb._async_fetch_credits(dummy_mp3)
        await pilot.pause()

        assert calls["mbid"] == "d871b5ab"
        credits = wb.recording_credits
        assert credits is not None
        assert credits.singer_count == 1
        rendered = str(wb.query_one("#wb-task-status", Label).render())
        assert "Mich Gerber" in rendered


@pytest.mark.asyncio
async def test_workbench_tagging_pass_reports_tags(tmp_path: Path, monkeypatch):
    """NEURAL FULL tags are reported in the LAYERS status line."""
    from harvester.analysis.enhancement import tags as tags_mod

    dummy_mp3 = tmp_path / "tagged.mp3"
    dummy_mp3.write_bytes(b"mp3-data")
    calls: list[tuple[Path, Path]] = []

    class _FakeTagger:
        def __init__(self, **kwargs: object) -> None:
            pass

        def tag_and_store(
            self, path: Path, stem_dir: Path, progress_callback: object = None
        ) -> tags_mod.TagResult:
            calls.append((Path(path), Path(stem_dir)))
            return tags_mod.TagResult(labels=("strings",), scores={"strings": 0.51}, windows=2)

    monkeypatch.setattr(tags_mod, "ClapTagger", _FakeTagger)

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        # The pass only reports for the loaded track (generation guard).
        wb.load_job(
            TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        )
        wb.switch_page("layers")
        await wb._run_tagging_pass(dummy_mp3, tmp_path / "stems")
        await pilot.pause()

        assert calls == [(dummy_mp3, tmp_path / "stems")]
        assert "strings 0.51" in str(wb.query_one("#wb-task-status", Label).render())


@pytest.mark.asyncio
async def test_workbench_tagging_pass_degrades_without_the_model(tmp_path: Path, monkeypatch):
    """An unavailable CLAP model leaves the lanes untouched and says so."""
    from harvester.analysis.enhancement import tags as tags_mod

    class _MissingTagger:
        def __init__(self, **kwargs: object) -> None:
            pass

        def tag_and_store(self, *args: object, **kwargs: object) -> None:
            return None

    dummy_mp3 = tmp_path / "tagged.mp3"
    dummy_mp3.write_bytes(b"mp3-data")
    monkeypatch.setattr(tags_mod, "ClapTagger", _MissingTagger)

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        # The pass only reports for the loaded track (generation guard).
        wb.load_job(
            TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        )
        wb.switch_page("layers")
        await wb._run_tagging_pass(dummy_mp3, tmp_path / "stems")
        await pilot.pause()
        assert "Tags unavailable" in str(wb.query_one("#wb-task-status", Label).render())


@pytest.mark.asyncio
async def test_workbench_hosted_separation_reports_a_missing_key(tmp_path: Path, monkeypatch):
    """HOSTED SEPARATE is opt-in per track: no key → a message, no upload (D26)."""
    from harvester.services.mvsep import MvsepClient

    dummy_mp3 = tmp_path / "hosted_nokey.mp3"
    dummy_mp3.write_bytes(b"mp3-data")
    monkeypatch.setattr(MvsepClient, "available", property(lambda self: False))

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(
            TrackJob(
                mode=Mode.SINGLE_URL,
                input_path=tmp_path / "src.opus",
                output_path=dummy_mp3,
            )
        )
        wb.switch_page("layers")
        await pilot.pause()

        # The confirmation screen is bypassed in this test: pressing the
        # button only stages the screen, and the upload runs after YES.
        wb._launch_hosted_run("vocals")
        await pilot.pause(0.2)

        status = str(wb.query_one("#wb-task-status", Label).render())
        assert "MVSEP_API_KEY" in status
        assert wb._hosted_task_running is False


@pytest.mark.asyncio
async def test_workbench_speakers_are_advisory_and_credits_win(tmp_path: Path, monkeypatch):
    """MEASURE VOICES records the measured count but never overwrites credits (D27)."""
    from harvester.services import diarization as dia_mod
    from harvester.services.musicbrainz import Credit, RecordingCredits

    dummy_mp3 = tmp_path / "speakers.mp3"
    dummy_mp3.write_bytes(b"mp3-data")
    calls: dict[str, object] = {}

    class _FakeDiarizer:
        def diarize(self, audio, *, max_seconds=0.0, progress=None, num_speakers=None):
            calls["audio"] = audio
            calls["max_seconds"] = max_seconds
            if progress is not None:
                progress(100.0, "done")
            return dia_mod.DiarizationResult(
                speakers=("SPEAKER_00", "SPEAKER_01", "SPEAKER_02"),
                turns=(
                    dia_mod.SpeakerTurn(0.0, 1.0, "SPEAKER_00"),
                    dia_mod.SpeakerTurn(1.0, 2.0, "SPEAKER_01"),
                ),
                model="pyannote/fake",
                elapsed_s=1.0,
            )

    monkeypatch.setattr(dia_mod, "Diarizer", _FakeDiarizer)
    monkeypatch.setattr(dia_mod, "pyannote_available", lambda: True)

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.load_job(
            TrackJob(
                mode=Mode.SINGLE_URL,
                input_path=tmp_path / "src.opus",
                output_path=dummy_mp3,
            )
        )
        wb.recording_credits = RecordingCredits(
            recording_id="mbid",
            title="Headlock",
            vocals=(Credit(name="lead vocals", artist="Imogen Heap"),),
            instruments=(Credit(name="double bass", artist="Mich Gerber"),),
        )
        await pilot.pause()

        wb._start_diarization()
        await pilot.pause(0.3)

        assert wb.measured_speakers == 3
        status = str(wb.query_one("#wb-task-status", Label).render())
        assert "3" in status and "authoritative" in status
        assert wb._diarize_task_running is False


async def test_stream_controls_show_only_on_the_deck_page() -> None:
    """The MP3/ENH buttons, preset select and save button belong to the DECK page."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        await pilot.pause()
        assert wb.query_one("#wb-stream-row").styles.display != "none"
        assert wb.query_one("#wb-controls-row").styles.display != "none"

        for page in ("eq", "repair", "vis"):
            wb.switch_page(page)
            await pilot.pause()
            assert wb.query_one("#wb-stream-row").styles.display == "none", page
            assert wb.query_one("#wb-controls-row").styles.display == "none", page

        wb.switch_page("deck")
        await pilot.pause()
        assert wb.query_one("#wb-stream-row").styles.display != "none"
        assert wb.query_one("#wb-controls-row").styles.display != "none"


async def test_eq_target_routes_to_separated_stems(tmp_path: Path) -> None:
    """Choosing VOCALS/INSTRUMENTAL auditions that stem, or explains how to get one."""
    import numpy as np
    import soundfile as sf

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)
        dummy_mp3 = tmp_path / "route_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        # No stems yet: a clear hint, no exception (regression for the removed separator call).
        wb.set_active_stream("VOC")
        await pilot.pause()
        hint = str(wb.query_one("#wb-task-status", Label).render())
        assert "No separated vocals yet" in hint

        # With stems on disk the target routes playback to them.
        t = np.linspace(0, 1.0, 44100, endpoint=False)
        vocals = tmp_path / "route_song_ensemble_vocals.wav"
        inst = tmp_path / "route_song_ensemble_instrumental.wav"
        sf.write(vocals, np.stack([0.2 * np.sin(2 * np.pi * 440 * t)] * 2, axis=1), 44100)
        sf.write(inst, np.stack([0.2 * np.sin(2 * np.pi * 220 * t)] * 2, axis=1), 44100)
        wb.path_voc = vocals
        wb.path_inst = inst

        sel_target = app.query_one("#wb-eq-target-select", Select)
        sel_target.value = "vocals"
        await pilot.pause()
        assert wb.active_stream == "VOC"
        assert player.current_track == vocals

        sel_target.value = "instrumental"
        await pilot.pause()
        assert wb.active_stream == "INST"
        assert player.current_track == inst

        sel_target.value = "master"
        await pilot.pause()
        assert wb.eq_target == "master"
        assert wb.active_stream in ("MP3", "ENH")


def test_nav_keys_put_eq_last_and_repair_uses_theme_icon() -> None:
    from harvester.ui.app import HarvesterApp

    bindings = {key: action for key, action, _desc in HarvesterApp.BINDINGS}
    assert bindings["f4"] == "nav_page_repair"
    assert bindings["f5"] == "nav_page_eq"


async def test_stem_export_bakes_matching_target_eq(tmp_path: Path) -> None:
    """_write_stem_with_eq: flat curves copy bytes, non-flat curves shape the stem."""
    import numpy as np
    import soundfile as sf

    app = WorkbenchTestApp()
    async with app.run_test():
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        sr = 48000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        source = tmp_path / "vocal_in.wav"
        sf.write(source, np.stack([0.2 * np.sin(2 * np.pi * 1000 * t)] * 2, axis=1), sr)

        flat_out = tmp_path / "vocal_flat.wav"
        await asyncio.to_thread(wb._write_stem_with_eq, source, flat_out, "vocals")
        assert flat_out.read_bytes() == source.read_bytes()

        wb.eq_settings_by_target["vocals"].set_band(1000, 6.0)
        shaped_out = tmp_path / "vocal_shaped.wav"
        await asyncio.to_thread(wb._write_stem_with_eq, source, shaped_out, "vocals")
        original, _ = sf.read(str(source), dtype="float32", always_2d=True)
        shaped, _ = sf.read(str(shaped_out), dtype="float32", always_2d=True)
        assert float(np.max(np.abs(shaped - original))) > 0.01


async def test_eq_custom_edits_survive_target_switching(tmp_path: Path) -> None:
    """A manually tweaked curve is not wiped when switching targets and back."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        sel_target = app.query_one("#wb-eq-target-select", Select)
        sel_preset = app.query_one("#wb-eq-preset-select", Select)

        sel_target.value = "vocals"
        await pilot.pause()
        with patch.object(wb, "_schedule_eq_render"):
            app.query_one("#wb-eq-up-2000", Button).press()
            await pilot.pause()
        assert wb.eq_settings.preset_name == "Custom"
        assert wb.eq_settings.bands[2000] == 1.0
        assert sel_preset.value is Select.NULL

        sel_target.value = "master"
        await pilot.pause()
        sel_target.value = "vocals"
        await pilot.pause()
        assert wb.eq_settings.preset_name == "Custom"
        assert wb.eq_settings.bands[2000] == 1.0


async def test_stem_export_without_stems_never_falls_back_to_master(tmp_path: Path) -> None:
    from unittest.mock import patch as _patch

    from harvester.analysis.enhancement.presets import PRESETS

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "no_stem_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with _patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)
        wb.path_voc = None
        wb._export_mode = "VOC"

        with _patch.object(wb.app, "notify") as notify:
            await wb._async_export(wb.path_mp3, PRESETS["conservative"])
            await pilot.pause()

        assert notify.called
        assert "No separated vocals to export" in str(notify.call_args[0][0])
        assert not (tmp_path / f"{wb.path_mp3.stem}_vocals.wav").exists()
        assert not (tmp_path / f"{wb.path_mp3.stem}.enhanced.mp3").exists()


async def test_export_menu_offers_lossless_masters(tmp_path: Path) -> None:
    """The deck export menu routes WAV/FLAC masters and relabels the save button."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        labels = {button.id: str(button.label) for button in app.query(".wb-export-choice")}
        assert "Enhanced WAV (24-bit)" in labels["wb-export-choose-wav"]
        assert "Enhanced FLAC (24-bit)" in labels["wb-export-choose-flac"]

        with patch.object(wb, "_export_derivative") as export:
            app.query_one("#wb-export-choose-flac", Button).press()
            await pilot.pause()
        assert wb._export_mode == "ENH_FLAC"
        export.assert_called_once()
        assert "SAVE FLAC" in str(app.query_one("#wb-btn-export", Button).label)


async def test_lossless_export_renders_master(tmp_path: Path) -> None:
    """ENH_WAV/ENH_FLAC modes write a lossless master through the exporter."""
    from harvester.analysis.enhancement.presets import PRESETS

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "lossless_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)
        wb._export_mode = "ENH_WAV"
        wb.genre_mode = "hip_hop_trap"
        wb._apply_genre_mode(rerender=False)

        def _fake_lossless(**kwargs):
            out = Path(kwargs["output_path"])
            out.write_bytes(b"RIFF")
            return out

        with patch.object(
            wb.exporter, "export_enhanced_lossless", side_effect=_fake_lossless
        ) as lossless:
            await wb._async_export(wb.path_mp3, PRESETS["conservative"])
            await pilot.pause()

        assert lossless.called
        assert lossless.call_args.kwargs["fmt"] == "wav"
        sent_eq = lossless.call_args.kwargs["eq_settings"]
        assert sent_eq.bands[63] > 0  # genre colour rides on the lossless master
        assert lossless.call_args.kwargs["extra_tags"]["GENRE"] == "hip_hop_trap"
        assert (tmp_path / "lossless_song.enhanced.wav").exists()


async def test_genre_auto_detection_sets_recipe_and_choice(tmp_path: Path) -> None:
    """Tags detected on load land in the Auto option, the choice and the recipe line."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "genre_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        job.orig_tags = {"genre": "Hip-Hop/Trap"}
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)
        await pilot.pause()

        assert wb.genre_mode == "auto"
        assert wb._genre_choice.keys == ("hip_hop_trap",)
        select = app.query_one("#wb-genre-select", Select)
        auto_label = next(label for label, key in select._options if key == "auto")
        assert "Hip-Hop" in str(auto_label)
        recipe = str(app.query_one("#wb-genre-recipe", Label).render())
        assert "Hip-Hop" in recipe and "63 Hz" in recipe


async def test_genre_select_and_intensity_shape_playback(tmp_path: Path) -> None:
    """Choosing a genre and a stronger intensity changes the live EQ filter."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)
        dummy_mp3 = tmp_path / "genre_live.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)
        await pilot.pause()

        sel_genre = app.query_one("#wb-genre-select", Select)
        sel_intensity = app.query_one("#wb-genre-intensity", Select)
        with patch.object(wb, "_schedule_eq_render"):
            sel_genre.value = "house"
            await pilot.pause()
            assert wb.genre_mode == "house"
            assert "equalizer=f=63:width_type=o:w=1:g=0.90" in player.audio_filter

            sel_intensity.value = "bold"
            await pilot.pause()
            assert wb.genre_intensity == "bold"
            assert "equalizer=f=63:width_type=o:w=1:g=2.10" in player.audio_filter

        assert "Bold" in str(app.query_one("#wb-genre-recipe", Label).render())


async def test_genre_musicbrainz_refines_only_in_auto_mode(tmp_path: Path) -> None:
    """MB genres refine the auto suggestion; a manual pick is never overridden."""
    from harvester.services.musicbrainz import RecordingCredits

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "genre_mb.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        credits = RecordingCredits(
            recording_id="mbid",
            genres=(("trap", 4), ("hip hop", 2), ("pop", 1)),
        )
        with patch(
            "harvester.services.musicbrainz.CoverArtService.fetch_recording_credits",
            return_value=credits,
        ):
            await wb._async_genre_from_musicbrainz("mbid", wb.track_generation)
        await pilot.pause()
        assert wb._genre_detected.keys[:2] == ("hip_hop_trap", "pop")

        wb.genre_mode = "jazz"
        wb._apply_genre_mode(rerender=False)
        await wb._async_genre_from_musicbrainz("mbid", wb.track_generation)
        assert wb.genre_mode == "jazz"
        assert wb._genre_choice.keys == ("jazz",)


async def test_genre_mix_modal_flow(tmp_path: Path) -> None:
    """The Mix… entry opens the modal and the chosen keys become the manual mix."""
    from harvester.ui.genre_mix import GenreMixScreen

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "genre_mix.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        with patch.object(wb, "_schedule_eq_render"):
            app.query_one("#wb-genre-select", Select).value = "mix"
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, GenreMixScreen)
            screen.query_one("#genre-mix-list", SelectionList).select("house")
            screen.query_one("#genre-mix-list", SelectionList).select("techno")
            screen.query_one("#genre-mix-apply", Button).press()
            await pilot.pause()

        assert wb.genre_mode == "mix"
        assert wb._genre_choice.keys == ("house", "techno")
        assert abs(wb._genre_choice.mix[0][1] - 0.5) < 1e-9


async def test_async_export_applies_genre_effective_master_preset_policy(tmp_path: Path) -> None:
    """Deck export applies _effective_master_preset to lossless and derivative exports (Bug A)."""
    from harvester.analysis.enhancement.presets import PRESETS

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.audition_cache_dir = tmp_path / "audition"
        wb.audition_cache_dir.mkdir(parents=True, exist_ok=True)
        dummy_mp3 = tmp_path / "genre_export_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        wb.genre_mode = "house"
        wb._apply_genre_mode(rerender=False)
        base_preset = PRESETS["conservative"]
        expected_preset = wb._effective_master_preset(base_preset)

        # 1. MP3 cache-miss export path
        wb._export_mode = "MP3"
        with patch.object(
            wb.exporter, "export_enhanced_derivative", return_value=tmp_path / "out.mp3"
        ) as derivative:
            await wb._async_export(wb.path_mp3, base_preset)
            await pilot.pause()

        assert derivative.called
        mp3_passed = derivative.call_args.kwargs["preset"]
        assert mp3_passed.residual_stereo_width == expected_preset.residual_stereo_width
        assert mp3_passed.ceiling_dbfs == expected_preset.ceiling_dbfs

        # 2. Lossless export path
        wb._export_mode = "ENH_WAV"

        def _fake_lossless(**kwargs):
            out = Path(kwargs["output_path"])
            out.write_bytes(b"RIFF")
            return out

        with patch.object(
            wb.exporter, "export_enhanced_lossless", side_effect=_fake_lossless
        ) as lossless:
            await wb._async_export(wb.path_mp3, base_preset)
            await pilot.pause()

        assert lossless.called
        wav_passed = lossless.call_args.kwargs["preset"]
        assert wav_passed.residual_stereo_width == expected_preset.residual_stereo_width
        assert wav_passed.ceiling_dbfs == expected_preset.ceiling_dbfs


async def test_warm_remaining_presets_includes_eq_tag_and_genre_policy(tmp_path: Path) -> None:
    """Warm-cache pre-renders include the eq_tag in filename and pass effective preset and tags (Bug B)."""
    from harvester.analysis.enhancement.presets import PRESETS
    from harvester.ui.workbench import ECO_PRESET_OPTIONS

    app = WorkbenchTestApp()
    async with app.run_test():
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        wb.audition_cache_dir = tmp_path / "warm_audition"
        wb.audition_cache_dir.mkdir(parents=True, exist_ok=True)
        dummy_mp3 = tmp_path / "warm_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")
        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3, output_path=dummy_mp3)
        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        wb.neural_enabled = False
        wb.genre_mode = "house"
        wb._apply_genre_mode(rerender=False)

        eq_tag = wb._get_eq_cache_tag()
        assert eq_tag  # genre creates a non-empty cache tag

        calls: list[dict] = []

        def _fake_export(**kwargs):
            calls.append(kwargs)
            dest = Path(kwargs["output_path"])
            dest.write_bytes(b"rendered-mp3")
            return dest

        with patch.object(wb.exporter, "export_enhanced_derivative", side_effect=_fake_export):
            await wb._async_warm_remaining_presets(wb.path_mp3)

        expected_pids = [
            pid for _, pid in ECO_PRESET_OPTIONS if pid != wb.selected_preset_id
        ]
        assert len(calls) == len(expected_pids)
        for call_kw in calls:
            dest_path = Path(call_kw["output_path"])
            assert dest_path.name.endswith(f"{eq_tag}.mp3")
            eff = call_kw["preset"]
            base = PRESETS[eff.id]
            expected_eff = wb._effective_master_preset(base)
            assert eff.residual_stereo_width == expected_eff.residual_stereo_width
            assert eff.ceiling_dbfs == expected_eff.ceiling_dbfs
            assert call_kw["eq_settings"] == wb._master_eq_settings()
            assert call_kw["extra_tags"] == wb._genre_extra_tags()


async def test_report_panel_preview_and_export_handlers_with_empty_track(tmp_path: Path):
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        notifications: list[str] = []

        def fake_notify(msg, **kwargs):
            notifications.append(str(msg))

        wb.notify = fake_notify

        # Test calling preview with empty track does not crash
        for stream in ("original", "master", "vocals", "inst"):
            wb.on_report_panel_preview_requested(ReportPanel.PreviewRequested(stream))
        assert len(notifications) == 4
        assert all("No active track" in n for n in notifications)

        # Test calling export with empty track does not crash
        wb.on_report_panel_export_requested(ReportPanel.ExportRequested("wav"))
        assert any("No active track loaded to export" in n for n in notifications)

        # Test audition_stream directly
        wb.audition_stream("MP3")
        assert wb.active_stream == "MP3"


