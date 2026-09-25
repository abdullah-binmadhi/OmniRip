# 14 — UI Hardening & Product Polish

> **Partly superseded by docs/01 D35 (guided Repair, M18).** Per-track state, hosted-run isolation, confirmations and diagnostics remain; layer-terminal, lane-filter, dirty-edit and cache-repair sections describe removed UI. Kept for history.


Status: **done** (shipped in `fbe4929`). This is the durable execution ledger for the UI-hardening
milestones that follow the shipped lane-expansion work (docs/13, D21–D27).

The goal is not to add another model. The goal is to make the existing acquisition,
stem, lane, hosted and detached-terminal workflows correct when users switch tracks,
interrupt work, reopen projects, encounter stale caches, or use a small terminal.

## 1. Execution contract

This document survives context compaction. At every compaction boundary:

1. Read this document first.
2. Run `graphify query "<the current milestone question>"` from the repository root.
3. Run `git status --short --branch` and record the current commit.
4. Read the current milestone's source and tests before editing.
5. Keep exactly one milestone in progress in the task tracker.
6. Update this document after each verified vertical slice.
7. Run the focused tests after each slice; run the full suite and ruff at milestone end.
8. Never mark a checkbox complete from intent; require real test output or a live artifact.
9. After all milestones: update docs/01, docs/02, docs/08, docs/10, README, CHANGELOG,
   config.example.toml and this document; run graphify update; review the diff; commit;
   push; verify the remote SHA.

The repository's existing graphify knowledge graph is the first project lookup source.
Scratch probes and logs remain under `~/.hermes/cache/scratch/`; this file is the durable
source of truth for implementation state, decisions and acceptance evidence.

## 2. Baseline before M0

- Branch: `main`
- Baseline commit: `2657415`
- Remote `main`: same SHA as local
- Working tree: clean
- Baseline tests: **405 passed, 1 skipped**
- Baseline lint: **ruff clean**
- Existing warnings: 8 pytest warnings, including pre-existing Textual coroutine/resource
  warnings and the Python 3.14 torch.jit warning. They must not increase; new warnings in
  touched tests are regressions.

## 3. Milestones

### M0 — Durable plan and acceptance ledger

Status: **done**

Deliver:

- This document with milestones, invariants, test map and compaction protocol.
- README/docs/10 index references once the feature is shipped.
- A current task-list entry for every milestone.

Acceptance:

- A future session can resume from this file without relying on chat history.
- The graph, git SHA, test baseline and current milestone are recorded.

### M1 — Per-track correctness and operation lifecycle

Status: **done**

Delivered:

- `harvester.ui.operation_state` — `WorkbenchOperationState` with a monotonic
  generation, one exclusive `Operation` at a time, operation tokens, cancellation
  requests and dirty-edit state.
- `WorkbenchWidget.load_job()` resets every track-scoped field, cancels track-scoped
  workers, stops the transport timer and bumps the generation.
- Stem separation tasks are keyed by `(path, generation)` so a same-path reload can
  never steal a stale task's results.
- `render-stream-enh`, `warm-mode-cache`, stem separation, extra lanes, CLAP tagging,
  layer build, layer commit, hosted separation, speaker measurement and credits lookup
  all ignore late results from an older generation.
- `☁ HOSTED SEPARATE`, `👥 SPEAKERS`, `CREDITS` and `SAVE LAYERS` are one-at-a-time
  operations with conflict messages instead of silent second runs.
- `SAVE LAYERS` clears the dirty flag only after a verified successful commit.
- Dirty edits surface as `UNSAVED EDITS — save or clear before leaving.`
- `DiscardEditsConfirmScreen` guards track switches while dirty.
- `QuitDirtyConfirmScreen` guards quit while dirty.
- `_apply_flush` never auto-loads a track over dirty edits.

Acceptance:

- [x] Track A leaves no lanes/credits/tags/speakers/plan on Track B
      (`tests/test_ui_workbench_state_additions.py`).
- [x] A stale worker token is rejected after a track change (unit-tested).
- [x] Conflicting operations raise a busy message instead of double-running
      (`tests/test_workbench_state.py`).
