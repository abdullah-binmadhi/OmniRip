"""Killable yt-dlp subprocess integration for Mode A."""

from __future__ import annotations

import asyncio
import json
import re
import shlex
import shutil
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harvester.config import AppConfig
from harvester.models import DownloadProgress
from harvester.util.errors import (
    ConfigError,
    PermanentSource,
    RateLimited,
    TransientNetwork,
    ValidationError,
)
from harvester.util.subproc import SubprocessRegistry, subprocess_options

ProgressCallback = Callable[[DownloadProgress], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class YtdlpProgress:
    progress: DownloadProgress
    raw_line: str


_PROGRESS_PATTERN = re.compile(r"^download:(?P<fields>.*)$")
_SPEED_PATTERN = re.compile(r"(?P<number>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>[KMGTP]?i?B/s)?", re.I)


class YtdlpService:
    """Probe and download with yt-dlp while keeping progress machine-readable."""

    def __init__(self, config: AppConfig, registry: SubprocessRegistry | None = None) -> None:
        self.config = config
        self.registry = registry or SubprocessRegistry()

    async def _resolve(self) -> list[str]:
        try:
            parts = shlex.split(self.config.ytdlp.binary)
        except ValueError as exc:
            raise ConfigError(f"invalid yt-dlp command: {exc}") from exc
        if not parts:
            raise ConfigError("yt-dlp command cannot be empty")
        executable = await asyncio.to_thread(shutil.which, parts[0])
        if not executable:
            raise ConfigError(f"required executable {parts[0]!r} was not found on PATH")
        return [executable, *parts[1:]]

    @staticmethod
    def parse_progress(line: str) -> YtdlpProgress | None:
        match = _PROGRESS_PATTERN.match(line.strip())
        if not match:
            return None
        fields = match.group("fields").split("|")
        if len(fields) < 4:
            return None
        percent = _parse_percent(fields[0])
        bytes_done = _parse_int(fields[1])
        bytes_total = _parse_optional_int(fields[2])
        speed_bps = _parse_speed(fields[3])
        return YtdlpProgress(
            DownloadProgress(
                bytes_done=bytes_done,
                bytes_total=bytes_total,
                speed_bps=speed_bps,
                percent=percent,
            ),
            line.strip(),
        )

    @staticmethod
    def classify_failure(stderr: str, returncode: int) -> type[Exception]:
        lower = stderr.lower()
        if "http error 429" in lower or "too many requests" in lower:
            return RateLimited
        if any(
            token in lower
            for token in (
                "sign in to confirm",
                "age-restricted",
                "private video",
                "video unavailable",
                "video has been removed",
                "unsupported url",
                "no video formats",
                "is live",
                "premiere",
                "drm",
                "widevine",
            )
        ):
            return PermanentSource
        if returncode == 0:
            return ValidationError
        return TransientNetwork

    async def probe_url(self, url: str, *, job_id: str | None = None) -> dict[str, Any]:
        binary = await self._resolve()
        command = [
            *binary,
            "-J",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            url,
        ]
        stdout, stderr, returncode = await self._run_buffered(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.probe_s,
        )
        if returncode != 0:
            self._raise_failure(stderr, returncode, operation="metadata probe")
        try:
            metadata = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError("yt-dlp returned invalid metadata JSON") from exc
        if not isinstance(metadata, dict):
            raise ValidationError("yt-dlp metadata response was not an object")
        return metadata

    async def probe_playlist(self, url: str, *, job_id: str | None = None) -> list[dict[str, Any]]:
        """Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10).

        A non-playlist URL yields an empty list, which callers treat as a single track.
        """

        binary = await self._resolve()
        command = [
            *binary,
            "-J",
            "--flat-playlist",
            "--skip-download",
            "--no-warnings",
            url,
        ]
        stdout, stderr, returncode = await self._run_buffered(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.probe_s,
        )
        if returncode != 0:
            self._raise_failure(stderr, returncode, operation="playlist probe")
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError("yt-dlp returned invalid playlist JSON") from exc
        if not isinstance(data, dict):
            raise ValidationError("yt-dlp playlist response was not an object")
        entries = data.get("entries") or []
        return [entry for entry in entries if isinstance(entry, dict)]

    async def download(
        self,
        url: str,
        workspace_dir: Path,
        *,
        job_id: str,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        binary = await self._resolve()
        output_template = workspace_dir / f"{job_id}.%(ext)s"
        command = [
            *binary,
            "-f",
            self.config.ytdlp.format,
            "--no-playlist",
            "--newline",
            "--no-warnings",
            "--progress-template",
            "download:%(progress._percent_str)s|%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s|%(progress._speed_str)s|%(progress._eta_str)s",
            "-o",
            str(output_template),
        ]
        if self.config.ytdlp.cookies_from_browser:
            command.extend(["--cookies-from-browser", self.config.ytdlp.cookies_from_browser])
        command.append(url)

        await self._run_streaming(
            command,
            job_id=job_id,
            progress_callback=progress_callback,
        )
        outputs = [
            path
            for path in workspace_dir.glob(f"{job_id}.*")
            if path.is_file() and not path.name.endswith((".part", ".ytdl"))
        ]
        if not outputs:
            raise ValidationError("yt-dlp completed without producing an audio file")
        output = max(outputs, key=lambda path: path.stat().st_mtime_ns)
        if output.stat().st_size <= 0:
            raise ValidationError("yt-dlp produced an empty audio file")
        return output

    async def _run_buffered(
        self,
        command: list[str],
        *,
        job_id: str | None,
        timeout_s: float,
    ) -> tuple[str, str, int]:
        key = f"{job_id or 'probe'}:yt-dlp:{id(command)}"
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_options(),
            )
        except OSError as exc:
            raise ConfigError(f"could not start yt-dlp: {exc}") from exc
        await self.registry.register(key, process)
        try:
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
            except TimeoutError as exc:
                await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
                raise TransientNetwork(
                    f"yt-dlp {('metadata probe' if job_id is None else 'operation')} timed out",
                    user_hint="Try again later or update yt-dlp if the extractor is stale.",
                ) from exc
        finally:
            await self.registry.unregister(key)
        return (
            (stdout or b"").decode("utf-8", errors="replace"),
            (stderr or b"").decode("utf-8", errors="replace"),
            process.returncode or 0,
        )

    async def _run_streaming(
        self,
        command: list[str],
        *,
        job_id: str,
        progress_callback: ProgressCallback | None,
    ) -> None:
        key = f"{job_id}:yt-dlp:{id(command)}"
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_options(),
            )
        except OSError as exc:
            raise ConfigError(f"could not start yt-dlp: {exc}") from exc
        await self.registry.register(key, process)
        lines: asyncio.Queue[tuple[str, bytes | None]] = asyncio.Queue()
        tasks = [
            asyncio.create_task(self._read_stream("stdout", process.stdout, lines)),
            asyncio.create_task(self._read_stream("stderr", process.stderr, lines)),
        ]
        stderr_tail: deque[str] = deque(maxlen=30)
        finished_streams = 0
        last_progress = time.monotonic()
        try:
            async with asyncio.timeout(self.config.ytdlp.total_timeout_s):
                while finished_streams < 2:
                    try:
                        stream_name, raw_line = await asyncio.wait_for(lines.get(), timeout=1.0)
                    except TimeoutError:
                        if time.monotonic() - last_progress > self.config.ytdlp.stall_timeout_s:
                            raise TransientNetwork(
                                "yt-dlp download stalled with no progress",
                                user_hint=(
                                    "Retry the source later; the provider may be "
                                    "throttling the connection."
                                ),
                            ) from None
                        continue
                    if raw_line is None:
                        finished_streams += 1
                        continue
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if stream_name == "stderr":
                        stderr_tail.append(line)
                        continue
                    parsed = self.parse_progress(line)
                    if parsed is not None:
                        last_progress = time.monotonic()
                        if progress_callback is not None:
                            result = progress_callback(parsed.progress)
                            if asyncio.iscoroutine(result):
                                await result
                returncode = await process.wait()
        except TimeoutError as exc:
            await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
            raise TransientNetwork(
                f"yt-dlp download exceeded {self.config.ytdlp.total_timeout_s:g}s",
                user_hint="The source took too long; retry or choose another URL.",
            ) from exc
        except (PermanentSource, RateLimited, TransientNetwork, ValidationError):
            await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
            raise
        finally:
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.registry.unregister(key)
        if returncode != 0:
            self._raise_failure("\n".join(stderr_tail), returncode, operation="download")

    @staticmethod
    async def _read_stream(
        name: str,
        stream: asyncio.StreamReader | None,
        output: asyncio.Queue[tuple[str, bytes | None]],
    ) -> None:
        if stream is None:
            await output.put((name, None))
            return
        while True:
            line = await stream.readline()
            if not line:
                await output.put((name, None))
                return
            await output.put((name, line))

    @classmethod
    def _raise_failure(cls, stderr: str, returncode: int, *, operation: str) -> None:
        error_type = cls.classify_failure(stderr, returncode)
        detail = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown yt-dlp error"
        if error_type is RateLimited:
            raise RateLimited(
                f"yt-dlp {operation} was rate limited: {detail}",
                user_hint="Wait before retrying; the source provider returned HTTP 429.",
            )
        if error_type is PermanentSource:
            raise PermanentSource(
                f"yt-dlp cannot access this source: {detail}",
                user_hint="Check the URL, access permissions, cookies setting, or DRM status.",
            )
        if error_type is ValidationError:
            raise ValidationError(f"yt-dlp {operation} returned unusable output: {detail}")
        raise TransientNetwork(
            f"yt-dlp {operation} failed: {detail}",
            user_hint="Retry once; if it persists, update yt-dlp and check the URL.",
        )


def _parse_percent(value: str) -> float | None:
    cleaned = value.strip().replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value: str) -> int:
    try:
        return max(0, int(value.strip()))
    except ValueError:
        return 0


def _parse_optional_int(value: str) -> int | None:
    if not value.strip() or value.strip().lower() in {"na", "none", "unknown"}:
        return None
    return _parse_int(value)


def _parse_speed(value: str) -> float | None:
    match = _SPEED_PATTERN.search(value)
    if not match:
        return None
    number = float(match.group("number"))
    unit = (match.group("unit") or "B/s").lower()
    multipliers = {"b/s": 1, "kb/s": 1000, "kib/s": 1024, "mb/s": 1_000_000, "mib/s": 1_048_576}
    return number * multipliers.get(unit, 1)


__all__ = ["ProgressCallback", "YtdlpProgress", "YtdlpService"]
