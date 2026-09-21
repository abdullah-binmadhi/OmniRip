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
from typing import TYPE_CHECKING, Any, Literal

import platformdirs
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.visual import VisualType
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Label, ProgressBar, Select, SelectionList

from harvester.analysis.enhancement.acoustic_detector import (
    AcousticAnalysisResult,
    analyze_track_acoustics,
)
from harvester.analysis.enhancement.eq import (
    EQ_FREQUENCIES,
    EQ_PRESETS,
    MasteringEQSettings,
)
from harvester.analysis.enhancement.layer_editor import EditPlan
from harvester.analysis.enhancement.presets import PRESETS
from harvester.analysis.enhancement.stem_separator import (
    INST_REMEDIATIONS,
    VOCAL_REMEDIATIONS,
)
from harvester.models import TrackJob
from harvester.processing import (
    DEFAULT_PRESET,
    DEFAULT_SEP_TYPE,
    degraded,
    engine_note,
    get_preset,
    next_preset,
)
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.services.enhancement.preview import PreviewManager
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


class DefectChecklist(Vertical):
    """Directly tickable defect checklist with clean spacing and no vertical scrolling."""

    class SelectedChanged(Message):
        """Emitted when any checkbox option changes state."""

        def __init__(self, checklist: DefectChecklist) -> None:
            super().__init__()
            self.checklist = checklist
            self.selection_list = checklist  # For compatibility

    def __init__(self, items: list[tuple[str, str, bool]], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._items = items
        self._checkboxes: dict[str, Checkbox] = {}

    def compose(self) -> ComposeResult:
        for label, key, default_val in self._items:
            cb = Checkbox(label, value=default_val, id=f"chk-{self.id or 'list'}-{key}", classes="wb-defect-checkbox")
            self._checkboxes[key] = cb
            yield cb

    @property
    def selected(self) -> list[str]:
        return [k for k, cb in self._checkboxes.items() if cb.value]

    def select(self, key: str) -> None:
        if key in self._checkboxes:
            self._checkboxes[key].value = True

    def deselect(self, key: str) -> None:
        if key in self._checkboxes:
            self._checkboxes[key].value = False

    def select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.value = True

    def deselect_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.value = False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.stop()
        self.post_message(self.SelectedChanged(self))


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
    .wb-defect-checkbox {
        height: auto;
        background: transparent;
    }
    .wb-defect-checkbox:focus-within {
        background: transparent;
        color: $text;
    }
    .wb-defect-checkbox > .toggle--label {
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
    #wb-page-stems {
        height: auto;
        width: 1fr;
        display: none;
    }
    #wb-page-layers {
        height: auto;
        width: 1fr;
        display: none;
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
    #wb-layers-hint {
        height: auto;
        width: 1fr;
        color: $text-muted;
        margin-top: 1;
    }
    #wb-layer-status {
        margin-bottom: 1;
    }
    #wb-blend-row {
        height: auto;
        width: 1fr;
        margin-top: 1;
        display: block;
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
    #wb-page-stems .wb-step-btn {
        height: 1;
        min-width: 5;
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
    #wb-page-stems .wb-step-btn:hover {
        background: $accent;
        color: #000000;
    }
    .wb-blend-val {
        width: 6;
        height: 1;
        text-align: center;
        color: $warning;
        text-style: bold;
    }
    .wb-model-desc {
        height: 1;
        color: $text-muted;
        margin-left: 2;
    }
    #wb-stem-actions-row {
        height: 1;
        width: 1fr;
        margin-top: 1;
        align: left middle;
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
    #wb-stem-actions-row .wb-action-detect {
        background: $accent;
        color: #000000;
    }
    #wb-stem-actions-row .wb-action-detect:hover {
        background: $secondary;
        color: #000000;
    }
    #wb-stem-actions-row .wb-action-resep {
        background: $panel;
        color: $warning;
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
    #wb-acoustic-status {
        height: auto;
        width: 1fr;
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }
    #wb-stems-racks-row {
        height: auto;
        width: 1fr;
        margin-top: 1;
    }
    .wb-diagnostic-panel {
        height: auto;
        width: 1fr;
        margin-top: 0;
        margin-right: 1;
        display: none;
        background: $surface;
        border: round $accent;
        padding: 0 1;
    }
    .wb-diagnostic-toolbar {
        height: 1;
        width: 1fr;
        align: left middle;
        margin-bottom: 0;
    }
    .wb-diagnostic-label {
        width: 1fr;
        height: 1;
        color: $accent;
        text-style: bold;
    }
    #wb-stems-racks-row .wb-diagnostic-btn {
        min-width: 7;
        height: 1;
        margin-left: 1;
        border: none;
        text-align: center;
        content-align: center middle;
    }
    DefectChecklist {
        height: auto;
        width: 1fr;
        background: transparent;
        border: none;
        overflow-y: hidden;
        overflow-x: hidden;
        margin-top: 1;
        margin-bottom: 0;
    }
    .wb-defect-checkbox {
        height: 1;
        background: transparent;
        border: none;
        padding: 0 1;
        margin-bottom: 1;
    }
    .wb-defect-checkbox:hover {
        color: $accent;
    }
    .wb-defect-checkbox:focus {
        background: transparent;
        text-style: bold;
    }
    .wb-diagnostic-list {
        height: auto;
        width: 1fr;
        background: transparent;
        border: none;
        overflow-y: hidden;
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
        self.exporter = EnhancementExporter(neural_enabled=False)
        self.selected_preset_id: str = "conservative"
        self.neural_enabled: bool = False
        self.audition_cache_dir = Path(platformdirs.user_cache_dir("omnirip")) / "audition"
        self.audition_cache_dir.mkdir(parents=True, exist_ok=True)

        # Active page: "deck" or "eq"
        self.active_page: str = "deck"
        self.eq_settings: MasteringEQSettings = MasteringEQSettings()
        self._eq_debounce_timer: asyncio.TimerHandle | None = None

        # Stem blend weights: how much to trust neural model output vs. inversion subtraction
        self.stem_bsr_blend: float = 0.70  # BS-RoFormer (specialized transformer)
        self.stem_hdemucs_blend: float = 0.50  # HDEMUCS (general-purpose model)
        self.stem_crossover_hz: float = 300.0  # Phase-aligned LR4 crossover frequency
        self.stem_dereverb_intensity: float = 0.40  # Anechoic De-Reverb intensity (0.0 to 1.0)

        # Multi-choice stem defect remediations (10 vocal, 10 instrumental):
        self.vocal_flags: set[str] = set()
        self.inst_flags: set[str] = set()
        self.vocal_profile: str = "natural"
        self.inst_profile: str = "natural"

        # Stream paths: MP3 (Original), ENH (Restored), VOC (Vocals), INST (Instrumental)
        self.path_mp3: Path | None = None
        self.path_enh: Path | None = None
        self.path_voc: Path | None = None
        self.path_inst: Path | None = None
        self._is_generating_enh: bool = False
        self._is_generating_stems: bool = False
        self._active_stem_tasks: set[Path] = set()

        # Layer Studio: separated per-source stems + their stem directory
        self.layer_track = None
        self.layer_stem_dir: Path | None = None
        self.layer_edit_plan: EditPlan | None = None
        self._is_building_layers: bool = False

        # Detached layer terminal (Option B): open the Layers page in its own
        # Terminal.app window writing/reading the JSON sidecar instead of (only)
        # the embedded workbench panel.
        self.detach_layer_terminal: bool = True
        self._layer_terminal_launched: bool = False
        self._layer_terminal_pending: bool = False
        self._transport_timer: Timer | None = None

        # Processing preset (docs/13): which stages run for this session. The
        # engine fallback chain (neural → hdemucs → eco) is separate and always
        # reported out loud — a preset never silently degrades.
        self.processing_preset: str = getattr(
            getattr(getattr(self.app, "config", None), "processing", None),
            "preset",
            DEFAULT_PRESET,
        )
        self.recording_credits: object | None = None
        self._credits_task_running: bool = False
        # Measured speaker count (docs/13 D27) — advisory, never overwrites the
        # MusicBrainz credit count.
        self.measured_speakers: int | None = None
        self._hosted_task_running: bool = False
        self._diarize_task_running: bool = False

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

    @property
    def path_a(self) -> Path | None:
        return self.path_mp3

    @property
    def path_b(self) -> Path | None:
        return self.path_mp3

    @property
    def path_c(self) -> Path | None:
        return self.path_enh

    @path_c.setter
    def path_c(self, val: Path | None) -> None:
        self.path_enh = val

    def compose(self) -> ComposeResult:
        yield Label("CURATION & ENHANCEMENT WORKBENCH", id="wb-header")
        yield Label("No track selected — click a track in the table above", id="wb-track-meta")
        yield Label("Cutoff fc: -- kHz | State: IDLE", id="wb-cutoff-info")

        with Horizontal(id="wb-stream-row"):
            yield Button("[1] MP3", id="btn-stream-mp3", variant="primary")
            yield Button("[2] ENH", id="btn-stream-enh", variant="default")
            yield Button("[3] VOC", id="btn-stream-voc", variant="default", disabled=True)
            yield Button("[4] INST", id="btn-stream-inst", variant="default", disabled=True)
            yield Button("ECO DSP", id="wb-btn-neural-toggle", variant="default")
            yield Button("MODELS", id="wb-btn-models-download", variant="default")

        yield ProgressBar(id="wb-stem-progress", total=100, show_eta=False, show_percentage=True)

        with Horizontal(id="wb-controls-row"):
            preset_options = AI_PRESET_OPTIONS if self.neural_enabled else ECO_PRESET_OPTIONS
            yield Select(
                options=preset_options, value=self.selected_preset_id, id="wb-preset-select"
            )
            with Horizontal(id="wb-export-split"):
                yield Button("💾 SAVE ENHANCED", id="wb-btn-export", variant="success")
                yield Button("↓", id="wb-btn-export-menu", variant="success")

        with Horizontal(id="wb-export-dropdown"):
            yield Label("FORMAT:", id="wb-export-dropdown-title")
            yield Button("🎵  Enhanced MP3",       id="wb-export-choose-enh",  classes="wb-export-choice")
            yield Button("🎤  Vocals (WAV)",        id="wb-export-choose-voc",  classes="wb-export-choice")
            yield Button("🎸  Instrumental (WAV)", id="wb-export-choose-inst", classes="wb-export-choice")
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
                    yield Label("10-BAND STUDIO MASTERING EQUALIZER", id="wb-eq-title")
                    yield Select(
                        options=[(k, k) for k in EQ_PRESETS.keys()],
                        value="Flat",
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

            with Vertical(id="wb-page-stems"):
                yield Label(
                    "STEM SEPARATION & BLEND STUDIO  [Dual-Model Architecture: BS-RoFormer (>300Hz) + HDEMUCS (<300Hz)]",
                    classes="wb-section-title",
                )
                with Horizontal(id="wb-stem-actions-row"):
                    yield Button("🎧  AUTO-DETECT", id="wb-btn-stem-auto-detect", classes="wb-stem-action-btn wb-action-detect")
                    yield Button("⚡  RE-SEPARATE", id="wb-btn-stem-reseparate", classes="wb-stem-action-btn wb-action-resep")
                    yield Button("🎤  AUDITION VOC", id="wb-btn-audition-voc", classes="wb-stem-action-btn")
                    yield Button("🎸  AUDITION INST", id="wb-btn-audition-inst", classes="wb-stem-action-btn")
                    yield Button("📦  AI MODELS", id="wb-btn-stem-models", classes="wb-stem-action-btn")
                    yield Button("▤  OPEN IN LAYERS", id="wb-btn-open-layers", classes="wb-stem-action-btn wb-action-resep")
                yield Label("", id="wb-acoustic-status", classes="wb-acoustic-status")

                with Vertical(id="wb-blend-row"):
                    with Horizontal(classes="wb-model-row"):
                        yield Label("BS-RoFormer  (Vocals/Highs >300Hz):", classes="wb-model-title")
                        with Horizontal(classes="wb-stepper-box"):
                            yield Button("−", id="wb-blend-bsr-dn", classes="wb-step-btn")
                            yield Label(
                                f"{int(self.stem_bsr_blend * 100)}%",
                                id="wb-blend-bsr-val",
                                classes="wb-blend-val",
                            )
                            yield Button("+", id="wb-blend-bsr-up", classes="wb-step-btn")
                        yield Label(self._get_blend_desc(self.stem_bsr_blend), id="wb-blend-bsr-desc", classes="wb-model-desc")

                    with Horizontal(classes="wb-model-row"):
                        yield Label("HDEMUCS      (Bass/Drums  <300Hz):", classes="wb-model-title")
                        with Horizontal(classes="wb-stepper-box"):
                            yield Button("−", id="wb-blend-hdemucs-dn", classes="wb-step-btn")
                            yield Label(
                                f"{int(self.stem_hdemucs_blend * 100)}%",
                                id="wb-blend-hdemucs-val",
                                classes="wb-blend-val",
                            )
                            yield Button("+", id="wb-blend-hdemucs-up", classes="wb-step-btn")
                        yield Label(
                            self._get_blend_desc(self.stem_hdemucs_blend),
                            id="wb-blend-hdemucs-desc",
                            classes="wb-model-desc",
                        )

                    with Horizontal(classes="wb-model-row"):
                        yield Label(
                            "LR4 Crossover (Phase-Aligned Split):", classes="wb-model-title"
                        )
                        with Horizontal(classes="wb-stepper-box"):
                            yield Button("−", id="wb-crossover-dn", classes="wb-step-btn")
                            yield Label(
                                f"{int(self.stem_crossover_hz)} Hz",
                                id="wb-crossover-val",
                                classes="wb-blend-val",
                            )
                            yield Button("+", id="wb-crossover-up", classes="wb-step-btn")
                        yield Label(
                            "Zero-Phase Linkwitz-Riley 4th Order",
                            id="wb-crossover-desc",
                            classes="wb-model-desc",
                        )

                    with Horizontal(classes="wb-model-row"):
                        yield Label(
                            "De-Reverb     (Anechoic Vocal Strip):", classes="wb-model-title"
                        )
                        with Horizontal(classes="wb-stepper-box"):
                            yield Button("−", id="wb-dereverb-dn", classes="wb-step-btn")
                            yield Label(
                                f"{int(self.stem_dereverb_intensity * 100)}%",
                                id="wb-dereverb-val",
                                classes="wb-blend-val",
                            )
                            yield Button("+", id="wb-dereverb-up", classes="wb-step-btn")
                        yield Label(
                            self._get_dereverb_desc(self.stem_dereverb_intensity),
                            id="wb-dereverb-desc",
                            classes="wb-model-desc",
                        )

                with Horizontal(id="wb-stems-racks-row"):
                    with Vertical(id="wb-diagnostic-voc-panel", classes="wb-diagnostic-panel"):
                        with Horizontal(classes="wb-diagnostic-toolbar"):
                            yield Label(
                                "Vocal Defect Remediations (Surgical):",
                                classes="wb-diagnostic-label",
                            )
                            yield Button("STUDIO", id="wb-btn-voc-studio", classes="wb-diagnostic-btn")
                            yield Button("ALL", id="wb-btn-voc-all", classes="wb-diagnostic-btn")
                            yield Button(
                                "CLEAR", id="wb-btn-voc-clear", classes="wb-diagnostic-btn"
                            )
                        yield DefectChecklist(
                            [
                                (label, key, key in self.vocal_flags)
                                for key, label in VOCAL_REMEDIATIONS.items()
                            ],
                            id="wb-voc-flags-list",
                            classes="wb-diagnostic-list",
                        )
                    with Vertical(id="wb-diagnostic-inst-panel", classes="wb-diagnostic-panel"):
                        with Horizontal(classes="wb-diagnostic-toolbar"):
                            yield Label(
                                "Inst Defect Remediations (Surgical):",
                                classes="wb-diagnostic-label",
                            )
                            yield Button(
                                "STUDIO", id="wb-btn-inst-studio", classes="wb-diagnostic-btn"
                            )
                            yield Button("ALL", id="wb-btn-inst-all", classes="wb-diagnostic-btn")
                            yield Button(
                                "CLEAR", id="wb-btn-inst-clear", classes="wb-diagnostic-btn"
                            )
                        yield DefectChecklist(
                            [
                                (label, key, key in self.inst_flags)
                                for key, label in INST_REMEDIATIONS.items()
                            ],
                            id="wb-inst-flags-list",
                            classes="wb-diagnostic-list",
                        )

            with Vertical(id="wb-page-layers"):
                yield Label(
                    "LAYER STUDIO  [Detached Terminal: song-detected lanes, per-second surgical edits]",
                    id="wb-layers-title",
                    classes="wb-section-title",
                )
                with Horizontal(id="wb-layers-actions"):
                    yield Button("⚡ BUILD STEMS", id="wb-btn-build-layers", classes="wb-layers-btn")
                    yield Button("🪟 OPEN LAYER TERMINAL", id="wb-btn-layer-terminal", classes="wb-layers-btn")
                    yield Button("💾 SAVE LAYERS", id="wb-btn-save-layers", classes="wb-layers-btn")
                    yield Button("CLEAR", id="wb-btn-clear-layers", classes="wb-layers-btn")
                with Horizontal(id="wb-layers-actions-plan"):
                    yield Button(
                        f"PROCESSING: {get_preset(self.processing_preset).label}",
                        id="wb-btn-preset",
                        classes="wb-layers-btn",
                    )
                    yield Button("🏷 CREDITS", id="wb-btn-credits", classes="wb-layers-btn")
                    yield Button(
                        "☁ HOSTED SEPARATE", id="wb-btn-hosted-separate", classes="wb-layers-btn"
                    )
                    yield Button("👥 SPEAKERS", id="wb-btn-detect-speakers", classes="wb-layers-btn")
                yield Label("", id="wb-preset-status", classes="wb-acoustic-status")
                yield Label(
                    "Lanes are detected from the song and drawn in the detached layer terminal "
                    "(OPEN LAYER TERMINAL) — full height, no box. The terminal follows this "
                    "window's playhead and sends seeks straight back to the player.",
                    id="wb-layers-hint",
                )
                yield Label("", id="wb-lane-plan", classes="wb-acoustic-status")
                yield Label("", id="wb-layer-status", classes="wb-acoustic-status")

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
        self.current_job = job
        cutoff = job.spectral.cutoff_hz if (job.spectral and job.spectral.cutoff_hz) else 15500.0
        self.cutoff_hz = cutoff

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
            stem_dir = (
                Path.home()
                / ".cache"
                / "omnirip"
                / "stems"
                / f"{self.path_mp3.stem}_{self.path_mp3.stat().st_size}"
            )
            if stem_dir.exists():
                from harvester.analysis.enhancement.stem_separator import (
                    get_stem_cache_suffix,
                    load_stem_profile,
                )

                prof = load_stem_profile(stem_dir)
                self.vocal_profile = prof.get("vocal_profile", "natural")
                self.inst_profile = prof.get("inst_profile", "natural")
                self.vocal_flags = set(prof.get("vocal_flags", []))
                self.inst_flags = set(prof.get("inst_flags", []))
                if not self.vocal_flags and self.vocal_profile != "natural":
                    self.vocal_flags = {self.vocal_profile}
                if not self.inst_flags and self.inst_profile != "natural":
                    self.inst_flags = {self.inst_profile}

                try:
                    voc_list = self.query_one("#wb-voc-flags-list", DefectChecklist)
                    voc_list.deselect_all()
                    for f in self.vocal_flags:
                        try:
                            voc_list.select(f)
                        except Exception:
                            pass

                    inst_list = self.query_one("#wb-inst-flags-list", DefectChecklist)
                    inst_list.deselect_all()
                    for f in self.inst_flags:
                        try:
                            inst_list.select(f)
                        except Exception:
                            pass
                except Exception:
                    pass

            from harvester.analysis.enhancement.stem_separator import get_stem_cache_suffix

            v_sfx = get_stem_cache_suffix(self.vocal_flags or self.vocal_profile)
            i_sfx = get_stem_cache_suffix(self.inst_flags or self.inst_profile)

            # Check profile-specific stems first, then standard stems
            v_cand = stem_dir / f"{self.path_mp3.stem}_neural_vocals{v_sfx}.wav"
            i_cand = stem_dir / f"{self.path_mp3.stem}_neural_instrumental{i_sfx}.wav"
            if not (v_cand.exists() and i_cand.exists()):
                v_cand = stem_dir / f"{self.path_mp3.stem}_bs_roformer_vocals{v_sfx}.wav"
                i_cand = stem_dir / f"{self.path_mp3.stem}_bs_roformer_instrumental{i_sfx}.wav"
            if not (v_cand.exists() and i_cand.exists()):
                v_cand = stem_dir / f"{self.path_mp3.stem}_neural_vocals.wav"
                i_cand = stem_dir / f"{self.path_mp3.stem}_neural_instrumental.wav"
            if not (v_cand.exists() and i_cand.exists()):
                v_cand = stem_dir / f"{self.path_mp3.stem}_bs_roformer_vocals.wav"
                i_cand = stem_dir / f"{self.path_mp3.stem}_bs_roformer_instrumental.wav"
            if not (v_cand.exists() and i_cand.exists()):
                v_cand = stem_dir / f"{self.path_mp3.stem}_vocals.wav"
                i_cand = stem_dir / f"{self.path_mp3.stem}_instrumental.wav"
            if not (v_cand.exists() and i_cand.exists()):
                v_cand = stem_dir / f"{self.path_mp3.stem}_eco_vocals.wav"
                i_cand = stem_dir / f"{self.path_mp3.stem}_eco_instrumental.wav"

            if v_cand.exists() and i_cand.exists():
                self.path_voc = v_cand
                self.path_inst = i_cand
                if stem_dir.exists():
                    self.layer_stem_dir = stem_dir

        try:
            pb = self.query_one("#wb-stem-progress", ProgressBar)
            if self.path_mp3 and self.path_mp3 in self._active_stem_tasks:
                pb.styles.display = "block"
            else:
                pb.styles.display = "none"
        except Exception:
            pass

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
            btn_voc = self.query_one("#btn-stream-voc", Button)
            btn_inst = self.query_one("#btn-stream-inst", Button)
            btn_mp3.variant = "primary" if normalized == "MP3" else "default"
            btn_enh.variant = "primary" if normalized == "ENH" else "default"
            btn_voc.variant = "primary" if normalized == "VOC" else "default"
            btn_inst.variant = "primary" if normalized == "INST" else "default"

            voc_panel = self.query_one("#wb-diagnostic-voc-panel")
            inst_panel = self.query_one("#wb-diagnostic-inst-panel")
            blend_row = self.query_one("#wb-blend-row")
            if normalized == "VOC":
                voc_panel.styles.display = "block"
                inst_panel.styles.display = "none"
                blend_row.styles.display = "block"
            elif normalized == "INST":
                voc_panel.styles.display = "none"
                inst_panel.styles.display = "block"
                blend_row.styles.display = "block"
            else:
                voc_panel.styles.display = "none"
                inst_panel.styles.display = "none"
                blend_row.styles.display = "none"
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
        elif normalized == "VOC":
            if not self.neural_enabled:
                self.query_one("#wb-status", Label).update(
                    "⚠ Stem separation requires Neural AI mode — enable it first."
                )
                return
            if self.path_voc and self.path_voc.exists():
                self._route_to_player(
                    self.path_voc,
                    title=f"[VOC] Isolated Vocals ({track_name})",
                    is_enhanced=True,
                )
                self.query_one("#wb-status", Label).update(
                    "Auditioning [VOC]: Isolated Vocals (Acapella)"
                )
            elif self.path_mp3 and self.path_mp3.exists():
                self.query_one("#wb-status", Label).update("Separating stems: isolating vocals...")
                self._trigger_stem_separation("VOC")
            else:
                self.query_one("#wb-status", Label).update("No audio loaded to separate.")
        elif normalized == "INST":
            if not self.neural_enabled:
                self.query_one("#wb-status", Label).update(
                    "⚠ Stem separation requires Neural AI mode — enable it first."
                )
                return
            if self.path_inst and self.path_inst.exists():
                self._route_to_player(
                    self.path_inst,
                    title=f"[INST] Karaoke Backing ({track_name})",
                    is_enhanced=True,
                )
                self.query_one("#wb-status", Label).update(
                    "Auditioning [INST]: Karaoke Instrumental"
                )
            elif self.path_mp3 and self.path_mp3.exists():
                self.query_one("#wb-status", Label).update(
                    "Separating stems: creating karaoke backing..."
                )
                self._trigger_stem_separation("INST")
            else:
                self.query_one("#wb-status", Label).update("No audio loaded to separate.")

        self._update_inspector()

    def _trigger_stem_separation(
        self, target_stream: str = "VOC", force: bool = False
    ) -> None:
        """Initiate background stem separation for current track."""
        if not self.path_mp3 or not self.path_mp3.exists():
            return
        if self.path_mp3 in self._active_stem_tasks:
            self.query_one("#wb-status", Label).update(
                "Stem separation is already processing for this track..."
            )
            return
        self._active_stem_tasks.add(self.path_mp3)
        self._is_generating_stems = True
        asyncio.create_task(self._async_separate_stems(self.path_mp3, target_stream, force=force))

    async def _async_separate_stems(
        self, source_path: Path, target_stream: str, force: bool = False
    ) -> None:
        """Run stem separation asynchronously with live progress and route stream when ready."""
        pb = None
        try:
            pb = self.query_one("#wb-stem-progress", ProgressBar)
            pb.styles.display = "block"
            pb.progress = 0.0
            pb.total = 100.0
        except Exception:
            pass

        def on_progress(pct: float, step: str) -> None:
            def _ui() -> None:
                try:
                    if pb and self.path_mp3 == source_path:
                        pb.progress = pct
                    if self.path_mp3 == source_path:
                        self.query_one("#wb-status", Label).update(
                            f"Stem Separation [{int(pct)}%]: {step}"
                        )
                except Exception:
                    pass

            self.app.call_from_thread(_ui)

        try:
            from harvester.analysis.enhancement.stem_separator import (
                StemSeparator,
                save_stem_profile,
            )

            separator = StemSeparator()
            sep_mode = "ensemble" if self.neural_enabled else "eco"
            res = await asyncio.to_thread(
                separator.separate_file,
                source_path,
                mode=sep_mode,
                progress_callback=on_progress,
                bs_roformer_weight=self.stem_bsr_blend,
                hdemucs_weight=self.stem_hdemucs_blend,
                vocal_profile=self.vocal_profile,
                inst_profile=self.inst_profile,
                vocal_flags=self.vocal_flags or self.vocal_profile,
                inst_flags=self.inst_flags or self.inst_profile,
                force_reseparate=force,
                crossover_hz=self.stem_crossover_hz,
                dereverb_intensity=self.stem_dereverb_intensity,
                save_individual_sources=True,
            )

            if res.vocals_path and res.vocals_path.parent:
                save_stem_profile(
                    res.vocals_path.parent,
                    vocal_profile=self.vocal_profile,
                    inst_profile=self.inst_profile,
                    vocal_flags=self.vocal_flags,
                    inst_flags=self.inst_flags,
                )

            if self.path_mp3 == source_path:
                self.path_voc = res.vocals_path
                self.path_inst = res.instrumental_path
                track_name = source_path.name

                self.layer_track = None
                self.layer_stem_dir = (
                    res.vocals_path.parent
                    if res.vocals_path and res.vocals_path.parent
                    else None
                )

                # NEURAL FULL: add the 6-source extras (guitar / piano) before the
                # lane grid is built, so the extra lanes show up in the same pass.
                preset = get_preset(self.processing_preset)
                if (
                    preset.extra_sources
                    and sep_mode != "eco"
                    and self.layer_stem_dir is not None
                ):
                    await self._run_extra_lanes(source_path, self.layer_stem_dir, sep_mode)

                # NEURAL FULL also tags audible content (advisory lane rows); the
                # tags are written next to the stems so the lane build reads them.
                if preset.tags and self.layer_stem_dir is not None:
                    await self._run_tagging_pass(source_path, self.layer_stem_dir)

                self._ensure_layers_built()

                # Report the engine that actually ran — a fallback is never silent.
                engine_text = engine_note(res.engine)
                if degraded(res.engine):
                    self.app.notify(
                        f"Separation fell back to the {engine_text}.",
                        title="OmniRip Stems",
                        severity="warning",
                        timeout=6.0,
                    )

                if self.active_stream == "VOC":
                    self._route_to_player(
                        self.path_voc,
                        title=f"[VOC] Isolated Vocals ({track_name})",
                        is_enhanced=True,
                    )
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{engine_text}]: Auditioning Vocals"
                    )
                elif self.active_stream == "INST":
                    self._route_to_player(
                        self.path_inst,
                        title=f"[INST] Karaoke Backing ({track_name})",
                        is_enhanced=True,
                    )
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{engine_text}]: Auditioning Karaoke"
                    )
                else:
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{engine_text}]: Vocals & Instrumental"
                    )

            self.app.notify(
                f"Separation Complete: {source_path.stem}\nVocals & Instrumental ready.",
                title="OmniRip Stems",
                timeout=4.0,
            )

            if pb and self.path_mp3 == source_path:
                pb.progress = 100.0
                await asyncio.sleep(0.6)
                pb.styles.display = "none"

        except Exception as err:
            logger.error("Stem separation failed for %s: %s", source_path, err)
            err_msg = str(err)
            is_ai_unavailable = "BS-RoFormer and HDEMUCS are unavailable" in err_msg
            display_msg = (
                "⛔ Neural AI models unavailable — install torch & torchaudio."
                if is_ai_unavailable
                else f"Stem separation error: {err}"
            )
            try:
                if self.path_mp3 == source_path:
                    self.query_one("#wb-status", Label).update(display_msg)
            except Exception:
                pass
            self.app.notify(
                display_msg,
                title="Separation Error — AI Models Unavailable"
                if is_ai_unavailable
                else "Separation Error",
                severity="error",
                timeout=6.0 if is_ai_unavailable else 4.0,
            )
        finally:
            self._active_stem_tasks.discard(source_path)
            self._is_generating_stems = bool(self._active_stem_tasks)
            try:
                if pb and self.path_mp3 == source_path:
                    pb.styles.display = "none"
            except Exception:
                pass

    def _get_eq_cache_tag(self) -> str:
        """Generate a short cache tag representing active EQ settings."""
        if not self.eq_settings.enabled or (
            not self.eq_settings.hpf_30hz
            and self.eq_settings.output_trim_db == 0.0
            and all(v == 0.0 for v in self.eq_settings.bands.values())
        ):
            return ""
        import hashlib

        bands = self.eq_settings.bands
        band_str = "_".join(f"{f}:{bands.get(f, 0.0):.1f}" for f in EQ_FREQUENCIES)
        key = (
            f"{band_str}_{self.eq_settings.hpf_30hz}_"
            f"{self.eq_settings.output_trim_db}_{self.eq_settings.enabled}"
        )
        return f"_eq_{hashlib.md5(key.encode()).hexdigest()[:6]}"

    def switch_page(self, page_id: str) -> None:
        """Switch between 'deck', 'eq', 'stems', 'layers', and 'vis' tabs inside the inspector container."""
        self.active_page = page_id
        try:
            page_deck = self.query_one("#wb-page-deck", Vertical)
            page_eq = self.query_one("#wb-page-eq", Vertical)
            page_stems = self.query_one("#wb-page-stems", Vertical)
            page_layers = self.query_one("#wb-page-layers", Vertical)
            page_vis = self.query_one("#wb-page-vis", Vertical)

            # Update page containers display
            page_deck.styles.display = "block" if page_id == "deck" else "none"
            page_eq.styles.display = "block" if page_id == "eq" else "none"
            page_stems.styles.display = "block" if page_id == "stems" else "none"
            page_layers.styles.display = "block" if page_id == "layers" else "none"
            page_vis.styles.display = "block" if page_id == "vis" else "none"


            if page_id == "eq":
                self._update_eq_ui()
            elif page_id == "stems":
                if self.active_stream not in ("VOC", "INST"):
                    self.set_active_stream("VOC")
                else:
                    self._update_blend_ui()
            elif page_id == "layers":
                self._ensure_layers_built()
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
            if (
                self.eq_settings.preset_name in EQ_PRESETS
                and select_preset.value != self.eq_settings.preset_name
            ):
                select_preset.value = self.eq_settings.preset_name
        except Exception:
            pass

    def _sync_eq_to_player(self) -> None:
        """Apply active 10-band EQ settings directly to the audio player in real-time."""
        try:
            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
            af = self.eq_settings.to_ffmpeg_af()
            player.set_audio_filter(af)
        except Exception:
            pass

    def _schedule_eq_render(self) -> None:
        """Apply EQ to active playback in real time and debounce background audio re-rendering."""
        self._sync_eq_to_player()

        if self.active_stream != "ENH":
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
        self.run_worker(self._async_render_enh(src, preset), name="render-stream-enh")

    async def _async_render_enh(self, src: Path, preset) -> None:
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
                eq_settings=self.eq_settings,
            )
            if self.selected_preset_id == preset.id:
                self.path_enh = out_path

            self._is_generating_enh = False

            # If user has ENH active and is still on this preset, immediately switch playback!
            if self.active_stream == "ENH" and self.selected_preset_id == preset.id:
                self._route_to_player(
                    out_path,
                    title=f"[ENH] Restored ({preset.name})",
                    is_enhanced=True,
                    preset_name=preset.name,
                )
                self.query_one("#wb-status", Label).update(
                    f"Auditioning [ENH]: Restored ({preset.name})"
                )
            self._update_inspector()

            # Pre-warm remaining presets of the active mode in the background
            self.run_worker(self._async_warm_remaining_presets(src), name="warm-mode-cache")
        except asyncio.CancelledError:
            self._is_generating_enh = False
        except Exception as exc:
            self._is_generating_enh = False
            try:
                self.query_one("#wb-status", Label).update(f"Enhance failed: {exc}")
            except Exception:
                pass

    async def _async_warm_remaining_presets(self, src: Path) -> None:
        """Pre-render remaining presets of the active mode so subsequent clicks
        are instantaneous.
        """
        if self.neural_enabled:
            # Prevent background memory spikes from heavy neural models; render on demand
            return

        active_opts = ECO_PRESET_OPTIONS
        mode_tag = "eco"
        for _, pid in active_opts:
            if pid == self.selected_preset_id:
                continue
            cache_dest = self.audition_cache_dir / f"{src.stem}_{pid}_{mode_tag}.mp3"
            if not cache_dest.exists():
                p = PRESETS.get(pid)
                if p:
                    try:
                        # Cooperatively yield to event loop so TUI animations & inputs never hitch
                        await asyncio.sleep(0.05)
                        await asyncio.to_thread(
                            self.exporter.export_enhanced_derivative,
                            input_path=src,
                            preset=p,
                            output_path=cache_dest,
                            cutoff_hz=self.cutoff_hz,
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
            player.set_audio_filter(self.eq_settings.to_ffmpeg_af())
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
        elif event.select.id == "wb-eq-preset-select" and event.value is not None:
            preset_name = str(event.value)
            if preset_name in EQ_PRESETS:
                self.eq_settings.apply_preset(preset_name)
                self._update_eq_ui()
                self._schedule_eq_render()
        elif event.select.id == "wb-diagnostic-voc-select" and event.value is not None:
            new_prof = str(event.value)
            if new_prof != self.vocal_profile:
                self.vocal_profile = new_prof
                self.app.notify(
                    f"Vocal diagnostic profile: {new_prof.replace('_', ' ').title()}",
                    title="OmniRip Stem Diagnostics",
                    timeout=3.0,
                )
                if self.path_mp3:
                    self._trigger_stem_separation("VOC")
        elif event.select.id == "wb-diagnostic-inst-select" and event.value is not None:
            new_prof = str(event.value)
            if new_prof != self.inst_profile:
                self.inst_profile = new_prof
                self.app.notify(
                    f"Instrumental diagnostic profile: {new_prof.replace('_', ' ').title()}",
                    title="OmniRip Stem Diagnostics",
                    timeout=3.0,
                )
                if self.path_mp3:
                    self._trigger_stem_separation("INST")

    def on_defect_checklist_selected_changed(self, event: DefectChecklist.SelectedChanged) -> None:
        """Handle multi-choice checkbox toggling for stem defect remediations."""
        list_id = event.checklist.id or ""
        if list_id == "wb-voc-flags-list":
            new_flags = set(event.checklist.selected)
            if new_flags != self.vocal_flags:
                self.vocal_flags = new_flags
                active_str = ", ".join(sorted(new_flags)) or "None"
                self.app.notify(
                    f"Vocal Remediations ({len(new_flags)}): {active_str}",
                    title="OmniRip Stem Diagnostics",
                    timeout=2.5,
                )
                if self.path_mp3:
                    self._trigger_stem_separation("VOC")
        elif list_id == "wb-inst-flags-list":
            new_flags = set(event.checklist.selected)
            if new_flags != self.inst_flags:
                self.inst_flags = new_flags
                active_str = ", ".join(sorted(new_flags)) or "None"
                self.app.notify(
                    f"Inst Remediations ({len(new_flags)}): {active_str}",
                    title="OmniRip Stem Diagnostics",
                    timeout=2.5,
                )
                if self.path_mp3:
                    self._trigger_stem_separation("INST")

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged[str]) -> None:
        """Fallback compatibility handler for legacy SelectionList events."""
        list_id = event.selection_list.id or ""
        if list_id == "wb-voc-flags-list":
            new_flags = set(event.selection_list.selected)
            if new_flags != self.vocal_flags:
                self.vocal_flags = new_flags
                if self.path_mp3:
                    self._trigger_stem_separation("VOC")
        elif list_id == "wb-inst-flags-list":
            new_flags = set(event.selection_list.selected)
            if new_flags != self.inst_flags:
                self.inst_flags = new_flags
                if self.path_mp3:
                    self._trigger_stem_separation("INST")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id in ("btn-stream-mp3", "btn-stream-a", "btn-stream-b"):
            self.set_active_stream("MP3")
        elif btn_id in ("btn-stream-enh", "btn-stream-c"):
            self.set_active_stream("ENH")
        elif btn_id == "btn-stream-voc":
            self.set_active_stream("VOC")
        elif btn_id == "btn-stream-inst":
            self.set_active_stream("INST")
        elif btn_id == "wb-btn-voc-studio":
            try:
                sel = self.query_one("#wb-voc-flags-list", DefectChecklist)
                sel.deselect_all()
                sel.select("de_bleed")
                sel.select("fix_pumping")
                self.vocal_flags = set(sel.selected)
            except Exception:
                pass
        elif btn_id == "wb-btn-voc-all":
            try:
                sel = self.query_one("#wb-voc-flags-list", DefectChecklist)
                sel.select_all()
                self.vocal_flags = set(sel.selected)
            except Exception:
                pass
        elif btn_id == "wb-btn-voc-clear":
            try:
                sel = self.query_one("#wb-voc-flags-list", DefectChecklist)
                sel.deselect_all()
                self.vocal_flags = set()
            except Exception:
                pass
        elif btn_id == "wb-btn-inst-studio":
            try:
                sel = self.query_one("#wb-inst-flags-list", DefectChecklist)
                sel.deselect_all()
                sel.select("anti_bleed_synths")
                sel.select("sub_bass_clean")
                self.inst_flags = set(sel.selected)
            except Exception:
                pass
        elif btn_id == "wb-btn-inst-all":
            try:
                sel = self.query_one("#wb-inst-flags-list", DefectChecklist)
                sel.select_all()
                self.inst_flags = set(sel.selected)
            except Exception:
                pass
        elif btn_id == "wb-btn-inst-clear":
            try:
                sel = self.query_one("#wb-inst-flags-list", DefectChecklist)
                sel.deselect_all()
                self.inst_flags = set()
            except Exception:
                pass
        elif btn_id == "wb-btn-stem-auto-detect":
            self._trigger_acoustic_detection()
        elif btn_id == "wb-btn-stem-reseparate":
            target = self.active_stream if self.active_stream in ("VOC", "INST") else "VOC"
            self.query_one("#wb-status", Label).update("Forcing fresh neural stem re-separation...")
            self._trigger_stem_separation(target, force=True)
        elif btn_id == "wb-btn-neural-toggle":
            self.toggle_neural_engine()
        elif btn_id in ("wb-btn-models-download", "wb-btn-stem-models"):
            self.trigger_models_download()
        elif btn_id == "wb-btn-export":
            self._export_derivative()
        elif btn_id == "wb-btn-export-menu":
            self._toggle_export_dropdown()
        elif btn_id in ("wb-export-choose-enh", "wb-export-choose-voc", "wb-export-choose-inst"):
            mode_map = {
                "wb-export-choose-enh": "ENH",
                "wb-export-choose-voc": "VOC",
                "wb-export-choose-inst": "INST",
            }
            self._set_export_mode(mode_map[btn_id])
            self._toggle_export_dropdown(force_close=True)
            self._export_derivative()
        elif btn_id == "wb-export-choose-close":
            self._toggle_export_dropdown(force_close=True)
        elif btn_id == "wb-btn-open-layers":
            self.switch_page("layers")
        elif btn_id == "wb-btn-layer-terminal":
            self._layer_terminal_launched = False
            self._launch_layer_terminal()
        elif btn_id == "wb-btn-build-layers":
            target = self.path_mp3
            if target and target.exists():
                if not get_preset(self.processing_preset).separation:
                    # FETCH ONLY has no separation stage; pressing BUILD STEMS is
                    # the explicit per-track opt-in, so switch and say so.
                    self._set_preset("standard")
                    with contextlib.suppress(Exception):
                        self.query_one("#wb-layer-status", Label).update(
                            "FETCH ONLY skips separation — switched to STANDARD for this track."
                        )
                self._trigger_stem_separation(target, force=False)
                self._ensure_layers_built()
            else:
                try:
                    self.query_one("#wb-layer-status", Label).update("No active track loaded to separate.")
                except Exception:
                    pass

        elif btn_id == "wb-btn-preset":
            self._cycle_processing_preset()

        elif btn_id == "wb-btn-credits":
            self._start_credits_lookup()

        elif btn_id == "wb-btn-hosted-separate":
            self._start_hosted_separation()

        elif btn_id == "wb-btn-detect-speakers":
            self._start_diarization()

        elif btn_id == "wb-btn-save-layers":
            self._commit_layers_async()
        elif btn_id == "wb-btn-clear-layers":
            self._clear_layer_edits()
        elif btn_id == "wb-btn-audition-voc":
            self.set_active_stream("VOC")
        elif btn_id == "wb-btn-audition-inst":
            self.set_active_stream("INST")
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
        elif btn_id == "wb-blend-bsr-up":
            self.stem_bsr_blend = min(1.0, round(self.stem_bsr_blend + 0.05, 2))
            self._update_blend_ui()
        elif btn_id == "wb-blend-bsr-dn":
            self.stem_bsr_blend = max(0.0, round(self.stem_bsr_blend - 0.05, 2))
            self._update_blend_ui()
        elif btn_id == "wb-blend-hdemucs-up":
            self.stem_hdemucs_blend = min(1.0, round(self.stem_hdemucs_blend + 0.05, 2))
            self._update_blend_ui()
        elif btn_id == "wb-blend-hdemucs-dn":
            self.stem_hdemucs_blend = max(0.0, round(self.stem_hdemucs_blend - 0.05, 2))
            self._update_blend_ui()
        elif btn_id == "wb-crossover-up":
            self.stem_crossover_hz = min(600.0, self.stem_crossover_hz + 25.0)
            self._update_blend_ui()
        elif btn_id == "wb-crossover-dn":
            self.stem_crossover_hz = max(150.0, self.stem_crossover_hz - 25.0)
            self._update_blend_ui()
        elif btn_id == "wb-dereverb-up":
            self.stem_dereverb_intensity = min(1.0, round(self.stem_dereverb_intensity + 0.10, 2))
            self._update_blend_ui()
        elif btn_id == "wb-dereverb-dn":
            self.stem_dereverb_intensity = max(0.0, round(self.stem_dereverb_intensity - 0.10, 2))
            self._update_blend_ui()

    @staticmethod
    def _get_blend_desc(val: float) -> str:
        """Human-readable descriptor for model blend weights."""
        if val >= 0.8:
            return "(Richest Texture)"
        if val >= 0.4:
            return "(Balanced Separation)"
        return "(Cleanest Isolation)"

    @staticmethod
    def _get_dereverb_desc(intensity: float) -> str:
        """Human-readable descriptor for de-reverb intensity."""
        pct = int(round(intensity * 100))
        if pct <= 5:
            return "(Bypassed — natural room reflections preserved)"
        if pct <= 25:
            return "(Subtle — light room de-bleed)"
        if pct <= 50:
            return "(Balanced — dry studio vocal acapella)"
        if pct <= 75:
            return "(Aggressive — tight anechoic isolation)"
        return "(Maximum — 100% dry clinical vocal)"

    def _update_blend_ui(self) -> None:
        """Refresh blend weight value labels and descriptors after a change."""
        try:
            self.query_one("#wb-blend-bsr-val", Label).update(f"{int(self.stem_bsr_blend * 100)}%")
            self.query_one("#wb-blend-hdemucs-val", Label).update(
                f"{int(self.stem_hdemucs_blend * 100)}%"
            )
            self.query_one("#wb-crossover-val", Label).update(f"{int(self.stem_crossover_hz)} Hz")
            self.query_one("#wb-dereverb-val", Label).update(
                f"{int(self.stem_dereverb_intensity * 100)}%"
            )
            bsr_desc = self._get_blend_desc(self.stem_bsr_blend)
            hd_desc = self._get_blend_desc(self.stem_hdemucs_blend)
            drv_desc = self._get_dereverb_desc(self.stem_dereverb_intensity)

            try:
                self.query_one("#wb-blend-bsr-desc", Label).update(bsr_desc)
                self.query_one("#wb-blend-hdemucs-desc", Label).update(hd_desc)
                self.query_one("#wb-dereverb-desc", Label).update(drv_desc)
            except Exception:
                pass

            self.query_one("#wb-status", Label).update(
                f"Ensemble — BS-RoFormer: {int(self.stem_bsr_blend * 100)}% | "
                f"HDEMUCS: {int(self.stem_hdemucs_blend * 100)}% | "
                f"LR4: {int(self.stem_crossover_hz)}Hz | "
                f"De-Reverb: {int(self.stem_dereverb_intensity * 100)}%"
            )
        except Exception:
            pass

    def _trigger_acoustic_detection(self) -> None:
        """Analyze track acoustics, vocal presence, and defects to auto-configure stems."""
        if not self.path_mp3 or not self.path_mp3.exists():
            self.notify("Load an audio track to run Acoustic Auto-Detect", severity="warning")
            return

        try:
            self.query_one("#wb-status", Label).update(
                "Listening to track acoustics & analyzing vocal distribution..."
            )
            self.query_one("#wb-acoustic-status", Label).update(
                "Analyzing track acoustics..."
            )
        except Exception:
            pass

        self.run_worker(self._async_detect_acoustics(self.path_mp3), name="stem-acoustic-detect")

    async def _async_detect_acoustics(self, source_path: Path) -> None:
        """Run acoustic detector in background thread and apply recommended settings."""
        try:
            import soundfile as sf

            def _load_and_analyze() -> AcousticAnalysisResult:
                data, sr = sf.read(str(source_path), dtype="float32", always_2d=True)
                # soundfile returns (samples, channels) -> transpose to (channels, samples)
                audio = data.T
                return analyze_track_acoustics(audio, sr=int(sr))

            result = await asyncio.to_thread(_load_and_analyze)

            if self.path_mp3 != source_path:
                return

            self.vocal_flags = set(result.recommended_vocal_flags)
            self.inst_flags = set(result.recommended_inst_flags)
            self.stem_bsr_blend = result.recommended_blend_weight

            # Update UI SelectionLists
            try:
                voc_list = self.query_one("#wb-voc-flags-list", DefectChecklist)
                voc_list.deselect_all()
                for f in self.vocal_flags:
                    try:
                        voc_list.select(f)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                inst_list = self.query_one("#wb-inst-flags-list", DefectChecklist)
                inst_list.deselect_all()
                for f in self.inst_flags:
                    try:
                        inst_list.select(f)
                    except Exception:
                        pass
            except Exception:
                pass

            self._update_blend_ui()

            if result.is_pure_instrumental:
                status_text = (
                    f"🎧 PURE INSTRUMENTAL ({int(result.vocal_confidence * 100)}% vocal conf) · "
                    f"Vocal bleed suppression bypassed · Sub-bass punch preserved"
                )
                self.notify(
                    "Acoustic analysis: Pure instrumental track detected.",
                    severity="information",
                )
            else:
                v_conf = int(result.vocal_confidence * 100)
                n_voc = len(result.recommended_vocal_flags)
                n_inst = len(result.recommended_inst_flags)
                blend = int(result.recommended_blend_weight * 100)
                status_text = (
                    f"🎤 VOCALS DETECTED ({v_conf}% conf) · "
                    f"Auto-tuned {n_voc} vocal & {n_inst} inst remediations · "
                    f"Blend set to {blend}%"
                )
                self.notify(
                    f"Acoustic analysis: {int(result.vocal_confidence * 100)}% vocal confidence.",
                    severity="information",
                )

            try:
                self.query_one("#wb-acoustic-status", Label).update(status_text)
                self.query_one("#wb-status", Label).update(status_text)
            except Exception:
                pass

        except Exception as exc:
            logger.exception("Acoustic analysis failed: %s", exc)
            try:
                self.query_one("#wb-status", Label).update(f"Acoustic analysis failed: {exc}")
                self.query_one("#wb-acoustic-status", Label).update("Acoustic analysis failed.")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Processing preset + lane provenance (docs/13)
    # ------------------------------------------------------------------
    async def _run_extra_lanes(self, source_path: Path, stem_dir: Path, mode: str) -> None:
        """NEURAL FULL: persist guitar/piano raw stems for the lane grid.

        Writes the extras under the *same* mode suffix the 4-source run used, so
        ``dynamic_layers`` picks them up with no extra wiring. A missing model
        degrades to 4-source lanes and says so.
        """

        def _on_progress(pct: float, step: str) -> None:
            def _ui() -> None:
                with contextlib.suppress(Exception):
                    if self.path_mp3 == source_path:
                        self.query_one("#wb-status", Label).update(
                            f"Extra lanes [{int(pct)}%]: {step}"
                        )

            self.app.call_from_thread(_ui)

        try:
            from harvester.analysis.enhancement.stem_separator import StemSeparator

            separator = StemSeparator()
            extra = await asyncio.to_thread(
                separator.separate_extra_lanes,
                source_path,
                stem_dir,
                mode=mode,
                progress_callback=_on_progress,
            )
        except Exception as exc:
            logger.info("extra lane pass skipped: %s", exc)
            return
        with contextlib.suppress(Exception):
            self.query_one("#wb-layer-status", Label).update(
                "Extra lanes ready: " + ", ".join(sorted(extra))
                if extra
                else "Extra lanes unavailable (6-source model missing) — 4-source lanes only."
            )

    async def _run_tagging_pass(self, source_path: Path, stem_dir: Path) -> None:
        """NEURAL FULL: CLAP instrument/vocal tags → ``tags.json`` → plan rows.

        Advisory by design (docs/13 D25): tags only add provenance rows to the
        lane plan — never verdicts, never file metadata. A missing model or
        dependency leaves the track untagged instead of failing the run.
        """
        from harvester.analysis.enhancement.tags import ClapTagger

        def _on_progress(pct: float, step: str) -> None:
            def _ui() -> None:
                with contextlib.suppress(Exception):
                    if self.path_mp3 == source_path:
                        self.query_one("#wb-layer-status", Label).update(
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
            if result is None:
                self.query_one("#wb-layer-status", Label).update(
                    "Tags unavailable (CLAP model not cached) — lanes stay as detected."
                )
            else:
                self.query_one("#wb-layer-status", Label).update(result.describe())

    def _layer_work_target(self) -> tuple[Path, Path, str] | None:
        """(source, stem_dir, mode) for the loaded track, or None (status set).

        Hosted separation and speaker measurement both work on a track that was
        never separated locally, so the stem directory is derived from the same
        helper the separator uses instead of requiring a prior local run.
        """
        source = self.path_mp3
        if source is None or not source.exists():
            self._layer_status("No active track loaded.")
            return None
        mode = "ensemble" if self.neural_enabled else "eco"
        stem_dir = self.layer_stem_dir
        if stem_dir is None:
            try:
                from harvester.analysis.enhancement.stem_separator import stem_dir_for

                stem_dir = stem_dir_for(source)
            except Exception as exc:  # pragma: no cover - defensive
                logger.info("could not resolve a stem directory: %s", exc)
                self._layer_status("Could not resolve a stem directory for this track.")
                return None
        return source, stem_dir, mode

    def _layer_status(self, text: str) -> None:
        """Write the LAYERS status line (never raises on a stale widget)."""
        with contextlib.suppress(Exception):
            self.query_one("#wb-layer-status", Label).update(text)

    def _start_hosted_separation(self) -> None:
        """☁ HOSTED SEPARATE — the opt-in cloud run (docs/13 D26).

        Nothing is uploaded unless this is pressed: the preset never touches the
        network, and a missing key is reported instead of queued.
        """
        if self._hosted_task_running:
            self._layer_status("Hosted separation is already running for this track…")
            return
        target = self._layer_work_target()
        if target is None:
            return
        source, stem_dir, mode = target
        from harvester.services.mvsep import SEP_TYPE_LABELS

        processing = getattr(getattr(self.app, "config", None), "processing", None)
        sep_type = str(getattr(processing, "hosted_sep_type", DEFAULT_SEP_TYPE) or DEFAULT_SEP_TYPE)
        max_seconds = float(getattr(processing, "hosted_max_seconds", 0.0) or 0.0)
        self._hosted_task_running = True
        scope = f"up to {max_seconds:.0f}s" if max_seconds > 0 else "the whole track"
        self._layer_status(
            f"☁ Hosted separation: uploading {scope} to MVSEP "
            f"({SEP_TYPE_LABELS.get(sep_type, sep_type)})…"
        )
        self.run_worker(
            self._async_hosted_separation(source, stem_dir, mode, sep_type, max_seconds),
            name="hosted-separation",
        )

    async def _async_hosted_separation(
        self,
        source: Path,
        stem_dir: Path,
        mode: str,
        sep_type: str,
        max_seconds: float,
    ) -> None:
        """Upload → poll → download hosted stems, then rebuild the lane grid."""
        try:
            from harvester.services.mvsep import MvsepClient

            client = MvsepClient()
            if not client.available:
                self._layer_status(
                    "Hosted separation needs an MVSEP key — add MVSEP_API_KEY to .env."
                )
                return

            def _on_progress(pct: float, step: str) -> None:
                def _ui() -> None:
                    self._layer_status(f"☁ Hosted [{int(pct)}%]: {step}")

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
            self._layer_status(f"Hosted separation failed: {exc}")
            return
        finally:
            self._hosted_task_running = False

        if not result.stems:
            self._layer_status(result.message or "Hosted separation produced no usable stems.")
            return

        note = result.describe()
        if result.skipped:
            note += f" · skipped {', '.join(result.skipped)}"
        self._layer_status(note)
        # The hosted stems are on disk now: rebuild the grid so they appear as
        # rows with `hosted (MVSEP)` provenance.
        self.layer_track = None
        self._is_building_layers = False
        self._ensure_layers_built()

    def _start_diarization(self) -> None:
        """👥 SPEAKERS — measure voices in the track (advisory, docs/13 D27)."""
        if self._diarize_task_running:
            self._layer_status("Speaker measurement is already running…")
            return
        target = self._layer_work_target()
        if target is None:
            return
        source, _stem_dir, _mode = target
        audio = self.path_voc if self.path_voc and self.path_voc.exists() else source
        processing = getattr(getattr(self.app, "config", None), "processing", None)
        max_seconds = float(getattr(processing, "diarize_max_seconds", 0.0) or 0.0)
        self._diarize_task_running = True
        self._layer_status(
            f"👥 Measuring speakers in {audio.name} (pyannote, CPU — this takes a while)…"
        )
        self.run_worker(self._async_diarize(audio, max_seconds), name="speaker-measure")

    async def _async_diarize(self, audio: Path, max_seconds: float) -> None:
        """Diarize in a worker thread and fold the count into the plan (advisory)."""
        try:
            from harvester.services.diarization import Diarizer, pyannote_available

            if not pyannote_available():
                self._layer_status(
                    "Speaker measurement needs the optional extra: "
                    "uv pip install -e '.[diarize]'"
                )
                return

            def _on_progress(pct: float, step: str) -> None:
                def _ui() -> None:
                    self._layer_status(f"👥 Speakers [{int(pct)}%]: {step}")

                self.app.call_from_thread(_ui)

            diarizer = Diarizer()
            result = await asyncio.to_thread(
                diarizer.diarize, audio, max_seconds=max_seconds, progress=_on_progress
            )
        except Exception as exc:
            logger.info("speaker measurement failed: %s", exc)
            self._layer_status(f"Speaker measurement failed: {exc}")
            return
        finally:
            self._diarize_task_running = False

        self.measured_speakers = result.speaker_count
        track = self.layer_track
        if track is not None and hasattr(track, "replan"):
            try:
                track.replan(measured_speakers=result.speaker_count)
                self._render_lane_plan(track)
            except Exception as exc:  # pragma: no cover - defensive
                logger.info("lane replan after diarization failed: %s", exc)

        note = result.describe()
        credits = self.recording_credits
        credited = getattr(credits, "singer_count", None) if credits is not None else None
        if credited and result.speaker_count and credited != result.speaker_count:
            note += (
                f" · MusicBrainz credits say {credited} — credits stay authoritative"
            )
        self._layer_status(note)

    def _set_preset(self, name: str) -> None:
        """Apply a processing preset and report what it changes."""
        from harvester.processing import normalize_preset

        self.processing_preset = normalize_preset(name)
        preset = get_preset(self.processing_preset)
        with contextlib.suppress(Exception):
            self.query_one("#wb-btn-preset", Button).label = f"PROCESSING: {preset.label}"
        with contextlib.suppress(Exception):
            self.query_one("#wb-preset-status", Label).update(
                f"{preset.summary} · {preset.detail}"
            )

    def _cycle_processing_preset(self) -> None:
        """Cycle FETCH ONLY → STANDARD → NEURAL FULL."""
        self._set_preset(next_preset(self.processing_preset))
        with contextlib.suppress(Exception):
            self.query_one("#wb-status", Label).update(
                f"Processing preset: {get_preset(self.processing_preset).summary}"
            )

    def _render_lane_plan(self, track: object | None = None) -> None:
        """Show lane provenance rows (origin + confidence + note) in the panel."""
        target = track if track is not None else self.layer_track
        plan = getattr(target, "lane_plan", None)
        if plan is None:
            return
        rows = [f"LANE PLAN: {plan.summary()}"]
        entries = list(plan.entries)
        for entry in entries[:12]:
            rows.append(f"  • {entry.describe()}")
        if len(entries) > 12:
            rows.append(f"  … +{len(entries) - 12} more")
        with contextlib.suppress(Exception):
            self.query_one("#wb-lane-plan", Label).update("\n".join(rows))

    def _start_credits_lookup(self) -> None:
        """Fingerprint → AcoustID → MusicBrainz credits for the loaded track."""
        if self._credits_task_running:
            return
        target = self.path_mp3
        if target is None or not target.exists():
            with contextlib.suppress(Exception):
                self.query_one("#wb-layer-status", Label).update(
                    "No active track loaded for a credits lookup."
                )
            return
        self._credits_task_running = True
        self.run_worker(
            self._async_fetch_credits(target), name="credits-lookup", exclusive=True
        )

    async def _async_fetch_credits(self, target: Path) -> None:
        """Resolve documented instruments/vocalists and feed the lane plan."""
        try:
            with contextlib.suppress(Exception):
                self.query_one("#wb-layer-status", Label).update(
                    "Credits: fingerprinting the track…"
                )
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
            if not mbid:
                with contextlib.suppress(Exception):
                    self.query_one("#wb-layer-status", Label).update(
                        "Credits: no MusicBrainz recording id (AcoustID miss) — "
                        "lanes stay as detected."
                    )
                return
            mb = CoverArtService(app_cfg)
            try:
                credits = await mb.fetch_recording_credits(mbid)
            finally:
                await mb.close()
            self.recording_credits = credits
            text = credits.summary() if credits is not None else "credits unavailable"
            with contextlib.suppress(Exception):
                self.query_one("#wb-layer-status", Label).update(f"CREDITS: {text}")
            self._apply_credits_to_plan()
        except Exception as exc:
            logger.info("credits lookup failed: %s", exc)
            with contextlib.suppress(Exception):
                self.query_one("#wb-layer-status", Label).update(
                    f"Credits lookup failed: {exc}"
                )
        finally:
            self._credits_task_running = False

    def _apply_credits_to_plan(self) -> None:
        """Recompute lane provenance with the credit inventory (no re-analysis)."""
        track = self.layer_track
        if track is None or not hasattr(track, "replan"):
            return
        credits = self.recording_credits
        # Instruments *and* vocal credits annotate lanes (producers/performers do not).
        lane_credits = tuple(getattr(credits, "lane_credits", ()) or ()) if credits else ()
        singers = getattr(credits, "singer_count", None) if credits is not None else None
        try:
            track.replan(credit_instruments=lane_credits, singer_count=singers)
        except Exception as exc:
            logger.info("lane replan failed: %s", exc)
            return
        self._render_lane_plan(track)

    # ------------------------------------------------------------------
    # Layer studio → detached terminal transport (the terminal owns selection)
    # ------------------------------------------------------------------
    def _layer_sidecar_path(self) -> Path | None:
        if self.path_mp3 is None:
            return None
        return self.path_mp3.parent / "layer_sidecar.json"

    def _publish_layer_transport(self) -> None:
        """Publish this app's playhead and apply the terminal's seek/play requests.

        Runs while a detached layer terminal is open: OmniRip owns audio output,
        so it is the single writer of the live transport state, and it consumes
        the requests the terminal writes back (click-to-seek, space play/pause).
        """
        sidecar_path = self._layer_sidecar_path()
        if sidecar_path is None or not self._layer_terminal_launched:
            return
        try:
            from harvester.ipc.layer_sidecar import (
                TransportState,
                consume_requests,
                transport_path,
                write_transport,
            )

            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
        except Exception:
            return

        seek_request, play_request = None, None
        try:
            seek_request, play_request = consume_requests(sidecar_path)
        except Exception as exc:
            logger.debug("layer transport request read failed: %s", exc)

        if seek_request is not None:
            with contextlib.suppress(Exception):
                player.seek(float(seek_request))
                self.query_one("#wb-layer-status", Label).update(
                    f"Terminal seek → {float(seek_request):.0f}s"
                )
        if play_request is not None:
            with contextlib.suppress(Exception):
                if play_request and not player.is_playing:
                    player.play()
                elif not play_request and player.is_playing:
                    player.pause()

        # Nothing to say while paused on another page (a request was just answered,
        # so publish then too) — this keeps the 5 Hz write off the idle path.
        answered = seek_request is not None or play_request is not None
        if not answered:
            try:
                playing = bool(player.is_playing)
            except Exception:
                playing = False
            if not playing and getattr(self, "active_page", "layers") != "layers":
                return

        try:
            write_transport(
                transport_path(sidecar_path),
                TransportState(
                    playhead_s=float(player.elapsed_s),
                    playing=bool(player.is_playing),
                    duration_s=float(player.duration_s or 0.0),
                ),
            )
        except Exception as exc:
            logger.debug("layer transport publish failed: %s", exc)

    def _clear_layer_edits(self) -> None:
        """Remove all staged edits (raw cache untouched)."""
        self.layer_edit_plan = EditPlan()
        self.query_one("#wb-layer-status", Label).update(
            "Edits cleared. Nothing staged."
        )

    def _commit_layers_async(self) -> None:
        """Commit the staged edit plan onto the layer files in a background thread."""
        self._reload_sidecar_edits()
        if self.layer_track is None or not self.layer_edit_plan or self.layer_edit_plan.count == 0:
            self.query_one("#wb-layer-status", Label).update(
                "Nothing to save — stage edits by clicking a cell, then m/b/s/u/p."
            )
            return
        if self._is_building_layers:
            self.query_one("#wb-layer-status", Label).update(
                "Layer timeline is busy — wait for the current build to finish."
            )
            return
        self._is_building_layers = True
        self.run_worker(
            self._async_commit_layers(),
            name="layer-studio-commit",
        )

    async def _async_commit_layers(self) -> None:
        """Apply the staged EditPlan, then rebuild the grid from committed files."""
        from harvester.analysis.enhancement.layer_editor import commit_edit_plan
        from harvester.analysis.enhancement.layers import build_layer_sources

        try:
            if (
                not self.layer_track
                or not self.layer_edit_plan
                or not self.layer_stem_dir
            ):
                return
            stem_dir = self.layer_stem_dir
            input_stem = self.path_mp3.stem if self.path_mp3 else ""
            mode = "ensemble" if self.neural_enabled else "eco"
            self.query_one("#wb-layer-status", Label).update(
                "Committing edits with 20ms crossfades…"
            )
            sources = await asyncio.to_thread(
                build_layer_sources,
                stem_dir,
                input_stem,
                mode,
                sample_rate=44100,
                crossover_hz=self.stem_crossover_hz,
            )
            # M3: snapshot the pre-edit reconstruction so we can verify the
            # mix-reconstruction error budget on the edited seconds after commit.
            from harvester.analysis.enhancement.layer_editor import reconstruct_mix

            edited_cells = self.layer_edit_plan.cells()
            pre_mix = await asyncio.to_thread(reconstruct_mix, sources, 44100)
            written = await asyncio.to_thread(
                commit_edit_plan, self.layer_edit_plan, sources, 44100
            )
            self.layer_edit_plan = EditPlan()

            # Rebuild the grid so the timeline reflects the committed edits.
            from harvester.analysis.enhancement.layer_editor import rebuild_track_after_commit
            from harvester.analysis.enhancement.layers import estimate_duration

            duration_src = self.path_inst or self.path_voc or self.path_mp3
            duration = (
                await asyncio.to_thread(estimate_duration, duration_src)
                if duration_src
                else 0.0
            )
            track = await asyncio.to_thread(
                rebuild_track_after_commit,
                stem_dir,
                input_stem,
                mode,
                duration,
                sample_rate=44100,
                crossover_hz=self.stem_crossover_hz,
            )
            self.layer_track = track
            residual_note = ""
            try:
                from harvester.analysis.enhancement.layer_editor import (
                    RECONSTRUCTION_BUDGET_DB,
                    verify_mix_residual,
                )

                post_mix = await asyncio.to_thread(reconstruct_mix, sources, 44100)
                _, worst, violating = verify_mix_residual(
                    pre_mix, post_mix, 44100, budget_db=RECONSTRUCTION_BUDGET_DB
                )
                edited_idx = {idx for _, idx, _ in edited_cells}
                clean_violating = [i for i in violating if i not in edited_idx]
                if not clean_violating:
                    residual_note = f" · mix residual ≤ {RECONSTRUCTION_BUDGET_DB:.0f} dBFS"
                else:
                    residual_note = (
                        f" · residual {worst:.1f} dBFS @ s{clean_violating[0]} "
                        f"(unedited leak, {len(clean_violating)}s)"
                    )
            except Exception as res_exc:
                logger.debug("mix residual verification skipped: %s", res_exc)
            self.query_one("#wb-layer-status", Label).update(
                f"Saved layers: {', '.join(sorted(written))} · "
                f"timeline rebuilt ({track.n_segments}s).{residual_note}"
            )
            await self._refresh_sidecar_after_commit()
        except Exception as exc:
            logger.exception("Layer Studio commit failed: %s", exc)
            try:
                self.query_one("#wb-layer-status", Label).update(
                    f"Layer save failed: {exc}"
                )
            except Exception:
                pass
        finally:
            self._is_building_layers = False

    def _ensure_layers_built(self) -> None:
        """Build the per-source layer timeline if stems exist and it isn't built yet."""
        if self._is_building_layers or self.layer_track is not None:
            return
        if not self.path_mp3 or not self.path_mp3.exists():
            self.query_one("#wb-layer-status", Label).update(
                "Load and separate a track to build the Layer Studio timeline."
            )
            return
        if self.neural_enabled is False and self.path_inst is not None:
            stem_dir = self.path_inst.parent
        else:
            stem_dir = self.layer_stem_dir
        if stem_dir is None or not stem_dir.exists():
            if self._is_generating_stems or self._active_stem_tasks:
                self.query_one("#wb-layer-status", Label).update(
                    "Separating stems… the layer timeline builds automatically when done."
                )
            elif not get_preset(self.processing_preset).separation:
                self.query_one("#wb-layer-status", Label).update(
                    f"{get_preset(self.processing_preset).label}: this track was not separated. "
                    "Press ⚡ BUILD STEMS to opt in for it."
                )
            else:
                self.query_one("#wb-layer-status", Label).update(
                    "Separate stems first, then open LAYERS."
                )
            return

        mode = "ensemble" if self.neural_enabled else "eco"
        self._is_building_layers = True
        self.run_worker(
            self._async_build_layers(stem_dir, self.path_mp3.stem, mode),
            name="layer-studio-build",
        )

    async def _async_build_layers(
        self, stem_dir: Path, input_stem: str, mode: str
    ) -> None:
        """Run layer analysis in a background thread and hand the grid to the widget."""
        try:
            from harvester.analysis.enhancement.layers import (
                LayerTrack,
                build_layer_track,
                estimate_duration,
            )

            duration_src = self.path_inst or self.path_voc or self.path_mp3
            duration = await asyncio.to_thread(estimate_duration, duration_src) if duration_src else 0.0

            last_pct = {"v": -1.0}

            def _on_build_progress(pct: float, step: str) -> None:
                if pct - last_pct["v"] < 1.0:
                    return
                last_pct["v"] = pct

                def _ui() -> None:
                    try:
                        self.query_one("#wb-layer-status", Label).update(
                            f"Building layer timeline… {int(pct)}% ({step}) — "
                            "the grid appears when ready."
                        )
                    except Exception:
                        pass

                self.app.call_from_thread(_ui)

            credits = self.recording_credits
            credit_instruments = (
                tuple(getattr(credits, "lane_credits", ()) or ()) if credits else ()
            )
            singer_count = getattr(credits, "singer_count", None) if credits is not None else None
            preset = get_preset(self.processing_preset)
            tag_labels: tuple[str, ...] = ()
            if preset.tags:
                try:
                    from harvester.analysis.enhancement.tags import tagged_labels

                    tag_labels = tagged_labels(stem_dir)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.info("tags unavailable for the lane plan: %s", exc)

            def _build() -> LayerTrack:
                return build_layer_track(
                    stem_dir,
                    input_stem,
                    mode,
                    duration_s=duration,
                    sample_rate=44100,
                    crossover_hz=self.stem_crossover_hz,
                    progress_callback=_on_build_progress,
                    credit_instruments=credit_instruments,
                    singer_count=singer_count,
                    tag_labels=tag_labels,
                    measured_speakers=self.measured_speakers,
                )

            try:
                self.query_one("#wb-layer-status", Label).update(
                    "Building layer timeline… "
                )
            except Exception:
                pass
            track = await asyncio.to_thread(_build)
            if track is None or not track.segments:
                raise RuntimeError("Layer analysis produced no timeline segments.")

            self.layer_track = track
            self._render_lane_plan(track)
            if self._layer_terminal_pending and self.layer_track is not None:
                self._layer_terminal_pending = False
                self.run_worker(
                    self._async_launch_layer_terminal(),
                    name="layer-terminal-launch",
                    exclusive=True,
                )
            try:
                n_issues = sum(len(s.issues) for s in track.segments)
                detected = track.lane_summary
                lanes = len(track.active_layers)
                self.query_one("#wb-layer-status", Label).update(
                    f"LAYERS READY: {lanes} lanes ({detected}) · "
                    f"{track.n_segments}s timeline · {n_issues} defect seconds flagged "
                    "(open the layer terminal to edit)."
                )
            except Exception:
                pass
        except Exception as exc:
            logger.exception("Layer analysis failed: %s", exc)
            try:
                self.query_one("#wb-layer-status", Label).update(
                    f"Layer analysis failed: {exc}"
                )
            except Exception:
                pass
        finally:
            self._is_building_layers = False

    # ------------------------------------------------------------------
    # Detached layer terminal (Option B)
    # ------------------------------------------------------------------
    def _launch_layer_terminal(self) -> None:
        """Write the JSON sidecar and open the layer terminal on demand.

        Called only via the ``🪟 NEW WINDOW`` button (never auto-opened on
        page switch). The build is async, so if ``layer_track`` is not ready
        yet the launch is deferred until ``_async_build_layers`` finishes by
        setting the ``_layer_terminal_pending`` flag. Resetting
        ``_layer_terminal_launched`` before calling allows each click to open
        (or re-open after the window was closed) a fresh terminal window.
        """
        if not self.detach_layer_terminal or self._layer_terminal_launched:
            return
        if self.path_mp3 is None or not self.path_mp3.exists():
            return
        if self.layer_track is None:
            self._layer_terminal_pending = True
            self._ensure_layers_built()
            return
        self._layer_terminal_launched = True
        self.run_worker(
            self._async_launch_layer_terminal(),
            name="layer-terminal-launch",
            exclusive=True,
        )

    async def _async_launch_layer_terminal(self) -> None:
        """Write the sidecar and spawn the detached layer terminal process."""
        try:
            from harvester.ipc.layer_sidecar import write_sidecar
            from harvester.ui.layer_terminal import launch_layer_terminal

            sidecar_path = self._layer_sidecar_path()
            if sidecar_path is None:
                return
            plan = self.layer_edit_plan.edits if self.layer_edit_plan else {}
            await asyncio.to_thread(
                write_sidecar, self.layer_track, plan, sidecar_path
            )
            proc = await asyncio.to_thread(launch_layer_terminal, sidecar_path)
            if proc is not None:
                logger.info("Layer terminal launched (sidecar %s)", sidecar_path)
                self._start_layer_transport()
                self.query_one("#wb-layer-status", Label).update(
                    "LAYER TERMINAL open — it follows this window's playhead; "
                    "its seek/play requests drive this player. Edits come back on SAVE LAYERS."
                )
            else:
                self.query_one("#wb-layer-status", Label).update(
                    "Could not open a terminal window — run the layer editor manually: "
                    f"python -m harvester.ui.layer_terminal --sidecar {sidecar_path}"
                )
        except Exception as exc:
            logger.exception("layer terminal launch failed: %s", exc)
            self._layer_terminal_launched = False
            try:
                self.query_one("#wb-layer-status", Label).update(
                    f"Layer terminal launch failed: {exc}"
                )
            except Exception:
                pass

    def _start_layer_transport(self) -> None:
        """Begin publishing the playhead to the detached layer terminal (5 Hz)."""
        if self._transport_timer is None:
            self._transport_timer = self.set_interval(0.20, self._publish_layer_transport)

    def _reload_sidecar_edits(self) -> None:
        """Merge any edit plan written back by the detached layer terminal."""
        sidecar_path = self._layer_sidecar_path()
        if sidecar_path is None:
            return
        if not sidecar_path.exists():
            return
        try:
            from harvester.ipc.layer_sidecar import read_sidecar

            _, sidecar_plan = read_sidecar(sidecar_path)
        except Exception as exc:
            logger.debug("sidecar reload skipped: %s", exc)
            return
        if not sidecar_plan:
            return
        plan = self.layer_edit_plan or EditPlan()
        for cell, op in sidecar_plan.items():
            # Do not clobber edits already staged locally in the workbench.
            plan.edits.setdefault(cell, op)
        self.layer_edit_plan = plan
        logger.info("Picked up %d edit(s) from the detached layer terminal.", plan.count)

    async def _refresh_sidecar_after_commit(self) -> None:
        """Rewrite the sidecar with the committed grid so a stale plan is not
        re-applied by an already-open layer terminal on its next save."""
        if self.layer_track is None:
            return
        sidecar_path = self._layer_sidecar_path()
        if sidecar_path is None or not sidecar_path.exists():
            return
        try:
            from harvester.ipc.layer_sidecar import write_sidecar

            await asyncio.to_thread(
                write_sidecar, self.layer_track, {}, sidecar_path
            )
        except Exception:
            pass

    def toggle_neural_engine(self) -> None:
        """Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode."""
        for worker in self.workers:
            if worker.name in ("render-stream-enh", "warm-mode-cache", "vis-load"):
                worker.cancel()
        self.neural_enabled = not self.neural_enabled
        self.exporter.set_neural_enabled(self.neural_enabled)

        btn = self.query_one("#wb-btn-neural-toggle", Button)
        sel = self.query_one("#wb-preset-select", Select)

        if self.neural_enabled:
            btn.label = "NEURAL AI"
            btn.variant = "warning"
            sel.set_options(AI_PRESET_OPTIONS)
            valid_ai_ids = {pid for _, pid in AI_PRESET_OPTIONS}
            if self.selected_preset_id not in valid_ai_ids:
                self.selected_preset_id = "extended_air"
            sel.value = self.selected_preset_id
            self.query_one("#btn-stream-voc", Button).disabled = False
            self.query_one("#btn-stream-inst", Button).disabled = False

            self.query_one("#wb-status", Label).update(
                "Neural AI mode active: Deep neural models enabled."
            )
            self.app.notify(
                "Neural AI Enabled: Deep models will be used when available.",
                title="OmniRip Neural Mode",
                timeout=3.0,
            )
        else:
            btn.label = "ECO DSP"
            btn.variant = "default"
            sel.set_options(ECO_PRESET_OPTIONS)
            valid_eco_ids = {pid for _, pid in ECO_PRESET_OPTIONS}
            if self.selected_preset_id not in valid_eco_ids:
                self.selected_preset_id = "conservative"
            sel.value = self.selected_preset_id
            self.query_one("#btn-stream-voc", Button).disabled = True
            self.query_one("#btn-stream-inst", Button).disabled = True

            self.query_one("#wb-status", Label).update(
                "Eco DSP mode active: Lightweight, cool & quiet harmonic synthesis (Zero Heat)."
            )
            self.app.notify(
                "Eco DSP Enabled: Zero GPU/MPS load, keeps device cool & fans silent.",
                title="OmniRip Eco Mode",
                timeout=3.0,
            )

        self._update_inspector()

        # Check if audition for the new preset and mode already exists
        if self.path_mp3 and self.path_mp3.exists():
            mode_tag = "neural" if self.neural_enabled else "eco"
            eq_tag = self._get_eq_cache_tag()
            cache_name = f"{self.path_mp3.stem}_{self.selected_preset_id}_{mode_tag}{eq_tag}.mp3"
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

            if self.active_stream == "ENH":
                preset = PRESETS.get(self.selected_preset_id)
                p_name = preset.name if preset else "Enhanced"
                self.query_one("#wb-status", Label).update(
                    f"Switching engine: synthesizing '{p_name}'... (current audio continues)"
                )
            self._trigger_enhancement_pregeneration()

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

        # --- All 5 models cache status ---
        all_models = ("bs_roformer", "hdemucs", "dereverb", "nvsr", "flashsr")
        missing = [m for m in all_models if not mm.is_cached(m)]
        dereverb_status = "✅ Cached & Ready" if mm.is_cached("dereverb") else "✅ DSP Engine"
        nvsr_status = "✅ Cached" if "nvsr" not in missing else "⬇ Not downloaded"
        fsr_status = "✅ Cached" if "flashsr" not in missing else "⬇ Not downloaded"

        status_summary = (
            f"AI Model Registry — "
            f"BS-RoFormer: {bsr_status}  |  "
            f"HDEMUCS: {hdemucs_status}  |  "
            f"DeReverb: {dereverb_status}  |  "
            f"NVSR: {nvsr_status}  |  "
            f"FlashSR: {fsr_status}"
        )
        self.query_one("#wb-status", Label).update(status_summary)

        all_ready = bsr_ok and hdemucs_ok and not missing
        if all_ready:
            self.app.notify(
                f"All 5 AI models ready:\n"
                f"• BS-RoFormer (Stem): {bsr_status}\n"
                f"• HDEMUCS (Stem): {hdemucs_status}\n"
                f"• De-Reverb (Acoustic): {dereverb_status}\n"
                f"• NVSR (Enhance): ✅ Cached\n"
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
            "ENH": "💾 SAVE ENHANCED",
            "VOC": "💾 SAVE VOCALS",
            "INST": "💾 SAVE INST",
        }
        try:
            self.query_one("#wb-btn-export", Button).label = labels.get(
                mode, "💾 SAVE ENHANCED"
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

    async def _async_export(self, src: Path, preset) -> None:
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
            if self._export_mode == "VOC" and self.path_voc and self.path_voc.exists():
                target_dest = out_dir / f"{src.stem}_vocals.wav"
                temp_dest = target_dest.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.wav")
                await asyncio.to_thread(shutil.copy2, self.path_voc, temp_dest)
                os.replace(temp_dest, target_dest)
                if pb:
                    pb.progress = 100.0
                self.query_one("#wb-status", Label).update(
                    f"Saved Vocals (Acapella): {target_dest.name}"
                )
                self.app.notify(f"Saved Acapella: {target_dest.name}", title="OmniRip Stems")
                return

            if self._export_mode == "INST" and self.path_inst and self.path_inst.exists():
                target_dest = out_dir / f"{src.stem}_instrumental.wav"
                temp_dest = target_dest.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.wav")
                await asyncio.to_thread(shutil.copy2, self.path_inst, temp_dest)
                os.replace(temp_dest, target_dest)
                if pb:
                    pb.progress = 100.0
                self.query_one("#wb-status", Label).update(
                    f"Saved Instrumental (Karaoke): {target_dest.name}"
                )
                self.app.notify(f"Saved Instrumental: {target_dest.name}", title="OmniRip Stems")
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
                    eq_settings=self.eq_settings,
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
