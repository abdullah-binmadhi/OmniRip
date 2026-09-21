# 01 — Requirements

## 1. Vision

A single-operator desktop application (TUI) that upgrades a music library toward the best
verifiably-authentic audio obtainable, automatically:

1. **P2P-first**: prefer true lossless FLAC from Soulseek (via a local `slskd` daemon).
2. **Stream-fallback**: when P2P fails (no match, no peers, timeout, fraud), fall back to the
   best audio stream via `yt-dlp` (YouTube Opus in practice).
3. **Trust but verify**: identify every acquired file by audio fingerprint (AcoustID /
   MusicBrainz) and reject fake-lossless files by spectral analysis before they enter the
   library.
4. **Never block**: the UI stays interactive throughout; all I/O and CPU-heavy work runs in
   async workers/threads.

## 2. Operating modes

### Mode A — Single URL

| Step | Behavior |
|------|----------|
| Input | One URL (YouTube watch/playlist, or any yt-dlp-supported extractor) |
| Phase 1 | Probe metadata without downloading (`yt-dlp -J --skip-download`): title, artist/channel, album, duration, thumbnail |
| Playlists | Expand to individual track jobs, capped (default 50, config `batch.playlist_cap`); prompt for confirmation at the cap |
| Output | New file written to the configured output directory |

### Mode B — Local Batch Audit

| Step | Behavior |
|------|----------|
| Input | Local directory path (picked via in-TUI directory browser or typed) |
| Scan | Recursive walk of audio files; probe each with `mutagen` for codec, bitrate, duration, existing tags |
| Skip | Lossless containers (FLAC/ALAC/WAV/AIFF) always skipped; lossy files with bitrate ≥ `batch.skip_bitrate_kbps` skipped |
| Queue | Everything below the threshold becomes an upgrade job carrying its existing tags (or filename-derived query) |
| Replace | On success, atomically swap the new file into the **original filename/location**; the old file moves to `.trash/` (see D4/D5) |
| Report | A batch report (JSONL) records per-file outcome: skipped / upgraded / failed, old bitrate, source used, spectral verdict |

Excluded from scan: `.trash/`, hidden directories, non-audio files.

## 3. Functional requirements

IDs are normative and referenced by the roadmap and test plan.

### Acquisition

- **FR-1** Given a Mode A URL, the system SHALL extract metadata without downloading audio.
- **FR-2** The system SHALL search slskd for lossless candidates using cleaned queries
  (multi-query strategy per `docs/03-pipeline.md` Phase 2) and rank results with the scoring
  function in `docs/06-slskd-integration.md`.
- **FR-3** If no acceptable P2P candidate appears within `slskd.search_timeout_s` (default
  25 s total query budget), the system SHALL fall back to yt-dlp without user interaction.
- **FR-4** The yt-dlp fallback SHALL download the best available audio-only stream
  (preferring Opus), raw (no in-download transcode), with machine-readable progress.
- **FR-5** If a completed P2P download fails validation (unparseable, duration mismatch
  > 5% vs. reported, zero-byte), the system SHALL try the next-ranked candidate once, then
  fall back to yt-dlp.
- **FR-6** If slskd is unreachable at any point, hunting SHALL fast-fail to the yt-dlp path
  and the UI SHALL show a degraded-mode indicator (no crash, no stalls).

### Verification

- **FR-7** Every acquired file SHALL be fingerprinted with `fpcalc` and looked up against
  AcoustID **before any transcoding occurs** (Decision D9).
- **FR-8** When AcoustID returns a confident match, canonical metadata (title, artists,
  release, date/year, ISRCs, MusicBrainz IDs) SHALL be adopted; otherwise the metadata
  fallback chain applies (`docs/05-fingerprinting-metadata.md` §7).
- **FR-9** Every P2P-sourced file claiming lossless quality SHALL pass the spectral
  anti-fraud check (`docs/04-spectral-antifraud.md`). On a FRAUD verdict the file SHALL be
  deleted and the yt-dlp fallback triggered immediately.
- **FR-10** Files of known lossy provenance (yt-dlp fallback, or Mode B originals) SHALL be
  exempt from FR-9 by provenance, not by spectrum.

### Finishing

- **FR-11** The system SHALL embed canonical tags and cover art (Cover Art Archive front
  image when available) via `mutagen`.
