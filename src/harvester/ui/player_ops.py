"""Space-fit planner, random visual mix generator, and dead-space auditor.

PLAYER presets are authored data, but the canvas they render into is whatever
the terminal gives them. This module answers three questions without touching a
widget:

* :func:`plan_dashboard` — which dashboard tiling fills the measured canvas so
  that every card cell still clears its engine minimums, trimming the card
  count only when no tiling can hold that many.
* :func:`generate_mix` — a reproducible random mix of design grammar, grid,
  engines, palettes, and gap for the GENERATE action.
* :func:`audit_layout` — after the plan is mounted, verify that no panel
  collapsed, no rail grid cell is empty, and no card renders below its engine
  minimum.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from harvester.services.vision_layout_store import (
    BUILTIN_LAYOUTS,
    VisionCardConfig,
    VisionLayout,
)
from harvester.ui.visuals.registry import VisualizerRegistry

if TYPE_CHECKING:
    from harvester.ui.player_studio import PlayerStudioWidget

# Engine minimum (10x4) plus one header row and the two card border cells.
MIN_CARD_WIDTH = 12
MIN_CARD_HEIGHT = 8
# Hero cards carry min-height 14 in VisualizerCard CSS.
HERO_MIN_HEIGHT = 14
TARGET_CELL_ASPECT = 2.4
MAX_GENERATED_CARDS = 10
PALETTE_KEYS = ("cyan", "neon", "matrix", "thermal", "sunset", "crt", "stanford")

# Longer rows are only admitted for the styles whose mount logic supports them.
_STYLE_ORDER = (
    "solo",
    "dual",
    "three_columns",
    "split_columns",
    "hero_left",
    "hero_top",
    "five_by_two",
    "quad",
    "balanced_rows",
)


@dataclass(frozen=True)
class DashboardPlan:
    """A concrete, fillable dashboard tiling for a measured canvas region.

    ``rows`` holds the cards per row for row-oriented styles and the cards per
    column for column-oriented styles, mirroring the dashboard mount logic.
    """

    layout_style: str
    card_count: int
    rows: tuple[int, ...]
    cell_width: int
    cell_height: int

    @property
    def grid_label(self) -> str:
        span = max(self.rows, default=0)
        if self.layout_style in ("three_columns", "split_columns"):
            return f"{len(self.rows)}×{span}"
        return f"{span}×{len(self.rows)}"


@dataclass(frozen=True)
class GeneratedMix:
    """A reproducible random visual mix ready to be applied by the studio."""

    seed: int
    base_layout_id: str
    stitch_theme_id: str
    anime_character_id: str
    layout_style: str
    gap: int
    cards: tuple[dict[str, Any], ...]


def partition_counts(count: int, parts: int) -> tuple[int, ...]:
    """Split ``count`` items into ``parts`` groups, remainder to earlier groups."""
    parts = max(1, min(parts, count))
    quotient, remainder = divmod(count, parts)
    groups: list[int] = []
    for index in range(parts):
        size = quotient + (1 if index < remainder else 0)
        if size:
            groups.append(size)
    return tuple(groups)


def _rows_for(style: str, count: int) -> tuple[int, ...]:
    """Mirror the row/column sizes produced by VisualDashboardWidget mount logic."""
    if style in ("five_by_two", "quad"):
        return partition_counts(count, 2)
    if style == "balanced_rows":
        return partition_counts(count, min(3, count))
    if style == "hero_left" and count > 2:
        return partition_counts(count - 1, 3)
    if style == "hero_top" and count > 1:
        return partition_counts(count - 1, 2)
    if style == "three_columns" and count > 2:
        return tuple(len(range(index, count, 3)) for index in range(3))
    if style == "split_columns" and count > 1:
        return partition_counts(count, 2)
    return (count,)


def valid_styles(count: int) -> tuple[str, ...]:
    """Dashboard styles whose mount guard accepts ``count`` cards."""
    if count <= 0:
        return ()
    if count == 1:
        return ("solo",)
    if count == 2:
        return ("dual", "split_columns", "balanced_rows")
    return tuple(style for style in _STYLE_ORDER if style not in ("solo", "dual"))


def _shape(style: str, count: int, width: int, height: int) -> tuple[int, int, int]:
    """Return ``(cell_width, cell_height, hero_height)`` for the worst cell.

    ``hero_height`` is 0 for non-hero styles; hero styles must clear
    ``HERO_MIN_HEIGHT`` on top of the regular cell checks.
    """
    width = max(1, width)
    height = max(1, height)
    if style == "hero_left" and count > 2:
        hero_width = max(1, width // 3)
        detail_rows = partition_counts(count - 1, 3)
        detail_width = max(1, (width - hero_width) // 3)
        detail_height = max(1, height // len(detail_rows))
        return min(hero_width, detail_width), detail_height, height
    if style == "hero_top" and count > 1:
        rest_rows = partition_counts(count - 1, 2)
        hero_height = max(1, (height * 2) // (2 + len(rest_rows)))
        rest_height = max(1, height // (2 + len(rest_rows)))
        return max(1, width // 2), rest_height, hero_height
    if style == "three_columns" and count > 2:
        groups = tuple(len(range(index, count, 3)) for index in range(3))
        return max(1, width // 3), max(1, height // max(groups)), 0
    if style == "split_columns" and count > 1:
        groups = partition_counts(count, 2)
        return max(1, width // 2), max(1, height // max(groups)), 0
    rows = _rows_for(style, count)
    return max(1, width // max(rows)), max(1, height // len(rows)), 0


def _score(cell_width: int, cell_height: int) -> float:
    aspect_error = abs(math.log((cell_width / cell_height) / TARGET_CELL_ASPECT))
    return aspect_error - 0.02 * math.log(cell_width * cell_height)


def plan_dashboard(
    cards: Sequence[Any],
    width: int,
    height: int,
    *,
    prefer_style: str | None = None,
    min_width: int = MIN_CARD_WIDTH,
    min_height: int = MIN_CARD_HEIGHT,
) -> DashboardPlan | None:
    """Choose a tiling that fills ``width`` x ``height`` with ``cards``.

    Counts are scanned from the full card list downward; the largest count that
    can clear every engine minimum wins. Within that count, ``prefer_style`` is
    kept when it fits, otherwise the best aspect match is chosen. ``None`` is
    returned only when not even one card fits.
    """
    total = len(cards)
    if total <= 0 or width <= 0 or height <= 0:
        return None

    for count in range(total, 0, -1):
        fitting = [
            style
            for style in valid_styles(count)
            if _fits(style, count, width, height, min_width, min_height)
        ]
        if not fitting:
            continue
        if count == total and prefer_style in fitting:
            style = prefer_style
        else:
            style = min(
                fitting,
                key=lambda candidate: (
                    _score(*_shape(candidate, count, width, height)[:2]),
                    _STYLE_ORDER.index(candidate),
                ),
            )
        cell_width, cell_height, _hero_height = _shape(style, count, width, height)
        return DashboardPlan(
            layout_style=style,
            card_count=count,
            rows=_rows_for(style, count),
            cell_width=cell_width,
            cell_height=cell_height,
        )
    return None


def _fits(
    style: str,
    count: int,
    width: int,
    height: int,
    min_width: int,
    min_height: int,
) -> bool:
    cell_width, cell_height, hero_height = _shape(style, count, width, height)
    if cell_width < min_width or cell_height < min_height:
        return False
    return hero_height == 0 or hero_height >= HERO_MIN_HEIGHT


def _engine_pool(plan: DashboardPlan, gap: int) -> dict[str, Any]:
    """Distinct visual families whose engines fit the planned card content box."""
    usable_width = plan.cell_width - gap - 2
    usable_height = plan.cell_height - gap - 3
    pool: dict[str, Any] = {}
    for engine in VisualizerRegistry.list_all(include_presets=True):
        family = engine.visual_family_id
        if family in pool:
            continue
        if engine.min_width > usable_width or engine.min_height > usable_height:
            continue
        pool[family] = engine
    return pool


def fit_cards_to_plan(
    cards: Sequence[dict[str, Any]],
    plan: DashboardPlan,
    gap: int,
) -> tuple[list[dict[str, Any]], int]:
    """Trim and re-engineer cards so every cell holds an engine that fits.

    Cards whose engine minimums exceed the planned cell are swapped for the
    closest fitting engine in the same category, keeping visual families
    distinct where the pool allows it. Returns the new card list and the number
    of swaps performed.
    """
    pool = _engine_pool(plan, gap)
    usable_width = plan.cell_width - gap - 2
    usable_height = plan.cell_height - gap - 3
    used_ids: set[str] = set()
    result: list[dict[str, Any]] = []
    swaps = 0
    for card in list(cards)[: plan.card_count]:
        engine = VisualizerRegistry.get(str(card.get("engine_id", "")))
        if (
            engine is not None
            and engine.min_width <= usable_width
            and engine.min_height <= usable_height
        ):
            used_ids.add(engine.id)
            result.append({**card, "span": "normal", "tall": False})
            continue
        replacement = _replacement_engine(engine, pool, used_ids, usable_width, usable_height)
        normalized = {**card, "span": "normal", "tall": False}
        if replacement is not None:
            normalized["engine_id"] = replacement.id
            used_ids.add(replacement.id)
            swaps += 1
        result.append(normalized)
    return result, swaps


def _replacement_engine(
    original: Any,
    pool: dict[str, Any],
    used_ids: set[str],
    usable_width: int,
    usable_height: int,
) -> Any:
    """Pick an unused fitting engine, preferring the original's category."""
    candidates = [
        engine
        for engine in pool.values()
        if engine.id not in used_ids
        and engine.min_width <= usable_width
        and engine.min_height <= usable_height
    ]
    if not candidates:
        return None
    if original is not None:
        same_category = [engine for engine in candidates if engine.category == original.category]
        if same_category:
            candidates = same_category
    return candidates[0]


