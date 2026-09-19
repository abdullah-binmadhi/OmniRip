# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2285 nodes · 4507 edges · 207 communities (106 shown, 101 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 476 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `22590c3c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- config.py
- AudioPlayerWidget
- acoustid.py
- scanner.py
- AudioVisualizer
- Milestone M7 — QA & packaging
- numpy
- HarvesterApp
- pytest
- PreviewManager
- WorkbenchWidget
- exporter.py
- FlashSRProvider
- AppConfig
- test_spectral.py
- test_playlist.py
- ensure_2d_audio
- app.py
- test_orchestrator_m4.py
- TrackJob
- EnhancementExporter
- ValidationError
- test_orchestrator_m2.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- Phase 1 — Input Analysis
- State
- ComposeResult
- orchestrator.py
- phase1_analyze.py
- .__init__
- phase2_hunt.py
- test_phase4_spectral.py
- environment.py
- models.py
- PipelineOrchestrator
- Phase 5 — Polish and Sync
- test_model_manager.py
- titleclean.py
- scoring.py
- test_orchestrator_m3.py
- QualityEvidence
- test_ui_workbench.py
- ytdlp.py
- ModelManager
- EnhancementProvider
- FfmpegService
- FlushPlan
- BatchReport
- test_batch_trash.py
- slskd.py
- test_ui_pilot.py
- TrackJob
- apply_mastering_eq
- JobTable
- test_orchestrator_m5.py
- slskd daemon
- Textual TUI
- SlskdService
- CircuitBreaker
- yt-dlp
- NVSRProvider
- Minimal Implementation Ladder
- Pipeline orchestrator
- AppPaths
- CanonicalMetadata
- test_orchestrator.py
- player.py
- Mode B — Local Batch Audit
- logconsole.py
- test_phase5_polish.py
- .__init__
- logging_setup.py
- UiBridge
- Spectral fixture connectivity gap
- pathlib
- .build_transcode_args
- tagging.py
- retry.py
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- SecretMaskingFilter
- .submit_batch
- CI Workflow
- LogConsole
- ._load_selected_into_workbench_and_player
- ._update_eq_ui
- dataclasses
- phase1_analyze
- report.py
- BatchConfirmScreen
- test_export_progress_callback_granularity
- Path
- phase2_hunt
- State machine
- P2P candidate scoring
- BatchScan
- Any
- .submit_playlist
- FakeSlskdOffline
- NFR-1 — Strict async
- phase3_identify
- phase5_polish
- phase4_spectral
- Five-phase pipeline specification
- FakeAcoustid
- FakeSlskdOffline
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- FakeCover
- FakeSlskd
- FakeTagger
- FakeSlskd
- FakeTagger
- FakeYtdlp
- .wait_for_idle
- ._read_stream
- FakeCover
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
- analysis/__init__.py
- batch/__init__.py
- .validate
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- ui/__init__.py
- update_progress
- .__init__
- util/__init__.py
- Any
- AppConfig
- BatchScan
- CanonicalMetadata
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
- FlushPlan
- harvester_batch_report
- harvester_batch_scanner
- harvester_batch_trash
- harvester_pipeline_orchestrator
- harvester_pipeline_phase4_spectral
- harvester_pipeline_phase5_polish
- harvester_services_enhancement_conservative_provider
- harvester_services_enhancement_flashsr_provider
- harvester_services_enhancement_hybrid_provider
- harvester_services_enhancement_nvsr_provider
- harvester_ui_bridge
- harvester_ui_logconsole
- harvester_ui_workbench
- harvester_util_fsatomic
- JobEvent
- ndarray
- Path
- harvester
- PreviewManager
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- StrEnum
- Exception
- SlskdService
- EnhancementPreset
- AppConfig
- StrEnum
- AppConfig
- App
- Changed
- ComposeResult
- Pressed
- TrackJob
- Widget
- SubprocessRegistry
- asyncio
- Text

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 56 edges
2. `HarvesterApp` - 54 edges
3. `AppConfig` - 45 edges
4. `ValidationError` - 44 edges
5. `load_config()` - 41 edges
6. `AudioPlayerWidget` - 40 edges
7. `WorkbenchWidget` - 40 edges
8. `AudioVisualizer` - 36 edges
9. `CanonicalMetadata` - 33 edges
10. `EnhancementExporter` - 30 edges

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

## Communities (207 total, 101 thin omitted)

### Community 0 - "config.py"
Cohesion: 0.06
Nodes (56): AppPaths, argparse, ArgumentParser, copy, harvester, AcoustidConfig, _apply_environment(), BatchConfig (+48 more)

### Community 1 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 2 - "acoustid.py"
Cohesion: 0.07
Nodes (29): Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+21 more)

