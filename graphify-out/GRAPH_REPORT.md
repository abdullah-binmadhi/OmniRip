# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2263 nodes · 4633 edges · 181 communities (107 shown, 74 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 581 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `acc0ef36`
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
- pathlib
- test_orchestrator_m4.py
- test_playlist.py
- models.py
- AppConfig
- TrackJob
- PreviewManager
- SourceKind
- ModelManager
- JobEvent
- test_orchestrator_m2.py
- MasteringEQSettings
- CanonicalMetadata
- test_orchestrator_m3.py
- FfmpegService
- app.py
- ComposeResult
- EnhancementExporter
- numpy
- State
- __main__.py
- Phase 1 — Input Analysis
- LogConsole
- ensure_2d_audio
- test_batch_trash.py
- phase1_analyze.py
- PipelineOrchestrator
- logging_setup.py
- Phase 5 — Polish and Sync
- Harvester (Hybrid Music Harvest & Curation Engine)
- titleclean.py
- YtdlpService
- QualityEvidence
- test_orchestrator.py
- scoring.py
- CoverArtService
- slskd.py
- InteractiveScrubber
- dataclasses
- exporter.py
- ytdlp.py
- SlskdService
- test_spectral.py
- test_ui_pilot.py
- WorkbenchTestApp
- CircuitBreaker
- EnhancementProvider
- Verdict
- DependencyStatus
- JobTable
- slskd daemon
- Textual TUI
- test_slskd.py
- .__init__
- StatusBar
- Minimal Implementation Ladder
- HybridCoOpProvider
- TrackJob
- CurationWorkbenchModal
- test_enhancement_dsp.py
- .__init__
- asyncio
- Mode B — Local Batch Audit
- Pipeline orchestrator
- errors.py
- FlashSRProvider
- test_phase5_polish.py
- retry.py
- Spectral fixture connectivity gap
- test_enhancement_providers.py
- Graphify Knowledge Graph
- .submit_batch
- FR-7 — Fingerprint before transcode
- yt-dlp
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- .submit_playlist
- CI Workflow
- phase5_polish
- ._load_selected_into_workbench_and_player
- Any
- ValidationError
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
- pytest
- .compose
- .wait_for_idle
- .generate_residual
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
- ndarray
- StrEnum
- Exception
- Queue
- EnhancementPreset
- ndarray
- SubprocessRegistry
- Changed
- ComposeResult
- Pressed
- TrackJob
- Text
- App
- Text
- Changed
- TrackJob
- Path
- Widget

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 53 edges
2. `ValidationError` - 53 edges
3. `HarvesterApp` - 47 edges
4. `TrackJob` - 46 edges
5. `CanonicalMetadata` - 44 edges
6. `WorkbenchWidget` - 40 edges
7. `load_config()` - 40 edges
8. `AppConfig` - 39 edges
9. `AudioPlayerWidget` - 39 edges
10. `AudioVisualizer` - 33 edges

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

## Communities (181 total, 74 thin omitted)

### Community 0 - "config.py"
Cohesion: 0.06
Nodes (57): AppPaths, copy, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., AcoustidConfig (+49 more)

### Community 1 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 2 - "acoustid.py"
Cohesion: 0.07
Nodes (29): Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+21 more)

### Community 3 - "AudioVisualizer"
Cohesion: 0.06
Nodes (27): ComposeResult, AudioVisualizer, Path, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels. (+19 more)

### Community 4 - "HarvesterApp"
Cohesion: 0.06
Nodes (17): Changed, FlushPlan, HarvesterApp, wrapped(), Textual application connected to the asynchronous pipeline via a throttled…, Scan a directory; queue immediately unless confirmation is required., Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file. (+9 more)

### Community 5 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (24): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+16 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "WorkbenchWidget"
Cohesion: 0.10
Nodes (19): setter, Path, Pressed, Widget, Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., In-page audio enhancement and auditioning workbench panel. Supports real-time…, Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on… (+11 more)

### Community 8 - "orchestrator.py"
Cohesion: 0.07
Nodes (35): collections, harvester_analysis_scoring, harvester_analysis_titleclean, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral (+27 more)

