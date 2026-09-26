"""Unit tests for Full Vision Studio UI composition and interactions."""

import pytest
from textual.app import App, ComposeResult

from harvester.ui.full_vision import (
    FullVisionStudioWidget,
    SaveLayoutModal,
    AddSongModal,
)


class DummyVisionApp(App):
    def compose(self) -> ComposeResult:
        yield FullVisionStudioWidget()


@pytest.mark.asyncio
async def test_full_vision_studio_compose():
    app = DummyVisionApp()
    async with app.run_test() as pilot:
        studio = app.query_one(FullVisionStudioWidget)
        assert studio is not None

        # Check top bar buttons (btn-fvs-theme removed in favor of presets redesign)
        presets_btn = app.query_one("#btn-fvs-presets")
        assert "PRESETS" in str(presets_btn.label)

        omnirip_btn = app.query_one("#btn-fvs-omnirip")
        assert "OMNIRIP" in str(omnirip_btn.label)

        gap_btn = app.query_one("#btn-fvs-gap")
        assert "GAP:" in str(gap_btn.label)

        # Check music player dock
        play_btn = app.query_one("#btn-fvs-play")
        assert "PLAY" in str(play_btn.label)

        # Test gap cycle
        studio._cycle_gap()
        assert studio.active_gap == 2

        # Test full TUI redesign on layout application
        matrix_layout = studio.layout_store.get_layout("preset_matrix_terminal")
        assert matrix_layout is not None
        studio.apply_layout(matrix_layout)
        assert studio.current_theme.theme_id == "matrix_terminal"
        top_bar = studio.query_one("#fvs-top-bar")
        assert top_bar.styles.background.hex.lower() == studio.current_theme.surface_color.lower()


@pytest.mark.asyncio
async def test_preset_catalog_modal_and_apply():
    from harvester.ui.full_vision import PresetCatalogModal
    from harvester.services.vision_layout_store import VisionLayoutStore

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
    async with modal_app.run_test() as pilot:
        m = modal_app.query_one(PresetCatalogModal)
        assert m is not None
        # Verify apply buttons have valid IDs
        apply_btn = modal_app.query_one("#btn-preset-apply-preset_matrix_terminal")
        assert apply_btn is not None
        assert "APPLY" in str(apply_btn.label)
