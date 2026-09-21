# 13 — Lane Expansion: Presets, Provenance, Credits & 6-Source Extras

Status: **implemented (M11.5)**. Decisions D21–D24 in
[`docs/01-requirements.md`](01-requirements.md) §5 are the normative summary; this document
holds the detail, the budgets and the acceptance criteria.

## 1. What this milestone answers

Four questions, each with a mechanism rather than a guess:

| Question | Mechanism | Authoritative? |
| --- | --- | --- |
| Which stages run for this track? | Processing presets (`fetch_only` / `standard` / `neural_full`) | user choice |
| Why does this lane exist? | `LanePlan` provenance (origin + confidence + note) | derived from the detector |
| Which instruments/voices are on the recording? | MusicBrainz credits (instruments, vocals, singer count) | documented data |
| What is audible that no stem renders? | CLAP tagging (12 label prompts, `tags.json`) | advisory model output |
| Can we show more than four rows? | 6-source extras (HTDemucs-6s → guitar/piano) + dynamic family splits | model output |

Explicitly out of scope here: hosted separators (MVSEP) and singer *diarization* (pyannote) —
both blocked on credentials, see §8 for exactly what they would need.

## 2. Processing presets (D21)

Two axes, deliberately separate:

```
sourcing    slskd.acquisition_mode = best_available | lossless_preferred | fast_fallback | highest_quality_mp3
processing  [processing] preset    = fetch_only | standard | neural_full
```

`src/harvester/processing.py` is pure data (no numpy, no torch, no I/O) so the UI, the
config layer and the tests can all share one definition:

| preset | separation | extras (guitar/piano) | credits | tags | restoration | ≈ peak RAM |
| --- | --- | --- | --- | --- | --- | --- |
| `fetch_only` | — | — | — | — | — | 0.2 GB |
| `standard` (default) | 4-source | — | ✓ | — | — | 1.7 GB |
| `neural_full` | 4-source | ✓ | ✓ | ✓ | ✓ | 2.5 GB (7 GB with NVSR) |

Rules:

1. **A preset decides which stages run; the engine chain decides how they run.** The
   separator may still fall back (neural → hdemucs → eco) — that is resilience, not a mode
   change — and every degraded run is reported (`engine_note`, warning toast), never silent.
2. **`eco` keeps its spec'd meaning** (D14: a 2-layer mid/side fallback). It is *not* the
   "fast" preset; `fetch_only` is. Naming a no-separation mode "eco" would invert D14.
3. `fetch_only` + `⚡ BUILD STEMS` is an explicit per-track opt-in and switches the session
   to `standard`, announced in `#wb-layer-status`.

Config (`config.example.toml`):

```toml
[processing]
preset = "standard"      # fetch_only | standard | neural_full
use_credits = true       # allow the MusicBrainz credits lookup
```

An unknown preset is a `ConfigError` at load time (never a silent default in the middle of
a run); `normalize_preset()` is only for tolerant UI/CLI spellings.

## 3. Lane provenance (D22)

`src/harvester/analysis/enhancement/lane_plan.py` — torch-free, dependency-free.

Origins and their meaning:

| origin | confidence | means | has an audio row |
| --- | --- | --- | --- |
| `separator` | high | a stem a separation model produced | yes |
| `dsp-split` | medium | complementary crossover split of a separator stem | yes |
| `extra-source` | low | extra model lane (guitar/piano from the 6-source pass) | yes |
| `mix` | high | whole-track bus of the eco fallback | yes |
| `credit-only` | none | documented in MusicBrainz, no separator renders it | **no** |
| `tag-only` | low | audible to the tagger, not produced as a stem | **no** |

Confidence describes **how the row was made**, not how good the song is: a `dsp-split` is
exact but narrower than its parent; a 6-source lane is a low-SDR model output (public
MusicBrainz/MUSDB-style benchmarks put 6-source guitar around 2.6 dB SDR); a `credit-only`
row has no audio at all.

Wiring:

- `build_layer_sources_with_report()` returns `(lanes, LaneReport)`; `build_layer_sources()`
  remains the lanes-only wrapper (backwards compatible).
- `build_layer_track(..., credit_instruments=, singer_count=, tag_labels=)` builds the plan
  and stores it on the track (`lane_plan`, `lane_report`).
- `LayerTrack.replan(...)` recomputes provenance when credits arrive later — **no
  re-segmentation**, so the expensive per-second scan is never repeated for a metadata event.
- The workbench renders it in `#wb-lane-plan` (`LANE PLAN: …` + one `describe()` line per
  lane, capped at 12 with a `+N more` tail); the detached terminal shows the plan summary in
  its sub-title.

## 4. MusicBrainz credits (D23)

