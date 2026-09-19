# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2411 nodes · 4761 edges · 192 communities (108 shown, 84 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 493 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `60470f51`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PipelineOrchestrator
- test_orchestrator_m5.py
- AudioPlayerWidget
- acoustid.py
- scanner.py
- FlashSRProvider
- Milestone M7 — QA & packaging
- HarvesterApp
- WorkbenchWidget
- analysis/restoration.py
- ensure_2d_audio
- pathlib
- test_model_manager.py
- test_spectral.py
- test_playlist.py
- app.py
- read_slskd_credentials
- AppConfig
- test_orchestrator_m4.py
- TrackJob
- models.py
- test_enhancement_workbench.py
- numpy
- Harvester (Hybrid Music Harvest & Curation Engine)
- FfmpegService
- ._separate_bs_roformer
- test_orchestrator_m2.py
- workbench.py
- test_phase4_spectral.py
- MasteringEQSettings
- ytdlp.py
- StemSeparator
- phase1_analyze.py
- AudioVisualizer
- test_ui_workbench.py
- test_batch_trash.py
- Pipeline orchestrator
- logging_setup.py
- LogConsole
- Phase 1 — Input Analysis
- test_stem_separator.py
- yt-dlp
- CurationWorkbenchModal
- test_slskd_config.py
- Spectral fixture connectivity gap
- titleclean.py
- AppPaths
- ValidationError
- QualityEvidence
- scoring.py
- ModelManager
- CoverArtService
- test_orchestrator_m3.py
- config.py
- SlskdService
- test_ui_pilot.py
- EnhancementExporter
- JobTable
- Textual TUI
- tagging.py
- test_bridge.py
- CircuitBreaker
- textual_app
- slskd.py
- Minimal Implementation Ladder
- .__init__
- phase2_hunt
- load_config
- errors.py
- test_orchestrator.py
- Mode B — Local Batch Audit
- .render
- test_phase5_polish.py
- __main__.py
- Phase 5 — Polish and Sync
- retry.py
- Mode
- ._startup
- DependencyStatus
- UiBridge
- ConfigError
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- persist_first_run_acceptance
- CanonicalMetadata
- Any
- .parse_progress
- CI Workflow
- ._load_selected_into_workbench_and_player
- phase1_analyze
- BatchConfirmScreen
- test_ui_visualizer.py
- P2P candidate scoring
- BatchScan
- yt-dlp metadata probe
- QuitConfirmScreen
- PlaylistConfirmScreen
- FakeSlskdOffline
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- .compose
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- pytest
- presets.py
- .__init__
- update_progress
- FakeCover
- FakeSlskd
- FakeTagger
- OmniRip
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
- ComposeResult
- Pressed
- TrackJob
- Widget
- StreamId
- SubprocessRegistry
- asyncio

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 54 edges
2. `HarvesterApp` - 54 edges
3. `WorkbenchWidget` - 45 edges
4. `ValidationError` - 44 edges
5. `AppConfig` - 42 edges
6. `load_config()` - 40 edges
7. `AudioVisualizer` - 35 edges
8. `AudioPlayerWidget` - 33 edges
9. `CanonicalMetadata` - 33 edges
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

## Communities (192 total, 84 thin omitted)

### Community 0 - "PipelineOrchestrator"
Cohesion: 0.05
Nodes (47): AcoustidService, CoverArtService, DownloadProgress, EventKind, Exception, P2PCandidate, SlskdService, _entry_tags() (+39 more)

### Community 1 - "test_orchestrator_m5.py"
Cohesion: 0.05
Nodes (40): BatchReport, job_row(), TrackJob, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4)., Path (+32 more)

### Community 2 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 3 - "acoustid.py"
Cohesion: 0.07
Nodes (30): harvester_services_acoustid, Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json() (+22 more)

### Community 4 - "scanner.py"
Cohesion: 0.08
Nodes (51): BatchEntry, mutagen, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack (+43 more)

