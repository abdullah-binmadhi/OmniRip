"""Theme-dressed high-definition Braille anime characters and 60 FPS animation/color pipeline.

Each character uses authentic, high-definition Japanese Braille text mode art
extracted from authentic sources, complete with:
- 31 distinct characters (20 preset defaults + 11 bonus unlocked companions)
- 10 multi-stop gradient color palettes + custom hex support
- 5 real-time 60 FPS animation effects (scanline shimmer, audio pulse, color flow, hologram flicker, idle breathe)
"""

import functools
import math
from dataclasses import dataclass

import numpy as np
from rich.text import Text

from harvester.ui.visuals.base import AudioFeatureContext
from harvester.ui.visuals.braille_art import BRAILLE_ARTWORKS


@dataclass(frozen=True)
class AnimeCharacter:
    preset_id: str
    name: str
    title: str
    outfit_desc: str
    ascii_art: str
    char_id: str = ""
    series_lore: str = ""


# ---------------------------------------------------------------------------
# 10 Multi-Stop Color Palettes for Anime Text Rendering
# ---------------------------------------------------------------------------

ANIME_PALETTES: dict[str, dict[str, object]] = {
    "cyberpunk_neon": {
        "name": "Cyberpunk Neon",
        "icon": "⌬",
        "stops": [("#00f0ff", 0.0), ("#ff007f", 0.5), ("#ffee00", 1.0)],
        "accent": "#00f0ff",
    },
    "matrix_phosphor": {
        "name": "Matrix Green Phosphor",
        "icon": "⌗",
        "stops": [("#00ff66", 0.0), ("#22cc44", 0.6), ("#005522", 1.0)],
        "accent": "#00ff66",
    },
    "sunset_horizon": {
        "name": "Retrowave Sunset",
        "icon": "☼",
        "stops": [("#9900ff", 0.0), ("#ff4500", 0.5), ("#ffaa00", 1.0)],
        "accent": "#ff4500",
    },
    "pastel_dream": {
        "name": "Pastel Sakura Dream",
        "icon": "✦",
        "stops": [("#ff9ebb", 0.0), ("#c5a3ff", 0.5), ("#ffd1a4", 1.0)],
        "accent": "#ff9ebb",
    },
    "tokyo_night": {
        "name": "Tokyo Midnight Indigo",
        "icon": "≋",
        "stops": [("#00e5ff", 0.0), ("#5800ff", 0.5), ("#1a1f71", 1.0)],
        "accent": "#5800ff",
    },
    "amber_vintage": {
        "name": "Vintage Vacuum Amber",
        "icon": "⎇",
        "stops": [("#ffdd44", 0.0), ("#ff9900", 0.5), ("#aa4400", 1.0)],
        "accent": "#ff9900",
    },
    "deep_ocean": {
        "name": "Deep Oceanic Trench",
        "icon": "⌕",
        "stops": [("#e0ffff", 0.0), ("#00d4ff", 0.5), ("#003366", 1.0)],
        "accent": "#00d4ff",
    },
    "solar_flare": {
        "name": "Solar Flare Corona",
        "icon": "▲",
        "stops": [("#ffffff", 0.0), ("#ff6600", 0.5), ("#cc0000", 1.0)],
        "accent": "#ff6600",
    },
    "emerald_mint": {
        "name": "Cyber Jade & Mint",
        "icon": "◈",
        "stops": [("#00ffcc", 0.0), ("#2ebd85", 0.5), ("#0d4a36", 1.0)],
        "accent": "#00ffcc",
    },
    "monochrome_bone": {
        "name": "Bone Monochrome Silver",
        "icon": "𝄢",
        "stops": [("#ffffff", 0.0), ("#999999", 0.5), ("#333333", 1.0)],
        "accent": "#ffffff",
    },
}

# ---------------------------------------------------------------------------
# 5 Real-Time 60 FPS Animation FX Modes
# ---------------------------------------------------------------------------

