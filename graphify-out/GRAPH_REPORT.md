# Graph Report - OmniRip  (2026-09-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2553 nodes · 5060 edges · 204 communities (114 shown, 90 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 522 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `393a7df6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- stem_separator.py
- pathlib
- AudioPlayerWidget
- orchestrator.py
- AcoustidService
- scanner.py
- test_stem_separator.py
- test_orchestrator_m5.py
- AudioVisualizer
- PreviewManager
- Milestone M7 — QA & packaging
- app.py
- HarvesterApp
- read_slskd_credentials
- logging_setup.py
- test_spectral.py
- analysis/restoration.py
- test_playlist.py
- ModelManager
- acoustid.py
- test_orchestrator_m4.py
- TrackJob
- scoring.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- harvester_util_errors
- FfmpegService
- FlashSRProvider
- test_ui_workbench.py
- test_orchestrator_m3.py
- test_orchestrator_m2.py
- test_bridge.py
- AppConfig
- YtdlpService
- State
- Pipeline orchestrator
- EnhancementExporter
- WorkbenchWidget
- ensure_2d_audio
- MasteringEQSettings
- phase2_hunt.py
- phase1_analyze.py
- .on_button_pressed
- LogConsole
- analyze_track_acoustics
- Phase 1 — Input Analysis
- pytest
- environment.py
- ComposeResult
- yt-dlp
- .on_select_changed
- Spectral fixture connectivity gap
- titleclean.py
- QualityEvidence
- CoverArtService
- PipelineOrchestrator
- test_ui_pilot.py
- EnhancementProvider
- models.py
- JobTable
- config.py
- Textual TUI
- CircuitBreaker
- DefectChecklist
- SlskdService
- Minimal Implementation Ladder
- themes.py
- ._startup
- phase2_hunt
- CanonicalMetadata
- TrackJob
- test_enhancement_dsp.py
- test_orchestrator.py
- .__init__
- Mode B — Local Batch Audit
- load_config
- test_phase5_polish.py
- .__init__
- __main__.py
- Phase 5 — Polish and Sync
- ConfigError
- errors.py
- slskd.py
- persist_first_run_acceptance
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- .parse_progress
- .submit_playlist
- FakeSlskd
- atomic_replace
- CI Workflow
- StockTickerTape
- ._load_selected_into_workbench_and_player
- ValidationError
- ._write_log
- phase1_analyze
- .submit_batch
- BatchConfirmScreen
- test_export_progress_callback_granularity
- P2P candidate scoring
- BatchScan
- Any
- .generate_residual
- yt-dlp metadata probe
- .generate_residual
- metadata_from_probe
- ._trigger_stem_separation
- FakeSlskdOffline
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- .on_button_pressed
- test_enhancement_provider_protocol_check
- mutagen tagging
- yt-dlp failure catalog
- ._emit_progress
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- presets.py
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
- harvester_analysis_enhancement_stem_separator
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
- ndarray
- Path
- harvester
- Resilience & Testing (docs/09-resilience-testing.md)
- Roadmap (docs/10-roadmap.md)
- rich_console
- SelectedChanged
- StrEnum
- Exception
- SlskdService
- EnhancementPreset
- ModelManager
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
- textual_widgets_selection_list

## God Nodes (most connected - your core abstractions)
1. `WorkbenchWidget` - 55 edges
2. `HarvesterApp` - 54 edges
3. `PipelineOrchestrator` - 54 edges
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

## Communities (204 total, 90 thin omitted)

### Community 0 - "stem_separator.py"
Cohesion: 0.07
Nodes (57): scipy, apply_adaptive_spectral_gate(), apply_adaptive_vad_gate(), _apply_dereverb_isolation(), apply_inst_remediations(), apply_inversion_subtraction(), _apply_lr4_crossover(), apply_mid_side_vocal_suppression() (+49 more)

### Community 1 - "pathlib"
Cohesion: 0.06
Nodes (41): collections_abc, harvester_analysis_enhancement, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_presets, harvester_analysis_enhancement_provider, harvester_services_model_manager, hashlib, logging (+33 more)

