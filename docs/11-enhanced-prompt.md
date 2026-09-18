# 11 — Enhanced Development Prompt (copy-paste)

> **How to use:** paste everything below the line into a coding assistant. If the assistant
> has access to this repository, it must read the referenced docs before each build step —
> the prompt is a self-contained condensation of them, but the docs are normative on
> conflicts. Build milestone-by-milestone (`docs/10-roadmap.md`), not all at once.

---

## ROLE & MISSION

You are an expert Python systems engineer building **`harvester`** — a "Hybrid Music Harvest
& Curation Engine": a desktop TUI that acquires the best verifiably-authentic audio for a
track using a **P2P-first (Soulseek via a local `slskd` daemon), stream-fallback (yt-dlp)**
strategy, verifies files with **audio fingerprinting** and **spectral anti-fraud analysis**,
and finishes them with **canonical metadata + cover art**. Two entry modes feed one 5-phase
async pipeline. Personal, legally-entitled use only; no DRM circumvention ever.

## TECH STACK (fixed — see docs/02 §1 for rationale)

- **Python ≥ 3.11**, strict asyncio; **Textual** (latest stable) for the TUI.
- **Runtime deps:** `textual`, `httpx`, `mutagen`, `yt-dlp`, `numpy`, `platformdirs`.
  Dev/test: `pytest`, `pytest-asyncio`, `respx`, `pytest-httpserver`, `scipy`, `soundfile`,
  `ruff`.
- **External binaries:** `ffmpeg`/`ffprobe` (hard requirement), `fpcalc` (Chromaprint),
  `slskd` daemon (optional — app must run degraded without it).
- **Deliberate substitutions:** yt-dlp runs as a **subprocess** (not in-process API);
  slskd is called via a thin **httpx REST client** (no wrapper lib) with startup OpenAPI
  verification; fingerprinting = **fpcalc binary + httpx → AcoustID REST** (not pyacoustid);
  spectral analysis = **ffmpeg f32le pipe → numpy STFT** (not librosa/ffmpeg-python).

## NON-NEGOTIABLE DIRECTIVES

