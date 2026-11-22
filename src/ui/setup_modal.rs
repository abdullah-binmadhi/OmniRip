//! Guided First-Run Onboarding Gate & System Setup / Dependency Health Wizard.
//!
//! Guides users through complete one-click setup across macOS (Touch ID / Password),
//! Windows (UAC / Windows Hello + 3010 reboot detection), and Linux (zero-prompt PipeWire/PulseAudio).

use crate::driver::bundle::EXPECTED_DRIVER_BUNDLE_VERSION;
use crate::driver::{check_system_audio_health, DriverInstallOutcome, SystemAudioHealth};
use crate::harvest::bootstrap::{ToolInfo, ToolResolver};
use crossterm::event::KeyCode;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Clear, Gauge, Paragraph},
    Frame,
};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc};

/// Persisted onboarding state so OmniRip remembers setup completion & post-reboot recovery.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct SetupPersistence {
    pub completed_driver_version: u32,
    pub limited_mode_accepted: bool,
    pub pending_reboot_verification: bool,
}

impl SetupPersistence {
    pub fn default_path() -> PathBuf {
        crate::driver::bundle::user_driver_cache_dir().join("setup_state.json")
    }

    pub fn load() -> Self {
        Self::load_from_path(&Self::default_path())
    }

    pub fn load_from_path(path: &Path) -> Self {
        std::fs::read_to_string(path)
            .ok()
            .and_then(|s| serde_json::from_str::<Self>(&s).ok())
            .unwrap_or_default()
    }

    pub fn save(&self) {
        let _ = self.save_to_path(&Self::default_path());
    }

    pub fn save_to_path(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let body = serde_json::to_string_pretty(self)?;
        std::fs::write(path, body)
    }
}

/// Active screen state inside the Setup & Onboarding modal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SetupPhase {
    Overview,
    Running,
    Ready(String),
    RebootRequired(String),
    Failed(String),
}

/// Events pushed from background setup/driver worker threads to the TUI event loop.
#[derive(Debug, Clone)]
pub enum SetupWorkerEvent {
    Progress {
        pct: u16,
        tool: String,
        status: String,
    },
    RefreshHealth,
    DriverActivated(String),
    DriverRebootRequired(String),
    DriverUninstalled(String),
    Error(String),
}

/// Actions returned by `SetupModalState` upon key handling or worker polling.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SetupModalAction {
    None,
    Close,
    StatusUpdate(String),
    HotActivateSoundEngine,
    RequestAppQuit,
    TriggerOsReboot,
}

const SPINNER_FRAMES: [&str; 4] = ["|", "/", "-", "\\"];

/// Interactive Guided First-Run Onboarding Gate & Dependency Health Wizard.
pub struct SetupModalState {
    pub is_open: bool,
    pub first_run_gate: bool,
    pub phase: SetupPhase,
    pub ytdlp_info: ToolInfo,
    pub ffmpeg_info: ToolInfo,
    pub driver_installed: bool,
    pub audio_health: SystemAudioHealth,
    pub update_info: Option<crate::harvest::updater::UpdateInfo>,
    pub is_downloading: bool,
    pub download_tool: String,
    pub download_progress_pct: u16,
    pub download_status: String,
    pub cancel_signal: Arc<AtomicBool>,
    spinner_idx: usize,
    worker_rx: Option<mpsc::Receiver<SetupWorkerEvent>>,
}

impl SetupModalState {
    pub fn new() -> Self {
        let health = check_system_audio_health();
        let mut s = Self {
            is_open: false,
            first_run_gate: false,
            phase: SetupPhase::Overview,
            ytdlp_info: ToolResolver::probe_tool("yt-dlp"),
            ffmpeg_info: ToolResolver::probe_tool("ffmpeg"),
            driver_installed: health.driver_installed,
            audio_health: health,
            update_info: None,
            is_downloading: false,
            download_tool: String::new(),
            download_progress_pct: 0,
            download_status: String::new(),
            cancel_signal: Arc::new(AtomicBool::new(false)),
            spinner_idx: 0,
            worker_rx: None,
        };
        s.refresh();
        s
    }

    /// Check if the system audio driver is active / installed.
    pub fn check_driver_status() -> bool {
        check_system_audio_health().driver_installed
    }

