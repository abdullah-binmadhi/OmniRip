"""Unit tests for Full Vision Studio UI composition and interactions."""

import pytest
from textual.app import App, ComposeResult

from harvester.ui.full_vision import (
    FullVisionStudioWidget,
    SaveLayoutModal,
    AddSongModal,
)


class DummyVisionApp(App):
    def compose(self) -> ComposeResult:
        yield FullVisionStudioWidget()


@pytest.mark.asyncio
async def test_full_vision_studio_compose():
    app = DummyVisionApp()
    async with app.run_test() as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        assert studio is not None

        # Check top bar buttons
        theme_btn = app.query_one("#btn-fvs-theme")
        assert theme_btn is not None

        gap_btn = app.query_one("#btn-fvs-gap")
        assert "GAP:" in str(gap_btn.label)

        # Check music player dock
        play_btn = app.query_one("#btn-fvs-play")
        assert "PLAY" in str(play_btn.label)

        # Test gap cycle
        studio._cycle_gap()
        assert studio.active_gap == 2

        # Test Stitch theme cycle
        studio._cycle_stitch_theme()
        assert studio.current_theme is not None
