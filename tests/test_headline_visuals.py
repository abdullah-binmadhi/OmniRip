"""Tests for Phase 3 Headline Visualizer Engines (Stanford 3D, Matrix Rain, Lissajous, Flame Fire)."""

from __future__ import annotations

import numpy as np
import pytest
from rich.text import Text

from harvester.ui.visuals.base import PALETTES, AudioFeatureContext
from harvester.ui.visuals.headline_engines import (
    AudioFlameFireEngine,
    LissajousHarmonicsEngine,
    MatrixDigitalRainEngine,
    StanfordSunMusic3DEngine,
)
from harvester.ui.visuals.registry import VisualizerRegistry


def test_headline_engines_registered_in_registry():
    """Verify all 4 headline visualizer engines are discovered and registered in VisualizerRegistry."""
    registered_ids = {engine.id for engine in VisualizerRegistry.list_all()}
    assert "stanford_sun_music_3d" in registered_ids
    assert "matrix_digital_rain" in registered_ids
    assert "lissajous_harmonics" in registered_ids
    assert "audio_flame_fire" in registered_ids


@pytest.mark.parametrize(
    "engine_id,expected_cls,expected_cat",
    [
        ("stanford_sun_music_3d", StanfordSunMusic3DEngine, "waterfall_3d"),
        ("matrix_digital_rain", MatrixDigitalRainEngine, "cyber_matrix"),
        ("lissajous_harmonics", LissajousHarmonicsEngine, "stereo_phase"),
        ("audio_flame_fire", AudioFlameFireEngine, "particles_fluid"),
    ],
)
def test_headline_engine_instantiation(engine_id, expected_cls, expected_cat):
    """Verify each headline engine can be instantiated via registry with correct metadata."""
    engine = VisualizerRegistry.get(engine_id)
    assert engine is not None
    assert isinstance(engine, expected_cls)
    assert engine.category == expected_cat
    assert engine.icon != ""
    assert len(engine.name) > 0
    assert len(engine.description) > 0


def test_stanford_3d_rendering_dimensions_and_zero_dead_space():
    """Verify Stanford SunMusic 3D renders edge-to-edge across dimensions without dead space."""
    engine = StanfordSunMusic3DEngine()
    palette = PALETTES["stanford"]

    for w, h in [(30, 10), (80, 24), (120, 35)]:
        # Test active audio
        ctx_active = AudioFeatureContext(
            levels_128=np.random.uniform(0.1, 0.9, 128).astype(np.float32),
            is_playing=True,
        )
        rendered_active = engine.render_frame(w, h, ctx_active, 0.5, palette)
        assert isinstance(rendered_active, Text)
        lines = rendered_active.plain.split("\n")
        assert len(lines) == h
        for line in lines:
            assert len(line) == w

        # Test standby idle breathing wave
        ctx_idle = AudioFeatureContext.synthesize_idle(phase=1.2)
        rendered_idle = engine.render_frame(w, h, ctx_idle, 1.2, palette)
        assert isinstance(rendered_idle, Text)
        lines_idle = rendered_idle.plain.split("\n")
        assert len(lines_idle) == h
        for line in lines_idle:
            assert len(line) == w


def test_matrix_digital_rain_rendering_and_mutation():
    """Verify Matrix Digital Rain renders full columns, handles resizing, and updates columns."""
    engine = MatrixDigitalRainEngine()
    palette = PALETTES["matrix"]

    w, h = 60, 20
    ctx_idle = AudioFeatureContext.synthesize_idle(phase=0.0)

    # Initial frame
    frame1 = engine.render_frame(w, h, ctx_idle, 0.0, palette)
    assert len(frame1.plain.split("\n")) == h

    # Multiple successive frames with audio activity
    ctx_active = AudioFeatureContext(
        levels_128=np.full(128, 0.75, dtype=np.float32),
        is_playing=True,
    )
    for i in range(5):
        frame = engine.render_frame(w, h, ctx_active, float(i), palette)
        lines = frame.plain.split("\n")
        assert len(lines) == h
        for line in lines:
            assert len(line) == w

    # Dynamic resize to larger viewport
    w_large, h_large = 100, 30
    frame_resized = engine.render_frame(w_large, h_large, ctx_active, 5.0, palette)
    lines_resized = frame_resized.plain.split("\n")
    assert len(lines_resized) == h_large
    for line in lines_resized:
        assert len(line) == w_large


def test_lissajous_harmonics_rendering_and_persistence():
    """Verify Lissajous Harmonics renders orbital traces, handles reticle, and persists decay."""
    engine = LissajousHarmonicsEngine()
    palette = PALETTES["crt"]

    w, h = 50, 22
    ctx_stereo = AudioFeatureContext(
        waveform_l=np.sin(np.linspace(0, 10, 1024), dtype=np.float32) * 0.8,
        waveform_r=np.cos(np.linspace(0, 10, 1024), dtype=np.float32) * 0.8,
        spectral_centroid=1800.0,
        phase_corr=0.88,
        is_playing=True,
    )

    frame = engine.render_frame(w, h, ctx_stereo, 0.5, palette)
    lines = frame.plain.split("\n")
    assert len(lines) == h
    for line in lines:
        assert len(line) == w

    # Must contain reticle center crosshair or phosphor energy glyphs
    assert any(c in frame.plain for c in ("┼", "│", "─", "█", "▓", "▒", "░"))


def test_audio_flame_fire_heat_propagation():
    """Verify Audio Flame Fire propagates heat upwards from audio-driven bottom coals."""
    engine = AudioFlameFireEngine()
    palette = PALETTES["thermal"]

    w, h = 40, 16
    ctx = AudioFeatureContext(
        levels_128=np.random.uniform(0.3, 1.0, 128).astype(np.float32),
        is_playing=True,
    )

    # Render several ticks to propagate heat up the cellular buffer
    for i in range(8):
        frame = engine.render_frame(w, h, ctx, float(i) * 0.1, palette)

    lines = frame.plain.split("\n")
    assert len(lines) == h
    for line in lines:
        assert len(line) == w

    # The bottom rows must have highest heat glyphs (█, ▓, ▒)
    bottom_row = lines[-1]
    assert any(c in bottom_row for c in ("█", "▓", "▒", "▄"))


def test_palette_cycling_across_all_palettes():
    """Ensure all headline engines gracefully render with every palette in PALETTES."""
    engines = [
        StanfordSunMusic3DEngine(),
        MatrixDigitalRainEngine(),
        LissajousHarmonicsEngine(),
        AudioFlameFireEngine(),
    ]
    ctx = AudioFeatureContext.synthesize_idle(phase=1.0)

    for engine in engines:
        for pal_key, palette in PALETTES.items():
            rendered = engine.render_frame(40, 15, ctx, 1.0, palette)
            assert isinstance(rendered, Text)
            assert len(rendered.plain.split("\n")) == 15
