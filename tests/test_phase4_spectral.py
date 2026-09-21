from pathlib import Path

import numpy as np
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
    """Records the decode calls phase4 makes (docs/16 §4)."""

    def __init__(
        self,
        duration: float,
        sample_rate: int | None,
        *,
        bits: int | None = None,
        stereo: "np.ndarray | None" = None,
        native: "np.ndarray | None" = None,
        native_fails: bool = False,
    ) -> None:
        self.duration = duration
        self.sample_rate = sample_rate
        self.bits = bits
        self.stereo = stereo
        self.native = native
        self.native_fails = native_fails
        self.decode_calls: list[dict[str, object]] = []
        self.native_calls = 0

    async def probe_duration(self, path, *, job_id=None):
        return self.duration

    async def probe_sample_rate(self, path, *, job_id=None):
        return self.sample_rate

    async def probe_bit_depth(self, path, *, job_id=None):
        return self.bits

    async def decode_f32(self, path, *, offset_s, duration_s, sample_rate=48_000, channels=1, job_id=None):
        self.decode_calls.append({"channels": channels, "sample_rate": sample_rate})
        if self.stereo is not None:
            return self.stereo
        return np.zeros(int(sample_rate * 60), dtype=np.float32)

    async def decode_s32(self, path, *, offset_s, duration_s, job_id=None):
        from harvester.util.errors import ValidationError

        self.native_calls += 1
        if self.native_fails:
            raise ValidationError("native decode boom")
        if self.native is not None:
            return self.native
        return np.zeros(48_000, dtype=np.int32)


class _FakeFailureFfmpeg(_FakeFfmpeg):
    def __init__(self) -> None:
        super().__init__(100.0, 44_100)

    async def decode_f32(self, path, *, offset_s, duration_s, sample_rate=48_000, channels=1, job_id=None):
        from harvester.util.errors import ValidationError

        raise ValidationError("decode boom")


def _stereo_pair(duration_s: float = 60.0, fs: int = 48_000) -> np.ndarray:
    """Interleaved L/R whose mid is full-band and whose side is brick-walled."""

    rng = np.random.default_rng(7)
    samples = int(duration_s * fs)
    time = np.arange(samples) / fs
    mid = 0.5 * rng.standard_normal(samples) + 0.4 * np.sin(2 * np.pi * 220 * time)
    side = rng.standard_normal(samples) * 0.3
    frequencies = np.fft.rfftfreq(samples, 1.0 / fs)
    mask = np.where(frequencies > 16_000.0, 0.0, 1.0)
    side = np.fft.irfft(np.fft.rfft(side) * mask, samples)
    return np.stack([mid + side, mid - side], axis=1).reshape(-1).astype(np.float32)


def _mono_pair(duration_s: float = 60.0, fs: int = 48_000) -> np.ndarray:
    """Interleaved L/R that are identical: a mono file decoded to two channels."""

    rng = np.random.default_rng(11)
    samples = int(duration_s * fs)
    time = np.arange(samples) / fs
    mono = 0.5 * rng.standard_normal(samples) + 0.4 * np.sin(2 * np.pi * 220 * time)
    return np.repeat(mono, 2).astype(np.float32)


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
async def test_gate_decodes_stereo_and_judges_mid_side(tmp_path: Path) -> None:
    """phase4 hands the analysis a stereo pair, not a mono downmix (docs/16 §4)."""

    config = _config(tmp_path)
    job = _make_job(tmp_path)
    ffmpeg = _FakeFfmpeg(100.0, 44_100, stereo=_stereo_pair())

    result = await run_spectral_check(job, config, ffmpeg)

    assert ffmpeg.decode_calls == [{"channels": 2, "sample_rate": 48_000}]
    assert result.verdict is Verdict.FRAUD
    assert "stereo asymmetry" in result.detail


@pytest.mark.asyncio
async def test_gate_decodes_native_pcm_only_for_hires_claims(tmp_path: Path) -> None:
    config = _config(tmp_path)
    job = _make_job(tmp_path)

    cd = _FakeFfmpeg(100.0, 44_100, bits=16)
    hires = _FakeFfmpeg(100.0, 96_000, bits=24)

    await run_spectral_check(job, config, cd)
    await run_spectral_check(job, config, hires)

    assert cd.native_calls == 0
    assert hires.native_calls == 1


@pytest.mark.asyncio
async def test_gate_native_decode_failure_stays_best_effort(tmp_path: Path) -> None:
    """A failed bit-depth decode must not sink a verdict the spectral rules reached."""

    config = _config(tmp_path)
    job = _make_job(tmp_path)
    ffmpeg = _FakeFfmpeg(100.0, 96_000, bits=24, native_fails=True, stereo=_mono_pair())

    result = await run_spectral_check(job, config, ffmpeg)

    assert result.verdict is Verdict.PASS
    assert ffmpeg.native_calls == 1


@pytest.mark.asyncio
async def test_gate_disabled_by_config(tmp_path: Path) -> None:
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"spectral.enabled": False},
    )
    job = _make_job(tmp_path)

    result = await run_spectral_check(job, config, _FakeFfmpeg(100.0, 44_100))

    assert result.verdict is Verdict.NOT_APPLICABLE
