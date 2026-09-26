"""Terminal render-fidelity ladder for PLAYER artwork.

Turns a 2D coverage grid (0.0-1.0) into terminal cells across six modes:

- ``octant``: 2x4 sub-cells per character (Unicode 16, opt-in only)
- ``sextant``: 2x3 sub-cells per character (Unicode 13, default)
- ``quadrant``: 2x2 sub-cells per character (Unicode 1)
- ``halfblock``: two vertical samples per character with truecolor fg/bg
- ``braille``: 2x4 monochrome dots for line art and legacy terminals
- ``ascii``: no Unicode requirement, universal fallback

Pattern tables are built from Unicode character names, so the engine never
guesses a codepoint ordering. ``auto`` never selects octants without an
explicit opt-in, and shape-vector matching picks the closest available pattern
instead of thresholding blindly.
"""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from rich.style import Style
from rich.text import Text

MODES: tuple[str, ...] = ("ascii", "braille", "halfblock", "quadrant", "sextant", "octant")
DEFAULT_MODE = "sextant"
FALLBACK_LADDER = ("octant", "sextant", "quadrant", "halfblock", "braille", "ascii")

# (rows_per_cell, cols_per_cell)
CELL_GEOMETRY: dict[str, tuple[int, int]] = {
    "octant": (4, 2),
    "sextant": (3, 2),
    "quadrant": (2, 2),
    "halfblock": (2, 1),
    "braille": (4, 2),
    "ascii": (2, 1),
}

# braille dot bit per (row, col)
_BRAILLE_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))

_QUADRANT_NAMES = {
    "UPPER LEFT": (0, 0),
    "UPPER RIGHT": (0, 1),
    "LOWER LEFT": (1, 0),
    "LOWER RIGHT": (1, 1),
}

ASCII_RAMP = " .:-=+*#%@"


def _mask_from_cells(cells: Iterable[int], width: int) -> int:
    mask = 0
    for cell in cells:
        index = cell - 1
        if index < 0:
            continue
        row, column = divmod(index, width)
        mask |= 1 << (row * width + column)
    return mask


def _build_named_table(prefix: str, start: int, end: int, width: int) -> dict[int, str]:
    table: dict[int, str] = {}
    for codepoint in range(start, end):
        try:
            name = unicodedata.name(chr(codepoint))
        except ValueError:
            continue
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix) :].strip()
        if not suffix or not suffix.isdigit():
            continue
        mask = _mask_from_cells((int(digit) for digit in suffix), width)
        table[mask] = chr(codepoint)
    return table


def _build_quadrant_table() -> dict[int, str]:
    table: dict[int, str] = {}
    for codepoint in range(0x2596, 0x25A0):
        try:
            name = unicodedata.name(chr(codepoint))
        except ValueError:
            continue
        if name == "FULL BLOCK":
            table[0b1111] = chr(codepoint)
            continue
        if not name.startswith("QUADRANT "):
            continue
        mask = 0
        for label, (row, column) in _QUADRANT_NAMES.items():
            if label in name:
                mask |= 1 << (row * 2 + column)
        table[mask] = chr(codepoint)
    return table


def _build_braille_table() -> dict[int, str]:
    return {mask: chr(0x2800 + mask) for mask in range(256)}


def _with_specials(table: dict[int, str], full: int, width: int) -> dict[int, str]:
    """Add empty/left/right/full patterns, which Unicode stores as block chars."""
    enriched = dict(table)
    enriched[0] = " "
    height = full.bit_length() // width
    left = sum(1 << (row * width) for row in range(height))
    right = sum(1 << (row * width + width - 1) for row in range(height))
    enriched[left] = "▌"
    enriched[right] = "▐"
    enriched[full] = "█"
    return enriched


SEXTANT_TABLE = _with_specials(_build_named_table("BLOCK SEXTANT-", 0x1FB00, 0x1FB3C, 2), 0b111111, 2)
OCTANT_TABLE = _with_specials(_build_named_table("BLOCK OCTANT-", 0x1CD00, 0x1CE00, 2), 0b11111111, 2)
QUADRANT_TABLE = _with_specials(_build_quadrant_table(), 0b1111, 2)
BRAILLE_TABLE = _build_braille_table()
HALFBLOCK_TABLE = {0b00: " ", 0b01: "▀", 0b10: "▄", 0b11: "█"}

