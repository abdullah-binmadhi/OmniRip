# Sync Engine Latency Preset Enhancement, Glitch/Clipping Elimination & Hardware Optimization Plan

## 1. Root Cause Analysis: Why Switching `SyncMode` Felt Identical & Why `EXTREME` Clipped/Crackled

From your screenshot (`Screenshot 2026-11-24 at 1.23.13 pm.png`) and our deep inspection of `src/dsp/servo.rs`, `src/dsp/streamer.rs`, and `src/ui/app.rs`, we found **four concrete causes**:

### Bug 1: The Preset Labels (`256 / 512 / 1024 / 2048`) Did Not Match `SyncMode::target_frames()` (`512 / 1024 / 2048 / 4096`)
Look at your screenshot: `[* ACTIVE *] ULTRA (10.7ms)` is selected (`512 frames cushion`), yet the title bar directly above it reads **`Active Target: 21.3 ms @ 48.0 kHz`**.
- Reason: In `src/dsp/streamer.rs:67-76`:
  ```rust
  SyncMode::Extreme  => 512,   // UI label said 256 frames (5.3ms), real target was 512 (10.7ms)
  SyncMode::Ultra    => 1024,  // UI label said 512 frames (10.7ms), real target was 1024 (21.3ms)
  SyncMode::Balanced => 2048,  // UI label said 1024 frames (21.3ms), real target was 2048 (42.7ms)
  SyncMode::Stable   => 4096,  // UI label said 2048 frames (42.7ms), real target was 4096 (85.3ms)
  ```

### Bug 2: Changing Presets Only Changed a Soft Watermark Number (`AtomicUsize`) — Never the Hardware Buffer or Ring Trim
1. **No Hardware `cpal::BufferSize` Reconfiguration:** In `src/dsp/streamer.rs:1540`, the CoreAudio / WASAPI / ALSA output stream always opened with `cpal::BufferSize::Default` (~512 frames on macOS/USB DACs regardless of whether you chose `EXTREME`, `ULTRA`, `BALANCED`, or `STABLE`).
2. **40-Second PID Drain Illusion:** When switching from `STABLE` down to `EXTREME` or `ULTRA`, `ServoReader::read()` (`src/dsp/servo.rs:186`) only adjusted playback rate by at most **0.5% (`±0.005`)**. Shrinking a 4,096-frame backlog down to 512 frames at 0.5% took **~15+ seconds**, so toggling presets felt like nothing happened at all!

### Bug 3: Violent Step-Discontinuity Clicks / Crackling in `EXTREME` Mode When Switching Engine Mode (`[E]`)
Look at `src/dsp/servo.rs:154-205`:
1. **Un-ramped Hard Zero Cut (`avail < 4`):**
   - CoreAudio / WASAPI callbacks typically pull `256` or `512` frames per quantum, and `ShmCaptureHandle` / CoreAudio inputs produce audio in bursts.
   - When `target` is small (`256` or `512`), `avail` briefly touches `0` right at the end of an output callback.
   - Line 155 triggered `self.primed = false;` and lines 163–165 filled the next callback with **`0.0` immediately without any fade-out or fade-in envelope**. Jumping straight from an arbitrary waveform sample (say `0.45`) to `0.0` creates an audible high-frequency square-edge **snap/pop/clipping** sound!
2. **History Reset Click on Mode Toggle:**
   - When switching Active Engine Mode (`[E]`) from `Direct Hardware` back to `Orchestria System-Wide Engine`, stale audio from before the switch remained in `rtrb`, causing brief sample/phase discontinuities in `EXTREME` where there is almost no slack cushion.
3. **Oversized Fixed `rtrb` Pre-Priming Deadband:**
   - In `EXTREME`, using the heavy `16-point Blackman-Harris Sinc` resampler inside small hardware callbacks leaves less CPU margin per quantum, whereas `ULTRA` / `EXTREME` benefit from tighter hardware quantums + adaptive underrun concealment + smooth `2.5 ms` cosine crossfade recovery!

---

## 2. How We Enhance It: A Real, Audible, Glitch-Free 4-Tier Sync Engine Architecture

Rather than four arbitrary numbers that feel identical, each preset will configure a complete **Audio Profile Bundle** (Hardware Quantum Size + Ring Cushion + Resampler Mode + Dynamic Soft-Fade Concealment) and show live telemetry of what actually changed!

### A. Unified Preset Specifications (`SyncMode` Spec Table)

