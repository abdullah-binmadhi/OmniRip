"""
Integrated In-Page Curation & Audio Enhancement Workbench for OmniRip.

Provides in-layout A/B/C stream auditioning, cutoff frequency analysis,
preset selection, live spectrum visualization, and one-click derivative export.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Select

from harvester.analysis.enhancement.presets import PRESETS
from harvester.models import TrackJob
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.services.enhancement.preview import PreviewManager
from harvester.ui.visualizer import AudioVisualizer

if TYPE_CHECKING:
    from harvester.ui.player import AudioPlayerWidget

StreamId = Literal["A", "B", "C"]


class WorkbenchWidget(Widget):
    """
    In-page audio enhancement and auditioning workbench panel.
    Supports real-time A/B/C testing:
      [A] ORIGINAL : Source audio (YouTube Opus / raw file)
      [B] MP3      : Transcoded output (e.g. 320k MP3)
      [C] ENHANCED : Restored derivative with neural/DSP high band
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
    #wb-abc-row {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-bottom: 1;
    }
    #wb-abc-row Button {
        min-width: 14;
        margin-right: 1;
    }
    #wb-controls-row {
        height: 3;
        width: 1fr;
        align: left middle;
        margin-bottom: 1;
    }
    #wb-preset-select {
        width: 28;
        margin-right: 1;
    }
    #wb-btn-export {
        width: 24;
    }
    #wb-status {
        height: 1;
        color: $warning;
        margin-top: 1;
    }
    #wb-vis-container {
        height: 1fr;
        min-height: 5;
        border: round $secondary;
        background: $surface;
        padding: 0;
    }
    """

    active_stream: reactive[StreamId] = reactive("B")
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
        self.exporter = EnhancementExporter()
        self.selected_preset_id: str = "conservative"

        # Stream paths: A (Original), B (MP3), C (Enhanced)
        self.path_a: Path | None = None
        self.path_b: Path | None = None
        self.path_c: Path | None = None

    def compose(self) -> ComposeResult:
        yield Label("CURATION & ENHANCEMENT WORKBENCH", id="wb-header")
        yield Label("No track selected — click a track in the table above", id="wb-track-meta")
        yield Label("Cutoff fc: -- kHz | State: IDLE", id="wb-cutoff-info")

        with Horizontal(id="wb-abc-row"):
            yield Button("[A] ORIGINAL", id="btn-stream-a", variant="default")
            yield Button("[B] MP3", id="btn-stream-b", variant="primary")
            yield Button("[C] ENHANCED", id="btn-stream-c", variant="default")

        with Horizontal(id="wb-controls-row"):
            options = [(preset.name, preset.id) for preset in PRESETS.values()]
            yield Select(options=options, value=self.selected_preset_id, id="wb-preset-select")
            yield Button("[EXPORT ENHANCED MP3]", id="wb-btn-export", variant="success")

        with Vertical(id="wb-vis-container"):
            yield AudioVisualizer(num_bands=24, cutoff_hz=self.cutoff_hz, id="wb-visualizer")

        yield Label("", id="wb-status")

    def load_job(self, job: TrackJob) -> None:
        """Load a track job into the workbench and resolve its A/B/C streams."""
        self.current_job = job
        cutoff = job.spectral.cutoff_hz if (job.spectral and job.spectral.cutoff_hz) else 15500.0
        self.cutoff_hz = cutoff

        # Stream A: Raw original/downloaded audio (Opus/source)
        wp = job.workspace_path
        self.path_a = wp if (wp and wp.exists()) else None
        if not self.path_a and job.input_path and job.input_path.exists():
            self.path_a = job.input_path

        # Stream B: Transcoded MP3 output
        self.path_b = job.output_path if (job.output_path and job.output_path.exists()) else None

        # Stream C: Enhanced file if already exported
        if self.path_b:
            candidate_c = self.path_b.with_suffix(".enhanced.mp3")
            self.path_c = candidate_c if candidate_c.exists() else None
        else:
            self.path_c = None

        # Update metadata display
        name = job.display_name
        self.query_one("#wb-track-meta", Label).update(f"TRACK: {name}")
        self.query_one("#wb-cutoff-info", Label).update(
            f"Cutoff fc: {cutoff / 1000.0:.1f} kHz | Verdict: {job.spectral.verdict.value.upper()}"
        )

        vis = self.query_one("#wb-visualizer", AudioVisualizer)
        vis.set_cutoff(cutoff)

        # Default to B (MP3) or A if available
        if self.path_b:
            self.set_active_stream("B")
        elif self.path_a:
            self.set_active_stream("A")

    def set_active_stream(self, stream: StreamId) -> None:
        """Switch audition stream between A (Original), B (MP3), and C (Enhanced)."""
        self.active_stream = stream
        target_path: Path | None = None
        stream_name = ""

        btn_a = self.query_one("#btn-stream-a", Button)
        btn_b = self.query_one("#btn-stream-b", Button)
        btn_c = self.query_one("#btn-stream-c", Button)

        btn_a.variant = "primary" if stream == "A" else "default"
        btn_b.variant = "primary" if stream == "B" else "default"
        btn_c.variant = "primary" if stream == "C" else "default"

        if stream == "A":
            target_path = self.path_a
            stream_name = "Original (Source Stream)"
        elif stream == "B":
            target_path = self.path_b
            stream_name = "Transcoded (MP3)"
        elif stream == "C":
            stream_name = f"Enhanced ({PRESETS[self.selected_preset_id].name})"
            if self.path_c and self.path_c.exists():
                target_path = self.path_c
            elif self.path_b or self.path_a:
                # Render preview slice or derivative on the fly
                self._render_stream_c()
                return

        status = self.query_one("#wb-status", Label)
        if target_path and target_path.exists():
            status.update(f"Auditioning [{stream}]: {stream_name} ({target_path.name})")
            self._route_to_player(target_path, title=f"[{stream}] {stream_name}")
        else:
            status.update(f"Stream [{stream}] not found on disk yet.")

    def _render_stream_c(self) -> None:
        """Render enhanced preview slice for stream C if not already available."""
        src = self.path_b or self.path_a
        if not src or not src.exists():
            self.query_one("#wb-status", Label).update("No base audio available to enhance.")
            return

        preset = PRESETS[self.selected_preset_id]
        self.query_one("#wb-status", Label).update(
            f"Rendering enhanced preview with '{preset.name}'..."
        )
        self.run_worker(self._async_render_c(src, preset), name="render-stream-c")

    async def _async_render_c(self, src: Path, preset) -> None:
        try:
            _orig_wav, enh_wav = await asyncio.to_thread(
                self.preview_manager.generate_preview_pair,
                src,
                preset=preset,
                cutoff_hz=self.cutoff_hz,
            )
            self.path_c = enh_wav
            self.query_one("#wb-status", Label).update(
                f"Auditioning [C]: Enhanced ({preset.name})"
            )
            self._route_to_player(self.path_c, title=f"[C] Enhanced ({preset.name})")
        except Exception as exc:
            self.query_one("#wb-status", Label).update(f"Enhance failed: {exc}")

    def _route_to_player(self, audio_path: Path, title: str) -> None:
        """Load audio into the main player and visualizer."""
        try:
            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
            was_playing = player.is_playing
            player.load_track(audio_path, title=title, cutoff_hz=self.cutoff_hz)
            if was_playing:
                player.play()
        except Exception:
            pass

        # Also update the workbench embedded visualizer
        vis = self.query_one("#wb-visualizer", AudioVisualizer)
        vis.set_cutoff(self.cutoff_hz)
        self.run_worker(asyncio.to_thread(vis.load_audio_frames, audio_path), name="vis-load")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "wb-preset-select" and event.value is not None:
            self.selected_preset_id = str(event.value)
            # Invalidate cached C stream to re-render with new preset
            self.path_c = None
            if self.active_stream == "C":
                self.set_active_stream("C")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-stream-a":
            self.set_active_stream("A")
        elif event.button.id == "btn-stream-b":
            self.set_active_stream("B")
        elif event.button.id == "btn-stream-c":
            self.set_active_stream("C")
        elif event.button.id == "wb-btn-export":
            self._export_derivative()

    def _export_derivative(self) -> None:
        src = self.path_b or self.path_a
        if not src or not src.exists():
            self.query_one("#wb-status", Label).update("No audio file available to export.")
            return

        preset = PRESETS[self.selected_preset_id]
        self.query_one("#wb-status", Label).update(f"Exporting MP3 with '{preset.name}'...")
        self.run_worker(self._async_export(src, preset), name="export-derivative")

    async def _async_export(self, src: Path, preset) -> None:
        try:
            out_path = await asyncio.to_thread(
                self.exporter.export_enhanced_derivative,
                input_path=src,
                preset=preset,
                cutoff_hz=self.cutoff_hz,
            )
            self.path_c = out_path
            self.query_one("#wb-status", Label).update(f"Exported: {out_path.name}")
            self.app.notify(f"Exported: {out_path.name}", timeout=3.0)
            if self.on_exported:
                self.on_exported(out_path)
        except Exception as exc:
            self.query_one("#wb-status", Label).update(f"Export error: {exc}")
            self.app.notify(f"Export error: {exc}", severity="error")