- [x] Track switching and quitting confirm before discarding edits
      (`tests/test_ui_pilot.py` — 8 passed).
- [x] Focused suites green: workbench state, workbench UI, UI pilots, operation state.
- [x] Ruff clean.

### M2 — Sidecar, cache and hosted-result integrity

Status: **done**

Delivered:

- Per-track sidecar naming: `.{stem}.layer_sidecar.json` next to the source, so
  two tracks in one folder can no longer clobber each other's plans.
- Sidecars record source identity (path, size, mtime, content fingerprint);
  `sidecar_source_matches()` refuses a sidecar that belongs to different audio —
  the terminal never edits another source's plan, and the workbench never imports
  foreign edits (`layer_sidecar.py`).
- Sidecar writes are atomic (temp file + `os.replace`).
- `harvester.analysis.enhancement.stem_cache` — stem cache manifest
  (`cache_manifest.json`): source fingerprint (size + mtime + head/tail bytes),
  engine, mode, preset, written after every separation; `cache_matches()` treats
  a missing manifest as legacy-valid but rejects a proven mismatch.
- `load_job()` now uses `stem_dir_for()` (single source of truth) and refuses to
  adopt stems whose manifest belongs to another source file, with a rebuild hint.
- Hosted MVSEP runs are isolated: downloads stage to temp names, the previous
  run's hosted stems are swapped out only after every new stem succeeded, and a
  failed run leaves the old set intact (`_swap_hosted_run`).
- Stage metadata: `diarization.json` (advisory speaker count, model, device,
  source fingerprint) and `hosted_run.json` (sep_type, algorithm, lane keys)
  live beside the stems; a matching `diarization.json` restores the measured
  count on reload.

Acceptance:

- [x] Same basename + size, different content → stems not adopted
      (`test_load_job_rejects_stale_cross_track_cache`).
- [x] Same basename + size, different content → sidecar not matched
      (`test_sidecar_records_and_checks_source_identity`).
- [x] A new hosted run replaces the old run's stems atomically; a failed run
      keeps them (`tests/test_mvsep.py` — 10 passed).
- [x] Measured speakers restore from matching `diarization.json`
      (`test_load_job_restores_measured_speakers_from_meta`).
- [x] Manifest round-trip and legacy behaviour (`tests/test_stem_cache.py`).
- [x] Focused suites green (87 passed), Ruff clean.

### M3 — Safe, understandable operations UX

Status: **done**

Delivered:

- `HostedSeparationScreen` — the only audio-egress action now shows a blocking
  modal: file name, size, duration scope, MVSEP model picker (live algorithm
  list with the configured default preselected; falls back offline) and an
  explicit `UPLOAD TO MVSEP` confirm. Cancel = zero network activity.
- `_launch_hosted_run()` is the single entry to a hosted job and only runs after
  the screen's confirm callback.
- Every failure status names the cause and the retry action: hosted, stem
  separation, speaker measurement and credits lookups.
- `🔍 DIAG` button opens a read-only diagnostics modal (models via
  `importlib.metadata` — no heavy imports on the UI thread, tool paths via
  `shutil.which`, MVSEP key presence only, never its value, config + cache size).
- Speaker measurement heartbeat: elapsed-seconds status every 10 s while
  pyannote runs on CPU, auto-stopped when the pass ends or the track changes.

Acceptance:

- [x] Upload happens only after an explicit confirm
      (`test_hosted_screen_confirms_before_any_upload`).
- [x] Cancel never touches the network (`test_hosted_screen_cancel_never_uploads`).
- [x] A failed hosted run reports the reason and how to retry
      (`test_hosted_failure_status_names_the_cause_and_retry`).
- [x] Heartbeat reports elapsed time and stops when done
      (`test_diarization_heartbeat_reports_elapsed_and_stops_when_done`).
- [x] Diagnostics render injected rows and `collect_diagnostics()` is
      fast/metadata-only (`tests/test_ui_m3_confirmations.py` — 6 passed).
