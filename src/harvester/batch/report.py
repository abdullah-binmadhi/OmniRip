"""Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from harvester.models import SourceKind, TrackJob, utc_now

REPORT_FIELDS = (
    "ts",
    "job_id",
    "mode",
    "input",
    "status",
    "reason",
    "old_bitrate",
    "source_kind",
    "spectral_verdict",
    "cutoff_hz",
    "identity_shift",
    "canonical",
    "output_path",
    "trash_path",
    "error",
)


@dataclass(frozen=True, slots=True)
class BatchReport:
    """Append-only, per-row-flush JSONL report. One row per input file (AC-5)."""

    path: Path

    def append(self, row: dict[str, object]) -> None:
        """Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)."""
        ordered = {field: row.get(field) for field in REPORT_FIELDS}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(ordered, ensure_ascii=False, default=str) + "\n")
            handle.flush()

    def rows(self) -> list[dict[str, object]]:
        """Read back every persisted row (used by tests and summaries)."""
        if not self.path.exists():
            return []
        rows: list[dict[str, object]] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows


def skipped_row(
    path: Path,
    *,
    reason: str,
    old_bitrate: int | None = None,
) -> dict[str, object]:
    """Row for a file left untouched by the scanner (docs/03 §1B.3)."""
    return {
        "ts": utc_now().isoformat(),
        "job_id": None,
        "mode": "BATCH_AUDIT",
        "input": str(path),
        "status": "skipped",
        "reason": reason,
        "old_bitrate": old_bitrate,
        "source_kind": None,
        "spectral_verdict": None,
        "cutoff_hz": None,
        "identity_shift": False,
        "canonical": None,
        "output_path": None,
        "trash_path": None,
        "error": None,
    }


def job_row(job: TrackJob, *, status: str, error: str | None = None) -> dict[str, object]:
    """Row for a queued batch job that reached a terminal state (docs/03 §5.4)."""
    canonical = job.canonical_meta.to_dict() if job.canonical_meta else None
    return {
        "ts": utc_now().isoformat(),
        "job_id": job.id,
        "mode": "BATCH_AUDIT",
        "input": str(job.input_path) if job.input_path else None,
        "status": status,
        "reason": None,
        "old_bitrate": job.orig_bitrate,
        "source_kind": job.source_kind.value if job.source_kind is not SourceKind.NONE else None,
        "spectral_verdict": job.spectral.verdict.value if job.spectral else None,
        "cutoff_hz": job.spectral.cutoff_hz if job.spectral else None,
        "identity_shift": job.identity_shift,
        "canonical": canonical,
        "output_path": str(job.output_path) if job.output_path else None,
        "trash_path": str(job.trash_path) if job.trash_path else None,
        "error": error or (job.error.message if job.error else None),
    }


def batch_report_name(root: Path) -> str:
    """Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{root.name}-{timestamp}.jsonl"


__all__ = ["REPORT_FIELDS", "BatchReport", "batch_report_name", "job_row", "skipped_row"]