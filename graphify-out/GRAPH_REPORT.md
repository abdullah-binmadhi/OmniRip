# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- 130 files · ~94,345 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .toml 1, .tcss 1)

## Summary
- 2266 nodes · 4648 edges · 181 communities (97 shown, 84 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 580 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1da04f8e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- config.py
- scanner.py
- acoustid.py
- AudioVisualizer
- HarvesterApp
- test_orchestrator_m5.py
- Milestone M7 — QA & packaging
- WorkbenchWidget
- orchestrator.py
- AudioPlayerWidget
- analysis/restoration.py
- workbench.py
- test_orchestrator_m4.py
- test_playlist.py
- BatchReport
- ValidationError
- TrackJob
- PreviewManager
- models.py
- ModelManager
- JobEvent
- test_orchestrator_m2.py
- MasteringEQSettings
- report.py
- test_orchestrator_m3.py
- FfmpegService
- app.py
- ComposeResult
- .render_audio_buffer
- numpy
- QualityEvidence
- __main__.py
- Phase 1 — Input Analysis
- LogConsole
- ensure_2d_audio
- ytdlp.py
- BatchConfirmScreen
- PipelineOrchestrator
- logging_setup.py
- Phase 5 — Polish and Sync
- Harvester (Hybrid Music Harvest & Curation Engine)
- titleclean.py
- FakeFfmpeg
- FirstRunNoticeScreen
- test_orchestrator.py
- scoring.py
- FakeSlskdOffline
- slskd.py
- InteractiveScrubber
- environment.py
- pathlib
- FakeAcoustid
- SlskdService
- test_spectral.py
- JobTable
- test_ui_workbench.py
- CircuitBreaker
- EnhancementProvider
- SpectralResult
- DependencyStatus
- test_batch_swap.py
- slskd daemon
- Textual TUI
- test_slskd.py
- PlaylistConfirmScreen
- .__init__
- Minimal Implementation Ladder
- ConservativeDSPProvider
- FakeSlskd
- CurationWorkbenchModal
- test_enhancement_dsp.py
- FakeTagger
- ffmpeg.py
- Mode B — Local Batch Audit
- Pipeline orchestrator
- FakeYtdlp
- .generate_residual
- FakeCover
- retry.py
- Spectral fixture connectivity gap
- EnhancementExporter
- Graphify Knowledge Graph
- .action_seek_backward
- Any
- yt-dlp
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- AppConfig
- CI Workflow
- phase5_polish
- ._load_selected_into_workbench_and_player
- Changed
- ConservativeRestorationService
- phase1_analyze
- phase2_hunt
- State machine
- P2P candidate scoring
- .generate_residual
- test_ui_player.py
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- ComposeResult
- .compose
- harvester_services_enhancement_exporter
- split_bands
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
- update_progress
- util/__init__.py
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
- harvester_analysis_enhancement_eq
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_ffmpeg
- harvester_ui_themes
- harvester
- PreviewManager
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- harvester_services_enhancement_flashsr_provider
- StrEnum
- Exception
- Queue
- EnhancementPreset
- harvester_services_enhancement_hybrid_provider
- SubprocessRegistry
- ._submit_current
- harvester_services_enhancement_nvsr_provider
- harvester_ui_player
- harvester_ui_visualizer
- harvester_ui_workbench
- App
- ndarray
- Pressed
- Text
- Path
- Widget

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 53 edges
2. `ValidationError` - 53 edges
3. `HarvesterApp` - 49 edges
4. `TrackJob` - 46 edges
5. `WorkbenchWidget` - 44 edges
6. `CanonicalMetadata` - 44 edges
7. `AudioPlayerWidget` - 42 edges
8. `load_config()` - 40 edges
9. `AppConfig` - 39 edges
10. `AudioVisualizer` - 38 edges

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

## Communities (181 total, 84 thin omitted)

### Community 0 - "config.py"
Cohesion: 0.05
Nodes (60): AppPaths, copy, httpx, AcoustidConfig, AppConfig, _apply_environment(), BatchConfig, _bool() (+52 more)

### Community 1 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 2 - "acoustid.py"
Cohesion: 0.06
Nodes (37): os, Process, pytest, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json() (+29 more)

### Community 3 - "AudioVisualizer"
Cohesion: 0.06
Nodes (27): ComposeResult, AudioVisualizer, Path, Text, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc). (+19 more)