    /// Evaluates whether the Guided First-Run Gate should run before entering the workstations.
    /// Returns `true` when System-Wide EQ is ready to auto-enable immediately; opens the gate and
    /// returns `false` when first-time setup or a driver upgrade is needed.
    pub fn prepare_on_launch(&mut self) -> bool {
        self.refresh();
        let mut persisted = SetupPersistence::load();
        let ready = Self::is_system_wide_ready(&self.audio_health);

        if ready {
            if persisted.pending_reboot_verification
                || persisted.completed_driver_version < self.audio_health.expected_version
            {
                persisted.pending_reboot_verification = false;
                persisted.limited_mode_accepted = false;
                persisted.completed_driver_version = self.audio_health.expected_version;
                persisted.save();
            }
            return true;
        }

        if persisted.limited_mode_accepted {
            return false;
        }

        self.open_first_run_gate();
        false
    }

    pub fn is_system_wide_ready(health: &SystemAudioHealth) -> bool {
        #[cfg(target_os = "macos")]
        {
            health.driver_installed && health.driver_loaded && !health.needs_upgrade
        }
        #[cfg(target_os = "windows")]
        {
            if crate::driver::windows::is_headless_windows_ci() {
                return false;
            }
            health.driver_installed && health.driver_loaded
        }
        #[cfg(target_os = "linux")]
        {
            // Linux creates the user-space PipeWire/PulseAudio virtual sink transparently per session.
            let _ = health;
            true
        }
        #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
        {
            let _ = health;
            false
        }
    }

    /// Refresh tool and driver detection status.
    pub fn refresh(&mut self) {
        ToolResolver::activate_user_tools_path();
        self.ytdlp_info = ToolResolver::probe_tool("yt-dlp");
        self.ffmpeg_info = ToolResolver::probe_tool("ffmpeg");
        self.audio_health = check_system_audio_health();
        self.driver_installed = self.audio_health.driver_installed;
    }

    /// Open the setup modal manually (`F12` or `:setup`).
    pub fn open(&mut self) {
        self.refresh();
        self.first_run_gate = false;
        self.phase = SetupPhase::Overview;
        self.is_open = true;
    }

    /// Open as the mandatory-feeling Guided First-Run Onboarding Gate.
    pub fn open_first_run_gate(&mut self) {
        self.refresh();
        self.first_run_gate = true;
        self.phase = SetupPhase::Overview;
        self.is_open = true;
    }

    pub fn mark_ready(&mut self, summary: String) {
        self.refresh();
        self.is_downloading = false;
        self.download_progress_pct = 100;
        self.download_status = summary.clone();
        self.phase = SetupPhase::Ready(summary);
    }

    /// Close the setup modal.
    pub fn close(&mut self) {
        self.is_open = false;
        if self.is_downloading {
            self.cancel_signal.store(true, Ordering::Relaxed);
            self.is_downloading = false;
        }
    }

    fn setup_needs_action(&self) -> bool {
        !self.ytdlp_info.is_installed
            || !self.audio_health.driver_installed
            || !self.audio_health.driver_loaded
            || self.audio_health.needs_upgrade
    }

