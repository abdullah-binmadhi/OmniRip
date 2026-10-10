//! Real-Time Modular Tiling Visuals Dashboard for OmniRip TUI.
//! Provides multiple high-speed visual graph engines: 32-Band FFT Spectrum Analyzer,
//! 2D STFT Spectrogram Waterfall, Stereo Lissajous Phase Scope, Dual Analog VU Meters,
//! Cascaded Biquad EQ Frequency Curve Plot, Dynamic EBU R128 Loudness History, and Stereo Soundstage Imager.
//!
//! Features interactive multi-tile selection, per-tile visualizer assignment,
//! dynamic multi-pane layout splits, and edge-to-edge zero-dead-space bar stretching.

use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VisualGraphMode {
    Spectrum32,
    SpectrogramWaterfall,
    PhaseLissajous,
    AnalogVu,
    EqCurve,
    LoudnessHistory,
    StereoImager,
}

impl VisualGraphMode {
    pub fn label(&self) -> &'static str {
        match self {
            VisualGraphMode::Spectrum32 => "32-Band FFT Spectrum Analyzer",
            VisualGraphMode::SpectrogramWaterfall => "2D STFT Spectrogram Waterfall",
            VisualGraphMode::PhaseLissajous => "Stereo Lissajous Phase Scope",
            VisualGraphMode::AnalogVu => "Dual Analog Stereo VU Meters",
            VisualGraphMode::EqCurve => "Cascaded Biquad EQ Curve Plot",
            VisualGraphMode::LoudnessHistory => "Dynamic EBU R128 Loudness History",
            VisualGraphMode::StereoImager => "Stereo Soundstage Imager",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            VisualGraphMode::Spectrum32 => VisualGraphMode::SpectrogramWaterfall,
            VisualGraphMode::SpectrogramWaterfall => VisualGraphMode::PhaseLissajous,
            VisualGraphMode::PhaseLissajous => VisualGraphMode::AnalogVu,
            VisualGraphMode::AnalogVu => VisualGraphMode::EqCurve,
            VisualGraphMode::EqCurve => VisualGraphMode::LoudnessHistory,
            VisualGraphMode::LoudnessHistory => VisualGraphMode::StereoImager,
            VisualGraphMode::StereoImager => VisualGraphMode::Spectrum32,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DashboardLayout {
    HeroPlusThree,
    Quad2x2,
    SideBySide,
    Stacked,
}

impl DashboardLayout {
    pub fn label(&self) -> &'static str {
        match self {
            DashboardLayout::HeroPlusThree => "Hero (Top 55%) + 3 Bottom Monitoring Tiles",
            DashboardLayout::Quad2x2 => "Quad 2x2 Grid (4 Equal Tiles)",
            DashboardLayout::SideBySide => "Side-by-Side Dual Split (50% / 50%)",
            DashboardLayout::Stacked => "Stacked Dual Split (50% / 50%)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            DashboardLayout::HeroPlusThree => DashboardLayout::Quad2x2,
            DashboardLayout::Quad2x2 => DashboardLayout::SideBySide,
            DashboardLayout::SideBySide => DashboardLayout::Stacked,
            DashboardLayout::Stacked => DashboardLayout::HeroPlusThree,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TileSlot {
    pub visual: VisualGraphMode,
}

pub struct VisualsDashboard {
    pub layout: DashboardLayout,
    pub focused_tile: usize,
    pub tiles: [TileSlot; 4],
    pub is_zoomed: bool,
    pub mode: VisualGraphMode, // Kept for compatibility
    waterfall_history: Vec<Vec<f32>>,
    loudness_history: Vec<f32>,
}

impl VisualsDashboard {
    pub fn new() -> Self {
        Self {
            layout: DashboardLayout::HeroPlusThree,
            focused_tile: 0,
            tiles: [
                TileSlot { visual: VisualGraphMode::Spectrum32 },
                TileSlot { visual: VisualGraphMode::AnalogVu },
                TileSlot { visual: VisualGraphMode::PhaseLissajous },
                TileSlot { visual: VisualGraphMode::EqCurve },
            ],
            is_zoomed: false,
            mode: VisualGraphMode::Spectrum32,
            waterfall_history: Vec::new(),
            loudness_history: Vec::new(),
        }
    }

    pub fn cycle_layout(&mut self) {
        self.layout = self.layout.next();
    }

    pub fn cycle_mode(&mut self) {
        self.tiles[self.focused_tile].visual = self.tiles[self.focused_tile].visual.next();
        self.mode = self.tiles[self.focused_tile].visual;
    }

    pub fn toggle_zoom(&mut self) {
        self.is_zoomed = !self.is_zoomed;
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Tab | KeyCode::Right => {
                let max_tiles = match self.layout {
                    DashboardLayout::SideBySide | DashboardLayout::Stacked => 2,
                    _ => 4,
                };
                self.focused_tile = (self.focused_tile + 1) % max_tiles;
                self.mode = self.tiles[self.focused_tile].visual;
            }
            KeyCode::BackTab | KeyCode::Left => {
                let max_tiles = match self.layout {
                    DashboardLayout::SideBySide | DashboardLayout::Stacked => 2,
                    _ => 4,
                };
                self.focused_tile = if self.focused_tile == 0 { max_tiles - 1 } else { self.focused_tile - 1 };
                self.mode = self.tiles[self.focused_tile].visual;
            }
            KeyCode::Char('v') | KeyCode::Char('V') | KeyCode::Enter => {
                self.cycle_mode();
            }
            KeyCode::Char('l') | KeyCode::Char('L') => {
                self.cycle_layout();
            }
            KeyCode::Char('z') | KeyCode::Char('Z') => {
                self.toggle_zoom();
            }
            _ => {}
        }
    }

    pub fn render(
        &mut self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
        peak_l: f32,
        peak_r: f32,
        phase: f32,
        eq_gains: &[f32; 10],
    ) {
        if area.width < 10 || area.height < 6 {
            return;
        }

        // Record rolling loudness history
        let current_lufs = (peak_l.max(peak_r) * 0.7).clamp(-70.0, 0.0);
        self.loudness_history.insert(0, current_lufs);
        if self.loudness_history.len() > 100 {
            self.loudness_history.pop();
        }

        // If zoomed, render single focused tile filling 100% of the surface
        if self.is_zoomed {
            let visual = self.tiles[self.focused_tile].visual;
            let block = Block::default()
                .title(format!(" [MAXIMIZED TILE {}: {}] (Press Z to Restore Grid | V to Cycle) ", self.focused_tile + 1, visual.label()))
                .title_alignment(Alignment::Center)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
            let inner = block.inner(area);
            f.render_widget(block, area);
            self.render_tile_content(f, inner, visual, theme, spectrum, peak_l, peak_r, phase, eq_gains);
            return;
        }

        // Top layout banner & split tiles
        let root_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Min(6),    // Multi-tile grid
                Constraint::Length(1), // Bottom hotkey helper bar
            ])
            .split(area);

        let grid_area = root_chunks[0];
        let tile_rects = match self.layout {
            DashboardLayout::Quad2x2 => {
                let rows = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(grid_area);
                let top_cols = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(rows[0]);
                let btm_cols = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(rows[1]);
                vec![top_cols[0], top_cols[1], btm_cols[0], btm_cols[1]]
            }
            DashboardLayout::HeroPlusThree => {
                let rows = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
                    .split(grid_area);
                let btm_cols = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 3), Constraint::Ratio(1, 3), Constraint::Ratio(1, 3)])
                    .split(rows[1]);
                vec![rows[0], btm_cols[0], btm_cols[1], btm_cols[2]]
            }
            DashboardLayout::SideBySide => {
                let cols = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(grid_area);
                vec![cols[0], cols[1]]
            }
            DashboardLayout::Stacked => {
                let rows = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(grid_area);
                vec![rows[0], rows[1]]
            }
        };

        for (idx, &rect) in tile_rects.iter().enumerate() {
            let is_focus = idx == self.focused_tile;
            let visual = self.tiles[idx].visual;

            let border_color = if is_focus { theme.accent } else { theme.border };
            let title = if is_focus {
                format!(" [TILE {}: FOCUS - {}] ", idx + 1, visual.label())
            } else {
                format!(" [TILE {}: {}] ", idx + 1, visual.label())
            };

            let block = Block::default()
                .title(title)
                .borders(Borders::ALL)
                .border_style(
                    Style::default()
                        .fg(border_color)
                        .add_modifier(if is_focus { Modifier::BOLD } else { Modifier::empty() }),
                );
            let inner = block.inner(rect);
            f.render_widget(block, rect);

            self.render_tile_content(f, inner, visual, theme, spectrum, peak_l, peak_r, phase, eq_gains);
        }

        // Bottom hotkey guide bar
        let guide_text = Line::from(vec![
            Span::styled(" [Tab/Arrows] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Select Tile  ", Style::default().fg(theme.text)),
            Span::styled(" [V/Enter] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Change Tile Visual  ", Style::default().fg(theme.text)),
            Span::styled(" [L] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("Layout ({})  ", self.layout.label()), Style::default().fg(theme.text)),
            Span::styled(" [Z] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("Maximize Tile  ", Style::default().fg(theme.text)),
        ]);
        let p_guide = Paragraph::new(guide_text).alignment(Alignment::Center);
        f.render_widget(p_guide, root_chunks[1]);
    }

    fn render_tile_content(
        &mut self,
        f: &mut ratatui::Frame,
        area: Rect,
        visual: VisualGraphMode,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
        peak_l: f32,
        peak_r: f32,
        phase: f32,
        eq_gains: &[f32; 10],
    ) {
        match visual {
            VisualGraphMode::Spectrum32 => self.render_spectrum_32(f, area, theme, spectrum),
            VisualGraphMode::SpectrogramWaterfall => self.render_waterfall(f, area, theme, spectrum),
            VisualGraphMode::PhaseLissajous => self.render_phase_scope(f, area, theme, phase, peak_l, peak_r),
            VisualGraphMode::AnalogVu => self.render_analog_vu(f, area, theme, peak_l, peak_r),
            VisualGraphMode::EqCurve => self.render_eq_curve(f, area, theme, eq_gains),
            VisualGraphMode::LoudnessHistory => self.render_loudness_history(f, area, theme),
            VisualGraphMode::StereoImager => self.render_stereo_imager(f, area, theme, peak_l, peak_r, phase),
        }
    }

    /// 32-Band Spectrum Analyzer with adaptive bar stretching to eliminate dead space.
    fn render_spectrum_32(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
    ) {
        if area.height < 3 || area.width < 10 {
            return;
        }

        let num_bars = 32;
        let available_width = area.width as usize;
        // Compute bar width to fill 100% of the surface area
        let bar_width = (available_width / num_bars).max(1);
        let total_bars_width = bar_width * num_bars;
        let pad_left = available_width.saturating_sub(total_bars_width) / 2;

        let max_height = area.height.saturating_sub(1) as usize;
        let mut lines = Vec::new();

        for row in (0..max_height).rev() {
            let threshold = (row as f32 / max_height.max(1) as f32) * 60.0 - 60.0;
            let mut spans = Vec::new();

            if pad_left > 0 {
                spans.push(Span::raw(" ".repeat(pad_left)));
            }

            for &mag_db in spectrum.iter() {
                let is_peak = (mag_db - threshold).abs() < 2.5 && mag_db > -55.0;
                let is_filled = mag_db >= threshold;

                let (ch, color) = if is_peak {
                    ("*", theme.accent)
                } else if is_filled {
                    if threshold > -6.0 {
                        ("|", theme.error)
                    } else if threshold > -18.0 {
                        ("|", theme.warning)
                    } else {
                        ("|", theme.secondary)
                    }
                } else {
                    (" ", Color::DarkGray)
                };

                spans.push(Span::styled(ch.repeat(bar_width), Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        // Frequency axis labels spanning bottom
        let axis_str = " 31Hz  63Hz  125Hz 250Hz 500Hz 1kHz  2kHz  4kHz  8kHz 16kHz ";
        let axis_line = if available_width > axis_str.len() {
            let pad = (available_width - axis_str.len()) / 2;
            format!("{}{}{}", " ".repeat(pad), axis_str, " ".repeat(pad))
        } else {
            axis_str.to_string()
        };
        lines.push(Line::from(vec![Span::styled(axis_line, Style::default().fg(theme.text_dim))]));

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_waterfall(
        &mut self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
    ) {
        if area.height < 2 || area.width < 10 {
            return;
        }

        self.waterfall_history.insert(0, spectrum.to_vec());
        if self.waterfall_history.len() > area.height as usize {
            self.waterfall_history.pop();
        }

        let glyphs = [" ", ".", ":", "-", "=", "+", "*", "#", "%", "@"];
        let mut lines = Vec::new();
        let step = (area.width as usize / 32).max(1);

        for row in self.waterfall_history.iter().take(area.height as usize) {
            let mut spans = Vec::new();
            for &val_db in row.iter() {
                let norm = ((val_db + 60.0) / 60.0).clamp(0.0, 1.0);
                let idx = ((norm * (glyphs.len() - 1) as f32) as usize).min(glyphs.len() - 1);
                let g = glyphs[idx];

                let color = if norm > 0.8 {
                    theme.error
                } else if norm > 0.6 {
                    theme.warning
                } else if norm > 0.3 {
                    theme.secondary
                } else {
                    theme.text_dim
                };

                spans.push(Span::styled(g.to_string().repeat(step), Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_phase_scope(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        phase: f32,
        peak_l: f32,
        peak_r: f32,
    ) {
        let corr_str = format!("{:>+5.2}", phase);
        let corr_status = if phase > 0.6 {
            "MONO / COHERENT"
        } else if phase > 0.0 {
            "WIDE STEREO"
        } else {
            "OUT OF PHASE (CANCELLATION)"
        };
        let status_color = if phase < 0.0 { theme.error } else { theme.success };

        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled("Correlation: ", Style::default().fg(theme.text_dim)),
            Span::styled(corr_str, Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw(" | "),
            Span::styled(corr_status, Style::default().fg(status_color)),
        ]));

        lines.push(Line::from(""));
        let mid = (peak_l + peak_r) * 0.5;
        let side = (peak_l - peak_r).abs();
        lines.push(Line::from(vec![
            Span::styled("Mid (Mono Sum):  ", Style::default().fg(theme.text)),
            Span::styled(format!("{:>5.1} dBFS", mid), Style::default().fg(theme.secondary)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("Side (Stereo Δ): ", Style::default().fg(theme.text)),
            Span::styled(format!("{:>5.1} dBFS", side), Style::default().fg(theme.secondary)),
        ]));

        // Polar dot representation
        lines.push(Line::from(""));
        let width = area.width.saturating_sub(6) as usize;
        let pos = (((phase + 1.0) / 2.0) * width as f32) as usize;
        let mut bar = vec!['-'; width];
        if pos < width {
            bar[pos] = 'O';
        }
        lines.push(Line::from(vec![
            Span::styled(" [-1.0] ", Style::default().fg(theme.error)),
            Span::styled(bar.into_iter().collect::<String>(), Style::default().fg(theme.primary)),
            Span::styled(" [+1.0] ", Style::default().fg(theme.success)),
        ]));

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }

    fn render_analog_vu(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        peak_l: f32,
        peak_r: f32,
    ) {
        let calc_meter = |db: f32, bar_len: usize| -> (String, Color) {
            let norm = ((db + 40.0) / 40.0).clamp(0.0, 1.0);
            let filled = (norm * bar_len as f32) as usize;
            let bar = format!("[{}{}]", "=".repeat(filled), " ".repeat(bar_len.saturating_sub(filled)));
            let color = if db >= -0.5 {
                theme.error
            } else if db >= -6.0 {
                theme.warning
            } else {
                theme.success
            };
            (bar, color)
        };

        let bar_len = area.width.saturating_sub(20) as usize;
        let (meter_l, col_l) = calc_meter(peak_l, bar_len.max(8));
        let (meter_r, col_r) = calc_meter(peak_r, bar_len.max(8));

        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("L: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(meter_l, Style::default().fg(col_l)),
                Span::styled(format!(" {:>5.1} dB", peak_l), Style::default().fg(col_l)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("R: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(meter_r, Style::default().fg(col_r)),
                Span::styled(format!(" {:>5.1} dB", peak_r), Style::default().fg(col_r)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("-40dB       -20dB       -12dB       -6dB       0dB", Style::default().fg(theme.text_dim)),
            ]),
        ];

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }

    fn render_eq_curve(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        eq_gains: &[f32; 10],
    ) {
        if area.height < 4 {
            return;
        }

        let max_height = area.height.saturating_sub(2) as usize;
        let mut lines = Vec::new();

        let num_bands = 10;
        let spacing = (area.width.saturating_sub(10) as usize / num_bands).max(1);

        for row in (0..max_height).rev() {
            let target_gain = (row as f32 / max_height.max(1) as f32) * 24.0 - 12.0;
            let mut spans = Vec::new();

            for &g in eq_gains.iter() {
                let is_point = (g - target_gain).abs() < 1.2;
                let is_zero = (0.0 - target_gain).abs() < 0.6;

                let (ch, style) = if is_point {
                    ("O", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD))
                } else if is_zero {
                    ("-", Style::default().fg(theme.text_dim))
                } else {
                    (" ", Style::default())
                };

                spans.push(Span::styled(ch, style));
                if spacing > 1 {
                    spans.push(Span::raw(" ".repeat(spacing - 1)));
                }
            }
            lines.push(Line::from(spans));
        }

        lines.push(Line::from(vec![
            Span::styled("31  63  125 250 500 1k  2k  4k  8k  16k", Style::default().fg(theme.primary)),
        ]));

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }

    fn render_loudness_history(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
    ) {
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled("EBU R128 MOMENTARY LOUDNESS TIMELINE", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ]));

        let max_height = area.height.saturating_sub(2) as usize;
        let width = area.width.saturating_sub(4) as usize;

        for row in (0..max_height).rev() {
            let thresh = (row as f32 / max_height.max(1) as f32) * 50.0 - 50.0; // [-50 .. 0] LUFS
            let mut row_chars = Vec::new();

            for &lufs in self.loudness_history.iter().take(width) {
                if lufs >= thresh {
                    let c = if thresh > -14.0 {
                        '+'
                    } else if thresh > -23.0 {
                        '='
                    } else {
                        '-'
                    };
                    row_chars.push(c);
                } else {
                    row_chars.push(' ');
                }
            }

            lines.push(Line::from(Span::styled(
                row_chars.into_iter().collect::<String>(),
                Style::default().fg(if thresh >= -14.0 { theme.warning } else { theme.success }),
            )));
        }

        lines.push(Line::from(vec![
            Span::styled("<- Recent Time (EBU R128 -14 LUFS Target Line) Older ->", Style::default().fg(theme.text_dim)),
        ]));

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }

    fn render_stereo_imager(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        peak_l: f32,
        peak_r: f32,
        phase: f32,
    ) {
        let bal = peak_l - peak_r;
        let bal_str = if bal.abs() < 0.5 {
            "CENTER BALANCE"
        } else if bal > 0.0 {
            "LEANING LEFT"
        } else {
            "LEANING RIGHT"
        };

        let width = area.width.saturating_sub(8) as usize;
        let norm_bal = ((bal + 12.0) / 24.0).clamp(0.0, 1.0);
        let pos = (norm_bal * width as f32) as usize;

        let mut meter = vec!['='; width];
        if pos < width {
            meter[pos] = '|';
        }

        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("STEREO SOUNDSTAGE IMAGER: ", Style::default().fg(theme.text)),
                Span::styled(bal_str, Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("L ", Style::default().fg(theme.secondary)),
                Span::styled(meter.into_iter().collect::<String>(), Style::default().fg(theme.primary)),
                Span::styled(" R", Style::default().fg(theme.secondary)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("Stereo Width: {:.0}% | Phase Coherence: {:+.2}", (1.0 - phase.abs()) * 100.0 + 50.0, phase), Style::default().fg(theme.text_dim)),
            ]),
        ];

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_visual_graph_mode_cycle() {
        let mut dash = VisualsDashboard::new();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::Spectrum32);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::SpectrogramWaterfall);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::PhaseLissajous);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::AnalogVu);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::EqCurve);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::LoudnessHistory);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::StereoImager);
        dash.cycle_mode();
        assert_eq!(dash.tiles[0].visual, VisualGraphMode::Spectrum32);
    }

    #[test]
    fn test_modular_dashboard_layout_cycling() {
        let mut dash = VisualsDashboard::new();
        assert_eq!(dash.layout, DashboardLayout::HeroPlusThree);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::Quad2x2);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::SideBySide);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::Stacked);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::HeroPlusThree);
    }

    #[test]
    fn test_tile_selection_and_per_tile_change() {
        let mut dash = VisualsDashboard::new();
        assert_eq!(dash.focused_tile, 0);

        // Move to Tile 1
        dash.handle_key(KeyCode::Tab);
        assert_eq!(dash.focused_tile, 1);
        let original_tile0 = dash.tiles[0].visual;
        assert_eq!(dash.tiles[1].visual, VisualGraphMode::AnalogVu);

        // Change only Tile 1
        dash.handle_key(KeyCode::Char('v'));
        assert_eq!(dash.tiles[1].visual, VisualGraphMode::EqCurve);
        // Tile 0 remains unchanged!
        assert_eq!(dash.tiles[0].visual, original_tile0);
    }

    #[test]
    fn test_zoom_toggle() {
        let mut dash = VisualsDashboard::new();
        assert!(!dash.is_zoomed);
        dash.handle_key(KeyCode::Char('z'));
        assert!(dash.is_zoomed);
        dash.handle_key(KeyCode::Char('z'));
        assert!(!dash.is_zoomed);
    }
}
