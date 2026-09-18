# Changelog

All notable changes to `harvester` are documented here. Versioning follows
[Semantic Versioning](https://semver.org/). The milestone mapping is in
[`docs/10-roadmap.md`](docs/10-roadmap.md).

## [Unreleased]

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