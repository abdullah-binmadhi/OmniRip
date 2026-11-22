# OmniRip: Rolling Auto-Update & Plain-English "What's New" Popup Plan

> **Goal:** Every time you push to `main` on GitHub and `.github/workflows/ci.yml` passes all tests across macOS, Linux, and Windows, GitHub Actions automatically builds and publishes the updated release—and every OmniRip user receives an automatic, non-blocking update notification with a super-simple, jargon-free summary of what was added or fixed, then clicks one key to update and restart directly into the new version.

---

## 1. Executive Summary & How This Improves on Phaenna

Phaenna already proves the core continuous-delivery pattern (`build.rs` baking `GIT_SHA` + `COMMIT_TS` paired with a rolling release tag in `.github/workflows/release.yml` and HTTP Range-resumed self-updates in `src/services/updater.rs`). For OmniRip, we adopt that proven core **and harden five critical areas** so the experience is even simpler, safer, and completely zero-jargon for everyday listeners:

| Capability | Phaenna Today | OmniRip Target Design |
| :--- | :--- | :--- |
| **Trigger on every `main` push** | `push: branches: [main]` + `tags: [v*]` | `push: branches: [main]` + `tags: [v*]`, strictly gated on `needs: test` (`ci.yml` passing 311+ tests on macOS, Linux, Windows) |
| **Release Notes Popup** | Shows raw GitHub commit body (`commit_msg`) | **Plain-English "What's New & Fixed" Translator**: strips technical jargon (`SHM`, `HAL`, `biquad`, `WASAPI`) into simple user benefits (`[NEW]`, `[FIXED]`, `[IMPROVED]`) |
| **Update Detection** | Background check + modal (`[U]`) | Non-blocking check **2s after launch** + **every 30 minutes**; shows subtle top-right pill if typing, or opens Update Popup when idle |
| **Restart Experience** | Exits process (`Enter` -> user manually types `phaenna`) | **True 1-Key Self-Restart (`execv` / Spawn Handoff)**: cleanly restores audio hardware & terminal, then re-launches the new OmniRip right in the same window |
| **Post-Update Confirmation** | None after restarting | **Post-Update Welcome Popup ("OmniRip Just Got Better!")** shown once after relaunch, plus automatic 1-click Touch ID prompt if `OmniRipAudio.driver` also upgraded |
| **Safety & Rollback** | Binary magic check + HTTP Range resume + codesign | Adds **automatic rollback backup** (`omnirip --rollback` / `:rollback`) + dual-tier integrity (`SHA256SUMS` always + Minisign when key is configured) |

---

## 2. Root-Cause Audit: Why OmniRip's Current Updater Doesn't Do This Today

Inspection of OmniRip's existing files confirms five concrete gaps:

1. **Gap 1 — Tag-Only Release Workflow (`.github/workflows/release.yml:3-6`):**
   - `release.yml` triggers **only** on `push: tags: ['v*']`. Normal `git commit && git push` to `main` runs tests in `ci.yml` but never builds or publishes a release.
2. **Gap 2 — SemVer-Only Comparison Without Build Git Metadata (`src/harvest/updater.rs:45-60, 114-116`):**
   - OmniRip has **no `build.rs`** baking `OMNIRIP_GIT_SHA` or `OMNIRIP_COMMIT_TS` at compile time.
   - `check_latest_release()` (`updater.rs:116`) only calls `is_newer_version(CARGO_PKG_VERSION, remote_tag)`. Commits pushed without bumping `0.2.0` in `Cargo.toml` are completely invisible to users.
3. **Gap 3 — Empty `UPDATE_PUBLIC_KEY` & Hard-Failing `MINISIGN_SECRET_KEY` (`src/harvest/updater.rs:143`, `.github/workflows/release.yml:112-115`):**
   - `UPDATE_PUBLIC_KEY` (`updater.rs:143`) is `""`, which causes `integrity::verify_minisign()` (`updater.rs:195`) to reject 100% of updates. Meanwhile `release.yml:113-116` aborts CI publishing if `MINISIGN_SECRET_KEY` is unset.
4. **Gap 4 — Manual-Only Update Checks (`src/ui/setup_modal.rs`, `src/ui/app.rs`):**
   - `check_latest_release()` is only called when the user manually types `:update` or presses `U` inside `F12` Setup Wizard—never automatically on launch or in the background.
