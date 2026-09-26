"""Deterministic companion behaviour: moods, BPM, scenes, and dialogue.

The companion listens to the same :class:`AudioFeatureContext` stream as the
visualizers. ``MoodEngine`` classifies that stream into a small set of authored
states with hysteresis and cooldowns (so it never flickers), ``BpmEstimator``
derives tempo from stable onset intervals, ``SceneEngine`` renders a
deterministic ambient strip per preset, and ``dialogue_for`` maps context
events to short preset-voiced lines. Nothing here draws widgets; it is pure
state plus string output, so it is unit-testable without a terminal.
"""

from __future__ import annotations

import random
import statistics
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from harvester.ui.visuals.base import AudioFeatureContext


class Mood(StrEnum):
    SLEEPY = "sleepy"
    CHILL = "chill"
    FOCUS = "focus"
    GROOVE = "groove"
    HYPE = "hype"
    EUPHORIC = "euphoric"


# Moods that animate the scene strongly; calm moods stay sparse.
MOOD_INTENSITY: dict[str, float] = {
    Mood.SLEEPY.value: 0.15,
    Mood.FOCUS.value: 0.3,
    Mood.CHILL.value: 0.45,
    Mood.GROOVE.value: 0.7,
    Mood.HYPE.value: 0.95,
    Mood.EUPHORIC.value: 1.2,
}

MIN_BPM = 50.0
MAX_BPM = 200.0
SLEEP_AFTER_SECONDS = 4.0
QUIET_RMS_DB = -55.0

MOOD_HOLD_SECONDS: Mapping[str, float] = {
    Mood.SLEEPY.value: 1.5,
    Mood.EUPHORIC.value: 1.0,
    Mood.HYPE.value: 0.8,
    Mood.GROOVE.value: 0.7,
    Mood.FOCUS.value: 0.9,
    Mood.CHILL.value: 1.0,
}
MOOD_COOLDOWN_SECONDS = 0.4


@dataclass
class BpmEstimator:
    """Estimate tempo from onset intervals gated by transients, not noise."""

    min_bpm: float = MIN_BPM
    max_bpm: float = MAX_BPM
    window: int = 12
    min_gap: float = 0.15
    max_gap: float = 2.0

    bpm: float | None = None
    intervals: list[float] = field(default_factory=list)
    _clock: float = 0.0
    _last_onset: float | None = None
    _quiet_for: float = 0.0

    def observe(self, ctx: AudioFeatureContext, dt: float) -> float | None:
        """Advance the estimator by one frame and return the current BPM."""
        self._clock += dt
        quiet = (not ctx.is_playing) or ctx.rms_db < QUIET_RMS_DB
        if quiet:
            self._quiet_for += dt
            if self._quiet_for >= SLEEP_AFTER_SECONDS:
                self.intervals.clear()
                self._last_onset = None
                self.bpm = None
            return self.bpm

        self._quiet_for = 0.0
        if ctx.transient_flag:
            if self._last_onset is not None:
                gap = self._clock - self._last_onset
                if self.min_gap < gap < self.max_gap:
                    self.intervals.append(gap)
                    if len(self.intervals) > self.window:
                        self.intervals.pop(0)
                    if len(self.intervals) >= 4:
                        bpm = 60.0 / statistics.median(self.intervals)
                        if self.min_bpm <= bpm <= self.max_bpm:
                            self.bpm = bpm
            self._last_onset = self._clock
        return self.bpm


