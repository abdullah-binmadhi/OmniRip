"""Genre mix modal: pick up to six profiles for a hybrid track (docs/01 D38)."""

from __future__ import annotations

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, SelectionList

from harvester.analysis.enhancement.genres import MAX_MIX_GENRES


class GenreMixScreen(ModalScreen[list[str] | None]):
    """Multi-select genre mixer; dismisses with the chosen profile keys or None."""

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        selected: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self._options = list(options)
        self._selected = tuple(selected)

    def compose(self) -> ComposeResult:
        with Vertical(id="genre-mix-box"):
            yield Label("◈ GENRE MIX", id="genre-mix-title")
            yield Label(
                "Pick up to six genres — the curves are averaged, so hybrids get "
                "less colour, never more.",
                id="genre-mix-hint",
            )
            yield SelectionList[str](
                *[
                    (label, key, key in self._selected)
                    for label, key in self._options
                ],
                id="genre-mix-list",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", id="genre-mix-cancel")
                yield Button("Apply mix", id="genre-mix-apply", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "genre-mix-apply":
            chosen = list(self.query_one("#genre-mix-list", SelectionList).selected)
            if len(chosen) > MAX_MIX_GENRES:
                self.query_one("#genre-mix-hint", Label).update(
                    f"Too many genres ({len(chosen)}) — pick at most {MAX_MIX_GENRES}."
                )
                return
            self.dismiss(chosen)
            return
        self.dismiss(None)


__all__ = ["MAX_MIX_GENRES", "GenreMixScreen"]
