"""Mode B scanner tests: skip matrix, exclusions, filename parsing (docs/09 §7.1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from harvester.batch.scanner import (
    _HARVESTER_TMP_PATTERN,
    parse_filename,
    purge_stale_temps,
    scan_directory,
)
from harvester.config import load_config
from harvester.models import SkipReason


def write_mp3(path: Path, bitrate_bps: int, n_frames: int = 4) -> Path:
    """Craft a minimal valid MPEG-1 Layer III file by bitrate (mutagen-parseable).

    Header: 0xFF 0xFB = MPEG-1 Layer III, no CRC; bitrate indexes per the MPEG-1
    Layer III table (128k→9, 192k→11, 256k→13). Four frames satisfy mutagen's
    minimum-frame scan (fewer parse as truncated).
    """

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


def write_wav(path: Path) -> Path:
    sf.write(path, np.zeros(4410, dtype=np.float32), 44_100, format="WAV")
    return path


def write_ogg(path: Path) -> Path:
    sf.write(path, np.zeros(4410, dtype=np.float32), 44_100, format="OGG")
    return path


def _config(tmp_path: Path, skip_kbps: int = 256):
    return load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={
            "general.output_dir": str(tmp_path / "output"),
            "batch.skip_bitrate_kbps": skip_kbps,
        },
    )


def test_skip_matrix_mixed_directory(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    write_flac(root / "a.flac")
    write_wav(root / "b.wav")
    write_mp3(root / "c-high.mp3", 256_000)
    write_mp3(root / "d-low.mp3", 128_000)
    (root / "e-broken.mp3").write_bytes(b"\x00" * 512)

    scan = scan_directory(root, _config(tmp_path))

    by_name = {entry.path.name: entry for entry in scan.entries}
    assert set(by_name) == {"a.flac", "b.wav", "c-high.mp3", "d-low.mp3", "e-broken.mp3"}
    assert by_name["a.flac"].reason is SkipReason.LOSSLESS
    assert by_name["b.wav"].reason is SkipReason.LOSSLESS
    assert by_name["c-high.mp3"].reason is SkipReason.BITRATE
    assert by_name["c-high.mp3"].bitrate_kbps == 256
    assert by_name["d-low.mp3"].reason is None  # queued
    assert by_name["d-low.mp3"].bitrate_kbps == 128
    assert by_name["e-broken.mp3"].reason is SkipReason.UNREADABLE
    assert scan.found == 5
    assert len(scan.queued) == 1
    assert len(scan.skipped) == 4


def test_scan_respects_custom_threshold(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    write_mp3(root / "mid.mp3", 192_000)

    scan = scan_directory(root, _config(tmp_path, skip_kbps=192))

    assert scan.entries[0].reason is SkipReason.BITRATE  # >= threshold (D1: single threshold)


def test_scan_excludes_trash_hidden_and_quarantine(tmp_path: Path) -> None:
    root = tmp_path / "library"
    (root / ".trash").mkdir(parents=True)
    (root / ".hidden").mkdir()
    (root / "quarantine").mkdir()
    write_flac(root / ".trash" / "old.flac")
    write_flac(root / ".hidden" / "secret.flac")
    write_flac(root / "quarantine" / "bad.flac")
    write_mp3(root / "queued.mp3", 128_000)

    scan = scan_directory(root, _config(tmp_path))

    assert [entry.path.name for entry in scan.entries] == ["queued.mp3"]


def test_scan_ignores_and_purges_stale_temps(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    stale = root / "song.abc123.harvester.tmp.flac"
    stale.write_bytes(b"partial")
    write_mp3(root / "queued.mp3", 128_000)

    assert _HARVESTER_TMP_PATTERN.search(stale.name)
    scan = scan_directory(root, _config(tmp_path))

    assert not stale.exists()  # purged by the scan (AC-6)
    assert [entry.path.name for entry in scan.entries] == ["queued.mp3"]


def test_purge_stale_temps_targets_only_harvester_temps(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    stale = root / "a.abc.harvester.tmp.mp3"
    innocent = root / "artist - track (1).mp3"
    stale.write_bytes(b"x")
    write_mp3(innocent, 128_000)

    purge_stale_temps(root)

    assert not stale.exists()
    assert innocent.exists()


def test_scan_mp4_branches(monkeypatch, tmp_path: Path) -> None:
    """MP4 codec branches (ALAC skip, AAC queue) via fake MP4 objects.

    Real AAC fixtures need an encoder that is not guaranteed on this machine;
    the scanner's MP4 branch is exercised with MP4-subclass fakes.
    """

    from types import SimpleNamespace

    from mutagen.mp4 import MP4

    import harvester.batch.scanner as scanner

    root = tmp_path / "library"
    root.mkdir()
    (root / "lossless.m4a").write_bytes(b"x")
    (root / "lossy.m4a").write_bytes(b"x")

    fakes: dict[str, object] = {}

    def fake_open(path):
        fake = object.__new__(MP4)
        if path.name == "lossless.m4a":
            fake.info = SimpleNamespace(codec="alac", bitrate=None, length=None)
        else:
            fake.info = SimpleNamespace(codec="mp4a", bitrate=128_000, length=1.0)
        fake.tags = None
        fakes[path.name] = fake
        return fake

    monkeypatch.setattr(scanner, "MutagenFile", fake_open)

    scan = scan_directory(root, _config(tmp_path))

    by_name = {entry.path.name: entry for entry in scan.entries}
    assert by_name["lossless.m4a"].reason is SkipReason.LOSSLESS
    assert by_name["lossless.m4a"].codec == "alac"
    assert by_name["lossy.m4a"].reason is None  # queued
    assert by_name["lossy.m4a"].codec == "m4a/aac"
    assert by_name["lossy.m4a"].bitrate_kbps == 128


def test_scan_ogg_vorbis_never_crashes(tmp_path: Path) -> None:
    try:
        write_ogg(tmp_path / "library" / "v.ogg")
    except Exception as exc:  # pragma: no cover - libsndfile build may lack OGG
        pytest.skip(f"libsndfile cannot write OGG here: {exc}")
    root = tmp_path / "library"

    scan = scan_directory(root, _config(tmp_path))

    assert len(scan.entries) == 1
    assert scan.entries[0].codec.startswith(("ogg", "vorbis"))


def test_scan_non_audio_and_non_directory(tmp_path: Path) -> None:
    root = tmp_path / "library"
    root.mkdir()
    (root / "notes.txt").write_text("not audio")

    scan = scan_directory(root, _config(tmp_path))

    assert scan.entries == ()

    with pytest.raises(FileNotFoundError):
        scan_directory(tmp_path / "missing", _config(tmp_path))


def test_parse_filename_ordered_patterns() -> None:
    assert parse_filename("03 - Artist - Title") == ("Artist", "Title")
    assert parse_filename("Artist - Title") == ("Artist", "Title")
    assert parse_filename("03. Title") == (None, "Title")
    assert parse_filename("Title (1)") == (None, "Title")
    assert parse_filename("my_underscored_song") == (None, "my underscored song")
    assert parse_filename("PlainTitle") == (None, "PlainTitle")