"""Tests for the genre mix modal (docs/01 D38)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Button, Label, SelectionList

from harvester.analysis.enhancement.genres import GENRE_PROFILES
from harvester.ui.genre_mix import MAX_MIX_GENRES, GenreMixScreen

OPTIONS = [
    (profile.label, key) for key, profile in GENRE_PROFILES.items() if key != "neutral"
]


class MixApp(App[None]):
    def __init__(self, selected: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.dismissed: list[list[str] | None] = []
        self._selected = selected

    def compose(self) -> ComposeResult:
        yield Button("placeholder", id="placeholder")

    def on_mount(self) -> None:
        self.push_screen(
            GenreMixScreen(OPTIONS, self._selected),
            lambda value: self.dismissed.append(value),
        )


async def test_mix_modal_preselects_and_applies():
    app = MixApp(selected=("house",))
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, GenreMixScreen)
        selection = screen.query_one("#genre-mix-list", SelectionList)
        assert list(selection.selected) == ["house"]
        selection.select("techno")
        screen.query_one("#genre-mix-apply", Button).press()
        await pilot.pause()
        assert app.dismissed[-1] == ["house", "techno"]


async def test_mix_modal_cancels():
    app = MixApp()
    async with app.run_test() as pilot:
        screen = app.screen
        screen.query_one("#genre-mix-cancel", Button).press()
        await pilot.pause()
        assert app.dismissed[-1] is None


async def test_mix_modal_rejects_more_than_six_genres():
    too_many = tuple(
        key for key, _profile in OPTIONS if key in ("house", "techno", "trance_prog")
    )
    app = MixApp(selected=too_many)
    async with app.run_test() as pilot:
        screen = app.screen
        selection = screen.query_one("#genre-mix-list", SelectionList)
        for key, _label in OPTIONS:
            selection.select(key)
            if len(selection.selected) > MAX_MIX_GENRES:
                break
        assert len(selection.selected) > MAX_MIX_GENRES
        screen.query_one("#genre-mix-apply", Button).press()
        await pilot.pause()
        assert app.dismissed == []
        hint = str(screen.query_one("#genre-mix-hint", Label).render())
        assert "at most" in hint
