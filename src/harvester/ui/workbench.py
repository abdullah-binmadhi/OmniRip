"""
Integrated In-Page Curation & Audio Enhancement Workbench for OmniRip.

Provides in-layout stream auditioning ([1] MP3 vs [2] ENH), cutoff frequency analysis,
dynamic mastering deck, preset selection, and full-track derivative export.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import platformdirs
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

StreamId = Literal["MP3", "ENH", "A", "B", "C"]


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
        min-width: 14;
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
        min-width: 20;
        margin-right: 1;
    }
    #wb-btn-export {
        width: auto;
        min-width: 16;
        padding: 0 1;
    }
    #wb-inspector-container {
        height: 1fr;
        min-height: 14;
        border: round $secondary;
        background: $surface;
        padding: 0;
    }
    #wb-inspector-body {
        height: 1fr;
        min-height: 14;
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
    .wb-spec-line {
        height: 1;
        color: $text;
    }
    #wb-status {
        height: 1;
        color: $warning;
        margin-top: 1;
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

        # Stream paths: MP3 (Original) and ENH (Enhanced derivative)
        self.path_mp3: Path | None = None
        self.path_enh: Path | None = None
        self._is_generating_enh: bool = False

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
            yield Button("[1] ♫ MP3", id="btn-stream-mp3", variant="primary")
            yield Button("[2] ✦ ENH", id="btn-stream-enh", variant="default")

        with Horizontal(id="wb-controls-row"):
            options = [(preset.name, preset.id) for preset in PRESETS.values()]
            yield Select(options=options, value=self.selected_preset_id, id="wb-preset-select")
            yield Button("🌱 ECO MODE", id="wb-btn-neural-toggle", variant="default")
            yield Button("📥 AI MODELS", id="wb-btn-models-download", variant="default")
            yield Button("⤓ DOWNLOAD ENHANCED", id="wb-btn-export", variant="success")

        with Vertical(id="wb-inspector-container"):
            yield AudioVisualizer(num_bands=24, cutoff_hz=self.cutoff_hz, id="wb-visualizer")
            with Vertical(id="wb-inspector-body"):
                yield Label("✦ RESTORATION MASTERING DECK", id="wb-inspector-title")
                yield Label("", id="wb-gauge-orig")
                yield Label("", id="wb-gauge-enh")
                yield Label("", id="wb-spec-cutoff", classes="wb-spec-line")
                yield Label("", id="wb-spec-bandwidth", classes="wb-spec-line")
                yield Label("", id="wb-spec-gain", classes="wb-spec-line")
                yield Label("", id="wb-spec-trim", classes="wb-spec-line")
                yield Label("", id="wb-spec-slope", classes="wb-spec-line")
                yield Label("", id="wb-spec-stereo", classes="wb-spec-line")
                yield Label("", id="wb-spec-base", classes="wb-spec-line")
                yield Label("", id="wb-spec-ceiling", classes="wb-spec-line")
                yield Label("", id="wb-spec-engine", classes="wb-spec-line")
                yield Label("", id="wb-spec-stream", classes="wb-spec-line")
                yield Label("", id="wb-spec-profile-header", classes="wb-spec-line")
                yield Label("", id="wb-spec-profile-desc", classes="wb-spec-line")

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

        # Check if enhanced derivative is available (exported or in audition cache)
        if self.path_mp3:
            candidate_enh = self.path_mp3.with_suffix(".enhanced.mp3")
            cached_audition = (
                self.audition_cache_dir / f"{self.path_mp3.stem}_{self.selected_preset_id}.mp3"
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
                f"✦ MASTERING DECK // {preset_name.upper()}"
            )

            # Clean frequency expansion diagram without bracket leaks or overflow
            self.query_one("#wb-gauge-orig", Label).update(
                f"[bold cyan]Baseband:[/bold cyan] [cyan]0k ═════ "
                f"{cutoff_khz:.1f}k[/cyan] [red]── CUTOFF ── 22k[/red]"
            )
            self.query_one("#wb-gauge-enh", Label).update(
                f"[bold green]Restored:[/bold green] [cyan]0k ═════ "
                f"{cutoff_khz:.1f}k[/cyan] [bold green]✦✦✦✦✦✦ 22.05k[/bold green]"
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
                "[bold green]✦ NEURAL RESTORED ACTIVE (A/B)[/bold green]"
                if is_enh
                else "[bold cyan]♫ MP3 ORIGINAL BASEBAND (A/B)[/bold cyan]"
            )
            self.query_one("#wb-spec-stream", Label).update(f"• Active Stream : {stream_style}")

            # Wrapped profile description to utilize bottom space
            words = description.split()
            w1: list[str] = []
            w2: list[str] = []
            cur_l = 0
            for w in words:
                if cur_l + len(w) + 1 <= 36 and not w2:
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
        except Exception:
            pass

    def set_active_stream(self, stream: StreamId) -> None:
        """Switch audition stream between [1] MP3 (Original) and [2] ENH (Restored)."""
        normalized: StreamId = "ENH" if stream in ("ENH", "C") else "MP3"
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

        if normalized == "MP3":
            if self.path_mp3 and self.path_mp3.exists():
                self._route_to_player(
                    self.path_mp3,
                    title=f"[♫ MP3] {self.path_mp3.name}",
                    is_enhanced=False,
                )
                self.query_one("#wb-status", Label).update("Auditioning [♫ MP3]: Original Audio")
            else:
                self.query_one("#wb-status", Label).update("MP3 stream not found on disk.")
        elif normalized == "ENH":
            if self.path_enh and self.path_enh.exists():
                self._route_to_player(
                    self.path_enh,
                    title=f"[✦ ENH] Neural Restored ({p_name})",
                    is_enhanced=True,
                    preset_name=p_name,
                )
                self.query_one("#wb-status", Label).update(
                    f"Auditioning [✦ ENH]: Neural Restored ({p_name})"
                )
            elif self.path_mp3 and self.path_mp3.exists():
                self.query_one("#wb-status", Label).update(
                    f"✦ Synthesizing neural restoration with '{p_name}'..."
                )
                self._trigger_enhancement_pregeneration()

        self._update_inspector()

    def _trigger_enhancement_pregeneration(self) -> None:
        """Asynchronously pre-generate the enhanced derivative."""
        src = self.path_mp3
        if not src or not src.exists() or self._is_generating_enh:
            return

        preset = PRESETS.get(self.selected_preset_id) or PRESETS["conservative"]
        self._is_generating_enh = True
        self.run_worker(self._async_render_enh(src, preset), name="render-stream-enh")

    async def _async_render_enh(self, src: Path, preset) -> None:
        try:
            mode_tag = "neural" if self.neural_enabled else "eco"
            cache_dest = self.audition_cache_dir / f"{src.stem}_{preset.id}_{mode_tag}.mp3"
            out_path = await asyncio.to_thread(
                self.exporter.export_enhanced_derivative,
                input_path=src,
                preset=preset,
                output_path=cache_dest,
                cutoff_hz=self.cutoff_hz,
            )
            self.path_enh = out_path
            self._is_generating_enh = False

            # If user has ENH active, immediately switch playback to the restored audio!
            if self.active_stream == "ENH":
                self._route_to_player(
                    self.path_enh,
                    title=f"[✦ ENH] Neural Restored ({preset.name})",
                    is_enhanced=True,
                    preset_name=preset.name,
                )
                self.query_one("#wb-status", Label).update(
                    f"Auditioning [✦ ENH]: Neural Restored ({preset.name})"
                )
            self._update_inspector()
        except Exception as exc:
            self._is_generating_enh = False
            self.query_one("#wb-status", Label).update(f"Enhance failed: {exc}")

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
            self.run_worker(asyncio.to_thread(vis.load_audio_frames, audio_path), name="vis-load")
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "wb-preset-select" and event.value is not None:
            self.selected_preset_id = str(event.value)
            self._update_inspector()

            # If audition file for this preset is already cached, reuse it instantly!
            if self.path_mp3:
                mode_tag = "neural" if self.neural_enabled else "eco"
                cache_name = f"{self.path_mp3.stem}_{self.selected_preset_id}_{mode_tag}.mp3"
                cached_audition = self.audition_cache_dir / cache_name
                if cached_audition.exists():
                    self.path_enh = cached_audition
                    if self.active_stream == "ENH":
                        preset = PRESETS.get(self.selected_preset_id)
                        p_name = preset.name if preset else "Enhanced"
                        self._route_to_player(
                            self.path_enh,
                            title=f"[✦ ENH] Neural Restored ({p_name})",
                            is_enhanced=True,
                            preset_name=p_name,
                        )
                        self.query_one("#wb-status", Label).update(
                            f"Auditioning [✦ ENH]: Neural Restored ({p_name})"
                        )
                    return

            self.path_enh = None
            self._trigger_enhancement_pregeneration()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-stream-mp3", "btn-stream-a", "btn-stream-b"):
            self.set_active_stream("MP3")
        elif event.button.id in ("btn-stream-enh", "btn-stream-c"):
            self.set_active_stream("ENH")
        elif event.button.id == "wb-btn-neural-toggle":
            self.toggle_neural_engine()
        elif event.button.id == "wb-btn-models-download":
            self.trigger_models_download()
        elif event.button.id == "wb-btn-export":
            self._export_derivative()

    def toggle_neural_engine(self) -> None:
        """Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode."""
        self.neural_enabled = not self.neural_enabled
        self.exporter.set_neural_enabled(self.neural_enabled)

        btn = self.query_one("#wb-btn-neural-toggle", Button)
        if self.neural_enabled:
            btn.label = "⚡ NEURAL AI"
            btn.variant = "warning"
            self.query_one("#wb-status", Label).update(
                "⚡ Neural AI mode active: Deep neural models enabled."
            )
            self.app.notify(
                "⚡ Neural AI Enabled: Deep models will be used when available.",
                title="OmniRip Neural Mode",
                timeout=3.0,
            )
        else:
            btn.label = "🌱 ECO MODE"
            btn.variant = "default"
            self.query_one("#wb-status", Label).update(
                "🌱 Eco DSP mode active: Lightweight, cool & quiet harmonic synthesis (Zero Heat)."
            )
            self.app.notify(
                "🌱 Eco DSP Enabled: Zero GPU/MPS load, keeps device cool & fans silent.",
                title="OmniRip Eco Mode",
                timeout=3.0,
            )

        self._update_inspector()

        # If auditioning ENH, invalidate current cache and re-render with the new engine mode
        self.path_enh = None
        if self.path_mp3 and self.path_mp3.exists():
            if self.active_stream == "ENH":
                preset = PRESETS.get(self.selected_preset_id)
                p_name = preset.name if preset else "Enhanced"
                self.query_one("#wb-status", Label).update(
                    f"Switching engine: re-synthesizing '{p_name}'..."
                )
            self._trigger_enhancement_pregeneration()

    def trigger_models_download(self) -> None:
        """Download or verify local caching of all AI neural model weights."""
        from harvester.services.model_manager import SUPPORTED_MODELS, ModelManager

        mm = ModelManager()
        missing = [m for m in SUPPORTED_MODELS if not mm.is_cached(m)]
        if not missing:
            self.query_one("#wb-status", Label).update(
                "✅ All neural models (NVSR & FlashSR) are already downloaded and cached locally."
            )
            self.app.notify(
                "✅ Neural weights verified! NVSR and FlashSR models are ready for use.",
                title="OmniRip AI Models",
                timeout=4.0,
            )
            return

        self.query_one("#wb-status", Label).update(
            f"📥 Downloading neural model weights ({', '.join(missing)})..."
        )
        self.run_worker(self._async_download_models(missing), name="download-models")

    async def _async_download_models(self, models: list[str]) -> None:
        from harvester.services.model_manager import ModelManager

        mm = ModelManager()
        try:
            for model_name in models:
                self.query_one("#wb-status", Label).update(
                    f"📥 Downloading {model_name.upper()} weights from Hugging Face..."
                )
                await asyncio.to_thread(mm.download_model, model_name)
            self.query_one("#wb-status", Label).update(
                "✅ All neural model weights downloaded successfully!"
            )
            self.app.notify(
                "✅ Model download complete! Neural super-resolution weights are now cached.",
                title="OmniRip Models Downloaded",
                timeout=5.0,
            )
            self._update_inspector()
        except Exception as exc:
            self.query_one("#wb-status", Label).update(
                f"Model download failed: {exc}"
            )
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

        preset = PRESETS[self.selected_preset_id]
        self.query_one("#wb-status", Label).update(
            f"Downloading Enhanced MP3 with '{preset.name}'..."
        )
        self.run_worker(self._async_export(src, preset), name="export-derivative")

    async def _async_export(self, src: Path, preset) -> None:
        try:
            target_dest = src.parent / f"{src.stem}.enhanced.mp3"
            out_path = await asyncio.to_thread(
                self.exporter.export_enhanced_derivative,
                input_path=src,
                preset=preset,
                output_path=target_dest,
                cutoff_hz=self.cutoff_hz,
            )
            self.path_enh = out_path
            self.query_one("#wb-status", Label).update(f"✓ Downloaded: {out_path.name}")
            self.app.notify(
                f"✓ Downloaded Enhanced MP3: {out_path.name}\nPreset: {preset.name}",
                title="OmniRip Enhanced Download",
                timeout=4.0,
            )
            if self.on_exported:
                self.on_exported(out_path)
        except Exception as exc:
            self.query_one("#wb-status", Label).update(f"Download error: {exc}")
            self.app.notify(f"Download error: {exc}", severity="error")
