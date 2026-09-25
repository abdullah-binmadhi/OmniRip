"""Textual UI: throttled bridge, level-filtered console, and M6 hardening (docs/08)."""

from __future__ import annotations

import asyncio
import logging
import re
import typing
from dataclasses import replace
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from harvester.config import AppConfig, load_config, persist_first_run_acceptance
from harvester.models import Mode, SourceKind, State, TrackJob, Verdict
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.services.environment import (
    DependencyStatus,
    EnvironmentStatus,
    check_slskd,
    detect_environment,
)
from harvester.services.slskd_config import read_slskd_credentials
from harvester.ui.bridge import FlushPlan, UiBridge
from harvester.ui.help_modal import HelpModalScreen
from harvester.ui.logconsole import LogConsole
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.themes import cycle_theme, register_custom_themes
from harvester.ui.workbench import WorkbenchWidget
from harvester.util.errors import ConfigError
from harvester.util.logging_setup import LoggingController, configure_logging

_MAX_VISIBLE_JOBS = 500
_OVERFLOW_KEY = "__overflow__"


class StatusBar(Static):
    """Compact service-status line rendered below Textual's title header."""

    def __init__(self) -> None:
        super().__init__(id="statusbar")
        self._parts: dict[str, str] = {
            "slskd": "▲ checking",
            "ffmpeg": "▲ checking",
            "fpcalc": "▲ checking",
            "acoustid": "▲ checking",
            "jobs": "jobs 0/0",
        }

    def set_environment(self, status: EnvironmentStatus) -> None:
        for name in ("slskd", "ffmpeg", "fpcalc", "acoustid"):
            dependency = status.get(name)
            self._parts[name] = f"{dependency.icon} {name}"
        self.refresh()

    def set_pill(self, name: str, status: DependencyStatus) -> None:
        self._parts[name] = f"{status.icon} {name}"
        self.refresh()

    def set_jobs(self, jobs: list[TrackJob]) -> None:
        completed = sum(job.state in {State.COMPLETED, State.SKIPPED} for job in jobs)
        self._parts["jobs"] = f"jobs {completed}/{len(jobs)}"
        self.refresh()

    def render(self) -> str:
        return "OMNIRIP // WORKSTATION   |   " + "   ".join(self._parts.values())


