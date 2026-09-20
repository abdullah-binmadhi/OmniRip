# 09 — Resilience, Error Handling & Testing

## 1. Error taxonomy (`util/errors.py`)

Single exception hierarchy; every raised error carries `retryable: bool`, `user_hint: str`,
and optional `job_id`. Workers classify once, at the boundary — no string-matching deeper
in the stack.

| Class | Examples | Retryable | Policy |
|-------|----------|-----------|--------|
| `ConfigError` | ffmpeg/yt-dlp binary missing, bad config TOML, slskd 401, OpenAPI schema mismatch (D6) | ❌ | Hard fail (launch screen) or lane-disable with explicit UI message |
| `ServiceUnavailable` | slskd connect refused, AcoustID 5xx | ⚠️ lane-scoped | Counts toward circuit breaker; job reroutes (hunt → fallback) rather than retrying in place |
| `TransientNetwork` | timeouts, DNS blips, yt-dlp unmatched exit≠0, stalled transfers | ✅ | Backoff policy §2 |
| `RateLimited` | AcoustID 429, YouTube HTTP 429 | ✅ | Longer backoff (§2 note) |
| `PermanentSource` | private/unavailable/geo-blocked/DRM/live video, unsupported URL | ❌ | FAILED immediately with the docs/07 §6 user hint |
| `ValidationError` | unparseable download, duration mismatch > 5%, size 0, mutagen write failure after retry | ⚠️ | Quarantine file; candidate retry (P2P, FR-5) or fallback (once, D12); else FAILED |
| `FraudVerdict` | spectral FRAUD | n/a | **Not an error** — control-flow event: delete + fallback (docs/03 Phase 4) |
| `DiskError` | no space, permission denied, fsync/replace failure | ❌ | FAILED; Mode B rollback from `.trash/` (docs/03 §5.3) |
| `Cancelled` | user cancel, shutdown | n/a | Terminal CANCELLED; subprocess kill + temp cleanup |

`IllegalTransition` (state machine) is a **programming-error** exception: crash the worker,
log full traceback, surface "pipeline halted" banner (docs/08 §7). It must never be caught
and swallowed.

## 2. Retry & backoff

- Exponential: `delay = min(cap, base × 2^attempt) × uniform(0.75, 1.25)` (jitter ±25%).
- Defaults: `base = 2 s`, `cap = 60 s`.

| Operation | Max attempts | Notes |
|-----------|--------------|-------|
| AcoustID lookup | 2 (1 retry) | then metadata fallback chain — never blocks the job |
| RateLimited (YouTube 429) | 3 | first backoff forced ≥ 60 s |
| yt-dlp download (lane total) | 2 | per docs/07 §6; then FAILED |
| P2P candidate download | 1 per candidate; ≤ 2 candidates | then fallback lane |
| slskd REST call (non-search) | 2 | connect-level failures feed the breaker |
| Cover Art fetch | 1 | best-effort |
| mutagen write | 2 | then ValidationError |

## 3. Circuit breaker (slskd lane)

States: `CLOSED → OPEN` after **3 consecutive** connect-level failures; `OPEN` for **60 s**
(all hunts fast-fail to fallback — FR-6); `OPEN → HALF_OPEN` single probe
(`GET /api/v0/session`); success → CLOSED, failure → OPEN (timer resets). Transitions
logged WARNING and mirrored to the StatusBar pill (docs/08 §6). Application-level errors
(404s, empty searches) never trip the breaker — only transport/connect/auth failures.

## 4. Timeout registry (single source of truth)

Every value configurable; defaults normative. Anything not listed here must not invent its
own timeout — add it here first.

| Operation | Default | Config key |
|-----------|---------|------------|
| yt-dlp metadata probe | 30 s | `timeouts.probe_s` |
| slskd search total budget (per job) | 25 s | `slskd.search_timeout_s` |
| slskd search poll interval | 1.5 s | `slskd.poll_interval_s` |
| slskd transfer poll interval | 2 s | `slskd.transfer_poll_s` |
| P2P download stall (no bytes) | 120 s | `slskd.stall_timeout_s` |
| yt-dlp download stall (no progress line) | 90 s | `ytdlp.stall_timeout_s` |
| yt-dlp download total | 900 s | `ytdlp.total_timeout_s` |
| fpcalc subprocess | 60 s | `timeouts.fpcalc_s` |
| AcoustID HTTP | 15 s | `timeouts.acoustid_s` |
| MusicBrainz/Cover Art HTTP | 15 s | `timeouts.coverart_s` |
| ffmpeg transcode | 300 s | `timeouts.transcode_s` |
| ffmpeg probe (`ffprobe` duration) | 15 s | `timeouts.ffprobe_s` |
| Spectral phase (decode+analysis) | 30 s | `timeouts.spectral_s` |
| slskd health check | 5 s | `timeouts.health_s` |
| Subprocess kill grace (TERM→KILL) | 5 s | `timeouts.kill_grace_s` |
| UI service status interval | 10 s | `ui.status_interval_s` |
| Layer Studio per-second analysis budget | 100 ms / s of track | `layers.ANALYSIS_MS_PER_SECOND_BUDGET` |
| Layer Studio run-length collapse threshold | 600 s (≥ 600 segments) | `layers.LONG_TRACK_SECONDS` |

## 5. Cancellation & shutdown semantics

- Per-job: `cancel_requested` checked at each stage boundary and inside poll loops
  (≤ 2 s reaction, AC-8); kills that job's tracked subprocesses only.