1. **Strictly async.** One event loop (Textual's). Subprocesses via
   `asyncio.create_subprocess_exec` with concurrently drained stdout/stderr; blocking I/O
   (mutagen, fs, SQLite) via `asyncio.to_thread`; numpy STFT via `asyncio.to_thread`.
   No `requests`, no `time.sleep`, no sync `subprocess.run`, no heavy CPU on the loop.
   Event-loop lag must stay < 50 ms under load.
2. **No placeholders.** Every function ships production-ready: real FFT math, real
   AcoustID calls, real atomic file ops. TODOs are only allowed where docs mark something
   v2, and must cite the doc.
3. **State machine is truth.** States: `QUEUED, ANALYZING, HUNTING, P2P_DOWNLOADING,
   FALLBACK_DOWNLOADING, IDENTIFYING, SPECTRAL_CHECK, POLISHING, COMPLETED, SKIPPED,
   FAILED, CANCELLED`. A single transition table guards all changes; UI renders states,
   never infers them. Anti-loop invariant: once `fallback_attempted`, re-entering HUNTING
   or SPECTRAL_CHECK is illegal.
4. **Pipeline → UI via events only.** Immutable `JobEvent{job_id, seq, kind:
   STATE|PROGRESS|LOG|ERROR, ...}` on a bounded asyncio queue; a UI bridge coalesces to the
   latest state/progress per job and flushes at 8 Hz. Services never touch widgets.
5. **Every timeout from the registry** (docs/09 §4): probe 30 s; slskd search budget 25 s
   (poll 1.5 s); P2P stall 120 s; transfer poll 2 s; yt-dlp stall 90 s / total 900 s;
   fpcalc 60 s; AcoustID 15 s; cover art 15 s; transcode 300 s; spectral 30 s; health 5 s;
   kill grace 5 s. Retries: exponential backoff base 2 s, cap 60 s, jitter ±25%, per-class
   attempt limits (docs/09 §2). slskd behind a circuit breaker (3 failures → open 60 s →
   half-open probe).
6. **File safety.** Library-facing writes: temp file in target dir → fsync → `os.replace`.
   Mode B swap: write+tag temp → verify re-openable & duration ±5% → `os.replace(original →
   .trash/<date>/<HHMMSS>-<name>)` → `os.replace(temp → original)` → fsync dir; any failure
   after trashing rolls back from `.trash/`. Corrupt P2P downloads go to `quarantine/`.
   Startup sweeps stale workspace temps.
7. **Secrets** (`SLSKD_API_KEY`, `ACOUSTID_API_KEY`) come from environment only; config
   stores env-var *names*; logs are masked; reports never contain keys.
8. **Config-driven** (TOML, schema in docs/02 §6; precedence CLI > env > file > defaults).
   App dirs via `platformdirs` (`workspace/`, `cache/`, `logs/`, `reports/`, `quarantine/`).
9. **Tests alongside every module** (docs/09 §7): unit tests for pure logic; integration
   against fake slskd (pytest-httpserver/respx), stub yt-dlp/fpcalc executables, canned
   AcoustID payloads; Textual pilot tests for UI behavior. No test touches the real network.

## THE TWO MODES

- **Mode A (Single URL):** probe via `yt-dlp -J --no-playlist --skip-download` → hunt FLAC
  on slskd → download or fallback → identify → (spectral if P2P) → polish → write to
  `output_dir`. Playlists: `--flat-playlist` expansion, cap 50, user confirmation modal.
- **Mode B (Batch Audit):** recursive scan (exclude `.trash/`, hidden, quarantine);
  mutagen probe per container (matrix in docs/03 §1B.3); **always skip lossless**; skip
  lossy ≥ `batch.skip_bitrate_kbps` (**default 256** — this resolves the brief's
  193–319 kbps gap); queue the rest carrying existing tags or filename-parsed queries
  (`NN - Artist - Title` / `Artist - Title` patterns). Success ⇒ atomic in-place swap
  keeping the **original filename** (D4). Incremental JSONL batch report: every input file
  exactly one row (skipped/upgraded/failed, old bitrate, source, verdict, paths).
  Free-space guard: jobs × 40 MB × 1.5. Confirmation modal above 25 jobs.

## THE 5-PHASE PIPELINE (async stage queues; workers: analyze 2, hunt 2, p2p-dl 2,
fallback-dl 2, identify 1, spectral 1, polish 2; bounded queues = backpressure)

**Phase 1 — Input Analysis.** As per mode above. Reject live streams/DRM with clear
reasons; warn (allow) duration > 20 min.

**Phase 2 — Hybrid Hunt.** Title cleaning (NFKD + diacritic fold; strip noise tokens:
`official video|audio`, `lyric(s)`, `hd/hq/4k`, `mv`, `remaster(ed) [year]`, `explicit`,
site tags `[FLAC]`, leading track numbers; collapse whitespace). Up to 3 queries sharing
the 25 s budget: `"artist - title"` (feat kept) → `"artist title"` (feat stripped) →
`"title"` (only if zero candidates so far). slskd flow: POST search {searchText, unique
int token} → poll → **hard filters** (`.flac`; bitDepth ≥ 16 when reported; size within
0.85–1.30× expected `dur × bitdepth × sr × ch / 8`, or `dur × 110 KB/s` when attributes
missing; duration ±5% when known) → **score & rank** (weights table in docs/06 §8: user
speed ≥ 1000 kbps +15, queueLength 0 +10, uploadCount ≥ 1000 +10, 24-bit +10, size/duration
precision bonuses, spam-filename −20, VBR-on-FLAC −25; deterministic tie-break) → enqueue
download → poll transfers → stall = no byte progress 120 s → move completed file to
`workspace/<job_id>.flac` → validate (mutagen parses, FLAC stream, duration ±5% of
reported, bits ≥ 16). Invalid ⇒ next candidate once (max), then fallback. Fallback
triggers: budget exhausted with zero candidates, breaker open/disabled slskd, stall, two
candidate failures. Fallback download:
`yt-dlp -f "bestaudio[acodec^=opus]/bestaudio/best" --no-playlist --newline
--progress-template "download:%(progress._percent_str)s|%(progress.downloaded_bytes)s|
%(progress.total_bytes_estimate)s|%(progress._speed_str)s|%(progress._eta_str)s"
-o workspace/<job_id>.%(ext)s URL` — **no `-x`** (raw Opus; transcode is Phase 5 after
fingerprinting). Parse progress lines (concurrent stdout/stderr drains); classify failures
via the stderr catalog (docs/07 §6: 429 → RateLimited backoff ≥ 60 s ×3; sign-in/age →
PermanentSource with cookies hint; private/unavailable/DRM/live → PermanentSource;
unmatched exit ≠ 0 → TransientNetwork, lane max 2 attempts). Post-validate: exists,
> 1 MB, ffprobe duration ±5% of probe. `source_kind ∈ {P2P_FLAC, STREAM_OPUS,
STREAM_OTHER}` from actual container.

