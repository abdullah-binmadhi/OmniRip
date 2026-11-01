//! Universal Link Bank & Shared Libraries Drawer / Modal
//!
//! Allows users to store, paste, label, and sync multiple playlist links
//! (Spotify, YouTube Music, Apple Music, and shared friends' playlists).
//! Persisted automatically to ~/.config/omnirip/link_bank.json and links.txt.

use crate::harvest::link_bank::LinkBankStore;
use crate::harvest::StreamingService;
use crate::ui::streaming_hub::truncate_display_str;
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LinkBankInputMode {
    Normal,
    AddingUrl,
    EditingNote,
}

pub struct LinkBankModal {
    pub is_open: bool,
    pub store: LinkBankStore,
    pub selected_idx: usize,
    pub list_state: ListState,
    pub input_mode: LinkBankInputMode,
    pub input_buffer: String,
    pub status_message: Option<String>,
}

impl Default for LinkBankModal {
    fn default() -> Self {
        Self::new()
    }
}

impl LinkBankModal {
    pub fn new() -> Self {
        let store = LinkBankStore::load();
        let mut list_state = ListState::default();
        if !store.entries.is_empty() {
            list_state.select(Some(0));
        }
        Self {
            is_open: false,
            store,
            selected_idx: 0,
            list_state,
            input_mode: LinkBankInputMode::Normal,
            input_buffer: String::new(),
            status_message: None,
        }
    }

    pub fn open(&mut self) {
        self.store.reload();
        self.is_open = true;
        self.input_mode = LinkBankInputMode::Normal;
        self.input_buffer.clear();
        self.status_message = None;
        if self.selected_idx >= self.store.entries.len() {
            self.selected_idx = self.store.entries.len().saturating_sub(1);
        }
        self.list_state.select(if self.store.entries.is_empty() { None } else { Some(self.selected_idx) });
    }

    pub fn close(&mut self) {
        self.is_open = false;
        self.input_mode = LinkBankInputMode::Normal;
        self.input_buffer.clear();
    }

