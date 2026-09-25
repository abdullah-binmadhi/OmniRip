# 13 — Lane Expansion: Presets, Provenance, Credits & 6-Source Extras

> **Superseded by docs/01 D35 (guided Repair, M18).** The lane grid, provenance rows and per-second editing are removed from the app; credits, CLAP tags, speaker measurement and hosted MVSEP survive inside Track Info and the Repair engine. This document is kept as the historical detail for D21–D27.


Status: **implemented (M11.5 + M11.6)**. Decisions D21–D27 in
[`docs/01-requirements.md`](01-requirements.md) §5 are the normative summary; this document
holds the detail, the budgets and the acceptance criteria.

## 1. What this milestone answers

Six questions, each with a mechanism rather than a guess:

| Question | Mechanism | Authoritative? |
| --- | --- | --- |
| Which stages run for this track? | Processing presets (`fetch_only` / `standard` / `neural_full`) | user choice |
| Why does this lane exist? | `LanePlan` provenance (origin + confidence + note) | derived from the detector |
| Which instruments/voices are on the recording? | MusicBrainz credits (instruments, vocals, singer count) | documented data |
| What is audible that no stem renders? | CLAP tagging (12 label prompts, `tags.json`) | advisory model output |
| Can we show more than four rows? | 6-source extras (HTDemucs-6s → guitar/piano) + dynamic family splits | model output |
| What if the local models are not enough? | hosted separation (MVSEP), **opt-in per track** | model output, off-machine |
| How many voices are actually in the mix? | pyannote diarization, **advisory only** | model output, never overrides credits |

Two of these are deliberately *not* part of any preset:

- **Hosted separation (MVSEP, D26)** is the only path that sends audio off this machine. Nothing
  hosted runs unless the user presses `☁ HOSTED SEPARATE` on the LAYERS page for a specific
  track, and the preset axis never touches the network.
- **Diarization (pyannote, D27)** measures how many voices the audio contains and reports the
  number **next to** the MusicBrainz credit count. It never overwrites it: measured speaker
  counts are demonstrably noisy (§7.1), while credits are documented data.

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
| `neural_full` | 4-source | ✓ | ✓ | ✓ | ✓ | 2.5 GB (+3.2 GB with the FlashSR pipeline) |

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

## 5c. Hosted separation (D26)

`src/harvester/services/mvsep.py` — the opt-in cloud engine. It is **not** a preset and **not**
part of any stage chain: the only entry point is the `☁ HOSTED SEPARATE` button on the LAYERS
page, per track.

| aspect | behaviour |
| --- | --- |
| trigger | `☁ HOSTED SEPARATE` (workbench LAYERS) — nothing hosted runs from a preset, a job, or startup |
| key | `MVSEP_API_KEY` from the environment (`.env` fallback, NFR-6); missing key → a status line, no upload |
| request | `POST {base}/separation/create` (multipart: `api_token`, `audiofile`, `sep_type`, `output_format`) → `data.hash` |
| poll | `GET {base}/separation/get?hash=…` every 4 s until the **top-level** `status` is `done`/`error` (`waiting` → `processing` → `done`), budget `max_wait_s` (default 1800 s — the queue took ~2 min for a 20 s clip) |
| download | each returned file's `url` → `{input_stem}_{mode}_hosted_raw_{lane_key}.wav` in the same stem dir the local run uses |
| `sep_type` | the **`render_id`** field of `GET /api/app/algorithms`, *not* its `id` (using `id` silently runs a different model). `SEP_TYPES` maps friendly names → ids (`karaoke_lead_back` 49, `mega_53_stem` 126, …); `[processing] hosted_sep_type` picks one |
| excerpt | `[processing] hosted_max_seconds` (0 = whole track) trims the upload; credits are the user's money |
| lane naming | the filename token *is* the lane key: `vocals-lead` → `lead_vocals`, `vocals-back` → `back_vocals`, `instrum-only`/`back-instrum` are sums and are downloaded but never become rows, any other token becomes its own lane — so a 4-, 21- or 53-stem model needs **no per-model table** |
| provenance | `hosted` origin, confidence `high`, note "hosted MVSEP separation"; the row renders audio like any local lane |
| failure policy | HTTP error / queue timeout / `error` status → a status line with the server's message, no stems, no crash. **The API key is never logged and is scrubbed from every message** (a hostile server that echoes the token back in an error body cannot leak it into the log) |

