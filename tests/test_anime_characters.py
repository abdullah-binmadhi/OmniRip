"""Unit tests for theme-dressed ASCII anime characters."""

from harvester.ui.visuals.anime_characters import (
    THEME_ANIME_CHARACTERS,
    get_anime_character,
)


def test_theme_anime_characters_count_and_content():
    """Verify that all 20 presets have distinct anime characters with rich ASCII art."""
    assert len(THEME_ANIME_CHARACTERS) == 20

    seen_names = set()
    for preset_id, char in THEME_ANIME_CHARACTERS.items():
        assert char.preset_id == preset_id
        assert len(char.name) > 0
        assert len(char.title) > 0
        assert len(char.outfit_desc) > 0
        assert len(char.ascii_art) > 50  # Must be a rich multi-line ASCII drawing
        assert "\n" in char.ascii_art
        seen_names.add(char.name)

    # Every character must have a unique name
    assert len(seen_names) == 20


def test_get_anime_character_lookup():
    """Verify lookup by preset_id with graceful fallback."""
    y2k_char = get_anime_character("preset_y2k_aesthetic")
    assert "Aimi" in y2k_char.name
    assert "Butterfly" in y2k_char.outfit_desc

    cyber_char = get_anime_character("preset_cyberpunk_2077")
    assert "V-Kira" in cyber_char.name

    matrix_char = get_anime_character("preset_matrix_terminal")
    assert "Trinity-X" in matrix_char.name

    # Unknown preset fallback
    fallback = get_anime_character("non_existent_preset")
    assert fallback is not None
    assert "Aimi" in fallback.name


def test_all_31_braille_characters():
    """Verify that all 31 characters exist, have Braille artwork, and are unique."""
    from harvester.ui.visuals.anime_characters import list_all_anime_characters

    all_chars = list_all_anime_characters()
    assert len(all_chars) == 31

    char_ids = {c.char_id for c in all_chars}
    assert len(char_ids) == 31

    for c in all_chars:
        assert len(c.ascii_art) > 50
        assert "\n" in c.ascii_art
        # Check that art contains Braille patterns or unicode
        assert any(ord(ch) >= 0x2800 for ch in c.ascii_art)


def test_anime_palettes_and_custom_hex():
    """Verify all 10 curated palettes and custom hex gradient generation."""
    from harvester.ui.visuals.anime_characters import (
        ANIME_PALETTES,
        _build_custom_stops,
        _interpolate_color_stops,
    )

    assert len(ANIME_PALETTES) == 10
    for pal_id, pal_meta in ANIME_PALETTES.items():
        assert "stops" in pal_meta
        assert len(pal_meta["stops"]) >= 2
        for stop_color, stop_pos in pal_meta["stops"]:
            assert stop_color.startswith("#")
            assert 0.0 <= stop_pos <= 1.0

    # Custom stops
    custom = _build_custom_stops("#ff007f")
    assert len(custom) == 3
    assert custom[1][0] == "#ff007f"

    # Interpolation
    c0 = _interpolate_color_stops(custom, 0.0)
    c1 = _interpolate_color_stops(custom, 1.0)
    assert c0.startswith("#")
    assert c1.startswith("#")


def test_animated_rendering_fx():
    """Verify 60 FPS animation rendering across all 5 FX modes."""
    from harvester.ui.visuals.anime_characters import (
        ANIME_FX_MODES,
        get_anime_character,
        render_animated_anime_frame,
    )
    from harvester.ui.visuals.base import AudioFeatureContext

    char = get_anime_character("preset_cyberpunk_2077")
    ctx = AudioFeatureContext(is_playing=True, transient_flag=True, spectral_centroid=2500.0)

    assert len(ANIME_FX_MODES) == 5
    for fx_mode in ANIME_FX_MODES:
        frame = render_animated_anime_frame(
            character=char,
            palette_id="cyberpunk_neon",
            fx_mode=fx_mode,
            tick=60,
            ctx=ctx,
            max_lines=24,
            max_cols=50,
        )
        assert frame is not None
        assert len(frame.plain) > 0

    # Test with custom hex
    custom_frame = render_animated_anime_frame(
        character=char,
        palette_id="custom",
        custom_hex="#00e5ff",
        fx_mode="scanline_shimmer",
        tick=120,
    )
    assert custom_frame is not None
    assert len(custom_frame.plain) > 0


def test_anime_character_autofit_and_scaling():
    """Verify that wide Braille anime characters auto-fit inside narrow companion frames."""
    from harvester.ui.visuals.anime_characters import (
        list_all_anime_characters,
        render_animated_anime_frame,
        fit_braille_art,
    )

    all_chars = list_all_anime_characters()
    # Test all 31 characters in a realistic narrow companion panel (e.g. 34 cols x 18 lines)
    for c in all_chars:
        frame = render_animated_anime_frame(
            character=c,
            palette_id="electric_amethyst",
            max_lines=18,
            max_cols=34,
        )
        lines = frame.plain.split("\n")
        assert len(lines) <= 18
        for line in lines:
            assert len(line) <= 34, f"Line exceeded max_cols: len({line}) > 34 for char {c.char_id}"

