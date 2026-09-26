"""PLAYER Studio: Terminal Music Player & Visual Design Canvas.

Integrates Google Stitch API design tokens, custom visualizer layouts (with
persistent save/load), 60 FPS audio feature synchronization, and a complete
cyberpunk music player dock. Can run as a standalone terminal app (spawned in a
new window via AppleScript) or an in-app fullscreen studio.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    ProgressBar,
    Static,
)

from harvester.services.stitch import StitchClient, StitchTheme
from harvester.services.vision_layout_store import (
    VisionCardConfig,
    VisionLayout,
    VisionLayoutStore,
)
from harvester.services.vision_player import (
    PlaybackState,
    PlaylistTrack,
    VisionAudioPlayer,
)
from harvester.ui.companion import CompanionSession
from harvester.ui.player_designs import PlayerPageDesign, get_player_design
from harvester.ui.player_layout import (
    ButtonState,
    MotionDriver,
    apply_button_frames,
    apply_page,
    resolve_page,
    theme_color_palette,
    theme_palette,
)
from harvester.ui.visual_dashboard import (
    VisualDashboardWidget,
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

logger = logging.getLogger(__name__)


def launch_player_external() -> bool:
    """Launch PLAYER Studio in a new external macOS Terminal or iTerm tab."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    venv_python = repo_root / ".venv" / "bin" / "python3"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    cmd_script = f"cd '{repo_root}' && '{python_bin}' -m harvester.ui.player_studio"

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
                logger.info("Successfully launched PLAYER in new macOS terminal window.")
                return True
            else:
                logger.warning("AppleScript launch returned %d: %s", res.returncode, res.stderr)
        except Exception as exc:
            logger.warning("Failed to invoke osascript: %s", exc)

    # Fallback: spawn background terminal process if tmux or standard terminal
    try:
        subprocess.Popen(
            [python_bin, "-m", "harvester.ui.player_studio"],
            cwd=str(repo_root),
            start_new_session=True,
        )
        return True
    except Exception as exc:
        logger.error("Failed to launch background PLAYER process: %s", exc)
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
            yield Label("💾  SAVE PLAYER CANVAS DESIGN", id="save-layout-title")
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
    #anime-char-motif {
        height: 1;
        width: 100%;
        display: none;
        color: #8b949e;
        text-align: center;
    }
    #anime-char-scene {
        height: 1;
        width: 100%;
        color: #58a6ff;
        text-align: center;
        overflow: hidden;
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
        height: 7;
        min-height: 7;
        width: 100%;
        border-top: solid #00ffcc;
        padding-top: 1;
        layout: vertical;
    }
    #anime-char-speech {
        height: 1;
        color: #e6edf3;
        text-style: italic;
    }
    #anime-char-status {
        height: 1;
        color: #58a6ff;
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
        clock_managed_externally: bool = False,
    ):
        super().__init__(id=id)
        self.character = character or get_anime_character("preset_y2k_aesthetic")
        self.palette_id = palette_id
        self.custom_hex = custom_hex
        self.fx_mode = fx_mode
        self.tick = 0
        self.audio_ctx: Optional[AudioFeatureContext] = None
        self.clock_managed_externally = clock_managed_externally
        self._anim_timer = None
        self.session = CompanionSession()

    def compose(self) -> ComposeResult:
        yield Label(f"👤 {self.character.name}", id="anime-char-header")
        yield Label("", id="anime-char-motif")
        yield Label("", id="anime-char-scene")
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
            yield Label("", id="anime-char-speech")
            yield Label("", id="anime-char-status")
            yield Label(f"PAL: {self._display_pal_name()} • FX: {self.fx_mode.upper()}", id="anime-char-meta")

    def on_mount(self) -> None:
        if not self.clock_managed_externally:
            self._anim_timer = self.set_interval(1.0 / 60.0, self._tick_60fps)

    def on_unmount(self) -> None:
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None

    def _display_pal_name(self) -> str:
        if self.palette_id == "custom" and self.custom_hex:
            return self.custom_hex.upper()
        return self.palette_id.upper()

    def set_motif(self, text: Optional[str]) -> None:
        """Show or hide the preset motif line inside the companion frame."""
        try:
            label = self.query_one("#anime-char-motif", Label)
        except Exception:
            return
        if text:
            label.update(text)
            label.styles.display = "block"
        else:
            label.styles.display = "none"

    def apply_palette(self, palette) -> None:
        """Recolor companion chrome from the shared PLAYER palette."""
        try:
            self.query_one("#anime-char-scene", Label).styles.color = palette.accent
            self.query_one("#anime-char-status", Label).styles.color = palette.accent
            self.query_one("#anime-char-speech", Label).styles.color = palette.foreground
            self.query_one("#anime-char-motif", Label).styles.color = palette.secondary
            self.query_one("#anime-char-meta", Label).styles.color = palette.secondary
        except Exception:
            pass

    def feed_audio(self, ctx: AudioFeatureContext) -> None:
        self.audio_ctx = ctx

    def notify_event(self, event: str) -> None:
        """Route a context event (track_change, pause, drop) to companion dialogue."""
        self.session.notify(event, self.tick)
        self._update_session_labels()

    def _update_session_labels(self) -> None:
        try:
            status = self.query_one("#anime-char-status", Label)
            status.update(self.session.status_line())
            scene = self.query_one("#anime-char-scene", Label)
            width = max(12, (self.size.width or 34) - 4)
            scene.update(self.session.scene_line(width, self.tick))
            speech = self.query_one("#anime-char-speech", Label)
            speech.update(self.session.speech)
        except Exception:
            pass

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

        ctx = self.audio_ctx or AudioFeatureContext.synthesize_idle(self.tick * 0.02)
        self.session.observe(ctx, self.tick)
        if self.tick % 6 == 0:
            self._update_session_labels()

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
        self.session.set_design(character.preset_id)
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


