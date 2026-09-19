# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2187 nodes · 4490 edges · 168 communities (99 shown, 69 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 558 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `836270c8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- config.py
- AudioPlayerWidget
- scanner.py
- test_orchestrator_m5.py
- AudioVisualizer
- HarvesterApp
- WorkbenchWidget
- Milestone M7 — QA & packaging
- PreviewManager
- QualityEvidence
- analysis/restoration.py
- ensure_2d_audio
- JobEvent
- ModelManager
- EnhancementExporter
- logging_setup.py
- orchestrator.py
- FlashSRProvider
- pathlib
- TrackJob
- test_spectral.py
- test_orchestrator_m4.py
- test_playlist.py
- ValidationError
- test_orchestrator_m2.py
- test_orchestrator_m3.py
- AppConfig
- yt-dlp
- player.py
- FfmpegService
- PipelineOrchestrator
- Pipeline orchestrator
- test_batch_trash.py
- SourceKind
- ComposeResult
- models.py
- AcoustidService
- app.py
- Phase 1 — Input Analysis
- environment.py
- Phase 5 — Polish and Sync
- Harvester (Hybrid Music Harvest & Curation Engine)
- TrackJob
- test_batch_swap.py
- titleclean.py
- LogConsole
- scoring.py
- slskd.py
- acoustid.py
- SlskdService
- phase1_analyze.py
- test_ui_pilot.py
- ytdlp.py
- EnhancementProvider
- JobTable
- Textual TUI
- CircuitBreaker
- test_slskd.py
- tagging.py
- textual_app
- Minimal Implementation Ladder
- StatusBar
- phase2_hunt
- collections_abc
- Mode B — Local Batch Audit
- CanonicalMetadata
- test_phase5_polish.py
- SubprocessRegistry
- .submit_batch
- Spectral fixture connectivity gap
- test_ui_workbench.py
- musicbrainz.py
- CoverArtService
- test_acoustid.py
- Graphify Knowledge Graph
- .__init__
- FR-7 — Fingerprint before transcode
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- CI Workflow
- ._load_selected_into_workbench_and_player
- .__init__
- phase1_analyze
- phase4_spectral.py
- BatchConfirmScreen
- P2P candidate scoring
- .submit_playlist
- ._run_inference
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- test_analyze_url_rejects_live_streams
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- pytest
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
- batch/__init__.py
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- ui/__init__.py
- .__init__
- util/__init__.py
- App
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
- EnhancementExporter
- harvester_analysis
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_ffmpeg
- harvester_services_model_manager
- harvester_ui_themes
- harvester_ui_workbench
- ndarray
- harvester
- PreviewManager
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- StrEnum
- Exception
- Queue
- EnhancementPreset
- ModelManager
- Any
- ModelManager
- Changed
- ComposeResult
- Path
- Pressed
- TrackJob
- Widget
- Path
- Text

## God Nodes (most connected - your core abstractions)
1. `ValidationError` - 53 edges
2. `PipelineOrchestrator` - 53 edges
3. `HarvesterApp` - 50 edges
4. `TrackJob` - 46 edges
5. `CanonicalMetadata` - 44 edges
6. `AppConfig` - 42 edges
7. `load_config()` - 38 edges
8. `AudioPlayerWidget` - 33 edges
9. `AudioVisualizer` - 33 edges
10. `WorkbenchWidget` - 29 edges

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

## Communities (168 total, 69 thin omitted)

### Community 0 - "config.py"
Cohesion: 0.06
Nodes (54): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+46 more)

### Community 1 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (29): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+21 more)

### Community 2 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 3 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (24): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+16 more)

### Community 4 - "AudioVisualizer"
Cohesion: 0.06
Nodes (24): ComposeResult, AudioVisualizer, Path, Text, Widget, Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels. (+16 more)

### Community 5 - "HarvesterApp"
Cohesion: 0.06
Nodes (15): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Toggle visualizer between spectrum analyzer and oscilloscope. (+7 more)

### Community 6 - "WorkbenchWidget"
Cohesion: 0.08
Nodes (25): Changed, harvester_batch_report, Path, Pressed, setter, BatchReport, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record). (+17 more)

### Community 7 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 8 - "PreviewManager"
Cohesion: 0.06
Nodes (32): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+24 more)

### Community 9 - "QualityEvidence"
Cohesion: 0.08
Nodes (35): enum, RuntimeError, assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality. (+27 more)

### Community 10 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 11 - "ensure_2d_audio"
Cohesion: 0.09
Nodes (34): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+26 more)

### Community 12 - "JobEvent"
Cohesion: 0.09
Nodes (24): Apply, ErrorInfo, EventKind, JobEvent, Any, coalesce_events(), FlushPlan, Queue (+16 more)

