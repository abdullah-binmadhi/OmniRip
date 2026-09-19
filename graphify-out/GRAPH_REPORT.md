# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2431 nodes · 4818 edges · 194 communities (114 shown, 80 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 499 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e1f37e9a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ValidationError
- stem_separator.py
- config.py
- AudioPlayerWidget
- scanner.py
- HarvesterApp
- test_orchestrator_m5.py
- Milestone M7 — QA & packaging
- analysis/restoration.py
- FlashSRProvider
- test_model_manager.py
- ensure_2d_audio
- test_spectral.py
- AppConfig
- numpy
- EnhancementExporter
- ._startup
- test_playlist.py
- test_orchestrator_m4.py
- TrackJob
- Harvester (Hybrid Music Harvest & Curation Engine)
- PipelineOrchestrator
- test_orchestrator_m2.py
- PreviewManager
- test_orchestrator_m3.py
- test_ui_workbench.py
- slskd_config.py
- WorkbenchWidget
- app.py
- CanonicalMetadata
- Pipeline orchestrator
- State
- orchestrator.py
- phase2_hunt.py
- logging_setup.py
- environment.py
- test_phase4_spectral.py
- models.py
- Phase 1 — Input Analysis
- test_slskd_config.py
- report.py
- AcoustidService
- AudioVisualizer
- yt-dlp
- titleclean.py
- QualityEvidence
- Spectral fixture connectivity gap
- FfmpegService
- scoring.py
- test_batch_trash.py
- test_bridge.py
- SlskdService
- test_ui_pilot.py
- .on_select_changed
- CircuitBreaker
- apply_mastering_eq
- JobTable
- Textual TUI
- Path
- ModelManager
- CurationWorkbenchModal
- .__init__
- pathlib
- .submit_batch
- NVSRProvider
- Minimal Implementation Ladder
- phase2_hunt
- ._worker_loop
- SoulseekLoginModal
- player.py
- Mode B — Local Batch Audit
- AppPaths
- test_acoustid.py
- logconsole.py
- .render
- test_phase5_polish.py
- .__init__
- __main__.py
- Phase 5 — Polish and Sync
- retry.py
- acoustid.py
- UiBridge
- .build_transcode_args
- httpx
- CoverArtService
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- FakeSlskd
- CI Workflow
- LogConsole
- ._load_selected_into_workbench_and_player
- slskd.py
- themes.py
- cycle_theme
- phase1_analyze
- test_export_progress_callback_granularity
- test_ui_visualizer.py
- P2P candidate scoring
- pytest
- BatchScan
- Any
- BatchConfirmScreen
- asyncio
- yt-dlp metadata probe
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- .wait_for_idle
- mutagen tagging
- yt-dlp failure catalog
- .__init__
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- .__init__
- OmniRip
- .load_audio_frames
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
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- ui/__init__.py
- util/__init__.py
- BatchScan
- CanonicalMetadata
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
- harvester_batch_report
- harvester_batch_scanner
- harvester_batch_trash
- harvester_pipeline_phase4_spectral
- harvester_pipeline_phase5_polish
- harvester_services_enhancement_conservative_provider
- harvester_services_enhancement_flashsr_provider
- harvester_services_enhancement_hybrid_provider
- harvester_services_enhancement_nvsr_provider
- harvester_ui_workbench
- harvester_util_fsatomic
- JobEvent
- Path
- harvester
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
- Text
- Changed
- Pressed
- TrackJob
- Widget
- StreamId
- SubprocessRegistry
- asyncio

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 54 edges
2. `HarvesterApp` - 54 edges
3. `WorkbenchWidget` - 47 edges
4. `ValidationError` - 44 edges
5. `AppConfig` - 42 edges
6. `load_config()` - 40 edges
7. `AudioVisualizer` - 35 edges
8. `CanonicalMetadata` - 33 edges
9. `AudioPlayerWidget` - 33 edges
10. `EnhancementExporter` - 27 edges

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

## Communities (194 total, 80 thin omitted)

### Community 0 - "ValidationError"
Cohesion: 0.05
Nodes (56): harvester_pipeline_phase1_analyze, Process, ProgressCallback, DownloadProgress, ErrorClass, analyze_url(), build_query(), Mode A URL analysis stage. (+48 more)

### Community 1 - "stem_separator.py"
Cohesion: 0.06
Nodes (66): Any, fixture, ndarray, scipy, apply_adaptive_spectral_gate(), apply_inversion_subtraction(), apply_mid_side_vocal_suppression(), apply_vocal_harmonic_polish() (+58 more)

