"""ObsidianSync orchestration tests: exports, hub, and wants import/settle (docs/15)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from harvester.config import ObsidianConfig
from harvester.models import ErrorClass, ErrorInfo, Mode, State, TrackJob
from harvester.services.obsidian.frontmatter import parse_frontmatter
from harvester.services.obsidian.sync import ObsidianSync


def _sync(tmp_path: Path) -> ObsidianSync:
    return ObsidianSync(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))


def _write_report(tmp_path: Path, name: str) -> Path:
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    report = reports / name
    report.write_text(
        json.dumps(
            {
                "status": "upgraded",
                "old_bitrate": 128,
                "source_kind": "P2P_FLAC",
                "spectral_verdict": "PASS",
                "cutoff_hz": 21000.0,
                "canonical": {"title": "Chandelier", "artists": ["Sia"], "album": "This Is Acting"},
                "output_path": "/out/Chandelier.flac",
                "input": "/in/song.flac",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def test_full_export_writes_all_namespaces(tmp_path: Path) -> None:
    sync = _sync(tmp_path)
    sync.ensure()
    report = _write_report(tmp_path, "MyMusic-20260921-120000.jsonl")

    rows = [json.loads(line) for line in report.read_text().splitlines() if line.strip()]
    library = sync.export_library(rows)
    sessions = sync.export_sessions([report])
    studio = sync.export_studio()
    hub = sync.write_hub()

    assert len(library) == 1
    assert len(sessions) == 1
    assert any(note.name == "README.md" for note in studio)
    assert hub.name == "OmniRip.md"
    assert library[0].read_text().startswith("---")
    assert "Chandelier" in library[0].read_text()


@pytest.mark.asyncio
async def test_import_wants_marks_queued_and_settle_marks_done(tmp_path: Path) -> None:
    sync = _sync(tmp_path)
    sync.ensure()
    note = sync.vault.wants / "Sia - Chandelier.md"
    note.write_text("---\nstatus: want\n---\n# Sia — Chandelier\n", encoding="utf-8")

    async def submit(query: str):
        job = TrackJob(mode=Mode.SINGLE_URL)
        job.state = State.COMPLETED
        job.output_path = Path("/out/Chandelier.flac")
        return job

    pending = await sync.import_wants(submit)
    assert len(pending) == 1
    assert "status: queued" in note.read_text()

    results = sync.settle_wants(pending)
    assert results[note] == "done"
    text = note.read_text()
    assert "status: done" in text
    assert "done -> /out/Chandelier.flac" in text


@pytest.mark.asyncio
async def test_import_wants_skips_done_and_requeues_failed_with_retry(tmp_path: Path) -> None:
    sync = _sync(tmp_path)
    sync.ensure()
    done = sync.vault.wants / "done.md"
    done.write_text("---\nstatus: done\n---\n# A — B\n", encoding="utf-8")
    failed = sync.vault.wants / "failed.md"
    failed.write_text("---\nstatus: failed\n---\n# C — D\n", encoding="utf-8")

    async def submit(query: str):
        return TrackJob(mode=Mode.SINGLE_URL)

    assert await sync.import_wants(submit) == {}
    pending = await sync.import_wants(submit, retry_failed=True)
    assert len(pending) == 1
    assert list(pending)[0].name == "failed.md"


@pytest.mark.asyncio
async def test_settle_wants_records_failures(tmp_path: Path) -> None:
    sync = _sync(tmp_path)
    sync.ensure()
    note = sync.vault.wants / "boo.md"
    note.write_text("---\nstatus: want\n---\n# X — Y\n", encoding="utf-8")

    async def submit(query: str):
        return TrackJob(mode=Mode.SINGLE_URL)

    pending = await sync.import_wants(submit)
    job = pending[note]
    job.state = State.FAILED
    job.error = ErrorInfo(error_class=ErrorClass.PERMANENT_SOURCE, message="gone")

    results = sync.settle_wants(pending)

    assert results[note] == "failed"
    assert "status: failed" in note.read_text()
    assert "failed: gone" in note.read_text()


def test_hub_note_is_valid(tmp_path: Path) -> None:
    sync = _sync(tmp_path)
    sync.ensure()
    hub = sync.write_hub()

    data, body = parse_frontmatter(hub.read_text(encoding="utf-8"))
    assert data["type"] == "hub"
    assert "Wants/" in body


def test_studio_index_and_hub_links_resolve_to_written_notes(tmp_path: Path) -> None:
    """Regression: preset wikilinks must match the slugified note file names.

    Obsidian resolves ``[[presets/x]]`` by path suffix, so a raw preset id
    (``fast_balanced``) links to a note that does not exist — the file on disk is
    ``presets/fast-balanced.md`` (docs/15 §3).
    """
    sync = _sync(tmp_path)
    sync.ensure()
    sync.export_studio()
    hub = sync.write_hub()
    root = sync.vault.root
    notes = {path.relative_to(root).with_suffix("").as_posix() for path in root.rglob("*.md")}

    for note in (root / "Studio" / "README.md", hub):
        links = re.findall(r"\[\[([^\]]+)\]\]", note.read_text(encoding="utf-8"))
        assert links, f"{note.name} should link to the preset notes"
        unresolved = [
            link
            for link in links
            if not any(path == link or path.endswith(f"/{link}") for path in notes)
        ]
        assert unresolved == [], f"{note.name} has unresolved links: {unresolved}"
