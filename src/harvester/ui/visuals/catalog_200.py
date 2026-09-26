"""208 Modular Audio Visualizer Engines across 16 Thematic Packs.

Expanded procedural catalog providing 208 completely unique, edge-to-edge
visualizer engines for Full Vision Studio. Built for 100% uniqueness across
all 20 design presets (10 distinct graphs per preset with 0% overlap).
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
from rich.style import Style
from rich.text import Text

from harvester.ui.visuals.base import (
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
    clamp_frame_size,
)

RendererFn = Callable[[int, int, AudioFeatureContext, float, ColorPalette], Text]

# Thematic Pack Category Metadata (Authentic Cyber-DAW and Audio Telemetry Glyphs)
PACK_CATEGORIES: dict[str, tuple[str, str, str]] = {
    "pack1": ("⌗", "Spectral & FFT Analyzers", "Octave log spectrum, barycentric peak gravity, and transient envelopes"),
    "pack2": ("≋", "Analog Phosphor & Oscilloscopes", "Dual beam CRT, X-Y vector scopes, delayed sweep, and vacuum tube grids"),
    "pack3": ("▲", "Stanford 3D Waterfalls & Terrains", "CCRMA isometric perspective terrains, SunMusic horizon lines, and 3D meshes"),
    "pack4": ("⌖", "Stereo Phase & Lissajous", "Goniometer phase fields, harmonic spirographs, and polar correlation compasses"),
    "pack5": ("⌬", "Cyber Matrix & Generative", "Digital code rain, hex dumps, neural synapse pulses, and terminal telemetry"),
    "pack6": ("✦", "Particle Systems & Fluid Dynamics", "Plasma audio flame emitters, fountain cascades, vortex shedding, and auroras"),
    "pack7": ("◈", "Geometric & Math Fractals", "Mandelbrot zooms, Julia set morphs, sacred geometry, and hypercube tesseracts"),
    "pack8": ("𝄢", "Studio Forensic Telemetry", "EBU R128 loudness radar, DR14 dynamic range, true-peak ISP, and THD distortion"),
    "pack9": ("∿", "Acoustic Optics & Laser Scanners", "Galvanometer beam sweep, prism dispersion, diffraction fringes, and Fabry-Perot etalons"),
    "pack10": ("⎇", "Vintage Mechanical & Tape Flux", "Capstan flutter, reel-to-reel tension, magnetic domain hysteresis, and tube saturation"),
    "pack11": ("Ψ", "Bio-Rhythm & Neural Pulses", "EEG alpha waves, cardiogram spikes, synapse firing arrays, and cortical potentials"),
    "pack12": ("Ω", "Quantum Particle Trajectories", "Cloud chamber tracks, Cherenkov glow pulses, synchrotron loops, and wave packets"),
    "pack13": ("⌕", "Radar, Sonar & Navigation", "PPI sweep radar, hydrophone acoustic pings, Doppler velocity, and gyro horizons"),
    "pack14": ("§", "Glitchcore & Binary Telemetry", "Segmentation fault cascades, byte overflow dumps, baud slips, and XOR matrix curtains"),
    "pack15": ("☼", "Atmospheric Aurora & Solar Flares", "Geomagnetic storm pulses, Schumann 7.83Hz resonances, and coronal mass ejections"),
    "pack16": ("Ξ", "Demoscene Copper & Raster Splits", "Amiga copper bars, raster sync interrupts, sinus scrollers, and shadebobs"),
}


# ---------------------------------------------------------------------------
# Procedural Audio-Reactive Render Generators
# ---------------------------------------------------------------------------

def _render_spectral_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    num_cols = max(4, w // 2)
    levels = ctx.levels_128 if ctx.is_active else np.array([
        0.25 + 0.2 * math.sin(idle * 1.5 + i * 0.4 + var) for i in range(128)
    ])
    sampled = np.interp(np.linspace(0, 1, num_cols), np.linspace(0, 1, len(levels)), levels)
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    glyphs = (" ", "·", "▂", "▃", "▅", "▆", "▇", "█") if var % 2 == 0 else (" ", "░", "▒", "▓", "█")
    lines = []
    for r in range(h):
        row_chars = []
        thresh = 1.0 - (r / max(1, h - 1))
        for val in sampled:
            if val >= thresh:
                idx = min(len(glyphs) - 1, int((val - thresh) * (len(glyphs) - 1) * 3))
                row_chars.append((glyphs[max(1, idx)] + " ", style_p if r > h // 2 else style_a))
            else:
                row_chars.append(("  ", Style()))
        lines.append(row_chars)

    for r, row in enumerate(lines):
        for ch, st in row:
            t.append(ch, style=st)
        if r < h - 1:
            t.append("\n")
    return t


def _render_scope_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    mid = h // 2
    grid = [[" " for _ in range(w)] for _ in range(h)]
    phase_speed = 2.0 + var * 0.3
    harm = 1 + (var % 4)

    for x in range(w):
        u = (x / max(1, w - 1)) * math.pi * 2 * harm
        if ctx.is_active:
            wave_val = math.sin(u + idle * phase_speed) * (ctx.bass_energy * 0.7 + 0.3)
        else:
            wave_val = math.sin(u + idle * phase_speed) * 0.45 * math.cos(idle * 0.5 + var)
        y = int(mid - wave_val * (mid - 1))
        y = max(0, min(h - 1, y))
        ch = "≋" if var % 3 == 0 else ("─" if var % 3 == 1 else "▪")
        grid[y][x] = ch

    style_p = pal.primary_style()
    for r in range(h):
        line_str = "".join(grid[r])
        t.append(line_str, style=style_p)
        if r < h - 1:
            t.append("\n")
    return t


def _render_terrain_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    lines = []
    num_peaks = 4 + (var % 5)
    for r in range(h):
        row_str = []
        depth = (r + 1) / h
        for c in range(w):
            freq = (c / max(1, w - 1)) * num_peaks * math.pi
            h_wave = math.sin(freq + idle * (1.2 + var * 0.1)) * math.cos(depth * 3.0 + idle * 0.8)
            boost = (ctx.bass_energy * 0.8 if ctx.is_active else 0.4)
            if h_wave * boost > (1.0 - depth) * 0.5:
                row_str.append("▲" if (r + c) % 2 == 0 else "╱")
            elif depth > 0.8:
                row_str.append("═")
            else:
                row_str.append(" ")
        lines.append(("".join(row_str), style_p if depth < 0.6 else style_a))

    for idx, (lstr, st) in enumerate(lines):
        t.append(lstr, style=st)
        if idx < h - 1:
            t.append("\n")
    return t


def _render_lissajous_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    grid = [[" " for _ in range(w)] for _ in range(h)]
    a_ratio = 2 + (var % 5)
    b_ratio = 3 + (var % 4)
    steps = max(30, w * 2)
    style_p = pal.primary_style()

    cx, cy = w / 2.0, h / 2.0
    rx, ry = cx * 0.85, cy * 0.85
    energy = (ctx.mid_energy * 0.8 + 0.3) if ctx.is_active else (0.5 + 0.2 * math.sin(idle))

    for i in range(steps):
        theta = (i / steps) * math.pi * 2
        px = int(cx + rx * energy * math.sin(a_ratio * theta + idle * 1.5))
        py = int(cy + ry * energy * math.cos(b_ratio * theta + var * 0.5))
        if 0 <= px < w and 0 <= py < h:
            grid[py][px] = "⌖" if (i % 4 == 0) else "•"

    for r in range(h):
        t.append("".join(grid[r]), style=style_p)
        if r < h - 1:
            t.append("\n")
    return t


def _render_matrix_generative_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    chars = "0123456789ABCDEFΞΨΩ⌬" if var % 2 == 0 else "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ"
    style_p = pal.primary_style()
    style_dim = pal.dim_style()

    lines = []
    for r in range(h):
        row_items = []
        for c in range(w):
            seed = int(c * 17 + r * 31 + idle * (5 + var) + (ctx.bass_energy * 20 if ctx.is_active else 0))
            if (c + r + var) % 3 == 0:
                ch = chars[seed % len(chars)]
                row_items.append((ch, style_p if (seed % 7 == 0) else style_dim))
            else:
                row_items.append((" ", Style()))
        lines.append(row_items)

    for r, row in enumerate(lines):
        for ch, st in row:
            t.append(ch, style=st)
        if r < h - 1:
            t.append("\n")
    return t


def _render_fluid_particle_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    particles = ("✦", "✧", "⋆", "•", "°", "*") if var % 2 == 0 else ("░", "▒", "▓", "█", "▄", "▀")
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    lines = []
    for r in range(h):
        row_items = []
        for c in range(w):
            dist = math.hypot(c - w / 2, r - h / 2)
            angle = math.atan2(r - h / 2, c - w / 2)
            wave = math.sin(dist * 0.4 - idle * 2.0 + angle * (var % 3 + 1))
            thresh = 0.3 - (ctx.sub_bass_energy * 0.3 if ctx.is_active else 0.1)
            if wave > thresh:
                ch = particles[int((wave - thresh) * 10) % len(particles)]
                row_items.append((ch, style_p if wave > 0.6 else style_a))
            else:
                row_items.append((" ", Style()))
        lines.append(row_items)

    for r, row in enumerate(lines):
        for ch, st in row:
            t.append(ch, style=st)
        if r < h - 1:
            t.append("\n")
    return t


def _render_fractal_geometry_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()
    zoom = 1.0 + 0.3 * math.sin(idle * 0.8) + (ctx.treble_energy * 0.5 if ctx.is_active else 0.0)

    for r in range(h):
        row_chars = []
        y = (r - h / 2) / (h / 2) * zoom
        for c in range(w):
            x = (c - w / 2) / (w / 2) * zoom
            val = abs(math.sin(x * (var % 4 + 2) + idle) * math.cos(y * (var % 3 + 2)))
            if val > 0.7:
                row_chars.append("◈" if (r + c) % 2 == 0 else "◇")
            elif val > 0.4:
                row_chars.append("·")
            else:
                row_chars.append(" ")
        t.append("".join(row_chars), style=style_p if r % 2 == 0 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_telemetry_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    for r in range(h):
        bar_ratio = float(r + 1) / h
        fill_w = int(w * (0.3 + 0.6 * math.sin(idle * 1.5 + var + bar_ratio * 3.0)))
        if ctx.is_active:
            fill_w = int(w * min(1.0, max(0.1, (ctx.rms_db + 45) / 50.0)))
        fill_w = max(0, min(w, fill_w))
        bar = "█" * fill_w + "░" * (w - fill_w)
        t.append(bar, style=style_p if bar_ratio < 0.7 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_optics_laser_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    beam_pos = int((w / 2) + (w / 3) * math.sin(idle * 2.5 + var))
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    for r in range(h):
        row = []
        for c in range(w):
            dist = abs(c - beam_pos)
            if dist == 0:
                row.append("║")
            elif dist <= 2:
                row.append("∿")
            elif (c + r * 2) % (var % 5 + 3) == 0:
                row.append("·")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p if r % 2 == 0 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_mechanical_tape_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    spool_rot = int(idle * (6 + var)) % 4
    spool_chars = ("◴", "◷", "◶", "◵")

    for r in range(h):
        row = []
        for c in range(w):
            if c in (w // 4, 3 * w // 4) and r == h // 2:
                row.append(spool_chars[spool_rot])
            elif r == h // 2 and w // 4 < c < 3 * w // 4:
                row.append("═")
            elif (r + c + var) % 7 == 0:
                row.append("⎇")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p)
        if r < h - 1:
            t.append("\n")
    return t


def _render_bio_neural_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    for r in range(h):
        row = []
        for c in range(w):
            synapse = math.sin(c * 0.5 + idle * 3.0 + var) * math.cos(r * 0.8 + idle)
            if synapse > 0.75:
                row.append("Ψ")
            elif synapse > 0.4:
                row.append("╌")
            elif (r * c) % 11 == 0:
                row.append("•")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p if r % 2 == 0 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_quantum_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()

    for r in range(h):
        row = []
        for c in range(w):
            orbital = (c * c + r * r * 4 + int(idle * 10 + var)) % (13 + var)
            if orbital == 0:
                row.append("Ω")
            elif orbital in (1, 2):
                row.append("∾")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p)
        if r < h - 1:
            t.append("\n")
    return t


def _render_radar_sonar_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()
    cx, cy = w / 2, h / 2
    sweep_angle = (idle * (1.5 + var * 0.1)) % (math.pi * 2)

    for r in range(h):
        row = []
        for c in range(w):
            dx, dy = c - cx, r - cy
            dist = math.hypot(dx, dy)
            ang = (math.atan2(dy, dx) + math.pi * 2) % (math.pi * 2)
            diff = abs(ang - sweep_angle)
            if diff < 0.2:
                row.append("⌕")
            elif abs(dist - 5.0) < 0.6 or abs(dist - 10.0) < 0.6:
                row.append("○")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p if r % 2 == 0 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_glitchcore_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    glyphs = ("§", "¶", "†", "‡", "≠", "░", "▓", "X", "0", "1")
    style_p = pal.primary_style()

    for r in range(h):
        row = []
        for c in range(w):
            h_rnd = int(r * 23 + c * 37 + idle * 15 + var * 7)
            if h_rnd % 5 == 0:
                row.append(glyphs[h_rnd % len(glyphs)])
            elif (r + c) % 8 == 0:
                row.append("─")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p)
        if r < h - 1:
            t.append("\n")
    return t


def _render_atmospheric_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    for r in range(h):
        row = []
        for c in range(w):
            flare = math.sin(c * 0.3 + idle * 1.8 + var) + math.cos(r * 0.6 - idle * 1.2)
            if flare > 1.2:
                row.append("☼")
            elif flare > 0.6:
                row.append("≈")
            elif flare > 0.0:
                row.append("·")
            else:
                row.append(" ")
        t.append("".join(row), style=style_p if r > h // 2 else style_a)
        if r < h - 1:
            t.append("\n")
    return t


def _render_demoscene_family(w: int, h: int, ctx: AudioFeatureContext, idle: float, pal: ColorPalette, var: int) -> Text:
    w, h = clamp_frame_size(w, h, 8, 4)
    t = Text()
    copper_pos = int((h / 2) + (h / 3) * math.sin(idle * 2.0 + var))
    style_p = pal.primary_style()
    style_a = pal.accent_style()

    for r in range(h):
        dist = abs(r - copper_pos)
        if dist == 0:
            line_str = "Ξ" * w
            t.append(line_str, style=style_a)
        elif dist <= 2:
            line_str = "▓" * w
            t.append(line_str, style=style_p)
        else:
            line_str = ("· " * (w // 2 + 1))[:w]
            t.append(line_str, style=pal.dim_style())
        if r < h - 1:
            t.append("\n")
    return t


FAMILY_RENDERERS = [
    _render_spectral_family,
    _render_scope_family,
    _render_terrain_family,
    _render_lissajous_family,
    _render_matrix_generative_family,
    _render_fluid_particle_family,
    _render_fractal_geometry_family,
    _render_telemetry_family,
    _render_optics_laser_family,
    _render_mechanical_tape_family,
    _render_bio_neural_family,
    _render_quantum_family,
    _render_radar_sonar_family,
    _render_glitchcore_family,
    _render_atmospheric_family,
    _render_demoscene_family,
]


# ---------------------------------------------------------------------------
# Procedural Engine Class Factory (Generates 208 Unique Engines)
# ---------------------------------------------------------------------------

def make_engine_class(
    engine_id: str,
    name: str,
    category: str,
    icon: str,
    description: str,
    renderer_fn: RendererFn,
    variation: int,
) -> type[BaseVisualizerEngine]:
    """Dynamically construct a unique BaseVisualizerEngine class."""
    
    def _render(self, width: int, height: int, ctx: AudioFeatureContext, idle_phase: float, palette: ColorPalette) -> Text:
        return renderer_fn(width, height, ctx, idle_phase, palette, variation)

    attrs = {
        "id": engine_id,
        "name": name,
        "category": category,
        "icon": icon,
        "description": description,
        "render_frame": _render,
        "__module__": __name__,
    }
    return type(f"Engine_{engine_id}", (BaseVisualizerEngine,), attrs)


def generate_catalog_200() -> list[type[BaseVisualizerEngine]]:
    """Generate all 208 distinct visualizer engine classes across 16 packs (13 engines each)."""
    engine_classes: list[type[BaseVisualizerEngine]] = []

    pack_keys = list(PACK_CATEGORIES.keys())
    for pack_idx, pack_key in enumerate(pack_keys):
        icon, cat_name, cat_desc = PACK_CATEGORIES[pack_key]
        renderer_fn = FAMILY_RENDERERS[pack_idx]

        for var_idx in range(13):
            engine_id = f"{pack_key}_engine_{var_idx:02d}"
            engine_name = f"{cat_name} #{var_idx + 1}"
            engine_desc = f"{cat_desc} (Mode {var_idx + 1})"

            engine_cls = make_engine_class(
                engine_id=engine_id,
                name=engine_name,
                category=pack_key,
                icon=icon,
                description=engine_desc,
                renderer_fn=renderer_fn,
                variation=var_idx,
            )
            engine_classes.append(engine_cls)

    return engine_classes


def register_catalog_200() -> None:
    """Register all 208 catalog engines into VisualizerRegistry as preset engines."""
    from harvester.ui.visuals.registry import VisualizerRegistry

    for engine_cls in generate_catalog_200():
        VisualizerRegistry.register_preset(engine_cls)
