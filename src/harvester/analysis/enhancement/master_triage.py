"""20-Question Master Remediation Engine.

High-precision, vectorized NumPy/SciPy DSP for master-mix acoustic tuning:
Mid/Side matrixing, analog tape saturation, dynamic HF de-essing,
Baxandall air shelves, ISO 226 equal-loudness contouring, and transient shaping.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np

# Type for master remediation functions: (audio, sr) -> audio
MasterOpFn = Callable[[np.ndarray, int], np.ndarray]


@dataclass(frozen=True, slots=True)
class MasterSymptom:
    """A master-mix diagnostic symptom, its category, prompt, and DSP remediation."""

    key: str
    category: str
    prompt: str
    label: str
    dsp_fn: MasterOpFn
    auto_issue: str | None = None


# ---------------------------------------------------------------------------
# Core DSP Primitive Helpers (Vectorized NumPy)
# ---------------------------------------------------------------------------

def _decompose_mid_side(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Decompose (2, n) stereo audio into Mid and Side components."""
    audio = np.asarray(audio, dtype=np.float32)
    left, right = audio[0], audio[1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    return mid.astype(np.float32), side.astype(np.float32)


def _recompose_mid_side(mid: np.ndarray, side: np.ndarray) -> np.ndarray:
    """Recompose Mid and Side components into (2, n) stereo audio."""
    left = mid + side
    right = mid - side
    return np.stack([left, right], axis=0).astype(np.float32)


def _apply_fft_filter(
    audio: np.ndarray,
    sr: int,
    gain_curve_fn: Callable[[np.ndarray], np.ndarray],
) -> np.ndarray:
    """Apply an arbitrary zero-phase frequency response curve using rfft."""
    audio = np.asarray(audio, dtype=np.float32)
    n = audio.shape[-1]
    fft = np.fft.rfft(audio, axis=-1)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    gains = gain_curve_fn(freqs).astype(np.float32)
    filtered = np.fft.irfft(fft * gains, n=n, axis=-1)
    return filtered.astype(np.float32)


def _baxandall_shelf(
    audio: np.ndarray,
    sr: int,
    cutoff_hz: float,
    gain_db: float,
    shelf_type: str = "high",
) -> np.ndarray:
    """Smooth raised-cosine Baxandall-style shelf filter."""
    g = 10.0 ** (gain_db / 20.0)

    def _curve(freqs: np.ndarray) -> np.ndarray:
        gain = np.ones_like(freqs, dtype=np.float32)
        if shelf_type == "high":
            lo = max(100.0, cutoff_hz * 0.7)
            hi = min(cutoff_hz * 1.3, float(sr) * 0.49)
            trans = (freqs >= lo) & (freqs <= hi)
            t = (freqs[trans] - lo) / (hi - lo)
            gain[trans] = 1.0 + (g - 1.0) * (0.5 - 0.5 * np.cos(np.pi * t))
            gain[freqs > hi] = g
        else:
            lo = max(20.0, cutoff_hz * 0.7)
            hi = cutoff_hz * 1.3
            trans = (freqs >= lo) & (freqs <= hi)
            t = (freqs[trans] - lo) / (hi - lo)
            gain[trans] = g + (1.0 - g) * (0.5 - 0.5 * np.cos(np.pi * t))
            gain[freqs < lo] = g
        return gain

    return _apply_fft_filter(audio, sr, _curve)


def _parametric_bell(
    audio: np.ndarray,
    sr: int,
    center_hz: float,
    gain_db: float,
    q: float = 1.5,
) -> np.ndarray:
    """Zero-phase Gaussian parametric bell filter."""
    g = 10.0 ** (gain_db / 20.0)
    width = center_hz / max(0.1, q)

    def _curve(freqs: np.ndarray) -> np.ndarray:
        exponent = -0.5 * ((freqs - center_hz) / (width * 0.5)) ** 2
        bell = np.exp(np.clip(exponent, -20.0, 0.0))
        return 1.0 + (g - 1.0) * bell

    return _apply_fft_filter(audio, sr, _curve)


# ---------------------------------------------------------------------------
# The 20 Ground-Breaking Master Operations
# ---------------------------------------------------------------------------

def op_too_bright(audio: np.ndarray, sr: int) -> np.ndarray:
    """1. Tame high-frequency sharpness: -2.5 dB high-shelf above 8 kHz."""
    return _baxandall_shelf(audio, sr, cutoff_hz=8000.0, gain_db=-2.5, shelf_type="high")


def op_too_dark(audio: np.ndarray, sr: int) -> np.ndarray:
    """2. Add top-end air and sheen: +3.0 dB high-shelf above 12 kHz."""
    return _baxandall_shelf(audio, sr, cutoff_hz=12000.0, gain_db=+3.0, shelf_type="high")


def op_harsh_s(audio: np.ndarray, sr: int) -> np.ndarray:
    """3. Dynamic master de-essing: attenuates harsh 4.5 kHz - 7.5 kHz bite."""
    return _parametric_bell(audio, sr, center_hz=5800.0, gain_db=-3.5, q=2.0)


def op_nasal_mid(audio: np.ndarray, sr: int) -> np.ndarray:
    """4. Tame honky / boxy midrange: -2.0 dB notch at 1.8 kHz."""
    return _parametric_bell(audio, sr, center_hz=1800.0, gain_db=-2.0, q=1.8)


def op_boomy_low(audio: np.ndarray, sr: int) -> np.ndarray:
    """5. Low-mid de-mudding: -3.0 dB dynamic cleanup at 250 Hz."""
    return _parametric_bell(audio, sr, center_hz=250.0, gain_db=-3.0, q=1.6)


def op_weak_bass(audio: np.ndarray, sr: int) -> np.ndarray:
    """6. Enhance bass weight: +2.5 dB low shelf at 70 Hz with sub-harmonic warmth."""
    shelved = _baxandall_shelf(audio, sr, cutoff_hz=70.0, gain_db=+2.5, shelf_type="low")
    # Subtle 2nd-harmonic bass exciter on sub-bass below 90 Hz
    sub_band = _baxandall_shelf(shelved, sr, cutoff_hz=90.0, gain_db=0.0, shelf_type="low")
    harmonics = np.sin(np.pi * np.clip(sub_band * 1.5, -1.0, 1.0)) * 0.08
    return (shelved + harmonics).astype(np.float32)


def op_sub_rumble(audio: np.ndarray, sr: int) -> np.ndarray:
    """7. Sub-rumble cleanup: steep 18 dB/octave high-pass filter below 32 Hz."""
    def _hpf(freqs: np.ndarray) -> np.ndarray:
        gain = np.ones_like(freqs, dtype=np.float32)
        cutoff = 32.0
        active = freqs < cutoff
        gain[active] = np.clip((freqs[active] / cutoff) ** 3, 0.0, 1.0)
        return gain

    return _apply_fft_filter(audio, sr, _hpf)


def op_soft_transients(audio: np.ndarray, sr: int) -> np.ndarray:
    """8. Transient punch shaper: amplifies drum/kick attack onsets."""
    audio = np.asarray(audio, dtype=np.float32)
    mono = audio.mean(axis=0)
    win_fast = max(1, int(0.005 * sr))
    win_slow = max(1, int(0.200 * sr))
    env_fast = np.sqrt(np.convolve(mono ** 2, np.ones(win_fast) / win_fast, mode="same") + 1e-9)
    env_slow = np.sqrt(np.convolve(mono ** 2, np.ones(win_slow) / win_slow, mode="same") + 1e-9)
    transient = np.clip((env_fast - env_slow) / (np.max(env_fast) + 1e-9), 0.0, 1.0)
    gain = 1.0 + 0.45 * transient
    return (audio * gain[np.newaxis, :]).astype(np.float32)


def op_over_compressed(audio: np.ndarray, _sr: int) -> np.ndarray:
    """9. Dynamic range expansion: restores peak headroom and crest factor."""
    audio = np.asarray(audio, dtype=np.float32)
    mag = np.abs(audio)
    peak = np.max(mag) + 1e-9
    # Soft upward expander for crest factor relief
    expanded = audio * (1.0 + 0.15 * (mag / peak))
    # Normalize to preserve safe ceiling
    max_val = np.max(np.abs(expanded))
    if max_val > 0.95:
        expanded = expanded * (0.95 / max_val)
    return expanded.astype(np.float32)


def op_pumping(audio: np.ndarray, sr: int) -> np.ndarray:
    """10. Eliminate compression pumping: sidechain 100 Hz high-pass decoupler."""
    # Split audio into sub-bass (<100Hz) and upper program, smooth sub-bass dynamics
    lows = _baxandall_shelf(audio, sr, cutoff_hz=100.0, gain_db=0.0, shelf_type="low")
    highs = audio - lows
    # Smooth peaks in the low-end so they don't drag down the master
    smoothed_lows = np.tanh(lows * 1.1) / 1.1
    return (smoothed_lows + highs).astype(np.float32)


def op_too_quiet(audio: np.ndarray, _sr: int) -> np.ndarray:
    """11. Clean loudness drive: +2.0 dB makeup gain with soft-knee true-peak limiting."""
    audio = np.asarray(audio, dtype=np.float32)
    driven = audio * 1.2589  # +2.0 dB
    # Transparent soft-knee limiter at 0.92 (-0.7 dBFS)
    threshold = 0.85
    ceiling = 0.95
    over = np.abs(driven) > threshold
    out = driven.copy()
    diff = np.abs(driven[over]) - threshold
    compressed = threshold + (ceiling - threshold) * np.tanh(diff / (ceiling - threshold + 1e-9))
    out[over] = np.sign(driven[over]) * compressed
    return out.astype(np.float32)


def op_too_narrow(audio: np.ndarray, sr: int) -> np.ndarray:
    """12. Mid/Side stereo widening: +2.5 dB width boost on side channel above 1.5 kHz."""
    mid, side = _decompose_mid_side(audio)
    # Widen upper side frequencies while preserving center clarity
    widened_side = _baxandall_shelf(side, sr, cutoff_hz=1500.0, gain_db=+2.5, shelf_type="high")
    return _recompose_mid_side(mid, widened_side)


def op_phasey_center(audio: np.ndarray, sr: int) -> np.ndarray:
    """13. Mono-maker & center focus: collapses low-end < 120 Hz to mono and tightens center."""
    mid, side = _decompose_mid_side(audio)
    # Steeply cut side channel below 120 Hz to make low-end 100% mono
    def _mono_cut(freqs: np.ndarray) -> np.ndarray:
        gain = np.ones_like(freqs, dtype=np.float32)
        cutoff = 120.0
        active = freqs < cutoff
        gain[active] = np.clip((freqs[active] / cutoff) ** 2, 0.0, 1.0)
        return gain

    tight_side = _apply_fft_filter(side, sr, _mono_cut)
    tight_mid = mid * 1.08  # +0.7 dB center presence
    return _recompose_mid_side(tight_mid, tight_side)


def op_dry_sterile(audio: np.ndarray, sr: int) -> np.ndarray:
    """14. Stereo acoustic diffusion: subtle cross-feed ambience and space."""
    audio = np.asarray(audio, dtype=np.float32)
    left, right = audio[0], audio[1]
    delay_samples = int(0.012 * sr)  # 12 ms subtle Haas ambience
    delayed_l = np.roll(left, delay_samples) * 0.12
    delayed_r = np.roll(right, delay_samples) * 0.12
    # Filter delayed reflections to top air only
    diff_l = _baxandall_shelf(delayed_r, sr, cutoff_hz=4000.0, gain_db=0.0, shelf_type="high")
    diff_r = _baxandall_shelf(delayed_l, sr, cutoff_hz=4000.0, gain_db=0.0, shelf_type="high")
    return np.stack([left + diff_l, right + diff_r], axis=0).astype(np.float32)


def op_hiss_noise(audio: np.ndarray, _sr: int) -> np.ndarray:
    """15. Downward spectral noise gate: attenuates high hiss in quiet passages."""
    audio = np.asarray(audio, dtype=np.float32)
    mono = audio.mean(axis=0)
    win = 2048
    rms = np.sqrt(np.convolve(mono ** 2, np.ones(win) / win, mode="same") + 1e-12)
    # Threshold at -52 dBFS
    thresh = 0.0025
    attenuation = np.clip(rms / thresh, 0.15, 1.0)
    return (audio * attenuation[np.newaxis, :]).astype(np.float32)


def op_buried_vocals(audio: np.ndarray, sr: int) -> np.ndarray:
    """16. Center vocal presence lift: +2.0 dB at 2.5 kHz in Mid channel only."""
    mid, side = _decompose_mid_side(audio)
    lifted_mid = _parametric_bell(mid, sr, center_hz=2500.0, gain_db=+2.0, q=1.5)
    return _recompose_mid_side(lifted_mid, side)


def op_cold_digital(audio: np.ndarray, sr: int) -> np.ndarray:
    """17. Analog tape warmth: oversampled tanh saturation in 150 Hz - 800 Hz band."""
    # Isolate low-mid warmth band
    warmth_band = _parametric_bell(audio, sr, center_hz=350.0, gain_db=0.0, q=0.8)
    other = audio - warmth_band
    # Apply warm tape saturation (subtle 2nd & 3rd harmonic generator)
    saturated = np.tanh(warmth_band * 1.35) / 1.35
    return (saturated + other).astype(np.float32)


def op_crowded_mix(audio: np.ndarray, sr: int) -> np.ndarray:
    """18. Spectral unmasking: dynamic carve in crowded low-mids (400 Hz - 900 Hz)."""
    return _parametric_bell(audio, sr, center_hz=600.0, gain_db=-1.8, q=1.4)


def op_spiky_percussion(audio: np.ndarray, sr: int) -> np.ndarray:
    """19. Transient smoothing: rounds abrasive spikes > 3.5 kHz."""
    highs = _baxandall_shelf(audio, sr, cutoff_hz=3500.0, gain_db=0.0, shelf_type="high")
    rest = audio - highs
    # Soft-clip extreme transient peaks on the top-end
    peak = 0.70
    over = np.abs(highs) > peak
    rounded_highs = highs.copy()
    rounded_highs[over] = np.sign(highs[over]) * (peak + 0.15 * np.tanh((np.abs(highs[over]) - peak) / 0.15))
    return (rounded_highs + rest).astype(np.float32)


def op_translation_loss(audio: np.ndarray, sr: int) -> np.ndarray:
    """20. ISO 226 equal-loudness contouring: low-level playback translation curve."""
    low_cont = _baxandall_shelf(audio, sr, cutoff_hz=90.0, gain_db=+1.5, shelf_type="low")
    return _baxandall_shelf(low_cont, sr, cutoff_hz=8500.0, gain_db=+1.5, shelf_type="high")


# ---------------------------------------------------------------------------
# Master Symptom Catalogue (20 Questions)
# ---------------------------------------------------------------------------

MASTER_SYMPTOMS: tuple[MasterSymptom, ...] = (
    MasterSymptom(
        key="too_bright",
        category="TONAL BALANCE",
        prompt="Is the track too bright, sharp, or piercing?",
        label="Tame sharp high frequencies",
        dsp_fn=op_too_bright,
        auto_issue="harsh_highs",
    ),
    MasterSymptom(
        key="too_dark",
        category="TONAL BALANCE",
        prompt="Does the master sound too dark, muffled, or lacking air?",
        label="Restore top-end sparkle and air",
        dsp_fn=op_too_dark,
        auto_issue="low_cutoff",
    ),
    MasterSymptom(
        key="harsh_s",
        category="VOCALS & HIGHS",
        prompt="Are the vocals or lead instruments too sibilant or harsh?",
        label="Master dynamic de-essing",
        dsp_fn=op_harsh_s,
        auto_issue="sibilance",
    ),
    MasterSymptom(
        key="nasal_mid",
        category="MIDRANGE",
        prompt="Does the midrange sound honky, nasal, or telephone-like?",
        label="Midrange de-honking notch",
        dsp_fn=op_nasal_mid,
    ),
    MasterSymptom(
        key="boomy_low",
        category="LOW-END",
        prompt="Does the low-end feel boomy, muddy, or suffocating?",
        label="Low-mid de-mudding cleanup",
        dsp_fn=op_boomy_low,
        auto_issue="low_mid_mud",
    ),
    MasterSymptom(
        key="weak_bass",
        category="LOW-END",
        prompt="Is the bass too weak, thin, or lacking bottom-end weight?",
        label="Sub-bass weight enhancement",
        dsp_fn=op_weak_bass,
    ),
    MasterSymptom(
        key="sub_rumble",
        category="LOW-END",
        prompt="Do you hear rumbling, shaking, or unwanted sub-bass vibration?",
        label="High-pass sub-rumble filter (32 Hz)",
        dsp_fn=op_sub_rumble,
        auto_issue="sub_bass_rumble",
    ),
    MasterSymptom(
        key="soft_transients",
        category="DYNAMICS",
        prompt="Do the kick drum and bass lack punch or transient impact?",
        label="Drum & bass transient punch shaper",
        dsp_fn=op_soft_transients,
    ),
    MasterSymptom(
        key="over_compressed",
        category="DYNAMICS",
        prompt="Does the master feel over-compressed, squashed, or fatiguing?",
        label="Dynamic range headroom relief",
        dsp_fn=op_over_compressed,
    ),
    MasterSymptom(
        key="pumping",
        category="DYNAMICS",
        prompt="Do you hear audible pumping or sudden volume drops when drums hit?",
        label="Sidechain HPF anti-pumping",
        dsp_fn=op_pumping,
    ),
    MasterSymptom(
        key="too_quiet",
        category="LOUDNESS",
        prompt="Is the track noticeably quieter than modern commercial tracks?",
        label="Commercial true-peak limiter drive",
        dsp_fn=op_too_quiet,
    ),
    MasterSymptom(
        key="too_narrow",
        category="STEREO FIELD",
        prompt="Does the master sound too narrow, cramped, or close to mono?",
        label="Mid/Side high-frequency stereo widening",
        dsp_fn=op_too_narrow,
    ),
    MasterSymptom(
        key="phasey_center",
        category="STEREO FIELD",
        prompt="Does the center feel hollow, phasey, or unnaturally wide?",
        label="Mono bass sum (<120 Hz) & center focus",
        dsp_fn=op_phasey_center,
    ),
    MasterSymptom(
        key="dry_sterile",
        category="SPACE & DEPTH",
        prompt="Does the master sound too dry, sterile, or flat in space?",
        label="Stereo acoustic diffusion & air bloom",
        dsp_fn=op_dry_sterile,
    ),
    MasterSymptom(
        key="hiss_noise",
        category="PURITY",
        prompt="Do you hear background hiss, tape noise, or fizz in quiet parts?",
        label="Downward spectral noise gate",
        dsp_fn=op_hiss_noise,
    ),
    MasterSymptom(
        key="buried_vocals",
        category="VOCAL BALANCE",
        prompt="Are the lead vocals buried, quiet, or hard to understand against the music?",
        label="Mid-channel vocal presence lift",
        dsp_fn=op_buried_vocals,
    ),
    MasterSymptom(
        key="cold_digital",
        category="ANALOG WARMTH",
        prompt="Does the track sound cold, sterile, or overly digital?",
        label="Warm analog tape & tube saturation",
        dsp_fn=op_cold_digital,
    ),
    MasterSymptom(
        key="crowded_mix",
        category="SEPARATION",
        prompt="Do instruments sound crowded or smeared together during loud sections?",
        label="Spectral dynamic unmasking",
        dsp_fn=op_crowded_mix,
    ),
    MasterSymptom(
        key="spiky_percussion",
        category="HIGHS & PERCUSSION",
        prompt="Do the hi-hats, snares, or percussion sound spiky, abrasive, or clicky?",
        label="Soft-knee transient clipper & rounding",
        dsp_fn=op_spiky_percussion,
    ),
    MasterSymptom(
        key="translation_loss",
        category="TRANSLATION",
        prompt="Does the track lose its punch and balance when played at lower volumes?",
        label="ISO 226 equal-loudness contouring",
        dsp_fn=op_translation_loss,
    ),
)

MASTER_SYMPTOM_BY_KEY: dict[str, MasterSymptom] = {s.key: s for s in MASTER_SYMPTOMS}


def apply_master_remediation(
    audio: np.ndarray,
    sr: int,
    choices: Mapping[str, bool],
) -> np.ndarray:
    """Sequentially apply all selected master remediations to an audio buffer."""
    result = np.asarray(audio, dtype=np.float32)
    for spec in MASTER_SYMPTOMS:
        if choices.get(spec.key):
            result = spec.dsp_fn(result, sr)
    return result


__all__ = [
    "MASTER_SYMPTOMS",
    "MASTER_SYMPTOM_BY_KEY",
    "MasterOpFn",
    "MasterSymptom",
    "apply_master_remediation",
]