### Community 2 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 3 - "orchestrator.py"
Cohesion: 0.06
Nodes (52): datetime, harvester_pipeline_phase2_hunt, harvester_services_acoustid, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_retry, harvester_util_subproc (+44 more)

### Community 4 - "AcoustidService"
Cohesion: 0.06
Nodes (29): Process, AcoustidService, _earliest_release(), Fingerprint, _metadata_from_json(), _metadata_to_json(), _number(), Any (+21 more)

### Community 5 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 6 - "test_stem_separator.py"
Cohesion: 0.05
Nodes (51): fixture, get_stem_cache_suffix(), load_stem_profile(), Generate a compact, deterministic, collision-free filesystem cache suffix., Load user-selected imperfection profiles and settings for a stem directory.…, Path, Tests for Vocal and Instrumental Stem Separation service., Test that BS-RoFormer failure falls back to HDEMUCS when available. (+43 more)

### Community 7 - "test_orchestrator_m5.py"
Cohesion: 0.08
Nodes (25): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeSlskdOffline, FakeTagger, FakeYtdlp (+17 more)

### Community 8 - "AudioVisualizer"
Cohesion: 0.06
Nodes (26): AudioVisualizer, Path, Widget, Ensure the animation timer is active if paused during idle., Cycle through all 5 visualizer modes., Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses in-memory… (+18 more)

### Community 9 - "PreviewManager"
Cohesion: 0.06
Nodes (34): EnhancementExporter, Popen, PreviewManager, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes… (+26 more)

### Community 10 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 11 - "app.py"
Cohesion: 0.08
Nodes (35): collections, harvester_analysis_enhancement_eq, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge (+27 more)

### Community 12 - "HarvesterApp"
Cohesion: 0.06
Nodes (15): FlushPlan, HarvesterApp, wrapped(), Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Toggle visualizer between spectrum analyzer and oscilloscope., Seek backward 5 seconds in player., Seek forward 5 seconds in player. (+7 more)

### Community 13 - "read_slskd_credentials"
Cohesion: 0.08
Nodes (30): Any, MonkeyPatch, find_repo_root(), generate_api_key(), get_slskd_config_path(), get_slskd_template_path(), Path, Locate the OmniRip repository root directory. (+22 more)

### Community 14 - "logging_setup.py"
Cohesion: 0.08
Nodes (25): logging_handlers, LogRecord, Queue, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+17 more)

### Community 15 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 16 - "analysis/restoration.py"
Cohesion: 0.12
Nodes (31): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+23 more)

### Community 17 - "test_playlist.py"
Cohesion: 0.10
Nodes (16): harvester_util_circuit, _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp (+8 more)

### Community 18 - "ModelManager"
Cohesion: 0.09
Nodes (25): Path, ModelManager, ModelSpec, Path, Check if model checkpoint exists locally., Calculate and verify SHA-256 checksum of a file., Download a model checkpoint to the local cache directory. Args: model_name:…, Specification of an audio enhancement model checkpoint. (+17 more)

### Community 19 - "acoustid.py"
Cohesion: 0.10
Nodes (25): asyncio, dataclasses, httpx, json, mock, os, re, secrets (+17 more)

### Community 20 - "test_orchestrator_m4.py"
Cohesion: 0.13
Nodes (14): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, asyncio (+6 more)

### Community 21 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 22 - "scoring.py"
Cohesion: 0.11
Nodes (26): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+18 more)

### Community 23 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 24 - "harvester_util_errors"
Cohesion: 0.11
Nodes (21): harvester_analysis, harvester_util_errors, excerpt_window(), _excerpt_window(), SpectralResult, TrackJob, Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3). (+13 more)

### Community 25 - "FfmpegService"
Cohesion: 0.13
Nodes (16): harvester_services_ffmpeg, SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass. (+8 more)

### Community 26 - "FlashSRProvider"
Cohesion: 0.09
Nodes (19): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, FlashSR single-step distilled diffusion air-band generator. Generates ultra-…, HybridCoOpProvider, Hybrid multi-band provider: - NVSR reconstructs mid-high frequencies:… (+11 more)

