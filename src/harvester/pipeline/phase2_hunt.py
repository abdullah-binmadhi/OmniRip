"""Phase 2 hunt policy: queries, candidate selection, and fallback decisions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.flac import FLAC

from harvester.analysis.scoring import rank_candidates
from harvester.analysis.titleclean import build_queries
from harvester.models import P2PCandidate, TrackJob
from harvester.services.slskd import SearchResponse, SlskdService
from harvester.util.errors import ValidationError


def build_hunt_queries(job: TrackJob) -> tuple[str, ...]:
    """Build the ordered query set from probe or canonical metadata."""

    meta = job.canonical_meta
    artist = (meta.artist if meta else None) or job.probe_meta.get("uploader") or ""
    title = (meta.title if meta else None) or job.probe_meta.get("title") or ""
    if not title and job.query_raw:
        title = job.query_raw
    return build_queries(artist, title)


def select_candidate(job: TrackJob) -> P2PCandidate | None:
    """Return the next candidate from the ranked list, or None when exhausted."""

    if job.candidate_cursor >= len(job.candidates):
        return None
    candidate = job.candidates[job.candidate_cursor]
    job.selected_candidate = candidate
    return candidate


def prepare_fallback(job: TrackJob, *, reason: str = "P2P hunt unavailable") -> None:
    """Mark a job as having entered the one allowed fallback lane."""

    if not job.input_url:
        raise ValidationError("fallback requires the original Mode A URL")
    if job.fallback_attempted:
        raise ValidationError("fallback has already been attempted for this job")
    job.fallback_attempted = True
    job.probe_meta["p2p_reason"] = reason


async def validate_lossless_file(path: Path) -> None:
    """Run the deterministic Phase 2.3 post-download validation in a thread."""

    file = await asyncio.to_thread(MutagenFile, path)
    if file is None or not isinstance(file, FLAC):
        raise ValidationError("downloaded file is not a parseable FLAC")
    info = getattr(file, "info", None)
    if info is None:
        raise ValidationError("downloaded FLAC has no stream info")
    if getattr(info, "bits_per_sample", 16) < 16:
        raise ValidationError("downloaded FLAC has fewer than 16 bits per sample")


async def hunt_and_score(
    slskd: SlskdService,
    job: TrackJob,
) -> list[P2PCandidate]:
    """Run the shared-budget search and return ranked, hard-filtered candidates."""

    queries = build_hunt_queries(job)
    if not queries:
        return []
    responses: list[SearchResponse] = await slskd.search(
        queries,
        timeout_s=min(
            slskd.config.slskd.search_timeout_s,
            slskd.config.slskd.p2p_timeout_s,
        ),
    )
    candidates: list[P2PCandidate] = []
    for response in responses:
        for file in response.files:
            candidates.append(
                P2PCandidate(
                    username=response.user,
                    filename=file.filename,
                    size_bytes=file.size_bytes,
                    duration_s=file.duration_s,
                    bit_depth=file.bit_depth,
                    sample_rate=file.sample_rate,
                    queue_length=response.queue_length,
                    user_speed_kbps=response.speed_kbps,
                )
            )
    expected = _number(job.probe_meta.get("duration")) or job.orig_duration_s
    ranked = rank_candidates(candidates, expected_duration_s=expected)
    max_queue = slskd.config.slskd.max_queue_length
    if slskd.config.slskd.acquisition_mode in {"best_available", "fast_fallback"}:
        ranked = [
            candidate
            for candidate in ranked
            if candidate.queue_length is None or candidate.queue_length <= max_queue
        ]
    return ranked


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "build_hunt_queries",
    "hunt_and_score",
    "prepare_fallback",
    "select_candidate",
    "validate_lossless_file",
]