- [x] Full suite green (429 passed, 1 skipped), Ruff clean.

### M4 — Cache repair, metadata and result reuse

Status: **done**

Delivered:

- `♻ REBUILD` — drops the cached grid and rebuilds the timeline from stems
  (`_ensure_layers_built(force=True)`).
- `🏷 RE-TAGS` — re-runs the CLAP pass and replans with fresh tags; tagging
  results persist to a `tags.json` stage meta and reload only when the source
  size matches.
- `🗑 CLEAR CACHE` — confirmation screen (`CacheClearConfirmScreen`), then
  deletes exactly this track's stem dir (refuses anything outside the stem
  cache root) and drops the derived state.
- The pyannote pipeline loads once per session (`self._diarizer`), not once
  per click.
- Advisory results restored on reload show model/device/tags in the status
  line ("Restored from cache: speakers … · tags …").

Acceptance:

- [x] Rebuild forces a fresh timeline (`test_rebuild_layers_forces_a_new_timeline`).
- [x] RE-TAGS replans after tagging (`test_rerun_tags_runs_tagging_then_rebuilds`).
- [x] Cache clear is confirmed and deletes only the track's own dir
      (`test_clear_cache_requires_confirmation_and_deletes_only_the_stem_dir`).
- [x] One pipeline load for two measurements (`test_diarizer_reused_across_runs`).
- [x] Matching tags.json resurfaces on reload (`test_tags_restore_with_source_check`).
- [x] `tests/test_ui_m4_repair.py` 5 passed; Ruff clean.

### M5 — Detached terminal, lane and accessibility polish

Status: **done**

Delivered:

- Terminal heartbeat (`layer_sidecar.terminal.json`, terminal-owned): the main
  app detects a dead window after 30 s and shows a one-time relaunch hint; a
  clean exit removes the file.
- Ownership banner in the detached terminal: "Selection & edits live in this
  terminal · playhead/transport owned by the main OmniRip window".
- Lane provenance filter in `LayerStudio` (`f` in the terminal): all → audio
  (separator/DSP/6-source/mix) → hosted → credits → tags; click mapping and
  rendering both use the filtered list; a footer shows the active filter.
- Save verification summary extended: files written, seconds edited, rebuilt
  length and the mix-residual verdict in one line.

Deferred (recorded, not silently dropped):

- Full A/B audition between original/local/hosted/edited output needs a
  multi-stream render pipeline; the existing [1] MP3 vs [2] ENH stream switch
  already covers the original-vs-processed case. Deferred until the audition
  pipeline is designed.
- Main-app global keyboard shortcuts (h/d/r/t on LAYERS) — the page is
  reachable via focus and the terminal has its full binding set; added when
  the accessibility pass covers all pages at once.

Acceptance:

- [x] Filter cycles and hides non-matching rows (`tests/test_ui_m5_polish.py`).
- [x] Unknown-origin lanes appear only in the "all" view.
- [x] Terminal ownership banner renders (`test_layer_terminal_shows_ownership_banner`).
- [x] Save summary reports files/seconds/residual (`test_commit_summary_reports_edited_seconds`).
- [x] Stale terminal gets one visible relaunch hint (`test_stale_terminal_transport_hint`).
- [x] Heartbeat write/read/age/clear round-trip (`test_terminal_heartbeat_round_trip`).
- [x] `tests/test_ui_m5_polish.py` 6 passed; layer terminal/sidecar suites green;
      Ruff clean.

### M6 — Verification, documentation and delivery

Status: planned

Deliver:

- Focused tests for every new behavior, written RED → GREEN → REFACTOR.
- Full pytest, ruff, import smoke tests and headless Textual tests.
- Real artifacts for sidecar/cache/hosted-result workflows without exposing credentials.
- Update docs/01 decision/acceptance rows, docs/02 architecture, docs/08 TUI behavior,
  docs/10 roadmap, README, CHANGELOG, config.example.toml and this document.
- Run `/graphify --update` / `graphify update .` after all project file changes.
- Review the complete diff for secrets, stale TODOs, accidental scope and warning increases.
- Commit with a durable multi-line message and push to GitHub.
- Verify local HEAD equals `git ls-remote origin main`.

