"""Base classes and data structures for modular audio visualizer engines."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
from rich.style import Style
from rich.text import Text


@dataclass
class AudioFeatureContext:
    """Acoustic and spectral features extracted from audio for visualizer rendering."""

    levels_128: np.ndarray = field(default_factory=lambda: np.zeros(128, dtype=np.float32))
    peaks_128: np.ndarray = field(default_factory=lambda: np.zeros(128, dtype=np.float32))
    waveform_l: np.ndarray = field(default_factory=lambda: np.zeros(1024, dtype=np.float32))
    waveform_r: np.ndarray = field(default_factory=lambda: np.zeros(1024, dtype=np.float32))
    mid_channel: np.ndarray = field(default_factory=lambda: np.zeros(1024, dtype=np.float32))
    side_channel: np.ndarray = field(default_factory=lambda: np.zeros(1024, dtype=np.float32))
    rms_db: float = -60.0
    lufs_m: float = -24.0
    crest_factor: float = 12.0
    phase_corr: float = 0.95
    spectral_centroid: float = 1200.0
    transient_flag: bool = False
    is_playing: bool = False

    @classmethod
    def synthesize_idle(cls, phase: float = 0.0) -> AudioFeatureContext:
        """Create a living ambient standby feature context to prevent empty dead space."""
        # Generate organic low-frequency breathing harmonics across 128 FFT bins
        idx = np.arange(128, dtype=np.float32)
        base = 0.22 * np.sin(phase * 1.5 + idx * 0.08) + 0.12 * np.cos(phase * 0.8 + idx * 0.04)
        levels = np.clip(0.18 + base, 0.04, 0.75).astype(np.float32)

        # Generate smooth continuous sine waveform
        t = np.linspace(0, 4 * math.pi, 1024, dtype=np.float32)
        wave_l = (0.28 * np.sin(t + phase * 2.0) + 0.10 * np.sin(3 * t - phase)).astype(np.float32)
        wave_r = (0.28 * np.sin(t + phase * 2.0 + 0.1) + 0.10 * np.sin(3 * t - phase + 0.2)).astype(np.float32)
        mid = ((wave_l + wave_r) * 0.5).astype(np.float32)
        side = ((wave_l - wave_r) * 0.5).astype(np.float32)

        return cls(
            levels_128=levels,
            peaks_128=levels.copy(),
            waveform_l=wave_l,
            waveform_r=wave_r,
            mid_channel=mid,
            side_channel=side,
            rms_db=-24.0 + 3.0 * math.sin(phase * 1.2),
            lufs_m=-18.0 + 2.0 * math.sin(phase * 1.2),
            crest_factor=11.5 + 1.5 * math.cos(phase),
            phase_corr=0.92 + 0.06 * math.sin(phase * 0.5),
            spectral_centroid=1450.0 + 300.0 * math.sin(phase * 0.9),
            transient_flag=False,
            is_playing=False,
        )


@dataclass(frozen=True)
class ColorPalette:
    """Color palette definition for visualizer rendering."""

    id: str
    name: str
    primary: str
    secondary: str
    accent: str
    background: str
    dim: str

    def primary_style(self, bold: bool = True) -> Style:
        prefix = "bold " if bold else ""
        return Style.parse(f"{prefix}{self.primary}")

    def accent_style(self, bold: bool = True) -> Style:
        prefix = "bold " if bold else ""
        return Style.parse(f"{prefix}{self.accent}")

    def dim_style(self) -> Style:
        return Style.parse(self.dim)


PALETTES: dict[str, ColorPalette] = {
    "cyan": ColorPalette(
        id="cyan",
        name="Cyber Cyan",
        primary="#00e5ff",
        secondary="#0088cc",
        accent="#ff007f",
        background="#0a1218",
        dim="#0d303d",
    ),
    "neon": ColorPalette(
        id="neon",
        name="Neon Pulse",
        primary="#ff007f",
        secondary="#b000ff",
        accent="#00ffcc",
        background="#140a1c",
        dim="#441155",
    ),
    "matrix": ColorPalette(
        id="matrix",
        name="Matrix Green",
        primary="#00ff66",
        secondary="#009933",
        accent="#ffffff",
        background="#051408",
        dim="#003810",
    ),
    "thermal": ColorPalette(
        id="thermal",
        name="Thermal Fire",
        primary="#ff3300",
        secondary="#ff9900",
        accent="#ffff33",
        background="#1a0805",
        dim="#4a1505",
    ),
    "sunset": ColorPalette(
        id="sunset",
        name="Synth Sunset",
        primary="#ff7700",
        secondary="#ff0088",
        accent="#00eeff",
        background="#1c0b16",
        dim="#4d1b37",
    ),
    "crt": ColorPalette(
        id="crt",
        name="CRT Phosphor",
        primary="#39ff14",
        secondary="#20aa0b",
        accent="#70ff50",
        background="#051508",
        dim="#0b3815",
    ),
    "stanford": ColorPalette(
        id="stanford",
        name="Stanford CCRMA",
        primary="#ffaa00",
        secondary="#cc6600",
        accent="#00ccff",
        background="#161208",
        dim="#4a3610",
    ),
}


class BaseVisualizerEngine(ABC):
    """Abstract base class for all 100 modular audio visualizer engines."""

    id: str
    name: str
    category: str
    icon: str
    description: str
    min_width: int = 10
    min_height: int = 4

    @abstractmethod
    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        """Render a single frame filling width x height completely with zero dead space."""
        ...