    /// Polls background setup worker events on each UI tick without ever blocking the terminal.
    pub fn poll_worker(&mut self) -> SetupModalAction {
        if self.is_downloading {
            self.spinner_idx = (self.spinner_idx + 1) % SPINNER_FRAMES.len();
        }

        let mut drained = Vec::new();
        let mut disconnected = false;
        if let Some(ref rx) = self.worker_rx {
            loop {
                match rx.try_recv() {
                    Ok(ev) => drained.push(ev),
                    Err(mpsc::TryRecvError::Empty) => break,
                    Err(mpsc::TryRecvError::Disconnected) => {
                        disconnected = true;
                        break;
                    }
                }
            }
        }
        if disconnected {
            self.worker_rx = None;
        }

        let mut action = SetupModalAction::None;
        for ev in drained {
            match ev {
                SetupWorkerEvent::Progress { pct, tool, status } => {
                    self.is_downloading = true;
                    self.download_progress_pct = pct;
                    self.download_tool = tool;
                    self.download_status = status;
                }
                SetupWorkerEvent::RefreshHealth => {
                    self.refresh();
                }
                SetupWorkerEvent::DriverActivated(msg) => {
                    let mut p = SetupPersistence::load();
                    p.completed_driver_version = EXPECTED_DRIVER_BUNDLE_VERSION;
                    p.limited_mode_accepted = false;
                    p.pending_reboot_verification = false;
                    p.save();
                    self.refresh();
                    self.is_downloading = false;
                    self.download_progress_pct = 100;
                    self.download_status = msg.clone();
                    self.phase = SetupPhase::Ready(msg);
                    action = SetupModalAction::HotActivateSoundEngine;
                }
                SetupWorkerEvent::DriverRebootRequired(msg) => {
                    let mut p = SetupPersistence::load();
                    p.pending_reboot_verification = true;
                    p.limited_mode_accepted = false;
                    p.save();
                    self.refresh();
                    self.is_downloading = false;
                    self.download_progress_pct = 100;
                    self.download_status = msg.clone();
                    self.phase = SetupPhase::RebootRequired(msg.clone());
                    action = SetupModalAction::StatusUpdate(msg);
                }
                SetupWorkerEvent::DriverUninstalled(msg) => {
                    let mut p = SetupPersistence::load();
                    p.completed_driver_version = 0;
                    p.pending_reboot_verification = false;
                    p.save();
                    self.refresh();
                    self.is_downloading = false;
                    self.phase = SetupPhase::Overview;
                    self.download_status = msg.clone();
                    action = SetupModalAction::StatusUpdate(msg);
                }
                SetupWorkerEvent::Error(err) => {
                    self.refresh();
                    self.is_downloading = false;
                    self.phase = SetupPhase::Failed(err.clone());
                    self.download_status = err.clone();
                    action = SetupModalAction::StatusUpdate(err);
                }
            }
        }
        action
    }

    /// Handle key events for the setup wizard modal.
    pub fn handle_key(&mut self, key: KeyCode) -> SetupModalAction {
        match &self.phase {
            SetupPhase::RebootRequired(_) => match key {
                KeyCode::Char('r') | KeyCode::Char('R') | KeyCode::Enter => {
                    let mut p = SetupPersistence::load();
                    p.pending_reboot_verification = true;
                    p.save();
                    SetupModalAction::TriggerOsReboot
                }
                KeyCode::Char('q') | KeyCode::Char('Q') | KeyCode::Esc => {
                    let mut p = SetupPersistence::load();
                    p.pending_reboot_verification = true;
                    p.save();
                    self.close();
                    SetupModalAction::RequestAppQuit
                }
                _ => SetupModalAction::None,
            },
            SetupPhase::Ready(_) => match key {
                KeyCode::Enter | KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('Q') => {
                    self.close();
                    SetupModalAction::Close
                }
                _ => SetupModalAction::None,
            },
            SetupPhase::Running => match key {
                KeyCode::Esc => {
                    self.close();
                    SetupModalAction::Close
                }
                _ => SetupModalAction::None,
            },
            SetupPhase::Overview | SetupPhase::Failed(_) => match key {
                KeyCode::Esc => {
                    self.close();
                    SetupModalAction::Close
                }
                KeyCode::Char('q') | KeyCode::Char('Q') if !self.is_downloading => {
                    self.close();
                    SetupModalAction::Close
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.refresh();
                    SetupModalAction::StatusUpdate("Refreshed dependency and driver health checks.".to_string())
                }
                KeyCode::Char('u') | KeyCode::Char('U') => {
                    if !self.is_downloading {
                        self.start_self_update();
                        SetupModalAction::StatusUpdate("Checking for latest release and initiating self-update...".to_string())
                    } else {
                        SetupModalAction::None
                    }
                }
                KeyCode::Char('d') | KeyCode::Char('D') => {
                    if !self.ytdlp_info.is_installed && !self.is_downloading {
                        self.start_yt_dlp_download();
                        SetupModalAction::StatusUpdate("Started official yt-dlp standalone download...".to_string())
                    } else {
                        self.close();
                        SetupModalAction::Close
                    }
                }
                KeyCode::Enter => {
                    if self.is_downloading {
                        SetupModalAction::None
                    } else if self.setup_needs_action() {
                        self.start_full_guided_setup();
                        SetupModalAction::StatusUpdate("Starting guided System-Wide Sound Engine & tool setup...".to_string())
                    } else {
                        self.close();
                        SetupModalAction::Close
                    }
                }
                KeyCode::Char('i') | KeyCode::Char('I') => {
                    if !self.is_downloading {
                        self.start_driver_install_async();
                        SetupModalAction::StatusUpdate("Opening native OS permission prompt for Sound Engine...".to_string())
                    } else {
                        SetupModalAction::None
                    }
                }
                KeyCode::Char('x') | KeyCode::Char('X') => {
                    if !self.is_downloading {
                        self.start_driver_uninstall_async();
                        SetupModalAction::StatusUpdate("Removing Sound Engine driver via OS authorization...".to_string())
                    } else {
                        SetupModalAction::None
                    }
                }
                KeyCode::Char('l') | KeyCode::Char('L') => {
                    let mut p = SetupPersistence::load();
                    p.limited_mode_accepted = true;
                    p.save();
                    self.close();
                    SetupModalAction::StatusUpdate(
                        "Limited App-Only Mode active (press F12 anytime to enable System-Wide EQ).".to_string(),
                    )
                }
                _ => SetupModalAction::None,
            },
        }
    }

