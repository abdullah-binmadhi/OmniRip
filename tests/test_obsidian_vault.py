"""Vault layout + atomic note I/O tests (docs/15)."""

from __future__ import annotations

from pathlib import Path

import pytest

from harvester.config import ObsidianConfig
from harvester.services.obsidian.naming import (
    album_note_name,
    resolve_within,
    sanitize_part,
    slugify,
)
from harvester.services.obsidian.vault import VaultPaths, read_note, write_note


def test_vault_paths_layout(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(
        ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault")
    )

    assert vault.root == (tmp_path / "vault").resolve()
    assert vault.library == vault.root / "Library"
    assert vault.sessions == vault.root / "Sessions"
    assert vault.wants == vault.root / "Wants"
    assert vault.studio == vault.root / "Studio" / "presets"
    assert vault.hub == vault.root / "OmniRip.md"


def test_ensure_creates_owned_namespaces(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(
        ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault")
    )
    vault.ensure()

    for directory in (vault.root, vault.library, vault.sessions, vault.studio, vault.wants):
        assert directory.is_dir()


def test_write_note_is_idempotent_and_readable(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(
        ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault")
    )
    note = vault.session_note("abc-123")
    write_note(note, "# v1\n")
    write_note(note, "# v2\n")

    assert read_note(note) == "# v2\n"


def test_album_note_creates_artist_folder(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(
        ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault")
    )
    path = vault.album_note("Sia", "This Is Acting")

    assert path.parent.name == "sia"
    assert path.name == album_note_name("Sia", "This Is Acting") + ".md"
    assert path.parent.is_dir()


def test_slug_handles_noise(tmp_path: Path) -> None:
    assert slugify("The  Rolling / Stones (2024!)") == "the-rolling-stones-2024"
    assert sanitize_part('a/b\\c:d*e?f"g<h>i|j') == "a-b-c-d-e-f-g-h-i-j"


def test_resolve_within_blocks_escape(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (tmp_path / "outside.md").write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes the vault"):
        resolve_within(root, "../outside.md")


def test_resolve_within_accepts_sibling(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    resolved = resolve_within(root, "Library/sia/note.md")

    assert resolved == (root / "Library/sia/note.md").resolve()