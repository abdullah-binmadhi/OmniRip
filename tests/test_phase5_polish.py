"""Phase 5 polish unit tests: path helpers, target selection, keep-opus guard."""

from __future__ import annotations

import pytest

from harvester.config import load_config
from harvester.models import CanonicalMetadata, Mode, SourceKind, TrackJob
from harvester.pipeline.phase5_polish import (
    _batch_target_path,
    _choose_output_path,
    _mutagen_parses,
    _safe_component,
    _verify_temporary,
    polish_stream,
)
from harvester.util.errors import ConfigError, ValidationError


def _config(tmp_path, **overrides):
    return load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"general.output_dir": str(tmp_path / "output"), **overrides},
    )


def test_safe_component_sanitizes_and_reserves() -> None:
    assert _safe_component("a/b:c*d") == "a_b_c_d"
    assert _safe_component("CON") == "_CON"
    assert _safe_component("...") == "untitled"
    assert len(_safe_component("x" * 300)) <= 180


def test_choose_output_path_collision_suffix(tmp_path) -> None:
    metadata = CanonicalMetadata(title="Title", artists=("Artist",))
    first = _choose_output_path(tmp_path, metadata, "id", ".mp3")
    first.write_bytes(b"x")

    second = _choose_output_path(tmp_path, metadata, "id", ".mp3")

    assert second.name == "Artist - Title (2).mp3"


def test_batch_target_default_keeps_original_path(tmp_path) -> None:
    config = _config(tmp_path)
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=tmp_path / "song.mp3")
    metadata = CanonicalMetadata(title="New", artists=("Artist",))

    target = _batch_target_path(job, config, metadata, tmp_path, ".flac")

    assert target == job.input_path


def test_batch_target_canonical_when_enabled(tmp_path) -> None:
    config = _config(tmp_path, **{"batch.rename_to_canonical": True})
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=tmp_path / "song.mp3")
    metadata = CanonicalMetadata(title="New Title", artists=("Artist",))

    target = _batch_target_path(job, config, metadata, tmp_path, ".flac")

    assert target == tmp_path / "Artist - New Title.flac"


def test_mutagen_parses_rejects_garbage(tmp_path) -> None:
    path = tmp_path / "garbage.mp3"
    path.write_bytes(b"not an audio file")

    assert _mutagen_parses(path) is False


@pytest.mark.asyncio
async def test_verify_temporary_rejects_unparseable(tmp_path) -> None:
    path = tmp_path / "garbage.mp3"
    path.write_bytes(b"not audio")
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=tmp_path / "orig.mp3")

    class FakeFfmpeg:
        async def probe_duration(self, path, *, job_id=None):
            return 1

    with pytest.raises(ValidationError, match="parseable"):
        await _verify_temporary(job, FakeFfmpeg(), path)


@pytest.mark.asyncio
async def test_polish_stream_rejects_keep_opus(tmp_path) -> None:
    config = _config(tmp_path, **{"ffmpeg.transcode": "keep-opus"})
    job = TrackJob(mode=Mode.SINGLE_URL, source_kind=SourceKind.STREAM_OPUS)
    job.workspace_path = tmp_path / "w.webm"
    job.workspace_path.write_bytes(b"x")

    with pytest.raises(ConfigError, match="keep-opus"):
        await polish_stream(job, config, None, None)


@pytest.mark.asyncio
async def test_polish_stream_requires_workspace(tmp_path) -> None:
    config = _config(tmp_path)
    job = TrackJob(mode=Mode.SINGLE_URL, source_kind=SourceKind.STREAM_OPUS)

    with pytest.raises(ValidationError, match="workspace"):
        await polish_stream(job, config, None, None)
