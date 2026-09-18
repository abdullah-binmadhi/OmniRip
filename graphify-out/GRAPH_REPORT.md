# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2161 nodes · 4471 edges · 174 communities (101 shown, 73 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 537 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2949e808`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- slskd.py
- scanner.py
- acoustid.py
- AudioPlayerWidget
- numpy
- pathlib
- Milestone M7 — QA & packaging
- AudioVisualizer
- dataclasses
- analysis/restoration.py
- ModelManager
- WorkbenchWidget
- FlashSRProvider
- JobTable
- test_playlist.py
- PreviewManager
- TrackJob
- test_orchestrator_m3.py
- HarvesterApp
- test_orchestrator_m4.py
- JobEvent
- EnhancementExporter
- test_orchestrator_m2.py
- SourceKind
- config.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- Phase 1 — Input Analysis
- test_batch_trash.py
- FfmpegService
- State
- CanonicalMetadata
- ValidationError
- AppConfig
- phase2_hunt.py
- YtdlpService
- PipelineOrchestrator
- LogConsole
- test_orchestrator_m5.py
- environment.py
- Phase 5 — Polish and Sync
- titleclean.py
- test_spectral.py
- QualityEvidence
- test_orchestrator.py
- CurationWorkbenchModal
- SpectralResult
- orchestrator.py
- BatchReport
- TrackJob
- NVSRProvider
- slskd daemon
- Textual TUI
- .__init__
- models.py
- yt-dlp
- ._startup
- CircuitBreaker
- Minimal Implementation Ladder
- StatusBar
- Pipeline orchestrator
- themes.py
- Mode B — Local Batch Audit
- test_phase5_polish.py
- __main__.py
- retry.py
- ytdlp.py
- errors.py
- ComposeResult
- Spectral fixture connectivity gap
- circuit.py
- test_batch_swap.py
- load_config
- persist_first_run_acceptance
- CoverArtService
- Graphify Knowledge Graph
- .submit_batch
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- Pressed
- CI Workflow
- test_musicbrainz.py
- os
- ._load_selected_into_workbench_and_player
- Any
- .__init__
- phase1_analyze
- BatchConfirmScreen
- phase2_hunt
- State machine
- P2P candidate scoring
- pytest
- FakeFfmpeg
- PlaylistConfirmScreen
- NFR-1 — Strict async
- phase3_identify
- phase5_polish
- phase4_spectral
- Five-phase pipeline specification
- mutagen tagging
- yt-dlp failure catalog
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- OmniRip
- .probe_playlist
- test_models.py
- FakeAcoustid
- FakeTagger
- _FakeFailureFfmpeg
- .wait_for_idle
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
- batch/__init__.py
- harvester/__init__.py
- pipeline/__init__.py
- services/__init__.py
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
- harvester_services_ffmpeg
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
- Any
- Changed
- Pressed
- TrackJob
- Widget
- Path
- Path
- Text

## God Nodes (most connected - your core abstractions)
1. `ValidationError` - 53 edges
2. `PipelineOrchestrator` - 53 edges
3. `HarvesterApp` - 50 edges
4. `TrackJob` - 46 edges
5. `CanonicalMetadata` - 44 edges
6. `AppConfig` - 42 edges
7. `load_config()` - 38 edges
8. `AudioPlayerWidget` - 33 edges
9. `AudioVisualizer` - 33 edges
10. `Mode` - 27 edges

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

## Communities (174 total, 73 thin omitted)

### Community 0 - "slskd.py"
Cohesion: 0.07
Nodes (45): _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters., Compute the documented weighted score for one candidate. (+37 more)

### Community 1 - "scanner.py"
Cohesion: 0.08
Nodes (53): mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, _bitrate_kbps(), _codec_label() (+45 more)

### Community 2 - "acoustid.py"
Cohesion: 0.07
Nodes (30): json, Process, sqlite3, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json() (+22 more)

### Community 3 - "AudioPlayerWidget"
Cohesion: 0.06
Nodes (28): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+20 more)

### Community 4 - "numpy"
Cohesion: 0.08
Nodes (42): harvester_services_enhancement_conservative_provider, logging, numpy, apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray (+34 more)

### Community 5 - "pathlib"
Cohesion: 0.07
Nodes (37): asyncio, collections_abc, harvester_pipeline_orchestrator, harvester_services_enhancement_preview, harvester_services_environment, harvester_ui_bridge, harvester_ui_logconsole, harvester_ui_player (+29 more)

### Community 6 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 7 - "AudioVisualizer"
Cohesion: 0.06
Nodes (23): AudioVisualizer, Path, Text, Widget, Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses downsampled hop… (+15 more)

### Community 8 - "dataclasses"
Cohesion: 0.07
Nodes (29): dataclasses, logging_handlers, LogRecord, EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering., AppPaths, Path (+21 more)

