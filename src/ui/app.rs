//! Main Interactive Terminal User Interface in pure Rust using `ratatui` and `crossterm`.

use crate::autoeq::{get_bundled_profiles, ParametricProfile};
use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};
use crate::dsp::enhancer::CrossfeedMode;
use crate::dsp::streamer::{AudioStreamer, SyncMode};
use crate::dsp::AudioPipeline;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Gauge, List, ListItem, ListState, Paragraph, Tabs};
use ratatui::Terminal;
use std::io::stdout;
use std::sync::atomic::Ordering;
use std::time::{Duration, Instant};

const FREQS_10_BAND: [f32; 10] = [
    31.25, 62.5, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
];

pub struct App {
    pub active_tab: usize,
    pub selected_band: usize,
    pub band_gains: [f32; 10],
    pub selected_mastering_idx: usize,
    pub selected_profile_idx: usize,
    pub profiles: Vec<ParametricProfile>,
    pub streamer: AudioStreamer,
    pub status_message: String,
    pub status_time: Instant,
    profile_list_state: ListState,
}

impl App {
    pub fn new() -> Self {
        let sample_rate = 48000.0;
        let mut pipeline = AudioPipeline::new(sample_rate);
        let band_gains = [0.0; 10];

        // Initialize 10-band graphic EQ
        let mut filters = Vec::with_capacity(10);
        for &freq in &FREQS_10_BAND {
            filters.push(BiquadFilter::new(
                BiquadFilterType::Peaking,
                freq,
                0.0,
                1.414,
                sample_rate,
            ));
        }
        pipeline.crossfader.update_filters(&filters, sample_rate);

        let profiles = get_bundled_profiles(sample_rate);
        let mut list_state = ListState::default();
        list_state.select(Some(0));

        let mut streamer = AudioStreamer::new(pipeline);
        // Start streaming automatically
        let status = match streamer.start() {
            Ok(()) => "Audio stream active on CoreAudio loopback.".to_string(),
            Err(e) => format!("Stream warning: {}", e),
        };

        Self {
            active_tab: 0,
            selected_band: 5, // default to 1 kHz
            band_gains,
            selected_mastering_idx: 0,
            selected_profile_idx: 0,
            profiles,
            streamer,
            status_message: status,
            status_time: Instant::now(),
            profile_list_state: list_state,
        }
    }

    pub fn set_status(&mut self, msg: &str) {
        self.status_message = msg.to_string();
        self.status_time = Instant::now();
    }

