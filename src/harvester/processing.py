"""
Processing presets — which pipeline stages run for a track.

A preset is the *processing* axis, orthogonal to the sourcing axis
(``slskd.acquisition_mode``, which decides where a file comes from). Three
levels are exposed, in ascending cost:

- ``fetch_only``   acquire → validate/normalize → tags + AcoustID. No stems,
                   no lanes, no restoration. Seconds of wall time, ~0.2 GB.
- ``standard``     4-source separation (BS-RoFormer → HDEMUCS) plus the
                   song-driven lanes of ``docs/12 §6``. The default.
- ``neural_full``  adds the 6-source extras (guitar / piano), the MusicBrainz
                   credit inventory and instrument tagging on top of
                   ``standard``.

The separator's engine fallback chain (neural → hdemucs → eco) is deliberately
*not* a preset: it decides **how** a stage runs, never **whether** it runs.
Whenever a stage degrades, the run report says so out loud — see
``engine_note`` — because a silent fallback is what made the old mode set
confusing (``eco`` is a 2-layer mid/side fallback, not a "fast" mode).

Pure data — no numpy, no torch, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_PRESET",
    "DEFAULT_SEP_TYPE",
    "ENGINE_NOTES",
    "HOSTED_RAW_TOKEN",
    "PRESETS",
    "TAG_THRESHOLD",
    "ProcessingPreset",
    "degraded",
    "engine_note",
    "get_preset",
    "next_preset",
    "normalize_preset",
    "preset_names",
]

# Filename token that marks a hosted (MVSEP) raw stem: a hosted run writes
# ``{input_stem}_{mode}_hosted_raw_{lane_key}.wav`` next to the local stems, so
# lane discovery can tell cloud stems from local ones (docs/13 D26).
HOSTED_RAW_TOKEN = "_hosted_raw_"

# Default hosted separation model (docs/13 D26). The value is a key of
# ``services.mvsep.SEP_TYPES`` — the lead/back-vocal karaoke split, which is the
# hosted output nothing local can produce.
DEFAULT_SEP_TYPE = "karaoke_lead_back"

# Mean per-window CLAP label share a label needs before it is reported as a tag
# (``[processing] tag_threshold``). The share is the softmax mass across the
# label prompts — relative, not a calibrated probability — and an even spread
# over the 12 labels is ≈8 %, so 15 % means "at least twice the even share".
TAG_THRESHOLD: float = 0.15


@dataclass(frozen=True, slots=True)
class ProcessingPreset:
    """One processing level and the stages it enables."""

    name: str
    label: str
    detail: str
    separation: bool  # run stem separation at all
    extra_sources: bool  # include the 6-source extras (guitar / piano)
    credits: bool  # MusicBrainz credit inventory for the lane plan
    tags: bool  # instrument tagging pass
    enhancement: bool  # restoration / super-resolution stages
    est_ram_gb: float  # rough resident-memory ceiling for the UI

    @property
    def summary(self) -> str:
        """One-line cost/benefit note for the status line."""
        if not self.separation:
            return f"{self.label}: fetch + tag only (~{self.est_ram_gb:.1f} GB, no lanes)"
        lanes = "4-source + extras" if self.extra_sources else "4-source"
        return f"{self.label}: {lanes} lanes (~{self.est_ram_gb:.1f} GB)"


PRESETS: dict[str, ProcessingPreset] = {
    "fetch_only": ProcessingPreset(
        name="fetch_only",
        label="FETCH ONLY",
        detail="Acquire, normalize, tag. No separation, no lane grid.",
        separation=False,
        extra_sources=False,
        credits=False,
        tags=False,
        enhancement=False,
        est_ram_gb=0.2,
    ),
    "standard": ProcessingPreset(
        name="standard",
        label="STANDARD",
        detail="4-source separation + song-driven lanes.",
        separation=True,
        extra_sources=False,
        credits=True,
        tags=False,
        enhancement=False,
        est_ram_gb=1.7,
    ),
    "neural_full": ProcessingPreset(
        name="neural_full",
        label="NEURAL FULL",
        detail="Adds 6-source extras (guitar/piano), credits and tagging.",
        separation=True,
        extra_sources=True,
        credits=True,
        tags=True,
        enhancement=True,
        est_ram_gb=2.5,
    ),
}

DEFAULT_PRESET = "standard"

# How each separator engine should be described when it is reported back. The
# eco entry is the loud one on purpose: it is the last-resort fallback, and a
# run that lands there must never look like a normal neural run.
ENGINE_NOTES: dict[str, str] = {
    "bs_roformer": "BS-RoFormer (neural)",
    "neural": "BS-RoFormer (neural)",
    "ensemble": "BS-RoFormer + HDEMUCS (ensemble)",
    "hdemucs": "HDEMUCS (neural)",
    "eco": "eco DSP fallback — mid/side cannot split drums/bass/other",
    "unknown": "unknown engine",
}


def preset_names() -> tuple[str, ...]:
    """Preset keys in ascending cost order."""
    return tuple(PRESETS)


def normalize_preset(name: str | None) -> str:
    """Coerce a preset name to a known key (unknown/empty → the default)."""
    key = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return key if key in PRESETS else DEFAULT_PRESET


def get_preset(name: str | None) -> ProcessingPreset:
    """Return the preset for ``name``, falling back to the default."""
    return PRESETS[normalize_preset(name)]


def next_preset(name: str | None) -> str:
    """Cycle to the next preset (UI selector helper)."""
    keys = preset_names()
    return keys[(keys.index(normalize_preset(name)) + 1) % len(keys)]


def engine_note(engine: str | None) -> str:
    """Describe the engine that actually ran, degrading loudly."""
    key = str(engine or "").strip().lower()
    if key in ENGINE_NOTES:
        return ENGINE_NOTES[key]
    if key.startswith("bs_roformer+"):
        return f"BS-RoFormer + {key.split('+', 1)[1]} extras (neural)"
    return key or ENGINE_NOTES["unknown"]


def degraded(engine: str | None) -> bool:
    """True when the run fell back to a non-neural engine."""
    return str(engine or "").strip().lower() == "eco"