**Phase 3 — Ground-Truth ID.** `fpcalc -json -length 120 <file>` → SHA-256(fingerprint)
cache check (SQLite WAL, TTL 90 d) → miss: `POST https://api.acoustid.org/v2/lookup`
(client key from env; `meta=recordings+releases+releasegroups+isrcs`; token-bucket
≤ 3 req/s; 429/5xx → one retry after 2 s). Select top result: score ≥ 0.85 HIGH (adopt
fully), 0.60–0.85 MEDIUM (adopt, keep existing album/year if missing, flag low confidence),
< 0.60 → no match. Fields: title, artists (join " / "), album + year from earliest dated
release, first sorted ISRC, `mb_recording_id`, `mb_release_id`. **Fallback chain** (merge
per-field, first title wins): AcoustID → probe_meta (A; split `title` on " - ", `channel`
as artist fallback) → orig_tags (B) → filename parse → stem + "Unknown Artist". Record
`meta_source`. Cover art: `GET https://coverartarchive.org/release/{mbid}/front-500`
(follow redirects, 1 req/s, file-cached by mbid; 404/timeout ⇒ no art, never fails job).
Phase 3 never fails a job except fpcalc error on a validated file → quarantine + fallback
(once). Mode B: canonical vs orig_tags divergence (different MBID or < 50% title
similarity) → WARNING + `identity_shift: true` in report. **Fingerprinting always precedes
transcoding.**

**Phase 4 — Spectral Anti-Fraud** (only `source_kind == P2P_FLAC`; others record
NOT_APPLICABLE — provenance exemption; this also prevents the mandated Opus→MP3-320 upcast
from tripping our own check). Decode:
`ffmpeg -v error -ss {0.3×dur} -t 60 -i file -ac 1 -ar 48000 -f f32le -` → numpy. STFT
n_fft 8192, hop 2048, Hann; 500 Hz bands 1–24 kHz; band energy = 90th-percentile over
frames of mean band power, in dB. `BASE` = median(E[2–10 kHz]); `FLOOR` = p10(all bands);
band dead when `E < max(BASE−55, FLOOR+3)`. Cutoff `f_c` = upper edge of highest non-dead
band under a contiguous dead run ≥ 1.5 kHz (none ⇒ f_c = 24 kHz). Steepness
`S = E[f_c−1k..f_c] − E[f_c..f_c+1k]` (dB/kHz). Verdicts in order: analyzable < 10 s or
RMS < −50 dBFS or decode error → INCONCLUSIVE; (f_c ≤ 19.0k ∧ S ≥ 30) ∨ (f_c ≤ 17.0k ∧
S ≥ 20) ∨ (f_c ≤ 15.0k ∧ S ≥ 12) → **FRAUD**; claimed SR ≥ 88.2 kHz ∧ everything above
22.4 kHz dead → INCONCLUSIVE (hi-res upsample suspicion); f_c ≤ 19.0k ∧ 15 ≤ S < 30 →
INCONCLUSIVE (borderline); else PASS. INCONCLUSIVE = PASS + WARNING unless
`spectral.strict`. **FRAUD ⇒ unlink file, log cutoff+steepness, reroute to
FALLBACK_DOWNLOADING.** Budget ≤ 3 s/file. Ship the 7 synthetic fixtures (docs/04 §10:
fraud @16.0k & @18.5k Butterworth-8 lowpass FLAC, honest full-band, honest gradual
12 dB/oct roll-off, near-silent, 5 s short, 96 kHz void-upsample) as deterministic unit
tests. Return a verdict dataclass `(verdict, f_c, S, debug_bands)`; raise only on
decode/subprocess failure → mapped to INCONCLUSIVE.

