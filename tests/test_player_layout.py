"""Unit tests for the PLAYER runtime page-layout orchestrator."""

from dataclasses import replace

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.services.vision_layout_store import VisionLayoutStore
from harvester.ui.player_designs import PLAYER_PAGE_DESIGNS
from harvester.ui.player_layout import (
    ButtonState,
    MotionDriver,
    render_button_label,
    resolve_page,
    role_label,
    theme_color_palette,
    theme_palette,
)
from harvester.ui.player_studio import AnimeCompanionWidget, PlayerStudioWidget


def _layout(layout_id: str = "preset_y2k_aesthetic"):
    layout = VisionLayoutStore().get_layout(layout_id)
    assert layout is not None
    return layout


def test_resolve_all_builtin_designs():
    store = VisionLayoutStore()
    resolved = []
    for layout in store.list_layouts():
        design = PLAYER_PAGE_DESIGNS.get(layout.layout_id)
        if design is None:
            continue
        page = resolve_page(design, layout)
        assert page.design_id == design.layout_id
        assert page.rail_style.get("dock")
        assert page.companion_style
        assert page.dock_style
        assert page.border_type
        resolved.append(page)

    assert len(resolved) == len(PLAYER_PAGE_DESIGNS) == 23


def test_resolve_falls_back_on_unknown_vocabulary():
    base = PLAYER_PAGE_DESIGNS["preset_y2k_aesthetic"]
    broken = replace(
        base,
        rail="nonsense",
        rail_axis="diagonal",
        panel_slots={"companion": "nowhere", "dock": "somewhere", "motif": "void"},
        frame_glyphs="neon",
    )
    page = resolve_page(broken, _layout())
    assert page.rail == "masthead"
    assert page.rail_axis == "horizontal"
    assert page.companion_slot == "rail_right"
    assert page.dock_slot == "footer"
    assert page.motif_slot == "masthead"
    assert page.border_type in ("heavy", "double", "round", "ascii", "tall", "solid", "dashed")


def test_button_role_labels_and_frames():
    state = ButtonState(playing=True, loop_mode="ALL", shuffle=True, queue_size=3)
    assert role_label("play", state) == "⏸ PAUSE"
    assert role_label("loop", state) == "🔁 LOOP: ALL"
    assert role_label("shuffle", state) == "🔀 SHUFFLE: ON"
    assert role_label("queue", state) == "QUEUE (3)"
    assert render_button_label("[F{n}:{label}]", "play", state) == "[F2:⏸ PAUSE]"
    assert render_button_label("【{label}】", "stop", state) == "【⏹ STOP】"


class _PlayerApp(App):
    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()


@pytest.mark.asyncio
async def test_page_grammar_applies_rail_slots_and_frames(monkeypatch):
    base = PLAYER_PAGE_DESIGNS["preset_y2k_aesthetic"]
    variant = replace(
        base,
        rail="rail_left",
        rail_axis="vertical",
        button_frame="[F{n}:{label}]",
        frame_glyphs="double",
        panel_slots={
            "companion": "footer",
            "dock": "header",
            "motif": "footer",
        },
        motion=(("blink", "idle", 1.0, "hold"),),
    )
    monkeypatch.setitem(PLAYER_PAGE_DESIGNS, variant.layout_id, variant)

    app = _PlayerApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        studio.apply_layout(_layout(variant.layout_id))
        await pilot.pause()

        rail = app.query_one("#plr-top-bar")
        companion = app.query_one("#plr-anime-companion", AnimeCompanionWidget)
        dock = app.query_one("#plr-bottom-dock")
        top_motif = app.query_one("#plr-motif", Label)
        dock_motif = app.query_one("#plr-dock-motif", Label)

        assert rail.styles.dock == "left"
        assert companion.styles.dock == "bottom"
        assert dock.styles.dock == "top"
        assert rail.styles.border_right[0] == "double"
        assert str(app.query_one("#btn-plr-play", Button).label).startswith("[F2:")
        assert top_motif.styles.display == "none"
        assert dock_motif.styles.display != "none"
        assert str(dock_motif.render()) == base.motif

        # Motion driver blinks the motif deterministically for masthead slots.
        monkeypatch.setitem(
            PLAYER_PAGE_DESIGNS,
            variant.layout_id,
            replace(variant, panel_slots={**variant.panel_slots, "motif": "masthead"}),
        )
        studio.apply_layout(_layout(variant.layout_id))
        await pilot.pause()
        driver = MotionDriver()
        driver.observe(studio, studio._resolved_page)
        first = str(top_motif.render())
        driver.tick += 30
        driver.observe(studio, studio._resolved_page)
        second = str(top_motif.render())
        assert first != second or first.strip().endswith("▌")


