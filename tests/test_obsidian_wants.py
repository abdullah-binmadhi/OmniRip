"""Wants note tests: query derivation, queueability, and settlement (docs/15)."""

from __future__ import annotations

from pathlib import Path

from harvester.config import ObsidianConfig
from harvester.services.obsidian.vault import VaultPaths
from harvester.services.obsidian.wants import (
    STATUS_DONE,
    WantNote,
    append_omnirip_log,
    list_wants,
    queueable,
    read_want,
    settle_note,
)


def _write_want(vault: VaultPaths, name: str, content: str) -> Path:
    path = vault.wants / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_read_want_derives_query_from_heading(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))
    path = _write_want(vault, "Chandelier.md", "---\nstatus: want\n---\n# Sia — Chandelier\n")

    note = read_want(path)

    assert note.status == "want"
    assert note.query == "Sia Chandelier"


def test_read_want_defaults_status_and_uses_filename(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))
    path = _write_want(vault, "Radiohead - Karma Police.md", "just a note\n")

    note = read_want(path)

    assert note.status == "want"
    assert note.query == "Radiohead Karma Police"


def test_frontmatter_title_and_artist_win(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))
    path = _write_want(
        vault,
        "Anything.md",
        "---\ntitle: Back to Black\nartist: Amy Winehouse\nstatus: want\n---\n# ignored\n",
    )

    assert read_want(path).query == "Amy Winehouse Back to Black"


def test_queueable_selects_want_and_skips_terminal(tmp_path: Path) -> None:
    notes = [
        WantNote(path=Path("/w/a.md"), status="want", query="q1"),
        WantNote(path=Path("/w/b.md"), status="queued", query="q2"),
        WantNote(path=Path("/w/c.md"), status="done", query="q3"),
        WantNote(path=Path("/w/d.md"), status="failed", query="q4"),
    ]

    assert [n.query for n in queueable(notes)] == ["q1"]
    assert [n.query for n in queueable(notes, retry_failed=True)] == ["q1", "q4"]


def test_list_wants_honours_subfolders_and_hidden_files(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))
    _write_want(vault, "a.md", "# Artist — Title\n")
    nested = vault.wants / "deep" / "b.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# x — y\n", encoding="utf-8")
    _write_want(vault, ".hidden.md", "# nope\n")

    names = [note.path.name for note in list_wants(vault)]

    assert names == ["a.md", "b.md"]


def test_settle_note_flips_status_and_logs_without_touching_body(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault"))
    path = _write_want(vault, "song.md", "---\nstatus: want\n---\n# Artist — Title\n\nMy notes.\n")

    settle_note(path, STATUS_DONE, "2026-09-21T00:00:00Z done -> /out.flac")

    text = path.read_text(encoding="utf-8")
    assert "status: done" in text
    assert "# Artist — Title" in text
    assert "My notes." in text
    assert "## OmniRip" in text
    assert "- 2026-09-21T00:00:00Z done -> /out.flac" in text


def test_append_log_keeps_user_content_above_before_marker(tmp_path: Path) -> None:
    text = "# Title\n\nnotes\n"
    appended = append_omnirip_log(text, "first")

    first = append_omnirip_log(appended, "second")
    assert first.count("- first") == 1
    assert first.count("- second") == 1
    assert first.index("- first") < first.index("- second")


def test_append_log_does_not_leak_into_user_sections_after_marker() -> None:
    text = "# Title\n\n## OmniRip\n- existing\n\n## My notes\n- user\n"
    updated = append_omnirip_log(text, "queued")

    assert updated.index("- queued") < updated.index("## My notes")
    assert "- user" in updated