**Phase 5 — Polish & Sync.** Tag via mutagen: MP3 → **ID3v2.3** (`save(v2_version=3)`;
strip old tags first, then write TIT2/TPE1/TALB/TYER/TSRC + TXXX MUSICBRAINZ_*/
SOURCE_ORIGIN/TAG_ORIGIN + COMM); FLAC → Vorbis comments (TITLE/ARTIST/ALBUM/DATE/ISRC/
MUSICBRAINZ_*/SOURCE_ORIGIN/DESCRIPTION) + `add_picture` front-cover JPEG (type 3, skip if
art > ~400 KB or absent). Fallback files: transcode per `ffmpeg.transcode` —
`mp3-320` (default): `ffmpeg -v error -y -i in -map 0:a:0 -c:a libmp3lame -b:a 320k
out.mp3`; `mp3-v0`: `-q:a 0`; `keep-opus`: no transcode — then tag with mutagen (never
rely on ffmpeg metadata). **Mandatory provenance** on transcoded output:
`TXXX:SOURCE_ORIGIN=youtube_opus_transcoded_mp3` + COMM "Lossy stream origin (YouTube
Opus ≈160 kbps), transcoded to MP3 320 CBR — not a lossless source." Placement — Mode A:
`output_dir/<Artist> - <Title>.<ext>` (sanitized; same-MBID existing file → skip as
duplicate; other collision → ` (2)` suffix), temp+fsync+replace. Mode B: atomic swap per
Directive 6, keep original filename (D4; `batch.rename_to_canonical` optional off-default).
Cleanup: delete workspace temps, append report row
`(ts, job_id, mode, input, status, old_bitrate, source_kind, spectral_verdict, cutoff_hz,
canonical{...}, output_path, trash_path, error)`, emit COMPLETED.

## TUI (Textual — full spec docs/08)

- **StatusBar** (custom): title + service pills (slskd/ffmpeg/fpcalc/acoustid; ● ok,
  ▲ degraded-optional, ✗ unavailable, ⏻ disabled) + `jobs done/total`. Status worker
  every 10 s (skips slskd probe while breaker OPEN).
- **InputRow**: mode Select (A/B, Ctrl+P), Input, GO button, ⋯ button → **DirectoryPicker
  modal** (`DirectoryTree` + path input — Textual has no OS-native dialog).
- **JobTable** (`DataTable`): columns Track | Original (`mp3 128k`) | Target (`P2P FLAC`/
  `Fallback MP3`) | Phase (humanized state; `⚠FRAUD→` badge on reroute) | Progress
  (`▰▰▰▱…` 10-cell bar + pct; terminal: ✔/⏭/✖/⦸). Styling via TCSS classes on theme
  variables — never hardcoded colors. 500-row cap, render-hash diffing, updates only via
  the 8 Hz bridge flush.
- **LogConsole** (`RichLog`): `[job] PHASE` prefixes, level filter cycling (`l`), 2000-line
  cap, auto-scroll unless user scrolled up.
