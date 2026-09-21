"""Spectral anti-fraud v2 rules: hi-res void, SBR scan, bit depth, stereo (docs/16)."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.analysis.spectral import (
    analyze,
    band_energies_db,
    detect_cutoff,
    low_byte_zero_share,
    noise_reference,
    passband_top,
    tonal_peaks,
)
from harvester.models import Verdict

_FS = 44_100
requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


def _sharp_lowpass_mask(length: int, fs: int, cutoff: float, transition: float = 500.0) -> np.ndarray:
    """Encoder-style brick wall (same recipe as tests/test_spectral.py, docs/04 §10)."""

    frequencies = np.fft.rfftfreq(length, 1.0 / fs)
    mask = np.ones_like(frequencies)
    above = frequencies > cutoff + transition
    mask[above] = 0.0
    ramp = (frequencies - cutoff) / transition
    inside = (frequencies > cutoff) & ~above
    mask[inside] = 0.5 * (1.0 + np.cos(np.pi * np.clip(ramp[inside], 0.0, 1.0)))
    return mask


def _content(duration_s: float, fs: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    samples = int(duration_s * fs)
    time = np.arange(samples) / fs
    tone = 0.4 * np.sin(2 * np.pi * 220 * time) + 0.2 * np.sin(2 * np.pi * 440 * time)
    return 0.5 * rng.standard_normal(samples) + tone


def _masked(duration_s: float, fs: int, seed: int, cutoff: float) -> np.ndarray:
    signal = _content(duration_s, fs, seed)
    return np.fft.irfft(np.fft.rfft(signal) * _sharp_lowpass_mask(len(signal), fs, cutoff), len(signal))


def _with_birdies(signal: np.ndarray, fs: int, frequencies: tuple[float, ...]) -> np.ndarray:
    time = np.arange(len(signal)) / fs
    return signal + sum(0.01 * np.sin(2 * np.pi * f * time) for f in frequencies)


# --- R1: hi-res void ---------------------------------------------------------


def test_hires_claim_with_void_is_fraud() -> None:
    """A 96 kHz claim whose content stops at 22.05 kHz is an upsample (docs/04 §9.1)."""

    signal = _content(30.0, _FS, seed=31)
    upsampled = np.fft.irfft(np.fft.rfft(signal), n=2 * len(signal)) * 2.0

    result = analyze(upsampled.astype(np.float32), float(_FS * 2), claimed_sample_rate=96_000)

    assert result.verdict is Verdict.FRAUD
    assert "void above" in result.detail


def test_hires_claim_with_real_content_passes() -> None:
    """Honest 96 kHz material carries energy above 22.05 kHz and is left alone."""

    rng = np.random.default_rng(32)
    samples = int(30.0 * _FS * 2)
    time = np.arange(samples) / (_FS * 2)
    signal = (0.5 * rng.standard_normal(samples) + 0.4 * np.sin(2 * np.pi * 220 * time)).astype(
        np.float32
    )

    result = analyze(signal, float(_FS * 2), claimed_sample_rate=96_000)

    assert result.verdict is Verdict.PASS


def test_44k_claim_without_hi_res_is_not_touched_by_the_void_rule() -> None:
    """The void rule only fires for hi-res claims; a 44.1 kHz file is judged by v1."""

    signal = _masked(30.0, _FS, seed=33, cutoff=14_000.0)

    result = analyze(signal.astype(np.float32), float(_FS), claimed_sample_rate=_FS)

    assert result.verdict is Verdict.FRAUD
    assert "brick wall" in result.detail


# --- R2: fake bit depth ------------------------------------------------------


def test_low_byte_zero_share_reads_the_padding() -> None:
    rng = np.random.default_rng(41)
    sixteen = (rng.integers(-32768, 32767, size=4096)).astype(np.int64) << 16
    twenty_four = ((rng.integers(-(2**23), 2**23 - 1, size=4096)).astype(np.int64)) << 8

    assert low_byte_zero_share(sixteen.astype(np.int32)) == 1.0
    assert low_byte_zero_share(twenty_four.astype(np.int32)) < 0.05
    assert low_byte_zero_share(np.zeros(4096, dtype=np.int32)) == 1.0


def test_one_clipped_sample_does_not_hide_the_padding() -> None:
    """The share tolerates outliers a bitwise-OR union would let dominate."""

    rng = np.random.default_rng(46)
    padded = (rng.integers(-32768, 32767, size=48_000)).astype(np.int64) << 16
    padded[7] = 2**31 - 1  # a clipped sample: every bit set

    assert low_byte_zero_share(padded.astype(np.int32)) > 0.99


def test_24bit_claim_carrying_16_bits_is_fraud() -> None:
    content = _content(30.0, _FS, seed=42)
    grid16 = np.round(content * 32768.0) / 32768.0
    native = ((grid16 * 32768.0).astype(np.int64) << 16).astype(np.int32)

    result = analyze(
        content.astype(np.float32),
        float(_FS),
        claimed_bits=24,
        native_pcm=native,
    )

    assert result.verdict is Verdict.FRAUD
    assert "bits of information" in result.detail


def test_genuine_24bit_content_is_not_flagged() -> None:
    content = _content(30.0, _FS, seed=43)
    native = ((content * float(2**23)).astype(np.int64) << 8).astype(np.int32)

    result = analyze(
        content.astype(np.float32),
        float(_FS),
        claimed_bits=24,
        native_pcm=native,
    )

    assert result.verdict is Verdict.PASS


def test_16bit_claim_is_out_of_scope_for_the_bit_rule() -> None:
    content = _content(30.0, _FS, seed=44)
    native = ((content * 32768.0).astype(np.int64) << 16).astype(np.int32)

    result = analyze(
        content.astype(np.float32),
        float(_FS),
        claimed_bits=16,
        native_pcm=native,
    )

    assert result.verdict is Verdict.PASS


@requires_ffmpeg
@pytest.mark.asyncio
async def test_fake_24bit_detected_through_a_real_ffmpeg_decode(tmp_path: Path) -> None:
    """End-to-end: the padding survives the real FLAC → s32le path (docs/16 §4)."""

    from harvester.config import load_config
    from harvester.services.ffmpeg import FfmpegService

    content = _content(3.0, _FS, seed=45)
    grid16 = (np.round(content * 32768.0) / 32768.0).astype(np.float32)
    fake = tmp_path / "fake24.flac"
    genuine = tmp_path / "genuine24.flac"
    sf.write(fake, grid16, _FS, format="FLAC", subtype="PCM_24")
    sf.write(genuine, content.astype(np.float32), _FS, format="FLAC", subtype="PCM_24")

    service = FfmpegService(load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")}))

    fake_native = await service.decode_s32(fake)
    genuine_native = await service.decode_s32(genuine)

    assert low_byte_zero_share(fake_native) > 0.98
    assert low_byte_zero_share(genuine_native) < 0.05
    assert await service.probe_bit_depth(fake) == 24


# --- R3: SBR / tonal artifacts ----------------------------------------------


def test_birdies_above_the_passband_are_fraud() -> None:
    """Tonal peaks above a 14 kHz passband are encoder bandwidth extension."""

    signal = _with_birdies(
        _masked(90.0, _FS, seed=51, cutoff=14_000.0),
        _FS,
        (19_500.0, 20_500.0, 21_500.0),
    )

    result = analyze(signal.astype(np.float32), float(_FS))

    assert result.verdict is Verdict.FRAUD
    assert "bandwidth extension" in result.detail


def test_brick_wall_without_birdies_keeps_the_v1_reason() -> None:
    """No injected peaks → the v1 brick-wall rule reports, the SBR scan stays quiet."""

    signal = _masked(90.0, _FS, seed=52, cutoff=14_000.0)

    result = analyze(signal.astype(np.float32), float(_FS))

    assert result.verdict is Verdict.FRAUD
    assert "brick wall" in result.detail


def test_passband_top_and_tonal_peaks_helpers() -> None:
    signal = _with_birdies(
        _masked(60.0, _FS, seed=53, cutoff=14_000.0),
        _FS,
        (19_500.0, 20_500.0, 21_500.0),
    ).astype(np.float32)
    edges, energies = band_energies_db(signal, float(_FS))
    base, floor = noise_reference(energies, edges)
    top = passband_top(energies, edges, base)

    peaks = tonal_peaks(energies, edges, above_hz=top + 1_000.0, floor=floor)

    assert top <= 15_000.0
    assert len(peaks) >= 3
    assert all(peak >= 19_000.0 for peak in peaks)


# --- R4: stereo asymmetry ---------------------------------------------------


def test_stereo_asymmetry_is_fraud() -> None:
    """A side channel that stops 8 kHz below the mid is filtered, not recorded."""

    mid = _content(90.0, _FS, seed=61).astype(np.float32)
    side = (_masked(90.0, _FS, seed=62, cutoff=16_000.0) * 0.5).astype(np.float32)

    result = analyze(mid, float(_FS), side_pcm=side)

    assert result.verdict is Verdict.FRAUD
    assert "stereo asymmetry" in result.detail


def test_symmetric_stereo_passes() -> None:
    mid = _content(90.0, _FS, seed=63).astype(np.float32)
    side = (_content(90.0, _FS, seed=64) * 0.5).astype(np.float32)

    result = analyze(mid, float(_FS), side_pcm=side)

    assert result.verdict is Verdict.PASS


def test_quiet_side_channel_abstains() -> None:
    """A side channel buried 30 dB down cannot be judged — the rule abstains."""

    mid = _content(90.0, _FS, seed=65).astype(np.float32)
    side = (_masked(90.0, _FS, seed=66, cutoff=16_000.0) * 0.02).astype(np.float32)

    result = analyze(mid, float(_FS), side_pcm=side)

    assert result.verdict is Verdict.PASS


def test_mono_decode_yields_a_silent_side_channel() -> None:
    """A mono file duplicates into L/R, so the side is empty and never judged."""

    from harvester.pipeline.phase4_spectral import mid_side

    mono = _content(30.0, _FS, seed=67).astype(np.float32)
    interleaved = np.repeat(mono, 2)

    mid, side = mid_side(interleaved)

    assert np.allclose(mid, mono, atol=1e-6)
    assert float(np.max(np.abs(side))) == 0.0


def test_cutoff_detection_still_matches_v1_on_a_masked_signal() -> None:
    """The v1 detector is untouched by the v2 additions."""

    signal = _masked(90.0, _FS, seed=68, cutoff=16_000.0).astype(np.float32)
    edges, energies = band_energies_db(signal, float(_FS))

    cutoff, steepness, _, _ = detect_cutoff(energies, edges)

    assert 15_000.0 <= cutoff <= 17_500.0
    assert steepness >= 25.0
