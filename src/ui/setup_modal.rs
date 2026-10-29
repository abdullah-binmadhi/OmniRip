use crate::harvest::bootstrap::{ToolInfo, ToolResolver};
use crossterm::event::KeyCode;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Clear, Gauge, Paragraph},
    Frame,
};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Actions returned by the setup modal upon key handling.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SetupModalAction {
    None,
    Close,
    StatusUpdate(String),
}

/// Interactive Setup & Dependency Health Wizard Modal.
pub struct SetupModalState {
    pub is_open: bool,
    pub ytdlp_info: ToolInfo,
    pub ffmpeg_info: ToolInfo,
    pub driver_installed: bool,
    pub update_info: Option<crate::harvest::updater::UpdateInfo>,
    pub is_downloading: bool,
    pub download_tool: String,
    pub download_progress_pct: u16,
    pub download_status: String,
    pub cancel_signal: Arc<AtomicBool>,
}

impl SetupModalState {
    pub fn new() -> Self {
        let mut s = Self {
            is_open: false,
            ytdlp_info: ToolResolver::probe_tool("yt-dlp"),
            ffmpeg_info: ToolResolver::probe_tool("ffmpeg"),
            driver_installed: Self::check_driver_status(),
            update_info: None,
            is_downloading: false,
            download_tool: String::new(),
            download_progress_pct: 0,
            download_status: String::new(),
            cancel_signal: Arc::new(AtomicBool::new(false)),
        };
        s.refresh();
        s
    }

    /// Check if the system audio driver is active / installed.
    pub fn check_driver_status() -> bool {
        #[cfg(target_os = "macos")]
        {
            std::path::Path::new("/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver").exists()
        }
        #[cfg(not(target_os = "macos"))]
        {
            // Windows WASAPI Loopback and Linux PipeWire Monitor are native & driverless
            true
        }
    }

    /// Refresh tool and driver detection status.
    pub fn refresh(&mut self) {
        ToolResolver::activate_user_tools_path();
        self.ytdlp_info = ToolResolver::probe_tool("yt-dlp");
        self.ffmpeg_info = ToolResolver::probe_tool("ffmpeg");
        self.driver_installed = Self::check_driver_status();
    }

    /// Open the setup modal.
    pub fn open(&mut self) {
        self.refresh();
        self.is_open = true;
    }

    /// Close the setup modal.
    pub fn close(&mut self) {
        self.is_open = false;
        if self.is_downloading {
            self.cancel_signal.store(true, Ordering::Relaxed);
        }
    }

    /// Handle key events for the setup wizard modal.
    pub fn handle_key(&mut self, key: KeyCode) -> SetupModalAction {
        match key {
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
            KeyCode::Char('d') | KeyCode::Char('D') | KeyCode::Enter => {
                if !self.ytdlp_info.is_installed && !self.is_downloading {
                    self.start_yt_dlp_download();
                    SetupModalAction::StatusUpdate("Started official yt-dlp standalone download...".to_string())
                } else {
                    self.close();
                    SetupModalAction::Close
                }
            }
            KeyCode::Char('i') | KeyCode::Char('I') => {
                #[cfg(target_os = "macos")]
                {
                    match crate::driver::install_driver_gui() {
                        Ok(msg) => {
                            self.refresh();
                            SetupModalAction::StatusUpdate(msg)
                        }
                        Err(e) => SetupModalAction::StatusUpdate(format!("Driver Setup Error: {}", e)),
                    }
                }
                #[cfg(not(target_os = "macos"))]
                {
                    SetupModalAction::StatusUpdate("System audio loopback is native and driverless on this platform.".to_string())
                }
            }
            _ => SetupModalAction::None,
        }
    }

