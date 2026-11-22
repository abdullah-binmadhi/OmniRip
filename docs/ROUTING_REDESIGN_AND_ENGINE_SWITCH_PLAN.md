# Audio Engine `[E]` Switching Fix & `[3] Routing` Page Redesign Plan

## 1. Root Cause Analysis: Why Pressing `[E]` Switched to Your Dongle DAC Once, But Wouldn't Switch Back to Orchestria

When we traced the `[E]` hotkey (`Cycle Engine`) in `src/ui/app.rs` and `src/dsp/streamer.rs`, we found a two-part state desynchronization bug:

1. **`self.streamer.engine_type` Was Disconnected from `input_capture_enabled` (`src/ui/app.rs:1635` & `src/dsp/streamer.rs:1470`):**
   - Pressing `[E]` executed:
     ```rust
     self.streamer.engine_type = self.streamer.engine_type.next();
     if self.streamer.is_running.load(Ordering::SeqCst) {
         let _ = self.streamer.restart();
     }
     ```
   - Inside `AudioStreamer::start()`, `self.engine_type` was **never read**. Instead, `start()` only checked `self.is_input_capture_enabled()`:
     - When `input_capture_enabled` was `false`, `start()` called `restore_system_output()`, which switched macOS Default Output directly to your connected USB-C Dongle DAC (`iBasso-DC03-Pro`).
     - When you pressed `[E]` a second time to switch back to **Orchestria System-Wide Sound Engine** (`AudioEngineType::PureRustIpc`), `engine_type` flipped back to `PureRustIpc`, but `input_capture_enabled` remained `false`!
     - As a result, `restart()` ran `start()` with `input_capture_enabled == false`, called `restore_system_output()` again, and **left macOS stuck on `iBasso-DC03-Pro` instead of switching macOS Default Output back to `Orchestria Audio`**.

2. **How We Fix `[E]` Switching (`AudioStreamer::cycle_engine_mode()`):**
   - Unify `AudioEngineType` and `input_capture_enabled` into a single atomic transition method `pub fn cycle_engine_mode(&mut self) -> (AudioEngineType, String)` on `AudioStreamer`:
     - **Switching to `AudioEngineType::DirectHardware` (Direct Hardware DAC Mode):**
       - Calls `self.set_input_capture(false)`, which stops the system loopback capture stream and switches macOS Default Output directly to your selected physical DAC (`iBasso-DC03-Pro`) with calibrated volume.
     - **Switching to `AudioEngineType::PureRustIpc` (Orchestria System-Wide Sound Engine):**
       - Calls `self.set_input_capture(true)`, which starts the Zero-Dot POSIX Shared Memory reader (`/orchestria_audio_shm`) and switches macOS Default Output right back to **`Orchestria Audio`** while routing the processed 64-bit DSP output to `iBasso-DC03-Pro`.
   - Keep `self.engine_type` and `self.input_capture_enabled` 1:1 synchronized whenever `[E]`, `[X]`, or `:mic` / `:syseq` is used, so pressing `[E]` repeatedly toggles cleanly back and forth:
     `Orchestria Audio (System-Wide EQ)` ⇄ `iBasso-DC03-Pro (Direct Hardware DAC)` every single time.

---

## 2. Why the Current `[3] Routing` Page Is Cluttered (Problems Identified)

From your screenshot of `[3] Routing`:
1. **Unnecessary Audition Panel Taking Up 25% of the Screen:**
   - The bottom-left `BUILT-IN ACOUSTIC AUDITION ENGINE ([P] Toggle, [O] Cycle Mode)` box takes up an entire quadrant for synthetic test tones that are not needed.
2. **Redundant Bottom-Right Setup Box:**
   - The bottom-right `MACOS SYSTEM-WIDE SOUND LOOPBACK SETUP GUIDE` box repeats the same output device name, IPC description, and test-tone instructions already displayed in the middle panes.
3. **15-Line Vertical ASCII Tree Causes Horizontal Text Truncation:**
   - In `HARDWARE SIGNAL FLOW TOPOLOGY`, the 15-line vertical ASCII tree (`|`, `v`, `+--`, `\--`) forces long strings like `Pure Rust Zero-Driver IPC Transport (/tmp/orchestria_audio.sock` to clip right into the border.
4. **Outdated & Confusing Labels:**
   - Even when `OrchestriaAudio.driver` v2 (Zero-Dot SHM) is active, the topology box still says `(Direct Hardware Stream - Zero Loopback Driver)` and `Pure Rust Zero-Driver IPC Transport`, making it hard to tell at a glance whether macOS is currently routed through **Orchestria Audio** or **Direct to `iBasso-DC03-Pro`**.

---

## 3. Visual Design Sketch: New `[3] Routing` Studio Layout

We remove the entire bottom row (`BUILT-IN ACOUSTIC AUDITION ENGINE` + redundant setup guide) and give that vertical space to two spacious, clean side-by-side cards with visual mode pills, live OS routing status, a horizontal signal flow bar, and clean hardware/clock telemetry.

