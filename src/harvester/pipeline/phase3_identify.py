"""M3 identity stage: AcoustID ground truth with the documented fallback chain."""

from __future__ import annotations

from difflib import SequenceMatcher

from harvester.models import CanonicalMetadata, Mode, TrackJob
from harvester.services.acoustid import AcoustidService
from harvester.services.tagging import metadata_from_probe
from harvester.util.errors import ValidationError


async def identify_job(job: TrackJob, acoustid: AcoustidService) -> CanonicalMetadata:
    """Resolve canonical metadata, degrading to probe/original metadata when needed."""

    if not job.workspace_path or not job.workspace_path.is_file():
        raise ValidationError("cannot identify a job without an acquired file")

    result = await acoustid.identify(job.workspace_path, job_id=job.id)
    if result is not None:
        job.canonical_meta = result
        job.identity_shift = _identity_shift(job)
        return result
    return identify_from_fallback(job)


def identify_from_fallback(job: TrackJob) -> CanonicalMetadata:
    """Resolve a useful canonical-shaped record from the docs/03 \u00a7\u00a712-4 chain.

    Level 1: Mode A probe metadata. Level 2: Mode B original tags. Level 3: filename
    parse (queue entry) / stem-as-title. Phase 3 never fails a job this way.
    """

    if job.probe_meta:
        metadata = metadata_from_probe(job.probe_meta)
        if metadata.title:
            job.canonical_meta = metadata
            return metadata
    if job.mode is Mode.BATCH_AUDIT:
        metadata = metadata_from_orig_tags(job)
        if metadata.title:
            job.canonical_meta = metadata
            return metadata
    if job.query_raw:
        job.canonical_meta = metadata_from_query(job.query_raw)
        return job.canonical_meta
    if job.input_path:
        job.canonical_meta = metadata_from_query(job.input_path.stem)
        return job.canonical_meta
    raise ValidationError("no probe metadata and no query derived from the input")


def metadata_from_orig_tags(job: TrackJob) -> CanonicalMetadata:
    """Canonical-shaped record sourced from the original file's tags (Mode B)."""

    title = _first_orig(job, ("title", "TIT2", "\xa9nam", "Title"))
    artist = _first_orig(job, ("artist", "albumartist", "TPE1", "\xa9ART", "Author"))
    album = _first_orig(job, ("album", "TALB", "\xa9alb", "Album"))
    year = _orig_year(job)
    isrc = _first_orig(job, ("isrc", "TXXX:ISRC", "----:com.apple.iTunes:ISRC"))
    mbid = _first_orig(job, ("musicip_puid", "musicbrainz_trackid", "MusicBrainz Track Id"))
    return CanonicalMetadata(
        title=title,
        artists=(artist,) if artist else (),
        album=album,
        year=year,
        isrc=isrc,
        mb_recording_id=mbid or None,
        source="original_tags",
    )


def metadata_from_query(query: str) -> CanonicalMetadata:
    """Canonical-shaped record derived from a query/filename parse (Level 3)."""

    if " - " in query:
        artist, title = query.split(" - ", 1)
        return CanonicalMetadata(
            title=title.strip(),
            artists=(artist.strip(),) if artist.strip() else (),
            source="filename",
        )
    return CanonicalMetadata(title=query.strip(), source="filename")


def _identity_shift(job: TrackJob) -> bool:
    """Mode B warning: canonical diverges from the original tags (docs/03 Phase 3 \u00a76)."""

    if job.mode is not Mode.BATCH_AUDIT or job.canonical_meta is None:
        return False
    orig_title = _first_orig(job, ("title", "TIT2", "\xa9nam", "Title"))
    orig_mbid = _first_orig(job, ("musicbrainz_trackid", "MusicBrainz Track Id"))
    if orig_mbid and job.canonical_meta.mb_recording_id:
        return orig_mbid != job.canonical_meta.mb_recording_id
    if orig_title and job.canonical_meta.title:
        ratio = SequenceMatcher(None, orig_title.lower(), job.canonical_meta.title.lower()).ratio()
        return ratio < 0.5
    return False


def _first_orig(job: TrackJob, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = job.orig_tags.get(key)
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        if value:
            text = str(value).strip()
            if text:
                return text
    return None


def _orig_year(job: TrackJob) -> int | None:
    for key in ("date", "year", "TDRC", "\xa9day"):
        raw = job.orig_tags.get(key)
        if isinstance(raw, list):
            raw = ".".join(raw)
        if raw:
            digits = "".join(ch for ch in str(raw) if ch.isdigit())[:4]
            if len(digits) == 4:
                return int(digits)
    return None


__all__ = [
    "identify_from_fallback",
    "identify_job",
    "metadata_from_orig_tags",
    "metadata_from_query",
]
