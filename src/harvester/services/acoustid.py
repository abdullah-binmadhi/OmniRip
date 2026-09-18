"""AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shlex
import shutil
import sqlite3
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from harvester.config import AppConfig
from harvester.models import CanonicalMetadata
from harvester.util.subproc import SubprocessRegistry, subprocess_options

_LOOKUP_ENDPOINT = "https://api.acoustid.org/v2/lookup"
_HIGH_CONFIDENCE = 0.85
_MEDIUM_CONFIDENCE = 0.6


@dataclass(frozen=True, slots=True)
class Fingerprint:
    duration: float
    value: str

    @property
    def cache_key(self) -> str:
        return hashlib.sha256(f"{self.duration:.3f}:{self.value}".encode()).hexdigest()


class AcoustidService:
    """Fingerprint files and resolve canonical metadata, never failing the job."""

    def __init__(
        self,
        config: AppConfig,
        *,
        registry: SubprocessRegistry | None = None,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self.registry = registry or SubprocessRegistry()
        self._client = client
        self._clock = clock
        self.logger = logging.getLogger("harvester.services.acoustid")
        self._tokens: list[float] = []
        self._lock = asyncio.Lock()

    @property
    def api_key(self) -> str:
        return os.environ.get(self.config.acoustid.api_key_env, "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def identify(self, path: Path, *, job_id: str | None = None) -> CanonicalMetadata | None:
        """Fingerprint a file and resolve metadata; return None to use the fallback chain."""

        fingerprint = await self.fingerprint(path, job_id=job_id)
        if fingerprint is None:
            return None
        return await self.lookup(fingerprint, job_id=job_id)

    async def fingerprint(self, path: Path, *, job_id: str | None = None) -> Fingerprint | None:
        binary = await self._resolve_fpcalc()
        if binary is None:
            return None
        try:
            process = await asyncio.create_subprocess_exec(
                *binary,
                "-json",
                "-length",
                "120",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_options(),
            )
        except OSError as exc:
            self.logger.warning("fpcalc could not start: %s", exc)
            return None
        key = f"{job_id or 'identify'}:fpcalc:{id(process)}"
        await self.registry.register(key, process)
        try:
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.config.timeouts.fpcalc_s
                )
            except TimeoutError:
                await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
                return None
        finally:
            await self.registry.unregister(key)
        if process.returncode != 0:
            self.logger.warning(
                "fpcalc failed on %s: %s",
                path.name,
                (stderr or b"").decode("utf-8", errors="replace").strip(),
            )
            return None
        try:
            payload = json.loads((stdout or b"").decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None
        fingerprint = str(payload.get("fingerprint", ""))
        try:
            duration = float(payload["duration"])
        except (KeyError, TypeError, ValueError):
            return None
        if not fingerprint or duration <= 0:
            return None
        return Fingerprint(duration=duration, value=fingerprint)

    async def lookup(
        self, fingerprint: Fingerprint, *, job_id: str | None = None
    ) -> CanonicalMetadata | None:
        cached = await asyncio.to_thread(self._read_cache, fingerprint.cache_key)
        if cached is not None:
            await self._mark_cache_used(job_id)
            return cached
        if not self.configured:
            return None
        payload = await self._lookup_remote(fingerprint, job_id=job_id)
        if payload is None:
            return None
        metadata = _select_metadata(payload)
        if metadata is not None:
            await asyncio.to_thread(
                self._write_cache, fingerprint.cache_key, metadata, job_id=job_id
            )
        return metadata

    async def _lookup_remote(
        self, fingerprint: Fingerprint, *, job_id: str | None
    ) -> Mapping[str, Any] | None:
        client = await self._get_client()
        await self._acquire_token()
        form = {
            "client": self.api_key,
            "format": "json",
            "meta": "recordings+releases+releasegroups+isrcs",
            "duration": str(int(fingerprint.duration)),
            "fingerprint": fingerprint.value,
        }
        for attempt in range(2):
            try:
                response = await client.post(_LOOKUP_ENDPOINT, data=form)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("AcoustID lookup failed (attempt %d): %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                return None
            if payload.get("status") != "ok":
                return None
            return payload
        return None

    async def _acquire_token(self) -> None:
        async with self._lock:
            now = self._clock()
            self._tokens = [t for t in self._tokens if t > now - 1.0]
            if len(self._tokens) >= max(1, int(self.config.acoustid.rate_limit_per_s)):
                oldest = self._tokens[0]
                await asyncio.sleep(1.0 - (now - oldest))
                now = self._clock()
                self._tokens = [t for t in self._tokens if t > now - 1.0]
            self._tokens.append(now)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeouts.acoustid_s),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _resolve_fpcalc(self) -> list[str] | None:
        try:
            parts = shlex.split("fpcalc")
        except ValueError:
            return None
        executable = await asyncio.to_thread(shutil.which, parts[0])
        if not executable:
            self.logger.warning("fpcalc binary not found; falling back to probe metadata")
            return None
        return [executable, *parts[1:]]

    def _db_path(self) -> Path:
        return self.config.paths.cache / "acoustid.sqlite3"

    def _read_cache(self, cache_key: str) -> CanonicalMetadata | None:
        db = self._db_path()
        if not db.exists():
            return None
        try:
            connection = sqlite3.connect(db)
            try:
                row = connection.execute(
                    "SELECT response_json, fetched_at FROM lookups WHERE fp_hash = ?",
                    (cache_key,),
                ).fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        fetched_at = datetime.fromisoformat(row[1])
        ttl = timedelta(days=self.config.acoustid.cache_ttl_days)
        if datetime.now(UTC) - fetched_at > ttl:
            return None
        cache_hit = getattr(self, "_last_cache_hit", None)
        if cache_hit is not None:
            cache_hit[0] = cache_key
        return _metadata_from_json(row[0])

    def _write_cache(
        self, cache_key: str, metadata: CanonicalMetadata, *, job_id: str | None
    ) -> None:
        db = self._db_path()
        db.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(db)
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS lookups (
                        fp_hash TEXT PRIMARY KEY,
                        duration REAL NOT NULL,
                        response_json TEXT NOT NULL,
                        fetched_at TEXT NOT NULL
                    )"""
                )
                connection.execute(
                    "INSERT OR REPLACE INTO lookups VALUES (?, ?, ?, ?)",
                    (
                        cache_key,
                        0.0,
                        _metadata_to_json(metadata),
                        datetime.now(UTC).isoformat(),
                    ),
                )
                connection.commit()
            finally:
                connection.close()
        except sqlite3.Error as exc:
            self.logger.warning("AcoustID cache write failed: %s", exc)

    async def _mark_cache_used(self, job_id: str | None) -> None:
        self.logger.info("AcoustID cache hit for job %s", job_id or "-")


