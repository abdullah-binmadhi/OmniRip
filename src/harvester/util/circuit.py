"""Circuit breaker for the slskd lane (docs/09 §3)."""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum


class BreakerState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Fast-fail a dependency lane after consecutive failures."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        open_seconds: float = 60.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self._clock = clock
        self.state = BreakerState.CLOSED
        self.consecutive_failures = 0
        self.opened_at: float | None = None
        self.last_failure_reason: str | None = None

    @property
    def available(self) -> bool:
        if self.state is BreakerState.OPEN:
            if self.opened_at is not None and self._clock() - self.opened_at >= self.open_seconds:
                self.state = BreakerState.HALF_OPEN
                self.opened_at = None
                return True
            return False
        return self.state is BreakerState.CLOSED or self.state is BreakerState.HALF_OPEN

    def record_failure(self, reason: str | None = None) -> None:
        self.last_failure_reason = reason
        if self.state is BreakerState.HALF_OPEN:
            self.state = BreakerState.OPEN
            self.opened_at = self._clock()
            self.consecutive_failures = 1
            return
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = BreakerState.OPEN
            self.opened_at = self._clock()

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if self.state is not BreakerState.CLOSED:
            self.state = BreakerState.CLOSED


__all__ = ["BreakerState", "CircuitBreaker"]
