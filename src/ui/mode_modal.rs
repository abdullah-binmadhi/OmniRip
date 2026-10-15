//! Startup Mode Selection Modal for OmniRip.
//! Presents a high-contrast popup asking the user whether to launch
//! the MP3 Downloader & Harvester or the System EQ & Audiophile Mastering Suite.

use crate::ui::theme::ThemePalette;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, Paragraph, Wrap};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkstationMode {
    Downloader,
    SystemEq,
    Archiver,
    StreamingHub,
}

pub struct ModeModal {
    pub is_open: bool,
    pub selected_index: usize,
}

impl ModeModal {
    pub fn new() -> Self {
        Self {
            is_open: true, // Opened on startup by default
            selected_index: 0,
        }
    }

    pub fn toggle(&mut self) {
        self.is_open = !self.is_open;
    }

    pub fn current_mode(&self) -> WorkstationMode {
        match self.selected_index {
            0 => WorkstationMode::Downloader,
            1 => WorkstationMode::SystemEq,
            2 => WorkstationMode::Archiver,
            _ => WorkstationMode::StreamingHub,
        }
    }

    pub fn render(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        if !self.is_open {
            return;
        }

        // Center a modal card (width 94, height 26)
        let popup_width = 94.min(area.width.saturating_sub(2));
        let popup_height = 26.min(area.height.saturating_sub(2));

        let vertical_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length((area.height.saturating_sub(popup_height)) / 2),
                Constraint::Length(popup_height),
                Constraint::Min(0),
            ])
            .split(area);

        let horizontal_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length((area.width.saturating_sub(popup_width)) / 2),
                Constraint::Length(popup_width),
                Constraint::Min(0),
            ])
            .split(vertical_chunks[1]);

        let card_area = horizontal_chunks[1];

        // Clear beneath modal
        f.render_widget(Clear, card_area);

        let block = Block::default()
            .title(" OMNIRIP WORKSTATION - SELECT STARTUP MODE ")
            .title_alignment(Alignment::Center)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary).add_modifier(Modifier::BOLD))
            .style(Style::default().bg(theme.background));

        let inner = block.inner(card_area);
        f.render_widget(block, card_area);

        let opt1_selected = self.selected_index == 0;
        let opt2_selected = self.selected_index == 1;
        let opt3_selected = self.selected_index == 2;
        let opt4_selected = self.selected_index == 3;

        let opt1_style = if opt1_selected {
            Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };

        let opt2_style = if opt2_selected {
            Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };

        let opt3_style = if opt3_selected {
            Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };

        let opt4_style = if opt4_selected {
            Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };

        let opt1_prefix = if opt1_selected { "> " } else { "  " };
        let opt2_prefix = if opt2_selected { "> " } else { "  " };
        let opt3_prefix = if opt3_selected { "> " } else { "  " };
        let opt4_prefix = if opt4_selected { "> " } else { "  " };

        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("Choose your primary workspace for this session:", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("{}[1] MP3 Downloader & Media Harvester", opt1_prefix), opt1_style),
            ]),
            Line::from(vec![
                Span::styled("     Paste URLs, Soulseek P2P swarm hunt, yt-dlp ripping, ID3 tagging, spectral check.", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("{}[2] System EQ & Audiophile Mastering Suite", opt2_prefix), opt2_style),
            ]),
            Line::from(vec![
                Span::styled("     CoreAudio loopback, 10-band EQ, tube warmth, soundstage widener, AutoEQ calibration.", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("{}[3] Cloud Playlist Archiver & Lossless Ingestion", opt3_prefix), opt3_style),
            ]),
            Line::from(vec![
                Span::styled("     Spotify, Apple Music, and YouTube playlist ingestion, custom folder hierarchies, M3U8 export.", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("{}[4] Cloud Streaming Hub & Universal Music Player", opt4_prefix), opt4_style),
            ]),
            Line::from(vec![
                Span::styled("     Unified player for Spotify, Apple Music & YouTube Music via high-bitrate Opus streams & DSP.", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" [1 / 2 / 3 / 4] Select Directly   [Up/Down] Navigate   [Enter] Launch   [M / Esc] Close", Style::default().fg(theme.accent)),
            ]),
        ];

        let p = Paragraph::new(lines).alignment(Alignment::Left).wrap(Wrap { trim: false });
        f.render_widget(p, inner);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mode_modal_defaults() {
        let mut modal = ModeModal::new();
        assert!(modal.is_open);
        assert_eq!(modal.current_mode(), WorkstationMode::Downloader);

        modal.selected_index = 1;
        assert_eq!(modal.current_mode(), WorkstationMode::SystemEq);

        modal.selected_index = 2;
        assert_eq!(modal.current_mode(), WorkstationMode::Archiver);

        modal.selected_index = 3;
        assert_eq!(modal.current_mode(), WorkstationMode::StreamingHub);
    }
}