Acceptance:

- All milestone checkboxes in this document have evidence beside them.
- Full suite is green with no new warnings attributable to the work.
- Ruff is clean.
- Working tree is clean after commit.
- Remote commit SHA matches local HEAD.

## 4. Non-negotiable invariants

- MusicBrainz credits remain authoritative over measured pyannote speaker counts.
- MVSEP is never invoked by startup, acquisition or a preset; it remains explicit per track.
- Raw audio egress is visible and confirmed before MVSEP upload.
- Spectral verdicts remain deterministic and never depend on CLAP, pyannote or an LLM.
- Credit-only and tag-only entries never receive fabricated audio.
- Hosted output from different models/runs is never silently mixed.
- One process owns each sidecar field; writes are atomic.
- A stale worker cannot mutate the current track.
- No secret value is printed, logged, committed or included in diagnostics.
- A failed/cancelled optional stage never destroys a valid local result.
- Existing mix-reconstruction, presence-gate, analysis-budget and atomic-swap invariants
  remain intact.

## 5. Test map

Expected additions/changes include:

- `tests/test_ui_workbench.py` — track reset, stale worker, operation gating, dirty state,
  confirmation and hosted/diarization lifecycle.
- `tests/test_layer_sidecar.py` — per-track identity, stale sidecar, schema migration,
  atomic recovery and transport ownership.
- `tests/test_stem_separator.py` — cache identity and manifest invalidation.
- `tests/test_mvsep.py` — run isolation, cancellation, cleanup, redaction and retry states.
- `tests/test_diarization.py` — reuse metadata, cancellation/failure states and persistence.
- New cache/operation-model tests where the behavior is complex enough to be independent.
- Existing dynamic-lane, layer-editor, terminal-app and hardening tests must stay green.

## 6. Decision log for this milestone

- Hosted default remains the lead/back vocal model until the model picker provides a visible
  cost/output choice.
- Speaker measurement remains advisory; no automatic credit correction is allowed.
- Credits remain explicit unless a later UX decision adds a visible automatic lookup mode.
- Batch hosted separation remains out of scope until cost/consent/reporting are designed.
- Existing pre-work warnings are recorded; this milestone must not add new warnings.

## 7. Progress ledger

- [x] M0 plan and baseline recorded.
- [x] M1 per-track state and operation lifecycle.
- [x] M2 sidecar/cache/hosted integrity.
- [x] M3 safe operations UX and diagnostics.
- [x] M4 cache repair and result reuse.
- [x] M5 terminal/lane/accessibility polish.
- [x] M6 tests, docs, graph, review, commit and remote verification.

Last verified baseline: `405 passed, 1 skipped; ruff clean` at commit `2657415`.
Independent review (docs/14 M6): two critical bugs found and fixed before ship —
the MVSEP model picker silently ignored the selected model (collapsed button-id
mapping), and the diarization staleness guard compared the vocals-stem path
against the track path, discarding every speaker count; plus `_swap_hosted_run`
backup moved outside the rollback block (split old set on mid-move failure).
Regression tests added for all three.
Shipped: `fbe4929` on origin/main — `443 passed, 1 skipped`; Ruff clean;
graphify 3485 nodes / 7866 edges / 212 communities; local and remote SHA equal.

M6 follow-up (independent review round 2, all findings closed): the diarization
stage-meta restore now verifies the recorded file's fingerprint (the vocals
stem, not the mp3); the tagging/extra-lane status tails are generation-guarded;
a stale diarize worker can no longer stop the new track's heartbeat timer; the
hosted confirm captures its source track and refuses to upload if the track
changed while the dialog was open; "retag-pass" joins the track-worker cancel
set; the algorithm fetch never refills a dismissed screen; successful hosted
swaps sweep `.staging-*`/`.old-*` crash litter. Remaining deferred minors
(recorded, not dropped): sync `_clear_track_cache` rmtree + in-flight guard,
same-basename sidecar collision naming, app-side `clear_dirty()` accessor.