PATTERN_TABLES: dict[str, dict[int, str]] = {
    "octant": OCTANT_TABLE,
    "sextant": SEXTANT_TABLE,
    "quadrant": QUADRANT_TABLE,
    "halfblock": HALFBLOCK_TABLE,
    "braille": BRAILLE_TABLE,
}


@dataclass(frozen=True, slots=True)
class Cell:
    """One terminal cell produced by the fidelity renderer."""

    char: str
    fg: str | None = None
    bg: str | None = None


@dataclass
class FrameBuffer:
    """Cell-level delta tracker: only changed cells need re-emitting."""

    rows: tuple[tuple[Cell, ...], ...] = field(default_factory=tuple)

    def diff(self, rows: Sequence[Sequence[Cell]]) -> tuple[tuple[int, int, Cell], ...]:
        changes: list[tuple[int, int, Cell]] = []
        previous = self.rows
        for row_index, row in enumerate(rows):
            old_row = previous[row_index] if row_index < len(previous) else ()
            for column_index, cell in enumerate(row):
                old_cell = old_row[column_index] if column_index < len(old_row) else None
                if old_cell != cell:
                    changes.append((row_index, column_index, cell))
        return tuple(changes)

    def store(self, rows: Sequence[Sequence[Cell]]) -> None:
        self.rows = tuple(tuple(row) for row in rows)


def detect_mode(env: Mapping[str, str] | None = None) -> str:
    """Pick a conservative default mode from the environment alone."""
    environment = env if env is not None else os.environ
    term = environment.get("TERM", "")
    encoding = environment.get("PYTHONIOENCODING", "utf-8") or "utf-8"
    if environment.get("NO_COLOR") or term in ("", "dumb") or "utf" not in encoding.lower():
        return "ascii"
    return DEFAULT_MODE


def resolve_mode(configured: str | None, env: Mapping[str, str] | None = None) -> str:
    """Resolve an explicit fidelity setting, otherwise auto-detect."""
    if configured in MODES:
        return configured
    return detect_mode(env)


def floyd_steinberg(grid: np.ndarray) -> np.ndarray:
    """Error-diffusion dithering for continuous-tone material."""
    work = grid.astype(np.float64).copy()
    height, width = work.shape
    for y in range(height):
        for x in range(width):
            old = work[y, x]
            new = 1.0 if old > 0.5 else 0.0
            work[y, x] = new
            error = old - new
            if x + 1 < width:
                work[y, x + 1] += error * 7 / 16
            if y + 1 < height:
                if x > 0:
                    work[y + 1, x - 1] += error * 3 / 16
                work[y + 1, x] += error * 5 / 16
                if x + 1 < width:
                    work[y + 1, x + 1] += error * 1 / 16
    return np.clip(work, 0.0, 1.0)


