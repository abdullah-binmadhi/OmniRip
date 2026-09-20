"""
Layer Studio Editor — per-second surgical stem editing (M2).

Non-destructive edit plan over the Layer Studio timeline: each cell edit is a
small structured op (mute / de_bleed / de_ess / de_mud / drum_punch / reset)
applied to one fixed 1-second window of one layer's WAV. Edits never touch the
raw neural cache; they ride on the blended per-layer files and are committed
with ~20 ms equal-power crossfades at segment boundaries so neighbours stay
click-free and (sample-)identical. Export runs a soft-knee limiter at -1 dBFS
and writes 32-bit PCM so nothing clips.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.dsp import apply_limiter
from harvester.analysis.enhancement.layers import (
    MUD_BAND,
    SEGMENT_SIZE_S,
    SIBILANCE_BAND,
    VOCAL_CORE_BAND,
    LayerTrack,
    build_layer_track,
)

logger = logging.getLogger(__name__)

FADE_MS: float = 20.0
LIMITER_CEILING_DBFS: float = -1.0

# Band-attack depths per op. DE_BLEED is ≥24 dB so a committed de-bleed cell
# (injected vocal-band leakage) demonstrably drops ≥20 dB residual — the M3
# acceptance threshold — even past raised-cosine edge rounding and dithering.
DE_BLEED_ATTEN_DB: float = -24.0
DE_ESS_ATTEN_DB: float = -14.0
DE_MUD_ATTEN_DB: float = -10.0
DE_HUM_ATTEN_DB: float = -18.0

# Mix reconstruction residual budget (dBFS) for verify_mix_residual.
RECONSTRUCTION_BUDGET_DB: float = -40.0

# Available per-cell operations (the Layer Studio action menu)
OPS: tuple[str, ...] = (
    "mute",
    "de_bleed",
    "de_ess",
    "de_mud",
    "drum_punch",
    "de_hum",
    "air_boost",
    "de_click",
    "noise_gate",
    "transient_tame",
    "reset",
)

OP_LABELS: dict[str, str] = {
    "mute": "Mute",
    "de_bleed": "De-bleed",
    "de_ess": "De-ess",
    "de_mud": "De-mud",
    "drum_punch": "Drum-punch",
    "de_hum": "De-hum",
    "air_boost": "Air-boost",
    "de_click": "De-click",
    "noise_gate": "Noise-gate",
    "transient_tame": "Transient-tame",
    "reset": "Reset",
}

OP_KEYS: dict[str, str] = {
    "m": "mute",
    "b": "de_bleed",
    "s": "de_ess",
    "u": "de_mud",
    "p": "drum_punch",
    "h": "de_hum",
    "a": "air_boost",
    "c": "de_click",
    "g": "noise_gate",
    "t": "transient_tame",
    "r": "reset",
}


@dataclass
class EditPlan:
    """Non-destructive set of per-cell edits keyed by (layer, segment_idx).

    A `reset` op removes the cell's entry so the original blended audio is
    restored. Re-rendering always starts from the on-disk blended layer file.
    """

    edits: dict[tuple[str, int], str] = field(default_factory=dict)

    def add(self, layer: str, segment_idx: int, op: str) -> None:
        if op == "reset":
            self.edits.pop((layer, segment_idx), None)
            return
        if op not in OPS:
            raise ValueError(f"Unknown edit op: {op!r}")
        if self.edits.get((layer, segment_idx)) == op:
            del self.edits[(layer, segment_idx)]  # toggle off
            return
        self.edits[(layer, segment_idx)] = op

    def get(self, layer: str, segment_idx: int) -> str | None:
        return self.edits.get((layer, segment_idx))

    def clear(self) -> None:
        self.edits.clear()

    def cells(self) -> list[tuple[str, int, str]]:
        return sorted((layer, idx, op) for (layer, idx), op in self.edits.items())

    @property
    def count(self) -> int:
        return len(self.edits)

    @property
    def layers(self) -> list[str]:
        return sorted({layer for layer, _ in self.edits})

    def changed_paths(self, sources: dict[str, Path]) -> list[Path]:
        return [sources[layer] for layer in self.layers if layer in sources]


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


def render_edited_layer(
    path: Path,
    edits_for_layer: list[tuple[int, str]],
    sample_rate: int = 44100,
) -> np.ndarray:
    """Render one layer file with its cell edits, cross-faded at boundaries.

    Only the edited 1-second windows change; every other sample is preserved
    exactly (same float32 values round-trip to identical 16-bit samples).
    """
    import soundfile as sf

    audio, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
    audio = audio.T
    if sample_rate != file_sr:
        sample_rate = file_sr

    seg_len = int(SEGMENT_SIZE_S * sample_rate)
    for seg_idx, op in sorted(edits_for_layer):
        start = seg_idx * seg_len
        end = min(audio.shape[1], start + seg_len)
        if start >= audio.shape[1]:
            continue
        original = audio[:, start:end].copy()
        edited = apply_op(original, op, sample_rate)
        edited = _crossfade_edges(original, edited, sample_rate)
        audio[:, start:end] = edited.astype(np.float32, copy=False)

    return apply_limiter(audio, ceiling_dbfs=LIMITER_CEILING_DBFS)


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


def commit_edit_plan(
    plan: EditPlan,
    sources: dict[str, Path],
    sample_rate: int = 44100,
) -> dict[str, Path]:
    """Commit an EditPlan onto the blended layer files in-place.

    ``sources`` maps layer name -> current per-layer WAV path (from
    ``build_layer_sources``). Returns layer name -> written path. The raw
    neural cache is never touched, so a later re-separation is always available.

    Raises:
        ValueError: if any cell references a layer missing from ``sources``.
    """
    if plan.count == 0:
        return {}

    by_layer: dict[str, list[tuple[int, str]]] = {}
    for layer, idx, op in plan.cells():
        if layer not in sources:
            raise ValueError(f"Cannot commit edits: layer {layer!r} has no source file.")
        by_layer.setdefault(layer, []).append((idx, op))

    written: dict[str, Path] = {}
    for layer, edits in by_layer.items():
        path = sources[layer]
        rendered = render_edited_layer(path, edits, sample_rate=sample_rate)
        save_pcm32(rendered, path, sample_rate)
        written[layer] = path
        logger.info("Layer Studio: committed %d edit(s) to %s", len(edits), path)
    return written


def rebuild_track_after_commit(
    stem_dir: Path,
    input_stem: str,
    mode: str,
    duration_s: float,
    sample_rate: int = 44100,
    crossover_hz: float = 300.0,
) -> LayerTrack:
    """Re-run the layer analysis so the grid reflects committed edits."""
    return build_layer_track(
        stem_dir,
        input_stem,
        mode,
        duration_s=duration_s,
        sample_rate=sample_rate,
        crossover_hz=crossover_hz,
    )


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