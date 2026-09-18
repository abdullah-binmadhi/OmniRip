from pathlib import Path

import pytest

from harvester.config import AppConfig, load_config
from harvester.models import Mode, SourceKind, TrackJob, Verdict
from harvester.pipeline.phase4_spectral import _excerpt_window, run_spectral_check
from harvester.util.errors import ValidationError


def test_excerpt_window_norms() -> None:
    assert _excerpt_window(600.0) == pytest.approx((180.0, 60.0))
    assert _excerpt_window(30.0) == pytest.approx((4.5, 21.0))
    with pytest.raises(ValidationError):
        _excerpt_window(0.0)


class _FakeFfmpeg:
    def __init__(self, duration: float, sample_rate: int | None) -> None:
        self.duration = duration
        self.sample_rate = sample_rate

    async def probe_duration(self, path, *, job_id=None):
        return self.duration

    async def probe_sample_rate(self, path, *, job_id=None):
        return self.sample_rate

    async def decode_f32(self, path, *, offset_s, duration_s, job_id=None):
        import numpy as np

        return np.zeros(int(48_000 * 60), dtype=np.float32)


class _FakeFailureFfmpeg:
    async def probe_duration(self, path, *, job_id=None):
        return 100.0

    async def probe_sample_rate(self, path, *, job_id=None):
        return 44_100

    async def decode_f32(self, path, *, offset_s, duration_s, job_id=None):
        from harvester.util.errors import ValidationError

        raise ValidationError("decode boom")


def _config(tmp: Path) -> AppConfig:
    return load_config(environ={"HARVESTER_DATA_DIR": str(tmp / "data")})


def _make_job(tmp: Path) -> TrackJob:
    job = TrackJob(mode=Mode.SINGLE_URL)
    job.source_kind = SourceKind.P2P_FLAC
    path = tmp / "file.flac"
    path.write_bytes(b"fake")
    job.workspace_path = path
    return job


@pytest.mark.asyncio
async def test_gate_skips_lossy_provenance(tmp_path: Path) -> None:
    config = _config(tmp_path)
    job = _make_job(tmp_path)
    job.source_kind = SourceKind.STREAM_OPUS

    result = await run_spectral_check(job, config, _FakeFfmpeg(100.0, 44_100))

    assert result.verdict is Verdict.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_gate_decode_failure_yields_inconclusive(tmp_path: Path) -> None:
    config = _config(tmp_path)
    job = _make_job(tmp_path)

    result = await run_spectral_check(job, config, _FakeFailureFfmpeg())

    assert result.verdict is Verdict.INCONCLUSIVE
    assert "decode" in result.detail.lower()


@pytest.mark.asyncio
async def test_gate_disabled_by_config(tmp_path: Path) -> None:
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"spectral.enabled": False},
    )
    job = _make_job(tmp_path)

    result = await run_spectral_check(job, config, _FakeFfmpeg(100.0, 44_100))

    assert result.verdict is Verdict.NOT_APPLICABLE