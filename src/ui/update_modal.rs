//! Dedicated In-App Auto-Update & Plain-English "What's New & Fixed" Popup Modal.
//!
//! Displays:
//! 1. **Update Available Popup** whenever a newer SemVer or rolling commit build is published on GitHub.
//! 2. **Live Download Progress** (or quiet background download when the user presses `[B]`).
//! 3. **Post-Update "What's New" Welcome Popup** on the first launch after an update completes.

use crate::harvest::updater::{self, UpdateInfo, UPDATE_REPO};
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Clear, Gauge, Paragraph, Wrap},
    Frame,
};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc};

/// Current visual state of the Auto-Update & "What's New" popup modal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UpdateModalMode {
    Hidden,
    Available(UpdateInfo),
    Downloading {
        info: UpdateInfo,
        pct: u16,
        status: String,
        background: bool,
    },
    ReadyToRestart {
        info: UpdateInfo,
    },
    PostUpdateWelcome {
        version_label: String,
        notes: Vec<String>,
    },
    Failed {
        info: Option<UpdateInfo>,
        error: String,
    },
}

/// Events sent from background update check/download worker tasks to the TUI thread.
#[derive(Debug, Clone)]
pub enum UpdateWorkerEvent {
    CheckComplete(Result<Option<UpdateInfo>, String>),
    DownloadProgress {
        pct: u16,
        status: String,
    },
    DownloadComplete(UpdateInfo),
    DownloadFailed {
        info: Option<UpdateInfo>,
        error: String,
    },
}

/// Actions returned by `UpdateModalState` to `App`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UpdateModalAction {
    None,
    Close,
    StatusUpdate(String),
    RestartIntoNewBinary,
}

/// State machine for background rolling update checks, downloads, and plain-English popups.
pub struct UpdateModalState {
    pub mode: UpdateModalMode,
    /// Queued update waiting for the user to finish typing or close the first-run setup gate.
    pub pending_update: Option<UpdateInfo>,
    /// Build identifier dismissed with `[Esc] Remind Me Later` during the current session.
    pub dismissed_version: Option<String>,
    /// True when the user explicitly pressed `Ctrl+U` or ran `:update` (opens popup even if up-to-date).
    pub manual_check_in_flight: bool,
    pub cancel_signal: Arc<AtomicBool>,
    worker_rx: Option<mpsc::Receiver<UpdateWorkerEvent>>,
}

impl Default for UpdateModalState {
    fn default() -> Self {
        Self::new()
    }
}

impl UpdateModalState {
    pub fn new() -> Self {
        Self {
            mode: UpdateModalMode::Hidden,
            pending_update: None,
            dismissed_version: None,
            manual_check_in_flight: false,
            cancel_signal: Arc::new(AtomicBool::new(false)),
            worker_rx: None,
        }
    }

    /// True when the modal should be drawn on screen and intercept keyboard input.
    pub fn is_visible(&self) -> bool {
        match &self.mode {
            UpdateModalMode::Hidden => false,
            UpdateModalMode::Downloading { background, .. } => !*background,
            _ => true,
        }
    }

    /// True when an update is available or ready to restart in the header badge.
    pub fn has_pending_badge(&self) -> bool {
        self.pending_update.is_some()
            || matches!(
                self.mode,
                UpdateModalMode::Available(_)
                    | UpdateModalMode::ReadyToRestart { .. }
                    | UpdateModalMode::Downloading {
                        background: true,
                        ..
                    }
            )
    }

    /// Opens the Post-Update "What's New & Fixed" welcome popup on first boot after an update.
    pub fn open_post_update_welcome(&mut self, version_label: String, notes: Vec<String>) {
        self.mode = UpdateModalMode::PostUpdateWelcome {
            version_label,
            notes,
        };
    }