### Community 5 - "FlashSRProvider"
Cohesion: 0.05
Nodes (31): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, Any, ModelManager, ndarray (+23 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "HarvesterApp"
Cohesion: 0.06
Nodes (17): FlushPlan, HarvesterApp, Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Open the Soulseek credentials and configuration dialog., Toggle visualizer between spectrum analyzer and oscilloscope. (+9 more)

### Community 8 - "WorkbenchWidget"
Cohesion: 0.09
Nodes (22): Changed, Pressed, setter, Path, Generate a short cache tag representing active EQ settings., Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Apply active 10-band EQ settings directly to the audio player in real-time. (+14 more)

### Community 9 - "analysis/restoration.py"
Cohesion: 0.10
Nodes (34): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+26 more)

### Community 10 - "ensure_2d_audio"
Cohesion: 0.08
Nodes (34): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+26 more)

### Community 11 - "pathlib"
Cohesion: 0.08
Nodes (32): Any, asyncio, harvester_analysis, harvester_analysis_scoring, harvester_analysis_titleclean, harvester_pipeline_phase2_hunt, harvester_services_musicbrainz, harvester_services_slskd (+24 more)

### Community 12 - "test_model_manager.py"
Cohesion: 0.06
Nodes (30): harvester_analysis_enhancement, hashlib, importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider (+22 more)

### Community 13 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 14 - "test_playlist.py"
Cohesion: 0.10
Nodes (16): harvester_util_circuit, _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+8 more)

### Community 15 - "app.py"
Cohesion: 0.07
Nodes (20): harvester_pipeline_orchestrator, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge, harvester_ui_logconsole, harvester_ui_player, harvester_ui_themes, harvester_util_logging_setup (+12 more)

### Community 16 - "read_slskd_credentials"
Cohesion: 0.09
Nodes (26): MonkeyPatch, find_repo_root(), get_slskd_config_path(), get_slskd_template_path(), Path, Locate the OmniRip repository root directory., Attempt to start or restart the local slskd daemon process., Return path to tools/slskd/slskd.local.yml. (+18 more)

### Community 17 - "AppConfig"
Cohesion: 0.17
Nodes (31): harvester_services_restoration, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac(), _polish_mp3() (+23 more)

### Community 18 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 19 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 20 - "models.py"
Cohesion: 0.10
Nodes (25): enum, RuntimeError, JobEvent, Domain models shared by the pipeline, services, and UI., Apply one guarded state transition through the canonical state machine., Return an aware UTC timestamp suitable for persisted events., utc_now(), assert_transition() (+17 more)

### Community 21 - "test_enhancement_workbench.py"
Cohesion: 0.09
Nodes (25): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+17 more)

### Community 22 - "numpy"
Cohesion: 0.14
Nodes (20): collections_abc, dataclasses, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_model_manager, logging, numpy, platform (+12 more)

### Community 23 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 24 - "FfmpegService"
Cohesion: 0.13
Nodes (16): harvester_services_ffmpeg, SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass. (+8 more)

### Community 25 - "._separate_bs_roformer"
Cohesion: 0.12
Nodes (24): ndarray, apply_adaptive_spectral_gate(), apply_inversion_subtraction(), apply_vocal_harmonic_polish(), load_audio_numpy(), Path, Apply natural vocal envelope leveling and gentle inter-phrase silence…, Smooth vocal dynamics and limit peak overs without phase degradation or robotic… (+16 more)

### Community 26 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 27 - "workbench.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_enhancement_eq, harvester_analysis_enhancement_presets, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_ui_visualizer, math, rich_style, rich_text (+13 more)

### Community 28 - "test_phase4_spectral.py"
Cohesion: 0.13
Nodes (18): excerpt_window(), _excerpt_window(), SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2., run_spectral_check(), _config() (+10 more)

### Community 29 - "MasteringEQSettings"
Cohesion: 0.11
Nodes (20): apply_mastering_eq(), MasteringEQSettings, ndarray, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+12 more)

### Community 30 - "ytdlp.py"
Cohesion: 0.11
Nodes (20): collections, os, re, secrets, shlex, shutil, probe_binary(), Asynchronous startup checks for local binaries and optional services. (+12 more)

### Community 31 - "StemSeparator"
Cohesion: 0.11
Nodes (23): fixture, Multi-stage audio stem separation and de-bleeding service., StemSeparator, Path, Test that BS-RoFormer failure falls back to HDEMUCS when available., Verify progress callback reports steps and percentages monotonically., Verify different songs maintain isolated caches without collisions., Verify BS-RoFormer inference produces isolated vocal and instrumental stems. (+15 more)