### Community 4 - "HarvesterApp"
Cohesion: 0.07
Nodes (12): FlushPlan, HarvesterApp, wrapped(), Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file., Toggle visualizer between spectrum analyzer and oscilloscope., Seek forward 5 seconds in player. (+4 more)

### Community 5 - "test_orchestrator_m5.py"
Cohesion: 0.30
Nodes (16): _build(), _mixed_library(), asyncio, Path, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison., test_batch_audit_mixed_directory_ac5() (+8 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "WorkbenchWidget"
Cohesion: 0.09
Nodes (22): setter, Changed, Path, Pressed, TrackJob, Widget, Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Download or verify local caching of all AI neural model weights. (+14 more)

### Community 8 - "orchestrator.py"
Cohesion: 0.07
Nodes (36): asyncio, collections, harvester_analysis_scoring, harvester_analysis_titleclean, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify (+28 more)

### Community 9 - "AudioPlayerWidget"
Cohesion: 0.09
Nodes (15): AudioPlayerWidget, Path, Pressed, Dedicated in-app audio player bar featuring playback controls, track metadata,…, Load an audio file into the player and prepare visualizer frames., Instant zero-gap stream switch between original and enhanced audio, preserving…, Toggle playback between playing and paused/stopped., Begin audio playback and animate visualizer. (+7 more)

### Community 10 - "analysis/restoration.py"
Cohesion: 0.12
Nodes (31): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+23 more)

### Community 11 - "workbench.py"
Cohesion: 0.19
Nodes (13): harvester_services_enhancement_preview, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive…, Real-time Audio Visualizer Widget for OmniRip TUI. Provides multi-mode audio…, Integrated In-Page Curation & Audio Enhancement Workbench for OmniRip. Provides…, subprocess (+5 more)

### Community 12 - "test_orchestrator_m4.py"
Cohesion: 0.15
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 13 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 14 - "BatchReport"
Cohesion: 0.18
Nodes (13): harvester_batch_report, Path, BatchReport, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Batch report tests: schema, incremental appends, row builders (FR-14)., test_append_writes_all_schema_fields() (+5 more)

### Community 15 - "ValidationError"
Cohesion: 0.26
Nodes (21): CanonicalMetadata, harvester_util_fsatomic, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac(), _polish_mp3() (+13 more)

### Community 16 - "TrackJob"
Cohesion: 0.05
Nodes (66): difflib, mutagen_flac, mutagen_id3, soundfile, CanonicalMetadata, Mode, Any, Mutable job aggregate owned by the orchestrator. (+58 more)

### Community 17 - "PreviewManager"
Cohesion: 0.12
Nodes (19): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+11 more)

### Community 18 - "models.py"
Cohesion: 0.12
Nodes (22): Pure analysis logic: query cleaning and P2P candidate ranking., StrEnum, Domain models shared by the pipeline, services, and UI., SourceKind, Verdict, excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only. (+14 more)

### Community 19 - "ModelManager"
Cohesion: 0.11
Nodes (21): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+13 more)

### Community 20 - "JobEvent"
Cohesion: 0.14
Nodes (22): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+14 more)

### Community 21 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 22 - "MasteringEQSettings"
Cohesion: 0.10
Nodes (21): apply_mastering_eq(), MasteringEQSettings, ndarray, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+13 more)

### Community 23 - "report.py"
Cohesion: 0.19
Nodes (12): datetime, json, batch_report_name(), job_row(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3). (+4 more)

### Community 24 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 25 - "FfmpegService"
Cohesion: 0.17
Nodes (13): SourceKind, FfmpegService, Any, AppConfig, ndarray, Path, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+5 more)

### Community 26 - "app.py"
Cohesion: 0.11
Nodes (23): App, harvester_pipeline_orchestrator, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_util_logging_setup, Textual UI: throttled bridge, level-filtered console, and M6 hardening…, Textual Curation Workbench Modal Screen for OmniRip M10. (+15 more)

### Community 27 - "ComposeResult"
Cohesion: 0.11
Nodes (10): FatalSetupScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17). (+2 more)

