# 05 — Fingerprinting & Canonical Metadata

Covers Phase 3 and the tagging half of Phase 5. Tools: `fpcalc` (Chromaprint), AcoustID web
service, MusicBrainz, Cover Art Archive, `mutagen`.

## 1. Pipeline position & ordering rule

Fingerprint the **downloaded source file** (FLAC or raw Opus) **before** any transcoding
(Decision D9): Chromaprint fingerprints survive light transcoding but match rates degrade on
double-transcoded audio (e.g. Opus→MP3). Phase order 3 → 4 → 5 is mandatory.

## 2. fpcalc invocation

```
fpcalc -json -length 120 <file>
```

- `-length 120`: fingerprint the first 120 s — AcoustID's reference length; faster and
  matches the database better than full-file prints.
- Output JSON: `{"duration": <float>, "fingerprint": "<base64-ish string>"}`.
- Async subprocess, 60 s timeout, stderr captured for diagnostics.
- Failure modes: binary missing (startup check already warns; Phase 3 → fallback chain),
  unparseable file (should be impossible post-validation → ValidationError, docs/03 §3.5).

## 3. AcoustID lookup

```
POST https://api.acoustid.org/v2/lookup
form: client=<APP_KEY>&format=json&meta=recordings&meta=releases
      &meta=releasegroups&meta=isrcs&duration=<int>&fingerprint=<fp>
```

- `meta` is posted as a **repeated** form field, not one `+`-joined string: URL-encoding turns
  the `+` into a literal plus and AcoustID then returns bare results with no `recordings`
  block (silent metadata loss — verified against the live API).
- **API key:** free registration at `acoustid.org/new-application`; supplied via env
  `ACOUSTID_API_KEY` (config stores only the env-var name — NFR-6). A gitignored `.env`
  (`ACOUSTID_API_KEY=…`, path override `OMNIRIP_ENV_FILE`) is loaded at startup for GUI
  launches that do not inherit shell exports; real environment variables always win (docs/01 D20).
- **Rate limit:** ≤ 3 requests/s (AC-9). Enforced by a token-bucket in `services/acoustid.py`
  plus the single `q_identify` worker (docs/02 §5.1). On HTTP 429 or `error` response about
  rate: back off 2 s, one retry.
- Response shape (abridged):

```json
{"status":"ok","results":[
  {"id":"<recording-gid>","score":0.93,
   "recordings":[{"id":"<mb-recording-mbid>","title":"Track Name",
     "artists":[{"id":"...","name":"Artist Name"}],
     "isrcs":["USRC17607839"],
     "releasegroups":[{"id":"...","title":"Album","type":"Album","secondarytypes":[]}]}],
   "releases":[{"id":"<mb-release-mbid>","title":"Album","country":"US",
     "date":{"year":1999,"month":5,"day":17}}]}
]}
```

- `status != "ok"` with no results → clean "no match" (fallback chain). Network error →
  one retry (15 s timeout) → fallback chain. **Never fails the job** (docs/03 §3.5).

## 4. Result selection & confidence

| AcoustID top-result `score` | Confidence | Behavior |
|------------------------------|------------|----------|
| ≥ 0.85 | HIGH | Adopt canonical metadata fully |
| 0.60 – 0.85 | MEDIUM | Adopt title/artist/album; keep existing album/year if result lacks releases; mark `low_confidence` in report |
| < 0.60 | LOW | Treat as no match → fallback chain |

Within an accepted result: prefer recordings that have `releases` with dates; album =
release title of the earliest dated release (original release preferred over reissues);
year = that release's `date.year`; ISRC = first of `recordings[0].isrcs` (sorted for
determinism). Store `mb_recording_id`, `mb_release_id`.

## 5. Caching (AC-9)

- SQLite `cache/acoustid.sqlite3`, WAL mode, accessed via `to_thread`.
- Table `lookups(fp_hash TEXT PK, duration INT, response_json TEXT, fetched_at TEXT)`;
  `fp_hash = sha256(fingerprint)`.
- Hit → skip network entirely. TTL `acoustid.cache_ttl_days` (90): stale rows re-fetched
  and overwritten.
- Cover art cached as files `cache/art/<mb_release_id>.jpg`.

