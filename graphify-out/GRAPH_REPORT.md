# Graph Report - OmniRip  (2026-09-18)

## Corpus Check
- 102 files · ~52,202 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .toml 1, .tcss 1)

## Summary
- 1680 nodes · 3810 edges · 137 communities (66 shown, 71 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 525 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- PipelineOrchestrator
- CanonicalMetadata
- scanner.py
- AcoustidService
- SourceKind
- Milestone M7 — QA & packaging
- Verdict
- JobEvent
- analysis/restoration.py
- Mode
- test_orchestrator_m4.py
- config.py
- test_playlist.py
- HarvesterApp
- logging_setup.py
- SlskdService
- app.py
- CoverArtService
- QualityEvidence
- Harvester (Hybrid Music Harvest & Curation Engine)
- phase1_analyze.py
- ValidationError
- Pipeline orchestrator
- .__init__
- test_orchestrator.py
- test_orchestrator_m3.py
- ComposeResult
- Phase 1 — Input Analysis
- titleclean.py
- EnvironmentStatus
- test_ui_pilot.py
- CircuitBreaker
- models.py
- TrackJob
- yt-dlp
- ytdlp.py
- .submit_batch
- Spectral fixture connectivity gap
- test_orchestrator_m5.py
- test_batch_swap.py
- circuit.py
- yt-dlp metadata probe
- Textual TUI
- phase2_hunt
- FR-9 — Spectral anti-fraud for P2P lossless claims
- Minimal Implementation Ladder
- orchestrator.py
- FfmpegService
- acoustid.py
- Phase 1 URL and batch adapter split
- test_models.py
- Mode B — Local Batch Audit
- .__init__
- BatchConfirmScreen
- PlaylistConfirmScreen
- Graphify Knowledge Graph
- phase3_identify
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- phase4_spectral
- CI Workflow
- .wait_for_idle
- phase1_analyze
- FirstRunNoticeScreen
- P2P candidate scoring
- OmniRip
- NFR-1 — Strict async
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- harvester_analysis_scoring
- batch/__init__.py
- services/__init__.py
- AC-1 — Launch < 3 s
- AC-10 — No-key fallback chain
- AC-8 — Cancel within 2 s
- D2 — Upcast honesty: provenance tags mandatory
- D7 — ID3v2.3 / Vorbis comments
- Runtime dependency set
- yt-dlp kill and cancel semantics
- Textual pilot tests
- Definition of done
- Enhanced development prompt
- ui/__init__.py
- util/__init__.py
- harvester
- Legal & ethical constraints (normative for UX)
- NFR-2 — Bounded concurrency
- AcoustID SQLite cache
- CanonicalMetadata
- External binaries
- mutagen tagging library
- harvester package layout
- Quarantine directory
- Workspace directory
- Fallback legal and no-DRM constraint
- FirstRunNotice
- Cancelled
- End-to-end tests
- FraudVerdict
- PermanentSource
- pytest and pytest-asyncio
- RateLimited
- respx HTTP mocking
- Module-by-module build order
- Constraints and honesty
- Secrets directive
- Strict async directive
- harvester_analysis
- harvester_pipeline
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_acoustid
- harvester_util_subproc
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- harvester_analysis_titleclean
- harvester_batch_report
- harvester_batch_scanner
- harvester_batch_trash
- harvester_pipeline_phase1_analyze
- harvester_pipeline_phase3_identify
- harvester_pipeline_phase4_spectral
- harvester_services_environment
- harvester_services_ffmpeg
- harvester_services_musicbrainz
- harvester_services_slskd
- harvester_services_tagging
- harvester_services_ytdlp
- harvester_ui_bridge
- harvester_util_circuit
- harvester_util_errors
- harvester_util_fsatomic
- harvester_util_logging_setup
- harvester_util_retry

## God Nodes (most connected - your core abstractions)
1. `TrackJob` - 102 edges
2. `PipelineOrchestrator` - 82 edges
3. `ValidationError` - 61 edges
4. `CanonicalMetadata` - 50 edges
5. `AppConfig` - 47 edges
6. `HarvesterApp` - 43 edges
7. `load_config()` - 41 edges
8. `Mode` - 39 edges
9. `SourceKind` - 39 edges
10. `ConfigError` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Milestone M1 — Mode A fallback-only (CHANGELOG entry)` --semantically_similar_to--> `Milestone M1 — Mode A, fallback-only`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/10-roadmap.md
- `Milestone M3 — Ground-truth ID (CHANGELOG entry)` --semantically_similar_to--> `Milestone M3 — Ground-truth ID`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/10-roadmap.md
- `Milestone M4 — Spectral anti-fraud (CHANGELOG entry)` --semantically_similar_to--> `Milestone M4 — Spectral anti-fraud`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/10-roadmap.md
- `Milestone M5 — Mode B batch audit (CHANGELOG entry)` --semantically_similar_to--> `Milestone M5 — Mode B batch audit`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/10-roadmap.md
- `Milestone M6 — TUI hardening (CHANGELOG entry)` --semantically_similar_to--> `Milestone M6 — TUI hardening`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/10-roadmap.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Async stage-queue worker architecture** — docs_02_architecture_orchestrator, docs_02_architecture_q_analyze, docs_02_architecture_q_hunt, docs_02_architecture_q_p2p_dl, docs_02_architecture_q_fallback_dl, docs_02_architecture_q_identify, docs_02_architecture_q_spectral, docs_02_architecture_q_polish, docs_02_architecture_jobevent [EXTRACTED 1.00]
- **CI lint and test flow** — _github_workflows_ci_ci, _github_workflows_ci_ruff, _github_workflows_ci_pytest [EXTRACTED 1.00]
- **Five-phase acquisition and curation flow** — docs_03_pipeline_phase_1_input_analysis, docs_03_pipeline_phase_2_hybrid_hunt, docs_03_pipeline_phase_3_ground_truth_id, docs_03_pipeline_phase_4_spectral_check, docs_03_pipeline_phase_5_polish_and_sync [EXTRACTED 1.00]
- **Ground-truth identification** — readme_fpcalc, graphify_out_memory_query_20260918_090058_d4ba1f0c_seven_architecture_questions_about_phase_2_the_or_acoustid, docs_03_pipeline_phase_3_ground_truth_id [EXTRACTED 1.00]
- **Mode B atomic replacement with .trash rollback** — docs_01_requirements_mode_b, docs_01_requirements_fr_13, docs_01_requirements_trash_dir [EXTRACTED 1.00]
- **P2P-first, stream-fallback acquisition** — readme_harvester, readme_slskd, readme_yt_dlp [EXTRACTED 1.00]
- **M4 spectral anti-fraud verification chain (spec → code → verdicts → fixtures)** — docs_04_spectral_antifraud_check, docs_04_spectral_antifraud_spectral_py, docs_04_spectral_antifraud_verdict_rules, docs_04_spectral_antifraud_fixture_suite [EXTRACTED 1.00]
- **Verification and canonical metadata flow** — docs_05_fingerprinting_metadata_fpcalc_chromaprint, docs_05_fingerprinting_metadata_acoustid_lookup, docs_05_fingerprinting_metadata_musicbrainz_release_selection, docs_05_fingerprinting_metadata_cover_art_archive, docs_05_fingerprinting_metadata_mutagen_tagging [EXTRACTED 1.00]
- **Fallback lane across milestones** — docs_10_roadmap_m1, docs_10_roadmap_m2, docs_10_roadmap_m4 [INFERRED 0.65]
- **Release gate definition** — docs_10_roadmap_m7, docs_10_roadmap_smoke_checklist, changelog_0_1_0_release [INFERRED 0.75]
- **slskd 0.26 OpenAPI compatibility fix** — changelog_slskd_0_26_api_compatibility, docs_10_roadmap_m2, docs_10_roadmap_d6 [INFERRED 0.85]

## Communities (137 total, 71 thin omitted)

### Community 0 - "PipelineOrchestrator"
Cohesion: 0.15
Nodes (9): ErrorInfo, PipelineOrchestrator, Exception, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., _remove_workspace(), prepare_fallback() (+1 more)

### Community 1 - "CanonicalMetadata"
Cohesion: 0.06
Nodes (71): mutagen_id3, soundfile, move_to_trash(), purge(), Path, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step). (+63 more)

### Community 2 - "scanner.py"
Cohesion: 0.07
Nodes (55): mutagen, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps() (+47 more)

### Community 3 - "AcoustidService"
Cohesion: 0.09
Nodes (24): AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number(), Any, AsyncClient (+16 more)

### Community 4 - "SourceKind"
Cohesion: 0.18
Nodes (16): SourceKind, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 5 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 6 - "Verdict"
Cohesion: 0.09
Nodes (44): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+36 more)

### Community 7 - "JobEvent"
Cohesion: 0.10
Nodes (23): Apply, EventKind, JobEvent, Any, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08… (+15 more)

### Community 8 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (36): numpy, _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive() (+28 more)

### Community 9 - "Mode"
Cohesion: 0.14
Nodes (27): difflib, Mode, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift(), metadata_from_orig_tags(), metadata_from_query() (+19 more)

### Community 10 - "test_orchestrator_m4.py"
Cohesion: 0.16
Nodes (17): SpectralResult, _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio (+9 more)

### Community 11 - "config.py"
Cohesion: 0.05
Nodes (63): argparse, ArgumentParser, copy, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+55 more)

### Community 12 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 13 - "HarvesterApp"
Cohesion: 0.12
Nodes (6): Changed, HarvesterApp, wrapped(), Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Submitted

### Community 14 - "logging_setup.py"
Cohesion: 0.10
Nodes (20): dataclasses, logging, logging_handlers, LogRecord, platformdirs, queue, Platform-aware runtime directories., CallbackHandler (+12 more)

### Community 15 - "SlskdService"
Cohesion: 0.06
Nodes (49): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+41 more)

### Community 16 - "app.py"
Cohesion: 0.19
Nodes (14): AppConfig, check_slskd(), detect_environment(), probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable., Run independent dependency checks concurrently. (+6 more)

### Community 17 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 18 - "QualityEvidence"
Cohesion: 0.08
Nodes (36): enum, RuntimeError, assess_replacement(), _assessment(), StrEnum, quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This… (+28 more)

### Community 19 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.08
Nodes (34): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Batch trash manager, Incremental JSONL batch report, Metadata fallback chain (+26 more)

### Community 20 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+11 more)

### Community 21 - "ValidationError"
Cohesion: 0.15
Nodes (21): ProgressCallback, ErrorClass, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable. (+13 more)

### Community 22 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 24 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 25 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 26 - "ComposeResult"
Cohesion: 0.11
Nodes (8): ComposeResult, Pressed, HelpScreen, PurgeConfirmScreen, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17)., Confirm trash purge before deleting rollback sources (docs/08 §5, D5).

### Community 27 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Five-phase pipeline specification, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+13 more)

### Community 28 - "titleclean.py"
Cohesion: 0.17
Nodes (17): Match, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase…, NFKD-normalize and fold diacritics to ASCII while keeping the case. (+9 more)

### Community 29 - "EnvironmentStatus"
Cohesion: 0.16
Nodes (7): DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static, test_all_required_dependencies_ready_when_optional_services_are_down(), test_required_dependency_controls_ready_state()

### Community 30 - "test_ui_pilot.py"
Cohesion: 0.08
Nodes (25): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+17 more)

### Community 31 - "CircuitBreaker"
Cohesion: 0.13
Nodes (7): SearchResponse, SlskdFile, CircuitBreaker, Fast-fail a dependency lane after consecutive failures., FakeSlskd, FakeSlskd, FakeSlskd

### Community 32 - "models.py"
Cohesion: 0.14
Nodes (15): httpx, mutagen_flac, pathlib, re, Domain models shared by the pipeline, services, and UI., Path, Phase 2 hunt policy: queries, candidate selection, and fallback decisions., Run the deterministic Phase 2.3 post-download validation in a thread. (+7 more)

### Community 33 - "TrackJob"
Cohesion: 0.16
Nodes (7): Mutable job aggregate owned by the orchestrator., TrackJob, Return the next candidate from the ranked list, or None when exhausted., select_candidate(), JobTable, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 34 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 35 - "ytdlp.py"
Cohesion: 0.28
Nodes (10): collections, DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress (+2 more)

### Community 36 - ".submit_batch"
Cohesion: 0.10
Nodes (12): _entry_tags(), _number(), Any, Path, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14). (+4 more)

### Community 37 - "Spectral fixture connectivity gap"
Cohesion: 0.10
Nodes (22): Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation (+14 more)

### Community 38 - "test_orchestrator_m5.py"
Cohesion: 0.06
Nodes (37): BatchReport, job_row(), Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4)., Path, Batch report tests: schema, incremental appends, row builders (FR-14). (+29 more)

### Community 39 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (7): Asynchronous pipeline stages., _job(), Path, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 40 - "circuit.py"
Cohesion: 0.31
Nodes (6): BreakerState, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens()

### Community 41 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 42 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 43 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 44 - "FR-9 — Spectral anti-fraud for P2P lossless claims"
Cohesion: 0.40
Nodes (5): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D3 — Spectral check scope: P2P lossless claims only, FR-10 — Provenance-based spectral exemption, FR-9 — Spectral anti-fraud for P2P lossless claims

### Community 45 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 46 - "orchestrator.py"
Cohesion: 0.10
Nodes (21): asyncio, collections_abc, shlex, shutil, Pure analysis logic: query cleaning and P2P candidate ranking., Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Async stage-queue orchestrator for the M2 P2P-first workflow., excerpt_window() (+13 more)

### Community 47 - "FfmpegService"
Cohesion: 0.10
Nodes (16): Process, pytest, Queue, FfmpegService, ndarray, Path, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+8 more)

### Community 48 - "acoustid.py"
Cohesion: 0.12
Nodes (18): datetime, hashlib, json, os, sqlite3, batch_report_name(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14). (+10 more)

### Community 49 - "Phase 1 URL and batch adapter split"
Cohesion: 0.40
Nodes (5): Batch adapter, Normalized Phase 1 facade, Phase 1 architecture conclusion, Phase 1 URL and batch adapter split, URL adapter

### Community 50 - "test_models.py"
Cohesion: 0.50
Nodes (3): test_canonical_metadata_normalizes_artists_and_serializes(), test_source_and_verdict_defaults_are_explicit(), test_track_job_display_name_prefers_canonical_metadata()

### Community 51 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 53 - "BatchConfirmScreen"
Cohesion: 0.33
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 55 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 56 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 57 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 58 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 59 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 60 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 61 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 63 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 65 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 67 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 70 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 73 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 74 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 75 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

## Knowledge Gaps
- **163 isolated node(s):** `harvester`, `Answer`, `Source Nodes`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 600 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `CanonicalMetadata`, `scanner.py`, `AcoustidService`, `SourceKind`, `Verdict`, `JobEvent`, `Mode`, `test_orchestrator_m4.py`, `config.py`, `test_playlist.py`, `HarvesterApp`, `SlskdService`, `app.py`, `CoverArtService`, `ValidationError`, `test_orchestrator.py`, `test_orchestrator_m3.py`, `TrackJob`, `ytdlp.py`, `.submit_batch`, `test_orchestrator_m5.py`, `orchestrator.py`, `FfmpegService`, `.wait_for_idle`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `TrackJob` connect `TrackJob` to `PipelineOrchestrator`, `CanonicalMetadata`, `Verdict`, `JobEvent`, `Mode`, `test_orchestrator_m4.py`, `SlskdService`, `app.py`, `QualityEvidence`, `phase1_analyze.py`, `EnvironmentStatus`, `test_ui_pilot.py`, `models.py`, `.submit_batch`, `test_orchestrator_m5.py`, `test_batch_swap.py`, `orchestrator.py`, `acoustid.py`, `test_models.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `app.py` to `PipelineOrchestrator`, `CanonicalMetadata`, `scanner.py`, `AcoustidService`, `models.py`, `ytdlp.py`, `Verdict`, `analysis/restoration.py`, `config.py`, `HarvesterApp`, `orchestrator.py`, `FfmpegService`, `acoustid.py`, `CoverArtService`, `SlskdService`, `.__init__`, `ValidationError`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `ValidationError` (e.g. with `PipelineOrchestrator` and `_excerpt_window()`) actually correct?**
  _`ValidationError` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `CanonicalMetadata` (e.g. with `identify_from_fallback()` and `identify_job()`) actually correct?**
  _`CanonicalMetadata` has 27 INFERRED edges - model-reasoned connections that need verification._