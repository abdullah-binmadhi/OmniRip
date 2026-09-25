# 10 — Roadmap (M0 → M7)

Each milestone ends with a **runnable app** and a demo script. Suggested cadence: one
milestone per work session with a coding assistant, feeding it
`docs/11-enhanced-prompt.md` + the docs listed under "Specs" for that milestone.

| M | Name | Depends on | Key deliverable |
|---|------|-----------|-----------------|
| 0 | Scaffold & environment | — | ✅ Complete — project skeleton, config system, dependency detection, empty TUI boots |
| 1 | Mode A, fallback-only | M0 | ✅ Complete — URL → tagged MP3 via yt-dlp (no P2P, no fingerprint) |
| 2 | slskd hunt lane | M1 | ✅ Complete — P2P search, scoring, download, validation, failover to M1 path |
| 3 | Ground-truth ID | M2 | ✅ Complete — fpcalc + AcoustID + cover art + tagging conventions |
| 4 | Spectral anti-fraud | M3 | ✅ Complete — FFT verdicts, FRAUD→fallback reroute, fixture test suite |
| 5 | Mode B batch audit | M4 | ✅ Complete — scanner, skip matrix, atomic swap, `.trash/`, batch report |
| 6 | TUI hardening | M5 | ✅ Complete — bridge throttle/coalesce, modals, keybindings, first-run, status worker, playlist flow |
| 7 | QA & packaging | M6 | ✅ Complete — CI matrix, coverage gate, quickstart, CHANGELOG |
| 10 | Neural Audio Enhancement Workbench | M6 | ✅ Complete — model manager, DSP crossover/progressive mono, NVSR/FlashSR providers, presets, preview manager, workbench screen, CLI --enhance |
| 11 | Layer Studio (M1: visualize & inspect + M2: per-second editing + M3: hardening) | M10 | ✅ Complete — raw 4-stem persistence, per-second LR4 layer assembly + segment flags, LAYERS tab, playhead-synced grid + click-to-seek, cell-op edits (docs/12 §4), mix reconstruction residual budget + de-bleed fixture + run-length collapse (docs/12 §5) |
| 12 | Detached Layer Terminal (Option B) | M11 | ✅ Complete — JSON sidecar IPC (`harvester/ipc/layer_sidecar.py`), standalone `layer_terminal.py` reusing `LayerStudio` unchanged in its own Terminal.app window, explicit `🪟 NEW WINDOW` button (`wb-btn-layer-terminal`) launches it on demand (no auto-open), edits merge back into the main plan on next SAVE LAYERS / export; empty-stem sets now show a "run ⚡ BUILD STEMS" hint with live % progress (D17) |
| 13 | Song-driven lanes + two-way transport link | M12 | ✅ Complete — `dynamic_layers.py` expands the four base rows into the lanes the song actually has (kick/snare/hats, sub_bass/bass, any extra neural source) with a presence gate and an exact complementary partition; lane rows render only in the detached terminal (workbench LAYERS page = control panel) and both processes stay in sync through `layer_sidecar.transport.json` (5 Hz playhead publish + seek/play requests, atomic writes, re-issued until confirmed) (D18, D19) |
| 14 | AcoustID hardening | M12 | ✅ Complete — `meta` posted as repeated form fields (the `+`-joined form silently returned no recordings), `ACOUSTID_API_KEY` loadable from a gitignored `.env` while real env vars win (D20) |
| 15 | UI hardening & product polish | M14 | ✅ Complete — per-track state + operation lifecycle with generation tokens and dirty-edit guards (D28), per-track sidecars with source identity, stem cache manifests, atomic hosted-run swap and advisory-result persistence (D29), MVSEP upload confirmation + model picker, retry-naming failures, diagnostics modal, speaker heartbeat (D30), cache repair actions (REBUILD / RE-TAGS / CLEAR CACHE), pyannote session reuse, terminal heartbeat + ownership banner + lane provenance filter, save verification summary (D31) — full ledger and acceptance in docs/14 |
| 16 | Obsidian second-brain bridge | M15 | ✅ Complete — opt-in, manual two-way bridge to a local Obsidian vault (`OmniRip obsidian-sync`, docs/15): exports `Library/` (one note per album, built from `upgraded` batch rows), `Sessions/` (one note per Mode B report), `Studio/` (preset snapshots + inventory) and rewrites the `OmniRip.md` hub; imports `Wants/` notes through the real pipeline (`want → queued → done\|failed`, `--retry-failed`) and edits only their `status` key plus the `## OmniRip` log. stdlib frontmatter codec, atomic writes, traversal-safe paths, no orchestrator changes. Live-verified against a real vault: real Mode B report (1 skipped + 1 upgraded) → album + session notes, a real Wants rip settled to `done`, `Journal/` untouched, byte-identical resync (docs/15 §11) |
| 17 | Spectral anti-fraud v2 | M16 | ✅ Complete — the four `docs/04 §9` rules are now real (docs/16): hi-res void → FRAUD (with a second condition so flat masters are not mislabelled), fake-24-bit via a low-byte histogram over a native-rate s32 decode (saturation-tolerant, no `-ac`/`-ar` so the bits survive), SBR/tonal-artifact scan above the passband top, and stereo asymmetry from a mid/side pair decoded as stereo instead of a mono downmix. `FfmpegService` gains `probe_bit_depth` / `decode_s32` / `channels`; no new dependencies, deterministic fixtures, 17 new cases plus the `up96_void` fixture fix (it never had a void — its old INCONCLUSIVE came from FLOOR sitting at content level) |

