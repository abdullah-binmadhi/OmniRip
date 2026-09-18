from harvester.util.circuit import BreakerState, CircuitBreaker


def test_breaker_opens_after_three_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=3, open_seconds=60.0)

    assert breaker.available
    breaker.record_failure("a")
    breaker.record_failure("b")
    assert breaker.available
    breaker.record_failure("c")

    assert breaker.state is BreakerState.OPEN
    assert not breaker.available


def test_breaker_recovers_after_open_window() -> None:
    clock = {"now": 0.0}

    def fake_clock() -> float:
        return clock["now"]

    breaker = CircuitBreaker(failure_threshold=1, open_seconds=30.0, clock=fake_clock)
    breaker.record_failure("boom")
    assert not breaker.available

    clock["now"] = 31.0
    assert breaker.available
    assert breaker.state is BreakerState.HALF_OPEN

    breaker.record_success()
    assert breaker.state is BreakerState.CLOSED


def test_failure_in_half_open_reopens() -> None:
    clock = {"now": 0.0}
    breaker = CircuitBreaker(failure_threshold=1, open_seconds=10.0, clock=lambda: clock["now"])
    breaker.record_failure("x")
    assert breaker.state is BreakerState.OPEN
    clock["now"] = 11.0
    assert breaker.available
    assert breaker.state is BreakerState.HALF_OPEN

    breaker.record_failure("y")
    assert breaker.state is BreakerState.OPEN
    assert breaker.last_failure_reason == "y"