### Community 32 - "phase1_analyze.py"
Cohesion: 0.12
Nodes (20): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+12 more)

### Community 33 - "AudioVisualizer"
Cohesion: 0.10
Nodes (12): AudioVisualizer, Path, Widget, Ensure the animation timer is active if paused during idle., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses in-memory…, Start active playback visualization. (+4 more)

### Community 34 - "test_ui_workbench.py"
Cohesion: 0.15
Nodes (22): ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer. (+14 more)

### Community 35 - "test_batch_trash.py"
Cohesion: 0.19
Nodes (21): datetime, move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step). (+13 more)

### Community 36 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 37 - "logging_setup.py"
Cohesion: 0.13
Nodes (15): logging_handlers, LogRecord, Queue, CallbackHandler, configure_logging(), ContextDefaultsFilter, _level(), LoggingController (+7 more)

### Community 38 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 39 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 40 - "test_stem_separator.py"
Cohesion: 0.10
Nodes (18): Path, Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify that EnhancementExporter toggles neural acceleration across all…, Verify all 5 planned presets exist and have valid attributes., Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify render_audio_buffer produces valid audio for every preset., Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file. (+10 more)

### Community 41 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 42 - "CurationWorkbenchModal"
Cohesion: 0.11
Nodes (12): EnhancementExporter, PreviewManager, Open the detailed Curation Workbench modal for the selected job's audio file., CurationWorkbenchModal, Changed, ComposeResult, Path, Pressed (+4 more)

### Community 43 - "test_slskd_config.py"
Cohesion: 0.22
Nodes (13): harvester_ui_screens_soulseek_login, httpx, respx, Unit and integration tests for Soulseek configuration and in-app credential…, asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route() (+5 more)

### Community 44 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 45 - "titleclean.py"
Cohesion: 0.17
Nodes (17): Match, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase…, NFKD-normalize and fold diacritics to ASCII while keeping the case. (+9 more)

### Community 46 - "AppPaths"
Cohesion: 0.14
Nodes (12): platformdirs, AppPaths, Path, Platform-aware runtime directories., All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., Path (+4 more)

### Community 47 - "ValidationError"
Cohesion: 0.20
Nodes (10): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+2 more)

### Community 48 - "QualityEvidence"
Cohesion: 0.22
Nodes (15): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+7 more)

### Community 49 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 50 - "ModelManager"
Cohesion: 0.16
Nodes (11): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+3 more)

### Community 51 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 52 - "test_orchestrator_m3.py"
Cohesion: 0.19
Nodes (8): _build(), FakeAcoustid, FakeFfmpeg, FakeYtdlp, asyncio, Path, test_ground_truth_metadata_reaches_flac_output(), test_no_match_falls_back_to_probe_metadata()

### Community 53 - "config.py"
Cohesion: 0.18
Nodes (17): AppPaths, copy, AcoustidConfig, BatchConfig, _build_config(), section(), FfmpegConfig, GeneralConfig (+9 more)

### Community 54 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 55 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 56 - "EnhancementExporter"
Cohesion: 0.20
Nodes (11): EnhancementPreset, EnhancementExporter, ndarray, Path, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+3 more)

### Community 57 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 58 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 59 - "tagging.py"
Cohesion: 0.22
Nodes (14): mutagen_flac, mutagen_id3, soundfile, metadata_from_probe(), Any, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields., _text() (+6 more)

### Community 60 - "test_bridge.py"
Cohesion: 0.19
Nodes (13): coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7)., test_bridge_coalesces_1000_event_storm_into_one_flush() (+5 more)

### Community 61 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 62 - "textual_app"
Cohesion: 0.19
Nodes (12): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+4 more)

### Community 63 - "slskd.py"
Cohesion: 0.28
Nodes (10): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+2 more)

### Community 64 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 65 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 66 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 67 - "load_config"
Cohesion: 0.22
Nodes (12): _deep_merge(), load_config(), _load_toml(), Path, Load config with precedence CLI > environment > TOML > defaults., Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected() (+4 more)

### Community 68 - "errors.py"
Cohesion: 0.29
Nodes (12): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+4 more)

