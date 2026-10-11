//! Modal popup interface for Preset Management: Save, Squiglink Import, and Remote Download.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Clear, Paragraph, Wrap},
    Frame,
};

/// Action triggered by user keyboard interactions inside the modal.
#[derive(Debug, Clone, PartialEq)]
pub enum ModalKeyAction {
    None,
    Close,
    SubmitSaveCurrent { name: String },
    SubmitImportSquiglink { name: String, text: String },
    SubmitDownloadUrl { name: String, url: String },
}

/// Active state and form fields for the Preset Management modal.
#[derive(Debug, Clone, PartialEq)]
pub enum PresetModalState {
    Hidden,
    SaveCurrent {
        name_input: String,
        error_msg: Option<String>,
    },
    ImportSquiglink {
        name_input: String,
        text_input: String,
        focus_index: usize, // 0 = Preset Name, 1 = EqualizerAPO Text
        error_msg: Option<String>,
    },
    DownloadUrl {
        name_input: String,
        url_input: String,
        focus_index: usize, // 0 = Preset Name, 1 = Download URL
        status_msg: Option<String>,
        is_loading: bool,
    },
}

impl PresetModalState {
    pub fn is_active(&self) -> bool {
        !matches!(self, PresetModalState::Hidden)
    }

    pub fn new_save_current() -> Self {
        PresetModalState::SaveCurrent {
            name_input: String::new(),
            error_msg: None,
        }
    }

    pub fn new_import_squiglink() -> Self {
        PresetModalState::ImportSquiglink {
            name_input: String::new(),
            text_input: String::new(),
            focus_index: 0,
            error_msg: None,
        }
    }

    pub fn new_download_url() -> Self {
        PresetModalState::DownloadUrl {
            name_input: String::new(),
            url_input: String::new(),
            focus_index: 0,
            status_msg: None,
            is_loading: false,
        }
    }

    pub fn paste_text(&mut self, text: &str) {
        match self {
            PresetModalState::Hidden => {}
            PresetModalState::SaveCurrent { name_input, error_msg } => {
                name_input.push_str(text.trim());
                *error_msg = None;
            }
            PresetModalState::ImportSquiglink { name_input, text_input, focus_index, error_msg } => {
                if *focus_index == 0 {
                    name_input.push_str(text.trim());
                } else {
                    text_input.push_str(text);
                }
                *error_msg = None;
            }
            PresetModalState::DownloadUrl { name_input, url_input, focus_index, status_msg, .. } => {
                if *focus_index == 0 {
                    name_input.push_str(text.trim());
                } else {
                    url_input.push_str(text.trim());
                }
                *status_msg = None;
            }
        }
    }

