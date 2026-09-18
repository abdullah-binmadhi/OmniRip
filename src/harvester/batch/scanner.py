"""Mode B scanner: directory walk, mutagen probe, skip matrix (docs/03 §1B)."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.aiff import AIFF
from mutagen.asf import ASF
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.wavpack import WavPack

from harvester.batch.trash import TRASH_DIRNAME
from harvester.config import AppConfig
from harvester.models import BatchEntry, BatchScan, SkipReason

AUDIO_EXTENSIONS = frozenset(
    {
        ".mp3",
        ".m4a",
        ".mp4",
        ".aac",
        ".flac",
        ".ogg",
        ".oga",
        ".opus",
        ".wav",
        ".aiff",
        ".aif",
        ".wma",
        ".wv",
        ".ape",
    }
)
_EXCLUDED_DIRS_UPPER = frozenset({TRASH_DIRNAME.upper().lstrip("."), "QUARANTINE"})
_HARVESTER_TMP_PATTERN = re.compile(r"\.harvester\.tmp\.")

# NFR-5: estimate = jobs × 40 MB × 1.5 (download + transcode headroom).
_ESTIMATED_BYTES_PER_JOB = int(40 * 1024 * 1024)
_ESTIMATE_MULTIPLIER = 1.5

_TITLE_KEYS = ("title", "TIT2", "\xa9nam", "Title")
_ARTIST_KEYS = ("artist", "albumartist", "aartist", "TPE1", "\xa9ART", "Author")
_ALBUM_KEYS = ("album", "TALB", "\xa9alb", "Album")


def scan_directory(root: Path, config: AppConfig) -> BatchScan:
    """Recursively probe a music directory and apply the docs/03 §1B skip matrix.

    Deterministic: entries are sorted by path; unreadable files become
    ``skipped(reason=unreadable)`` rows and never crash the scan. Harvester's own
    leftover temp files (``*.harvester.tmp.*``) are purged when stale and skipped
    during the walk so a crash between trash-move and replace cannot re-queue them
    (AC-6).
    """
    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"not a directory: {root}")
    threshold_bps = config.batch.skip_bitrate_kbps * 1000
    entries: list[BatchEntry] = []
    purge_stale_temps(resolved)
    for dirpath, dirnames, filenames in _walk(resolved):
        dirnames[:] = [
            name
            for name in dirnames
            if name.upper().lstrip(".") not in _EXCLUDED_DIRS_UPPER
            and not name.startswith(".")
        ]
        for name in filenames:
            if name.startswith(".") or _HARVESTER_TMP_PATTERN.search(name):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            entries.append(_probe(path, threshold_bps))
    entries.sort(key=lambda entry: entry.path)
    free_bytes, needed_bytes = _free_space_estimate(resolved, entries)
    return BatchScan(
        root=resolved,
        entries=tuple(entries),
        free_bytes=free_bytes,
        needed_bytes=needed_bytes,
    )


def purge_stale_temps(root: Path) -> None:
    """Remove leftover ``*.harvester.tmp.*`` files from a crashed atomic swap (AC-6)."""
    for dirpath, dirnames, filenames in _walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name.upper().lstrip(".") not in _EXCLUDED_DIRS_UPPER
            and not name.startswith(".")
        ]
        for name in filenames:
            if _HARVESTER_TMP_PATTERN.search(name):
                try:
                    (Path(dirpath) / name).unlink(missing_ok=True)
                except OSError:
                    pass


def _walk(root: Path):
    """Yield ``os.walk`` tuples; sort in place so callers can prune traversal."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        yield dirpath, dirnames, filenames


def _probe(path: Path, threshold_bps: int) -> BatchEntry:
    try:
        file = MutagenFile(path)
        if file is None:
            return _skip(path, SkipReason.UNREADABLE)
        if isinstance(file, (FLAC, WAVE, AIFF, WavPack)):
            return _skip(path, SkipReason.LOSSLESS, _codec_label(file))
        if isinstance(file, MP4):
            codec = str(getattr(file.info, "codec", ""))
            if codec.lower() == "alac":
                return _skip(path, SkipReason.LOSSLESS, "alac")
            return _lossy(path, "m4a/aac", _file_bitrate(file), threshold_bps, file)
        if isinstance(file, MP3):
            return _lossy(path, "mp3", _file_bitrate(file), threshold_bps, file)
        if isinstance(file, ASF):
            return _lossy(path, "wma", _file_bitrate(file), threshold_bps, file)
        return _lossy(path, _codec_label(file), _file_bitrate(file), threshold_bps, file)
    except Exception:
        return _skip(path, SkipReason.UNREADABLE)


