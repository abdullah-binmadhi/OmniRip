"""Cover Art Archive client with a release-MBID disk cache."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from harvester.config import AppConfig

_FRONT_ENDPOINT = "https://coverartarchive.org/release/{release_id}/front-500"
_MAX_EMBED_BYTES = 400_000


class CoverArtService:
    """Best-effort front-cover fetching; failures never fail a job."""

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


__all__ = ["CoverArtService"]
