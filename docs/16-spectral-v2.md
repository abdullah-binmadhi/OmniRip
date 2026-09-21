# 16 — Spectral anti-fraud v2

Status: merged (2026-09-22)

Implements the v2 rules promised by `docs/04-spectral-antifraud.md` §9: hi-res void
detection, the SBR/tonal-artifact scan, fake bit depth, and stereo asymmetry.
Everything here is deterministic and dependency-free — the same STFT machinery the
v1 detector already uses, no new packages, no network.

## 1. What changes for the user

| Claim in the file | v1 verdict | v2 verdict |
| --- | --- | --- |
| 96 kHz FLAC whose content stops at 22.05 kHz | INCONCLUSIVE | **FRAUD** (hi-res void) |
| "24-bit" FLAC carrying 16-bit masters | PASS | **FRAUD** (empty low byte) |
| Lossy upcast whose high band was rebuilt (birdies) | PASS | **FRAUD** (bandwidth extension) |
| Stereo file with one channel filtered | PASS | **FRAUD** (stereo asymmetry) |
| Honest 24/96 material, honest stereo, honest roll-off | PASS | PASS (unchanged) |

The verdict taxonomy, the report fields, and the phase4 gate behaviour are
untouched: this milestone only makes more of the *same* decisions correct.

## 2. Scope

In scope: the four §9 rules, the two new decode paths they need (stereo f32,
native-rate s32), the bit-depth probe, fixtures and tests.

Out of scope: ML-based upcast detection, per-track reference comparison, any
change to `Verdict`, `SpectralResult` fields, or the report schema.

## 3. Rules (normative)

Evaluation order is the v1 order with the v2 rules appended; the verdict is FRAUD
either way, so ordering only decides which reason is reported.

1. **Guards** — too short, silent, or unreadable → INCONCLUSIVE (v1, unchanged).
2. **v1 brick wall** — rules 2–4 of `docs/04` §6, unchanged.
3. **R1 hi-res void** (docs/04 §9.1). Claimed rate ≥ 88.2 kHz and *both*:
   * `max(E)` over bands with edge ≥ 22.05 kHz ≤ FLOOR + 6 dB, **and**
   * the same `max(E)` ≤ BASE − 20 dB.

   Two conditions, not one. On genuinely flat material (broadband noise, dense
   electronic mixes) the 10th-percentile FLOOR sits *at* the content level, so
   "within 6 dB of the floor" alone calls honest hi-res audio a void. The second
   condition keeps the rule honest and is why v1's INCONCLUSIVE upgrade (§9.1)
   does not fire on flat masters.
4. **R2 fake bit depth** (docs/04 §9.3). Claimed depth ≥ 24 bits, ≥ 1 s of decoded
   samples, and the content's low byte is zero in ≥ 98 % of samples.
   * ffmpeg left-aligns every bit depth into `s32le`, so a 16-bit master padded
     into a 24-bit container keeps bits 8–15 at zero for every sample. The
     content byte is therefore bits 8–15, not the container's bits 0–7 (which are
     always zero and carry no information).
   * A *share*, not a bitwise OR: one outlier would dominate a union.
   * Saturated samples are excluded — a clipped master pins that byte to 0xFF for
     reasons unrelated to the depth it was recorded at.
   * The native decode must not resample or mix: `-ac`/`-ar` rewrite the low bits
     (measured: `-ac 2` on a mono file fabricates a full-range low byte; `-ac 1`
     on a stereo file leaks a 17th bit through the downmix).
5. **R3 SBR / tonal artifacts** (docs/04 §9.2). The passband top is the highest
   band still within BASE − 20 dB. Above it + 1 kHz, count bands whose energy
   exceeds the mean of their four neighbours by ≥ 6 dB *and* sits ≥ FLOOR + 6 dB.
   Three or more → FRAUD: content above the encoder's own passband is injected,
   not recorded.