- **FR-12** yt-dlp Opus downloads SHALL be transcoded to MP3 per `ffmpeg.transcode` config
  (default `320k CBR` — see Decision D2) and SHALL carry provenance tags
  (`TXXX:SOURCE_ORIGIN` + human-readable comment) stating the lossy origin.
- **FR-13** Mode B replacements SHALL be atomic: temp file in target dir → fsync → move
  original to `.trash/<date>/<timestamp>-<name>` → `os.replace` temp over original; any
  failure after trashing SHALL roll back from `.trash/`.
- **FR-14** The batch report SHALL be written incrementally (append per completed job) so a
  crash loses at most one record.

### UI

- **FR-15** The TUI SHALL show: header with live service status (slskd, ffmpeg, fpcalc,
  AcoustID key), input area (URL text input / Mode B directory picker), a live job
  DataTable (Track, Original Status, Target Source, Phase, Progress), and a scrolling log
  console.
- **FR-16** The UI SHALL remain responsive during all operations (no synchronous network,
  subprocess, or CPU-heavy calls on the event loop).
- **FR-17** Users SHALL be able to cancel an individual job or all jobs, and quit cleanly
  (in-flight subprocesses killed, temp files cleaned, `.trash/` intact).

## 4. Non-functional requirements

- **NFR-1 Strict async**: all subprocesses via `asyncio.create_subprocess_exec` or
  `asyncio.to_thread`; CPU-bound FFT in a thread (or process) pool. The event loop is never
  blocked > 50 ms.
- **NFR-2 Bounded concurrency**: per-stage worker pools (defaults in
  `docs/02-architecture.md` §5); simultaneous downloads capped (default 2 P2P + 2 yt-dlp).
- **NFR-3 Resilience**: every network operation has an explicit timeout (registry in
  `docs/09-resilience-testing.md` §4); transient failures retried with exponential backoff
  and jitter; slskd guarded by a circuit breaker.
- **NFR-4 Graceful degradation**: missing slskd → yt-dlp-only mode; missing fpcalc/AcoustID
  key → filename/yt-dlp metadata mode; missing ffmpeg → hard stop at launch with
  instructions (nothing can finish without it).
- **NFR-5 Disk safety**: free-space check before batch (estimate ≈ jobs × 40 MB × 1.5);
  corrupt/incomplete downloads quarantined, never swapped into the library.
- **NFR-6 Secrets hygiene**: API keys only from environment variables; never hardcoded;
  masked in logs and never written to the batch report.
- **NFR-7 Portability**: macOS and Linux first-class; Windows supported where
  slskd/ffmpeg/fpcalc binaries exist (Docker Desktop or native slskd).
- **NFR-8 Observability**: rotating file log (DEBUG) + UI console (INFO); every job emits
  structured events; every phase transition logged with job id.

## 5. Resolved ambiguities & decisions

The original brief left gaps; these decisions are **normative** (change them only by editing
this table and propagating the change).

