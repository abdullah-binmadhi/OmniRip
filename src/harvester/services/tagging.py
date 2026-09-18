"""Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, COMM, ID3, TALB, TIT2, TPE1, TSRC, TXXX, TYER, ID3NoHeaderError

from harvester.models import CanonicalMetadata
from harvester.util.errors import ValidationError

_PROVENANCE_MP3 = (
    "Lossy stream origin (YouTube Opus), transcoded to MP3 320 CBR — not a lossless source."
)
_PROVENANCE_FLAC = "Soulseek lossless download; metadata secured from probe fallback."

_MP3_FRAMES = {
    "title": TIT2,
    "artist": TPE1,
    "album": TALB,
    "year": TYER,
    "isrc": TSRC,
}


def metadata_from_probe(probe: Mapping[str, Any]) -> CanonicalMetadata:
    """Build Phase M1 metadata fallback from yt-dlp probe fields."""

    raw_title = _text(probe.get("track")) or _text(probe.get("title"))
    artist = (
        _text(probe.get("artist")) or _text(probe.get("uploader")) or _text(probe.get("channel"))
    )
    album = _text(probe.get("album"))

    if raw_title and not probe.get("track") and " - " in raw_title:
        possible_artist, possible_title = raw_title.split(" - ", 1)
        if possible_artist.strip() and possible_title.strip():
            artist = artist or possible_artist.strip()
            raw_title = possible_title.strip()

    year = _year(probe.get("upload_date"))
    return CanonicalMetadata(
        title=raw_title or None,
        artists=(artist,) if artist else (),
        album=album,
        year=year,
        source="probe",
    )


class MetadataTagger:
    """Write only canonical fields plus explicit provenance and best-effort art."""

    def tag_mp3(
        self,
        path: Path,
        metadata: CanonicalMetadata,
        *,
        cover_bytes: bytes | None = None,
        source_origin: str = "youtube_opus_transcoded_mp3",
        provenance_comment: str = _PROVENANCE_MP3,
    ) -> Path:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValidationError(f"cannot tag missing or empty MP3: {path}")
        try:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            tags.clear()
            if metadata.title:
                tags.add(_MP3_FRAMES["title"](encoding=3, text=[metadata.title]))
            if metadata.artists:
                tags.add(_MP3_FRAMES["artist"](encoding=3, text=[" / ".join(metadata.artists)]))
            if metadata.album:
                tags.add(_MP3_FRAMES["album"](encoding=3, text=[metadata.album]))
            if metadata.year:
                tags.add(_MP3_FRAMES["year"](encoding=3, text=[str(metadata.year)]))
            if metadata.isrc:
                tags.add(_MP3_FRAMES["isrc"](encoding=3, text=[metadata.isrc]))
            if metadata.mb_recording_id:
                tags.add(
                    TXXX(encoding=3, desc="MUSICBRAINZ_TRACKID", text=[metadata.mb_recording_id])
                )
            if metadata.mb_release_id:
                tags.add(
                    TXXX(encoding=3, desc="MUSICBRAINZ_ALBUMID", text=[metadata.mb_release_id])
                )
            if cover_bytes:
                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="",
                        data=cover_bytes,
                    )
                )
            tags.add(TXXX(encoding=3, desc="SOURCE_ORIGIN", text=[source_origin]))
            tags.add(COMM(encoding=3, lang="eng", desc="", text=[provenance_comment]))
            if metadata.source not in {"probe", "unknown"}:
                tags.add(TXXX(encoding=3, desc="TAG_ORIGIN", text=[metadata.source]))
            tags.save(path, v2_version=3)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(f"could not write ID3v2.3 tags to {path.name}: {exc}") from exc
        return path

    def tag_flac(
        self,
        path: Path,
        metadata: CanonicalMetadata,
        *,
        cover_bytes: bytes | None = None,
        provenance_comment: str = _PROVENANCE_FLAC,
    ) -> Path:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValidationError(f"cannot tag missing or empty FLAC: {path}")
        try:
            audio = FLAC(path)
            audio.clear()
            values = {
                "TITLE": metadata.title,
                "ARTIST": " / ".join(metadata.artists) if metadata.artists else None,
                "ALBUM": metadata.album,
                "DATE": str(metadata.year) if metadata.year else None,
                "ISRC": metadata.isrc,
                "MUSICBRAINZ_TRACKID": metadata.mb_recording_id,
                "MUSICBRAINZ_ALBUMID": metadata.mb_release_id,
                "SOURCE_ORIGIN": "p2p_flac",
                "DESCRIPTION": provenance_comment,
            }
            for key, value in values.items():
                if value:
                    audio[key] = [value]
            if metadata.source not in {"probe", "unknown"}:
                audio["TAG_ORIGIN"] = [metadata.source]
            if cover_bytes:
                picture = Picture()
                picture.type = 3
                picture.mime = "image/jpeg"
                picture.desc = ""
                picture.data = cover_bytes
                audio.add_picture(picture)
            audio.save()
        except Exception as exc:
            raise ValidationError(f"could not write FLAC tags to {path.name}: {exc}") from exc
        return path

    async def tag_mp3_async(
        self,
        path: Path,
        metadata: CanonicalMetadata,
        *,
        cover_bytes: bytes | None = None,
        source_origin: str = "youtube_opus_transcoded_mp3",
        provenance_comment: str = _PROVENANCE_MP3,
    ) -> Path:
        return await asyncio.to_thread(
            self.tag_mp3,
            path,
            metadata,
            cover_bytes=cover_bytes,
            source_origin=source_origin,
            provenance_comment=provenance_comment,
        )

    async def tag_flac_async(
        self,
        path: Path,
        metadata: CanonicalMetadata,
        *,
        cover_bytes: bytes | None = None,
        provenance_comment: str = _PROVENANCE_FLAC,
    ) -> Path:
        return await asyncio.to_thread(
            self.tag_flac,
            path,
            metadata,
            cover_bytes=cover_bytes,
            provenance_comment=provenance_comment,
        )


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value).strip() if value is not None else ""


def _year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", _text(value))
    return int(match.group(1)) if match else None


__all__ = ["MetadataTagger", "metadata_from_probe"]
