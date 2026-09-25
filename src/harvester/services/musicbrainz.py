"""
MusicBrainz clients: cover art (release MBID) and recording credits.

The credit lookup is the deterministic half of the lane plan (``docs/13``):
MusicBrainz documents *which* instruments and voices are on a recording, so the
Layer Studio can plan lanes from documented data instead of guessing. Credits
are advisory — a credited instrument may be inaudible in the mix, and many
recordings have no credits at all — so the plan marks every lane's origin and
never fabricates an audio row for a credited-only instrument.

Both lookups are best-effort: a failure never fails a job.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from harvester.config import AppConfig

_FRONT_ENDPOINT = "https://coverartarchive.org/release/{release_id}/front-500"
_RECORDING_ENDPOINT = "https://musicbrainz.org/ws/2/recording/{recording_id}"
_MAX_EMBED_BYTES = 400_000

# MusicBrainz requires a descriptive User-Agent on every web-service request.
_USER_AGENT = "OmniRip/0.1 ( https://github.com/omnirip )"


@dataclass(frozen=True, slots=True)
class Credit:
    """One credited contributor: an instrument, a vocal part, or a role."""

    name: str
    artist: str = ""
    artist_id: str = ""
    relation_type: str = ""
    attributes: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        """``double bass — Mich Gerber`` style label for the UI."""
        return f"{self.name} — {self.artist}" if self.artist else self.name


@dataclass(frozen=True, slots=True)
class RecordingCredits:
    """MusicBrainz artist relationships for one recording."""

    recording_id: str
    title: str = ""
    instruments: tuple[Credit, ...] = ()
    vocals: tuple[Credit, ...] = ()
    performers: tuple[Credit, ...] = ()
    producers: tuple[Credit, ...] = ()
    genres: tuple[tuple[str, int], ...] = ()

    @property
    def genre_names(self) -> tuple[str, ...]:
        return tuple(name for name, _count in self.genres)

    @property
    def singer_count(self) -> int | None:
        """Distinct credited vocalists, or None when the recording is undocumented."""
        artists = {c.artist for c in self.vocals if c.artist}
        if artists:
            return len(artists)
        return None

    @property
    def instrument_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.instruments if c.name)

    @property
    def lane_credits(self) -> tuple[Credit, ...]:
        """Credits that can annotate a lane: instruments + vocal parts.

        Performers and producers are deliberately excluded — "producer" is not
        a lane, and an unlabelled performance credit would add noise rows.
        """
        return (*self.instruments, *self.vocals)

    @property
    def empty(self) -> bool:
        return not (self.instruments or self.vocals or self.performers or self.producers)

    def summary(self) -> str:
        """Compact one-line account for the CREDITS panel / status line."""
        if self.empty:
            return "no credits documented in MusicBrainz"
        parts: list[str] = []
        if self.instruments:
            parts.append("instruments: " + ", ".join(c.label for c in self.instruments))
        if self.vocals:
            singers = self.singer_count or 0
            parts.append(f"vocals ({singers}): " + ", ".join(c.label for c in self.vocals))
        if not parts and self.performers:
            parts.append("performers: " + ", ".join(c.label for c in self.performers))
        return " · ".join(parts)


def _parse_credits(payload: dict[str, object], recording_id: str) -> RecordingCredits:
    """Split MusicBrainz artist-rels into instrument / vocal / other buckets."""
    instruments: list[Credit] = []
    vocals: list[Credit] = []
    performers: list[Credit] = []
    producers: list[Credit] = []

    relations = payload.get("relations")
    if isinstance(relations, list):
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            rel_type = str(rel.get("type", "") or "")
            raw_attributes = rel.get("attributes")
            attributes = tuple(
                str(a) for a in raw_attributes if isinstance(a, (str, int, float))
            ) if isinstance(raw_attributes, list) else ()
            artist_raw = rel.get("artist")
            artist_obj: dict[str, object] = artist_raw if isinstance(artist_raw, dict) else {}
            artist = str(artist_obj.get("name", "") or "")
            artist_id = str(artist_obj.get("id", "") or "")
            name = ", ".join(attributes) if attributes else rel_type
            credit = Credit(
                name=name,
                artist=artist,
                artist_id=artist_id,
                relation_type=rel_type,
                attributes=attributes,
            )
            if rel_type == "instrument":
                instruments.append(credit)
            elif rel_type == "vocal":
                vocals.append(credit)
            elif rel_type == "producer":
                producers.append(credit)
            elif rel_type in ("performer", "performance"):
                performers.append(credit)

    genres: dict[str, int] = {}
    for field in ("genres", "tags"):
        entries = payload.get(field)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "") or "").strip()
            if not name or name in genres:
                continue
            try:
                count = int(entry.get("count", 0) or 0)
            except (TypeError, ValueError):
                count = 0
            genres[name] = max(1, count)

    title = str(payload.get("title", "") or "")
    return RecordingCredits(
        recording_id=recording_id,
        genres=tuple(sorted(genres.items(), key=lambda item: item[1], reverse=True)),
        title=title,
        instruments=tuple(instruments),
        vocals=tuple(vocals),
        performers=tuple(performers),
        producers=tuple(producers),
    )


class CoverArtService:
    """MusicBrainz best-effort lookups (cover art + recording credits)."""

    def __init__(
        self,
        config: AppConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self.logger = logging.getLogger("harvester.services.musicbrainz")

    async def fetch_front(self, release_id: str) -> bytes | None:
        if not release_id:
            return None
        cached = await asyncio.to_thread(self._read_cache, release_id)
        if cached is not None:
            return cached
        client = await self._get_client()
        try:
            response = await client.get(_FRONT_ENDPOINT.format(release_id=release_id))
        except httpx.HTTPError as exc:
            self.logger.info("cover art fetch failed for %s: %s", release_id, exc)
            return None
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            self.logger.info("cover art HTTP %s for %s", response.status_code, release_id)
            return None
        data = response.content
        if not data or len(data) > _MAX_EMBED_BYTES:
            return None
        await asyncio.to_thread(self._write_cache, release_id, data)
        return data

    async def fetch_recording_credits(self, recording_id: str) -> RecordingCredits | None:
        """Documented instruments / vocals for one recording (cached on disk)."""
        if not recording_id:
            return None
        cached = await asyncio.to_thread(self._read_credits_cache, recording_id)
        if cached is not None:
            return cached
        client = await self._get_client()
        try:
            response = await client.get(
                _RECORDING_ENDPOINT.format(recording_id=recording_id),
                params={"inc": "artist-rels+genres+tags", "fmt": "json"},
                headers={"User-Agent": _USER_AGENT},
            )
        except httpx.HTTPError as exc:
            self.logger.info("credits fetch failed for %s: %s", recording_id, exc)
            return None
        if response.status_code != 200:
            self.logger.info("credits HTTP %s for %s", response.status_code, recording_id)
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        credits = _parse_credits(payload, recording_id)
        await asyncio.to_thread(self._write_credits_cache, recording_id, credits)
        return credits

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeouts.coverart_s),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _cache_dir(self) -> Path:
        return (self.config.paths.cache / "art").resolve()

    def _credits_cache_dir(self) -> Path:
        return (self.config.paths.cache / "credits").resolve()

    def _read_cache(self, release_id: str) -> bytes | None:
        path = self._cache_dir() / f"{release_id}.jpg"
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path.read_bytes()
        except OSError:
            pass
        return None

    def _write_cache(self, release_id: str, data: bytes) -> None:
        cache_dir = self._cache_dir()
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / f"{release_id}.jpg"
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
        except OSError as exc:
            self.logger.warning("cover art cache write failed: %s", exc)

    def _read_credits_cache(self, recording_id: str) -> RecordingCredits | None:
        path = self._credits_cache_dir() / f"{recording_id}.json"
        try:
            if not path.is_file() or path.stat().st_size == 0:
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return _parse_credits(data, recording_id)

    def _write_credits_cache(self, recording_id: str, credits: RecordingCredits) -> None:
        cache_dir = self._credits_cache_dir()
        payload = {
            "id": recording_id,
            "title": credits.title,
            "genres": [{"name": name, "count": count} for name, count in credits.genres],
            "relations": [
                {
                    "type": c.relation_type,
                    "attributes": list(c.attributes),
                    "artist": {"id": c.artist_id, "name": c.artist},
                }
                for c in (*credits.instruments, *credits.vocals, *credits.performers, *credits.producers)
            ],
        }
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / f"{recording_id}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            temporary.replace(target)
        except OSError as exc:
            self.logger.warning("credits cache write failed: %s", exc)


__all__ = ["CoverArtService", "Credit", "RecordingCredits"]
