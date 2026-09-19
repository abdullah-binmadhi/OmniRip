"""Modal screen for configuring Soulseek account credentials and local daemon."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from harvester.services.slskd_config import (
    check_soulseek_status,
    read_slskd_credentials,
    restart_slskd_daemon,
    save_slskd_credentials,
)


class SoulseekLoginModal(ModalScreen[bool]):
    """Interactive modal dialog to enter Soulseek credentials and connect."""

    DEFAULT_CSS = """
    SoulseekLoginModal {
        align: center middle;
    }
    #slsk-dialog {
        width: 72;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #slsk-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #slsk-description {
        color: $text-muted;
        margin-bottom: 1;
    }
    .input-label {
        color: $text;
        text-style: bold;
        margin-top: 1;
    }
    #slsk-status {
        margin-top: 1;
        margin-bottom: 1;
        min-height: 2;
    }
    #slsk-actions {
        margin-top: 1;
        align: right middle;
    }
    #btn-slsk-cancel {
        margin-right: 1;
    }
    """

    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def __init__(self, repo_root: Path | None = None) -> None:
        super().__init__()
        self.repo_root = repo_root

    def compose(self) -> ComposeResult:
        with Vertical(id="slsk-dialog"):
            yield Label("Soulseek Account & Network Setup", id="slsk-title")
            yield Label(
                "Connect OmniRip to the decentralized Soulseek P2P network. "
                "Enter your username and password below. Your local API key "
                "is generated automatically.",
                id="slsk-description",
            )
            yield Label("Username", classes="input-label")
            yield Input(placeholder="Soulseek Username", id="slsk-username")
            yield Label("Password", classes="input-label")
            yield Input(
                placeholder="Soulseek Password",
                password=True,
                id="slsk-password",
            )
            yield Static("", id="slsk-status")
            with Horizontal(id="slsk-actions"):
                yield Button("Cancel", id="btn-slsk-cancel")
                yield Button("Save & Connect", id="btn-slsk-save", variant="primary")

    def on_mount(self) -> None:
        creds = read_slskd_credentials(self.repo_root)
        if creds.get("username"):
            self.query_one("#slsk-username", Input).value = creds["username"]
        if creds.get("password"):
            self.query_one("#slsk-password", Input).value = creds["password"]

        status_lbl = self.query_one("#slsk-status", Static)
        if creds.get("configured"):
            status_lbl.update(
                f"[green]Configured for @{creds['username']}. "
                "Click 'Save & Connect' to verify.[/green]"
            )
        else:
            status_lbl.update(
                "[dim]Enter your Soulseek credentials to enable high-speed FLAC acquisition.[/dim]"
            )

    def action_dismiss_modal(self) -> None:
        self.dismiss(False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-slsk-cancel":
            self.dismiss(False)
            return

        if event.button.id == "btn-slsk-save":
            user_input = self.query_one("#slsk-username", Input).value.strip()
            pass_input = self.query_one("#slsk-password", Input).value.strip()
            status_lbl = self.query_one("#slsk-status", Static)

            if not user_input:
                status_lbl.update("[bold red]Please enter your Soulseek username.[/bold red]")
                return

            save_btn = self.query_one("#btn-slsk-save", Button)
            save_btn.disabled = True
            status_lbl.update("[yellow]Saving configuration and generating API key...[/yellow]")

            try:
                # 1. Save config with auto-generated API key if missing
                save_slskd_credentials(
                    user_input,
                    pass_input,
                    repo_root=self.repo_root,
                )

                # 2. Check local daemon status
                status_lbl.update("[yellow]Checking slskd daemon connection...[/yellow]")
                status = await check_soulseek_status()

                # If daemon is not running, attempt local restart
                if not status["daemon_running"]:
                    status_lbl.update("[yellow]Starting local slskd background daemon...[/yellow]")
                    started = await restart_slskd_daemon(self.repo_root)
                    if started:
                        await asyncio.sleep(2.0)
                        status = await check_soulseek_status()

                if status["logged_in"]:
                    status_lbl.update(
                        f"[bold green]Connected to Soulseek as @{user_input}![/bold green]"
                    )
                    await asyncio.sleep(0.8)
                    self.dismiss(True)
                elif status["connected"]:
                    daemon_state = status["state"]
                    status_lbl.update(
                        f"[bold green]Connected! Soulseek: {daemon_state}[/bold green]"
                    )
                    await asyncio.sleep(0.8)
                    self.dismiss(True)
                elif status["daemon_running"]:
                    status_lbl.update(
                        f"[yellow]Credentials saved! Daemon running: {status['detail']}[/yellow]"
                    )
                    await asyncio.sleep(1.0)
                    self.dismiss(True)
                else:
                    status_lbl.update(
                        "[yellow]Credentials saved to slskd.local.yml. "
                        "Daemon will connect when started.[/yellow]"
                    )
                    await asyncio.sleep(1.2)
                    self.dismiss(True)
            except Exception as exc:
                status_lbl.update(f"[bold red]Error: {exc}[/bold red]")
            finally:
                save_btn.disabled = False
