# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2284 nodes · 4516 edges · 203 communities (105 shown, 98 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 476 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c8ed91d2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- scanner.py
- test_orchestrator_m5.py
- P2PCandidate
- ensure_2d_audio
- EnhancementExporter
- Milestone M7 — QA & packaging
- dataclasses
- AudioVisualizer
- QualityEvidence
- PreviewManager
- WorkbenchWidget
- analysis/restoration.py
- FlashSRProvider
- HarvesterApp
- AudioPlayerWidget
- test_spectral.py
- test_playlist.py
- test_orchestrator_m4.py
- TrackJob
- app.py
- pathlib
- report.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- config.py
- FfmpegService
- FlushPlan
- test_orchestrator_m2.py
- ComposeResult
- test_phase4_spectral.py
- AppConfig
- CanonicalMetadata
- test_batch_trash.py
- Pipeline orchestrator
- phase2_hunt.py
- phase1_analyze.py
- LogConsole
- environment.py
- test_orchestrator_m3.py
- Phase 1 — Input Analysis
- ValidationError
- yt-dlp
- test_model_manager.py
- AcoustidService
- test_orchestrator.py
- test_ui_workbench.py
- InteractiveScrubber
- Spectral fixture connectivity gap
- EnhancementProvider
- test_enhancement_exporter.py
- PipelineOrchestrator
- test_ui_pilot.py
- orchestrator.py
- models.py
- JobTable
- Textual TUI
- ModelManager
- CircuitBreaker
- textual_app
- ConfigError
- ytdlp.py
- Minimal Implementation Ladder
- phase2_hunt
- TrackJob
- SlskdService
- .__init__
- Mode B — Local Batch Audit
- acoustid.py
- test_acoustid.py
- .__init__
- __main__.py
- Phase 5 — Polish and Sync
- SubprocessRegistry
- slskd.py
- musicbrainz.py
- persist_first_run_acceptance
- CoverArtService
- test_phase5_polish.py
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- .submit_batch
- atomic_replace
- CI Workflow
- ._load_selected_into_workbench_and_player
- FakeSlskd
- phase1_analyze
- BatchConfirmScreen
- P2P candidate scoring
- pytest
- BatchScan
- Any
- .submit_playlist
- ._worker_loop
- yt-dlp metadata probe
- PlaylistConfirmScreen
- test_config.py
- test_ui_player.py
- test_ui_visualizer.py
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- .compose
- FakeCover
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
- analysis/__init__.py
- batch/__init__.py
- .public_dict
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- .action_open_workbench
- .action_seek_backward
- ._confirm_batch
- ui/__init__.py
- update_progress
- util/__init__.py
- Any
- AppConfig
- BatchScan
- CanonicalMetadata
- Changed
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
- FlushPlan
- harvester_analysis_enhancement_eq
- harvester_batch_report
- harvester_batch_scanner
- harvester_batch_trash
- harvester_pipeline_orchestrator
- harvester_pipeline_phase4_spectral
- harvester_pipeline_phase5_polish
- harvester_services_enhancement_conservative_provider
- harvester_services_enhancement_exporter
- harvester_services_enhancement_flashsr_provider
- harvester_services_enhancement_hybrid_provider
- harvester_services_enhancement_nvsr_provider
- harvester_services_ffmpeg
- harvester_ui_bridge
- harvester_ui_logconsole
- harvester_ui_player
- harvester_ui_visualizer
- harvester_ui_workbench
- harvester_util_fsatomic
- JobEvent
- ndarray
- Path
- harvester
- Pressed
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
- SubprocessRegistry
- Text
- TrackJob
- Widget

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 56 edges
2. `HarvesterApp` - 54 edges
3. `AppConfig` - 45 edges
4. `WorkbenchWidget` - 44 edges
5. `ValidationError` - 44 edges
6. `AudioPlayerWidget` - 42 edges
7. `load_config()` - 42 edges
8. `AudioVisualizer` - 38 edges
9. `CanonicalMetadata` - 33 edges
10. `EnhancementExporter` - 32 edges

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

## Communities (203 total, 98 thin omitted)

### Community 0 - "scanner.py"
Cohesion: 0.06
Nodes (68): BatchEntry, Match, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack (+60 more)

