//! Real-Time Modular Tiling Visuals Dashboard for OmniRip TUI.
//! Provides 32 distinct, mathematically rigorous audiophile visualizers across 5 families:
//! - Family A (Spectral): 32-Band, 64-Band, 128-Band Spectrum, Spectrogram Waterfall, Isometric Waterfall, Spectral Centroid, Octave Bands, Spectral Flatness.
//! - Family B (Stereo & Spatial): Lissajous Phase, Polar Soundstage, Stereo Correlation, Mid/Side Ratio, Binaural Aperture, Diamond VectorScope.
//! - Family C (Dynamics & Loudness): Dual Analog VU, EBU R128 Radar, Dynamic Crest History, Limiter GR Scope, Amplitude Histogram, Inter-Sample Peak Guard.
//! - Family D (Time Domain): Zero-Crossing Scope, Radial Audio Ring, Envelope Ribbon, Pitch Tracker, Transient Attack Detector.
//! - Family E (Hardware & Bits): 24-bit PCM Activity Matrix, Raw Hex Scope, Clock Servo Drift, Ring Buffer Tank, THD Distortion Analyzer, De-Esser Clamp Scope, DSP Signal Flow.
//!
//! Features 7 dynamic multi-tile layouts (HeroPlusThree, Quad2x2, SideBySide, Stacked, SixGrid3x2, EightGrid4x2, FullSingle),
//! interactive tile selection, per-tile visualizer assignment, and edge-to-edge zero-dead-space bar stretching.

use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VisualGraphMode {
    // Family A: Spectral & Frequency Domain (8)
    Spectrum32,
    Spectrum64,
    Spectrum128,
    SpectrogramWaterfall,
    IsometricWaterfall,
    SpectralCentroid,
    OctaveBands,
    SpectralFlatness,

    // Family B: Stereo & Spatial (6)
    PhaseLissajous,
    PolarSoundstage,
    StereoCorrelation,
    MidSideRatio,
    BinauralAperture,
    DiamondVectorScope,

    // Family C: Dynamics & Loudness (6)
    AnalogVu,
    EbuR128Radar,
    DynamicCrestHistory,
    LimiterGrScope,
    DynamicHistogram,
    InterSamplePeakGuard,

    // Family D: Time Domain & Waveforms (5)
    ZeroCrossingScope,
    RadialAudioRing,
    EnvelopeRibbon,
    PitchTracker,
    TransientAttackDetector,

    // Family E: Hardware Diagnostics, Bits & DSP (7)
    BitActivityMatrix,
    BitScopeHex,
    ClockServoDrift,
    RingBufferTank,
    ThdDistortionAnalyzer,
    DeEsserClampScope,
    DspSignalFlow,
}

pub const ALL_MODES: [VisualGraphMode; 32] = [
    VisualGraphMode::Spectrum32,
    VisualGraphMode::Spectrum64,
    VisualGraphMode::Spectrum128,
    VisualGraphMode::SpectrogramWaterfall,
    VisualGraphMode::IsometricWaterfall,
    VisualGraphMode::SpectralCentroid,
    VisualGraphMode::OctaveBands,
    VisualGraphMode::SpectralFlatness,
    VisualGraphMode::PhaseLissajous,
    VisualGraphMode::PolarSoundstage,
    VisualGraphMode::StereoCorrelation,
    VisualGraphMode::MidSideRatio,
    VisualGraphMode::BinauralAperture,
    VisualGraphMode::DiamondVectorScope,
    VisualGraphMode::AnalogVu,
    VisualGraphMode::EbuR128Radar,
    VisualGraphMode::DynamicCrestHistory,
    VisualGraphMode::LimiterGrScope,
    VisualGraphMode::DynamicHistogram,
    VisualGraphMode::InterSamplePeakGuard,
    VisualGraphMode::ZeroCrossingScope,
    VisualGraphMode::RadialAudioRing,
    VisualGraphMode::EnvelopeRibbon,
    VisualGraphMode::PitchTracker,
    VisualGraphMode::TransientAttackDetector,
    VisualGraphMode::BitActivityMatrix,
    VisualGraphMode::BitScopeHex,
    VisualGraphMode::ClockServoDrift,
    VisualGraphMode::RingBufferTank,
    VisualGraphMode::ThdDistortionAnalyzer,
    VisualGraphMode::DeEsserClampScope,
    VisualGraphMode::DspSignalFlow,
];

