"""Unit tests for PLAYER Studio UI composition and interactions."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from harvester.ui.player_studio import PlayerStudioWidget


class DummyPlayerApp(App):
    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()


@pytest.mark.asyncio
async def test_player_studio_compose():
    app = DummyPlayerApp()
    async with app.run_test():
        studio = app.query_one(PlayerStudioWidget)
        assert studio is not None

        # Check top bar buttons (labels come from the selected page design).
        presets_btn = app.query_one("#btn-plr-presets")
        assert str(presets_btn.label) == studio.current_design.top_controls[1]

        omnirip_btn = app.query_one("#btn-plr-omnirip")
        assert str(omnirip_btn.label) == studio.current_design.top_controls[0]

        gap_btn = app.query_one("#btn-plr-gap")
        assert str(gap_btn.label) == studio.current_design.top_controls[4].format(gap=1)

        # Check music player dock (default design is the first starter layout)
        play_btn = app.query_one("#btn-plr-play")
        assert str(play_btn.label) == "◉ RUN"

        # Test gap cycle
        studio._cycle_gap()
        assert studio.active_gap == 2

        # Test full TUI redesign on layout application
        matrix_layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert matrix_layout is not None
        studio.apply_layout(matrix_layout)
        assert studio.current_theme.theme_id == "matrix_terminal"
        top_bar = studio.query_one("#plr-top-bar")
        assert top_bar.styles.background.hex.lower() == studio.current_theme.surface_color.lower()

        # Verify Anime Companion Character and Outfit Lore
        from harvester.ui.player_studio import AnimeCompanionWidget
        companion = studio.query_one("#plr-anime-companion", AnimeCompanionWidget)
        assert companion is not None
        assert "Trinity-X" in companion.character.name
        assert "trenchcoat" in companion.character.outfit_desc.lower()

        # Verify design-specific controls and the LCD transport vocabulary.
        assert str(omnirip_btn.label) == studio.current_design.top_controls[0]
        assert "[>PLAY]" in str(play_btn.label)

        # Apply Cyberpunk layout with cyber_brackets
        cyber_layout = studio.layout_store.get_layout("preset_cyberpunk_2077")
        assert cyber_layout is not None
        studio.apply_layout(cyber_layout)
        assert "V-Kira" in companion.character.name
        assert str(omnirip_btn.label) == studio.current_design.top_controls[0]
        assert "[>> EXEC]" in str(play_btn.label)


def test_legacy_full_vision_module_is_removed():
    """Regression: the PLAYER rename must not leave old module names behind."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("harvester.ui.full_vision")
    importlib.import_module("harvester.ui.player_studio")

    from harvester.ui.player_studio import PlayerStudioWidget

    assert "fvs-" not in PlayerStudioWidget.DEFAULT_CSS


def test_auto_fidelity_resolves_to_a_supported_mode():
    from harvester.ui.render_fidelity import MODES

    studio = PlayerStudioWidget()
    assert studio.fidelity_mode in MODES
    assert studio.reduced_motion is False


