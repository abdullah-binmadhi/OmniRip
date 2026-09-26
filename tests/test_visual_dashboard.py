"""Unit tests for the modular VisualDashboardWidget, VisualizerCard, and VisualCatalogModal."""

from __future__ import annotations

import numpy as np
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label, Select

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


async def test_visual_catalog_modal_lists_all_100_engines():
    """The catalog must expose the entire 100-engine catalog, not a truncated sample."""

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

        # 1. Unfiltered, the modal lists every registered engine.
        rows = modal.query(".vis-item-row")
        assert len(rows) == 100, f"Catalog modal listed {len(rows)} engines, expected 100"

        # 2. Every row offers an add button carrying that engine's id.
        add_buttons = modal.query(".vis-item-btn-add")
        assert len(add_buttons) == 100
        listed_ids = {btn.name for btn in add_buttons}
        assert listed_ids == {engine.id for engine in VisualizerRegistry.list_all()}

        # 3. Every category is represented in the default listing.
        modal.query_one("#vis-catalog-category", Select).value = "all"
        await pilot.pause()
        assert len(modal.query(".vis-item-row")) == 100

        # 4. Picking a category narrows the list to that pack's quota.
        modal.query_one("#vis-catalog-category", Select).value = "studio_meters"
        await pilot.pause()
        assert len(modal.query(".vis-item-row")) == len(
            VisualizerRegistry.list_by_category("studio_meters")
        )

    # 5. Adding an engine dismisses the modal and returns that engine's id.
    # The app has no screen-level on_button_pressed here, otherwise the press
    # would bubble up and re-push a fresh modal over the top of the one closing.
    class AddTestApp(App[str | None]):
        def compose(self) -> ComposeResult:
            yield Label("base")

    add_app = AddTestApp()
    async with add_app.run_test() as pilot:
        result: list[str | None] = []
        add_app.push_screen(VisualCatalogModal(), callback=result.append)
        await pilot.pause()

        add_modal = add_app.screen
        assert isinstance(add_modal, VisualCatalogModal)
        target = "fractal_chladni_plate"
        add_btn = next(btn for btn in add_modal.query(".vis-item-btn-add") if btn.name == target)
        add_btn.press()
        await pilot.pause()
        await pilot.pause()

        assert result == [target], f"Expected the modal to return {target!r}, got {result!r}"
        assert not isinstance(add_app.screen, VisualCatalogModal)


async def test_narrow_card_still_renders_engine_minimum_frame():
    """A squeezed card must render the engine's minimum frame, not a clipped one."""
    class NarrowApp(App[None]):
        CSS = """
        #narrow { width: 12; }
        """

        def compose(self) -> ComposeResult:
            yield VisualDashboardWidget(id="test-dashboard")

    app = NarrowApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("matrix_digital_rain", palette="cyan")
        await pilot.pause()

        canvas = app.query_one(VisualizerEngineCanvas)
        engine = canvas.engine
        # Feed a real measured frame so the engine is not on standby fallback.
        canvas.set_audio_features(
            AudioFeatureContext(
                levels_128=np.linspace(0.1, 0.9, 128).astype(np.float32),
                waveform_l=np.sin(np.linspace(0, 10, 1024)).astype(np.float32),
                is_playing=True,
            )
        )
        await pilot.pause()

        frame = canvas.render()
        lines = frame.plain.split("\n")
        assert len(lines) >= engine.min_height
        assert min(len(line) for line in lines) >= engine.min_width


async def test_visual_dashboard_plays_routed_feature_track():
    """A routed feature track must drive the card, and clearing it restores standby."""
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("matrix_digital_rain", palette="cyan")
        await pilot.pause()

        canvas = app.query_one(VisualizerEngineCanvas)
        first = AudioFeatureContext(
            levels_128=np.full(128, 0.9, dtype=np.float32),
            waveform_l=np.sin(np.linspace(0, 12, 1024)).astype(np.float32),
            spectral_centroid=4200.0,
            is_playing=True,
        )
        second = AudioFeatureContext(
            levels_128=np.full(128, 0.05, dtype=np.float32),
            waveform_l=(0.02 * np.sin(np.linspace(0, 12, 1024))).astype(np.float32),
            spectral_centroid=300.0,
            is_playing=True,
        )
        track = [first, second]

        # Installing a track shows its first frame. Drive the tick manually so
        # the assertion does not race the canvas's own 30 FPS timer.
        if canvas._anim_timer is not None:
            canvas._anim_timer.stop()
        dash.set_feature_track(track)
        await pilot.pause()
        assert canvas.feature_ctx.spectral_centroid == 4200.0
        assert canvas.feature_ctx.is_playing

        # Each tick advances one frame, and the track loops rather than freezing.
        canvas._on_tick()
        assert canvas.feature_ctx.spectral_centroid == 300.0
        canvas._on_tick()
        assert canvas.feature_ctx.spectral_centroid == 4200.0

        # Clearing the track returns the card to standby synthesis.
        dash.clear_audio_features()
        canvas._on_tick()
        assert canvas.feature_ctx.is_playing is False


async def test_feed_audio_without_data_cannot_fake_playback():
    """The original bug: a bare is_playing flag froze cards on a zero context."""
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("matrix_digital_rain", palette="cyan")
        await pilot.pause()

        canvas = app.query_one(VisualizerEngineCanvas)
        canvas.set_audio_features(AudioFeatureContext.synthesize_idle())

        dash.feed_audio(is_playing=True)
        await pilot.pause()
        assert canvas.feature_ctx.is_playing is False

        # Supplying real data does mark playback.
        dash.feed_audio(
            levels=np.full(128, 0.5, dtype=np.float32),
            wave=np.sin(np.linspace(0, 8, 1024)).astype(np.float32),
            is_playing=True,
        )
        await pilot.pause()
        assert canvas.feature_ctx.is_playing is True
        assert float(np.max(canvas.feature_ctx.levels_128)) == pytest.approx(0.5)


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


