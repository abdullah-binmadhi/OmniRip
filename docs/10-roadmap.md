# 10 — Roadmap (M0 → M7)

Each milestone ends with a **runnable app** and a demo script. Suggested cadence: one
milestone per work session with a coding assistant, feeding it
`docs/11-enhanced-prompt.md` + the docs listed under "Specs" for that milestone.

| M | Name | Depends on | Key deliverable |
|---|------|-----------|-----------------|
| 0 | Scaffold & environment | — | ✅ Complete — project skeleton, config system, dependency detection, empty TUI boots |
| 1 | Mode A, fallback-only | M0 | ✅ Complete — URL → tagged MP3 via yt-dlp (no P2P, no fingerprint) |
| 2 | slskd hunt lane | M1 | ✅ Complete — P2P search, scoring, download, validation, failover to M1 path |
| 3 | Ground-truth ID | M2 | ✅ Complete — fpcalc + AcoustID + cover art + tagging conventions |
| 4 | Spectral anti-fraud | M3 | ✅ Complete — FFT verdicts, FRAUD→fallback reroute, fixture test suite |
| 5 | Mode B batch audit | M4 | ✅ Complete — scanner, skip matrix, atomic swap, `.trash/`, batch report |
| 6 | TUI hardening | M5 | ✅ Complete — bridge throttle/coalesce, modals, keybindings, first-run, status worker, playlist flow |
| 7 | QA & packaging | M6 | ✅ Complete — CI matrix, coverage gate, quickstart, CHANGELOG |
| 10 | Neural Audio Enhancement Workbench | M6 | ✅ Complete — model manager, DSP crossover/progressive mono, NVSR/FlashSR providers, presets, preview manager, workbench screen, CLI --enhance |

---

## M0 — Scaffold & environment

**Specs:** 01 (read fully), 02, 11.
**Build:** `pyproject.toml` (deps per docs/02 §1), package tree (docs/02 §2), appdirs
layout, config loader + `config.example.toml`, logging setup with masking, binary
detection (ffmpeg/ffprobe/fpcalc/yt-dlp/slskd health), `models.py` + `statemachine.py`,
Textual shell rendering the docs/08 §1 layout with static placeholder data, FatalSetupScreen
for missing ffmpeg.
**Acceptance:** `python -m harvester` boots < 3 s (AC-1) showing real service pills;
statemachine unit tests exhaustive; config validation errors are actionable; no pipeline yet.

**Status:** ✅ Complete. Validated with 21 passing tests, clean Ruff checks, packaged CLI
version/help smoke checks, and asynchronous dependency probing. This machine lacks
`ffmpeg`/`ffprobe`, so the runtime correctly routes to its fatal setup screen until those
required binaries are installed.

## M1 — Mode A, fallback-only

**Specs:** 03 (Phase 1A, 5), 07, 02 §5 (orchestrator with analyze/fallback/identify-passthrough/polish queues).
**Build:** orchestrator skeleton (queues, workers, events, shutdown), yt-dlp probe +
download + progress parsing + failure catalog, Phase 5 tagging from `probe_meta` only
(fallback chain levels 2/4/5), MP3 transcode per D2 with provenance tags, Mode A input row
wired to the pipeline, JobTable live updates (unthrottled is fine here).
**Acceptance:** public-domain/CC test video URL → tagged 320k MP3 in output_dir with
provenance comment; PermanentSource hints correct for private/live/DRM URLs; cancel kills
subprocess ≤ 2 s (AC-8); quit leaves no temps (AC-6 partial).

**Status:** ✅ Implementation complete. Validated with 34 passing tests, clean Ruff checks,
bytecode compilation, fake-service end-to-end orchestration, live progress parsing, atomic
placement, and cancellation. A real public-domain URL smoke test is pending installation
of `ffmpeg` and `ffprobe` on the development machine.

## M2 — slskd hunt lane

**Specs:** 06, 03 (Phase 2), 09 (§1–§4).
**Build:** slskd client (health, OpenAPI verification per D6, search+poll, download
enqueue+transfer poll), titleclean multi-query, hard filters + scoring, candidate retry
(FR-5), stall detection, circuit breaker, degraded-mode fast-fail (FR-6), file handoff to
workspace, quarantine.
**Acceptance:** with a seeded test track: P2P FLAC acquired, validated, tagged-from-probe
(no fingerprint yet); slskd stopped → automatic fallback, pill red, hunt fast-fails (AC-3);
fake slskd integration tests green (docs/09 §7.2).