- **Keys**: Enter submit, Ctrl+P mode, `c` cancel selected (job flag + subprocess kill
  ≤ 2 s), `C` cancel all, `l` log level, `p` purge `.trash` (confirm), `r` re-run failed,
  `?` help overlay (includes the D2 honesty note: 320 CBR from ~160 kbps Opus is an upcast
  kept for compatibility; provenance-tagged), Ctrl+Q quit (confirm if jobs active →
  graceful shutdown: stop event → cancel workers → TERM/KILL subprocess registry → drop
  queued as CANCELLED → clean temps → final flush; `.trash/` and outputs untouched).
- **Modals**: FirstRunNotice (personal-use/ToS/jurisdiction text; persists acceptance),
  PlaylistConfirm (count + cap), QuitConfirm, batch > 25 confirmation, batch summary.
- **Lifecycle**: on_mount → config → env detection (missing ffmpeg/yt-dlp →
  FatalSetupScreen with install commands; missing fpcalc/AcoustID key → ▲ pill + degraded
  metadata chain; slskd down → ✗ pill, yt-dlp-only mode) → start orchestrator worker
  (`run_worker(..., exclusive=True, group="pipeline")`) + bridge + status workers.
  `WorkerFailed` → log traceback, ERROR console line, "pipeline halted" banner, app stays
  inspectable.

## BUILD ORDER (module-by-module; complete files + tests each step)

1. `pyproject.toml`, package skeleton, `appdirs.py`, `config.py` (+ `config.example.toml`)
2. `util/errors.py`, `util/retry.py` (backoff + circuit breaker), `util/logging_setup.py`
   (QueueHandler fan-out, secret masking), `util/subproc.py` (tracked registry, kill-all),
   `util/fsatomic.py`
3. `models.py`, `statemachine.py` (+ exhaustive transition tests)
4. `services/ffmpeg.py` (detection, f32le decode pipe, transcode, ffprobe duration)
5. `services/ytdlp.py` (probe, download, progress parse, failure catalog, kill semantics)
6. `analysis/titleclean.py`, `analysis/scoring.py`, `services/slskd.py` (health, OpenAPI
   verify, search/poll, transfers, breaker hook)
7. `services/acoustid.py` (fpcalc runner, lookup, rate limit, SQLite cache),
   `services/musicbrainz.py` (cover art), `services/tagging.py` (mutagen maps, D7)
8. `analysis/spectral.py` (+ the 7 fixture tests)
9. `pipeline/orchestrator.py` + `phase1…phase5` modules
10. `batch/scanner.py`, `batch/trash.py`, `batch/report.py`
11. `ui/` (bridge → widgets → screens → app), `__main__.py`
12. Integration tests with fakes (docs/09 §7.2), pilot tests (§7.3), packaging + user
    README quickstart

## DEFINITION OF DONE (map to docs/01 §6)

AC-1 launch < 3 s, pills < 1 s · AC-2 seeded FLAC → tagged lossless with art · AC-3 slskd
down → clean fallback MP3 + degraded pill · AC-4 16 kHz upcast fixture → FRAUD → delete →
fallback completes · AC-5 batch: skips correct, identical paths replaced, originals in
`.trash/`, report complete · AC-6 SIGTERM mid-batch → zero partials in library · AC-7 event
storm → lag < 50 ms, ≤ 8 flushes/s · AC-8 cancel ≤ 2 s subprocess death · AC-9 ≤ 3 req/s
+ cache hits offline · AC-10 no AcoustID key → full pipeline via fallback chain. Plus:
ruff clean, pytest green on 3.11/3.12 (ubuntu+macos), ≥ 80% coverage on
analysis/pipeline/batch/util, no placeholder functions, no blocking calls on the loop,
every timeout/threshold traceable to docs/09 §4 or config.

## CONSTRAINTS & HONESTY

- Personal use, legally entitled content only; YouTube downloading generally violates its
  ToS (first-run notice states this); no DRM circumvention — DRM content is refused
  explicitly.
- The Opus→MP3-320 default is an **upcast** (no quality gain): provenance tags are
  mandatory, `keep-opus`/`mp3-v0` are first-class config alternatives, and the help overlay
  says so plainly.
- If a requirement here conflicts with the normative docs (`docs/01–09`), the docs win —
  stop and flag the conflict instead of guessing.
