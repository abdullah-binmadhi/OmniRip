"""Tests for StudioTelemetryWidget and telemetry mode cycling."""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.ui.help_modal import HelpModalScreen
from harvester.ui.player import AudioPlayerWidget, StudioTelemetryWidget


def test_studio_telemetry_init():
    widget = StudioTelemetryWidget()
    assert widget.telemetry_mode == "LUFS"
    assert widget._lufs_integrated == -14.0
    assert widget._true_peak_db == -0.4


def test_studio_telemetry_cycle_mode():
    widget = StudioTelemetryWidget()
    assert widget.telemetry_mode == "LUFS"

    new_mode, desc = widget.cycle_telemetry_mode()
    assert new_mode == "PHASE"
    assert "Phase" in desc
    assert widget.telemetry_mode == "PHASE"

    new_mode, desc = widget.cycle_telemetry_mode()
    assert new_mode == "RADAR"
    assert "Anti-Fraud" in desc
    assert widget.telemetry_mode == "RADAR"

    new_mode, desc = widget.cycle_telemetry_mode()
    assert new_mode == "LUFS"
    assert "Loudness" in desc
    assert widget.telemetry_mode == "LUFS"


def test_studio_telemetry_update_levels():
    widget = StudioTelemetryWidget()
    widget.is_playing = True
    widget.update_telemetry(0.7, 0.6)

    assert widget._lufs_momentary > -30.0
    assert widget._phase_correlation > 0.5
    assert widget._mid_energy_pct > 50.0

    # Idle update
    widget.is_playing = False
    widget.update_telemetry(0.0, 0.0)
    assert widget._lufs_momentary == -70.0


def test_studio_telemetry_render_all_modes():
    widget = StudioTelemetryWidget()
    widget.is_playing = True
    widget.cutoff_hz = 20500.0

    # LUFS render
    widget.telemetry_mode = "LUFS"
    text_lufs = str(widget.render())
    assert "EBU R128 LOUDNESS" in text_lufs
    assert "LUFS" in text_lufs

    # PHASE render
    widget.telemetry_mode = "PHASE"
    text_phase = str(widget.render())
    assert "STEREO PHASE" in text_phase
    assert "Phase:" in text_phase

    # RADAR render
    widget.telemetry_mode = "RADAR"
    text_radar = str(widget.render())
    assert "FORENSIC CUTOFF" in text_radar
    assert "20.5 kHz" in text_radar


class DummyPlayerApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")


@pytest.mark.asyncio
async def test_audio_player_telemetry_button_click():
    app = DummyPlayerApp()
    async with app.run_test():
        player = app.query_one(AudioPlayerWidget)
        btn = player.query_one("#btn-vis-mode", Button)
        vis = player.query_one("#player-visualizer", StudioTelemetryWidget)

        assert str(btn.label) == "LUFS"
        assert vis.telemetry_mode == "LUFS"

        player.toggle_vis_mode()
        assert str(btn.label) == "PHASE"
        assert vis.telemetry_mode == "PHASE"

        player.toggle_vis_mode()
        assert str(btn.label) == "RADAR"
        assert vis.telemetry_mode == "RADAR"

        player.toggle_vis_mode()
        assert str(btn.label) == "LUFS"
        assert vis.telemetry_mode == "LUFS"


def test_studio_telemetry_target_cycling():
    widget = StudioTelemetryWidget()
    assert widget.target_lufs == -14.0

    target, desc = widget.cycle_target_lufs()
    assert target == -16.0
    assert "Apple" in desc
    assert "EBU R128 LOUDNESS [-16 LUFS" in str(widget.render())

    target, desc = widget.cycle_target_lufs()
    assert target == -9.0
    assert "Club" in desc
    assert "EBU R128 LOUDNESS [-9 LUFS" in str(widget.render())

    target, desc = widget.cycle_target_lufs()
    assert target == -14.0
    assert "Spotify" in desc


def test_studio_telemetry_peaks_and_expanded_phase():
    widget = StudioTelemetryWidget()
    widget.is_playing = True
    widget.update_telemetry(0.9, 0.9)
    assert widget._true_peak_db > -10.0
    assert widget._peak_hold_db >= widget._true_peak_db

    widget.reset_peaks()
    assert widget._peak_hold_db == widget._true_peak_db

    widget.telemetry_mode = "PHASE"
    widget.phase_expanded = True
    txt = str(widget.render())
    assert "GONIOMETER STEREO EXPANDED" in txt
    assert "Mid/Side:" in txt


@pytest.mark.asyncio
async def test_audio_player_stream_badges_and_targets():
    app = DummyPlayerApp()
    async with app.run_test():
        player = app.query_one(AudioPlayerWidget)
        badge = player.query_one("#player-stream-badge", Label)

        # Baseband FLAC
        player._update_stream_badge(Path("track.flac"), is_enhanced=False)
        assert "FLAC LOSSLESS" in str(badge.content)

        # Baseband MP3
        player._update_stream_badge(Path("track.mp3"), is_enhanced=False)
        assert "MP3 BASEBAND" in str(badge.content)

        # Enhanced stream
        player._update_stream_badge(Path("track.flac"), is_enhanced=True, preset_name="CLUB_PUNCH")
        assert "NEURAL RESTORED" in str(badge.content)
        assert "CLUB_PUNCH" in str(badge.content)

        # Target and reset actions
        player.cycle_telemetry_target()
        vis = player.query_one("#player-visualizer", StudioTelemetryWidget)
        assert vis.target_lufs == -16.0
        player.reset_telemetry_peaks()


@pytest.mark.asyncio
async def test_help_modal_screen():
    class HelpApp(App[None]):
        def compose(self) -> ComposeResult:
            yield AudioPlayerWidget()

    app = HelpApp()
    async with app.run_test():
        await app.push_screen(HelpModalScreen())
        modal = app.screen
        assert isinstance(modal, HelpModalScreen)
        assert modal.query_one("#help-title", Label) is not None
        assert modal.query_one("#btn-help-close", Button) is not None
        modal.query_one("#btn-help-close", Button).press()