@dataclass
class MoodEngine:
    """Classify audio frames into authored moods with hysteresis."""

    mood: Mood = Mood.CHILL
    bpm: float | None = None
    _idle_for: float = 0.0
    _hype_for: float = 0.0
    _candidate: Mood | None = None
    _candidate_for: float = 0.0
    _cooldown: float = 0.0
    _estimator: BpmEstimator = field(default_factory=BpmEstimator)

    def observe(self, ctx: AudioFeatureContext, dt: float = 1.0 / 60.0) -> Mood:
        self.bpm = self._estimator.observe(ctx, dt)
        if self._cooldown > 0:
            self._cooldown = max(0.0, self._cooldown - dt)

        if ctx.is_playing and ctx.rms_db >= QUIET_RMS_DB:
            self._idle_for = 0.0
        else:
            self._idle_for += dt

        target = self.classify(ctx)
        if target == self.mood:
            self._candidate = None
            self._candidate_for = 0.0
            return self.mood

        if target == self._candidate:
            self._candidate_for += dt
        else:
            self._candidate = target
            self._candidate_for = 0.0

        if self._cooldown <= 0 and self._candidate_for >= MOOD_HOLD_SECONDS.get(target.value, 0.8):
            self.mood = target
            self._candidate = None
            self._candidate_for = 0.0
            self._cooldown = MOOD_COOLDOWN_SECONDS
        return self.mood

    def classify(self, ctx: AudioFeatureContext) -> Mood:
        """Pure classification without hysteresis; used by tests and observe()."""
        if self._idle_for >= SLEEP_AFTER_SECONDS:
            return Mood.SLEEPY
        if not ctx.is_playing or ctx.rms_db < QUIET_RMS_DB:
            return Mood.CHILL

        bass = max(ctx.sub_bass_energy, ctx.bass_energy)
        transient = bool(ctx.transient_flag)
        self._hype_for = self._hype_for + 1.0 if (transient and bass > 0.55) else max(0.0, self._hype_for - 2.0)
        if self._hype_for >= 8.0:
            return Mood.EUPHORIC
        if bass > 0.6 or (transient and bass > 0.4):
            return Mood.HYPE
        if self.bpm is not None and self.bpm >= 140.0:
            return Mood.GROOVE
        if ctx.spectral_centroid >= 3200.0 and bass < 0.3:
            return Mood.FOCUS
        if bass < 0.28:
            return Mood.CHILL
        return Mood.GROOVE


@dataclass(frozen=True, slots=True)
class SceneRecipe:
    """A preset's ambient particle vocabulary and density."""

    scene_id: str
    glyphs: tuple[str, ...]
    density: float
    drift: float


SCENE_RECIPES: dict[str, SceneRecipe] = {
    "preset_y2k_aesthetic": SceneRecipe("aero_bubbles", ("°", "○", "·", "✧"), 0.34, 0.5),
    "preset_cyberpunk_2077": SceneRecipe("acid_rain", ("│", "╱", "·", "▖"), 0.42, 1.4),
    "preset_matrix_terminal": SceneRecipe("code_drizzle", ("0", "1", "│", "░"), 0.4, 1.1),
    "preset_lofi_chill": SceneRecipe("window_rain", ("˙", "·", "│", "☁"), 0.26, 0.4),
    "preset_tokyo_night": SceneRecipe("platform_streaks", ("─", "·", "▬", "│"), 0.3, 0.9),
    "preset_retrowave_sunset": SceneRecipe("horizon_dust", ("·", "╱", "▁", "✦"), 0.34, 1.2),
    "preset_industrial_decay": SceneRecipe("sparks", ("˙", "·", "*", "╱"), 0.22, 0.3),
    "preset_deep_ocean": SceneRecipe("bubble_column", ("°", "·", "○", "⌁"), 0.3, 0.35),
    "preset_solar_flare": SceneRecipe("ember_arc", ("·", "˙", "☼", "╲"), 0.3, 0.6),
    "preset_acid_techno": SceneRecipe("step_blink", ("▖", "▘", "▪", "·"), 0.5, 2.0),
    "preset_vaporwave_mall": SceneRecipe("fountain_mist", ("·", "˚", "○", "≈"), 0.22, 0.3),
    "preset_dungeon_synth": SceneRecipe("torch_embers", ("˙", "·", "†", "░"), 0.2, 0.25),
    "preset_chiptune_gameboy": SceneRecipe("pixel_sparkle", ("▪", "▫", "·", "×"), 0.4, 1.6),
    "preset_nordic_aurora": SceneRecipe("aurora_veil", ("╱", "╲", "⋰", "·"), 0.28, 0.25),
    "preset_bioshock_steampunk": SceneRecipe("water_ripple", ("≈", "·", "⌁", "○"), 0.26, 0.35),
    "preset_quantum_void": SceneRecipe("decoherence", ("·", "∘", "|", "⟩"), 0.24, 0.4),
    "preset_hyprland_rice": SceneRecipe("status_pulse", ("·", "▪", "│", "┈"), 0.3, 0.6),
    "preset_dos_mpxplay": SceneRecipe("block_levels", ("░", "▒", "▓", "─"), 0.36, 0.5),
    "preset_analog_mastering": SceneRecipe("calibration_ticks", ("─", "·", "╱", "│"), 0.24, 0.2),
    "preset_stellar_galaxy": SceneRecipe("star_chart", ("·", "✦", "°", "⋆"), 0.26, 0.2),
    "builtin_solo_stanford": SceneRecipe("lab_scope", ("·", "─", "╱", "○"), 0.28, 0.45),
    "builtin_dual_cyber": SceneRecipe("dual_streams", ("│", "·", "▖", "▗"), 0.36, 0.9),
    "builtin_quad_matrix": SceneRecipe("bus_ticks", ("·", "│", "▪", "─"), 0.3, 0.5),
}
DEFAULT_SCENE = SceneRecipe("default_ambient", ("·", "˙", "○", "░"), 0.24, 0.3)


