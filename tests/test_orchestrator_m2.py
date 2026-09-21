from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.config import load_config
from harvester.models import EventKind, SourceKind, State
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.services.slskd import SearchResponse, SlskdFile
from harvester.util.circuit import CircuitBreaker
from harvester.util.errors import TransientNetwork


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
        path = workspace_dir / f"{job_id}.webm"
        path.write_bytes(b"fake")
        return path


class FakeFfmpeg:
    async def source_kind(self, path: Path, *, job_id: str | None = None):
        from harvester.models import SourceKind

        return SourceKind.STREAM_OPUS

    async def probe_duration(self, path: Path, *, job_id: str | None = None):
        return 1

    async def probe_sample_rate(self, path: Path, *, job_id: str | None = None):
        return 44_100

    async def probe_bit_depth(self, path: Path, *, job_id: str | None = None):
        return None

    async def decode_f32(
        self,
        path: Path,
        *,
        offset_s: float = 0.0,
        duration_s: float = 5.0,
        channels: int = 1,
        job_id: str | None = None,
    ):
        # Near-silent excerpt -> real analyzer answers INCONCLUSIVE -> lax default PASS.
        return np.zeros(int(48_000 * duration_s), dtype=np.float32)

    async def transcode_to_mp3(
        self, input_path: Path, output_path: Path, *, job_id: str | None = None
    ):
        output_path.write_bytes(b"fake-mp3")
        return output_path


class FakeTagger:
    async def tag_mp3_async(self, path, metadata, **kwargs):
        return path

    async def tag_flac_async(self, path, metadata, **kwargs):
        return path


def _write_flac(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.zeros((44100, 2), dtype=np.int16)
    sf.write(path, data, 44100, format="FLAC", subtype="PCM_16")


class FakeSlskd:
    def __init__(
        self,
        *,
        available: bool = True,
        fail_first_download: bool = False,
        download_dir: Path | None = None,
        queue_length: int = 0,
    ) -> None:
        self.available = available
        self.breaker = CircuitBreaker()
        self.download_calls = 0
        self.search_calls = 0
        self.fail_first_download = fail_first_download
        self.download_dir = download_dir or Path("/tmp/harvester-test-flac")
        self.queue_length = queue_length

    async def search(self, queries, *, timeout_s, poll_interval_s=None):
        self.search_calls += 1
        response = SearchResponse(
            user="peer",
            speed_kbps=1200,
            queue_length=self.queue_length,
            files=(
                SlskdFile(
                    filename="test artist - test song.flac",
                    size_bytes=120_000,
                    duration_s=1.0,
                    bit_depth=16,
                    sample_rate=44100,
                ),
                SlskdFile(
                    filename="test artist - test song (alternate).flac",
                    size_bytes=120_000,
                    duration_s=1.0,
                    bit_depth=16,
                    sample_rate=44100,
                ),
            ),
        )
        return [response]

    async def download(self, candidate, *, download_dir=None):
        self.download_calls += 1
        if self.fail_first_download and self.download_calls == 1:
            raise TransientNetwork("candidate unavailable")
        path = self.download_dir / candidate.filename
        _write_flac(path)
        return path

    async def close(self) -> None:
        return None


def _orchestrator(
    tmp_path: Path,
    slskd: FakeSlskd | None = None,
    *,
    overrides: dict[str, object] | None = None,
) -> PipelineOrchestrator:
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={
            "general.output_dir": str(tmp_path / "output"),
            **(overrides or {}),
        },
    )
    active = slskd or FakeSlskd(download_dir=tmp_path / "peers")
    active.config = config
    return PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger(),
        slskd=active,
    )


@pytest.mark.asyncio
async def test_p2p_hunt_downloads_verifies_and_finishes(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, FakeSlskd())

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.source_kind is SourceKind.P2P_FLAC
    assert job.workspace_path is not None
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_slskd_unavailable_fast_fails_to_fallback(tmp_path: Path) -> None:
    slskd = FakeSlskd(available=False)
    orchestrator = _orchestrator(tmp_path, slskd)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.fallback_attempted is True
    assert job.source_kind is SourceKind.STREAM_OPUS
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_candidate_failure_retries_once_then_finishes(tmp_path: Path) -> None:
    slskd = FakeSlskd(fail_first_download=True)
    orchestrator = _orchestrator(tmp_path, slskd)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.p2p_retries == 1
    assert slskd.download_calls == 2
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_fast_fallback_policy_skips_p2p_lane(tmp_path: Path) -> None:
    slskd = FakeSlskd()
    orchestrator = _orchestrator(
        tmp_path,
        slskd,
        overrides={"slskd.acquisition_mode": "fast_fallback"},
    )

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.fallback_attempted is True
    assert job.source_kind is SourceKind.STREAM_OPUS
    assert slskd.search_calls == 0
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_highest_quality_mp3_policy_skips_p2p_lane(tmp_path: Path) -> None:
    slskd = FakeSlskd()
    orchestrator = _orchestrator(
        tmp_path,
        slskd,
        overrides={"slskd.acquisition_mode": "highest_quality_mp3"},
    )

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.fallback_attempted is True
    assert job.source_kind is SourceKind.STREAM_OPUS
    assert slskd.search_calls == 0
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_best_available_rejects_peer_with_long_queue(tmp_path: Path) -> None:
    slskd = FakeSlskd(queue_length=50)
    orchestrator = _orchestrator(
        tmp_path,
        slskd,
        overrides={"slskd.acquisition_mode": "best_available", "slskd.max_queue_length": 5},
    )

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.fallback_attempted is True
    assert job.source_kind is SourceKind.STREAM_OPUS
    assert slskd.search_calls == 1
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_p2p_path_emits_download_state_events(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, FakeSlskd())

    await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)
    events = []
    while not orchestrator.events.empty():
        events.append(orchestrator.events.get_nowait())
    states = [event.state for event in events if event.kind is EventKind.STATE]

    assert State.HUNTING in states
    assert State.P2P_DOWNLOADING in states
    assert State.COMPLETED in states
    await orchestrator.shutdown()
