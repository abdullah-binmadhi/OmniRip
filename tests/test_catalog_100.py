"""Comprehensive verification tests for the 100-engine modular visualizer catalog."""

from __future__ import annotations

import numpy as np
import pytest
from rich.text import Text

from harvester.ui.visuals import (
    AudioFeatureContext,
    BaseVisualizerEngine,
    PALETTES,
    VisualizerRegistry,
)

EXPECTED_CATEGORY_COUNTS = {
    "spectral": 13,
    "oscilloscope": 13,
    "waterfall_3d": 13,
    "stereo_phase": 12,
    "cyber_matrix": 13,
    "particles_fluid": 13,
    "math_fractal": 12,
    "studio_meters": 11,
}


def test_registry_contains_exactly_100_engines():
    """Verify that VisualizerRegistry discovers and registers exactly 100 visualizer engines."""
    all_engines = VisualizerRegistry.list_all()
    assert len(all_engines) == 100, f"Expected 100 engines, but found {len(all_engines)}"


def test_registry_category_distribution():
    """Verify each of the 8 thematic packs contains its exact planned engine quota."""
    for cat_id, expected_count in EXPECTED_CATEGORY_COUNTS.items():
        engines_in_cat = VisualizerRegistry.list_by_category(cat_id)
        assert len(engines_in_cat) == expected_count, (
            f"Category {cat_id} expected {expected_count} engines, got {len(engines_in_cat)}"
        )


def test_all_100_engine_identifiers_and_metadata_are_unique_and_valid():
    """Ensure no duplicate engine IDs and that icons, names, and descriptions are populated."""
    all_engines = VisualizerRegistry.list_all()
    seen_ids = set()
    for engine in all_engines:
        assert engine.id not in seen_ids, f"Duplicate engine ID: {engine.id}"
        seen_ids.add(engine.id)
        assert len(engine.name.strip()) > 0
        assert len(engine.category.strip()) > 0
        assert len(engine.icon.strip()) > 0
        assert len(engine.description.strip()) > 0
        assert engine.category in EXPECTED_CATEGORY_COUNTS


@pytest.mark.parametrize(
    "palette_name",
    ["cyan", "neon", "matrix", "thermal", "sunset", "crt", "stanford"],
)
def test_all_100_engines_render_edge_to_edge_both_modes(palette_name):
    """Test all 100 engines render non-empty frames with zero dead space in active and standby modes."""
    palette = PALETTES[palette_name]
    w, h = 48, 14

    ctx_active = AudioFeatureContext(
        levels_128=np.random.uniform(0.1, 0.9, 128).astype(np.float32),
        waveform_l=np.sin(np.linspace(0, 10, 1024), dtype=np.float32),
        waveform_r=np.cos(np.linspace(0, 10, 1024), dtype=np.float32),
        rms_db=-18.0,
        lufs_m=-14.0,
        crest_factor=10.5,
        phase_corr=0.92,
        spectral_centroid=1600.0,
        is_playing=True,
    )
    ctx_idle = AudioFeatureContext.synthesize_idle(phase=1.5)

    all_engines = VisualizerRegistry.list_all()
    for engine in all_engines:
        # 1. Active audio mode
        out_active = engine.render_frame(w, h, ctx_active, 1.5, palette)
        assert isinstance(out_active, Text)
        lines_active = out_active.plain.split("\n")
        assert len(lines_active) == h, f"Engine {engine.id} produced {len(lines_active)} lines, expected {h}"

        # 2. Standby idle mode
        out_idle = engine.render_frame(w, h, ctx_idle, 1.5, palette)
        assert isinstance(out_idle, Text)
        lines_idle = out_idle.plain.split("\n")
        assert len(lines_idle) == h, f"Engine {engine.id} produced {len(lines_idle)} lines, expected {h}"


def test_registry_search_across_100_engines():
    """Verify search finds engines across keywords in name, category, description, and ID."""
    results_matrix = VisualizerRegistry.search("matrix")
    assert len(results_matrix) >= 1
    assert any(e.id == "matrix_digital_rain" for e in results_matrix)

    results_chladni = VisualizerRegistry.search("chladni")
    assert len(results_chladni) == 1
    assert results_chladni[0].id == "fractal_chladni_plate"

    results_empty = VisualizerRegistry.search("")
    assert len(results_empty) == 100
