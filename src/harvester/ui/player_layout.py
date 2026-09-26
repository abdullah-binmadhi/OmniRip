"""Runtime page-layout orchestrator for PLAYER designs.

``resolve_page`` turns a :class:`PlayerPageDesign` into concrete geometry: rail
placement, panel slots, frame glyphs, border roles, and motion specs.
``apply_page`` is the only side-effecting part; it applies that geometry to a
``PlayerStudioWidget`` with runtime Textual styles. Legacy ``ui_structure_style``
and ``button_style_mode`` values only apply to user-saved layouts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from harvester.services.stitch import StitchTheme
from harvester.services.vision_layout_store import VisionLayout
from harvester.ui.player_designs import PlayerPageDesign
from harvester.ui.visuals.base import ColorPalette

if TYPE_CHECKING:
    from harvester.ui.player_studio import PlayerStudioWidget

ALLOWED_BORDERS = frozenset({"heavy", "double", "round", "ascii", "tall", "solid", "dashed"})
DEFAULT_BORDER = "heavy"

RAIL_SLOTS = frozenset({"masthead", "rail_left", "rail_right", "footer", "split_hud", "corner_hud"})
RAIL_AXES = frozenset({"horizontal", "vertical", "grid"})
COMPANION_SLOTS = frozenset({"rail_right", "rail_left", "footer", "inset", "hidden"})
DOCK_SLOTS = frozenset({"footer", "header"})
MOTIF_SLOTS = frozenset({"masthead", "companion", "footer", "hidden"})

RAIL_STYLES: dict[str, dict[str, Any]] = {
    "masthead": {"dock": "top", "height": 3, "layout": "horizontal"},
    "rail_left": {"dock": "left", "width": 24, "layout": "vertical"},
    "rail_right": {"dock": "right", "width": 24, "layout": "vertical"},
    "footer": {"dock": "bottom", "height": 3, "layout": "horizontal"},
    "split_hud": {"dock": "top", "height": 4, "layout": "grid", "grid": (2, 4)},
    "corner_hud": {"dock": "top", "height": 3, "layout": "horizontal", "align": "right middle"},
}

COMPANION_STYLES: dict[str, dict[str, Any]] = {
    "rail_right": {"dock": "right", "width": 38, "height": "100%", "display": "block"},
    "rail_left": {"dock": "left", "width": 38, "height": "100%", "display": "block"},
    "footer": {"dock": "bottom", "height": 9, "width": "100%", "display": "block"},
    "inset": {"dock": None, "width": 38, "height": "100%", "display": "block"},
    "hidden": {"display": "none"},
}

DOCK_STYLES: dict[str, dict[str, Any]] = {
    "footer": {"dock": "bottom", "height": 7, "display": "block"},
    "header": {"dock": "top", "height": 7, "display": "block"},
}

# role -> default presentation; order defines the {n} placeholder value.
BUTTON_ROLES: tuple[str, ...] = ("prev", "play", "stop", "next", "loop", "shuffle", "add", "queue")
ROLE_INDEX = {role: index + 1 for index, role in enumerate(BUTTON_ROLES)}
ROLE_BUTTON_IDS = {
    "prev": "#btn-plr-prev",
    "play": "#btn-plr-play",
    "stop": "#btn-plr-stop",
    "next": "#btn-plr-next",
    "loop": "#btn-plr-loop",
    "shuffle": "#btn-plr-shuffle",
    "add": "#btn-plr-add-song",
    "queue": "#btn-plr-queue",
}

THEME_ROLES = {
    "primary": "primary_color",
    "secondary": "secondary_color",
    "accent": "accent_color",
    "surface": "surface_color",
    "background": "background_color",
}


@dataclass(frozen=True, slots=True)
class PlayerPalette:
    """Single palette source for PLAYER chrome, cards, companion, and scene."""

    background: str
    surface: str
    primary: str
    secondary: str
    accent: str
    foreground: str
    dim: str


def theme_palette(theme: StitchTheme) -> PlayerPalette:
    """Derive the PLAYER palette from a Stitch theme."""
    stops = list(theme.gradient_stops or [])
    return PlayerPalette(
        background=theme.background_color,
        surface=theme.surface_color,
        primary=theme.primary_color,
        secondary=theme.secondary_color,
        accent=theme.accent_color,
        foreground=theme.secondary_color,
        dim=stops[3] if len(stops) > 3 else theme.surface_color,
    )


def theme_color_palette(theme: StitchTheme) -> ColorPalette:
    """Derive the visualizer card palette from the same theme source."""
    stops = list(theme.gradient_stops or [])
    return ColorPalette(
        id="theme_bound",
        name=theme.name,
        primary=stops[0] if stops else theme.primary_color,
        secondary=stops[1] if len(stops) > 1 else theme.secondary_color,
        accent=theme.accent_color,
        background=theme.background_color,
        dim=theme.surface_color,
    )


@dataclass(frozen=True, slots=True)
class ButtonState:
    """Current transport state used to render design button frames."""

    playing: bool = False
    loop_mode: str = "OFF"
    shuffle: bool = False
    queue_size: int = 0
    gap: int = 1


@dataclass
class ResolvedPage:
    """Concrete page geometry derived from a design and its layout."""

    design_id: str
    rail: str
    rail_axis: str
    rail_style: dict[str, Any]
    companion_slot: str
    companion_style: dict[str, Any]
    dock_slot: str
    dock_style: dict[str, Any]
    motif_slot: str
    dash_layout: str
    border_type: str
    border_roles: dict[str, str] = field(default_factory=dict)
    motion: tuple[tuple[str, str, float, str], ...] = ()
    button_frame: str = ""
    button_family: str = ""

    @property
    def signature(self) -> tuple[str, str, str, str, str, str]:
        """Structural signature used to assert per-preset uniqueness."""
        return (
            self.rail,
            self.rail_axis,
            self.companion_slot,
            self.dock_slot,
            self.motif_slot,
            self.border_type,
        )


def _panel_slot(design: PlayerPageDesign, name: str, allowed: frozenset[str], default: str) -> str:
    value = design.panel_slots.get(name, default)
    return value if value in allowed else default


def resolve_page(
    design: PlayerPageDesign,
    layout: VisionLayout,
    *,
    theme: StitchTheme | None = None,
) -> ResolvedPage:
    """Resolve a design into concrete geometry without touching any widget."""
    rail = design.rail if design.rail in RAIL_SLOTS else "masthead"
    rail_axis = design.rail_axis if design.rail_axis in RAIL_AXES else "horizontal"
    companion_slot = _panel_slot(design, "companion", COMPANION_SLOTS, "rail_right")
    dock_slot = _panel_slot(design, "dock", DOCK_SLOTS, "footer")
    motif_slot = _panel_slot(design, "motif", MOTIF_SLOTS, "masthead")

    border_type = design.frame_glyphs if design.frame_glyphs in ALLOWED_BORDERS else ""
    if not border_type and theme is not None and theme.border_style in ALLOWED_BORDERS:
        border_type = theme.border_style
    border_type = border_type or DEFAULT_BORDER

    rail_style = dict(RAIL_STYLES[rail])
    if rail_axis != "horizontal":
        rail_style["layout"] = "vertical" if rail_axis == "vertical" else "grid"

    motion = tuple(tuple(spec) for spec in design.motion if spec and spec[0])

    return ResolvedPage(
        design_id=design.layout_id,
        rail=rail,
        rail_axis=rail_axis,
        rail_style=rail_style,
        companion_slot=companion_slot,
        companion_style=dict(COMPANION_STYLES[companion_slot]),
        dock_slot=dock_slot,
        dock_style=dict(DOCK_STYLES[dock_slot]),
        motif_slot=motif_slot,
        dash_layout=design.dashboard_layout,
        border_type=border_type,
        border_roles=dict(design.border_roles),
        motion=motion,
        button_frame=design.button_frame,
        button_family=design.button_family,
    )


def role_label(role: str, state: ButtonState) -> str:
    """Render the stateful label for one transport role."""
    if role == "play":
        return "⏸ PAUSE" if state.playing else "▶ PLAY"
    if role == "stop":
        return "⏹ STOP"
    if role == "prev":
        return "⏮ PREV"
    if role == "next":
        return "⏭ NEXT"
    if role == "loop":
        return f"🔁 LOOP: {state.loop_mode}"
    if role == "shuffle":
        return f"🔀 SHUFFLE: {'ON' if state.shuffle else 'OFF'}"
    if role == "add":
        return "+ LOAD SONG"
    if role == "queue":
        return f"QUEUE ({state.queue_size})"
    return role.upper()


def render_button_label(frame: str, role: str, state: ButtonState) -> str:
    """Apply a design frame template to a role's stateful label."""
    label = role_label(role, state)
    return frame.replace("{label}", label).replace("{n}", str(ROLE_INDEX.get(role, 0)))