def _seed(*parts: object) -> int:
    """Stable cross-process seed; builtin hash() is salted per process."""
    value = 7
    for part in parts:
        value = (value * 131 + sum(ord(ch) for ch in str(part))) % 0xFFFFFFFF
    return value


class SceneEngine:
    """Deterministic ambient strip renderer for companion scenes."""

    def __init__(self, scene_id: str = "") -> None:
        self.scene_id = scene_id
        self.recipe = SCENE_RECIPES.get(scene_id, DEFAULT_SCENE)
        self._recipe_cache: dict[str, SceneRecipe] = {}

    def recipe_for(self, scene_id: str) -> SceneRecipe:
        if scene_id not in self._recipe_cache:
            self._recipe_cache[scene_id] = SCENE_RECIPES.get(scene_id, DEFAULT_SCENE)
        return self._recipe_cache[scene_id]

    def render_strip(
        self,
        width: int,
        tick: int,
        mood: Mood = Mood.CHILL,
        scene_id: str | None = None,
    ) -> str:
        """Render one deterministic ambient line for the companion panel."""
        recipe = self.recipe_for(scene_id or self.scene_id)
        multiplier = MOOD_INTENSITY.get(mood.value, 0.5)
        density = min(1.0, recipe.density * multiplier)
        drift = int(tick * recipe.drift)
        cells: list[str] = []
        for column in range(max(1, width)):
            rng = random.Random(_seed(recipe.scene_id, tick + column, drift))
            if rng.random() < density:
                cells.append(rng.choice(recipe.glyphs))
            else:
                cells.append(" ")
        return "".join(cells)


VOICE_LINES: dict[str, dict[str, tuple[str, ...]]] = {
    "aero": {
        "track_change": ("New disc loaded.", "Buffering a fresh track...", "Audio stream online."),
        "pause": ("Signal held.", "Standing by...", "Paused, still glowing."),
        "drop": ("Full spectrum!", "That hit landed.", "Loud and clear!"),
    },
    "night_city": {
        "track_change": ("New feed intercepted.", "Channel switched.", "Signal acquired."),
        "pause": ("Holding position.", "Feed muted.", "Standby, choom."),
        "drop": ("Breach detected!", "Transient spike!", "That's the drop!"),
    },
    "operator": {
        "track_change": ("Load complete.", "Next entry parsed.", "Stream reconnected."),
        "pause": ("Awaiting input.", "Process suspended.", "Idle loop."),
        "drop": ("Peak threshold hit.", "Anomaly logged.", "Signal surge."),
    },
    "cozy": {
        "track_change": ("New song on the tape.", "Fresh side ready.", "Let's listen."),
        "pause": ("Tea break.", "Resting a moment.", "Softly paused."),
        "drop": ("Ooh, this part!", "Feel that warm bass?", "What a groove."),
    },
    "archivist": {
        "track_change": ("Another page turns.", "The chronicle continues.", "A new verse begins."),
        "pause": ("The hall falls quiet.", "Torches dim.", "A silent interlude."),
        "drop": ("The stone echoes!", "Ancient drums stir!", "A mighty swell."),
    },
    "engineer": {
        "track_change": ("Next program queued.", "Alignment reset.", "Reference loaded."),
        "pause": ("Monitor muted.", "Transport held.", "Calibration pause."),
        "drop": ("True peak approaching!", "Threshold exceeded.", "Full-scale transient."),
    },
}

