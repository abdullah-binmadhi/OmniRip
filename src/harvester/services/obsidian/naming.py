"""Traversal-safe, human-readable note paths (docs/15).

Obsidian indexes files by name, so we keep display names friendly (``Artist — Album``)
while every path segment is sanitized and confined to the vault root. No exported note
may ever escape ``vault_dir`` — even for hostile metadata from the wild P2P soup.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
_SPACES = re.compile(r"\s+")
_DASHES = re.compile(r"-+")


def sanitize_part(text: str) -> str:
    """Strip characters that break file names or Obsidian links."""
    cleaned = _UNSAFE.sub("-", text)
    return _SPACES.sub(" ", cleaned).strip(" .")


def slugify(text: str) -> str:
    """Lowercase, unicode-normalized, dash-separated slug for folders/ids."""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = _UNSAFE.sub("-", normalized.lower())
    slug = _DASHES.sub("-", _SPACES.sub("-", slug))
    alnum = "".join(ch if ch.isalnum() else "-" for ch in slug)
    return _DASHES.sub("-", alnum).strip("-")


def album_note_name(artist: str, album: str) -> str:
    """Filename for an album note: ``<Artist> — <Album>.md``."""
    return f"{sanitize_part(artist)} — {sanitize_part(album)}"


def artist_folder(artist: str) -> str:
    """Folder name for an artist under ``Library/``."""
    return sanitize_part(slugify(artist)) or "Unknown Artist"


def studio_note_name(preset_id: str) -> str:
    """Filename stem for a preset note under ``Studio/presets/``.

    Single source of truth for the name *and* for the ``[[presets/…]]`` wikilinks
    that point at it — a raw preset id (``fast_balanced``) would link to a note
    that does not exist (docs/15 §3).
    """
    return slugify(preset_id)


def resolve_within(root: Path, candidate: Path | str) -> Path:
    """Resolve ``candidate`` and refuse any path that escapes ``root``."""
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"path escapes the vault: {resolved}")
    return resolved


__all__ = [
    "album_note_name",
    "artist_folder",
    "resolve_within",
    "sanitize_part",
    "slugify",
    "studio_note_name",
]