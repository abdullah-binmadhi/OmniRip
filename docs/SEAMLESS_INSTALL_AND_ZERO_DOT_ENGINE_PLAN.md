# Orchestria: Seamless Cross-Platform Sound Engine Installation & Zero-Dot / Zero-Echo Architecture Plan

> **Core Assumption:** **Every user wants full System-Wide EQ and all four Orchestria workstations working out of the box with zero bugs.**
> **Goal:** Guide the user through a single, effortless, bug-free first-run setup flow (with native OS permission dialogs—Touch ID on macOS, UAC / Windows Hello on Windows, and zero prompts on Linux), notify cleanly if a one-time OS restart is required, and deliver zero-dot / zero-echo System-Wide EQ everywhere.

---

## 1. Executive Summary & Guided First-Run Philosophy

Unlike single-app players such as Phaenna (which delegate playback and EQ to an external `mpv` process and only process audio inside that app), Orchestria ships a pure-Rust 64-bit DSP engine (`cpal` + `symphonia` + `rustfft` + biquad EQ + DAC mimicker + brickwall limiter) designed to equalize **both** Orchestria's internal workstations **and** all desktop audio system-wide (Spotify, YouTube in browsers, Apple Music, games, Discord) at ~5–20 ms latency.

To make installing and running Orchestria effortless for **every** user on **macOS, Windows, and Linux**:

