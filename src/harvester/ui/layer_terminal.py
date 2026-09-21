"""
Layer Terminal — standalone FL Studio-style layer editor (Option B).

Detached from the main OmniRip app: launched in its own Terminal.app window (or
as a background process on non-macOS), it reads a JSON sidecar file holding the
``LayerTrack`` and the pending edit plan, hands them to the reused
``LayerStudio`` widget unchanged, and writes staged edits back to the same
sidecar. The main app picks those edits up on the next SAVE LAYERS / export.

Two-way live link with the main app (which owns audio output):

* ``layer_sidecar.transport.json`` is polled at 5 Hz — the playhead, playing
  state and duration published by the main app drive this window's timeline, so
  it moves in lockstep with whatever is playing.
* Click-to-seek and ``space`` write seek / play-pause requests back into the
  transport file; the main app applies them to its player. Requests are
  re-issued until the published state confirms them, so a poll race cannot
  swallow a request.
* The sidecar itself is watched for changes, so a rebuild or commit in the main
  app refreshes the lanes here without restarting the terminal.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import shlex
import subprocess
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static

from harvester.analysis.enhancement.layer_editor import OP_LABELS, OPS, EditPlan
from harvester.analysis.enhancement.layers import LayerTrack
from harvester.ipc.layer_sidecar import (
    TransportState,
    clear_terminal_heartbeat,
    read_sidecar,
    read_transport,
    request_play_state,
    request_seek,
    transport_path,
    write_terminal_heartbeat,
)
from harvester.processing import engine_note
from harvester.ui.layer_studio import LayerStudio

logger = logging.getLogger(__name__)

TOOLS_CSS = """
#lt-tools {
    width: 38;
    height: 1fr;
    background: #10101c;
    border-right: solid #334455;
    padding: 0 1;
}
#lt-inspector {
    height: auto;
    margin: 1 0 0 0;
}
#lt-opgrid {
    height: 1fr;
}
.opbtn {
    width: 100%;
}
#lt-btn-commit {
    margin-top: 1;
}
#lt-btn-close {
    margin-top: 1;
}
"""


class LayerTerminalApp(App[None]):
    """Full-window detached layer editor driving the reused LayerStudio widget."""

    TITLE = "OmniRip — Layer Terminal"
    CSS = TOOLS_CSS + """
    Screen { layout: vertical; }
    #lt-root { width: 1fr; height: 1fr; }
    #lt-studio-scroll { height: 1fr; width: 1fr; }
    LayerStudio { width: 1fr; height: auto; }
    #lt-status {
        height: 1;
        background: #0d0e15;
        color: #aaccff;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
        ("left", "layer_left", "Scroll left"),
        ("right", "layer_right", "Scroll right"),
        ("home", "layer_home", "Scroll start"),
        ("end", "layer_end", "Scroll end"),
        ("m", "edit('mute')", "Mute cell"),
        ("b", "edit('de_bleed')", "De-bleed"),
        ("s", "edit('de_ess')", "De-ess"),
        ("u", "edit('de_mud')", "De-mud"),
        ("p", "edit('drum_punch')", "Punch"),
        ("h", "edit('de_hum')", "De-hum"),
        ("a", "edit('air_boost')", "Air+"),
        ("c", "edit('de_click')", "De-click"),
        ("g", "edit('noise_gate')", "Gate"),
        ("t", "edit('transient_tame')", "Tame"),
        ("r", "edit_reset", "Reset cell"),
        ("f", "cycle_filter", "Filter lanes"),
        ("space", "play_pause", "Play/pause (main app)"),
    ]

    def __init__(self, sidecar_path: Path) -> None:
        super().__init__()
        self.sidecar_path = Path(sidecar_path)
        self.track: LayerTrack | None = None
        self.edit_plan: EditPlan | None = None
        self._load_error: str | None = None
        self._transport = TransportState()
        self._pending_seek: float | None = None
        self._pending_play: bool | None = None
        self._last_sidecar_mtime: int = 0
        self._status_second: int = -1
        self._status_playing: bool | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="lt-root"):
            with Vertical(id="lt-tools"):
                yield Static(id="lt-inspector", classes="panel")
                with VerticalScroll(id="lt-opgrid"):
                    for op in OPS:
                        yield Button(
                            OP_LABELS.get(op, op.replace("_", "-").upper()).upper(),
                            id=f"lt-op-{op}",
                            classes="opbtn",
                        )
                yield Button("💾 COMMIT EDITS", id="lt-btn-commit", variant="success")
                yield Button("✕ CLOSE", id="lt-btn-close", variant="error")
            with VerticalScroll(id="lt-studio-scroll"):
                yield LayerStudio(id="lt-studio")
        # Ownership banner (docs/14 M5): selection is staged here, while the
        # playhead and transport belong to the main window.
        yield Static(
            "Selection & edits live in this terminal · playhead/transport owned "
            "by the main OmniRip window",
            id="lt-ownership",
        )
        yield Static(id="lt-status")

    async def on_mount(self) -> None:
        studio = self.query_one("#lt-studio", LayerStudio)
        # Playhead comes from the main app over the transport file, not from an
        # audio player this process does not own.
        studio.playhead_provider = lambda: self._transport.playhead_s
        # Liveness heartbeat (docs/14 M5): the main app reads this file to know
        # this window is still alive; rewritten every 5 s.
        self._write_heartbeat()
        self._heartbeat_timer = self.set_interval(5.0, self._write_heartbeat)
        try:
            track, plan_dict = await self._load()
            self.track = track
            plan = EditPlan()
            plan.edits.update(plan_dict)
            self.edit_plan = plan
            studio.track = track
            studio.edit_plan = plan
            plan_summary = track.lane_plan.summary() if track.lane_plan else ""
            self.sub_title = (
                f"LAYER TERMINAL · {engine_note(track.engine)} · "
                f"{len(track.active_layers)} lanes · {track.n_segments}s"
                + (f" · {plan_summary}" if plan_summary else "")
            )
            self._last_sidecar_mtime = self._sidecar_mtime()
            self._update_status()
        except Exception as exc:
            self._load_error = str(exc)
            self.query_one("#lt-status", Static).update(
                f"SIDECAR LOAD FAILED: {exc} — press q to quit"
            )
        self._transport = read_transport(transport_path(self.sidecar_path))
        self.set_interval(0.20, self._poll_transport)
        self.set_interval(0.50, self._poll_sidecar)

    async def _load(self) -> tuple[LayerTrack, dict]:
        return read_sidecar(self.sidecar_path)

    def _sidecar_mtime(self) -> int:
        try:
            return self.sidecar_path.stat().st_mtime_ns
        except OSError:
            return 0

    # ------------------------------------------------------------------
    # Live transport (playhead follows the main app's player)
    # ------------------------------------------------------------------
    def _poll_transport(self) -> None:
        if self._load_error is not None:
            return
        state = read_transport(transport_path(self.sidecar_path))
        if self._pending_seek is not None and abs(state.playhead_s - self._pending_seek) <= 0.75:
            # The main app moved to our requested position — request satisfied.
            self._pending_seek = None
        if self._pending_play is not None and state.playing == self._pending_play:
            self._pending_play = None
        if self._pending_seek is not None:
            request_seek(self.sidecar_path, self._pending_seek)
        if self._pending_play is not None:
            request_play_state(self.sidecar_path, self._pending_play)
        self._transport = state
        try:
            studio = self.query_one("#lt-studio", LayerStudio)
            if state.playhead_s != studio.playhead_s:
                studio.playhead_s = state.playhead_s
        except Exception:
            pass
        second = int(state.playhead_s)
        if second != self._status_second or state.playing != self._status_playing:
            self._status_second = second
            self._status_playing = state.playing
            self._update_status()

    def _poll_sidecar(self) -> None:
        """Reload the lanes when the main app rewrites the sidecar."""
        if self._load_error is not None:
            return
        mtime = self._sidecar_mtime()
        if mtime == 0 or mtime == self._last_sidecar_mtime:
            return
        self._last_sidecar_mtime = mtime
        try:
            track, plan_dict = read_sidecar(self.sidecar_path)
        except Exception as exc:
            logger.debug("sidecar reload skipped: %s", exc)
            return
        self.track = track
        plan = self.edit_plan or EditPlan()
        for cell, op in plan_dict.items():
            plan.edits.setdefault(cell, op)
        self.edit_plan = plan
        try:
            studio = self.query_one("#lt-studio", LayerStudio)
            studio.track = track
            studio.edit_plan = plan
        except Exception:
            pass
        self._update_status()

    # ------------------------------------------------------------------
    # UI feedback
    # ------------------------------------------------------------------
    def _update_status(self) -> None:
        count = self.edit_plan.count if self.edit_plan else 0
        engine = self.track.engine if self.track else "?"
        n_lanes = len(self.track.active_layers) if self.track else 0
        lanes = ", ".join(self.track.active_layers) if self.track else ""
        icon = "▶" if self._transport.playing else "⏸"
        pos = int(self._transport.playhead_s)
        duration = int(self._transport.duration_s or (self.track.duration_s if self.track else 0))
        stamp = f"{pos // 60:02d}:{pos % 60:02d}/{duration // 60:02d}:{duration % 60:02d}"
        self.query_one("#lt-status", Static).update(
            f"{icon} {stamp} · {engine} · {n_lanes} lanes [{lanes}] · "
            f"{count} edit(s) staged — space play/pause · click a cell to seek · "
            "cell keys: m mute · b bleed · s ess · u mud · p punch · r reset"
        )

    def _update_inspector(self, layer: str | None, start_s: float, end_s: float) -> None:
        if self.track is None:
            return
        seg = self.track.segment_at(start_s)
        lines: list[str] = []
        if seg is not None:
            lines.append(f"t={seg.start_s:.0f}s–{seg.end_s:.0f}s")
            lines.append(
                "levels: " + ", ".join(
                    f"{k} {int(v * 100)}%" for k, v in seg.levels.items()
                )
            )
            if seg.issues:
                lines.append(
                    "issues: " + "; ".join(
                        f"{i.layer} {i.label} ({i.severity:.0%})" for i in seg.issues
                    )
                )
            else:
                lines.append("issues: none flagged")
        if layer:
            lines.append(f"layer: {layer}")
        if self.edit_plan and self.edit_plan.count:
            lines.append(f"staged: {self.edit_plan.count} edit(s)")
        self.query_one("#lt-inspector", Static).update("\n".join(lines))

    # ------------------------------------------------------------------
    # Message handlers from the reused LayerStudio widget
    # ------------------------------------------------------------------
    def on_layer_studio_edit_requested(
        self, message: LayerStudio.EditRequested
    ) -> None:
        """Record the per-cell op into the shared edit plan (workbench parity)."""
        plan = self.edit_plan
        if plan is None:
            plan = EditPlan()
            self.edit_plan = plan
        try:
            plan.add(message.layer or "", message.segment_idx, message.op)
        except ValueError:
            return
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).edit_plan = self.edit_plan
        self._update_status()

    def on_layer_studio_selection_changed(
        self, message: LayerStudio.SelectionChanged
    ) -> None:
        if message.segment is None:
            self.query_one("#lt-inspector", Static).update("No cell selected")
            return
        seg = message.segment
        self._update_inspector(
            message.layer or "", seg.start_s, seg.end_s
        )

    def on_layer_studio_seek_requested(self, message: LayerStudio.SeekRequested) -> None:
        """Ask the main app (which owns audio) to jump to the clicked second."""
        self._pending_seek = float(message.seconds)
        try:
            request_seek(self.sidecar_path, self._pending_seek)
        except Exception as exc:
            logger.debug("seek request failed: %s", exc)
            self.notify(f"Seek request failed: {exc}")
            return
        self.notify(
            f"Seek requested @ {message.seconds:.0f}s — the main app moves playback."
        )

    # ------------------------------------------------------------------
    # Tool palette + commit / close
    # ------------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "lt-btn-commit":
            self._commit_edits()
            return
        if btn_id == "lt-btn-close":
            self.exit()
            return
        if btn_id.startswith("lt-op-"):
            op = btn_id.removeprefix("lt-op-")
            with contextlib.suppress(Exception):
                self.query_one("#lt-studio", LayerStudio)._request_edit(op)

    def _commit_edits(self) -> None:
        """Write the staged plan back to the sidecar for the main app to apply."""
        from harvester.ipc.layer_sidecar import write_sidecar

        if self.track is None or self.edit_plan is None:
            self.query_one("#lt-status", Static).update("Nothing staged to commit")
            return
        try:
            write_sidecar(self.track, self.edit_plan, self.sidecar_path)
            self._last_sidecar_mtime = self._sidecar_mtime()
            self.query_one("#lt-status", Static).update(
                f"✎ {self.edit_plan.count} edit(s) saved to sidecar — "
                "main app applies them on next SAVE LAYERS / export."
            )
            self._update_status()
        except Exception as exc:
            logger.exception("sidecar commit failed: %s", exc)
            self.query_one("#lt-status", Static).update(f"COMMIT FAILED: {exc}")

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------
    def action_quit(self) -> None:
        self.exit()

    def _write_heartbeat(self) -> None:
        """Own the liveness file; the main app only reads it."""
        with contextlib.suppress(Exception):
            write_terminal_heartbeat(self.sidecar_path)

    def on_unmount(self) -> None:
        """Clean exit removes the heartbeat so the main app sees the window closed."""
        clear_terminal_heartbeat(self.sidecar_path)
        if getattr(self, "_heartbeat_timer", None) is not None:
            self._heartbeat_timer.stop()  # type: ignore[attr-defined]
            self._heartbeat_timer = None  # type: ignore[attr-defined]

    def action_cycle_filter(self) -> None:
        """f — cycle the lane provenance filter (docs/14 M5)."""
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).cycle_provenance_filter()

    def action_edit(self, op: str) -> None:
        """Apply a per-cell op to the currently selected cell (palette parity)."""
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio)._request_edit(op)

    def action_edit_reset(self) -> None:
        self.action_edit("reset")

    def action_layer_left(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).action_layer_left()

    def action_layer_right(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).action_layer_right()

    def action_layer_home(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).action_layer_home()

    def action_layer_end(self) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#lt-studio", LayerStudio).action_layer_end()

    def action_play_pause(self) -> None:
        """Toggle the main app's player (this process never owns audio)."""
        target = not self._transport.playing
        self._pending_play = target
        try:
            request_play_state(self.sidecar_path, target)
        except Exception as exc:
            logger.debug("play/pause request failed: %s", exc)
            return
        self._update_status()


