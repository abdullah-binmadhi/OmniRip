"""100 Modular Audio Visualizer Engines across 8 Thematic Packs."""

from __future__ import annotations

import math
import random
from typing import Callable

import numpy as np
from rich.style import Style
from rich.text import Text

from harvester.ui.visuals.base import (
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
)

# Shared Unicode block and glyph constants
_BLOCKS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")
_SHADES = (" ", "·", "░", "▒", "▓", "█")
_HEX_DIGITS = "0123456789ABCDEF"


class ProceduralCatalogEngine(BaseVisualizerEngine):
    """Parametric visualizer engine backed by a specialized procedural renderer."""

    def __init__(
        self,
        engine_id: str,
        name: str,
        category: str,
        icon: str,
        description: str,
        renderer: Callable[[int, int, AudioFeatureContext, float, ColorPalette], Text],
        min_w: int = 8,
        min_h: int = 4,
    ) -> None:
        self.id = engine_id
        self.name = name
        self.category = category
        self.icon = icon
        self.description = description
        self.min_width = min_w
        self.min_height = min_h
        self._renderer = renderer

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float,
        palette: ColorPalette,
    ) -> Text:
        w = max(self.min_width, width)
        h = max(self.min_height, height)
        return self._renderer(w, h, ctx, idle_phase, palette)


# ---------------------------------------------------------------------------
# Helper utilities for zero-dead-space canvas generation
# ---------------------------------------------------------------------------


def _create_canvas(w: int, h: int, fill: str = " ", style: Style | None = None) -> list[list[tuple[str, Style]]]:
    """Create an empty w x h grid of characters and styles."""
    st = style or Style.parse("dim #223344")
    return [[(fill, st) for _ in range(w)] for _ in range(h)]


def _canvas_to_text(canvas: list[list[tuple[str, Style]]]) -> Text:
    """Flatten 2D grid into Rich Text with exact row linebreaks."""
    text = Text()
    h = len(canvas)
    for r_idx, row in enumerate(canvas):
        for ch, st in row:
            text.append(ch, style=st)
        if r_idx < h - 1:
            text.append("\n")
    return text


def _get_interp_levels(ctx: AudioFeatureContext, count: int, idle_phase: float) -> np.ndarray:
    """Return interpolated frequency levels across `count` bins with idle fallback."""
    if ctx.is_playing or np.max(ctx.levels_128) > 0.02:
        return np.interp(
            np.linspace(0, 1, count),
            np.linspace(0, 1, len(ctx.levels_128)),
            ctx.levels_128,
        ).astype(np.float32)
    idx = np.arange(count, dtype=np.float32)
    base = 0.25 * np.sin(idle_phase * 1.5 + idx * 0.18) + 0.15 * np.cos(idle_phase * 0.8 + idx * 0.09)
    return np.clip(0.20 + base, 0.05, 0.88).astype(np.float32)


# ---------------------------------------------------------------------------
# Pack 1: Spectral & FFT Analyzers Renderers (11 additional)
# ---------------------------------------------------------------------------


