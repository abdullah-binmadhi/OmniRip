"""Polishing: FLAC keep-and-tag for P2P, transcode+tag for streams, batch atomic swap."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path

from harvester.config import AppConfig
from harvester.models import CanonicalMetadata, SourceKind, TrackJob
from harvester.services.ffmpeg import FfmpegService
from harvester.services.restoration import ConservativeRestorationService
from harvester.services.tagging import MetadataTagger, metadata_from_probe
from harvester.util.errors import ConfigError, DiskError, ValidationError
from harvester.util.fsatomic import atomic_replace, fsync_directory, fsync_file

_INVALID_FILENAME = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


async def polish_stream(
    job: TrackJob,
    config: AppConfig,
    ffmpeg: FfmpegService,
    tagger: MetadataTagger,
    *,
    cover_bytes: bytes | None = None,
) -> Path:
    """Tag and atomically place a file; P2P FLAC keeps its lossless container."""

    if not job.workspace_path or not job.workspace_path.is_file():
        raise ValidationError("workspace file is missing")

    metadata = job.canonical_meta or metadata_from_probe(job.probe_meta)
    output_dir = config.general.output_dir.expanduser()
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

    if job.source_kind is SourceKind.P2P_FLAC:
        return await _polish_flac(job, config, tagger, metadata, output_dir, cover_bytes)

    if config.ffmpeg.transcode == "keep-opus":
        raise ConfigError("keep-opus output is reserved for a later stream-tagging milestone")
    if not (config.ffmpeg.transcode.startswith("mp3-") or config.ffmpeg.transcode == "mp3-v0"):
        raise ConfigError(f"unsupported transcode mode: {config.ffmpeg.transcode}")
    return await _polish_mp3(job, config, ffmpeg, tagger, metadata, output_dir, cover_bytes)


async def polish_batch(
    job: TrackJob,
    config: AppConfig,
    ffmpeg: FfmpegService,
    tagger: MetadataTagger,
    *,
    cover_bytes: bytes | None = None,
) -> Path:
    """Mode B atomic swap into the original location (docs/03 §5.3, FR-13).

    Ordered, failure-safe steps: temp written+tagged in the original directory,
    fsync, mutagen/duration verify, original moved to ``.trash/<date>/``, temp
    ``os.replace``d onto the original path, directory fsynced. Any failure after the
    trash move rolls the original back from ``.trash/`` (byte-identical, AC-5).
    """

    if not job.input_path or not job.input_path.is_file():
        raise ValidationError("Mode B job has no original file to replace")
    if not job.workspace_path or not job.workspace_path.is_file():
        raise ValidationError("workspace file is missing")
    original = job.input_path
    workspace = job.workspace_path

    metadata = job.canonical_meta or metadata_from_probe(job.probe_meta)
    original_dir = original.parent
    extension = ".flac" if job.source_kind is SourceKind.P2P_FLAC else ".mp3"
    target = _batch_target_path(job, config, metadata, original_dir, extension)
    temporary_path = original_dir / f".{original.stem}.{job.id}.harvester.tmp{extension}"
    await _write_and_tag(
        workspace, job, config, ffmpeg, tagger, metadata, temporary_path, cover_bytes
    )
    await asyncio.to_thread(fsync_file, temporary_path)
    await _verify_temporary(job, ffmpeg, temporary_path)

    # The swap itself is sequential and thread-safe; keep it in one thread so the
    # trash-move → replace window is as small as possible.
    try:
        trash_path = await asyncio.to_thread(
            _swap_into_place, job, temporary_path, target, original_dir
        )
    except Exception:
        await asyncio.to_thread(temporary_path.unlink, True)
        raise
    job.output_path = target
    job.trash_path = trash_path
    return target


async def _write_and_tag(
    workspace: Path,
    job: TrackJob,
    config: AppConfig,
    ffmpeg: FfmpegService,
    tagger: MetadataTagger,
    metadata: CanonicalMetadata,
    temporary_path: Path,
    cover_bytes: bytes | None,
) -> None:
    if job.source_kind is SourceKind.P2P_FLAC:
        await asyncio.to_thread(shutil.copy2, workspace, temporary_path)
        await tagger.tag_flac_async(temporary_path, metadata, cover_bytes=cover_bytes)
        return
    if config.ffmpeg.transcode == "keep-opus":
        raise ConfigError("keep-opus output is reserved for a later stream-tagging milestone")
    if not (config.ffmpeg.transcode.startswith("mp3-") or config.ffmpeg.transcode == "mp3-v0"):
        raise ConfigError(f"unsupported transcode mode: {config.ffmpeg.transcode}")
    await ffmpeg.transcode_to_mp3(workspace, temporary_path, job_id=job.id)
    await tagger.tag_mp3_async(
        temporary_path,
        metadata,
        cover_bytes=cover_bytes,
        source_origin="youtube_opus_transcoded_mp3",
    )


async def _verify_temporary(job: TrackJob, ffmpeg: FfmpegService, path: Path) -> None:
    """Guard against swapping in a wrong/short file (docs/03 §5.3 step 2)."""

    try:
        parsed = await asyncio.to_thread(_mutagen_parses, path)
    except Exception as exc:
        raise ValidationError(f"replacement failed mutagen verification: {exc}") from exc
    if not parsed:
        raise ValidationError("replacement is not a parseable audio file")
    if job.orig_duration_s and job.orig_duration_s > 0:
        measured = await ffmpeg.probe_duration(path, job_id=job.id)
        if abs(measured - job.orig_duration_s) / job.orig_duration_s > 0.05:
            raise ValidationError(
                f"replacement duration mismatch: original {job.orig_duration_s:.1f}s, "
                f"new {measured:.1f}s"
            )


def _mutagen_parses(path: Path) -> bool:
    from mutagen import File as MutagenFile

    try:
        return MutagenFile(path) is not None
    except Exception:
        return False


def _swap_into_place(job: TrackJob, temporary_path: Path, target: Path, original_dir: Path) -> Path:
    from harvester.batch.trash import move_to_trash, rollback

    assert job.input_path is not None
    scanned_root = job.batch_root or original_dir
    trash_path = move_to_trash(job.input_path, scanned_root)
    try:
        os.replace(temporary_path, target)
        fsync_directory(original_dir)
    except OSError as exc:
        rollback(trash_path, job.input_path)
        raise DiskError(
            f"batch swap failed after trashing; original restored from .trash/: {exc}"
        ) from exc
    return trash_path


def _batch_target_path(
    job: TrackJob,
    config: AppConfig,
    metadata: CanonicalMetadata,
    original_dir: Path,
    extension: str,
) -> Path:
    input_path = job.input_path
    if input_path is None:
        raise ValidationError("Mode B job has no original file")
    if not config.batch.rename_to_canonical:
        return input_path
    artist = metadata.artist or "Unknown Artist"
    title = metadata.title or input_path.stem
    base = f"{_safe_component(artist)} - {_safe_component(title)}"
    candidate = original_dir / f"{base}{extension}"
    counter = 2
    while candidate.exists():
        candidate = original_dir / f"{base} ({counter}){extension}"
        counter += 1
    return candidate


async def _polish_flac(
    job: TrackJob,
    config: AppConfig,
    tagger: MetadataTagger,
    metadata: CanonicalMetadata,
    output_dir: Path,
    cover_bytes: bytes | None,
) -> Path:
    final_path = await asyncio.to_thread(_choose_output_path, output_dir, metadata, job.id, ".flac")
    temporary_path = output_dir / f".{final_path.stem}.{job.id}.tmp.flac"
    workspace = job.workspace_path
    if workspace is None or not workspace.is_file():
        raise ValidationError("workspace file is missing")
    try:
        await asyncio.to_thread(shutil.copy2, workspace, temporary_path)
        await tagger.tag_flac_async(temporary_path, metadata, cover_bytes=cover_bytes)
        await asyncio.to_thread(fsync_file, temporary_path)
        await asyncio.to_thread(atomic_replace, temporary_path, final_path)
    except OSError as exc:
        if temporary_path.exists():
            await asyncio.to_thread(temporary_path.unlink, True)
        raise DiskError(f"could not atomically place {final_path.name}: {exc}") from exc
    except Exception:
        if temporary_path.exists():
            await asyncio.to_thread(temporary_path.unlink, True)
        raise
    job.output_path = final_path
    return final_path


async def _polish_mp3(
    job: TrackJob,
    config: AppConfig,
    ffmpeg: FfmpegService,
    tagger: MetadataTagger,
    metadata: CanonicalMetadata,
    output_dir: Path,
    cover_bytes: bytes | None,
) -> Path:
    final_path = await asyncio.to_thread(_choose_output_path, output_dir, metadata, job.id, ".mp3")
    temporary_path = output_dir / f".{final_path.stem}.{job.id}.tmp.mp3"
    workspace = job.workspace_path
    if workspace is None or not workspace.is_file():
        raise ValidationError("workspace file is missing")
    try:
        source_origin = "youtube_opus_transcoded_mp3"
        if config.restoration.enabled:
            await ConservativeRestorationService(config).enhance_to_mp3(
                workspace,
                temporary_path,
                job_id=job.id,
            )
            source_origin = "lossy_conservative_restoration_mp3"
        else:
            await ffmpeg.transcode_to_mp3(workspace, temporary_path, job_id=job.id)
        await tagger.tag_mp3_async(
            temporary_path,
            metadata,
            cover_bytes=cover_bytes,
            source_origin=source_origin,
            provenance_comment=(
                "Derived from lossy input; conservative bounded DSP applied"
                if config.restoration.enabled
                else "Downloaded via yt-dlp and transcoded to MP3"
            ),
        )
        await asyncio.to_thread(fsync_file, temporary_path)
        await asyncio.to_thread(atomic_replace, temporary_path, final_path)
    except OSError as exc:
        if temporary_path.exists():
            await asyncio.to_thread(temporary_path.unlink, True)
        raise DiskError(f"could not atomically place {final_path.name}: {exc}") from exc
    except Exception:
        if temporary_path.exists():
            await asyncio.to_thread(temporary_path.unlink, True)
        raise
    job.output_path = final_path
    return final_path


def _choose_output_path(
    output_dir: Path,
    metadata: CanonicalMetadata,
    job_id: str,
    extension: str = ".mp3",
) -> Path:
    artist = metadata.artist or "Unknown Artist"
    title = metadata.title or job_id
    base = f"{_safe_component(artist)} - {_safe_component(title)}"
    candidate = output_dir / f"{base}{extension}"
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"{base} ({counter}){extension}"
        counter += 1
    return candidate


def _safe_component(value: str) -> str:
    cleaned = _INVALID_FILENAME.sub("_", value).strip().strip(".")
    if not cleaned:
        return "untitled"
    if cleaned.upper() in _RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned[:180]


__all__ = ["polish_batch", "polish_stream"]