---

## M0 — Scaffold & environment

**Specs:** 01 (read fully), 02, 11.
**Build:** `pyproject.toml` (deps per docs/02 §1), package tree (docs/02 §2), appdirs
layout, config loader + `config.example.toml`, logging setup with masking, binary
detection (ffmpeg/ffprobe/fpcalc/yt-dlp/slskd health), `models.py` + `statemachine.py`,
Textual shell rendering the docs/08 §1 layout with static placeholder data, FatalSetupScreen
for missing ffmpeg.
**Acceptance:** `python -m harvester` boots < 3 s (AC-1) showing real service pills;
statemachine unit tests exhaustive; config validation errors are actionable; no pipeline yet.

**Status:** ✅ Complete. Validated with 21 passing tests, clean Ruff checks, packaged CLI
version/help smoke checks, and asynchronous dependency probing. This machine lacks
`ffmpeg`/`ffprobe`, so the runtime correctly routes to its fatal setup screen until those
required binaries are installed.

## M1 — Mode A, fallback-only

**Specs:** 03 (Phase 1A, 5), 07, 02 §5 (orchestrator with analyze/fallback/identify-passthrough/polish queues).
**Build:** orchestrator skeleton (queues, workers, events, shutdown), yt-dlp probe +
download + progress parsing + failure catalog, Phase 5 tagging from `probe_meta` only
(fallback chain levels 2/4/5), MP3 transcode per D2 with provenance tags, Mode A input row
wired to the pipeline, JobTable live updates (unthrottled is fine here).
**Acceptance:** public-domain/CC test video URL → tagged 320k MP3 in output_dir with
provenance comment; PermanentSource hints correct for private/live/DRM URLs; cancel kills
subprocess ≤ 2 s (AC-8); quit leaves no temps (AC-6 partial).

**Status:** ✅ Implementation complete. Validated with 34 passing tests, clean Ruff checks,
bytecode compilation, fake-service end-to-end orchestration, live progress parsing, atomic
placement, and cancellation. A real public-domain URL smoke test is pending installation
of `ffmpeg` and `ffprobe` on the development machine.

## M2 — slskd hunt lane

**Specs:** 06, 03 (Phase 2), 09 (§1–§4).
**Build:** slskd client (health, OpenAPI verification per D6, search+poll, download
enqueue+transfer poll), titleclean multi-query, hard filters + scoring, candidate retry
(FR-5), stall detection, circuit breaker, degraded-mode fast-fail (FR-6), file handoff to
workspace, quarantine.
**Acceptance:** with a seeded test track: P2P FLAC acquired, validated, tagged-from-probe
(no fingerprint yet); slskd stopped → automatic fallback, pill red, hunt fast-fails (AC-3);
fake slskd integration tests green (docs/09 §7.2).

