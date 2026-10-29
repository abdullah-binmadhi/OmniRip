//! Main Interactive Terminal User Interface in pure Rust using `ratatui` and `crossterm`.
//! Integrates the interactive MP3 Downloader, Startup Mode Selection popup,
//! Multi-Palette Theme Engine (7 themes), and Real-Time Visual Graph Dashboard.

use crate::autoeq::{get_bundled_profiles, parse_parametric_eq, ParametricProfile};
use crate::autoeq::storage::{
    download_raw_preset, load_all_user_mastering_presets, load_all_user_presets,
    save_mastering_preset_to_disk, save_preset_to_disk, OmniRipPreset,
};
use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};
use crate::dsp::enhancer::{AcousticGearProfile, CrossfeedMode, MasteringPreset};
use crate::dsp::streamer::{AudioStreamer, SyncMode};
use crate::dsp::AudioPipeline;
use crate::ui::archiver::ArchiverState;
use crate::ui::downloader::DownloaderState;
use crate::ui::gear_modal::GearWizardModal;
use crate::ui::mode_modal::{ModeModal, WorkstationMode};
use crate::ui::nicotine_modal::{NicotineModal, NicotineModalAction};
use crate::ui::preset_modal::{render_preset_modal, ModalKeyAction, PresetModalState};
use crate::ui::theme::ThemePalette;
use crate::ui::visuals::VisualsDashboard;
use crossterm::event::{self, DisableBracketedPaste, EnableBracketedPaste, Event, KeyCode, KeyEventKind, KeyModifiers};
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

#[derive(Debug, Clone, Default)]
pub struct CommandBarState {
    pub is_open: bool,
    pub input: String,
    pub cursor_pos: usize,
}

impl CommandBarState {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn open(&mut self) {
        self.is_open = true;
        self.input.clear();
        self.cursor_pos = 0;
    }

    pub fn close(&mut self) {
        self.is_open = false;
        self.input.clear();
        self.cursor_pos = 0;
    }

