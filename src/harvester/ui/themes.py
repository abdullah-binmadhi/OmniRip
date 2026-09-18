"""Theme registry and dynamic switcher for OmniRip TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.theme import Theme

if TYPE_CHECKING:
    from textual.app import App


CYBERPUNK_THEME = Theme(
    name="cyberpunk-neon",
    primary="#ff007f",
    secondary="#00f0ff",
    accent="#ffe600",
    warning="#ffaa00",
    error="#ff3366",
    success="#00ff9f",
    surface="#120e24",
    panel="#1a1435",
    background="#0d091a",
    dark=True,
)

AVAILABLE_THEMES: list[tuple[str, str]] = [
    ("Tokyo Night", "tokyo-night"),
    ("Cyberpunk Neon", "cyberpunk-neon"),
    ("Catppuccin Mocha", "catppuccin-mocha"),
    ("Nordic Frost", "nord"),
    ("Dracula Night", "dracula"),
    ("Gruvbox Retro", "gruvbox"),
    ("Monokai Pro", "monokai"),
    ("Textual Dark", "textual-dark"),
]


def register_custom_themes(app: App) -> None:
    """Register custom OmniRip palettes with the Textual app theme manager."""
    try:
        app.register_theme(CYBERPUNK_THEME)
    except Exception:
        # Theme may already be registered or app does not support register_theme
        pass


def cycle_theme(app: App) -> str:
    """
    Cycle to the next available theme, apply it to the app, and return
    the human-readable display name of the newly activated theme.
    """
    register_custom_themes(app)
    theme_ids = [tid for _, tid in AVAILABLE_THEMES]
    current = getattr(app, "theme", "tokyo-night")
    if current in theme_ids:
        next_idx = (theme_ids.index(current) + 1) % len(theme_ids)
    else:
        next_idx = 0

    next_name, next_id = AVAILABLE_THEMES[next_idx]
    try:
        app.theme = next_id
    except Exception:
        app.theme = "textual-dark"
        next_name = "Textual Dark"
    return next_name
