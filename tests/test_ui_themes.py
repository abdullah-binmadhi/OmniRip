"""Unit tests for theme registry and dynamic cycling."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Label

from harvester.ui.themes import AVAILABLE_THEMES, cycle_theme, register_custom_themes


class ThemeTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Label("Theme Test")


async def test_theme_registry_and_cycling() -> None:
    app = ThemeTestApp()
    async with app.run_test():
        register_custom_themes(app)
        assert len(AVAILABLE_THEMES) >= 8

        # Cycle theme multiple times and verify valid names returned
        t1 = cycle_theme(app)
        assert isinstance(t1, str)
        t2 = cycle_theme(app)
        assert isinstance(t2, str)
        assert t1 != t2
