"""UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7)."""

from __future__ import annotations

import asyncio

import pytest

from harvester.models import ErrorClass, ErrorInfo, EventKind, JobEvent, State
from harvester.ui.bridge import FlushPlan, UiBridge, coalesce_events


def test_coalesce_keeps_latest_state_per_job_in_order() -> None:
    events = [
        JobEvent(job_id="a", kind=EventKind.STATE, state=State.QUEUED),
        JobEvent(job_id="a", kind=EventKind.PROGRESS),
        JobEvent(job_id="b", kind=EventKind.STATE, state=State.ANALYZING),
        JobEvent(job_id="a", kind=EventKind.STATE, state=State.HUNTING),
    ]

    plan = coalesce_events(events)

    assert plan.job_ids == ["a", "b"]
    assert plan.drained == 4
    assert not plan.log_lines
    assert not plan.hint_lines


def test_coalesce_batches_logs_in_order() -> None:
    events = [
        JobEvent(job_id="a", kind=EventKind.LOG, level="INFO", text="one"),
        JobEvent(job_id="a", kind=EventKind.LOG, level="WARNING", text="two"),
    ]

    plan = coalesce_events(events)

    assert plan.log_lines == [("INFO", "one"), ("WARNING", "two")]
    assert plan.job_ids == []


def test_coalesce_extracts_error_hint() -> None:
    events = [
        JobEvent(
            job_id="a",
            kind=EventKind.ERROR,
            level="ERROR",
            text="boom",
            error=ErrorInfo(error_class=ErrorClass.DISK, message="boom", user_hint="free space"),
        )
    ]

    plan = coalesce_events(events)

    assert plan.hint_lines == ["free space"]
    assert plan.log_lines == [("ERROR", "boom")]


def test_empty_plan_has_no_content() -> None:
    assert not coalesce_events([]).has_content


@pytest.mark.asyncio
async def test_bridge_coalesces_1000_event_storm_into_one_flush() -> None:
    events: asyncio.Queue[JobEvent] = asyncio.Queue()
    flushes: list[FlushPlan] = []
    bridge = UiBridge(events, interval_s=0.01, apply=lambda plan: flushes.append(plan))

    for index in range(1000):
        events.put_nowait(
            JobEvent(job_id=str(index % 10), kind=EventKind.PROGRESS)
        )

    task = asyncio.create_task(bridge.run())
    await asyncio.sleep(0.05)
    bridge.stop()
    await task

    assert bridge.flushes == 1  # only the first tick had content to flush
    assert len(flushes[0].job_ids) == 10  # 1000 events coalesced to 10 jobs
    assert sum(plan.drained for plan in flushes) == 1000
    assert bridge.flushes == 1


@pytest.mark.asyncio
async def test_bridge_pairs_task_done_for_every_event() -> None:
    events: asyncio.Queue[JobEvent] = asyncio.Queue()
    bridge = UiBridge(events, interval_s=0.01, apply=lambda plan: None)
    for index in range(50):
        events.put_nowait(JobEvent(job_id=str(index), kind=EventKind.LOG, level="INFO", text="x"))

    plan = bridge.drain_now()

    assert plan.drained == 50
    await asyncio.wait_for(events.join(), timeout=1.0)  # every get paired with task_done