"""Persistent Layout Storage Service for Full Vision Canvas.

Allows users to design, save, load, and manage custom visualizer layouts
with custom engine combinations, palettes, sizing (span/tall), gap spacing,
Stitch design themes, anime characters, and structural TUI styles.
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
    """A full canvas layout blueprint containing multiple visual cards, anime companion, and TUI structure."""

    layout_id: str
    name: str
    description: str = ""
    author: str = "OmniRip User"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    stitch_theme_id: str = "neon_cyber"
    gap_distance: int = 1
    cards: List[VisionCardConfig] = field(default_factory=list)
    is_builtin: bool = False
    ui_structure_style: str = "hyprland_floating"
    button_style_mode: str = "pill"
    anime_character_id: str = ""


# 20 Curated Built-in Canvas Layout Presets
# All 20 presets feature 100% unique visualizer engine allocations (0% overlap),
# drawing across all 8 procedural packs and headline visualizer engines.
BUILTIN_LAYOUTS: List[VisionLayout] = [
    VisionLayout(
        layout_id="builtin_solo_stanford",
        name="Solo Hero: Stanford 3D Waterfall",
        description="Full-screen CCRMA Stanford 3D isometric perspective terrain.",
        stitch_theme_id="neon_cyber",
        gap_distance=1,
        ui_structure_style="hyprland_floating",
        button_style_mode="pill",
        anime_character_id="preset_cyberpunk_2077",
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=True, tall_two=True, order=0),
        ],
        is_builtin=True,
    ),
    # 1. Y2K Aesthetic
    VisionLayout(
        layout_id="preset_y2k_aesthetic",
        name="Y2K Chrome & Aqua Deck",
        description="Late-90s cyber-pop futurism with translucent visor, platform sneakers, and hypercube rotation.",
        stitch_theme_id="y2k_aesthetic",
        gap_distance=2,
        ui_structure_style="y2k_cyber",
        button_style_mode="pill",
        anime_character_id="preset_y2k_aesthetic",
        cards=[
            VisionCardConfig(engine_id="pack7_hypercube_tesseract_rotator", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack4_lissajous_knot_3_4_ratio", palette="neon", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack6_bubble_acoustic_cavitation", palette="cyan", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_high_shelf_sparkle", palette="magenta", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 2. Cyberpunk 2077
    VisionLayout(
        layout_id="preset_cyberpunk_2077",
        name="Cyberpunk 2077 Quad Deck",
        description="High-energy 4-way studio: Stanford 3D terrain, Matrix code rain, Lissajous scope, and Audio flame.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_cyberpunk_2077",
        cards=[
            VisionCardConfig(engine_id="stanford_sun_music_3d", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="matrix_digital_rain", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="lissajous_harmonics", palette="purple", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="audio_flame_fire", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 3. Matrix Terminal
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
            VisionCardConfig(engine_id="pack5_matrix_falling_code_rain", palette="green", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack5_hex_dump_audio_memory", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack5_terminal_cursor_telemetry", palette="green", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack5_encrypted_signal_decoder", palette="green", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 4. Lo-Fi Chill
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
            VisionCardConfig(engine_id="pack2_vacuum_tube_glow_grid", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack2_analog_tape_head_flux", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack1_octave_log_spectrum", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack6_dust_mote_brownian_drift", palette="crt", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 5. Synthwave Horizon
    VisionLayout(
        layout_id="preset_synthwave_horizon",
        name="Synthwave Horizon 1984",
        description="Sunset neon grid mountains, retro CRT reticle, and transient audio flashes with cassette idol.",
        stitch_theme_id="synthwave_dusk",
        gap_distance=1,
        ui_structure_style="hyprland_floating",
        button_style_mode="pill",
        anime_character_id="preset_synthwave_horizon",
        cards=[
            VisionCardConfig(engine_id="pack3_retro_sun_neon_grid", palette="sunset", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack3_stanford_terrain_wireframe", palette="sunset", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack2_reticle_crt_graticule", palette="crt", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_transient_spike_flashes", palette="neon", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 6. Vaporwave Dream
    VisionLayout(
        layout_id="preset_vaporwave_dream",
        name="Aesthetic Vaporwave Plaza",
        description="Pastel pink sun visor, sacred geometry flowers, goniometer ellipses, and aurora curtains.",
        stitch_theme_id="vaporwave_aesthetic",
        gap_distance=2,
        ui_structure_style="rmpc_split",
        button_style_mode="bracket_caps",
        anime_character_id="preset_vaporwave_dream",
        cards=[
            VisionCardConfig(engine_id="pack7_sacred_flower_of_life", palette="magenta", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack4_goniometer_ellipse_scope", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack6_solar_wind_aurora_curtain", palette="neon", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_mel_scale_filterbank", palette="magenta", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 7. Tokyo Drift
    VisionLayout(
        layout_id="preset_tokyo_drift",
        name="Tokyo Touge Drift Telemetry",
        description="Shinjuku night street racing telemetry with 3D flight valleys and dynamic range meters.",
        stitch_theme_id="tokyo_midnight",
        gap_distance=1,
        ui_structure_style="drift_telemetry",
        button_style_mode="hud_caps",
        anime_character_id="preset_tokyo_drift",
        cards=[
            VisionCardConfig(engine_id="pack3_flight_simulator_valley", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack2_delayed_sweep_timebase", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack8_dynamic_range_dr14_meter", palette="neon", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_sub_bass_rumble_meter", palette="cyan", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 8. Analog Warmth
    VisionLayout(
        layout_id="preset_analog_warmth",
        name="Audiophile Vinyl & Tubes Deck",
        description="Walnut open-back cans, spring reverb tank, bias saturation curves, and classic analog VU needle.",
        stitch_theme_id="analog_warmth",
        gap_distance=1,
        ui_structure_style="rackmount_hardware",
        button_style_mode="tactile_knobs",
        anime_character_id="preset_analog_warmth",
        cards=[
            VisionCardConfig(engine_id="pack2_analog_spring_reverb_tank", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack2_bias_saturation_curves", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack8_thd_harmonic_distortion_bar", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="vu_meter", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 9. 8-Bit Chiptune
    VisionLayout(
        layout_id="preset_8bit_chiptune",
        name="8-Bit Chiptune Arcade Cabinet",
        description="Pixel snapback cap, handheld gaming rig, chiptune frequency bars, and packet sniffing.",
        stitch_theme_id="nord_frost",
        gap_distance=2,
        ui_structure_style="arcade_cabinet",
        button_style_mode="retro_arcade",
        anime_character_id="preset_8bit_chiptune",
        cards=[
            VisionCardConfig(engine_id="frequency_bars", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack5_databank_packet_sniffer", palette="green", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack7_sierpinski_gasket_pulse", palette="cyan", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_crest_factor_envelope", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 10. Acid Demoscene
    VisionLayout(
        layout_id="preset_acid_demoscene",
        name="Amiga Acid Demoscene 1993",
        description="Amiga tracker visor, Mandelbrot fractal zoom, plasma flames, and CRT beam deflection.",
        stitch_theme_id="matrix_terminal",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_acid_demoscene",
        cards=[
            VisionCardConfig(engine_id="pack7_mandelbrot_audio_zoom", palette="neon", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack6_plasma_audio_flame_emitter", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack2_crt_beam_deflection", palette="green", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack3_vector_matrix_landscape", palette="cyan", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 11. Gothic Lolita
    VisionLayout(
        layout_id="preset_gothic_lolita",
        name="Victorian Darkwave Maiden",
        description="Multi-tiered black lace gown, Fibonacci spirals, orbital spirograph, and phosphor decay trails.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        ui_structure_style="rmpc_split",
        button_style_mode="bracket_caps",
        anime_character_id="preset_gothic_lolita",
        cards=[
            VisionCardConfig(engine_id="pack7_golden_ratio_fibonacci_spiral", palette="purple", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack4_orbital_harmonic_spirograph", palette="purple", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack2_phosphor_decay_trails", palette="crt", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack8_spectral_flatness_tonality", palette="neon", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 12. Deep Space
    VisionLayout(
        layout_id="preset_deep_space",
        name="Deep Space Voyager Cockpit",
        description="EVA navigator helmet, spiral galaxy discs, chasm depth, and quantum bit superposition.",
        stitch_theme_id="deep_space",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_deep_space",
        cards=[
            VisionCardConfig(engine_id="pack6_galaxy_spiral_particle_disc", palette="green", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack3_infinite_chasm_depth", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack4_polar_stereo_phase_field", palette="green", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack5_quantum_bit_superposition", palette="neon", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 13. Neon Miami Vice
    VisionLayout(
        layout_id="preset_neon_vice",
        name="Miami Vice '86 Detective Console",
        description="Turquoise pastel blazer, sunglasses, sunmusic horizons, and dual beam phosphor scopes.",
        stitch_theme_id="synthwave_dusk",
        gap_distance=1,
        ui_structure_style="hyprland_floating",
        button_style_mode="pill",
        anime_character_id="preset_neon_vice",
        cards=[
            VisionCardConfig(engine_id="pack3_sunmusic_horizon_lines", palette="sunset", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack1_spectral_flux_pulse", palette="magenta", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack2_dual_beam_phosphor_scope", palette="cyan", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack8_spectral_centroid_brightness", palette="neon", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 14. Coffee Acoustic
    VisionLayout(
        layout_id="preset_coffee_acoustic",
        name="Indie Coffee Shop Acoustic Snug",
        description="Barista apron, slouchy beanie, pure audio oscilloscope, and vortex smoke rings.",
        stitch_theme_id="analog_warmth",
        gap_distance=1,
        ui_structure_style="lofi_cafe",
        button_style_mode="cozy_soft",
        anime_character_id="preset_coffee_acoustic",
        cards=[
            VisionCardConfig(engine_id="oscilloscope", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack1_mid_side_stereo_imager", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack6_smoke_ring_vortex_shedding", palette="crt", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack8_crest_factor_crest_meter", palette="amber", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 15. Glitchcore Breakcore
    VisionLayout(
        layout_id="preset_glitchcore_breakcore",
        name="Glitchcore 240 BPM Riot Deck",
        description="Studded spiked collar, torn fishnets, binary decompilation, and true-peak clipping tracers.",
        stitch_theme_id="tokyo_midnight",
        gap_distance=2,
        ui_structure_style="drift_telemetry",
        button_style_mode="hud_caps",
        anime_character_id="preset_glitchcore_breakcore",
        cards=[
            VisionCardConfig(engine_id="pack5_glitch_binary_decompilation", palette="neon", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack6_firework_transient_bursts", palette="magenta", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack2_clipping_hard_knee_tracer", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack8_inter_sample_peak_true_isp", palette="cyan", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 16. Sunset Lounge
    VisionLayout(
        layout_id="preset_sunset_lounge",
        name="Tropical Sunset Island Deck",
        description="Breeze-blown floral yukata, hibiscus pin, viscous fluid shear waves, and Braille fluid.",
        stitch_theme_id="vaporwave_aesthetic",
        gap_distance=1,
        ui_structure_style="hyprland_floating",
        button_style_mode="pill",
        anime_character_id="preset_sunset_lounge",
        cards=[
            VisionCardConfig(engine_id="pack6_viscous_fluid_shear_waves", palette="sunset", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack4_phase_correlation_wheel", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack1_spectral_rolloff_ridge", palette="magenta", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="braille_fluid", palette="sunset", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 17. Dubstep Bass Cannon
    VisionLayout(
        layout_id="preset_dubstep_bass",
        name="Sub-Bass Heavyweight Cannon",
        description="Sound-reactive respirator mask, LED lightsticks, supernova blasts, and 40Hz sub-bass flags.",
        stitch_theme_id="cyberpunk_2077",
        gap_distance=1,
        ui_structure_style="cyberdeck_terminal",
        button_style_mode="cyber_brackets",
        anime_character_id="preset_dubstep_bass",
        cards=[
            VisionCardConfig(engine_id="pack6_supernova_transient_blast", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack8_sub_harmonic_sub_bass_flag", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack1_stereo_coherence_bars", palette="cyan", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack6_magnetohydrodynamic_sparks", palette="neon", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 18. Industrial Dark Synth
    VisionLayout(
        layout_id="preset_industrial_synth",
        name="Mecha Heavy Combat Console",
        description="Ballistic ceramic armor, combat headset, bio-cyber HUD gauges, and core reactor telemetry.",
        stitch_theme_id="nord_frost",
        gap_distance=1,
        ui_structure_style="rackmount_hardware",
        button_style_mode="tactile_knobs",
        anime_character_id="preset_industrial_synth",
        cards=[
            VisionCardConfig(engine_id="pack5_bio_cybernetic_hud_gauges", palette="cyan", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack5_mainframe_core_reactor", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack8_broadcast_ebu_r128_loudness", palette="crt", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack3_wireframe_pyramid_peak", palette="cyan", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 19. Kawaii Future Bass
    VisionLayout(
        layout_id="preset_kawaii_future",
        name="Kawaii Future Magical Stage",
        description="Cat-ear headphones, holographic star skirt, Julia set morph, and fountain particle cascades.",
        stitch_theme_id="y2k_aesthetic",
        gap_distance=2,
        ui_structure_style="y2k_cyber",
        button_style_mode="pill",
        anime_character_id="preset_kawaii_future",
        cards=[
            VisionCardConfig(engine_id="pack7_julia_set_dynamic_morph", palette="magenta", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack6_fountain_particle_cascade", palette="cyan", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack4_binaural_delay_circle", palette="neon", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack1_spectral_waterfall_bars", palette="magenta", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
    # 20. Vintage Speakeasy Jazz
    VisionLayout(
        layout_id="preset_vintage_jazz",
        name="1920s Speakeasy Velvet Salon",
        description="Shimmering fringe dress, feather headband, chrome ribbon mic, and mirrored dance pillars.",
        stitch_theme_id="analog_warmth",
        gap_distance=1,
        ui_structure_style="dos_mpxplay",
        button_style_mode="dos_keys",
        anime_character_id="preset_vintage_jazz",
        cards=[
            VisionCardConfig(engine_id="mirrored_dance", palette="amber", span_two=False, tall_two=False, order=0),
            VisionCardConfig(engine_id="pack2_ac_power_hum_ripple", palette="amber", span_two=False, tall_two=False, order=1),
            VisionCardConfig(engine_id="pack8_phase_cancellation_detector", palette="amber", span_two=False, tall_two=False, order=2),
            VisionCardConfig(engine_id="pack4_stereo_balance_quadrant", palette="crt", span_two=False, tall_two=False, order=3),
        ],
        is_builtin=True,
    ),
]


class VisionLayoutStore:
    """Manages the persistence, validation, and retrieval of visual layouts."""

    def __init__(self, layouts_dir: Optional[Path] = None, storage_dir: Optional[Path] = None):
        self.layouts_dir = layouts_dir or storage_dir or DEFAULT_LAYOUTS_DIR
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory if it doesn't exist."""
        try:
            self.layouts_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create vision layouts dir: {e}")

    def list_layouts(self) -> List[VisionLayout]:
        """List all available layouts (built-ins followed by user-created)."""
        layouts: List[VisionLayout] = list(BUILTIN_LAYOUTS)

        if self.layouts_dir.exists():
            for p in sorted(self.layouts_dir.glob("*.json")):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cards = [VisionCardConfig(**c) for c in data.get("cards", [])]
                        data["cards"] = cards
                        data["is_builtin"] = False
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
