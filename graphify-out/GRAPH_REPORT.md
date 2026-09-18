# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- 128 files · ~65,644 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .toml 1, .tcss 1)

## Summary
- 2155 nodes · 4465 edges · 166 communities (93 shown, 73 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 539 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0ad9ac32`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DiskError
- AudioPlayerWidget
- scanner.py
- acoustid.py
- PreviewManager
- Milestone M7 — QA & packaging
- test_orchestrator_m5.py
- analysis/restoration.py
- phase2_hunt.py
- exporter.py
- HarvesterApp
- logging_setup.py
- JobTable
- AudioVisualizer
- TrackJob
- ModelManager
- test_playlist.py
- config.py
- slskd.py
- SourceKind
- Harvester (Hybrid Music Harvest & Curation Engine)
- ValidationError
- test_orchestrator_m2.py
- BatchReport
- CircuitBreaker
- PipelineOrchestrator
- FfmpegService
- FakeSlskd
- AppConfig
- report.py
- Pipeline orchestrator
- pathlib
- environment.py
- ComposeResult
- player.py
- musicbrainz.py
- LogConsole
- Phase 1 — Input Analysis
- yt-dlp
- titleclean.py
- test_spectral.py
- ytdlp.py
- EnhancementExporter
- test_orchestrator.py
- Spectral fixture connectivity gap
- models.py
- HybridCoOpProvider
- errors.py
- State
- Textual TUI
- ConservativeDSPProvider
- CoverArtService
- app.py
- Minimal Implementation Ladder
- NVSRProvider
- .__init__
- phase2_hunt
- Path
- TrackJob
- asyncio
- test_enhancement_dsp.py
- __main__.py
- Mode B — Local Batch Audit
- FakeSlskdOffline
- Phase 5 — Polish and Sync
- persist_first_run_acceptance
- Graphify Knowledge Graph
- FakeAcoustid
- .submit_batch
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- FakeTagger
- .submit_playlist
- FlashSRProvider
- FakeYtdlp
- FakeCover
- CI Workflow
- Changed
- ._load_selected_into_workbench_and_player
- Any
- Pressed
- .__init__
- phase1_analyze
- os
- P2P candidate scoring
- analysis/enhancement/__init__.py
- phase1_analyze.py
- yt-dlp metadata probe
- BatchConfirmScreen
- load_config
- TrackJob
- dataclasses
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- Widget
- PlaylistConfirmScreen
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- orchestrator.py
- OmniRip
- pytest
- .wait_for_idle
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
- ConfigError
- harvester/__init__.py
- services/__init__.py
- ui/__init__.py
- util/__init__.py
- App
- WorkbenchWidget
- ComposeResult
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
- harvester_pipeline
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_ffmpeg
- harvester_ui_themes
- ndarray
- Path
- harvester
- PreviewManager
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- StrEnum
- Exception
- Queue
- Any
- Text

## God Nodes (most connected - your core abstractions)
1. `ValidationError` - 53 edges
2. `PipelineOrchestrator` - 53 edges
3. `HarvesterApp` - 50 edges
4. `TrackJob` - 48 edges
5. `CanonicalMetadata` - 44 edges
6. `AppConfig` - 42 edges
7. `load_config()` - 38 edges
8. `AudioPlayerWidget` - 33 edges
9. `AudioVisualizer` - 33 edges
10. `Mode` - 31 edges

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

## Communities (166 total, 73 thin omitted)

### Community 0 - "DiskError"
Cohesion: 0.20
Nodes (21): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+13 more)

### Community 1 - "AudioPlayerWidget"
Cohesion: 0.06
Nodes (28): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+20 more)

### Community 2 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 3 - "acoustid.py"
Cohesion: 0.07
Nodes (29): Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+21 more)

### Community 4 - "PreviewManager"
Cohesion: 0.06
Nodes (32): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+24 more)

### Community 5 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 6 - "test_orchestrator_m5.py"
Cohesion: 0.26
Nodes (15): _build(), _mixed_library(), asyncio, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison., test_batch_audit_mixed_directory_ac5(), test_batch_failure_writes_failed_report_row() (+7 more)

### Community 7 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 8 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 9 - "exporter.py"
Cohesion: 0.13
Nodes (27): harvester_services_enhancement_conservative_provider, logging, numpy, apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray (+19 more)

### Community 10 - "HarvesterApp"
Cohesion: 0.06
Nodes (15): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Toggle visualizer between spectrum analyzer and oscilloscope. (+7 more)

### Community 11 - "logging_setup.py"
Cohesion: 0.08
Nodes (24): logging_handlers, LogRecord, Queue, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+16 more)

### Community 12 - "JobTable"
Cohesion: 0.11
Nodes (15): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network). (+7 more)

### Community 13 - "AudioVisualizer"
Cohesion: 0.06
Nodes (23): AudioVisualizer, Path, Text, Widget, Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses downsampled hop… (+15 more)

### Community 14 - "TrackJob"
Cohesion: 0.05
Nodes (69): difflib, mutagen_flac, mutagen_id3, soundfile, CanonicalMetadata, Mode, Mutable job aggregate owned by the orchestrator., TrackJob (+61 more)

### Community 15 - "ModelManager"
Cohesion: 0.12
Nodes (17): Path, ModelManager, Path, Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally., Calculate and verify SHA-256 checksum of a file., Download a model checkpoint to the local cache directory. Args: model_name:… (+9 more)

### Community 16 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 17 - "config.py"
Cohesion: 0.19
Nodes (16): AppPaths, copy, AcoustidConfig, BatchConfig, _build_config(), FfmpegConfig, GeneralConfig, Validated TOML configuration with file, environment, and CLI precedence. (+8 more)

### Community 18 - "slskd.py"
Cohesion: 0.05
Nodes (55): collections_abc, random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8). (+47 more)

### Community 19 - "SourceKind"
Cohesion: 0.06
Nodes (52): Pure analysis logic: query cleaning and P2P candidate ranking., analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+44 more)

### Community 20 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 21 - "ValidationError"
Cohesion: 0.20
Nodes (12): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+4 more)

### Community 22 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 23 - "BatchReport"
Cohesion: 0.21
Nodes (11): BatchReport, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Path, Batch report tests: schema, incremental appends, row builders (FR-14)., test_append_writes_all_schema_fields(), test_appends_are_incremental_and_order_preserved() (+3 more)

### Community 24 - "CircuitBreaker"
Cohesion: 0.05
Nodes (37): enum, assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source. (+29 more)

### Community 25 - "PipelineOrchestrator"
Cohesion: 0.18
Nodes (7): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 26 - "FfmpegService"
Cohesion: 0.19
Nodes (11): SourceKind, FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines., Build the deterministic Phase 5 transcode arguments. (+3 more)

### Community 28 - "AppConfig"
Cohesion: 0.24
Nodes (23): CanonicalMetadata, harvester_util_fsatomic, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac() (+15 more)

### Community 29 - "report.py"
Cohesion: 0.19
Nodes (12): datetime, json, batch_report_name(), job_row(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3). (+4 more)

### Community 30 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 31 - "pathlib"
Cohesion: 0.08
Nodes (23): harvester_analysis_enhancement_presets, harvester_ui_screens_curation_workbench, hashlib, pathlib, platform, platformdirs, Platform-aware runtime directories., Headless preview generation and system audio player dispatch for OmniRip M10. (+15 more)

### Community 32 - "environment.py"
Cohesion: 0.15
Nodes (13): shlex, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+5 more)

### Community 33 - "ComposeResult"
Cohesion: 0.09
Nodes (12): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application. (+4 more)

### Community 34 - "player.py"
Cohesion: 0.11
Nodes (20): harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_ui_player, harvester_ui_visualizer, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive… (+12 more)

### Community 35 - "musicbrainz.py"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 36 - "LogConsole"
Cohesion: 0.12
Nodes (15): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+7 more)

### Community 37 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 38 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 39 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 40 - "test_spectral.py"
Cohesion: 0.28
Nodes (19): parametrize, _content(), fixture_fraud_128(), fixture_fraud_192(), fixture_honest_full(), fixture_honest_rolloff(), fixture_near_silent(), fixture_short() (+11 more)

### Community 41 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

### Community 42 - "EnhancementExporter"
Cohesion: 0.16
Nodes (15): EnhancementExporter, EnhancementPreset, ndarray, Path, Render enhanced audio array according to preset parameters: 1. Progressive mono…, Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+7 more)

### Community 43 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 44 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 45 - "models.py"
Cohesion: 0.12
Nodes (24): Apply, EventKind, JobEvent, Domain models shared by the pipeline, services, and UI., coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08… (+16 more)

### Community 46 - "HybridCoOpProvider"
Cohesion: 0.14
Nodes (9): Protocol, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider., Whether the provider's dependencies and weights are ready for inference., Generate the high-frequency residual signal strictly above cutoff_hz. Args:…, HybridCoOpProvider (+1 more)

### Community 47 - "errors.py"
Cohesion: 0.30
Nodes (10): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+2 more)

### Community 48 - "State"
Cohesion: 0.14
Nodes (18): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), StrEnum, The single source of truth for legal job-state transitions. ``State`` lives… (+10 more)

### Community 49 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 50 - "ConservativeDSPProvider"
Cohesion: 0.11
Nodes (14): harvester_services_enhancement, ConservativeDSPProvider, ndarray, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, Generate high-frequency residual harmonics based on the top octave of the…, Tests for M10-C Enhancement Providers., Verify ConservativeDSPProvider is available and generates residual above cutoff., Verify NVSRProvider gracefully generates high-pass residual when model weights… (+6 more)

### Community 51 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 52 - "app.py"
Cohesion: 0.12
Nodes (19): harvester_pipeline_orchestrator, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_util_logging_setup, Textual UI: throttled bridge, level-filtered console, and M6 hardening…, cycle_theme(), App (+11 more)

### Community 53 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 54 - "NVSRProvider"
Cohesion: 0.21
Nodes (7): Any, NVSRProvider, ndarray, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if torch is installed and weights are cached., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 55 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 56 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 59 - "asyncio"
Cohesion: 0.33
Nodes (5): asyncio, Any, Tracked subprocess lifecycle helpers for cancellation-safe services., Return portable process-group options for subprocess creation., subprocess_options()

### Community 60 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 61 - "__main__.py"
Cohesion: 0.21
Nodes (11): argparse, ArgumentParser, harvester, harvester_util_errors, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys (+3 more)

### Community 62 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 64 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 65 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 66 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 68 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 69 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 70 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 71 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 73 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 74 - "FlashSRProvider"
Cohesion: 0.24
Nodes (5): FlashSRProvider, ndarray, Path, FlashSR single-step distilled diffusion air-band generator. Generates ultra-…, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 77 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 79 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 82 - ".__init__"
Cohesion: 0.14
Nodes (9): AcoustidService, CoverArtService, DownloadProgress, EventKind, JobEvent, MetadataTagger, SlskdService, SubprocessRegistry (+1 more)

### Community 83 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 84 - "os"
Cohesion: 0.32
Nodes (7): os, atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename.

### Community 85 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 86 - "analysis/enhancement/__init__.py"
Cohesion: 0.29
Nodes (6): importlib_util, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, Verify check_enhancement_available returns boolean and descriptive string., test_check_enhancement_available_returns_status()

### Community 87 - "phase1_analyze.py"
Cohesion: 0.14
Nodes (18): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+10 more)

### Community 88 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 89 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 90 - "load_config"
Cohesion: 0.31
Nodes (10): _deep_merge(), load_config(), _load_toml(), Path, Load config with precedence CLI > environment > TOML > defaults., Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected() (+2 more)

### Community 92 - "dataclasses"
Cohesion: 0.40
Nodes (4): dataclasses, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

### Community 93 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 94 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 95 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 96 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 99 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 100 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 101 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 102 - "orchestrator.py"
Cohesion: 0.12
Nodes (16): collections, harvester_batch_report, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral, harvester_services_acoustid (+8 more)

### Community 103 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 104 - "pytest"
Cohesion: 0.33
Nodes (5): pytest, asyncio, test_registry_terminates_process_by_job_prefix(), asyncio, test_m0_shell_mounts_without_startup_checks()

### Community 119 - "ConfigError"
Cohesion: 0.27
Nodes (10): _apply_environment(), _bool(), section(), _float(), _int(), Any, Validate cross-field invariants and return this config for fluent use., Return diagnostic configuration without exposing secret values. (+2 more)

### Community 131 - "WorkbenchWidget"
Cohesion: 0.09
Nodes (20): Changed, Pressed, setter, ComposeResult, Path, Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, In-page audio enhancement and auditioning workbench panel. Supports real-time… (+12 more)

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 827 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HarvesterApp` connect `HarvesterApp` to `environment.py`, `ComposeResult`, `AudioPlayerWidget`, `WorkbenchWidget`, `PreviewManager`, `pytest`, `JobTable`, `._load_selected_into_workbench_and_player`, `app.py`, `.__init__`, `BatchConfirmScreen`, `__main__.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `environment.py`, `persist_first_run_acceptance`, `scanner.py`, `acoustid.py`, `FfmpegService`, `musicbrainz.py`, `orchestrator.py`, `analysis/restoration.py`, `ytdlp.py`, `config.py`, `.__init__`, `SourceKind`, `CoverArtService`, `slskd.py`, `ValidationError`, `ConfigError`, `PipelineOrchestrator`, `load_config`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `AudioVisualizer` connect `AudioVisualizer` to `AudioPlayerWidget`, `player.py`, `WorkbenchWidget`, `PreviewManager`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `CurationWorkbenchModal`) actually correct?**
  _`HarvesterApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 38 INFERRED edges - model-reasoned connections that need verification._