class JobTable(DataTable[str]):
    """Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)."""

    COLUMNS = ("Track", "Original", "Target", "Phase", "Progress")

    def __init__(self) -> None:
        super().__init__(id="jobs")
        self.cursor_type = "row"
        self._job_order: list[str] = []
        self._row_hashes: dict[str, tuple[str, ...]] = {}
        self._overflow = 0
        self._overflow_row_added = False
        self._show_placeholder = True

    def on_mount(self) -> None:
        self.add_columns(*self.COLUMNS)
        self.add_row(
            "No jobs yet",
            "—",
            "—",
            "Waiting",
            "waiting for input",
            key="m0-placeholder",
        )

    def update_job(self, job: TrackJob) -> None:
        if self._show_placeholder:
            self.remove_row("m0-placeholder")
            self._show_placeholder = False
        labels = self._labels(job)
        if job.id not in self._job_order:
            if len(self._job_order) >= _MAX_VISIBLE_JOBS:
                self._overflow += 1
                self._refresh_overflow()
                return
            self._job_order.append(job.id)
            self._row_hashes[job.id] = labels
            self.add_row(*labels, key=job.id)
            return
        previous = self._row_hashes.get(job.id)
        if previous is None or self._live_row_key(job.id) is None:
            # Textual may have dropped a row during a mode switch or refresh. Rebuild it
            # from the authoritative job table instead of crashing the UI bridge.
            self._job_order = [job_id for job_id in self._job_order if job_id != job.id]
            self._row_hashes.pop(job.id, None)
            self.update_job(job)
            return
        if previous == labels:
            return
        row_key = self._live_row_key(job.id)
        if row_key is None:
            return
        row_index = self.get_row_index(row_key)
        for column_index, (old, new) in enumerate(zip(previous, labels, strict=True)):
            if old != new:
                self.update_cell_at(Coordinate(row_index, column_index), new)
        self._row_hashes[job.id] = labels

    def _live_row_key(self, job_id: str):
        return next(
            (key for key in self.rows if getattr(key, "value", key) == job_id),
            None,
        )

    def _live_column_key(self, label: str):
        return next(
            (key for key in self.columns if getattr(key, "value", key) == label),
            None,
        )

    def _refresh_overflow(self) -> None:
        if not self._overflow or self._show_placeholder:
            return
        if self._overflow_row_added:
            row_key = self._live_row_key(_OVERFLOW_KEY)
            if row_key is not None:
                self.update_cell_at(
                    Coordinate(self.get_row_index(row_key), len(self.COLUMNS) - 1),
                    f"+{self._overflow} more",
                )
        else:
            self.add_row("", "", "", "", f"+{self._overflow} more", key=_OVERFLOW_KEY)
            self._overflow_row_added = True

    def has_job(self, job_id: str) -> bool:
        """Return whether a job already has a visible row (used by tests and callers)."""
        return job_id in self._job_order

    def current_job_id(self) -> str | None:
        if self._show_placeholder or not self._job_order:
            return None
        if self.cursor_row < 0 or self.cursor_row >= len(self._job_order):
            return self._job_order[-1]
        return self._job_order[self.cursor_row]

    @classmethod
    def _labels(cls, job: TrackJob) -> tuple[str, str, str, str, str]:
        return (
            cls._track_label(job),
            cls._original_label(job),
            cls._target_label(job),
            cls._phase_label(job),
            cls._progress_label(job),
        )

    @staticmethod
    def _track_label(job: TrackJob) -> str:
        return f"[DIR] {job.display_name}" if job.mode is Mode.BATCH_AUDIT else job.display_name

    @staticmethod
    def _original_label(job: TrackJob) -> str:
        if job.orig_codec and job.orig_bitrate:
            return f"{job.orig_codec} {job.orig_bitrate}k"
        return "—"

    @staticmethod
    def _target_label(job: TrackJob) -> str:
        return {
            SourceKind.STREAM_OPUS: "Fallback Opus",
            SourceKind.STREAM_OTHER: "Fallback audio",
            SourceKind.P2P_FLAC: "P2P FLAC",
            SourceKind.NONE: "Fallback MP3" if job.fallback_attempted else "—",
        }[job.source_kind]

    @staticmethod
    def _phase_label(job: TrackJob) -> str:
        label = job.state.value.replace("_", " ").title()
        if job.spectral.verdict is Verdict.FRAUD:
            return f"[FRAUD] {label}"
        return label

    @staticmethod
    def _progress_label(job: TrackJob) -> str:
        percent = job.download.percent
        if percent is None:
            percent = job.progress if job.progress else None
        if percent is None:
            if job.state is State.COMPLETED:
                return "[OK]"
            if job.state is State.SKIPPED:
                return "[SKIP]"
            if job.state is State.FAILED:
                return "[FAIL]"
            if job.state is State.CANCELLED:
                return "[CANCEL]"
            return "—"
        filled = max(0, min(10, round(percent / 10)))
        return f"{'█' * filled}{'░' * (10 - filled)} {percent:3.0f}%"


