"""Track Info modal (docs/01 D35): the new home for enrichment and upkeep.

Replaces the old layers-page buttons. Read-only rows show the track's
identity, spectral verdict, credits, tags, measured voices, hosted-key and
model-cache status; the action row runs the low-frequency upkeep tasks. The
screen dismisses with the chosen action key (or None) and the workbench
dispatches it.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

ACTIONS: tuple[tuple[str, str], ...] = (
    ("ti-tags", "tags"),
    ("ti-speakers", "speakers"),
    ("ti-credits", "credits"),
    ("ti-models", "models"),
    ("ti-diagnostics", "diagnostics"),
)


class TrackInfoScreen(ModalScreen[str | None]):
    """Modal listing track facts, enrichment and model upkeep actions."""

    def __init__(
        self,
        rows: list[tuple[str, str]] | None = None,
        *,
        hosted_available: bool = False,
    ) -> None:
        super().__init__()
        self._rows = rows or []
        self._hosted_available = hosted_available

    def compose(self) -> ComposeResult:
        with Vertical(id="ti-box"):
            yield Label("ℹ TRACK INFO", id="ti-title")
            yield Static("", id="ti-body")
            with Horizontal(id="ti-actions"):
                yield Button("🏷 REFRESH TAGS", id="ti-tags")
                yield Button("👥 MEASURE VOICES", id="ti-speakers")
                yield Button("🎼 CREDITS", id="ti-credits")
                yield Button("⬇ MODELS", id="ti-models")
                yield Button("🩺 DIAGNOSTICS", id="ti-diagnostics")
            with Horizontal(classes="modal-buttons"):
                yield Button("✗ Close", id="ti-close")

    def on_mount(self) -> None:
        body = self.query_one("#ti-body", Static)
        width = max((len(label) for label, _value in self._rows), default=0)
        lines = [f"{label.ljust(width)}  {value}" for label, value in self._rows]
        hosted = "MVSEP key configured" if self._hosted_available else "no MVSEP key configured"
        lines.append(f"{'Hosted'.ljust(width)}  {hosted}")
        body.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "ti-close":
            self.dismiss(None)
            return
        for known_id, action in ACTIONS:
            if button_id == known_id:
                self.dismiss(action)
                return


__all__ = ["ACTIONS", "TrackInfoScreen"]