`CoverArtService.fetch_recording_credits(recording_id) -> RecordingCredits | None`

- Endpoint: `https://musicbrainz.org/ws/2/recording/<mbid>?inc=artist-rels&fmt=json` with a
  descriptive `User-Agent` (`OmniRip/0.1 ( … )`) — required by MusicBrainz.
- Parsing: `instrument` → instruments, `vocal` → vocals, `producer` → producers,
  `performer`/`performance` → performers. The instrument/vocal *type* lives in `attributes`
  (`["double bass"]`, `["lead vocals"]`), falling back to the relation type when empty.
- `singer_count` = distinct credited vocalists (or `None` when undocumented).
- `lane_credits` = instruments + vocals: the credits allowed to annotate a lane. Producers
  are not a lane, and unlabelled performance credits would add noise rows.
- Cache: `cache/credits/<mbid>.json` (raw payload, atomic replace), so a repeat lookup is
  offline. Live example (`Headlock`, Imogen Heap): `double bass — Mich Gerber`,
  `lead vocals — Imogen Heap`, `vocal — Richie Mills` → **2 singers**.
- Failure policy: missing id / 404 / 500 / non-JSON → `None`, and the UI says "no credits
  documented"; a job never fails because metadata is thin.

UI: `🏷 CREDITS` on the `LAYERS` page fingerprints the loaded track (AcoustID → MBID →
credits) in a worker, prints the summary into `#wb-layer-status` and replans the lanes in
place.

## 5. 6-source extras (D24)

`StemSeparator.separate_extra_lanes(input_path, output_dir, mode=…, progress_callback=…)`

- Model: `htdemucs_6s` → `adefossez/HTDemucs-6s`, file `5c90dfd2.safetensors` (54.9 MB),
  loaded with `demucs.hf.load_safetensors_model` from the OmniRip model cache (single
  download, `ModelManager`-managed).
- Output: `{stem}_{mode}_raw_guitar.wav` and `{stem}_{mode}_raw_piano.wav` — the **same mode
  suffix** as the 4-source run, so `dynamic_layers._collect_extra_lanes` (which globs
  `{suffix}_raw_<name>.wav`) turns them into lanes with zero lane-code changes.
- Order: 4-source separation → extras → lane build. The extras model is loaded alone and
  unloaded (`del`, `gc.collect()`, `empty_cache`) before anything else runs, which keeps the
  measured 1.7 GB separation envelope intact (extras add ~55 MB of weights).
- Gates: extras pass the same presence gate as every other lane (≥5 % active seconds above
  −45 dBFS and mean RMS ≥ −50 dBFS), so a bleed-only guitar stem produces no row.
- Degradation: no `demucs`, no model, failed download, or failed inference → `{}` and a
  status line ("Extra lanes unavailable … 4-source lanes only"). Never an exception.
- Quality honesty: 6-source SDR is lower than 4-source (vocals 8.66 vs 8.53, bass 9.11 vs
  9.78, drums 9.54 vs 10.01 in a public 2026 MUSDB18-HQ benchmark). Extra lanes are labelled
  `extra-source` / low confidence so nobody mistakes them for first-class stems.
- Measured on this machine (Apple M2, 16 GB, MPS): weights **54,885,744 B (54.9 MB)**, extras
  pass **6.9–7.4 s per 20 s excerpt** (≈0.35× realtime) on top of the 4-source run, and the
  whole `neural_full` chain peaked at **2380–2662 MB RSS** — inside the documented ~2.5 GB.

### 5.1 Presence gate behaviour on real audio

The gate is measured over the **whole track**, which matters when reading probe output:

| stem (real runs) | per-second profile | verdict |
| --- | --- | --- |
| guitar, 20 s mid-song excerpt (cover with guitar) | −18 dBFS sustained | lane created, `[6-source model, low]` |
| piano, same excerpt (no piano in the song) | −78 dBFS | rejected — no fake row |
| guitar, 20 s excerpt with 8 s of leading silence | −25…−34 dBFS after 8 s silence, mean −50.0 dBFS | rejected (mean sits exactly on the boundary) |
| guitar / piano, *Headlock* (no guitar part) | −47.8 / −54.7 dBFS bleed | rejected |

A 20 s excerpt that starts with silence can therefore drop a lane that the full track keeps;
that is the gate working as specified (≥5 % active seconds **and** mean RMS ≥ −50 dBFS), not
a bug — separators emit bleed at −45…−55 dBFS for parts that are not in the mix.

## 5b. CLAP tagging (D25)

`src/harvester/analysis/enhancement/tags.py` — the last piece of "what is in this song":
content that is audible but that no separator renders as a stem.

