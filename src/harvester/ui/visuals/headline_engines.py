"""Headline visualizer engines: Stanford 3D Waterfall, Matrix Digital Rain, Lissajous, and Audio Flame."""

from __future__ import annotations

import math
import random

import numpy as np
from rich.style import Style
from rich.text import Text

from harvester.ui.visuals.base import (
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
)

# Katakana and cyber glyph alphabet for Matrix Digital Rain
_MATRIX_GLYPHS = (
    "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ"
    "0123456789"
    "ABCDEF"
    "⚡⌗⌬◈✦"
)


class StanfordSunMusic3DEngine(BaseVisualizerEngine):
    """CCRMA Stanford 3D perspective waterfall wireframe terrain with hidden-line culling.

    Inspired by Stanford CCRMA SunMusic2 and cliviz 3D spectrogram visualizers.
    Draws a deep 3D perspective mesh receding into the horizon, projecting
    audio frequency FFT slices across time with dynamic elevation and contour lines.
    """

    id = "stanford_sun_music_3d"
    name = "Stanford SunMusic 3D Waterfall"
    category = "waterfall_3d"
    icon = "▲"
    description = "CCRMA Stanford 3D perspective waterfall wireframe terrain with hidden-line culling."
    min_width = 24
    min_height = 8

    def __init__(self) -> None:
        super().__init__()
        self._history_slices: list[np.ndarray] = []
        self._max_history: int = 24
        self._last_phase: float = 0.0

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

        # 1. Update historical FFT slice ring buffer
        if ctx.is_active:
            current_slice = ctx.levels_128.copy()
        else:
            # Standby breathing harmonic wave across 128 bins
            idx = np.arange(128, dtype=np.float32)
            base = 0.32 * np.sin(idle_phase * 1.8 + idx * 0.12) + 0.18 * np.cos(idle_phase * 0.9 + idx * 0.06)
            current_slice = np.clip(0.24 + base, 0.05, 0.90).astype(np.float32)

        self._history_slices.insert(0, current_slice)
        if len(self._history_slices) > self._max_history:
            self._history_slices = self._history_slices[: self._max_history]

        # Ensure we have at least 8 slices for depth perspective
        while len(self._history_slices) < 8:
            self._history_slices.append(current_slice.copy() * 0.7)

        num_slices = len(self._history_slices)

        # 2. 3D Screen buffer: characters and styles
        screen: list[list[tuple[str, Style]]] = [
            [(" ", palette.dim_style()) for _ in range(w)] for _ in range(h)
        ]

        # Horizon line and vanishing point
        horizon_y = max(1, int(h * 0.18))
        ground_y = h - 1

        # Render background grid and starfield/horizon guide lines
        for c in range(w):
            if c % 8 == 0:
                screen[horizon_y][c] = ("·", palette.dim_style())
            if c % 16 == 0 and horizon_y > 0:
                screen[horizon_y - 1][c] = ("·", palette.dim_style())

        # 3. Front-to-back perspective projection with painter's occlusion
        # We render slices from back (horizon, distance) to front (screen foreground)
        # to layer closer ridges over distant valleys.
        slice_indices = list(range(num_slices - 1, -1, -1))

        # Color depth ramps
        style_peak = palette.accent_style(bold=True)
        style_near = palette.primary_style(bold=True)
        style_mid = Style.parse(palette.secondary)
        style_far = palette.dim_style()

        for s_idx in slice_indices:
            depth_ratio = s_idx / max(1, num_slices - 1)  # 0.0 (near) to 1.0 (far horizon)
            slice_data = self._history_slices[s_idx]

            # Perspective geometry parameters
            persp = 1.0 - (depth_ratio * 0.62)  # Closer slices are wider and taller
            slice_baseline_y = horizon_y + int((ground_y - horizon_y) * (1.0 - depth_ratio))

            # Resample FFT slice across terminal columns
            # Apply perspective inset toward vanishing center
            center_x = w / 2.0
            margin_x = int(center_x * depth_ratio * 0.35)
            active_cols = max(4, w - (margin_x * 2))

            interp_levels = np.interp(
                np.linspace(0, 1, active_cols),
                np.linspace(0, 1, len(slice_data)),
                slice_data,
            )

            # Pick style based on depth layer
            if depth_ratio < 0.25:
                curr_style = style_near
                fill_char = "█"
                wire_char = "━"
            elif depth_ratio < 0.55:
                curr_style = style_mid
                fill_char = "▓"
                wire_char = "─"
            else:
                curr_style = style_far
                fill_char = "░"
                wire_char = "┄"

            # Draw cross-sectional mountain ridge
            prev_py = -1
            for col_offset in range(active_cols):
                col_x = margin_x + col_offset
                if col_x >= w:
                    break

                lvl = float(interp_levels[col_offset])
                # Peak height scaled by perspective and audio amplitude
                peak_height = int(lvl * (h * 0.48) * persp)
                projected_y = max(0, min(h - 1, slice_baseline_y - peak_height))

                # Ridge crest glyph
                if lvl > 0.65 and depth_ratio < 0.3:
                    crest_char = "▲"
                    crest_style = style_peak
                elif prev_py != -1 and abs(projected_y - prev_py) >= 1:
                    crest_char = "╱" if projected_y < prev_py else "╲"
                    crest_style = curr_style
                else:
                    crest_char = wire_char
                    crest_style = curr_style

                screen[projected_y][col_x] = (crest_char, crest_style)

                # Vertical wireframe rib down to slice baseline
                for fill_y in range(projected_y + 1, min(h, slice_baseline_y + 1)):
                    # Only fill if cell is empty or dim
                    if screen[fill_y][col_x][0] in (" ", "·", "┄"):
                        screen[fill_y][col_x] = ("│" if col_x % 4 == 0 else fill_char, curr_style)

                prev_py = projected_y

        # Build Rich Text object
        text = Text()
        for r_idx, row_cells in enumerate(screen):
            for char, st in row_cells:
                text.append(char, style=st)
            if r_idx < h - 1:
                text.append("\n")

        return text


