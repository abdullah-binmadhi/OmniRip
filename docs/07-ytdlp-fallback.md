# 07 — yt-dlp Fallback Lane

Specifies `services/ytdlp.py`: subprocess-based extraction for Phase 1 probes (Mode A) and
the FALLBACK_DOWNLOADING lane. Design principles: **process isolation** (crashes can't take
down the app), **killability** (cancel = terminate the process), **machine-readable
output** (`-J` JSON, `--progress-template`).

## 1. Binary management

- Resolve `ytdlp.binary` via `shutil.which`; support `python -m yt_dlp` form (config).
- Startup: `yt-dlp --version` (to_thread, 10 s). Missing → hard stop with install help
  (docs/02 §8). Version older than **30 days** → WARNING pill: YouTube extractors break
  often; the standard fix is `pip install -U yt-dlp`. Surface the exact command in the log.
- Pin nothing in `pyproject.toml` beyond `yt-dlp>=2024.x` floor; always allow user updates.

## 2. Metadata probe (Phase 1, Mode A)

```
yt-dlp -J --no-playlist --skip-download --no-warnings <URL>
```

- Timeout 30 s (registry). Parse stdout as JSON (stderr kept for diagnostics).
- Fields captured → `probe_meta`: `id`, `title`, `channel`, `uploader`, `artist`, `track`,
  `album`, `duration`, `thumbnail`, `webpage_url`, `extractor_key`, `is_live`.
- Playlist expansion (D10, UI-confirmed): `yt-dlp -J --flat-playlist --no-warnings <URL>`
  → `entries[]` (id, title, duration, url); cap `batch.playlist_cap`; each entry becomes a
  child job with a direct watch URL when the extractor is YouTube.

## 3. Audio download (FALLBACK_DOWNLOADING)

```
yt-dlp -f "bestaudio[acodec^=opus]/bestaudio/best"
       --no-playlist --newline --no-warnings
       --progress-template "download:%(progress._percent_str)s|%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s|%(progress._speed_str)s|%(progress._eta_str)s"
       --progress-template "postprocess:postprocess|%(postprocess.status)s"
       -o "<workspace>/<job_id>.%(ext)s"
       <URL>
```

- **No `-x`/`--extract-audio`**: we want the raw Opus/webm; transcoding is Phase 5's job
  after fingerprinting (D9) and spectral exemption is provenance-based (D3).
- Format string rationale: YouTube's best audio is Opus ≈128–160 kbps full-band; on other
  extractors `bestaudio` may be m4a/aac — `source_kind` is set from the actual container
  (`STREAM_OPUS` if `.webm`/`.opus` with opus codec per ffprobe, else `STREAM_OTHER`).
- Optional (user risk, config `ytdlp.cookies_from_browser`): append
  `--cookies-from-browser <browser>` for age-restricted content (docs §7).
- Output template is job-id keyed → no filename collisions, trivial cleanup.

## 4. Progress & stream parsing

- Read stdout and stderr **concurrently** (two drain tasks; prevents pipe-buffer deadlock).
- `download:` lines → parse percent/bytes/speed → update `job.download` → PROGRESS event
  (coalesced by the UI bridge to ≤ 5 Hz per job).
- `postprocess:` lines → ignored for progress (we do no yt-dlp postprocessing) but logged.
- stderr lines matching the failure catalog (§6) set a pending classification; exit code +
  file validation make the final decision.
- No progress line for `ytdlp.stall_timeout_s` (90 s) → treat as stall → terminate.
  Overall cap `ytdlp.total_timeout_s` (900 s).

## 5. Post-download validation

1. Output file exists, size > 1 MB (audio-only sanity), else FAILED(TransientNetwork, retry
   once — YouTube throttling often produces truncated files).
2. `ffprobe -v error -show_entries format=duration -of csv=p=0 <file>` duration within ±5%
   of `probe_meta.duration` when known (catches wrong/part streams).
3. Handoff to IDENTIFYING with `source_kind` set; `fallback_attempted = true` (D12).

## 6. Failure catalog (stderr pattern → classification)

| Pattern (substring/regex, case-insensitive) | Class | Action / user-facing hint |
|---------------------------------------------|-------|---------------------------|
| `HTTP Error 429`, `Too Many Requests` | RateLimited | Backoff 60 s, 2 retries; hint: wait / re-run later; frequent 429 → suggest checking IP (YouTube throttling) |
| `Sign in to confirm`, `age-restricted`, `login` | PermanentSource | Fail; hint: configure `cookies_from_browser` (own risk) |
| `Private video`, `unavailable`, `removed`, `not exist` | PermanentSource | Fail with reason from JSON `availability` when present |
| `Unsupported URL`, `No video formats`, `extraction failed` | PermanentSource | Fail; hint: check the URL / update yt-dlp |
| `is live`, `Premiere` | PermanentSource | Reject live (no VOD audio); hint: retry after the stream ends |
| `DRM`, `Widevine` | PermanentSource | Out of scope (docs/01 §7); explicit refusal message |
| `ffmpeg ... not found` | ConfigError | Startup check should prevent; hard fail with install hint |
| `Fragment N not found` (repeated, non-fatal) | — | Log WARNING; rely on §5 validation |
| exit ≠ 0, unmatched | TransientNetwork | Retry once with backoff, then FAILED |
| `Unable to extract` / traceback dump | TransientNetwork | Retry once; hint: `pip install -U yt-dlp`; include last stderr lines in log |

Retry policy details (backoff/jitter): docs/09 §2. All retries share the per-job fallback
budget: at most **2 attempts** total in this lane before FAILED.

## 7. Kill & cancel semantics

- Cancel/stall/quit → `proc.terminate()` (SIGTERM), 5 s grace, then `proc.kill()`.
- Use a process group (`start_new_session=True` on POSIX) so yt-dlp's child ffmpeg
  processes die too; `kill_all()` on shutdown walks the registry.
- After kill: remove partial `<job_id>.*` files from workspace (`.part` included).

## 8. Transcode handoff (Phase 5 reminder)

Transcoding is **not** done here. Phase 5 applies `ffmpeg.transcode` policy (D2):
`mp3-320` (default, `-b:a 320k`), `mp3-v0` (`-q:a 0`), or `keep-opus` (no transcode; output
stays `.opus`/`.webm` audio-only). Mandatory provenance tags on any transcoded output
(FR-12). Commands in docs/03 §5.2.

## 9. Legal note (surfaced in first-run notice)

Downloading from YouTube generally violates YouTube's ToS; this lane exists per the user's
brief and is the user's responsibility (docs/01 §8). No DRM circumvention is implemented or
attempted; DRM-protected content is refused explicitly (§6).