### Community 9 - "analysis/restoration.py"
Cohesion: 0.10
Nodes (34): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+26 more)

### Community 10 - "ModelManager"
Cohesion: 0.07
Nodes (28): hashlib, importlib_util, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, Path, ModelManager, Path (+20 more)

### Community 11 - "WorkbenchWidget"
Cohesion: 0.09
Nodes (21): Changed, Pressed, setter, ComposeResult, Path, Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on…, In-page audio enhancement and auditioning workbench panel. Supports real-time… (+13 more)

### Community 12 - "FlashSRProvider"
Cohesion: 0.06
Nodes (23): harvester_services_enhancement, Protocol, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider., Whether the provider's dependencies and weights are ready for inference., Generate the high-frequency residual signal strictly above cutoff_hz. Args:… (+15 more)

### Community 13 - "JobTable"
Cohesion: 0.11
Nodes (15): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4)., _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network). (+7 more)

### Community 14 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 15 - "PreviewManager"
Cohesion: 0.09
Nodes (26): harvester_analysis_enhancement_presets, harvester_ui_screens_curation_workbench, platform, Popen, PreviewManager, EnhancementPreset, ndarray, Path (+18 more)

### Community 16 - "TrackJob"
Cohesion: 0.15
Nodes (29): difflib, Mode, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 17 - "test_orchestrator_m3.py"
Cohesion: 0.11
Nodes (11): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+3 more)

### Community 18 - "HarvesterApp"
Cohesion: 0.07
Nodes (12): FlushPlan, HarvesterApp, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Open the detailed Curation Workbench modal for the selected job's audio file., Toggle visualizer between spectrum analyzer and oscilloscope., Seek backward 5 seconds in player., Seek forward 5 seconds in player. (+4 more)

### Community 19 - "test_orchestrator_m4.py"
Cohesion: 0.15
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 20 - "JobEvent"
Cohesion: 0.14
Nodes (22): Apply, EventKind, JobEvent, coalesce_events(), FlushPlan, Queue, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates. (+14 more)

### Community 21 - "EnhancementExporter"
Cohesion: 0.10
Nodes (23): harvester_services_enhancement_exporter, mutagen_id3, EnhancementExporter, EnhancementPreset, ndarray, Path, Render enhanced audio array according to preset parameters: 1. Progressive mono…, Decode input file, render enhanced audio, write MP3 derivative, and attach ID3… (+15 more)

### Community 22 - "test_orchestrator_m2.py"
Cohesion: 0.17
Nodes (16): harvester_util_circuit, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path (+8 more)

### Community 23 - "SourceKind"
Cohesion: 0.16
Nodes (19): Pure analysis logic: query cleaning and P2P candidate ranking., StrEnum, SourceKind, Verdict, excerpt_window(), _excerpt_window(), Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3). (+11 more)

### Community 24 - "config.py"
Cohesion: 0.15
Nodes (23): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+15 more)

### Community 25 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.11
Nodes (25): AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D9 — Fingerprint before transcode, FR-7 — Fingerprint before transcode, Trust but verify principle, Metadata fallback chain, Phase 3 — Ground-Truth ID, AcoustID (+17 more)

### Community 26 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (25): Atomic filesystem helpers, Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check (+17 more)

### Community 27 - "test_batch_trash.py"
Cohesion: 0.18
Nodes (23): shutil, move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step). (+15 more)

### Community 28 - "FfmpegService"
Cohesion: 0.17
Nodes (13): SourceKind, Validate cross-field invariants and return this config for fluent use., FfmpegService, ndarray, Path, SubprocessRegistry, Decode a mono excerpt to float32 PCM without blocking the loop., Run FFmpeg tools in killable subprocesses with explicit deadlines. (+5 more)

### Community 29 - "State"
Cohesion: 0.13
Nodes (19): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), StrEnum, The single source of truth for legal job-state transitions. ``State`` lives… (+11 more)

### Community 30 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (16): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields. (+8 more)

### Community 31 - "ValidationError"
Cohesion: 0.14
Nodes (20): analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url() (+12 more)

### Community 32 - "AppConfig"
Cohesion: 0.25
Nodes (22): CanonicalMetadata, harvester_util_fsatomic, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac() (+14 more)

### Community 33 - "phase2_hunt.py"
Cohesion: 0.11
Nodes (22): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, mutagen_flac, P2PCandidate, build_hunt_queries(), hunt_and_score() (+14 more)

### Community 34 - "YtdlpService"
Cohesion: 0.16
Nodes (14): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+6 more)

### Community 35 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (8): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 36 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 37 - "test_orchestrator_m5.py"
Cohesion: 0.23
Nodes (17): _build(), FakeYtdlp, _mixed_library(), asyncio, Path, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison. (+9 more)