### Community 2 - "config.py"
Cohesion: 0.05
Nodes (57): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+49 more)

### Community 3 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 4 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 5 - "HarvesterApp"
Cohesion: 0.05
Nodes (17): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the Soulseek credentials and configuration dialog., Toggle visualizer between spectrum analyzer and oscilloscope. (+9 more)

### Community 6 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (25): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+17 more)

### Community 7 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 8 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 9 - "FlashSRProvider"
Cohesion: 0.07
Nodes (24): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, Any, ModelManager, ndarray (+16 more)

### Community 10 - "test_model_manager.py"
Cohesion: 0.06
Nodes (29): harvester_analysis_enhancement, importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray (+21 more)

### Community 11 - "ensure_2d_audio"
Cohesion: 0.09
Nodes (32): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+24 more)

### Community 12 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 13 - "AppConfig"
Cohesion: 0.16
Nodes (33): harvester_services_restoration, Restore a trashed original to its original location (FR-13 rollback step)., rollback(), AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch() (+25 more)

### Community 14 - "numpy"
Cohesion: 0.11
Nodes (24): collections_abc, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_model_manager, harvester_ui_screens_curation_workbench, logging, mutagen_id3, numpy (+16 more)

### Community 15 - "EnhancementExporter"
Cohesion: 0.08
Nodes (23): EnhancementPreset, MasteringEQSettings, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB)., Apply a named preset profile., EnhancementExporter (+15 more)

### Community 16 - "._startup"
Cohesion: 0.07
Nodes (14): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PlaylistConfirmScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen (+6 more)

### Community 17 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 18 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 19 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 20 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 21 - "PipelineOrchestrator"
Cohesion: 0.23
Nodes (6): DownloadProgress, Exception, PipelineOrchestrator, TrackJob, Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract.

### Community 22 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 23 - "PreviewManager"
Cohesion: 0.11
Nodes (22): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+14 more)

### Community 24 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 25 - "test_ui_workbench.py"
Cohesion: 0.14
Nodes (25): harvester_ui_player, harvester_ui_visualizer, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench… (+17 more)

### Community 26 - "slskd_config.py"
Cohesion: 0.13
Nodes (24): MonkeyPatch, secrets, find_repo_root(), generate_api_key(), get_slskd_config_path(), get_slskd_template_path(), Path, Management and auto-generation of local slskd configuration and credentials. (+16 more)

### Community 27 - "WorkbenchWidget"
Cohesion: 0.11
Nodes (13): Pressed, ComposeResult, Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Apply active 10-band EQ settings directly to the audio player in real-time., Apply EQ to active playback in real time and debounce background audio re-…, Refresh blend weight value labels after a change., Check or download all AI model weights and show status for all 4 models. (+5 more)

### Community 28 - "app.py"
Cohesion: 0.13
Nodes (20): harvester_analysis_enhancement_eq, harvester_analysis_enhancement_presets, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge (+12 more)

### Community 29 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (16): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields. (+8 more)

### Community 30 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 31 - "State"
Cohesion: 0.14
Nodes (18): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives…, Raise :class:`IllegalTransition` when the transition is not valid. (+10 more)

### Community 32 - "orchestrator.py"
Cohesion: 0.13
Nodes (18): harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_acoustid, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors, harvester_util_retry (+10 more)

### Community 33 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, mutagen, mutagen_flac, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 34 - "logging_setup.py"
Cohesion: 0.13
Nodes (15): logging_handlers, LogRecord, Queue, CallbackHandler, configure_logging(), ContextDefaultsFilter, _level(), LoggingController (+7 more)

### Community 35 - "environment.py"
Cohesion: 0.16
Nodes (13): shlex, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+5 more)

### Community 36 - "test_phase4_spectral.py"
Cohesion: 0.16
Nodes (14): SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., run_spectral_check(), _config(), _FakeFailureFfmpeg, _FakeFfmpeg, _make_job() (+6 more)

### Community 37 - "models.py"
Cohesion: 0.15
Nodes (17): datetime, EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., Return an aware UTC timestamp suitable for persisted events. (+9 more)

### Community 38 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 39 - "test_slskd_config.py"
Cohesion: 0.20
Nodes (14): harvester_services_slskd, harvester_ui_screens_soulseek_login, harvester_util_circuit, respx, Unit and integration tests for Soulseek configuration and in-app credential…, asyncio, Path, test_download_completes_and_locates_file() (+6 more)

