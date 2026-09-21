"""Phase 4 gate: run the spectral check on P2P lossless claims only."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from harvester.analysis import spectral as spectral_analysis
from harvester.config import AppConfig
from harvester.models import SourceKind, SpectralResult, TrackJob, Verdict
from harvester.services.ffmpeg import FfmpegService
from harvester.util.errors import ValidationError

_EXCERPT_S = 60.0


async def run_spectral_check(
    job: TrackJob,
    config: AppConfig,
    ffmpeg: FfmpegService,
) -> SpectralResult:
    """Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)."""

    if job.source_kind is not SourceKind.P2P_FLAC:
        return SpectralResult(
            verdict=Verdict.NOT_APPLICABLE,
            detail="provenance is lossy; spectral check skipped (D3)",
        )
    if not config.spectral.enabled:
        return SpectralResult(
            verdict=Verdict.NOT_APPLICABLE,
            detail="spectral check disabled by configuration",
        )
    if not job.workspace_path or not job.workspace_path.is_file():
        raise ValidationError("spectral check requires the acquired file")

    path = job.workspace_path
    duration = await ffmpeg.probe_duration(path, job_id=job.id)
    offset, length = _excerpt_window(duration)
    claimed_sr = await ffmpeg.probe_sample_rate(path, job_id=job.id)
    claimed_bits = await ffmpeg.probe_bit_depth(path, job_id=job.id)
    try:
        stereo = await ffmpeg.decode_f32(
            path,
            offset_s=offset,
            duration_s=length,
            channels=2,
            job_id=job.id,
        )
    except ValidationError as exc:
        return SpectralResult(
            verdict=Verdict.INCONCLUSIVE,
            detail=f"decode failure ({exc})",
        )
    mid, side = mid_side(stereo)
    native = await _native_samples(ffmpeg, path, job.id, claimed_bits, offset, length)
    return await asyncio.to_thread(
        spectral_analysis.analyze,
        mid,
        48_000.0,
        claimed_sample_rate=claimed_sr,
        claimed_bits=claimed_bits,
        side_pcm=side,
        native_pcm=native,
    )


async def _native_samples(
    ffmpeg: FfmpegService,
    path: Path,
    job_id: str | None,
    claimed_bits: int | None,
    offset: float,
    length: float,
) -> np.ndarray | None:
    """int32 excerpt at the file's own rate, only when a ≥24-bit claim needs it.

    Best-effort: a failed native decode leaves the bit-depth rule to abstain
    instead of failing a verdict the spectral rules already reached.
    """

    if not claimed_bits or claimed_bits < spectral_analysis.FAKE_BIT_CLAIM_MIN:
        return None
    try:
        return await ffmpeg.decode_s32(
            path,
            offset_s=offset,
            duration_s=length,
            job_id=job_id,
        )
    except ValidationError:
        return None


def mid_side(interleaved: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split an interleaved stereo decode into (mid, side) (docs/16 R3/R4)."""

    samples = interleaved
    if samples.size % 2:
        samples = samples[:-1]
    if samples.size < 2:
        return samples.astype(np.float32), np.zeros(0, dtype=np.float32)
    frames = samples.reshape(-1, 2).astype(np.float32)
    left = frames[:, 0]
    right = frames[:, 1]
    return (left + right) / 2.0, (left - right) / 2.0


def excerpt_window(duration_s: float) -> tuple[float, float]:
    """Normative offset/length selection per docs/04 §2."""

    return _excerpt_window(duration_s)


def _excerpt_window(duration_s: float) -> tuple[float, float]:
    if duration_s <= 0:
        raise ValidationError("cannot select an excerpt from a zero-length file")
    if duration_s < 70.0:
        return 0.15 * duration_s, min(_EXCERPT_S, 0.7 * duration_s)
    return 0.3 * duration_s, _EXCERPT_S


__all__ = ["excerpt_window", "mid_side", "run_spectral_check"]