### Community 13 - "ModelManager"
Cohesion: 0.08
Nodes (27): harvester_analysis_enhancement, hashlib, Path, ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint. (+19 more)

### Community 14 - "EnhancementExporter"
Cohesion: 0.08
Nodes (29): EnhancementPreset, harvester_ui_screens_curation_workbench, mutagen_id3, EnhancementExporter, ndarray, Path, Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers. (+21 more)

### Community 15 - "logging_setup.py"
Cohesion: 0.08
Nodes (24): logging_handlers, LogRecord, Queue, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+16 more)

### Community 16 - "orchestrator.py"
Cohesion: 0.08
Nodes (33): collections, harvester_analysis_scoring, harvester_analysis_titleclean, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral (+25 more)

### Community 17 - "FlashSRProvider"
Cohesion: 0.07
Nodes (22): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, ndarray, Path, FlashSR single-step distilled diffusion air-band generator. Generates ultra-… (+14 more)

### Community 18 - "pathlib"
Cohesion: 0.11
Nodes (23): harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_enhancement_conservative_provider, logging, numpy, pathlib, platform, platformdirs (+15 more)

### Community 19 - "TrackJob"
Cohesion: 0.14
Nodes (30): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+22 more)

### Community 20 - "test_spectral.py"
Cohesion: 0.14
Nodes (32): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+24 more)

### Community 21 - "test_orchestrator_m4.py"
Cohesion: 0.14
Nodes (18): SpectralResult, _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+10 more)

### Community 22 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 23 - "ValidationError"
Cohesion: 0.15
Nodes (21): ProgressCallback, ErrorClass, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable. (+13 more)

### Community 24 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 25 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 26 - "AppConfig"
Cohesion: 0.20
Nodes (23): CanonicalMetadata, harvester_util_fsatomic, AppConfig, Validate cross-field invariants and return this config for fluent use., Return diagnostic configuration without exposing secret values., _batch_target_path(), _choose_output_path(), _mutagen_parses() (+15 more)

### Community 27 - "yt-dlp"
Cohesion: 0.08
Nodes (26): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+18 more)

### Community 28 - "player.py"
Cohesion: 0.11
Nodes (20): harvester_analysis_enhancement_presets, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_ui_visualizer, math, rich_style, rich_text, Log console: level-filtered, capped RichLog (docs/08 §2/§4). (+12 more)

### Community 29 - "FfmpegService"
Cohesion: 0.16
Nodes (14): SourceKind, FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines., Build the deterministic Phase 5 transcode arguments. (+6 more)

### Community 30 - "PipelineOrchestrator"
Cohesion: 0.13
Nodes (8): EventKind, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Wait until every submitted job has reached a terminal state. Queue joins are…, Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 31 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 32 - "test_batch_trash.py"
Cohesion: 0.20
Nodes (21): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+13 more)

### Community 33 - "SourceKind"
Cohesion: 0.18
Nodes (15): StrEnum, SourceKind, Verdict, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., run_spectral_check(), test_source_and_verdict_defaults_are_explicit(), _config(), _FakeFailureFfmpeg (+7 more)

### Community 34 - "ComposeResult"
Cohesion: 0.10
Nodes (10): FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17). (+2 more)

### Community 35 - "models.py"
Cohesion: 0.12
Nodes (19): dataclasses, datetime, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., batch_report_name(), job_row(), Path (+11 more)

### Community 36 - "AcoustidService"
Cohesion: 0.15
Nodes (6): AcoustidService, Fingerprint, AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 37 - "app.py"
Cohesion: 0.12
Nodes (18): argparse, ArgumentParser, harvester, harvester_pipeline_orchestrator, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_util_errors (+10 more)

### Community 38 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 39 - "environment.py"
Cohesion: 0.17
Nodes (12): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable. (+4 more)

### Community 40 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 41 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.14
Nodes (20): Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID, Audio fingerprinting, Decision D3 - Phase 4 applies only to P2P lossless-claiming files, Requirements (docs/01-requirements.md), Architecture (docs/02-architecture.md), Pipeline Phases (docs/03-pipeline.md) (+12 more)

### Community 42 - "TrackJob"
Cohesion: 0.28
Nodes (4): DownloadProgress, Exception, TrackJob, Append the terminal report row for a Mode B job (FR-14: per completed job).

### Community 43 - "test_batch_swap.py"
Cohesion: 0.16
Nodes (17): harvester_pipeline, atomic_replace(), fsync_directory(), fsync_file(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a file's contents to stable storage., fsync a directory fd so renames inside it survive a crash (POSIX only). (+9 more)

### Community 44 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 45 - "LogConsole"
Cohesion: 0.13
Nodes (13): RichLog, level_passes(), LogConsole, next_mode(), Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter. (+5 more)

### Community 46 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 47 - "slskd.py"
Cohesion: 0.20
Nodes (11): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+3 more)

