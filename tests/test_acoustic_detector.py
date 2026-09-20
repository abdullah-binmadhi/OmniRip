"""Tests for Acoustic Music & Vocal Presence Detector."""

import numpy as np
import pytest

from harvester.analysis.enhancement.acoustic_detector import (
    AcousticAnalysisResult,
    analyze_track_acoustics,
)


def _generate_synthetic_track(
    sr: int = 44100,
    duration_s: float = 1.0,
    vocal_gain: float = 0.0,
    inst_gain: float = 0.5,
    rumble_gain: float = 0.0,
    boxiness_gain: float = 0.0,
    side_synth_gain: float = 0.0,
    sibilance_gain: float = 0.0,
) -> np.ndarray:
    """Generate deterministic synthetic stereo audio (2, samples) for testing."""
    samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, samples, endpoint=False, dtype=np.float32)

    left = np.zeros(samples, dtype=np.float32)
    right = np.zeros(samples, dtype=np.float32)

    # Base instrumental (rhythm/bass)
    if inst_gain > 0:
        bass = np.sin(2 * np.pi * 80.0 * t, dtype=np.float32)
        left += inst_gain * bass
        right += inst_gain * bass

    # Center vocal with harmonic formants (500, 1000, 1500, 2500 Hz)
    if vocal_gain > 0:
        voc = (
            np.sin(2 * np.pi * 500.0 * t, dtype=np.float32)
            + 0.8 * np.sin(2 * np.pi * 1000.0 * t, dtype=np.float32)
            + 0.5 * np.sin(2 * np.pi * 1500.0 * t, dtype=np.float32)
            + 0.3 * np.sin(2 * np.pi * 2500.0 * t, dtype=np.float32)
        )
        left += vocal_gain * voc
        right += vocal_gain * voc

    # Sub-bass rumble (<35 Hz)
    if rumble_gain > 0:
        rumble = np.sin(2 * np.pi * 20.0 * t, dtype=np.float32)
        left += rumble_gain * rumble
        right += rumble_gain * rumble

    # Low-mid mud / boxiness (250-350 Hz)
    if boxiness_gain > 0:
        box = np.sin(2 * np.pi * 300.0 * t, dtype=np.float32)
        left += boxiness_gain * box
        right += boxiness_gain * box

    # Wide stereo synths in vocal band (pure side channel)
    if side_synth_gain > 0:
        synth = np.sin(2 * np.pi * 1200.0 * t, dtype=np.float32)
        left += side_synth_gain * synth
        right -= side_synth_gain * synth  # Opposite phase creates 100% side energy

    # Sibilance / fizz (>6000 Hz)
    if sibilance_gain > 0:
        sib = np.sin(2 * np.pi * 8000.0 * t, dtype=np.float32)
        left += sibilance_gain * sib
        right += sibilance_gain * sib

    return np.stack([left, right], axis=0)


def test_pure_instrumental_detection() -> None:
    """Test pure instrumental track with zero vocals flags is_pure_instrumental=True."""
    audio = _generate_synthetic_track(vocal_gain=0.0, inst_gain=0.7)
    res: AcousticAnalysisResult = analyze_track_acoustics(audio, sr=44100)

    assert isinstance(res, AcousticAnalysisResult)
    assert res.is_pure_instrumental is True
    assert res.has_vocals is False
    assert res.vocal_confidence < 0.25
    assert res.recommended_blend_weight == 0.0
    assert "vad_gate" not in res.recommended_vocal_flags


def test_vocal_presence_detection() -> None:
    """Test track with strong center vocal formants detects vocals with high confidence."""
    audio = _generate_synthetic_track(vocal_gain=0.6, inst_gain=0.2)
    res = analyze_track_acoustics(audio, sr=44100)

    assert res.is_pure_instrumental is False
    assert res.has_vocals is True
    assert res.vocal_confidence > 0.45
    assert "vad_gate" in res.recommended_vocal_flags
    assert "kill_whispers" in res.recommended_inst_flags


def test_sub_bass_rumble_defect() -> None:
    """Test that prominent subsonic rumble triggers sub_bass_clean inst remediation."""
    audio = _generate_synthetic_track(inst_gain=0.2, rumble_gain=0.9)
    res = analyze_track_acoustics(audio, sr=44100)

    assert "sub_bass_clean" in res.recommended_inst_flags
    assert any("sub_bass" in issue.lower() for issue in res.detected_issues)


def test_low_mid_mud_defect() -> None:
    """Test that heavy 300 Hz energy triggers de_mud remediation."""
    audio = _generate_synthetic_track(inst_gain=0.2, boxiness_gain=0.9)
    res = analyze_track_acoustics(audio, sr=44100)

    assert "de_mud" in res.recommended_inst_flags
    assert any("mud" in issue.lower() for issue in res.detected_issues)


def test_side_synth_bleed_defect() -> None:
    """Test that out-of-phase stereo synth energy in vocal band triggers anti_bleed_synths."""
    audio = _generate_synthetic_track(inst_gain=0.2, side_synth_gain=0.8)
    res = analyze_track_acoustics(audio, sr=44100)

    assert "anti_bleed_synths" in res.recommended_inst_flags
    assert any("synth" in issue.lower() or "bleed" in issue.lower() for issue in res.detected_issues)


def test_sibilance_defect() -> None:
    """Test that high-frequency energy triggers de-essing flag."""
    audio = _generate_synthetic_track(vocal_gain=0.5, sibilance_gain=0.9)
    res = analyze_track_acoustics(audio, sr=44100)

    assert "de_ess" in res.recommended_vocal_flags or "air_de_fizz" in res.recommended_vocal_flags


def test_mono_and_silence() -> None:
    """Test analyzer handles 1D mono audio and complete digital silence without errors."""
    sr = 44100
    # 1D silence
    silent_1d = np.zeros(44100, dtype=np.float32)
    res_silence = analyze_track_acoustics(silent_1d, sr=sr)
    assert res_silence.is_pure_instrumental is True
    assert res_silence.vocal_confidence == 0.0

    # 1D with vocal
    t = np.linspace(0, 1.0, 44100, endpoint=False, dtype=np.float32)
    voc_1d = np.sin(2 * np.pi * 1000.0 * t, dtype=np.float32)
    res_mono = analyze_track_acoustics(voc_1d, sr=sr)
    assert isinstance(res_mono, AcousticAnalysisResult)