### Community 28 - ".render_audio_buffer"
Cohesion: 0.22
Nodes (9): EnhancementPreset, ndarray, Path, Apply complete enhancement DSP pipeline to in-memory audio array. Pipeline: 1.…, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Decode any audio file directly into 48kHz float32 stereo numpy array using… (+1 more)

### Community 29 - "numpy"
Cohesion: 0.13
Nodes (19): collections_abc, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_enhancement_conservative_provider, harvester_services_model_manager, logging, numpy, Enhancement provider protocol and base types for OmniRip M10. (+11 more)

### Community 30 - "QualityEvidence"
Cohesion: 0.08
Nodes (35): enum, RuntimeError, assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality. (+27 more)

### Community 31 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 32 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (25): Atomic filesystem helpers, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+17 more)

### Community 33 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 34 - "ensure_2d_audio"
Cohesion: 0.24
Nodes (13): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+5 more)

### Community 35 - "ytdlp.py"
Cohesion: 0.05
Nodes (68): ProgressCallback, shutil, move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.… (+60 more)

### Community 36 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 37 - "PipelineOrchestrator"
Cohesion: 0.07
Nodes (30): AcoustidService, BatchScan, CoverArtService, DownloadProgress, EventKind, Exception, JobEvent, Queue (+22 more)

### Community 38 - "logging_setup.py"
Cohesion: 0.08
Nodes (23): logging_handlers, LogRecord, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., CallbackHandler (+15 more)

### Community 39 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 40 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.11
Nodes (25): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID (+17 more)

### Community 41 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 44 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 45 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 47 - "slskd.py"
Cohesion: 0.20
Nodes (11): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+3 more)

### Community 48 - "InteractiveScrubber"
Cohesion: 0.12
Nodes (11): Click, Message, InteractiveScrubber, ComposeResult, Text, Widget, Interactive timeline scrubber allowing instant click-to-seek, showing visual…, Dispatched when user clicks anywhere on timeline to seek. (+3 more)

### Community 49 - "environment.py"
Cohesion: 0.12
Nodes (11): dataclasses, harvester_analysis_enhancement, hashlib, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., Asynchronous startup checks for local binaries and optional services., Model management and checkpoint downloading service for OmniRip M10. (+3 more)

### Community 50 - "pathlib"
Cohesion: 0.08
Nodes (27): harvester_analysis_enhancement_presets, harvester_ui_screens_curation_workbench, pathlib, platform, platformdirs, Platform-aware runtime directories., Headless preview generation and system audio player dispatch for OmniRip M10., Path (+19 more)

### Community 52 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 53 - "test_spectral.py"
Cohesion: 0.28
Nodes (19): parametrize, _content(), fixture_fraud_128(), fixture_fraud_192(), fixture_honest_full(), fixture_honest_rolloff(), fixture_near_silent(), fixture_short() (+11 more)

### Community 54 - "JobTable"
Cohesion: 0.11
Nodes (15): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network). (+7 more)

### Community 55 - "test_ui_workbench.py"
Cohesion: 0.17
Nodes (18): ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer. (+10 more)

### Community 56 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 57 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 58 - "SpectralResult"
Cohesion: 0.20
Nodes (17): analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray, Spectral anti-fraud detector: brick-wall cutoff and steepness analysis.… (+9 more)

### Community 59 - "DependencyStatus"
Cohesion: 0.15
Nodes (11): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable., Run independent dependency checks concurrently. (+3 more)

### Community 60 - "test_batch_swap.py"
Cohesion: 0.16
Nodes (17): harvester_pipeline, atomic_replace(), fsync_directory(), fsync_file(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a file's contents to stable storage., fsync a directory fd so renames inside it survive a crash (POSIX only). (+9 more)

### Community 61 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 62 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 63 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 65 - ".__init__"
Cohesion: 0.15
Nodes (6): DependencyStatus, EnvironmentStatus, AppConfig, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 66 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 67 - "ConservativeDSPProvider"
Cohesion: 0.29
Nodes (4): ConservativeDSPProvider, ndarray, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, Generate high-frequency residual harmonics based on the top octave of the…

### Community 69 - "CurationWorkbenchModal"
Cohesion: 0.13
Nodes (11): CurationWorkbenchModal, Changed, Path, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App, asyncio (+3 more)

### Community 70 - "test_enhancement_dsp.py"
Cohesion: 0.17
Nodes (11): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter(), test_apply_progressive_mono() (+3 more)

### Community 72 - "ffmpeg.py"
Cohesion: 0.22
Nodes (7): harvester_util_errors, harvester_util_subproc, shlex, Async FFmpeg/ffprobe adapter used by fallback acquisition., Path, test_build_mp3_v0_arguments(), test_probe_audio_info_cache()

### Community 73 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 74 - "Pipeline orchestrator"
Cohesion: 0.19
Nodes (14): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+6 more)