### Community 3 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 4 - "AudioVisualizer"
Cohesion: 0.06
Nodes (27): ComposeResult, AudioVisualizer, Path, Text, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc). (+19 more)

### Community 5 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 6 - "numpy"
Cohesion: 0.09
Nodes (36): numpy, _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive() (+28 more)

### Community 7 - "HarvesterApp"
Cohesion: 0.06
Nodes (15): HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file., Cycle to next dynamic color theme., Toggle visualizer between spectrum analyzer and oscilloscope. (+7 more)

### Community 8 - "pytest"
Cohesion: 0.09
Nodes (25): httpx, pytest, CoverArtService, AsyncClient, Path, Cover Art Archive client with a release-MBID disk cache., Best-effort front-cover fetching; failures never fail a job., _config() (+17 more)

### Community 9 - "PreviewManager"
Cohesion: 0.07
Nodes (30): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+22 more)

### Community 10 - "WorkbenchWidget"
Cohesion: 0.10
Nodes (20): Changed, Pressed, setter, Path, Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Download or verify local caching of all AI neural model weights., In-page audio enhancement and auditioning workbench panel. Supports real-time…, Load a track job into the workbench, resolve streams, and pre-render ENH. (+12 more)

### Community 11 - "exporter.py"
Cohesion: 0.08
Nodes (29): collections_abc, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_presets, harvester_analysis_enhancement_provider, harvester_services_model_manager, harvester_ui_screens_curation_workbench, logging, mutagen (+21 more)

### Community 12 - "FlashSRProvider"
Cohesion: 0.07
Nodes (24): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, Any, ModelManager, ndarray (+16 more)

### Community 13 - "AppConfig"
Cohesion: 0.15
Nodes (34): harvester_services_restoration, os, Restore a trashed original to its original location (FR-13 rollback step)., rollback(), AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses() (+26 more)

### Community 14 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 15 - "test_playlist.py"
Cohesion: 0.10
Nodes (16): harvester_util_circuit, _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+8 more)

### Community 16 - "ensure_2d_audio"
Cohesion: 0.09
Nodes (31): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+23 more)

### Community 17 - "app.py"
Cohesion: 0.09
Nodes (27): App, harvester_analysis_enhancement_eq, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_player, harvester_ui_themes, harvester_ui_visualizer (+19 more)

### Community 18 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 19 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 20 - "EnhancementExporter"
Cohesion: 0.11
Nodes (18): EnhancementPreset, MasteringEQSettings, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB)., Apply a named preset profile., EnhancementExporter (+10 more)

### Community 21 - "ValidationError"
Cohesion: 0.19
Nodes (19): ProgressCallback, ErrorClass, Any, Exception, Path, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+11 more)

### Community 22 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 23 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.11
Nodes (25): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID (+17 more)

### Community 24 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (25): Atomic filesystem helpers, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+17 more)

### Community 25 - "State"
Cohesion: 0.13
Nodes (19): enum, RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives… (+11 more)

### Community 26 - "ComposeResult"
Cohesion: 0.10
Nodes (10): FirstRunNoticeScreen, HelpScreen, PlaylistConfirmScreen, PurgeConfirmScreen, ComposeResult, Pressed, Non-blocking help overlay for the application., Show entry count and cap before expanding a playlist (docs/08 §2, D10). (+2 more)

### Community 27 - "orchestrator.py"
Cohesion: 0.12
Nodes (19): harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_acoustid, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors, harvester_util_retry (+11 more)

### Community 28 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+11 more)

### Community 29 - ".__init__"
Cohesion: 0.10
Nodes (9): DependencyStatus, EnvironmentStatus, FatalSetupScreen, QuitConfirmScreen, Confirm quit while jobs are still active (docs/08 §5, FR-17)., Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar (+1 more)

### Community 30 - "phase2_hunt.py"
Cohesion: 0.13
Nodes (20): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number(), prepare_fallback() (+12 more)

### Community 31 - "test_phase4_spectral.py"
Cohesion: 0.16
Nodes (14): SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., run_spectral_check(), _config(), _FakeFailureFfmpeg, _FakeFfmpeg, _make_job() (+6 more)

### Community 32 - "environment.py"
Cohesion: 0.16
Nodes (12): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable. (+4 more)

### Community 33 - "models.py"
Cohesion: 0.15
Nodes (17): datetime, EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., Return an aware UTC timestamp suitable for persisted events. (+9 more)

### Community 34 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (8): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 35 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 36 - "test_model_manager.py"
Cohesion: 0.12
Nodes (16): harvester_analysis_enhancement, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Verify that a dummy class adhering to EnhancementProvider satisfies isinstance…, Test model path resolution and caching checks in ModelManager., Verify SHA-256 calculation and verification., Test downloading a model via mocked huggingface_hub., Test that requesting an unknown model raises KeyError. (+8 more)