| Preset | Hardware Callback Quantum (`cpal::BufferSize`) | Servo Ring Cushion (`target_frames`) | Total End-to-End Latency (`@ 48 kHz`) | Resampler Kernel | Underrun Protection & Ideal Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`EXTREME`** *(Esports / Zero-Lag)* | `Fixed(128)` (fallback `Default` if DAC rejects) | `256 frames` (`5.3 ms`) | **~8.0 ms** (`2.7ms` HW + `5.3ms` Ring) | **4-Point Fast Hermite Cubic** *(zero trig CPU overhead)* | Smooth `3 ms` Raised-Cosine Fade-Out/In + Zero-Crossing Hold; zero pops even if CPU spikes. Best for **FPS/MOBA gaming & live synth monitoring**. |
| **`ULTRA`** *(High-Speed DAC)* | `Fixed(256)` | `512 frames` (`10.7 ms`) | **~16.0 ms** (`5.3ms` HW + `10.7ms` Ring) | **16-Point Blackman-Harris Sinc** *(fast lock)* | Tight audiophile clock lock with sub-16ms tactile responsiveness. Best for **USB-C Dongle DACs (`iBasso DC03 Pro`) & desktop responsiveness**. |
| **`BALANCED`** *(Studio Reference)* | `Fixed(512)` (or `Default`) | `1024 frames` (`21.3 ms`) | **~32.0 ms** (`10.7ms` HW + `21.3ms` Ring) | **16-Point Blackman-Harris Sinc** | Classic reference equilibrium between crisp UI/video sync and rock-solid Bluetooth/Wi-Fi immunity. Best for **daily music, YouTube/Movies & AirPods**. |
| **`STABLE`** *(Audiophile Fortress)* | `Default` (`1024–2048` OS max stability) | `2048 frames` (`42.7 ms`) | **~64.0 ms+** | **16-Point Blackman-Harris Sinc** | Huge buffer reserve immune to heavy background compiles, Wi-Fi jitter, and Bluetooth A2DP interference. |

### B. Elimination of All Clipping, Popping & Crackling (DSP Engineering Fixes)

1. **Clickless Underrun Concealer + 128-Sample (2.7ms) Raised-Cosine Fade Envelope (`src/dsp/servo.rs`):**
   - Replace the harsh instant cut to `0.0` (`avail < 4 -> out.fill(0.0)`) with a deterministic **Clickless Micro-Crossfade State Machine**:
     - **Track Output Envelope Gain (`gain_env: f32` in `0.0..=1.0`)**:
       - On an underrun (`consumer.pop()` fails), instead of jumping to zero on sample `k`, smoothly ramp `gain_env` down over **128 samples (~2.67 ms)** using a smooth Linear/Cosine ramp (`step = 1.0 / 128.0`) holding a gently damped (`* 0.992`) slope from `history[14]..history[15]`.
       - When audio resumes (`primed` becomes `true`), ramp `gain_env` smoothly back from `0.0` to `1.0` over **128 samples (~2.67 ms)** so switching Engine Mode (`[E]`) or recovering in `EXTREME` never produces a single click or pop!
   - **Adaptive Floor Safety Margin (No Self-Starving in `EXTREME`):**
     - Ensure `ServoReader::read()` only enters pre-buffering when `avail == 0` AND keep an automatic **underrun counter (`underruns: AtomicU64`)** + **auto-cushion floor guard**: if `EXTREME` detects `>= 3` underruns within 2 seconds on slow hardware, it raises an internal adaptive safety floor slightly (or logs `"0 XRUNs"` / `"Auto-Protected"`) without clipping!
2. **Smooth 20ms Queue Trim on Preset Downgrade (`trim_excess_to_target()`):**
   - When switching from `STABLE` (`2048 frames`) down to `EXTREME` (`256 frames`), instead of making the user wait 40 seconds for the PID loop to drift down at 0.5%, `set_sync_mode()` triggers a **smooth 64-frame crossfaded trim** in the ring consumer (`excess > target * 2`), bringing latency down to the new target in **under 50 milliseconds** cleanly!
3. **Zero-Glitch Mode Switching (`[E]` Engine Toggle & `set_sync_mode` Hardware Rebind):**
   - When switching `SyncMode` (`[S]`, `[←]`, `[→]`):
     1. Apply the new `target_frames` and matching `ResamplingMode` (`FastHermite` on `EXTREME`, `AudiophileSinc` on others, unless user explicitly enabled Game Mode).
     2. If the requested hardware quantum (`cpal::BufferSize::Fixed(quantum)`) differs from the currently active stream's hardware buffer size (e.g., switching between `EXTREME` / `ULTRA` / `BALANCED` / `STABLE`), smoothly fade out (`15ms`), rebuild the CPAL stream with the new `cpal::BufferSize` (with automatic fallback to `cpal::BufferSize::Default` if a particular Bluetooth headset or Windows driver rejects `Fixed(128)`), and fade back in cleanly!
     3. That way, switching from `STABLE` to `EXTREME` gives an **immediate, measurable change** in hardware callback size, total latency (`ms`), resampler kernel, and zero-clipping response!

### C. Enhanced Preset Bar UI (`render_routing()` in `src/ui/app.rs`)

