"""Real audio feature extraction feeding the modular visualizer engines.

Every visualizer engine renders from an :class:`AudioFeatureContext`. Without a
real producer for that context the dashboard can only ever animate from the
synthetic standby waveform, so playback looked identical whether or not music
was actually routed. This module decodes a routed track once, pre-computes a
track of feature frames, and lets the dashboard play them back in sync.
"""

from __future__ import annotations

import math
import subprocess
from collections import OrderedDict
from pathlib import Path

import numpy as np

from harvester.ui.visuals.base import AudioFeatureContext

SAMPLE_RATE = 22050
FRAME_SIZE = 1024
HOP_SIZE = 368  # ~16.6ms at 22050Hz for 60 FPS smooth playback
N_LEVELS = 128
N_WAVEFORM = 1024
MAX_FRAMES = 3600  # Up to 60s at 60 FPS
PEAK_DECAY = 0.94

_MAX_CACHE_ENTRIES = 4
_FEATURE_CACHE: OrderedDict[tuple[str, float], list[AudioFeatureContext]] = OrderedDict()


def _decode_stereo(audio_file: Path) -> np.ndarray:
    """Decode an audio file to interleaved float32 stereo at SAMPLE_RATE.

    Returns an empty array when the file cannot be decoded.
    """
    cmd = [
        "ffmpeg",
        "-v",
        "quiet",
        "-i",
        str(audio_file),
        "-f",
        "s16le",
        "-ac",
        "2",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        return np.zeros(0, dtype=np.float32)
    interleaved = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return interleaved.reshape(-1, 2)


def _levels_from_magnitude(mag: np.ndarray) -> np.ndarray:
    """Reduce an rFFT magnitude spectrum to 128 perceptually-scaled level bins."""
    n_freq = len(mag)
    n_bins = min(N_LEVELS, n_freq)
    edges = np.linspace(0, n_freq, n_bins + 1).astype(int)
    starts = edges[:-1]
    # Guard against empty groups when the spectrum is shorter than the bin count.
    starts = np.minimum(starts, n_freq - 1)
    sums = np.add.reduceat(mag, starts)
    counts = np.maximum(edges[1:] - edges[:-1], 1)
    levels = (sums[:n_bins] / counts[:n_bins]).astype(np.float32)
    # Map linear magnitude to a 0..1 display scale anchored on -60 dB.
    db = 20.0 * np.log10(levels + 1e-6)
    scaled = np.clip((db + 60.0) / 60.0, 0.0, 1.0).astype(np.float32)
    if n_bins < N_LEVELS:
        scaled = np.pad(scaled, (0, N_LEVELS - n_bins))
    return scaled


def _spectral_centroid(mag: np.ndarray) -> float:
    """Return the magnitude-weighted mean frequency in Hz."""
    total = float(np.sum(mag))
    if total <= 1e-9:
        return 0.0
    freqs = np.fft.rfftfreq(len(mag) * 2 - 2, d=1.0 / SAMPLE_RATE)
    return float(np.sum(freqs * mag) / total)


def _frame_context(
    window_l: np.ndarray,
    window_r: np.ndarray,
    levels: np.ndarray,
    prev_mag: np.ndarray | None,
) -> tuple[AudioFeatureContext, np.ndarray]:
    """Build one AudioFeatureContext from a single analysis window."""
    mid = (window_l + window_r) * 0.5
    side = (window_l - window_r) * 0.5

    rms = float(np.sqrt(np.mean(mid.astype(np.float64) ** 2)))
    peak = float(np.max(np.abs(mid))) if len(mid) else 0.0
    rms_db = 20.0 * math.log10(rms) if rms > 1e-6 else -60.0
    crest = 20.0 * math.log10(peak / rms) if rms > 1e-6 and peak > 1e-6 else 0.0

    denom = float(np.sqrt(np.sum(window_l.astype(np.float64) ** 2) * np.sum(window_r.astype(np.float64) ** 2)))
    if denom > 1e-9:
        phase_corr = float(np.sum(window_l * window_r) / denom)
    else:
        phase_corr = 0.0

    mag = np.abs(np.fft.rfft(mid * np.hanning(len(mid))))
    flux = 0.0
    if prev_mag is not None and len(prev_mag) == len(mag):
        diff = mag - prev_mag
        flux = float(np.sum(np.maximum(diff, 0.0)))

    # K-weighted loudness proxy: map RMS onto the momentary LUFS-M scale.
    lufs_m = -70.0 + (rms_db + 70.0) * 0.85 if rms_db > -70.0 else -70.0

    ctx = AudioFeatureContext(
        levels_128=levels,
        peaks_128=levels.copy(),
        waveform_l=window_l.astype(np.float32),
        waveform_r=window_r.astype(np.float32),
        mid_channel=mid.astype(np.float32),
        side_channel=side.astype(np.float32),
        rms_db=rms_db,
        lufs_m=lufs_m,
        crest_factor=crest,
        phase_corr=max(-1.0, min(1.0, phase_corr)),
        spectral_centroid=_spectral_centroid(mag),
        transient_flag=flux > float(np.mean(mag)) * 0.5,
        is_playing=True,
    )
    return ctx, mag


def build_feature_track(audio_file: Path, max_frames: int = MAX_FRAMES) -> list[AudioFeatureContext]:
    """Decode `audio_file` and pre-compute a playback track of feature frames.

    Returns an empty list when the file is unreadable or too short to analyse.
    Results are memoised per (path, mtime) so re-routing a track is free.
    """
    try:
        stat = audio_file.stat()
    except OSError:
        return []

    key = (str(audio_file), stat.st_mtime)
    cached = _FEATURE_CACHE.get(key)
    if cached is not None:
        _FEATURE_CACHE.move_to_end(key)
        return cached

    stereo = _decode_stereo(audio_file)
    if len(stereo) < FRAME_SIZE:
        _FEATURE_CACHE[key] = []
        return []

    left = np.ascontiguousarray(stereo[:, 0])
    right = np.ascontiguousarray(stereo[:, 1])

    n_frames = min(max_frames, (len(left) - FRAME_SIZE) // HOP_SIZE + 1)
    if n_frames <= 0:
        _FEATURE_CACHE[key] = []
        return []

    total = (n_frames - 1) * HOP_SIZE + FRAME_SIZE
    starts = np.arange(n_frames) * HOP_SIZE
    l_win = np.lib.stride_tricks.sliding_window_view(left[:total], FRAME_SIZE)[starts]
    r_win = np.lib.stride_tricks.sliding_window_view(right[:total], FRAME_SIZE)[starts]

    window = np.hanning(FRAME_SIZE)
    l_hann = l_win * window
    r_hann = r_win * window
    magnitudes = np.abs(np.fft.rfft((l_hann + r_hann) * 0.5, axis=1))

    track: list[AudioFeatureContext] = []
    peaks = np.zeros(N_LEVELS, dtype=np.float32)
    prev_mag: np.ndarray | None = None
    for i in range(n_frames):
        levels = _levels_from_magnitude(magnitudes[i])
        peaks = np.maximum(peaks * PEAK_DECAY, levels)
        ctx, prev_mag = _frame_context(l_win[i], r_win[i], levels, prev_mag)
        ctx.peaks_128 = peaks.copy()
        track.append(ctx)

    _FEATURE_CACHE[key] = track
    while len(_FEATURE_CACHE) > _MAX_CACHE_ENTRIES:
        _FEATURE_CACHE.popitem(last=False)
    return track
