"""Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02, FR-13)."""

from __future__ import annotations

import os
from pathlib import Path


def fsync_file(path: Path) -> None:
    """fsync a file's contents to stable storage."""
    try:
        # On Windows (NT), _commit requires the file descriptor to be opened for writing
        mode = "r+b" if os.name == "nt" else "rb"
        with path.open(mode) as handle:
            os.fsync(handle.fileno())
    except OSError:
        pass


def fsync_directory(path: Path) -> None:
    """fsync a directory fd so renames inside it survive a crash (POSIX only)."""
    if os.name != "posix":
        return
    flags = getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, os.O_RDONLY | flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_replace(source: Path, destination: Path) -> None:
    """Atomically move ``source`` onto ``destination`` and persist the rename."""
    os.replace(source, destination)
    fsync_directory(destination.parent)


__all__ = ["atomic_replace", "fsync_directory", "fsync_file"]
