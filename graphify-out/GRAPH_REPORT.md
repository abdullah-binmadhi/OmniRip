# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2187 nodes · 4494 edges · 175 communities (98 shown, 77 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 557 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cdbdede9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_spectral.py
- ensure_2d_audio
- scanner.py
- AudioPlayerWidget
- acoustid.py
- AudioVisualizer
- test_orchestrator_m5.py
- WorkbenchWidget
- Milestone M7 — QA & packaging
- HarvesterApp
- ModelManager
- models.py
- TrackJob
- logging_setup.py
- JobTable
- app.py
- NVSRProvider
- analysis/restoration.py
- test_playlist.py
- AppConfig
- PreviewManager
- scoring.py
- pathlib
- JobEvent
- test_orchestrator_m2.py
- config.py
- test_orchestrator_m3.py
- orchestrator.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- Phase 1 — Input Analysis
- FfmpegService
- State
- YtdlpService
- EnhancementExporter
- LogConsole
- environment.py
- CanonicalMetadata
- test_batch_trash.py
- ComposeResult
- PipelineOrchestrator
- Phase 5 — Polish and Sync
- phase2_hunt.py
- titleclean.py
- QualityEvidence
- test_orchestrator.py
- ValidationError
- phase1_analyze.py
- CircuitBreaker
- EnhancementProvider
- test_phase4_spectral.py
- slskd daemon
- Textual TUI
- test_slskd.py
- yt-dlp
- SlskdService
- Minimal Implementation Ladder
- .__init__
- Pipeline orchestrator
- TrackJob
- themes.py
- Mode B — Local Batch Audit
- errors.py
- test_phase5_polish.py
- .__init__
- __main__.py
- ytdlp.py
- slskd.py
- CurationWorkbenchModal
- Spectral fixture connectivity gap
- musicbrainz.py
- persist_first_run_acceptance
- CoverArtService
- Graphify Knowledge Graph
- .submit_batch
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- SearchResponse
- CI Workflow
- ._load_selected_into_workbench_and_player
- Any
- phase1_analyze
- BatchConfirmScreen
- phase2_hunt
- State machine
- P2P candidate scoring
- pytest
- .submit_playlist
- PlaylistConfirmScreen
- test_config.py
- dataclasses
- NFR-1 — Strict async
- phase3_identify
- phase5_polish
- phase4_spectral
- Five-phase pipeline specification
- FirstRunNoticeScreen
- mutagen tagging
- yt-dlp failure catalog
- ._emit_progress
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
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
- .public_dict
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
- .action_seek_backward
- .action_seek_backward_15
- ui/__init__.py
- util/__init__.py
- App
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
- harvester_analysis
- harvester_pipeline_phase2_hunt
- harvester_pipeline_phase5_polish
- harvester_services_enhancement_exporter
- harvester_services_ffmpeg
- harvester_services_model_manager
- harvester_ui_themes
- harvester_ui_workbench
- ndarray
- harvester
- PreviewManager
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- StrEnum
- Exception
- Queue
- EnhancementPreset
- ModelManager
- Any
- ModelManager
- Changed
- Pressed
- TrackJob
- Widget
- Path
- Text

## God Nodes (most connected - your core abstractions)
1. `PipelineOrchestrator` - 53 edges
2. `ValidationError` - 53 edges
3. `HarvesterApp` - 50 edges
4. `TrackJob` - 46 edges
5. `CanonicalMetadata` - 44 edges
6. `AppConfig` - 42 edges
7. `load_config()` - 38 edges
8. `AudioPlayerWidget` - 33 edges
9. `AudioVisualizer` - 33 edges
10. `WorkbenchWidget` - 31 edges

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

## Communities (175 total, 77 thin omitted)

### Community 0 - "test_spectral.py"
Cohesion: 0.07
Nodes (52): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+44 more)

### Community 1 - "ensure_2d_audio"
Cohesion: 0.06
Nodes (46): Any, EnhancementPreset, apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.… (+38 more)

### Community 2 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 3 - "AudioPlayerWidget"
Cohesion: 0.06
Nodes (28): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+20 more)

### Community 4 - "acoustid.py"
Cohesion: 0.07
Nodes (29): Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number() (+21 more)

### Community 5 - "AudioVisualizer"
Cohesion: 0.06
Nodes (25): ComposeResult, AudioVisualizer, Path, Text, Widget, Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels. (+17 more)

### Community 6 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (24): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+16 more)

### Community 7 - "WorkbenchWidget"
Cohesion: 0.08
Nodes (26): Changed, harvester_ui_player, Pressed, setter, Path, Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, In-page audio enhancement and auditioning workbench panel. Supports real-time… (+18 more)

### Community 8 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 9 - "HarvesterApp"
Cohesion: 0.07
Nodes (14): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file., Cycle to next dynamic color theme. (+6 more)

