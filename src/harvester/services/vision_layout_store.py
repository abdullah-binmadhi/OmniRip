"""Full Vision Layout Store and Persistence Engine.

Manages preset and user-saved visualizer card layouts, theme associations,
and dynamic canvas configurations.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
    cards: list[VisionCardConfig] = field(default_factory=list)
    is_builtin: bool = False


# Built-in quickstart starter templates
BUILTIN_STARTER_LAYOUTS: list[VisionLayout] = [
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
# Curated thematic renderer assignments. A preset has ten distinct render
# families within its own screen; families may recur in other presets.
# ---------------------------------------------------------------------------

PRESET_ENGINE_IDS: dict[str, tuple[str, ...]] = {
   'preset_acid_techno': (   'pack11_engine_04',
                              'pack10_engine_08',
                              'pack5_engine_09',
                              'terrain_cyber_wireframe',
                              'pack16_engine_01',
                              'particles_plasma_sphere',
                              'pack7_engine_06',
                              'pack14_engine_05',
                              'fractal_fibonacci_spiral',
                              'phase_vector_flower'),
    'preset_analog_mastering': (   'pack5_engine_08',
                                   'pack13_engine_03',
                                   'pack3_engine_04',
                                   'pack8_engine_04',
                                   'pack10_engine_05',
                                   'meter_true_peak_forensic',
                                   'pack15_engine_08',
                                   'pack7_engine_11',
                                   'pack1_engine_09',
                                   'pack4_engine_10'),
    'preset_bioshock_steampunk': (   'pack5_engine_01',
                                     'pack6_engine_01',
                                     'pack15_engine_03',
                                     'meter_clipping_density',
                                     'phase_sub_bass_mono_check',
                                     'pack7_engine_09',
                                     'particles_electric_arc',
                                     'scope_audio_glitch',
                                     'pack3_engine_03',
                                     'phase_polar_vector'),
    'preset_chiptune_gameboy': (   'pack2_engine_08',
                                   'pack11_engine_12',
                                   'pack6_engine_05',
                                   'pack10_engine_07',
                                   'pack12_engine_05',
                                   'pack1_engine_04',
                                   'scope_dual_trace',
                                   'scope_vector_xy',
                                   'pack3_engine_06',
                                   'pack14_engine_12'),
    'preset_cyberpunk_2077': (   'pack3_engine_05',
                                 'pack13_engine_07',
                                 'cyber_circuit_trace',
                                 'pack1_engine_06',
                                 'pack11_engine_06',
                                 'pack16_engine_04',
                                 'pack7_engine_02',
                                 'pack2_engine_02',
                                 'pack15_engine_09',
                                 'stanford_sun_music_3d'),
    'preset_deep_ocean': (   'pack2_engine_07',
                             'pack14_engine_08',
                             'pack11_engine_00',
                             'pack9_engine_01',
                             'scope_subpixel_interp',
                             'cyber_audio_spectrum_shred',
                             'pack1_engine_00',
                             'terrain_dune_ripples',
                             'pack3_engine_08',
                             'pack5_engine_07'),
    'preset_dos_mpxplay': (   'pack12_engine_12',
                              'pack14_engine_07',
                              'pack5_engine_00',
                              'pack1_engine_08',
                              'pack11_engine_08',
                              'pack13_engine_00',
                              'terrain_vector_globe',
                              'scope_tape_head',
                              'pack16_engine_11',
                              'pack3_engine_00'),
    'preset_dungeon_synth': (   'pack12_engine_04',
                                'pack10_engine_09',
                                'particles_cellular_automata',
                                'pack5_engine_04',
                                'pack6_engine_03',
                                'terrain_spectral_canyon',
                                'pack4_engine_12',
                                'particles_vortex_tornado',
                                'cyber_dna_helix',
                                'fractal_barnsley_fern'),
    'preset_hyprland_rice': (   'pack12_engine_11',
                                'pack8_engine_00',
                                'scope_braille_stereo',
                                'phosphor_crt_wave',
                                'pack4_engine_02',
                                'cyber_cyberdeck_boot',
                                'pack14_engine_00',
                                'pack10_engine_10',
                                'pack13_engine_05',
                                'pack9_engine_04'),
    'preset_industrial_decay': (   'pack8_engine_10',
                                   'pack15_engine_04',
                                   'matrix_digital_rain',
                                   'pack11_engine_10',
                                   'scope_trigger_holdoff',
                                   'pack14_engine_06',
                                   'pack2_engine_10',
                                   'pack12_engine_02',
                                   'pack10_engine_11',
                                   'pack7_engine_10'),
    'preset_lofi_chill': (   'meter_harman_target_tracker',
                             'pack1_engine_03',
                             'pack3_engine_07',
                             'fractal_koch_snowflake',
                             'pack2_engine_09',
                             'spectral_differential',
                             'spectral_vfd_vintage',
                             'pack10_engine_02',
                             'pack14_engine_09',
                             'pack8_engine_09'),
    'preset_matrix_terminal': (   'pack15_engine_00',
                                  'pack12_engine_01',
                                  'pack8_engine_11',
                                  'pack16_engine_08',
                                  'pack4_engine_07',
                                  'spectrum_10band',
                                  'phase_stereo_jostle',
                                  'particles_sand_storm',
                                  'pack13_engine_11',
                                  'terrain_tunnel_vortex'),
    'preset_nordic_aurora': (   'pack6_engine_04',
                                'pack2_engine_11',
                                'cyber_quantum_lattice',
                                'fractal_chladni_plate',
                                'pack13_engine_06',
                                'pack5_engine_06',
                                'stereo_vu_deck',
                                'pack16_engine_09',
                                'fractal_lorenz_attractor',
                                'pack3_engine_12'),
    'preset_quantum_void': (   'pack6_engine_12',
                               'pack3_engine_02',
                               'pack13_engine_09',
                               'mirrored_dance',
                               'pack12_engine_07',
                               'pack15_engine_12',
                               'particles_aurora_borealis',
                               'pack7_engine_00',
                               'fractal_dragon_curve',
                               'pack9_engine_05'),
    'preset_retrowave_sunset': (   'pack14_engine_03',
                                   'pack10_engine_06',
                                   'pack7_engine_03',
                                   'pack15_engine_01',
                                   'phase_orbit_knot',
                                   'cyber_binary_cascade',
                                   'pack8_engine_08',
                                   'scope_circular_polar',
                                   'pack13_engine_12',
                                   'pack12_engine_08'),
    'preset_solar_flare': (   'pack11_engine_02',
                              'lissajous_harmonics',
                              'pack9_engine_00',
                              'spectral_waterfall_bars',
                              'pack4_engine_00',
                              'pack1_engine_07',
                              'fractal_voronoi_cells',
                              'pack10_engine_00',
                              'pack5_engine_05',
                              'pack16_engine_10'),
    'preset_stellar_galaxy': (   'pack10_engine_01',
                                 'pack3_engine_11',
                                 'pack4_engine_04',
                                 'pack7_engine_12',
                                 'pack13_engine_10',
                                 'particles_spark_fountain',
                                 'terrain_hex_grid_mesh',
                                 'pack2_engine_04',
                                 'pack5_engine_12',
                                 'pack15_engine_07'),
    'preset_tokyo_night': (   'terrain_ribbon_highway',
                              'pack7_engine_04',
                              'pack14_engine_04',
                              'pack8_engine_01',
                              'pack5_engine_02',
                              'pack2_engine_00',
                              'pack1_engine_05',
                              'pack12_engine_00',
                              'particles_bubble_chamber',
                              'pack11_engine_01'),
    'preset_vaporwave_mall': (   'pack11_engine_03',
                                 'pack16_engine_12',
                                 'pack10_engine_03',
                                 'pack4_engine_05',
                                 'meter_k_system_master',
                                 'pack12_engine_10',
                                 'fractal_hyperbolic_tiling',
                                 'meter_phase_correlation_bar',
                                 'pack13_engine_01',
                                 'pack8_engine_12'),
    'preset_y2k_aesthetic': (   'pack4_engine_08',
                                'particles_galaxy_spiral',
                                'pack11_engine_07',
                                'spectral_sub_bass_rumble',
                                'pack8_engine_06',
                                'pack6_engine_08',
                                'terrain_mountain_horizon',
                                'terrain_isometric_voxels',
                                'spectral_braille_dense',
                                'pack9_engine_08')}

_PRESET_PALETTE_KEYS: dict[str, str] = {
    "preset_y2k_aesthetic": "cyan",
    "preset_cyberpunk_2077": "neon",
    "preset_matrix_terminal": "green",
    "preset_lofi_chill": "amber",
    "preset_tokyo_night": "neon",
    "preset_retrowave_sunset": "magenta",
    "preset_industrial_decay": "amber",
    "preset_deep_ocean": "cyan",
    "preset_solar_flare": "amber",
    "preset_acid_techno": "green",
    "preset_vaporwave_mall": "magenta",
    "preset_dungeon_synth": "crt",
    "preset_chiptune_gameboy": "green",
    "preset_nordic_aurora": "green",
    "preset_bioshock_steampunk": "amber",
    "preset_quantum_void": "purple",
    "preset_hyprland_rice": "cyan",
    "preset_dos_mpxplay": "green",
    "preset_analog_mastering": "amber",
    "preset_stellar_galaxy": "purple",
}


def _preset_cards(layout_id: str) -> list[VisionCardConfig]:
    palette = _PRESET_PALETTE_KEYS[layout_id]
    return [
        VisionCardConfig(engine_id=engine_id, palette=palette, order=order)
        for order, engine_id in enumerate(PRESET_ENGINE_IDS[layout_id])
    ]

PRESET_LAYOUTS: list[VisionLayout] = [
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
        cards=_preset_cards("preset_y2k_aesthetic"),
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
        cards=_preset_cards("preset_cyberpunk_2077"),
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
        cards=_preset_cards("preset_matrix_terminal"),
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
        cards=_preset_cards("preset_lofi_chill"),
        is_builtin=True,
    ),

    # 5. Tokyo Night (Pack 9: 10-12 + Pack 2: 0-6)
    VisionLayout(
        layout_id="preset_tokyo_night",
        name="Tokyo Midnight Neon Deck",
        description="Shibuya crossing rain puddles, neon kanji reflections, and night drive synthesizer scopes.",
        stitch_theme_id="tokyo_midnight",
        gap_distance=1,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_tokyo_night",
        cards=_preset_cards("preset_tokyo_night"),
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
        cards=_preset_cards("preset_retrowave_sunset"),
        is_builtin=True,
    ),

    # 7. Industrial Decay (Pack 14: 0-9)
    VisionLayout(
        layout_id="preset_industrial_decay",
        name="Industrial Wasteland Terminal",
        description="Rust, concrete, heavy bass sub-oscillators, and harsh telemetry distortion.",
        stitch_theme_id="industrial_metal",
        gap_distance=0,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_industrial_decay",
        cards=_preset_cards("preset_industrial_decay"),
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
        cards=_preset_cards("preset_deep_ocean"),
        is_builtin=True,
    ),

    # 9. Solar Flare (Pack 15: 4-12 + Mirrored Dance)
    VisionLayout(
        layout_id="preset_solar_flare",
        name="Solar Flare Thermonuclear Deck",
        description="Thermonuclear coronal loops, radioactive plasma fire, and high-frequency solar flares.",
        stitch_theme_id="solar_flare",
        gap_distance=1,
        ui_structure_style="demoscene_split",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_solar_flare",
        cards=_preset_cards("preset_solar_flare"),
        is_builtin=True,
    ),

    # 10. Acid Techno (Pack 1: 0-9)
    VisionLayout(
        layout_id="preset_acid_techno",
        name="Acid Techno 303 Lab",
        description="Roland TB-303 square wave resonance, distortion pedal harmonics, and hypnotic rave strobe.",
        stitch_theme_id="acid_rave",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_acid_techno",
        cards=_preset_cards("preset_acid_techno"),
        is_builtin=True,
    ),

    # 11. Vaporwave Mall (Pack 7: 0-9)
    VisionLayout(
        layout_id="preset_vaporwave_mall",
        name="Vaporwave Plaza Aesthetic",
        description="Pastel marble columns, Arizona green tea cans, Windows 95 icons, and slowed vinyl reverbs.",
        stitch_theme_id="vaporwave_mallsoft",
        gap_distance=2,
        ui_structure_style="modern_minimal",
        button_style_mode="pill",
        anime_character_id="preset_vaporwave_mall",
        cards=_preset_cards("preset_vaporwave_mall"),
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
        cards=_preset_cards("preset_dungeon_synth"),
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
        cards=_preset_cards("preset_chiptune_gameboy"),
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
        cards=_preset_cards("preset_nordic_aurora"),
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
        cards=_preset_cards("preset_bioshock_steampunk"),
        is_builtin=True,
    ),

    # 16. Quantum Void (Pack 12: 7-12 + Pack 11: 0-3)
    VisionLayout(
        layout_id="preset_quantum_void",
        name="Zero-Point Quantum Collider",
        description="Dark energy wave-function collapse, subatomic particle tracks, and deep cosmic void resonance.",
        stitch_theme_id="quantum_void",
        gap_distance=1,
        ui_structure_style="hyprland_rice",
        button_style_mode="hyprland_pills",
        anime_character_id="preset_quantum_void",
        cards=_preset_cards("preset_quantum_void"),
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
        cards=_preset_cards("preset_hyprland_rice"),
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
        cards=_preset_cards("preset_dos_mpxplay"),
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
        cards=_preset_cards("preset_analog_mastering"),
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
        cards=_preset_cards("preset_stellar_galaxy"),
        is_builtin=True,
    ),
]

# Combined builtin layouts (3 starter templates + 20 distinct presets)
BUILTIN_LAYOUTS: list[VisionLayout] = BUILTIN_STARTER_LAYOUTS + PRESET_LAYOUTS


class VisionLayoutStore:
    """Manages persistent layout templates and user custom dashboard profiles."""

    def __init__(self, storage_dir: Path | None = None):
        if storage_dir is None:
            self.storage_dir = Path.home() / ".config" / "omnirip"
        else:
            self.storage_dir = Path(storage_dir)

        self.layouts_dir = self.storage_dir / "vision_layouts"
        self.layouts_dir.mkdir(parents=True, exist_ok=True)

    def list_layouts(self) -> list[VisionLayout]:
        """Return all built-in presets plus user-saved custom layouts."""
        layouts: list[VisionLayout] = list(BUILTIN_LAYOUTS)

        # Load user custom layouts from disk
        if self.layouts_dir.exists():
            for p in sorted(self.layouts_dir.glob("*.json")):
                try:
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                        cards_data = data.pop("cards", [])
                        cards = [VisionCardConfig(**c) for c in cards_data]
                        data["cards"] = cards
                        layouts.append(VisionLayout(**data))
                except Exception as e:
                    logger.warning(f"Failed to load layout from {p}: {e}")

        return layouts

    def get_layout(self, layout_id: str) -> VisionLayout | None:
        """Fetch a specific layout by ID."""
        for ly in self.list_layouts():
            if ly.layout_id == layout_id:
                return ly
        return None

    def save_layout(self, layout: VisionLayout) -> Path | None:
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