## 5d. Measured speakers (D27)

`src/harvester/services/diarization.py` — pyannote, optional (`uv pip install -e '.[diarize]'`).

- **Advisory, always.** `LanePlan.measured_speakers` rides *next to* `singer_count`: the plan
  summary reads `2 singers · 3 speakers measured`, and the workbench says so explicitly when the
  two disagree ("MusicBrainz credits say 2 — credits stay authoritative"). Diarization never
  rewrites credits, never creates or removes a lane, and never gates a stage.
- **Device:** CPU. Apple MPS fails on the pooling layer (`invalid low watermark ratio 1.4`).
- **Pipeline:** `pyannote/speaker-diarization-community-1` when the token may read it; otherwise
  the pipeline is assembled from components that are openly readable
  (`segmentation-3.0` + `wespeaker-voxceleb-resnet34-LM` + agglomerative clustering) and
  `get_plda` is patched out, because the PLDA step lives in a gated repo. Either way the
  feature works with the token the user has.
- **Input:** the separated vocals stem when the track has one, else the source file;
  `[processing] diarize_max_seconds` (0 = whole track) caps the measurement.
- **Accuracy is the caveat, not the plumbing:** on the *Headlock* vocals stem the model reports
  **1** speaker while the credits document 2, and a controlled two-singer splice reports **3**
  at every threshold from 0.70 to 0.90. That is why the number is advisory (§7.1).

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
13. No preset, job or startup path ever calls MVSEP: the hosted client is reachable only from
    `☁ HOSTED SEPARATE`, and a missing `MVSEP_API_KEY` produces a status line instead of an
    upload.
14. A hosted run writes `{suffix}_hosted_raw_{lane_key}.wav` per returned stem and rebuilds the
    grid so those files appear as `hosted` rows; sum stems (`instrum-only`, `back-instrum`) are
    skipped, and an unknown token still becomes a lane.
15. No MVSEP failure (HTTP error, queue timeout, `error` status, hostile error body) can put the
    API key into a message or a log line.
16. `measured_speakers` is recorded beside `singer_count` and changes neither the credits nor the
    lane set; with no credits the plan still shows the measured count as advisory, and the
    workbench names the credit count as authoritative when the two differ.

Test map: `tests/test_processing.py`, `tests/test_lane_plan.py`, `tests/test_musicbrainz.py`,
`tests/test_six_source_lanes.py`, `tests/test_layer_sidecar.py`, `tests/test_ui_workbench.py`,
`tests/test_model_manager.py`, `tests/test_tags.py`, `tests/test_mvsep.py`,
`tests/test_diarization.py`, `tests/test_config.py`, `tests/test_dynamic_layers.py`.

### 7.1 Measured end-to-end evidence (real weights, real songs, Apple M2)

| run | result |
| --- | --- |
| `Headlock` (Imogen Heap), 20 s excerpt, `ensemble` | 4-source in 37.9 s, engine `BS-RoFormer + HDEMUCS (ensemble)`; extras 22.2 s (first run, incl. model load); lanes `vocals/drums/bass/other`; guitar + piano stems produced but correctly **rejected** by the gate |
| cover with guitar, 20 s mid-song excerpt | **8 lanes**: `vocals, kick, snare, hats, sub_bass, bass, other, guitar`; plan `2 separator · 5 DSP split · 1 6-source model`; `GUITAR [6-source model, low]`; sidecar v2 round trip preserved every lane + origin (32,816 B) |
| live credits chain (full file → fpcalc → AcoustID → MBID → MusicBrainz) | `Headlock / Imogen Heap / d871b5ab-… / 0.984`; credits `double bass — Mich Gerber`, `lead vocals — Imogen Heap`, `vocal — Richie Mills`, `producer — Imogen Heap`; **2 singers**; plan `4 separator · 1 credits only · 2 singers`; rows annotated (`VOCALS … lead vocals — Imogen Heap`, `BASS … credit: double bass — Mich Gerber`) and one `VOCAL [credits only, none]` row listed **without** audio |
| CLAP tagging (real weights, full-length tracks, CPU) | *Headlock*: 24 windows × 5 s in **4.9 s** → `lead vocals 0.66` (next best 0.07), i.e. the tagger agrees the track is vocal-led; cover of the same song: `lead vocals 0.44`, `brass 0.19`, `guitar 0.11`; `tags.json` written and read back identically both times. White-noise sanity probe → `synth 0.87`, nothing else reported |
| hosted separation (real key, real API, `karaoke_lead_back`) | the shipped client uploaded a 20 s excerpt, polled the queue (`waiting` → `processing` → `done`, ~2 min wait, cost coefficient 1) and filed the returned stems as `excerpt20s_eco_hosted_raw_lead_vocals.wav` / `…_back_vocals.wav` (44.1 kHz stereo, 20.000 s, ffprobe-verified) in **222 s** total. Lane discovery picked them up with no lane-code changes: `lead_vocals` became a `hosted (MVSEP)` / high-confidence row, while the back-vocal stem was correctly **dropped by the presence gate** (this excerpt has no audible backing vocal — the gate working, not a bug). Sum stems (`instrum-only`, `back-instrum`) were downloaded-then-skipped. Two earlier raw jobs (`sep_type=49` → 4 WAVs, `sep_type=126` → 23 FLACs) were ffprobe-verified |
| speaker measurement (real pipeline, real vocals stem) | *Headlock* vocals stem, first 60 s: `speaker-diarization-community-1` on CPU in **34.9 s** (51.8 s wall incl. model load), 6 turns / 29.4 s speech → **1 speaker measured** vs **2 credited**; the plan reads `2 separator · 1 DSP split · 2 singers · 1 speakers measured`, i.e. credits stayed authoritative. Controlled two-singer splice → 3 speakers at 0.70/0.80/0.90 alike |

