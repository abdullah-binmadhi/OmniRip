# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2158 nodes · 4467 edges · 168 communities (101 shown, 67 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 540 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `90de7031`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- scanner.py
- AudioPlayerWidget
- test_orchestrator_m5.py
- PreviewManager
- acoustid.py
- AudioVisualizer
- Milestone M7 — QA & packaging
- QualityEvidence
- analysis/restoration.py
- HarvesterApp
- environment.py
- models.py
- logging_setup.py
- test_spectral.py
- test_orchestrator_m4.py
- test_playlist.py
- numpy
- config.py
- TrackJob
- WorkbenchWidget
- Harvester (Hybrid Music Harvest & Curation Engine)
- EnhancementExporter
- CanonicalMetadata
- JobEvent
- AppConfig
- test_orchestrator_m2.py
- ValidationError
- test_orchestrator_m3.py
- test_model_manager.py
- Pipeline orchestrator
- LogConsole
- DiskError
- phase1_analyze.py
- ComposeResult
- phase2_hunt.py
- FfmpegService
- Phase 1 — Input Analysis
- player.py
- yt-dlp
- titleclean.py
- test_orchestrator.py
- Spectral fixture connectivity gap
- PipelineOrchestrator
- ConservativeDSPProvider
- scoring.py
- slskd.py
- orchestrator.py
- YtdlpService
- HybridCoOpProvider
- SlskdService
- test_ui_pilot.py
- ytdlp.py
- JobTable
- Textual TUI
- ModelManager
- CircuitBreaker
- test_slskd.py
- StatusBar
- SourceKind
- textual_app
- .__init__
- Minimal Implementation Ladder
- phase2_hunt
- pathlib
- errors.py
- TrackJob
- test_enhancement_dsp.py
- __main__.py
- collections_abc
- Mode B — Local Batch Audit
- NVSRProvider
- Phase 5 — Polish and Sync
- app.py
- SubprocessRegistry
- persist_first_run_acceptance
- Graphify Knowledge Graph
- .submit_batch
- test_ui_workbench.py
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- .submit_playlist
- CI Workflow
- .__init__
- ._load_selected_into_workbench_and_player
- Any
- phase1_analyze
- os
- FlashSRProvider
- BatchConfirmScreen
- P2P candidate scoring
- yt-dlp metadata probe
- test_config.py
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
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
- harvester/__init__.py
- services/__init__.py
- .action_seek_forward
- .action_toggle_vis_mode
- ui/__init__.py
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
- Changed
- Pressed
- TrackJob
- Widget
- ComposeResult
- Text

## God Nodes (most connected - your core abstractions)
1. `ValidationError` - 53 edges
2. `PipelineOrchestrator` - 53 edges
3. `HarvesterApp` - 50 edges
4. `TrackJob` - 49 edges
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

## Communities (168 total, 67 thin omitted)

### Community 0 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 1 - "AudioPlayerWidget"
Cohesion: 0.06
Nodes (28): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+20 more)

### Community 2 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (24): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+16 more)

### Community 3 - "PreviewManager"
Cohesion: 0.06
Nodes (34): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+26 more)

### Community 4 - "acoustid.py"
Cohesion: 0.09
Nodes (27): json, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+19 more)

### Community 5 - "AudioVisualizer"
Cohesion: 0.06
Nodes (24): ComposeResult, AudioVisualizer, Path, Text, Widget, Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels. (+16 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "QualityEvidence"
Cohesion: 0.08
Nodes (36): enum, RuntimeError, assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality. (+28 more)

### Community 8 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 9 - "HarvesterApp"
Cohesion: 0.07
Nodes (13): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Seek backward 5 seconds in player. (+5 more)

### Community 10 - "environment.py"
Cohesion: 0.08
Nodes (23): httpx, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+15 more)

### Community 11 - "models.py"
Cohesion: 0.09
Nodes (29): dataclasses, datetime, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., batch_report_name(), BatchReport, job_row() (+21 more)

### Community 12 - "logging_setup.py"
Cohesion: 0.08
Nodes (24): logging_handlers, LogRecord, Queue, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+16 more)

### Community 13 - "test_spectral.py"
Cohesion: 0.14
Nodes (32): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+24 more)

### Community 14 - "test_orchestrator_m4.py"
Cohesion: 0.14
Nodes (18): SpectralResult, _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+10 more)

