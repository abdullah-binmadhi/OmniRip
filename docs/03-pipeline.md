# 03 — The 5-Phase Pipeline (detailed spec)

Normative details for each phase. Worker/queue topology: `docs/02-architecture.md` §5.
Timeouts referenced below are registered in `docs/09-resilience-testing.md` §4.

## Phase overview

| # | Phase | Reads | Writes | On failure |
|---|-------|-------|--------|-----------|
| 1 | Input Analysis | URL or directory | `probe_meta` / job set (Mode B: + `orig_*`) | Permanent → FAILED |
| 2 | Hybrid Hunt | `probe_meta`/`orig_tags`, slskd | `candidates`, `source_kind`, `workspace_path` | No match/timeout → fallback lane |
| 3 | Ground-Truth ID | `workspace_path` | `canonical_meta` | Degrade to fallback chain, continue |
| 4 | Spectral Check | `workspace_path` (P2P lossless only) | `spectral.verdict` | FRAUD → delete + fallback lane |
| 5 | Polish & Sync | everything above | tags, art, transcode, final placement, report row | Rollback (Mode B), FAILED |

---

## Phase 1 — Input Analysis

### 1A. Mode A (URL)

1. Validate URL syntax (must parse with scheme `http(s)`); reject obviously non-URL input
   with an actionable message.
2. Metadata probe (no download):
   `yt-dlp -J --no-playlist --skip-download --no-warnings --no-check-certificates? (no — keep certs) <URL>`
   Timeout 30 s. Parse JSON: `id`, `title`, `channel`/`uploader`, `album`, `artist`,
   `track`, `duration`, `thumbnail`, `webpage_url`, `extractor_key`.
