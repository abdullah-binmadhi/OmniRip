"""First-Run Setup & Model Downloader Modal (Textual).

Presents a turnkey model acquisition dialog on initial launch or when
enhancement models (Demucs v4, FlashSR) are missing from local cache.
"""

from __future__ import annotations

import asyncio
import logging

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
        self._fractions: dict[str, float] = {}

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

        missing = list(self._missing_models)
        self._fractions = {name: 0.0 for name in missing}

        def on_progress(name: str, fraction: float) -> None:
            self._fractions[name] = max(0.0, min(1.0, fraction))
            try:
                self.app.call_from_thread(self._render_progress)
            except Exception:
                pass

        # Parallel downloads: Hugging Face throttles per connection, so the
        # setup bundle finishes several times sooner than one file at a time.
        results = await asyncio.to_thread(
            self.model_manager.download_many,
            missing,
            progress_callback=on_progress,
        )

        failed = [name for name, path in results.items() if path is None]
        if failed:
            logger.warning("Model download failures: %s", ", ".join(failed))
            self._check_missing_models()
            status_label.update(f"[red]✗ Failed to download:[/red] {', '.join(failed)}")
            btn_download.label = "Retry Download"
            btn_download.disabled = False
            skip_btn.disabled = False
            self._is_downloading = False
            return

        status_label.update("[green]✓ Setup complete! All models verified.[/green]")
        progress_bar.update(progress=100.0, total=100.0)
        btn_download.label = "Enter OmniRip"
        btn_download.disabled = False
        skip_btn.disabled = False
        self._missing_models.clear()
        self._is_downloading = False

    def _render_progress(self) -> None:
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            status = self.query_one("#model-status", Label)
        except Exception:
            return
        missing = self._missing_models
        total = max(1, len(missing))
        overall = sum(self._fractions.get(name, 0.0) for name in missing) / total
        bar.update(progress=overall * 100.0, total=100.0)
        active = [
            f"{name} {self._fractions.get(name, 0.0) * 100:.0f}%"
            for name in missing
            if 0.0 < self._fractions.get(name, 0.0) < 1.0
        ]
        if active:
            status.update("[cyan]Downloading[/cyan] " + " · ".join(active))
