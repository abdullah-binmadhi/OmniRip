# 12 — Layer Studio (per-second layered stem timeline)

Photoshop/Lightroom-style **per-second** stem editing for the Neural Enhancement
Workbench: one row per **song-detected** lane (vocals / kick / snare / hats /
sub_bass / bass / other, split out of the separated stems when the audio supports
it), one column per **fixed 1-second** segment, playhead-synced to the audio
player, click-to-seek, per-second defect flags, and (M2) surgical per-second edits
committed back to the stems.

The lane rows live **only** in the detached layer terminal (§6): the workbench
`LAYERS` page is the control panel (build / open / save), so the grid gets a full
terminal's width instead of a cramped box.

Delivered in four milestone phases:

| Phase | Name | Status |
|-------|------|--------|
| M1 | Visualize + inspect | ✅ Complete — raw 4-stem persistence, segment analysis engine, grid + playhead sync + click-to-seek |
| M2 | Per-second editing | ✅ Complete — cell actions (mute / de-bleed / de-ess / de-mud / drum-punch / …), edit plan, ~20 ms crossfade splice commit, "SAVE LAYERS" export |
| M3 | Backend hardening / polish | ✅ Complete — mix reconstruction residual budget (-40 dBFS) verified pre-edit and across commits, ≥ 20 dB de-bleed acceptance fixture, 600 s per-second analysis budget with run-length cell collapse |
| M4 | Dynamic lanes + detached terminal link | ✅ Complete — song-driven lane expansion (docs/01 D18), lanes render only in the detached terminal (D19), live two-way transport link over `layer_sidecar.transport.json` |

## 1. Decisions (normative — see docs/01 D14)

- **Time grid:** fixed `SEGMENT_SIZE_S = 1.0` seconds per column (no zoom in M1).
- **Layer set (dynamic):** the separated sources are the *source* set; rows are
  song-detected lanes (`vocals`, `kick`, `snare`, `hats`, `drums`, `sub_bass`,
  `bass`, `other`, plus any extra neural source such as `guitar` / `piano` from a
  6-source model); `mix` is used only as the Eco fallback row. See §6.
- **Home:** lane rows live in the **detached layer terminal** (`layer_terminal.py`,
  its own Terminal.app window). The workbench's `LAYERS` tab (`#wb-page-layers`) is
  the control panel — `⚡ BUILD STEMS`, `🪟 OPEN LAYER TERMINAL`, `💾 SAVE LAYERS`,
  `CLEAR` — and embeds no grid and no tool palette.
- **Raw source persistence:** neural and ensemble mode now persist per-source stems in
  the stem dir: `{input_stem}_{mode}_raw_{vocals,bass,drums,other}.wav`, plus
  `_hdemucs`-suffixed twins from the HDEMUCS pass (so BS-RoFormer files are never
  clobbered). Eco mode publishes only vocals + instrumental (`{suffix}_vocals.wav` /
  `{suffix}_instrumental.wav`).
- **LR4 low anchor:** per-source layer files are the HDEMUCS raw source below
  `crossover_hz` LR4-blended against the BS-RoFormer raw source above it — matching the
  merged VOC/INST audition. Eco fallback yields a 2-layer track (vocals + mix) because
  mid/side phase matrixing cannot split drums/bass/other reliably.
- **Analysis backend is torch-free:** envelopes (RMS dBFS clipped to [-60, 0] + peak)
  and per-second issue flags run in numpy + soundfile; only the neural separation itself
  loads torch, so building a timeline reuses the already-cached stems.

## 2. Feature fingerprint (M1, inspected)

### 2.1 Analysis engine — `src/harvester/analysis/enhancement/layers.py`

Pure-data backend, self-contained and UI-agnostic:

- `LayerTrack` / `LayerSource` / `LayerSegment` / `LayerIssue` dataclasses.
  `LayerSource.rms` (n_segments dBFS) + `level(seg_idx)` normalizes to 0..1 for bars.
  `LayerSegment.primary_issue` = highest-severity issue.
- `build_layer_sources(stem_dir, input_stem, mode, ...) -> dict[source, Path]` assembles
  the per-source WAVs (LR4 per-source blend, cached `{suffix}_layer_{name}.wav` on disk).
- `analyze_layer_segments(...)` slices the timeline into fixed segments, computes
  envelopes, and flags defects per second.
