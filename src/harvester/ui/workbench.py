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
from typing import TYPE_CHECKING, Literal

import platformdirs
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar, Select

from harvester.analysis.enhancement.eq import (
    EQ_FREQUENCIES,
    EQ_PRESETS,
    MasteringEQSettings,
)
from harvester.analysis.enhancement.presets import PRESETS
from harvester.models import TrackJob
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.services.enhancement.preview import PreviewManager
from harvester.ui.visualizer import AudioVisualizer

if TYPE_CHECKING:
    from harvester.ui.player import AudioPlayerWidget

logger = logging.getLogger(__name__)

StreamId = Literal["MP3", "ENH", "A", "B", "C"]

ECO_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("Conservative DSP", "conservative"),
    ("Fast Neural (Balanced)", "fast_balanced"),
]

AI_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("Milder Highs (De-Sizzle)", "de_sizzle"),
    ("Extended Air (Hybrid)", "extended_air"),
    ("Narrow Residual (Headphone Safe)", "narrow_stereo"),
]


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
    #wb-btn-export {
        width: auto;
        min-width: 22;
        padding: 0 1;
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
    .wb-page-btn {
        height: 3;
        min-width: 10;
        margin-left: 1;
        padding: 0 1;
        border: solid $secondary;
        background: $surface;
        color: $secondary;
        text-style: bold;
    }
    .wb-page-btn:hover {
        background: $secondary;
        color: #000000;
    }
    .wb-page-btn-active {
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
    .wb-eq-btn-up, .wb-eq-btn-dn {
        height: 1;
        min-width: 4;
        width: 5;
        padding: 0;
        margin: 0;
        border: solid $secondary;
        background: $surface;
        color: $secondary;
        text-style: bold;
    }
    .wb-eq-btn-up:hover, .wb-eq-btn-dn:hover {
        background: $secondary;
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
        height: 1;
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
    #wb-blend-row {
        height: auto;
        width: 1fr;
        margin-top: 1;
        align: left middle;
    }
    .wb-blend-label {
        width: 1fr;
        height: 1;
        color: $accent;
        text-style: bold;
    }
    .wb-blend-val {
        width: 6;
        height: 1;
        text-align: center;
        color: $warning;
        text-style: bold;
    }
    .wb-blend-btn {
        height: 1;
        min-width: 3;
        width: 3;
        padding: 0;
        margin: 0 0 0 1;
        border: solid $secondary;
        background: $surface;
        color: $secondary;
        text-style: bold;
    }
    .wb-blend-btn:hover {
        background: $secondary;
        color: #000000;
    }
    #wb-status {
        height: 1;
        color: $warning;
        margin-top: 1;
    }
    .wb-diagnostic-row {
        height: auto;
        width: 1fr;
        margin-top: 1;
        display: none;
        align: left middle;
    }
    .wb-diagnostic-label {
        width: 12;
        height: 1;
        color: $accent;
        text-style: bold;
    }
    .wb-diagnostic-select {
        width: 1fr;
        height: auto;
    }
    """

    active_stream: reactive[StreamId] = reactive("MP3")
    current_job: reactive[TrackJob | None] = reactive(None)
    cutoff_hz: reactive[float] = reactive(15500.0)

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

        # Imperfection remediation diagnostic profiles:
        # Vocal: "natural", "fix_pumping", "de_robot", "air_boost"
        # Instrumental: "natural", "kill_whispers", "restore_center", "preserve_drums"
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
            yield Button("SAVE ENHANCED", id="wb-btn-export", variant="success")

        with Vertical(id="wb-inspector-container"):
            with Horizontal(id="wb-deck-header-row"):
                yield Label(f"fc: {self.cutoff_hz / 1000.0:.1f} kHz (Cutoff)", id="wb-cutoff-badge")
                with Horizontal(id="wb-page-switch"):
                    yield Button(
                        "DECK", id="wb-btn-page-deck", classes="wb-page-btn wb-page-btn-active"
                    )
                    yield Button("EQ", id="wb-btn-page-eq", classes="wb-page-btn")
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

                # --- Stem Blend Weight Controls ---
                yield Label(
                    "STEM BLEND  [0% = Cleanest Separation  ·  100% = Richest Texture]",
                    classes="wb-section-title",
                )
                with Horizontal(id="wb-blend-row"):
                    yield Label("BS-RoFormer:", classes="wb-blend-label")
                    yield Label(
                        f"{int(self.stem_bsr_blend * 100)}%",
                        id="wb-blend-bsr-val",
                        classes="wb-blend-val",
                    )
                    yield Button("+", id="wb-blend-bsr-up", classes="wb-blend-btn")
                    yield Button("-", id="wb-blend-bsr-dn", classes="wb-blend-btn")
                    yield Label("  HDEMUCS:", classes="wb-blend-label")
                    yield Label(
                        f"{int(self.stem_hdemucs_blend * 100)}%",
                        id="wb-blend-hdemucs-val",
                        classes="wb-blend-val",
                    )
                    yield Button("+", id="wb-blend-hdemucs-up", classes="wb-blend-btn")
                    yield Button("-", id="wb-blend-hdemucs-dn", classes="wb-blend-btn")

                # --- Stem Imperfection Remediation Diagnostic Controls ---
                with Horizontal(id="wb-diagnostic-voc-row", classes="wb-diagnostic-row"):
                    yield Label("Vocal Fix:", classes="wb-diagnostic-label")
                    yield Select(
                        [
                            ("Standard Polish (Natural Envelope)", "natural"),
                            ("Fix Volume Pumping (Bypass Gate)", "fix_pumping"),
                            ("De-Robotize (Phase Smoothing)", "de_robot"),
                            ("Restore Air & Highs (+2.5dB >8kHz)", "air_boost"),
                        ],
                        value=self.vocal_profile,
                        id="wb-diagnostic-voc-select",
                        allow_blank=False,
                        classes="wb-diagnostic-select",
                    )
                with Horizontal(id="wb-diagnostic-inst-row", classes="wb-diagnostic-row"):
                    yield Label("Inst Fix:", classes="wb-diagnostic-label")
                    yield Select(
                        [
                            ("Standard Blend (Natural De-Bleed)", "natural"),
                            (
                                "Kill Vocal Bleed & Whispers (Stereo Side Attenuation)",
                                "kill_whispers",
                            ),
                            ("Restore Center Punch (Kick & Snare)", "restore_center"),
                            ("Preserve Drums & Percussion", "preserve_drums"),
                        ],
                        value=self.inst_profile,
                        id="wb-diagnostic-inst-select",
                        allow_blank=False,
                        classes="wb-diagnostic-select",
                    )

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

        yield ProgressBar(id="wb-download-progress", total=100, show_eta=True)
        yield Label("", id="wb-status")

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
                from harvester.analysis.enhancement.stem_separator import load_stem_profile

                prof = load_stem_profile(stem_dir)
                self.vocal_profile = prof.get("vocal_profile", "natural")
                self.inst_profile = prof.get("inst_profile", "natural")
                try:
                    self.query_one("#wb-diagnostic-voc-select", Select).value = self.vocal_profile
                    self.query_one("#wb-diagnostic-inst-select", Select).value = self.inst_profile
                except Exception:
                    pass

            v_sfx = f"_{self.vocal_profile}" if self.vocal_profile != "natural" else ""
            i_sfx = f"_{self.inst_profile}" if self.inst_profile != "natural" else ""

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

            stereo_pct = int(round(stereo_width * 100))
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
                engine_display = f"🌱 Eco DSP ({engine_str} - Cool & Zero Heat)"
            else:
                engine_display = f"⚡ Neural AI ({engine_str} - Accelerated)"
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

            # Signal Chain Pipeline
            flow_str = (
                f"[cyan]\\[1. Baseband 0..{cutoff_khz:.1f}k\\][/cyan] ──> "
                f"[magenta]\\[2. FIR Split\\][/magenta] ──> "
                f"[yellow]\\[3. {preset_name}\\][/yellow] ──> "
                f"[blue]\\[4. Stereo ({stereo_pct}%)\\][/blue] ──> "
                f"[green]\\[5. Limiter {ceiling:.1f}dBFS\\][/green]"
            )
            self.query_one("#wb-chain-flow", Label).update(f"  {flow_str}")
            active_flag = (
                "[bold green]LIVE AUDITION RESTORED[/bold green]"
                if is_enh
                else "[bold cyan]LIVE AUDITION ORIGINAL BASEBAND[/bold cyan]"
            )
            self.query_one("#wb-chain-detail", Label).update(
                f"  [dim]Engine: {engine_display} • Status: [/dim]{active_flag}"
            )

            # Mastering & Provenance Telemetry
            self.query_one("#wb-telem-nyquist", Label).update(
                "• Nyquist Headroom : [bold green]22.05 kHz[/bold green] "
                "[dim](Full-Band Restoration)[/dim]"
            )
            self.query_one("#wb-telem-crossover", Label).update(
                "• Crossover Filter : [bold cyan]384-tap FIR[/bold cyan] "
                f"[dim](Phase Linear @ {cutoff_khz:.2f}k)[/dim]"
            )
            self.query_one("#wb-telem-passthrough", Label).update(
                "• Sub-Cutoff Audio : [bold green]Bit-Exact Passthrough[/bold green] "
                "[dim](100% Preserved)[/dim]"
            )
            self.query_one("#wb-telem-limiter", Label).update(
                f"• Limiter Ceiling  : [bold yellow]{ceiling:.1f} dBFS[/bold yellow] "
                "[dim](ITU-R BS.1770 Guard)[/dim]"
            )
            self.query_one("#wb-telem-format", Label).update(
                "• Export Encoding  : [bold]320 kbps CBR MP3[/bold] "
                "[dim](ID3v2 TXXX Provenance)[/dim]"
            )
            dest_folder = "~/Music/Harvested"
            if (
                hasattr(self.app, "config")
                and hasattr(self.app.config, "general")
                and self.app.config.general.output_dir
            ):
                dest_folder = str(self.app.config.general.output_dir)
            elif self.current_job and self.current_job.output_path:
                dest_folder = str(self.current_job.output_path.parent)
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

            voc_row = self.query_one("#wb-diagnostic-voc-row")
            inst_row = self.query_one("#wb-diagnostic-inst-row")
            blend_row = self.query_one("#wb-blend-row")
            if normalized == "VOC":
                voc_row.styles.display = "block"
                inst_row.styles.display = "none"
                blend_row.styles.display = "block"
            elif normalized == "INST":
                voc_row.styles.display = "none"
                inst_row.styles.display = "block"
                blend_row.styles.display = "block"
            else:
                voc_row.styles.display = "none"
                inst_row.styles.display = "none"
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

    def _trigger_stem_separation(self, target_stream: str = "VOC") -> None:
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
        asyncio.create_task(self._async_separate_stems(self.path_mp3, target_stream))

    async def _async_separate_stems(self, source_path: Path, target_stream: str) -> None:
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
            from harvester.analysis.enhancement.stem_separator import StemSeparator

            separator = StemSeparator()
            res = await asyncio.to_thread(
                separator.separate_file,
                source_path,
                mode="neural",
                progress_callback=on_progress,
                bs_roformer_weight=self.stem_bsr_blend,
                hdemucs_weight=self.stem_hdemucs_blend,
                vocal_profile=self.vocal_profile,
                inst_profile=self.inst_profile,
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
        """Switch between 'deck' and 'eq' tabs inside the inspector container."""
        self.active_page = page_id
        try:
            btn_deck = self.query_one("#wb-btn-page-deck", Button)
            btn_eq = self.query_one("#wb-btn-page-eq", Button)
            page_deck = self.query_one("#wb-page-deck", Vertical)
            page_eq = self.query_one("#wb-page-eq", Vertical)

            if page_id == "deck":
                btn_deck.label = "DECK"
                btn_deck.add_class("wb-page-btn-active")
                btn_eq.label = "EQ"
                btn_eq.remove_class("wb-page-btn-active")
                page_deck.styles.display = "block"
                page_eq.styles.display = "none"
            else:
                btn_deck.label = "DECK"
                btn_deck.remove_class("wb-page-btn-active")
                btn_eq.label = "EQ"
                btn_eq.add_class("wb-page-btn-active")
                page_deck.styles.display = "none"
                page_eq.styles.display = "block"
                self._update_eq_ui()
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
        elif btn_id == "wb-btn-neural-toggle":
            self.toggle_neural_engine()
        elif btn_id == "wb-btn-models-download":
            self.trigger_models_download()
        elif btn_id == "wb-btn-export":
            self._export_derivative()
        elif btn_id == "wb-btn-page-deck":
            self.switch_page("deck")
        elif btn_id == "wb-btn-page-eq":
            self.switch_page("eq")
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

    def _update_blend_ui(self) -> None:
        """Refresh blend weight value labels after a change."""
        try:
            self.query_one("#wb-blend-bsr-val", Label).update(f"{int(self.stem_bsr_blend * 100)}%")
            self.query_one("#wb-blend-hdemucs-val", Label).update(
                f"{int(self.stem_hdemucs_blend * 100)}%"
            )
            bsr_desc = (
                "Richest Texture"
                if self.stem_bsr_blend >= 0.8
                else ("Balanced" if self.stem_bsr_blend >= 0.4 else "Cleanest")
            )
            hd_desc = (
                "Richest Texture"
                if self.stem_hdemucs_blend >= 0.8
                else ("Balanced" if self.stem_hdemucs_blend >= 0.4 else "Cleanest")
            )
            self.query_one("#wb-status", Label).update(
                f"Blend — BS-RoFormer: {int(self.stem_bsr_blend * 100)}% texture ({bsr_desc})  |  "
                f"HDEMUCS: {int(self.stem_hdemucs_blend * 100)}% texture ({hd_desc})"
                f"  · 0%=Clean separation · 100%=Rich instruments"
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

        from harvester.services.model_manager import SUPPORTED_MODELS, ModelManager

        mm = ModelManager()

        # --- Stem separation model availability (self-managed) ---
        bsr_ok = (
            importlib.util.find_spec("demucs") is not None
            or importlib.util.find_spec("transformers") is not None
        )
        hdemucs_ok = importlib.util.find_spec("demucs") is not None
        bsr_status = "✅ Available" if bsr_ok else "⚠ Needs: pip install transformers"
        hdemucs_status = "✅ Available" if hdemucs_ok else "⚠ Needs: pip install demucs"

        # --- Enhancement model cache status ---
        missing = [m for m in SUPPORTED_MODELS if not mm.is_cached(m)]
        nvsr_status = "✅ Cached" if "nvsr" not in missing else "⬇ Not downloaded"
        fsr_status = "✅ Cached" if "flashsr" not in missing else "⬇ Not downloaded"

        status_summary = (
            f"AI Model Registry — "
            f"BS-RoFormer: {bsr_status}  |  "
            f"HDEMUCS: {hdemucs_status}  |  "
            f"NVSR: {nvsr_status}  |  "
            f"FlashSR: {fsr_status}"
        )
        self.query_one("#wb-status", Label).update(status_summary)

        all_ready = bsr_ok and hdemucs_ok and not missing
        if all_ready:
            self.app.notify(
                f"All 4 AI models ready:\n"
                f"• BS-RoFormer (Stem): {bsr_status}\n"
                f"• HDEMUCS (Stem): {hdemucs_status}\n"
                f"• NVSR (Enhance): ✅ Cached\n"
                f"• FlashSR (Enhance): ✅ Cached",
                title="OmniRip AI Models",
                timeout=6.0,
            )
            return

        install_demucs = not hdemucs_ok
        if not missing and not install_demucs:
            self.app.notify(
                f"OmniRip AI Model Status:\n"
                f"• BS-RoFormer (Stem): {bsr_status}\n"
                f"• HDEMUCS (Stem): {hdemucs_status}\n"
                f"• NVSR (Enhance): {nvsr_status}\n"
                f"• FlashSR (Enhance): {fsr_status}",
                title="OmniRip AI Models",
                timeout=6.0,
            )
            return

        tasks_desc: list[str] = []
        if install_demucs:
            tasks_desc.append("Demucs stem engine")
        if missing:
            tasks_desc.append(f"Enhancement weights ({', '.join(missing)})")

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
                    f"Downloading {model_name.upper()} weights from Hugging Face..."
                )
                await asyncio.to_thread(mm.download_model, model_name)
            self.query_one("#wb-status", Label).update(
                "All neural models and weights configured successfully!"
            )
            self.app.notify(
                "Model download complete! Neural weights are now cached.",
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

    def _export_derivative(self) -> None:
        src = self.path_mp3
        if not src or not src.exists():
            self.query_one("#wb-status", Label).update("No audio file available to download.")
            return

        preset = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
        if self.active_stream == "VOC":
            self.query_one("#wb-status", Label).update("Saving Isolated Vocals (Acapella)...")
        elif self.active_stream == "INST":
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
            if self.current_job and self.current_job.output_path:
                out_dir = self.current_job.output_path.parent
            elif (
                hasattr(self.app, "config")
                and hasattr(self.app.config, "general")
                and self.app.config.general.output_dir
            ):
                out_dir = Path(self.app.config.general.output_dir)
            else:
                from harvester.config import load_config

                out_dir = Path(load_config().general.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            # Handle isolated stem export if active stream is VOC or INST
            if self.active_stream == "VOC" and self.path_voc and self.path_voc.exists():
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

            if self.active_stream == "INST" and self.path_inst and self.path_inst.exists():
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