class HelpScreen(ModalScreen[None]):
    """Non-blocking help overlay for the application."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Harvester controls", id="help-title")
            yield Label(
                'Mode A: paste a URL; Enter or GO submits it. Enable "Playlists" to\n'
                "expand a playlist URL into child jobs (capped, confirmed).\n"
                "Mode B: switch to 'Batch directory', enter a music folder path;\n"
                "       lossless and >= 256 kbps files are skipped, the rest are\n"
                "       upgraded in place (originals go to .trash/).\n"
                "ctrl+p toggles Mode A/B; l cycles the log level filter.\n"
                "p purges the last batch's .trash/ older than the retention window.\n"
                "c cancels the selected job; C cancels all active jobs.\n"
                "Ctrl+Q shuts down workers and quits (confirms while jobs are active).",
                id="help-body",
            )
            yield Button("Close", id="close-help", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class BatchConfirmScreen(ModalScreen[None]):
    """Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, scan) -> None:
        super().__init__()
        self.scan = scan

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Confirm batch", id="confirm-title")
            yield Label(
                f"Scan of {self.scan.root}:\n"
                f"  found {self.scan.found}, skip {len(self.scan.skipped)}, "
                f"queue {len(self.scan.queued)} upgrades\n"
                f"  approx {self.scan.needed_bytes / (1024**2):.0f} MiB disk space needed\n\n"
                "Originals are moved to .trash/ and replaced in place.",
                id="confirm-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button("Queue upgrades", id="confirm-start", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-start":
            self.app.run_worker(self._start_batch(), name="submit-batch")
            self.app.pop_screen()
        else:
            self.dismiss()

    async def _start_batch(self) -> None:
        app = typing.cast(HarvesterApp, self.app)
        await app._confirm_batch(self.scan)


class PlaylistConfirmScreen(ModalScreen[None]):
    """Show entry count and cap before expanding a playlist (docs/08 §2, D10)."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, url: str, entry_count: int, cap: int) -> None:
        super().__init__()
        self.url = url
        self.entry_count = entry_count
        self.cap = cap

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Expand playlist?", id="confirm-title")
            yield Label(
                f"{self.entry_count} entries (capped at {self.cap}) will be queued\n"
                "as individual track jobs.",
                id="confirm-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button("Expand", id="confirm-start", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-start":
            self.app.run_worker(self._start(), name="submit-playlist")
            self.app.pop_screen()
        else:
            self.dismiss()

    async def _start(self) -> None:
        app = typing.cast(HarvesterApp, self.app)
        await app._confirm_playlist(self.url)


class QuitConfirmScreen(ModalScreen[None]):
    """Confirm quit while jobs are still active (docs/08 §5, FR-17)."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, active_jobs: int) -> None:
        super().__init__()
        self.active_jobs = active_jobs

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Quit with active jobs?", id="confirm-title")
            yield Label(
                f"{self.active_jobs} job(s) still running — quitting cancels them.",
                id="confirm-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button("Quit", id="confirm-start", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-start":
            app = typing.cast(HarvesterApp, self.app)
            app.run_worker(app._shutdown_and_exit(), name="shutdown", exclusive=True)
            self.app.pop_screen()
        else:
            self.dismiss()


class PurgeConfirmScreen(ModalScreen[None]):
    """Confirm trash purge before deleting rollback sources (docs/08 §5, D5)."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Purge .trash/?", id="confirm-title")
            yield Label(
                "Day-directories older than the retention window will be deleted\n"
                "permanently (rollback sources are lost).",
                id="confirm-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button("Purge", id="confirm-start", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-start":
            app = typing.cast(HarvesterApp, self.app)
            app.run_worker(app._purge_trash_confirmed(), name="purge-trash")
            self.app.pop_screen()
        else:
            self.dismiss()
class FirstRunNoticeScreen(ModalScreen[None]):
    """Legal/ToS notice shown once; acceptance persists to config (docs/01 §8, docs/08 §2)."""

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield Label("Before you begin", id="notice-title")
            yield Label(
                "Harvester is for personal use with content you are legally entitled\n"
                "to obtain (your own works, public-domain/CC material, or purchases\n"
                "and rips where local law permits). Downloading from YouTube generally\n"
                "violates its Terms of Service, and sharing copyrighted material on\n"
                "P2P networks may be illegal in your jurisdiction. You are responsible\n"
                "for compliant use.",
                id="notice-body",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="notice-cancel")
                yield Button("I understand", id="notice-accept", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "notice-accept":
            self.app.run_worker(self._accept(), name="persist-notice")
            self.dismiss()
        else:
            self.dismiss()

    async def _accept(self) -> None:
        app = typing.cast(HarvesterApp, self.app)
        await app._accept_notice()


class FatalSetupScreen(ModalScreen[None]):
    """Shown when a required runtime dependency prevents acquisition."""

    def __init__(self, status: EnvironmentStatus) -> None:
        super().__init__()
        self.status = status

    def compose(self) -> ComposeResult:
        missing = "\n".join(
            f"• {dependency.name}: {dependency.detail}"
            for dependency in self.status.missing_required
        )
        with Container(classes="modal-card"):
            yield Label("Harvester cannot start", classes="error-text")
            yield Label(
                "Required dependencies are missing or failed their version check:\n\n"
                + missing
                + "\n\nInstall the tools, then relaunch harvester.",
                id="fatal-details",
            )
            yield Button("Quit", id="quit-fatal", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.exit()


class HarvesterApp(App[None]):
    """Textual application connected to the asynchronous pipeline via a throttled bridge."""

    TITLE = "OMNIRIP"
    SUB_TITLE = "P2P-First Music Acquisition & Curation"
    CSS_PATH = Path(__file__).with_name("app.tcss")
    # docs/08 §5 binds Ctrl+P to mode toggling; Textual's default command palette
    # uses the same chord, so the palette is disabled here.
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+p", "toggle_mode", "Toggle mode"),
        ("?", "help", "Help"),
        ("c", "cancel_selected", "Cancel"),
        ("C", "cancel_all", "Cancel all"),
        ("l", "cycle_log_level", "Log level"),
        ("p", "purge_trash", "Purge trash"),
        ("w", "open_workbench", "Workbench"),
        ("t", "cycle_theme", "Theme"),
        ("k", "open_soulseek_login", "Soulseek"),
        ("ctrl+s", "open_settings", "Settings"),
        ("f6", "open_settings", "Settings"),
        ("m", "open_model_setup", "Models"),
        ("space", "toggle_playback", "Play/Pause"),
        ("left", "seek_backward", "Seek -5s"),
        ("right", "seek_forward", "Seek +5s"),
        ("bracket_left", "seek_backward_15", "Seek -15s"),
        ("bracket_right", "seek_forward_15", "Seek +15s"),
        ("1", "select_stream_mp3", "Stream MP3"),
        ("2", "select_stream_enh", "Stream ENH"),
        ("i", "open_track_info", "Track info"),
        ("d", "open_diagnostics", "Diagnostics"),
        ("v", "toggle_vis_mode", "Visualizer"),
        ("t", "toggle_vis_mode", "Telemetry Mode"),
        ("T", "cycle_telemetry_target", "LUFS Target"),
        ("p", "reset_telemetry_peaks", "Reset Peaks"),
        ("question_mark", "show_help", "Help"),
        ("f1", "nav_page_tracks", "Tracks"),
        ("f2", "nav_page_vis", "Visualizer"),
        ("f3", "nav_page_deck", "Deck"),
        ("f4", "nav_page_repair", "Repair"),
        ("f5", "nav_page_eq", "EQ"),
    ]

    def __init__(
        self,
        config: AppConfig | None = None,
        *,
        auto_startup: bool = True,
    ) -> None:
        super().__init__()
        self.config = config or load_config()
        self.auto_startup = auto_startup
        self.environment: EnvironmentStatus | None = None
        self.logging_controller: LoggingController | None = None
        self.orchestrator: PipelineOrchestrator | None = None
        self.bridge: UiBridge | None = None
        self._pipeline_halted = False
        self.logger = logging.getLogger("harvester.ui")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield StatusBar()
        with Vertical(id="main"):
            with Container(id="input-area"):
                with Horizontal(id="input-row"):
                    yield Select(
                        [
                            ("Single URL", Mode.SINGLE_URL.value),
                            ("Batch directory", Mode.BATCH_AUDIT.value),
                        ],
                        value=Mode.SINGLE_URL.value,
                        id="mode",
                        allow_blank=False,
                    )
                    yield Select(
                        [
                            ("Best available", "best_available"),
                            ("Highest quality / Soulseek FLAC", "lossless_preferred"),
                            ("Fast fallback", "fast_fallback"),
                            ("MP3 only", "highest_quality_mp3"),
                        ],
                        value=self.config.slskd.acquisition_mode,
                        id="acquisition-policy",
                        allow_blank=False,
                    )
                    yield Select(
                        [
                            ("MP3 128k", "mp3-128"),
                            ("MP3 192k", "mp3-192"),
                            ("MP3 256k", "mp3-256"),
                            ("MP3 320k", "mp3-320"),
                            ("MP3 V0", "mp3-v0"),
                        ],
                        value=self.config.ffmpeg.transcode
                        if self.config.ffmpeg.transcode != "keep-opus"
                        else "mp3-320",
                        id="mp3-quality",
                        allow_blank=False,
                    )
                    yield Input(
                        placeholder="Paste a URL (Mode A)",
                        id="source-input",
                    )
                    yield Checkbox("Playlists", value=False, id="expand-playlists")
                    yield Button("CONVERT", id="submit", variant="primary", disabled=True)
                    yield Button("THEME", id="btn-theme")
                    yield Button("SOULSEEK", id="btn-soulseek")
                    yield Button("SETTINGS", id="btn-settings")
            with Horizontal(id="app-nav-bar"):
                yield Button("≡ TRACKS & LOGS", id="btn-nav-tracks", classes="app-nav-btn app-nav-active")
                yield Button("◈ VISUALIZER", id="btn-nav-vis", classes="app-nav-btn")
                yield Button("⎈ DECK", id="btn-nav-deck", classes="app-nav-btn")
                yield Button("♻ REPAIR", id="btn-nav-repair", classes="app-nav-btn")
                yield Button("🎚 EQ", id="btn-nav-eq", classes="app-nav-btn")
            with Container(id="workspace-pages"):
                with Vertical(id="tracks-pane", classes="app-full-page"):
                    yield JobTable()
                    yield LogConsole(max_lines=self.config.ui.max_log_lines)
                with Vertical(id="workbench-pane", classes="app-full-page"):
                    yield WorkbenchWidget(
                        on_exported=lambda path: self.notify(
                            f"Exported: {path.name}", severity="information"
                        ),
                        id="workbench-widget",
                    )
            yield AudioPlayerWidget(id="audio-player")

    def on_mount(self) -> None:
        register_custom_themes(self)
        try:
            self.theme = "cyberpunk-neon"
        except Exception:
            pass
        self._refresh_soulseek_button_label()
        if self.auto_startup:
            self._run_guarded(self._startup(), name="startup", exclusive=True)

    async def _startup(self) -> None:
        try:
            await asyncio.to_thread(self.config.paths.ensure)
            self.logging_controller = await asyncio.to_thread(
                configure_logging,
                self.config.paths,
                file_level=self.config.general.log_level_file,
                ui_level=self.config.general.log_level_ui,
            )
            self.environment = await detect_environment(self.config)
            self.query_one(StatusBar).set_environment(self.environment)
            self._write_log("INFO", "environment checks complete")
            for line in self.environment.display_lines():
                self._write_log("INFO", line)
            if not self.environment.ready:
                self.push_screen(FatalSetupScreen(self.environment))
                return
            self.orchestrator = PipelineOrchestrator(self.config)
            await self.orchestrator.start()
            self.bridge = UiBridge(
                self.orchestrator.events,
                interval_s=1.0 / self.config.ui.refresh_hz,
                apply=self._apply_flush,
                jobs_by_id=self.orchestrator.jobs,
            )
            self._run_guarded(self.bridge.run(), name="ui-bridge")
            self.set_interval(self.config.ui.status_interval_s, self._status_tick)
            self.query_one("#submit", Button).disabled = False
            self._write_log("INFO", "pipeline ready")
            if not self.config.general.first_run_notice_accepted:
                self.push_screen(FirstRunNoticeScreen(), self._on_first_run_notice_dismiss)
            else:
                self._check_first_run_models()
        except ConfigError as exc:
            self._write_log("ERROR", f"configuration error: {exc}")
        except Exception as exc:  # startup must leave a visible diagnostic, not a blank TUI
            self.logger.exception("startup checks failed")
            self._write_log("ERROR", f"startup checks failed: {exc}")

    def _apply_flush(self, plan: FlushPlan) -> None:
        orchestrator = self.orchestrator
        if orchestrator is None:
            return
        table = self.query_one(JobTable)
        status = self.query_one(StatusBar)
        console = self.query_one(LogConsole)
        for job_id in plan.job_ids:
            job = orchestrator.jobs.get(job_id)
            if job is not None:
                table.update_job(job)
                if job.state is State.COMPLETED:
                    player = self.query_one(AudioPlayerWidget)
                    if player.current_track is None:
                        wb = self.query_one("#workbench-widget", WorkbenchWidget)
                        wb.load_job(job)
        status.set_jobs(list(orchestrator.jobs.values()))
        for level, text in plan.log_lines:
            console.write_line(level, text)
        for hint in plan.hint_lines:
            console.write_line("INFO", f"hint: {hint}")

    async def _status_tick(self) -> None:
        if self.orchestrator is None:
            return
        self._refresh_soulseek_button_label()
        status = await check_slskd(self.config)
        self.query_one(StatusBar).set_pill("slskd", status)

    def _run_guarded(self, coro, *, name: str, exclusive: bool = False):
        async def wrapped() -> None:
            try:
                await coro
            except Exception as exc:  # WorkerFailed banner path (docs/08 §7)
                self.logger.exception("worker %s crashed", name)
                self._write_log("ERROR", f"worker {name} crashed: {exc}")
                self._pipeline_halted = True
                self.notify("pipeline halted — see logs", severity="error", timeout=0)

        return self.run_worker(wrapped(), name=name, exclusive=exclusive)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._run_guarded(self._submit_current(), name="submit")
        elif event.button.id == "btn-theme":
            self.action_cycle_theme()
        elif event.button.id == "btn-soulseek":
            self.action_open_soulseek_login()
        elif event.button.id == "btn-settings":
            self.action_open_settings()
        elif event.button.id == "btn-nav-tracks":
            self.switch_workspace_page("tracks")
        elif event.button.id == "btn-nav-vis":
            self.switch_workspace_page("vis")
        elif event.button.id == "btn-nav-deck":
            self.switch_workspace_page("deck")
        elif event.button.id == "btn-nav-eq":
            self.switch_workspace_page("eq")
        elif event.button.id == "btn-nav-repair":
            self.switch_workspace_page("repair")

    def switch_workspace_page(self, target: str) -> None:
        """Switch full-screen page between tracks-pane and workbench subpages."""
        try:
            tracks_pane = self.query_one("#tracks-pane", Vertical)
            wb_pane = self.query_one("#workbench-pane", Vertical)
            wb = self.query_one(WorkbenchWidget)

            nav_buttons = {
                "tracks": "#btn-nav-tracks",
                "vis": "#btn-nav-vis",
                "deck": "#btn-nav-deck",
                "eq": "#btn-nav-eq",
                "repair": "#btn-nav-repair",
            }
            for key, btn_id in nav_buttons.items():
                try:
                    btn = self.query_one(btn_id, Button)
                    if key == target:
                        btn.add_class("app-nav-active")
                    else:
                        btn.remove_class("app-nav-active")
                except Exception:
                    pass

            if target == "tracks":
                tracks_pane.styles.display = "block"
                wb_pane.styles.display = "none"
            else:
                tracks_pane.styles.display = "none"
                wb_pane.styles.display = "block"
                wb.switch_page(target)
        except Exception:
            pass

    def action_nav_page_tracks(self) -> None:
        self.switch_workspace_page("tracks")

    def action_nav_page_vis(self) -> None:
        self.switch_workspace_page("vis")

    def action_nav_page_deck(self) -> None:
        self.switch_workspace_page("deck")

    def action_nav_page_eq(self) -> None:
        self.switch_workspace_page("eq")

    def action_nav_page_repair(self) -> None:
        self.switch_workspace_page("repair")


    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "source-input":
            self._run_guarded(self._submit_current(), name="submit")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in {"acquisition-policy", "mp3-quality"}:
            self._apply_acquisition_controls()
            return
        if event.select.id != "mode":
            return
        is_single = event.value == Mode.SINGLE_URL.value
        input_widget = self.query_one("#source-input", Input)
        input_widget.placeholder = (
            "Paste a URL (Mode A)" if is_single else "Path to a music directory (Mode B)"
        )
        self.query_one("#submit", Button).disabled = self.orchestrator is None

    def _apply_acquisition_controls(self) -> None:
        policy = self.query_one("#acquisition-policy", Select).value
        bitrate = self.query_one("#mp3-quality", Select).value
        if not isinstance(policy, str) or not isinstance(bitrate, str):
            return
        self.config = replace(
            self.config,
            slskd=replace(self.config.slskd, acquisition_mode=policy),
            ffmpeg=replace(self.config.ffmpeg, transcode=bitrate),
        )
        if self.orchestrator is not None:
            self.orchestrator.config = self.config
            for service_name in ("slskd", "ytdlp", "ffmpeg"):
                service = getattr(self.orchestrator, service_name, None)
                if service is not None and hasattr(service, "config"):
                    service.config = self.config
        self._write_log("INFO", f"acquisition policy={policy}; output={bitrate}")

    async def _submit_current(self) -> None:
        self._apply_acquisition_controls()
        mode = self.query_one("#mode", Select).value
        if self.orchestrator is None:
            self._write_log("ERROR", "pipeline is not ready; check required dependencies")
            self.notify("Pipeline is not ready", severity="error")
            return
        input_widget = self.query_one("#source-input", Input)
        value = input_widget.value.strip()
        if not value:
            self.notify("Enter a URL or directory path first", severity="error")
            return
        try:
            if mode == Mode.BATCH_AUDIT.value:
                await self._submit_batch(value)
            else:
                await self._submit_url(value)
                input_widget.value = ""
        except Exception as exc:
            self._write_log("ERROR", f"could not submit: {exc}")
            self.notify(str(exc), severity="error")

    async def _submit_url(self, url: str) -> None:
        orchestrator = self.orchestrator
        assert orchestrator is not None

        items = [u.strip() for u in re.split(r"[\r\n,;]+", url) if u.strip()]
        if len(items) > 1:
            queued_count = 0
            for item in items:
                try:
                    await orchestrator.submit_url(item)
                    queued_count += 1
                except Exception as exc:
                    self._write_log("WARNING", f"Could not enqueue {item}: {exc}")
            self.notify(f"Enqueued {queued_count} batch download jobs", timeout=3.0)
            return

        expand = self.query_one("#expand-playlists", Checkbox).value
        if expand and "list=" in url:
            entries = await orchestrator.probe_playlist(url)
            if len(entries) > 1:
                self.push_screen(
                    PlaylistConfirmScreen(url, len(entries), self.config.batch.playlist_cap)
                )
                return
        await orchestrator.submit_url(url)

    async def _confirm_playlist(self, url: str) -> None:
        if self.orchestrator is None:
            return
        jobs = await self.orchestrator.submit_playlist(url, confirmed=True)
        self._write_log("INFO", f"playlist expanded into {len(jobs)} job(s)")
        self.query_one("#source-input", Input).value = ""

    async def _submit_batch(self, path: str) -> None:
        """Scan a directory; queue immediately unless confirmation is required."""

        orchestrator = self.orchestrator
        assert orchestrator is not None
        scan = await orchestrator.scan_batch(path)
        if scan.queued and len(scan.queued) > 25:
            self.push_screen(BatchConfirmScreen(scan))
            return
        await orchestrator.submit_batch(scan=scan, confirmed=True)
        self.query_one("#source-input", Input).value = ""

    async def _confirm_batch(self, scan) -> None:
        """Callback from the confirmation modal: queue the confirmed scan."""

        if self.orchestrator is None:
            return
        await self.orchestrator.submit_batch(scan=scan, confirmed=True)
        self.query_one("#source-input", Input).value = ""

    async def _accept_notice(self) -> None:
        await asyncio.to_thread(persist_first_run_acceptance, self.config)
        self._write_log("INFO", "first-run notice accepted")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_mode(self) -> None:
        select = self.query_one("#mode", Select)
        select.value = (
            Mode.BATCH_AUDIT.value
            if select.value == Mode.SINGLE_URL.value
            else Mode.SINGLE_URL.value
        )
        self.query_one("#source-input", Input).placeholder = (
            "Path to a music directory (Mode B)"
            if select.value == Mode.BATCH_AUDIT.value
            else "Paste a URL (Mode A)"
        )

    def action_cycle_log_level(self) -> None:
        console = self.query_one(LogConsole)
        mode = console.cycle_level()
        self.notify(f"log level: {mode}")

    def action_cancel_selected(self) -> None:
        if self.orchestrator is None:
            return
        job_id = self.query_one(JobTable).current_job_id()
        if job_id:
            self.run_worker(self.orchestrator.cancel(job_id), name="cancel-job")

    def action_cancel_all(self) -> None:
        if self.orchestrator is not None:
            self.run_worker(self.orchestrator.cancel_all(), name="cancel-all")

    def action_open_workbench(self) -> None:
        """Open the detailed Curation Workbench modal for the selected job's audio file."""
        from harvester.ui.screens.curation_workbench import CurationWorkbenchModal

        if self.orchestrator is None:
            self.notify("Orchestrator not initialized", severity="warning")
            return
        job_id = self.query_one(JobTable).current_job_id()
        if not job_id:
            self.notify("No job selected in table", severity="warning")
            return
        job = self.orchestrator.jobs.get(job_id)
        if not job:
            self.notify(f"Job '{job_id}' not found", severity="warning")
            return
        target_path = job.output_path or job.input_path
        if not target_path or not target_path.exists():
            self.notify("No audio file on disk for selected job", severity="warning")
            return

        cutoff = job.spectral.cutoff_hz if (job.spectral and job.spectral.cutoff_hz) else 15500.0
        self.push_screen(
            CurationWorkbenchModal(
                audio_file=target_path,
                detected_cutoff_hz=cutoff,
                on_exported=lambda path: self.notify(
                    f"Exported: {path.name}", severity="information"
                ),
            )
        )

    def action_cycle_theme(self) -> None:
        """Cycle to next dynamic color theme."""
        theme_name = cycle_theme(self)
        self.notify(f"Theme: {theme_name}", timeout=2.0)

    def action_open_soulseek_login(self) -> None:
        """Open the Soulseek credentials and configuration dialog."""
        from harvester.ui.screens.soulseek_login import SoulseekLoginModal

        self.push_screen(SoulseekLoginModal(), self._on_soulseek_modal_dismiss)

    def _on_soulseek_modal_dismiss(self, connected: bool | None) -> None:
        self._refresh_soulseek_button_label()
        if connected:
            self._run_guarded(self._refresh_soulseek_status(), name="slskd-refresh")

    def _refresh_soulseek_button_label(self) -> None:
        try:
            creds = read_slskd_credentials()
            btn = self.query_one("#btn-soulseek", Button)
            if creds.get("username"):
                btn.label = f"@{creds['username']}"
            else:
                btn.label = "SOULSEEK"
        except Exception:
            pass

    async def _refresh_soulseek_status(self) -> None:
        status = await check_slskd(self.config)
        self.query_one(StatusBar).set_pill("slskd", status)
        if status.available:
            self.notify("Soulseek daemon connected and verified", severity="information")

    def action_open_settings(self) -> None:
        """Open the in-TUI settings and API keys dialog."""
        from harvester.ui.settings_modal import SettingsModal

        self.push_screen(SettingsModal(self.config), self._on_settings_modal_dismiss)

    def _on_settings_modal_dismiss(self, saved: bool | None) -> None:
        if saved:
            self.notify("Settings and credentials saved", severity="information")
            self._run_guarded(self._refresh_soulseek_status(), name="slskd-refresh")

    def action_open_model_setup(self) -> None:
        """Open the AI models setup and download dialog."""
        from harvester.ui.setup_modal import ModelSetupModal

        self.push_screen(ModelSetupModal())

    def _on_first_run_notice_dismiss(self, _: object = None) -> None:
        self._check_first_run_models()

    def _check_first_run_models(self) -> None:
        """Check if essential AI models are missing and prompt user if needed."""
        try:
            from harvester.services.model_manager import ModelManager
            from harvester.ui.setup_modal import DEFAULT_SETUP_MODELS, ModelSetupModal

            mm = ModelManager()
            if any(not mm.is_cached(m) for m in DEFAULT_SETUP_MODELS):
                self.push_screen(ModelSetupModal(mm))
        except Exception as exc:
            self.logger.debug("First-run model check skipped: %s", exc)

    def action_toggle_playback(self) -> None:
        """Play or pause the current track in the audio player."""
        player = self.query_one(AudioPlayerWidget)
        if player.current_track is None:
            self._load_selected_into_workbench_and_player()
        player.toggle_playback()

    def action_toggle_vis_mode(self) -> None:
        """Toggle visualizer mode and switch to dedicated visualizer page."""
        self.switch_workspace_page("vis")
        try:
            player = self.query_one(AudioPlayerWidget)
            player.toggle_vis_mode()
        except Exception:
            pass

    def action_cycle_telemetry_target(self) -> None:
        """Cycle loudness target reference on studio telemetry radar."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.cycle_telemetry_target()
        except Exception:
            pass

    def action_reset_telemetry_peaks(self) -> None:
        """Reset peak-hold meter values on studio telemetry radar."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.reset_telemetry_peaks()
        except Exception:
            pass

    def action_show_help(self) -> None:
        """Open the fast keyboard cheatsheet & telemetry command overlay."""
        self.push_screen(HelpModalScreen())

    def action_seek_backward(self) -> None:
        """Seek backward 5 seconds in player."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.seek_relative(-5.0)
        except Exception:
            pass

    def action_seek_forward(self) -> None:
        """Seek forward 5 seconds in player."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.seek_relative(5.0)
        except Exception:
            pass

    def action_seek_backward_15(self) -> None:
        """Seek backward 15 seconds in player."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.seek_relative(-15.0)
        except Exception:
            pass

    def action_seek_forward_15(self) -> None:
        """Seek forward 15 seconds in player."""
        try:
            player = self.query_one(AudioPlayerWidget)
            player.seek_relative(15.0)
        except Exception:
            pass

    def action_select_stream_mp3(self) -> None:
        """Switch audition stream to [1] MP3 (Original)."""
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
            wb.set_active_stream("MP3")
        except Exception:
            pass

    def action_select_stream_enh(self) -> None:
        """Switch audition stream to [2] ENH (Restored)."""
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
            wb.set_active_stream("ENH")
        except Exception:
            pass

    def action_open_track_info(self) -> None:
        """Open the Track Info / upkeep modal."""
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
            wb.open_track_info()
        except Exception:
            pass

    def action_open_diagnostics(self) -> None:
        """Open the diagnostics modal."""
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
            wb.open_diagnostics()
        except Exception:
            pass

    def _load_job_into_workbench(self, job: TrackJob) -> None:
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
            wb.load_job(job)
        except Exception:
            pass

    def _load_selected_into_workbench_and_player(self) -> None:
        if self.orchestrator is None:
            return
        job_id = self.query_one(JobTable).current_job_id()
        if not job_id:
            return
        job = self.orchestrator.jobs.get(job_id)
        if not job:
            return
        try:
            wb = self.query_one("#workbench-widget", WorkbenchWidget)
        except Exception:
            return
        wb.load_job(job)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """When user selects a job in the table, load its audio into workbench and player."""
        self._load_selected_into_workbench_and_player()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """When user navigates or clicks a job row, immediately load it into workbench."""
        self._load_selected_into_workbench_and_player()

    def action_purge_trash(self) -> None:
        if self.orchestrator is not None and self.orchestrator.last_batch_root is not None:
            self.push_screen(PurgeConfirmScreen())

    async def _purge_trash_confirmed(self) -> None:
        if self.orchestrator is None:
            return
        removed = await self.orchestrator.purge_batch_trash()
        self._write_log("INFO", f"purged {removed} expired .trash/ day-director(ies)")
        self.notify(f"Purged {removed} trash day-director(ies)")

    async def action_quit(self) -> None:
        if self.orchestrator is not None and any(
            not job.state.terminal for job in self.orchestrator.jobs.values()
        ):
            active = sum(not job.state.terminal for job in self.orchestrator.jobs.values())
            self.push_screen(QuitConfirmScreen(active))
            return
        self._run_guarded(self._shutdown_and_exit(), name="shutdown", exclusive=True)

    async def _shutdown_and_exit(self) -> None:
        if self.bridge is not None:
            self.bridge.stop()
            self.bridge = None
        if self.orchestrator is not None:
            await self.orchestrator.shutdown()
            self.orchestrator = None
        self.exit()

    def _write_log(self, level: str, message: str) -> None:
        try:
            self.query_one(LogConsole).write_line(level, message)
        except Exception:
            # This only occurs during teardown or before widgets mount.
            pass

    def on_unmount(self) -> None:
        if self.logging_controller is not None:
            self.logging_controller.close()
            self.logging_controller = None


__all__ = [
    "BatchConfirmScreen",
    "FatalSetupScreen",
    "FirstRunNoticeScreen",
    "HarvesterApp",
    "HelpScreen",
    "JobTable",
    "PlaylistConfirmScreen",
    "PurgeConfirmScreen",
    "QuitConfirmScreen",
    "StatusBar",
]
