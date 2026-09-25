"""Library export: one note per album built from batch-report rows (docs/15).

An album note is the readable face of the rip database: YAML frontmatter that
Dataview-style queries can pivot on, plus a per-track table and provenance blurb.
Notes are keyed by ``(artist, album)`` and are idempotent — re-running the sync
rewrites the same note with the latest state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from harvester.services.obsidian.frontmatter import encode_frontmatter
from harvester.services.obsidian.vault import OMNIRIP_NOTE_TYPE, VaultPaths, write_note

_UNKNOWN_ARTIST = "Unknown Artist"
_UNKNOWN_ALBUM = "Unknown Album"


def album_identity(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return (artist, album) for a batch-report row with safe fallbacks."""
    canonical = row.get("canonical")
    if isinstance(canonical, dict):
        artist = canon_artist(canonical) or _UNKNOWN_ARTIST
        album = str(canonical.get("album") or _UNKNOWN_ALBUM)
        return artist, album
    artist = _UNKNOWN_ARTIST
    album = _UNKNOWN_ALBUM
    if row.get("input"):
        owner = Path(str(row["input"])).parent
        artist = owner.parent.name or _UNKNOWN_ARTIST
        album = owner.name or _UNKNOWN_ALBUM
        if album in {".", ""}:
            artist, album = _UNKNOWN_ARTIST, _UNKNOWN_ALBUM
    return artist, album


def canon_artist(canonical: Mapping[str, Any]) -> str | None:
    """Best-effort artist string from the canonical dict (``artists`` list or ``artist``)."""
    raw = canonical.get("artists") or canonical.get("artist")
    if isinstance(raw, list):
        cleaned = [str(item) for item in raw if item]
        return " / ".join(cleaned) if cleaned else None
    if raw:
        text = str(raw).strip()
        return text or None
    return None


def track_row_fields(track: Mapping[str, Any]) -> dict[str, Any]:
    """Curated frontmatter fields for one track within an album note."""
    canonical = track.get("canonical") if isinstance(track.get("canonical"), dict) else {}
    return {
        "title": (canonical.get("title") or Path(str(track.get("input") or "")).stem) or None,
        "status": track.get("status"),
        "source_kind": track.get("source_kind"),
        "spectral_verdict": track.get("spectral_verdict"),
        "cutoff_hz": track.get("cutoff_hz"),
        "identity_shift": track.get("identity_shift"),
        "old_bitrate": track.get("old_bitrate"),
        "output_path": track.get("output_path"),
        "job_id": track.get("job_id"),
        "ts": track.get("ts"),
        "genre": canonical.get("genre") or track.get("genre"),
        "genre_mix": track.get("genre_mix"),
        "genre_intensity": track.get("genre_intensity"),
        "enhancement_preset": track.get("enhancement_preset"),
    }


def _album_frontmatter(artist: str, album: str, tracks: list[dict[str, Any]]) -> dict[str, Any]:
    years = set()
    genres = set()
    for track in tracks:
        canonical = track.get("canonical")
        if isinstance(canonical, dict) and isinstance(canonical.get("year"), int):
            years.add(canonical["year"])
        g = None
        if isinstance(canonical, dict) and canonical.get("genre"):
            g = canonical.get("genre")
        elif track.get("genre"):
            g = track.get("genre")
        if g:
            if isinstance(g, list):
                genres.update(str(x) for x in g if x)
            elif isinstance(g, str):
                genres.add(g)
    fm = {
        "omnirip": OMNIRIP_NOTE_TYPE,
        "type": "album",
        "title": album,
        "artist": artist,
        "year": min(years) if years else None,
        "tracks": len(tracks),
        "tags": ["omnirip", "library"],
    }
    if genres:
        fm["genres"] = sorted(genres)
    return fm


def _album_body(artist: str, album: str, tracks: list[dict[str, Any]]) -> str:
    if tracks:
        source = tracks[0].get("source_kind") or "unknown"
        verdict = tracks[0].get("spectral_verdict") or "n/a"
        cutoff = tracks[0].get("cutoff_hz")
        cutoff_text = f"{cutoff:.0f} Hz" if isinstance(cutoff, (int, float)) else "n/a"
    else:
        source = verdict = cutoff_text = "n/a"
    lines = [
        f"# {artist} — {album}",
        "",
        f"> {len(tracks)} track(s) from OmniRip · source `{source}` · spectral `{verdict}` "
        f"@ {cutoff_text}",
        "",
        "## Tracks",
        "",
        "| # | Title | Status | Source | Verdict | Cutoff | Genre | Output |",
        "|---|-------|--------|--------|---------|--------|-------|--------|",
    ]
    for index, track in enumerate(tracks, start=1):
        fields = track_row_fields(track)
        output = f"`{fields['output_path']}`" if fields.get("output_path") else "—"
        cutoff = fields.get("cutoff_hz")
        cutoff_cell = f"{cutoff:.0f} Hz" if isinstance(cutoff, (int, float)) else "—"
        genre_cell = escape_cell(str(fields.get("genre") or "—"))
        lines.append(
            f"| {index} | {escape_cell(str(fields['title']))} | {fields['status'] or '—'} "
            f"| {fields['source_kind'] or '—'} | {fields['spectral_verdict'] or '—'} "
            f"| {cutoff_cell} | {genre_cell} | {output} |"
        )
    return "\n".join(lines)


def escape_cell(text: str) -> str:
    """Keep markdown table cells from swallowing ``|`` in metadata."""
    return text.replace("|", "\\|")


def build_album_note(artist: str, album: str, tracks: list[dict[str, Any]]) -> str:
    """Render the full album note text for a (possibly multi-track) album."""
    frontmatter = _album_frontmatter(artist, album, tracks)
    return encode_frontmatter(frontmatter) + "\n" + _album_body(artist, album, tracks)


def group_by_album(
    rows: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Group upgraded report rows into ``(artist, album) -> [track rows]``."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        artist, album = album_identity(row)
        grouped.setdefault((artist, album), []).append(dict(row))
    for tracks in grouped.values():
        tracks.sort(key=lambda track: str(track.get("input") or str(track.get("ts") or "")))
    return grouped


def export_library(
    vault: VaultPaths, rows: Iterable[Mapping[str, Any]]
) -> list[Path]:
    """Write/update one album note per upgraded track, returning the written paths."""
    written: list[Path] = []
    for (artist, album), tracks in group_by_album(rows).items():
        path = vault.album_note(artist, album)
        write_note(path, build_album_note(artist, album, tracks))
        written.append(path)
    return written


__all__ = ["album_identity", "build_album_note", "export_library", "group_by_album"]