DESIGN_VOICES: dict[str, str] = {
    "preset_y2k_aesthetic": "aero",
    "preset_cyberpunk_2077": "night_city",
    "preset_matrix_terminal": "operator",
    "preset_lofi_chill": "cozy",
    "preset_tokyo_night": "night_city",
    "preset_retrowave_sunset": "aero",
    "preset_industrial_decay": "operator",
    "preset_deep_ocean": "operator",
    "preset_solar_flare": "operator",
    "preset_acid_techno": "night_city",
    "preset_vaporwave_mall": "cozy",
    "preset_dungeon_synth": "archivist",
    "preset_chiptune_gameboy": "aero",
    "preset_nordic_aurora": "archivist",
    "preset_bioshock_steampunk": "archivist",
    "preset_quantum_void": "operator",
    "preset_hyprland_rice": "engineer",
    "preset_dos_mpxplay": "engineer",
    "preset_analog_mastering": "engineer",
    "preset_stellar_galaxy": "archivist",
    "builtin_solo_stanford": "engineer",
    "builtin_dual_cyber": "operator",
    "builtin_quad_matrix": "engineer",
}


def dialogue_for(design_id: str, event: str, tick: int = 0) -> str:
    """Pick a short deterministic line for a context event."""
    voice = DESIGN_VOICES.get(design_id, "cozy")
    lines = VOICE_LINES.get(voice, VOICE_LINES["cozy"]).get(event)
    if not lines:
        return ""
    return lines[_seed(design_id, event, tick) % len(lines)]


@dataclass
class CheerMeter:
    """Lightweight affinity signal: grows while the set is playing."""

    value: float = 0.0
    cap: float = 100.0

    def observe(self, ctx: AudioFeatureContext, dt: float) -> float:
        if ctx.is_playing and ctx.rms_db >= QUIET_RMS_DB:
            rate = 1.6 if ctx.transient_flag else 0.6
            self.value = min(self.cap, self.value + rate * dt)
        return self.value

    @property
    def label(self) -> str:
        filled = int(round(self.value / self.cap * 8))
        return "▰" * filled + "▱" * (8 - filled)


@dataclass
class CompanionSession:
    """Bundle the companion state so widgets and tests share one entry point."""

    design_id: str = ""
    mood_engine: MoodEngine = field(default_factory=MoodEngine)
    scene_engine: SceneEngine = field(default_factory=SceneEngine)
    cheer: CheerMeter = field(default_factory=CheerMeter)
    speech: str = ""
    speech_until_tick: int = 0
    _last_speech_event: str = ""
    _event_cooldowns: dict[str, int] = field(default_factory=dict)

    def set_design(self, design_id: str) -> None:
        self.design_id = design_id
        self.scene_engine.scene_id = design_id

    def observe(self, ctx: AudioFeatureContext, tick: int, dt: float = 1.0 / 60.0) -> Mood:
        mood = self.mood_engine.observe(ctx, dt)
        self.cheer.observe(ctx, dt)
        if self.speech and tick >= self.speech_until_tick:
            self.speech = ""
        return mood

    def notify(self, event: str, tick: int, cooldown_ticks: int = 150) -> str:
        """Set a speech line unless the event is on cooldown."""
        last = self._event_cooldowns.get(event, -cooldown_ticks)
        if tick - last < cooldown_ticks:
            return self.speech
        line = dialogue_for(self.design_id, event, tick)
        if not line:
            return self.speech
        self.speech = line
        self.speech_until_tick = tick + 180
        self._last_speech_event = event
        self._event_cooldowns[event] = tick
        return self.speech

    def status_line(self) -> str:
        bpm = f"{int(round(self.mood_engine.bpm))} BPM" if self.mood_engine.bpm else "--- BPM"
        return f"{self.mood_engine.mood.value.upper()} · {bpm} · {self.cheer.label}"

    def scene_line(self, width: int, tick: int) -> str:
        return self.scene_engine.render_strip(width, tick, self.mood_engine.mood, self.design_id)