    /// Runs the complete guided pre-flight setup (yt-dlp + ffmpeg + Sound Engine driver + Touch ID / UAC)
    /// asynchronously in a background thread so the TUI spinner never freezes.
    pub fn start_full_guided_setup(&mut self) {
        self.phase = SetupPhase::Running;
        self.is_downloading = true;
        self.download_tool = "Full Sound Engine Setup".to_string();
        self.download_progress_pct = 5;
        self.download_status = "Checking media harvesting tools (yt-dlp & ffmpeg)...".to_string();
        self.cancel_signal = Arc::new(AtomicBool::new(false));

        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);
        let cancel_signal = Arc::clone(&self.cancel_signal);
        let need_ytdlp = !self.ytdlp_info.is_installed;
        let need_driver = !self.audio_health.driver_installed
            || !self.audio_health.driver_loaded
            || self.audio_health.needs_upgrade;

        std::thread::spawn(move || {
            if let Ok(rt) = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
            {
                if need_ytdlp {
                    let _ = tx.send(SetupWorkerEvent::Progress {
                        pct: 15,
                        tool: "yt-dlp".to_string(),
                        status: "Downloading official yt-dlp standalone binary...".to_string(),
                    });
                    let tx_prog = tx.clone();
                    let res = rt.block_on(crate::harvest::bootstrap::ToolBootstrapper::bootstrap_yt_dlp(
                        move |dl, tot| {
                            if let Some(t) = tot {
                                if t > 0 {
                                    let p = (15 + ((dl * 30) / t)).min(45) as u16;
                                    let _ = tx_prog.send(SetupWorkerEvent::Progress {
                                        pct: p,
                                        tool: "yt-dlp".to_string(),
                                        status: format!("Downloading yt-dlp ({} KB)...", dl / 1024),
                                    });
                                }
                            }
                        },
                        Arc::clone(&cancel_signal),
                    ));
                    if let Err(e) = res {
                        let _ = tx.send(SetupWorkerEvent::Error(format!(
                            "Failed to bootstrap yt-dlp: {}",
                            e
                        )));
                        return;
                    }
                    let _ = tx.send(SetupWorkerEvent::RefreshHealth);
                }

                let _ = tx.send(SetupWorkerEvent::Progress {
                    pct: 50,
                    tool: "ffmpeg".to_string(),
                    status: "Checking audio decoder/muxer (ffmpeg)...".to_string(),
                });
                let _ = rt.block_on(
                    crate::harvest::bootstrap::ToolBootstrapper::bootstrap_ffmpeg_if_missing(
                        Arc::clone(&cancel_signal),
                    ),
                );
                let _ = tx.send(SetupWorkerEvent::RefreshHealth);
            }

            if cancel_signal.load(Ordering::Relaxed) {
                let _ = tx.send(SetupWorkerEvent::Error("Setup canceled.".to_string()));
                return;
            }

            if need_driver {
                let _ = tx.send(SetupWorkerEvent::Progress {
                    pct: 65,
                    tool: "Sound Engine Driver".to_string(),
                    status: "Waiting for native OS permission (Touch ID / UAC / Password)...".to_string(),
                });
                match crate::driver::install_driver_gui() {
                    Ok(DriverInstallOutcome::ActivatedImmediate(msg)) => {
                        let _ = tx.send(SetupWorkerEvent::Progress {
                            pct: 95,
                            tool: "Sound Engine Driver".to_string(),
                            status: "Activating Zero-Dot / Zero-Echo audio pipeline...".to_string(),
                        });
                        let _ = tx.send(SetupWorkerEvent::DriverActivated(msg));
                    }
                    Ok(DriverInstallOutcome::RebootRequired(msg)) => {
                        let _ = tx.send(SetupWorkerEvent::DriverRebootRequired(msg));
                    }
                    Err(e) => {
                        let _ = tx.send(SetupWorkerEvent::Error(e));
                    }
                }
            } else {
                let _ = tx.send(SetupWorkerEvent::DriverActivated(
                    "OmniRip Sound Engine & media tools verified ready.".to_string(),
                ));
            }
        });
    }

    /// Runs only the Sound Engine driver installer/upgrader asynchronously via `mpsc`.
    pub fn start_driver_install_async(&mut self) {
        self.phase = SetupPhase::Running;
        self.is_downloading = true;
        self.download_tool = "Sound Engine Driver".to_string();
        self.download_progress_pct = 35;
        self.download_status = "Waiting for native OS authorization (Touch ID / UAC / Password)...".to_string();

        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);

        std::thread::spawn(move || {
            match crate::driver::install_driver_gui() {
                Ok(DriverInstallOutcome::ActivatedImmediate(msg)) => {
                    let _ = tx.send(SetupWorkerEvent::DriverActivated(msg));
                }
                Ok(DriverInstallOutcome::RebootRequired(msg)) => {
                    let _ = tx.send(SetupWorkerEvent::DriverRebootRequired(msg));
                }
                Err(e) => {
                    let _ = tx.send(SetupWorkerEvent::Error(e));
                }
            }
        });
    }

    /// Runs the native GUI driver uninstaller asynchronously.
    pub fn start_driver_uninstall_async(&mut self) {
        self.phase = SetupPhase::Running;
        self.is_downloading = true;
        self.download_tool = "Driver Removal".to_string();
        self.download_progress_pct = 50;
        self.download_status = "Waiting for OS authorization to uninstall driver...".to_string();

        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);

        std::thread::spawn(move || match crate::driver::uninstall_driver_gui() {
            Ok(msg) => {
                let _ = tx.send(SetupWorkerEvent::DriverUninstalled(msg));
            }
            Err(e) => {
                let _ = tx.send(SetupWorkerEvent::Error(e));
            }
        });
    }

    /// Start asynchronous download of `yt-dlp`.
    pub fn start_yt_dlp_download(&mut self) {
        self.phase = SetupPhase::Running;
        self.is_downloading = true;
        self.download_tool = "yt-dlp".to_string();
        self.download_progress_pct = 0;
        self.download_status = "Connecting to official GitHub release...".to_string();
        self.cancel_signal = Arc::new(AtomicBool::new(false));

        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);
        let cancel_signal = Arc::clone(&self.cancel_signal);

        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                let tx_prog = tx.clone();
                let res = crate::harvest::bootstrap::ToolBootstrapper::bootstrap_yt_dlp(
                    move |dl, tot| {
                        if let Some(t) = tot {
                            if t > 0 {
                                let pct = ((dl * 100) / t).min(100) as u16;
                                let _ = tx_prog.send(SetupWorkerEvent::Progress {
                                    pct,
                                    tool: "yt-dlp".to_string(),
                                    status: format!("Downloading yt-dlp ({} KB)...", dl / 1024),
                                });
                            }
                        }
                    },
                    cancel_signal,
                )
                .await;

                match res {
                    Ok(_) => {
                        let _ = tx.send(SetupWorkerEvent::RefreshHealth);
                        let _ = tx.send(SetupWorkerEvent::DriverActivated(
                            "yt-dlp installed and verified.".to_string(),
                        ));
                    }
                    Err(e) => {
                        let _ = tx.send(SetupWorkerEvent::Error(format!(
                            "Failed to download yt-dlp: {}",
                            e
                        )));
                    }
                }
            });
        }
    }

    /// Start asynchronous self-update of OmniRip.
    pub fn start_self_update(&mut self) {
        self.phase = SetupPhase::Running;
        self.is_downloading = true;
        self.download_tool = "OmniRip Update".to_string();
        self.download_progress_pct = 0;
        self.download_status = "Checking latest release on GitHub...".to_string();
        self.cancel_signal = Arc::new(AtomicBool::new(false));

        let cancel_signal = Arc::clone(&self.cancel_signal);

        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                let release_res = crate::harvest::updater::check_latest_release("abdullah-binmadhi/OmniRip").await;
                match release_res {
                    Ok(Some(info)) => {
                        let dl_url = info.download_url;
                        let apply_res = crate::harvest::updater::apply_self_update(
                            &dl_url,
                            |_dl, _tot| {},
                            cancel_signal,
                        )
                        .await;

                        match apply_res {
                            Ok(exe_path) => {
                                println!("[Update] Successfully updated executable: {:?}", exe_path);
                            }
                            Err(e) => {
                                eprintln!("[Update] Update failed: {}", e);
                            }
                        }
                    }
                    Ok(None) => {
                        println!("[Update] OmniRip is already at the latest version.");
                    }
                    Err(e) => {
                        eprintln!("[Update] Failed to query releases: {}", e);
                    }
                }
            });
        }
    }

    /// Render the setup modal interface.
    pub fn render(&self, f: &mut Frame, area: Rect) {
        if !self.is_open {
            return;
        }

        let modal_w = 82.min(area.width.saturating_sub(4));
        let modal_h = 24.min(area.height.saturating_sub(2));

        let popup_area = Rect {
            x: area.x + (area.width.saturating_sub(modal_w)) / 2,
            y: area.y + (area.height.saturating_sub(modal_h)) / 2,
            width: modal_w,
            height: modal_h,
        };

        f.render_widget(Clear, popup_area);

        let title = if self.first_run_gate {
            " OMNIRIP FIRST-RUN SETUP & PRE-FLIGHT CHECK "
        } else {
            " SYSTEM SETUP & SOUND ENGINE HEALTH WIZARD "
        };

        let border_color = match self.phase {
            SetupPhase::Ready(_) => Color::Green,
            SetupPhase::RebootRequired(_) => Color::Yellow,
            SetupPhase::Failed(_) => Color::Red,
            _ => Color::Cyan,
        };

        let block = Block::default()
            .title(title)
            .title_alignment(Alignment::Center)
            .borders(Borders::ALL)
            .border_type(BorderType::Double)
            .border_style(Style::default().fg(border_color).add_modifier(Modifier::BOLD))
            .style(Style::default().bg(Color::Rgb(15, 20, 28)));
        f.render_widget(block, popup_area);

        let inner = popup_area.inner(ratatui::layout::Margin {
            horizontal: 2,
            vertical: 1,
        });

        match &self.phase {
            SetupPhase::RebootRequired(msg) => {
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([
                        Constraint::Length(3),
                        Constraint::Min(8),
                        Constraint::Length(3),
                    ])
                    .split(inner);

                let hdr = Paragraph::new(vec![
                    Line::from(Span::styled(
                        "SETUP COMPLETE — ONE-TIME RESTART REQUIRED",
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                    )),
                    Line::from(Span::styled(
                        "Your OS needs one quick restart to finish activating the audio device.",
                        Style::default().fg(Color::White),
                    )),
                ]);
                f.render_widget(hdr, chunks[0]);

                let body = Paragraph::new(vec![
                    Line::from(""),
                    Line::from(Span::styled(format!("Details: {}", msg), Style::default().fg(Color::Cyan))),
                    Line::from(""),
                    Line::from(Span::styled(
                        "After restarting your computer, just launch `omnirip` and System-Wide EQ",
                        Style::default().fg(Color::Gray),
                    )),
                    Line::from(Span::styled(
                        "will activate automatically with nothing else to configure.",
                        Style::default().fg(Color::Gray),
                    )),
                ]);
                f.render_widget(body, chunks[1]);

                let footer = Paragraph::new(Line::from(vec![
                    Span::styled("[R / Enter] Restart Computer Now   ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                    Span::styled("[Q / Esc] Save & I'll Restart Later", Style::default().fg(Color::White)),
                ]));
                f.render_widget(footer, chunks[2]);
                return;
            }
            SetupPhase::Ready(msg) => {
                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([
                        Constraint::Length(3),
                        Constraint::Min(8),
                        Constraint::Length(3),
                    ])
                    .split(inner);

                let hdr = Paragraph::new(vec![
                    Line::from(Span::styled(
                        "OMNIRIP READY — ALL SYSTEMS GREEN",
                        Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                    )),
                    Line::from(Span::styled(
                        "No restart required. System-Wide EQ is active across all apps.",
                        Style::default().fg(Color::White),
                    )),
                ]);
                f.render_widget(hdr, chunks[0]);

                let out_lbl = self
                    .audio_health
                    .physical_output_name
                    .as_deref()
                    .unwrap_or("Detected Hardware Output");
                let body = Paragraph::new(vec![
                    Line::from(""),
                    Line::from(Span::styled(format!("  [x] Sound Engine    : {}", msg), Style::default().fg(Color::Green))),
                    Line::from(Span::styled(format!("  [x] Physical Output : {}", out_lbl), Style::default().fg(Color::Green))),
                    Line::from(Span::styled(
                        format!(
                            "  [x] Media Tools     : yt-dlp={} • ffmpeg={}",
                            if self.ytdlp_info.is_installed { "Ready" } else { "Optional" },
                            if self.ffmpeg_info.is_installed { "Ready" } else { "Optional" }
                        ),
                        Style::default().fg(Color::Green),
                    )),
                ]);
                f.render_widget(body, chunks[1]);

                let footer = Paragraph::new(Line::from(vec![
                    Span::styled("[Enter / Esc] Launch OmniRip Now", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                ]));
                f.render_widget(footer, chunks[2]);
                return;
            }
            _ => {}
        }

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Header description
                Constraint::Length(8), // Health checks
                Constraint::Length(4), // Progress / Status
                Constraint::Min(4),    // Action footer
            ])
            .split(inner);

        let header = Paragraph::new(vec![
            Line::from(Span::styled(
                "Complete System-Wide Sound Engine & Dependency Pre-Flight",
                Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
            )),
            Line::from(Span::styled(
                "Approve Touch ID / Windows Hello / Password when prompted — zero terminal sudo required.",
                Style::default().fg(Color::DarkGray),
            )),
        ]);
        f.render_widget(header, chunks[0]);

        let ytdlp_status = if self.ytdlp_info.is_installed {
            Span::styled(
                format!("[INSTALLED] {}", self.ytdlp_info.version.as_deref().unwrap_or("Active")),
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            )
        } else {
            Span::styled(
                "[MISSING] Will Auto-Download",
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            )
        };

        let ffmpeg_status = if self.ffmpeg_info.is_installed {
            Span::styled(
                format!("[INSTALLED] {}", self.ffmpeg_info.version.as_deref().unwrap_or("Active")),
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            )
        } else {
            Span::styled("[OPTIONAL] Auto-Checked on Setup", Style::default().fg(Color::Cyan))
        };

        let driver_status = if self.audio_health.needs_upgrade {
            Span::styled(
                format!(
                    "[UPGRADE AVAILABLE] v{} -> v{} (Zero-Dot SHM)",
                    self.audio_health.driver_version.unwrap_or(1),
                    self.audio_health.expected_version
                ),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            )
        } else if self.audio_health.driver_installed && self.audio_health.driver_loaded {
            #[cfg(target_os = "macos")]
            let msg = "[ACTIVE] Zero-Dot CoreAudio HAL v2 Loaded";
            #[cfg(target_os = "windows")]
            let msg = "[ACTIVE] Windows Zero-Echo Virtual Endpoint";
            #[cfg(target_os = "linux")]
            let msg = "[ACTIVE] PipeWire/PulseAudio User-Space Sink";
            #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
            let msg = "[ACTIVE] Sound Engine Ready";
            Span::styled(msg, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
        } else if self.audio_health.driver_installed {
            Span::styled(
                "[PENDING] Installed — Waiting for OS Audio Refresh",
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            )
        } else {
            #[cfg(target_os = "linux")]
            let msg = "[READY] Zero-Sudo PipeWire Sink Auto-Activated on Start";
            #[cfg(not(target_os = "linux"))]
            let msg = "[NOT INSTALLED] Press [Enter] for 1-Click OS Setup";
            Span::styled(msg, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        };

        let tools_dir_str = ToolResolver::user_tools_dir().to_string_lossy().to_string();

        let health_p = Paragraph::new(vec![
            Line::from(vec![
                Span::styled("1. System-Wide Sound Engine : ", Style::default().fg(Color::White)),
                driver_status,
            ]),
            Line::from(vec![
                Span::styled("2. Media Streamer (yt-dlp)  : ", Style::default().fg(Color::White)),
                ytdlp_status,
            ]),
            Line::from(vec![
                Span::styled("3. Audio Muxer (ffmpeg)     : ", Style::default().fg(Color::White)),
                ffmpeg_status,
            ]),
            Line::from(vec![
                Span::styled("4. Physical Transducer      : ", Style::default().fg(Color::White)),
                Span::styled(
                    self.audio_health
                        .physical_output_name
                        .as_deref()
                        .unwrap_or("Auto-Detected Output"),
                    Style::default().fg(Color::Cyan),
                ),
            ]),
            Line::from(vec![
                Span::styled("   User Tools Directory     : ", Style::default().fg(Color::DarkGray)),
                Span::styled(tools_dir_str, Style::default().fg(Color::DarkGray)),
            ]),
        ]);
        f.render_widget(health_p, chunks[1]);

        if self.is_downloading {
            let spin = SPINNER_FRAMES[self.spinner_idx % SPINNER_FRAMES.len()];
            let gauge = Gauge::default()
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .title(format!(" {} {} ", spin, self.download_tool)),
                )
                .gauge_style(Style::default().fg(Color::Magenta).bg(Color::Rgb(25, 30, 45)))
                .percent(self.download_progress_pct)
                .label(format!("{}% - {}", self.download_progress_pct, self.download_status));
            f.render_widget(gauge, chunks[2]);
        } else if let SetupPhase::Failed(err) = &self.phase {
            let err_p = Paragraph::new(vec![
                Line::from(Span::styled(format!("Error: {}", err), Style::default().fg(Color::Red))),
                Line::from(Span::styled("Press [Enter] to retry or [L] for App-Only EQ mode.", Style::default().fg(Color::DarkGray))),
            ]);
            f.render_widget(err_p, chunks[2]);
        } else {
            let note = Paragraph::new(vec![
                Line::from(Span::styled(
                    "Press [Enter] to set up everything automatically (recommended), or [L] for App-Only EQ.",
                    Style::default().fg(Color::Gray),
                )),
            ]);
            f.render_widget(note, chunks[2]);
        }

        let footer = Paragraph::new(vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("[Enter] Set Up All  ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::styled("[I] Install/Upgrade Driver  ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
                Span::styled("[X] Uninstall Driver  ", Style::default().fg(Color::Red)),
                Span::styled("[L] App-Only  ", Style::default().fg(Color::Yellow)),
                Span::styled("[U] Update App  ", Style::default().fg(Color::Cyan)),
                Span::styled("[R] Rescan  ", Style::default().fg(Color::White)),
                Span::styled("[Esc] Close", Style::default().fg(Color::DarkGray)),
            ]),
        ]);
        f.render_widget(footer, chunks[3]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_setup_modal_creation_and_toggle() {
        let mut modal = SetupModalState::new();
        assert!(!modal.is_open);

        modal.open();
        assert!(modal.is_open);

        modal.handle_key(KeyCode::Esc);
        assert!(!modal.is_open);
    }

    #[test]
    fn test_setup_modal_rescan_key() {
        let mut modal = SetupModalState::new();
        modal.open();
        let action = modal.handle_key(KeyCode::Char('r'));
        match action {
            SetupModalAction::StatusUpdate(msg) => {
                assert!(msg.contains("Refreshed"));
            }
            _ => panic!("Expected StatusUpdate"),
        }
    }

    #[test]
    fn test_setup_modal_update_key() {
        let mut modal = SetupModalState::new();
        modal.open();
        let action = modal.handle_key(KeyCode::Char('u'));
        match action {
            SetupModalAction::StatusUpdate(msg) => {
                assert!(msg.contains("self-update"));
            }
            _ => panic!("Expected StatusUpdate"),
        }
    }

    #[test]
    fn test_setup_persistence_roundtrip_and_reboot_phase() {
        let path = std::env::temp_dir().join(format!("omnirip-setup-test-{}.json", std::process::id()));
        let _ = std::fs::remove_file(&path);

        let p = SetupPersistence {
            completed_driver_version: 2,
            limited_mode_accepted: false,
            pending_reboot_verification: true,
        };
        p.save_to_path(&path).expect("save setup_state");
        let loaded = SetupPersistence::load_from_path(&path);
        assert_eq!(loaded, p);
        let _ = std::fs::remove_file(&path);

        let mut modal = SetupModalState::new();
        modal.open();
        modal.phase = SetupPhase::RebootRequired("Windows 3010".to_string());
        assert_eq!(modal.handle_key(KeyCode::Char('r')), SetupModalAction::TriggerOsReboot);
    }
}