### Community 38 - "environment.py"
Cohesion: 0.17
Nodes (12): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable. (+4 more)

### Community 39 - "Phase 5 — Polish and Sync"
Cohesion: 0.11
Nodes (20): Batch trash manager, Retry and circuit-breaker utilities, Fallback transcoding, Fallback triggers, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check (+12 more)

### Community 40 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 41 - "test_spectral.py"
Cohesion: 0.28
Nodes (19): parametrize, _content(), fixture_fraud_128(), fixture_fraud_192(), fixture_honest_full(), fixture_honest_rolloff(), fixture_near_silent(), fixture_short() (+11 more)

### Community 42 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 43 - "test_orchestrator.py"
Cohesion: 0.17
Nodes (9): FakeFfmpeg, FakeSlskdOffline, FakeTagger, FakeYtdlp, asyncio, Path, Deterministic stand-in for an unreachable slskd daemon., test_orchestrator_cancel_marks_job_cancelled() (+1 more)

### Community 44 - "CurationWorkbenchModal"
Cohesion: 0.12
Nodes (12): CurationWorkbenchModal, Changed, ComposeResult, Path, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App (+4 more)

### Community 45 - "SpectralResult"
Cohesion: 0.20
Nodes (17): analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray, Spectral anti-fraud detector: brick-wall cutoff and steepness analysis.… (+9 more)

### Community 46 - "orchestrator.py"
Cohesion: 0.12
Nodes (15): collections, harvester_batch_scanner, harvester_batch_trash, harvester_pipeline_phase1_analyze, harvester_pipeline_phase3_identify, harvester_pipeline_phase4_spectral, harvester_services_acoustid, harvester_services_musicbrainz (+7 more)

### Community 47 - "BatchReport"
Cohesion: 0.17
Nodes (14): harvester_batch_report, Path, BatchReport, job_row(), Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4). (+6 more)

### Community 49 - "NVSRProvider"
Cohesion: 0.15
Nodes (10): Any, NVSRProvider, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if torch is installed and weights are cached., Generate high-frequency residual using NVSR, isolating strictly the band >… (+2 more)

### Community 50 - "slskd daemon"
Cohesion: 0.12
Nodes (16): AC-3 — slskd stopped fallback to yt-dlp, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-6 — slskd unreachable fast-fail, NFR-4 — Graceful degradation, NFR-7 — Portability (+8 more)

### Community 51 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 52 - ".__init__"
Cohesion: 0.13
Nodes (10): AcoustidService, CoverArtService, DownloadProgress, EventKind, JobEvent, Queue, MetadataTagger, SlskdService (+2 more)

### Community 53 - "models.py"
Cohesion: 0.18
Nodes (12): datetime, batch_report_name(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3)., skipped_row(), Domain models shared by the pipeline, services, and UI. (+4 more)

### Community 54 - "yt-dlp"
Cohesion: 0.14
Nodes (15): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, D10 — Playlist cap 50 + confirmation, D3 — Spectral check scope: P2P lossless claims only, FR-1 — Extract metadata without downloading, FR-10 — Provenance-based spectral exemption, FR-4 — yt-dlp best audio-only raw download, FR-5 — P2P candidate retry then fallback (+7 more)

### Community 55 - "._startup"
Cohesion: 0.17
Nodes (3): wrapped(), Changed, Submitted

### Community 56 - "CircuitBreaker"
Cohesion: 0.15
Nodes (5): CircuitBreaker, Fast-fail a dependency lane after consecutive failures., FakeSlskd, FakeSlskdOffline, Deterministic stand-in for an unreachable slskd daemon (forces the fallback…

### Community 57 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 58 - "StatusBar"
Cohesion: 0.14
Nodes (7): DependencyStatus, EnvironmentStatus, FatalSetupScreen, Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 59 - "Pipeline orchestrator"
Cohesion: 0.19
Nodes (14): HarvestApp, JobEvent, Pipeline orchestrator, Python 3.11 and asyncio, SourceKind, Textual reactive TUI, TrackJob, UI bridge (+6 more)

### Community 60 - "themes.py"
Cohesion: 0.20
Nodes (11): cycle_theme(), App, Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+3 more)

### Community 61 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 62 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 63 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 64 - "retry.py"
Cohesion: 0.23
Nodes (9): random, backoff_delay(), Async retry timing primitives shared by service integrations., Return exponential backoff with the documented ±25% jitter., Sleep asynchronously and return the actual delay used., sleep_backoff(), asyncio, test_backoff_has_expected_bounds() (+1 more)

### Community 65 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

### Community 66 - "errors.py"
Cohesion: 0.30
Nodes (10): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+2 more)

