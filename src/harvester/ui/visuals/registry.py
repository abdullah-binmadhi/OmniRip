"""VisualizerRegistry managing catalog discovery, categorization, and engine instantiation."""

from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
from rich.style import Style
from rich.text import Text

from harvester.ui.visuals.base import (
    _BLOCKS,
    _BRAILLE_MAP,
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
    clamp_frame_size,
)
from harvester.ui.visuals.headline_engines import (
    AudioFlameFireEngine,
    LissajousHarmonicsEngine,
    MatrixDigitalRainEngine,
    StanfordSunMusic3DEngine,
)

CATEGORIES: dict[str, tuple[str, str, str]] = {
    "spectral": ("⌗", "Spectral & FFT Analyzers", "Multi-band octave analyzers and peak gravity meters"),
    "oscilloscope": ("≋", "Oscilloscopes & CRT Traces", "Analog phosphor traces and continuous sub-pixel waveforms"),
    "waterfall_3d": ("▲", "Stanford 3D Waterfalls", "CCRMA-inspired isometric perspective terrain and spectrograms"),
    "stereo_phase": ("⌖", "Stereo Phase & Lissajous", "Goniometers, phase correlation compasses, and orbital Lissajous"),
    "cyber_matrix": ("⌬", "Cyberpunk Matrix & Generative", "Digital code rain, hex memory dumps, and generative ASCII"),
    "particles_fluid": ("✦", "Particle Systems & Fluid", "Acoustic fire, bass sparks, starfield warp, and fluid whirlpools"),
    "math_fractal": ("◈", "Geometric & Math Fractals", "Chladni nodal plates, Mandelbrot zooms, and sacred spirographs"),
    "studio_meters": ("𝄢", "Studio Forensic Telemetry", "EBU R128 loudness radar, K-System meters, and crest factor dials"),
}