- `build_layer_track(...)` = the full pipeline → one `LayerTrack`.
- Issue fingerprint bands (reuse acoustic_detector semantics): vocal core
  300–3500 Hz (instruments → `vocal_bleed`), side-channel 1000–2800 Hz dominance
  (vocals/other → `whisper`), 5.5–8.5 kHz (vocals → `sizzle`), 250–350 Hz
  (vocals/other → `mud`), 30–120 Hz (bass/drums → `sub_rumble`).

### 2.2 Widget — `src/harvester/ui/layer_studio.py`

- `LayerStudio` (Textual `Widget`):
  - Emits `SeekRequested(seconds, layer)` and `SelectionChanged(segment, layer)` messages.
  - Renders a ruler row (timestamp every 10 s, `▶{n}s` playhead marker on the active
    cell) plus one row per active layer; block-glyph `▁…█` intensity bars color-flagged
    by primary issue; `visible/1` segments shown, auto-scrolling to keep the playhead
    centered while audio plays.
  - `playhead_provider: Callable[[], tuple[float, bool]] | None` — when set, the widget
    asks the host for `(playhead_s, playing)` instead of reading `#audio-player`, which
    is how the detached terminal follows OmniRip's audio (§6). `playhead_s` is public so
    a headless `run_test` probe can assert sync.
  - Click-to-seek maps widget x → second, y → layer; left/right/home/end scroll.

### 2.3 Workbench integration — `src/harvester/ui/workbench.py`

- `LAYERS` page → `#wb-page-layers` (title, hint, control buttons, status line). Lanes
  are **not** rendered here (docs/01 D19).
- Separation now calls `separate_file(..., save_individual_sources=True)`; after
  success `layer_stem_dir = res.vocals_path.parent` and `_ensure_layers_built()` runs.
- `_ensure_layers_built` / `_async_build_layers` run the analysis in a background thread
  (worker `layer-studio-build`), keep the `LayerTrack` on the screen, and summarize
  "LAYERS READY: N lanes · Ns timeline · N defect seconds flagged".
- `🪟 OPEN LAYER TERMINAL` writes `layer_sidecar.json` (`write_sidecar`) and spawns
  `layer_terminal.py` detached; `SAVE LAYERS` merges the terminal's plan back
  (`read_sidecar`) and commits it; `CLEAR` drops the staged plan.
- Transport: `_transport_timer` (5 Hz) publishes `playhead_s` / `playing` / `duration_s`
  from `#audio-player` and consumes the terminal's `seek_request` / `play_request`
  (`seek()` / `pause()` / `play()`), so the two processes stay in sync both ways (§6).
- Status line reports the lane summary (`kick/snare/hats · bass → sub_bass/bass`).

### 2.4 Stem separator support — `src/harvester/analysis/enhancement/stem_separator.py`

- `separate_file(..., save_individual_sources: bool = False)`.
- `_separate_bs_roformer` / `_separate_neural` / `_separate_ensemble` accept
  `raw_bass_path` / `raw_drums_path` / `raw_other_path` and persist each source via
  `save_audio_numpy`; HDEMUCS variants named `{...}_hdemucs.wav` inside the ensemble
  refinements so both models' sources coexist.

## 3. Test mapping

- `tests/test_layers.py` — envelope units, LR4 per-source assembly + on-disk cache,
  Eco 2-layer fallback, dynamic-lane detection (`test_build_layer_sources_detects_dynamic_lanes`,
  `test_build_layer_track_segments_levels_and_bleed_issue`) → `vocal_bleed` on exactly the
  injected second, and a headless `LayerStudio` mount/render/playhead-sync probe.
- `tests/test_dynamic_layers.py` — family-split detection table (kick/snare absent → drums
  kept whole), complementary partition of a parent lane (children sum == parent, no energy
  lost or doubled), child cache reuse on rebuild, extra neural lanes (`guitar`/`piano`) and
  the `lane_summary` wording.
- `tests/test_layer_sidecar.py` — `LayerTrack` round-trip incl. per-segment arrays and
  `layer_order`, plan round-trip, version mismatch, and the transport channel
  (`test_transport_requests_flow_both_ways`: seek + play requests coexist, `consume_requests`
  clears them once, published state is preserved).
- `tests/test_layer_terminal_app.py` — headless terminal app: loads the sidecar, renders one
  row per detected lane, **follows the main app's published playhead** (the reported bug),
  commits an edit back to the sidecar, and `q` quits cleanly.
