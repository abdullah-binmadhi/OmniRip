"""Modular Dynamic Audio Visualizer Dashboard for OmniRip TUI."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select

from harvester.services.stitch import StitchTheme
from harvester.ui.full_vision_designs import SUPPORTED_DASHBOARD_LAYOUTS
from harvester.ui.visuals.audio_features import build_feature_track
from harvester.ui.visuals.base import (
    PALETTES,
    AudioFeatureContext,
    BaseVisualizerEngine,
    ColorPalette,
)
from harvester.ui.visuals.registry import CATEGORIES, VisualizerRegistry

AVAILABLE_PALETTE_KEYS: list[str] = ["cyan", "neon", "matrix", "thermal", "sunset", "crt", "stanford"]


class VisualizerEngineCanvas(Widget):
    """Low-level canvas rendering a specific visualizer engine at 30 FPS."""

    DEFAULT_CSS = """
    VisualizerEngineCanvas {
        height: 1fr;
        width: 1fr;
        min-height: 4;
        background: transparent;
        padding: 0;
    }
    """

    def __init__(
        self,
        engine: BaseVisualizerEngine,
        palette_key: str = "cyan",
        id: str | None = None,
        classes: str | None = None,
        palette_override: ColorPalette | None = None,
        clock_managed_externally: bool = False,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.engine = engine
        self.palette_key = palette_key
        self.palette_override = palette_override
        self.clock_managed_externally = clock_managed_externally
        self.feature_ctx = AudioFeatureContext.synthesize_idle()
        self._idle_phase = 0.0
        self._anim_timer: Timer | None = None
        self._feature_track: list[AudioFeatureContext] = []
        self._feature_idx = 0
        # Last context pushed by a live per-frame feed, held between pushes.
        self._live_ctx: AudioFeatureContext | None = None

    def on_mount(self) -> None:
        if not self.clock_managed_externally:
            self._anim_timer = self.set_interval(1.0 / 60.0, self._on_tick)

    def on_unmount(self) -> None:
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None

    def _on_tick(self) -> None:
        self.advance_frame()

    def advance_frame(self, ctx: AudioFeatureContext | None = None) -> None:
        """Advance one animation frame; parent dashboards can own the clock."""
        self._idle_phase = (self._idle_phase + 0.04) % (2.0 * np.pi * 100.0)
        if self._feature_track:
            self._feature_idx = (self._feature_idx + 1) % len(self._feature_track)
            self.feature_ctx = self._feature_track[self._feature_idx]
            self._live_ctx = None
        elif ctx is not None:
            self._live_ctx = ctx
            self.feature_ctx = ctx
        elif self._live_ctx is None:
            self.feature_ctx = AudioFeatureContext.synthesize_idle(self._idle_phase)
        self.refresh()

    def on_click(self) -> None:
        if self.parent and hasattr(self.parent, "select"):
            self.parent.select()
            self.parent.focus()

    def set_audio_features(self, ctx: AudioFeatureContext) -> None:
        """Push a single live frame, which the animation loop then holds.

        The animation timer would otherwise overwrite this with standby
        synthesis between pushes, so a live feed is latched until it is cleared
        or replaced by a feature track.
        """
        self._live_ctx = ctx
        self.feature_ctx = ctx
        self.refresh()

    def set_feature_track(self, track: Sequence[AudioFeatureContext]) -> None:
        """Install a pre-computed feature track and start playing it from the top."""
        self._feature_track = list(track)
        self._feature_idx = 0
        self._live_ctx = None
        if self._feature_track:
            self.feature_ctx = self._feature_track[0]
        self.refresh()

    def clear_feature_track(self) -> None:
        """Return to standby synthesis, e.g. when playback stops."""
        self._feature_track = []
        self._feature_idx = 0
        self._live_ctx = None

    def render(self) -> Text:
        w = max(self.engine.min_width, self.size.width)
        h = max(self.engine.min_height, self.size.height)
        palette = self.palette_override or PALETTES.get(self.palette_key, PALETTES["cyan"])
        return self.engine.render_frame(w, h, self.feature_ctx, self._idle_phase, palette)


class VisualizerCard(Widget):
    """An interactive card tile on the dashboard housing a visualizer engine."""

    DEFAULT_CSS = """
    VisualizerCard {
        height: 1fr;
        width: 1fr;
        min-height: 8;
        border: round $secondary;
        background: #0d0e15;
        margin: 0;
        padding: 0;
    }
    VisualizerCard.-selected {
        border: double #00e5ff;
        background: #120e24;
    }
    VisualizerCard.-span-full {
        width: 100%;
    }
    VisualizerCard.-hero {
        width: 2fr;
        height: 2fr;
        min-height: 14;
    }
    VisualizerCard.-wide {
        width: 2fr;
    }
    VisualizerCard.-compact {
        height: 1fr;
        min-height: 6;
    }
    VisualizerCard.-tall {
        height: 2fr;
        min-height: 14;
    }
    VisualizerCard.-read-only .vis-card-btn-palette,
    VisualizerCard.-read-only .vis-card-btn-close,
    VisualizerCard.-read-only .vis-card-arrange-bar {
        display: none;
    }
    .vis-grid-col {
        width: 1fr;
        height: 100%;
    }
    .vis-grid-col.-hero {
        width: 2fr;
    }
    .vis-grid-col.-sidebar {
        width: 1fr;
    }
    .vis-card-header {
        height: 1;
        width: 1fr;
        background: $surface;
        padding: 0 1;
        align: left middle;
        border-bottom: solid $surface-lighten-1;
    }
    .vis-card-title {
        width: 1fr;
        height: 1;
        color: $warning;
        text-style: bold;
    }
    .vis-card-btn-palette {
        min-width: 8;
        height: 1;
        border: none;
        background: transparent;
        color: $accent;
        text-style: bold;
        padding: 0;
        margin-right: 1;
    }
    .vis-card-btn-palette:hover {
        background: $panel;
        color: #ffffff;
    }
    .vis-card-btn-close {
        min-width: 3;
        height: 1;
        border: none;
        background: transparent;
        color: $error;
        text-style: bold;
        padding: 0;
    }
    .vis-card-btn-close:hover {
        background: $error;
        color: #ffffff;
    }
    .vis-card-arrange-bar {
        height: 3;
        width: 1fr;
        background: #18132c;
        border-top: solid #2d264f;
        border-bottom: solid #2d264f;
        padding: 0 1;
        align: left middle;
        display: none;
    }
    VisualizerCard.-selected .vis-card-arrange-bar {
        display: block;
    }
    .vis-card-nav-btn {
        height: 3;
        min-height: 3;
        min-width: 9;
        border: solid #2d264f;
        background: #251c47;
        color: #00e5ff;
        text-style: bold;
        margin-right: 1;
        padding: 0 1;
    }
    .vis-card-nav-btn:hover {
        background: #00e5ff;
        color: #050b14;
    }
    .vis-card-arrange-hint {
        color: #ffe600;
        text-style: bold;
        margin-left: 1;
    }
    """

    can_focus = True

    class RemoveRequested(Message):
        def __init__(self, card_id: str) -> None:
            super().__init__()
            self.card_id = card_id

    class SelectRequested(Message):
        def __init__(self, card_id: str) -> None:
            super().__init__()
            self.card_id = card_id

    class MoveRequested(Message):
        def __init__(self, card_id: str, direction: str) -> None:
            super().__init__()
            self.card_id = card_id
            self.direction = direction

    class ResizeRequested(Message):
        def __init__(self, card_id: str, resize_type: str) -> None:
            super().__init__()
            self.card_id = card_id
            self.resize_type = resize_type

    def __init__(
        self,
        engine_id: str,
        palette_key: str = "cyan",
        card_id: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        palette_override: ColorPalette | None = None,
        theme: StitchTheme | None = None,
        is_read_only: bool = False,
        clock_managed_externally: bool = False,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.card_id = card_id or str(uuid.uuid4())[:8]
        self.engine_id = engine_id
        self.palette_key = palette_key
        self.palette_override = palette_override
        self.theme = theme
        self.is_read_only = is_read_only
        self.clock_managed_externally = clock_managed_externally
        if is_read_only:
            self.add_class("-read-only")
        engine = VisualizerRegistry.get(engine_id)
        if not engine:
            from harvester.ui.visuals.registry import MirroredDanceEngine
            engine = MirroredDanceEngine()
        self.engine = engine
        self.canvas = VisualizerEngineCanvas(
            engine=self.engine,
            palette_key=self.palette_key,
            palette_override=self.palette_override,
            clock_managed_externally=self.clock_managed_externally,
        )

    def on_mount(self) -> None:
        if self.theme is not None:
            self.apply_theme(self.theme)

    def apply_theme(self, theme: StitchTheme) -> None:
        """Apply the theme's panel material after the card's children are mounted."""
        allowed_borders = {"heavy", "double", "round", "ascii", "tall", "solid", "dashed"}
        border_type = cast(
            Literal["heavy", "double", "round", "ascii", "tall", "solid", "dashed"],
            theme.border_style if theme.border_style in allowed_borders else "heavy",
        )
        self.styles.background = theme.surface_color
        self.styles.border = (border_type, theme.primary_color)
        header = self.query_one(".vis-card-header", Horizontal)
        header.styles.background = theme.surface_color
        header.styles.border_bottom = ("solid", theme.secondary_color)
        title = self.query_one(".vis-card-title", Label)
        title.styles.color = theme.primary_color
        self.canvas.styles.background = theme.background_color
        palette_button = self.query_one(f"#btn-pal-{self.card_id}", Button)
        palette_button.styles.color = theme.accent_color
        close_button = self.query_one(f"#btn-close-{self.card_id}", Button)
        close_button.styles.color = theme.accent_color

    def compose(self) -> ComposeResult:
        with Horizontal(classes="vis-card-header"):
            yield Label(f"{self.engine.icon} {self.engine.name}", classes="vis-card-title")
            yield Button(
                f"[{self.palette_key.upper()}]",
                id=f"btn-pal-{self.card_id}",
                classes="vis-card-btn-palette",
            )
            yield Button("✕", id=f"btn-close-{self.card_id}", classes="vis-card-btn-close")
        with Horizontal(classes="vis-card-arrange-bar", id=f"vis-arrange-bar-{self.card_id}"):
            yield Button("◀ LEFT", id=f"btn-move-left-{self.card_id}", classes="vis-card-nav-btn")
            yield Button("▲ UP", id=f"btn-move-up-{self.card_id}", classes="vis-card-nav-btn")
            yield Button("▼ DOWN", id=f"btn-move-down-{self.card_id}", classes="vis-card-nav-btn")
            yield Button("▶ RIGHT", id=f"btn-move-right-{self.card_id}", classes="vis-card-nav-btn")
            yield Button("⇲ SPAN", id=f"btn-span-{self.card_id}", classes="vis-card-nav-btn")
            yield Button("⤢ TALL", id=f"btn-tall-{self.card_id}", classes="vis-card-nav-btn")
            yield Label("⌨ ARROWS: MOVE | S: SPAN | T: TALL", classes="vis-card-arrange-hint")
        yield self.canvas

    def select(self) -> None:
        self.post_message(self.SelectRequested(self.card_id))

    def on_click(self) -> None:
        self.select()
        self.focus()

    def on_key(self, event: events.Key) -> None:
        if self.is_read_only:
            return
        k = event.key
        if k in ("left", "h"):
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "left"))
        elif k in ("right", "l"):
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "right"))
        elif k in ("up", "k"):
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "up"))
        elif k in ("down", "j"):
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "down"))
        elif k in ("s", "space"):
            event.stop()
            self.post_message(self.ResizeRequested(self.card_id, "span"))
        elif k in ("t",):
            event.stop()
            self.post_message(self.ResizeRequested(self.card_id, "tall"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.is_read_only:
            event.stop()
            return
        bid = event.button.id or ""
        if bid == f"btn-close-{self.card_id}":
            event.stop()
            self.post_message(self.RemoveRequested(self.card_id))
        elif bid == f"btn-pal-{self.card_id}":
            event.stop()
            self.cycle_palette()
        elif bid == f"btn-move-left-{self.card_id}":
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "left"))
        elif bid == f"btn-move-right-{self.card_id}":
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "right"))
        elif bid == f"btn-move-up-{self.card_id}":
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "up"))
        elif bid == f"btn-move-down-{self.card_id}":
            event.stop()
            self.post_message(self.MoveRequested(self.card_id, "down"))
        elif bid == f"btn-span-{self.card_id}":
            event.stop()
            self.post_message(self.ResizeRequested(self.card_id, "span"))
        elif bid == f"btn-tall-{self.card_id}":
            event.stop()
            self.post_message(self.ResizeRequested(self.card_id, "tall"))

    def set_read_only(self, read_only: bool) -> None:
        self.is_read_only = read_only
        if read_only:
            self.add_class("-read-only")
        else:
            self.remove_class("-read-only")

    def cycle_palette(self) -> None:
        if self.is_read_only:
            return
        try:
            curr_idx = AVAILABLE_PALETTE_KEYS.index(self.palette_key)
            next_idx = (curr_idx + 1) % len(AVAILABLE_PALETTE_KEYS)
            self.palette_key = AVAILABLE_PALETTE_KEYS[next_idx]
        except ValueError:
            self.palette_key = "cyan"
        self.palette_override = None
        self.canvas.palette_override = None
        self.canvas.palette_key = self.palette_key
        btn = self.query_one(f"#btn-pal-{self.card_id}", Button)
        btn.label = f"[{self.palette_key.upper()}]"

    def feed_audio(self, ctx: AudioFeatureContext) -> None:
        self.canvas.set_audio_features(ctx)

    def tick_frame(self, ctx: AudioFeatureContext | None = None) -> None:
        self.canvas.advance_frame(ctx)

    def set_feature_track(self, track: Sequence[AudioFeatureContext]) -> None:
        self.canvas.set_feature_track(track)


class VisualCatalogModal(ModalScreen[str | None]):
    """Catalog browser modal dialog to search, preview, and add visualizers."""

    DEFAULT_CSS = """
    VisualCatalogModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #vis-catalog-dialog {
        width: 80;
        height: 32;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #vis-catalog-header {
        height: 2;
        width: 1fr;
        color: $accent;
        text-style: bold;
        border-bottom: solid $secondary;
        margin-bottom: 1;
    }
    #vis-catalog-filter-bar {
        height: 3;
        width: 1fr;
        margin-bottom: 1;
    }
    #vis-catalog-search {
        width: 1fr;
        margin-right: 1;
    }
    #vis-catalog-category {
        width: 30;
    }
    #vis-catalog-list {
        height: 1fr;
        width: 1fr;
        background: $panel;
        padding: 0 1;
    }
    .vis-item-row {
        height: 4;
        width: 1fr;
        border-bottom: solid $surface-lighten-1;
        padding: 0 1;
        margin-bottom: 1;
    }
    .vis-item-info {
        width: 1fr;
        height: 3;
    }
    .vis-item-name {
        color: $warning;
        text-style: bold;
    }
    .vis-item-desc {
        color: $text-muted;
    }
    .vis-item-btn-add {
        min-width: 12;
        height: 3;
        margin-left: 1;
    }
    #vis-catalog-footer {
        height: 3;
        width: 1fr;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.query_text = ""
        self.selected_category = "all"

    def compose(self) -> ComposeResult:
        with Vertical(id="vis-catalog-dialog"):
            yield Label("⌗ AUDIO VISUALIZER CATALOG [100 ENGINES]", id="vis-catalog-header")
            with Horizontal(id="vis-catalog-filter-bar"):
                yield Input(placeholder="Search visualizers (name, tags, description)...", id="vis-catalog-search")
                cat_options = [("All Categories", "all")] + [
                    (f"{meta[0]} {meta[1]}", key) for key, meta in CATEGORIES.items()
                ]
                yield Select(options=cat_options, value="all", id="vis-catalog-category", prompt="Filter Category")
            with VerticalScroll(id="vis-catalog-list"):
                yield from self._render_items()
            with Horizontal(id="vis-catalog-footer"):
                yield Button("CLOSE [ESC]", id="btn-catalog-close", variant="default")

    def _render_items(self) -> ComposeResult:
        engines = VisualizerRegistry.list_all()
        if self.selected_category != "all":
            engines = [e for e in engines if e.category == self.selected_category]
        if self.query_text:
            q = self.query_text.lower()
            engines = [
                e for e in engines
                if q in e.name.lower() or q in e.description.lower() or q in e.category.lower() or q in e.id.lower()
            ]

        if not engines:
            yield Label("No visualizer engines matched your search criteria.", classes="vis-item-desc")
            return

        for e in engines:
            with Horizontal(classes="vis-item-row"):
                with Vertical(classes="vis-item-info"):
                    cat_name = CATEGORIES.get(e.category, ("", e.category, ""))[1]
                    yield Label(f"{e.icon} {e.name}  [dim][{cat_name}][/dim]", classes="vis-item-name")
                    yield Label(e.description, classes="vis-item-desc")
                yield Button("+ ADD", name=e.id, variant="primary", classes="vis-item-btn-add")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "vis-catalog-search":
            self.query_text = event.value
            self._refresh_list()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "vis-catalog-category":
            val = str(event.value) if event.value != Select.NULL else "all"
            self.selected_category = val
            self._refresh_list()

    def _refresh_list(self) -> None:
        scroll = self.query_one("#vis-catalog-list", VerticalScroll)
        scroll.remove_children()
        engines = VisualizerRegistry.list_all()
        if self.selected_category != "all":
            engines = [e for e in engines if e.category == self.selected_category]
        if self.query_text:
            q = self.query_text.lower()
            engines = [
                e for e in engines
                if q in e.name.lower() or q in e.description.lower() or q in e.category.lower() or q in e.id.lower()
            ]

        if not engines:
            scroll.mount(Label("No visualizer engines matched your search criteria.", classes="vis-item-desc"))
            return

        for e in engines:
            row = Horizontal(classes="vis-item-row")
            scroll.mount(row)
            info = Vertical(classes="vis-item-info")
            row.mount(info)
            cat_name = CATEGORIES.get(e.category, ("", e.category, ""))[1]
            info.mount(Label(f"{e.icon} {e.name}  [dim][{cat_name}][/dim]", classes="vis-item-name"))
            info.mount(Label(e.description, classes="vis-item-desc"))
            row.mount(Button("+ ADD", name=e.id, variant="primary", classes="vis-item-btn-add"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-catalog-close":
            self.dismiss(None)
        elif event.button.has_class("vis-item-btn-add"):
            self.dismiss(event.button.name)


class VisualDashboardWidget(Widget):
    """Dynamic multi-engine Audio Visualizer Dashboard with custom layouts and empty state."""

    DEFAULT_CSS = """
    VisualDashboardWidget {
        height: 1fr;
        width: 1fr;
        background: transparent;
        padding: 0;
    }
    #vis-dash-toolbar {
        height: 3;
        width: 1fr;
        background: $surface;
        padding: 0 1;
        align: left middle;
        border-bottom: solid $secondary;
    }
    #vis-dash-title {
        color: $accent;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }
    .vis-dash-btn {
        height: 3;
        min-height: 3;
        min-width: 13;
        margin-right: 1;
        border: solid #2d264f;
        background: #140f28;
        color: #00e5ff;
        text-style: bold;
    }
    .vis-dash-btn.-active {
        background: #00e5ff;
        color: #050b14;
        border: solid #00e5ff;
    }
    .vis-gap-cluster {
        width: auto;
        height: 3;
        align: left middle;
        margin-right: 1;
        background: #16122c;
        border: solid #2d264f;
        padding: 0 1;
    }
    .vis-gap-label {
        color: #8b9bb4;
        text-style: bold;
        margin-right: 1;
    }
    .vis-gap-val {
        color: #00e5ff;
        text-style: bold;
        min-width: 2;
        text-align: center;
    }
    .vis-gap-btn {
        min-width: 3;
        height: 1;
        border: none;
        background: #251c47;
        color: #ffffff;
        text-style: bold;
        padding: 0;
        margin: 0 1;
    }
    .vis-gap-btn:hover {
        background: #00e5ff;
        color: #050b14;
    }
    #vis-dash-container {
        height: 1fr;
        width: 1fr;
        padding: 1;
        background: transparent;
    }
    #vis-dash-empty-state {
        height: 1fr;
        width: 1fr;
        align: center middle;
        background: transparent;
        padding: 2;
    }
    #vis-empty-box {
        width: 74;
        height: 20;
        border: heavy #00e5ff;
        background: #0d0a1a;
        padding: 1 2;
        align: center middle;
    }
    #vis-empty-title {
        color: #00e5ff;
        text-style: bold;
        margin-bottom: 1;
    }
    #vis-empty-desc {
        color: #8b9bb4;
        text-align: center;
        margin-bottom: 2;
    }
    #vis-empty-hero-btn {
        min-width: 36;
        height: 3;
        min-height: 3;
        background: #00e5ff;
        color: #050b14;
        text-style: bold;
        border: none;
        margin-bottom: 2;
    }
    .vis-quickstart-row {
        height: 3;
        width: auto;
        align: center middle;
    }
    .vis-quickstart-btn {
        margin: 0 1;
        min-width: 16;
        height: 3;
        min-height: 3;
        background: #18132c;
        color: #00e5ff;
        text-style: bold;
        border: solid #2d264f;
    }
    #vis-dash-grid {
        height: 1fr;
        width: 1fr;
        background: transparent;
    }
    .vis-grid-row {
        height: 1fr;
        width: 1fr;
        margin-bottom: 0;
    }
    """

    cards: reactive[list[dict[str, Any]]] = reactive(list)
    layout_style: reactive[str] = reactive("auto")
    gap_size: reactive[int] = reactive(0)
    is_arrange_mode: reactive[bool] = reactive(False)
    selected_card_id: reactive[str | None] = reactive(None)

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
        clock_managed_externally: bool = False,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._feature_ctx = AudioFeatureContext.synthesize_idle()
        self._has_live_audio = False
        self.clock_managed_externally = clock_managed_externally
        self._anim_timer: Timer | None = None
        self.is_editable = True

    def on_mount(self) -> None:
        if not self.clock_managed_externally:
            self._anim_timer = self.set_interval(1.0 / 60.0, self.tick_frame)

    def on_unmount(self) -> None:
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None

    def tick_frame(self, ctx: AudioFeatureContext | None = None) -> None:
        if ctx is not None:
            self._feature_ctx = ctx
            self._has_live_audio = True
        frame_ctx = self._feature_ctx if self._has_live_audio else None
        for card in self.query(VisualizerCard):
            card.tick_frame(frame_ctx)

    def compose(self) -> ComposeResult:
        with Horizontal(id="vis-dash-toolbar"):
            yield Label("⌗ AUDIO VISUALIZATION STUDIO", id="vis-dash-title")
            yield Button("⛶ FULL VISION", id="btn-vis-full-vision", variant="warning", classes="vis-dash-btn")
            yield Button("＋ ADD VISUAL", id="btn-vis-add", variant="primary", classes="vis-dash-btn")
            with Horizontal(classes="vis-gap-cluster"):
                yield Label("GAP:", classes="vis-gap-label")
                yield Button("−", id="btn-vis-gap-dec", classes="vis-gap-btn")
                yield Label("0", id="lbl-vis-gap", classes="vis-gap-val")
                yield Button("＋", id="btn-vis-gap-inc", classes="vis-gap-btn")
            yield Button("✥ ARRANGE", id="btn-vis-arrange", classes="vis-dash-btn")
            yield Button("◖ SOLO", id="btn-vis-preset-solo", variant="default", classes="vis-dash-btn")
            yield Button("◫ DUAL", id="btn-vis-preset-dual", variant="default", classes="vis-dash-btn")
            yield Button("⌸ QUAD", id="btn-vis-preset-quad", variant="default", classes="vis-dash-btn")
            yield Button("✕ CLEAR", id="btn-vis-clear", variant="error", classes="vis-dash-btn")
        with Container(id="vis-dash-container"):
            with Vertical(id="vis-dash-empty-state"):
                with Vertical(id="vis-empty-box"):
                    yield Label("⌗ MODULAR AUDIO VISUALIZER DASHBOARD", id="vis-empty-title")
                    yield Label(
                        "Your visualizer dashboard is currently empty.\n"
                        "Build a custom studio dashboard by picking engines from our catalog,\n"
                        "or choose a quickstart preset below.",
                        id="vis-empty-desc",
                    )
                    yield Button(
                        "＋ BROWSE VISUAL CATALOG (100 ENGINES)",
                        id="btn-empty-browse",
                        variant="primary",
                    )
                    yield Label("QUICKSTART TEMPLATES:", classes="vis-item-name")
                    with Horizontal(classes="vis-quickstart-row"):
                        yield Button("◖ SOLO HERO", id="btn-empty-solo", classes="vis-quickstart-btn")
                        yield Button("◫ DUAL SPLIT", id="btn-empty-dual", classes="vis-quickstart-btn")
                        yield Button("⌸ STUDIO QUAD", id="btn-empty-quad", classes="vis-quickstart-btn")
            with Vertical(id="vis-dash-grid"):
                pass

    def set_editable(self, editable: bool) -> None:
        """Toggle curated preset lock without constraining user-owned layouts."""
        self.is_editable = editable
        self.query_one("#vis-dash-toolbar").styles.display = "block" if editable else "none"
        for card in self.query(VisualizerCard):
            card.set_read_only(not editable)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.is_editable:
            event.stop()
            return
        btn_id = event.button.id or ""
        if btn_id in ("btn-vis-add", "btn-empty-browse"):
            event.stop()
            self._open_catalog_modal()
        elif btn_id == "btn-vis-gap-dec":
            event.stop()
            self.set_gap(self.gap_size - 1)
        elif btn_id == "btn-vis-gap-inc":
            event.stop()
            self.set_gap(self.gap_size + 1)
        elif btn_id == "btn-vis-arrange":
            event.stop()
            self.toggle_arrange_mode()
        elif btn_id in ("btn-vis-preset-solo", "btn-empty-solo"):
            event.stop()
            self.apply_preset("solo")
        elif btn_id in ("btn-vis-preset-dual", "btn-empty-dual"):
            event.stop()
            self.apply_preset("dual")
        elif btn_id in ("btn-vis-preset-quad", "btn-empty-quad"):
            event.stop()
            self.apply_preset("quad")
        elif btn_id == "btn-vis-clear":
            event.stop()
            self.clear_canvas()
        elif btn_id == "btn-vis-full-vision":
            event.stop()
            self._open_full_vision()

    def _open_full_vision(self) -> None:
        """Launch Full Vision Studio in a new terminal window and push in-app screen."""
        from harvester.ui.full_vision import FullVisionScreen, launch_full_vision_external
        launch_full_vision_external()
        try:
            self.app.push_screen(FullVisionScreen())
        except Exception as exc:
            logger.debug("Could not push in-app FullVisionScreen: %s", exc)

    def _open_catalog_modal(self) -> None:
        def on_modal_result(engine_id: str | None) -> None:
            if engine_id:
                self.add_card(engine_id)

        self.app.push_screen(VisualCatalogModal(), on_modal_result)

    def on_visualizer_card_remove_requested(self, event: VisualizerCard.RemoveRequested) -> None:
        event.stop()
        self.remove_card(event.card_id)

    def add_card(self, engine_id: str, palette: str = "cyan") -> None:
        """Add an engine card to the dashboard canvas."""
        if not self.is_editable:
            return
        new_card = {
            "card_id": str(uuid.uuid4())[:8],
            "engine_id": engine_id,
            "palette": palette,
        }
        curr = list(self.cards)
        if len(curr) >= 6:
            curr.pop(0)  # max 6 active cards per dashboard
        curr.append(new_card)
        self.cards = curr
        self._refresh_canvas()

    def remove_card(self, card_id: str) -> None:
        """Remove a card by ID and re-tile the canvas."""
        if not self.is_editable:
            return
        self.cards = [c for c in self.cards if c["card_id"] != card_id]
        self._refresh_canvas()

    def clear_canvas(self) -> None:
        """Clear all visualizer cards, returning to the empty state."""
        if not self.is_editable:
            return
        self.cards = []
        self._refresh_canvas()

    def apply_preset(self, preset_name: str) -> None:
        """Apply a preset configuration of visualizer cards."""
        if not self.is_editable:
            return
        if preset_name == "solo":
            self.cards = [
                {"card_id": "solo-1", "engine_id": "mirrored_dance", "palette": "cyan"}
            ]
        elif preset_name == "dual":
            self.cards = [
                {"card_id": "dual-1", "engine_id": "spectrum_10band", "palette": "cyan"},
                {"card_id": "dual-2", "engine_id": "phosphor_crt_wave", "palette": "crt"},
            ]
        elif preset_name == "quad":
            self.cards = [
                {"card_id": "quad-1", "engine_id": "spectrum_10band", "palette": "cyan"},
                {"card_id": "quad-2", "engine_id": "phosphor_crt_wave", "palette": "crt"},
                {"card_id": "quad-3", "engine_id": "mirrored_dance", "palette": "neon"},
                {"card_id": "quad-4", "engine_id": "stereo_vu_deck", "palette": "thermal"},
            ]
        self._refresh_canvas()

    def _create_card(self, item: dict[str, Any]) -> VisualizerCard:
        card = VisualizerCard(
            engine_id=item["engine_id"],
            palette_key=item.get("palette", "cyan"),
            card_id=item["card_id"],
            id=f"vis-card-{item['card_id']}",
            palette_override=item.get("palette_override"),
            theme=item.get("theme"),
            is_read_only=not self.is_editable,
            clock_managed_externally=True,
        )
        if item.get("span") == "full":
            card.add_class("-span-full")
        if item.get("tall"):
            card.add_class("-tall")
        if self.is_arrange_mode and self.selected_card_id == item["card_id"]:
            card.add_class("-selected")
        if self.gap_size > 0:
            card.styles.margin = (0, self.gap_size, self.gap_size, 0)
        else:
            card.styles.margin = (0, 0, 0, 0)
        return card

    def _refresh_canvas(self) -> None:
        empty_box = self.query_one("#vis-dash-empty-state")
        grid = self.query_one("#vis-dash-grid")
        has_cards = bool(self.cards)
        empty_box.styles.display = "none" if has_cards else "block"
        grid.styles.display = "block" if has_cards else "none"
        self.run_worker(
            self._rebuild_canvas,
            group="dashboard-layout",
            exclusive=True,
        )

    async def _rebuild_canvas(self) -> None:
        grid = self.query_one("#vis-dash-grid")
        await grid.remove_children()
        if self.cards:
            await self._mount_dynamic_layout(grid)
        self._focus_selected_card()

    async def _mount_dynamic_layout(self, grid: Widget) -> None:
        """Mount every card using an explicit, tested page-layout strategy."""
        cards = list(self.cards)
        count = len(cards)
        if not count:
            return
        mode = self.layout_style if self.layout_style in SUPPORTED_DASHBOARD_LAYOUTS else "balanced_rows"

        def partition(items: list[dict[str, Any]], parts: int) -> list[list[dict[str, Any]]]:
            quotient, remainder = divmod(len(items), parts)
            groups: list[list[dict[str, Any]]] = []
            start = 0
            for index in range(parts):
                size = quotient + (1 if index < remainder else 0)
                if size:
                    groups.append(items[start : start + size])
                start += size
            return groups

        async def mount_children(parent: Widget, *children: Widget) -> bool:
            """Mount children unless Textual has started pruning this layout."""
            if not parent.is_attached:
                return False
            await parent.mount(*children)
            return all(child.is_attached for child in children)

        async def make_row(
            parent: Widget,
            items: list[dict[str, Any]],
            height: str = "1fr",
        ) -> bool:
            row = Horizontal(classes="vis-grid-row")
            row.styles.height = height
            if self.gap_size:
                row.styles.margin = (0, 0, self.gap_size, 0)
            if not await mount_children(parent, row):
                return False
            return await mount_children(
                row, *(self._create_card(item) for item in items)
            )

        if mode == "hero_left" and count > 2:
            shell = Horizontal(classes="vis-grid-row")
            if not await mount_children(grid, shell):
                return
            hero_column = Vertical(classes="vis-grid-col")
            detail_column = Vertical(classes="vis-grid-col -hero")
            if not await mount_children(shell, hero_column, detail_column):
                return
            hero = self._create_card(cards[0])
            hero.add_class("-tall")
            if not await mount_children(hero_column, hero):
                return
            for row_items in partition(cards[1:], 3):
                if not await make_row(detail_column, row_items):
                    return
            return

        if mode == "hero_top" and count > 1:
            hero_row = Horizontal(classes="vis-grid-row")
            hero_row.styles.height = "2fr"
            if not await mount_children(grid, hero_row):
                return
            hero = self._create_card(cards[0])
            hero.add_class("-hero")
            if not await mount_children(hero_row, hero):
                return
            for row_items in partition(cards[1:], min(2, count - 1)):
                if not await make_row(grid, row_items):
                    return
            return

        if mode == "three_columns" and count > 2:
            shell = Horizontal(classes="vis-grid-row")
            if not await mount_children(grid, shell):
                return
            for column_index in range(3):
                column = Vertical(classes="vis-grid-col")
                if not await mount_children(shell, column):
                    return
                if not await mount_children(
                    column,
                    *(self._create_card(item) for item in cards[column_index::3]),
                ):
                    return
            return

        if mode == "split_columns" and count > 1:
            shell = Horizontal(classes="vis-grid-row")
            if not await mount_children(grid, shell):
                return
            for column_items in partition(cards, 2):
                column = Vertical(classes="vis-grid-col")
                if not await mount_children(shell, column):
                    return
                if not await mount_children(
                    column, *(self._create_card(item) for item in column_items)
                ):
                    return
            return

        if mode == "solo" or count == 1:
            await make_row(grid, cards)
            return

        if mode == "dual" or (count == 2 and mode != "quad"):
            await make_row(grid, cards)
            return

        if mode == "quad":
            for row_items in partition(cards, 2):
                if not await make_row(grid, row_items):
                    return
            return

        row_count = 2 if mode == "five_by_two" else min(3, count)
        for row_items in partition(cards, row_count):
            if not await make_row(grid, row_items):
                return

    def on_visualizer_card_select_requested(self, event: VisualizerCard.SelectRequested) -> None:
        event.stop()
        if self.is_arrange_mode:
            self.selected_card_id = event.card_id
            self._update_card_selection()

    def on_visualizer_card_move_requested(self, event: VisualizerCard.MoveRequested) -> None:
        event.stop()
        self.move_card(event.card_id, event.direction)

    def on_visualizer_card_resize_requested(self, event: VisualizerCard.ResizeRequested) -> None:
        event.stop()
        if event.resize_type == "span":
            self.toggle_card_span(event.card_id)
        elif event.resize_type == "tall":
            self.toggle_card_tall(event.card_id)

    def set_gap(self, val: int) -> None:
        self.gap_size = max(0, min(4, val))
        try:
            self.query_one("#lbl-vis-gap", Label).update(str(self.gap_size))
        except Exception:
            pass
        self._refresh_canvas()

    def toggle_arrange_mode(self) -> None:
        self.is_arrange_mode = not self.is_arrange_mode
        try:
            btn = self.query_one("#btn-vis-arrange", Button)
            if self.is_arrange_mode:
                btn.label = "✥ ARRANGE (ON)"
                btn.add_class("-active")
                if not self.selected_card_id and self.cards:
                    self.selected_card_id = self.cards[0]["card_id"]
            else:
                btn.label = "✥ ARRANGE"
                btn.remove_class("-active")
                self.selected_card_id = None
        except Exception:
            pass
        self._update_card_selection()
        if self.is_arrange_mode:
            self._focus_selected_card()

    def _focus_selected_card(self) -> None:
        if self.selected_card_id:
            try:
                card = self.query_one(f"#vis-card-{self.selected_card_id}", VisualizerCard)
                card.focus()
            except Exception:
                pass

    def on_key(self, event: events.Key) -> None:
        if not self.is_arrange_mode or not self.selected_card_id:
            return
        k = event.key
        if k in ("left", "h"):
            event.stop()
            self.move_card(self.selected_card_id, "left")
        elif k in ("right", "l"):
            event.stop()
            self.move_card(self.selected_card_id, "right")
        elif k in ("up", "k"):
            event.stop()
            self.move_card(self.selected_card_id, "up")
        elif k in ("down", "j"):
            event.stop()
            self.move_card(self.selected_card_id, "down")
        elif k in ("s", "space"):
            event.stop()
            self.toggle_card_span(self.selected_card_id)
        elif k in ("t",):
            event.stop()
            self.toggle_card_tall(self.selected_card_id)
        elif k == "escape":
            event.stop()
            self.toggle_arrange_mode()

    def _update_card_selection(self) -> None:
        for card in self.query(VisualizerCard):
            is_sel = self.is_arrange_mode and (card.card_id == self.selected_card_id)
            if is_sel:
                card.add_class("-selected")
            else:
                card.remove_class("-selected")

    def move_card(self, card_id: str, direction: str) -> None:
        ids = [c["card_id"] for c in self.cards]
        if card_id not in ids:
            return
        idx = ids.index(card_id)
        cards = [dict(c) for c in self.cards]
        if direction == "left" and idx > 0:
            cards[idx], cards[idx - 1] = cards[idx - 1], cards[idx]
        elif direction == "right" and idx < len(cards) - 1:
            cards[idx], cards[idx + 1] = cards[idx + 1], cards[idx]
        elif direction == "up" and idx >= 2:
            item = cards.pop(idx)
            cards.insert(idx - 2, item)
        elif direction == "down" and idx + 2 < len(cards):
            item = cards.pop(idx)
            cards.insert(idx + 2, item)
        self.cards = cards
        self._refresh_canvas()

    def toggle_card_span(self, card_id: str) -> None:
        cards = [dict(c) for c in self.cards]
        for c in cards:
            if c["card_id"] == card_id:
                c["span"] = "full" if c.get("span") != "full" else "half"
                break
        self.cards = cards
        self._refresh_canvas()

    def toggle_card_tall(self, card_id: str) -> None:
        cards = [dict(c) for c in self.cards]
        for c in cards:
            if c["card_id"] == card_id:
                c["tall"] = not c.get("tall", False)
                break
        self.cards = cards
        self._refresh_canvas()

    def feed_audio(
        self,
        levels: np.ndarray | AudioFeatureContext | None = None,
        wave: np.ndarray | None = None,
        is_playing: bool = False,
    ) -> None:
        """Route live audio features to all active visualizer cards.

        Accepts either an explicit AudioFeatureContext (e.g. from FullVision player)
        or raw (levels, wave, is_playing) arrays.
        """
        if isinstance(levels, AudioFeatureContext):
            ctx = levels
        else:
            has_data = levels is not None or wave is not None
            ctx = AudioFeatureContext(
                levels_128=levels if levels is not None else np.zeros(128, dtype=np.float32),
                waveform_l=wave if wave is not None else np.zeros(1024, dtype=np.float32),
                is_playing=bool(is_playing) and has_data,
            )
        self._feature_ctx = ctx
        self._has_live_audio = True
        for card in self.query(VisualizerCard):
            card.feed_audio(ctx)

    def set_feature_track(self, track: Sequence[AudioFeatureContext]) -> None:
        """Hand already-computed feature frames to every card.

        Accepts a pre-built track so a decoded file and a synthetic test track
        follow the same playback path.
        """
        frames = list(track)
        for card in self.query(VisualizerCard):
            card.set_feature_track(frames)
        if frames:
            self._feature_ctx = frames[0]
            self._has_live_audio = False

    def load_audio_features(self, audio_file: Path) -> None:
        """Decode a routed track and hand its real feature frames to every card.

        This is the only path that gives the engines genuine decoded audio; the
        cards fall back to standby synthesis when the track cannot be decoded.
        """
        self.set_feature_track(build_feature_track(audio_file))

    def clear_audio_features(self) -> None:
        """Drop any routed feature track and return every card to standby."""
        self._feature_ctx = AudioFeatureContext.synthesize_idle()
        self._has_live_audio = False
        for card in self.query(VisualizerCard):
            card.canvas.clear_feature_track()