**Status:** ✅ Implementation complete. Validated with 55 passing tests, clean Ruff checks,
bytecode compilation, mocked slskd HTTP transport flows, fake-service P2P orchestration,
candidate retry, quarantine, and breaker-open fallback. A real slskd smoke run is pending
installation of the slskd daemon plus local `ffmpeg`/`ffprobe`.

## M3 — Ground-truth ID

**Specs:** 05, 03 (Phase 3).
**Build:** fpcalc subprocess, AcoustID client (token bucket ≤ 3/s, SQLite cache, score
thresholds), field mapping, Cover Art Archive client + cache, mutagen tagging module
(ID3v2.3 / FLAC picture, D7), fallback chain wiring, `meta_source` recording.
**Acceptance:** real lookup on a known track returns HIGH-confidence canonical tags + art
(AC-2 partial); key unset → chain degrades gracefully with header pill ▲ (AC-10); cache
hit makes zero HTTP calls (AC-9); tagging unit tests incl. v2.3 assertion.

**Status:** ✅ Implementation complete. Validated with 64 passing tests, clean Ruff checks,
mocked AcoustID/Cover Art HTTP flows, real FLAC/MP3 tagging with art, cache bypass, and
fallback-chain orchestration. A real AcoustID smoke run is pending installation of the
slskd daemon, local `ffmpeg`/`ffprobe`, and an AcoustID API key.

## M4 — Spectral anti-fraud

**Specs:** 04, 03 (Phase 4), 09 §7.1 (fixtures).
**Build:** ffmpeg decode pipe → numpy STFT analyzer, verdict rules §6, fixture generator
(7 fixtures), Phase 4 gate + FRAUD→fallback reroute with D12 guard, verdict numbers in
logs/report, `spectral.strict` config.
**Acceptance:** all fixture verdicts correct (AC-4); a real upscaled sample (manual smoke
4) rejected and re-acquired via fallback; phase ≤ 3 s; UI shows `⚠FRAUD→` badge;
NOT_APPLICABLE for fallback files (D3).

**Status:** ✅ Implementation complete. Validated with the 7-fixture verdict suite
(sharp raised-cosine spectral bricks per the docs/04 §10 encoder-faithfulness deviation),
Phase 4 gate tests, FRAUD→fallback reroute under the D12 guard, and NOT_APPLICABLE
handling for the fallback lane; verdict numbers surface in logs and the batch report.
A real upscaled-sample smoke (manual item 4) remains pending real-service execution.

## M5 — Mode B batch audit

**Specs:** 03 (Phase 1B, 5.3), 01 (FR-13/14, D1/D4/D5), 09 §6.
**Build:** scanner (walk, exclusions, container/bitrate matrix, filename parsing), free-space
guard, batch confirmation modal, atomic swap with rollback, `.trash/` layout + retention
purge + `p` keybind, JSONL report writer (incremental), `identity_shift` warnings.
**Acceptance:** mixed 5-file dir → correct skips/queues (AC-5); injected failure between
trash-move and replace rolls back byte-identical (unit); SIGTERM mid-batch → AC-6; report
lists every input exactly once (AC-5); original filename preserved (D4).

**Status:** ✅ Implementation complete. Validated with 110 passing tests (12 new: scanner
skip matrix with real MPEG fixtures, trash layout/collisions/rollback/purge, atomic swap
success + injected failure, report schema/incremental rows, Mode B orchestration AC-5
semantics, >25 confirmation guard, free-space guard, failure report rows, identity-shift
flagging, batch trash purge), clean Ruff checks and bytecode compilation. The batch
fallback lane uses `ytsearch1:<query>` inputs (D13); stale `*.harvester.tmp.*` artifacts
from a crashed swap are purged by the next scan (AC-6). Real-library smoke tests remain
pending `ffmpeg`/`ffprobe` installation on this machine.

## M6 — TUI hardening

**Specs:** 08 (all), 09 §5.
**Build:** UiBridge coalescing + 8 Hz flush, row render-hash diffing, log level cycling,
row cap/paging, all keybindings + modals (help, playlist confirm, quit confirm, purge),
first-run notice persistence, event-loop lag instrumentation, WorkerFailed banner path.
**Acceptance:** 1000-event storm pilot test: ≤ 8 flushes/s, loop lag < 50 ms (AC-7);
10-job simulated batch fully interactive; playlist cap + confirm flow (D10); all pilot
tests green (docs/09 §7.3).

