from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.config import load_config
from harvester.models import SourceKind, SpectralResult, State, TrackJob, Verdict
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.services.slskd import SearchResponse, SlskdFile
from harvester.util.circuit import CircuitBreaker


class FakeYtdlp:
    async def probe_url(self, url: str, *, job_id: str | None = None):
        return {
            "title": "Fallback Artist - Fallback Song",
            "uploader": "Fallback Artist",
            "duration": 1,
            "webpage_url": url,
        }

    async def download(self, url: str, workspace_dir: Path, *, job_id: str, progress_callback=None):
        workspace_dir.mkdir(parents=True, exist_ok=True)
        path = workspace_dir / f"{job_id}.webm"
        path.write_bytes(b"fake")
        return path


class FakeFfmpeg:
    async def source_kind(self, path: Path, *, job_id: str | None = None):
        return SourceKind.STREAM_OPUS

    async def probe_duration(self, path: Path, *, job_id: str | None = None):
        return 1

    async def transcode_to_mp3(
        self, input_path: Path, output_path: Path, *, job_id: str | None = None
    ):
        output_path.write_bytes(b"fake-mp3")
        return output_path


class FakeTagger:
    def __init__(self, recording: dict[str, object]) -> None:
        self.recording = recording

    async def tag_mp3_async(self, path, metadata, **kwargs):
        self.recording["mp3"] = metadata
        return path

    async def tag_flac_async(self, path, metadata, **kwargs):
        self.recording["flac"] = metadata
        return path


class FakeAcoustid:
    async def identify(self, path: Path, *, job_id: str | None = None):
        return None

    async def close(self) -> None:
        return None


class FakeCover:
    async def fetch_front(self, release_id: str) -> bytes | None:
        return None

    async def close(self) -> None:
        return None


class FakeSlskd:
    available = True

    def __init__(self, flac_dir: Path) -> None:
        self.flac_dir = flac_dir
        self.breaker = CircuitBreaker()

    async def search(self, queries, *, timeout_s, poll_interval_s=None):
        return [
            SearchResponse(
                user="peer",
                speed_kbps=1200,
                queue_length=0,
                files=(
                    SlskdFile(
                        filename="fraud check - song.flac",
                        size_bytes=120_000,
                        duration_s=1.0,
                        bit_depth=16,
                        sample_rate=44100,
                    ),
                ),
            )
        ]

    async def download(self, candidate, *, download_dir=None):
        path = self.flac_dir / candidate.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        data = np.zeros((44100, 2), dtype=np.int16)
        sf.write(path, data, 44100, format="FLAC", subtype="PCM_16")
        return path

    async def close(self) -> None:
        return None


def _build(tmp_path: Path):
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output")},
    )
    slskd = FakeSlskd(tmp_path / "peers")
    slskd.config = config
    recording: dict[str, object] = {}
    orchestrator = PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger(recording),
        slskd=slskd,
        acoustid=FakeAcoustid(),
        cover=FakeCover(),
    )
    return orchestrator, recording


@pytest.mark.asyncio
async def test_fraud_reroutes_to_fallback(tmp_path: Path, monkeypatch) -> None:
    async def fake_spectral(job: TrackJob, config, ffmpeg) -> SpectralResult:
        job.spectral = SpectralResult(
            verdict=Verdict.FRAUD, cutoff_hz=16_000.0, steepness_db_per_khz=38.0
        )
        return job.spectral

    monkeypatch.setattr("harvester.pipeline.orchestrator.run_spectral_check", fake_spectral)
    orchestrator, _ = _build(tmp_path)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.spectral.verdict is Verdict.FRAUD
    assert job.fallback_attempted is True
    assert job.source_kind is SourceKind.STREAM_OPUS
    assert job.state is State.COMPLETED
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_pass_proceeds_to_flac_polish(tmp_path: Path, monkeypatch) -> None:
    async def fake_spectral(job: TrackJob, config, ffmpeg) -> SpectralResult:
        job.spectral = SpectralResult(
            verdict=Verdict.PASS, cutoff_hz=22_000.0, steepness_db_per_khz=2.0
        )
        return job.spectral

    monkeypatch.setattr("harvester.pipeline.orchestrator.run_spectral_check", fake_spectral)
    orchestrator, recording = _build(tmp_path)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.spectral.verdict is Verdict.PASS
    assert job.state is State.COMPLETED
    assert recording["flac"] is not None
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_inconclusive_defaults_to_pass_and_strict_falls_back(
    tmp_path: Path, monkeypatch
) -> None:
    calls = {"count": 0}

    async def fake_spectral(job: TrackJob, config, ffmpeg) -> SpectralResult:
        calls["count"] += 1
        job.spectral = SpectralResult(
            verdict=Verdict.INCONCLUSIVE, cutoff_hz=18_000.0, steepness_db_per_khz=20.0
        )
        return job.spectral

    monkeypatch.setattr("harvester.pipeline.orchestrator.run_spectral_check", fake_spectral)
    lax, _ = _build(tmp_path)
    job = await lax.submit_url("https://example.test/watch?v=1")
    await lax.wait_for_idle(timeout_s=5)
    assert job.state is State.COMPLETED
    assert job.spectral.verdict is Verdict.INCONCLUSIVE
    assert job.fallback_attempted is False
    await lax.shutdown()

    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data-strict")},
        cli_overrides={
            "general.output_dir": str(tmp_path / "output-strict"),
            "spectral.strict": True,
        },
    )
    slskd = FakeSlskd(tmp_path / "peers-strict")
    slskd.config = config
    orchestrator = PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger({}),
        slskd=slskd,
        acoustid=FakeAcoustid(),
        cover=FakeCover(),
    )
    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)
    assert job.fallback_attempted is True
    assert job.state is State.COMPLETED
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_stream_path_never_enters_spectral_stage(tmp_path: Path, monkeypatch) -> None:
    calls = {"count": 0}

    async def fake_spectral(job: TrackJob, config, ffmpeg) -> SpectralResult:
        calls["count"] += 1
        return SpectralResult(verdict=Verdict.NOT_APPLICABLE)

    monkeypatch.setattr("harvester.pipeline.orchestrator.run_spectral_check", fake_spectral)
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output")},
    )
    orchestrator = PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger({}),
        acoustid=FakeAcoustid(),
        cover=FakeCover(),
    )

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert calls["count"] == 0
    assert job.spectral.verdict is Verdict.NOT_APPLICABLE
    assert job.source_kind is SourceKind.STREAM_OPUS
    await orchestrator.shutdown()
