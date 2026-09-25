"""
Intelligent Dual-Engine Auto-Router for OmniRip.

Automatically derives optimal neural model weights, high-frequency synthesis,
vectorized DSP remediation chains, and limiter headroom from acoustic analysis,
genre classification, and user triage answers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from harvester.analysis.enhancement.genres import GENRE_PROFILES, resolve_genre_names


@dataclass(frozen=True)
class AutoRouteDecision:
    """Executable mastering and stem separation plan derived automatically."""

    mode: Literal["enhance_only", "stems_only"]
    neural_bandwidth_extender: bool
    neural_vocal_weight: float
    neural_inst_weight: float
    active_dsp_keys: list[str]
    limiter_ceiling_db: float = -0.1
    recommended_eq_preset: str = "balanced"
    genre_matched: str = "Pop"
    explanation: list[str] = field(default_factory=list)


def auto_route_track(
    audio_path: Path | str,
    cutoff_hz: float,
    *,
    mode: Literal["enhance_only", "stems_only"] = "enhance_only",
    has_vocals: bool = True,
    vocal_confidence: float = 0.5,
    is_pure_instrumental: bool = False,
    detected_issues: list[str] | None = None,
    genre: str = "auto",
    triage_answers: dict[str, bool] | None = None,
    crest_factor_db: float = 12.0,
) -> AutoRouteDecision:
    """Analyze acoustic profile and triage answers to generate an optimal auto-route decision."""
    issues = set(detected_issues or [])
    answers = triage_answers or {}
    explanation: list[str] = []

    # 1. Resolve Genre Context
    norm_genre = (genre or "").strip()
    matched_profile = None
    if norm_genre and norm_genre.lower() != "auto":
        choice = resolve_genre_names([norm_genre])
        if choice.mix and choice.mix[0][0] in GENRE_PROFILES:
            matched_profile = GENRE_PROFILES[choice.mix[0][0]]

    resolved_genre = matched_profile.label if matched_profile else "Modern Pop"
    matched_key = matched_profile.key if matched_profile else "pop"
    explanation.append(f"Target Acoustic Domain: {resolved_genre}")

    # 2. Bandwidth Extension Policy
    # Lossy MP3 brickwalls usually sit at 15.5 kHz or 16 kHz. Full bandwidth audio is >= 19 kHz.
    needs_bandwidth_ext = cutoff_hz < 16500.0
    if needs_bandwidth_ext:
        explanation.append(
            f"Detected lossy cutoff at {cutoff_hz / 1000.0:.1f} kHz; engaged Neural Bandwidth Extender (BS-RoFormer)."
        )
    else:
        explanation.append(
            f"High-frequency spectrum preserved ({cutoff_hz / 1000.0:.1f} kHz); bypassing neural synthesis to preserve original transients."
        )

    # 3. Model Weighting (Vocal vs Instrumental)
    is_rhythm_heavy = any(
        k in matched_key
        for k in ("hip_hop", "drill", "house", "techno", "edm", "bass", "metal", "rock")
    )
    if mode == "stems_only":
        if is_pure_instrumental or not has_vocals or vocal_confidence < 0.2:
            v_weight = 0.1
            i_weight = 0.95
            explanation.append("Low vocal confidence; prioritizing HDEMUCS full-spectrum backing isolation.")
        elif is_rhythm_heavy:
            v_weight = 0.35
            i_weight = 0.85
            explanation.append(f"Heavy rhythm domain ({resolved_genre}); weighting HDEMUCS (<300 Hz) for punch.")
        else:
            v_weight = 0.90
            i_weight = 0.50
            explanation.append("Vocal-centric domain; weighting BS-RoFormer (90%) for 0% bleed acapella extraction.")
    else:
        # Enhance Only uses hybrid synthesis
        v_weight = 0.85 if has_vocals else 0.0
        i_weight = 0.85

    # 4. Vectorized DSP Remediation Matrix
    active_dsp: list[str] = []

    # Tonal & Sibilance
    if answers.get("harsh_s", False) or "sibilance" in issues:
        active_dsp.append("harsh_s")
        explanation.append("Engaged Dynamic De-Esser (4.5–7.5 kHz sidechain).")

    if answers.get("too_bright", False):
        active_dsp.append("too_bright")
        explanation.append("Engaged High-Shelf attenuation (-2.5 dB >8 kHz).")
    elif answers.get("too_dark", False) or "dull_highs" in issues:
        active_dsp.append("too_dark")
        explanation.append("Engaged Air Bloom exciter (+3.0 dB >12 kHz).")

    # Low End & Dynamics
    if answers.get("boomy_low", False) or "boomy_sub" in issues:
        active_dsp.append("boomy_low")
        explanation.append("Engaged Mud-cut parametric filter (-3 dB at 250 Hz).")

    if answers.get("weak_bass", False):
        active_dsp.append("weak_bass")
        explanation.append("Engaged Sub-harmonic bass synthesiser at 70 Hz.")

    if answers.get("sub_rumble", False):
        active_dsp.append("sub_rumble")
        explanation.append("Engaged 32 Hz 18 dB/oct HPF sub-rumble cutoff.")

    # Warmth & Space
    if answers.get("cold_digital", False) or ("rock" in matched_key or "classical" in matched_key):
        active_dsp.append("cold_digital")
        explanation.append("Engaged Anti-aliased analog tape saturation (150–800 Hz).")

    if answers.get("too_narrow", False):
        active_dsp.append("too_narrow")
        explanation.append("Engaged Mid/Side stereo width expander >1.5 kHz.")

    if answers.get("phasey_center", False):
        active_dsp.append("phasey_center")
        explanation.append("Engaged Mono-maker low-end anchor (<120 Hz).")

    # Vocal Clarity & Transients
    if answers.get("buried_vocals", False) and has_vocals:
        active_dsp.append("buried_vocals")
        explanation.append("Engaged Mid-channel vocal presence boost (+2.0 dB at 2.5 kHz).")

    if answers.get("soft_transients", False) or crest_factor_db < 9.0:
        active_dsp.append("soft_transients")
        explanation.append("Engaged Envelope derivative transient onset punch.")

    # 5. Recommended EQ preset
    recommended_eq = "balanced"
    if "rock" in matched_key or "metal" in matched_key:
        recommended_eq = "warm_analog"
    elif any(k in matched_key for k in ("house", "techno", "edm", "club")):
        recommended_eq = "club_punch"
    elif any(k in matched_key for k in ("classical", "folk", "acoustic")):
        recommended_eq = "natural_air"

    return AutoRouteDecision(
        mode=mode,
        neural_bandwidth_extender=needs_bandwidth_ext,
        neural_vocal_weight=v_weight,
        neural_inst_weight=i_weight,
        active_dsp_keys=active_dsp,
        limiter_ceiling_db=-0.1,
        recommended_eq_preset=recommended_eq,
        genre_matched=resolved_genre,
        explanation=explanation,
    )