- **Model:** `laion/clap-htsat-unfused` (CLAP; 614 MB; registry key `clap`; snapshot cached
  under `<model cache>/clap-htsat-unfused/`). Loaded alone, `eval()`, 48 kHz mono input.
- **Device:** CPU. CLAP's BatchNorm raises `Placeholder storage has not been allocated on MPS
  device!` under Apple MPS (measured on this machine), and CPU is fast enough that a workaround
  is not worth the risk: **24 windows ≈ 4.9 s** for a full 3.5 min track. `ClapTagger(device=…)`
  still accepts another device and retries once on CPU if it fails.
- **Windows:** up to `TAG_MAX_WINDOWS = 24` evenly spaced 5 s windows (`window_bounds()` is a
  pure function so the cost is testable without a model). A 3.5 min track therefore costs 24
  forwards, not 42 — the cap is what keeps a full-length tag pass interactive.
- **Scoring:** 12 label prompts (`drums, bass, guitar, piano, synth, strings, brass, flute,
  lead vocals, backing vocals, male vocals, female vocals`). Per window the model's
  similarity logits are turned into a **softmax share across the labels**, then averaged over
  windows. This is deliberately *not* a sigmoid "probability": CLAP similarities are not
  calibrated, and an unopinionated label would sit at 0.5 and pass any sane threshold. With
  shares, an unknown track spreads the mass evenly (1/12 ≈ 8 %) and reports nothing, while a
  clearly present instrument takes most of the mass.
- **Selection:** `labels_for_threshold(scores, threshold, limit)` keeps labels at or above
  `[processing] tag_threshold` (default 0.15 ≈ twice the even share), best first, capped at
  `TAG_MAX_LABELS = 8`.
- **Storage:** `tags.json` beside the stems (schema v1, atomic replace) with the labels, the
  full score table, the window count and the threshold — so a surprising tag can always be
  explained after the fact.
- **Wiring:** `neural_full` runs `ClapTagger.tag_and_store()` right after the extras pass; the
  lane build reads `tags.json` and passes the labels into `plan_lanes`. A tag that maps to a
  rendered lane (`guitar` → guitar row, via the same `lane_for_credit` keyword table used for
  credits) **annotates** that row (`· CLAP tag: guitar`); anything else becomes a
  `tag-only` row with no audio.
- **Failure policy:** no `transformers`, no cached model, an unreadable file, an unsupported
  MPS op (one retry on CPU) or any scoring error → `None`/no tags and a status line. The lane
  grid is never blocked by the tagger, and tags never touch the spectral verdict, the mix or
  the file metadata.

## 6. Engine reporting (the anti-confusion rule)

`engine_note(engine)` renders the engine that actually ran:

| engine | note |
| --- | --- |
| `bs_roformer` / `neural` | BS-RoFormer (neural) |
| `ensemble` | BS-RoFormer + HDEMUCS (ensemble) |
| `hdemucs` | HDEMUCS (neural) |
| `eco` | eco DSP fallback — mid/side cannot split drums/bass/other |
| `bs_roformer+htdemucs_6s` | BS-RoFormer + htdemucs_6s extras (neural) |

`degraded(engine)` is true only for `eco`; the workbench raises a warning toast in that case
and the status line carries the note. A user who picked `neural_full` and got the eco
fallback must see it.

## 7. Acceptance criteria

1. `[processing] preset` round-trips from TOML; an unknown value is a `ConfigError`.
2. `fetch_only` runs no separation stage; `⚡ BUILD STEMS` under it switches to `standard`
   and reports the switch.
3. Every rendered lane has an origin; no lane is ever shown without provenance.
4. `credit-only` / `tag-only` entries are listed but never produce an audio row
   (`rendered is False`, `missing` reports them).
5. A silent (bleed-only) extra stem creates no lane.
6. Credits round-trip from the cache without network, and 404/500 degrade to `None`.
7. Sidecar schema v2 carries the plan; a track without a plan loads as an empty plan (not an
   error); a v1/foreign version still raises `ValueError`.
8. The detached terminal shows the same plan summary as the workbench (same file, same plan).
9. `window_bounds()` covers a track with ≤24 evenly spaced windows (uniform hop, no overlap)
   and degrades to a single window for short input.
10. Tag selection is deterministic and self-limiting: an even score spread reports **no**
    labels; only labels at or above `[processing] tag_threshold` are reported, capped at
    `TAG_MAX_LABELS`, best first.
11. A tag that maps to a rendered lane annotates that row instead of adding a duplicate row;
    unrenderable tags become `tag-only` rows with no audio.
12. Every tagging failure mode (no `transformers`, no cached model, unreadable file, unsupported
    device op) returns "no tags" and leaves the lane grid untouched.

Test map: `tests/test_processing.py`, `tests/test_lane_plan.py`, `tests/test_musicbrainz.py`,
`tests/test_six_source_lanes.py`, `tests/test_layer_sidecar.py`, `tests/test_ui_workbench.py`,
`tests/test_model_manager.py`, `tests/test_tags.py`.

### 7.1 Measured end-to-end evidence (real weights, real songs, Apple M2)

| run | result |
| --- | --- |
| `Headlock` (Imogen Heap), 20 s excerpt, `ensemble` | 4-source in 37.9 s, engine `BS-RoFormer + HDEMUCS (ensemble)`; extras 22.2 s (first run, incl. model load); lanes `vocals/drums/bass/other`; guitar + piano stems produced but correctly **rejected** by the gate |
| cover with guitar, 20 s mid-song excerpt | **8 lanes**: `vocals, kick, snare, hats, sub_bass, bass, other, guitar`; plan `2 separator · 5 DSP split · 1 6-source model`; `GUITAR [6-source model, low]`; sidecar v2 round trip preserved every lane + origin (32,816 B) |
| live credits chain (full file → fpcalc → AcoustID → MBID → MusicBrainz) | `Headlock / Imogen Heap / d871b5ab-… / 0.984`; credits `double bass — Mich Gerber`, `lead vocals — Imogen Heap`, `vocal — Richie Mills`, `producer — Imogen Heap`; **2 singers**; plan `4 separator · 1 credits only · 2 singers`; rows annotated (`VOCALS … lead vocals — Imogen Heap`, `BASS … credit: double bass — Mich Gerber`) and one `VOCAL [credits only, none]` row listed **without** audio |
| CLAP tagging (real weights, full-length tracks, CPU) | *Headlock*: 24 windows × 5 s in **4.9 s** → `lead vocals 0.66` (next best 0.07), i.e. the tagger agrees the track is vocal-led; cover of the same song: `lead vocals 0.44`, `brass 0.19`, `guitar 0.11`; `tags.json` written and read back identically both times. White-noise sanity probe → `synth 0.87`, nothing else reported |

Reproduce with the scratch probes (`lane_expansion_e2e.py`, `lane_expansion_e2e2.py`,
`credits_chain_probe.py`, `clap_e2e.py`).

## 8. Deliberately not built (and why)

| Idea | Status | Reason |
| --- | --- | --- |
| CLAP instrument tagging (`laion/clap-htsat-unfused`) | **shipped** (D25) | See §5b: 614 MB, `neural_full` only, advisory rows, `tags.json`. |
| MVSEP hosted (lead/back vocals, 53-stem detector) | **deferred — blocked on credentials** | Needs an MVSEP account and API key plus a per-track upload; there is no key on this machine, so the integration cannot be verified end to end. Everything else it would feed (provenance rows, lead/back-vocal lanes) already exists, so it is a transport problem, not a design one. |
| pyannote diarization (singer counting from audio) | **deferred — blocked on credentials + dependency** | `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` are gated on the Hub: a HF token is required (none on this machine) and `pyannote.audio` is not installed (Python 3.14 wheels unverified). Diarization on *singing* also degrades with doubles and heavy processing. The credit-based singer count ships first because it is free, documented and deterministic. |
| Audio-LLM / BYOK inference in the pipeline | **rejected** | LLMs cannot separate sources, and they must never touch the spectral verdict (docs/01) or metadata authority (AcoustID/MusicBrainz). A spectrogram-image round trip is possible but advisory-only; it adds a network dependency and an unverifiable failure mode for zero lane capability. |
| Rewriting `eco` into "no separation" | **rejected** | Inverts a spec'd decision (D14). `fetch_only` covers the intent without breaking the fallback contract. |

## 9. Open questions

- Where should `neural_full` extras land when the 4-source run is a *warm cache* hit? Today
  the extras pass runs only when separation actually runs; a cached 4-source dir with no
  extras stays 4-source until `⚡ BUILD STEMS` is pressed again (which re-runs the extras and
  tag passes against the cache).
- `tags.json` is per stem directory, so re-tagging after a threshold change means deleting the
  file (or switching the preset and pressing `⚡ BUILD STEMS`). A `🏷 TAGS` button mirroring
  `🏷 CREDITS` would make that explicit — not built yet because `neural_full` already covers
  the normal path.
- The 12-label prompt set is deliberately coarse. Adding finer labels (sax vs brass, cello vs
  strings, "spoken word") is a data change in `tags.py`, but each addition dilutes the softmax
  share, so `tag_threshold` should be re-tuned with real tracks when the set grows.
- MVSEP (hosted lead/back-vocal separation) and pyannote (audio diarization) stay out until
  credentials exist; both would slot into the same provenance model without a redesign (§8).
