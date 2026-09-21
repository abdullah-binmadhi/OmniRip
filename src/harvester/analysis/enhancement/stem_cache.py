"""Stem cache identity and stage metadata (docs/14 M2).

The stem directory name is ``{input_stem}_{size}`` — two different files can
share both. The manifest records a cheap content fingerprint of the source
(size, mtime and head/tail bytes) plus the engine/mode/preset that produced the
stems, so the workbench can tell a valid cache from a stale or cross-track one
without re-reading whole audio files.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

__all__ = [
    "MANIFEST_NAME",
    "cache_matches",
    "read_cache_manifest",
    "read_stage_meta",
    "source_fingerprint",
    "write_cache_manifest",
    "write_stage_meta",
]

MANIFEST_NAME = "cache_manifest.json"
_FINGERPRINT_BYTES = 65536


def source_fingerprint(path: Path, head_bytes: int = _FINGERPRINT_BYTES) -> str:
    """Cheap, stable identity for one source audio file.

    Size + mtime_ns + head/tail bytes. Two different files that happen to share
    a stem and size will still differ in mtime or bytes; a plain copy of the
    same file keeps its mtime and matches, which is the desired behavior.
    """
    path = Path(path)
    stat = path.stat()
    hasher = hashlib.sha256()
    hasher.update(str(stat.st_size).encode())
    hasher.update(str(stat.st_mtime_ns).encode())
    try:
        with path.open("rb") as fh:
            hasher.update(fh.read(head_bytes))
            fh.seek(max(0, stat.st_size - head_bytes))
            hasher.update(fh.read(head_bytes))
    except OSError:  # pragma: no cover - unreadable source
        pass
    return hasher.hexdigest()[:32]


def manifest_path(stem_dir: Path) -> Path:
    return Path(stem_dir) / MANIFEST_NAME


def _stage_path(stem_dir: Path, name: str) -> Path:
    return Path(stem_dir) / f"{name}.json"


def read_cache_manifest(stem_dir: Path) -> dict[str, Any] | None:
    """The manifest for a stem directory, or None when absent/corrupt (legacy)."""
    path = manifest_path(stem_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_cache_manifest(
    stem_dir: Path,
    source_path: Path,
    *,
    engine: str | None = None,
    mode: str | None = None,
    preset: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record what produced these stems and which source they belong to."""
    stem_dir = Path(stem_dir)
    stem_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "source_path": str(source_path),
        "source_size": source_path.stat().st_size,
        "source_mtime_ns": source_path.stat().st_mtime_ns,
        "source_fingerprint": source_fingerprint(source_path),
    }
    if engine:
        payload["engine"] = engine
    if mode:
        payload["mode"] = mode
    if preset:
        payload["preset"] = preset
    if extra:
        payload.update(extra)
    tmp = manifest_path(stem_dir).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, manifest_path(stem_dir))
    return payload


def cache_matches(stem_dir: Path, source_path: Path) -> bool:
    """Whether a cached stem directory provably belongs to ``source_path``.

    A missing manifest is a pre-manifest cache: accepted as legacy so existing
    users keep their stems. A present-but-mismatched manifest is rejected.
    """
    manifest = read_cache_manifest(stem_dir)
    if manifest is None:
        return True
    stored = manifest.get("source_fingerprint")
    if not stored:
        return True  # identity-free manifest: nothing to contradict
    try:
        if int(manifest.get("source_size", -1)) != source_path.stat().st_size:
            return False
        if int(manifest.get("source_mtime_ns", -1)) != source_path.stat().st_mtime_ns:
            return False
    except OSError:  # pragma: no cover - unreadable source
        return False
    return str(stored) == source_fingerprint(source_path)


def write_stage_meta(stem_dir: Path, name: str, data: dict[str, Any]) -> None:
    """Persist one advisory stage's result (diarization, hosted run) as JSON."""
    stem_dir = Path(stem_dir)
    stem_dir.mkdir(parents=True, exist_ok=True)
    path = _stage_path(stem_dir, name)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def read_stage_meta(stem_dir: Path, name: str) -> dict[str, Any] | None:
    """Read one advisory stage result, or None when absent/corrupt."""
    path = _stage_path(stem_dir, name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
