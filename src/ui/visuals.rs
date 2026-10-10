//! Real-Time Visual Graph Dashboard for OmniRip TUI.
//! Provides multiple high-speed visual graph engines: 32-Band FFT Spectrum Analyzer,
//! 2D STFT Spectrogram Waterfall, Stereo Lissajous Phase Scope, Dual Analog VU Meters,
//! and Cascaded Biquad EQ Frequency Curve Plot.

use crate::ui::theme::ThemePalette;
use ratatui::layout::{Alignment, Rect};
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
}

impl VisualGraphMode {
    pub fn label(&self) -> &'static str {
        match self {
            VisualGraphMode::Spectrum32 => "32-Band FFT Spectrum Analyzer",
            VisualGraphMode::SpectrogramWaterfall => "2D STFT Spectrogram Waterfall",
            VisualGraphMode::PhaseLissajous => "Stereo Lissajous Phase Scope",
            VisualGraphMode::AnalogVu => "Dual Analog Stereo VU Meters",
            VisualGraphMode::EqCurve => "Cascaded Biquad EQ Curve Plot",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            VisualGraphMode::Spectrum32 => VisualGraphMode::SpectrogramWaterfall,
            VisualGraphMode::SpectrogramWaterfall => VisualGraphMode::PhaseLissajous,
            VisualGraphMode::PhaseLissajous => VisualGraphMode::AnalogVu,
            VisualGraphMode::AnalogVu => VisualGraphMode::EqCurve,
            VisualGraphMode::EqCurve => VisualGraphMode::Spectrum32,
        }
    }
}

pub struct VisualsDashboard {
    pub mode: VisualGraphMode,
    waterfall_history: Vec<Vec<f32>>,
}

impl VisualsDashboard {
    pub fn new() -> Self {
        Self {
            mode: VisualGraphMode::Spectrum32,
            waterfall_history: Vec::new(),
        }
    }

    pub fn cycle_mode(&mut self) {
        self.mode = self.mode.next();
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
        let block = Block::default()
            .title(format!(" REAL-TIME VISUAL GRAPH: {} (Press V to Cycle) ", self.mode.label()))
            .title_alignment(Alignment::Center)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        match self.mode {
            VisualGraphMode::Spectrum32 => self.render_spectrum_32(f, inner, theme, spectrum),
            VisualGraphMode::SpectrogramWaterfall => self.render_waterfall(f, inner, theme, spectrum),
            VisualGraphMode::PhaseLissajous => self.render_phase_scope(f, inner, theme, phase, peak_l, peak_r),
            VisualGraphMode::AnalogVu => self.render_analog_vu(f, inner, theme, peak_l, peak_r),
            VisualGraphMode::EqCurve => self.render_eq_curve(f, inner, theme, eq_gains),
        }
    }

    fn render_spectrum_32(
        &self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
    ) {
        if area.height < 4 || area.width < 32 {
            return;
        }

        let max_height = area.height.saturating_sub(2) as usize;
        let mut lines = Vec::new();

        // Build vertical bars for each dB level
        for row in (0..max_height).rev() {
            let threshold = (row as f32 / max_height as f32) * 60.0 - 60.0; // [-60dB .. 0dB]
            let mut spans = Vec::new();

            for (i, &mag_db) in spectrum.iter().enumerate() {
                let is_peak = (mag_db - threshold).abs() < 2.0 && mag_db > -55.0;
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

                spans.push(Span::styled(ch, Style::default().fg(color)));
                if i % 2 == 1 {
                    spans.push(Span::raw(" "));
                }
            }
            lines.push(Line::from(spans));
        }

        // Frequency axis labels
        lines.push(Line::from(vec![
            Span::styled("31Hz   63Hz   125Hz  250Hz  500Hz  1kHz   2kHz   4kHz   8kHz   16kHz", Style::default().fg(theme.text_dim)),
        ]));

        let p = Paragraph::new(lines).alignment(Alignment::Center);
        f.render_widget(p, area);
    }

