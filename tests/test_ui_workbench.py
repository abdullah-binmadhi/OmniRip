"""Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player scrubber."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, ProgressBar, Select

from harvester.analysis.enhancement.acoustic_detector import AcousticAnalysisResult
from harvester.analysis.enhancement.stem_separator import VOCAL_REMEDIATIONS
from harvester.models import Mode, State, TrackJob
from harvester.ui.player import AudioPlayerWidget, InteractiveScrubber, StreamMonitorWidget
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

        # Switch to Neural AI Mode: reveals the 3 AI presets
        btn_neural = app.query_one("#wb-btn-neural-toggle", Button)
        btn_neural.press()
        await pilot.pause()
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


async def test_workbench_neural_toggle_and_models_button() -> None:
    """Verify that user can toggle between Eco DSP mode and Neural AI mode,
    and access the AI models download button."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        btn_toggle = app.query_one("#wb-btn-neural-toggle", Button)
        btn_download = app.query_one("#wb-btn-models-download", Button)
        engine_label = app.query_one("#wb-spec-engine")

        # Initially in Eco Mode (keeps device cool)
        assert wb.neural_enabled is False
        assert "ECO DSP" in str(btn_toggle.label)
        assert "Eco DSP" in str(engine_label.render())

        # Click to switch to Neural AI mode
        btn_toggle.press()
        await pilot.pause()

        assert wb.neural_enabled
        assert "NEURAL AI" in str(btn_toggle.label)
        assert "Neural AI" in str(engine_label.render())

        # Click again to switch back to Eco DSP mode
        btn_toggle.press()
        await pilot.pause()

        assert wb.neural_enabled is False
        assert "ECO DSP" in str(btn_toggle.label)
        assert "Eco DSP" in str(engine_label.render())

        # Models download button exists on Deck page
        assert "MODELS" in str(btn_download.label)
        with patch.object(wb, "trigger_models_download") as mock_dl:
            btn_download.press()
            await pilot.pause()
            mock_dl.assert_called_once()

        # Stems page AI models button also exists and triggers trigger_models_download
        wb.switch_page("stems")
        await pilot.pause()
        btn_stem_models = app.query_one("#wb-btn-stem-models", Button)
        assert "AI MODELS" in str(btn_stem_models.label)
        with patch.object(wb, "trigger_models_download") as mock_stem_dl:
            btn_stem_models.press()
            await pilot.pause()
            mock_stem_dl.assert_called_once()

        # Test trigger_models_download when models are already cached — shows all 4 models
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
            assert "NVSR" in status_text
            assert "FlashSR" in status_text

        # Test trigger_models_download when demucs is missing triggers background install worker
        with (
            patch("harvester.services.model_manager.ModelManager.is_cached", return_value=True),
            patch("importlib.util.find_spec", return_value=None),
            patch.object(wb, "run_worker") as mock_worker,
        ):
            wb.trigger_models_download()
            mock_worker.assert_called_once()


