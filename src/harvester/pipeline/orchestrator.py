"""Async stage-queue orchestrator for the M2 P2P-first workflow."""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections import deque
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from harvester.batch.report import BatchReport, batch_report_name, job_row, skipped_row
from harvester.batch.scanner import hunt_query_from_entry, scan_directory
from harvester.batch.trash import purge as purge_trash
from harvester.config import AppConfig
from harvester.models import (
    BatchScan,
    DownloadProgress,
    ErrorClass,
    ErrorInfo,
    EventKind,
    JobEvent,
    Mode,
    SkipReason,
    SourceKind,
    State,
    TrackJob,
    Verdict,
)
from harvester.pipeline.phase1_analyze import analyze_url
from harvester.pipeline.phase2_hunt import (
    build_hunt_queries,
    hunt_and_score,
    prepare_fallback,
    select_candidate,
    validate_lossless_file,
)
from harvester.pipeline.phase3_identify import identify_job
from harvester.pipeline.phase4_spectral import run_spectral_check
from harvester.pipeline.phase5_polish import polish_batch, polish_stream
from harvester.services.acoustid import AcoustidService
from harvester.services.ffmpeg import FfmpegService
from harvester.services.musicbrainz import CoverArtService
from harvester.services.slskd import SlskdService
from harvester.services.tagging import MetadataTagger
from harvester.services.ytdlp import YtdlpService
from harvester.util.errors import (
    ConfigError,
    DiskError,
    HarvesterError,
    JobCancelled,
    PermanentSource,
    RateLimited,
    ServiceUnavailable,
    TransientNetwork,
    ValidationError,
)
from harvester.util.retry import sleep_backoff
from harvester.util.subproc import SubprocessRegistry

StageHandler = Callable[[TrackJob], Awaitable[None]]

_P2P_TRANSIENT = (TransientNetwork, ValidationError, ServiceUnavailable)


