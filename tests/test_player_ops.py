"""Space-fit, generation, and dead-space audit coverage for PLAYER ops."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input

from harvester.services.vision_layout_store import VisionLayoutStore
from harvester.ui.player_layout import fit_grid
from harvester.ui.player_ops import (
    MIN_CARD_HEIGHT,
    MIN_CARD_WIDTH,
    audit_layout,
    build_generated_layout,
    fit_cards_to_plan,
    generate_mix,
    partition_counts,
    plan_dashboard,
)
from harvester.ui.player_studio import PlayerStudioWidget, SeedInputModal
from harvester.ui.visual_dashboard import VisualizerCard
from harvester.ui.visuals.registry import VisualizerRegistry


def test_partition_counts_distributes_remainder_to_earlier_groups():
    assert partition_counts(10, 3) == (4, 3, 3)
    assert partition_counts(2, 5) == (1, 1)
    assert partition_counts(0, 3) == ()


def test_fit_grid_never_leaves_empty_cells():
    assert fit_grid(2, 4, 8) == (2, 4)
    assert fit_grid(2, 4, 9) == (3, 3)
    for children in range(1, 13):
        rows, columns = fit_grid(2, 4, children)
        assert rows * columns == children


def test_plan_dashboard_keeps_a_full_mix_when_it_fits():
    plan = plan_dashboard([None] * 10, 160, 37, min_width=13, min_height=9)
    assert plan is not None
    assert plan.card_count == 10
    assert plan.cell_width >= 13 and plan.cell_height >= 9
    assert all(row for row in plan.rows)


def test_plan_dashboard_trims_to_the_largest_fitting_count():
    plan = plan_dashboard([None] * 10, 42, 12, min_width=13, min_height=9)
    assert plan is not None
    assert plan.card_count == 3
    assert plan.cell_width >= 13 and plan.cell_height >= 9


def test_plan_dashboard_prefers_the_current_style_when_it_fits():
    plan = plan_dashboard(
        [None] * 10,
        160,
        37,
        prefer_style="five_by_two",
        min_width=13,
        min_height=9,
    )
    assert plan is not None and plan.layout_style == "five_by_two"
    hero = plan_dashboard(
        [None] * 10,
        160,
        37,
        prefer_style="hero_top",
        min_width=13,
        min_height=9,
    )
    assert hero is not None and hero.layout_style == "hero_top"


def test_plan_dashboard_returns_none_without_room():
    assert plan_dashboard([], 100, 30) is None
    assert plan_dashboard([None], 0, 0) is None


def test_fit_cards_swaps_engines_that_cannot_fit():
    plan = plan_dashboard([None] * 4, 40, 18, min_width=13, min_height=9)
    assert plan is not None
    cards = [
        {
            "card_id": f"card-{index}",
            "engine_id": "stanford_sun_music_3d",
            "palette": "cyan",
        }
        for index in range(4)
    ]
    fitted, swaps = fit_cards_to_plan(cards, plan, 1)
    assert swaps == 4
    for card in fitted:
        engine = VisualizerRegistry.get(card["engine_id"])
        assert engine is not None
        assert engine.min_width <= plan.cell_width - 3
        assert engine.min_height <= plan.cell_height - 4
        assert card["tall"] is False


def test_generate_mix_is_seeded_and_family_unique():
    first = generate_mix(42, 160, 37)
    second = generate_mix(42, 160, 37)
    assert first == second
    assert first is not None
    assert 1 <= len(first.cards) <= 10
    engines = [VisualizerRegistry.get(card["engine_id"]) for card in first.cards]
    assert all(engine is not None for engine in engines)
    families = [engine.visual_family_id for engine in engines]
    assert len(families) == len(set(families))
    layout = build_generated_layout(first)
    assert layout.is_builtin is False
    assert layout.dashboard_layout == first.layout_style
    assert len(layout.cards) == len(first.cards)


def test_generate_mix_never_reuses_the_excluded_base():
    for seed in range(20):
        mix = generate_mix(seed, 160, 37, exclude_layout_id="preset_y2k_aesthetic")
        assert mix is not None
        assert mix.base_layout_id != "preset_y2k_aesthetic"


class _OpsApp(App):
    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(80, 24), (200, 50)])
async def test_optimize_fills_every_builtin_without_dead_space(size):
    app = _OpsApp()
    async with app.run_test(size=size) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        for layout in studio.layout_store.list_layouts():
            if not layout.is_builtin:
                continue
            studio.apply_layout(layout)
            await pilot.pause()
            assert studio._optimize_view(announce=False), layout.layout_id
            await pilot.pause()
            await pilot.pause()
            assert audit_layout(studio) == [], layout.layout_id


@pytest.mark.asyncio
async def test_optimize_keeps_the_builtin_curated_and_read_only():
    app = _OpsApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        layout = studio.layout_store.get_layout("preset_y2k_aesthetic")
        assert layout is not None
        studio.apply_layout(layout)
        await pilot.pause()
        assert studio._optimize_view(announce=False)
        await pilot.pause()
        assert studio.current_layout is layout
        assert studio.current_layout.is_builtin
        assert studio.query_one("#plr-dashboard").is_editable is False


@pytest.mark.asyncio
async def test_generate_applies_an_editable_unique_mix_and_fits_it():
    app = _OpsApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        studio._generate_view()
        await pilot.pause()
        await pilot.pause()
        dashboard = studio.query_one("#plr-dashboard")
        assert dashboard.is_editable
        assert studio.current_layout is not None
        assert not studio.current_layout.is_builtin
        cards = list(studio.query(VisualizerCard))
        assert 1 <= len(cards) <= 10
        families = [card.engine.visual_family_id for card in cards]
        assert len(families) == len(set(families))
        assert audit_layout(studio) == []


@pytest.mark.asyncio
async def test_ops_buttons_are_wired_and_compact():
    app = _OpsApp()
    async with app.run_test(size=(100, 30)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        optimize = studio.query_one("#btn-plr-optimize", Button)
        generate = studio.query_one("#btn-plr-generate", Button)
        seed = studio.query_one("#btn-plr-seed", Button)
        assert optimize.compact is True
        assert generate.compact is True
        assert seed.compact is True
        assert optimize.region.height == 1

        generate.press()
        await pilot.pause()
        await pilot.pause()
        assert studio.current_layout is not None
        assert not studio.current_layout.is_builtin

        optimize.press()
        await pilot.pause()
        await pilot.pause()
        assert audit_layout(studio) == []


def test_card_minimums_are_larger_than_raw_engine_minimums():
    assert MIN_CARD_WIDTH > VisualizerRegistry.get("mirrored_dance").min_width
    assert MIN_CARD_HEIGHT > VisualizerRegistry.get("mirrored_dance").min_height


@pytest.mark.asyncio
async def test_gap_cycling_keeps_an_optimized_view_audited():
    app = _OpsApp()
    async with app.run_test(size=(100, 30)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert layout is not None
        studio.apply_layout(layout)
        await pilot.pause()
        assert studio._optimize_view(announce=False)
        await pilot.pause()
        await pilot.pause()
        for _ in range(4):
            studio._cycle_gap()
            await pilot.pause()
            await pilot.pause()
            assert audit_layout(studio) == [], studio.active_gap


@pytest.mark.asyncio
async def test_saved_optimized_layout_round_trips(tmp_path):
    store = VisionLayoutStore(tmp_path)

    class _StoreApp(App):
        def compose(self) -> ComposeResult:
            yield PlayerStudioWidget(layout_store=store)

    app = _StoreApp()
    async with app.run_test(size=(120, 36)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        layout = store.get_layout("preset_retrowave_sunset")
        assert layout is not None
        studio.apply_layout(layout)
        await pilot.pause()
        assert studio._optimize_view(announce=False)
        await pilot.pause()
        card_count = len(studio.query_one("#plr-dashboard").cards)

        studio._handle_save_layout("OPTIMIZED TEST")
        await pilot.pause()

        saved = [candidate for candidate in store.list_layouts() if not candidate.is_builtin]
        assert len(saved) == 1
        assert len(saved[0].cards) == card_count
        assert saved[0].gap_distance == studio.active_gap
        assert saved[0].dashboard_layout == studio.query_one("#plr-dashboard").layout_style

        studio.apply_layout(saved[0])
        await pilot.pause()
        await pilot.pause()
        assert audit_layout(studio) == []


@pytest.mark.asyncio
async def test_fit_mode_survives_theme_cycling():
    app = _OpsApp()
    async with app.run_test(size=(100, 30)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert layout is not None
        studio.apply_layout(layout)
        await pilot.pause()
        assert studio._optimize_view(announce=False)
        await pilot.pause()
        await pilot.pause()
        for _ in range(3):
            studio._cycle_layout(1)
            await pilot.pause()
            await pilot.pause()
            assert studio._ops_managed
            assert audit_layout(studio) == []


@pytest.mark.asyncio
async def test_generate_with_explicit_seed_reproduces_mix():
    app = _OpsApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        await pilot.pause()
        studio._generate_view(seed=777)
        await pilot.pause()
        await pilot.pause()
        first = [card.engine.id for card in studio.query(VisualizerCard)]
        first_layout = studio.current_layout
        assert first_layout is not None and first_layout.layout_id == "generated_777"

        studio._generate_view(seed=777)
        await pilot.pause()
        await pilot.pause()
        second = [card.engine.id for card in studio.query(VisualizerCard)]
        assert first and first == second


@pytest.mark.asyncio
async def test_seed_modal_accepts_digits_and_rejects_junk():
    class _SeedHost(App):
        def __init__(self) -> None:
            super().__init__()
            self.dismissed_with: int | None | str = "unset"

        def on_mount(self) -> None:
            self.push_screen(SeedInputModal(), self._captured)

        def _captured(self, seed: int | None) -> None:
            self.dismissed_with = seed

    valid = _SeedHost()
    async with valid.run_test() as pilot:
        await pilot.pause()
        modal = valid.screen
        assert isinstance(modal, SeedInputModal)
        modal.query_one("#input-seed", Input).focus()
        await pilot.press("4", "2", "enter")
        await pilot.pause()
        assert valid.dismissed_with == 42

    invalid = _SeedHost()
    async with invalid.run_test() as pilot:
        await pilot.pause()
        modal = invalid.screen
        assert isinstance(modal, SeedInputModal)
        modal.query_one("#input-seed", Input).value = "not-a-seed"
        modal.query_one("#btn-seed-confirm", Button).press()
        await pilot.pause()
        assert invalid.dismissed_with is None
