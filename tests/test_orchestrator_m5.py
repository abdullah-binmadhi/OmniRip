"""Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.batch.report import BatchReport
from harvester.config import load_config
from harvester.models import CanonicalMetadata, Mode, SourceKind, State
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.services.slskd import SearchResponse, SlskdFile
from harvester.util.circuit import CircuitBreaker
from harvester.util.errors import PermanentSource, ValidationError


def write_mp3(path: Path, bitrate_bps: int, n_frames: int = 4) -> Path:
    """Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)."""

    index = {128_000: 9, 192_000: 11, 256_000: 13}[bitrate_bps]
    frame_length = 144 * bitrate_bps // 44_100
    header = bytes([0xFF, 0xFB, index << 4, 0x00])
    path.write_bytes((header + b"\x00" * (frame_length - 4)) * n_frames)
    return path


def mp3_duration_s(n_frames: int = 4) -> float:
    return n_frames * 1152 / 44_100


def write_flac(path: Path) -> Path:
    sf.write(path, np.zeros(4410, dtype=np.float32), 44_100, format="FLAC")
    return path


_LOW_DURATION = mp3_duration_s()


class FakeYtdlp:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def probe_url(self, url: str, *, job_id: str | None = None):
        return {"title": "Fallback Artist - Fallback Song", "uploader": "Fallback", "duration": 1}

    async def download(self, url: str, workspace_dir: Path, *, job_id: str, progress_callback=None):
        if self.fail:
            raise PermanentSource("cannot fetch this track")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        path = workspace_dir / f"{job_id}.webm"
        path.write_bytes(b"fake")
        return path


class FakeFfmpeg:
    def __init__(self, duration: float = 1.0) -> None:
        self.duration = duration

    async def source_kind(self, path: Path, *, job_id: str | None = None):
        return SourceKind.STREAM_OPUS

    async def probe_duration(self, path: Path, *, job_id: str | None = None):
        return self.duration

    async def probe_sample_rate(self, path: Path, *, job_id: str | None = None):
        return 44_100

    async def decode_f32(
        self,
        path: Path,
        *,
        offset_s: float = 0.0,
        duration_s: float = 5.0,
        job_id: str | None = None,
    ):
        # Near-silent excerpt -> real analyzer answers INCONCLUSIVE -> lax default PASS.
        return np.zeros(int(48_000 * 0.7), dtype=np.float32)

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
    def __init__(self, metadata: CanonicalMetadata | None = None) -> None:
        self.metadata = metadata

    async def identify(self, path: Path, *, job_id: str | None = None):
        return self.metadata

    async def close(self) -> None:
        return None


class FakeCover:
    async def fetch_front(self, release_id: str) -> bytes | None:
        return None

    async def close(self) -> None:
        return None


class FakeSlskd:
    available = True

    def __init__(self, peer_dir: Path, duration: float) -> None:
        self.peer_dir = peer_dir
        self.duration = duration
        self.breaker = CircuitBreaker()

    async def search(self, queries, *, timeout_s, poll_interval_s=None):
        return [
            SearchResponse(
                user="peer",
                speed_kbps=1200,
                queue_length=0,
                files=(
                    SlskdFile(
                        filename="Artist - Track.flac",
                        size_bytes=12_000,
                        duration_s=self.duration,
                        bit_depth=16,
                        sample_rate=44100,
                    ),
                ),
            )
        ]

    async def download(self, candidate, *, download_dir=None):
        path = self.peer_dir / candidate.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        data = np.zeros((int(self.duration * 44100), 1), dtype=np.float32)
        sf.write(path, data, 44100, format="FLAC")
        return path

    async def close(self) -> None:
        return None


class FakeSlskdOffline:
    """Deterministic stand-in for an unreachable slskd daemon (forces the fallback lane)."""

    available = False

    def __init__(self, config) -> None:
        self.config = config
        self.breaker = CircuitBreaker()

    async def search(self, queries, *, timeout_s, poll_interval_s=None):
        raise RuntimeError("unreachable")

    async def close(self) -> None:
        return None


def _build(
    tmp_path: Path,
    *,
    acoustid_metadata=None,
    ytdlp: FakeYtdlp | None = None,
    slskd_offline: bool = False,
):
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output")},
    )
    if slskd_offline:
        slskd = FakeSlskdOffline(config)
    else:
        peer_dir = tmp_path / "peers"
        slskd = FakeSlskd(peer_dir, _LOW_DURATION)
        slskd.config = config
    recording: dict[str, object] = {}
    orchestrator = PipelineOrchestrator(
        config,
        ytdlp=ytdlp or FakeYtdlp(),
        ffmpeg=FakeFfmpeg(duration=_LOW_DURATION),
        tagger=FakeTagger(recording),
        slskd=slskd,  # type: ignore[arg-type]
        acoustid=FakeAcoustid(acoustid_metadata),
        cover=FakeCover(),
    )
    return orchestrator, recording


def _mixed_library(tmp_path: Path) -> Path:
    music = tmp_path / "library"
    music.mkdir()
    write_flac(music / "keep.flac")
    write_mp3(music / "high.mp3", 256_000)
    low = music / "03 - Artist - Track.mp3"
    write_mp3(low, 128_000)
    return music


@pytest.mark.asyncio
async def test_batch_audit_mixed_directory_ac5(tmp_path: Path) -> None:
    orchestrator, recording = _build(tmp_path)
    music = _mixed_library(tmp_path)

    scan = await orchestrator.submit_batch(music, confirmed=False)
    await orchestrator.wait_for_idle(timeout_s=10)

    assert len(scan.queued) == 1
    jobs = list(orchestrator.jobs.values())
    assert len(jobs) == 1
    job = jobs[0]
    assert job.mode is Mode.BATCH_AUDIT
    assert job.state is State.COMPLETED
    assert job.source_kind is SourceKind.P2P_FLAC
    assert recording["flac"] is not None

    # Original filename preserved (D4) and replaced with the lossless content.
    assert job.output_path == music / "03 - Artist - Track.mp3"
    assert music.joinpath("03 - Artist - Track.mp3").is_file()
    assert recording["flac"] is not None
    assert job.trash_path is not None and job.trash_path.is_file()
    assert job.trash_path.parent.parent == music / ".trash"
    # The trashed original is byte-identical to the pre-swap file.
    assert job.trash_path.read_bytes() == write_mp3_bytes(job.input_path.name)

    # Lossless and high-bitrate files untouched.
    assert (music / "keep.flac").is_file()
    assert (music / "high.mp3").is_file()

    # Report lists every input file exactly once (AC-5).
    report = BatchReport(orchestrator._batch_reports[job.id].path)
    rows = report.rows()
    assert len(rows) == 3
    statuses = sorted(row["status"] for row in rows)
    assert statuses == ["skipped", "skipped", "upgraded"]
    inputs = {str(row["input"]) for row in rows}
    assert inputs == {
        str(music / "keep.flac"),
        str(music / "high.mp3"),
        str(music / "03 - Artist - Track.mp3"),
    }
    await orchestrator.shutdown()


def write_mp3_bytes(name: str) -> bytes:
    """Re-materialize the crafted 128 kbps MP3 for byte comparison."""

    index = {128_000: 9, 192_000: 11, 256_000: 13}[128_000]
    frame_length = 144 * 128_000 // 44_100
    header = bytes([0xFF, 0xFB, index << 4, 0x00])
    return (header + b"\x00" * (frame_length - 4)) * 4


@pytest.mark.asyncio
async def test_batch_over_25_requires_confirmation(tmp_path: Path) -> None:
    orchestrator, _ = _build(tmp_path)
    music = tmp_path / "many"
    music.mkdir()
    for index in range(26):
        write_mp3(music / f"track-{index:02d}.mp3", 128_000)

    scan = await orchestrator.scan_batch(music)

    with pytest.raises(ValidationError, match="confirmation required"):
        await orchestrator.submit_batch(scan=scan, confirmed=False)

    await orchestrator.submit_batch(scan=scan, confirmed=True)
    assert len(orchestrator.jobs) == 26
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_batch_free_space_guard_blocks_queue(tmp_path: Path, monkeypatch) -> None:
    orchestrator, _ = _build(tmp_path)
    music = tmp_path / "library"
    music.mkdir()
    write_mp3(music / "low.mp3", 128_000)

    import harvester.batch.scanner as scanner_module

    monkeypatch.setattr(
        scanner_module.shutil, "disk_usage", lambda path: type("DU", (), {"free": 1_000_000})()
    )

    from harvester.util.errors import DiskError

    with pytest.raises(DiskError, match="not enough free space"):
        await orchestrator.submit_batch(music, confirmed=False)
    assert orchestrator.jobs == {}
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_batch_failure_writes_failed_report_row(tmp_path: Path) -> None:
    orchestrator, _ = _build(tmp_path, ytdlp=FakeYtdlp(fail=True), slskd_offline=True)
    music = tmp_path / "library"
    music.mkdir()
    write_mp3(music / "low.mp3", 128_000)

    scan = await orchestrator.submit_batch(music, confirmed=False)
    await orchestrator.wait_for_idle(timeout_s=10)

    job = list(orchestrator.jobs.values())[0]
    assert job.state is State.FAILED
    report = BatchReport(orchestrator._batch_reports[job.id].path)
    rows = report.rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["job_id"] == job.id
    assert rows[0]["error"]
    assert scan.queued[0].path == music / "low.mp3"
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_batch_identity_shift_recorded_when_tags_diverge(tmp_path: Path) -> None:
    from mutagen.id3 import ID3, TIT2

    orchestrator, _ = _build(
        tmp_path,
        acoustid_metadata=CanonicalMetadata(
            title="Completely Different Song",
            artists=("Another Artist",),
            confidence=0.9,
            source="acoustid",
        ),
    )
    music = tmp_path / "library"
    music.mkdir()
    low = music / "low.mp3"
    write_mp3(low, 128_000)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=["Original Title"]))
    tags.save(low)

    await orchestrator.submit_batch(music, confirmed=False)
    await orchestrator.wait_for_idle(timeout_s=10)

    job = list(orchestrator.jobs.values())[0]
    assert job.state is State.COMPLETED
    assert job.canonical_meta is not None
    assert job.identity_shift is True  # recording MBID unknown, title similarity < 50%
    report = BatchReport(orchestrator._batch_reports[job.id].path)
    row = report.rows()[0]
    assert row["identity_shift"] is True
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_purge_trash_for_last_batch(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    from harvester.batch.trash import trash_root_for

    orchestrator, _ = _build(tmp_path)
    music = _mixed_library(tmp_path)
    await orchestrator.submit_batch(music, confirmed=False)
    await orchestrator.wait_for_idle(timeout_s=10)

    old_day = trash_root_for(music) / (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    old_day.mkdir(parents=True)
    (old_day / "stale.mp3").write_bytes(b"x")

    removed = await orchestrator.purge_batch_trash()

    assert removed == 1
    assert not old_day.exists()
    await orchestrator.shutdown()