### Mode A: When Orchestria System-Wide Sound Engine Is Active (`[E]` Mode 1)

```text
┌─ AUDIO ROUTING & LOW-LATENCY STREAM ENGINE ────────────────────────────────────────────────────────────────────────────┐
│ ┌─ SYNC ENGINE LATENCY PRESET (Press [S] or [Left/Right] to Change) ─────────────────────────────────────────────────┐ │
│ │     [        ] EXTREME (5.3ms)      [        ] ULTRA (10.7ms)     [* ACTIVE *] BALANCED (21.3ms)   [        ] STABLE│ │
│ │         256 frames cushion              512 frames cushion              1024 frames cushion           2048 frames   │ │
│ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ AUDIO ENGINE & HARDWARE ROUTING ─────────────────────────┐ ┌─ REAL-TIME BUFFER, CLOCK & DSP TELEMETRY ────────────┐ │
│ │                                                           │ │                                                      │ │
│ │  ACTIVE ENGINE MODE ([E] or [X] to Switch)                │ │  BUFFER CUSHION & STREAM HEALTH                      │ │
│ │  ┌───────────────────────────────────┐ ┌────────────────┐ │ │  Tank Level:   [██████████░░░░░░░░░░]  50% Cushion   │ │
│ │  │ ● ORCHESTRIA SYSTEM-WIDE ENGINE   │ │ ○ DIRECT DAC   │ │ │  Latency:      1024 / 2048 frames (~21.3 ms)         │ │
│ │  └───────────────────────────────────┘ └────────────────┘ │ │  Stream State: ACTIVE • Phase-Locked (0 Dropouts)    │ │
│ │  OS Default Output: Orchestria Audio (Zero-Dot SHM v2)    │ │                                                      │ │
│ │  Privacy Status:    Zero Mic Access (No macOS Orange Dot) │ │  MASTER CLOCK PLL & RESAMPLER ([R] Re-Sync)          │ │
│ │                                                           │ │  Capture Link: Zero-Dot POSIX SHM (/orchestria_shm)  │ │
│ │  PHYSICAL OUTPUT TRANSDUCER ([D] Cycle • [A] Auto-DAC)    │ │  Clock Drift:  +0.00 PPM (PID Servo Phase-Locked)    │ │
│ │  Active Output:     [ iBasso-DC03-Pro ]                   │ │  Resampler:    16-Point Blackman-Harris Sinc         │ │
│ │  Detected DAC Chip: Dual Cirrus Logic CS43131 (USB-C DAC) │ │  PCM Streamed: 14.20 MB (1,861,220 stereo frames)    │ │
│ │  Available Outputs: ● iBasso-DC03-Pro  ○ MacBook Speakers │ │                                                      │ │
│ │                                                           │ │  DSP WORKER HEADROOM                                 │ │
│ │  LIVE SIGNAL CHAIN                                        │ │  Thread Load:  [██░░░░░░░░░░░░░░░░░░]   2.1% / 100%  │ │
│ │  [macOS Audio] ──► [Orchestria SHM] ──► [64-Bit EQ/DSP]   │ │  Sample Rate:  48,000 Hz • 64-Bit Internal / 32f I/O │ │
│ │                                          └──► [iBasso DAC]│ │  Active Stage: 10-Band ISO EQ + Mastering + AutoEQ   │ │
│ └───────────────────────────────────────────────────────────┘ └──────────────────────────────────────────────────────┘ │
│  [E] Switch Engine (Orchestria ⇄ Direct DAC)  [D] Cycle Output DAC  [A] Auto-Select Best DAC  [S] Latency  [R] Re-Sync │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Mode B: When Switched to Direct Hardware DAC (`[E]` Mode 2)

Pressing **`[E]`** immediately flips the active pill to **`● DIRECT HARDWARE DAC`** and switches macOS Default Output straight to `iBasso-DC03-Pro`. Pressing **`[E]`** again immediately flips back to **`● ORCHESTRIA SYSTEM-WIDE ENGINE`** and routes macOS Default Output back through `Orchestria Audio`:

```text
│  ACTIVE ENGINE MODE ([E] or [X] to Switch)                │
│  ┌───────────────────────────────────┐ ┌────────────────┐ │
│  │ ○ ORCHESTRIA SYSTEM-WIDE ENGINE   │ │ ● DIRECT DAC   │ │
│  └───────────────────────────────────┘ └────────────────┘ │
│  OS Default Output: iBasso-DC03-Pro (Direct Hardware)     │
│  Mode Description:  OS audio goes straight to your DAC;   │
│                     Orchestria Player streams bit-perfect │
│                                                           │
│  LIVE SIGNAL CHAIN                                        │
│  [Orchestria Player] ──► [64-Bit EQ/DSP] ──► [iBasso DAC] │
```

---

## 4. Implementation Steps

### Phase 1: Fix `[E]` Bidirectional Audio Engine Switching (`src/dsp/streamer.rs` & `src/ui/app.rs`)
1. In `src/dsp/streamer.rs`:
   - Update `AudioEngineType::label()` to clear, user-friendly labels:
     - `AudioEngineType::PureRustIpc` → `"Orchestria System-Wide Sound Engine"`
     - `AudioEngineType::DirectHardware` → `"Direct Hardware DAC (Bit-Perfect)"`
   - Keep `self.engine_type` synchronized inside `set_input_capture(enable: bool)`:
     - When `enable == true` (and capture activates): `self.engine_type = AudioEngineType::PureRustIpc;`
     - When `enable == false`: `self.engine_type = AudioEngineType::DirectHardware;`
   - Add `pub fn cycle_engine_mode(&mut self) -> (AudioEngineType, String)`:
     - If currently in System-Wide mode (`self.is_input_capture_enabled()`), calls `self.set_input_capture(false)` so macOS immediately switches to the physical output DAC (`iBasso-DC03-Pro`).
     - If currently in Direct Hardware mode (`!self.is_input_capture_enabled()`), calls `self.set_input_capture(true)` (and starts the streamer if stopped) so macOS immediately switches back to `Orchestria Audio` and activates Zero-Dot SHM capture!
   - In `activate_system_capture_streams()` (`src/dsp/streamer.rs:840-866`):
     - Call `set_macos_system_output_to_device_id(target_id)` right before/with `ShmCaptureHandle::start(...)` and ensure `saved_physical_output_id` is always preserved when switching away and back.
2. In `src/ui/app.rs`:
   - Update the `[E]` key handler in `WorkstationMode::SystemEq` (`src/ui/app.rs:1635`) to call `let (_, msg) = self.streamer.cycle_engine_mode(); self.set_status(&msg);` instead of only flipping the enum without activating system capture.

### Phase 2: Remove Built-In Acoustic Audition Engine & Redesign `[3] Routing` (`src/ui/app.rs`)
1. In `src/ui/app.rs`:
   - Remove the `BUILT-IN ACOUSTIC AUDITION ENGINE ([P] Toggle, [O] Cycle Mode)` panel and the redundant `MACOS SYSTEM-WIDE SOUND LOOPBACK SETUP GUIDE` bottom panel from `render_routing()`.
   - Remove the `[P]` and `[O]` test-tone hotkeys in `WorkstationMode::SystemEq` (`src/ui/app.rs:1618-1634`) and the `[AUDITION: OFF]` header badge (`src/ui/app.rs:2217-2224`) so the header and routing tab are cleaner.
   - Replace `render_routing()` with the 2-card studio layout sketched above:
     - **Top Bar (`Length(4)`):** 4 Latency Preset pills (`EXTREME 5.3ms`, `ULTRA 10.7ms`, `BALANCED 21.3ms`, `STABLE 42.7ms`).
     - **Left Card (`52%` width — `AUDIO ENGINE & HARDWARE ROUTING`):**
       - Side-by-side active engine mode indicator (`[● ORCHESTRIA SYSTEM-WIDE ENGINE]` vs `[○ DIRECT HARDWARE DAC]`), live OS default output status, and zero-dot privacy indicator.
       - Physical Output Transducer section showing active output (`[ iBasso-DC03-Pro ]`), detected DAC chip profile (`self.streamer.hardware_chip_profile().summary_line()`), and available physical output devices with active dot markers (`●` / `○`).
       - Compact horizontal Live Signal Chain diagram that adapts dynamically to System-Wide vs Direct DAC mode without ever clipping or wrapping.
     - **Right Card (`48%` width — `REAL-TIME BUFFER, CLOCK & DSP TELEMETRY`):**
       - Buffer Cushion Tank Gauge (`[██████████░░░░░░░░░░]`), frame count, latency in ms, and health status.
       - Master Clock PLL & Resampler section showing the real active capture backend (`Zero-Dot POSIX SHM (/orchestria_audio_shm)` vs `Direct Hardware`), PID PLL drift in PPM (`[R] Re-Sync`), active resampler (`16-Point Blackman-Harris Sinc` vs `4-Point Hermite Fast Game Mode`), and total frames streamed.
       - DSP Worker Headroom section showing thread load bar, sample rate/bit depth, and active DSP stages.
     - **Footer Bar (`Length(1)`):**
       `[E] Switch Engine (Orchestria ⇄ Direct DAC)  [D] Cycle Output DAC  [A] Auto-Select Best DAC  [S] Latency Mode  [R] Re-Sync Clock  [Space] Pause/Play  [B] Bypass`

### Phase 3: Verification
1. Add unit test `test_cycle_engine_mode_toggles_between_system_wide_and_direct_dac` in `src/dsp/streamer.rs` and a rendering test for `[3] Routing` across standard and compact terminal widths (`140x36`, `100x24`, `180x50`) in `src/ui/app.rs`.
2. Run `cargo test --locked -- --test-threads=1` and `cargo build --release --locked`, reinstall the updated `orchestria` binary to `~/.local/bin/orchestria` and `~/.cargo/bin/orchestria`, update `graphify-out/`, commit, merge, and push.
