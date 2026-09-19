"""Trash lifecycle tests: layout, collisions, byte-identical rollback, purge."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from harvester.batch.trash import move_to_trash, purge, rollback, trash_root_for
from harvester.util.errors import DiskError


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_move_lands_in_dated_trash_directory(tmp_path: Path) -> None:
    original = _write(tmp_path / "music" / "song.mp3", b"ORIGINAL")
    trash = move_to_trash(original, tmp_path / "music")

    day_dir = datetime.now(UTC).strftime("%Y-%m-%d")
    assert trash.parent.name == day_dir
    assert trash.parent.parent == trash_root_for(tmp_path / "music")
    assert trash.name.endswith("-song.mp3")
    assert not original.exists()
    assert trash.read_bytes() == b"ORIGINAL"


def test_same_day_collision_gets_numeric_suffix(tmp_path: Path) -> None:
    music = tmp_path / "music"
    first = _write(music / "song.mp3", b"FIRST")
    second = _write(music / "sub" / "song.mp3", b"SECOND")

    first_trash = move_to_trash(first, music)
    second_trash = move_to_trash(second, music)

    assert first_trash != second_trash
    assert first_trash.read_bytes() == b"FIRST"
    assert second_trash.read_bytes() == b"SECOND"


def test_rollback_restores_byte_identical(tmp_path: Path) -> None:
    original = _write(tmp_path / "music" / "song.mp3", b"PRECIOUS BYTES")
    trash = move_to_trash(original, tmp_path / "music")

    restored = rollback(trash, original)

    assert restored == original
    assert original.read_bytes() == b"PRECIOUS BYTES"
    assert not trash.exists()


def test_trash_requires_existing_file(tmp_path: Path) -> None:
    with pytest_raises_disk_error():
        move_to_trash(tmp_path / "music" / "missing.mp3", tmp_path / "music")


def test_purge_removes_expired_days_only(tmp_path: Path) -> None:
    music = tmp_path / "music"
    trash = trash_root_for(music)
    old = trash / (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    fresh = trash / datetime.now(UTC).strftime("%Y-%m-%d")
    old.mkdir(parents=True)
    fresh.mkdir(parents=True)

    removed = purge(music, retention_days=7)

    assert removed == 1
    assert not old.exists()
    assert fresh.exists()


def test_purge_survives_missing_or_garbage_dirs(tmp_path: Path) -> None:
    music = tmp_path / "music"
    (trash_root_for(music) / "not-a-date").mkdir(parents=True)

    assert purge(music, retention_days=7) == 0


def pytest_raises_disk_error():
    import pytest

    return pytest.raises(DiskError)
