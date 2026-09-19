"""Playlist expansion orchestration tests (docs/03 Phase 1A §3, D10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from harvester.config import load_config
from harvester.models import Mode, SourceKind
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.util.circuit import CircuitBreaker
from harvester.util.errors import PermanentSource, ValidationError


class FakeYtdlp:
    def __init__(self, entries: list[dict] | None = None) -> None:
        self.entries = entries or []

    async def probe_playlist(self, url: str, *, job_id: str | None = None):
        return self.entries

    async def probe_url(self, url: str, *, job_id: str | None = None):
        return {"title": "T", "uploader": "A", "duration": 1}

    async def download(self, url: str, workspace_dir: Path, *, job_id: str, progress_callback=None):
        raise PermanentSource("not used in this test")


class FakeSlskd:
    available = False

    def __init__(self, config) -> None:
        self.config = config
        self.breaker = CircuitBreaker()

    async def search(self, *args, **kwargs):
        raise RuntimeError("offline")

    async def close(self) -> None:
        return None


class FakeFfmpeg:
    async def source_kind(self, path: Path, *, job_id: str | None = None):
        return SourceKind.STREAM_OPUS

    async def probe_duration(self, path: Path, *, job_id: str | None = None):
        return 1

    async def transcode_to_mp3(self, *args, **kwargs):
        return Path("out.mp3")

    async def probe_sample_rate(self, path: Path, *, job_id: str | None = None):
        return 44_100

    async def decode_f32(self, *args, **kwargs):
        return []


class FakeTagger:
    async def tag_mp3_async(self, *args, **kwargs):
        return args[0]

    async def tag_flac_async(self, *args, **kwargs):
        return args[0]


class FakeAcoustid:
    async def identify(self, *args, **kwargs):
        return None

    async def close(self) -> None:
        return None


class FakeCover:
    async def fetch_front(self, release_id: str) -> bytes | None:
        return None

    async def close(self) -> None:
        return None


def _orchestrator(tmp_path: Path, entries: list[dict]):
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={
            "general.output_dir": str(tmp_path / "output"),
            "batch.playlist_cap": 5,
        },
    )
    slskd = FakeSlskd(config)
    return PipelineOrchestrator(
        config,
        ytdlp=FakeYtdlp(entries),
        ffmpeg=FakeFfmpeg(),
        tagger=FakeTagger(),
        slskd=slskd,
        acoustid=FakeAcoustid(),
        cover=FakeCover(),
    )


def _entries(count: int) -> list[dict]:
    return [
        {"id": f"id-{i}", "url": f"https://example.test/watch?v={i}", "title": f"Track {i}"}
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_probe_playlist_is_capped(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, _entries(9))

    entries = await orchestrator.probe_playlist("https://example.test/playlist")

    assert len(entries) == 5  # capped at batch.playlist_cap
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_submit_playlist_requires_confirmation(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, _entries(3))

    with pytest.raises(ValidationError, match="confirmation required"):
        await orchestrator.submit_playlist("https://example.test/playlist", confirmed=False)
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_submit_playlist_creates_child_jobs(tmp_path: Path) -> None:
    orchestrator = _orchestrator(tmp_path, _entries(3))

    jobs = await orchestrator.submit_playlist("https://example.test/playlist", confirmed=True)

    assert len(jobs) == 3
    assert all(job.mode is Mode.SINGLE_URL for job in jobs)
    assert {job.input_url for job in jobs} == {
        "https://example.test/watch?v=0",
        "https://example.test/watch?v=1",
        "https://example.test/watch?v=2",
    }
    assert len(orchestrator.jobs) == 3
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_submit_playlist_skips_non_http_entries(tmp_path: Path) -> None:
    entries = _entries(2) + [{"id": "stray"}]
    orchestrator = _orchestrator(tmp_path, entries)

    jobs = await orchestrator.submit_playlist("https://example.test/playlist", confirmed=True)

    assert len(jobs) == 2
    await orchestrator.shutdown()
