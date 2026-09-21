"""Session export tests: report filename → session note rollup (docs/15)."""

from __future__ import annotations

import json
from pathlib import Path

from harvester.config import ObsidianConfig
from harvester.services.obsidian.frontmatter import parse_frontmatter
from harvester.services.obsidian.sessions import build_session_note, session_identity
from harvester.services.obsidian.vault import VaultPaths


def test_session_identity_parses_root_and_timestamp() -> None:
    root, stem = session_identity(Path("MyMusic-20260921-123456.jsonl"))

    assert root == "MyMusic"
    assert stem == "MyMusic-20260921-123456"


def test_session_identity_handles_dashes_in_root() -> None:
    root, stem = session_identity(Path("The-Beatles-20260801-000000.jsonl"))

    assert root == "The-Beatles"
    assert stem == "The-Beatles-20260801-000000"


def test_build_session_note_rolls_up_rows() -> None:
    rows = [
        {"status": "upgraded", "old_bitrate": 128, "spectral_verdict": "PASS", "cutoff_hz": 21000.0, "input": "/a.flac", "error": None},
        {"status": "upgraded", "old_bitrate": 192, "spectral_verdict": "FRAUD", "cutoff_hz": None, "input": "/b.flac", "error": None},
        {"status": "skipped", "old_bitrate": 320, "spectral_verdict": None, "cutoff_hz": None, "input": "/c.flac", "error": None},
    ]
    text = build_session_note(Path("MyMusic-20260921-123456.jsonl"), rows)
    data, body = parse_frontmatter(text)

    assert data["type"] == "session"
    assert data["report"] == "MyMusic-20260921-123456.jsonl"
    assert data["statuses"] == {"skipped": 1, "upgraded": 2}
    assert data["verdicts"] == {"FRAUD": 1, "PASS": 1}
    assert "| upgraded | 2 |" in body
    assert "| FRAUD |" in body


def test_export_writes_one_note_per_report(tmp_path: Path) -> None:
    report = tmp_path / "reports" / "MyMusic-20260921-000000.jsonl"
    report.parent.mkdir()
    report.write_text(json.dumps({"status": "skipped", "input": "/song.flac"}) + "\n")
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))

    from harvester.services.obsidian.sessions import export_sessions

    written = export_sessions(vault, [report])

    assert len(written) == 1
    assert written[0].name == "MyMusic-20260921-000000.md"
    assert written[0].is_file()