Instead of showing static misleading numbers that don't reflect the active preset, the Top Bar of `[3] Routing` will show the **complete live Sync Preset Strip** with:
1. Accurate hardware quantum + servo cushion (`HW + Ring`) and real total latency (`ms`),
2. Highlighted Active Preset Badge showing both **Quantum**, **Resampler Kernel**, and **0 XRUN / Glitch Status**,
3. A compact live **Latency & Jitter Bar** showing `Active Target`, `Actual Measured Latency`, `HW Quantum`, `Sinc/Hermite Kernel`, and `XRUN Count (Underruns: 0)` right inside the Sync Preset header so you can visually verify every preset change the instant you press `[S]` or `[←/→]`!

```text
┌─ SYNC ENGINE LATENCY PRESET ([S] or [Left/Right] • Live: 7.9ms total │ HW: 128f + Ring: 256f │ Fast Hermite │ 0 XRUNs) ┐
│   [* ACTIVE *] EXTREME (5.3ms)        [        ] ULTRA (10.7ms)        [        ] BALANCED (21.3ms)    [        ] STABLE (42.7ms) │
│   256f Ring • 128f HW • Hermite       512f Ring • 256f HW • Sinc       1024f Ring • 512f HW • Sinc      2048f Ring • Auto • Sinc  │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Concrete Code Changes Across Files

1. **`src/dsp/servo.rs`:**
   - Add `gain_env: f32`, `underrun_count: Arc<AtomicU64>`, and `pending_trim: Arc<AtomicBool>` to `ServoReader`.
   - Fix `ServoReader::read()`:
     - Remove abrupt `0.0` cuts; apply **128-sample clickless fade-out** on underrun and **128-sample clickless fade-in** on re-prime / Engine Mode switch.
     - Increment `underrun_count` cleanly on true empty-ring underruns and expose `underrun_count()` via `pll_telemetry_ext()`.
     - Implement instant smooth excess-frame skip/crossfade when `set_sync_mode()` lowers `target_frames` so shrinking from `STABLE` -> `EXTREME` takes `<50ms` instead of 40 seconds!
2. **`src/dsp/streamer.rs`:**
   - Align `SyncMode` methods cleanly:
     - `SyncMode::target_frames()` → `Extreme: 256`, `Ultra: 512`, `Balanced: 1024`, `Stable: 2048` (matching the UI labels 1:1!).
     - `SyncMode::hardware_buffer_frames()` → `Extreme: Some(128)`, `Ultra: Some(256)`, `Balanced: Some(512)`, `Stable: None` (`BufferSize::Default`).
     - `SyncMode::recommended_resampler()` → `Extreme: FastHermite`, others `AudiophileSinc`.
     - `SyncMode::label()` & `SyncMode::detail()`.
   - Update `start()` to try `cpal::BufferSize::Fixed(frames)` for `Extreme`/`Ultra`/`Balanced` with automatic seamless fallback to `cpal::BufferSize::Default` if the OS audio driver (macOS Bluetooth A2DP, Windows Shared WASAPI, or Linux ALSA/PipeWire) doesn't support that exact fixed period size — guaranteeing **100% cross-platform compatibility** on macOS, Windows, and Linux!
   - Update `set_sync_mode()` to apply the matching `ResamplingMode`, trigger excess trim, and smoothly rebuild the output stream if the hardware buffer quantum changed (only when already running), eliminating pops/crackles and making every preset switch immediately measurable!
   - Store `active_hw_buffer_frames: Arc<AtomicUsize>` and expose `effective_latency_breakdown()` `(hw_ms, ring_ms, total_ms, xruns)` for the UI.
3. **`src/ui/app.rs`:**
   - Update `render_routing()` Tier 1 Sync Preset Strip and Tier 2/3 telemetry cards to display accurate `Active Target (ring_ms + hw_ms = total_ms)`, active kernel (`4-Point Fast Hermite` vs `16-Point Blackman-Harris Sinc`), and live `Underruns (XRUNs)` counter!
   - Update status bar messages when cycling `[S]` / `[←/→]`.
4. **Verification & Tests:**
   - Add unit tests in `src/dsp/servo.rs`:
     - `test_servo_underrun_and_reprime_no_step_clipping`: verifies that starved ring buffers ramp smoothly with bounded sample-to-sample derivative (`max |delta| < 0.08`) instead of snapping violently to `0.0`!
     - `test_servo_downgrade_trim_shrinks_backlog_immediately`: verifies switching from `2048` -> `256` frames trims backlog down smoothly instead of stalling.
   - Add unit tests in `src/dsp/streamer.rs`:
     - `test_sync_mode_specs_match_labels_and_resamplers`: verifies `Extreme(256)`, `Ultra(512)`, `Balanced(1024)`, `Stable(2048)` targets, quantums, and resampler kernels.
   - Run `cargo test --locked -- --test-threads=1` and `cargo build --release --locked`.
