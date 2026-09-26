"""Full Vision Studio: Terminal Music Player & Visual Design Canvas.

Integrates Google Stitch API design tokens, custom visualizer layouts (with
persistent save/load), 60 FPS audio feature synchronization, and a complete
cyberpunk music player dock. Can run as a standalone terminal app (spawned in a
new window via AppleScript) or an in-app fullscreen studio.
"""

from __future__ import annotations
from harvester.ui.full_vision_designs import get_full_vision_design

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.markup import escape
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
)

from harvester.services.stitch import STITCH_BUILTIN_THEMES, StitchClient, StitchTheme
from harvester.services.vision_layout_store import (
    VisionCardConfig,
    VisionLayout,
    VisionLayoutStore,
)
from harvester.services.vision_player import (
    LoopMode,
    PlaybackState,
    PlaylistTrack,
    VisionAudioPlayer,
)
from harvester.ui.visual_dashboard import (
    PALETTES,
    VisualCatalogModal,
    VisualDashboardWidget,
    VisualizerCard,
    VisualizerEngineCanvas,
)
from harvester.ui.visuals.anime_characters import (
    ANIME_FX_MODES,
    ANIME_PALETTES,
    AnimeCharacter,
    get_anime_character,
    list_all_anime_characters,
    render_animated_anime_frame,
)
from harvester.ui.visuals.base import AudioFeatureContext
from harvester.ui.visuals.registry import VisualizerRegistry

logger = logging.getLogger(__name__)


def launch_full_vision_external() -> bool:
    """Launch Full Vision Studio in a new external macOS Terminal or iTerm tab."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    venv_python = repo_root / ".venv" / "bin" / "python3"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    cmd_script = f"cd '{repo_root}' && '{python_bin}' -m harvester.ui.full_vision"

    if sys.platform == "darwin":
        # Check if iTerm2 or standard Terminal is preferred
        is_iterm = "iterm" in os.environ.get("TERM_PROGRAM", "").lower()
        if is_iterm:
            apple_script = f'''
            tell application "iTerm"
                activate
                if (count of windows) = 0 then
                    create window with default profile
                else
                    tell current window
                        create tab with default profile
                    end tell
                end if
                tell current session of current window
                    write text "{cmd_script}"
                end tell
            end tell
            '''
        else:
            apple_script = f'''
            tell application "Terminal"
                activate
                tell application "System Events"
                    tell process "Terminal"
                        keystroke "t" using command down
                    end tell
                end tell
                delay 0.3
                do script "{cmd_script}" in selected tab of front window
            end tell
            '''

        try:
            res = subprocess.run(
                ["osascript", "-e", apple_script],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                logger.info("Successfully launched Full Vision in new macOS terminal window.")
                return True
            else:
                logger.warning("AppleScript launch returned %d: %s", res.returncode, res.stderr)
        except Exception as exc:
            logger.warning("Failed to invoke osascript: %s", exc)

    # Fallback: spawn background terminal process if tmux or standard terminal
    try:
        subprocess.Popen(
            [python_bin, "-m", "harvester.ui.full_vision"],
            cwd=str(repo_root),
            start_new_session=True,
        )
        return True
    except Exception as exc:
        logger.error("Failed to launch background Full Vision process: %s", exc)
        return False


class SaveLayoutModal(ModalScreen[Optional[str]]):
    """Modal dialog for saving the current canvas design blueprint."""

    DEFAULT_CSS = """
    SaveLayoutModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.85);
    }
    #save-layout-box {
        width: 60;
        height: auto;
        border: heavy #00ffcc;
        background: #121820;
        padding: 1 2;
    }
    #save-layout-title {
        color: #00ffcc;
        text-style: bold;
        margin-bottom: 1;
        text-align: center;
    }
    .save-input {
        margin: 1 0;
        border: round #7209b7;
    }
    .save-actions {
        width: 100%;
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    .save-btn {
        margin: 0 1;
        min-width: 14;
        height: 3;
    }
    """

    def __init__(self, current_name: str = "My Custom Canvas"):
        super().__init__()
        self.initial_name = current_name

    def compose(self) -> ComposeResult:
        with Vertical(id="save-layout-box"):
            yield Label("💾  SAVE FULL VISION CANVAS DESIGN", id="save-layout-title")
            yield Label("Layout Name:")
            yield Input(value=self.initial_name, id="input-layout-name", classes="save-input")
            yield Label("Description:")
            yield Input(placeholder="e.g. Dual 3D Synthwave with 60 FPS telemetry", id="input-layout-desc", classes="save-input")
            with Horizontal(classes="save-actions"):
                yield Button("CANCEL", variant="default", id="btn-save-cancel", classes="save-btn")
                yield Button("SAVE DESIGN", variant="primary", id="btn-save-confirm", classes="save-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-confirm":
            name_input = self.query_one("#input-layout-name", Input).value.strip()
            if name_input:
                self.dismiss(name_input)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)


class AddSongModal(ModalScreen[Optional[Path]]):
    """Modal dialog for loading a music file into the playlist."""

    DEFAULT_CSS = """
    AddSongModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.85);
    }
    #add-song-box {
        width: 72;
        height: auto;
        border: heavy #ff007f;
        background: #121820;
        padding: 1 2;
    }
    #add-song-title {
        color: #ff007f;
        text-style: bold;
        margin-bottom: 1;
        text-align: center;
    }
    .song-input {
        margin: 1 0;
        border: round #ff007f;
    }
    .song-actions {
        width: 100%;
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    .song-btn {
        margin: 0 1;
        min-width: 14;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add-song-box"):
            yield Label("🎵  LOAD AUDIO TRACK OR PLAYLIST", id="add-song-title")
            yield Label("Enter absolute or relative audio file path (WAV, MP3, FLAC, OGG, AAC):")
            yield Input(placeholder="/path/to/song.mp3 or ~/Music/track.wav", id="input-song-path", classes="song-input")
            with Horizontal(classes="song-actions"):
                yield Button("GENERATE DEMO SYNTH", variant="warning", id="btn-song-demo", classes="song-btn")
                yield Button("CANCEL", variant="default", id="btn-song-cancel", classes="song-btn")
                yield Button("LOAD TRACK", variant="primary", id="btn-song-load", classes="song-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-song-load":
            raw_path = self.query_one("#input-song-path", Input).value.strip()
            if raw_path:
                path = Path(raw_path).expanduser().resolve()
                if path.exists():
                    self.dismiss(path)
                    return
            self.dismiss(None)
        elif event.button.id == "btn-song-demo":
            # Generate a 3-minute synthetic cyberpunk test song
            demo_path = Path("/tmp/omnirip_cyberpunk_demo.wav")
            if not demo_path.exists():
                sr = 44100
                duration = 180.0
                t = np.linspace(0, duration, int(sr * duration), endpoint=False)
                # Funky bassline & chord sweep
                sig = 0.4 * np.sin(2 * np.pi * 55 * t) + 0.3 * np.sin(2 * np.pi * 110 * (1 + 0.1 * np.sin(2 * np.pi * 0.5 * t)))
                sig += 0.2 * np.sin(2 * np.pi * 440 * (1 + 0.05 * np.cos(2 * np.pi * 2.0 * t)))
                pcm = (sig * 32767).astype(np.int16)
                import wave
                with wave.open(str(demo_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(pcm.tobytes())
            self.dismiss(demo_path)
        else:
            self.dismiss(None)


class PresetCatalogModal(ModalScreen[Optional[VisionLayout]]):
    """Modal dialog for choosing from the 20 curated Google Stitch design presets."""

    DEFAULT_CSS = """
    PresetCatalogModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.90);
    }
    #preset-catalog-box {
        width: 86;
        height: 80%;
        border: heavy #00ffcc;
        background: #121820;
        padding: 1 2;
    }
    #preset-catalog-title {
        color: #00ffcc;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #preset-search {
        margin-bottom: 1;
        border: round #7209b7;
    }
    #preset-scroll-container {
        height: 1fr;
        width: 100%;
        border: solid #2d264f;
        background: #0a0e14;
        padding: 0 1;
    }
    .preset-card-row {
        height: 4;
        width: 100%;
        border-bottom: solid #1f2937;
        margin-bottom: 1;
        padding: 0 1;
        align: left middle;
    }
    .preset-card-info {
        width: 1fr;
        height: 3;
    }
    .preset-card-name {
        color: #00ffcc;
        text-style: bold;
    }
    .preset-card-desc {
        color: #8b949e;
    }
    .preset-apply-btn {
        min-width: 12;
        height: 3;
        margin-left: 1;
    }
    #preset-footer {
        height: 3;
        width: 100%;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self, layout_store: VisionLayoutStore):
        super().__init__()
        self.layout_store = layout_store
        self.all_presets = [ly for ly in self.layout_store.list_layouts() if ly.is_builtin]

    def compose(self) -> ComposeResult:
        with Vertical(id="preset-catalog-box"):
            yield Label("✨ 20 CURATED GOOGLE STITCH DESIGN PRESETS", id="preset-catalog-title")
            yield Input(placeholder="Search presets (y2k, cyberpunk, matrix, lofi, synthwave...)", id="preset-search")
            with VerticalScroll(id="preset-scroll-container"):
                for ly in self.all_presets:
                    with Horizontal(classes="preset-card-row", id=f"row-{ly.layout_id}"):
                        with Vertical(classes="preset-card-info"):
                            yield Label(f"✨ {ly.name}", classes="preset-card-name")
                            yield Label(ly.description[:70], classes="preset-card-desc")
                        btn = Button("APPLY", variant="primary", classes="preset-apply-btn", id=f"btn-preset-apply-{ly.layout_id}")
                        yield btn
            with Horizontal(id="preset-footer"):
                yield Button("CLOSE", variant="default", id="btn-preset-close")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        for ly in self.all_presets:
            try:
                row = self.query_one(f"#row-{ly.layout_id}")
                matches = (query in ly.name.lower()) or (query in ly.description.lower()) or (query in ly.stitch_theme_id.lower())
                row.display = matches
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-preset-close":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("btn-preset-apply-"):
            layout_id = event.button.id[len("btn-preset-apply-"):]
            layout = self.layout_store.get_layout(layout_id)
            self.dismiss(layout)


class AnimeCharacterSelectModal(ModalScreen[Optional[AnimeCharacter]]):
    """Modal dialog for selecting from 31 authentic Braille anime companions."""

    DEFAULT_CSS = """
    AnimeCharacterSelectModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.90);
    }
    #char-modal-box {
        width: 86;
        height: 82%;
        border: heavy #00f0ff;
        background: #0f141c;
        padding: 1 2;
    }
    #char-modal-title {
        color: #00f0ff;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #char-search-input {
        margin-bottom: 1;
        border: round #5800ff;
    }
    #char-scroll-container {
        height: 1fr;
        width: 100%;
        border: solid #1f2937;
        background: #0a0e14;
        padding: 0 1;
    }
    .char-card-row {
        height: 4;
        width: 100%;
        border-bottom: solid #1f2937;
        margin-bottom: 1;
        padding: 0 1;
        align: left middle;
    }
    .char-card-info {
        width: 1fr;
        height: 3;
    }
    .char-card-name {
        color: #00f0ff;
        text-style: bold;
    }
    .char-card-desc {
        color: #8b949e;
    }
    .char-card-btn {
        min-width: 12;
        height: 3;
        margin-left: 1;
    }
    #char-modal-footer {
        height: 3;
        width: 100%;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.all_characters = list_all_anime_characters()

    def compose(self) -> ComposeResult:
        with Vertical(id="char-modal-box"):
            yield Label("🎌 SELECT ANIME COMPANION (31 AUTHENTIC BRAILLE ARTWORKS)", id="char-modal-title")
            yield Input(placeholder="Search character name, title, or lore...", id="char-search-input")
            with VerticalScroll(id="char-scroll-container"):
                for char in self.all_characters:
                    with Horizontal(classes="char-card-row", id=f"char-row-{char.char_id}"):
                        with Vertical(classes="char-card-info"):
                            yield Label(f"👤 {char.name} • {char.title}", classes="char-card-name")
                            yield Label(char.outfit_desc.replace("\n", " • ")[:65], classes="char-card-desc")
                        yield Button("SELECT", variant="primary", id=f"btn-select-char-{char.char_id}", classes="char-card-btn")
            with Horizontal(id="char-modal-footer"):
                yield Button("CANCEL", variant="default", id="btn-char-modal-cancel")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "char-search-input":
            query = event.value.strip().lower()
            for char in self.all_characters:
                try:
                    row = self.query_one(f"#char-row-{char.char_id}")
                    matches = (query in char.name.lower()) or (query in char.title.lower()) or (query in char.outfit_desc.lower())
                    row.display = matches
                except Exception:
                    pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-char-modal-cancel":
            self.dismiss(None)
        elif btn_id.startswith("btn-select-char-"):
            char_id = btn_id[len("btn-select-char-"):]
            for c in self.all_characters:
                if c.char_id == char_id:
                    self.dismiss(c)
                    return
            self.dismiss(None)