def theme_role_color(theme: StitchTheme, role: str, fallback: str) -> str:
    """Resolve a named theme role to a concrete color."""
    attribute = THEME_ROLES.get(role)
    if attribute is None:
        return fallback
    if role == "background":
        return theme.background_color
    return getattr(theme, attribute, fallback)


def _border_edge(slot: str) -> str:
    if slot in ("rail_left", "left"):
        return "border_right"
    if slot in ("rail_right", "right"):
        return "border_left"
    if slot in ("footer", "bottom"):
        return "border_top"
    return "border_bottom"


def _apply_border(widget: Any, edge: str, border_type: str, color: str) -> None:
    for candidate in ("border_top", "border_right", "border_bottom", "border_left"):
        setattr(widget.styles, candidate, (border_type, color) if candidate == edge else None)


def apply_page(studio: PlayerStudioWidget, page: ResolvedPage, theme: StitchTheme) -> None:
    """Apply resolved geometry to a mounted PlayerStudioWidget."""
    border_type = page.border_type
    primary = theme_role_color(theme, page.border_roles.get("rail", "primary"), theme.primary_color)
    dock_role = theme_role_color(theme, page.border_roles.get("dock", "secondary"), theme.secondary_color)
    companion_role = theme_role_color(theme, page.border_roles.get("companion", "primary"), theme.primary_color)

    rail = studio.query_one("#plr-top-bar")
    rail.styles.dock = page.rail_style.get("dock")
    rail.styles.height = page.rail_style.get("height")
    rail.styles.width = page.rail_style.get("width")
    layout = page.rail_style.get("layout")
    rail.styles.layout = layout
    align = page.rail_style.get("align")
    if align:
        rail.styles.align = align
    if layout == "grid":
        rows, columns = page.rail_style.get("grid", (2, 4))
        rail.styles.grid_size_rows = rows
        rail.styles.grid_size_columns = columns
    _apply_border(rail, _border_edge(str(page.rail_style.get("dock") or "top")), border_type, primary)

    companion = studio.query_one("#plr-anime-companion")
    companion.styles.display = page.companion_style.get("display", "block")
    companion.styles.dock = page.companion_style.get("dock")
    companion.styles.width = page.companion_style.get("width")
    companion.styles.height = page.companion_style.get("height")
    companion_layout = page.companion_style.get("layout")
    if companion_layout:
        companion.styles.layout = companion_layout
    if page.companion_slot != "hidden":
        _apply_border(
            companion,
            _border_edge(page.companion_slot if page.companion_slot != "inset" else "rail_right"),
            border_type,
            companion_role,
        )

    dock = studio.query_one("#plr-bottom-dock")
    dock.styles.display = page.dock_style.get("display", "block")
    dock.styles.dock = page.dock_style.get("dock")
    dock.styles.height = page.dock_style.get("height")
    _apply_border(dock, _border_edge(str(page.dock_style.get("dock") or "bottom")), border_type, dock_role)

    _apply_motif(studio, page)


