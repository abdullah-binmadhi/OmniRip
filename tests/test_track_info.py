"""Tests for the Track Info modal (enrichment + upkeep relocation, M18.3)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Button

from harvester.ui.track_info import TrackInfoScreen

ROWS = [("Track", "Ghost Town"), ("Models", "3/8 cached")]


class InfoApp(App[None]):
    def __init__(self, *, hosted_available: bool = True) -> None:
        super().__init__()
        self.dismissed: list[str | None] = []
        self._hosted_available = hosted_available

    def compose(self) -> ComposeResult:
        yield Button("placeholder", id="placeholder")

    def on_mount(self) -> None:
        self.push_screen(
            TrackInfoScreen(ROWS, hosted_available=self._hosted_available),
            lambda value: self.dismissed.append(value),
        )


async def test_rows_render_and_action_dismisses_with_key():
    app = InfoApp()
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, TrackInfoScreen)
        body = str(screen.query_one("#ti-body").render())
        assert "Ghost Town" in body
        assert "3/8 cached" in body
        assert "MVSEP key configured" in body

        screen.query_one("#ti-tags", Button).press()
        await pilot.pause()
        assert app.dismissed == ["tags"]


async def test_close_returns_none_and_missing_key_is_reported():
    app = InfoApp(hosted_available=False)
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, TrackInfoScreen)
        assert "no MVSEP key configured" in str(screen.query_one("#ti-body").render())
        screen.query_one("#ti-close", Button).press()
        await pilot.pause()
        assert app.dismissed == [None]


async def test_every_action_button_maps_to_its_key():
    app = InfoApp()
    async with app.run_test() as pilot:
        expected = {
            "ti-tags": "tags",
            "ti-speakers": "speakers",
            "ti-credits": "credits",
            "ti-models": "models",
            "ti-diagnostics": "diagnostics",
        }
        for button_id, action in expected.items():
            app.push_screen(TrackInfoScreen(ROWS), lambda value: app.dismissed.append(value))
            await pilot.pause()
            app.screen.query_one(f"#{button_id}", Button).press()
            await pilot.pause()
            assert app.dismissed[-1] == action