### Community 48 - "acoustid.py"
Cohesion: 0.22
Nodes (16): asyncio, json, os, sqlite3, _earliest_release(), _metadata_from_json(), _metadata_to_json(), _number() (+8 more)

### Community 49 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 50 - "phase1_analyze.py"
Cohesion: 0.17
Nodes (16): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+8 more)

### Community 51 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 52 - "ytdlp.py"
Cohesion: 0.20
Nodes (13): harvester_util_subproc, shlex, shutil, DownloadProgress, Async FFmpeg/ffprobe adapter used by fallback acquisition., _parse_int(), _parse_optional_int(), _parse_percent() (+5 more)

### Community 53 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 54 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 55 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 56 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 57 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 58 - "tagging.py"
Cohesion: 0.23
Nodes (13): mutagen_flac, soundfile, metadata_from_probe(), Any, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields., _text(), _year() (+5 more)

### Community 59 - "textual_app"
Cohesion: 0.19
Nodes (12): cycle_theme(), App, Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+4 more)

### Community 60 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 61 - "StatusBar"
Cohesion: 0.14
Nodes (7): DependencyStatus, EnvironmentStatus, FatalSetupScreen, Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 62 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 63 - "collections_abc"
Cohesion: 0.21
Nodes (10): collections_abc, random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio (+2 more)

### Community 64 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 65 - "CanonicalMetadata"
Cohesion: 0.26
Nodes (6): CanonicalMetadata, MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art., test_canonical_metadata_normalizes_artists_and_serializes(), test_track_job_display_name_prefers_canonical_metadata()

### Community 66 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 67 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 68 - ".submit_batch"
Cohesion: 0.22
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 69 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 70 - "test_ui_workbench.py"
Cohesion: 0.29
Nodes (10): harvester_ui_player, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, test_player_interactive_scrubber_and_seeking(), test_workbench_explicit_download_enhanced_button(), test_workbench_neural_toggle_and_models_button() (+2 more)

### Community 71 - "musicbrainz.py"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 72 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 73 - "test_acoustid.py"
Cohesion: 0.40
Nodes (8): _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network(), test_low_confidence_result_is_rejected(), test_missing_api_key_returns_none_without_network()

### Community 74 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 75 - ".__init__"
Cohesion: 0.22
Nodes (3): AppConfig, PlaylistConfirmScreen, Show entry count and cap before expanding a playlist (docs/08 §2, D10).

### Community 76 - "FR-7 — Fingerprint before transcode"
Cohesion: 0.20
Nodes (10): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+2 more)

### Community 77 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 78 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 79 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 80 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 81 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 82 - ".__init__"
Cohesion: 0.25
Nodes (7): AcoustidService, CoverArtService, JobEvent, MetadataTagger, SlskdService, SubprocessRegistry, YtdlpService

### Community 83 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 84 - "phase4_spectral.py"
Cohesion: 0.29
Nodes (6): Pure analysis logic: query cleaning and P2P candidate ranking., excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only., Normative offset/length selection per docs/04 §2., test_excerpt_window_norms()

### Community 85 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 86 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 87 - ".submit_playlist"
Cohesion: 0.29
Nodes (4): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73).

### Community 88 - "._run_inference"
Cohesion: 0.40
Nodes (3): Any, ndarray, Internal inference wrapper.

### Community 89 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 90 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 91 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 92 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 93 - "test_analyze_url_rejects_live_streams"
Cohesion: 0.40
Nodes (3): asyncio, test_analyze_url_populates_meta_and_query(), test_analyze_url_rejects_live_streams()

### Community 94 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 95 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 96 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 97 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 98 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

## Knowledge Gaps
- **163 isolated node(s):** `harvester`, `Answer`, `Source Nodes`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 845 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **69 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AudioPlayerWidget` connect `AudioPlayerWidget` to `ComposeResult`, `AudioVisualizer`, `HarvesterApp`, `app.py`, `player.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `config.py`, `AudioPlayerWidget`, `ComposeResult`, `app.py`, `WorkbenchWidget`, `PreviewManager`, `.__init__`, `._load_selected_into_workbench_and_player`, `test_ui_pilot.py`, `BatchConfirmScreen`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `AudioVisualizer` connect `AudioVisualizer` to `PreviewManager`, `AudioPlayerWidget`, `player.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `CurationWorkbenchModal`) actually correct?**
  _`HarvesterApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 36 INFERRED edges - model-reasoned connections that need verification._