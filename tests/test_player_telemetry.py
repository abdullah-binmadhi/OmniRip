"""Tests for StudioTelemetryWidget and telemetry mode cycling."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

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