    pub fn handle_key(&mut self, key: KeyEvent) -> ModalKeyAction {
        match self {
            PresetModalState::Hidden => ModalKeyAction::None,
            PresetModalState::SaveCurrent { name_input, error_msg } => {
                match key.code {
                    KeyCode::Esc => {
                        *self = PresetModalState::Hidden;
                        ModalKeyAction::Close
                    }
                    KeyCode::Enter => {
                        let trimmed = name_input.trim();
                        if trimmed.is_empty() {
                            *error_msg = Some("Preset name cannot be empty".to_string());
                            ModalKeyAction::None
                        } else {
                            ModalKeyAction::SubmitSaveCurrent {
                                name: trimmed.to_string(),
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        name_input.pop();
                        *error_msg = None;
                        ModalKeyAction::None
                    }
                    KeyCode::Char(c) => {
                        if !key.modifiers.contains(KeyModifiers::CONTROL) {
                            name_input.push(c);
                            *error_msg = None;
                        }
                        ModalKeyAction::None
                    }
                    _ => ModalKeyAction::None,
                }
            }
            PresetModalState::ImportSquiglink {
                name_input,
                text_input,
                focus_index,
                error_msg,
            } => {
                match key.code {
                    KeyCode::Esc => {
                        *self = PresetModalState::Hidden;
                        ModalKeyAction::Close
                    }
                    KeyCode::Tab | KeyCode::BackTab => {
                        *focus_index = if *focus_index == 0 { 1 } else { 0 };
                        ModalKeyAction::None
                    }
                    KeyCode::Enter => {
                        if *focus_index == 0 {
                            // Move focus to text area on enter from name
                            *focus_index = 1;
                            ModalKeyAction::None
                        } else {
                            // In text area, Ctrl+Enter or Enter when name is set can submit
                            let trimmed_name = name_input.trim();
                            let trimmed_text = text_input.trim();
                            if trimmed_name.is_empty() {
                                *error_msg = Some("Preset name cannot be empty".to_string());
                                *focus_index = 0;
                                ModalKeyAction::None
                            } else if trimmed_text.is_empty() {
                                *error_msg = Some("EqualizerAPO text buffer cannot be empty".to_string());
                                ModalKeyAction::None
                            } else {
                                ModalKeyAction::SubmitImportSquiglink {
                                    name: trimmed_name.to_string(),
                                    text: trimmed_text.to_string(),
                                }
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        if *focus_index == 0 {
                            name_input.pop();
                        } else {
                            text_input.pop();
                        }
                        *error_msg = None;
                        ModalKeyAction::None
                    }
                    KeyCode::Char(c) => {
                        if !key.modifiers.contains(KeyModifiers::CONTROL) {
                            if *focus_index == 0 {
                                name_input.push(c);
                            } else {
                                text_input.push(c);
                            }
                            *error_msg = None;
                        }
                        ModalKeyAction::None
                    }
                    _ => ModalKeyAction::None,
                }
            }
            PresetModalState::DownloadUrl {
                name_input,
                url_input,
                focus_index,
                status_msg,
                is_loading,
            } => {
                if *is_loading {
                    return ModalKeyAction::None;
                }
                match key.code {
                    KeyCode::Esc => {
                        *self = PresetModalState::Hidden;
                        ModalKeyAction::Close
                    }
                    KeyCode::Tab | KeyCode::BackTab => {
                        *focus_index = if *focus_index == 0 { 1 } else { 0 };
                        ModalKeyAction::None
                    }
                    KeyCode::Enter => {
                        let trimmed_url = url_input.trim();
                        if trimmed_url.is_empty() {
                            *status_msg = Some("Download URL cannot be empty".to_string());
                            ModalKeyAction::None
                        } else {
                            let trimmed_name = name_input.trim();
                            let final_name = if trimmed_name.is_empty() {
                                // Default name from url basename
                                trimmed_url
                                    .rsplit('/')
                                    .next()
                                    .unwrap_or("Downloaded_Preset")
                                    .replace(".txt", "")
                                    .replace(".json", "")
                            } else {
                                trimmed_name.to_string()
                            };
                            ModalKeyAction::SubmitDownloadUrl {
                                name: final_name,
                                url: trimmed_url.to_string(),
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        if *focus_index == 0 {
                            name_input.pop();
                        } else {
                            url_input.pop();
                        }
                        *status_msg = None;
                        ModalKeyAction::None
                    }
                    KeyCode::Char(c) => {
                        if !key.modifiers.contains(KeyModifiers::CONTROL) {
                            if *focus_index == 0 {
                                name_input.push(c);
                            } else {
                                url_input.push(c);
                            }
                            *status_msg = None;
                        }
                        ModalKeyAction::None
                    }
                    _ => ModalKeyAction::None,
                }
            }
        }
    }
}

/// Helper function to create a centered Rect within the current terminal frame.
pub fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
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

/// Render the preset modal overlay over the application frame.
pub fn render_preset_modal(f: &mut Frame, area: Rect, state: &PresetModalState) {
    match state {
        PresetModalState::Hidden => {}
        PresetModalState::SaveCurrent { name_input, error_msg } => {
            let modal_area = centered_rect(60, 32, area);
            f.render_widget(Clear, modal_area);

            let block = Block::default()
                .title(" SAVE ACTIVE SETTINGS TO AUTOEQ [Shift+S] ")
                .title_alignment(Alignment::Center)
                .borders(Borders::ALL)
                .border_type(BorderType::Double)
                .border_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
                .style(Style::default().bg(Color::Rgb(15, 20, 28)));
            f.render_widget(block, modal_area);

            let inner = Layout::default()
                .direction(Direction::Vertical)
                .margin(2)
                .constraints([
                    Constraint::Length(2), // Subtitle
                    Constraint::Length(3), // Input field
                    Constraint::Length(2), // Error message or hint
                    Constraint::Length(2), // Controls footer
                ])
                .split(modal_area);

            let subtitle = Paragraph::new(Line::from(vec![
                Span::raw("Captures current 10-Band EQ, Preamp, Tube Warmth, Spatial Width & Volume Boost:"),
            ]))
            .style(Style::default().fg(Color::Gray));
            f.render_widget(subtitle, inner[0]);

            let input_text = format!("{}_", name_input);
            let input_box = Paragraph::new(input_text)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .title(" Preset Name ")
                        .border_style(Style::default().fg(Color::Yellow)),
                )
                .style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD));
            f.render_widget(input_box, inner[1]);

            if let Some(err) = error_msg {
                let err_widget = Paragraph::new(Line::from(vec![
                    Span::styled(format!("Error: {}", err), Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                ]));
                f.render_widget(err_widget, inner[2]);
            } else {
                let hint = Paragraph::new("Stored to ~/.config/omnirip/presets/ and loaded to AutoEQ profiles.")
                    .style(Style::default().fg(Color::DarkGray));
                f.render_widget(hint, inner[2]);
            }

            let controls = Paragraph::new(Line::from(vec![
                Span::styled("[ Enter: Save Preset ]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::raw("    "),
                Span::styled("[ Esc: Cancel ]", Style::default().fg(Color::Gray)),
            ]))
            .alignment(Alignment::Center);
            f.render_widget(controls, inner[3]);
        }

        PresetModalState::ImportSquiglink {
            name_input,
            text_input,
            focus_index,
            error_msg,
        } => {
            let modal_area = centered_rect(75, 75, area);
            f.render_widget(Clear, modal_area);

            let block = Block::default()
                .title(" IMPORT SQUIGLINK / EQUALIZERAPO TEXT [Shift+I] ")
                .title_alignment(Alignment::Center)
                .borders(Borders::ALL)
                .border_type(BorderType::Double)
                .border_style(Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
                .style(Style::default().bg(Color::Rgb(15, 20, 28)));
            f.render_widget(block, modal_area);

            let inner = Layout::default()
                .direction(Direction::Vertical)
                .margin(2)
                .constraints([
                    Constraint::Length(2), // Subtitle
                    Constraint::Length(3), // Name input
                    Constraint::Min(6),    // Text area
                    Constraint::Length(2), // Status/Error
                    Constraint::Length(2), // Controls footer
                ])
                .split(modal_area);

            let subtitle = Paragraph::new("Paste raw EqualizerAPO / Squiglink parametric text directly below:")
                .style(Style::default().fg(Color::Gray));
            f.render_widget(subtitle, inner[0]);

            // Name field
            let name_style = if *focus_index == 0 {
                Style::default().fg(Color::Yellow)
            } else {
                Style::default().fg(Color::DarkGray)
            };
            let name_display = if *focus_index == 0 {
                format!("{}_", name_input)
            } else {
                name_input.clone()
            };
            let name_box = Paragraph::new(name_display)
                .block(Block::default().borders(Borders::ALL).title(" Profile / IEM Name ").border_style(name_style))
                .style(Style::default().fg(Color::White));
            f.render_widget(name_box, inner[1]);

            // Text buffer field
            let text_style = if *focus_index == 1 {
                Style::default().fg(Color::Yellow)
            } else {
                Style::default().fg(Color::DarkGray)
            };
            let placeholder = if text_input.is_empty() && *focus_index != 1 {
                "e.g.\nPreamp: -4.5 dB\nFilter 1: ON PK Fc 32 Hz Gain 2.1 dB Q 1.41\nFilter 2: ON LSC Fc 105 Hz Gain 4.5 dB Q 0.71"
            } else if *focus_index == 1 {
                &format!("{}_", text_input)
            } else {
                text_input
            };

            let text_box = Paragraph::new(placeholder)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .title(" EqualizerAPO Parametric Text Buffer (Paste or Type) ")
                        .border_style(text_style),
                )
                .wrap(Wrap { trim: false })
                .style(Style::default().fg(Color::White));
            f.render_widget(text_box, inner[2]);

            if let Some(err) = error_msg {
                let err_widget = Paragraph::new(Line::from(vec![
                    Span::styled(format!("Error: {}", err), Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                ]));
                f.render_widget(err_widget, inner[3]);
            } else {
                let hint = Paragraph::new("Press Tab to toggle focus between Name and Parametric Buffer.")
                    .style(Style::default().fg(Color::DarkGray));
                f.render_widget(hint, inner[3]);
            }

            let controls = Paragraph::new(Line::from(vec![
                Span::styled("[ Enter: Import & Activate ]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::raw("    "),
                Span::styled("[ Tab: Switch Field ]", Style::default().fg(Color::Yellow)),
                Span::raw("    "),
                Span::styled("[ Esc: Cancel ]", Style::default().fg(Color::Gray)),
            ]))
            .alignment(Alignment::Center);
            f.render_widget(controls, inner[4]);
        }

        PresetModalState::DownloadUrl {
            name_input,
            url_input,
            focus_index,
            status_msg,
            is_loading,
        } => {
            let modal_area = centered_rect(65, 42, area);
            f.render_widget(Clear, modal_area);

            let border_color = if *is_loading { Color::Yellow } else { Color::Magenta };
            let block = Block::default()
                .title(" DOWNLOAD PARAMETRIC PRESET FROM URL [Shift+D] ")
                .title_alignment(Alignment::Center)
                .borders(Borders::ALL)
                .border_type(BorderType::Double)
                .border_style(Style::default().fg(border_color).add_modifier(Modifier::BOLD))
                .style(Style::default().bg(Color::Rgb(15, 20, 28)));
            f.render_widget(block, modal_area);

            let inner = Layout::default()
                .direction(Direction::Vertical)
                .margin(2)
                .constraints([
                    Constraint::Length(2), // Subtitle
                    Constraint::Length(3), // Preset Name
                    Constraint::Length(3), // URL Input
                    Constraint::Length(2), // Status/Error
                    Constraint::Length(2), // Controls footer
                ])
                .split(modal_area);

            let subtitle = Paragraph::new("Fetch raw parametric EqualizerAPO text from direct URL (5s timeout, 1MB limit):")
                .style(Style::default().fg(Color::Gray));
            f.render_widget(subtitle, inner[0]);

            let name_style = if *focus_index == 0 {
                Style::default().fg(Color::Yellow)
            } else {
                Style::default().fg(Color::DarkGray)
            };
            let name_display = if *focus_index == 0 {
                format!("{}_", name_input)
            } else {
                name_input.clone()
            };
            let name_box = Paragraph::new(name_display)
                .block(Block::default().borders(Borders::ALL).title(" Preset Name (Optional) ").border_style(name_style))
                .style(Style::default().fg(Color::White));
            f.render_widget(name_box, inner[1]);

            let url_style = if *focus_index == 1 {
                Style::default().fg(Color::Yellow)
            } else {
                Style::default().fg(Color::DarkGray)
            };
            let url_display = if *focus_index == 1 {
                format!("{}_", url_input)
            } else {
                url_input.clone()
            };
            let url_box = Paragraph::new(url_display)
                .block(Block::default().borders(Borders::ALL).title(" Raw Preset URL (HTTP / HTTPS) ").border_style(url_style))
                .style(Style::default().fg(Color::White));
            f.render_widget(url_box, inner[2]);

            if *is_loading {
                let loading_msg = Paragraph::new(Line::from(vec![
                    Span::styled("Fetching preset over network...", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                ]));
                f.render_widget(loading_msg, inner[3]);
            } else if let Some(status) = status_msg {
                let status_color = if status.to_lowercase().contains("error") || status.to_lowercase().contains("failed") {
                    Color::Red
                } else {
                    Color::Green
                };
                let status_widget = Paragraph::new(Line::from(vec![
                    Span::styled(status.clone(), Style::default().fg(status_color).add_modifier(Modifier::BOLD)),
                ]));
                f.render_widget(status_widget, inner[3]);
            } else {
                let hint = Paragraph::new("Press Tab to cycle fields. Enter to initiate safe download.")
                    .style(Style::default().fg(Color::DarkGray));
                f.render_widget(hint, inner[3]);
            }

            let controls = Paragraph::new(Line::from(vec![
                Span::styled("[ Enter: Download & Apply ]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::raw("    "),
                Span::styled("[ Tab: Switch Field ]", Style::default().fg(Color::Yellow)),
                Span::raw("    "),
                Span::styled("[ Esc: Cancel ]", Style::default().fg(Color::Gray)),
            ]))
            .alignment(Alignment::Center);
            f.render_widget(controls, inner[4]);
        }
    }
}
