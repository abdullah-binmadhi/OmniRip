# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- 128 files · ~64,161 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .toml 1, .tcss 1)

## Summary
- 2139 nodes · 4435 edges · 170 communities (103 shown, 67 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 541 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cfc46e3f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SourceKind
- config.py
- State
- scanner.py
- AcoustidService
- test_orchestrator_m5.py
- test_enhancement_workbench.py
- Milestone M7 — QA & packaging
- environment.py
- analysis/restoration.py
- ensure_2d_audio
- pathlib
- test_model_manager.py
- TrackJob
- dataclasses
- ConservativeDSPProvider
- test_playlist.py
- HarvesterApp
- BatchReport
- ytdlp.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- JobEvent
- test_orchestrator_m2.py
- test_orchestrator_m3.py
- tagging.py
- AudioVisualizer
- Pipeline orchestrator
- LogConsole
- WorkbenchWidget
- AppConfig
- test_batch_trash.py
- ComposeResult
- Phase 1 — Input Analysis
- TrackJob
- yt-dlp
- titleclean.py
- orchestrator.py
- AudioPlayerWidget
- Spectral fixture connectivity gap
- ValidationError
- scoring.py
- EnhancementExporter
- QualityEvidence
- asyncio
- test_orchestrator.py
- SlskdService
- CurationWorkbenchModal
- Textual TUI
- CircuitBreaker
- test_slskd.py
- models.py
- HybridCoOpProvider
- Minimal Implementation Ladder
- .__init__
- phase2_hunt
- themes.py
- NVSRProvider
- Mode B — Local Batch Audit
- test_phase5_polish.py
- ffmpeg.py
- Phase 5 — Polish and Sync
- fsatomic.py
- Graphify Knowledge Graph
- app.py
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- InteractiveScrubber
- CI Workflow
- test_acoustid.py
- PipelineOrchestrator
- phase1_analyze
- P2P candidate scoring
- slskd.py
- SearchResponse
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- acoustid.py
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
- ui/__init__.py
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
- harvester_analysis
- harvester_pipeline
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_ffmpeg
- harvester
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- StrEnum
- Exception
- Queue
- yt-dlp metadata probe
- report.py
- Changed
- SubprocessRegistry
- asyncio
- test_models.py
- pytest
- .__init__
- FfmpegService
- ComposeResult
- Path
- Pressed
- Any
- asyncio
- CanonicalMetadata
- .verify_checksum
- persist_first_run_acceptance
- ._submit_current
- .submit_batch
- YtdlpService
- test_ui_player.py
- .submit_playlist
- ._load_selected_into_workbench_and_player
- FirstRunNoticeScreen
- .wait_for_idle
- TrackJob
- Any
- BatchConfirmScreen
- ._startup
- QuitConfirmScreen
- test_ui_visualizer.py
- WorkbenchTestApp
- metadata_from_query
- .public_dict
- harvester_ui_visualizer
- Text

## God Nodes (most connected - your core abstractions)
1. `ValidationError` - 53 edges
2. `PipelineOrchestrator` - 53 edges
3. `HarvesterApp` - 49 edges
4. `TrackJob` - 48 edges
5. `CanonicalMetadata` - 44 edges
6. `AppConfig` - 42 edges
7. `load_config()` - 38 edges
8. `AudioPlayerWidget` - 36 edges
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

## Communities (170 total, 67 thin omitted)

### Community 0 - "SourceKind"
Cohesion: 0.05
Nodes (69): parametrize, Pure analysis logic: query cleaning and P2P candidate ranking., analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference() (+61 more)

### Community 1 - "config.py"
Cohesion: 0.11
Nodes (36): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+28 more)

### Community 2 - "State"
Cohesion: 0.13
Nodes (20): enum, RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), StrEnum (+12 more)

### Community 3 - "scanner.py"
Cohesion: 0.08
Nodes (51): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+43 more)

### Community 4 - "AcoustidService"
Cohesion: 0.17
Nodes (5): AcoustidService, AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 5 - "test_orchestrator_m5.py"
Cohesion: 0.09
Nodes (23): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, _mixed_library() (+15 more)

