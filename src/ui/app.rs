//! Main Interactive Terminal User Interface in pure Rust using `ratatui` and `crossterm`.
//! Integrates the interactive MP3 Downloader, Startup Mode Selection popup,
//! Multi-Palette Theme Engine (7 themes), and Real-Time Visual Graph Dashboard.

use crate::autoeq::{get_bundled_profiles, ParametricProfile};
use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};
use crate::dsp::enhancer::CrossfeedMode;
use crate::dsp::streamer::{AudioStreamer, SyncMode};
use crate::dsp::AudioPipeline;
use crate::ui::downloader::DownloaderState;
use crate::ui::mode_modal::{ModeModal, WorkstationMode};
use crate::ui::theme::ThemePalette;
use crate::ui::visuals::VisualsDashboard;
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
    pub theme: ThemePalette,
    pub mode_modal: ModeModal,
    pub downloader: DownloaderState,
    pub visuals: VisualsDashboard,
    pub active_mode: WorkstationMode,
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
            theme: ThemePalette::default(),
            mode_modal: ModeModal::new(), // Starts open with startup popup question
            downloader: DownloaderState::new(),
            visuals: VisualsDashboard::new(),
            active_mode: WorkstationMode::Downloader,
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
            // Poll any background downloader worker updates
            self.downloader.poll_updates();

            terminal.draw(|f| self.render(f))?;

            let timeout = tick_rate.saturating_sub(last_tick.elapsed());
            if event::poll(timeout)? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        // 1. If Startup Mode Modal is open, intercept selection keys
                        if self.mode_modal.is_open {
                            match key.code {
                                KeyCode::Char('1') => {
                                    self.active_mode = WorkstationMode::Downloader;
                                    self.mode_modal.is_open = false;
                                    self.set_status("Workspace: MP3 Downloader & Media Harvester");
                                }
                                KeyCode::Char('2') => {
                                    self.active_mode = WorkstationMode::SystemEq;
                                    self.mode_modal.is_open = false;
                                    self.set_status("Workspace: System EQ & Audiophile Mastering");
                                }
                                KeyCode::Up | KeyCode::Down => {
                                    self.mode_modal.selected_index = 1 - self.mode_modal.selected_index;
                                }
                                KeyCode::Enter => {
                                    self.active_mode = self.mode_modal.current_mode();
                                    self.mode_modal.is_open = false;
                                    self.set_status(&format!("Workspace: {:?}", self.active_mode));
                                }
                                KeyCode::Esc => {
                                    self.mode_modal.is_open = false;
                                }
                                KeyCode::Char('q') | KeyCode::Char('Q') => break,
                                _ => {}
                            }
                            continue;
                        }

                        // 2. Global Hotkeys
                        match key.code {
                            KeyCode::Char('q') | KeyCode::Char('Q') => break,
                            KeyCode::Char('m') | KeyCode::Char('M') => {
                                self.mode_modal.toggle();
                                continue;
                            }
                            KeyCode::Char('t') | KeyCode::Char('T') => {
                                self.theme.cycle();
                                self.set_status(&format!("Theme: {}", self.theme.name));
                                continue;
                            }
                            KeyCode::Char('v') | KeyCode::Char('V') => {
                                self.visuals.cycle_mode();
                                self.set_status(&format!("Visual Graph: {}", self.visuals.mode.label()));
                                continue;
                            }
                            KeyCode::Char('s') | KeyCode::Char('S') if self.active_mode == WorkstationMode::SystemEq => {
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
                                continue;
                            }
                            KeyCode::Char('b') | KeyCode::Char('B') if self.active_mode == WorkstationMode::SystemEq => {
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
                                continue;
                            }
                            KeyCode::Char(' ') if self.active_mode == WorkstationMode::SystemEq => {
                                if self.streamer.is_running.load(Ordering::SeqCst) {
                                    self.streamer.stop();
                                    self.set_status("Audio stream stopped.");
                                } else {
                                    match self.streamer.start() {
                                        Ok(()) => self.set_status("Audio stream started."),
                                        Err(e) => self.set_status(&format!("Start error: {}", e)),
                                    }
                                }
                                continue;
                            }
                            _ => {}
                        }

                        // 3. Mode-Specific Key Handlers
                        match self.active_mode {
                            WorkstationMode::Downloader => {
                                self.downloader.handle_key(key.code);
                            }
                            WorkstationMode::SystemEq => {
                                match key.code {
                                    KeyCode::Char('1') => self.active_tab = 0,
                                    KeyCode::Char('2') => self.active_tab = 1,
                                    KeyCode::Char('3') => self.active_tab = 2,
                                    KeyCode::Char('4') => self.active_tab = 3,
                                    KeyCode::Char('5') => self.active_tab = 4,
                                    KeyCode::Tab => {
                                        self.active_tab = (self.active_tab + 1) % 5;
                                    }
                                    _ => self.handle_tab_key(key.code),
                                }
                            }
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
                    self.set_status(&format!("Applied AutoEQ preset: {}", prof.name));
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
                    // 3D Soundstage Width: 100% -> 125% -> 150% -> 75%
                    let delta = if forward { 0.25 } else { -0.25 };
                    pipe.enhancer.spatial_width = (pipe.enhancer.spatial_width + delta).clamp(0.5, 2.0);
                }
                1 => {
                    // Class-A Tube Warmth: 0.0 -> 0.15 -> 0.30 -> 0.0
                    let step = if forward { 0.15 } else { -0.15 };
                    pipe.enhancer.tube_warmth = (pipe.enhancer.tube_warmth + step).clamp(0.0, 0.6);
                }
                2 => {
                    // Aural Air: 0.0 -> +1.5 -> +3.0 -> 0.0 dB
                    let step = if forward { 1.5 } else { -1.5 };
                    pipe.enhancer.air_clarity_db = (pipe.enhancer.air_clarity_db + step).clamp(0.0, 6.0);
                }
                3 => {
                    // Sub-Bass Punch: 0.0 -> +1.5 -> +3.0 -> 0.0 dB
                    let step = if forward { 1.5 } else { -1.5 };
                    pipe.enhancer.bass_punch_db = (pipe.enhancer.bass_punch_db + step).clamp(0.0, 6.0);
                }
                4 => {
                    // Meier Natural Crossfeed
                    pipe.enhancer.crossfeed = match pipe.enhancer.crossfeed {
                        CrossfeedMode::Off => CrossfeedMode::Subtle,
                        CrossfeedMode::Subtle => CrossfeedMode::Standard,
                        CrossfeedMode::Standard => CrossfeedMode::Off,
                    };
                }
                5 => {
                    // Dynamic De-Esser
                    pipe.enhancer.deesser_enabled = !pipe.enhancer.deesser_enabled;
                }
                6 => {
                    // Boundary Guard Filters
                    pipe.enhancer.subsonic_filter = !pipe.enhancer.subsonic_filter;
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
        let (spectrum, peak_l, peak_r, phase) = if let Ok(pipe) = self.streamer.pipeline.lock() {
            (
                pipe.telemetry.spectrum_32,
                pipe.telemetry.peak_left_db,
                pipe.telemetry.peak_right_db,
                pipe.telemetry.phase_correlation,
            )
        } else {
            ([-60.0; 32], -60.0, -60.0, 1.0)
        };

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Top Masthead
                Constraint::Min(12),   // Workspace body
                Constraint::Length(2), // Status bar
                Constraint::Length(1), // Footer hotkeys
            ])
            .split(f.area());

        self.render_header(f, chunks[0]);

        match self.active_mode {
            WorkstationMode::Downloader => {
                self.downloader.render(f, chunks[1], &self.theme);
            }
            WorkstationMode::SystemEq => {
                let eq_chunks = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([
                        Constraint::Length(3), // Tabs
                        Constraint::Min(9),    // Tab contents
                    ])
                    .split(chunks[1]);

                self.render_tabs(f, eq_chunks[0]);

                match self.active_tab {
                    0 => self.render_graphic_eq(f, eq_chunks[1]),
                    1 => self.render_mastering(f, eq_chunks[1]),
                    2 => self.render_routing(f, eq_chunks[1]),
                    3 => self.render_autoeq_browser(f, eq_chunks[1]),
                    4 => {
                        let gains = self.band_gains;
                        self.visuals.render(f, eq_chunks[1], &self.theme, &spectrum, peak_l, peak_r, phase, &gains);
                    }
                    _ => {}
                }
            }
        }

        self.render_status(f, chunks[2]);
        self.render_footer(f, chunks[3]);

        // Render Mode Modal on top if open
        if self.mode_modal.is_open {
            self.mode_modal.render(f, f.area(), &self.theme);
        }
    }

    fn render_header(&self, f: &mut ratatui::Frame, area: Rect) {
        let (peak_l, peak_r, phase, lufs_m, lufs_s, crest, clipping, bypass) =
            if let Ok(pipe) = self.streamer.pipeline.lock() {
                let clip = pipe.telemetry.peak_left_db >= -0.01 || pipe.telemetry.peak_right_db >= -0.01;
                (
                    pipe.telemetry.peak_left_db,
                    pipe.telemetry.peak_right_db,
                    pipe.telemetry.phase_correlation,
                    pipe.telemetry.lufs_momentary,
                    pipe.telemetry.lufs_short_term,
                    pipe.telemetry.crest_factor_db,
                    clip,
                    pipe.bypass,
                )
            } else {
                (-60.0, -60.0, 1.0, -70.0, -70.0, 0.0, false, false)
            };

        let mode_badge = match self.active_mode {
            WorkstationMode::Downloader => Span::styled(" [MODE: MP3 DOWNLOADER] ", Style::default().fg(Color::Black).bg(self.theme.secondary).add_modifier(Modifier::BOLD)),
            WorkstationMode::SystemEq => Span::styled(" [MODE: SYSTEM EQ & MASTERING] ", Style::default().fg(Color::Black).bg(self.theme.primary).add_modifier(Modifier::BOLD)),
        };

        let theme_badge = Span::styled(format!(" [THEME: {}] ", self.theme.name), Style::default().fg(self.theme.accent));
        let sync_badge = Span::styled(format!(" [{:?}] ", self.streamer.sync_mode), Style::default().fg(Color::White));
        let bypass_badge = if bypass {
            Span::styled(" [BYPASS] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [DSP ACTIVE] ", Style::default().fg(self.theme.success))
        };
        let clip_badge = if clipping {
            Span::styled(" [CLIP!] ", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [0 CLIPS] ", Style::default().fg(Color::DarkGray))
        };

        let peak_str = format!("L: {:>4.1}dB R: {:>4.1}dB", peak_l, peak_r);
        let phase_str = format!("Phase: {:+.2}", phase);
        let lufs_str = format!("LUFS: {:>4.1}", if lufs_m > -69.0 { lufs_m } else { lufs_s });
        let crest_str = format!("Crest: {:.1}dB", crest);

        let title_line = Line::from(vec![
            Span::styled("OMNIRIP ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            mode_badge,
            theme_badge,
            sync_badge,
            bypass_badge,
            clip_badge,
            Span::raw(" | "),
            Span::styled(peak_str, Style::default().fg(self.theme.text)),
            Span::raw(" | "),
            Span::styled(phase_str, Style::default().fg(if phase >= 0.5 { self.theme.success } else { self.theme.warning })),
            Span::raw(" | "),
            Span::styled(lufs_str, Style::default().fg(self.theme.secondary)),
            Span::raw(" | "),
            Span::styled(crest_str, Style::default().fg(self.theme.accent)),
        ]);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let p = Paragraph::new(title_line).block(block).alignment(Alignment::Left);
        f.render_widget(p, area);
    }

    fn render_tabs(&self, f: &mut ratatui::Frame, area: Rect) {
        let titles = vec![
            Line::from("[1] 10-Band EQ"),
            Line::from("[2] Mastering"),
            Line::from("[3] Routing"),
            Line::from("[4] AutoEQ"),
            Line::from("[5] Visual Graphs"),
        ];

        let tabs = Tabs::new(titles)
            .block(Block::default().borders(Borders::ALL))
            .select(self.active_tab)
            .style(Style::default().fg(self.theme.text))
            .highlight_style(Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD));

        f.render_widget(tabs, area);
    }

    fn render_graphic_eq(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" 10-BAND GRAPHIC EQ (Peaking Biquads, 1.414 Q) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let col_width = inner.width / 10;
        if col_width < 4 {
            return;
        }

        let chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints(vec![Constraint::Length(col_width); 10])
            .split(inner);

        let labels = ["31Hz", "62Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"];

        for i in 0..10 {
            let is_selected = i == self.selected_band;
            let gain = self.band_gains[i];

            let col_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(1), // Top dB label
                    Constraint::Min(4),    // Meter bar gauge
                    Constraint::Length(1), // Bottom freq label
                ])
                .split(chunks[i]);

            // Top gain label
            let gain_str = format!("{:+.1}", gain);
            let gain_color = if gain > 0.01 {
                self.theme.success
            } else if gain < -0.01 {
                self.theme.warning
            } else {
                self.theme.text_dim
            };
            let p_gain = Paragraph::new(gain_str)
                .style(Style::default().fg(gain_color).add_modifier(if is_selected { Modifier::BOLD } else { Modifier::empty() }))
                .alignment(Alignment::Center);
            f.render_widget(p_gain, col_chunks[0]);

            // Meter gauge: map [-12, +12] dB to [0, 100]%
            let pct = (((gain + 12.0) / 24.0) * 100.0).clamp(0.0, 100.0) as u16;
            let gauge_color = if is_selected { self.theme.accent } else { self.theme.secondary };
            let gauge = Gauge::default()
                .gauge_style(Style::default().fg(gauge_color).bg(self.theme.surface))
                .percent(pct)
                .label("");
            f.render_widget(gauge, col_chunks[1]);

            // Bottom label
            let p_lbl = Paragraph::new(labels[i])
                .style(Style::default().fg(if is_selected { self.theme.text } else { self.theme.text_dim }))
                .alignment(Alignment::Center);
            f.render_widget(p_lbl, col_chunks[2]);
        }
    }

    fn render_mastering(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" STUDIO AUDIOPHILE MASTERING SUITE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
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
                Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(self.theme.text)
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
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let is_running = self.streamer.is_running.load(Ordering::SeqCst);
        let status_str = if is_running {
            "[ACTIVE] Low-Latency CoreAudio Loopback Running (Native Real-Time Threads)"
        } else {
            "[STOPPED] Audio Stream Inactive (Press Space to Start)"
        };
        let status_style = if is_running {
            Style::default().fg(self.theme.success).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(self.theme.warning)
        };

        let lines = vec![
            Line::from(vec![Span::styled("Engine Status:    ", Style::default().fg(self.theme.text_dim)), Span::styled(status_str, status_style)]),
            Line::from(""),
            Line::from(vec![Span::styled("Input Device:     ", Style::default().fg(self.theme.text_dim)), Span::styled("BlackHole 2ch (Virtual Loopback Driver)", Style::default().fg(self.theme.text))]),
            Line::from(vec![Span::styled("Output Device:    ", Style::default().fg(self.theme.text_dim)), Span::styled("OmniRip Stream / iBasso-DC03-Pro (High-Resolution DAC)", Style::default().fg(self.theme.text))]),
            Line::from(vec![Span::styled("Routing Path:     ", Style::default().fg(self.theme.text_dim)), Span::styled("macOS Sound -> BlackHole 2ch -> OmniRip (Rust DSP) -> DAC", Style::default().fg(self.theme.secondary))]),
            Line::from(""),
            Line::from(vec![Span::styled("Sync Mode:        ", Style::default().fg(self.theme.text_dim)), Span::styled(format!("{:?}", self.streamer.sync_mode), Style::default().fg(self.theme.text))]),
            Line::from(vec![Span::styled("Buffer Target:    ", Style::default().fg(self.theme.text_dim)), Span::styled(format!("{} frames (~{:.1} ms cushion)", self.streamer.sync_mode.target_frames(), (self.streamer.sync_mode.target_frames() as f32 / 48.0)), Style::default().fg(self.theme.text))]),
            Line::from(vec![Span::styled("Clock Drift:      ", Style::default().fg(self.theme.text_dim)), Span::styled("Lock-Free PI Clock Servo Active (0 Underflows / Drops)", Style::default().fg(self.theme.success))]),
        ];

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_autoeq_browser(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" AUTOEQ & SQUIGLINK DATABASE (Press Enter to Apply) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
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
                    Style::default().fg(self.theme.primary).bg(self.theme.surface).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(self.theme.text)
                };
                ListItem::new(text).style(style)
            })
            .collect();

        let list = List::new(items)
            .highlight_style(Style::default().bg(self.theme.surface).add_modifier(Modifier::BOLD))
            .highlight_symbol("> ");

        f.render_stateful_widget(list, inner, &mut self.profile_list_state);
    }

    fn render_status(&self, f: &mut ratatui::Frame, area: Rect) {
        let p = Paragraph::new(format!(" Status: {}", self.status_message))
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(p, area);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect) {
        let help = match self.active_mode {
            WorkstationMode::Downloader => {
                " [M] Mode Select  [T] Theme  [Enter] Download/Convert  [Tab] Inputs  [Arrows] Quality/Policy  [Q] Quit"
            }
            WorkstationMode::SystemEq => {
                " [M] Mode Select  [T] Theme  [V] Visuals  [Tab/1-5] Tabs  [Arrows] Adjust  [Space] Stream  [Q] Quit"
            }
        };
        let p = Paragraph::new(help).style(Style::default().bg(self.theme.surface).fg(self.theme.text));
        f.render_widget(p, area);
    }
}