class MirroredDanceEngine(BaseVisualizerEngine):
    """Symmetrical center-mirrored frequency dance with edge-to-edge gradient blocks."""

    id = "mirrored_dance"
    name = "Symmetrical Mirrored Dance"
    category = "spectral"
    icon = "⌗"
    description = "Center-mirrored dual gradient frequency pillars with standby ambient breathing waves."

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        # Honour the engine's advertised minimum size so narrow cards never clip.
        width, height = clamp_frame_size(width, height, self.min_width, self.min_height)
        text = Text()
        total_w = max(8, width)
        # Each column occupies 2 cells (glyph + gap) to fill total_w exactly.
        num_cols = max(4, total_w // 2)
        mid = max(1, height // 2)

        if ctx.is_active:
            col_levels = np.interp(
                np.linspace(0, 1, num_cols),
                np.linspace(0, 1, len(ctx.levels_128)),
                ctx.levels_128,
            ).astype(np.float32)
        else:
            col_levels = np.array([
                0.22 + 0.16 * math.sin(idle_phase * 1.6 + i * 0.45)
                + 0.10 * math.cos(idle_phase * 0.9 + i * 0.22)
                for i in range(num_cols)
            ], dtype=np.float32)
            col_levels = np.clip(col_levels, 0.06, 0.85)

        lines: list[list[tuple[str, Style]]] = [[] for _ in range(height)]
        style_primary = palette.primary_style()
        style_accent = palette.accent_style()
        style_dim = palette.dim_style()

        for col_idx in range(num_cols):
            lvl = float(col_levels[col_idx])
            up_h = int(lvl * mid)
            down_h = int(lvl * (height - mid - 1))

            for row in range(height):
                if row == mid:
                    char = "═"
                    style = style_primary
                elif row < mid:
                    dist = mid - row
                    if dist <= up_h:
                        char = "█"
                        style = style_primary if dist <= mid // 2 else style_accent
                    elif dist == up_h + 1 and lvl > 0.1:
                        char = "▄"
                        style = style_dim
                    else:
                        char = "·" if dist % 2 == 0 else " "
                        style = style_dim
                else:
                    dist = row - mid
                    if dist <= down_h:
                        char = "█"
                        style = style_primary if dist <= mid // 2 else style_accent
                    elif dist == down_h + 1 and lvl > 0.1:
                        char = "▀"
                        style = style_dim
                    else:
                        char = "·" if dist % 2 == 0 else " "
                        style = style_dim
                lines[row].append((char, style))
                lines[row].append((" ", style_dim))

        for r_idx, line in enumerate(lines):
            for char, style in line:
                text.append(char, style=style)
            if r_idx < height - 1:
                text.append("\n")
        return text


class Spectrum10BandEngine(BaseVisualizerEngine):
    """10-band ISO mastering octave analyzer with peak decay needles."""

    id = "spectrum_10band"
    name = "10-Band Mastering Spectrum"
    category = "spectral"
    icon = "⌗"
    description = "Calibrated 10-band mastering spectrum across standard ISO octaves with peak holds."
    min_width = 29

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        # Honour the engine's advertised minimum size so narrow cards never clip.
        width, height = clamp_frame_size(width, height, self.min_width, self.min_height)
        text = Text()
        n_bands = 10
        labels = ["31Hz", "63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"]
        total_w = max(20, width)
        col_total = max(3, total_w // n_bands)
        gap_w = 1 if col_total <= 4 else 2
        bar_w = max(2, col_total - gap_w)
        used_w = (bar_w + gap_w) * n_bands - gap_w
        margin_left = max(0, (total_w - used_w) // 2)

        band_levels = np.interp(
            np.linspace(0, 1, n_bands),
            np.linspace(0, 1, len(ctx.levels_128)),
            ctx.levels_128,
        ).astype(np.float32)

        spectrum_h = max(2, height - 1)
        lines: list[list[tuple[str, Style]]] = [[] for _ in range(spectrum_h)]

        for col_idx in range(n_bands):
            lvl = float(band_levels[col_idx])
            fill_h = lvl * (spectrum_h - 1)

            for row in range(spectrum_h):
                row_from_bot = spectrum_h - 1 - row
                if row_from_bot < int(fill_h):
                    char = "█"
                    style = palette.primary_style() if row_from_bot < spectrum_h // 2 else palette.accent_style()
                elif row_from_bot == int(fill_h):
                    frac = fill_h - int(fill_h)
                    char = _BLOCKS[int(round(frac * 8))]
                    style = palette.primary_style()
                else:
                    char = " "
                    style = palette.dim_style()
                lines[row].append((char * bar_w, style))
                if col_idx < n_bands - 1:
                    lines[row].append((" " * gap_w, palette.dim_style()))

        margin_str = " " * margin_left
        for line in lines:
            text.append(margin_str)
            for c_str, st in line:
                text.append(c_str, style=st)
            text.append("\n")

        # Ruler line
        ruler = Text()
        ruler.append(margin_str)
        for col_idx in range(n_bands):
            lbl = labels[col_idx][:bar_w].center(bar_w)
            ruler.append(lbl, style="dim cyan")
            if col_idx < n_bands - 1:
                ruler.append("─" * gap_w, style="dim #223344")
        text.append_text(ruler)
        return text


class PhosphorCrtWaveEngine(BaseVisualizerEngine):
    """Analog phosphor audio CRT oscilloscope waveform trace."""

    id = "phosphor_crt_wave"
    name = "Phosphor CRT Oscilloscope"
    category = "oscilloscope"
    icon = "≋"
    description = "True analog CRT oscilloscope with green phosphor decay and scanning reticle."

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        # Honour the engine's advertised minimum size so narrow cards never clip.
        width, height = clamp_frame_size(width, height, self.min_width, self.min_height)
        text = Text()
        grid = [[" " for _ in range(width)] for _ in range(height)]
        mid_y = height // 2

        interp_x = np.linspace(0, len(ctx.waveform_l) - 1, width)
        if ctx.is_active:
            samples = np.interp(interp_x, np.arange(len(ctx.waveform_l)), ctx.waveform_l)
        else:
            samples = np.array([
                0.28 * math.sin(idle_phase * 2.2 + col * (6.28 / max(1, width / 2)))
                * (0.8 + 0.2 * math.cos(idle_phase + col * 0.1))
                for col in range(width)
            ])

        for col in range(width):
            val = float(samples[col])
            row = int(round(mid_y - val * (mid_y - 1)))
            row = max(0, min(height - 1, row))
            grid[row][col] = "─" if abs(val) < 0.1 else ("╱" if val > 0 else "╲")

        for r in range(height):
            for c in range(width):
                char = grid[r][c]
                if char != " ":
                    text.append(char, style=palette.primary_style())
                elif r == mid_y:
                    text.append("·", style=palette.dim_style())
                elif c % 8 == 0 and r % 2 == 0:
                    text.append("·", style=palette.dim_style())
                else:
                    text.append(" ")
            if r < height - 1:
                text.append("\n")
        return text


class BrailleSmoothWaveEngine(BaseVisualizerEngine):
    """High-density 2x4 Unicode Braille audio wave matrix."""

    id = "braille_smooth_wave"
    name = "Braille Sub-Pixel Waveform"
    category = "oscilloscope"
    icon = "≋"
    description = "Ultra-dense 2x4 Unicode Braille sub-pixel continuous audio waveform matrix."

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        # Honour the engine's advertised minimum size so narrow cards never clip.
        width, height = clamp_frame_size(width, height, self.min_width, self.min_height)
        text = Text()
        grid_w = max(10, width - 1)
        grid_h = max(2, height)
        dot_w = grid_w * 2
        dot_h = grid_h * 4

        dots = np.zeros((dot_h, dot_w), dtype=bool)
        x_coords = np.arange(dot_w)

        if ctx.is_active:
            wave_scaled = np.interp(
                np.linspace(0, len(ctx.waveform_l) - 1, dot_w),
                np.arange(len(ctx.waveform_l)),
                ctx.waveform_l,
            )
        else:
            wave_scaled = np.array([
                0.32 * math.sin(idle_phase * 1.8 + i * 0.12)
                + 0.15 * math.cos(idle_phase * 0.7 + i * 0.05)
                for i in range(dot_w)
            ])

        mid_y = dot_h / 2.0
        y_coords = np.clip(mid_y + (wave_scaled * (dot_h * 0.44)), 0, dot_h - 1).astype(int)

        for x, y in zip(x_coords, y_coords, strict=False):
            dots[y, x] = True

        for char_y in range(grid_h):
            for char_x in range(grid_w):
                val = 0x2800
                base_x = char_x * 2
                base_y = char_y * 4
                for dx in range(2):
                    for dy in range(4):
                        cur_x = base_x + dx
                        cur_y = base_y + dy
                        if cur_x < dot_w and cur_y < dot_h and dots[cur_y, cur_x]:
                            val |= _BRAILLE_MAP[dx][dy]

                char = chr(val) if val != 0x2800 else " "
                style = palette.accent_style() if char != " " else palette.dim_style()
                text.append(char, style=style)
            if char_y < grid_h - 1:
                text.append("\n")
        return text


class StereoVuDeckEngine(BaseVisualizerEngine):
    """Wide stereo dual-channel VU meters with calibrated decibel scales and telemetry."""

    id = "stereo_vu_deck"
    name = "Stereo VU Deck & Telemetry"
    category = "studio_meters"
    icon = "𝄢"
    description = "Wide dual-channel stereo VU meters with multi-row dynamic mastering telemetry."
    min_width = 26

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        # Honour the engine's advertised minimum size so narrow cards never clip.
        width, height = clamp_frame_size(width, height, self.min_width, self.min_height)
        text = Text()
        bar_len = max(4, width - 16)

        half = len(ctx.levels_128) // 2
        if ctx.is_active:
            lvl_l = float(np.mean(ctx.levels_128[:half])) if half > 0 else 0.0
            lvl_r = float(np.mean(ctx.levels_128[half:])) if half > 0 else 0.0
        else:
            lvl_l = 0.35 + 0.15 * math.sin(idle_phase * 1.4)
            lvl_r = 0.35 + 0.15 * math.cos(idle_phase * 1.4)

        n_l = min(bar_len, int(lvl_l * bar_len))
        n_r = min(bar_len, int(lvl_r * bar_len))

        db_l = 20 * math.log10(max(1e-4, lvl_l)) if lvl_l > 0.05 else -60.0
        db_r = 20 * math.log10(max(1e-4, lvl_r)) if lvl_r > 0.05 else -60.0

        header = "[-40dB ─── -20dB ─── -10dB ─── -6dB ─── -3dB ─── 0dB ── +3dB ─── +6dB]"
        text.append(f"  {header[: width - 2]}\n", style="dim cyan")

        # Left Channel
        text.append("  L ❚", style="bold white")
        text.append("█" * n_l, style=palette.primary_style() if n_l < bar_len - 4 else palette.accent_style())
        text.append("░" * (bar_len - n_l), style="dim #223344")
        text.append(f"  {db_l:6.1f} dB\n", style=palette.primary_style())

        # Right Channel
        text.append("  R ❚", style="bold white")
        text.append("█" * n_r, style=palette.primary_style() if n_r < bar_len - 4 else palette.accent_style())
        text.append("░" * (bar_len - n_r), style="dim #223344")
        text.append(f"  {db_r:6.1f} dB\n", style=palette.primary_style())

        curr_row = 3
        if height >= 5:
            text.append(
                f"  TRUE PEAK: {ctx.rms_db + 3.0:4.1f} dBFS   LUFS: {ctx.lufs_m:4.1f}   CORR: {ctx.phase_corr:+4.2f}\n",
                style="bold yellow",
            )
            curr_row += 1
        if height >= 6:
            text.append(
                f"  CREST FACTOR: {ctx.crest_factor:4.1f} dB   CENTROID: {ctx.spectral_centroid:5.0f} Hz\n",
                style="dim cyan",
            )
            curr_row += 1
        while curr_row < height:
            dots = "· " * (width // 2)
            filler = f"  {dots[:width - 2]}"
            text.append(f"{filler}\n" if curr_row < height - 1 else filler, style="dim #102028")
            curr_row += 1
        return text


class VisualizerRegistry:
    """Master registry holding all available audio visualizer engines."""

    _engines: ClassVar[dict[str, type[BaseVisualizerEngine]]] = {}

    @classmethod
    def register(cls, engine_cls: type[BaseVisualizerEngine]) -> type[BaseVisualizerEngine]:
        """Register an engine class into the catalog."""
        cls._engines[engine_cls.id] = engine_cls
        return engine_cls

    @classmethod
    def get(cls, engine_id: str) -> BaseVisualizerEngine | None:
        """Instantiate and return an engine by its identifier."""
        engine_cls = cls._engines.get(engine_id)
        if engine_cls:
            return engine_cls()
        return None

    @classmethod
    def list_all(cls) -> list[BaseVisualizerEngine]:
        """Return instances of all registered visualizer engines."""
        return [engine_cls() for engine_cls in cls._engines.values()]

    @classmethod
    def list_by_category(cls, category: str) -> list[BaseVisualizerEngine]:
        """Filter visualizer engines by category."""
        return [
            engine_cls()
            for engine_cls in cls._engines.values()
            if engine_cls.category == category
        ]

    @classmethod
    def search(cls, query: str) -> list[BaseVisualizerEngine]:
        """Search visualizer engines by query keyword across name, category, and description."""
        q = query.strip().lower()
        if not q:
            return cls.list_all()
        return [
            engine_cls()
            for engine_cls in cls._engines.values()
            if q in engine_cls.name.lower()
            or q in engine_cls.category.lower()
            or q in engine_cls.description.lower()
            or q in engine_cls.id.lower()
        ]

    @classmethod
    def categories(cls) -> dict[str, tuple[str, str, str]]:
        """Return the dictionary of 8 categories with (icon, name, description)."""
        return dict(CATEGORIES)


# Register initial foundational engines
VisualizerRegistry.register(MirroredDanceEngine)
VisualizerRegistry.register(Spectrum10BandEngine)
VisualizerRegistry.register(PhosphorCrtWaveEngine)
VisualizerRegistry.register(BrailleSmoothWaveEngine)
VisualizerRegistry.register(StereoVuDeckEngine)

# Register Phase 3 headline engines
VisualizerRegistry.register(StanfordSunMusic3DEngine)
VisualizerRegistry.register(MatrixDigitalRainEngine)
VisualizerRegistry.register(LissajousHarmonicsEngine)
VisualizerRegistry.register(AudioFlameFireEngine)

# Register Phase 4 procedural engines (Completing all 100 engines across 8 packs)
from harvester.ui.visuals.catalog_100 import register_catalog_100  # noqa: E402

register_catalog_100()