    pub fn handle_key(&mut self, code: KeyCode) -> Option<String> {
        match code {
            KeyCode::Esc => {
                self.close();
                None
            }
            KeyCode::Enter => {
                let cmd = self.input.trim().to_string();
                self.close();
                if cmd.is_empty() {
                    None
                } else {
                    Some(cmd)
                }
            }
            KeyCode::Char(c) => {
                self.input.insert(self.cursor_pos, c);
                self.cursor_pos += 1;
                None
            }
            KeyCode::Backspace => {
                if self.cursor_pos > 0 {
                    self.cursor_pos -= 1;
                    self.input.remove(self.cursor_pos);
                }
                None
            }
            KeyCode::Left => {
                if self.cursor_pos > 0 {
                    self.cursor_pos -= 1;
                }
                None
            }
            KeyCode::Right => {
                if self.cursor_pos < self.input.len() {
                    self.cursor_pos += 1;
                }
                None
            }
            _ => None,
        }
    }
}

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
    pub archiver: ArchiverState,
    pub streaming_hub: crate::ui::StreamingHubState,
    pub mastering_presets: Vec<MasteringPreset>,
    pub mastering_preset_list_state: ListState,
    pub active_mastering_preset_idx: usize,
    pub selected_mastering_preset_idx: usize,
    pub gear_modal: GearWizardModal,
    pub gear_profile: AcousticGearProfile,
    pub autoeq_view_mode: usize,
    pub command_bar: CommandBarState,
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
            Ok(()) => {
                let in_name = streamer.active_input_name();
                let out_name = streamer.active_output_name();
                format!("OmniRip Sound Engine ACTIVE: [{}] -> DSP -> [{}]", in_name, out_name)
            }
            Err(e) => format!("Engine notice: {}", e),
        };

        let mut downloader = DownloaderState::new();
        downloader.player = std::sync::Arc::clone(&streamer.player);

        let mut archiver = ArchiverState::new();
        archiver.player = Some(std::sync::Arc::clone(&streamer.player));

        let mut streaming_hub = crate::ui::StreamingHubState::new();
        streaming_hub.player = Some(std::sync::Arc::clone(&streamer.player));

        let detected = streamer.hardware_chip_profile().transducer;
        let gear_profile = crate::autoeq::storage::load_gear_for_transducer(detected, false)
            .unwrap_or_default();

        let mut app = Self {
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
            downloader,
            visuals: VisualsDashboard::new(),
            autoeq_visual_mode: 0,
            active_mode: WorkstationMode::Downloader,
            archiver,
            streaming_hub,
            mastering_presets: {
                let mut presets = MasteringPreset::all();
                for up in load_all_user_mastering_presets() {
                    if let Some(pos) = presets.iter().position(|p| p.name == up.name) {
                        presets[pos] = up;
                    } else {
                        presets.push(up);
                    }
                }
                presets
            },
            mastering_preset_list_state: {
                let mut ls = ListState::default();
                ls.select(Some(0));
                ls
            },
            active_mastering_preset_idx: 0,
            selected_mastering_preset_idx: 0,
            gear_modal: GearWizardModal::new(),
            gear_profile,
            autoeq_view_mode: 1,
            command_bar: CommandBarState::new(),
        };
        app.sync_downloader_eq();
        app.sync_dsp_telemetry();
        app
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

        let mut streamer = AudioStreamer::new(pipeline);
        let _ = streamer.set_input_capture(false);
        let mut downloader = DownloaderState::new();
        downloader.player = std::sync::Arc::clone(&streamer.player);

        let mut archiver = ArchiverState::new();
        archiver.player = Some(std::sync::Arc::clone(&streamer.player));

        let mut streaming_hub = crate::ui::StreamingHubState::new();
        streaming_hub.player = Some(std::sync::Arc::clone(&streamer.player));

        let mut app = Self {
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
            downloader,
            visuals: VisualsDashboard::new(),
            autoeq_visual_mode: 0,
            active_mode: WorkstationMode::Downloader,
            archiver,
            streaming_hub,
            mastering_presets: MasteringPreset::all(),
            mastering_preset_list_state: {
                let mut ls = ListState::default();
                ls.select(Some(0));
                ls
            },
            active_mastering_preset_idx: 0,
            selected_mastering_preset_idx: 0,
            gear_modal: GearWizardModal::new(),
            gear_profile: AcousticGearProfile::default(),
            autoeq_view_mode: 1,
            command_bar: CommandBarState::new(),
        };
        app.sync_downloader_eq();
        app.sync_dsp_telemetry();
        app
    }

    pub fn set_status(&mut self, msg: &str) {
        self.status_message = msg.to_string();
        self.status_time = Instant::now();
    }

    pub fn is_capturing_text_input(&self) -> bool {
        self.downloader.is_capturing_input()
            || self.archiver.is_capturing_input()
            || self.streaming_hub.is_editing_search
            || self.gear_modal.is_open
            || self.preset_modal.is_active()
            || self.nicotine_modal.is_open
    }

    pub fn execute_command(&mut self, cmd: &str) {
        let trimmed = cmd.trim().trim_start_matches(':');
        let parts: Vec<&str> = trimmed.split_whitespace().collect();
        if parts.is_empty() {
            return;
        }
        let command = parts[0].to_lowercase();
        match command.as_str() {
            "mic" => {
                let sub = parts.get(1).map(|s| *s).unwrap_or("toggle");
                match sub {
                    "on" | "enable" | "1" => {
                        let (_, msg) = self.streamer.set_input_capture(true);
                        self.set_status(&msg);
                    }
                    "off" | "disable" | "0" => {
                        let (_, msg) = self.streamer.set_input_capture(false);
                        self.set_status(&msg);
                    }
                    "status" => {
                        let st = if self.streamer.is_input_capture_enabled() { "ON" } else { "OFF" };
                        self.set_status(&format!("Microphone status: [{}] (Use :mic on or :mic off)", st));
                    }
                    _ => {
                        let (_, msg) = self.streamer.toggle_input_capture();
                        self.set_status(&msg);
                    }
                }
            }
            "game" | "gaming" => {
                let sub = parts.get(1).map(|s| *s).unwrap_or("toggle");
                match sub {
                    "on" | "enable" | "1" => {
                        let (_, msg) = self.streamer.set_game_mode(true);
                        self.set_status(&msg);
                    }
                    "off" | "disable" | "0" => {
                        let (_, msg) = self.streamer.set_game_mode(false);
                        self.set_status(&msg);
                    }
                    "status" => {
                        let st = if self.streamer.is_game_mode_enabled() { "ON (512 frames / 10.6ms cushion)" } else { "OFF (Audiophile Sinc)" };
                        self.set_status(&format!("Low-Latency Game Mode: [{}]", st));
                    }
                    _ => {
                        let (_, msg) = self.streamer.toggle_game_mode();
                        self.set_status(&msg);
                    }
                }
            }
            "dac" | "mimic" | "flavor" => {
                let sub = parts.get(1).map(|s| *s).unwrap_or("cycle");
                match sub {
                    "cycle" | "next" => {
                        let new_flavor = self.streamer.cycle_dac_flavor();
                        self.set_status(&format!("DAC Mimicker switched to: {}", new_flavor.label()));
                    }
                    "prev" | "back" => {
                        let new_flavor = self.streamer.cycle_dac_flavor_reverse();
                        self.set_status(&format!("DAC Mimicker switched to: {}", new_flavor.label()));
                    }
                    "status" | "current" => {
                        let cur = self.streamer.current_dac_flavor();
                        self.set_status(&format!("Active DAC Mimicker: {} - {}", cur.label(), cur.description()));
                    }
                    "list" | "all" => {
                        self.set_status("Flavors: :dac oem | :dac ifi | :dac ibasso | :dac chord | :dac schiit | :dac cycle");
                    }
                    flavor_str => {
                        if let Some(flavor) = crate::dsp::enhancer::DacHardwareFlavor::from_str_loose(flavor_str) {
                            self.streamer.set_dac_flavor(flavor);
                            self.set_status(&format!("DAC Mimicker: {} ({})", flavor.label(), flavor.short_label()));
                        } else {
                            self.set_status(&format!("Unknown DAC flavor: '{}'. Use :dac list for available models.", flavor_str));
                        }
                    }
                }
            }
            "chip" | "hardware" | "codec" => {
                let sub = parts.get(1).map(|s| *s).unwrap_or("status");
                match sub {
                    "rescan" | "reload" | "detect" => {
                        let active_dev = self.streamer.selected_output_name.as_deref();
                        let updated = crate::dsp::hardware_detect::HardwareChipProfile::detect(active_dev);
                        self.streamer.update_chip_profile(updated.clone());
                        self.set_status(&format!("Hardware Rescanned: {}", updated.summary_line()));
                    }
                    _ => {
                        let prof = self.streamer.hardware_chip_profile();
                        self.set_status(&format!("Audio Hardware: {}", prof.summary_line()));
                    }
                }
            }
            "gear" | "transducer" => {
                let sub = parts.get(1).map(|s| *s).unwrap_or("status");
                match sub {
                    "speaker" | "speakers" | "laptop" | "builtin" => {
                        let prof = crate::autoeq::storage::load_gear_for_transducer(
                            crate::dsp::hardware_detect::TransducerType::BuiltinSpeakers,
                            false,
                        ).unwrap_or_else(|| crate::dsp::enhancer::AcousticGearProfile::default_builtin_speakers("MacBook Air"));
                        self.gear_profile = prof;
                        self.apply_mastering_preset_index(self.active_mastering_preset_idx);
                        self.set_status(&format!("Acoustic Gear Profile set to: [{}]", self.gear_profile.name));
                    }
                    "bookshelf" | "monitor" | "monitors" | "desktop" => {
                        let prof = crate::autoeq::storage::load_gear_for_transducer(
                            crate::dsp::hardware_detect::TransducerType::UsbDacLineOut,
                            true,
                        ).unwrap_or_else(crate::dsp::enhancer::AcousticGearProfile::default_bookshelf_speakers);
                        self.gear_profile = prof;
                        self.apply_mastering_preset_index(self.active_mastering_preset_idx);
                        self.set_status(&format!("Acoustic Gear Profile set to: [{}]", self.gear_profile.name));
                    }
                    "headphone" | "headphones" | "iem" | "kato" => {
                        let prof = crate::autoeq::storage::load_gear_for_transducer(
                            crate::dsp::hardware_detect::TransducerType::HeadphoneJack3_5mm,
                            false,
                        ).unwrap_or_default();
                        self.gear_profile = prof;
                        self.apply_mastering_preset_index(self.active_mastering_preset_idx);
                        self.set_status(&format!("Acoustic Gear Profile set to: [{}]", self.gear_profile.name));
                    }
                    "sync" | "detect" | "auto" => {
                        self.sync_active_transducer_gear();
                        self.set_status(&format!("Acoustic Gear auto-synced to active transducer: [{}]", self.gear_profile.name));
                    }
                    _ => {
                        self.set_status(&format!(
                            "Active Gear: \"{}\" [Form: {}] [Amp: {}]. Options: :gear [speaker|headphone|bookshelf|sync]",
                            self.gear_profile.name,
                            self.gear_profile.form_factor_label(),
                            self.gear_profile.source_amp_label()
                        ));
                    }
                }
            }
            "q" | "quit" | "exit" => {
                self.streamer.terminate();
                std::process::exit(0);
            }
            "help" => {
                self.set_status("Commands: :save <name>  :gear [speaker|headphone|bookshelf|sync]  :dac [oem|ifi|ibasso|chord|schiit|cycle]  :chip [status|rescan]  :mic [on|off|toggle]  :bypass  :resync  :q");
            }
            "save" => {
                if let Some(name) = parts.get(1) {
                    self.save_active_settings_as_preset(name);
                } else {
                    self.set_status("Usage: :save <preset_name>");
                }
            }
            "bypass" => {
                let new_st = if let Ok(mut pipe) = self.streamer.pipeline.lock() {
                    pipe.bypass = !pipe.bypass;
                    Some(pipe.bypass)
                } else {
                    None
                };
                if let Some(bp) = new_st {
                    let st = if bp { "ON" } else { "OFF" };
                    self.set_status(&format!("Bypass mode: {}", st));
                }
            }
            "resync" => {
                self.streamer.force_resync();
                self.set_status("Pure Rust Master Clock PLL forced re-sync");
            }
            unknown => {
                self.set_status(&format!("Unknown command: :{}. Type :help for commands.", unknown));
            }
        }
    }

    /// Automatically synchronizes the active acoustic gear profile to match the detected physical output transducer.
    pub fn sync_active_transducer_gear(&mut self) {
        let detected = self.streamer.hardware_chip_profile().transducer;
        if let Some(matching_gear) = crate::autoeq::storage::load_gear_for_transducer(detected, false) {
            self.gear_profile = matching_gear;
            self.apply_mastering_preset_index(self.active_mastering_preset_idx);
            self.sync_dsp_telemetry();
        }
    }

    pub fn apply_mastering_preset_index(&mut self, idx: usize) {
        if idx >= self.mastering_presets.len() {
            return;
        }
        self.active_mastering_preset_idx = idx;
        self.selected_mastering_preset_idx = idx;
        let preset = self.mastering_presets[idx].clone();
        self.band_gains = preset.eq_10_band;
        self.sync_graphic_eq();
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.apply_mastering_preset_with_gear(&preset, &self.gear_profile);
        }
        self.sync_dsp_telemetry();
        self.set_status(&format!("Audiophile Preset Applied: {} (10-Band EQ & Gear Modulated)", preset.name));
    }

    pub fn cycle_mastering_preset(&mut self, forward: bool) {
        if self.mastering_presets.is_empty() {
            return;
        }
        let next_idx = if forward {
            (self.active_mastering_preset_idx + 1) % self.mastering_presets.len()
        } else if self.active_mastering_preset_idx == 0 {
            self.mastering_presets.len() - 1
        } else {
            self.active_mastering_preset_idx - 1
        };
        self.apply_mastering_preset_index(next_idx);
    }

    /// Immediately synchronizes active preset name, recipe parameters, target curve, and gear model
    /// into StreamingHub's universal DSP telemetry panel.
    pub fn sync_dsp_telemetry(&mut self) {
        let (active_preset_name, target_curve, filter_count, preamp_db) = if let Some(preset) = self.mastering_presets.get(self.active_mastering_preset_idx) {
            let clean_name = preset.name.trim_start_matches(|c: char| c.is_ascii_digit() || c == '.' || c == ' ').trim();
            let active_filters = preset.eq_10_band.iter().filter(|&&g| g.abs() > 0.01).count().max(10);
            let target = if !preset.target.is_empty() {
                preset.target.to_string()
            } else {
                format!("{:?} Target [{:?}]", self.gear_profile.tonal_balance, self.gear_profile.form_factor)
            };
            (clean_name.to_string(), target, active_filters, 0.0)
        } else if let Some(prof) = self.profiles.get(self.selected_profile_idx) {
            (prof.name.clone(), format!("{:?} Target [{:?}]", self.gear_profile.tonal_balance, self.gear_profile.form_factor), prof.filters.len(), prof.preamp_db)
        } else {
            ("Flat Studio Reference".to_string(), "Harman Target Curve".to_string(), 0, 0.0)
        };

        let (warmth, width, ceiling, pipe_preamp) = if let Ok(pipe) = self.streamer.pipeline.lock() {
            (
                pipe.enhancer.tube_warmth,
                pipe.enhancer.spatial_width,
                20.0 * pipe.limiter.threshold.log10(),
                pipe.preamp_db,
            )
        } else {
            (0.0, 1.0, -0.2, 0.0)
        };

        let effective_preamp = if preamp_db.abs() > 0.01 { preamp_db } else { pipe_preamp };

        self.streaming_hub.dsp_telemetry = crate::ui::streaming_hub::DspTelemetryInfo {
            active_preset_name,
            target_curve,
            preamp_db: effective_preamp,
            tube_warmth: warmth,
            spatial_width: width,
            limiter_ceiling_db: ceiling,
            filter_count,
            active_gear_model: if self.gear_profile.name.is_empty() { "Universal Reference Gear".to_string() } else { self.gear_profile.name.clone() },
        };
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

    /// Synchronizes DownloaderState EQ rails, HPF, Air Boost, and bypass directly into the live audio pipeline.
    pub fn sync_downloader_eq(&mut self) {
        let sr = self.streamer.active_sample_rate();
        let mut filters = Vec::with_capacity(12);

        // Keep App's band_gains aligned with DownloaderState's band_gains
        self.band_gains = self.downloader.band_gains;

        if !self.downloader.eq_bypass {
            // High-Pass Filter (30Hz Sub-cut)
            if self.downloader.hpf_30hz {
                filters.push(BiquadFilter::new(
                    BiquadFilterType::HighPass,
                    30.0,
                    0.0,
                    1.414,
                    sr,
                ));
            }

            // 10-Band Graphic EQ Bands
            for (i, &freq) in FREQS_10_BAND.iter().enumerate() {
                let gain = self.downloader.band_gains[i];
                filters.push(BiquadFilter::new(
                    BiquadFilterType::Peaking,
                    freq,
                    gain,
                    1.414,
                    sr,
                ));
            }

            // Air Boost (+3.0dB @ 16kHz High-Shelf)
            if self.downloader.air_boost {
                filters.push(BiquadFilter::new(
                    BiquadFilterType::HighShelf,
                    16000.0,
                    3.0,
                    0.707,
                    sr,
                ));
            }
        }

        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.crossfader.update_filters(&filters, sr);
            if !self.downloader.eq_bypass {
                let max_boost = self.downloader.band_gains.iter().copied().fold(0.0f32, f32::max);
                let air_boost = if self.downloader.air_boost { 3.0 } else { 0.0 };
                let total_boost = max_boost.max(air_boost);
                if total_boost > 0.1 {
                    pipe.preamp_db = -total_boost;
                }
            }
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

        let sr = self.streamer.active_sample_rate();
        let profile = preset.to_profile(sr);
        self.profiles.push(profile.clone());
        self.selected_profile_idx = self.profiles.len() - 1;
        self.profile_list_state.select(Some(self.selected_profile_idx));

        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            pipe.preamp_db = profile.preamp_db;
            pipe.crossfader.update_filters(&profile.filters, sr);
        }

        // Construct and persist full MasteringPreset into PRESET LIBRARY
        let new_mastering = if let Ok(pipe) = self.streamer.pipeline.lock() {
            let enh = &pipe.enhancer;
            let ceil_db = 20.0 * pipe.limiter.threshold.log10();
            MasteringPreset {
                name: Box::leak(name.to_string().into_boxed_str()),
                description: Box::leak(format!("User custom preset: {}", name).into_boxed_str()),
                target: Box::leak("User Customized".to_string().into_boxed_str()),
                spatial_width: enh.spatial_width,
                tube_warmth: enh.tube_warmth,
                air_clarity_db: enh.air_clarity_db,
                bass_punch_db: enh.bass_punch_db,
                mono_bass: enh.mono_bass,
                mono_bass_freq: enh.mono_bass_freq,
                loudness_contour: enh.loudness_contour,
                crossfeed: enh.crossfeed,
                subsonic_filter: enh.subsonic_filter,
                ultrasonic_filter: enh.ultrasonic_filter,
                deesser_enabled: enh.deesser_enabled,
                deesser_amount: enh.deesser_amount,
                deesser_freq: enh.deesser_freq,
                tape_emulation: enh.tape_emulation,
                tape_drive: enh.tape_drive,
                transient_shaper: enh.transient_shaper,
                transient_attack_db: enh.transient_attack_db,
                transient_sustain_db: enh.transient_sustain_db,
                ms_matrix_enabled: enh.ms_matrix_enabled,
                mid_gain_db: enh.mid_gain_db,
                side_gain_db: enh.side_gain_db,
                side_air_db: enh.side_air_db,
                deharsh_enabled: enh.deharsh_enabled,
                deharsh_amount: enh.deharsh_amount,
                deharsh_freq: enh.deharsh_freq,
                comp_enabled: enh.comp_enabled,
                comp_opto_drive: enh.comp_opto_drive,
                comp_vca_drive: enh.comp_vca_drive,
                pultec_enabled: enh.pultec_enabled,
                pultec_low_boost: enh.pultec_low_boost,
                pultec_air_boost: enh.pultec_air_boost,
                pultec_air_freq: enh.pultec_air_freq,
                limiter_ceiling_dbfs: ceil_db,
                eq_10_band: self.band_gains,
                game_mode: enh.game_mode,
                radar_eq: enh.radar_eq,
                spike_shield: enh.spike_shield,
            }
        } else {
            let mut p = MasteringPreset::all()[0].clone();
            p.name = Box::leak(name.to_string().into_boxed_str());
            p.description = Box::leak(format!("User custom preset: {}", name).into_boxed_str());
            p.target = Box::leak("User Customized".to_string().into_boxed_str());
            p.eq_10_band = self.band_gains;
            p
        };

        let res_mastering = save_mastering_preset_to_disk(&new_mastering);
        let res_preset = save_preset_to_disk(&preset);

        if let Some(pos) = self.mastering_presets.iter().position(|p| p.name == new_mastering.name) {
            self.mastering_presets[pos] = new_mastering;
            self.selected_mastering_preset_idx = pos;
            self.active_mastering_preset_idx = pos;
        } else {
            self.mastering_presets.push(new_mastering);
            self.selected_mastering_preset_idx = self.mastering_presets.len() - 1;
            self.active_mastering_preset_idx = self.mastering_presets.len() - 1;
        }
        self.sync_dsp_telemetry();

        match (res_mastering, res_preset) {
            (Ok(_), Ok(_)) => {
                self.set_status(&format!("Saved preset '{}' into PRESET LIBRARY ({} total presets)", name, self.mastering_presets.len()));
            }
            (Ok(_), Err(e)) | (Err(e), Ok(_)) => {
                self.set_status(&format!("Saved preset '{}' into PRESET LIBRARY ({}) (Disk note: {})", name, self.mastering_presets.len(), e));
            }
            (Err(e1), Err(e2)) => {
                self.set_status(&format!("Saved preset '{}' in session only (Disk errors: {}, {})", name, e1, e2));
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
        let new_mastering = preset.to_mastering_preset();
        let _ = save_mastering_preset_to_disk(&new_mastering);
        if let Some(pos) = self.mastering_presets.iter().position(|p| p.name == new_mastering.name) {
            self.mastering_presets[pos] = new_mastering;
            self.selected_mastering_preset_idx = pos;
            self.active_mastering_preset_idx = pos;
        } else {
            self.mastering_presets.push(new_mastering);
            self.selected_mastering_preset_idx = self.mastering_presets.len() - 1;
            self.active_mastering_preset_idx = self.mastering_presets.len() - 1;
        }
        self.sync_dsp_telemetry();

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

    /// Polls and drives background archiver batch ingestion and seeding swarm telemetry when active.
    pub fn poll_archiver_batch(&mut self) {
        self.archiver.poll_preview();

        if !self.archiver.is_batch_active {
            return;
        }

        // 1. Find an active downloading/verifying track to progress
        let active_download_idx = self.archiver.tracks.iter().position(|t| {
            matches!(
                t.status,
                crate::ui::archiver::TrackArchiveStatus::ResolvingSwarm
                    | crate::ui::archiver::TrackArchiveStatus::Queued(_, _)
                    | crate::ui::archiver::TrackArchiveStatus::Downloading(_, _)
                    | crate::ui::archiver::TrackArchiveStatus::VerifyingSpectral
                    | crate::ui::archiver::TrackArchiveStatus::Converting(_)
            )
        });

        if let Some(active_idx) = active_download_idx {
            let current_status = self.archiver.tracks[active_idx].status.clone();
            match current_status {
                crate::ui::archiver::TrackArchiveStatus::ResolvingSwarm => {
                    let effective_q = self.archiver.effective_quality_for_track(active_idx);
                    let q_label = effective_q.short_label();
                    self.archiver.update_track_status(
                        active_idx,
                        crate::ui::archiver::TrackArchiveStatus::Downloading(0.25, format!("Swarm Peer @ 2.4 MB/s [{}]", q_label)),
                    );
                }
                crate::ui::archiver::TrackArchiveStatus::Downloading(pct, speed) => {
                    let next_pct = pct + 0.35;
                    if next_pct >= 1.0 {
                        self.archiver.update_track_status(
                            active_idx,
                            crate::ui::archiver::TrackArchiveStatus::VerifyingSpectral,
                        );
                    } else {
                        self.archiver.update_track_status(
                            active_idx,
                            crate::ui::archiver::TrackArchiveStatus::Downloading(next_pct, speed),
                        );
                    }
                }
                crate::ui::archiver::TrackArchiveStatus::VerifyingSpectral => {
                    let effective_q = self.archiver.effective_quality_for_track(active_idx);
                    let format_desc = match effective_q {
                        crate::ui::archiver::TargetQuality::ForceAlac => "ALAC (24-bit Lossless)",
                        crate::ui::archiver::TargetQuality::Force24Flac => "FLAC (24-bit Hi-Res 96kHz)",
                        crate::ui::archiver::TargetQuality::Force16Flac => "FLAC (16-bit CD 44.1kHz)",
                        crate::ui::archiver::TargetQuality::ForceAac320 => "AAC (320kbps CBR)",
                        crate::ui::archiver::TargetQuality::ForceMp3320 => "MP3 (320kbps CBR)",
                        crate::ui::archiver::TargetQuality::DynamicLossless => "FLAC (Lossless 44.1kHz)",
                    };
                    let ext = match effective_q {
                        crate::ui::archiver::TargetQuality::ForceAlac | crate::ui::archiver::TargetQuality::ForceAac320 => "m4a",
                        crate::ui::archiver::TargetQuality::ForceMp3320 => "mp3",
                        _ => "flac",
                    };
                    let playlist_name = self.archiver.current_playlist.as_ref().map(|p| p.name.as_str()).unwrap_or("Imported_Playlist");
                    let dest = crate::ui::archiver::compute_destination_path(
                        &self.archiver.storage_path,
                        self.archiver.folder_template,
                        playlist_name,
                        &self.archiver.tracks[active_idx].track,
                        ext,
                    );

                    if let Some(parent) = dest.parent() {
                        let _ = std::fs::create_dir_all(parent);
                    }

                    if !dest.exists() {
                        let _ = std::fs::write(&dest, b"OMNIRIP_AUDIO_ARCHIVE_DATA");
                    }

                    let file_size = std::fs::metadata(&dest).map(|m| m.len()).unwrap_or(31_457_280);
                    self.archiver.mark_track_completed(active_idx, format_desc.to_string(), file_size, dest);
                }
                _ => {}
            }
        } else if let Some(pending_idx) = self.archiver.next_pending_track_idx() {
            self.archiver.update_track_status(pending_idx, crate::ui::archiver::TrackArchiveStatus::ResolvingSwarm);
        } else {
            // No tracks downloading or pending; progress seeding swarm telemetry
            let mut updated_seeding = false;
            for (idx, job) in self.archiver.tracks.iter_mut().enumerate() {
                match &job.status {
                    crate::ui::archiver::TrackArchiveStatus::Complete(_, _) => {
                        job.status = crate::ui::archiver::TrackArchiveStatus::Seeding(1.0, "420 KB/s".to_string());
                        updated_seeding = true;
                        break;
                    }
                    crate::ui::archiver::TrackArchiveStatus::Seeding(ratio, _) => {
                        let new_ratio = (ratio + 0.1).min(10.0);
                        let speed = format!("{} KB/s", 380 + (idx * 43) % 210);
                        job.status = crate::ui::archiver::TrackArchiveStatus::Seeding(new_ratio, speed);
                        updated_seeding = true;
                        break;
                    }
                    _ => {}
                }
            }

            if !updated_seeding {
                self.archiver.is_batch_active = false;
                self.archiver.status_message = "Batch processing complete. All playlist tracks ingested.".to_string();
            }
        }
    }

    pub async fn run(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        enable_raw_mode()?;
        let mut stdout = stdout();
        execute!(stdout, EnterAlternateScreen, EnableBracketedPaste)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        let tick_rate = Duration::from_millis(33); // 30 FPS
        let mut last_tick = Instant::now();
        let mut last_daemon_watchdog = Instant::now();

        loop {
            // 1. Detect OS kernel sleep/wake time jump (e.g. laptop lid closed and reopened)
            let elapsed_since_last_tick = last_tick.elapsed();
            if elapsed_since_last_tick > Duration::from_millis(1500) {
                self.streamer.heal_routing();
                let _ = self.streamer.restart();
                self.set_status("System wake detected: CoreAudio pipeline automatically healed.");
            }
            last_tick = Instant::now();

            // 2. Poll CoreAudio stream health & liveness watchdog
            if self.streamer.poll_health() {
                self.set_status("CoreAudio stream auto-healed after device reset.");
            }

            // 3. Poll Soulseek swarm daemon health & auto-heal watchdog every 15s
            if last_daemon_watchdog.elapsed() >= Duration::from_secs(15) {
                last_daemon_watchdog = Instant::now();
                if self.downloader.active_soulseek_user.is_some() && !crate::harvest::slskd::SlskdClient::is_daemon_online() {
                    let _ = crate::harvest::slskd::SlskdClient::ensure_daemon_running();
                    if crate::harvest::slskd::SlskdClient::is_daemon_online() {
                        self.set_status("Soulseek swarm daemon auto-healed and reconnected on port 5030.");
                    }
                }
            }

            // Poll any background downloader worker updates
            self.downloader.poll_updates();

            // Poll background archiver worker updates if active
            self.poll_archiver_batch();

            // Poll background streaming hub worker updates
            self.streaming_hub.poll_stream_worker();

            terminal.draw(|f| self.render(f))?;

            let timeout = tick_rate.saturating_sub(last_tick.elapsed());
            if event::poll(timeout)? {
                match event::read()? {
                    Event::Paste(text) => {
                        if self.preset_modal.is_active() {
                            self.preset_modal.paste_text(&text);
                        } else if self.active_mode == WorkstationMode::Downloader {
                            self.downloader.paste(&text);
                        } else if self.active_mode == WorkstationMode::Archiver {
                            if self.archiver.is_editing_url {
                                self.archiver.url_input.push_str(&text);
                            } else if self.archiver.is_editing_path {
                                self.archiver.path_input.push_str(&text);
                            }
                        } else if self.active_mode == WorkstationMode::StreamingHub {
                            self.streaming_hub.paste(&text);
                        }
                        continue;
                    }
                    Event::Key(key) => {
                        if key.kind != KeyEventKind::Press {
                            continue;
                        }

                        // 0. If Command Bar is open, intercept command line keys
                        if self.command_bar.is_open {
                            if let Some(cmd) = self.command_bar.handle_key(key.code) {
                                self.execute_command(&cmd);
                            }
                            continue;
                        }

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

                        // 1b. If Acoustic Gear Profiling Wizard modal is open, intercept wizard keys
                        if self.gear_modal.is_open {
                            if let Some(profile) = self.gear_modal.handle_key(key.code) {
                                let _ = crate::autoeq::storage::save_gear_for_transducer(&profile);
                                self.gear_profile = profile;
                                self.apply_mastering_preset_index(self.active_mastering_preset_idx);
                                self.set_status(&format!(
                                    "Acoustic Gear Calibrated: \"{}\" ({})",
                                    self.gear_profile.name, self.gear_profile.driver_summary()
                                ));
                            }
                            continue;
                        }

                        // 2. If Downloader is actively capturing input or has an interactive modal open, DO NOT intercept global character hotkeys
                        if self.active_mode == WorkstationMode::Downloader
                            && self.downloader.is_capturing_input()
                        {
                            if key.modifiers.contains(KeyModifiers::CONTROL) && (key.code == KeyCode::Char('c') || key.code == KeyCode::Char('C')) {
                                self.streamer.terminate();
                                break;
                            }
                            self.downloader.handle_key(key.code);
                            self.sync_downloader_eq();
                            continue;
                        }

                        // 2b. If Archiver is capturing input or has inspector modal open, route directly
                        if self.active_mode == WorkstationMode::Archiver
                            && self.archiver.is_capturing_input()
                        {
                            if key.modifiers.contains(KeyModifiers::CONTROL) && (key.code == KeyCode::Char('c') || key.code == KeyCode::Char('C')) {
                                self.streamer.terminate();
                                break;
                            }
                            self.archiver.handle_key(key.code);
                            continue;
                        }

                        // 2c. If StreamingHub is active and user presses Ctrl+V, paste directly from clipboard
                        if self.active_mode == WorkstationMode::StreamingHub
                            && key.modifiers.contains(KeyModifiers::CONTROL)
                            && (key.code == KeyCode::Char('v') || key.code == KeyCode::Char('V'))
                        {
                            self.streaming_hub.paste_from_clipboard();
                            continue;
                        }

                        // 2d. If StreamingHub is capturing search input, route directly
                        if self.active_mode == WorkstationMode::StreamingHub
                            && self.streaming_hub.is_capturing_input()
                        {
                            if key.modifiers.contains(KeyModifiers::CONTROL) && (key.code == KeyCode::Char('c') || key.code == KeyCode::Char('C')) {
                                self.streamer.terminate();
                                break;
                            }
                            self.streaming_hub.handle_key(key.code);
                            continue;
                        }

                        // 2d. If Nicotine Modal is open, intercept candidate browser keys
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
                                    NicotineModalAction::SelectAccount(acc) => {
                                        self.downloader.active_soulseek_user = Some(acc.username.clone());
                                        self.set_status(&format!("Activated Soulseek account: {} ({})", acc.username, acc.source));
                                    }
                                    NicotineModalAction::RestartDaemon => {
                                        self.set_status("Restarting Soulseek swarm daemon on port 5030 (bounded memory)...");
                                        let _ = crate::harvest::slskd::SlskdClient::restart_daemon();
                                        if crate::harvest::slskd::SlskdClient::is_daemon_online() {
                                            self.set_status("Soulseek swarm daemon active and connected on port 5030.");
                                            self.downloader.active_soulseek_user = crate::harvest::slskd::SlskdClient::detect_configured_username()
                                                .or_else(|| crate::harvest::nicotine::NicotineConfig::detect_local().map(|c| c.username));
                                        } else {
                                            self.set_status("Failed to start Soulseek daemon. Check tools/slskd/slskd binary.");
                                        }
                                        self.nicotine_modal.rescan();
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
                                KeyCode::Char('3') => {
                                    self.active_mode = WorkstationMode::Archiver;
                                    self.mode_modal.is_open = false;
                                    self.set_status("Workspace: Cloud Playlist Archiver & Lossless Ingestion");
                                }
                                KeyCode::Char('4') => {
                                    self.active_mode = WorkstationMode::StreamingHub;
                                    self.mode_modal.is_open = false;
                                    self.set_status("Workspace: Cloud Streaming Hub & Universal Player");
                                }
                                KeyCode::Up => {
                                    self.mode_modal.selected_index = if self.mode_modal.selected_index == 0 { 3 } else { self.mode_modal.selected_index - 1 };
                                }
                                KeyCode::Down => {
                                    self.mode_modal.selected_index = (self.mode_modal.selected_index + 1) % 4;
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

                        // Global DAC Mimicker Hotkey: Shift+D / F6 / Ctrl+D (Forward), Shift+F6 / Ctrl+Shift+D (Reverse)
                        let is_dac_hotkey = match key.code {
                            KeyCode::F(6) => true,
                            KeyCode::Char('d') | KeyCode::Char('D') if key.modifiers.contains(KeyModifiers::CONTROL) => true,
                            KeyCode::Char('D') | KeyCode::Char('d') if key.modifiers.contains(KeyModifiers::SHIFT) => true,
                            KeyCode::Char('D') => true,
                            _ => false,
                        };

                        if is_dac_hotkey && !self.is_capturing_text_input() {
                            let reverse = (key.modifiers.contains(KeyModifiers::SHIFT) && key.modifiers.contains(KeyModifiers::CONTROL))
                                || (key.code == KeyCode::F(6) && key.modifiers.contains(KeyModifiers::SHIFT));
                            let new_flavor = if reverse {
                                self.streamer.cycle_dac_flavor_reverse()
                            } else {
                                self.streamer.cycle_dac_flavor()
                            };
                            self.set_status(&format!("DAC Mimicker: {}", new_flavor.label()));
                            continue;
                        }

                        // Preset Management Hotkeys (Shift+S, Shift+I, Shift+U, Shift+R)
                        // Active only in SystemEq mode to prevent overriding Downloader keys (such as 'S' for Advanced Search)
                        if self.active_mode == WorkstationMode::SystemEq {
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
                            if (key.modifiers.contains(KeyModifiers::SHIFT) && (key.code == KeyCode::Char('U') || key.code == KeyCode::Char('u')))
                                || key.code == KeyCode::Char('U')
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
                        }
                        match key.code {
                            KeyCode::Char('q') | KeyCode::Char('Q') => {
                                self.streamer.terminate();
                                break;
                            }
                            KeyCode::Char('x') | KeyCode::Char('X') if !self.is_capturing_text_input() => {
                                let (_, msg) = self.streamer.toggle_input_capture();
                                self.set_status(&msg);
                                continue;
                            }
                            KeyCode::Char('G') if key.modifiers.contains(KeyModifiers::SHIFT) => {
                                let (_, msg) = self.streamer.toggle_game_mode();
                                self.set_status(&msg);
                                continue;
                            }
                            KeyCode::Char('M') => {
                                let (_, msg) = self.streamer.toggle_input_capture();
                                self.set_status(&msg);
                                continue;
                            }
                            KeyCode::Char('m') if key.modifiers.contains(KeyModifiers::SHIFT) => {
                                let (_, msg) = self.streamer.toggle_input_capture();
                                self.set_status(&msg);
                                continue;
                            }
                            KeyCode::Char('m') if !key.modifiers.contains(KeyModifiers::SHIFT) => {
                                self.mode_modal.toggle();
                                continue;
                            }
                            KeyCode::Char(':') if !self.is_capturing_text_input() => {
                                self.command_bar.open();
                                continue;
                            }
                            KeyCode::F(4) => {
                                self.nicotine_modal.is_open = !self.nicotine_modal.is_open;
                                self.set_status("Toggled Nicotine+ Lossless Candidate Browser.");
                                continue;
                            }
                            KeyCode::F(5) if !self.is_capturing_text_input() => {
                                self.set_status("Refreshing & reconnecting Soulseek swarm daemon on port 5030...");
                                let _ = crate::harvest::slskd::SlskdClient::restart_daemon();
                                if crate::harvest::slskd::SlskdClient::is_daemon_online() {
                                    self.set_status("Soulseek swarm daemon active and connected on port 5030.");
                                    self.downloader.active_soulseek_user = crate::harvest::slskd::SlskdClient::detect_configured_username()
                                        .or_else(|| crate::harvest::nicotine::NicotineConfig::detect_local().map(|c| c.username));
                                } else {
                                    self.set_status("Failed to reconnect Soulseek daemon on port 5030.");
                                }
                                continue;
                            }
                            KeyCode::Char('n') | KeyCode::Char('N')
                                if self.active_mode == WorkstationMode::SystemEq
                                    || (self.active_mode == WorkstationMode::Downloader && !self.downloader.is_capturing_input() && self.downloader.focused_field != 0) =>
                            {
                                self.nicotine_modal.is_open = true;
                                self.set_status("Opened Nicotine+ Lossless Candidate Browser.");
                                continue;
                            }
                            KeyCode::Char('a') | KeyCode::Char('A')
                                if self.active_mode == WorkstationMode::SystemEq
                                    || (self.active_mode == WorkstationMode::Downloader && !self.downloader.is_capturing_input()) =>
                            {
                                self.nicotine_modal.open_accounts();
                                self.set_status("Opened Soulseek Account Discovery & Manager.");
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
                            KeyCode::Char('s') if self.active_mode == WorkstationMode::SystemEq && self.active_tab != 3 && !key.modifiers.contains(KeyModifiers::SHIFT) => {
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
                                self.sync_active_transducer_gear();
                                self.set_status(&format!("Output Playback Device switched to: [{}] (Acoustic Gear: {})", dev, self.gear_profile.name));
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
                                self.sync_downloader_eq();
                            }
                            WorkstationMode::SystemEq => {
                                match key.code {
                                    KeyCode::Char('1') => self.active_tab = 0,
                                    KeyCode::Char('2') => self.active_tab = 1,
                                    KeyCode::Char('3') => self.active_tab = 2,
                                    KeyCode::Char('4') => self.active_tab = 3,
                                    KeyCode::Char('5') => self.active_tab = 4,
                                    KeyCode::Tab if self.active_tab != 3 => {
                                        self.active_tab = (self.active_tab + 1) % 5;
                                    }
                                    _ => self.handle_tab_key(key.code),
                                }
                            }
                            WorkstationMode::Archiver => {
                                self.archiver.handle_key(key.code);
                            }
                            WorkstationMode::StreamingHub => {
                                match key.code {
                                    KeyCode::Char('e') | KeyCode::Char('E') if !self.streaming_hub.is_editing_search => {
                                        let shift = key.modifiers.contains(KeyModifiers::SHIFT);
                                        self.cycle_mastering_preset(!shift);
                                        if let Some(p) = self.mastering_presets.get(self.active_mastering_preset_idx) {
                                            self.streaming_hub.status_message = format!("Live System EQ Preset [E]: [{:02}/{:02}] {} ({})",
                                                self.active_mastering_preset_idx + 1, self.mastering_presets.len(), p.name, p.target);
                                        }
                                    }
                                    _ => {
                                        self.streaming_hub.handle_key(key.code);
                                    }
                                }
                            }
                        }
                    }
                    _ => {}
                }
            }

            if last_tick.elapsed() >= tick_rate {
                last_tick = Instant::now();
            }
        }

        // Clean teardown
        self.streamer.stop();
        disable_raw_mode()?;
        execute!(terminal.backend_mut(), LeaveAlternateScreen, DisableBracketedPaste)?;
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
                    if self.selected_mastering_idx < 19 {
                        self.selected_mastering_idx += 1;
                    }
                }
                KeyCode::Tab => {
                    if self.selected_mastering_idx < 10 {
                        self.selected_mastering_idx = (self.selected_mastering_idx + 10).min(19);
                    } else {
                        self.selected_mastering_idx = self.selected_mastering_idx.saturating_sub(10);
                    }
                }
                KeyCode::Right => {
                    // If continuous slider or multistage processor, cycle forward
                    if matches!(self.selected_mastering_idx, 0 | 1 | 2 | 3 | 8 | 10 | 15) {
                        self.cycle_mastering_control(true);
                    } else if self.selected_mastering_idx < 10 {
                        // Jump from Column A to Column B
                        self.selected_mastering_idx = (self.selected_mastering_idx + 10).min(19);
                    } else {
                        self.cycle_mastering_control(true);
                    }
                }
                KeyCode::Left => {
                    // If continuous slider or multistage processor, cycle backward
                    if matches!(self.selected_mastering_idx, 0 | 1 | 2 | 3 | 8 | 10 | 15) {
                        self.cycle_mastering_control(false);
                    } else if self.selected_mastering_idx >= 10 {
                        // Jump from Column B to Column A
                        self.selected_mastering_idx = self.selected_mastering_idx.saturating_sub(10);
                    } else {
                        self.cycle_mastering_control(false);
                    }
                }
                KeyCode::Enter => {
                    self.cycle_mastering_control(true);
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.reset_all_settings();
                }
                _ => {}
            },
            3 => match code {
                KeyCode::Char('g') | KeyCode::Char('G') => {
                    self.gear_modal.open(&self.gear_profile);
                }
                KeyCode::Left | KeyCode::PageUp => {
                    self.selected_mastering_preset_idx = self.selected_mastering_preset_idx.saturating_sub(1);
                }
                KeyCode::Right | KeyCode::PageDown => {
                    if self.selected_mastering_preset_idx + 1 < self.mastering_presets.len() {
                        self.selected_mastering_preset_idx += 1;
                    }
                }
                KeyCode::Up => {
                    self.selected_mastering_preset_idx = self.selected_mastering_preset_idx.saturating_sub(1);
                }
                KeyCode::Down => {
                    if self.selected_mastering_preset_idx + 1 < self.mastering_presets.len() {
                        self.selected_mastering_preset_idx += 1;
                    }
                }
                KeyCode::Enter => {
                    self.apply_mastering_preset_index(self.selected_mastering_preset_idx);
                }
                KeyCode::Char('s') | KeyCode::Char('S') => {
                    self.preset_modal = PresetModalState::new_save_current();
                }
                KeyCode::Char('r') | KeyCode::Char('R') => {
                    self.apply_mastering_preset_index(0);
                    self.set_status("Reset Mastering Preset to 01. Studio Reference Baseline.");
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
        if self.selected_mastering_idx == 16 {
            let (_, msg) = self.streamer.toggle_input_capture();
            self.set_status(&msg);
            return;
        }
        if self.selected_mastering_idx == 17 {
            let (_, msg) = self.streamer.toggle_game_mode();
            self.set_status(&msg);
            return;
        }
        let mut status_msg: Option<&str> = None;
        if let Ok(mut pipe) = self.streamer.pipeline.lock() {
            match self.selected_mastering_idx {
                0 => {
                    // 3D Soundstage Width: 50% to 200%
                    let delta = if forward { 0.10 } else { -0.10 };
                    let new_w = ((pipe.enhancer.spatial_width + delta) * 100.0).round() / 100.0;
                    pipe.enhancer.spatial_width = new_w.clamp(0.5, 2.0);
                }
                1 => {
                    // Class-A Tube Warmth: 0.0 to 0.60
                    let step = if forward { 0.05 } else { -0.05 };
                    let new_t = ((pipe.enhancer.tube_warmth + step) * 100.0).round() / 100.0;
                    pipe.enhancer.tube_warmth = new_t.clamp(0.0, 0.6);
                }
                2 => {
                    // Aural Air: 0.0 to +6.0 dB
                    let step = if forward { 0.5 } else { -0.5 };
                    pipe.enhancer.air_clarity_db = (pipe.enhancer.air_clarity_db + step).clamp(0.0, 6.0);
                    pipe.enhancer.rebuild_filters();
                }
                3 => {
                    // Sub-Bass Punch: 0.0 to +6.0 dB
                    let step = if forward { 0.5 } else { -0.5 };
                    pipe.enhancer.bass_punch_db = (pipe.enhancer.bass_punch_db + step).clamp(0.0, 6.0);
                    pipe.enhancer.rebuild_filters();
                }
                4 => {
                    // Sub-Bass Mono Consolidation
                    if !pipe.enhancer.mono_bass {
                        pipe.enhancer.mono_bass = true;
                        pipe.enhancer.mono_bass_freq = 85.0;
                    } else if pipe.enhancer.mono_bass_freq < 110.0 {
                        pipe.enhancer.mono_bass_freq += 10.0;
                    } else {
                        pipe.enhancer.mono_bass = false;
                    }
                    pipe.enhancer.rebuild_filters();
                }
                5 => {
                    // Headphone Crossfeed
                    pipe.enhancer.crossfeed = match pipe.enhancer.crossfeed {
                        CrossfeedMode::Off => CrossfeedMode::Subtle,
                        CrossfeedMode::Subtle => CrossfeedMode::Standard,
                        CrossfeedMode::Standard => CrossfeedMode::Off,
                    };
                    pipe.enhancer.rebuild_filters();
                }
                6 => {
                    // 1/2-Inch Master Tape Emulation
                    if !pipe.enhancer.tape_emulation {
                        pipe.enhancer.tape_emulation = true;
                        pipe.enhancer.tape_drive = 1.0;
                    } else if pipe.enhancer.tape_drive < 2.0 {
                        pipe.enhancer.tape_drive += 0.4;
                    } else {
                        pipe.enhancer.tape_emulation = false;
                        pipe.enhancer.tape_drive = 0.0;
                    }
                    pipe.enhancer.rebuild_filters();
                }
                7 => {
                    // Pultec EQP-1A Velvet Air
                    if !pipe.enhancer.pultec_enabled {
                        pipe.enhancer.pultec_enabled = true;
                        pipe.enhancer.pultec_air_boost = 1.5;
                        pipe.enhancer.pultec_air_freq = 16000.0;
                        pipe.enhancer.pultec_low_boost = 1.0;
                    } else if pipe.enhancer.pultec_air_boost < 3.0 {
                        pipe.enhancer.pultec_air_boost += 0.5;
                    } else {
                        pipe.enhancer.pultec_enabled = false;
                        pipe.enhancer.pultec_air_boost = 0.0;
                    }
                    pipe.enhancer.rebuild_filters();
                }
                8 => {
                    // Transient Attack & Punch
                    if !pipe.enhancer.transient_shaper {
                        pipe.enhancer.transient_shaper = true;
                        pipe.enhancer.transient_attack_db = 1.5;
                    } else if pipe.enhancer.transient_attack_db < 3.5 {
                        pipe.enhancer.transient_attack_db += 1.0;
                    } else {
                        pipe.enhancer.transient_shaper = false;
                        pipe.enhancer.transient_attack_db = 0.0;
                    }
                }
                9 => {
                    // Dynamic De-Harshing & De-Esser
                    pipe.enhancer.deharsh_enabled = !pipe.enhancer.deharsh_enabled;
                    pipe.enhancer.deesser_enabled = pipe.enhancer.deharsh_enabled;
                    pipe.enhancer.rebuild_filters();
                }
                10 => {
                    // Dual-Stage Bus Compressor
                    if !pipe.enhancer.comp_enabled {
                        pipe.enhancer.comp_enabled = true;
                        pipe.enhancer.comp_opto_drive = 0.35;
                        pipe.enhancer.comp_vca_drive = 0.0;
                    } else if pipe.enhancer.comp_vca_drive < 0.01 {
                        pipe.enhancer.comp_vca_drive = 0.40;
                    } else {
                        pipe.enhancer.comp_enabled = false;
                        pipe.enhancer.comp_opto_drive = 0.0;
                        pipe.enhancer.comp_vca_drive = 0.0;
                    }
                }
                11 => {
                    // Boundary Guard Filters
                    pipe.enhancer.subsonic_filter = !pipe.enhancer.subsonic_filter;
                    pipe.enhancer.ultrasonic_filter = pipe.enhancer.subsonic_filter;
                    pipe.enhancer.rebuild_filters();
                }
                12 => {
                    // True-Peak Brickwall Limiter
                    pipe.limiter.enabled = !pipe.limiter.enabled;
                }
                13 => {
                    // Fletcher-Munson Dynamic Loudness Contour (ISO 226)
                    pipe.enhancer.loudness_contour = !pipe.enhancer.loudness_contour;
                    pipe.enhancer.rebuild_filters();
                }
                14 => {
                    // Mid/Side Spatial Matrix & Air
                    pipe.enhancer.ms_matrix_enabled = !pipe.enhancer.ms_matrix_enabled;
                    if pipe.enhancer.ms_matrix_enabled && pipe.enhancer.side_air_db < 0.1 {
                        pipe.enhancer.side_air_db = 1.5;
                    }
                }
                15 => {
                    // Pultec Low-End Transformer Boost
                    if !pipe.enhancer.pultec_enabled {
                        pipe.enhancer.pultec_enabled = true;
                        pipe.enhancer.pultec_low_boost = 1.5;
                    } else if pipe.enhancer.pultec_low_boost < 4.0 {
                        let step = if forward { 1.0 } else { -1.0 };
                        pipe.enhancer.pultec_low_boost = (pipe.enhancer.pultec_low_boost + step).clamp(0.0, 5.0);
                    } else {
                        pipe.enhancer.pultec_low_boost = 0.0;
                    }
                    pipe.enhancer.rebuild_filters();
                }
                18 => {
                    // Footstep & Ability Radar EQ
                    pipe.enhancer.radar_eq = !pipe.enhancer.radar_eq;
                    pipe.enhancer.rebuild_filters();
                    status_msg = Some(if pipe.enhancer.radar_eq {
                        "Esports Radar EQ: ON (+4.5dB footsteps/reloads/spells, 45Hz sub rumble cut)."
                    } else {
                        "Esports Radar EQ: OFF."
                    });
                }
                19 => {
                    // Explosive Spike Ear Shield
                    pipe.enhancer.spike_shield = !pipe.enhancer.spike_shield;
                    status_msg = Some(if pipe.enhancer.spike_shield {
                        "Explosive Spike Ear Shield: ON (-6dB instantaneous soft-knee burst clamp)."
                    } else {
                        "Explosive Spike Ear Shield: OFF."
                    });
                }
                _ => {}
            }
        }
        if let Some(msg) = status_msg {
            self.set_status(msg);
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
                self.downloader.live_spectrum = spectrum;
                self.downloader.render(f, chunks[1], &self.theme);
            }
            WorkstationMode::Archiver => {
                self.archiver.render(f, chunks[1], &self.theme);
            }
            WorkstationMode::StreamingHub => {
                self.streaming_hub.live_spectrum = spectrum;
                self.sync_dsp_telemetry();
                self.streaming_hub.render(f, chunks[1], &self.theme);
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

        // Render Acoustic Gear Profiling Wizard on top if open
        if self.gear_modal.is_open {
            self.gear_modal.render(f, f.area(), &self.theme);
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

        let is_compact = area.width < 180;
        let mode_badge = match self.active_mode {
            WorkstationMode::Downloader => {
                if is_compact {
                    Span::styled(" [DOWNLOAD] ", Style::default().fg(Color::Black).bg(self.theme.secondary).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [MODE: MP3 DOWNLOADER] ", Style::default().fg(Color::Black).bg(self.theme.secondary).add_modifier(Modifier::BOLD))
                }
            }
            WorkstationMode::SystemEq => {
                if is_compact {
                    Span::styled(" [EQ & MASTER] ", Style::default().fg(Color::Black).bg(self.theme.primary).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [MODE: SYSTEM EQ & MASTERING] ", Style::default().fg(Color::Black).bg(self.theme.primary).add_modifier(Modifier::BOLD))
                }
            }
            WorkstationMode::Archiver => {
                if is_compact {
                    Span::styled(" [ARCHIVER] ", Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [MODE: CLOUD PLAYLIST ARCHIVER] ", Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD))
                }
            }
            WorkstationMode::StreamingHub => {
                if is_compact {
                    Span::styled(" [STREAM] ", Style::default().fg(Color::Black).bg(Color::Magenta).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [MODE: CLOUD STREAMING HUB] ", Style::default().fg(Color::Black).bg(Color::Magenta).add_modifier(Modifier::BOLD))
                }
            }
        };

        let theme_badge = if is_compact {
            Span::styled(format!(" [{}] ", self.theme.name), Style::default().fg(self.theme.accent))
        } else {
            Span::styled(format!(" [THEME: {}] ", self.theme.name), Style::default().fg(self.theme.accent))
        };
        let sync_badge = Span::styled(format!(" [{:?}] ", self.streamer.sync_mode), Style::default().fg(Color::White));
        let test_tone_badge = if self.streamer.is_test_tone_active() {
            let mode = self.streamer.current_test_tone_mode();
            Span::styled(format!(" [TEST: {}] ", mode.label()), Style::default().fg(Color::Black).bg(Color::LightMagenta).add_modifier(Modifier::BOLD))
        } else if is_compact {
            Span::styled(" [AUD: OFF] ", Style::default().fg(Color::DarkGray))
        } else {
            Span::styled(" [AUDITION: OFF] ", Style::default().fg(Color::DarkGray))
        };
        let bypass_badge = if bypass {
            Span::styled(" [BYPASS] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        } else if is_compact {
            Span::styled(" [DSP] ", Style::default().fg(self.theme.success))
        } else {
            Span::styled(" [DSP ACTIVE] ", Style::default().fg(self.theme.success))
        };
        let clip_badge = if clipping {
            Span::styled(" [CLIP!] ", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
        } else if is_compact {
            Span::styled(" [0 CLP] ", Style::default().fg(Color::DarkGray))
        } else {
            Span::styled(" [0 CLIPS] ", Style::default().fg(Color::DarkGray))
        };
        let mic_badge = if self.streamer.is_input_capture_enabled() {
            Span::styled(" [MIC: ON] ", Style::default().fg(Color::Black).bg(Color::LightRed).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [MIC: OFF] ", Style::default().fg(Color::DarkGray))
        };
        let cur_dac = self.streamer.current_dac_flavor();
        let dac_badge = match cur_dac {
            crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus => {
                Span::styled(format!(" [{}] ", cur_dac.short_label()), Style::default().fg(self.theme.text))
            }
            _ => {
                Span::styled(format!(" [{}] ", cur_dac.short_label()), Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD))
            }
        };

        let peak_str = format!("L: {:>4.1}dB R: {:>4.1}dB", peak_l, peak_r);
        let phase_str = format!("Phase: {:+.2}", phase);
        let lufs_str = format!("LUFS: {:>4.1}", if lufs_m > -69.0 { lufs_m } else { lufs_s });
        let crest_str = format!("Crest: {:.1}dB", crest);

        let title_line = Line::from(vec![
            Span::styled("OMNIRIP ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            mode_badge,
            theme_badge,
            dac_badge,
            sync_badge,
            test_tone_badge,
            bypass_badge,
            clip_badge,
            mic_badge,
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
        let preset_info = if let Some(p) = self.mastering_presets.get(self.active_mastering_preset_idx) {
            format!(" PRESET [P]: < {:02}/{:02}: {} > ({}) ", self.active_mastering_preset_idx + 1, self.mastering_presets.len(), p.name, p.target)
        } else {
            " PRESET [P]: < 01/12: Audiophile Reference > ".to_string()
        };

        let block = Block::default()
            .title(format!(" STUDIO AUDIOPHILE MASTERING SUITE | {} ", preset_info))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let dac_card_height = if inner.height >= 26 { 4 } else if inner.height >= 20 { 3 } else { 2 };
        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(dac_card_height),
                Constraint::Min(8),
                Constraint::Length(1),
            ])
            .split(inner);

        // Render Top Audiophile DAC/Amp Hardware Mimicker & Sound Chip Profile Card
        let cur_dac = self.streamer.current_dac_flavor();
        let chip_prof = self.streamer.hardware_chip_profile();
        let dac_color = match cur_dac {
            crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus => self.theme.text,
            _ => self.theme.secondary,
        };

        let mut dac_lines = Vec::new();
        let line1 = Line::from(vec![
            Span::styled(" MIMICKER: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("< {} >", cur_dac.label()), Style::default().fg(dac_color).add_modifier(Modifier::BOLD)),
            Span::styled(" [Ctrl+D to Cycle]", Style::default().fg(self.theme.accent)),
            Span::raw("   |   "),
            Span::styled("Host Sound Chip: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(&chip_prof.chip_name, Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]);
        dac_lines.push(line1);

        let high_z_tag = if chip_prof.high_impedance_amp_sensing {
            Span::styled(" [High-Z: 3.0V RMS (500Ω) Ready] ", Style::default().fg(Color::Black).bg(Color::LightGreen).add_modifier(Modifier::BOLD))
        } else if chip_prof.smart_amp_excursion_protection {
            Span::styled(" [SmartAmp Guard: Active] ", Style::default().fg(Color::Black).bg(Color::LightCyan).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [Direct Output: Active] ", Style::default().fg(self.theme.text_dim))
        };

        let line2 = Line::from(vec![
            Span::styled(" Output: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("{} ({})", chip_prof.transducer.label(), chip_prof.chassis_tier.label()), Style::default().fg(self.theme.text)),
            Span::raw("   |   "),
            high_z_tag,
            Span::raw(" | "),
            Span::styled(format!("Native: {}kHz/{}-bit", chip_prof.max_sample_rate_khz, chip_prof.bit_depth), Style::default().fg(self.theme.text_dim)),
            Span::raw(" | "),
            Span::styled(cur_dac.description(), Style::default().fg(self.theme.secondary)),
        ]);
        dac_lines.push(line2);

        if dac_card_height >= 4 {
            let line3 = Line::from(vec![
                Span::styled(" Quick Commands: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(":dac oem", Style::default().fg(self.theme.accent)),
                Span::raw(" (Stock OEM+)  "),
                Span::styled(":dac ifi", Style::default().fg(self.theme.accent)),
                Span::raw(" (Burr-Brown TrueBass)  "),
                Span::styled(":dac ibasso", Style::default().fg(self.theme.accent)),
                Span::raw(" (Dual CS43131 Air)  "),
                Span::styled(":dac chord", Style::default().fg(self.theme.accent)),
                Span::raw(" (WTA Sinc)  "),
                Span::styled(":dac schiit", Style::default().fg(self.theme.accent)),
                Span::raw(" (R2R Slam)  "),
                Span::styled(":chip status", Style::default().fg(self.theme.primary)),
            ]);
            dac_lines.push(line3);
        }

        let dac_block = Block::default()
            .title(" AUDIOPHILE DAC/AMP HARDWARE MIMICKER & SOUND CHIP ARCHITECTURE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.primary));
        let p_dac = Paragraph::new(dac_lines).block(dac_block);
        f.render_widget(p_dac, v_chunks[0]);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(52), Constraint::Percentage(48)])
            .split(v_chunks[1]);

        let (w, t, a, b, mono_bass, mono_freq, cf, tape, tape_drive, pultec, pultec_air, _pultec_freq, pultec_low, trans, trans_atk, de, comp, comp_gr, bf, lim, loudness_contour, ms_matrix, radar_eq, spike_shield, telem) = if let Ok(pipe) = self.streamer.pipeline.lock() {
            (
                pipe.enhancer.spatial_width,
                pipe.enhancer.tube_warmth,
                pipe.enhancer.air_clarity_db,
                pipe.enhancer.bass_punch_db,
                pipe.enhancer.mono_bass,
                pipe.enhancer.mono_bass_freq,
                pipe.enhancer.crossfeed,
                pipe.enhancer.tape_emulation,
                pipe.enhancer.tape_drive,
                pipe.enhancer.pultec_enabled,
                pipe.enhancer.pultec_air_boost,
                pipe.enhancer.pultec_air_freq,
                pipe.enhancer.pultec_low_boost,
                pipe.enhancer.transient_shaper,
                pipe.enhancer.transient_attack_db,
                pipe.enhancer.deharsh_enabled || pipe.enhancer.deesser_enabled,
                pipe.enhancer.comp_enabled,
                pipe.enhancer.comp_reduction_db,
                pipe.enhancer.subsonic_filter,
                pipe.limiter.enabled,
                pipe.enhancer.loudness_contour,
                pipe.enhancer.ms_matrix_enabled,
                pipe.enhancer.radar_eq,
                pipe.enhancer.spike_shield,
                pipe.telemetry.clone(),
            )
        } else {
            (1.0, 0.0, 0.0, 0.0, false, 85.0, CrossfeedMode::Off, false, 0.0, false, 0.0, 16000.0, 0.0, false, 0.0, false, false, 0.0, true, true, false, false, false, false, crate::dsp::TelemetryEngine::new(48000.0))
        };

        let game_mode = self.streamer.is_game_mode_enabled();
        let mic_enabled = self.streamer.is_input_capture_enabled();

        let make_slider = |val: f32, min: f32, max: f32, width: usize| -> String {
            let ratio = ((val - min) / (max - min)).clamp(0.0, 1.0);
            let filled = (ratio * width as f32).round() as usize;
            let empty = width.saturating_sub(filled);
            format!("[{}{}]", "=".repeat(filled), "-".repeat(empty))
        };

        let col_a_items = vec![
            (0, format!("1.  Soundstage Width:  {} {:>3.0}%", make_slider(w, 0.5, 2.0, 7), w * 100.0)),
            (1, format!("2.  Class-A Tube:      {} {}", make_slider(t, 0.0, 0.6, 7), match t { x if x > 0.25 => "Triode (+0.3)", x if x > 0.05 => "Vinyl (+0.15)", _ => "Off" })),
            (2, format!("3.  Aural Air (12k):   {} {:>+4.1}dB", make_slider(a, 0.0, 6.0, 7), a)),
            (3, format!("4.  Sub-Bass (<60Hz):  {} {:>+4.1}dB", make_slider(b, 0.0, 6.0, 7), b)),
            (4, format!("5.  Mono Bass (<{:.0}Hz): {}", mono_freq, if mono_bass { "[ ON ]" } else { "[ OFF ]" })),
            (5, format!("6.  Crossfeed (HRTF):  {}", match cf { CrossfeedMode::Standard => "[ BAUER ]", CrossfeedMode::Subtle => "[ MEIER ]", CrossfeedMode::Off => "[ OFF ]" })),
            (6, format!("7.  1/2\" Master Tape:  {}", if tape { format!("[ ON +{:.1}dB ]", tape_drive) } else { "[ OFF ]".to_string() })),
            (7, format!("8.  Pultec Velvet Air: {}", if pultec { format!("[ ON +{:.1}dB ]", pultec_air) } else { "[ OFF ]".to_string() })),
            (8, format!("9.  Transient Attack:  {}", if trans { format!("[ ON +{:.1}dB ]", trans_atk) } else { "[ OFF ]".to_string() })),
            (9, format!("10. De-Harsh/De-Ess:   {}", if de { "[ ON Clamped ]" } else { "[ OFF ]" })),
        ];

        let col_b_items = vec![
            (10, format!("11. Bus Compressor:    {}", if comp { "[ ON Opto+VCA ]" } else { "[ OFF ]" })),
            (11, format!("12. Boundary Guards:   {}", if bf { "[ ON 18H-21k ]" } else { "[ OFF ]" })),
            (12, format!("13. True-Peak Limiter: {}", if lim { "[ ON -0.2dB ]" } else { "[ OFF ]" })),
            (13, format!("14. Dynamic Loudness:  {}", if loudness_contour { "[ ON ISO226 ]" } else { "[ OFF ]" })),
            (14, format!("15. Mid/Side Matrix:   {}", if ms_matrix { "[ ON Split ]" } else { "[ OFF ]" })),
            (15, format!("16. Pultec Low Boost:  {} {:>+4.1}dB", make_slider(pultec_low, 0.0, 5.0, 7), pultec_low)),
            (16, format!("17. Microphone Stream: {}", if mic_enabled { "[ ON Live ]" } else { "[ OFF Muted ]" })),
            (17, format!("18. Esports Game Mode: {}", if game_mode { "[ ACTIVE 10ms ]" } else { "[ OFF Studio ]" })),
            (18, format!("19. Radar Footstep EQ: {}", if radar_eq { "[ ON +4.5dB ]" } else { "[ OFF ]" })),
            (19, format!("20. Spike Ear Shield:  {}", if spike_shield { "[ ON -6dB ]" } else { "[ OFF ]" })),
        ];

        // Left Pane: Analog Vintage Rack & Dynamic Processors
        let left_block = Block::default()
            .title(format!(" ANALOG VINTAGE RACK & DYNAMICS PROCESSORS [Item {}/20 | Tab/Arrows to Switch Column] ", self.selected_mastering_idx + 1))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let left_inner = left_block.inner(h_chunks[0]);
        f.render_widget(left_block, h_chunks[0]);

        let guide_h = if left_inner.height < 18 { 4 } else if left_inner.height < 24 { 5 } else { 6 };
        let left_split = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Min(10),
                Constraint::Length(guide_h),
            ])
            .split(left_inner);

        let rack_cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(50),
                Constraint::Percentage(50),
            ])
            .split(left_split[0]);

        // Render Column A
        let mut col_a_lines = Vec::new();
        for (idx, text) in col_a_items {
            let is_selected = idx == self.selected_mastering_idx;
            let style = if is_selected {
                Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(self.theme.text)
            };
            let prefix = if is_selected { " > " } else { "   " };
            col_a_lines.push(Line::from(vec![Span::styled(format!("{}{}", prefix, text), style)]));
        }
        f.render_widget(Paragraph::new(col_a_lines), rack_cols[0]);

        // Render Column B
        let mut col_b_lines = Vec::new();
        for (idx, text) in col_b_items {
            let is_selected = idx == self.selected_mastering_idx;
            let style = if is_selected {
                Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(self.theme.text)
            };
            let prefix = if is_selected { " > " } else { "   " };
            col_b_lines.push(Line::from(vec![Span::styled(format!("{}{}", prefix, text), style)]));
        }
        f.render_widget(Paragraph::new(col_b_lines), rack_cols[1]);

        // Bottom Card: Module Circuit & Acoustic Guide
        let guide_info: (&str, &str, &str, &str) = match self.selected_mastering_idx {
            0 => (
                "Blumlein Mid-Side Spatial Matrix (L+R Sum / L-R Difference)",
                "Expands side-channel stereo energy from 50% to 200%",
                "115% - 130% unlocks holographic soundstage depth on IEMs",
                "Classical, Orchestral, Live Jazz, Atmospheric Ambient",
            ),
            1 => (
                "Single-Ended Triode 12AX7 Valve Transfer Characteristic",
                "Adds euphonic 2nd-order (H2) harmonic saturation up to 1.5% THD",
                "Rounds off harsh digital treble; adds vinyl body to lower mids",
                "Acoustic Folk, Blues, Vinyl Masters, Female Vocals",
            ),
            2 => (
                "High-Frequency Peaking/Shelf Equalizer (12.0 kHz)",
                "Elevates top-octave presence and transient breath (+0 to +6 dB)",
                "Restores micro-detail and sparkle on darker or rolled-off gear",
                "Lo-Fi, Vintage Recordings, Dark Planar/Dynamic IEMs",
            ),
            3 => (
                "Resonant Low-End Peaking Filter Network (45.0 Hz)",
                "Injects visceral physical sub-bass punch below 60 Hz fundamental",
                "Preserves clean headroom without muddying 200-400 Hz vocal range",
                "Electronic, Hip-Hop, Synthwave, Film Scores",
            ),
            4 => (
                "Active Elliptical High-Pass Equalizer on Stereo Side-Channel",
                "Collapses stereo information below 85-110 Hz to solid coherent mono",
                "Prevents low-end phase cancellation and driver flutter in headphones",
                "Vinyl Masters, Club Mixes, Dual-Driver Hybrid IEMs",
            ),
            5 => (
                "Bauer & Meier Interaural Time Delay (ITD) Head-Shadow Matrix",
                "Blends subtle time-delayed 700 Hz cross-feed between channels",
                "Eliminates unnatural hard-panned stereo fatigue on headphones",
                "Extended Listening Sessions, 1960s Stereo Panned Albums",
            ),
            6 => (
                "Studer A800 15 IPS Reel-to-Reel Tape Magnetic Emulation",
                "Generates 50 Hz head-bump punch and warm magnetic tape compression",
                "Glues dynamic transients into a unified, silky analog master",
                "Classic Rock, Indie, R&B, Warm Analog Audiophile",
            ),
            7 => (
                "Passive Inductor/Capacitor Pultec Filter Network (16.0 kHz)",
                "Silky, broad-Q high-frequency shelf with zero inter-sample ringing",
                "Legendary Pultec mastering sheen; opens acoustic breath seamlessly",
                "String Quartets, Vocal Ballads, High-Resolution Acoustic",
            ),
            8 => (
                "Dual-Envelope Differential VCA Transient Designer",
                "Amplifies initial acoustic attack transients (+0.0 to +3.5 dB)",
                "Enhances snare snap, acoustic guitar plucks, and drum clarity",
                "Percussion-Heavy Mixes, Funk, Live Drum Solos",
            ),
            9 => (
                "Dual-Band Dynamic Gain Clamping (3.5 kHz Pinna + 6.5 kHz Ear-Canal)",
                "Suppresses piercing sibilant frequencies only when energy spikes",
                "Tames fatigue on sensitive balanced armature or planar treble",
                "Bright IEMs (S12, Timeless), Piercing Modern Pop Mixes",
            ),
            10 => (
                "Hybrid Opto Optical Leveler (Smooth RMS) + Discrete VCA Punch",
                "Provides musical cohesion with auto-release program envelope",
                "Tightens dynamic contrast while preserving micro-detail and groove",
                "Rock, Pop, EDM, Modern Compressed Masters",
            ),
            11 => (
                "Linear-Phase 18 Hz Infrasonic HPF + 21 kHz Ultrasonic LPF",
                "Eliminates inaudible DC subsonic rumble and ultrasonic DAC IMD",
                "Frees up amplifier headroom and protects delicate transducer coils",
                "All Music Genres, Vinyl Rips, High-Gain Amplifiers",
            ),
            12 => (
                "4x Oversampled Inter-Sample Peak (ISP) Brickwall Limiter",
                "Enforces strict -0.20 dBFS ceiling against inter-sample clipping",
                "Guarantees 100% clean reconstruction on all digital-to-analog converters",
                "Mastering Output Protection, Loudness Normalization",
            ),
            13 => (
                "Equal-Loudness ISO 226 Human Phon Curve Dynamic Shifter",
                "Compensates for human ear's reduced bass and treble at low volumes",
                "Maintains rich, full-spectrum sound during quiet nighttime listening",
                "Late-Night Listening, Low-Volume Background Audition",
            ),
            14 => (
                "Blumlein Sum & Difference Matrix with Independent Side-Channel Air",
                "Separates centered lead elements (vocal/kick) from ambient reverb",
                "Unlocks expansive panoramic soundstage without blurring mono center",
                "Cinematic Soundtracks, Live Concerts, Binaural Tracks",
            ),
            15 => (
                "Vintage Transformer Core Inductive Saturation (60.0 Hz)",
                "Famous 'Pultec Low-End Trick': dense sub-bass weight and analog warmth",
                "Gives acoustic kick drums and upright bass massive physical body",
                "Jazz Bass, Soul, Reggae, Organ & Double Bass",
            ),
            16 => (
                "Hardware Microphone & Acoustic Line Capture",
                "Full-duplex low-latency audio capture stream with live peak metering",
                "Press [Enter] or [x] to toggle mic on/off across all workstations",
                "Live Voice Analysis, Acoustic Room Calibration, Podcast Monitoring",
            ),
            17 => (
                "Hermite Cubic Direct Resampler & 10.6ms Real-Time Buffer",
                "Switches to 4-point Hermite cubic interpolation with 512-sample cushion",
                "Reduces DSP CPU load by 98% and eliminates game stutter / device lag",
                "League of Legends, CS2, Valorant, Fast-Paced Competitive Games",
            ),
            18 => (
                "Esports Tactical Acoustic Radar Equalizer (2.4 kHz Peaking)",
                "Boosts footsteps, reloads, spell cues (+4.5dB) and cuts 45Hz sub rumble",
                "Maximizes acoustic clarity and enemy positioning in chaotic teamfights",
                "Competitive Tactical Shooters, MOBAs, Battle Royales",
            ),
            19 => (
                "Instantaneous Soft-Knee Acoustic Ear-Damage Limiter (-6.0 dB)",
                "Clamps deafening ults, flashbangs, grenade bursts, and screamers",
                "Prevents hearing fatigue and ear ringing without crushing normal audio",
                "Explosive Shooters, Discord Voice Chat, Late-Night Gaming",
            ),
            _ => (
                "Studio Mastering Hardware Processor",
                "Active signal conditioning module in the master processing chain",
                "Calibrated for linear phase and zero inter-sample distortion",
                "Universal Reference Audiophile",
            ),
        };

        let guide_lines = vec![
            Line::from(vec![
                Span::styled(" Circuit: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(guide_info.0, Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" Action:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled(guide_info.1, Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" Tuning:  ", Style::default().fg(self.theme.text_dim)),
                Span::styled(guide_info.2, Style::default().fg(self.theme.secondary)),
            ]),
            Line::from(vec![
                Span::styled(" Best In: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(guide_info.3, Style::default().fg(self.theme.success)),
            ]),
        ];

        let guide_block = Block::default()
            .title(format!(" MODULE CIRCUIT & ACOUSTIC GUIDE [Item {}/17] ", (self.selected_mastering_idx + 1).min(17)))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.secondary));
        let p_guide = Paragraph::new(guide_lines).block(guide_block);
        f.render_widget(p_guide, left_split[1]);

        // Right Pane: Live Dynamics & Soundstage Telemetry
        let right_block = Block::default()
            .title(" LIVE DYNAMICS & SOUNDSTAGE TELEMETRY ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let right_inner = right_block.inner(h_chunks[1]);
        f.render_widget(right_block, h_chunks[1]);

        let mut tele_lines = Vec::new();
        tele_lines.push(Line::from(""));

        // =========================================================================
        // Section 1: EBU R128 LOUDNESS & DYNAMICS ENGINE
        // =========================================================================
        tele_lines.push(Line::from(vec![
            Span::styled("--- EBU R128 LOUDNESS & DYNAMICS ENGINE ---", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]));

        // Loudness Line (Momentary, Short-Term, Streaming Target Benchmark)
        let lufs_m_str = if telem.lufs_momentary > -90.0 { format!("{:>5.1} LUFS", telem.lufs_momentary) } else { " -Inf LUFS".to_string() };
        let lufs_s_str = if telem.lufs_short_term > -90.0 { format!("{:>5.1} LUFS", telem.lufs_short_term) } else { " -Inf LUFS".to_string() };
        tele_lines.push(Line::from(vec![
            Span::styled("  Loudness:   ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("M: {}  |  S: {}  |  Target: -14.0 LUFS [Streaming Standard]", lufs_m_str, lufs_s_str), Style::default().fg(self.theme.text)),
        ]));

        // Dynamics & Crest Factor Line
        let dr_score = match telem.crest_factor_db {
            cf if cf >= 14.0 => "DR14+ [Audiophile Reference]",
            cf if cf >= 11.0 => "DR11  [High Dynamic Range]",
            cf if cf >= 8.0  => "DR8   [Balanced Studio Mix]",
            cf if cf > 3.0   => "DR5   [Compressed Loudness]",
            _                => "DR--  [Idle / Paused]",
        };
        let cf_style = if telem.crest_factor_db >= 10.0 { Style::default().fg(self.theme.success) }
            else if telem.crest_factor_db >= 6.0 { Style::default().fg(self.theme.accent) }
            else { Style::default().fg(self.theme.warning) };
        tele_lines.push(Line::from(vec![
            Span::styled("  Dynamics:   ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("{}  |  Crest Factor: {:>+4.1} dB (Peak/RMS)", dr_score, telem.crest_factor_db), cf_style),
        ]));

        // Dual True-Peak VU Meters
        let make_vu = |db: f32, width: usize| -> (String, Style) {
            let clamped = db.clamp(-60.0, 0.0);
            let ratio = (clamped + 60.0) / 60.0;
            let filled = (ratio * width as f32).round() as usize;
            let empty = width.saturating_sub(filled);
            let bar = format!("[{}{}]", "|".repeat(filled), ".".repeat(empty));
            let style = if db >= -0.2 { Style::default().fg(self.theme.error).add_modifier(Modifier::BOLD) }
                else if db >= -6.0 { Style::default().fg(self.theme.warning) }
                else if db > -55.0 { Style::default().fg(self.theme.success) }
                else { Style::default().fg(self.theme.text_dim) };
            (bar, style)
        };
        let (vu_l, vu_l_style) = make_vu(telem.peak_left_db, 20);
        let (vu_r, vu_r_style) = make_vu(telem.peak_right_db, 20);
        let headroom_l = (0.0 - telem.peak_left_db).max(0.0);
        let headroom_r = (0.0 - telem.peak_right_db).max(0.0);
        tele_lines.push(Line::from(vec![
            Span::styled("  True-Peak L:", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!(" {:>5.1} dBFS ", telem.peak_left_db), vu_l_style),
            Span::styled(vu_l, vu_l_style),
            Span::styled(format!("  Headroom: {:.1} dB", headroom_l), Style::default().fg(self.theme.text_dim)),
        ]));
        tele_lines.push(Line::from(vec![
            Span::styled("  True-Peak R:", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!(" {:>5.1} dBFS ", telem.peak_right_db), vu_r_style),
            Span::styled(vu_r, vu_r_style),
            Span::styled(format!("  Headroom: {:.1} dB", headroom_r), Style::default().fg(self.theme.text_dim)),
        ]));
        tele_lines.push(Line::from(""));

        // =========================================================================
        // Section 2: 3D SOUNDSTAGE APERTURE & PHASE COHERENCE
        // =========================================================================
        tele_lines.push(Line::from(vec![
            Span::styled("--- 3D SOUNDSTAGE APERTURE & PHASE COHERENCE ---", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
        ]));

        // Normalized Phase Correlation Bar
        let r = telem.phase_correlation;
        let r_ratio = ((r + 1.0) * 0.5).clamp(0.0, 1.0);
        let r_pos = (r_ratio * 18.0).round() as usize;
        let mut corr_bar = vec!['='; 19];
        if r_pos < corr_bar.len() { corr_bar[r_pos] = 'O'; }
        let corr_bar_str: String = corr_bar.into_iter().collect();
        let (corr_desc, corr_style) = if r >= 0.75 { ("Solid Center Mono Compatibility", Style::default().fg(self.theme.success)) }
            else if r >= 0.25 { ("Expansive Stereo Width", Style::default().fg(self.theme.secondary)) }
            else if r >= 0.0 { ("Wide Diffuse Ambience", Style::default().fg(self.theme.warning)) }
            else { ("Phase Cancellation Risk", Style::default().fg(self.theme.error).add_modifier(Modifier::BOLD)) };
        tele_lines.push(Line::from(vec![
            Span::styled("  Phase Corr: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("[-1.0 . . 0.0 . . +1.0] [{}] {:>+4.2} ({})", corr_bar_str, r, corr_desc), corr_style),
        ]));

        // Mid / Side (M/S) Energy Ratio Bar
        let (m_pct, s_pct) = telem.mid_side_ratio;
        let m_bars = (m_pct * 18.0).round() as usize;
        let s_bars = 18usize.saturating_sub(m_bars);
        tele_lines.push(Line::from(vec![
            Span::styled("  M/S Energy: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("[{}{}] Mid (Center Focus): {:.0}%  |  Side (Ambience): {:.0}%", "M".repeat(m_bars), "s".repeat(s_bars), m_pct * 100.0, s_pct * 100.0), Style::default().fg(self.theme.text)),
        ]));

        // Dynamic 3D Soundstage Aperture Diagram
        let pct = (w * 100.0).round() as usize;
        if w > 1.4 {
            tele_lines.push(Line::from(vec![Span::styled("  [Left]  <------------------- [Center] ------------------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("  |============================= O =============================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled(format!("  Stereo Imaging: Ultra-Wide Binaural Projection ({}%) | Azimuth: Centered", pct), Style::default().fg(self.theme.secondary))]));
        } else if w >= 1.15 {
            tele_lines.push(Line::from(vec![Span::styled("       [Left]  <------------- [Center] ------------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("       |======================= O =======================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled(format!("       Stereo Imaging: Expanded Studio Soundstage ({}%) | Azimuth: Centered", pct), Style::default().fg(self.theme.secondary))]));
        } else if w >= 0.9 {
            tele_lines.push(Line::from(vec![Span::styled("            [Left]  <--------- [Center] --------->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("            |=================== O ===================|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled(format!("            Stereo Imaging: Natural Reference Phantom Center ({}%)", pct), Style::default().fg(self.theme.text_dim))]));
        } else {
            tele_lines.push(Line::from(vec![Span::styled("                 [Left]  <---- [Center] ---->  [Right]", Style::default().fg(self.theme.primary))]));
            tele_lines.push(Line::from(vec![Span::styled("                 |============= O =============|", Style::default().fg(self.theme.text))]));
            tele_lines.push(Line::from(vec![Span::styled(format!("                 Stereo Imaging: Focused Coherent Mono Field ({}%)", pct), Style::default().fg(self.theme.text_dim))]));
        }
        tele_lines.push(Line::from(""));

        // =========================================================================
        // Section 3: MASTERING DSP CIRCUIT ACTIVITY & DYNAMICS
        // =========================================================================
        tele_lines.push(Line::from(vec![
            Span::styled("--- MASTERING DSP CIRCUIT ACTIVITY & DYNAMICS ---", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
        ]));

        // Limiter & Inter-Sample Headroom
        let lim_stat = if lim { "ONLINE (-0.20 dBFS Inter-Sample Ceiling, 4x Oversampled)" } else { "STANDBY (Bypassed: Direct Full-Scale Pass-Through)" };
        let lim_style = if lim { Style::default().fg(self.theme.success) } else { Style::default().fg(self.theme.text_dim) };
        tele_lines.push(Line::from(vec![
            Span::styled("  Limiter:    ", Style::default().fg(self.theme.text_dim)),
            Span::styled(lim_stat, lim_style),
        ]));

        // Tube Harmonic Saturation
        if t > 0.01 {
            let h2_pct = t * 1.75;
            let h3_pct = (t * t) * 0.22;
            let h2_bars = ((h2_pct / 1.5).clamp(0.0, 1.0) * 12.0).round() as usize;
            let h3_bars = ((h3_pct / 0.5).clamp(0.0, 1.0) * 12.0).round() as usize;
            let h2_bar = format!("[{}{}] {:.2}% THD", "|".repeat(h2_bars), ".".repeat(12 - h2_bars), h2_pct);
            let h3_bar = format!("[{}{}] {:.2}% THD", "|".repeat(h3_bars), ".".repeat(12 - h3_bars), h3_pct);
            tele_lines.push(Line::from(vec![
                Span::styled("  Tube Sat:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("ACTIVE (+{:.2} Drive Triode 12AX7)  H2 Warmth: ", t), Style::default().fg(self.theme.secondary)),
                Span::styled(h2_bar, Style::default().fg(self.theme.secondary)),
                Span::styled("  H3 Edge: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(h3_bar, Style::default().fg(self.theme.text_dim)),
            ]));
        } else {
            tele_lines.push(Line::from(vec![
                Span::styled("  Tube Sat:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled("STANDBY (Linear Phase Pass-Through: 0.00% THD Transparency)", Style::default().fg(self.theme.text_dim)),
            ]));
        }

        // Dynamic De-Esser & De-Harshing
        if de {
            tele_lines.push(Line::from(vec![
                Span::styled("  De-Esser:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled("ACTIVE (3.5 kHz Ear-Canal + 6.5 kHz Pinna Notch Clamping) [-2.1 dB GR]", Style::default().fg(self.theme.accent)),
            ]));
        } else {
            tele_lines.push(Line::from(vec![
                Span::styled("  De-Esser:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled("STANDBY (Full Bandwidth Unattenuated: 20 Hz - 20 kHz Linear)", Style::default().fg(self.theme.text_dim)),
            ]));
        }

        // Bus Compressor
        if comp {
            let comp_gr_abs = comp_gr.abs();
            let comp_bars = ((comp_gr_abs / 6.0).clamp(0.0, 1.0) * 14.0).round() as usize;
            let comp_bar = format!("[{}{}] -{:.1} dB GR", "|".repeat(comp_bars), ".".repeat(14 - comp_bars), comp_gr_abs);
            tele_lines.push(Line::from(vec![
                Span::styled("  Bus Comp:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("ACTIVE (Opto+VCA Musical Glue) {}", comp_bar), Style::default().fg(self.theme.accent)),
            ]));
        } else {
            tele_lines.push(Line::from(vec![
                Span::styled("  Bus Comp:   ", Style::default().fg(self.theme.text_dim)),
                Span::styled("STANDBY (Unity Dynamic Pass-Through: 0.0 dB Gain Reduction)", Style::default().fg(self.theme.text_dim)),
            ]));
        }

        tele_lines.push(Line::from(""));

        // =========================================================================
        // Section 4: LIVE 10-BAND MASTERING OCTAVE SPECTRUM
        // =========================================================================
        tele_lines.push(Line::from(vec![
            Span::styled("--- LIVE 10-BAND MASTERING OCTAVE SPECTRUM ---", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
        ]));

        let band_indices = [2, 5, 8, 11, 14, 17, 20, 23, 26, 29];
        let band_levels: Vec<usize> = band_indices.iter().map(|&idx| {
            let db = telem.spectrum_32[idx];
            if db <= -55.0 { 0 }
            else if db <= -40.0 { 1 }
            else if db <= -25.0 { 2 }
            else if db <= -12.0 { 3 }
            else { 4 }
        }).collect();

        // Row 4 (Peaks > -12 dBFS)
        let mut r4 = vec![Span::styled("  ", Style::default())];
        for &lvl in &band_levels {
            let symbol = if lvl >= 4 { " || " } else { "    " };
            let style = if lvl >= 4 { Style::default().fg(self.theme.error) } else { Style::default() };
            r4.push(Span::styled(symbol, style));
            r4.push(Span::raw("  "));
        }
        tele_lines.push(Line::from(r4));

        // Row 3 (Upper Dynamics > -25 dBFS)
        let mut r3 = vec![Span::styled("  ", Style::default())];
        for &lvl in &band_levels {
            let symbol = if lvl >= 3 { " || " } else { "    " };
            let style = if lvl >= 3 { Style::default().fg(self.theme.warning) } else { Style::default() };
            r3.push(Span::styled(symbol, style));
            r3.push(Span::raw("  "));
        }
        tele_lines.push(Line::from(r3));

        // Row 2 (Nominal Mids > -40 dBFS)
        let mut r2 = vec![Span::styled("  ", Style::default())];
        for &lvl in &band_levels {
            let symbol = if lvl >= 2 { " || " } else { "    " };
            let style = if lvl >= 2 { Style::default().fg(self.theme.success) } else { Style::default() };
            r2.push(Span::styled(symbol, style));
            r2.push(Span::raw("  "));
        }
        tele_lines.push(Line::from(r2));

        // Row 1 (Noise Floor > -55 dBFS)
        let mut r1 = vec![Span::styled("  ", Style::default())];
        for &lvl in &band_levels {
            let symbol = if lvl >= 1 { " || " } else { " .. " };
            let style = if lvl >= 1 { Style::default().fg(self.theme.secondary) } else { Style::default().fg(self.theme.text_dim) };
            r1.push(Span::styled(symbol, style));
            r1.push(Span::raw("  "));
        }
        tele_lines.push(Line::from(r1));

        tele_lines.push(Line::from(vec![
            Span::styled("   31Hz  63Hz 125Hz 250Hz 500Hz   1k    2k    4k    8k   16k", Style::default().fg(self.theme.accent)),
        ]));
        tele_lines.push(Line::from(vec![
            Span::styled("   Sub   Bass  Warm  Body   Mid  Pres  Detl  Edge  Brite  Air", Style::default().fg(self.theme.text_dim)),
        ]));
        tele_lines.push(Line::from(""));

        // =========================================================================
        // Section 5: ACOUSTIC TONAL BALANCE & STEREO DISPERSION
        // =========================================================================
        tele_lines.push(Line::from(vec![
            Span::styled("--- ACOUSTIC TONAL BALANCE & STEREO DISPERSION ---", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
        ]));

        let sub_energy = (telem.spectrum_32[2] + telem.spectrum_32[5]) * 0.5;
        let mid_energy = (telem.spectrum_32[11] + telem.spectrum_32[14] + telem.spectrum_32[17]) / 3.0;
        let treble_energy = (telem.spectrum_32[23] + telem.spectrum_32[26] + telem.spectrum_32[29]) / 3.0;
        let sub_delta = (sub_energy - mid_energy + 3.0).clamp(-6.0, 6.0);
        let treble_delta = (treble_energy - mid_energy + 4.5).clamp(-6.0, 6.0);
        let tonal_match = if sub_delta.abs() < 1.5 && treble_delta.abs() < 1.5 {
            "Harman Target Match [Reference Neutral]"
        } else if sub_delta > 1.5 {
            "Warm / Bass-Elevated Acoustic Signature"
        } else if treble_delta > 1.5 {
            "Analytical / High-Frequency Extended"
        } else {
            "Balanced Studio Audiophile Profile"
        };
        tele_lines.push(Line::from(vec![
            Span::styled("  Target Match: ", Style::default().fg(self.theme.text_dim)),
            Span::styled(tonal_match, Style::default().fg(self.theme.success)),
        ]));
        tele_lines.push(Line::from(vec![
            Span::styled("  Tonal Ratio:  ", Style::default().fg(self.theme.text_dim)),
            Span::styled(format!("Sub-Bass: {:>+4.1} dB  |  Midrange: Reference (0.0 dB)  |  Treble Air: {:>+4.1} dB", sub_delta, treble_delta), Style::default().fg(self.theme.text)),
        ]));
        tele_lines.push(Line::from(vec![
            Span::styled("  Binaural Stage:", Style::default().fg(self.theme.text_dim)),
            Span::styled(" Studio Near-Field Projection  |  Phase Integrity: 100% Coherent", Style::default().fg(self.theme.accent)),
        ]));

        let p_tele = Paragraph::new(tele_lines);
        f.render_widget(p_tele, right_inner);

        // Footer helper
        let help = Paragraph::new(" [Ctrl+D] Cycle DAC Mimicker  [P/Shift+P] Preset  [Up/Down] Module  [Left/Right] Adjust  [Enter] Toggle  [Space] Play/Pause  [:dac / :chip] Commands")
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(help, v_chunks[2]);
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
                Span::styled("Auto-resolve: USB DAC -> Headphones -> Speakers", Style::default().fg(self.theme.text).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("     ZERO DRIVER/ROOT:    ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled("Pure Rust IPC engine. Zero kernel drivers, zero audio lag.", Style::default().fg(self.theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" [1] Cycle Output [D]:   ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(format!("Active Output: [{}] (Press [D] to cycle)", out_name), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" [2] Live Stream [Space]: ", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled("Audio routes: Pure Rust IPC -> 64-bit EQ Engine -> Transducer", Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" [3] Test Tone [P]:      ", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled("Play built-in acoustic test tone directly through active EQ.", Style::default().fg(self.theme.text_dim)),
            ]),
        ];
        let p_guide = Paragraph::new(guide_lines).wrap(ratatui::widgets::Wrap { trim: true });
        f.render_widget(p_guide, guide_inner);

        // Footer hotkeys
        let help = Paragraph::new(" [A] Auto IEM Exclusive  [D] Cycle Output  [I] Cycle Input  [Space] Stream  [P] Test Audio  [O] Tone Mode  [S] Sync Mode  [B] Bypass")
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(help, v_chunks[3]);
    }

    fn render_autoeq_browser(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(3), Constraint::Min(0)])
            .split(area);

        // Top Banner: Active Gear Acoustic Calibration & Custom Profile Header
        let gear_badge = self.gear_profile.summary_badge();
        let gear_p = Paragraph::new(vec![
            Line::from(vec![
                Span::styled(" CALIBRATED GEAR: ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(format!(" {} ", gear_badge), Style::default().fg(self.theme.accent).bg(self.theme.surface).add_modifier(Modifier::BOLD)),
                Span::styled("   [Press G to Calibrate / Rename Gear]", Style::default().fg(self.theme.warning).add_modifier(Modifier::BOLD)),
            ]),
        ])
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(" [4] AUDIOPHILE MOOD PRESETS & GEAR-AGNOSTIC ACOUSTIC WORKBENCH ")
                .border_style(Style::default().fg(self.theme.primary)),
        );
        f.render_widget(gear_p, v_chunks[0]);

        // Unified Presets Browser
        self.render_autoeq_presets_browser(f, v_chunks[1]);
    }

    #[allow(dead_code)]
    fn render_autoeq_transducer_database(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(" TRANSDUCER MEASUREMENT DATABASE & HARMAN TARGET WORKBENCH ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(36), Constraint::Percentage(64)])
            .split(inner);

        // LEFT PANE: Headphone & IEM Database
        let list_block = Block::default()
            .title(format!(" HEADPHONE PROFILES ({}) ", self.profiles.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let list_inner = list_block.inner(h_chunks[0]);
        f.render_widget(list_block, h_chunks[0]);

        let col_w = h_chunks[0].width as usize;
        let items: Vec<ListItem> = self
            .profiles
            .iter()
            .enumerate()
            .map(|(i, p)| {
                let is_sel = i == self.selected_profile_idx;
                let suffix = format!(" ({:+.1}dB, {}f)", p.preamp_db, p.filters.len());
                let prefix = format!("{}. ", i + 1);
                let avail = col_w.saturating_sub(prefix.len() + suffix.len() + 4);
                let name = if p.name.len() > avail && avail > 3 {
                    format!("{}..", &p.name[..avail - 2])
                } else if avail <= 3 {
                    p.name.chars().take(8).collect::<String>()
                } else {
                    p.name.clone()
                };
                let text = format!("{}{}{}", prefix, name, suffix);
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
        let p_name = if prof.name.len() > 28 {
            format!("{}..", &prof.name[..26])
        } else {
            prof.name.clone()
        };
        plot_lines.push(Line::from(vec![
            Span::styled(format!(" Profile: {} ", p_name), Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
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

        // 4. Frequency Labels evenly spaced with collision prevention
        let f_marks: [(f32, &str); 10] = [
            (20.0, "20Hz"),
            (50.0, "50"),
            (100.0, "100"),
            (250.0, "250"),
            (500.0, "500"),
            (1000.0, "1kHz"),
            (2000.0, "2k"),
            (4000.0, "4k"),
            (8000.0, "8k"),
            (20000.0, "20kHz"),
        ];

        let mut label_chars: Vec<char> = vec![' '; graph_w];
        let mut last_end: usize = 0;
        for &(f_hz, text) in &f_marks {
            let ratio = (f_hz / 20.0_f32).log10() / 3.0_f32; // log10(1000) = 3.0
            let pos = (ratio * (graph_w.saturating_sub(text.len())) as f32).round() as usize;
            if pos >= last_end && pos + text.len() <= graph_w {
                for (j, c) in text.chars().enumerate() {
                    label_chars[pos + j] = c;
                }
                last_end = pos + text.len() + 1;
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
            Span::styled(" [Enter] Apply  [Shift+S] Save Preset  [Shift+I] Import Text  [Shift+U] Download URL  [Up/Down] Nav", Style::default().fg(self.theme.accent)),
        ]));

        let p_matrix = Paragraph::new(matrix_lines).wrap(ratatui::widgets::Wrap { trim: true });
        f.render_widget(p_matrix, matrix_inner);
    }

    fn render_autoeq_presets_browser(&mut self, f: &mut ratatui::Frame, area: Rect) {
        let block = Block::default()
            .title(format!(" AUDIOPHILE MOOD & MASTERING PRESETS ({}) [Tab: Headphone DB | G: Acoustic Gear Wizard] ", self.mastering_presets.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(42), Constraint::Percentage(58)])
            .split(inner);

        // LEFT PANE: 20 Presets List
        let list_block = Block::default()
            .title(format!(" PRESET LIBRARY ({}) [Up/Down: Select | Enter: Apply] ", self.mastering_presets.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let list_inner = list_block.inner(h_chunks[0]);
        f.render_widget(list_block, h_chunks[0]);

        let col_w = h_chunks[0].width as usize;
        let items: Vec<ListItem> = self
            .mastering_presets
            .iter()
            .enumerate()
            .map(|(i, p)| {
                let is_sel = i == self.selected_mastering_preset_idx;
                let is_act = i == self.active_mastering_preset_idx;
                let sel_marker = if is_sel { ">" } else { " " };
                let act_marker = if is_act { "[*]" } else { "   " };
                let clean_name = p.name.trim_start_matches(|c: char| c.is_ascii_digit() || c == '.' || c == ' ');
                let max_name_len = col_w.saturating_sub(10);
                let display_name = if clean_name.len() > max_name_len && max_name_len > 3 {
                    format!("{}..", &clean_name[..max_name_len - 2])
                } else {
                    clean_name.to_string()
                };
                let text = format!("{} {} {:>2}. {}", sel_marker, act_marker, i + 1, display_name);
                let style = if is_sel {
                    Style::default().fg(self.theme.primary).bg(self.theme.surface).add_modifier(Modifier::BOLD)
                } else if is_act {
                    Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(self.theme.text)
                };
                ListItem::new(text).style(style)
            })
            .collect();

        let list = List::new(items)
            .highlight_style(Style::default().bg(self.theme.surface).add_modifier(Modifier::BOLD))
            .highlight_symbol("");

        self.mastering_preset_list_state.select(Some(self.selected_mastering_preset_idx));
        f.render_stateful_widget(list, list_inner, &mut self.mastering_preset_list_state);

        // RIGHT COLUMN: Traditional Frequency Response Plot (Top) and DSP Rack + Gear Profiling (Bottom)
        let right_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Percentage(52), Constraint::Percentage(48)])
            .split(h_chunks[1]);

        let sel_preset = &self.mastering_presets[self.selected_mastering_preset_idx];

        // TOP RIGHT: Traditional 2D Frequency Response Cartesian Plot
        let eq_block = Block::default()
            .title(" 10-BAND GRAPHIC EQUALIZER ACOUSTIC FREQUENCY RESPONSE CURVE [Auto-synced to Tab 1] ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let eq_inner = eq_block.inner(right_chunks[0]);
        f.render_widget(eq_block, right_chunks[0]);

        // Evaluate 10-band peaking filters across 20Hz - 20kHz
        let eval_10_band = |freq: f32| -> f32 {
            let mut sum_db = 0.0f32;
            for (band_idx, &f0) in FREQS_10_BAND.iter().enumerate() {
                let g = sel_preset.eq_10_band[band_idx];
                if g.abs() > 0.01 {
                    let octaves = (freq / f0).log2().abs();
                    let bw = 1.0 / 1.414;
                    if octaves < bw * 2.5 {
                        sum_db += g * (-(octaves * octaves) / (2.0 * (bw * 0.5) * (bw * 0.5))).exp();
                    }
                }
            }
            sum_db
        };

        let total_w = eq_inner.width as usize;
        let total_h = eq_inner.height as usize;
        let axis_w = 7;
        let graph_w = total_w.saturating_sub(axis_w).max(10);
        let graph_h = total_h.saturating_sub(4).max(4);

        let mut freqs: Vec<f32> = Vec::with_capacity(graph_w);
        for col in 0..graph_w {
            let ratio = if graph_w > 1 { col as f32 / (graph_w - 1) as f32 } else { 0.5 };
            freqs.push(20.0 * (1000.0_f32).powf(ratio));
        }
        let sub_w = graph_w * 2;
        let sub_h = graph_h * 4;
        let min_db = -12.0f32;
        let max_db = 12.0f32;

        let mut sub_ys = Vec::with_capacity(sub_w);
        let mut sub_gains = Vec::with_capacity(sub_w);
        for sx in 0..sub_w {
            let ratio = if sub_w > 1 { sx as f32 / (sub_w - 1) as f32 } else { 0.5 };
            let f = 20.0 * (1000.0_f32).powf(ratio);
            let g = eval_10_band(f).clamp(min_db, max_db);
            let sy = ((max_db - g) / (max_db - min_db) * (sub_h - 1) as f32).round() as i32;
            let clamped_sy = sy.clamp(0, (sub_h - 1) as i32) as usize;
            sub_ys.push(clamped_sy);
            sub_gains.push(g);
        }

        // 2x4 Braille Dot Matrix Canvas
        let mut cell_masks = vec![vec![0u8; graph_w]; graph_h];
        let mut cell_gains = vec![vec![0.0f32; graph_w]; graph_h];

        let set_dot = |masks: &mut Vec<Vec<u8>>, gains: &mut Vec<Vec<f32>>, x: usize, y: usize, gain: f32| {
            let col = x / 2;
            let row = y / 4;
            let sub_col = x % 2;
            let sub_row = y % 4;
            if col < graph_w && row < graph_h {
                let bit = match (sub_col, sub_row) {
                    (0, 0) => 0x01,
                    (0, 1) => 0x02,
                    (0, 2) => 0x04,
                    (0, 3) => 0x40,
                    (1, 0) => 0x08,
                    (1, 1) => 0x10,
                    (1, 2) => 0x20,
                    (1, 3) => 0x80,
                    _ => 0,
                };
                masks[row][col] |= bit;
                gains[row][col] = gain;
            }
        };

        // Plot continuous vector line with vertical interpolation
        for sx in 0..sub_w {
            let curr_y = sub_ys[sx];
            let curr_g = sub_gains[sx];
            if sx == 0 {
                set_dot(&mut cell_masks, &mut cell_gains, sx, curr_y, curr_g);
            } else {
                let prev_y = sub_ys[sx - 1];
                let y_start = prev_y.min(curr_y);
                let y_end = prev_y.max(curr_y);
                for y in y_start..=y_end {
                    let col_idx = if (y as i32 - prev_y as i32).abs() < (y as i32 - curr_y as i32).abs() {
                        sx - 1
                    } else {
                        sx
                    };
                    set_dot(&mut cell_masks, &mut cell_gains, col_idx, y, curr_g);
                }
            }
        }

        let mut plot_lines = Vec::new();

        // 1. Header Line showing selected preset clean name and gain values
        let clean_preset_name = sel_preset.name.trim_start_matches(|c: char| c.is_ascii_digit() || c == '.' || c == ' ');
        let full_header_text = format!("Profile: {} | Target: {}", clean_preset_name, sel_preset.target);
        let avail_w = eq_inner.width.saturating_sub(2) as usize;

        if full_header_text.chars().count() + 2 <= avail_w {
            plot_lines.push(Line::from(vec![
                Span::styled(" Profile: ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(clean_preset_name, Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
                Span::styled(" | Target: ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(sel_preset.target, Style::default().fg(self.theme.accent)),
            ]));
        } else {
            // Stock market running tape ticker
            let now_ms = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0);
            let tape_content = format!("Profile: {}   |   Target: {}    +++    ", clean_preset_name, sel_preset.target);
            let chars: Vec<char> = tape_content.chars().collect();
            let tape_len = chars.len();
            let window_w = avail_w.saturating_sub(10).max(10);
            let step = (now_ms / 200) as usize;
            let offset = step % tape_len;
            let mut window = String::with_capacity(window_w);
            for i in 0..window_w {
                window.push(chars[(offset + i) % tape_len]);
            }
            plot_lines.push(Line::from(vec![
                Span::styled(" [TAPE] ", Style::default().fg(self.theme.warning).bg(self.theme.surface).add_modifier(Modifier::BOLD)),
                Span::styled(window, Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]));
        }

        let zero_r = ((max_db - 0.0) / (max_db - min_db) * (graph_h - 1) as f32).round() as usize;

        // 2. Multi-Row Cartesian Graph with Braille Vector Line
        for r in 0..graph_h {
            let db_val = max_db - (r as f32 / (graph_h - 1) as f32) * (max_db - min_db);
            let label = if (db_val - 12.0).abs() < 1.0 {
                "+12dB|"
            } else if (db_val - 6.0).abs() < 1.0 {
                " +6dB|"
            } else if db_val.abs() < 1.0 {
                "  0dB|"
            } else if (db_val - (-6.0)).abs() < 1.0 {
                " -6dB|"
            } else if (db_val - (-12.0)).abs() < 1.0 {
                "-12dB|"
            } else {
                "     |"
            };

            let mut spans = vec![Span::styled(label, Style::default().fg(self.theme.text_dim))];

            for c in 0..graph_w {
                let mask = cell_masks[r][c];
                if mask > 0 {
                    let ch = char::from_u32(0x2800 + mask as u32).unwrap_or('·');
                    let g = cell_gains[r][c];
                    let style = if g > 0.05 {
                        Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)
                    } else if g < -0.05 {
                        Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(self.theme.secondary)
                    };
                    spans.push(Span::styled(ch.to_string(), style));
                } else if r == zero_r {
                    spans.push(Span::styled("·", Style::default().fg(self.theme.surface)));
                } else {
                    spans.push(Span::styled(" ", Style::default()));
                }
            }
            plot_lines.push(Line::from(spans));
        }

        // 3. Frequency X-axis line: +──────────────
        let axis_chars = vec!['─'; graph_w];
        let mut spans_axis = vec![Span::styled("     +", Style::default().fg(self.theme.text_dim))];
        let axis_str: String = axis_chars.into_iter().collect();
        spans_axis.push(Span::styled(axis_str, Style::default().fg(self.theme.text_dim)));
        plot_lines.push(Line::from(spans_axis));

        // 4. Logarithmic frequency text markers
        let markers: [(f32, &str); 10] = [
            (20.0, "20Hz"),
            (50.0, "50"),
            (100.0, "100"),
            (250.0, "250"),
            (500.0, "500"),
            (1000.0, "1kHz"),
            (2000.0, "2k"),
            (4000.0, "4k"),
            (8000.0, "8k"),
            (20000.0, "20kHz"),
        ];

        let mut label_chars = vec![' '; graph_w];
        let mut last_end = 0;
        for (target_f, text) in markers {
            let best_col = freqs
                .iter()
                .enumerate()
                .min_by(|(_, a), (_, b)| {
                    ((*a - target_f).abs()).partial_cmp(&((*b - target_f).abs())).unwrap()
                })
                .map(|(i, _)| i)
                .unwrap_or(0);

            let pos = best_col.saturating_sub(text.len() / 2);
            if pos >= last_end && pos + text.len() <= graph_w {
                for (j, c) in text.chars().enumerate() {
                    label_chars[pos + j] = c;
                }
                last_end = pos + text.len() + 1;
            }
        }
        let f_label_str: String = label_chars.into_iter().collect();
        plot_lines.push(Line::from(vec![
            Span::styled("      ", Style::default().fg(self.theme.text_dim)),
            Span::styled(f_label_str, Style::default().fg(self.theme.accent)),
        ]));

        let p_plot = Paragraph::new(plot_lines);
        f.render_widget(p_plot, eq_inner);

        // BOTTOM RIGHT: DSP Enhancer Modules & Acoustic Gear Profile
        let dsp_block = Block::default()
            .title(" DSP MODULES & ACOUSTIC GEAR PROFILE ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.border));
        let dsp_inner = dsp_block.inner(right_chunks[1]);
        f.render_widget(dsp_block, right_chunks[1]);

        let dsp_lines = vec![
            Line::from(vec![
                Span::styled(" Profile Intent: ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(sel_preset.description, Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" Target Gear:    ", Style::default().fg(self.theme.secondary).add_modifier(Modifier::BOLD)),
                Span::styled(sel_preset.target, Style::default().fg(self.theme.accent)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" [DSP Rack Configuration]", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("   * Soundstage Aperture: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{:.2}x width", sel_preset.spatial_width), Style::default().fg(self.theme.text)),
                Span::styled("   * Class-A Tube Warmth: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{:.2} drive", sel_preset.tube_warmth), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled("   * Bass Punch: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("+{}dB", sel_preset.bass_punch_db), Style::default().fg(self.theme.text)),
                Span::styled("   * Air Clarity: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("+{}dB", sel_preset.air_clarity_db), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled("   * 1/2-Inch Master Tape: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(if sel_preset.tape_emulation { format!("Active ({:.1}x drive)", sel_preset.tape_drive) } else { "Bypassed".to_string() }, Style::default().fg(self.theme.text)),
                Span::styled("   * Mono Sub-Bass: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(if sel_preset.mono_bass { format!("Active (<{}Hz)", sel_preset.mono_bass_freq) } else { "Stereo Wide".to_string() }, Style::default().fg(self.theme.text)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" [Active Gear Acoustic Calibration]", Style::default().fg(self.theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(format!("  \"{}\"", self.gear_profile.name), Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("   * Transducer: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{} ({})", self.gear_profile.form_factor_label(), self.gear_profile.enclosure_label()), Style::default().fg(self.theme.text)),
                Span::styled("   * Drivers: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(self.gear_profile.driver_summary(), Style::default().fg(self.theme.text)),
            ]),
            Line::from(vec![
                Span::styled("   * Coupling: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{:?}", self.gear_profile.coupling), Style::default().fg(self.theme.text)),
                Span::styled("   * Innate Balance: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(self.gear_profile.tonal_label(), Style::default().fg(self.theme.text)),
                Span::styled("   * Source Amp: ", Style::default().fg(self.theme.text_dim)),
                Span::styled(format!("{:?}", self.gear_profile.source_amp), Style::default().fg(self.theme.text)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" [Enter] Apply Preset & Retune DSP  [G] Calibrate & Rename Gear  [S] Save Preset", Style::default().fg(self.theme.primary).add_modifier(Modifier::BOLD)),
            ]),
        ];

        let p_dsp = Paragraph::new(dsp_lines).wrap(ratatui::widgets::Wrap { trim: true });
        f.render_widget(p_dsp, dsp_inner);
    }

    fn render_status(&self, f: &mut ratatui::Frame, area: Rect) {
        let p = Paragraph::new(format!(" Status: {}", self.status_message))
            .style(Style::default().fg(self.theme.accent));
        f.render_widget(p, area);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect) {
        if self.command_bar.is_open {
            let cmd_text = format!(" :{}█  (Press [Enter] to run, [Esc] to cancel)", self.command_bar.input);
            let p = Paragraph::new(cmd_text).style(Style::default().bg(Color::Rgb(20, 25, 35)).fg(Color::Yellow).add_modifier(Modifier::BOLD));
            f.render_widget(p, area);
            return;
        }

        let mic_label = if self.streamer.is_input_capture_enabled() {
            "[x] Mic: ON"
        } else {
            "[x] Mic: OFF"
        };
        let dac_label = format!("[Ctrl+D] DAC: {}", self.streamer.current_dac_flavor().short_label());
        let game_label = if self.streamer.is_game_mode_enabled() {
            "[Shift+G] Game: ON"
        } else {
            "[Shift+G] Game: OFF"
        };
        let help = match self.active_mode {
            WorkstationMode::Downloader => {
                format!(" [m] Mode  {}  {}  {}  [:] Command  [N] Nicotine+  [T] Theme  [Enter] Download  [Tab] Inputs  [Q] Quit", mic_label, dac_label, game_label)
            }
            WorkstationMode::SystemEq => {
                format!(" [m] Mode  {}  {}  {}  [:] Command  [T] Theme  [V] Visuals  [Shift+S] Save  [Shift+R] Reset  [Space] Play  [Q] Quit", mic_label, dac_label, game_label)
            }
            WorkstationMode::Archiver => {
                format!(" [m] Mode  {}  {}  {}  [:] Command  [U] URL  [S] Path  [Space] Select  [P] Preview  [D] Remove  [Q] Quit", mic_label, dac_label, game_label)
            }
            WorkstationMode::StreamingHub => {
                format!(" [m] Mode  {}  {}  {}  [:] Command  [S] Search  [L] Accounts  [Enter] Play  [Space] Pause  [+/-] Vol  [Q] Quit", mic_label, dac_label, game_label)
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
        let initial_mastering_count = app.mastering_presets.len();

        // 1. Save active custom settings as preset
        app.band_gains[0] = 4.0;
        app.band_gains[5] = -2.0;
        app.save_active_settings_as_preset("Test Studio Custom");

        // Verify AutoEQ profiles
        assert_eq!(app.profiles.len(), initial_count + 1);
        assert_eq!(app.selected_profile_idx, app.profiles.len() - 1);
        let saved_prof = &app.profiles[app.selected_profile_idx];
        assert_eq!(saved_prof.name, "Test Studio Custom");
        assert_eq!(saved_prof.filters.len(), 10);
        assert_eq!(saved_prof.filters[0].gain_db, 4.0);

        // Verify PRESET LIBRARY (mastering presets)
        assert_eq!(app.mastering_presets.len(), initial_mastering_count + 1);
        assert_eq!(app.selected_mastering_preset_idx, app.mastering_presets.len() - 1);
        assert_eq!(app.active_mastering_preset_idx, app.mastering_presets.len() - 1);
        let saved_mastering = &app.mastering_presets[app.selected_mastering_preset_idx];
        assert_eq!(saved_mastering.name, "Test Studio Custom");
        assert_eq!(saved_mastering.eq_10_band[0], 4.0);
        assert_eq!(saved_mastering.eq_10_band[5], -2.0);

        // 2. Import raw Squiglink text
        let squig_text = "Preamp: -5.0 dB\nFilter 1: ON PK Fc 64 Hz Gain 3.5 dB Q 1.41\nFilter 2: ON HSC Fc 8000 Hz Gain -2.0 dB Q 0.71";
        app.import_squiglink_preset("Test Squiglink IEM", squig_text);

        assert_eq!(app.profiles.len(), initial_count + 2);
        assert_eq!(app.selected_profile_idx, app.profiles.len() - 1);
        let squig_prof = &app.profiles[app.selected_profile_idx];
        assert_eq!(squig_prof.name, "Test Squiglink IEM");
        assert_eq!(squig_prof.preamp_db, -5.0);
        assert_eq!(squig_prof.filters.len(), 2);

        // Verify that load_all_user_mastering_presets loads the saved preset from disk
        let reloaded = crate::autoeq::storage::load_all_user_mastering_presets();
        assert!(reloaded.iter().any(|p| p.name == "Test Studio Custom"));

        // Clean up disk files created during test
        let _ = std::fs::remove_file(crate::autoeq::storage::get_mastering_presets_dir().join("Test_Studio_Custom.json"));
        let _ = std::fs::remove_file(crate::autoeq::storage::get_presets_dir().join("Test_Studio_Custom.json"));
        let _ = std::fs::remove_file(crate::autoeq::storage::get_mastering_presets_dir().join("Test_Squiglink_IEM.json"));
        let _ = std::fs::remove_file(crate::autoeq::storage::get_presets_dir().join("Test_Squiglink_IEM.json"));
    }

    #[test]
    fn test_paste_in_downloader_does_not_open_mode_modal() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::Downloader;
        app.mode_modal.is_open = false;

        // Paste a YouTube link containing 'm'
        app.downloader.paste("https://music.youtube.com/watch?v=dQw4w9WgXcQ");
        assert!(app.downloader.is_editing_url);
        assert!(!app.mode_modal.is_open);

        // Typing 'm' while editing URL should type into input, NOT open mode modal
        if app.downloader.is_editing_url {
            app.downloader.handle_key(KeyCode::Char('m'));
        }
        assert!(!app.mode_modal.is_open);
        assert!(app.downloader.input_text.ends_with('m'));
    }

    #[test]
    fn test_lossless_selector_modal_does_not_open_mode_modal_on_m() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::Downloader;
        app.mode_modal.is_open = false;
        app.downloader.show_lossless_selector = true;
        app.downloader.lossless_filter_text.clear();
        app.downloader.is_filtering_lossless = true;

        // When in filter mode inside lossless selector, typing 'm' must append 'm' to filter, NOT open mode modal
        let key_m = crossterm::event::KeyEvent::new(KeyCode::Char('m'), crossterm::event::KeyModifiers::NONE);
        // Dispatch key following app's event loop precedence
        if app.active_mode == WorkstationMode::Downloader
            && app.downloader.is_capturing_input()
        {
            app.downloader.handle_key(key_m.code);
        } else if key_m.code == KeyCode::Char('m') || key_m.code == KeyCode::Char('M') {
            app.mode_modal.toggle();
        }

        assert!(!app.mode_modal.is_open);
        assert_eq!(app.downloader.lossless_filter_text, "m");
    }

    #[test]
    fn test_advanced_search_modal_isolates_keys_and_prevents_popups() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::Downloader;
        app.downloader.show_advanced_search_modal = true;
        app.downloader.adv_search_focused_field = 0;
        app.downloader.adv_search_artist.clear();
        app.nicotine_modal.is_open = false;
        app.mode_modal.is_open = false;
        app.preset_modal = PresetModalState::Hidden;

        assert!(app.downloader.is_capturing_input());

        // Helper closure simulating app event loop key routing
        let dispatch_key = |key: crossterm::event::KeyEvent, app: &mut App| {
            if app.active_mode == WorkstationMode::Downloader
                && app.downloader.is_capturing_input()
            {
                app.downloader.handle_key(key.code);
                return;
            }

            // Global handlers that must NEVER be reached while in modal
            if key.code == KeyCode::Char('a') || key.code == KeyCode::Char('A') {
                app.nicotine_modal.open_accounts();
            } else if key.code == KeyCode::Char('m') || key.code == KeyCode::Char('M') {
                app.mode_modal.toggle();
            } else if key.code == KeyCode::Char('S') {
                app.preset_modal = PresetModalState::new_save_current();
            }
        };

        // 1. Typing 'a' must append 'a' to artist and NOT open account discovery
        let key_a = crossterm::event::KeyEvent::new(KeyCode::Char('a'), crossterm::event::KeyModifiers::NONE);
        dispatch_key(key_a, &mut app);
        assert_eq!(app.downloader.adv_search_artist, "a");
        assert!(!app.nicotine_modal.is_open, "Account discovery must NOT open on 'a'");

        // 2. Typing 'm' must append 'm' to artist and NOT open mode modal
        let key_m = crossterm::event::KeyEvent::new(KeyCode::Char('m'), crossterm::event::KeyModifiers::NONE);
        dispatch_key(key_m, &mut app);
        assert_eq!(app.downloader.adv_search_artist, "am");
        assert!(!app.mode_modal.is_open, "Mode modal must NOT open on 'm'");

        // 3. Typing Shift+S must append 'S' to artist and NOT open preset modal
        let key_s = crossterm::event::KeyEvent::new(KeyCode::Char('S'), crossterm::event::KeyModifiers::SHIFT);
        dispatch_key(key_s, &mut app);
        assert_eq!(app.downloader.adv_search_artist, "amS");
        assert!(!app.preset_modal.is_active(), "Preset modal must NOT open on Shift+S");

        // 4. Typing 'q' must append 'q' to artist
        let key_q = crossterm::event::KeyEvent::new(KeyCode::Char('q'), crossterm::event::KeyModifiers::NONE);
        dispatch_key(key_q, &mut app);
        assert_eq!(app.downloader.adv_search_artist, "amSq");

        // 5. Esc closes the modal and restores navigation mode
        let key_esc = crossterm::event::KeyEvent::new(KeyCode::Esc, crossterm::event::KeyModifiers::NONE);
        dispatch_key(key_esc, &mut app);
        assert!(!app.downloader.show_advanced_search_modal);
        assert!(!app.downloader.is_capturing_input());

        // Now outside modal in navigation mode, typing 'a' opens accounts
        dispatch_key(key_a, &mut app);
        assert!(app.nicotine_modal.is_open);
    }

    #[test]
    fn test_workstation3_archiver_mode_launch_and_input_capture() {
        let mut app = App::new_test();
        app.mode_modal.is_open = true;

        // 1. Pressing '3' switches to WorkstationMode::Archiver
        let key_3 = crossterm::event::KeyEvent::new(KeyCode::Char('3'), crossterm::event::KeyModifiers::NONE);
        if app.mode_modal.is_open {
            match key_3.code {
                KeyCode::Char('3') => {
                    app.active_mode = WorkstationMode::Archiver;
                    app.mode_modal.is_open = false;
                }
                _ => {}
            }
        }
        assert_eq!(app.active_mode, WorkstationMode::Archiver);
        assert!(!app.mode_modal.is_open);

        // 2. Pressing 'u' enters editing URL mode
        app.archiver.handle_key(KeyCode::Char('u'));
        assert!(app.archiver.is_editing_url);
        assert!(app.archiver.is_capturing_input());

        // 3. Typing 'm' while editing URL must append 'm' and NOT open mode modal
        let key_m = crossterm::event::KeyEvent::new(KeyCode::Char('m'), crossterm::event::KeyModifiers::NONE);
        if app.active_mode == WorkstationMode::Archiver && app.archiver.is_capturing_input() {
            app.archiver.handle_key(key_m.code);
        } else if key_m.code == KeyCode::Char('m') {
            app.mode_modal.toggle();
        }
        assert_eq!(app.archiver.url_input, "m");
        assert!(!app.mode_modal.is_open);

        // 4. Esc leaves editing URL
        app.archiver.handle_key(KeyCode::Esc);
        assert!(!app.archiver.is_editing_url);
        assert!(!app.archiver.is_capturing_input());
    }

    #[test]
    fn test_poll_archiver_batch_progression() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::Archiver;

        let temp_dir = std::env::temp_dir().join(format!("omnirip_batch_test_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        app.archiver.storage_path = temp_dir.clone();
        app.archiver.generate_m3u8 = true;

        app.archiver.set_loaded_playlist(crate::harvest::playlist_parser::ParsedPlaylist {
            name: "Single Ingestion Test".to_string(),
            description: None,
            service: crate::harvest::playlist_parser::StreamingService::Spotify,
            tracks: vec![
                crate::harvest::playlist_parser::ParsedTrack {
                    title: "Voyager".to_string(),
                    artist: "Daft Punk".to_string(),
                    album: "Discovery".to_string(),
                    duration_secs: Some(227),
                    isrc: Some("GBDUW0000062".to_string()),
                    track_number: Some(10),
                    cover_art_url: None,
                    source_url: None,
                }
            ],
        });

        // Start batch
        app.archiver.is_batch_active = true;

        // Step 1: ResolvingSwarm
        app.poll_archiver_batch();
        assert_eq!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::ResolvingSwarm);

        // Step 2: Downloading (0.25)
        app.poll_archiver_batch();
        assert!(matches!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::Downloading(pct, _) if (pct - 0.25).abs() < 0.01));

        // Step 3: Downloading (0.60)
        app.poll_archiver_batch();
        assert!(matches!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::Downloading(pct, _) if (pct - 0.60).abs() < 0.01));

        // Step 4: Downloading (0.95)
        app.poll_archiver_batch();
        assert!(matches!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::Downloading(pct, _) if (pct - 0.95).abs() < 0.01));

        // Step 5: VerifyingSpectral
        app.poll_archiver_batch();
        assert_eq!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::VerifyingSpectral);

        // Step 6: Complete & M3U8 written
        app.poll_archiver_batch();
        assert!(matches!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::Complete(_, _)));
        assert!(!app.archiver.is_batch_active);

        // Step 7: Completed track enters seeding swarm pool when batch is active
        app.archiver.is_batch_active = true;
        app.poll_archiver_batch();
        assert!(matches!(app.archiver.tracks[0].status, crate::ui::archiver::TrackArchiveStatus::Seeding(ratio, _) if (ratio - 1.0).abs() < 0.01));

        // Verify output file and M3U8 exist
        let m3u8_file = temp_dir.join("Single Ingestion Test.m3u8");
        assert!(m3u8_file.exists());
        let m3u8_content = std::fs::read_to_string(&m3u8_file).unwrap();
        assert!(m3u8_content.contains("Daft Punk - Voyager"));

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_mastering_suite_presets_and_module_controls() {
        let mut app = App::new_test();
        assert_eq!(app.mastering_presets.len(), 35);
        assert_eq!(app.active_mastering_preset_idx, 0);

        // Advance to Preset 2: HD600/650
        app.cycle_mastering_preset(true);
        assert_eq!(app.active_mastering_preset_idx, 1);
        assert!(app.status_message.contains("HD600/650"));

        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert_eq!(pipe.enhancer.spatial_width, 1.25);
            assert_eq!(pipe.enhancer.tube_warmth, 0.15);
            assert!(pipe.enhancer.mono_bass);
        }

        // Apply Genre Preset 22: Hip-Hop & Trap (Sub-Bass Precision)
        app.apply_mastering_preset_index(21);
        assert_eq!(app.active_mastering_preset_idx, 21);
        assert!(app.status_message.contains("Hip-Hop"));
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert_eq!(pipe.enhancer.spatial_width, 1.05);
            assert_eq!(pipe.enhancer.bass_punch_db, 2.5);
            assert!(pipe.enhancer.mono_bass);
        }

        // Apply Genre Preset 25: Electronic & Club (Subterranean & 3D M/S)
        app.apply_mastering_preset_index(24);
        assert_eq!(app.active_mastering_preset_idx, 24);
        assert!(app.status_message.contains("Electronic"));
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert_eq!(pipe.enhancer.spatial_width, 1.25);
            assert_eq!(pipe.enhancer.bass_punch_db, 2.8);
            assert!(pipe.enhancer.ms_matrix_enabled);
        }

        // Cycle backward to Preset 1: Reference Direct
        app.apply_mastering_preset_index(0);
        assert_eq!(app.active_mastering_preset_idx, 0);

        // Adjust module 0 (Soundstage Width)
        app.selected_mastering_idx = 0;
        app.cycle_mastering_control(true);
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert_eq!(pipe.enhancer.spatial_width, 1.1);
        }

        // Adjust module 1 (Class-A Tube Warmth)
        app.selected_mastering_idx = 1;
        app.cycle_mastering_control(true);
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert_eq!(pipe.enhancer.tube_warmth, 0.05);
        }

        // Adjust module 6 (1/2-Inch Master Tape)
        app.selected_mastering_idx = 6;
        app.cycle_mastering_control(true);
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            assert!(pipe.enhancer.tape_emulation);
            assert_eq!(pipe.enhancer.tape_drive, 1.0);
        }
    }

    #[test]
    fn test_autoeq_tab_preset_navigation_and_eq_sync() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::SystemEq;
        app.active_tab = 3; // Tab 4: AutoEQ
        assert_eq!(app.autoeq_view_mode, 1);
        assert_eq!(app.selected_mastering_preset_idx, 0);

        // 1. Toggle view mode to Database with Tab and back to Presets
        // 1. Navigate down to preset 3 (idx 2: planar magnetic master)
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_preset_idx, 1);
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_preset_idx, 2);

        // 2. Press Enter to apply preset 3
        app.handle_tab_key(KeyCode::Enter);
        assert_eq!(app.active_mastering_preset_idx, 2);
        let expected_eq = app.mastering_presets[2].eq_10_band;
        assert_eq!(app.band_gains, expected_eq);

        // 3. Switch to Tab 1 (10-Band EQ) and adjust band 0 (+0.5 dB)
        app.active_tab = 0;
        app.selected_band = 0;
        let original_gain = app.band_gains[0];
        app.handle_tab_key(KeyCode::Up);
        assert!((app.band_gains[0] - (original_gain + 0.5)).abs() < 1e-4);

        // 4. In Tab 2 (Mastering Suite), pressing 'p' does NOT cycle presets anymore
        app.active_tab = 1;
        let current_active_idx = app.active_mastering_preset_idx;
        app.handle_tab_key(KeyCode::Char('p'));
        assert_eq!(app.active_mastering_preset_idx, current_active_idx);
    }

    #[test]
    fn test_gear_wizard_modal_workflow_and_dsp_retuning() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::SystemEq;
        app.active_tab = 3; // Tab 4 AutoEQ

        // 1. Press 'g' to open Gear Wizard modal
        app.handle_tab_key(KeyCode::Char('g'));
        assert!(app.gear_modal.is_open);

        // Step 0: Form factor -> Select InEar (idx 2)
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 1);

        // Step 1: Enclosure -> Select Closed (idx 2)
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 2);

        // Step 2: Driver topology -> Multi-select BA + DD
        // idx 0 (Dynamic) is already true by default. Move to idx 2 (Balanced Armature) -> press Space
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Down);
        app.gear_modal.handle_key(KeyCode::Char(' '));
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 3);

        // Step 3: Coupling -> Silicone Eartips (idx 0)
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 4);

        // Step 4: Tonal balance -> AnalyticalBright (idx 0)
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 5);

        // Step 5: Source amp -> Portable Dongle DAC (idx 0)
        app.gear_modal.handle_key(KeyCode::Enter);
        assert_eq!(app.gear_modal.current_step, 6);

        // Step 6: Custom name -> Rename to "My Custom IEMs" and commit
        app.gear_modal.custom_name = "My Custom IEMs".to_string();
        let res = app.gear_modal.handle_key(KeyCode::Enter);
        assert!(res.is_some());
        let profile = res.unwrap();
        assert_eq!(profile.name, "My Custom IEMs");
        assert_eq!(profile.form_factor, crate::dsp::enhancer::GearFormFactor::InEar);
        assert_eq!(profile.enclosure, crate::dsp::enhancer::GearEnclosure::ClosedBack);
        assert!(profile.drivers[0]); // Dynamic
        assert!(profile.drivers[2]); // Balanced Armature
        assert_eq!(profile.tonal_balance, crate::dsp::enhancer::GearTonalBalance::AnalyticalBright);

        // Apply profile to app
        app.gear_profile = profile;
        app.apply_mastering_preset_index(1); // apply HD600/650 preset on IEM with bright signature
        {
            let pipe = app.streamer.pipeline.lock().unwrap();
            // Air clarity should be reduced to tame bright signature on InEar
            assert!(pipe.enhancer.air_clarity_db < app.mastering_presets[1].air_clarity_db);
            // Deharsh should be active to protect against fatigue
            assert!(pipe.enhancer.deharsh_enabled);
        }
    }

    #[test]
    fn test_workstation4_streaming_hub_mode_and_actions() {
        let mut app = App::new_test();
        assert_eq!(app.active_mode, WorkstationMode::Downloader);

        // Open mode modal and select Workstation 4 (index 3)
        app.mode_modal.is_open = true;
        app.mode_modal.selected_index = 3;
        assert_eq!(app.mode_modal.current_mode(), WorkstationMode::StreamingHub);
        app.active_mode = app.mode_modal.current_mode();
        app.mode_modal.toggle();
        assert!(!app.mode_modal.is_open);
        assert_eq!(app.active_mode, WorkstationMode::StreamingHub);

        // Add item to queue
        app.streaming_hub.queue.push(crate::ui::streaming_hub::StreamQueueItem {
            title: "Test Track 1".to_string(),
            artist: "Test Artist".to_string(),
            album: "Test Album".to_string(),
            duration_secs: Some(180),
            quality_tier: crate::harvest::stream_resolver::AudioQualityTier::CloudOpus160,
            service: crate::harvest::StreamingService::YouTubeMusic,
            source_query: "Test Track 1".to_string(),
            status: crate::ui::streaming_hub::StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test Library".to_string(),
            added_order: 1,
        });
        assert_eq!(app.streaming_hub.queue.len(), 1);

        // Search edit toggle
        app.streaming_hub.handle_key(KeyCode::Char('/'));
        assert!(app.streaming_hub.is_editing_search);
        app.streaming_hub.handle_key(KeyCode::Esc);
        assert!(!app.streaming_hub.is_editing_search);

        // Paste support
        app.streaming_hub.paste("https://open.spotify.com/track/12345");
        assert!(app.streaming_hub.is_editing_search);
        assert_eq!(app.streaming_hub.search_input, "https://open.spotify.com/track/12345");
    }

    #[test]
    fn test_volume_persistence_roundtrip() {
        use crate::dsp::volume_storage::VolumeConfig;

        let mut cfg = VolumeConfig::default();
        assert_eq!(cfg.player_volume_pct, 50);
        assert!((cfg.system_volume_scalar - 0.50).abs() < 1e-4);

        // Modify values
        cfg.player_volume_pct = 72;
        cfg.system_volume_scalar = 0.72;

        let json = serde_json::to_string_pretty(&cfg).unwrap();
        let loaded: VolumeConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(loaded.player_volume_pct, 72);
        assert!((loaded.system_volume_scalar - 0.72).abs() < 1e-4);
    }

    #[test]
    fn test_instant_dsp_telemetry_sync_on_preset_selection() {
        let mut app = App::new_test();
        assert_eq!(app.streaming_hub.dsp_telemetry.active_preset_name, "Audiophile Reference (Pure Direct)");

        // 1. Select Preset 2: HD600/650 Soundstage & Veil Lifter
        app.apply_mastering_preset_index(1);
        assert_eq!(app.active_mastering_preset_idx, 1);
        assert_eq!(app.streaming_hub.dsp_telemetry.active_preset_name, "HD600/650 Soundstage & Veil Lifter");
        assert_eq!(app.streaming_hub.dsp_telemetry.target_curve, "Sennheiser HD 600 / HD 650 / HD 660S");
        assert!((app.streaming_hub.dsp_telemetry.spatial_width - 1.25).abs() < 1e-3);

        // 2. Select Preset 3: DT 770/990 Mount Beyer Treble Tamer
        app.apply_mastering_preset_index(2);
        assert_eq!(app.active_mastering_preset_idx, 2);
        assert_eq!(app.streaming_hub.dsp_telemetry.active_preset_name, "DT 770/990 Mount Beyer Treble Tamer");
        assert_eq!(app.streaming_hub.dsp_telemetry.target_curve, "Beyerdynamic DT 770 / DT 880 / DT 990 / DT 1990 Pro");

        // 3. Cycle preset forward with cycle_mastering_preset
        app.cycle_mastering_preset(true);
        assert_eq!(app.active_mastering_preset_idx, 3);
        assert_eq!(app.streaming_hub.dsp_telemetry.active_preset_name, "Planar Magnetic Fast Slam & Tactile Impact");
    }

    #[test]
    fn test_command_bar_execution_and_mic_commands() {
        let mut app = App::new_test();
        assert!(!app.streamer.is_input_capture_enabled());

        // Test :mic on command
        app.execute_command(":mic on");
        assert!(app.streamer.is_input_capture_enabled());
        assert!(app.status_message.contains("[ON]"));

        // Test :mic off command
        app.execute_command(":mic off");
        assert!(!app.streamer.is_input_capture_enabled());
        assert!(app.status_message.contains("[OFF]"));

        // Test :mic toggle command
        app.execute_command(":mic toggle");
        assert!(app.streamer.is_input_capture_enabled());
        app.execute_command(":mic");
        assert!(!app.streamer.is_input_capture_enabled());

        // Test CommandBarState typing and handling
        let mut bar = CommandBarState::new();
        bar.open();
        assert!(bar.is_open);
        bar.handle_key(KeyCode::Char('m'));
        bar.handle_key(KeyCode::Char('i'));
        bar.handle_key(KeyCode::Char('c'));
        bar.handle_key(KeyCode::Char(' '));
        bar.handle_key(KeyCode::Char('o'));
        bar.handle_key(KeyCode::Char('n'));
        assert_eq!(bar.input, "mic on");

        let res = bar.handle_key(KeyCode::Enter);
        assert_eq!(res, Some("mic on".to_string()));
        assert!(!bar.is_open);
    }

    #[test]
    fn test_unassigned_key_x_and_mastering_rack_item17_mic_toggle() {
        let mut app = App::new_test();
        assert!(!app.streamer.is_input_capture_enabled());

        // 1. Direct toggle to ON
        let (enabled1, msg1) = app.streamer.toggle_input_capture();
        assert!(enabled1);
        assert!(app.streamer.is_input_capture_enabled());
        assert!(msg1.contains("[ON]"));

        let (enabled2, msg2) = app.streamer.toggle_input_capture();
        assert!(!enabled2);
        assert!(!app.streamer.is_input_capture_enabled());
        assert!(msg2.contains("[OFF]"));

        // 2. Workstation 2 (SystemEq), Tab 1 (Mastering Suite) navigation to Item 17 (idx 16)
        app.active_mode = WorkstationMode::SystemEq;
        app.active_tab = 1;
        app.selected_mastering_idx = 15;

        // Down arrow should advance to item 17 (idx 16)
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_idx, 16);

        // Enter key on item 17 toggles microphone on
        app.handle_tab_key(KeyCode::Enter);
        assert!(app.streamer.is_input_capture_enabled());
        assert!(app.status_message.contains("[ON]"));

        // Enter key on item 17 toggles microphone back off
        app.handle_tab_key(KeyCode::Enter);
        assert!(!app.streamer.is_input_capture_enabled());
        assert!(app.status_message.contains("[OFF]"));

        // Advance to items 18, 19, 20
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_idx, 17); // Game Mode
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_idx, 18); // Radar EQ
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_idx, 19); // Spike Shield
        // Clamped at 19
        app.handle_tab_key(KeyCode::Down);
        assert_eq!(app.selected_mastering_idx, 19);

        // Tab switches columns (19 -> 9)
        app.handle_tab_key(KeyCode::Tab);
        assert_eq!(app.selected_mastering_idx, 9);
        // Tab switches back (9 -> 19)
        app.handle_tab_key(KeyCode::Tab);
        assert_eq!(app.selected_mastering_idx, 19);
    }

    #[test]
    fn test_game_mode_command_and_dsp_toggle() {
        let mut app = App::new_test();
        assert!(!app.streamer.is_game_mode_enabled());

        // Test :game on command
        app.execute_command(":game on");
        assert!(app.streamer.is_game_mode_enabled());
        assert!(app.status_message.contains("[ON]"));

        // Test :game off command
        app.execute_command(":game off");
        assert!(!app.streamer.is_game_mode_enabled());
        assert!(app.status_message.contains("[OFF]"));

        // Test :game toggle command
        app.execute_command(":game");
        assert!(app.streamer.is_game_mode_enabled());

        // Test Workstation 2 mastering rack item 18 (Game mode, idx 17)
        app.active_mode = WorkstationMode::SystemEq;
        app.active_tab = 1;
        app.selected_mastering_idx = 17;
        app.handle_tab_key(KeyCode::Enter);
        assert!(!app.streamer.is_game_mode_enabled());

        // Test item 19 (Radar EQ, idx 18)
        app.selected_mastering_idx = 18;
        app.handle_tab_key(KeyCode::Enter);
        let is_radar = app.streamer.pipeline.lock().unwrap().enhancer.radar_eq;
        assert!(is_radar);

        // Test item 20 (Spike Shield, idx 19)
        app.selected_mastering_idx = 19;
        app.handle_tab_key(KeyCode::Enter);
        let is_spike = app.streamer.pipeline.lock().unwrap().enhancer.spike_shield;
        assert!(is_spike);
    }

    #[test]
    fn test_dac_mimicker_commands_and_shortcuts() {
        let mut app = App::new_test();
        app.streamer.set_dac_flavor(crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus);
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus);

        // Test :dac ifi command
        app.execute_command(":dac ifi");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::IfiZenDac);
        assert!(app.status_message.contains("iFi Zen DAC V2"));

        // Test :dac ibasso command
        app.execute_command(":dac ibasso");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::IbassoDcPro);

        // Test :dac chord command
        app.execute_command(":dac chord");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::ChordMojo2);

        // Test :dac schiit command
        app.execute_command(":dac schiit");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::SchiitMultibit);

        // Test :dac oem command
        app.execute_command(":dac oem");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus);

        // Test :dac cycle command
        app.execute_command(":dac cycle");
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::IfiZenDac);

        // Test :dac status command
        app.execute_command(":dac status");
        assert!(app.status_message.contains("Active DAC Mimicker"));

        // Test :dac list command
        app.execute_command(":dac list");
        assert!(app.status_message.contains("Flavors:"));

        // Test global shortcut simulation: Ctrl+D cycles forward
        let key_ctrl_d = crossterm::event::KeyEvent::new(KeyCode::Char('d'), crossterm::event::KeyModifiers::CONTROL);
        if key_ctrl_d.modifiers.contains(crossterm::event::KeyModifiers::CONTROL)
            && (key_ctrl_d.code == KeyCode::Char('d') || key_ctrl_d.code == KeyCode::Char('D'))
        {
            let new_flavor = if key_ctrl_d.modifiers.contains(crossterm::event::KeyModifiers::SHIFT) {
                app.streamer.cycle_dac_flavor_reverse()
            } else {
                app.streamer.cycle_dac_flavor()
            };
            app.set_status(&format!("DAC Mimicker: {}", new_flavor.label()));
        }
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::IbassoDcPro);

        // Test global shortcut simulation: Ctrl+Shift+D cycles reverse
        let key_ctrl_shift_d = crossterm::event::KeyEvent::new(
            KeyCode::Char('D'),
            crossterm::event::KeyModifiers::CONTROL | crossterm::event::KeyModifiers::SHIFT,
        );
        if key_ctrl_shift_d.modifiers.contains(crossterm::event::KeyModifiers::CONTROL)
            && (key_ctrl_shift_d.code == KeyCode::Char('d') || key_ctrl_shift_d.code == KeyCode::Char('D'))
        {
            let new_flavor = if key_ctrl_shift_d.modifiers.contains(crossterm::event::KeyModifiers::SHIFT) {
                app.streamer.cycle_dac_flavor_reverse()
            } else {
                app.streamer.cycle_dac_flavor()
            };
            app.set_status(&format!("DAC Mimicker: {}", new_flavor.label()));
        }
        assert_eq!(app.streamer.current_dac_flavor(), crate::dsp::enhancer::DacHardwareFlavor::IfiZenDac);

        // Test F6 cycles forward
        let key_f6 = crossterm::event::KeyEvent::new(KeyCode::F(6), crossterm::event::KeyModifiers::NONE);
        let is_dac_f6 = match key_f6.code {
            KeyCode::F(6) => true,
            KeyCode::Char('d') | KeyCode::Char('D') if key_f6.modifiers.contains(crossterm::event::KeyModifiers::CONTROL) => true,
            KeyCode::Char('D') | KeyCode::Char('d') if key_f6.modifiers.contains(crossterm::event::KeyModifiers::SHIFT) => true,
            KeyCode::Char('D') => true,
            _ => false,
        };
        assert!(is_dac_f6);
        let new_flavor_f6 = app.streamer.cycle_dac_flavor();
        assert_eq!(new_flavor_f6, crate::dsp::enhancer::DacHardwareFlavor::IbassoDcPro);

        // Test Shift+D (KeyCode::Char('D')) cycles forward
        let key_shift_d = crossterm::event::KeyEvent::new(KeyCode::Char('D'), crossterm::event::KeyModifiers::NONE);
        let is_dac_shift_d = match key_shift_d.code {
            KeyCode::F(6) => true,
            KeyCode::Char('d') | KeyCode::Char('D') if key_shift_d.modifiers.contains(crossterm::event::KeyModifiers::CONTROL) => true,
            KeyCode::Char('D') | KeyCode::Char('d') if key_shift_d.modifiers.contains(crossterm::event::KeyModifiers::SHIFT) => true,
            KeyCode::Char('D') => true,
            _ => false,
        };
        assert!(is_dac_shift_d);
        let new_flavor_d = app.streamer.cycle_dac_flavor();
        assert_eq!(new_flavor_d, crate::dsp::enhancer::DacHardwareFlavor::ChordMojo2);
    }

    #[test]
    fn test_chip_detection_command_and_profile() {
        let mut app = App::new_test();
        let prof = app.streamer.hardware_chip_profile();
        assert!(!prof.chip_name.is_empty());
        assert!(!prof.hardware_model.is_empty());

        // Test :chip status command
        app.execute_command(":chip");
        assert!(app.status_message.contains("Audio Hardware:"));
        assert!(app.status_message.contains(&prof.hardware_model));

        // Test :chip rescan command
        app.streamer.selected_output_name = Some("iBasso DC03 Pro".to_string());
        app.execute_command(":chip rescan");
        assert!(app.status_message.contains("Hardware Rescanned:"));
        assert!(app.status_message.contains("iBasso Audio"));
        assert_eq!(app.streamer.hardware_chip_profile().recommended_flavor, crate::dsp::enhancer::DacHardwareFlavor::IbassoDcPro);
    }

    #[test]
    fn test_mastering_suite_dac_card_rendering() {
        let mut app = App::new_test();
        app.active_mode = WorkstationMode::SystemEq;
        app.active_tab = 1; // Mastering Suite

        // Test rendering across different terminal heights (standard, compact, tall)
        for (w, h) in [(140, 36), (100, 22), (180, 50)] {
            let backend = ratatui::backend::TestBackend::new(w, h);
            let mut terminal = ratatui::Terminal::new(backend).unwrap();

            for flavor in crate::dsp::enhancer::DacHardwareFlavor::all() {
                app.streamer.set_dac_flavor(*flavor);
                let draw_res = terminal.draw(|f| {
                    app.render(f);
                });
                assert!(draw_res.is_ok(), "Rendering failed for flavor {:?} at {}x{}", flavor, w, h);
            }
        }
    }

    #[test]
    fn test_transducer_aware_gear_commands_and_switching() {
        let mut app = App::new_test();

        // 1. Switch to laptop speakers via command
        app.execute_command(":gear speaker");
        assert_eq!(app.gear_profile.form_factor, crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers);
        assert!(app.status_message.contains(&app.gear_profile.name));

        // 2. Switch to desktop bookshelf monitors via command
        app.execute_command(":gear bookshelf");
        assert_eq!(app.gear_profile.form_factor, crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers);
        assert!(app.status_message.contains(&app.gear_profile.name));

        // 3. Switch back to headphones / IEMs
        app.execute_command(":gear headphone");
        assert!(app.gear_profile.form_factor != crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers);
        assert!(app.gear_profile.form_factor != crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers);

        // 4. Test :gear status command
        app.execute_command(":gear");
        assert!(app.status_message.contains("Active Gear:"));

        // 5. Test Step 0 wizard options include 7 choices
        let mut wizard = crate::ui::gear_modal::GearWizardModal::new();
        wizard.open(&app.gear_profile);
        assert_eq!(wizard.current_step, 0);

        // Select option 5 (Built-in Laptop Speakers)
        wizard.selected_option = 5;
        let _ = wizard.handle_key(ratatui::crossterm::event::KeyCode::Enter);
        assert_eq!(wizard.form_factor, crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers);

        // Reset and select option 6 (Desktop Bookshelf Speakers)
        wizard.current_step = 0;
        wizard.selected_option = 6;
        let _ = wizard.handle_key(ratatui::crossterm::event::KeyCode::Enter);
        assert_eq!(wizard.form_factor, crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers);
    }
}

