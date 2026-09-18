"""
In-app Audio Player widget with real-time spectrum and oscilloscope visualization.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar

from harvester.ui.visualizer import AudioVisualizer


class AudioPlayerWidget(Widget):
    """
    Dedicated in-app audio player bar featuring playback controls,
    track metadata, elapsed duration tracking, and dynamic audio visualization.
    """

    DEFAULT_CSS = """
    AudioPlayerWidget {
        height: 8;
        min-height: 7;
        margin: 0 1;
        border: round $accent;
        background: $panel;
        padding: 0 1;
    }
    #player-layout {
        height: 1fr;
        width: 1fr;
    }
    #player-left {
        width: 44;
        height: 1fr;
        padding-right: 1;
    }
    #player-right {
        width: 1fr;
        height: 1fr;
    }
    #player-title-row {
        height: 1;
        width: 1fr;
        align: left middle;
    }
    #player-track-name {
        text-style: bold;
        color: $text;
        width: 1fr;
    }
    #player-controls {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-top: 1;
    }
    #player-controls Button {
        min-width: 8;
        height: 3;
        margin-right: 1;
    }
    #player-time {
        color: $text-muted;
        margin-left: 1;
        height: 3;
        content-align: left middle;
    }
    #player-progress {
        height: 1;
        margin-top: 1;
    }
    """

    is_playing: reactive[bool] = reactive(False)
    current_track: reactive[Path | None] = reactive(None)
    track_title: reactive[str] = reactive("No track loaded — select a track or press Space")
    duration_s: reactive[float] = reactive(0.0)
    elapsed_s: reactive[float] = reactive(0.0)

    def __init__(
        self,
        id: str | None = "audio-player",
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._proc: subprocess.Popen[bytes] | None = None
        self._progress_timer: Timer | None = None
        self._ffplay_path = shutil.which("ffplay")

    def compose(self) -> ComposeResult:
        with Horizontal(id="player-layout"):
            with Vertical(id="player-left"):
                with Horizontal(id="player-title-row"):
                    yield Label(self.track_title, id="player-track-name")
                with Horizontal(id="player-controls"):
                    yield Button("▶ Play", id="btn-play", variant="primary")
                    yield Button("⏹ Stop", id="btn-stop")
                    yield Button("📊 Mode", id="btn-vis-mode")
                    yield Label("00:00 / 00:00", id="player-time")
                yield ProgressBar(total=100, show_eta=False, id="player-progress")
            with Vertical(id="player-right"):
                yield AudioVisualizer(num_bands=24, id="player-visualizer")

    def on_mount(self) -> None:
        self._progress_timer = self.set_interval(0.25, self._on_progress_tick)

    def on_unmount(self) -> None:
        self.stop()
        if self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None

    def watch_track_title(self, new_title: str) -> None:
        try:
            self.query_one("#player-track-name", Label).update(new_title)
        except Exception:
            pass

    def watch_is_playing(self, playing: bool) -> None:
        try:
            btn = self.query_one("#btn-play", Button)
            btn.label = "⏸ Pause" if playing else "▶ Play"
            btn.variant = "warning" if playing else "primary"
        except Exception:
            pass

    def load_track(
        self,
        path: Path,
        title: str | None = None,
        cutoff_hz: float | None = None,
    ) -> None:
        """Load an audio file into the player and prepare visualizer frames."""
        self.stop()
        self.current_track = Path(path)
        self.track_title = title or self.current_track.name
        self.elapsed_s = 0.0
        self.duration_s = self._probe_duration(self.current_track)

        vis = self.query_one("#player-visualizer", AudioVisualizer)
        vis.set_cutoff(cutoff_hz)
        # Precompute visualizer frames in background worker
        self.run_worker(self._async_load_frames(self.current_track), name="load-vis-frames")

    async def _async_load_frames(self, path: Path) -> None:
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        await asyncio.to_thread(vis.load_audio_frames, path)

    def toggle_playback(self) -> None:
        """Toggle playback between playing and paused/stopped."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        """Begin audio playback and animate visualizer."""
        if not self.current_track or not self.current_track.exists():
            return

        vis = self.query_one("#player-visualizer", AudioVisualizer)

        if self._proc is not None and self._proc.poll() is None:
            # Already active process
            self.is_playing = True
            vis.play()
            return

        if self._ffplay_path:
            cmd = [
                self._ffplay_path,
                "-nodisp",
                "-autoexit",
                "-ss", f"{self.elapsed_s:.2f}",
                "-loglevel", "quiet",
                str(self.current_track),
            ]
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                self._proc = None

        self.is_playing = True
        vis.play()

    def pause(self) -> None:
        """Pause playback."""
        self._kill_proc()
        self.is_playing = False
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        vis.pause()

    def stop(self) -> None:
        """Stop playback and rewind to start."""
        self._kill_proc()
        self.is_playing = False
        self.elapsed_s = 0.0
        try:
            vis = self.query_one("#player-visualizer", AudioVisualizer)
            vis.stop()
            self.query_one("#player-progress", ProgressBar).progress = 0
            self._update_time_label()
        except Exception:
            pass

    def toggle_vis_mode(self) -> None:
        """Cycle visualizer display mode."""
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        mode = vis.toggle_mode()
        self.app.notify(f"Visualizer: {mode.title()}", timeout=2.0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-play":
            self.toggle_playback()
        elif event.button.id == "btn-stop":
            self.stop()
        elif event.button.id == "btn-vis-mode":
            self.toggle_vis_mode()

    def _on_progress_tick(self) -> None:
        if not self.is_playing:
            return
        if self._proc is not None and self._proc.poll() is not None:
            # Process terminated (finished playing)
            self.stop()
            return

        self.elapsed_s += 0.25
        if self.duration_s > 0:
            pct = min(100.0, (self.elapsed_s / self.duration_s) * 100.0)
            try:
                self.query_one("#player-progress", ProgressBar).progress = pct
            except Exception:
                pass
            if self.elapsed_s >= self.duration_s:
                self.stop()
                return

        self._update_time_label()

    def _update_time_label(self) -> None:
        cur_m, cur_s = divmod(int(self.elapsed_s), 60)
        tot_m, tot_s = divmod(int(self.duration_s), 60)
        label_text = f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}"
        try:
            self.query_one("#player-time", Label).update(label_text)
        except Exception:
            pass

    def _kill_proc(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=0.2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    @staticmethod
    def _probe_duration(file_path: Path) -> float:
        import subprocess

        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 30.0