### Community 37 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 38 - "scoring.py"
Cohesion: 0.19
Nodes (18): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+10 more)

### Community 39 - "test_orchestrator_m3.py"
Cohesion: 0.18
Nodes (9): soundfile, _build(), FakeAcoustid, FakeFfmpeg, FakeYtdlp, asyncio, Path, test_ground_truth_metadata_reaches_flac_output() (+1 more)

### Community 40 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 41 - "test_ui_workbench.py"
Cohesion: 0.17
Nodes (18): ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer. (+10 more)

### Community 42 - "ytdlp.py"
Cohesion: 0.18
Nodes (15): asyncio, DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress (+7 more)

### Community 43 - "ModelManager"
Cohesion: 0.16
Nodes (12): hashlib, ModelManager, ModelSpec, Path, Model management and checkpoint downloading service for OmniRip M10., Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights. (+4 more)

### Community 44 - "EnhancementProvider"
Cohesion: 0.11
Nodes (14): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Enhancement provider protocol and base types for OmniRip M10. (+6 more)

### Community 45 - "FfmpegService"
Cohesion: 0.23
Nodes (9): SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+1 more)

### Community 46 - "FlushPlan"
Cohesion: 0.15
Nodes (14): ErrorInfo, coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7). (+6 more)

### Community 47 - "BatchReport"
Cohesion: 0.16
Nodes (15): BatchReport, job_row(), TrackJob, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4)., Path (+7 more)

### Community 48 - "test_batch_trash.py"
Cohesion: 0.24
Nodes (17): move_to_trash(), purge(), Path, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Delete trash day-directories older than ``retention_days``; return count.…, trash_root_for(), Path (+9 more)

### Community 49 - "slskd.py"
Cohesion: 0.22
Nodes (13): _bool_or_none(), _concrete_paths(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), _pick_download_route(), Any (+5 more)

### Community 50 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 52 - "apply_mastering_eq"
Cohesion: 0.15
Nodes (15): apply_mastering_eq(), ndarray, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Tests for 10-Band Studio Equalizer (Milestone 10-EQ)., Verify that extreme boosts do not exceed ceiling_dbfs., Verify default settings and preset switching., Verify that flat EQ is a transparent near-identity. (+7 more)

### Community 53 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 54 - "test_orchestrator_m5.py"
Cohesion: 0.26
Nodes (15): _build(), _mixed_library(), asyncio, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison., test_batch_audit_mixed_directory_ac5(), test_batch_failure_writes_failed_report_row() (+7 more)

### Community 55 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 56 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 57 - "SlskdService"
Cohesion: 0.24
Nodes (6): P2PCandidate, AsyncClient, Path, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService, ServiceUnavailable

### Community 58 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 59 - "yt-dlp"
Cohesion: 0.14
Nodes (15): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D10 — Playlist cap 50 + confirmation, D3 — Spectral check scope: P2P lossless claims only, FR-1 — Extract metadata without downloading, FR-10 — Provenance-based spectral exemption, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback (+7 more)

### Community 60 - "NVSRProvider"
Cohesion: 0.16
Nodes (9): NVSRProvider, Any, ModelManager, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if neural acceleration is enabled, torch is installed, and weights are… (+1 more)

### Community 61 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 62 - "Pipeline orchestrator"
Cohesion: 0.19
Nodes (14): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+6 more)

### Community 63 - "AppPaths"
Cohesion: 0.19
Nodes (9): AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., Path, test_app_paths_are_isolated_and_created(), Path (+1 more)

### Community 64 - "CanonicalMetadata"
Cohesion: 0.26
Nodes (8): CanonicalMetadata, MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art., Path, test_flac_tagging_writes_vorbis_picture_and_provenance(), test_mp3_tagging_writes_id3v23_provenance_and_art(), _write_flac()

### Community 65 - "test_orchestrator.py"
Cohesion: 0.27
Nodes (7): FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path, test_orchestrator_cancel_marks_job_cancelled(), test_orchestrator_runs_fallback_path_with_fake_services()

### Community 66 - "player.py"
Cohesion: 0.21
Nodes (11): collections, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive…, Real-time Audio Visualizer Widget for OmniRip TUI. Provides multi-mode audio…, textual, textual_message (+3 more)

### Community 67 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 68 - "logconsole.py"
Cohesion: 0.21
Nodes (10): level_passes(), next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., Log console filter tests (docs/08 §5: INFO -> DEBUG -> WARN+ERROR cycling)., test_level_passes_debug_shows_everything(), test_level_passes_info_hides_debug() (+2 more)

