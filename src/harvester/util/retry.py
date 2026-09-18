"""Async retry timing primitives shared by service integrations."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable


def backoff_delay(
    attempt: int,
    *,
    base_s: float = 2.0,
    cap_s: float = 60.0,
    random_fn: Callable[[], float] = random.random,
) -> float:
    """Return exponential backoff with the documented ±25% jitter."""

    if attempt < 0:
        raise ValueError("attempt must not be negative")
    raw = min(cap_s, base_s * (2**attempt))
    jitter = 0.75 + 0.5 * random_fn()
    return min(cap_s, raw * jitter)


async def sleep_backoff(
    attempt: int,
    *,
    base_s: float = 2.0,
    cap_s: float = 60.0,
    random_fn: Callable[[], float] = random.random,
) -> float:
    """Sleep asynchronously and return the actual delay used."""

    delay = backoff_delay(attempt, base_s=base_s, cap_s=cap_s, random_fn=random_fn)
    await asyncio.sleep(delay)
    return delay


__all__ = ["backoff_delay", "sleep_backoff"]