    /// Start asynchronous download of `yt-dlp`.
    pub fn start_yt_dlp_download(&mut self) {
        self.is_downloading = true;
        self.download_tool = "yt-dlp".to_string();
        self.download_progress_pct = 0;
        self.download_status = "Connecting to official GitHub release...".to_string();
        self.cancel_signal = Arc::new(AtomicBool::new(false));

        let cancel_signal = Arc::clone(&self.cancel_signal);

        // Spawn background tokio task if a runtime is active
        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                let res = crate::harvest::bootstrap::ToolBootstrapper::bootstrap_yt_dlp(
                    |_dl, _tot| {},
                    cancel_signal,
                )
                .await;

                match res {
                    Ok(path) => {
                        println!("[Setup] yt-dlp installed to: {:?}", path);
                    }
                    Err(e) => {
                        eprintln!("[Setup] Failed to download yt-dlp: {}", e);
                    }
                }
            });
        }
    }

    /// Start asynchronous self-update of OmniRip.
    pub fn start_self_update(&mut self) {
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
                        ).await;

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

        let modal_w = 78.min(area.width.saturating_sub(4));
        let modal_h = 24.min(area.height.saturating_sub(2));

        let popup_area = Rect {
            x: area.x + (area.width.saturating_sub(modal_w)) / 2,
            y: area.y + (area.height.saturating_sub(modal_h)) / 2,
            width: modal_w,
            height: modal_h,
        };

        f.render_widget(Clear, popup_area);

        let block = Block::default()
            .title(" SYSTEM SETUP & DEPENDENCY HEALTH WIZARD ")
            .title_alignment(Alignment::Center)
            .borders(Borders::ALL)
            .border_type(BorderType::Double)
            .border_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
            .style(Style::default().bg(Color::Rgb(15, 20, 28)));
        f.render_widget(block, popup_area);

        let inner = popup_area.inner(ratatui::layout::Margin { horizontal: 2, vertical: 1 });

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Header description
                Constraint::Length(8), // Health checks
                Constraint::Length(4), // Active download progress
                Constraint::Min(4),    // Action footer
            ])
            .split(inner);

        // 1. Header
        let header = Paragraph::new(vec![
            Line::from(Span::styled("OmniRip Self-Contained Diagnostic & Onboarding Wizard", Style::default().fg(Color::White).add_modifier(Modifier::BOLD))),
            Line::from(Span::styled("All components can be automated in-app with zero terminal setup.", Style::default().fg(Color::DarkGray))),
        ]);
        f.render_widget(header, chunks[0]);

        // 2. Health Check Cards
        let ytdlp_status = if self.ytdlp_info.is_installed {
            Span::styled(format!("[INSTALLED] {}", self.ytdlp_info.version.as_deref().unwrap_or("Active")), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
        } else {
            Span::styled("[MISSING] Available for Auto-Download", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        };

        let ffmpeg_status = if self.ffmpeg_info.is_installed {
            Span::styled(format!("[INSTALLED] {}", self.ffmpeg_info.version.as_deref().unwrap_or("Active")), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
        } else {
            Span::styled("[OPTIONAL] System PATH or Homebrew", Style::default().fg(Color::Cyan))
        };

        let driver_status = if self.driver_installed {
            #[cfg(target_os = "macos")]
            let msg = "[ACTIVE] CoreAudio HAL Driver Loaded";
            #[cfg(target_os = "windows")]
            let msg = "[NATIVE] WASAPI Loopback (Driverless)";
            #[cfg(target_os = "linux")]
            let msg = "[NATIVE] PipeWire/PulseAudio Monitor (Driverless)";
            Span::styled(msg, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
        } else {
            Span::styled("[NOT INSTALLED] Required for Desktop System EQ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        };

        let tools_dir_str = ToolResolver::user_tools_dir().to_string_lossy().to_string();

        let health_p = Paragraph::new(vec![
            Line::from(vec![
                Span::styled("1. Media Streamer (yt-dlp) : ", Style::default().fg(Color::White)),
                ytdlp_status,
            ]),
            Line::from(vec![
                Span::styled("2. Audio Muxer (ffmpeg)   : ", Style::default().fg(Color::White)),
                ffmpeg_status,
            ]),
            Line::from(vec![
                Span::styled("3. System Audio Engine   : ", Style::default().fg(Color::White)),
                driver_status,
            ]),
            Line::from(vec![
                Span::styled("4. OmniRip Version       : ", Style::default().fg(Color::White)),
                if let Some(ref u) = self.update_info {
                    if u.has_update {
                        Span::styled(format!("[UPDATE AVAILABLE] {} -> {} (Press [U] to Upgrade)", u.current_version, u.latest_version), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
                    } else {
                        Span::styled(format!("[UP TO DATE] v{}", u.current_version), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
                    }
                } else {
                    Span::styled(format!("v{} (Press [U] to Check Update)", env!("CARGO_PKG_VERSION")), Style::default().fg(Color::Cyan))
                },
            ]),
            Line::from(vec![
                Span::styled("   User Tools Location   : ", Style::default().fg(Color::DarkGray)),
                Span::styled(tools_dir_str, Style::default().fg(Color::DarkGray)),
            ]),
        ]);
        f.render_widget(health_p, chunks[1]);

        // 3. Progress bar if downloading
        if self.is_downloading {
            let gauge = Gauge::default()
                .block(Block::default().borders(Borders::ALL).title(format!(" Downloading {} ", self.download_tool)))
                .gauge_style(Style::default().fg(Color::Magenta).bg(Color::Rgb(25, 30, 45)))
                .percent(self.download_progress_pct)
                .label(format!("{}% - {}", self.download_progress_pct, self.download_status));
            f.render_widget(gauge, chunks[2]);
        } else {
            let note = Paragraph::new(vec![
                Line::from(Span::styled("Ready. Press [D] to download missing tools or [I] to configure driver.", Style::default().fg(Color::DarkGray))),
            ]);
            f.render_widget(note, chunks[2]);
        }

        // 4. Action Footer
        #[cfg(target_os = "macos")]
        let driver_key = "[I] Install Audio Driver (Touch ID / Admin)  ";
        #[cfg(not(target_os = "macos"))]
        let driver_key = "";

        let footer = Paragraph::new(vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("Actions: ", Style::default().fg(Color::DarkGray)),
                Span::styled("[D] Auto-Download yt-dlp  ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled(driver_key, Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
                Span::styled("[U] Upgrade App  ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
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
}
