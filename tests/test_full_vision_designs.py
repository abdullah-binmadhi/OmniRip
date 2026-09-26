import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.services.stitch import STITCH_BUILTIN_THEMES
from harvester.services.vision_layout_store import BUILTIN_LAYOUTS, PRESET_LAYOUTS
from harvester.ui.full_vision import FullVisionStudioWidget
from harvester.ui.full_vision_designs import (
    FULL_VISION_DESIGNS,
    SUPPORTED_DASHBOARD_LAYOUTS,
)


def test_every_builtin_layout_has_a_complete_distinct_art_direction():
    layout_ids = {layout.layout_id for layout in BUILTIN_LAYOUTS}
    assert set(FULL_VISION_DESIGNS) == layout_ids

    designs = list(FULL_VISION_DESIGNS.values())
    assert len({design.page_title for design in designs}) == len(layout_ids)
    assert len({design.motif for design in designs}) == len(layout_ids)

    for design in designs:
        assert design.eyebrow
        assert design.subtitle
        assert design.companion_heading
        assert len(design.top_controls) == 6
        assert design.dashboard_layout in SUPPORTED_DASHBOARD_LAYOUTS
        assert design.control_style
        assert design.title_style


def test_every_thematic_preset_uses_its_own_registered_theme():
    theme_ids = [layout.stitch_theme_id for layout in PRESET_LAYOUTS]
    assert len(theme_ids) == 20
    assert len(set(theme_ids)) == 20
    assert set(theme_ids) <= set(STITCH_BUILTIN_THEMES)


def test_every_starter_theme_resolves_without_generic_fallback():
    for layout in BUILTIN_LAYOUTS:
        assert layout.stitch_theme_id in STITCH_BUILTIN_THEMES, layout.layout_id


class _FullVisionDesignApp(App):
    def compose(self) -> ComposeResult:
        yield FullVisionStudioWidget()


@pytest.mark.asyncio
async def test_applying_y2k_rebuilds_page_chrome_and_controls():
    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        layout = studio.layout_store.get_layout("preset_y2k_aesthetic")
        assert layout is not None
        design = FULL_VISION_DESIGNS[layout.layout_id]

        studio.apply_layout(layout)
        await pilot.pause()

        assert str(app.query_one("#fvs-page-title", Label).render()) == design.page_title
        assert str(app.query_one("#fvs-theme-subtitle", Label).render()) == design.subtitle
        assert str(app.query_one("#btn-fvs-omnirip", Button).label) == design.top_controls[0]
        assert str(app.query_one("#btn-fvs-presets", Button).label) == design.top_controls[1]


@pytest.mark.asyncio
async def test_applying_preset_populates_its_curated_renderer_families():
    from harvester.ui.visual_dashboard import VisualDashboardWidget
    from harvester.ui.visuals.registry import VisualizerRegistry

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert layout is not None

        studio.apply_layout(layout)
        await pilot.pause()

        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        engine_ids = [card["engine_id"] for card in dashboard.cards]
        assert engine_ids == [card.engine_id for card in layout.cards]
        engines = [VisualizerRegistry.get(engine_id) for engine_id in engine_ids]
        assert all(engine is not None for engine in engines)
        family_ids = [engine.visual_family_id for engine in engines if engine is not None]
        assert len(family_ids) == 10
        assert len(set(family_ids)) == len(family_ids)
        assert dashboard.layout_style == FULL_VISION_DESIGNS[layout.layout_id].dashboard_layout


@pytest.mark.asyncio
async def test_preset_uses_its_art_directed_companion_identity():
    from harvester.ui.full_vision import AnimeCompanionWidget

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        layout = studio.layout_store.get_layout("preset_nordic_aurora")
        assert layout is not None
        design = FULL_VISION_DESIGNS[layout.layout_id]

        studio.apply_layout(layout)
        await pilot.pause()

        companion = app.query_one("#fvs-anime-companion", AnimeCompanionWidget)
        heading = companion.query_one("#anime-char-header", Label)
        assert str(heading.render()) == design.companion_heading
        assert companion.styles.background.hex.lower() == STITCH_BUILTIN_THEMES[
            layout.stitch_theme_id
        ].surface_color.lower()


@pytest.mark.asyncio
async def test_builtin_panels_inherit_the_theme_palette_and_remain_curated():
    from harvester.ui.visual_dashboard import VisualDashboardWidget, VisualizerCard
    from harvester.ui.visuals.base import ColorPalette
    from harvester.ui.visuals.registry import VisualizerRegistry

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        layout = studio.layout_store.get_layout("preset_chiptune_gameboy")
        assert layout is not None
        theme = STITCH_BUILTIN_THEMES[layout.stitch_theme_id]

        studio.apply_layout(layout)
        await pilot.pause()

        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        assert getattr(dashboard, "is_editable", True) is False
        cards = list(dashboard.query(VisualizerCard))
        assert len(cards) == 10
        assert all(getattr(card, "is_read_only", False) for card in cards)
        palette_override = getattr(cards[0].canvas, "palette_override", None)
        assert isinstance(palette_override, ColorPalette)
        assert palette_override.primary == theme.gradient_stops[0]
        engines = [VisualizerRegistry.get(card.engine_id) for card in cards]
        assert all(engine is not None for engine in engines)
        families = [engine.visual_family_id for engine in engines if engine is not None]
        assert len(set(families)) == 10


