"""Modular Audio Visualizer Engine Core for OmniRip TUI."""

from __future__ import annotations

from harvester.ui.visuals.base import (
    PALETTES,
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
)
from harvester.ui.visuals.headline_engines import (
    AudioFlameFireEngine,
    LissajousHarmonicsEngine,
    MatrixDigitalRainEngine,
    StanfordSunMusic3DEngine,
)
from harvester.ui.visuals.registry import VisualizerRegistry

__all__ = [
    "AudioFeatureContext",
    "AudioFlameFireEngine",
    "BaseVisualizerEngine",
    "ColorPalette",
    "LissajousHarmonicsEngine",
    "MatrixDigitalRainEngine",
    "PALETTES",
    "StanfordSunMusic3DEngine",
    "VisualizerRegistry",
]

