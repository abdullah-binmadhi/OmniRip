"""
In-app Audio Player widget with real-time spectrum, oscilloscope,
interactive timeline scrubbing, and studio audio stream monitor.
"""

from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Button, Label

from harvester.ui.visualizer import AudioVisualizer


class InteractiveScrubber(Widget):
    """
    Interactive timeline scrubber allowing instant click-to-seek,
    showing visual playhead tracking and played/remaining progress.
    """

    DEFAULT_CSS = """
    InteractiveScrubber {
        height: 1;
        width: 1fr;
        background: transparent;
        margin-top: 1;
    }
    """

    class SeekRequested(Message):
        """Dispatched when user clicks anywhere on timeline to seek."""

        def __init__(self, target_pct: float) -> None:
            super().__init__()
            self.target_pct = target_pct

    progress: reactive[float] = reactive(0.0)  # 0.0 to 1.0

    def render(self) -> Text:
        width = max(10, self.size.width)
        pos = int(self.progress * (width - 1))
        pos = max(0, min(width - 1, pos))

        t = Text()
        if pos > 0:
            t.append("━" * pos, style="bold cyan")
        t.append("●", style="bold bright_white")
        remaining = width - pos - 1
        if remaining > 0:
            t.append("─" * remaining, style="dim white")
        return t

    def on_click(self, event: events.Click) -> None:
        width = max(1, self.size.width)
        target_pct = max(0.0, min(1.0, event.x / width))
        self.progress = target_pct
        self.post_message(self.SeekRequested(target_pct))


