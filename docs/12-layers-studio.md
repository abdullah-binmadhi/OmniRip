# 12 — Layer Studio (per-second layered stem timeline)

Photoshop/Lightroom-style **per-second** stem editing for the Neural Enhancement
Workbench: one row per separated source (vocals / bass / drums / other), one column
per **fixed 1-second** segment, playhead-synced to the audio player, click-to-seek,
per-second defect flags, and (M2) surgical per-second edits committed back to the stems.

Delivered in three milestone phases:

| Phase | Name | Status |
|-------|------|--------|
| M1 | Visualize + inspect | ✅ Complete — raw 4-stem persistence, segment analysis engine, LAYERS tab with grid + playhead sync + click-to-seek |
| M2 | Per-second editing | ✅ Complete — cell actions (mute / de-bleed / de-ess / de-mud / drum-punch), edit plan, ~20 ms crossfade splice commit, "SAVE LAYERS" export |
| M3 | Backend hardening / polish | ✅ Complete — mix reconstruction residual budget (-40 dBFS) verified pre-edit and across commits, ≥ 20 dB de-bleed acceptance fixture, 600 s per-second analysis budget with run-length cell collapse |

## 1. Decisions (normative — see docs/01 D14)

- **Time grid:** fixed `SEGMENT_SIZE_S = 1.0` seconds per column (no zoom in M1).
- **Layer set:** vocals, bass, drums, other rows; `mix` used only as the Eco fallback row.
- **Home:** Layer Studio lives in the workbench's `LAYERS` tab (`#wb-page-layers`),
  seeded from the separated track's stem directory.
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

`LayerStudio` (Textual `Widget`):

- Emits `SeekRequested(seconds, layer)` and `SelectionChanged(segment, layer)` messages.
- Renders a ruler row (timestamp every 10 s, `▶{n}s` playhead marker on the active
  cell) plus one row per active layer; block-glyph `▁…█` intensity bars color-flagged
  by primary issue; `visible/1` segments shown, auto-scrolling to keep the playhead
  centered while audio plays (0.25 s sync timer reads `#audio-player` `elapsed_s`).
- Click-to-seek maps widget x → second, y → layer; left/right/home/end scroll.

### 2.3 Workbench integration — `src/harvester/ui/workbench.py`

- `LAYERS` page button → `#wb-page-layers` (title, widget, status line).
- Separation now calls `separate_file(..., save_individual_sources=True)`; after
  success `layer_stem_dir = res.vocals_path.parent` and `_ensure_layers_built()` runs.
- `_ensure_layers_built` / `_async_build_layers` run the analysis in a background thread
  (worker `layer-studio-build`), hand the `LayerTrack` to the widget, and summarize
  "LAYERS READY: N layers · Ns timeline · N defect seconds flagged".
- Seek → `AudioPlayerWidget.seek(seconds)`; selection → status line with per-layer % + issues.

### 2.4 Stem separator support — `src/harvester/analysis/enhancement/stem_separator.py`

- `separate_file(..., save_individual_sources: bool = False)`.
- `_separate_bs_roformer` / `_separate_neural` / `_separate_ensemble` accept
  `raw_bass_path` / `raw_drums_path` / `raw_other_path` and persist each source via
  `save_audio_numpy`; HDEMUCS variants named `{...}_hdemucs.wav` inside the ensemble
  refinements so both models' sources coexist.

## 3. Test mapping

- `tests/test_layers.py` — envelope units, LR4 per-source assembly + on-disk cache,
  Eco 2-layer fallback, full `build_layer_track` with injected vocal-band burst on the
  bass row → `vocal_bleed` on exactly that second, and a headless `LayerStudio`
  mount/render/playhead-sync probe.
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
  - **One-Click Bridge (`[ ▤ OPEN IN LAYERS ]`):** On the `STEMS` page, pressing this button immediately opens the `LAYERS` page and populates the multi-track timeline from separated stems.
  - **On-Demand Neural Build (`[ ⚡ BUILD STEMS ]`):** On the `LAYERS` toolbar, triggers neural separation if stems have not yet been generated.
  - **Mouse-Clickable Tool Palette:** Dedicated buttons on the Layers toolbar for `MUTE`, `BLEED`, `DE-ESS`, `DE-MUD`, `PUNCH`, `DE-HUM`, `AIR+`, `DE-CLICK`, `GATE`, `TAME`, `RESET`, `[ 💾 SAVE LAYERS ]`, and `[ CLEAR ]`.

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