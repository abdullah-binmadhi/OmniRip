"""Genre intent profiles: curated, capped mastering colour for enhanced masters.

Each profile is a small, hand-tuned set of tonal moves (never more than four
bands, never more than 2.5 dB) plus a limiter ceiling and a residual-width
factor. Multi-genre tracks blend profiles with a weighted mean, which makes
conflicting intentions cancel instead of stacking, and the blend keeps at
least six of the ten bands untouched (docs/01 D38).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from harvester.analysis.enhancement.eq import (
    EQ_FREQUENCIES,
    MasteringEQSettings,
)
from harvester.analysis.enhancement.presets import EnhancementPreset

GENRE_INTENSITIES: dict[str, float] = {"subtle": 0.6, "balanced": 1.0, "bold": 1.4}
DEFAULT_GENRE_INTENSITY = "subtle"

MAX_SINGLE_GAIN_DB = 2.5
MAX_BLEND_GAIN_DB = 2.0
MIN_UNTOUCHED_BANDS = 6
TOUCH_EPSILON_DB = 0.05
MAX_PROFILE_BANDS = 4
MAX_MIX_GENRES = 6
MAX_AUTO_GENRES = 3

WIDTH_FLOOR = 0.5
WIDTH_CEILING = 1.3


@dataclass(frozen=True, slots=True)
class GenreProfile:
    """One curated genre character applied to the enhanced master."""

    key: str
    label: str
    blurb: str
    bands: dict[int, float] = field(default_factory=dict)
    hpf_30hz: bool = False
    residual_width: float = 1.0
    limiter_ceiling_dbfs: float = -0.3


GENRE_PROFILES: dict[str, GenreProfile] = {
    "neutral": GenreProfile(
        key="neutral",
        label="Neutral",
        blurb="No colour — the enhanced master exactly as rendered.",
        limiter_ceiling_dbfs=-0.1,
    ),
    "hip_hop_trap": GenreProfile(
        key="hip_hop_trap",
        label="Hip-Hop / Trap",
        blurb="808 focus, soft low-mid cleanup, crisp hi-hat air.",
        bands={31: 1.5, 63: 2.0, 125: 1.0, 250: -1.5},
    ),
    "drill_uk": GenreProfile(
        key="drill_uk",
        label="Drill / UK Rap",
        blurb="Sliding 808 weight with a gritty top end.",
        bands={31: 1.5, 63: 1.5, 250: -1.0, 4000: 1.0},
    ),
    "rnb_soul": GenreProfile(
        key="rnb_soul",
        label="R&B / Soul",
        blurb="Round low end, forward lead, silky air.",
        bands={63: 1.5, 125: 0.5, 250: -1.0, 16000: 1.5},
    ),
    "pop": GenreProfile(
        key="pop",
        label="Pop",
        blurb="Tight low-mid, vocal presence, glossy top.",
        bands={63: 1.0, 250: -1.0, 2000: 1.0, 16000: 1.5},
    ),
    "house": GenreProfile(
        key="house",
        label="House",
        blurb="Warm four-on-the-floor kick with open hats.",
        bands={63: 1.5, 125: 0.5, 250: -1.0, 8000: 1.5},
        residual_width=1.15,
    ),
    "techno": GenreProfile(
        key="techno",
        label="Techno",
        blurb="Driving sub, dry mids, mechanical top.",
        bands={31: 1.0, 63: 1.5, 2000: 1.0, 8000: 1.0},
        residual_width=1.1,
    ),
    "trance_prog": GenreProfile(
        key="trance_prog",
        label="Trance / Progressive",
        blurb="Rolling bass body with wide airy leads.",
        bands={63: 1.0, 125: 1.0, 8000: 1.5, 16000: 2.0},
        residual_width=1.15,
    ),
    "bass_dubstep_dnb": GenreProfile(
        key="bass_dubstep_dnb",
        label="Bass / Dubstep / DnB",
        blurb="Deep sub weight, scooped low-mid, snappy top.",
        bands={31: 2.0, 63: 2.5, 250: -1.0, 8000: 1.0},
    ),
    "rock": GenreProfile(
        key="rock",
        label="Rock",
        blurb="Guitar body with a forward snare crack.",
        bands={125: 1.0, 500: -0.5, 1000: 0.5, 2000: 1.0},
        limiter_ceiling_dbfs=-0.5,
    ),
    "metal": GenreProfile(
        key="metal",
        label="Metal",
        blurb="Tight low-mid, aggressive presence, fizzy top tamed.",
        bands={125: 1.0, 250: -1.0, 2000: 1.5, 8000: -0.5},
        limiter_ceiling_dbfs=-0.5,
    ),
    "punk": GenreProfile(
        key="punk",
        label="Punk",
        blurb="Raw midrange attack with a bright edge.",
        bands={125: 0.5, 500: 0.5, 2000: 1.5, 8000: 0.5},
        limiter_ceiling_dbfs=-0.5,
    ),
    "indie_alt": GenreProfile(
        key="indie_alt",
        label="Indie / Alternative",
        blurb="Natural body with a soft sparkle lift.",
        bands={125: 0.5, 250: -0.5, 2000: 0.5, 8000: 1.0},
    ),
    "jazz": GenreProfile(
        key="jazz",
        label="Jazz",
        blurb="Minimal shaping: rumble removed, horns kept warm.",
        bands={250: -0.5, 2000: 0.5},
        hpf_30hz=True,
        limiter_ceiling_dbfs=-1.0,
    ),
    "classical_orchestral": GenreProfile(
        key="classical_orchestral",
        label="Classical / Orchestral",
        blurb="Transparent: sub cleanup and a whisper of hall air.",
        bands={31: -0.5, 250: -0.5, 16000: 0.5},
        hpf_30hz=True,
        limiter_ceiling_dbfs=-1.0,
    ),
    "acoustic_folk": GenreProfile(
        key="acoustic_folk",
        label="Acoustic / Folk",
        blurb="Woody body, de-boxed mids, string shimmer.",
        bands={250: -1.0, 2000: 0.5, 8000: 1.0},
        hpf_30hz=True,
        limiter_ceiling_dbfs=-0.7,
    ),
    "country": GenreProfile(
        key="country",
        label="Country",
        blurb="Warm acoustic body with vocal-forward presence.",
        bands={125: 1.0, 250: -0.5, 2000: 1.0, 8000: 1.0},
    ),
    "reggae_dancehall": GenreProfile(
        key="reggae_dancehall",
        label="Reggae / Dancehall",
        blurb="Heavy bassline weight with hollow low-mid.",
        bands={63: 2.0, 125: 1.0, 250: -1.5, 8000: 0.5},
    ),
    "latin_reggaeton": GenreProfile(
        key="latin_reggaeton",
        label="Latin / Reggaeton",
        blurb="Dembow kick weight with bright percussion.",
        bands={63: 1.5, 250: -1.0, 2000: 0.5, 8000: 1.5},
    ),
    "lofi_chill": GenreProfile(
        key="lofi_chill",
        label="Lo-fi / Chill",
        blurb="Soft highs and a gentle low-mid haze.",
        bands={31: -1.0, 250: -0.5, 8000: -1.0, 16000: -1.5},
        limiter_ceiling_dbfs=-0.7,
    ),
    "ambient_drone": GenreProfile(
        key="ambient_drone",
        label="Ambient / Drone",
        blurb="Wide, quiet, top rolled off for long listening.",
        bands={31: -1.5, 250: -0.5, 8000: -0.5},
        hpf_30hz=True,
        residual_width=1.05,
        limiter_ceiling_dbfs=-1.0,
    ),
}

GENRE_ALIASES: dict[str, str] = {
    "hip hop": "hip_hop_trap",
    "hip-hop": "hip_hop_trap",
    "hiphop": "hip_hop_trap",
    "rap": "hip_hop_trap",
    "trap": "hip_hop_trap",
    "phonk": "hip_hop_trap",
    "grime": "drill_uk",
    "drill": "drill_uk",
    "uk rap": "drill_uk",
    "uk drill": "drill_uk",
    "road rap": "drill_uk",
    "rnb": "rnb_soul",
    "r&b": "rnb_soul",
    "rhythm and blues": "rnb_soul",
    "soul": "rnb_soul",
    "neo soul": "rnb_soul",
    "motown": "rnb_soul",
    "funk": "rnb_soul",
    "pop": "pop",
    "dance pop": "pop",
    "synthpop": "pop",
    "synth pop": "pop",
    "electropop": "pop",
    "k-pop": "pop",
    "kpop": "pop",
    "j-pop": "pop",
    "jpop": "pop",
    "city pop": "pop",
    "house": "house",
    "deep house": "house",
    "tech house": "house",
    "progressive house": "house",
    "garage": "house",
    "uk garage": "house",
    "2-step": "house",
    "techno": "techno",
    "minimal techno": "techno",
    "industrial techno": "techno",
    "electro": "techno",
    "idm": "techno",
    "trance": "trance_prog",
    "progressive trance": "trance_prog",
    "psytrance": "trance_prog",
    "psytance": "trance_prog",
    "progressive": "trance_prog",
    "dubstep": "bass_dubstep_dnb",
    "drum and bass": "bass_dubstep_dnb",
    "drum & bass": "bass_dubstep_dnb",
    "dnb": "bass_dubstep_dnb",
    "d'n'b": "bass_dubstep_dnb",
    "jungle": "bass_dubstep_dnb",
    "bass": "bass_dubstep_dnb",
    "bass music": "bass_dubstep_dnb",
    "edm": "bass_dubstep_dnb",
    "rock": "rock",
    "classic rock": "rock",
    "hard rock": "rock",
    "alternative rock": "rock",
    "alt rock": "rock",
    "grunge": "rock",
    "post-rock": "rock",
    "post rock": "rock",
    "psychedelic rock": "rock",
    "prog rock": "rock",
    "metal": "metal",
    "heavy metal": "metal",
    "death metal": "metal",
    "black metal": "metal",
    "metalcore": "metal",
    "nu metal": "metal",
    "thrash": "metal",
    "punk": "punk",
    "pop punk": "punk",
    "hardcore punk": "punk",
    "hardcore": "punk",
    "emo": "punk",
    "indie": "indie_alt",
    "indie rock": "indie_alt",
    "indie pop": "indie_alt",
    "alternative": "indie_alt",
    "shoegaze": "indie_alt",
    "dream pop": "indie_alt",
    "britpop": "indie_alt",
    "jazz": "jazz",
    "bebop": "jazz",
    "swing": "jazz",
    "fusion": "jazz",
    "smooth jazz": "jazz",
    "big band": "jazz",
    "classical": "classical_orchestral",
    "orchestral": "classical_orchestral",
    "orchestra": "classical_orchestral",
    "baroque": "classical_orchestral",
    "romantic": "classical_orchestral",
    "opera": "classical_orchestral",
    "symphony": "classical_orchestral",
    "chamber music": "classical_orchestral",
    "soundtrack": "classical_orchestral",
    "score": "classical_orchestral",
    "film score": "classical_orchestral",
    "acoustic": "acoustic_folk",
    "folk": "acoustic_folk",
    "singer-songwriter": "acoustic_folk",
    "singer songwriter": "acoustic_folk",
    "americana": "acoustic_folk",
    "bluegrass": "acoustic_folk",
    "country": "country",
    "country pop": "country",
    "outlaw country": "country",
    "reggae": "reggae_dancehall",
    "dancehall": "reggae_dancehall",
    "ska": "reggae_dancehall",
    "dub": "reggae_dancehall",
    "roots reggae": "reggae_dancehall",
    "latin": "latin_reggaeton",
    "reggaeton": "latin_reggaeton",
    "latin pop": "latin_reggaeton",
    "salsa": "latin_reggaeton",
    "bachata": "latin_reggaeton",
    "cumbia": "latin_reggaeton",
    "bossa nova": "latin_reggaeton",
    "lo-fi": "lofi_chill",
    "lofi": "lofi_chill",
    "lo-fi hip hop": "lofi_chill",
    "chillhop": "lofi_chill",
    "chill": "lofi_chill",
    "ambient": "ambient_drone",
    "drone": "ambient_drone",
    "new age": "ambient_drone",
    "meditation": "ambient_drone",
}


@dataclass(frozen=True, slots=True)
class GenreChoice:
    """A resolved genre mix: ``(profile key, weight)`` pairs plus its source."""

    mix: tuple[tuple[str, float], ...] = ()
    source: str = "none"

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key, _weight in self.mix)

    @property
    def detected(self) -> bool:
        return bool(self.mix)

    @property
    def is_neutral(self) -> bool:
        return not self.mix or self.mix[0][0] == "neutral"

    def label(self, *, max_auto: int = MAX_AUTO_GENRES) -> str:
        if not self.detected:
            return "Neutral"
        top = self.mix[:max_auto]
        if len(top) == 1:
            return GENRE_PROFILES[top[0][0]].label
        parts = []
        for key, weight in top:
            parts.append(f"{GENRE_PROFILES[key].label} ({int(round(weight * 100))}%)")
        return " + ".join(parts)


def _normalise(text: str) -> str:
    return " ".join(str(text).lower().replace("_", " ").split())


def _match_alias(text: str) -> str | None:
    """Best-effort alias match for one raw genre name."""
    candidate = _normalise(text)
    if not candidate:
        return None
    if candidate in GENRE_ALIASES:
        return GENRE_ALIASES[candidate]
    if candidate in GENRE_PROFILES:
        return candidate
    parts = [part.strip() for part in candidate.replace(";", ",").replace("&", ",").split(",")]
    parts = [p for part in parts for p in part.split("/")]
    for part in parts:
        part = part.strip()
        if part in GENRE_ALIASES:
            return GENRE_ALIASES[part]
        if part in GENRE_PROFILES:
            return part
    longest = None
    for alias, key in GENRE_ALIASES.items():
        if alias in candidate and (longest is None or len(alias) > len(longest[0])):
            longest = (alias, key)
    return longest[1] if longest else None


def resolve_genre_names(
    names: Iterable[str] | None,
    *,
    source: str = "tags",
    weights: Mapping[str, float] | None = None,
    max_genres: int = MAX_MIX_GENRES,
) -> GenreChoice:
    """Resolve raw genre strings (tags or MusicBrainz) into a weighted mix."""
    if not names:
        return GenreChoice()
    accumulated: dict[str, float] = {}
    for raw in names:
        key = _match_alias(str(raw))
        if key is None or key == "neutral":
            continue
        weight = float(weights.get(raw, 1.0)) if weights else 1.0
        accumulated[key] = accumulated.get(key, 0.0) + max(0.0, weight)
    if not accumulated:
        return GenreChoice()
    ranked = sorted(accumulated.items(), key=lambda item: item[1], reverse=True)[:max_genres]
    total = sum(weight for _key, weight in ranked) or 1.0
    mix = tuple((key, weight / total) for key, weight in ranked)
    return GenreChoice(mix=mix, source=source)


def blend_genre_bands(
    choice: GenreChoice,
    intensity: str = DEFAULT_GENRE_INTENSITY,
) -> dict[int, float]:
    """Weighted-mean blend of the chosen profiles, scaled and safely capped."""
    factor = GENRE_INTENSITIES.get(intensity, GENRE_INTENSITIES[DEFAULT_GENRE_INTENSITY])
    profiles = [GENRE_PROFILES[key] for key, _weight in choice.mix if key in GENRE_PROFILES]
    profiles = [profile for profile in profiles if profile.key != "neutral"]
    if not profiles:
        return {}
    weights = [weight for key, weight in choice.mix if key in GENRE_PROFILES and key != "neutral"]
    blend: dict[int, float] = {}
    for freq in EQ_FREQUENCIES:
        blended = sum(profile.bands.get(freq, 0.0) * weight for profile, weight in zip(profiles, weights, strict=True))
        if abs(blended) >= TOUCH_EPSILON_DB:
            blend[freq] = blended * factor
    cap = MAX_SINGLE_GAIN_DB if len(profiles) == 1 else MAX_BLEND_GAIN_DB
    blend = {freq: max(-cap, min(cap, gain)) for freq, gain in blend.items()}
    return _enforce_untouched_bands(blend)


def _enforce_untouched_bands(bands: dict[int, float]) -> dict[int, float]:
    """Keep the strongest moves and zero the weakest so bands stay untouched."""
    min_touched = len(EQ_FREQUENCIES) - MIN_UNTOUCHED_BANDS
    if len(bands) <= min_touched:
        return bands
    ranked = sorted(bands.items(), key=lambda item: abs(item[1]), reverse=True)
    return dict(ranked[:min_touched])


def genre_hpf(choice: GenreChoice) -> bool:
    """HPF engages when any chosen profile asks for it (Jazz/Classical/etc.)."""
    return any(
        GENRE_PROFILES[key].hpf_30hz for key in choice.keys if key in GENRE_PROFILES
    )


def effective_preset(base: EnhancementPreset, choice: GenreChoice) -> EnhancementPreset:
    """Apply the genre mix's width and limiter policy on top of the base preset."""
    profiles = [GENRE_PROFILES[key] for key in choice.keys if key in GENRE_PROFILES]
    if not profiles:
        return base
    profile_width = min(profile.residual_width for profile in profiles)
    if base.residual_stereo_width < 1.0:
        profile_width = min(profile_width, base.residual_stereo_width)
    width = min(WIDTH_CEILING, max(WIDTH_FLOOR, profile_width))
    ceiling = min(base.ceiling_dbfs, min(profile.limiter_ceiling_dbfs for profile in profiles))
    return replace(
        base,
        residual_stereo_width=width,
        ceiling_dbfs=ceiling,
    )


