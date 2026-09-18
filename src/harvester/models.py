"""Domain models shared by the pipeline, services, and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from harvester.statemachine import State  # noqa: F401 - re-exported for `models.State`


class Mode(StrEnum):
    SINGLE_URL = "SINGLE_URL"
    BATCH_AUDIT = "BATCH_AUDIT"


class SourceKind(StrEnum):
    NONE = "NONE"
    P2P_FLAC = "P2P_FLAC"
    STREAM_OPUS = "STREAM_OPUS"
    STREAM_OTHER = "STREAM_OTHER"


class Verdict(StrEnum):
    PASS = "PASS"
    FRAUD = "FRAUD"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SkipReason(StrEnum):
    """Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)."""

    LOSSLESS = "lossless"
    BITRATE = "bitrate"
    UNREADABLE = "unreadable"


class ErrorClass(StrEnum):
    UNKNOWN = "UNKNOWN"
    CONFIG = "CONFIG"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    RATE_LIMITED = "RATE_LIMITED"
    PERMANENT_SOURCE = "PERMANENT_SOURCE"
    VALIDATION = "VALIDATION"
    FRAUD = "FRAUD"
    DISK = "DISK"
    CANCELLED = "CANCELLED"


class EventKind(StrEnum):
    STATE = "STATE"
    PROGRESS = "PROGRESS"
    LOG = "LOG"
    ERROR = "ERROR"


def utc_now() -> datetime:
    """Return an aware UTC timestamp suitable for persisted events."""

    return datetime.now(UTC)


@dataclass(slots=True)
class DownloadProgress:
    bytes_done: int = 0
    bytes_total: int | None = None
    speed_bps: float | None = None
    percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes_done": self.bytes_done,
            "bytes_total": self.bytes_total,
            "speed_bps": self.speed_bps,
            "percent": self.percent,
        }


@dataclass(slots=True)
class SpectralResult:
    verdict: Verdict = Verdict.NOT_APPLICABLE
    cutoff_hz: float | None = None
    steepness_db_per_khz: float | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "cutoff_hz": self.cutoff_hz,
            "steepness_db_per_khz": self.steepness_db_per_khz,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class CanonicalMetadata:
    title: str | None = None
    artists: tuple[str, ...] = ()
    album: str | None = None
    year: int | None = None
    isrc: str | None = None
    mb_recording_id: str | None = None
    mb_release_id: str | None = None
    confidence: float | None = None
    source: str = "unknown"

    def __post_init__(self) -> None:
        object.__setattr__(self, "artists", tuple(self.artists))

    @property
    def artist(self) -> str | None:
        return " / ".join(self.artists) if self.artists else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "artists": list(self.artists),
            "album": self.album,
            "year": self.year,
            "isrc": self.isrc,
            "mb_recording_id": self.mb_recording_id,
            "mb_release_id": self.mb_release_id,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    error_class: ErrorClass
    message: str
    retryable: bool = False
    attempt: int = 0
    user_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_class": self.error_class.value,
            "message": self.message,
            "retryable": self.retryable,
            "attempt": self.attempt,
            "user_hint": self.user_hint,
        }


@dataclass(slots=True)
class P2PCandidate:
    username: str
    filename: str
    size_bytes: int | None = None
    duration_s: float | None = None
    bit_depth: int | None = None
    sample_rate: int | None = None
    score: float = 0.0
    queue_length: int | None = None
    user_speed_kbps: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "duration_s": self.duration_s,
            "bit_depth": self.bit_depth,
            "sample_rate": self.sample_rate,
            "score": self.score,
            "queue_length": self.queue_length,
            "user_speed_kbps": self.user_speed_kbps,
        }


@dataclass(frozen=True, slots=True)
class BatchEntry:
    """One audio file discovered by the Mode B scanner (docs/03 \u00a71B)."""

    path: Path
    codec: str
    bitrate_kbps: int | None = None
    duration_s: float | None = None
    size_bytes: int = 0
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    reason: SkipReason | None = None


@dataclass(frozen=True, slots=True)
class BatchScan:
    """Result of a Mode B directory scan with the pre-flight summary."""

    root: Path
    entries: tuple[BatchEntry, ...]
    free_bytes: int
    needed_bytes: int

    @property
    def queued(self) -> list[BatchEntry]:
        return [entry for entry in self.entries if entry.reason is None]

    @property
    def skipped(self) -> list[BatchEntry]:
        return [entry for entry in self.entries if entry.reason is not None]

    @property
    def found(self) -> int:
        return len(self.entries)


@dataclass(slots=True)
class TrackJob:
    """Mutable job aggregate owned by the orchestrator."""

    mode: Mode
    input_url: str | None = None
    input_path: Path | None = None
    batch_root: Path | None = None
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    state: State = State.QUEUED
    query_raw: str = ""
    queries: list[str] = field(default_factory=list)
    probe_meta: dict[str, Any] = field(default_factory=dict)
    orig_codec: str | None = None
    orig_bitrate: int | None = None
    orig_duration_s: float | None = None
    orig_size: int | None = None
    orig_tags: dict[str, Any] = field(default_factory=dict)
    candidates: list[P2PCandidate] = field(default_factory=list)
    candidate_cursor: int = 0
    selected_candidate: P2PCandidate | None = None
    p2p_retries: int = 0
    source_kind: SourceKind = SourceKind.NONE
    workspace_path: Path | None = None
    output_path: Path | None = None
    trash_path: Path | None = None
    identity_shift: bool = False
    download: DownloadProgress = field(default_factory=DownloadProgress)
    canonical_meta: CanonicalMetadata | None = None
    spectral: SpectralResult = field(default_factory=SpectralResult)
    fingerprint_cached: bool = False
    fallback_attempted: bool = False
    progress: float = 0.0
    error: ErrorInfo | None = None
    cancel_requested: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def transition(self, target: State, *, reason: str | None = None) -> None:
        """Apply one guarded state transition through the canonical state machine."""

        from harvester.statemachine import assert_transition

        assert_transition(self.state, target, fallback_attempted=self.fallback_attempted)
        self.state = target
        self.updated_at = utc_now()
        if reason:
            self.probe_meta.setdefault("transition_reasons", []).append(reason)

    def request_cancel(self) -> None:
        self.cancel_requested = True
        self.updated_at = utc_now()

    @property
    def display_name(self) -> str:
        title = self.canonical_meta.title if self.canonical_meta else None
        if title:
            artist = self.canonical_meta.artist if self.canonical_meta else None
            return f"{artist} — {title}" if artist else title
        if self.probe_meta.get("title"):
            return str(self.probe_meta["title"])
        if self.input_path:
            return self.input_path.name
        return self.query_raw or self.input_url or self.id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "state": self.state.value,
            "input_url": self.input_url,
            "input_path": str(self.input_path) if self.input_path else None,
            "batch_root": str(self.batch_root) if self.batch_root else None,
            "query_raw": self.query_raw,
            "queries": list(self.queries),
            "probe_meta": dict(self.probe_meta),
            "orig_codec": self.orig_codec,
            "orig_bitrate": self.orig_bitrate,
            "orig_duration_s": self.orig_duration_s,
            "orig_size": self.orig_size,
            "orig_tags": dict(self.orig_tags),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "candidate_cursor": self.candidate_cursor,
            "selected_candidate": self.selected_candidate.to_dict()
            if self.selected_candidate
            else None,
            "p2p_retries": self.p2p_retries,
            "source_kind": self.source_kind.value,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "output_path": str(self.output_path) if self.output_path else None,
            "trash_path": str(self.trash_path) if self.trash_path else None,
            "identity_shift": self.identity_shift,
            "download": self.download.to_dict(),
            "canonical_meta": self.canonical_meta.to_dict() if self.canonical_meta else None,
            "spectral": self.spectral.to_dict(),
            "fingerprint_cached": self.fingerprint_cached,
            "fallback_attempted": self.fallback_attempted,
            "progress": self.progress,
            "error": self.error.to_dict() if self.error else None,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class JobEvent:
    job_id: str
    kind: EventKind
    seq: int = 0
    state: State | None = None
    progress: DownloadProgress | None = None
    level: str = "INFO"
    text: str | None = None
    error: ErrorInfo | None = None
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind.value,
            "seq": self.seq,
            "state": self.state.value if self.state else None,
            "progress": self.progress.to_dict() if self.progress else None,
            "level": self.level,
            "text": self.text,
            "error": self.error.to_dict() if self.error else None,
            "created_at": self.created_at.isoformat(),
        }


__all__ = [
    "BatchEntry",
    "BatchScan",
    "CanonicalMetadata",
    "DownloadProgress",
    "ErrorClass",
    "ErrorInfo",
    "EventKind",
    "JobEvent",
    "Mode",
    "P2PCandidate",
    "SkipReason",
    "SourceKind",
    "SpectralResult",
    "State",
    "TrackJob",
    "Verdict",
    "utc_now",
]