def _apply_motif(studio: PlayerStudioWidget, page: ResolvedPage) -> None:
    text = studio.current_design.motif if studio.current_design else ""
    top_motif = studio.query_one("#plr-motif")
    dock_motif = studio.query_one("#plr-dock-motif")
    top_motif.display = page.motif_slot == "masthead"
    dock_motif.display = page.motif_slot == "footer"
    if page.motif_slot == "masthead":
        top_motif.update(text)
    if page.motif_slot == "footer":
        dock_motif.update(text)
    companion = studio.query_one("#plr-anime-companion")
    setter = getattr(companion, "set_motif", None)
    if setter is not None:
        setter(text if page.motif_slot == "companion" else None)


def apply_button_frames(studio: PlayerStudioWidget, page: ResolvedPage, state: ButtonState) -> None:
    """Apply design button frames; no-op when the design keeps legacy labels."""
    if not page.button_frame:
        return
    for role, button_id in ROLE_BUTTON_IDS.items():
        try:
            button = studio.query_one(button_id)
        except Exception:
            continue
        button.label = render_button_label(page.button_frame, role, state)


class MotionDriver:
    """Consumes design motion specs against motif/subtitle labels.

    Only ``blink`` and ``marquee`` are label-level motions; other kinds are
    owned by the companion and visualizer engines and are resolved but not
    driven here.
    """

    def __init__(self) -> None:
        self.tick = 0

    def observe(self, studio: PlayerStudioWidget, page: ResolvedPage) -> None:
        self.tick += 1
        for spec in page.motion:
            kind, _trigger, intensity, reduced = (spec + ("",))[:4]
            if kind == "blink":
                self._blink(studio, float(intensity or 1.0), str(reduced or "hold"))
            elif kind == "marquee":
                self._marquee(studio, float(intensity or 1.0), str(reduced or "hold"))

    def _blink(self, studio: PlayerStudioWidget, intensity: float, reduced: str) -> None:
        motif = studio.query_one("#plr-motif")
        if reduced == "hide" or intensity <= 0:
            return
        rate = 15 if reduced == "slow" else 30
        cursor = "▌" if (self.tick // max(1, rate // 2)) % 2 == 0 else " "
        base = studio.current_design.motif if studio.current_design else ""
        motif.update(f"{base} {cursor}")

    def _marquee(self, studio: PlayerStudioWidget, intensity: float, reduced: str) -> None:
        if studio.current_design is None or intensity <= 0:
            return
        subtitle = studio.query_one("#plr-theme-subtitle")
        text = studio.current_design.subtitle
        if reduced == "hide" or len(text) < 8:
            subtitle.update(text)
            return
        offset = (self.tick // (4 if reduced == "slow" else 2)) % len(text)
        rotated = text[offset:] + text[:offset]
        subtitle.update(rotated)