def generate_mix(
    seed: int,
    width: int,
    height: int,
    *,
    exclude_layout_id: str | None = None,
) -> GeneratedMix | None:
    """Build a reproducible random mix that fits the measured canvas."""
    rng = random.Random(seed)
    bases = [layout for layout in BUILTIN_LAYOUTS if layout.layout_id != exclude_layout_id] or list(
        BUILTIN_LAYOUTS
    )
    base = rng.choice(bases)

    gap = rng.randint(0, 2)
    min_width = MIN_CARD_WIDTH + gap
    min_height = MIN_CARD_HEIGHT + gap
    fitting = [
        count
        for count in range(1, MAX_GENERATED_CARDS + 1)
        if plan_dashboard(
            [None] * count,
            width,
            height,
            min_width=min_width,
            min_height=min_height,
        )
    ]
    if not fitting:
        return None
    rich = [count for count in fitting if count >= 4]
    count = rng.choice(rich or fitting)
    plan = plan_dashboard(
        [None] * count,
        width,
        height,
        min_width=min_width,
        min_height=min_height,
    )
    if plan is None:
        return None

    pool = _engine_pool(plan, gap)
    if not pool:
        return None
    families = sorted(pool)
    if len(families) >= plan.card_count:
        chosen = rng.sample(families, plan.card_count)
    else:
        chosen = [rng.choice(families) for _ in range(plan.card_count)]

    cards = tuple(
        {
            "card_id": f"gen-{seed}-{index}",
            "engine_id": pool[family].id,
            "palette": rng.choice(PALETTE_KEYS),
            "palette_override": None,
            "span": "normal",
            "tall": False,
        }
        for index, family in enumerate(chosen)
    )
    return GeneratedMix(
        seed=seed,
        base_layout_id=base.layout_id,
        stitch_theme_id=base.stitch_theme_id,
        anime_character_id=base.anime_character_id,
        layout_style=plan.layout_style,
        gap=gap,
        cards=cards,
    )


