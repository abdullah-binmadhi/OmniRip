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