- `tests/test_ui_workbench.py` — LAYERS page keeps the control buttons + status, hosts **no**
  `LayerStudio` and no tool palette, and never auto-opens the terminal window.
- `tests/test_stem_separator.py` — `save_individual_sources=True` persists
  `{stem}_{mode}_raw_{source}.wav` and defaults stay off.
- `tests/test_layer_editor.py` — EditPlan toggle/reset semantics, `mute` zeroing vs
  band-cut ops, band-energy assertions for de-mud/de-ess (≥6 dB cut in-band),
  `render_edited_layer` neighbour-byte-identity + crossfade boundary continuity, the full
  `commit_edit_plan` → `build_layer_track` mute flow, missing-layer ValueError, and
  PCM_32/-1 dBFS export ceiling.
- `tests/test_layers.py` widget probe — `EditRequested(1, 'bass', 'mute')` fired by
  `action_edit_mute`, and a `✎` marker renders when an `EditPlan` is attached.

## 4. M2 — per-second surgical editing & FL Studio arrangement (expanded)

Editing backend lives in `src/harvester/analysis/enhancement/layer_editor.py`:

1. **Edit plan** — `EditPlan` keyed by `(layer, segment_idx) -> op`. Non-destructive &
   reversible: `reset` (or re-applying the same op) removes the cell's entry; edits always
   re-read the on-disk blended layer file, so the raw neural cache is never touched.
2. **10 Surgical Cell Ops** —
   - `mute` (`m`, badge `M`): zeroes amplitude in the selected segment.
   - `de_bleed` (`b`, badge `B`): -24 dB notch on the 300–3500 Hz vocal core.
   - `de_ess` (`s`, badge `S`): -14 dB notch on 5.5–8.5 kHz sibilance.
   - `de_mud` (`u`, badge `U`): -10 dB notch on 250–350 Hz boxiness.
   - `drum_punch` (`p`, badge `P`): transient emphasis via RMS-envelope ratio boost ×0.6 (smoothed 2 ms).
   - `de_hum` (`h`, badge `H`): dual 50/60 Hz notch filters plus -18 dB sub-rumble attenuation below 120 Hz.
   - `air_boost` (`a`, badge `A`): +4 dB high-shelf sheen filter from 10–20 kHz for presence and sparkle.
   - `de_click` (`c`, badge `C`): outlier transient derivative spike detector with 5-sample median interpolation.
   - `noise_gate` (`g`, badge `G`): soft downward expander attenuating low-level noise floors (< -38 dBFS).
   - `transient_tame` (`t`, badge `T`): soft hyperbolic-tangent (`tanh`) compression limiter for hot transients (> -3 dBFS).
   - `reset` (`r`): clears staged edit and restores original stem audio.
3. **Splice commit** — `render_edited_layer` replaces only the edited 1 s window; ~20 ms
   equal-power (`cos²`/`sin²`) crossfades at both edges of the window spare neighbours from
   clicks while leaving every other sample byte-identical. `commit_edit_plan` writes the
   rendered layer back to its `{suffix}_layer_{name}.wav` path in place (32-bit PCM).
4. **"SAVE LAYERS"** (workbench button) runs `commit_edit_plan` on a background worker,
   then re-runs `build_layer_track` so the grid reflects the committed edits. "CLEAR EDITS"
   drops the staged plan only (already-committed files stay).
5. **Soft limiter** — every render passes `apply_limiter(ceiling_dbfs=-1 dBFS)` and is
   exported as 32-bit PCM WAV, so rebuilt neighbourhood joins cannot clip.

### Widget / workbench wiring (FL Studio Arrangement & Pipeline Cohesion)

- **FL Studio Arrangement Interface (`src/harvester/ui/layer_studio.py`):**
  - **Track Header Cards (24 chars):** Fixed-width headers displaying track badge (`[VOC]`, `[DRM]`, `[BAS]`, `[INS]`), Mute `[●]` LED indicator, Solo `[S]` button, and stem theme color accents.
  - **3-Row High-Density Braille Waveforms:** Multi-row per-track waveform rendering (`⣀⣄⣆⣇⣧⣷⣿`) displaying acoustic energy contours per cell.
  - **Dual Musical Ruler:** Bars/Beats division (`BAR 1.1`, `BAR 2.1`) synchronized to track BPM, alongside wall-clock time markers (`00:00`, `00:05`, `00:10`).
  - **Operation Badges:** Staged cell edits render distinct badges (`M`, `B`, `S`, `U`, `P`, `H`, `A`, `C`, `G`, `T`) in high-contrast styling.
