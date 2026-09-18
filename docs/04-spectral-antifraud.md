# 04 — Spectral Anti-Fraud Check (FFT cutoff detector)

Normative algorithm for `analysis/spectral.py`. Applies **only** to P2P-sourced files
claiming lossless quality (Decision D3). Goal: detect MP3s (or other lossy audio) transcoded
up to FLAC — the most common Soulseek fraud — by finding the brick-wall low-pass fingerprint
the original lossy encoder imprinted.

## 1. Threat model

| Variant | Signature | v1 coverage |
|---------|-----------|-------------|
| (a) MP3/AAC → FLAC upcast | Hard spectral cutoff at the encoder's lowpass (≈16 kHz @128k, ≈18–19 kHz @192k, ≈20–20.5 kHz @320k LAME) with a very steep "cliff" | ✅ primary target |
| (b) 44.1 kHz → 96/192 kHz upsample | Content void above 22.05 kHz despite hi-res claim | ⚠️ soft flag (INCONCLUSIVE); full rule in §9 |
| (c) 16-bit → "24-bit" fake | No new information in lower bits (quantization-noise floor analysis) | ❌ v2 (§9) |

Known limitation (accepted): a **320k MP3 upcast** cuts at ≈20.5 kHz and passes v1 rules —
audibly near-transparent anyway; strictness is tunable (§6).

## 2. Decode step (async, ffmpeg pipe)

```
ffmpeg -v error -ss {0.3 × duration} -t 60 -i <file> -ac 1 -ar 48000 -f f32le -
```

- 60 s mid-track excerpt: avoids silent intros/outros, bounds CPU (≤ ~3 s total).
- Mono downmix: fraud filtering affects both channels; averaging is fine and halves data.
- 48 kHz output: Nyquist 24 kHz covers the whole detection band (13–22 kHz) regardless of
  source rate. Read exactly `48000 × 60 × 4` bytes (or to EOF) into
  `np.frombuffer(..., dtype=np.float32)`.
- If the file is shorter than 70 s, analyze from `0.15 × duration` for
  `min(60, 0.7 × duration)` seconds; if analyzable audio < 10 s → INCONCLUSIVE.

## 3. Spectral estimation

Parameters (constants in one place, tunable):

| Param | Value | Notes |
|-------|-------|-------|
| `n_fft` | 8192 | ≈5.9 Hz/bin @48k |
| `hop` | 2048 | ≈1406 frames per 60 s |
| Window | Hann | `np.hanning` |
| Band width | 500 Hz | Bands from 1 kHz to 24 kHz |
| Frame aggregate | 90th percentile of per-frame band power | Robust to quiet passages |

Compute power spectrogram `P[f, t] = |STFT|²`, convert to dB: `10·log10(P + 1e-12)`.
Band energy `E(b)` = dB of mean power across the band's bins, aggregated over frames with
the 90th percentile.

Reference quantities:
- `BASE` = median of `E(b)` over bands 2–10 kHz (the "musical content" baseline).
- `FLOOR` = 10th percentile of `E(b)` over all bands ≥ 1 kHz (noise floor estimate).
- `RMS` of the excerpt; if RMS < −50 dBFS → INCONCLUSIVE (near-silent file).

## 4. Cutoff detection

A band is **dead** when `E(b) < max(BASE − 55 dB, FLOOR + 3 dB)`.

Starting from the top band (24 kHz), find the highest contiguous run of dead bands spanning
**≥ 1.5 kHz**. The cutoff `f_c` is the upper edge of the highest **non-dead** band directly
below that run. No qualifying dead run → `f_c = Nyquist (24 kHz)`.

## 5. Steepness (brick-wall metric)

```
S = E(f_c − 1000 .. f_c) − E(f_c .. f_c + 1000)      [dB per kHz]
```

i.e. the energy drop across the cutoff. Lossy encoders produce cliffs typically
≥ 25–40 dB/kHz; natural recordings and honest lossless roll off gradually (< 10 dB/kHz)
or have no cutoff at all.

## 6. Verdict rules (v1, in evaluation order)

| # | Condition | Verdict |
|---|-----------|---------|
| 1 | Analyzable audio < 10 s, or RMS < −50 dBFS, or decode error | INCONCLUSIVE |
| 2 | `f_c ≤ 19.0 kHz` **and** `S ≥ 30 dB/kHz` | FRAUD |
| 3 | `f_c ≤ 17.0 kHz` **and** `S ≥ 20 dB/kHz` | FRAUD |
| 4 | `f_c ≤ 15.0 kHz` **and** `S ≥ 12 dB/kHz` | FRAUD |
| 5 | File claims sample rate ≥ 88.2 kHz **and** everything above 22.4 kHz is dead | INCONCLUSIVE (hi-res upsample suspicion; log loudly) |
| 6 | `f_c ≤ 19.0 kHz` and `15 ≤ S < 30` | INCONCLUSIVE (borderline) |
| 7 | otherwise | PASS |

`INCONCLUSIVE` handling (Phase 4): default = treat as PASS with WARNING; if
`spectral.strict = true` → trigger fallback. `FRAUD` → delete + fallback (docs/03 Phase 4).

