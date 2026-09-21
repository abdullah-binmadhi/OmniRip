"""Tests for the stem cache manifest and stage metadata (docs/14 M2)."""

from __future__ import annotations

from pathlib import Path

from harvester.analysis.enhancement.stem_cache import (
    MANIFEST_NAME,
    cache_matches,
    read_cache_manifest,
    read_stage_meta,
    source_fingerprint,
    write_cache_manifest,
    write_stage_meta,
)


def test_fingerprint_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"A" * 4096)
    first = source_fingerprint(source)
    assert first == source_fingerprint(source)

    source.write_bytes(b"B" * 4096)
    assert source_fingerprint(source) != first


def test_manifest_round_trip_and_match(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"data" * 1024)
    stem_dir = tmp_path / "stems" / "song_4096"
    stem_dir.mkdir(parents=True)

    write_cache_manifest(stem_dir, source, engine="bs_roformer", mode="ensemble")
    manifest = read_cache_manifest(stem_dir)
    assert manifest is not None
    assert manifest["engine"] == "bs_roformer"
    assert manifest["mode"] == "ensemble"
    assert cache_matches(stem_dir, source) is True

    # A different file with the same stem+size would collide by directory name;
    # the manifest fingerprint must reject it.
    other = tmp_path / "other.mp3"
    other.write_bytes(b"different" * 512)
    assert cache_matches(stem_dir, other) is False


def test_missing_manifest_is_legacy_and_accepted(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"data")
    stem_dir = tmp_path / "stems" / "song_4"
    stem_dir.mkdir(parents=True)
    # No manifest: pre-manifest caches must keep working (backward compatible).
    assert read_cache_manifest(stem_dir) is None
    assert cache_matches(stem_dir, source) is True


def test_stage_meta_round_trip(tmp_path: Path) -> None:
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir(parents=True)
    write_stage_meta(
        stem_dir,
        "diarization",
        {"speaker_count": 2, "model": "speaker-diarization-community-1", "device": "cpu"},
    )
    assert read_stage_meta(stem_dir, "diarization") == {
        "speaker_count": 2,
        "model": "speaker-diarization-community-1",
        "device": "cpu",
    }
    assert read_stage_meta(stem_dir, "hosted_run") is None
    assert MANIFEST_NAME == "cache_manifest.json"
