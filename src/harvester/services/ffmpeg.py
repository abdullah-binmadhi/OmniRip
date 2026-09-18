"""Async FFmpeg/ffprobe adapter used by fallback acquisition."""

from __future__ import annotations

import asyncio
import shlex
import shutil
from pathlib import Path

import numpy as np

from harvester.config import AppConfig
from harvester.models import SourceKind
from harvester.util.errors import ConfigError, TransientNetwork, ValidationError
from harvester.util.subproc import SubprocessRegistry, subprocess_options


class FfmpegService:
    """Run FFmpeg tools in killable subprocesses with explicit deadlines."""

    def __init__(self, config: AppConfig, registry: SubprocessRegistry | None = None) -> None:
        self.config = config
        self.registry = registry or SubprocessRegistry()

    async def _resolve(self, setting: str) -> list[str]:
        try:
            parts = shlex.split(setting)
        except ValueError as exc:
            raise ConfigError(f"invalid FFmpeg command {setting!r}: {exc}") from exc
        if not parts:
            raise ConfigError("FFmpeg command cannot be empty")
        executable = await asyncio.to_thread(shutil.which, parts[0])
        if not executable:
            raise ConfigError(f"required executable {parts[0]!r} was not found on PATH")
        return [executable, *parts[1:]]

    async def _run(
        self,
        command: list[str],
        *,
        job_id: str | None,
        timeout_s: float,
    ) -> tuple[int, bytes, bytes]:
        key = f"{job_id or 'probe'}:ffmpeg:{id(command)}"
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_options(),
            )
        except OSError as exc:
            raise ConfigError(f"could not start {command[0]!r}: {exc}") from exc
        await self.registry.register(key, process)
        try:
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
            except TimeoutError as exc:
                await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
                raise TransientNetwork(
                    f"FFmpeg command timed out after {timeout_s:g}s",
                    user_hint="The media tool may be stalled or the input may be corrupt.",
                ) from exc
        finally:
            await self.registry.unregister(key)
        return process.returncode or 0, stdout or b"", stderr or b""

    @staticmethod
    def build_transcode_args(
        input_path: Path,
        output_path: Path,
        *,
        mode: str,
    ) -> list[str]:
        """Build the deterministic Phase 5 transcode arguments."""

        args = [
            "-v",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-map",
            "0:a:0",
            "-c:a",
            "libmp3lame",
        ]
        if mode.startswith("mp3-") and mode[4:].isdigit():
            args.extend(["-b:a", f"{mode[4:]}k"])
        elif mode == "mp3-v0":
            args.extend(["-q:a", "0"])
        else:
            raise ConfigError(f"transcoding mode {mode!r} is not an MP3 mode")
        args.append(str(output_path))
        return args

    async def probe_duration(self, path: Path, *, job_id: str | None = None) -> float:
        binary = await self._resolve(self.config.ffmpeg.probe_binary)
        command = [
            *binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        returncode, stdout, stderr = await self._run(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.ffprobe_s,
        )
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(f"ffprobe could not read {path.name}: {detail}")
        try:
            duration = float(stdout.decode("utf-8", errors="replace").strip())
        except ValueError as exc:
            raise ValidationError(f"ffprobe returned an invalid duration for {path.name}") from exc
        if duration <= 0:
            raise ValidationError(f"ffprobe returned a non-positive duration for {path.name}")
        return duration

    async def probe_codec(self, path: Path, *, job_id: str | None = None) -> str:
        binary = await self._resolve(self.config.ffmpeg.probe_binary)
        command = [
            *binary,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        returncode, stdout, stderr = await self._run(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.ffprobe_s,
        )
        if returncode != 0:

            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(f"ffprobe could not identify {path.name}: {detail}")
        codec = stdout.decode("utf-8", errors="replace").strip().lower()
        if not codec:
            raise ValidationError(f"ffprobe found no audio stream in {path.name}")
        return codec

    async def decode_f32(
        self,
        path: Path,
        *,
        offset_s: float = 0.0,
        duration_s: float | None = None,
        sample_rate: int = 48_000,
        job_id: str | None = None,
    ) -> np.ndarray:
        """Decode a mono excerpt to float32 PCM without blocking the loop."""

        binary = await self._resolve(self.config.ffmpeg.binary)
        command = [
            *binary,
            "-v",
            "error",
            "-ss",
            f"{offset_s:.3f}",
        ]
        if duration_s is not None:
            command.extend(["-t", f"{duration_s:.3f}"])
        command.extend(
            [
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "f32le",
                "-",
            ]
        )
        key = f"{job_id or 'probe'}:ffmpeg-decode:{id(command)}"
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_options(),
            )
        except OSError as exc:
            raise ConfigError(f"could not start {command[0]!r}: {exc}") from exc
        await self.registry.register(key, process)
        try:
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.config.timeouts.spectral_s
                )
            except TimeoutError as exc:
                await self.registry.terminate(key, grace_s=self.config.timeouts.kill_grace_s)
                raise ValidationError("FFmpeg decode timed out") from exc
        finally:
            await self.registry.unregister(key)
        if process.returncode != 0:
            detail = (stderr or b"").decode("utf-8", errors="replace").strip()
            raise ValidationError(f"FFmpeg decode failed: {detail or 'unknown error'}")
        pcm = np.frombuffer(stdout, dtype=np.float32).copy()
        if pcm.size < 2:
            raise ValidationError("FFmpeg decode produced no samples")
        return pcm

    async def probe_sample_rate(
        self, path: Path, *, job_id: str | None = None
    ) -> int | None:
        binary = await self._resolve(self.config.ffmpeg.probe_binary)
        command = [
            *binary,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        returncode, stdout, stderr = await self._run(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.ffprobe_s,
        )
        if returncode != 0:
            return None
        text = stdout.decode("utf-8", errors="replace").strip()
        try:
            return int(text)
        except ValueError:
            return None

    async def source_kind(self, path: Path, *, job_id: str | None = None) -> SourceKind:
        codec = await self.probe_codec(path, job_id=job_id)
        if codec == "opus" or path.suffix.lower() in {".opus", ".webm"}:
            return SourceKind.STREAM_OPUS
        return SourceKind.STREAM_OTHER

    async def transcode_to_mp3(
        self,
        input_path: Path,
        output_path: Path,
        *,
        job_id: str | None = None,
    ) -> Path:
        mode = self.config.ffmpeg.transcode
        output_path.parent.mkdir(parents=True, exist_ok=True)
        binary = await self._resolve(self.config.ffmpeg.binary)
        command = [
            *binary,
            *self.build_transcode_args(input_path, output_path, mode=mode),
        ]
        returncode, _stdout, stderr = await self._run(
            command,
            job_id=job_id,
            timeout_s=self.config.timeouts.transcode_s,
        )
        if returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(f"FFmpeg MP3 transcode failed: {detail or 'empty output'}")
        return output_path


__all__ = ["FfmpegService"]