5. **Gap 5 — Raw Technical Release Notes (`src/harvest/updater.rs:137`):**
   - `release_notes` passes raw GitHub release body text straight through without formatting or simplifying technical developer commit messages.

---

## 3. Part 1 — CI/CD Rolling Release Pipeline (`build.rs` + `.github/workflows/release.yml`)

### A. Compile-Time Build Provenance (`build.rs`)
Mirroring `phaenna/build.rs:1-60`, add a lightweight `build.rs` in the OmniRip root:
- Reads `GITHUB_SHA` (or `git rev-parse HEAD` locally) → emits `cargo:rustc-env=OMNIRIP_GIT_SHA=<40-char-sha>`.
- Reads `git show -s --format=%ct HEAD` → emits `cargo:rustc-env=OMNIRIP_COMMIT_TS=<unix_seconds>`.
- Watches `.git/HEAD`, the active branch ref, and `.git/packed-refs` via `cargo:rerun-if-changed=...` so every commit automatically rebakes fresh metadata without breaking offline/tarball builds (falling back safely to `"unknown"` / `"0"`).

### B. CI-Gated Rolling Workflow (`.github/workflows/release.yml`)
```text
git push origin main
        │
        ▼
  [1. CI Gate: .github/workflows/ci.yml]
   • macos-latest   -> cargo test --locked -- --test-threads=1
   • windows-latest -> cargo test --locked -- --test-threads=1
   • ubuntu-latest  -> cargo test --locked -- --test-threads=1
        │ (ALL 3 MUST PASS — zero broken updates ever shipped!)
        ▼
  [2. Build Matrix (4 Targets + HAL v2 Universal Driver)]
   • aarch64-apple-darwin + OmniRipAudio.driver (v2)
   • x86_64-apple-darwin  + OmniRipAudio.driver (v2)
   • x86_64-unknown-linux-gnu
   • x86_64-pc-windows-msvc
        │
        ▼
  [3. Publish Rolling Release (tag: v0.2.0-rolling, make_latest: true)]
   • Generates plain-English "What's New" bullets from commits since last rolling tag
   • Embeds hidden metadata markers + SHA256SUMS (+ optional Minisign signature)
   • Cancels stale in-flight builds if you push again rapidly (`cancel-in-progress: true`)
```

**Embedded Release Body Markers:**
```markdown
<!-- omnirip-sha:FULL_40_CHAR_GIT_SHA -->
<!-- omnirip-ts:UNIX_COMMIT_TIMESTAMP -->
<!-- omnirip-driver-ver:2 -->
<!-- omnirip-notes-start -->
[NEW] System-wide sound works cleanly on macOS with zero orange microphone dot.
[FIXED] Pressing X no longer mutes desktop sound when switching back to speakers or AirPods.
[IMPROVED] Guided setup now uses Touch ID / Windows Hello with no terminal commands.
<!-- omnirip-notes-end -->
```

### C. Rolling Update Decision Rules (`evaluate_release_update`)
An update is offered **only when ALL safety checks pass**:
1. Either **SemVer is strictly newer** (`v0.2.1 > 0.2.0`), **OR** the rolling tag has a **different `omnirip-sha`** AND `remote_ts >= local_ts` (so a newer local `cargo build` is **never** downgraded by an older CI release!).
2. A matching platform archive asset exists (`omnirip-macos-arm64.tar.gz`, `omnirip-macos-x86_64.tar.gz`, `omnirip-linux-x86_64.tar.gz`, or `omnirip-windows-x64.zip`).
3. **Dual-Tier Cryptographic Verification:**
   - **Always required:** Fetch `SHA256SUMS`, verify SHA-256 of the downloaded archive (`integrity::expected_sha256_for`), extract binary, verify `size >= 1_000_000` bytes, and verify native executable magic (`Mach-O` on macOS, `0x7F ELF` on Linux, `MZ` on Windows).
   - **Optional Minisign layer:** If `UPDATE_PUBLIC_KEY` is non-empty (and `SHA256SUMS.minisig` is present), verify the Minisign signature before trusting `SHA256SUMS`; if `UPDATE_PUBLIC_KEY` is empty during personal/dev distribution, verify `SHA256SUMS` + native binary magic without hard-blocking updates.

