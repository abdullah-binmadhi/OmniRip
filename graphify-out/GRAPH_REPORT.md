# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- 136 files · ~314,348 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .toml 1, .tcss 1)

## Summary
- 2413 nodes · 4764 edges · 189 communities (108 shown, 81 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 493 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `306e1463`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PipelineOrchestrator
- test_orchestrator_m5.py
- AudioPlayerWidget
- acoustid.py
- scanner.py
- numpy
- Milestone M7 — QA & packaging
- HarvesterApp
- WorkbenchWidget
- analysis/restoration.py
- ensure_2d_audio
- orchestrator.py
- test_model_manager.py
- test_spectral.py
- test_playlist.py
- ComposeResult
- slskd_config.py
- AppConfig
- test_orchestrator_m4.py
- TrackJob
- State
- PreviewManager
- .on_select_changed
- Harvester (Hybrid Music Harvest & Curation Engine)
- FfmpegService
- Path
- test_orchestrator_m2.py
- app.py
- test_phase4_spectral.py
- MasteringEQSettings
- yt-dlp
- StemSeparator
- phase1_analyze.py
- AudioVisualizer
- test_ui_workbench.py
- test_batch_trash.py
- Pipeline orchestrator
- pathlib
- LogConsole
- Phase 1 — Input Analysis
- EnhancementExporter
- slskd daemon
- ._startup
- test_slskd_config.py
- Spectral fixture connectivity gap
- titleclean.py
- test_enhancement_workbench.py
- ValidationError
- QualityEvidence
- scoring.py
- ModelManager
- CoverArtService
- test_orchestrator_m3.py
- config.py
- SlskdService
- test_ui_pilot.py
- report.py
- JobTable
- Textual TUI
- tagging.py
- test_bridge.py
- CircuitBreaker
- .on_button_pressed
- slskd.py
- Minimal Implementation Ladder
- .__init__
- phase2_hunt
- test_enhancement_dsp.py
- errors.py
- __main__.py
- Mode B — Local Batch Audit
- retry.py
- test_phase5_polish.py
- SoulseekLoginModal
- Phase 5 — Polish and Sync
- .build_transcode_args
- models.py
- test_export_progress_callback_granularity
- environment.py
- UiBridge
- asyncio
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- State machine
- CanonicalMetadata
- Any
- ytdlp.py
- CI Workflow
- ._load_selected_into_workbench_and_player
- phase1_analyze
- BatchConfirmScreen
- .generate_residual
- P2P candidate scoring
- BatchScan
- phase5_polish
- .generate_residual
- PlaylistConfirmScreen
- FirstRunNoticeScreen
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- .on_button_pressed
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- pytest
- .__init__
- generate_api_key
- update_progress
- ComposeResult
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
- .__init__

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 54 edges
2. `HarvesterApp` - 54 edges
3. `WorkbenchWidget` - 46 edges
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

## Communities (189 total, 81 thin omitted)

### Community 0 - "PipelineOrchestrator"
Cohesion: 0.05
Nodes (49): AcoustidService, CoverArtService, DownloadProgress, EventKind, Exception, harvester_analysis_scoring, harvester_analysis_titleclean, mutagen (+41 more)

### Community 1 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (25): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+17 more)

### Community 2 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 3 - "acoustid.py"
Cohesion: 0.07
Nodes (29): Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+21 more)

### Community 4 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 5 - "numpy"
Cohesion: 0.07
Nodes (34): collections_abc, EnhancementProvider, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_enhancement, harvester_services_model_manager, logging, numpy (+26 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "HarvesterApp"
Cohesion: 0.07
Nodes (13): FlushPlan, HarvesterApp, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Toggle visualizer between spectrum analyzer and oscilloscope., Seek backward 5 seconds in player., Seek forward 5 seconds in player., Seek backward 15 seconds in player. (+5 more)

### Community 8 - "WorkbenchWidget"
Cohesion: 0.16
Nodes (10): setter, Path, Generate a short cache tag representing active EQ settings., Pre-render remaining presets of the active mode so subsequent clicks are…, Route audio stream to player with zero-gap playhead preservation., Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., In-page audio enhancement and auditioning workbench panel. Supports real-time…, Run stem separation asynchronously with live progress and route stream when… (+2 more)

### Community 9 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 10 - "ensure_2d_audio"
Cohesion: 0.17
Nodes (18): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+10 more)

### Community 11 - "orchestrator.py"
Cohesion: 0.11
Nodes (19): harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_acoustid, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors, harvester_util_retry (+11 more)

### Community 12 - "test_model_manager.py"
Cohesion: 0.06
Nodes (29): harvester_analysis_enhancement, hashlib, importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider (+21 more)

### Community 13 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 14 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 15 - "ComposeResult"
Cohesion: 0.09
Nodes (10): FatalSetupScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17). (+2 more)

