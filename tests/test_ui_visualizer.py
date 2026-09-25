"""Unit tests for AudioVisualizer widget across all 5 visualizer modes."""

from __future__ import annotations

from textual.app import App, ComposeResult

from harvester.ui.visualizer import MODES_LIST, AudioVisualizer


class VisualizerTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioVisualizer(num_bands=16, cutoff_hz=16000.0, id="test-vis")


async def test_audio_visualizer_modes_and_render() -> None:
    app = VisualizerTestApp()
    async with app.run_test() as pilot:
        vis = app.query_one("#test-vis", AudioVisualizer)
        assert vis.mode == "spectrum"
        assert vis.num_bands == 16
        assert vis.cutoff_hz == 16000.0

        # Feed manual normalized levels
        levels = [0.05 * (i + 1) for i in range(16)]
        vis.feed_levels(levels)
        vis.is_playing = True

        # Test all 5 visualizer modes render non-empty content
        for expected_mode in MODES_LIST:
            assert vis.mode == expected_mode
            rendered = vis.render()
            assert rendered is not None
            assert len(rendered.plain) > 0
            # Advance to next mode
            vis.toggle_mode()

        # Cycle back to start
        assert vis.mode == "spectrum"
        await pilot.pause()


async def test_audio_visualizer_10bands_and_full_width_ruler() -> None:
    """Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler."""
    vis = AudioVisualizer(num_bands=10, cutoff_hz=15500.0)
    vis.is_playing = True
    vis.feed_levels([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

    rendered = vis._render_spectrum(width=100, height=8)
    plain = rendered.plain

    # Verify all 10 frequency band labels are present in the calibrated ruler
    for band_label in [
        "31Hz",
        "63Hz",
        "125Hz",
        "250Hz",
        "500Hz",
        "1kHz",
        "2kHz",
        "4kHz",
        "8kHz",
        "16kHz",
    ]:
        assert band_label in plain

    # Verify cutoff marker indicator
    assert "┆" in plain
    assert vis.cutoff_hz == 15500.0


async def test_audio_visualizer_spectrogram_and_phase_scope() -> None:
    """Verify Mode 6 (spectrogram waterfall) and Mode 7 (phase correlation scope)."""
    vis = AudioVisualizer(num_bands=10, cutoff_hz=16000.0)
    vis.is_playing = True
    vis.feed_levels([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

    # 1. Spectrogram waterfall test
    vis.mode = "spectrogram"
    rendered_spec = vis.render()
    assert rendered_spec is not None
    assert "16k" in rendered_spec.plain
    assert "1k" in rendered_spec.plain

    # Full height render includes lower frequencies
    full_spec = vis._render_spectrogram(width=60, height=10)
    assert "31" in full_spec.plain

    # 2. Phase scope healthy stereo
    vis.mode = "phase_scope"
    vis.set_phase_correlation(0.85, stereo_width_pct=110.0)
    rendered_phase = vis.render()
    assert "PHASE CORRELATION" in rendered_phase.plain
    assert "+0.85" in rendered_phase.plain
    assert "110%" in rendered_phase.plain
    assert "Phase alignment healthy" in rendered_phase.plain

    # 3. Phase scope cancellation warning
    vis.set_phase_correlation(-0.65, stereo_width_pct=140.0)
    rendered_warn = vis.render()
    assert "-0.65" in rendered_warn.plain
    assert "WARNING: Phase cancellation" in rendered_warn.plain
