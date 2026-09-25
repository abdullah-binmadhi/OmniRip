"""Tests for ModelSetupModal (First-run model downloader)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from harvester.services.model_manager import ModelManager
from harvester.ui.setup_modal import DEFAULT_SETUP_MODELS, ModelSetupModal


class DummySetupApp(App[None]):
    def __init__(self, modal: ModelSetupModal) -> None:
        super().__init__()
        self.modal = modal

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(self.modal)


def test_setup_modal_init_detects_cached_and_missing():
    mock_mm = MagicMock(spec=ModelManager)
    mock_mm.is_cached.side_effect = lambda name: name == "hdemucs"

    modal = ModelSetupModal(model_manager=mock_mm, models=["hdemucs", "flashsr"])
    assert modal.models_to_check == ["hdemucs", "flashsr"]
    assert modal.model_manager is mock_mm


@pytest.mark.asyncio
async def test_setup_modal_compose_and_skip():
    mock_mm = MagicMock(spec=ModelManager)
    mock_mm.is_cached.return_value = False

    modal = ModelSetupModal(model_manager=mock_mm, models=["hdemucs"])
    app = DummySetupApp(modal)

    async with app.run_test() as pilot:
        btn_download = modal.query_one("#btn-download", Button)
        btn_skip = modal.query_one("#btn-skip", Button)
        status_label = modal.query_one("#model-status", Label)

        assert btn_download is not None
        assert btn_skip is not None
        assert "Missing" in str(status_label.render())

        await pilot.click("#btn-skip")


@pytest.mark.asyncio
async def test_setup_modal_when_all_cached():
    mock_mm = MagicMock(spec=ModelManager)
    mock_mm.is_cached.return_value = True

    modal = ModelSetupModal(model_manager=mock_mm, models=DEFAULT_SETUP_MODELS)
    app = DummySetupApp(modal)

    async with app.run_test() as pilot:
        btn_download = modal.query_one("#btn-download", Button)
        assert btn_download.label == "Enter OmniRip"
        await pilot.click("#btn-download")
