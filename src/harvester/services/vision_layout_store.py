"""Full Vision Layout Store and Persistence Engine.

Manages preset and user-saved visualizer card layouts, theme associations,
and dynamic canvas configurations.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VisionCardConfig:
    engine_id: str
    palette: str = "cyan"
    span_two: bool = False
    tall_two: bool = False
    order: int = 0


@dataclass
class VisionLayout:
    layout_id: str
    name: str
    description: str
    stitch_theme_id: str
    gap_distance: int = 1
    ui_structure_style: str = "default_cards"  # cyberdeck_terminal, dos_mpxplay, hyprland_rice, lofi_cafe, demoscene_split, modern_minimal
    button_style_mode: str = "cyber_brackets"  # cyber_brackets, dos_keys, hyprland_pills, cozy_soft, minimal_clean
    anime_character_id: str = "default"
    cards: List[VisionCardConfig] = field(default_factory=list)
    is_builtin: bool = False


# Built-in quickstart starter templates
BUILTIN_STARTER_LAYOUTS: List[VisionLayout] = [
    VisionLayout(
        layout_id="builtin_solo_stanford",
        name="Solo Stanford 3D Waterfall",
        description="Massive full-screen 3D landscape waterfall visualizer.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_cyberpunk_2077",
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=True, tall_two=True, order=0),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="builtin_dual_cyber",
        name="Dual Cyber Deck (Rain & Phase)",
        description="Split-screen Matrix digital code stream and Lissajous phosphor scope.",
        stitch_theme_id="matrix_terminal",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_matrix_terminal",
        cards=[
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=True, order=0),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=False, tall_two=True, order=1),
        ],
        is_builtin=True,
    ),
    VisionLayout(
        layout_id="builtin_quad_matrix",
        name="Quad Studio Master Deck",
        description="4-way telemetry: Stanford 3D, Matrix Rain, Lissajous Scope, and Audio Flame.",
        stitch_theme_id="synthwave_dusk",
        gap_distance=1,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_y2k_aesthetic",
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
]


# ---------------------------------------------------------------------------
# 20 Distinct Thematic Presets (Each with 10 Completely Unique Engines, 0% Overlap)
# ---------------------------------------------------------------------------

PRESET_LAYOUTS: List[VisionLayout] = [
    # 1. Y2K Aesthetic (Pack 9: 0-9)
    VisionLayout(
        layout_id="preset_y2k_aesthetic",
        name="Y2K Chrome & Aqua Deck",
        description="Late-90s cyber-pop futurism with translucent visor, CD laser diffraction, and optical prism arrays.",
        stitch_theme_id="y2k_aesthetic",
        gap_distance=2,
        ui_structure_style="y2k_cyber",
        button_style_mode="pill",
        anime_character_id="preset_y2k_aesthetic",
        cards=[
            VisionCardConfig(engine_id=f"pack9_engine_{i:02d}", palette="cyan" if i % 2 == 0 else "magenta", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 2. Cyberpunk 2077 (4 Headline + Pack 5: 0-5)
    VisionLayout(
        layout_id="preset_cyberpunk_2077",
        name="Cyberpunk 2077 Quad Deck",
        description="High-energy Night City netrunning: Stanford 3D terrain, Matrix rain, Lissajous scope, Audio flame & cyber nodes.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_cyberpunk_2077",
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", order=2),
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", order=3),
            VisionCardConfig(engine_id="pack5_engine_00", palette="neon", order=4),
            VisionCardConfig(engine_id="pack5_engine_01", palette="cyan", order=5),
            VisionCardConfig(engine_id="pack5_engine_02", palette="purple", order=6),
            VisionCardConfig(engine_id="pack5_engine_03", palette="amber", order=7),
            VisionCardConfig(engine_id="pack5_engine_04", palette="neon", order=8),
            VisionCardConfig(engine_id="pack5_engine_05", palette="cyan", order=9),
        ],
        is_builtin=True,
    ),

    # 3. Matrix Terminal (Pack 5: 6-12 + Pack 8: 0-2)
    VisionLayout(
        layout_id="preset_matrix_terminal",
        name="Matrix Green Phosphor Deck",
        description="Pure green digital rain stream, low-level hex memory dump, and terminal telemetry cursor.",
        stitch_theme_id="matrix_terminal",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_matrix_terminal",
        cards=[
            VisionCardConfig(engine_id=f"pack5_engine_{i:02d}", palette="green", order=i - 6) for i in range(6, 13)
        ] + [
            VisionCardConfig(engine_id=f"pack8_engine_{i:02d}", palette="green", order=7 + i) for i in range(3)
        ],
        is_builtin=True,
    ),

    # 4. Lo-Fi Chill (Pack 10: 0-9)
    VisionLayout(
        layout_id="preset_lofi_chill",
        name="Lo-Fi Chill & Study Desk",
        description="Cozy fleece hoodie, matcha mug, vintage vacuum tubes, and tape saturation glow.",
        stitch_theme_id="lofi_chill_vinyl",
        gap_distance=1,
        ui_structure_style="lofi_cafe",
        button_style_mode="cozy_soft",
        anime_character_id="preset_lofi_chill",
        cards=[
            VisionCardConfig(engine_id=f"pack10_engine_{i:02d}", palette="amber" if i % 2 == 0 else "crt", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 5. Tokyo Night (Pack 9: 10-12 + Pack 2: 0-6)
    VisionLayout(
        layout_id="preset_tokyo_night",
        name="Tokyo Midnight Neon Deck",
        description="Shibuya crossing rain puddles, neon kanji reflections, and night drive synthesizer scopes.",
        stitch_theme_id="tokyo_night_shibuya",
        gap_distance=1,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_tokyo_night",
        cards=[
            VisionCardConfig(engine_id=f"pack9_engine_{i:02d}", palette="neon", order=i - 10) for i in range(10, 13)
        ] + [
            VisionCardConfig(engine_id=f"pack2_engine_{i:02d}", palette="cyan" if i % 2 == 0 else "purple", order=3 + i) for i in range(7)
        ],
        is_builtin=True,
    ),

    # 6. Retrowave Sunset (Pack 2: 7-12 + Pack 15: 0-3)
    VisionLayout(
        layout_id="preset_retrowave_sunset",
        name="Outrun Synthwave Sunset",
        description="1984 Miami horizon, neon wireframe palm trees, and chrome cassette deck.",
        stitch_theme_id="synthwave_dusk",
        gap_distance=1,
        ui_structure_style="modern_minimal",
        button_style_mode="minimal_clean",
        anime_character_id="preset_retrowave_sunset",
        cards=[
            VisionCardConfig(engine_id=f"pack2_engine_{i:02d}", palette="magenta", order=i - 7) for i in range(7, 13)
        ] + [
            VisionCardConfig(engine_id=f"pack15_engine_{i:02d}", palette="amber", order=6 + i) for i in range(4)
        ],
        is_builtin=True,
    ),

    # 7. Industrial Decay (Pack 14: 0-9)
    VisionLayout(
        layout_id="preset_industrial_decay",
        name="Industrial Wasteland Terminal",
        description="Rust, concrete, heavy bass sub-oscillators, and harsh telemetry distortion.",
        stitch_theme_id="industrial_decay",
        gap_distance=0,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_industrial_decay",
        cards=[
            VisionCardConfig(engine_id=f"pack14_engine_{i:02d}", palette="amber" if i % 2 == 0 else "crt", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 8. Deep Ocean (Pack 13: 0-9)
    VisionLayout(
        layout_id="preset_deep_ocean",
        name="Abyssal Sub-Bass Trench",
        description="Submarine sonar ping, bioluminescent jellyfish trails, and deep water pressure hydrophones.",
        stitch_theme_id="deep_ocean_abyss",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_deep_ocean",
        cards=[
            VisionCardConfig(engine_id=f"pack13_engine_{i:02d}", palette="cyan" if i % 2 == 0 else "green", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 9. Solar Flare (Pack 15: 4-12 + Mirrored Dance)
    VisionLayout(
        layout_id="preset_solar_flare",
        name="Solar Flare Thermonuclear Deck",
        description="Thermonuclear coronal loops, radioactive plasma fire, and high-frequency solar flares.",
        stitch_theme_id="solar_flare_plasma",
        gap_distance=1,
        ui_structure_style="demoscene_split",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_solar_flare",
        cards=[
            VisionCardConfig(engine_id=f"pack15_engine_{i:02d}", palette="amber", order=i - 4) for i in range(4, 13)
        ] + [
            VisionCardConfig(engine_id="mirrored_dance", palette="magenta", order=9)
        ],
        is_builtin=True,
    ),

    # 10. Acid Techno (Pack 1: 0-9)
    VisionLayout(
        layout_id="preset_acid_techno",
        name="Acid Techno 303 Lab",
        description="Roland TB-303 square wave resonance, distortion pedal harmonics, and hypnotic rave strobe.",
        stitch_theme_id="acid_techno_303",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_acid_techno",
        cards=[
            VisionCardConfig(engine_id=f"pack1_engine_{i:02d}", palette="green" if i % 2 == 0 else "neon", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 11. Vaporwave Mall (Pack 7: 0-9)
    VisionLayout(
        layout_id="preset_vaporwave_mall",
        name="Vaporwave Plaza Aesthetic",
        description="Pastel marble columns, Arizona green tea cans, Windows 95 icons, and slowed vinyl reverbs.",
        stitch_theme_id="vaporwave_aesthetic",
        gap_distance=2,
        ui_structure_style="modern_minimal",
        button_style_mode="pill",
        anime_character_id="preset_vaporwave_mall",
        cards=[
            VisionCardConfig(engine_id=f"pack7_engine_{i:02d}", palette="magenta" if i % 2 == 0 else "cyan", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 12. Dungeon Synth (Pack 16: 0-9)
    VisionLayout(
        layout_id="preset_dungeon_synth",
        name="Dungeon Synth Crypt Vault",
        description="Medieval stone crypts, flickering iron torches, forgotten fantasy runes, and ancient tape hiss.",
        stitch_theme_id="dungeon_synth_crypt",
        gap_distance=1,
        ui_structure_style="demoscene_split",
        button_style_mode="dos_keys",
        anime_character_id="preset_dungeon_synth",
        cards=[
            VisionCardConfig(engine_id=f"pack16_engine_{i:02d}", palette="amber" if i % 2 == 0 else "crt", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 13. Chiptune Gameboy (Pack 16: 10-12 + Pack 14: 10-12 + 4 Headline)
    VisionLayout(
        layout_id="preset_chiptune_gameboy",
        name="Game Boy 8-Bit Pixel Studio",
        description="Nintendo DMG-01 green LCD, pulse wave square channels, noise sweeps, and pixel sprite bursts.",
        stitch_theme_id="chiptune_gameboy_dmg",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_chiptune_gameboy",
        cards=[
            VisionCardConfig(engine_id="pack16_engine_10", palette="green", order=0),
            VisionCardConfig(engine_id="pack16_engine_11", palette="green", order=1),
            VisionCardConfig(engine_id="pack16_engine_12", palette="green", order=2),
            VisionCardConfig(engine_id="pack14_engine_10", palette="green", order=3),
            VisionCardConfig(engine_id="pack14_engine_11", palette="green", order=4),
            VisionCardConfig(engine_id="pack14_engine_12", palette="green", order=5),
            VisionCardConfig(engine_id="phosphor_crt_wave", palette="green", order=6),
            VisionCardConfig(engine_id="spectrum_10band", palette="green", order=7),
            VisionCardConfig(engine_id="braille_smooth_wave", palette="green", order=8),
            VisionCardConfig(engine_id="stereo_vu_deck", palette="green", order=9),
        ],
        is_builtin=True,
    ),

    # 14. Nordic Aurora (Pack 6: 0-9)
    VisionLayout(
        layout_id="preset_nordic_aurora",
        name="Nordic Fjord Borealis Array",
        description="Glacial ice silence, green and violet curtains of northern lights, and gentle sub-bass drift.",
        stitch_theme_id="nordic_aurora_fjord",
        gap_distance=1,
        ui_structure_style="modern_minimal",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_nordic_aurora",
        cards=[
            VisionCardConfig(engine_id=f"pack6_engine_{i:02d}", palette="cyan" if i % 2 == 0 else "green", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 15. Bioshock Steampunk (Pack 10: 10-12 + Pack 12: 0-6)
    VisionLayout(
        layout_id="preset_bioshock_steampunk",
        name="Rapture Brass Bathysphere",
        description="Art deco brass gauges, vacuum steam release valves, and art-deco underwater ballroom echoes.",
        stitch_theme_id="bioshock_steampunk_rapture",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_bioshock_steampunk",
        cards=[
            VisionCardConfig(engine_id=f"pack10_engine_{i:02d}", palette="amber", order=i - 10) for i in range(10, 13)
        ] + [
            VisionCardConfig(engine_id=f"pack12_engine_{i:02d}", palette="crt" if i % 2 == 0 else "amber", order=3 + i) for i in range(7)
        ],
        is_builtin=True,
    ),

    # 16. Quantum Void (Pack 12: 7-12 + Pack 11: 0-3)
    VisionLayout(
        layout_id="preset_quantum_void",
        name="Zero-Point Quantum Collider",
        description="Dark energy wave-function collapse, subatomic particle tracks, and deep cosmic void resonance.",
        stitch_theme_id="quantum_void_collider",
        gap_distance=1,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_quantum_void",
        cards=[
            VisionCardConfig(engine_id=f"pack12_engine_{i:02d}", palette="purple", order=i - 7) for i in range(7, 13)
        ] + [
            VisionCardConfig(engine_id=f"pack11_engine_{i:02d}", palette="cyan", order=6 + i) for i in range(4)
        ],
        is_builtin=True,
    ),

    # 17. Hyprland Rice (Pack 11: 4-12 + Pack 7: 10)
    VisionLayout(
        layout_id="preset_hyprland_rice",
        name="Hyprland Wayland Rice Terminal",
        description="Nord color palette, smooth rounded borders, dynamic master stack tiling, and catppuccin accents.",
        stitch_theme_id="hyprland_nord_rice",
        gap_distance=2,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_hyprland_rice",
        cards=[
            VisionCardConfig(engine_id=f"pack11_engine_{i:02d}", palette="purple" if i % 2 == 0 else "cyan", order=i - 4) for i in range(4, 13)
        ] + [
            VisionCardConfig(engine_id="pack7_engine_10", palette="magenta", order=9)
        ],
        is_builtin=True,
    ),

    # 18. DOS Mpxplay (Pack 8: 3-12)
    VisionLayout(
        layout_id="preset_dos_mpxplay",
        name="DOS Mpxplay ANSI Rig",
        description="Authentic MS-DOS command-line player interface, ANSI graphics, and FAT32 directory tracklist.",
        stitch_theme_id="dos_mpxplay_classic",
        gap_distance=0,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_dos_mpxplay",
        cards=[
            VisionCardConfig(engine_id=f"pack8_engine_{i:02d}", palette="cyan" if i % 2 == 0 else "amber", order=i - 3)
            for i in range(3, 13)
        ],
        is_builtin=True,
    ),

    # 19. Analog Mastering (Pack 4: 0-9)
    VisionLayout(
        layout_id="preset_analog_mastering",
        name="Mastering Lab Reference Console",
        description="Abbey Road precision: dual needle ballistic VU meters, stereo phase goniometer, and R128 loudness radar.",
        stitch_theme_id="analog_mastering_console",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_analog_mastering",
        cards=[
            VisionCardConfig(engine_id=f"pack4_engine_{i:02d}", palette="amber" if i % 2 == 0 else "green", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),

    # 20. Stellar Galaxy (Pack 3: 0-9)
    VisionLayout(
        layout_id="preset_stellar_galaxy",
        name="Hubble Deep Nebula Observatory",
        description="Spiral galaxy gravitational waves, interstellar dust spectrum, and cosmic microwave background radiation.",
        stitch_theme_id="deep_space_nebula",
        gap_distance=1,
        ui_structure_style="modern_minimal",
        button_style_mode="minimal_clean",
        anime_character_id="preset_stellar_galaxy",
        cards=[
            VisionCardConfig(engine_id=f"pack3_engine_{i:02d}", palette="purple" if i % 2 == 0 else "cyan", order=i)
            for i in range(10)
        ],
        is_builtin=True,
    ),
]

# Combined builtin layouts (3 starter templates + 20 distinct presets)
BUILTIN_LAYOUTS: List[VisionLayout] = BUILTIN_STARTER_LAYOUTS + PRESET_LAYOUTS


class VisionLayoutStore:
    """Manages persistent layout templates and user custom dashboard profiles."""

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            self.storage_dir = Path.home() / ".config" / "omnirip"
        else:
            self.storage_dir = Path(storage_dir)

        self.layouts_dir = self.storage_dir / "vision_layouts"
        self.layouts_dir.mkdir(parents=True, exist_ok=True)

    def list_layouts(self) -> List[VisionLayout]:
        """Return all built-in presets plus user-saved custom layouts."""
        layouts: List[VisionLayout] = list(BUILTIN_LAYOUTS)

        # Load user custom layouts from disk
        if self.layouts_dir.exists():
            for p in sorted(self.layouts_dir.glob("*.json")):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cards_data = data.pop("cards", [])
                        cards = [VisionCardConfig(**c) for c in cards_data]
                        data["cards"] = cards
                        layouts.append(VisionLayout(**data))
                except Exception as e:
                    logger.warning(f"Failed to load layout from {p}: {e}")

        return layouts

    def get_layout(self, layout_id: str) -> Optional[VisionLayout]:
        """Fetch a specific layout by ID."""
        for ly in self.list_layouts():
            if ly.layout_id == layout_id:
                return ly
        return None

    def save_layout(self, layout: VisionLayout) -> Optional[Path]:
        """Persist a user custom layout to disk and return saved Path."""
        if not layout.layout_id:
            import uuid
            layout.layout_id = f"custom_{uuid.uuid4().hex[:8]}"

        if layout.is_builtin:
            return None

        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", layout.layout_id.lower())
        target_path = self.layouts_dir / f"{clean_id}.json"

        try:
            data = asdict(layout)
            data["is_builtin"] = False
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return target_path
        except Exception as e:
            logger.error(f"Failed to save layout {layout.layout_id}: {e}")
            return None

    def delete_layout(self, layout_id: str) -> bool:
        """Delete a custom layout file."""
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", layout_id.lower())
        target_path = self.layouts_dir / f"{clean_id}.json"

        if target_path.exists():
            try:
                target_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to delete layout {layout_id}: {e}")
                return False
        return False