Reproduce with the scratch probes (`lane_expansion_e2e.py`, `lane_expansion_e2e2.py`,
`credits_chain_probe.py`, `clap_e2e.py`, `hosted_lane_e2e.py`, `speakers_e2e.py`).

## 8. Deliberately not built (and why)

| Idea | Status | Reason |
| --- | --- | --- |
| CLAP instrument tagging (`laion/clap-htsat-unfused`) | **shipped** (D25) | See §5b: 614 MB, `neural_full` only, advisory rows, `tags.json`. |
| MVSEP hosted (lead/back vocals, 53-stem detector) | **shipped** (D26, §5c) | The key authenticates (`GET /api/app/user` → the account, `premium_enabled=1`) and the app now has the transport: `harvester/services/mvsep.py` uploads, polls (`sep_type` is the `render_id` of `GET /api/app/algorithms`, **not** its `id`; the result's `status` is top-level), downloads and files every returned stem as `{suffix}_hosted_raw_{lane_key}.wav`. It is deliberately **not** a preset and runs only from `☁ HOSTED SEPARATE`, because it is the only path that sends audio off the machine. Sum stems are skipped; unknown tokens still become lanes, so a 4-, 21- or 53-stem model needs no per-model table. |
| pyannote diarization (singer counting from audio) | **shipped, advisory only** (D27, §5d) | `pyannote.audio 4.0.7` is the optional `diarize` extra; the token now reads both pipeline repos (terms accepted) so `speaker-diarization-community-1` loads directly, with a component-built fallback (`segmentation-3.0` + wespeaker + agglomerative clustering, `get_plda` patched out) for a token that cannot. `👥 SPEAKERS` measures the vocals stem and records `measured_speakers` **beside** `singer_count`. Measured: 60 s in 34.9 s on CPU; Apple MPS is unusable (`invalid low watermark ratio 1.4`). **Accuracy is the caveat:** *Headlock* → 1 measured vs 2 credited, and a controlled two-singer splice → 3 speakers at thresholds 0.70/0.80/0.90 alike. So a measured count never overwrites the credit count. |
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
- MVSEP (hosted lead/back-vocal separation) and pyannote (audio diarization) are both wired in
  now (§5c/§5d). Remaining open questions: for pyannote, whether a *measured* count should ever
  be allowed to **suggest** a credit correction (today it is a second number and nothing more);
  for MVSEP, which `sep_type` should be the default (`karaoke_lead_back` splits vocals, the
  53-stem model is far richer but slower and more expensive).
- MVSEP costs real credits and uploads audio off-machine: today it is strictly per-track and
  opt-in (D26). A batch or queue-level hosted run is a product decision, not a technical one —
  and it would have to stay an explicit, per-job choice.
- The hosted queue took ~2 min for a 20 s clip at peak. `max_wait_s` defaults to 1800 s; if
  real-world waits get longer, the honest fix is a visible queue position in the status line
  (the client already receives `current_order` / `eta_seconds`) rather than a bigger timeout.
