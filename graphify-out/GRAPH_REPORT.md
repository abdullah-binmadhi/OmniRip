# Graph Report - OmniRip  (2026-09-20)

## Corpus Check
- 139 files · ~325,577 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 5, .toml 1, .tcss 1)

## Summary
- 2553 nodes · 5063 edges · 223 communities (124 shown, 99 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 522 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7350f7b9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- StemSeparator
- numpy
- AudioPlayerWidget
- test_batch_trash.py
- AcoustidService
- scanner.py
- test_stem_separator.py
- test_orchestrator_m5.py
- AudioVisualizer
- test_enhancement_workbench.py
- Milestone M7 — QA & packaging
- app.py
- HarvesterApp
- test_slskd_config.py
- logging_setup.py
- test_spectral.py
- analysis/restoration.py
- test_playlist.py
- test_model_manager.py
- pathlib
- test_orchestrator_m4.py
- TrackJob
- scoring.py
- Harvester (Hybrid Music Harvest & Curation Engine)
- phase4_spectral.py
- subprocess_options
- FlashSRProvider
- test_ui_workbench.py
- CircuitBreaker
- test_orchestrator_m2.py
- test_bridge.py
- phase5_polish.py
- YtdlpService
- State
- Pipeline orchestrator
- stem_separator.py
- WorkbenchWidget
- ensure_2d_audio
- EnhancementExporter
- phase2_hunt.py
- ValidationError
- .on_button_pressed
- logconsole.py
- analyze_track_acoustics
- Phase 1 — Input Analysis
- pytest
- AppConfig
- ._startup
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
- report.py
- DefectChecklist
- SlskdService
- Minimal Implementation Ladder
- textual_app
- .__init__
- phase2_hunt
- CanonicalMetadata
- TrackJob
- FfmpegService
- test_orchestrator.py
- PlaylistConfirmScreen
- Mode B — Local Batch Audit
- load_config
- test_phase5_polish.py
- .__init__
- __main__.py
- Phase 5 — Polish and Sync
- .public_dict
- errors.py
- slskd.py
- persist_first_run_acceptance
- Graphify Knowledge Graph
- Error taxonomy
- Spectral Anti-Fraud Check — FFT cutoff (brick-wall) detector, v1
- AcoustID lookup
- test_batch_swap.py
- ytdlp.py
- .submit_playlist
- BatchReport
- player.py
- CI Workflow
- StockTickerTape
- test_acoustid.py
- _mock_separate_bs_roformer
- ._run_guarded
- phase1_analyze
- .submit_batch
- BatchConfirmScreen
- test_enhancement_exporter.py
- P2P candidate scoring
- load_stem_profile
- Any
- NVSRProvider
- yt-dlp metadata probe
- SubprocessRegistry
- acoustid.py
- ._trigger_stem_separation
- FakeSlskdOffline
- NFR-1 — Strict async
- phase3_identify
- phase4_spectral
- Five-phase pipeline specification
- UiBridge
- test_enhancement_provider_protocol_check
- mutagen tagging
- yt-dlp failure catalog
- ModelManager
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
- ._download_direct_http
- ._resume_anim_timer
- LogConsole
- Path
- test_ui_visualizer.py
- analysis/enhancement/__init__.py
- QuitConfirmScreen
- FakeAcoustid
- FakeSlskdOffline
- _apply_dereverb_isolation
- _apply_lr4_crossover
- _apply_residual_inversion_loop
- .__init__
- update_progress
- FakeSlskd
- FakeTagger
- .load_audio_frames
- FakeCover
- harvester_analysis_enhancement_acoustic_detector

## God Nodes (most connected - your core abstractions)
1. `WorkbenchWidget` - 56 edges
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

## Communities (223 total, 99 thin omitted)

### Community 0 - "StemSeparator"
Cohesion: 0.16
Nodes (20): load_audio_numpy(), Path, Multi-stage audio stem separation and de-bleeding service., Separate audio track into isolated vocals and instrumental backing using the…, Load audio file into a 2D float32 numpy array of shape (channels, samples)., Eco DSP Stem Separation with adaptive gating and inversion polish., State-of-the-Art Band-Split Rotary Position Transformer (BS-RoFormer).…, Dual-Model Architecture Ensembling (BS-RoFormer + HDEMUCS). Combines: - Low… (+12 more)

### Community 1 - "numpy"
Cohesion: 0.11
Nodes (23): collections_abc, dataclasses, harvester_analysis_enhancement_dsp, harvester_analysis_enhancement_provider, harvester_services_model_manager, logging, numpy, platform (+15 more)

### Community 2 - "AudioPlayerWidget"
Cohesion: 0.05
Nodes (30): Click, Message, AudioPlayerWidget, InteractiveScrubber, ComposeResult, Path, Pressed, Text (+22 more)

### Community 3 - "test_batch_trash.py"
Cohesion: 0.20
Nodes (20): move_to_trash(), purge(), Path, Mode B trash lifecycle: layout, rollback, retention purge (docs/03 §5.3, D5).…, Return the trash directory for a scanned music directory., Move ``original`` into today's trash directory; return the trash path.…, Restore a trashed original to its original location (FR-13 rollback step)., Delete trash day-directories older than ``retention_days``; return count.… (+12 more)

### Community 4 - "AcoustidService"
Cohesion: 0.15
Nodes (6): AcoustidService, _metadata_to_json(), AsyncClient, Path, Fingerprint files and resolve canonical metadata, never failing the job., Fingerprint a file and resolve metadata; return None to use the fallback chain.

### Community 5 - "scanner.py"
Cohesion: 0.08
Nodes (50): BatchEntry, mutagen_aiff, mutagen_asf, mutagen_mp3, mutagen_mp4, mutagen_wave, mutagen_wavpack, SkipReason (+42 more)

### Community 6 - "test_stem_separator.py"
Cohesion: 0.08
Nodes (29): fixture, Path, Tests for Vocal and Instrumental Stem Separation service., Test that BS-RoFormer failure falls back to HDEMUCS when available., Verify adaptive spectral gate attenuates inter-phrase noise floor with smooth…, Verify vocal harmonic polish smooths isolated phase smearing., Verify phase-inversion subtraction extracts instrumental backing., Verify different songs maintain isolated caches without collisions. (+21 more)

### Community 7 - "test_orchestrator_m5.py"
Cohesion: 0.20
Nodes (16): _build(), FakeYtdlp, _mixed_library(), asyncio, Mode B orchestration: scan → queue → swap + trash + report exactly-once (AC-5)., Craft a minimal valid MPEG-1 Layer III file (mirrors test_batch_scanner)., Re-materialize the crafted 128 kbps MP3 for byte comparison., test_batch_audit_mixed_directory_ac5() (+8 more)

### Community 8 - "AudioVisualizer"
Cohesion: 0.12
Nodes (12): AudioVisualizer, Widget, Set or clear the visual cutoff frequency marker (fc)., Pause playback visualization., Stop playback visualization and reset to idle., Mode 1: Multi-band Spectrum Analyzer with gravity peaks across 10 mastering…, Mode 3: Symmetrical Center-Mirrored Dance Spectrum., Mode 4: High-density 2x4 Unicode Braille audio wave matrix. (+4 more)

### Community 9 - "test_enhancement_workbench.py"
Cohesion: 0.05
Nodes (37): EnhancementExporter, harvester_ui_screens_curation_workbench, Popen, PreviewManager, PreviewManager, EnhancementPreset, ndarray, Path (+29 more)

### Community 10 - "Milestone M7 — QA & packaging"
Cohesion: 0.08
Nodes (45): harvester 0.1.0 milestone-complete release (M0–M7), harvester project CHANGELOG, Milestone M0 — Scaffold & environment (CHANGELOG entry), Milestone M1 — Mode A fallback-only (CHANGELOG entry), Milestone M2 — slskd hunt lane (CHANGELOG entry), Milestone M3 — Ground-truth ID (CHANGELOG entry), Milestone M4 — Spectral anti-fraud (CHANGELOG entry), Milestone M5 — Mode B batch audit (CHANGELOG entry) (+37 more)

### Community 11 - "app.py"
Cohesion: 0.11
Nodes (21): harvester_analysis_enhancement_eq, harvester_analysis_enhancement_presets, harvester_pipeline_orchestrator, harvester_services_enhancement_exporter, harvester_services_enhancement_preview, harvester_services_environment, harvester_services_slskd_config, harvester_ui_bridge (+13 more)

### Community 12 - "HarvesterApp"
Cohesion: 0.05
Nodes (18): FlushPlan, RowHighlighted, RowSelected, HarvesterApp, Textual application connected to the asynchronous pipeline via a throttled…, Callback from the confirmation modal: queue the confirmed scan., Play or pause the current track in the audio player., Toggle visualizer between spectrum analyzer and oscilloscope. (+10 more)

### Community 13 - "test_slskd_config.py"
Cohesion: 0.05
Nodes (52): Any, harvester_services_slskd, harvester_ui_screens_soulseek_login, harvester_util_circuit, httpx, mock, MonkeyPatch, respx (+44 more)

### Community 14 - "logging_setup.py"
Cohesion: 0.08
Nodes (25): logging_handlers, LogRecord, Queue, AppPaths, Path, All paths used by harvester runtime state. The object is pure until…, Create runtime directories and return this immutable path set., Return a deterministic per-job directory without creating it. (+17 more)

### Community 15 - "test_spectral.py"
Cohesion: 0.13
Nodes (34): parametrize, analyze(), band_energies_db(), detect_cutoff(), _frames(), _fraud(), noise_reference(), ndarray (+26 more)

### Community 16 - "analysis/restoration.py"
Cohesion: 0.10
Nodes (34): _apply_limits(), AudioMetrics, _bounded(), correlation_interlock(), _enhance_transients(), measure_metrics(), _positive(), ndarray (+26 more)

### Community 17 - "test_playlist.py"
Cohesion: 0.10
Nodes (15): _entries(), FakeAcoustid, FakeCover, FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator() (+7 more)

### Community 18 - "test_model_manager.py"
Cohesion: 0.13
Nodes (18): harvester_analysis_enhancement, hashlib, Path, Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)., Test that requesting an unknown model raises KeyError., Test downloading a model via direct HTTP streaming fallback when…, Test downloading hdemucs using fallback direct_url when torchaudio fails., Test model path resolution and caching checks in ModelManager. (+10 more)

