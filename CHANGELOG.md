# Changelog

All notable changes to `harvester` are documented here. Versioning follows
[Semantic Versioning](https://semver.org/). The milestone mapping is in
[`docs/10-roadmap.md`](docs/10-roadmap.md).

## [Unreleased]

### Added

- **Lane Expansion (docs/13, D21–D24):**
  - **Processing presets** (`[processing] preset`): `fetch_only` (acquire + tag, no separation), `standard` (4-source separation + song-driven lanes, default), `neural_full` (adds guitar/piano extras, MusicBrainz credits and tagging). The separator's engine fallback chain stays separate and is now reported loudly — a run that lands on the `eco` 2-layer fallback raises a warning instead of silently replacing the chosen preset.
  - **Lane provenance** (`analysis/enhancement/lane_plan.py`): every grid row carries an origin (`separator`, `dsp-split`, `extra-source`, `mix`, `credit-only`, `tag-only`), a confidence and a human note. Credited-but-unrenderable instruments (sax, violin) and tag-only labels are listed **without** an audio row — never faked. `LayerTrack.replan()` refreshes provenance when credits arrive, with no re-segmentation.
  - **MusicBrainz recording credits** (`CoverArtService.fetch_recording_credits`): documented instruments, vocal parts and a singer count, cached under `cache/credits/`, surfaced via the new `🏷 CREDITS` button on the `LAYERS` page. Live-verified on Imogen Heap — *Headlock* (double bass, lead vocals + 1 backing vocal → 2 singers).
  - **6-source extras** (`StemSeparator.separate_extra_lanes`): HTDemucs-6s (54.9 MB, `adefossez/HTDemucs-6s`) writes `{stem}_{mode}_raw_guitar.wav` / `_raw_piano.wav` after the 4-source run, so guitar and piano become first-class lanes via the existing disk discovery. Loaded alone and unloaded before the next stage; a missing model degrades to 4-source lanes.
  - Sidecar schema **v2** carries the lane plan (`lane_plan`, `singer_count`, `credit_instruments`, `tag_labels`) so the detached terminal labels rows exactly like the workbench.
  - **CLAP instrument/vocal tagging** (`analysis/enhancement/tags.py`, D25): `laion/clap-htsat-unfused` (614 MB) scores up to 24 evenly spaced 5 s windows against 12 instrument/vocal prompts. Scores are the mean softmax share across labels (relative, not calibrated probabilities — an even spread reports nothing), gated by `[processing] tag_threshold` (default 0.15). Results land in `tags.json` beside the stems and fold into the lane plan: a tag annotates the lane that renders it, or becomes a `tags only` row with no audio. Advisory only — never the verdict, the mix or the file metadata; every failure mode degrades to "no tags".
- **Optional `diarize` extra:** `pyannote.audio>=4.0` installs cleanly on this Python 3.14 venv (58 additive packages, no upgrades to existing pins) and powers the advisory speaker measurement (D27).
- **Hosted separation, opt-in per track** (`services/mvsep.py`, D26): the new `☁ HOSTED SEPARATE` button on the `LAYERS` page uploads an excerpt to MVSEP, polls the job (`waiting` → `processing` → `done`, top-level `status`, `sep_type` = the **`render_id`** of `GET /api/app/algorithms` — *not* its `id`), downloads every returned stem and files it as `{stem}_{mode}_hosted_raw_{lane_key}.wav`. Because the filename token *is* the lane key, a 4-, 21- or 53-stem model needs **no per-model table**: sum stems (`instrum-only`, `back-instrum`) are skipped, an unknown token still becomes a lane, and every hosted row carries `hosted (MVSEP)` provenance at high confidence. Deliberately **not** a preset: it is the only path that sends audio off the machine, so nothing hosted runs unless the button is pressed for a specific track, and a missing `MVSEP_API_KEY` is a status line, not an error. New `[processing] hosted_sep_type` / `hosted_max_seconds` (0 = whole track). The API key is never logged and is scrubbed from every message, including a hostile error body that echoes it back. Live-verified: a real job queued, separated and filed as lanes (docs/13 §7.1).
- **Advisory speaker measurement** (`services/diarization.py`, D27): the new `👥 SPEAKERS` button measures the vocals stem with pyannote (`speaker-diarization-community-1`, or a component-built fallback when the token cannot read the pipeline repo) and records `LanePlan.measured_speakers` **beside** `singer_count` — the plan reads `2 singers · 1 speakers measured`, and the workbench names credits as authoritative when the two disagree. It never overwrites credits, never adds or removes a lane, and never gates a stage: measured counts are noisy (*Headlock* → 1 measured vs 2 credited; a controlled two-singer splice → 3). Runs on CPU by design (Apple MPS fails on the pooling layer). New `[processing] diarize_max_seconds` (0 = whole track).
- **6-Page Full-Width Navigation Architecture:**
  - Decoupled workbench into six dedicated full-width pages (`F1`–`F6`): `[ ≡ TRACKS & LOGS ]`, `[ ◈ VISUALIZER ]`, `[ ⎈ DECK ]`, `[ 🎚 EQ ]`, `[ 𝄢 STEMS ]`, and `[ ▤ LAYERS ]`.
  - Dedicated multi-panel Audio Visualizer studio (`F2`) featuring a dual-channel calibrated VU meter, real-time 10-band octave spectrum analyzer, stereo phase correlation meter, and full-width braille waveform scrub ruler.
- **FL Studio Multi-Track Arrangement Interface:**
  - 24-character track header cards displaying stem badges, glowing Mute `[●]` LED indicators, Solo `[S]` buttons, and distinct stem color accents (Vocals Pink, Drums Red, Bass Blue, Instruments Amber).
  - 3-row high-density Braille waveforms per track displaying amplitude and transient contours.
  - Dual musical Bars/Beats and time ruler calibrated to track BPM.
- **10 Per-Second Surgical Stem DSP Operations:**
  - Expanded surgical toolkit with 5 new operations: `de_hum` (50/60 Hz notch + sub-rumble cut, -18 dB), `air_boost` (10–20 kHz high-shelf presence sheen, +4 dB), `de_click` (outlier derivative spike detector with 5-sample median interpolation), `noise_gate` (downward expander for noise floor < -38 dBFS), and `transient_tame` (soft tanh peak compression limiter > -3 dBFS).
  - Existing surgical operations: `mute`, `de_bleed`, `de_ess`, `de_mud`, `drum_punch`, and `reset`.
  - Distinct op badges (`M`, `B`, `S`, `U`, `P`, `H`, `A`, `C`, `G`, `T`) on timeline cells.
- **Stems-to-Layers Pipeline Cohesion:**
  - One-click `[ ▤ OPEN IN LAYERS ]` bridge on `STEMS` page directly populating the FL Studio arrangement timeline.
  - One-click `[ ⚡ BUILD STEMS ]` trigger on `LAYERS` toolbar initiating neural separation on demand.
  - Mouse-clickable tool palette buttons for all 10 operations, `[ 💾 COMMIT ]`, and `[ RELOAD ]` — these live in the detached layer terminal (the workbench `LAYERS` page is the control panel: build / open terminal / save / clear).

### Changed

- **Song-driven dynamic lanes:** the fixed four rows (vocals / bass / drums / other) are replaced by the lanes the song actually has. `analysis/enhancement/dynamic_layers.py` splits a family into disjoint child lanes — `drums → kick / snare / hats`, `bass → sub_bass / bass` — using the zero-phase complementary crossover with a narrow transition, and keeps a split only when every child clears the presence gate (active-second ratio ≥ 5 %, mean RMS ≥ -50 dBFS); otherwise the parent row survives whole. Children partition the parent exactly, so mix reconstruction keeps its -40 dBFS budget. Extra neural sources (e.g. `guitar` / `piano` from a 6-source model) become lanes automatically, so a track can render 4–8+ rows. The `LAYERS` status line reports the detected layout (`kick/snare/hats · bass → sub_bass/bass`).
- **Lane rows render only in the detached layer terminal:** the workbench `LAYERS` page no longer embeds the grid or the tool palette, so the timeline gets the full width of its own terminal window.
- **The detached terminal is now genuinely connected to OmniRip playback:** a new transport channel (`layer_sidecar.transport.json`, atomic writes) publishes the playhead / playing state / duration from the main app — which owns audio — at 5 Hz and carries the terminal's seek/play requests back. The terminal follows that playhead (the grid moves with the song), re-issues unanswered requests until the main app confirms them, and reloads lanes whenever the sidecar changes. Fixes the detached page sitting still while a track played in OmniRip.
- **AcoustID `meta` is posted as a repeated form field** (`meta=recordings&meta=releases&…`) instead of one `+`-joined string, which URL-encoded to a literal `+` and silently returned results with no recordings block (no title/artist resolution). Verified against the live API on a real track (title + artist + MusicBrainz recording id + 0.98 confidence).
- **Local secret file for API keys:** a gitignored `.env` (or `OMNIRIP_ENV_FILE`) is loaded into the process environment at startup, so GUI launches that do not inherit shell exports still find `ACOUSTID_API_KEY`; real environment variables still win and values are never logged or written back. `.env.example` documents the keys.

## [0.2.0] — 2026-09-18

Milestone 10 release: Neural Audio Enhancement Workbench.

### Added

- **M10 — Optional Neural & DSP Audio Enhancement Workbench:**
  - `restore` optional extra in `pyproject.toml` (`torch`, `torchaudio`, `huggingface_hub`).
  - `ModelManager` for automated Hugging Face checkpoint download and SHA-256 integrity verification into `~/.cache/omnirip/models/`.
  - DSP engine: complementary linear-phase crossover (`split_bands`), progressive mono bass filter (`apply_progressive_mono`: <100Hz mono, 100-250Hz fade, >250Hz stereo preserved), spectral slope matching (`match_spectral_slope`), and soft-knee peak limiter (`apply_limiter`).
  - Four enhancement providers: `ConservativeDSPProvider` (pure NumPy), `NVSRProvider` (Apple Silicon MPS / CPU), `FlashSRProvider` (air-band generator), and `HybridCoOpProvider`.
  - Five deterministic presets: `Conservative DSP`, `Fast Neural (Balanced)`, `Milder Highs (De-Sizzle)`, `Extended Air (Hybrid)`, and `Narrow Residual`.
  - Non-destructive `EnhancementExporter`: direct FFmpeg subprocess encoding to 320k MP3 derivatives with explicit Mutagen ID3 provenance tags (`TXXX:DERIVED_FROM_LOSSY`, `TXXX:SYNTHETIC_HIGH_BAND`, etc.).
  - `PreviewManager`: RMS-based 15s energetic excerpt detection, matched A/B WAV pair generation, and non-blocking system player dispatch.
  - `CurationWorkbenchModal` in Textual TUI accessible via `w` keybinding in `JobTable`.
  - Headless CLI flags: `harvester --enhance <file> [--preset <preset>] [--bitrate <bitrate>]`.

## [0.1.0] — 2026-09-18

Initial milestone-complete release (M0–M7).

### Added

- **M0 — Scaffold & environment:** package layout, validated TOML config with
  CLI > env > file precedence (secrets only via env vars), platformdirs layout,
  state machine with legal-transition table + D12 anti-loop guard, error taxonomy,
  async dependency probing, secret-masking logging, bootable Textual shell.
- **M1 — Mode A fallback-only:** killable subprocess registry, yt-dlp probe/download
  with progress parsing and failure catalog, ffmpeg transcode + probe, ID3v2.3 +
  provenance tagging, 5-stage async orchestrator, TUI wiring.
- **M2 — slskd hunt lane:** title cleaning (multi-query), candidate hard filters +
  scoring, circuit breaker, typed slskd client (OpenAPI verification, search/poll,
  transfer poll, stall detection), candidate retry + quarantine + fast-fail fallback.
- **M3 — Ground-truth ID:** fpcalc subprocess, AcoustID client (≤3 req/s token bucket,
  90-day SQLite cache), MusicBrainz/Cover Art Archive, FLAC Vorbis + MP3 APIC tagging,
  metadata fallback chain.
- **M4 — Spectral anti-fraud:** pure-numpy FFT brick-wall detector, 7-fixture verdict
  suite (encoder-faithful spectral bricks), Phase 4 gate with FRAUD→fallback reroute
  and `spectral.strict`.
- **M5 — Mode B batch audit:** recursive mutagen scanner with D1 skip matrix, free-space
  guard, atomic swap with byte-identical `.trash/` rollback, retention purge, incremental
  JSONL batch report, `identity_shift` warnings.
- **M6 — TUI hardening:** throttled UI bridge (coalescing ≤ 8 Hz, render-hash diffing,
  500-row cap), level-filtered log console, quit/purge/playlist/first-run modals,
  `Ctrl+P` mode toggle, live status worker, worker-crash banner, playlist expansion (D10).
- **M7 — QA & packaging:** CI matrix (Python 3.11/3.12 × ubuntu/macos, ruff + pytest with
  80% core-coverage gate), console script `harvester`, quick-start README, this changelog.

### Notes

- `ffmpeg`/`ffprobe`, `yt-dlp`, and (for fingerprinting) `fpcalc` are runtime binaries —
  they are **not** vendored. Install them before first run.
- The P2P lane requires a running [slskd](https://github.com/slskd/slskd) daemon and an
  API key; without it, harvester runs in yt-dlp-only fallback mode (FR-6).
- AcoustID lookups require a free API key (`ACOUSTID_API_KEY`); without it, the metadata
  fallback chain is used (AC-10).