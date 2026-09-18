"""UI bridge: throttle and coalesce pipeline events into widget updates (docs/08 §3).

The pipeline emits ``JobEvent`` objects into a bounded queue. The bridge drains that
queue on a fixed cadence (``1 / ui.refresh_hz``), coalesces per-job STATE/PROGRESS to
their latest value, batches LOG/ERROR lines, and hands one ``FlushPlan`` per tick to the
application for rendering. Keeping this logic free of Textual imports makes the
coalescing contract unit-testable without a terminal (docs/08 §9).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field

from harvester.models import EventKind, JobEvent


@dataclass(slots=True)
class FlushPlan:
    """One throttled batch of UI updates."""

    job_ids: list[str] = field(default_factory=list)
    log_lines: list[tuple[str, str]] = field(default_factory=list)
    hint_lines: list[str] = field(default_factory=list)
    drained: int = 0

    @property
    def has_content(self) -> bool:
        return bool(self.job_ids or self.log_lines or self.hint_lines)


def coalesce_events(events: Sequence[JobEvent]) -> FlushPlan:
    """Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job."""
    plan = FlushPlan(drained=len(events))
    seen_jobs: set[str] = set()
    for event in events:
        if event.kind in (EventKind.STATE, EventKind.PROGRESS):
            if event.job_id not in seen_jobs:
                seen_jobs.add(event.job_id)
                plan.job_ids.append(event.job_id)
        elif event.kind is EventKind.LOG:
            if event.text:
                plan.log_lines.append((event.level or "INFO", event.text))
        elif event.kind is EventKind.ERROR:
            if event.text:
                plan.log_lines.append((event.level or "ERROR", event.text))
            if event.error and event.error.user_hint:
                plan.hint_lines.append(event.error.user_hint)
    return plan


Apply = Callable[[FlushPlan], Awaitable[None] | None]


class UiBridge:
    """Drain ``events`` on a fixed cadence and apply coalesced plans."""

    def __init__(
        self,
        events: asyncio.Queue[JobEvent],
        *,
        interval_s: float,
        apply: Apply,
        jobs_by_id: Mapping[str, object] | None = None,
    ) -> None:
        self.events = events
        self.interval_s = max(interval_s, 0.001)
        self.apply = apply
        self.jobs_by_id = jobs_by_id or {}
        self.flushes = 0
        self.drained = 0
        self._running = True

    def drain_now(self) -> FlushPlan:
        """Drain everything currently queued (non-blocking) and coalesce it."""
        batch: list[JobEvent] = []
        while True:
            try:
                batch.append(self.events.get_nowait())
            except asyncio.QueueEmpty:
                break
        for _ in batch:
            self.events.task_done()
        self.drained += len(batch)
        return coalesce_events(batch)

    async def run(self) -> None:
        """Loop forever, flushing at most once per ``interval_s``."""
        while self._running:
            await asyncio.sleep(self.interval_s)
            plan = self.drain_now()
            if plan.has_content:
                self.flushes += 1
            result = self.apply(plan)
            if asyncio.iscoroutine(result):
                await result

    def stop(self) -> None:
        self._running = False


__all__ = ["Apply", "FlushPlan", "UiBridge", "coalesce_events"]