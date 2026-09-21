"""
Lane provenance — where every Layer Studio row came from.

The lane grid is only trustworthy if each row can say what it *is*. This module
turns the detector's report plus the MusicBrainz credit inventory into a
``LanePlan``: one entry per lane with an origin, a confidence and a note, so the
workbench and the detached terminal can label rows instead of showing anonymous
levels.

Origins:

- ``separator``     a stem a separation model produced (vocals / drums / bass / other).
- ``dsp-split``     a complementary crossover split of a separator stem
                    (drums → kick/snare/hats), summed back exactly.
- ``extra-source``  an extra model lane (guitar / piano from a 6-source pass).
- ``mix``           the whole-track bus lane of the eco fallback.
- ``credit-only``   documented in MusicBrainz but not rendered by any separator
                    (sax, violin, …). These carry **no audio row** on purpose.
- ``tag-only``      audible to the tagger but not produced as a stem.

Torch-free and dependency-free: plain data in, plain data out.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

__all__ = [
    "CONFIDENCE_BY_ORIGIN",
    "CREDIT_LANE_HINTS",
    "LanePlan",
    "LanePlanEntry",
    "ORIGIN_CREDIT",
    "ORIGIN_EXTRA",
    "ORIGIN_HOSTED",
    "ORIGIN_MIX",
    "ORIGIN_SEPARATOR",
    "ORIGIN_SPLIT",
    "ORIGIN_TAG",
    "ORIGIN_LABELS",
    "decode_plan",
    "encode_plan",
    "lane_for_credit",
    "plan_lanes",
]

ORIGIN_SEPARATOR = "separator"
ORIGIN_SPLIT = "dsp-split"
ORIGIN_EXTRA = "extra-source"
ORIGIN_HOSTED = "hosted"
ORIGIN_MIX = "mix"
ORIGIN_CREDIT = "credit-only"
ORIGIN_TAG = "tag-only"

ORIGIN_LABELS: dict[str, str] = {
    ORIGIN_SEPARATOR: "separator",
    ORIGIN_SPLIT: "DSP split",
    ORIGIN_EXTRA: "6-source model",
    ORIGIN_HOSTED: "hosted (MVSEP)",
    ORIGIN_MIX: "mix bus",
    ORIGIN_CREDIT: "credits only",
    ORIGIN_TAG: "tags only",
}

# Confidence is about *how the row was made*, not how good the song is: a
# separator stem is a model output, a DSP split is exact but narrower, an extra
# 6-source lane is a low-SDR model output (guitar ≈ 2.6 dB SDR in public
# benchmarks), a hosted lane is a top-tier cloud model output, and a
# credit-only row has no audio at all.
CONFIDENCE_BY_ORIGIN: dict[str, str] = {
    ORIGIN_SEPARATOR: "high",
    ORIGIN_MIX: "high",
    ORIGIN_HOSTED: "high",
    ORIGIN_SPLIT: "medium",
    ORIGIN_EXTRA: "low",
    ORIGIN_TAG: "low",
    ORIGIN_CREDIT: "none",
}

# MusicBrainz credit keywords → the lane that can actually render them. First
# match wins, so the more specific keywords come first.
CREDIT_LANE_HINTS: tuple[tuple[str, str], ...] = (
    ("lead vocal", "vocals"),
    ("background vocal", "vocals"),
    ("backing vocal", "vocals"),
    ("choir", "vocals"),
    ("harmon", "vocals"),
    ("vocal", "vocals"),
    ("drum machine", "drums"),
    ("drum", "drums"),
    ("percussion", "drums"),
    ("tambourine", "drums"),
    ("double bass", "bass"),
    ("bass", "bass"),
    ("guitar", "guitar"),
    ("piano", "piano"),
    ("electric piano", "piano"),
    ("keyboard", "other"),
    ("synthes", "other"),
    ("programming", "other"),
    ("strings", "other"),
    ("organ", "other"),
)


def lane_for_credit(instrument: str) -> str | None:
    """Map a MusicBrainz instrument credit to a lane key, if one can render it."""
    text = str(instrument or "").strip().lower()
    if not text:
        return None
    for keyword, lane in CREDIT_LANE_HINTS:
        if keyword in text:
            return lane
    return None


def _credit_name(credit: object) -> str:
    """Instrument label of a credit (accepts plain strings too)."""
    if isinstance(credit, str):
        return credit.strip()
    return str(getattr(credit, "name", "") or "").strip()


def _credit_artist(credit: object) -> str:
    if isinstance(credit, str):
        return ""
    return str(getattr(credit, "artist", "") or "").strip()


def _credit_text(credit: object) -> str:
    name = _credit_name(credit)
    artist = _credit_artist(credit)
    return f"{name} — {artist}" if artist else name


@dataclass(frozen=True, slots=True)
class LanePlanEntry:
    """One planned lane row: what it is, where it came from, how much to trust it."""

    name: str
    origin: str
    confidence: str
    note: str = ""

    @property
    def origin_label(self) -> str:
        return ORIGIN_LABELS.get(self.origin, self.origin)

    @property
    def rendered(self) -> bool:
        """True when this lane carries an audio row in the grid."""
        return self.origin not in (ORIGIN_CREDIT, ORIGIN_TAG)

    def describe(self) -> str:
        parts = [f"{self.name.upper()} [{self.origin_label}, {self.confidence}]"]
        if self.note:
            parts.append(self.note)
        return " · ".join(parts)


@dataclass(slots=True)
class LanePlan:
    """Provenance for one track's lane set plus the credit inventory behind it."""

    entries: tuple[LanePlanEntry, ...] = ()
    singer_count: int | None = None
    credit_instruments: tuple[str, ...] = ()
    tag_labels: tuple[str, ...] = ()
    measured_speakers: int | None = None

    def entry(self, name: str) -> LanePlanEntry | None:
        for item in self.entries:
            if item.name == name:
                return item
        return None

    def origin_of(self, name: str) -> str:
        item = self.entry(name)
        return item.origin if item else ""

    def confidence_of(self, name: str) -> str:
        item = self.entry(name)
        return item.confidence if item else ""

    def note_of(self, name: str) -> str:
        item = self.entry(name)
        return item.note if item else ""

    @property
    def rendered_lanes(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.entries if item.rendered)

    @property
    def missing(self) -> tuple[LanePlanEntry, ...]:
        """Credited/tagged content with no audio row (shown, never faked)."""
        return tuple(item for item in self.entries if not item.rendered)

    def summary(self) -> str:
        """Compact status-line account of the plan."""
        parts: list[str] = []
        counts: dict[str, int] = {}
        for item in self.entries:
            counts[item.origin] = counts.get(item.origin, 0) + 1
        for origin in (
            ORIGIN_SEPARATOR,
            ORIGIN_SPLIT,
            ORIGIN_EXTRA,
            ORIGIN_HOSTED,
            ORIGIN_MIX,
            ORIGIN_TAG,
            ORIGIN_CREDIT,
        ):
            if counts.get(origin):
                parts.append(f"{counts[origin]} {ORIGIN_LABELS[origin]}")
        text = " · ".join(parts)
        if self.singer_count:
            text += f" · {self.singer_count} singers"
        if self.measured_speakers:
            text += f" · {self.measured_speakers} speakers measured"
        return text


