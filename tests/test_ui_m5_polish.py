"""M5 detached terminal, lane provenance, keyboard and save-summary polish (docs/14)."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Label

from harvester.analysis.enhancement.lane_plan import (
    CONFIDENCE_BY_ORIGIN,
    ORIGIN_CREDIT,
    ORIGIN_HOSTED,
    ORIGIN_SEPARATOR,
    ORIGIN_TAG,
    LanePlan,
    LanePlanEntry,
)
from harvester.analysis.enhancement.layers import LayerSegment, LayerSource, LayerTrack
from harvester.models import Mode, TrackJob
from harvester.ui.layer_studio import LayerStudio
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.workbench import WorkbenchWidget


class M5TestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")
        yield LayerStudio(id="test-studio")


def _track_with_plan(tmp_path: Path) -> LayerTrack:
    import numpy as np

    plan = LanePlan(
        entries=(
            LanePlanEntry("vocals", ORIGIN_SEPARATOR, CONFIDENCE_BY_ORIGIN[ORIGIN_SEPARATOR]),
            LanePlanEntry("lead_vocals", ORIGIN_HOSTED, CONFIDENCE_BY_ORIGIN[ORIGIN_HOSTED]),
            LanePlanEntry("strings", ORIGIN_TAG, CONFIDENCE_BY_ORIGIN[ORIGIN_TAG], note="CLAP"),
            LanePlanEntry("guitar", ORIGIN_CREDIT, CONFIDENCE_BY_ORIGIN[ORIGIN_CREDIT], note="Mich Gerber"),
        ),
    )
    env = np.array([0.0], dtype=np.float32)
    track = LayerTrack(
        duration_s=8.0,
        sample_rate=44100,
        engine="neural",
        lane_plan=plan,
        segments=[LayerSegment(0, 0.0, 1.0, {"vocals": 1.0})],
    )
    for name in ("vocals", "lead_vocals", "strings", "guitar"):
        track.sources[name] = LayerSource(name, tmp_path / f"{name}.wav", env, env)
    return track


async def test_studio_provenance_filter_hides_nonmatching_rows(tmp_path: Path) -> None:
    """Cycling the provenance filter dims/hides rows from other origins."""
    app = M5TestApp()
    async with app.run_test() as pilot:
        studio = app.query_one("#test-studio", LayerStudio)
        studio.track = _track_with_plan(tmp_path)
        await pilot.pause()

        assert studio.provenance_filter == "all"
        all_rows = studio._filtered_layers()
        assert set(all_rows) == {"vocals", "lead_vocals", "strings", "guitar"}

        studio.cycle_provenance_filter()
        assert studio.provenance_filter == "audio"
        assert set(studio._filtered_layers()) == {"vocals"}

        studio.cycle_provenance_filter()
        assert studio.provenance_filter == "hosted"
        assert set(studio._filtered_layers()) == {"lead_vocals"}

        studio.cycle_provenance_filter()
        assert studio.provenance_filter == "credits"
        assert set(studio._filtered_layers()) == {"guitar"}

        studio.cycle_provenance_filter()
        assert studio.provenance_filter == "tags"
        assert set(studio._filtered_layers()) == {"strings"}

        studio.cycle_provenance_filter()
        assert studio.provenance_filter == "all"

        # The rendered footer announces the active filter.
        text = str(studio.render())
        assert "filter: all" in text


async def test_studio_unknown_origin_hidden_when_filtered(tmp_path: Path) -> None:
    """Lanes without a plan entry only appear in the 'all' view."""
    app = M5TestApp()
    async with app.run_test() as pilot:
        studio = app.query_one("#test-studio", LayerStudio)
        studio.track = _track_with_plan(tmp_path)
        await pilot.pause()

        studio.provenance_filter = "audio"
        unknown = "no_plan_lane"
        import numpy as np

        env = np.array([0.0], dtype=np.float32)
        studio.track.sources[unknown] = LayerSource(unknown, tmp_path / "n.wav", env, env)
        assert unknown not in studio._filtered_layers()
        studio.provenance_filter = "all"
        assert unknown in studio._filtered_layers()


async def test_layer_terminal_shows_ownership_banner(tmp_path: Path) -> None:
    """The detached terminal states who owns selection vs transport."""
    from harvester.ui.layer_terminal import LayerTerminalApp

    app = LayerTerminalApp(tmp_path / "layer_sidecar.json")
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Static

        banner = str(app.query_one("#lt-ownership", Static).render())
        assert "selection" in banner.lower()
        assert "transport" in banner.lower()


async def test_commit_summary_reports_edited_seconds(tmp_path: Path) -> None:
    """The save summary names files, edited seconds and the residual verdict."""
    app = M5TestApp()
    async with app.run_test():
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        summary = wb._layer_save_summary(
            written=["vocals.wav", "bass.wav"],
            edited_cells=3,
            n_segments=12,
            residual_note=" · mix residual ≤ -60 dBFS",
        )
        assert "vocals.wav" in summary and "bass.wav" in summary
        assert "3s edited" in summary
        assert "12s" in summary
        assert "residual" in summary


async def test_stale_terminal_transport_hint(tmp_path: Path) -> None:
    """A launched terminal that stopped beating gets one visible hint."""
    import time as _time

    app = M5TestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        dummy = tmp_path / "stale.mp3"
        dummy.write_bytes(b"mp3-data")
        wb.load_job(TrackJob(mode=Mode.SINGLE_URL, input_path=tmp_path / "src.opus", output_path=dummy))
        wb.switch_page("layers")
        await pilot.pause()

        sidecar = wb._layer_sidecar_path()
        assert sidecar is not None
        from harvester.ipc.layer_sidecar import terminal_path, write_terminal_heartbeat

        # A terminal whose last heartbeat payload is 90 s old (crashed without
        # cleanup): the age comes from the payload timestamp, not file mtime.
        write_terminal_heartbeat(sidecar, pid=1234)
        import json

        heartbeat = terminal_path(sidecar)
        payload = json.loads(heartbeat.read_text(encoding="utf-8"))
        payload["written_at"] = _time.time() - 90.0
        heartbeat.write_text(json.dumps(payload), encoding="utf-8")
        wb._layer_terminal_launched = True

        wb._publish_layer_transport()

        status = str(wb.query_one("#wb-layer-status", Label).render())
        assert "not responding" in status or "relaunch" in status

        # A fresh heartbeat does not re-raise the stale report after relaunch.
        write_terminal_heartbeat(sidecar, pid=1234)
        wb._terminal_stale_reported = False
        wb._publish_layer_transport()
        assert wb._terminal_stale_reported is False


async def test_terminal_heartbeat_round_trip(tmp_path: Path) -> None:
    """Heartbeat write/read/age and clean-exit removal behave."""
    from harvester.ipc.layer_sidecar import (
        clear_terminal_heartbeat,
        read_terminal_heartbeat,
        terminal_heartbeat_age_s,
        terminal_path,
        write_terminal_heartbeat,
    )

    sidecar = tmp_path / "layer_sidecar.json"
    assert read_terminal_heartbeat(sidecar) is None
    assert terminal_heartbeat_age_s(sidecar) is None

    write_terminal_heartbeat(sidecar, pid=42)
    beat = read_terminal_heartbeat(sidecar)
    assert beat is not None and beat["pid"] == 42
    written_at = float(str(beat.get("written_at", 0.0)))
    assert terminal_heartbeat_age_s(sidecar, now=written_at + 10.0) == 10.0
    assert terminal_path(sidecar).exists()

    clear_terminal_heartbeat(sidecar)
    assert read_terminal_heartbeat(sidecar) is None
