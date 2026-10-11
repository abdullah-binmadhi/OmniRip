//! Soulseek / Nicotine+ Account Discovery, Switcher & Candidate Modal for OmniRip.
//! Automatically scans the local device for saved Soulseek accounts, presents interactive
//! account switching, provides empty-state guidance for new users, and supports manual login.

use crate::harvest::nicotine::{score_candidate, DiscoveredAccount, NicotineCandidate, NicotineConfig};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, Paragraph};
use ratatui::Frame;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NicotineModalView {
    Accounts,
    ManualEntry,
    Candidates,
}

pub enum NicotineModalAction {
    Close,
    SubmitSearch(String),
    SelectCandidate(NicotineCandidate),
    SelectAccount(DiscoveredAccount),
}

pub struct NicotineModal {
    pub is_open: bool,
    pub view_mode: NicotineModalView,
    pub config: Option<NicotineConfig>,
    pub accounts: Vec<DiscoveredAccount>,
    pub selected_account_idx: usize,
    pub manual_username: String,
    pub manual_password: String,
    pub manual_field: usize, // 0: username, 1: password
    pub query_input: String,
    pub candidates: Vec<NicotineCandidate>,
    pub selected_idx: usize,
    pub status_msg: String,
}

impl NicotineModal {
    pub fn new() -> Self {
        let accounts = NicotineConfig::discover_all_accounts();
        let selected_account_idx = accounts.iter().position(|a| a.is_active).unwrap_or(0);
        let config = NicotineConfig::detect_local();
        let status_msg = if accounts.is_empty() {
            "No Soulseek accounts detected. Press [M] for manual setup.".to_string()
        } else {
            format!("Discovered {} Soulseek account(s) on device.", accounts.len())
        };

        Self {
            is_open: false,
            view_mode: NicotineModalView::Accounts,
            config,
            accounts,
            selected_account_idx,
            manual_username: String::new(),
            manual_password: String::new(),
            manual_field: 0,
            query_input: String::new(),
            candidates: Vec::new(),
            selected_idx: 0,
            status_msg,
        }
    }

    /// Opens the modal directly into the Account Discovery & Selection view, re-scanning local storage.
    pub fn open_accounts(&mut self) {
        self.rescan();
        self.is_open = true;
        self.view_mode = NicotineModalView::Accounts;
    }

    /// Re-scans all known configuration paths for saved Soulseek accounts.
    pub fn rescan(&mut self) {
        self.accounts = NicotineConfig::discover_all_accounts();
        self.selected_account_idx = self.accounts.iter().position(|a| a.is_active).unwrap_or(0);
        self.config = NicotineConfig::detect_local();
        self.status_msg = if self.accounts.is_empty() {
            "No Soulseek accounts detected. Press [M] for manual setup.".to_string()
        } else {
            format!("Discovered {} Soulseek account(s) on device.", self.accounts.len())
        };
    }

    pub fn open_with_query(&mut self, query: &str) {
        self.is_open = true;
        self.view_mode = NicotineModalView::Candidates;
        self.query_input = query.to_string();
        self.status_msg = format!("Ready to search for: {}", query);
    }

    pub fn set_candidates(&mut self, mut candidates: Vec<NicotineCandidate>) {
        for c in candidates.iter_mut() {
            c.score = score_candidate(c);
        }
        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        self.candidates = candidates;
        self.selected_idx = 0;
        self.view_mode = NicotineModalView::Candidates;
        self.status_msg = format!("Found {} lossless candidates", self.candidates.len());
    }