def compose_master_settings(
    user: MasteringEQSettings,
    choice: GenreChoice,
    intensity: str = DEFAULT_GENRE_INTENSITY,
) -> MasteringEQSettings:
    """Genre curve on top of the user's EQ; the user keeps trim and bypass."""
    genre_bands = blend_genre_bands(choice, intensity)
    bands = dict(user.bands)
    for freq, gain in genre_bands.items():
        bands[freq] = max(-12.0, min(12.0, bands.get(freq, 0.0) + gain))
    label = choice.label() if choice.detected else "Neutral"
    return MasteringEQSettings(
        bands=bands,
        enabled=user.enabled,
        hpf_30hz=user.hpf_30hz or genre_hpf(choice),
        output_trim_db=user.output_trim_db,
        preset_name=f"{label} · {intensity.title()}",
    )


def recipe_line(
    choice: GenreChoice,
    intensity: str = DEFAULT_GENRE_INTENSITY,
    *,
    ceiling_dbfs: float | None = None,
) -> str:
    """Human-readable account of the genre moves, for the deck recipe label."""
    if not choice.detected:
        return "Genre: Neutral — no colour applied."
    moves = blend_genre_bands(choice, intensity)
    top = sorted(moves.items(), key=lambda item: abs(item[1]), reverse=True)[:3]
    rendered = " · ".join(f"{gain:+.1f} dB @ {freq} Hz" for freq, gain in top) or "no tonal moves"
    parts = [
        f"Genre: {GENRE_PROFILES[choice.keys[0]].label}" if len(choice.keys) == 1 else f"Genre mix: {choice.label()}",
        intensity.title(),
        rendered,
    ]
    if ceiling_dbfs is not None:
        parts.append(f"limiter {ceiling_dbfs:.1f} dBFS")
    return " · ".join(parts)