ANIME_FX_MODES: dict[str, tuple[str, str]] = {
    "scanline_shimmer": ("≋", "CRT Scanline Shimmer (Holographic raster beam sweep)"),
    "audio_pulse": ("⚡", "Audio Bass Pulse (Reactive transient brightness flares)"),
    "color_flow": ("◈", "Color Flow Aurora (Continuous vertical gradient cycling)"),
    "hologram_flicker": ("⌬", "Hologram Jitter (Phase flicker & scanline dropout)"),
    "idle_breathe": ("∿", "Idle Sine Breathe (Gentle 0.5Hz ambient luminescence)"),
}


# ---------------------------------------------------------------------------
# Character Lore & Braille Artwork Definitions (31 Total)
# ---------------------------------------------------------------------------

_RAW = BRAILLE_ARTWORKS

_CHAR_METADATA = [
    # 1. Y2K Aesthetic
    ("char_01", "preset_y2k_aesthetic", "Aimi / アイミ", "Y2K Cyber-Pop Netrunner",
     "Butterfly clips & tint shades\nBaggy cargo pants & CD player\nTranslucent cyber visor", 0),
    # 2. Cyberpunk 2077
    ("char_02", "preset_cyberpunk_2077", "V-Kira / キラ", "Night City Solo Netrunner",
     "Optical cyber-eye & neural jack\nArmored chrome leather jacket\nDual katana harness", 1),
    # 3. Matrix Terminal
    ("char_03", "preset_matrix_terminal", "Trinity-X / トリニティ", "Nebuchadnezzar Matrix Operator",
     "Dark wireframe sunglasses\nGlossy floor-length trenchcoat\nStreaming green operator code", 2),
    # 4. Lo-Fi Chill
    ("char_04", "preset_lofi_chill", "Maya / マヤ", "Lo-Fi Study Companion",
     "Oversized cozy knit hoodie\nMatcha latte mug & wired headphones\nWarm vinyl dust glow", 3),
    # 5. Tokyo Night
    ("char_05", "preset_tokyo_night", "Ren / レン", "Shibuya Neon Drifter",
     "Reflective Shibuya puffer jacket\nNeon ear-cuff communication array\nUnderground club pass", 4),
    # 6. Retrowave Sunset
    ("char_06", "preset_retrowave_sunset", "Chloe / クロエ", "Outrun Synthwave Cruiser",
     "Mirrored gradient aviator shades\nPastel synthwave bomber jacket\nRollerskates & walkman tape deck", 5),
    # 7. Industrial Decay
    ("char_07", "preset_industrial_decay", "Rust-01 / ラスト", "Wasteland Salvage Engineer",
     "Welder mask with cracked phosphor lens\nHeavy oil-stained work vest\nExoskeleton pneumatic arm", 6),
    # 8. Deep Ocean
    ("char_08", "preset_deep_ocean", "Marina / マリーナ", "Abyssal Sonar Specialist",
     "Bioluminescent wetsuit\nPressurized diving helmet visor\nSonar ping headphones", 7),
    # 9. Solar Flare
    ("char_09", "preset_solar_flare", "Solara / ソララ", "Solar Observatory Pilot",
     "Golden radiation shielding cape\nSolar corona crest headband\nThermal plasma gauntlets", 8),
    # 10. Acid Techno
    ("char_10", "preset_acid_techno", "Acid-DJ / アシッド", "Underground Rave Alchemist",
     "Strobe reflective jumpsuit\n303 acid smiley badge & respirator\nLED equalizer visor", 9),
    # 11. Vaporwave Mall
    ("char_11", "preset_vaporwave_mall", "Crystal / クリスタル", "Aesthetic Plaza Spirit",
     "Classic Greek bust silhouette choker\nAesthetic teal & magenta windbreaker\nCassette tape earrings", 10),
    # 12. Dungeon Synth
    ("char_12", "preset_dungeon_synth", "Morwen / モルウェン", "Crypt Runic Arch-Mage",
     "Gothic iron sorceress cowl\nAntiquated runic spell parchment\nBronze skull talisman", 11),
    # 13. Chiptune Gameboy
    ("char_13", "preset_chiptune_gameboy", "Dot-Chan / ドット", "8-Bit Handheld Pixie",
     "Monochrome 8-bit ribbon\nOriginal Game Boy shell backpack\nChiptune tracker cartridge", 12),
    # 14. Nordic Aurora
    ("char_14", "preset_nordic_aurora", "Freya / フレイヤ", "Fjord Aurora Navigator",
     "Fur-trimmed polar expedition parka\nAurora crystal quartz amulet\nThermal snow goggles", 13),
    # 15. Bioshock Steampunk
    ("char_15", "preset_bioshock_steampunk", "Ada / エイダ", "Pneumatic Clockwork Artisan",
     "Brass pressure gauge monocle\nLeather rivet corset & copper piping\nSteam escapement chronometer", 14),
    # 16. Quantum Void
    ("char_16", "preset_quantum_void", "Nova / ノヴァ", "Singularity Event Observer",
     "Event horizon dark matter cloak\nZero-point quantum levitator\nSubatomic particle halo", 15),
    # 17. Hyprland Rice
    ("char_17", "preset_hyprland_rice", "Dotfile / ドットファイル", "Wayland Tiling Architect",
     "Minimalist monochrome turtleneck\nMechanical keyboard keycap necklace\nArch Linux cat-ear headset", 16),
    # 18. DOS Mpxplay
    ("char_18", "preset_dos_mpxplay", "Commander Ken / ケン", "Real-Mode DOS Guru",
     "Retro beige PC technician coat\n5.25 inch floppy disk badge\nCRT phosphor anti-glare specs", 17),
    # 19. Analog Mastering
    ("char_19", "preset_analog_mastering", "Elena / エレナ", "Mastering Lab Precision Engineer",
     "Audiophile reference velvet robe\nGold-plated XLR jack earrings\nPrecision VU meter cuff links", 18),
    # 20. Stellar Galaxy
    ("char_20", "preset_stellar_galaxy", "Astra / アストラ", "Deep Space Pulsar Cartographer",
     "Interstellar star-chart jumpsuit\nCosmic dust navigation ring\nNebula prism visor", 19),
    # 21-31: Unlocked Bonus Characters
    ("char_21", "bonus_madoka", "Madoka / まどか", "Cosmic Starlight Weaver",
     "Ribbon-tied cosmic dress\nBow of celestial starlight\nGolden soul gem choker", 20),
    ("char_22", "bonus_homura", "Homura / ほむら", "Temporal Loop Guardian",
     "Deep obsidian school uniform\nShield of looping chronometry\nTime-traveler wrist apparatus", 21),
    ("char_23", "bonus_sayaka", "Sayaka / さやか", "Symphonic Blade Maiden",
     "Azure flowing knight cloak\nDual harmonic sabers\nMusical clef hairpin", 22),
    ("char_24", "bonus_kyoko", "Kyoko / きょうこ", "Crimson Spear Wanderer",
     "Scarlet layered battle vest\nSegmented gold-chain spear\nPocky stick & rebel grin", 23),
    ("char_25", "bonus_kanna", "Kanna / カンナ", "Dragon Spark Darling",
     "Pastel gothic lolita frills\nElectro-static tail plug\nFeathered dragon horns", 24),
    ("char_26", "bonus_tohru", "Tohru / トール", "Chaos Dragon Maid",
     "Victorian maid headband & apron\nEmerald draconic wings\nEternal flame aura", 25),
    ("char_27", "bonus_frieren", "Frieren / フリーレン", "Timeless Melodic Sage",
     "Elven ceremonial white tunic\nGold-trimmed spellcaster wand\nCenturies-old tranquil gaze", 26),
    ("char_28", "bonus_fern", "Fern / フェルン", "High-Speed Arcane Sniper",
     "Deep purple apprentice cloak\nRapid-fire mana focus staff\nPouting perfectionist aura", 27),
    ("char_29", "bonus_bocchi", "Bocchi / ぼっち", "Introvert Guitar God",
     "Oversized pink zip-up jersey\nBlack Les Paul gig bag\nCardboard box hiding posture", 28),
    ("char_30", "bonus_nijika", "Nijika / にじか", "Shimokitazawa Rhythm Heart",
     "Side ponytail yellow star clip\nPair of matched 5A drumsticks\nRadiant sunshine smile", 29),
    ("char_31", "bonus_kita", "Kita / きた", "Kita-Aura Spotlight Frontwoman",
     "Shujin red school blazer\nPelham Blue Gibson double-cut\nDazzling Kita-aura sparkles", 30),
]

