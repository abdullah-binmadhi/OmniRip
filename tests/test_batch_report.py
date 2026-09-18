"""Batch report tests: schema, incremental appends, row builders (FR-14)."""

from __future__ import annotations

from pathlib import Path

from harvester.batch.report import (
    REPORT_FIELDS,
    BatchReport,
    job_row,
    skipped_row,
)
from harvester.models import (
    CanonicalMetadata,
    Mode,
    SourceKind,
    SpectralResult,
    State,
    TrackJob,
    Verdict,
)


def test_append_writes_all_schema_fields(tmp_path: Path) -> None:
    report = BatchReport(tmp_path / "batch.jsonl")
    report.append({"input": "/music/song.mp3", "status": "skipped", "reason": "lossless"})

    assert report.path.exists()
    assert REPORT_FIELDS == tuple(
        ("ts", "job_id", "mode", "input", "status", "reason", "old_bitrate", "source_kind",
         "spectral_verdict", "cutoff_hz", "identity_shift", "canonical", "output_path",
         "trash_path", "error")
    )
    row = report.rows()[0]
    assert set(row) == set(REPORT_FIELDS)


def test_appends_are_incremental_and_order_preserved(tmp_path: Path) -> None:
    report = BatchReport(tmp_path / "batch.jsonl")
    report.append({"input": "a", "status": "skipped"})
    report.append({"input": "b", "status": "upgraded"})
    report.append({"input": "c", "status": "failed"})

    rows = report.rows()
    assert [row["input"] for row in rows] == ["a", "b", "c"]


def test_skipped_row_builds_valid_schema(tmp_path: Path) -> None:
    p = Path("/music/keep.flac")
    row = skipped_row(p, reason="lossless", old_bitrate=None)

    assert row["mode"] == "BATCH_AUDIT"
    assert row["status"] == "skipped"
    assert row["reason"] == "lossless"
    assert row["input"] == str(p)


def test_job_row_carries_terminal_state_fields(tmp_path: Path) -> None:
    low_mp3 = Path("/music/low.mp3")
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.id = "abc123"
    job.input_path = low_mp3
    job.orig_bitrate = 128
    job.source_kind = SourceKind.P2P_FLAC
    job.spectral = SpectralResult(verdict=Verdict.PASS, cutoff_hz=21_000.0)
    job.canonical_meta = CanonicalMetadata(title="Real Title", artists=("Real Artist",), year=1987)
    job.output_path = low_mp3
    job.trash_path = Path("/music/.trash/2026-01-01/120000-low.mp3")
    job.identity_shift = True

    row = job_row(job, status="upgraded")

    assert row["job_id"] == "abc123"
    assert row["status"] == "upgraded"
    assert row["old_bitrate"] == 128
    assert row["source_kind"] == "P2P_FLAC"
    assert row["spectral_verdict"] == "PASS"
    assert row["cutoff_hz"] == 21_000.0
    assert row["identity_shift"] is True
    assert row["canonical"]["title"] == "Real Title"
    assert row["output_path"] == str(low_mp3)
    assert row["trash_path"].endswith("low.mp3")


def test_job_row_carries_failure_message(tmp_path: Path) -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.state = State.FAILED

    row = job_row(job, status="failed", error="disk full")

    assert row["status"] == "failed"
    assert row["error"] == "disk full"


def test_rows_on_missing_file_are_empty(tmp_path: Path) -> None:
    report = BatchReport(tmp_path / "absent.jsonl")
    assert report.rows() == []