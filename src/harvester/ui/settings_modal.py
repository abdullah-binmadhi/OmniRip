"""In-TUI Settings & API Keys Modal (Textual).

Allows users to configure and test external API keys and daemon connections
(slskd, AcoustID, MVSEP, TypeSafe Jev, and Obsidian) directly within the TUI
without editing config files manually.
"""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from harvester.config import AppConfig
from harvester.services.environment import check_slskd

logger = logging.getLogger(__name__)


class SettingsModal(ModalScreen[bool]):
    """Modal dialog for managing credentials, API keys, and service paths."""

    DEFAULT_CSS = """
    SettingsModal {
        align: center middle;
        background: rgba(10, 10, 18, 0.85);
    }

    #settings-card {
        width: 80;
        height: 85%;
        border: heavy cyan;
        background: #0d1117;
        padding: 1 2;
    }

    #settings-title {
        color: cyan;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    .section-title {
        color: #58a6ff;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    .field-label {
        color: #8b949e;
        margin-top: 0;
    }

    .settings-input {
        margin-bottom: 1;
    }

    #test-result {
        margin-top: 1;
        text-align: center;
    }

    #settings-buttons {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    #settings-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-card"):
            yield Static("⚙  OMNIRIP SETTINGS & API CREDENTIALS", id="settings-title")
            with ScrollableContainer():
                # Soulseek / slskd
                yield Label("Soulseek / slskd Daemon", classes="section-title")
                yield Label("Daemon URL:", classes="field-label")
                yield Input(
                    value=self.config.slskd.url,
                    placeholder="http://localhost:5000",
                    id="input-slskd-url",
                    classes="settings-input",
                )
                yield Label("slskd API Key:", classes="field-label")
                current_slskd_key = os.environ.get(self.config.slskd.api_key_env, "")
                yield Input(
                    value=current_slskd_key,
                    placeholder="Enter slskd API key (or leave empty if auth disabled)",
                    password=True,
                    id="input-slskd-key",
                    classes="settings-input",
                )

                # AcoustID
                yield Label("AcoustID (Audio Fingerprinting)", classes="section-title")
                yield Label("AcoustID API Key:", classes="field-label")
                current_acoustid_key = os.environ.get(self.config.acoustid.api_key_env, "")
                yield Input(
                    value=current_acoustid_key,
                    placeholder="Paste your AcoustID application key",
                    password=True,
                    id="input-acoustid-key",
                    classes="settings-input",
                )

                # Hosted Separation (MVSEP)
                yield Label("Hosted Stem Separation (MVSEP, Optional)", classes="section-title")
                yield Label("MVSEP API Key:", classes="field-label")
                current_mvsep_key = os.environ.get("MVSEP_API_KEY", "")
                yield Input(
                    value=current_mvsep_key,
                    placeholder="Paste MVSEP API key for cloud stem extraction",
                    password=True,
                    id="input-mvsep-key",
                    classes="settings-input",
                )

                # TypeSafe Jev
                yield Label("TypeSafe Jev AI Advisory (Optional)", classes="section-title")
                yield Label("TypeSafe API Key:", classes="field-label")
                current_jev_key = os.environ.get(self.config.jev.api_key_env, "")
                yield Input(
                    value=current_jev_key,
                    placeholder="Paste TypeSafe API key for P2P advisory triage",
                    password=True,
                    id="input-jev-key",
                    classes="settings-input",
                )

                # Obsidian
                yield Label("Obsidian Second Brain Vault (Optional)", classes="section-title")
                yield Label("Obsidian Vault Folder:", classes="field-label")
                current_vault = (
                    str(self.config.obsidian.vault_dir) if self.config.obsidian.vault_dir else ""
                )
                yield Input(
                    value=current_vault,
                    placeholder="~/Documents/Obsidian/MusicVault",
                    id="input-obsidian-vault",
                    classes="settings-input",
                )

                yield Label("", id="test-result")

            with Center():
                with Horizontal(id="settings-buttons"):
                    yield Button("Test Connections", id="btn-test", variant="default")
                    yield Button("Save & Apply", id="btn-save", variant="primary")
                    yield Button("Cancel", id="btn-cancel", variant="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        result_label = self.query_one("#test-result", Label)

        if event.button.id == "btn-cancel":
            self.dismiss(False)
            return

        if event.button.id == "btn-test":
            url = self.query_one("#input-slskd-url", Input).value.strip() or self.config.slskd.url
            key = self.query_one("#input-slskd-key", Input).value.strip()
            if key:
                os.environ[self.config.slskd.api_key_env] = key
            test_config = replace(self.config, slskd=replace(self.config.slskd, url=url))
            result_label.update("[yellow]Testing connections...[/yellow]")
            event.button.disabled = True

            try:
                # Test slskd
                status = await check_slskd(test_config)
                if status.available:
                    result_label.update(
                        f"[green]✓ slskd connected successfully at {url}[/green]"
                    )
                else:
                    detail = status.detail or "unreachable"
                    result_label.update(
                        f"[red]✗ slskd check failed: {detail}[/red]"
                    )
            except Exception as exc:
                result_label.update(f"[red]✗ Connection error: {exc}[/red]")
            finally:
                event.button.disabled = False
            return

        if event.button.id == "btn-save":
            self._save_settings()
            self.dismiss(True)

    def _save_settings(self) -> None:
        """Apply inputs to runtime environment and active config."""
        slskd_url = self.query_one("#input-slskd-url", Input).value.strip()
        slskd_key = self.query_one("#input-slskd-key", Input).value.strip()
        acoustid_key = self.query_one("#input-acoustid-key", Input).value.strip()
        mvsep_key = self.query_one("#input-mvsep-key", Input).value.strip()
        jev_key = self.query_one("#input-jev-key", Input).value.strip()
        vault_path = self.query_one("#input-obsidian-vault", Input).value.strip()

        # Update environment variables
        if slskd_key:
            os.environ[self.config.slskd.api_key_env] = slskd_key
        if acoustid_key:
            os.environ[self.config.acoustid.api_key_env] = acoustid_key
        if mvsep_key:
            os.environ["MVSEP_API_KEY"] = mvsep_key
        if jev_key:
            os.environ[self.config.jev.api_key_env] = jev_key

        # Update runtime config
        if slskd_url:
            self.config = replace(
                self.config, slskd=replace(self.config.slskd, url=slskd_url)
            )
        if vault_path:
            self.config = replace(
                self.config,
                obsidian=replace(
                    self.config.obsidian,
                    vault_dir=Path(vault_path).expanduser(),
                    enabled=True,
                ),
            )

        logger.info("Saved in-TUI settings and credentials.")