@pytest.mark.asyncio
async def test_matrix_page_uses_its_five_by_two_card_geometry():
    from harvester.ui.visual_dashboard import VisualDashboardWidget, VisualizerCard

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert layout is not None
        studio.apply_layout(layout)
        await pilot.pause()

        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        rows = list(dashboard.query(".vis-grid-row"))
        assert len(rows) == 2
        assert [len(list(row.query(VisualizerCard))) for row in rows] == [5, 5]


@pytest.mark.asyncio
async def test_full_vision_drives_all_animation_from_one_frame_clock():
    from harvester.ui.full_vision import AnimeCompanionWidget
    from harvester.ui.visual_dashboard import VisualDashboardWidget, VisualizerCard

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)):
        studio = app.query_one(FullVisionStudioWidget)
        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        companion = app.query_one("#fvs-anime-companion", AnimeCompanionWidget)
        cards = list(dashboard.query(VisualizerCard))

        assert getattr(studio, "_frame_timer", None) is not None
        assert getattr(dashboard, "clock_managed_externally", False) is True
        assert getattr(dashboard, "_anim_timer", None) is None
        assert getattr(companion, "clock_managed_externally", False) is True
        assert companion._anim_timer is None
        assert cards and all(
            getattr(card.canvas, "clock_managed_externally", False)
            and card.canvas._anim_timer is None
            for card in cards
        )
        old_tick = companion.tick
        old_phase = cards[0].canvas._idle_phase
        studio._tick_60fps()
        assert companion.tick == old_tick + 1
        assert cards[0].canvas._idle_phase > old_phase


@pytest.mark.asyncio
async def test_saving_a_builtin_preset_creates_an_editable_custom_copy(tmp_path):
    from harvester.services.vision_layout_store import VisionLayoutStore
    from harvester.ui.full_vision import FullVisionStudioWidget
    from harvester.ui.visual_dashboard import VisualDashboardWidget, VisualizerCard

    store = VisionLayoutStore(tmp_path)

    class SaveApp(App):
        def compose(self) -> ComposeResult:
            yield FullVisionStudioWidget(layout_store=store)

    app = SaveApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        y2k = studio.layout_store.get_layout("preset_y2k_aesthetic")
        assert y2k is not None and len(y2k.cards) == 10
        studio.apply_layout(y2k)
        await pilot.pause()
        studio._handle_save_layout("Y2K personal deck")
        await pilot.pause()

        saved_layout = studio.current_layout
        assert saved_layout is not None and not saved_layout.is_builtin
        assert saved_layout.layout_id.startswith("custom_")
        persisted = store.get_layout(saved_layout.layout_id)
        assert persisted is not None and all(card.palette == "theme" for card in persisted.cards)
        assert (store.layouts_dir / f"{saved_layout.layout_id}.json").is_file()

        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        assert dashboard.is_editable
        assert str(dashboard.query_one("#vis-dash-toolbar").styles.display) != "none"
        assert all(not card.is_read_only for card in dashboard.query(VisualizerCard))
        assert len(dashboard.cards) == 10


@pytest.mark.asyncio
async def test_custom_layouts_keep_legacy_geometry_and_allow_duplicate_families():
    from dataclasses import replace

    from harvester.services.vision_layout_store import VisionCardConfig
    from harvester.ui.full_vision import FullVisionStudioWidget
    from harvester.ui.visual_dashboard import VisualDashboardWidget, VisualizerCard
    from harvester.ui.visuals.registry import VisualizerRegistry

    app = _FullVisionDesignApp()
    async with app.run_test(size=(132, 42)) as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        base = studio.layout_store.get_layout("preset_y2k_aesthetic")
        assert base is not None
        custom = replace(
            base,
            layout_id="user_freeform",
            name="My freeform deck",
            description="No renderer uniqueness rules apply.",
            ui_structure_style="dos_mpxplay",
            button_style_mode="dos_keys",
            cards=[
                VisionCardConfig(engine_id=base.cards[0].engine_id, palette="cyan", order=i)
                for i in range(3)
            ],
            is_builtin=False,
        )
        studio.apply_layout(custom)
        await pilot.pause()

        dashboard = app.query_one("#fvs-dashboard", VisualDashboardWidget)
        assert dashboard.is_editable
        assert len(dashboard.cards) == 3
        assert studio.current_design is not None
        assert studio.current_design.dashboard_layout == "five_by_two"
        assert studio.current_design.control_style == "terminal"
        cards = list(dashboard.query(VisualizerCard))
        families = [
            engine.visual_family_id
            for card in cards
            if (engine := VisualizerRegistry.get(card.engine_id)) is not None
        ]
        assert len(cards) == 3 and len(set(families)) == 1
        assert all(not card.is_read_only for card in cards)
        assert all(card.canvas.palette_override is None for card in cards)

