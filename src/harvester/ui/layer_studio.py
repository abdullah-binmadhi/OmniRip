"""
Layer Studio Widget — FL Studio-Style Multi-Track Stem Arrangement Workstation.

Renders high-density multi-row Braille audio waveforms across dedicated track swimlanes
for separated audio stems (Vocals, Drums, Bass, Instruments/Other, Master Mix).
Features left-hand FL Studio track header cards with interactive Mute [●] and Solo [S]
LED toggles, color badges, dB level meters, dual Bars/Beats and Time timeline rulers,
playhead tracking, and per-second surgical defect repair.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.text import Text
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.widget import Widget

from harvester.analysis.enhancement.layer_editor import (
    EditPlan,
)
from harvester.analysis.enhancement.layers import (
    ISSUE_COLORS,
    LayerSegment,
    LayerTrack,
)

_OP_MARK = "✎"
OP_GLYPHS: dict[str, str] = {
    "mute": "M",
    "de_bleed": "B",
    "de_ess": "S",
    "de_mud": "U",
    "drum_punch": "P",
    "de_hum": "H",
    "air_boost": "A",
    "de_click": "C",
    "noise_gate": "G",
    "transient_tame": "T",
}
_LABEL_COL = 24  # Width of the left-hand FL Studio track header card
TRACK_HEIGHT = 3  # 3 vertical terminal lines per stem lane
HEADER_HEIGHT = 2  # 2 lines: Bars/Beats + Time ruler

STEM_THEMES: dict[str, dict[str, str]] = {
    "vocals": {
        "color": "#ff3399",
        "dim": "#551a3a",
        "bg": "#1c0014",
        "label": "VOCALS",
        "sub": "Lead & Harmony",
    },
    "kick": {
        "color": "#ff5555",
        "dim": "#551818",
        "bg": "#1c0404",
        "label": "KICK",
        "sub": "Drums › Low Punch",
    },
    "snare": {
        "color": "#ff9955",
        "dim": "#553a18",
        "bg": "#1c0e02",
        "label": "SNARE",
        "sub": "Drums › Body & Crack",
    },
    "hats": {
        "color": "#ffdd66",
        "dim": "#554a18",
        "bg": "#1c1602",
        "label": "HATS",
        "sub": "Drums › Cymbals / Air",
    },
    "drums": {
        "color": "#ff4444",
        "dim": "#551818",
        "bg": "#1c0404",
        "label": "DRUMS",
        "sub": "Kicks / Snares / Hi-Hats",
    },
    "sub_bass": {
        "color": "#2266dd",
        "dim": "#122f5c",
        "bg": "#02091a",
        "label": "SUB BASS",
        "sub": "Bass › Sub Frequencies",
    },
    "bass": {
        "color": "#3388ff",
        "dim": "#153366",
        "bg": "#040e24",
        "label": "BASS",
        "sub": "Sub & Low Frequencies",
    },
    "other": {
        "color": "#ffaa00",
        "dim": "#553a00",
        "bg": "#1c1200",
        "label": "INSTRUMENTS",
        "sub": "Keys / Synths / Guitars",
    },
    "guitar": {
        "color": "#00ddaa",
        "dim": "#0b4a3a",
        "bg": "#021712",
        "label": "GUITAR",
        "sub": "Neural › Guitar",
    },
    "piano": {
        "color": "#cc88ff",
        "dim": "#3d2255",
        "bg": "#0d0518",
        "label": "PIANO",
        "sub": "Neural › Piano",
    },
    "mix": {
        "color": "#00e699",
        "dim": "#004d33",
        "bg": "#001a12",
        "label": "MASTER MIX",
        "sub": "Composite Audio",
    },
}

# Braille waveform multi-level glyph pairs for (top, mid, bot) rows
_BRAILLE_LEVELS = [
    (" ", "·", " "),      # Level 0 (Silence / Grid)
    (" ", "⠤", " "),      # Level 1
    (" ", "⣤", " "),      # Level 2
    ("⢀", "⣶", " "),      # Level 3
    ("⢀", "⣶", "⣀"),      # Level 4
    ("⣠", "⣿", "⣀"),      # Level 5
    ("⣴", "⣿", "⣤"),      # Level 6
    ("⣶", "⣿", "⣶"),      # Level 7
    ("⣿", "⣿", "⣿"),      # Level 8 (Peak clipping)
]


class LayerStudio(Widget):
    """
    FL Studio-Style Multi-Track Stem Arrangement Timeline.

    Features interactive track headers (Mute/Solo LEDs, gain meters),
    multi-row Braille waveforms, musical Bars/Beats ruler, and playhead sync.
    """

    DEFAULT_CSS = """
    LayerStudio {
        height: auto;
        min-height: 18;
        width: 1fr;
        background: #0d0e15;
        padding: 0 1;
    }
    """

    class SeekRequested(Message):
        """User clicked a timeline cell and wants playback to jump there."""

        def __init__(self, seconds: float, layer: str | None = None) -> None:
            super().__init__()
            self.seconds = seconds
            self.layer = layer

    class SelectionChanged(Message):
        """A cell/layer was clicked and should be surfaced in the inspector."""

        def __init__(self, segment: LayerSegment | None, layer: str | None = None) -> None:
            super().__init__()
            self.segment = segment
            self.layer = layer

    class EditRequested(Message):
        """A per-second edit op was triggered on the currently selected cell."""

        def __init__(self, segment_idx: int, layer: str | None, op: str) -> None:
            super().__init__()
            self.segment_idx = segment_idx
            self.layer = layer
            self.op = op

    class TrackMuteToggled(Message):
        """User toggled the mute LED of a track."""

        def __init__(self, layer: str, muted: bool) -> None:
            super().__init__()
            self.layer = layer
            self.muted = muted

    class TrackSoloToggled(Message):
        """User toggled the solo button of a track."""

        def __init__(self, layer: str, soloed: bool) -> None:
            super().__init__()
            self.layer = layer
            self.soloed = soloed

    track: reactive[LayerTrack | None] = reactive(None)
    playhead_s: reactive[float] = reactive(0.0)
    edit_plan: reactive[EditPlan | None] = reactive(None)

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._sync_timer: Timer | None = None
        self._scroll_s = 0.0
        self._selected_layer: str | None = None
        self._selected_idx: int | None = None
        self._muted_layers: set[str] = set()
        self._solo_layer: str | None = None
        # Playhead source. When set (detached layer terminal), the widget reads
        # the position from it instead of this process's `#audio-player`, which
        # only exists in the main OmniRip process.
        self.playhead_provider: Callable[[], float] | None = None

    def on_mount(self) -> None:
        self._sync_timer = self.set_interval(0.20, self._sync_playhead)

    def on_unmount(self) -> None:
        if self._sync_timer:
            self._sync_timer.stop()
            self._sync_timer = None

    def watch_track(self, track: LayerTrack | None) -> None:
        self._scroll_s = 0.0
        self._selected_layer = None
        self._selected_idx = None
        self.refresh()

    def _sync_playhead(self) -> None:
        if self.track is None:
            return
        if self.playhead_provider is not None:
            try:
                self.playhead_s = float(self.playhead_provider())
            except Exception:
                return
            return
        try:
            from harvester.ui.player import AudioPlayerWidget

            player: AudioPlayerWidget = self.app.query_one("#audio-player")  # type: ignore
            self.playhead_s = float(player.elapsed_s)
        except Exception:
            return

    def watch_playhead_s(self, seconds: float) -> None:
        if self.track is None:
            return
        col = int(seconds // self.track.segment_size_s)
        visible = max(4, self._visible_cols())
        if col < self._first_visible_col():
            self._scroll_s = max(0.0, col * self.track.segment_size_s)
        elif col >= self._first_visible_col() + visible - 2:
            self._scroll_s = max(
                0.0,
                (col - visible + 2) * self.track.segment_size_s,
            )
        self.refresh()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def _visible_cols(self) -> int:
        if self.track is None:
            return 8
        lab = _LABEL_COL + 1
        return max(8, self.size.width - lab)

    def _first_visible_col(self) -> int:
        return int(self._scroll_s // self.track.segment_size_s) if self.track else 0

    def _last_segment_idx(self) -> int:
        return max(0, self.track.n_segments - 1) if self.track else 0

    def _col_to_seconds(self, col_in_click: int) -> float | None:
        """Map a click x-coordinate (relative to widget) to a timestamp."""
        if self.track is None:
            return None
        grid_x = col_in_click - (_LABEL_COL + 1)
        if grid_x < 0:
            return None
        return (self._first_visible_col() + grid_x) * self.track.segment_size_s

    def _grid_row_to_layer(self, row_in_click: int) -> str | None:
        layers = self.track.active_layers if self.track else []
        rel = row_in_click - HEADER_HEIGHT
        if rel < 0:
            return None
        track_idx = rel // TRACK_HEIGHT
        if 0 <= track_idx < len(layers):
            return layers[track_idx]
        return None

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def on_click(self, event: events.Click) -> None:
        if self.track is None:
            return

        # Check if clicked on Left Track Header card
        if event.x < _LABEL_COL:
            layer = self._grid_row_to_layer(event.y)
            if layer:
                # Col 0..3: Mute toggle [●]
                if event.x <= 3:
                    if layer in self._muted_layers:
                        self._muted_layers.remove(layer)
                        self.post_message(self.TrackMuteToggled(layer, False))
                    else:
                        self._muted_layers.add(layer)
                        self.post_message(self.TrackMuteToggled(layer, True))
                    self.refresh()
                    return
                # Col 4..7: Solo toggle [S]
                elif 4 <= event.x <= 7:
                    if self._solo_layer == layer:
                        self._solo_layer = None
                        self.post_message(self.TrackSoloToggled(layer, False))
                    else:
                        self._solo_layer = layer
                        self.post_message(self.TrackSoloToggled(layer, True))
                    self.refresh()
                    return
                else:
                    self._selected_layer = layer
                    self.refresh()
                    return

        # Clicked on arrangement timeline
        seconds = self._col_to_seconds(event.x)
        if seconds is None:
            return
        idx = min(
            self._last_segment_idx(),
            int(seconds // self.track.segment_size_s),
        )
        seg = self.track.segments[idx] if idx < len(self.track.segments) else None
        layer = self._grid_row_to_layer(event.y)
        self._selected_idx = idx
        self._selected_layer = layer
        self.post_message(self.SeekRequested(seconds, layer))
        self.post_message(self.SelectionChanged(seg, layer))
        self.refresh()

    def action_layer_left(self) -> None:
        if self.track is None:
            return
        self._scroll_s = max(0.0, self._scroll_s - self.track.segment_size_s * 10)
        self.refresh()

    def action_layer_right(self) -> None:
        if self.track is None:
            return
        self._scroll_s = min(
            self.track.n_segments * self.track.segment_size_s,
            self._scroll_s + self.track.segment_size_s * 10,
        )
        self.refresh()

    def action_layer_home(self) -> None:
        self._scroll_s = 0.0
        self.refresh()

    def action_layer_end(self) -> None:
        if self.track is None:
            return
        self._scroll_s = self.track.duration_s
        self.refresh()

    def _selected_cell(self) -> tuple[int, str] | None:
        if self.track is None:
            return None
        layer = self._selected_layer
        idx = self._selected_idx
        if layer is None or idx is None or not (0 <= idx < self.track.n_segments):
            return None
        return idx, layer

    def _request_edit(self, op: str) -> None:
        cell = self._selected_cell()
        if cell is None:
            return
        idx, layer = cell
        self.post_message(self.EditRequested(idx, layer, op))

    def action_edit_mute(self) -> None:
        self._request_edit("mute")

    def action_edit_de_bleed(self) -> None:
        self._request_edit("de_bleed")

    def action_edit_de_ess(self) -> None:
        self._request_edit("de_ess")

    def action_edit_de_mud(self) -> None:
        self._request_edit("de_mud")

    def action_edit_drum_punch(self) -> None:
        self._request_edit("drum_punch")

    def action_edit_de_hum(self) -> None:
        self._request_edit("de_hum")

    def action_edit_air_boost(self) -> None:
        self._request_edit("air_boost")

    def action_edit_de_click(self) -> None:
        self._request_edit("de_click")

    def action_edit_noise_gate(self) -> None:
        self._request_edit("noise_gate")

    def action_edit_transient_tame(self) -> None:
        self._request_edit("transient_tame")

    def action_edit_reset(self) -> None:
        self._request_edit("reset")

    BINDINGS = [
        ("left", "layer_left", "Scroll left"),
        ("right", "layer_right", "Scroll right"),
        ("home", "layer_home", "Scroll start"),
        ("end", "layer_end", "Scroll end"),
        ("m", "edit_mute", "Mute"),
        ("b", "edit_de_bleed", "De-Bleed"),
        ("s", "edit_de_ess", "De-Ess"),
        ("u", "edit_de_mud", "De-Mud"),
        ("p", "edit_drum_punch", "Punch"),
        ("h", "edit_de_hum", "De-Hum"),
        ("a", "edit_air_boost", "Air+"),
        ("c", "edit_de_click", "De-Click"),
        ("g", "edit_noise_gate", "Gate"),
        ("t", "edit_transient_tame", "Tame"),
        ("r", "edit_reset", "Reset"),
    ]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(self) -> Text:
        t = Text()
        if self.track is None:
            t.append("\n  ┌─ FL STUDIO STEM ARRANGEMENT ───────────────────────────────────────────────┐\n", style="bold cyan")
            t.append("  │ Separate a track in the STEMS tab to load multi-track waveform swimlanes.  │\n", style="dim white")
            t.append("  └────────────────────────────────────────────────────────────────────────────┘\n", style="bold cyan")
            return t

        layers = self.track.active_layers
        visible = self._visible_cols()
        first_idx = self._first_visible_col()
        playhead_idx = int(self.playhead_s // self.track.segment_size_s)
        seg_size = self.track.segment_size_s

        # 1. RULER LINE 1: Musical Bars & Beats (4 seconds = 1 Bar @ 120 BPM 4/4)
        t.append("   BARS / BEATS       │", style="bold #667799")
        for col in range(visible):
            seg_idx = first_idx + col
            bar_num = (seg_idx // 4) + 1
            beat_num = (seg_idx % 4) + 1
            is_playhead = seg_idx == playhead_idx
            if beat_num == 1:
                t.append(f"{bar_num}.1", style="bold bright_white" if is_playhead else "bold #00ddff")
            elif col % 2 == 0:
                t.append(f".{beat_num}", style="bold #ffcc00" if is_playhead else "dim #446688")
            else:
                t.append(" ", style="dim")
        t.append("\n")

        # 2. RULER LINE 2: Timeline Timestamps & Playhead Cursor
        t.append("   TIME (SECONDS)     │", style="bold #667799")
        for col in range(visible):
            seg_idx = first_idx + col
            sec = int(seg_idx * seg_size)
            is_playhead = seg_idx == playhead_idx
            if is_playhead:
                t.append("▶", style="bold #00ffcc on #113344")
            elif col % 10 == 0:
                s_str = f"{sec}s"
                t.append(s_str[:2], style="dim cyan")
            elif col % 5 == 0:
                t.append("┼", style="dim #445566")
            else:
                t.append("·", style="dim #223344")
        t.append("\n")

        # Top border separator
        t.append("─" * _LABEL_COL + "┼" + "─" * visible + "\n", style="dim #334455")

        # Empty-state hint: built track but no resolvable layer sources.
        if not layers:
            hint = " No layer sources found in this stem set — run ⚡ BUILD STEMS to regenerate. "
            pad = max(2, (visible - len(hint)) // 2)
            trail = max(1, visible - pad - len(hint))
            t.append(
                " " * _LABEL_COL + "│" + " " * visible + "\n",
                style="dim #223344",
            )
            t.append(
                " " * _LABEL_COL + "│" + " " * pad + hint + " " * trail + "\n",
                style="#ffcc00 on #223344",
            )
            t.append(
                " " * _LABEL_COL + "│" + " " * visible + "\n",
                style="dim #223344",
            )

        # 3. Render Each FL Studio Multi-Row Track Lane
        for layer_name in layers:
            src = self.track.sources.get(layer_name)
            theme = STEM_THEMES.get(layer_name, STEM_THEMES["other"])
            is_muted = layer_name in self._muted_layers or (
                self._solo_layer is not None and self._solo_layer != layer_name
            )
            is_soloed = self._solo_layer == layer_name

            # Peak and average dB level
            avg_rms = float(src.rms.mean()) if (src is not None and src.rms.size > 0) else -60.0
            level_str = f"{avg_rms:+.1f}dB" if avg_rms > -55.0 else "-inf dB"

            # Render 3 Vertical Lines for this Track
            row_lines: list[Text] = [Text(), Text(), Text()]

            # --- Line 0: Track Header Top + Upper Waveform Peak ---
            led_glyph = " [●] " if not is_muted else " [○] "
            led_style = "bold #00ff66" if not is_muted else "dim #555566"
            solo_glyph = "[S] "
            solo_style = "bold #ffcc00" if is_soloed else "dim #666677"
            display_title = (theme["label"][:11]).ljust(11)

            h0 = Text()
            h0.append(led_glyph, style=led_style)
            h0.append(solo_glyph, style=solo_style)
            h0.append(display_title, style=f"bold {theme['color']}")
            h0.append("│", style="dim #334455")
            row_lines[0].append(h0)

            # --- Line 1: Track Header Mid (Sub-type & dB) + Core Waveform Body ---
            sub_info = f" █ {theme['sub'][:11]} {level_str:>6} "
            h1 = Text()
            h1.append(sub_info[:_LABEL_COL], style=f"dim {theme['color']}" if not is_muted else "dim #444455")
            h1.append("│", style="dim #334455")
            row_lines[1].append(h1)

            # --- Line 2: Track Divider Line + Lower Waveform / Floor ---
            h2 = Text()
            h2.append("─" * _LABEL_COL, style="dim #334455")
            h2.append("┼", style="dim #334455")
            row_lines[2].append(h2)

            # --- Waveform Columns (Right Arrangement Grid) ---
            for col in range(visible):
                seg_idx = first_idx + col
                in_range = 0 <= seg_idx < self.track.n_segments
                seg = self.track.segments[seg_idx] if in_range else None
                lvl = src.level(seg_idx) if (src and in_range) else 0.0
                is_playhead = seg_idx == playhead_idx
                selected = self._selected_layer == layer_name and self._selected_idx == seg_idx
                op = self.edit_plan.get(layer_name, seg_idx) if self.edit_plan else None
                has_issue = any(i.layer == layer_name for i in (seg.issues if seg else []))
                issue = seg.primary_issue if seg else None

                # Calculate Braille level (0..8)
                bin_idx = max(0, min(8, int(round(lvl * 8)))) if lvl > 0.01 else 0
                g_top, g_mid, g_bot = _BRAILLE_LEVELS[bin_idx]

                # Styling
                if op:
                    c_style = "bold #ffffff on #8800aa"
                    badge = OP_GLYPHS.get(op, "✎")
                    g_top, g_mid, g_bot = "✎", badge, " "
                elif has_issue:
                    c_color = issue.color if issue else ISSUE_COLORS.get("vocal_bleed", "#ff3366")
                    c_style = f"bold {c_color}"
                elif is_muted:
                    c_style = "dim #333344"
                elif selected:
                    c_style = "bold #ffcc00 on #332200"
                else:
                    c_style = f"bold {theme['color']}"

                if is_playhead:
                    # White playhead cursor stripe
                    row_lines[0].append("┃", style="bold bright_white on #004455")
                    row_lines[1].append("┃", style="bold bright_white on #004455")
                    row_lines[2].append("┃", style="bold bright_white on #004455")
                else:
                    row_lines[0].append(g_top, style=c_style)
                    row_lines[1].append(g_mid, style=c_style)
                    row_lines[2].append("─" if bin_idx == 0 else g_bot, style="dim #223344" if bin_idx == 0 else c_style)

            # Append track lines to widget text
            for line in row_lines:
                t.append(line)
                t.append("\n")

        return t