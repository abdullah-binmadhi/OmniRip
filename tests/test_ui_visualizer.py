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
