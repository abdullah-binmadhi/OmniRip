"""Unit tests for AudioVisualizer widget (spectrum & oscilloscope modes)."""

from __future__ import annotations

import numpy as np
from textual.app import App, ComposeResult

from harvester.ui.visualizer import AudioVisualizer


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
        levels = [0.1 * i for i in range(16)]
        vis.feed_levels(levels)
        rendered = vis.render()
        assert rendered is not None
        assert len(rendered.plain) > 0

        # Toggle to oscilloscope mode
        new_mode = vis.toggle_mode()
        assert new_mode == "oscilloscope"
        assert vis.mode == "oscilloscope"
        rendered_wave = vis.render()
        assert rendered_wave is not None

        # Feed raw PCM data
        pcm = np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, 4410)).astype(np.float32)
        vis.feed_pcm(pcm, sample_rate=44100)
        assert vis._levels is not None
        await pilot.pause()
