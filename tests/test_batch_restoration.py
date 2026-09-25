"""Tests for Batch Library Auto-Restoration and Curation (M21)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from harvester.batch.restoration import (
    restore_directory,
    restore_file,
    safe_swap,
    should_restore_entry,
)
from harvester.util.errors import DiskError


def test_should_restore_entry(tmp_path: Path) -> None:
    # 1. Non-audio file
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    needs, codec, _ = should_restore_entry(txt)
    assert not needs
    assert codec == "non-audio"

    # 2. Lossless file
    flac = tmp_path / "song.flac"
    flac.write_bytes(b"FLAC" + b"\x00" * 100)
    needs, codec, _ = should_restore_entry(flac)
    assert not needs

    # 3. Low-bitrate mp3 (simulated via mock or unreadable)
    broken_mp3 = tmp_path / "broken.mp3"
    broken_mp3.write_bytes(b"\x00" * 50)
    needs, codec, _ = should_restore_entry(broken_mp3)
    # Mutagen will fail to read, so unreadable -> not restored
    assert not needs


def test_safe_swap_success(tmp_path: Path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    target = root / "song.mp3"
    target.write_bytes(b"ORIGINAL_AUDIO")

    temp = root / ".song.harvester.tmp.mp3"
    temp.write_bytes(b"ENHANCED_AUDIO")

    trash_path = safe_swap(temp, target, root)

    assert target.read_bytes() == b"ENHANCED_AUDIO"
    assert trash_path.read_bytes() == b"ORIGINAL_AUDIO"
    assert trash_path.is_file()
    assert ".trash" in str(trash_path)
    assert not temp.exists()


def test_safe_swap_rollback_on_failure(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "music"
    root.mkdir()
    target = root / "song.mp3"
    target.write_bytes(b"ORIGINAL_AUDIO")

    temp = root / ".song.harvester.tmp.mp3"
    temp.write_bytes(b"ENHANCED_AUDIO")

    def _broken_replace(src, dst):
        raise OSError("Simulated disk error during rename")

    monkeypatch.setattr(os, "replace", _broken_replace)

    with pytest.raises(DiskError, match="batch swap failed after trashing"):
        safe_swap(temp, target, root)

    # Original must be restored byte-for-byte
    assert target.read_bytes() == b"ORIGINAL_AUDIO"


def test_safe_swap_missing_files(tmp_path: Path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    target = root / "missing.mp3"
    temp = root / "temp.mp3"
    temp.write_bytes(b"DATA")

    with pytest.raises(DiskError, match="missing target file"):
        safe_swap(temp, target, root)

    target.write_bytes(b"TARGET")
    missing_temp = root / "missing_temp.mp3"
    with pytest.raises(DiskError, match="missing temporary file"):
        safe_swap(missing_temp, target, root)


def test_restore_file_dry_run(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "music"
    root.mkdir()
    song = root / "track.mp3"
    song.write_bytes(b"AUDIO")

    # Mock should_restore_entry to return True
    monkeypatch.setattr(
        "harvester.batch.restoration.should_restore_entry",
        lambda p, skip_bitrate_kbps=256: (True, "mp3", 128),
    )

    res = restore_file(song, root, dry_run=True, preset_name="extended_air")
    assert res.status == "dry_run"
    assert res.original_bitrate_kbps == 128
    assert res.applied_preset == "Extended Air (Hybrid)"
    assert song.read_bytes() == b"AUDIO"  # Untouched


def test_restore_file_skipped(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "music"
    root.mkdir()
    song = root / "high_quality.mp3"
    song.write_bytes(b"AUDIO")

    monkeypatch.setattr(
        "harvester.batch.restoration.should_restore_entry",
        lambda p, skip_bitrate_kbps=256: (False, "mp3", 320),
    )

    res = restore_file(song, root, dry_run=False)
    assert res.status == "skipped"
    assert res.original_bitrate_kbps == 320


def test_restore_file_success_and_purges_vram(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "music"
    root.mkdir()
    song = root / "lossy.mp3"
    song.write_bytes(b"ORIGINAL_BYTES")

    monkeypatch.setattr(
        "harvester.batch.restoration.should_restore_entry",
        lambda p, skip_bitrate_kbps=256: (True, "mp3", 128),
    )

    mock_exporter = MagicMock()

    def fake_export(input_path, preset, output_path, **kwargs):
        output_path.write_bytes(b"ENHANCED_BYTES")
        return output_path

    mock_exporter.export_enhanced_derivative = MagicMock(side_effect=fake_export)

    purge_mock = MagicMock()
    monkeypatch.setattr("harvester.batch.restoration.purge_neural_vram", purge_mock)

    res = restore_file(
        song,
        root,
        dry_run=False,
        preset_name="conservative",
        genre_override="Electronic",
        exporter=mock_exporter,
    )

    assert res.status == "restored"
    assert song.read_bytes() == b"ENHANCED_BYTES"
    assert res.trash_path is not None
    assert res.trash_path.read_bytes() == b"ORIGINAL_BYTES"
    # Ensure memory was purged for M2 16GB RAM headroom safety
    assert purge_mock.called


def test_restore_directory_end_to_end(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "album"
    root.mkdir()
    t1 = root / "01 - Intro.mp3"
    t1.write_bytes(b"OLD_1")
    t2 = root / "02 - Drop.mp3"
    t2.write_bytes(b"OLD_2")

    monkeypatch.setattr(
        "harvester.batch.restoration.should_restore_entry",
        lambda p, skip_bitrate_kbps=256: (True, "mp3", 128),
    )

    mock_exporter = MagicMock()

    def fake_export(input_path, preset, output_path, **kwargs):
        output_path.write_bytes(b"RESTORED_" + input_path.name.encode())
        return output_path

    mock_exporter.export_enhanced_derivative = MagicMock(side_effect=fake_export)
    monkeypatch.setattr(
        "harvester.batch.restoration.EnhancementExporter",
        lambda: mock_exporter,
    )

    progress_events = []

    def on_progress(current, total, path):
        progress_events.append((current, total, path.name))

    summary = restore_directory(
        root,
        preset_name="extended_air",
        genre_override="House",
        progress_callback=on_progress,
    )

    assert summary.total_scanned == 2
    assert summary.restored_count == 2
    assert summary.failed_count == 0
    assert summary.skipped_count == 0
    assert len(progress_events) == 2

    # Verify Markdown summary output
    table = summary.to_markdown_table()
    assert "# Batch Restoration Summary — album" in table
    assert "01 - Intro.mp3" in table
    assert "02 - Drop.mp3" in table
    assert "House · Extended Air (Hybrid)" in table