- **Pipeline Cohesion (`src/harvester/ui/workbench.py`):**
  - **One-Click Bridge (`[ ▤ OPEN IN LAYERS ]`):** On the `STEMS` page, pressing this button immediately opens the `LAYERS` page and (re)builds the multi-lane timeline from the separated stems.
  - **On-Demand Neural Build (`[ ⚡ BUILD STEMS ]`):** On the `LAYERS` toolbar, triggers neural separation if stems have not yet been generated.
  - **Detached Open (`[ 🪟 OPEN LAYER TERMINAL ]`):** writes the sidecar and launches the terminal window that renders the lanes.
- **Mouse-Clickable Tool Palette (`src/harvester/ui/layer_terminal.py`):** Dedicated buttons in the detached terminal for `MUTE`, `BLEED`, `DE-ESS`, `DE-MUD`, `PUNCH`, `DE-HUM`, `AIR+`, `DE-CLICK`, `GATE`, `TAME`, `RESET`, `[ 💾 COMMIT ]`, and `[ RELOAD ]` (the workbench page no longer carries the palette — D19).

## 5. M3 — backend hardening / polish (complete)

All three hardening goals landed (tests: `tests/test_layer_hardening.py`, 6 tests):

1. **Mix reconstruction error budget** — `reconstruct_mix` inverts the layered mix: the sum
   of the four per-layer files equals the LR4 recombination of the summed raw sources exactly
   (linearity of the crossover). `mix_residual_db` / `verify_mix_residual` report the per-second
   reconstruction residual in dBFS against a `-40 dBFS` budget. Verified both pre-edit
   (inversion near round-trip, violating == 0) and across a commit: only the edited seconds
   violate the budget; every unedited second stays byte-identical (residual ≤ budget). The
   workbench commit worker snapshots the pre-commit mix and surfaces a `mix residual ≤ -40 dBFS`
   (or a leak location) in the save status.
2. **De-bleed acceptance fixture** — a loud 1000 Hz vocal-band burst is injected into a
   synthetic 90 Hz bass stem; the analysis flags `vocal_bleed` on exactly that second (and no
   other). After a `de_bleed` commit, the in-band residual leak (measured over the segment
   middle with `segment_band_level`, below the 20 ms crossfade margins) drops ≥ 20 dB — the
   op is -24 dB deep so the drop is ~24 dB with margin.
3. **Long-track stress budget + run-length collapse** — a 600 s @8000 Hz fixture analyzes
   inside `600 s × 100 ms/s` (`ANALYSIS_MS_PER_SECOND_BUDGET`, `LONG_TRACK_SECONDS = 600`).
   `run_length_collapse(track, edit_plan, split_at)` merges adjacent identical cells (same
   level bucket, primary issue, staged op) into `CellRun`s; the widget renders tracks with
   ≥ 600 segments as run-length cells (split at the playhead/selection), so a constant
   long layer costs one styled span instead of thousands of cell lookups.

## 6. M4 — song-driven lanes + detached terminal link (complete)

### 6.1 Dynamic lanes — `src/harvester/analysis/enhancement/dynamic_layers.py`

Four static rows become as many rows as the song actually has parts:

- `FAMILY_SPLITS` defines the known families and their children:
  `drums → kick (low of 130 Hz) / snare (high of 130 → low of 5000) / hats (high of 130 →
  high of 5000)`, `bass → sub_bass (low of 105) / bass (high of 105)`.
- `expand_dynamic_lanes(sources, sample_rate, ...)` re-validates a split with
  `is_present` (active-second ratio ≥ 5 %, mean RMS ≥ -50 dBFS) on the **rendered children**;
  if any child is effectively silent the parent lane survives whole and the family is never
  split. Both splits are **complementary** (`dsp.split_bands` low+high), so children sum to
  the parent sample-for-sample: per-lane edits keep the -40 dBFS reconstruction budget and
  `reconstruct_mix` remains valid for 5–7 lanes exactly as it was for 4.
- Extra lanes are discovered from disk: `_collect_extra_lanes` scans the stem dir for
  `{suffix}_raw_{name}.wav` files beyond the known four and renders each as a first-class row
  (`guitar`, `piano`, …), so the engine is not limited to a fixed lane list. The built-in
  separator still writes only the four neural sources (BS-RoFormer's output tensor is fixed at
  bass/drums/other/vocals), so an extra lane appears when such a raw file exists in the stem
  dir — e.g. from an external splitter or a future 6-source model — and a normal run renders
  4–7 rows.
