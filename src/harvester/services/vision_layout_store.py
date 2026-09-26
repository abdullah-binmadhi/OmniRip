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


# Factory Built-in Canvas Layouts
BUILTIN_LAYOUTS: List[VisionLayout] = [
    VisionLayout(
        layout_id="builtin_solo_stanford",
        name="Solo Stanford 3D Waterfall",
        description="Massive full-screen 3D landscape terrain visualizer with perspective rendering.",
        stitch_theme_id="tokyo_midnight",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=True, tall_two=True, order=0)
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="builtin_cyber_split",
        name="Dual Cyber Split",
        description="High-energy pairing of Stanford 3D wireframe mountains and Matrix digital rain.",
        stitch_theme_id="neon_cyber",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=True, order=1),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="builtin_studio_quad",
        name="Studio Quad Command",
        description="Balanced 4-way studio grid: 3D terrain, Matrix rain, Lissajous scope, and Audio flame.",
        stitch_theme_id="synthwave_dusk",
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
        layout_id="builtin_mastering_suite",
        name="Mastering Forensic Suite",
        description="6-engine precision audio telemetry and visualization dashboard.",
        stitch_theme_id="sunset_gold",
        gap_distance=1,
        cards=[
            VisionCardConfig(engine_id="p1_iso_octave_bars", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="p4_stereo_lissajous_circle", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="p1_analog_vu_needle", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="purple", span_two=True, tall_two=False, order=3),
            VisionCardConfig(engine_id="p8_crest_factor_radar", palette="green", span_two=False, tall_two=False, order=4),
        ],
        is_builtin=True,
    ),
]


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