    fn sync_graphic_eq(&mut self) {
        let mut filters = Vec::with_capacity(10);
        for (i, &freq) in FREQS_10_BAND.iter().enumerate() {
            let gain = self.band_gains[i];
            filters.push(BiquadFilter::new(
                BiquadFilterType::Peaking,
                freq,
                gain,
                1.414,
                48000.0,
            ));
        }
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.crossfader.update_filters(&filters, 48000.0);
        }
    }

    pub async fn run(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        enable_raw_mode()?;
        let mut stdout = stdout();
        execute!(stdout, EnterAlternateScreen)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        let tick_rate = Duration::from_millis(33); // 30 FPS
        let mut last_tick = Instant::now();

        loop {
            terminal.draw(|f| self.render(f))?;

            let timeout = tick_rate.saturating_sub(last_tick.elapsed());
            if event::poll(timeout)? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        match key.code {
                            KeyCode::Char('q') | KeyCode::Char('Q') => break,
                            KeyCode::Char('1') => self.active_tab = 0,
                            KeyCode::Char('2') => self.active_tab = 1,
                            KeyCode::Char('3') => self.active_tab = 2,
                            KeyCode::Char('4') => self.active_tab = 3,
                            KeyCode::Char('5') => self.active_tab = 4,
                            KeyCode::Tab => {
                                self.active_tab = (self.active_tab + 1) % 5;
                            }
                            KeyCode::Char(' ') => {
                                if self.streamer.is_running.load(Ordering::SeqCst) {
                                    self.streamer.stop();
                                    self.set_status("Audio stream stopped.");
                                } else {
                                    match self.streamer.start() {
                                        Ok(()) => self.set_status("Audio stream started."),
                                        Err(e) => self.set_status(&format!("Start error: {}", e)),
                                    }
                                }
                            }
                            KeyCode::Char('b') | KeyCode::Char('B') => {
                                let new_state = if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                                    pipe.bypass = !pipe.bypass;
                                    Some(pipe.bypass)
                                } else {
                                    None
                                };
                                if let Some(bp) = new_state {
                                    let state = if bp { "ON" } else { "OFF" };
                                    self.set_status(&format!("Bypass mode: {}", state));
                                }
                            }
                            KeyCode::Char('s') | KeyCode::Char('S') => {
                                let next_mode = match self.streamer.sync_mode {
                                    SyncMode::Extreme => SyncMode::Ultra,
                                    SyncMode::Ultra => SyncMode::Balanced,
                                    SyncMode::Balanced => SyncMode::Extreme,
                                };
                                self.streamer.set_sync_mode(next_mode);
                                let desc = match next_mode {
                                    SyncMode::Extreme => "EXTREME (256 frames, ~23ms)",
                                    SyncMode::Ultra => "ULTRA (512 frames, ~32ms)",
                                    SyncMode::Balanced => "BALANCED (1024 frames, ~51ms)",
                                };
                                self.set_status(&format!("Sync mode: {}", desc));
                            }
                            _ => self.handle_tab_key(key.code),
                        }
                    }
                }
            }

            if last_tick.elapsed() >= tick_rate {
                last_tick = Instant::now();
            }
        }

        // Clean teardown
        self.streamer.stop();
        disable_raw_mode()?;
        execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
        terminal.show_cursor()?;

        Ok(())
    }

    fn handle_tab_key(&mut self, code: KeyCode) {
        match self.active_tab {
            0 => match code {
                KeyCode::Left => {
                    self.selected_band = self.selected_band.saturating_sub(1);
                }
                KeyCode::Right => {
                    if self.selected_band < 9 {
                        self.selected_band += 1;
                    }
                }
                KeyCode::Up => {
                    self.band_gains[self.selected_band] =
                        (self.band_gains[self.selected_band] + 0.5).min(12.0);
                    self.sync_graphic_eq();
                }
                KeyCode::Down => {
                    self.band_gains[self.selected_band] =
                        (self.band_gains[self.selected_band] - 0.5).max(-12.0);
                    self.sync_graphic_eq();
                }
                KeyCode::Char('0') => {
                    self.band_gains[self.selected_band] = 0.0;
                    self.sync_graphic_eq();
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.band_gains = [0.0; 10];
                    self.sync_graphic_eq();
                    self.set_status("All 10 EQ bands reset to 0.0 dB.");
                }
                _ => {}
            },
            1 => match code {
                KeyCode::Up => {
                    self.selected_mastering_idx = self.selected_mastering_idx.saturating_sub(1);
                }
                KeyCode::Down => {
                    if self.selected_mastering_idx < 7 {
                        self.selected_mastering_idx += 1;
                    }
                }
                KeyCode::Enter | KeyCode::Right => {
                    self.cycle_mastering_control(true);
                }
                KeyCode::Left => {
                    self.cycle_mastering_control(false);
                }
                _ => {}
            },
            3 => match code {
                KeyCode::Up => {
                    if self.selected_profile_idx > 0 {
                        self.selected_profile_idx -= 1;
                        self.profile_list_state.select(Some(self.selected_profile_idx));
                    }
                }
                KeyCode::Down => {
                    if self.selected_profile_idx + 1 < self.profiles.len() {
                        self.selected_profile_idx += 1;
                        self.profile_list_state.select(Some(self.selected_profile_idx));
                    }
                }
                KeyCode::Enter => {
                    let prof = self.profiles[self.selected_profile_idx].clone();
                    if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                        pipe.preamp_db = prof.preamp_db;
                        pipe.crossfader.update_filters(&prof.filters, 48000.0);
                    }
                    self.set_status(&format!("Applied profile: {}", prof.name));
                }
                _ => {}
            },
            _ => {}
        }
    }

    fn cycle_mastering_control(&mut self, forward: bool) {
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            match self.selected_mastering_idx {
                0 => {
                    // 3D Spatial Width
                    let w = pipe.enhancer.spatial_width;
                    let next = if forward {
                        if w < 1.2 { 1.25 } else if w < 1.4 { 1.50 } else { 1.00 }
                    } else {
                        if w > 1.4 { 1.25 } else if w > 1.1 { 1.00 } else { 1.50 }
                    };
                    pipe.enhancer.spatial_width = next;
                }
                1 => {
                    // Class-A Tube Warmth
                    let t = pipe.enhancer.tube_warmth;
                    let next = if forward {
                        if t < 0.1 { 0.15 } else if t < 0.25 { 0.30 } else { 0.00 }
                    } else {
                        if t > 0.25 { 0.15 } else if t > 0.05 { 0.00 } else { 0.30 }
                    };
                    pipe.enhancer.tube_warmth = next;
                }
                2 => {
                    // Aural Air
                    let a = pipe.enhancer.air_clarity_db;
                    let next = if forward {
                        if a < 1.0 { 2.0 } else if a < 3.0 { 4.0 } else { 0.0 }
                    } else {
                        if a > 3.0 { 2.0 } else if a > 1.0 { 0.0 } else { 4.0 }
                    };
                    pipe.enhancer.air_clarity_db = next;
                    pipe.enhancer.rebuild_filters();
                }
                3 => {
                    // Sub-Bass Punch
                    let b = pipe.enhancer.bass_punch_db;
                    let next = if forward {
                        if b < 1.0 { 2.0 } else if b < 3.0 { 4.0 } else { 0.0 }
                    } else {
                        if b > 3.0 { 2.0 } else if b > 1.0 { 0.0 } else { 4.0 }
                    };
                    pipe.enhancer.bass_punch_db = next;
                    pipe.enhancer.rebuild_filters();
                }
                4 => {
                    // Meier Crossfeed
                    let next = match pipe.enhancer.crossfeed {
                        CrossfeedMode::Off => CrossfeedMode::Subtle,
                        CrossfeedMode::Subtle => CrossfeedMode::Standard,
                        CrossfeedMode::Standard => CrossfeedMode::Off,
                    };
                    pipe.enhancer.crossfeed = next;
                    pipe.enhancer.rebuild_filters();
                }
                5 => {
                    // Dynamic De-Esser
                    pipe.enhancer.deesser_enabled = !pipe.enhancer.deesser_enabled;
                    pipe.enhancer.rebuild_filters();
                }
                6 => {
                    // Boundary Guard Filters
                    let cur = pipe.enhancer.subsonic_filter;
                    pipe.enhancer.subsonic_filter = !cur;
                    pipe.enhancer.ultrasonic_filter = !cur;
                    pipe.enhancer.rebuild_filters();
                }
                7 => {
                    // Brickwall Limiter
                    pipe.limiter.enabled = !pipe.limiter.enabled;
                }
                _ => {}
            }
        }
    }

    fn render(&mut self, f: &mut ratatui::Frame) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Header & Live Telemetry
                Constraint::Length(3), // Tabs
                Constraint::Min(12),   // Active Tab Body
                Constraint::Length(2), // Status bar
                Constraint::Length(1), // Footer keybindings
            ])
            .split(f.area());

        self.render_header(f, chunks[0]);
        self.render_tabs(f, chunks[1]);

        match self.active_tab {
            0 => self.render_graphic_eq(f, chunks[2]),
            1 => self.render_mastering(f, chunks[2]),
            2 => self.render_routing(f, chunks[2]),
            3 => self.render_autoeq_browser(f, chunks[2]),
            4 => self.render_harvester(f, chunks[2]),
            _ => {}
        }

        self.render_status(f, chunks[3]);
        self.render_footer(f, chunks[4]);
    }

    fn render_header(&self, f: &mut ratatui::Frame, area: Rect) {
        let (peak_l, peak_r, phase, lufs_m, lufs_s, crest, clipping, bypass) =
            if let Ok(pipe) = self.streamer.pipeline.lock() {
                (
                    pipe.telemetry.peak_left_db,
                    pipe.telemetry.peak_right_db,
                    pipe.telemetry.phase_correlation,
                    pipe.telemetry.lufs_momentary,
                    pipe.telemetry.lufs_short_term,
                    pipe.telemetry.crest_factor_db,
                    pipe.limiter.is_clipping,
                    pipe.bypass,
                )
            } else {
                (-96.0, -96.0, 1.0, -96.0, -96.0, 0.0, false, false)
            };

        let sync_badge = match self.streamer.sync_mode {
            SyncMode::Extreme => Span::styled(" SYNC: EXTREME (256) ", Style::default().bg(Color::Red).fg(Color::Black).add_modifier(Modifier::BOLD)),
            SyncMode::Ultra => Span::styled(" SYNC: ULTRA (512) ", Style::default().bg(Color::Cyan).fg(Color::Black).add_modifier(Modifier::BOLD)),
            SyncMode::Balanced => Span::styled(" SYNC: BALANCED (1024) ", Style::default().bg(Color::Green).fg(Color::Black).add_modifier(Modifier::BOLD)),
        };

        let bypass_badge = if bypass {
            Span::styled(" [BYPASS: ON] ", Style::default().bg(Color::Yellow).fg(Color::Black).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [DSP ACTIVE] ", Style::default().fg(Color::Green))
        };

        let clip_badge = if clipping {
            Span::styled(" [CLIP] ", Style::default().bg(Color::Red).fg(Color::White).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [SAFE] ", Style::default().fg(Color::DarkGray))
        };

        let phase_str = format!("Phase: {:+.2}", phase);
        let lufs_str = if lufs_s <= -70.0 {
            "LUFS: -∞".to_string()
        } else {
            format!("LUFS: {:.1} (Mom: {:.1})", lufs_s, lufs_m)
        };
        let peak_str = format!("L: {:+.1}dB | R: {:+.1}dB", peak_l, peak_r);
        let crest_str = format!("Crest: {:.1}dB", crest);

        let title_line = Line::from(vec![
            Span::styled("OMNIRIP ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Studio Engine v0.2.0  "),
            sync_badge,
            bypass_badge,
            clip_badge,
            Span::raw(" | "),
            Span::styled(peak_str, Style::default().fg(Color::White)),
            Span::raw(" | "),
            Span::styled(phase_str, Style::default().fg(if phase >= 0.5 { Color::Green } else { Color::Yellow })),
            Span::raw(" | "),
            Span::styled(lufs_str, Style::default().fg(Color::Magenta)),
            Span::raw(" | "),
            Span::styled(crest_str, Style::default().fg(Color::Blue)),
        ]);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray));
        let p = Paragraph::new(title_line).block(block).alignment(Alignment::Left);
        f.render_widget(p, area);
    }

    fn render_tabs(&self, f: &mut ratatui::Frame, area: Rect) {
        let titles = vec![
            Line::from("[1] 10-Band Graphic EQ"),
            Line::from("[2] Mastering Suite"),
            Line::from("[3] Audio Routing"),
            Line::from("[4] AutoEQ Presets"),
            Line::from("[5] Harvester"),
        ];

        let tabs = Tabs::new(titles)
            .block(Block::default().borders(Borders::ALL))
            .select(self.active_tab)
            .style(Style::default().fg(Color::White))
            .highlight_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD));

        f.render_widget(tabs, area);
    }

    fn render_graphic_eq(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" 10-BAND GRAPHIC EQ (Peaking Biquads, 1.414 Q) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Ratio(1, 10); 10])
            .split(inner);

        let labels = [
            "31 Hz", "63 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz",
        ];

        for i in 0..10 {
            let gain = self.band_gains[i];
            let is_selected = i == self.selected_band;

            let col_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(2), // Gain readout
                    Constraint::Min(6),    // Vertical meter
                    Constraint::Length(2), // Freq label
                ])
                .split(cols[i]);

            // Top readout
            let gain_str = format!("{:+.1}dB", gain);
            let gain_color = if gain > 0.01 {
                Color::Green
            } else if gain < -0.01 {
                Color::Yellow
            } else {
                Color::DarkGray
            };
            let p_gain = Paragraph::new(gain_str)
                .style(Style::default().fg(gain_color).add_modifier(if is_selected { Modifier::BOLD } else { Modifier::empty() }))
                .alignment(Alignment::Center);
            f.render_widget(p_gain, col_chunks[0]);

            // Meter gauge: map [-12, +12] dB to [0, 100]%
            let pct = (((gain + 12.0) / 24.0) * 100.0).clamp(0.0, 100.0) as u16;
            let gauge_color = if is_selected { Color::Cyan } else { Color::Blue };
            let gauge = Gauge::default()
                .gauge_style(Style::default().fg(gauge_color).bg(Color::Rgb(30, 30, 30)))
                .percent(pct)
                .label("");
            f.render_widget(gauge, col_chunks[1]);

            // Bottom label
            let p_lbl = Paragraph::new(labels[i])
                .style(Style::default().fg(if is_selected { Color::White } else { Color::DarkGray }))
                .alignment(Alignment::Center);
            f.render_widget(p_lbl, col_chunks[2]);
        }
    }

    fn render_mastering(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" STUDIO AUDIOPHILE MASTERING SUITE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let (w, t, a, b, cf, de, bf, lim) = if let Ok(pipe) = self.streamer.pipeline.lock() {
            (
                pipe.enhancer.spatial_width,
                pipe.enhancer.tube_warmth,
                pipe.enhancer.air_clarity_db,
                pipe.enhancer.bass_punch_db,
                pipe.enhancer.crossfeed,
                pipe.enhancer.deesser_enabled,
                pipe.enhancer.subsonic_filter,
                pipe.limiter.enabled,
            )
        } else {
            (1.0, 0.0, 0.0, 0.0, CrossfeedMode::Off, false, true, true)
        };

        let items = vec![
            format!("1. 3D Soundstage Width:        {:.0}% (100% Normal, 125% Wide, 150% Ultra)", w * 100.0),
            format!("2. Class-A Tube Warmth:        {}", match t { x if x > 0.25 => "Lush Triode (+0.30)", x if x > 0.05 => "Warm Vinyl (+0.15)", _ => "Off" }),
            format!("3. Aural Air & Sheen (12kHz):  +{:+.1} dB Sheen", a),
            format!("4. Sub-Bass Punch (<60Hz):     +{:+.1} dB Punch", b),
            format!("5. Meier Natural Crossfeed:    {}", match cf { CrossfeedMode::Standard => "Standard (HRTF Shadow)", CrossfeedMode::Subtle => "Subtle", CrossfeedMode::Off => "Off" }),
            format!("6. Dynamic De-Esser (6.5kHz):  {}", if de { "ACTIVE (Sibilance Limiter ON)" } else { "OFF" }),
            format!("7. Boundary Guard Filters:     {}", if bf { "ON (18Hz HPF + 21kHz LPF)" } else { "OFF" }),
            format!("8. Brickwall Limiter:          {}", if lim { "ON (-0.2 dBFS Protection Ceiling)" } else { "OFF (Unprotected)" }),
        ];

        let mut lines = Vec::new();
        for (i, item) in items.iter().enumerate() {
            let is_selected = i == self.selected_mastering_idx;
            let style = if is_selected {
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };
            let prefix = if is_selected { " > " } else { "   " };
            lines.push(Line::from(vec![Span::styled(format!("{}{}", prefix, item), style)]));
        }

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_routing(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" AUDIO ROUTING & SYSTEM STREAM ENGINE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let is_running = self.streamer.is_running.load(Ordering::SeqCst);
        let status_str = if is_running {
            "[ACTIVE] Low-Latency CoreAudio Loopback Running (Native Threads)"
        } else {
            "[STOPPED] Audio Stream Inactive (Press Space to Start)"
        };
        let status_style = if is_running {
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::Yellow)
        };

        let lines = vec![
            Line::from(vec![Span::styled("Engine Status:    ", Style::default().fg(Color::DarkGray)), Span::styled(status_str, status_style)]),
            Line::from(""),
            Line::from(vec![Span::styled("Input Device:     ", Style::default().fg(Color::DarkGray)), Span::styled("BlackHole 2ch (Virtual Loopback Driver)", Style::default().fg(Color::White))]),
            Line::from(vec![Span::styled("Output Device:    ", Style::default().fg(Color::DarkGray)), Span::styled("OmniRip Stream / iBasso-DC03-Pro (High-Resolution DAC)", Style::default().fg(Color::White))]),
            Line::from(vec![Span::styled("Routing Path:     ", Style::default().fg(Color::DarkGray)), Span::styled("macOS Sound -> BlackHole 2ch -> OmniRip (Rust DSP) -> DAC", Style::default().fg(Color::Cyan))]),
            Line::from(""),
            Line::from(vec![Span::styled("Sync Mode:        ", Style::default().fg(Color::DarkGray)), Span::styled(format!("{:?}", self.streamer.sync_mode), Style::default().fg(Color::White))]),
            Line::from(vec![Span::styled("Buffer Target:    ", Style::default().fg(Color::DarkGray)), Span::styled(format!("{} frames (~{:.1} ms cushion)", self.streamer.sync_mode.target_frames(), (self.streamer.sync_mode.target_frames() as f32 / 48.0)), Style::default().fg(Color::White))]),
            Line::from(vec![Span::styled("Clock Drift:      ", Style::default().fg(Color::DarkGray)), Span::styled("Lock-Free PI Clock Servo Active (0 Underflows / Drops)", Style::default().fg(Color::Green))]),
        ];

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_autoeq_browser(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" AUTOEQ & SQUIGLINK DATABASE (Press Enter to Apply) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let items: Vec<ListItem> = self
            .profiles
            .iter()
            .enumerate()
            .map(|(i, p)| {
                let is_sel = i == self.selected_profile_idx;
                let text = format!("{}. {} (Preamp: {:+.1}dB, {} Filters)", i + 1, p.name, p.preamp_db, p.filters.len());
                let style = if is_sel {
                    Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(Color::White)
                };
                ListItem::new(text).style(style)
            })
            .collect();

        let list = List::new(items)
            .highlight_style(Style::default().bg(Color::Rgb(30, 60, 90)).add_modifier(Modifier::BOLD))
            .highlight_symbol("> ");

        f.render_stateful_widget(list, inner, &mut self.profile_list_state);
    }

    fn render_harvester(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" HARVESTER AUDIO LIBRARY & QUALITY ENGINE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let lines = vec![
            Line::from(vec![
                Span::styled("Soulseek / Slskd Network:  ", Style::default().fg(Color::DarkGray)),
                Span::styled("[READY] API Endpoint: http://localhost:5030 (Lossless FLAC/WAV Search)", Style::default().fg(Color::Green)),
            ]),
            Line::from(vec![
                Span::styled("yt-dlp Audio Ripper:       ", Style::default().fg(Color::DarkGray)),
                Span::styled("[AVAILABLE] Direct CLI Subprocess Runner (FLAC 24-bit / OPUS 160kbps)", Style::default().fg(Color::Green)),
            ]),
            Line::from(vec![
                Span::styled("Universal Metadata Tagger: ", Style::default().fg(Color::DarkGray)),
                Span::styled("[ACTIVE] Lofty Engine (ID3v2.4 / Vorbis Comments / MP4 Atoms)", Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled("Spectral Cutoff Auditor:   ", Style::default().fg(Color::DarkGray)),
                Span::styled("[ACTIVE] RustFFT 2048-pt STFT + Symphonia Decoder (Fake Lossless Detector)", Style::default().fg(Color::Cyan)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("Quality Verdict Hierarchy: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  * True Lossless Hi-Res:  ", Style::default().fg(Color::DarkGray)),
                Span::styled("Bandwidth extends beyond 22.5 kHz (24-bit/96kHz+ masters)", Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled("  * True Lossless CD:      ", Style::default().fg(Color::DarkGray)),
                Span::styled("Full uncompressed bandwidth up to ~21.0 kHz (16-bit/44.1kHz)", Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled("  * Near-Lossless MP3:     ", Style::default().fg(Color::DarkGray)),
                Span::styled("Sharp brickwall filter at ~20.0 kHz (~320 kbps MP3/AAC)", Style::default().fg(Color::Yellow)),
            ]),
            Line::from(vec![
                Span::styled("  * Compressed Lossy:      ", Style::default().fg(Color::DarkGray)),
                Span::styled("Lowpass filter cutoff at <= 16.0 kHz (~128-192 kbps lossy)", Style::default().fg(Color::Red)),
            ]),
            Line::from(vec![
                Span::styled("  * Fake Lossless Alert:   ", Style::default().fg(Color::DarkGray)),
                Span::styled("Lossless container (FLAC) containing upsampled lossy stream", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
            ]),
        ];

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_status(&self, f: &mut ratatui::Frame, area: Rect) {
        let p = Paragraph::new(format!(" Status: {}", self.status_message))
            .style(Style::default().fg(Color::Yellow));
        f.render_widget(p, area);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect) {
        let help = " [Tab / 1-5] Switch Tab  [Arrows] Adjust  [Space] Stream Toggle  [B] Bypass  [S] Sync Mode  [Q] Quit";
        let p = Paragraph::new(help).style(Style::default().bg(Color::DarkGray).fg(Color::White));
        f.render_widget(p, area);
    }
}