### Community 16 - "slskd_config.py"
Cohesion: 0.15
Nodes (21): MonkeyPatch, secrets, find_repo_root(), get_slskd_config_path(), get_slskd_template_path(), Path, Management and auto-generation of local slskd configuration and credentials., Locate the OmniRip repository root directory. (+13 more)

### Community 17 - "AppConfig"
Cohesion: 0.21
Nodes (26): harvester_services_restoration, Restore a trashed original to its original location (FR-13 rollback step)., rollback(), AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch() (+18 more)

### Community 18 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 19 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 20 - "State"
Cohesion: 0.13
Nodes (19): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives…, Raise :class:`IllegalTransition` when the transition is not valid. (+11 more)

### Community 21 - "PreviewManager"
Cohesion: 0.06
Nodes (34): EnhancementExporter, Popen, PreviewManager, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes… (+26 more)

### Community 22 - ".on_select_changed"
Cohesion: 0.15
Nodes (9): Changed, Apply active 10-band EQ settings directly to the audio player in real-time., Apply EQ to active playback in real time and debounce background audio re-…, Asynchronously pre-generate the enhanced derivative., Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, Switch audition stream: [1] MP3, [2] ENH, [3] VOC, or [4] INST., Initiate background stem separation for current track. (+1 more)

### Community 23 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.11
Nodes (25): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID (+17 more)

### Community 24 - "FfmpegService"
Cohesion: 0.19
Nodes (12): SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+4 more)

### Community 26 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 27 - "app.py"
Cohesion: 0.07
Nodes (37): collections, harvester_analysis_enhancement_eq, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge (+29 more)

### Community 28 - "test_phase4_spectral.py"
Cohesion: 0.14
Nodes (16): _excerpt_window(), SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., run_spectral_check(), _config(), _FakeFailureFfmpeg, _FakeFfmpeg (+8 more)

### Community 29 - "MasteringEQSettings"
Cohesion: 0.10
Nodes (21): apply_mastering_eq(), MasteringEQSettings, ndarray, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer. (+13 more)

### Community 30 - "yt-dlp"
Cohesion: 0.14
Nodes (15): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D10 — Playlist cap 50 + confirmation, D3 — Spectral check scope: P2P lossless claims only, FR-1 — Extract metadata without downloading, FR-10 — Provenance-based spectral exemption, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback (+7 more)

### Community 31 - "StemSeparator"
Cohesion: 0.07
Nodes (50): fixture, ndarray, scipy, apply_adaptive_spectral_gate(), apply_inversion_subtraction(), apply_vocal_harmonic_polish(), load_audio_numpy(), Path (+42 more)

### Community 32 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+11 more)

### Community 33 - "AudioVisualizer"
Cohesion: 0.06
Nodes (26): AudioVisualizer, Path, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses in-memory… (+18 more)

### Community 34 - "test_ui_workbench.py"
Cohesion: 0.14
Nodes (23): harvester_ui_visualizer, ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench… (+15 more)

### Community 35 - "test_batch_trash.py"
Cohesion: 0.24
Nodes (17): move_to_trash(), purge(), Path, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Delete trash day-directories older than ``retention_days``; return count.…, trash_root_for(), Path (+9 more)

### Community 36 - "Pipeline orchestrator"
Cohesion: 0.19
Nodes (14): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+6 more)

### Community 37 - "pathlib"
Cohesion: 0.06
Nodes (34): dataclasses, logging_handlers, LogRecord, pathlib, platformdirs, Queue, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10. (+26 more)

### Community 38 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 39 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (25): Atomic filesystem helpers, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+17 more)

### Community 40 - "EnhancementExporter"
Cohesion: 0.13
Nodes (18): EnhancementPreset, EnhancementExporter, ndarray, Path, Apply complete enhancement DSP pipeline to in-memory audio array. Pipeline: 1.…, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers. (+10 more)

### Community 41 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 42 - "._startup"
Cohesion: 0.17
Nodes (3): wrapped(), Changed, Submitted

### Community 43 - "test_slskd_config.py"
Cohesion: 0.19
Nodes (15): harvester_services_slskd, harvester_ui_screens_soulseek_login, harvester_util_circuit, httpx, respx, Unit and integration tests for Soulseek configuration and in-app credential…, asyncio, Path (+7 more)

### Community 44 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 45 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 46 - "test_enhancement_workbench.py"
Cohesion: 0.18
Nodes (11): harvester_analysis_enhancement_presets, harvester_ui_screens_curation_workbench, mutagen_id3, platform, Headless preview generation and system audio player dispatch for OmniRip M10., Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify all 5 planned presets exist and have valid attributes., test_presets_coverage() (+3 more)

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
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 53 - "config.py"
Cohesion: 0.05
Nodes (57): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+49 more)

### Community 54 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 55 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 56 - "report.py"
Cohesion: 0.10
Nodes (25): datetime, json, batch_report_name(), BatchReport, job_row(), Path, TrackJob, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14). (+17 more)

