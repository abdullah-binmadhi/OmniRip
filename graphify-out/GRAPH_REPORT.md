# Graph Report - OmniRip  (2026-09-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2449 nodes · 4859 edges · 218 communities (126 shown, 92 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 501 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `55aff95c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- config.py
- AudioPlayerWidget
- scanner.py
- HarvesterApp
- Milestone M7 — QA & packaging
- analysis/restoration.py
- FlashSRProvider
- test_spectral.py
- pathlib
- test_playlist.py
- TrackJob
- app.py
- scoring.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- numpy
- test_orchestrator_m4.py
- test_orchestrator_m2.py
- ComposeResult
- test_stem_separator.py
- FfmpegService
- AppConfig
- PreviewManager
- State
- slskd_config.py
- WorkbenchWidget
- CanonicalMetadata
- test_phase4_spectral.py
- test_ui_workbench.py
- Pipeline orchestrator
- EnhancementExporter
- phase1_analyze.py
- ensure_2d_audio
- MasteringEQSettings
- test_orchestrator_m3.py
- orchestrator.py
- phase2_hunt.py
- test_batch_trash.py
- models.py
- Phase 1 — Input Analysis
- test_slskd_config.py
- AcoustidService
- .on_select_changed
- yt-dlp
- titleclean.py
- stem_separator.py
- QualityEvidence
- Spectral fixture connectivity gap
- PipelineOrchestrator
- test_model_manager.py
- test_batch_swap.py
- ValidationError
- StemSeparator
- CurationWorkbenchModal
- ytdlp.py
- BatchReport
- test_bridge.py
- SlskdService
- DependencyStatus
- AudioVisualizer
- test_ui_pilot.py
- EnhancementProvider
- JobTable
- test_orchestrator_m5.py
- Textual TUI
- ModelManager
- CircuitBreaker
- .__init__
- test_enhancement_workbench.py
- slskd.py
- Minimal Implementation Ladder
- .__init__
- phase2_hunt
- test_acoustid.py
- errors.py
- TrackJob
- SoulseekLoginModal
- test_enhancement_dsp.py
- player.py
- Mode B — Local Batch Audit
- AppPaths
- logconsole.py
- .render
- test_phase5_polish.py
- __main__.py
- Phase 5 — Polish and Sync
- SubprocessRegistry
- acoustid.py
- UiBridge
- httpx
- Path
- CoverArtService
- _mock_separate_bs_roformer
- Graphify Knowledge Graph
- cycle_theme
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- load_stem_profile
- .submit_batch
- .submit_playlist
- CI Workflow
- LogConsole
- ._load_selected_into_workbench_and_player
- check_soulseek_status
- phase1_analyze
- report.py
- BatchConfirmScreen
- test_export_progress_callback_granularity
- Path
- test_ui_visualizer.py
- P2P candidate scoring
- BatchScan
- Any
- .generate_residual
- yt-dlp metadata probe
- .generate_residual
- check_slskd
- PlaylistConfirmScreen
- ._resume_anim_timer
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- ._trigger_stem_separation
- FakeAcoustid
- FakeSlskdOffline
- mutagen tagging
- yt-dlp failure catalog
- .__init__
- Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation
- pytest
- presets.py
- test_stem_separator_multi_flag_fast_cache
- .__init__
- FakeCover
- FakeTagger
- FakeSlskd
- FakeSlskd
- FakeTagger
- FakeYtdlp
- OmniRip
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
1. `HarvesterApp` - 54 edges
2. `PipelineOrchestrator` - 54 edges
3. `WorkbenchWidget` - 48 edges
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

## Communities (218 total, 92 thin omitted)

### Community 0 - "config.py"
Cohesion: 0.05
Nodes (57): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+49 more)

### Community 1 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 2 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 3 - "HarvesterApp"
Cohesion: 0.06
Nodes (18): FlushPlan, HarvesterApp, wrapped(), Changed, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Cycle to next dynamic color theme., Open the Soulseek credentials and configuration dialog. (+10 more)

### Community 4 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 5 - "analysis/restoration.py"
Cohesion: 0.09
Nodes (35): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+27 more)