class AnimePaletteSelectModal(ModalScreen[Optional[Tuple[str, Optional[str]]]]):
    """Modal dialog for selecting anime color palette or picking a custom hex color."""

    DEFAULT_CSS = """
    AnimePaletteSelectModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.90);
    }
    #palette-modal-box {
        width: 82;
        height: 82%;
        border: heavy #ff007f;
        background: #0f141c;
        padding: 1 2;
    }
    #palette-modal-title {
        color: #ff007f;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #custom-hex-container {
        width: 100%;
        height: 4;
        border: round #ff007f;
        padding: 0 1;
        margin-bottom: 1;
        align: left middle;
    }
    #custom-hex-label {
        width: 18;
        color: #ff007f;
        text-style: bold;
    }
    #input-custom-hex {
        width: 1fr;
        margin-right: 1;
    }
    #palette-scroll-container {
        height: 1fr;
        width: 100%;
        border: solid #1f2937;
        background: #0a0e14;
        padding: 0 1;
    }
    .pal-card-row {
        height: 3;
        width: 100%;
        border-bottom: solid #1f2937;
        margin-bottom: 1;
        padding: 0 1;
        align: left middle;
    }
    .pal-card-name {
        width: 32;
        color: #00ffcc;
        text-style: bold;
    }
    .pal-card-swatch {
        width: 1fr;
    }
    .pal-card-btn {
        min-width: 10;
        height: 3;
        margin-left: 1;
    }
    #palette-modal-footer {
        height: 3;
        width: 100%;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self, active_palette: str = "cyberpunk_neon", custom_hex: Optional[str] = None):
        super().__init__()
        self.active_palette = active_palette
        self.custom_hex = custom_hex or "#00f0ff"

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-modal-box"):
            yield Label("🎨 ANIME GRADIENT PALETTES & COLOR PICKER", id="palette-modal-title")
            with Horizontal(id="custom-hex-container"):
                yield Label("CUSTOM HEX COLOR:", id="custom-hex-label")
                yield Input(value=self.custom_hex, placeholder="#00f0ff or #ff007f", id="input-custom-hex")
                yield Button("APPLY HEX", variant="primary", id="btn-apply-custom-hex")
            with VerticalScroll(id="palette-scroll-container"):
                for pal_id, pal_meta in ANIME_PALETTES.items():
                    with Horizontal(classes="pal-card-row"):
                        icon = pal_meta.get("icon", "◈")
                        name = pal_meta.get("name", pal_id)
                        stops = pal_meta.get("stops", [("#ffffff", 0.0), ("#000000", 1.0)])  # type: ignore
                        c1, c2, c3 = stops[0][0], stops[len(stops)//2][0], stops[-1][0]
                        yield Label(f"{icon} {name}", classes="pal-card-name")
                        yield Label(f"[{c1}]████[/][{c2}]████[/][{c3}]████[/]", classes="pal-card-swatch")
                        is_active = (pal_id == self.active_palette)
                        yield Button(
                            "ACTIVE" if is_active else "APPLY",
                            variant="success" if is_active else "default",
                            id=f"btn-apply-pal-{pal_id}",
                            classes="pal-card-btn",
                        )
            with Horizontal(id="palette-modal-footer"):
                yield Button("CLOSE", variant="default", id="btn-palette-modal-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-palette-modal-close":
            self.dismiss(None)
        elif btn_id == "btn-apply-custom-hex":
            hex_val = self.query_one("#input-custom-hex", Input).value.strip()
            if hex_val:
                if not hex_val.startswith("#"):
                    hex_val = f"#{hex_val}"
                self.dismiss(("custom", hex_val))
            else:
                self.dismiss(None)
        elif btn_id.startswith("btn-apply-pal-"):
            pal_id = btn_id[len("btn-apply-pal-"):]
            self.dismiss((pal_id, None))


class AnimeCompanionWidget(Vertical):
    """Side panel displaying the theme-dressed Braille anime companion, real-time 60 FPS animation & palette controls."""

    DEFAULT_CSS = """
    AnimeCompanionWidget {
        width: 38;
        min-width: 32;
        max-width: 44;
        height: 100%;
        background: #0f141c;
        border-left: heavy #00ffcc;
        padding: 0 1;
        layout: vertical;
    }
    #anime-char-header {
        height: 3;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: #00ffcc;
        border-bottom: solid #00ffcc;
    }
    #anime-char-controls {
        height: 3;
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
        align: center middle;
    }
    .char-ctrl-btn {
        min-width: 5;
        max-width: 10;
        height: 3;
        margin: 0 0;
        padding: 0 1;
    }
    #anime-char-art-scroll {
        width: 100%;
        height: 1fr;
    }
    #anime-char-art {
        width: 100%;
        content-align: center top;
        color: #e6edf3;
    }
    #anime-char-footer {
        height: 5;
        min-height: 5;
        width: 100%;
        border-top: solid #00ffcc;
        padding-top: 1;
        layout: vertical;
    }
    #anime-char-title {
        color: #00ffcc;
        text-style: bold;
    }
    #anime-char-desc {
        color: #8b949e;
    }
    #anime-char-meta {
        color: #58a6ff;
        text-style: italic;
    }
    """

    def __init__(
        self,
        character: Optional[AnimeCharacter] = None,
        palette_id: str = "cyberpunk_neon",
        custom_hex: Optional[str] = None,
        fx_mode: str = "scanline_shimmer",
        id: Optional[str] = None,
    ):
        super().__init__(id=id)
        self.character = character or get_anime_character("preset_y2k_aesthetic")
        self.palette_id = palette_id
        self.custom_hex = custom_hex
        self.fx_mode = fx_mode
        self.tick = 0
        self.audio_ctx: Optional[AudioFeatureContext] = None
        self._anim_timer = None

    def compose(self) -> ComposeResult:
        yield Label(f"👤 {self.character.name}", id="anime-char-header")
        with Horizontal(id="anime-char-controls"):
            yield Button("◀", id="btn-char-prev", classes="char-ctrl-btn")
            yield Button("⌸ CHAR", id="btn-char-select", classes="char-ctrl-btn")
            yield Button("◧ COLOR", id="btn-char-color", classes="char-ctrl-btn")
            yield Button("⚡ FX", id="btn-char-fx", classes="char-ctrl-btn")
            yield Button("▶", id="btn-char-next", classes="char-ctrl-btn")
        with VerticalScroll(id="anime-char-art-scroll"):
            yield Static(id="anime-char-art")
        with Vertical(id="anime-char-footer"):
            yield Label(self.character.title, id="anime-char-title")
            yield Label(self.character.outfit_desc[:60].replace("\n", " "), id="anime-char-desc")
            yield Label(f"PAL: {self._display_pal_name()} • FX: {self.fx_mode.upper()}", id="anime-char-meta")

    def on_mount(self) -> None:
        self._anim_timer = self._frame_timer = self._frame_timer = self.set_interval(1.0 / 60.0, self._tick_60fps)

    def _display_pal_name(self) -> str:
        if self.palette_id == "custom" and self.custom_hex:
            return self.custom_hex.upper()
        return self.palette_id.upper()

    def feed_audio(self, ctx: AudioFeatureContext) -> None:
        self.audio_ctx = ctx

    def _tick_60fps(self) -> None:
        self.tick += 1
        frame = render_animated_anime_frame(
            character=self.character,
            palette_id=self.palette_id,
            custom_hex=self.custom_hex,
            fx_mode=self.fx_mode,
            tick=self.tick,
            ctx=self.audio_ctx,
            max_lines=28,
            max_cols=36,
        )
        try:
            art_widget = self.query_one("#anime-char-art", Static)
            art_widget.update(frame)
        except Exception:
            pass

    def _cycle_character(self, delta: int) -> None:
        chars = list_all_anime_characters()
        curr_idx = 0
        for i, c in enumerate(chars):
            if c.char_id == self.character.char_id or c.name == self.character.name:
                curr_idx = i
                break
        next_idx = (curr_idx + delta) % len(chars)
        self.update_character(chars[next_idx])

    def _cycle_fx(self) -> None:
        fx_keys = list(ANIME_FX_MODES.keys())
        idx = fx_keys.index(self.fx_mode) if self.fx_mode in fx_keys else 0
        self.fx_mode = fx_keys[(idx + 1) % len(fx_keys)]
        self._update_meta_label()

    def _update_meta_label(self) -> None:
        try:
            meta = self.query_one("#anime-char-meta", Label)
            meta.update(f"PAL: {self._display_pal_name()} • FX: {self.fx_mode.upper()}")
        except Exception:
            pass

    def update_character(self, character: AnimeCharacter, theme: Optional[StitchTheme] = None) -> None:
        self.character = character
        try:
            hdr = self.query_one("#anime-char-header", Label)
            hdr.update(f"👤 {character.name}")
            ttl = self.query_one("#anime-char-title", Label)
            ttl.update(character.title)
            desc = self.query_one("#anime-char-desc", Label)
            desc.update(character.outfit_desc[:60].replace("\n", " "))
            self._update_meta_label()
            if theme:
                border_type = theme.border_style if theme.border_style in ("heavy", "double", "round", "ascii", "tall", "solid", "dashed") else "heavy"
                self.styles.background = theme.surface_color
                self.styles.border_left = (border_type, theme.primary_color)
                hdr.styles.color = theme.primary_color
                hdr.styles.border_bottom = ("solid", theme.primary_color)
                ttl.styles.color = theme.primary_color
                desc.styles.color = theme.secondary_color
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-char-prev":
            self._cycle_character(-1)
        elif btn_id == "btn-char-next":
            self._cycle_character(1)
        elif btn_id == "btn-char-fx":
            self._cycle_fx()
        elif btn_id == "btn-char-select":
            self.app.push_screen(AnimeCharacterSelectModal(), self._on_character_selected)
        elif btn_id == "btn-char-color":
            self.app.push_screen(AnimePaletteSelectModal(active_palette=self.palette_id, custom_hex=self.custom_hex), self._on_palette_selected)

    def _on_character_selected(self, character: Optional[AnimeCharacter]) -> None:
        if character:
            self.update_character(character)

    def _on_palette_selected(self, result: Optional[Tuple[str, Optional[str]]]) -> None:
        if result:
            pal_id, custom_hex = result
            self.palette_id = pal_id
            self.custom_hex = custom_hex
            self._update_meta_label()


class FullVisionStudioWidget(Container):
    """Main studio widget comprising the visual canvas, top toolbar, and bottom player dock."""

    DEFAULT_CSS = """
    FullVisionStudioWidget {
        width: 100%;
        height: 100%;
        layout: vertical;
        background: #0a0e14;
    }
    #fvs-top-bar {
        width: 100%;
        height: 3;
        background: #121820;
        border-bottom: heavy #00ffcc;
        align: left middle;
        padding: 0 1;
    }
    #fvs-brand {
        color: #00ffcc;
        text-style: bold;
        width: 24;
        content-align: left middle;
    }
    .fvs-top-btn {
        margin: 0 1;
        height: 3;
        min-height: 3;
    }
    #fvs-canvas-container {
        width: 100%;
        height: 1fr;
        padding: 0;
        margin: 0;
        layout: horizontal;
    }
    #fvs-dashboard {
        width: 1fr;
        height: 100%;
    }
    #fvs-bottom-dock {
        width: 100%;
        height: 7;
        min-height: 7;
        background: #10141d;
        border-top: heavy #ff007f;
        layout: horizontal;
        padding: 0 1;
    }
    #fvs-track-info-col {
        width: 32;
        height: 100%;
        layout: vertical;
        padding-top: 1;
    }
    #fvs-now-playing-title {
        color: #00ffcc;
        text-style: bold;
    }
    #fvs-now-playing-meta {
        color: #8b949e;
    }
    #fvs-player-center-col {
        width: 1fr;
        height: 100%;
        layout: vertical;
        align: center middle;
    }
    #fvs-transport-row {
        height: 3;
        align: center middle;
    }
    .transport-btn {
        margin: 0 1;
        min-width: 8;
        height: 3;
        min-height: 3;
    }
    #fvs-scrubber-row {
        width: 100%;
        height: 2;
        align: center middle;
        layout: horizontal;
    }
    #fvs-time-elapsed {
        width: 8;
        color: #00ffcc;
        text-align: right;
    }
    #fvs-scrubber {
        width: 1fr;
        margin: 0 1;
    }
    #fvs-time-total {
        width: 8;
        color: #8b949e;
        text-align: left;
    }
    #fvs-player-right-col {
        width: 32;
        height: 100%;
        layout: vertical;
        align: right middle;
    }
    .playlist-btn {
        margin: 0 1;
        height: 3;
        min-height: 3;
    }
    """

    def __init__(self, layout_store=None):
        super().__init__()
        self.stitch_client = StitchClient()
        self.layout_store = layout_store or VisionLayoutStore()
        self.player = VisionAudioPlayer()
        self.current_layout: Optional[VisionLayout] = None
        self.current_design = None
        self.current_theme: StitchTheme = self.stitch_client.get_theme("neon_cyber")
        self.active_gap: int = 1

    def compose(self) -> ComposeResult:
        # 1. Top Control Bar
        with Horizontal(id="fvs-top-bar"):
            yield Label("⛶ FULL VISION STUDIO", id="fvs-page-title")
            yield Label("SYSTEM NOMINAL", id="fvs-theme-subtitle")
            yield Button("1: OMNIRIP", variant="warning", id="btn-fvs-omnirip", classes="fvs-top-btn")
            yield Button("✨ PRESETS (20)", variant="primary", id="btn-fvs-presets", classes="fvs-top-btn")
            yield Button("📐 LOAD LAYOUT", id="btn-fvs-load-layout", classes="fvs-top-btn")
            yield Button("💾 SAVE LAYOUT", id="btn-fvs-save-layout", classes="fvs-top-btn")
            yield Button("GAP: (1)", id="btn-fvs-gap", classes="fvs-top-btn")
            yield Button("↗ NEW TAB", id="btn-fvs-popout", classes="fvs-top-btn")

        # 2. Main Visual Canvas & Anime Companion Side Panel
        with Horizontal(id="fvs-canvas-container"):
            yield VisualDashboardWidget(id="fvs-dashboard")
            yield AnimeCompanionWidget(id="fvs-anime-companion")

        # 3. Bottom Music Player Dock
        with Horizontal(id="fvs-bottom-dock"):
            # Left: Track Metadata
            with Vertical(id="fvs-track-info-col"):
                yield Label("🎵 Standby Synthesizer", id="fvs-now-playing-title")
                yield Label("60 FPS Telemetry | Real-Time Sync", id="fvs-now-playing-meta")

            # Center: Transport Controls & Scrubber
            with Vertical(id="fvs-player-center-col"):
                with Horizontal(id="fvs-transport-row"):
                    yield Button("⏮ PREV", id="btn-fvs-prev", classes="transport-btn")
                    yield Button("▶ PLAY", variant="primary", id="btn-fvs-play", classes="transport-btn")
                    yield Button("⏹ STOP", id="btn-fvs-stop", classes="transport-btn")
                    yield Button("⏭ NEXT", id="btn-fvs-next", classes="transport-btn")
                    yield Button("🔁 LOOP: OFF", id="btn-fvs-loop", classes="transport-btn")
                    yield Button("🔀 SHUFFLE: OFF", id="btn-fvs-shuffle", classes="transport-btn")

                with Horizontal(id="fvs-scrubber-row"):
                    yield Label("00:00", id="fvs-time-elapsed")
                    yield ProgressBar(id="fvs-scrubber", show_eta=False, show_percentage=False)
                    yield Label("00:00", id="fvs-time-total")

            # Right: Audio Actions
            with Vertical(id="fvs-player-right-col"):
                with Horizontal():
                    yield Button("+ LOAD SONG", variant="success", id="btn-fvs-add-song", classes="playlist-btn")
                    yield Button("QUEUE (0)", id="btn-fvs-queue", classes="playlist-btn")

    def on_mount(self) -> None:
        """Initialize 60 FPS animation loop, default layout, and player listener."""
        self.player.add_listener(self._on_track_changed)
        # Apply default layout
        layouts = self.layout_store.list_layouts()
        if layouts:
            self.apply_layout(layouts[0])

        try:
            companion = self.query_one("#fvs-anime-companion")
            companion.clock_managed_externally = True
        except Exception:
            pass

        try:
            companion = self.query_one("#fvs-anime-companion")
            companion.clock_managed_externally = True
        except Exception:
            pass

        # 60 FPS Timer
        self._frame_timer = self._frame_timer = self.set_interval(1.0 / 60.0, self._tick_60fps)

    def apply_layout(self, layout: VisionLayout) -> None:
        """Apply a full visual layout and transform the entire TUI design."""
        from harvester.ui.visuals.base import ColorPalette
        
        self.current_layout = layout
        self.active_gap = layout.gap_distance
        self.current_theme = self.stitch_client.get_theme(layout.stitch_theme_id)

        design = get_full_vision_design(layout.layout_id)
        self.current_design = design or get_full_vision_design("preset_matrix_terminal")

        try:
            gap_btn = self.query_one("#btn-fvs-gap", Button)
            gap_btn.label = f"GAP: ({self.active_gap})"
        except Exception:
            pass

        theme = self.current_theme
        border_type = theme.border_style if theme.border_style in ("heavy", "double", "round", "ascii", "tall", "solid", "dashed") else "heavy"

        try:
            self.styles.background = theme.background_color
        except Exception:
            pass

        try:
            top_bar = self.query_one("#fvs-top-bar")
            top_bar.styles.background = theme.surface_color
            top_bar.styles.border_bottom = (border_type, theme.primary_color)
            brand = self.query_one("#fvs-page-title", Label)
            brand.styles.color = theme.primary_color
            brand.update(self.current_design.page_title)
            
            sub = self.query_one("#fvs-theme-subtitle", Label)
            sub.update(self.current_design.subtitle)
            
            self.query_one("#btn-fvs-omnirip", Button).label = self.current_design.top_controls[0]
            self.query_one("#btn-fvs-presets", Button).label = self.current_design.top_controls[1]
            self.query_one("#anime-char-header", Label).update(self.current_design.companion_heading)
        except Exception:
            pass

        try:
            dock = self.query_one("#fvs-bottom-dock")
            dock.styles.background = theme.surface_color
            dock.styles.border_top = (border_type, theme.secondary_color)
            title_lbl = self.query_one("#fvs-now-playing-title", Label)
            title_lbl.styles.color = theme.primary_color
            elapsed_lbl = self.query_one("#fvs-time-elapsed", Label)
            elapsed_lbl.styles.color = theme.primary_color
        except Exception:
            pass

        dash = self.query_one("#fvs-dashboard", VisualDashboardWidget)
        dash.gap_size = self.active_gap
        dash.clock_managed_externally = True
        dash.is_editable = not layout.is_builtin
        dash.layout_style = self.current_design.dashboard_layout
        
        custom_palette = ColorPalette(
            id="theme_bound", 
            name="Theme", 
            primary=theme.gradient_stops[0] if theme.gradient_stops else theme.primary_color, 
            secondary=theme.gradient_stops[1] if len(theme.gradient_stops) > 1 else theme.secondary_color, 
            accent=theme.accent_color, 
            background=theme.background_color, 
            dim=theme.surface_color
        )
        
        dash_cards = []
        for idx, card_conf in enumerate(layout.cards):
            dash_cards.append({
                "card_id": f"card-{idx}",
                "engine_id": card_conf.engine_id,
                "palette": card_conf.palette,
                "palette_override": custom_palette if layout.is_builtin else None,
                "span": "full" if card_conf.span_two else "normal",
                "tall": card_conf.tall_two,
            })
        dash.cards = dash_cards
        dash._refresh_canvas()

        # 6. Transform Anime Companion Character & Lore
        try:
            char_id = layout.anime_character_id or layout.layout_id
            character = get_anime_character(char_id)
            companion = self.query_one("#fvs-anime-companion", AnimeCompanionWidget)
            companion.update_character(character, theme)
        except Exception:
            pass

        # 7. Transform Full TUI Button Labels and Layout Structure
        self._apply_button_and_layout_structure(layout, theme)
        
        # 8. ENFORCE DESIGN OVERRIDES
        try:
            self.query_one("#btn-fvs-omnirip", Button).label = self.current_design.top_controls[0]
            self.query_one("#btn-fvs-presets", Button).label = self.current_design.top_controls[1]
            self.query_one("#anime-char-header", Label).update(self.current_design.companion_heading)
            
            # Fix duplicate timer bug
            if getattr(dash, "_anim_timer", None):
                dash._anim_timer.stop()
                dash._anim_timer = None
                
            companion = self.query_one("#fvs-anime-companion")
            if getattr(companion, "_anim_timer", None):
                companion._anim_timer.stop()
                companion._anim_timer = None
                
            if not layout.is_builtin:
                self.current_design.dashboard_layout = "five_by_two"

        except Exception:
            pass


    def _apply_button_and_layout_structure(self, layout: VisionLayout, theme: StitchTheme) -> None:
        """Completely overhaul button styling, labeling, placements, and structural heights."""
        mode = getattr(layout, "button_style_mode", "pill")
        structure = getattr(layout, "ui_structure_style", "hyprland_floating")

        # Map button labels based on mode
        style_maps = {
            "dos_keys": {
                "#btn-fvs-omnirip": "[F1:OMNIRIP]",
                "#btn-fvs-presets": "[F2:PRESETS]",
                "#btn-fvs-load-layout": "[F3:LOAD]",
                "#btn-fvs-save-layout": "[F4:SAVE]",
                "#btn-fvs-gap": f"[F5:GAP:{self.active_gap}]",
                "#btn-fvs-popout": "[F6:TAB]",
                "#btn-fvs-prev": "[F7:PREV]",
                "#btn-fvs-play": "[F8:PLAY]",
                "#btn-fvs-stop": "[F9:STOP]",
                "#btn-fvs-next": "[F10:NEXT]",
                "#btn-fvs-loop": f"[F11:LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[F12:SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[+LOAD SONG]",
                "#btn-fvs-queue": f"[QUEUE:{len(self.player.playlist)}]",
            },
            "cyber_brackets": {
                "#btn-fvs-omnirip": "[// OMNIRIP //]",
                "#btn-fvs-presets": "[// PRESETS:20 //]",
                "#btn-fvs-load-layout": "[// IMPORT //]",
                "#btn-fvs-save-layout": "[// EXPORT //]",
                "#btn-fvs-gap": f"[// GAP:{self.active_gap} //]",
                "#btn-fvs-popout": "[// SHELL //]",
                "#btn-fvs-prev": "[<< SCAN]",
                "#btn-fvs-play": "[>> EXEC]",
                "#btn-fvs-stop": "[## HALT]",
                "#btn-fvs-next": "[>> SEEK]",
                "#btn-fvs-loop": f"[↺ LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[∿ SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[++ AUDIO_SRC]",
                "#btn-fvs-queue": f"[Q_BUFF:{len(self.player.playlist)}]",
            },
            "retro_arcade": {
                "#btn-fvs-omnirip": "[🪙 1P/OMNI]",
                "#btn-fvs-presets": "[🕹️ PRESETS]",
                "#btn-fvs-load-layout": "[📂 LOAD]",
                "#btn-fvs-save-layout": "[💾 SAVE]",
                "#btn-fvs-gap": f"[● GAP:{self.active_gap}]",
                "#btn-fvs-popout": "[↗ NEW]",
                "#btn-fvs-prev": "[◀ REV]",
                "#btn-fvs-play": "[★ START]",
                "#btn-fvs-stop": "[■ OVER]",
                "#btn-fvs-next": "[▶ FWD]",
                "#btn-fvs-loop": f"[🔄 RPT:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[🎲 RND:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[INSERT COIN]",
                "#btn-fvs-queue": f"[STAGE:{len(self.player.playlist)}]",
            },
            "cozy_soft": {
                "#btn-fvs-omnirip": "☕ omnirip",
                "#btn-fvs-presets": "✿ presets",
                "#btn-fvs-load-layout": "♡ load",
                "#btn-fvs-save-layout": "☁ save",
                "#btn-fvs-gap": f"⋆ gap ({self.active_gap})",
                "#btn-fvs-popout": "↗ tab",
                "#btn-fvs-prev": "⏮ softly",
                "#btn-fvs-play": "▶ listen",
                "#btn-fvs-stop": "⏹ rest",
                "#btn-fvs-next": "⏭ skip",
                "#btn-fvs-loop": f"↻ loop: {self.player.loop_mode.value}",
                "#btn-fvs-shuffle": f"~ shuffle: {'on' if self.player.shuffle else 'off'}",
                "#btn-fvs-add-song": "♪ add track",
                "#btn-fvs-queue": f"tea queue ({len(self.player.playlist)})",
            },
            "tactile_knobs": {
                "#btn-fvs-omnirip": "[CH-1: OMNI]",
                "#btn-fvs-presets": "[BNK: PRESETS]",
                "#btn-fvs-load-layout": "[INP: LOAD]",
                "#btn-fvs-save-layout": "[ROM: SAVE]",
                "#btn-fvs-gap": f"[ATT: GAP-{self.active_gap}]",
                "#btn-fvs-popout": "[AUX: TAB]",
                "#btn-fvs-prev": "|<< REWIND",
                "#btn-fvs-play": "> PLAY",
                "#btn-fvs-stop": "[] STOP",
                "#btn-fvs-next": ">>| FAST-FWD",
                "#btn-fvs-loop": f"(RPT: {self.player.loop_mode.value[:3]})",
                "#btn-fvs-shuffle": f"(RND: {'ON' if self.player.shuffle_mode else 'OFF'})",
                "#btn-fvs-add-song": "[REC INP]",
                "#btn-fvs-queue": f"[TRK-Q: {len(self.player.playlist)}]",
            },
            "hud_caps": {
                "#btn-fvs-omnirip": "1//OMNI",
                "#btn-fvs-presets": "2//PRESETS",
                "#btn-fvs-load-layout": "3//LOAD",
                "#btn-fvs-save-layout": "4//SAVE",
                "#btn-fvs-gap": f"5//GAP:{self.active_gap}",
                "#btn-fvs-popout": "6//POPOUT",
                "#btn-fvs-prev": "◄◄ REV",
                "#btn-fvs-play": "► IGNITION",
                "#btn-fvs-stop": "■ BRAKE",
                "#btn-fvs-next": "►► FWD",
                "#btn-fvs-loop": f"↺ LAP:{self.player.loop_mode.value[:3]}",
                "#btn-fvs-shuffle": f"⇄ DRIFT:{'ON' if self.player.shuffle_mode else 'OFF'}",
                "#btn-fvs-add-song": "+ TELEMETRY",
                "#btn-fvs-queue": f"GRID:[{len(self.player.playlist)}]",
            },
            "bracket_caps": {
                "#btn-fvs-omnirip": "【OMNIRIP】",
                "#btn-fvs-presets": "【PRESETS】",
                "#btn-fvs-load-layout": "【LOAD】",
                "#btn-fvs-save-layout": "【SAVE】",
                "#btn-fvs-gap": f"【GAP:{self.active_gap}】",
                "#btn-fvs-popout": "【TAB】",
                "#btn-fvs-prev": "【⏮ PREV】",
                "#btn-fvs-play": "【▶ PLAY】",
                "#btn-fvs-stop": "【⏹ STOP】",
                "#btn-fvs-next": "【⏭ NEXT】",
                "#btn-fvs-loop": f"【🔁 {self.player.loop_mode.value[:3]}】",
                "#btn-fvs-shuffle": f"【🔀 {'ON' if self.player.shuffle_mode else 'OFF'}】",
                "#btn-fvs-add-song": "【+ SONG】",
                "#btn-fvs-queue": f"【Q:{len(self.player.playlist)}】",
            },
            "pill": {
                "#btn-fvs-omnirip": "( 1: OMNIRIP )",
                "#btn-fvs-presets": "( ✨ PRESETS )",
                "#btn-fvs-load-layout": "( 📐 LOAD )",
                "#btn-fvs-save-layout": "( 💾 SAVE )",
                "#btn-fvs-gap": f"( ⚬ GAP: {self.active_gap} )",
                "#btn-fvs-popout": "( ↗ TAB )",
                "#btn-fvs-prev": "◀ PREV",
                "#btn-fvs-play": "▶ PLAY",
                "#btn-fvs-stop": "■ STOP",
                "#btn-fvs-next": "▶▶ NEXT",
                "#btn-fvs-loop": f"🔁 {self.player.loop_mode.value}",
                "#btn-fvs-shuffle": f"🔀 {'ON' if self.player.shuffle else 'OFF'}",
                "#btn-fvs-add-song": "+ LOAD SONG",
                "#btn-fvs-queue": f"QUEUE ({len(self.player.playlist)})",
            },
        }

        labels = style_maps.get(mode, style_maps["pill"])
        for btn_id, label_text in labels.items():
            try:
                b = self.query_one(btn_id, Button)
                b.label = escape(label_text)
            except Exception:
                pass

        # Structural layout sizing adjustments per style
        try:
            dock = self.query_one("#fvs-bottom-dock")
            top_bar = self.query_one("#fvs-top-bar")
            if structure in ("dos_mpxplay", "rackmount_hardware"):
                top_bar.styles.height = 3
                dock.styles.height = 6
            elif structure in ("hyprland_floating", "rmpc_split"):
                top_bar.styles.height = 3
                dock.styles.height = 7
            else:
                top_bar.styles.height = 3
                dock.styles.height = 7
        except Exception:
            pass

        # 6. Transform Anime Companion Character & Lore
        try:
            char_id = layout.anime_character_id or layout.layout_id
            character = get_anime_character(char_id)
            companion = self.query_one("#fvs-anime-companion", AnimeCompanionWidget)
            companion.update_character(character, theme)
        except Exception:
            pass

        # 7. Transform Full TUI Button Labels and Layout Structure
        self._apply_button_and_layout_structure(layout, theme)
        
        # 8. ENFORCE DESIGN OVERRIDES
        try:
            self.query_one("#btn-fvs-omnirip", Button).label = self.current_design.top_controls[0]
            self.query_one("#btn-fvs-presets", Button).label = self.current_design.top_controls[1]
            self.query_one("#anime-char-header", Label).update(self.current_design.companion_heading)
            
            # Fix duplicate timer bug
            if getattr(dash, "_anim_timer", None):
                dash._anim_timer.stop()
                dash._anim_timer = None
                
            companion = self.query_one("#fvs-anime-companion")
            if getattr(companion, "_anim_timer", None):
                companion._anim_timer.stop()
                companion._anim_timer = None
                
            if not layout.is_builtin:
                self.current_design.dashboard_layout = "five_by_two"

        except Exception:
            pass

    def _apply_button_and_layout_structure(self, layout: VisionLayout, theme: StitchTheme) -> None:
        """Completely overhaul button styling, labeling, placements, and structural heights."""
        mode = getattr(layout, "button_style_mode", "pill")
        structure = getattr(layout, "ui_structure_style", "hyprland_floating")

        # Map button labels based on mode
        style_maps = {
            "dos_keys": {
                "#btn-fvs-omnirip": "[F1:OMNIRIP]",
                "#btn-fvs-presets": "[F2:PRESETS]",
                "#btn-fvs-load-layout": "[F3:LOAD]",
                "#btn-fvs-save-layout": "[F4:SAVE]",
                "#btn-fvs-gap": f"[F5:GAP:{self.active_gap}]",
                "#btn-fvs-popout": "[F6:TAB]",
                "#btn-fvs-prev": "[F7:PREV]",
                "#btn-fvs-play": "[F8:PLAY]",
                "#btn-fvs-stop": "[F9:STOP]",
                "#btn-fvs-next": "[F10:NEXT]",
                "#btn-fvs-loop": f"[F11:LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[F12:SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[+LOAD SONG]",
                "#btn-fvs-queue": f"[QUEUE:{len(self.player.playlist)}]",
            },
            "cyber_brackets": {
                "#btn-fvs-omnirip": "[// OMNIRIP //]",
                "#btn-fvs-presets": "[// PRESETS:20 //]",
                "#btn-fvs-load-layout": "[// IMPORT //]",
                "#btn-fvs-save-layout": "[// EXPORT //]",
                "#btn-fvs-gap": f"[// GAP:{self.active_gap} //]",
                "#btn-fvs-popout": "[// SHELL //]",
                "#btn-fvs-prev": "[<< SCAN]",
                "#btn-fvs-play": "[>> EXEC]",
                "#btn-fvs-stop": "[## HALT]",
                "#btn-fvs-next": "[>> SEEK]",
                "#btn-fvs-loop": f"[↺ LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[∿ SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[++ AUDIO_SRC]",
                "#btn-fvs-queue": f"[Q_BUFF:{len(self.player.playlist)}]",
            },
            "retro_arcade": {
                "#btn-fvs-omnirip": "[🪙 1P/OMNI]",
                "#btn-fvs-presets": "[🕹️ PRESETS]",
                "#btn-fvs-load-layout": "[📂 LOAD]",
                "#btn-fvs-save-layout": "[💾 SAVE]",
                "#btn-fvs-gap": f"[● GAP:{self.active_gap}]",
                "#btn-fvs-popout": "[↗ NEW]",
                "#btn-fvs-prev": "[◀ REV]",
                "#btn-fvs-play": "[★ START]",
                "#btn-fvs-stop": "[■ OVER]",
                "#btn-fvs-next": "[▶ FWD]",
                "#btn-fvs-loop": f"[🔄 RPT:{self.player.loop_mode.value[:3]}]",
                "#btn-fvs-shuffle": f"[🎲 RND:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-fvs-add-song": "[INSERT COIN]",
                "#btn-fvs-queue": f"[STAGE:{len(self.player.playlist)}]",
            },
            "cozy_soft": {
                "#btn-fvs-omnirip": "☕ omnirip",
                "#btn-fvs-presets": "✿ presets",
                "#btn-fvs-load-layout": "♡ load",
                "#btn-fvs-save-layout": "☁ save",
                "#btn-fvs-gap": f"⋆ gap ({self.active_gap})",
                "#btn-fvs-popout": "↗ tab",
                "#btn-fvs-prev": "⏮ softly",
                "#btn-fvs-play": "▶ listen",
                "#btn-fvs-stop": "⏹ rest",
                "#btn-fvs-next": "⏭ skip",
                "#btn-fvs-loop": f"↻ loop: {self.player.loop_mode.value}",
                "#btn-fvs-shuffle": f"~ shuffle: {'on' if self.player.shuffle else 'off'}",
                "#btn-fvs-add-song": "♪ add track",
                "#btn-fvs-queue": f"tea queue ({len(self.player.playlist)})",
            },
            "tactile_knobs": {
                "#btn-fvs-omnirip": "[CH-1: OMNI]",
                "#btn-fvs-presets": "[BNK: PRESETS]",
                "#btn-fvs-load-layout": "[INP: LOAD]",
                "#btn-fvs-save-layout": "[ROM: SAVE]",
                "#btn-fvs-gap": f"[ATT: GAP-{self.active_gap}]",
                "#btn-fvs-popout": "[AUX: TAB]",
                "#btn-fvs-prev": "|<< REWIND",
                "#btn-fvs-play": "> PLAY",
                "#btn-fvs-stop": "[] STOP",
                "#btn-fvs-next": ">>| FAST-FWD",
                "#btn-fvs-loop": f"(RPT: {self.player.loop_mode.value[:3]})",
                "#btn-fvs-shuffle": f"(RND: {'ON' if self.player.shuffle_mode else 'OFF'})",
                "#btn-fvs-add-song": "[REC INP]",
                "#btn-fvs-queue": f"[TRK-Q: {len(self.player.playlist)}]",
            },
            "hud_caps": {
                "#btn-fvs-omnirip": "1//OMNI",
                "#btn-fvs-presets": "2//PRESETS",
                "#btn-fvs-load-layout": "3//LOAD",
                "#btn-fvs-save-layout": "4//SAVE",
                "#btn-fvs-gap": f"5//GAP:{self.active_gap}",
                "#btn-fvs-popout": "6//POPOUT",
                "#btn-fvs-prev": "◄◄ REV",
                "#btn-fvs-play": "► IGNITION",
                "#btn-fvs-stop": "■ BRAKE",
                "#btn-fvs-next": "►► FWD",
                "#btn-fvs-loop": f"↺ LAP:{self.player.loop_mode.value[:3]}",
                "#btn-fvs-shuffle": f"⇄ DRIFT:{'ON' if self.player.shuffle_mode else 'OFF'}",
                "#btn-fvs-add-song": "+ TELEMETRY",
                "#btn-fvs-queue": f"GRID:[{len(self.player.playlist)}]",
            },
            "bracket_caps": {
                "#btn-fvs-omnirip": "【OMNIRIP】",
                "#btn-fvs-presets": "【PRESETS】",
                "#btn-fvs-load-layout": "【LOAD】",
                "#btn-fvs-save-layout": "【SAVE】",
                "#btn-fvs-gap": f"【GAP:{self.active_gap}】",
                "#btn-fvs-popout": "【TAB】",
                "#btn-fvs-prev": "【⏮ PREV】",
                "#btn-fvs-play": "【▶ PLAY】",
                "#btn-fvs-stop": "【⏹ STOP】",
                "#btn-fvs-next": "【⏭ NEXT】",
                "#btn-fvs-loop": f"【🔁 {self.player.loop_mode.value[:3]}】",
                "#btn-fvs-shuffle": f"【🔀 {'ON' if self.player.shuffle_mode else 'OFF'}】",
                "#btn-fvs-add-song": "【+ SONG】",
                "#btn-fvs-queue": f"【Q:{len(self.player.playlist)}】",
            },
            "pill": {
                "#btn-fvs-omnirip": "( 1: OMNIRIP )",
                "#btn-fvs-presets": "( ✨ PRESETS )",
                "#btn-fvs-load-layout": "( 📐 LOAD )",
                "#btn-fvs-save-layout": "( 💾 SAVE )",
                "#btn-fvs-gap": f"( ⚬ GAP: {self.active_gap} )",
                "#btn-fvs-popout": "( ↗ TAB )",
                "#btn-fvs-prev": "◀ PREV",
                "#btn-fvs-play": "▶ PLAY",
                "#btn-fvs-stop": "■ STOP",
                "#btn-fvs-next": "▶▶ NEXT",
                "#btn-fvs-loop": f"🔁 {self.player.loop_mode.value}",
                "#btn-fvs-shuffle": f"🔀 {'ON' if self.player.shuffle else 'OFF'}",
                "#btn-fvs-add-song": "+ LOAD SONG",
                "#btn-fvs-queue": f"QUEUE ({len(self.player.playlist)})",
            },
        }

        labels = style_maps.get(mode, style_maps["pill"])
        for btn_id, label_text in labels.items():
            try:
                b = self.query_one(btn_id, Button)
                b.label = escape(label_text)
            except Exception:
                pass

        # Structural layout sizing adjustments per style
        try:
            dock = self.query_one("#fvs-bottom-dock")
            top_bar = self.query_one("#fvs-top-bar")
            if structure in ("dos_mpxplay", "rackmount_hardware"):
                top_bar.styles.height = 3
                dock.styles.height = 6
            elif structure in ("hyprland_floating", "rmpc_split"):
                top_bar.styles.height = 3
                dock.styles.height = 7
            else:
                top_bar.styles.height = 3
                dock.styles.height = 7
        except Exception:
            pass

    def _on_track_changed(self, track: PlaylistTrack) -> None:
        """Update track information in UI."""
        try:
            title_lbl = self.query_one("#fvs-now-playing-title", Label)
            meta_lbl = self.query_one("#fvs-now-playing-meta", Label)
            total_lbl = self.query_one("#fvs-time-total", Label)
            queue_btn = self.query_one("#btn-fvs-queue", Button)

            title_lbl.update(f"🎵 {track.title[:28]}")
            meta_lbl.update(f"{track.artist} | {track.sample_rate}Hz | 60 FPS")
            total_lbl.update(track.formatted_duration)
            queue_btn.label = f"QUEUE ({len(self.player.playlist)})"
        except Exception:
            pass

    def _tick_60fps(self) -> None:
        """60 FPS playback progress and audio feature synchronization tick."""
        # Update audio player position and fetch synchronized feature frame
        ctx = self.player.update_frame()

        # Update Scrubber & Elapsed Time
        if self.player.current_track:
            pos = self.player.current_position_seconds
            dur = self.player.current_track.duration_seconds
            try:
                scrubber = self.query_one("#fvs-scrubber", ProgressBar)
                elapsed_lbl = self.query_one("#fvs-time-elapsed", Label)
                if dur > 0:
                    scrubber.progress = (pos / dur) * 100.0
                elapsed_lbl.update(self.player.formatted_position)
            except Exception:
                pass

        # Update Play/Pause button label
        try:
            play_btn = self.query_one("#btn-fvs-play", Button)
            if self.player.state == PlaybackState.PLAYING:
                play_btn.label = "⏸ PAUSE"
                play_btn.variant = "warning"
            else:
                play_btn.label = "▶ PLAY"
                play_btn.variant = "primary"
        except Exception:
            pass

        # Feed feature frame to all active canvas cards and anime companion
        try:
            dash = self.query_one("#fvs-dashboard", VisualDashboardWidget)
            dash.tick_frame(ctx)
            companion = self.query_one("#fvs-anime-companion", AnimeCompanionWidget)
            companion.feed_audio(ctx)
            companion._tick_60fps()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-fvs-play":
            self.player.toggle_play_pause()
        elif btn_id == "btn-fvs-stop":
            self.player.stop()
        elif btn_id == "btn-fvs-next":
            self.player.next_track()
        elif btn_id == "btn-fvs-prev":
            self.player.prev_track()
        elif btn_id == "btn-fvs-loop":
            mode = self.player.toggle_loop()
            event.button.label = f"🔁 LOOP: {mode.value}"
        elif btn_id == "btn-fvs-shuffle":
            shuf = self.player.toggle_shuffle()
            event.button.label = f"🔀 SHUFFLE: {'ON' if shuf else 'OFF'}"
        elif btn_id == "btn-fvs-omnirip":
            self._return_to_omnirip()
        elif btn_id == "btn-fvs-presets":
            self.app.push_screen(PresetCatalogModal(self.layout_store), self._handle_preset_selected)
        elif btn_id == "btn-fvs-gap":
            self._cycle_gap()
        elif btn_id == "btn-fvs-add-song":
            self.app.push_screen(AddSongModal(), self._handle_add_song)
        elif btn_id == "btn-fvs-save-layout":
            self.app.push_screen(SaveLayoutModal(), self._handle_save_layout)
        elif btn_id == "btn-fvs-load-layout":
            self._cycle_layout()
        elif btn_id == "btn-fvs-popout":
            launch_full_vision_external()

    def _return_to_omnirip(self) -> None:
        """Return to the OmniRip main workstation view."""
        if hasattr(self.screen, "dismiss"):
            self.screen.dismiss()
        elif hasattr(self.app, "pop_screen"):
            try:
                self.app.pop_screen()
            except Exception:
                pass

    def _handle_preset_selected(self, layout: Optional[VisionLayout]) -> None:
        """Apply a full preset design including Stitch theme and visuals layout."""
        if layout:
            self.apply_layout(layout)

    def _cycle_gap(self) -> None:
        """Cycle gap distance: 0 -> 1 -> 2 -> 3 -> 4 -> 0."""
        self.active_gap = (self.active_gap + 1) % 5
        btn = self.query_one("#btn-fvs-gap", Button)
        btn.label = f"GAP: ({self.active_gap})"

        dash = self.query_one("#fvs-dashboard", VisualDashboardWidget)
        dash.gap_size = self.active_gap
        dash.clock_managed_externally = True
        dash.is_editable = not layout.is_builtin
        dash._refresh_canvas()

    def _cycle_layout(self) -> None:
        """Cycle through available layouts."""
        layouts = self.layout_store.list_layouts()
        if not layouts:
            return

        current_idx = 0
        if self.current_layout:
            for i, ly in enumerate(layouts):
                if ly.layout_id == self.current_layout.layout_id:
                    current_idx = i
                    break

        next_idx = (current_idx + 1) % len(layouts)
        self.apply_layout(layouts[next_idx])

    def _handle_add_song(self, path: Optional[Path]) -> None:
        if path and path.exists():
            track = self.player.load_track(path)
            if track:
                self.player.play()

    def _handle_save_layout(self, name: Optional[str]) -> None:
        if not name:
            return

        dash = self.query_one("#fvs-dashboard", VisualDashboardWidget)
        cards = []
        for idx, item in enumerate(dash.cards):
            cards.append(
                VisionCardConfig(
                    engine_id=item["engine_id"],
                    palette="theme",
                    span_two=(item.get("span") == "full"),
                    tall_two=bool(item.get("tall", False)),
                    order=idx,
                )
            )

        layout = VisionLayout(
            layout_id="",
            name=name,
            description="",
            stitch_theme_id=self.current_theme.theme_id,
            gap_distance=self.active_gap,
            cards=cards,
            is_builtin=False,
        )
        self.layout_store.save_layout(layout)
        self.apply_layout(layout)
        self.current_layout = layout


class FullVisionScreen(ModalScreen):
    """In-app fullscreen modal studio for Full Vision."""

    DEFAULT_CSS = """
    FullVisionScreen {
        width: 100%;
        height: 100%;
        background: #0a0e14;
    }
    """

    def compose(self) -> ComposeResult:
        yield FullVisionStudioWidget()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("1", "escape"):
            self.dismiss()


class FullVisionApp(App):
    """Standalone Textual application for Full Vision Studio."""

    CSS = """
    Screen {
        background: #0a0e14;
    }
    """

    def compose(self) -> ComposeResult:
        yield FullVisionStudioWidget()
        yield Footer()


def main():
    """Entry point for standalone `omnirip-vision` terminal execution."""
    app = FullVisionApp()
    app.run()


if __name__ == "__main__":
    main()
