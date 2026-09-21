"""Processing presets + loud engine reporting (docs/13)."""

from __future__ import annotations

from harvester.processing import (
    DEFAULT_PRESET,
    ENGINE_NOTES,
    PRESETS,
    degraded,
    engine_note,
    get_preset,
    next_preset,
    normalize_preset,
    preset_names,
)


def test_preset_names_are_ordered_by_cost() -> None:
    """fetch_only < standard < neural_full, in that order."""
    assert preset_names() == ("fetch_only", "standard", "neural_full")


def test_fetch_only_runs_no_separation_stage() -> None:
    """FETCH ONLY is acquisition + tagging only — no stems, no lanes, no extras."""
    preset = get_preset("fetch_only")
    assert preset.separation is False
    assert preset.extra_sources is False
    assert preset.tags is False
    assert preset.enhancement is False
    assert "no lanes" in preset.summary


def test_standard_separates_but_adds_no_extras() -> None:
    preset = get_preset("standard")
    assert preset.separation is True
    assert preset.extra_sources is False
    assert preset.tags is False


def test_neural_full_enables_everything() -> None:
    preset = get_preset("neural_full")
    assert (preset.separation, preset.extra_sources, preset.tags, preset.enhancement) == (
        True,
        True,
        True,
        True,
    )


def test_normalize_preset_falls_back_to_default() -> None:
    assert normalize_preset(None) == DEFAULT_PRESET
    assert normalize_preset("") == DEFAULT_PRESET
    assert normalize_preset("nonsense") == DEFAULT_PRESET
    # Tolerant spellings from config files / CLI flags.
    assert normalize_preset("NEURAL-FULL") == "neural_full"
    assert normalize_preset(" neural full ") == "neural_full"


def test_next_preset_cycles_and_wraps() -> None:
    assert next_preset("fetch_only") == "standard"
    assert next_preset("standard") == "neural_full"
    assert next_preset("neural_full") == "fetch_only"
    assert next_preset("garbage") == next_preset(DEFAULT_PRESET)


def test_engine_note_names_every_engine() -> None:
    assert engine_note("bs_roformer") == ENGINE_NOTES["bs_roformer"]
    assert engine_note("ensemble") == ENGINE_NOTES["ensemble"]
    assert engine_note("hdemucs") == ENGINE_NOTES["hdemucs"]
    assert "eco" in engine_note("eco")
    assert "mid/side" in engine_note("eco")
    assert engine_note(None) == ENGINE_NOTES["unknown"]
    # A 6-source run reports both halves instead of hiding the extras.
    assert "extras" in engine_note("bs_roformer+htdemucs_6s")


def test_degraded_only_for_the_eco_fallback() -> None:
    assert degraded("eco") is True
    assert degraded("ECO") is True
    assert degraded("bs_roformer") is False
    assert degraded("hdemucs") is False
    assert degraded(None) is False


def test_presets_are_self_describing() -> None:
    """Every preset carries a label, a detail line and a RAM estimate."""
    for name, preset in PRESETS.items():
        assert preset.name == name
        assert preset.label
        assert preset.detail
        assert preset.est_ram_gb > 0
        assert preset.summary
