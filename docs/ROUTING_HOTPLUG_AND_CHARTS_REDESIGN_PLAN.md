# Dynamic Output DAC Hot-Plug Switching & `[3] Routing` Charts/Telemetry Redesign Plan

## 1. Root Cause Analysis: Why You Had to Restart Orchestria to Detect / Switch `Active Output DAC`

From your two screenshots (`Screenshot 2026-11-24 at 1.04.08 pm.png` and `Screenshot 2026-11-24 at 1.05.21 pm.png`), we traced three interacting bugs in `src/dsp/streamer.rs`:

### Bug A: `selected_output_name` Locked onto the Startup Device (`MacBook Air Speakers`) and Ignored Hot-Plugged DACs
- In `src/dsp/streamer.rs:1045-1052`, `set_input_capture(true)` executed:
  ```rust
  let best_out = self.active_output_name();
  if !best_out.is_empty() && !crate::driver::is_virtual_audio_device_name(&best_out) {
      self.selected_output_name = Some(best_out.clone());
  }
  ```
- When Orchestria started while only `MacBook Air Speakers` was connected, `self.selected_output_name` was permanently pinned to `Some("MacBook Air Speakers")`.
- When you plugged in your external USB-C Dongle DAC (`iBasso-DC03-Pro`) or headphones afterward:
  1. `active_output_name()` (`src/dsp/streamer.rs:525`) unconditionally returned `self.selected_output_name` (`"MacBook Air Speakers"`) without checking if a higher-priority USB DAC had been hot-plugged!
  2. Conversely, if `iBasso-DC03-Pro` was selected and then unplugged, `self.selected_output_name` remained `Some("iBasso-DC03-Pro")` even though the device was no longer present in `available_output_names()`.

### Bug B: CoreAudio Hot-Plug Device Reset Left the Engine Permanently `STOPPED`
- Look at your second screenshot (`Screenshot 2026-11-24 at 1.05.21 pm.png`):
  - Bottom status bar: `Status: CoreAudio stream auto-healed after device reset.`
  - Right pane: `Engine State: STOPPED (Press [Space] to Start Engine)`
  - Left pane: `[ ● ORCHESTRIA SYSTEM-WIDE ENGINE ]` is green, yet `Capture Architecture` fell back to `OS audio plays straight to [MacBook Air Speakers]` (`CaptureBackendKind::None`)!
- **Why this happened:**
  - When a USB DAC is plugged in or unplugged, macOS CoreAudio resets the audio device topology and triggers `needs_rebuild = true` in `poll_health()` (`src/dsp/streamer.rs:1165`).
  - `poll_health()` immediately called `self.restart()` (`self.stop()` followed 0ms later by `self.start()`).
  - Because CoreAudio takes ~150–400ms to finish settling a newly plugged-in USB audio device, `self.start()` returned a transient error during the reset.
  - Because `self.stop()` had already set `self.is_running = false`, every subsequent call to `poll_health()` exited on line 1151 (`if !self.is_running.load(...) { return false; }`) and **never retried `self.start()`**!

### Bug C: No Live Hardware Bus Hot-Plug Polling or Direct Numbered Device Selection
- `poll_health()` did not compare `available_output_names()` against the previously connected hardware list, so plugging in a USB DAC never triggered an automatic switch or UI refresh unless you restarted Orchestria.

---

## 2. How We Fix Dynamic Output DAC Detection & Switching (Zero Restart Needed)

1. **Automatic 1.5-Second Hardware Hot-Plug & Hot-Unplug Watchdog (`poll_health()` in `src/dsp/streamer.rs`):**
   - Store `known_output_devices: Vec<String>` and `user_pinned_output: bool` on `AudioStreamer`.
   - Every 1.5 seconds in `poll_health()`, probe `Self::available_output_names()`:
     - **Hot-Plug Auto-Switch:** If a new physical output device appears (e.g. you plug in `iBasso-DC03-Pro`, USB DAC, Headphones, or AirPods) and it has higher transducer priority than the current device (or `!self.user_pinned_output`), Orchestria **automatically switches `selected_output_name` to the newly connected DAC**, updates `HardwareChipProfile`, syncs the Acoustic Gear profile, and restarts the audio stream onto the new DAC!
     - **Hot-Unplug Auto-Fallback:** If the currently active output device is unplugged and disappears from `available_output_names()`, Orchestria automatically clears the stale selection, falls back to the highest-priority remaining physical output (e.g. `MacBook Air Speakers`), updates `HardwareChipProfile`, and restarts the stream cleanly.

