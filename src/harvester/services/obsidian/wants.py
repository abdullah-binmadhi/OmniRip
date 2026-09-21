"""Inbound rip queue: ``Wants/`` notes → rip queries (docs/15).

Wants notes are user-owned. OmniRip only ever

1. reads the frontmatter + first heading to derive a search query, and
2. rewrites the ``status`` key and appends a bullet to the ``## OmniRip`` section.

The note body before ``## OmniRip`` is never modified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harvester.services.obsidian.frontmatter import parse_frontmatter, set_status
from harvester.services.obsidian.vault import VaultPaths, read_note, write_note

STATUS_WANT = "want"
STATUS_QUEUED = "queued"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
TERMINAL_STATUSES = {STATUS_DONE, STATUS_FAILED}

_SEPARATORS = re.compile(r"\s*[—–-]\s*")
_HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_OMNIRIP_SECTION = "## OmniRip"


@dataclass(frozen=True, slots=True)
class WantNote:
    path: Path
    status: str
    query: str


def _derive_query(title: str | None, artist: str | None, body: str, stem: str) -> str:
    if artist and title:
        return f"{artist} {title}".strip()
    heading = ""
    match = _HEADING.search(body)
    if match:
        heading = match.group(1).strip().strip("#").strip()
    parts = None
    for candidate in (heading, title, stem):
        if not candidate:
            continue
        parts = [part.strip() for part in _SEPARATORS.split(candidate) if part.strip()]
        if len(parts) >= 2:
            return " ".join(parts)
        return candidate
    return heading or title or stem or ""


def read_want(path: Path) -> WantNote:
    """Read one wants note into a (status, query) pair."""
    text = read_note(path)
    data, body = parse_frontmatter(text)
    status = str(data.get("status") or STATUS_WANT)
    title = data.get("title")
    artist = data.get("artist")
    query = data.get("query")
    if isinstance(title, (int, float, bool)) or not title:
        title = None
    if isinstance(artist, (int, float, bool)) or not artist:
        artist = None
    if not query or not isinstance(query, str) or not query.strip():
        query = _derive_query(str(title) if title else None, str(artist) if artist else None, body, path.stem)
    return WantNote(path=path, status=status, query=query.strip() or path.stem)


def iter_want_notes(vault: VaultPaths) -> list[Path]:
    """All ``.md`` files below ``Wants/`` (hidden files are ignored)."""
    if not vault.wants.exists():
        return []
    return sorted(
        path
        for path in vault.wants.rglob("*.md")
        if not path.name.startswith(".") and not any(part.startswith(".") for part in path.parts)
    )


def list_wants(vault: VaultPaths) -> list[WantNote]:
    return [read_want(path) for path in iter_want_notes(vault)]


def queueable(notes: list[WantNote], *, retry_failed: bool = False) -> list[WantNote]:
    """Notes ready to be submitted right now.

    ``want`` (or a missing status) queues immediately; terminal statuses are skipped
    unless ``retry_failed`` explicitly re-queues failed notes. ``queued`` is treated
    as in-flight and never auto-requeued.
    """
    result = []
    for note in notes:
        if note.status == STATUS_WANT:
            result.append(note)
        elif note.status == STATUS_FAILED and retry_failed:
            result.append(WantNote(path=note.path, status=STATUS_WANT, query=note.query))
    return result


def append_omnirip_log(text: str, line: str) -> str:
    """Append ``line`` as a bullet inside the ``## OmniRip`` section, creating it if needed."""
    bullet = f"- {line}"
    if _OMNIRIP_SECTION not in text:
        return text.rstrip() + "\n\n" + _OMNIRIP_SECTION + "\n" + bullet + "\n"
    lines = text.splitlines()
    marker_idx = lines.index(_OMNIRIP_SECTION)
    end = len(lines)
    # Anything after the marker but before the next heading belongs to the section.
    for candidate in range(marker_idx + 1, len(lines)):
        if lines[candidate].lstrip().startswith("#"):
            end = candidate
            break
    content = [bullet]
    if end > marker_idx + 1:
        content = lines[marker_idx + 1 : end] + [bullet]
    # Rebuild: marker + section content + bullet, then whatever came after the section.
    rebuilt = lines[: marker_idx + 1] + content
    tail = lines[end:]
    if tail:
        rebuilt += [""] + tail
    return "\n".join(rebuilt).rstrip() + "\n"


def settle_note(path: Path, status: str, line: str) -> None:
    """Flip ``status`` and record ``line`` in the OmniRip log (never touches the body)."""
    text = read_note(path)
    updated = set_status(text, status)
    write_note(path, append_omnirip_log(updated, line))


__all__ = [
    "STATUS_DONE",
    "STATUS_FAILED",
    "STATUS_QUEUED",
    "STATUS_WANT",
    "TERMINAL_STATUSES",
    "WantNote",
    "append_omnirip_log",
    "iter_want_notes",
    "list_wants",
    "queueable",
    "read_want",
    "settle_note",
]