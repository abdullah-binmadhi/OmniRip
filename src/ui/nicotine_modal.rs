//! Nicotine+ Lossless Candidate Browser & Search Modal for OmniRip.
//! Allows searching the Soulseek network via Nicotine+ and viewing peer candidates ranked by lossless fidelity.

use crate::harvest::nicotine::{score_candidate, NicotineCandidate, NicotineConfig};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, Paragraph};
use ratatui::Frame;

pub enum NicotineModalAction {
    Close,
    SubmitSearch(String),
    SelectCandidate(NicotineCandidate),
}

pub struct NicotineModal {
    pub is_open: bool,
    pub config: Option<NicotineConfig>,
    pub query_input: String,
    pub candidates: Vec<NicotineCandidate>,
    pub selected_idx: usize,
    pub status_msg: String,
}

impl NicotineModal {
    pub fn new() -> Self {
        let config = NicotineConfig::detect_local();
        let status_msg = if let Some(ref cfg) = config {
            format!("Connected to Nicotine+ account: {}", cfg.username)
        } else {
            "Nicotine+ config not found in standard paths. Ready for search.".to_string()
        };

        Self {
            is_open: false,
            config,
            query_input: String::new(),
            candidates: Vec::new(),
            selected_idx: 0,
            status_msg,
        }
    }

    pub fn open_with_query(&mut self, query: &str) {
        self.is_open = true;
        self.query_input = query.to_string();
        self.status_msg = format!("Ready to search for: {}", query);
    }

    pub fn set_candidates(&mut self, mut candidates: Vec<NicotineCandidate>) {
        // Sort by fidelity score descending
        for c in candidates.iter_mut() {
            c.score = score_candidate(c);
        }
        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        self.candidates = candidates;
        self.selected_idx = 0;
        self.status_msg = format!("Found {} lossless candidates", self.candidates.len());
    }

    pub fn handle_key(&mut self, code: KeyCode) -> Option<NicotineModalAction> {
        if !self.is_open {
            return None;
        }

        match code {
            KeyCode::Esc => {
                self.is_open = false;
                Some(NicotineModalAction::Close)
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
        }
    }

    pub fn render(&self, frame: &mut Frame, area: Rect, palette: &ThemePalette) {
        if !self.is_open {
            return;
        }

        // Center popup modal
        let popup_width = (area.width * 85 / 100).max(60);
        let popup_height = (area.height * 80 / 100).max(18);
        let x = (area.width.saturating_sub(popup_width)) / 2;
        let y = (area.height.saturating_sub(popup_height)) / 2;
        let modal_area = Rect::new(x, y, popup_width, popup_height);

        frame.render_widget(Clear, modal_area);

        let border_style = Style::default().fg(palette.accent);

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

        let inner = block.inner(modal_area);
        frame.render_widget(block, modal_area);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Account info & search input
                Constraint::Min(6),    // Candidates table
                Constraint::Length(2), // Status bar & hotkeys
            ])
            .split(inner);

        // Render search input line
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

        // Render candidates
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

        // Status bar & controls
        let status_line = Line::from(vec![
            Span::styled(&self.status_msg, Style::default().fg(Color::Yellow)),
            Span::raw(" | "),
            Span::styled("[Enter] Select / Search  [Up/Down] Navigate  [Esc] Close", Style::default().fg(Color::DarkGray)),
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
