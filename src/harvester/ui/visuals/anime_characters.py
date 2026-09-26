"""Theme-dressed ASCII anime characters for Full Vision Studio presets.

Each character is meticulously formatted with distinct theme-specific fashion,
accessories, and hairstyles matching the 20 Google Stitch visual presets.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AnimeCharacter:
    preset_id: str
    name: str
    title: str
    outfit_desc: str
    ascii_art: str


Y2K_AIMI = r"""
       .-''''-.
     .'  _  _  '.     [ Y2K CYBER-POP ]
    /   (o)(o)   \    Aimi / アイミ
   :      /\      :   • Butterfly clips & tint shades
   :    .----.    :   • Baggy cargo pants & CD player
    \  '------'  /    • Translucent cyber visor
     '.  `--'  .'
      /`-....-'\
    / /|      |\ \
   (_/ |  Y2K | \_)
       |  2000|
       |______|
       /  /\  \
      /  /  \  \
     (__/    \__)
"""

CYBERPUNK_VKIRA = r"""
       .---.
     _/ /_\ \_        [ NIGHT CITY NETRUNNER ]
    ( \ @   @ / )     V-Kira / キラ
     \ \  ^  / /      • Optical cyber-eye & neural jack
      \ \---/ /       • Armored chrome leather jacket
     .-' `-' '-.      • Dual katana harness
   / /|  [CY] |\ \
  (_/ |  BER  | \_)
      |  2077 |
      /  .-.  \
     /  /   \  \
    (__/     \__)
"""

MATRIX_TRINITY = r"""
       .---.
      /     \         [ NEB MATRIX OPERATOR ]
     | () () |        Trinity-X / トリニティ
     |   ^   |        • Dark wireframe sunglasses
      \ === /         • Glossy floor-length trenchcoat
     .-'---'-.        • Streaming green operator code
    /  |:::|  \
   /   |:::|   \
  / /| |:::| |\ \
 (_/ | |:::| | \_)
     | |:::| |
     | |:::| |
     / |:::| \
    (__/   \__)
"""

LOFI_CHIYO = r"""
       .---.
      /  _  \         [ COZY LO-FI STUDY ]
     |  (o)(o)|       Chiyo / ちよ
     |   __  |        • Oversized fleece pastel hoodie
     |  (__) |        • Studio headphones & matcha mug
     /       \        • Cat resting on warm oak desk
    / /|   |\ \
   / / | ☕ | \ \
  (_/  |   |  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

SYNTHWAVE_REIKO = r"""
       .---.
      / ~ ~ \         [ '84 RETRO POP IDOL ]
     |  > <  |        Reiko / レイコ
     |   -   |        • Sunset gradient aviators
      \  _  /         • Neon windbreaker & cassette deck
     .-'---'-.        • Fingerless driving gloves
    /  |SUN|  \
   / / |SET| \ \
  (_/  | 84|  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

VAPORWAVE_AURA = r"""
       .---.
      / === \         [ AESTHETIC VAPORWAVE ]
     |  o  o |        Aura / アウラ
     |   ~   |        • Translucent pink sun visor
      \ === /         • Pastel denim jacket & roller skates
     .-'---'-.        • Marble statue bust aura
    /  | 90|  \
   / / |S  | \ \
  (_/  |   |  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

TOKYO_HANAKO = r"""
       .---.
      / \ / \         [ SHINJUKU TOUGE RACER ]
     |  ` `  |        Hanako / ハナコ
     |   -   |        • Red racing suit unzipped to waist
      \ === /         • Checkered bandana & leather gloves
     .-'---'-.        • Midnight drift telemetry
    /  |DRF|  \
   / / |777| \ \
  (_/  |   |  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

ANALOG_SHIORI = r"""
       .---.
      / (_) \         [ AUDIOPHILE PURIST ]
     |  - -  |        Shiori / 栞
     |   u   |        • Hand-knit oversized cable sweater
      \ === /         • Walnut open-back dynamic cans
     .-'---'-.        • Vinyl 180g master sleeve in hand
    /  |LP |  \
   / / | 33| \ \
  (_/  |   |  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

CHIPTUNE_PICO = r"""
      [#####]
      | ^ ^ |         [ 8-BIT ARCADE GAMER ]
      |  =  |         Pico / ピコ
      [-----]         • Pixel cap & retro handheld
     .-'---'-.        • Arcade coin token necklace
    /  |JOY|  \       • Chibi 8-bit platformer sprites
   / / |PAD| \ \
  (_/  |   |  \_)
       |===|
       |   |
      /     \
     [#]   [#]
"""

DEMOSCENE_HEXA = r"""
      .-----.
     / [HUD] \        [ AMIGA DEMOSCENE CRACKER ]
    |  o   o  |       Hexa / ヘクサ
    |    -    |       • Raster split visor & tracker patch
     \  ---  /        • Demoparty 1993 lanyard
     .-'---'-.        • Copper list register readout
    /  |ASM|  \
   / / |SYS| \ \
  (_/  |   |  \_)
       |___|
       /   \
      /     \
     (__) (__)
"""

GOTHIC_LILITH = r"""
       /---\
      / / \ \         [ VICTORIAN DARKWAVE ]
     |  o o  |        Lilith / リリス
     |   .   |        • Multi-tiered black lace gown
      \  ~  /         • Satin ribbon choker & parasol
     .-'---'-.        • Bat wing silver hairpin
    /  |✝ ✝|  \
   / / |   | \ \
  (_/  |___|  \_)
      /=====\
     /       \
    /_________\
"""

DEEP_SPACE_STELLA = r"""
      .-----.
     / [EVA] \        [ COSMIC EVA NAVIGATOR ]
    |  (o o)  |       Stella / ステラ
     \   =   /        • Zero-G pressurized helm & gold visor
     .-'---'-.        • Solar propulsion thruster pack
    /  |NASA| \       • Orbital telemetry HUD
   / / |EVA | \ \
  (_/  |____|  \_)
       |    |
      /  /\  \
     (__/  \__)
"""

NEON_SONYA = r"""
       .---.
      / / \ \         [ '86 MIAMI DETECTIVE ]
     | [===] |        Sonya / ソーニャ
     |   -   |        • Rolled-up turquoise pastel blazer
      \ === /         • White linen pants & dark shades
     .-'---'-.        • Flaming palm tree motif
    /  |VIC|  \
   / / | E | \ \
  (_/  |___|  \_)
       |   |
      /  /\ \
     (__/  \__)
"""

COFFEE_MAYA = r"""
       .---.
      / === \         [ INDIE ACOUSTIC BARISTA ]
     |  u u  |        Maya / マヤ
     |   -   |        • Slouchy knit beanie & canvas apron
      \ === /         • Acoustic guitar strap over shoulder
     .-'---'-.        • Steaming pour-over brew
    /  |COF|  \
   / / |FEE| \ \
  (_/  |___|  \_)
       |   |
      /  /\ \
     (__/  \__)
"""

GLITCHCORE_RAVE = r"""
       /\_/\
      / > < \         [ GLITCHCORE BREAKCORE ]
     |   #   |        Rave-Zero / 零
      \ === /         • Spiky neon twin-tails & safety pins
     .-'---'-.        • Studded spiked choker & torn fishnets
    /  |GLT|  \       • 240 BPM amen break cadence
   / / | CH| \ \
  (_/  |___|  \_)
       |   |
      /  /\ \
     (__/  \__)
"""

SUNSET_NAMI = r"""
       .---.
      / \ / \         [ TROPICAL SUNSET LOUNGE ]
     |  - -  |        Nami / 波
     |   u   |        • Floral summer kimono & hibiscus pin
      \ === /         • Bamboo folding fan & sea breeze
     .-'---'-.        • Amber cocktail by the tide
    /  |~~~|  \
   / / |~~~| \ \
  (_/  |___|  \_)
      /=====\
     /       \
    /_________\
"""

DUBSTEP_SUBDROP = r"""
      .-----.
     / [SUB] \        [ SUB-BASS BASS CANNON ]
    |  !   !  |       Sub-Drop / 重低音
    |  [===]  |       • Heavy respirator & LED glowsticks
     \  ---  /        • Heavy spiked drop-crotch armor
     .-'---'-.        • 40 Hz seismic bass sub-rig
    /  |40H|  \
   / / | z | \ \
  (_/  |___|  \_)
       |   |
      /  /\ \
     (__/  \__)
"""

INDUSTRIAL_KRIEG = r"""
      .-----.
     / [TAC] \        [ MECHA COMBAT PILOT ]
    |  =   =  |       Krieg / 鉄
    |   ---   |       • Ballistic ceramic combat rig
     \  ===  /        • Forearm combat telemetry link
     .-'---'-.        • Heavy industrial exosuit boots
    /  |MIL|  \
   / / |SPEC| \ \
  (_/  |____|  \_)
       |    |
      /  /\  \
     (__/  \__)
"""

KAWAII_MIKU = r"""
      /'-^-'\
     (  ^ ^  )        [ FUTURE BASS MAGICAL IDOL ]
     |   v   |        Miku-Pop / ミク
     (  ---  )        • Cat-ear light-up headphones
     .-'---'-.        • Holographic frilled star skirt
    /  |★ ★|  \       • Star wand & candy pop drops
   / / |   | \ \
  (_/  |___|  \_)
      /=====\
     /       \
    /_________\
"""

VINTAGE_CELESTE = r"""
       .---.
      /  _  \         [ 1920s SPEAKEASY FLAPPER ]
     |  o o  |        Celeste / セレスト
     |   .   |        • Shimmering gold fringe flapper dress
      \  ~  /         • Ostrich feather headband & pearls
     .-'---'-.        • Vintage chrome ribbon microphone
    /  |JAZ|  \
   / / | Z | \ \
  (_/  |___|  \_)
      /=====\
     /       \
    /_________\
"""

THEME_ANIME_CHARACTERS: Dict[str, AnimeCharacter] = {
    "preset_y2k_aesthetic": AnimeCharacter(
        preset_id="preset_y2k_aesthetic",
        name="Aimi (アイミ)",
        title="Y2K Cyber-Pop Specialist",
        outfit_desc="Butterfly clips, CD headphones, translucent visor, baggy cargo pants",
        ascii_art=Y2K_AIMI.strip(),
    ),
    "preset_cyberpunk_2077": AnimeCharacter(
        preset_id="preset_cyberpunk_2077",
        name="V-Kira (キラ)",
        title="Night City Netrunner",
        outfit_desc="Optical cyber-eye, neural jack cables, armored leather jacket, dual katana harness",
        ascii_art=CYBERPUNK_VKIRA.strip(),
    ),
    "preset_matrix_terminal": AnimeCharacter(
        preset_id="preset_matrix_terminal",
        name="Trinity-X (トリニティ)",
        title="Nebuchadnezzar Operator",
        outfit_desc="Dark wireframe shades, glossy floor-length trenchcoat, combat boots",
        ascii_art=MATRIX_TRINITY.strip(),
    ),
    "preset_lofi_chill": AnimeCharacter(
        preset_id="preset_lofi_chill",
        name="Chiyo (ちよ)",
        title="Cozy Lo-Fi Study Companion",
        outfit_desc="Oversized pastel fleece hoodie, studio headphones, steaming matcha mug",
        ascii_art=LOFI_CHIYO.strip(),
    ),
    "preset_synthwave_horizon": AnimeCharacter(
        preset_id="preset_synthwave_horizon",
        name="Reiko (レイコ)",
        title="'84 Retro Outrun Idol",
        outfit_desc="Sunset gradient aviators, neon windbreaker, cassette walkman, driving gloves",
        ascii_art=SYNTHWAVE_REIKO.strip(),
    ),
    "preset_vaporwave_dream": AnimeCharacter(
        preset_id="preset_vaporwave_dream",
        name="Aura (アウラ)",
        title="Aesthetic Vaporwave Muse",
        outfit_desc="Translucent pink sun visor, oversized pastel denim jacket, retro roller skates",
        ascii_art=VAPORWAVE_AURA.strip(),
    ),
    "preset_tokyo_drift": AnimeCharacter(
        preset_id="preset_tokyo_drift",
        name="Hanako (ハナコ)",
        title="Shinjuku Touge Racer",
        outfit_desc="Red racing jumpsuit unzipped, checkered bandana, leather driving gloves",
        ascii_art=TOKYO_HANAKO.strip(),
    ),
    "preset_analog_warmth": AnimeCharacter(
        preset_id="preset_analog_warmth",
        name="Shiori (栞)",
        title="Audiophile Vinyl Purist",
        outfit_desc="Chunky knit cable sweater, walnut-backed dynamic cans, 180g master vinyl",
        ascii_art=ANALOG_SHIORI.strip(),
    ),
    "preset_8bit_chiptune": AnimeCharacter(
        preset_id="preset_8bit_chiptune",
        name="Pico (ピコ)",
        title="8-Bit Arcade Speedrunner",
        outfit_desc="Pixelated snapback cap, handheld gaming rig, arcade token necklace",
        ascii_art=CHIPTUNE_PICO.strip(),
    ),
    "preset_acid_demoscene": AnimeCharacter(
        preset_id="preset_acid_demoscene",
        name="Hexa (ヘクサ)",
        title="Amiga Demoscene Cracker",
        outfit_desc="Raster split visor, tracker patch track jacket, 1993 demoparty lanyard",
        ascii_art=DEMOSCENE_HEXA.strip(),
    ),
    "preset_gothic_lolita": AnimeCharacter(
        preset_id="preset_gothic_lolita",
        name="Lilith (リリス)",
        title="Victorian Darkwave Maiden",
        outfit_desc="Multi-tiered black lace gown, satin ribbon choker, lace parasol, bat wing pin",
        ascii_art=GOTHIC_LILITH.strip(),
    ),
    "preset_deep_space": AnimeCharacter(
        preset_id="preset_deep_space",
        name="Stella (ステラ)",
        title="Cosmic EVA Navigator",
        outfit_desc="Zero-G pressurized helm, solar flare gold visor, magnetic thruster boots",
        ascii_art=DEEP_SPACE_STELLA.strip(),
    ),
    "preset_neon_vice": AnimeCharacter(
        preset_id="preset_neon_vice",
        name="Sonya (ソーニャ)",
        title="'86 Miami Vice Detective",
        outfit_desc="Rolled-up turquoise pastel blazer, white linen trousers, dark sunglasses",
        ascii_art=NEON_SONYA.strip(),
    ),
    "preset_coffee_acoustic": AnimeCharacter(
        preset_id="preset_coffee_acoustic",
        name="Maya (マヤ)",
        title="Indie Acoustic Barista",
        outfit_desc="Slouchy knit beanie, barista apron over flannel, acoustic guitar strap",
        ascii_art=COFFEE_MAYA.strip(),
    ),
    "preset_glitchcore_breakcore": AnimeCharacter(
        preset_id="preset_glitchcore_breakcore",
        name="Rave-Zero (零)",
        title="Glitchcore Cyber Rebel",
        outfit_desc="Spiky neon twin-tails, studded spiked collar, torn fishnets, safety pins",
        ascii_art=GLITCHCORE_RAVE.strip(),
    ),
    "preset_sunset_lounge": AnimeCharacter(
        preset_id="preset_sunset_lounge",
        name="Nami (波)",
        title="Tropical Sunset Resort Muse",
        outfit_desc="Breeze-blown floral summer yukata, hibiscus hairpin, bamboo folding fan",
        ascii_art=SUNSET_NAMI.strip(),
    ),
    "preset_dubstep_bass": AnimeCharacter(
        preset_id="preset_dubstep_bass",
        name="Sub-Drop (重低音)",
        title="Sub-Bass Heavyweight DJ",
        outfit_desc="Sound-reactive respirator mask, LED lightstick bracers, drop-crotch armor",
        ascii_art=DUBSTEP_SUBDROP.strip(),
    ),
    "preset_industrial_synth": AnimeCharacter(
        preset_id="preset_industrial_synth",
        name="Krieg (鉄)",
        title="Mecha Combat Pilot",
        outfit_desc="Ballistic ceramic tactical vest, heavy exoskeleton boots, combat headset",
        ascii_art=INDUSTRIAL_KRIEG.strip(),
    ),
    "preset_kawaii_future": AnimeCharacter(
        preset_id="preset_kawaii_future",
        name="Miku-Pop (ミク)",
        title="Future Bass Magical Idol",
        outfit_desc="Cat-ear glowing headphones, holographic star skirt, pastel twintails",
        ascii_art=KAWAII_MIKU.strip(),
    ),
    "preset_vintage_jazz": AnimeCharacter(
        preset_id="preset_vintage_jazz",
        name="Celeste (セレスト)",
        title="1920s Speakeasy Flapper",
        outfit_desc="Shimmering fringe flapper dress, feather headband, vintage chrome microphone",
        ascii_art=VINTAGE_CELESTE.strip(),
    ),
}


def get_anime_character(preset_id: str) -> AnimeCharacter:
    """Retrieve the theme-dressed anime character for a preset, defaulting to Aimi."""
    return THEME_ANIME_CHARACTERS.get(preset_id, THEME_ANIME_CHARACTERS["preset_y2k_aesthetic"])