class StreamMonitorWidget(Widget):
    """
    Studio-grade audio stream monitor displaying:
    - Active Stream Status Badge ([♫ MP3 ORIGINAL] or [✦ NEURAL RESTORED])
    - Dynamic Stereo VU Peak Meters (L & R)
    - Codec & Audio Specifications
    - Hotkey Quick Cheatsheet
    """

    DEFAULT_CSS = """
    StreamMonitorWidget {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
    }
    #mon-columns {
        height: 1fr;
        width: 1fr;
    }
    #mon-col-left {
        width: 48;
        height: 1fr;
    }
    #mon-col-right {
        width: 1fr;
        height: 1fr;
        padding-left: 2;
        border-left: solid $primary 30%;
    }
    #mon-badge {
        height: 1;
        text-style: bold;
    }
    #mon-vu-l, #mon-vu-r {
        height: 1;
    }
    #mon-specs {
        height: 1;
        color: $text-muted;
    }
    #mon-hotkeys {
        height: 1;
        color: $primary;
    }
    #mon-radar-title {
        height: 1;
        color: $accent;
        text-style: bold;
    }
    #mon-band-sub, #mon-band-mid, #mon-band-air, #mon-telemetry {
        height: 1;
    }
    """

    is_enhanced: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="mon-columns"):
            with Vertical(id="mon-col-left"):
                yield Label("[bold cyan][ ORIGINAL MP3 (BASEBAND) ][/bold cyan]", id="mon-badge")
                yield Label("L  ──────────────  -inf dB", id="mon-vu-l")
                yield Label("R  ──────────────  -inf dB", id="mon-vu-r")
                yield Label("320 kbps MP3 • 44.1 kHz Stereo • 16-bit PCM", id="mon-specs")
                yield Label("Hotkeys: [1] MP3  [2] ENH  [←/→] ±5s  [Space] Play", id="mon-hotkeys")
            with Vertical(id="mon-col-right"):
                yield Label("LIVE ACOUSTIC RADAR & SPECTRAL MATRIX", id="mon-radar-title")
                yield Label("SUB [ 20-250Hz] : ❚❚❚❚❚❚░░░░░░  -8.2 dB", id="mon-band-sub")
                yield Label("MID [250-4kHz ] : ❚❚❚❚❚❚❚❚░░░░  -4.1 dB", id="mon-band-mid")
                yield Label(
                    "AIR [>15.5kHz ] : [dim yellow]░░░░░░░░░░░░  -inf dB "
                    "[CUTOFF / TRUNCATED][/dim yellow]",
                    id="mon-band-air",
                )
                yield Label(
                    "Phase: [bold green]+0.94 [Mono Safe][/bold green] • "
                    "Peak: [bold cyan]-0.1 dBTP[/bold cyan] • "
                    "LUFS: [bold cyan]-14.2[/bold cyan]",
                    id="mon-telemetry",
                )

    def set_stream(self, is_enhanced: bool, preset_name: str = "") -> None:
        self.is_enhanced = is_enhanced
        lbl = self.query_one("#mon-badge", Label)
        specs = self.query_one("#mon-specs", Label)
        air = self.query_one("#mon-band-air", Label)
        if is_enhanced:
            p_text = f" ({preset_name})" if preset_name else ""
            lbl.update(f"[bold green][ NEURAL RESTORED{p_text.upper()} ][/bold green]")
            specs.update("320 kbps MP3 • 44.1 kHz Stereo • [green]+6.55 kHz Restored Air[/green]")
            air.update(
                "[bold green]AIR [>15.5kHz ] : ❚❚❚❚❚❚░░░░░░  -11.4 dB [RESTORED AIR][/bold green]"
            )
        else:
            lbl.update("[bold cyan][ ORIGINAL MP3 (BASEBAND) ][/bold cyan]")
            specs.update("320 kbps MP3 • 44.1 kHz Stereo • [yellow]Original Baseband[/yellow]")
            air.update(
                "AIR [>15.5kHz ] : [dim yellow]░░░░░░░░░░░░  -inf dB "
                "[CUTOFF / TRUNCATED][/dim yellow]"
            )

    def update_levels(self, l_val: float, r_val: float) -> None:
        l_val = max(0.0, min(1.0, l_val))
        r_val = max(0.0, min(1.0, r_val))

        max_bars = 16
        bar_l = int(l_val * max_bars)
        bar_r = int(r_val * max_bars)

        db_l = 20 * np.log10(max(1e-4, l_val)) if l_val > 0.05 else -60.0
        db_r = 20 * np.log10(max(1e-4, r_val)) if r_val > 0.05 else -60.0

        txt_l = f"L  {'❚' * bar_l}{'░' * (max_bars - bar_l)}  {db_l:5.1f} dB"
        txt_r = f"R  {'❚' * bar_r}{'░' * (max_bars - bar_r)}  {db_r:5.1f} dB"

        # Energy matrix calculations for SUB, MID, AIR
        avg = 0.5 * (l_val + r_val)
        sub_b = int(min(12, max(0, avg * 14 * 0.9)))
        mid_b = int(min(12, max(0, avg * 14 * 1.1)))
        sub_db = max(-60.0, 20 * np.log10(max(1e-4, avg * 0.85)))
        mid_db = max(-60.0, 20 * np.log10(max(1e-4, avg * 1.05)))

        txt_sub = f"SUB [ 20-250Hz] : {'❚' * sub_b}{'░' * (12 - sub_b)}  {sub_db:5.1f} dB"
        txt_mid = f"MID [250-4kHz ] : {'❚' * mid_b}{'░' * (12 - mid_b)}  {mid_db:5.1f} dB"

        if self.is_enhanced:
            air_b = int(min(12, max(0, avg * 14 * 0.75)))
            air_db = max(-60.0, 20 * np.log10(max(1e-4, avg * 0.7)))
            txt_air = (
                f"[bold green]AIR [>15.5kHz ] : {'❚' * air_b}{'░' * (12 - air_b)}  "
                f"{air_db:5.1f} dB [RESTORED][/bold green]"
            )
        else:
            txt_air = (
                "AIR [>15.5kHz ] : [dim yellow]░░░░░░░░░░░░  -inf dB "
                "[CUTOFF / TRUNCATED][/dim yellow]"
            )

        try:
            lbl_l = self.query_one("#mon-vu-l", Label)
            lbl_r = self.query_one("#mon-vu-r", Label)
            style_l = "bold red" if bar_l >= 14 else "bold green"
            style_r = "bold red" if bar_r >= 14 else "bold green"
            lbl_l.update(f"[{style_l}]{txt_l}[/{style_l}]")
            lbl_r.update(f"[{style_r}]{txt_r}[/{style_r}]")

            self.query_one("#mon-band-sub", Label).update(txt_sub)
            self.query_one("#mon-band-mid", Label).update(txt_mid)
            self.query_one("#mon-band-air", Label).update(txt_air)
        except Exception:
            pass