### Community 6 - "test_enhancement_workbench.py"
Cohesion: 0.10
Nodes (22): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+14 more)

### Community 7 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 8 - "environment.py"
Cohesion: 0.08
Nodes (24): httpx, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+16 more)

### Community 9 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 10 - "ensure_2d_audio"
Cohesion: 0.08
Nodes (34): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+26 more)

### Community 11 - "pathlib"
Cohesion: 0.09
Nodes (29): harvester_analysis_enhancement_presets, harvester_services_enhancement_conservative_provider, logging, mutagen_id3, numpy, pathlib, platform, platformdirs (+21 more)

### Community 12 - "test_model_manager.py"
Cohesion: 0.09
Nodes (20): hashlib, importlib_util, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Verify that a dummy class adhering to EnhancementProvider satisfies isinstance… (+12 more)

### Community 13 - "TrackJob"
Cohesion: 0.17
Nodes (26): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+18 more)

### Community 14 - "dataclasses"
Cohesion: 0.07
Nodes (29): dataclasses, logging_handlers, LogRecord, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., AppPaths, Path (+21 more)

### Community 15 - "ConservativeDSPProvider"
Cohesion: 0.12
Nodes (12): harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, Tests for M10-C Enhancement Providers., Verify ConservativeDSPProvider is available and generates residual above cutoff., Verify NVSRProvider gracefully generates high-pass residual when model weights…, Verify FlashSRProvider produces air-band residual (> 16 kHz)., Verify HybridCoOpProvider correctly merges providers. (+4 more)

### Community 16 - "test_playlist.py"
Cohesion: 0.12
Nodes (14): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, _orchestrator(), asyncio (+6 more)

### Community 17 - "HarvesterApp"
Cohesion: 0.07
Nodes (12): FlushPlan, HarvesterApp, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file., Toggle visualizer between spectrum analyzer and oscilloscope., Seek backward 5 seconds in player., Seek forward 5 seconds in player. (+4 more)

### Community 18 - "BatchReport"
Cohesion: 0.18
Nodes (14): BatchReport, job_row(), Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4)., Path, Batch report tests: schema, incremental appends, row builders (FR-14). (+6 more)

### Community 19 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

### Community 20 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 21 - "JobEvent"
Cohesion: 0.14
Nodes (21): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+13 more)

### Community 22 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 23 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 24 - "tagging.py"
Cohesion: 0.23
Nodes (13): mutagen_flac, soundfile, metadata_from_probe(), Any, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields., _text(), _year() (+5 more)

### Community 25 - "AudioVisualizer"
Cohesion: 0.07
Nodes (18): ndarray, ComposeResult, AudioVisualizer, Path, Text, Widget, Set or clear the visual cutoff frequency marker (fc)., Manually update the current band energy levels. (+10 more)

### Community 26 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 27 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 28 - "WorkbenchWidget"
Cohesion: 0.11
Nodes (15): setter, Changed, ComposeResult, Path, Pressed, TrackJob, Widget, Load a track job into the workbench and resolve its streams. (+7 more)

### Community 29 - "AppConfig"
Cohesion: 0.21
Nodes (24): CanonicalMetadata, harvester_util_fsatomic, AppConfig, Validate cross-field invariants and return this config for fluent use., _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch() (+16 more)

### Community 30 - "test_batch_trash.py"
Cohesion: 0.19
Nodes (21): shutil, move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step). (+13 more)

### Community 31 - "ComposeResult"
Cohesion: 0.10
Nodes (9): FatalSetupScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, Non-blocking help overlay for the application., Confirm trash purge before deleting rollback sources (docs/08 §5, D5)., Shown when a required runtime dependency prevents acquisition. (+1 more)

### Community 32 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 34 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 35 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 36 - "orchestrator.py"
Cohesion: 0.07
Nodes (34): collections, harvester_analysis_scoring, harvester_analysis_titleclean, harvester_batch_report, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify (+26 more)