### Community 15 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 16 - "numpy"
Cohesion: 0.15
Nodes (25): harvester_services_enhancement_conservative_provider, logging, numpy, apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray (+17 more)

### Community 17 - "config.py"
Cohesion: 0.14
Nodes (30): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+22 more)

### Community 18 - "TrackJob"
Cohesion: 0.15
Nodes (29): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 19 - "WorkbenchWidget"
Cohesion: 0.11
Nodes (15): Changed, Pressed, setter, ComposeResult, Path, Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, In-page audio enhancement and auditioning workbench panel. Supports real-time… (+7 more)

### Community 20 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 21 - "EnhancementExporter"
Cohesion: 0.10
Nodes (24): harvester_analysis_enhancement_presets, harvester_services_enhancement_exporter, EnhancementExporter, EnhancementPreset, ndarray, Path, Render enhanced audio array according to preset parameters: 1. Progressive mono…, Decode input file, render enhanced audio, write MP3 derivative, and attach ID3… (+16 more)

### Community 22 - "CanonicalMetadata"
Cohesion: 0.12
Nodes (21): mutagen_flac, mutagen_id3, soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path (+13 more)

### Community 23 - "JobEvent"
Cohesion: 0.14
Nodes (22): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+14 more)

### Community 24 - "AppConfig"
Cohesion: 0.17
Nodes (26): CanonicalMetadata, harvester_services_tagging, harvester_util_fsatomic, AppConfig, Validate cross-field invariants and return this config for fluent use., Return diagnostic configuration without exposing secret values., _batch_target_path(), _choose_output_path() (+18 more)

### Community 25 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 26 - "ValidationError"
Cohesion: 0.14
Nodes (19): Pure analysis logic: query cleaning and P2P candidate ranking., Verdict, excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2., run_spectral_check() (+11 more)

### Community 27 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 28 - "test_model_manager.py"
Cohesion: 0.10
Nodes (19): hashlib, importlib_util, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Verify that a dummy class adhering to EnhancementProvider satisfies isinstance… (+11 more)

### Community 29 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 30 - "LogConsole"
Cohesion: 0.12
Nodes (15): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+7 more)

### Community 31 - "DiskError"
Cohesion: 0.20
Nodes (21): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+13 more)

### Community 32 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+11 more)

### Community 33 - "ComposeResult"
Cohesion: 0.10
Nodes (10): FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17). (+2 more)

### Community 34 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 35 - "FfmpegService"
Cohesion: 0.19
Nodes (11): SourceKind, FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines., Build the deterministic Phase 5 transcode arguments. (+3 more)

### Community 36 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 37 - "player.py"
Cohesion: 0.14
Nodes (16): asyncio, harvester_services_enhancement_preview, harvester_ui_visualizer, math, rich_style, rich_text, Cover Art Archive client with a release-MBID disk cache., In-app Audio Player widget with real-time spectrum, oscilloscope, interactive… (+8 more)

### Community 38 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 39 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 40 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 41 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 42 - "PipelineOrchestrator"
Cohesion: 0.18
Nodes (7): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 43 - "ConservativeDSPProvider"
Cohesion: 0.11
Nodes (14): harvester_services_enhancement, ConservativeDSPProvider, ndarray, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, Generate high-frequency residual harmonics based on the top octave of the…, Tests for M10-C Enhancement Providers., Verify ConservativeDSPProvider is available and generates residual above cutoff., Verify NVSRProvider gracefully generates high-pass residual when model weights… (+6 more)

### Community 44 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 45 - "slskd.py"
Cohesion: 0.20
Nodes (11): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+3 more)

### Community 46 - "orchestrator.py"
Cohesion: 0.12
Nodes (16): collections, harvester_batch_report, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral, harvester_services_acoustid (+8 more)

### Community 47 - "YtdlpService"
Cohesion: 0.20
Nodes (9): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+1 more)

### Community 48 - "HybridCoOpProvider"
Cohesion: 0.12
Nodes (11): Protocol, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider., Whether the provider's dependencies and weights are ready for inference., Generate the high-frequency residual signal strictly above cutoff_hz. Args:…, HybridCoOpProvider (+3 more)

### Community 49 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 50 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 51 - "ytdlp.py"
Cohesion: 0.20
Nodes (13): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, Any (+5 more)

### Community 52 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 53 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 54 - "ModelManager"
Cohesion: 0.17
Nodes (9): Path, Path, ModelManager, Path, Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally., Calculate and verify SHA-256 checksum of a file. (+1 more)

