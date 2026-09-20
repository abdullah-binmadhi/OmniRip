"""
Integrated In-Page Curation & Audio Enhancement Workbench for OmniRip.

Provides in-layout stream auditioning ([1] MP3 vs [2] ENH), cutoff frequency analysis,
dynamic mastering deck, preset selection, and full-track derivative export.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import platformdirs
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
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
from harvester.analysis.enhancement.presets import PRESETS
from harvester.analysis.enhancement.stem_separator import (
    INST_REMEDIATIONS,
    VOCAL_REMEDIATIONS,
)
from harvester.models import TrackJob
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
        width: 30;
        background: $surface;
        border: round $success;
        padding: 0;
        offset: 0 3;
        layer: overlay;
    }
    #wb-export-dropdown .wb-export-choice {
        width: 1fr;
        height: 1;
        margin: 0;
        padding: 0 1;
        background: $surface;
        border: none;
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
    #wb-deck-header-row {
        height: 3;
        width: 1fr;
        align: left middle;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary;
    }
    #wb-cutoff-badge {
        width: 1fr;
        color: $warning;
        text-style: bold;
    }
    #wb-page-switch {
        width: auto;
        align: right middle;
    }
    /* Scoped by id: Textual's `Button.-style-default` tops out at specificity
       (0, 1, 1), so unscoped class rules lose the skin below to the Button default. */
    #wb-page-switch .wb-page-btn {
        height: 3;
        min-width: 10;
        margin-left: 1;
        padding: 0 1;
        border: solid $secondary;
        background: $surface;
        color: $secondary;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    #wb-page-switch .wb-page-btn:hover {
        background: $secondary;
        color: #000000;
    }
    #wb-page-switch .wb-page-btn-active {
        border: solid $primary;
        background: $primary;
        color: #ffffff;
        text-style: bold;
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
            with Vertical(id="wb-export-dropdown"):
                yield Button("🎵  Enhanced MP3",       id="wb-export-choose-enh",  classes="wb-export-choice")
                yield Button("🎤  Vocals (WAV)",        id="wb-export-choose-voc",  classes="wb-export-choice")
                yield Button("🎸  Instrumental (WAV)", id="wb-export-choose-inst", classes="wb-export-choice")

        with Vertical(id="wb-inspector-container"):
            with Horizontal(id="wb-deck-header-row"):
                yield Label(f"fc: {self.cutoff_hz / 1000.0:.1f} kHz (Cutoff)", id="wb-cutoff-badge")
                with Horizontal(id="wb-page-switch"):
                    yield Button(
                        "DECK", id="wb-btn-page-deck", classes="wb-page-btn wb-page-btn-active"
                    )
                    yield Button("EQ", id="wb-btn-page-eq", classes="wb-page-btn")
                    yield Button("STEMS", id="wb-btn-page-stems", classes="wb-page-btn")
            yield AudioVisualizer(num_bands=10, cutoff_hz=self.cutoff_hz, id="wb-visualizer")
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

                if self.active_stream == "VOC":
                    self._route_to_player(
                        self.path_voc,
                        title=f"[VOC] Isolated Vocals ({track_name})",
                        is_enhanced=True,
                    )
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{res.engine.upper()}]: Auditioning Vocals"
                    )
                elif self.active_stream == "INST":
                    self._route_to_player(
                        self.path_inst,
                        title=f"[INST] Karaoke Backing ({track_name})",
                        is_enhanced=True,
                    )
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{res.engine.upper()}]: Auditioning Karaoke"
                    )
                else:
                    self.query_one("#wb-status", Label).update(
                        f"Stems Ready [{res.engine.upper()}]: Vocals & Instrumental"
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
        """Switch between 'deck', 'eq', and 'stems' tabs inside the inspector container."""
        self.active_page = page_id
        try:
            btn_deck = self.query_one("#wb-btn-page-deck", Button)
            btn_eq = self.query_one("#wb-btn-page-eq", Button)
            btn_stems = self.query_one("#wb-btn-page-stems", Button)
            page_deck = self.query_one("#wb-page-deck", Vertical)
            page_eq = self.query_one("#wb-page-eq", Vertical)
            page_stems = self.query_one("#wb-page-stems", Vertical)

            # Update button active styles
            for btn, pid in ((btn_deck, "deck"), (btn_eq, "eq"), (btn_stems, "stems")):
                if page_id == pid:
                    btn.add_class("wb-page-btn-active")
                else:
                    btn.remove_class("wb-page-btn-active")

            # Update page containers display
            page_deck.styles.display = "block" if page_id == "deck" else "none"
            page_eq.styles.display = "block" if page_id == "eq" else "none"
            page_stems.styles.display = "block" if page_id == "stems" else "none"

            if page_id == "eq":
                self._update_eq_ui()
            elif page_id == "stems":
                if self.active_stream not in ("VOC", "INST"):
                    self.set_active_stream("VOC")
                else:
                    self._update_blend_ui()
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
            vis = self.query_one("#wb-visualizer", AudioVisualizer)
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
        elif btn_id == "wb-btn-page-deck":
            self.switch_page("deck")
        elif btn_id == "wb-btn-page-eq":
            self.switch_page("eq")
        elif btn_id == "wb-btn-page-stems":
            self.switch_page("stems")
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
            dd = self.query_one("#wb-export-dropdown", Vertical)
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
            self.query_one("#wb-status", Label).update(f"Downloaded: {out_path.name}")
            self.app.notify(
                f"Downloaded Enhanced MP3: {out_path.name}\n"
                f"Preset: {preset.name}\nFolder: {out_dir}",
                title="OmniRip Enhanced Download",
                timeout=5.0,
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
