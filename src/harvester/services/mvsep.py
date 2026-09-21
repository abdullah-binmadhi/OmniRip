"""
MVSEP hosted separation — the opt-in cloud engine (docs/13 D26).

This is the **only** part of OmniRip that sends audio off the machine, so it is
deliberately not a preset: nothing here runs unless the user presses
``☁ HOSTED SEPARATE`` for a specific track. Every lane it produces is marked
with the ``hosted`` origin in the lane plan, so a hosted row can never be
mistaken for a local model output.

Verified API behaviour (docs/13 §8, live-tested end to end):

- ``POST /api/separation/create`` (multipart, ``api_token`` + ``audiofile``)
  returns ``{"success": true, "data": {"hash": …}}``.
- ``GET /api/separation/get?hash=…`` returns ``{"success": true, "status":
  "waiting"|"processing"|"done"|"error", "data": {…}}`` — the status is at the
  **top level** and the stem list only appears in ``data.files`` once done.
- ``sep_type`` is the ``render_id`` field of ``GET /api/app/algorithms``, *not*
  its ``id`` field (the two differ by one or two).
- HTTP 400 means an invalid key. The token is never logged, echoed in an
  exception message or written to disk by this module.

The client is async (``httpx.AsyncClient``) so the workbench worker can poll
without blocking the UI thread; audio is only read from disk at upload time.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from harvester.processing import DEFAULT_SEP_TYPE, HOSTED_RAW_TOKEN

__all__ = [
    "API_BASE",
    "DEFAULT_SEP_TYPE",
    "HOSTED_RAW_TOKEN",
    "MVSEP_KEY_VAR",
    "SEP_TYPES",
    "STEM_LANE_KEYS",
    "HostedResult",
    "HostedStem",
    "MvsepClient",
    "lane_key_for_token",
]

logger = logging.getLogger(__name__)

API_BASE = "https://mvsep.com/api"
MVSEP_KEY_VAR = "MVSEP_API_KEY"

# Friendly name → MVSEP ``sep_type`` (the ``render_id`` from /api/app/algorithms,
# verified live: 49 = MVSep Karaoke, 126 = Mega 53-stem, 20 = Demucs4 HT,
# 63 = BS Roformer SW, 32 = Ensemble All-In).
SEP_TYPES: dict[str, int] = {
    "karaoke_lead_back": 49,
    "mega_53_stem": 126,
    "bs_roformer_sw": 63,
    "demucs4_ht": 20,
    "ensemble_all_in": 32,
}

SEP_TYPE_LABELS: dict[str, str] = {
    "karaoke_lead_back": "MVSep Karaoke (lead/back vocals)",
    "mega_53_stem": "Mega 53-stem Model",
    "bs_roformer_sw": "BS Roformer SW (6 stems)",
    "demucs4_ht": "Demucs4 HT (4 stems)",
    "ensemble_all_in": "Ensemble All-In (21 outputs)",
}

# MVSEP stem token → lane key. ``None`` means "downloaded but not a lane":
# ``instrum-only`` / ``back-instrum`` are sums of other stems, and rendering
# them as lanes would double every instrument in the grid.
STEM_LANE_KEYS: dict[str, str | None] = {
    "vocals-lead": "lead_vocals",
    "vocals-back": "back_vocals",
    "instrum-only": None,
    "back-instrum": None,
    "vocals": "vocals",
    "instrum": None,
    "lead-vocal": "lead_vocals",
    "back-vocal": "back_vocals",
    "double-bass": "double_bass",
    "digital-piano": "digital_piano",
    "acoustic-guitar": "acoustic_guitar",
    "electric-guitar": "electric_guitar",
    "bowed_strings": "bowed_strings",
    "wind-chimes": "wind_chimes",
    "other-no-vocals-bass-drums": "other",
}

# MVSEP answers 400 for a bad key and 429 when the account is rate-limited.
_RETRY_STATUS = {429, 500, 502, 503, 504}


def _as_dict(value: object) -> dict[str, Any]:
    """MVSEP responses nest their payload under ``data``; treat junk as empty."""
    return value if isinstance(value, dict) else {}


def lane_key_for_token(token: str) -> str | None:
    """Lane key for an MVSEP stem token (``vocals-lead`` → ``lead_vocals``)."""
    text = str(token or "").strip().lower()
    if not text:
        return None
    if text in STEM_LANE_KEYS:
        return STEM_LANE_KEYS[text]
    return text.replace("-", "_").replace(" ", "_")


def _stem_token(filename: str, entry: dict[str, object]) -> str:
    """Stem token for one result entry: explicit field first, filename second."""
    for key in ("stem", "name", "stem_name"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    stem = Path(str(filename)).stem
    return stem.rsplit("_", 1)[-1].strip().lower()


def _duration_s(path: Path) -> float:
    """Duration in seconds via ffprobe (0.0 when it cannot be read)."""
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
        return float(out) if out else 0.0
    except Exception:  # pragma: no cover - ffprobe missing/unreadable
        return 0.0


def _excerpt(path: Path, max_seconds: float) -> Path | None:
    """Cut a bounded excerpt for upload, or None when the whole file is used."""
    if max_seconds <= 0:
        return None
    duration = _duration_s(path)
    if duration and duration <= max_seconds:
        return None
    target = Path(tempfile.mkdtemp(prefix="omnirip-mvsep-")) / f"{path.stem}_excerpt.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-t",
                f"{max_seconds:.3f}",
                "-i",
                str(path),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "320k",
                str(target),
            ],
            capture_output=True,
            check=True,
            timeout=300,
        )
    except Exception as exc:
        logger.info("MVSEP excerpt creation failed, uploading the whole file: %s", exc)
        return None
    return target if target.exists() and target.stat().st_size > 1024 else None


@dataclass(frozen=True, slots=True)
class HostedStem:
    """One stem the hosted service returned."""

    token: str
    lane_key: str
    filename: str
    url: str
    path: Path | None = None

    @property
    def label(self) -> str:
        return self.lane_key.replace("_", " ").upper()


@dataclass(slots=True)
class HostedResult:
    """Outcome of one hosted separation: what ran, what landed on disk."""

    job_hash: str = ""
    sep_type: int = 0
    algorithm: str = ""
    stems: tuple[HostedStem, ...] = ()
    downloaded: tuple[Path, ...] = ()
    skipped: tuple[str, ...] = ()
    uploaded_seconds: float = 0.0
    waited_s: float = 0.0
    message: str = ""
    extra: dict[str, object] = field(default_factory=dict)

    @property
    def lane_keys(self) -> tuple[str, ...]:
        return tuple(stem.lane_key for stem in self.stems)

    def describe(self) -> str:
        if not self.stems:
            return self.message or "hosted separation produced no usable stems"
        lanes = ", ".join(stem.label for stem in self.stems)
        model = self.algorithm or f"sep_type {self.sep_type}"
        return (
            f"Hosted ({model}): {len(self.stems)} stems in {self.waited_s:.0f}s — {lanes}"
        )


class MvsepClient:
    """Async MVSEP client: create a job, poll it, download the stems."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = API_BASE,
        timeout_s: float = 120.0,
        poll_interval_s: float = 4.0,
        max_wait_s: float = 1800.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.environ.get(MVSEP_KEY_VAR, ""))
        self._api_key = str(self._api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self.poll_interval_s = float(poll_interval_s)
        self.max_wait_s = float(max_wait_s)
        self._client = client
        self._algorithms: list[dict[str, object]] | None = None

    # -- plumbing ---------------------------------------------------------
    @property
    def available(self) -> bool:
        """True when an API key is configured (no network call)."""
        return bool(self._api_key)

    def _redact(self, text: str) -> str:
        return text.replace(self._api_key, "***") if self._api_key else text

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> MvsepClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    # -- API --------------------------------------------------------------
    async def account(self) -> dict[str, object]:
        """Account details for the configured key (also the key check)."""
        if not self.available:
            raise RuntimeError(f"no MVSEP key configured (set {MVSEP_KEY_VAR})")
        resp = await self._http().get(
            f"{self.base_url}/app/user", params={"api_token": self._api_key}
        )
        if resp.status_code == 400:
            raise RuntimeError("MVSEP rejected the API key (HTTP 400)")
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def algorithms(self) -> list[dict[str, object]]:
        """Separation types (cached for the client's lifetime)."""
        if self._algorithms is not None:
            return self._algorithms
        resp = await self._http().get(f"{self.base_url}/app/algorithms")
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("algorithms") if isinstance(payload, dict) else payload
        self._algorithms = [item for item in items or [] if isinstance(item, dict)]
        return self._algorithms

    async def sep_type_for(self, name: str) -> int:
        """Resolve a friendly name to MVSEP's ``sep_type`` (render_id)."""
        key = str(name or "").strip().lower()
        if key.isdigit():
            return int(key)
        if key in SEP_TYPES:
            return SEP_TYPES[key]
        # Fall back to a live lookup by model name, then to the default.
        with contextlib.suppress(Exception):
            for item in await self.algorithms():
                label = str(item.get("name", "")).lower()
                if key and key.replace("_", " ") in label:
                    render_id = item.get("render_id")
                    if isinstance(render_id, int):
                        return render_id
        return SEP_TYPES[DEFAULT_SEP_TYPE]

    async def separate(
        self,
        source: Path,
        dest_dir: Path,
        *,
        output_prefix: str,
        sep_type: str | int = DEFAULT_SEP_TYPE,
        max_seconds: float = 0.0,
        output_format: int = 1,
        progress: Callable[[float, str], None] | None = None,
        cancel: Callable[[], bool] | None = None,
    ) -> HostedResult:
        """Upload, wait, download. Raises RuntimeError with a redacted message.

        ``output_prefix`` is the lane-discovery stem prefix
        (``{input_stem}_{mode}``), so stems land as
        ``{output_prefix}_hosted_raw_{lane_key}.wav`` and the existing lane
        builder picks them up with no extra wiring.
        """
        if not self.available:
            raise RuntimeError(f"no MVSEP key configured (set {MVSEP_KEY_VAR})")
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"source audio not found: {source}")

        def _progress(pct: float, step: str) -> None:
            if progress is not None:
                progress(pct, step)

        def _cancelled() -> bool:
            return bool(cancel and cancel())

        started = asyncio.get_event_loop().time()
        resolved = await self.sep_type_for(str(sep_type))
        upload_path = _excerpt(source, float(max_seconds))
        uploaded_seconds = _duration_s(upload_path or source)
        tmp_upload = upload_path is not None
        staged: list[tuple[Path, Path]] = []
        try:
            _progress(5.0, f"uploading {uploaded_seconds:.0f}s to MVSEP…")
            data = await asyncio.to_thread(upload_path.read_bytes) if tmp_upload else None
            if data is None:
                data = await asyncio.to_thread(source.read_bytes)
            files = {
                "audiofile": (
                    (upload_path or source).name,
                    data,
                    "audio/mpeg" if (upload_path or source).suffix == ".mp3" else "audio/wav",
                )
            }
            resp = await self._http().post(
                f"{self.base_url}/separation/create",
                data={
                    "api_token": self._api_key,
                    "sep_type": str(resolved),
                    "output_format": str(output_format),
                },
                files=files,
            )
            if resp.status_code == 400:
                raise RuntimeError("MVSEP rejected the API key (HTTP 400)")
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"MVSEP create failed (HTTP {resp.status_code}): "
                    f"{self._redact(resp.text)[:200]}"
                )
            payload = resp.json()
            inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            job_hash = str((inner or {}).get("hash") or "").strip()
            if not job_hash:
                raise RuntimeError(f"MVSEP returned no job hash: {self._redact(resp.text)[:200]}")
            _progress(15.0, f"queued on MVSEP ({job_hash.rsplit('-', 1)[-1][:24]})…")

            status, body = await self._wait(job_hash, progress=_progress, cancel=_cancelled)
            waited = asyncio.get_event_loop().time() - started
            if status != "done":
                message = str(_as_dict(body.get("data")).get("message") or status)
                return HostedResult(
                    job_hash=job_hash,
                    sep_type=resolved,
                    waited_s=waited,
                    message=f"MVSEP job ended as '{status}': {self._redact(message)[:200]}",
                )

            data_block = _as_dict(body.get("data"))
            algorithm = str(data_block.get("algorithm") or "")
            entries = [
                item for item in (data_block.get("files") or []) if isinstance(item, dict)
            ]
            _progress(70.0, f"downloading {len(entries)} hosted stems…")
            dest_dir = Path(dest_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            stems: list[HostedStem] = []
            downloaded: list[Path] = []
            skipped: list[str] = []
            staged: list[tuple[Path, Path]] = []  # (staging file, final target)
            for index, entry in enumerate(entries):
                if _cancelled():
                    break
                url = str(entry.get("url") or entry.get("download_url") or "")
                filename = str(
                    entry.get("download_filename") or entry.get("filename") or Path(url).name
                )
                if not url or not filename:
                    continue
                token = _stem_token(filename, entry)
                lane_key = lane_key_for_token(token)
                if lane_key is None:
                    skipped.append(token)
                    continue
                target = dest_dir / f"{output_prefix}{HOSTED_RAW_TOKEN}{lane_key}.wav"
                stage = target.with_name(f"{target.name}.staging-{job_hash[-8:]}")
                await self._download(url, stage)
                staged.append((stage, target))
                stems.append(
                    HostedStem(
                        token=token,
                        lane_key=lane_key,
                        filename=filename,
                        url=url,
                        path=target,
                    )
                )
                downloaded.append(target)
                _progress(
                    70.0 + 25.0 * (index + 1) / max(1, len(entries)),
                    f"downloaded {lane_key.replace('_', ' ')}",
                )

            if not _cancelled() and staged:
                # Commit as one swap so a new run never mixes with the previous
                # run's stems (docs/14 M2): back up the old set, move the new
                # files in, then remove the backups. A failure restores the old
                # set instead of leaving a half-replaced directory.
                _swap_hosted_run(dest_dir, output_prefix, staged, job_hash)

            result = HostedResult(
                job_hash=job_hash,
                sep_type=resolved,
                algorithm=algorithm,
                stems=tuple(stems),
                downloaded=tuple(downloaded),
                skipped=tuple(skipped),
                uploaded_seconds=uploaded_seconds,
                waited_s=asyncio.get_event_loop().time() - started,
            )
            result.message = result.describe()
            return result
        finally:
            for stage, _target in staged:
                with contextlib.suppress(Exception):
                    stage.unlink()
            if tmp_upload and upload_path is not None:
                with contextlib.suppress(Exception):
                    upload_path.unlink()
                    upload_path.parent.rmdir()

    async def _wait(
        self,
        job_hash: str,
        *,
        progress: Callable[[float, str], None],
        cancel: Callable[[], bool],
    ) -> tuple[str, dict[str, Any]]:
        """Poll until the job leaves waiting/processing (or the budget runs out)."""
        deadline = asyncio.get_event_loop().time() + self.max_wait_s
        status = "waiting"
        body: dict[str, Any] = {}
        while True:
            if cancel():
                with contextlib.suppress(Exception):
                    await self._http().post(
                        f"{self.base_url}/separation/cancel",
                        data={"api_token": self._api_key, "hash": job_hash},
                    )
                return "cancelled", {}
            try:
                resp = await self._http().get(
                    f"{self.base_url}/separation/get", params={"hash": job_hash}
                )
                resp.raise_for_status()
                body = resp.json()
                status = str(body.get("status") or "").strip().lower() or "waiting"
            except httpx.HTTPError as exc:
                logger.info("MVSEP poll failed (will retry): %s", type(exc).__name__)
            if status == "waiting":
                block = _as_dict(body.get("data"))
                position = block.get("current_order")
                eta = block.get("eta_seconds")
                progress(
                    20.0,
                    f"MVSEP queue: {position if position is not None else '?'} ahead"
                    + (f", ~{eta}s" if eta else ""),
                )
            elif status == "processing":
                progress(45.0, "MVSEP is separating the track…")
            if status not in ("waiting", "processing", ""):
                return status, body
            if asyncio.get_event_loop().time() >= deadline:
                return "timeout", body
            await asyncio.sleep(self.poll_interval_s)

    async def _download(self, url: str, target: Path) -> None:
        """Stream one stem to ``target`` atomically (temp file + replace)."""
        tmp = target.with_suffix(target.suffix + ".part")
        async with self._http().stream("GET", url) as stream:
            stream.raise_for_status()
            with tmp.open("wb") as fh:
                async for chunk in stream.aiter_bytes():
                    fh.write(chunk)
        os.replace(tmp, target)


def _swap_hosted_run(
    dest_dir: Path,
    output_prefix: str,
    staged: list[tuple[Path, Path]],
    job_hash: str,
) -> None:
    """Replace the previous hosted run's stems with a freshly staged set.

    The old set is moved aside first, the new files are moved in, and only
    then are the backups removed. If anything fails mid-move the old set is
    restored and the staging files are dropped — a lane grid can therefore
    never see stems from two different hosted runs mixed together (docs/14
    M2).
    """
    dest_dir = Path(dest_dir)
    backup_suffix = f".old-{job_hash[-8:]}"
    old = sorted(dest_dir.glob(f"{output_prefix}{HOSTED_RAW_TOKEN}*.wav"))
    backups: list[tuple[Path, Path]] = [
        (p, p.with_name(f"{p.name}{backup_suffix}")) for p in old
    ]
    # The whole swap — backup, staging move-in, and restore — lives in one
    # try/except. A failure while moving the old set aside (disk full, perms)
    # restores exactly the files that were already moved; untouched originals
    # stay at their names, so the old run is never left split across two
    # naming schemes (docs/14 M2).
    backed_up: list[tuple[Path, Path]] = []
    try:
        for path, backup in backups:
            os.replace(path, backup)
            backed_up.append((path, backup))
        for stage, target in staged:
            os.replace(stage, target)
    except Exception:
        for _stage, target in staged:
            with contextlib.suppress(Exception):
                target.unlink()
        for stage, _target in staged:
            with contextlib.suppress(Exception):
                stage.unlink()
        for path, backup in backed_up:
            if backup.exists():
                with contextlib.suppress(Exception):
                    os.replace(backup, path)
        raise
    else:
        for _path, backup in backups:
            with contextlib.suppress(Exception):
                backup.unlink()
        # Sweep crash litter from runs that died mid-swap (docs/14 M6 review):
        # staging temps and old backups never match the lane globs, so without
        # this they would pile up until a manual clean.
        for litter in dest_dir.glob(f"{output_prefix}{HOSTED_RAW_TOKEN}*.wav.staging-*"):
            with contextlib.suppress(Exception):
                litter.unlink()
        for litter in dest_dir.glob(f"{output_prefix}{HOSTED_RAW_TOKEN}*.wav.old-*"):
            with contextlib.suppress(Exception):
                litter.unlink()