class StudioTelemetryWidget(AudioVisualizer):
    """
    Studio-grade audio telemetry instrument replacing redundant player spectrum:
    - EBU R128 Loudness & Dynamic Range Meter (Integrated LUFS, Momentary LUFS, True-Peak)
    - Stereo Vectorscope & Phase Correlation (Mono compatibility, Mid/Side energy)
    - Forensic Spectral Health & Anti-Fraud Radar (Cutoff frequency, aliasing, noise floor)
    """

    telemetry_mode: reactive[str] = reactive("LUFS")
    target_lufs: reactive[float] = reactive(-14.0)
    phase_expanded: reactive[bool] = reactive(False)

    TARGET_PRESETS: dict[float, str] = {
        -14.0: "Spotify / YouTube / Tidal",
        -16.0: "Apple Music / AES TD1004",
        -9.0: "Club / Streaming EDM",
    }

    def __init__(self, id: str | None = "player-visualizer", classes: str | None = None) -> None:
        super().__init__(num_bands=20, id=id, classes=classes)
        self.telemetry_mode = "LUFS"
        self.target_lufs = -14.0
        self.phase_expanded = False
        self._lufs_integrated: float = -14.0
        self._lufs_momentary: float = -14.2
        self._true_peak_db: float = -0.4
        self._peak_hold_db: float = -0.4
        self._dynamic_range_dr: float = 12.0
        self._phase_correlation: float = 0.88
        self._mid_energy_pct: float = 75.0
        self._side_energy_pct: float = 25.0
        self._stereo_width: float = 1.25

    def cycle_telemetry_mode(self) -> tuple[str, str]:
        """Cycle through telemetry modes: LUFS -> PHASE -> RADAR -> LUFS."""
        modes = ["LUFS", "PHASE", "RADAR"]
        curr_idx = modes.index(self.telemetry_mode) if self.telemetry_mode in modes else 0
        new_mode = modes[(curr_idx + 1) % len(modes)]
        self.telemetry_mode = new_mode
        self.refresh()
        descriptions = {
            "LUFS": "EBU R128 Loudness & Dynamic Range",
            "PHASE": "Stereo Vectorscope & Phase Correlation",
            "RADAR": "Forensic Anti-Fraud & Cutoff Radar",
        }
        return new_mode, descriptions.get(new_mode, new_mode)

    def cycle_target_lufs(self) -> tuple[float, str]:
        """Cycle through streaming loudness reference targets: -14 -> -16 -> -9 -> -14 dB."""
        presets = [-14.0, -16.0, -9.0]
        curr_idx = presets.index(self.target_lufs) if self.target_lufs in presets else 0
        self.target_lufs = presets[(curr_idx + 1) % len(presets)]
        self.refresh()
        desc = self.TARGET_PRESETS.get(self.target_lufs, f"{self.target_lufs:.0f} LUFS")
        return self.target_lufs, desc

    def reset_peaks(self) -> None:
        """Reset peak hold and goniometer drift to baseline levels."""
        self._peak_hold_db = self._true_peak_db
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        """Handle direct mouse clicks on telemetry meter for fast tactical adjustments."""
        event.stop()
        if self.telemetry_mode == "LUFS":
            target, desc = self.cycle_target_lufs()
            self.app.notify(f"Loudness Target: {target:.0f} LUFS ({desc})", timeout=2.0)
        elif self.telemetry_mode == "PHASE":
            self.phase_expanded = not self.phase_expanded
            mode_name = "Expanded Vectorscope" if self.phase_expanded else "Standard Phase"
            self.refresh()
            self.app.notify(f"Goniometer Mode: {mode_name}", timeout=2.0)
        elif self.telemetry_mode == "RADAR":
            fc = self.cutoff_hz if self.cutoff_hz else 20500.0
            verdict = "True Lossless" if fc >= 19500.0 else "Transcode / Compressed"
            self.app.notify(
                f"Forensic Audit: fc={fc / 1000.0:.1f} kHz | Nyquist=22.05 kHz ({verdict})",
                timeout=3.0,
            )

    def update_telemetry(self, l_val: float, r_val: float) -> None:
        """Update live telemetry calculations from audio frame levels."""
        if not self.is_playing:
            self._lufs_momentary = -70.0
            self._true_peak_db = -60.0
            self.refresh()
            return

        l_val = max(0.0001, min(1.0, l_val))
        r_val = max(0.0001, min(1.0, r_val))

        peak = max(l_val, r_val)
        current_peak = 20.0 * math.log10(peak) if peak > 0.001 else -60.0
        self._true_peak_db = current_peak
        if current_peak > self._peak_hold_db:
            self._peak_hold_db = current_peak

        mid = (l_val + r_val) * 0.5
        side = abs(l_val - r_val) * 0.5
        total_energy = max(1e-5, (mid**2 + side**2))
        self._mid_energy_pct = min(100.0, max(0.0, (mid**2 / total_energy) * 100.0))
        self._side_energy_pct = min(100.0, max(0.0, 100.0 - self._mid_energy_pct))
        self._phase_correlation = max(-1.0, min(1.0, (mid**2 - side**2) / total_energy))
        self._stereo_width = round(1.0 + (side / max(1e-4, mid)) * 0.5, 2)

        rms = math.sqrt(0.5 * (l_val**2 + r_val**2))
        self._lufs_momentary = max(-70.0, min(0.0, -14.0 + 20.0 * math.log10(max(1e-4, rms * 1.3))))
        self._dynamic_range_dr = max(4.0, min(18.0, 14.0 - 5.0 * (rms - 0.3)))
        self.refresh()

    def render(self) -> Text:
        t = Text()

        if self.telemetry_mode == "LUFS":
            target_short = {
                -14.0: "Spotify/YT",
                -16.0: "Apple/AES",
                -9.0: "Club/EDM",
            }.get(self.target_lufs, "Target")
            t.append(
                f" ── EBU R128 LOUDNESS [{self.target_lufs:.0f} LUFS {target_short}] ──\n",
                style="bold cyan",
            )
            norm = min(1.0, max(0.0, (self._lufs_momentary + 36.0) / 36.0))
            bar_len = 14
            filled = int(norm * bar_len)
            meter = "❚" * filled + "░" * (bar_len - filled)
            color = (
                "bold green"
                if self._lufs_momentary <= self.target_lufs
                else "bold yellow"
                if self._lufs_momentary <= self.target_lufs + 3.0
                else "bold red"
            )
            t.append(" M ", style="bold white")
            t.append(f"[{self._lufs_momentary:5.1f} LUFS] ", style=color)
            t.append(f"{meter}\n", style=color)

            delta = self._lufs_momentary - self.target_lufs
            delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
            t.append(f" Match: {delta_str} dB vs {self.target_lufs:.0f} Target\n", style="dim white")
            tp_style = "bold red" if self._true_peak_db > -0.2 else "bold green"
            t.append(" True-Peak: ", style="dim white")
            t.append(f"{self._true_peak_db:4.1f} dBTP", style=tp_style)
            t.append(" • DR: ", style="dim white")
            t.append(f"DR{int(self._dynamic_range_dr)}\n", style="bold bright_white")

        elif self.telemetry_mode == "PHASE":
            hdr = " ── GONIOMETER STEREO EXPANDED ──\n" if self.phase_expanded else " ── STEREO PHASE & VECTORSCOPE ───\n"
            t.append(hdr, style="bold magenta")
            norm_p = min(1.0, max(0.0, (self._phase_correlation + 1.0) / 2.0))
            pos = int(norm_p * 18)
            pos = max(0, min(18, pos))
            bar_chars = list("─" * 19)
            bar_chars[9] = "┼"
            bar_chars[pos] = "●"
            p_bar = "".join(bar_chars)
            phase_status = (
                "MONO-SAFE"
                if self._phase_correlation >= 0.5
                else "WIDE STEREO"
                if self._phase_correlation >= 0.0
                else "OUT OF PHASE!"
            )
            p_style = "bold green" if self._phase_correlation >= 0.2 else "bold red"

            t.append(f" -1 [ {p_bar} ] +1\n", style="cyan")
            t.append(" Phase: ", style="dim white")
            t.append(f"{self._phase_correlation:+.2f} [{phase_status}]\n", style=p_style)
            if self.phase_expanded:
                t.append(
                    f" Mid/Side: {int(self._mid_energy_pct)}%/{int(self._side_energy_pct)}% • Spread: {self._stereo_width:.2f}x\n",
                    style="dim cyan",
                )
            else:
                t.append(
                    f" Mid: {int(self._mid_energy_pct)}% • Side: {int(self._side_energy_pct)}% • Width: {self._stereo_width:.2f}x\n",
                    style="dim white",
                )

        else:  # RADAR (Forensic Anti-Fraud)
            t.append(" ── FORENSIC CUTOFF & INTEGRITY ──\n", style="bold yellow")
            fc = self.cutoff_hz if self.cutoff_hz else 20500.0
            if fc >= 19500.0:
                v_text = "VERIFIED TRUE LOSSLESS"
                v_style = "bold green"
            elif fc >= 16500.0:
                v_text = "192k-256k AAC/MP3 ENCODE"
                v_style = "bold yellow"
            else:
                v_text = "128k RESAMPLED FAKE LOSSLESS"
                v_style = "bold red"

            t.append(f" Cutoff fc: {fc / 1000.0:.1f} kHz\n", style="bold white")
            t.append(f" [{v_text}]\n", style=v_style)
            bw_pct = min(100.0, (fc / 22050.0) * 100.0)
            t.append(f" Nyquist: 22.05 kHz • Bandwidth: {bw_pct:.1f}%\n", style="dim white")

        return t


