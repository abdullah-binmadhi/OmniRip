import pytest

from harvester.models import Mode, State, TrackJob
from harvester.statemachine import IllegalTransition, is_transition_allowed, legal_transitions


def test_happy_path_transitions_are_allowed() -> None:
    path = [
        State.QUEUED,
        State.ANALYZING,
        State.HUNTING,
        State.P2P_DOWNLOADING,
        State.IDENTIFYING,
        State.SPECTRAL_CHECK,
        State.POLISHING,
        State.COMPLETED,
    ]
    assert all(
        is_transition_allowed(current, target)
        for current, target in zip(path, path[1:], strict=False)
    )


def test_fallback_path_skips_spectral_check() -> None:
    path = [
        State.HUNTING,
        State.FALLBACK_DOWNLOADING,
        State.IDENTIFYING,
        State.POLISHING,
        State.COMPLETED,
    ]
    assert all(
        is_transition_allowed(current, target)
        for current, target in zip(path, path[1:], strict=False)
    )


def test_every_non_terminal_state_can_fail_or_cancel() -> None:
    for state in State:
        if not state.terminal:
            assert State.FAILED in legal_transitions(state)
            assert State.CANCELLED in legal_transitions(state)


def test_terminal_states_cannot_restart() -> None:
    for terminal in (State.COMPLETED, State.SKIPPED, State.FAILED, State.CANCELLED):
        assert not legal_transitions(terminal)


def test_fallback_attempted_blocks_hunt_and_spectral_reentry() -> None:
    assert not is_transition_allowed(State.P2P_DOWNLOADING, State.HUNTING, fallback_attempted=True)
    assert not is_transition_allowed(
        State.IDENTIFYING, State.SPECTRAL_CHECK, fallback_attempted=True
    )


def test_track_job_uses_guarded_state_changes() -> None:
    job = TrackJob(mode=Mode.SINGLE_URL)
    job.transition(State.ANALYZING)
    assert job.state is State.ANALYZING

    with pytest.raises(IllegalTransition):
        job.transition(State.COMPLETED)
