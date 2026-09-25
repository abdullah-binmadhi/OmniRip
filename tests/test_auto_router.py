"""Unit tests for the Intelligent Dual-Engine Auto-Router."""

from __future__ import annotations

from pathlib import Path

from harvester.analysis.enhancement.auto_router import auto_route_track


def test_auto_route_lossy_mp3_engages_bandwidth_extender():
    decision = auto_route_track(
        audio_path=Path("track.mp3"),
        cutoff_hz=15500.0,
        mode="enhance_only",
        has_vocals=True,
    )
    assert decision.neural_bandwidth_extender is True
    assert decision.limiter_ceiling_db == -0.1
    assert any("Neural Bandwidth Extender" in line for line in decision.explanation)


def test_auto_route_lossless_audio_bypasses_bandwidth_extender():
    decision = auto_route_track(
        audio_path=Path("master.wav"),
        cutoff_hz=21000.0,
        mode="enhance_only",
        has_vocals=True,
    )
    assert decision.neural_bandwidth_extender is False
    assert any("bypassing neural synthesis" in line for line in decision.explanation)


def test_auto_route_stems_vocal_weighting_vs_dance():
    # Vocal-centric Pop
    pop_decision = auto_route_track(
        audio_path=Path("vocal_pop.wav"),
        cutoff_hz=18000.0,
        mode="stems_only",
        genre="Pop",
        has_vocals=True,
        vocal_confidence=0.9,
    )
    assert pop_decision.neural_vocal_weight >= 0.85

    # Heavy Electronic / Dance
    dance_decision = auto_route_track(
        audio_path=Path("club_track.mp3"),
        cutoff_hz=15000.0,
        mode="stems_only",
        genre="Electronic",
        has_vocals=True,
        vocal_confidence=0.5,
    )
    assert dance_decision.neural_inst_weight >= 0.80


def test_auto_route_maps_detected_issues_and_triage_answers():
    decision = auto_route_track(
        audio_path=Path("song.mp3"),
        cutoff_hz=15400.0,
        mode="enhance_only",
        detected_issues=["sibilance", "boomy_sub"],
        triage_answers={
            "cold_digital": True,
            "too_narrow": True,
            "weak_bass": True,
        },
    )
    assert "harsh_s" in decision.active_dsp_keys
    assert "boomy_low" in decision.active_dsp_keys
    assert "cold_digital" in decision.active_dsp_keys
    assert "too_narrow" in decision.active_dsp_keys
    assert "weak_bass" in decision.active_dsp_keys
    assert len(decision.explanation) >= 5