    fn render_waterfall(
        &mut self,
        f: &mut ratatui::Frame,
        area: Rect,
        theme: &ThemePalette,
        spectrum: &[f32; 32],
    ) {
        // Record rolling history
        self.waterfall_history.insert(0, spectrum.to_vec());
        if self.waterfall_history.len() > area.height as usize {
            self.waterfall_history.pop();
        }

        let glyphs = [" ", ".", ":", "-", "=", "+", "*", "#", "%", "@"];
        let mut lines = Vec::new();

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

                spans.push(Span::styled(format!("{} ", g), Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines).alignment(Alignment::Center);
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
        let width_pct = ((1.0 - phase) * 50.0).clamp(0.0, 100.0);
        let phase_status = if phase >= 0.7 {
            ("[MONO-COMPATIBLE / COHERENT]", theme.success)
        } else if phase >= 0.2 {
            ("[WIDE STEREO SOUNDSTAGE]", theme.secondary)
        } else if phase >= 0.0 {
            ("[ULTRA-WIDE STEREO]", theme.warning)
        } else {
            ("[OUT-OF-PHASE / MONO CANCELLATION WARNING]", theme.error)
        };

        let mut lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("STEREO POLAR GONIOMETER & LISSAJOUS PHASE CORRELATION", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(format!("Phase Correlation: {:+.2} ", phase), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(phase_status.0, Style::default().fg(phase_status.1).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(format!("Estimated Soundstage Width: {:.1}%", width_pct), Style::default().fg(theme.text_dim)),
            ]),
            Line::from(""),
        ];

        // Draw correlation meter bar: [-1.0 ... 0.0 ... +1.0]
        let bar_width = 40;
        let pos = (((phase + 1.0) / 2.0) * bar_width as f32) as usize;
        let mut bar = vec!["-"; bar_width];
        bar[bar_width / 2] = "|";
        if pos < bar_width {
            bar[pos] = "O";
        }

        lines.push(Line::from(vec![
            Span::styled(" [-1.0 Phase] ", Style::default().fg(theme.error)),
            Span::styled(format!("[{}]", bar.join("")), Style::default().fg(theme.secondary)),
            Span::styled(" [+1.0 Mono] ", Style::default().fg(theme.success)),
        ]));

        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled(format!("Left Channel Peak: {:>5.1} dBFS  |  Right Channel Peak: {:>5.1} dBFS", peak_l, peak_r), Style::default().fg(theme.text_dim)),
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
        let calc_meter = |db: f32| -> (String, Color) {
            let width: usize = 36;
            let norm = ((db + 40.0) / 40.0).clamp(0.0, 1.0);
            let filled = (norm * width as f32) as usize;
            let bar = format!("[{}{}]", "=".repeat(filled), " ".repeat(width.saturating_sub(filled)));
            let color = if db >= -0.5 {
                theme.error
            } else if db >= -6.0 {
                theme.warning
            } else {
                theme.success
            };
            (bar, color)
        };

        let (meter_l, col_l) = calc_meter(peak_l);
        let (meter_r, col_r) = calc_meter(peak_r);

        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("DUAL CHANNEL ANALOG PEAK VU METERS", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("LEFT  ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(meter_l, Style::default().fg(col_l)),
                Span::styled(format!(" {:>5.1} dBFS", peak_l), Style::default().fg(col_l)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("RIGHT ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(meter_r, Style::default().fg(col_r)),
                Span::styled(format!(" {:>5.1} dBFS", peak_r), Style::default().fg(col_r)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" -40dB    -30dB    -20dB    -12dB    -6dB    -3dB    0dB PEAK", Style::default().fg(theme.text_dim)),
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
        if area.height < 5 {
            return;
        }

        let max_height = area.height.saturating_sub(2) as usize;
        let mut lines = Vec::new();

        // 10 bands interpolated across columns
        for row in (0..max_height).rev() {
            let target_gain = (row as f32 / max_height as f32) * 24.0 - 12.0; // [-12dB .. +12dB]
            let mut spans = Vec::new();

            for &g in eq_gains.iter() {
                let is_point = (g - target_gain).abs() < 1.0;
                let is_zero = (0.0 - target_gain).abs() < 0.8;

                let (ch, style) = if is_point {
                    ("o", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD))
                } else if is_zero {
                    ("-", Style::default().fg(theme.text_dim))
                } else {
                    (" ", Style::default())
                };

                spans.push(Span::styled(ch, style));
                spans.push(Span::raw("    "));
            }
            lines.push(Line::from(spans));
        }

        lines.push(Line::from(vec![
            Span::styled("31Hz   63Hz   125Hz  250Hz  500Hz  1kHz   2kHz   4kHz   8kHz   16kHz", Style::default().fg(theme.primary)),
        ]));

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
        assert_eq!(dash.mode, VisualGraphMode::Spectrum32);
        dash.cycle_mode();
        assert_eq!(dash.mode, VisualGraphMode::SpectrogramWaterfall);
        dash.cycle_mode();
        assert_eq!(dash.mode, VisualGraphMode::PhaseLissajous);
        dash.cycle_mode();
        assert_eq!(dash.mode, VisualGraphMode::AnalogVu);
        dash.cycle_mode();
        assert_eq!(dash.mode, VisualGraphMode::EqCurve);
        dash.cycle_mode();
        assert_eq!(dash.mode, VisualGraphMode::Spectrum32);
    }
}