### Community 6 - "FlashSRProvider"
Cohesion: 0.07
Nodes (24): EnhancementProvider, harvester_services_enhancement, FlashSRProvider, ModelManager, Path, FlashSR single-step distilled diffusion air-band generator. Generates ultra-…, HybridCoOpProvider, Hybrid multi-band provider: - NVSR reconstructs mid-high frequencies:… (+16 more)

### Community 7 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 8 - "pathlib"
Cohesion: 0.08
Nodes (23): dataclasses, hashlib, logging_handlers, LogRecord, pathlib, platformdirs, Queue, Platform-aware runtime directories. (+15 more)

### Community 9 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 10 - "TrackJob"
Cohesion: 0.11
Nodes (29): difflib, harvester_pipeline_phase3_identify, Mutable job aggregate owned by the orchestrator., TrackJob, _first_orig(), identify_from_fallback(), identify_job(), _identity_shift() (+21 more)

### Community 11 - "app.py"
Cohesion: 0.10
Nodes (25): harvester_analysis_enhancement_eq, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge, harvester_ui_logconsole (+17 more)

### Community 12 - "scoring.py"
Cohesion: 0.11
Nodes (26): random, _expected_size(), _has_spam_hint(), is_hard_filtered(), _looks_transcoded(), rank_candidates(), P2P candidate hard filters and weighted scoring (docs/06 §7-§8)., Return whether a candidate fails the Phase 2 hard filters. (+18 more)

### Community 13 - "Harvester (Hybrid Music Harvest & Curation Engine)"
Cohesion: 0.09
Nodes (30): AC-2 — Mode A seeded FLAC end-to-end, AC-4 — Upscaled fixture rejected as FRAUD, AC-9 — AcoustID rate limit + cache, D11 — Dedup skip by MBID, D3 — Spectral check scope: P2P lossless claims only, D9 — Fingerprint before transcode, FR-10 — Provenance-based spectral exemption, FR-7 — Fingerprint before transcode (+22 more)

### Community 14 - "numpy"
Cohesion: 0.14
Nodes (18): collections_abc, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_model_manager, logging, numpy, 10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10., Enhancement provider protocol and base types for OmniRip M10. (+10 more)

### Community 15 - "test_orchestrator_m4.py"
Cohesion: 0.15
Nodes (13): _build(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path (+5 more)

### Community 16 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 17 - "ComposeResult"
Cohesion: 0.09
Nodes (12): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, QuitConfirmScreen, Non-blocking help overlay for the application. (+4 more)

### Community 18 - "test_stem_separator.py"
Cohesion: 0.10
Nodes (25): fixture, Path, Tests for Vocal and Instrumental Stem Separation service., Test that BS-RoFormer failure falls back to HDEMUCS when available., Verify adaptive spectral gate attenuates inter-phrase noise floor with smooth…, Verify vocal harmonic polish smooths isolated phase smearing., Verify phase-inversion subtraction extracts instrumental backing., Verify different songs maintain isolated caches without collisions. (+17 more)

### Community 19 - "FfmpegService"
Cohesion: 0.15
Nodes (14): harvester_services_ffmpeg, SourceKind, FfmpegService, Any, ndarray, Path, SubprocessRegistry, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass. (+6 more)

### Community 20 - "AppConfig"
Cohesion: 0.23
Nodes (24): harvester_services_restoration, AppConfig, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac(), _polish_mp3() (+16 more)

### Community 21 - "PreviewManager"
Cohesion: 0.12
Nodes (19): Popen, PreviewManager, EnhancementPreset, ndarray, Path, Launch audio file in the host operating system's default media player. Executes…, Manages rendering 15-second A/B comparison audio slices and triggering external…, Locate the start and end sample of the most energetic continuous excerpt.… (+11 more)

### Community 22 - "State"
Cohesion: 0.13
Nodes (19): enum, RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives… (+11 more)

### Community 23 - "slskd_config.py"
Cohesion: 0.14
Nodes (23): MonkeyPatch, secrets, find_repo_root(), generate_api_key(), get_slskd_config_path(), get_slskd_template_path(), Path, Management and auto-generation of local slskd configuration and credentials. (+15 more)

### Community 24 - "WorkbenchWidget"
Cohesion: 0.12
Nodes (13): Pressed, ComposeResult, Switch between 'deck' and 'eq' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Apply active 10-band EQ settings directly to the audio player in real-time., Apply EQ to active playback in real time and debounce background audio re-…, Refresh blend weight value labels after a change., Check or download all AI model weights and show status for all 4 models. (+5 more)

### Community 25 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (16): soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging., Build Phase M1 metadata fallback from yt-dlp probe fields. (+8 more)

### Community 26 - "test_phase4_spectral.py"
Cohesion: 0.14
Nodes (16): _excerpt_window(), SpectralResult, TrackJob, Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., run_spectral_check(), _config(), _FakeFailureFfmpeg, _FakeFfmpeg (+8 more)

### Community 27 - "test_ui_workbench.py"
Cohesion: 0.16
Nodes (23): Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer., Verify that EQ adjustments update the player's live audio filter across both… (+15 more)

### Community 28 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 29 - "EnhancementExporter"
Cohesion: 0.13
Nodes (17): EnhancementPreset, EnhancementExporter, ndarray, Path, Generate default output path for enhancement derivative., Decode input file, render enhanced audio, write MP3 derivative, and attach ID3…, Copy metadata tags from source and append strict provenance headers., Renders enhanced audio and exports MP3 derivatives with explicit provenance… (+9 more)

### Community 30 - "phase1_analyze.py"
Cohesion: 0.13
Nodes (19): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+11 more)

