"""Mode A URL analysis stage."""

from __future__ import annotations

from urllib.parse import urlparse

from harvester.models import TrackJob
from harvester.services.ytdlp import YtdlpService
from harvester.util.errors import PermanentSource, ValidationError


def validate_url(url: str) -> str:
    """Validate and normalize a URL before passing it to yt-dlp."""

    normalized = url.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("input must be a complete http(s) URL")
    return normalized


async def analyze_url(job: TrackJob, ytdlp: YtdlpService) -> dict[str, object]:
    """Probe a single URL without downloading its media."""

    if not job.input_url:
        raise ValidationError("Mode A job has no input URL")
    job.input_url = validate_url(job.input_url)
    metadata = await ytdlp.probe_url(job.input_url, job_id=job.id)
    if bool(metadata.get("is_live")):
        raise PermanentSource(
            "live streams are not accepted as Mode A sources",
            user_hint="Retry the URL after the stream becomes a recorded video.",
        )
    job.probe_meta = metadata
    job.query_raw = build_query(metadata)
    return metadata


def build_query(metadata: dict[str, object]) -> str:
    """Build a deterministic fallback query from yt-dlp metadata."""

    artist = _text(metadata.get("artist")) or _text(metadata.get("uploader"))
    title = _text(metadata.get("track")) or _text(metadata.get("title"))
    if artist and title:
        return f"{artist} - {title}"
    if title and " - " in title:
        possible_artist, possible_title = title.split(" - ", 1)
        if possible_artist.strip() and possible_title.strip():
            return title
    return title or artist


def _text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value).strip() if value is not None else ""


__all__ = ["analyze_url", "build_query", "validate_url"]