def build_generated_layout(mix: GeneratedMix) -> VisionLayout:
    """Wrap a generated mix in a non-builtin layout so it is editable and saveable."""
    return VisionLayout(
        layout_id=f"generated_{mix.seed}",
        name=f"GENERATED MIX {mix.seed}",
        description="Randomized visual mix generated by PLAYER Studio.",
        stitch_theme_id=mix.stitch_theme_id,
        gap_distance=mix.gap,
        dashboard_layout=mix.layout_style,
        anime_character_id=mix.anime_character_id,
        cards=[
            VisionCardConfig(engine_id=card["engine_id"], palette=card["palette"], order=index)
            for index, card in enumerate(mix.cards)
        ],
        is_builtin=False,
    )


def dashboard_region(
    studio: PlayerStudioWidget,
    *,
    measure: bool = True,
    assume_editable: bool = False,
) -> tuple[int, int]:
    """Return the dashboard grid region.

    ``measure`` reads the mounted grid; set it False right after chrome changes
    (for example when the editable toolbar is about to appear) so the region is
    derived from the new resolved page instead of stale geometry.
    ``assume_editable`` forces the toolbar row into the estimate, which makes a
    GENERATE plan independent of whether the current view is a locked built-in.
    """
    if measure:
        try:
            grid = studio.query_one("#vis-dash-grid")
            if grid.is_attached:
                size = grid.content_size
                if size.width > 0 and size.height > 0:
                    return int(size.width), int(size.height)
        except Exception:
            pass
    return _estimate_region(studio, assume_editable=assume_editable)