ALL_ANIME_CHARACTERS: dict[str, AnimeCharacter] = {}
THEME_ANIME_CHARACTERS: dict[str, AnimeCharacter] = {}

for char_id, preset_id, name, title, outfit_desc, art_idx in _CHAR_METADATA:
    art = _RAW[art_idx] if art_idx < len(_RAW) else _RAW[0]
    char_obj = AnimeCharacter(
        char_id=char_id,
        preset_id=preset_id,
        name=name,
        title=title,
        outfit_desc=outfit_desc,
        ascii_art=art,
        series_lore=f"{title} • {name}",
    )
    ALL_ANIME_CHARACTERS[char_id] = char_obj
    if preset_id.startswith("preset_"):
        THEME_ANIME_CHARACTERS[preset_id] = char_obj


def get_anime_character(preset_or_char_id: str) -> AnimeCharacter:
    """Retrieve an anime character by preset ID or character ID with fallback."""
    if preset_or_char_id in THEME_ANIME_CHARACTERS:
        return THEME_ANIME_CHARACTERS[preset_or_char_id]
    if preset_or_char_id in ALL_ANIME_CHARACTERS:
        return ALL_ANIME_CHARACTERS[preset_or_char_id]
    # Fallback to Aimi
    return THEME_ANIME_CHARACTERS.get("preset_y2k_aesthetic", list(ALL_ANIME_CHARACTERS.values())[0])


