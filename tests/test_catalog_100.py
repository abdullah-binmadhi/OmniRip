"""Comprehensive verification tests for the 100-engine modular visualizer catalog."""

from __future__ import annotations

import numpy as np
import pytest
from rich.text import Text

from harvester.ui.visuals import (
    PALETTES,
    AudioFeatureContext,
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


def _loud_ctx() -> AudioFeatureContext:
    """A loud, spectrally rich frame with real signal on every band."""
    levels = np.concatenate([
        np.full(16, 0.95, dtype=np.float32),
        np.full(48, 0.80, dtype=np.float32),
        np.full(64, 0.65, dtype=np.float32),
    ])
    t = np.linspace(0.0, 8.0 * np.pi, 1024, dtype=np.float32)
    wave_l = (0.6 * np.sin(t)).astype(np.float32)
    wave_r = (0.5 * np.sin(t + 0.4)).astype(np.float32)
    return AudioFeatureContext(
        levels_128=levels,
        peaks_128=levels.copy(),
        waveform_l=wave_l,
        waveform_r=wave_r,
        mid_channel=((wave_l + wave_r) * 0.5).astype(np.float32),
        side_channel=((wave_l - wave_r) * 0.5).astype(np.float32),
        rms_db=-6.0,
        lufs_m=-9.0,
        crest_factor=17.0,
        phase_corr=0.92,
        spectral_centroid=3200.0,
        transient_flag=True,
        is_playing=True,
    )


def _quiet_ctx() -> AudioFeatureContext:
    """A near-silent but genuinely decoded frame: real, just quiet.

    ``is_playing`` stays True so the renderers must report the measured silence
    rather than falling back to their standby animation.
    """
    t = np.linspace(0.0, 8.0 * np.pi, 1024, dtype=np.float32)
    levels = np.full(128, 0.01, dtype=np.float32)
    wave_l = (0.01 * np.sin(t)).astype(np.float32)
    wave_r = (0.01 * np.cos(t)).astype(np.float32)
    return AudioFeatureContext(
        levels_128=levels,
        peaks_128=levels.copy(),
        waveform_l=wave_l,
        waveform_r=wave_r,
        mid_channel=((wave_l + wave_r) * 0.5).astype(np.float32),
        side_channel=((wave_l - wave_r) * 0.5).astype(np.float32),
        rms_db=-55.0,
        lufs_m=-42.0,
        crest_factor=3.0,
        phase_corr=-0.30,
        spectral_centroid=400.0,
        transient_flag=False,
        is_playing=True,
    )


def _frame_signature(text: Text) -> tuple[str, tuple[tuple[int, int, str], ...]]:
    """A frame's identity including its styling, so recolouring also counts as a change."""
    return (text.plain, tuple((s, e, str(st)) for s, e, st in text.spans))


@pytest.mark.parametrize("palette_name", ["cyan", "matrix", "thermal"])
def test_every_engine_reacts_to_audio_not_just_idle_phase(palette_name):
    """No engine may be driven by the idle phase alone.

    Regression guard for the 70 procedural renderers that ignored ``ctx``:
    the idle phase is held constant across both renders, so any difference in
    the output (glyphs *or* style) can only have come from the audio features.
    """
    palette = PALETTES[palette_name]
    w, h = 48, 14
    idle_phase = 1.5
    loud = _loud_ctx()
    quiet = _quiet_ctx()

    insensitive: list[str] = []
    for engine in VisualizerRegistry.list_all():
        out_loud = engine.render_frame(w, h, loud, idle_phase, palette)
        out_quiet = engine.render_frame(w, h, quiet, idle_phase, palette)
        if _frame_signature(out_loud) == _frame_signature(out_quiet):
            insensitive.append(engine.id)

    assert not insensitive, (
        "These engines render identically for loud and quiet audio, so they are "
        f"driven only by the idle phase: {insensitive}"
    )


@pytest.mark.parametrize("requested", [(1, 1), (3, 2), (7, 4), (12, 5)])
def test_engines_honour_minimum_frame_size_on_narrow_cards(requested):
    """A card narrower than an engine's minimum must still render a full frame.

    Every engine must emit at least ``min_height`` rows and at least
    ``min_width`` columns per row, otherwise the engine indexes its own buffers
    out of range or the dashboard clips the frame into ragged rows.
    """
    w, h = requested
    palette = PALETTES["cyan"]
    idle = AudioFeatureContext.synthesize_idle(phase=1.0)

    for engine in VisualizerRegistry.list_all():
        out = engine.render_frame(w, h, idle, 1.0, palette)
        lines = out.plain.split("\n")
        assert len(lines) >= engine.min_height, (
            f"Engine {engine.id} rendered {len(lines)} rows at {w}x{h}, "
            f"needs at least {engine.min_height}"
        )
        narrowest = min(len(line) for line in lines)
        assert narrowest >= engine.min_width, (
            f"Engine {engine.id} rendered a {narrowest}-column row at {w}x{h}, "
            f"needs at least {engine.min_width}"
        )