async def test_mode_dependent_presets_and_immediate_switching(tmp_path: Path) -> None:
    """Verify that:
    1. Eco Mode reveals only the first 2 options (Conservative DSP and Fast Neural).
    2. AI Mode reveals only the last 3 options (Milder Highs, Extended Air, Narrow Residual).
    3. Switching between the 3 AI options updates the audio stream and player immediately.
    """
    from textual.widgets import Select

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        player = app.query_one("#audio-player", AudioPlayerWidget)
        sel = app.query_one("#wb-preset-select", Select)
        btn_toggle = app.query_one("#wb-btn-neural-toggle", Button)
        btn_enh = app.query_one("#btn-stream-enh", Button)

        # 1. Initially in Eco Mode: only 2 options revealed
        assert wb.neural_enabled is False
        assert [opt[1] for opt in sel._options if opt[1] != Select.NULL] == [
            "conservative",
            "fast_balanced",
        ]
        assert wb.selected_preset_id == "conservative"

        # 2. Toggle to Neural AI Mode: reveals only the 3 AI options
        btn_toggle.press()
        await pilot.pause()

        assert wb.neural_enabled
        assert [opt[1] for opt in sel._options if opt[1] != Select.NULL] == [
            "de_sizzle",
            "extended_air",
            "narrow_stereo",
        ]
        assert wb.selected_preset_id in ("extended_air", "de_sizzle", "narrow_stereo")

        # 3. Setup mock audio and audition files for all 3 AI options
        dummy_mp3 = tmp_path / "track.mp3"
        dummy_mp3.write_bytes(b"base-audio")
        wb.path_mp3 = dummy_mp3

        ai_files = {}
        for pid in ["de_sizzle", "extended_air", "narrow_stereo"]:
            enh_file = wb.audition_cache_dir / f"{dummy_mp3.stem}_{pid}_neural.mp3"
            enh_file.parent.mkdir(parents=True, exist_ok=True)
            enh_file.write_bytes(f"audio-{pid}".encode())
            ai_files[pid] = enh_file

        # Activate ENH stream
        btn_enh.press()
        await pilot.pause()
        assert wb.active_stream == "ENH"

        # 4. Switch between the 3 AI options and verify immediate sound/player routing
        for pid in ["de_sizzle", "extended_air", "narrow_stereo"]:
            sel.value = pid
            await pilot.pause()
            assert wb.selected_preset_id == pid
            assert wb.path_enh == ai_files[pid]
            assert player.current_track == ai_files[pid]

        # 5. Toggle back to Eco Mode: returns to the 2 Eco options
        btn_toggle.press()
        await pilot.pause()

        assert wb.neural_enabled is False
        assert [opt[1] for opt in sel._options if opt[1] != Select.NULL] == [
            "conservative",
            "fast_balanced",
        ]
        assert wb.selected_preset_id in ("conservative", "fast_balanced")


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

        btn_page_deck = app.query_one("#wb-btn-page-deck", Button)
        btn_page_eq = app.query_one("#wb-btn-page-eq", Button)
        assert "DECK" in str(btn_page_deck.label)
        assert "EQ" in str(btn_page_eq.label)
        assert "wb-page-btn-active" in btn_page_deck.classes

        # 2. Switch to 10-Band EQ page
        btn_page_eq.press()
        await pilot.pause()

        assert wb.active_page == "eq"
        assert page_deck.styles.display == "none"
        assert page_eq.styles.display != "none"
        assert "DECK" in str(btn_page_deck.label)
        assert "EQ" in str(btn_page_eq.label)
        assert "wb-page-btn-active" in btn_page_eq.classes

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

        # 9. Test Preset selection
        sel_preset = app.query_one("#wb-eq-preset-select", Select)
        with patch.object(wb, "_schedule_eq_render"):
            sel_preset.value = "Hi-Fi Air"
            await pilot.pause()
            assert wb.eq_settings.preset_name == "Hi-Fi Air"
            assert wb.eq_settings.bands[16000] == 5.0
            assert "+5.0dB" in str(val_16k.render())

        # 10. Switch back to Deck page
        btn_page_deck.press()
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

        # 4. Apply 'Club Punch' preset while on ENH
        sel_preset = app.query_one("#wb-eq-preset-select", Select)
        sel_preset.value = "Club Punch"
        await pilot.pause()
        assert "equalizer=f=31:width_type=o:w=1:g=3.50" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=4.00" in player.audio_filter

        # 5. Switch back to MP3 -> active EQ filter must still apply!
        btn_mp3 = app.query_one("#btn-stream-mp3", Button)
        btn_mp3.press()
        await pilot.pause()
        assert wb.active_stream == "MP3"
        assert "equalizer=f=31:width_type=o:w=1:g=3.50" in player.audio_filter
        assert "equalizer=f=63:width_type=o:w=1:g=4.00" in player.audio_filter

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