    pub fn handle_key(&mut self, code: KeyCode) -> Option<NicotineModalAction> {
        if !self.is_open {
            return None;
        }

        match self.view_mode {
            NicotineModalView::Accounts => match code {
                KeyCode::Esc => {
                    self.is_open = false;
                    Some(NicotineModalAction::Close)
                }
                KeyCode::Up => {
                    if !self.accounts.is_empty() {
                        self.selected_account_idx = if self.selected_account_idx == 0 {
                            self.accounts.len() - 1
                        } else {
                            self.selected_account_idx - 1
                        };
                    }
                    None
                }
                KeyCode::Down => {
                    if !self.accounts.is_empty() {
                        self.selected_account_idx = (self.selected_account_idx + 1) % self.accounts.len();
                    }
                    None
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.rescan();
                    None
                }
                KeyCode::Char('m') | KeyCode::Char('M') => {
                    self.view_mode = NicotineModalView::ManualEntry;
                    self.manual_field = 0;
                    None
                }
                KeyCode::Char('s') | KeyCode::Char('S') => {
                    self.view_mode = NicotineModalView::Candidates;
                    None
                }
                KeyCode::Enter => {
                    if !self.accounts.is_empty() && self.selected_account_idx < self.accounts.len() {
                        let selected = self.accounts[self.selected_account_idx].clone();
                        let _ = NicotineConfig::save_active_account(&selected.username, selected.password.as_deref());
                        self.is_open = false;
                        Some(NicotineModalAction::SelectAccount(selected))
                    } else {
                        self.view_mode = NicotineModalView::ManualEntry;
                        None
                    }
                }
                _ => None,
            },
            NicotineModalView::ManualEntry => match code {
                KeyCode::Esc => {
                    self.view_mode = NicotineModalView::Accounts;
                    None
                }
                KeyCode::Tab | KeyCode::BackTab => {
                    self.manual_field = (self.manual_field + 1) % 2;
                    None
                }
                KeyCode::Enter => {
                    let u = self.manual_username.trim().to_string();
                    let p = self.manual_password.trim().to_string();
                    if !u.is_empty() {
                        let _ = NicotineConfig::save_active_account(&u, Some(&p));
                        self.rescan();
                        let acc = DiscoveredAccount {
                            username: u,
                            password: if p.is_empty() { None } else { Some(p) },
                            source: "Manual Entry (OmniRip Config)".to_string(),
                            config_path: None,
                            is_active: true,
                        };
                        self.is_open = false;
                        Some(NicotineModalAction::SelectAccount(acc))
                    } else {
                        self.status_msg = "Please enter a valid username".to_string();
                        None
                    }
                }
                KeyCode::Backspace => {
                    if self.manual_field == 0 {
                        self.manual_username.pop();
                    } else {
                        self.manual_password.pop();
                    }
                    None
                }
                KeyCode::Char(c) => {
                    if self.manual_field == 0 {
                        self.manual_username.push(c);
                    } else {
                        self.manual_password.push(c);
                    }
                    None
                }
                _ => None,
            },
            NicotineModalView::Candidates => match code {
                KeyCode::Esc => {
                    self.is_open = false;
                    Some(NicotineModalAction::Close)
                }
                KeyCode::Char('a') | KeyCode::Char('A') => {
                    self.view_mode = NicotineModalView::Accounts;
                    None
                }
                KeyCode::Up => {
                    if !self.candidates.is_empty() {
                        self.selected_idx = if self.selected_idx == 0 {
                            self.candidates.len() - 1
                        } else {
                            self.selected_idx - 1
                        };
                    }
                    None
                }
                KeyCode::Down => {
                    if !self.candidates.is_empty() {
                        self.selected_idx = (self.selected_idx + 1) % self.candidates.len();
                    }
                    None
                }
                KeyCode::Enter => {
                    if !self.candidates.is_empty() && self.selected_idx < self.candidates.len() {
                        let chosen = self.candidates[self.selected_idx].clone();
                        self.is_open = false;
                        Some(NicotineModalAction::SelectCandidate(chosen))
                    } else if !self.query_input.trim().is_empty() {
                        let q = self.query_input.trim().to_string();
                        Some(NicotineModalAction::SubmitSearch(q))
                    } else {
                        None
                    }
                }
                KeyCode::Char(c) => {
                    self.query_input.push(c);
                    None
                }
                KeyCode::Backspace => {
                    self.query_input.pop();
                    None
                }
                _ => None,
            },
        }
    }

