"""Hosted separation confirmation + model picker (docs/14 M3).

The only audio-egress action in the app gets an explicit, blocking decision:
a modal listing what will be uploaded (file, size, duration cap) and which
MVSEP algorithm will run. Nothing leaves the machine unless the user presses
``UPLOAD TO MVSEP``.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioButton, RadioSet

logger = logging.getLogger(__name__)


def _pretty_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{value:.1f} GB"  # pragma: no cover - defensive


class HostedSeparationScreen(ModalScreen[str | None]):
    """Confirm an MVSEP upload; dismisses with the chosen ``sep_type`` or None."""

    def __init__(
        self,
        source: Path,
        default_sep_type: str,
        max_seconds: float = 0.0,
        algorithms: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__()
        self._source = Path(source)
        self._default = str(default_sep_type or "vocals")
        self._max_seconds = float(max_seconds)
        self._algorithms = algorithms  # None → fetch from MVSEP on mount
        self._radio: RadioSet | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="hosted-box"):
            try:
                size = self._source.stat().st_size
                size_text = _pretty_size(size)
            except OSError:
                size_text = "unknown size"
            scope = f"up to {self._max_seconds:.0f}s of" if self._max_seconds > 0 else "the whole"
            yield Label(
                f"☁ Upload {scope} “{self._source.name}” ({size_text}) to MVSEP?", id="hosted-title"
            )
            yield Label(
                "Audio leaves this machine ONLY for this hosted separation — "
                "local stages (separation, tags, speakers) never upload.",
                classes="dim",
            )
            yield Label("Model:", classes="dim")
            yield RadioSet(id="hosted-models")
            with Horizontal(classes="modal-buttons"):
                yield Button("✗ Cancel", id="hosted-cancel")
                yield Button("✓ UPLOAD TO MVSEP", id="hosted-confirm", variant="warning")

    def on_mount(self) -> None:
        if self._algorithms is None:
            self.fetch_algorithms()
        else:
            self._fill(self._algorithms)

    @work(exclusive=True, group="hosted-algorithms")
    async def fetch_algorithms(self) -> None:
        algorithms: list[dict[str, object]] = []
        try:
            from harvester.services.mvsep import MvsepClient

            client = MvsepClient()
            try:
                if client.available:
                    algorithms = await client.algorithms()
            finally:
                await client.close()
        except Exception as exc:  # no network / bad key → fall back to default
            logger.info("hosted algorithm list unavailable: %s", exc)
        self.call_after_refresh(self._fill, algorithms)

    def _fill(self, algorithms: list[dict[str, object]]) -> None:
        radio = self.query_one("#hosted-models", RadioSet)
        self._radio = radio
        # Idempotent: drop any previously mounted buttons (this screen may be
        # refilled once the live algorithm list arrives after a local fallback).
        for existing in radio.query(RadioButton):
            existing.remove()
        self._id_to_sep_type: dict[str, str] = {}
        choices: list[tuple[str, str]] = []
        for item in algorithms:
            name = str(item.get("name", "")).strip()
            render_id = item.get("render_id")
            if not name or not isinstance(render_id, int):
                continue
            choices.append((name, str(render_id)))
        if not choices:
            # Offline / keyless: still let the user run with the configured
            # default, clearly labelled as fallback.
            choices.append((f"{self._default} (configured default)", self._default))
        for index, (label, sep_type) in enumerate(choices):
            # Explicit stable id: an auto-assigned id would not exist yet at
            # construction time, collapsing the sep_type mapping to one key.
            button = RadioButton(label, id=f"hosted-model-{index}")
            assert button.id is not None  # set explicitly above
            self._id_to_sep_type[button.id] = sep_type
            radio.mount(button)
        # Preselect the configured default when present.
        for button in radio.query(RadioButton):
            if self._id_to_sep_type.get(button.id or "") == str(self._default):
                button.value = True
                break
        if not any(bool(b.value) for b in radio.query(RadioButton)):
            with contextlib.suppress(Exception):
                radio.query(RadioButton).first().value = True

    def _selected(self) -> str | None:
        if self._radio is None:
            return None
        button = self._radio.pressed_button
        if button is None:
            return None
        return self._id_to_sep_type.get(str(button.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "hosted-confirm":
            self.dismiss(self._selected() or self._default)
        elif event.button.id == "hosted-cancel":
            self.dismiss(None)