    /// Opens any queued update immediately, or triggers an immediate check when pressed via `Ctrl+U` / `:update`.
    pub fn open_or_check_now(&mut self) -> UpdateModalAction {
        if let Some(info) = self.pending_update.take() {
            self.mode = UpdateModalMode::Available(info);
            return UpdateModalAction::None;
        }
        if let UpdateModalMode::Downloading {
            info,
            pct,
            status,
            background: true,
        } = &self.mode
        {
            self.mode = UpdateModalMode::Downloading {
                info: info.clone(),
                pct: *pct,
                status: status.clone(),
                background: false,
            };
            return UpdateModalAction::None;
        }
        self.manual_check_in_flight = true;
        self.spawn_update_check(0);
        UpdateModalAction::StatusUpdate(
            "Checking GitHub for the latest Orchestria self-update...".to_string(),
        )
    }

    /// Spawns an asynchronous GitHub release check after `delay_ms`.
    pub fn spawn_update_check(&mut self, delay_ms: u64) {
        if matches!(self.mode, UpdateModalMode::Downloading { .. }) {
            return;
        }
        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);

        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                if delay_ms > 0 {
                    tokio::time::sleep(std::time::Duration::from_millis(delay_ms)).await;
                }
                let res = updater::check_latest_release(UPDATE_REPO).await;
                let _ = tx.send(UpdateWorkerEvent::CheckComplete(res));
            });
        }
    }

    /// Starts downloading & installing `info` (either foreground modal or background status bar).
    pub fn start_update_install(&mut self, info: UpdateInfo, background: bool) -> UpdateModalAction {
        self.cancel_signal.store(false, Ordering::SeqCst);
        let cancel = Arc::clone(&self.cancel_signal);
        let (tx, rx) = mpsc::channel();
        self.worker_rx = Some(rx);

        let initial_status = if info.is_homebrew {
            "Upgrading Orchestria via Homebrew (`brew upgrade orchestria`)...".to_string()
        } else {
            format!(
                "Downloading & verifying Orchestria {}...",
                info.display_version()
            )
        };

        self.mode = UpdateModalMode::Downloading {
            info: info.clone(),
            pct: 5,
            status: initial_status.clone(),
            background,
        };

        if let Ok(handle) = tokio::runtime::Handle::try_current() {
            handle.spawn(async move {
                if info.is_homebrew {
                    let _ = tx.send(UpdateWorkerEvent::DownloadProgress {
                        pct: 35,
                        status: "Running `brew upgrade orchestria`...".to_string(),
                    });
                    let out = Command::new("brew").args(["upgrade", "orchestria"]).output();
                    match out {
                        Ok(o) if o.status.success() => {
                            updater::record_pending_post_update_welcome(&info);
                            let _ = tx.send(UpdateWorkerEvent::DownloadComplete(info));
                        }
                        Ok(o) => {
                            let stderr = String::from_utf8_lossy(&o.stderr).trim().to_string();
                            let _ = tx.send(UpdateWorkerEvent::DownloadFailed {
                                info: Some(info),
                                error: if stderr.is_empty() {
                                    "Homebrew upgrade returned non-zero status.".to_string()
                                } else {
                                    stderr
                                },
                            });
                        }
                        Err(e) => {
                            let _ = tx.send(UpdateWorkerEvent::DownloadFailed {
                                info: Some(info),
                                error: format!("Failed to invoke brew: {}", e),
                            });
                        }
                    }
                    return;
                }

                let tx_prog = tx.clone();
                let info_for_install = info.clone();
                let res = updater::apply_self_update_with_info(
                    &info_for_install,
                    move |downloaded, total| {
                        let pct = match total {
                            Some(t) if t > 0 => ((downloaded.saturating_mul(100)) / t).min(99) as u16,
                            _ => 50,
                        };
                        let mb = downloaded as f64 / (1024.0 * 1024.0);
                        let status = match total {
                            Some(t) if t > 0 => {
                                let tot_mb = t as f64 / (1024.0 * 1024.0);
                                format!("Downloading update... {:.1} / {:.1} MB ({}%)", mb, tot_mb, pct)
                            }
                            _ => format!("Downloading update... {:.1} MB", mb),
                        };
                        let _ = tx_prog.send(UpdateWorkerEvent::DownloadProgress { pct, status });
                    },
                    cancel,
                )
                .await;

                match res {
                    Ok(_) => {
                        let _ = tx.send(UpdateWorkerEvent::DownloadComplete(info));
                    }
                    Err(e) => {
                        let _ = tx.send(UpdateWorkerEvent::DownloadFailed {
                            info: Some(info),
                            error: e,
                        });
                    }
                }
            });
        }

        if background {
            UpdateModalAction::StatusUpdate(initial_status)
        } else {
            UpdateModalAction::None
        }
    }

    /// Polls background worker events and auto-opens any pending update popup once the user is idle.
    pub fn poll_worker(
        &mut self,
        user_busy_typing: bool,
        blocking_modal_open: bool,
    ) -> UpdateModalAction {
        let mut action = UpdateModalAction::None;

        if let Some(rx) = &self.worker_rx {
            while let Ok(ev) = rx.try_recv() {
                match ev {
                    UpdateWorkerEvent::CheckComplete(Ok(Some(info))) => {
                        let was_manual = self.manual_check_in_flight;
                        self.manual_check_in_flight = false;

                        if info.has_update {
                            let id = info.display_version();
                            let already_dismissed =
                                self.dismissed_version.as_deref() == Some(id.as_str());
                            if already_dismissed && !was_manual {
                                self.pending_update = Some(info);
                            } else if (user_busy_typing || blocking_modal_open) && !was_manual {
                                self.pending_update = Some(info.clone());
                                action = UpdateModalAction::StatusUpdate(format!(
                                    "⬆ Orchestria {} update available! Press Ctrl+U to view What's New & update.",
                                    info.display_version()
                                ));
                            } else {
                                self.pending_update = None;
                                self.mode = UpdateModalMode::Available(info);
                            }
                        } else if was_manual {
                            action = UpdateModalAction::StatusUpdate(format!(
                                "Orchestria is already up to date ({}).",
                                info.current_display_version()
                            ));
                        }
                    }
                    UpdateWorkerEvent::CheckComplete(Ok(None)) => {
                        if self.manual_check_in_flight {
                            self.manual_check_in_flight = false;
                            action = UpdateModalAction::StatusUpdate(
                                "Orchestria is up to date (no published releases found).".to_string(),
                            );
                        }
                    }
                    UpdateWorkerEvent::CheckComplete(Err(e)) => {
                        if self.manual_check_in_flight {
                            self.manual_check_in_flight = false;
                            action = UpdateModalAction::StatusUpdate(format!(
                                "Update check notice: {}",
                                e
                            ));
                        }
                    }
                    UpdateWorkerEvent::DownloadProgress { pct, status } => {
                        if let UpdateModalMode::Downloading {
                            pct: cur_pct,
                            status: cur_status,
                            ..
                        } = &mut self.mode
                        {
                            *cur_pct = pct;
                            *cur_status = status;
                        }
                    }
                    UpdateWorkerEvent::DownloadComplete(info) => {
                        let was_background = matches!(
                            self.mode,
                            UpdateModalMode::Downloading {
                                background: true,
                                ..
                            }
                        );
                        if was_background {
                            self.mode = UpdateModalMode::ReadyToRestart { info: info.clone() };
                            action = UpdateModalAction::StatusUpdate(format!(
                                "✨ Orchestria {} installed! Press Enter to restart into the new version.",
                                info.display_version()
                            ));
                        } else {
                            self.mode = UpdateModalMode::ReadyToRestart { info };
                            return UpdateModalAction::RestartIntoNewBinary;
                        }
                    }
                    UpdateWorkerEvent::DownloadFailed { info, error } => {
                        self.mode = UpdateModalMode::Failed { info, error };
                    }
                }
            }
        }

        // If an update was queued while the user was typing or in another modal, pop it up once idle.
        if matches!(self.mode, UpdateModalMode::Hidden)
            && !user_busy_typing
            && !blocking_modal_open
        {
            if let Some(info) = self.pending_update.take() {
                let id = info.display_version();
                if self.dismissed_version.as_deref() != Some(id.as_str()) {
                    self.mode = UpdateModalMode::Available(info);
                } else {
                    self.pending_update = Some(info);
                }
            }
        }

        action
    }

    /// Handles keyboard input when `self.is_visible()` is true.
    pub fn handle_key(&mut self, key: KeyEvent) -> UpdateModalAction {
        match &self.mode {
            UpdateModalMode::Hidden => UpdateModalAction::None,
            UpdateModalMode::Available(info) => {
                let info_clone = info.clone();
                match key.code {
                    KeyCode::Enter | KeyCode::Char('u') | KeyCode::Char('U') => {
                        self.start_update_install(info_clone, false)
                    }
                    KeyCode::Char('b') | KeyCode::Char('B') if !info_clone.is_homebrew => {
                        self.start_update_install(info_clone, true)
                    }
                    KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('Q') => {
                        let id = info_clone.display_version();
                        self.dismissed_version = Some(id.clone());
                        self.pending_update = Some(info_clone);
                        self.mode = UpdateModalMode::Hidden;
                        UpdateModalAction::StatusUpdate(format!(
                            "Update {} snoozed. Press Ctrl+U or type :update anytime.",
                            id
                        ))
                    }
                    _ => UpdateModalAction::None,
                }
            }
            UpdateModalMode::Downloading {
                info, background, ..
            } => match key.code {
                KeyCode::Char('b') | KeyCode::Char('B') if !*background => {
                    let info_clone = info.clone();
                    if let UpdateModalMode::Downloading { background: bg, .. } = &mut self.mode {
                        *bg = true;
                    }
                    UpdateModalAction::StatusUpdate(format!(
                        "Downloading Orchestria {} in the background...",
                        info_clone.display_version()
                    ))
                }
                KeyCode::Esc => {
                    self.cancel_signal.store(true, Ordering::SeqCst);
                    self.mode = UpdateModalMode::Hidden;
                    UpdateModalAction::StatusUpdate("Update download canceled.".to_string())
                }
                _ => UpdateModalAction::None,
            },
            UpdateModalMode::ReadyToRestart { .. } => match key.code {
                KeyCode::Enter | KeyCode::Char('r') | KeyCode::Char('R') => {
                    UpdateModalAction::RestartIntoNewBinary
                }
                KeyCode::Esc => {
                    self.mode = UpdateModalMode::Hidden;
                    UpdateModalAction::StatusUpdate(
                        "Update installed! Restart Orchestria anytime to use the new version."
                            .to_string(),
                    )
                }
                _ => UpdateModalAction::None,
            },
            UpdateModalMode::PostUpdateWelcome { .. } => match key.code {
                KeyCode::Enter | KeyCode::Esc | KeyCode::Char(' ') | KeyCode::Char('q') => {
                    self.mode = UpdateModalMode::Hidden;
                    UpdateModalAction::Close
                }
                _ => UpdateModalAction::None,
            },
            UpdateModalMode::Failed { info, .. } => match key.code {
                KeyCode::Enter | KeyCode::Char('r') | KeyCode::Char('R') => {
                    if let Some(info_clone) = info.clone() {
                        self.start_update_install(info_clone, false)
                    } else {
                        self.mode = UpdateModalMode::Hidden;
                        self.open_or_check_now()
                    }
                }
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('Q') => {
                    self.mode = UpdateModalMode::Hidden;
                    UpdateModalAction::Close
                }
                _ => UpdateModalAction::None,
            },
        }
    }

    /// Renders the Update Available, Downloading, Ready-to-Restart, or Post-Update Welcome popup.
    pub fn render(&self, f: &mut Frame, area: Rect) {
        if !self.is_visible() {
            return;
        }

        let popup_area = centered_rect(68, 62, area);
        f.render_widget(Clear, popup_area);

        match &self.mode {
            UpdateModalMode::Hidden => {}
            UpdateModalMode::Available(info) => {
                let block = Block::default()
                    .title(Span::styled(
                        " 🚀 Orchestria Update Available ",
                        Style::default()
                            .fg(Color::Black)
                            .bg(Color::Cyan)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::Cyan));

                let mut lines = vec![
                    Line::from(""),
                    Line::from(vec![
                        Span::styled(
                            "  Current Version: ",
                            Style::default().fg(Color::Gray),
                        ),
                        Span::styled(
                            info.current_display_version(),
                            Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
                        ),
                        Span::styled("   →   ", Style::default().fg(Color::Cyan)),
                        Span::styled("New Version: ", Style::default().fg(Color::Gray)),
                        Span::styled(
                            info.display_version(),
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                    ]),
                    Line::from(""),
                    Line::from(Span::styled(
                        "  What's New & Fixed for You:",
                        Style::default()
                            .fg(Color::Yellow)
                            .add_modifier(Modifier::BOLD),
                    )),
                    Line::from(""),
                ];

                for note in &info.simple_notes {
                    lines.push(format_plain_english_bullet(note));
                }

                lines.push(Line::from(""));
                lines.push(Line::from(Span::styled(
                    "  Your music library, presets, and sound settings will stay right where they are.",
                    Style::default().fg(Color::DarkGray),
                )));
                lines.push(Line::from(""));

                if info.is_homebrew {
                    lines.push(Line::from(vec![
                        Span::styled(
                            "  [Enter] ",
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                        Span::styled(
                            "Upgrade via Homebrew & Restart   ",
                            Style::default().fg(Color::White),
                        ),
                        Span::styled(
                            "[Esc] ",
                            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                        ),
                        Span::styled("Remind Me Later", Style::default().fg(Color::Gray)),
                    ]));
                } else {
                    lines.push(Line::from(vec![
                        Span::styled(
                            "  [Enter] ",
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                        Span::styled(
                            "Update & Restart Now   ",
                            Style::default().fg(Color::White),
                        ),
                        Span::styled(
                            "[B] ",
                            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                        ),
                        Span::styled(
                            "Update in Background   ",
                            Style::default().fg(Color::White),
                        ),
                        Span::styled(
                            "[Esc] ",
                            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                        ),
                        Span::styled("Remind Me Later", Style::default().fg(Color::Gray)),
                    ]));
                }

                let p = Paragraph::new(lines)
                    .block(block)
                    .wrap(Wrap { trim: false })
                    .alignment(Alignment::Left);
                f.render_widget(p, popup_area);
            }
            UpdateModalMode::Downloading {
                info, pct, status, ..
            } => {
                let block = Block::default()
                    .title(Span::styled(
                        " ⬇ Installing Orchestria Update ",
                        Style::default()
                            .fg(Color::Black)
                            .bg(Color::Cyan)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::Cyan));

                let inner = block.inner(popup_area);
                f.render_widget(block, popup_area);

                let chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .margin(1)
                    .constraints([
                        Constraint::Length(3),
                        Constraint::Length(3),
                        Constraint::Min(3),
                    ])
                    .split(inner);

                let header = Paragraph::new(vec![
                    Line::from(vec![
                        Span::styled("Updating to ", Style::default().fg(Color::Gray)),
                        Span::styled(
                            info.display_version(),
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                    ]),
                    Line::from(Span::styled(
                        status.as_str(),
                        Style::default().fg(Color::White),
                    )),
                ]);
                f.render_widget(header, chunks[0]);

                let gauge = Gauge::default()
                    .block(Block::default().borders(Borders::ALL).title(" Progress "))
                    .gauge_style(
                        Style::default()
                            .fg(Color::Cyan)
                            .bg(Color::Black)
                            .add_modifier(Modifier::BOLD),
                    )
                    .percent((*pct).min(100));
                f.render_widget(gauge, chunks[1]);

                let footer = Paragraph::new(Line::from(vec![
                    Span::styled(
                        "[B] ",
                        Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        "Finish in Background   ",
                        Style::default().fg(Color::White),
                    ),
                    Span::styled(
                        "[Esc] ",
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled("Cancel", Style::default().fg(Color::Gray)),
                ]));
                f.render_widget(footer, chunks[2]);
            }
            UpdateModalMode::ReadyToRestart { info } => {
                let block = Block::default()
                    .title(Span::styled(
                        " ✨ Orchestria Update Ready ",
                        Style::default()
                            .fg(Color::Black)
                            .bg(Color::LightGreen)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::LightGreen));

                let mut lines = vec![
                    Line::from(""),
                    Line::from(vec![
                        Span::styled(
                            "  Orchestria ",
                            Style::default().fg(Color::White),
                        ),
                        Span::styled(
                            info.display_version(),
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                        Span::styled(
                            " is verified and ready!",
                            Style::default().fg(Color::White),
                        ),
                    ]),
                    Line::from(""),
                    Line::from(Span::styled(
                        "  What's Included:",
                        Style::default()
                            .fg(Color::Yellow)
                            .add_modifier(Modifier::BOLD),
                    )),
                    Line::from(""),
                ];
                for note in &info.simple_notes {
                    lines.push(format_plain_english_bullet(note));
                }
                lines.push(Line::from(""));
                lines.push(Line::from(vec![
                    Span::styled(
                        "  [Enter / R] ",
                        Style::default()
                            .fg(Color::LightGreen)
                            .add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        "Restart Into New Version Now   ",
                        Style::default().fg(Color::White),
                    ),
                    Span::styled(
                        "[Esc] ",
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled("Later", Style::default().fg(Color::Gray)),
                ]));

                let p = Paragraph::new(lines)
                    .block(block)
                    .wrap(Wrap { trim: false });
                f.render_widget(p, popup_area);
            }
            UpdateModalMode::PostUpdateWelcome {
                version_label,
                notes,
            } => {
                let block = Block::default()
                    .title(Span::styled(
                        format!(" ✨ Orchestria Just Got Better! (v{}) ", version_label),
                        Style::default()
                            .fg(Color::Black)
                            .bg(Color::LightGreen)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::LightGreen));

                let mut lines = vec![
                    Line::from(""),
                    Line::from(Span::styled(
                        "  You are now running the latest version of Orchestria. Here is what changed:",
                        Style::default().fg(Color::White),
                    )),
                    Line::from(""),
                ];
                for note in notes {
                    lines.push(format_plain_english_bullet(note));
                }
                lines.push(Line::from(""));
                lines.push(Line::from(Span::styled(
                    "  Tip: If anything ever feels off, run `orchestria --rollback` or `:rollback` to restore the previous build.",
                    Style::default().fg(Color::DarkGray),
                )));
                lines.push(Line::from(""));
                lines.push(Line::from(vec![
                    Span::styled(
                        "  [Enter / Esc] ",
                        Style::default()
                            .fg(Color::LightGreen)
                            .add_modifier(Modifier::BOLD),
                    ),
                    Span::styled("Start Listening", Style::default().fg(Color::White)),
                ]));

                let p = Paragraph::new(lines)
                    .block(block)
                    .wrap(Wrap { trim: false });
                f.render_widget(p, popup_area);
            }
            UpdateModalMode::Failed { error, .. } => {
                let block = Block::default()
                    .title(Span::styled(
                        " ⚠ Update Notice ",
                        Style::default()
                            .fg(Color::Black)
                            .bg(Color::Yellow)
                            .add_modifier(Modifier::BOLD),
                    ))
                    .borders(Borders::ALL)
                    .border_type(BorderType::Rounded)
                    .border_style(Style::default().fg(Color::Yellow));

                let lines = vec![
                    Line::from(""),
                    Line::from(Span::styled(
                        "  Orchestria could not complete the update right now:",
                        Style::default().fg(Color::White),
                    )),
                    Line::from(""),
                    Line::from(Span::styled(
                        format!("  {}", error),
                        Style::default().fg(Color::LightRed),
                    )),
                    Line::from(""),
                    Line::from(Span::styled(
                        "  Your current Orchestria installation was not modified.",
                        Style::default().fg(Color::Gray),
                    )),
                    Line::from(""),
                    Line::from(vec![
                        Span::styled(
                            "  [Enter / R] ",
                            Style::default()
                                .fg(Color::LightGreen)
                                .add_modifier(Modifier::BOLD),
                        ),
                        Span::styled("Retry Update   ", Style::default().fg(Color::White)),
                        Span::styled(
                            "[Esc] ",
                            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                        ),
                        Span::styled("Close", Style::default().fg(Color::Gray)),
                    ]),
                ];

                let p = Paragraph::new(lines)
                    .block(block)
                    .wrap(Wrap { trim: false });
                f.render_widget(p, popup_area);
            }
        }
    }
}

fn format_plain_english_bullet(note: &str) -> Line<'static> {
    let trimmed = note.trim();
    if let Some(rest) = trimmed.strip_prefix("[NEW]") {
        Line::from(vec![
            Span::raw("  • "),
            Span::styled(
                "[NEW] ",
                Style::default()
                    .fg(Color::LightGreen)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(rest.trim().to_string(), Style::default().fg(Color::White)),
        ])
    } else if let Some(rest) = trimmed.strip_prefix("[FIXED]") {
        Line::from(vec![
            Span::raw("  • "),
            Span::styled(
                "[FIXED] ",
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(rest.trim().to_string(), Style::default().fg(Color::White)),
        ])
    } else if let Some(rest) = trimmed.strip_prefix("[IMPROVED]") {
        Line::from(vec![
            Span::raw("  • "),
            Span::styled(
                "[IMPROVED] ",
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(rest.trim().to_string(), Style::default().fg(Color::White)),
        ])
    } else {
        Line::from(vec![
            Span::raw("  • "),
            Span::styled(trimmed.to_string(), Style::default().fg(Color::White)),
        ])
    }
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::KeyModifiers;

    fn sample_update_info() -> UpdateInfo {
        UpdateInfo {
            current_version: "0.2.0".to_string(),
            latest_version: "v0.2.0-rolling".to_string(),
            has_update: true,
            download_url: "https://example.com/orchestria.tar.gz".to_string(),
            release_name: "Orchestria Rolling".to_string(),
            release_notes: String::new(),
            remote_sha: Some("1234567890abcdef".to_string()),
            simple_notes: vec![
                "[NEW] System-wide sound processing without the orange microphone indicator."
                    .to_string(),
                "[FIXED] Turning off sound capture restores your headphones immediately."
                    .to_string(),
            ],
            is_homebrew: false,
            driver_version: Some(2),
        }
    }

    #[test]
    fn test_update_modal_available_and_snooze() {
        let mut modal = UpdateModalState::new();
        assert!(!modal.is_visible());

        let info = sample_update_info();
        modal.mode = UpdateModalMode::Available(info.clone());
        assert!(modal.is_visible());
        assert!(modal.has_pending_badge());

        // Pressing Esc snoozes the modal but keeps the pending update badge available via Ctrl+U
        let act = modal.handle_key(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE));
        assert!(!modal.is_visible());
        assert!(modal.has_pending_badge());
        assert!(matches!(act, UpdateModalAction::StatusUpdate(_)));

        // Pressing Ctrl+U (`open_or_check_now`) re-opens the snoozed update immediately
        modal.open_or_check_now();
        assert!(modal.is_visible());
        assert_eq!(modal.mode, UpdateModalMode::Available(info));
    }

    #[test]
    fn test_post_update_welcome_dismissal() {
        let mut modal = UpdateModalState::new();
        modal.open_post_update_welcome(
            "0.2.0 (1234567)".to_string(),
            vec!["[NEW] Faster startup.".to_string()],
        );
        assert!(modal.is_visible());

        let act = modal.handle_key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE));
        assert_eq!(act, UpdateModalAction::Close);
        assert!(!modal.is_visible());
    }
}
