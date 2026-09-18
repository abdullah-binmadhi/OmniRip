"""P2P candidate hard filters and weighted scoring (docs/06 §7-§8)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from pathlib import Path

from harvester.models import P2PCandidate

_LOSSLESS_EXTENSIONS = {".flac", ".ape", ".wv", ".wav"}


def is_hard_filtered(candidate: P2PCandidate, *, expected_duration_s: float | None) -> bool:
    """Return whether a candidate fails the Phase 2 hard filters."""

    extension = Path(candidate.filename).suffix.lower()
    if extension != ".flac":
        return True
    if candidate.bit_depth is not None and candidate.bit_depth < 16:
        return True
    if candidate.size_bytes is not None and expected_duration_s:
        expected = expected_duration_s * 110_000
        if candidate.size_bytes < expected * 0.85 or candidate.size_bytes > expected * 1.30:
            return True
    if expected_duration_s and candidate.duration_s is not None:
        if abs(candidate.duration_s - expected_duration_s) / expected_duration_s > 0.05:
            return True
    return False


def score_candidate(
    candidate: P2PCandidate,
    *,
    expected_duration_s: float | None,
    expected_size_bytes: int | None,
) -> float:
    """Compute the documented weighted score for one candidate."""

    score = 0.0
    if candidate.bit_depth is not None:
        score += 10 if candidate.bit_depth >= 24 else 0
    if candidate.sample_rate is not None:
        score += 5 if candidate.sample_rate >= 44_100 else 0
    speed = candidate.user_speed_kbps or 0
    score += 15 if speed >= 1000 else (8 if speed >= 300 else 0)
    queue = candidate.queue_length
    if queue is not None:
        score += 10 if queue == 0 else (5 if queue <= 3 else -10 if queue > 10 else 0)
    if expected_size_bytes and candidate.size_bytes:
        ratio = candidate.size_bytes / expected_size_bytes
        score += 10 if abs(ratio - 1.0) <= 0.05 else 4 if abs(ratio - 1.0) <= 0.15 else 0
    if expected_duration_s and candidate.duration_s:
        delta = abs(candidate.duration_s - expected_duration_s) / expected_duration_s
        score += 8 if delta <= 0.01 else 3 if delta <= 0.05 else 0
    if _has_spam_hint(candidate.filename):
        score -= 20
    if _looks_transcoded(candidate.filename):
        score -= 25
    return score


def rank_candidates(
    candidates: Sequence[P2PCandidate],
    *,
    expected_duration_s: float | None,
    seed: int | None = None,
) -> list[P2PCandidate]:
    """Filter, score, sort, and deterministically tie-break candidates."""

    rng = random.Random(seed)
    ranked = [
        candidate
        for candidate in candidates
        if not is_hard_filtered(candidate, expected_duration_s=expected_duration_s)
    ]
    for candidate in ranked:
        candidate.score = score_candidate(
            candidate,
            expected_duration_s=expected_duration_s,
            expected_size_bytes=_expected_size(candidate, expected_duration_s),
        )
    ranked.sort(key=lambda item: (-item.score, -rng.random()))
    return ranked


def _expected_size(
    candidate: P2PCandidate,
    expected_duration_s: float | None,
) -> int | None:
    if expected_duration_s and candidate.size_bytes:
        return int(expected_duration_s * 110_000)
    return None


def _has_spam_hint(filename: str) -> bool:
    lowered = filename.lower()
    tokens = ("www.", "http", "transcode", "remix", "320", "mp3")
    return any(token in lowered for token in tokens)


def _looks_transcoded(filename: str) -> bool:
    lowered = Path(filename).stem.lower()
    return "transcoded" in lowered or "converted" in lowered or "fake" in lowered


__all__ = ["is_hard_filtered", "rank_candidates", "score_candidate"]