### Community 1 - "test_orchestrator_m5.py"
Cohesion: 0.07
Nodes (25): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+17 more)

### Community 2 - "P2PCandidate"
Cohesion: 0.09
Nodes (37): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+29 more)

### Community 3 - "ensure_2d_audio"
Cohesion: 0.07
Nodes (38): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+30 more)

### Community 4 - "EnhancementExporter"
Cohesion: 0.07
Nodes (33): EnhancementPreset, apply_mastering_eq(), MasteringEQSettings, ndarray, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.… (+25 more)

### Community 5 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 6 - "dataclasses"
Cohesion: 0.06
Nodes (31): dataclasses, logging_handlers, LogRecord, platformdirs, Queue, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering. (+23 more)

### Community 7 - "AudioVisualizer"
Cohesion: 0.06
Nodes (22): ComposeResult, AudioVisualizer, Path, Text, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc). (+14 more)

### Community 8 - "QualityEvidence"
Cohesion: 0.08
Nodes (35): enum, RuntimeError, assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality. (+27 more)

### Community 9 - "PreviewManager"
Cohesion: 0.07
Nodes (32): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+24 more)

### Community 10 - "WorkbenchWidget"
Cohesion: 0.09
Nodes (22): setter, Changed, Path, Pressed, TrackJob, Widget, Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Download or verify local caching of all AI neural model weights. (+14 more)

### Community 11 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 12 - "FlashSRProvider"
Cohesion: 0.06
Nodes (26): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, ModelManager, Path, FlashSR single-step distilled diffusion air-band generator. Generates ultra-… (+18 more)

### Community 13 - "HarvesterApp"
Cohesion: 0.08
Nodes (12): HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Cycle to next dynamic color theme., Toggle visualizer between spectrum analyzer and oscilloscope., Seek forward 5 seconds in player., Seek backward 15 seconds in player. (+4 more)

### Community 14 - "AudioPlayerWidget"
Cohesion: 0.10
Nodes (15): AudioPlayerWidget, Path, Pressed, Dedicated in-app audio player bar featuring playback controls, track metadata,…, Load an audio file into the player and prepare visualizer frames., Instant zero-gap stream switch between original and enhanced audio, preserving…, Toggle playback between playing and paused/stopped., Begin audio playback and animate visualizer. (+7 more)

### Community 15 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 16 - "test_playlist.py"
Cohesion: 0.10
Nodes (16): harvester_util_circuit, _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+8 more)

### Community 17 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 18 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 19 - "app.py"
Cohesion: 0.11
Nodes (24): asyncio, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_themes, harvester_util_logging_setup, math, rich_style, rich_text (+16 more)

### Community 20 - "pathlib"
Cohesion: 0.14
Nodes (20): collections_abc, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_presets, harvester_analysis_enhancement_provider, harvester_services_model_manager, hashlib, logging, numpy (+12 more)

### Community 21 - "report.py"
Cohesion: 0.10
Nodes (25): datetime, json, batch_report_name(), BatchReport, job_row(), Path, TrackJob, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14). (+17 more)

### Community 22 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 23 - "config.py"
Cohesion: 0.15
Nodes (28): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+20 more)

### Community 24 - "FfmpegService"
Cohesion: 0.14
Nodes (16): SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+8 more)

### Community 25 - "FlushPlan"
Cohesion: 0.10
Nodes (20): Apply, ErrorInfo, coalesce_events(), FlushPlan, JobEvent, Queue, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job. (+12 more)

### Community 26 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 27 - "ComposeResult"
Cohesion: 0.09
Nodes (12): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application. (+4 more)

### Community 28 - "test_phase4_spectral.py"
Cohesion: 0.13
Nodes (18): excerpt_window(), _excerpt_window(), SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2., run_spectral_check(), _config() (+10 more)

### Community 29 - "AppConfig"
Cohesion: 0.22
Nodes (23): harvester_services_restoration, os, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac() (+15 more)

### Community 30 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (16): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields. (+8 more)

### Community 31 - "test_batch_trash.py"
Cohesion: 0.18
Nodes (22): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+14 more)