    pub fn render(&self, frame: &mut Frame, area: Rect, palette: &ThemePalette) {
        if !self.is_open {
            return;
        }

        let popup_width = (area.width * 85 / 100).max(64);
        let popup_height = (area.height * 80 / 100).max(18);
        let x = (area.width.saturating_sub(popup_width)) / 2;
        let y = (area.height.saturating_sub(popup_height)) / 2;
        let modal_area = Rect::new(x, y, popup_width, popup_height);

        frame.render_widget(Clear, modal_area);

        let border_style = Style::default().fg(palette.accent);

        match self.view_mode {
            NicotineModalView::Accounts => self.render_accounts_view(frame, modal_area, border_style, palette),
            NicotineModalView::ManualEntry => self.render_manual_entry_view(frame, modal_area, border_style, palette),
            NicotineModalView::Candidates => self.render_candidates_view(frame, modal_area, border_style, palette),
        }
    }

    fn render_accounts_view(&self, frame: &mut Frame, area: Rect, border_style: Style, palette: &ThemePalette) {
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(Span::styled(
                " [ SOULSEEK / NICOTINE+ ACCOUNT DISCOVERY & MANAGER ] ",
                Style::default()
                    .fg(palette.primary)
                    .add_modifier(Modifier::BOLD),
            ))
            .title_alignment(Alignment::Center);

        let inner = block.inner(area);
        frame.render_widget(block, area);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2), // Status header
                Constraint::Min(6),    // Account list or empty guidance
                Constraint::Length(2), // Hotkey footer
            ])
            .split(inner);

        // Header status
        let header_p = Paragraph::new(Line::from(vec![
            Span::styled(" STATUS: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled(&self.status_msg, Style::default().fg(Color::Yellow)),
        ]));
        frame.render_widget(header_p, layout[0]);

        if self.accounts.is_empty() {
            let guidance = vec![
                Line::from(Span::styled("  No Soulseek accounts detected on this device.", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))),
                Line::from(""),
                Line::from(Span::styled("  To acquire authentic lossless FLAC files directly from the P2P swarm:", Style::default().fg(Color::White))),
                Line::from(Span::styled("  1. Download and log in to Nicotine+ (https://nicotine-plus.org) or SoulseekQt.", Style::default().fg(Color::Gray))),
                Line::from(Span::styled("  2. Or press [M] to enter your Soulseek username and password manually.", Style::default().fg(Color::Yellow))),
                Line::from(Span::styled("  3. Or press [R] to re-scan storage after logging into your client.", Style::default().fg(Color::Gray))),
                Line::from(""),
                Line::from(Span::styled("  (OmniRip automatically saves your active credentials to ~/.config/omnirip/soulseek.ini)", Style::default().fg(Color::DarkGray))),
            ];
            let guidance_p = Paragraph::new(guidance);
            frame.render_widget(guidance_p, layout[1]);

            let footer = Line::from(vec![
                Span::styled(" [M] Manual Entry ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::raw(" | "),
                Span::styled(" [R] Re-Scan Storage ", Style::default().fg(Color::Green)),
                Span::raw(" | "),
                Span::styled(" [Esc] Dismiss ", Style::default().fg(Color::DarkGray)),
            ]);
            frame.render_widget(Paragraph::new(footer), layout[2]);
        } else {
            let mut list_lines = Vec::new();
            list_lines.push(Line::from(vec![
                Span::styled(" SEL ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled("USERNAME        ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled("SOURCE CLIENT / LOCATION                    ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled("STATUS", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            ]));

            for (idx, acc) in self.accounts.iter().enumerate() {
                let is_selected = idx == self.selected_account_idx;
                let bg_color = if is_selected {
                    Color::Rgb(30, 45, 70)
                } else {
                    Color::Reset
                };

                let marker = if is_selected { " [►] " } else { " [ ] " };
                let user_col = format!("{:<16}", truncate_str(&acc.username, 16));
                let source_col = format!("{:<44}", truncate_str(&acc.source, 44));
                let status_col = if acc.is_active {
                    Span::styled(" [ACTIVE] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [Standby] ", Style::default().fg(Color::DarkGray))
                };

                let row_style = if is_selected {
                    Style::default().fg(Color::Yellow).bg(bg_color).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(Color::White).bg(bg_color)
                };

                list_lines.push(Line::from(vec![
                    Span::styled(marker, Style::default().fg(Color::Yellow)),
                    Span::styled(user_col, row_style),
                    Span::styled(source_col, Style::default().fg(Color::Gray)),
                    status_col,
                ]));
            }

            let accounts_p = Paragraph::new(list_lines);
            frame.render_widget(accounts_p, layout[1]);

            let footer = Line::from(vec![
                Span::styled(" [Enter] Select & Activate ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::raw(" | "),
                Span::styled(" [↑/↓] Navigate ", Style::default().fg(Color::White)),
                Span::raw(" | "),
                Span::styled(" [R] Re-Scan ", Style::default().fg(Color::Green)),
                Span::raw(" | "),
                Span::styled(" [M] Manual Entry ", Style::default().fg(Color::Magenta)),
                Span::raw(" | "),
                Span::styled(" [Esc] Close ", Style::default().fg(Color::DarkGray)),
            ]);
            frame.render_widget(Paragraph::new(footer), layout[2]);
        }
    }

    fn render_manual_entry_view(&self, frame: &mut Frame, area: Rect, border_style: Style, palette: &ThemePalette) {
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(Span::styled(
                " [ MANUAL SOULSEEK ACCOUNT SETUP ] ",
                Style::default()
                    .fg(palette.primary)
                    .add_modifier(Modifier::BOLD),
            ))
            .title_alignment(Alignment::Center);

        let inner = block.inner(area);
        frame.render_widget(block, area);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2), // Guidance
                Constraint::Length(3), // Username field
                Constraint::Length(3), // Password field
                Constraint::Min(2),    // Note
                Constraint::Length(2), // Controls
            ])
            .split(inner);

        let guide_p = Paragraph::new(Span::styled(
            " Enter your Soulseek username and password below (free registration via Nicotine+/SoulseekQt):",
            Style::default().fg(Color::White),
        ));
        frame.render_widget(guide_p, layout[0]);

        // Username
        let user_border = if self.manual_field == 0 { Color::Yellow } else { Color::DarkGray };
        let user_p = Paragraph::new(self.manual_username.as_str())
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(user_border)).title(" Username "));
        frame.render_widget(user_p, layout[1]);

        // Password (masked)
        let pass_border = if self.manual_field == 1 { Color::Yellow } else { Color::DarkGray };
        let masked_pass: String = "•".repeat(self.manual_password.len());
        let pass_p = Paragraph::new(masked_pass.as_str())
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(pass_border)).title(" Password "));
        frame.render_widget(pass_p, layout[2]);

        let note_p = Paragraph::new(vec![
            Line::from(""),
            Line::from(Span::styled(" Credentials will be safely persisted to ~/.config/omnirip/soulseek.ini", Style::default().fg(Color::DarkGray))),
        ]);
        frame.render_widget(note_p, layout[3]);

        let footer = Line::from(vec![
            Span::styled(" [Tab] Switch Field ", Style::default().fg(Color::Cyan)),
            Span::raw(" | "),
            Span::styled(" [Enter] Save & Connect ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw(" | "),
            Span::styled(" [Esc] Back to Accounts ", Style::default().fg(Color::DarkGray)),
        ]);
        frame.render_widget(Paragraph::new(footer), layout[4]);
    }

    fn render_candidates_view(&self, frame: &mut Frame, area: Rect, border_style: Style, palette: &ThemePalette) {
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(Span::styled(
                " [ NICOTINE+ LOSSLESS P2P RETRIEVAL ] ",
                Style::default()
                    .fg(palette.primary)
                    .add_modifier(Modifier::BOLD),
            ))
            .title_alignment(Alignment::Center);

        let inner = block.inner(area);
        frame.render_widget(block, area);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Account info & search input
                Constraint::Min(6),    // Candidates table
                Constraint::Length(2), // Status bar & hotkeys
            ])
            .split(inner);

        let user_str = self
            .config
            .as_ref()
            .map(|c| format!("User: {}", c.username))
            .unwrap_or_else(|| "Local account".to_string());

        let input_line = Line::from(vec![
            Span::styled(
                format!(" [{}] Search: ", user_str),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                if self.query_input.is_empty() {
                    "Type query and press Enter..."
                } else {
                    &self.query_input
                },
                Style::default().fg(Color::White),
            ),
        ]);

        let input_p = Paragraph::new(input_line).block(
            Block::default()
                .borders(Borders::BOTTOM)
                .border_style(Style::default().fg(Color::DarkGray)),
        );
        frame.render_widget(input_p, layout[0]);

        let mut list_lines = Vec::new();
        list_lines.push(Line::from(vec![
            Span::styled(" RANK ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("PEER        ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("FORMAT  ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("DEPTH   ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("BITRATE  ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("SIZE     ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("SPEED     ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("FILENAME", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        ]));

        if self.candidates.is_empty() {
            list_lines.push(Line::from(Span::styled(
                "  No candidates loaded. Press Enter to search Nicotine+ network.",
                Style::default().fg(Color::DarkGray),
            )));
        } else {
            for (idx, c) in self.candidates.iter().take(15).enumerate() {
                let is_selected = idx == self.selected_idx;
                let bg_color = if is_selected {
                    Color::Rgb(30, 45, 70)
                } else {
                    Color::Reset
                };

                let rank_str = format!("  #{:02} ", idx + 1);
                let peer_str = format!("{:<12}", truncate_str(&c.username, 12));
                let fmt_str = if c.is_flac() { "FLAC    " } else if c.is_wav() { "WAV     " } else { "MP3     " };
                let depth_str = c.bit_depth.map(|d| format!("{:02}-bit  ", d)).unwrap_or_else(|| "--      ".into());
                let br_str = c.bitrate_kbps.map(|b| format!("{:>4}kbps ", b)).unwrap_or_else(|| "--       ".into());
                let size_str = format!("{:<9}", c.formatted_size());
                let speed_str = c.speed_kbps.map(|s| format!("{:.0}KB/s   ", s)).unwrap_or_else(|| "--        ".into());
                let name_str = truncate_str(&c.filename, 35);

                let row_style = if is_selected {
                    Style::default().fg(Color::Yellow).bg(bg_color).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(Color::White).bg(bg_color)
                };

                list_lines.push(Line::from(vec![
                    Span::styled(rank_str, Style::default().fg(Color::Green)),
                    Span::styled(peer_str, row_style),
                    Span::styled(fmt_str, Style::default().fg(Color::Magenta)),
                    Span::styled(depth_str, Style::default().fg(Color::Cyan)),
                    Span::styled(br_str, Style::default().fg(Color::White)),
                    Span::styled(size_str, Style::default().fg(Color::DarkGray)),
                    Span::styled(speed_str, Style::default().fg(Color::LightBlue)),
                    Span::styled(name_str, row_style),
                ]));
            }
        }

        let candidates_p = Paragraph::new(list_lines);
        frame.render_widget(candidates_p, layout[1]);

        let status_line = Line::from(vec![
            Span::styled(&self.status_msg, Style::default().fg(Color::Yellow)),
            Span::raw(" | "),
            Span::styled("[A] Accounts  [Enter] Select / Search  [Up/Down] Navigate  [Esc] Close", Style::default().fg(Color::DarkGray)),
        ]);
        let status_p = Paragraph::new(status_line);
        frame.render_widget(status_p, layout[2]);
    }
}

fn truncate_str(s: &str, max_len: usize) -> String {
    if s.len() > max_len {
        format!("{}...", &s[..max_len.saturating_sub(3)])
    } else {
        s.to_string()
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    pub fn test_nicotine_modal_creation_and_rescan() {
        let mut modal = NicotineModal::new();
        assert_eq!(modal.view_mode, NicotineModalView::Accounts);
        assert!(!modal.is_open);

        modal.open_accounts();
        assert!(modal.is_open);
        assert_eq!(modal.view_mode, NicotineModalView::Accounts);
    }
}