def _select_metadata(payload: Mapping[str, Any]) -> CanonicalMetadata | None:
    results = payload.get("results") or []
    if not isinstance(results, list):
        return None
    for result in results:
        score = _score(result.get("score"))
        if score is None or score <= _MEDIUM_CONFIDENCE:
            continue
        recordings = result.get("recordings") or []
        if not recordings:
            continue
        recording = recordings[0]
        title = _text(recording.get("title"))
        artists = tuple(
            _text(artist.get("name"))
            for artist in recording.get("artists", [])
            if _text(artist.get("name"))
        )
        releases = recording.get("releases") or []
        release = _earliest_release(releases)
        year = _release_year(release)
        isrcs = recording.get("isrcs") or []
        return CanonicalMetadata(
            title=title or None,
            artists=artists,
            album=_text(release.get("title")) if release else None,
            year=year,
            isrc=_text(isrcs[0]) if isrcs else None,
            mb_recording_id=_text(recording.get("id")) or None,
            mb_release_id=_text(release.get("id")) if release else None,
            confidence=score,
            source="acoustid",
        )
    return None


def _earliest_release(releases: Any) -> Mapping[str, Any] | None:
    if not isinstance(releases, list):
        return None
    dated = [
        release
        for release in releases
        if isinstance(release, Mapping) and _release_year(release) is not None
    ]
    if not dated:
        return releases[0] if releases and isinstance(releases[0], Mapping) else None
    return min(dated, key=lambda release: _release_year(release) or 9999)


def _release_year(release: Any) -> int | None:
    if not isinstance(release, Mapping):
        return None
    date = release.get("date")
    if isinstance(date, Mapping):
        return _number(date.get("year"))
    return None


def _metadata_from_json(raw: str) -> CanonicalMetadata | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    raw_artists = payload.get("artists")
    artist_list = raw_artists if isinstance(raw_artists, list) else []
    return CanonicalMetadata(
        title=_text(payload.get("title")),
        artists=tuple(str(artist) for artist in artist_list),
        album=_text(payload.get("album")),
        year=_number(payload.get("year")) if payload.get("year") is not None else None,
        isrc=_text(payload.get("isrc")),
        mb_recording_id=_text(payload.get("mb_recording_id")),
        mb_release_id=_text(payload.get("mb_release_id")),
        confidence=_score(payload.get("confidence"))
        if payload.get("confidence") is not None
        else None,
        source=_text(payload.get("source")) or "acoustid",
    )


def _metadata_to_json(metadata: CanonicalMetadata) -> str:
    return json.dumps(metadata.to_dict(), ensure_ascii=False)


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value).strip() if value is not None else ""


def _score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _number(value: Any) -> int | None:
    """Parse a numeric field as an integer (years and similar); None when not numeric."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = ["AcoustidService", "Fingerprint"]