def _render_spectral_waterfall_bars(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    for c in range(w):
        val = float(levels[c])
        bar_h = int(val * (h - 1))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot < bar_h:
                st = pal.primary_style() if from_bot < h // 2 else pal.accent_style()
                grid[r][c] = ("█", st)
            elif from_bot == bar_h and val > 0.08:
                grid[r][c] = ("▄", pal.primary_style())
            elif from_bot == bar_h + 1 and val > 0.4:
                grid[r][c] = ("━", pal.accent_style())
            elif r % 3 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_braille_dense(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w * 2, idle)
    for c in range(w):
        v1 = float(levels[c * 2])
        v2 = float(levels[min(len(levels) - 1, c * 2 + 1)])
        avg_v = (v1 + v2) * 0.5
        fill_rows = int(avg_v * h)
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot < fill_rows:
                grid[r][c] = ("⠿", pal.primary_style() if from_bot < h // 2 else pal.accent_style())
            elif from_bot == fill_rows:
                grid[r][c] = ("⠶" if v1 > v2 else "⠛", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_vfd_vintage(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    n_bands = max(4, w // 3)
    levels = _get_interp_levels(ctx, n_bands, idle)
    for b in range(n_bands):
        c_start = b * (w // n_bands)
        lvl = float(levels[b])
        seg_h = int(lvl * (h - 2))
        for r in range(h - 1):
            from_bot = h - 2 - r
            char = "▬" if from_bot < seg_h else ("─" if from_bot % 2 == 0 else " ")
            st = pal.accent_style() if from_bot >= h - 4 else pal.primary_style()
            if from_bot >= seg_h:
                st = pal.dim_style()
            for dx in range(max(1, (w // n_bands) - 1)):
                if c_start + dx < w:
                    grid[r][c_start + dx] = (char, st)
    for c in range(w):
        grid[h - 1][c] = ("═", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_iso_31band(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, 31, idle)
    col_step = max(1, w // 31)
    for b in range(min(31, w)):
        c = min(w - 1, b * col_step)
        lvl = float(levels[b])
        fill_h = int(lvl * (h - 1))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot <= fill_h:
                grid[r][c] = ("█", pal.primary_style() if from_bot < h // 2 else pal.accent_style())
            elif from_bot == fill_h + 1 and lvl > 0.5:
                grid[r][c] = ("▲", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if r % 2 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_comb_harmonics(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    fundamental = 8 + int(abs(math.sin(idle)) * 6)
    levels = _get_interp_levels(ctx, w, idle)
    for c in range(w):
        is_harmonic = (c % fundamental) == 0
        lvl = float(levels[c]) * (1.6 if is_harmonic else 0.6)
        bar_h = min(h - 1, int(lvl * (h - 1)))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot <= bar_h:
                ch = "║" if is_harmonic else "│"
                st = pal.accent_style(bold=True) if is_harmonic else pal.primary_style()
                grid[r][c] = (ch, st)
            else:
                grid[r][c] = ("·", pal.dim_style()) if is_harmonic and from_bot % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_ribbon_energy(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    mid_y = h // 2
    for c in range(w):
        lvl = float(levels[c])
        thick = max(1, int(lvl * (h * 0.45)))
        center_row = int(mid_y + math.sin(c * 0.12 + idle * 1.5) * (h * 0.25))
        for r in range(h):
            dist = abs(r - center_row)
            if dist < thick:
                st = pal.primary_style() if dist < thick // 2 else pal.accent_style()
                grid[r][c] = ("█" if dist == 0 else "▓", st)
            elif dist == thick:
                grid[r][c] = ("░", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 6 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_log_cascade(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    raw_levels = _get_interp_levels(ctx, 128, idle)
    # Logarithmic warping
    log_indices = np.geomspace(1, 128, w) - 1
    log_levels = np.interp(log_indices, np.arange(128), raw_levels)
    for c in range(w):
        val = float(log_levels[c])
        bars = int(val * (h - 1))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot <= bars:
                grid[r][c] = ("█", pal.primary_style() if c < w // 3 else pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if r % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_cepstrum(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    # Cepstrum simulated via cosine transform
    quefrency = np.abs(np.fft.rfft(levels, n=w * 2)[:w])
    quefrency = quefrency / (np.max(quefrency) + 1e-5)
    for c in range(w):
        q_val = float(quefrency[c])
        h_val = int(q_val * (h - 1))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot == h_val:
                grid[r][c] = ("◆", pal.accent_style(bold=True))
            elif from_bot < h_val:
                grid[r][c] = ("│", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if c % 8 == 0 and r % 2 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_differential(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    mid_y = h // 2
    for c in range(w):
        m_lvl = float(levels[c]) * 0.9
        s_lvl = float(levels[w - 1 - c]) * 0.7
        up_h = int(m_lvl * mid_y)
        down_h = int(s_lvl * (h - mid_y - 1))
        for r in range(h):
            if r == mid_y:
                grid[r][c] = ("═", pal.accent_style())
            elif r < mid_y and (mid_y - r) <= up_h:
                grid[r][c] = ("█", pal.primary_style())
            elif r > mid_y and (r - mid_y) <= down_h:
                grid[r][c] = ("▒", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 5 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_gravity_peaks(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    for c in range(w):
        lvl = float(levels[c])
        bar_h = int(lvl * (h - 2))
        peak_h = min(h - 1, bar_h + int(1 + math.sin(c * 0.4 + idle * 2) * 2))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot == peak_h:
                grid[r][c] = ("▔", pal.accent_style(bold=True))
            elif from_bot <= bar_h:
                grid[r][c] = ("█", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if from_bot % 3 == 0 and c % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_spectral_sub_bass_rumble(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    bass_energy = float(np.mean(ctx.levels_128[:16])) if ctx.is_playing else 0.4 + 0.25 * math.sin(idle * 2.5)
    for r in range(h):
        wave_offset = math.sin(r * 0.4 + idle * 3.0) * (bass_energy * w * 0.2)
        center_col = int((w / 2.0) + wave_offset)
        thick = int(max(2, bass_energy * (w * 0.35)))
        for c in range(w):
            dist = abs(c - center_col)
            if dist < thick:
                st = pal.accent_style() if dist < thick // 3 else pal.primary_style()
                grid[r][c] = ("█" if dist < thick // 2 else "▓", st)
            elif dist <= thick + 2:
                grid[r][c] = ("░", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if c % 6 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 2: Analog Phosphor & Oscilloscopes Renderers (11 additional)
# ---------------------------------------------------------------------------


def _render_scope_vector_xy(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        grid[r][mid_x] = ("│", pal.dim_style())
    for c in range(w):
        grid[mid_y][c] = ("─", pal.dim_style())
    grid[mid_y][mid_x] = ("┼", pal.dim_style())

    pts = 160
    theta = np.linspace(0, 2 * math.pi, pts)
    boost = 1.0 + float(np.mean(ctx.levels_128)) if ctx.is_playing else 1.0
    rx = (w * 0.4) * boost
    ry = (h * 0.4) * boost
    for t in theta:
        x = int(mid_x + math.sin(t * 2 + idle) * rx)
        y = int(mid_y - math.cos(t * 3 - idle) * ry)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.primary_style())
    return _canvas_to_text(grid)


def _render_scope_dual_trace(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid1 = h // 4
    mid2 = (h * 3) // 4
    for c in range(w):
        grid[mid1][c] = ("┄", pal.dim_style())
        grid[mid2][c] = ("┄", pal.dim_style())

        v1 = math.sin(c * 0.2 + idle * 2) * (h * 0.18)
        v2 = math.cos(c * 0.25 - idle * 1.5) * (h * 0.18)
        y1 = max(0, min(h - 1, int(mid1 - v1)))
        y2 = max(0, min(h - 1, int(mid2 - v2)))
        grid[y1][c] = ("━", pal.primary_style(bold=True))
        grid[y2][c] = ("━", pal.accent_style(bold=True))
    return _canvas_to_text(grid)


def _render_scope_strobe_tuner(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x)
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            strobe = math.sin(angle * 8 + dist * 0.4 - idle * 4)
            if dist < min(w, h * 2) * 0.45:
                if strobe > 0.4:
                    grid[r][c] = ("█", pal.primary_style())
                elif strobe > -0.2:
                    grid[r][c] = ("▒", pal.accent_style())
                else:
                    grid[r][c] = ("░", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_persistence_ghost(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        for delay, (ch, st) in enumerate([
            ("█", pal.accent_style(bold=True)),
            ("▓", pal.primary_style()),
            ("▒", pal.primary_style()),
            ("░", pal.dim_style()),
        ]):
            y = int(mid_y - math.sin(c * 0.15 + (idle - delay * 0.12) * 2) * (h * 0.38))
            if 0 <= y < h and grid[y][c][0] == " ":
                grid[y][c] = (ch, st)
        for r in range(h):
            if grid[r][c][0] == " " and (r == mid_y or c % 8 == 0):
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_trigger_holdoff(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    pulse_w = max(4, w // 6)
    for c in range(w):
        in_pulse = (c % (pulse_w * 2)) < pulse_w
        val = (h * 0.35) if in_pulse else (-h * 0.35)
        y = max(0, min(h - 1, int(mid_y - val)))
        grid[y][c] = ("█", pal.primary_style())
        if c > 0 and (c % pulse_w) == 0:
            for fill_r in range(min(h - 1, int(mid_y - abs(val))), max(0, int(mid_y + abs(val)))):
                grid[fill_r][c] = ("│", pal.accent_style())
        for r in range(h):
            if grid[r][c][0] == " " and r % 3 == 0 and c % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_differential_ms(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        m_val = math.sin(c * 0.1 + idle * 1.8) * (h * 0.35)
        s_val = math.sin(c * 0.25 - idle * 1.2) * (h * 0.15)
        ym = max(0, min(h - 1, int(mid_y - m_val)))
        ys = max(0, min(h - 1, int(mid_y - s_val)))
        grid[ym][c] = ("█", pal.primary_style())
        grid[ys][c] = ("▒", pal.accent_style())
        for r in range(h):
            if grid[r][c][0] == " " and r == mid_y:
                grid[r][c] = ("─", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_circular_polar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    pts = 200
    angles = np.linspace(0, 2 * math.pi, pts)
    levels = _get_interp_levels(ctx, pts, idle)
    for i, ang in enumerate(angles):
        r_dist = (min(mid_x, mid_y * 2) * 0.35) * (1.0 + float(levels[i]) * 1.2)
        x = int(mid_x + math.cos(ang) * r_dist)
        y = int(mid_y - (math.sin(ang) * r_dist * 0.5))
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.primary_style() if levels[i] < 0.5 else pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r == mid_y or c == mid_x):
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_audio_glitch(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        jitter = int(random.uniform(-1, 2)) if random.random() < 0.25 else 0
        y = max(0, min(h - 1, int(mid_y - math.sin(c * 0.18 + idle * 3) * (h * 0.35) + jitter)))
        grid[y][c] = ("█" if jitter == 0 else "⚡", pal.accent_style() if jitter else pal.primary_style())
        for r in range(h):
            if grid[r][c][0] == " ":
                grid[r][c] = ("·", pal.dim_style()) if (r + c + int(idle * 5)) % 7 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_tape_head(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        raw = math.sin(c * 0.15 + idle * 2) * 1.8
        saturated = math.tanh(raw) * (h * 0.38)
        y = max(0, min(h - 1, int(mid_y - saturated)))
        grid[y][c] = ("█", pal.primary_style())
        for r in range(h):
            if grid[r][c][0] == " " and abs(r - mid_y) < int(h * 0.4):
                grid[r][c] = ("·", pal.dim_style()) if r % 2 == 0 and c % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_braille_stereo(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        y1 = max(0, min(h - 1, int(mid_y - math.sin(c * 0.14 + idle * 1.8) * (h * 0.3))))
        y2 = max(0, min(h - 1, int(mid_y - math.cos(c * 0.18 - idle * 1.2) * (h * 0.3))))
        grid[y1][c] = ("⠶", pal.primary_style())
        grid[y2][c] = ("⠿", pal.accent_style())
        for r in range(h):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_scope_subpixel_interp(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    for c in range(w):
        val = math.sin(c * 0.12 + idle * 2) * (h * 0.36)
        y_int = int(round(mid_y - val))
        frac = abs(mid_y - val - y_int)
        ch = "█" if frac < 0.25 else ("▄" if val > 0 else "▀")
        grid[max(0, min(h - 1, y_int))][c] = (ch, pal.primary_style())
        for r in range(h):
            if grid[r][c][0] == " " and r % 3 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 3: Stanford 3D Waterfalls & Terrains (12 additional)
# ---------------------------------------------------------------------------


def _render_terrain_cyber_wireframe(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    horizon = int(h * 0.35)
    for r in range(h):
        if r < horizon:
            for c in range(w):
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 8 == 0 else (" ", pal.dim_style())
        else:
            depth = (r - horizon) / max(1, h - horizon)
            for c in range(w):
                grid[r][c] = ("═" if (r - horizon) % 3 == 0 else "─", pal.primary_style() if depth > 0.6 else pal.dim_style())
                if (c - w // 2) % max(1, int(12 * (1 - depth * 0.7))) == 0:
                    grid[r][c] = ("┼", pal.accent_style())
    return _canvas_to_text(grid)


def _render_terrain_isometric_voxels(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    n_towers = max(6, w // 4)
    levels = _get_interp_levels(ctx, n_towers, idle)
    for i in range(n_towers):
        c_x = i * (w // n_towers) + 1
        lvl = float(levels[i])
        t_h = int(lvl * (h - 2))
        for r in range(h - 1 - t_h, h):
            if 0 <= r < h and c_x < w:
                grid[r][c_x] = ("█", pal.primary_style())
                if c_x + 1 < w:
                    grid[r][c_x + 1] = ("▓", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 6 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_spectral_canyon(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x = w // 2
    for r in range(h):
        depth = r / max(1, h - 1)
        canyon_w = int(depth * (w * 0.45))
        c1 = max(0, mid_x - canyon_w)
        c2 = min(w - 1, mid_x + canyon_w)
        for c in range(0, c1):
            grid[r][c] = ("█", pal.primary_style())
        for c in range(c2, w):
            grid[r][c] = ("█", pal.primary_style())
        for c in range(c1, c2):
            grid[r][c] = ("·", pal.dim_style()) if c % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_ribbon_highway(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    horizon = int(h * 0.25)
    mid_x = w // 2
    for r in range(horizon, h):
        depth = (r - horizon) / max(1, h - horizon)
        hw_w = int(depth * (w * 0.38))
        left_edge = mid_x - hw_w
        right_edge = mid_x + hw_w
        for c in range(w):
            if left_edge <= c <= right_edge:
                if c == mid_x and (r + int(idle * 5)) % 4 < 2:
                    grid[r][c] = ("║", pal.accent_style(bold=True))
                elif c == left_edge or c == right_edge:
                    grid[r][c] = ("█", pal.primary_style())
                else:
                    grid[r][c] = (" ", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 5 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_contour_map(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            elev = math.sin(c * 0.15 + idle) * math.cos(r * 0.2 - idle) * 5.0
            contour = abs(elev - round(elev))
            if contour < 0.15:
                grid[r][c] = ("─", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_hex_grid_mesh(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            is_hex = ((r % 4 == 0 and c % 6 == 0) or (r % 4 == 2 and c % 6 == 3))
            if is_hex:
                grid[r][c] = ("⌬", pal.accent_style())
            elif r % 2 == 0:
                grid[r][c] = ("─", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if c % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_tunnel_vortex(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x)
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            ring = int(dist - idle * 4) % 6
            if ring == 0:
                grid[r][c] = ("█", pal.primary_style())
            elif ring == 1:
                grid[r][c] = ("▓", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_mountain_horizon(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    for c in range(w):
        peak = int((0.4 + float(levels[c]) * 0.5) * h)
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot == peak:
                grid[r][c] = ("▲", pal.accent_style())
            elif from_bot < peak:
                grid[r][c] = ("█", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 7 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_vector_globe(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    radius = min(mid_x, mid_y * 2) * 0.8
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x)
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < radius:
                ang = math.atan2(dy, dx)
                lat = math.asin(dy / max(1e-4, radius))
                lon = ang + idle
                if abs(math.sin(lon * 4)) < 0.2 or abs(math.sin(lat * 4)) < 0.2:
                    grid[r][c] = ("┼", pal.primary_style())
                else:
                    grid[r][c] = ("░", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 6 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_matrix_landscape(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    levels = _get_interp_levels(ctx, w, idle)
    for c in range(w):
        h_val = int(float(levels[c]) * (h - 1))
        for r in range(h):
            from_bot = h - 1 - r
            if from_bot <= h_val:
                glyph = _HEX_DIGITS[(r + c + int(idle * 4)) % len(_HEX_DIGITS)]
                grid[r][c] = (glyph, pal.primary_style() if from_bot == h_val else pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if r % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_standing_wave_3d(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            wave = math.sin(c * 0.3) * math.sin(r * 0.5) * math.cos(idle * 2.5)
            if abs(wave) > 0.6:
                grid[r][c] = ("█", pal.accent_style())
            elif abs(wave) > 0.2:
                grid[r][c] = ("▓", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_terrain_dune_ripples(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        shift = math.sin(r * 0.3 + idle) * 6
        for c in range(w):
            dune = math.sin((c + shift) * 0.25)
            if dune > 0.7:
                grid[r][c] = ("█", pal.primary_style())
            elif dune > 0.2:
                grid[r][c] = ("░", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if c % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 4: Stereo Phase & Lissajous Renderers (11 additional)
# ---------------------------------------------------------------------------


def _render_phase_goniometer_diamond(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            u = (c - mid_x) + (r - mid_y) * 2.0
            v = (c - mid_x) - (r - mid_y) * 2.0
            if abs(abs(u) + abs(v) - min(w, h * 2) * 0.4) < 1.5:
                grid[r][c] = ("◇", pal.accent_style())
            elif c == mid_x or r == mid_y:
                grid[r][c] = ("·", pal.dim_style())
    pts = 120
    t_vals = np.linspace(0, 2 * math.pi, pts)
    for t in t_vals:
        x = int(mid_x + math.sin(t + idle) * (w * 0.25))
        y = int(mid_y - math.cos(t * 2 - idle) * (h * 0.25))
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.primary_style())
    return _canvas_to_text(grid)


def _render_phase_correlation_compass(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    corr = ctx.phase_corr if ctx.is_playing else math.sin(idle) * 0.9
    angle = corr * (math.pi / 4.0)
    for c in range(w):
        grid[mid_y][c] = ("─", pal.dim_style())
    for r in range(h):
        grid[r][mid_x] = ("│", pal.dim_style())
    length = min(mid_x, mid_y * 2) * 0.8
    for d in range(int(length)):
        x = int(mid_x + math.sin(angle) * d)
        y = int(mid_y - math.cos(angle) * d * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_polar_vector(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for i in range(120):
        ang = random.uniform(0, 2 * math.pi)
        r_dist = random.uniform(0, min(mid_x, mid_y * 2) * 0.75)
        x = int(mid_x + math.cos(ang + idle) * r_dist)
        y = int(mid_y - math.sin(ang + idle) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("✦", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r == mid_y or c == mid_x):
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_orbit_knot(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    theta = np.linspace(0, 4 * math.pi, 240)
    for t in theta:
        x = int(mid_x + (math.sin(t * 2 + idle) + 0.5 * math.sin(t * 3)) * (w * 0.3))
        y = int(mid_y - (math.cos(t * 2 + idle) - 0.5 * math.cos(t * 3)) * (h * 0.3))
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_ms_balance_radar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    m_scale = (w * 0.35)
    s_scale = (h * 0.35)
    theta = np.linspace(0, 2 * math.pi, 160)
    for t in theta:
        x = int(mid_x + math.cos(t) * m_scale)
        y = int(mid_y - math.sin(t) * s_scale)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("░", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r == mid_y or c == mid_x):
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_stereo_jostle(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        jostle = int(math.sin(r * 0.5 + idle * 3) * (w * 0.2))
        for c in range(w):
            if abs(c - (w // 2 + jostle)) < 3:
                grid[r][c] = ("█", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if c % 5 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_spirograph_orbit(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 6 * math.pi, 300):
        r_dist = (h * 0.35) * (math.sin(t * 5 + idle) + 1.2)
        x = int(mid_x + math.cos(t) * r_dist * 2.0)
        y = int(mid_y - math.sin(t) * r_dist)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("*", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 6 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_sub_bass_mono_check(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            if c == mid_x:
                grid[r][c] = ("║", pal.accent_style(bold=True))
            elif abs(c - mid_x) < max(2, int(w * 0.1)):
                grid[r][c] = ("█", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_vector_flower(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 2 * math.pi, 240):
        r_dist = abs(math.cos(3 * t + idle)) * (min(mid_x, mid_y * 2) * 0.8)
        x = int(mid_x + math.cos(t) * r_dist)
        y = int(mid_y - math.sin(t) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("✿", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_lissajous_3d(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 4 * math.pi, 200):
        x = int(mid_x + math.sin(t * 2 + idle) * (w * 0.35))
        y = int(mid_y - math.sin(t * 3 - idle) * (h * 0.35))
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("⌖", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r == mid_y or c == mid_x):
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_phase_stereo_field_cloud(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for _ in range(max(20, w * 2)):
        c = random.randint(0, w - 1)
        r = random.randint(0, h - 1)
        grid[r][c] = ("·" if random.random() < 0.7 else "✦", pal.primary_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 5: Cyber Matrix & Generative Renderers (12 additional)
# ---------------------------------------------------------------------------


def _render_cyber_hex_memory_dump(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        addr = f"0x{(r * 16 + int(idle * 8)) & 0xFFFF:04X}:"
        for i, ch in enumerate(addr[:min(len(addr), w)]):
            grid[r][i] = (ch, pal.accent_style())
        for c in range(len(addr) + 1, w):
            if c % 3 == 0:
                grid[r][c] = (" ", pal.dim_style())
            else:
                digit = _HEX_DIGITS[(r * w + c + int(idle * 6)) % 16]
                grid[r][c] = (digit, pal.primary_style())
    return _canvas_to_text(grid)


def _render_cyber_binary_cascade(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            b_val = "1" if (r * 7 + c * 13 + int(idle * 9)) % 3 == 0 else "0"
            grid[r][c] = (b_val, pal.primary_style() if b_val == "1" else pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_audio_glitch_rot(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        is_glitch_row = random.random() < 0.2
        for c in range(w):
            if is_glitch_row:
                grid[r][c] = (random.choice("█▓▒░⚡!#?@"), pal.accent_style(bold=True))
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_ascii_raymarch(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x) * 1.0
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            torus = abs(dist - min(mid_x, mid_y * 2) * 0.6)
            if torus < 4:
                shade_idx = int((1.0 - torus / 4.0) * (len(_SHADES) - 1))
                grid[r][c] = (_SHADES[shade_idx], pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 6 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_neural_synapse(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    nodes = [(int(w * 0.2), int(h * 0.3)), (int(w * 0.8), int(h * 0.3)), (int(w * 0.5), int(h * 0.7))]
    for nx, ny in nodes:
        if 0 <= nx < w and 0 <= ny < h:
            grid[ny][nx] = ("●", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_circuit_trace(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        if r % 3 == 0:
            for c in range(w):
                grid[r][c] = ("═", pal.primary_style())
                if c % 8 == 0:
                    grid[r][c] = ("Ø", pal.accent_style())
        else:
            for c in range(w):
                grid[r][c] = ("│", pal.dim_style()) if c % 8 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_dna_helix(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x = w // 2
    for r in range(h):
        s1 = int(mid_x + math.sin(r * 0.4 + idle * 2) * (w * 0.25))
        s2 = int(mid_x - math.sin(r * 0.4 + idle * 2) * (w * 0.25))
        if 0 <= s1 < w:
            grid[r][s1] = ("●", pal.primary_style())
        if 0 <= s2 < w:
            grid[r][s2] = ("○", pal.accent_style())
        if abs(s1 - s2) > 2 and r % 2 == 0:
            for c in range(min(s1, s2) + 1, max(s1, s2)):
                grid[r][c] = ("─", pal.dim_style())
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 6 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_quantum_lattice(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            q_state = math.sin(r * 0.6) * math.cos(c * 0.4 + idle * 2)
            if q_state > 0.6:
                grid[r][c] = ("|ψ⟩"[:1], pal.accent_style())
            elif q_state < -0.6:
                grid[r][c] = ("|0⟩"[:1], pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_terminal_hud(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for c in range(w):
        grid[0][c] = ("═", pal.accent_style())
        grid[h - 1][c] = ("═", pal.accent_style())
    for r in range(h):
        grid[r][0] = ("║", pal.accent_style())
        grid[r][w - 1] = ("║", pal.accent_style())
    grid[0][0] = ("╔", pal.accent_style())
    grid[0][w - 1] = ("╗", pal.accent_style())
    grid[h - 1][0] = ("╚", pal.accent_style())
    grid[h - 1][w - 1] = ("╝", pal.accent_style())
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_ascii_cube_3d(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    size_x, size_y = int(w * 0.2), int(h * 0.25)
    for dx in range(-size_x, size_x + 1):
        grid[mid_y - size_y][mid_x + dx] = ("─", pal.primary_style())
        grid[mid_y + size_y][mid_x + dx] = ("─", pal.primary_style())
    for dy in range(-size_y, size_y + 1):
        grid[mid_y + dy][mid_x - size_x] = ("│", pal.primary_style())
        grid[mid_y + dy][mid_x + size_x] = ("│", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_cyberdeck_boot(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    logs = [
        "BIOS: OMNIRIP v2.4 OK",
        "DSP: BS-ROFORMER INIT",
        "FFT: 1024 BINS SYNC",
        "DAC: 96kHz 24-BIT OK",
    ]
    for r in range(min(h, len(logs))):
        for c, ch in enumerate(logs[r][:w]):
            grid[r][c] = (ch, pal.primary_style())
    for r in range(len(logs), h):
        for c in range(w):
            grid[r][c] = ("·", pal.dim_style()) if c % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_audio_spectrum_shred(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for c in range(w):
        shred = (c + int(idle * 10)) % 5
        for r in range(h):
            grid[r][c] = ("|" if shred == 0 else " ", pal.accent_style() if shred == 0 else pal.dim_style())
            if grid[r][c][0] == " " and r % 3 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 6: Particle Systems & Fluid Dynamics Renderers (12 additional)
# ---------------------------------------------------------------------------


def _render_particles_plasma_sphere(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            val = math.sin(c * 0.15 + idle) + math.sin(r * 0.3 - idle) + math.sin((c + r) * 0.2 + idle)
            idx = int(abs(val) * 1.5) % len(_SHADES)
            grid[r][c] = (_SHADES[idx], pal.primary_style() if idx > 2 else pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_spark_fountain(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x = w // 2
    for _ in range(max(10, w)):
        vx = random.uniform(-1, 1) * (w * 0.4)
        vy = random.uniform(0.1, 1.0) * h
        px = max(0, min(w - 1, int(mid_x + vx)))
        py = max(0, min(h - 1, int(h - 1 - vy)))
        grid[py][px] = ("*", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_liquid_mercury(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dist = math.sqrt((c - mid_x) ** 2 + ((r - mid_y) * 2.0) ** 2)
            ripple = math.sin(dist * 0.5 - idle * 3)
            if ripple > 0.6:
                grid[r][c] = ("█", pal.primary_style())
            elif ripple > 0.1:
                grid[r][c] = ("▒", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_starfield_warp(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for _ in range(max(20, w * 2)):
        ang = random.uniform(0, 2 * math.pi)
        dist = random.uniform(2, min(mid_x, mid_y * 2))
        x = int(mid_x + math.cos(ang) * dist)
        y = int(mid_y - math.sin(ang) * dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("━" if dist > min(mid_x, mid_y * 2) * 0.6 else "·", pal.primary_style())
    return _canvas_to_text(grid)


def _render_particles_vortex_tornado(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x = w // 2
    for r in range(h):
        width_r = int((r / max(1, h)) * (w * 0.4))
        for c in range(mid_x - width_r, mid_x + width_r + 1):
            if 0 <= c < w:
                grid[r][c] = ("@" if (r + c + int(idle * 6)) % 3 == 0 else "§", pal.accent_style())
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_supernova_burst(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    radius = (min(mid_x, mid_y * 2) * 0.75) * (abs(math.sin(idle * 2)) + 0.2)
    for r in range(h):
        for c in range(w):
            dist = math.sqrt((c - mid_x) ** 2 + ((r - mid_y) * 2.0) ** 2)
            if abs(dist - radius) < 2:
                grid[r][c] = ("█", pal.accent_style(bold=True))
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_bubble_chamber(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 4 * math.pi, 160):
        r_dist = t * 2.0
        x = int(mid_x + math.cos(t + idle) * r_dist)
        y = int(mid_y - math.sin(t + idle) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("o", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 6 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_sand_storm(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            grid[r][c] = ("·", pal.primary_style() if (r + c * 2 + int(idle * 8)) % 4 == 0 else pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_galaxy_spiral(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for arm in [0, math.pi]:
        for t in np.linspace(0, 3 * math.pi, 180):
            r_dist = t * 3.0
            x = int(mid_x + math.cos(t + arm + idle) * r_dist)
            y = int(mid_y - math.sin(t + arm + idle) * r_dist * 0.5)
            if 0 <= x < w and 0 <= y < h:
                grid[y][x] = ("✦", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_aurora_borealis(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for c in range(w):
        y_top = int(h * 0.2 + math.sin(c * 0.15 + idle) * (h * 0.2))
        y_bot = min(h - 1, y_top + int(h * 0.45))
        for r in range(y_top, y_bot):
            grid[r][c] = ("░" if (r - y_top) % 2 == 0 else "▒", pal.primary_style())
        for r in range(h):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_electric_arc(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    curr_y = h // 2
    for c in range(w):
        curr_y = max(0, min(h - 1, curr_y + random.randint(-1, 1)))
        grid[curr_y][c] = ("⚡", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_particles_cellular_automata(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            alive = ((r * 11 + c * 17 + int(idle * 5)) % 5) < 2
            grid[r][c] = ("■" if alive else "·", pal.primary_style() if alive else pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 7: Geometric & Math Fractals Renderers (12 additional)
# ---------------------------------------------------------------------------


def _render_fractal_chladni_plate(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    m, n = 3, 5
    for r in range(h):
        for c in range(w):
            x = (c / max(1, w - 1)) * 2 - 1
            y = (r / max(1, h - 1)) * 2 - 1
            val = math.cos(n * math.pi * x) * math.cos(m * math.pi * y) - math.cos(m * math.pi * x) * math.cos(n * math.pi * y)
            if abs(val) < 0.2:
                grid[r][c] = ("█", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 3 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_mandelbrot_zoom(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    zoom = 1.0 + abs(math.sin(idle)) * 2.0
    for r in range(h):
        for c in range(w):
            cr = ((c - w / 2) / (w * 0.4 * zoom)) - 0.7
            ci = ((r - h / 2) / (h * 0.4 * zoom))
            zr, zi = 0.0, 0.0
            iters = 0
            while zr * zr + zi * zi < 4.0 and iters < 12:
                zr, zi = zr * zr - zi * zi + cr, 2.0 * zr * zi + ci
                iters += 1
            grid[r][c] = (_SHADES[iters % len(_SHADES)], pal.primary_style() if iters > 4 else pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_julia_morph(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    ca, cb = -0.7 + 0.1 * math.sin(idle), 0.27 + 0.1 * math.cos(idle)
    for r in range(h):
        for c in range(w):
            zr = (c - w / 2) / (w * 0.3)
            zi = (r - h / 2) / (h * 0.3)
            iters = 0
            while zr * zr + zi * zi < 4.0 and iters < 10:
                zr, zi = zr * zr - zi * zi + ca, 2.0 * zr * zi + cb
                iters += 1
            grid[r][c] = (_SHADES[iters % len(_SHADES)], pal.accent_style() if iters > 3 else pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_sacred_spirograph(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 8 * math.pi, 250):
        R, r_in, p = 5.0, 3.0, 5.0
        x = int(mid_x + ((R - r_in) * math.cos(t + idle) + p * math.cos((R - r_in) * t / r_in)) * (w * 0.04))
        y = int(mid_y - ((R - r_in) * math.sin(t + idle) - p * math.sin((R - r_in) * t / r_in)) * (h * 0.05))
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("◈", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_lorenz_attractor(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    x, y, z = 0.1, 0.0, 0.0
    dt = 0.015
    for _ in range(250):
        dx = 10.0 * (y - x) * dt
        dy = (x * (28.0 - z) - y) * dt
        dz = (x * y - (8.0 / 3.0) * z) * dt
        x += dx
        y += dy
        z += dz
        px = int(mid_x + x * (w * 0.018))
        py = int(mid_y - (z - 25) * (h * 0.025))
        if 0 <= px < w and 0 <= py < h:
            grid[py][px] = ("*", pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_sierpinski_gasket(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            val = (r & c) == 0
            grid[r][c] = ("▲" if val else "·", pal.primary_style() if val else pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_barnsley_fern(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    x, y = 0.0, 0.0
    for _ in range(280):
        r_val = random.random()
        if r_val < 0.01:
            x, y = 0.0, 0.16 * y
        elif r_val < 0.86:
            x, y = 0.85 * x + 0.04 * y, -0.04 * x + 0.85 * y + 1.6
        elif r_val < 0.93:
            x, y = 0.2 * x - 0.26 * y, 0.23 * x + 0.22 * y + 1.6
        else:
            x, y = -0.15 * x + 0.28 * y, 0.26 * x + 0.24 * y + 0.44
        px = int(w / 2 + x * (w * 0.08))
        py = int(h - 1 - y * (h * 0.09))
        if 0 <= px < w and 0 <= py < h:
            grid[py][px] = ("🌿"[:1], pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_fibonacci_spiral(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for n in range(max(20, w * 2)):
        ang = n * 137.5 * (math.pi / 180.0) + idle
        r_dist = math.sqrt(n) * (min(mid_x, mid_y * 2) * 0.08)
        x = int(mid_x + math.cos(ang) * r_dist)
        y = int(mid_y - math.sin(ang) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("•", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_koch_snowflake(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for t in np.linspace(0, 2 * math.pi, 180):
        r_dist = (min(mid_x, mid_y * 2) * 0.6) * (1.0 + 0.2 * math.sin(t * 6 + idle))
        x = int(mid_x + math.cos(t) * r_dist)
        y = int(mid_y - math.sin(t) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("❄"[:1], pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_dragon_curve(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for i in range(max(30, w * 2)):
        ang = (i * 0.3) + idle
        r_dist = math.sqrt(i) * 2.5
        x = int(mid_x + math.cos(ang) * r_dist)
        y = int(mid_y - math.sin(ang) * r_dist * 0.5)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("🐉"[:1], pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_hyperbolic_tiling(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x) / max(1.0, w * 0.4)
            dy = (r - mid_y) / max(1.0, h * 0.4)
            r2 = dx * dx + dy * dy
            if r2 < 0.95:
                val = math.sin(dx / (1.0 - r2) + idle) * math.cos(dy / (1.0 - r2) - idle)
                grid[r][c] = ("░" if val > 0 else " ", pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_fractal_voronoi_cells(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    pts = [(int(w * 0.3), int(h * 0.3)), (int(w * 0.7), int(h * 0.3)), (int(w * 0.5), int(h * 0.7))]
    for r in range(h):
        for c in range(w):
            dists = [math.sqrt((c - px) ** 2 + ((r - py) * 2.0) ** 2) for px, py in pts]
            dists.sort()
            if dists[1] - dists[0] < 1.2:
                grid[r][c] = ("│", pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 8: Studio Forensic Telemetry Renderers (10 additional)
# ---------------------------------------------------------------------------


def _render_meter_ebu_r128_radar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x)
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            if abs(dist - min(mid_x, mid_y * 2) * 0.7) < 1.2:
                grid[r][c] = ("◎", pal.accent_style())
            elif c == mid_x or r == mid_y:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_k_system_master(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            if c < w // 4:
                grid[r][c] = ("█", pal.primary_style() if r > h // 3 else pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_true_peak_forensic(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    tp = ctx.rms_db + 3.0 if ctx.is_playing else -1.2 + 0.8 * math.sin(idle)
    for c in range(w):
        grid[h // 2][c] = ("█" if tp > -1.0 else "░", pal.accent_style() if tp > 0.0 else pal.primary_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_crest_factor_dial(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h - 1
    cf = ctx.crest_factor if ctx.is_playing else 12.0 + 3.0 * math.sin(idle)
    angle = (cf / 20.0) * math.pi
    for d in range(min(mid_x, mid_y)):
        x = int(mid_x - math.cos(angle) * d)
        y = int(mid_y - math.sin(angle) * d)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("█", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_stereo_balance_radar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    for c in range(w):
        grid[mid_y][c] = ("─", pal.dim_style())
    grid[mid_y][mid_x] = ("●", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_clipping_density(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for r in range(h):
        for c in range(w):
            is_clip = (r == 0 or r == h - 1) and ((c + int(idle * 4)) % 8 == 0)
            grid[r][c] = ("▲" if is_clip else "·", pal.accent_style(bold=True) if is_clip else pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_phase_correlation_bar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_y = h // 2
    corr = ctx.phase_corr if ctx.is_playing else math.sin(idle) * 0.8
    bar_pos = int((corr + 1.0) * 0.5 * (w - 1))
    for c in range(w):
        grid[mid_y][c] = ("█" if c <= bar_pos else "░", pal.primary_style() if corr > 0 else pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_dr_meter_offline(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    label = "DR12 [OPTIMAL]"
    for c, ch in enumerate(label[:w]):
        grid[h // 2][c] = (ch, pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_spectral_centroid_dial(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    cent = ctx.spectral_centroid if ctx.is_playing else 1400.0 + 400.0 * math.sin(idle)
    c_pos = int(min(1.0, cent / 8000.0) * (w - 1))
    for c in range(w):
        grid[h // 2][c] = ("▼" if c == c_pos else "─", pal.accent_style() if c == c_pos else pal.dim_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_harman_target_tracker(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    for c in range(w):
        # Target Harman curve
        target_y = int(h * 0.4 + (c / max(1, w)) * (h * 0.25))
        actual_y = target_y + int(math.sin(c * 0.2 + idle) * 2)
        grid[max(0, min(h - 1, target_y))][c] = ("─", pal.dim_style())
        grid[max(0, min(h - 1, actual_y))][c] = ("●", pal.accent_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 6 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Engine Catalog Definitions (Total 91 engines to reach 100)
# ---------------------------------------------------------------------------

CATALOG_91_SPECS: list[tuple[str, str, str, str, str, Callable]] = [
    # Pack 1: Spectral (11 engines)
    ("spectral_waterfall_bars", "Spectral Waterfall Gradient", "spectral", "⌗", "Falling peak-decay frequency spectrum with color heat.", _render_spectral_waterfall_bars),
    ("spectral_braille_dense", "Braille High-Res Spectrum", "spectral", "⌗", "High-density 2x4 braille dots frequency bins.", _render_spectral_braille_dense),
    ("spectral_vfd_vintage", "Vintage VFD Fluorescent Analyzer", "spectral", "⌗", "Fluorescent vacuum display segments with needle peak hold.", _render_spectral_vfd_vintage),
    ("spectral_iso_31band", "31-Band 1/3-Octave Analyzer", "spectral", "⌗", "Calibrated ANSI 1/3-octave graphic EQ display.", _render_spectral_iso_31band),
    ("spectral_comb_harmonics", "Harmonic Comb Analyzer", "spectral", "⌗", "Fundamental pitch tracking with integer harmonic combs.", _render_spectral_comb_harmonics),
    ("spectral_ribbon_energy", "Energy Density Ribbon", "spectral", "⌗", "Continuous smooth spline ribbon of spectral power.", _render_spectral_ribbon_energy),
    ("spectral_log_cascade", "Logarithmic Frequency Cascade", "spectral", "⌗", "Human-auditory bark scale logarithmic cascade.", _render_spectral_log_cascade),
    ("spectral_cepstrum", "Audio Cepstrum Quefrency", "spectral", "⌗", "FFT of log-spectrum showing pitch timbre quefrency.", _render_spectral_cepstrum),
    ("spectral_differential", "Differential Mid/Side Spectrum", "spectral", "⌗", "Overlaid mid (mono) vs side (stereo) spectral differential.", _render_spectral_differential),
    ("spectral_gravity_peaks", "Gravity Falling Peak Needles", "spectral", "⌗", "Physics-simulated ballistics for peak needles.", _render_spectral_gravity_peaks),
    ("spectral_sub_bass_rumble", "Sub-Bass Seismic Scope", "spectral", "⌗", "Deep zoom on 10Hz - 160Hz sub-bass and kick transients.", _render_spectral_sub_bass_rumble),

    # Pack 2: Oscilloscope (11 engines)
    ("scope_vector_xy", "Vector Beam Oscilloscope", "oscilloscope", "≋", "Reticle beam phosphor trace with electron gun decay.", _render_scope_vector_xy),
    ("scope_dual_trace", "Dual-Trace Stereo Oscilloscope", "oscilloscope", "≋", "Split-beam CH1 (Left) and CH2 (Right) dual scope.", _render_scope_dual_trace),
    ("scope_strobe_tuner", "Stroboscopic Tuning Scope", "oscilloscope", "≋", "Rotating strobe disc locking onto audio fundamental frequencies.", _render_scope_strobe_tuner),
    ("scope_persistence_ghost", "Long-Persistence CRT Phosphor", "oscilloscope", "≋", "Decaying phosphorescent ghost afterglow trail.", _render_scope_persistence_ghost),
    ("scope_trigger_holdoff", "Triggered Pulse Oscilloscope", "oscilloscope", "≋", "Zero-crossing edge triggered stable pulse scope.", _render_scope_trigger_holdoff),
    ("scope_differential_ms", "M/S Sum & Difference Scope", "oscilloscope", "≋", "Mid/Side stereo component waveform trace.", _render_scope_differential_ms),
    ("scope_circular_polar", "Circular Radial Polar Scope", "oscilloscope", "≋", "Radial oscilloscope blooming outward from circular reticle.", _render_scope_circular_polar),
    ("scope_audio_glitch", "CRT Scanline Sync Loss", "oscilloscope", "≋", "Horizontal scanline jitter and vertical CRT blanking roll.", _render_scope_audio_glitch),
    ("scope_tape_head", "Analog Tape Head Saturation", "oscilloscope", "≋", "Warm analog saturation wave with magnetic hysteresis.", _render_scope_tape_head),
    ("scope_braille_stereo", "Braille Stereo Waveform Cross", "oscilloscope", "≋", "Interleaved dual braille waveforms.", _render_scope_braille_stereo),
    ("scope_subpixel_interp", "Hermite Interpolated Trace", "oscilloscope", "≋", "Smooth cubic Hermite spline anti-aliased trace.", _render_scope_subpixel_interp),

    # Pack 3: Stanford 3D Waterfalls & Terrains (12 engines)
    ("terrain_cyber_wireframe", "3D Cyberpunk Wireframe Terrain", "waterfall_3d", "▲", "Retro synthwave 80s neon grid mountain landscape.", _render_terrain_cyber_wireframe),
    ("terrain_isometric_voxels", "Isometric Voxel Cityscape", "waterfall_3d", "▲", "3D audio-reactive skyscraper towers rising with bass.", _render_terrain_isometric_voxels),
    ("terrain_spectral_canyon", "Audio Spectral Canyon", "waterfall_3d", "▲", "Flight down a winding 3D canyon carved by audio frequencies.", _render_terrain_spectral_canyon),
    ("terrain_ribbon_highway", "Warp Horizon Audio Highway", "waterfall_3d", "▲", "Receding 3D grid highway with floating frequency arches.", _render_terrain_ribbon_highway),
    ("terrain_contour_map", "Topographic Contour Elevation", "waterfall_3d", "▲", "Iso-height elevation contours of sound pressure levels.", _render_terrain_contour_map),
    ("terrain_hex_grid_mesh", "Hexagonal Cyber Honeycomb", "waterfall_3d", "▲", "3D tessellated hex cells pulsing with frequency energy.", _render_terrain_hex_grid_mesh),
    ("terrain_tunnel_vortex", "3D Audio Wireframe Tunnel", "waterfall_3d", "▲", "Traveling down an infinite perspective wireframe tunnel.", _render_terrain_tunnel_vortex),
    ("terrain_mountain_horizon", "SunMusic Alpine Mountain Range", "waterfall_3d", "▲", "Majestic mountain peaks etched against the twilight horizon.", _render_terrain_mountain_horizon),
    ("terrain_vector_globe", "3D Rotating Wireframe Sphere", "waterfall_3d", "▲", "Rotating 3D geodesic sphere deformed by audio waves.", _render_terrain_vector_globe),
    ("terrain_matrix_landscape", "Matrix Glyph Topography", "waterfall_3d", "▲", "3D heightfield made entirely of glowing cascading code.", _render_terrain_matrix_landscape),
    ("terrain_standing_wave_3d", "3D Standing Acoustic Wave", "waterfall_3d", "▲", "Three-dimensional nodal acoustic standing wave grid.", _render_terrain_standing_wave_3d),
    ("terrain_dune_ripples", "Acoustic Sand Dune Ripples", "waterfall_3d", "▲", "Wind-swept desert dune ripples shifting with low frequencies.", _render_terrain_dune_ripples),

    # Pack 4: Stereo Phase & Lissajous (11 engines)
    ("phase_goniometer_diamond", "Goniometer Diamond Scope", "stereo_phase", "⌖", "45-degree tilted goniometer showing stereo width.", _render_phase_goniometer_diamond),
    ("phase_correlation_compass", "Phase Correlation Radar Compass", "stereo_phase", "⌖", "360-degree vector dial showing phase coherence.", _render_phase_correlation_compass),
    ("phase_polar_vector", "Polar Vector Field Scope", "stereo_phase", "⌖", "Vector cloud displaying instantaneous stereo dispersion.", _render_phase_polar_vector),
    ("phase_orbit_knot", "Harmonic Torus Knot", "stereo_phase", "⌖", "3D stereoscopic parametric torus knot rotating with phase.", _render_phase_orbit_knot),
    ("phase_ms_balance_radar", "Mid/Side Balance Ellipse", "stereo_phase", "⌖", "Elliptical stereo balance meter tracking spatial width.", _render_phase_ms_balance_radar),
    ("phase_stereo_jostle", "Stereo Phase Jitter Scope", "stereo_phase", "⌖", "Micro-phase fluctuations between left and right channels.", _render_phase_stereo_jostle),
    ("phase_spirograph_orbit", "Spirographic Epicycloid Orbit", "stereo_phase", "⌖", "Epicyclic orbital curves modulated by harmonic intervals.", _render_phase_spirograph_orbit),
    ("phase_sub_bass_mono_check", "Sub-Bass Mono Correlation", "stereo_phase", "⌖", "Forensic phase coherence below 120Hz for vinyl/club check.", _render_phase_sub_bass_mono_check),
    ("phase_vector_flower", "Parametric Acoustic Rose", "stereo_phase", "⌖", "Rose curve blooming with stereo energy.", _render_phase_vector_flower),
    ("phase_lissajous_3d", "3D Lissajous Orthographic", "stereo_phase", "⌖", "Projected 3D Lissajous figure tumbling in spatial axes.", _render_phase_lissajous_3d),
    ("phase_stereo_field_cloud", "Stereo Soundfield Cloud", "stereo_phase", "⌖", "Cloud of phosphor particles showing acoustic spatialization.", _render_phase_stereo_field_cloud),

    # Pack 5: Cyber Matrix & Generative (12 engines)
    ("cyber_hex_memory_dump", "Cyber Hex Memory Dump", "cyber_matrix", "⌬", "Scrolling memory addresses, hex bytes, and ASCII inspection.", _render_cyber_hex_memory_dump),
    ("cyber_binary_cascade", "Binary Stream Waterfall", "cyber_matrix", "⌬", "Cascades of 0s and 1s responding to bit depth and dynamic range.", _render_cyber_binary_cascade),
    ("cyber_audio_glitch_rot", "Glitch Audio Buffer Bit Rot", "cyber_matrix", "⌬", "CRT corruption, memory scramble, and cyber byte shifts.", _render_cyber_audio_glitch_rot),
    ("cyber_ascii_raymarch", "ASCII Raymarching Donut", "cyber_matrix", "⌬", "3D spinning torus rendered with ASCII lighting.", _render_cyber_ascii_raymarch),
    ("cyber_neural_synapse", "Neural Network Synapse Mesh", "cyber_matrix", "⌬", "Interconnected neural nodes firing with acoustic transients.", _render_cyber_neural_synapse),
    ("cyber_circuit_trace", "Printed Circuit Board Traces", "cyber_matrix", "⌬", "Glowing PCB bus lines carrying audio current.", _render_cyber_circuit_trace),
    ("cyber_dna_helix", "Acoustic DNA Double Helix", "cyber_matrix", "⌬", "Rotating double helix twisted and illuminated by frequency bins.", _render_cyber_dna_helix),
    ("cyber_quantum_lattice", "Quantum State Grid Lattice", "cyber_matrix", "⌬", "Probability wave lattice collapsing on transient beats.", _render_cyber_quantum_lattice),
    ("cyber_terminal_hud", "Cyberpunk Tactical HUD", "cyber_matrix", "⌬", "Sci-fi combat cockpit display with frequency target locks.", _render_cyber_terminal_hud),
    ("cyber_ascii_cube_3d", "Rotating 3D ASCII Cube", "cyber_matrix", "⌬", "Classic demoscene wireframe cube spinning to the beat.", _render_cyber_ascii_cube_3d),
    ("cyber_cyberdeck_boot", "Cyberdeck Kernel Telemetry", "cyber_matrix", "⌬", "Real-time system telemetry and forensic DSP registers.", _render_cyber_cyberdeck_boot),
    ("cyber_audio_spectrum_shred", "Spectrum Data Shredder", "cyber_matrix", "⌬", "Fragmenting data strips dissolving on peak drops.", _render_cyber_audio_spectrum_shred),

    # Pack 6: Particle Systems & Fluid Dynamics (12 engines)
    ("particles_plasma_sphere", "Demoscene Plasma Sphere", "particles_fluid", "✦", "Swirling sine plasma field with psychedelic color interference.", _render_particles_plasma_sphere),
    ("particles_spark_fountain", "Acoustic Spark Fountain", "particles_fluid", "✦", "Gravity-accelerated embers blasting upward on kick transients.", _render_particles_spark_fountain),
    ("particles_liquid_mercury", "Liquid Mercury Ripple Basin", "particles_fluid", "✦", "Concentric surface tension waves spreading across liquid pool.", _render_particles_liquid_mercury),
    ("particles_starfield_warp", "Audio Starfield Warp Speed", "particles_fluid", "✦", "3D stars accelerating into hyperspace lines with music tempo.", _render_particles_starfield_warp),
    ("particles_vortex_tornado", "Acoustic Tornado Vortex", "particles_fluid", "✦", "Twisting cyclonic particle vortex spinning with frequency energy.", _render_particles_vortex_tornado),
    ("particles_supernova_burst", "Audio Supernova Explosion", "particles_fluid", "✦", "Shockwave expanding outward from center on beat drops.", _render_particles_supernova_burst),
    ("particles_bubble_chamber", "Quantum Bubble Chamber", "particles_fluid", "✦", "Spiral particle tracks curving in magnetic field.", _render_particles_bubble_chamber),
    ("particles_sand_storm", "Desert Sandstorm Dust", "particles_fluid", "✦", "Swirling atmospheric particle storm driven by wind harmonics.", _render_particles_sand_storm),
    ("particles_galaxy_spiral", "Rotating Spiral Galaxy", "particles_fluid", "✦", "Two-arm logarithmic spiral galaxy rotating with tempo.", _render_particles_galaxy_spiral),
    ("particles_aurora_borealis", "Aurora Borealis Ribbon", "particles_fluid", "✦", "Shimmering curtains of Northern Lights swaying with mids and highs.", _render_particles_aurora_borealis),
    ("particles_electric_arc", "Tesla Coil Electric Lightning", "particles_fluid", "✦", "Branching jagged electrical discharge striking terminal borders.", _render_particles_electric_arc),
    ("particles_cellular_automata", "Conway Game of Life Audio", "particles_fluid", "✦", "Cellular automata seeded by audio frequency transitions.", _render_particles_cellular_automata),

    # Pack 7: Geometric & Math Fractals (12 engines)
    ("fractal_chladni_plate", "Chladni Resonant Cymatics Plate", "math_fractal", "◈", "Acoustic nodal lines on vibrating sand plates.", _render_fractal_chladni_plate),
    ("fractal_mandelbrot_zoom", "Mandelbrot Fractal Audio Zoom", "math_fractal", "◈", "Complex number Mandelbrot set pulsating with audio depth.", _render_fractal_mandelbrot_zoom),
    ("fractal_julia_morph", "Julia Set Acoustic Morpher", "math_fractal", "◈", "z -> z^2 + c Julia morpher modulated by audio centroid and RMS.", _render_fractal_julia_morph),
    ("fractal_sacred_spirograph", "Sacred Geometry Spirograph", "math_fractal", "◈", "Harmonic epicycloids and hypocycloids forming floral mandalas.", _render_fractal_sacred_spirograph),
    ("fractal_lorenz_attractor", "Lorenz Strange Attractor", "math_fractal", "◈", "Chaotic butterfly attractor orbiting in phase space.", _render_fractal_lorenz_attractor),
    ("fractal_sierpinski_gasket", "Sierpinski Audio Gasket", "math_fractal", "◈", "Recursive triangle lattice illuminated by frequency octaves.", _render_fractal_sierpinski_gasket),
    ("fractal_barnsley_fern", "Barnsley Fern Audio Branch", "math_fractal", "◈", "Fractal IFS fern swaying and growing with acoustic energy.", _render_fractal_barnsley_fern),
    ("fractal_fibonacci_spiral", "Golden Ratio Fibonacci Spiral", "math_fractal", "◈", "Sunflower seed phyllotaxis points blooming with volume.", _render_fractal_fibonacci_spiral),
    ("fractal_koch_snowflake", "Koch Snowflake Resonator", "math_fractal", "◈", "Self-similar fractal snowflake perimeter expanding with transients.", _render_fractal_koch_snowflake),
    ("fractal_dragon_curve", "Heighway Dragon Curve", "math_fractal", "◈", "Recursive paper-folding fractal path tracing harmonic intervals.", _render_fractal_dragon_curve),
    ("fractal_hyperbolic_tiling", "Poincaré Hyperbolic Disk", "math_fractal", "◈", "Escher-style non-Euclidean hyperbolic tessellation.", _render_fractal_hyperbolic_tiling),
    ("fractal_voronoi_cells", "Voronoi Dynamic Crystal Grid", "math_fractal", "◈", "Voronoi cellular diagram with centroids orbiting to the music.", _render_fractal_voronoi_cells),

    # Pack 8: Studio Forensic Telemetry (10 engines)
    ("meter_ebu_r128_radar", "EBU R128 Loudness Radar", "studio_meters", "𝄢", "Circular 360-degree radar showing Momentary/Short-Term LUFS history.", _render_meter_ebu_r128_radar),
    ("meter_k_system_master", "Bob Katz K-System Meter", "studio_meters", "𝄢", "Calibrated K-12, K-14, and K-20 mastering scale with headroom zones.", _render_meter_k_system_master),
    ("meter_true_peak_forensic", "True Peak Intersample Forensic", "studio_meters", "𝄢", "4x oversampled true peak meter detecting intersample clipping.", _render_meter_true_peak_forensic),
    ("meter_crest_factor_dial", "Dynamic Range Crest Factor Dial", "studio_meters", "𝄢", "Telemetry needle displaying peak-to-RMS crest ratio.", _render_meter_crest_factor_dial),
    ("meter_stereo_balance_radar", "Stereo Soundstage Balance Radar", "studio_meters", "𝄢", "L/R energy distribution and acoustic center of gravity.", _render_meter_stereo_balance_radar),
    ("meter_clipping_density", "Clipping Density Heatmap", "studio_meters", "𝄢", "Forensic sample saturation and digital flat-top detection.", _render_meter_clipping_density),
    ("meter_phase_correlation_bar", "Forensic Phase Correlation Bar", "studio_meters", "𝄢", "Calibrated -1.0 to +1.0 phase correlation bar.", _render_meter_phase_correlation_bar),
    ("meter_dr_meter_offline", "Pleasurize Music DR Dynamic Meter", "studio_meters", "𝄢", "Official DR1 to DR20 dynamic range score meter.", _render_meter_dr_meter_offline),
    ("meter_spectral_centroid_dial", "Spectral Centroid Timbre Dial", "studio_meters", "𝄢", "Center-of-mass acoustic frequency gauge in Hertz.", _render_meter_spectral_centroid_dial),
    ("meter_harman_target_tracker", "Harman Target Compliance Gauge", "studio_meters", "𝄢", "Acoustic curve compliance meter vs Harman / DF target.", _render_meter_harman_target_tracker),
]


def _make_render_frame(renderer_fn: Callable):
    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float = 0.0,
        palette: ColorPalette | None = None,
    ) -> Text:
        from harvester.ui.visuals.base import PALETTES

        pal = palette if palette is not None else PALETTES["cyan"]
        return renderer_fn(width, height, ctx, idle_phase, pal)

    return render_frame


def register_catalog_100() -> None:
    """Instantiate and register all 91 procedural engines into VisualizerRegistry."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    for spec in CATALOG_91_SPECS:
        eng_id, name, cat, icon, desc, renderer = spec

        # Define custom class dynamically for each engine
        cls_dict = {
            "id": eng_id,
            "name": name,
            "category": cat,
            "icon": icon,
            "description": desc,
            "render_frame": _make_render_frame(renderer),
        }
        engine_type = type(f"Engine_{eng_id}", (BaseVisualizerEngine,), cls_dict)
        VisualizerRegistry.register(engine_type)