**Status:** ✅ Implementation complete. Validated with 55 passing tests, clean Ruff checks,
bytecode compilation, mocked slskd HTTP transport flows, fake-service P2P orchestration,
candidate retry, quarantine, and breaker-open fallback. A real slskd smoke run is pending
installation of the slskd daemon plus local `ffmpeg`/`ffprobe`.

## M3 — Ground-truth ID

**Specs:** 05, 03 (Phase 3).
**Build:** fpcalc subprocess, AcoustID client (token bucket ≤ 3/s, SQLite cache, score
thresholds), field mapping, Cover Art Archive client + cache, mutagen tagging module
(ID3v2.3 / FLAC picture, D7), fallback chain wiring, `meta_source` recording.
**Acceptance:** real lookup on a known track returns HIGH-confidence canonical tags + art
(AC-2 partial); key unset → chain degrades gracefully with header pill ▲ (AC-10); cache
hit makes zero HTTP calls (AC-9); tagging unit tests incl. v2.3 assertion.

**Status:** ✅ Implementation complete. Validated with 64 passing tests, clean Ruff checks,
mocked AcoustID/Cover Art HTTP flows, real FLAC/MP3 tagging with art, cache bypass, and
fallback-chain orchestration. A real AcoustID smoke run is pending installation of the
slskd daemon, local `ffmpeg`/`ffprobe`, and an AcoustID API key.

## M4 — Spectral anti-fraud

**Specs:** 04, 03 (Phase 4), 09 §7.1 (fixtures).
**Build:** ffmpeg decode pipe → numpy STFT analyzer, verdict rules §6, fixture generator
(7 fixtures), Phase 4 gate + FRAUD→fallback reroute with D12 guard, verdict numbers in
logs/report, `spectral.strict` config.
**Acceptance:** all fixture verdicts correct (AC-4); a real upscaled sample (manual smoke
4) rejected and re-acquired via fallback; phase ≤ 3 s; UI shows `⚠FRAUD→` badge;
NOT_APPLICABLE for fallback files (D3).

**Status:** ✅ Implementation complete. Validated with the 7-fixture verdict suite
(sharp raised-cosine spectral bricks per the docs/04 §10 encoder-faithfulness deviation),
Phase 4 gate tests, FRAUD→fallback reroute under the D12 guard, and NOT_APPLICABLE
handling for the fallback lane; verdict numbers surface in logs and the batch report.
A real upscaled-sample smoke (manual item 4) remains pending real-service execution.

## M5 — Mode B batch audit

**Specs:** 03 (Phase 1B, 5.3), 01 (FR-13/14, D1/D4/D5), 09 §6.
**Build:** scanner (walk, exclusions, container/bitrate matrix, filename parsing), free-space
guard, batch confirmation modal, atomic swap with rollback, `.trash/` layout + retention
purge + `p` keybind, JSONL report writer (incremental), `identity_shift` warnings.
**Acceptance:** mixed 5-file dir → correct skips/queues (AC-5); injected failure between
trash-move and replace rolls back byte-identical (unit); SIGTERM mid-batch → AC-6; report
lists every input exactly once (AC-5); original filename preserved (D4).

**Status:** ✅ Implementation complete. Validated with 110 passing tests (12 new: scanner
skip matrix with real MPEG fixtures, trash layout/collisions/rollback/purge, atomic swap
success + injected failure, report schema/incremental rows, Mode B orchestration AC-5
semantics, >25 confirmation guard, free-space guard, failure report rows, identity-shift
flagging, batch trash purge), clean Ruff checks and bytecode compilation. The batch
fallback lane uses `ytsearch1:<query>` inputs (D13); stale `*.harvester.tmp.*` artifacts
from a crashed swap are purged by the next scan (AC-6). Real-library smoke tests remain
pending `ffmpeg`/`ffprobe` installation on this machine.

## M6 — TUI hardening

**Specs:** 08 (all), 09 §5.
**Build:** UiBridge coalescing + 8 Hz flush, row render-hash diffing, log level cycling,
row cap/paging, all keybindings + modals (help, playlist confirm, quit confirm, purge),
first-run notice persistence, event-loop lag instrumentation, WorkerFailed banner path.
**Acceptance:** 1000-event storm pilot test: ≤ 8 flushes/s, loop lag < 50 ms (AC-7);
10-job simulated batch fully interactive; playlist cap + confirm flow (D10); all pilot
tests green (docs/09 §7.3).

