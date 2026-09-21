"""Environment diagnostics (docs/14 M3).

A read-only modal showing what the machine can run and what is configured —
model presence/versions via ``importlib.metadata`` (never a heavy import on the
UI thread), tool availability via ``shutil.which``, and credential *presence*
only (values are never rendered).
"""

from __future__ import annotations

import importlib.metadata
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

_PACKAGES = (
    "torch",
    "torchaudio",
    "demucs",
    "transformers",
    "pyannote.audio",
    "mutagen",
    "httpx",
    "numpy",
    "textual",
)
_TOOLS = ("ffmpeg", "ffprobe", "fpcalc")


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def collect_diagnostics(config: Any = None) -> list[tuple[str, str]]:
    """Collect environment rows without importing model libraries."""
    rows: list[tuple[str, str]] = [
        ("python", sys.version.split()[0]),
        ("platform", f"{platform.system()} {platform.machine()}"),
    ]
    for package in _PACKAGES:
        rows.append((package, _version(package)))
    for tool in _TOOLS:
        found = shutil.which(tool)
        rows.append((tool, found or "not found"))
    # MVSEP: presence only — the key itself is never printed.
    try:
        from harvester.services.mvsep import MvsepClient

        rows.append(("mvsep key", "configured" if MvsepClient().available else "missing"))
    except Exception:  # pragma: no cover - defensive
        rows.append(("mvsep key", "unknown"))
    try:
        from harvester.services.diarization import pyannote_available

        rows.append(
            (
                "pyannote ready",
                "yes" if pyannote_available() else "no (uv pip install -e '.[diarize]')",
            )
        )
    except Exception:  # pragma: no cover - defensive
        rows.append(("pyannote ready", "unknown"))
    if config is not None:
        processing = getattr(config, "processing", None)
        if processing is not None:
            rows.append(("processing.preset", str(getattr(processing, "preset", "?"))))
            rows.append(
                ("processing.hosted_sep_type", str(getattr(processing, "hosted_sep_type", "?")))
            )
            rows.append(
                (
                    "processing.hosted_max_seconds",
                    str(getattr(processing, "hosted_max_seconds", 0.0)),
                )
            )
            rows.append(
                (
                    "processing.diarize_max_seconds",
                    str(getattr(processing, "diarize_max_seconds", 0.0)),
                )
            )
    cache_dir = Path.home() / ".cache" / "omnirip" / "stems"
    if cache_dir.exists():
        total = sum(p.stat().st_size for p in cache_dir.rglob("*") if p.is_file())
        rows.append(("stem cache", f"{cache_dir} ({total / 1_048_576:.0f} MB)"))
    else:
        rows.append(("stem cache", f"{cache_dir} (empty)"))
    return rows


class DiagnosticsScreen(ModalScreen[None]):
    """Modal listing environment rows; closes with the ✗ button."""

    def __init__(self, rows: list[tuple[str, str]] | None = None, config: Any = None) -> None:
        super().__init__()
        self._rows = rows
        self._config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="diag-box"):
            yield Label("🔍 DIAGNOSTICS", id="diag-title")
            yield Static("Collecting environment information…", id="diag-body")
            with Horizontal(classes="modal-buttons"):
                yield Button("✗ Close", id="diag-close")

    def on_mount(self) -> None:
        if self._rows is not None:
            self._show_rows(self._rows)
        else:
            self.run_worker(
                self._collect(), name="diagnostics-collect", thread=True, exclusive=True
            )

    async def _collect(self) -> None:
        import asyncio

        rows = await asyncio.to_thread(collect_diagnostics, self._config)
        self.call_after_refresh(self._show_rows, rows)

    def _show_rows(self, rows: list[tuple[str, str]]) -> None:
        body = self.query_one("#diag-body", Static)
        width = max((len(label) for label, _value in rows), default=0)
        lines = [f"{label.ljust(width)}  {value}" for label, value in rows]
        body.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diag-close":
            self.dismiss(None)
