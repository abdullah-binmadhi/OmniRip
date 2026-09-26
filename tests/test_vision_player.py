"""Unit tests for Full Vision Audio Player and 60 FPS Telemetry."""

import wave
from pathlib import Path

import numpy as np
import pytest

from harvester.services.vision_player import (
    LoopMode,
    PlaybackState,
    VisionAudioPlayer,
    extract_60fps_features,
)


@pytest.fixture
def sample_wav_file(tmp_path: Path) -> Path:
    """Create a 1.0-second synthetic stereo WAV file."""
    wav_path = tmp_path / "test_track.wav"
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    sig_l = 0.5 * np.sin(2 * np.pi * 220 * t)
    sig_r = 0.5 * np.sin(2 * np.pi * 440 * t)

    # Interleave stereo 16-bit PCM
    stereo = np.empty((len(t) * 2,), dtype=np.int16)
    stereo[0::2] = (sig_l * 32767).astype(np.int16)
    stereo[1::2] = (sig_r * 32767).astype(np.int16)

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

    return wav_path


def test_extract_60fps_features():
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = (0.5 * np.sin(2 * np.pi * 100 * t)).astype(np.float32)

    features = extract_60fps_features(y, sr)
    # Approx 60 frames for 1 second of audio
    assert len(features) >= 58
    assert len(features) <= 62

    first_frame = features[0]
    assert len(first_frame.levels_128) == 128
    assert len(first_frame.waveform_l) == 1024
    assert first_frame.is_playing is True


def test_player_lifecycle(sample_wav_file: Path):
    player = VisionAudioPlayer()
    assert player.state == PlaybackState.STOPPED

    track = player.load_track(sample_wav_file)
    assert track is not None
    assert track.title == "Test Track"
    assert len(track.feature_track) >= 58
    assert len(player.playlist) == 1
    assert player.current_track == track

    # Transport controls
    player.play()
    assert player.state == PlaybackState.PLAYING

    ctx = player.update_frame()
    assert ctx.is_playing is True

    player.pause()
    assert player.state == PlaybackState.PAUSED

    player.resume()
    assert player.state == PlaybackState.PLAYING

    player.seek(0.5)
    assert player.current_position_seconds >= 0.45

    player.stop()
    assert player.state == PlaybackState.STOPPED
    assert player.current_position_seconds == 0.0

    # Loop and shuffle toggles
    assert player.toggle_loop() == LoopMode.TRACK
    assert player.toggle_loop() == LoopMode.ALL
    assert player.toggle_loop() == LoopMode.OFF

    assert player.toggle_shuffle() is True
    assert player.toggle_shuffle() is False
