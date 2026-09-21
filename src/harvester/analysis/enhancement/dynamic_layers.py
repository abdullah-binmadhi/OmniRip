"""
Dynamic layer detection — song-driven lane generation for the Layer Studio.

The static four-stem model (vocals / bass / drums / other) is the *source* set;
this module decides which **lanes** the Layer Studio actually shows by splitting
each source into disjoint sub-lanes with the zero-phase complementary DSP
crossover in ``dsp.split_bands`` (sum of children == parent, so the mix
reconstruction budget of docs/12 §5 still holds) and then keeping a split only
when every child carries audible content in *this* song.

Drums → kick / snare / hats, bass → sub-bass / bass. A song with no drum
content keeps a single ``drums`` lane; a busier arrangement expands to 7-10
lanes. Extra neural sources (guitar / piano from a 6-source model such as
``htdemucs_6s``) become lanes automatically when their raw stem files are
present in the stem directory.

Torch-free: numpy + soundfile only, mirroring ``layers.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.dsp import split_bands

logger = logging.getLogger(__name__)

SEGMENT_SIZE_S: float = 1.0

# Presence gate: a lane is real only when it is audible for a meaningful part
# of the song, not just bleed/crosstalk.
PRESENCE_ACTIVE_DB: float = -45.0  # a second counts as "active" above this RMS
PRESENCE_MIN_RATIO: float = 0.05  # ≥5% of the timeline must be active
PRESENCE_MEAN_DB: float = -50.0  # and the lane's mean RMS must clear this


@dataclass(frozen=True, slots=True)
class LaneSpec:
    """One dynamically derived lane: a filtered view of a parent source lane."""

    name: str  # lane key used by the UI / edit plan
    label: str  # track-header label
    family: str  # parent lane this lane is carved from
    detail: str  # FL Studio-style header subtitle
    color: str
    splits: tuple[tuple[float, str], ...]  # ordered (cutoff_hz, "low"|"high")
    file_token: str | None = None  # layer file name token (defaults to name)

    @property
    def token(self) -> str:
        return self.file_token or self.name


# Child lanes per family. Each family's children partition the parent exactly
# (successive complementary crossovers), so replacing the parent with its
# children preserves the mix reconstruction invariant.
FAMILY_SPLITS: dict[str, tuple[LaneSpec, ...]] = {
    "drums": (
        LaneSpec(
            name="kick",
            label="KICK",
            family="drums",
            detail="Drums › Low Punch",
            color="#ff5555",
            splits=((130.0, "low"),),
        ),
        LaneSpec(
            name="snare",
            label="SNARE",
            family="drums",
            detail="Drums › Body & Crack",
            color="#ff9955",
            splits=((130.0, "high"), (5000.0, "low")),
        ),
        LaneSpec(
            name="hats",
            label="HATS",
            family="drums",
            detail="Drums › Cymbals / Air",
            color="#ffdd66",
            splits=((130.0, "high"), (5000.0, "high")),
        ),
    ),
    "bass": (
        LaneSpec(
            name="sub_bass",
            label="SUB BASS",
            family="bass",
            detail="Bass › Sub Frequencies",
            color="#2266dd",
            splits=((80.0, "low"),),
        ),
        LaneSpec(
            name="bass",
            label="BASS",
            family="bass",
            detail="Bass › Body & Growl",
            color="#3388ff",
            splits=((80.0, "high"),),
            file_token="bass_upper",
        ),
    ),
}

# Optional extra neural sources (6-source models such as htdemucs_6s). When the
# raw stem exists in the stem dir it becomes a first-class lane.
EXTRA_LANE_SOURCES: dict[str, str] = {
    "guitar": "_raw_guitar.wav",
    "piano": "_raw_piano.wav",
}


@dataclass(slots=True)
class LaneReport:
    """What the detector decided for one song (surfaced in the UI status line)."""

    lanes: tuple[str, ...] = ()
    splits: dict[str, tuple[str, ...]] = field(default_factory=dict)
    extras: tuple[str, ...] = ()
    kept_whole: tuple[str, ...] = ()

    def summary(self) -> str:
        parts: list[str] = []
        for family, children in self.splits.items():
            parts.append(f"{family} → {'/'.join(children)}")
        parts.extend(f"+{name}" for name in self.extras)
        parts.extend(f"{family} (whole)" for family in self.kept_whole)
        return " · ".join(parts)


def lane_transition_hz(cutoff_hz: float) -> float:
    """Tight raised-cosine width so neighbouring lanes stay separated.

    ``dsp.split_bands`` defaults to a wide 500 Hz mastering crossover; lanes
    want narrower edges (a 500 Hz skirt around an 80 Hz sub-bass split would
    swallow the whole bass guitar).
    """
    return float(min(500.0, max(50.0, cutoff_hz * 0.6)))


def apply_lane_path(
    audio: np.ndarray, sr: int, splits: tuple[tuple[float, str], ...]
) -> np.ndarray:
    """Filter ``audio`` through an ordered list of complementary crossovers."""
    band = audio
    for cutoff_hz, side in splits:
        low, high = split_bands(
            band,
            cutoff_hz=cutoff_hz,
            sample_rate=sr,
            transition_width_hz=lane_transition_hz(cutoff_hz),
        )
        band = low if side == "low" else high
    return np.asarray(band, dtype=np.float32)


def lane_envelope(
    audio: np.ndarray, sr: int, segment_size_s: float = SEGMENT_SIZE_S
) -> np.ndarray:
    """Per-second RMS in dBFS for an in-memory (channels, samples) array."""
    mono = np.asarray(audio, dtype=np.float32)
    if mono.ndim > 1:
        mono = mono.mean(axis=0)
    seg_len = max(1, int(segment_size_s * sr))
    n_segments = max(1, int(np.ceil(mono.shape[0] / seg_len)))
    padded = np.zeros(n_segments * seg_len, dtype=np.float32)
    padded[: mono.shape[0]] = mono[: n_segments * seg_len]
    segs = padded.reshape(n_segments, seg_len).astype(np.float64)
    rms = np.sqrt(np.mean(segs**2, axis=1) + 1e-12)
    return np.clip(20.0 * np.log10(np.maximum(rms, 1e-6)), -60.0, 0.0).astype(np.float32)


def lane_presence(
    audio: np.ndarray, sr: int, segment_size_s: float = SEGMENT_SIZE_S
) -> tuple[float, float]:
    """Return (active second ratio, mean RMS dBFS) for a candidate lane."""
    rms = lane_envelope(audio, sr, segment_size_s)
    if rms.size == 0:
        return 0.0, -60.0
    return float(np.mean(rms > PRESENCE_ACTIVE_DB)), float(rms.mean())


def is_present(
    audio: np.ndarray, sr: int, segment_size_s: float = SEGMENT_SIZE_S
) -> bool:
    """True when the lane carries real content across the song (not bleed)."""
    active, mean_db = lane_presence(audio, sr, segment_size_s)
    return active >= PRESENCE_MIN_RATIO and mean_db >= PRESENCE_MEAN_DB


def _load_lane(path: Path, sample_rate: int) -> tuple[np.ndarray, int]:
    from harvester.analysis.enhancement.stem_separator import load_audio_numpy

    return load_audio_numpy(path, target_sr=sample_rate)


def _save_lane(audio: np.ndarray, path: Path, sr: int) -> None:
    from harvester.analysis.enhancement.stem_separator import save_audio_numpy

    save_audio_numpy(audio, path, sr)


def child_lane_path(parent_path: Path, spec: LaneSpec) -> Path:
    """``{suffix}_layer_{family}.wav`` → ``{suffix}_layer_{spec.token}.wav``."""
    token = f"_layer_{spec.family}"
    if token in parent_path.name:
        return parent_path.with_name(parent_path.name.replace(token, f"_layer_{spec.token}"))
    return parent_path.with_name(f"{parent_path.stem}{token}_{spec.token}.wav")


def _split_family(
    family: str,
    parent_path: Path,
    sample_rate: int,
    segment_size_s: float,
) -> dict[str, Path]:
    """Split one family into its child lanes on disk.

    Returns the child lane → path map, or an empty dict when a child turned out
    to be silent in this song (the parent lane is then kept whole).
    """
    specs = FAMILY_SPLITS[family]
    child_paths = {spec.name: child_lane_path(parent_path, spec) for spec in specs}
    cached = all(p.exists() and p.stat().st_size > 44 for p in child_paths.values())

    if not cached:
        try:
            parent_audio, sr = _load_lane(parent_path, sample_rate)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("dynamic lane split skipped for %s: %s", family, exc)
            return {}
        children: dict[str, np.ndarray] = {}
        for spec in specs:
            child_audio = apply_lane_path(parent_audio, sr, spec.splits)
            if not is_present(child_audio, sr, segment_size_s):
                logger.debug(
                    "dynamic lane %s absent in this song — keeping %s whole",
                    spec.name,
                    family,
                )
                return {}
            children[spec.name] = child_audio
        del parent_audio
        for name, audio in children.items():
            try:
                _save_lane(audio, child_paths[name], sr)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("dynamic lane save failed for %s: %s", name, exc)
                return {}

    # Validate cached lanes too, so a stale cache cannot resurrect a lane this
    # song does not contain.
    for path in child_paths.values():
        try:
            audio, sr = _load_lane(path, sample_rate)
        except Exception:  # pragma: no cover - defensive
            return {}
        if not is_present(audio, sr, segment_size_s):
            return {}
    return child_paths


def expand_dynamic_lanes(
    sources: dict[str, Path],
    *,
    sample_rate: int = 44100,
    segment_size_s: float = SEGMENT_SIZE_S,
    stem_dir: Path | None = None,
    suffix: str | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
) -> tuple[dict[str, Path], LaneReport]:
    """Replace splittable source lanes with their detected child lanes.

    ``sources`` maps base lane name → layer WAV path (from
    ``build_layer_sources``). Families whose children are not all audible in
    this song keep their parent lane, so the lane count is driven by the song.
    """
    if progress_callback:
        progress_callback(18.0, "Layer Studio: detecting song lanes…")

    lanes: dict[str, Path] = dict(sources)
    report = LaneReport()
    splits: dict[str, tuple[str, ...]] = {}
    kept_whole: list[str] = []

    for family in FAMILY_SPLITS:
        parent_path = lanes.get(family)
        if parent_path is None or not (parent_path.exists() and parent_path.stat().st_size > 44):
            continue
        children = _split_family(family, parent_path, sample_rate, segment_size_s)
        if not children:
            kept_whole.append(family)
            continue
        lanes.pop(family, None)
        lanes.update(children)
        splits[family] = tuple(children)
        if progress_callback:
            progress_callback(
                19.0,
                f"Layer Studio: {family} → {'/'.join(children)} detected.",
            )

    extras = _collect_extra_lanes(
        stem_dir, suffix, lanes, sample_rate=sample_rate, segment_size_s=segment_size_s
    )
    if extras:
        lanes.update(extras)

    report.splits = splits
    report.extras = tuple(extras)
    report.kept_whole = tuple(kept_whole)
    report.lanes = tuple(lanes)
    if progress_callback:
        progress_callback(20.0, "Layer Studio: song lanes ready.")
    return lanes, report


def _collect_extra_lanes(
    stem_dir: Path | None,
    suffix: str | None,
    lanes: dict[str, Path],
    *,
    sample_rate: int,
    segment_size_s: float,
) -> dict[str, Path]:
    """Pick up optional neural lanes (guitar / piano) already on disk."""
    if stem_dir is None or not suffix:
        return {}
    found: dict[str, Path] = {}
    for name, token in EXTRA_LANE_SOURCES.items():
        if name in lanes:
            continue
        raw = stem_dir / f"{suffix}{token}"
        if not (raw.exists() and raw.stat().st_size > 44):
            continue
        layer_path = stem_dir / f"{suffix}_layer_{name}.wav"
        try:
            if not (layer_path.exists() and layer_path.stat().st_size > 44):
                audio, sr = _load_lane(raw, sample_rate)
                if not is_present(audio, sr, segment_size_s):
                    continue
                _save_lane(audio, layer_path, sr)
            else:
                audio, sr = _load_lane(layer_path, sample_rate)
                if not is_present(audio, sr, segment_size_s):
                    continue
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("extra lane %s skipped: %s", name, exc)
            continue
        found[name] = layer_path
    return found


__all__ = [
    "EXTRA_LANE_SOURCES",
    "FAMILY_SPLITS",
    "LaneReport",
    "LaneSpec",
    "PRESENCE_ACTIVE_DB",
    "PRESENCE_MIN_RATIO",
    "apply_lane_path",
    "child_lane_path",
    "expand_dynamic_lanes",
    "is_present",
    "lane_envelope",
    "lane_presence",
    "lane_transition_hz",
]