| ID | Issue | Decision |
|----|-------|----------|
| D1 | Brief says "skip ≥ 320 kbps, queue ≤ 192 kbps" — 193–319 kbps undefined | Single threshold `batch.skip_bitrate_kbps`, **default 256**. Lossless always skipped. Gray zone eliminated. |
| D2 | Transcoding ~130–160 kbps Opus to 320 kbps CBR MP3 is an **upcast** — no quality gain, and the result mimics a native "320 MP3" to other tools | Default remains MP3 320 CBR (per brief) **but** provenance tags are mandatory (FR-12), with config alternatives `mp3-v0` and `keep-opus` (`.opus` container). Stated honestly in UI help text. |
| D3 | Spectral check scope | Applied **only** to P2P files claiming lossless. Known-lossy files exempt by provenance (FR-10). Prevents the D2 upcast from tripping our own fraud check. |
| D4 | Mode B output naming | **Keep original filename/path** (per brief). Canonical renaming available behind config flag `batch.rename_to_canonical` (default off). |
| D5 | `.trash/` lifecycle | Retention `batch.trash_retention_days` default **7**; purge command in UI + optional auto-purge on startup. `.trash/` is the rollback source of truth until purged. |
| D6 | slskd REST routes vary across releases | The client verifies routes at startup against the daemon's OpenAPI spec (`/swagger/v0/swagger.json`), logs the detected version, and fails with a clear message on incompatible schemas. |
| D7 | ID3 version | **ID3v2.3** for MP3 (widest device/car-stereo compatibility); FLAC uses Vorbis comments + `METADATA_BLOCK_PICTURE`. |
| D8 | Where FFT runs | `asyncio.to_thread` first (numpy releases the GIL for most ops); escalate to `ProcessPoolExecutor` if UI frame drops are observed. |
| D9 | Fingerprint vs. transcode order | Fingerprint the **downloaded source** (Opus/FLAC) *before* transcoding — Chromaprint matching degrades on transcoded files. Phase order 3 → 4 → 5 is mandatory. |
| D10 | Playlist handling | Expand with cap (default 50) + confirmation prompt; single-video URLs with playlist query params are treated as single tracks (`--no-playlist` semantics). |
| D11 | Duplicate acquisitions | v1: skip when a file with the same canonical fingerprint (AcoustID recording MBID) already exists in the output directory. Full dedup database is v2. |
| D12 | Anti-loop invariant | A job may use the fallback path at most once (`fallback_attempted` flag). After fallback, the job never re-enters HUNTING or SPECTRAL_CHECK. |
| D13 | Mode B fallback + crash temps (M5) | Batch jobs carry no input URL; the fallback lane uses `ytsearch1:<query>` so yt-dlp downloads the top search hit (probe-verified by Phase 3). Mode B swap temps are named `*.harvester.tmp.*` (hidden), skipped by scans, and purged at the next scan start — a SIGTERM between trash-move and replace leaves the original recoverable in `.trash/` and at most one invisible temp (AC-6). |
| D14 | Layer Studio time grid + raw-source persistence | Layer Studio (docs/12) uses a **fixed 1-second** per-column grid (no zoom in M1). Neural/ensemble runs persist per-source stems `{stem}_{mode}_raw_{vocals,bass,drums,other}.wav` (+ `_hdemucs` twins); per-layer grid files are HDEMUCS LR4-blended against BS-RoFormer (`crossover_hz` low anchor), matching the VOC/INST audition. Eco mode is a 2-layer fallback (vocals + mix) since mid/side cannot split drums/bass/other. |
| D15 | M3 hardening depths & budgets (Layer Studio) | De-bleed attacks the 300–3500 Hz vocal core at **-24 dB** (not -18) so a committed cell drops injected in-band leak by ≥ 20 dB with margin through the notch's raised-cosine edges. Mix-reconstruction residual budget is **-40 dBFS** per segment (`verify_mix_residual`): only genuinely edited seconds may exceed it. Analysis budget is **100 ms/s** (600 s track ≤ 60 s), with run-length cell collapse above `LONG_TRACK_SECONDS = 600`. The `vocal_bleed` flag may persist after a de-bleed commit because the detector compares in-band magnitude-mean with whole-second RMS (conservative for sub-dominant bass); the M3 acceptance is the ≥ 20 dB in-band drop, not flag-clearing. |
| D16 | Detached Layer Terminal (Option B) | Opening `▤ LAYERS` serializes the `LayerTrack` + `EditPlan` to `layer_sidecar.json` and launches `layer_terminal.py` in a new Terminal.app window (fire-and-forget `osascript`; detached-process fallback elsewhere). The terminal **reuses `LayerStudio` unchanged** and always stays write-following to one JSON file that the main app merges via `_reload_sidecar_edits` on SAVE LAYERS. Playback stays in the main process. The sidecar schema must reflect the real model — `LayerSource.rms/peak` are per-segment **arrays**, `LayerSegment.levels` + `LayerIssue` objects — not scalar aggregates. 11 ops are exposed (the real `layer_editor.OPS`); keyboard cell keys live at app level (`LayerStudio.can_focus` is False) but drive `studio._request_edit()` so selection semantics match the workbench exactly. No new timeouts; subprocess spawns are fire-and-forget and never raise. |
| D17 | Explicit terminal launch + empty-grid diagnosis | The detached terminal is **never auto-opened**: it opens only via the `🪟 OPEN LAYER TERMINAL` button (`wb-btn-layer-terminal`), which resets `_layer_terminal_launched` so every click (re)opens a window; a not-yet-built track defers the launch via `_layer_terminal_pending` until `_async_build_layers` completes. Real-stem diagnosis on a 251 s / 252-segment track: `build_layer_sources` yields base lanes **only** when BS-RoFormer raw sources exist for every part (many two-stem cache dirs ship `raw_vocals` + `raw_inst` only → 1 row; empty stem dirs → 0 rows), so `LayerStudio.render` shows a **"No layer sources found — run ⚡ BUILD STEMS"** hint instead of a ruler-only blank grid, and the workbench reports live **% build progress** into `#wb-layer-status` ("Separating stems…" while separation runs) so the long per-second defect scan never looks stalled. |
| D18 | Song-driven dynamic lanes | The static four-stem row set is only the *source* set: `dynamic_layers.expand_dynamic_lanes` splits a family into disjoint child lanes (`drums → kick/snare/hats`, `bass → sub_bass/bass`) with the zero-phase complementary `dsp.split_bands` crossover (narrow transition, `lane_transition_hz = min(500, max(50, cutoff×0.6))`) and keeps a split **only** when every child clears the presence gate (active-second ratio ≥ 5 % above -45 dBFS **and** mean RMS ≥ -50 dBFS); otherwise the parent lane survives whole (`{family} (whole)` in the status summary). Children partition their parent exactly, so `reconstruct_mix` keeps its -40 dBFS budget (verified in `tests/test_layer_hardening.py`). Extra lanes are disk-discovered (`_collect_extra_lanes` globs `{suffix}_raw_{name}.wav` beyond the known four, rendered after the known order), so the engine is not a fixed lane list — but the built-in separator still writes only the four neural sources (BS-RoFormer's tensor is fixed at bass/drums/other/vocals), so guitar/piano rows appear only when such raw files exist. Child lane files are cached (`{suffix}_layer_{token}.wav`, the upper bass half using the `bass_upper` file token so the parent file is never clobbered); committed edits survive rebuilds. |
| D19 | Detached-only lane rendering + live transport link | Lane rows render **only** in the detached layer terminal: the workbench `LAYERS` page keeps `⚡ BUILD STEMS` / `🪟 OPEN LAYER TERMINAL` / `💾 SAVE LAYERS` / `CLEAR` plus the status line and embeds no `LayerStudio` and no tool palette (cell ops live in the terminal). The two processes are linked live through `layer_sidecar.transport.json` (atomic `os.replace` writes): the main app — which owns audio output — publishes `playhead_s` / `playing` / `duration_s` at 5 Hz and consumes the terminal's `seek_request` / `play_request` (`consume_requests`), while the terminal polls the same file at 5 Hz, feeds `LayerStudio.playhead_provider` so the grid moves with the song, re-issues unanswered requests until the published state confirms them (a poll race can never swallow a request), and reloads lanes when the sidecar's mtime changes. |
| D20 | Local secret file for API keys | API keys still come from environment variables only (NFR-6); `load_env_file` additionally reads a gitignored `KEY=VALUE` `.env` (explicit path → `OMNIRIP_ENV_FILE` → next to the config file → CWD → data dir) into the process environment at startup so GUI launches that do not inherit shell exports still find `ACOUSTID_API_KEY`. Real environment variables always win, values are never logged or written back. AcoustID's `meta` field is posted as a **repeatable** form parameter (`recordings`, `releases`, `releasegroups`, `isrcs`): a single `+`-joined string is URL-encoded to a literal `+` and the API then returns bare results with no recordings, silently resolving no metadata. |
| D21 | Processing presets vs engine fallback | Which stages run is an explicit, user-facing **preset** (`[processing] preset`: `fetch_only` \| `standard` \| `neural_full`, `harvester/processing.py`) and is orthogonal to sourcing (`slskd.acquisition_mode`). The separator's engine chain (neural → hdemucs → eco) only decides **how** a stage runs and is never a preset: `eco` remains the spec'd 2-layer mid/side fallback (D14), and any run that lands there is reported loudly (`engine_note`, warning toast) instead of silently swapping the user's choice. `fetch_only` runs no separation, no lanes and no restoration; `standard` adds the 4-source separation + song lanes; `neural_full` adds the 6-source extras, credits and tagging. Pressing `⚡ BUILD STEMS` under `fetch_only` is an explicit per-track opt-in and switches the session to `standard`. |
| D22 | Lane provenance (`LanePlan`) | Every grid row carries an origin — `separator`, `dsp-split`, `extra-source`, `mix`, `credit-only`, `tag-only` — plus a confidence and a human note (`harvester/analysis/enhancement/lane_plan.py`). `build_layer_track` builds the plan from the detector's `LaneReport`; `LayerTrack.replan()` recomputes it (credits arriving later) **without re-segmenting**. `credit-only` / `tag-only` entries are listed but `rendered is False`: they never get a fabricated audio row. The plan rides in the sidecar (`lane_plan`, `singer_count`, `credit_instruments`, `tag_labels`; **schema v2**) so the detached terminal labels rows exactly like the workbench. |
| D23 | MusicBrainz recording credits | `CoverArtService.fetch_recording_credits(recording_id)` hits `/ws/2/recording/<mbid>?inc=artist-rels&fmt=json` with a descriptive User-Agent, splits relations into instruments / vocals / performers / producers, and caches the raw payload under `cache/credits/<mbid>.json`. It is the deterministic half of the lane plan: instruments + vocal parts annotate lanes (`lane_credits`), the distinct vocalist count drives the "N singers" badge, and instruments no separator can render (sax, violin) become `credit-only` rows. Credits are advisory — a credited instrument may be inaudible and many recordings have none — so a miss/404/500 degrades to "no credits documented" and never fails a job. |
| D24 | 6-source extras (guitar / piano) | `neural_full` runs `StemSeparator.separate_extra_lanes` after the 4-source separation: HTDemucs-6s (`adefossez/HTDemucs-6s`, `5c90dfd2.safetensors`, 54.9 MB, registry key `htdemucs_6s`) is loaded on its own and writes `{stem}_{mode}_raw_guitar.wav` / `_raw_piano.wav` under the **same mode suffix** as the 4-source run, so `dynamic_layers._collect_extra_lanes` picks them up with no lane-code changes. The model is unloaded (`del` + `empty_cache`) before the next stage; a missing model/dependency returns `{}` and the track keeps 4-source lanes. Extras still pass the presence gate, so a silent guitar stem creates no row, and they are labelled `extra-source` / low confidence because 6-source SDR is materially lower than 4-source. |
| D25 | CLAP instrument/vocal tags | `neural_full` runs `ClapTagger` (`laion/clap-htsat-unfused`, 614 MB, registry key `clap`, cached under `cache/models/clap-htsat-unfused/`) over up to 24 evenly spaced 5 s windows and reports the labels that carry real mass. Scoring runs on **CPU on purpose**: CLAP's BatchNorm raises "Placeholder storage has not been allocated on MPS device!" on Apple MPS (measured), and a 24-window pass costs ~5 s. Scores are the **mean softmax share across the 12 label prompts** — relative, not calibrated probabilities — so an even spread (~8 %) reports nothing and `[processing] tag_threshold` (default 0.15 ≈ twice the even share) decides how loud a label must be. Results land in `tags.json` beside the stems (atomic write) and are folded into the lane plan: a tag annotates the lane that can render it (`guitar` → guitar row) or becomes a `tag-only` row with no audio. **Advisory only** — tags never touch the spectral verdict, the mix or the file metadata, and any failure (no model, no `transformers`, scoring error, non-CPU device with a CPU retry) degrades to "no tags", never a failed run. |
| D26 | Hosted separation (MVSEP) | `harvester/services/mvsep.py` is an **opt-in, per-track** engine: it is not part of any preset and nothing in it runs unless the user presses `☁ HOSTED SEPARATE` on the LAYERS page for a specific track, because it is the only path that uploads audio off this machine. `MVSEP_API_KEY` comes from the environment (`.env` fallback, NFR-6); a missing key is a status line, not an error. The client posts multipart to `{base}/separation/create`, polls `GET {base}/separation/get?hash=…` every 4 s until the **top-level** `status` is `done`/`error` (budget `max_wait_s`, default 1800 s) and downloads every returned file to `{input_stem}_{mode}_hosted_raw_{lane_key}.wav` in the same stem dir the local run uses. `sep_type` is the **`render_id`** of `GET /api/app/algorithms`, *not* its `id` (using `id` silently runs a different model); `SEP_TYPES` maps friendly names → ids and `[processing] hosted_sep_type` picks one, with `[processing] hosted_max_seconds` (0 = whole track) trimming the upload. The filename token *is* the lane key (`vocals-lead` → `lead_vocals`; `instrum-only`/`back-instrum` are sums and never become rows; an unknown token becomes its own lane), so any model — 4, 21 or 53 stems — needs no per-model table; hosted rows carry the `hosted` origin at high confidence and render audio like local lanes. Failures (HTTP error, queue timeout, `error` status) produce a status line with the server's message; the API key is never logged and is scrubbed from every message. |
| D27 | Measured speaker count (pyannote) | `harvester/services/diarization.py` measures how many voices the audio contains and reports the number **beside** the MusicBrainz credit count — `LanePlan.measured_speakers` vs `LanePlan.singer_count` (plan summary: `2 singers · 3 speakers measured`). It never overwrites credits, never adds or removes a lane and never gates a stage, because measured counts are demonstrably noisy (*Headlock* → 1 measured vs 2 credited; a controlled two-singer splice → 3 speakers at thresholds 0.70/0.80/0.90 alike). It is the optional `diarize` extra (`pyannote.audio>=4.0`), runs on **CPU** (Apple MPS fails on the pooling layer, `invalid low watermark ratio 1.4`), measures the separated vocals stem when there is one, and is capped by `[processing] diarize_max_seconds` (0 = whole track). The pipeline is `pyannote/speaker-diarization-community-1` when the token may read it, else assembled from `segmentation-3.0` + `wespeaker-voxceleb-resnet34-LM` + agglomerative clustering with `get_plda` patched out (the PLDA step lives in a gated repo). A missing extra or model degrades to a status line, never a failed run. |

## 6. Acceptance criteria

Verifiable statements; the test plan (`docs/09-resilience-testing.md`) maps to these.

- **AC-1** App launches in < 3 s and shows service status within 1 s of mount.
- **AC-2** Mode A with slskd healthy and a seeded FLAC match → output is a tagged FLAC whose
  spectral analysis shows no brick-wall cutoff below 20 kHz, with embedded cover art when
  the Cover Art Archive has a front image.
- **AC-3** Mode A with slskd stopped → job completes via yt-dlp within the fallback timeout;
  UI shows the degraded-mode indicator; output is a tagged MP3 with provenance comment.
- **AC-4** A synthetic upscaled MP3→FLAC fixture (low-passed at 16 kHz) is rejected with
  verdict FRAUD, deleted, and the job completes via fallback (fixture recipe in `docs/04`).
- **AC-5** Mode B on a mixed directory: lossless and ≥ threshold files untouched;
  below-threshold files replaced at identical paths; every original recoverable from
  `.trash/`; batch report lists every input file exactly once.
- **AC-6** Killing the app mid-batch (SIGTERM) leaves no partial files in the library:
  originals either untouched or in `.trash/`, temp files cleaned.
- **AC-7** During a 10-job batch with active downloads, the UI processes keypresses and
  redraws without visible stalls (Textual pilot test asserts event-loop lag < 50 ms).
- **AC-8** Cancelling a job terminates its subprocesses within 2 s and marks it CANCELLED.
- **AC-9** AcoustID lookups respect ≤ 3 req/s and repeat files hit the local cache (no
  second network call).
- **AC-10** With no AcoustID key configured, the app still runs end-to-end using the
  metadata fallback chain (FR-8) and says so in the header.

## 7. Out of scope (v1)

- DRM circumvention of any kind; streaming-service account logins (browser cookies only as a
  user-configured yt-dlp option, at the user's own risk).
- Full dedup database, cross-library matching, listening statistics.
- Multi-user/server deployment, our own REST API, web GUI.
- Fake-24-bit detection and hi-res "spectral void" upsample detection (v2 extensions,
  `docs/04-spectral-antifraud.md` §9).

## 8. Legal & ethical constraints (normative for UX)

- The UI SHALL display a one-time first-run notice: the tool is for personal, legally
  entitled use; YouTube downloading generally violates YouTube's ToS; sharing copyrighted
  material on P2P networks may be illegal in the user's jurisdiction.
- No feature may be designed to defeat access controls or DRM.
- Logs and reports SHALL NOT contain API keys.
