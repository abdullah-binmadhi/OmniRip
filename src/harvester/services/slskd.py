"""Async slskd REST client with health, search, download, and transfer polling."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from harvester.config import AppConfig
from harvester.models import P2PCandidate
from harvester.util.circuit import CircuitBreaker
from harvester.util.errors import (
    ServiceUnavailable,
    TransientNetwork,
    ValidationError,
)

_SEARCH_PATH = "/api/v0/searches"
_SESSION_PATH = "/api/v0/session"
_TRANSFERS_PATH = "/api/v0/transfers/downloads"
_OPENAPI_PATH = "/swagger/v0/swagger.json"

_STATE_DONE = {"Completed", "Completed?", "TimedOut"}
_STATE_FAILED = {"Errored", "Cancelled", "Rejected", "Removed"}
_STATE_ACTIVE = {"Requested", "Queued", "Transferring", "InProgress"}


@dataclass(slots=True)
class SlskdFile:
    filename: str
    size_bytes: int | None = None
    duration_s: float | None = None
    bit_depth: int | None = None
    sample_rate: int | None = None
    bitrate: int | None = None
    vbr: bool | None = None


@dataclass(slots=True)
class SearchResponse:
    user: str
    speed_kbps: int | None = None
    queue_length: int | None = None
    files: tuple[SlskdFile, ...] = ()


class SlskdService:
    """Talk to the local slskd daemon; policy stays in the pipeline."""

    def __init__(
        self,
        config: AppConfig,
        *,
        registry=None,
        client: httpx.AsyncClient | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.config = config
        self.logger = logging.getLogger("harvester.services.slskd")
        self.breaker = breaker or CircuitBreaker(failure_threshold=3, open_seconds=60.0)
        self._client = client
        self._download_semaphore = asyncio.Semaphore(config.slskd.max_concurrent_downloads)
        self._openapi_checked = False
        self._download_route: str | None = None
        self._api_key = os.environ.get(config.slskd.api_key_env) or ""

    @property
    def available(self) -> bool:
        return self.config.slskd.enabled and self.breaker.available

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.slskd.url,
                headers={"X-API-Key": self._api_key} if self._api_key else {},
                timeout=httpx.Timeout(self.config.timeouts.health_s * 3),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def check_health(self) -> bool:
        client = await self._get_client()
        try:
            response = await client.get(_SESSION_PATH)
        except httpx.HTTPError as exc:
            self.breaker.record_failure(str(exc))
            return False
        if response.status_code in {404, 405}:
            self.breaker.record_failure("session endpoint missing; slskd API may differ")
            return False
        if response.status_code in {401, 403}:
            self.breaker.record_failure("slskd rejected the API key")
            return False
        if response.status_code >= 500:
            self.breaker.record_failure(f"session HTTP {response.status_code}")
            return False
        self.breaker.record_success()
        return True

    async def ensure_openapi_verified(self) -> bool:
        if not self.config.slskd.verify_openapi or self._openapi_checked:
            self._openapi_checked = True
            return True
        client = await self._get_client()
        try:
            swagger = (await client.get(_OPENAPI_PATH)).raise_for_status().json()
        except httpx.HTTPError as exc:
            self.breaker.record_failure(f"OpenAPI check failed: {exc}")
            return False
        paths = _concrete_paths(set(swagger.get("paths", {})))
        known = {_SESSION_PATH, _SEARCH_PATH, _TRANSFERS_PATH}
        missing = {path for path in known if path not in paths}
        if missing:
            self.logger.warning("slskd OpenAPI missing expected paths: %s", sorted(missing))
        self._download_route = _pick_download_route(paths)
        self._openapi_checked = True
        return True

    async def search(
        self,
        queries: Iterable[str],
        *,
        timeout_s: float,
        poll_interval_s: float | None = None,
    ) -> list[SearchResponse]:
        client = await self._get_client()
        poll = poll_interval_s or self.config.slskd.poll_interval_s
        results: list[SearchResponse] = []
        deadline = time.monotonic() + timeout_s
        for query in queries:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            token = abs(hash(query)) % (2**31 - 1)
            try:
                created = await client.post(
                    _SEARCH_PATH,
                    json={"searchText": query, "token": token},
                )
                created.raise_for_status()
                body = created.json()
                search_id = body.get("id") or body.get("token")
                if search_id is None:
                    raise ValidationError("slskd search response had no id")
                while time.monotonic() < deadline:
                    polled = await client.get(f"{_SEARCH_PATH}/{search_id}")
                    polled.raise_for_status()
                    payload = polled.json()
                    parsed = _parse_search_payload(payload)
                    if parsed:
                        results.extend(parsed)
                    if payload.get("isComplete") or payload.get("state") in {
                        "Completed",
                        "Complete",
                    }:
                        break
                    await asyncio.sleep(poll)
            except (httpx.HTTPError, ValidationError) as exc:
                self.breaker.record_failure(str(exc))
                return results
        return results

    async def download(
        self,
        candidate: P2PCandidate,
        *,
        download_dir: Path | None = None,
    ) -> Path:
        if not self.available:
            raise ServiceUnavailable("slskd lane is unavailable")
        async with self._download_semaphore:
            client = await self._get_client()
            await self.ensure_openapi_verified()
            route = self._download_route or _DEFAULT_DOWNLOAD_ROUTE
            # slskd 0.26+ takes a bare file array on /transfers/downloads/{username};
            # older versions wrapped the files in an object on /users/{username}/downloads.
            if "transfers" in route:
                payload = [{"filename": candidate.filename}]
            else:
                payload = {
                    "files": [{"filename": candidate.filename}],
                    "username": candidate.username,
                }
            try:
                response = await client.post(
                    route.format(username=candidate.username, token="download"),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                self.breaker.record_failure(str(exc))
                raise TransientNetwork(f"slskd download request failed: {exc}") from exc
            await self._wait_for_completion(candidate)
        return await self._locate_completed(candidate, download_dir)

    async def _wait_for_completion(self, candidate: P2PCandidate) -> None:
        client = await self._get_client()
        deadline = self.config.slskd.search_timeout_s * 4
        started = time.monotonic()
        last_progress = time.monotonic()
        last_bytes = 0
        while time.monotonic() - started < deadline:
            try:
                response = await client.get(_TRANSFERS_PATH)
                response.raise_for_status()
                entries = (
                    response.json()
                    if isinstance(response.json(), list)
                    else response.json().get("transfers", [])
                )
            except (httpx.HTTPError, ValueError) as exc:
                self.breaker.record_failure(str(exc))
                raise TransientNetwork(f"slskd transfer poll failed: {exc}") from exc
            for entry in entries:
                if _matches_candidate(entry, candidate):
                    state = str(entry.get("state", "InProgress"))
                    if state in _STATE_DONE:
                        return
                    if state in _STATE_FAILED:
                        raise TransientNetwork(f"slskd transfer ended as {state}")
                    bytes_now = int(entry.get("bytesTransferred", 0))
                    if bytes_now != last_bytes:
                        last_progress = time.monotonic()
                        last_bytes = bytes_now
                    break
            if time.monotonic() - last_progress > self.config.slskd.stall_timeout_s:
                raise TransientNetwork("slskd transfer stalled with no progress")
            await asyncio.sleep(self.config.slskd.poll_interval_s)
        raise TransientNetwork("slskd transfer exceeded timeout")

    async def _locate_completed(self, candidate: P2PCandidate, download_dir: Path | None) -> Path:
        base = download_dir or self.config.slskd.download_dir.expanduser()
        direct = base / candidate.username / candidate.filename
        if direct.is_file() and direct.stat().st_size > 0:
            return direct
        for path in base.rglob(candidate.filename):
            if path.is_file() and path.stat().st_size > 0:
                return path
        raise ValidationError("slskd completed transfer but the file was not found")


def _concrete_paths(paths: set[str]) -> set[str]:
    """Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.

    0.26 serves ``/api/v{version}/searches``-style templates instead of the literal
    ``/api/v0/searches`` URLs it actually routes to; normalize the templates so the
    D6 presence-check and route picker compare apples to apples.
    """

    return {p.replace("/v{version}", "/v0").replace("/v{version:apiVersion}", "/v0") for p in paths}


def _pick_download_route(paths: set[str]) -> str | None:
    candidates = (
        "/api/v0/transfers/downloads/{username}",
        "/api/v0/users/{username}/downloads/{token}",
        "/api/v0/users/{username}/downloads/{token}/{filename}",
    )
    concrete = _concrete_paths(paths)
    for candidate in candidates:
        pattern = re.sub(r"\{[a-zA-Z]+\}", "[^/]+", candidate)
        if any(re.fullmatch(pattern, path) for path in concrete):
            return candidate
    return None


def _parse_search_payload(payload: Mapping[str, Any]) -> list[SearchResponse]:
    responses = payload.get("responses") or []
    if not isinstance(responses, list):
        return []
    parsed: list[SearchResponse] = []
    for item in responses:
        user = item.get("user") or ""
        speed = _int_or_none(item.get("speed"))
        queue = _int_or_none(item.get("queueLength"))
        files = [
            SlskdFile(
                filename=_text(file.get("filename")),
                size_bytes=_int_or_none(file.get("size")),
                duration_s=_float_or_none(file.get("duration")),
                bit_depth=_int_or_none(file.get("bitDepth")),
                sample_rate=_int_or_none(file.get("sampleRate")),
                bitrate=_int_or_none(file.get("bitrate")),
                vbr=_bool_or_none(file.get("vbr", file.get("isVariableBitRate"))),
            )
            for file in item.get("files", [])
            if _text(file.get("filename"))
        ]
        if user and files:
            parsed.append(SearchResponse(user, speed, queue, tuple(files)))
    return parsed


def _matches_candidate(entry: Mapping[str, Any], candidate: P2PCandidate) -> bool:
    user = entry.get("user") or entry.get("username") or ""
    filename = entry.get("filename") or ""
    return user == candidate.username and filename == candidate.filename


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def filter_search_responses(
    responses: Iterable[SearchResponse],
    *,
    lossless_only: bool = False,
    min_bitrate: int | None = None,
    min_speed_kbps: int | None = None,
    max_queue_depth: int | None = None,
) -> list[SearchResponse]:
    """Filter search responses by audio quality, peer speed, and queue length."""
    results: list[SearchResponse] = []
    for resp in responses:
        if min_speed_kbps is not None and resp.speed_kbps is not None:
            if resp.speed_kbps < min_speed_kbps:
                continue
        if max_queue_depth is not None and resp.queue_length is not None:
            if resp.queue_length > max_queue_depth:
                continue

        filtered_files: list[SlskdFile] = []
        for file in resp.files:
            ext = Path(file.filename).suffix.lower()
            if lossless_only:
                if ext not in {".flac", ".wav", ".aif", ".aiff"}:
                    continue
            if min_bitrate is not None and file.bitrate is not None:
                if file.bitrate < min_bitrate:
                    continue
            filtered_files.append(file)

        if filtered_files:
            results.append(
                SearchResponse(
                    user=resp.user,
                    speed_kbps=resp.speed_kbps,
                    queue_length=resp.queue_length,
                    files=tuple(filtered_files),
                )
            )
    return results


_DEFAULT_DOWNLOAD_ROUTE = "/api/v0/transfers/downloads/{username}"


__all__ = [
    "SearchResponse",
    "SlskdFile",
    "SlskdService",
    "filter_search_responses",
]