def plan_lanes(
    lane_names: Sequence[str],
    *,
    splits: dict[str, tuple[str, ...]] | None = None,
    extras: Iterable[str] = (),
    hosted: Iterable[str] = (),
    kept_whole: Iterable[str] = (),
    credit_instruments: Sequence[object] = (),
    singer_count: int | None = None,
    tag_labels: Sequence[str] = (),
    measured_speakers: int | None = None,
) -> LanePlan:
    """Build the provenance plan for one track's lane set.

    ``lane_names`` is the lane order the grid will render (from
    ``LayerTrack.active_layers``); ``splits`` / ``extras`` / ``hosted`` /
    ``kept_whole`` come from ``dynamic_layers.LaneReport``;
    ``credit_instruments`` is the MusicBrainz instrument inventory (objects with
    ``name``/``artist`` or plain strings).
    """
    split_children: dict[str, str] = {}
    for family, children in (splits or {}).items():
        for child in children:
            split_children[child] = family
    extra_set = {str(name) for name in extras}
    hosted_set = {str(name) for name in hosted}
    whole_set = {str(name) for name in kept_whole}

    entries: list[LanePlanEntry] = []
    claimed_credits: set[int] = set()
    credits = list(credit_instruments)

    for name in lane_names:
        note = ""
        if name in hosted_set:
            origin = ORIGIN_HOSTED
            note = "uploaded to MVSEP — hosted separation stem"
        elif name in extra_set:
            origin = ORIGIN_EXTRA
        elif name in split_children:
            origin = ORIGIN_SPLIT
            note = f"from {split_children[name]} (complementary crossover)"
        elif name == "mix":
            origin = ORIGIN_MIX
        else:
            origin = ORIGIN_SEPARATOR
            if name in whole_set:
                note = "kept whole — no audible split in this song"

        # Annotate a rendered lane with the credit that documents it.
        for idx, credit in enumerate(credits):
            if idx in claimed_credits:
                continue
            if lane_for_credit(_credit_name(credit)) == name:
                claimed_credits.add(idx)
                text = _credit_text(credit)
                note = f"MusicBrainz credit: {text}" if not note else f"{note} · credit: {text}"
                break

        entries.append(
            LanePlanEntry(
                name=name,
                origin=origin,
                confidence=CONFIDENCE_BY_ORIGIN.get(origin, "medium"),
                note=note,
            )
        )

    # Credited instruments nothing can render — listed, but with no audio row.
    for idx, credit in enumerate(credits):
        if idx in claimed_credits:
            continue
        text = _credit_text(credit)
        entries.append(
            LanePlanEntry(
                name=_credit_name(credit) or text,
                origin=ORIGIN_CREDIT,
                confidence=CONFIDENCE_BY_ORIGIN[ORIGIN_CREDIT],
                note=f"documented in MusicBrainz ({text}) — no separator renders it",
            )
        )

    # Tags annotate a rendered lane when one can carry them (guitar tag → guitar
    # row); otherwise they become a "tags only" row with no audio (docs/13 D25).
    rendered_index = {entry.name: index for index, entry in enumerate(entries) if entry.rendered}
    for label in tag_labels:
        text = str(label).strip()
        if not text:
            continue
        lane = lane_for_credit(text)
        index = rendered_index.get(lane) if lane else None
        if index is not None:
            current = entries[index]
            note = f"{current.note} · CLAP tag: {text}" if current.note else f"CLAP tag: {text}"
            entries[index] = replace(current, note=note)
            continue
        entries.append(
            LanePlanEntry(
                name=text,
                origin=ORIGIN_TAG,
                confidence=CONFIDENCE_BY_ORIGIN[ORIGIN_TAG],
                note="audible to the tagger, not produced as a stem",
            )
        )

    return LanePlan(
        entries=tuple(entries),
        singer_count=singer_count,
        credit_instruments=tuple(_credit_name(c) for c in credits if _credit_name(c)),
        tag_labels=tuple(str(label) for label in tag_labels),
        measured_speakers=measured_speakers,
    )


