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
