"""Repair ops: apply defect fixes to arbitrary time ranges of a stereo file.

The guided Repair flow (docs/01 D35) replaces per-second layer editing with
plain time ranges: each symptom maps to one DSP operation applied to the
vocals and/or instrumental stem, whole-track or over the sections the user
picked. Whole-track rendering calls the operation once; ranged rendering
slices the file, renders each window and equal-power crossfades the edges so
the result stays click-free.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.segment_analysis import (
    MUD_BAND,
    SEGMENT_SIZE_S,
    SIBILANCE_BAND,
    VOCAL_CORE_BAND,
)

FADE_MS: float = 20.0
LIMITER_CEILING_DBFS: float = -1.0
DE_BLEED_ATTEN_DB: float = -24.0
DE_ESS_ATTEN_DB: float = -14.0
DE_MUD_ATTEN_DB: float = -10.0
DE_HUM_ATTEN_DB: float = -18.0
RECONSTRUCTION_BUDGET_DB: float = -40.0
Range = tuple[float, float]
SegmentFn = Callable[[np.ndarray, int], np.ndarray]

MIN_WINDOW_S: float = 0.10
MERGE_GAP_S: float = 0.25


def normalise_ranges(
    ranges: Iterable[Range],
    duration_s: float,
    *,
    merge_gap_s: float = MERGE_GAP_S,
    min_window_s: float = MIN_WINDOW_S,
) -> list[Range]:
    """Sort, clamp and merge user ranges into a clean, non-overlapping list."""
    cleaned: list[Range] = []
    for raw in ranges:
        try:
            t0, t1 = float(raw[0]), float(raw[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not (np.isfinite(t0) and np.isfinite(t1)) or t1 <= t0:
            continue
        t0 = max(0.0, t0)
        t1 = min(float(duration_s), t1)
        if t1 - t0 < min_window_s:
            continue
        cleaned.append((t0, t1))
    cleaned.sort(key=lambda item: item[0])
    merged: list[Range] = []
    for t0, t1 in cleaned:
        if merged and t0 <= merged[-1][1] + merge_gap_s:
            merged[-1] = (merged[-1][0], max(merged[-1][1], t1))
        else:
            merged.append((t0, t1))
    return merged


def render_ranges(
    audio: np.ndarray,
    sr: int,
    ranges: Iterable[Range] | None,
    fn: SegmentFn,
    *,
    fade_ms: float = FADE_MS,
) -> np.ndarray:
    """Apply ``fn`` to ``ranges`` (None/empty = whole track) of a (2, n) signal."""
    source = np.asarray(audio, dtype=np.float32)
    if ranges is None:
        return np.asarray(fn(source, sr), dtype=np.float32)

    windows = normalise_ranges(ranges, source.shape[1] / float(sr))
    if not windows:
        return np.asarray(fn(source, sr), dtype=np.float32)

    out = source.copy()
    for t0, t1 in windows:
        start = max(0, int(round(t0 * sr)))
        end = min(out.shape[1], int(round(t1 * sr)))
        if end - start < 32:
            continue
        original = out[:, start:end]
        edited = np.asarray(fn(original, sr), dtype=np.float32)
        edited = _crossfade_edges(original, edited, sr, fade_ms)
        out[:, start:end] = edited
    return out


def load_stereo(path: Path) -> tuple[np.ndarray, int]:
    """Load an audio file as (channels, samples) float32; stereo is preserved."""
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.T, int(sr)


def write_pcm32(audio: np.ndarray, path: Path, sr: int) -> Path:
    """Write 32-bit PCM with the -1 dBFS ceiling."""
    return save_pcm32(audio, path, sr)


def verify_reconstruction(
    reference_mix: np.ndarray,
    layer_files: dict[str, Path],
    sample_rate: int = 44100,
    budget_db: float = RECONSTRUCTION_BUDGET_DB,
) -> tuple[float, list[int]]:
    """Worst per-second residual of the reconstructed mix vs the source mix."""
    per_seg = mix_residual_db(
        reference_mix,
        reconstruct_mix(layer_files, sample_rate=sample_rate),
        sample_rate=sample_rate,
    )
    worst = float(np.max(per_seg)) if per_seg.size else float("-inf")
    violating = [int(i) for i, value in enumerate(per_seg) if value > budget_db]
    return worst, violating


def op_de_bleed(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "de_bleed", sr)


def op_de_ess(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "de_ess", sr)


def op_de_mud(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "de_mud", sr)


def op_de_hum(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "de_hum", sr)


def op_de_click(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "de_click", sr)


def op_air_boost(segment: np.ndarray, sr: int) -> np.ndarray:
    return apply_op(segment, "air_boost", sr)


def op_fix_pumping(segment: np.ndarray, sr: int) -> np.ndarray:
    from harvester.analysis.enhancement.stem_separator import apply_adaptive_spectral_gate

    return apply_adaptive_spectral_gate(segment, sr, profile="fix_pumping")


def op_kill_whispers(segment: np.ndarray, sr: int) -> np.ndarray:
    from harvester.analysis.enhancement.stem_separator import apply_mid_side_vocal_suppression

    return apply_mid_side_vocal_suppression(segment, sr, profile="kill_whispers")


def make_dereverb_op(intensity: float) -> SegmentFn:
    """Dereverb op factory: keeps only the dry half of the isolation split."""

    def _op(segment: np.ndarray, sr: int) -> np.ndarray:
        from harvester.analysis.enhancement.stem_separator import _apply_dereverb_isolation

        dry, _reverb = _apply_dereverb_isolation(segment, sr, intensity=float(intensity))
        return dry

    return _op


def _apply_band_attenuation(
    audio: np.ndarray, sr: int, band: tuple[float, float], attenuation_db: float
) -> np.ndarray:
    """Zero-phase FFT band attenuation with raised-cosine edges."""
    audio = np.asarray(audio, dtype=np.float32)
    n = audio.shape[1]
    fft = np.fft.rfft(audio, axis=1)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    lo, hi = band
    width = max(50.0, (hi - lo) * 0.15)
    gain = np.ones(freqs.shape[0], dtype=np.float32)
    g = 10.0 ** (attenuation_db / 20.0)

    in_band = (freqs >= lo + width) & (freqs <= hi - width)
    gain[in_band] = g

    left = (freqs >= lo - width) & (freqs < lo + width)
    t = (freqs[left] - (lo - width)) / (2.0 * width)
    gain[left] = 1.0 + (g - 1.0) * t

    right = (freqs > hi - width) & (freqs <= hi + width)
    t = (freqs[right] - (hi - width)) / (2.0 * width)
    gain[right] = g + (1.0 - g) * t

    return np.fft.irfft(fft * gain, n=n, axis=1).astype(np.float32)


def apply_drum_punch(segment: np.ndarray, sr: int, amount: float = 0.6) -> np.ndarray:
    """Transient emphasis: boost onsets above a slow-running average envelope."""
    segment = np.asarray(segment, dtype=np.float32)
    n = segment.shape[1]
    mono = segment.mean(axis=0)

    win = max(1, int(0.005 * sr))
    env = np.sqrt(
        np.convolve(mono.astype(np.float64) ** 2, np.ones(win, dtype=np.float64) / win, mode="same")
        + 1e-9
    )
    swin = max(1, int(0.25 * sr))
    slow = np.convolve(env, np.ones(swin, dtype=np.float64) / swin, mode="same")

    boost = np.clip((env - slow) / (float(np.max(env)) + 1e-9), 0.0, 1.0)
    gain = 1.0 + amount * boost
    k = max(1, int(0.002 * sr))
    gain = np.convolve(gain, np.ones(k, dtype=np.float64) / k, mode="same")
    if gain.shape[0] != n:
        gain = gain[:n]
    return (segment * gain.astype(np.float32)[np.newaxis, :]).astype(np.float32)


def apply_de_hum(segment: np.ndarray, sr: int) -> np.ndarray:
    """De-hum / sub-cut: attenuate low-end AC hum (50/60Hz) and sub-rumble below 120Hz."""
    return _apply_band_attenuation(segment, sr, (30.0, 120.0), DE_HUM_ATTEN_DB)


def apply_air_boost(segment: np.ndarray, sr: int, boost_db: float = 4.0) -> np.ndarray:
    """High-frequency air presence sheen above 10 kHz with raised-cosine shelf."""
    audio = np.asarray(segment, dtype=np.float32)
    n = audio.shape[1]
    fft = np.fft.rfft(audio, axis=1)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    g = 10.0 ** (boost_db / 20.0)
    lo, hi = 10000.0, 14000.0
    gain = np.ones(freqs.shape[0], dtype=np.float32)
    ramp = (freqs >= lo) & (freqs < hi)
    t = (freqs[ramp] - lo) / (hi - lo)
    gain[ramp] = 1.0 + (g - 1.0) * (0.5 - 0.5 * np.cos(np.pi * t))
    gain[freqs >= hi] = g
    return np.fft.irfft(fft * gain, n=n, axis=1).astype(np.float32)


def apply_de_click(segment: np.ndarray, sr: int) -> np.ndarray:
    """De-click: transient impulse and vinyl glitch detection and interpolation."""
    out = np.asarray(segment, dtype=np.float32).copy()
    for ch in range(out.shape[0]):
        diff = np.diff(out[ch], prepend=out[ch, 0])
        med = float(np.median(diff))
        mad = float(np.median(np.abs(diff - med))) + 1e-7
        spikes = np.where(np.abs(diff - med) > 6.0 * mad)[0]
        for idx in spikes:
            left = max(0, idx - 2)
            right = min(out.shape[1] - 1, idx + 2)
            out[ch, idx] = 0.5 * (out[ch, left] + out[ch, right])
    return out


def apply_noise_gate(
    segment: np.ndarray, sr: int, threshold_db: float = -38.0, max_cut_db: float = 24.0
) -> np.ndarray:
    """Noise gate / silence floor: soft downward expansion for low-level pause noise."""
    segment = np.asarray(segment, dtype=np.float32)
    n = segment.shape[1]
    mono = segment.mean(axis=0)
    win = max(1, int(0.01 * sr))
    rms = np.sqrt(
        np.convolve(mono.astype(np.float64) ** 2, np.ones(win, dtype=np.float64) / win, mode="same")
        + 1e-9
    )
    rms_db = 20.0 * np.log10(np.maximum(rms, 1e-6))
    diff = np.maximum(0.0, threshold_db - rms_db)
    att_db = np.clip(diff * 2.0, 0.0, max_cut_db)
    gain = 10.0 ** (-att_db / 20.0)
    smooth_win = max(1, int(0.005 * sr))
    gain = np.convolve(gain, np.ones(smooth_win, dtype=np.float64) / smooth_win, mode="same")
    if gain.shape[0] != n:
        gain = gain[:n]
    return (segment * gain.astype(np.float32)[np.newaxis, :]).astype(np.float32)


def apply_transient_tame(segment: np.ndarray, sr: int, ceiling: float = 0.70) -> np.ndarray:
    """Transient tamer: soft tanh saturation limiting of harsh peaks above ceiling."""
    audio = np.asarray(segment, dtype=np.float32)
    peak = np.maximum(np.abs(audio), 1e-9)
    mask = peak > ceiling
    out = audio.copy()
    margin = max(1e-5, 1.0 - ceiling)
    out[mask] = np.sign(audio[mask]) * (ceiling + margin * np.tanh((peak[mask] - ceiling) / margin))
    return out.astype(np.float32)


def apply_op(segment: np.ndarray, op: str, sr: int) -> np.ndarray:
    """Apply one per-cell operation to a single segment window."""
    if op == "mute":
        return np.zeros_like(segment, dtype=np.float32)
    if op == "de_bleed":
        return _apply_band_attenuation(segment, sr, VOCAL_CORE_BAND, DE_BLEED_ATTEN_DB)
    if op == "de_ess":
        return _apply_band_attenuation(segment, sr, SIBILANCE_BAND, DE_ESS_ATTEN_DB)
    if op == "de_mud":
        return _apply_band_attenuation(segment, sr, MUD_BAND, DE_MUD_ATTEN_DB)
    if op == "drum_punch":
        return apply_drum_punch(segment, sr)
    if op == "de_hum":
        return apply_de_hum(segment, sr)
    if op == "air_boost":
        return apply_air_boost(segment, sr)
    if op == "de_click":
        return apply_de_click(segment, sr)
    if op == "noise_gate":
        return apply_noise_gate(segment, sr)
    if op == "transient_tame":
        return apply_transient_tame(segment, sr)
    raise ValueError(f"Unknown edit op: {op!r}")


def _crossfade_edges(
    original: np.ndarray, edited: np.ndarray, sr: int, fade_ms: float = FADE_MS
) -> np.ndarray:
    """Equal-power (cos^2/sin^2) 20 ms crossfade at both edges of the window."""
    fade_n = max(1, min(int(fade_ms / 1000.0 * sr), edited.shape[1] // 2))
    out = edited.copy()
    if fade_n <= 0 or fade_n * 2 >= edited.shape[1]:
        return out

    x = np.linspace(0.0, np.pi / 2.0, fade_n)
    g_in = np.cos(x) ** 2  # original -> edited
    g_ed = np.sin(x) ** 2

    out[:, :fade_n] = original[:, :fade_n] * g_in[np.newaxis, :] + edited[:, :fade_n] * g_ed[
        np.newaxis, :
    ]
    out[:, -fade_n:] = edited[:, -fade_n:] * g_in[np.newaxis, :] + original[:, -fade_n:] * g_ed[
        np.newaxis, :
    ]
    return out


def save_pcm32(audio: np.ndarray, path: Path, sample_rate: int) -> Path:
    """Write 32-bit PCM WAV with a final -1 dBFS soft ceiling."""
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    out = np.clip(audio, -1.0, 1.0).astype(np.float32)
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 10.0 ** (LIMITER_CEILING_DBFS / 20.0):
        out = out * (10.0 ** (LIMITER_CEILING_DBFS / 20.0) / peak)
    data = out.T if out.ndim == 2 else out
    sf.write(str(path), data, sample_rate, subtype="PCM_32")
    return path


def reconstruct_mix(layer_files: dict[str, Path], sample_rate: int = 44100) -> np.ndarray:
    """Invert the layered mix: sum all per-layer files into one mono mix.

    Because every per-source layer is the LR4 recombination of its two raw
    sources and the LR4 crossover is linear, the sum of the four layer files is
    exactly the full mix the user auditions (up to float32/PCM rounding).
    """
    import soundfile as sf

    mix: np.ndarray | None = None
    n_reference = 0
    for name in sorted(layer_files):
        path = layer_files[name]
        if not (path.exists() and path.stat().st_size > 44):
            continue
        data, _file_sr = sf.read(str(path), dtype="float32", always_2d=True)
        if mix is None:
            mix = np.zeros(data.shape[0], dtype=np.float64)
            n_reference = data.shape[0]
        audio = data.T
        width = min(n_reference, audio.shape[1])
        mix[:width] += audio[:, :width].mean(axis=0).astype(np.float64)
    if mix is None:
        return np.zeros(0, dtype=np.float32)
    return mix.astype(np.float32)


def mix_residual_db(
    reference_mix: np.ndarray,
    test_mix: np.ndarray,
    sample_rate: int = 44100,
    segment_size_s: float = SEGMENT_SIZE_S,
) -> np.ndarray:
    """Per-second reconstruction residual of ``test_mix`` vs ``reference_mix``.

    Returns one RMS residual value per 1-second segment, in dBFS
    (20*log10 of the RMS of the difference). -inf means sample-identical.
    """
    n = min(reference_mix.shape[0], test_mix.shape[0])
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    ref = reference_mix[:n].astype(np.float64)
    test = test_mix[:n].astype(np.float64)
    seg_len = int(segment_size_s * sample_rate)
    n_segments = max(1, n // seg_len)
    usable = n_segments * seg_len
    diff = test[:usable] - ref[:usable]
    segs = diff.reshape(n_segments, seg_len)
    rms = np.sqrt(np.mean(segs**2, axis=1) + 1e-12)
    return (20.0 * np.log10(np.maximum(rms, 1e-6))).astype(np.float32)


def verify_mix_residual(
    reference_mix: np.ndarray,
    test_mix: np.ndarray,
    sample_rate: int = 44100,
    segment_size_s: float = SEGMENT_SIZE_S,
    budget_db: float = RECONSTRUCTION_BUDGET_DB,
) -> tuple[np.ndarray, float, list[int]]:
    """Verify the mix-reconstruction error budget.

    Returns ``(per_segment_db, worst_db, violating_indices)`` where a segment
    violates the budget when its residual sits above ``budget_db``.
    """
    per_seg = mix_residual_db(
        reference_mix, test_mix, sample_rate=sample_rate, segment_size_s=segment_size_s
    )
    worst = float(np.max(per_seg)) if per_seg.size else float("-inf")
    violating = [int(i) for i, v in enumerate(per_seg) if v > budget_db]
    return per_seg, worst, violating

__all__ = [
    "FADE_MS",
    "MIN_WINDOW_S",
    "MERGE_GAP_S",
    "Range",
    "SegmentFn",
    "load_stereo",
    "make_dereverb_op",
    "normalise_ranges",
    "op_air_boost",
    "op_de_bleed",
    "op_de_click",
    "op_de_ess",
    "op_de_hum",
    "op_de_mud",
    "op_fix_pumping",
    "op_kill_whispers",
    "reconstruct_mix",
    "render_ranges",
    "verify_reconstruction",
    "write_pcm32",
]