def encode_plan(plan: LanePlan | None) -> list[dict[str, object]]:
    """JSON-safe plan rows for the layer sidecar."""
    if plan is None:
        return []
    return [
        {
            "name": item.name,
            "origin": item.origin,
            "confidence": item.confidence,
            "note": item.note,
        }
        for item in plan.entries
    ]


def decode_plan(
    data: object,
    *,
    singer_count: int | None = None,
    credit_instruments: Sequence[str] = (),
    tag_labels: Sequence[str] = (),
    measured_speakers: int | None = None,
) -> LanePlan:
    """Rehydrate a plan from sidecar rows (unknown/missing data → empty plan)."""
    entries: list[LanePlanEntry] = []
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            entries.append(
                LanePlanEntry(
                    name=name,
                    origin=str(row.get("origin", "") or ORIGIN_SEPARATOR),
                    confidence=str(row.get("confidence", "") or "medium"),
                    note=str(row.get("note", "") or ""),
                )
            )
    return LanePlan(
        entries=tuple(entries),
        singer_count=singer_count,
        credit_instruments=tuple(str(c) for c in credit_instruments),
        tag_labels=tuple(str(label) for label in tag_labels),
        measured_speakers=measured_speakers,
    )


# Kept for symmetry with other modules that expose a default empty plan.
EMPTY_PLAN: LanePlan = LanePlan(
    entries=(),
    singer_count=None,
    credit_instruments=(),
    tag_labels=(),
    measured_speakers=None,
)
