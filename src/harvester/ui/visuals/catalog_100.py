"""100 Modular Audio Visualizer Engines across 8 Thematic Packs."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from rich.style import Style
from rich.text import Text

from harvester.ui.visuals.base import (
    PALETTES,
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
    clamp_frame_size,
)

# Shared glyph tables
_SHADES = (" ", "·", "░", "▒", "▓", "█")
_HEX_DIGITS = "0123456789ABCDEF"

# Signature every procedural renderer shares.
RendererFn = Callable[[int, int, AudioFeatureContext, float, ColorPalette], Text]

DEFAULT_PALETTE_KEY = "cyan"


# ---------------------------------------------------------------------------
# Audio-reactive modulation helpers
#
# Every renderer in this module is a pure function of (width, height, ctx, idle
# phase, palette). Renderers that ignore `ctx` and drive themselves purely off
# the idle phase look identical whether or not music is playing, so they route
# their animation through these helpers instead. Each returns a value derived
# from real decoded audio whenever audio is present, and degrades to a
# breathing standby value when it is not.
# ---------------------------------------------------------------------------


def audio_envelope(ctx: AudioFeatureContext) -> float:
    """Return a 0..1 loudness envelope from real audio, or a standby breath.

    Standby synthesis returns a neutral 0.5 so idle animation keeps moving at an
    unremarkable pace instead of pretending a track is playing.
    """
    if not ctx.is_active:
        return 0.5
    energy = max(ctx.sub_bass_energy, ctx.bass_energy, ctx.mid_energy, ctx.treble_energy)
    if energy <= 0.0:
        return 0.0
    return float(min(1.0, energy * 2.2))


def audio_scale(ctx: AudioFeatureContext, idle: float, floor: float = 0.45, gain: float = 0.9) -> float:
    """Return a multiplicative amplitude scale driven by the audio envelope."""
    return floor + gain * audio_envelope(ctx) * (0.75 + 0.25 * math.sin(idle * 1.3))


def audio_clock(ctx: AudioFeatureContext, idle: float, rate: float = 1.0) -> float:
    """Return an animation phase that advances faster and further on real audio.

    Motion is phase-driven in every renderer here, so warping the phase by the
    audio envelope makes the whole family respond to playback rate and energy
    without each renderer re-deriving its own clock.
    """
    return idle * rate * (0.6 + 0.8 * audio_envelope(ctx))


def audio_band(ctx: AudioFeatureContext, index: int) -> float:
    """Return one real frequency bin in 0..1, cycling when the spectrum is short."""
    levels = ctx.levels_128
    if len(levels) == 0:
        return 0.0
    return float(levels[index % len(levels)])


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
    if ctx.is_active:
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
    if ctx.is_active:
        # A real triggered scope: the pulse period comes from the actual
        # zero-crossing rate of the live waveform and the duty cycle from level.
        wave = np.sign(ctx.waveform_l)
        crossings = int(np.count_nonzero(np.diff(wave) != 0)) if len(wave) > 1 else 1
        period = max(4, min(w, int(w / max(1, crossings)) * 2))
        duty = 0.2 + 0.5 * float(np.mean(np.abs(ctx.waveform_l)))
    else:
        period = max(4, w // 6)
        duty = 0.5
    pulse_w = max(2, int(period * duty))
    for c in range(w):
        in_pulse = (c % period) < pulse_w
        val = (h * 0.35) if in_pulse else (-h * 0.35)
        y = max(0, min(h - 1, int(mid_y - val)))
        grid[y][c] = ("█", pal.primary_style())
        if c > 0 and (c % period) == 0:
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
    # Synthwave grid: the horizon glow and the perspective scroll are both
    # driven by the live spectrum, so the landscape surges with the track.
    levels = _get_interp_levels(ctx, w, idle)
    env = audio_envelope(ctx)
    scroll = int(idle * (2.0 + 6.0 * env))
    for r in range(h):
        if r < horizon:
            for c in range(w):
                if c % max(1, w // 8) == 0:
                    grid[r][c] = ("·", pal.dim_style())
                else:
                    glow = 1.0 - (horizon - r) / max(1, horizon)
                    if glow > 0.55 + 0.4 * float(levels[c]):
                        grid[r][c] = ("▒", pal.accent_style())
                    else:
                        grid[r][c] = ("·", pal.dim_style()) if (r + c) % 8 == 0 else (" ", pal.dim_style())
        else:
            depth = (r - horizon) / max(1, h - horizon)
            for c in range(w):
                grid[r][c] = ("═" if (r - horizon + scroll) % 3 == 0 else "─", pal.primary_style() if depth > 0.6 else pal.dim_style())
                if (c - w // 2 + scroll) % max(1, int(12 * (1 - depth * 0.7))) == 0:
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
    # The canyon walls are carved by the live spectrum: each row's notch width
    # follows a different frequency band, so the gorge profile is the spectrum.
    levels = _get_interp_levels(ctx, max(1, h), idle)
    for r in range(h):
        depth = r / max(1, h - 1)
        carve = float(levels[r % len(levels)])
        canyon_w = int(depth * (w * 0.45) * (0.35 + 1.3 * carve))
        c1 = max(0, mid_x - canyon_w)
        c2 = min(w - 1, mid_x + canyon_w)
        wall = "▓" if carve > 0.55 else "█"
        for c in range(0, c1):
            grid[r][c] = (wall, pal.primary_style())
        for c in range(c2, w):
            grid[r][c] = (wall, pal.primary_style())
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
    # Each hex cell is driven by its own frequency bin, so the honeycomb
    # tessellation pulses with the real spectrum across the plate.
    levels = _get_interp_levels(ctx, max(1, (h // 4 + 1) * (w // 6 + 1)), idle)
    cell = 0
    for r in range(h):
        for c in range(w):
            is_hex = ((r % 4 == 0 and c % 6 == 0) or (r % 4 == 2 and c % 6 == 3))
            if is_hex:
                val = float(levels[cell % len(levels)])
                cell += 1
                grid[r][c] = ("⌬", pal.accent_style() if val > 0.45 else pal.primary_style())
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
    for _ in range(120):
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
    # Ellipse geometry from the real mid/side decomposition of the track.
    if ctx.is_active:
        mid_e = float(np.mean(np.abs(ctx.mid_channel))) if len(ctx.mid_channel) else 0.0
        side_e = float(np.mean(np.abs(ctx.side_channel))) if len(ctx.side_channel) else 0.0
        width_frac = 0.0 if mid_e + side_e <= 1e-6 else side_e / (side_e + mid_e)
    else:
        width_frac = 0.4 + 0.25 * math.sin(idle)
    m_scale = (w * 0.35) * (0.25 + 0.75 * width_frac)
    s_scale = (h * 0.35) * (0.35 + 0.65 * (1.0 - width_frac))
    theta = np.linspace(0, 2 * math.pi, 160)
    for t in theta:
        x = int(mid_x + math.cos(t) * m_scale)
        y = int(mid_y - math.sin(t) * s_scale)
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("░", pal.accent_style() if width_frac > 0.5 else pal.primary_style())
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
    mid_x = w // 2
    # Below ~120 Hz a mono-summed signal collapses onto the centre line: real
    # sub-bass energy decides how solid that column reads, and phase_corr says
    # whether the low end is actually mono-compatible.
    if ctx.is_active:
        sub = ctx.sub_bass_energy
        coherent = ctx.phase_corr > 0.5
    else:
        sub = 0.4 + 0.3 * math.sin(idle)
        coherent = math.cos(idle) > 0.0
    col_w = max(1, int(sub * (w * 0.1)))
    for r in range(h):
        for c in range(w):
            if c == mid_x:
                grid[r][c] = ("║", pal.accent_style(bold=True) if coherent else pal.dim_style())
            elif abs(c - mid_x) < col_w:
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
    # Torus radius and surface lighting follow the live band energies, so the
    # donut inflates and re-shades with the music instead of sitting static.
    env = audio_envelope(ctx)
    treble = ctx.treble_energy if ctx.is_active else 0.3 + 0.2 * math.sin(idle)
    ring_r = min(mid_x, mid_y * 2) * (0.45 + 0.3 * env)
    thickness = 3.0 + 2.0 * treble
    light = idle * 1.4
    for r in range(h):
        for c in range(w):
            dx = (c - mid_x) * 1.0
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            torus = abs(dist - ring_r)
            if torus < thickness:
                # Fake a directional light term around the torus cross-section.
                lit = math.cos(math.atan2(dy, dx) * 2.0 + light) * (1.0 - torus / thickness)
                shade_idx = int(max(0.0, min(1.0, 0.5 + 0.5 * lit)) * (len(_SHADES) - 1))
                grid[r][c] = (_SHADES[shade_idx], pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 6 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_neural_synapse(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    # Neuron count and firing intensity come from the live spectrum; transients
    # light the whole mesh up, sustained energy keeps a subset lit.
    levels = _get_interp_levels(ctx, 16, idle)
    env = audio_envelope(ctx)
    n_nodes = 3 + int(env * 6)
    nodes: list[tuple[int, int]] = []
    for i in range(n_nodes):
        ang = (i / max(1, n_nodes)) * 2 * math.pi + idle * 0.6
        rad = (0.18 + 0.28 * float(levels[i % len(levels)])) * min(w, h * 2)
        nodes.append(
            (
                max(0, min(w - 1, int(w / 2 + math.cos(ang) * rad))),
                max(0, min(h - 1, int(h / 2 + math.sin(ang) * rad * 0.5))),
            )
        )
    # Synaptic connections between neighbouring nodes.
    for a, b in zip(nodes, nodes[1:], strict=False):
        (x0, y0), (x1, y1) = a, b
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = int(x0 + (x1 - x0) * s / steps)
            y = int(y0 + (y1 - y0) * s / steps)
            if 0 <= x < w and 0 <= y < h and grid[y][x][0] == " ":
                grid[y][x] = ("·", pal.primary_style())
    for i, (nx, ny) in enumerate(nodes):
        if 0 <= nx < w and 0 <= ny < h:
            firing = float(levels[i % len(levels)]) > 0.5 or (ctx.transient_flag and env > 0.4)
            grid[ny][nx] = ("●", pal.accent_style(bold=True) if firing else pal.dim_style())
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_circuit_trace(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    # Current visibly flows along the bus lines: each trace carries a travelling
    # pulse whose brightness is that row's real frequency bin.
    levels = _get_interp_levels(ctx, max(1, h // 3 + 1), idle)
    flow = int(idle * (3.0 + 9.0 * audio_envelope(ctx)))
    for r in range(h):
        if r % 3 == 0:
            bus = r // 3
            val = float(levels[bus % len(levels)])
            for c in range(w):
                grid[r][c] = ("═", pal.primary_style() if val > 0.25 else pal.dim_style())
                if c % 8 == 0:
                    grid[r][c] = ("Ø", pal.accent_style())
                elif (c + flow) % max(4, int(8 + 24 * (1.0 - val))) == 0:
                    grid[r][c] = ("━", pal.accent_style(bold=True))
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
    # HUD interior: a real target lock that tracks the live band balance, plus
    # a sweeping radar line, so the frame is an instrument and not a border.
    levels = _get_interp_levels(ctx, max(1, w), idle)
    lock_x = int(float(np.argmax(levels)) / max(1, len(levels)) * (w - 1))
    lock_y = 1 + int(audio_envelope(ctx) * max(0, h - 3))
    if 0 <= lock_x < w and 0 <= lock_y < h:
        for d in range(2):
            if 0 <= lock_y - d < h:
                grid[lock_y - d][lock_x] = ("┃", pal.accent_style(bold=True))
            if 0 <= lock_x - d < w:
                grid[lock_y][lock_x - d] = ("━", pal.accent_style(bold=True))
        grid[lock_y][lock_x] = ("◉", pal.accent_style(bold=True))
    sweep = int(idle * 2.0) % max(1, w)
    for r in range(1, h - 1):
        if 0 <= sweep < w:
            grid[r][sweep] = ("▏", pal.primary_style())
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            if grid[r][c][0] == " " and (r + c) % 4 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_ascii_cube_3d(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    # Demoscene cube: true rotation about Y, with per-edge lighting from the
    # live band energies, so it genuinely tumbles and pulses to the beat.
    levels = _get_interp_levels(ctx, 12, idle)
    size_x, size_y = int(w * 0.2), int(h * 0.25)
    ang = idle
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    corners: list[tuple[int, int, float]] = []
    for cx, cy in ((-size_x, -size_y), (size_x, -size_y), (size_x, size_y), (-size_x, size_y)):
        rx = cx * cos_a - cy * sin_a
        ry = cx * sin_a + cy * cos_a
        depth = math.sin(ang) * 0.0 + (rx / max(1, size_x))
        corners.append((int(mid_x + rx), int(mid_y + ry), depth))
    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    for a_i, b_i in edges:
        (x0, y0, _), (x1, y1, _) = corners[a_i], corners[b_i]
        band = float(levels[a_i % len(levels)])
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = int(x0 + (x1 - x0) * s / steps)
            y = int(y0 + (y1 - y0) * s / steps)
            if 0 <= x < w and 0 <= y < h:
                style = pal.accent_style() if band > 0.5 else pal.primary_style()
                if (s // 2) % 2 == 0:
                    grid[y][x] = ("─" if abs(y1 - y0) <= abs(x1 - x0) else "│", style)
    for x, y, d in corners:
        if 0 <= x < w and 0 <= y < h:
            grid[y][x] = ("◆" if d >= 0 else "◇", pal.accent_style(bold=True))
    for r in range(h):
        for c in range(w):
            if grid[r][c][0] == " " and (r + c) % 5 == 0:
                grid[r][c] = ("·", pal.dim_style())
    return _canvas_to_text(grid)


def _render_cyber_cyberdeck_boot(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    # Telemetry lines are read off the live feature context, not hardcoded.
    if ctx.is_active:
        env = audio_envelope(ctx)
        logs = [
            f"DSP RMS {ctx.rms_db:6.1f} dBFS",
            f"LUFS-M {ctx.lufs_m:6.1f} LKFS",
            f"CREST {ctx.crest_factor:5.1f} dB TP",
            f"CENTROID {ctx.spectral_centroid:5.0f} Hz",
            f"BASS {ctx.bass_energy * 100:4.0f}%  ENV {env * 100:3.0f}%",
        ]
    else:
        logs = [
            "BIOS: OMNIRIP v2.4 OK",
            "DSP: STANDBY AWAITING SIGNAL",
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
    # Shred width and scroll speed are driven by the high end of the spectrum.
    treble = ctx.treble_energy if ctx.is_active else 0.25 + 0.15 * math.sin(idle)
    period = max(2, int(3 + 12 * (1.0 - treble)))
    speed = int(idle * (4.0 + 26.0 * treble))
    for c in range(w):
        shred = (c + speed) % period
        hot = shred == 0
        for r in range(h):
            grid[r][c] = ("|", pal.accent_style() if hot else pal.dim_style()) if hot else (" ", pal.dim_style())
            if grid[r][c][0] == " " and r % 3 == 0:
                grid[r][c] = ("·", pal.primary_style() if treble > 0.5 else pal.dim_style())
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
    # The funnel throat and spin rate are set by low-end energy, so a kick
    # tightens and whips the tornado while a sustained bass holds it open.
    bass = ctx.bass_energy if ctx.is_active else 0.2 + 0.1 * math.sin(idle)
    env = audio_envelope(ctx)
    throat = w * (0.12 + 0.5 * env)
    spin = int(idle * (5.0 + 30.0 * bass))
    for r in range(h):
        spread = (r / max(1, h)) ** 1.4
        width_r = int(spread * throat)
        for c in range(mid_x - width_r, mid_x + width_r + 1):
            if 0 <= c < w:
                hot = (r + c + spin) % max(2, int(2 + 6 * (1.0 - bass))) == 0
                grid[r][c] = ("@" if hot else "§", pal.accent_style() if hot else pal.primary_style())
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
    # Grain density rides the envelope, and the streak period shortens as the
    # broadband energy rises, so quiet passages look like still air.
    env = audio_envelope(ctx)
    streak = max(2, int(3 + 10 * (1.0 - env)))
    speed = int(idle * (6.0 + 34.0 * env))
    for r in range(h):
        for c in range(w):
            lit = (r + c * 2 + speed) % streak == 0
            grid[r][c] = ("·", pal.primary_style() if lit else pal.dim_style())
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
    # Chladni nodal lines for mode (m, n): the mode pair is chosen from the real
    # spectral centroid and energy, so different tracks excite different figures.
    if ctx.is_active:
        cent = ctx.spectral_centroid
        energy = max(ctx.bass_energy, ctx.mid_energy, ctx.treble_energy)
        m = 2 + int(cent / 900.0) % 5
        n = m + 2 + int(energy * 6.0) % 4
    else:
        m = 3 + int(abs(math.sin(idle)) * 3)
        n = 5 + int(abs(math.cos(idle)) * 3)
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
    # Chaos driven by the live spectrum: each frequency bin perturbs the
    # Lorenz coupling, so the attractor traces a genuinely track-specific path.
    levels = _get_interp_levels(ctx, 64, idle)
    rho = 20.0 + 14.0 * float(np.mean(levels[:32]))
    sigma = 8.0 + 4.0 * float(np.mean(levels[32:]))
    x, y, z = 0.1, 0.0, 0.0
    dt = 0.015
    for i in range(250):
        drive = 1.0 + 0.6 * float(levels[i % len(levels)])
        dx = 10.0 * (y - x) * dt
        dy = (x * (rho - z) - y) * dt * drive
        dz = (x * y - sigma * z) * dt
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
    # The gasket lattice stays fixed; its illumination is octave-driven, so the
    # solid cells breathe with the real frequency octaves of the track.
    levels = _get_interp_levels(ctx, 32, idle)
    for r in range(h):
        for c in range(w):
            val = (r & c) == 0
            octave = float(levels[(r + c) % len(levels)])
            if val and octave > 0.6:
                grid[r][c] = ("▲", pal.accent_style())
            elif val and octave > 0.3:
                grid[r][c] = ("▲", pal.primary_style())
            elif val:
                grid[r][c] = ("▲", pal.dim_style())
            else:
                grid[r][c] = ("·", pal.dim_style())
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
    # Seed count and centroid orbit both track the live spectrum.
    n_seeds = 3 + int(audio_envelope(ctx) * 5)
    energy = audio_envelope(ctx)
    pts: list[tuple[int, int]] = []
    for i in range(n_seeds):
        ang = (i / max(1, n_seeds)) * 2 * math.pi + idle
        rad = (0.2 + 0.25 * ((i % 3) / 2.0)) * min(w, h * 2)
        px = int(w / 2 + math.cos(ang) * rad)
        py = int(h / 2 + math.sin(ang) * rad * 0.5)
        pts.append((max(0, min(w - 1, px)), max(0, min(h - 1, py))))
    for r in range(h):
        for c in range(w):
            dists = sorted(math.sqrt((c - px) ** 2 + ((r - py) * 2.0) ** 2) for px, py in pts)
            if len(dists) > 1 and dists[1] - dists[0] < 1.2:
                grid[r][c] = ("│", pal.accent_style() if energy > 0.5 else pal.primary_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


# ---------------------------------------------------------------------------
# Pack 8: Studio Forensic Telemetry Renderers (10 additional)
# ---------------------------------------------------------------------------


def _render_meter_ebu_r128_radar(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    mid_x, mid_y = w // 2, h // 2
    # Real momentary loudness mapped onto the EBU R128 -70..0 LUFS scale.
    lufs = ctx.lufs_m if ctx.is_active else -30.0 + 12.0 * math.sin(idle)
    loud_frac = max(0.0, min(1.0, (lufs + 70.0) / 70.0))
    radius = min(mid_x, mid_y * 2)
    for r in range(h):
        for c in range(w):
            dx = c - mid_x
            dy = (r - mid_y) * 2.0
            dist = math.sqrt(dx * dx + dy * dy)
            ring = radius * 0.7
            if abs(dist - ring) < 1.2:
                grid[r][c] = ("◎", pal.accent_style())
            elif c == mid_x or r == mid_y:
                grid[r][c] = ("·", pal.dim_style())

    # Loudness wedge sweeping from the centre out to the current LUFS position.
    wedge = max(0.0, min(radius * 0.7, loud_frac * radius * 0.7))
    for c in range(w):
        if abs(c - mid_x) <= wedge:
            grid[mid_y][c] = ("█", pal.primary_style() if loud_frac < 0.86 else pal.accent_style())
    bar_row = min(h - 1, mid_y + max(1, mid_y // 2))
    for c in range(w):
        grid[bar_row][c] = ("▬", pal.dim_style())
    for c in range(w):
        pos = int(loud_frac * (w - 1))
        if c == pos:
            grid[bar_row][c] = ("▼", pal.accent_style(bold=True))
    return _canvas_to_text(grid)


def _render_meter_k_system_master(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    # K-12/K-14/K-20 reference lines drawn against the live level spectrum.
    levels = _get_interp_levels(ctx, w, idle)
    ref = 0.72 if ctx.is_active else 0.45 + 0.2 * math.sin(idle)
    for r in range(h):
        for c in range(w):
            val = float(levels[c])
            filled = val >= ref
            if r == h // 3:
                grid[r][c] = ("─", pal.accent_style())
            elif filled:
                grid[r][c] = ("█", pal.primary_style() if r > h // 3 else pal.accent_style())
            else:
                grid[r][c] = ("·", pal.dim_style()) if (r + c) % 4 == 0 else (" ", pal.dim_style())
    return _canvas_to_text(grid)


def _render_meter_true_peak_forensic(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette) -> Text:
    grid = _create_canvas(w, h, " ", pal.dim_style())
    if ctx.is_active:
        # Inter-sample true peak in dBFS, straight off the decoded samples.
        peak = float(np.max(np.abs(ctx.waveform_l))) if len(ctx.waveform_l) else 0.0
        tp_db = 20.0 * math.log10(peak) if peak > 1e-6 else -60.0
    else:
        tp_db = -12.0 + 8.0 * math.sin(idle)
    for c in range(w):
        grid[h // 2][c] = (
            "█" if tp_db >= -0.1 else ("▆" if tp_db > -6.0 else "░"),
            pal.accent_style() if tp_db > -0.1 else pal.primary_style(),
        )
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
    # Centre of gravity from real mid (mono) vs side (stereo) energy.
    if ctx.is_active:
        mid_e = float(np.mean(np.abs(ctx.mid_channel))) if len(ctx.mid_channel) else 0.0
        side_e = float(np.mean(np.abs(ctx.side_channel))) if len(ctx.side_channel) else 0.0
        balance = 0.0 if mid_e + side_e <= 1e-6 else (side_e - mid_e) / (side_e + mid_e)
    else:
        balance = math.sin(idle) * 0.6
    for c in range(w):
        grid[mid_y][c] = ("─", pal.dim_style())
    for r in range(h):
        grid[r][mid_x] = ("│", pal.dim_style())
    marker_x = int(max(0, min(w - 1, mid_x + balance * (mid_x * 0.8))))
    for d in range(max(1, mid_y)):
        y = mid_y - d
        if 0 <= y < h:
            grid[y][marker_x] = ("●", pal.accent_style(bold=True))
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
    if ctx.is_active:
        # Pleasurize DR: crest-derived DR estimate, clamped to the published 1..20 scale.
        dr = int(round(max(1.0, min(20.0, ctx.crest_factor * 0.85))))
    else:
        dr = 12
    rating = "PERFECT" if dr >= 14 else ("OPTIMAL" if dr >= 10 else ("CLIPPING" if dr <= 6 else "GOOD"))
    label = f"DR{dr} [{rating}]"
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
# Engine Catalog Definitions (91 procedural engines, 100 total with the
# foundational and headline engines registered by registry.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineSpec:
    """Declarative description of one catalog visualizer engine."""

    id: str
    name: str
    category: str
    icon: str
    description: str
    renderer: RendererFn
    min_width: int = 10
    min_height: int = 4


CATALOG_91_SPECS: list[tuple[str, str, str, str, str, Callable]] = [
    # Pack 1: Spectral (11 engines)
    EngineSpec("spectral_waterfall_bars", "Spectral Waterfall Gradient", "spectral", "⌗", "Falling peak-decay frequency spectrum with color heat.", _render_spectral_waterfall_bars),
    EngineSpec("spectral_braille_dense", "Braille High-Res Spectrum", "spectral", "⌗", "High-density 2x4 braille dots frequency bins.", _render_spectral_braille_dense),
    EngineSpec("spectral_vfd_vintage", "Vintage VFD Fluorescent Analyzer", "spectral", "⌗", "Fluorescent vacuum display segments with needle peak hold.", _render_spectral_vfd_vintage),
    EngineSpec("spectral_iso_31band", "31-Band 1/3-Octave Analyzer", "spectral", "⌗", "Calibrated ANSI 1/3-octave graphic EQ display.", _render_spectral_iso_31band),
    EngineSpec("spectral_comb_harmonics", "Harmonic Comb Analyzer", "spectral", "⌗", "Fundamental pitch tracking with integer harmonic combs.", _render_spectral_comb_harmonics),
    EngineSpec("spectral_ribbon_energy", "Energy Density Ribbon", "spectral", "⌗", "Continuous smooth spline ribbon of spectral power.", _render_spectral_ribbon_energy),
    EngineSpec("spectral_log_cascade", "Logarithmic Frequency Cascade", "spectral", "⌗", "Human-auditory bark scale logarithmic cascade.", _render_spectral_log_cascade),
    EngineSpec("spectral_cepstrum", "Audio Cepstrum Quefrency", "spectral", "⌗", "FFT of log-spectrum showing pitch timbre quefrency.", _render_spectral_cepstrum),
    EngineSpec("spectral_differential", "Differential Mid/Side Spectrum", "spectral", "⌗", "Overlaid mid (mono) vs side (stereo) spectral differential.", _render_spectral_differential),
    EngineSpec("spectral_gravity_peaks", "Gravity Falling Peak Needles", "spectral", "⌗", "Physics-simulated ballistics for peak needles.", _render_spectral_gravity_peaks),
    EngineSpec("spectral_sub_bass_rumble", "Sub-Bass Seismic Scope", "spectral", "⌗", "Deep zoom on 10Hz - 160Hz sub-bass and kick transients.", _render_spectral_sub_bass_rumble),

    # Pack 2: Oscilloscope (11 engines)
    EngineSpec("scope_vector_xy", "Vector Beam Oscilloscope", "oscilloscope", "≋", "Reticle beam phosphor trace with electron gun decay.", _render_scope_vector_xy),
    EngineSpec("scope_dual_trace", "Dual-Trace Stereo Oscilloscope", "oscilloscope", "≋", "Split-beam CH1 (Left) and CH2 (Right) dual scope.", _render_scope_dual_trace),
    EngineSpec("scope_strobe_tuner", "Stroboscopic Tuning Scope", "oscilloscope", "≋", "Rotating strobe disc locking onto audio fundamental frequencies.", _render_scope_strobe_tuner),
    EngineSpec("scope_persistence_ghost", "Long-Persistence CRT Phosphor", "oscilloscope", "≋", "Decaying phosphorescent ghost afterglow trail.", _render_scope_persistence_ghost),
    EngineSpec("scope_trigger_holdoff", "Triggered Pulse Oscilloscope", "oscilloscope", "≋", "Zero-crossing edge triggered stable pulse scope.", _render_scope_trigger_holdoff),
    EngineSpec("scope_differential_ms", "M/S Sum & Difference Scope", "oscilloscope", "≋", "Mid/Side stereo component waveform trace.", _render_scope_differential_ms),
    EngineSpec("scope_circular_polar", "Circular Radial Polar Scope", "oscilloscope", "≋", "Radial oscilloscope blooming outward from circular reticle.", _render_scope_circular_polar),
    EngineSpec("scope_audio_glitch", "CRT Scanline Sync Loss", "oscilloscope", "≋", "Horizontal scanline jitter and vertical CRT blanking roll.", _render_scope_audio_glitch),
    EngineSpec("scope_tape_head", "Analog Tape Head Saturation", "oscilloscope", "≋", "Warm analog saturation wave with magnetic hysteresis.", _render_scope_tape_head),
    EngineSpec("scope_braille_stereo", "Braille Stereo Waveform Cross", "oscilloscope", "≋", "Interleaved dual braille waveforms.", _render_scope_braille_stereo),
    EngineSpec("scope_subpixel_interp", "Hermite Interpolated Trace", "oscilloscope", "≋", "Smooth cubic Hermite spline anti-aliased trace.", _render_scope_subpixel_interp),

    # Pack 3: Stanford 3D Waterfalls & Terrains (12 engines)
    EngineSpec("terrain_cyber_wireframe", "3D Cyberpunk Wireframe Terrain", "waterfall_3d", "▲", "Retro synthwave 80s neon grid mountain landscape.", _render_terrain_cyber_wireframe),
    EngineSpec("terrain_isometric_voxels", "Isometric Voxel Cityscape", "waterfall_3d", "▲", "3D audio-reactive skyscraper towers rising with bass.", _render_terrain_isometric_voxels),
    EngineSpec("terrain_spectral_canyon", "Audio Spectral Canyon", "waterfall_3d", "▲", "Flight down a winding 3D canyon carved by audio frequencies.", _render_terrain_spectral_canyon),
    EngineSpec("terrain_ribbon_highway", "Warp Horizon Audio Highway", "waterfall_3d", "▲", "Receding 3D grid highway with floating frequency arches.", _render_terrain_ribbon_highway),
    EngineSpec("terrain_contour_map", "Topographic Contour Elevation", "waterfall_3d", "▲", "Iso-height elevation contours of sound pressure levels.", _render_terrain_contour_map),
    EngineSpec("terrain_hex_grid_mesh", "Hexagonal Cyber Honeycomb", "waterfall_3d", "▲", "3D tessellated hex cells pulsing with frequency energy.", _render_terrain_hex_grid_mesh),
    EngineSpec("terrain_tunnel_vortex", "3D Audio Wireframe Tunnel", "waterfall_3d", "▲", "Traveling down an infinite perspective wireframe tunnel.", _render_terrain_tunnel_vortex),
    EngineSpec("terrain_mountain_horizon", "SunMusic Alpine Mountain Range", "waterfall_3d", "▲", "Majestic mountain peaks etched against the twilight horizon.", _render_terrain_mountain_horizon),
    EngineSpec("terrain_vector_globe", "3D Rotating Wireframe Sphere", "waterfall_3d", "▲", "Rotating 3D geodesic sphere deformed by audio waves.", _render_terrain_vector_globe),
    EngineSpec("terrain_matrix_landscape", "Matrix Glyph Topography", "waterfall_3d", "▲", "3D heightfield made entirely of glowing cascading code.", _render_terrain_matrix_landscape),
    EngineSpec("terrain_standing_wave_3d", "3D Standing Acoustic Wave", "waterfall_3d", "▲", "Three-dimensional nodal acoustic standing wave grid.", _render_terrain_standing_wave_3d),
    EngineSpec("terrain_dune_ripples", "Acoustic Sand Dune Ripples", "waterfall_3d", "▲", "Wind-swept desert dune ripples shifting with low frequencies.", _render_terrain_dune_ripples),

    # Pack 4: Stereo Phase & Lissajous (11 engines)
    EngineSpec("phase_goniometer_diamond", "Goniometer Diamond Scope", "stereo_phase", "⌖", "45-degree tilted goniometer showing stereo width.", _render_phase_goniometer_diamond),
    EngineSpec("phase_correlation_compass", "Phase Correlation Radar Compass", "stereo_phase", "⌖", "360-degree vector dial showing phase coherence.", _render_phase_correlation_compass),
    EngineSpec("phase_polar_vector", "Polar Vector Field Scope", "stereo_phase", "⌖", "Vector cloud displaying instantaneous stereo dispersion.", _render_phase_polar_vector),
    EngineSpec("phase_orbit_knot", "Harmonic Torus Knot", "stereo_phase", "⌖", "3D stereoscopic parametric torus knot rotating with phase.", _render_phase_orbit_knot),
    EngineSpec("phase_ms_balance_radar", "Mid/Side Balance Ellipse", "stereo_phase", "⌖", "Elliptical stereo balance meter tracking spatial width.", _render_phase_ms_balance_radar),
    EngineSpec("phase_stereo_jostle", "Stereo Phase Jitter Scope", "stereo_phase", "⌖", "Micro-phase fluctuations between left and right channels.", _render_phase_stereo_jostle),
    EngineSpec("phase_spirograph_orbit", "Spirographic Epicycloid Orbit", "stereo_phase", "⌖", "Epicyclic orbital curves modulated by harmonic intervals.", _render_phase_spirograph_orbit),
    EngineSpec("phase_sub_bass_mono_check", "Sub-Bass Mono Correlation", "stereo_phase", "⌖", "Forensic phase coherence below 120Hz for vinyl/club check.", _render_phase_sub_bass_mono_check),
    EngineSpec("phase_vector_flower", "Parametric Acoustic Rose", "stereo_phase", "⌖", "Rose curve blooming with stereo energy.", _render_phase_vector_flower),
    EngineSpec("phase_lissajous_3d", "3D Lissajous Orthographic", "stereo_phase", "⌖", "Projected 3D Lissajous figure tumbling in spatial axes.", _render_phase_lissajous_3d),
    EngineSpec("phase_stereo_field_cloud", "Stereo Soundfield Cloud", "stereo_phase", "⌖", "Cloud of phosphor particles showing acoustic spatialization.", _render_phase_stereo_field_cloud),

    # Pack 5: Cyber Matrix & Generative (12 engines)
    EngineSpec("cyber_hex_memory_dump", "Cyber Hex Memory Dump", "cyber_matrix", "⌬", "Scrolling memory addresses, hex bytes, and ASCII inspection.", _render_cyber_hex_memory_dump),
    EngineSpec("cyber_binary_cascade", "Binary Stream Waterfall", "cyber_matrix", "⌬", "Cascades of 0s and 1s responding to bit depth and dynamic range.", _render_cyber_binary_cascade),
    EngineSpec("cyber_audio_glitch_rot", "Glitch Audio Buffer Bit Rot", "cyber_matrix", "⌬", "CRT corruption, memory scramble, and cyber byte shifts.", _render_cyber_audio_glitch_rot),
    EngineSpec("cyber_ascii_raymarch", "ASCII Raymarching Donut", "cyber_matrix", "⌬", "3D spinning torus rendered with ASCII lighting.", _render_cyber_ascii_raymarch),
    EngineSpec("cyber_neural_synapse", "Neural Network Synapse Mesh", "cyber_matrix", "⌬", "Interconnected neural nodes firing with acoustic transients.", _render_cyber_neural_synapse),
    EngineSpec("cyber_circuit_trace", "Printed Circuit Board Traces", "cyber_matrix", "⌬", "Glowing PCB bus lines carrying audio current.", _render_cyber_circuit_trace),
    EngineSpec("cyber_dna_helix", "Acoustic DNA Double Helix", "cyber_matrix", "⌬", "Rotating double helix twisted and illuminated by frequency bins.", _render_cyber_dna_helix),
    EngineSpec("cyber_quantum_lattice", "Quantum State Grid Lattice", "cyber_matrix", "⌬", "Probability wave lattice collapsing on transient beats.", _render_cyber_quantum_lattice),
    EngineSpec("cyber_terminal_hud", "Cyberpunk Tactical HUD", "cyber_matrix", "⌬", "Sci-fi combat cockpit display with frequency target locks.", _render_cyber_terminal_hud),
    EngineSpec("cyber_ascii_cube_3d", "Rotating 3D ASCII Cube", "cyber_matrix", "⌬", "Classic demoscene wireframe cube spinning to the beat.", _render_cyber_ascii_cube_3d),
    EngineSpec("cyber_cyberdeck_boot", "Cyberdeck Kernel Telemetry", "cyber_matrix", "⌬", "Real-time system telemetry and forensic DSP registers.", _render_cyber_cyberdeck_boot),
    EngineSpec("cyber_audio_spectrum_shred", "Spectrum Data Shredder", "cyber_matrix", "⌬", "Fragmenting data strips dissolving on peak drops.", _render_cyber_audio_spectrum_shred),

    # Pack 6: Particle Systems & Fluid Dynamics (12 engines)
    EngineSpec("particles_plasma_sphere", "Demoscene Plasma Sphere", "particles_fluid", "✦", "Swirling sine plasma field with psychedelic color interference.", _render_particles_plasma_sphere),
    EngineSpec("particles_spark_fountain", "Acoustic Spark Fountain", "particles_fluid", "✦", "Gravity-accelerated embers blasting upward on kick transients.", _render_particles_spark_fountain),
    EngineSpec("particles_liquid_mercury", "Liquid Mercury Ripple Basin", "particles_fluid", "✦", "Concentric surface tension waves spreading across liquid pool.", _render_particles_liquid_mercury),
    EngineSpec("particles_starfield_warp", "Audio Starfield Warp Speed", "particles_fluid", "✦", "3D stars accelerating into hyperspace lines with music tempo.", _render_particles_starfield_warp),
    EngineSpec("particles_vortex_tornado", "Acoustic Tornado Vortex", "particles_fluid", "✦", "Twisting cyclonic particle vortex spinning with frequency energy.", _render_particles_vortex_tornado),
    EngineSpec("particles_supernova_burst", "Audio Supernova Explosion", "particles_fluid", "✦", "Shockwave expanding outward from center on beat drops.", _render_particles_supernova_burst),
    EngineSpec("particles_bubble_chamber", "Quantum Bubble Chamber", "particles_fluid", "✦", "Spiral particle tracks curving in magnetic field.", _render_particles_bubble_chamber),
    EngineSpec("particles_sand_storm", "Desert Sandstorm Dust", "particles_fluid", "✦", "Swirling atmospheric particle storm driven by wind harmonics.", _render_particles_sand_storm),
    EngineSpec("particles_galaxy_spiral", "Rotating Spiral Galaxy", "particles_fluid", "✦", "Two-arm logarithmic spiral galaxy rotating with tempo.", _render_particles_galaxy_spiral),
    EngineSpec("particles_aurora_borealis", "Aurora Borealis Ribbon", "particles_fluid", "✦", "Shimmering curtains of Northern Lights swaying with mids and highs.", _render_particles_aurora_borealis),
    EngineSpec("particles_electric_arc", "Tesla Coil Electric Lightning", "particles_fluid", "✦", "Branching jagged electrical discharge striking terminal borders.", _render_particles_electric_arc),
    EngineSpec("particles_cellular_automata", "Conway Game of Life Audio", "particles_fluid", "✦", "Cellular automata seeded by audio frequency transitions.", _render_particles_cellular_automata),

    # Pack 7: Geometric & Math Fractals (12 engines)
    EngineSpec("fractal_chladni_plate", "Chladni Resonant Cymatics Plate", "math_fractal", "◈", "Acoustic nodal lines on vibrating sand plates.", _render_fractal_chladni_plate),
    EngineSpec("fractal_mandelbrot_zoom", "Mandelbrot Fractal Audio Zoom", "math_fractal", "◈", "Complex number Mandelbrot set pulsating with audio depth.", _render_fractal_mandelbrot_zoom),
    EngineSpec("fractal_julia_morph", "Julia Set Acoustic Morpher", "math_fractal", "◈", "z -> z^2 + c Julia morpher modulated by audio centroid and RMS.", _render_fractal_julia_morph),
    EngineSpec("fractal_sacred_spirograph", "Sacred Geometry Spirograph", "math_fractal", "◈", "Harmonic epicycloids and hypocycloids forming floral mandalas.", _render_fractal_sacred_spirograph),
    EngineSpec("fractal_lorenz_attractor", "Lorenz Strange Attractor", "math_fractal", "◈", "Chaotic butterfly attractor orbiting in phase space.", _render_fractal_lorenz_attractor),
    EngineSpec("fractal_sierpinski_gasket", "Sierpinski Audio Gasket", "math_fractal", "◈", "Recursive triangle lattice illuminated by frequency octaves.", _render_fractal_sierpinski_gasket),
    EngineSpec("fractal_barnsley_fern", "Barnsley Fern Audio Branch", "math_fractal", "◈", "Fractal IFS fern swaying and growing with acoustic energy.", _render_fractal_barnsley_fern),
    EngineSpec("fractal_fibonacci_spiral", "Golden Ratio Fibonacci Spiral", "math_fractal", "◈", "Sunflower seed phyllotaxis points blooming with volume.", _render_fractal_fibonacci_spiral),
    EngineSpec("fractal_koch_snowflake", "Koch Snowflake Resonator", "math_fractal", "◈", "Self-similar fractal snowflake perimeter expanding with transients.", _render_fractal_koch_snowflake),
    EngineSpec("fractal_dragon_curve", "Heighway Dragon Curve", "math_fractal", "◈", "Recursive paper-folding fractal path tracing harmonic intervals.", _render_fractal_dragon_curve),
    EngineSpec("fractal_hyperbolic_tiling", "Poincaré Hyperbolic Disk", "math_fractal", "◈", "Escher-style non-Euclidean hyperbolic tessellation.", _render_fractal_hyperbolic_tiling),
    EngineSpec("fractal_voronoi_cells", "Voronoi Dynamic Crystal Grid", "math_fractal", "◈", "Voronoi cellular diagram with centroids orbiting to the music.", _render_fractal_voronoi_cells),

    # Pack 8: Studio Forensic Telemetry (10 engines)
    EngineSpec("meter_ebu_r128_radar", "EBU R128 Loudness Radar", "studio_meters", "𝄢", "Circular 360-degree radar showing Momentary/Short-Term LUFS history.", _render_meter_ebu_r128_radar),
    EngineSpec("meter_k_system_master", "Bob Katz K-System Meter", "studio_meters", "𝄢", "Calibrated K-12, K-14, and K-20 mastering scale with headroom zones.", _render_meter_k_system_master),
    EngineSpec("meter_true_peak_forensic", "True Peak Intersample Forensic", "studio_meters", "𝄢", "4x oversampled true peak meter detecting intersample clipping.", _render_meter_true_peak_forensic),
    EngineSpec("meter_crest_factor_dial", "Dynamic Range Crest Factor Dial", "studio_meters", "𝄢", "Telemetry needle displaying peak-to-RMS crest ratio.", _render_meter_crest_factor_dial),
    EngineSpec("meter_stereo_balance_radar", "Stereo Soundstage Balance Radar", "studio_meters", "𝄢", "L/R energy distribution and acoustic center of gravity.", _render_meter_stereo_balance_radar),
    EngineSpec("meter_clipping_density", "Clipping Density Heatmap", "studio_meters", "𝄢", "Forensic sample saturation and digital flat-top detection.", _render_meter_clipping_density),
    EngineSpec("meter_phase_correlation_bar", "Forensic Phase Correlation Bar", "studio_meters", "𝄢", "Calibrated -1.0 to +1.0 phase correlation bar.", _render_meter_phase_correlation_bar),
    EngineSpec("meter_dr_meter_offline", "Pleasurize Music DR Dynamic Meter", "studio_meters", "𝄢", "Official DR1 to DR20 dynamic range score meter.", _render_meter_dr_meter_offline),
    EngineSpec("meter_spectral_centroid_dial", "Spectral Centroid Timbre Dial", "studio_meters", "𝄢", "Center-of-mass acoustic frequency gauge in Hertz.", _render_meter_spectral_centroid_dial),
    EngineSpec("meter_harman_target_tracker", "Harman Target Compliance Gauge", "studio_meters", "𝄢", "Acoustic curve compliance meter vs Harman / DF target.", _render_meter_harman_target_tracker),
]


def _make_render_frame(spec: EngineSpec) -> Callable[..., Text]:
    """Bind an EngineSpec's renderer into a BaseVisualizerEngine.render_frame."""

    def render_frame(
        self,
        width: int,
        height: int,
        ctx: AudioFeatureContext,
        idle_phase: float = 0.0,
        palette: ColorPalette | None = None,
    ) -> Text:
        pal = palette if palette is not None else PALETTES[DEFAULT_PALETTE_KEY]
        # Every renderer here is a pure function of its phase, so warping the
        # phase by the live audio envelope makes the whole catalog react to
        # playback even where the renderer draws no explicit audio term.
        phase = audio_clock(ctx, idle_phase)
        frame_w, frame_h = clamp_frame_size(width, height, spec.min_width, spec.min_height)
        return spec.renderer(frame_w, frame_h, ctx, phase, pal)

    return render_frame


def register_catalog_100() -> None:
    """Register all 91 procedural catalog engines into VisualizerRegistry."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    for spec in CATALOG_91_SPECS:
        engine_type = type(
            f"Engine_{spec.id}",
            (BaseVisualizerEngine,),
            {
                "id": spec.id,
                "name": spec.name,
                "category": spec.category,
                "icon": spec.icon,
                "description": spec.description,
                "min_width": spec.min_width,
                "min_height": spec.min_height,
                "render_frame": _make_render_frame(spec),
            },
        )
        VisualizerRegistry.register(engine_type)

