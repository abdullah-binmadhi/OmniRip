"""Phase 5 reskin acceptance: every built-in owns a distinct page grammar."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.services.vision_layout_store import VisionLayoutStore
from harvester.ui.companion import DESIGN_VOICES, SCENE_RECIPES
from harvester.ui.player_designs import PLAYER_PAGE_DESIGNS
from harvester.ui.player_layout import FAMILY_ROLE_LABELS, resolve_page
from harvester.ui.player_studio import PlayerStudioWidget


def _builtin_pairs():
    store = VisionLayoutStore()
    pairs = []
    for layout in store.list_layouts():
        design = PLAYER_PAGE_DESIGNS.get(layout.layout_id)
        if design is not None:
            pairs.append((layout, design))
    return pairs


def test_every_builtin_declares_a_complete_runtime_grammar():
    for _layout, design in _builtin_pairs():
        assert design.rail, design.layout_id
        assert design.rail_axis, design.layout_id
        assert design.button_family in FAMILY_ROLE_LABELS, design.layout_id
        assert design.button_frame, design.layout_id
        assert design.frame_glyphs, design.layout_id
        assert design.panel_slots.get("companion"), design.layout_id
        assert design.motion, design.layout_id


def test_structural_signatures_are_unique_per_preset():
    signatures: dict[tuple, str] = {}
    for layout, design in _builtin_pairs():
        page = resolve_page(design, layout)
        assert page.signature not in signatures, (
            f"{design.layout_id} shares {page.signature} with {signatures.get(page.signature)}"
        )
        signatures[page.signature] = design.layout_id
    assert len(signatures) == len(PLAYER_PAGE_DESIGNS) == 23


def test_visual_signatures_are_unique_per_preset():
    signatures: dict[tuple, str] = {}
    for _layout, design in _builtin_pairs():
        signature = (design.button_family, design.button_frame, design.frame_glyphs)
        assert signature not in signatures, (
            f"{design.layout_id} shares {signature} with {signatures.get(signature)}"
        )
        signatures[signature] = design.layout_id
    assert len(signatures) == 23


def test_companion_signatures_cover_every_preset():
    design_ids = set(PLAYER_PAGE_DESIGNS)
    assert set(SCENE_RECIPES) == design_ids
    assert set(DESIGN_VOICES) == design_ids
    scene_ids = [recipe.scene_id for recipe in SCENE_RECIPES.values()]
    assert len(set(scene_ids)) == len(scene_ids) == 23


class _PlayerApp(App):
    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(80, 24), (100, 30), (200, 50)])
async def test_every_builtin_applies_and_keeps_core_panels_visible(size):
    app = _PlayerApp()
    async with app.run_test(size=size) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        for layout, design in _builtin_pairs():
            studio.apply_layout(layout)
            await pilot.pause()

            rail = app.query_one("#plr-top-bar")
            companion = app.query_one("#plr-anime-companion")
            dock = app.query_one("#plr-bottom-dock")
            play = app.query_one("#btn-plr-play", Button)
            motif = app.query_one("#plr-motif", Label)

            assert rail.styles.display != "none", design.layout_id
            assert dock.styles.display != "none", design.layout_id
            assert companion.styles.display != "none", design.layout_id
            assert str(play.label), design.layout_id
            if design.panel_slots.get("motif") == "masthead":
                assert motif.styles.display != "none", design.layout_id
            assert studio._resolved_page is not None
            assert studio._resolved_page.design_id == design.layout_id