### Community 55 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 56 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 57 - "StatusBar"
Cohesion: 0.13
Nodes (7): DependencyStatus, EnvironmentStatus, FatalSetupScreen, Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 58 - "SourceKind"
Cohesion: 0.20
Nodes (13): StrEnum, SourceKind, _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix() (+5 more)

### Community 59 - "textual_app"
Cohesion: 0.19
Nodes (12): cycle_theme(), App, Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+4 more)

### Community 60 - ".__init__"
Cohesion: 0.14
Nodes (9): AcoustidService, CoverArtService, DownloadProgress, EventKind, JobEvent, MetadataTagger, SlskdService, SubprocessRegistry (+1 more)

### Community 61 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 62 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 63 - "pathlib"
Cohesion: 0.18
Nodes (10): pathlib, platform, platformdirs, Platform-aware runtime directories., Headless preview generation and system audio player dispatch for OmniRip M10., ModelSpec, Model management and checkpoint downloading service for OmniRip M10., Specification of an audio enhancement model checkpoint. (+2 more)

### Community 64 - "errors.py"
Cohesion: 0.29
Nodes (12): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+4 more)

### Community 66 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 67 - "__main__.py"
Cohesion: 0.21
Nodes (11): argparse, ArgumentParser, harvester, harvester_util_errors, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys (+3 more)

### Community 68 - "collections_abc"
Cohesion: 0.21
Nodes (10): collections_abc, random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio (+2 more)

### Community 69 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 70 - "NVSRProvider"
Cohesion: 0.21
Nodes (7): Any, NVSRProvider, ndarray, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if torch is installed and weights are cached., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 71 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 72 - "app.py"
Cohesion: 0.18
Nodes (10): harvester_pipeline_orchestrator, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_util_logging_setup, Textual UI: throttled bridge, level-filtered console, and M6 hardening…, Textual Curation Workbench Modal Screen for OmniRip M10., textual_containers (+2 more)

### Community 73 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 74 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 75 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 76 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 77 - "test_ui_workbench.py"
Cohesion: 0.27
Nodes (8): ComposeResult, harvester_ui_player, harvester_ui_workbench, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, test_player_interactive_scrubber_and_seeking(), test_workbench_stream_switching_and_metrics(), WorkbenchTestApp

### Community 78 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 79 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 80 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 81 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (7): Asynchronous pipeline stages., _job(), Path, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 82 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 83 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 84 - ".__init__"
Cohesion: 0.25
Nodes (3): AppConfig, PlaylistConfirmScreen, Show entry count and cap before expanding a playlist (docs/08 §2, D10).

### Community 85 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 87 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 88 - "os"
Cohesion: 0.32
Nodes (7): os, atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename.

### Community 89 - "FlashSRProvider"
Cohesion: 0.32
Nodes (4): FlashSRProvider, ndarray, FlashSR single-step distilled diffusion air-band generator. Generates ultra-…, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 90 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 91 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 92 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 93 - "test_config.py"
Cohesion: 0.53
Nodes (5): Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected(), test_precedence_is_cli_over_environment_over_file(), test_secret_values_are_never_in_public_config()

### Community 94 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 95 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 96 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 97 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 98 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 99 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 100 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 101 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 102 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 828 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **67 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `TrackJob`, `test_orchestrator_m5.py`, `FfmpegService`, `.wait_for_idle`, `test_orchestrator.py`, `HarvesterApp`, `.submit_batch`, `orchestrator.py`, `test_orchestrator_m4.py`, `test_playlist.py`, `.submit_playlist`, `AppConfig`, `test_orchestrator_m2.py`, `test_orchestrator_m3.py`, `.__init__`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `ComposeResult`, `AudioPlayerWidget`, `__main__.py`, `PreviewManager`, `app.py`, `config.py`, `test_ui_pilot.py`, `WorkbenchWidget`, `.__init__`, `.action_seek_forward`, `._load_selected_into_workbench_and_player`, `.action_toggle_vis_mode`, `BatchConfirmScreen`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `AudioPlayerWidget` connect `AudioPlayerWidget` to `ComposeResult`, `AudioVisualizer`, `player.py`, `app.py`, `HarvesterApp`, `test_ui_workbench.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `CurationWorkbenchModal`) actually correct?**
  _`HarvesterApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 39 INFERRED edges - model-reasoned connections that need verification._