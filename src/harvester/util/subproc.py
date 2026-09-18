"""Tracked subprocess lifecycle helpers for cancellation-safe services."""

from __future__ import annotations

import asyncio
import os
from typing import Any


class SubprocessRegistry:
    """Track child processes by job key so cancellation can kill the right work."""

    def __init__(self) -> None:
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

    async def register(self, key: str, process: asyncio.subprocess.Process) -> None:
        async with self._lock:
            self._processes[key] = process

    async def unregister(self, key: str) -> None:
        async with self._lock:
            self._processes.pop(key, None)

    async def get(self, key: str) -> asyncio.subprocess.Process | None:
        async with self._lock:
            return self._processes.get(key)

    async def terminate(self, key: str, *, grace_s: float = 5.0) -> None:
        process = await self.get(key)
        if process is None or process.returncode is not None:
            await self.unregister(key)
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=grace_s)
        except TimeoutError:
            process.kill()
            await process.wait()
        finally:
            await self.unregister(key)

    async def terminate_prefix(self, prefix: str, *, grace_s: float = 5.0) -> None:
        async with self._lock:
            keys = tuple(key for key in self._processes if key.startswith(prefix))
        await asyncio.gather(
            *(self.terminate(key, grace_s=grace_s) for key in keys),
            return_exceptions=True,
        )

    async def terminate_all(self, *, grace_s: float = 5.0) -> None:
        async with self._lock:
            keys = tuple(self._processes)
        await asyncio.gather(
            *(self.terminate(key, grace_s=grace_s) for key in keys),
            return_exceptions=True,
        )

    async def keys(self) -> tuple[str, ...]:
        async with self._lock:
            return tuple(self._processes)


def subprocess_options() -> dict[str, Any]:
    """Return portable process-group options for subprocess creation."""

    return {"start_new_session": True} if os.name == "posix" else {}


__all__ = ["SubprocessRegistry", "subprocess_options"]
