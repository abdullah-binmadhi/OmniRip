"""Unit tests for Full Vision Layout Store and Persistence."""

from pathlib import Path
import pytest

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


def test_preset_engine_diversity():
    """Verify that all 20 presets have at least 80% unique visualizer engines (<= 20% similarity)."""
    presets = [ly for ly in BUILTIN_LAYOUTS if ly.layout_id.startswith("preset_")]
    assert len(presets) == 20

    # Collect all engines used across presets
    all_engines = set()
    preset_engines = {}

    for ly in presets:
        engines = [c.engine_id for c in ly.cards]
        assert len(engines) >= 3, f"Preset {ly.layout_id} must have at least 3 visualizer engines"
        preset_engines[ly.layout_id] = set(engines)
        all_engines.update(engines)
        # Verify anime character and structural style are set
        assert ly.anime_character_id != ""
        assert ly.ui_structure_style != ""
        assert ly.button_style_mode != ""

    # At least 60 distinct visualizer engines must be utilized across the presets
    assert len(all_engines) >= 60, f"Expected at least 60 distinct engines utilized, got {len(all_engines)}"

    # Check pairwise similarity between every preset pair
    preset_ids = list(preset_engines.keys())
    for i in range(len(preset_ids)):
        for j in range(i + 1, len(preset_ids)):
            id_a = preset_ids[i]
            id_b = preset_ids[j]
            set_a = preset_engines[id_a]
            set_b = preset_engines[id_b]

            intersection = set_a.intersection(set_b)
            smaller_len = min(len(set_a), len(set_b))
            similarity = len(intersection) / smaller_len if smaller_len > 0 else 0.0

            # Must not exceed 20% similarity (at least 80% unique)
            assert similarity <= 0.20, f"Presets {id_a} and {id_b} have {similarity:.2%} similarity (max allowed is 20%)"


def test_200_unique_engines_across_20_presets():
    """Verify that every preset has exactly 10 cards, and all 200 engines are 100% unique (0% overlap)."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    registered_ids = {e.id for e in VisualizerRegistry.list_all(include_presets=True)}
    presets = [ly for ly in BUILTIN_LAYOUTS if ly.layout_id.startswith("preset_")]
    assert len(presets) == 20

    all_cards = []
    for ly in presets:
        assert len(ly.cards) == 10, f"Preset {ly.layout_id} must have 10 cards, got {len(ly.cards)}"
        engine_ids = [c.engine_id for c in ly.cards]
        # Internal uniqueness
        assert len(set(engine_ids)) == 10, f"Duplicate engines inside preset {ly.layout_id}"
        # All engines must exist in registry
        for eid in engine_ids:
            assert eid in registered_ids, f"Engine {eid} in preset {ly.layout_id} is not registered!"
        all_cards.extend(engine_ids)

    # 100% uniqueness across the entire preset collection
    assert len(all_cards) == 200
    assert len(set(all_cards)) == 200, "Zero overlap allowed: every preset must have 100% unique engines!"


