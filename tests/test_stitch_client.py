"""Unit tests for Google Stitch API Integration and Design Synthesis."""

import json

import pytest

from harvester.services.stitch import (
    STITCH_BUILTIN_THEMES,
    StitchClient,
    StitchTheme,
    StitchVisualDesign,
    load_configured_stitch_key,
)


def test_stitch_client_init_and_themes():
    client = StitchClient(api_key="custom_test_key")
    assert client.api_key == "custom_test_key"

    themes = client.get_all_themes()
    assert "neon_cyber" in themes
    assert "synthwave_dusk" in themes
    assert "tokyo_midnight" in themes
    assert "sunset_gold" in themes

    theme = client.get_theme("neon_cyber")
    assert theme.name == "Neon Cyberpunk"
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
    assert data["theme"]["theme_id"] == "neon_cyber"