### Community 27 - "test_ui_workbench.py"
Cohesion: 0.13
Nodes (27): harvester_analysis_enhancement_acoustic_detector, harvester_ui_visualizer, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench… (+19 more)

### Community 28 - "test_orchestrator_m3.py"
Cohesion: 0.12
Nodes (11): soundfile, _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio (+3 more)

### Community 29 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 30 - "test_bridge.py"
Cohesion: 0.11
Nodes (20): Apply, ErrorInfo, coalesce_events(), FlushPlan, JobEvent, Queue, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job. (+12 more)

### Community 31 - "AppConfig"
Cohesion: 0.23
Nodes (24): harvester_services_restoration, Restore a trashed original to its original location (FR-13 rollback step)., rollback(), AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch() (+16 more)

### Community 32 - "YtdlpService"
Cohesion: 0.14
Nodes (16): ProgressCallback, analyze_url(), Probe a single URL without downloading its media., Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A… (+8 more)

### Community 33 - "State"
Cohesion: 0.13
Nodes (19): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives…, Raise :class:`IllegalTransition` when the transition is not valid. (+11 more)

### Community 34 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 35 - "EnhancementExporter"
Cohesion: 0.13
Nodes (17): EnhancementPreset, EnhancementExporter, ndarray, Path, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+9 more)

### Community 36 - "WorkbenchWidget"
Cohesion: 0.13
Nodes (12): setter, Path, Run stem separation asynchronously with live progress and route stream when…, In-page audio enhancement and auditioning workbench panel. Supports real-time…, Pre-render remaining presets of the active mode so subsequent clicks are…, Route audio stream to player with zero-gap playhead preservation., WorkbenchWidget, update_progress() (+4 more)

### Community 37 - "ensure_2d_audio"
Cohesion: 0.16
Nodes (19): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+11 more)

### Community 38 - "MasteringEQSettings"
Cohesion: 0.10
Nodes (19): apply_mastering_eq(), MasteringEQSettings, ndarray, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+11 more)

### Community 39 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, harvester_services_slskd, mutagen, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 40 - "phase1_analyze.py"
Cohesion: 0.12
Nodes (18): harvester_pipeline_phase1_analyze, build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Build a deterministic fallback query from yt-dlp metadata., _text(), validate_url(), asyncio (+10 more)

### Community 41 - ".on_button_pressed"
Cohesion: 0.11
Nodes (11): Pressed, ComposeResult, Switch between 'deck', 'eq', and 'stems' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Human-readable descriptor for model blend weights., Human-readable descriptor for de-reverb intensity., Refresh blend weight value labels and descriptors after a change., Analyze track acoustics, vocal presence, and defects to auto-configure stems. (+3 more)

### Community 42 - "LogConsole"
Cohesion: 0.13
Nodes (14): RichLog, level_passes(), LogConsole, next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., A ``RichLog`` that filters by minimum severity and trims to a line cap. (+6 more)