def list_all_anime_characters() -> list[AnimeCharacter]:
    """Return all 31 available Braille anime characters."""
    return list(ALL_ANIME_CHARACTERS.values())


# ---------------------------------------------------------------------------
# Color Gradient Math & Real-Time Animated Rendering Pipeline
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    ir = max(0, min(255, int(r)))
    ig = max(0, min(255, int(g)))
    ib = max(0, min(255, int(b)))
    return f"#{ir:02x}{ig:02x}{ib:02x}"


def _interpolate_color_stops(stops: list[tuple[str, float]], t: float) -> str:
    """Interpolate along multi-stop RGB gradient where t in [0.0, 1.0]."""
    t = max(0.0, min(1.0, t))
    if t <= stops[0][1]:
        return stops[0][0]
    if t >= stops[-1][1]:
        return stops[-1][0]

    for i in range(len(stops) - 1):
        c1, p1 = stops[i]
        c2, p2 = stops[i + 1]
        if p1 <= t <= p2:
            span = p2 - p1 if p2 > p1 else 1.0
            ratio = (t - p1) / span
            r1, g1, b1 = _hex_to_rgb(c1)
            r2, g2, b2 = _hex_to_rgb(c2)
            r = r1 + (r2 - r1) * ratio
            g = g1 + (g2 - g1) * ratio
            b = b1 + (b2 - b1) * ratio
            return _rgb_to_hex(r, g, b)
    return stops[0][0]


def _build_custom_stops(hex_code: str) -> list[tuple[str, float]]:
    """Build a rich 3-stop gradient from an arbitrary user hex code."""
    r, g, b = _hex_to_rgb(hex_code)
    # Bright highlight
    br = _rgb_to_hex(min(255, r * 1.35 + 30), min(255, g * 1.35 + 30), min(255, b * 1.35 + 30))
    # Mid tone
    mid = hex_code
    # Deep shadow
    drk = _rgb_to_hex(r * 0.45, g * 0.45, b * 0.45)
    return [(br, 0.0), (mid, 0.5), (drk, 1.0)]