**Status:** ✅ Implementation complete. Validated with 162 passing tests (27 new: bridge
coalescing/storm, log-console filter, config persistence, playlist orchestration, Phase
1/3/5 unit coverage, and UI pilots for bindings/modal/render). Clean Ruff and bytecode
checks; core coverage (analysis/pipeline/batch/util) at 85%. Textual's default `ctrl+p`
command-palette binding is disabled so the chord toggles Mode A/B per docs/08 §5.

## M7 — QA & packaging

**Specs:** 09 §7–§8, 01 §6 (all ACs).
**Build:** coverage gaps to ≥ 80% core; CI workflow (ruff + pytest matrix); manual smoke
checklist executed and recorded; packaging (console script `harvester`, version pinning
policy per docs/07 §1); user-facing README quickstart (install deps → configure keys →
run); CHANGELOG.
**Acceptance:** every AC-1…AC-10 demonstrated; smoke checklist items 1–6 pass on a clean
machine (or VM/container with binaries installed); fresh-clone install runs the TUI in
< 10 minutes following the README.

**Status:** ✅ Implementation complete. Console script `harvester` (verified `harvester
--version`), `CHANGELOG.md`, README quick-start, coverage config (`[tool.coverage]`), and
a GitHub Actions CI matrix (Python 3.11/3.12 × ubuntu/macos; ruff + pytest with an 80%
core-coverage gate). Core coverage measured at 85%. Items 1–6 of the manual smoke
checklist (docs/09 §7.4) remain pending real-service execution on a machine with slskd,
ffmpeg/ffprobe, and an AcoustID key installed — they are recorded as release gates here,
not automatable without those binaries.

## M10 — Neural Audio Enhancement Workbench

**Specs:** `m10_enhancement_workbench_plan.md`, band-limited residual isolation, sub-$f_c$ invariance.
**Build:**
- Optional dependencies extras in `pyproject.toml`: `restore = ["torch", "torchaudio", "demucs", "transformers", "beartype", "rotary_embedding_torch", …]`, `flashsr = ["librosa", "matplotlib", "psutil", "pyyaml", "tqdm"]`.
- `ModelManager` with automated Hugging Face checkpoint download and SHA-256 validation.
- `EnhancementProvider` protocol and 4 providers: `ConservativeDSPProvider` (pure NumPy), `NVSRProvider` (harmonic high-band engine, Torch on MPS/CPU with a NumPy fallback), `FlashSRProvider` (the real FlashSR pipeline — student LDM + VAE + SR vocoder over 5.12 s windows at 48 kHz — with the harmonic air-band generator as its offline fallback), `HybridCoOpProvider`.
- The `nvsr` registry slot was removed: its checkpoint (`haoheliu/wellsolve` `basic.pth`) is the AudioSR latent-diffusion bundle, not a one-shot SR model, and upstream `audiosr` pins `numpy<=1.23.5` / `transformers==4.30.2`, so it cannot coexist with this project (see docs/01 D34).
- DSP engine (`split_bands` zero-phase crossover, `apply_progressive_mono` sub-100Hz mono blend, `match_spectral_slope`, `apply_limiter` soft-knee ceiling at -0.1 dBFS).
- 5 deterministic presets (`conservative`, `fast_balanced`, `de_sizzle`, `extended_air`, `narrow_stereo`).
- `EnhancementExporter` rendering 320k MP3 derivatives with Mutagen ID3 provenance tags (`TXXX:DERIVED_FROM_LOSSY=true`, `TXXX:SYNTHETIC_HIGH_BAND=true`, etc.) while leaving original master untouched.
- `PreviewManager` generating 15s energetic A/B preview WAV pairs and launching non-blocking OS player (`open` / `xdg-open`).
- `CurationWorkbenchModal` interactive Textual screen accessible via `w` keybinding in `HarvesterApp`.
- Headless CLI flags: `harvester --enhance FILE [--preset PRESET] [--bitrate BITRATE]`.