### Community 19 - "pathlib"
Cohesion: 0.13
Nodes (16): asyncio, harvester_pipeline_phase2_hunt, harvester_services_musicbrainz, harvester_services_tagging, harvester_services_ytdlp, harvester_util_errors, harvester_util_retry, harvester_util_subproc (+8 more)

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

### Community 24 - "phase4_spectral.py"
Cohesion: 0.12
Nodes (20): harvester_analysis, excerpt_window(), _excerpt_window(), SpectralResult, TrackJob, Phase 4 gate: run the spectral check on P2P lossless claims only., Gate a P2P file claiming lossless quality (docs/03 Phase 4, D3)., Normative offset/length selection per docs/04 §2. (+12 more)

### Community 25 - "subprocess_options"
Cohesion: 0.20
Nodes (9): SourceKind, Any, ndarray, Path, Probe duration, sample rate, codec, and channels in a single ffprobe JSON pass., Decode a mono excerpt to float32 PCM without blocking the loop., Any, Return portable process-group options for subprocess creation. (+1 more)

### Community 26 - "FlashSRProvider"
Cohesion: 0.07
Nodes (22): EnhancementProvider, harvester_services_enhancement, ConservativeDSPProvider, Non-neural harmonic exciter providing subtle, mathematically bounded high-end…, FlashSRProvider, Any, ndarray, Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)). (+14 more)