### Community 67 - "ComposeResult"
Cohesion: 0.18
Nodes (5): FirstRunNoticeScreen, PurgeConfirmScreen, ComposeResult, Confirm trash purge before deleting rollback sources (docs/08 §5, D5)., Legal/ToS notice shown once; acceptance persists to config (docs/01 §8, docs/08…

### Community 68 - "Spectral fixture connectivity gap"
Cohesion: 0.22
Nodes (11): Generated audio fixtures, Spectral fixture layer, M4 milestone, Phase 4, Spectral analysis responsibility split, Spectral analysis architecture conclusion, Spectral detector, Spectral fixture connectivity gap (+3 more)

### Community 69 - "circuit.py"
Cohesion: 0.24
Nodes (8): enum, BreakerState, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens(), time

### Community 70 - "test_batch_swap.py"
Cohesion: 0.27
Nodes (9): harvester_pipeline, harvester_util_errors, _job(), Path, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash() (+1 more)

### Community 71 - "load_config"
Cohesion: 0.31
Nodes (10): _deep_merge(), load_config(), _load_toml(), Path, Load config with precedence CLI > environment > TOML > defaults., Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected() (+2 more)

### Community 72 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 73 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 74 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 75 - ".submit_batch"
Cohesion: 0.24
Nodes (7): BatchScan, _entry_tags(), Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 76 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 77 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 78 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 79 - "Pressed"
Cohesion: 0.20
Nodes (4): HelpScreen, Pressed, Non-blocking help overlay for the application., Cycle to next dynamic color theme.

### Community 80 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 81 - "test_musicbrainz.py"
Cohesion: 0.39
Nodes (7): httpx, _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 82 - "os"
Cohesion: 0.31
Nodes (8): os, atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename., test_fsatomic_helpers()

### Community 83 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 85 - ".__init__"
Cohesion: 0.25
Nodes (3): AppConfig, QuitConfirmScreen, Confirm quit while jobs are still active (docs/08 §5, FR-17).

### Community 86 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 87 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 88 - "phase2_hunt"
Cohesion: 0.29
Nodes (7): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, Concurrent download semaphore

### Community 89 - "State machine"
Cohesion: 0.29
Nodes (7): State machine, Title cleaning analysis, Fallback anti-loop guard, IllegalTransition, Unit test plan, State-machine truth directive, Tests alongside every module

### Community 90 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 91 - "pytest"
Cohesion: 0.33
Nodes (5): pytest, asyncio, test_registry_terminates_process_by_job_prefix(), asyncio, test_m0_shell_mounts_without_startup_checks()

### Community 94 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 95 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 96 - "phase5_polish"
Cohesion: 0.40
Nodes (5): Batch report writer, FFmpeg service, phase5_polish, q_polish stage queue, Tagging service

### Community 97 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 98 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 99 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 100 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 101 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 102 - "OmniRip"
Cohesion: 0.50
Nodes (3): OmniRip script, HARVESTER_CONFIG, SLSKD_API_KEY

### Community 103 - ".probe_playlist"
Cohesion: 0.50
Nodes (3): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10).

### Community 104 - "test_models.py"
Cohesion: 0.50
Nodes (3): test_canonical_metadata_normalizes_artists_and_serializes(), test_source_and_verdict_defaults_are_explicit(), test_track_job_display_name_prefers_canonical_metadata()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Batch adapter`, `Candidate scoring` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 829 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `AppConfig`, `test_orchestrator_m5.py`, `.probe_playlist`, `.submit_batch`, `.wait_for_idle`, `test_orchestrator.py`, `orchestrator.py`, `test_playlist.py`, `TrackJob`, `test_orchestrator_m3.py`, `test_orchestrator_m4.py`, `.__init__`, `test_orchestrator_m2.py`, `._startup`, `FfmpegService`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `slskd.py`, `scanner.py`, `acoustid.py`, `PipelineOrchestrator`, `ytdlp.py`, `pathlib`, `environment.py`, `load_config`, `persist_first_run_acceptance`, `CoverArtService`, `analysis/restoration.py`, `YtdlpService`, `orchestrator.py`, `.__init__`, `SourceKind`, `config.py`, `FfmpegService`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `ComposeResult`, `AudioPlayerWidget`, `pathlib`, `WorkbenchWidget`, `CurationWorkbenchModal`, `JobTable`, `Pressed`, `._load_selected_into_workbench_and_player`, `.__init__`, `BatchConfirmScreen`, `._startup`, `pytest`, `__main__.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `PipelineOrchestrator` (e.g. with `AppConfig` and `FfmpegService`) actually correct?**
  _`PipelineOrchestrator` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HarvesterApp` (e.g. with `AudioPlayerWidget` and `CurationWorkbenchModal`) actually correct?**
  _`HarvesterApp` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `TrackJob` (e.g. with `job_row()` and `State`) actually correct?**
  _`TrackJob` has 36 INFERRED edges - model-reasoned connections that need verification._