**Status:** ✅ Implementation complete. Validated with 28 passing unit and integration tests across DSP, providers, exporter, presets, previews, and UI pilot (`tests/test_model_manager.py`, `tests/test_enhancement_dsp.py`, `tests/test_enhancement_providers.py`, `tests/test_enhancement_exporter.py`, `tests/test_enhancement_workbench.py`, `tests/test_main.py`, `tests/test_ui_pilot.py`). Zero regressions on full project test suite (205 passed).
## M18 — Guided Repair (Stems/Layers removal)

Status: **implemented**. Replaces the Stems and Layers pages with one guided
**REPAIR** flow (docs/01 D35): zero-question Quick Fix from acoustic detection,
a sequential MCQ wizard for refinement, per-symptom `min:sec` sections with hot-spot
suggestions, Local/Hosted-MVSEP engine choice, three deliverables (enhanced repaired
master, acapella, instrumental), Track Info modal (`i`) for credits/tags/speakers/models,
diagnostics on `d`. Deletes the detached layer terminal, sidecar channel, lane plans and
per-second editing wholesale; D16–D19, D21–D27, D31 and D33 are superseded.

## M19 — Lossless Enhanced Exports (D37)

Status: **implemented**. Adds 24-bit 48 kHz WAV and FLAC masters beside the 320 kbps MP3 default.
Extracted the shared audio render and composed EQ pipeline into a unified helper. Exports embed
full provenance tags (`DERIVED_FROM_LOSSY=true`, `LOSSLESS_SOURCE=false`, `SYNTHETIC_HIGH_BAND=true`,
`ENHANCEMENT_PRESET`, and genre tags) via FLAC Vorbis comments and WAV ID3 TXXX frames.
Deck export menu routes WAV and FLAC masters, updating the export button dynamically.

## M20 — Genre Intent Engine (D38)

Status: **implemented**. Genre-aware mastering with 20 sparse, test-capped profiles (Hip-Hop/Trap,
House, Techno, Jazz, Pop, etc.) + Neutral. Features 150+ aliases for automatic ID3 tag and probe
metadata resolution, non-blocking background MusicBrainz credit/genre integration, hybrid weighted
averaging (blend_curves cancels conflicting intentions without additive boost), intensity scaling
(Subtle 0.6×, Balanced 1.0×, Bold 1.4×), and multi-select Genre Mix modal (up to 6 profiles).
Composed curves feed playback, audition cache, MP3/WAV/FLAC exports, and the Repair master while
keeping isolated stems uncolored. Validated with 515 passing unit and integration tests (1 skipped).

## M21 — Batch Library Auto-Restoration & Curation

Status: **implemented**. Provides serial batch restoration of lossy/substandard audio files
within a directory tree. Integrates acoustic detection, genre intent resolution, and enhancement
rendering with atomic file replacement and automatic `.trash/<date>/` rollback backup. To protect
MacBook Air M2 (16GB RAM) hardware, processing runs strictly serially and invokes `purge_neural_vram()`
between tracks, preventing swap spikes and out-of-memory errors. Generates GitHub-flavored Markdown
summary tables detailing per-track format, bitrate, spectral cutoff, applied genre profile, and export status.

## M22 — Real-Time Spectrogram Waterfall & Phase Scope

Status: **implemented**. Extends `AudioVisualizer` with 7 reactive visualizer modes, adding
`"spectrogram"` (Mode 6: STFT Waterfall with cutoff overlay line) and `"phase_scope"` (Mode 7: Stereo
Lissajous Phase Scope with -1.0 to +1.0 correlation meter, width percentage, and mono-cancellation
warnings). Renders responsive ASCII/Unicode visualizations in the Textual TUI during live playback
and A/B auditioning.

## M23 — Obsidian Second-Brain Automated Hunting & Enriched Notes

Status: **implemented**. Enriches Obsidian album and want notes with genre intent and enhancement
provenance. Adds `genre`, `genre_mix`, `genre_intensity`, and `enhancement_preset` to `track_row_fields`,
aggregates unique album `genres` in YAML frontmatter, adds a `Genre` column to Markdown track tables,
and enriches settled want notes with acoustic verdict and cutoff metadata (`spectral PASS @ 21500Hz`).

## M24 — Neural Acceleration & 16GB Memory Hardening