def _estimate_region(
    studio: PlayerStudioWidget, *, assume_editable: bool = False
) -> tuple[int, int]:
    """Chrome arithmetic fallback used before the dashboard grid is laid out."""
    width = int(studio.size.width or 0)
    height = int(studio.size.height or 0)
    page = getattr(studio, "_resolved_page", None)
    rail_style = page.rail_style if page is not None else {"dock": "top", "height": 3}
    rail_dock = rail_style.get("dock")
    if rail_dock in ("top", "bottom"):
        height -= int(rail_style.get("height", 3) or 0)
    elif rail_dock in ("left", "right"):
        width -= int(rail_style.get("width", 24) or 0)
    height -= 1  # ops bar
    dock_style = page.dock_style if page is not None else {"display": "block", "height": 7}
    if dock_style.get("display", "block") != "none":
        height -= int(dock_style.get("height", 7) or 0)
    companion_style = page.companion_style if page is not None else {}
    if companion_style.get("display", "block") != "none":
        companion_dock = companion_style.get("dock")
        if companion_dock in ("left", "right"):
            width -= int(companion_style.get("width", 38) or 0)
        else:
            companion_height = companion_style.get("height", 9)
            height -= int(companion_height) if isinstance(companion_height, int) else 9
    try:
        toolbar_visible = (
            assume_editable or str(studio.query_one("#vis-dash-toolbar").styles.display) != "none"
        )
    except Exception:
        toolbar_visible = assume_editable
    if toolbar_visible:
        height -= 3
    width -= 2  # #vis-dash-container padding
    height -= 2
    return max(0, width), max(0, height)


def audit_layout(studio: PlayerStudioWidget) -> list[str]:
    """Return dead-space / clipping violations found in the mounted studio."""
    issues: list[str] = []

    def _widget(selector: str) -> Any:
        try:
            return studio.query_one(selector)
        except Exception:
            return None

    for selector in (
        "#plr-top-bar",
        "#plr-ops-bar",
        "#plr-anime-companion",
        "#plr-bottom-dock",
        "#plr-dashboard",
    ):
        widget = _widget(selector)
        if widget is None:
            issues.append(f"{selector} is missing")
            continue
        if str(widget.styles.display) == "none":
            continue
        if widget.region.width <= 0 or widget.region.height <= 0:
            issues.append(f"{selector} collapsed to zero size")

    page = getattr(studio, "_resolved_page", None)
    rail = _widget("#plr-top-bar")
    if rail is not None and page is not None and page.rail_style.get("layout") == "grid":
        visible = sum(1 for child in rail.children if child.display)
        style_rows, style_columns = page.rail_style.get("grid", (2, 4))
        from harvester.ui.player_layout import fit_grid

        rows, columns = fit_grid(int(style_rows), int(style_columns), visible)
        actual_rows = _style_int(rail.styles.grid_size_rows)
        actual_columns = _style_int(rail.styles.grid_size_columns)
        if (actual_rows, actual_columns) != (rows, columns):
            issues.append(
                f"rail grid {actual_rows}×{actual_columns} leaves empty cells for {visible} children"
            )
        cells = (actual_rows or 0) * (actual_columns or 0)
        if cells != visible:
            issues.append(f"rail grid exposes {cells - visible} dead cell(s)")

    from harvester.ui.visual_dashboard import VisualizerCard

    cards = [card for card in studio.query(VisualizerCard) if card.is_attached]
    for card in cards:
        if (
            card.canvas.size.width < card.engine.min_width
            or card.canvas.size.height < card.engine.min_height
        ):
            issues.append(
                f"card {card.card_id} ({card.engine.id}) renders below its engine minimum"
            )

    grid = _widget("#vis-dash-grid")
    if grid is not None and grid.is_attached and str(grid.styles.display) != "none":
        rows = list(grid.query(".vis-grid-row"))
        if cards and not rows:
            issues.append("dashboard grid has cards but no mounted rows")
        if any(not row.children for row in rows):
            issues.append("dashboard grid contains an empty row")
    return issues


def _style_int(value: Any) -> int | None:
    """Unwrap a Textual style scalar to int, tolerating int passthrough."""
    if value is None:
        return None
    inner = getattr(value, "value", value)
    try:
        return int(inner)
    except (TypeError, ValueError):
        return None
