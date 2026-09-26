"""Persistent Layout Storage Service for Full Vision Canvas.

Allows users to design, save, load, and manage custom visualizer layouts
with custom engine combinations, palettes, sizing (span/tall), gap spacing,
and Stitch design themes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_LAYOUTS_DIR = Path.home() / ".config" / "omnirip" / "vision_layouts"


@dataclass
class VisionCardConfig:
    """Configuration for an individual visualizer card on the canvas."""

    engine_id: str
    palette: str = "cyan"
    span_two: bool = False
    tall_two: bool = False
    order: int = 0


@dataclass
class VisionLayout:
    """A full canvas layout blueprint containing multiple visual cards and layout styling."""

    layout_id: str
    name: str
    description: str = ""
    author: str = "OmniRip User"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    stitch_theme_id: str = "neon_cyber"
    gap_distance: int = 1
    cards: List[VisionCardConfig] = field(default_factory=list)
    is_builtin: bool = False


# 20 Curated Built-in Canvas Layout Presets
BUILTIN_LAYOUTS: List[VisionLayout] = [
    VisionLayout(
        layout_id="preset_cyberpunk_2077",
        name="Cyberpunk 2077 Quad Deck",
        description="High-energy 4-way studio: Stanford 3D terrain, Matrix code rain, Lissajous scope, and Audio flame.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_matrix_terminal",
        name="Matrix Green Phosphor Deck",
        description="Pure green digital rain stream and low-level hex memory telemetry cascade.",
        stitch_theme_id="matrix_terminal",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p5_hex_memory_dump", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p5_cyber_grid_cascade", palette="matrix", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_y2k_aesthetic",
        name="Y2K Chrome & Aqua Deck",
        description="Late-90s futurism with metallic chrome silver, bubblegum pink, and icy aqua orbitals.",
        stitch_theme_id="y2k_aesthetic",
        gap_distance=2,
        cards=[
            VisionCardConfig(engine_id="p7_hologram_pyramid", palette="cyan", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p7_3d_wireframe_hypercube", palette="neon", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p4_lissajous_3d_knot", palette="cyan", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_synthwave_dusk",
        name="Synthwave Dusk 1984",
        description="Neon purple grid mountains, sunset horizons, and retro CRT phosphor vectors.",
        stitch_theme_id="synthwave_dusk",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p3_wireframe_mountains", palette="sunset", span_two=True, tall_two=False, order=0),
            VisionCardConfig(engine_id="p2_crt_vector_glow", palette="crt", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p2_dual_beam_trace", palette="cyan", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_tokyo_midnight",
        name="Tokyo Midnight Phosphor",
        description="Deep navy blue, teal phosphor laser displays, and harmonic Lissajous scopes.",
        stitch_theme_id="tokyo_midnight",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=True, tall_two=False, order=0),
            VisionCardConfig(engine_id="p2_vector_laser_display", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_lofi_chill_vinyl",
        name="Lo-Fi Chill & Vinyl Lounge",
        description="Warm analog vacuum tubes, dancing analog VU needles, and tape-saturation bars.",
        stitch_theme_id="lofi_chill_vinyl",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p1_analog_vu_needle", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p1_iso_octave_bars", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p2_crt_vector_glow", palette="crt", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_deep_space",
        name="Deep Space Voyager",
        description="Cosmic emerald nebula glow with warp speed starfields and 3D terrain exploration.",
        stitch_theme_id="deep_space",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p6_warp_speed_starfield", palette="green", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p4_lissajous_3d_knot", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="green", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_arcade_8bit",
        name="8-Bit Arcade Demoscene",
        description="Chiptune waveforms, glowing pixel analyzer bars, and demoscene fire.",
        stitch_theme_id="arcade_8bit",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p1_iso_octave_bars", palette="neon", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p5_hex_memory_dump", palette="matrix", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_acid_rave",
        name="Acid Techno 303 Rave",
        description="High-voltage radioactive lime bass scope, strobe flash waterfalls, and plasma fountains.",
        stitch_theme_id="acid_rave",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="lissajous_harmonics", palette="neon", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p6_plasma_fountain", palette="matrix", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="green", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_sunset_gold",
        name="Sunset Gold Audiophile",
        description="Precision mastering telemetry: 1/3 octave ISO bars, stereo circle, and crest radar.",
        stitch_theme_id="sunset_gold",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p1_iso_octave_bars", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereo_lissajous_circle", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p1_analog_vu_needle", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="green", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_holographic_prism",
        name="Holographic Prism Array",
        description="Full-spectrum light refraction with 3D pyramids and stereoscopic phase rings.",
        stitch_theme_id="holographic_prism",
        gap_distance=2,
        cards=[
            VisionCardConfig(engine_id="p7_hologram_pyramid", palette="cyan", span_two=True, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereoscopic_phase_ring", palette="neon", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p7_3d_wireframe_hypercube", palette="cyan", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_industrial_metal",
        name="Industrial Heavy Metal",
        description="Scorched rust and carbon steel with heavy RMS impact meters and fire cascades.",
        stitch_theme_id="industrial_metal",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="audio_flame_fire", palette="thermal", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="thermal", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p3_wireframe_mountains", palette="thermal", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_vaporwave_mallsoft",
        name="Vaporwave Mallsoft Plaza",
        description="Pastel pink and mint green marble wireframes with ambient plasma drift.",
        stitch_theme_id="vaporwave_mallsoft",
        gap_distance=2,
        cards=[
            VisionCardConfig(engine_id="p3_wireframe_mountains", palette="sunset", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereo_lissajous_circle", palette="neon", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p6_plasma_fountain", palette="sunset", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_ccrma_stanford",
        name="CCRMA Stanford Sound Lab (Solo 3D)",
        description="Massive full-screen 3D landscape waterfall terrain in vintage laboratory amber.",
        stitch_theme_id="ccrma_stanford",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="amber", span_two=True, tall_two=True, order=0)
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_glitchcore_chaos",
        name="Glitchcore Chaos Rig",
        description="Distorted magenta and toxic green bitcrusher noise telemetry.",
        stitch_theme_id="glitchcore_chaos",
        gap_distance=0,
        cards=[
            VisionCardConfig(engine_id="p5_hex_memory_dump", palette="neon", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_biohazard_deck",
        name="Biohazard Cyberdeck",
        description="Nuclear radiation warning telemetry, Geiger radar, and toxic plasma fountains.",
        stitch_theme_id="biohazard_deck",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="green", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p6_plasma_fountain", palette="matrix", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_golden_era",
        name="Golden Era Audiophile Suite",
        description="Luxury 24k gold audiophile mastering telemetry with twin analog needles and 3D terrain.",
        stitch_theme_id="golden_era",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p1_analog_vu_needle", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereo_lissajous_circle", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="amber", span_two=True, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_minimalist_bauhaus",
        name="Minimalist Bauhaus Triad",
        description="Stark architectural balance: pure white, deep slate grey, and bold crimson telemetry.",
        stitch_theme_id="minimalist_bauhaus",
        gap_distance=2,
        cards=[
            VisionCardConfig(engine_id="p1_iso_octave_bars", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereo_lissajous_circle", palette="crt", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="cyan", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_solar_flare",
        name="Solar Flare Thermonuclear",
        description="Blazing solar wind plasma fountains, audio fire, and thermonuclear landscape wireframes.",
        stitch_theme_id="solar_flare",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p6_plasma_fountain", palette="thermal", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p3_wireframe_mountains", palette="sunset", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="preset_quantum_void",
        name="Quantum Superposition",
        description="Deep quantum void violet, 3D hypercubes, and probabilistic wavefunction phase knots.",
        stitch_theme_id="quantum_void",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p4_lissajous_3d_knot", palette="purple", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="p7_3d_wireframe_hypercube", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=False, tall_two=False, order=2),
        ],
        is_builtin=True,
    ),
]

# Aliases for backwards compatibility
BUILTIN_LAYOUTS_BY_ID = {ly.layout_id: ly for ly in BUILTIN_LAYOUTS}
BUILTIN_LAYOUTS.append(
    VisionLayout(
        layout_id="builtin_solo_stanford",
        name="Solo Stanford 3D Waterfall",
        description="Massive full-screen 3D landscape terrain visualizer with perspective rendering.",
        stitch_theme_id="ccrma_stanford",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="amber", span_two=True, tall_two=True, order=0)
        ],
        is_builtin=True,
    )
)


class VisionLayoutStore:
    """Manages persistent saving, loading, listing, and deletion of custom visual layouts."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir or DEFAULT_LAYOUTS_DIR)
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create vision layout directory %s: %s", self.storage_dir, exc)

    def _slugify(self, text: str) -> str:
        s = text.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_-]+", "_", s)
        return s or "layout"

    def list_layouts(self) -> List[VisionLayout]:
        """Return all available layouts (built-ins followed by saved user layouts)."""
        layouts = list(BUILTIN_LAYOUTS)

        if not self.storage_dir.exists():
            return layouts

        for file_path in sorted(self.storage_dir.glob("*.json")):
            try:
                layout = self.load_layout_from_file(file_path)
                if layout:
                    layouts.append(layout)
            except Exception as exc:
                logger.warning("Failed to load layout from %s: %s", file_path, exc)

        return layouts

    def load_layout_from_file(self, file_path: Path) -> Optional[VisionLayout]:
        """Load a VisionLayout from a specific JSON file."""
        if not file_path.is_file():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cards = [
            VisionCardConfig(
                engine_id=c.get("engine_id", "stanford_sun_music_3d"),
                palette=c.get("palette", "cyan"),
                span_two=c.get("span_two", False),
                tall_two=c.get("tall_two", False),
                order=c.get("order", idx),
            )
            for idx, c in enumerate(data.get("cards", []))
        ]

        return VisionLayout(
            layout_id=data.get("layout_id", file_path.stem),
            name=data.get("name", file_path.stem.replace("_", " ").title()),
            description=data.get("description", ""),
            author=data.get("author", "OmniRip User"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            stitch_theme_id=data.get("stitch_theme_id", "neon_cyber"),
            gap_distance=int(data.get("gap_distance", 1)),
            cards=cards,
            is_builtin=False,
        )

    def get_layout(self, layout_id: str) -> Optional[VisionLayout]:
        """Get a layout by ID (checking built-in layouts first, then user files)."""
        for builtin in BUILTIN_LAYOUTS:
            if builtin.layout_id == layout_id:
                return builtin

        target_file = self.storage_dir / f"{layout_id}.json"
        if target_file.exists():
            return self.load_layout_from_file(target_file)

        return None

    def save_layout(self, layout: VisionLayout) -> Path:
        """Save a user layout to disk."""
        self._ensure_storage_dir()
        if not layout.layout_id or layout.layout_id.startswith("builtin_"):
            layout.layout_id = f"custom_{self._slugify(layout.name)}_{int(datetime.now().timestamp())}"

        target_file = self.storage_dir / f"{layout.layout_id}.json"
        layout_dict = asdict(layout)
        layout_dict["is_builtin"] = False

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(layout_dict, f, indent=2)

        logger.info("Saved visual layout %s to %s", layout.name, target_file)
        return target_file

    def delete_layout(self, layout_id: str) -> bool:
        """Delete a custom layout file (cannot delete built-ins)."""
        if layout_id.startswith("builtin_"):
            return False

        target_file = self.storage_dir / f"{layout_id}.json"
        if target_file.exists():
            target_file.unlink()
            return True
        return False