Status: **implemented**. Creates `src/harvester/util/memory.py` to harden the neural inference pipeline
against unified memory constraints on 16GB Apple Silicon machines (MacBook Air M2). Provides
`purge_neural_vram()` (MPS/CUDA cache flushing and garbage collection), `get_memory_headroom_mb()`
(system memory headroom queries), `is_low_memory_headroom()` (< 2048 MB memory pressure warning),
`get_safe_neural_device()` & `get_safe_neural_dtype()` (FP16 half-precision selection), and
`get_safe_chunk_duration()` (dynamic chunk shrinking from 8.0s to 4.0s under pressure). Integrated
into all `workbench.py` render/export `finally` blocks and batch restoration runners.



## M11 — Layer Studio (M1: visualize & inspect + M2: per-second editing)  
_Superseded by M18 (guided Repair) — kept for history._

**Specs:** docs/12-layers-studio.md (M1, M2), D14.
**Build:**
- `stem_separator.py`: `save_individual_sources` + per-source raw stems
  (`raw_bass/drums/other_path`) persisted through `_separate_ensemble` / `_separate_bs_roformer`
  / `_separate_neural`, HDEMUCS twins named `{...}_hdemucs.wav`.
- `layers.py`: `LayerTrack`/`LayerSource`/`LayerSegment`/`LayerIssue`, per-source LR4
  assembly (HDEMUCS low anchor vs BS-RoFormer), fixed 1 s envelopes (RMS dBFS + peak),
  5 issue fingerprints (vocal_bleed / whisper / sizzle / mud / sub_rumble), Eco 2-layer
  fallback, `build_layer_track`.
- `layer_studio.py`: `LayerStudio` widget — ruler + per-layer grid, block-glyph levels,
  issue color flags, playhead-synced auto-scroll (0.25 s timer vs `#audio-player`),
  click-to-seek (`SeekRequested` / `SelectionChanged`), scroll keybindings, and M2:
  `edit_plan` reactive, `EditRequested` message, `m/b/s/u/p/r` cell-op keybindings,
  `✎` edited-cell markers.
- `layer_editor.py`: `EditPlan` (toggle/reset/clear), cell ops (mute / de-bleed -24 dB
  vocal core / de-ess -14 dB sibilance / de-mud -10 dB mud / drum-punch), zero-phase FFT
  band notches, `render_edited_layer` with 20 ms equal-power crossfade splices,
  `commit_edit_plan` (32-bit PCM in place) with -1 dBFS soft limiter,
  `rebuild_track_after_commit`, and M3: `reconstruct_mix` / `mix_residual_db` /
  `verify_mix_residual` (per-second inversion residual, -40 dBFS budget).
- `layers.py` M3: `CellRun` + `run_length_collapse` (level bucket × issue × op, split_at
  boundaries), `segment_band_level` in-band meter, `LONG_TRACK_SECONDS = 600`,
  `ANALYSIS_MS_PER_SECOND_BUDGET = 100 ms/s`; `layer_studio.py` renders ≥ 600 s tracks as
  run-length cells; `workbench.py` commit worker surfaces the post-commit mix residual.
- `workbench.py`: LAYERS page, background `layer-studio-build` worker, seek/selection
  message handlers, `save_individual_sources=True` on separation, `layer_stem_dir` set in
  `load_job`, LAYERS READY status summary, and M2: layer edit-plan state,
  `EditRequested` handler, SAVE LAYERS / CLEAR EDITS buttons, async `layer-studio-commit`
  worker reusing cached layer files then rebuilding the grid.

**Status:** ✅ M1 + M2 + M3 implementation complete. Full suite 292 passed / 1 skipped,
clean Ruff. New coverage (`tests/test_layers.py`): envelope units, 4-stem LR4 assembly +
disk cache, Eco fallback, full track build with injected bass vocal-band burst →
`vocal_bleed` on the exact second, headless `LayerStudio` mount/render/playhead sync,
`EditRequested` probe + edit-marker render; plus `save_individual_sources` persistence in
`tests/test_stem_separator.py` and `tests/test_layer_editor.py` (EditPlan semantics,
band-cut energy assertions, neighbour byte-identity + crossfade continuity, commit→rebuild
mute flow, PCM_32/-1 dBFS ceiling). M3 hardening (`tests/test_layer_hardening.py`): mix
reconstruction ≤ -40 dBFS inversion, edited-seconds-only budget violations, de-bleed
fixture dropping in-band leak ≥ 20 dB, 600 s analysis within the per-second budget with
single-run-length collapse, and the widget's long-track run-length render. Spec in
docs/12 §5.