def _lossy(
    path: Path,
    codec: str,
    bitrate: int | None,
    threshold_bps: int,
    file,
) -> BatchEntry:
    duration = _duration(file)
    bitrate_kbps = _bitrate_kbps(bitrate, path, duration)
    entry = BatchEntry(
        path=path,
        codec=codec,
        bitrate_kbps=bitrate_kbps,
        duration_s=duration,
        size_bytes=_size(path),
        title=_first_meta(file, _TITLE_KEYS),
        artist=_first_meta(file, _ARTIST_KEYS),
        album=_first_meta(file, _ALBUM_KEYS),
    )
    if bitrate_kbps is not None and bitrate_kbps * 1000 >= threshold_bps:
        return BatchEntry(
            path=entry.path,
            codec=entry.codec,
            bitrate_kbps=entry.bitrate_kbps,
            duration_s=entry.duration_s,
            size_bytes=entry.size_bytes,
            title=entry.title,
            artist=entry.artist,
            album=entry.album,
            reason=SkipReason.BITRATE,
        )
    return entry


def _bitrate_kbps(bitrate: int | None, path: Path, duration: float | None) -> int | None:
    if bitrate:
        return int(bitrate) // 1000
    if duration and duration > 0:
        return int(_size(path) * 8 / duration / 1000)
    return None


def _file_bitrate(file) -> int | None:
    info = getattr(file, "info", None)
    if info is None:
        return None
    return getattr(info, "bitrate", None) or None


def _duration(file) -> float | None:
    info = getattr(file, "info", None)
    if info is None:
        return None
    try:
        return float(getattr(info, "length", 0.0)) or None
    except (TypeError, ValueError):
        return None


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _first_meta(file, keys: tuple[str, ...]) -> str | None:
    """Best-effort tag lookup across frame dicts (ID3, Vorbis, MP4, ASF)."""
    tags = getattr(file, "tags", None)
    if tags is None:
        return None
    for key in keys:
        try:
            value = tags.get(key)
        except Exception:
            continue
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:
                value = None
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _codec_label(file) -> str:
    mime = getattr(file, "mime", None)
    if mime:
        return mime[0].split("/")[-1]
    info = getattr(file, "info", None)
    return info.__class__.__name__.lower() if info else "audio"


def _skip(path: Path, reason: SkipReason, codec: str = "audio") -> BatchEntry:
    return BatchEntry(
        path=path,
        codec=codec,
        size_bytes=_size(path),
        reason=reason,
    )


def _free_space_estimate(root: Path, entries: list[BatchEntry]) -> tuple[int, int]:
    queued = sum(1 for entry in entries if entry.reason is None)
    needed = int(queued * _ESTIMATED_BYTES_PER_JOB * _ESTIMATE_MULTIPLIER)
    try:
        free = shutil.disk_usage(root).free
    except OSError:
        free = 0
    return free, needed


# --- filename parsing (docs/03 §1B.4, ordered patterns) ----------------------

_TRACK_PREFIX = re.compile(r"^\s*(\d{1,3})[\s._-]+")
_SUFFIX_NOISE = re.compile(r"\s*\(\d+\)\s*$")


def parse_filename(stem: str) -> tuple[str | None, str]:
    """Derive ``(artist, title)`` using the ordered docs/03 §1B.4 patterns."""
    cleaned = _TRACK_PREFIX.sub("", _SUFFIX_NOISE.sub("", stem)).strip()
    cleaned = cleaned.replace("_", " ").strip()
    if " - " in cleaned:
        possible_artist, possible_title = cleaned.split(" - ", 1)
        artist = possible_artist.strip() or None
        title = possible_title.strip()
        return artist, title or (artist or "")
    return None, cleaned or stem


def hunt_query_from_entry(entry: BatchEntry) -> str:
    """Build the Mode B hunt query: tags win, else the filename parse (docs/03 §1B.4)."""
    artist, title = entry.artist, entry.title
    if not title:
        parsed_artist, parsed_title = parse_filename(entry.path.stem)
        artist, title = artist or parsed_artist, parsed_title
    if title and artist:
        return f"{artist} - {title}"
    return title or artist or entry.path.stem


__all__ = [
    "AUDIO_EXTENSIONS",
    "hunt_query_from_entry",
    "parse_filename",
    "purge_stale_temps",
    "scan_directory",
]