### Community 32 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 33 - "phase2_hunt.py"
Cohesion: 0.11
Nodes (22): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, mutagen_flac, P2PCandidate, build_hunt_queries(), hunt_and_score() (+14 more)

### Community 34 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+11 more)

### Community 35 - "LogConsole"
Cohesion: 0.12
Nodes (15): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+7 more)

### Community 36 - "environment.py"
Cohesion: 0.15
Nodes (13): shlex, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+5 more)

### Community 37 - "test_orchestrator_m3.py"
Cohesion: 0.15
Nodes (9): _build(), FakeAcoustid, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path, test_ground_truth_metadata_reaches_flac_output() (+1 more)

### Community 38 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 39 - "ValidationError"
Cohesion: 0.20
Nodes (12): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+4 more)

### Community 40 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 41 - "test_model_manager.py"
Cohesion: 0.12
Nodes (16): harvester_analysis_enhancement, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Verify that a dummy class adhering to EnhancementProvider satisfies isinstance…, Test model path resolution and caching checks in ModelManager., Verify SHA-256 calculation and verification., Test downloading a model via mocked huggingface_hub., Test that requesting an unknown model raises KeyError. (+8 more)

### Community 42 - "AcoustidService"
Cohesion: 0.16
Nodes (5): AcoustidService, AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 43 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 44 - "test_ui_workbench.py"
Cohesion: 0.17
Nodes (18): ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer. (+10 more)

### Community 45 - "InteractiveScrubber"
Cohesion: 0.12
Nodes (11): Click, Message, InteractiveScrubber, ComposeResult, Text, Widget, Interactive timeline scrubber allowing instant click-to-seek, showing visual…, Dispatched when user clicks anywhere on timeline to seek. (+3 more)

### Community 46 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 47 - "EnhancementProvider"
Cohesion: 0.11
Nodes (14): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Enhancement provider protocol and base types for OmniRip M10. (+6 more)

### Community 48 - "test_enhancement_exporter.py"
Cohesion: 0.12
Nodes (17): mutagen_id3, Path, Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify that EnhancementExporter toggles neural acceleration across all…, Verify all 5 planned presets exist and have valid attributes., Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify render_audio_buffer produces valid audio for every preset., Verify that ID3 provenance tags are correctly added to MP3 derivative. (+9 more)

### Community 49 - "PipelineOrchestrator"
Cohesion: 0.18
Nodes (6): DownloadProgress, Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract.

### Community 50 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 51 - "orchestrator.py"
Cohesion: 0.15
Nodes (14): collections, harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_acoustid, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors (+6 more)

### Community 52 - "models.py"
Cohesion: 0.19
Nodes (14): EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, SourceKind (+6 more)

### Community 53 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 54 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 55 - "ModelManager"
Cohesion: 0.19
Nodes (10): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+2 more)

### Community 56 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 57 - "textual_app"
Cohesion: 0.19
Nodes (12): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+4 more)

### Community 58 - "ConfigError"
Cohesion: 0.24
Nodes (12): Validate cross-field invariants and return this config for fluent use., ErrorClass, ConfigError, HarvesterError, JobCancelled, PermanentSource, Any, Exception (+4 more)

### Community 59 - "ytdlp.py"
Cohesion: 0.23
Nodes (12): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, Any (+4 more)

### Community 60 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 61 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 63 - "SlskdService"
Cohesion: 0.25
Nodes (4): AsyncClient, Path, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 64 - ".__init__"
Cohesion: 0.17
Nodes (5): DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 65 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 66 - "acoustid.py"
Cohesion: 0.33
Nodes (12): sqlite3, _earliest_release(), _metadata_from_json(), _metadata_to_json(), _number(), Any, AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache., Parse a numeric field as an integer (years and similar); None when not numeric. (+4 more)

### Community 67 - "test_acoustid.py"
Cohesion: 0.35
Nodes (9): Fingerprint, _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network(), test_low_confidence_result_is_rejected() (+1 more)

### Community 68 - ".__init__"
Cohesion: 0.17
Nodes (9): AcoustidService, CoverArtService, EventKind, SlskdService, JobEvent, MetadataTagger, Queue, SubprocessRegistry (+1 more)