### Community 31 - "ensure_2d_audio"
Cohesion: 0.16
Nodes (19): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+11 more)

### Community 32 - "MasteringEQSettings"
Cohesion: 0.10
Nodes (19): apply_mastering_eq(), MasteringEQSettings, ndarray, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer., Set gain in dB for a specific band (-12dB to +12dB). (+11 more)

### Community 33 - "test_orchestrator_m3.py"
Cohesion: 0.15
Nodes (9): _build(), FakeAcoustid, FakeFfmpeg, FakeSlskd, FakeYtdlp, asyncio, Path, test_ground_truth_metadata_reaches_flac_output() (+1 more)

### Community 34 - "orchestrator.py"
Cohesion: 0.12
Nodes (17): asyncio, harvester_analysis, harvester_pipeline_phase2_hunt, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors, harvester_util_retry (+9 more)

### Community 35 - "phase2_hunt.py"
Cohesion: 0.12
Nodes (21): harvester_analysis_scoring, harvester_analysis_titleclean, mutagen, mutagen_flac, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number() (+13 more)

### Community 36 - "test_batch_trash.py"
Cohesion: 0.20
Nodes (20): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+12 more)

### Community 37 - "models.py"
Cohesion: 0.15
Nodes (17): datetime, EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., Why a scanned Mode B file is left untouched (docs/03 \u00a71B.3)., Return an aware UTC timestamp suitable for persisted events. (+9 more)

### Community 38 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 39 - "test_slskd_config.py"
Cohesion: 0.20
Nodes (14): harvester_services_slskd, harvester_ui_screens_soulseek_login, harvester_util_circuit, respx, Unit and integration tests for Soulseek configuration and in-app credential…, asyncio, Path, test_download_completes_and_locates_file() (+6 more)

### Community 40 - "AcoustidService"
Cohesion: 0.15
Nodes (6): AcoustidService, _metadata_to_json(), AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 41 - ".on_select_changed"
Cohesion: 0.15
Nodes (10): Changed, Generate a short cache tag representing active EQ settings., Asynchronously pre-generate the enhanced derivative., Pre-render remaining presets of the active mode so subsequent clicks are…, Route audio stream to player with zero-gap playhead preservation., Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode., Load a track job into the workbench, resolve streams, and pre-render ENH., Update comparative spectral gauges and dynamic mastering metrics based on… (+2 more)

### Community 42 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 43 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 44 - "stem_separator.py"
Cohesion: 0.17
Nodes (19): ndarray, scipy, apply_adaptive_spectral_gate(), apply_inst_remediations(), apply_inversion_subtraction(), apply_mid_side_vocal_suppression(), apply_vocal_harmonic_polish(), apply_vocal_remediations() (+11 more)