---

## M11.5 — Lane expansion: presets, provenance, credits, extras & tags  
_Superseded by M18 (guided Repair) — kept for history._

**Goal:** stop guessing. Every lane row says what it is, every stage that runs is a
user-visible choice, and the instrument inventory comes from documented data plus an
advisory tagger — never from an LLM.

**Status:** ✅ implemented (docs/13, decisions D21–D27). Shipped:

1. **Processing presets** (`[processing] preset`, `processing.py`): `fetch_only` /
   `standard` (default) / `neural_full`. The preset decides *which* stages run; the
   separator's engine chain still decides *how* they run, and any fallback to the eco
   2-layer DSP is reported loudly (`engine_note` + warning toast) instead of silently
   replacing the user's choice.
2. **Lane provenance** (`analysis/enhancement/lane_plan.py`): origin (`separator`,
   `dsp-split`, `extra-source`, `mix`, `credit-only`, `tag-only`) + confidence + note per
   row. `credit-only` / `tag-only` rows are listed but carry **no** audio row — nothing is
   faked. Sidecar schema **v2** carries the plan so the detached terminal labels rows
   identically.
3. **MusicBrainz recording credits** (`services/musicbrainz.py`): instruments, vocal parts,
   producers and a singer count, cached under `cache/credits/`, surfaced by the `🏷 CREDITS`
   button; credited-but-unrenderable instruments (sax, violin) become listed rows.
4. **6-source extras** (`stem_separator.separate_extra_lanes`, HTDemucs-6s): guitar/piano
   raw stems under the same mode suffix, so the lane engine picks them up generically;
   presence-gated, so bleed does not invent rows.
5. **CLAP tagging** (`analysis/enhancement/tags.py`, D25): zero-shot instrument/vocal tags
   over evenly spaced windows, stored as `tags.json` beside the stems and folded into the
   lane plan as annotations or `tags only` rows. Advisory only — it never touches the
   spectral verdict or file metadata.
6. **Hosted separation** (`services/mvsep.py`, D26): the `☁ HOSTED SEPARATE` button uploads
   an excerpt to MVSEP, polls the job and files every returned stem as a lane. Opt-in per
   track and deliberately **not** a preset — it is the only path that sends audio off the
   machine. The filename token is the lane key, so a 4-, 21- or 53-stem model needs no
   per-model table.
7. **Measured speakers** (`services/diarization.py`, D27): `👥 SPEAKERS` measures the vocals
   stem with pyannote and reports `N speakers measured` **beside** the MusicBrainz credit
   count. Advisory only — measured counts are noisy, so they never overwrite credits.

**Verification:** full suite green + ruff clean; real-weight end-to-end runs on real songs
(8 lanes including `GUITAR [6-source model, low]`, live AcoustID → MusicBrainz credit chain
with `2 singers`, a real hosted MVSEP job filed as `hosted (MVSEP)` lanes, a real pyannote
measurement reported beside the credit count, sidecar v2 round trip). Measurements, gates and
the exact commands live in docs/13 §7.1.

**Out of scope (documented, not built):** audio-LLM/BYOK inference in the pipeline (rejected:
an LLM must never touch the spectral verdict or the metadata authority) and any *batch* hosted
run (a hosted job is per-track and opt-in by design, D26). See docs/13 §8.

---

## Working agreement for coding-assistant sessions

1. One milestone per session; start by reading this roadmap + the milestone's spec docs.
2. Deliver complete files (no placeholders — brief directive #3), plus the module's unit
   tests in the same pass.
3. End each session by updating: roadmap checkbox state (this file), any decision-log
   changes in docs/01 §5, and the timeout registry if new timeouts appeared.
4. Never weaken a spec silently — if a requirement is infeasible, record the conflict in
   docs/01 §5 and ask before proceeding.
