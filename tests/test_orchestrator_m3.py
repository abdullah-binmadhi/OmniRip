from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.config import load_config
from harvester.models import CanonicalMetadata, SourceKind, State
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
        return np.zeros(int(48_000 * duration_s), dtype=np.float32)

    async def transcode_to_mp3(
        self, input_path: Path, output_path: Path, *, job_id: str | None = None
    ):
        output_path.write_bytes(b"fake-mp3")
        return output_path


class FakeTagger:
    def __init__(self, recording: dict[str, object]) -> None:
        self.recordings = recording

    async def tag_mp3_async(self, path, metadata, **kwargs):
        self.recordings["mp3"] = metadata
        return path

    async def tag_flac_async(self, path, metadata, **kwargs):
        self.recordings["flac"] = metadata
        return path


class FakeAcoustid:
    def __init__(self, metadata: CanonicalMetadata | None) -> None:
        self.metadata = metadata

    async def identify(self, path: Path, *, job_id: str | None = None):
        return self.metadata

    async def close(self) -> None:
        return None


class FakeCover:
    def __init__(self) -> None:
        self.fetched: list[str] = []

    async def fetch_front(self, release_id: str) -> bytes | None:
        self.fetched.append(release_id)
        return b"JPEGDATA"

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
                        filename="ground truth - song.flac",
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


def _build(
    tmp_path: Path,
    acoustid_metadata: CanonicalMetadata | None,
):
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output")},
    )
    slskd = FakeSlskd(tmp_path / "peers")
    slskd.config = config
    recorder: dict[str, object] = {}
    tagger = FakeTagger(recorder)
    return (
        PipelineOrchestrator(
            config,
            ytdlp=FakeYtdlp(),
            ffmpeg=FakeFfmpeg(),
            tagger=tagger,
            slskd=slskd,
            acoustid=FakeAcoustid(acoustid_metadata),
            cover=FakeCover(),
        ),
        recorder,
    )


@pytest.mark.asyncio
async def test_ground_truth_metadata_reaches_flac_output(tmp_path: Path) -> None:
    canonical = CanonicalMetadata(
        title="Real Title",
        artists=("Real Artist",),
        album="Album",
        year=1987,
        mb_recording_id="rec-1",
        mb_release_id="rel-1",
        confidence=0.95,
        source="acoustid",
    )
    orchestrator, recorder = _build(tmp_path, canonical)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.source_kind is SourceKind.P2P_FLAC
    assert job.output_path == tmp_path / "output" / "Real Artist - Real Title.flac"
    assert recorder["flac"] is canonical
    await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_no_match_falls_back_to_probe_metadata(tmp_path: Path) -> None:
    orchestrator, recorder = _build(tmp_path, None)

    job = await orchestrator.submit_url("https://example.test/watch?v=1")
    await orchestrator.wait_for_idle(timeout_s=5)

    assert job.state is State.COMPLETED
    assert job.canonical_meta.source == "probe"
    assert recorder["flac"].title == "Fallback Song"
    await orchestrator.shutdown()