1. **Assume System-Wide EQ is wanted by default:** Do not hide System-Wide EQ behind manual terminal commands or obscure settings. Treat complete System-Wide Sound Engine readiness as the default first-run path.
2. **Guided Pre-Flight Onboarding Gate (Zero Half-Configured States):** As soon as a user installs and launches Orchestria for the first time (or after a driver-version upgrade), Orchestria runs a guided, non-blocking pre-flight setup gate that configures and verifies **everything** before entering the main workstations:
   - **System-Wide Sound Engine** (Zero-Dot HAL v2 + SHM on macOS; Zero-Echo Virtual Audio Endpoint on Windows; Zero-Echo User-Space PipeWire/PulseAudio Null Sink on Linux).
   - **Media Harvesting & Decoding Tools** (`yt-dlp` + `ffmpeg` auto-bootstrapped into Orchestria's isolated tools directory if absent from `PATH`).
   - **Live Audio-Path & Routing Self-Test** (confirms virtual endpoint registration, capture stream health, physical transducer detection/unmute, and sample-rate lock).
3. **Clear "One-Time Restart Required" Handling:** If the OS completes driver registration only after a reboot (for example, Windows returning exit code `3010` / `ERROR_SUCCESS_REBOOT_REQUIRED`, or a rare macOS `coreaudiod` cache case), Orchestria notifies the user clearly with `[R] Restart Now` or `[Q] Restart Later`—and once restarted, Orchestria verifies green automatically and opens directly into the workstations with **nothing else to configure**.
4. **Zero Orange Mic Dot (macOS) & Zero `[X]` Bugs:** Redesign macOS desktop capture from CoreAudio input loopback to an **Output-Only HAL v2 + POSIX Shared Memory (`/orchestria_audio_shm`)** design, and fix the `AudioStreamer` state machine and physical output device enumeration across all OSes.

---

## 2. Root-Cause Bug Investigation (Verified in Codebase)

### Bug 1 — Why the Orange Microphone Dot Appears on macOS (`OrchestriaAudio.c`, `streamer.rs`)
- **Where:** `drivers/orchestria_hal/OrchestriaAudio.h:25-26`, `drivers/orchestria_hal/OrchestriaAudio.c:1013-1070`, `src/dsp/streamer.rs:678`
- **Mechanism:**
  - `OrchestriaAudio.driver` currently registers both `kObjectID_Stream_Output` (ID `3`) and `kObjectID_Stream_Input` (ID `4`), and `Driver_WillDoIOOperation` / `Driver_DoIOOperation` implement both `WriteMix` and `ReadInput`.
  - To pull system audio into Rust, `AudioStreamer::build_input_stream_internal()` (`src/dsp/streamer.rs:678`) opens `in_d.build_input_stream(...)` via `cpal`.
  - Even though `find_devices()` (`src/dsp/streamer.rs:500-534`) excludes physical microphones (`!n.contains("mic")`), macOS (`micactivityd` + TCC) flags **every** active CoreAudio input stream with the orange microphone indicator and triggers the `"orchestria would like to access the microphone"` prompt.

### Bug 2 — Startup / State Contradiction (`streamer.rs:256` vs `975-1044` & `823-828`)
- **Where:** `src/dsp/streamer.rs:256`, `src/dsp/streamer.rs:975-1044`, `src/dsp/streamer.rs:823-828`, `src/ui/app.rs:194`
- **Mechanism:**
  - `AudioStreamer::new()` initializes `input_capture_enabled` to **`false`** (`streamer.rs:256`).
  - `App::new()` immediately calls `streamer.start()` (`app.rs:194`).
  - Inside `AudioStreamer::start()` (`streamer.rs:975-1044`), the code **never checks `self.input_capture_enabled`**:
    - Lines `975-997` unconditionally switch macOS default output to `Orchestria Audio` (or `BlackHole`).
    - Line `1043` unconditionally opens `self.build_input_stream_internal()`, lighting the orange dot while `is_input_capture_enabled()` still reports `false`.
  - Pressing `X` once flips `false -> true` (the dot stays ON); pressing `X` again flips `true -> false`. Worse, `poll_health()` watchdog restarts (`streamer.rs:823-828`) call `self.restart()` -> `self.start()`, silently re-hijacking macOS output and re-opening the input stream.

### Bug 3 — Why Pressing `[X]` Turns Off Sound or Switches to the Device Default Driver (`streamer.rs:727-747`, `148-156`, `360-399`)
- **Where:** `src/dsp/streamer.rs:727-747`, `src/dsp/streamer.rs:453-458`, `src/dsp/streamer.rs:148-156`, `src/dsp/streamer.rs:360-399`
- **Mechanism:**
  1. In v1, `input_stream` is the **only** drain moving audio out of `OrchestriaAudio.driver`'s RAM buffer to physical speakers. Dropping it in `set_input_capture(false)` (`streamer.rs:730-747`) turns `Orchestria Audio` into an unread silent black hole.
  2. To avoid silence, lines `739-743` switch macOS's default output back via `physical_output_device_id().or(saved_physical_output_id)`, falling back to `set_macos_system_output_to_hardware()` (`streamer.rs:148-156`), which **only checks 4 hardcoded substrings**: `"ibasso"`, `"dac"`, `"headphone"`, `"speaker"` (likewise `available_output_names()` at `streamer.rs:374` uses a 5-keyword filter).
  3. **Two failure modes:**
     - **Total silence:** On AirPods / Bluetooth headsets, DisplayPort/HDMI monitors, or USB DACs whose names omit those substrings (when `saved_physical_output_id` is `None`), `set_macos_system_output_to_hardware()` returns `Err(...)`, silently ignored by `let _ = ...`—leaving macOS routed to the unread `Orchestria Audio` buffer.
     - **EQ bypass:** When hardware restoration succeeds, desktop apps route straight to the physical device driver and bypass Orchestria's DSP completely.

### Bug 4 — `curl | bash` Installer Breaks on Interactive `sudo` (`scripts/install.sh:110-114`)
- **Where:** `scripts/install.sh:110-114`, `src/driver/mod.rs:420-454`
- **Mechanism:** Under `curl -fsSL .../install.sh | bash`, `stdin` is bound to the curl pipe instead of a TTY, so calling `orchestria driver install` (which spawns terminal `sudo` at `driver/mod.rs:420`) fails when prompting for a password.

### Bug 5 — Homebrew Formula Drops the HAL Driver (`Formula/orchestria.rb`, `src/driver/bundle.rs`)
- **Where:** `.github/workflows/release.yml:68-70`, `Formula/orchestria.rb:23-25`, `src/driver/bundle.rs:19-36`
- **Mechanism:** CI builds and ships `OrchestriaAudio.driver` inside the macOS tarball, but `Formula/orchestria.rb:24` only runs `bin.install "orchestria"` and discards the driver bundle. Meanwhile `locate_driver_source()` (`bundle.rs:19-36`) does not canonicalize Homebrew symlinks or check `../share/orchestria/OrchestriaAudio.driver` / `../libexec/`.

### Bug 6 — Blocking UI Elevation, Redundant `sudo` & Stale Updater Driver (`src/driver/mod.rs`, `src/ui/setup_modal.rs`, `src/harvest/updater.rs`)
- **Where:** `src/driver/mod.rs:458-480`, `src/ui/setup_modal.rs:54-64,120-135`, `src/harvest/updater.rs:247-290`
- **Mechanism:**
  - `install_driver_gui()` (`driver/mod.rs:458-472`) runs `osascript ... with administrator privileges` (already UID 0) invoking `orchestria driver install`, which redundantly calls `sudo` (`driver/mod.rs:420,446,452`), omits a user-friendly `with prompt "..."`, and executes synchronously on the TUI thread (`setup_modal.rs:123`), freezing the UI.
  - `check_driver_status()` (`setup_modal.rs:57`) checks only `.exists()` without comparing `CFBundleVersion` (so v1 loopback drivers are never flagged for v2 upgrade).
  - After elevation succeeds, `app.rs` never hot-restarts `AudioStreamer`, forcing users to quit and reopen Orchestria.
  - `apply_self_update()` (`updater.rs:247-290`) atomically replaces only the `orchestria` executable and discards the shipped `OrchestriaAudio.driver` from the release archive.

### Bug 7 — Windows Audio Stubbed Out & Plain WASAPI Loopback Echo Trap (`src/dsp/streamer.rs`, `src/driver/mod.rs`, `scripts/install.ps1`)
- **Where:** `src/dsp/streamer.rs:320-323, 360-364, 488-491`, `src/driver/mod.rs:569-573`, `scripts/install.ps1:64`
- **Mechanism:**
  - Under `#[cfg(target_os = "windows")]`, `available_input_names()` returns only the Unix IPC socket string (`streamer.rs:322`), `available_output_names()` returns a placeholder `"Default Audio Output"` (`streamer.rs:363`), and `find_devices()` immediately returns **`(None, None)`** (`streamer.rs:488-491`)—so **audio playback and DSP fail completely on Windows** (`"No output playback device found"` at `streamer.rs:972`).
  - Furthermore, existing comments/stubs (`src/driver/mod.rs:571`, `PACKAGING_BUNDLING_AND_CROSS_PLATFORM_DRIVER_INVESTIGATION.md:68-71`) assume plain **WASAPI Loopback (`AUDCLNT_STREAMFLAGS_LOOPBACK`)** provides driverless System-Wide EQ.
  - **Why plain WASAPI Loopback causes a fatal echo bug:** WASAPI Loopback captures audio **already mixing into the physical speaker endpoint**. If Orchestria captures from `Speakers (Loopback)`, applies EQ, and outputs the EQ'd audio back to `Speakers`:
    1. The user hears **both** the un-EQ'd original desktop audio AND the delayed EQ'd Orchestria stream (**double audio / comb-filter echo**), OR
    2. Capturing the same endpoint Orchestria outputs to creates an **infinite feedback loop**.
  - True, echo-free System-Wide EQ on Windows requires routing Windows default audio into an isolated **virtual audio sink** (or inline APO), capturing only from that sink, and outputting the EQ'd audio to the physical speakers/DAC.

### Bug 8 — Linux Monitor Loopback Echo Trap
- **Where:** `src/dsp/streamer.rs:324-399, 492-583`, `src/driver/mod.rs:569-578`
- **Mechanism:**
  - `available_input_names()` (`streamer.rs:334`) filters only for `"orchestria"` or `"blackhole"`, ignoring PipeWire/PulseAudio monitor sources.
  - Even if pointed at `<physical_sink>.monitor` directly (as suggested in older docs), reading `<physical_sink>.monitor` while writing EQ'd audio back to `<physical_sink>` causes the exact same **double-audio / feedback echo** as Windows unless desktop audio is first isolated onto a user-space virtual sink (`Orchestria_Audio`).

---

## 3. Part 1 — Design Sketch: macOS Zero-Dot Sound Engine (Output-Only HAL v2 + POSIX SHM)

### Why This Eliminates the Orange Dot Permanently
Inspection of macOS's CoreAudio daemon sandbox profile (`/System/Library/Sandbox/Profiles/com.apple.audio.coreaudiod.sb`, line `141`) confirms:
```scheme
(allow ipc-posix-shm)
```
`coreaudiod` explicitly permits POSIX shared memory (`shm_open` + `mmap`).

By dropping `kObjectID_Stream_Input` from `OrchestriaAudio.driver` (making it an **Output-Only HAL Virtual Device**) and reading PCM frames from POSIX shared memory instead of `cpal::build_input_stream`:
- macOS recognizes `Orchestria Audio` strictly as an **Output** device—never as a microphone.
- `orchestria` opens **zero CoreAudio input streams** → `micactivityd` never fires → **zero orange dot, zero Microphone TCC prompt, and full system-wide EQ across every macOS app**.

### Audio Data Flow (macOS v2 Zero-Dot)

```text
+-----------------------------------------------------------------------------+
| macOS Desktop Apps (YouTube, Spotify, Apple Music, Games, System Audio)     |
+--------------------------------------+--------------------------------------+
                                       | CoreAudio Default Output
                                       v
+-----------------------------------------------------------------------------+
| OrchestriaAudio.driver v2 (Output-Only HAL Plug-In inside coreaudiod)          |
|  * Exposes ONLY Output Stream (kObjectID_Stream_Output = 3)                 |
|  * NO Input Stream -> macOS NEVER flags it as a microphone                  |
|  * WriteMix copies unity-gain PCM + atomic volume/mute state into SHM       |
+--------------------------------------+--------------------------------------+
                                       | POSIX Shared Memory (/orchestria_audio_shm)
                                       | (_coreaudiod writes RW; fchmod 0644)
                                       v
+-----------------------------------------------------------------------------+
| Orchestria Pure-Rust Sound Engine (User Space)                                 |
|  * ShmCaptureReader (O_RDONLY / PROT_READ, lock-free acquire/release load)  |
|  * Feeds ServoWriter -> ServoReader PLL (drift compensation)                |
|  * Mixes with TrackPlayer (Symphonia local/cloud stream player)             |
|  * 64-Bit AudioPipeline: Preamp -> DAC Mimic -> 10-Band EQ -> Limiter -> FFT|
+--------------------------------------+--------------------------------------+
                                       | cpal Output Stream ONLY
                                       v
+-----------------------------------------------------------------------------+
| Physical Output Hardware (Speakers, Headphone Jack, USB DAC, AirPods/BT)    |
+-----------------------------------------------------------------------------+
```

### Shared Memory Ring Buffer Contract (`OrchestriaShmRing`)

Shared object name: **`/orchestria_audio_shm`** (18 characters, safely under macOS's 31-character `PSHMNAMLEN`).

```c
#define ORCHESTRIA_SHM_NAME    "/orchestria_audio_shm"
#define ORCHESTRIA_SHM_MAGIC   0x4F4D5348u  // "OMSH"
#define ORCHESTRIA_SHM_VERSION 2u
#define ORCHESTRIA_SHM_FRAMES  32768u       // power of two (~682 ms at 48 kHz)

typedef struct __attribute__((aligned(64))) OrchestriaShmRing {
    uint32_t         magic;            // ORCHESTRIA_SHM_MAGIC
    uint32_t         version;          // ORCHESTRIA_SHM_VERSION
    uint32_t         channels;         // 2 (interleaved stereo f32)
    uint32_t         capacity_frames;  // 32768
    _Atomic uint32_t sample_rate_hz;   // 48000 / 96000 / 192000
    _Atomic uint32_t volume_bits;      // IEEE-754 f32 bits of CoreAudio output volume
    _Atomic uint32_t is_muted;         // 0 or 1
    _Atomic uint32_t io_running;       // 1 while IO active, 0 when idle
    _Atomic uint64_t write_cursor;     // monotonic frame counter (release store / acquire load)
    _Atomic uint64_t heartbeat_ns;     // mach_absolute_time / monotonic timestamp
    uint8_t          _pad[16];
    float            frames[ORCHESTRIA_SHM_FRAMES * 2]; // unity-gain PCM from WriteMix
} OrchestriaShmRing;
```

- **Permissions:** Driver runs `shm_open(..., O_CREAT | O_RDWR, 0644)` followed immediately by `fchmod(fd, 0644)` so `_coreaudiod`'s `umask` cannot block user-space `O_RDONLY` / `PROT_READ` mapping.
- **Unity-gain PCM + clean volume parity:** Eliminates the v1 `1.0 / in_vol` noise-floor amplification hack (`streamer.rs:698-703`); driver writes raw unity-gain PCM and mirrors `volume_bits`/`is_muted` atomically.
- **Clean idle silence:** When `io_running == 0` or `heartbeat_ns` goes stale (>25 ms), `ShmCaptureReader` emits zeros instead of looping stale samples.

---

## 4. Part 2 — Cross-Platform Zero-Echo Sound Engine (Windows & Linux Fixes)

### A. Windows Zero-Echo System-Wide EQ Architecture (`src/dsp/streamer.rs`, `src/driver/windows.rs`)

```text
+-----------------------------------------------------------------------------+
| Windows Apps (Spotify, Chrome/Edge, Games, System Audio)                    |
+--------------------------------------+--------------------------------------+
                                       | Windows Default Playback Endpoint
                                       v
+-----------------------------------------------------------------------------+
| Orchestria Virtual Audio Endpoint (Pre-Signed / WHQL Virtual Render+Loopback)  |
|  * Installed 1-time via native UAC / Windows Hello sheet                    |
|  * Default Output switched via IPolicyConfig COM (physical device saved)    |
+--------------------------------------+--------------------------------------+
                                       | WASAPI Loopback Capture (Isolated Sink!)
                                       | (NO physical speaker audio in this mix!)
                                       v
+-----------------------------------------------------------------------------+
| Orchestria Pure-Rust Sound Engine (WASAPI Exclusive/Shared -> 64-Bit DSP)      |
+--------------------------------------+--------------------------------------+
                                       | cpal WASAPI Output Stream
                                       v
+-----------------------------------------------------------------------------+
| Physical Transducer (Realtek Speakers, USB DAC, Headphones, Bluetooth)      |
+-----------------------------------------------------------------------------+
```

1. **Un-stub `cpal` WASAPI Device Discovery (`src/dsp/streamer.rs:320,361,488-491`):**
   - Remove the early `#[cfg(target_os = "windows")] return (None, None)` and placeholder strings.
   - Enumerate all real WASAPI render endpoints via `cpal::default_host().output_devices()` (excluding virtual endpoints like `"Orchestria Virtual"` / `"VB-Cable"` when choosing the physical transducer target) and enumerate WASAPI loopback/capture endpoints cleanly.
2. **Eliminate the Echo Bug via Isolated Virtual Endpoint + `IPolicyConfig`:**
   - Why **not** a brand-new unsigned kernel WDM driver? On Windows 10/11 with Secure Boot enabled, custom kernel-mode `.sys` audio drivers require an **EV Code Signing Certificate + Microsoft WHQL Hardware Dev Center attestation**, or Windows refuses to load them.
   - **Shipping automated path:** Bundle/bootstrap a **pre-signed virtual audio driver package** (e.g., WHQL-signed virtual audio cable/endpoint) alongside `orchestria.exe`, installed silently via **one native Windows UAC prompt** (`ShellExecuteW("runas")` / `pnputil /add-driver ... /install`).
   - **Automatic Default-Device Handoff (`IPolicyConfig` COM):**
     - On System-Wide EQ start, Orchestria queries the current default Windows render endpoint (`IMMDeviceEnumerator::GetDefaultAudioEndpoint`), persists its device ID (`saved_physical_output_id`), and switches Windows' default render endpoint to `"Orchestria Virtual Audio"` via `IPolicyConfig::SetDefaultEndpoint`.
     - Orchestria captures from the virtual endpoint (WASAPI loopback on that virtual sink or its paired capture pin), processes through `AudioPipeline`, and outputs strictly to the saved physical device—**100% echo-free**.
     - On `[X]` toggle OFF, exit, or panic hook, `restore_system_output()` restores the saved physical endpoint ID immediately (never stranding Windows on the virtual sink).
   - **Future option (APO inline):** An `IAudioProcessingObject` COM DLL injected into `audiodg.exe` (like EqualizerAPO) avoids routing changes entirely, but requires per-device registry FX registration and breaks on Windows driver updates; the isolated virtual endpoint + `IPolicyConfig` design is cleaner and self-healing across USB DAC / Bluetooth plug-unplug events.
3. **Smart Reboot Detection on Windows:**
   - After silent driver installation (`pnputil` / installer MSI/EXE), Orchestria checks the exit code and restarts `Audiosrv` if needed, polling up to 5s for the virtual endpoint in WASAPI.
   - If the installer returns exit code **`3010` (`ERROR_SUCCESS_REBOOT_REQUIRED`)** or the endpoint has not registered after service refresh, Orchestria transitions cleanly into the **One-Time Restart Required** screen (see §5).

### B. Linux Zero-Echo System-Wide EQ Architecture (`src/driver/linux.rs`, `src/dsp/streamer.rs`)

- **Zero `sudo`, Zero Driver Install, Zero Reboot:** Modern Linux desktops run **PipeWire** (with `pipewire-pulse`) or **PulseAudio**, both of which allow user-space virtual sinks without administrator privileges.
- **Echo-Free Routing Flow:**
  1. Detect physical default sink (e.g. `pactl get-default-sink`), persist it, and verify it is not already `Orchestria_Audio`.
  2. Create a user-space virtual sink (`Orchestria_Audio`) via `pactl load-module module-null-sink sink_name=Orchestria_Audio sink_properties=device.description="Orchestria Audio"` (stored module ID for clean teardown).
  3. Set `Orchestria_Audio` as the default sink (`pactl set-default-sink Orchestria_Audio`) and move active audio streams if needed.
  4. Orchestria captures `Orchestria_Audio.monitor` (which contains **only** desktop apps, never Orchestria's own output) → 64-bit `AudioPipeline` → outputs via `cpal` directly to the saved physical sink (`alsa_output...` / Bluetooth / USB DAC).
  5. On `[X]` toggle OFF, exit, or panic, Orchestria restores the saved physical sink and runs `pactl unload-module <id>`.

### C. Unified `[X]` Toggle & Full Physical Device Discovery (All OSes)
- Replace the 4-keyword `set_macos_system_output_to_hardware()` (`streamer.rs:148-156`) and 5-keyword `available_output_names()` (`streamer.rs:374`) with real device enumeration across **all physical outputs** (Built-in Speakers, 3.5mm Headphones, AirPods/Bluetooth, HDMI/DisplayPort, USB DACs) while excluding virtual devices (`orchestria`, `blackhole`, `soundflower`, `loopback`, `vb-cable`).
- Both `AudioStreamer::start()` and `poll_health()` strictly honor `system_capture_enabled` and preserve user preferences across sleep/wake or DAC reconnects.
- Pressing `X` cleanly toggles between **System-Wide EQ (`ON`)** and **Direct Hardware (`App-Only EQ`)** without ever causing silence or losing EQ inside Workstation 4.

---

## 5. Part 3 — Guided First-Run Onboarding Gate & Native OS Permission Pipeline

### Cross-Platform Authorization & Reboot Matrix

| Platform | Admin Needed? | Native Authorization Popup | What Happens After "Yes" | Restart Needed? |
| :--- | :--- | :--- | :--- | :--- |
| **macOS** | **Yes (1-time)** for `/Library/Audio/Plug-Ins/HAL/` | `osascript` `do shell script ... with prompt "..." with administrator privileges` → **Touch ID / Apple Watch / Password** | Copies HAL v2 bundle, sets `root:wheel`, clears quarantine, runs `launchctl kickstart -k system/com.apple.audio.coreaudiod`, maps `/orchestria_audio_shm`, hot-activates live | **No** (99% instant live activation; fallback restart screen only if CoreAudio stalls) |
| **Windows** | **Yes (1-time)** for virtual audio endpoint | `ShellExecuteW("runas")` / PowerShell `-Verb RunAs` → **Windows UAC (Yes / Windows Hello Face, Fingerprint, PIN)** | Silently installs signed virtual endpoint driver, refreshes `Audiosrv`, polls WASAPI; detects exit code `3010` if reboot needed | **Only if Windows returns `3010`** (explicit Restart screen; after reboot opens straight into Orchestria) |
| **Linux** | **No (0 prompts)** | None (`pactl` / PipeWire user-space sink; optional `pkexec` Polkit popup only if user asks to auto-install missing system tools) | Creates `Orchestria_Audio` null sink in user space, verifies `Orchestria_Audio.monitor`, hot-activates live | **No** (always instant) |

### Full-Setup Guided Gatekeeper Flow (TUI Wireframes)

Instead of dropping new users into a half-configured app, launching `orchestria` on an unconfigured machine opens the **Full Setup & Verification Gate** automatically (and remembers completion in `~/.config/orchestria/setup_state.json`, re-checking whenever the binary or driver version advances):

#### Screen 1 — Guided First-Run Gate (Everything Verified Before First Use)

```text
+------------------------------------------------------------------------------+
|                   ORCHESTRIA FIRST-RUN SETUP & PRE-FLIGHT CHECK                 |
+------------------------------------------------------------------------------+
|                                                                              |
|  Welcome to Orchestria! Let's finish setting up your System-Wide Sound Engine   |
|  and media tools so every feature works properly on your first launch:       |
|                                                                              |
|   [!] 1. System-Wide Sound Engine  : Not installed (macOS HAL v2 Zero-Dot)  |
|   [!] 2. Media Tools (yt-dlp/ffmpeg): Missing yt-dlp (auto-download ready)   |
|   [ ] 3. Audio Routing & Self-Test  : Pending driver setup                   |
|                                                                              |
|  When prompted by your OS, simply click Allow / Yes and authenticate with    |
|  Touch ID, Windows Hello, or your system password.                           |
|                                                                              |
|  --------------------------------------------------------------------------  |
|   [Enter] Set Up Everything Automatically (Recommended)                      |
|   [L]     Use App-Only Mode (No system audio EQ; for locked/work PCs)        |
|                                                                              |
+------------------------------------------------------------------------------+
```

#### Screen 2 — Live Non-Blocking Setup Execution (`mpsc` Background Worker)

```text
+------------------------------------------------------------------------------+
|                   CONFIGURING ORCHESTRIA SYSTEM-WIDE ENGINE...                  |
+------------------------------------------------------------------------------+
|                                                                              |
|   [x] 1. Staged OrchestriaAudio.driver v2.0 bundle                              |
|   [x] 2. Downloaded yt-dlp & verified ffmpeg in ~/.local/share/orchestria/bin   |
|   [>] 3. Waiting for OS permission (Touch ID / UAC / Password)...            |
|   [ ] 4. Refreshing audio service & running live routing self-test           |
|                                                                              |
|   Status: Approve the native macOS/Windows dialog to continue.               |
|                                                                              |
+------------------------------------------------------------------------------+
```

#### Screen 3A — Ready Immediately (macOS / Linux / Live-Loaded Windows)

```text
+------------------------------------------------------------------------------+
|                       ORCHESTRIA READY — ALL SYSTEMS GREEN                      |
+------------------------------------------------------------------------------+
|                                                                              |
|   [x] Sound Engine     : Orchestria Audio v2 (Zero-Dot SHM / Zero-Echo) ACTIVE  |
|   [x] Physical Output  : MacBook Pro Speakers (48,000 Hz • Unmuted)          |
|   [x] Media Pipeline   : yt-dlp + ffmpeg verified                            |
|   [x] Routing Check    : Desktop audio -> 64-bit DSP -> Speakers (OK)        |
|                                                                              |
|   No restart needed. You're ready to use all 4 Orchestria workstations.         |
|                                                                              |
|                      [Enter] Launch Orchestria Now                              |
|                                                                              |
+------------------------------------------------------------------------------+
```

#### Screen 3B — One-Time Restart Required (Windows `3010` / Pending Driver Registration)

```text
+------------------------------------------------------------------------------+
|                 SETUP COMPLETE — ONE-TIME RESTART REQUIRED                   |
+------------------------------------------------------------------------------+
|                                                                              |
|   [x] Driver Installed : Orchestria Virtual Audio Endpoint                      |
|   [x] Media Pipeline   : yt-dlp + ffmpeg verified                            |
|   [!] Activation State : Waiting on OS kernel/audio service reboot (3010)    |
|                                                                              |
|   Everything else is finished! Please restart your computer once so the OS   |
|   activates the new audio device. After rebooting, just run `orchestria` and    |
|   System-Wide EQ will start automatically with nothing else to configure.    |
|                                                                              |
|         [R] Restart Computer Now       [Q] Save & I'll Restart Later         |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Installer Entry Points (Zero Terminal `sudo` Traps)
- **macOS (`scripts/install.sh`, `scripts/install.command`, `Formula/orchestria.rb`):**
  - `Formula/orchestria.rb` installs `bin.install "orchestria"` AND `pkgshare.install "OrchestriaAudio.driver"`; `src/driver/bundle.rs` canonicalizes `current_exe()` and searches sibling binary dir, `../share/orchestria/`, and `../libexec/`.
  - `install.sh` / `install.command` copy both binary + driver bundle, strip `com.apple.quarantine`, and **never call raw terminal `sudo`** when stdin is piped (`curl ... | bash`). If a macOS desktop session is active, they can either launch `orchestria` directly into the First-Run Gate or invoke `orchestria driver install-gui` (native Touch ID sheet) immediately after copy-paste.
- **Windows (`scripts/install.ps1`):**
  - Downloads verified zip to `%LOCALAPPDATA%\Programs\Orchestria`, bundles the signed virtual audio driver installer package + `ffmpeg`/`yt-dlp` bootstrap config, adds `%LOCALAPPDATA%\Programs\Orchestria` to User `PATH`, and prints a clean prompt to run `orchestria` (or launches Orchestria's guided first-run setup immediately, which triggers the single UAC/Windows Hello prompt and handles `3010` reboot notification if required).
- **In-App Updater (`src/harvest/updater.rs`):**
  - Extracts `OrchestriaAudio.driver` (macOS) / Windows driver package alongside the updated binary during `:update`, compares installed driver version (`CFBundleVersion` / Windows driver version) against bundled version, and re-opens the guided gate if a driver upgrade is available.

---

## 6. Phased Implementation Roadmap & File Touch List

| Phase | Scope | Files Modified / Added |
| :--- | :--- | :--- |
| **Phase 1: Routing State Machine & Full Output Discovery** | Fix `input_capture_enabled` vs `start()` mismatch, guard `poll_health()`, replace hardcoded 4/5-keyword output filters with real physical device enumeration across all transducers (AirPods, BT, HDMI, USB DAC, Speakers), and keep Workstation 4 DSP live when system capture is off. | `src/dsp/streamer.rs`, `src/driver/mod.rs`, `src/ui/app.rs` |
| **Phase 2: macOS Zero-Dot Output-Only HAL v2 + POSIX SHM** | Remove `kObjectID_Stream_Input` from HAL driver, implement `OrchestriaShmRing` (`fchmod` `0644`, unity-gain PCM + atomic volume/mute), bump `CFBundleVersion` to `2`, and implement Rust `ShmCaptureReader` + `CaptureBackend` selector. | `drivers/orchestria_hal/OrchestriaAudio.h`, `drivers/orchestria_hal/OrchestriaAudio.c`, `drivers/orchestria_hal/Info.plist`, `src/dsp/shm_capture.rs` (new), `src/dsp/mod.rs`, `src/dsp/streamer.rs` |
| **Phase 3: Windows & Linux Zero-Echo System-Wide Audio** | Un-stub Windows WASAPI in `streamer.rs`; implement `windows.rs` (signed virtual endpoint UAC installer, `IPolicyConfig` default-device switch & crash-safe restore, `Audiosrv` refresh, `3010` reboot detection); implement `linux.rs` (`Orchestria_Audio` PipeWire/PulseAudio user-space null-sink + monitor capture + clean unload). | `src/dsp/streamer.rs`, `src/driver/mod.rs`, `src/driver/windows.rs` (new), `src/driver/linux.rs` (new) |
| **Phase 4: Guided First-Run Pre-Flight Gate & Smart Restart UX** | Turn `SetupModalState` into a full guided first-run onboarding gate (auto-trigger on missing/outdated setup, parallel `yt-dlp` + `ffmpeg` bootstrap, non-blocking `mpsc` native OS auth runner, audio-path self-test, hot-activation, and `3010` Restart Now/Later flow + persistent `setup_state.json`). | `src/ui/setup_modal.rs`, `src/ui/app.rs`, `src/harvest/bootstrap.rs`, `src/driver/bundle.rs`, `src/main.rs` |
| **Phase 5: Seamless Installers, Homebrew & Updater** | Ship HAL driver in `Formula/orchestria.rb` `pkgshare`, canonicalize symlink lookup in `bundle.rs`, remove piped-stdin `sudo` from `install.sh`, update `install.ps1` + `.github/workflows/release.yml` for Windows driver packaging, and stage driver updates in `updater.rs`. | `Formula/orchestria.rb`, `scripts/install.sh`, `scripts/install.command`, `scripts/install.ps1`, `src/harvest/updater.rs`, `.github/workflows/release.yml` |

---

## 7. Verification Plan

1. **Automated Unit & Integration Tests (`cargo test`)**
   - `ShmRing` ABI layout, wraparound, and overrun recovery tests (`src/dsp/shm_capture.rs`).
   - `AudioStreamer` state-machine tests: `start()` and `poll_health()` strictly honor capture toggle; physical output discovery enumerates Bluetooth/AirPods/Display/USB devices without keyword blind spots; Windows WASAPI discovery no longer returns empty `(None, None)`.
   - `bundle::locate_driver_source` tests for symlinked Homebrew Cellar (`../share/orchestria/`, `../libexec/`).
   - `SetupModalState` state-transition tests: first-run trigger, v1→v2 upgrade detection, `3010` reboot-required state persistence, and `Ready` state post-reboot.
2. **macOS Live Verification**
   - Universal HAL build (`make -C drivers/orchestria_hal`), `codesign -v`, `CFBundleVersion == 2`, System Settings → Sound shows `Orchestria Audio` **only under Output**.
   - Play YouTube + Spotify desktop with EQ active → **zero orange dot** and **zero microphone TCC prompt**; verify `[X]` switches cleanly across Speakers, AirPods, and USB DAC without silence; verify `curl | bash`, Homebrew, and Touch ID hot-activation without app restart.
3. **Windows Live Verification**
   - Run `install.ps1` → launch `orchestria` → guided setup triggers 1 UAC / Windows Hello prompt → confirm isolated virtual sink switches via `IPolicyConfig` and plays **echo-free** EQ'd desktop audio to physical speakers/DAC.
   - Verify `3010` path triggers the **One-Time Restart Required** screen and post-reboot launch verifies green and opens straight into Orchestria.
4. **Linux Live Verification**
   - On PipeWire and PulseAudio sessions, launch `orchestria` → guided setup finishes with **0 prompts and 0 reboots** → confirm `Orchestria_Audio` null sink + `.monitor` delivers **echo-free** desktop EQ and restores original default sink cleanly on `[X]` or quit.

---

## 8. Key Risks & Mitigations

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| **Windows Secure Boot blocks unsigned virtual audio drivers** | Driver installation fails or refuses to load | Only ship/bootstrap a **WHQL / EV-signed virtual audio endpoint** package; verify signature before `pnputil` and fall back gracefully to App-Only EQ with clear explanation if blocked by corporate Group Policy. |
| **`_coreaudiod` `umask` strips world-read bit on `shm_open`** | macOS user-space `orchestria` gets `EACCES` on `/orchestria_audio_shm` | Driver calls `fchmod(fd, 0644)` explicitly right after `shm_open`; Rust checks `EACCES` and degrades gracefully instead of panicking. |
| **Apple restricts `ipc-posix-shm` in a future macOS `coreaudiod.sb`** | SHM reader cannot connect | Keep `CaptureBackend` modular so Tier 2 loopback or macOS 14.2+ `AudioHardwareCreateProcessTap` can slot in cleanly. |
| **App crash leaves macOS/Windows/Linux default output on virtual device** | Desktop audio plays into an unread sink until manually switched | Harden `restore_system_output()` in panic hook, `Drop`, and `[X]` OFF across all 3 OSes using full physical output enumeration so a valid physical device is always restored. |
| **Gatekeeper / SmartScreen blocks downloaded binaries or drivers** | OS refuses launch or driver load | Strip `com.apple.quarantine` in macOS installers/updater and verify SHA-256 + Minisign checksums; plan Developer ID notarization (macOS) + Authenticode signing (Windows) in release CI. |
