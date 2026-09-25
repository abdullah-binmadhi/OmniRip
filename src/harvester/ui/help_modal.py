"""
Help and Quick Keyboard Cheatsheet modal for OmniRip.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class HelpModalScreen(ModalScreen[None]):
    """Sleek cyber-themed hotkey cheatsheet and guide overlay."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("?", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    HelpModalScreen {
        align: center middle;
        background: rgba(10, 15, 20, 0.85);
    }
    #help-card {
        width: 76;
        height: auto;
        max-height: 90%;
        border: heavy $primary;
        background: #0d1218;
        padding: 1 2;
    }
    #help-header {
        width: 1fr;
        height: auto;
        border-bottom: solid $primary 50%;
        margin-bottom: 1;
        padding-bottom: 1;
    }
    #help-title {
        color: $accent;
        text-style: bold;
    }
    #help-subtitle {
        color: $text-muted;
    }
    #help-grid {
        grid-size: 2;
        grid-gutter: 1 2;
        height: auto;
        margin-bottom: 1;
    }
    .help-section {
        height: auto;
        background: #131b24;
        border: solid #1f2b38;
        padding: 1;
    }
    .section-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    .hotkey-row {
        height: 1;
    }
    .hotkey-key {
        width: 14;
        color: $accent;
        text-style: bold;
    }
    .hotkey-desc {
        width: 1fr;
        color: $text;
    }
    #help-footer {
        align: right middle;
        height: auto;
        margin-top: 1;
    }
    #btn-help-close {
        min-width: 14;
        background: $primary;
        color: #000;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="help-card"):
            with Vertical(id="help-header"):
                yield Label("⚡ OMNIRIP COMMAND & TELEMETRY CHEATSHEET", id="help-title")
                yield Label(
                    "Quick reference for playback, studio telemetry, and workspace navigation.",
                    id="help-subtitle",
                )

            with Grid(id="help-grid"):
                # Audio Playback
                with Vertical(classes="help-section"):
                    yield Label("▶ AUDIO ENGINE & SCRUBBING", classes="section-title")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Space", classes="hotkey-key")
                        yield Label("Play / Pause playback", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("← / →", classes="hotkey-key")
                        yield Label("Seek ±5 seconds", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Shift + ← / →", classes="hotkey-key")
                        yield Label("Seek ±15 seconds", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Click Scrub", classes="hotkey-key")
                        yield Label("Direct click-to-seek timestamp", classes="hotkey-desc")

                # Studio Telemetry & Radar
                with Vertical(classes="help-section"):
                    yield Label("◈ STUDIO TELEMETRY & RADAR", classes="section-title")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("t", classes="hotkey-key")
                        yield Label("Cycle Mode (LUFS ➔ PHASE ➔ RADAR)", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("T (Shift+t)", classes="hotkey-key")
                        yield Label("Cycle LUFS Target (-14, -16, -9 dB)", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Click Radar", classes="hotkey-key")
                        yield Label("Cycle target / View forensic report", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("p", classes="hotkey-key")
                        yield Label("Reset peak hold / goniometer", classes="hotkey-desc")

                # Navigation
                with Vertical(classes="help-section"):
                    yield Label("⌘ WORKSPACE NAVIGATION", classes="section-title")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("1 - 5", classes="hotkey-key")
                        yield Label("Workbench, Studio, Repair, Logs, Config", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Tab / Shift+Tab", classes="hotkey-key")
                        yield Label("Navigate active controls", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Ctrl+J", classes="hotkey-key")
                        yield Label("Focus Job Queue Table", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Ctrl+F", classes="hotkey-key")
                        yield Label("Jump to Search & Rip bar", classes="hotkey-desc")

                # System & Diagnostics
                with Vertical(classes="help-section"):
                    yield Label("⚙ SYSTEM & FORENSICS", classes="section-title")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("?", classes="hotkey-key")
                        yield Label("Toggle this cheatsheet modal", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Ctrl+S", classes="hotkey-key")
                        yield Label("Quick-open API Settings", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Ctrl+C / q", classes="hotkey-key")
                        yield Label("Graceful shutdown & exit", classes="hotkey-desc")
                    with Horizontal(classes="hotkey-row"):
                        yield Label("Esc", classes="hotkey-key")
                        yield Label("Close open modals & dialogs", classes="hotkey-desc")

            with Horizontal(id="help-footer"):
                yield Button("CLOSE (ESC)", id="btn-help-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-help-close":
            self.dismiss()
