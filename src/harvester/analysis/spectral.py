"""Spectral anti-fraud detector: brick-wall cutoff and steepness analysis.

Normative algorithm per docs/04-spectral-antifraud.md §§3-6 (v1 rules) and
docs/16-spectral-v2.md (v2 rules: hi-res void, SBR/tonal artifacts, fake bit
depth, stereo asymmetry). Pure numpy — no I/O.
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

# --- v2 rules (docs/16-spectral-v2.md §3) ------------------------------------
HIRES_VOID_HZ = 22_050.0
HIRES_VOID_MARGIN_DB = 6.0
HIRES_VOID_DROP_DB = 20.0
PASSBAND_DROP_DB = 20.0
SBR_MIN_PEAKS = 3
SBR_PROMINENCE_DB = 6.0
SBR_FLOOR_MARGIN_DB = 6.0
SBR_MIN_GAP_HZ = 1_000.0
FAKE_BIT_CLAIM_MIN = 24
FAKE_BIT_ZERO_SHARE = 0.98
FAKE_BIT_MIN_SAMPLES = 48_000
FAKE_BIT_SHIFT = 8
STEREO_DELTA_MIN_HZ = 2_000.0
STEREO_LOW_CUTOFF_MAX_HZ = 19_000.0
STEREO_LOW_STEEPNESS_MIN = 20.0
STEREO_SIDE_MIN_REL_DB = -20.0


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


def detect_cutoff(energies: np.ndarray, edges: np.ndarray) -> tuple[float, float, float, float]:
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


def passband_top(energies: np.ndarray, edges: np.ndarray, base: float) -> float:
    """Upper edge of the highest band still carrying musical content (docs/16 R3).

    Bands within ``PASSBAND_DROP_DB`` of BASE are the recording's own passband;
    anything above that top is where an encoder's bandwidth extension lands.
    """

    limit = base - PASSBAND_DROP_DB
    top = float(edges[0])
    for index in range(len(energies)):
        if np.isfinite(energies[index]) and energies[index] >= limit:
            top = float(edges[index]) + BAND_WIDTH_HZ
    return top


def tonal_peaks(
    energies: np.ndarray,
    edges: np.ndarray,
    *,
    above_hz: float,
    floor: float,
) -> list[float]:
    """Narrowband peaks above ``above_hz`` (docs/16 R3, "birdies").

    A peak is one 500 Hz band that stands ``SBR_PROMINENCE_DB`` above the mean of
    its two neighbours on each side while still sitting above the noise floor —
    the signature of encoder bandwidth extension, not of musical content.
    """

    peaks: list[float] = []
    for index in range(len(energies)):
        edge = float(edges[index])
        if edge + BAND_WIDTH_HZ <= above_hz:
            continue
        value = energies[index]
        if not np.isfinite(value) or value < floor + SBR_FLOOR_MARGIN_DB:
            continue
        neighbours = [
            float(energies[offset])
            for offset in (index - 2, index - 1, index + 1, index + 2)
            if 0 <= offset < len(energies) and np.isfinite(energies[offset])
        ]
        if not neighbours:
            continue
        if value - float(np.mean(neighbours)) >= SBR_PROMINENCE_DB:
            peaks.append(edge)
    return peaks


def low_byte_zero_share(samples: np.ndarray, *, shift: int = FAKE_BIT_SHIFT) -> float:
    """Share of samples whose low content byte carries nothing (docs/16 R2).

    ffmpeg left-aligns every bit depth into ``s32le``, so a 16-bit master padded
    into a 24-bit stream keeps bits ``shift..shift+8`` at zero for every sample —
    the classic fake-24-bit histogram. Two robustness choices:

    * a *share*, not a bitwise OR — one outlier would otherwise dominate a union;
    * saturated samples are dropped — a clipped master pins that byte to 0xFF for
      reasons that have nothing to do with the depth it was recorded at.
    """

    if samples.size == 0:
        return 0.0
    content = samples.astype(np.int64) >> shift
    usable = np.abs(content) <= (1 << 23) - 2
    if not usable.any():
        return 0.0
    return float(np.mean((content[usable] & 0xFF) == 0))


def stereo_cutoffs(
    mid: np.ndarray,
    side: np.ndarray,
    sample_rate: float,
) -> tuple[float, float, float, float] | None:
    """(f_c mid, S mid, f_c side, S side) or ``None`` when the side is too quiet.

    An upcast that filters one channel before the other (a known trick) leaves the
    two channels with different bandwidths; a side channel buried in the noise
    floor cannot be judged, so the rule abstains instead of guessing.
    """

    if side.size < N_FFT or mid.size < N_FFT:
        return None
    mid_rms = rms_db(mid)
    if rms_db(side) < mid_rms + STEREO_SIDE_MIN_REL_DB:
        return None
    mid_edges, mid_energies = band_energies_db(mid, sample_rate)
    side_edges, side_energies = band_energies_db(side, sample_rate)
    mid_cutoff, mid_steepness, _, _ = detect_cutoff(mid_energies, mid_edges)
    side_cutoff, side_steepness, _, _ = detect_cutoff(side_energies, side_edges)
    return mid_cutoff, mid_steepness, side_cutoff, side_steepness


def rms_db(pcm: np.ndarray) -> float:
    if pcm.size == 0:
        return -np.inf
    return float(10.0 * np.log10(np.mean(np.square(pcm.astype(np.float64))) + 1e-12))


def analyze(
    pcm: np.ndarray,
    sample_rate: float,
    *,
    claimed_sample_rate: int | float | None = None,
    claimed_bits: int | float | None = None,
    side_pcm: np.ndarray | None = None,
    native_pcm: np.ndarray | None = None,
) -> SpectralResult:
    """Evaluate one decoded excerpt and return the normative verdict.

    ``pcm`` is the mono/mid excerpt analysed by the v1 rules; the v2 rules use the
    optional evidence: ``side_pcm`` (side channel of a stereo decode),
    ``native_pcm`` (int32 samples at the file's own sample rate, for the bit-depth
    histogram) and ``claimed_bits`` (the container's declared bit depth).
    """

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

    claimed_depth = float(claimed_bits) if claimed_bits else 0.0
    fake_bits = _fake_bit_depth(native_pcm, claimed_depth)
    if fake_bits is not None:
        depth, share = fake_bits
        return _fraud(
            cutoff,
            steepness,
            (
                f"{claimed_depth:.0f}-bit claim carries {depth} bits of information "
                f"(empty low byte in {share:.1%} of samples)"
            ),
        )

    asymmetry = _stereo_asymmetry(side_pcm, pcm, sample_rate)
    if asymmetry is not None:
        return _fraud(cutoff, steepness, asymmetry)

    top = passband_top(energies, edges, base)
    peaks = tonal_peaks(energies, edges, above_hz=top + SBR_MIN_GAP_HZ, floor=floor)
    if len(peaks) >= SBR_MIN_PEAKS:
        return _fraud(
            cutoff,
            steepness,
            (
                f"encoder bandwidth extension: {len(peaks)} tonal peaks above the "
                f"{top:.0f} Hz passband"
            ),
        )

    void = energies[(edges[:-1] >= HIRES_VOID_HZ) & np.isfinite(energies)]
    if (
        claimed >= HIRES_SR
        and void.size
        and float(np.max(void)) <= floor + HIRES_VOID_MARGIN_DB
        and float(np.max(void)) <= base - HIRES_VOID_DROP_DB
    ):
        # Two conditions, not one: on genuinely flat material (broadband noise,
        # dense electronic mixes) the 10th-percentile FLOOR sits *at* the content
        # level, so "within 6 dB of the floor" alone would call honest hi-res
        # audio a void. The void must also sit far below the musical baseline.
        return _fraud(
            cutoff,
            steepness,
            (
                f"hi-res claim {claimed:.0f} Hz with void above {HIRES_VOID_HZ:.0f} Hz "
                f"(floor {floor:.1f} dB)"
            ),
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


def _fake_bit_depth(native_pcm: np.ndarray | None, claimed_bits: float) -> tuple[int, float] | None:
    """(effective depth, empty-low-byte share) for a padded ≥24-bit claim, else ``None``."""

    if native_pcm is None or claimed_bits < FAKE_BIT_CLAIM_MIN:
        return None
    if native_pcm.size < FAKE_BIT_MIN_SAMPLES:
        return None
    share = low_byte_zero_share(native_pcm)
    if share < FAKE_BIT_ZERO_SHARE:
        return None
    return int(claimed_bits) - FAKE_BIT_SHIFT, share


def _stereo_asymmetry(
    side_pcm: np.ndarray | None,
    mid_pcm: np.ndarray,
    sample_rate: float,
) -> str | None:
    """Reason string when the two channels carry different bandwidths."""

    if side_pcm is None:
        return None
    cutoffs = stereo_cutoffs(mid_pcm, side_pcm, sample_rate)
    if cutoffs is None:
        return None
    mid_cutoff, mid_steepness, side_cutoff, side_steepness = cutoffs
    delta = abs(mid_cutoff - side_cutoff)
    if delta < STEREO_DELTA_MIN_HZ:
        return None
    lower = min(mid_cutoff, side_cutoff)
    lower_steepness = mid_steepness if mid_cutoff <= side_cutoff else side_steepness
    if lower > STEREO_LOW_CUTOFF_MAX_HZ or lower_steepness < STEREO_LOW_STEEPNESS_MIN:
        return None
    channel = "side" if side_cutoff <= mid_cutoff else "mid"
    return (
        f"stereo asymmetry: {channel} channel cuts at {lower:.0f} Hz "
        f"(S={lower_steepness:.1f} dB/kHz), other channel at "
        f"{max(mid_cutoff, side_cutoff):.0f} Hz"
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


__all__ = [
    "analyze",
    "band_energies_db",
    "detect_cutoff",
    "low_byte_zero_share",
    "noise_reference",
    "passband_top",
    "rms_db",
    "stereo_cutoffs",
    "tonal_peaks",
]