# Map dot position (row 0..3, col 0..1) to bit index in Unicode braille offset (0..255)
DOT_MAP = [
    (0, 0, 0x01), (1, 0, 0x02), (2, 0, 0x04), (3, 0, 0x40),
    (0, 1, 0x08), (1, 1, 0x10), (2, 1, 0x20), (3, 1, 0x80),
]


def _braille_to_dot_grid(text: str) -> np.ndarray:
    raw_lines = [line.rstrip() for line in text.split("\n") if line.strip()]
    if not raw_lines:
        return np.zeros((0, 0), dtype=bool)
    max_c = max(len(line) for line in raw_lines)
    grid = np.zeros((len(raw_lines) * 4, max_c * 2), dtype=bool)
    for r_idx, line in enumerate(raw_lines):
        for c_idx, ch in enumerate(line):
            code = ord(ch)
            if 0x2800 <= code <= 0x28FF:
                bits = code - 0x2800
                for dr, dc, bit in DOT_MAP:
                    if bits & bit:
                        grid[r_idx * 4 + dr, c_idx * 2 + dc] = True
    return grid


def _dot_grid_to_braille(grid: np.ndarray) -> str:
    h, w = grid.shape
    pad_h = (4 - (h % 4)) % 4
    pad_w = (2 - (w % 2)) % 2
    if pad_h > 0 or pad_w > 0:
        grid = np.pad(grid, ((0, pad_h), (0, pad_w)), mode="constant")
    h, w = grid.shape

    lines = []
    for r in range(0, h, 4):
        chars = []
        for c in range(0, w, 2):
            code = 0x2800
            for dr, dc, bit in DOT_MAP:
                if grid[r + dr, c + dc]:
                    code |= bit
            chars.append(chr(code))
        lines.append("".join(chars).rstrip())
    return "\n".join(lines)


@functools.lru_cache(maxsize=128)
def fit_braille_art(text: str, max_cols: int = 34, max_lines: int = 28) -> str:
    """Proportionally downsample 2D Braille dot matrix so art fully fits in frame without cropping."""
    grid = _braille_to_dot_grid(text)
    if grid.size == 0:
        return text
    src_h, src_w = grid.shape
    tgt_w = max_cols * 2
    tgt_h = max_lines * 4

    scale_x = tgt_w / src_w if src_w > tgt_w else 1.0
    scale_y = tgt_h / src_h if src_h > tgt_h else 1.0
    scale = min(scale_x, scale_y)

    if scale >= 1.0:
        # Already fits comfortably
        return text

    new_w = max(2, int(round(src_w * scale)))
    new_h = max(4, int(round(src_h * scale)))

    down_grid = np.zeros((new_h, new_w), dtype=bool)
    for dy in range(new_h):
        sy0 = int(dy / scale)
        sy1 = max(sy0 + 1, int((dy + 1) / scale))
        for dx in range(new_w):
            sx0 = int(dx / scale)
            sx1 = max(sx0 + 1, int((dx + 1) / scale))
            if np.any(grid[sy0:sy1, sx0:sx1]):
                down_grid[dy, dx] = True

    return _dot_grid_to_braille(down_grid)


