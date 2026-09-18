"""Spectral anti-fraud detector: brick-wall cutoff and steepness analysis.

Normative algorithm per docs/04-spectral-antifraud.md §§3-6. Pure numpy — no I/O.
"""

from __future__ import annotations

import numpy as np

from harvester.models import SpectralResult, Verdict

BAND_START_HZ = 1_000.0
BAND_END_HZ = 24_000.0
BAND_WIDTH_HZ = 500.0
N_FFT = 8192
HOP_LENGTH = 2048
DEAD_MARGIN_DB = 55.0
DEAD_MIN_SPAN_HZ = 1_500.0
FLOOR_PERCENTILE = 10
BASE_LOW_HZ, BASE_HIGH_HZ = 2_000.0, 10_000.0
MIN_SECONDS = 10.0
RMS_SILENCE_DB = -50.0
HIRES_SR = 88_200.0
HIRES_VOID_HZ = 22_400.0


def band_energies_db(pcm: np.ndarray, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (band edges, per-band 90th-percentile energy in dB)."""

    frames = _frames(pcm, sample_rate)
    frequencies = np.fft.rfftfreq(N_FFT, 1.0 / sample_rate)
    window = np.hanning(N_FFT)
    windowed = frames * window
    power = np.abs(np.fft.rfft(windowed, axis=1)) ** 2
    if power.size == 0:
        raise ValueError("no STFT frames produced")
    edges = np.arange(BAND_START_HZ, BAND_END_HZ + BAND_WIDTH_HZ, BAND_WIDTH_HZ)
    energies = np.empty(len(edges) - 1, dtype=np.float64)
    for index in range(len(edges) - 1):
        mask = (frequencies >= edges[index]) & (frequencies < edges[index + 1])
        band = power[:, mask]
        if band.size == 0:
            energies[index] = -np.inf
            continue
        band_power = np.mean(band, axis=1)
        energies[index] = 10.0 * np.log10(np.percentile(band_power, 90) + 1e-12)
    return edges, energies


def noise_reference(energies: np.ndarray, edges: np.ndarray) -> tuple[float, float]:
    """Return (BASE, FLOOR) reference levels used by the deadness rule."""

    lower = edges[:-1] >= BASE_LOW_HZ
    upper = edges[:-1] < BASE_HIGH_HZ
    base_bands = energies[lower & upper]
    if base_bands.size == 0:
        base = float(np.median(energies))
    else:
        base = float(np.median(base_bands))
    floor = float(np.percentile(energies, FLOOR_PERCENTILE))
    return base, floor


def detect_cutoff(
    energies: np.ndarray, edges: np.ndarray
) -> tuple[float, float, float, float]:
    """Return (f_c, steepness S, base, floor) per the brick-wall rules."""

    base, floor = noise_reference(energies, edges)
    dead = energies < np.maximum(base - DEAD_MARGIN_DB, floor + 3.0)

    start_index = None
    index = len(dead) - 1
    while index >= 0:
        if dead[index]:
            run_start = index
            while run_start >= 0 and dead[run_start]:
                run_start -= 1
            span = (index - run_start) * BAND_WIDTH_HZ
            if span >= DEAD_MIN_SPAN_HZ and run_start >= 0:
                start_index = run_start + 1
                break
            index = run_start
        else:
            index -= 1

    if start_index is None:
        return float(edges[-1]), 0.0, base, floor

    cutoff = float(edges[start_index])
    low = energies[(edges[:-1] >= cutoff - 1_000.0) & (edges[:-1] < cutoff)]
    high = energies[(edges[:-1] >= cutoff) & (edges[:-1] < cutoff + 1_000.0)]
    steepness = float(np.mean(low) - np.mean(high)) if low.size and high.size else 0.0
    return cutoff, steepness, base, floor


def rms_db(pcm: np.ndarray) -> float:
    if pcm.size == 0:
        return -np.inf
    return float(10.0 * np.log10(np.mean(np.square(pcm.astype(np.float64))) + 1e-12))


def analyze(
    pcm: np.ndarray,
    sample_rate: float,
    *,
    claimed_sample_rate: int | float | None = None,
) -> SpectralResult:
    """Evaluate one decoded excerpt and return the normative verdict."""

    duration_s = len(pcm) / sample_rate
    if duration_s < MIN_SECONDS or rms_db(pcm) < RMS_SILENCE_DB:
        return SpectralResult(
            verdict=Verdict.INCONCLUSIVE,
            detail=f"insufficient audio (duration {duration_s:.1f}s, rms {rms_db(pcm):.1f} dBFS)",
        )

    edges, energies = band_energies_db(pcm, sample_rate)
    cutoff, steepness, base, floor = detect_cutoff(energies, edges)
    claimed = float(claimed_sample_rate) if claimed_sample_rate else 0.0

    if cutoff <= 19_000.0 and steepness >= 30.0:
        return _fraud(cutoff, steepness, "16-19 kHz brick wall")
    if cutoff <= 17_000.0 and steepness >= 20.0:
        return _fraud(cutoff, steepness, "15-17 kHz brick wall")
    if cutoff <= 15_000.0 and steepness >= 12.0:
        return _fraud(cutoff, steepness, "low brick wall")

    void = energies[(edges[:-1] >= HIRES_VOID_HZ) & np.isfinite(energies)]
    dead_threshold = np.maximum(base - DEAD_MARGIN_DB, floor + 3.0)
    if claimed >= HIRES_SR and void.size and np.all(void < dead_threshold):
        return SpectralResult(
            verdict=Verdict.INCONCLUSIVE,
            cutoff_hz=cutoff,
            steepness_db_per_khz=steepness,
            detail=f"hi-res claim {claimed:.0f} Hz with void above {HIRES_VOID_HZ:.0f} Hz",
        )

    if cutoff <= 19_000.0 and 15.0 <= steepness < 30.0:
        return SpectralResult(
            verdict=Verdict.INCONCLUSIVE,
            cutoff_hz=cutoff,
            steepness_db_per_khz=steepness,
            detail=f"borderline cutoff {cutoff:.0f} Hz, S={steepness:.1f} dB/kHz",
        )

    return SpectralResult(
        verdict=Verdict.PASS,
        cutoff_hz=cutoff,
        steepness_db_per_khz=steepness,
        detail=(
            f"no brick wall detected (f_c={cutoff:.0f} Hz, S={steepness:.1f} dB/kHz, "
            f"base={base:.1f} dB, floor={floor:.1f} dB)"
        ),
    )


def _fraud(cutoff: float, steepness: float, reason: str) -> SpectralResult:
    return SpectralResult(
        verdict=Verdict.FRAUD,
        cutoff_hz=cutoff,
        steepness_db_per_khz=steepness,
        detail=f"{reason}: f_c={cutoff:.0f} Hz, S={steepness:.1f} dB/kHz",
    )


def _frames(pcm: np.ndarray, sample_rate: float) -> np.ndarray:
    if pcm.dtype != np.float32:
        pcm = pcm.astype(np.float32)
    if len(pcm) < N_FFT:
        raise ValueError(f"signal too short for STFT ({len(pcm)} samples)")
    frames = np.lib.stride_tricks.sliding_window_view(pcm, N_FFT)[::HOP_LENGTH]
    return np.ascontiguousarray(frames)


__all__ = ["analyze", "band_energies_db", "detect_cutoff", "noise_reference", "rms_db"]