class PipelineOrchestrator:
    """Own jobs, bounded stage queues, and the pipeline-to-UI event contract."""

    def __init__(
        self,
        config: AppConfig,
        *,
        ytdlp: YtdlpService | None = None,
        ffmpeg: FfmpegService | None = None,
        tagger: MetadataTagger | None = None,
        slskd: SlskdService | None = None,
        acoustid: AcoustidService | None = None,
        cover: CoverArtService | None = None,
        registry: SubprocessRegistry | None = None,
        event_queue: asyncio.Queue[JobEvent] | None = None,
    ) -> None:
        self.config = config
        self.registry = registry or SubprocessRegistry()
        self.ytdlp = ytdlp or YtdlpService(config, self.registry)
        self.ffmpeg = ffmpeg or FfmpegService(config, self.registry)
        self.tagger = tagger or MetadataTagger()
        self.slskd = slskd or SlskdService(config)
        self.acoustid = acoustid or AcoustidService(config, registry=self.registry)
        self.cover = cover or CoverArtService(config)
        self.events: asyncio.Queue[JobEvent] = event_queue or asyncio.Queue(maxsize=1000)
        self.jobs: dict[str, TrackJob] = {}
        self._batch_reports: dict[str, BatchReport] = {}
        self.last_batch_root: Path | None = None
        self._sequences: dict[str, int] = {}
        self._queues: dict[str, asyncio.Queue[TrackJob]] = {
            "analyze": asyncio.Queue(maxsize=8),
            "hunt": asyncio.Queue(maxsize=8),
            "p2p": asyncio.Queue(maxsize=8),
            "fallback": asyncio.Queue(maxsize=8),
            "identify": asyncio.Queue(maxsize=8),
            "spectral": asyncio.Queue(maxsize=8),
            "polish": asyncio.Queue(maxsize=8),
        }
        self._workers: list[asyncio.Task[None]] = []
        self._started = False
        self._stopping = False
        self.logger = logging.getLogger("harvester.pipeline")

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stopping = False
        self._workers = [
            *self._spawn_workers("analyze", self._analyze_stage, 2),
            *self._spawn_workers("hunt", self._hunt_stage, 2),
            *self._spawn_workers(
                "p2p", self._p2p_stage, self.config.slskd.max_concurrent_downloads
            ),
            *self._spawn_workers("fallback", self._fallback_stage, 2),
            *self._spawn_workers("identify", self._identify_stage, 1),
            *self._spawn_workers("spectral", self._spectral_stage, 1),
            *self._spawn_workers("polish", self._polish_stage, 2),
        ]

    async def submit_url(self, url: str) -> TrackJob:
        if self._stopping:
            raise RuntimeError("pipeline is shutting down")
        await self.start()
        job = TrackJob(mode=Mode.SINGLE_URL, input_url=url.strip())
        self.jobs[job.id] = job
        await self._emit_state(job, text=job.display_name)
        await self._queues["analyze"].put(job)
        return job

    async def probe_playlist(self, url: str) -> list[dict[str, Any]]:
        """Return playlist entries capped at ``batch.playlist_cap`` (D10)."""

        entries = await self.ytdlp.probe_playlist(url)
        return entries[: self.config.batch.playlist_cap]

    async def submit_playlist(self, url: str, *, confirmed: bool = False) -> list[TrackJob]:
        """Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)."""

        entries = await self.probe_playlist(url)
        if len(entries) > 1 and not confirmed:
            raise ValidationError(
                f"playlist has {len(entries)} entries; confirmation required"
            )
        jobs: list[TrackJob] = []
        for entry in entries:
            entry_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
            if not entry_url or not str(entry_url).startswith(("http", "ytsearch")):
                continue
            jobs.append(await self.submit_url(str(entry_url)))
        return jobs

    async def scan_batch(self, path: str | Path) -> BatchScan:
        """Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)."""

        scan = await asyncio.to_thread(scan_directory, Path(path), self.config)
        await self._emit_log(
            None,
            "INFO",
            (
                f"scan {scan.root}: found {scan.found}, skip {len(scan.skipped)}, "
                f"queue {len(scan.queued)}; free {scan.free_bytes / (1024 ** 2):.0f} MiB, "
                f"need {scan.needed_bytes / (1024 ** 2):.0f} MiB for the upgrades"
            ),
        )
        return scan

    async def submit_batch(
        self,
        path: str | Path | None = None,
        *,
        scan: BatchScan | None = None,
        confirmed: bool = False,
    ) -> BatchScan:
        """Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)."""

        if self._stopping:
            raise RuntimeError("pipeline is shutting down")
        await self.start()
        if scan is None:
            if path is None:
                raise ValidationError("submit_batch requires a directory path or a scan")
            scan = await self.scan_batch(path)
        if scan.needed_bytes > scan.free_bytes:
            raise DiskError(
                f"not enough free space for the batch: need "
                f"{scan.needed_bytes / (1024 ** 2):.0f} MiB, have "
                f"{scan.free_bytes / (1024 ** 2):.0f} MiB (docs/01 NFR-5)"
            )
        if len(scan.queued) > 25 and not confirmed:
            raise ValidationError(
                f"batch queues {len(scan.queued)} jobs (> 25); confirmation required"
            )

        report_path = self.config.paths.reports / batch_report_name(scan.root)
        report = BatchReport(report_path)
        for entry in scan.skipped:
            reason = entry.reason or SkipReason.UNREADABLE
            report.append(
                skipped_row(entry.path, reason=reason.value, old_bitrate=entry.bitrate_kbps)
            )
        self.last_batch_root = scan.root

        for entry in scan.queued:
            query = hunt_query_from_entry(entry)
            job = TrackJob(
                mode=Mode.BATCH_AUDIT,
                input_url=f"ytsearch1:{query}",
                input_path=entry.path,
                batch_root=scan.root,
                query_raw=query,
                orig_codec=entry.codec,
                orig_bitrate=entry.bitrate_kbps,
                orig_duration_s=entry.duration_s,
                orig_size=entry.size_bytes,
                orig_tags=_entry_tags(entry),
            )
            self.jobs[job.id] = job
            self._batch_reports[job.id] = report
            await self._emit_state(job, text=job.display_name)
            await self._queues["analyze"].put(job)
        await self._emit_log(
            None,
            "INFO",
            f"batch queued {len(scan.queued)} upgrade job(s); report: {report.path.name}",
        )
        return scan

    async def purge_batch_trash(self) -> int:
        """Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)."""

        if self.last_batch_root is None:
            return 0
        removed = await asyncio.to_thread(
            purge_trash, self.last_batch_root, self.config.batch.trash_retention_days
        )
        return removed

    async def run(self) -> None:
        """Start workers and wait until shutdown is requested."""

        await self.start()
        while not self._stopping:
            await asyncio.sleep(0.25)

    async def wait_for_idle(self, *, timeout_s: float = 30.0) -> None:
        """Wait until every submitted job has reached a terminal state.

        Queue joins are racy across stage boundaries (a stage can momentarily drain
        while the next stage still holds the job), so poll job state instead.
        """

        async def _drain() -> None:
            while True:
                if self.jobs and all(job.state.terminal for job in self.jobs.values()):
                    return
                await asyncio.sleep(0.02)

        await asyncio.wait_for(_drain(), timeout=timeout_s)

    async def cancel(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if job is None or job.state.terminal:
            return
        job.request_cancel()
        await self.registry.terminate_prefix(job_id, grace_s=self.config.timeouts.kill_grace_s)
        await self._mark_cancelled(job)

    async def cancel_all(self) -> None:
        await asyncio.gather(
            *(
                self.cancel(job_id)
                for job_id, job in tuple(self.jobs.items())
                if not job.state.terminal
            ),
            return_exceptions=True,
        )

    async def shutdown(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        for job in self.jobs.values():
            if not job.state.terminal:
                job.request_cancel()
        await self.registry.terminate_all(grace_s=self.config.timeouts.kill_grace_s)
        await asyncio.gather(
            *(self._mark_cancelled(job) for job in self.jobs.values()), return_exceptions=True
        )
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        await asyncio.gather(
            self.slskd.close(), self.acoustid.close(), self.cover.close(), return_exceptions=True
        )
        self._started = False

    def _spawn_workers(
        self, stage: str, handler: StageHandler, count: int
    ) -> list[asyncio.Task[None]]:
        return [
            asyncio.create_task(
                self._worker_loop(stage, self._queues[stage], handler),
                name=f"harvester-{stage}-{index}",
            )
            for index in range(count)
        ]

    async def _worker_loop(
        self,
        stage: str,
        queue: asyncio.Queue[TrackJob],
        handler: StageHandler,
    ) -> None:
        while True:
            job = await queue.get()
            try:
                await handler(job)
            except JobCancelled:
                await self._mark_cancelled(job)
            except Exception as exc:
                if job.cancel_requested:
                    await self._mark_cancelled(job)
                else:
                    await self._fail(job, exc, stage=stage)
            finally:
                queue.task_done()

    async def _analyze_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        job.transition(State.ANALYZING, reason="input analysis")
        await self._emit_state(job)
        if job.mode is Mode.BATCH_AUDIT:
            # Phase 1 for Mode B was the directory scan (docs/03 \u00a71B); the
            # original file metadata already lives on the job in ``orig_*``.
            await self._emit_log(job, "INFO", "batch metadata carried from the scan")
        else:
            await analyze_url(job, self.ytdlp)
        self._check_cancel(job)
        job.transition(State.HUNTING, reason="probe complete")
        await self._emit_state(job)
        await self._queues["hunt"].put(job)

    async def _hunt_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        if self.config.slskd.acquisition_mode == "highest_quality_mp3":
            prepare_fallback(job, reason="highest-quality MP3 policy skips P2P")
            await self._emit_log(job, "INFO", "P2P skipped by highest-quality MP3 policy")
            job.transition(State.FALLBACK_DOWNLOADING, reason="policy skips P2P")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return
        if self.config.slskd.acquisition_mode == "fast_fallback":
            prepare_fallback(job, reason="fast fallback policy skips P2P")
            await self._emit_log(job, "INFO", "P2P skipped by fast-fallback policy")
            job.transition(State.FALLBACK_DOWNLOADING, reason="policy skips P2P")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return
        if not self.slskd.available:
            reason = (
                "degraded to fallback"
                if job.fallback_attempted
                else self.slskd.breaker.last_failure_reason or "slskd unavailable"
            )
            prepare_fallback(job, reason=reason)
            await self._emit_log(job, "WARNING", f"P2P hunt fast-failed; {reason}")
            job.transition(State.FALLBACK_DOWNLOADING, reason="P2P unavailable")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return

        queries = build_hunt_queries(job)
        if not queries:
            prepare_fallback(job, reason="no hunt queries derivable")
            await self._emit_log(job, "WARNING", "no P2P queries; using stream fallback")
            job.transition(State.FALLBACK_DOWNLOADING, reason="no queries")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return

        await self._emit_log(job, "INFO", f"hunting {queries[0]}")
        try:
            candidates = await hunt_and_score(self.slskd, job)
        except ServiceUnavailable:
            prepare_fallback(
                job, reason=self.slskd.breaker.last_failure_reason or "slskd unavailable"
            )
            await self._emit_log(job, "WARNING", "slskd search failed; using stream fallback")
            job.transition(State.FALLBACK_DOWNLOADING, reason="search failure")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return
        if not candidates:
            prepare_fallback(job, reason="no lossless candidates found")
            await self._emit_log(job, "INFO", "no P2P candidates; using stream fallback")
            job.transition(State.FALLBACK_DOWNLOADING, reason="no candidates")
            await self._emit_state(job)
            await self._queues["fallback"].put(job)
            return
        job.candidates = candidates
        job.candidate_cursor = 0
        await self._emit_log(
            job, "INFO", f"{len(candidates)} candidate(s) ranked; top: {candidates[0].filename}"
        )
        job.transition(State.P2P_DOWNLOADING, reason="candidate selected")
        await self._emit_state(job)
        await self._queues["p2p"].put(job)

    async def _p2p_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        while True:
            candidate = select_candidate(job)
            if candidate is None:
                await self._enter_fallback(
                    job, f"P2P candidates exhausted ({job.p2p_retries} retries)"
                )
                return
            await self._emit_log(
                job,
                "INFO",
                f"downloading {candidate.filename} from {candidate.username}",
            )
            try:
                source = await self.slskd.download(candidate)
                await validate_lossless_file(source)
                await self._validate_download_duration(job, actual=source)
                job.workspace_path = await asyncio.to_thread(
                    self._handoff_to_workspace, job, source
                )
                job.source_kind = SourceKind.P2P_FLAC
                job.transition(State.IDENTIFYING, reason="P2P download verified")
                await self._emit_state(job)
                await self._queues["identify"].put(job)
                return
            except _P2P_TRANSIENT as exc:
                job.p2p_retries += 1
                await self._quarantine_candidate(job, exc)
                if job.p2p_retries <= 1 and job.candidate_cursor + 1 < len(job.candidates):
                    job.candidate_cursor += 1
                    await self._emit_log(
                        job,
                        "WARNING",
                        f"candidate failed ({exc}); trying next candidate",
                    )
                    continue
                await self._enter_fallback(job, f"P2P download failed: {exc}")
                return

    async def _enter_fallback(self, job: TrackJob, reason: str) -> None:
        if job.fallback_attempted:
            await self._fail(
                job,
                TransientNetwork(reason),
                stage="p2p",
            )
            return
        prepare_fallback(job, reason=reason)
        await self._emit_log(job, "WARNING", f"{reason}; using stream fallback")
        job.transition(State.FALLBACK_DOWNLOADING, reason="P2P lane failed")
        await self._emit_state(job)
        await self._queues["fallback"].put(job)

    async def _fallback_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        workspace = self.config.paths.job_workspace(job.id)
        attempts = 0
        while attempts < 2:
            try:
                path = await self.ytdlp.download(
                    job.input_url or "",
                    workspace,
                    job_id=job.id,
                    progress_callback=lambda progress: self._on_progress(job, progress),
                )
                job.workspace_path = path
                job.source_kind = await self.ffmpeg.source_kind(path, job_id=job.id)
                await self._validate_download_duration(job, actual=path)
                job.transition(State.IDENTIFYING, reason="fallback download complete")
                await self._emit_state(job)
                await self._queues["identify"].put(job)
                return
            except (PermanentSource, ConfigError):
                raise
            except (RateLimited, TransientNetwork, ValidationError):
                attempts += 1
                if attempts >= 2:
                    raise
                await self._emit_log(
                    job, "WARNING", f"fallback attempt failed; retrying ({attempts}/1)"
                )
                await sleep_backoff(attempts - 1)

    async def _identify_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        await identify_job(job, self.acoustid)
        source_label = job.canonical_meta.source if job.canonical_meta else "unknown"
        confidence = job.canonical_meta.confidence if job.canonical_meta else None
        detail = f"{source_label}"
        if confidence is not None:
            detail += f" (confidence {confidence:.2f})"
        await self._emit_log(job, "INFO", f"identity resolved from {detail}")
        if job.source_kind is SourceKind.P2P_FLAC:
            job.transition(State.SPECTRAL_CHECK, reason="P2P lossless claim")
            await self._emit_state(job)
            await self._queues["spectral"].put(job)
        else:
            job.transition(State.POLISHING, reason="stream file identity")
            await self._emit_state(job)
            await self._queues["polish"].put(job)

    async def _spectral_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        result = await run_spectral_check(job, self.config, self.ffmpeg)
        job.spectral = result
        cutoff = (
            f"cutoff={result.cutoff_hz:.0f}Hz " if result.cutoff_hz is not None else ""
        )
        steepness = (
            f"steepness={result.steepness_db_per_khz:.1f}dB/kHz "
            if result.steepness_db_per_khz is not None
            else ""
        )
        await self._emit_log(
            job,
            "INFO",
            f"spectral {result.verdict.value} {cutoff}{steepness}({result.detail})",
        )
        if result.verdict is Verdict.FRAUD:
            await self._emit_log(job, "WARNING", "FRAUD: upscaled lossy file rejected")
            await self._cleanup_workspace(job)
            await self._enter_fallback(job, "spectral FRAUD verdict")
            return
        if result.verdict is Verdict.INCONCLUSIVE and self.config.spectral.strict:
            await self._emit_log(job, "WARNING", "INCONCLUSIVE under strict mode; falling back")
            await self._cleanup_workspace(job)
            await self._enter_fallback(job, "spectral INCONCLUSIVE under strict mode")
            return
        job.transition(State.POLISHING, reason="spectral gate passed")
        await self._emit_state(job)
        await self._queues["polish"].put(job)

    async def _polish_stage(self, job: TrackJob) -> None:
        self._check_cancel(job)
        cover_bytes = None
        release_id = job.canonical_meta.mb_release_id if job.canonical_meta else None
        if release_id:
            cover_bytes = await self.cover.fetch_front(release_id)
        if job.mode is Mode.BATCH_AUDIT:
            output = await polish_batch(
                job, self.config, self.ffmpeg, self.tagger, cover_bytes=cover_bytes
            )
        else:
            output = await polish_stream(
                job, self.config, self.ffmpeg, self.tagger, cover_bytes=cover_bytes
            )
        job.progress = 100.0
        job.transition(State.COMPLETED, reason="tagged file placed")
        await self._emit_state(job, text=str(output))
        await self._emit_log(job, "INFO", f"completed: {output}")
        if job.mode is Mode.BATCH_AUDIT:
            self._report_row(job, status="upgraded")
        await self._cleanup_workspace(job)

    async def _validate_download_duration(
        self, job: TrackJob, *, actual: Path | None = None
    ) -> None:
        expected = _number(job.probe_meta.get("duration"))
        target = actual or job.workspace_path
        if expected is None or expected <= 0 or target is None:
            return
        measured = await self.ffmpeg.probe_duration(target, job_id=job.id)
        if abs(measured - expected) / expected > 0.05:
            raise ValidationError(
                f"download duration mismatch: expected {expected:.1f}s, got {measured:.1f}s"
            )

    async def _quarantine_candidate(self, job: TrackJob, exc: Exception) -> None:
        selected = job.selected_candidate
        quit_dir = self.config.paths.quarantine
        quit_dir.mkdir(parents=True, exist_ok=True)
        base = self.config.slskd.download_dir.expanduser()
        target = (
            base / (selected.username if selected else "") / (selected.filename if selected else "")
        )
        if target.is_file():
            destination = quit_dir / f"{job.id}-{target.name}"
            await asyncio.to_thread(shutil.copy2, target, destination)
        await self._emit_log(
            job,
            "WARNING",
            f"quarantined invalid P2P file: {exc}",
        )

    def _handoff_to_workspace(self, job: TrackJob, source: Path) -> Path:
        workspace = self.config.paths.job_workspace(job.id)
        workspace.mkdir(parents=True, exist_ok=True)
        destination = workspace / f"{job.id}.flac"
        shutil.copy2(source, destination)
        return destination

    async def _on_progress(self, job: TrackJob, progress: DownloadProgress) -> None:
        job.download = progress
        if progress.percent is not None:
            job.progress = max(0.0, min(100.0, progress.percent))
        await self._emit_progress(job)

    async def _fail(self, job: TrackJob, exc: Exception, *, stage: str) -> None:
        if job.state.terminal:
            return
        error_class = exc.error_class if isinstance(exc, HarvesterError) else ErrorClass.UNKNOWN
        retryable = exc.retryable if isinstance(exc, HarvesterError) else False
        message = str(exc) or exc.__class__.__name__
        job.error = ErrorInfo(
            error_class=error_class,
            message=message,
            retryable=retryable,
            user_hint=exc.user_hint if isinstance(exc, HarvesterError) else None,
        )
        self.logger.exception("job failed in %s", stage, extra={"job_id": job.id, "phase": stage})
        if not job.state.terminal:
            job.transition(State.FAILED, reason=f"{stage}: {message}")
        await self._emit_error(job, message)
        await self._emit_state(job)
        if job.mode is Mode.BATCH_AUDIT:
            self._report_row(job, status="failed", error=message)
        await self._cleanup_workspace(job)

    async def _mark_cancelled(self, job: TrackJob) -> None:
        if job.state.terminal:
            return
        job.cancel_requested = True
        job.transition(State.CANCELLED, reason="user or application shutdown")
        await self._emit_state(job)
        await self._emit_log(job, "INFO", "cancelled")
        if job.mode is Mode.BATCH_AUDIT:
            self._report_row(job, status="cancelled")
        await self._cleanup_workspace(job)

    def _report_row(self, job: TrackJob, *, status: str, error: str | None = None) -> None:
        """Append the terminal report row for a Mode B job (FR-14: per completed job)."""

        report = self._batch_reports.get(job.id)
        if report is None:
            return
        report.append(job_row(job, status=status, error=error))

    def _check_cancel(self, job: TrackJob) -> None:
        if job.cancel_requested or self._stopping:
            raise JobCancelled("job cancellation requested")

    async def _cleanup_workspace(self, job: TrackJob) -> None:
        workspace = self.config.paths.job_workspace(job.id)
        if workspace.exists():
            await asyncio.to_thread(_remove_workspace, workspace)

    async def _emit_state(self, job: TrackJob, *, text: str | None = None) -> None:
        await self._put_event(
            JobEvent(
                job_id=job.id,
                kind=EventKind.STATE,
                seq=self._next_seq(job.id),
                state=job.state,
                text=text or job.display_name,
            )
        )

    async def _emit_progress(self, job: TrackJob) -> None:
        await self._put_event(
            JobEvent(
                job_id=job.id,
                kind=EventKind.PROGRESS,
                seq=self._next_seq(job.id),
                state=job.state,
                progress=job.download,
            )
        )

    async def _emit_log(
        self, job: TrackJob | None, level: str, text: str
    ) -> None:
        job_id = job.id if job is not None else "batch"
        await self._put_event(
            JobEvent(
                job_id=job_id,
                kind=EventKind.LOG,
                seq=self._next_seq(job_id),
                state=job.state if job is not None else None,
                level=level,
                text=text,
            )
        )

    async def _emit_error(self, job: TrackJob, text: str) -> None:
        await self._put_event(
            JobEvent(
                job_id=job.id,
                kind=EventKind.ERROR,
                seq=self._next_seq(job.id),
                state=job.state,
                level="ERROR",
                text=text,
                error=job.error,
            )
        )

    async def _put_event(self, event: JobEvent) -> None:
        try:
            self.events.put_nowait(event)
        except asyncio.QueueFull:
            # Backpressure: shed the least-informative event first, never STATE/ERROR
            # (docs/08 \u00a73). Fall back to blocking when only those remain.
            if self._drop_oldest(EventKind.PROGRESS) or self._drop_oldest(EventKind.LOG):
                self.events.put_nowait(event)
            else:
                await self.events.put(event)

    def _drop_oldest(self, kind: EventKind) -> bool:
        queue: deque[JobEvent] = cast(Any, self.events)._queue  # noqa: SLF001
        for index, candidate in enumerate(queue):
            if candidate.kind is kind:
                del queue[index]
                return True
        return False

    def _next_seq(self, job_id: str) -> int:
        sequence = self._sequences.get(job_id, 0) + 1
        self._sequences[job_id] = sequence
        return sequence


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _entry_tags(entry) -> dict[str, object]:
    """Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03 \u00a71B.6)."""

    tags: dict[str, object] = {}
    if entry.title:
        tags["title"] = entry.title
    if entry.artist:
        tags["artist"] = entry.artist
    if entry.album:
        tags["album"] = entry.album
    return tags


def _remove_workspace(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _remove_workspace(child)
        else:
            child.unlink(missing_ok=True)
    path.rmdir()


__all__ = ["PipelineOrchestrator"]