### Community 10 - "ModelManager"
Cohesion: 0.07
Nodes (29): harvester_analysis_enhancement, hashlib, Path, Path, ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET. (+21 more)

### Community 11 - "models.py"
Cohesion: 0.08
Nodes (31): datetime, harvester_batch_report, json, Path, batch_report_name(), BatchReport, job_row(), Path (+23 more)

### Community 12 - "TrackJob"
Cohesion: 0.12
Nodes (32): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+24 more)

### Community 13 - "logging_setup.py"
Cohesion: 0.08
Nodes (24): logging_handlers, LogRecord, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., CallbackHandler (+16 more)

### Community 14 - "JobTable"
Cohesion: 0.11
Nodes (15): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network). (+7 more)

### Community 15 - "app.py"
Cohesion: 0.09
Nodes (28): collections_abc, harvester_pipeline_orchestrator, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_ui_visualizer, harvester_util_logging_setup (+20 more)

### Community 16 - "NVSRProvider"
Cohesion: 0.08
Nodes (22): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, FlashSR single-step distilled diffusion air-band generator. Generates ultra-…, HybridCoOpProvider, Hybrid multi-band provider: - NVSR reconstructs mid-high frequencies:… (+14 more)

### Community 17 - "analysis/restoration.py"
Cohesion: 0.12
Nodes (30): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+22 more)

### Community 18 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 19 - "AppConfig"
Cohesion: 0.16
Nodes (31): CanonicalMetadata, harvester_util_fsatomic, os, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch() (+23 more)

### Community 20 - "PreviewManager"
Cohesion: 0.10
Nodes (25): harvester_ui_screens_curation_workbench, Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external… (+17 more)

### Community 21 - "scoring.py"
Cohesion: 0.11
Nodes (26): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+18 more)

### Community 22 - "pathlib"
Cohesion: 0.13
Nodes (19): harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_enhancement_conservative_provider, logging, numpy, pathlib, platform, platformdirs (+11 more)

### Community 23 - "JobEvent"
Cohesion: 0.14
Nodes (22): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+14 more)

### Community 24 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 25 - "config.py"
Cohesion: 0.16
Nodes (27): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+19 more)

### Community 26 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (10): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+2 more)

### Community 27 - "orchestrator.py"
Cohesion: 0.09
Nodes (22): asyncio, collections, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral, harvester_services_acoustid (+14 more)

### Community 28 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.11
Nodes (25): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID (+17 more)

### Community 29 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (25): Atomic filesystem helpers, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+17 more)

### Community 30 - "FfmpegService"
Cohesion: 0.17
Nodes (13): SourceKind, Validate cross-field invariants and return this config for fluent use., FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+5 more)

### Community 31 - "State"
Cohesion: 0.13
Nodes (19): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), StrEnum, The single source of truth for legal job-state transitions. ``State`` lives… (+11 more)

### Community 32 - "YtdlpService"
Cohesion: 0.16
Nodes (14): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+6 more)

### Community 33 - "EnhancementExporter"
Cohesion: 0.11
Nodes (19): harvester_analysis_enhancement_presets, EnhancementExporter, Renders enhanced audio and exports MP3 derivatives with explicit provenance…, Toggle between Neural Model Acceleration and Eco DSP synthesis., Path, Path, Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify that EnhancementExporter toggles neural acceleration across all… (+11 more)

### Community 34 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 35 - "environment.py"
Cohesion: 0.16
Nodes (13): shlex, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+5 more)

### Community 36 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (15): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Build Phase M1 metadata fallback from yt-dlp probe fields., Write only canonical fields plus explicit provenance and best-effort art. (+7 more)

### Community 37 - "test_batch_trash.py"
Cohesion: 0.20
Nodes (20): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+12 more)

### Community 38 - "ComposeResult"
Cohesion: 0.10
Nodes (10): FatalSetupScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application., Confirm quit while jobs are still active (docs/08 §5, FR-17). (+2 more)

### Community 39 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (8): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 40 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 41 - "phase2_hunt.py"
Cohesion: 0.13
Nodes (19): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, mutagen_flac, P2PCandidate, build_hunt_queries(), hunt_and_score() (+11 more)

### Community 42 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 43 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 44 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 45 - "ValidationError"
Cohesion: 0.18
Nodes (13): Pure analysis logic: query cleaning and P2P candidate ranking., excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2., run_spectral_check(), ConservativeRestorationService (+5 more)

### Community 46 - "phase1_analyze.py"
Cohesion: 0.17
Nodes (16): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+8 more)

### Community 47 - "CircuitBreaker"
Cohesion: 0.16
Nodes (10): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+2 more)