### Community 45 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 46 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 47 - "PipelineOrchestrator"
Cohesion: 0.18
Nodes (7): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 48 - "test_model_manager.py"
Cohesion: 0.13
Nodes (15): harvester_analysis_enhancement, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Verify that a dummy class adhering to EnhancementProvider satisfies isinstance…, Test model path resolution and caching checks in ModelManager., Verify SHA-256 calculation and verification., Test downloading a model via mocked huggingface_hub., Test that requesting an unknown model raises KeyError. (+7 more)

### Community 49 - "test_batch_swap.py"
Cohesion: 0.16
Nodes (16): harvester_pipeline, os, atomic_replace(), fsync_directory(), Path, Atomic filesystem helpers: fsync, replace, and crash-safe swaps (docs/02,…, fsync a directory fd so renames inside it survive a crash (POSIX only)., Atomically move ``source`` onto ``destination`` and persist the rename. (+8 more)

### Community 50 - "ValidationError"
Cohesion: 0.20
Nodes (10): ProgressCallback, Any, Exception, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+2 more)

### Community 51 - "StemSeparator"
Cohesion: 0.19
Nodes (14): load_audio_numpy(), State-of-the-Art Band-Split Rotary Position Transformer (BS-RoFormer).…, Multi-Stage Neural AI Pipeline: 1. HDEMUCS Source Separation (Chunked Hann-…, Save 2D float32 numpy array (channels, samples) to audio file with -1.0 dBFS…, Container for separated stem audio file paths and metadata., Multi-stage audio stem separation and de-bleeding service., Separate audio track into isolated vocals and instrumental backing using the…, Load audio file into a 2D float32 numpy array of shape (channels, samples). (+6 more)

### Community 52 - "CurationWorkbenchModal"
Cohesion: 0.12
Nodes (12): Open the detailed Curation Workbench modal for the selected job's audio file., CurationWorkbenchModal, Changed, ComposeResult, Pressed, Interactive modal dialog for previewing, auditioning, and exporting enhanced…, _MockApp, App (+4 more)

### Community 53 - "ytdlp.py"
Cohesion: 0.18
Nodes (14): shlex, DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress (+6 more)

### Community 54 - "BatchReport"
Cohesion: 0.16
Nodes (15): BatchReport, job_row(), TrackJob, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Row for a queued batch job that reached a terminal state (docs/03 §5.4)., Path (+7 more)

### Community 55 - "test_bridge.py"
Cohesion: 0.16
Nodes (14): ErrorInfo, coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7). (+6 more)

### Community 56 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 57 - "DependencyStatus"
Cohesion: 0.16
Nodes (9): DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Find a configured executable and run its version command without blocking the…, Run independent dependency checks concurrently., _run_version(), test_all_required_dependencies_ready_when_optional_services_are_down() (+1 more)

### Community 58 - "AudioVisualizer"
Cohesion: 0.12
Nodes (9): AudioVisualizer, Path, Widget, Set or clear the visual cutoff frequency marker (fc)., Manually update band energy levels., Fast-parse and pre-compute FFT frames from an audio file. Uses in-memory…, Pause playback visualization., Stop playback visualization and reset to idle. (+1 more)

### Community 59 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 60 - "EnhancementProvider"
Cohesion: 0.12
Nodes (13): importlib_util, Protocol, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers. (+5 more)

### Community 61 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 62 - "test_orchestrator_m5.py"
Cohesion: 0.26
Nodes (15): _build(), _mixed_library(), asyncio, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison., test_batch_audit_mixed_directory_ac5(), test_batch_failure_writes_failed_report_row() (+7 more)

### Community 63 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 64 - "ModelManager"
Cohesion: 0.19
Nodes (10): ModelManager, ModelSpec, Path, Download model checkpoint directly via streaming HTTP GET., Specification of an audio enhancement model checkpoint., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check if model checkpoint exists locally. (+2 more)

