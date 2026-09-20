"""
Acoustic Music & Vocal Presence Detector for OmniRip.

Performs high-speed spectral, harmonic, and mid/side acoustic analysis on audio
to detect vocal presence, detect pure instrumental tracks, diagnose acoustic
defects (sub-rumble, low-mid mud, synth bleed), and auto-tune stem separation
and defect remediation parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class AcousticAnalysisResult:
    """Diagnostic telemetry and auto-tuning recommendations from acoustic analysis."""

    has_vocals: bool
    vocal_confidence: float  # 0.0 to 1.0
    is_pure_instrumental: bool
    detected_issues: list[str] = field(default_factory=list)
    recommended_vocal_flags: set[str] = field(default_factory=set)
    recommended_inst_flags: set[str] = field(default_factory=set)
    recommended_blend_weight: float = 0.70
    recommended_engine: str = "ensemble"
    summary: str = ""


def analyze_track_acoustics(
    audio: np.ndarray,
    sr: int,
) -> AcousticAnalysisResult:
    """
    Perform fast acoustic and vocal-presence analysis on 2D audio (channels, samples).

    Analyzes:
    1. Vocal Core (300 Hz - 3500 Hz) mid/side energy concentration & harmonicity.
    2. Sub-bass rumble (<35 Hz) for subsonic filter recommendation.
    3. Low-mid boxiness (250 Hz - 350 Hz) for de-mud filter recommendation.
    4. Side-channel synth energy overlapping vocal band for anti-bleed recommendation.
    5. High-frequency sibilance (5.5 kHz - 8.5 kHz) for de-esser recommendation.
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)

    n_channels, n_samples = audio.shape
    if n_samples < 2048 or sr <= 0:
        return AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.50,
            is_pure_instrumental=False,
            summary="Audio too short for acoustic fingerprinting; default studio settings applied.",
        )

    # Subsample for blazing fast analysis (<50ms even on 10-minute audio tracks)
    max_analysis_samples = 44100 * 60 * 3  # Up to 3 minutes
    if n_samples > max_analysis_samples:
        step = n_samples // max_analysis_samples
        work_audio = audio[:, ::step]
    else:
        work_audio = audio

    w_samples = work_audio.shape[1]
    left = work_audio[0].astype(np.float32)
    right = work_audio[1].astype(np.float32)

    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)

    # Compute FFT
    freqs = np.fft.rfftfreq(w_samples, d=1.0 / sr)
    mid_fft = np.abs(np.fft.rfft(mid))
    side_fft = np.abs(np.fft.rfft(side))
    total_fft = mid_fft + side_fft + 1e-9

    # Frequency Bands
    sub_mask = (freqs >= 10.0) & (freqs < 35.0)
    low_mid_mask = (freqs >= 250.0) & (freqs <= 350.0)
    vocal_core_mask = (freqs >= 300.0) & (freqs <= 3500.0)
    sibilance_mask = (freqs >= 5500.0) & (freqs <= 8500.0)
    total_mask = freqs >= 20.0

    total_energy = float(np.sum(total_fft[total_mask] ** 2)) + 1e-9
    mid_vocal_energy = float(np.sum(mid_fft[vocal_core_mask] ** 2))
    side_vocal_energy = float(np.sum(side_fft[vocal_core_mask] ** 2))

    # Vocal Presence Metric:
    # Vocals in modern production are predominantly center-panned (mid channel) in the 300-3500 Hz formant band.
    # We measure both the mid-to-total ratio in the vocal band and the mid-to-side dominance, gated by vocal band share.
    vocal_band_total = mid_vocal_energy + side_vocal_energy + 1e-9
    mid_dominance = mid_vocal_energy / vocal_band_total
    vocal_band_share = (mid_vocal_energy + side_vocal_energy) / total_energy

    # Spectral peakiness / harmonic prominence in vocal core:
    vocal_mags = mid_fft[vocal_core_mask]
    geometric_mean = float(np.exp(np.mean(np.log(vocal_mags + 1e-9))))
    arithmetic_mean = float(np.mean(vocal_mags)) + 1e-9
    spectral_flatness = geometric_mean / arithmetic_mean  # lower = more tonal/harmonic (voices/instruments)

    # Vocal confidence computation (0.0 to 1.0)
    # Voices have high mid-dominance (center panned), high energy in 300-3500Hz, and low spectral flatness (strong harmonics).
    # If the track has virtually no energy in 300-3500Hz, gate confidence to 0.
    vocal_energy_gate = float(np.clip(vocal_band_share * 10.0, 0.0, 1.0))
    tonality = float(np.clip(1.0 - spectral_flatness, 0.0, 1.0))
    raw_confidence = (
        (mid_dominance * 0.45)
        + (min(1.0, vocal_band_share * 3.5) * 0.35)
        + (tonality * 0.20)
    ) * vocal_energy_gate
    confidence = float(np.clip(raw_confidence, 0.0, 1.0))

    has_vocals = confidence >= 0.25
    is_pure_instrumental = confidence < 0.18

    # Diagnostic Defect Detection:
    detected_issues: list[str] = []
    rec_v_flags: set[str] = set()
    rec_i_flags: set[str] = set()

    # 1. Sub-bass rumble detection (<35 Hz)
    sub_energy = float(np.sum(total_fft[sub_mask] ** 2))
    if (sub_energy / total_energy) > 0.08:
        detected_issues.append("sub_bass_rumble")
        rec_i_flags.add("sub_bass_clean")

    # 2. Low-mid boxiness / mud detection (250 - 350 Hz)
    mud_energy = float(np.sum(total_fft[low_mid_mask] ** 2))
    if (mud_energy / total_energy) > 0.18:
        detected_issues.append("low_mid_mud")
        rec_i_flags.add("de_mud")

    # 3. Dense stereo synths / side bleed in vocal range
    if side_vocal_energy / vocal_band_total > 0.45:
        detected_issues.append("synth_bleed")
        rec_i_flags.add("anti_bleed_synths")
        rec_v_flags.add("de_bleed")

    # 4. Sibilance harshness in 5.5 - 8.5 kHz
    sib_energy = float(np.sum(total_fft[sibilance_mask] ** 2))
    if (sib_energy / total_energy) > 0.14:
        detected_issues.append("sibilance")
        rec_v_flags.add("de_ess")

    # Always recommend smooth pumping fix & adaptive VAD gate for vocal separation if vocals present
    if has_vocals:
        rec_v_flags.add("fix_pumping")
        rec_v_flags.add("vad_gate")
        rec_i_flags.add("kill_whispers")

    # Determine recommended engine & summary
    if is_pure_instrumental:
        rec_engine = "eco"
        summary = (
            f"Pure Instrumental Detected ({int((1.0 - confidence) * 100)}% certainty). "
            "Minimal vocal extraction recommended to preserve musical dynamics."
        )
    else:
        rec_engine = "ensemble"
        issues_str = ", ".join(detected_issues) if detected_issues else "None (Clean Production)"
        summary = (
            f"Vocal Track Detected ({int(confidence * 100)}% confidence). "
            f"Acoustic issues detected: {issues_str}. Optimal remediation profile applied."
        )

    blend_weight = 0.0 if is_pure_instrumental else 0.70

    return AcousticAnalysisResult(
        has_vocals=has_vocals,
        vocal_confidence=confidence,
        is_pure_instrumental=is_pure_instrumental,
        detected_issues=detected_issues,
        recommended_vocal_flags=rec_v_flags,
        recommended_inst_flags=rec_i_flags,
        recommended_blend_weight=blend_weight,
        recommended_engine=rec_engine,
        summary=summary,
    )
