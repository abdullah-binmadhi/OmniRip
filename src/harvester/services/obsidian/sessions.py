"""Session export: one note per Mode B report (docs/15).

Each batch run writes a ``<dirname>-<timestamp>.jsonl`` report (docs/03 §5.4). The
sync turns every such report into a human-readable session note with a rollup and a
per-track table, so Obsidian can answer "what did that run do?" without opening JSON.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from harvester.services.obsidian.frontmatter import encode_frontmatter
from harvester.services.obsidian.library import escape_cell
from harvester.services.obsidian.vault import OMNIRIP_NOTE_TYPE, VaultPaths, write_note


def _rollup(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    verdicts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        verdict = row.get("spectral_verdict")
        if verdict:
            verdicts[str(verdict)] = verdicts.get(str(verdict), 0) + 1
    return {
        "total": sum(statuses.values()),
        "statuses": dict(sorted(statuses.items())),
        "verdicts": dict(sorted(verdicts.items())),
    }


def session_identity(report_path: Path) -> tuple[str, str]:
    """Return (root_name, stem) from a ``<root>-<utctime>.jsonl`` report filename."""
    stem = report_path.stem
    parts = stem.split("-")
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        return "-".join(parts[:-2]), stem
    return stem, stem


def build_session_note(report_path: Path, rows: list[dict[str, Any]]) -> str:
    """Render a session note from a report path and its parsed rows."""
    root, _ = session_identity(report_path)
    rollup = _rollup(rows)
    verdict_text = ", ".join(f"{k}: {v}" for k, v in rollup["verdicts"].items()) or "none"
    frontmatter: dict[str, Any] = {
        "omnirip": OMNIRIP_NOTE_TYPE,
        "type": "session",
        "report": report_path.name,
        "root": root,
        "statuses": rollup["statuses"],
        "verdicts": rollup["verdicts"],
        "tags": ["omnirip", "sessions"],
    }
    header = f"# Session — {report_path.name}"
    summary = [
        "",
        f"> {rollup['total']} track(s) scanned · verdicts: {verdict_text}",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    summary.extend(f"| {status} | {count} |" for status, count in rollup["statuses"].items())
    table = ["", "## Track log", "", "| Status | Input | Old bitrate | Verdict | Cutoff | Error |", "|--------|-------|-------------|---------|--------|-------|"]
    for row in rows:
        cutoff = row.get("cutoff_hz")
        cutoff_cell = f"{cutoff:.0f} Hz" if isinstance(cutoff, (int, float)) else "—"
        table.append(
            f"| {row.get('status') or '—'} | {escape_cell(str(row.get('input') or ''))} "
            f"| {row.get('old_bitrate') or '—'} | {row.get('spectral_verdict') or '—'} "
            f"| {cutoff_cell} | {escape_cell(str(row.get('error') or '')) or '—'} |"
        )
    return encode_frontmatter(frontmatter) + "\n" + header + "\n".join(summary) + "\n".join(table) + "\n"


def export_sessions(vault: VaultPaths, reports: Iterable[Path]) -> list[Path]:
    """Write one session note per report file, returning the written paths."""
    written: list[Path] = []
    for report_path in reports:
        rows: list[dict[str, Any]] = []
        if report_path.exists():
            with report_path.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        _, stem = session_identity(report_path)
        path = vault.session_note(stem)
        write_note(path, build_session_note(report_path, rows))
        written.append(path)
    return written


__all__ = ["build_session_note", "export_sessions", "session_identity"]