@pytest.mark.asyncio
async def test_fidelity_and_reduced_motion_thread_from_screen():
    from textual.widgets import Label

    from harvester.ui.player_studio import AnimeCompanionWidget, PlayerScreen

    class ConfiguredPlayerApp(App):
        def compose(self) -> ComposeResult:
            yield PlayerScreen(fidelity_mode="braille", reduced_motion=True)

    app = ConfiguredPlayerApp()
    async with app.run_test(size=(120, 36)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        companion = app.query_one("#plr-anime-companion", AnimeCompanionWidget)
        assert studio.fidelity_mode == "braille"
        assert companion.fidelity_mode == "braille"
        assert studio.reduced_motion is True
        assert companion.reduced_motion is True

        await pilot.pause()
        motif = app.query_one("#plr-motif", Label)
        before = str(motif.render())
        for _ in range(30):
            studio._motion.observe(studio, studio._resolved_page)
            companion._tick_60fps()
        assert str(motif.render()) == before

        scene = companion.query_one("#anime-char-scene", Label)
        companion.tick = 10
        companion._update_session_labels()
        first = str(scene.render())
        companion.tick = 900
        companion._update_session_labels()
        assert str(scene.render()) == first


@pytest.mark.asyncio
async def test_preset_catalog_modal_and_apply():
    from harvester.services.vision_layout_store import VisionLayoutStore
    from harvester.ui.player_studio import PresetCatalogModal

    store = VisionLayoutStore()
    modal = PresetCatalogModal(store)
    assert len(modal.all_presets) >= 20
    preset_ids = [p.layout_id for p in modal.all_presets]
    assert "preset_y2k_aesthetic" in preset_ids
    assert "preset_cyberpunk_2077" in preset_ids
    assert "preset_matrix_terminal" in preset_ids

    # Test composing the modal inside an App
    class ModalApp(App):
        def compose(self) -> ComposeResult:
            yield PresetCatalogModal(store)

    modal_app = ModalApp()
    async with modal_app.run_test():
        m = modal_app.query_one(PresetCatalogModal)
        assert m is not None
        # Verify apply buttons have valid IDs
        apply_btn = modal_app.query_one("#btn-preset-apply-preset_matrix_terminal")
        assert apply_btn is not None
        assert "APPLY" in str(apply_btn.label)


@pytest.mark.asyncio
async def test_anime_companion_interactions_and_modals():
    from harvester.ui.player_studio import (
        AnimeCharacterSelectModal,
        AnimeCompanionWidget,
        AnimePaletteSelectModal,
    )
    from harvester.ui.visuals.anime_characters import get_anime_character
    from harvester.ui.visuals.base import AudioFeatureContext

    # 1. Test AnimeCompanionWidget cycles and ticks
    class CompanionApp(App):
        def compose(self) -> ComposeResult:
            yield AnimeCompanionWidget(character=get_anime_character("preset_y2k_aesthetic"))

    app = CompanionApp()
    async with app.run_test():
        comp = app.query_one(AnimeCompanionWidget)
        assert "Aimi" in comp.character.name

        # Cycle character forward and backward
        initial_name = comp.character.name
        comp._cycle_character(1)
        assert comp.character.name != initial_name
        comp._cycle_character(-1)
        assert comp.character.name == initial_name

        # Cycle FX mode
        initial_fx = comp.fx_mode
        comp._cycle_fx()
        assert comp.fx_mode != initial_fx

        # Feed audio context and tick frame
        ctx = AudioFeatureContext(is_playing=True, transient_flag=True, spectral_centroid=3000.0)
        comp.feed_audio(ctx)
        assert comp.audio_ctx == ctx
        comp._tick_60fps()

        # Test palette selection callback
        comp._on_palette_selected(("matrix_phosphor", None))
        assert comp.palette_id == "matrix_phosphor"
        comp._on_palette_selected(("custom", "#ff007f"))
        assert comp.palette_id == "custom"
        assert comp.custom_hex == "#ff007f"

    # 2. Test AnimeCharacterSelectModal composition
    char_modal = AnimeCharacterSelectModal()
    assert len(char_modal.all_characters) == 31
    class CharModalApp(App):
        def compose(self) -> ComposeResult:
            yield AnimeCharacterSelectModal()

    c_app = CharModalApp()
    async with c_app.run_test():
        modal = c_app.query_one(AnimeCharacterSelectModal)
        assert modal is not None
        btn = c_app.query_one("#btn-select-char-char_02", Button)
        assert btn is not None

    # 3. Test AnimePaletteSelectModal composition
    class PalModalApp(App):
        def compose(self) -> ComposeResult:
            yield AnimePaletteSelectModal()

    p_app = PalModalApp()
    async with p_app.run_test():
        p_modal = p_app.query_one(AnimePaletteSelectModal)
        assert p_modal is not None
        apply_pal = p_app.query_one("#btn-apply-pal-matrix_phosphor", Button)
        assert apply_pal is not None