**Status:** ✅ Implementation complete. Validated with 162 passing tests (27 new: bridge
coalescing/storm, log-console filter, config persistence, playlist orchestration, Phase
1/3/5 unit coverage, and UI pilots for bindings/modal/render). Clean Ruff and bytecode
checks; core coverage (analysis/pipeline/batch/util) at 85%. Textual's default `ctrl+p`
command-palette binding is disabled so the chord toggles Mode A/B per docs/08 §5.

## M7 — QA & packaging

**Specs:** 09 §7–§8, 01 §6 (all ACs).
**Build:** coverage gaps to ≥ 80% core; CI workflow (ruff + pytest matrix); manual smoke
checklist executed and recorded; packaging (console script `harvester`, version pinning
policy per docs/07 §1); user-facing README quickstart (install deps → configure keys →
run); CHANGELOG.
**Acceptance:** every AC-1…AC-10 demonstrated; smoke checklist items 1–6 pass on a clean
machine (or VM/container with binaries installed); fresh-clone install runs the TUI in
< 10 minutes following the README.

**Status:** ✅ Implementation complete. Console script `harvester` (verified `harvester
--version`), `CHANGELOG.md`, README quick-start, coverage config (`[tool.coverage]`), and
a GitHub Actions CI matrix (Python 3.11/3.12 × ubuntu/macos; ruff + pytest with an 80%
core-coverage gate). Core coverage measured at 85%. Items 1–6 of the manual smoke
checklist (docs/09 §7.4) remain pending real-service execution on a machine with slskd,
ffmpeg/ffprobe, and an AcoustID key installed — they are recorded as release gates here,
not automatable without those binaries.

## M10 — Neural Audio Enhancement Workbench

**Specs:** `m10_enhancement_workbench_plan.md`, band-limited residual isolation, sub-$f_c$ invariance.
**Build:**
- Optional dependencies extra `restore = ["huggingface_hub>=0.20", "torch>=2.2", "torchaudio>=2.2"]` in `pyproject.toml`.
- `ModelManager` with automated Hugging Face checkpoint download and SHA-256 validation.
- `EnhancementProvider` protocol and 4 providers: `ConservativeDSPProvider` (pure NumPy), `NVSRProvider` (Apple Silicon MPS / CPU), `FlashSRProvider` (distilled diffusion air-band), `HybridCoOpProvider`.
- DSP engine (`split_bands` zero-phase crossover, `apply_progressive_mono` sub-100Hz mono blend, `match_spectral_slope`, `apply_limiter` soft-knee ceiling at -0.1 dBFS).
- 5 deterministic presets (`conservative`, `fast_balanced`, `de_sizzle`, `extended_air`, `narrow_stereo`).
- `EnhancementExporter` rendering 320k MP3 derivatives with Mutagen ID3 provenance tags (`TXXX:DERIVED_FROM_LOSSY=true`, `TXXX:SYNTHETIC_HIGH_BAND=true`, etc.) while leaving original master untouched.
- `PreviewManager` generating 15s energetic A/B preview WAV pairs and launching non-blocking OS player (`open` / `xdg-open`).
- `CurationWorkbenchModal` interactive Textual screen accessible via `w` keybinding in `HarvesterApp`.
- Headless CLI flags: `harvester --enhance FILE [--preset PRESET] [--bitrate BITRATE]`.

**Status:** ✅ Implementation complete. Validated with 28 passing unit and integration tests across DSP, providers, exporter, presets, previews, and UI pilot (`tests/test_model_manager.py`, `tests/test_enhancement_dsp.py`, `tests/test_enhancement_providers.py`, `tests/test_enhancement_exporter.py`, `tests/test_enhancement_workbench.py`, `tests/test_main.py`, `tests/test_ui_pilot.py`). Zero regressions on full project test suite (205 passed).

---

## Working agreement for coding-assistant sessions

1. One milestone per session; start by reading this roadmap + the milestone's spec docs.
2. Deliver complete files (no placeholders — brief directive #3), plus the module's unit
   tests in the same pass.
3. End each session by updating: roadmap checkbox state (this file), any decision-log
   changes in docs/01 §5, and the timeout registry if new timeouts appeared.
4. Never weaken a spec silently — if a requirement is infeasible, record the conflict in
   docs/01 §5 and ask before proceeding.
