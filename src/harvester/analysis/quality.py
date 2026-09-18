"""Source-quality evidence and replacement decisions for library upgrades.

This module compares sources without pretending that a higher bitrate container recovers
information. It is deliberately metadata-driven; the pipeline must still validate identity,
decodeability, and tags before an atomic replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReplacementDecision(StrEnum):
    KEEP = "KEEP"
    PREVIEW = "PREVIEW"
    REPLACE = "REPLACE"


@dataclass(frozen=True, slots=True)
class QualityEvidence:
    """Measured or probed evidence about one candidate audio source."""

    codec: str
    bitrate_kbps: int | None = None
    sample_rate_hz: int | None = None
    duration_s: float | None = None
    channels: int | None = None
    cutoff_hz: float | None = None
    identity_match: bool = False
    decode_ok: bool = True
    synthetic_high_band: bool = False

    @property
    def lossless(self) -> bool:
        return self.codec.lower() in {"flac", "alac", "wav", "aiff", "wavpack"}

    @property
    def lossy(self) -> bool:
        return not self.lossless


@dataclass(frozen=True, slots=True)
class ReplacementAssessment:
    """Explain whether a candidate is safe to offer as a replacement."""

    decision: ReplacementDecision
    current_score: float
    candidate_score: float
    reasons: tuple[str, ...]


def assess_replacement(
    current: QualityEvidence,
    candidate: QualityEvidence,
    *,
    minimum_improvement: float = 25.0,
    allow_synthetic: bool = False,
) -> ReplacementAssessment:
    """Assess a candidate without treating upconversion as quality recovery.

    Identity and decodeability are hard requirements. A candidate that only has a higher
    nominal bitrate than the current lossy file is not automatically better.
    """

    if not candidate.identity_match:
        return _assessment(ReplacementDecision.KEEP, current, candidate, "identity mismatch")
    if not candidate.decode_ok:
        return _assessment(ReplacementDecision.KEEP, current, candidate, "candidate failed decode")
    if candidate.synthetic_high_band and not allow_synthetic:
        return _assessment(
            ReplacementDecision.PREVIEW,
            current,
            candidate,
            "synthetic band requires review",
        )

    current_score = quality_score(current)
    candidate_score = quality_score(candidate)
    improvement = candidate_score - current_score
    reasons: list[str] = []
    if candidate.lossless and current.lossy:
        reasons.append("lossless source replaces lossy source")
    elif candidate.codec.lower() != current.codec.lower():
        reasons.append(f"source codec changes {current.codec} -> {candidate.codec}")
    if candidate.bitrate_kbps and current.bitrate_kbps:
        reasons.append(f"bitrate evidence {current.bitrate_kbps}k -> {candidate.bitrate_kbps}k")
    if improvement < minimum_improvement:
        reasons.append("quality evidence is not materially better")
        return ReplacementAssessment(
            ReplacementDecision.PREVIEW,
            current_score,
            candidate_score,
            tuple(reasons),
        )
    return ReplacementAssessment(
        ReplacementDecision.REPLACE,
        current_score,
        candidate_score,
        tuple(reasons) or ("candidate has materially stronger quality evidence",),
    )


def quality_score(evidence: QualityEvidence) -> float:
    """Return a conservative comparable score; synthetic high bands never add quality."""

    codec_score = {
        "flac": 100.0,
        "alac": 100.0,
        "wav": 100.0,
        "aiff": 100.0,
        "wavpack": 100.0,
        "opus": 70.0,
        "aac": 65.0,
        "mp3": 50.0,
        "vorbis": 55.0,
    }.get(evidence.codec.lower(), 40.0)
    bitrate_score = min(float(evidence.bitrate_kbps or 0) / 10.0, 32.0)
    cutoff_score = min(float(evidence.cutoff_hz or 0) / 1_000.0, 24.0)
    return codec_score + bitrate_score + cutoff_score


def _assessment(
    decision: ReplacementDecision,
    current: QualityEvidence,
    candidate: QualityEvidence,
    reason: str,
) -> ReplacementAssessment:
    return ReplacementAssessment(
        decision,
        quality_score(current),
        quality_score(candidate),
        (reason,),
    )


__all__ = [
    "QualityEvidence",
    "ReplacementAssessment",
    "ReplacementDecision",
    "assess_replacement",
    "quality_score",
]