@pytest.mark.asyncio
async def test_motion_reduced_modes(monkeypatch):
    base = PLAYER_PAGE_DESIGNS["preset_y2k_aesthetic"]
    app = _PlayerApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        motif = app.query_one("#plr-motif", Label)
        subtitle = app.query_one("#plr-theme-subtitle", Label)

        hidden = replace(base, motion=(("blink", "idle", 1.0, "hide"),))
        monkeypatch.setitem(PLAYER_PAGE_DESIGNS, hidden.layout_id, hidden)
        studio.apply_layout(_layout(hidden.layout_id))
        await pilot.pause()
        driver = MotionDriver()
        for _ in range(5):
            driver.observe(studio, studio._resolved_page)
        assert str(motif.render()) == base.motif

        slow = replace(base, motion=(("marquee", "playing", 1.0, "slow"),))
        monkeypatch.setitem(PLAYER_PAGE_DESIGNS, slow.layout_id, slow)
        studio.apply_layout(_layout(slow.layout_id))
        await pilot.pause()
        driver = MotionDriver()
        driver.tick = 8
        driver.observe(studio, studio._resolved_page)
        assert str(subtitle.render()) == slow.subtitle[2:] + slow.subtitle[:2]

        held = replace(base, motion=(("marquee", "playing", 1.0, "hide"),))
        monkeypatch.setitem(PLAYER_PAGE_DESIGNS, held.layout_id, held)
        studio.apply_layout(_layout(held.layout_id))
        await pilot.pause()
        driver = MotionDriver()
        driver.tick = 20
        driver.observe(studio, studio._resolved_page)
        assert str(subtitle.render()) == held.subtitle


@pytest.mark.asyncio
async def test_theme_palette_drives_chrome_cards_companion_and_scene():
    layout = _layout("preset_matrix_terminal")
    app = _PlayerApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        studio.apply_layout(layout)
        await pilot.pause()

        theme = studio.current_theme
        palette = theme_palette(theme)
        assert studio.palette == palette

        rail = app.query_one("#plr-top-bar")
        assert rail.styles.background.hex.lower() == palette.surface.lower()

        companion = app.query_one("#plr-anime-companion", AnimeCompanionWidget)
        assert companion.styles.background.hex.lower() == palette.surface.lower()

        scene = app.query_one("#anime-char-scene", Label)
        assert scene.styles.color.hex.lower() == palette.accent.lower()

        dashboard = app.query_one("#plr-dashboard")
        override = dashboard.cards[0].get("palette_override")
        expected = theme_color_palette(theme)
        assert override is not None
        assert override.primary == expected.primary
        assert override.accent == expected.accent


@pytest.mark.asyncio
async def test_custom_layout_uses_canonical_design_and_stays_editable():
    from harvester.services.vision_layout_store import VisionLayout

    layout = VisionLayout(
        layout_id="user_freeform",
        name="Freeform",
        description="",
        stitch_theme_id="y2k_aesthetic",
        cards=[],
        is_builtin=False,
    )
    app = _PlayerApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        studio.apply_layout(layout)
        await pilot.pause()

        assert studio.current_design is not None
        assert studio.current_design.layout_id == "preset_matrix_terminal"
        page = studio._resolved_page
        assert page is not None
        assert page.rail == "masthead"
        assert studio.query_one("#plr-dashboard").is_editable