### Community 69 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 70 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 71 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 72 - "slskd.py"
Cohesion: 0.32
Nodes (11): _bool_or_none(), _concrete_paths(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), _pick_download_route(), Any (+3 more)

### Community 73 - "musicbrainz.py"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 74 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 75 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 76 - "test_phase5_polish.py"
Cohesion: 0.29
Nodes (9): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_polish_stream_rejects_keep_opus(), test_polish_stream_requires_workspace() (+1 more)

### Community 77 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

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
Nodes (8): harvester_pipeline, _job(), Path, TrackJob, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 82 - ".submit_batch"
Cohesion: 0.24
Nodes (7): _entry_tags(), BatchScan, Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 83 - "atomic_replace"
Cohesion: 0.31
Nodes (9): atomic_replace(), fsync_directory(), fsync_file(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a file's contents to stable storage., fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename. (+1 more)

### Community 84 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 85 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 86 - "FakeSlskd"
Cohesion: 0.33
Nodes (3): SearchResponse, SlskdFile, FakeSlskd

### Community 87 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 88 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 89 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 90 - "pytest"
Cohesion: 0.33
Nodes (5): pytest, asyncio, test_registry_terminates_process_by_job_prefix(), asyncio, test_m0_shell_mounts_without_startup_checks()

### Community 91 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 93 - ".submit_playlist"
Cohesion: 0.29
Nodes (4): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73).

### Community 94 - "._worker_loop"
Cohesion: 0.33
Nodes (3): Start workers and wait until shutdown is requested., StageHandler, Task

### Community 95 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 97 - "test_config.py"
Cohesion: 0.53
Nodes (5): Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected(), test_precedence_is_cli_over_environment_over_file(), test_secret_values_are_never_in_public_config()

### Community 98 - "test_ui_player.py"
Cohesion: 0.40
Nodes (4): PlayerTestApp, ComposeResult, Unit tests for AudioPlayerWidget controls and state., test_audio_player_widget_lifecycle()

### Community 99 - "test_ui_visualizer.py"
Cohesion: 0.40
Nodes (5): Unit tests for AudioVisualizer widget across all 5 visualizer modes., Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler., test_audio_visualizer_10bands_and_full_width_ruler(), test_audio_visualizer_modes_and_render(), VisualizerTestApp

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

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 907 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **98 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppConfig` connect `AppConfig` to `scanner.py`, `analysis/restoration.py`, `HarvesterApp`, `app.py`, `config.py`, `FfmpegService`, `test_phase4_spectral.py`, `environment.py`, `ValidationError`, `AcoustidService`, `PipelineOrchestrator`, `orchestrator.py`, `ConfigError`, `ytdlp.py`, `SlskdService`, `.__init__`, `acoustid.py`, `.__init__`, `SubprocessRegistry`, `slskd.py`, `musicbrainz.py`, `persist_first_run_acceptance`, `CoverArtService`, `.public_dict`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `.action_seek_backward`, `._confirm_batch`, `.__init__`, `LogConsole`, `environment.py`, `__main__.py`, `WorkbenchWidget`, `AudioPlayerWidget`, `PipelineOrchestrator`, `test_ui_pilot.py`, `app.py`, `._load_selected_into_workbench_and_player`, `BatchConfirmScreen`, `FlushPlan`, `pytest`, `ComposeResult`, `AppConfig`, `.action_open_workbench`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `test_orchestrator_m5.py`, `.__init__`, `test_orchestrator_m3.py`, `test_orchestrator.py`, `HarvesterApp`, `.wait_for_idle`, `test_playlist.py`, `test_orchestrator_m4.py`, `.submit_batch`, `orchestrator.py`, `.submit_playlist`, `report.py`, `app.py`, `FfmpegService`, `._worker_loop`, `test_orchestrator_m2.py`, `AppConfig`, `TrackJob`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `HarvesterApp` (e.g. with `AppConfig` and `PipelineOrchestrator`) actually correct?**
  _`HarvesterApp` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AppConfig` (e.g. with `scan_directory()` and `PipelineOrchestrator`) actually correct?**
  _`AppConfig` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `MasteringEQSettings`) actually correct?**
  _`WorkbenchWidget` has 13 INFERRED edges - model-reasoned connections that need verification._