3. Playlist detection: if URL contains `list=` **and** user intent is a playlist (UI toggle
   "expand playlists", default off per D10), re-probe with `--flat-playlist -J`, cap at
   `batch.playlist_cap`, and require confirmation at the cap. Each entry becomes a child job
   with URL `https://www.youtube.com/watch?v=<entry.id>` (or the entry's `url`).
4. Sanity gates: reject live streams (`is_live == true` without VOD), reject DRM errors
   (mapped in docs/07 §6), warn (but allow) duration > 20 min.
5. Build `query_raw` preference chain: `artist + title` tags if present → else parse
   `title` (YouTube music titles are usually "Artist - Title" or "Title" with `channel`
   as artist) → else full title.

### 1B. Mode B (directory scan)

Runs as a single worker streaming results into `q_analyze` (backpressure via bounded queue).

1. Walk: `os.walk` (in `to_thread`, chunked yields), excluding `.trash/`, hidden dirs,
   `quarantine/`, and symlink loops.
2. Audio extensions: `.mp3 .m4a .mp4 .aac .flac .ogg .oga .opus .wav .aiff .aif .wma .wv .ape`.
3. Probe each file with mutagen (`to_thread`); unreadable files → report row
   `status=skipped, reason=unreadable` (never crash the scan).

   | Container | Bitrate source | Skip rule |
   |-----------|----------------|-----------|
   | FLAC / WAV / AIFF / ALAC(m4a codec alac) / WavPack / APE | lossless | always skip |
   | MP3 | `MP3.info.bitrate` | skip if ≥ `skip_bitrate_kbps × 1000` (D1) |
   | M4A/AAC | `MP4.info.bitrate` | same |
   | OGG/Opus | `OggOpus.info.bitrate` / estimate size÷duration | same |
   | WMA | `ASF.info.bitrate` (if available) else size÷duration | same |

4. For queued files extract search metadata: `title`/`artist`/`album` tags → else filename
   parse. Filename patterns (ordered): `NN - Artist - Title`, `Artist - Title`,
   `NN. Title`, fallback `Title = stem` (strip track numbers, underscores→spaces, strip
   extension-like suffixes such as `(1)`).
5. Pre-flight: free-space check (NFR-5) and a scan summary event (`found N, skip X,
   queue Y`) rendered in the log + a confirmation for batches > 25 jobs.
6. Each queued file becomes a `TrackJob(mode=BATCH_AUDIT)` with `orig_*` populated.

---

## Phase 2 — Hybrid Hunt

### 2.1 Query cleaning (`analysis/titleclean.py`)

Deterministic, unit-tested. Steps:

1. Unicode NFKD normalize; fold diacritics to ASCII (`é→e`); keep case.
2. Strip bracketed/parenthesised noise tokens (case-insensitive): `official video`,
   `official audio`, `lyric video`, `lyrics`, `audio`, `hd`, `hq`, `4k`, `mv`, `video`,
   `remaster(ed) <year>?`, `<year> remaster`, `explicit`, `mono`, `stereo`, `digital`.
   **Keep** `(feat. X)` / `(with X)` in query 1; strip in query 2.
3. Strip leading track numbers (`01.`, `1 -`) and site tags `[FLAC]`, `[MP3]`, `【...】`.
4. Collapse whitespace; strip trailing punctuation; drop tokens that are pure noise
   (`www.`, `.com`, URL fragments).
5. Emit ordered unique queries (max 3):
   - `q1 = "<artist> - <title>"` (feat kept)
   - `q2 = "<artist> <title>"` (feat/subtitle stripped)
   - `q3 = "<title>"` (only if q1/q2 returned zero hard-filtered candidates)

Query budget: `search_timeout_s` (25 s) **shared** across queries — q1 gets the remaining
budget, q2/q3 run only while budget remains (each poll cycle checks the deadline).

### 2.2 Search & candidate selection

Full client behavior in `docs/06-slskd-integration.md`. Summary:

1. `POST` search {searchText: qN, unique token}; poll every `poll_interval_s` until
   complete or deadline.
2. **Hard filters** per file response: extension `.flac`; reported `bitDepth ≥ 16` when
   present; size sanity `0.85 ≤ size / expected_bytes ≤ 1.30` where
   `expected ≈ duration_s × bit_depth × sample_rate × channels / 8` (attributes) or
   `duration_s × 110 KB/s` (16/44 heuristic) when attributes absent; duration within ±5%
   of `probe_meta.duration_s` / `orig_duration_s` when known.
3. **Score & rank** survivors (weights: docs/06 §8). Deduplicate by (user, filename).
4. Select top candidate → request download → poll transfers → on completion move file from
   slskd download dir to `workspace/<job_id>.flac` (cross-device-safe copy+unlink fallback).

### 2.3 Post-download validation (still Phase 2)

- mutagen can parse it and reports a FLAC stream (`FLAC.info` present).
- Duration within ±5% of the search-response-reported duration (catches truncated/wrong files).
- Non-zero size; `bits_per_sample ≥ 16`.

Failure → `p2p_retries += 1`; if ≤ 1 retry and another candidate exists → next candidate;
else → fallback lane. Corrupt file moved to `quarantine/` (NFR-5).

### 2.4 Fallback triggers (→ FALLBACK_DOWNLOADING)

Any of: query budget exhausted with zero hard-filtered candidates; slskd circuit open or
disabled; download stall (no byte progress for 120 s); two candidate failures; user cancel
of P2P lane only (n/a v1). Sets `source_kind = STREAM_*` after yt-dlp completes
(spec: `docs/07-ytdlp-fallback.md`).

---

## Phase 3 — Ground-Truth ID

Spec: `docs/05-fingerprinting-metadata.md`. Contract here:

1. Run `fpcalc -json -length 120 <workspace_path>` (subprocess, 60 s timeout).
2. Check local SQLite cache by fingerprint hash → hit: skip network.
3. Miss: AcoustID `POST /v2/lookup` (`meta=recordings+releases+releasegroups+isrcs`),
   rate-limited ≤ 3 req/s, 15 s timeout, one retry on 5xx/timeout.
4. Select best result (score thresholds per docs/05 §4); build `CanonicalMetadata`
   (title, artists, album, year, isrc, MB recording/release ids, confidence).
5. No/low match → fallback chain: `probe_meta` (A) / `orig_tags` (B) → filename parse →
   stem-as-title. **Phase 3 never fails the job** unless fpcalc itself errors on a file we
   just validated — then treat as ValidationError → quarantine + fallback lane (once).
6. Mode B note: also compare `canonical_meta` against `orig_tags`; large divergence
   (different recording MBID or < 50% title similarity) is logged as a WARNING and recorded
   in the report row (`identity_shift: true`) — the file may be a mislabeled original.

Fingerprinting **always precedes** transcoding (D9).

---

## Phase 4 — Spectral Anti-Fraud Check

Normative algorithm: `docs/04-spectral-antifraud.md`. Contract here:

1. **Applies only when** `source_kind == P2P_FLAC` (D3). Otherwise record
   `verdict = NOT_APPLICABLE` and pass through.
2. Decode a 60 s mid-track excerpt → numpy → STFT → cutoff + steepness → verdict
   (`PASS | FRAUD | INCONCLUSIVE`), all under a 30 s phase timeout, in `to_thread` (D8).
3. Outcomes:
   - `PASS` → Phase 5.
   - `INCONCLUSIVE` → default PASS + WARNING; if `spectral.strict` → fallback lane.
   - `FRAUD` → unlink file (log path + metrics), set `spectral` detail,
     `fallback_attempted` guard checked (D12) → FALLBACK_DOWNLOADING.
4. Every verdict is written to the batch report row and logged with cutoff/steepness numbers.

---

## Phase 5 — Polish & Sync

### 5.1 Tagging & art (all sources)

Per `docs/05-fingerprinting-metadata.md` §8: write canonical tags with mutagen
(MP3 → ID3v2.3 per D7; FLAC → Vorbis comments + picture block). Fetch Cover Art Archive
front-500 image by release MBID (15 s timeout, cached); embed if ≤ ~400 KB; **art failure
never fails the job**. Provenance tags per FR-12 for transcoded fallback files:

- `TXXX:SOURCE_ORIGIN` = `youtube_opus_transcoded_mp3` (or `p2p_flac`, `stream_opus_kept`)
- `COMM` (MP3) / `DESCRIPTION` (FLAC): `"Lossy stream origin (YouTube Opus ≈160 kbps),
  transcoded to MP3 320 CBR — not a lossless source."`

### 5.2 Transcode (fallback files only, if `ffmpeg.transcode != "keep-opus"`)

```
ffmpeg -v error -y -i workspace/<job>.webm -map 0:a:0 -c:a libmp3lame -b:a 320k out.mp3   # mp3-320
ffmpeg -v error -y -i workspace/<job>.webm -map 0:a:0 -c:a libmp3lame -q:a 0   out.mp3   # mp3-v0
```

Then tag the MP3 with mutagen (do not rely on ffmpeg metadata mapping). `keep-opus` →
remux only if container isn't `.opus`/`.webm` audio-only; tag in place.

### 5.3 Final placement

**Mode A:** target `output_dir/<Artist> - <Title>.<ext>` (canonical if confident, else
probe/filename-derived; filesystem-sanitized). Collision policy: same canonical MBID
existing → skip as duplicate (D11); otherwise append ` (2)`, ` (3)`. Write via
temp+fsync+`os.replace` in the target dir.

**Mode B (atomic swap, FR-13)** — ordered steps, each failure-safe:

1. Precondition: temp new file fully written & tagged in the **same directory** as the
   original: `.<stem>.<jobid>.tmp`.
2. `fsync` temp file; verify re-openable by mutagen and duration within ±5% of original
   (guards against swapping in a wrong/short file).
3. Create `.trash/<YYYY-MM-DD>/` inside the scanned root if absent.
4. `os.replace(original, .trash/<YYYY-MM-DD>/<HHMMSS>-<original name>)` → `trash_path`.
5. `os.replace(temp, original_path)`.
6. `fsync` the directory fd (POSIX) to persist both renames.
7. On failure between steps 4–5: `os.replace(trash_path, original_path)` (rollback),
   then FAILED with `ErrorClass=DiskError`.
8. Success: append report row; delete other temp artifacts; emit COMPLETED.

Mode B keeps the original filename (D4); if `rename_to_canonical` is on, step 5 instead
targets `<dir>/<canonical name>.<ext>` and the report records both paths.

### 5.4 Cleanup & report

Remove `workspace/<job_id>.*`; append JSONL report row (schema: docs/09 §7 fixtures aside,
fields: `ts, job_id, mode, input, status, old_bitrate, source_kind, spectral_verdict,
cutoff_hz, canonical {title, artist, album, year, mbid}, output_path, trash_path, error`).