async def test_visual_dashboard_gap_tool():
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        assert dash.gap_size == 0

        # Press Gap +
        app.query_one("#btn-vis-gap-inc", Button).press()
        await pilot.pause()
        assert dash.gap_size == 1
        assert app.query_one("#lbl-vis-gap", Label).render().plain == "1"

        # Press Gap -
        app.query_one("#btn-vis-gap-dec", Button).press()
        await pilot.pause()
        assert dash.gap_size == 0
        assert app.query_one("#lbl-vis-gap", Label).render().plain == "0"


async def test_visual_dashboard_arrange_mode_customization():
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.apply_preset("dual")
        await pilot.pause()

        assert len(dash.cards) == 2
        card1_id = dash.cards[0]["card_id"]
        card2_id = dash.cards[1]["card_id"]

        # Activate arrange mode
        arrange_btn = app.query_one("#btn-vis-arrange", Button)
        arrange_btn.press()
        await pilot.pause()
        assert dash.is_arrange_mode is True
        assert "ON" in str(arrange_btn.label)
        assert dash.selected_card_id == card1_id

        # Selected card has -selected class and full button labels
        card1 = app.query_one(f"#vis-card-{card1_id}", VisualizerCard)
        assert card1.has_class("-selected")

        btn_left = app.query_one(f"#btn-move-left-{card1_id}", Button)
        btn_right = app.query_one(f"#btn-move-right-{card1_id}", Button)
        btn_span = app.query_one(f"#btn-span-{card1_id}", Button)
        btn_tall = app.query_one(f"#btn-tall-{card1_id}", Button)

        assert "LEFT" in str(btn_left.label)
        assert "RIGHT" in str(btn_right.label)
        assert "SPAN" in str(btn_span.label)
        assert "TALL" in str(btn_tall.label)

        # Move card 1 to the right (swapping with card 2) via button click
        btn_right.press()
        await pilot.pause()
        assert dash.cards[0]["card_id"] == card2_id
        assert dash.cards[1]["card_id"] == card1_id

        # Move card 1 back to the left using Arrow Key Left
        await pilot.press("left")
        await pilot.pause()
        assert dash.cards[0]["card_id"] == card1_id
        assert dash.cards[1]["card_id"] == card2_id

        # Canvas click selection: clicking card 2 canvas selects card 2
        card2 = app.query_one(f"#vis-card-{card2_id}", VisualizerCard)
        card2.canvas.on_click()
        await pilot.pause()
        assert dash.selected_card_id == card2_id
        assert card2.has_class("-selected")

        # Toggle span on card 2 via 's' key
        await pilot.press("s")
        await pilot.pause()
        assert dash.cards[1].get("span") == "full"
        assert app.query_one(f"#vis-card-{card2_id}", VisualizerCard).has_class("-span-full")

        # Toggle tall on card 2 via 't' key
        await pilot.press("t")
        await pilot.pause()
        assert dash.cards[1].get("tall") is True
        assert app.query_one(f"#vis-card-{card2_id}", VisualizerCard).has_class("-tall")

        # Deactivate arrange mode via escape key
        await pilot.press("escape")
        await pilot.pause()
        assert dash.is_arrange_mode is False
        assert dash.selected_card_id is None
        assert not app.query_one(f"#vis-card-{card2_id}", VisualizerCard).has_class("-selected")


async def test_visual_dashboard_60fps_cadence():
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("mirrored_dance")
        await pilot.pause()

        canvas = app.query_one(VisualizerEngineCanvas)
        assert canvas._anim_timer is not None
        # Timer interval must be 1.0 / 60.0 (approx 0.016667)
        assert canvas._anim_timer._interval == pytest.approx(1.0 / 60.0, rel=1e-3)


async def test_feed_audio_with_audio_feature_context_instance():
    """Verify dash.feed_audio accepts an explicit AudioFeatureContext without nesting."""
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)
        dash.add_card("audio_flame_fire")
        dash.add_card("matrix_digital_rain")
        await pilot.pause()

        # Feed an explicit context like Full Vision does
        ctx = AudioFeatureContext.synthesize_idle()
        dash.feed_audio(ctx)
        await pilot.pause()

        cards = list(dash.query(VisualizerCard))
        assert len(cards) == 2
        for card in cards:
            assert isinstance(card.canvas.feature_ctx.levels_128, np.ndarray)
            # Must render without TypeError
            rendered = card.canvas.render()
            assert rendered is not None


async def test_dynamic_layout_engine_mounts_all_cards():
    """Verify that all cards (including 7 to 10 cards) are mounted across diverse layout styles."""
    app = DashboardTestApp()
    async with app.run_test() as pilot:
        dash = app.query_one("#test-dashboard", VisualDashboardWidget)

        test_10_cards = [
            {"card_id": f"c_{i}", "engine_id": "mirrored_dance", "palette": "cyan", "span": "normal", "tall": False}
            for i in range(10)
        ]

        styles_to_test = [
            "termusic_master_stack",
            "three_column_studio",
            "hero_top_split_bottom",
            "multi_tier_rack",
            "auto",
        ]

        for style in styles_to_test:
            dash.layout_style = style
            dash.cards = list(test_10_cards)
            dash._refresh_canvas()
            await pilot.pause()

            mounted_cards = list(app.query(VisualizerCard))
            assert len(mounted_cards) == 10, (
                f"Layout style '{style}' mounted {len(mounted_cards)} cards instead of all 10!"
            )