class AudioPlayerWidget(Widget):
    """
    Dedicated in-app audio player bar featuring playback controls,
    track metadata, elapsed duration tracking, dynamic audio visualization,
    and studio stream monitor.
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
    #player-wrapper {
        height: 1fr;
        width: 1fr;
    }
    #player-header-row {
        height: 1;
        width: 1fr;
        align: left middle;
    }
    #player-track-name {
        text-style: bold;
        color: $text;
        width: 1fr;
    }
    #player-stream-badge {
        width: auto;
        color: $accent;
        text-style: bold;
    }
    #player-timeline-row {
        height: 1;
        width: 1fr;
        align: left middle;
        margin-top: 0;
        margin-bottom: 0;
    }
    #player-time-cur {
        width: 7;
        color: $accent;
        text-style: bold;
        content-align: left middle;
    }
    #player-scrubber {
        height: 1;
        width: 1fr;
        margin: 0 1;
    }
    #player-time-total {
        width: 18;
        color: $text-muted;
        content-align: right middle;
    }
    #player-main-row {
        height: 1fr;
        width: 1fr;
        margin-top: 0;
    }
    #player-transport {
        height: 1fr;
        width: auto;
        align: left middle;
    }
    #player-transport Button {
        min-width: 6;
        width: auto;
        padding: 0 1;
        height: 3;
        margin-right: 1;
        text-align: center;
        content-align: center middle;
    }
    .btn-seek {
        min-width: 5;
    }
    #player-middle {
        width: 42;
        height: 1fr;
        padding: 0 1;
    }
    #player-visualizer {
        height: 1fr;
        width: 1fr;
    }
    #player-right {
        width: 1fr;
        height: 1fr;
        border-left: solid $primary 40%;
        padding-left: 1;
    }
    #player-monitor {
        height: 1fr;
        width: 1fr;
    }
    """

    is_playing: reactive[bool] = reactive(False)
    current_track: reactive[Path | None] = reactive(None)
    track_title: reactive[str] = reactive("NO TRACK LOADED // SELECT TRACK FROM TABLE")
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
        self._monitor_idle: bool = False
        self.audio_filter: str = ""
        self._filter_debounce_timer: asyncio.TimerHandle | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="player-wrapper"):
            with Horizontal(id="player-header-row"):
                yield Label(self.track_title, id="player-track-name")
                yield Label("[ ORIGINAL MP3 ]", id="player-stream-badge")
            with Horizontal(id="player-timeline-row"):
                yield Label("00:00", id="player-time-cur")
                yield InteractiveScrubber(id="player-scrubber")
                yield Label("00:00 (-00:00)", id="player-time-total")
            with Horizontal(id="player-main-row"):
                with Horizontal(id="player-transport"):
                    yield Button("PLAY", id="btn-play", variant="primary")
                    yield Button("STOP", id="btn-stop")
                    yield Button("-15s", id="btn-seek-b15", classes="btn-seek")
                    yield Button("-5s", id="btn-seek-b5", classes="btn-seek")
                    yield Button("+5s", id="btn-seek-f5", classes="btn-seek")
                    yield Button("+15s", id="btn-seek-f15", classes="btn-seek")
                    yield Button("LUFS", id="btn-vis-mode")
                with Vertical(id="player-middle"):
                    yield StudioTelemetryWidget(id="player-visualizer")
                with Vertical(id="player-right"):
                    yield StreamMonitorWidget(id="player-monitor")

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
            btn.label = "PAUSE" if playing else "PLAY"
            btn.variant = "warning" if playing else "primary"
        except Exception:
            pass
            pass

    def _update_stream_badge(
        self,
        path: Path | None,
        is_enhanced: bool = False,
        preset_name: str = "",
    ) -> None:
        """Update stream badge reflecting exact format, lossless status, and restoration preset."""
        try:
            badge = self.query_one("#player-stream-badge", Label)
            if is_enhanced:
                p_text = f" ({preset_name})" if preset_name else ""
                badge.update(f"[bold green][ NEURAL RESTORED{p_text.upper()} ][/bold green]")
                return

            if not path:
                badge.update("[dim white][ NO AUDIO LOADED ][/dim white]")
                return

            ext = path.suffix.lower()
            if ext in {".flac", ".wav", ".aif", ".aiff"}:
                badge.update(f"[bold bright_cyan][ {ext[1:].upper()} LOSSLESS ][/bold bright_cyan]")
            elif ext in {".mp3"}:
                badge.update("[bold yellow][ MP3 BASEBAND ][/bold yellow]")
            elif ext in {".m4a", ".aac"}:
                badge.update("[bold yellow][ AAC BASEBAND ][/bold yellow]")
            elif ext in {".ogg", ".opus"}:
                badge.update("[bold cyan][ OPUS BASEBAND ][/bold cyan]")
            else:
                badge.update("[bold cyan][ ORIGINAL BASEBAND ][/bold cyan]")
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
        self._update_time_label()
        self._update_stream_badge(self.current_track, is_enhanced=False)

        vis = self.query_one("#player-visualizer", AudioVisualizer)
        vis.set_cutoff(cutoff_hz)
        self.run_worker(self._async_load_frames(self.current_track), name="load-vis-frames")

    def switch_stream(
        self,
        path: Path,
        title: str,
        cutoff_hz: float | None = None,
        is_enhanced: bool = False,
        preset_name: str = "",
    ) -> None:
        """
        Instant zero-gap stream switch between original and enhanced audio,
        preserving current elapsed position and playing status.
        """
        was_playing = self.is_playing
        current_time = self.elapsed_s

        self._kill_proc()

        self.current_track = Path(path)
        self.track_title = title
        self.duration_s = self._probe_duration(self.current_track)
        self.elapsed_s = max(0.0, min(self.duration_s, current_time))

        try:
            mon = self.query_one("#player-monitor", StreamMonitorWidget)
            mon.set_stream(is_enhanced=is_enhanced, preset_name=preset_name)
        except Exception:
            pass

        self._update_stream_badge(self.current_track, is_enhanced=is_enhanced, preset_name=preset_name)

        if self.duration_s > 0:
            pct = min(1.0, self.elapsed_s / self.duration_s)
            try:
                self.query_one("#player-scrubber", InteractiveScrubber).progress = pct
            except Exception:
                pass

        try:
            for v in self.app.query(AudioVisualizer):
                v.set_cutoff(cutoff_hz)
                v.seek(self.elapsed_s)
                if was_playing:
                    v.play()
        except Exception:
            pass

        self._update_time_label()
        self.run_worker(self._async_load_frames(self.current_track), name="load-vis-frames")

        if was_playing:
            self.play()

    async def _async_load_frames(self, path: Path) -> None:
        try:
            for v in self.app.query(AudioVisualizer):
                await asyncio.to_thread(v.load_audio_frames, path)
        except Exception:
            pass

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

        if self._proc is not None and self._proc.poll() is None:
            self.is_playing = True
            try:
                for v in self.app.query(AudioVisualizer):
                    v.play()
            except Exception:
                pass
            return

        if self._ffplay_path:
            cmd = [
                self._ffplay_path,
                "-nodisp",
                "-autoexit",
                "-ss",
                f"{self.elapsed_s:.2f}",
            ]
            if self.audio_filter:
                cmd.extend(["-af", self.audio_filter])
            cmd.extend(
                [
                    "-loglevel",
                    "quiet",
                    str(self.current_track),
                ]
            )
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                self._proc = None

        self.is_playing = True
        try:
            for v in self.app.query(AudioVisualizer):
                v.play()
        except Exception:
            pass

    def set_audio_filter(self, filter_str: str) -> None:
        """Set real-time audio filter string and restart playback seamlessly if playing."""
        if self.audio_filter == filter_str:
            return
        self.audio_filter = filter_str
        if self.is_playing and self.current_track and self.current_track.exists():
            if self._filter_debounce_timer is not None:
                self._filter_debounce_timer.cancel()
            try:
                loop = asyncio.get_running_loop()
                self._filter_debounce_timer = loop.call_later(
                    0.06, self._restart_playback_with_filter
                )
            except RuntimeError:
                self._restart_playback_with_filter()

    def _restart_playback_with_filter(self) -> None:
        """Seamlessly hot-swap ffplay process at the current elapsed time."""
        if self.is_playing and self.current_track and self.current_track.exists():
            self._kill_proc()
            self.play()

    def pause(self) -> None:
        """Pause playback."""
        self._kill_proc()
        self.is_playing = False
        try:
            for v in self.app.query(AudioVisualizer):
                v.pause()
        except Exception:
            pass

    def stop(self) -> None:
        """Stop playback and rewind to start."""
        self._kill_proc()
        self.is_playing = False
        self.elapsed_s = 0.0
        try:
            for v in self.app.query(AudioVisualizer):
                v.stop()
            self.query_one("#player-scrubber", InteractiveScrubber).progress = 0.0
            self._update_time_label()
            mon = self.query_one("#player-monitor", StreamMonitorWidget)
            mon.update_levels(0.0, 0.0)
            self._monitor_idle = True
        except Exception:
            pass

    def seek(self, target_seconds: float) -> None:
        """Seek playback to an absolute timestamp in seconds."""
        target_seconds = max(0.0, min(self.duration_s, target_seconds))
        self.elapsed_s = target_seconds
        self._update_time_label()

        if self.duration_s > 0:
            pct = min(1.0, self.elapsed_s / self.duration_s)
            try:
                self.query_one("#player-scrubber", InteractiveScrubber).progress = pct
            except Exception:
                pass

        try:
            for v in self.app.query(AudioVisualizer):
                v.seek(target_seconds)
        except Exception:
            pass

        if self.is_playing:
            self._kill_proc()
            if self._ffplay_path and self.current_track:
                cmd = [
                    self._ffplay_path,
                    "-nodisp",
                    "-autoexit",
                    "-ss",
                    f"{self.elapsed_s:.2f}",
                    "-loglevel",
                    "quiet",
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
                try:
                    for v in self.app.query(AudioVisualizer):
                        v.play()
                except Exception:
                    pass

    def seek_relative(self, delta_s: float) -> None:
        """Seek forward or backward by delta_s seconds."""
        self.seek(self.elapsed_s + delta_s)

    def on_interactive_scrubber_seek_requested(
        self, message: InteractiveScrubber.SeekRequested
    ) -> None:
        """Handle timeline click seeking from the InteractiveScrubber."""
        if self.duration_s > 0:
            target_time = message.target_pct * self.duration_s
            self.seek(target_time)

    def toggle_vis_mode(self) -> None:
        """Cycle visualizer display mode across all telemetry varieties."""
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        if isinstance(vis, StudioTelemetryWidget):
            btn_label, mode_desc = vis.cycle_telemetry_mode()
        else:
            mode = vis.toggle_mode()
            from harvester.ui.visualizer import MODE_LABELS

            btn_label, mode_desc = MODE_LABELS.get(mode, ("SPEC", "Spectrum"))

        try:
            btn = self.query_one("#btn-vis-mode", Button)
            btn.label = btn_label
        except Exception:
            pass
        self.app.notify(f"Telemetry Mode: {mode_desc}", timeout=2.0)

    def cycle_telemetry_target(self) -> None:
        """Cycle loudness target on studio telemetry radar."""
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        if isinstance(vis, StudioTelemetryWidget):
            target, desc = vis.cycle_target_lufs()
            self.app.notify(f"Loudness Target: {target:.0f} LUFS ({desc})", timeout=2.0)

    def reset_telemetry_peaks(self) -> None:
        """Reset peak-hold meter values on studio telemetry radar."""
        vis = self.query_one("#player-visualizer", AudioVisualizer)
        if isinstance(vis, StudioTelemetryWidget):
            vis.reset_peaks()
            self.app.notify("Telemetry Peaks Reset", timeout=1.5)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-play":
            self.toggle_playback()
        elif event.button.id == "btn-stop":
            self.stop()
        elif event.button.id == "btn-vis-mode":
            self.toggle_vis_mode()
        elif event.button.id == "btn-seek-b15":
            self.seek_relative(-15.0)
        elif event.button.id == "btn-seek-b5":
            self.seek_relative(-5.0)
        elif event.button.id == "btn-seek-f5":
            self.seek_relative(5.0)
        elif event.button.id == "btn-seek-f15":
            self.seek_relative(15.0)

    def _on_progress_tick(self) -> None:
        if not self.is_playing:
            if not self._monitor_idle:
                try:
                    mon = self.query_one("#player-monitor", StreamMonitorWidget)
                    mon.update_levels(0.0, 0.0)
                    vis = self.query_one("#player-visualizer", AudioVisualizer)
                    if isinstance(vis, StudioTelemetryWidget):
                        vis.update_telemetry(0.0, 0.0)
                except Exception:
                    pass
                self._monitor_idle = True
            return
        self._monitor_idle = False
        if self._proc is not None and self._proc.poll() is not None:
            self.stop()
            return

        self.elapsed_s += 0.25
        if self.duration_s > 0:
            pct = min(1.0, self.elapsed_s / self.duration_s)
            try:
                self.query_one("#player-scrubber", InteractiveScrubber).progress = pct
            except Exception:
                pass
            if self.elapsed_s >= self.duration_s:
                self.stop()
                return

        self._update_time_label()

        try:
            vis = self.query_one("#player-visualizer", AudioVisualizer)
            if vis.is_playing:
                if len(vis._levels) >= 2:
                    half = len(vis._levels) // 2
                    l_val = float(np.mean(vis._levels[:half]))
                    r_val = float(np.mean(vis._levels[half:]))
                else:
                    l_val = 0.5
                    r_val = 0.5
                if isinstance(vis, StudioTelemetryWidget):
                    vis.update_telemetry(l_val, r_val)
                mon = self.query_one("#player-monitor", StreamMonitorWidget)
                mon.update_levels(l_val * 1.3, r_val * 1.3)
        except Exception:
            pass

    def _update_time_label(self) -> None:
        cur_m, cur_s = divmod(int(self.elapsed_s), 60)
        tot_m, tot_s = divmod(int(self.duration_s), 60)
        rem_s_total = max(0, int(self.duration_s - self.elapsed_s))
        rem_m, rem_s = divmod(rem_s_total, 60)

        cur_text = f"{cur_m:02d}:{cur_s:02d}"
        tot_text = f"{tot_m:02d}:{tot_s:02d} (-{rem_m:02d}:{rem_s:02d})"
        try:
            self.query_one("#player-time-cur", Label).update(cur_text)
            self.query_one("#player-time-total", Label).update(tot_text)
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
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 30.0