### Community 57 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 58 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 59 - "tagging.py"
Cohesion: 0.23
Nodes (13): mutagen_flac, soundfile, metadata_from_probe(), Any, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields., _text(), _year() (+5 more)

### Community 60 - "test_bridge.py"
Cohesion: 0.16
Nodes (14): ErrorInfo, coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7). (+6 more)

### Community 61 - "CircuitBreaker"
Cohesion: 0.16
Nodes (10): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+2 more)

### Community 62 - ".on_button_pressed"
Cohesion: 0.16
Nodes (10): App, Cycle to next dynamic color theme., Open the Soulseek credentials and configuration dialog., cycle_theme(), Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult (+2 more)

### Community 63 - "slskd.py"
Cohesion: 0.20
Nodes (11): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+3 more)

### Community 64 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 65 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 66 - "phase2_hunt"
Cohesion: 0.29
Nodes (7): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, Concurrent download semaphore

### Community 67 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 68 - "errors.py"
Cohesion: 0.29
Nodes (12): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+4 more)

### Community 69 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 70 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 71 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 72 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 73 - "SoulseekLoginModal"
Cohesion: 0.16
Nodes (7): ComposeResult, Path, Interactive modal dialog to enter Soulseek credentials and connect., SoulseekLoginModal, DummyModalApp, ComposeResult, test_soulseek_login_modal_compose()

### Community 74 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 75 - ".build_transcode_args"
Cohesion: 0.22
Nodes (7): harvester_services_ffmpeg, Build the deterministic Phase 5 transcode arguments., Path, test_build_mp3_320_arguments(), test_build_mp3_v0_arguments(), test_keep_opus_is_not_an_mp3_transcode(), test_probe_audio_info_cache()

### Community 76 - "models.py"
Cohesion: 0.19
Nodes (14): EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, SourceKind (+6 more)

### Community 77 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 78 - "environment.py"
Cohesion: 0.17
Nodes (12): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable. (+4 more)

### Community 79 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 80 - "asyncio"
Cohesion: 0.38
Nodes (7): Any, asyncio, mock, check_soulseek_status(), Query local slskd daemon session and Soulseek network connection status., test_check_soulseek_status_connected(), test_check_soulseek_status_unauthorized()

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
Cohesion: 0.17
Nodes (15): harvester_pipeline, atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename., _job() (+7 more)

### Community 86 - "State machine"
Cohesion: 0.29
Nodes (7): State machine, Title cleaning analysis, Fallback anti-loop guard, IllegalTransition, Unit test plan, State-machine truth directive, Tests alongside every module

### Community 87 - "CanonicalMetadata"
Cohesion: 0.36
Nodes (4): CanonicalMetadata, MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art.

### Community 89 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

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

### Community 94 - ".generate_residual"
Cohesion: 0.40
Nodes (3): Any, ndarray, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 95 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 96 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 97 - "phase5_polish"
Cohesion: 0.40
Nodes (5): Batch report writer, FFmpeg service, phase5_polish, q_polish stage queue, Tagging service

### Community 98 - ".generate_residual"
Cohesion: 0.33
Nodes (4): Any, ndarray, Internal inference wrapper., Generate high-frequency residual using NVSR, isolating strictly the band >…

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

### Community 105 - ".on_button_pressed"
Cohesion: 0.18
Nodes (6): Pressed, ComposeResult, Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Refresh blend weight value labels after a change., Render a 13-line vertical studio fader rail with center 0dB line, calibration…

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
Cohesion: 0.33
Nodes (5): os, pytest, Tracked subprocess lifecycle helpers for cancellation-safe services., asyncio, test_registry_terminates_process_by_job_prefix()

### Community 111 - "generate_api_key"
Cohesion: 0.67
Nodes (3): generate_api_key(), Generate a cryptographically secure 32-byte hex secret (64 characters)., test_generate_api_key()

### Community 112 - "update_progress"
Cohesion: 0.50
Nodes (3): update_progress(), on_progress(), _ui()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 959 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **81 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EnhancementExporter` connect `EnhancementExporter` to `numpy`, `__main__.py`, `WorkbenchWidget`, `test_export_progress_callback_granularity`, `test_enhancement_workbench.py`, `PreviewManager`, `MasteringEQSettings`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `.__init__`, `__main__.py`, `WorkbenchWidget`, `._startup`, `._load_selected_into_workbench_and_player`, `ComposeResult`, `PreviewManager`, `config.py`, `test_ui_pilot.py`, `app.py`, `BatchConfirmScreen`, `.on_button_pressed`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `AudioPlayerWidget` connect `AudioPlayerWidget` to `AudioVisualizer`, `test_ui_workbench.py`, `app.py`, `ComposeResult`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `StemSeparator`) actually correct?**
  _`WorkbenchWidget` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._