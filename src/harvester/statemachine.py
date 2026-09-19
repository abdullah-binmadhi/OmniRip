"""The single source of truth for legal job-state transitions.

``State`` lives here (with the machine that governs it) so this module never imports
``harvester.models`` — breaking the import cycle that a lazy ``models → statemachine``
import would otherwise create. ``models`` re-exports ``State`` for callers that
prefer the data-model namespace.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum


class State(StrEnum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    HUNTING = "HUNTING"
    P2P_DOWNLOADING = "P2P_DOWNLOADING"
    FALLBACK_DOWNLOADING = "FALLBACK_DOWNLOADING"
    IDENTIFYING = "IDENTIFYING"
    SPECTRAL_CHECK = "SPECTRAL_CHECK"
    POLISHING = "POLISHING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def terminal(self) -> bool:
        return self in {State.COMPLETED, State.SKIPPED, State.FAILED, State.CANCELLED}


class IllegalTransition(RuntimeError):
    """Raised when a job attempts a transition not allowed by the workflow."""

    def __init__(
        self,
        current: State,
        target: State,
        *,
        fallback_attempted: bool = False,
    ) -> None:
        suffix = " after fallback was attempted" if fallback_attempted else ""
        super().__init__(f"Illegal job transition {current.value} -> {target.value}{suffix}")
        self.current = current
        self.target = target
        self.fallback_attempted = fallback_attempted


_BASE_TRANSITIONS: Mapping[State, frozenset[State]] = {
    State.QUEUED: frozenset({State.ANALYZING}),
    State.ANALYZING: frozenset({State.HUNTING, State.SKIPPED}),
    State.HUNTING: frozenset({State.P2P_DOWNLOADING, State.FALLBACK_DOWNLOADING}),
    State.P2P_DOWNLOADING: frozenset(
        {State.IDENTIFYING, State.HUNTING, State.FALLBACK_DOWNLOADING}
    ),
    State.FALLBACK_DOWNLOADING: frozenset({State.IDENTIFYING}),
    State.IDENTIFYING: frozenset({State.SPECTRAL_CHECK, State.POLISHING}),
    State.SPECTRAL_CHECK: frozenset({State.POLISHING, State.FALLBACK_DOWNLOADING}),
    State.POLISHING: frozenset({State.COMPLETED}),
    State.COMPLETED: frozenset(),
    State.SKIPPED: frozenset(),
    State.FAILED: frozenset(),
    State.CANCELLED: frozenset(),
}


def legal_transitions(
    current: State,
    *,
    fallback_attempted: bool = False,
) -> frozenset[State]:
    """Return legal next states, including universal failure/cancel paths."""

    transitions = set(_BASE_TRANSITIONS[current])
    if not current.terminal:
        transitions.update({State.FAILED, State.CANCELLED})
    if fallback_attempted:
        transitions.discard(State.HUNTING)
        transitions.discard(State.SPECTRAL_CHECK)
    return frozenset(transitions)


def is_transition_allowed(
    current: State,
    target: State,
    *,
    fallback_attempted: bool = False,
) -> bool:
    """Return whether a transition is valid without mutating any state."""

    if current == target:
        return True
    return target in legal_transitions(current, fallback_attempted=fallback_attempted)


def assert_transition(
    current: State,
    target: State,
    *,
    fallback_attempted: bool = False,
) -> None:
    """Raise :class:`IllegalTransition` when the transition is not valid."""

    if not is_transition_allowed(current, target, fallback_attempted=fallback_attempted):
        raise IllegalTransition(current, target, fallback_attempted=fallback_attempted)


__all__ = [
    "IllegalTransition",
    "State",
    "assert_transition",
    "is_transition_allowed",
    "legal_transitions",
]
