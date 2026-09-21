"""Tests for the detached layer terminal app (layer_terminal.py)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from textual.widgets import Button, Static

from harvester.analysis.enhancement.layer_editor import EditPlan
from harvester.analysis.enhancement.layers import (
    LayerIssue,
    LayerSegment,
    LayerSource,
    LayerTrack,
)
from harvester.ipc.layer_sidecar import (
    TransportState,
    read_sidecar,
    read_transport,
    transport_path,
    write_sidecar,
    write_transport,
)
from harvester.ui.layer_studio import LayerStudio
from harvester.ui.layer_terminal import LayerTerminalApp


def _build_track(stem_dir) -> LayerTrack:
    """A minimal in-memory LayerTrack (no WAVs needed for the sidecar/app)."""
    sources = {
        "vocals": LayerSource(
            name="vocals",
            path=Path(stem_dir) / "song_bs_roformer_layer_vocals.wav",
            rms=np.asarray([-18.5, -20.1], dtype=np.float32),
            peak=np.asarray([0.92, 0.71], dtype=np.float32),
        ),
        "bass": LayerSource(
            name="bass",
            path=Path(stem_dir) / "song_bs_roformer_layer_bass.wav",
            rms=np.asarray([-22.0, -23.4], dtype=np.float32),
            peak=np.asarray([0.4, 0.3], dtype=np.float32),
        ),
    }
    segments = [
        LayerSegment(
            index=0,
            start_s=0.0,
            end_s=1.0,
            levels={"vocals": 0.69, "bass": 0.63},
            issues=[LayerIssue("vocal_bleed", "bass", 0.82)],
        ),
        LayerSegment(
            index=1,
            start_s=1.0,
            end_s=2.0,
            levels={"vocals": 0.66, "bass": 0.61},
            issues=[],
        ),
    ]
    return LayerTrack(
        duration_s=2.0,
        sample_rate=44100,
        segment_size_s=1.0,
        sources=sources,
        segments=segments,
        engine="bs_roformer",
    )


def _write_minimal_sidecar(tmp_path) -> Path:
    sidecar = tmp_path / "layer_sidecar.json"
    track = _build_track(tmp_path)
    plan = EditPlan()
    plan.add("vocals", 1, "de_bleed")
    write_sidecar(track, plan, sidecar)
    return sidecar


async def test_layer_terminal_mounts(tmp_path) -> None:
    """The standalone app mounts the reused LayerStudio and loads the sidecar."""
    sidecar = _write_minimal_sidecar(tmp_path)
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._load_error is None
        studio = app.query_one("#lt-studio", LayerStudio)
        assert studio.track is not None
        assert studio.track.n_segments == 2
        assert studio.track.active_layers == ["vocals", "bass"]
        assert studio.edit_plan is not None
        assert studio.edit_plan.get("vocals", 1) == "de_bleed"
        # The tools palette exposes every supported surgical op.
        assert app.query_one("#lt-op-de_bleed", Button) is not None


async def test_layer_terminal_edit_and_commit_writes_sidecar(tmp_path) -> None:
    """A staged cell edit then COMMIT EDITS persists the plan back to the sidecar."""
    sidecar = _write_minimal_sidecar(tmp_path)
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        studio = app.query_one("#lt-studio", LayerStudio)
        # Select the bass cell at second 0 and mute it with the cell key.
        studio._selected_idx = 0
        studio._selected_layer = "bass"
        await pilot.press("m")
        await pilot.pause()
        assert app.edit_plan is not None
        assert app.edit_plan.get("bass", 0) == "mute"

        # COMMIT EDITS -> sidecar now carries the newly staged edit.
        app.query_one("#lt-btn-commit", Button).focus()
        await pilot.press("enter")
        await pilot.pause()
        restored, plan = read_sidecar(sidecar)
        assert restored.n_segments == 2
        assert plan[("bass", 0)] == "mute"


async def test_layer_terminal_quit_key(tmp_path) -> None:
    """Pressing q cleanly closes the detached layer terminal."""
    sidecar = _write_minimal_sidecar(tmp_path)
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.is_running
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


async def test_layer_terminal_playhead_follows_main_app_transport(tmp_path) -> None:
    """The detached page moves with the song: it reads the main app's transport
    file (playhead + playing state) and drives its own timeline from it."""
    sidecar = _write_minimal_sidecar(tmp_path)
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        studio = app.query_one("#lt-studio", LayerStudio)
        assert studio.playhead_s == pytest.approx(0.0)

        # The main app plays on: it publishes a moving playhead.
        write_transport(
            transport_path(sidecar),
            TransportState(playhead_s=1.5, playing=True, duration_s=2.0),
        )
        app._poll_transport()
        await pilot.pause()

        assert studio.playhead_s == pytest.approx(1.5)
        assert app._transport.playing is True
        status = str(app.query_one("#lt-status", Static).content)
        assert "▶" in status
        assert "2 lanes" in status


async def test_layer_terminal_seek_and_play_requests_reach_the_main_app(tmp_path) -> None:
    """Clicking a cell / pressing space writes seek + play requests for the main app."""
    sidecar = _write_minimal_sidecar(tmp_path)
    write_transport(
        transport_path(sidecar),
        TransportState(playhead_s=0.0, playing=False, duration_s=2.0),
    )
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        app._poll_transport()

        # space → ask the main app (which owns audio) to start playing.
        await pilot.press("space")
        await pilot.pause()
        assert read_transport(transport_path(sidecar)).play_request is True

        # A click on the arrangement requests a seek to that second.
        studio = app.query_one("#lt-studio", LayerStudio)
        studio.post_message(LayerStudio.SeekRequested(1.0, "bass"))
        await pilot.pause()
        state = read_transport(transport_path(sidecar))
        assert state.seek_request == pytest.approx(1.0)


async def test_layer_terminal_reloads_lanes_when_sidecar_changes(tmp_path) -> None:
    """A rebuild/commit in the main app refreshes the lanes here (mtime watch)."""
    sidecar = _write_minimal_sidecar(tmp_path)
    app = LayerTerminalApp(sidecar_path=sidecar)

    async with app.run_test() as pilot:
        await pilot.pause()
        studio = app.query_one("#lt-studio", LayerStudio)
        assert len(studio.track.active_layers) == 2

        # The main app detected more lanes and rewrote the sidecar.
        track = _build_track(tmp_path)
        track.sources["kick"] = LayerSource(
            name="kick",
            path=Path(tmp_path) / "song_bs_roformer_layer_kick.wav",
            rms=np.asarray([-14.0, -15.0], dtype=np.float32),
            peak=np.asarray([0.7, 0.6], dtype=np.float32),
        )
        write_sidecar(track, EditPlan(), sidecar)

        app._poll_sidecar()
        await pilot.pause()

        assert "kick" in studio.track.active_layers
        assert len(studio.track.active_layers) == 3