### Community 76 - ".generate_residual"
Cohesion: 0.40
Nodes (3): Any, ndarray, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 78 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 79 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 80 - "EnhancementExporter"
Cohesion: 0.08
Nodes (22): EnhancementProvider, harvester_services_enhancement, EnhancementExporter, Renders enhanced audio and exports MP3 derivatives with explicit provenance…, Toggle between Neural Model Acceleration and Eco DSP synthesis., FlashSRProvider, ModelManager, Path (+14 more)

### Community 81 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 84 - "yt-dlp"
Cohesion: 0.14
Nodes (15): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D10 — Playlist cap 50 + confirmation, D3 — Spectral check scope: P2P lossless claims only, FR-1 — Extract metadata without downloading, FR-10 — Provenance-based spectral exemption, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback (+7 more)

### Community 85 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 86 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 87 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 89 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 90 - "phase5_polish"
Cohesion: 0.40
Nodes (5): Batch report writer, FFmpeg service, phase5_polish, q_polish stage queue, Tagging service

### Community 91 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 93 - "ConservativeRestorationService"
Cohesion: 0.43
Nodes (4): ConservativeRestorationService, ndarray, Path, Apply the deterministic restoration chain to a file without mutating it.

### Community 94 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 95 - "phase2_hunt"
Cohesion: 0.29
Nodes (7): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, Concurrent download semaphore

### Community 96 - "State machine"
Cohesion: 0.29
Nodes (7): State machine, Title cleaning analysis, Fallback anti-loop guard, IllegalTransition, Unit test plan, State-machine truth directive, Tests alongside every module

### Community 97 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 98 - ".generate_residual"
Cohesion: 0.33
Nodes (4): Any, ndarray, Internal inference wrapper., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 99 - "test_ui_player.py"
Cohesion: 0.40
Nodes (4): PlayerTestApp, ComposeResult, Unit tests for AudioPlayerWidget controls and state., test_audio_player_widget_lifecycle()

### Community 100 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 101 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 102 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 103 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 104 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 105 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 106 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 107 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 111 - "split_bands"
Cohesion: 0.29
Nodes (6): Split audio into low and high bands at cutoff_hz using a linear-phase smooth…, split_bands(), ndarray, Synthesize multi-band residual combining NVSR mid-high and FlashSR air band., Verify complementary band splitting sums to original signal., test_split_bands_reconstruction_flatness()

### Community 169 - "._submit_current"
Cohesion: 0.20
Nodes (3): Changed, Cycle to next dynamic color theme., Submitted

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Batch adapter`, `Candidate scoring` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 890 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **84 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkbenchWidget` connect `WorkbenchWidget` to `AudioVisualizer`, `HarvesterApp`, `AudioPlayerWidget`, `workbench.py`, `.compose`, `EnhancementExporter`, `MasteringEQSettings`, `test_ui_workbench.py`, `app.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `config.py`, `.__init__`, `BatchConfirmScreen`, `WorkbenchWidget`, `._submit_current`, `._load_selected_into_workbench_and_player`, `AudioPlayerWidget`, `DependencyStatus`, `.action_seek_backward`, `JobTable`, `app.py`, `ComposeResult`, `__main__.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `config.py` to `scanner.py`, `acoustid.py`, `ytdlp.py`, `PipelineOrchestrator`, `orchestrator.py`, `analysis/restoration.py`, `ValidationError`, `slskd.py`, `environment.py`, `models.py`, `SlskdService`, `DependencyStatus`, `ConservativeRestorationService`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `WorkbenchWidget`) actually correct?**
  _`HarvesterApp` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 36 INFERRED edges - model-reasoned connections that need verification._