- Child lane files are cached as `{suffix}_layer_{token}.wav` (`kick`, `snare`, `hats`,
  `sub_bass`, the upper bass half as `bass_upper` so the whole-bass file is never clobbered),
  so rebuilds are cheap and committed edits survive.
- `LayerTrack.active_layers` is data-driven (`LAYER_ORDER` first, then extra lanes in insert
  order); `lane_summary` reports `kick/snare/hats · bass → sub_bass/bass` for the status lines.
- Cutoffs/transition widths: `lane_transition_hz(cutoff) = min(500, max(50, cutoff × 0.6))`
  keeps `fs/2` headroom at 8–16 kHz sample rates (the hardening fixtures run at 8000 Hz).

### 6.2 Detached terminal — `src/harvester/ui/layer_terminal.py`

- Opens in its own Terminal.app window (`osascript`; detached background process elsewhere)
  and renders the full lane grid at the real terminal's width — nothing is constrained to the
  workbench box.
- `LayerTerminalApp` polls the sidecar every 0.2 s: transport (`playhead_s` / `playing` /
  `duration_s`) → `LayerStudio.playhead_provider`, so the grid **moves with OmniRip's
  playback**; sidecar mtime changes → lanes/plan reload (edits made in the main app appear live).
- Controls (parity with the workbench palette): click a cell to select the lane/second
  (a ruler/second click also requests a seek), `←/→/home/end` scroll the grid,
  `m/b/s/u/p/h/a/c/g/t` apply the cell ops, `r` resets the cell, `space` requests
  play/pause from the main app, the palette buttons drive the same ops, `💾 COMMIT` writes
  the staged plan into the sidecar, `q`/`escape` quit. Requests are written to
  `transport.json` and **re-issued** on every poll until the main app publishes a state that
  confirms them (position within one segment, `playing` matching the request), so a poll race
  cannot swallow a seek.
- Commit (`💾 COMMIT`) only writes the sidecar; the lane files are rewritten when the main app
  applies the plan on its next `SAVE LAYERS` / export.

### 6.3 Transport channel — `src/harvester/ipc/layer_sidecar.py`

- Sidecar file `layer_sidecar.json`: `LayerTrack` + plan (the model channel, unchanged apart
  from `layer_order`).
- Transport file `layer_sidecar.transport.json`: `TransportState(playhead_s, playing,
  duration_s, seek_request, play_request, written_at)`. Both writers use `os.replace` (atomic),
  so a reader never sees a half-written JSON; requests are consumed once (`consume_requests`)
  and are field-independent (`request_seek` / `request_play_state` only touch their own field).
- Ownership: the **main app** owns audio and therefore owns `playhead_s` / `playing`; the
  terminal owns selection and the staged plan. Neither writes the other's fields.
### 6.4 Lane provenance, presets & extra sources (docs/13)

- Every lane row carries provenance from `analysis/enhancement/lane_plan.py`:
  `separator` (model stem), `dsp-split` (complementary crossover child), `extra-source`
  (guitar/piano from the 6-source pass), `mix` (eco bus), and the two **no-audio-row**
  origins `credit-only` (documented in MusicBrainz, unrenderable) and `tag-only`.
  Confidence describes how the row was made (high / medium / low / none), and the plan
  summary (`2 separator · 5 DSP split · 1 credits only · 2 singers`) rides in the status
  line of both the workbench (`#wb-lane-plan`) and the detached terminal sub-title.
- Which stages run is the **processing preset** (`[processing] preset`): `fetch_only`
  (acquire + tag, no lanes), `standard` (4-source + lanes), `neural_full` (adds guitar/piano
  extras, MusicBrainz credits and tagging). The separator's engine fallback stays separate
  and is always reported — `eco` means the 2-layer mid/side fallback (D14), never a
  "fast mode", and a run that lands there raises a warning.
- `🏷 CREDITS` fingerprints the loaded track (AcoustID → recording MBID) and pulls the
  documented instrument/vocal inventory, which annotates lanes and adds the singer count
  without re-running the per-second scan (`LayerTrack.replan`).
- The sidecar is **schema v2**: it carries `lane_plan`, `singer_count`, `credit_instruments`
  and `tag_labels` alongside `layer_order`, so both windows label rows identically.
