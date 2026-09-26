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