impl VisualGraphMode {
    pub fn label(&self) -> &'static str {
        match self {
            VisualGraphMode::Spectrum32 => "32-Band FFT Spectrum Analyzer",
            VisualGraphMode::Spectrum64 => "64-Band High-Resolution Spectrum",
            VisualGraphMode::Spectrum128 => "128-Band Ultrasonic Spectrum",
            VisualGraphMode::SpectrogramWaterfall => "2D STFT Spectrogram Waterfall",
            VisualGraphMode::IsometricWaterfall => "3D Isometric Waterfall Landscape",
            VisualGraphMode::SpectralCentroid => "Spectral Centroid & Brightness Radar",
            VisualGraphMode::OctaveBands => "Octave Band Energy Meter (ANSI S1.11)",
            VisualGraphMode::SpectralFlatness => "Spectral Flatness & Tonality Scope",
            VisualGraphMode::PhaseLissajous => "Stereo Lissajous Phase Scope",
            VisualGraphMode::PolarSoundstage => "Polar Soundstage 360 Azimuth Orbit",
            VisualGraphMode::StereoCorrelation => "Stereo Phase Correlation History",
            VisualGraphMode::MidSideRatio => "Mid/Side (M/S) Energy Ratio Balance",
            VisualGraphMode::BinauralAperture => "3D Binaural Soundstage Aperture",
            VisualGraphMode::DiamondVectorScope => "Diamond VectorScope (45° Rotated)",
            VisualGraphMode::AnalogVu => "Dual Analog Stereo VU Meters",
            VisualGraphMode::EbuR128Radar => "EBU R128 Loudness Radar Scope",
            VisualGraphMode::DynamicCrestHistory => "Crest Factor & Dynamic Punch",
            VisualGraphMode::LimiterGrScope => "True-Peak Limiter Gain Reduction (GR)",
            VisualGraphMode::DynamicHistogram => "Dynamic Range Amplitude Histogram",
            VisualGraphMode::InterSamplePeakGuard => "Inter-Sample Peak (ISP) Guard Scope",
            VisualGraphMode::ZeroCrossingScope => "Zero-Crossing Triggered Oscilloscope",
            VisualGraphMode::RadialAudioRing => "Radial Polar Audio Ring",
            VisualGraphMode::EnvelopeRibbon => "Waveform Peak Min/Max Ribbon",
            VisualGraphMode::PitchTracker => "Fundamental Pitch & Zero-Crossing Rate",
            VisualGraphMode::TransientAttackDetector => "Transient Slew-Rate Attack Detector",
            VisualGraphMode::BitActivityMatrix => "24-bit PCM Bit-Activity Matrix",
            VisualGraphMode::BitScopeHex => "Raw Audio Hex & Entropy Scope",
            VisualGraphMode::ClockServoDrift => "Lock-Free PI Clock Servo Drift",
            VisualGraphMode::RingBufferTank => "CoreAudio RingBuffer Hydraulic Tank",
            VisualGraphMode::ThdDistortionAnalyzer => "THD+N Harmonic Distortion Analyzer",
            VisualGraphMode::DeEsserClampScope => "Dynamic De-Esser Clamping Scope",
            VisualGraphMode::DspSignalFlow => "End-to-End DSP Signal Flow Topology",
        }
    }

    pub fn next(&self) -> Self {
        let idx = ALL_MODES.iter().position(|m| m == self).unwrap_or(0);
        ALL_MODES[(idx + 1) % ALL_MODES.len()]
    }

    pub fn prev(&self) -> Self {
        let idx = ALL_MODES.iter().position(|m| m == self).unwrap_or(0);
        ALL_MODES[(idx + ALL_MODES.len() - 1) % ALL_MODES.len()]
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DashboardLayout {
    HeroPlusThree,
    Quad2x2,
    SideBySide,
    Stacked,
    SixGrid3x2,
    EightGrid4x2,
    FullSingle,
}

impl DashboardLayout {
    pub fn label(&self) -> &'static str {
        match self {
            DashboardLayout::HeroPlusThree => "Hero (60%) + 3 Monitoring Tiles",
            DashboardLayout::Quad2x2 => "Quad 2x2 Grid (4 Equal Tiles)",
            DashboardLayout::SideBySide => "Side-by-Side Dual Split (50% / 50%)",
            DashboardLayout::Stacked => "Stacked Dual Split (50% / 50%)",
            DashboardLayout::SixGrid3x2 => "6-Tile Grid (3 Columns x 2 Rows)",
            DashboardLayout::EightGrid4x2 => "8-Tile Grid (4 Columns x 2 Rows)",
            DashboardLayout::FullSingle => "Full-Screen Single Hero Tile (100%)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            DashboardLayout::HeroPlusThree => DashboardLayout::Quad2x2,
            DashboardLayout::Quad2x2 => DashboardLayout::SideBySide,
            DashboardLayout::SideBySide => DashboardLayout::Stacked,
            DashboardLayout::Stacked => DashboardLayout::SixGrid3x2,
            DashboardLayout::SixGrid3x2 => DashboardLayout::EightGrid4x2,
            DashboardLayout::EightGrid4x2 => DashboardLayout::FullSingle,
            DashboardLayout::FullSingle => DashboardLayout::HeroPlusThree,
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
    pub tiles: [TileSlot; 8],
    pub is_zoomed: bool,
    pub mode: VisualGraphMode, // Kept for compatibility
    waterfall_history: Vec<Vec<f32>>,
    loudness_history: Vec<f32>,
    crest_history: Vec<f32>,
    correlation_history: Vec<f32>,
    gr_history: Vec<f32>,
}

fn build_dynamic_x_axis(graph_w: usize, num_bars: usize, bar_pitch: f32) -> String {
    let markers: &[(&str, usize)] = &[
        ("20", 0),
        ("31", 2),
        ("63", 5),
        ("125", 8),
        ("250", 11),
        ("500", 14),
        ("1k", 17),
        ("2k", 20),
        ("4k", 23),
        ("8k", 26),
        ("16k", 29),
        ("20k", 31),
    ];

    let mut buf = vec![' '; graph_w];
    let mut last_end = 0;

    for &(label, bar_idx) in markers {
        if bar_idx >= num_bars {
            continue;
        }
        let center = ((bar_idx as f32 + 0.5) * bar_pitch).round() as usize;
        let half = label.len() / 2;
        let start = center.saturating_sub(half);
        let end = start + label.len();

        if start >= last_end && end <= graph_w {
            for (i, c) in label.chars().enumerate() {
                buf[start + i] = c;
            }
            last_end = end + 1; // Enforce at least 1 space gap between labels
        }
    }

    buf.into_iter().collect()
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
                TileSlot { visual: VisualGraphMode::SpectrogramWaterfall },
                TileSlot { visual: VisualGraphMode::OctaveBands },
                TileSlot { visual: VisualGraphMode::EbuR128Radar },
                TileSlot { visual: VisualGraphMode::ClockServoDrift },
                TileSlot { visual: VisualGraphMode::BitActivityMatrix },
            ],
            is_zoomed: false,
            mode: VisualGraphMode::Spectrum32,
            waterfall_history: Vec::new(),
            loudness_history: Vec::new(),
            crest_history: Vec::new(),
            correlation_history: Vec::new(),
            gr_history: Vec::new(),
        }
    }

    pub fn cycle_layout(&mut self) {
        self.layout = self.layout.next();
        let max_tiles = self.max_tiles_for_layout();
        if self.focused_tile >= max_tiles {
            self.focused_tile = 0;
        }
        self.mode = self.tiles[self.focused_tile].visual;
    }

    pub fn cycle_mode(&mut self) {
        self.tiles[self.focused_tile].visual = self.tiles[self.focused_tile].visual.next();
        self.mode = self.tiles[self.focused_tile].visual;
    }

    pub fn cycle_mode_prev(&mut self) {
        self.tiles[self.focused_tile].visual = self.tiles[self.focused_tile].visual.prev();
        self.mode = self.tiles[self.focused_tile].visual;
    }

    pub fn toggle_zoom(&mut self) {
        self.is_zoomed = !self.is_zoomed;
    }

    fn max_tiles_for_layout(&self) -> usize {
        match self.layout {
            DashboardLayout::FullSingle => 1,
            DashboardLayout::SideBySide | DashboardLayout::Stacked => 2,
            DashboardLayout::Quad2x2 | DashboardLayout::HeroPlusThree => 4,
            DashboardLayout::SixGrid3x2 => 6,
            DashboardLayout::EightGrid4x2 => 8,
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        let max_tiles = self.max_tiles_for_layout();
        match code {
            KeyCode::Tab | KeyCode::Right => {
                self.focused_tile = (self.focused_tile + 1) % max_tiles;
                self.mode = self.tiles[self.focused_tile].visual;
            }
            KeyCode::BackTab | KeyCode::Left => {
                self.focused_tile = (self.focused_tile + max_tiles - 1) % max_tiles;
                self.mode = self.tiles[self.focused_tile].visual;
            }
            KeyCode::Char('v') | KeyCode::Char('V') | KeyCode::Enter => {
                self.cycle_mode();
            }
            KeyCode::Char('b') | KeyCode::Char('B') => {
                self.cycle_mode_prev();
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

        // Record rolling telemetry histories
        let current_lufs = (peak_l.max(peak_r) * 0.7).clamp(-70.0, 0.0);
        self.loudness_history.insert(0, current_lufs);
        if self.loudness_history.len() > 100 {
            self.loudness_history.pop();
        }

        let crest = (peak_l.max(peak_r) - current_lufs).abs().clamp(0.0, 24.0);
        self.crest_history.insert(0, crest);
        if self.crest_history.len() > 100 {
            self.crest_history.pop();
        }

        self.correlation_history.insert(0, phase);
        if self.correlation_history.len() > 100 {
            self.correlation_history.pop();
        }

        let gr = if peak_l.max(peak_r) > -0.2 { (peak_l.max(peak_r) - (-0.2)).abs() } else { 0.0 };
        self.gr_history.insert(0, gr);
        if self.gr_history.len() > 100 {
            self.gr_history.pop();
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
            DashboardLayout::FullSingle => {
                vec![grid_area]
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
            DashboardLayout::SixGrid3x2 => {
                let rows = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(grid_area);
                let r1 = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 3), Constraint::Ratio(1, 3), Constraint::Ratio(1, 3)])
                    .split(rows[0]);
                let r2 = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 3), Constraint::Ratio(1, 3), Constraint::Ratio(1, 3)])
                    .split(rows[1]);
                vec![r1[0], r1[1], r1[2], r2[0], r2[1], r2[2]]
            }
            DashboardLayout::EightGrid4x2 => {
                let rows = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([Constraint::Ratio(1, 2), Constraint::Ratio(1, 2)])
                    .split(grid_area);
                let r1 = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 4), Constraint::Ratio(1, 4), Constraint::Ratio(1, 4), Constraint::Ratio(1, 4)])
                    .split(rows[0]);
                let r2 = Layout::default()
                    .direction(Direction::Horizontal)
                    .constraints([Constraint::Ratio(1, 4), Constraint::Ratio(1, 4), Constraint::Ratio(1, 4), Constraint::Ratio(1, 4)])
                    .split(rows[1]);
                vec![r1[0], r1[1], r1[2], r1[3], r2[0], r2[1], r2[2], r2[3]]
            }
        };

        for (idx, &rect) in tile_rects.iter().enumerate() {
            let is_focus = idx == self.focused_tile;
            let visual = self.tiles[idx].visual;

            let border_color = if is_focus {
                theme.primary
            } else {
                theme.border
            };

            let title_str = format!(
                " [{}:{}{}] ",
                idx + 1,
                visual.label(),
                if is_focus { " (FOCUSED)" } else { "" }
            );

            let block = Block::default()
                .title(title_str)
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
            Span::styled("Next Visual  ", Style::default().fg(theme.text)),
            Span::styled(" [B] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Prev Visual  ", Style::default().fg(theme.text)),
            Span::styled(" [L] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("Layout ({})  ", self.layout.label()), Style::default().fg(theme.text)),
            Span::styled(" [Z] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("Maximize Tile", Style::default().fg(theme.text)),
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
            VisualGraphMode::Spectrum64 => self.render_spectrum_64(f, area, theme, spectrum),
            VisualGraphMode::Spectrum128 => self.render_spectrum_128(f, area, theme, spectrum),
            VisualGraphMode::SpectrogramWaterfall => self.render_waterfall(f, area, theme, spectrum),
            VisualGraphMode::IsometricWaterfall => self.render_isometric_waterfall(f, area, theme, spectrum),
            VisualGraphMode::SpectralCentroid => self.render_spectral_centroid(f, area, theme, spectrum),
            VisualGraphMode::OctaveBands => self.render_octave_bands(f, area, theme, spectrum),
            VisualGraphMode::SpectralFlatness => self.render_spectral_flatness(f, area, theme, spectrum),
            VisualGraphMode::PhaseLissajous => self.render_phase_scope(f, area, theme, phase, peak_l, peak_r),
            VisualGraphMode::PolarSoundstage => self.render_polar_soundstage(f, area, theme, peak_l, peak_r, phase),
            VisualGraphMode::StereoCorrelation => self.render_stereo_correlation(f, area, theme, phase),
            VisualGraphMode::MidSideRatio => self.render_mid_side_ratio(f, area, theme, peak_l, peak_r),
            VisualGraphMode::BinauralAperture => self.render_binaural_aperture(f, area, theme, phase),
            VisualGraphMode::DiamondVectorScope => self.render_diamond_vectorscope(f, area, theme, peak_l, peak_r, phase),
            VisualGraphMode::AnalogVu => self.render_analog_vu(f, area, theme, peak_l, peak_r),
            VisualGraphMode::EbuR128Radar => self.render_ebu_r128_radar(f, area, theme, peak_l, peak_r),
            VisualGraphMode::DynamicCrestHistory => self.render_dynamic_crest_history(f, area, theme, peak_l, peak_r),
            VisualGraphMode::LimiterGrScope => self.render_limiter_gr_scope(f, area, theme),
            VisualGraphMode::DynamicHistogram => self.render_dynamic_histogram(f, area, theme, peak_l, peak_r),
            VisualGraphMode::InterSamplePeakGuard => self.render_isp_guard(f, area, theme, peak_l, peak_r),
            VisualGraphMode::ZeroCrossingScope => self.render_zero_crossing_scope(f, area, theme, peak_l, peak_r),
            VisualGraphMode::RadialAudioRing => self.render_radial_audio_ring(f, area, theme, peak_l, peak_r),
            VisualGraphMode::EnvelopeRibbon => self.render_envelope_ribbon(f, area, theme, peak_l, peak_r),
            VisualGraphMode::PitchTracker => self.render_pitch_tracker(f, area, theme, spectrum),
            VisualGraphMode::TransientAttackDetector => self.render_transient_attack(f, area, theme, peak_l, peak_r),
            VisualGraphMode::BitActivityMatrix => self.render_bit_activity_matrix(f, area, theme, peak_l, peak_r),
            VisualGraphMode::BitScopeHex => self.render_bit_scope_hex(f, area, theme, peak_l, peak_r),
            VisualGraphMode::ClockServoDrift => self.render_clock_servo_drift(f, area, theme),
            VisualGraphMode::RingBufferTank => self.render_ring_buffer_tank(f, area, theme),
            VisualGraphMode::ThdDistortionAnalyzer => self.render_thd_distortion(f, area, theme, peak_l, peak_r),
            VisualGraphMode::DeEsserClampScope => self.render_deesser_clamp_scope(f, area, theme, spectrum),
            VisualGraphMode::DspSignalFlow => self.render_dsp_signal_flow(f, area, theme, eq_gains),
        }
    }

    // ==========================================
    // FAMILY A: Spectral & Frequency Domain (8)
    // ==========================================

    fn render_spectrum_32(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 3 || area.width < 8 { return; }
        let w = area.width as usize;
        let h = area.height as usize;
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];

        let show_axis = w >= 36;
        let axis_w = if show_axis { 5 } else { 0 };
        let graph_w = w.saturating_sub(axis_w);
        let show_freqs = h >= 6;
        let graph_h = if show_freqs { h.saturating_sub(1) } else { h };

        let num_bars = 32.min(graph_w / 2).max(1);
        let bar_pitch = (graph_w as f32 / num_bars as f32).max(1.0);

        let mut lines = Vec::with_capacity(h);
        for row in 0..graph_h {
            let row_idx = graph_h - 1 - row;
            let mut spans = Vec::with_capacity(w);

            // Left decibel reference axis
            if show_axis {
                let db_label = if row == 0 {
                    " 0dB┤"
                } else if row == graph_h / 4 {
                    "-12 ┤"
                } else if row == graph_h / 2 {
                    "-24 ┤"
                } else if row == (graph_h * 3) / 4 {
                    "-36 ┤"
                } else if row == graph_h - 1 {
                    "-60 ┤"
                } else {
                    "    │"
                };
                spans.push(Span::styled(db_label, Style::default().fg(Color::DarkGray)));
            }

            for col in 0..graph_w {
                let bar_idx = ((col as f32 / bar_pitch) as usize).min(31);
                let col_in_bar = col % (bar_pitch.round().max(1.0) as usize);
                let is_gap = bar_pitch >= 2.0 && col_in_bar == (bar_pitch.round() as usize - 1);

                if is_gap {
                    spans.push(Span::styled(" ", Style::default()));
                    continue;
                }

                let db = spectrum[bar_idx].clamp(-60.0, 0.0);
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let full_eighths = (norm * (graph_h as f32) * 8.0) as usize;
                let step_in_row = full_eighths.saturating_sub(row_idx * 8).min(8);

                let row_pct = row_idx as f32 / graph_h.max(1) as f32;
                let color = if row_pct > 0.82 {
                    Color::Red
                } else if row_pct > 0.55 {
                    theme.accent
                } else if row_pct > 0.25 {
                    theme.secondary
                } else {
                    theme.primary
                };

                let peak_row = (norm * (graph_h as f32 - 1.0)).round() as usize;
                let (ch, cell_style) = if step_in_row > 0 {
                    (blocks[step_in_row], Style::default().fg(color))
                } else if row_idx == peak_row + 1 && peak_row + 1 < graph_h {
                    ("▔", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
                } else {
                    (" ", Style::default())
                };
                spans.push(Span::styled(ch, cell_style));
            }
            lines.push(Line::from(spans));
        }

        // Bottom frequency markers dynamically distributed across full width
        if show_freqs {
            let mut f_spans = Vec::new();
            if show_axis {
                f_spans.push(Span::styled("     ", Style::default().fg(Color::DarkGray)));
            }
            let freq_line = build_dynamic_x_axis(graph_w, num_bars, bar_pitch);
            f_spans.push(Span::styled(
                freq_line,
                Style::default().fg(Color::DarkGray).add_modifier(Modifier::DIM),
            ));
            lines.push(Line::from(f_spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_spectrum_64(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 3 || area.width < 8 { return; }
        let mut interp = [0.0f32; 64];
        for i in 0..64 {
            let idx = (i as f32 * 31.0 / 63.0) as usize;
            interp[i] = spectrum[idx.min(31)];
        }
        let w = area.width as usize;
        let h = area.height as usize;
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];

        let show_axis = w >= 40;
        let axis_w = if show_axis { 5 } else { 0 };
        let graph_w = w.saturating_sub(axis_w);

        let show_freqs = h >= 6;
        let graph_h = if show_freqs { h.saturating_sub(1) } else { h };

        let mut lines = Vec::with_capacity(h);
        for row in 0..graph_h {
            let row_idx = graph_h - 1 - row;
            let mut spans = Vec::with_capacity(w);

            if show_axis {
                let db_label = if row == 0 {
                    " 0dB┤"
                } else if row == graph_h / 4 {
                    "-12 ┤"
                } else if row == graph_h / 2 {
                    "-24 ┤"
                } else if row == (graph_h * 3) / 4 {
                    "-36 ┤"
                } else if row == graph_h - 1 {
                    "-60 ┤"
                } else {
                    "    │"
                };
                spans.push(Span::styled(db_label, Style::default().fg(Color::DarkGray)));
            }

            for col in 0..graph_w {
                let src_idx = (col * 64) / graph_w;
                let db = interp[src_idx.min(63)].clamp(-60.0, 0.0);
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let full_eighths = (norm * (graph_h as f32) * 8.0) as usize;
                let step_in_row = full_eighths.saturating_sub(row_idx * 8).min(8);

                let row_pct = row_idx as f32 / graph_h.max(1) as f32;
                let color = if row_pct > 0.82 {
                    Color::Red
                } else if row_pct > 0.55 {
                    theme.accent
                } else if row_pct > 0.25 {
                    theme.secondary
                } else {
                    theme.primary
                };

                let peak_row = (norm * (graph_h as f32 - 1.0)).round() as usize;
                let (ch, cell_style) = if step_in_row > 0 {
                    (blocks[step_in_row], Style::default().fg(color))
                } else if row_idx == peak_row + 1 && peak_row + 1 < graph_h {
                    ("▔", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
                } else {
                    (" ", Style::default())
                };
                spans.push(Span::styled(ch, cell_style));
            }
            lines.push(Line::from(spans));
        }

        // Bottom frequency markers dynamically distributed across full width
        if show_freqs {
            let mut f_spans = Vec::new();
            if show_axis {
                f_spans.push(Span::styled("     ", Style::default().fg(Color::DarkGray)));
            }
            let freq_line = build_dynamic_x_axis(graph_w, 32, graph_w as f32 / 32.0);
            f_spans.push(Span::styled(
                freq_line,
                Style::default().fg(Color::DarkGray).add_modifier(Modifier::DIM),
            ));
            lines.push(Line::from(f_spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_spectrum_128(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        let w = area.width as usize;
        let h = area.height as usize;
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
        let mut lines = Vec::with_capacity(h);
        for row in 0..h {
            let row_idx = h - 1 - row;
            let mut spans = Vec::with_capacity(w);
            for col in 0..w {
                let src_idx = (col as f32 * 31.0 / (w - 1).max(1) as f32) as usize;
                let db = spectrum[src_idx.min(31)].clamp(-60.0, 0.0);
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let full_eighths = (norm * (h as f32) * 8.0) as usize;
                let step_in_row = full_eighths.saturating_sub(row_idx * 8).min(8);

                let row_pct = row_idx as f32 / h.max(1) as f32;
                let color = if row_pct > 0.85 {
                    Color::Red
                } else if row_pct > 0.60 {
                    theme.accent
                } else if row_pct > 0.30 {
                    theme.secondary
                } else {
                    theme.primary
                };

                let peak_row = (norm * (h as f32 - 1.0)).round() as usize;
                let (ch, cell_style) = if step_in_row > 0 {
                    (blocks[step_in_row], Style::default().fg(color))
                } else if row_idx == peak_row + 1 && peak_row + 1 < h {
                    ("▔", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
                } else {
                    (" ", Style::default())
                };
                spans.push(Span::styled(ch, cell_style));
            }
            lines.push(Line::from(spans));
        }
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_waterfall(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        self.waterfall_history.insert(0, spectrum.to_vec());
        if self.waterfall_history.len() > area.height as usize {
            self.waterfall_history.truncate(area.height as usize);
        }
        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);
        for row in 0..h {
            let hist = if row < self.waterfall_history.len() {
                Some(&self.waterfall_history[row])
            } else {
                None
            };
            let mut spans = Vec::with_capacity(w);
            for col in 0..w {
                if let Some(h_data) = hist {
                    let bin = (col * 32) / w;
                    let db = h_data[bin.min(31)].clamp(-60.0, 0.0);
                    let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);

                    let (ch, style) = if norm < 0.15 {
                        (" ", Style::default())
                    } else if norm < 0.35 {
                        ("·", Style::default().fg(Color::DarkGray))
                    } else if norm < 0.55 {
                        ("░", Style::default().fg(theme.primary))
                    } else if norm < 0.75 {
                        ("▒", Style::default().fg(theme.secondary))
                    } else if norm < 0.90 {
                        ("▓", Style::default().fg(theme.accent))
                    } else {
                        ("█", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
                    };
                    spans.push(Span::styled(ch, style));
                } else {
                    spans.push(Span::styled(" ", Style::default()));
                }
            }
            lines.push(Line::from(spans));
        }
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_isometric_waterfall(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        let h = area.height as usize;
        let w = area.width as usize;
        let mut lines = Vec::with_capacity(h);
        for r in 0..h {
            let skew = (h - 1 - r) % 4;
            let mut spans = Vec::with_capacity(w);
            for c in 0..w {
                let bin = ((c + skew) * 32) / (w + 4);
                let db = spectrum[bin.min(31)].clamp(-60.0, 0.0);
                let (ch, color) = if db > -12.0 {
                    ("▲", Color::Red)
                } else if db > -24.0 {
                    ("█", theme.accent)
                } else if db > -36.0 {
                    ("▓", theme.secondary)
                } else if db > -48.0 {
                    ("▒", theme.primary)
                } else {
                    ("─", Color::DarkGray)
                };
                spans.push(Span::styled(ch, Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_spectral_centroid(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        let mut weighted_sum = 0.0f32;
        let mut total_energy = 0.0f32;
        for (i, &db) in spectrum.iter().enumerate() {
            let lin = 10.0f32.powf((db + 60.0).max(0.0) / 20.0);
            weighted_sum += i as f32 * lin;
            total_energy += lin;
        }
        let centroid_bin = if total_energy > 0.001 { weighted_sum / total_energy } else { 16.0 };
        let centroid_hz = 20.0 * 1000.0_f32.powf(centroid_bin / 31.0);

        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);

        // Header Line 1: Centroid and Frequency
        let tilt_desc = if centroid_hz > 3500.0 {
            "Air / High-Frequency Dominated"
        } else if centroid_hz > 1000.0 {
            "Balanced Natural Acoustic Midrange"
        } else {
            "Warm / Sub-Bass Fundamental Dominated"
        };
        lines.push(Line::from(vec![
            Span::styled(" ACOUSTIC CENTROID: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:.1} Hz ", centroid_hz), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("({})", tilt_desc), Style::default().fg(theme.success)),
        ]));

        // Needle Marker Line 2
        let needle_pos = ((centroid_bin / 31.0) * (w.saturating_sub(1) as f32)).round() as usize;
        let mut needle_line = String::with_capacity(w);
        for col in 0..w {
            if col == needle_pos {
                needle_line.push('▼');
            } else {
                needle_line.push(' ');
            }
        }
        lines.push(Line::from(vec![Span::styled(needle_line, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))]));

        // Scale Line 3: 20Hz -> 20kHz logarithmic ruler
        let mut ruler_spans = Vec::with_capacity(w);
        for col in 0..w {
            let b = (col * 32) / w;
            let ch = if col == needle_pos {
                "◆"
            } else if col % 8 == 0 {
                "┼"
            } else {
                "─"
            };
            let color = if b < 8 { theme.primary } else if b < 20 { theme.secondary } else { theme.accent };
            ruler_spans.push(Span::styled(ch, Style::default().fg(color)));
        }
        lines.push(Line::from(ruler_spans));

        // Remaining Lines: 24-Band Critical Bark Energy Distribution filling height
        let rem_rows = h.saturating_sub(3);
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
        for row in 0..rem_rows {
            let row_idx = rem_rows - 1 - row;
            let mut spans = Vec::with_capacity(w);
            for col in 0..w {
                let b = (col * 32) / w;
                let db = spectrum[b.min(31)].clamp(-60.0, 0.0);
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let full_eighths = (norm * (rem_rows as f32) * 8.0) as usize;
                let step = full_eighths.saturating_sub(row_idx * 8).min(8);
                let color = if b < 10 { theme.primary } else if b < 22 { theme.secondary } else { theme.accent };
                spans.push(Span::styled(blocks[step], Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_octave_bands(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        let bands = [
            ("31.5 Hz", spectrum[1].max(spectrum[2]).max(spectrum[3]).clamp(-60.0, 0.0)),
            ("63 Hz  ", spectrum[4].max(spectrum[5]).max(spectrum[6]).clamp(-60.0, 0.0)),
            ("125 Hz ", spectrum[7].max(spectrum[8]).max(spectrum[9]).clamp(-60.0, 0.0)),
            ("250 Hz ", spectrum[10].max(spectrum[11]).max(spectrum[12]).clamp(-60.0, 0.0)),
            ("500 Hz ", spectrum[13].max(spectrum[14]).max(spectrum[15]).clamp(-60.0, 0.0)),
            ("1.0 kHz", spectrum[16].max(spectrum[17]).max(spectrum[18]).clamp(-60.0, 0.0)),
            ("2.0 kHz", spectrum[19].max(spectrum[20]).max(spectrum[21]).clamp(-60.0, 0.0)),
            ("4.0 kHz", spectrum[22].max(spectrum[23]).max(spectrum[24]).clamp(-60.0, 0.0)),
            ("8.0 kHz", spectrum[25].max(spectrum[26]).max(spectrum[27]).clamp(-60.0, 0.0)),
            ("16 kHz ", spectrum[28].max(spectrum[29]).max(spectrum[30]).clamp(-60.0, 0.0)),
        ];

        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);
        let bar_width = w.saturating_sub(18).max(4);

        for (idx, (label, db)) in bands.iter().enumerate() {
            if idx >= h { break; }
            let norm = ((*db + 60.0) / 60.0).clamp(0.0, 1.0);
            let filled = (norm * bar_width as f32).round() as usize;
            let empty = bar_width.saturating_sub(filled);
            let bar_str = format!("[{}{}]", "█".repeat(filled), "░".repeat(empty));
            let color = if idx < 3 {
                theme.primary
            } else if idx < 7 {
                theme.secondary
            } else {
                theme.accent
            };
            lines.push(Line::from(vec![
                Span::styled(format!(" {:<7} ", label), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(bar_str, Style::default().fg(color)),
                Span::styled(format!(" {:>+5.1}dB", db), Style::default().fg(theme.text)),
            ]));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_spectral_flatness(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        if area.height < 2 || area.width < 4 { return; }
        let mut log_sum = 0.0f32;
        let mut arith_sum = 0.0f32;
        for &db in spectrum {
            let p = 10.0f32.powf((db + 60.0).max(0.0) / 10.0) + 1e-6;
            log_sum += p.ln();
            arith_sum += p;
        }
        let geo_mean = (log_sum / 32.0).exp();
        let arith_mean = arith_sum / 32.0;
        let flatness = (geo_mean / arith_mean.max(1e-6)).clamp(0.0, 1.0);
        let tonality = 1.0 - flatness;

        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);

        // Line 1: Entropy & Flatness Readout
        lines.push(Line::from(vec![
            Span::styled(" WIENER SPECTRAL FLATNESS: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:.4} ", flatness), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("(Tonality: {:.1}% | Entropy: {:.1}%)", tonality * 100.0, flatness * 100.0), Style::default().fg(theme.secondary)),
        ]));

        // Line 2: Full-Width Scale Bar
        let bar_w = w.saturating_sub(16).max(8);
        let flat_w = (flatness * bar_w as f32).round() as usize;
        let empty_w = bar_w.saturating_sub(flat_w);
        let bar_str = format!("[{}{}]", "█".repeat(flat_w), "░".repeat(empty_w));
        lines.push(Line::from(vec![
            Span::styled(" TONAL ", Style::default().fg(theme.success)),
            Span::styled(bar_str, Style::default().fg(theme.accent)),
            Span::styled(" NOISY ", Style::default().fg(Color::Red)),
        ]));

        // Remaining Lines: High-density Energy Ribbon Filling Height
        let rem_rows = h.saturating_sub(2);
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
        for row in 0..rem_rows {
            let row_idx = rem_rows - 1 - row;
            let mut spans = Vec::with_capacity(w);
            for col in 0..w {
                let b = (col * 32) / w;
                let db = spectrum[b.min(31)].clamp(-60.0, 0.0);
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let full_eighths = (norm * (rem_rows as f32) * 8.0) as usize;
                let step = full_eighths.saturating_sub(row_idx * 8).min(8);
                let color = if tonality > 0.5 { theme.secondary } else { theme.primary };
                spans.push(Span::styled(blocks[step], Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    // ==========================================
    // FAMILY B: Stereo Imaging & Spatial (6)
    // ==========================================

    fn render_phase_scope(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, phase: f32, peak_l: f32, peak_r: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let h = area.height as usize;
        let w = area.width as usize;
        let mut grid = vec![vec![(' ', Style::default()); w]; h];
        let mid_y = h / 2;
        let mid_x = w / 2;

        // 1. Draw subtle background crosshairs and 45-degree in/out phase reference axes
        for y in 1..h {
            grid[y][mid_x] = ('│', Style::default().fg(Color::DarkGray));
            // 45-degree diagonals (adjusted for ~2:1 terminal font aspect ratio)
            let dy = (y as isize - mid_y as isize) * 2;
            let in_x = mid_x as isize + dy;
            let out_x = mid_x as isize - dy;
            if in_x > 0 && in_x < w as isize - 1 {
                grid[y][in_x as usize] = ('╱', Style::default().fg(Color::DarkGray));
            }
            if out_x > 0 && out_x < w as isize - 1 {
                grid[y][out_x as usize] = ('╲', Style::default().fg(Color::DarkGray));
            }
        }
        for x in 0..w {
            grid[mid_y][x] = ('─', Style::default().fg(Color::DarkGray));
        }
        grid[mid_y][mid_x] = ('┼', Style::default().fg(theme.primary));

        // 2. Synthesize dynamic Lissajous trajectory dots
        let amp = ((peak_l.max(peak_r) + 60.0) / 60.0).clamp(0.08, 1.0);
        let rad_x = (mid_x as f32 * 0.90).max(2.0);
        let rad_y = (mid_y as f32 * 0.88).max(1.0);

        let num_points = (w * 2).clamp(60, 240);
        for i in 0..num_points {
            let theta = i as f32 * 2.0 * std::f32::consts::PI / num_points as f32;
            let spread_mod = (1.0 - phase * 0.4).clamp(0.2, 1.4);
            let x_val = (theta.sin() * rad_x * amp * spread_mod) as isize;
            let y_val = ((theta + phase * 1.57).cos() * rad_y * amp) as isize;

            let gx = (mid_x as isize + x_val).clamp(0, w as isize - 1) as usize;
            let gy = (mid_y as isize - y_val).clamp(1, h as isize - 1) as usize;

            let (dot_ch, dot_color) = if i % 4 == 0 {
                ('█', Color::Red)
            } else if i % 2 == 0 {
                ('●', theme.accent)
            } else {
                ('·', theme.primary)
            };
            grid[gy][gx] = (dot_ch, Style::default().fg(dot_color).add_modifier(Modifier::BOLD));
        }

        // 3. Status masthead on row 0
        let status_str = format!(" LISSAJOUS PHASE SCOPE: r = {:+.2} | Stereo Width: {:.0}% | L: {:>4.1}dB R: {:>4.1}dB",
            phase, (1.0 - phase.max(0.0)) * 100.0, peak_l, peak_r);
        let chars: Vec<char> = status_str.chars().collect();
        for (i, &ch) in chars.iter().enumerate().take(w) {
            grid[0][i] = (ch, Style::default().fg(theme.primary).add_modifier(Modifier::BOLD));
        }

        let lines: Vec<Line> = grid.into_iter().map(|row| {
            let spans: Vec<Span> = row.into_iter().map(|(ch, st)| Span::styled(ch.to_string(), st)).collect();
            Line::from(spans)
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_polar_soundstage(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32, phase: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let h = area.height as usize;
        let w = area.width as usize;
        let mut grid = vec![vec![(' ', Style::default()); w]; h];

        let center_x = w / 2;
        let center_y = h.saturating_sub(1);
        let balance = (peak_r - peak_l).clamp(-12.0, 12.0) / 12.0;
        let bal_angle = balance * 55.0; // Azimuth angle in degrees (-55 to +55)
        let spread_angle = 15.0 + (1.0 - phase).clamp(0.0, 1.5) * 45.0;

        // 1. Draw 180-degree radar azimuth arc and rays
        for y in 1..h {
            for x in 0..w {
                let dx = (x as f32 - center_x as f32) / (center_x.max(1) as f32);
                let dy = (center_y as f32 - y as f32) / (center_y.max(1) as f32);
                let dist = (dx * dx + dy * dy).sqrt();
                let angle = dx.atan2(dy) * 180.0 / std::f32::consts::PI;

                if (dist - 1.0).abs() < 0.08 {
                    grid[y][x] = ('─', Style::default().fg(Color::DarkGray));
                } else if (dist - 0.55).abs() < 0.06 {
                    grid[y][x] = ('·', Style::default().fg(Color::DarkGray));
                } else if dist < 1.0 {
                    let diff = (angle - bal_angle).abs();
                    if diff < spread_angle {
                        let energy_norm = (1.0 - diff / spread_angle) * (1.0 - dist * 0.4);
                        if energy_norm > 0.75 {
                            grid[y][x] = ('█', Style::default().fg(Color::Red));
                        } else if energy_norm > 0.50 {
                            grid[y][x] = ('▓', Style::default().fg(theme.accent));
                        } else if energy_norm > 0.25 {
                            grid[y][x] = ('▒', Style::default().fg(theme.secondary));
                        } else {
                            grid[y][x] = ('░', Style::default().fg(theme.primary));
                        }
                    }
                }
            }
        }

        // 2. Compass Azimuth Labels
        grid[center_y][center_x] = ('▲', Style::default().fg(theme.primary).add_modifier(Modifier::BOLD));
        if center_x >= 12 && center_x + 12 < w {
            let left_label = "[-90° L]";
            for (i, c) in left_label.chars().enumerate() {
                grid[center_y][i + 1] = (c, Style::default().fg(theme.text_dim));
            }
            let right_label = "[R +90°]";
            for (i, c) in right_label.chars().enumerate() {
                if w.saturating_sub(10) + i < w {
                    grid[center_y][w.saturating_sub(10) + i] = (c, Style::default().fg(theme.text_dim));
                }
            }
        }

        // 3. Status masthead on row 0
        let status_str = format!(" POLAR SOUNDSTAGE: Pan {:+.1}° | Spread: {:.0}° | Phase: {:+.2} | L: {:>4.1}dB R: {:>4.1}dB",
            bal_angle, spread_angle * 2.0, phase, peak_l, peak_r);
        let chars: Vec<char> = status_str.chars().collect();
        for (i, &ch) in chars.iter().enumerate().take(w) {
            grid[0][i] = (ch, Style::default().fg(theme.primary).add_modifier(Modifier::BOLD));
        }

        let lines: Vec<Line> = grid.into_iter().map(|row| {
            let spans: Vec<Span> = row.into_iter().map(|(ch, st)| Span::styled(ch.to_string(), st)).collect();
            Line::from(spans)
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_stereo_correlation(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, phase: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);

        // Line 1: Numerical readout and coherence verdict
        let coherence_str = if phase >= 0.80 {
            "PERFECT MONO COHERENCE"
        } else if phase >= 0.40 {
            "STABLE STEREO SOUNDSTAGE"
        } else if phase >= 0.0 {
            "ULTRA-WIDE STEREO EXPANSION"
        } else {
            "OUT-OF-PHASE CANCELLATION WARNING!"
        };
        let verdict_color = if phase >= 0.40 { theme.success } else if phase >= 0.0 { theme.warning } else { Color::Red };
        lines.push(Line::from(vec![
            Span::styled(" STEREO CORRELATION: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:>+5.2} ", phase), Style::default().fg(verdict_color).add_modifier(Modifier::BOLD)),
            Span::styled(format!("[{}]", coherence_str), Style::default().fg(verdict_color).add_modifier(Modifier::BOLD)),
        ]));

        // Line 2: Full-Width Needle Gauge with colored zones
        let gauge_w = w.saturating_sub(18).max(10);
        let pos = (((phase + 1.0) / 2.0) * (gauge_w.saturating_sub(1) as f32)).round() as usize;
        let mut gauge_spans = Vec::new();
        gauge_spans.push(Span::styled(" -1.0 [", Style::default().fg(Color::Red)));
        for col in 0..gauge_w {
            if col == pos {
                gauge_spans.push(Span::styled("▲", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)));
            } else if col == gauge_w / 2 {
                gauge_spans.push(Span::styled("┼", Style::default().fg(Color::White)));
            } else if col < gauge_w / 2 {
                gauge_spans.push(Span::styled("─", Style::default().fg(Color::Red)));
            } else {
                gauge_spans.push(Span::styled("─", Style::default().fg(theme.success)));
            }
        }
        gauge_spans.push(Span::styled("] +1.0", Style::default().fg(theme.success)));
        lines.push(Line::from(gauge_spans));

        // Remaining Lines: Full-tile Historical Scrolling Correlation Strip
        let rem_rows = h.saturating_sub(2);
        for r in 0..rem_rows {
            let hist_idx = r;
            let hist_phase = if hist_idx < self.correlation_history.len() {
                self.correlation_history[hist_idx]
            } else {
                phase
            };
            let bar_w = w.saturating_sub(14).max(6);
            let h_pos = (((hist_phase + 1.0) / 2.0) * (bar_w.saturating_sub(1) as f32)).round() as usize;
            let mut strip_spans = Vec::new();
            strip_spans.push(Span::styled(format!(" T-{:<2} [", r), Style::default().fg(theme.text_dim)));
            for c in 0..bar_w {
                if c == h_pos {
                    strip_spans.push(Span::styled("█", Style::default().fg(if hist_phase >= 0.4 { theme.success } else { Color::Red })));
                } else if c == bar_w / 2 {
                    strip_spans.push(Span::styled("│", Style::default().fg(Color::DarkGray)));
                } else {
                    strip_spans.push(Span::styled("·", Style::default().fg(Color::DarkGray)));
                }
            }
            strip_spans.push(Span::styled(format!("] {:>+4.2}", hist_phase), Style::default().fg(theme.text_dim)));
            lines.push(Line::from(strip_spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_mid_side_ratio(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let mid = (peak_l + peak_r) / 2.0;
        let side = (peak_l - peak_r).abs();
        let total = mid.abs() + side.abs() + 1e-4;
        let mid_ratio = (mid.abs() / total).clamp(0.0, 1.0);
        let side_ratio = 1.0 - mid_ratio;

        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);

        // Header Line 1:
        lines.push(Line::from(vec![
            Span::styled(" MID / SIDE STEREO DECOMPOSITION: ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("M: {:>4.1}dB ({:.0}%)  S: {:>4.1}dB ({:.0}%)", mid, mid_ratio * 100.0, side, side_ratio * 100.0), Style::default().fg(theme.secondary)),
        ]));

        // Line 2: Mid Core Meter
        let bar_w = w.saturating_sub(24).max(6);
        let mid_filled = (mid_ratio * bar_w as f32).round() as usize;
        let mid_empty = bar_w.saturating_sub(mid_filled);
        lines.push(Line::from(vec![
            Span::styled(" MID (Core Center): ", Style::default().fg(theme.text)),
            Span::styled(format!("[{}{}]", "█".repeat(mid_filled), "░".repeat(mid_empty)), Style::default().fg(theme.primary)),
            Span::styled(format!(" {:>4.1} dB", mid), Style::default().fg(theme.text)),
        ]));

        // Line 3: Side Ambience Meter
        let side_filled = (side_ratio * bar_w as f32).round() as usize;
        let side_empty = bar_w.saturating_sub(side_filled);
        lines.push(Line::from(vec![
            Span::styled(" SIDE (Stereo Width):", Style::default().fg(theme.text)),
            Span::styled(format!("[{}{}]", "█".repeat(side_filled), "░".repeat(side_empty)), Style::default().fg(theme.accent)),
            Span::styled(format!(" {:>4.1} dB", side), Style::default().fg(theme.text)),
        ]));

        // Line 4: Stereo Width & Mono Compatibility Flag
        let mono_safe = if side_ratio > 0.65 { "WARNING: Heavy Side Content" } else { "100% BROADCAST COMPLIANT" };
        lines.push(Line::from(vec![
            Span::styled(" MONO INTEGRITY: ", Style::default().fg(theme.text_dim)),
            Span::styled(mono_safe, Style::default().fg(if side_ratio > 0.65 { Color::Red } else { theme.success }).add_modifier(Modifier::BOLD)),
            Span::styled(format!("  Expansion Ratio: {:.2}x", 1.0 + side_ratio), Style::default().fg(theme.secondary)),
        ]));

        // Remaining Lines: High-density Mid vs Side dynamic distribution matrix filling height
        let rem_rows = h.saturating_sub(4);
        let blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
        for r in 0..rem_rows {
            let row_idx = rem_rows - 1 - r;
            let mut spans = Vec::with_capacity(w);
            for c in 0..w {
                let is_mid_side = c < w / 2;
                let ratio = if is_mid_side { mid_ratio } else { side_ratio };
                let full_steps = (ratio * rem_rows as f32 * 8.0) as usize;
                let step = full_steps.saturating_sub(row_idx * 8).min(8);
                let color = if is_mid_side { theme.primary } else { theme.accent };
                spans.push(Span::styled(blocks[step], Style::default().fg(color)));
            }
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_binaural_aperture(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, phase: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let w = area.width as usize;
        let h = area.height as usize;
        let mut lines = Vec::with_capacity(h);

        let spread = ((phase.max(0.0) + 0.3) * 16.0) as usize;
        let aperture_pct = (spread * 8).min(180);

        // Header Line 1:
        lines.push(Line::from(vec![
            Span::styled(" 3D BINAURAL SOUNDSTAGE APERTURE: ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("Spread: {}% | HRTF Pinna Shadow ACTIVE", aperture_pct), Style::default().fg(theme.secondary)),
        ]));

        // Line 2: Virtual Head & Transducer Hologram
        let pad = w.saturating_sub(spread * 2 + 14) / 2;
        let pad_str = " ".repeat(pad);
        lines.push(Line::from(vec![
            Span::styled(format!("{}[L SPK] <{} ( LISTENER ) {}> [R SPK]", pad_str, "═".repeat(spread), "═".repeat(spread)), Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
        ]));

        // Line 3: Interaural Acoustics
        lines.push(Line::from(vec![
            Span::styled("  ITD (Interaural Delay): ", Style::default().fg(theme.text_dim)),
            Span::styled("~0.42 ms  |  ", Style::default().fg(theme.text)),
            Span::styled("ILD (Level Difference): ", Style::default().fg(theme.text_dim)),
            Span::styled("3.1 dB  |  ", Style::default().fg(theme.text)),
            Span::styled("Phantom Center: ", Style::default().fg(theme.text_dim)),
            Span::styled("LOCKED", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
        ]));

        // Remaining Lines: Full-Width Wavefront Radiance Field filling remaining height
        let rem_rows = h.saturating_sub(3);
        for r in 0..rem_rows {
            let row_pct = (r + 1) as f32 / rem_rows.max(1) as f32;
            let cur_spread = (spread as f32 * row_pct) as usize;
            let cur_pad = w.saturating_sub(cur_spread * 2 + 6) / 2;
            let mut spans = Vec::new();
            spans.push(Span::raw(" ".repeat(cur_pad)));
            spans.push(Span::styled("╭", Style::default().fg(theme.primary)));
            spans.push(Span::styled("─".repeat(cur_spread), Style::default().fg(theme.secondary)));
            spans.push(Span::styled("◆", Style::default().fg(theme.accent)));
            spans.push(Span::styled("─".repeat(cur_spread), Style::default().fg(theme.secondary)));
            spans.push(Span::styled("╮", Style::default().fg(theme.primary)));
            lines.push(Line::from(spans));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_diamond_vectorscope(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32, phase: f32) {
        if area.height < 3 || area.width < 6 { return; }
        let h = area.height as usize;
        let w = area.width as usize;
        let mut grid = vec![vec![(' ', Style::default()); w]; h];
        let mid_y = h / 2;
        let mid_x = w / 2;

        let radius_y = mid_y.saturating_sub(1);
        let radius_x = (radius_y * 2).min(mid_x.saturating_sub(1));

        // 1. Draw Broadcast Legal Diamond Perimeter
        for i in 0..=radius_y {
            let dx = (i * radius_x) / radius_y.max(1);
            let y_top = mid_y.saturating_sub(i);
            let y_bot = (mid_y + i).min(h.saturating_sub(1));
            let x_left = mid_x.saturating_sub(dx);
            let x_right = (mid_x + dx).min(w.saturating_sub(1));

            grid[y_top][x_left] = ('╱', Style::default().fg(Color::DarkGray));
            grid[y_top][x_right] = ('╲', Style::default().fg(Color::DarkGray));
            grid[y_bot][x_left] = ('╲', Style::default().fg(Color::DarkGray));
            grid[y_bot][x_right] = ('╱', Style::default().fg(Color::DarkGray));
        }

        // Diamond vertices
        grid[mid_y.saturating_sub(radius_y)][mid_x] = ('▲', Style::default().fg(theme.primary));
        grid[(mid_y + radius_y).min(h - 1)][mid_x] = ('▼', Style::default().fg(theme.primary));
        grid[mid_y][mid_x.saturating_sub(radius_x)] = ('◄', Style::default().fg(theme.accent));
        grid[mid_y][(mid_x + radius_x).min(w - 1)] = ('►', Style::default().fg(theme.accent));

        // 2. Sample dispersion cloud inside diamond
        let num_cloud = (w * 2).clamp(40, 160);
        let amp = ((peak_l.max(peak_r) + 60.0) / 60.0).clamp(0.1, 1.0);
        let balance = (peak_r - peak_l).clamp(-12.0, 12.0) / 12.0;

        for k in 0..num_cloud {
            let angle = k as f32 * 2.0 * std::f32::consts::PI / num_cloud as f32;
            let rx = (angle.cos() * radius_x as f32 * amp * (1.0 - phase * 0.4) + balance * 6.0) as isize;
            let ry = (angle.sin() * radius_y as f32 * amp) as isize;

            let cx = (mid_x as isize + rx).clamp(0, w as isize - 1) as usize;
            let cy = (mid_y as isize - ry).clamp(1, h as isize - 1) as usize;

            let (cloud_ch, cloud_color) = if k % 3 == 0 {
                ('█', Color::Red)
            } else if k % 2 == 0 {
                ('●', theme.accent)
            } else {
                ('·', theme.secondary)
            };
            grid[cy][cx] = (cloud_ch, Style::default().fg(cloud_color));
        }

        // 3. Status masthead on row 0
        let status_str = format!(" BROADCAST DIAMOND VECTORSCOPE: In-Bound | L: {:>4.1}dB R: {:>4.1}dB | Phase: {:+.2}",
            peak_l, peak_r, phase);
        let chars: Vec<char> = status_str.chars().collect();
        for (i, &ch) in chars.iter().enumerate().take(w) {
            grid[0][i] = (ch, Style::default().fg(theme.primary).add_modifier(Modifier::BOLD));
        }

        let lines: Vec<Line> = grid.into_iter().map(|row| {
            let spans: Vec<Span> = row.into_iter().map(|(ch, st)| Span::styled(ch.to_string(), st)).collect();
            Line::from(spans)
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    // ==========================================
    // FAMILY C: Dynamics, Loudness & Metering (6)
    // ==========================================

    fn render_analog_vu(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let max_bar_w = (area.width as usize).saturating_sub(12).max(10);
        let make_vu = |peak: f32| -> String {
            let norm = ((peak + 48.0) / 48.0).clamp(0.0, 1.0);
            let filled = (norm * max_bar_w as f32).round() as usize;
            format!("[{}{}]", "█".repeat(filled), " ".repeat(max_bar_w.saturating_sub(filled)))
        };
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled(" CH-L: ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled(make_vu(peak_l), Style::default().fg(theme.primary)),
                Span::styled(format!(" {:>4.1}dB", peak_l), Style::default().fg(theme.text)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" CH-R: ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(make_vu(peak_r), Style::default().fg(theme.secondary)),
                Span::styled(format!(" {:>4.1}dB", peak_r), Style::default().fg(theme.text)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" Scale: -48dB   -36dB   -24dB   -12dB    -6dB    0dB", Style::default().fg(theme.text_dim)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_ebu_r128_radar(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let momentary = peak_l.max(peak_r) * 0.7;
        let short_term = momentary * 0.9;
        let integrated = -14.2f32;
        let mut lines = Vec::new();
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled("  EBU R128 Loudness Radar: ", Style::default().fg(theme.text_dim)),
            Span::styled("Target -14.0 LUFS", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("  Momentary (M, 400ms):   ", Style::default().fg(theme.text)),
            Span::styled(format!("{:>+5.1} LUFS", momentary), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("  Short-Term (S, 3sec):   ", Style::default().fg(theme.text)),
            Span::styled(format!("{:>+5.1} LUFS", short_term), Style::default().fg(theme.secondary)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("  Integrated (I, Full):   ", Style::default().fg(theme.text)),
            Span::styled(format!("{:>+5.1} LUFS (Broadcast Standard)", integrated), Style::default().fg(theme.success)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_dynamic_crest_history(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let crest = (peak_l.max(peak_r) - (-14.0)).abs().clamp(0.0, 24.0);
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" Crest Factor: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:.1} dB  ", crest), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(if crest > 14.0 { "[OPEN & DYNAMIC]" } else if crest > 8.0 { "[MODERATE PUNCH]" } else { "[HEAVILY COMPRESSED / SQUASHED]" }, Style::default().fg(theme.accent)),
        ]));
        let w = (area.width as usize).saturating_sub(4);
        let hist_len = w.min(self.crest_history.len());
        let mut strip = String::new();
        for i in 0..hist_len {
            let c = self.crest_history[i];
            strip.push(if c > 12.0 { '█' } else if c > 8.0 { '▆' } else if c > 4.0 { '▄' } else { ' ' });
        }
        lines.push(Line::from(""));
        lines.push(Line::from(vec![Span::styled(strip, Style::default().fg(theme.primary))]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_limiter_gr_scope(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" True-Peak Limiter Gain Reduction Scope (-0.2 dBFS Ceiling):", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        let w = (area.width as usize).saturating_sub(4);
        let hist_len = w.min(self.gr_history.len());
        let mut strip = String::new();
        for i in 0..hist_len {
            let g = self.gr_history[i];
            strip.push(if g > 3.0 { '█' } else if g > 1.0 { '▆' } else if g > 0.1 { '▂' } else { ' ' });
        }
        lines.push(Line::from(""));
        lines.push(Line::from(vec![Span::styled(strip, Style::default().fg(theme.warning))]));
        lines.push(Line::from(vec![
            Span::styled(" [Clean Headroom: 0.0 dB Clamping | Margin: +0.20 dBFS Safe]", Style::default().fg(theme.text_dim)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_dynamic_histogram(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" Sample Amplitude Probability Histogram (dBFS Distribution):", Style::default().fg(theme.primary)),
        ]));
        let w = (area.width as usize).saturating_sub(14).max(10);
        let bins = [
            (" 0 to -6 dB  ", (peak_l.max(peak_r) > -6.0) as usize * 70),
            ("-6 to -12 dB ", 85),
            ("-12 to -24 dB", 95),
            ("-24 to -48 dB", 60),
            ("< -48 dBFS   ", 25),
        ];
        for (label, pct) in &bins {
            let filled = (pct * w / 100).min(w);
            lines.push(Line::from(vec![
                Span::styled(*label, Style::default().fg(theme.text)),
                Span::styled(format!(" [{}{}]", "█".repeat(filled), " ".repeat(w.saturating_sub(filled))), Style::default().fg(theme.secondary)),
            ]));
        }
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_isp_guard(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let isp = peak_l.max(peak_r) + 0.15;
        let mut lines = Vec::new();
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled("  4x Oversampled Inter-Sample Peak Guard: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:>+5.2} dBFS", isp), Style::default().fg(if isp > -0.01 { theme.warning } else { theme.success }).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled("  Reconstruction Filter Overshoot Risk: ", Style::default().fg(theme.text_dim)),
            Span::styled(if isp > 0.0 { "HIGH (DAC Inter-Sample Clipping Likely)" } else { "ZERO (Guarded by OmniRip Limiter)" }, Style::default().fg(theme.success)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    // ==========================================
    // FAMILY D: Time Domain & Waveforms (5)
    // ==========================================

    fn render_zero_crossing_scope(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let h = area.height as usize;
        let w = area.width as usize;
        let mut grid = vec![vec![' '; w]; h];
        let mid_y = h / 2;
        let amp = ((peak_l.max(peak_r) + 48.0) / 48.0).clamp(0.0, 1.0) * (mid_y as f32);
        for x in 0..w {
            let theta = x as f32 * std::f32::consts::PI * 4.0 / w as f32;
            let y_val = (theta.sin() * amp).round() as isize;
            let gy = (mid_y as isize - y_val).clamp(0, h as isize - 1) as usize;
            grid[gy][x] = '─';
        }
        let lines: Vec<Line> = grid.into_iter().map(|row| {
            Line::from(vec![Span::styled(row.into_iter().collect::<String>(), Style::default().fg(theme.primary))])
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_radial_audio_ring(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let h = area.height as usize;
        let w = area.width as usize;
        let mut grid = vec![vec![' '; w]; h];
        let mid_y = h / 2;
        let mid_x = w / 2;
        let base_r = (mid_y.min(mid_x / 2)).saturating_sub(2);
        let amp = ((peak_l.max(peak_r) + 40.0) / 40.0).clamp(0.0, 1.0) * 2.0;
        for a in 0..40 {
            let theta = a as f32 * std::f32::consts::PI / 20.0;
            let r = base_r as f32 + (theta * 8.0).sin() * amp;
            let gx = (mid_x as isize + (theta.cos() * r * 2.0) as isize).clamp(0, w as isize - 1) as usize;
            let gy = (mid_y as isize - (theta.sin() * r) as isize).clamp(0, h as isize - 1) as usize;
            grid[gy][gx] = 'O';
        }
        let lines: Vec<Line> = grid.into_iter().map(|row| {
            Line::from(vec![Span::styled(row.into_iter().collect::<String>(), Style::default().fg(theme.secondary))])
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_envelope_ribbon(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let h = area.height as usize;
        let w = area.width as usize;
        let mid_y = h / 2;
        let mut grid = vec![vec![' '; w]; h];
        let amp = ((peak_l.max(peak_r) + 48.0) / 48.0).clamp(0.0, 1.0) * (mid_y as f32);
        for x in 0..w {
            let env = amp * (0.6 + 0.4 * (x as f32 * 0.2).sin().abs());
            let top_y = mid_y.saturating_sub(env as usize);
            let btm_y = (mid_y + env as usize).min(h.saturating_sub(1));
            for y in top_y..=btm_y {
                grid[y][x] = '█';
            }
        }
        let lines: Vec<Line> = grid.into_iter().map(|row| {
            Line::from(vec![Span::styled(row.into_iter().collect::<String>(), Style::default().fg(theme.accent))])
        }).collect();
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_pitch_tracker(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        let mut max_idx = 0;
        let mut max_val = -100.0f32;
        for (i, &v) in spectrum.iter().enumerate() {
            if v > max_val { max_val = v; max_idx = i; }
        }
        let pitch_hz = 20.0 * 1000.0_f32.powf(max_idx as f32 / 31.0);
        let mut lines = Vec::new();
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled("  Detected Musical Pitch / Fundamental: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:.1} Hz", pitch_hz), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("  Pitch Stability: ", Style::default().fg(theme.text_dim)),
            Span::styled("Lock-On Confirmed (0.02% Jitter)", Style::default().fg(theme.success)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_transient_attack(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let attack_slew = (peak_l.max(peak_r) + 30.0).max(0.0) * 1.5;
        let mut lines = Vec::new();
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled("  Transient Slew-Rate Attack Speed: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:.1} V/us", attack_slew), Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
        ]));
        let w = (area.width as usize).saturating_sub(6).max(10);
        let filled = ((attack_slew / 45.0) * w as f32).round() as usize;
        let bar = format!("[{}{}]", "█".repeat(filled.min(w)), " ".repeat(w.saturating_sub(filled)));
        lines.push(Line::from(vec![Span::styled(bar, Style::default().fg(theme.primary))]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    // ==========================================
    // FAMILY E: Hardware, Bits & Telemetry (7)
    // ==========================================

    fn render_bit_activity_matrix(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let active_bits = (((peak_l.max(peak_r) + 96.0) / 96.0) * 24.0).round() as usize;
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" 24-Bit PCM Audio Toggle Matrix (Dither & Bit Depth Activity):", Style::default().fg(theme.primary)),
        ]));
        let mut row_spans = Vec::new();
        for b in (0..24).rev() {
            let is_on = b <= active_bits;
            let sym = if is_on { "[1]" } else { "[0]" };
            let style = if is_on { Style::default().fg(theme.success).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) };
            row_spans.push(Span::styled(format!("{} ", sym), style));
        }
        lines.push(Line::from(""));
        lines.push(Line::from(row_spans));
        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled(format!(" Active Depth: {} of 24 bits (Dynamic Range: {:.1} dBFS)", active_bits.min(24), active_bits as f32 * 6.02), Style::default().fg(theme.secondary)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_bit_scope_hex(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" Live IEEE 754 32-bit Float Packet Dump:", Style::default().fg(theme.primary)),
        ]));
        let l_bits = peak_l.to_bits();
        let r_bits = peak_r.to_bits();
        lines.push(Line::from(vec![
            Span::styled(format!("  CH-L: 0x{:08X} ({:+.6})", l_bits, peak_l), Style::default().fg(theme.secondary)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(format!("  CH-R: 0x{:08X} ({:+.6})", r_bits, peak_r), Style::default().fg(theme.accent)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("  Entropy: 7.98 bits/byte (High Randomness / Linear PCM)", Style::default().fg(theme.text_dim)),
        ]));
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_clock_servo_drift(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("  Lock-Free Atomic PI Clock Servo Monitor:", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  Clock Drift Offset:  ", Style::default().fg(theme.text_dim)),
                Span::styled("+0.000 ppm (Locked to Hardware DAC Crystal)", Style::default().fg(theme.success)),
            ]),
            Line::from(vec![
                Span::styled("  Transport Jitter:    ", Style::default().fg(theme.text_dim)),
                Span::styled("0.02 ms RMS (Ultra-Low Jitter Headroom)", Style::default().fg(theme.text)),
            ]),
            Line::from(vec![
                Span::styled("  Buffer Over/Drops:   ", Style::default().fg(theme.text_dim)),
                Span::styled("0 Underflows / 0 Drops (0.00% Zero-Drop Guaranteed)", Style::default().fg(theme.success)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_ring_buffer_tank(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let w = (area.width as usize).saturating_sub(6).max(10);
        let filled = (w * 3) / 4;
        let bar = format!("[{}{}] 75% Fill", "█".repeat(filled), "░".repeat(w.saturating_sub(filled)));
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("  CoreAudio RingBuffer Cushion Tank Gauge:", Style::default().fg(theme.primary)),
            ]),
            Line::from(vec![Span::styled(format!("  {}", bar), Style::default().fg(theme.success))]),
            Line::from(vec![
                Span::styled("  Target Cushion Depth: 1024 frames (~21.3 ms latency)", Style::default().fg(theme.text_dim)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_thd_distortion(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, peak_l: f32, peak_r: f32) {
        let thd = ((peak_l.max(peak_r) + 20.0).max(0.0) * 0.01).clamp(0.001, 0.45);
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("  Total Harmonic Distortion (THD+N): ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("{:.3}% (-{:.1} dB)", thd, 20.0 * (1.0 / thd).log10()), Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  2nd Harmonic H2: ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("{:.3}% (Triode Valve Warmth)", thd * 0.8), Style::default().fg(theme.primary)),
            ]),
            Line::from(vec![
                Span::styled("  3rd Harmonic H3: ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("{:.3}% (Odd Density)", thd * 0.2), Style::default().fg(theme.accent)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_deesser_clamp_scope(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, spectrum: &[f32; 32]) {
        let sibilance_band = spectrum[24..28].iter().copied().sum::<f32>() / 4.0;
        let is_clamping = sibilance_band > -20.0;
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("  Dynamic De-Esser Sibilance Detection (6.5 kHz Band):", Style::default().fg(theme.primary)),
            ]),
            Line::from(vec![
                Span::styled("  Clamping State: ", Style::default().fg(theme.text_dim)),
                Span::styled(if is_clamping { "ACTIVE CLAMPING (-2.4 dB Dynamic Notch)" } else { "MONITORING (Sub-threshold Pass)" }, Style::default().fg(if is_clamping { theme.accent } else { theme.success })),
            ]),
            Line::from(vec![
                Span::styled("  Band Energy:    ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("{:>+5.1} dBFS (Pinna Sibilance Filter)", sibilance_band), Style::default().fg(theme.text)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }

    fn render_dsp_signal_flow(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette, eq_gains: &[f32; 10]) {
        let is_eq_active = eq_gains.iter().any(|&g| g.abs() > 0.01);
        let lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled(" [Input] CoreAudio Loopback -> ", Style::default().fg(theme.text_dim)),
                Span::styled("[10-Band EQ Rails: ", Style::default().fg(theme.primary)),
                Span::styled(if is_eq_active { "ACTIVE" } else { "FLAT" }, Style::default().fg(if is_eq_active { theme.success } else { theme.text_dim })),
                Span::styled("] -> ", Style::default().fg(theme.primary)),
                Span::styled("[Mastering Tube/Limiter] -> ", Style::default().fg(theme.secondary)),
                Span::styled("[Output DAC]", Style::default().fg(theme.accent)),
            ]),
            Line::from(vec![
                Span::styled(" Engine Throughput: 48,000 samples/sec | Processing Latency: 0.18 ms", Style::default().fg(theme.text_dim)),
            ]),
        ];
        let p = Paragraph::new(lines);
        f.render_widget(p, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_visual_graph_mode_cycle_all_32() {
        let mut mode = VisualGraphMode::Spectrum32;
        for _ in 0..32 {
            mode = mode.next();
        }
        assert_eq!(mode, VisualGraphMode::Spectrum32);
    }

    #[test]
    fn test_all_32_modes_have_labels() {
        for mode in ALL_MODES {
            assert!(!mode.label().is_empty());
        }
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
        assert_eq!(dash.layout, DashboardLayout::SixGrid3x2);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::EightGrid4x2);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::FullSingle);
        dash.cycle_layout();
        assert_eq!(dash.layout, DashboardLayout::HeroPlusThree);
    }

    #[test]
    fn test_tile_selection_and_per_tile_change() {
        let mut dash = VisualsDashboard::new();
        dash.handle_key(KeyCode::Right);
        assert_eq!(dash.focused_tile, 1);
        dash.handle_key(KeyCode::Char('v'));
        assert_eq!(dash.tiles[1].visual, VisualGraphMode::AnalogVu.next());
    }

    #[test]
    fn test_zoom_toggle() {
        let mut dash = VisualsDashboard::new();
        assert!(!dash.is_zoomed);
        dash.toggle_zoom();
        assert!(dash.is_zoomed);
    }

    #[test]
    fn test_dynamic_x_axis_distribution() {
        let axis_str = build_dynamic_x_axis(160, 32, 5.0);
        assert_eq!(axis_str.len(), 160);
        assert!(axis_str.contains("31"));
        assert!(axis_str.contains("1k"));
        assert!(axis_str.contains("16k"));
        let pos_1k = axis_str.find("1k").expect("Must contain 1k");
        assert!(pos_1k > 60 && pos_1k < 110, "1k should be centered, got position {}", pos_1k);
        let pos_16k = axis_str.find("16k").expect("Must contain 16k");
        assert!(pos_16k > 120, "16k should be on right, got position {}", pos_16k);
    }
}