    pub fn handle_key(&mut self, key: KeyCode) -> bool {
        match self.input_mode {
            LinkBankInputMode::AddingUrl => match key {
                KeyCode::Esc => {
                    self.input_mode = LinkBankInputMode::Normal;
                    self.input_buffer.clear();
                    true
                }
                KeyCode::Enter => {
                    let trimmed = self.input_buffer.trim().to_string();
                    if !trimmed.is_empty() {
                        let entry = self.store.add_link(&trimmed, None, None);
                        let _ = self.store.save();
                        self.selected_idx = self.store.entries.len().saturating_sub(1);
                        self.list_state.select(Some(self.selected_idx));
                        self.status_message = Some(format!("Added {} link to Link Bank", entry.service.label()));
                    }
                    self.input_mode = LinkBankInputMode::Normal;
                    self.input_buffer.clear();
                    true
                }
                KeyCode::Backspace => {
                    self.input_buffer.pop();
                    true
                }
                KeyCode::Char(c) => {
                    self.input_buffer.push(c);
                    true
                }
                _ => false,
            },
            LinkBankInputMode::EditingNote => match key {
                KeyCode::Esc => {
                    self.input_mode = LinkBankInputMode::Normal;
                    self.input_buffer.clear();
                    true
                }
                KeyCode::Enter => {
                    if let Some(entry) = self.store.entries.get_mut(self.selected_idx) {
                        entry.curator = self.input_buffer.trim().to_string();
                        let title = entry.title.clone();
                        let _ = self.store.save();
                        self.status_message = Some(format!("Updated curator note for {}", title));
                    }
                    self.input_mode = LinkBankInputMode::Normal;
                    self.input_buffer.clear();
                    true
                }
                KeyCode::Backspace => {
                    self.input_buffer.pop();
                    true
                }
                KeyCode::Char(c) => {
                    self.input_buffer.push(c);
                    true
                }
                _ => false,
            },
            LinkBankInputMode::Normal => match key {
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('Q') => {
                    self.close();
                    true
                }
                KeyCode::Up | KeyCode::Char('k') => {
                    if self.selected_idx > 0 {
                        self.selected_idx -= 1;
                        self.list_state.select(Some(self.selected_idx));
                    }
                    true
                }
                KeyCode::Down | KeyCode::Char('j') => {
                    if self.selected_idx + 1 < self.store.entries.len() {
                        self.selected_idx += 1;
                        self.list_state.select(Some(self.selected_idx));
                    }
                    true
                }
                KeyCode::Char(' ') => {
                    if let Some(entry) = self.store.entries.get_mut(self.selected_idx) {
                        entry.enabled = !entry.enabled;
                        let is_act = entry.enabled;
                        let title = entry.title.clone();
                        let _ = self.store.save();
                        self.status_message = Some(format!(
                            "{} is now {}",
                            title,
                            if is_act { "ENABLED" } else { "DISABLED" }
                        ));
                    }
                    true
                }
                KeyCode::Char('p') | KeyCode::Char('P') | KeyCode::Char('a') | KeyCode::Char('A') => {
                    self.input_mode = LinkBankInputMode::AddingUrl;
                    self.input_buffer.clear();
                    true
                }
                KeyCode::Char('n') | KeyCode::Char('N') | KeyCode::Char('e') | KeyCode::Char('E') => {
                    if let Some(entry) = self.store.entries.get(self.selected_idx) {
                        self.input_buffer = if entry.curator == "Shared Collection" {
                            String::new()
                        } else {
                            entry.curator.clone()
                        };
                        self.input_mode = LinkBankInputMode::EditingNote;
                    }
                    true
                }
                KeyCode::Char('d') | KeyCode::Char('D') | KeyCode::Delete | KeyCode::Backspace => {
                    if !self.store.entries.is_empty() {
                        let removed = self.store.entries.remove(self.selected_idx);
                        let _ = self.store.save();
                        if self.selected_idx >= self.store.entries.len() && self.selected_idx > 0 {
                            self.selected_idx -= 1;
                        }
                        self.list_state.select(if self.store.entries.is_empty() {
                            None
                        } else {
                            Some(self.selected_idx)
                        });
                        self.status_message = Some(format!("Removed {}", removed.title));
                    }
                    true
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.store.reload();
                    self.selected_idx = 0;
                    self.list_state.select(if self.store.entries.is_empty() { None } else { Some(0) });
                    self.status_message = Some("Reloaded from disk and links.txt".to_string());
                    true
                }
                _ => false,
            },
        }
    }

    pub fn render(&self, f: &mut ratatui::Frame, area: Rect, palette: &ThemePalette) {
        if !self.is_open {
            return;
        }

        let modal_w = 88u16.min(area.width.saturating_sub(4));
        let modal_h = 24u16.min(area.height.saturating_sub(2));
        let modal_x = (area.width.saturating_sub(modal_w)) / 2;
        let modal_y = (area.height.saturating_sub(modal_h)) / 2;
        let modal_rect = Rect::new(modal_x, modal_y, modal_w, modal_h);

        f.render_widget(Clear, modal_rect);

        let main_block = Block::default()
            .title(Span::styled(
                " UNIVERSAL LINK BANK & SHARED LIBRARIES [ESC/Q: Close] ",
                Style::default().fg(palette.accent).add_modifier(Modifier::BOLD),
            ))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(palette.accent));

