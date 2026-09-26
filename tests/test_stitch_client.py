"""Unit tests for Google Stitch API Integration and Design Synthesis."""

import json

from harvester.services.stitch import StitchClient, StitchVisualDesign


def test_stitch_client_init_and_themes():
    client = StitchClient(api_key="custom_test_key")
    assert client.api_key == "custom_test_key"

    themes = client.get_all_themes()
    assert len(themes) >= 20
    assert "cyberpunk_2077" in themes
    assert "matrix_terminal" in themes
    assert "y2k_aesthetic" in themes
    assert "synthwave_dusk" in themes
    assert "tokyo_midnight" in themes
    assert "lofi_chill_vinyl" in themes
    assert "dungeon_synth_crypt" in themes
    assert "nordic_aurora_fjord" in themes

    theme = client.get_theme("cyberpunk_2077")
    assert "Cyberpunk" in theme.name
    assert theme.primary_color == "#00ffcc"

    css_dict = theme.to_css_dict()
    assert css_dict["primary"] == "#00ffcc"
    assert css_dict["background"] == "#0a0e14"


def test_stitch_synthesize_design():
    client = StitchClient()

    # Test 3D landscape recommendation
    design_3d = client.synthesize_design("3D Mountain Wireframe Terrain")
    assert isinstance(design_3d, StitchVisualDesign)
    assert any("3d" in eng for eng in design_3d.engine_recommendations)

    # Test Matrix code recommendation
    design_matrix = client.synthesize_design("Cyber Matrix Rain Code")
    assert any("matrix" in eng for eng in design_matrix.engine_recommendations)

    # Export JSON
    json_str = client.export_design_json(design_3d)
    data = json.loads(json_str)
    assert data["design_id"] == design_3d.design_id
    assert "cyberpunk" in data["theme"]["theme_id"]
