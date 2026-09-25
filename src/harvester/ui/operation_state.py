"""Track-scoped Workbench operation state (docs/14 M1).

This module is intentionally UI-agnostic. Textual workers can carry an
OperationToken and discard results when the user has loaded another track or
started a different operation. Keeping the state machine out of the widget
makes the race rules unit-testable without spinning up Textual.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "Operation",
    "OperationBusyError",
    "OperationToken",
    "WorkbenchOperationState",
]


class Operation(StrEnum):
    """Mutually exclusive Workbench operations."""

    IDLE = "idle"
    CREDITS = "credits"
    HOSTED_SEPARATION = "hosted_separation"
    DIARIZATION = "diarization"


class OperationBusyError(RuntimeError):
    """Raised when a second exclusive operation is requested."""


@dataclass(frozen=True, slots=True)
class OperationToken:
    """Immutable identity carried by an asynchronous operation."""

    generation: int
    operation: Operation
    track_key: str


@dataclass(slots=True)
class WorkbenchOperationState:
    """Track identity and the currently running exclusive operation."""

    generation: int = 0
    track_key: str = ""
    operation: Operation = Operation.IDLE
    cancel_requested: bool = False
    dirty: bool = False

    def load_track(self, track_key: str | None) -> int:
        """Switch context and invalidate every worker from the old track."""
        self.generation += 1
        self.track_key = str(track_key or "")
        self.operation = Operation.IDLE
        self.cancel_requested = False
        self.dirty = False
        return self.generation

    def begin(self, operation: Operation) -> OperationToken:
        """Start one exclusive operation for the current track."""
        if operation is Operation.IDLE:
            raise ValueError("idle is not an operation that can be started")
        if self.operation is not Operation.IDLE:
            raise OperationBusyError(
                f"{self.operation.value} is already running for {self.track_key or 'no track'}"
            )
        if not self.track_key:
            raise RuntimeError("cannot start a Workbench operation without a track")
        self.operation = operation
        self.cancel_requested = False
        return OperationToken(self.generation, operation, self.track_key)

    def is_current(self, token: OperationToken) -> bool:
        """Whether a worker result still belongs to the active track/operation."""
        return (
            token.operation is not Operation.IDLE
            and token.generation == self.generation
            and token.track_key == self.track_key
            and token.operation is self.operation
        )

    def request_cancel(self, token: OperationToken) -> bool:
        """Request cancellation only for the currently active operation."""
        if not self.is_current(token):
            return False
        self.cancel_requested = True
        return True

    def finish(self, token: OperationToken, *, dirty: bool | None = None) -> bool:
        """Finish a current operation; stale workers cannot change UI state."""
        if not self.is_current(token):
            return False
        self.operation = Operation.IDLE
        self.cancel_requested = False
        if dirty is not None:
            self.dirty = dirty
        return True

    def mark_dirty(self, token: OperationToken | None = None) -> bool:
        """Mark edits dirty, optionally requiring a current operation token."""
        if token is not None and not self.is_current(token):
            return False
        self.dirty = True
        return True

    def clear_dirty(self) -> None:
        """Mark the current track's staged edits as persisted."""
        self.dirty = False