def render_animated_anime_frame(
    character: AnimeCharacter,
    palette_id: str = "cyberpunk_neon",
    custom_hex: str | None = None,
    fx_mode: str = "scanline_shimmer",
    tick: int = 0,
    ctx: AudioFeatureContext | None = None,
    max_lines: int = 32,
    max_cols: int = 70,
) -> Text:
    """Render a 60 FPS animated, colored Braille text frame with dynamic audio FX.

    Args:
        character: The AnimeCharacter instance to render.
        palette_id: Key from ANIME_PALETTES or 'custom'.
        custom_hex: User-supplied hex string when palette_id == 'custom'.
        fx_mode: One of ANIME_FX_MODES.
        tick: Monotonic frame counter incremented at 60 FPS.
        ctx: Live audio feature context (optional).
        max_lines: Maximum terminal lines to render (fits sidebar).
        max_cols: Maximum terminal columns to fit.
    """
    # Proportional downscaling via 2D Braille dot-matrix pooling
    fitted_art = fit_braille_art(character.ascii_art, max_cols=max_cols, max_lines=max_lines)
    raw_lines = [line for line in fitted_art.split("\n") if line.strip()]
    if not raw_lines:
        return Text("No Braille Art Available", style="dim")

    # Center lines horizontally within max_cols
    centered_lines: list[str] = []
    for line in raw_lines[:max_lines]:
        if len(line) < max_cols:
            pad = max(0, (max_cols - len(line)) // 2)
            centered_lines.append(" " * pad + line)
        else:
            centered_lines.append(line[:max_cols])

    total_lines = len(centered_lines)
    lines_to_render = centered_lines

    # Resolve gradient color stops
    if custom_hex and custom_hex.startswith("#") and len(custom_hex) in (4, 7):
        stops = _build_custom_stops(custom_hex)
    else:
        pal_meta = ANIME_PALETTES.get(palette_id, ANIME_PALETTES["cyberpunk_neon"])
        stops = pal_meta["stops"]  # type: ignore

    # Calculate global FX modulation
    audio_transient = ctx.transient_flag if ctx else False
    is_playing = ctx.is_playing if ctx else False
    bass_energy = getattr(ctx, "bass", 0.5) if ctx else 0.5

    # 1. Idle breathe luminance wave
    breathe_mult = 1.0
    if fx_mode == "idle_breathe" or not is_playing:
        breathe_mult = 0.80 + 0.20 * math.sin(tick * 0.08)

    # 2. Audio transient pulse flash
    transient_flash = audio_transient and is_playing

    # 3. Scanline sweep position (moves down 1.2 lines per frame)
    scanline_pos = int((tick * 0.75) % max(1, total_lines))

    # 4. Color flow aurora phase offset
    flow_phase = (tick * 0.015) % 1.0 if fx_mode == "color_flow" else 0.0

    # 5. Hologram jitter effect (brief glitches every 60 frames)
    is_glitch_frame = (fx_mode == "hologram_flicker") and ((tick % 75) in (0, 1, 2))

    output = Text()

    for y, line in enumerate(lines_to_render):
        # Truncate line width cleanly
        cropped = line[:max_cols]

        # Calculate gradient position for this row
        t = (float(y) / max(1.0, float(total_lines - 1)) + flow_phase) % 1.0
        hex_color = _interpolate_color_stops(stops, t)
        r, g, b = _hex_to_rgb(hex_color)

        # Apply breathing modulation
        r = r * breathe_mult
        g = g * breathe_mult
        b = b * breathe_mult

        # Apply audio bass pulse
        if fx_mode == "audio_pulse" and is_playing:
            boost = 1.0 + 0.5 * bass_energy
            r, g, b = min(255, r * boost), min(255, g * boost), min(255, b * boost)

        # Apply transient flash
        if transient_flash:
            r = min(255, r + 70)
            g = min(255, g + 70)
            b = min(255, b + 70)

        # Check scanline shimmer
        is_scanline = (fx_mode == "scanline_shimmer") and (y == scanline_pos)
        is_scanline_adjacent = (fx_mode == "scanline_shimmer") and (abs(y - scanline_pos) == 1)

        row_style = ""
        if is_scanline:
            row_style = "bold #ffffff"
        elif is_scanline_adjacent:
            row_style = f"bold {_rgb_to_hex(min(255, r * 1.4), min(255, g * 1.4), min(255, b * 1.4))}"
        elif is_glitch_frame and (y % 4 == 0):
            # Horizontal glitch displacement and color inversion
            cropped = "  " + cropped[:-2]
            row_style = f"reverse {_rgb_to_hex(r, g, b)}"
        if y < total_lines - 1:
            output.append(cropped + "\n", style=row_style)
        else:
            output.append(cropped, style=row_style)

    return output

