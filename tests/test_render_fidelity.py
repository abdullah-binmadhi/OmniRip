"""Unit tests for the terminal render-fidelity engine."""

import numpy as np

from harvester.ui.render_fidelity import (
    CELL_GEOMETRY,
    OCTANT_TABLE,
    QUADRANT_TABLE,
    SEXTANT_TABLE,
    Cell,
    FrameBuffer,
    atkinson,
    detect_mode,
    floyd_steinberg,
    render_bitmap,
    render_to_text,
    resolve_mode,
)


def test_pattern_tables_are_built_from_unicode_names():
    # Sextant top row (cells 1 and 2) is U+1FB02; left column collapses to half block.
    assert SEXTANT_TABLE[0b000011] == chr(0x1FB02)
    assert SEXTANT_TABLE[0b010101] == "▌"
    assert SEXTANT_TABLE[0b111111] == "█"
    # Octants use row-major cell numbering: first encoded pattern is OCTANT-3 (mask 4).
    assert OCTANT_TABLE[0b00000100] == chr(0x1CD00)
    assert OCTANT_TABLE[0b01010101] == "▌"
    assert OCTANT_TABLE[0b11111111] == "█"
    # Quadrants: upper-left single cell and full block.
    assert QUADRANT_TABLE[0b0001] == chr(0x2598)
    assert QUADRANT_TABLE[0b1111] == "█"
    for table in (SEXTANT_TABLE, OCTANT_TABLE, QUADRANT_TABLE):
        assert all(len(char) == 1 for char in table.values())


def test_cell_geometry_is_declared_for_every_mode():
    assert set(CELL_GEOMETRY) == {"octant", "sextant", "quadrant", "halfblock", "braille", "ascii"}


def test_render_bitmap_shapes_and_empty_grid():
    grid = np.zeros((8, 8), dtype=np.float64)
    for mode in CELL_GEOMETRY:
        rows = render_bitmap(grid, mode, fg="#ffffff")
        rows_per_cell, cols_per_cell = CELL_GEOMETRY[mode]
        expected_rows = -(-8 // rows_per_cell)
        expected_cols = -(-8 // cols_per_cell)
        assert len(rows) == expected_rows
        assert all(len(row) == expected_cols for row in rows)
        assert all(cell.fg == "#ffffff" for row in rows for cell in row)


def test_shape_match_selects_exact_pattern():
    grid = np.array([[1.0, 1.0], [0.0, 0.0], [0.0, 0.0]])
    rows = render_bitmap(grid, "sextant", fg="#00ffcc", bg="#000000")
    assert rows[0][0].char == chr(0x1FB02)
    assert rows[0][0].bg == "#000000"


def test_octant_missing_patterns_fall_back_to_nearest():
    # Masks 1 and 2 are not encoded; the engine must still produce a glyph.
    grid = np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    rows = render_bitmap(grid, "octant")
    assert rows[0][0].char != " "


def test_dithering_changes_gradient_output():
    gradient = np.linspace(0.0, 1.0, 64, dtype=np.float64).reshape(8, 8)
    plain = render_bitmap(gradient, "sextant")
    dithered = render_bitmap(gradient, "sextant", dither="floyd")
    assert plain != dithered
    assert floyd_steinberg(gradient).shape == gradient.shape
    assert atkinson(gradient).shape == gradient.shape


def test_frame_buffer_delta_tracks_only_changes():
    first = [[Cell("a"), Cell("b")], [Cell("c"), Cell("d")]]
    buffer = FrameBuffer()
    assert len(buffer.diff(first)) == 4
    buffer.store(first)
    assert buffer.diff(first) == ()
    second = [[Cell("a"), Cell("B")], [Cell("c"), Cell("d")]]
    changes = buffer.diff(second)
    assert changes == ((0, 1, Cell("B")),)


def test_render_to_text_plain_text_matches_cells():
    rows = [[Cell("a", "#ffffff"), Cell("b", "#ffffff")], [Cell("c", "#00ff00")]]
    text = render_to_text(rows)
    assert text.plain == "ab\nc"


def test_mode_detection_and_override():
    assert detect_mode({"TERM": "xterm-256color"}) == "sextant"
    assert detect_mode({"TERM": "xterm-256color", "NO_COLOR": "1"}) == "ascii"
    assert detect_mode({"TERM": "dumb"}) == "ascii"
    assert resolve_mode("octant", {"TERM": "dumb"}) == "octant"
    assert resolve_mode(None, {"TERM": "xterm-256color"}) == "sextant"
    assert resolve_mode("bogus", {"TERM": "xterm-256color"}) == "sextant"