### Community 9 - "AudioPlayerWidget"
Cohesion: 0.10
Nodes (15): AudioPlayerWidget, Path, Pressed, Dedicated in-app audio player bar featuring playback controls, track metadata,…, Load an audio file into the player and prepare visualizer frames., Instant zero-gap stream switch between original and enhanced audio, preserving…, Toggle playback between playing and paused/stopped., Begin audio playback and animate visualizer. (+7 more)

### Community 10 - "analysis/restoration.py"
Cohesion: 0.12
Nodes (31): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+23 more)

### Community 11 - "pathlib"
Cohesion: 0.11
Nodes (26): harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_ui_visualizer, math, pathlib, platform, platformdirs, rich_style (+18 more)

### Community 12 - "test_orchestrator_m4.py"
Cohesion: 0.14
Nodes (18): SpectralResult, _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+10 more)

### Community 13 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 14 - "models.py"
Cohesion: 0.09
Nodes (27): datetime, harvester_batch_report, json, Path, batch_report_name(), BatchReport, job_row(), Path (+19 more)

### Community 15 - "AppConfig"
Cohesion: 0.17
Nodes (30): CanonicalMetadata, harvester_util_fsatomic, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac() (+22 more)

### Community 16 - "TrackJob"
Cohesion: 0.15
Nodes (29): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 17 - "PreviewManager"
Cohesion: 0.09
Nodes (25): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+17 more)

### Community 18 - "SourceKind"
Cohesion: 0.12
Nodes (20): Pure analysis logic: query cleaning and P2P candidate ranking., StrEnum, SourceKind, excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2. (+12 more)

### Community 19 - "ModelManager"
Cohesion: 0.10
Nodes (22): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+14 more)

### Community 20 - "JobEvent"
Cohesion: 0.14
Nodes (22): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+14 more)

### Community 21 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 22 - "MasteringEQSettings"
Cohesion: 0.10
Nodes (21): ndarray, apply_mastering_eq(), MasteringEQSettings, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+13 more)

### Community 23 - "CanonicalMetadata"
Cohesion: 0.14
Nodes (18): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields. (+10 more)

### Community 24 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 25 - "FfmpegService"
Cohesion: 0.18
Nodes (13): Any, SourceKind, FfmpegService, Path, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines., Decode a mono excerpt to float32 PCM without blocking the loop., Build the deterministic Phase 5 transcode arguments. (+5 more)

### Community 26 - "app.py"
Cohesion: 0.10
Nodes (21): App, harvester_pipeline_orchestrator, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_ui_player, harvester_ui_workbench, harvester_util_logging_setup (+13 more)

### Community 27 - "ComposeResult"
Cohesion: 0.10
Nodes (10): ComposeResult, Pressed, BatchConfirmScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, Non-blocking help overlay for the application., Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5). (+2 more)

### Community 28 - "EnhancementExporter"
Cohesion: 0.12
Nodes (18): EnhancementPreset, EnhancementExporter, ndarray, Path, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+10 more)

### Community 29 - "numpy"
Cohesion: 0.14
Nodes (16): collections_abc, harvester_analysis_enhancement_dsp, harvester_services_model_manager, logging, numpy, Enhancement provider protocol and base types for OmniRip M10., FlashSR (Distilled Diffusion Air-Band) provider for OmniRip M10., Hybrid Co-Op Provider (NVSR + FlashSR) for OmniRip M10. (+8 more)

### Community 30 - "State"
Cohesion: 0.13
Nodes (19): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), StrEnum, The single source of truth for legal job-state transitions. ``State`` lives… (+11 more)

### Community 31 - "__main__.py"
Cohesion: 0.13
Nodes (18): argparse, ArgumentParser, harvester, harvester_pipeline, harvester_util_errors, build_parser(), main(), Command-line entry point for the OmniRip TUI. (+10 more)

### Community 32 - "Phase 1 — Input Analysis"
Cohesion: 0.12
Nodes (22): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+14 more)

### Community 33 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 34 - "ensure_2d_audio"
Cohesion: 0.18
Nodes (18): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+10 more)

### Community 35 - "test_batch_trash.py"
Cohesion: 0.20
Nodes (20): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+12 more)

