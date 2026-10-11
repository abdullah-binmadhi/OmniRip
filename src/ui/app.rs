//! Main Interactive Terminal User Interface in pure Rust using `ratatui` and `crossterm`.
//! Integrates the interactive MP3 Downloader, Startup Mode Selection popup,
//! Multi-Palette Theme Engine (7 themes), and Real-Time Visual Graph Dashboard.

use crate::autoeq::{get_bundled_profiles, parse_parametric_eq, ParametricProfile};
use crate::autoeq::storage::{download_raw_preset, load_all_user_presets, save_preset_to_disk, OmniRipPreset};
use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};
use crate::dsp::enhancer::CrossfeedMode;
use crate::dsp::streamer::{AudioStreamer, SyncMode};
use crate::dsp::AudioPipeline;
use crate::ui::downloader::DownloaderState;
use crate::ui::mode_modal::{ModeModal, WorkstationMode};
use crate::ui::nicotine_modal::{NicotineModal, NicotineModalAction};
use crate::ui::preset_modal::{render_preset_modal, ModalKeyAction, PresetModalState};
use crate::ui::theme::ThemePalette;
use crate::ui::visuals::VisualsDashboard;
use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use crossterm::execute;
use crossterm::terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Tabs};
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
    pub nicotine_modal: NicotineModal,
    pub preset_modal: PresetModalState,
    pub downloader: DownloaderState,
    pub visuals: VisualsDashboard,
    pub autoeq_visual_mode: usize,
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

        let mut profiles = get_bundled_profiles(sample_rate);
        for (_preset, prof) in load_all_user_presets(sample_rate) {
            profiles.push(prof);
        }
        let mut list_state = ListState::default();
        list_state.select(Some(0));

        let mut streamer = AudioStreamer::new(pipeline);
        // Start Pure Rust Audio Engine automatically on launch
        let status = match streamer.start() {
            Ok(()) => "Pure Rust Audio Engine ready on /tmp/omnirip_audio.sock & TCP 49152".to_string(),
            Err(e) => format!("Engine notice: {}", e),
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
            nicotine_modal: NicotineModal::new(),
            preset_modal: PresetModalState::Hidden,
            downloader: DownloaderState::new(),
            visuals: VisualsDashboard::new(),
            autoeq_visual_mode: 0,
            active_mode: WorkstationMode::Downloader,
        }
    }

    #[cfg(test)]
    pub fn new_test() -> Self {
        let sample_rate = 48000.0;
        let mut pipeline = AudioPipeline::new(sample_rate);
        let band_gains = [0.0; 10];

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

        let mut profiles = get_bundled_profiles(sample_rate);
        for (_preset, prof) in load_all_user_presets(sample_rate) {
            profiles.push(prof);
        }
        let mut list_state = ListState::default();
        list_state.select(Some(0));

        let streamer = AudioStreamer::new(pipeline);

        Self {
            active_tab: 0,
            selected_band: 5,
            band_gains,
            selected_mastering_idx: 0,
            selected_profile_idx: 0,
            profiles,
            streamer,
            status_message: "Test instance".to_string(),
            status_time: Instant::now(),
            profile_list_state: list_state,
            theme: ThemePalette::default(),
            mode_modal: ModeModal::new(),
            nicotine_modal: NicotineModal::new(),
            preset_modal: PresetModalState::Hidden,
            downloader: DownloaderState::new(),
            visuals: VisualsDashboard::new(),
            autoeq_visual_mode: 0,
            active_mode: WorkstationMode::Downloader,
        }
    }

    pub fn set_status(&mut self, msg: &str) {
        self.status_message = msg.to_string();
        self.status_time = Instant::now();
    }

    fn sync_graphic_eq(&mut self) {
        let sr = self.streamer.active_sample_rate();
        let mut filters = Vec::with_capacity(10);
        for (i, &freq) in FREQS_10_BAND.iter().enumerate() {
            let gain = self.band_gains[i];
            filters.push(BiquadFilter::new(
                BiquadFilterType::Peaking,
                freq,
                gain,
                1.414,
                sr,
            ));
        }
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.crossfader.update_filters(&filters, sr);
        }
    }

    /// Master Factory Reset: completely restores EQ, mastering suite, enhancer,
    /// volume/preamp, balance, AutoEQ profile, and sync cushion to pristine defaults.
    pub fn reset_all_settings(&mut self) {
        // 1. Reset 10-band graphic EQ
        self.band_gains = [0.0; 10];
        self.sync_graphic_eq();

        // 2. Reset Audio Pipeline mastering suite & enhancer
        let sr = self.streamer.active_sample_rate();
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.preamp_db = 0.0;
            pipe.volume_boost_db = 0.0;
            pipe.balance = 0.0;
            pipe.bypass = false;
            pipe.enhancer = crate::dsp::enhancer::AudiophileEnhancer::new(sr);
            pipe.limiter = crate::dsp::limiter::BrickwallLimiter::new(sr);
        }

        // 3. Reset AutoEQ profiles and selection
        self.selected_profile_idx = 0;
        self.profile_list_state.select(Some(0));

        // 4. Reset Sync cushion mode to default
        self.streamer.set_sync_mode(SyncMode::Balanced);
        self.streamer.force_resync();

        // 5. Heal CoreAudio routing & unpause
        self.streamer.heal_routing();

        self.set_status("MASTER FACTORY RESET: All settings restored & CoreAudio routing healed.");
    }

    /// Save current active settings across all tabs as a named preset.
    pub fn save_active_settings_as_preset(&mut self, name: &str) {
        let (preamp_db, volume_boost_db, balance, tube_warmth, spatial_width, limiter_ceiling_db) =
            if let Ok(pipe) = self.streamer.pipeline.lock() {
                (
                    pipe.preamp_db,
                    pipe.volume_boost_db,
                    pipe.balance,
                    pipe.enhancer.tube_warmth,
                    pipe.enhancer.spatial_width,
                    20.0 * pipe.limiter.threshold.log10(),
                )
            } else {
                (0.0, 0.0, 0.0, 0.0, 1.0, -0.2)
            };

        let preset = OmniRipPreset::from_active_state(
            name.to_string(),
            preamp_db,
            volume_boost_db,
            balance,
            tube_warmth,
            spatial_width,
            limiter_ceiling_db,
            self.band_gains,
            None,
        );

        match save_preset_to_disk(&preset) {
            Ok(path) => {
                let sr = self.streamer.active_sample_rate();
                let profile = preset.to_profile(sr);
                self.profiles.push(profile.clone());
                self.selected_profile_idx = self.profiles.len() - 1;
                self.profile_list_state.select(Some(self.selected_profile_idx));

                if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                    pipe.preamp_db = profile.preamp_db;
                    pipe.crossfader.update_filters(&profile.filters, sr);
                }

                let fname = path.file_name().and_then(|f| f.to_str()).unwrap_or("saved.json");
                self.set_status(&format!("Saved preset '{}' to ~/.config/omnirip/presets/{}", name, fname));
            }
            Err(e) => {
                self.set_status(&format!("Error saving preset: {}", e));
            }
        }
    }

    /// Import raw EqualizerAPO / Squiglink parametric EQ text directly into AutoEQ profiles.
    pub fn import_squiglink_preset(&mut self, name: &str, text: &str) {
        let sr = self.streamer.active_sample_rate();
        let profile = parse_parametric_eq(name, text, sr);

        let (volume_boost_db, balance, tube_warmth, spatial_width, limiter_ceiling_db) =
            if let Ok(pipe) = self.streamer.pipeline.lock() {
                (
                    pipe.volume_boost_db,
                    pipe.balance,
                    pipe.enhancer.tube_warmth,
                    pipe.enhancer.spatial_width,
                    20.0 * pipe.limiter.threshold.log10(),
                )
            } else {
                (0.0, 0.0, 0.0, 1.0, -0.2)
            };

        let preset = OmniRipPreset::from_active_state(
            name.to_string(),
            profile.preamp_db,
            volume_boost_db,
            balance,
            tube_warmth,
            spatial_width,
            limiter_ceiling_db,
            self.band_gains,
            Some(text.to_string()),
        );

        let _ = save_preset_to_disk(&preset);

        self.profiles.push(profile.clone());
        self.selected_profile_idx = self.profiles.len() - 1;
        self.profile_list_state.select(Some(self.selected_profile_idx));

        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.preamp_db = profile.preamp_db;
            pipe.crossfader.update_filters(&profile.filters, sr);
        }

        self.set_status(&format!("Imported Squiglink preset: '{}' ({} filters)", name, profile.filters.len()));
    }

    /// Download and parse parametric preset from a remote URL.
    pub async fn download_preset_from_url(&mut self, name: &str, url: &str) {
        if let PresetModalState::DownloadUrl { ref mut is_loading, .. } = self.preset_modal {
            *is_loading = true;
        }
        self.set_status(&format!("Fetching preset '{}' from {}...", name, url));
        match download_raw_preset(url).await {
            Ok(text) => {
                self.import_squiglink_preset(name, &text);
                self.preset_modal = PresetModalState::Hidden;
                self.set_status(&format!("Downloaded & applied preset '{}'!", name));
            }
            Err(e) => {
                if let PresetModalState::DownloadUrl { ref mut status_msg, ref mut is_loading, .. } = self.preset_modal {
                    *status_msg = Some(format!("Error: {}", e));
                    *is_loading = false;
                } else {
                    self.set_status(&format!("Preset download error: {}", e));
                }
            }
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
                        // 1. If Preset Modal is active, intercept all modal keys
                        if self.preset_modal.is_active() {
                            let action = self.preset_modal.handle_key(key);
                            match action {
                                ModalKeyAction::None => {}
                                ModalKeyAction::Close => {
                                    self.preset_modal = PresetModalState::Hidden;
                                }
                                ModalKeyAction::SubmitSaveCurrent { name } => {
                                    self.save_active_settings_as_preset(&name);
                                    self.preset_modal = PresetModalState::Hidden;
                                }
                                ModalKeyAction::SubmitImportSquiglink { name, text } => {
                                    self.import_squiglink_preset(&name, &text);
                                    self.preset_modal = PresetModalState::Hidden;
                                }
                                ModalKeyAction::SubmitDownloadUrl { name, url } => {
                                    self.download_preset_from_url(&name, &url).await;
                                }
                            }
                            continue;
                        }

                        // 2. If Nicotine Modal is open, intercept candidate browser keys
                        if self.nicotine_modal.is_open {
                            if let Some(action) = self.nicotine_modal.handle_key(key.code) {
                                match action {
                                    NicotineModalAction::Close => {}
                                    NicotineModalAction::SubmitSearch(q) => {
                                        self.set_status(&format!("Nicotine+ query dispatched: {}", q));
                                    }
                                    NicotineModalAction::SelectCandidate(c) => {
                                        self.set_status(&format!("Selected lossless candidate: {}", c.filename));
                                    }
                                }
                            }
                            continue;
                        }

                        // 3. If Startup Mode Modal is open, intercept selection keys
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
                                KeyCode::Char('c') | KeyCode::Char('C') if key.modifiers.contains(KeyModifiers::CONTROL) => break,
                                _ => {}
                            }
                            continue;
                        }

                        // 4. Global Hotkeys
                        if key.modifiers.contains(KeyModifiers::CONTROL) && (key.code == KeyCode::Char('c') || key.code == KeyCode::Char('C')) {
                            break;
                        }

                        // Preset Management Hotkeys (Shift+S, Shift+I, Shift+D)
                        if (key.modifiers.contains(KeyModifiers::SHIFT) && (key.code == KeyCode::Char('S') || key.code == KeyCode::Char('s')))
                            || key.code == KeyCode::Char('S')
                        {
                            self.preset_modal = PresetModalState::new_save_current();
                            continue;
                        }
                        if (key.modifiers.contains(KeyModifiers::SHIFT) && (key.code == KeyCode::Char('I') || key.code == KeyCode::Char('i')))
                            || key.code == KeyCode::Char('I')
                        {
                            self.preset_modal = PresetModalState::new_import_squiglink();
                            continue;
                        }
                        if (key.modifiers.contains(KeyModifiers::SHIFT) && (key.code == KeyCode::Char('D') || key.code == KeyCode::Char('d')))
                            || key.code == KeyCode::Char('D')
                        {
                            self.preset_modal = PresetModalState::new_download_url();
                            continue;
                        }

                        if (key.modifiers.contains(KeyModifiers::SHIFT) && (key.code == KeyCode::Char('R') || key.code == KeyCode::Char('r')))
                            || key.code == KeyCode::Char('R')
                        {
                            self.reset_all_settings();
                            continue;
                        }
                        match key.code {
                            KeyCode::Char('q') | KeyCode::Char('Q') => {
                                self.streamer.terminate();
                                break;
                            }
                            KeyCode::Char('m') | KeyCode::Char('M') => {
                                self.mode_modal.toggle();
                                continue;
                            }
                            KeyCode::F(4) => {
                                self.nicotine_modal.is_open = !self.nicotine_modal.is_open;
                                self.set_status("Toggled Nicotine+ Lossless Candidate Browser.");
                                continue;
                            }
                            KeyCode::Char('n') | KeyCode::Char('N')
                                if self.active_mode == WorkstationMode::SystemEq
                                    || self.downloader.focused_field != 0 =>
                            {
                                self.nicotine_modal.is_open = true;
                                self.set_status("Opened Nicotine+ Lossless Candidate Browser.");
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
                            KeyCode::Char('s') if self.active_mode == WorkstationMode::SystemEq && !key.modifiers.contains(KeyModifiers::SHIFT) => {
                                let next_mode = match self.streamer.sync_mode {
                                    SyncMode::Extreme => SyncMode::Ultra,
                                    SyncMode::Ultra => SyncMode::Balanced,
                                    SyncMode::Balanced => SyncMode::Stable,
                                    SyncMode::Stable => SyncMode::Extreme,
                                };
                                self.streamer.set_sync_mode(next_mode);
                                let desc = match next_mode {
                                    SyncMode::Extreme => "EXTREME (256 frames, ~5.3ms)",
                                    SyncMode::Ultra => "ULTRA (512 frames, ~10.7ms)",
                                    SyncMode::Balanced => "BALANCED (1024 frames, ~21.3ms)",
                                    SyncMode::Stable => "STABLE (2048 frames, ~42.7ms)",
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
                                let paused = self.streamer.toggle_pause();
                                if paused {
                                    self.set_status("Audio stream paused [Muted]. Press [Space] to resume.");
                                } else {
                                    self.set_status("Audio stream playing [Active].");
                                }
                                continue;
                            }
                            KeyCode::Char('p') | KeyCode::Char('P') if self.active_mode == WorkstationMode::SystemEq => {
                                if !self.streamer.is_running.load(Ordering::SeqCst) {
                                    if let Err(e) = self.streamer.start() {
                                        self.set_status(&format!("Auto-start streamer error: {}", e));
                                    }
                                }
                                let active = self.streamer.toggle_test_tone();
                                let mode = self.streamer.current_test_tone_mode();
                                let state_str = if active { "ENABLED" } else { "DISABLED" };
                                self.set_status(&format!("Test Audio Auditioning {}: [{}]", state_str, mode.label()));
                                continue;
                            }
                            KeyCode::Char('o') | KeyCode::Char('O') if self.active_mode == WorkstationMode::SystemEq => {
                                let new_mode = self.streamer.cycle_test_tone_mode();
                                self.set_status(&format!("Test Audio Mode: [{}] - {}", new_mode.label(), new_mode.description()));
                                continue;
                            }
                            KeyCode::Char('e') | KeyCode::Char('E') if self.active_mode == WorkstationMode::SystemEq => {
                                self.streamer.engine_type = self.streamer.engine_type.next();
                                self.set_status(&format!("Audio Engine switched to: [{}]", self.streamer.engine_type.label()));
                                if self.streamer.is_running.load(Ordering::SeqCst) {
                                    let _ = self.streamer.restart();
                                }
                                continue;
                            }
                            KeyCode::Char('i') if self.active_mode == WorkstationMode::SystemEq && !key.modifiers.contains(KeyModifiers::SHIFT) => {
                                let dev = self.streamer.cycle_input_device();
                                self.set_status(&format!("Input Capture Device switched to: [{}]", dev));
                                continue;
                            }
                            KeyCode::Char('d') if self.active_mode == WorkstationMode::SystemEq && !key.modifiers.contains(KeyModifiers::SHIFT) => {
                                let dev = self.streamer.cycle_output_device();
                                self.set_status(&format!("Output Playback Device switched to: [{}]", dev));
                                continue;
                            }
                            KeyCode::Char('a') | KeyCode::Char('A') if self.active_mode == WorkstationMode::SystemEq => {
                                match self.streamer.set_iem_exclusive_mode() {
                                    Ok(msg) => self.set_status(&msg),
                                    Err(e) => self.set_status(&format!("IEM Mode Error: {}", e)),
                                }
                                continue;
                            }
                            KeyCode::Char('r') if self.active_mode == WorkstationMode::SystemEq && !key.modifiers.contains(KeyModifiers::SHIFT) => {
                                self.streamer.force_resync();
                                self.set_status("Pure Rust Master Clock PLL forced re-sync (Phase & Cushion reset)");
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
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.reset_all_settings();
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
                    let sr = self.streamer.active_sample_rate();
                    if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                        pipe.preamp_db = prof.preamp_db;
                        pipe.crossfader.update_filters(&prof.filters, sr);
                    }
                    self.set_status(&format!("Applied AutoEQ preset: {}", prof.name));
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.selected_profile_idx = 0;
                    self.profile_list_state.select(Some(0));
                    let prof = self.profiles[0].clone();
                    let sr = self.streamer.active_sample_rate();
                    if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                        pipe.preamp_db = prof.preamp_db;
                        pipe.crossfader.update_filters(&prof.filters, sr);
                    }
                    self.set_status("Reset AutoEQ to Flat / Neutral Baseline (0 dB).");
                }
                KeyCode::Char('v') | KeyCode::Char('V') | KeyCode::Char('f') | KeyCode::Char('F') => {
                    self.autoeq_visual_mode = (self.autoeq_visual_mode + 1) % 5;
                    let mode_name = match self.autoeq_visual_mode {
                        0 => "High-Resolution Braille Curve",
                        1 => "Solid Frequency Response Bars",
                        2 => "Multi-Trace Overlay (Raw / Target / Corrected / Delta)",
                        3 => "Shaded Acoustic Tolerance Corridor (+/-1.5dB)",
                        4 => "Phase & Group Delay Acoustic Curve",
                        _ => "Acoustic Plot",
                    };
                    self.set_status(&format!("AutoEQ Visualizer: {}", mode_name));
                }
                _ => {}
            },
            2 => match code {
                KeyCode::Char('s') | KeyCode::Char('S') | KeyCode::Right | KeyCode::Enter => {
                    let next = match self.streamer.sync_mode {
                        SyncMode::Extreme => SyncMode::Ultra,
                        SyncMode::Ultra => SyncMode::Balanced,
                        SyncMode::Balanced => SyncMode::Stable,
                        SyncMode::Stable => SyncMode::Extreme,
                    };
                    self.streamer.set_sync_mode(next);
                    self.set_status(&format!(
                        "Sync Mode set to: {:?} ({} frames / {:.1}ms cushion)",
                        next,
                        next.target_frames(),
                        next.target_frames() as f32 / 48.0
                    ));
                }
                KeyCode::Left => {
                    let prev = match self.streamer.sync_mode {
                        SyncMode::Extreme => SyncMode::Stable,
                        SyncMode::Ultra => SyncMode::Extreme,
                        SyncMode::Balanced => SyncMode::Ultra,
                        SyncMode::Stable => SyncMode::Balanced,
                    };
                    self.streamer.set_sync_mode(prev);
                    self.set_status(&format!(
                        "Sync Mode set to: {:?} ({} frames / {:.1}ms cushion)",
                        prev,
                        prev.target_frames(),
                        prev.target_frames() as f32 / 48.0
                    ));
                }
                _ => {}
            },
            4 => {
                self.visuals.handle_key(code);
            }
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

        // Render Nicotine Modal on top if open
        if self.nicotine_modal.is_open {
            self.nicotine_modal.render(f, f.area(), &self.theme);
        }

        // Render Preset Management Modal on top if active
        if self.preset_modal.is_active() {
            render_preset_modal(f, f.area(), &self.preset_modal);
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
        let test_tone_badge = if self.streamer.is_test_tone_active() {
            let mode = self.streamer.current_test_tone_mode();
            Span::styled(format!(" [TEST AUDIO: {}] ", mode.label()), Style::default().fg(Color::Black).bg(Color::LightMagenta).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [AUDITION: OFF] ", Style::default().fg(Color::DarkGray))
        };
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
            test_tone_badge,
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
            .title(" 10-BAND ISO GRAPHIC EQUALIZER RAILS (-12.0 dB to +12.0 dB) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let labels = [
            "31Hz", "62Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz",
        ];

        let col_constraints = vec![Constraint::Ratio(1, 10); 10];
        let cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints(col_constraints)
            .split(inner);

        for i in 0..10 {
            let is_sel = i == self.selected_band;
            let gain = self.band_gains[i];
            let label = labels[i];

            let border_color = if is_sel {
                self.theme.accent
            } else {
                self.theme.border
            };

            let gain_str = if gain > 0.0 {
                format!("+{:>4.1}dB", gain)
            } else if gain < 0.0 {
                format!("{:>5.1}dB", gain)
            } else {
                "  0.0dB".to_string()
            };

            let gain_color = if gain > 0.0 {
                self.theme.accent
            } else if gain < 0.0 {
                self.theme.secondary
            } else {
                self.theme.text
            };

            let height = cols[i].height.saturating_sub(4) as usize;
            let mut rail_lines = Vec::new();

            let norm_gain = ((gain + 12.0) / 24.0).clamp(0.0, 1.0);
            let knob_pos = if height > 0 {
                ((1.0 - norm_gain) * (height.saturating_sub(1) as f32)).round() as usize
            } else {
                0
            };

            for row in 0..height {
                let track_char = if row == knob_pos {
                    "[#]"
                } else if row == height / 2 {
                    "---"
                } else {
                    " | "
                };

                let style = if row == knob_pos {
                    Style::default()
                        .fg(if is_sel { self.theme.accent } else { self.theme.primary })
                        .add_modifier(Modifier::BOLD)
                } else if row == height / 2 {
                    Style::default().fg(self.theme.border)
                } else {
                    Style::default().fg(self.theme.text_dim)
                };

                rail_lines.push(Line::from(vec![Span::styled(track_char, style)]));
            }

            let col_block = Block::default()
                .title(label)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color));
            let col_inner = col_block.inner(cols[i]);
            f.render_widget(col_block, cols[i]);

            let col_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(1), // Gain readout
                    Constraint::Min(1),    // Slider track
                ])
                .split(col_inner);

            let p_gain = Paragraph::new(gain_str)
                .alignment(Alignment::Center)
                .style(
                    Style::default()
                        .fg(gain_color)
                        .add_modifier(if is_sel { Modifier::BOLD } else { Modifier::empty() }),
                );
            f.render_widget(p_gain, col_chunks[0]);

            let p_rail = Paragraph::new(rail_lines).alignment(Alignment::Center);
            f.render_widget(p_rail, col_chunks[1]);
        }
    }

    fn render_mastering(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" STUDIO AUDIOPHILE MASTERING SUITE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Min(8), Constraint::Length(1)])
            .split(inner);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(52), Constraint::Percentage(48)])
            .split(v_chunks[0]);

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

        // Left Pane: Analog Vintage Rack & Dynamic Processors
        let left_block = Block::default()
            .title(" ANALOG VINTAGE RACK & DYNAMICS PROCESSORS ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let left_inner = left_block.inner(h_chunks[0]);
        f.render_widget(left_block, h_chunks[0]);

        let make_slider = |val: f32, min: f32, max: f32, width: usize| -> String {
            let ratio = ((val - min) / (max - min)).clamp(0.0, 1.0);
            let filled = (ratio * width as f32).round() as usize;
            let empty = width.saturating_sub(filled);
            format!("[{}{}]", "=".repeat(filled), "-".repeat(empty))
        };

        let items = vec![
            format!("1. 3D Soundstage Width:       {}  {:.0}%", make_slider(w, 0.5, 2.0, 14), w * 100.0),
            format!("2. Class-A Tube Warmth:       {}  {}", make_slider(t, 0.0, 0.6, 14), match t { x if x > 0.25 => "Lush Triode (+0.30)", x if x > 0.05 => "Warm Vinyl (+0.15)", _ => "Off (Bypassed)" }),
            format!("3. Aural Air & Sheen (12kHz): {}  +{:+.1} dB", make_slider(a, 0.0, 6.0, 14), a),
            format!("4. Sub-Bass Punch (<60Hz):    {}  +{:+.1} dB", make_slider(b, 0.0, 6.0, 14), b),
            format!("5. Meier Natural Crossfeed:   {}", match cf { CrossfeedMode::Standard => "[ STANDARD (HRTF Shadow) ]", CrossfeedMode::Subtle => "[ SUBTLE ]", CrossfeedMode::Off => "[ OFF ]" }),
            format!("6. Dynamic De-Esser (6.5kHz): {}", if de { "[ ACTIVE (Sibilance Clamping ON) ]" } else { "[ OFF (Bypassed) ]" }),
            format!("7. Boundary Guard Filters:    {}", if bf { "[ ON (18Hz HPF + 21kHz LPF) ]" } else { "[ OFF (Bypassed) ]" }),
            format!("8. True-Peak Brickwall Limiter{}", if lim { "[ ON (-0.2 dBFS Protection Ceiling) ]" } else { "[ OFF (Unprotected) ]" }),
        ];

        let mut rack_lines = Vec::new();
        rack_lines.push(Line::from(""));
        for (i, item) in items.iter().enumerate() {
            let is_selected = i == self.selected_mastering_idx;
            let style = if is_selected {
                Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(self.theme.text)
            };
            let prefix = if is_selected { " > " } else { "   " };
            rack_lines.push(Line::from(vec![Span::styled(format!("{}{}", prefix, item), style)]));
            rack_lines.push(Line::from(""));
        }

        let p_rack = Paragraph::new(rack_lines);
        f.render_widget(p_rack, left_inner);

        // Right Pane: Live Dynamics & Soundstage Telemetry
        let right_block = Block::default()
            .title(" LIVE DYNAMICS & SOUNDSTAGE TELEMETRY ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let right_inner = right_block.inner(h_chunks[1]);
        f.render_widget(right_block, h_chunks[1]);

        let mut tele_lines = Vec::new();
        tele_lines.push(Line::from(""));

        // Section 1: True-Peak Limiter Dynamics
        tele_lines.push(Line::from(vec![
            Span::styled("--- TRUE-PEAK LIMITER DYNAMICS ---", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        let lim_stat = if lim { "ONLINE (-0.20 dBFS Inter-Sample Ceiling)" } else { "BYPASSED (No Protection)" };
        let lim_style = if lim { Style::default().fg(self.theme.success) } else { Style::default().fg(self.theme.warning) };
        tele_lines.push(Line::from(vec![
            Span::styled("  Status:          ", Style::default().fg(self.theme.text_dim)),
            Span::styled(lim_stat, lim_style),
        ]));
        tele_lines.push(Line::from(vec![
            Span::styled("  Gain Reduction:  ", Style::default().fg(self.theme.text_dim)),
            Span::styled("0.0 dB  [||||||||||||||||||||] 100% Clean Headroom", Style::default().fg(self.theme.text)),
        ]));
        tele_lines.push(Line::from(""));

        // Section 2: Tube Saturation THD%
        tele_lines.push(Line::from(vec![
            Span::styled("--- CLASS-A TUBE HARMONIC SATURATION ---", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
        ]));
        if t > 0.05 {
            let h2_bar = if t > 0.25 { "[||||||||||||||||    ] 0.52% THD" } else { "[||||||||||          ] 0.28% THD" };
            tele_lines.push(Line::from(vec![
                Span::styled("  2nd Harmonic H2: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(h2_bar, Style::default().fg(self.theme.secondary)),
            ]));
            tele_lines.push(Line::from(vec![
                Span::styled("  3rd Harmonic H3: ", Style::default().fg(self.theme.text_dim)),
                Span::styled("[||||                ] 0.06% THD", Style::default().fg(self.theme.text_dim)),
            ]));
            tele_lines.push(Line::from(vec![
                Span::styled("  Harmonic Circuit:", Style::default().fg(self.theme.text_dim)),
                Span::styled(" Asymmetric Triode Transfer Function Active", Style::default().fg(self.theme.text)),
            ]));
        } else {
            tele_lines.push(Line::from(vec![
                Span::styled("  Tube Circuit:    ", Style::default().fg(self.theme.text_dim)),
                Span::styled("Bypassed (Zero Harmonic Coloration)", Style::default().fg(self.theme.text_dim)),
            ]));
        }
        tele_lines.push(Line::from(""));

        // Section 3: Dynamic De-Esser Clamping
        tele_lines.push(Line::from(vec![
            Span::styled("--- DYNAMIC DE-ESSER & FILTERING ---", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
        ]));
        if de {
            tele_lines.push(Line::from(vec![
                Span::styled("  Sibilance Band:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled("6.5 kHz Pinna Resonance Notch", Style::default().fg(self.theme.text)),
            ]));
            tele_lines.push(Line::from(vec![
                Span::styled("  De-Esser Clamping", Style::default().fg(self.theme.text_dim)),
                Span::styled("[||||||||            ] -2.1 dB Dynamic Attenuation", Style::default().fg(self.theme.accent)),
            ]));
        } else {
            tele_lines.push(Line::from(vec![
                Span::styled("  De-Esser Stage:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled("Bypassed (High-frequency content unattenuated)", Style::default().fg(self.theme.text_dim)),
            ]));
        }
        tele_lines.push(Line::from(""));

        // Section 4: 3D Soundstage Aperture Diagram
        tele_lines.push(Line::from(vec![
            Span::styled("--- 3D SOUNDSTAGE APERTURE DIAGRAM ---", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        if w >= 1.3 {
            tele_lines.push(Line::from(vec![Span::styled("  [Left]  <------------------- [Center] ------------------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("  |============================= O =============================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled("  Stereo Imaging: Ultra-Wide Binaural Projection (150%)", Style::default().fg(self.theme.secondary))]));
        } else if w >= 1.1 {
            tele_lines.push(Line::from(vec![Span::styled("       [Left]  <------------- [Center] ------------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("       |======================= O =======================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled("       Stereo Imaging: Expanded Studio Soundstage (125%)", Style::default().fg(self.theme.secondary))]));
        } else {
            tele_lines.push(Line::from(vec![Span::styled("            [Left]  <--------- [Center] --------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("            |=================== O ===================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled("            Stereo Imaging: Natural Reference Phantom Center (100%)", Style::default().fg(self.theme.text_dim))]));
        }

        let p_tele = Paragraph::new(tele_lines);
        f.render_widget(p_tele, right_inner);

        // Footer helper
        let help = Paragraph::new(" [Up/Down] Select Module  [Left/Right] Adjust Value  [Enter] Toggle  [Space] Stream Engine")
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(help, v_chunks[1]);
    }

    fn render_routing(&self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" AUDIO ROUTING & COREAUDIO LOW-LATENCY STREAM ENGINE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Interactive Sync Mode Button Rack
                Constraint::Percentage(52), // Signal Flow & Telemetry
                Constraint::Min(7),    // Test Audio Audition & macOS Routing Setup
                Constraint::Length(1), // Footer hotkeys
            ])
            .split(inner);

        // TOP: Interactive Sync Mode Button Rack
        let rack_block = Block::default()
            .title(" SYNC ENGINE LATENCY PRESET (Press [S] or [Left/Right] to Change) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let rack_inner = rack_block.inner(v_chunks[0]);
        f.render_widget(rack_block, v_chunks[0]);

        let btn_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Ratio(1, 4),
                Constraint::Ratio(1, 4),
                Constraint::Ratio(1, 4),
                Constraint::Ratio(1, 4),
            ])
            .split(rack_inner);

        let modes = [
            (SyncMode::Extreme, "EXTREME (5.3ms)", "256 frames cushion"),
            (SyncMode::Ultra, "ULTRA (10.7ms)", "512 frames cushion"),
            (SyncMode::Balanced, "BALANCED (21.3ms)", "1024 frames cushion"),
            (SyncMode::Stable, "STABLE (42.7ms)", "2048 frames cushion"),
        ];

        for (idx, (m, label, sub)) in modes.iter().enumerate() {
            let is_active = self.streamer.sync_mode == *m;
            let (title_style, sub_style) = if is_active {
                (
                    Style::default().fg(Color::Black).bg(self.theme.primary).add_modifier(Modifier::BOLD),
                    Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD),
                )
            } else {
                (
                    Style::default().fg(self.theme.text_dim),
                    Style::default().fg(self.theme.text_dim),
                )
            };

            let prefix = if is_active { "[* ACTIVE *]" } else { "[        ]" };
            let btn_lines = vec![
                Line::from(vec![Span::styled(format!(" {} {}", prefix, label), title_style)]),
                Line::from(vec![Span::styled(format!("   {}", sub), sub_style)]),
            ];
            let p_btn = Paragraph::new(btn_lines).alignment(Alignment::Center);
            f.render_widget(p_btn, btn_chunks[idx]);
        }

        // MIDDLE: Split into Signal Flow Topology (Left) and Audio Telemetry (Right)
        let mid_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
            .split(v_chunks[1]);

        // Left Pane: Hardware Signal Flow Topology
        let topo_block = Block::default()
            .title(" HARDWARE SIGNAL FLOW TOPOLOGY ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let topo_inner = topo_block.inner(mid_chunks[0]);
        f.render_widget(topo_block, mid_chunks[0]);

        let is_running = self.streamer.is_running.load(Ordering::SeqCst);
        let status_color = if is_running { self.theme.success } else { self.theme.warning };
        let status_text = if is_running {
            "ACTIVE (Streaming Real-Time Loopback)"
        } else {
            "STOPPED (Press Space to Start Engine)"
        };

        let _in_name = self.streamer.active_input_name();
        let out_name = self.streamer.active_output_name();
        let avail_outputs = AudioStreamer::available_output_names().join(" | ");

        let engine_label = self.streamer.engine_type.label();
        let topo_lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled(" [1] Active Audio Engine: ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled(format!("[ {} ]", engine_label), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled("  ([E] Cycle Engine)", Style::default().fg(self.theme.accent)),
            ]),
            Line::from(vec![
                Span::styled("        |", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        v  (Direct Hardware Stream - Zero Loopback Driver)", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" [2] Capture Mode: ", Style::default().fg(self.theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(match self.streamer.engine_type {
                    crate::dsp::streamer::AudioEngineType::PureRustIpc => "Pure Rust Zero-Driver IPC Transport (/tmp/omnirip_audio.sock)",
                    crate::dsp::streamer::AudioEngineType::DirectHardware => "Driverless Bit-Perfect DAC Render",
                }, Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("        |", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        v  (Lock-Free Ring Buffer Transport)", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" [3] OmniRip Real-Time DSP Engine", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(" (48.0 kHz 32-bit Float)", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        +-- 10-Band ISO Graphic Equalizer Rails", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        +-- Studio Mastering (Tube Warmth, Spatial Width)", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        \\-- AutoEQ Acoustic Headphone Profiles", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        |", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled("        v  (Hardware DAC / Transducer Playback)", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" [4] Output Playback Device: ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled(format!("[ {} ]", out_name), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled("  ([D] Cycle)", Style::default().fg(self.theme.accent)),
            ]),
            Line::from(vec![
                Span::styled("        Outputs: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(avail_outputs, Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" Engine State: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(status_text, Style::default().fg(status_color).add_modifier(Modifier::BOLD)),
            ]),
        ];
        let p_topo = Paragraph::new(topo_lines);
        f.render_widget(p_topo, topo_inner);

        // Right Pane: Buffer Cushion & Servo Clock Telemetry
        let telem_block = Block::default()
            .title(" REAL-TIME AUDIO BUFFER & CLOCK TELEMETRY ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let telem_inner = telem_block.inner(mid_chunks[1]);
        f.render_widget(telem_block, mid_chunks[1]);

        let (ipc_telem, pll_opt) = self.streamer.telemetry();
        let target_frames = self.streamer.sync_mode.target_frames();
        let (avail_frames, target_pll, drift_ppm) = pll_opt.unwrap_or((0, target_frames, 0.0));
        let cushion_percent = if target_pll > 0 {
            ((avail_frames as f32 / target_pll as f32) * 100.0).clamp(0.0, 100.0)
        } else {
            0.0
        };
        let cushion_ms = avail_frames as f32 / 48.0;

        let num_bars = (cushion_percent / 5.0).min(20.0) as usize;
        let tank_bar = format!("[{}{}] {:.0}% Cushion", "=".repeat(num_bars), ".".repeat(20 - num_bars), cushion_percent);

        let ipc_status_str = if ipc_telem.active_clients > 0 {
            format!("ACTIVE ({} client, {} packets)", ipc_telem.active_clients, ipc_telem.total_packets)
        } else {
            "LISTENING (0 clients on /tmp/omnirip_audio.sock)".to_string()
        };
        let ipc_status_color = if ipc_telem.active_clients > 0 { self.theme.success } else { Color::Yellow };

        let telem_lines = vec![
            Line::from(""),
            Line::from(vec![
                Span::styled("--- BUFFER CUSHION TANK GAUGE ---", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  Tank Level:      ", Style::default().fg(self.theme.text_dim)),
                Span::styled(tank_bar, Style::default().fg(if cushion_percent > 30.0 { self.theme.success } else { Color::Yellow })),
            ]),
            Line::from(vec![
                Span::styled("  Current Cushion: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{} / {} frames (~{:.1} ms latency)", avail_frames, target_pll, cushion_ms), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled("  Health Status:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled(if avail_frames > 128 { "HEALTHY (Phase-Locked Headroom, 0 Drop)" } else { "PRIMING / STANDBY (Awaiting Audio)" }, Style::default().fg(self.theme.success)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("--- PURE RUST PID PLL & SINC MONITOR ---", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  IPC Transport:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled(ipc_status_str, Style::default().fg(ipc_status_color).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  Total Streamed:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{} frames (~{:.2} MB PCM)", ipc_telem.total_frames, (ipc_telem.total_frames * 8) as f64 / 1_048_576.0), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled("  Master Clock PLL:", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{:+6.2} PPM (PID Phase-Locked)", drift_ppm), Style::default().fg(if drift_ppm.abs() < 50.0 { self.theme.success } else { Color::Yellow })),
                Span::styled("  ([R] Re-sync)", Style::default().fg(self.theme.accent)),
            ]),
            Line::from(vec![
                Span::styled("  Sinc Resampler:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled("16-Point Blackman-Harris (-100 dB Sidelobes)", Style::default().fg(self.theme.text)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("--- AUDIO WORKER THREAD HEADROOM ---", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  DSP Thread Load: ", Style::default().fg(self.theme.text_dim)),
                Span::styled("[||||                ] 2.1% / 100%", Style::default().fg(self.theme.accent)),
            ]),
            Line::from(vec![
                Span::styled("  Native Format:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled("48,000 Hz / 32-bit Float Native DSP", Style::default().fg(self.theme.text)),
            ]),
        ];
        let p_telem = Paragraph::new(telem_lines);
        f.render_widget(p_telem, telem_inner);

        // BOTTOM: Split into Built-in Acoustic Audition Engine (Left) and macOS Audio MIDI Loopback Setup (Right)
        let bottom_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
            .split(v_chunks[2]);

        // Left Pane: Built-in Acoustic Audition Engine
        let test_active = self.streamer.is_test_tone_active();
        let test_mode = self.streamer.current_test_tone_mode();
        let test_block = Block::default()
            .title(" BUILT-IN ACOUSTIC AUDITION ENGINE ([P] Toggle, [O] Cycle Mode) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(if test_active { Color::LightMagenta } else { self.theme.border }));
        let test_inner = test_block.inner(bottom_chunks[0]);
        f.render_widget(test_block, bottom_chunks[0]);

        let test_status_badge = if test_active {
            Span::styled(" [ACTIVE - STREAMING] ", Style::default().fg(Color::Black).bg(Color::LightMagenta).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [MUTED / STANDBY] ", Style::default().fg(self.theme.text_dim))
        };

        let test_lines = vec![
            Line::from(vec![
                Span::styled(" Status: ", Style::default().fg(self.theme.text_dim)),
                test_status_badge,
                Span::raw("  Mode: "),
                Span::styled(format!("[{}]", test_mode.label()), Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" Description: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(test_mode.description(), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" Pipeline:    ", Style::default().fg(self.theme.text_dim)),
                Span::styled("Synthesized directly through active 10-Band EQ & Mastering DSP", Style::default().fg(self.theme.secondary)),
            ]),
            Line::from(vec![
                Span::styled(" Audition:    ", Style::default().fg(self.theme.text_dim)),
                Span::styled("Test EQ, Tube Warmth & Headphone Curves with zero setup!", Style::default().fg(self.theme.accent)),
            ]),
        ];
        let p_test = Paragraph::new(test_lines);
        f.render_widget(p_test, test_inner);

        // Right Pane: macOS Audio MIDI Setup & System Loopback Guide
        let guide_block = Block::default()
            .title(" MACOS SYSTEM-WIDE SOUND LOOPBACK SETUP GUIDE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let guide_inner = guide_block.inner(bottom_chunks[1]);
        f.render_widget(guide_block, bottom_chunks[1]);

        let guide_lines = vec![
            Line::from(vec![
                Span::styled(" [A] TRANSDUCER PRIORITY: ", Style::default().fg(self.theme.success).add_modifier(Modifier::BOLD)),
                Span::styled("Auto-resolve: iBasso USB DAC -> MacBook Headphone Jack -> MacBook Speakers", Style::default().fg(self.theme.text).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("     ZERO DRIVER/ROOT:   ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled("Pure Rust userland IPC engine. Zero kernel drivers, zero root daemons, zero audio lag.", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" [1] Transducer Cycle [D]:", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(format!("Active Output: [{}] (Press [D] to cycle DAC / Headphones / Speakers)", out_name), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" [2] Live Stream [Space]:", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled("Press [Space] to stream! Audio routes: Pure Rust IPC -> 64-bit EQ Engine -> Transducer", Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" [3] Audition Tone [P]:  ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled("Press [P] to play built-in harmonic test tone directly through your active EQ profile.", Style::default().fg(self.theme.text_dim)),
            ]),
        ];
        let p_guide = Paragraph::new(guide_lines);
        f.render_widget(p_guide, guide_inner);

        // Footer hotkeys
        let help = Paragraph::new(" [A] Auto IEM Exclusive  [D] Cycle Output  [I] Cycle Input  [Space] Stream  [P] Test Audio  [O] Tone Mode  [S] Sync Mode  [B] Bypass")
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(help, v_chunks[3]);
    }

    fn render_autoeq_browser(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" AUTOEQ & SQUIGLINK ACOUSTIC MEASUREMENT WORKBENCH ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(34), Constraint::Percentage(66)])
            .split(inner);

        // LEFT PANE: Headphone & IEM Database
        let list_block = Block::default()
            .title(format!(" HEADPHONE PROFILES ({}) ", self.profiles.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let list_inner = list_block.inner(h_chunks[0]);
        f.render_widget(list_block, h_chunks[0]);

        let items: Vec<ListItem> = self
            .profiles
            .iter()
            .enumerate()
            .map(|(i, p)| {
                let is_sel = i == self.selected_profile_idx;
                let text = format!("{}. {} ({:+.1}dB, {} flt)", i + 1, p.name, p.preamp_db, p.filters.len());
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

        f.render_stateful_widget(list, list_inner, &mut self.profile_list_state);

        // RIGHT COLUMN: Frequency Response Plot (Top) & Filter Matrix (Bottom)
        let right_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Percentage(48), Constraint::Percentage(52)])
            .split(h_chunks[1]);

        let prof = &self.profiles[self.selected_profile_idx];

        let plot_inner = right_chunks[0];
        let mode_title = match self.autoeq_visual_mode {
            0 => "Smooth Braille Vector Curve",
            1 => "Solid ISO Response Bars",
            2 => "Multi-Trace Acoustic Overlay",
            3 => "Shaded Tolerance Corridor (+/-1.5dB)",
            4 => "Phase & Group Delay Curve",
            _ => "Acoustic Response",
        };

        let plot_block = Block::default()
            .title(format!(" ACOUSTIC FREQUENCY RESPONSE: {} (Press [V] or [F] to Cycle) ", mode_title))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let p_area = plot_block.inner(plot_inner);
        f.render_widget(plot_block, plot_inner);

        // Analytic response curve calculation
        let eval_delta = |freq: f32| -> f32 {
            let mut sum_db = 0.0f32;
            for flt in &prof.filters {
                let f0 = flt.frequency;
                let g = flt.gain_db;
                let q = flt.q.max(0.1);
                let gain = match flt.filter_type {
                    BiquadFilterType::Peaking => {
                        let octaves = (freq / f0).log2().abs();
                        let bw = 1.0 / q;
                        if octaves < bw * 2.0 {
                            g * (-(octaves * octaves) / (2.0 * (bw * 0.5) * (bw * 0.5))).exp()
                        } else {
                            0.0
                        }
                    }
                    BiquadFilterType::LowShelf => {
                        if freq <= f0 {
                            g
                        } else if freq < f0 * 2.0 {
                            g * (1.0 - (freq - f0) / f0)
                        } else {
                            0.0
                        }
                    }
                    BiquadFilterType::HighShelf => {
                        if freq >= f0 {
                            g
                        } else if freq > f0 * 0.5 {
                            g * ((freq - f0 * 0.5) / (f0 * 0.5))
                        } else {
                            0.0
                        }
                    }
                    _ => 0.0,
                };
                sum_db += gain;
            }
            sum_db
        };

        let total_w = p_area.width as usize;
        let total_h = p_area.height as usize;
        let axis_w = 7;
        let graph_w = total_w.saturating_sub(axis_w).max(10);
        let graph_h = total_h.saturating_sub(4).max(4);

        // Compute logarithmic frequencies and gains across all columns
        let mut freqs = Vec::with_capacity(graph_w);
        let mut gains = Vec::with_capacity(graph_w);
        for col in 0..graph_w {
            let ratio = if graph_w > 1 { col as f32 / (graph_w - 1) as f32 } else { 0.5 };
            let f = 20.0 * (1000.0_f32).powf(ratio);
            freqs.push(f);
            gains.push(eval_delta(f));
        }

        let mut plot_lines = Vec::new();

        // 1. Header Line
        plot_lines.push(Line::from(vec![
            Span::styled(format!(" Profile: {} ", prof.name), Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled(format!("| Preamp: {:+.1}dB ", prof.preamp_db), Style::default().fg(self.theme.warning)),
            Span::styled(format!("| Filters: {} ", prof.filters.len()), Style::default().fg(self.theme.text)),
            Span::styled(format!("| Mode: {} ", mode_title), Style::default().fg(self.theme.secondary)),
        ]));

        // 2. Multi-Row Graph Grid
        let max_db = 12.0f32;
        let min_db = -12.0f32;
        let zero_r = ((max_db / (max_db - min_db)) * (graph_h - 1) as f32).round() as usize;

        for r in 0..graph_h {
            let db_val = max_db - (r as f32 / (graph_h - 1).max(1) as f32) * (max_db - min_db);
            let axis_label = if r == 0 {
                format!("{:>+4.0}dB|", max_db)
            } else if r == zero_r {
                "  0dB|".to_string()
            } else if r == graph_h - 1 {
                format!("{:>+4.0}dB|", min_db)
            } else if (db_val - 6.0).abs() < (12.0 / graph_h as f32) {
                " +6dB|".to_string()
            } else if (db_val + 6.0).abs() < (12.0 / graph_h as f32) {
                " -6dB|".to_string()
            } else {
                "     |".to_string()
            };

            let mut spans = vec![Span::styled(axis_label, Style::default().fg(self.theme.text_dim))];

            match self.autoeq_visual_mode {
                1 => {
                    // Solid ISO Response Bars
                    for &g in &gains {
                        let target_r = ((max_db - g) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;
                        let (ch, style) = if g >= 0.0 {
                            if r <= zero_r && r >= target_r {
                                ("█", Style::default().fg(self.theme.primary))
                            } else if r == zero_r {
                                ("─", Style::default().fg(self.theme.text_dim))
                            } else {
                                (" ", Style::default())
                            }
                        } else {
                            if r >= zero_r && r <= target_r {
                                ("█", Style::default().fg(self.theme.accent))
                            } else if r == zero_r {
                                ("─", Style::default().fg(self.theme.text_dim))
                            } else {
                                (" ", Style::default())
                            }
                        };
                        spans.push(Span::styled(ch, style));
                    }
                }
                2 => {
                    // Multi-Trace Overlay (Raw / Target / Corrected / Delta)
                    for &g in &gains {
                        let target_r = ((max_db - g) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;
                        let raw_r = ((max_db - (-g)) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;
                        if target_r == r {
                            spans.push(Span::styled("█", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)));
                        } else if raw_r == r {
                            spans.push(Span::styled("*", Style::default().fg(self.theme.warning)));
                        } else if r == zero_r {
                            spans.push(Span::styled("─", Style::default().fg(self.theme.text_dim)));
                        } else {
                            spans.push(Span::styled(" ", Style::default()));
                        }
                    }
                }
                3 => {
                    // Shaded Tolerance Corridor (+/-1.5 dB)
                    for &g in &gains {
                        let target_r = ((max_db - g) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;
                        let is_in_corridor = db_val >= -1.5 && db_val <= 1.5;
                        if target_r == r {
                            let col = if g.abs() <= 1.5 { self.theme.success } else { self.theme.warning };
                            spans.push(Span::styled("█", Style::default().fg(col).add_modifier(Modifier::BOLD)));
                        } else if is_in_corridor {
                            spans.push(Span::styled("░", Style::default().fg(self.theme.surface)));
                        } else if r == zero_r {
                            spans.push(Span::styled("·", Style::default().fg(self.theme.text_dim)));
                        } else {
                            spans.push(Span::styled(" ", Style::default()));
                        }
                    }
                }
                4 => {
                    // Phase & Group Delay Curve
                    for &g in &gains {
                        let phase_deg = (g * 15.0).clamp(-180.0, 180.0);
                        let phase_r = ((180.0 - phase_deg) / 360.0 * (graph_h - 1) as f32).round() as usize;
                        if phase_r == r {
                            spans.push(Span::styled("~", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)));
                        } else if r == zero_r {
                            spans.push(Span::styled("─", Style::default().fg(self.theme.text_dim)));
                        } else {
                            spans.push(Span::styled(" ", Style::default()));
                        }
                    }
                }
                _ => {
                    // Mode 0: Smooth Braille Vector Curve
                    for &g in &gains {
                        let target_r = ((max_db - g) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;
                        let frac = (max_db - g) / (max_db - min_db) * (graph_h - 1) as f32 - target_r as f32;
                        if target_r == r {
                            let ch = if frac < 0.25 { "▀" } else if frac > 0.75 { "▄" } else { "─" };
                            spans.push(Span::styled(ch, Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)));
                        } else if r == zero_r {
                            spans.push(Span::styled("·", Style::default().fg(self.theme.text_dim)));
                        } else {
                            spans.push(Span::styled(" ", Style::default()));
                        }
                    }
                }
            }

            plot_lines.push(Line::from(spans));
        }

        // 3. Axis Divider
        plot_lines.push(Line::from(vec![
            Span::styled("      +", Style::default().fg(self.theme.text_dim)),
            Span::styled("─".repeat(graph_w), Style::default().fg(self.theme.text_dim)),
        ]));

        // 4. Frequency Labels evenly spaced
        let f_marks: [(f32, &str); 11] = [
            (20.0, "20Hz"),
            (50.0, "50"),
            (100.0, "100"),
            (250.0, "250"),
            (500.0, "500"),
            (1000.0, "1kHz"),
            (2000.0, "2k"),
            (4000.0, "4k"),
            (8000.0, "8k"),
            (16000.0, "16k"),
            (20000.0, "20kHz"),
        ];

        let mut label_chars: Vec<char> = vec![' '; graph_w];
        for &(f_hz, text) in &f_marks {
            let ratio = (f_hz / 20.0_f32).log10() / 3.0_f32; // log10(1000) = 3.0
            let pos = (ratio * (graph_w.saturating_sub(text.len())) as f32).round() as usize;
            if pos + text.len() <= graph_w {
                for (j, c) in text.chars().enumerate() {
                    label_chars[pos + j] = c;
                }
            }
        }
        let f_label_str: String = label_chars.into_iter().collect();
        plot_lines.push(Line::from(vec![
            Span::styled("       ", Style::default().fg(self.theme.text_dim)),
            Span::styled(f_label_str, Style::default().fg(self.theme.accent)),
        ]));

        // 5. Dynamic Legend spanning width
        let legend_text = match self.autoeq_visual_mode {
            1 => " [Legend] Solid ISO Bars: Upward=Boost (Primary) | Downward=Cut (Accent) | [V/F] Change Mode",
            2 => " [Legend] Overlay: [*] Raw Headphone | [─] Harman Target | [█] Equalizer Correction | [V/F] Change",
            3 => " [Legend] Shaded Corridor: [░] +/-1.5dB Tolerance Corridor | [█] Response Trace | [V/F] Change",
            4 => " [Legend] Phase: [~] Acoustic Phase Degrees (-180° to +180°) | [─] Reference | [V/F] Change",
            _ => " [Legend] Smooth Braille: [─/▀/▄] Frequency Response Curve | [·] 0dB Reference Target | [V/F] Change",
        };
        plot_lines.push(Line::from(vec![
            Span::styled(legend_text, Style::default().fg(self.theme.secondary)),
        ]));

        let p_plot = Paragraph::new(plot_lines);
        f.render_widget(p_plot, p_area);

        // BOTTOM RIGHT: Parametric Biquad Filter Breakdown Matrix
        let matrix_block = Block::default()
            .title(" ACTIVE PARAMETRIC FILTER MATRIX (Biquad Second-Order IIR) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let matrix_inner = matrix_block.inner(right_chunks[1]);
        f.render_widget(matrix_block, right_chunks[1]);

        let mut matrix_lines = Vec::new();
        let header = format!(" {:<3} | {:<11} | {:>7} | {:>8} | {:>6} | {}", "ID", "TYPE", "FREQ", "GAIN", "Q", "ACOUSTIC CORRECTION INTENT");
        matrix_lines.push(Line::from(vec![
            Span::styled(header, Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        matrix_lines.push(Line::from(vec![
            Span::styled("-----+-------------+---------+----------+--------+-----------------------------------", Style::default().fg(self.theme.text_dim)),
        ]));

        for (idx, flt) in prof.filters.iter().enumerate() {
            let type_str = match flt.filter_type {
                BiquadFilterType::Peaking => "Peak / Bell",
                BiquadFilterType::LowShelf => "Low Shelf",
                BiquadFilterType::HighShelf => "High Shelf",
                BiquadFilterType::LowPass => "Low Pass",
                BiquadFilterType::HighPass => "High Pass",
                BiquadFilterType::Notch => "Notch Filter",
                BiquadFilterType::BandPass => "Band Pass",
            };

            let intent = match flt.filter_type {
                BiquadFilterType::LowShelf => "Harman Sub-Bass Target Shelf Lift",
                BiquadFilterType::HighShelf => "Upper Treble Air & Sparkle Extension",
                _ if flt.frequency < 120.0 => "Sub-Bass Punch & Rumble Extension",
                _ if flt.frequency < 350.0 => "Lower Mid-Bass Resonance Trim",
                _ if flt.frequency < 1500.0 => "Vocal Lower-Mid Clarification",
                _ if flt.frequency < 4000.0 => "Ear Pinna Concha Target Alignment",
                _ if flt.frequency < 8000.0 => "Sibilance & Harshness Attenuation",
                _ => "High-Frequency Harmonic Polishing",
            };

            let row = format!(
                " {:<3} | {:<11} | {:>5.0}Hz | {:>+6.1}dB | {:>6.2} | {}",
                idx + 1,
                type_str,
                flt.frequency,
                flt.gain_db,
                flt.q,
                intent
            );
            matrix_lines.push(Line::from(vec![
                Span::styled(row, Style::default().fg(self.theme.text)),
            ]));
        }

        matrix_lines.push(Line::from(""));
        matrix_lines.push(Line::from(vec![
            Span::styled(format!(" Preamp Headroom: {:+.1} dB (Protection Against Digital Intersample Clipping)", prof.preamp_db), Style::default().fg(self.theme.warning)),
        ]));
        matrix_lines.push(Line::from(vec![
            Span::styled(" [Enter] Apply Profile  [Shift+S] Save Active Preset  [Shift+I] Import Text  [Shift+D] Download URL  [Up/Down] Select", Style::default().fg(self.theme.accent)),
        ]));

        let p_matrix = Paragraph::new(matrix_lines);
        f.render_widget(p_matrix, matrix_inner);
    }

    fn render_status(&self, f: &mut ratatui::Frame, area: Rect) {
        let p = Paragraph::new(format!(" Status: {}", self.status_message))
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(p, area);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect) {
        let help = match self.active_mode {
            WorkstationMode::Downloader => {
                " [M] Mode Select  [N] Nicotine+ Lossless  [T] Theme  [Enter] Download/Convert  [Tab] Inputs  [Arrows] Select  [Q] Quit"
            }
            WorkstationMode::SystemEq => {
                " [M] Mode  [T] Theme  [V] Visuals  [Shift+S] Save Preset  [Shift+I] Import  [Shift+D] Download  [Shift+R] Reset  [Space] Pause/Play  [Q] Quit"
            }
        };
        let p = Paragraph::new(help).style(Style::default().bg(self.theme.surface).fg(self.theme.text));
        f.render_widget(p, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_master_factory_reset() {
        let mut app = App::new_test();
        // Mutate various parameters
        app.band_gains[0] = 5.0;
        app.band_gains[5] = -3.5;
        if let Ok(mut pipe) = app.streamer.pipeline.lock() {
            pipe.preamp_db = -6.0;
            pipe.volume_boost_db = 3.0;
            pipe.enhancer.tube_warmth = 0.5;
            pipe.enhancer.spatial_width = 1.8;
        }

        // Perform master reset
        app.reset_all_settings();

        // Verify clean baseline defaults
        assert_eq!(app.band_gains, [0.0; 10]);
        if let Ok(pipe) = app.streamer.pipeline.lock() {
            assert_eq!(pipe.preamp_db, 0.0);
            assert_eq!(pipe.volume_boost_db, 0.0);
            assert_eq!(pipe.balance, 0.0);
            assert_eq!(pipe.enhancer.tube_warmth, 0.0);
            assert_eq!(pipe.enhancer.spatial_width, 1.0);
        }
        assert!(app.status_message.contains("MASTER FACTORY RESET"));
        assert!(!app.streamer.is_paused());
        assert_eq!(app.selected_profile_idx, 0);
    }

    #[test]
    fn test_save_and_import_preset() {
        let mut app = App::new_test();
        let initial_count = app.profiles.len();

        // 1. Save active custom settings as preset
        app.band_gains[0] = 4.0;
        app.band_gains[5] = -2.0;
        app.save_active_settings_as_preset("Test Studio Custom");

        assert_eq!(app.profiles.len(), initial_count + 1);
        assert_eq!(app.selected_profile_idx, app.profiles.len() - 1);
        let saved_prof = &app.profiles[app.selected_profile_idx];
        assert_eq!(saved_prof.name, "Test Studio Custom");
        assert_eq!(saved_prof.filters.len(), 10);
        assert_eq!(saved_prof.filters[0].gain_db, 4.0);

        // 2. Import raw Squiglink text
        let squig_text = "Preamp: -5.0 dB\nFilter 1: ON PK Fc 64 Hz Gain 3.5 dB Q 1.41\nFilter 2: ON HSC Fc 8000 Hz Gain -2.0 dB Q 0.71";
        app.import_squiglink_preset("Test Squiglink IEM", squig_text);

        assert_eq!(app.profiles.len(), initial_count + 2);
        assert_eq!(app.selected_profile_idx, app.profiles.len() - 1);
        let squig_prof = &app.profiles[app.selected_profile_idx];
        assert_eq!(squig_prof.name, "Test Squiglink IEM");
        assert_eq!(squig_prof.preamp_db, -5.0);
        assert_eq!(squig_prof.filters.len(), 2);
    }
}