---

## 4. Part 2 — Plain-English "What's New" Translation Engine (Zero Jargon)

Every commit message you write is automatically converted into friendly, everyday language—no file paths, no function names, no acronyms like `SHM`, `HAL`, `WASAPI`, `biquad`, or `mutex`.

### Two-Tier Translation Pipeline (CI Release Step + Rust Client Fallback)

1. **Tier 1 — Optional Author Override (`Simple:` or `Note:` trailer in commit message):**
   - Whenever you want exact custom wording, add a line in your commit message body:
     ```text
     Simple: Fixed sound cutting out when unplugging AirPods.
     ```
   - The generator picks that exact sentence verbatim and tags it `[NEW]`, `[FIXED]`, or `[IMPROVED]`.
2. **Tier 2 — Automatic Jargon-to-Plain-English Mapper (for normal commits):**
   - Collects commits since the previous rolling SHA (`git log PREV_SHA..HEAD`), ignores `chore:`, `ci:`, `docs:`, and `test:` noise unless user-facing, strips conventional prefixes (`feat(audio):`), and maps technical keywords to clear user benefits:

| Commit Keywords / Subsystem | Technical Jargon (Hidden) | What the User Sees in the Popup |
| :--- | :--- | :--- |
| `shm`, `hal`, `orange dot`, `coreaudio` | POSIX SHM, `OmniRipAudio.driver`, `micactivityd` | `[IMPROVED] System-wide sound works smoothly on macOS without the orange mic dot.` |
| `input_capture`, `x key`, `loopback`, `airpods`, `bluetooth` | `set_input_capture`, `find_devices`, `CoreAudio` routing | `[FIXED] Switching sound on or off with X works cleanly with speakers, AirPods, and DACs.` |
| `wasapi`, `ipolicyconfig`, `windows`, `3010` | WASAPI COM, `pnputil`, `Audiosrv` | `[NEW] Added full Windows system sound support and smoother speaker switching.` |
| `pipewire`, `pulseaudio`, `pactl`, `null-sink` | `module-null-sink`, `.monitor` | `[NEW] Added clean, echo-free Linux system sound support with no password prompts.` |
| `biquad`, `eq`, `dac`, `enhancer`, `limiter`, `autoeq`, `gear` | SOS filters, R2R saturation, `sinc_interp_16` | `[IMPROVED] Refined sound quality, EQ tuning, and headphone calibration.` |
| `slskd`, `soulseek`, `nicotine`, `spectral`, `lossless` | P2P daemon, FFT brickwall cutoff | `[IMPROVED] Faster lossless music search and more reliable audio quality checks.` |
| `yt-dlp`, `ffmpeg`, `streaming_hub`, `playlist`, `archiver` | Stream resolver, demuxing, M3U8 | `[IMPROVED] More reliable music streaming, playlist importing, and downloads.` |
| `setup_modal`, `install`, `touch id`, `updater`, `rollback` | `osascript`, `execv`, `Range`, `SHA256SUMS` | `[IMPROVED] Easier first-time setup and faster, safer automatic updates.` |

- Caps the popup list at **5 clean, deduplicated bullets** (plus `"• ...and minor stability improvements"` if more commits exist) so the dialog is always scannable in 3 seconds.

### Example: Before vs. After
- **Raw git commit:** `feat(audio): zero-dot SHM HAL v2, cross-platform system EQ, and guided setup`
- **What OmniRip users actually read:**
  - `[NEW] Mac system sound now runs cleanly without triggering the orange microphone dot.`
  - `[NEW] Full Windows & Linux system-wide EQ support with echo-free routing.`
  - `[IMPROVED] Guided first-time setup with Touch ID / Windows Hello—no terminal commands needed.`

---

## 5. Part 3 — Non-Intrusive Auto-Update & Popup UX (`src/ui/update_modal.rs`)

### Background Detection Flow (`App::new` + `App::run`)
1. **Launch Check (2 seconds after startup, async Tokio task):** Queries GitHub Releases API (`timeout: 6s`) without slowing down audio or UI startup.
2. **Periodic Check (every 30 minutes):** Re-checks silently in the background while OmniRip is open.
3. **Smart Interruption Guard (`is_capturing_text_input()`):**
   - If the user is **actively typing** in a search bar, URL box, or modal, OmniRip does **not** steal focus—it shows a bright badge in the top bar: `[⬆ Update Ready • Press Ctrl+U]`.
   - As soon as the user is idle on the main view (or right on startup after First-Run Setup is complete), the **Update Available Popup** appears cleanly.

