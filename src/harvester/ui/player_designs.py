"""Art direction for every built-in PLAYER page.

A design is a terminal-native page brief: its hierarchy, layout strategy, frame,
controls, and companion treatment. Audio renderer assignments live with the
built-in layout data so visual identity and graph identity stay independently
reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

SUPPORTED_DASHBOARD_LAYOUTS = frozenset(
    {
        "balanced_rows",
        "hero_left",
        "hero_top",
        "five_by_two",
        "three_columns",
        "split_columns",
        "solo",
        "dual",
        "quad",
    }
)

SUPPORTED_CONTROL_STYLES = frozenset(
    {"capsule", "cutout", "terminal", "soft", "flat", "heavy", "lcd", "instrument"}
)

LEGACY_DASHBOARD_LAYOUTS = {
    "cyberdeck_terminal": "hero_left",
    "dos_mpxplay": "five_by_two",
    "hyprland_rice": "three_columns",
    "lofi_cafe": "split_columns",
    "demoscene_split": "hero_top",
    "modern_minimal": "balanced_rows",
    "default_cards": "balanced_rows",
}

LEGACY_CONTROL_STYLES = {
    "cyber_brackets": "heavy",
    "dos_keys": "terminal",
    "hyprland_pills": "capsule",
    "cozy_soft": "soft",
    "minimal_clean": "flat",
    "pill": "capsule",
    "soft": "soft",
}


@dataclass(frozen=True, slots=True)
class PlayerPageDesign:
    """One curated visual language for a built-in PLAYER layout.

    The first block of fields is applied by ``PlayerStudioWidget`` directly.
    The second block is the runtime page grammar consumed by ``player_layout``;
    it defaults to the current masthead/footer shell so a design can be
    authored incrementally without a code change.
    """

    layout_id: str
    eyebrow: str
    page_title: str
    subtitle: str
    motif: str
    dashboard_layout: str
    control_style: str
    title_style: str
    companion_heading: str
    top_controls: tuple[str, str, str, str, str, str]
    rail: str = "masthead"
    rail_axis: str = "horizontal"
    button_family: str = ""
    button_frame: str = ""
    panel_slots: dict[str, str] = field(
        default_factory=lambda: {
            "companion": "rail_right",
            "dock": "footer",
            "motif": "masthead",
        }
    )
    frame_glyphs: str = ""
    border_roles: Mapping[str, str] = field(default_factory=dict)
    motion: Sequence[tuple[str, str, float, str]] = ()


PLAYER_PAGE_DESIGNS: dict[str, PlayerPageDesign] = {
    "preset_y2k_aesthetic": PlayerPageDesign(
        "preset_y2k_aesthetic",
        "DESKTOP 2K / STARTUP",
        "AQUA OS 2000",
        "LIQUID CHROME · PRISMATIC AUDIO",
        "✧ . ｡ﾟ CD-ROM / ONLINE ﾟ｡ . ✧",
        "hero_top",
        "capsule",
        "bold",
        "AQUA BUDDY // WINDOW 01",
        ("⌂ DESKTOP", "✦ STYLES", "▣ OPEN", "↓ SAVE", "GAP {gap}", "↗ NEW TAB"),
    ),
    "preset_cyberpunk_2077": PlayerPageDesign(
        "preset_cyberpunk_2077",
        "NIGHT CITY / NETRUNNER",
        "AFTERIMAGE 2077",
        "CONTRABAND SIGNAL DECK · CITY GRID",
        "╳ ━━━ SIGNAL BREACH ━━━ ╳",
        "hero_left",
        "heavy",
        "bold underline",
        "NIGHT CITY OPERATIVE",
        ("◈ MAIN", "⚡ LOADOUT", "⇧ IMPORT", "⇩ EXPORT", "GAP {gap}", "⌑ JACK OUT"),
    ),
    "preset_matrix_terminal": PlayerPageDesign(
        "preset_matrix_terminal",
        "SIMULATION / NODE 01",
        "PHOSPHOR CORE",
        "WAKEFUL SIGNAL · GREEN CHANNEL",
        "0101 ░▒▓ SIGNAL / STREAM ▓▒░ 1010",
        "five_by_two",
        "terminal",
        "bold",
        "RESIDUAL AGENT // CONNECTED",
        ("[HOME]", "[MODES]", "[READ]", "[WRITE]", "[GAP {gap}]", "[SHELL]"),
    ),
    "preset_lofi_chill": PlayerPageDesign(
        "preset_lofi_chill",
        "STUDY SESSION / SIDE A",
        "AFTERNOON TAPE",
        "WARM NEEDLE · DUST · ROOM TONE",
        "♪  ────── ◉ ──────  ♫",
        "hero_top",
        "soft",
        "italic",
        "STUDY BUDDY // TEA BREAK",
        ("☕ HOME", "✿ MOODS", "♡ OPEN", "☁ KEEP", "GAP {gap}", "↗ ROOM"),
    ),
    "preset_tokyo_night": PlayerPageDesign(
        "preset_tokyo_night",
        "TOKYO / AFTER HOURS",
        "SHIBUYA AFTER RAIN",
        "CITY SOUND MAP · PLATFORM 03",
        "SHIBUYA ── SHINJUKU ── 00:42",
        "three_columns",
        "cutout",
        "bold",
        "MIDNIGHT RIDER // PLATFORM 03",
        ("⌂ STATION", "◆ SCENES", "↧ BOARD", "↓ STORE", "GAP {gap}", "↗ PLATFORM"),
    ),
    "preset_retrowave_sunset": PlayerPageDesign(
        "preset_retrowave_sunset",
        "COASTAL CIRCUIT / 1984",
        "SUNSET DRIVE '84",
        "OUTRUN FM · CHROME HORIZON",
        "☼ ╲╲╲ ────── 1984 ────── ╱╱╱ ☼",
        "hero_top",
        "heavy",
        "bold",
        "OUTRUN PILOT // GOLDEN HOUR",
        ("⌂ GARAGE", "◈ SETS", "▣ LOAD", "▣ SAVE", "GAP {gap}", "↗ OUTRUN"),
    ),
    "preset_industrial_decay": PlayerPageDesign(
        "preset_industrial_decay",
        "SECTOR 09 / BASSWORKS",
        "RUST & PRESSURE",
        "PRESSURE 88 PSI · LOW FREQUENCY WARNING",
        "// RUST / STEEL / SUBSONIC //",
        "balanced_rows",
        "heavy",
        "bold",
        "SECTOR WARDEN // SHIFT 03",
        ("⌂ CONTROL", "! PROFILES", "▣ LOAD", "↓ LOG", "GAP {gap}", "↗ EXIT"),
    ),
    "preset_deep_ocean": PlayerPageDesign(
        "preset_deep_ocean",
        "ABYSSAL LISTENING POST",
        "TRENCH / −4,200 M",
        "BATHYMETRY · HYDROPHONE A",
        "◉─────·─────◉ / DEPTH / ◉─────",
        "hero_left",
        "terminal",
        "bold",
        "ABYSS DIVER // PRESSURE SUIT",
        ("⌂ LAB", "◉ MISSIONS", "▣ DEPLOY", "↓ LOG", "GAP {gap}", "↗ SUB"),
    ),
    "preset_solar_flare": PlayerPageDesign(
        "preset_solar_flare",
        "CORONA OBSERVATORY",
        "ACTIVE REGION / X-RAY",
        "SDO · MULTI-BAND CORONAL MONITOR",
        "☼ ╱╲ CORONAL LOOP ╱╲ ☼",
        "hero_top",
        "heavy",
        "bold",
        "CORONA OBSERVER // HELIO LAB",
        ("⌂ FLIGHT", "☼ FLARES", "▣ LOAD", "↓ RECORD", "GAP {gap}", "↗ ORBIT"),
    ),
    "preset_acid_techno": PlayerPageDesign(
        "preset_acid_techno",
        "303 RESONANCE LAB",
        "PATTERN A / LIVE",
        "CUTOFF · RESONANCE · ACCENT",
        "[01] x01  [02] x04  [03] x02  [04] x05",
        "five_by_two",
        "lcd",
        "bold",
        "ACID OPERATOR // PATTERN A",
        ("◂ MIXER", "⚡ PATTERNS", "▣ LOAD", "↓ STORE", "GAP {gap}", "↗ LIVE"),
    ),
    "preset_vaporwave_mall": PlayerPageDesign(
        "preset_vaporwave_mall",
        "NORTH WING / LEVEL 03",
        "MALL DIRECTORY",
        "WAYFINDING SYSTEM · AFTER CLOSING",
        "PALM COURT ── FOUNTAIN ── EXIT B",
        "three_columns",
        "cutout",
        "italic",
        "MALL WALKER // ATRIUM LEVEL 03",
        ("⌂ ATRIUM", "◈ DIRECTORY", "▣ ENTER", "↓ POLAROID", "GAP {gap}", "↗ MALL"),
    ),
    "preset_dungeon_synth": PlayerPageDesign(
        "preset_dungeon_synth",
        "THE CRYPT ARCHIVE / VOL. VII",
        "THE STONE GATE",
        "TORCHLIGHT · OLD STONE · TAPE HISS",
        "† ── TORCH / ECHO / DUST ── †",
        "hero_left",
        "heavy",
        "bold",
        "CRYPT KEEPER // THE LOWER HALL",
        ("⌂ CAMP", "♜ TOMES", "▣ UNSEAL", "↓ CHRONICLE", "GAP {gap}", "↗ PORTAL"),
    ),
    "preset_chiptune_gameboy": PlayerPageDesign(
        "preset_chiptune_gameboy",
        "POCKET SOUND / DMG-01",
        "DOT MATRIX AUDIO",
        "FOUR-SHADE SIGNAL · PULSE / NOISE / WAVE",
        "[ A ]  ▴ / ▾  [ B ]  ◀ / ▶",
        "five_by_two",
        "lcd",
        "bold",
        "POCKET COMPANION // PIXEL MODE",
        ("⌂ HOME", "◉ CARTS", "▣ LOAD", "↓ SAVE", "GAP {gap}", "↗ LINK"),
    ),
    "preset_nordic_aurora": PlayerPageDesign(
        "preset_nordic_aurora",
        "BOREALIS FIELD STATION",
        "QUIET SKY / KIRUNA",
        "67°51′N · MAGNETIC NIGHT WATCH",
        "⋰⋱ GREEN VEIL / VIOLET ARC ⋰⋱",
        "balanced_rows",
        "soft",
        "italic",
        "BOREALIS SCOUT // WINTER WATCH",
        ("⌂ STATION", "✧ LAYERS", "▣ LOAD", "↓ JOURNAL", "GAP {gap}", "↗ FIELD"),
    ),
    "preset_bioshock_steampunk": PlayerPageDesign(
        "preset_bioshock_steampunk",
        "RAPTURE / BATHYSPHERE 01",
        "THE BRASS BALLROOM",
        "ART DECO ACOUSTICS · PRESSURE 108 ATM",
        "◇ ══ BRASS / TIDE / REVERB ══ ◇",
        "three_columns",
        "cutout",
        "bold",
        "BATHYSPHERE DIVER // RAPTURE",
        ("⌂ DOCK", "◈ PROFILES", "▣ DIVE", "↓ JOURNAL", "GAP {gap}", "↗ ASCEND"),
    ),
    "preset_quantum_void": PlayerPageDesign(
        "preset_quantum_void",
        "VACUUM STATE MONITOR",
        "SUPERPOSITION WINDOW",
        "COLLAPSE DETECTOR · NULL ENERGY 0.00",
        "|ψ⟩ ── decohere ── |0⟩",
        "hero_top",
        "terminal",
        "bold",
        "STATE OBSERVER // PHASE UNRESOLVED",
        ("⌂ LAB", "⌬ STATES", "▣ MEASURE", "↓ RECORD", "GAP {gap}", "↗ COLLAPSE"),
    ),
    "preset_hyprland_rice": PlayerPageDesign(
        "preset_hyprland_rice",
        "WAYLAND / WORKSPACE 03",
        "NORD TILE MAP",
        "FOCUS FOLLOWS SOUND · GAPS 02",
        "╭──────┬─────────┬──────╮",
        "three_columns",
        "flat",
        "bold",
        "WORKSPACE COMPANION // FLOATING",
        ("⌂ SPACE", "◫ THEMES", "▣ TILE IN", "↓ SAVE RICE", "GAP {gap}", "↗ FLOAT"),
    ),
    "preset_dos_mpxplay": PlayerPageDesign(
        "preset_dos_mpxplay",
        "MPXPLAY / ANSI RIG",
        "C:\\MUSIC\\LIVE",
        "16-COLOR MODE · DIRECTORY / PLAYLIST",
        "MUSIC  DIR  WAV  FLAC  MP3  ─── READY",
        "five_by_two",
        "lcd",
        "bold",
        "DOS BUDDY // ANSI SESSION",
        ("OMNI", "PRESETS", "LOAD", "SAVE", "GAP {gap}", "SHELL"),
    ),
    "preset_analog_mastering": PlayerPageDesign(
        "preset_analog_mastering",
        "MASTERING REFERENCE",
        "MONITOR A / AES17",
        "−20 dBFS ALIGNMENT · HEADROOM IS SIGNAL",
        "VU 1  ├──────────────┤  +3",
        "balanced_rows",
        "instrument",
        "bold",
        "MASTERING ENGINEER // CONTROL ROOM",
        ("⌂ CONSOLE", "◈ BANKS", "RECALL", "STORE", "GAP {gap}", "PATCH BAY"),
    ),
    "preset_stellar_galaxy": PlayerPageDesign(
        "preset_stellar_galaxy",
        "DEEP FIELD OBSERVATORY",
        "VOYAGER / INTERSTELLAR",
        "COSMIC AUDIO MAP · OUTBOUND TRAJECTORY",
        "✦ . · ˚ · . * · ˚ · . ✦",
        "hero_left",
        "cutout",
        "italic",
        "FIELD ASTRONOMER // DEEP SPACE",
        ("⌂ MISSION", "✦ STARS", "▣ LOAD", "↓ ARCHIVE", "GAP {gap}", "↗ LAUNCH"),
    ),
    "builtin_solo_stanford": PlayerPageDesign(
        "builtin_solo_stanford",
        "CCRMA / STANFORD SOUND LAB",
        "3D WATERFALL",
        "SOUND PRESSURE / FREQUENCY / TIME",
        "╱╲╱╲╱╲ ACOUSTIC TERRAIN ╱╲╱╲╱╲",
        "solo",
        "instrument",
        "bold",
        "CCRMA RESEARCH COMPANION",
        ("⌂ HOME", "⌗ MODES", "▣ LOAD", "↓ SAVE", "GAP {gap}", "↗ OPEN"),
    ),
    "builtin_dual_cyber": PlayerPageDesign(
        "builtin_dual_cyber",
        "CYBERDECK / RAIN × PHASE",
        "TWO SIGNALS",
        "DATA STREAM · STEREO FIELD",
        "01 // DATA STREAM     02 // PHASE FIELD",
        "dual",
        "terminal",
        "bold",
        "CYBERDECK COMPANION // LINKED",
        ("⌂ HOME", "◈ FEEDS", "▣ LOAD", "↓ SAVE", "GAP {gap}", "↗ SHELL"),
    ),
    "builtin_quad_matrix": PlayerPageDesign(
        "builtin_quad_matrix",
        "MASTER DECK / FOUR CHANNEL",
        "CONTROL ROOM",
        "FOUR DISTINCT INSTRUMENTS · ONE PLAYHEAD",
        "MATRIX  •  PHASE  •  FLAME  •  TERRAIN",
        "quad",
        "cutout",
        "bold",
        "STUDIO COMPANION // FOUR-BUS",
        ("⌂ HOME", "🎛 BANKS", "▣ LOAD", "↓ SAVE", "GAP {gap}", "↗ STUDIO"),
    ),
}


def get_player_design(layout_id: str) -> PlayerPageDesign | None:
    """Return the curated design for a built-in layout, or ``None`` for user layouts."""
    return PLAYER_PAGE_DESIGNS.get(layout_id)
