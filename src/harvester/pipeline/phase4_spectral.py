"""Phase 4 gate: run the spectral check on P2P lossless claims only."""

from __future__ import annotations

import asyncio

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

    duration = await ffmpeg.probe_duration(job.workspace_path, job_id=job.id)
    offset, length = _excerpt_window(duration)
    claimed_sr = await ffmpeg.probe_sample_rate(job.workspace_path, job_id=job.id)
    try:
        pcm = await ffmpeg.decode_f32(
            job.workspace_path,
            offset_s=offset,
            duration_s=length,
            job_id=job.id,
        )
    except ValidationError as exc:
        return SpectralResult(
            verdict=Verdict.INCONCLUSIVE,
            detail=f"decode failure ({exc})",
        )
    return await asyncio.to_thread(
        spectral_analysis.analyze,
        pcm,
        48_000.0,
        claimed_sample_rate=claimed_sr,
    )


def excerpt_window(duration_s: float) -> tuple[float, float]:
    """Normative offset/length selection per docs/04 §2."""

    return _excerpt_window(duration_s)


def _excerpt_window(duration_s: float) -> tuple[float, float]:
    if duration_s <= 0:
        raise ValidationError("cannot select an excerpt from a zero-length file")
    if duration_s < 70.0:
        return 0.15 * duration_s, min(_EXCERPT_S, 0.7 * duration_s)
    return 0.3 * duration_s, _EXCERPT_S


__all__ = ["excerpt_window", "run_spectral_check"]