### Wireframe 1 — Update Available Popup (`src/ui/update_modal.rs`)

```text
+------------------------------------------------------------------------------+
|                       ⬆  NEW OMNIRIP UPDATE AVAILABLE                        |
+------------------------------------------------------------------------------+
|                                                                              |
|  A fresh update is ready!  Current: v0.2.0 (005bd19) -> Latest: main@a8f31c2 |
|                                                                              |
|  What's New & Fixed for You:                                                 |
|    • [NEW] Mac system sound works cleanly with zero orange mic dot.          |
|    • [FIXED] Switching sound with X works smoothly on AirPods & speakers.    |
|    • [IMPROVED] Faster streaming queue & clearer headphone calibration.      |
|                                                                              |
|  --------------------------------------------------------------------------  |
|  [████████████████████░░░░░░░░░░░░░░░░░░░░]  54% • Downloading (4.8 MB/s)    |
|                                                                              |
|   [Enter] Update & Restart Now (~3s)   [B] Background   [Esc] Later          |
|                                                                              |
+------------------------------------------------------------------------------+
```

*(Homebrew installs detected via `is_homebrew_install()` automatically show a clear 1-line notice: `"Installed via Homebrew — run 'brew upgrade omnirip' in Terminal"` instead of overwriting Cellar symlinks.)*

### Wireframe 2 — Post-Restart Welcome Popup ("OmniRip Just Got Better!")

Persisted via `~/.local/share/omnirip/last_seen_build.json` (`{ "last_seen_sha": "...", "pending_whats_new": [...] }`). The very first time the newly updated binary boots after restarting, it greets the user once:

```text
+------------------------------------------------------------------------------+
|                     ✨  OMNIRIP UPDATED TO main@a8f31c2                      |
+------------------------------------------------------------------------------+
|                                                                              |
|  Welcome back! OmniRip just finished updating. Here is what changed:         |
|                                                                              |
|    • [NEW] Mac system sound works cleanly with zero orange mic dot.          |
|    • [FIXED] Switching sound with X works smoothly on AirPods & speakers.    |
|    • [IMPROVED] Faster streaming queue & clearer headphone calibration.      |
|                                                                              |
|  Everything is ready—your EQ presets, playlists & settings were preserved.   |
|                                                                              |
|                         [Enter] Start Listening                              |
|                                                                              |
+------------------------------------------------------------------------------+
```

*(If the update also carries a newer `OmniRipAudio.driver` version (`omnirip-driver-ver > installed_driver_version()`), our existing First-Run/Upgrade Gate prompts 1-click Touch ID refresh right after `[Enter]` so the sound driver never lags behind the app!)*

---

## 6. Part 4 — Bulletproof Reliability & Safety Mechanisms

1. **HTTP Range Resume + Retry (`download_binary_with_resume`):**
   - Port Phaenna's 4-attempt exponential-backoff HTTP `Range: bytes=N-` downloader (`phaenna/src/services/updater.rs:315-495`) with 30s chunk stall timeouts and automatic URL refresh on transient CDN/GitHub errors.
