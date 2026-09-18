"""Opt-in file-level conservative restoration adapter.

The adapter keeps the original input untouched, decodes through FFmpeg, applies the
bounded NumPy restoration module, and writes a portable MP3 derivative. It does not
synthesize a high band and never labels the result lossless.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from harvester.analysis.restoration import RestorationConfig, restore
from harvester.config import AppConfig
from harvester.util.errors import ValidationError


class ConservativeRestorationService:
    """Apply the deterministic restoration chain to a file without mutating it."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def enhance_to_mp3(
        self,
        input_path: Path,
        output_path: Path,
        *,
        job_id: str | None = None,
    ) -> Path:
        if not input_path.is_file() or input_path.stat().st_size == 0:
            raise ValidationError(f"restoration input is missing or empty: {input_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pcm = await self._decode(input_path, job_id=job_id)
        result = await asyncio.to_thread(
            restore,
            pcm,
            48_000.0,
            config=RestorationConfig(),
        )
        await self._encode(result.audio, output_path, job_id=job_id)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise ValidationError("restoration produced an empty MP3")
        return output_path

    async def _decode(self, path: Path, *, job_id: str | None) -> np.ndarray:
        process = await asyncio.create_subprocess_exec(
            self.config.ffmpeg.binary,
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-f",
            "f32le",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.config.timeouts.transcode_s
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise ValidationError(
                f"restoration decode timed out for {job_id or path.name}"
            ) from exc
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(f"restoration decode failed: {detail or 'unknown error'}")
        values = np.frombuffer(stdout, dtype=np.float32).copy()
        if values.size < 4 or values.size % 2:
            raise ValidationError("restoration decode returned invalid stereo PCM")
        return values.reshape((-1, 2))

    async def _encode(self, audio: np.ndarray, path: Path, *, job_id: str | None) -> None:
        process = await asyncio.create_subprocess_exec(
            self.config.ffmpeg.binary,
            "-v",
            "error",
            "-f",
            "f32le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            "-",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            "-y",
            str(path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(
                process.communicate(input=np.asarray(audio, dtype=np.float32).tobytes()),
                timeout=self.config.timeouts.transcode_s,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise ValidationError(
                f"restoration encode timed out for {job_id or path.name}"
            ) from exc
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ValidationError(f"restoration encode failed: {detail or 'unknown error'}")


__all__ = ["ConservativeRestorationService"]