async def test_workbench_stem_separation_and_auditioning(tmp_path: Path) -> None:
    """Verify Workbench vocal and instrumental stem switching and export."""
    from harvester.analysis.enhancement.stem_separator import StemResult

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "stem_song.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.id = "job-stem-test"
        job.output_path = dummy_mp3

        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        btn_voc = app.query_one("#btn-stream-voc", Button)
        btn_inst = app.query_one("#btn-stream-inst", Button)
        assert "[3] VOC" in str(btn_voc.label)
        assert "[4] INST" in str(btn_inst.label)

        # Mock stem separator result
        voc_file = tmp_path / "stem_song_vocals.wav"
        inst_file = tmp_path / "stem_song_instrumental.wav"
        voc_file.write_bytes(b"RIFFdummyvocalswav")
        inst_file.write_bytes(b"RIFFdummyinstwav")

        mock_res = StemResult(
            vocals_path=voc_file,
            instrumental_path=inst_file,
            mode="eco",
            sample_rate=44100,
            duration_s=2.5,
            engine="eco",
        )

        with patch(
            "harvester.analysis.enhancement.stem_separator.StemSeparator.separate_file",
            return_value=mock_res,
        ):
            # Enable Neural AI mode first — VOC/INST buttons are gated behind it
            btn_neural = app.query_one("#wb-btn-neural-toggle", Button)
            btn_neural.press()
            await pilot.pause()
            assert wb.neural_enabled, "Neural mode must be active to use stem separation"
            assert not btn_voc.disabled, "VOC button should be enabled after neural toggle"
            assert not btn_inst.disabled, "INST button should be enabled after neural toggle"

            # Press [3] VOC
            btn_voc.press()
            await pilot.pause()

            assert wb.active_stream == "VOC"
            assert btn_voc.variant == "primary"
            assert wb.path_voc == voc_file

            # Press [4] INST
            btn_inst.press()
            await pilot.pause()

            assert wb.active_stream == "INST"
            assert btn_inst.variant == "primary"
            assert wb.path_inst == inst_file

            # Export while on INST
            exported_inst = tmp_path / "stem_song_instrumental.wav"
            btn_export = app.query_one("#wb-btn-export", Button)
            btn_export.press()
            for _ in range(25):
                await pilot.pause(0.05)
                if exported_inst.exists():
                    break

            assert exported_inst.exists()

            # Verify stem progress bar is present in workbench DOM
            pb_stem = app.query_one("#wb-stem-progress", ProgressBar)
            assert pb_stem is not None


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
async def test_workbench_stem_diagnostic_dropdowns_and_profile_memory(tmp_path: Path) -> None:
    """Verify vocal and instrumental diagnostic multi-choice panels, buttons, and profile memory."""
    import json

    from textual.widgets import Button

    from harvester.ui.workbench import DefectChecklist

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one(WorkbenchWidget)
        voc_panel = app.query_one("#wb-diagnostic-voc-panel")
        inst_panel = app.query_one("#wb-diagnostic-inst-panel")
        voc_list = app.query_one("#wb-voc-flags-list", DefectChecklist)
        inst_list = app.query_one("#wb-inst-flags-list", DefectChecklist)

        # 1. Initial state: stream is MP3, both diagnostic panels are hidden
        assert voc_panel.styles.display == "none"
        assert inst_panel.styles.display == "none"

        # 2. Switch to VOC: voc_panel becomes visible, inst_panel stays hidden
        wb.set_active_stream("VOC")
        await pilot.pause()
        assert voc_panel.styles.display == "block"
        assert inst_panel.styles.display == "none"

        # 3. Switch to INST: inst_panel becomes visible, voc_panel is hidden
        wb.set_active_stream("INST")
        await pilot.pause()
        assert voc_panel.styles.display == "none"
        assert inst_panel.styles.display == "block"

        # 4. Switch back to MP3: both are hidden
        wb.set_active_stream("MP3")
        await pilot.pause()
        assert voc_panel.styles.display == "none"
        assert inst_panel.styles.display == "none"

        # 5. Multi-choice SelectionList allows selecting multiple options
        voc_list.select("fix_pumping")
        voc_list.select("de_robot")
        await pilot.pause()
        assert "fix_pumping" in wb.vocal_flags
        assert "de_robot" in wb.vocal_flags

        # 6. Test STUDIO, ALL, and CLEAR buttons for Vocal
        btn_voc_studio = app.query_one("#wb-btn-voc-studio", Button)
        btn_voc_studio.press()
        await pilot.pause()
        assert wb.vocal_flags == {"de_bleed", "fix_pumping"}

        btn_voc_all = app.query_one("#wb-btn-voc-all", Button)
        btn_voc_all.press()
        await pilot.pause()
        assert len(wb.vocal_flags) == len(VOCAL_REMEDIATIONS)

        btn_voc_clear = app.query_one("#wb-btn-voc-clear", Button)
        btn_voc_clear.press()
        await pilot.pause()
        assert len(wb.vocal_flags) == 0

        # 7. Test STUDIO, ALL, and CLEAR buttons for Instrumental
        btn_inst_studio = app.query_one("#wb-btn-inst-studio", Button)
        btn_inst_studio.press()
        await pilot.pause()
        assert wb.inst_flags == {"anti_bleed_synths", "sub_bass_clean"}

        btn_inst_all = app.query_one("#wb-btn-inst-all", Button)
        btn_inst_all.press()
        await pilot.pause()
        assert len(wb.inst_flags) == 10

        btn_inst_clear = app.query_one("#wb-btn-inst-clear", Button)
        btn_inst_clear.press()
        await pilot.pause()
        assert len(wb.inst_flags) == 0

        # 7b. Test RE-SEPARATE button
        btn_resep = app.query_one("#wb-btn-stem-reseparate", Button)
        with patch.object(wb, "_trigger_stem_separation") as mock_resep:
            btn_resep.press()
            await pilot.pause()
            mock_resep.assert_called_once_with("VOC", force=True)

        # 7c. Test AUTO-DETECT button
        btn_autodetect = app.query_one("#wb-btn-stem-auto-detect", Button)
        with patch.object(wb, "_trigger_acoustic_detection") as mock_autodetect:
            btn_autodetect.press()
            await pilot.pause()
            mock_autodetect.assert_called_once()

        # 7d. Test _async_detect_acoustics applying recommendations
        mock_result = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.88,
            is_pure_instrumental=False,
            detected_issues=["synth_bleed"],
            recommended_vocal_flags={"vad_gate", "fix_pumping"},
            recommended_inst_flags={"anti_bleed_synths", "sub_bass_clean"},
            recommended_blend_weight=0.75,
            recommended_engine="ensemble",
            summary="Vocal track detected",
        )
        fake_track = tmp_path / "fake_detect.wav"
        fake_track.write_bytes(b"RIFF....WAVEfmt ")
        wb.path_mp3 = fake_track

        with patch("harvester.ui.workbench.analyze_track_acoustics", return_value=mock_result), \
             patch("soundfile.read", return_value=(__import__("numpy").zeros((1000, 2)), 44100)):
            await wb._async_detect_acoustics(fake_track)
            await pilot.pause()

            assert wb.vocal_flags == {"vad_gate", "fix_pumping"}
            assert wb.inst_flags == {"anti_bleed_synths", "sub_bass_clean"}
            assert wb.stem_bsr_blend == 0.75
            assert "VOCALS DETECTED" in str(app.query_one("#wb-acoustic-status", Label).render())

        # 8. Test loading track with existing profile.json restores the saved multi-flags
        track_file = tmp_path / "test_track.mp3"
        track_file.write_bytes(b"TESTAUDIO")
        cache_dir = (
            Path.home()
            / ".cache"
            / "omnirip"
            / "stems"
            / f"{track_file.stem}_{track_file.stat().st_size}"
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "profile.json").write_text(
            json.dumps(
                {
                    "vocal_flags": ["de_robot", "air_boost"],
                    "inst_flags": ["preserve_drums", "kill_whispers"],
                }
            )
        )

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=track_file)
        job.output_path = track_file

        wb.load_job(job)
        await pilot.pause()

        assert wb.vocal_flags == {"de_robot", "air_boost"}
        assert wb.inst_flags == {"preserve_drums", "kill_whispers"}
        assert set(voc_list.selected) == {"de_robot", "air_boost"}
        assert set(inst_list.selected) == {"preserve_drums", "kill_whispers"}


