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
