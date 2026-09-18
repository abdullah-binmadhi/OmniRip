# Changelog

All notable changes to `harvester` are documented here. Versioning follows
[Semantic Versioning](https://semver.org/). The milestone mapping is in
[`docs/10-roadmap.md`](docs/10-roadmap.md).

## [Unreleased]

### Fixed

- **slskd 0.26 API compatibility:** the D6 OpenAPI check now normalizes the
  version-templated route strings served by slskd 0.26+ (`/api/v{version}/...`),
  and the download lane targets `POST /api/v0/transfers/downloads/{username}` with
  the new array body instead of the legacy `/api/v0/users/{username}/downloads/{token}`
  form. The OpenAPI route picker no longer relies on a dead placeholder regex, so
  download-route selection is derived from the live API surface again.

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