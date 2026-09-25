"""Batch Library Auto-Restoration and Curation Engine (M21).

Provides serial batch restoration of lossy/substandard audio files within a directory tree.
Applies spectral analysis, genre intent profiling, and enhancement rendering, followed by
atomic file replacement with rollback guarantees.

Memory constraint (Apple Silicon M2 / 16GB RAM):
Executes tracks strictly serially and purges neural VRAM and PyTorch caches after each track
to prevent swap thrashing and out-of-memory kernel panics.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mutagen import File as MutagenFile

from harvester.analysis.enhancement.eq import MasteringEQSettings
from harvester.analysis.enhancement.genres import (
    DEFAULT_GENRE_INTENSITY,
    GenreChoice,
    choices_from_tags,
    compose_master_settings,
    effective_preset,
    resolve_genre_names,
)
from harvester.analysis.enhancement.presets import PRESETS
from harvester.batch.scanner import AUDIO_EXTENSIONS
from harvester.batch.trash import move_to_trash, rollback
from harvester.config import AppConfig
from harvester.services.enhancement.exporter import EnhancementExporter
from harvester.util.errors import DiskError
from harvester.util.fsatomic import fsync_directory
from harvester.util.memory import purge_neural_vram

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BatchRestoreTrackResult:
    """Summary record for a single processed track in a batch restoration run."""

    input_path: Path
    status: str  # "restored", "skipped", "failed", "dry_run"
    original_codec: str | None = None
    original_bitrate_kbps: int | None = None
    spectral_verdict: str | None = None
    cutoff_hz: float | None = None
    genre_label: str = "Neutral"
    applied_preset: str = "conservative"
    output_path: Path | None = None
    trash_path: Path | None = None
    error: str | None = None


@dataclass(slots=True)
class BatchRestoreSummary:
    """Aggregated report of a batch library restoration run."""

    root: Path
    results: list[BatchRestoreTrackResult] = field(default_factory=list)

    @property
    def total_scanned(self) -> int:
        return len(self.results)

    @property
    def restored_count(self) -> int:
        return sum(1 for r in self.results if r.status in ("restored", "dry_run"))

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def to_markdown_table(self) -> str:
        """Format the restoration summary into a clean GitHub-flavored markdown table."""
        lines = [
            f"# Batch Restoration Summary — {self.root.name}",
            "",
            f"> Processed {self.total_scanned} track(s): {self.restored_count} restored, "
            f"{self.skipped_count} skipped, {self.failed_count} failed.",
            "",
            "| # | Track | Status | Format / Bitrate | Spectral Cutoff | Genre / Profile | Output |",
            "|---|-------|--------|------------------|-----------------|-----------------|--------|",
        ]
        for idx, res in enumerate(self.results, start=1):
            name = res.input_path.name
            bitrate_str = (
                f"{res.original_bitrate_kbps} kbps" if res.original_bitrate_kbps else "unknown"
            )
            fmt_str = f"{res.original_codec or 'audio'} ({bitrate_str})"
            cutoff_str = (
                f"{res.cutoff_hz:.0f} Hz"
                if res.cutoff_hz
                else (res.spectral_verdict or "—")
            )
            genre_str = f"{res.genre_label} · {res.applied_preset}"
            out_str = (
                f"`{res.output_path.name}`"
                if res.output_path
                else ("(dry run)" if res.status == "dry_run" else "—")
            )
            lines.append(
                f"| {idx} | {name} | {res.status} | {fmt_str} | {cutoff_str} | {genre_str} | {out_str} |"
            )
        return "\n".join(lines)


def safe_swap(temporary_path: Path, target: Path, scanned_root: Path) -> Path:
    """Atomically swap the enhanced derivative into place with .trash/ backup and rollback.

    Moves the original file into scanned_root/.trash/<date>/<time>-<name>,
    then atomically renames the temporary enhanced file into the target location.
    If the atomic rename fails, the original file is rolled back from .trash/.
    """
    if not target.is_file():
        raise DiskError(f"cannot swap missing target file: {target}")
    if not temporary_path.is_file():
        raise DiskError(f"cannot swap missing temporary file: {temporary_path}")

    trash_path = move_to_trash(target, scanned_root)
    try:
        os.replace(temporary_path, target)
        fsync_directory(target.parent)
    except OSError as exc:
        rollback(trash_path, target)
        raise DiskError(
            f"batch swap failed after trashing; original restored from .trash/: {exc}"
        ) from exc
    return trash_path


def should_restore_entry(
    path: Path,
    *,
    skip_bitrate_kbps: int = 256,
) -> tuple[bool, str, int | None]:
    """Inspect whether a file qualifies for audio enhancement/restoration.

    Returns (needs_restore, codec_name, bitrate_kbps).
    """
    ext = path.suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return False, "non-audio", None

    try:
        audio = MutagenFile(path)
    except Exception:
        return False, "unreadable", None

    if audio is None:
        return False, "unknown", None

    codec = ext.lstrip(".")
    bitrate_kbps = None

    info = getattr(audio, "info", None)
    if info is not None:
        raw_bitrate = getattr(info, "bitrate", None)
        if raw_bitrate:
            bitrate_kbps = int(raw_bitrate) // 1000

    # Lossless formats: flac, alac, wav, aiff (unless explicitly forced)
    if ext in {".flac", ".wav", ".aif", ".aiff", ".wv", ".ape"}:
        return False, codec, bitrate_kbps

    if bitrate_kbps and bitrate_kbps >= skip_bitrate_kbps:
        return False, codec, bitrate_kbps

    return True, codec, bitrate_kbps


def restore_file(
    path: Path,
    scanned_root: Path,
    *,
    config: AppConfig | None = None,
    preset_name: str = "conservative",
    genre_override: str | None = None,
    genre_intensity: str = DEFAULT_GENRE_INTENSITY,
    format: str = "mp3",
    dry_run: bool = False,
    exporter: EnhancementExporter | None = None,
) -> BatchRestoreTrackResult:
    """Restore a single audio file with genre-aware mastering and atomic swap.

    Strictly manages memory by guaranteeing purge_neural_vram() in finally block.
    """
    path = Path(path)
    if not path.is_file():
        return BatchRestoreTrackResult(
            input_path=path,
            status="failed",
            error=f"File not found: {path}",
        )

    skip_kbps = config.batch.skip_bitrate_kbps if config else 256
    needs_restore, codec, bitrate_kbps = should_restore_entry(path, skip_bitrate_kbps=skip_kbps)
    if not needs_restore:
        return BatchRestoreTrackResult(
            input_path=path,
            status="skipped",
            original_codec=codec,
            original_bitrate_kbps=bitrate_kbps,
        )

    # Read tags for genre detection
    genre_choice = GenreChoice()
    if genre_override:
        genre_choice = resolve_genre_names([genre_override], source="cli_override")
    else:
        try:
            m = MutagenFile(path)
            if m and getattr(m, "tags", None):
                genre_choice = choices_from_tags(m.tags)
        except Exception as exc:
            logger.debug("Failed reading tags for genre detection on %s: %s", path, exc)

    base_preset = PRESETS.get(preset_name, PRESETS["conservative"])
    eff_preset = effective_preset(base_preset, genre_choice)
    eq_settings = compose_master_settings(
        MasteringEQSettings(), genre_choice, intensity=genre_intensity
    )
    genre_label = genre_choice.label() if genre_choice.detected else "Neutral"

    if dry_run:
        return BatchRestoreTrackResult(
            input_path=path,
            status="dry_run",
            original_codec=codec,
            original_bitrate_kbps=bitrate_kbps,
            genre_label=genre_label,
            applied_preset=eff_preset.name,
            output_path=path,
        )

    if exporter is None:
        exporter = EnhancementExporter()

    # Create temporary file in same folder for atomic os.replace
    tmp_out = path.parent / f".{path.stem}.harvester.tmp.{format}"
    try:
        # Run restoration export
        if format.lower() in ("flac", "wav"):
            exported = exporter.export_enhanced_lossless(
                input_path=path,
                preset=eff_preset,
                output_path=tmp_out,
                format=format.lower(),
                eq_settings=eq_settings,
            )
        else:
            exported = exporter.export_enhanced_derivative(
                input_path=path,
                preset=eff_preset,
                output_path=tmp_out,
                eq_settings=eq_settings,
                bitrate="320k",
            )

        trash_path = safe_swap(exported, path, scanned_root)
        return BatchRestoreTrackResult(
            input_path=path,
            status="restored",
            original_codec=codec,
            original_bitrate_kbps=bitrate_kbps,
            genre_label=genre_label,
            applied_preset=eff_preset.name,
            output_path=path,
            trash_path=trash_path,
        )
    except Exception as exc:
        if tmp_out.exists():
            try:
                tmp_out.unlink()
            except OSError:
                pass
        logger.error("Failed restoring %s: %s", path, exc, exc_info=True)
        return BatchRestoreTrackResult(
            input_path=path,
            status="failed",
            original_codec=codec,
            original_bitrate_kbps=bitrate_kbps,
            genre_label=genre_label,
            applied_preset=eff_preset.name,
            error=str(exc),
        )
    finally:
        # Essential for Apple Silicon M2 16GB memory protection
        purge_neural_vram()


def restore_directory(
    root: Path,
    *,
    config: AppConfig | None = None,
    preset_name: str = "conservative",
    genre_override: str | None = None,
    genre_intensity: str = DEFAULT_GENRE_INTENSITY,
    format: str = "mp3",
    dry_run: bool = False,
    progress_callback: Callable[[int, int, Path], None] | None = None,
) -> BatchRestoreSummary:
    """Iterate serially over a directory, restoring lossy tracks with M2 RAM safety."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")

    # Gather audio candidate files, excluding .trash and hidden dirs
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".") and d.upper() not in (".TRASH", "QUARANTINE")
        ]
        for fn in filenames:
            if fn.startswith("."):
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() in AUDIO_EXTENSIONS:
                candidates.append(p)

    candidates.sort()
    exporter = None if dry_run else EnhancementExporter()
    summary = BatchRestoreSummary(root=root)

    for idx, candidate in enumerate(candidates, start=1):
        if progress_callback:
            progress_callback(idx, len(candidates), candidate)

        res = restore_file(
            candidate,
            scanned_root=root,
            config=config,
            preset_name=preset_name,
            genre_override=genre_override,
            genre_intensity=genre_intensity,
            format=format,
            dry_run=dry_run,
            exporter=exporter,
        )
        summary.results.append(res)
        # Extra explicit purge between serial tracks
        purge_neural_vram()

    return summary


__all__ = [
    "BatchRestoreSummary",
    "BatchRestoreTrackResult",
    "restore_directory",
    "restore_file",
    "safe_swap",
    "should_restore_entry",
]