# ----------------------------------------------------------------------
# Process launcher (used by workbench)
# ----------------------------------------------------------------------
def _launch_apple_terminal(cmd: list[str]) -> subprocess.Popen | None:
    """Open a new Terminal.app window running `cmd` (macOS)."""
    import shutil

    if shutil.which("osascript") is None:
        return None
    quoted = shlex.join(cmd).replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "Terminal"\n'
        f'  do script "{quoted}"\n'
        '  activate\n'
        'end tell'
    )
    return subprocess.Popen(
        ["osascript", "-e", script],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_layer_terminal(sidecar_path: Path) -> subprocess.Popen | None:
    """Launch the layer terminal in a detached window (fire-and-forget).

    Uses Terminal.app on macOS via osascript; falls back to a detached
    ``sys.executable`` process with a new session everywhere else. Never
    blocks and never raises on launch failure — returns the Popen handle or
    None so callers can warn.
    """
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--sidecar",
        str(sidecar_path),
    ]
    if sys.platform == "darwin":
        try:
            proc = _launch_apple_terminal(cmd)
            if proc is not None:
                return proc
            logger.debug("osascript unavailable — falling back to detached process")
        except Exception as exc:
            logger.warning("Terminal.app launch failed (%s) — detached fallback", exc)
    try:
        return subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.warning("layer terminal launch failed: %s", exc)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="layer_terminal",
        description="OmniRip detached FL Studio-style layer editor.",
    )
    parser.add_argument(
        "--sidecar",
        required=True,
        type=Path,
        help="Path to the JSON sidecar written by the main app.",
    )
    args = parser.parse_args(argv)
    LayerTerminalApp(sidecar_path=args.sidecar).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