        let inner = main_block.inner(modal_rect);
        f.render_widget(main_block, modal_rect);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Instructions & file path
                Constraint::Min(8),    // List of links
                Constraint::Length(3), // Input prompt / Status bar
            ])
            .split(inner);

        // Header instructions
        let instructions = vec![
            Line::from(vec![
                Span::styled("[P/A] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Paste/Add Link  "),
                Span::styled("[Space] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Toggle  "),
                Span::styled("[N] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Curator Note  "),
                Span::styled("[D] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Delete  "),
                Span::styled("[R] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Sync links.txt"),
            ]),
            Line::from(vec![
                Span::styled("Persistent Storage: ", Style::default().fg(Color::DarkGray)),
                Span::styled(
                    "~/.config/omnirip/link_bank.json & links.txt (Auto-detected on boot/sync)",
                    Style::default().fg(Color::Cyan),
                ),
            ]),
        ];
        f.render_widget(Paragraph::new(instructions).alignment(Alignment::Left), chunks[0]);

        // Entries list
        if self.store.entries.is_empty() {
            let empty_text = vec![
                Line::from(""),
                Line::from(Span::styled(
                    "No links saved in Link Bank yet.",
                    Style::default().fg(Color::DarkGray).add_modifier(Modifier::ITALIC),
                )),
                Line::from(""),
                Line::from(Span::styled(
                    "Press [P] or [A] to paste a Spotify, YouTube Music, or Apple Music link.",
                    Style::default().fg(palette.accent),
                )),
                Line::from(Span::styled(
                    "You can also paste shared playlists from friends with custom curator labels!",
                    Style::default().fg(Color::Gray),
                )),
            ];
            f.render_widget(
                Paragraph::new(empty_text).alignment(Alignment::Center),
                chunks[1],
            );
        } else {
            let mut list_items = Vec::new();
            for (idx, entry) in self.store.entries.iter().enumerate() {
                let is_selected = idx == self.selected_idx;
                let active_box = if entry.enabled { "[X]" } else { "[ ]" };
                let active_style = if entry.enabled {
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(Color::DarkGray)
                };

                let (svc_tag, svc_color) = match entry.service {
                    StreamingService::Spotify => ("SPOTIFY", Color::Rgb(30, 215, 96)),
                    StreamingService::YouTubeMusic => ("YT MUSIC", Color::Rgb(255, 60, 60)),
                    StreamingService::AppleMusic => ("APPLE", Color::Rgb(250, 88, 106)),
                    StreamingService::LocalM3u => ("M3U/CSV", Color::Cyan),
                    StreamingService::Unknown => ("LINK", Color::Gray),
                };

                let note_display = if !entry.curator.is_empty() && entry.curator != "Shared Collection" {
                    format!(" [{}]", truncate_display_str(&entry.curator, 18))
                } else {
                    String::new()
                };

                let title_w = (chunks[1].width as usize).saturating_sub(42).max(15);
                let title_str = truncate_display_str(&entry.title, title_w);
                let url_w = (chunks[1].width as usize).saturating_sub(48).max(20);
                let url_str = truncate_display_str(&entry.url, url_w);

                let row_style = if is_selected {
                    Style::default().bg(Color::Rgb(35, 45, 65)).fg(Color::White)
                } else {
                    Style::default()
                };

                let mut spans = vec![
                    Span::styled(format!(" {} ", active_box), active_style),
                    Span::styled(
                        format!("[{:^8}] ", svc_tag),
                        Style::default().fg(svc_color).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        format!("{:<width$}", title_str, width = title_w),
                        if is_selected {
                            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                        } else {
                            Style::default().fg(Color::Rgb(220, 220, 220))
                        },
                    ),
                ];

                if !note_display.is_empty() {
                    spans.push(Span::styled(
                        format!("{:<20}", note_display),
                        Style::default().fg(Color::Yellow).add_modifier(Modifier::ITALIC),
                    ));
                } else {
                    spans.push(Span::raw(" ".repeat(20)));
                }

                spans.push(Span::styled(
                    url_str,
                    Style::default().fg(Color::DarkGray),
                ));

                list_items.push(ListItem::new(Line::from(spans)).style(row_style));
            }

            let entries_list = List::new(list_items)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(Color::Rgb(60, 60, 80)))
                        .title(Span::styled(
                            format!(" Saved Links ({}) ", self.store.entries.len()),
                            Style::default().fg(Color::Cyan),
                        )),
                )
                .highlight_symbol("▶ ");

            f.render_stateful_widget(entries_list, chunks[1], &mut self.list_state.clone());
        }

        // Input or Status bar
        match self.input_mode {
            LinkBankInputMode::AddingUrl => {
                let input_widget = Paragraph::new(Line::from(vec![
                    Span::styled(" PASTE / TYPE URL: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                    Span::styled(&self.input_buffer, Style::default().fg(Color::White)),
                    Span::styled("█", Style::default().fg(palette.accent)),
                    Span::styled(" [ENTER: Save | ESC: Cancel]", Style::default().fg(Color::DarkGray)),
                ]))
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(Color::Yellow))
                        .title(" Add New Library Link "),
                );
                f.render_widget(input_widget, chunks[2]);
            }
            LinkBankInputMode::EditingNote => {
                let input_widget = Paragraph::new(Line::from(vec![
                    Span::styled(" CURATOR / FRIEND LABEL: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                    Span::styled(&self.input_buffer, Style::default().fg(Color::White)),
                    Span::styled("█", Style::default().fg(palette.accent)),
                    Span::styled(" [ENTER: Save | ESC: Cancel]", Style::default().fg(Color::DarkGray)),
                ]))
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(Color::Cyan))
                        .title(" Edit Friend / Curator Label "),
                );
                f.render_widget(input_widget, chunks[2]);
            }
            LinkBankInputMode::Normal => {
                let status_text = if let Some(ref msg) = self.status_message {
                    Line::from(vec![
                        Span::styled(" STATUS: ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                        Span::styled(msg, Style::default().fg(Color::White)),
                    ])
                } else {
                    Line::from(vec![
                        Span::styled(" TIP: ", Style::default().fg(palette.accent).add_modifier(Modifier::BOLD)),
                        Span::raw("Add your friends' shared playlists to sync and harvest their tracklists effortlessly."),
                    ])
                };
                let status_widget = Paragraph::new(status_text)
                    .block(
                        Block::default()
                            .borders(Borders::ALL)
                            .border_style(Style::default().fg(Color::Rgb(50, 50, 70))),
                    );
                f.render_widget(status_widget, chunks[2]);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_link_bank_modal_open_close_navigation() {
        let mut modal = LinkBankModal::default();
        assert!(!modal.is_open);

        modal.open();
        assert!(modal.is_open);
        assert_eq!(modal.input_mode, LinkBankInputMode::Normal);

        // Add dummy entry
        modal.store.add_link("https://open.spotify.com/playlist/test1", Some("Bestie Alex"), None);
        modal.store.add_link("https://music.youtube.com/playlist?list=PL2", Some("Gym Mix"), None);

        modal.selected_idx = 0;
        modal.handle_key(KeyCode::Down);
        assert_eq!(modal.selected_idx, 1);

        modal.handle_key(KeyCode::Up);
        assert_eq!(modal.selected_idx, 0);

        modal.handle_key(KeyCode::Esc);
        assert!(!modal.is_open);
    }

    #[test]
    fn test_link_bank_modal_add_url_and_edit_note() {
        let mut modal = LinkBankModal::default();
        modal.open();

        // Trigger Add Url
        modal.handle_key(KeyCode::Char('p'));
        assert_eq!(modal.input_mode, LinkBankInputMode::AddingUrl);

        // Type characters
        for c in "https://open.spotify.com/playlist/3xx123".chars() {
            modal.handle_key(KeyCode::Char(c));
        }
        assert_eq!(modal.input_buffer, "https://open.spotify.com/playlist/3xx123");

        // Submit Enter
        modal.handle_key(KeyCode::Enter);
        assert_eq!(modal.input_mode, LinkBankInputMode::Normal);
        assert!(modal.input_buffer.is_empty());
        let last = modal.store.entries.last().unwrap();
        assert!(last.url.contains("3xx123"));
        assert_eq!(last.service, StreamingService::Spotify);

        // Trigger Edit Curator Note
        modal.selected_idx = modal.store.entries.len() - 1;
        modal.handle_key(KeyCode::Char('n'));
        assert_eq!(modal.input_mode, LinkBankInputMode::EditingNote);

        for c in "Sarah's Roadtrip".chars() {
            modal.handle_key(KeyCode::Char(c));
        }
        modal.handle_key(KeyCode::Enter);
        assert_eq!(modal.input_mode, LinkBankInputMode::Normal);
        assert_eq!(modal.store.entries.last().unwrap().curator, "Sarah's Roadtrip");
    }

    #[test]
    fn test_link_bank_modal_toggle_and_delete() {
        let mut modal = LinkBankModal::default();
        modal.open();
        modal.store.add_link("https://music.apple.com/us/playlist/lofi/pl.u-123", Some("Chill Beats"), None);
        modal.selected_idx = modal.store.entries.len() - 1;

        assert!(modal.store.entries[modal.selected_idx].enabled);
        modal.handle_key(KeyCode::Char(' '));
        assert!(!modal.store.entries[modal.selected_idx].enabled);

        let count_before = modal.store.entries.len();
        modal.handle_key(KeyCode::Char('d'));
        assert_eq!(modal.store.entries.len(), count_before - 1);
    }
}