class PlayerStudioWidget(Container):
    """Main studio widget comprising the visual canvas, top toolbar, and bottom player dock."""

    DEFAULT_CSS = """
    PlayerStudioWidget {
        width: 100%;
        height: 100%;
        layout: vertical;
        background: #0a0e14;
    }
    #plr-top-bar {
        width: 100%;
        height: 3;
        background: #121820;
        border-bottom: heavy #00ffcc;
        align: left middle;
        padding: 0 1;
    }
    #plr-page-title {
        color: #00ffcc;
        text-style: bold;
        width: 24;
        content-align: left middle;
    }
    #plr-theme-subtitle {
        color: #8b949e;
        width: 1fr;
        content-align: left middle;
    }
    #plr-motif {
        width: auto;
        color: #8b949e;
        content-align: left middle;
        margin-right: 1;
    }
    #plr-dock-motif {
        width: auto;
        display: none;
        color: #8b949e;
        content-align: left middle;
        margin-right: 2;
    }
    .plr-top-btn {
        margin: 0 1;
        height: 3;
        min-height: 3;
    }
    #plr-canvas-container {
        width: 100%;
        height: 1fr;
        padding: 0;
        margin: 0;
        layout: horizontal;
    }
    #plr-dashboard {
        width: 1fr;
        height: 100%;
    }
    #plr-bottom-dock {
        width: 100%;
        height: 7;
        min-height: 7;
        background: #10141d;
        border-top: heavy #ff007f;
        layout: horizontal;
        padding: 0 1;
    }
    #plr-track-info-col {
        width: 32;
        height: 100%;
        layout: vertical;
        padding-top: 1;
    }
    #plr-now-playing-title {
        color: #00ffcc;
        text-style: bold;
    }
    #plr-now-playing-meta {
        color: #8b949e;
    }
    #plr-player-center-col {
        width: 1fr;
        height: 100%;
        layout: vertical;
        align: center middle;
    }
    #plr-transport-row {
        height: 3;
        align: center middle;
    }
    .transport-btn {
        margin: 0 1;
        min-width: 8;
        height: 3;
        min-height: 3;
    }
    #plr-scrubber-row {
        width: 100%;
        height: 2;
        align: center middle;
        layout: horizontal;
    }
    #plr-time-elapsed {
        width: 8;
        color: #00ffcc;
        text-align: right;
    }
    #plr-scrubber {
        width: 1fr;
        margin: 0 1;
    }
    #plr-time-total {
        width: 8;
        color: #8b949e;
        text-align: left;
    }
    #plr-player-right-col {
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
        self.current_design: Optional[PlayerPageDesign] = None
        self.current_theme: StitchTheme = self.stitch_client.get_theme("neon_cyber")
        self.active_gap: int = 1
        self.palette = theme_palette(self.current_theme)
        self._motion = MotionDriver()
        self._resolved_page = None
        self._last_button_state = None

    def compose(self) -> ComposeResult:
        # 1. Top Control Bar
        with Horizontal(id="plr-top-bar"):
            yield Label("⛶ PLAYER STUDIO", id="plr-page-title")
            yield Label("SYSTEM NOMINAL", id="plr-theme-subtitle")
            yield Label("", id="plr-motif")
            yield Button("1: OMNIRIP", variant="warning", id="btn-plr-omnirip", classes="plr-top-btn")
            yield Button("✨ PRESETS (20)", variant="primary", id="btn-plr-presets", classes="plr-top-btn")
            yield Button("📐 LOAD LAYOUT", id="btn-plr-load-layout", classes="plr-top-btn")
            yield Button("💾 SAVE LAYOUT", id="btn-plr-save-layout", classes="plr-top-btn")
            yield Button("GAP: (1)", id="btn-plr-gap", classes="plr-top-btn")
            yield Button("↗ NEW TAB", id="btn-plr-popout", classes="plr-top-btn")

        # 2. Main Visual Canvas; the companion is a root sibling so the page
        # orchestrator can dock it to any rail or footer per preset.
        with Horizontal(id="plr-canvas-container"):
            yield VisualDashboardWidget(id="plr-dashboard", clock_managed_externally=True)
        yield AnimeCompanionWidget(
            id="plr-anime-companion",
            clock_managed_externally=True,
        )

        # 3. Bottom Music Player Dock
        with Horizontal(id="plr-bottom-dock"):
            yield Label("", id="plr-dock-motif")
            # Left: Track Metadata
            with Vertical(id="plr-track-info-col"):
                yield Label("🎵 Standby Synthesizer", id="plr-now-playing-title")
                yield Label("60 FPS Telemetry | Real-Time Sync", id="plr-now-playing-meta")

            # Center: Transport Controls & Scrubber
            with Vertical(id="plr-player-center-col"):
                with Horizontal(id="plr-transport-row"):
                    yield Button("⏮ PREV", id="btn-plr-prev", classes="transport-btn")
                    yield Button("▶ PLAY", variant="primary", id="btn-plr-play", classes="transport-btn")
                    yield Button("⏹ STOP", id="btn-plr-stop", classes="transport-btn")
                    yield Button("⏭ NEXT", id="btn-plr-next", classes="transport-btn")
                    yield Button("🔁 LOOP: OFF", id="btn-plr-loop", classes="transport-btn")
                    yield Button("🔀 SHUFFLE: OFF", id="btn-plr-shuffle", classes="transport-btn")

                with Horizontal(id="plr-scrubber-row"):
                    yield Label("00:00", id="plr-time-elapsed")
                    yield ProgressBar(id="plr-scrubber", show_eta=False, show_percentage=False)
                    yield Label("00:00", id="plr-time-total")

            # Right: Audio Actions
            with Vertical(id="plr-player-right-col"):
                with Horizontal():
                    yield Button("+ LOAD SONG", variant="success", id="btn-plr-add-song", classes="playlist-btn")
                    yield Button("QUEUE (0)", id="btn-plr-queue", classes="playlist-btn")

    def on_mount(self) -> None:
        """Initialize 60 FPS animation loop, default layout, and player listener."""
        self.player.add_listener(self._on_track_changed)
        # Apply default layout
        layouts = self.layout_store.list_layouts()
        if layouts:
            self.apply_layout(layouts[0])

        self._frame_timer = self.set_interval(1.0 / 60.0, self._tick_60fps)

    def apply_layout(self, layout: VisionLayout) -> None:
        """Apply a full visual layout and transform the entire TUI design."""
        self.current_layout = layout
        self.active_gap = layout.gap_distance
        self.current_theme = self.stitch_client.get_theme(layout.stitch_theme_id)

        design = get_player_design(layout.layout_id)
        self.current_design = design or get_player_design("preset_matrix_terminal")

        try:
            gap_btn = self.query_one("#btn-plr-gap", Button)
            gap_btn.label = f"GAP: ({self.active_gap})"
        except Exception:
            pass

        theme = self.current_theme
        palette = theme_palette(theme)
        self.palette = palette
        border_type = theme.border_style if theme.border_style in ("heavy", "double", "round", "ascii", "tall", "solid", "dashed") else "heavy"

        try:
            self.styles.background = theme.background_color
        except Exception:
            pass

        try:
            top_bar = self.query_one("#plr-top-bar")
            top_bar.styles.background = theme.surface_color
            top_bar.styles.border_bottom = (border_type, theme.primary_color)
            brand = self.query_one("#plr-page-title", Label)
            brand.styles.color = theme.primary_color
            brand.update(self.current_design.page_title)

            sub = self.query_one("#plr-theme-subtitle", Label)
            sub.update(self.current_design.subtitle)
        except Exception:
            pass

        try:
            dock = self.query_one("#plr-bottom-dock")
            dock.styles.background = theme.surface_color
            dock.styles.border_top = (border_type, theme.secondary_color)
            title_lbl = self.query_one("#plr-now-playing-title", Label)
            title_lbl.styles.color = theme.primary_color
            elapsed_lbl = self.query_one("#plr-time-elapsed", Label)
            elapsed_lbl.styles.color = theme.primary_color
        except Exception:
            pass

        dash = self.query_one("#plr-dashboard", VisualDashboardWidget)
        dash.gap_size = self.active_gap
        dash.set_editable(not layout.is_builtin)
        dash.layout_style = self.current_design.dashboard_layout

        custom_palette = theme_color_palette(theme)

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
            companion = self.query_one("#plr-anime-companion", AnimeCompanionWidget)
            companion.update_character(character, theme)
        except Exception:
            pass

        # 7. Transform Full TUI Button Labels and Layout Structure
        self._apply_button_and_layout_structure(layout, theme)
        self._apply_design_control_labels()
        self.query_one("#anime-char-header", Label).update(self.current_design.companion_heading)

        # 8. Apply resolved page grammar: rail, panel slots, frames, motion.
        page = resolve_page(self.current_design, layout, theme=theme)
        self._resolved_page = page
        apply_page(self, page, theme)
        self._refresh_transport_labels(force=True)

        # 9. One palette source for chrome, companion, and scene.
        try:
            self.query_one("#plr-motif", Label).styles.color = palette.secondary
        except Exception:
            pass
        try:
            companion = self.query_one("#plr-anime-companion", AnimeCompanionWidget)
            companion.apply_palette(palette)
        except Exception:
            pass

    def _apply_button_and_layout_structure(self, layout: VisionLayout, theme: StitchTheme) -> None:
        """Completely overhaul button styling, labeling, placements, and structural heights."""
        mode = getattr(layout, "button_style_mode", "pill")
        structure = getattr(layout, "ui_structure_style", "hyprland_floating")

        # Map button labels based on mode
        style_maps = {
            "dos_keys": {
                "#btn-plr-omnirip": "[F1:OMNIRIP]",
                "#btn-plr-presets": "[F2:PRESETS]",
                "#btn-plr-load-layout": "[F3:LOAD]",
                "#btn-plr-save-layout": "[F4:SAVE]",
                "#btn-plr-gap": f"[F5:GAP:{self.active_gap}]",
                "#btn-plr-popout": "[F6:TAB]",
                "#btn-plr-prev": "[F7:PREV]",
                "#btn-plr-play": "[F8:PLAY]",
                "#btn-plr-stop": "[F9:STOP]",
                "#btn-plr-next": "[F10:NEXT]",
                "#btn-plr-loop": f"[F11:LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-plr-shuffle": f"[F12:SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-plr-add-song": "[+LOAD SONG]",
                "#btn-plr-queue": f"[QUEUE:{len(self.player.playlist)}]",
            },
            "cyber_brackets": {
                "#btn-plr-omnirip": "[// OMNIRIP //]",
                "#btn-plr-presets": "[// PRESETS:20 //]",
                "#btn-plr-load-layout": "[// IMPORT //]",
                "#btn-plr-save-layout": "[// EXPORT //]",
                "#btn-plr-gap": f"[// GAP:{self.active_gap} //]",
                "#btn-plr-popout": "[// SHELL //]",
                "#btn-plr-prev": "[<< SCAN]",
                "#btn-plr-play": "[>> EXEC]",
                "#btn-plr-stop": "[## HALT]",
                "#btn-plr-next": "[>> SEEK]",
                "#btn-plr-loop": f"[↺ LOOP:{self.player.loop_mode.value[:3]}]",
                "#btn-plr-shuffle": f"[∿ SHUF:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-plr-add-song": "[++ AUDIO_SRC]",
                "#btn-plr-queue": f"[Q_BUFF:{len(self.player.playlist)}]",
            },
            "retro_arcade": {
                "#btn-plr-omnirip": "[🪙 1P/OMNI]",
                "#btn-plr-presets": "[🕹️ PRESETS]",
                "#btn-plr-load-layout": "[📂 LOAD]",
                "#btn-plr-save-layout": "[💾 SAVE]",
                "#btn-plr-gap": f"[● GAP:{self.active_gap}]",
                "#btn-plr-popout": "[↗ NEW]",
                "#btn-plr-prev": "[◀ REV]",
                "#btn-plr-play": "[★ START]",
                "#btn-plr-stop": "[■ OVER]",
                "#btn-plr-next": "[▶ FWD]",
                "#btn-plr-loop": f"[🔄 RPT:{self.player.loop_mode.value[:3]}]",
                "#btn-plr-shuffle": f"[🎲 RND:{'ON' if self.player.shuffle_mode else 'OFF'}]",
                "#btn-plr-add-song": "[INSERT COIN]",
                "#btn-plr-queue": f"[STAGE:{len(self.player.playlist)}]",
            },
            "cozy_soft": {
                "#btn-plr-omnirip": "☕ omnirip",
                "#btn-plr-presets": "✿ presets",
                "#btn-plr-load-layout": "♡ load",
                "#btn-plr-save-layout": "☁ save",
                "#btn-plr-gap": f"⋆ gap ({self.active_gap})",
                "#btn-plr-popout": "↗ tab",
                "#btn-plr-prev": "⏮ softly",
                "#btn-plr-play": "▶ listen",
                "#btn-plr-stop": "⏹ rest",
                "#btn-plr-next": "⏭ skip",
                "#btn-plr-loop": f"↻ loop: {self.player.loop_mode.value}",
                "#btn-plr-shuffle": f"~ shuffle: {'on' if self.player.shuffle else 'off'}",
                "#btn-plr-add-song": "♪ add track",
                "#btn-plr-queue": f"tea queue ({len(self.player.playlist)})",
            },
            "tactile_knobs": {
                "#btn-plr-omnirip": "[CH-1: OMNI]",
                "#btn-plr-presets": "[BNK: PRESETS]",
                "#btn-plr-load-layout": "[INP: LOAD]",
                "#btn-plr-save-layout": "[ROM: SAVE]",
                "#btn-plr-gap": f"[ATT: GAP-{self.active_gap}]",
                "#btn-plr-popout": "[AUX: TAB]",
                "#btn-plr-prev": "|<< REWIND",
                "#btn-plr-play": "> PLAY",
                "#btn-plr-stop": "[] STOP",
                "#btn-plr-next": ">>| FAST-FWD",
                "#btn-plr-loop": f"(RPT: {self.player.loop_mode.value[:3]})",
                "#btn-plr-shuffle": f"(RND: {'ON' if self.player.shuffle_mode else 'OFF'})",
                "#btn-plr-add-song": "[REC INP]",
                "#btn-plr-queue": f"[TRK-Q: {len(self.player.playlist)}]",
            },
            "hud_caps": {
                "#btn-plr-omnirip": "1//OMNI",
                "#btn-plr-presets": "2//PRESETS",
                "#btn-plr-load-layout": "3//LOAD",
                "#btn-plr-save-layout": "4//SAVE",
                "#btn-plr-gap": f"5//GAP:{self.active_gap}",
                "#btn-plr-popout": "6//POPOUT",
                "#btn-plr-prev": "◄◄ REV",
                "#btn-plr-play": "► IGNITION",
                "#btn-plr-stop": "■ BRAKE",
                "#btn-plr-next": "►► FWD",
                "#btn-plr-loop": f"↺ LAP:{self.player.loop_mode.value[:3]}",
                "#btn-plr-shuffle": f"⇄ DRIFT:{'ON' if self.player.shuffle_mode else 'OFF'}",
                "#btn-plr-add-song": "+ TELEMETRY",
                "#btn-plr-queue": f"GRID:[{len(self.player.playlist)}]",
            },
            "bracket_caps": {
                "#btn-plr-omnirip": "【OMNIRIP】",
                "#btn-plr-presets": "【PRESETS】",
                "#btn-plr-load-layout": "【LOAD】",
                "#btn-plr-save-layout": "【SAVE】",
                "#btn-plr-gap": f"【GAP:{self.active_gap}】",
                "#btn-plr-popout": "【TAB】",
                "#btn-plr-prev": "【⏮ PREV】",
                "#btn-plr-play": "【▶ PLAY】",
                "#btn-plr-stop": "【⏹ STOP】",
                "#btn-plr-next": "【⏭ NEXT】",
                "#btn-plr-loop": f"【🔁 {self.player.loop_mode.value[:3]}】",
                "#btn-plr-shuffle": f"【🔀 {'ON' if self.player.shuffle_mode else 'OFF'}】",
                "#btn-plr-add-song": "【+ SONG】",
                "#btn-plr-queue": f"【Q:{len(self.player.playlist)}】",
            },
            "pill": {
                "#btn-plr-omnirip": "( 1: OMNIRIP )",
                "#btn-plr-presets": "( ✨ PRESETS )",
                "#btn-plr-load-layout": "( 📐 LOAD )",
                "#btn-plr-save-layout": "( 💾 SAVE )",
                "#btn-plr-gap": f"( ⚬ GAP: {self.active_gap} )",
                "#btn-plr-popout": "( ↗ TAB )",
                "#btn-plr-prev": "◀ PREV",
                "#btn-plr-play": "▶ PLAY",
                "#btn-plr-stop": "■ STOP",
                "#btn-plr-next": "▶▶ NEXT",
                "#btn-plr-loop": f"🔁 {self.player.loop_mode.value}",
                "#btn-plr-shuffle": f"🔀 {'ON' if self.player.shuffle else 'OFF'}",
                "#btn-plr-add-song": "+ LOAD SONG",
                "#btn-plr-queue": f"QUEUE ({len(self.player.playlist)})",
            },
        }

        labels = style_maps.get(mode, style_maps["pill"])
        for btn_id, label_text in labels.items():
            try:
                b = self.query_one(btn_id, Button)
                b.label = Content(label_text)
            except Exception:
                pass

        # Structural layout sizing adjustments per style
        try:
            dock = self.query_one("#plr-bottom-dock")
            top_bar = self.query_one("#plr-top-bar")
            top_bar.styles.height = 3
            dock.styles.height = 6 if structure in ("dos_mpxplay", "rackmount_hardware") else 7
        except Exception:
            pass

    def _apply_design_control_labels(self) -> None:
        """Apply the curated labels for page-level controls after legacy styling."""
        if self.current_design is None:
            return

        button_ids = (
            "#btn-plr-omnirip",
            "#btn-plr-presets",
            "#btn-plr-load-layout",
            "#btn-plr-save-layout",
            "#btn-plr-gap",
            "#btn-plr-popout",
        )
        values = {
            "gap": self.active_gap,
            "queue": len(self.player.playlist),
        }
        for button_id, template in zip(button_ids, self.current_design.top_controls, strict=True):
            label = Content(template.format(**values))
            try:
                button = self.query_one(button_id, Button)
            except Exception:
                continue
            if str(button.label) != label:
                button.label = label

    def _play_pause_label(self, is_playing: bool) -> str:
        mode = getattr(self.current_layout, "button_style_mode", "pill")
        labels = {
            "dos_keys": ("[F8:PAUSE]", "[F8:PLAY]"),
            "cyber_brackets": ("[|| PAUSE]", "[>> EXEC]"),
            "retro_arcade": ("[Ⅱ PAUSE]", "[★ START]"),
            "cozy_soft": ("Ⅱ pause", "▶ listen"),
            "tactile_knobs": ("|| PAUSE", "> PLAY"),
            "hud_caps": ("Ⅱ HOLD", "► IGNITION"),
            "bracket_caps": ("【⏸ PAUSE】", "【▶ PLAY】"),
        }
        playing_label, paused_label = labels.get(mode, ("⏸ PAUSE", "▶ PLAY"))
        return playing_label if is_playing else paused_label

    def _transport_button_state(self) -> ButtonState:
        return ButtonState(
            playing=self.player.state == PlaybackState.PLAYING,
            loop_mode=self.player.loop_mode.value,
            shuffle=bool(self.player.shuffle_mode),
            queue_size=len(self.player.playlist),
            gap=self.active_gap,
        )

    def _refresh_transport_labels(self, force: bool = False) -> None:
        """Apply design button frames when the preset defines them."""
        page = self._resolved_page
        if page is None or not page.button_frame:
            return
        state = self._transport_button_state()
        key = (state.playing, state.loop_mode, state.shuffle, state.queue_size)
        if force or key != self._last_button_state:
            apply_button_frames(self, page, state)
            self._last_button_state = key

    def _on_track_changed(self, track: PlaylistTrack) -> None:
        """Update track information in UI."""
        try:
            title_lbl = self.query_one("#plr-now-playing-title", Label)
            meta_lbl = self.query_one("#plr-now-playing-meta", Label)
            total_lbl = self.query_one("#plr-time-total", Label)
            queue_btn = self.query_one("#btn-plr-queue", Button)

            title_lbl.update(f"🎵 {track.title[:28]}")
            meta_lbl.update(f"{track.artist} | {track.sample_rate}Hz | 60 FPS")
            total_lbl.update(track.formatted_duration)
            if self.current_layout is not None:
                self._apply_button_and_layout_structure(self.current_layout, self.current_theme)
                self._apply_design_control_labels()
            else:
                queue_btn.label = f"QUEUE ({len(self.player.playlist)})"
            try:
                companion = self.query_one("#plr-anime-companion", AnimeCompanionWidget)
                companion.notify_event("track_change")
            except Exception:
                pass
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
                scrubber = self.query_one("#plr-scrubber", ProgressBar)
                elapsed_lbl = self.query_one("#plr-time-elapsed", Label)
                if dur > 0:
                    scrubber.progress = (pos / dur) * 100.0
                elapsed_lbl.update(self.player.formatted_position)
            except Exception:
                pass

        # Update Play/Pause button label (legacy path; framed designs refresh below)
        page = self._resolved_page
        if page is None or not page.button_frame:
            try:
                play_btn = self.query_one("#btn-plr-play", Button)
                is_playing = self.player.state == PlaybackState.PLAYING
                label = Content(self._play_pause_label(is_playing))
                if str(play_btn.label) != label:
                    play_btn.label = label
                play_btn.variant = "warning" if is_playing else "primary"
            except Exception:
                pass

        # Feed feature frame to all active canvas cards and anime companion
        try:
            dash = self.query_one("#plr-dashboard", VisualDashboardWidget)
            dash.tick_frame(ctx)
            companion = self.query_one("#plr-anime-companion", AnimeCompanionWidget)
            companion.feed_audio(ctx)
            companion._tick_60fps()
            if ctx.transient_flag and self.player.state == PlaybackState.PLAYING:
                companion.notify_event("drop")
        except Exception:
            pass

        # Design-level motion and framed transport labels
        if page is not None:
            try:
                self._motion.observe(self, page)
                self._refresh_transport_labels()
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-plr-play":
            self.player.toggle_play_pause()
            if self.player.state != PlaybackState.PLAYING:
                try:
                    companion = self.query_one("#plr-anime-companion", AnimeCompanionWidget)
                    companion.notify_event("pause")
                except Exception:
                    pass
        elif btn_id == "btn-plr-stop":
            self.player.stop()
        elif btn_id == "btn-plr-next":
            self.player.next_track()
        elif btn_id == "btn-plr-prev":
            self.player.prev_track()
        elif btn_id == "btn-plr-loop":
            self.player.toggle_loop()
            if self.current_layout is not None:
                self._apply_button_and_layout_structure(self.current_layout, self.current_theme)
                self._apply_design_control_labels()
        elif btn_id == "btn-plr-shuffle":
            self.player.toggle_shuffle()
            if self.current_layout is not None:
                self._apply_button_and_layout_structure(self.current_layout, self.current_theme)
                self._apply_design_control_labels()
        elif btn_id == "btn-plr-omnirip":
            self._return_to_omnirip()
        elif btn_id == "btn-plr-presets":
            self.app.push_screen(PresetCatalogModal(self.layout_store), self._handle_preset_selected)
        elif btn_id == "btn-plr-gap":
            self._cycle_gap()
        elif btn_id == "btn-plr-add-song":
            self.app.push_screen(AddSongModal(), self._handle_add_song)
        elif btn_id == "btn-plr-save-layout":
            self.app.push_screen(SaveLayoutModal(), self._handle_save_layout)
        elif btn_id == "btn-plr-load-layout":
            self._cycle_layout()
        elif btn_id == "btn-plr-popout":
            launch_player_external()

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
        self._apply_design_control_labels()

        dash = self.query_one("#plr-dashboard", VisualDashboardWidget)
        dash.gap_size = self.active_gap
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

        dash = self.query_one("#plr-dashboard", VisualDashboardWidget)
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


class PlayerScreen(ModalScreen):
    """In-app fullscreen modal studio for PLAYER."""

    DEFAULT_CSS = """
    PlayerScreen {
        width: 100%;
        height: 100%;
        background: #0a0e14;
    }
    """

    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("1", "escape"):
            self.dismiss()


class PlayerApp(App):
    """Standalone Textual application for PLAYER Studio."""

    CSS = """
    Screen {
        background: #0a0e14;
    }
    """

    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()
        yield Footer()


def main():
    """Entry point for standalone `omnirip-player` terminal execution."""
    app = PlayerApp()
    app.run()


if __name__ == "__main__":
    main()