### Community 65 - "CircuitBreaker"
Cohesion: 0.17
Nodes (9): BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window(), test_failure_in_half_open_reopens() (+1 more)

### Community 66 - ".__init__"
Cohesion: 0.13
Nodes (10): AcoustidService, CoverArtService, DownloadProgress, EventKind, SlskdService, JobEvent, MetadataTagger, Queue (+2 more)

### Community 67 - "test_enhancement_workbench.py"
Cohesion: 0.16
Nodes (12): harvester_analysis_enhancement_presets, harvester_ui_screens_curation_workbench, mutagen_id3, platform, Headless preview generation and system audio player dispatch for OmniRip M10., subprocess, Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify all 5 planned presets exist and have valid attributes. (+4 more)

### Community 68 - "slskd.py"
Cohesion: 0.28
Nodes (10): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+2 more)

### Community 69 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 70 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 71 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 72 - "test_acoustid.py"
Cohesion: 0.31
Nodes (10): harvester_services_acoustid, Fingerprint, _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network() (+2 more)

### Community 73 - "errors.py"
Cohesion: 0.29
Nodes (12): ErrorClass, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited, Application error taxonomy used at service and pipeline boundaries. (+4 more)

### Community 75 - "SoulseekLoginModal"
Cohesion: 0.16
Nodes (7): ComposeResult, Path, Interactive modal dialog to enter Soulseek credentials and connect., SoulseekLoginModal, DummyModalApp, ComposeResult, test_soulseek_login_modal_compose()

### Community 76 - "test_enhancement_dsp.py"
Cohesion: 0.14
Nodes (13): Tests for DSP engine (Milestone 10-B)., Verify peak limiter confines signal to ceiling., Verify safe recombination of bands., Verify 1D and 2D conversions., Verify complementary band splitting sums to original signal., Verify sub-100Hz is mono and >250Hz preserves stereo., Verify residual energy is scaled to match reference band decay., test_apply_limiter() (+5 more)

### Community 77 - "player.py"
Cohesion: 0.21
Nodes (11): collections, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive…, Real-time Audio Visualizer Widget for OmniRip TUI. Provides multi-mode audio…, textual, textual_message (+3 more)

### Community 78 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 79 - "AppPaths"
Cohesion: 0.21
Nodes (9): AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it., Path, test_app_paths_are_isolated_and_created(), Path (+1 more)

### Community 80 - "logconsole.py"
Cohesion: 0.21
Nodes (10): level_passes(), next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., Log console filter tests (docs/08 §5: INFO -> DEBUG -> WARN+ERROR cycling)., test_level_passes_debug_shows_everything(), test_level_passes_info_hides_debug() (+2 more)

### Community 81 - ".render"
Cohesion: 0.22
Nodes (6): Mode 1: Multi-band Spectrum Analyzer with gravity peaks across 10 mastering…, Mode 3: Symmetrical Center-Mirrored Dance Spectrum., Mode 4: High-density 2x4 Unicode Braille audio wave matrix., Mode 5: Wide Stereo Dual-Deck VU Meter with decibel scales., Mode 2: Analog phosphor audio oscilloscope waveform., Text

### Community 82 - "test_phase5_polish.py"
Cohesion: 0.23
Nodes (11): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+3 more)

### Community 83 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 84 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 85 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 86 - "acoustid.py"
Cohesion: 0.38
Nodes (11): sqlite3, _earliest_release(), _metadata_from_json(), _number(), Any, AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache., Parse a numeric field as an integer (years and similar); None when not numeric., _release_year() (+3 more)

### Community 87 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 88 - "httpx"
Cohesion: 0.31
Nodes (8): httpx, Cover Art Archive client with a release-MBID disk cache., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches(), handler(), test_missing_cover_returns_none()

### Community 89 - "Path"
Cohesion: 0.18
Nodes (5): setter, Path, update_progress(), on_progress(), _ui()

### Community 90 - "CoverArtService"
Cohesion: 0.25
Nodes (4): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job.

