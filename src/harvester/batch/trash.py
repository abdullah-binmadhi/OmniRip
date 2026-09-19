"""Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).

Layout: ``<scanned root>/.trash/<YYYY-MM-DD>/<HHMMSS>-<name>`` — the day directory
groups rollback sources, and the timestamp prefix keeps same-day renames of the same
filename from colliding. ``.trash/`` lives inside the scanned music directory so the
trash move and the final replace share one filesystem (required for atomic
``os.replace``, docs/02 §3).
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from harvester.util.errors import DiskError

TRASH_DIRNAME = ".trash"


def trash_root_for(scanned_root: Path) -> Path:
    """Return the trash directory for a scanned music directory."""
    return scanned_root / TRASH_DIRNAME


def move_to_trash(original: Path, scanned_root: Path) -> Path:
    """Move ``original`` into today's trash directory; return the trash path.

    Colliding names within the same day get a numeric suffix (``-1``, ``-2``...).
    """
    if not original.is_file():
        raise DiskError(f"cannot trash a missing file: {original}")
    now = datetime.now(UTC)
    day_dir = trash_root_for(scanned_root) / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    candidate = day_dir / f"{now.strftime('%H%M%S')}-{original.name}"
    counter = 1
    while candidate.exists():
        candidate = day_dir / f"{now.strftime('%H%M%S')}-{counter}-{original.name}"
        counter += 1
    shutil.move(str(original), candidate)
    return candidate


def rollback(trash_path: Path, original: Path) -> Path:
    """Restore a trashed original to its original location (FR-13 rollback step)."""
    if not trash_path.is_file():
        raise DiskError(f"cannot roll back a missing trash file: {trash_path}")
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(trash_path), original)
    return original


def purge(root: Path, retention_days: int) -> int:
    """Delete trash day-directories older than ``retention_days``; return count.

    Retention is measured against the day directory name (UTC date), so a directory
    is removed once it is strictly older than ``retention_days`` days. A negative or
    zero retention removes today's directory too (intentional purge).
    """
    trash_root = trash_root_for(root)
    if not trash_root.is_dir():
        return 0
    cutoff = (datetime.now(UTC) - timedelta(days=max(retention_days, 0))).date()
    removed = 0
    for day_dir in sorted(trash_root.iterdir()):
        if not day_dir.is_dir():
            continue
        try:
            day = datetime.strptime(day_dir.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            shutil.rmtree(day_dir)
            removed += 1
    return removed


__all__ = ["TRASH_DIRNAME", "move_to_trash", "purge", "rollback", "trash_root_for"]