### Community 36 - "phase1_analyze.py"
Cohesion: 0.14
Nodes (18): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+10 more)

### Community 37 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (7): DownloadProgress, EventKind, Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract.

### Community 38 - "logging_setup.py"
Cohesion: 0.13
Nodes (14): logging_handlers, LogRecord, CallbackHandler, configure_logging(), ContextDefaultsFilter, _level(), LoggingController, Queue-based logging fan-out with secret redaction. (+6 more)

### Community 39 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 40 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.14
Nodes (20): Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID, Audio fingerprinting, Decision D3 - Phase 4 applies only to P2P lossless-claiming files, Requirements (docs/01-requirements.md), Architecture (docs/02-architecture.md), Pipeline Phases (docs/03-pipeline.md) (+12 more)

### Community 41 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 42 - "YtdlpService"
Cohesion: 0.19
Nodes (11): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+3 more)

### Community 43 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 44 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 45 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 46 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 47 - "slskd.py"
Cohesion: 0.20
Nodes (11): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+3 more)

### Community 48 - "InteractiveScrubber"
Cohesion: 0.13
Nodes (10): Click, Message, InteractiveScrubber, ComposeResult, Widget, Interactive timeline scrubber allowing instant click-to-seek, showing visual…, Dispatched when user clicks anywhere on timeline to seek., Studio-grade audio stream monitor displaying: - Active Stream Status Badge ([♫… (+2 more)

### Community 49 - "dataclasses"
Cohesion: 0.12
Nodes (12): dataclasses, harvester_analysis_enhancement, harvester_analysis_enhancement_provider, hashlib, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., Model management and checkpoint downloading service for OmniRip M10. (+4 more)

### Community 50 - "exporter.py"
Cohesion: 0.12
Nodes (16): harvester_analysis_enhancement_presets, harvester_services_enhancement_conservative_provider, harvester_services_enhancement_flashsr_provider, harvester_services_enhancement_hybrid_provider, harvester_services_enhancement_nvsr_provider, mutagen_id3, Non-destructive Enhancement Exporter and FFmpeg Audio I/O for OmniRip M10., Tests for EnhancementExporter and Presets (Milestone 10-D). (+8 more)

### Community 51 - "ytdlp.py"
Cohesion: 0.18
Nodes (14): os, DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress (+6 more)

### Community 52 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 53 - "test_spectral.py"
Cohesion: 0.32
Nodes (17): _content(), fixture_fraud_128(), fixture_fraud_192(), fixture_honest_full(), fixture_honest_rolloff(), fixture_near_silent(), fixture_short(), fixture_up96_void() (+9 more)

### Community 54 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 55 - "WorkbenchTestApp"
Cohesion: 0.15
Nodes (17): ComposeResult, Path, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer., Verify that EQ adjustments update the player's live audio filter across both… (+9 more)

### Community 56 - "CircuitBreaker"
Cohesion: 0.16
Nodes (10): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+2 more)

### Community 57 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 58 - "Verdict"
Cohesion: 0.22
Nodes (16): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+8 more)

### Community 59 - "DependencyStatus"
Cohesion: 0.18
Nodes (8): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable., Run independent dependency checks concurrently., test_all_required_dependencies_ready_when_optional_services_are_down(), test_required_dependency_controls_ready_state()

### Community 60 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., TrackJob

### Community 61 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 62 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 63 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 64 - ".__init__"
Cohesion: 0.14
Nodes (6): AppConfig, PlaylistConfirmScreen, QuitConfirmScreen, Show entry count and cap before expanding a playlist (docs/08 §2, D10)., Confirm quit while jobs are still active (docs/08 §5, FR-17)., SubprocessRegistry

### Community 65 - "StatusBar"
Cohesion: 0.13
Nodes (7): DependencyStatus, EnvironmentStatus, FatalSetupScreen, Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 66 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 67 - "HybridCoOpProvider"
Cohesion: 0.15
Nodes (7): EnhancementProvider, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, HybridCoOpProvider, Hybrid multi-band provider: - NVSR reconstructs mid-high frequencies:…, Verify that every provider actively synthesizes audible high-frequency…, test_all_providers_bandlimited_excitation()

