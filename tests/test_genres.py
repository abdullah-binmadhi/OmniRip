"""Tests for the genre intent engine (docs/01 D38)."""

from __future__ import annotations

from harvester.analysis.enhancement.eq import EQ_FREQUENCIES, MasteringEQSettings
from harvester.analysis.enhancement.genres import (
    DEFAULT_GENRE_INTENSITY,
    GENRE_ALIASES,
    GENRE_INTENSITIES,
    GENRE_PROFILES,
    MAX_BLEND_GAIN_DB,
    MAX_MIX_GENRES,
    MAX_PROFILE_BANDS,
    MAX_SINGLE_GAIN_DB,
    MIN_UNTOUCHED_BANDS,
    TOUCH_EPSILON_DB,
    blend_genre_bands,
    choices_from_tags,
    compose_master_settings,
    effective_preset,
    genre_hpf,
    recipe_line,
    resolve_genre_names,
)
from harvester.analysis.enhancement.presets import PRESETS


def test_profiles_are_tasteful_and_valid():
    assert "neutral" in GENRE_PROFILES
    for key, profile in GENRE_PROFILES.items():
        assert key == profile.key
        assert profile.label and profile.blurb
        assert len(profile.bands) <= MAX_PROFILE_BANDS, key
        assert -0.1 >= profile.limiter_ceiling_dbfs >= -1.5, key
        assert 0.5 <= profile.residual_width <= 1.3, key
        for freq, gain in profile.bands.items():
            assert freq in EQ_FREQUENCIES, (key, freq)
            assert abs(gain) <= MAX_SINGLE_GAIN_DB, (key, freq, gain)


def test_alias_table_resolves_every_entry():
    for alias, key in GENRE_ALIASES.items():
        assert key in GENRE_PROFILES, alias
        assert alias == alias.lower()


def test_resolve_genre_names_handles_slashes_weights_and_caps():
    choice = resolve_genre_names(["Trap", "hip hop", "R&B/Soul"])
    assert choice.keys == ("hip_hop_trap", "rnb_soul")
    assert abs(sum(weight for _key, weight in choice.mix) - 1.0) < 1e-9
    assert choice.source == "tags"

    weighted = resolve_genre_names(
        ["hip hop", "pop"], weights={"hip hop": 3.0, "pop": 1.0}
    )
    assert weighted.mix[0] == ("hip_hop_trap", 0.75)

    many = resolve_genre_names(
        ["trap", "pop", "house", "techno", "rock", "jazz", "metal", "country"]
    )
    assert len(many.mix) == MAX_MIX_GENRES

    assert not resolve_genre_names(["purple monkey dishwasher"]).detected
    assert not resolve_genre_names(["neutral"]).detected
    assert not resolve_genre_names(None).detected


def test_blend_scales_with_intensity_and_never_stacks():
    choice = resolve_genre_names(["hip hop"])
    subtle = blend_genre_bands(choice, "subtle")
    bold = blend_genre_bands(choice, "bold")
    assert 0 < subtle[63] < bold[63] <= MAX_SINGLE_GAIN_DB
    assert DEFAULT_GENRE_INTENSITY == "subtle"
    assert set(GENRE_INTENSITIES) == {"subtle", "balanced", "bold"}

    # Opposing intents cancel instead of stacking: lo-fi -1.0 @8k vs latin +1.5 @8k
    mixed = resolve_genre_names(["lo-fi", "reggaeton"])
    bands = blend_genre_bands(mixed, "balanced")
    assert abs(bands.get(8000, 0.0)) <= 0.3  # near neutral, never +1.5


def test_blend_keeps_at_least_six_untouched_bands():
    choice = resolve_genre_names(
        ["trap", "pop", "house", "techno", "rock", "metal"], max_genres=MAX_MIX_GENRES
    )
    bands = blend_genre_bands(choice, "bold")
    touched = [f for f in EQ_FREQUENCIES if abs(bands.get(f, 0.0)) >= TOUCH_EPSILON_DB]
    assert len(touched) <= len(EQ_FREQUENCIES) - MIN_UNTOUCHED_BANDS
    assert all(abs(gain) <= MAX_BLEND_GAIN_DB + 1e-9 for gain in bands.values())


def test_compose_master_settings_adds_genre_curve_to_user_eq():
    user = MasteringEQSettings()
    user.set_band(63, 1.0)
    user.output_trim_db = -1.0

    choice = resolve_genre_names(["trap"])
    composed = compose_master_settings(user, choice, "balanced")
    assert composed.bands[63] > user.bands[63]  # genre adds on top
    assert composed.output_trim_db == -1.0
    assert composed.enabled is True
    assert "Balanced" in composed.preset_name

    jazz = compose_master_settings(MasteringEQSettings(), resolve_genre_names(["jazz"]))
    assert jazz.hpf_30hz is True
    assert genre_hpf(resolve_genre_names(["jazz"])) is True
    assert genre_hpf(resolve_genre_names(["techno"])) is False


def test_effective_preset_applies_width_and_ceiling_policy():
    base = PRESETS["conservative"]
    house = effective_preset(base, resolve_genre_names(["house"]))
    assert house.residual_stereo_width > base.residual_stereo_width
    assert house.ceiling_dbfs <= base.ceiling_dbfs

    narrowed = effective_preset(PRESETS["narrow_stereo"], resolve_genre_names(["house"]))
    assert narrowed.residual_stereo_width <= PRESETS["narrow_stereo"].residual_stereo_width

    classical = effective_preset(base, resolve_genre_names(["classical"]))
    assert classical.ceiling_dbfs == -1.0

    untouched = effective_preset(base, resolve_genre_names(["unknown genre"]))
    assert untouched is base


def test_recipe_line_and_tag_detection():
    line = recipe_line(resolve_genre_names(["trap", "drill"]), "subtle", ceiling_dbfs=-0.3)
    assert "Hip-Hop / Trap" in line and "Drill / UK" in line
    assert "Subtle" in line and "limiter -0.3 dBFS" in line
    assert "Neutral" in recipe_line(resolve_genre_names(None))

    tags = {
        "TCON": ["Hip-Hop/Rap", "Trap"],
        "genre": "lo-fi hip hop",
    }
    choice = choices_from_tags(tags)
    assert choice.keys == ("hip_hop_trap", "lofi_chill")


def test_tag_hunt_ignores_non_genre_metadata():
    noisy = {
        "title": "House of Cards",
        "artist": "Techno Man",
        "comment": "trap banger",
        "album": {"name": "Jazz Nights"},
    }
    assert not choices_from_tags(noisy).detected

    nested = {"format": {"tags": {"genre": "Deep House", "title": "ignored"}}}
    assert choices_from_tags(nested).keys == ("house",)
