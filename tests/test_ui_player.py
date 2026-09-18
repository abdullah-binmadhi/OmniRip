"""Unit tests for AudioPlayerWidget controls and state."""

from __future__ import annotations

from textual.app import App, ComposeResult

from harvester.ui.player import AudioPlayerWidget


class PlayerTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="test-player")


async def test_audio_player_widget_lifecycle() -> None:
    app = PlayerTestApp()
    async with app.run_test() as pilot:
        player = app.query_one("#test-player", AudioPlayerWidget)
        assert player.is_playing is False
        assert player.current_track is None

        # Toggle playback without track
        player.toggle_playback()
        assert player.is_playing is False

        # Toggle visualizer mode
        player.toggle_vis_mode()
        await pilot.pause()