def atkinson(grid: np.ndarray) -> np.ndarray:
    """Higher-contrast dithering used for line art and portraits."""
    work = grid.astype(np.float64).copy()
    height, width = work.shape
    for y in range(height):
        for x in range(width):
            old = work[y, x]
            new = 1.0 if old > 0.5 else 0.0
            work[y, x] = new
            error = (old - new) / 8.0
            for dy, dx in ((0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    work[ny, nx] += error
    return np.clip(work, 0.0, 1.0)


DITHERERS = {"floyd": floyd_steinberg, "floyd_steinberg": floyd_steinberg, "atkinson": atkinson}


def _pad_grid(grid: np.ndarray, rows_per_cell: int, cols_per_cell: int) -> np.ndarray:
    height, width = grid.shape
    pad_h = (-height) % rows_per_cell
    pad_w = (-width) % cols_per_cell
    if pad_h or pad_w:
        return np.pad(grid, ((0, pad_h), (0, pad_w)), mode="constant")
    return grid


def _nearest_pattern(mask: int, table: Mapping[int, str]) -> str:
    if mask in table:
        return table[mask]
    best_mask: int | None = None
    best_distance = mask.bit_length() + 1
    for candidate in sorted(table):
        if candidate == 0:
            continue  # never collapse a lit cell to blank
        distance = bin(mask ^ candidate).count("1")
        if distance < best_distance:
            best_mask, best_distance = candidate, distance
    if best_mask is None:
        return table.get(0, " ")
    return table[best_mask]


_LOOKUP_CACHE: dict[str, tuple[str, ...]] = {}


def _pattern_lookup(mode: str) -> tuple[str, ...]:
    """256-entry mask-to-glyph table with nearest-pattern fallback baked in."""
    cached = _LOOKUP_CACHE.get(mode)
    if cached is None:
        table = PATTERN_TABLES.get(mode, {})
        cached = tuple(_nearest_pattern(mask, table) for mask in range(256))
        _LOOKUP_CACHE[mode] = cached
    return cached


def render_bitmap(
    grid: np.ndarray,
    mode: str = DEFAULT_MODE,
    *,
    fg: str | None = None,
    bg: str | None = None,
    threshold: float = 0.5,
    dither: str | None = None,
) -> list[list[Cell]]:
    """Render a coverage grid into terminal cells for the requested mode."""
    if mode not in MODES:
        mode = DEFAULT_MODE
    work = np.asarray(grid, dtype=np.float64)
    if work.ndim == 1:
        work = work[:, None]
    if dither:
        ditherer = DITHERERS.get(dither)
        if ditherer is not None:
            work = ditherer(work)

    rows_per_cell, cols_per_cell = CELL_GEOMETRY[mode]
    work = _pad_grid(work, rows_per_cell, cols_per_cell)
    cell_rows = work.shape[0] // rows_per_cell
    cell_cols = work.shape[1] // cols_per_cell
    cells = work.reshape(cell_rows, rows_per_cell, cell_cols, cols_per_cell).transpose(0, 2, 1, 3)
    on = cells > threshold

    if mode == "ascii":
        means = cells.mean(axis=(2, 3))
        indices = np.clip(
            np.round(means * (len(ASCII_RAMP) - 1)).astype(int),
            0,
            len(ASCII_RAMP) - 1,
        )
        return [
            [Cell(ASCII_RAMP[int(indices[r][c])], fg, None) for c in range(cell_cols)]
            for r in range(cell_rows)
        ]

    if mode == "braille":
        braille_bits = np.array(_BRAILLE_BITS, dtype=np.int64)
        masks = (on * braille_bits).sum(axis=(2, 3))
        return [
            [Cell(BRAILLE_TABLE[int(masks[r][c])], fg, None) for c in range(cell_cols)]
            for r in range(cell_rows)
        ]

    bit_values = (1 << np.arange(rows_per_cell * cols_per_cell)).reshape(rows_per_cell, cols_per_cell)
    masks = (on * bit_values).sum(axis=(2, 3))
    lookup = _pattern_lookup(mode)
    return [
        [Cell(lookup[int(masks[r][c])], fg, bg) for c in range(cell_cols)]
        for r in range(cell_rows)
    ]


def _cell_style(cell: Cell, default_fg: str | None) -> Style | None:
    if not (cell.fg or cell.bg or default_fg):
        return None
    color = cell.fg or default_fg
    if cell.bg:
        return Style(color=color, bgcolor=cell.bg)
    return Style(color=color)


def render_to_text(rows: Sequence[Sequence[Cell]], *, default_fg: str | None = None) -> Text:
    """Flatten cells into a rich Text, grouping runs with identical styles."""
    text = Text()
    for row_index, row in enumerate(rows):
        if row_index:
            text.append("\n")
        run_chars: list[str] = []
        run_style: Style | None = None
        for cell in row:
            style = _cell_style(cell, default_fg)
            if style != run_style:
                if run_chars:
                    text.append("".join(run_chars), style=run_style)
                run_chars = []
                run_style = style
            run_chars.append(cell.char)
        if run_chars:
            text.append("".join(run_chars), style=run_style)
    return text
