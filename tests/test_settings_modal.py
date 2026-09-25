"""Tests for SettingsModal (In-TUI settings and API credentials)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Label

from harvester.config import load_config
from harvester.ui.settings_modal import SettingsModal


class DummySettingsApp(App[None]):
    def __init__(self, modal: SettingsModal) -> None:
        super().__init__()
        self.modal = modal

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(self.modal)


@pytest.mark.asyncio
async def test_settings_modal_init_and_compose():
    config = load_config()
    modal = SettingsModal(config)
    app = DummySettingsApp(modal)

    async with app.run_test() as pilot:
        slskd_input = modal.query_one("#input-slskd-url", Input)
        assert slskd_input.value == config.slskd.url
        await pilot.click("#btn-cancel")


@pytest.mark.asyncio
async def test_settings_modal_save_updates_config_and_env():
    config = load_config()
    modal = SettingsModal(config)
    app = DummySettingsApp(modal)

    async with app.run_test() as pilot:
        modal.query_one("#input-slskd-url", Input).value = "http://192.168.1.100:5000"
        modal.query_one("#input-slskd-key", Input).value = "secret-slskd-key"
        modal.query_one("#input-acoustid-key", Input).value = "secret-acoustid-key"
        modal.query_one("#input-mvsep-key", Input).value = "secret-mvsep-key"
        modal.query_one("#input-jev-key", Input).value = "secret-jev-key"
        modal.query_one("#input-obsidian-vault", Input).value = "~/TestVault"

        await pilot.click("#btn-save")

        assert modal.config.slskd.url == "http://192.168.1.100:5000"
        assert os.environ.get("SLSKD_API_KEY") == "secret-slskd-key"
        assert os.environ.get("ACOUSTID_API_KEY") == "secret-acoustid-key"
        assert os.environ.get("MVSEP_API_KEY") == "secret-mvsep-key"
        assert os.environ.get("TYPESAFE_API_KEY") == "secret-jev-key"
        assert modal.config.obsidian.enabled is True
        assert "TestVault" in str(modal.config.obsidian.vault_dir)


@pytest.mark.asyncio
async def test_settings_modal_test_connection_button():
    from unittest.mock import AsyncMock

    config = load_config()
    modal = SettingsModal(config)
    app = DummySettingsApp(modal)

    async with app.run_test() as pilot:
        modal.query_one("#input-slskd-url", Input).value = "http://localhost:5000"
        modal.query_one("#input-slskd-key", Input).value = "test-key"

        with patch("harvester.ui.settings_modal.check_slskd", new_callable=AsyncMock) as mock_check:
            status_mock = MagicMock()
            status_mock.available = True
            mock_check.return_value = status_mock

            await pilot.click("#btn-test")
            await pilot.pause()

            result_label = modal.query_one("#test-result", Label)
            assert "✓ slskd connected" in str(result_label.render())
