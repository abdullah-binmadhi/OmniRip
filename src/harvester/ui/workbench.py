"""
Integrated In-Page Curation & Audio Enhancement Workbench for OmniRip.

Provides in-layout stream auditioning ([1] MP3 vs [2] ENH), cutoff frequency analysis,
dynamic mastering deck, preset selection, and full-track derivative export.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal

import platformdirs
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.visual import VisualType
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar, Select

from harvester.analysis.enhancement.acoustic_detector import (
    AcousticAnalysisResult,
    analyze_track_acoustics,
)
from harvester.analysis.enhancement.eq import (
    DEFAULT_EQ_PRESET,
    EQ_FREQUENCIES,
    EQ_PRESET_BANKS,
    EQ_TARGETS,
    MasteringEQSettings,
    apply_mastering_eq,
    eq_bank,
    is_flat,
)
from harvester.analysis.enhancement.genres import (
    DEFAULT_GENRE_INTENSITY,
    GENRE_INTENSITIES,
    GENRE_PROFILES,
    GenreChoice,
    choices_from_tags,
    compose_master_settings,
    effective_preset,
    recipe_line,
    resolve_genre_names,
)
from harvester.analysis.enhancement.presets import PRESETS
from harvester.models import TrackJob
from harvester.processing import (
    DEFAULT_SEP_TYPE,
)
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.services.enhancement.preview import PreviewManager
from harvester.ui.genre_mix import GenreMixScreen
from harvester.ui.operation_state import (
    Operation,
    OperationBusyError,
    OperationToken,
    WorkbenchOperationState,
)
from harvester.ui.repair import RepairPanel
from harvester.ui.track_info import TrackInfoScreen
from harvester.ui.visualizer import AudioVisualizer

if TYPE_CHECKING:
    from harvester.ui.player import AudioPlayerWidget

logger = logging.getLogger(__name__)

StreamId = Literal["MP3", "ENH", "A", "B", "C", "VOC", "INST"]

ECO_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("Conservative DSP", "conservative"),
    ("Fast Neural (Balanced)", "fast_balanced"),
]

AI_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("Milder Highs (De-Sizzle)", "de_sizzle"),
    ("Extended Air (Hybrid)", "extended_air"),
    ("Narrow Residual (Headphone Safe)", "narrow_stereo"),
]


class StockTickerTape(Label):
    """Marquee stock ribbon ticker tape displaying real-time audio and model status."""

    DEFAULT_CSS = """
    StockTickerTape {
        height: 1;
        width: 1fr;
        color: $warning;
        background: #11111b;
        text-style: bold;
        padding: 0 1;
        overflow-x: hidden;
        overflow-y: hidden;
        text-wrap: nowrap;
        text-overflow: clip;
    }
    """

    def __init__(self, initial_text: str = "", **kwargs: Any) -> None:
        super().__init__(initial_text, **kwargs)
        self._raw_message: str = initial_text
        self._ticker_pos: int = 0
        self._default_feed: str = (
            "OmniRip Studio Engine  ·  "
            "▲ BSR: 85% (>300Hz Vocals)  ·  "
            "▼ HDEMUCS: 15% (<300Hz Bass)  ·  "
            "★ Limiter: -0.1 dBFS  ·  "
            "✔ Models: Active  ·  "
            "✦ Master 24-bit/320k"
        )

    def set_feed(self, feed: str) -> None:
        self._default_feed = feed

    def update(self, content: VisualType = "", *, layout: bool = True) -> None:
        msg = str(content) if content else ""
        self._raw_message = msg
        self._ticker_pos = 0
        self._render_marquee()

    def on_mount(self) -> None:
        self.set_interval(0.20, self._step_ticker)

    def _step_ticker(self) -> None:
        self._ticker_pos += 1
        self._render_marquee()

    def _render_marquee(self) -> None:
        feed = self._raw_message.strip() if self._raw_message.strip() else self._default_feed
        unit = f"  ▲▼  {feed}    ▪▪▪    "
        # Repeat the unit to fill at least 3× the widget width so there is
        # never dead space even when the message is very short.
        target_len = max(len(unit), self.size.width * 3 if self.size.width else len(unit) * 3)
        ribbon = (unit * (target_len // len(unit) + 1))[:target_len]
        pos = self._ticker_pos % len(ribbon)
        super().update(ribbon[pos:] + ribbon[:pos])


class WorkbenchWidget(Widget):
    """
    In-page audio enhancement and auditioning workbench panel.
    Supports real-time A/B comparative testing:
      [1] ♫ MP3 : Transcoded output (original audio)
      [2] ✦ ENH : Restored derivative with neural/DSP synthesized high band
    """

    DEFAULT_CSS = """
    WorkbenchWidget {
        width: 1fr;
        height: 1fr;
        border: round $primary;
        background: $panel;
        padding: 0 1;
    }
    #wb-header {
        height: 1;
        width: 1fr;
        background: $surface;
        color: $accent;
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }
    #wb-track-meta {
        height: 1;
        color: $text;
        text-style: bold;
    }
    #wb-cutoff-info {
        height: 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    #wb-stream-row {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-bottom: 1;
    }
    #wb-stream-row Button {
        width: 1fr;
        min-width: 12;
        padding: 0 1;
        margin-right: 1;
        text-align: center;
        content-align: center middle;
    }
    #wb-controls-row {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-bottom: 1;
    }
    #wb-preset-select {
        width: 1fr;
        min-width: 22;
        margin-right: 1;
    }
    #wb-export-split {
        width: auto;
        min-width: 26;
        height: 3;
        align: left middle;
    }
    #wb-btn-export {
        width: auto;
        min-width: 18;
        height: 3;
        padding: 0 2;
        border-right: none;
        text-align: center;
        content-align: center middle;
    }
    #wb-btn-export-menu {
        width: 5;
        min-width: 5;
        height: 3;
        padding: 0 1;
        border-left: tall $success-darken-2;
        text-align: center;
        content-align: center middle;
    }
    #wb-export-dropdown {
        display: none;
        height: auto;
        min-height: 5;
        width: 1fr;
        align: left middle;
        background: $surface-darken-1;
        border: round $success;
        padding: 0 1;
        margin-bottom: 1;
    }
    #wb-export-dropdown-title {
        width: auto;
        color: $success;
        text-style: bold;
        margin-right: 2;
    }
    #wb-export-dropdown .wb-export-choice {
        width: auto;
        height: 3;
        margin-right: 1;
        padding: 0 2;
        background: $surface;
        border: solid $success-darken-2;
        text-align: center;
        content-align: center middle;
    }
    #wb-export-dropdown .wb-export-choice:hover {
        background: $success 30%;
        color: $success;
    }
    .wb-defect-checkbox:focus-within {
        background: transparent;
        color: $text;
    }
    .wb-defect-checkbox:focus-within > .toggle--label {
        color: $text;
    }
    #wb-visualizer {
        height: 8;
        min-height: 6;
        width: 1fr;
    }
    #wb-inspector-container {
        height: 1fr;
        min-height: 14;
        border: round $secondary;
        background: $surface;
        padding: 0;
        overflow-y: auto;
    }
    #wb-page-deck {
        height: auto;
        min-height: 1fr;
        border-top: heavy $primary;
        background: $panel;
        padding: 0 1;
    }
    #wb-page-eq {
        height: auto;
        min-height: 1fr;
        border-top: heavy $primary;
        background: $panel;
        padding: 0 1;
        display: none;
    }
    #wb-eq-toolbar {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-bottom: 1;
        padding: 0 1;
    }
    #wb-eq-title {
        width: 1fr;
        color: $accent;
        text-style: bold;
        height: 1;
    }
    #wb-eq-preset-select {
        width: 22;
        height: 3;
    }
    #wb-eq-target-select {
        width: 16;
        height: 3;
    }
    .wb-eq-toolbar-label {
        height: 3;
        padding: 1 1 0 1;
        color: $text-muted;
    }
    #wb-genre-select {
        width: 24;
        height: 3;
    }
    #wb-genre-intensity {
        width: 13;
        height: 3;
    }
    #wb-genre-recipe {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #wb-eq-sliders-row {
        height: auto;
        width: 1fr;
        align: center top;
        margin-top: 0;
        margin-bottom: 1;
        padding: 0 1;
    }
    .wb-eq-col {
        width: 1fr;
        min-width: 6;
        height: auto;
        align: center top;
        padding: 0;
    }
    /* Borderless chips: a 1-row button cannot carry a border without eating its label. */
    #wb-page-eq .wb-eq-btn-up, #wb-page-eq .wb-eq-btn-dn {
        height: 1;
        min-width: 4;
        width: 5;
        padding: 0;
        margin: 0;
        border: none;
        background: $secondary;
        color: #000000;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    #wb-page-eq .wb-eq-btn-up:hover, #wb-page-eq .wb-eq-btn-dn:hover {
        background: $accent;
        color: #000000;
    }
    .wb-eq-track {
        height: 13;
        width: 5;
        text-align: center;
        padding: 0;
        margin: 0;
    }
    .wb-eq-val {
        height: 1;
        text-align: center;
        text-style: bold;
    }
    .wb-eq-label {
        height: 1;
        text-align: center;
        text-style: bold;
        color: $warning;
    }
    #wb-eq-controls-row {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-top: 1;
        margin-bottom: 1;
        padding: 0 1;
    }
    #wb-eq-controls-row Button {
        height: 3;
        min-width: 11;
        margin-right: 1;
        padding: 0 1;
        text-align: center;
        content-align: center middle;
    }
    #wb-inspector-body {
        height: auto;
        min-height: 1fr;
        border-top: heavy $primary;
        background: $panel;
        padding: 0 1;
    }
    #wb-inspector-title {
        color: $accent;
        text-style: bold;
        height: 1;
    }
    #wb-gauge-orig, #wb-gauge-enh {
        height: 1;
    }
    #wb-specs-grid {
        height: auto;
        width: 1fr;
        margin-top: 0;
    }
    #wb-specs-col-left {
        width: 1fr;
        height: auto;
        margin-right: 1;
    }
    #wb-specs-col-right {
        width: 1fr;
        height: auto;
    }
    .wb-spec-line {
        min-height: 1;
        height: auto;
        color: $text;
    }
    .wb-section-title {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        height: 1;
    }
    #wb-chain-box {
        height: auto;
        background: $surface;
        border: dashed $secondary;
        padding: 0 1;
        margin-top: 0;
        margin-bottom: 0;
    }
    #wb-telemetry-grid {
        height: auto;
        width: 1fr;
        margin-top: 0;
    }
    #wb-telemetry-col-left {
        width: 1fr;
        height: auto;
        margin-right: 1;
    }
    #wb-telemetry-col-right {
        width: 1fr;
        height: auto;
    }
    #wb-download-progress {
        height: 1;
        width: 1fr;
        display: none;
        margin-top: 1;
    }
    #wb-stem-progress {
        height: 1;
        width: 1fr;
        display: none;
        margin-top: 1;
    }
    #wb-task-status {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #wb-page-repair {
        height: auto;
        min-height: 1fr;
        width: 1fr;
        display: none;
        border-top: heavy $primary;
        background: $panel;
        padding: 0 1;
    }
    #rp-title {
        text-style: bold;
        color: $accent;
    }
    #rp-status, #rp-progress, #rp-detector-hint {
        color: $text-muted;
    }
    #rp-question, #rp-summary {
        margin-top: 1;
    }
    .rp-range-title {
        color: $text-muted;
    }
    .rp-range-input {
        width: 10;
    }
    .rp-range-arrow {
        width: 3;
        padding: 0 1;
    }
    .rp-range-remove {
        min-width: 5;
    }
    #wb-page-vis {
        height: auto;
        min-height: 1fr;
        border-top: heavy $primary;
        background: $panel;
        padding: 0 1;
        display: none;
    }
    .wb-vis-row-top {
        height: 10;
        width: 1fr;
        margin-top: 1;
        margin-bottom: 1;
    }
    .wb-vis-row-bot {
        height: 10;
        width: 1fr;
        margin-bottom: 1;
    }
    .wb-vis-cell {
        width: 1fr;
        height: 10;
        border: round $secondary;
        background: #0d0e15;
        padding: 0 1;
        margin-right: 1;
    }
    .wb-vis-label {
        text-style: bold;
        color: $warning;
        height: 1;
        margin-bottom: 0;
    }
    #wb-layers-title {
        height: 1;
        width: 1fr;
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }
    #wb-layers-actions {
        height: auto;
        width: 1fr;
        margin-top: 1;
    }
    #wb-layers-actions .wb-layers-btn {
        margin-right: 1;
    }
    #wb-layers-actions .wb-layers-btn:hover {
        text-style: bold;
        background: $accent;
        color: $surface;
    }
    .wb-model-row {
        height: 1;
        width: 1fr;
        margin-top: 0;
        margin-bottom: 0;
        align: left middle;
    }
    .wb-model-title {
        width: 38;
        height: 1;
        color: $accent;
        text-style: bold;
    }
    .wb-stepper-box {
        height: 1;
        width: auto;
        align: left middle;
    }
    /* Borderless chips: the default `tall` border would consume the single row
       and hide the `−` / `+` glyph; colours give 15:1 contrast. */
    .wb-model-desc {
        height: 1;
        color: $text-muted;
        margin-left: 2;
    }
    #wb-stem-actions-row .wb-stem-action-btn {
        height: 1;
        min-width: 15;
        padding: 0 1;
        margin-right: 1;
        border: none;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    #wb-stem-actions-row .wb-action-detect:hover {
        background: $secondary;
        color: #000000;
    }
    #wb-stem-actions-row .wb-action-resep:hover {
        background: $warning;
        color: #000000;
    }
    #wb-status {
        height: 1;
        width: 1fr;
        color: $warning;
        background: #11111b;
        text-style: bold;
        margin-top: 1;
        padding: 0 1;
        overflow: hidden;
    }
    #wb-stems-racks-row .wb-diagnostic-btn {
        min-width: 7;
        height: 1;
        margin-left: 1;
        border: none;
        text-align: center;
        content-align: center middle;
    }
    .wb-defect-checkbox:hover {
        color: $accent;
    }
    """

    active_stream: reactive[StreamId] = reactive("MP3")
    current_job: reactive[TrackJob | None] = reactive(None)
    cutoff_hz: reactive[float] = reactive(15500.0)
    _export_mode: reactive[str] = reactive("ENH")  # "ENH" | "VOC" | "INST"

    def __init__(
        self,
        on_exported: Callable[[Path], None] | None = None,
        id: str | None = "workbench-widget",
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.on_exported = on_exported
        self.preview_manager = PreviewManager()
        self.exporter = EnhancementExporter(neural_enabled=True)
        self.selected_preset_id: str = "conservative"
        self.neural_enabled: bool = True
        self.audition_cache_dir = Path(platformdirs.user_cache_dir("omnirip")) / "audition"
        self.audition_cache_dir.mkdir(parents=True, exist_ok=True)

        # Active page: "deck" or "eq"
        self.active_page: str = "deck"
        self.eq_target: str = "master"
        self.eq_settings_by_target: dict[str, MasteringEQSettings] = {}
        for target in EQ_TARGETS:
            settings = MasteringEQSettings()
            settings.apply_preset(DEFAULT_EQ_PRESET.get(target, "Flat"), eq_bank(target))
            self.eq_settings_by_target[target] = settings
        self.eq_settings: MasteringEQSettings = self.eq_settings_by_target["master"]
        self.genre_mode: str = "auto"
        self.genre_intensity: str = DEFAULT_GENRE_INTENSITY
        self._genre_configured: bool = False
        self._genre_detected: GenreChoice = GenreChoice()
        self._genre_choice: GenreChoice = GenreChoice()
        self._genre_mix_keys: tuple[str, ...] = ()
        self._eq_debounce_timer: asyncio.TimerHandle | None = None

        # Stem blend weights: how much to trust neural model output vs. inversion subtraction
        self.stem_bsr_blend: float = 0.70
        self.stem_hdemucs_blend: float = 0.50
        self.stem_crossover_hz: float = 300.0
        self.stem_dereverb_intensity: float = 0.40

        # Multi-choice stem defect remediations (10 vocal, 10 instrumental):

        # Stream paths: MP3 (Original), ENH (Restored), VOC (Vocals), INST (Instrumental)
        self.path_mp3: Path | None = None
        self.path_enh: Path | None = None
        self.path_voc: Path | None = None
        self.path_inst: Path | None = None
        self._is_generating_enh: bool = False
        self._operation_state = WorkbenchOperationState()

        # Layer Studio: separated per-source stems + their stem directory
        self.stem_cache_dir: Path | None = None

        # Detached layer terminal (Option B): open the Layers page in its own
        # Terminal.app window writing/reading the JSON sidecar instead of (only)
        # the embedded workbench panel.
        self._diarize_timer: Timer | None = None
        self._diarize_started: float = 0.0
        self._diarizer: object | None = None
        self._hosted_pending: tuple[Path, int] | None = None

        # Processing preset (docs/13): which stages run for this session. The
        self.recording_credits: object | None = None
        self._credits_task_running: bool = False
        # Measured speaker count (docs/13 D27) — advisory, never overwrites the
        # MusicBrainz credit count.
        self.measured_speakers: int | None = None
        self._hosted_task_running: bool = False
        self._diarize_task_running: bool = False
        self._pending_repair_plan: Any = None
        self._repair_result: Any = None

    @property
    def track_generation(self) -> int:
        """Monotonic context generation used to reject late worker results."""
        return self._operation_state.generation

    def _begin_operation(self, operation: Operation) -> OperationToken | None:
        """Start an exclusive UI operation and report conflicts without raising."""
        try:
            return self._operation_state.begin(operation)
        except (OperationBusyError, RuntimeError) as exc:
            self._update_status(f"Busy: {exc}")
            return None

    def _finish_operation(self, token: OperationToken, *, dirty: bool | None = None) -> bool:
        """Finish an operation only if it still belongs to the visible track."""
        return self._operation_state.finish(token, dirty=dirty)

    def _is_current_operation(self, token: OperationToken) -> bool:
        """Return false for a worker that belongs to an old track or operation."""
        return self._operation_state.is_current(token)

    def _is_current_track(self, source: Path | None, generation: int) -> bool:
        """Guard UI mutations from late workers, including same-path track reloads."""
        return generation == self.track_generation and source == self.path_mp3

    def _cancel_track_workers(self) -> None:
        """Cancel workers whose results are scoped to the current track."""
        track_worker_names = {
            "render-stream-enh",
            "warm-mode-cache",
            "stem-acoustic-detect",
            "hosted-separation",
            "speaker-measure",
            "credits-lookup",
            "layer-studio-build",
            "layer-studio-commit",
            "layer-terminal-launch",
            "retag-pass",
            "repair-detect",
            "repair-run",
            "repair-suggest",
            "repair-export",
            "genre-mb",
        }
        for worker in list(self.workers):
            if worker.name in track_worker_names:
                worker.cancel()

    def _reset_track_scoped_state(self, job: TrackJob) -> None:
        """Invalidate workers and clear every result owned by the previous track."""
        self._cancel_track_workers()
        self._operation_state.load_track(job.id or str(job.input_path or job.output_path or ""))
        self._is_generating_enh = False
        self._credits_task_running = False
        self._hosted_task_running = False
        self._diarize_task_running = False
        self._pending_repair_plan = None
        self._repair_result = None
        self._genre_detected = GenreChoice()
        self._genre_choice = GenreChoice()
        self._genre_mix_keys = ()
        self.path_mp3 = None
        self.path_enh = None
        self.path_voc = None
        self.path_inst = None
        self.stem_cache_dir = None
        self.recording_credits = None
        self.measured_speakers = None
        self._diarize_started = 0.0
        if self._diarize_timer is not None:
            self._diarize_timer.stop()
            self._diarize_timer = None
        with contextlib.suppress(Exception):
            self.query_one("#wb-status", Label).update("Loading track…")

    def _render_fader_track(self, gain_db: float) -> str:
        """Render a 13-line vertical studio fader rail with center 0dB line,
        calibration ticks, and movable thumb.

        Gain range: -12.0dB to +12.0dB in 2.0dB slot increments.
        """
        if gain_db >= 11.0:
            slot = 0
        elif gain_db >= 9.0:
            slot = 1
        elif gain_db >= 7.0:
            slot = 2
        elif gain_db >= 5.0:
            slot = 3
        elif gain_db >= 3.0:
            slot = 4
        elif gain_db >= 1.0:
            slot = 5
        elif gain_db > -1.0:
            slot = 6
        elif gain_db > -3.0:
            slot = 7
        elif gain_db > -5.0:
            slot = 8
        elif gain_db > -7.0:
            slot = 9
        elif gain_db > -9.0:
            slot = 10
        elif gain_db > -11.0:
            slot = 11
        else:
            slot = 12

        thumb = (
            "[bold cyan]─█─[/bold cyan]"
            if gain_db > 0.1
            else (
                "[bold magenta]─█─[/bold magenta]"
                if gain_db < -0.1
                else "[bold white]─█─[/bold white]"
            )
        )

        lines = []
        for i in range(13):
            if i == slot:
                lines.append(thumb)
            elif i == 0:
                lines.append("[dim]─┬─[/dim]")
            elif i == 6:
                lines.append("[yellow]─┼─[/yellow]")
            elif i == 12:
                lines.append("[dim]─┴─[/dim]")
            elif i in (3, 9):
                lines.append("[dim]─┼─[/dim]")
            else:
                lines.append("[dim] │ [/dim]")
        return "\n".join(lines)

    def path_c(self, val: Path | None) -> None:
        self.path_enh = val

    def compose(self) -> ComposeResult:
        yield Label("CURATION & ENHANCEMENT WORKBENCH", id="wb-header")
        yield Label("No track selected — click a track in the table above", id="wb-track-meta")
        yield Label("Cutoff fc: -- kHz | State: IDLE", id="wb-cutoff-info")

        with Horizontal(id="wb-stream-row"):
            yield Button("[1] MP3", id="btn-stream-mp3", variant="primary")
            yield Button("[2] ENH", id="btn-stream-enh", variant="default")

        yield ProgressBar(id="wb-stem-progress", total=100, show_eta=False, show_percentage=True)
        yield Label("", id="wb-task-status")

        with Horizontal(id="wb-controls-row"):
            preset_options = ECO_PRESET_OPTIONS + AI_PRESET_OPTIONS
            yield Select(
                options=preset_options, value=self.selected_preset_id, id="wb-preset-select"
            )
            yield Label("GENRE", classes="wb-eq-toolbar-label")
            yield Select(
                options=self._genre_options(), value="auto", id="wb-genre-select"
            )
            yield Select(
                options=[(name.title(), name) for name in GENRE_INTENSITIES],
                value=self.genre_intensity,
                id="wb-genre-intensity",
            )
            with Horizontal(id="wb-export-split"):
                yield Button("⤓ SAVE ENHANCED", id="wb-btn-export", variant="success")
                yield Button("↓", id="wb-btn-export-menu", variant="success")

        yield Label("", id="wb-genre-recipe")

        with Horizontal(id="wb-export-dropdown"):
            yield Label("FORMAT:", id="wb-export-dropdown-title")
            yield Button("♪  Enhanced MP3",        id="wb-export-choose-enh",  classes="wb-export-choice")
            yield Button("▤  Enhanced WAV (24-bit)", id="wb-export-choose-wav", classes="wb-export-choice")
            yield Button("▥  Enhanced FLAC (24-bit)", id="wb-export-choose-flac", classes="wb-export-choice")
            yield Button("♬  Vocals (WAV)",        id="wb-export-choose-voc",  classes="wb-export-choice")
            yield Button("♩  Instrumental (WAV)", id="wb-export-choose-inst", classes="wb-export-choice")
            yield Button("✕  Close",               id="wb-export-choose-close", classes="wb-export-choice")

        with Vertical(id="wb-inspector-container"):
            with Vertical(id="wb-page-deck"):
                yield Label("RESTORATION MASTERING DECK", id="wb-inspector-title")
                yield Label("", id="wb-gauge-orig")
                yield Label("", id="wb-gauge-enh")
                with Horizontal(id="wb-specs-grid"):
                    with Vertical(id="wb-specs-col-left"):
                        yield Label("", id="wb-spec-cutoff", classes="wb-spec-line")
                        yield Label("", id="wb-spec-bandwidth", classes="wb-spec-line")
                        yield Label("", id="wb-spec-gain", classes="wb-spec-line")
                        yield Label("", id="wb-spec-trim", classes="wb-spec-line")
                        yield Label("", id="wb-spec-slope", classes="wb-spec-line")
                    with Vertical(id="wb-specs-col-right"):
                        yield Label("", id="wb-spec-stereo", classes="wb-spec-line")
                        yield Label("", id="wb-spec-base", classes="wb-spec-line")
                        yield Label("", id="wb-spec-ceiling", classes="wb-spec-line")
                        yield Label("", id="wb-spec-engine", classes="wb-spec-line")
                        yield Label("", id="wb-spec-stream", classes="wb-spec-line")
                yield Label("", id="wb-spec-profile-header", classes="wb-spec-line")
                yield Label("", id="wb-spec-profile-desc", classes="wb-spec-line")
                yield Label(
                    "ACOUSTIC RESTORATION SIGNAL CHAIN PIPELINE",
                    id="wb-chain-title",
                    classes="wb-section-title",
                )
                with Vertical(id="wb-chain-box"):
                    yield Label("", id="wb-chain-flow")
                    yield Label("", id="wb-chain-detail")
                yield Label(
                    "PROVENANCE & HARMONIC MASTERING TELEMETRY",
                    id="wb-telemetry-title",
                    classes="wb-section-title",
                )
                with Horizontal(id="wb-telemetry-grid"):
                    with Vertical(id="wb-telemetry-col-left"):
                        yield Label("", id="wb-telem-nyquist", classes="wb-spec-line")
                        yield Label("", id="wb-telem-crossover", classes="wb-spec-line")
                        yield Label("", id="wb-telem-passthrough", classes="wb-spec-line")
                    with Vertical(id="wb-telemetry-col-right"):
                        yield Label("", id="wb-telem-limiter", classes="wb-spec-line")
                        yield Label("", id="wb-telem-format", classes="wb-spec-line")
                        yield Label("", id="wb-telem-destination", classes="wb-spec-line")

            with Vertical(id="wb-page-eq"):
                with Horizontal(id="wb-eq-toolbar"):
                    yield Label("10-BAND STUDIO EQ · MASTER", id="wb-eq-title")
                    yield Label("Target:", classes="wb-eq-toolbar-label")
                    yield Select(
                        options=[(label, key) for key, label in EQ_TARGETS.items()],
                        value="master",
                        id="wb-eq-target-select",
                    )
                    yield Label("Preset:", classes="wb-eq-toolbar-label")
                    yield Select(
                        options=[(k, k) for k in EQ_PRESET_BANKS["master"]],
                        value="Flat",
                        allow_blank=True,
                        id="wb-eq-preset-select",
                    )
                with Horizontal(id="wb-eq-sliders-row"):
                    for freq in EQ_FREQUENCIES:
                        lbl_text = f"{freq}Hz" if freq < 1000 else f"{freq // 1000}kHz"
                        with Vertical(classes="wb-eq-col", id=f"wb-eq-col-{freq}"):
                            yield Button("+", id=f"wb-eq-up-{freq}", classes="wb-eq-btn-up")
                            yield Label(
                                self._render_fader_track(0.0),
                                id=f"wb-eq-track-{freq}",
                                classes="wb-eq-track",
                            )
                            yield Button("-", id=f"wb-eq-dn-{freq}", classes="wb-eq-btn-dn")
                            yield Label("0.0dB", id=f"wb-eq-val-{freq}", classes="wb-eq-val")
                            yield Label(lbl_text, classes="wb-eq-label")
                with Horizontal(id="wb-eq-controls-row"):
                    yield Button("RESET FLAT", id="wb-btn-eq-reset", variant="default")
                    yield Button("EQ: ENGAGED", id="wb-btn-eq-toggle", variant="primary")
                    yield Button("HPF 30Hz: OFF", id="wb-btn-eq-hpf", variant="default")
                    yield Button("+3dB AIR", id="wb-btn-eq-air", variant="default")
                    yield Button("TRIM: 0.0dB", id="wb-btn-eq-trim", variant="default")

            with Vertical(id="wb-page-repair"):
                yield RepairPanel()

            with Vertical(id="wb-page-vis"):
                yield Label(
                    "AUDIO VISUALIZATION STUDIO  [Multi-Engine Acoustic Analysis]",
                    id="wb-vis-title",
                    classes="wb-section-title",
                )
                with Horizontal(classes="wb-vis-row-top"):
                    with Vertical(classes="wb-vis-cell"):
                        yield Label("10-BAND SPECTRUM ANALYZER (fc Cutoff)", classes="wb-vis-label")
                        yield AudioVisualizer(num_bands=10, mode="spectrum", cutoff_hz=self.cutoff_hz, id="wb-visualizer")
                    with Vertical(classes="wb-vis-cell"):
                        yield Label("PHOSPHOR WAVEFORM OSCILLOSCOPE", classes="wb-vis-label")
                        yield AudioVisualizer(mode="oscilloscope", id="wb-vis-osc")
                with Horizontal(classes="wb-vis-row-bot"):
                    with Vertical(classes="wb-vis-cell"):
                        yield Label("SYMMETRICAL MIRRORED DANCE", classes="wb-vis-label")
                        yield AudioVisualizer(mode="mirrored", id="wb-vis-mir")
                    with Vertical(classes="wb-vis-cell"):
                        yield Label("BRAILLE WAVE MATRIX (2x4 Dot Matrix)", classes="wb-vis-label")
                        yield AudioVisualizer(mode="braille", id="wb-vis-braille")
                    with Vertical(classes="wb-vis-cell"):
                        yield Label("STEREO VU DECK (dB Headroom)", classes="wb-vis-label")
                        yield AudioVisualizer(mode="vu_meter", id="wb-vis-vu")

        yield ProgressBar(id="wb-download-progress", total=100, show_eta=True)
        yield StockTickerTape("", id="wb-status")

    def load_job(self, job: TrackJob) -> None:
        """Load a track job into the workbench, resolve streams, and pre-render ENH."""
        self._reset_track_scoped_state(job)
        self.current_job = job
        cutoff = job.spectral.cutoff_hz if (job.spectral and job.spectral.cutoff_hz) else 15500.0
        self.cutoff_hz = cutoff
        self._configure_genre_once()
        self._detect_genre_from_tags(job)
        self._apply_genre_mode(rerender=False)

        # MP3 audio: prefer output_path (transcode), fallback to workspace/input
        if job.output_path and job.output_path.exists():
            self.path_mp3 = job.output_path
        elif job.workspace_path and job.workspace_path.exists():
            self.path_mp3 = job.workspace_path
        elif job.input_path and job.input_path.exists():
            self.path_mp3 = job.input_path
        else:
            self.path_mp3 = None

        # Check if separated stems are already available in cache
        self.path_voc = None
        self.path_inst = None
        if self.path_mp3:
            from harvester.analysis.enhancement.stem_separator import stem_dir_for

            stem_dir = stem_dir_for(self.path_mp3)
            stale_cache = False
            if stem_dir.exists():
                from harvester.analysis.enhancement.stem_cache import (
                    cache_matches,
                    read_stage_meta,
                )

                if not cache_matches(stem_dir, self.path_mp3):
                    # Same stem + size but provably different audio: adopting
                    # these stems would show another song's lanes (docs/14 M2).
                    stale_cache = True
                    self._update_status(
                        "Cached stems belong to another source file — "
                        "press ⚡ BUILD STEMS to replace them."
                    )
                else:
                    # Advisory results persist beside the stems and come back
                    # only when they belong to this exact source.
                    restored: list[str] = []
                    dia_meta = read_stage_meta(stem_dir, "diarization")
                    # The production writer records the file actually diarized
                    # (the vocals stem when one exists), so verify THAT file's
                    # identity instead of the mp3's (docs/14 M2, review finding).
                    # The stem dir itself already matched this source above.
                    dia_ok = False
                    if dia_meta:
                        try:
                            from harvester.analysis.enhancement.stem_cache import (
                                source_fingerprint,
                            )

                            recorded_fp = str(dia_meta.get("source_fingerprint") or "")
                            recorded_path = Path(str(dia_meta.get("source_path") or ""))
                            if recorded_fp and recorded_path.exists():
                                dia_ok = recorded_fp == source_fingerprint(recorded_path)
                            elif recorded_path.exists():
                                dia_ok = recorded_path.stat().st_size == int(
                                    dia_meta.get("source_size", -1)
                                )
                        except (OSError, TypeError, ValueError):
                            dia_ok = False
                    if dia_ok and dia_meta:
                        try:
                            self.measured_speakers = int(dia_meta["speaker_count"])
                            restored.append(
                                f"speakers {self.measured_speakers} "
                                f"({dia_meta.get('model', 'pyannote')}, {dia_meta.get('device', 'cpu')})"
                            )
                        except (KeyError, TypeError, ValueError):
                            self.measured_speakers = None
                    tags_meta = read_stage_meta(stem_dir, "tags")
                    if tags_meta and self.path_mp3.stat().st_size == int(
                        tags_meta.get("source_size", -1)
                    ):
                        labels = [str(label) for label in (tags_meta.get("labels") or [])]
                        model = str(tags_meta.get("model", "clap")).rsplit("/", 1)[-1]
                        if labels:
                            restored.append(f"tags ({model}): {', '.join(labels)}")
                    if restored:
                        self._update_status("Restored from cache: " + " · ".join(restored))
            if stem_dir.exists() and not stale_cache:
                base = self.path_mp3.stem
                templates = (
                    (f"{base}_ensemble_vocals.wav", f"{base}_ensemble_instrumental.wav"),
                    (f"{base}_neural_vocals.wav", f"{base}_neural_instrumental.wav"),
                    (f"{base}_bs_roformer_vocals.wav", f"{base}_bs_roformer_instrumental.wav"),
                    (f"{base}_vocals.wav", f"{base}_instrumental.wav"),
                    (f"{base}_eco_vocals.wav", f"{base}_eco_instrumental.wav"),
                    (
                        f"{base}_hosted_repair_vocals.wav",
                        f"{base}_hosted_repair_instrumental.wav",
                    ),
                )
                for vocals_name, inst_name in templates:
                    v_cand = stem_dir / vocals_name
                    i_cand = stem_dir / inst_name
                    if v_cand.exists() and i_cand.exists():
                        self.path_voc = v_cand
                        self.path_inst = i_cand
                        self.stem_cache_dir = stem_dir
                        break

        with contextlib.suppress(Exception):
            self.query_one("#wb-stem-progress", ProgressBar).styles.display = "none"

        # Check if enhanced derivative is available (exported or in audition cache)
        if self.path_mp3:
            candidate_enh = self.path_mp3.with_suffix(".enhanced.mp3")
            mode_tag = "neural" if self.neural_enabled else "eco"
            cached_audition = (
                self.audition_cache_dir
                / f"{self.path_mp3.stem}_{self.selected_preset_id}_{mode_tag}.mp3"
            )
            if candidate_enh.exists():
                self.path_enh = candidate_enh
            elif cached_audition.exists():
                self.path_enh = cached_audition
            else:
                self.path_enh = None
                # Pre-generate in isolated audition cache without polluting output folder
                self._trigger_enhancement_pregeneration()
        else:
            self.path_enh = None

        # Update metadata and inspector
        name = job.display_name
        self.query_one("#wb-track-meta", Label).update(f"TRACK: {name}")
        self.query_one("#wb-cutoff-info", Label).update(
            f"Cutoff fc: {cutoff / 1000.0:.1f} kHz | Verdict: {job.spectral.verdict.value.upper()}"
        )

        vis = self.query_one("#wb-visualizer", AudioVisualizer)
        vis.set_cutoff(cutoff)
        self._update_inspector()

        # Default to MP3 stream
        self.set_active_stream("MP3")
        self._start_genre_musicbrainz_lookup(job)
        if self.active_page == "repair":
            self._start_repair_detection()

    def _update_inspector(self) -> None:
        """Update comparative spectral gauges and dynamic mastering metrics based on preset."""
        cutoff_khz = self.cutoff_hz / 1000.0
        restored_khz = 22.05
        delta_khz = max(0.0, restored_khz - cutoff_khz)
        preset = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
        preset_name = preset.name
        gain_db = preset.residual_gain_db
        decay_slope = preset.target_decay_db_per_oct
        stereo_width = preset.residual_stereo_width
        provider_type = preset.provider_type
        ceiling = preset.ceiling_dbfs
        description = preset.description

        try:
            self.query_one("#wb-inspector-title", Label).update(
                f"MASTERING DECK // {preset_name.upper()}"
            )

            # Clean frequency expansion diagram without bracket leaks or overflow
            self.query_one("#wb-gauge-orig", Label).update(
                f"[bold cyan]Baseband:[/bold cyan] [cyan]0k ═════ "
                f"{cutoff_khz:.1f}k[/cyan] [red]── CUTOFF ── 22k[/red]"
            )
            self.query_one("#wb-gauge-enh", Label).update(
                f"[bold green]Restored:[/bold green] [cyan]0k ═════ "
                f"{cutoff_khz:.1f}k[/cyan] [bold green]══════ 22.05k[/bold green]"
            )

            self.query_one("#wb-spec-cutoff", Label).update(
                f"• Cutoff Limit  : [bold cyan]{cutoff_khz:.2f} kHz[/bold cyan] (Original)"
            )
            self.query_one("#wb-spec-bandwidth", Label).update(
                f"• Restored Band : [bold green]{restored_khz:.2f} kHz[/bold green] "
                f"([green]+{delta_khz:.2f}k Air[/green])"
            )

            # Dynamic Gain / Loss display
            if gain_db > 0:
                gain_markup = f"[bold green]+{gain_db:.1f} dB (Air Boost)[/bold green]"
                trim_bar = "[cyan]-- 0dB [/cyan][bold green]══▲══ +3dB[/bold green]"
            elif gain_db < 0:
                gain_markup = f"[bold red]{gain_db:.1f} dB (De-Sizzle Cut)[/bold red]"
                trim_bar = "[bold red]-3dB ══▲══[/bold red][cyan] 0dB --[/cyan]"
            else:
                gain_markup = "[bold cyan]0.0 dB (Neutral Overtones)[/bold cyan]"
                trim_bar = "[cyan]-3dB ─── ▲ ─── +3dB[/cyan]"

            self.query_one("#wb-spec-gain", Label).update(f"• High-Band Gain: {gain_markup}")
            self.query_one("#wb-spec-trim", Label).update(f"• Gain Trim Bar : {trim_bar}")

            self.query_one("#wb-spec-slope", Label).update(
                f"• Acoustic Slope: [bold]-{decay_slope:.1f} dB/oct[/bold] (Roll-off)"
            )

            stereo_pct = round(stereo_width * 100)
            if stereo_pct < 80:
                stereo_str = f"[yellow]{stereo_pct}% Focused (Headphone)[/yellow]"
            else:
                stereo_str = f"[cyan]{stereo_pct}% Stereo (Mono <100Hz)[/cyan]"
            self.query_one("#wb-spec-stereo", Label).update(f"• Stereo Width  : {stereo_str}")

            self.query_one("#wb-spec-base", Label).update(
                f"• Sub-Cutoff Base: [bold]0–{cutoff_khz:.1f}k Bit-Exact[/bold]"
            )
            self.query_one("#wb-spec-ceiling", Label).update(
                f"• Limiter Guard : [bold]{ceiling:.1f} dBFS[/bold] Headroom"
            )

            engine_names = {
                "conservative": "Non-Neural DSP Exciter",
                "nvsr": "NVSR Multi-Band Residual",
                "hybrid": "Hybrid (NVSR + FlashSR)",
            }
            engine_str = engine_names.get(provider_type, provider_type.upper())
            if not self.neural_enabled:
                engine_display = f"🌱 Eco DSP ({engine_str})"
            else:
                engine_display = f"⚡ Neural AI ({engine_str})"
            self.query_one("#wb-spec-engine", Label).update(
                f"• Model Engine  : [bold]{engine_display}[/bold]"
            )

            is_enh = self.active_stream == "ENH"
            stream_style = (
                "[bold green]NEURAL RESTORED ACTIVE (A/B)[/bold green]"
                if is_enh
                else "[bold cyan]MP3 ORIGINAL BASEBAND (A/B)[/bold cyan]"
            )
            self.query_one("#wb-spec-stream", Label).update(f"• Active Stream : {stream_style}")

            # Wrapped profile description to utilize bottom space
            words = description.split()
            w1: list[str] = []
            w2: list[str] = []
            cur_l = 0
            for w in words:
                if cur_l + len(w) + 1 <= 68 and not w2:
                    w1.append(w)
                    cur_l += len(w) + 1
                else:
                    w2.append(w)
            desc1 = " ".join(w1)
            desc2 = " ".join(w2)

            self.query_one("#wb-spec-profile-header", Label).update(
                f"• Sonic Goal    : [dim italic]{desc1}[/dim italic]"
            )
            self.query_one("#wb-spec-profile-desc", Label).update(
                f"  [dim italic]{desc2}[/dim italic]" if desc2 else ""
            )

            # Signal Chain Pipeline - concise 5 stages that fit on any terminal
            flow_str = (
                f"[cyan]\\[1. Baseband 0..{cutoff_khz:.1f}k\\][/cyan] ─> "
                f"[magenta]\\[2. FIR Split\\][/magenta] ─> "
                f"[yellow]\\[3. {preset_name}\\][/yellow] ─> "
                f"[blue]\\[4. Stereo\\][/blue] ─> "
                f"[green]\\[5. Limiter {ceiling:.1f}dB\\][/green]"
            )
            self.query_one("#wb-chain-flow", Label).update(f"  {flow_str}")
            active_flag = (
                "[bold green]LIVE AUDITION RESTORED[/bold green]"
                if is_enh
                else "[bold cyan]LIVE AUDITION BASEBAND[/bold cyan]"
            )
            self.query_one("#wb-chain-detail", Label).update(
                f"  [dim]Engine: {engine_display} • Status: [/dim]{active_flag}"
            )

            # Mastering & Provenance Telemetry - concise <=42 chars per col
            self.query_one("#wb-telem-nyquist", Label).update(
                "• Nyquist Headroom : [bold green]22.05 kHz[/bold green] [dim](Full-Band)[/dim]"
            )
            self.query_one("#wb-telem-crossover", Label).update(
                f"• Crossover Filter : [bold cyan]384-tap FIR[/bold cyan] "
                f"[dim]({cutoff_khz:.1f}k Linear)[/dim]"
            )
            self.query_one("#wb-telem-passthrough", Label).update(
                "• Sub-Cutoff Audio : [bold green]Bit-Exact[/bold green] [dim](100% Pure)[/dim]"
            )
            self.query_one("#wb-telem-limiter", Label).update(
                f"• Limiter Ceiling  : [bold yellow]{ceiling:.1f} dBFS[/bold yellow] "
                f"[dim](ITU-R Guard)[/dim]"
            )
            self.query_one("#wb-telem-format", Label).update(
                "• Export Encoding  : [bold]320 kbps CBR[/bold] [dim](ID3v2 TXXX)[/dim]"
            )
            dest_folder = "~/Music/Harvested"
            app_cfg = getattr(self.app, "config", None)
            if app_cfg and hasattr(app_cfg, "general") and app_cfg.general.output_dir:
                dest_folder = str(app_cfg.general.output_dir)
            elif self.current_job and self.current_job.output_path:
                dest_folder = str(self.current_job.output_path.parent)

            # Contract home directory to ~ to prevent path clipping
            home = str(Path.home())
            if dest_folder.startswith(home):
                dest_folder = "~" + dest_folder[len(home):]
            if len(dest_folder) > 28:
                dest_folder = "..." + dest_folder[-25:]

            self.query_one("#wb-telem-destination", Label).update(
                f"• Target Directory : [cyan]{dest_folder}[/cyan]"
            )
        except Exception:
            pass

    def set_active_stream(self, stream: str) -> None:
        """Switch audition stream: [1] MP3, [2] ENH, [3] VOC, or [4] INST."""
        if stream in ("ENH", "C"):
            normalized = "ENH"
        elif stream in ("VOC", "V"):
            normalized = "VOC"
        elif stream in ("INST", "I", "KARAOKE"):
            normalized = "INST"
        else:
            normalized = "MP3"

        self.active_stream = normalized
        preset = PRESETS.get(self.selected_preset_id)
        p_name = preset.name if preset else "Conservative DSP"

        try:
            btn_mp3 = self.query_one("#btn-stream-mp3", Button)
            btn_enh = self.query_one("#btn-stream-enh", Button)
            btn_mp3.variant = "primary" if normalized == "MP3" else "default"
            btn_enh.variant = "primary" if normalized == "ENH" else "default"

        except Exception:
            pass

        track_name = self.path_mp3.name if self.path_mp3 else "Audio"
        if normalized == "MP3":
            if self.path_mp3 and self.path_mp3.exists():
                self._route_to_player(
                    self.path_mp3,
                    title=f"[MP3] {self.path_mp3.name}",
                    is_enhanced=False,
                )
                self.query_one("#wb-status", Label).update("Auditioning [MP3]: Original Audio")
            else:
                self.query_one("#wb-status", Label).update("MP3 stream not found on disk.")
        elif normalized == "ENH":
            if self.path_enh and self.path_enh.exists():
                self._route_to_player(
                    self.path_enh,
                    title=f"[ENH] Restored ({p_name})",
                    is_enhanced=True,
                    preset_name=p_name,
                )
                self.query_one("#wb-status", Label).update(
                    f"Auditioning [ENH]: Restored ({p_name})"
                )
            elif self.path_mp3 and self.path_mp3.exists():
                self.query_one("#wb-status", Label).update(
                    f"Synthesizing restoration with '{p_name}'..."
                )
                self._trigger_enhancement_pregeneration()
        elif normalized in ("VOC", "INST"):
            self._audition_stem(normalized, track_name)

        self._update_inspector()

    def _audition_stem(self, stream: str, track_name: str) -> None:
        """Audition a separated stem, or explain how to create one."""
        if not self.neural_enabled:
            self.query_one("#wb-status", Label).update(
                "⚠ Stem separation requires Neural AI mode — enable it first."
            )
            return
        is_vocals = stream == "VOC"
        stem = self.path_voc if is_vocals else self.path_inst
        if stem is not None and stem.exists():
            title = (
                f"[VOC] Isolated Vocals ({track_name})"
                if is_vocals
                else f"[INST] Karaoke Backing ({track_name})"
            )
            status = (
                "Auditioning [VOC]: Isolated Vocals (Acapella)"
                if is_vocals
                else "Auditioning [INST]: Karaoke Instrumental"
            )
            self._route_to_player(stem, title=title, is_enhanced=True)
            self.query_one("#wb-status", Label).update(status)
            return
        label = "vocals" if is_vocals else "instrumental"
        self._update_status(
            f"No separated {label} yet — run Repair → 𝄢 STEMS ONLY to create them."
        )

    # ------------------------------------------------------------------
    # Genre intent colour (docs/01 D38)
    # ------------------------------------------------------------------

    def _master_eq_settings(self) -> MasteringEQSettings:
        """User master EQ + genre intent: what playback and every master export use."""
        return compose_master_settings(
            self.eq_settings_by_target["master"], self._genre_choice, self.genre_intensity
        )

    def _effective_master_preset(self, preset):
        """Base enhancement preset with the genre mix's width/limiter policy applied."""
        return effective_preset(preset, self._genre_choice)

    def _genre_extra_tags(self) -> dict[str, str]:
        if not self._genre_choice.detected:
            return {}
        return {
            "GENRE": ",".join(self._genre_choice.keys),
            "GENRE_MIX": self._genre_choice.label(),
            "GENRE_INTENSITY": self.genre_intensity,
        }

    def _genre_options(self) -> list[tuple[str, str]]:
        auto_label = "Auto"
        if self._genre_detected.detected:
            auto_label = f"Auto — {self._genre_detected.label(max_auto=2)}"
        options = [("Neutral", "neutral"), ("Mix…", "mix"), (auto_label, "auto")]
        options.extend(
            (profile.label, key)
            for key, profile in GENRE_PROFILES.items()
            if key != "neutral"
        )
        return options

    def _update_genre_ui(self) -> None:
        options = self._genre_options()
        with contextlib.suppress(Exception):
            select = self.query_one("#wb-genre-select", Select)
            select.set_options(options)
            keys = {key for _label, key in options}
            target = self.genre_mode if self.genre_mode in keys else "auto"
            if select.value != target:
                select.value = target
        with contextlib.suppress(Exception):
            intensity = self.query_one("#wb-genre-intensity", Select)
            if intensity.value != self.genre_intensity:
                intensity.value = self.genre_intensity
        with contextlib.suppress(Exception):
            base = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
            effective = effective_preset(base, self._genre_choice)
            self.query_one("#wb-genre-recipe", Label).update(
                recipe_line(
                    self._genre_choice,
                    self.genre_intensity,
                    ceiling_dbfs=effective.ceiling_dbfs,
                )
            )

    def _apply_genre_mode(self, *, rerender: bool = True) -> None:
        previous_tag = self._master_eq_settings().cache_tag()
        if self.genre_mode == "mix" and self._genre_mix_keys:
            weight = 1.0 / len(self._genre_mix_keys)
            self._genre_choice = GenreChoice(
                mix=tuple((key, weight) for key in self._genre_mix_keys), source="manual"
            )
        elif self.genre_mode in GENRE_PROFILES and self.genre_mode != "neutral":
            self._genre_choice = GenreChoice(mix=((self.genre_mode, 1.0),), source="manual")
        elif self.genre_mode == "auto":
            self._genre_choice = self._genre_detected
        else:
            self._genre_choice = GenreChoice()
        self._update_genre_ui()
        self._sync_eq_to_player()
        if rerender and self._master_eq_settings().cache_tag() != previous_tag:
            self._schedule_eq_render()

    def _configure_genre_once(self) -> None:
        if self._genre_configured:
            return
        self._genre_configured = True
        processing = getattr(getattr(self.app, "config", None), "processing", None)
        if processing is None:
            return
        if processing.genre in {"auto", "mix", *GENRE_PROFILES}:
            self.genre_mode = processing.genre
        if processing.genre_intensity in GENRE_INTENSITIES:
            self.genre_intensity = processing.genre_intensity

    def _detect_genre_from_tags(self, job: Any) -> None:
        tags: dict[str, Any] = {}
        tags.update(getattr(job, "orig_tags", None) or {})
        probe = getattr(job, "probe_meta", None)
        if probe:
            tags["_probe"] = probe
        choice = choices_from_tags(tags)
        if choice.detected:
            self._genre_detected = choice

    def _start_genre_musicbrainz_lookup(self, job: Any) -> None:
        if self.genre_mode != "auto":
            return
        mbid = getattr(getattr(job, "canonical_meta", None), "mb_recording_id", None)
        if not mbid:
            return
        self.run_worker(
            self._async_genre_from_musicbrainz(str(mbid), self.track_generation),
            name="genre-mb",
        )

    async def _async_genre_from_musicbrainz(self, mbid: str, generation: int) -> None:
        from harvester.config import load_config
        from harvester.services.musicbrainz import CoverArtService

        app_cfg = getattr(self.app, "config", None) or load_config()
        service = CoverArtService(app_cfg)
        try:
            credits = await service.fetch_recording_credits(mbid)
        except Exception as exc:
            logger.info("genre lookup skipped: %s", exc)
            return
        finally:
            await service.close()
        if credits is None or not credits.genres:
            return
        if generation != self.track_generation or self.genre_mode != "auto":
            return
        choice = resolve_genre_names(
            [name for name, _count in credits.genres],
            weights=dict(credits.genres),
            source="musicbrainz",
        )
        if not choice.detected:
            return
        if choice.keys == self._genre_detected.keys:
            return
        self._genre_detected = choice
        self._apply_genre_mode()

    def _open_genre_mix(self) -> None:
        options = [
            (profile.label, key)
            for key, profile in GENRE_PROFILES.items()
            if key != "neutral"
        ]
        selected = self._genre_mix_keys or self._genre_choice.keys
        self.app.push_screen(GenreMixScreen(options, selected), self._genre_mix_done)

    def _genre_mix_done(self, keys: list[str] | None) -> None:
        if keys is None:
            self._update_genre_ui()
            return
        self._genre_mix_keys = tuple(keys)
        self.genre_mode = "mix" if keys else "neutral"
        self._apply_genre_mode()

    def _get_eq_cache_tag(self) -> str:
        """Cache tag for the enhanced stream, which always carries the master curve."""
        return self._master_eq_settings().cache_tag()

    def switch_page(self, page_id: str) -> None:
        """Switch between 'deck', 'eq', 'repair', and 'vis' tabs inside the inspector container."""
        self.active_page = page_id
        try:
            page_deck = self.query_one("#wb-page-deck", Vertical)
            page_eq = self.query_one("#wb-page-eq", Vertical)
            page_repair = self.query_one("#wb-page-repair", Vertical)
            page_vis = self.query_one("#wb-page-vis", Vertical)

            # Update page containers display
            page_deck.styles.display = "block" if page_id == "deck" else "none"
            page_eq.styles.display = "block" if page_id == "eq" else "none"
            page_repair.styles.display = "block" if page_id == "repair" else "none"
            page_vis.styles.display = "block" if page_id == "vis" else "none"

            deck_controls = "block" if page_id == "deck" else "none"
            for selector in ("#wb-stream-row", "#wb-controls-row", "#wb-genre-recipe"):
                with contextlib.suppress(Exception):
                    self.query_one(selector).styles.display = deck_controls
            with contextlib.suppress(Exception):
                self.query_one("#wb-export-dropdown").styles.display = "none"

            if page_id == "eq":
                self._update_eq_ui()
            elif page_id == "repair":
                self._start_repair_detection()
        except Exception:
            pass

    def _update_eq_ui(self) -> None:
        """Update all 10 band labels, values, fader tracks, and control buttons."""
        for f in EQ_FREQUENCIES:
            val = self.eq_settings.bands.get(f, 0.0)
            sign = "+" if val > 0 else ""
            try:
                self.query_one(f"#wb-eq-val-{f}", Label).update(f"{sign}{val:.1f}dB")
                self.query_one(f"#wb-eq-track-{f}", Label).update(self._render_fader_track(val))
            except Exception:
                pass

        try:
            btn_toggle = self.query_one("#wb-btn-eq-toggle", Button)
            if self.eq_settings.enabled:
                btn_toggle.label = "EQ: ENGAGED"
                btn_toggle.variant = "primary"
            else:
                btn_toggle.label = "EQ: BYPASS"
                btn_toggle.variant = "default"

            btn_hpf = self.query_one("#wb-btn-eq-hpf", Button)
            if self.eq_settings.hpf_30hz:
                btn_hpf.label = "HPF 30Hz: ON"
                btn_hpf.variant = "warning"
            else:
                btn_hpf.label = "HPF 30Hz: OFF"
                btn_hpf.variant = "default"

            btn_trim = self.query_one("#wb-btn-eq-trim", Button)
            trim_sign = "+" if self.eq_settings.output_trim_db > 0 else ""
            btn_trim.label = f"TRIM: {trim_sign}{self.eq_settings.output_trim_db:.1f}dB"

            select_preset = self.query_one("#wb-eq-preset-select", Select)
            bank = eq_bank(self.eq_target)
            shown = (
                self.eq_settings.preset_name
                if self.eq_settings.preset_name in bank
                else Select.NULL
            )
            if select_preset.value != shown:
                select_preset.value = shown
        except Exception:
            pass

    def _set_eq_target(self, target: str) -> None:
        """Switch the EQ page between master / vocals / instrumental shaping."""
        if target not in EQ_TARGETS:
            return
        self.eq_target = target
        self.eq_settings = self.eq_settings_by_target[target]
        bank = eq_bank(target)
        select_preset = self.query_one("#wb-eq-preset-select", Select)
        select_preset.set_options([(name, name) for name in bank])
        select_preset.value = (
            self.eq_settings.preset_name
            if self.eq_settings.preset_name in bank
            else Select.NULL
        )

        with contextlib.suppress(Exception):
            self.query_one("#wb-eq-title", Label).update(
                f"10-BAND STUDIO EQ · {EQ_TARGETS[target]}"
            )
        self._update_eq_ui()
        self._sync_eq_to_player()
        self._route_eq_target(target)

    def _route_eq_target(self, target: str) -> None:
        """Audition the stream this EQ target shapes."""
        if target == "master":
            if self.active_stream in ("VOC", "INST"):
                self.set_active_stream("ENH" if self.path_enh else "MP3")
            return
        stem = self.path_voc if target == "vocals" else self.path_inst
        if stem is not None and stem.exists():
            self.set_active_stream("VOC" if target == "vocals" else "INST")
        else:
            label = "vocals" if target == "vocals" else "instrumental"
            self._update_status(
                f"No separated {label} yet — run Repair → 𝄢 STEMS ONLY to shape them."
            )

    def _sync_eq_to_player(self) -> None:
        """Apply active 10-band EQ settings directly to the audio player in real-time."""
        try:
            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
            af = self._master_eq_settings().to_ffmpeg_af()
            player.set_audio_filter(af)
        except Exception:
            pass

    def _schedule_eq_render(self) -> None:
        """Apply EQ to active playback in real time and debounce background audio re-rendering."""
        self._sync_eq_to_player()

        if self.eq_target != "master" or self.active_stream != "ENH":
            return

        if self._eq_debounce_timer is not None:
            self._eq_debounce_timer.cancel()

        try:
            loop = asyncio.get_running_loop()
            self._eq_debounce_timer = loop.call_later(0.35, self._trigger_enhancement_pregeneration)
        except RuntimeError:
            self._trigger_enhancement_pregeneration()

    def _trigger_enhancement_pregeneration(self) -> None:
        """Asynchronously pre-generate the enhanced derivative."""
        src = self.path_mp3
        if not src or not src.exists():
            return

        # Cancel any previous in-flight render worker so rapid clicks are never dropped
        for w in list(self.workers):
            if w.name in ("render-stream-enh", "warm-mode-cache"):
                w.cancel()

        preset = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
        self._is_generating_enh = True
        self.run_worker(
            self._async_render_enh(src, preset, generation=self.track_generation),
            name="render-stream-enh",
        )

    async def _async_render_enh(
        self, src: Path, preset, *, generation: int | None = None
    ) -> None:
        if generation is None:
            generation = self.track_generation
        preset = self._effective_master_preset(preset)
        try:
            mode_tag = "neural" if self.neural_enabled else "eco"
            eq_tag = self._get_eq_cache_tag()
            cache_dest = self.audition_cache_dir / f"{src.stem}_{preset.id}_{mode_tag}{eq_tag}.mp3"
            out_path = await asyncio.to_thread(
                self.exporter.export_enhanced_derivative,
                input_path=src,
                preset=preset,
                output_path=cache_dest,
                cutoff_hz=self.cutoff_hz,
                eq_settings=self._master_eq_settings(),
                extra_tags=self._genre_extra_tags(),
            )
            if self._is_current_track(src, generation) and self.selected_preset_id == preset.id:
                self.path_enh = out_path

            if self._is_current_track(src, generation):
                self._is_generating_enh = False

            # If user has ENH active and is still on this preset, immediately switch playback!
            if (
                self._is_current_track(src, generation)
                and self.active_stream == "ENH"
                and self.selected_preset_id == preset.id
            ):
                self._route_to_player(
                    out_path,
                    title=f"[ENH] Restored ({preset.name})",
                    is_enhanced=True,
                    preset_name=preset.name,
                )
                self.query_one("#wb-status", Label).update(
                    f"Auditioning [ENH]: Restored ({preset.name})"
                )
            if self._is_current_track(src, generation):
                self._update_inspector()

                # Pre-warm remaining presets of the active mode in the background
                self.run_worker(
                    self._async_warm_remaining_presets(src), name="warm-mode-cache"
                )
        except asyncio.CancelledError:
            if self._is_current_track(src, generation):
                self._is_generating_enh = False
        except Exception as exc:
            if not self._is_current_track(src, generation):
                return
            self._is_generating_enh = False
            try:
                self.query_one("#wb-status", Label).update(f"Enhance failed: {exc}")
            except Exception:
                pass
        finally:
            from harvester.util.memory import purge_neural_vram

            purge_neural_vram()

    async def _async_warm_remaining_presets(self, src: Path) -> None:
        """Pre-render remaining presets of the active mode so subsequent clicks
        are instantaneous.
        """
        if self.neural_enabled:
            # Prevent background memory spikes from heavy neural models; render on demand
            return

        active_opts = ECO_PRESET_OPTIONS
        mode_tag = "eco"
        eq_tag = self._get_eq_cache_tag()
        for _, pid in active_opts:
            if pid == self.selected_preset_id:
                continue
            cache_dest = self.audition_cache_dir / f"{src.stem}_{pid}_{mode_tag}{eq_tag}.mp3"
            if not cache_dest.exists():
                p = PRESETS.get(pid)
                if p:
                    eff_preset = self._effective_master_preset(p)
                    try:
                        # Cooperatively yield to event loop so TUI animations & inputs never hitch
                        await asyncio.sleep(0.05)
                        await asyncio.to_thread(
                            self.exporter.export_enhanced_derivative,
                            input_path=src,
                            preset=eff_preset,
                            output_path=cache_dest,
                            cutoff_hz=self.cutoff_hz,
                            eq_settings=self._master_eq_settings(),
                            extra_tags=self._genre_extra_tags(),
                        )
                    except Exception:
                        pass

    def _route_to_player(
        self,
        audio_path: Path,
        title: str,
        is_enhanced: bool = False,
        preset_name: str = "",
    ) -> None:
        """Route audio stream to player with zero-gap playhead preservation."""
        try:
            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
            player.set_audio_filter(self._master_eq_settings().to_ffmpeg_af())
            player.switch_stream(
                audio_path,
                title=title,
                cutoff_hz=self.cutoff_hz,
                is_enhanced=is_enhanced,
                preset_name=preset_name,
            )
        except Exception:
            pass

        # Update workbench visualizer
        try:
            for vis in self.query(AudioVisualizer):
                vis.set_cutoff(self.cutoff_hz)
                vis.play()
                self.run_worker(asyncio.to_thread(vis.load_audio_frames, audio_path), name="vis-load")
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "wb-preset-select" and event.value is not None:
            for worker in self.workers:
                if worker.name in ("render-stream-enh", "warm-mode-cache", "vis-load"):
                    worker.cancel()
            self.selected_preset_id = str(event.value)
            self._update_inspector()

            # If audition file for this preset is already cached, reuse it instantly!
            if self.path_mp3:
                mode_tag = "neural" if self.neural_enabled else "eco"
                eq_tag = self._get_eq_cache_tag()
                cache_name = (
                    f"{self.path_mp3.stem}_{self.selected_preset_id}_{mode_tag}{eq_tag}.mp3"
                )
                cached_audition = self.audition_cache_dir / cache_name
                if cached_audition.exists():
                    self.path_enh = cached_audition
                    if self.active_stream == "ENH":
                        preset = PRESETS.get(self.selected_preset_id)
                        p_name = preset.name if preset else "Enhanced"
                        self._route_to_player(
                            self.path_enh,
                            title=f"[ENH] Restored ({p_name})",
                            is_enhanced=True,
                            preset_name=p_name,
                        )
                        self.query_one("#wb-status", Label).update(
                            f"Auditioning [ENH]: Restored ({p_name})"
                        )
                    return

            # Keep playing current audio seamlessly while synthesizing in background
            preset = PRESETS.get(self.selected_preset_id)
            p_name = preset.name if preset else "Enhanced"
            self.query_one("#wb-status", Label).update(
                f"Synthesizing '{p_name}'... (current audio continues)"
            )
            self._trigger_enhancement_pregeneration()
        elif event.select.id == "wb-genre-select" and isinstance(event.value, str):
            if event.value == "mix":
                if self.genre_mode != "mix":
                    self._open_genre_mix()
                return
            if event.value == self.genre_mode:
                return
            self.genre_mode = event.value
            self._apply_genre_mode()
        elif event.select.id == "wb-genre-intensity" and isinstance(event.value, str):
            if event.value == self.genre_intensity:
                return
            self.genre_intensity = event.value
            self._apply_genre_mode()
        elif event.select.id == "wb-eq-target-select" and event.value is not None:
            self._set_eq_target(str(event.value))
        elif event.select.id == "wb-eq-preset-select" and isinstance(event.value, str):
            preset_name = event.value
            if self.eq_settings.apply_preset(preset_name, eq_bank(self.eq_target)):
                self._update_eq_ui()
                self._schedule_eq_render()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id in ("btn-stream-mp3", "btn-stream-a", "btn-stream-b"):
            self.set_active_stream("MP3")
        elif btn_id in ("btn-stream-enh", "btn-stream-c"):
            self.set_active_stream("ENH")
        elif btn_id == "wb-btn-export":
            self._export_derivative()
        elif btn_id == "wb-btn-export-menu":
            self._toggle_export_dropdown()
        elif btn_id in (
            "wb-export-choose-enh",
            "wb-export-choose-wav",
            "wb-export-choose-flac",
            "wb-export-choose-voc",
            "wb-export-choose-inst",
        ):
            mode_map = {
                "wb-export-choose-enh": "ENH",
                "wb-export-choose-wav": "ENH_WAV",
                "wb-export-choose-flac": "ENH_FLAC",
                "wb-export-choose-voc": "VOC",
                "wb-export-choose-inst": "INST",
            }
            self._set_export_mode(mode_map[btn_id])
            self._toggle_export_dropdown(force_close=True)
            self._export_derivative()
        elif btn_id == "wb-export-choose-close":
            self._toggle_export_dropdown(force_close=True)
        elif btn_id == "wb-btn-credits":
            self._start_credits_lookup()

        elif btn_id.startswith("wb-eq-up-"):
            freq = int(btn_id.replace("wb-eq-up-", ""))
            curr = self.eq_settings.bands.get(freq, 0.0)
            self.eq_settings.set_band(freq, min(12.0, curr + 1.0))
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id.startswith("wb-eq-dn-"):
            freq = int(btn_id.replace("wb-eq-dn-", ""))
            curr = self.eq_settings.bands.get(freq, 0.0)
            self.eq_settings.set_band(freq, max(-12.0, curr - 1.0))
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id == "wb-btn-eq-reset":
            self.eq_settings.reset_flat()
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id == "wb-btn-eq-toggle":
            self.eq_settings.enabled = not self.eq_settings.enabled
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id == "wb-btn-eq-hpf":
            self.eq_settings.hpf_30hz = not self.eq_settings.hpf_30hz
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id == "wb-btn-eq-air":
            curr_16k = self.eq_settings.bands.get(16000, 0.0)
            self.eq_settings.set_band(16000, min(12.0, curr_16k + 3.0))
            self._update_eq_ui()
            self._schedule_eq_render()
        elif btn_id == "wb-btn-eq-trim":
            trims = [0.0, -1.0, -2.0, -3.0, 1.0]
            curr_trim = self.eq_settings.output_trim_db
            next_idx = (trims.index(curr_trim) + 1) % len(trims) if curr_trim in trims else 0
            self.eq_settings.output_trim_db = trims[next_idx]
            self._update_eq_ui()
            self._schedule_eq_render()
    def open_track_info(self) -> None:
        """Open the Track Info / upkeep modal (key: i)."""
        self.app.push_screen(
            TrackInfoScreen(self._track_info_rows(), hosted_available=self._hosted_available()),
            self._track_info_done,
        )

    def open_diagnostics(self) -> None:
        """Open the diagnostics modal (key: d)."""
        self._open_diagnostics()

    def _track_info_done(self, action: str | None) -> None:
        if not action:
            return
        if action == "tags":
            self._rerun_tags()
        elif action == "speakers":
            self._start_diarization()
        elif action == "credits":
            self._start_credits_lookup()
        elif action == "models":
            self.trigger_models_download()
        elif action == "diagnostics":
            self._open_diagnostics()

    def _track_info_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        job = self.current_job
        if job is not None:
            rows.append(("Track", job.display_name))
        elif self.path_mp3 is not None:
            rows.append(("Track", self.path_mp3.name))
        if self.path_mp3 is not None:
            rows.append(("Source", self.path_mp3.name))
        verdict = f"{self.cutoff_hz / 1000.0:.1f} kHz"
        if job is not None and job.spectral is not None:
            verdict += f" · {job.spectral.verdict.value.upper()}"
        rows.append(("Cutoff / verdict", verdict))
        credits = self.recording_credits
        if credits is not None and not credits.empty:
            rows.append(("Credits", credits.summary()))
        else:
            rows.append(("Credits", "not looked up"))
        rows.append(
            ("Voices", str(self.measured_speakers) if self.measured_speakers else "not measured")
        )
        rows.append(("Tags", self._cached_tags_summary()))
        rows.append(("Last repair", self._repair_result_notes()))
        rows.append(("Models", self._model_cache_summary()))
        return rows

    def _cached_tags_summary(self) -> str:
        if self.path_mp3 is None:
            return "—"
        try:
            from harvester.analysis.enhancement.stem_cache import read_stage_meta
            from harvester.analysis.enhancement.stem_separator import stem_dir_for

            meta = read_stage_meta(stem_dir_for(self.path_mp3), "tags")
            labels = [str(label) for label in (meta or {}).get("labels") or []]
            return ", ".join(labels) if labels else "none yet (run REFRESH TAGS)"
        except Exception:
            return "—"

    def _repair_result_notes(self) -> str:
        result = self._repair_result
        if result is None:
            return "none yet"
        parts = [
            label
            for label, attr in (("master", "master"), ("vocals", "vocals"), ("instrumental", "inst"))
            if getattr(result, attr, None) is not None
        ]
        if not parts:
            return "none yet"
        text = " + ".join(parts)
        worst = getattr(result, "residual_worst_db", None)
        if worst is not None:
            text += f" · residual {worst:.1f} dB"
        return text

    def _model_cache_summary(self) -> str:
        try:
            from harvester.services.model_manager import SUPPORTED_MODELS, ModelManager

            manager = ModelManager()
            cached = sum(1 for name in SUPPORTED_MODELS if manager.is_cached(name))
            return f"{cached}/{len(SUPPORTED_MODELS)} cached"
        except Exception:
            return "—"

    # ------------------------------------------------------------------
    # Guided repair page (docs/01 D35)
    # ------------------------------------------------------------------

    def _repair_panel(self) -> RepairPanel:
        return self.query_one(RepairPanel)

    def _neural_engine_status(self) -> tuple[str, bool]:
        """What the repair engine will actually run: neural models or eco fallback."""
        import importlib.util

        from harvester.services.model_manager import ModelManager

        deps = importlib.util.find_spec("transformers") is not None and (
            importlib.util.find_spec("demucs") is not None
        )
        manager = ModelManager()
        models = manager.is_cached("bs_roformer") and manager.is_cached("hdemucs")
        if deps and models:
            return ("ENGINE: NEURAL AI · BS-RoFormer + HDEMUCS", True)
        if not deps and not models:
            return ("ENGINE: ECO DSP · neural models not installed (Track Info → MODELS)", False)
        if not deps:
            return (
                "ENGINE: ECO DSP · transformers/demucs missing (uv sync --extra restore)",
                False,
            )
        return (
            "ENGINE: ECO DSP · BS-RoFormer/HDEMUCS not cached (Track Info → MODELS)",
            False,
        )

    def on_repair_panel_rerun_requested(self, event: RepairPanel.RerunRequested) -> None:
        event.stop()
        if self.path_mp3 is None:
            self.notify("Load a track first.", severity="warning")
            return
        self._start_repair_detection(force=True)

    def _start_repair_detection(self, *, force: bool = False) -> None:
        """Point the repair panel at the current track and run the detector once."""
        panel = self._repair_panel()
        stems_ready = bool(self.path_voc and self.path_inst)
        panel.set_track(self.path_mp3, self.cutoff_hz, stems_ready)
        panel.set_hosted_available(self._hosted_available())
        status, neural = self._neural_engine_status()
        panel.set_engine_status(status, neural=neural)
        if force:
            panel.detection = None
            panel.plan = None
            panel.result = None
            panel.error = None
            self._repair_result = None
        if self.path_mp3 is None or panel.detection is not None or panel.result is not None:
            return
        self.run_worker(
            self._async_repair_detection(self.path_mp3, self.track_generation),
            name="repair-detect",
        )

    async def _async_repair_detection(self, source: Path, generation: int) -> None:
        try:
            import soundfile as sf

            from harvester.analysis.enhancement.repair_plan import plan_from_detection

            def _load_and_analyze() -> AcousticAnalysisResult:
                data, sr = sf.read(str(source), dtype="float32", always_2d=True)
                return analyze_track_acoustics(data.T, sr=int(sr))

            result = await asyncio.to_thread(_load_and_analyze)
        except Exception as exc:
            logger.exception("Repair detection failed: %s", exc)
            if self._is_current_track(source, generation):
                self._repair_panel().set_error(str(exc))
            return
        if not self._is_current_track(source, generation):
            return
        self._repair_panel().set_detection(result, plan_from_detection(result))
        with contextlib.suppress(Exception):
            self.query_one("#wb-status", Label).update(f"Repair: {result.summary}")

    def on_repair_panel_separate_requested(self, event: RepairPanel.SeparateRequested) -> None:
        event.stop()
        if self.path_mp3 is None:
            self.notify("Load a track first.", severity="warning")
            return
        self.run_worker(
            self._async_repair_run(self.path_mp3, event.plan, self.track_generation),
            name="repair-run",
        )

    def on_repair_panel_apply_requested(self, event: RepairPanel.ApplyRequested) -> None:
        event.stop()
        if self.path_mp3 is None:
            self.notify("Load a track first.", severity="warning")
            return
        if getattr(event.plan, "engine", "local") == "hosted":
            if not self._hosted_available():
                self.notify(
                    "Hosted MVSEP needs a key — add MVSEP_API_KEY to .env or pick Local.",
                    severity="warning",
                )
                return
            self._pending_repair_plan = event.plan
            self._start_hosted_separation()
            return
        self.run_worker(
            self._async_repair_run(self.path_mp3, event.plan, self.track_generation),
            name="repair-run",
        )

    def _hosted_available(self) -> bool:
        try:
            from harvester.services.mvsep import MvsepClient

            return bool(MvsepClient().available)
        except Exception:
            return False

    async def _async_repair_run(
        self, source: Path, plan: Any, generation: int, separate: Any = None
    ) -> None:
        from harvester.services.repair import execute_repair

        panel = self._repair_panel()
        pb: ProgressBar | None = None
        try:
            pb = self.query_one("#wb-stem-progress", ProgressBar)
            pb.styles.display = "block"
            pb.progress = 0.0
        except Exception:
            pb = None

        def on_progress(pct: float, step: str) -> None:
            def _ui() -> None:
                try:
                    if self._is_current_track(source, generation):
                        if pb is not None:
                            pb.progress = pct
                        self.query_one("#wb-status", Label).update(f"Repair [{int(pct)}%]: {step}")
                        panel.set_progress(f"Working… {int(pct)}% — {step}")
                except Exception:
                    pass

            self.app.call_from_thread(_ui)

        out_dir = self.repair_work_dir(source)
        try:
            result = await asyncio.to_thread(
                execute_repair,
                source,
                plan,
                output_dir=out_dir,
                cutoff_hz=self.cutoff_hz,
                separate=separate,
                eq_by_target={
                    **self.eq_settings_by_target,
                    "master": self._master_eq_settings(),
                },
                master_preset=self._effective_master_preset(
                    PRESETS.get(plan.enhance_preset_id) or PRESETS["fast_balanced"]
                ),
                extra_tags=self._genre_extra_tags(),
                progress=on_progress,
            )
        except Exception as exc:
            logger.exception("Repair run failed: %s", exc)
            if self._is_current_track(source, generation):
                self.notify(f"Repair failed: {exc}", severity="error")
                panel.set_progress(f"Repair failed: {exc}")
            return
        finally:
            if pb is not None:
                pb.styles.display = "none"

        if not self._is_current_track(source, generation):
            return
        if result.vocals is not None:
            self.path_voc = result.vocals
        if result.inst is not None:
            self.path_inst = result.inst
        self._repair_result = result
        panel.set_stems_ready(bool(self.path_voc and self.path_inst))
        panel.show_result(result)
        self.notify("Repair complete — preview and export from the REPAIR page.", timeout=6.0)

    def repair_work_dir(self, source: Path) -> Path:
        """Session directory where repair deliverables are rendered before export."""
        return self.audition_cache_dir / "repairs" / source.stem

    def on_repair_panel_preview_requested(self, event: RepairPanel.PreviewRequested) -> None:
        event.stop()
        result = self._repair_panel().result
        if result is None:
            return
        candidates = {
            "master": (getattr(result, "master", None), "REPAIRED MASTER"),
            "vocals": (getattr(result, "vocals", None), "CLEAN VOCALS"),
            "inst": (getattr(result, "inst", None), "CLEAN INSTRUMENTAL"),
        }
        path, title = candidates.get(event.output, (None, ""))
        if path is not None and Path(path).exists():
            self._route_to_player(Path(path), title)

    def on_repair_panel_export_requested(self, event: RepairPanel.ExportRequested) -> None:
        event.stop()
        self.run_worker(self._async_export_repair(), name="repair-export")

    async def _async_export_repair(self) -> None:
        import os
        import shutil
        import uuid

        from harvester.config import load_config

        result = self._repair_panel().result
        source = self.path_mp3
        if result is None or source is None:
            self.notify("Nothing to export yet.", severity="warning")
            return
        out_dir = Path(load_config().general.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        deliverables = (
            (getattr(result, "master", None), f"{source.stem}.repaired.mp3"),
            (getattr(result, "vocals", None), f"{source.stem}_vocals.wav"),
            (getattr(result, "inst", None), f"{source.stem}_instrumental.wav"),
        )
        written = 0
        for src, name in deliverables:
            if src is None or not Path(src).exists():
                continue
            destination = out_dir / name
            temp = destination.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}{destination.suffix}")
            await asyncio.to_thread(shutil.copy2, src, temp)
            os.replace(temp, destination)
            written += 1
        if written:
            self.notify(f"Exported {written} repaired file(s) to {out_dir}.", timeout=6.0)
        else:
            self.notify("No repair outputs available to export.", severity="warning")

    def on_repair_panel_suggest_requested(self, event: RepairPanel.SuggestRequested) -> None:
        event.stop()
        from harvester.analysis.enhancement.repair_plan import SYMPTOM_BY_KEY, TARGET_VOCALS

        spec = SYMPTOM_BY_KEY.get(event.symptom)
        if spec is None or spec.suggestion is None:
            return
        target, source_name, issue = spec.suggestion
        stem = self.path_voc if target == TARGET_VOCALS else self.path_inst
        if stem is None or not Path(stem).exists():
            self.notify(
                "Run a fix first (or build stems) so the analysis can find the spots.",
                severity="warning",
            )
            return
        self.run_worker(
            self._async_suggest_ranges(event.symptom, Path(stem), source_name, issue),
            name="repair-suggest",
        )

    async def _async_suggest_ranges(
        self, symptom: str, stem: Path, source_name: str, issue: str
    ) -> None:
        import soundfile as sf

        from harvester.analysis.enhancement.segment_analysis import suggest_ranges

        try:
            info = await asyncio.to_thread(sf.info, str(stem))
            duration = info.frames / float(info.samplerate) if info.samplerate else 0.0
            ranges = await asyncio.to_thread(
                suggest_ranges,
                stem,
                issue,
                source_name,
                duration_s=duration,
                sample_rate=int(info.samplerate),
            )
        except Exception as exc:
            logger.exception("Range suggestion failed: %s", exc)
            return
        await self._repair_panel().set_suggested_ranges(symptom, ranges)

    # ------------------------------------------------------------------
    # Processing preset + lane provenance (docs/13)
    # ------------------------------------------------------------------
    async def _run_tagging_pass(
        self,
        source_path: Path,
        stem_dir: Path,
        *,
        generation: int | None = None,
    ) -> None:
        """NEURAL FULL: CLAP instrument/vocal tags → ``tags.json`` → plan rows.

        Advisory by design (docs/13 D25): tags only add provenance rows to the
        lane plan — never verdicts, never file metadata. A missing model or
        dependency leaves the track untagged instead of failing the run.
        """
        if generation is None:
            generation = self.track_generation
        from harvester.analysis.enhancement.tags import ClapTagger

        def _on_progress(pct: float, step: str) -> None:
            def _ui() -> None:
                with contextlib.suppress(Exception):
                    if self._is_current_track(source_path, generation):
                        self.query_one("#wb-status", Label).update(
                            f"Tags [{int(pct)}%]: {step}"
                        )

            self.app.call_from_thread(_ui)

        processing = getattr(getattr(self.app, "config", None), "processing", None)
        threshold = getattr(processing, "tag_threshold", None)
        tagger = ClapTagger(threshold=float(threshold)) if threshold else ClapTagger()
        try:
            result = await asyncio.to_thread(
                tagger.tag_and_store, source_path, stem_dir, progress_callback=_on_progress
            )
        except Exception as exc:
            logger.info("tagging pass skipped: %s", exc)
            return
        with contextlib.suppress(Exception):
            if not self._is_current_track(source_path, generation):
                return
            if result is None:
                self._update_status("Tags unavailable (CLAP model not cached).")
            else:
                from harvester.analysis.enhancement.stem_cache import write_stage_meta

                write_stage_meta(
                    stem_dir,
                    "tags",
                    {
                        "labels": list(result.labels),
                        "scores": {k: float(v) for k, v in result.score_map.items()},
                        "windows": int(result.windows),
                        "model": str(result.model),
                        "source_size": source_path.stat().st_size,
                    },
                )
                self._update_status(result.describe())

    def _update_status(self, text: str) -> None:
        """Status-line helper used by background track work."""
        with contextlib.suppress(Exception):
            self.query_one("#wb-task-status", Label).update(text)

    def _open_diagnostics(self) -> None:
        """🔍 DIAG — show a read-only environment/credentials overview (docs/14 M3)."""
        app = self.app
        if app is None:
            return
        from harvester.ui.diagnostics import DiagnosticsScreen

        app.push_screen(DiagnosticsScreen(config=getattr(app, "config", None)))

    def _rerun_tags(self) -> None:
        """Re-run the CLAP pass for the loaded track (Track Info action)."""
        source = self.path_mp3
        if source is None:
            return
        from harvester.analysis.enhancement.stem_separator import stem_dir_for

        stem_dir = stem_dir_for(source)
        generation = self.track_generation
        self._update_status("Re-running CLAP tags…")

        async def _rerun() -> None:
            await self._run_tagging_pass(source, stem_dir, generation=generation)

        self.run_worker(_rerun(), name="retag-pass")

    def _start_hosted_separation(self) -> None:
        """☁ HOSTED SEPARATE — the opt-in cloud run (docs/13 D26, docs/14 M3).

        Nothing is uploaded unless the confirmation screen's upload button is
        pressed: the preset never touches the network, and a missing key is
        reported instead of queued.
        """
        if self._hosted_task_running:
            self._update_status("Hosted separation is already running for this track…")
            return
        source = self.path_mp3
        if source is None:
            return
        # Capture the track this dialog belongs to (docs/14 M6 review): if the
        # user switches tracks while the modal is open, the confirm must NOT
        # upload the new track's audio under the old dialog.
        self._hosted_pending = (source, self.track_generation)
        app = self.app
        if app is None:
            return
        processing = getattr(getattr(app, "config", None), "processing", None)
        sep_type = str(
            getattr(processing, "hosted_sep_type", DEFAULT_SEP_TYPE) or DEFAULT_SEP_TYPE
        )
        max_seconds = float(getattr(processing, "hosted_max_seconds", 0.0) or 0.0)
        from harvester.ui.hosted_screen import HostedSeparationScreen

        app.push_screen(
            HostedSeparationScreen(source, sep_type, max_seconds=max_seconds),
            self._hosted_screen_done,
        )

    def _hosted_screen_done(self, choice: str | None) -> None:
        """Callback from HostedSeparationScreen: None = cancelled."""
        if not choice:
            self._pending_repair_plan = None
            return
        pending = self._hosted_pending
        self._hosted_pending = None
        if pending is not None and not self._is_current_track(*pending):
            self._update_status(
                "Hosted run skipped — the track changed while the dialog was open."
            )
            return
        self._launch_hosted_run(choice)

    def _launch_hosted_run(self, sep_type: str) -> None:
        """Start the MVSEP job with an explicitly chosen sep_type."""
        if self._hosted_task_running:
            self._update_status("Hosted separation is already running for this track…")
            return
        source = self.path_mp3
        if source is None:
            return
        from harvester.analysis.enhancement.stem_separator import stem_dir_for

        stem_dir = stem_dir_for(source)
        mode = "ensemble" if self.neural_enabled else "eco"
        from harvester.services.mvsep import SEP_TYPE_LABELS

        token = self._begin_operation(Operation.HOSTED_SEPARATION)
        if token is None:
            return
        processing = getattr(getattr(self.app, "config", None), "processing", None)
        max_seconds = float(getattr(processing, "hosted_max_seconds", 0.0) or 0.0)
        self._hosted_task_running = True
        scope = f"up to {max_seconds:.0f}s" if max_seconds > 0 else "the whole track"
        self._update_status(
            f"☁ Hosted separation: uploading {scope} to MVSEP "
            f"({SEP_TYPE_LABELS.get(sep_type, sep_type)})…"
        )
        self.run_worker(
            self._async_hosted_separation(
                source, stem_dir, mode, sep_type, max_seconds, token
            ),
            name="hosted-separation",
        )

    async def _async_hosted_separation(
        self,
        source: Path,
        stem_dir: Path,
        mode: str,
        sep_type: str,
        max_seconds: float,
        token: OperationToken,
    ) -> None:
        """Upload → poll → download hosted stems, then rebuild the lane grid."""
        def _status(text: str) -> None:
            if self._is_current_track(source, token.generation):
                self._update_status(text)

        try:
            from harvester.services.mvsep import MvsepClient

            client = MvsepClient()
            if not client.available:
                _status(
                    "Hosted separation needs an MVSEP key — add MVSEP_API_KEY to .env."
                )
                return

            def _on_progress(pct: float, step: str) -> None:
                def _ui() -> None:
                    _status(f"☁ Hosted [{int(pct)}%]: {step}")

                self.app.call_from_thread(_ui)

            try:
                result = await client.separate(
                    source,
                    stem_dir,
                    output_prefix=f"{source.stem}_{mode}",
                    sep_type=sep_type,
                    max_seconds=max_seconds,
                    progress=_on_progress,
                )
            finally:
                await client.close()
        except Exception as exc:
            logger.info("hosted separation failed: %s", exc)
            _status(f"Hosted separation failed: {exc} — press ☁ HOSTED SEPARATE to retry.")
            return
        finally:
            if self._is_current_operation(token):
                self._hosted_task_running = False
            self._finish_operation(token)

        if not self._is_current_track(source, token.generation):
            return
        if not result.stems:
            _status(result.message or "Hosted separation produced no usable stems.")
            return

        note = result.describe()
        if result.skipped:
            note += f" · skipped {', '.join(result.skipped)}"
        _status(note)
        try:
            from harvester.analysis.enhancement.stem_cache import write_stage_meta

            write_stage_meta(
                stem_dir,
                "hosted_run",
                {
                    "sep_type": str(result.sep_type),
                    "algorithm": str(result.algorithm),
                    "lane_keys": list(result.lane_keys),
                    "waited_s": round(float(result.waited_s), 1),
                    "job_hash": str(result.job_hash),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.info("hosted run meta not persisted: %s", exc)
        plan = self._pending_repair_plan
        self._pending_repair_plan = None
        if plan is not None and self._is_current_track(source, token.generation):
            stems = self._hosted_repair_stems(stem_dir, source)
            if stems is None:
                self.query_one("#wb-status", Label).update(
                    "Hosted run produced no vocals lane to repair — use Local engine."
                )
                self.notify(
                    "Hosted run had no vocals lane; repair skipped.", severity="warning"
                )
            else:
                self.run_worker(
                    self._async_repair_run(
                        source,
                        plan,
                        token.generation,
                        separate=lambda src, p, sd, progress, stems=stems: stems,
                    ),
                    name="repair-run",
                )

    def _hosted_repair_stems(self, stem_dir: Path, source: Path) -> tuple[Path, Path] | None:
        """Derive a vocals/instrumental pair from the downloaded hosted lanes."""
        from harvester.analysis.enhancement.stem_separator import (
            apply_inversion_subtraction,
            load_audio_numpy,
            save_audio_numpy,
        )
        from harvester.processing import HOSTED_RAW_TOKEN

        try:
            raws = [
                path
                for path in sorted(stem_dir.glob(f"*{HOSTED_RAW_TOKEN}*.wav"))
                if path.stat().st_size > 44
            ]
            vocals_parts = [path for path in raws if "vocal" in path.name.lower()]
            inst_parts = [
                path
                for path in raws
                if "instrument" in path.name.lower() and "back" not in path.name.lower()
            ]
            if not vocals_parts:
                return None
            vocals_path = stem_dir / f"{source.stem}_hosted_repair_vocals.wav"
            if not (vocals_path.exists() and vocals_path.stat().st_size > 44):
                mixed = None
                sr = 44100
                for part in vocals_parts:
                    audio, sr = load_audio_numpy(part)
                    if mixed is None:
                        mixed = audio.astype("float32")
                    else:
                        width = min(mixed.shape[1], audio.shape[1])
                        mixed = mixed[:, :width] + audio[:, :width]
                save_audio_numpy(mixed, vocals_path, sr)
            if inst_parts:
                return vocals_path, inst_parts[0]
            inst_path = stem_dir / f"{source.stem}_hosted_repair_instrumental.wav"
            if not (inst_path.exists() and inst_path.stat().st_size > 44):
                original, sr = load_audio_numpy(source)
                vocals_audio, _ = load_audio_numpy(vocals_path)
                save_audio_numpy(
                    apply_inversion_subtraction(original, vocals_audio, sr), inst_path, sr
                )
            return vocals_path, inst_path
        except Exception as exc:
            logger.info("hosted repair stems unavailable: %s", exc)
            return None

    def _start_diarization(self) -> None:
        """👥 SPEAKERS — measure voices in the track (advisory, docs/13 D27)."""
        if self._diarize_task_running:
            self._update_status("Speaker measurement is already running…")
            return
        source = self.path_mp3
        if source is None:
            return
        audio = self.path_voc if self.path_voc and self.path_voc.exists() else source
        token = self._begin_operation(Operation.DIARIZATION)
        if token is None:
            return
        processing = getattr(getattr(self.app, "config", None), "processing", None)
        max_seconds = float(getattr(processing, "diarize_max_seconds", 0.0) or 0.0)
        self._diarize_task_running = True
        self._diarize_started = monotonic()
        self._update_status(
            f"👥 Measuring speakers in {audio.name} (pyannote, CPU — this takes a while)…"
        )
        if self._diarize_timer is not None:
            self._diarize_timer.stop()
        self._diarize_timer = self.set_interval(10.0, self._diarize_heartbeat)
        from harvester.analysis.enhancement.stem_separator import stem_dir_for

        self.run_worker(
            self._async_diarize(source, audio, max_seconds, token, stem_dir_for(source)),
            name="speaker-measure",
        )

    def _diarize_heartbeat(self) -> None:
        """Liveness tick: pyannote on CPU takes minutes, so show elapsed time."""
        if not self._diarize_task_running:
            if self._diarize_timer is not None:
                self._diarize_timer.stop()
                self._diarize_timer = None
            return
        elapsed = int(monotonic() - self._diarize_started)
        self._update_status(
            f"👥 Measuring speakers… {elapsed}s elapsed "
            "(pyannote on CPU — minutes are normal, it is still working)"
        )

    async def _async_diarize(
        self,
        source: Path,
        audio: Path,
        max_seconds: float,
        token: OperationToken,
        stem_dir: Path,
    ) -> None:
        """Diarize ``audio`` and fold the count into the plan (advisory).

        ``source`` is the loaded track (path_mp3) and is what the staleness
        guard keys on; ``audio`` may be the vocals stem, whose path never
        equals the track's (docs/14 M4).
        """
        def _status(text: str) -> None:
            if self._is_current_track(source, token.generation):
                self._update_status(text)

        try:
            from harvester.services.diarization import Diarizer, pyannote_available

            if not pyannote_available():
                _status(
                    "Speaker measurement needs the optional extra: "
                    "uv pip install -e '.[diarize]'"
                )
                return

            def _on_progress(pct: float, step: str) -> None:
                def _ui() -> None:
                    _status(f"👥 Speakers [{int(pct)}%]: {step}")

                self.app.call_from_thread(_ui)

            diarizer = getattr(self, "_diarizer", None)
            if diarizer is None:
                diarizer = Diarizer()
                self._diarizer = diarizer
            result = await asyncio.to_thread(
                diarizer.diarize, audio, max_seconds=max_seconds, progress=_on_progress
            )
        except Exception as exc:
            logger.info("speaker measurement failed: %s", exc)
            _status(f"Speaker measurement failed: {exc} — press 👥 SPEAKERS to retry.")
            return
        finally:
            if self._is_current_operation(token):
                self._diarize_task_running = False
                if self._diarize_timer is not None:
                    self._diarize_timer.stop()
                    self._diarize_timer = None
            self._finish_operation(token)

        if not self._is_current_track(source, token.generation):
            return

        self.measured_speakers = result.speaker_count
        try:
            from harvester.analysis.enhancement.stem_cache import (
                source_fingerprint,
                write_stage_meta,
            )

            write_stage_meta(
                stem_dir,
                "diarization",
                {
                    "speaker_count": int(result.speaker_count or 0),
                    "model": str(result.model),
                    "device": str(result.device),
                    "elapsed_s": round(float(result.elapsed_s), 1),
                    "speech_s": round(float(result.speech_s), 1),
                    "source_path": str(audio),
                    "source_size": audio.stat().st_size,
                    "source_fingerprint": source_fingerprint(audio),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.info("diarization meta not persisted: %s", exc)
        note = result.describe()
        credits = self.recording_credits
        credited = getattr(credits, "singer_count", None) if credits is not None else None
        if credited and result.speaker_count and credited != result.speaker_count:
            note += (
                f" · MusicBrainz credits say {credited} — credits stay authoritative"
            )
        _status(note)

    def _start_credits_lookup(self) -> None:
        """Fingerprint → AcoustID → MusicBrainz credits for the loaded track."""
        if self._credits_task_running:
            return
        target = self.path_mp3
        if target is None or not target.exists():
            with contextlib.suppress(Exception):
                self.query_one("#wb-status", Label).update(
                    "No active track loaded for a credits lookup."
                )
            return
        token = self._begin_operation(Operation.CREDITS)
        if token is None:
            return
        self._credits_task_running = True
        self.run_worker(
            self._async_fetch_credits(target, token), name="credits-lookup", exclusive=True
        )

    async def _async_fetch_credits(
        self, target: Path, token: OperationToken | None = None
    ) -> None:
        """Resolve documented instruments/vocalists and feed the lane plan."""
        if token is None:
            token = self._begin_operation(Operation.CREDITS)
            if token is None:
                return
        def _status(text: str) -> None:
            if self._is_current_track(target, token.generation):
                self._update_status(text)

        try:
            _status("Credits: fingerprinting the track…")
            from harvester.config import load_config
            from harvester.services.acoustid import AcoustidService
            from harvester.services.musicbrainz import CoverArtService

            app_cfg = getattr(self.app, "config", None) or load_config()
            acoustid = AcoustidService(app_cfg)
            try:
                meta = await acoustid.identify(target)
            finally:
                await acoustid.close()
            mbid = getattr(meta, "mb_recording_id", None) if meta else None
            if not self._is_current_track(target, token.generation):
                return
            if not mbid:
                _status(
                    "Credits: no MusicBrainz recording id (AcoustID miss) — "
                    "lanes stay as detected."
                )
                return
            mb = CoverArtService(app_cfg)
            try:
                credits = await mb.fetch_recording_credits(mbid)
            finally:
                await mb.close()
            if not self._is_current_track(target, token.generation):
                return
            self.recording_credits = credits
            text = credits.summary() if credits is not None else "credits unavailable"
            _status(f"CREDITS: {text}")
        except Exception as exc:
            logger.info("credits lookup failed: %s", exc)
            _status(f"Credits lookup failed: {exc} — press 🏷 CREDITS to retry.")
        finally:
            if self._is_current_operation(token):
                self._credits_task_running = False
            self._finish_operation(token)

    def trigger_models_download(self) -> None:
        """Check or download all AI model weights and show status for all 4 models."""
        import importlib
        import importlib.util

        from harvester.services.model_manager import ModelManager

        mm = ModelManager()

        # --- Stem separation model availability (self-managed) ---
        bsr_installed = importlib.util.find_spec("transformers") is not None
        bsr_cached = mm.is_cached("bs_roformer")
        bsr_ok = bsr_installed and bsr_cached
        if not bsr_installed:
            bsr_status = "⚠ Needs: pip install transformers"
        elif not bsr_cached:
            bsr_status = "⬇ Not downloaded"
        else:
            bsr_status = "✅ Cached & Ready"

        hdemucs_ok = importlib.util.find_spec("demucs") is not None
        hdemucs_status = "✅ Available" if hdemucs_ok else "⚠ Needs: pip install demucs"

        # --- All model cache status (FlashSR is a three-file pipeline) ---
        flashsr_parts = ("flashsr", "flashsr_ldm", "flashsr_vae")
        all_models = ("bs_roformer", "hdemucs", "dereverb", *flashsr_parts)
        missing = [m for m in all_models if not mm.is_cached(m)]
        dereverb_status = "✅ Cached & Ready" if mm.is_cached("dereverb") else "✅ DSP Engine"
        fsr_missing = [m for m in flashsr_parts if m in missing]
        fsr_status = "✅ Cached" if not fsr_missing else f"⬇ {len(fsr_missing)}/3 file(s) missing"

        status_summary = (
            f"AI Model Registry — "
            f"BS-RoFormer: {bsr_status}  |  "
            f"HDEMUCS: {hdemucs_status}  |  "
            f"DeReverb: {dereverb_status}  |  "
            f"FlashSR: {fsr_status}"
        )
        self.query_one("#wb-status", Label).update(status_summary)

        all_ready = bsr_ok and hdemucs_ok and not missing
        if all_ready:
            self.app.notify(
                f"All AI models ready:\n"
                f"• BS-RoFormer (Stem): {bsr_status}\n"
                f"• HDEMUCS (Stem): {hdemucs_status}\n"
                f"• De-Reverb (Acoustic): {dereverb_status}\n"
                f"• FlashSR (Enhance): ✅ Cached",
                title="OmniRip AI Models",
                timeout=6.0,
            )
            return

        install_demucs = not hdemucs_ok
        tasks_desc: list[str] = []
        if install_demucs:
            tasks_desc.append("Demucs stem engine")
        if missing:
            tasks_desc.append(f"AI weights ({', '.join(missing)})")

        self.app.notify(
            f"Setting up AI models: {', '.join(tasks_desc)}...",
            title="OmniRip AI Models",
            timeout=5.0,
        )
        self.run_worker(
            self._async_download_models(missing, install_demucs=install_demucs),
            name="download-models",
        )

    async def _async_download_models(self, models: list[str], install_demucs: bool = False) -> None:
        import importlib
        import subprocess
        import sys

        from harvester.services.model_manager import ModelManager

        mm = ModelManager()
        try:
            if install_demucs:
                self.query_one("#wb-status", Label).update(
                    "Installing Demucs neural stem engine..."
                )
                await asyncio.to_thread(
                    subprocess.run,
                    [sys.executable, "-m", "pip", "install", "demucs>=4.0.0"],
                    check=True,
                    capture_output=True,
                )
                importlib.invalidate_caches()

            for model_name in models:
                self.query_one("#wb-status", Label).update(
                    f"Downloading {model_name.upper()} AI weights..."
                )
                await asyncio.to_thread(mm.download_model, model_name)
            self.query_one("#wb-status", Label).update(
                "All neural models and weights configured successfully!"
            )
            self.app.notify(
                "Model download complete! All AI weights are cached and ready.",
                title="OmniRip Models Downloaded",
                timeout=5.0,
            )
            self._update_inspector()
        except Exception as exc:
            self.query_one("#wb-status", Label).update(f"Model download failed: {exc}")
            self.app.notify(
                f"Model download error: {exc}",
                title="Download Error",
                severity="error",
                timeout=5.0,
            )

    def _toggle_export_dropdown(self, force_close: bool = False) -> None:
        """Show or hide the export-type dropdown menu."""
        try:
            dd = self.query_one("#wb-export-dropdown", Horizontal)
            if force_close or dd.styles.display != "none":
                dd.styles.display = "none"
            else:
                dd.styles.display = "block"
        except Exception:
            pass

    def _set_export_mode(self, mode: str) -> None:
        """Update the export mode and reflect it in the main button label."""
        self._export_mode = mode
        labels = {
            "ENH": "⤓ SAVE ENHANCED",
            "ENH_WAV": "⤓ SAVE WAV",
            "ENH_FLAC": "⤓ SAVE FLAC",
            "VOC": "⤓ SAVE VOCALS",
            "INST": "⤓ SAVE INST",
        }
        try:
            self.query_one("#wb-btn-export", Button).label = labels.get(
                mode, "⤓ SAVE ENHANCED"
            )
        except Exception:
            pass

    def _export_derivative(self) -> None:
        src = self.path_mp3
        if not src or not src.exists():
            self.query_one("#wb-status", Label).update("No audio file available to download.")
            return

        preset = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
        if self._export_mode == "VOC":
            self.query_one("#wb-status", Label).update("Saving Isolated Vocals (Acapella)...")
        elif self._export_mode == "INST":
            self.query_one("#wb-status", Label).update("Saving Karaoke Instrumental...")
        else:
            self.query_one("#wb-status", Label).update(
                f"Downloading Enhanced MP3 with '{preset.name}'..."
            )
        try:
            pb = self.query_one("#wb-download-progress", ProgressBar)
            pb.styles.display = "block"
            pb.progress = 0.0
            pb.total = 100.0
        except Exception:
            pass
        self.run_worker(self._async_export(src, preset), name="export-derivative")

    async def _export_stem(
        self, mode: str, stem: Path, src: Path, out_dir: Path, pb: object
    ) -> None:
        """Atomically save one separated stem, baking its target EQ curve."""
        import os
        import uuid

        is_vocals = mode == "VOC"
        target = "vocals" if is_vocals else "instrumental"
        suffix = "vocals" if is_vocals else "instrumental"
        status_label = "Vocals (Acapella)" if is_vocals else "Instrumental (Karaoke)"
        short_label = "Acapella" if is_vocals else "Instrumental"
        target_dest = out_dir / f"{src.stem}_{suffix}.wav"
        temp_dest = target_dest.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.wav")
        await asyncio.to_thread(self._write_stem_with_eq, stem, temp_dest, target)
        os.replace(temp_dest, target_dest)
        if pb is not None:
            pb.progress = 100.0
        with contextlib.suppress(Exception):
            self.query_one("#wb-status", Label).update(
                f"Saved {status_label}: {target_dest.name}"
            )
        self.app.notify(f"Saved {short_label}: {target_dest.name}", title="OmniRip Stems")

    def _write_stem_with_eq(self, source: Path, destination: Path, target: str) -> None:
        """Copy a stem, baking that target's EQ curve when it is not flat."""
        import shutil

        settings = self.eq_settings_by_target.get(target)
        if settings is None or is_flat(settings):
            shutil.copy2(source, destination)
            return
        from harvester.analysis.enhancement.repair_ops import load_stereo, write_pcm32

        audio, sample_rate = load_stereo(source)
        equalized = apply_mastering_eq(audio, settings, sample_rate=sample_rate)
        write_pcm32(equalized, destination, sample_rate)

    async def _async_export(self, src: Path, preset) -> None:
        preset = self._effective_master_preset(preset)
        try:
            import os
            import shutil
            import uuid

            pb = None
            try:
                pb = self.query_one("#wb-download-progress", ProgressBar)
            except Exception:
                pass

            def update_progress(pct: float, step: str) -> None:
                def _ui() -> None:
                    try:
                        if pb:
                            pb.progress = pct
                        self.query_one("#wb-status", Label).update(
                            f"Downloading [{int(pct)}%]: {step}"
                        )
                    except Exception:
                        pass

                self.app.call_from_thread(_ui)

            # 1. Resolve target output directory
            app_cfg = getattr(self.app, "config", None)
            if self.current_job and self.current_job.output_path:
                out_dir = self.current_job.output_path.parent
            elif app_cfg and hasattr(app_cfg, "general") and app_cfg.general.output_dir:
                out_dir = Path(app_cfg.general.output_dir)
            else:
                from harvester.config import load_config

                out_dir = Path(load_config().general.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            # Handle isolated stem export based on user-selected export mode
            if self._export_mode in ("VOC", "INST"):
                stem = self.path_voc if self._export_mode == "VOC" else self.path_inst
                label = "vocals" if self._export_mode == "VOC" else "instrumental"
                if stem is None or not stem.exists():
                    with contextlib.suppress(Exception):
                        self.query_one("#wb-status", Label).update(
                            f"No separated {label} to export — run Repair → 𝄢 STEMS ONLY first."
                        )
                    self.app.notify(
                        f"No separated {label} to export.", severity="warning"
                    )
                    return
                await self._export_stem(self._export_mode, stem, src, out_dir, pb)
                return

            if self._export_mode in ("ENH_WAV", "ENH_FLAC"):
                fmt = "wav" if self._export_mode == "ENH_WAV" else "flac"
                target_dest = out_dir / f"{src.stem}.enhanced.{fmt}"
                temp_dest = target_dest.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.{fmt}")
                await asyncio.to_thread(
                    self.exporter.export_enhanced_lossless,
                    input_path=src,
                    preset=preset,
                    output_path=temp_dest,
                    cutoff_hz=self.cutoff_hz,
                    fmt=fmt,
                    progress_callback=update_progress,
                    eq_settings=self._master_eq_settings(),
                    extra_tags=self._genre_extra_tags(),
                )
                os.replace(temp_dest, target_dest)
                if pb:
                    pb.progress = 100.0
                self.query_one("#wb-status", Label).update(
                    f"Saved lossless master: {target_dest.name}"
                )
                self.app.notify(
                    f"Lossless master saved: {target_dest.name}",
                    title="OmniRip Lossless",
                    timeout=4.0,
                )
                return

            target_dest = out_dir / f"{src.stem}.enhanced.mp3"

            # 2. Check if already pre-rendered in audition cache for instant, lock-free download
            mode_tag = "neural" if self.neural_enabled else "eco"
            eq_tag = self._get_eq_cache_tag()
            cache_name = f"{src.stem}_{preset.id}_{mode_tag}{eq_tag}.mp3"
            cached_audition = self.audition_cache_dir / cache_name

            temp_dest = target_dest.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.mp3")

            if cached_audition.exists() and cached_audition.stat().st_size > 1024:
                # Instant atomic copy from warm audition cache with smooth progress bar
                if pb:
                    pb.progress = 25.0
                await asyncio.sleep(0.04)
                if pb:
                    pb.progress = 65.0
                await asyncio.to_thread(shutil.copy2, cached_audition, temp_dest)
                os.replace(temp_dest, target_dest)
                if pb:
                    pb.progress = 95.0
                await asyncio.sleep(0.04)
                out_path = target_dest
            else:
                # Render via isolated temp file to prevent locking conflicts during active playback
                if pb:
                    pb.progress = 10.0
                rendered_path = await asyncio.to_thread(
                    self.exporter.export_enhanced_derivative,
                    input_path=src,
                    preset=preset,
                    output_path=temp_dest,
                    cutoff_hz=self.cutoff_hz,
                    progress_callback=update_progress,
                    eq_settings=self._master_eq_settings(),
                    extra_tags=self._genre_extra_tags(),
                )
                if rendered_path != target_dest and temp_dest.exists():
                    os.replace(temp_dest, target_dest)
                out_path = target_dest

            self.path_enh = out_path
            if pb:
                pb.progress = 100.0
            self.query_one("#wb-status", Label).update(
                f"Downloaded: {out_path.name} · preset {preset.name} · "
                f"folder {out_dir}"
            )
            self.app.notify(
                f"Enhanced MP3 saved: {out_path.name}",
                title="OmniRip Enhanced Download",
                timeout=4.0,
            )
            if self.on_exported:
                self.on_exported(out_path)

            await asyncio.sleep(1.2)
            if pb:
                pb.styles.display = "none"
        except Exception as exc:
            self.query_one("#wb-status", Label).update(f"Download error: {exc}")
            self.app.notify(f"Download error: {exc}", severity="error")
            try:
                self.query_one("#wb-download-progress", ProgressBar).styles.display = "none"
            except Exception:
                pass
        finally:
            from harvester.util.memory import purge_neural_vram

            purge_neural_vram()