### Community 27 - "test_ui_workbench.py"
Cohesion: 0.13
Nodes (26): ComposeResult, Path, Unit tests for WorkbenchWidget in-page layout, dual-stream audition, and player…, Verify that auditioning does not pollute output dir until button is clicked., Verify that user can toggle between Eco DSP mode and Neural AI mode, and access…, Verify that: 1. Eco Mode reveals only the first 2 options (Conservative DSP and…, Verify that: 1. The signal chain pipeline and telemetry grid fill the workbench…, Verify Workbench 2-page system and interactive 10-band equalizer. (+18 more)

### Community 28 - "CircuitBreaker"
Cohesion: 0.07
Nodes (20): enum, BreakerState, CircuitBreaker, StrEnum, Circuit breaker for the slskd lane (docs/09 §3)., Fast-fail a dependency lane after consecutive failures., test_breaker_opens_after_three_failures(), test_breaker_recovers_after_open_window() (+12 more)

### Community 29 - "test_orchestrator_m2.py"
Cohesion: 0.18
Nodes (15): FakeFfmpeg, FakeSlskd, FakeTagger, FakeYtdlp, _orchestrator(), asyncio, Path, test_best_available_rejects_peer_with_long_queue() (+7 more)

### Community 30 - "test_bridge.py"
Cohesion: 0.16
Nodes (14): ErrorInfo, coalesce_events(), FlushPlan, UI bridge: throttle and coalesce pipeline events into widget updates (docs/08…, One throttled batch of UI updates., Reduce a burst of events to one plan; latest STATE/PROGRESS wins per job., asyncio, UiBridge tests: coalescing semantics and throttled flushing (docs/08 §3, AC-7). (+6 more)

### Community 31 - "phase5_polish.py"
Cohesion: 0.15
Nodes (32): harvester_services_restoration, os, _batch_target_path(), _choose_output_path(), _mutagen_parses(), polish_batch(), _polish_flac(), _polish_mp3() (+24 more)

### Community 32 - "YtdlpService"
Cohesion: 0.19
Nodes (10): ProgressCallback, Validate cross-field invariants and return this config for fluent use., Any, Path, Queue, Return the flat playlist entries for a URL (docs/03 Phase 1A \u00a73, D10). A…, Probe and download with yt-dlp while keeping progress machine-readable., YtdlpService (+2 more)

### Community 33 - "State"
Cohesion: 0.14
Nodes (18): RuntimeError, Apply one guarded state transition through the canonical state machine., assert_transition(), IllegalTransition, is_transition_allowed(), legal_transitions(), The single source of truth for legal job-state transitions. ``State`` lives…, Raise :class:`IllegalTransition` when the transition is not valid. (+10 more)

### Community 34 - "Pipeline orchestrator"
Cohesion: 0.12
Nodes (23): Batch report writer, FFmpeg service, Atomic filesystem helpers, HarvestApp, JobEvent, Pipeline orchestrator, phase5_polish, Python 3.11 and asyncio (+15 more)

### Community 35 - "stem_separator.py"
Cohesion: 0.15
Nodes (22): scipy, apply_adaptive_spectral_gate(), apply_adaptive_vad_gate(), apply_inst_remediations(), apply_inversion_subtraction(), apply_mid_side_vocal_suppression(), apply_vocal_harmonic_polish(), apply_vocal_remediations() (+14 more)

### Community 36 - "WorkbenchWidget"
Cohesion: 0.17
Nodes (10): setter, Path, Run stem separation asynchronously with live progress and route stream when…, Generate a short cache tag representing active EQ settings., In-page audio enhancement and auditioning workbench panel. Supports real-time…, Pre-render remaining presets of the active mode so subsequent clicks are…, Route audio stream to player with zero-gap playhead preservation., Toggle between Eco DSP mode (cool, zero heat) and Neural AI mode. (+2 more)

### Community 37 - "ensure_2d_audio"
Cohesion: 0.09
Nodes (31): apply_limiter(), apply_progressive_mono(), ensure_2d_audio(), match_spectral_slope(), ndarray, Digital Signal Processing (DSP) engine for OmniRip M10 audio enhancement.…, Match the residual high-frequency energy to follow the natural spectral decay…, Ensure audio is 2D array of shape (channels, samples). Returns:… (+23 more)

### Community 38 - "EnhancementExporter"
Cohesion: 0.07
Nodes (31): EnhancementPreset, apply_mastering_eq(), MasteringEQSettings, ndarray, Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass., Convert active EQ settings to an FFmpeg audio filter (-af) string for real-time…, Apply zero-phase 10-band mastering equalization and acoustic conditioning.…, Settings state for the 10-Band Studio Equalizer. (+23 more)

### Community 39 - "phase2_hunt.py"
Cohesion: 0.13
Nodes (20): harvester_analysis_scoring, harvester_analysis_titleclean, mutagen, P2PCandidate, build_hunt_queries(), hunt_and_score(), _number(), prepare_fallback() (+12 more)

### Community 40 - "ValidationError"
Cohesion: 0.13
Nodes (20): harvester_pipeline_phase1_analyze, analyze_url(), build_query(), Mode A URL analysis stage., Validate and normalize a URL before passing it to yt-dlp., Probe a single URL without downloading its media., Build a deterministic fallback query from yt-dlp metadata., _text() (+12 more)

### Community 41 - ".on_button_pressed"
Cohesion: 0.12
Nodes (10): Pressed, ComposeResult, Switch between 'deck', 'eq', and 'stems' tabs inside the inspector container., Update all 10 band labels, values, fader tracks, and control buttons., Human-readable descriptor for model blend weights., Human-readable descriptor for de-reverb intensity., Refresh blend weight value labels and descriptors after a change., Analyze track acoustics, vocal presence, and defects to auto-configure stems. (+2 more)

### Community 42 - "logconsole.py"
Cohesion: 0.21
Nodes (10): level_passes(), next_mode(), Log console: level-filtered, capped RichLog (docs/08 §2/§4)., Return whether ``level`` (upper) should be shown under ``mode``., Return the next filter mode in the cycle., Log console filter tests (docs/08 §5: INFO -> DEBUG -> WARN+ERROR cycling)., test_level_passes_debug_shows_everything(), test_level_passes_info_hides_debug() (+2 more)

### Community 43 - "analyze_track_acoustics"
Cohesion: 0.12
Nodes (25): AcousticAnalysisResult, analyze_track_acoustics(), ndarray, Acoustic Music & Vocal Presence Detector for OmniRip. Performs high-speed…, Diagnostic telemetry and auto-tuning recommendations from acoustic analysis., Perform fast acoustic and vocal-presence analysis on 2D audio (channels,…, _load_and_analyze(), _generate_synthetic_track() (+17 more)

### Community 44 - "Phase 1 — Input Analysis"
Cohesion: 0.10
Nodes (21): Mode A URL probe, Mode B directory scan, Phase 1 — Input Analysis, Phase 2 — Hybrid Hunt, Query cleaning, Shared 25-second query budget, slskd health check, Startup OpenAPI verification (+13 more)

### Community 45 - "pytest"
Cohesion: 0.67
Nodes (3): pytest, asyncio, test_registry_terminates_process_by_job_prefix()

### Community 46 - "AppConfig"
Cohesion: 0.16
Nodes (13): AppConfig, check_slskd(), DependencyStatus, detect_environment(), EnvironmentStatus, probe_binary(), Asynchronous startup checks for local binaries and optional services., Find a configured executable and run its version command without blocking the… (+5 more)

### Community 47 - "._startup"
Cohesion: 0.10
Nodes (10): FatalSetupScreen, FirstRunNoticeScreen, HelpScreen, PurgeConfirmScreen, ComposeResult, Pressed, Non-blocking help overlay for the application., Confirm trash purge before deleting rollback sources (docs/08 §5, D5). (+2 more)

### Community 48 - "yt-dlp"
Cohesion: 0.11
Nodes (20): AC-3 — slskd stopped fallback to yt-dlp, D10 — Playlist cap 50 + confirmation, D12 — fallback_attempted anti-loop flag, D6 — slskd OpenAPI route verification, FR-1 — Extract metadata without downloading, FR-2 — slskd lossless search & scoring, FR-3 — P2P timeout fallback to yt-dlp, FR-4 — yt-dlp best audio-only raw download (+12 more)

### Community 49 - ".on_select_changed"
Cohesion: 0.17
Nodes (8): Changed, Update comparative spectral gauges and dynamic mastering metrics based on…, Switch audition stream: [1] MP3, [2] ENH, [3] VOC, or [4] INST., Apply active 10-band EQ settings directly to the audio player in real-time., Apply EQ to active playback in real time and debounce background audio re-…, Asynchronously pre-generate the enhanced derivative., Load a track job into the workbench, resolve streams, and pre-render ENH., TrackJob

### Community 50 - "Spectral fixture connectivity gap"
Cohesion: 0.12
Nodes (19): Retry and circuit-breaker utilities, Fallback triggers, slskd circuit breaker, slskd degraded mode, Fallback audio download, Machine-readable progress, Fallback post-download validation, Circuit breaker (+11 more)

### Community 51 - "titleclean.py"
Cohesion: 0.16
Nodes (18): Match, re, build_queries(), clean_title(), _ellipsis_if_noise(), fold_unicode(), _normalize(), Deterministic query construction for the P2P hunt. Implements docs/03 Phase… (+10 more)

### Community 52 - "QualityEvidence"
Cohesion: 0.21
Nodes (16): assess_replacement(), _assessment(), quality_score(), QualityEvidence, Source-quality evidence and replacement decisions for library upgrades. This…, Return a conservative comparable score; synthetic high bands never add quality., Measured or probed evidence about one candidate audio source., Explain whether a candidate is safe to offer as a replacement. (+8 more)

### Community 53 - "CoverArtService"
Cohesion: 0.17
Nodes (10): CoverArtService, AsyncClient, Path, Best-effort front-cover fetching; failures never fail a job., _config(), asyncio, Path, test_fetch_front_returns_bytes_and_caches() (+2 more)

### Community 54 - "PipelineOrchestrator"
Cohesion: 0.16
Nodes (8): Exception, PipelineOrchestrator, Purge the most recent batch's trash per ``batch.trash_retention_days`` (D5)., Start workers and wait until shutdown is requested., Append the terminal report row for a Mode B job (FR-14: per completed job)., Own jobs, bounded stage queues, and the pipeline-to-UI event contract., StageHandler, Task

### Community 55 - "test_ui_pilot.py"
Cohesion: 0.22
Nodes (11): _app(), asyncio, UI pilot tests for M6 bindings, modals, and bridge rendering (docs/08 §9)., Minimal orchestrator stand-in for UI pilots (no services, no network)., StubOrchestrator, test_apply_flush_log_lines_reach_console(), test_apply_flush_renders_job_row(), test_log_level_cycles_on_l_key() (+3 more)

### Community 56 - "EnhancementProvider"
Cohesion: 0.20
Nodes (7): Protocol, EnhancementProvider, ndarray, Protocol governing high-frequency audio enhancement providers., Human-readable name of the enhancement provider., Whether the provider's dependencies and weights are ready for inference., Generate the high-frequency residual signal strictly above cutoff_hz. Args:…

### Community 57 - "models.py"
Cohesion: 0.13
Nodes (18): BatchEntry, BatchScan, EventKind, JobEvent, Mode, StrEnum, Domain models shared by the pipeline, services, and UI., One audio file discovered by the Mode B scanner (docs/03 \u00a71B). (+10 more)

### Community 58 - "JobTable"
Cohesion: 0.23
Nodes (4): JobTable, TrackJob, Return whether a job already has a visible row (used by tests and callers)., Live job table with render-hash diffing and a visible-row cap (docs/08 §3/§4).

### Community 59 - "config.py"
Cohesion: 0.16
Nodes (23): AppPaths, copy, AcoustidConfig, _apply_environment(), BatchConfig, _bool(), _build_config(), section() (+15 more)

### Community 60 - "Textual TUI"
Cohesion: 0.14
Nodes (16): DirectoryPicker, Event coalescing and throttling, InputRow, JobEvent queue, JobTable, TUI layout, LogConsole, PlaylistConfirm (+8 more)

### Community 61 - "report.py"
Cohesion: 0.16
Nodes (13): datetime, json, batch_report_name(), job_row(), Path, TrackJob, Mode B batch report: append-only JSONL per completed job (docs/03 §5.4, FR-14)., Report filename per docs/02 §3: ``<dirname>-<UTC timestamp>.jsonl``. (+5 more)

### Community 62 - "DefectChecklist"
Cohesion: 0.16
Nodes (6): DefectChecklist, Any, Directly tickable defect checklist with clean spacing and no vertical scrolling., Emitted when any checkbox option changes state., SelectedChanged, Vertical

### Community 63 - "SlskdService"
Cohesion: 0.20
Nodes (8): P2PCandidate, _concrete_paths(), _pick_download_route(), AsyncClient, Path, Expand slskd's templated OpenAPI routes (0.26+) to concrete ``/api/v0/`` forms.…, Talk to the local slskd daemon; policy stays in the pipeline., SlskdService

### Community 64 - "Minimal Implementation Ladder"
Cohesion: 0.18
Nodes (14): Guard: Lazy about the Solution, Never about Reading, Guard: Spec-Mandated Bodies Are Requirements, Not YAGNI Candidates, Guard: Never Skip Validation, Error Handling, Cancellation, Timeouts, or Tests, Rung 5: Installed Dependency Does It? (textual, httpx, mutagen, yt-dlp, numpy), Rung 7: The Minimum That Works, Rung 4: Native/Platform Feature Does It? (OS APIs, ffmpeg, shell), Rung 6: One Line? (one line), Rung 2: Already in This Codebase? (reuse, don't rewrite) (+6 more)

### Community 65 - "textual_app"
Cohesion: 0.17
Nodes (13): App, cycle_theme(), Theme registry and dynamic switcher for OmniRip TUI., Register custom OmniRip palettes with the Textual app theme manager., Cycle to the next available theme, apply it to the app, and return the human-…, register_custom_themes(), ComposeResult, Unit tests for theme registry and dynamic cycling. (+5 more)

### Community 66 - ".__init__"
Cohesion: 0.15
Nodes (6): AppConfig, DependencyStatus, EnvironmentStatus, Compact service-status line rendered below Textual's title header., StatusBar, Static

### Community 67 - "phase2_hunt"
Cohesion: 0.14
Nodes (14): phase2_hunt, q_hunt stage queue, q_p2p_dl stage queue, Candidate scoring analysis, Direct slskd REST client, slskd service, State machine, Title cleaning analysis (+6 more)

### Community 68 - "CanonicalMetadata"
Cohesion: 0.16
Nodes (17): mutagen_flac, soundfile, CanonicalMetadata, metadata_from_probe(), MetadataTagger, Any, Path, Deterministic MP3 (ID3v2.3) and FLAC (Vorbis + picture) tagging. (+9 more)

### Community 70 - "FfmpegService"
Cohesion: 0.16
Nodes (10): harvester_services_ffmpeg, FfmpegService, SubprocessRegistry, Run FFmpeg tools in killable subprocesses with explicit deadlines., Build the deterministic Phase 5 transcode arguments., Path, test_build_mp3_320_arguments(), test_build_mp3_v0_arguments() (+2 more)

### Community 71 - "test_orchestrator.py"
Cohesion: 0.27
Nodes (7): FakeFfmpeg, FakeTagger, FakeYtdlp, asyncio, Path, test_orchestrator_cancel_marks_job_cancelled(), test_orchestrator_runs_fallback_path_with_fake_services()

### Community 73 - "Mode B — Local Batch Audit"
Cohesion: 0.22
Nodes (13): AC-5 — Mode B mixed directory audit, AC-6 — SIGTERM mid-batch safety, D1 — Single bitrate threshold (default 256), D13 — Mode B fallback via ytsearch1 + swap temps, D4 — Keep original filename/path, D5 — .trash/ retention (7 days), FR-13 — Atomic Mode B replacement, FR-14 — Incremental JSONL batch report (+5 more)

### Community 74 - "load_config"
Cohesion: 0.22
Nodes (12): _deep_merge(), load_config(), _load_toml(), Path, Load config with precedence CLI > environment > TOML > defaults., Path, test_defaults_are_valid_and_use_the_requested_data_dir(), test_invalid_url_is_rejected() (+4 more)

### Community 75 - "test_phase5_polish.py"
Cohesion: 0.26
Nodes (10): _config(), asyncio, Phase 5 polish unit tests: path helpers, target selection, keep-opus guard., test_batch_target_canonical_when_enabled(), test_batch_target_default_keeps_original_path(), test_choose_output_path_collision_suffix(), test_mutagen_parses_rejects_garbage(), test_polish_stream_rejects_keep_opus() (+2 more)

### Community 76 - ".__init__"
Cohesion: 0.17
Nodes (9): AcoustidService, CoverArtService, EventKind, SlskdService, JobEvent, MetadataTagger, Queue, SubprocessRegistry (+1 more)

### Community 77 - "__main__.py"
Cohesion: 0.23
Nodes (10): argparse, ArgumentParser, harvester, build_parser(), main(), Command-line entry point for the OmniRip TUI., sys, test_enhance_cli_nonexistent_file() (+2 more)

### Community 78 - "Phase 5 — Polish and Sync"
Cohesion: 0.17
Nodes (12): Batch trash manager, Fallback transcoding, Incremental JSONL batch report, Mode A final placement, Mode B atomic swap, Phase 4 — Spectral Check, Phase 5 — Polish and Sync, P2P spectral gate (+4 more)

### Community 80 - "errors.py"
Cohesion: 0.24
Nodes (13): ErrorClass, Exception, HarvesterError, JobCancelled, PermanentSource, Any, Exception, RateLimited (+5 more)

### Community 81 - "slskd.py"
Cohesion: 0.28
Nodes (10): _bool_or_none(), _float_or_none(), _int_or_none(), _matches_candidate(), _parse_search_payload(), Any, Async slskd REST client with health, search, download, and transfer polling., SearchResponse (+2 more)

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

### Community 88 - "ytdlp.py"
Cohesion: 0.32
Nodes (9): DownloadProgress, _parse_int(), _parse_optional_int(), _parse_percent(), _parse_speed(), Killable yt-dlp subprocess integration for Mode A., YtdlpProgress, test_progress_parser_handles_machine_readable_line() (+1 more)

### Community 89 - ".submit_playlist"
Cohesion: 0.29
Nodes (4): _number(), Any, Return playlist entries capped at ``batch.playlist_cap`` (D10)., Expand a playlist into child Mode A jobs (docs/03 Phase 1A \u00a73).

### Community 90 - "BatchReport"
Cohesion: 0.20
Nodes (12): BatchReport, Append-only, per-row-flush JSONL report. One row per input file (AC-5)., Serialize ``row`` and persist it immediately (crash loses ≤ 1 record)., Read back every persisted row (used by tests and summaries)., Path, Batch report tests: schema, incremental appends, row builders (FR-14)., test_append_writes_all_schema_fields(), test_appends_are_incremental_and_order_preserved() (+4 more)

### Community 91 - "player.py"
Cohesion: 0.19
Nodes (12): collections, math, rich_style, rich_text, In-app Audio Player widget with real-time spectrum, oscilloscope, interactive…, Real-time Audio Visualizer Widget for OmniRip TUI. Provides multi-mode audio…, textual, textual_message (+4 more)

### Community 92 - "CI Workflow"
Cohesion: 0.22
Nodes (9): CI Workflow, GitHub Actions, harvester.analysis, harvester.batch, harvester.pipeline, harvester.util, pytest, Ruff (+1 more)

### Community 93 - "StockTickerTape"
Cohesion: 0.28
Nodes (4): Label, Marquee stock ribbon ticker tape displaying real-time audio and model status., StockTickerTape, VisualType

### Community 94 - "test_acoustid.py"
Cohesion: 0.31
Nodes (10): harvester_services_acoustid, Fingerprint, _config(), asyncio, Path, test_lookup_maps_fields_and_prefers_earliest_release(), handler(), test_lookup_uses_cache_and_skips_network() (+2 more)

### Community 95 - "_mock_separate_bs_roformer"
Cohesion: 0.15
Nodes (12): _mock_separate_bs_roformer(), Any, Verify progress callback reports steps and percentages monotonically., Verify BS-RoFormer inference produces isolated vocal and instrumental stems., Verify diagnostic profiles produce tailored stems and leverage cached raw stems., Verify force_reseparate=True bypasses cached results and runs separation anew., test_stem_separator_bs_roformer_execution(), test_stem_separator_diagnostic_profiles_and_fast_cache() (+4 more)

### Community 96 - "._run_guarded"
Cohesion: 0.13
Nodes (5): wrapped(), Changed, Cycle to next dynamic color theme., Open the Soulseek credentials and configuration dialog., Submitted

### Community 97 - "phase1_analyze"
Cohesion: 0.25
Nodes (8): Batch scanner, phase1_analyze, q_analyze stage queue, q_fallback_dl stage queue, Tracked subprocess registry, yt-dlp service, yt-dlp subprocess isolation, Cancellation and shutdown semantics

### Community 98 - ".submit_batch"
Cohesion: 0.24
Nodes (7): _entry_tags(), BatchScan, Path, Scan a music directory without creating jobs (pre-flight, docs/03 \u00a71B.5)., Queue a Mode B directory audit: free-space guard, report, jobs (FR-13/14)., Carry the scanned tags onto the job so Phase 3 can fall back to them (docs/03…, _remove_workspace()

### Community 99 - "BatchConfirmScreen"
Cohesion: 0.29
Nodes (3): BatchConfirmScreen, Confirmation for scans that queue more than 25 upgrade jobs (docs/03 §1B.5)., Scan a directory; queue immediately unless confirmation is required.

### Community 100 - "test_enhancement_exporter.py"
Cohesion: 0.11
Nodes (18): mutagen_id3, Path, Tests for EnhancementExporter and Presets (Milestone 10-D)., Verify that EnhancementExporter toggles neural acceleration across all…, Verify all 5 planned presets exist and have valid attributes., Verify that export_enhanced_derivative calls progress_callback with granular AI…, Verify render_audio_buffer produces valid audio for every preset., Verify that ID3 provenance tags are correctly added to MP3 derivative. (+10 more)

### Community 101 - "P2P candidate scoring"
Cohesion: 0.29
Nodes (7): P2P candidate scoring, P2P download lifecycle, slskd file handoff, P2P hard filters, P2P validation quarantine, Search and transfer polling, slskd search request

### Community 102 - "load_stem_profile"
Cohesion: 0.18
Nodes (13): get_safe_neural_device(), get_stem_cache_suffix(), load_stem_profile(), Any, Generate a compact, deterministic, collision-free filesystem cache suffix., Return the safest and most stable PyTorch device for neural audio separation., Load user-selected imperfection profiles and settings for a stem directory.…, Save user-selected defect remediation profile to disk so OmniRip remembers the… (+5 more)

### Community 104 - "NVSRProvider"
Cohesion: 0.16
Nodes (9): NVSRProvider, Any, ModelManager, ndarray, Path, Internal inference wrapper., NVSR non-diffusion base neural stabilization provider. Executes super-…, True if neural acceleration is enabled, torch is installed, and weights are… (+1 more)

### Community 105 - "yt-dlp metadata probe"
Cohesion: 0.33
Nodes (6): yt-dlp binary management, yt-dlp metadata probe, Playlist expansion, yt-dlp subprocess lane, Fake external services, Integration test plan

### Community 106 - "SubprocessRegistry"
Cohesion: 0.24
Nodes (3): Process, Track child processes by job key so cancellation can kill the right work., SubprocessRegistry

### Community 107 - "acoustid.py"
Cohesion: 0.38
Nodes (11): sqlite3, _earliest_release(), _metadata_from_json(), _number(), Any, AcoustID client: fpcalc fingerprinting, rate-limited lookup, SQLite cache., Parse a numeric field as an integer (years and similar); None when not numeric., _release_year() (+3 more)

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

### Community 114 - "UiBridge"
Cohesion: 0.20
Nodes (7): Apply, JobEvent, Queue, Drain ``events`` on a fixed cadence and apply coalesced plans., Drain everything currently queued (non-blocking) and coalesce it., Loop forever, flushing at most once per ``interval_s``., UiBridge

### Community 116 - "mutagen tagging"
Cohesion: 0.50
Nodes (4): FLAC Vorbis comments and picture block, ID3v2.3 tags, mutagen tagging, Provenance tags

### Community 117 - "yt-dlp failure catalog"
Cohesion: 0.50
Nodes (4): Browser-cookie option, yt-dlp failure catalog, Permanent-source failure, Rate-limited failure

### Community 118 - "ModelManager"
Cohesion: 0.22
Nodes (6): Path, ModelManager, Check if model checkpoint exists locally., Manages downloading, caching, and verifying neural enhancement model weights., Return the local path to a cached model if it exists, else None., Check or download all AI model weights and show status for all 4 models.

### Community 119 - "Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation"
Cohesion: 0.50
Nodes (3): Answer, Q: Seven architecture questions about Phase 2, the orchestrator, Phase 1, spectral fixtures, module boundaries, and slskd isolation, Source Nodes

### Community 120 - "presets.py"
Cohesion: 0.50
Nodes (3): EnhancementPreset, Deterministic Enhancement Presets for OmniRip M10., Configuration preset for audio enhancement rendering.

### Community 204 - "._download_direct_http"
Cohesion: 0.27
Nodes (6): ModelSpec, Path, Calculate and verify SHA-256 checksum of a file., Download a model checkpoint to the local cache directory. Args: model_name:…, Specification of an audio enhancement model checkpoint., Download model checkpoint directly via streaming HTTP GET.

### Community 205 - "._resume_anim_timer"
Cohesion: 0.20
Nodes (4): Ensure the animation timer is active if paused during idle., Manually update band energy levels., Start active playback visualization., Seek the visualizer to an audio timestamp in seconds.

### Community 206 - "LogConsole"
Cohesion: 0.25
Nodes (4): RichLog, LogConsole, A ``RichLog`` that filters by minimum severity and trims to a line cap., Append a line if it passes the current level filter.

### Community 208 - "test_ui_visualizer.py"
Cohesion: 0.29
Nodes (6): ComposeResult, Unit tests for AudioVisualizer widget across all 5 visualizer modes., Verify that spectrum analyzer renders 10 frequency bands and calibrated ruler., test_audio_visualizer_10bands_and_full_width_ruler(), test_audio_visualizer_modes_and_render(), VisualizerTestApp

### Community 209 - "analysis/enhancement/__init__.py"
Cohesion: 0.29
Nodes (6): importlib_util, check_enhancement_available(), OmniRip M10 Enhancement and High-Frequency Reconstruction module., Check if the optional neural restoration dependencies are installed. Returns:…, Verify check_enhancement_available returns boolean and descriptive string., test_check_enhancement_available_returns_status()

### Community 213 - "_apply_dereverb_isolation"
Cohesion: 0.50
Nodes (4): _apply_dereverb_isolation(), Acoustic Anechoic Isolation Engine (De-Reverb). Decomposes an isolated vocal…, Verify acoustic anechoic engine extracts dry vocal formants and room reverb…, test_dereverb_isolation()

### Community 214 - "_apply_lr4_crossover"
Cohesion: 0.50
Nodes (4): _apply_lr4_crossover(), 4th-Order Linkwitz-Riley (LR4) Phase-Aligned Frequency Crossover Recombination.…, Verify 4th-Order Linkwitz-Riley crossover reconstructs input with flat…, test_lr4_crossover_reconstruction()

### Community 215 - "_apply_residual_inversion_loop"
Cohesion: 0.50
Nodes (4): _apply_residual_inversion_loop(), Residual Inversion 2.0 Cancellation Loop. Eliminates residual ghost vocals in…, Verify Residual Inversion 2.0 loop preserves energy and suppresses leakage., test_residual_inversion_loop()

### Community 217 - "update_progress"
Cohesion: 0.50
Nodes (3): update_progress(), on_progress(), _ui()

## Knowledge Gaps
- **163 isolated node(s):** `Answer`, `Source Nodes`, `harvester`, `Five phase workers`, `Batch adapter` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1030 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **99 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorkbenchWidget` connect `WorkbenchWidget` to `StemSeparator`, `.on_button_pressed`, `analyze_track_acoustics`, `app.py`, `HarvesterApp`, `._trigger_stem_separation`, `._startup`, `.on_select_changed`, `ModelManager`, `test_ui_workbench.py`, `DefectChecklist`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `HarvesterApp` connect `HarvesterApp` to `._run_guarded`, `.__init__`, `BatchConfirmScreen`, `WorkbenchWidget`, `test_enhancement_workbench.py`, `load_config`, `app.py`, `__main__.py`, `._startup`, `QuitConfirmScreen`, `test_ui_pilot.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `PipelineOrchestrator` connect `PipelineOrchestrator` to `.submit_batch`, `TrackJob`, `.wait_for_idle`, `phase2_hunt.py`, `FfmpegService`, `test_orchestrator_m5.py`, `test_orchestrator.py`, `.__init__`, `AppConfig`, `._startup`, `test_playlist.py`, `pathlib`, `test_orchestrator_m4.py`, `.submit_playlist`, `BatchReport`, `CircuitBreaker`, `test_orchestrator_m2.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `WorkbenchWidget` (e.g. with `HarvesterApp` and `AcousticAnalysisResult`) actually correct?**
  _`WorkbenchWidget` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HarvesterApp` (e.g. with `WorkbenchWidget` and `_app()`) actually correct?**
  _`HarvesterApp` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `PipelineOrchestrator` (e.g. with `BatchReport` and `AppConfig`) actually correct?**
  _`PipelineOrchestrator` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `ValidationError` (e.g. with `.submit_batch()` and `.submit_playlist()`) actually correct?**
  _`ValidationError` has 25 INFERRED edges - model-reasoned connections that need verification._