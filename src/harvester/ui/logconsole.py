"""Log console: level-filtered, capped RichLog (docs/08 §2/§4)."""

from __future__ import annotations

from textual.widgets import RichLog

#: Three cycling filter states: everything, INFO-and-up, WARNING-and-up (docs/08 §5).
FILTER_MODES = ("DEBUG", "INFO", "WARN+ERROR")
_LEVEL_ORDER = ("DEBUG", "INFO", "WARNING", "ERROR")


def level_passes(mode: str, level: str) -> bool:
    """Return whether ``level`` (upper) should be shown under ``mode``."""
    upper = level.upper()
    if mode == "DEBUG":
        return True
    if mode == "INFO":
        return upper in {"INFO", "WARNING", "ERROR"}
    return upper in {"WARNING", "ERROR"}


def next_mode(current: str) -> str:
    """Return the next filter mode in the cycle."""
    index = FILTER_MODES.index(current)
    return FILTER_MODES[(index + 1) % len(FILTER_MODES)]


class LogConsole(RichLog):
    """A ``RichLog`` that filters by minimum severity and trims to a line cap."""

    def __init__(self, *, max_lines: int = 2000) -> None:
        super().__init__(id="logs", markup=False, wrap=True, highlight=False)
        self._line_cap = max_lines
        self._mode = "INFO"
        self._buffer: list[tuple[str, str]] = []

    @property
    def mode(self) -> str:
        return self._mode

    def cycle_level(self) -> str:
        self._mode = next_mode(self._mode)
        self._repaint()
        return self._mode

    def write_line(self, level: str, text: str) -> None:
        """Append a line if it passes the current level filter."""
        upper = level.upper()
        if not level_passes(self._mode, upper):
            return
        self._buffer.append((upper, text))
        if len(self._buffer) > self._line_cap:
            del self._buffer[: len(self._buffer) - self._line_cap]
        super().write(f"{upper:<7} {text}")

    def _repaint(self) -> None:
        self.clear()
        for level, text in self._buffer:
            if level_passes(self._mode, level):
                super().write(f"{level:<7} {text}")


__all__ = ["FILTER_MODES", "LogConsole", "level_passes", "next_mode"]
