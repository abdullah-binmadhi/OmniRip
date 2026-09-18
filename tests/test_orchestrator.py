from pathlib import Path

import pytest

from harvester.config import load_config
from harvester.models import EventKind, State
from harvester.pipeline.orchestrator import PipelineOrchestrator


class FakeYtdlp:
    async def probe_url(self, url: str, *, job_id: str | None = None):
        return {
            "title": "Test Artist - Test Song",
            "uploader": "Test Artist",
            "duration": 1,
            "webpage_url": url,
        }

    async def download(self, url: str, workspace_dir: Path, *, job_id: str, progress_callback=None):
        workspace_dir.mkdir(parents=True, exist_ok=True)
        if progress_callback:
            await progress_callback(type("Progress", (), {"percent": 50, "bytes_done": 1})())
        path = workspace_dir / f"{job_id}.webm"
        path.write_bytes(b"fake")
        return path


class FakeFfmpeg:
    async def source_kind(self, path: Path, *, job_id: str | None = None):
        from harvester.models import SourceKind

        return SourceKind.STREAM_OPUS

    async def probe_duration(self, path: Path, *, job_id: str | None = None):
        return 1

    async def transcode_to_mp3(
        self, input_path: Path, output_path: Path, *, job_id: str | None = None
    ):
        output_path.write_bytes(b"fake-mp3")
        return output_path


class FakeTagger:
    async def tag_mp3_async(self, path, metadata, **kwargs):
        return path


class FakeSlskdOffline:
    """Deterministic stand-in for an unreachable slskd daemon."""

    available = False
    config = None

    def __init__(self, config) -> None:
        from harvester.util.circuit import CircuitBreaker

        self.config = config
        self.breaker = CircuitBreaker()

    async def search(self, queries, *, timeout_s, poll_interval_s=None):
        return []

    async def download(self, candidate, *, download_dir=None):
        from harvester.util.errors import ServiceUnavailable

        raise ServiceUnavailable("slskd lane is unavailable")

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_orchestrator_runs_fallback_path_with_fake_services(tmp_path: Path):
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output")},
    )
    orchestrator = PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger(),
        slskd=FakeSlskdOffline(config),
    )

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.output_path == tmp_path / "output" / "Test Artist - Test Song.mp3"
    events = []
    while not orchestrator.events.empty():
        events.append(orchestrator.events.get_nowait())
    states = [event.state for event in events if event.kind is EventKind.STATE]
    assert State.FALLBACK_DOWNLOADING in states
    assert State.COMPLETED in states
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_orchestrator_cancel_marks_job_cancelled(tmp_path: Path):
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    orchestrator = PipelineOrchestrator(
        config, ytdlp=FakeYtdlp(), ffmpeg=FakeFfmpeg(), tagger=FakeTagger()
    )
    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.cancel(job.id)

    assert job.state is State.CANCELLED
    await orchestrator.shutdown()
