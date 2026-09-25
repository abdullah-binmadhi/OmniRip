"""Unit tests for the modular VisualDashboardWidget, VisualizerCard, and VisualCatalogModal."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Select

from harvester.ui.visual_dashboard import (
    VisualCatalogModal,
    VisualDashboardWidget,
    VisualizerCard,
    VisualizerEngineCanvas,
)
from harvester.ui.visuals import AudioFeatureContext, VisualizerRegistry


class DashboardTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield VisualDashboardWidget(id="test-dashboard")


async def test_visual_dashboard_empty_state_and_quickstarts():
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        assert dash is not None

        # 1. Canvas starts empty by default
        assert len(dash.cards) == 0
        assert app.query_one("#vis-dash-empty-state") is not None
        assert app.query_one("#btn-empty-browse") is not None

        # 2. Press solo quickstart button
        app.query_one("#btn-empty-solo", Button).press()
        await pilot.pause()
        assert len(dash.cards) == 1
        assert len(app.query(VisualizerCard)) == 1

        # 3. Press clear toolbar button
        app.query_one("#btn-vis-clear", Button).press()
        await pilot.pause()
        assert len(dash.cards) == 0
        assert app.query_one("#vis-dash-empty-state") is not None

        # 4. Press quad quickstart button
        app.query_one("#btn-empty-quad", Button).press()
        await pilot.pause()
        assert len(dash.cards) == 4
        assert len(app.query(VisualizerCard)) == 4


async def test_visualizer_card_palette_cycle_and_remove():
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("mirrored_dance", palette="cyan")
        await pilot.pause()

        card = app.query_one(VisualizerCard)
        assert card.engine_id == "mirrored_dance"
        assert card.palette_key == "cyan"

        # Cycle palette
        btn_pal = card.query_one(f"#btn-pal-{card.card_id}", Button)
        btn_pal.press()
        await pilot.pause()
        assert card.palette_key == "neon"

        # Remove card via close button
        btn_close = card.query_one(f"#btn-close-{card.card_id}", Button)
        btn_close.press()
        await pilot.pause()
        assert len(dash.cards) == 0


async def test_visual_catalog_modal_search_and_filter():
    class ModalTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield Button("Open", id="btn-open")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.push_screen(VisualCatalogModal())

    app = ModalTestApp()
    async with app.run_test() as pilot:
        app.query_one("#btn-open", Button).press()
        await pilot.pause()

        modal = app.screen
        assert isinstance(modal, VisualCatalogModal)

        # Search for braille
        inp = modal.query_one("#vis-catalog-search", Input)
        inp.value = "braille"
        await pilot.pause()
        assert len(modal.query(".vis-item-row")) >= 1

        # Select category filter
        sel = modal.query_one("#vis-catalog-category", Select)
        sel.value = "spectral"
        await pilot.pause()
        assert modal.selected_category == "spectral"