6. **R4 stereo asymmetry** (docs/04 §9.4). The side channel must carry energy
   within 20 dB of the mid (otherwise the rule abstains — a near-mono mix cannot
   be judged). Then, with both cutoffs from the v1 detector: the lower cutoff must
   be ≤ 19 kHz, the two must differ by ≥ 2 kHz, and the lower one must be steep
   (S ≥ 20 dB/kHz). One channel filtered and the other not is a transcode
   signature, not a microphone.

## 4. Pipeline integration

`phase4_spectral.run_spectral_check` now:

* probes the declared bit depth alongside duration and sample rate;
* decodes the excerpt as **stereo f32** at 48 kHz and splits it into mid/side
  (`mid_side`, exported for tests) instead of a mono downmix — a downmix would
  average the asymmetry away before the analysis ever sees it;
* decodes a **native-rate s32** excerpt only when the claim is ≥ 24 bits, and
  treats that decode as best-effort: if it fails, the bit-depth rule abstains and
  the verdict the spectral rules reached stands.

`ffmpeg` service gains `probe_bit_depth`, `decode_s32`, and a `channels`
parameter on `decode_f32`. `probe_audio_info` now reports `bits`
(`bits_per_raw_sample`, falling back to `bits_per_sample`).

## 5. Fixtures and measurements

Deterministic fixtures live in `tests/test_spectral_v2.py` (unit + one
ffmpeg-backed end-to-end case); `tests/test_spectral.py` keeps the v1 fixture
table with the upgraded expectation.

Findings worth keeping:

* **`fixture_up96_void` never had a void.** The old recipe,
  `irfft(rfft(signal, n=2N), 2N)`, zero-pads the *time* domain — it reinterprets
  the 44.1 kHz samples at 88.2 kHz, which shifts the whole spectrum *up* and fills
  the top of the band with down-shifted content. The v1 rule only called it
  INCONCLUSIVE because FLOOR sat at the content level and the void bands landed
  3 dB under FLOOR+3 — a coincidence, not a detection. The corrected recipe
  zero-pads the *spectrum* (`irfft(rfft(signal), n=2N)`), which is true
  band-limited interpolation and produces a real void at −74 dB and below.
* **Saturation is common enough to matter.** A fake-24-bit fixture built from
  loud content clips ~5 % of samples; with an unfiltered histogram the share drops
  to 0.954 and the rule misses. Excluding saturated samples restores 1.0.
* **`-ac` is not neutral.** See R2 above; the native decode keeps the channel
  layout and the sample rate of the file.

## 6. Tests

`tests/test_spectral_v2.py` (new, 17 cases): the four rules, their controls
(honest hi-res, symmetric stereo, quiet side, no-birdie brick wall), the helper
functions, and the ffmpeg-backed bit-depth case.
`tests/test_spectral.py`: the `fixture_up96_void` row now expects FRAUD.
`tests/test_phase4_spectral.py`: fakes record the decode calls; three new cases
cover the stereo decode, the gated native decode, and the best-effort failure.

## 7. Acceptance criteria

* All four §9 rules implemented with the thresholds above.
* No new dependencies; no network access in any test.
* `uv run pytest -q` green, `uv run ruff check .` clean.
* v1 fixtures keep their verdicts except the documented upgrade.
* A real file path still works end to end (see §8).

## 8. Live verification (2026-09-22)

* Full suite green after the change; ruff clean.
* `tests/test_spectral_v2.py::test_fake_24bit_detected_through_a_real_ffmpeg_decode`
  decodes a real FLAC through the production `FfmpegService` (not a mock) and
  confirms the padding survives the FLAC → s32le path.
* Fixture table (unit, 44.1/96 kHz PCM) verified locally with the diagnostics
  printed during development; the numbers quoted in §5 come from that run.

## 9. Follow-ups

* Real-world corpus pass: run the new rules over the harvested library and record
  how many tracks change verdict, then tune thresholds if the false-positive rate
  is non-zero on honest material.
* The report could name the *rule* that fired (currently it is prose in `detail`);
  worth doing only if the UI ever needs to filter by reason.
