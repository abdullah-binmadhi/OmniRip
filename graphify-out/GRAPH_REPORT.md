# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- 130 files · ~161,766 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .toml 1, .tcss 1)

## Summary
- 2285 nodes · 4514 edges · 199 communities (108 shown, 91 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 474 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5f814e11`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- scanner.py
- test_orchestrator_m5.py
- P2PCandidate
- ensure_2d_audio
- MasteringEQSettings
- Milestone M7 — QA & packaging
- AppPaths
- AudioVisualizer
- models.py
- PreviewManager
- WorkbenchWidget
- analysis/restoration.py
- HybridCoOpProvider
- HarvesterApp
- AudioPlayerWidget
- test_spectral.py
- test_playlist.py
- test_orchestrator_m4.py
- TrackJob
- pathlib
- numpy
- orchestrator.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- config.py
- FfmpegService
- UiBridge
- test_orchestrator_m2.py
- ComposeResult
- test_phase4_spectral.py
- polish_batch
- CanonicalMetadata
- test_batch_trash.py
- Pipeline orchestrator
- phase2_hunt.py
- test_phase1_analyze.py
- LogConsole
- DependencyStatus
- _build
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
- test_export_progress_callback_granularity
- PipelineOrchestrator
- test_ui_pilot.py
- test_batch_scanner.py
- Mode
- JobTable
- Textual TUI
- ModelManager
- CircuitBreaker
- themes.py
- .__init__
- .parse_progress
- Minimal Implementation Ladder
- phase2_hunt
- TrackJob
- SlskdService
- .__init__
- Mode B — Local Batch Audit
- EnhancementExporter
- QualityEvidence
- .__init__
- __main__.py
- Phase 5 — Polish and Sync
- titleclean.py
- _parse_search_payload
- AppConfig
- persist_first_run_acceptance
- CoverArtService
- test_slskd.py
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- .submit_batch
- FlashSRProvider
- CI Workflow
- ._load_selected_into_workbench_and_player
- FakeSlskd
- phase1_analyze
- BatchConfirmScreen
- P2P candidate scoring
- pytest
- BatchScan
- NVSRProvider
- retry.py
- ._put_event
- yt-dlp metadata probe
- PlaylistConfirmScreen
- FlushPlan
- test_ui_player.py
- test_enhancement_provider_protocol_check
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- ._update_eq_ui
- check_enhancement_available
- presets.py
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
- asyncio
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- Path
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
- harvester_ui_bridge
- harvester_ui_logconsole
- harvester_ui_player
- harvester_ui_visualizer
- harvester_ui_workbench
- harvester_util_fsatomic
- JobEvent
- ndarray
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

## Communities (199 total, 91 thin omitted)

### Community 0 - "scanner.py"
Cohesion: 0.13
Nodes (27): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+19 more)

### Community 1 - "test_orchestrator_m5.py"
Cohesion: 0.06
Nodes (37): BatchReport, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Path, Batch report tests: schema, incremental appends, row builders (FR-14)., test_append_writes_all_schema_fields(), test_appends_are_incremental_and_order_preserved() (+29 more)

### Community 2 - "P2PCandidate"
Cohesion: 0.22
Nodes (18): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+10 more)

### Community 3 - "ensure_2d_audio"
Cohesion: 0.09
Nodes (33): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+25 more)

### Community 4 - "MasteringEQSettings"
Cohesion: 0.11
Nodes (20): apply_mastering_eq(), MasteringEQSettings, ndarray, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+12 more)

### Community 5 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 6 - "AppPaths"
Cohesion: 0.08
Nodes (22): LogRecord, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., CallbackHandler, configure_logging() (+14 more)

### Community 7 - "AudioVisualizer"
Cohesion: 0.06
Nodes (26): AudioVisualizer, Path, Text, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels. (+18 more)

### Community 8 - "models.py"
Cohesion: 0.12
Nodes (22): enum, RuntimeError, JobEvent, Domain models shared by the pipeline, services, and UI., Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed() (+14 more)

### Community 9 - "PreviewManager"
Cohesion: 0.06
Nodes (35): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+27 more)

### Community 10 - "WorkbenchWidget"
Cohesion: 0.10
Nodes (20): setter, Changed, Path, Pressed, TrackJob, Widget, Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Download or verify local caching of all AI neural model weights. (+12 more)

### Community 11 - "analysis/restoration.py"
Cohesion: 0.10
Nodes (34): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+26 more)

### Community 12 - "HybridCoOpProvider"
Cohesion: 0.09
Nodes (17): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, HybridCoOpProvider, Hybrid multi-band provider: - NVSR reconstructs mid-high frequencies:…, Tests for M10-C Enhancement Providers., Verify ConservativeDSPProvider is available and generates residual above cutoff. (+9 more)

### Community 13 - "HarvesterApp"
Cohesion: 0.07
Nodes (14): HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Toggle visualizer between spectrum analyzer and oscilloscope., Seek backward 5 seconds in player. (+6 more)

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
Cohesion: 0.10
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 19 - "pathlib"
Cohesion: 0.08
Nodes (34): harvester_analysis_enhancement_presets, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_themes, harvester_util_logging_setup, logging, logging_handlers, math (+26 more)

### Community 20 - "numpy"
Cohesion: 0.16
Nodes (15): harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_model_manager, mutagen_id3, numpy, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Deterministic Conservative DSP Provider for OmniRip M10. Generates synthetic…, Non-destructive Enhancement Exporter and FFmpeg Audio I/O for OmniRip M10. (+7 more)

### Community 21 - "orchestrator.py"
Cohesion: 0.08
Nodes (29): collections, datetime, harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_musicbrainz, harvester_services_restoration, harvester_services_tagging, harvester_services_ytdlp (+21 more)

### Community 22 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 23 - "config.py"
Cohesion: 0.11
Nodes (35): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+27 more)

### Community 24 - "FfmpegService"
Cohesion: 0.11
Nodes (19): harvester_services_ffmpeg, Path, SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry (+11 more)

### Community 25 - "UiBridge"
Cohesion: 0.14
Nodes (16): Apply, ErrorInfo, coalesce_events(), JobEvent, Queue, Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., Drain ``events`` on a fixed cadence and apply coalesced plans., UiBridge (+8 more)

### Community 26 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 27 - "ComposeResult"
Cohesion: 0.09
Nodes (12): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application. (+4 more)

### Community 28 - "test_phase4_spectral.py"
Cohesion: 0.13
Nodes (18): excerpt_window(), _excerpt_window(), SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2., run_spectral_check(), _config() (+10 more)

### Community 29 - "polish_batch"
Cohesion: 0.11
Nodes (39): _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac(), _polish_mp3(), polish_stream(), CanonicalMetadata (+31 more)

### Community 30 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (15): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Build Phase M1 metadata fallback from yt-dlp probe fields., Write only canonical fields plus explicit provenance and best-effort art. (+7 more)

### Community 31 - "test_batch_trash.py"
Cohesion: 0.24
Nodes (17): move_to_trash(), purge(), Path, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Delete trash day-directories older than ``retention_days``; return count.…, trash_root_for(), Path (+9 more)

### Community 32 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 33 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 34 - "test_phase1_analyze.py"
Cohesion: 0.13
Nodes (16): harvester_pipeline_phase1_analyze, build_query(), Validate and normalize a URL before passing it to yt-dlp., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url(), asyncio, Phase 1 analysis unit tests (URL validation, query building, live rejection). (+8 more)

### Community 35 - "LogConsole"
Cohesion: 0.13
Nodes (13): RichLog, level_passes(), LogConsole, next_mode(), Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter. (+5 more)

### Community 36 - "DependencyStatus"
Cohesion: 0.14
Nodes (11): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable., Run independent dependency checks concurrently. (+3 more)

### Community 37 - "_build"
Cohesion: 0.11
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 38 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 39 - "ValidationError"
Cohesion: 0.12
Nodes (28): ProgressCallback, Validate cross-field invariants and return this config for fluent use., ErrorClass, analyze_url(), Mode A URL analysis stage., Probe a single URL without downloading its media., Any, Exception (+20 more)

### Community 40 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 41 - "test_model_manager.py"
Cohesion: 0.17
Nodes (14): harvester_analysis_enhancement, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Test model path resolution and caching checks in ModelManager., Verify SHA-256 calculation and verification., Test downloading a model via mocked huggingface_hub., Test that requesting an unknown model raises KeyError., Test downloading a model via direct HTTP streaming fallback when… (+6 more)

### Community 42 - "AcoustidService"
Cohesion: 0.06
Nodes (28): harvester_services_acoustid, Process, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+20 more)

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
Cohesion: 0.14
Nodes (10): importlib_util, Protocol, OmniRip M10 Enhancement and High-Frequency Reconstruction module., EnhancementProvider, ndarray, Enhancement provider protocol and base types for OmniRip M10., Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider. (+2 more)

### Community 48 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 49 - "PipelineOrchestrator"
Cohesion: 0.13
Nodes (9): _number(), PipelineOrchestrator, Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Wait until every submitted job has reached a terminal state. Queue joins are… (+1 more)

### Community 50 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 51 - "test_batch_scanner.py"
Cohesion: 0.18
Nodes (23): parse_filename(), BatchScan, Derive ``(artist, title)`` using the ordered docs/03 §1B.4 patterns., Recursively probe a music directory and apply the docs/03 §1B skip matrix.…, scan_directory(), _config(), Path, Mode B scanner tests: skip matrix, exclusions, filename parsing (docs/09 §7.1). (+15 more)

### Community 52 - "Mode"
Cohesion: 0.23
Nodes (11): EventKind, Mode, StrEnum, Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, SourceKind, Verdict, test_canonical_metadata_normalizes_artists_and_serializes() (+3 more)

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
Cohesion: 0.19
Nodes (7): BreakerState, CircuitBreaker, StrEnum, Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens()

### Community 57 - "themes.py"
Cohesion: 0.18
Nodes (11): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+3 more)

### Community 59 - ".parse_progress"
Cohesion: 0.15
Nodes (9): DownloadProgress, Any, SpectralResult, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), YtdlpProgress (+1 more)

### Community 60 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 61 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 62 - "TrackJob"
Cohesion: 0.32
Nodes (3): Exception, TrackJob, Append the terminal report row for a Mode B job (FR-14: per completed job).

### Community 63 - "SlskdService"
Cohesion: 0.20
Nodes (7): _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 64 - ".__init__"
Cohesion: 0.17
Nodes (5): DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 65 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 66 - "EnhancementExporter"
Cohesion: 0.13
Nodes (17): EnhancementPreset, EnhancementExporter, ndarray, Path, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+9 more)

### Community 67 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 68 - ".__init__"
Cohesion: 0.18
Nodes (9): AcoustidService, CoverArtService, SlskdService, MetadataTagger, Queue, SubprocessRegistry, StageHandler, Task (+1 more)

### Community 69 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 70 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 71 - "titleclean.py"
Cohesion: 0.17
Nodes (17): Match, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase…, NFKD-normalize and fold diacritics to ASCII while keeping the case. (+9 more)

### Community 72 - "_parse_search_payload"
Cohesion: 0.48
Nodes (7): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, _text()

### Community 73 - "AppConfig"
Cohesion: 0.11
Nodes (26): asyncio, collections_abc, dataclasses, hashlib, httpx, json, mutagen_flac, os (+18 more)

### Community 74 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 75 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 76 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

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

### Community 83 - "FlashSRProvider"
Cohesion: 0.19
Nodes (7): FlashSRProvider, Any, ModelManager, ndarray, Path, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000))., FlashSR single-step distilled diffusion air-band generator. Generates ultra-…

### Community 84 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 85 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 86 - "FakeSlskd"
Cohesion: 0.36
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
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

### Community 91 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 92 - "NVSRProvider"
Cohesion: 0.17
Nodes (8): NVSRProvider, Any, ModelManager, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if neural acceleration is enabled, torch is installed, and weights are…

### Community 93 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 94 - "._put_event"
Cohesion: 0.25
Nodes (3): DownloadProgress, EventKind, JobEvent

### Community 95 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 97 - "FlushPlan"
Cohesion: 0.25
Nodes (4): FlushPlan, One throttled batch of UI updates., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``.

### Community 98 - "test_ui_player.py"
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

### Community 108 - "._update_eq_ui"
Cohesion: 0.25
Nodes (4): ComposeResult, Render a 13-line vertical studio fader rail with center 0dB line, calibration…, Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons.

### Community 109 - "check_enhancement_available"
Cohesion: 0.50
Nodes (4): check_enhancement_available(), Check if the optional neural restoration dependencies are installed. Returns:…, Verify check_enhancement_available returns boolean and descriptive string., test_check_enhancement_available_returns_status()

### Community 110 - "presets.py"
Cohesion: 0.50
Nodes (3): EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 908 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **91 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppConfig` connect `AppConfig` to `scanner.py`, `analysis/restoration.py`, `HarvesterApp`, `pathlib`, `orchestrator.py`, `config.py`, `FfmpegService`, `test_phase4_spectral.py`, `polish_batch`, `DependencyStatus`, `ValidationError`, `AcoustidService`, `PipelineOrchestrator`, `test_batch_scanner.py`, `SlskdService`, `.__init__`, `.__init__`, `persist_first_run_acceptance`, `CoverArtService`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `test_orchestrator_m5.py`, `.__init__`, `DependencyStatus`, `_build`, `AppConfig`, `test_orchestrator.py`, `HarvesterApp`, `test_playlist.py`, `test_orchestrator_m4.py`, `.submit_batch`, `pathlib`, `orchestrator.py`, `FfmpegService`, `._put_event`, `test_orchestrator_m2.py`, `TrackJob`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `.__init__`, `FlushPlan`, `LogConsole`, `DependencyStatus`, `__main__.py`, `AppConfig`, `PreviewManager`, `WorkbenchWidget`, `AudioPlayerWidget`, `PipelineOrchestrator`, `test_ui_pilot.py`, `pathlib`, `._load_selected_into_workbench_and_player`, `config.py`, `BatchConfirmScreen`, `themes.py`, `ComposeResult`, `UiBridge`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `HarvesterApp` (e.g. with `AppConfig` and `PipelineOrchestrator`) actually correct?**
  _`HarvesterApp` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AppConfig` (e.g. with `scan_directory()` and `PipelineOrchestrator`) actually correct?**
  _`AppConfig` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `MasteringEQSettings`) actually correct?**
  _`WorkbenchWidget` has 13 INFERRED edges - model-reasoned connections that need verification._