### Community 91 - "_mock_separate_bs_roformer"
Cohesion: 0.20
Nodes (9): _mock_separate_bs_roformer(), Any, Verify progress callback reports steps and percentages monotonically., Verify BS-RoFormer inference produces isolated vocal and instrumental stems., Verify diagnostic profiles produce tailored stems and leverage cached raw stems., test_stem_separator_bs_roformer_execution(), test_stem_separator_diagnostic_profiles_and_fast_cache(), test_stem_separator_progress_callback() (+1 more)

### Community 92 - "Graphify Knowledge Graph"
Cohesion: 0.27
Nodes (10): Graph Sources (README.md, docs/*.md, Future Code), graphify-out/graph.json — Persistent Source of Truth, Graphify CLI Installation (uv tool install graphifyy / pip fallback), Optional Graphify Hook Hardening (post-commit auto-rebuild), Graphify Knowledge Graph, graphify-out Pipeline Outputs (graph.json, graph.html, GRAPH_REPORT.md), Query-First Rule (graphify query before re-reading files), Mandatory Per-Turn Update Rule (/graphify . --update) (+2 more)

### Community 93 - "cycle_theme"
Cohesion: 0.24
Nodes (8): App, cycle_theme(), Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, test_theme_registry_and_cycling(), ThemeTestApp

### Community 94 - "Error taxonomy"
Cohesion: 0.20
Nodes (10): P2P candidate selection, P2P post-download validation, Invalid-download quarantine, ConfigError, DiskError, Error taxonomy, Exponential retry with jitter, ServiceUnavailable (+2 more)

### Community 95 - "Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1"
Cohesion: 0.24
Nodes (10): Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1, Decision D3 — only P2P lossless-claiming files are spectrally checked, Threat (c) — 16-bit → fake 24-bit, Test fixture suite (7 fixtures, scipy/soundfile recipes), Threat (b) — 44.1 kHz → 96/192 kHz upsample (hi-res void), Threat (a) — MP3/AAC → FLAC upcast, q_spectral worker queue (one worker, ≈20 files/min), analysis/spectral.py (normative target of docs/04) (+2 more)

### Community 96 - "AcoustID lookup"
Cohesion: 0.22
Nodes (10): AcoustID confidence thresholds, AcoustID lookup, Canonical metadata, Cover Art Archive client, Best-effort cover art, Fingerprint downloaded source before transcoding, fpcalc and Chromaprint, Metadata fallback chain (+2 more)

### Community 97 - "load_stem_profile"
Cohesion: 0.27
Nodes (9): load_stem_profile(), Any, Path, Load user-selected imperfection profiles and settings for a stem directory.…, Save user-selected defect remediation profile to disk so OmniRip remembers the…, save_stem_profile(), Run stem separation asynchronously with live progress and route stream when…, Verify stem defect profiles save and load correctly. (+1 more)

### Community 98 - ".submit_batch"
Cohesion: 0.24
Nodes (7): _entry_tags(), BatchScan, Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 99 - ".submit_playlist"
Cohesion: 0.20
Nodes (5): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73)., Start workers and wait until shutdown is requested.

### Community 100 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 101 - "LogConsole"
Cohesion: 0.25
Nodes (4): RichLog, LogConsole, A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter.

### Community 102 - "._load_selected_into_workbench_and_player"
Cohesion: 0.22
Nodes (5): RowHighlighted, RowSelected, Play or pause the current track in the audio player., When user selects a job in the table, load its audio into workbench and player., When user navigates or clicks a job row, immediately load it into workbench.

### Community 103 - "check_soulseek_status"
Cohesion: 0.29
Nodes (7): Any, mock, check_soulseek_status(), Query local slskd daemon session and Soulseek network connection status., Pressed, test_check_soulseek_status_connected(), test_check_soulseek_status_unauthorized()

### Community 104 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 105 - "report.py"
Cohesion: 0.29
Nodes (7): json, batch_report_name(), Path, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``., Row for a file left untouched by the scanner (docs/03 §1B.3)., skipped_row()

### Community 106 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 107 - "test_export_progress_callback_granularity"
Cohesion: 0.25
Nodes (7): Path, Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify that ID3 provenance tags are correctly added to MP3 derivative., Verify that exporting never alters or removes the original file., test_apply_provenance_tags(), test_export_preserves_original_master(), test_export_progress_callback_granularity()

### Community 109 - "test_ui_visualizer.py"
Cohesion: 0.29
Nodes (6): ComposeResult, Unit tests for AudioVisualizer widget across all 5 visualizer modes., Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler., test_audio_visualizer_10bands_and_full_width_ruler(), test_audio_visualizer_modes_and_render(), VisualizerTestApp

### Community 110 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 111 - "BatchScan"
Cohesion: 0.33
Nodes (4): BatchEntry, BatchScan, One audio file discovered by the Mode B scanner (docs/03 \u00a71B)., Result of a Mode B directory scan with the pre-flight summary.

### Community 113 - ".generate_residual"
Cohesion: 0.33
Nodes (4): Any, ndarray, Internal inference wrapper., Generate high-frequency residual using NVSR, isolating strictly the band >…

### Community 114 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 115 - ".generate_residual"
Cohesion: 0.40
Nodes (3): Any, ndarray, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).

### Community 118 - "._resume_anim_timer"
Cohesion: 0.33
Nodes (3): Ensure the animation timer is active if paused during idle., Start active playback visualization., Seek the visualizer to an audio timestamp in seconds.

### Community 119 - "NFR-1 — Strict async"
Cohesion: 0.40
Nodes (5): AC-7 — UI responsiveness pilot, D8 — FFT in asyncio.to_thread, FR-16 — UI responsiveness, Never block (UI responsiveness) principle, NFR-1 — Strict async

### Community 120 - "phase3_identify"
Cohesion: 0.40
Nodes (5): AcoustID service, fpcalc plus AcoustID REST, MusicBrainz service, phase3_identify, q_identify stage queue

### Community 121 - "phase4_spectral"
Cohesion: 0.40
Nodes (5): FFmpeg decode pipe plus NumPy STFT, P2P_FLAC source kind, phase4_spectral, q_spectral stage queue, Spectral analysis module

### Community 122 - "Five-phase pipeline specification"
Cohesion: 0.40
Nodes (5): Five-phase pipeline specification, Timeout registry, Five-phase async pipeline prompt, Timeout registry directive, Two entry modes

### Community 123 - "._trigger_stem_separation"
Cohesion: 0.40
Nodes (3): SelectedChanged, Initiate background stem separation for current track., Handle multi-choice checkbox toggling for stem defect remediations.

### Community 126 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 127 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 128 - ".__init__"
Cohesion: 0.50
Nodes (3): EnhancementExporter, PreviewManager, Path

### Community 129 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 130 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

### Community 131 - "presets.py"
Cohesion: 0.50
Nodes (3): EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

### Community 132 - "test_stem_separator_multi_flag_fast_cache"
Cohesion: 0.50
Nodes (4): get_stem_cache_suffix(), Generate a compact, deterministic, collision-free filesystem cache suffix., Verify multi-choice flag sets generate distinct cached derivatives from raw…, test_stem_separator_multi_flag_fast_cache()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 978 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **92 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkbenchWidget` connect `WorkbenchWidget` to `load_stem_profile`, `HarvesterApp`, `test_ui_workbench.py`, `.on_select_changed`, `app.py`, `ComposeResult`, `StemSeparator`, `PreviewManager`, `Path`, `._trigger_stem_separation`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `config.py`, `test_orchestrator_m3.py`, `orchestrator.py`, `.__init__`, `.submit_batch`, `.submit_playlist`, `test_playlist.py`, `TrackJob`, `.wait_for_idle`, `test_orchestrator_m4.py`, `test_orchestrator_m2.py`, `FfmpegService`, `AppConfig`, `BatchReport`, `DependencyStatus`, `test_orchestrator_m5.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `config.py`, `._load_selected_into_workbench_and_player`, `.__init__`, `BatchConfirmScreen`, `app.py`, `ComposeResult`, `__main__.py`, `CurationWorkbenchModal`, `check_slskd`, `WorkbenchWidget`, `DependencyStatus`, `test_ui_pilot.py`, `cycle_theme`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `StemSeparator`) actually correct?**
  _`WorkbenchWidget` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._