### Community 43 - "analyze_track_acoustics"
Cohesion: 0.12
Nodes (22): AcousticAnalysisResult, analyze_track_acoustics(), ndarray, Diagnostic telemetry and auto-tuning recommendations from acoustic analysis., Perform fast acoustic and vocal-presence analysis on 2D audio (channels,…, _generate_synthetic_track(), ndarray, Test that heavy 300 Hz energy triggers de_mud remediation. (+14 more)

### Community 44 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 45 - "pytest"
Cohesion: 0.20
Nodes (13): harvester_ui_screens_soulseek_login, pytest, respx, Unit and integration tests for Soulseek configuration and in-app credential…, asyncio, Path, test_download_completes_and_locates_file(), test_download_uses_legacy_object_body_for_legacy_route() (+5 more)

### Community 46 - "environment.py"
Cohesion: 0.17
Nodes (12): check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the…, Check slskd health and, optionally, whether its OpenAPI endpoint is reachable. (+4 more)

### Community 47 - "ComposeResult"
Cohesion: 0.11
Nodes (8): FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, Non-blocking help overlay for the application., Confirm trash purge before deleting rollback sources (docs/08 §5, D5)., Legal/ToS notice shown once; acceptance persists to config (docs/01 §8, docs/08…

### Community 48 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 49 - ".on_select_changed"
Cohesion: 0.14
Nodes (10): Changed, Update comparative spectral gauges and dynamic mastering metrics based on…, Switch audition stream: [1] MP3, [2] ENH, [3] VOC, or [4] INST., Generate a short cache tag representing active EQ settings., Apply active 10-band EQ settings directly to the audio player in real-time., Apply EQ to active playback in real time and debounce background audio re-…, Asynchronously pre-generate the enhanced derivative., Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode. (+2 more)

### Community 50 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 51 - "titleclean.py"
Cohesion: 0.17
Nodes (17): Match, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase…, NFKD-normalize and fold diacritics to ASCII while keeping the case. (+9 more)

### Community 52 - "QualityEvidence"
Cohesion: 0.22
Nodes (15): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+7 more)

### Community 53 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 54 - "PipelineOrchestrator"
Cohesion: 0.19
Nodes (7): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 55 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 56 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 57 - "models.py"
Cohesion: 0.19
Nodes (14): EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., SkipReason, SourceKind (+6 more)

### Community 58 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 59 - "config.py"
Cohesion: 0.21
Nodes (15): AppPaths, copy, AcoustidConfig, BatchConfig, _build_config(), FfmpegConfig, GeneralConfig, Validated TOML configuration with file, environment, and CLI precedence. (+7 more)

### Community 60 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 61 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+1 more)

### Community 62 - "DefectChecklist"
Cohesion: 0.16
Nodes (6): DefectChecklist, Any, Directly tickable defect checklist with clean spacing and no vertical scrolling., Emitted when any checkbox option changes state., SelectedChanged, Vertical

### Community 63 - "SlskdService"
Cohesion: 0.26
Nodes (5): P2PCandidate, AsyncClient, Path, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 64 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 65 - "themes.py"
Cohesion: 0.20
Nodes (11): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+3 more)

### Community 66 - "._startup"
Cohesion: 0.14
Nodes (7): DependencyStatus, EnvironmentStatus, FatalSetupScreen, Shown when a required runtime dependency prevents acquisition., Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 67 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 68 - "CanonicalMetadata"
Cohesion: 0.26
Nodes (8): CanonicalMetadata, MetadataTagger, Path, Write only canonical fields plus explicit provenance and best-effort art., Path, test_flac_tagging_writes_vorbis_picture_and_provenance(), test_mp3_tagging_writes_id3v23_provenance_and_art(), _write_flac()

### Community 70 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 71 - "test_orchestrator.py"
Cohesion: 0.27
Nodes (7): FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path, test_orchestrator_cancel_marks_job_cancelled(), test_orchestrator_runs_fallback_path_with_fake_services()

### Community 72 - ".__init__"
Cohesion: 0.17
Nodes (5): AppConfig, PlaylistConfirmScreen, QuitConfirmScreen, Show entry count and cap before expanding a playlist (docs/08 §2, D10)., Confirm quit while jobs are still active (docs/08 §5, FR-17).

### Community 73 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 74 - "load_config"
Cohesion: 0.24
Nodes (12): _deep_merge(), load_config(), _load_toml(), Path, Load config with precedence CLI > environment > TOML > defaults., Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected() (+4 more)

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

### Community 79 - "ConfigError"
Cohesion: 0.27
Nodes (10): _apply_environment(), _bool(), section(), _float(), _int(), Any, Validate cross-field invariants and return this config for fluent use., Return diagnostic configuration without exposing secret values. (+2 more)

### Community 80 - "errors.py"
Cohesion: 0.30
Nodes (10): ErrorClass, HarvesterError, JobCancelled, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries., Base error carrying retry and user-facing classification metadata. (+2 more)

### Community 81 - "slskd.py"
Cohesion: 0.32
Nodes (11): _bool_or_none(), _concrete_paths(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), _pick_download_route(), Any (+3 more)

