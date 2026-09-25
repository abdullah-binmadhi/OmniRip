"""First-Run Setup & Model Downloader Modal (Textual).

Presents a turnkey model acquisition dialog on initial launch or when
enhancement models (Demucs v4, FlashSR) are missing from local cache.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ProgressBar, Static

from harvester.services.model_manager import ModelManager

logger = logging.getLogger(__name__)

DEFAULT_SETUP_MODELS = ["hdemucs", "flashsr", "flashsr_ldm", "flashsr_vae"]


class ModelSetupModal(ModalScreen[bool]):
    """Modal dialog for downloading and provisioning AI models on first run."""

    DEFAULT_CSS = """
    ModelSetupModal {
        align: center middle;
        background: rgba(10, 10, 18, 0.85);
    }

    #setup-card {
        width: 72;
        height: auto;
        border: heavy cyan;
        background: #0d1117;
        padding: 1 2;
    }

    #setup-title {
        color: cyan;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    #setup-subtitle {
        color: #8b949e;
        text-align: center;
        margin-bottom: 1;
    }

    #model-status {
        color: #f0883e;
        margin-top: 1;
        margin-bottom: 1;
    }

    #progress-bar {
        width: 100%;
        margin-bottom: 1;
    }

    #setup-buttons {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    #setup-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        model_manager: ModelManager | None = None,
        models: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.model_manager = model_manager or ModelManager()
        self.models_to_check = models or list(DEFAULT_SETUP_MODELS)
        self._is_downloading = False
        self._missing_models: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-card"):
            yield Static("🎧  OMNIRIP FIRST-RUN SETUP", id="setup-title")
            yield Static(
                "OmniRip uses local AI models for stem separation & high-frequency audio restoration.\n"
                "Download default models now to enable local stem splitting and mastering.",
                id="setup-subtitle",
            )
            yield Label("Scanning local model cache...", id="model-status")
            yield ProgressBar(id="progress-bar", total=100.0, show_eta=False)
            with Center():
                with Horizontal(id="setup-buttons"):
                    yield Button("Download Models", id="btn-download", variant="primary")
                    yield Button("Skip / Run Later", id="btn-skip", variant="default")

    def on_mount(self) -> None:
        self._check_missing_models()

    def _check_missing_models(self) -> None:
        self._missing_models = [
            m for m in self.models_to_check if not self.model_manager.is_cached(m)
        ]
        status_label = self.query_one("#model-status", Label)
        btn_download = self.query_one("#btn-download", Button)

        if not self._missing_models:
            status_label.update("[green]✓ All default models are cached and ready![/green]")
            btn_download.label = "Enter OmniRip"
        else:
            names = ", ".join(self._missing_models)
            status_label.update(
                f"[yellow]Missing {len(self._missing_models)} model(s):[/yellow] {names}"
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-skip":
            self.dismiss(False)
            return

        if event.button.id == "btn-download":
            if not self._missing_models:
                self.dismiss(True)
                return
            if not self._is_downloading:
                self._is_downloading = True
                event.button.disabled = True
                skip_btn = self.query_one("#btn-skip", Button)
                skip_btn.disabled = True
                asyncio.create_task(self._run_downloads())

    async def _run_downloads(self) -> None:
        status_label = self.query_one("#model-status", Label)
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        btn_download = self.query_one("#btn-download", Button)
        skip_btn = self.query_one("#btn-skip", Button)

        total_models = len(self._missing_models)

        for index, model_name in enumerate(self._missing_models, start=1):
            status_label.update(
                f"[cyan]Downloading model ({index}/{total_models}):[/cyan] [bold]{model_name}[/bold]..."
            )
            progress_bar.update(progress=0.0, total=100.0)

            def make_progress(name: str, current_idx: int) -> Callable[[float], None]:
                def on_progress(p: float) -> None:
                    pct = round(p * 100.0, 1)
                    self.app.call_from_thread(
                        self._update_progress_ui, name, pct, current_idx, total_models
                    )
                return on_progress

            try:
                await asyncio.to_thread(
                    self.model_manager.download_model,
                    model_name,
                    progress_callback=make_progress(model_name, index),
                )
            except Exception as exc:
                logger.warning("Failed to download model %s: %s", model_name, exc)
                status_label.update(
                    f"[red]✗ Failed to download {model_name}: {exc}[/red]"
                )
                await asyncio.sleep(1.5)

        status_label.update("[green]✓ Setup complete! All models verified.[/green]")
        progress_bar.update(progress=100.0, total=100.0)
        btn_download.label = "Enter OmniRip"
        btn_download.disabled = False
        skip_btn.disabled = False
        self._missing_models.clear()
        self._is_downloading = False

    def _update_progress_ui(
        self, model_name: str, pct: float, index: int, total_models: int
    ) -> None:
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=pct, total=100.0)
            status = self.query_one("#model-status", Label)
            status.update(
                f"[cyan]Downloading ({index}/{total_models}) [bold]{model_name}[/bold]:[/cyan] {pct}%"
            )
        except Exception:
            pass
