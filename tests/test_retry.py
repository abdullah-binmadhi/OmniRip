import asyncio

import pytest

from harvester.util.retry import backoff_delay, sleep_backoff


def test_backoff_has_expected_bounds() -> None:
    assert backoff_delay(0, random_fn=lambda: 0.0) == pytest.approx(1.5)
    assert backoff_delay(1, random_fn=lambda: 1.0) == pytest.approx(5.0)
    assert backoff_delay(99, random_fn=lambda: 1.0) <= 60.0


@pytest.mark.asyncio
async def test_sleep_backoff_is_async(monkeypatch) -> None:
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    result = await sleep_backoff(0, random_fn=lambda: 0.5)

    assert result == pytest.approx(2.0)
    assert delays == [pytest.approx(2.0)]
