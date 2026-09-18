"""Textual Curation Workbench Modal Screen for OmniRip M10."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from harvester.analysis.enhancement.presets import EnhancementPreset, PRESETS
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.services.enhancement.preview import PreviewManager


class CurationWorkbenchModal(ModalScreen[Path | None]):
    """
    Interactive modal dialog for previewing, auditioning, and exporting
    enhanced audio derivatives with deterministic mathematical presets.
    """

    DEFAULT_CSS = """
    CurationWorkbenchModal {
        align: center middle;
    }
    #workbench-dialog {
        width: 76;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #workbench-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #meta-info {
        margin-bottom: 1;
        color: $text-muted;
    }
    #preset-desc {
        margin-top: 1;
        margin-bottom: 1;
        color: $text;
        height: 2;
    }
    #status-msg {
        color: $warning;
        margin-top: 1;
        margin-bottom: 1;
    }
    #actions {
        margin-top: 1;
        align: right middle;
    }
    #actions Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        audio_file: Path,
        detected_cutoff_hz: float = 15500.0,
        preview_manager: PreviewManager | None = None,
        exporter: EnhancementExporter | None = None,
        on_exported: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__()
        self.audio_file = Path(audio_file)
        self.cutoff_hz = detected_cutoff_hz
        self.preview_manager = preview_manager or PreviewManager()
        self.exporter = exporter or EnhancementExporter()
        self.on_exported = on_exported

        self.selected_preset_id: str = "conservative"
        self._preview_pair: tuple[Path, Path] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="workbench-dialog"):
            yield Label(f"🎵 Audio Enhancement Workbench: {self.audio_file.name}", id="workbench-title")
            yield Label(
                f"Source: {self.audio_file.name} | Detected Cutoff: {self.cutoff_hz:.0f} Hz",
                id="meta-info",
            )

            options = [(preset.name, preset.id) for preset in PRESETS.values()]
            yield Select(options=options, value=self.selected_preset_id, id="preset-select")

            yield Static(
                PRESETS[self.selected_preset_id].description,
                id="preset-desc",
            )
            yield Static("Ready to preview or export.", id="status-msg")

            with Horizontal(id="actions"):
                yield Button("🎧 Play A/B Previews", id="btn-preview", variant="primary")
                yield Button("💾 Export Derivative (.mp3)", id="btn-export", variant="success")
                yield Button("Cancel", id="btn-cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "preset-select" and event.value is not None:
            self.selected_preset_id = str(event.value)
            desc_widget = self.query_one("#preset-desc", Static)
            preset = PRESETS.get(self.selected_preset_id)
            if preset:
                desc_widget.update(preset.description)
            # Invalidate cached preview for new preset
            self._preview_pair = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        status_widget = self.query_one("#status-msg", Static)

        if event.button.id == "btn-preview":
            preset = PRESETS[self.selected_preset_id]
            status_widget.update(f"Rendering 15s preview with '{preset.name}'...")
            try:
                if self._preview_pair is None:
                    self._preview_pair = self.preview_manager.generate_preview_pair(
                        self.audio_file,
                        preset=preset,
                        cutoff_hz=self.cutoff_hz,
                    )
                orig_wav, enh_wav = self._preview_pair
                # Launch enhanced preview in system player
                self.preview_manager.open_in_system_player(enh_wav)
                status_widget.update(f"Playing enhanced preview ({enh_wav.name}) in system player.")
            except Exception as e:
                status_widget.update(f"Preview error: {e}")

        elif event.button.id == "btn-export":
            preset = PRESETS[self.selected_preset_id]
            status_widget.update(f"Exporting MP3 derivative with '{preset.name}'...")
            try:
                out_path = self.exporter.export_enhanced_derivative(
                    input_path=self.audio_file,
                    preset=preset,
                    cutoff_hz=self.cutoff_hz,
                )
                status_widget.update(f"Exported: {out_path.name}")
                if self.on_exported:
                    self.on_exported(out_path)
                self.dismiss(out_path)
            except Exception as e:
                status_widget.update(f"Export failed: {e}")

        elif event.button.id == "btn-cancel":
            self.dismiss(None)