### Community 37 - "AudioPlayerWidget"
Cohesion: 0.11
Nodes (12): AudioPlayerWidget, Path, Pressed, Load an audio file into the player and prepare visualizer frames., Toggle playback between playing and paused/stopped., Begin audio playback and animate visualizer., Stop playback and rewind to start., Seek playback to an absolute timestamp in seconds. (+4 more)

### Community 38 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 39 - "ValidationError"
Cohesion: 0.14
Nodes (20): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+12 more)

### Community 40 - "scoring.py"
Cohesion: 0.20
Nodes (17): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+9 more)

### Community 41 - "EnhancementExporter"
Cohesion: 0.16
Nodes (15): EnhancementExporter, EnhancementPreset, ndarray, Path, Render enhanced audio array according to preset parameters: 1. Progressive mono…, Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+7 more)

### Community 42 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 43 - "asyncio"
Cohesion: 0.08
Nodes (24): asyncio, random, JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., backoff_delay(), Async retry timing primitives shared by service integrations. (+16 more)

### Community 44 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 45 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 46 - "CurationWorkbenchModal"
Cohesion: 0.13
Nodes (11): EnhancementExporter, PreviewManager, CurationWorkbenchModal, Changed, Path, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp (+3 more)

### Community 47 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 48 - "CircuitBreaker"
Cohesion: 0.13
Nodes (10): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+2 more)

### Community 49 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 50 - "models.py"
Cohesion: 0.18
Nodes (15): ErrorClass, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, DiskError, HarvesterError, JobCancelled (+7 more)

### Community 51 - "HybridCoOpProvider"
Cohesion: 0.14
Nodes (9): Protocol, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider., Whether the provider's dependencies and weights are ready for inference., Generate the high-frequency residual signal strictly above cutoff_hz. Args:…, HybridCoOpProvider (+1 more)

### Community 52 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 53 - ".__init__"
Cohesion: 0.14
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 54 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 55 - "themes.py"
Cohesion: 0.20
Nodes (11): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+3 more)

### Community 56 - "NVSRProvider"
Cohesion: 0.18
Nodes (8): Any, NVSRProvider, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if torch is installed and weights are cached., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 57 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 58 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 59 - "ffmpeg.py"
Cohesion: 0.15
Nodes (14): argparse, ArgumentParser, harvester, harvester_util_errors, harvester_util_subproc, shlex, build_parser(), main() (+6 more)

### Community 60 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 61 - "fsatomic.py"
Cohesion: 0.38
Nodes (6): atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename.

### Community 62 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 63 - "app.py"
Cohesion: 0.10
Nodes (29): collections_abc, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_ui_themes (+21 more)

### Community 64 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 65 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 66 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 67 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (7): Asynchronous pipeline stages., _job(), Path, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 68 - "InteractiveScrubber"
Cohesion: 0.15
Nodes (9): Click, Message, InteractiveScrubber, ComposeResult, Text, Widget, Interactive timeline scrubber allowing instant click-to-seek, showing visual…, Dispatched when user clicks anywhere on timeline to seek. (+1 more)

### Community 69 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 70 - "test_acoustid.py"
Cohesion: 0.35
Nodes (9): Fingerprint, _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network(), test_low_confidence_result_is_rejected() (+1 more)

### Community 71 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (7): DownloadProgress, EventKind, Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract.

### Community 72 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 73 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 74 - "slskd.py"
Cohesion: 0.47
Nodes (8): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., _text()

### Community 75 - "SearchResponse"
Cohesion: 0.18
Nodes (5): SearchResponse, SlskdFile, FakeSlskd, FakeSlskd, FakeSlskd

### Community 76 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 77 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 78 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 79 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 80 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 81 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 82 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 83 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 84 - "acoustid.py"
Cohesion: 0.38
Nodes (11): sqlite3, _earliest_release(), _metadata_from_json(), _number(), Any, AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache., Parse a numeric field as an integer (years and similar); None when not numeric., _release_year() (+3 more)