_GENRE_TAG_KEYS = frozenset({"genre", "tcon", "©gen", "gnre"})


def _collect_genre_strings(node: Any, out: list[str], *, in_genre: bool = False) -> None:
    """Depth-first hunt for genre-ish tags (flat mutagen dicts or ffprobe JSON).

    Only strings inside a genre-tagged key are harvested: titles, artists and
    comments must never masquerade as genres.
    """
    if isinstance(node, Mapping):
        for key, value in node.items():
            key_is_genre = in_genre or _normalise(str(key)) in _GENRE_TAG_KEYS
            _collect_genre_strings(value, out, in_genre=key_is_genre)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _collect_genre_strings(item, out, in_genre=in_genre)
    elif in_genre and node is not None and str(node).strip():
        out.append(str(node))


def choices_from_tags(tags: Mapping[str, Any]) -> GenreChoice:
    """Resolve genre candidates from a tag mapping (ID3, ffprobe or yt-dlp)."""
    candidates: list[str] = []
    _collect_genre_strings(tags, candidates)
    return resolve_genre_names(candidates, source="tags")


__all__ = [
    "DEFAULT_GENRE_INTENSITY",
    "GENRE_ALIASES",
    "GENRE_INTENSITIES",
    "GENRE_PROFILES",
    "MAX_AUTO_GENRES",
    "MAX_BLEND_GAIN_DB",
    "MAX_MIX_GENRES",
    "MAX_PROFILE_BANDS",
    "MAX_SINGLE_GAIN_DB",
    "MIN_UNTOUCHED_BANDS",
    "TOUCH_EPSILON_DB",
    "GenreChoice",
    "GenreProfile",
    "blend_genre_bands",
    "choices_from_tags",
    "compose_master_settings",
    "effective_preset",
    "genre_hpf",
    "recipe_line",
    "resolve_genre_names",
]