### Community 40 - "report.py"
Cohesion: 0.14
Nodes (17): json, BatchReport, job_row(), TrackJob, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries). (+9 more)

### Community 41 - "AcoustidService"
Cohesion: 0.15
Nodes (6): AcoustidService, _metadata_to_json(), AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 42 - "AudioVisualizer"
Cohesion: 0.12
Nodes (10): AudioVisualizer, Widget, Ensure the animation timer is active if paused during idle., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Start active playback visualization., Pause playback visualization., Stop playback visualization and reset to idle. (+2 more)

### Community 43 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 44 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 45 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 46 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 47 - "FfmpegService"
Cohesion: 0.23
Nodes (9): SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+1 more)

### Community 48 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 49 - "test_batch_trash.py"
Cohesion: 0.24
Nodes (17): move_to_trash(), purge(), Path, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Delete trash day-directories older than ``retention_days``; return count.…, trash_root_for(), Path (+9 more)

### Community 50 - "test_bridge.py"
Cohesion: 0.16
Nodes (14): ErrorInfo, coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7). (+6 more)

### Community 51 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 52 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 53 - ".on_select_changed"
Cohesion: 0.16
Nodes (9): Changed, Initiate background stem separation for current track., Generate a short cache tag representing active EQ settings., Asynchronously pre-generate the enhanced derivative., Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, Switch audition stream: [1] MP3, [2] ENH, [3] VOC, or [4] INST. (+1 more)

### Community 54 - "CircuitBreaker"
Cohesion: 0.16
Nodes (10): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+2 more)

### Community 55 - "apply_mastering_eq"
Cohesion: 0.15
Nodes (15): apply_mastering_eq(), ndarray, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Tests for 10-Band Studio Equalizer (Milestone 10-EQ)., Verify that extreme boosts do not exceed ceiling_dbfs., Verify default settings and preset switching., Verify that flat EQ is a transparent near-identity. (+7 more)

### Community 56 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 57 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 58 - "Path"
Cohesion: 0.15
Nodes (8): setter, Path, Run stem separation asynchronously with live progress and route stream when…, Pre-render remaining presets of the active mode so subsequent clicks are…, Route audio stream to player with zero-gap playhead preservation., update_progress(), on_progress(), _ui()

### Community 59 - "ModelManager"
Cohesion: 0.19
Nodes (10): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+2 more)

### Community 60 - "CurationWorkbenchModal"
Cohesion: 0.13
Nodes (9): Open the detailed Curation Workbench modal for the selected job's audio file., CurationWorkbenchModal, Changed, ComposeResult, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App (+1 more)

### Community 61 - ".__init__"
Cohesion: 0.14
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 62 - "pathlib"
Cohesion: 0.17
Nodes (10): dataclasses, hashlib, pathlib, platformdirs, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., Platform-aware runtime directories. (+2 more)

### Community 63 - ".submit_batch"
Cohesion: 0.16
Nodes (12): batch_report_name(), Path, Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3)., skipped_row(), _entry_tags(), BatchScan, Path (+4 more)

### Community 64 - "NVSRProvider"
Cohesion: 0.16
Nodes (9): NVSRProvider, Any, ModelManager, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if neural acceleration is enabled, torch is installed, and weights are… (+1 more)

### Community 65 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 66 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 67 - "._worker_loop"
Cohesion: 0.15
Nodes (7): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested., StageHandler, Task

### Community 68 - "SoulseekLoginModal"
Cohesion: 0.16
Nodes (7): ComposeResult, Path, Interactive modal dialog to enter Soulseek credentials and connect., SoulseekLoginModal, DummyModalApp, ComposeResult, test_soulseek_login_modal_compose()

### Community 69 - "player.py"
Cohesion: 0.21
Nodes (11): collections, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive…, Real-time Audio Visualizer Widget for OmniRip TUI. Provides multi-mode audio…, textual, textual_message (+3 more)

### Community 70 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 71 - "AppPaths"
Cohesion: 0.21
Nodes (9): AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., Path, test_app_paths_are_isolated_and_created(), Path (+1 more)

### Community 72 - "test_acoustid.py"
Cohesion: 0.35
Nodes (9): Fingerprint, _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network(), test_low_confidence_result_is_rejected() (+1 more)

### Community 73 - "logconsole.py"
Cohesion: 0.21
Nodes (10): level_passes(), next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., Log console filter tests (docs/08 §5: INFO -> DEBUG -> WARN+ERROR cycling)., test_level_passes_debug_shows_everything(), test_level_passes_info_hides_debug() (+2 more)