async def test_workbench_stems_page_navigation_and_controls(tmp_path: Path) -> None:
    """Verify Workbench 3-page system and dedicated STEMS studio page controls."""
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy_mp3 = tmp_path / "test_track.mp3"
        dummy_mp3.write_bytes(b"dummy-mp3-audio-data")

        job = TrackJob(mode=Mode.SINGLE_URL, input_path=dummy_mp3)
        job.output_path = dummy_mp3

        with patch.object(wb, "_trigger_enhancement_pregeneration"):
            wb.load_job(job)

        page_deck = app.query_one("#wb-page-deck")
        page_eq = app.query_one("#wb-page-eq")
        page_stems = app.query_one("#wb-page-stems")
        btn_page_deck = app.query_one("#wb-btn-page-deck", Button)
        btn_page_eq = app.query_one("#wb-btn-page-eq", Button)
        btn_page_stems = app.query_one("#wb-btn-page-stems", Button)

        # 1. Initially on DECK page
        assert wb.active_page == "deck"
        assert page_deck.styles.display != "none"
        assert page_eq.styles.display == "none"
        assert page_stems.styles.display == "none"
        assert "wb-page-btn-active" in btn_page_deck.classes
        assert "wb-page-btn-active" not in btn_page_eq.classes
        assert "wb-page-btn-active" not in btn_page_stems.classes

        # 2. Switch to STEMS page
        btn_page_stems.press()
        await pilot.pause()

        assert wb.active_page == "stems"
        assert page_deck.styles.display == "none"
        assert page_eq.styles.display == "none"
        assert page_stems.styles.display != "none"
        assert "wb-page-btn-active" in btn_page_stems.classes
        assert "wb-page-btn-active" not in btn_page_deck.classes

        # 3. Verify all controls on STEMS page exist
        assert app.query_one("#wb-btn-stem-auto-detect", Button) is not None
        assert app.query_one("#wb-btn-stem-reseparate", Button) is not None
        assert app.query_one("#wb-btn-audition-voc", Button) is not None
        assert app.query_one("#wb-btn-audition-inst", Button) is not None
        assert app.query_one("#wb-blend-bsr-val", Label) is not None
        assert app.query_one("#wb-blend-hdemucs-val", Label) is not None

        # 4. Test BS-RoFormer stepper on STEMS page
        btn_bsr_dn = app.query_one("#wb-blend-bsr-dn", Button)
        btn_bsr_up = app.query_one("#wb-blend-bsr-up", Button)
        init_bsr = wb.stem_bsr_blend
        btn_bsr_dn.press()
        await pilot.pause()
        assert wb.stem_bsr_blend == round(init_bsr - 0.05, 2)

        btn_bsr_up.press()
        await pilot.pause()
        assert wb.stem_bsr_blend == init_bsr

        # Test LR4 Crossover stepper on STEMS page
        btn_xo_dn = app.query_one("#wb-crossover-dn", Button)
        btn_xo_up = app.query_one("#wb-crossover-up", Button)
        init_xo = wb.stem_crossover_hz
        btn_xo_up.press()
        await pilot.pause()
        assert wb.stem_crossover_hz == init_xo + 25.0
        btn_xo_dn.press()
        await pilot.pause()
        assert wb.stem_crossover_hz == init_xo

        # Test De-Reverb stepper on STEMS page
        btn_drv_up = app.query_one("#wb-dereverb-up", Button)
        btn_drv_dn = app.query_one("#wb-dereverb-dn", Button)
        init_drv = wb.stem_dereverb_intensity
        btn_drv_up.press()
        await pilot.pause()
        assert wb.stem_dereverb_intensity == round(init_drv + 0.10, 2)
        btn_drv_dn.press()
        await pilot.pause()
        assert wb.stem_dereverb_intensity == init_drv

        # 5. Test Audition buttons on STEMS page
        btn_aud_inst = app.query_one("#wb-btn-audition-inst", Button)
        btn_aud_inst.press()
        await pilot.pause()
        assert wb.active_stream == "INST"

        btn_aud_voc = app.query_one("#wb-btn-audition-voc", Button)
        btn_aud_voc.press()
        await pilot.pause()
        assert wb.active_stream == "VOC"

        # 6. Switch back to DECK page
        btn_page_deck.press()
        await pilot.pause()
        assert wb.active_page == "deck"
        assert page_deck.styles.display != "none"
        assert page_stems.styles.display == "none"

