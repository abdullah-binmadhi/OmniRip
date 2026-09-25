"""Asynchronous startup checks for local binaries and optional services."""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from harvester.config import AppConfig


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    name: str
    available: bool
    required: bool
    path: Path | None = None
    version: str | None = None
    detail: str = ""

    @property
    def severity(self) -> str:
        if self.available:
            return "ok"
        return "error" if self.required else "warning"

    @property
    def icon(self) -> str:
        if self.available:
            return "●"
        return "✗" if self.required else "▲"


@dataclass(frozen=True, slots=True)
class EnvironmentStatus:
    dependencies: Mapping[str, DependencyStatus]

    @property
    def ready(self) -> bool:
        return not self.missing_required

    @property
    def missing_required(self) -> tuple[DependencyStatus, ...]:
        return tuple(
            status
            for status in self.dependencies.values()
            if status.required and not status.available
        )

    def get(self, name: str) -> DependencyStatus:
        return self.dependencies[name]

    def display_lines(self) -> tuple[str, ...]:
        return tuple(
            f"{status.name}: {self._display_detail(status)}"
            for status in self.dependencies.values()
        )

    @staticmethod
    def _display_detail(status: DependencyStatus) -> str:
        return status.detail or ("available" if status.available else "unavailable")


async def _run_version(command: Sequence[str], timeout_s: float = 10.0) -> tuple[bool, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        return False, str(exc)

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return False, f"version check timed out after {timeout_s:g}s"

    output = (stdout or stderr).decode("utf-8", errors="replace").strip()
    first_line = output.splitlines()[0] if output else ""
    if process.returncode != 0:
        return False, first_line or f"process exited with status {process.returncode}"
    return True, first_line or "available"


async def probe_binary(
    name: str,
    command: str,
    *,
    required: bool,
    version_flag: str,
) -> DependencyStatus:
    """Find a configured executable and run its version command without blocking the loop."""

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return DependencyStatus(name, False, required, detail=f"invalid command: {exc}")
    if not parts:
        return DependencyStatus(name, False, required, detail="no executable configured")

    resolved = await asyncio.to_thread(shutil.which, parts[0])
    if not resolved:
        return DependencyStatus(name, False, required, detail=f"{parts[0]!r} not found on PATH")

    ok, detail = await _run_version([resolved, *parts[1:], version_flag])
    return DependencyStatus(
        name=name,
        available=ok,
        required=required,
        path=Path(resolved),
        version=detail if ok else None,
        detail=detail,
    )


async def check_slskd(config: AppConfig) -> DependencyStatus:
    """Check slskd health and, optionally, whether its OpenAPI endpoint is reachable."""

    if not config.slskd.enabled:
        return DependencyStatus("slskd", False, False, detail="disabled by configuration")

    secret = os.environ.get(config.slskd.api_key_env)
    headers = {"X-API-Key": secret} if secret else {}
    timeout = httpx.Timeout(config.timeouts.health_s)
    try:
        async with httpx.AsyncClient(
            base_url=config.slskd.url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v0/session")
            if response.status_code in {401, 403}:
                return DependencyStatus(
                    "slskd", False, False, detail="daemon rejected the API key (401/403)"
                )
            response.raise_for_status()
            detail = "connected"
            if config.slskd.verify_openapi:
                openapi = await client.get("/swagger/v0/swagger.json")
                if openapi.is_success:
                    detail = "connected; OpenAPI available"
                else:
                    detail = f"connected; OpenAPI check returned HTTP {openapi.status_code}"
            return DependencyStatus("slskd", True, False, detail=detail)
    except httpx.TimeoutException:
        return DependencyStatus("slskd", False, False, detail="health check timed out")
    except httpx.HTTPStatusError as exc:
        return DependencyStatus("slskd", False, False, detail=f"HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        return DependencyStatus("slskd", False, False, detail=f"connection failed: {exc}")


async def detect_environment(
    config: AppConfig,
    *,
    check_slskd_service: bool = True,
) -> EnvironmentStatus:
    """Run independent dependency checks concurrently."""

    binary_tasks = {
        "ffmpeg": probe_binary(
            "ffmpeg", config.ffmpeg.binary, required=True, version_flag="-version"
        ),
        "ffprobe": probe_binary(
            "ffprobe", config.ffmpeg.probe_binary, required=True, version_flag="-version"
        ),
        "fpcalc": probe_binary("fpcalc", "fpcalc", required=False, version_flag="-version"),
        "yt-dlp": probe_binary(
            "yt-dlp", config.ytdlp.binary, required=True, version_flag="--version"
        ),
    }
    binary_results = await asyncio.gather(*binary_tasks.values())
    dependencies = dict(zip(binary_tasks, binary_results, strict=True))

    if check_slskd_service:
        dependencies["slskd"] = await check_slskd(config)
    else:
        dependencies["slskd"] = DependencyStatus("slskd", False, False, detail="check disabled")

    acoustid_available = bool(os.environ.get(config.acoustid.api_key_env))
    dependencies["acoustid"] = DependencyStatus(
        "acoustid",
        acoustid_available,
        False,
        detail="API key configured" if acoustid_available else "API key not configured",
    )
    jev_available = config.jev.enabled and bool(os.environ.get(config.jev.api_key_env))
    if not config.jev.enabled:
        jev_detail = "disabled by configuration"
    elif not jev_available:
        jev_detail = "API key not configured"
    else:
        jev_detail = "advisory triage enabled"
    dependencies["jev"] = DependencyStatus("jev", jev_available, False, detail=jev_detail)
    return EnvironmentStatus(dependencies)


__all__ = [
    "DependencyStatus",
    "EnvironmentStatus",
    "check_slskd",
    "detect_environment",
    "probe_binary",
]
