"""Vault layout + crash-safe note I/O (docs/15).

Ownership contract:

- ``Library/``, ``Sessions/``, ``Studio/`` are OmniRip-owned and regenerable: any
  note in those namespaces may be overwritten wholesale.
- ``Wants/`` is user-owned: OmniRip only flips the ``status`` frontmatter key and
  appends to the ``## OmniRip`` section — never the body.
- Anything else in the vault (``Journal/``, user notes, ``.obsidian/``) is never
  read or written by OmniRip.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harvester.config import ObsidianConfig
from harvester.services.obsidian.naming import resolve_within
from harvester.util.fsatomic import atomic_replace, fsync_file

OMNIRIP_NOTE_TYPE = "omnirip"


@dataclass(frozen=True, slots=True)
class VaultPaths:
    """Resolved, normalized paths for the Obsidian vault."""

    root: Path
    library: Path
    sessions: Path
    studio: Path
    wants: Path
    hub: Path

    @classmethod
    def from_config(cls, config: ObsidianConfig) -> VaultPaths:
        root = Path(config.vault_dir).expanduser().resolve()
        return cls(
            root=root,
            library=root / config.library,
            sessions=root / config.sessions,
            studio=root / config.studio / "presets",
            wants=root / config.wants,
            hub=root / "OmniRip.md",
        )

    def ensure(self) -> VaultPaths:
        for directory in (self.library, self.sessions, self.studio, self.wants):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    def album_note(self, artist: str, album: str) -> Path:
        from harvester.services.obsidian.naming import album_note_name, artist_folder

        folder = resolve_within(self.library, artist_folder(artist))
        folder.mkdir(parents=True, exist_ok=True)
        return folder / (album_note_name(artist, album) + ".md")

    def session_note(self, stem: str) -> Path:
        return resolve_within(self.sessions, f"{stem}.md")

    def studio_note(self, preset_id: str) -> Path:
        from harvester.services.obsidian.naming import studio_note_name

        return resolve_within(self.studio, f"{studio_note_name(preset_id)}.md")

    def want_note(self, path: Path) -> Path:
        return resolve_within(self.wants, path)


def write_note(path: Path, text: str) -> None:
    """Atomically write ``text`` to ``path`` (crash leaves either the old or new note)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    fsync_file(tmp)
    atomic_replace(tmp, path)


def read_note(path: Path) -> str:
    """Read a note, tolerating concurrent edits (best-effort ``utf-8``)."""
    return path.read_text(encoding="utf-8")


__all__ = ["OMNIRIP_NOTE_TYPE", "VaultPaths", "read_note", "write_note"]