### Community 69 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 70 - ".__init__"
Cohesion: 0.17
Nodes (9): AcoustidService, CoverArtService, EventKind, SlskdService, JobEvent, MetadataTagger, Queue, SubprocessRegistry (+1 more)

### Community 71 - "logging_setup.py"
Cohesion: 0.21
Nodes (10): logging_handlers, Queue, configure_logging(), ContextDefaultsFilter, _level(), LoggingController, Queue-based logging fan-out with secret redaction., Supply structured fields for logs emitted outside a pipeline job. (+2 more)

### Community 72 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 73 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 74 - "pathlib"
Cohesion: 0.27
Nodes (9): harvester_pipeline, pathlib, _job(), Path, TrackJob, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes() (+1 more)

### Community 75 - ".build_transcode_args"
Cohesion: 0.22
Nodes (7): harvester_services_ffmpeg, Build the deterministic Phase 5 transcode arguments., Path, test_build_mp3_320_arguments(), test_build_mp3_v0_arguments(), test_keep_opus_is_not_an_mp3_transcode(), test_probe_audio_info_cache()

### Community 76 - "tagging.py"
Cohesion: 0.33
Nodes (9): mutagen_flac, mutagen_id3, metadata_from_probe(), Any, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields., _text(), _year() (+1 more)

### Community 77 - "retry.py"
Cohesion: 0.25
Nodes (8): backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds(), test_sleep_backoff_is_async()

### Community 78 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 79 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 80 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 81 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 82 - "SecretMaskingFilter"
Cohesion: 0.22
Nodes (5): LogRecord, CallbackHandler, Replace configured secret values before a record reaches any handler., Small adapter for consumers that want formatted log records., SecretMaskingFilter

### Community 83 - ".submit_batch"
Cohesion: 0.24
Nodes (7): _entry_tags(), BatchScan, Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 84 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 85 - "LogConsole"
Cohesion: 0.25
Nodes (4): RichLog, LogConsole, A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter.

### Community 86 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 87 - "._update_eq_ui"
Cohesion: 0.25
Nodes (4): ComposeResult, Render a 13-line vertical studio fader rail with center 0dB line, calibration…, Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons.

### Community 88 - "dataclasses"
Cohesion: 0.25
Nodes (6): dataclasses, platformdirs, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., Platform-aware runtime directories.

### Community 89 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 90 - "report.py"
Cohesion: 0.29
Nodes (7): json, batch_report_name(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3)., skipped_row()

### Community 91 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 92 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 94 - "phase2_hunt"
Cohesion: 0.29
Nodes (7): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, Concurrent download semaphore

### Community 95 - "State machine"
Cohesion: 0.29
Nodes (7): State machine, Title cleaning analysis, Fallback anti-loop guard, IllegalTransition, Unit test plan, State-machine truth directive, Tests alongside every module

### Community 96 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 97 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 99 - ".submit_playlist"
Cohesion: 0.29
Nodes (4): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73).

### Community 101 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 102 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 103 - "phase5_polish"
Cohesion: 0.40
Nodes (5): Batch report writer, FFmpeg service, phase5_polish, q_polish stage queue, Tagging service

### Community 104 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 105 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 108 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 109 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 110 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 111 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Batch adapter`, `Candidate scoring` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 908 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **101 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HarvesterApp` connect `HarvesterApp` to `config.py`, `environment.py`, `PipelineOrchestrator`, `AudioPlayerWidget`, `UiBridge`, `WorkbenchWidget`, `AppConfig`, `FlushPlan`, `app.py`, `test_ui_pilot.py`, `LogConsole`, `._load_selected_into_workbench_and_player`, `ComposeResult`, `BatchConfirmScreen`, `.__init__`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `config.py`, `acoustid.py`, `scanner.py`, `.validate`, `numpy`, `HarvesterApp`, `pytest`, `app.py`, `ValidationError`, `orchestrator.py`, `.__init__`, `test_phase4_spectral.py`, `environment.py`, `PipelineOrchestrator`, `ytdlp.py`, `FfmpegService`, `slskd.py`, `SlskdService`, `.__init__`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `test_orchestrator.py`, `.submit_playlist`, `.__init__`, `HarvesterApp`, `test_orchestrator_m3.py`, `AppConfig`, `FfmpegService`, `BatchReport`, `test_playlist.py`, `app.py`, `test_orchestrator_m4.py`, `TrackJob`, `.submit_batch`, `.wait_for_idle`, `test_orchestrator_m2.py`, `test_orchestrator_m5.py`, `orchestrator.py`, `phase2_hunt.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `HarvesterApp` (e.g. with `AppConfig` and `PipelineOrchestrator`) actually correct?**
  _`HarvesterApp` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AppConfig` (e.g. with `scan_directory()` and `PipelineOrchestrator`) actually correct?**
  _`AppConfig` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._