### Community 133 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 134 - "report.py"
Cohesion: 0.21
Nodes (10): datetime, json, batch_report_name(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3)., skipped_row() (+2 more)

### Community 136 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 140 - "pytest"
Cohesion: 0.33
Nodes (5): os, pytest, Tracked subprocess lifecycle helpers for cancellation-safe services., asyncio, test_registry_terminates_process_by_job_prefix()

### Community 141 - ".__init__"
Cohesion: 0.17
Nodes (10): AcoustidService, CoverArtService, JobEvent, Queue, MetadataTagger, SlskdService, SubprocessRegistry, StageHandler (+2 more)

### Community 142 - "FfmpegService"
Cohesion: 0.19
Nodes (11): SourceKind, FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines., Build the deterministic Phase 5 transcode arguments. (+3 more)

### Community 148 - "CanonicalMetadata"
Cohesion: 0.29
Nodes (5): CanonicalMetadata, _metadata_to_json(), MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art.

### Community 149 - ".verify_checksum"
Cohesion: 0.22
Nodes (5): Path, Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally., Calculate and verify SHA-256 checksum of a file., Download a model checkpoint to the local cache directory. Args: model_name:…

### Community 150 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 151 - "._submit_current"
Cohesion: 0.20
Nodes (4): PlaylistConfirmScreen, Changed, Show entry count and cap before expanding a playlist (docs/08 §2, D10)., Submitted

### Community 152 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 153 - "YtdlpService"
Cohesion: 0.16
Nodes (14): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+6 more)

### Community 154 - "test_ui_player.py"
Cohesion: 0.40
Nodes (4): PlayerTestApp, ComposeResult, Unit tests for AudioPlayerWidget controls and state., test_audio_player_widget_lifecycle()

### Community 155 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 156 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 161 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 164 - "test_ui_visualizer.py"
Cohesion: 0.40
Nodes (4): ComposeResult, Unit tests for AudioVisualizer widget (spectrum & oscilloscope modes)., test_audio_visualizer_modes_and_render(), VisualizerTestApp

### Community 165 - "WorkbenchTestApp"
Cohesion: 0.40
Nodes (5): ComposeResult, Path, test_player_interactive_scrubber_and_seeking(), test_workbench_stream_switching_and_metrics(), WorkbenchTestApp

### Community 166 - "metadata_from_query"
Cohesion: 0.50
Nodes (4): metadata_from_query(), Canonical-shaped record derived from a query/filename parse (Level 3)., test_metadata_from_query_plain_stem(), test_metadata_from_query_splits_artist_title()

## Knowledge Gaps
- **163 isolated node(s):** `harvester`, `Answer`, `Source Nodes`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 817 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **67 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HarvesterApp` connect `HarvesterApp` to `BatchConfirmScreen`, `._startup`, `QuitConfirmScreen`, `config.py`, `AudioPlayerWidget`, `asyncio`, `WorkbenchWidget`, `.__init__`, `._submit_current`, `ffmpeg.py`, `._load_selected_into_workbench_and_player`, `app.py`, `ComposeResult`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `SourceKind`, `config.py`, `scanner.py`, `AcoustidService`, `environment.py`, `analysis/restoration.py`, `SubprocessRegistry`, `.__init__`, `FfmpegService`, `ytdlp.py`, `persist_first_run_acceptance`, `YtdlpService`, `orchestrator.py`, `.public_dict`, `SlskdService`, `ffmpeg.py`, `PipelineOrchestrator`, `slskd.py`, `acoustid.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `SourceKind`, `TrackJob`, `._startup`, `orchestrator.py`, `test_orchestrator_m5.py`, `test_orchestrator.py`, `.__init__`, `FfmpegService`, `test_playlist.py`, `test_orchestrator_m2.py`, `test_orchestrator_m3.py`, `.submit_batch`, `.submit_playlist`, `AppConfig`, `.wait_for_idle`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `WorkbenchWidget`) actually correct?**
  _`HarvesterApp` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 38 INFERRED edges - model-reasoned connections that need verification._