### Community 74 - ".render"
Cohesion: 0.22
Nodes (6): Mode 1: Multi-band Spectrum Analyzer with gravity peaks across 10 mastering…, Mode 3: Symmetrical Center-Mirrored Dance Spectrum., Mode 4: High-density 2x4 Unicode Braille audio wave matrix., Mode 5: Wide Stereo Dual-Deck VU Meter with decibel scales., Mode 2: Analog phosphor audio oscilloscope waveform., Text

### Community 75 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 76 - ".__init__"
Cohesion: 0.17
Nodes (9): AcoustidService, CoverArtService, EventKind, SlskdService, JobEvent, MetadataTagger, Queue, SubprocessRegistry (+1 more)

### Community 77 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 78 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 79 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 80 - "acoustid.py"
Cohesion: 0.38
Nodes (11): sqlite3, _earliest_release(), _metadata_from_json(), _number(), Any, AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache., Parse a numeric field as an integer (years and similar); None when not numeric., _release_year() (+3 more)

### Community 81 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 82 - ".build_transcode_args"
Cohesion: 0.22
Nodes (7): harvester_services_ffmpeg, Build the deterministic Phase 5 transcode arguments., Path, test_build_mp3_320_arguments(), test_build_mp3_v0_arguments(), test_keep_opus_is_not_an_mp3_transcode(), test_probe_audio_info_cache()

### Community 83 - "httpx"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 84 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 85 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 86 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 87 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 88 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 89 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (8): harvester_pipeline, _job(), Path, TrackJob, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 90 - "FakeSlskd"
Cohesion: 0.31
Nodes (3): SearchResponse, SlskdFile, FakeSlskd

### Community 91 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 92 - "LogConsole"
Cohesion: 0.25
Nodes (4): RichLog, LogConsole, A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter.

### Community 93 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 94 - "slskd.py"
Cohesion: 0.47
Nodes (8): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., _text()

### Community 95 - "themes.py"
Cohesion: 0.25
Nodes (6): Theme registry and dynamic switcher for OmniRip TUI., ComposeResult, Unit tests for theme registry and dynamic cycling., test_theme_registry_and_cycling(), ThemeTestApp, textual_theme

### Community 96 - "cycle_theme"
Cohesion: 0.29
Nodes (6): App, Cycle to next dynamic color theme., cycle_theme(), Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes()

### Community 97 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 98 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 99 - "test_ui_visualizer.py"
Cohesion: 0.29
Nodes (6): ComposeResult, Unit tests for AudioVisualizer widget across all 5 visualizer modes., Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler., test_audio_visualizer_10bands_and_full_width_ruler(), test_audio_visualizer_modes_and_render(), VisualizerTestApp

### Community 100 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 101 - "pytest"
Cohesion: 0.33
Nodes (5): os, pytest, Tracked subprocess lifecycle helpers for cancellation-safe services., asyncio, test_registry_terminates_process_by_job_prefix()

### Community 102 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 104 - "BatchConfirmScreen"
Cohesion: 0.33
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 105 - "asyncio"
Cohesion: 0.47
Nodes (6): asyncio, mock, check_soulseek_status(), Query local slskd daemon session and Soulseek network connection status., test_check_soulseek_status_connected(), test_check_soulseek_status_unauthorized()

### Community 106 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 107 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 108 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 109 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 110 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 112 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 113 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 114 - ".__init__"
Cohesion: 0.50
Nodes (3): EnhancementExporter, PreviewManager, Path

### Community 115 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 968 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkbenchWidget` connect `WorkbenchWidget` to `stem_separator.py`, `HarvesterApp`, `EnhancementExporter`, `._startup`, `.on_select_changed`, `test_ui_workbench.py`, `Path`, `app.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `cycle_theme`, `config.py`, `BatchConfirmScreen`, `__main__.py`, `CurationWorkbenchModal`, `._startup`, `.__init__`, `test_ui_pilot.py`, `WorkbenchWidget`, `app.py`, `._load_selected_into_workbench_and_player`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `orchestrator.py`, `ValidationError`, `config.py`, `environment.py`, `scanner.py`, `test_phase4_spectral.py`, `analysis/restoration.py`, `AcoustidService`, `.__init__`, `FfmpegService`, `acoustid.py`, `httpx`, `CoverArtService`, `PipelineOrchestrator`, `SlskdService`, `slskd.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `StemSeparator`) actually correct?**
  _`WorkbenchWidget` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._