2. **Self-Healing Auto-Retry When CoreAudio Resets (`want_running: AtomicBool`):**
   - Add `pub want_running: Arc<AtomicBool>` (set to `true` on `start()`, `false` only when the user explicitly stops/terminates).
   - If `restart()` inside `poll_health()` hits a transient CoreAudio device-reset window while a USB DAC is initializing, `poll_health()` continues retrying `self.start()` every 400ms until the new USB DAC stream locks in — **so the engine never drops into `STOPPED` after a device reset**!

3. **Interactive Output DAC Selector (`[D]`, `[1]–[9]`, `[A]`, `[F]`):**
   - **`[D]`**: Cycles through all currently connected physical output devices (`available_output_names()`), sets `user_pinned_output = true`, and hot-swaps the live output stream immediately.
   - **`[1]`–`[5]` (on the `[3] Routing` tab)**: Directly selects output device `#1..#5` from the live `CONNECTED OUTPUT TRANSDUCERS` table.
   - **`[A]`**: Re-enables `Auto-Select Best DAC` (`user_pinned_output = false`) and immediately locks onto the highest-priority connected DAC/headphone.
   - **`[F]`**: Forces an immediate hardware bus rescan (`rescan_output_devices()`), re-probing CoreAudio / WASAPI / PipeWire devices and refreshing `HardwareChipProfile` without restarting Orchestria.

---

## 3. Visual Design Sketch: Redesigned `[3] Routing` Page (Zero Empty Space + Live Charts & Complementary Features)

To eliminate the empty space in the bottom half of your second screenshot, `[3] Routing` is structured into **3 balanced horizontal tiers** that dynamically fill 100% of the terminal height:
- **Tier 1 (`Length(4)`):** Sync Engine Latency Preset Selector + Live Round-Trip Latency Badge.
- **Tier 2 (`Length(16)`):** Two-Card Core Routing & Hardware Matrix (`AUDIO ENGINE & INTERACTIVE OUTPUT DAC SWITCHER` on the left, `CLOCK SERVO, BUFFER TANK & ACTIVE DSP PIPELINE` on the right).
- **Tier 3 (`Min(10)` — Expands to Fill All Remaining Vertical Space):** Two Real-Time Visual Telemetry Charts (`LIVE I/O SIGNAL & LIMITER GAIN-REDUCTION CHART` on the left, `LIVE BUFFER CUSHION & CLOCK PLL STABILITY GRAPH` on the right).

