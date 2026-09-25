"""Library export tests: album grouping + album notes from report rows (docs/15)."""

from __future__ import annotations

from pathlib import Path

from harvester.config import ObsidianConfig
from harvester.services.obsidian.frontmatter import parse_frontmatter
from harvester.services.obsidian.library import (
    album_identity,
    build_album_note,
    export_library,
    group_by_album,
)
from harvester.services.obsidian.vault import VaultPaths


def _row(**overrides) -> dict:
    row = {
        "ts": "2026-09-21T10:00:00Z",
        "job_id": "abc123",
        "mode": "BATCH_AUDIT",
        "input": "/music/a/song.flac",
        "status": "upgraded",
        "old_bitrate": 128,
        "source_kind": "P2P_FLAC",
        "spectral_verdict": "PASS",
        "cutoff_hz": 21000.0,
        "identity_shift": False,
        "canonical": {
            "title": "Chandelier",
            "artists": ["Sia"],
            "album": "This Is Acting",
            "year": 2016,
            "source": "musicbrainz",
        },
        "output_path": "/music/Harvested/Sia/This Is Acting/Chandelier.flac",
        "trash_path": None,
        "error": None,
    }
    row.update(overrides)
    return row


def test_album_identity_from_canonical() -> None:
    assert album_identity(_row()) == ("Sia", "This Is Acting")


def test_album_identity_falls_back_to_input_dir() -> None:
    row = _row(canonical=None, input="/music/SomeArtist/AnAlbum/song.mp3")

    assert album_identity(row) == ("SomeArtist", "AnAlbum")


def test_group_by_album_sorts_tracks_by_input() -> None:
    rows = [
        _row(input="/music/a/2.flac", canonical={"title": "B", "artists": ["X"], "album": "Al"}),
        _row(input="/music/a/1.flac", canonical={"title": "A", "artists": ["X"], "album": "Al"}),
        _row(canonical={"title": "Z", "artists": ["Y"], "album": "Other"}),
    ]
    grouped = group_by_album(rows)

    assert set(grouped) == {("X", "Al"), ("Y", "Other")}
    titles = [track["canonical"]["title"] for track in grouped[("X", "Al")]]
    assert titles == ["A", "B"]


def test_album_note_has_frontmatter_and_track_table(tmp_path: Path) -> None:
    text = build_album_note("Sia", "This Is Acting", [_row()])
    data, body = parse_frontmatter(text)

    assert data["type"] == "album"
    assert data["artist"] == "Sia"
    assert data["title"] == "This Is Acting"
    assert data["year"] == 2016
    assert data["tracks"] == 1
    assert data["omnirip"] == "omnirip"
    assert "| 1 | Chandelier |" in body
    assert "`/music/Harvested/Sia/This Is Acting/Chandelier.flac`" in body


def test_export_writes_under_library(tmp_path: Path) -> None:
    vault = VaultPaths.from_config(
        ObsidianConfig(enabled=True, vault_dir=tmp_path / "vault")
    )
    written = export_library(vault, [_row()])

    assert len(written) == 1
    assert written[0].name.endswith(".md")
    assert "Library" in written[0].parts
    assert written[0].is_file()
    data, _ = parse_frontmatter(written[0].read_text(encoding="utf-8"))
    assert data["artist"] == "Sia"


def test_album_note_with_genres_and_presets() -> None:
    track1 = _row(
        genre="Pop",
        enhancement_preset="vocal_air",
        canonical={"title": "Song 1", "artists": ["Artist"], "album": "Album", "genre": ["Pop", "Dance"]},
    )
    track2 = _row(
        genre="Electronic",
        canonical={"title": "Song 2", "artists": ["Artist"], "album": "Album", "genre": "Synthpop"},
    )
    text = build_album_note("Artist", "Album", [track1, track2])
    data, body = parse_frontmatter(text)

    assert data["genres"] == ["Dance", "Pop", "Synthpop"]
    assert "| 1 | Song 1 | upgraded | P2P_FLAC | PASS | 21000 Hz | ['Pop', 'Dance'] |" in body
    assert "| 2 | Song 2 | upgraded | P2P_FLAC | PASS | 21000 Hz | Synthpop |" in body