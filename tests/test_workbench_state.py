"""Tests for Workbench operation/session state (docs/14 M1)."""

from __future__ import annotations

import pytest

from harvester.ui.operation_state import (
    Operation,
    OperationBusyError,
    OperationToken,
    WorkbenchOperationState,
)


def test_loading_a_track_invalidates_old_operations_and_clears_dirty_state() -> None:
    state = WorkbenchOperationState()
    first = state.load_track("track-a")
    token = state.begin(Operation.SEPARATING)
    state.mark_dirty(token)

    second = state.load_track("track-b")

    assert second == 2
    assert state.generation == 2
    assert state.track_key == "track-b"
    assert state.operation is Operation.IDLE
    assert state.dirty is False
    assert state.is_current(token) is False
    assert state.cancel_requested is False
    assert first == 1


def test_only_one_operation_can_run_and_stale_tokens_cannot_finish() -> None:
    state = WorkbenchOperationState()
    state.load_track("track-a")
    token = state.begin(Operation.HOSTED_SEPARATION)

    with pytest.raises(OperationBusyError):
        state.begin(Operation.DIARIZATION)

    assert state.is_current(token)
    stale = OperationToken(token.generation - 1, token.operation, token.track_key)
    assert state.is_current(stale) is False
    assert state.finish(stale) is False
    assert state.operation is Operation.HOSTED_SEPARATION

    assert state.request_cancel(token) is True
    assert state.cancel_requested is True
    assert state.finish(token) is True
    assert state.operation is Operation.IDLE
    assert state.cancel_requested is False


def test_finish_keeps_dirty_state_only_when_requested() -> None:
    state = WorkbenchOperationState()
    state.load_track("track-a")
    token = state.begin(Operation.SAVE_LAYERS)
    assert state.finish(token, dirty=False) is True
    assert state.dirty is False

    token = state.begin(Operation.LAYER_BUILD)
    assert state.finish(token, dirty=True) is True
    assert state.dirty is True
    state.clear_dirty()
    assert state.dirty is False


def test_idle_token_is_never_current() -> None:
    state = WorkbenchOperationState()
    state.load_track("track-a")
    idle = OperationToken(state.generation, Operation.IDLE, "track-a")
    assert state.is_current(idle) is False