False-positive containment rationale: rule steepness gates protect legitimately
band-limited recordings (historical transfers, some classical/mastered content roll off
gradually); the cost of a rare false FRAUD is merely a re-download via fallback, while the
cost of a false PASS is a fake-lossless file in the library — so thresholds deliberately
favor rejection within the cliff-evidence regime.

## 7. Reference cutoff table (for logs & tuning)

| Lossy source | Expected `f_c` |
|--------------|----------------|
| MP3 (LAME) 128k | ≈16.0–16.5 kHz |
| MP3 192k | ≈18–19 kHz |
| MP3 256k | ≈19.5–20 kHz |
| MP3 320k CBR | ≈20–20.5 kHz |
| AAC 128k | ≈16–17 kHz (softer knee) |
| AAC 256k | ≈18–19 kHz |
| Opus (YouTube) 128–160k | full-band to ≈20 kHz (why D3 exempts provenance-lossy files) |

## 8. Pseudocode (normative shape)

```
fn analyze(path, claimed_sample_rate) -> Verdict:
    pcm = ffmpeg_decode_excerpt(path)                     # §2
    if pcm is None or len(pcm) < 10s: return INCONCLUSIVE
    if rms_db(pcm) < -50: return INCONCLUSIVE
    E = band_energies_db(stft(pcm, 8192, 2048, hann))     # §3, 500Hz bands
    BASE = median(E[2k..10k]); FLOOR = p10(E[all])
    dead(b) = E[b] < max(BASE - 55, FLOOR + 3)            # §4
    f_c = highest_nondead_below_deadrun(min_span=1.5k)
    S = E[f_c-1k..f_c] - E[f_c..f_c+1k]                   # §5
    apply rules §6 in order -> verdict
    return Verdict(verdict, f_c, S, debug_bands=E)        # debug_bands to log at DEBUG
```

Return a dataclass — never raise for expected outcomes; raise only `SpectralError`
(decode/subprocess failure) which Phase 4 maps to INCONCLUSIVE.

## 9. v2 extensions (out of scope, documented for later)

1. **Hi-res void rule (upgrade §6.5 to FRAUD):** if claimed SR ≥ 88.2 kHz and energy above
   22.05 kHz is within 6 dB of the noise floor across the whole excerpt.
2. **SBR/tonal-artifact scan:** narrowband tonal peaks (harmonically sparse "birdies") above
   `f_c` indicate encoder bandwidth-extension on top of an upcast.
3. **Fake-24-bit test:** histogram of sample LSBs / quantization-noise spectrum → effective
   bit depth ≈ 16 in a "24-bit" file → FRAUD.
4. **Stereo asymmetry:** mid/side cutoff mismatch (some upscales filter side channel first).

## 10. Test fixtures (used by docs/09 unit tests — recipes)

Generate with scipy/soundfile in tests (no network, deterministic seeds):

| Fixture | Recipe | Expected |
|---------|--------|----------|
| `fraud_128.flac` | 90 s noise + 220/440 Hz tone mix, **spectral brick mask** (flat passband to the cutoff, 500 Hz raised-cosine transition, hard zero above), cutoff 16.0 kHz, 16-bit FLAC | FRAUD (rules 2–4) |
| `fraud_192.flac` | same brick recipe, cutoff 18.0 kHz (detected `f_c` ≈ 19 kHz per the §7 table) | FRAUD (rule 2) |
| `honest_full.flac` | same source material, **no** lowpass (full band to 22 kHz+) | PASS |
| `honest_rolloff.flac` | gentle 12 dB/oct natural roll-off above 12 kHz (no cliff) | PASS |
| `near_silent.flac` | −60 dBFS noise floor only (no peak normalization) | INCONCLUSIVE |
| `short.flac` | 5 s full-band | INCONCLUSIVE |
| `up96_void.flac` | 44.1 kHz content upsampled to 96 kHz, written as 24/96 FLAC | INCONCLUSIVE (rule 5) |

**Deviation note (M4, recorded here):** the original recipe prescribed a Butterworth
lowpass of order 8. Its rolloff (48 dB/octave) reaches only ≈ 15 dB attenuation 4 kHz above
a 16 kHz cutoff — nowhere near the `DEAD_MARGIN_DB = 55` dB rule — so Butterworth fixtures
drifted to PASS (false negatives). Real lossy encoders brick-wall (the spectrum above the
cutoff is encoded to zero), so the fixtures now use a deterministic raised-cosine mask with
a 500 Hz transition band and a hard zero knee: encoder-faithful, seed-independent, and it
triggers the dead-run rule exactly like real upscales. The detector thresholds in §6 were
not changed; only the fixture recipes were revised.

Tuning protocol: if any fixture verdict drifts after parameter changes, adjust thresholds
in §6 (not the fixtures) and record the change here.

## 11. Performance budget

60 s @48 kHz mono = 2.88 M samples → ≈1406 STFT frames (8192/2048) → numpy < 1 s on an
M1-class core; whole phase (incl. ffmpeg decode) ≤ 3 s per file. One `q_spectral` worker;
throughput ≈ 20 files/min — sufficient since only P2P downloads pass through it.