```text
┌─ AUDIO ROUTING, HARDWARE DAC MATRIX & REAL-TIME STREAM TELEMETRY ──────────────────────────────────────────────────────┐
│ ┌─ SYNC ENGINE LATENCY PRESET ([S] or [Left/Right] to Change • Effective Round-Trip: 21.3 ms @ 48.0 kHz) ────────────┐ │
│ │     [        ] EXTREME (5.3ms)      [        ] ULTRA (10.7ms)     [* ACTIVE *] BALANCED (21.3ms)   [        ] STABLE│ │
│ │         256 frames cushion              512 frames cushion              1024 frames cushion           2048 frames   │ │
│ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ AUDIO ENGINE & INTERACTIVE OUTPUT DAC SWITCHER ──────────┐ ┌─ CLOCK SERVO, BUFFER TANK & ACTIVE DSP PIPELINE ─────┐ │
│ │  ACTIVE ENGINE MODE ([E] or [X] to Switch)                │ │  BUFFER CUSHION & STREAM HEALTH                      │ │
│ │  [ ● ORCHESTRIA SYSTEM-WIDE ENGINE ] ⇄ [ ○ DIRECT DAC ]   │ │  Tank Level:   [██████████░░░░░░░░░░]  50% Cushion   │ │
│ │  OS Default Output: Orchestria Audio (Zero-Dot SHM v2)    │ │  Latency:      1024 / 2048 frames (21.3 / 42.7 ms)   │ │
│ │  Capture Link:      Zero-Dot POSIX SHM (/orchestria_shm)  │ │  Engine State: ACTIVE • Phase-Locked (0 Dropouts)    │ │
│ │                                                           │ │                                                      │ │
│ │  CONNECTED OUTPUT TRANSDUCERS ([D] Cycle • [A] Auto • [F])│ │  MASTER CLOCK PLL & RESAMPLER ([R] Force Re-Sync)    │ │
│ │  ▸ #1 [● ACTIVE] iBasso-DC03-Pro      │ USB DAC  │ 48kHz  │ │  Clock Drift:  +0.00 PPM (PID Servo Phase-Locked)    │ │
│ │    #2 [○ READY ] MacBook Air Speakers │ Speakers │ 48kHz  │ │  Resampler:    16-Point Blackman-Harris Sinc         │ │
│ │    #3 [○ READY ] External Headphones  │ 3.5mm    │ 48kHz  │ │  PCM Streamed: 824.90 MB (108,121,008 stereo frames) │ │
│ │  Hot-Plug Watchdog: AUTO-DETECT ON (Polls USB/BT every 1s)│ │  DSP Load:     [██░░░░░░░░░░░░░░░░░░]   2.1% / 100%  │ │
│ │  Detected DAC Chip: iBasso Audio • Dual Cirrus CS43131    │ │                                                      │ │
│ │                                                           │ │  ACTIVE 64-BIT DSP STAGE MATRIX                      │ │
│ │  LIVE SIGNAL CHAIN                                        │ │  [10-Band EQ: ON]  [DAC: Schiit R2R]  [Limiter: ON]  │ │
│ │  [OS Audio] ──► [Zero-Dot SHM] ──► [64f DSP] ──► [iBasso] │ │  [Gear: iBasso DC] [Game Mode: OFF]   [Vol: 75% 1:1] │ │
│ └───────────────────────────────────────────────────────────┘ └──────────────────────────────────────────────────────┘ │
│ ┌─ LIVE STEREO OUTPUT & LIMITER TELEMETRY CHART (60s) ──────┐ ┌─ LIVE BUFFER CUSHION & PLL CLOCK STABILITY GRAPH ────┐ │
│ │   0dB ┤      ▄▄    ▄▄▄         ▄▄                         │ │ 100% ┤                                               │ │
│ │  -6dB ┤   ▄▄███▄  ████▄   ▄▄  ████▄   ▄▄▄                 │ │  75% ┤ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ │ │
│ │ -18dB ┤ ▄███████▄▄█████▄▄████▄█████▄▄█████▄▄▄▄            │ │  50% ┤ █████████████████████████████████████████████ │ │
│ │ -36dB ┤████████████████████████████████████████▄▄▄▄▄▄▄▄▄▄ │ │  25% ┤ █████████████████████████████████████████████ │ │
│ │  -∞dB └────────────────────────────────────────────────── │ │   0% └────────────────────────────────────────────── │ │
│ │  Peak L/R: -1.4 / -1.6 dBFS  │ LUFS-M: -13.8 │ GR: 0.0 dB │ │  Cushion Avg: 51% (21.4ms) │ PLL Jitter: ±0.02 PPM   │ │
│ │  Stereo Phase: +0.94 [SOLID] │ Headroom: 1.4 dB (-0.2 Lim)│ │  Underruns: 0  │ Overruns: 0 │ USB Hot-Plug: READY   │ │
│ └───────────────────────────────────────────────────────────┘ └──────────────────────────────────────────────────────┘ │
│  [E] Switch Engine  [D] Cycle Output DAC  [A] Auto-Best DAC  [F] Rescan DACs  [S] Latency  [R] Re-Sync  [Space] Stream │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. New Complementary Features Added to `[3] Routing`

1. **Interactive Connected Output Transducers Table (`[D]` Cycle, `[A]` Auto-Best, `[F]` Rescan Hardware Bus):**
   - Lists every physical output device currently detected on macOS (CoreAudio), Windows (WASAPI), and Linux (ALSA/PipeWire), with its active status badge (`[● ACTIVE]` vs `[○ READY]`), classified transducer type (`USB DAC`, `3.5mm`, `Bluetooth`, `Speakers`), and native sample rate.
   - Displays `Hot-Plug Watchdog: AUTO-DETECT ON [Mode: Auto-Best DAC]` (or `[Mode: Pinned by User]`) so you always know Orchestria will automatically switch to your USB DAC the moment you plug it in.
2. **Active 64-Bit DSP Stage Matrix:**
   - Displays live color-coded badges for every stage in the audio engine (`10-Band EQ`, `DAC Mimicker Flavor`, `True-Peak -0.2 dBFS Limiter`, `Calibrated Gear Profile`, `Esports Game Mode`, and `1:1 Hardware Volume %`).
3. **Rolling 60-Tick Stereo Output & Limiter Telemetry Chart (Bottom-Left):**
   - Dynamically scales to fill the available terminal height (`Min(8)` rows) and plots a 60-column real-time bar graph of post-DSP output peak energy (`dBFS`), paired with live `Peak L/R`, `Momentary LUFS`, `Limiter Headroom`, and `Stereo Phase Correlation`.
4. **Rolling 60-Tick Buffer Cushion & Clock Stability Graph (Bottom-Right):**
   - Dynamically scales to match the left chart and plots a 60-column real-time history of the ring-buffer cushion percentage (`0%–100%`), paired with rolling `Cushion Average (ms)`, `PLL Jitter (PPM)`, and `Hot-Plug Watchdog` status.

---

## 5. Implementation Steps

1. **`src/dsp/streamer.rs` — Hot-Plug Watchdog, Self-Healing Retry & Force Rescan:**
   - Add `want_running: Arc<AtomicBool>`, `user_pinned_output: bool`, `known_output_devices: Vec<String>`, and `last_hotplug_probe_ms: u64` to `AudioStreamer`.
   - Add `pub fn rescan_output_devices(&mut self) -> (String, bool)` which re-queries `Self::available_output_names()`, validates whether `selected_output_name` is still connected, auto-promotes any newly plugged-in higher-priority DAC/headphone when `!self.user_pinned_output` (or when `rescan_output_devices` is called manually via `[F]`), updates `HardwareChipProfile`, and restarts the audio stream if the output device changed or if the stream was interrupted.
   - Update `poll_health()` to:
     1. Run `self.rescan_output_devices()` every 1,500 ms so plugging in or unplugging a USB DAC switches automatically within 1.5 seconds without restarting Orchestria.
     2. Auto-retry `self.start()` whenever `self.want_running` is `true` and `!self.is_running` (or when `self.is_input_capture_enabled()` is `true` but `self.active_capture_backend == CaptureBackendKind::None`), eliminating the bug where a CoreAudio device reset left the engine `STOPPED`.
   - Update `active_output_name()` so that if `selected_output_name` is set to a device that is no longer in `available_output_names()`, it dynamically falls back to `find_devices()` instead of returning a disconnected device name.
2. **`src/ui/app.rs` — Rolling Telemetry History & 3-Tier `[3] Routing` Dashboard:**
   - Add a 60-sample rolling telemetry ring (`routing_peak_history: VecDeque<f32>`, `routing_cushion_history: VecDeque<f32>`, `routing_drift_history: VecDeque<f32>`) updated in `sync_dsp_telemetry()`.
   - Wire `[F]` on the `[3] Routing` tab (`WorkstationMode::SystemEq`) to call `self.streamer.rescan_output_devices()` + `self.sync_active_transducer_gear()`.
   - Upgrade `render_routing()` to render the 3-tier layout (Latency Preset Bar + 2-Card Engine/DAC Switcher & DSP Matrix + 2-Card Dynamic Height Real-Time Stereo Level & Buffer Cushion Charts).
3. **Verification:**
   - Add unit tests for hot-plug output device promotion, disconnected device fallback, and 3-tier routing chart rendering across multiple terminal sizes.
   - Run `cargo test --locked -- --test-threads=1` and `cargo build --release --locked`.