## 6. Cover art (Cover Art Archive)

```
GET https://coverartarchive.org/release/{mb_release_id}/front-500
```

- Follow redirects (httpx `follow_redirects=True`), 15 s timeout, polite 1 req/s cap.
- 404/none → no art (not an error). Convert PNG→JPEG only if > 400 KB (keep embed small).
- No release MBID (fallback chain used) → try MusicBrainz recording→release lookup only if
  HIGH confidence title/artist exist; otherwise skip art. Art is best-effort everywhere:
  **art failure never fails the job** (docs/03 §5.1).

## 7. Metadata fallback chain (FR-8)

Applied in order; first source that yields a title wins; per-field merge (a later source
fills only missing fields):

1. AcoustID canonical result (per §4 confidence rules).
2. Mode A: `probe_meta` from yt-dlp (`artist`/`track`/`album` tags if the extractor
   provides them, else split `title` on " - " once → artist/title; `channel` as artist
   fallback when title has no separator).
3. Mode B: `orig_tags` from the file being replaced.
4. Filename parse (docs/03 §1B.4 patterns).
5. Last resort: title = filename stem, artist = "Unknown Artist" (flagged in report).

Provenance of the chosen metadata is recorded: `meta_source ∈ {acoustid, probe, orig_tags,
filename, stem}` → written to report row and (for `filename`/`stem`) a `TXXX:TAG_ORIGIN`
tag so the user knows tagging is heuristic.

## 8. Tagging conventions (Phase 5, mutagen)

### 8.1 Field map

| Canonical field | MP3 (ID3v2.3, D7) | FLAC (Vorbis comments) |
|-----------------|-------------------|------------------------|
| title | `TIT2` | `TITLE` |
| artist | `TPE1` (join multiple with " / ") | `ARTIST` |
| album | `TALB` | `ALBUM` |
| year | `TYER` (v2.3; mutagen maps `TDRC`→`TYER` when saving with `v2_version=3`) | `DATE` (YYYY or YYYY-MM-DD) |
| ISRC | `TSRC` | `ISRC` |
| track artist IDs | `TXXX:MUSICBRAINZ_ARTISTID` | `MUSICBRAINZ_ARTISTID` |
| recording ID | `TXXX:MUSICBRAINZ_TRACKID` | `MUSICBRAINZ_TRACKID` |
| release ID | `TXXX:MUSICBRAINZ_ALBUMID` | `MUSICBRAINZ_ALBUMID` |
| provenance | `TXXX:SOURCE_ORIGIN` + `COMM` (FR-12 text) | `SOURCE_ORIGIN` + `DESCRIPTION` |
| heuristic-tag flag | `TXXX:TAG_ORIGIN` | `TAG_ORIGIN` |
| cover art | `APIC` (encoding=3, mime `image/jpeg`, type 3 = front cover, desc "") | `Picture` block via `flac.add_picture()` (type 3) |

### 8.2 Write rules

- MP3: `audio.save(v2_version=3)`; strip pre-existing ID3v2.4-only frames that confuse
  v2.3 readers (delete all existing tags first, then write the map — deterministic output).
- FLAC: preserve existing non-conflicting Vorbis comments? **No** — write the canonical set
  only; the original file (with its tags) is preserved in `.trash/` for Mode B anyway.
- Merge policy for MEDIUM confidence: never blank a field the fallback chain doesn't
  provide; absent fields are simply not written.
- All mutagen I/O in `to_thread`; on `MutagenError` → one retry after re-open → else
  Phase 5 fails as `ErrorClass=ValidationError` (file goes to quarantine, original untouched).

## 9. Failure policy summary

| Failure | Effect |
|---------|--------|
| fpcalc missing | Startup warning; Phase 3 → fallback chain (§7) |
| fpcalc errors on validated file | ValidationError → quarantine + fallback lane (once, D12) |
| AcoustID key missing | FR-8/AC-10: fallback chain; header pill yellow |
| AcoustID network/5xx | Retry once → fallback chain |
| No match / low score | Fallback chain; `meta_source` recorded |
| CAA 404/timeout | No art; job proceeds |
| mutagen write error | Retry once → FAILED (Mode B: original untouched — swap happens only after successful tagging of the temp file) |
