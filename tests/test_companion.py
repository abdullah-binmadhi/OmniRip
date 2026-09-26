"""Unit tests for the deterministic companion behaviour system."""

import numpy as np
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from harvester.services.vision_layout_store import VisionLayoutStore
from harvester.ui.companion import (
    SCENE_RECIPES,
    VOICE_LINES,
    BpmEstimator,
    CompanionSession,
    Mood,
    MoodEngine,
    SceneEngine,
    dialogue_for,
)
from harvester.ui.player_designs import PLAYER_PAGE_DESIGNS
from harvester.ui.player_studio import AnimeCompanionWidget, PlayerStudioWidget
from harvester.ui.visuals.base import AudioFeatureContext


def _loud(transient: bool = False, bass: float = 0.9, centroid: float = 1500.0) -> AudioFeatureContext:
    return AudioFeatureContext(
        levels_128=np.full(128, bass, dtype=np.float32),
        is_playing=True,
        rms_db=-18.0,
        transient_flag=transient,
        spectral_centroid=centroid,
    )


def _quiet_frame() -> AudioFeatureContext:
    return AudioFeatureContext.synthesize_idle()


def test_bpm_estimator_from_stable_onsets():
    estimator = BpmEstimator()
    dt = 1.0 / 60.0
    frame = 0
    while frame < 60 * 8:
        transient = frame % 30 == 0  # 0.5s interval -> 120 BPM
        estimator.observe(_loud(transient=transient), dt)
        frame += 1
    assert estimator.bpm is not None
    assert 115.0 <= estimator.bpm <= 125.0


def test_bpm_estimator_resets_after_silence():
    estimator = BpmEstimator()
    dt = 1.0 / 60.0
    for frame in range(60 * 6):
        estimator.observe(_loud(transient=frame % 30 == 0), dt)
    assert estimator.bpm is not None
    for _ in range(60 * 6):
        estimator.observe(_quiet_frame(), dt)
    assert estimator.bpm is None


def test_mood_engine_sleeps_after_silence():
    engine = MoodEngine()
    dt = 1.0 / 60.0
    for _ in range(int(6.0 / dt)):
        engine.observe(_quiet_frame(), dt)
    assert engine.mood == Mood.SLEEPY


def test_mood_engine_hypes_on_sustained_bass():
    engine = MoodEngine()
    dt = 1.0 / 60.0
    for _ in range(int(2.0 / dt)):
        engine.observe(_loud(transient=True), dt)
    assert engine.mood in (Mood.HYPE, Mood.EUPHORIC)


def test_mood_engine_classify_focus_for_bright_low_bass():
    engine = MoodEngine()
    ctx = AudioFeatureContext(
        levels_128=np.full(128, 0.1, dtype=np.float32),
        is_playing=True,
        rms_db=-30.0,
        spectral_centroid=4000.0,
    )
    assert engine.classify(ctx) == Mood.FOCUS


def test_scene_recipes_cover_every_design_and_are_deterministic():
    assert set(SCENE_RECIPES) == set(PLAYER_PAGE_DESIGNS)
    scene = SceneEngine("preset_deep_ocean")
    first = scene.render_strip(30, 10, Mood.CHILL)
    assert first == scene.render_strip(30, 10, Mood.CHILL)
    assert len(first) == 30
    assert scene.render_strip(30, 11, Mood.CHILL) != first
    deeper = scene.render_strip(30, 10, Mood.EUPHORIC)
    assert deeper != first


def test_dialogue_for_uses_preset_voice_and_falls_back():
    line = dialogue_for("preset_matrix_terminal", "track_change", tick=3)
    assert line in VOICE_LINES["operator"]["track_change"]
    fallback = dialogue_for("unknown_design", "drop", tick=1)
    assert fallback in VOICE_LINES["cozy"]["drop"]
    assert dialogue_for("preset_matrix_terminal", "unknown_event", tick=1) == ""


def test_session_notify_cooldown_and_speech_expiry():
    session = CompanionSession(design_id="preset_lofi_chill")
    first = session.notify("track_change", tick=0)
    assert first
    assert session.notify("track_change", tick=20) == first
    second = session.notify("track_change", tick=200)
    assert second
    assert session.speech
    assert session.speech_until_tick == 380
    # observing past the expiry clears the bubble
    session.observe(_quiet_frame(), tick=400)
    assert session.speech == ""


def test_session_status_line_reports_mood_and_cheer():
    session = CompanionSession(design_id="preset_acid_techno")
    session.observe(_loud(transient=True), tick=1)
    session.cheer.value = 50.0
    status = session.status_line()
    assert "BPM" in status
    assert "▰" in status


class _PlayerApp(App):
    def compose(self) -> ComposeResult:
        yield PlayerStudioWidget()


@pytest.mark.asyncio
async def test_companion_widget_surfaces_mood_scene_and_speech():
    layout = VisionLayoutStore().get_layout("preset_y2k_aesthetic")
    assert layout is not None

    app = _PlayerApp()
    async with app.run_test(size=(140, 40)) as pilot:
        studio = app.query_one(PlayerStudioWidget)
        studio.apply_layout(layout)
        await pilot.pause()

        companion = app.query_one("#plr-anime-companion", AnimeCompanionWidget)
        assert companion.session.design_id == "preset_y2k_aesthetic"

        companion.feed_audio(_loud(transient=True))
        for _ in range(120):
            companion._tick_60fps()
        status = str(companion.query_one("#anime-char-status", Label).render())
        assert "HYPE" in status or "EUPHORIC" in status
        scene = str(companion.query_one("#anime-char-scene", Label).render())
        assert scene.strip()

        companion.notify_event("track_change")
        speech = str(companion.query_one("#anime-char-speech", Label).render())
        assert speech