- Global (quit/SIGTERM): docs/02 §5.3 — stop event, cancel workers, `kill_all()`
  (TERM → 5 s → KILL), drop queued jobs as CANCELLED, remove workspace temps, final UI
  flush, exit. `.trash/` and completed outputs are never touched by cleanup (AC-6).
- SIGINT in terminal = Textual's quit path; both signals route to `orchestrator.shutdown()`.

## 6. Disk & file safety

- Free-space guard before batches (NFR-5) and before each P2P download (candidate size ×
  1.2 vs. free space on the workspace volume).
- Workspace temp naming `<job_id>.*` — startup sweeps leftovers from prior crashes.
- Quarantine dir for validation failures; auto-purge > 7 days.
- Every library-facing write = temp + fsync + `os.replace` (invariant 4, docs/02 §9).

## 7. Test plan

Framework: `pytest` + `pytest-asyncio`; HTTP mocking `respx`; generated audio fixtures
(docs/04 §10); Textual `App.run_test()` pilots. No test touches the real network.
Coverage target: ≥ 80% on `analysis/`, `pipeline/`, `batch/`, `util/`; services covered via
mocks. `ruff` clean; CI matrix Python 3.11/3.12, ubuntu + macos.

### 7.1 Unit tests (mandatory per module)

| Module | Key cases |
|--------|-----------|
| `analysis/titleclean` | noise-token stripping table; feat handling q1 vs q2; unicode folding; track-number prefixes; idempotence (clean(clean(x)) == clean(x)) |
| `analysis/scoring` | canned slskd payloads → expected ordering; spam-filename penalty; missing attributes → heuristic path; tie-break determinism (seeded) |
| `analysis/spectral` | **all 7 fixtures from docs/04 §10**; parameter sensitivity snapshot; INCONCLUSIVE paths (short/silent) |
| `statemachine` | exhaustive legal/illegal transition table incl. D12 anti-loop (fallback→HUNTING illegal) |
| `batch/scanner` | skip matrix per container table (docs/03 §1B.3) with tiny generated files; exclusion dirs; unreadable-file isolation |
| `batch/trash` + `util/fsatomic` | swap success; failure injected after step 4 → rollback restores original byte-identical; retention purge; name collisions across same-day runs |
| `services/tagging` | MP3 saved as ID3v2.3 (re-read asserts `TYER` present, no v2.4-only frames); FLAC picture block round-trip; provenance tags on transcoded output (FR-12) |
| `services/acoustid` | cache hit → zero HTTP (respx assert); rate limiter ≤ 3/s under 10 concurrent lookups; score-threshold selection table (docs/05 §4) |
| `util/retry` | backoff sequence with jitter bounds; breaker state machine incl. half-open probe timing |
| `pipeline/phase5` | collision suffix policy; D11 duplicate skip; transcode policy switch (mp3-320 / mp3-v0 / keep-opus) via ffmpeg stub |

### 7.2 Integration tests (fake externals)

- **Fake slskd**: `pytest-httpserver` (or respx on httpx) serving: health, search with
  canned responses (including one fraud-flagged user), transfer polling sequence
  InProgress→Completed; download "file" = generated FLAC fixture served from a temp dir.
  Scenarios: happy path → tagged FLAC; timeout → fallback; stall → candidate retry;
  breaker open after 3 connection refusals.
- **Fake yt-dlp**: executable shell/python stub on PATH emitting canned `-J` JSON and
  scripted progress lines, copying a fixture Opus file to `-o` target; failure-catalog
  variants per docs/07 §6 (exit codes + stderr patterns).
- **Fake fpcalc**: stub returning canned JSON; AcoustID via respx with recorded real-shape
  responses (HIGH/MEDIUM/LOW/no-match).
- **End-to-end (all fakes)**: Mode A URL → COMPLETED FLAC with tags; Mode A with slskd
  down → MP3 + provenance; Mode B 3-file dir (flac skip, 320k skip, 128k upgrade) →
  swap + trash + report row set (AC-5 semantics).

### 7.3 UI pilot tests (docs/08 §9)

Launch < 3 s (AC-1); submit → row lifecycle QUEUED→ANALYZING; event storm (1000
PROGRESS events in 1 s) → flush ≤ 8/s and loop lag < 50 ms (AC-7); `c` cancels (AC-8);
degraded pill on slskd failure (AC-3 partial); first-run notice persistence.

### 7.4 Manual smoke checklist (release gate, real services)

1. slskd up + one known seeded track → Mode A → FLAC acquired, tags + art correct,
   spectral PASS logged with numbers.
2. Stop slskd → Mode A same track → MP3 via fallback, provenance comment present,
   degraded pill shown.
3. Copy a 5-file mixed library to /tmp → Mode B → verify swaps, `.trash/` recoverable,
   report complete; re-open files in a player.
4. Upload-test a deliberately upscaled FLAC on a test account (or simulate via hosts-file
   block mid-download) → FRAUD path exercised end-to-end (AC-4).
5. `kill -TERM` during a batch → AC-6 verified.
6. Age-restricted URL without cookies → clean PermanentSource message; with
   `cookies_from_browser` configured → proceeds (user's risk acknowledged in help).

## 8. Definition of done (every PR)

- Unit tests for changed modules; integration test when a service client changes.
- No blocking calls on the loop (checklist: docs/02 §5.2); `PYTHONASYNCIODEBUG=1` run of
  the touched flow is clean.
- New timeouts/thresholds added to the registry (§4) and config schema (docs/02 §6).
- State transitions go through `statemachine`; new states/edges update docs/02 §4.4.
- `ruff check` + `pytest` green; docs cross-references still valid.
