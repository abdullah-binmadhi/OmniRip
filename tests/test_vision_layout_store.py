"""Unit tests for Full Vision Layout Store and Persistence."""

from pathlib import Path

from harvester.services.vision_layout_store import (
    BUILTIN_LAYOUTS,
    VisionCardConfig,
    VisionLayout,
    VisionLayoutStore,
)


def test_builtin_layouts():
    store = VisionLayoutStore(storage_dir=Path("/tmp/test_omnirip_vision_layouts_empty"))
    layouts = store.list_layouts()
    assert len(layouts) >= 20

    y2k = store.get_layout("preset_y2k_aesthetic")
    assert y2k is not None
    assert y2k.name == "Y2K Chrome & Aqua Deck"
    assert y2k.stitch_theme_id == "y2k_aesthetic"

    matrix = store.get_layout("preset_matrix_terminal")
    assert matrix is not None
    assert matrix.stitch_theme_id == "matrix_terminal"

    solo = store.get_layout("builtin_solo_stanford")
    assert solo is not None
    assert solo.cards[0].engine_id == "stanford_sun_music_3d"


def test_save_load_custom_layout(tmp_path: Path):
    store = VisionLayoutStore(storage_dir=tmp_path)

    cards = [
        VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=True, tall_two=False, order=0),
        VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=True, order=1),
    ]
    layout = VisionLayout(
        layout_id="",
        name="Custom Neon Rig",
        description="Dual cyber monitors",
        stitch_theme_id="synthwave_dusk",
        gap_distance=2,
        cards=cards,
    )

    saved_path = store.save_layout(layout)
    assert saved_path.exists()
    assert layout.layout_id != ""

    # Load back
    loaded = store.get_layout(layout.layout_id)
    assert loaded is not None
    assert loaded.name == "Custom Neon Rig"
    assert loaded.gap_distance == 2
    assert loaded.stitch_theme_id == "synthwave_dusk"
    assert len(loaded.cards) == 2
    assert loaded.cards[0].engine_id == "stanford_sun_music_3d"
    assert loaded.cards[1].engine_id == "matrix_digital_rain"

    # List includes both builtins and custom
    all_layouts = store.list_layouts()
    assert any(ly.layout_id == layout.layout_id for ly in all_layouts)

    # Delete custom layout
    assert store.delete_layout(layout.layout_id) is True
    assert not saved_path.exists()

    # Deleting builtin is prevented
    assert store.delete_layout("builtin_solo_stanford") is False


def test_thematic_presets_use_distinct_renderer_families_per_preset():
    """Engine names and palettes do not count as distinct visuals."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    presets = [layout for layout in BUILTIN_LAYOUTS if layout.layout_id.startswith("preset_")]
    assert len(presets) == 20

    for layout in presets:
        assert len(layout.cards) == 10, f"{layout.layout_id} must retain 10 panels"
        family_ids = []
        for card in layout.cards:
            engine = VisualizerRegistry.get(card.engine_id)
            assert engine is not None, f"Unknown engine {card.engine_id} in {layout.layout_id}"
            family_id = getattr(engine, "visual_family_id", None)
            assert family_id, f"{card.engine_id} has no semantic renderer-family identity"
            family_ids.append(family_id)

        assert len(set(family_ids)) == len(family_ids), (
            f"{layout.layout_id} repeats a renderer family: {family_ids}"
        )


def test_starter_layouts_use_distinct_renderer_families_per_layout():
    """Each visible panel in a starter layout has its own graph renderer."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    starters = [layout for layout in BUILTIN_LAYOUTS if layout.layout_id.startswith("builtin_")]
    assert len(starters) == 3

    for layout in starters:
        family_ids = []
        for card in layout.cards:
            engine = VisualizerRegistry.get(card.engine_id)
            assert engine is not None, f"Unknown engine {card.engine_id} in {layout.layout_id}"
            family_id = getattr(engine, "visual_family_id", None)
            assert family_id, f"{card.engine_id} has no semantic renderer-family identity"
            family_ids.append(family_id)

        assert len(set(family_ids)) == len(family_ids), (
            f"{layout.layout_id} repeats a renderer family: {family_ids}"
        )


