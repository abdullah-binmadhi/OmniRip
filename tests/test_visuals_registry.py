"""Unit tests for the modular VisualizerRegistry and foundational visualizer engines."""

from __future__ import annotations

from harvester.ui.visuals import (
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
    PALETTES,
    VisualizerRegistry,
)


def test_audio_feature_context_idle_synthesis():
    ctx = AudioFeatureContext.synthesize_idle(phase=1.2)
    assert len(ctx.levels_128) == 128
    assert len(ctx.waveform_l) == 1024
    assert len(ctx.waveform_r) == 1024
    assert not ctx.is_playing
    assert ctx.rms_db < 0.0
    assert -30.0 < ctx.lufs_m < 0.0
    assert 0.0 < ctx.phase_corr <= 1.0


def test_color_palettes():
    assert "cyan" in PALETTES
    assert "matrix" in PALETTES
    assert "stanford" in PALETTES
    pal = PALETTES["cyan"]
    assert pal.primary_style() is not None
    assert pal.accent_style() is not None
    assert pal.dim_style() is not None


def test_visualizer_registry_discovery():
    all_engines = VisualizerRegistry.list_all()
    assert len(all_engines) >= 5

    mirrored = VisualizerRegistry.get("mirrored_dance")
    assert mirrored is not None
    assert mirrored.name == "Symmetrical Mirrored Dance"
    assert mirrored.category == "spectral"

    spectral_engines = VisualizerRegistry.list_by_category("spectral")
    assert any(e.id == "mirrored_dance" for e in spectral_engines)
    assert any(e.id == "spectrum_10band" for e in spectral_engines)

    osc_engines = VisualizerRegistry.list_by_category("oscilloscope")
    assert any(e.id == "phosphor_crt_wave" for e in osc_engines)
    assert any(e.id == "braille_smooth_wave" for e in osc_engines)

    search_hits = VisualizerRegistry.search("braille")
    assert len(search_hits) >= 1
    assert search_hits[0].id == "braille_smooth_wave"

    cats = VisualizerRegistry.categories()
    assert len(cats) == 8
    assert "spectral" in cats
    assert "waterfall_3d" in cats


def test_all_engines_render_frame_edge_to_edge():
    ctx_idle = AudioFeatureContext.synthesize_idle(phase=0.5)
    palette = PALETTES["cyan"]
    w, h = 60, 12

    for engine in VisualizerRegistry.list_all():
        assert isinstance(engine, BaseVisualizerEngine)
        rendered_text = engine.render_frame(w, h, ctx_idle, idle_phase=0.5, palette=palette)
        plain = rendered_text.plain
        assert len(plain) > 0
        lines = plain.split("\n")
        # Ensure rendered height matches target height within ±1
        assert abs(len(lines) - h) <= 1