### Community 82 - "persist_first_run_acceptance"
Cohesion: 0.35
Nodes (10): _insert_general_key(), persist_first_run_acceptance(), Persist ``general.first_run_notice_accepted = true`` to the config file. A…, _config(), Config persistence tests for the first-run notice (docs/08 §2)., test_persist_appends_general_section_when_missing(), test_persist_creates_missing_file(), test_persist_inserts_missing_key_under_general() (+2 more)

### Community 83 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 84 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 85 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 86 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 87 - "test_batch_swap.py"
Cohesion: 0.31
Nodes (8): harvester_pipeline, _job(), Path, TrackJob, Atomic swap tests: FR-13 success and injected-failure rollback (docs/09 §7.1)., test_swap_failure_between_trash_and_replace_rolls_back(), test_swap_success_replaces_and_trashes(), test_swap_with_nested_file_uses_batch_root_for_trash()

### Community 88 - ".parse_progress"
Cohesion: 0.29
Nodes (8): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), YtdlpProgress, test_progress_parser_handles_machine_readable_line(), test_progress_parser_ignores_unrelated_lines()

### Community 89 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 90 - "FakeSlskd"
Cohesion: 0.31
Nodes (3): SearchResponse, SlskdFile, FakeSlskd

### Community 91 - "atomic_replace"
Cohesion: 0.31
Nodes (9): atomic_replace(), fsync_directory(), fsync_file(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a file's contents to stable storage., fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename. (+1 more)

### Community 92 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 93 - "StockTickerTape"
Cohesion: 0.28
Nodes (4): Label, Marquee stock ribbon ticker tape displaying real-time audio and model status., StockTickerTape, VisualType

### Community 94 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 95 - "ValidationError"
Cohesion: 0.42
Nodes (5): ConservativeRestorationService, ndarray, Path, Apply the deterministic restoration chain to a file without mutating it., ValidationError

### Community 97 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 98 - ".submit_batch"
Cohesion: 0.32
Nodes (5): BatchScan, Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., _remove_workspace()

### Community 99 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 100 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 101 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 102 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 104 - ".generate_residual"
Cohesion: 0.33
Nodes (4): Any, ndarray, Internal inference wrapper., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 105 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 106 - ".generate_residual"
Cohesion: 0.40
Nodes (3): Any, ndarray, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 107 - "metadata_from_probe"
Cohesion: 0.53
Nodes (6): metadata_from_probe(), Any, Build Phase M1 metadata fallback from yt-dlp probe fields., _text(), _year(), test_metadata_from_probe_uses_title_separator_and_uploader()

### Community 108 - "._trigger_stem_separation"
Cohesion: 0.33
Nodes (3): Initiate background stem separation for current track., Handle multi-choice checkbox toggling for stem defect remediations., Fallback compatibility handler for legacy SelectionList events.

### Community 110 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 111 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 112 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 113 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 116 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 117 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 119 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 120 - "presets.py"
Cohesion: 0.50
Nodes (3): EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1029 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **90 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `.submit_batch`, `orchestrator.py`, `._startup`, `TrackJob`, `test_orchestrator_m5.py`, `test_orchestrator.py`, `.__init__`, `test_playlist.py`, `test_orchestrator_m4.py`, `._emit_progress`, `.submit_playlist`, `.wait_for_idle`, `test_orchestrator_m3.py`, `test_orchestrator_m2.py`, `FfmpegService`, `AppConfig`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `orchestrator.py`, `AcoustidService`, `scanner.py`, `analysis/restoration.py`, `acoustid.py`, `harvester_util_errors`, `FfmpegService`, `YtdlpService`, `environment.py`, `CoverArtService`, `PipelineOrchestrator`, `config.py`, `SlskdService`, `load_config`, `.__init__`, `ConfigError`, `slskd.py`, `persist_first_run_acceptance`, `ValidationError`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `._write_log`, `._startup`, `BatchConfirmScreen`, `WorkbenchWidget`, `.__init__`, `PreviewManager`, `load_config`, `app.py`, `__main__.py`, `ComposeResult`, `.on_button_pressed`, `test_ui_pilot.py`, `._load_selected_into_workbench_and_player`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `StemSeparator`) actually correct?**
  _`WorkbenchWidget` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._