### Community 48 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 49 - "test_phase4_spectral.py"
Cohesion: 0.22
Nodes (9): _config(), _FakeFailureFfmpeg, _FakeFfmpeg, _make_job(), asyncio, Path, test_gate_decode_failure_yields_inconclusive(), test_gate_disabled_by_config() (+1 more)

### Community 50 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 51 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 52 - "test_slskd.py"
Cohesion: 0.31
Nodes (10): _config(), asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route(), test_health_check_and_openapi_verification(), handler(), test_openapi_version_templates_normalize_and_pick_0_26_route() (+2 more)

### Community 53 - "yt-dlp"
Cohesion: 0.14
Nodes (15): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D10 — Playlist cap 50 + confirmation, D3 — Spectral check scope: P2P lossless claims only, FR-1 — Extract metadata without downloading, FR-10 — Provenance-based spectral exemption, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback (+7 more)

### Community 54 - "SlskdService"
Cohesion: 0.26
Nodes (5): P2PCandidate, AsyncClient, Path, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 55 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 56 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 57 - "Pipeline orchestrator"
Cohesion: 0.19
Nodes (14): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+6 more)

### Community 59 - "themes.py"
Cohesion: 0.20
Nodes (11): cycle_theme(), App, Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+3 more)

### Community 60 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 61 - "errors.py"
Cohesion: 0.29
Nodes (11): ErrorClass, DiskError, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited (+3 more)

### Community 62 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 63 - ".__init__"
Cohesion: 0.17
Nodes (9): AcoustidService, CoverArtService, EventKind, JobEvent, Queue, MetadataTagger, SlskdService, SubprocessRegistry (+1 more)

### Community 64 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 65 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

### Community 66 - "slskd.py"
Cohesion: 0.32
Nodes (11): _bool_or_none(), _concrete_paths(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), _pick_download_route(), Any (+3 more)

### Community 67 - "CurationWorkbenchModal"
Cohesion: 0.18
Nodes (7): CurationWorkbenchModal, Changed, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App, ComposeResult

### Community 68 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 69 - "musicbrainz.py"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 70 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 71 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 72 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 73 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 74 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 75 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 76 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 77 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (8): harvester_pipeline, _job(), Path, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash(), TrackJob

### Community 78 - "SearchResponse"
Cohesion: 0.31
Nodes (3): SearchResponse, SlskdFile, FakeSlskd

### Community 79 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 80 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 82 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 83 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 84 - "phase2_hunt"
Cohesion: 0.29
Nodes (7): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, Concurrent download semaphore

### Community 85 - "State machine"
Cohesion: 0.29
Nodes (7): State machine, Title cleaning analysis, Fallback anti-loop guard, IllegalTransition, Unit test plan, State-machine truth directive, Tests alongside every module

### Community 86 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 87 - "pytest"
Cohesion: 0.33
Nodes (5): pytest, asyncio, test_registry_terminates_process_by_job_prefix(), asyncio, test_m0_shell_mounts_without_startup_checks()

### Community 88 - ".submit_playlist"
Cohesion: 0.29
Nodes (4): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73).

### Community 90 - "test_config.py"
Cohesion: 0.53
Nodes (5): Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected(), test_precedence_is_cli_over_environment_over_file(), test_secret_values_are_never_in_public_config()

### Community 91 - "dataclasses"
Cohesion: 0.40
Nodes (4): dataclasses, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

### Community 92 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 93 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 94 - "phase5_polish"
Cohesion: 0.40
Nodes (5): Batch report writer, FFmpeg service, phase5_polish, q_polish stage queue, Tagging service

### Community 95 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 96 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 98 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 99 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 101 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 102 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Batch adapter`, `Candidate scoring` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 844 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `test_spectral.py`, `test_orchestrator_m3.py`, `._emit_progress`, `test_orchestrator_m5.py`, `.wait_for_idle`, `.submit_batch`, `HarvesterApp`, `test_orchestrator.py`, `test_playlist.py`, `AppConfig`, `.submit_playlist`, `test_orchestrator_m2.py`, `TrackJob`, `orchestrator.py`, `FfmpegService`, `.__init__`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `YtdlpService`, `ytdlp.py`, `scanner.py`, `environment.py`, `acoustid.py`, `musicbrainz.py`, `persist_first_run_acceptance`, `PipelineOrchestrator`, `CoverArtService`, `slskd.py`, `ValidationError`, `test_phase4_spectral.py`, `.public_dict`, `SlskdService`, `config.py`, `orchestrator.py`, `FfmpegService`, `.__init__`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `AudioPlayerWidget` connect `AudioPlayerWidget` to `AudioVisualizer`, `ComposeResult`, `WorkbenchWidget`, `HarvesterApp`, `app.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `CurationWorkbenchModal`) actually correct?**
  _`HarvesterApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 36 INFERRED edges - model-reasoned connections that need verification._