2. **Apple Silicon `SIGKILL` Prevention (Fresh Inode Swap + Ad-Hoc Codesign):**
   - Never overwrite the active Mach-O binary bytes in place (which invalidates the kernel's CS_VALID cache and triggers `SIGKILL`).
   - Stage into `.omnirip-update-<pid>.tmp` inside the executable's directory, strip `com.apple.quarantine`, run `codesign -s - -f` on macOS, then `std::fs::rename` atomically onto a brand-new inode.
3. **Automatic Rollback Backup (`omnirip --rollback` / `:rollback`):**
   - Before replacing `current_exe`, copy the currently working binary to `~/.local/share/omnirip/rollback/omnirip.prev` (keeping the last 1 known-good build).
   - If a user ever hits an unexpected regression, running `omnirip --rollback` or `:rollback` swaps `omnirip.prev` back in 1 second.
4. **True In-Place Self-Restart (`execv` on Unix / Spawn Handoff on Windows):**
   - On `[Enter]` after download completes:
     1. Call `self.streamer.terminate()` (restores physical OS default output cleanly).
     2. Drop `TerminalGuard` (leaves alternate screen & disables raw mode cleanly).
     3. Save `last_seen_build.json` with the plain-English `What's New` notes for the post-restart welcome popup.
     4. **macOS / Linux:** `std::os::unix::process::CommandExt::exec` replaces the process in-place with the newly installed binary in the exact same terminal window.
     5. **Windows:** `Command::new(&exe_path).args(&orig_args).spawn()` + `std::process::exit(0)`, and on next startup `cleanup_legacy_update_files()` deletes `.old_version`.
5. **macOS HAL Driver Sync (`apply_self_update`):**
   - Already partially implemented in `src/harvest/updater.rs:286-300`; wire it seamlessly with `omnirip-driver-ver` so any future HAL driver update is staged and offered via Touch ID cleanly.

---

## 7. Phased Implementation Roadmap & File Touch List

| Phase | Scope | Files Modified / Added |
| :--- | :--- | :--- |
| **Phase 1: Build Provenance & Rolling Evaluator** | Add `build.rs` (`OMNIRIP_GIT_SHA`, `OMNIRIP_COMMIT_TS`); add `evaluate_release_update`, `is_homebrew_install`, `OMNIRIP_GIT_SHA` markers, `last_seen_build.json` tracker, and Plain-English Commit Translator in `updater.rs`. | `build.rs` (new), `src/harvest/updater.rs` |
| **Phase 2: Hardened Downloader, Rollback & `execv` Restart** | Add HTTP Range resume, native executable magic/size guard, macOS ad-hoc `codesign` + quarantine strip, `omnirip.prev` rollback backup (`--rollback` / `:rollback`), dual-tier checksum+optional-Minisign gate, and `restart_into_updated_binary()`. | `src/harvest/updater.rs`, `src/harvest/integrity.rs`, `src/main.rs` |
| **Phase 3: Auto-Check Ticker & Plain-English Update Popups** | Add `src/ui/update_modal.rs` (Update Available Popup + Post-Update Welcome Popup), wire 2s startup check + 30-min background check + `[Ctrl+U]` pill + 1-key `execv` restart inside `App`. | `src/ui/update_modal.rs` (new), `src/ui/mod.rs`, `src/ui/app.rs`, `src/ui/setup_modal.rs` |
| **Phase 4: CI-Gated Rolling Release Pipeline** | Update `.github/workflows/release.yml` to run on `push: branches: [main]` + `tags: [v*]`, gated on `needs: test`, auto-updating `v{version}-rolling`, generating plain-English notes + markers + `SHA256SUMS` (and `.minisig` when secret key is configured). | `.github/workflows/release.yml`, `scripts/generate_simple_notes.py` (or inline bash/python in workflow) |

---

## 8. Verification Plan

1. **Automated Unit Tests (`cargo test --locked -- --test-threads=1`)**
   - `evaluate_release_update`: tests newer SemVer, same-SemVer newer rolling SHA, matching SHA (no update), and newer local dev timestamp protection (no downgrade).
   - `simplify_release_notes`: verifies technical commits (`feat(dsp): shm_open biquad...`) map to clean, jargon-free `[NEW]` / `[FIXED]` / `[IMPROVED]` bullets with zero file paths or hex hashes, and `Simple:` trailers pass through verbatim.
   - `has_valid_native_magic`: verifies `Mach-O`, `ELF`, and `PE MZ` headers and rejects HTML error pages or tiny checksum files.
   - `apply_rollback`: verifies staging and restoring `omnirip.prev` in temp directories.
2. **CI Workflow Verification**
   - Push a commit to `main`, confirm `ci.yml` runs and passes on macOS, Linux, and Windows, then `release.yml` builds all 4 archives (`+ OmniRipAudio.driver`), updates `v0.2.0-rolling`, and publishes clean plain-English release notes.
3. **End-to-End Live User Acceptance Test**
   - Launch an older compiled OmniRip binary → within 2s the **New Update Available** popup appears showing plain-English bullets → press `Enter` → watch live `MB/s` download progress → OmniRip closes audio cleanly and **restarts directly in the same terminal window** into the new SHA → **Post-Update Welcome Popup** displays once, then pressing `Enter` returns to listening.