class MatrixDigitalRainEngine(BaseVisualizerEngine):
    """Cyberpunk audio-reactive falling Katakana and hex code stream.

    Drop speeds accelerate with audio tempo and RMS energy. Transients and
    bass peaks fire intense neon head glyphs that trigger vertical cascading
    phosphor code trails across every terminal column.
    """

    id = "matrix_digital_rain"
    name = "Matrix Cyber Digital Rain"
    category = "cyber_matrix"
    icon = "⌬"
    description = "Audio-reactive falling katakana glyph streams with tempo cascades and neon transient glow."
    min_width = 16
    min_height = 6

    def __init__(self) -> None:
        super().__init__()
        # State for each column: head_y, speed, length, chars
        self._columns_head: list[float] = []
        self._columns_speed: list[float] = []
        self._columns_len: list[int] = []
        self._columns_chars: list[list[str]] = []
        self._last_w: int = 0
        self._last_h: int = 0

    def _init_columns(self, width: int, height: int) -> None:
        self._last_w = width
        self._last_h = height
        self._columns_head = [float(random.randint(-height, height)) for _ in range(width)]
        self._columns_speed = [random.uniform(0.35, 1.1) for _ in range(width)]
        self._columns_len = [random.randint(max(4, height // 3), max(8, height)) for _ in range(width)]
        self._columns_chars = [
            [random.choice(_MATRIX_GLYPHS) for _ in range(height + 16)]
            for _ in range(width)
        ]

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

        if w != self._last_w or h != self._last_h or len(self._columns_head) != w:
            self._init_columns(w, h)

        # Audio reactivity modulation factors
        # 1. Overall energy boost
        rms_energy = np.clip(np.mean(ctx.levels_128), 0.05, 1.0) if (ctx.is_active) else 0.20
        speed_mult = 1.0 + float(rms_energy * 2.2)

        # 2. Resample levels across all columns for per-column audio reactivity
        col_energies = np.interp(
            np.linspace(0, 1, w),
            np.linspace(0, 1, len(ctx.levels_128)),
            ctx.levels_128,
        ).astype(np.float32)

        # Styles
        style_lead = palette.accent_style(bold=True)  # White / neon head
        style_body = palette.primary_style(bold=True)  # Bright green
        style_tail = Style.parse(palette.secondary)     # Mid green
        style_dim = palette.dim_style()                 # Fading dark green

        lines: list[list[tuple[str, Style]]] = [
            [(" ", style_dim) for _ in range(w)] for _ in range(h)
        ]

        for c in range(w):
            col_eng = float(col_energies[c])
            # Advance stream head
            step = (self._columns_speed[c] * speed_mult) + (col_eng * 0.8)
            self._columns_head[c] += step

            trail_len = self._columns_len[c]
            head_y = self._columns_head[c]

            # Loop column stream when it runs off screen
            if head_y - trail_len > h:
                self._columns_head[c] = float(-random.randint(1, max(3, h // 2)))
                self._columns_speed[c] = random.uniform(0.35, 1.1)
                self._columns_len[c] = random.randint(max(4, h // 3), max(8, h))

            # Random glyph mutation (faster with higher audio energy)
            if random.random() < (0.12 + col_eng * 0.4):
                mutate_idx = random.randint(0, len(self._columns_chars[c]) - 1)
                self._columns_chars[c][mutate_idx] = random.choice(_MATRIX_GLYPHS)

            head_int = int(head_y)
            # Render trail upward from head
            for dist in range(trail_len):
                y = head_int - dist
                if 0 <= y < h:
                    glyph = self._columns_chars[c][(y + c) % len(self._columns_chars[c])]
                    if dist == 0:
                        # Bright leading spark
                        lines[y][c] = (glyph, style_lead)
                    elif dist < trail_len * 0.35:
                        lines[y][c] = (glyph, style_body)
                    elif dist < trail_len * 0.70:
                        lines[y][c] = (glyph, style_tail)
                    else:
                        lines[y][c] = (glyph, style_dim)

            # Ambient filler for completely empty cells so there is zero dead space
            for r in range(h):
                if lines[r][c][0] == " ":
                    if (r + c + int(idle_phase * 2)) % 11 == 0:
                        lines[r][c] = ("·", style_dim)

        text = Text()
        for r_idx, line in enumerate(lines):
            for char, st in line:
                text.append(char, style=st)
            if r_idx < h - 1:
                text.append("\n")

        return text


class LissajousHarmonicsEngine(BaseVisualizerEngine):
    """Stereo phosphor X-Y Lissajous orbital phase scope with harmonic persistence.

    Maps Left channel to X and Right channel to Y to render real-time
    stereo phase correlation, supplemented by orbital harmonic figure synthesis
    driven by spectral centroid and musical harmonic ratios (1:1, 1:2, 2:3, 3:4).
    """

    id = "lissajous_harmonics"
    name = "Lissajous Orbital Harmonics"
    category = "stereo_phase"
    icon = "⌖"
    description = "Stereo X-Y phosphor phase orbital scope with harmonic ratios and decaying persistence trails."
    min_width = 16
    min_height = 8

    def __init__(self) -> None:
        super().__init__()
        self._persistence: np.ndarray | None = None
        self._last_w: int = 0
        self._last_h: int = 0

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

        if self._persistence is None or w != self._last_w or h != self._last_h:
            self._persistence = np.zeros((h, w), dtype=np.float32)
            self._last_w = w
            self._last_h = h

        # Phosphor decay step (afterglow persistence)
        self._persistence *= 0.65

        # Determine harmonic orbital ratio from spectral centroid or idle phase
        if ctx.is_playing:
            ratio_idx = int(ctx.spectral_centroid / 800.0) % 4
            a_val, b_val = [(1.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0)][ratio_idx]
            delta = float(ctx.phase_corr * math.pi * 0.5)
            intensity_boost = 1.0 + float(np.mean(ctx.levels_128) * 1.5)
        else:
            a_val = 2.0
            b_val = 3.0
            delta = idle_phase * 0.8
            intensity_boost = 0.9

        # Generate parametric orbital curve points
        n_points = max(180, w * 4)
        theta = np.linspace(0, 4 * math.pi, n_points, dtype=np.float32)

        # Stereo wave modulation if active
        if ctx.is_playing and len(ctx.waveform_l) > 100:
            audio_x = np.interp(np.linspace(0, 1, n_points), np.linspace(0, 1, len(ctx.waveform_l)), ctx.waveform_l)
            audio_y = np.interp(np.linspace(0, 1, n_points), np.linspace(0, 1, len(ctx.waveform_r)), ctx.waveform_r)
            norm_x = 0.65 * np.sin(a_val * theta + delta) + 0.35 * audio_x
            norm_y = 0.65 * np.sin(b_val * theta) + 0.35 * audio_y
        else:
            norm_x = np.sin(a_val * theta + delta) * (0.82 + 0.12 * math.sin(idle_phase * 1.4))
            norm_y = np.sin(b_val * theta) * (0.82 + 0.12 * math.cos(idle_phase * 1.1))

        # Center coordinates
        center_x = (w - 1) / 2.0
        center_y = (h - 1) / 2.0
        radius_x = center_x * 0.88
        radius_y = center_y * 0.85

        px = np.clip(np.round(center_x + norm_x * radius_x), 0, w - 1).astype(int)
        py = np.clip(np.round(center_y - norm_y * radius_y), 0, h - 1).astype(int)

        # Deposit phosphor energy
        for x, y in zip(px, py, strict=False):
            self._persistence[y, x] = min(1.0, self._persistence[y, x] + 0.70 * intensity_boost)

        # Color and character styles
        style_bright = palette.accent_style(bold=True)
        style_primary = palette.primary_style()
        style_dim = palette.dim_style()
        style_scope = Style.parse(f"dim {palette.secondary}")

        text = Text()
        mid_row = h // 2
        mid_col = w // 2

        for y in range(h):
            for x in range(w):
                energy = float(self._persistence[y, x])

                if energy > 0.75:
                    text.append("█", style=style_bright)
                elif energy > 0.45:
                    text.append("▓", style=style_primary)
                elif energy > 0.20:
                    text.append("▒", style=style_primary)
                elif energy > 0.08:
                    text.append("░", style=style_dim)
                elif x == mid_col and y == mid_row:
                    text.append("┼", style=style_scope)
                elif x == mid_col:
                    text.append("│", style=style_dim)
                elif y == mid_row:
                    text.append("─", style=style_dim)
                elif (x - mid_col) ** 2 / max(1, radius_x**2) + (y - mid_row) ** 2 / max(1, radius_y**2) <= 1.05 and (
                    (x - mid_col) ** 2 / max(1, radius_x**2) + (y - mid_row) ** 2 / max(1, radius_y**2) >= 0.95
                ):
                    # Calibrated outer reticle circle ring
                    text.append("·", style=style_dim)
                else:
                    text.append(" ")
            if y < h - 1:
                text.append("\n")

        return text


class AudioFlameFireEngine(BaseVisualizerEngine):
    """Classic demoscene cellular campfire with bass-transient ember sparks.

    Cellular heat propagation algorithm where the bottom generation row is
    driven by audio frequency bins (sub-bass and bass ignite white-hot core
    embers, mids and highs create dancing flame tongues and spark crackles).
    """

    id = "audio_flame_fire"
    name = "Demoscene Audio Campfire"
    category = "particles_fluid"
    icon = "✦"
    description = "Cellular acoustic heat simulation with sub-bass ember sparks and rising flame tongues."
    min_width = 16
    min_height = 6

    def __init__(self) -> None:
        super().__init__()
        self._heat_map: np.ndarray | None = None
        self._last_w: int = 0
        self._last_h: int = 0

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

        if self._heat_map is None or w != self._last_w or h != self._last_h:
            self._heat_map = np.zeros((h, w), dtype=np.float32)
            self._last_w = w
            self._last_h = h

        # 1. Generate bottom ember coal layer driven by audio energy
        col_levels = np.interp(
            np.linspace(0, 1, w),
            np.linspace(0, 1, len(ctx.levels_128)),
            ctx.levels_128,
        ).astype(np.float32)

        is_active = ctx.is_active
        gen_row = h - 1

        for c in range(w):
            # Center weighting for natural campfire curve
            center_factor = 1.0 - (abs(c - (w / 2.0)) / (w / 2.0)) * 0.45
            if is_active:
                lvl = float(col_levels[c])
                val = (lvl * 240.0 * center_factor) + random.uniform(20.0, 50.0)
            else:
                # Standby ambient embers breathing
                idle_wave = 0.50 + 0.35 * math.sin(idle_phase * 2.0 + c * 0.3)
                val = (idle_wave * 190.0 * center_factor) + random.uniform(15.0, 35.0)

            # Seed bottom generator rows
            self._heat_map[gen_row, c] = float(np.clip(val, 0.0, 255.0))
            if h >= 2:
                self._heat_map[gen_row - 1, c] = float(np.clip(val * 0.88, 0.0, 255.0))

        # 2. Cellular heat propagation upward with smoothing and cooling
        # pixel(y, x) = avg(surrounding lower pixels) - cooling
        decay_base = 2.4 + (1.2 / max(1, h / 8.0))
        for y in range(max(0, h - 2)):
            src_y1 = y + 1
            src_y2 = min(h - 1, y + 2)
            for x in range(w):
                x_left = max(0, x - 1)
                x_right = min(w - 1, x + 1)

                h1 = self._heat_map[src_y1, x_left]
                h2 = self._heat_map[src_y1, x]
                h3 = self._heat_map[src_y1, x_right]
                h4 = self._heat_map[src_y2, x]

                avg_heat = (h1 + h2 + h3 + h4) * 0.248
                cooling = decay_base + random.uniform(-0.4, 0.8)
                self._heat_map[y, x] = max(0.0, avg_heat - cooling)

        # 3. Map heat values to ASCII / Unicode flame symbols and palette styles
        style_white = palette.accent_style(bold=True)  # White/yellow hot
        style_primary = palette.primary_style(bold=True)  # Bright orange/red
        style_sec = Style.parse(palette.secondary)         # Mid flame
        style_dim = palette.dim_style()                    # Smoke/cooling ember

        text = Text()
        for y in range(h):
            for x in range(w):
                heat = float(self._heat_map[y, x])
                if heat > 185.0:
                    text.append("█", style=style_white)
                elif heat > 140.0:
                    text.append("▓", style=style_white)
                elif heat > 95.0:
                    text.append("▒", style=style_primary)
                elif heat > 55.0:
                    text.append("▄", style=style_sec)
                elif heat > 25.0:
                    text.append("░", style=style_dim)
                elif heat > 10.0:
                    text.append("·", style=style_dim)
                else:
                    text.append(" ")
            if y < h - 1:
                text.append("\n")

        return text