### Community 69 - "CurationWorkbenchModal"
Cohesion: 0.15
Nodes (8): CurationWorkbenchModal, Changed, Path, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App, ComposeResult

### Community 70 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 71 - ".__init__"
Cohesion: 0.17
Nodes (10): AcoustidService, CoverArtService, JobEvent, Queue, MetadataTagger, SlskdService, SubprocessRegistry, StageHandler (+2 more)

### Community 72 - "asyncio"
Cohesion: 0.21
Nodes (10): asyncio, httpx, shlex, shutil, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, _run_version() (+2 more)

### Community 73 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 74 - "Pipeline orchestrator"
Cohesion: 0.21
Nodes (13): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+5 more)

### Community 75 - "errors.py"
Cohesion: 0.29
Nodes (11): ErrorClass, DiskError, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited (+3 more)

### Community 76 - "FlashSRProvider"
Cohesion: 0.19
Nodes (7): FlashSRProvider, Any, ModelManager, ndarray, Path, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000))., FlashSR single-step distilled diffusion air-band generator. Generates ultra-…

### Community 77 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 78 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 79 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 80 - "test_enhancement_providers.py"
Cohesion: 0.18
Nodes (10): harvester_services_enhancement, Tests for M10-C Enhancement Providers., Verify ConservativeDSPProvider is available and generates residual above cutoff., Verify NVSRProvider gracefully generates high-pass residual when model weights…, Verify FlashSRProvider produces air-band residual (> 16 kHz)., Verify HybridCoOpProvider correctly merges providers., test_conservative_dsp_provider(), test_flashsr_provider_air_band() (+2 more)

### Community 81 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 82 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 83 - "FR-7 — Fingerprint before transcode"
Cohesion: 0.20
Nodes (10): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+2 more)

### Community 84 - "yt-dlp"
Cohesion: 0.22
Nodes (10): D10 — Playlist cap 50 + confirmation, FR-1 — Extract metadata without downloading, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback, Mode A — Single URL, NFR-3 — Resilience, slskd Integration (docs/06-slskd-integration.md), yt-dlp Fallback (docs/07-ytdlp-fallback.md) (+2 more)

### Community 85 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 86 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 87 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 88 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 89 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 90 - "phase5_polish"
Cohesion: 0.25
Nodes (9): Batch report writer, FFmpeg service, Atomic filesystem helpers, phase5_polish, q_polish stage queue, Tagging service, Disk and file safety, File safety directive (+1 more)

### Community 91 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 93 - "ValidationError"
Cohesion: 0.42
Nodes (5): ConservativeRestorationService, ndarray, Path, Apply the deterministic restoration chain to a file without mutating it., ValidationError

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

### Community 108 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Batch adapter`, `Candidate scoring` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 883 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **74 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `TrackJob`, `HarvesterApp`, `test_orchestrator_m5.py`, `.__init__`, `orchestrator.py`, `test_orchestrator_m4.py`, `test_orchestrator.py`, `.wait_for_idle`, `AppConfig`, `test_playlist.py`, `.submit_batch`, `test_orchestrator_m2.py`, `.submit_playlist`, `FfmpegService`, `test_orchestrator_m3.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `.__init__`, `config.py`, `ComposeResult`, `DependencyStatus`, `test_ui_pilot.py`, `app.py`, `._load_selected_into_workbench_and_player`, `__main__.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `load_config()` connect `config.py` to `.__init__`, `scanner.py`, `acoustid.py`, `test_orchestrator_m5.py`, `WorkbenchWidget`, `test_orchestrator_m4.py`, `test_orchestrator.py`, `CoverArtService`, `AppConfig`, `test_phase5_polish.py`, `test_playlist.py`, `SourceKind`, `test_orchestrator_m2.py`, `test_ui_pilot.py`, `test_orchestrator_m3.py`, `FfmpegService`, `test_slskd.py`, `__main__.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `HarvesterApp` (e.g. with `_app()` and `test_m0_shell_mounts_without_startup_checks()`) actually correct?**
  _`HarvesterApp` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 36 INFERRED edges - model-reasoned connections that need verification._