### Community 69 - "test_orchestrator.py"
Cohesion: 0.27
Nodes (7): FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path, test_orchestrator_cancel_marks_job_cancelled(), test_orchestrator_runs_fallback_path_with_fake_services()

### Community 70 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 71 - ".render"
Cohesion: 0.22
Nodes (6): Mode 1: Multi-band Spectrum Analyzer with gravity peaks across 10 mastering…, Mode 3: Symmetrical Center-Mirrored Dance Spectrum., Mode 4: High-density 2x4 Unicode Braille audio wave matrix., Mode 5: Wide Stereo Dual-Deck VU Meter with decibel scales., Mode 2: Analog phosphor audio oscilloscope waveform., Text

### Community 72 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 73 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 74 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 75 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 76 - "Mode"
Cohesion: 0.23
Nodes (11): EventKind, Mode, StrEnum, Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, SourceKind, Verdict, test_canonical_metadata_normalizes_artists_and_serializes() (+3 more)

### Community 77 - "._startup"
Cohesion: 0.23
Nodes (5): check_slskd(), detect_environment(), Check slskd health and, optionally, whether its OpenAPI endpoint is reachable., Run independent dependency checks concurrently., wrapped()

### Community 78 - "DependencyStatus"
Cohesion: 0.26
Nodes (4): DependencyStatus, EnvironmentStatus, test_all_required_dependencies_ready_when_optional_services_are_down(), test_required_dependency_controls_ready_state()

### Community 79 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 80 - "ConfigError"
Cohesion: 0.31
Nodes (9): _apply_environment(), _bool(), _float(), _int(), Any, Validate cross-field invariants and return this config for fluent use., Return diagnostic configuration without exposing secret values., _set_dotted() (+1 more)

### Community 81 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 82 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 83 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 84 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 85 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (8): harvester_pipeline, _job(), Path, TrackJob, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 86 - "persist_first_run_acceptance"
Cohesion: 0.40
Nodes (9): persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general(), test_persist_replaces_existing_value() (+1 more)

### Community 87 - "CanonicalMetadata"
Cohesion: 0.36
Nodes (4): CanonicalMetadata, MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art.

### Community 88 - "Any"
Cohesion: 0.20
Nodes (3): ErrorInfo, Any, SpectralResult

### Community 89 - ".parse_progress"
Cohesion: 0.29
Nodes (8): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), YtdlpProgress, test_progress_parser_handles_machine_readable_line(), test_progress_parser_ignores_unrelated_lines()

### Community 90 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 91 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 92 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 93 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 94 - "test_ui_visualizer.py"
Cohesion: 0.29
Nodes (6): ComposeResult, Unit tests for AudioVisualizer widget across all 5 visualizer modes., Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler., test_audio_visualizer_10bands_and_full_width_ruler(), test_audio_visualizer_modes_and_render(), VisualizerTestApp

### Community 95 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 96 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 97 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 101 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 102 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 103 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 104 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 106 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 107 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 108 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 109 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

### Community 110 - "presets.py"
Cohesion: 0.50
Nodes (3): EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

### Community 112 - "update_progress"
Cohesion: 0.50
Nodes (3): update_progress(), on_progress(), _ui()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 958 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **84 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkbenchWidget` connect `WorkbenchWidget` to `test_ui_workbench.py`, `HarvesterApp`, `.compose`, `app.py`, `ModelManager`, `test_enhancement_workbench.py`, `workbench.py`, `StemSeparator`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `PipelineOrchestrator`, `load_config`, `scanner.py`, `acoustid.py`, `analysis/restoration.py`, `pathlib`, `._startup`, `ValidationError`, `ConfigError`, `CoverArtService`, `config.py`, `persist_first_run_acceptance`, `SlskdService`, `FfmpegService`, `test_phase4_spectral.py`, `ytdlp.py`, `slskd.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `.__init__`, `QuitConfirmScreen`, `load_config`, `WorkbenchWidget`, `__main__.py`, `CurationWorkbenchModal`, `._startup`, `app.py`, `test_ui_pilot.py`, `._load_selected_into_workbench_and_player`, `BatchConfirmScreen`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `StemSeparator`) actually correct?**
  _`WorkbenchWidget` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._