"""Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from harvester.models import Mode, SourceKind, TrackJob
from harvester.pipeline import phase5_polish as phase5
from harvester.util.errors import DiskError


def _job(music: Path, batch_root: Path, name: str = "song.mp3") -> TrackJob:
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=music / name, batch_root=batch_root)
    job.orig_bitrate = 128
    job.source_kind = SourceKind.STREAM_OPUS
    return job


def test_swap_success_replaces_and_trashes(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    original = music / "song.mp3"
    original.write_bytes(b"OLD-BYTES")
    temp = music / ".song.jobid.harvester.tmp.mp3"
    temp.write_bytes(b"NEW-BYTES")
    job = _job(music, music)

    trash_path = phase5._swap_into_place(job, temp, original, music)

    assert original.read_bytes() == b"NEW-BYTES"
    assert trash_path.read_bytes() == b"OLD-BYTES"
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    assert trash_path.parent.name == day
    assert trash_path.parent.parent == music / ".trash"
    assert not temp.exists()


def test_swap_failure_between_trash_and_replace_rolls_back(tmp_path: Path, monkeypatch) -> None:
    music = tmp_path / "music"
    music.mkdir()
    original = music / "song.mp3"
    original.write_bytes(b"PRECIOUS")
    temp = music / ".song.jobid.harvester.tmp.mp3"
    temp.write_bytes(b"NEW-BYTES")
    job = _job(music, music)

    def _boom(source, destination):
        raise OSError("injected replace failure")

    monkeypatch.setattr(phase5.os, "replace", _boom)

    with pytest.raises(DiskError, match="swap failed"):
        phase5._swap_into_place(job, temp, original, music)

    assert original.read_bytes() == b"PRECIOUS"  # rollback restored, byte-identical
    trash_root = music / ".trash"
    files = [p for p in trash_root.rglob("*") if p.is_file()] if trash_root.exists() else []
    assert files == []  # only the (empty) day directory may remain
    assert temp.exists()  # the caller cleans the temp, not the swap


def test_swap_with_nested_file_uses_batch_root_for_trash(tmp_path: Path) -> None:
    root = tmp_path / "music"
    original_dir = root / "sub dir"
    original_dir.mkdir(parents=True)
    original = original_dir / "song.mp3"
    original.write_bytes(b"OLD")
    temp = original_dir / ".song.jobid.harvester.tmp.mp3"
    temp.write_bytes(b"NEW")
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=original, batch_root=root)

    trash_path = phase5._swap_into_place(job, temp, original, original_dir)

    # .trash lives in the scanned root, not the file's subdirectory (docs/02 §3).
    assert trash_path.parent.parent == root / ".trash"
    assert original.read_bytes() == b"NEW"