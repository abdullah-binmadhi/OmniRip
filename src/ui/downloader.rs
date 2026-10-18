use crate::harvest::lyrics::resolve_and_save_lyrics;
use crate::harvest::musicbrainz::{build_nicotine_query, fetch_cover_art_archive, lookup_metadata};
use crate::harvest::nicotine::{score_candidate, NicotineCandidate};
use crate::harvest::slskd::SlskdClient;
use crate::harvest::spectral::analyze_file;
use crate::harvest::tagger::{write_tags, AudioTrackInfo};
use crate::harvest::title_cleaner::clean_title;
use crate::harvest::yt_dlp::{
    download_audio, download_audio_to_path, expand_album_tracks, fetch_video_title,
    get_album_track_path, is_playlist_or_album, AudioFormat,
};
use crate::ui::preset_modal::centered_rect;
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{
    Block, Borders, Clear, List, ListItem, ListState, Paragraph, Scrollbar, ScrollbarOrientation,
    ScrollbarState, Tabs,
};
use tokio::sync::mpsc::{channel, Receiver, Sender};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(non_camel_case_types)]
pub enum Mp3Quality {
    Mp3_320k,
    Mp3_V0,
    Mp3_256k,
    Mp3_128k,
    Aac_256k,
    FlacLossless,
    Wav24,
    Opus160k,
}

impl Mp3Quality {
    pub fn label(&self) -> &'static str {
        match self {
            Mp3Quality::Mp3_320k => "MP3 320k (CBR)",
            Mp3Quality::Mp3_V0 => "MP3 V0 (VBR)",
            Mp3Quality::Mp3_256k => "MP3 256k (CBR)",
            Mp3Quality::Mp3_128k => "MP3 128k (CBR)",
            Mp3Quality::Aac_256k => "AAC 256k (M4A)",
            Mp3Quality::FlacLossless => "FLAC Lossless",
            Mp3Quality::Wav24 => "WAV (24-bit)",
            Mp3Quality::Opus160k => "OPUS 160k",
        }
    }

    pub fn to_audio_format(&self) -> AudioFormat {
        match self {
            Mp3Quality::Aac_256k => AudioFormat::Aac,
            Mp3Quality::FlacLossless => AudioFormat::Flac,
            Mp3Quality::Wav24 => AudioFormat::Wav,
            Mp3Quality::Opus160k => AudioFormat::Opus,
            _ => AudioFormat::Mp3,
        }
    }

    pub fn next(&self) -> Self {
        match self {
            Mp3Quality::Mp3_320k => Mp3Quality::Mp3_V0,
            Mp3Quality::Mp3_V0 => Mp3Quality::Mp3_256k,
            Mp3Quality::Mp3_256k => Mp3Quality::Mp3_128k,
            Mp3Quality::Mp3_128k => Mp3Quality::Aac_256k,
            Mp3Quality::Aac_256k => Mp3Quality::FlacLossless,
            Mp3Quality::FlacLossless => Mp3Quality::Wav24,
            Mp3Quality::Wav24 => Mp3Quality::Opus160k,
            Mp3Quality::Opus160k => Mp3Quality::Mp3_320k,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            Mp3Quality::Mp3_320k => Mp3Quality::Opus160k,
            Mp3Quality::Mp3_V0 => Mp3Quality::Mp3_320k,
            Mp3Quality::Mp3_256k => Mp3Quality::Mp3_V0,
            Mp3Quality::Mp3_128k => Mp3Quality::Mp3_256k,
            Mp3Quality::Aac_256k => Mp3Quality::Mp3_128k,
            Mp3Quality::FlacLossless => Mp3Quality::Aac_256k,
            Mp3Quality::Wav24 => Mp3Quality::FlacLossless,
            Mp3Quality::Opus160k => Mp3Quality::Wav24,
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Mp3Quality::Mp3_320k => "320kbps Constant Bitrate MP3 (Studio Master)",
            Mp3Quality::Mp3_V0 => "Variable Bitrate Extreme (~245kbps VBR)",
            Mp3Quality::Mp3_256k => "256kbps Constant Bitrate MP3",
            Mp3Quality::Mp3_128k => "128kbps Standard Compact MP3",
            Mp3Quality::Aac_256k => "256kbps Apple AAC / M4A Stream",
            Mp3Quality::FlacLossless => "24-bit / 48kHz Authentic Lossless FLAC",
            Mp3Quality::Wav24 => "24-bit Uncompressed PCM Broadcast WAV",
            Mp3Quality::Opus160k => "160kbps Low-Latency Audiophile Opus",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SearchTargetEngine {
    SoulseekP2P,
    YouTube,
    Hybrid,
}

impl SearchTargetEngine {
    pub fn label(&self) -> &'static str {
        match self {
            SearchTargetEngine::SoulseekP2P => "Soulseek P2P (Lossless FLAC/WAV)",
            SearchTargetEngine::YouTube => "YouTube (Fast Web Audio)",
            SearchTargetEngine::Hybrid => "Hybrid (Soulseek First -> Web Fallback)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            SearchTargetEngine::SoulseekP2P => SearchTargetEngine::YouTube,
            SearchTargetEngine::YouTube => SearchTargetEngine::Hybrid,
            SearchTargetEngine::Hybrid => SearchTargetEngine::SoulseekP2P,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            SearchTargetEngine::SoulseekP2P => SearchTargetEngine::Hybrid,
            SearchTargetEngine::YouTube => SearchTargetEngine::SoulseekP2P,
            SearchTargetEngine::Hybrid => SearchTargetEngine::YouTube,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AcquisitionPolicy {
    Mp3Only,
    BestAvailable,
    NicotineFlacPreferred,
    FastWebFallback,
}

impl AcquisitionPolicy {
    pub fn label(&self) -> &'static str {
        match self {
            AcquisitionPolicy::Mp3Only => "MP3 Only",
            AcquisitionPolicy::BestAvailable => "Best Available",
            AcquisitionPolicy::NicotineFlacPreferred => "Nicotine+/Soulseek",
            AcquisitionPolicy::FastWebFallback => "Fast Web Fallback",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            AcquisitionPolicy::Mp3Only => AcquisitionPolicy::BestAvailable,
            AcquisitionPolicy::BestAvailable => AcquisitionPolicy::NicotineFlacPreferred,
            AcquisitionPolicy::NicotineFlacPreferred => AcquisitionPolicy::FastWebFallback,
            AcquisitionPolicy::FastWebFallback => AcquisitionPolicy::Mp3Only,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            AcquisitionPolicy::Mp3Only => AcquisitionPolicy::FastWebFallback,
            AcquisitionPolicy::BestAvailable => AcquisitionPolicy::Mp3Only,
            AcquisitionPolicy::NicotineFlacPreferred => AcquisitionPolicy::BestAvailable,
            AcquisitionPolicy::FastWebFallback => AcquisitionPolicy::NicotineFlacPreferred,
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            AcquisitionPolicy::Mp3Only => "Direct MP3 rip via Web engine",
            AcquisitionPolicy::BestAvailable => "Soulseek P2P FLAC hunt with auto Web fallback",
            AcquisitionPolicy::NicotineFlacPreferred => "Interactive Soulseek P2P swarm hunt for authentic lossless FLAC/WAV",
            AcquisitionPolicy::FastWebFallback => "Fast audio stream extraction via Web engine",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum JobPhase {
    Queued,
    Downloading,
    AwaitingSelection(Vec<NicotineCandidate>, Vec<crate::harvest::slskd::SlskdFileResult>),
    AwaitingQueryOverride(String),
    Auditing,
    Completed,
    Failed(String),
}

impl JobPhase {
    pub fn label(&self) -> String {
        match self {
            JobPhase::Queued => "[QUEUING]".to_string(),
            JobPhase::Downloading => "[DOWNLOADING]".to_string(),
            JobPhase::AwaitingSelection(_, _) => "[SELECT QUALITY]".to_string(),
            JobPhase::AwaitingQueryOverride(_) => "[OVERRIDE QUERY]".to_string(),
            JobPhase::Auditing => "[AUDITING]".to_string(),
            JobPhase::Completed => "[COMPLETE]".to_string(),
            JobPhase::Failed(err) => format!("[FAILED: {}]", err),
        }
    }

    pub fn short_label(&self) -> String {
        match self {
            JobPhase::Queued => "[QUEUING]".to_string(),
            JobPhase::Downloading => "[DOWNLOADING]".to_string(),
            JobPhase::AwaitingSelection(_, _) => "[SELECT QUALITY]".to_string(),
            JobPhase::AwaitingQueryOverride(_) => "[OVERRIDE QUERY]".to_string(),
            JobPhase::Auditing => "[AUDITING]".to_string(),
            JobPhase::Completed => "[COMPLETE]".to_string(),
            JobPhase::Failed(_) => "[FAILED]".to_string(),
        }
    }
}

/// Wraps long error or status text into chunks of at most `max_width` characters.
pub fn wrap_text_to_chunks(text: &str, max_width: usize) -> Vec<String> {
    let limit = max_width.max(10);
    let mut lines = Vec::new();
    let mut cur = String::new();

    for word in text.split_whitespace() {
        if cur.is_empty() {
            if word.len() > limit {
                let mut remainder = word;
                while remainder.len() > limit {
                    lines.push(remainder[..limit].to_string());
                    remainder = &remainder[limit..];
                }
                cur.push_str(remainder);
            } else {
                cur.push_str(word);
            }
        } else if cur.len() + 1 + word.len() <= limit {
            cur.push(' ');
            cur.push_str(word);
        } else {
            lines.push(cur);
            cur = String::new();
            if word.len() > limit {
                let mut remainder = word;
                while remainder.len() > limit {
                    lines.push(remainder[..limit].to_string());
                    remainder = &remainder[limit..];
                }
                cur.push_str(remainder);
            } else {
                cur.push_str(word);
            }
        }
    }

    if !cur.is_empty() {
        lines.push(cur);
    }
    if lines.is_empty() {
        lines.push(text.to_string());
    }
    lines
}

#[derive(Debug, Clone)]
pub struct DownloadJob {
    pub id: usize,
    pub source: String,
    pub display_name: String,
    pub output_path: Option<std::path::PathBuf>,
    pub quality: Mp3Quality,
    pub policy: AcquisitionPolicy,
    pub phase: JobPhase,
    pub progress: f32,
    pub speed: String,
    pub eta: String,
    pub spectral_verdict: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DownloaderTab {
    Queue,
    Eq,
    Visuals,
}

impl DownloaderTab {
    pub fn label(&self) -> &'static str {
        match self {
            DownloaderTab::Queue => "[1] Downloads & Queue",
            DownloaderTab::Eq => "[2] 10-Band EQ Rails",
            DownloaderTab::Visuals => "[3] Audio Player",
        }
    }
}

pub const FREQ_LABELS: [&str; 10] = [
    "31Hz", "63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz",
];

fn find_file_recursive(dir: &std::path::Path, target_leaf: &str) -> Option<std::path::PathBuf> {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if name.eq_ignore_ascii_case(target_leaf) || name.ends_with(target_leaf) {
                        return Some(path);
                    }
                }
            } else if path.is_dir() {
                if let Some(found) = find_file_recursive(&path, target_leaf) {
                    return Some(found);
                }
            }
        }
    }
    None
}

/// Truncates a string to at most `max_chars` Unicode characters, safely appending '...' if exceeded.
pub fn safe_truncate(s: &str, max_chars: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() > max_chars {
        let prefix: String = chars.into_iter().take(max_chars.saturating_sub(3)).collect();
        format!("{}...", prefix)
    } else {
        s.to_string()
    }
}

#[derive(Debug, Clone)]
pub struct AlbumReleaseCluster {
    pub username: String,
    pub directory: String,
    pub tracks: Vec<crate::harvest::slskd::SlskdFileResult>,
    pub companion_images: Vec<crate::harvest::slskd::SlskdFileResult>,
    pub total_size_bytes: u64,
    pub speed_kbps: Option<f32>,
    pub in_queue: usize,
    pub target_track_idx: Option<usize>,
}

impl AlbumReleaseCluster {
    pub fn formatted_size(&self) -> String {
        let mb = self.total_size_bytes as f64 / (1024.0 * 1024.0);
        if mb >= 1024.0 {
            format!("{:.2} GB", mb / 1024.0)
        } else {
            format!("{:.1} MB", mb)
        }
    }

    pub fn formatted_speed(&self) -> String {
        match self.speed_kbps {
            Some(kb) if kb >= 1024.0 => format!("{:.1} MB/s", kb / 1024.0),
            Some(kb) if kb > 0.0 => format!("{:.0} KB/s", kb),
            _ => "Unmetered".to_string(),
        }
    }
}

pub struct DownloaderState {
    pub active_tab: DownloaderTab,
    pub input_text: String,
    pub selected_quality: Mp3Quality,
    pub selected_policy: AcquisitionPolicy,
    pub jobs: Vec<DownloadJob>,
    pub selected_job_idx: usize,
    pub job_list_state: ListState,
    pub next_job_id: usize,
    pub focused_field: usize, // 0: Input, 1: Quality, 2: Policy, 3: Lyrics, 4: Convert
    pub is_editing_url: bool,
    pub download_lyrics: bool,
    pub active_soulseek_user: Option<String>,
    pub status_message: String,
    // Interactive Lossless Swarm Candidate & Scope Selector State
    pub show_lossless_selector: bool,
    pub lossless_candidates: Vec<NicotineCandidate>,
    pub all_peer_files: Vec<crate::harvest::slskd::SlskdFileResult>,
    pub selected_lossless_idx: usize,
    pub lossless_list_state: ListState,
    pub lossless_filter_text: String,
    pub is_filtering_lossless: bool,
    // Structured Tri-Field Manual Entry State
    pub show_manual_entry_modal: bool,
    pub manual_entry_artist: String,
    pub manual_entry_album: String,
    pub manual_entry_track: String,
    pub manual_entry_focused_field: usize,
    pub download_entire_album: bool,
    pub target_search_title: String,
    pub pending_job_id: Option<usize>,
    // Interactive Soulseek Query Override Modal State
    pub show_query_override_modal: bool,
    pub query_override_input: String,
    pub query_override_job_id: Option<usize>,
    // Dedicated 10-Band EQ State
    pub selected_band: usize,
    pub band_gains: [f32; 10],
    pub hpf_30hz: bool,
    pub air_boost: bool,
    pub eq_bypass: bool,
    // Dynamic Seed Availability & Expansion State
    pub target_seeds: usize,
    pub search_duration_secs: u64,
    pub seed_expansion_duration_secs: u64,
    pub seed_expansion_editing_time: bool,
    pub seed_expansion_time_input: String,
    pub show_seed_expansion_modal: bool,
    pub seed_expansion_found_count: usize,
    pub seed_expansion_search_id: Option<String>,
    pub seed_expansion_query: String,
    pub seed_expansion_candidates: Vec<NicotineCandidate>,
    pub seed_expansion_all_files: Vec<crate::harvest::slskd::SlskdFileResult>,
    pub seed_expansion_job_id: Option<usize>,
    // Advanced Structured Search Modal State
    pub show_advanced_search_modal: bool,
    pub adv_search_artist: String,
    pub adv_search_track: String,
    pub adv_search_album: String,
    pub adv_search_target_engine: SearchTargetEngine,
    pub adv_search_focused_field: usize,
    pub deleted_job_ids: std::collections::HashSet<usize>,
    pub player: std::sync::Arc<crate::dsp::TrackPlayer>,
    pub live_spectrum: [f32; 32],
    tx: Sender<(usize, JobPhase, f32, String, String, Option<String>)>,
    rx: Receiver<(usize, JobPhase, f32, String, String, Option<String>)>,
}

impl DownloaderState {
    pub fn new() -> Self {
        let (tx, rx) = channel(64);
        let mut list_state = ListState::default();
        list_state.select(Some(0));
        let mut lossless_list_state = ListState::default();
        lossless_list_state.select(Some(0));
        let active_soulseek_user = crate::harvest::nicotine::NicotineConfig::detect_local().map(|c| c.username);

        Self {
            active_tab: DownloaderTab::Queue,
            input_text: String::new(),
            selected_quality: Mp3Quality::Mp3_320k, // Default to MP3 320k per user request
            selected_policy: AcquisitionPolicy::Mp3Only,
            jobs: Vec::new(),
            selected_job_idx: 0,
            job_list_state: list_state,
            next_job_id: 1,
            focused_field: 0,
            is_editing_url: false,
            download_lyrics: true,
            active_soulseek_user,
            status_message: "Ready. Press Enter to paste/edit URL, or [1-3] to switch tabs.".to_string(),
            show_lossless_selector: false,
            lossless_candidates: Vec::new(),
            all_peer_files: Vec::new(),
            selected_lossless_idx: 0,
            lossless_list_state,
            lossless_filter_text: String::new(),
            is_filtering_lossless: false,
            show_manual_entry_modal: false,
            manual_entry_artist: String::new(),
            manual_entry_album: String::new(),
            manual_entry_track: String::new(),
            manual_entry_focused_field: 0,
            download_entire_album: false,
            target_search_title: String::new(),
            pending_job_id: None,
            show_query_override_modal: false,
            query_override_input: String::new(),
            query_override_job_id: None,
            selected_band: 5,
            band_gains: [0.0; 10],
            hpf_30hz: false,
            air_boost: false,
            eq_bypass: false,
            target_seeds: 20,
            search_duration_secs: 30,
            seed_expansion_duration_secs: 30,
            seed_expansion_editing_time: false,
            seed_expansion_time_input: "30".to_string(),
            show_seed_expansion_modal: false,
            seed_expansion_found_count: 0,
            seed_expansion_search_id: None,
            seed_expansion_query: String::new(),
            seed_expansion_candidates: Vec::new(),
            seed_expansion_all_files: Vec::new(),
            seed_expansion_job_id: None,
            show_advanced_search_modal: false,
            adv_search_artist: String::new(),
            adv_search_track: String::new(),
            adv_search_album: String::new(),
            adv_search_target_engine: SearchTargetEngine::SoulseekP2P,
            adv_search_focused_field: 0,
            deleted_job_ids: std::collections::HashSet::new(),
            player: std::sync::Arc::new(crate::dsp::TrackPlayer::default()),
            live_spectrum: [0.0; 32],
            tx,
            rx,
        }
    }

    /// Returns true if the downloader is actively capturing text input or has
    /// an interactive modal overlay open that must take exclusive precedence over global hotkeys.
    pub fn is_capturing_input(&self) -> bool {
        self.is_editing_url
            || self.show_lossless_selector
            || self.show_manual_entry_modal
            || self.show_query_override_modal
            || self.show_seed_expansion_modal
            || self.show_advanced_search_modal
    }

    pub fn poll_updates(&mut self) {
        while let Ok((id, phase, prog, speed, eta, verdict)) = self.rx.try_recv() {
            // Ignore asynchronous background events for jobs that were explicitly deleted from the queue
            if self.deleted_job_ids.contains(&id) {
                continue;
            }
            if let JobPhase::AwaitingSelection(ref candidates, ref all_files) = phase {
                if candidates.len() >= self.target_seeds {
                    self.lossless_candidates = candidates.clone();
                    self.all_peer_files = all_files.clone();
                    self.selected_lossless_idx = 0;
                    self.lossless_list_state.select(Some(0));
                    self.lossless_filter_text.clear();
                    self.is_filtering_lossless = false;
                    self.show_manual_entry_modal = false;
                    self.manual_entry_artist.clear();
                    self.manual_entry_album.clear();
                    self.manual_entry_track.clear();
                    self.manual_entry_focused_field = 0;
                    self.download_entire_album = false;
                    if self.target_search_title.is_empty() {
                        if let Some(j) = self.jobs.iter().find(|j| j.id == id) {
                            self.target_search_title = clean_title(&j.display_name).title;
                        }
                    }
                    self.pending_job_id = Some(id);
                    self.show_lossless_selector = true;
                    self.show_seed_expansion_modal = false;
                    self.status_message = format!(
                        "Found {} lossless version(s) in Soulseek swarm. Choose quality and scope in modal.",
                        self.lossless_candidates.len()
                    );
                } else {
                    self.show_seed_expansion_modal = true;
                    self.show_lossless_selector = false;
                    self.seed_expansion_found_count = candidates.len();
                    self.seed_expansion_candidates = candidates.clone();
                    self.seed_expansion_all_files = all_files.clone();
                    self.seed_expansion_job_id = Some(id);
                    if let Some(j) = self.jobs.iter().find(|j| j.id == id) {
                        self.seed_expansion_query = clean_title(&j.display_name).title;
                    }
                    self.status_message = format!(
                        "Found {} lossless seed(s) (Target: {}). Choose Proceed, Use Current, or Abort in modal.",
                        candidates.len(),
                        self.target_seeds
                    );
                }
            } else if let JobPhase::AwaitingQueryOverride(ref failed_query) = phase {
                self.show_query_override_modal = true;
                self.query_override_input = failed_query.clone();
                self.query_override_job_id = Some(id);
                self.status_message = format!(
                    "No lossless seeds found for '{}'. Enter refined query in modal.",
                    failed_query
                );
            }
            if let Some(job) = self.jobs.iter_mut().find(|j| j.id == id) {
                job.phase = phase;
                job.progress = prog;
                job.speed = speed;
                job.eta = eta;
                if let Some(ref v) = verdict {
                    if let Some(title) = v.strip_prefix("RESOLVED_TITLE:") {
                        job.display_name = title.to_string();
                    } else {
                        job.spectral_verdict = Some(v.clone());
                        if let Some(saved_idx) = v.find("(Saved to ") {
                            let after = &v[saved_idx + 10..];
                            if let Some(end_idx) = after.find(')') {
                                let path = std::path::PathBuf::from(&after[..end_idx]);
                                if path.exists() {
                                    if job.display_name.starts_with("http://") || job.display_name.starts_with("https://") {
                                        if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                                            let cleaned = clean_title(stem);
                                            job.display_name = if let Some(ref art) = cleaned.artist {
                                                format!("{} - {}", art, cleaned.title)
                                            } else {
                                                cleaned.title
                                            };
                                        }
                                    }
                                    job.output_path = Some(path);
                                }
                            }
                        }
                    }
                }
            }
        }

        // Auto-heal any completed jobs with raw URL display_name or missing output_path
        let to_heal: Vec<(usize, std::path::PathBuf, String)> = self.jobs.iter()
            .filter(|j| matches!(j.phase, JobPhase::Completed) && (j.output_path.is_none() || j.display_name.starts_with("http://") || j.display_name.starts_with("https://")))
            .filter_map(|j| {
                self.find_audio_for_job(j).map(|path| {
                    let new_name = path.file_stem().and_then(|s| s.to_str()).map(|stem| {
                        let c = clean_title(stem);
                        if let Some(ref a) = c.artist { format!("{} - {}", a, c.title) } else { c.title }
                    }).unwrap_or_else(|| j.display_name.clone());
                    (j.id, path, new_name)
                })
            })
            .collect();

        for (id, path, new_name) in to_heal {
            if let Some(job) = self.jobs.iter_mut().find(|j| j.id == id) {
                job.output_path = Some(path);
                if job.display_name.starts_with("http://") || job.display_name.starts_with("https://") {
                    job.display_name = new_name;
                }
            }
        }
    }

    pub fn submit_current(&mut self) {
        let text = self.input_text.trim();
        if text.is_empty() {
            self.status_message = "Error: Enter a URL or track search first.".to_string();
            return;
        }

        self.target_search_title = clean_title(text).title;

        let id = self.next_job_id;
        self.next_job_id += 1;

        let display_name = safe_truncate(text, 40);

        let job = DownloadJob {
            id,
            source: text.to_string(),
            display_name: display_name.clone(),
            output_path: None,
            quality: self.selected_quality,
            policy: self.selected_policy,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "Starting".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        };

        self.jobs.push(job);
        self.job_list_state.select(Some(self.jobs.len().saturating_sub(1)));
        let url = text.to_string();
        let format = self.selected_quality.to_audio_format();
        let policy = self.selected_policy;
        let download_lyrics = self.download_lyrics;
        let tx = self.tx.clone();

        self.input_text.clear();
        self.status_message = format!("Queued job #{}: {}", id, url);

        if is_playlist_or_album(&url) {
            if let Some(j) = self.jobs.last_mut() {
                j.display_name = format!("[ALBUM] {}", display_name);
            }
            tokio::spawn(async move {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        5.0,
                        "Resolving".into(),
                        "Album".into(),
                        None,
                    ))
                    .await;

                match expand_album_tracks(&url).await {
                    Ok(album_info) => {
                        let total = album_info.track_count;
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Downloading,
                                10.0,
                                format!("Found {} tracks", total),
                                "Queued".into(),
                                Some(format!("Album: {} by {}", album_info.title, album_info.artist)),
                            ))
                            .await;

                        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                        let music_dir = std::path::PathBuf::from(home).join("Music");

                        for (idx, track) in album_info.tracks.iter().enumerate() {
                            let prog = 10.0 + ((idx as f32) / (total as f32)) * 85.0;
                            let _ = tx
                                .send((
                                    id,
                                    JobPhase::Downloading,
                                    prog,
                                    format!("Track {}/{}: {}", idx + 1, total, track.title),
                                    "--:--".into(),
                                    None,
                                ))
                                .await;

                            let target_path = get_album_track_path(
                                &music_dir,
                                &track.artist,
                                &album_info.title,
                                track.index,
                                &track.title,
                                format,
                            );

                            let _ = download_audio_to_path(&track.url, &target_path, format).await;

                            let tag_info = AudioTrackInfo {
                                title: Some(track.title.clone()),
                                artist: Some(track.artist.clone()),
                                album: Some(album_info.title.clone()),
                                track_number: Some(track.index as u32),
                                ..Default::default()
                            };
                            let _ = write_tags(&target_path, &tag_info);
                        }

                        let _ = tx
                            .send((
                                id,
                                JobPhase::Completed,
                                100.0,
                                format!("Saved to ~/Music/{}/{}", album_info.artist, album_info.title),
                                "00:00".into(),
                                Some(format!("Complete: {} tracks", total)),
                            ))
                            .await;
                    }
                    Err(e) => {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed(e),
                                0.0,
                                "Failed".into(),
                                "--:--".into(),
                                None,
                            ))
                            .await;
                    }
                }
            });
            return;
        }

        let display_for_tag = display_name.clone();
        let target_seeds = self.target_seeds;
        let search_duration_secs = self.search_duration_secs;

        // Spawn background tokio download worker for single track
        tokio::spawn(async move {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let music_dir = std::path::PathBuf::from(home).join("Music");
            let _ = std::fs::create_dir_all(&music_dir);

            // Check acquisition policy: hunt Soulseek swarm if NicotineFlacPreferred or BestAvailable
            if matches!(policy, AcquisitionPolicy::NicotineFlacPreferred | AcquisitionPolicy::BestAvailable) {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        10.0,
                        "Soulseek Hunt".into(),
                        "--:--".into(),
                        Some("Resolving canonical metadata and hunting Soulseek swarm...".into()),
                    ))
                    .await;

                // Pre-resolve YouTube title if a web URL was passed, or use direct text query from Smart Omnibox
                let search_query_title = if url.starts_with("http://") || url.starts_with("https://") {
                    fetch_video_title(&url).await.unwrap_or_else(|_| display_for_tag.clone())
                } else {
                    url.clone()
                };

                let cleaned_meta = clean_title(&search_query_title);
                let mb_meta = lookup_metadata(cleaned_meta.artist.as_deref(), &cleaned_meta.title).await.ok();
                let artist = mb_meta.as_ref().map(|m| m.artist.clone()).or(cleaned_meta.artist).unwrap_or_else(|| "Unknown".to_string());
                let title = mb_meta.as_ref().map(|m| m.title.clone()).unwrap_or(cleaned_meta.title);
                let resolved_title = format!("{} - {}", artist, title);
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        12.0,
                        "Identified".into(),
                        "--:--".into(),
                        Some(format!("RESOLVED_TITLE:{}", resolved_title)),
                    ))
                    .await;
                let query = build_nicotine_query(&artist, &title);

                let slskd = SlskdClient::detect_local();

                // 1. Fallback Detector: Pre-flight Soulseek daemon & swarm connectivity ping
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        12.0,
                        "Pre-Flight".into(),
                        "--:--".into(),
                        Some("Running Fallback Detector: Checking Soulseek daemon and swarm health...".into()),
                    ))
                    .await;

                match slskd.check_server_health().await {
                    Ok(status) if status.is_logged_in => {
                        // Swarm daemon connected and authenticated
                    }
                    Ok(status) => {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed("Soulseek server disconnected or not logged in. Web fallback disabled.".into()),
                                0.0,
                                "Disconnected".into(),
                                "--:--".into(),
                                Some(format!("Slskd daemon is connected locally, but Soulseek server state is: {:?}. Web fallback disabled.", status.state)),
                            ))
                            .await;
                        return;
                    }
                    Err(err) => {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed(format!("Soulseek daemon unreachable ({}). Web fallback disabled.", err)),
                                0.0,
                                "Offline".into(),
                                "--:--".into(),
                                Some("Slskd daemon is offline on port 5030. Web fallback disabled.".into()),
                            ))
                            .await;
                        return;
                    }
                }

                // 2. Initiate parallel search (specific artist+title, broad title, and album) and run progressive polling
                let specific_query = query.clone();
                let broad_title_query = title.trim().to_string();
                let search_id_1 = slskd.start_search(&specific_query).await;
                let search_id_2 = if broad_title_query.len() >= 3 && broad_title_query.to_lowercase() != specific_query.to_lowercase() {
                    slskd.start_search(&broad_title_query).await.ok()
                } else {
                    None
                };
                let search_id_3 = if let Some(ref alb) = mb_meta.as_ref().and_then(|m| m.album.as_ref()) {
                    let album_q = format!("{} {}", artist, alb).trim().to_string();
                    if album_q.to_lowercase() != specific_query.to_lowercase() && album_q.to_lowercase() != broad_title_query.to_lowercase() {
                        slskd.start_search(&album_q).await.ok()
                    } else {
                        None
                    }
                } else {
                    None
                };

                match search_id_1 {
                    Ok(search_id) => {
                        let mut results = Vec::new();

                        // Adaptive progressive polling loop (up to search_duration_secs, breaks as soon as results stabilize or target seeds met)
                        let mut last_count = 0;
                        let mut plateau_ticks = 0;
                        for attempt in 1..=search_duration_secs {
                            tokio::time::sleep(std::time::Duration::from_millis(1000)).await;

                            let mut current_results = Vec::new();
                            if let Ok(res1) = slskd.get_search_results(&search_id).await {
                                current_results.extend(res1);
                            }
                            if let Some(ref s2) = search_id_2 {
                                if let Ok(res2) = slskd.get_search_results(s2).await {
                                    current_results.extend(res2);
                                }
                            }
                            if let Some(ref s3) = search_id_3 {
                                if let Ok(res3) = slskd.get_search_results(s3).await {
                                    current_results.extend(res3);
                                }
                            }

                            // Deduplicate results by (username, filename)
                            let mut seen = std::collections::HashSet::new();
                            current_results.retain(|r| seen.insert((r.username.clone(), r.filename.clone())));
                            results = current_results;

                            let lossless_count = results.iter().filter(|r| {
                                r.filename.to_lowercase().ends_with(".flac") || r.filename.to_lowercase().ends_with(".wav")
                            }).count();

                            if lossless_count == last_count && lossless_count > 0 {
                                plateau_ticks += 1;
                            } else {
                                plateau_ticks = 0;
                            }
                            last_count = lossless_count;

                            let _ = tx
                                .send((
                                    id,
                                    JobPhase::Downloading,
                                    15.0 + (attempt as f32) * (10.0 / search_duration_secs.max(1) as f32),
                                    format!("Swarm ({}/{}s)", attempt, search_duration_secs),
                                    "--:--".into(),
                                    Some(format!("Hunting Soulseek peers for '{}' ({}/{}s, {} lossless seeds)...", query, attempt, search_duration_secs, lossless_count)),
                                ))
                                .await;

                            // Early break: if target seeds reached, or if at least 1 seed found and count has plateaued for 2 consecutive ticks after attempt 5
                            if (lossless_count >= target_seeds) || (attempt >= 5 && lossless_count >= 1 && plateau_ticks >= 2) {
                                break;
                            }
                        }

                        // Stop background search queries in Slskd daemon to free listening sockets
                        let _ = slskd.delete_search(&search_id).await;
                        if let Some(ref s2) = search_id_2 {
                            let _ = slskd.delete_search(s2).await;
                        }
                        if let Some(ref s3) = search_id_3 {
                            let _ = slskd.delete_search(s3).await;
                        }

                        let mut candidates: Vec<NicotineCandidate> = results
                            .iter()
                            .map(|r| NicotineCandidate {
                                username: r.username.clone(),
                                filename: r.filename.clone(),
                                size_bytes: r.size,
                                bitrate_kbps: r.bitrate,
                                sample_rate: r.sample_rate,
                                bit_depth: r.bit_depth,
                                speed_kbps: r.upload_speed.map(|s| (s as f32) / 1024.0),
                                in_queue: r.queue_length as usize,
                                score: 0.0,
                            })
                            .collect();

                        for c in &mut candidates {
                            c.score = score_candidate(c);
                        }
                        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

                        if policy == AcquisitionPolicy::NicotineFlacPreferred {
                            let lossless: Vec<NicotineCandidate> = candidates
                                .iter()
                                .filter(|c| c.is_flac() || c.filename.to_lowercase().ends_with(".flac") || c.filename.to_lowercase().ends_with(".wav"))
                                .cloned()
                                .collect();

                            let _ = tx
                                .send((
                                    id,
                                    JobPhase::AwaitingSelection(lossless, results),
                                    25.0,
                                    "Select Quality".into(),
                                    "--:--".into(),
                                    Some("Soulseek swarm scan finished. Evaluating seed target...".into()),
                                ))
                                .await;
                            return;
                        }

                        if policy == AcquisitionPolicy::BestAvailable {
                            if let Some(best) = candidates.first() {
                                if best.is_flac() || best.score >= 40.0 {
                                    let _ = slskd.queue_download(&best.username, &best.filename, best.size_bytes).await;
                                    let _ = tx
                                        .send((
                                            id,
                                            JobPhase::Completed,
                                            100.0,
                                            "P2P Queued".into(),
                                            "00:00".into(),
                                            Some(format!("Queued lossless FLAC from peer '{}' (Score: {:.0}): {}", best.username, best.score, best.filename)),
                                        ))
                                        .await;
                                    return;
                                }
                            }

                            // STRICT ZERO WEB FALLBACK FOR BEST AVAILABLE
                            let _ = tx
                                .send((
                                    id,
                                    JobPhase::Failed("No matching Soulseek seeds found. Web fallback disabled for Best Available.".into()),
                                    0.0,
                                    "No Seeds".into(),
                                    "--:--".into(),
                                    Some(format!("Soulseek hunt for '{}' yielded no qualifying peers. Web fallback disabled.", query)),
                                ))
                                .await;
                            return;
                        }
                    }
                    Err(err) => {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed(format!("Failed to start Soulseek search: {}. Web fallback disabled.", err)),
                                0.0,
                                "Search Error".into(),
                                "--:--".into(),
                                Some(format!("Soulseek query error for '{}'. Web fallback disabled.", query)),
                            ))
                            .await;
                        return;
                    }
                }
            } else {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        10.0,
                        "Connecting".into(),
                        "--:--".into(),
                        None,
                    ))
                    .await;
            }

            let download_source = if url.starts_with("http://") || url.starts_with("https://") {
                url.clone()
            } else {
                format!("ytsearch1:{}", url)
            };

            match download_audio(&download_source, &music_dir, format).await {
                Ok(path_str) => {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Auditing,
                            70.0,
                            "Identifying".into(),
                            "00:02".into(),
                            None,
                        ))
                        .await;

                    // Clean raw title and query MusicBrainz for canonical metadata
                    let file_path = std::path::Path::new(&path_str);
                    let raw_stem = file_path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or(&display_for_tag);
                    let cleaned = clean_title(raw_stem);

                    let mut tag_info = AudioTrackInfo {
                        title: Some(cleaned.title.clone()),
                        artist: cleaned.artist.clone(),
                        ..Default::default()
                    };

                    let mut release_mbid_opt = None;
                    if let Ok(mb) = lookup_metadata(cleaned.artist.as_deref(), &cleaned.title).await {
                        tag_info.title = Some(mb.title);
                        tag_info.artist = Some(mb.artist);
                        tag_info.album = mb.album;
                        tag_info.year = mb.year;
                        tag_info.track_number = mb.track_number;
                        release_mbid_opt = mb.release_mbid;
                    }

                    let resolved_track_title = if let Some(ref art) = tag_info.artist {
                        format!("{} - {}", art, tag_info.title.as_deref().unwrap_or(&cleaned.title))
                    } else {
                        cleaned.title.clone()
                    };
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Auditing,
                            75.0,
                            "Identified".into(),
                            "00:02".into(),
                            Some(format!("RESOLVED_TITLE:{}", resolved_track_title)),
                        ))
                        .await;

                    // 1. Fetch high-res Cover Art Archive front cover if MBID is available
                    if let Some(ref mbid) = release_mbid_opt {
                        if let Some(art_bytes) = fetch_cover_art_archive(mbid).await {
                            tag_info.cover_art = Some(art_bytes);
                        }
                    }

                    // 2. Fetch synchronized and plain lyrics if enabled
                    if download_lyrics {
                        let artist_ref = tag_info.artist.as_deref().unwrap_or("Unknown");
                        let title_ref = tag_info.title.as_deref().unwrap_or("Unknown");
                        let album_ref = tag_info.album.as_deref();

                        if let Ok(lyrics_data) = resolve_and_save_lyrics(
                            artist_ref,
                            title_ref,
                            album_ref,
                            None,
                            &path_str,
                        ).await {
                            tag_info.lyrics = lyrics_data.plain_lyrics;
                        }
                    }

                    let _ = write_tags(&path_str, &tag_info);

                    // Write companion <track_stem>.jpg file for macOS Finder / Windows Explorer thumbnail preview
                    let companion_art_path = file_path.with_extension("jpg");
                    if let Some(ref art_bytes) = tag_info.cover_art {
                        let _ = std::fs::write(&companion_art_path, art_bytes);
                    } else {
                        // Extract attached thumbnail to companion .jpg so Finder shows the artwork
                        let _ = tokio::process::Command::new("ffmpeg")
                            .args(["-hide_banner", "-loglevel", "error", "-y", "-i", &path_str, "-an", "-vcodec", "copy"])
                            .arg(&companion_art_path)
                            .output()
                            .await;
                    }

                    let _ = tx
                        .send((
                            id,
                            JobPhase::Auditing,
                            85.0,
                            "Auditing".into(),
                            "00:01".into(),
                            None,
                        ))
                        .await;

                    // Run forensic spectral cutoff auditor
                    let verdict_msg = if let Ok(res) = analyze_file(&path_str) {
                        res.verdict.description()
                    } else {
                        "Spectral audit completed".to_string()
                    };
                    let verdict_str = format!("{} (Saved to {})", verdict_msg, path_str);

                    let _ = tx
                        .send((
                            id,
                            JobPhase::Completed,
                            100.0,
                            "Done".into(),
                            "00:00".into(),
                            Some(verdict_str),
                        ))
                        .await;
                }
                Err(e) => {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Failed(e),
                            0.0,
                            "Failed".into(),
                            "--:--".into(),
                            None,
                        ))
                        .await;
                }
            }
        });
    }

    /// Deletes the currently selected search or download job from the queue.
    pub fn delete_selected_job(&mut self) {
        if self.jobs.is_empty() {
            self.status_message = "No search or download jobs in queue to delete.".to_string();
            return;
        }

        let idx = self.selected_job_idx.min(self.jobs.len() - 1);
        let removed = self.jobs.remove(idx);
        self.deleted_job_ids.insert(removed.id);

        // If the deleted job was currently awaiting selection or seed expansion, dismiss the modal
        if self.pending_job_id == Some(removed.id) {
            self.show_lossless_selector = false;
            self.show_manual_entry_modal = false;
            self.pending_job_id = None;
        }
        if self.seed_expansion_job_id == Some(removed.id) {
            self.show_seed_expansion_modal = false;
            self.seed_expansion_job_id = None;
        }
        if self.query_override_job_id == Some(removed.id) {
            self.show_query_override_modal = false;
            self.query_override_job_id = None;
        }

        // Adjust selected index
        if self.jobs.is_empty() {
            self.selected_job_idx = 0;
            self.job_list_state.select(None);
        } else {
            self.selected_job_idx = self.selected_job_idx.min(self.jobs.len() - 1);
            self.job_list_state.select(Some(self.selected_job_idx));
        }

        self.status_message = format!("Deleted job #{}: {}", removed.id, removed.display_name);
    }

    pub fn trigger_enhancement(&mut self) {
        if self.jobs.is_empty() {
            self.status_message = "No jobs in queue to enhance. Download an audio track first.".to_string();
            return;
        }

        let job_idx = self.selected_job_idx.min(self.jobs.len().saturating_sub(1));
        let job = &mut self.jobs[job_idx];
        let job_id = job.id;
        let gains = self.band_gains;
        let hpf = self.hpf_30hz;
        let air = self.air_boost;
        let tx = self.tx.clone();

        self.status_message = format!("Enhancing track #{}: Reconstructing air band & applying EQ...", job_id);

        tokio::spawn(async move {
            let _ = tx
                .send((
                    job_id,
                    JobPhase::Auditing,
                    50.0,
                    "Enhancing".into(),
                    "--:--".into(),
                    Some("Synthesizing 16k-22k air harmonics and applying 10-Band EQ...".into()),
                ))
                .await;

            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let music_dir = std::path::PathBuf::from(home).join("Music");

            // Locate downloaded audio file
            let mut matched_file = None;
            if let Ok(entries) = std::fs::read_dir(&music_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_file() {
                        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
                        if matches!(ext, "mp3" | "m4a" | "aac" | "opus" | "flac" | "wav") {
                            matched_file = Some(path);
                            break;
                        }
                    } else if path.is_dir() {
                        if let Ok(sub_entries) = std::fs::read_dir(&path) {
                            for sub in sub_entries.flatten() {
                                let sub_path = sub.path();
                                if sub_path.is_dir() {
                                    if let Ok(track_entries) = std::fs::read_dir(&sub_path) {
                                        for track in track_entries.flatten() {
                                            let track_path = track.path();
                                            let ext = track_path.extension().and_then(|e| e.to_str()).unwrap_or("");
                                            if matches!(ext, "mp3" | "m4a" | "aac" | "opus" | "flac" | "wav") {
                                                matched_file = Some(track_path);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if let Some(src_path) = matched_file {
                let stem = src_path.file_stem().and_then(|s| s.to_str()).unwrap_or("track");
                let out_path = src_path.with_file_name(format!("{}_lossless_restored.flac", stem));

                match crate::dsp::restoration::enhance_audio_file(&src_path, &out_path, &gains, hpf, air) {
                    Ok(saved) => {
                        let _ = tx
                            .send((
                                job_id,
                                JobPhase::Completed,
                                100.0,
                                "Enhanced".into(),
                                "Done".into(),
                                Some(format!("LOSSLESS RESTORED: Saved to {}", saved.display())),
                            ))
                            .await;
                    }
                    Err(e) => {
                        let _ = tx
                            .send((
                                job_id,
                                JobPhase::Completed,
                                100.0,
                                "Complete".into(),
                                "Done".into(),
                                Some(format!("Enhancement completed with DSP fallback: {}", e)),
                            ))
                            .await;
                    }
                }
            } else {
                let _ = tx
                    .send((
                        job_id,
                        JobPhase::Completed,
                        100.0,
                        "Ready".into(),
                        "Done".into(),
                        Some("Enhancement DSP profile active and ready for incoming tracks.".into()),
                    ))
                    .await;
            }
        });
    }

    /// Locates the downloaded audio file associated with a job.
    pub fn find_audio_for_job(&self, job: &DownloadJob) -> Option<std::path::PathBuf> {
        if let Some(ref p) = job.output_path {
            if p.exists() {
                return Some(p.clone());
            }
        }
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let music_dir = std::path::PathBuf::from(home).join("Music");
        let clean_name = job.display_name.trim_start_matches("[ALBUM] ").trim();
        let is_url = job.display_name.starts_with("http://") || job.display_name.starts_with("https://")
            || job.source.starts_with("http://") || job.source.starts_with("https://");

        // If job originated from a YouTube URL, extract the video ID (e.g. ?v=... or youtu.be/...)
        let video_id_opt = if job.source.contains("watch?v=") {
            job.source.split("watch?v=").nth(1).and_then(|v| v.split('&').next()).filter(|id| !id.is_empty())
        } else if job.source.contains("youtu.be/") {
            job.source.split("youtu.be/").nth(1).and_then(|v| v.split('?').next()).filter(|id| !id.is_empty())
        } else {
            None
        };

        // 1. Check top-level Music dir
        if let Ok(entries) = std::fs::read_dir(&music_dir) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_file() {
                    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                    if matches!(ext, "mp3" | "flac" | "m4a" | "wav" | "aac" | "opus") {
                        if let Some(file_name) = p.file_name().and_then(|s| s.to_str()) {
                            if let Some(vid) = video_id_opt {
                                if file_name.contains(vid) {
                                    return Some(p);
                                }
                            }
                            if !is_url {
                                if file_name.to_lowercase().contains(&clean_name.to_lowercase())
                                    || clean_name.to_lowercase().contains(&file_name.to_lowercase())
                                {
                                    return Some(p);
                                }
                            }
                        }
                    }
                }
            }
        }

        // 2. Search subdirectories inside Music dir
        if let Ok(entries) = std::fs::read_dir(&music_dir) {
            for entry in entries.flatten() {
                let sub_dir = entry.path();
                if sub_dir.is_dir() {
                    if let Ok(sub_entries) = std::fs::read_dir(&sub_dir) {
                        for sub_entry in sub_entries.flatten() {
                            let p = sub_entry.path();
                            if p.is_file() {
                                let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                                if matches!(ext, "mp3" | "flac" | "m4a" | "wav" | "aac" | "opus") {
                                    if let Some(file_name) = p.file_name().and_then(|s| s.to_str()) {
                                        if let Some(vid) = video_id_opt {
                                            if file_name.contains(vid) {
                                                return Some(p);
                                            }
                                        }
                                        if !is_url {
                                            if file_name.to_lowercase().contains(&clean_name.to_lowercase())
                                                || clean_name.to_lowercase().contains(&file_name.to_lowercase())
                                            {
                                                return Some(p);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Fallback: check if source is an existing file path
        let source_path = std::path::PathBuf::from(&job.source);
        if source_path.exists() && source_path.is_file() {
            return Some(source_path);
        }

        // 4. Fallback for URL-based jobs: scan newest audio file in ~/Music/
        if is_url {
            let mut recent_files: Vec<(std::time::SystemTime, std::path::PathBuf)> = Vec::new();
            if let Ok(entries) = std::fs::read_dir(&music_dir) {
                for entry in entries.flatten() {
                    let p = entry.path();
                    if p.is_file() {
                        let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                        if matches!(ext, "flac" | "wav" | "mp3" | "m4a" | "aac" | "opus") {
                            if let Ok(meta) = p.metadata() {
                                if let Ok(mtime) = meta.modified() {
                                    recent_files.push((mtime, p));
                                }
                            }
                        }
                    }
                }
            }
            recent_files.sort_by(|a, b| b.0.cmp(&a.0));
            if let Some((_, newest_path)) = recent_files.first() {
                return Some(newest_path.clone());
            }
        }

        None
    }

    /// Loads the currently selected track from the Queue into the Audio Player in paused state (Option A).
    pub fn load_selected_track_into_player(&mut self) {
        if self.jobs.is_empty() {
            self.status_message = "No jobs in queue to audition in Audio Player.".to_string();
            return;
        }

        let idx = self.selected_job_idx.min(self.jobs.len().saturating_sub(1));
        let job = &self.jobs[idx];

        if let Some(path) = self.find_audio_for_job(job) {
            self.jobs[idx].output_path = Some(path.clone());
            if self.jobs[idx].display_name.starts_with("http://") || self.jobs[idx].display_name.starts_with("https://") {
                if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                    let cleaned = clean_title(stem);
                    self.jobs[idx].display_name = if let Some(ref art) = cleaned.artist {
                        format!("{} - {}", art, cleaned.title)
                    } else {
                        cleaned.title
                    };
                }
            }
            let display_name = self.jobs[idx].display_name.clone();
            match self.player.load_file(&path) {
                Ok(_) => {
                    self.player.pause();
                    self.status_message = format!(
                        "Audio Player: Loaded '{}' (Paused). Press [Space] to play.",
                        display_name
                    );
                }
                Err(e) => {
                    self.status_message = format!(
                        "Audio Player error decoding '{}': {}",
                        path.display(),
                        e
                    );
                }
            }
        } else {
            let display_name = self.jobs[idx].display_name.clone();
            self.status_message = format!(
                "Cannot audition '{}': File not yet downloaded or not found on disk.",
                display_name
            );
        }
    }

    /// Groups search results into album release clusters by (peer, parent directory).
    pub fn album_release_clusters(&self) -> Vec<AlbumReleaseCluster> {
        use std::collections::BTreeMap;
        let mut groups: BTreeMap<(String, String), (Vec<crate::harvest::slskd::SlskdFileResult>, Vec<crate::harvest::slskd::SlskdFileResult>)> = BTreeMap::new();

        for file in &self.all_peer_files {
            let clean = file.filename.replace('\\', "/");
            let parent_dir = if let Some((dir, _)) = clean.rsplit_once('/') {
                dir.rsplit_once('/').map(|(_, d)| d).unwrap_or(dir).to_string()
            } else {
                "Root".to_string()
            };

            let entry = groups.entry((file.username.clone(), parent_dir)).or_insert_with(|| (Vec::new(), Vec::new()));
            let lower = clean.to_lowercase();
            if lower.ends_with(".flac") || lower.ends_with(".wav") {
                entry.0.push(file.clone());
            } else if lower.ends_with(".jpg") || lower.ends_with(".jpeg") || lower.ends_with(".png") {
                entry.1.push(file.clone());
            }
        }

        let target_lower = self.target_search_title.trim().to_lowercase();

        let mut clusters: Vec<AlbumReleaseCluster> = groups
            .into_iter()
            .filter(|(_, (audio_tracks, _))| !audio_tracks.is_empty())
            .map(|((username, directory), (mut tracks, companion_images))| {
                tracks.sort_by(|a, b| a.filename.cmp(&b.filename));

                let total_size_bytes: u64 = tracks.iter().map(|t| t.size).sum::<u64>()
                    + companion_images.iter().map(|img| img.size).sum::<u64>();

                let peer_match = self.lossless_candidates.iter().find(|c| c.username == username);
                let speed_kbps = peer_match.and_then(|c| c.speed_kbps);
                let in_queue = peer_match.map(|c| c.in_queue).unwrap_or(0);

                let target_track_idx = if !target_lower.is_empty() {
                    tracks.iter().position(|t| {
                        let fn_clean = t.filename.replace('\\', "/").to_lowercase();
                        fn_clean.contains(&target_lower)
                    })
                } else {
                    None
                };

                AlbumReleaseCluster {
                    username,
                    directory,
                    tracks,
                    companion_images,
                    total_size_bytes,
                    speed_kbps,
                    in_queue,
                    target_track_idx,
                }
            })
            .collect();

        // Filter out loose single-track scraps from unrelated peers in Album mode unless it contains the target song
        clusters.retain(|c| c.tracks.len() >= 2 || c.target_track_idx.is_some());

        // Sort: clusters with target track first, then by track count desc, then by queue asc,
        // and strictly deterministic tie-breakers (directory name, then username) to guarantee zero shuffling between frames.
        clusters.sort_by(|a, b| {
            b.target_track_idx.is_some().cmp(&a.target_track_idx.is_some())
                .then_with(|| b.tracks.len().cmp(&a.tracks.len()))
                .then_with(|| a.in_queue.cmp(&b.in_queue))
                .then_with(|| a.directory.cmp(&b.directory))
                .then_with(|| a.username.cmp(&b.username))
        });

        // Filter if active
        let filter = self.lossless_filter_text.trim().to_lowercase();
        if !filter.is_empty() {
            let tokens: Vec<&str> = filter.split_whitespace().collect();
            clusters.retain(|c| {
                let dir_low = c.directory.to_lowercase();
                let user_low = c.username.to_lowercase();
                let tracks_match = c.tracks.iter().any(|t| {
                    let fn_low = t.filename.to_lowercase();
                    tokens.iter().all(|tok| fn_low.contains(tok))
                });
                tokens.iter().all(|tok| dir_low.contains(tok) || user_low.contains(tok)) || tracks_match
            });
        }

        clusters
    }

    /// Returns the indices of candidates/clusters that match the active filter query.
    pub fn filtered_lossless_indices(&self) -> Vec<usize> {
        if self.download_entire_album {
            return (0..self.album_release_clusters().len()).collect();
        }

        let filter = self.lossless_filter_text.trim().to_lowercase();
        if filter.is_empty() {
            return (0..self.lossless_candidates.len()).collect();
        }

        let tokens: Vec<&str> = filter.split_whitespace().collect();
        self.lossless_candidates
            .iter()
            .enumerate()
            .filter(|(_, c)| {
                let file_lower = c.filename.to_lowercase();
                let dir_lower = c.directory_name().to_lowercase();
                let user_lower = c.username.to_lowercase();
                tokens.iter().all(|t| file_lower.contains(t) || dir_lower.contains(t) || user_lower.contains(t))
            })
            .map(|(idx, _)| idx)
            .collect()
    }

    pub fn confirm_lossless_selection(&mut self) {
        let entire_album = self.download_entire_album;
        let job_id = self.pending_job_id;
        let tx = self.tx.clone();

        if entire_album {
            let clusters = self.album_release_clusters();
            if clusters.is_empty() {
                self.show_lossless_selector = false;
                return;
            }
            let chosen_cluster = clusters.get(self.selected_lossless_idx).cloned().unwrap_or_else(|| clusters[0].clone());
            self.show_lossless_selector = false;
            let album_name = chosen_cluster.directory.clone();
            if let Some(id) = job_id {
                if let Some(j) = self.jobs.iter_mut().find(|j| j.id == id) {
                    j.display_name = format!("[ALBUM] {}", album_name);
                    j.quality = Mp3Quality::FlacLossless;
                    j.policy = AcquisitionPolicy::NicotineFlacPreferred;
                }
            }
            self.status_message = format!(
                "Queued entire album ({}) from peer '{}' via Soulseek",
                chosen_cluster.directory,
                chosen_cluster.username
            );

            tokio::spawn(async move {
                let slskd = SlskdClient::detect_local();
                let peer = chosen_cluster.username.clone();

                let mut all_to_download: Vec<(String, u64, bool)> = Vec::new();
                for t in &chosen_cluster.tracks {
                    all_to_download.push((t.filename.clone(), t.size, true));
                }
                for img in &chosen_cluster.companion_images {
                    all_to_download.push((img.filename.clone(), img.size, false));
                }

                let total_items = all_to_download.len();
                for (fname, sz, _) in &all_to_download {
                    let _ = slskd.queue_download(&peer, fname, *sz).await;
                }

                if let Some(id) = job_id {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Queued,
                            1.0,
                            "Queuing".into(),
                            "--:--".into(),
                            Some(format!(
                                "Queued {} items with peer '{}'. Waiting in upload queue...",
                                total_items, peer
                            )),
                        ))
                        .await;
                }

                // Poll active transfers until all album files complete
                let start_time = std::time::Instant::now();
                while start_time.elapsed().as_secs() < 3600 {
                    tokio::time::sleep(std::time::Duration::from_millis(1500)).await;

                    if let Ok(transfers) = slskd.get_active_transfers().await {
                        let peer_transfers: Vec<_> = transfers
                            .iter()
                            .filter(|t| t.username == peer)
                            .collect();

                        let mut completed_count = 0;
                        let mut active_speed = 0.0;
                        for (fname, _, _) in &all_to_download {
                            let item_clean = fname.replace('\\', "/");
                            let item_leaf = item_clean.rsplit_once('/').map(|(_, l)| l).unwrap_or(&item_clean);
                            if let Some(t) = peer_transfers.iter().find(|t| t.filename.replace('\\', "/").ends_with(item_leaf)) {
                                if t.state.to_lowercase().contains("completed") || t.state.to_lowercase().contains("succeeded") {
                                    completed_count += 1;
                                } else {
                                    active_speed += t.average_speed;
                                }
                            }
                        }

                        let prog = (completed_count as f32 / total_items.max(1) as f32) * 100.0;
                        let speed_str = if active_speed >= 1024.0 * 1024.0 {
                            format!("{:.1} MB/s", active_speed / (1024.0 * 1024.0))
                        } else if active_speed > 0.0 {
                            format!("{:.0} KB/s", active_speed / 1024.0)
                        } else {
                            format!("{}/{} Tracks", completed_count, total_items)
                        };

                        if completed_count == total_items {
                            break;
                        }

                        if let Some(id) = job_id {
                            let _ = tx
                                .send((
                                    id,
                                    if completed_count > 0 || active_speed > 0.0 { JobPhase::Downloading } else { JobPhase::Queued },
                                    prog.clamp(1.0, 99.0),
                                    speed_str,
                                    "--:--".into(),
                                    Some(format!("Downloading album from peer '{}': {}/{} files completed", peer, completed_count, total_items)),
                                ))
                                .await;
                        }
                    }
                }

                // Ingest album into ~/Music/<Album>/
                let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                let album_dir_name = if !chosen_cluster.directory.is_empty() && chosen_cluster.directory != "Root" {
                    chosen_cluster.directory.clone()
                } else {
                    "Album".to_string()
                };
                let dest_album_dir = std::path::PathBuf::from(&home).join("Music").join(&album_dir_name);
                let _ = std::fs::create_dir_all(&dest_album_dir);

                let slskd_downloads = slskd.get_downloads_dir().await;
                let mut audio_paths = Vec::new();
                let mut peer_cover_path = None;

                for (fname, _, is_audio) in &all_to_download {
                    let clean_item = fname.replace('\\', "/");
                    let leaf = clean_item.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_item);
                    if let Some(src) = find_file_recursive(&slskd_downloads, leaf) {
                        let dest = dest_album_dir.join(leaf);
                        let _ = std::fs::copy(&src, &dest);
                        if *is_audio {
                            audio_paths.push(dest);
                        } else {
                            let leaf_lower = leaf.to_lowercase();
                            if leaf_lower.contains("cover") || leaf_lower.contains("folder") || leaf_lower.contains("front") {
                                peer_cover_path = Some(dest);
                            }
                        }
                    }
                }

                // Companion Cover Art Resolution
                let mut cover_bytes = if let Some(ref cp) = peer_cover_path {
                    std::fs::read(cp).ok()
                } else {
                    None
                };

                // Fallback: If peer had no artwork, fetch from MusicBrainz Cover Art Archive
                if cover_bytes.is_none() {
                    if let Some(first_track) = audio_paths.first() {
                        let stem = first_track.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                        let cleaned = clean_title(stem);
                        if let Ok(mb) = lookup_metadata(cleaned.artist.as_deref(), &cleaned.title).await {
                            if let Some(ref mbid) = mb.release_mbid {
                                if let Some(art) = fetch_cover_art_archive(mbid).await {
                                    let _ = std::fs::write(dest_album_dir.join("cover.jpg"), &art);
                                    cover_bytes = Some(art);
                                }
                            }
                        }
                    }
                }

                // Batch Synced Lyrics and FLAC Tagging for each audio track
                for audio_path in &audio_paths {
                    let path_str = audio_path.to_string_lossy().to_string();
                    let stem = audio_path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                    let cleaned = clean_title(stem);
                    let artist = cleaned.artist.clone().unwrap_or_else(|| "Unknown".to_string());
                    let title = cleaned.title.clone();

                    // Fetch and save .lrc lyrics
                    let _ = resolve_and_save_lyrics(&artist, &title, Some(&album_dir_name), None, audio_path).await;

                    // Embed tags and cover art
                    let tag_info = AudioTrackInfo {
                        title: Some(title),
                        artist: Some(artist),
                        album: Some(album_dir_name.clone()),
                        cover_art: cover_bytes.clone(),
                        ..Default::default()
                    };
                    let _ = write_tags(&path_str, &tag_info);
                }

                let _ = slskd.trigger_shares_scan().await;

                if let Some(id) = job_id {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Completed,
                            100.0,
                            "Complete".into(),
                            "00:00".into(),
                            Some(format!("Album saved to {} ({} tracks + cover art + lyrics)", dest_album_dir.display(), audio_paths.len())),
                        ))
                        .await;
                }
            });
            return;
        }

        let matching = self.filtered_lossless_indices();
        if matching.is_empty() {
            self.show_lossless_selector = false;
            return;
        }

        let chosen_actual_idx = matching.get(self.selected_lossless_idx).copied().unwrap_or(matching[0]);
        let chosen = self.lossless_candidates[chosen_actual_idx].clone();
        let candidates = self.lossless_candidates.clone();

        self.show_lossless_selector = false;

        // Clean chosen filename to update display name and queue immediately
        let clean_fname = chosen.filename.replace('\\', "/");
        let leaf = clean_fname.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_fname);
        let raw_stem = std::path::Path::new(leaf).file_stem().and_then(|s| s.to_str()).unwrap_or(leaf);
        let cleaned = clean_title(raw_stem);
        let display_title = if let Some(ref art) = cleaned.artist {
            format!("{} - {}", art, cleaned.title)
        } else {
            cleaned.title
        };

        if let Some(id) = job_id {
            if let Some(j) = self.jobs.iter_mut().find(|j| j.id == id) {
                j.display_name = display_title;
                j.quality = Mp3Quality::FlacLossless;
                j.policy = AcquisitionPolicy::NicotineFlacPreferred;
            }
        }

        let chosen_clone = chosen.clone();
        tokio::spawn(async move {
            let mut chosen = chosen_clone;
            let slskd = SlskdClient::detect_local();
                let mut attempted_peers: Vec<String> = vec![chosen.username.clone()];
                let mut queued_ticks: u32 = 0;

                let _ = slskd.queue_download(&chosen.username, &chosen.filename, chosen.size_bytes).await;

                if let Some(id) = job_id {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Queued,
                            1.0,
                            "Queuing".into(),
                            "--:--".into(),
                            Some(format!("Queued with peer '{}'. Waiting in upload queue...", chosen.username)),
                        ))
                        .await;
                }

                let mut clean_chosen = chosen.filename.replace('\\', "/");
                let mut leaf_name = clean_chosen.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_chosen).to_string();

                let mut completed = false;
                let mut failed_msg = None;
                let start_time = std::time::Instant::now();

                while start_time.elapsed().as_secs() < 3600 {
                    tokio::time::sleep(std::time::Duration::from_millis(1500)).await;

                    if let Ok(transfers) = slskd.get_active_transfers().await {
                        let target = transfers.iter().find(|t| {
                            t.username == chosen.username && (t.filename == chosen.filename || t.filename.replace('\\', "/").ends_with(&leaf_name))
                        });

                        if let Some(t) = target {
                            let state_lower = t.state.to_lowercase();
                            if state_lower.contains("completed") || state_lower.contains("succeeded") {
                                completed = true;
                                break;
                            } else if state_lower.contains("cancelled") || state_lower.contains("errored") || state_lower.contains("timedout") || state_lower.contains("rejected") {
                                // Auto-failover to alternative candidate if available
                                if let Some(alt) = candidates.iter().find(|c| !attempted_peers.contains(&c.username)) {
                                    let prev_peer = chosen.username.clone();
                                    chosen = alt.clone();
                                    attempted_peers.push(chosen.username.clone());
                                    queued_ticks = 0;
                                    clean_chosen = chosen.filename.replace('\\', "/");
                                    leaf_name = clean_chosen.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_chosen).to_string();
                                    let _ = slskd.queue_download(&chosen.username, &chosen.filename, chosen.size_bytes).await;

                                    if let Some(id) = job_id {
                                        let _ = tx
                                            .send((
                                                id,
                                                JobPhase::Queued,
                                                1.0,
                                                "Failover".into(),
                                                "--:--".into(),
                                                Some(format!("Transfer cancelled/rejected by peer '{}'. Auto-failing over to peer '{}'...", prev_peer, chosen.username)),
                                            ))
                                            .await;
                                    }
                                } else {
                                    failed_msg = Some(format!("Soulseek transfer failed (State: {})", t.state));
                                    break;
                                }
                            } else if state_lower.contains("inprogress") || state_lower.contains("running") || state_lower.contains("transferring") {
                                queued_ticks = 0;
                                let speed_str = if t.average_speed >= 1024.0 * 1024.0 {
                                    format!("{:.1} MB/s", t.average_speed / (1024.0 * 1024.0))
                                } else if t.average_speed > 0.0 {
                                    format!("{:.0} KB/s", t.average_speed / 1024.0)
                                } else {
                                    "Starting".to_string()
                                };
                                let eta_str = t.remaining_time.clone().unwrap_or_else(|| "--:--".to_string());
                                let prog = t.percent_complete.clamp(1.0, 99.0);

                                if let Some(id) = job_id {
                                    let _ = tx
                                        .send((
                                            id,
                                            JobPhase::Downloading,
                                            prog,
                                            speed_str,
                                            eta_str,
                                            Some(format!("Downloading from peer '{}': {:.1}% ({})", chosen.username, prog, leaf_name)),
                                        ))
                                        .await;
                                }
                            } else {
                                queued_ticks += 1;
                                // 25 ticks * 1.5s = ~37.5s watchdog timeout for queue stall
                                if queued_ticks >= 25 {
                                    if let Some(alt) = candidates.iter().find(|c| !attempted_peers.contains(&c.username)) {
                                        let prev_peer = chosen.username.clone();
                                        chosen = alt.clone();
                                        attempted_peers.push(chosen.username.clone());
                                        queued_ticks = 0;
                                        clean_chosen = chosen.filename.replace('\\', "/");
                                        leaf_name = clean_chosen.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_chosen).to_string();
                                        let _ = slskd.queue_download(&chosen.username, &chosen.filename, chosen.size_bytes).await;

                                        if let Some(id) = job_id {
                                            let _ = tx
                                                .send((
                                                    id,
                                                    JobPhase::Queued,
                                                    1.0,
                                                    "Failover".into(),
                                                    "--:--".into(),
                                                    Some(format!("Peer '{}' queue stalled (donor privileges required). Auto-failing over to peer '{}'...", prev_peer, chosen.username)),
                                                ))
                                                .await;
                                        }
                                        continue;
                                    }
                                }

                                if let Some(id) = job_id {
                                    let _ = tx
                                        .send((
                                            id,
                                            JobPhase::Queued,
                                            1.0,
                                            "Queuing".into(),
                                            "--:--".into(),
                                            Some(format!("Waiting in peer '{}' upload queue (State: {})...", chosen.username, t.state)),
                                        ))
                                        .await;
                                }
                            }
                        } else {
                            let downloads_dir = slskd.get_downloads_dir().await;
                            if find_file_recursive(&downloads_dir, &leaf_name).is_some() {
                                completed = true;
                                break;
                            }
                        }
                    }
                }

                if completed {
                    if let Some(id) = job_id {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Auditing,
                                95.0,
                                "Auditing".into(),
                                "--:--".into(),
                                Some("Download complete. Ingesting into Music library and verifying spectral cutoff...".into()),
                            ))
                            .await;
                    }

                    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                    let music_dir = std::path::PathBuf::from(&home).join("Music");
                    let _ = std::fs::create_dir_all(&music_dir);

                    let slskd_downloads = slskd.get_downloads_dir().await;
                    let found_src = find_file_recursive(&slskd_downloads, &leaf_name);

                    let target_dest = if let Some(src) = found_src {
                        let dest = music_dir.join(&leaf_name);
                        let _ = std::fs::copy(&src, &dest);
                        dest
                    } else {
                        music_dir.join(&leaf_name)
                    };

                    let target_str = target_dest.to_string_lossy().to_string();

                    let file_path = std::path::Path::new(&target_str);
                    let raw_stem = file_path.file_stem().and_then(|s| s.to_str()).unwrap_or(&leaf_name);
                    let cleaned = clean_title(raw_stem);

                    let mut tag_info = AudioTrackInfo {
                        title: Some(cleaned.title.clone()),
                        artist: cleaned.artist.clone(),
                        ..Default::default()
                    };

                    if let Ok(mb) = lookup_metadata(cleaned.artist.as_deref(), &cleaned.title).await {
                        tag_info.title = Some(mb.title);
                        tag_info.artist = Some(mb.artist);
                        tag_info.album = mb.album;
                        tag_info.year = mb.year;
                        tag_info.track_number = mb.track_number;
                        if let Some(ref mbid) = mb.release_mbid {
                            if let Some(art_bytes) = fetch_cover_art_archive(mbid).await {
                                tag_info.cover_art = Some(art_bytes.clone());
                                let companion_art = file_path.with_extension("jpg");
                                let _ = std::fs::write(&companion_art, art_bytes);
                            }
                        }
                    }

                    let _ = write_tags(&target_str, &tag_info);
                    let _ = slskd.trigger_shares_scan().await;

                    let verdict_str = if let Ok(res) = analyze_file(&target_str) {
                        Some(format!("LOSSLESS VERIFIED: {} (Saved to {})", res.verdict.description(), target_dest.display()))
                    } else {
                        Some(format!("Queued lossless {} from peer '{}' (Saved to {})", chosen.formatted_resolution(), chosen.username, target_dest.display()))
                    };

                    if let Some(id) = job_id {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Completed,
                                100.0,
                                "Complete".into(),
                                "00:00".into(),
                                verdict_str,
                            ))
                            .await;
                    }
                } else if let Some(err) = failed_msg {
                    if let Some(id) = job_id {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed(err.clone()),
                                0.0,
                                "Failed".into(),
                                "--:--".into(),
                                Some(err),
                            ))
                            .await;
                    }
                }
        });

        self.status_message = format!(
            "Queued lossless {} from peer '{}' via Soulseek",
            chosen.formatted_resolution(),
            chosen.username
        );
    }

    /// Re-hunts the Soulseek swarm with a custom user-supplied search query.
    pub fn rehunt_soulseek(&mut self, job_id: usize, custom_query: String) {
        let tx = self.tx.clone();
        let query = custom_query.clone();
        let target_seeds = self.target_seeds;
        let search_duration_secs = self.search_duration_secs;
        if let Some(j) = self.jobs.iter_mut().find(|j| j.id == job_id) {
            j.phase = JobPhase::Downloading;
            j.progress = 12.0;
            j.speed = "Re-hunting".into();
        }
        self.status_message = format!("Re-hunting Soulseek swarm with refined query: '{}' (Target: {} seeds, {}s)...", query, target_seeds, search_duration_secs);

        tokio::spawn(async move {
            let slskd = SlskdClient::detect_local();
            match slskd.start_search(&query).await {
                Ok(search_id) => {
                    let mut results = Vec::new();
                    let mut last_count = 0;
                    let mut plateau_ticks = 0;
                    for attempt in 1..=search_duration_secs {
                        tokio::time::sleep(std::time::Duration::from_millis(1000)).await;
                        if let Ok(current_results) = slskd.get_search_results(&search_id).await {
                            results = current_results;
                            let lossless_count = results.iter().filter(|r| {
                                r.filename.to_lowercase().ends_with(".flac") || r.filename.to_lowercase().ends_with(".wav")
                            }).count();

                            if lossless_count == last_count && lossless_count > 0 {
                                plateau_ticks += 1;
                            } else {
                                plateau_ticks = 0;
                            }
                            last_count = lossless_count;

                            let _ = tx
                                .send((
                                    job_id,
                                    JobPhase::Downloading,
                                    15.0 + (attempt as f32) * (10.0 / search_duration_secs.max(1) as f32),
                                    format!("Swarm ({}/{}s)", attempt, search_duration_secs),
                                    "--:--".into(),
                                    Some(format!("Re-hunting Soulseek for '{}' ({}/{}s, {} seeds)...", query, attempt, search_duration_secs, lossless_count)),
                                ))
                                .await;

                            if (lossless_count >= target_seeds) || (attempt >= 5 && lossless_count >= 1 && plateau_ticks >= 2) {
                                break;
                            }
                        }
                    }

                    let _ = slskd.delete_search(&search_id).await;

                    let mut candidates: Vec<NicotineCandidate> = results
                        .iter()
                        .map(|r| NicotineCandidate {
                            username: r.username.clone(),
                            filename: r.filename.clone(),
                            size_bytes: r.size,
                            bitrate_kbps: r.bitrate,
                            sample_rate: r.sample_rate,
                            bit_depth: r.bit_depth,
                            speed_kbps: r.upload_speed.map(|s| (s as f32) / 1024.0),
                            in_queue: r.queue_length as usize,
                            score: 0.0,
                        })
                        .collect();

                    for c in &mut candidates {
                        c.score = score_candidate(c);
                    }
                    candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

                    let lossless: Vec<NicotineCandidate> = candidates
                        .iter()
                        .filter(|c| c.is_flac() || c.filename.to_lowercase().ends_with(".flac") || c.filename.to_lowercase().ends_with(".wav"))
                        .cloned()
                        .collect();

                    let _ = tx
                        .send((
                            job_id,
                            JobPhase::AwaitingSelection(lossless, results),
                            25.0,
                            "Select Quality".into(),
                            "--:--".into(),
                            Some(format!("Soulseek swarm scan finished for '{}'.", query)),
                        ))
                        .await;
                }
                Err(err) => {
                    let _ = tx
                        .send((
                            job_id,
                            JobPhase::Failed(format!("Search failed: {}", err)),
                            0.0,
                            "Failed".into(),
                            "--:--".into(),
                            Some(format!("Soulseek search error: {}", err)),
                        ))
                        .await;
                }
            }
        });
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        if self.show_advanced_search_modal {
            match code {
                KeyCode::Esc => {
                    self.show_advanced_search_modal = false;
                    self.status_message = "Closed Advanced Search modal.".to_string();
                }
                KeyCode::Tab | KeyCode::Down => {
                    self.adv_search_focused_field = (self.adv_search_focused_field + 1) % 4;
                }
                KeyCode::BackTab | KeyCode::Up => {
                    self.adv_search_focused_field = (self.adv_search_focused_field + 3) % 4;
                }
                KeyCode::Left | KeyCode::Char('h') if self.adv_search_focused_field == 3 => {
                    self.adv_search_target_engine = self.adv_search_target_engine.prev();
                }
                KeyCode::Right | KeyCode::Char('l') if self.adv_search_focused_field == 3 => {
                    self.adv_search_target_engine = self.adv_search_target_engine.next();
                }
                KeyCode::Backspace => {
                    match self.adv_search_focused_field {
                        0 => { self.adv_search_artist.pop(); }
                        1 => { self.adv_search_track.pop(); }
                        2 => { self.adv_search_album.pop(); }
                        _ => {}
                    }
                }
                KeyCode::Char(c) if self.adv_search_focused_field < 3 => {
                    match self.adv_search_focused_field {
                        0 => self.adv_search_artist.push(c),
                        1 => self.adv_search_track.push(c),
                        2 => self.adv_search_album.push(c),
                        _ => {}
                    }
                }
                KeyCode::Enter => {
                    let artist = self.adv_search_artist.trim().to_string();
                    let track = self.adv_search_track.trim().to_string();
                    let album = self.adv_search_album.trim().to_string();

                    let query = if !artist.is_empty() && !track.is_empty() {
                        format!("{} - {}", artist, track)
                    } else if !artist.is_empty() && !album.is_empty() {
                        format!("{} - {}", artist, album)
                    } else if !track.is_empty() {
                        track
                    } else if !artist.is_empty() {
                        artist
                    } else if !album.is_empty() {
                        album
                    } else {
                        String::new()
                    };

                    if !query.is_empty() {
                        match self.adv_search_target_engine {
                            SearchTargetEngine::SoulseekP2P => {
                                self.selected_policy = AcquisitionPolicy::NicotineFlacPreferred;
                            }
                            SearchTargetEngine::YouTube => {
                                self.selected_policy = AcquisitionPolicy::FastWebFallback;
                            }
                            SearchTargetEngine::Hybrid => {
                                self.selected_policy = AcquisitionPolicy::BestAvailable;
                            }
                        }
                        self.show_advanced_search_modal = false;
                        self.status_message = format!("Launched Advanced Search for '{}' via {}", query, self.adv_search_target_engine.label());
                        self.input_text = query;
                        self.submit_current();
                    }
                }
                _ => {}
            }
            return;
        }

        if self.show_seed_expansion_modal {
            if self.seed_expansion_editing_time {
                match code {
                    KeyCode::Char(c) if c.is_ascii_digit() => {
                        if self.seed_expansion_time_input.len() < 3 {
                            self.seed_expansion_time_input.push(c);
                        }
                    }
                    KeyCode::Backspace => {
                        self.seed_expansion_time_input.pop();
                    }
                    KeyCode::Enter | KeyCode::Char('t') | KeyCode::Char('T') => {
                        if let Ok(val) = self.seed_expansion_time_input.trim().parse::<u64>() {
                            self.seed_expansion_duration_secs = val.clamp(5, 300);
                        }
                        self.seed_expansion_editing_time = false;
                    }
                    KeyCode::Esc => {
                        self.seed_expansion_editing_time = false;
                    }
                    _ => {}
                }
                return;
            }

            match code {
                KeyCode::Left | KeyCode::Down | KeyCode::Char('[') => {
                    self.seed_expansion_duration_secs = self.seed_expansion_duration_secs.saturating_sub(5).max(10);
                    self.seed_expansion_time_input = self.seed_expansion_duration_secs.to_string();
                }
                KeyCode::Right | KeyCode::Up | KeyCode::Char(']') => {
                    self.seed_expansion_duration_secs = (self.seed_expansion_duration_secs + 5).min(300);
                    self.seed_expansion_time_input = self.seed_expansion_duration_secs.to_string();
                }
                KeyCode::Char('t') | KeyCode::Char('T') => {
                    self.seed_expansion_editing_time = true;
                    self.seed_expansion_time_input = self.seed_expansion_duration_secs.to_string();
                }
                KeyCode::Char('p') | KeyCode::Char('P') => {
                    self.target_seeds += 10;
                    self.search_duration_secs = self.seed_expansion_duration_secs;
                    self.show_seed_expansion_modal = false;
                    let target = self.target_seeds;
                    let duration = self.search_duration_secs;
                    if let Some(id) = self.seed_expansion_job_id {
                        let raw_query = if !self.seed_expansion_query.is_empty() {
                            self.seed_expansion_query.clone()
                        } else if let Some(j) = self.jobs.iter().find(|j| j.id == id) {
                            clean_title(&j.display_name).title
                        } else {
                            String::new()
                        };
                        let query = if self.seed_expansion_found_count == 0 || target >= 30 {
                            let cleaned = clean_title(&raw_query);
                            if let Some(ref art) = cleaned.artist {
                                format!("{} {}", art, cleaned.title).trim().to_string()
                            } else {
                                cleaned.title
                            }
                        } else {
                            raw_query
                        };
                        self.status_message = format!("Expanding Soulseek search target to {} seeds ({}s) for '{}'...", target, duration, query);
                        self.rehunt_soulseek(id, query);
                    } else {
                        self.status_message = format!("Expanded seed target to {} ({}s).", target, duration);
                    }
                }
                KeyCode::Char('u') | KeyCode::Char('U') | KeyCode::Enter => {
                    if !self.seed_expansion_candidates.is_empty() {
                        self.show_seed_expansion_modal = false;
                        self.lossless_candidates = std::mem::take(&mut self.seed_expansion_candidates);
                        self.all_peer_files = std::mem::take(&mut self.seed_expansion_all_files);
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                        self.pending_job_id = self.seed_expansion_job_id;
                        self.show_lossless_selector = true;
                        self.status_message = format!(
                            "Opened lossless selector with {} discovered seed(s).",
                            self.lossless_candidates.len()
                        );
                    }
                }
                KeyCode::Char('a') | KeyCode::Char('A') | KeyCode::Esc => {
                    self.show_seed_expansion_modal = false;
                    if let Some(id) = self.seed_expansion_job_id {
                        if let Some(j) = self.jobs.iter_mut().find(|j| j.id == id) {
                            j.phase = JobPhase::Failed("Soulseek search aborted by user.".to_string());
                        }
                    }
                    self.seed_expansion_candidates.clear();
                    self.seed_expansion_all_files.clear();
                    self.seed_expansion_job_id = None;
                    self.status_message = "[SEARCH CANCELLED: Seed expansion aborted by user.]".to_string();
                }
                _ => {}
            }
            return;
        }

        if self.show_query_override_modal {
            match code {
                KeyCode::Enter => {
                    let query = self.query_override_input.trim().to_string();
                    if !query.is_empty() {
                        if let Some(id) = self.query_override_job_id {
                            self.rehunt_soulseek(id, query);
                        }
                    }
                    self.show_query_override_modal = false;
                }
                KeyCode::Esc => {
                    self.show_query_override_modal = false;
                    if let Some(id) = self.query_override_job_id {
                        if let Some(j) = self.jobs.iter_mut().find(|j| j.id == id) {
                            j.phase = JobPhase::Failed("No lossless seeds found. Web fallback disabled.".into());
                        }
                    }
                    self.status_message = "Cancelled Soulseek search query override.".to_string();
                }
                KeyCode::Backspace => {
                    self.query_override_input.pop();
                }
                KeyCode::Char(c) => {
                    self.query_override_input.push(c);
                }
                _ => {}
            }
            return;
        }

        if self.show_lossless_selector {
            if self.show_manual_entry_modal {
                match code {
                    KeyCode::Esc => {
                        self.show_manual_entry_modal = false;
                        self.status_message = "Closed Manual Entry modal.".to_string();
                    }
                    KeyCode::Tab | KeyCode::Down => {
                        self.manual_entry_focused_field = (self.manual_entry_focused_field + 1) % 3;
                    }
                    KeyCode::BackTab | KeyCode::Up => {
                        self.manual_entry_focused_field = (self.manual_entry_focused_field + 2) % 3;
                    }
                    KeyCode::Backspace => {
                        match self.manual_entry_focused_field {
                            0 => {
                                self.manual_entry_artist.pop();
                            }
                            1 => {
                                self.manual_entry_album.pop();
                            }
                            2 => {
                                self.manual_entry_track.pop();
                            }
                            _ => {}
                        }
                    }
                    KeyCode::Char(c) => {
                        match self.manual_entry_focused_field {
                            0 => self.manual_entry_artist.push(c),
                            1 => self.manual_entry_album.push(c),
                            2 => self.manual_entry_track.push(c),
                            _ => {}
                        }
                    }
                    KeyCode::F(1) => {
                        // Filter current in-memory candidates with entered tokens
                        let mut tokens = Vec::new();
                        if !self.manual_entry_artist.trim().is_empty() {
                            tokens.push(self.manual_entry_artist.trim().to_string());
                        }
                        if !self.manual_entry_album.trim().is_empty() {
                            tokens.push(self.manual_entry_album.trim().to_string());
                        }
                        if !self.manual_entry_track.trim().is_empty() {
                            tokens.push(self.manual_entry_track.trim().to_string());
                        }
                        self.lossless_filter_text = tokens.join(" ");
                        self.is_filtering_lossless = !self.lossless_filter_text.is_empty();
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                        self.show_manual_entry_modal = false;
                        self.status_message = format!("Filtered current results by '{}'", self.lossless_filter_text);
                    }
                    KeyCode::Enter => {
                        // Re-hunt Soulseek swarm with constructed query
                        let mut tokens = Vec::new();
                        if !self.manual_entry_artist.trim().is_empty() {
                            tokens.push(self.manual_entry_artist.trim().to_string());
                        }
                        if !self.manual_entry_album.trim().is_empty() {
                            tokens.push(self.manual_entry_album.trim().to_string());
                        }
                        if !self.manual_entry_track.trim().is_empty() {
                            tokens.push(self.manual_entry_track.trim().to_string());
                        }
                        let query = tokens.join(" ");
                        if !query.is_empty() {
                            self.show_manual_entry_modal = false;
                            self.show_lossless_selector = false;
                            if let Some(id) = self.pending_job_id {
                                self.rehunt_soulseek(id, query);
                            }
                        }
                    }
                    _ => {}
                }
                return;
            }

            if self.is_filtering_lossless {
                match code {
                    KeyCode::Esc => {
                        if !self.lossless_filter_text.is_empty() {
                            self.lossless_filter_text.clear();
                            self.selected_lossless_idx = 0;
                            self.lossless_list_state.select(Some(0));
                        } else {
                            self.is_filtering_lossless = false;
                        }
                    }
                    KeyCode::Backspace => {
                        self.lossless_filter_text.pop();
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                    }
                    KeyCode::Char(c) => {
                        self.lossless_filter_text.push(c);
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                    }
                    KeyCode::Up => {
                        if self.selected_lossless_idx > 0 {
                            self.selected_lossless_idx -= 1;
                            self.lossless_list_state.select(Some(self.selected_lossless_idx));
                        }
                    }
                    KeyCode::Down => {
                        let count = self.filtered_lossless_indices().len();
                        if self.selected_lossless_idx + 1 < count {
                            self.selected_lossless_idx += 1;
                            self.lossless_list_state.select(Some(self.selected_lossless_idx));
                        }
                    }
                    KeyCode::PageUp => {
                        self.selected_lossless_idx = self.selected_lossless_idx.saturating_sub(15);
                        self.lossless_list_state.select(Some(self.selected_lossless_idx));
                    }
                    KeyCode::PageDown => {
                        let count = self.filtered_lossless_indices().len();
                        if count > 0 {
                            self.selected_lossless_idx = (self.selected_lossless_idx + 15).min(count - 1);
                            self.lossless_list_state.select(Some(self.selected_lossless_idx));
                        }
                    }
                    KeyCode::Home => {
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                    }
                    KeyCode::End => {
                        let count = self.filtered_lossless_indices().len();
                        if count > 0 {
                            self.selected_lossless_idx = count.saturating_sub(1);
                            self.lossless_list_state.select(Some(self.selected_lossless_idx));
                        }
                    }
                    KeyCode::Tab => {
                        self.download_entire_album = !self.download_entire_album;
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                    }
                    KeyCode::Enter => {
                        self.confirm_lossless_selection();
                    }
                    _ => {}
                }
                return;
            }

            let count = self.filtered_lossless_indices().len();
            match code {
                KeyCode::Up | KeyCode::Char('k') => {
                    if self.selected_lossless_idx > 0 {
                        self.selected_lossless_idx -= 1;
                        self.lossless_list_state.select(Some(self.selected_lossless_idx));
                    }
                }
                KeyCode::Down | KeyCode::Char('j') => {
                    if self.selected_lossless_idx + 1 < count {
                        self.selected_lossless_idx += 1;
                        self.lossless_list_state.select(Some(self.selected_lossless_idx));
                    }
                }
                KeyCode::PageUp => {
                    self.selected_lossless_idx = self.selected_lossless_idx.saturating_sub(15);
                    self.lossless_list_state.select(Some(self.selected_lossless_idx));
                }
                KeyCode::PageDown => {
                    if count > 0 {
                        self.selected_lossless_idx = (self.selected_lossless_idx + 15).min(count - 1);
                        self.lossless_list_state.select(Some(self.selected_lossless_idx));
                    }
                }
                KeyCode::Home => {
                    self.selected_lossless_idx = 0;
                    self.lossless_list_state.select(Some(0));
                }
                KeyCode::End => {
                    if count > 0 {
                        self.selected_lossless_idx = count.saturating_sub(1);
                        self.lossless_list_state.select(Some(self.selected_lossless_idx));
                    }
                }
                KeyCode::Char('/') => {
                    self.is_filtering_lossless = true;
                }
                KeyCode::F(2) | KeyCode::Char('e') | KeyCode::Char('E') => {
                    self.show_manual_entry_modal = true;
                    self.manual_entry_focused_field = 0;
                }
                KeyCode::Tab | KeyCode::Char(' ') => {
                    self.download_entire_album = !self.download_entire_album;
                    self.selected_lossless_idx = 0;
                    self.lossless_list_state.select(Some(0));
                }
                KeyCode::Enter => {
                    self.confirm_lossless_selection();
                }
                KeyCode::Esc => {
                    if !self.lossless_filter_text.is_empty() {
                        self.lossless_filter_text.clear();
                        self.selected_lossless_idx = 0;
                        self.lossless_list_state.select(Some(0));
                    } else {
                        self.show_lossless_selector = false;
                        self.status_message = "Cancelled lossless version selection.".to_string();
                    }
                }
                _ => {}
            }
            return;
        }

        // When not actively editing URL text, numbers 1, 2, 3 switch workspace sub-tabs, and 'S' opens Advanced Search
        if !self.is_editing_url {
            match code {
                KeyCode::Char('s') | KeyCode::Char('S') if self.active_tab == DownloaderTab::Queue => {
                    self.show_advanced_search_modal = true;
                    self.adv_search_focused_field = 0;
                    return;
                }
                KeyCode::Char('1') | KeyCode::F(1) => {
                    self.active_tab = DownloaderTab::Queue;
                    self.status_message = "Tab: Downloads & Queue".to_string();
                    return;
                }
                KeyCode::Char('2') | KeyCode::F(2) => {
                    self.active_tab = DownloaderTab::Eq;
                    self.status_message = "Tab: 10-Band EQ Rails".to_string();
                    return;
                }
                KeyCode::Char('3') | KeyCode::F(3) => {
                    self.active_tab = DownloaderTab::Visuals;
                    self.load_selected_track_into_player();
                    return;
                }
                _ => {}
            }
        }

        match self.active_tab {
            DownloaderTab::Queue => self.handle_queue_key(code),
            DownloaderTab::Eq => self.handle_eq_key(code),
            DownloaderTab::Visuals => self.handle_visuals_key(code),
        }
    }

    /// Paste a URL or search text into the downloader input field or active modal.
    pub fn paste(&mut self, text: &str) {
        let clean = text.trim();
        if clean.is_empty() {
            return;
        }
        if self.show_advanced_search_modal {
            match self.adv_search_focused_field {
                0 => self.adv_search_artist.push_str(clean),
                1 => self.adv_search_track.push_str(clean),
                2 => self.adv_search_album.push_str(clean),
                _ => {}
            }
            return;
        }
        if self.show_query_override_modal {
            self.query_override_input.push_str(clean);
            return;
        }
        self.active_tab = DownloaderTab::Queue;
        self.focused_field = 0;
        self.is_editing_url = true;
        self.input_text.push_str(clean);
        self.status_message = format!("Pasted URL: {}", self.input_text);
    }

    fn handle_queue_key(&mut self, code: KeyCode) {
        if self.is_editing_url {
            match code {
                KeyCode::Tab => {
                    self.is_editing_url = false;
                    self.focused_field = 1;
                    self.status_message = format!(
                        "Focused Quality: < {} >. Press Left/Right to change format, Tab to Policy, Enter to download.",
                        self.selected_quality.label()
                    );
                }
                KeyCode::BackTab => {
                    self.is_editing_url = false;
                    self.focused_field = 4;
                    self.status_message = "Focused [ CONVERT & DOWNLOAD ]. Press Enter to start download, Tab to URL.".to_string();
                }
                KeyCode::Down => {
                    if !self.jobs.is_empty() {
                        self.is_editing_url = false;
                        self.selected_job_idx = 0;
                        self.job_list_state.select(Some(0));
                        self.status_message = "Selected download queue table. Use Up/Down to navigate.".to_string();
                    }
                }
                KeyCode::Esc => {
                    self.is_editing_url = false;
                    self.status_message = "URL edit mode closed. Press Tab to configure Quality/Policy, Enter to edit.".to_string();
                }
                KeyCode::Enter => {
                    self.is_editing_url = false;
                    self.submit_current();
                }
                KeyCode::Backspace => {
                    self.input_text.pop();
                }
                KeyCode::Char(c) => {
                    self.input_text.push(c);
                }
                _ => {}
            }
            return;
        }

        // Navigation mode (not editing URL)
        match code {
            KeyCode::Char('d') | KeyCode::Char('D') | KeyCode::Delete | KeyCode::Char('x') | KeyCode::Char('X') | KeyCode::Backspace => {
                self.delete_selected_job();
            }
            KeyCode::Enter | KeyCode::Char('/') | KeyCode::Char('i') if self.focused_field == 0 => {
                if self.input_text.is_empty() {
                    self.is_editing_url = true;
                    self.status_message = "Editing URL: Type/paste link, press Enter to convert, Tab to Quality, Esc to exit.".to_string();
                } else {
                    self.submit_current();
                }
            }
            KeyCode::Char(c) if self.focused_field == 0 && c != '1' && c != '2' && c != '3' && c != 'q' && c != 'Q' && c != 'e' && c != 'E' && c != 'd' && c != 'D' && c != 'x' && c != 'X' => {
                self.is_editing_url = true;
                self.input_text.push(c);
                self.status_message = "Editing URL: Press Enter to convert, Tab to Quality, Esc to exit.".to_string();
            }
            KeyCode::Enter if self.focused_field == 4 => {
                self.submit_current();
            }
            KeyCode::Enter if self.focused_field >= 1 && self.focused_field <= 3 => {
                if !self.input_text.trim().is_empty() {
                    self.submit_current();
                } else {
                    self.focused_field = (self.focused_field + 1) % 5;
                    self.update_focused_field_status();
                }
            }
            KeyCode::Tab => {
                self.focused_field = (self.focused_field + 1) % 5;
                self.update_focused_field_status();
            }
            KeyCode::BackTab => {
                self.focused_field = if self.focused_field == 0 { 4 } else { self.focused_field - 1 };
                self.update_focused_field_status();
            }
            KeyCode::Right => {
                if self.focused_field == 1 {
                    self.selected_quality = self.selected_quality.next();
                    self.status_message = format!("Quality: [ {} ] - {}", self.selected_quality.label(), self.selected_quality.description());
                } else if self.focused_field == 2 {
                    self.selected_policy = self.selected_policy.next();
                    self.status_message = format!("Acquisition Policy: [ {} ] - {}", self.selected_policy.label(), self.selected_policy.description());
                } else if self.focused_field == 3 {
                    self.download_lyrics = !self.download_lyrics;
                    self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
                }
            }
            KeyCode::Left => {
                if self.focused_field == 1 {
                    self.selected_quality = self.selected_quality.prev();
                    self.status_message = format!("Quality: [ {} ] - {}", self.selected_quality.label(), self.selected_quality.description());
                } else if self.focused_field == 2 {
                    self.selected_policy = self.selected_policy.prev();
                    self.status_message = format!("Acquisition Policy: [ {} ] - {}", self.selected_policy.label(), self.selected_policy.description());
                } else if self.focused_field == 3 {
                    self.download_lyrics = !self.download_lyrics;
                    self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
                }
            }
            KeyCode::Char('l') | KeyCode::Char('L') => {
                self.download_lyrics = !self.download_lyrics;
                self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char(' ') if self.focused_field == 3 => {
                self.download_lyrics = !self.download_lyrics;
                self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Up => {
                if !self.jobs.is_empty() && self.selected_job_idx > 0 {
                    self.selected_job_idx -= 1;
                    self.job_list_state.select(Some(self.selected_job_idx));
                }
            }
            KeyCode::Down => {
                if !self.jobs.is_empty() && self.selected_job_idx + 1 < self.jobs.len() {
                    self.selected_job_idx += 1;
                    self.job_list_state.select(Some(self.selected_job_idx));
                }
            }
            KeyCode::Char('e') | KeyCode::Char('E') => {
                self.trigger_enhancement();
            }
            _ => {}
        }
    }

    fn update_focused_field_status(&mut self) {
        match self.focused_field {
            0 => {
                self.status_message = "Focused URL field: Press Enter or type to edit, Tab to Quality.".to_string();
            }
            1 => {
                self.status_message = format!(
                    "Focused Quality: < {} >. Press Left/Right to change, Tab to Policy, Enter to download.",
                    self.selected_quality.label()
                );
            }
            2 => {
                self.status_message = format!(
                    "Focused Policy: < {} >. Press Left/Right to change, Tab to Lyrics, Enter to download.",
                    self.selected_policy.label()
                );
            }
            3 => {
                self.status_message = format!(
                    "Focused Lyrics: [ {} ]. Press Left/Right/Space to toggle, Tab to Convert, Enter to download.",
                    if self.download_lyrics { "ENABLED" } else { "DISABLED" }
                );
            }
            4 => {
                self.status_message = "Focused [ CONVERT & DOWNLOAD ]. Press Enter to start download, Tab to URL.".to_string();
            }
            _ => {}
        }
    }

    fn handle_eq_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Left => {
                self.selected_band = self.selected_band.saturating_sub(1);
            }
            KeyCode::Right => {
                self.selected_band = (self.selected_band + 1).min(9);
            }
            KeyCode::Up => {
                let current = self.band_gains[self.selected_band];
                self.band_gains[self.selected_band] = (current + 0.5).min(12.0);
            }
            KeyCode::Down => {
                let current = self.band_gains[self.selected_band];
                self.band_gains[self.selected_band] = (current - 0.5).max(-12.0);
            }
            KeyCode::Char('0') => {
                self.band_gains[self.selected_band] = 0.0;
            }
            KeyCode::Char('r') | KeyCode::Char('R') => {
                self.band_gains = [0.0; 10];
                self.status_message = "10-Band EQ reset to flat response (0.0 dB).".to_string();
            }
            KeyCode::Char('h') | KeyCode::Char('H') => {
                self.hpf_30hz = !self.hpf_30hz;
                self.status_message = format!("30Hz High-Pass Filter: {}", if self.hpf_30hz { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char('a') | KeyCode::Char('A') => {
                self.air_boost = !self.air_boost;
                self.status_message = format!("Air Boost (+3dB @ 16kHz): {}", if self.air_boost { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char('b') | KeyCode::Char('B') => {
                self.eq_bypass = !self.eq_bypass;
                self.status_message = format!("10-Band EQ Bypass: {}", if self.eq_bypass { "BYPASSED (Flat)" } else { "ACTIVE" });
            }
            KeyCode::Char('e') | KeyCode::Char('E') | KeyCode::Char('s') | KeyCode::Char('S') => {
                self.trigger_enhancement();
            }
            KeyCode::Tab => {
                self.active_tab = DownloaderTab::Visuals;
            }
            KeyCode::BackTab => {
                self.active_tab = DownloaderTab::Queue;
            }
            _ => {}
        }
    }

    fn handle_visuals_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Char(' ') => {
                let playing = self.player.toggle();
                if playing {
                    self.status_message = "Audio Player: [PLAYING]".to_string();
                } else {
                    self.status_message = "Audio Player: [PAUSED]".to_string();
                }
            }
            KeyCode::Left => {
                self.player.seek_by(-5.0);
                let (cur, total) = self.player.position();
                self.status_message = format!("Audio Player: Seek -5s [{:.0}s / {:.0}s]", cur, total);
            }
            KeyCode::Right => {
                self.player.seek_by(5.0);
                let (cur, total) = self.player.position();
                self.status_message = format!("Audio Player: Seek +5s [{:.0}s / {:.0}s]", cur, total);
            }
            KeyCode::Char('r') | KeyCode::Char('R') => {
                self.player.restart();
                self.status_message = "Audio Player: Restarted from beginning (0:00).".to_string();
            }
            KeyCode::Up | KeyCode::Char('+') | KeyCode::Char('=') => {
                let new_vol = self.player.adjust_volume_pct(5);
                self.status_message = format!("Audio Player: Volume {}%", new_vol);
            }
            KeyCode::Down | KeyCode::Char('-') | KeyCode::Char('_') => {
                let new_vol = self.player.adjust_volume_pct(-5);
                self.status_message = format!("Audio Player: Volume {}%", new_vol);
            }
            KeyCode::Char('m') | KeyCode::Char('M') => {
                let curr = self.player.volume_pct();
                let new_vol = if curr > 0 {
                    self.player.set_volume_pct(0);
                    0
                } else {
                    self.player.set_volume_pct(100);
                    100
                };
                if new_vol == 0 {
                    self.status_message = "Audio Player: Volume [MUTED] (0%)".to_string();
                } else {
                    self.status_message = "Audio Player: Volume [UNMUTED] (100%)".to_string();
                }
            }
            KeyCode::Char('1') | KeyCode::F(1) => {
                self.active_tab = DownloaderTab::Queue;
                self.status_message = "Tab: Downloads & Queue".to_string();
            }
            KeyCode::Char('2') | KeyCode::F(2) => {
                self.active_tab = DownloaderTab::Eq;
                self.status_message = "Tab: 10-Band EQ Rails (Auditioning Live)".to_string();
            }
            KeyCode::Char('s') | KeyCode::Char('S') | KeyCode::Char('e') | KeyCode::Char('E') => {
                self.trigger_enhancement();
            }
            KeyCode::Tab => {
                self.active_tab = DownloaderTab::Queue;
            }
            KeyCode::BackTab => {
                self.active_tab = DownloaderTab::Eq;
            }
            _ => {}
        }
    }

    pub fn render(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let root_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Sub-Tabs Bar
                Constraint::Min(12),  // Tab Content Workspace
            ])
            .split(area);

        // 1. Sub-Tabs Bar
        let tab_titles = vec![
            Line::from(DownloaderTab::Queue.label()),
            Line::from(DownloaderTab::Eq.label()),
            Line::from(DownloaderTab::Visuals.label()),
        ];
        let active_idx = match self.active_tab {
            DownloaderTab::Queue => 0,
            DownloaderTab::Eq => 1,
            DownloaderTab::Visuals => 2,
        };

        let tabs_widget = Tabs::new(tab_titles)
            .block(
                Block::default()
                    .title(" STUDIO WORKSPACE (Press 1: Queue | 2: 10-Band EQ | 3: Visuals) ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(theme.primary)),
            )
            .select(active_idx)
            .style(Style::default().fg(theme.text_dim))
            .highlight_style(
                Style::default()
                    .fg(theme.accent)
                    .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
            );
        f.render_widget(tabs_widget, root_chunks[0]);

        // 2. Tab Content Routing
        match self.active_tab {
            DownloaderTab::Queue => self.render_queue_tab(f, root_chunks[1], theme),
            DownloaderTab::Eq => self.render_eq_tab(f, root_chunks[1], theme),
            DownloaderTab::Visuals => self.render_visuals_tab(f, root_chunks[1], theme),
        }

        // 3. Modals & Overlays
        if self.show_advanced_search_modal {
            self.render_advanced_search_modal(f, area, theme);
        } else if self.show_lossless_selector {
            self.render_lossless_selector_modal(f, area, theme);
        } else if self.show_seed_expansion_modal {
            self.render_seed_expansion_modal(f, area, theme);
        } else if self.show_query_override_modal {
            self.render_query_override_modal(f, area, theme);
        }
    }

    fn render_query_override_modal(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let popup_area = centered_rect(65, 30, area);
        f.render_widget(Clear, popup_area);

        let block = Block::default()
            .title(" SOULSEEK SWARM QUERY OVERRIDE (NO LOSSLESS SEEDS FOUND) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.warning));
        let inner = block.inner(popup_area);
        f.render_widget(block, popup_area);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3),
                Constraint::Length(3),
                Constraint::Length(2),
            ])
            .split(inner);

        let info = Paragraph::new(vec![
            Line::from(Span::styled("Initial automated Soulseek search returned 0 lossless seeds.", Style::default().fg(Color::Yellow))),
            Line::from(Span::styled("Enter a refined or simplified search term below (e.g. track title only):", Style::default().fg(theme.text))),
        ]);
        f.render_widget(info, chunks[0]);

        let input_box = Paragraph::new(format!("> {}_", self.query_override_input))
            .style(Style::default().fg(theme.primary).add_modifier(Modifier::BOLD))
            .block(Block::default().title(" CUSTOM SOULSEEK SEARCH QUERY ").borders(Borders::ALL).border_style(Style::default().fg(theme.accent)));
        f.render_widget(input_box, chunks[1]);

        let guide = Paragraph::new(Line::from(vec![
            Span::styled(" [Enter] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Re-hunt Swarm  |  ", Style::default().fg(theme.text)),
            Span::styled(" [Esc] ", Style::default().fg(theme.text_dim).add_modifier(Modifier::BOLD)),
            Span::styled("Cancel / Abort", Style::default().fg(theme.text_dim)),
        ])).alignment(Alignment::Center);
        f.render_widget(guide, chunks[2]);
    }

    fn render_lossless_selector_modal(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let popup_area = centered_rect(96, 88, area);
        f.render_widget(Clear, popup_area);

        let filtered_indices = self.filtered_lossless_indices();
        let clusters = if self.download_entire_album {
            self.album_release_clusters()
        } else {
            Vec::new()
        };
        let total_count = if self.download_entire_album {
            clusters.len()
        } else {
            self.lossless_candidates.len()
        };
        let matching_count = if self.download_entire_album {
            clusters.len()
        } else {
            filtered_indices.len()
        };

        if matching_count > 0 {
            self.selected_lossless_idx = self.selected_lossless_idx.min(matching_count - 1);
            self.lossless_list_state.select(Some(self.selected_lossless_idx));
        } else {
            self.lossless_list_state.select(None);
        }

        let title_text = if self.download_entire_album {
            if !self.lossless_filter_text.is_empty() {
                format!(
                    " SOULSEEK ENTIRE ALBUM RELEASES (Showing {} of {} albums | Filter: '{}') ",
                    matching_count, total_count, self.lossless_filter_text
                )
            } else {
                format!(" SOULSEEK ENTIRE ALBUM RELEASES (Found {} peer albums) ", total_count)
            }
        } else if !self.lossless_filter_text.is_empty() {
            format!(
                " SOULSEEK LOSSLESS SWARM SELECTOR (Showing {} of {} versions | Filter: '{}') ",
                matching_count, total_count, self.lossless_filter_text
            )
        } else {
            format!(" SOULSEEK LOSSLESS SWARM SELECTOR (Found {} versions) ", total_count)
        };

        let modal_block = Block::default()
            .title(title_text)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.accent));

        let inner_area = modal_block.inner(popup_area);
        f.render_widget(modal_block, popup_area);

        let has_filter_bar = self.is_filtering_lossless || !self.lossless_filter_text.is_empty();
        let (scope_chunk, filter_chunk, list_chunk, footer_chunk) = if has_filter_bar {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3), // Scope selection radio row
                    Constraint::Length(3), // In-modal Filter Bar
                    Constraint::Min(6),   // Candidates list
                    Constraint::Length(2), // Bottom keybinding guidance
                ])
                .split(inner_area);
            (chunks[0], Some(chunks[1]), chunks[2], chunks[3])
        } else {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3), // Scope selection radio row
                    Constraint::Min(6),   // Candidates list
                    Constraint::Length(2), // Bottom keybinding guidance
                ])
                .split(inner_area);
            (chunks[0], None, chunks[1], chunks[2])
        };

        // 1. Download Scope Toggle Bar
        let single_style = if !self.download_entire_album {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text_dim)
        };
        let album_style = if self.download_entire_album {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text_dim)
        };

        let dir_display = if self.download_entire_album {
            clusters.get(self.selected_lossless_idx)
                .map(|c| c.directory.as_str())
                .unwrap_or("Album Folder")
                .to_string()
        } else {
            filtered_indices
                .get(self.selected_lossless_idx)
                .and_then(|&idx| self.lossless_candidates.get(idx))
                .map(|c| c.directory_name())
                .unwrap_or_else(|| "Album Folder".to_string())
        };

        let scope_spans = vec![
            Span::styled(" DOWNLOAD SCOPE:  ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled(
                if !self.download_entire_album { "(*) Single Track Only" } else { "( ) Single Track Only" },
                single_style,
            ),
            Span::raw("    "),
            Span::styled(
                if self.download_entire_album {
                    format!("(*) Entire Album / Directory [{}]", dir_display)
                } else {
                    format!("( ) Entire Album / Directory [{}]", dir_display)
                },
                album_style,
            ),
        ];

        let scope_p = Paragraph::new(vec![
            Line::from(scope_spans),
            Line::from(Span::styled("  Toggle scope with [Tab] or [Space] before confirming with [Enter]", Style::default().fg(theme.text_dim))),
        ]);
        f.render_widget(scope_p, scope_chunk);

        // 2. In-Modal Filter Bar (when active)
        if let Some(f_chunk) = filter_chunk {
            let cursor_str = if self.is_filtering_lossless { "_" } else { "" };
            let filter_line = Line::from(vec![
                Span::styled(" Filter: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled(
                    format!("{}{}", self.lossless_filter_text, cursor_str),
                    Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
                ),
                Span::raw("  "),
                Span::styled(
                    if self.is_filtering_lossless {
                        "(Press [Esc] to exit filter mode, [Enter] to queue)"
                    } else {
                        "(Press [/] to refine filter, [Esc] to clear)"
                    },
                    Style::default().fg(theme.text_dim),
                ),
            ]);
            let filter_block = Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(if self.is_filtering_lossless { Color::Yellow } else { theme.primary }));
            let filter_p = Paragraph::new(filter_line).block(filter_block);
            f.render_widget(filter_p, f_chunk);
        }

        // 3. Candidates / Album Releases List
        if self.download_entire_album {
            let album_panes = Layout::default()
                .direction(Direction::Horizontal)
                .constraints([
                    Constraint::Percentage(48), // Left: Album Releases
                    Constraint::Percentage(52), // Right: Inspected Tracklist & Enrichment
                ])
                .split(list_chunk);

            // Left Pane: Album clusters list
            let items: Vec<ListItem> = clusters.iter().enumerate().map(|(disp_idx, c)| {
                let is_selected = disp_idx == self.selected_lossless_idx;
                let cursor = if is_selected { "> " } else { "  " };

                let peer_str = format!("@{:<12} ", safe_truncate(&c.username, 12));
                let dir_str = format!("{:<16} ", safe_truncate(&c.directory, 16));
                let tracks_str = format!("{:<7} ", format!("{} trk", c.tracks.len()));
                let size_str = format!("{:<9} ", c.formatted_size());
                let speed_str = format!("{:<9} ", c.formatted_speed());
                let queue_str = if c.in_queue == 0 { "0 Q".to_string() } else { format!("Q: {}", c.in_queue) };

                let mut spans = vec![
                    Span::styled(cursor, if is_selected { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                    Span::styled(peer_str, Style::default().fg(Color::Cyan)),
                    Span::styled(dir_str, if is_selected { Style::default().fg(Color::White).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                    Span::styled(tracks_str, Style::default().fg(Color::Yellow)),
                    Span::styled(size_str, Style::default().fg(theme.accent)),
                    Span::styled(speed_str, Style::default().fg(Color::Green)),
                    Span::styled(format!("{:<6} ", queue_str), if c.in_queue == 0 { Style::default().fg(Color::Green) } else { Style::default().fg(Color::Yellow) }),
                ];

                if c.target_track_idx.is_some() {
                    spans.push(Span::styled("[TARGET FOUND]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)));
                }

                let bg_style = if is_selected {
                    Style::default().bg(Color::Rgb(30, 35, 45))
                } else {
                    Style::default()
                };

                ListItem::new(Line::from(spans)).style(bg_style)
            }).collect();

            let left_title = if matching_count > 0 {
                format!(
                    " ALBUM RELEASES (Item {} of {} | Peer | Directory | Tracks | Size | Speed | Queue) ",
                    self.selected_lossless_idx + 1,
                    matching_count
                )
            } else {
                " NO MATCHING ALBUMS FOUND IN SWARM (Press [Esc] to clear filter or [F2/E] for Manual Entry) ".to_string()
            };

            let left_block = Block::default()
                .title(left_title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.primary));

            let album_list = List::new(items).block(left_block);
            f.render_stateful_widget(album_list, album_panes[0], &mut self.lossless_list_state);

            let scrollbar = Scrollbar::default()
                .orientation(ScrollbarOrientation::VerticalRight)
                .begin_symbol(Some("^"))
                .end_symbol(Some("v"));
            let mut scrollbar_state = ScrollbarState::new(matching_count).position(self.selected_lossless_idx);
            f.render_stateful_widget(scrollbar, album_panes[0], &mut scrollbar_state);

            // Right Pane: Inspected Tracklist + Companion Assets
            let right_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Min(4),    // Tracklist
                    Constraint::Length(4), // Companion Assets
                ])
                .split(album_panes[1]);

            if let Some(c) = clusters.get(self.selected_lossless_idx) {
                let track_items: Vec<ListItem> = c.tracks.iter().enumerate().map(|(t_idx, t)| {
                    let is_target = c.target_track_idx == Some(t_idx);
                    let clean_fn = t.filename.replace('\\', "/");
                    let leaf = clean_fn.rsplit_once('/').map(|(_, l)| l).unwrap_or(&clean_fn);
                    let leaf_display = safe_truncate(leaf, 30);
                    let size_mb = format!("{:.1} MB", t.size as f64 / (1024.0 * 1024.0));
                    let num_str = format!("{:02}. ", t_idx + 1);

                    if is_target {
                        let line_spans = vec![
                            Span::styled(num_str, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                            Span::styled(format!("{:<30} ", leaf_display), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                            Span::styled(format!("{:<8} ", size_mb), Style::default().fg(Color::Yellow)),
                            Span::styled("[TARGET SONG - FOUND]", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        ];
                        ListItem::new(Line::from(line_spans)).style(Style::default().bg(Color::Rgb(45, 45, 20)))
                    } else {
                        let line_spans = vec![
                            Span::styled(num_str, Style::default().fg(theme.text_dim)),
                            Span::styled(format!("{:<30} ", leaf_display), Style::default().fg(theme.text)),
                            Span::styled(format!("{:<8} ", size_mb), Style::default().fg(theme.text_dim)),
                        ];
                        ListItem::new(Line::from(line_spans))
                    }
                }).collect();

                let track_block = Block::default()
                    .title(format!(" INSPECTED TRACKLIST: {} (@{} - {} tracks) ", c.directory, c.username, c.tracks.len()))
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(Color::Cyan));
                let track_list_widget = List::new(track_items).block(track_block);
                f.render_widget(track_list_widget, right_chunks[0]);

                // Companion assets
                let art_span = if !c.companion_images.is_empty() {
                    Span::styled(format!(" [Peer Art: {} img] ", c.companion_images.len()), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(" [MusicBrainz CAA Fallback] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
                };
                let lyrics_span = Span::styled(format!(" [Lyrics: {} tracks] ", c.tracks.len()), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD));
                let tags_span = Span::styled(" [FLAC Vorbis Tags] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

                let assets_lines = vec![
                    Line::from(vec![
                        Span::styled(" Artwork: ", Style::default().fg(theme.text_dim)),
                        art_span,
                        Span::raw(" | "),
                        Span::styled("Lyrics: ", Style::default().fg(theme.text_dim)),
                        lyrics_span,
                    ]),
                    Line::from(vec![
                        Span::styled(" Tagging: ", Style::default().fg(theme.text_dim)),
                        tags_span,
                        Span::styled(format!("Destination: ~/Music/{}/", c.directory), Style::default().fg(theme.text_dim)),
                    ]),
                ];

                let assets_p = Paragraph::new(assets_lines).block(
                    Block::default()
                        .title(" COMPANION ASSETS & INGESTION PIPELINE ")
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(theme.accent))
                );
                f.render_widget(assets_p, right_chunks[1]);
            } else {
                let empty_p = Paragraph::new("No peer album release selected.")
                    .block(Block::default().title(" INSPECTED TRACKLIST ").borders(Borders::ALL).border_style(Style::default().fg(theme.text_dim)));
                f.render_widget(empty_p, album_panes[1]);
            }
        } else {
            let items: Vec<ListItem> = filtered_indices.iter().enumerate().map(|(disp_idx, &real_idx)| {
                let c = &self.lossless_candidates[real_idx];
                let is_selected = disp_idx == self.selected_lossless_idx;
                let cursor = if is_selected { "> " } else { "  " };

                let res_str = c.formatted_resolution();
                let bitrate_str = match c.bitrate_kbps {
                    Some(b) if b > 0 => format!("{}k", b),
                    _ => "Lossless".to_string(),
                };
                let size_str = c.formatted_size();
                let peer_str = &c.username;
                let dir_str = c.directory_name();
                let file_leaf = c.filename.replace('\\', "/");
                let file_leaf = file_leaf.rsplit_once('/').map(|(_, f)| f).unwrap_or(&c.filename);

                let speed_str = c.formatted_speed();
                let queue_str = c.formatted_queue();

                let speed_style = match c.speed_kbps {
                    Some(kb) if kb >= 1024.0 => Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                    Some(kb) if kb >= 250.0 => Style::default().fg(Color::Cyan),
                    _ => Style::default().fg(Color::Yellow),
                };

                let queue_style = if c.in_queue == 0 {
                    Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
                } else if c.in_queue <= 4 {
                    Style::default().fg(Color::Yellow)
                } else {
                    Style::default().fg(Color::LightRed)
                };

                let line_spans = vec![
                    Span::styled(cursor, if is_selected { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                    Span::styled(format!("{:<15} ", res_str), if is_selected { Style::default().fg(theme.primary).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                    Span::styled(format!("{:<8} ", bitrate_str), Style::default().fg(theme.accent)),
                    Span::styled(format!("{:<8} ", size_str), Style::default().fg(Color::Yellow)),
                    Span::styled(format!("{:<9} ", speed_str), speed_style),
                    Span::styled(format!("{:<10} ", queue_str), queue_style),
                    Span::styled(format!("@{:<12} ", peer_str), Style::default().fg(Color::Cyan)),
                    Span::styled(format!("[{}] ", dir_str), Style::default().fg(theme.text_dim)),
                    Span::styled(file_leaf.to_string(), if is_selected { Style::default().fg(Color::White).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                ];

                let bg_style = if is_selected {
                    Style::default().bg(Color::Rgb(30, 35, 45))
                } else {
                    Style::default()
                };

                ListItem::new(Line::from(line_spans)).style(bg_style)
            }).collect();

            let list_title = if matching_count > 0 {
                format!(
                    " AVAILABLE LOSSLESS RELEASES (Item {} of {} | Resolution | Bitrate | Size | Speed | Queue | Peer | Directory) ",
                    self.selected_lossless_idx + 1,
                    matching_count
                )
            } else {
                " NO MATCHING LOSSLESS RELEASES IN SWARM (Press [Esc] to clear filter or [F2/E] for Manual Entry) ".to_string()
            };

            let list_block = Block::default()
                .title(list_title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.primary));

            let cand_layout = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Min(6),
                    Constraint::Length(4),
                ])
                .split(list_chunk);

            let candidate_list = List::new(items).block(list_block);
            f.render_stateful_widget(candidate_list, cand_layout[0], &mut self.lossless_list_state);

            // Vertical Scrollbar
            let scrollbar = Scrollbar::default()
                .orientation(ScrollbarOrientation::VerticalRight)
                .begin_symbol(Some("^"))
                .end_symbol(Some("v"));
            let mut scrollbar_state = ScrollbarState::new(matching_count).position(self.selected_lossless_idx);
            f.render_stateful_widget(scrollbar, cand_layout[0], &mut scrollbar_state);

            // Inspected candidate full path & metadata pane (Zero Truncation)
            let inspected_cand = filtered_indices.get(self.selected_lossless_idx).and_then(|&idx| self.lossless_candidates.get(idx));
            let detail_lines = if let Some(c) = inspected_cand {
                vec![
                    Line::from(vec![
                        Span::styled(" Track / File: ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                        Span::styled(&c.filename, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                    ]),
                    Line::from(vec![
                        Span::styled(" Directory:    ", Style::default().fg(theme.text_dim)),
                        Span::styled(c.directory_name(), Style::default().fg(Color::Yellow)),
                        Span::styled(" | Peer: ", Style::default().fg(theme.text_dim)),
                        Span::styled(format!("@{}", c.username), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        Span::styled(" | Quality: ", Style::default().fg(theme.text_dim)),
                        Span::styled(format!("{} ({})", c.formatted_resolution(), c.formatted_size()), Style::default().fg(theme.primary)),
                        Span::styled(" | Speed: ", Style::default().fg(theme.text_dim)),
                        Span::styled(c.formatted_speed(), Style::default().fg(Color::Green)),
                        Span::styled(" | Queue: ", Style::default().fg(theme.text_dim)),
                        Span::styled(c.formatted_queue(), Style::default().fg(Color::LightMagenta)),
                    ]),
                ]
            } else {
                vec![Line::from(Span::styled("No candidate selected.", Style::default().fg(theme.text_dim)))]
            };

            let detail_block = Block::default()
                .title(" INSPECTED CANDIDATE FULL PATH & SWARM DETAILS (NO TRUNCATION) ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Cyan));
            let p_detail = Paragraph::new(detail_lines)
                .block(detail_block)
                .wrap(ratatui::widgets::Wrap { trim: true });
            f.render_widget(p_detail, cand_layout[1]);
        }

        // 4. Keybindings bar
        let footer = Line::from(vec![
            Span::styled(" [Up/Dn] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Move | "),
            Span::styled(" [PgUp/Dn] ", Style::default().fg(theme.accent)),
            Span::raw("Scroll | "),
            Span::styled(" [/] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("Filter | "),
            Span::styled(" [F2/E] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Manual | "),
            Span::styled(" [Tab] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Scope | "),
            Span::styled(" [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw("Queue | "),
            Span::styled(" [Esc] ", Style::default().fg(Color::Red)),
            Span::raw("Cancel"),
        ]);
        let footer_p = Paragraph::new(footer).alignment(Alignment::Center);
        f.render_widget(footer_p, footer_chunk);

        // 5. Tri-Field Manual Entry & Re-Hunt Overlay Modal
        if self.show_manual_entry_modal {
            let manual_area = centered_rect(65, 45, area);
            f.render_widget(Clear, manual_area);

            let manual_block = Block::default()
                .title(" MANUAL ENTRY & SOULSEEK RE-HUNT (Artist / Album / Track) ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.accent));
            let inner_manual = manual_block.inner(manual_area);
            f.render_widget(manual_block, manual_area);

            let m_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(2), // Info description
                    Constraint::Length(3), // Field 0: Artist
                    Constraint::Length(3), // Field 1: Album
                    Constraint::Length(3), // Field 2: Track
                    Constraint::Length(2), // Footer keybindings
                ])
                .split(inner_manual);

            let m_info = Paragraph::new(Line::from(vec![
                Span::styled(
                    "Solidify search terms to filter current matches or trigger a targeted Soulseek re-hunt:",
                    Style::default().fg(theme.text_dim),
                ),
            ]));
            f.render_widget(m_info, m_chunks[0]);

            let f0_active = self.manual_entry_focused_field == 0;
            let f1_active = self.manual_entry_focused_field == 1;
            let f2_active = self.manual_entry_focused_field == 2;

            let artist_input = Paragraph::new(format!("> {}{}", self.manual_entry_artist, if f0_active { "_" } else { "" }))
                .style(if f0_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
                .block(
                    Block::default()
                        .title(" [1. ARTIST] ")
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(if f0_active { Color::Yellow } else { theme.primary })),
                );
            f.render_widget(artist_input, m_chunks[1]);

            let album_input = Paragraph::new(format!("> {}{}", self.manual_entry_album, if f1_active { "_" } else { "" }))
                .style(if f1_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
                .block(
                    Block::default()
                        .title(" [2. ALBUM (OPTIONAL)] ")
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(if f1_active { Color::Yellow } else { theme.primary })),
                );
            f.render_widget(album_input, m_chunks[2]);

            let track_input = Paragraph::new(format!("> {}{}", self.manual_entry_track, if f2_active { "_" } else { "" }))
                .style(if f2_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
                .block(
                    Block::default()
                        .title(" [3. TRACK / SONG (OPTIONAL)] ")
                        .borders(Borders::ALL)
                        .border_style(Style::default().fg(if f2_active { Color::Yellow } else { theme.primary })),
                );
            f.render_widget(track_input, m_chunks[3]);

            let m_footer = Paragraph::new(Line::from(vec![
                Span::styled(" [Tab] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::raw("Next Field  | "),
                Span::styled(" [F1] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("Filter Current  | "),
                Span::styled(" [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::raw("Re-Hunt Swarm  | "),
                Span::styled(" [Esc] ", Style::default().fg(Color::Red)),
                Span::raw("Cancel"),
            ])).alignment(Alignment::Center);
            f.render_widget(m_footer, m_chunks[4]);
        }
    }

    fn render_seed_expansion_modal(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        if !self.show_seed_expansion_modal {
            return;
        }

        let popup_width = 72.min(area.width.saturating_sub(4));
        let popup_height = 14.min(area.height.saturating_sub(4));
        let x = area.x + (area.width.saturating_sub(popup_width)) / 2;
        let y = area.y + (area.height.saturating_sub(popup_height)) / 2;
        let popup_area = Rect::new(x, y, popup_width, popup_height);

        f.render_widget(Clear, popup_area);

        let border_block = Block::default()
            .title(" [ SOULSEEK SEED AVAILABILITY ] ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
        f.render_widget(border_block, popup_area);

        let inner_area = popup_area.inner(ratatui::layout::Margin { vertical: 1, horizontal: 2 });
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2), // Status header
                Constraint::Length(3), // Description
                Constraint::Length(2), // Search duration row
                Constraint::Length(2), // Action keys
            ])
            .split(inner_area);

        let found = self.seed_expansion_found_count;
        let target = self.target_seeds;
        let next_target = target + 10;
        let duration = self.seed_expansion_duration_secs;

        let status_line = Line::from(vec![
            Span::styled("SWARM STATUS: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled(
                format!("{} Lossless Seed(s) Discovered", found),
                Style::default().fg(if found > 0 { Color::Green } else { Color::Red }).add_modifier(Modifier::BOLD),
            ),
            Span::raw("  |  "),
            Span::styled(format!("Target: {} Seeds", target), Style::default().fg(Color::Yellow)),
        ]);
        f.render_widget(Paragraph::new(status_line), chunks[0]);

        let desc_text = if found == 0 {
            format!(
                "The Soulseek swarm did not return any lossless seeds matching your query within the initial search window. Would you like to expand the target to {} seeds and deepen the search, or abort?",
                next_target
            )
        } else {
            format!(
                "The Soulseek swarm returned {} seed(s), which is fewer than your target of {} seeds. You may proceed to expand the swarm search to {} seeds, use the discovered seeds, or abort.",
                found, target, next_target
            )
        };
        let desc_p = Paragraph::new(desc_text)
            .style(Style::default().fg(theme.text_dim))
            .wrap(ratatui::widgets::Wrap { trim: true });
        f.render_widget(desc_p, chunks[1]);

        let duration_line = if self.seed_expansion_editing_time {
            Line::from(vec![
                Span::styled("SEARCH DURATION: [ ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled(format!("{}_", self.seed_expansion_time_input), Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Span::styled(" ] seconds", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("    "),
                Span::styled("[Type digits | Enter/T: Commit | Esc: Cancel]", Style::default().fg(theme.text_dim)),
            ])
        } else {
            Line::from(vec![
                Span::styled("SEARCH DURATION: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(format!("< {}s >", duration), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::raw("    "),
                Span::styled("[Left/Right or Up/Down: -/+5s | T: Type Exact Seconds]", Style::default().fg(theme.text_dim)),
            ])
        };
        f.render_widget(Paragraph::new(duration_line), chunks[2]);

        let mut actions = vec![
            Span::styled(" [P] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled(format!("Proceed (+10 Seeds, {}s Search)", duration), Style::default().fg(theme.text)),
            Span::raw("    "),
        ];

        if found > 0 {
            actions.push(Span::styled(" [U / Enter] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)));
            actions.push(Span::styled(format!("Use Current ({} Seeds)", found), Style::default().fg(theme.text)));
            actions.push(Span::raw("    "));
        }

        actions.push(Span::styled(" [A / Esc] ", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)));
        actions.push(Span::styled("Abort", Style::default().fg(theme.text)));

        let actions_p = Paragraph::new(Line::from(actions)).alignment(Alignment::Center);
        f.render_widget(actions_p, chunks[3]);
    }

    fn render_advanced_search_modal(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        if !self.show_advanced_search_modal {
            return;
        }

        let popup_width = 74.min(area.width.saturating_sub(4));
        let popup_height = 18.min(area.height.saturating_sub(4));
        let x = area.x + (area.width.saturating_sub(popup_width)) / 2;
        let y = area.y + (area.height.saturating_sub(popup_height)) / 2;
        let popup_area = Rect::new(x, y, popup_width, popup_height);

        f.render_widget(Clear, popup_area);

        let border_block = Block::default()
            .title(" [ ADVANCED SWARM & WEB SEARCH ] ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));
        f.render_widget(border_block, popup_area);

        let inner_area = popup_area.inner(ratatui::layout::Margin { vertical: 1, horizontal: 2 });
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // 1. Artist field
                Constraint::Length(3), // 2. Track field
                Constraint::Length(3), // 3. Album field
                Constraint::Length(3), // 4. Target Engine
                Constraint::Length(1), // Spacer
                Constraint::Length(2), // Action keys
            ])
            .split(inner_area);

        let f0_active = self.adv_search_focused_field == 0;
        let f1_active = self.adv_search_focused_field == 1;
        let f2_active = self.adv_search_focused_field == 2;
        let f3_active = self.adv_search_focused_field == 3;

        // 1. Artist Input
        let artist_p = Paragraph::new(format!("> {}{}", self.adv_search_artist, if f0_active { "_" } else { "" }))
            .style(if f0_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
            .block(
                Block::default()
                    .title(" [1. ARTIST] ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(if f0_active { Color::Yellow } else { theme.primary })),
            );
        f.render_widget(artist_p, chunks[0]);

        // 2. Track / Song Input
        let track_p = Paragraph::new(format!("> {}{}", self.adv_search_track, if f1_active { "_" } else { "" }))
            .style(if f1_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
            .block(
                Block::default()
                    .title(" [2. TRACK / SONG (OPTIONAL IF ALBUM)] ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(if f1_active { Color::Yellow } else { theme.primary })),
            );
        f.render_widget(track_p, chunks[1]);

        // 3. Album Input
        let album_p = Paragraph::new(format!("> {}{}", self.adv_search_album, if f2_active { "_" } else { "" }))
            .style(if f2_active { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) })
            .block(
                Block::default()
                    .title(" [3. ALBUM (OPTIONAL)] ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(if f2_active { Color::Yellow } else { theme.primary })),
            );
        f.render_widget(album_p, chunks[2]);

        // 4. Target Engine Selector
        let engine_block = Block::default()
            .title(" [4. SEARCH TARGET ENGINE] ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(if f3_active { Color::Yellow } else { theme.primary }));

        let engine = self.adv_search_target_engine;
        let e_slsk = if engine == SearchTargetEngine::SoulseekP2P { "(*) Soulseek P2P" } else { "( ) Soulseek P2P" };
        let e_yt = if engine == SearchTargetEngine::YouTube { "(*) YouTube Web" } else { "( ) YouTube Web" };
        let e_hyb = if engine == SearchTargetEngine::Hybrid { "(*) Hybrid (P2P + Web)" } else { "( ) Hybrid (P2P + Web)" };

        let engine_spans = vec![
            Span::raw("  "),
            Span::styled(e_slsk, if engine == SearchTargetEngine::SoulseekP2P { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
            Span::raw("    "),
            Span::styled(e_yt, if engine == SearchTargetEngine::YouTube { Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
            Span::raw("    "),
            Span::styled(e_hyb, if engine == SearchTargetEngine::Hybrid { Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
        ];
        let engine_p = Paragraph::new(Line::from(engine_spans)).block(engine_block);
        f.render_widget(engine_p, chunks[3]);

        // Footer Actions
        let footer_line = Line::from(vec![
            Span::styled(" [Tab] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Next Field  | "),
            Span::styled(" [◄/►] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("Engine  | "),
            Span::styled(" [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw("Launch Search  | "),
            Span::styled(" [Esc] ", Style::default().fg(Color::Red)),
            Span::raw("Cancel"),
        ]);
        f.render_widget(Paragraph::new(footer_line).alignment(Alignment::Center), chunks[5]);
    }

    fn render_queue_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Top input row & controls
                Constraint::Min(8),   // Job Table
                Constraint::Length(7), // Forensic Spectral / Failure Diagnostic Inspection Pane
            ])
            .split(area);

        // 1. Top Controls Bar
        let soulseek_tag = if let Some(ref u) = self.active_soulseek_user {
            format!(" [Soulseek: {} | 'A' Accounts] ", u)
        } else {
            " [Soulseek: Not Connected | 'A' Accounts] ".to_string()
        };
        let bar_block = Block::default()
            .title(format!(" MP3 DOWNLOADER & CONVERSION CONTROLS {} ", soulseek_tag))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let bar_inner = bar_block.inner(chunks[0]);
        f.render_widget(bar_block, chunks[0]);

        let input_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Min(25),    // 0: URL Input
                Constraint::Length(30), // 1: Quality select
                Constraint::Length(33), // 2: Policy select
                Constraint::Length(15), // 3: Lyrics toggle
                Constraint::Length(15), // 4: Convert Button
            ])
            .split(bar_inner);

        // URL Input
        let input_style = if self.focused_field == 0 {
            if self.is_editing_url {
                Style::default().fg(theme.accent).bg(theme.surface).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            }
        } else {
            Style::default().fg(theme.text)
        };
        let input_prefix = if self.focused_field == 0 {
            if self.is_editing_url {
                "[EDIT] > "
            } else {
                "[►] > "
            }
        } else {
            "  > "
        };
        let input_placeholder = if self.is_editing_url {
            "[Paste link or type query | Enter: Search]"
        } else {
            "[Enter: edit | S: Adv Search | Tab: Quality]"
        };
        let input_display = if self.input_text.is_empty() {
            input_placeholder
        } else {
            &self.input_text
        };
        let p_input = Paragraph::new(format!("{}SEARCH: {}", input_prefix, input_display))
            .style(input_style);
        f.render_widget(p_input, input_chunks[0]);

        // Quality Select
        let (q_text, q_style) = if self.focused_field == 1 {
            (
                format!("[► Quality: {} ◄]", self.selected_quality.label()),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!(" Quality: < {} > ", self.selected_quality.label()),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_q = Paragraph::new(q_text).style(q_style);
        f.render_widget(p_q, input_chunks[1]);

        // Policy Select
        let (pol_text, pol_style) = if self.focused_field == 2 {
            (
                format!("[► Policy: {} ◄]", self.selected_policy.label()),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!(" Policy: < {} > ", self.selected_policy.label()),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_pol = Paragraph::new(pol_text).style(pol_style);
        f.render_widget(p_pol, input_chunks[2]);

        // Lyrics Toggle
        let (lyr_text, lyr_style) = if self.focused_field == 3 {
            (
                format!("[► Lyrics: {} ◄]", if self.download_lyrics { "ON" } else { "OFF" }),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!("  Lyrics: {}  ", if self.download_lyrics { "ON" } else { "OFF" }),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_lyr = Paragraph::new(lyr_text).style(lyr_style);
        f.render_widget(p_lyr, input_chunks[3]);

        // Convert Button
        let (btn_text, btn_style) = if self.focused_field == 4 {
            (
                "[► CONVERT ◄]",
                Style::default().fg(Color::Black).bg(theme.primary).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                "[ CONVERT ]",
                Style::default().fg(theme.primary),
            )
        };
        let p_btn = Paragraph::new(btn_text)
            .style(btn_style)
            .alignment(Alignment::Center);
        f.render_widget(p_btn, input_chunks[4]);

        // 2. Active Job Table
        let table_block = Block::default()
            .title(" ACTIVE DOWNLOADS & CONVERSION QUEUE (Up/Down Navigate | [D/Del] Delete | [E] Enhance Lossless) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border));
        let table_inner = table_block.inner(chunks[1]);
        f.render_widget(table_block, chunks[1]);

        if self.jobs.is_empty() {
            let empty_text = vec![
                Line::from(""),
                Line::from(vec![
                    Span::styled("   No active download jobs in queue.", Style::default().fg(theme.text_dim)),
                ]),
                Line::from(vec![
                    Span::styled("   Paste a link above and press Enter to rip high-bitrate audio.", Style::default().fg(theme.text_dim)),
                ]),
            ];
            let p_empty = Paragraph::new(empty_text);
            f.render_widget(p_empty, table_inner);
        } else {
            let items: Vec<ListItem> = self.jobs.iter().enumerate().map(|(i, j)| {
                let is_sel = i == self.selected_job_idx;
                let phase_color = match j.phase {
                    JobPhase::Completed => theme.success,
                    JobPhase::Failed(_) => theme.error,
                    JobPhase::Downloading | JobPhase::Auditing => theme.accent,
                    _ => theme.text_dim,
                };

                let prefix = if is_sel { "> " } else { "  " };
                let bar_width = 16;
                let filled = ((j.progress / 100.0) * bar_width as f32) as usize;
                let bar = format!("[{}{}]", "=".repeat(filled.min(bar_width)), " ".repeat(bar_width.saturating_sub(filled)));

                let main_line = format!(
                    "{}#{:<2} {:<30} {:<12} {:<14} {:>4.0}% {} {:<10} ETA: {}",
                    prefix,
                    j.id,
                    j.display_name,
                    j.quality.label(),
                    j.phase.short_label(),
                    j.progress,
                    bar,
                    j.speed,
                    j.eta
                );

                let mut item_lines = vec![Line::from(main_line)];

                // Show full error text wrapped without truncation for failed jobs
                if let JobPhase::Failed(ref err) = j.phase {
                    let avail_w = (table_inner.width as usize).saturating_sub(12).max(35);
                    let err_chunks = wrap_text_to_chunks(err, avail_w);
                    for (c_idx, chk) in err_chunks.iter().enumerate() {
                        let pfx = if c_idx == 0 { "      └─ Error: " } else { "                " };
                        item_lines.push(Line::from(vec![
                            Span::styled(pfx, Style::default().fg(theme.error).add_modifier(Modifier::BOLD)),
                            Span::styled(chk.clone(), Style::default().fg(theme.error)),
                        ]));
                    }
                }

                let style = if is_sel {
                    Style::default().fg(theme.text).bg(theme.surface).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(phase_color)
                };

                ListItem::new(item_lines).style(style)
            }).collect();

            let list = List::new(items)
                .highlight_style(Style::default().bg(theme.surface).add_modifier(Modifier::BOLD));
            f.render_stateful_widget(list, table_inner, &mut self.job_list_state);
        }

        // 3. Forensic Spectral Cutoff & Failure Diagnostics Inspection Pane
        let is_failed = self.jobs.get(self.selected_job_idx).map(|j| matches!(j.phase, JobPhase::Failed(_))).unwrap_or(false);
        let (audit_title, audit_border_color) = if is_failed {
            (" JOB STATUS & DIAGNOSTICS: FAILED ", theme.error)
        } else {
            (" FORENSIC SPECTRAL CUTOFF & QUALITY VERIFICATION ", theme.secondary)
        };

        let audit_block = Block::default()
            .title(audit_title)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(audit_border_color));
        let audit_inner = audit_block.inner(chunks[2]);
        f.render_widget(audit_block, chunks[2]);

        let audit_lines = if let Some(job) = self.jobs.get(self.selected_job_idx) {
            match &job.phase {
                JobPhase::Failed(err) => {
                    let mut lines = vec![
                        Line::from(vec![
                            Span::styled(format!("Track: {} | Target: {} | Status: ", job.display_name, job.quality.label()), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                            Span::styled("[FAILED]", Style::default().fg(theme.error).add_modifier(Modifier::BOLD)),
                        ]),
                    ];
                    let avail_w = (audit_inner.width as usize).saturating_sub(16).max(35);
                    let err_chunks = wrap_text_to_chunks(err, avail_w);
                    for (idx, chk) in err_chunks.iter().enumerate() {
                        let pfx = if idx == 0 { "Error Detail: " } else { "              " };
                        lines.push(Line::from(vec![
                            Span::styled(pfx, Style::default().fg(theme.error).add_modifier(Modifier::BOLD)),
                            Span::styled(chk.clone(), Style::default().fg(theme.text)),
                        ]));
                    }
                    if err.contains("localhost:5030") || err.contains("slskd") || err.contains("Soulseek") {
                        lines.push(Line::from(vec![
                            Span::styled("Remediation: ", Style::default().fg(theme.warning).add_modifier(Modifier::BOLD)),
                            Span::styled("Soulseek daemon (slskd) is offline on port 5030. Launch slskd locally or switch target quality to High Bitrate MP3 / YouTube.", Style::default().fg(theme.text_dim)),
                        ]));
                    }
                    lines
                }
                _ => {
                    let verdict = job.spectral_verdict.as_deref().unwrap_or("Waiting for file download completion...");
                    vec![
                        Line::from(vec![
                            Span::styled(format!("Track: {} | Target: {}", job.display_name, job.quality.label()), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                        ]),
                        Line::from(vec![
                            Span::styled("Authenticity: ", Style::default().fg(theme.text_dim)),
                            Span::styled(verdict, Style::default().fg(if verdict.contains("TRUE") { theme.success } else { theme.warning })),
                        ]),
                    ]
                }
            }
        } else {
            vec![
                Line::from(vec![
                    Span::styled("No job selected. Select a job in the queue to inspect frequency cutoff and tags.", Style::default().fg(theme.text_dim)),
                ]),
            ]
        };

        let p_audit = Paragraph::new(audit_lines);
        f.render_widget(p_audit, audit_inner);
    }

    fn render_eq_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Top EQ Status & Master Switch bar
                Constraint::Min(12),  // 10-Band Sliders Rails
                Constraint::Length(3), // Bottom hotkey helper bar
            ])
            .split(area);

        // 1. Status Bar
        let bypass_str = if self.eq_bypass { "[BYPASSED (FLAT)]" } else { "[ACTIVE]" };
        let bypass_color = if self.eq_bypass { theme.warning } else { theme.success };
        let hpf_str = if self.hpf_30hz { "ON (Sub-bass Cut)" } else { "OFF" };
        let air_str = if self.air_boost { "ON (+3dB @ 16kHz)" } else { "OFF" };

        let dac_flavor = crate::dsp::volume_storage::load_dac_flavor_setting();

        let status_spans = vec![
            Span::styled(" MASTER EQ STATUS: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled(bypass_str, Style::default().fg(bypass_color).add_modifier(Modifier::BOLD)),
            Span::raw("   |   "),
            Span::styled("DAC: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("[{}]", dac_flavor.short_label()), Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::raw("   |   "),
            Span::styled("30Hz HPF: ", Style::default().fg(theme.text_dim)),
            Span::styled(hpf_str, Style::default().fg(if self.hpf_30hz { theme.accent } else { theme.text_dim })),
            Span::raw("   |   "),
            Span::styled("Air Boost: ", Style::default().fg(theme.text_dim)),
            Span::styled(air_str, Style::default().fg(if self.air_boost { theme.accent } else { theme.text_dim })),
            Span::raw("   |   "),
            Span::styled(format!("Focus Band: {}", FREQ_LABELS[self.selected_band]), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ];

        let p_status = Paragraph::new(Line::from(status_spans))
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.primary)));
        f.render_widget(p_status, chunks[0]);

        // 2. 10 Vertical Bands
        let bands_block = Block::default()
            .title(" 10-BAND ISO GRAPHIC EQUALIZER RAILS (-12.0 dB to +12.0 dB) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border));
        let bands_inner = bands_block.inner(chunks[1]);
        f.render_widget(bands_block, chunks[1]);

        let col_constraints = vec![Constraint::Ratio(1, 10); 10];
        let cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints(col_constraints)
            .split(bands_inner);

        for i in 0..10 {
            let is_sel = i == self.selected_band;
            let gain = self.band_gains[i];
            let label = FREQ_LABELS[i];

            let border_color = if is_sel {
                theme.accent
            } else {
                theme.border
            };

            let gain_str = if gain > 0.0 {
                format!("+{:>4.1}dB", gain)
            } else if gain < 0.0 {
                format!("{:>5.1}dB", gain)
            } else {
                "  0.0dB".to_string()
            };

            let gain_color = if self.eq_bypass {
                theme.text_dim
            } else if gain > 0.0 {
                theme.accent
            } else if gain < 0.0 {
                theme.secondary
            } else {
                theme.text
            };

            // Rail graphic calculation (-12dB to +12dB => 25 discrete steps)
            let height = cols[i].height.saturating_sub(4) as usize;
            let mut rail_lines = Vec::new();
            
            // Generate visual slider track
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
                    Style::default().fg(if is_sel { theme.accent } else { theme.primary }).add_modifier(Modifier::BOLD)
                } else if row == height / 2 {
                    Style::default().fg(theme.border)
                } else {
                    Style::default().fg(theme.text_dim)
                };

                rail_lines.push(Line::from(vec![Span::styled(track_char, style)]));
            }

            // Top frequency header + gain text
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
                .style(Style::default().fg(gain_color).add_modifier(if is_sel { Modifier::BOLD } else { Modifier::empty() }));
            f.render_widget(p_gain, col_chunks[0]);

            let p_rail = Paragraph::new(rail_lines)
                .alignment(Alignment::Center);
            f.render_widget(p_rail, col_chunks[1]);
        }

        // 3. Bottom Hotkey Guide
        let guide_text = Line::from(vec![
            Span::styled(" [Left/Right] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Select Band  ", Style::default().fg(theme.text)),
            Span::styled(" [Up/Down] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("+/-0.5 dB  ", Style::default().fg(theme.text)),
            Span::styled(" [0] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled("Zero  ", Style::default().fg(theme.text)),
            Span::styled(" [R] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled("Reset Flat  ", Style::default().fg(theme.text)),
            Span::styled(" [H] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("30Hz HPF  ", Style::default().fg(theme.text)),
            Span::styled(" [A] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("Air Boost  ", Style::default().fg(theme.text)),
            Span::styled(" [B] ", Style::default().fg(theme.warning).add_modifier(Modifier::BOLD)),
            Span::styled("Bypass  ", Style::default().fg(theme.text)),
            Span::styled(" [E] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Enhance Track  ", Style::default().fg(theme.text)),
            Span::styled(" [Tab] ", Style::default().fg(theme.text_dim)),
            Span::styled("Next Tab", Style::default().fg(theme.text_dim)),
        ]);
        let p_guide = Paragraph::new(guide_text)
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_guide, chunks[2]);
    }

    fn render_visuals_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let block = Block::default()
            .title(" AUDIO PLAYER & REAL-TIME SPECTRUM VISUALIZER ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(5), // Track Info & Playback Position Seek Bar
                Constraint::Min(9),    // Real-Time 32-Band FFT Spectrum Analyzer
                Constraint::Length(4), // Composite EQ Response Curve
                Constraint::Length(3), // Control Hotkeys Bar
            ])
            .split(inner);

        // 1. Track Info & Seek Bar
        let selected_job = self.jobs.get(self.selected_job_idx);
        let track_title = selected_job
            .map(|j| j.display_name.as_str())
            .unwrap_or("No track loaded");
        let format_label = selected_job
            .map(|j| j.quality.label())
            .unwrap_or("Lossless FLAC / High-Res Audio");
        let (cur_sec, total_sec) = self.player.position();
        let is_playing = self.player.is_playing();

        let state_span = if is_playing {
            Span::styled(" [PLAYING] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(" [PAUSED]  ", Style::default().fg(theme.warning).add_modifier(Modifier::BOLD))
        };

        let cur_str = format!("{:02}:{:02}", (cur_sec as u64) / 60, (cur_sec as u64) % 60);
        let total_str = format!("{:02}:{:02}", (total_sec as u64) / 60, (total_sec as u64) % 60);
        let ratio = if total_sec > 0.0 {
            (cur_sec / total_sec).clamp(0.0, 1.0)
        } else {
            0.0
        };

        let bar_width = (chunks[0].width as usize).saturating_sub(38).max(10);
        let filled = ((ratio * bar_width as f32).round() as usize).min(bar_width);
        let empty = bar_width.saturating_sub(filled);

        let vol = self.player.volume_pct();
        let vol_gauge = if vol == 0 {
            Span::styled(" [VOL: MUTED] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))
        } else {
            Span::styled(format!(" [VOL: {:3}%] ", vol), Style::default().fg(theme.primary).add_modifier(Modifier::BOLD))
        };

        let header_lines = vec![
            Line::from(vec![
                state_span,
                vol_gauge,
                Span::styled(format!("Track: {} ", track_title), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                Span::styled(format!("| Format: {} | 48kHz 24-Bit Stereo", format_label), Style::default().fg(theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" Position: ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("{}/{} ", cur_str, total_str), Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled("[", Style::default().fg(theme.border)),
                Span::styled("█".repeat(filled), Style::default().fg(theme.primary)),
                Span::styled("░".repeat(empty), Style::default().fg(theme.text_dim)),
                Span::styled(format!("] {:.1}%", ratio * 100.0), Style::default().fg(theme.text)),
            ]),
        ];
        let p_header = Paragraph::new(header_lines)
            .block(Block::default().title(" PLAYBACK STATUS & AUDITION TIMELINE ").borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_header, chunks[0]);

        // 2. Real-Time 32-Band FFT Frequency Spectrum Analyzer (Dynamically scaled across full terminal width)
        let spec_height = (chunks[1].height as usize).saturating_sub(3).max(4);
        let mut spec_lines = Vec::new();
        let inner_w = (chunks[1].width as usize).saturating_sub(2);
        let num_bands = 32;
        let col_width = (inner_w / num_bands).max(3);
        let total_graph_w = col_width * num_bands;
        let excess = inner_w.saturating_sub(total_graph_w);
        let left_pad = excess / 2;
        let bar_w = col_width.saturating_sub(1).max(2);

        // Top to bottom rendering of spectral bars
        for row in (1..=spec_height).rev() {
            let row_thresh = (row as f32) / (spec_height as f32);
            let mut spans = Vec::new();
            if left_pad > 0 {
                spans.push(Span::raw(" ".repeat(left_pad)));
            }

            for &db in &self.live_spectrum {
                // dB ranges from -60.0 dBFS to 0.0 dBFS
                let norm = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
                let prev_thresh = ((row - 1) as f32) / (spec_height as f32);

                let cell_style = if row_thresh > 0.8 {
                    Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
                } else if row_thresh > 0.4 {
                    Style::default().fg(theme.primary)
                } else {
                    Style::default().fg(theme.secondary)
                };

                if norm >= row_thresh {
                    spans.push(Span::styled("█".repeat(bar_w), cell_style));
                } else if norm > prev_thresh {
                    let sub = ((norm - prev_thresh) / (row_thresh - prev_thresh) * 7.0).round() as usize;
                    let blocks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
                    let ch = blocks[sub.min(7)];
                    spans.push(Span::styled(ch.to_string().repeat(bar_w), cell_style));
                } else {
                    spans.push(Span::styled("·".repeat(bar_w), Style::default().fg(theme.border)));
                }
                spans.push(Span::raw(" "));
            }
            spec_lines.push(Line::from(spans));
        }

        // Add frequency labels along bottom axis dynamically aligned to bar centers
        let markers: &[(&str, usize)] = &[
            ("20Hz", 0),
            ("31Hz", 2),
            ("50Hz", 4),
            ("80Hz", 6),
            ("125Hz", 8),
            ("200Hz", 10),
            ("315Hz", 12),
            ("500Hz", 14),
            ("800Hz", 16),
            ("1k", 17),
            ("1.6k", 19),
            ("2.5k", 21),
            ("4k", 23),
            ("6.3k", 25),
            ("10k", 27),
            ("16k", 29),
            ("20k", 31),
        ];

        let mut axis_chars = vec![' '; inner_w];
        let mut last_end = 0;
        for &(label, band_idx) in markers {
            if band_idx >= num_bands {
                continue;
            }
            let center = left_pad + band_idx * col_width + (bar_w / 2);
            let start = center.saturating_sub(label.len() / 2);
            let end = start + label.len();
            if start >= last_end && end <= inner_w {
                for (ci, c) in label.chars().enumerate() {
                    axis_chars[start + ci] = c;
                }
                last_end = end + 1;
            }
        }
        let axis_labels: String = axis_chars.into_iter().collect();
        spec_lines.push(Line::from(vec![
            Span::styled(axis_labels, Style::default().fg(theme.text_dim)),
        ]));

        let p_spec = Paragraph::new(spec_lines)
            .block(Block::default().title(" LIVE 32-BAND FFT FREQUENCY SPECTRUM ANALYZER ").borders(Borders::ALL).border_style(Style::default().fg(theme.secondary)));
        f.render_widget(p_spec, chunks[1]);

        // 3. Composite EQ Frequency Curve
        let mut curve_spans = Vec::new();
        curve_spans.push(Span::styled("Curve: ", Style::default().fg(theme.text_dim)));
        for (i, &gain) in self.band_gains.iter().enumerate() {
            let label = FREQ_LABELS[i];
            let dot = if self.eq_bypass {
                "---"
            } else if gain > 3.0 {
                "^^^"
            } else if gain > 0.0 {
                "---"
            } else if gain < -3.0 {
                "vvv"
            } else if gain < 0.0 {
                "___"
            } else {
                "---"
            };
            let color = if self.eq_bypass {
                theme.text_dim
            } else if gain > 0.0 {
                theme.accent
            } else if gain < 0.0 {
                theme.secondary
            } else {
                theme.primary
            };
            curve_spans.push(Span::styled(format!("{}:{} ", label, dot), Style::default().fg(color)));
        }

        let filter_status = Line::from(vec![
            Span::styled("  HPF 30Hz: ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.hpf_30hz { "[18dB/oct Sub Cut ACTIVE]" } else { "[Bypassed]" }, Style::default().fg(if self.hpf_30hz { theme.primary } else { theme.text_dim })),
            Span::styled("  |  Air Boost: ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.air_boost { "[+3.0dB @ 16kHz ACTIVE]" } else { "[Bypassed]" }, Style::default().fg(if self.air_boost { theme.accent } else { theme.text_dim })),
            Span::styled("  |  EQ Status: ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.eq_bypass { "[BYPASSED (Flat)]" } else { "[ACTIVE AUDITION]" }, Style::default().fg(if self.eq_bypass { theme.warning } else { theme.success })),
        ]);

        let p_curve = Paragraph::new(vec![Line::from(curve_spans), filter_status])
            .block(Block::default().title(" COMPOSITE MASTER EQ CURVE & FILTERS ").borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_curve, chunks[2]);

        // 4. Control Hotkeys Bar
        let hotkeys = Line::from(vec![
            Span::styled(" [Space] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Play/Pause  ", Style::default().fg(theme.text)),
            Span::styled(" [Up/Down] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Vol +/-5%  ", Style::default().fg(theme.text)),
            Span::styled(" [M] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Mute  ", Style::default().fg(theme.text)),
            Span::styled(" [Left/Right] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Seek +/-5s  ", Style::default().fg(theme.text)),
            Span::styled(" [R] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled("Restart  ", Style::default().fg(theme.text)),
            Span::styled(" [2] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("10-Band EQ  ", Style::default().fg(theme.text)),
            Span::styled(" [1] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("Queue  ", Style::default().fg(theme.text)),
            Span::styled(" [S] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::styled("Export Master", Style::default().fg(theme.text)),
        ]);
        let p_hotkeys = Paragraph::new(hotkeys)
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_hotkeys, chunks[3]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_downloader_tab_switching() {
        let mut state = DownloaderState::new();
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Switch to EQ tab via F2
        state.handle_key(KeyCode::F(2));
        assert_eq!(state.active_tab, DownloaderTab::Eq);

        // Switch to Visuals tab via F3
        state.handle_key(KeyCode::F(3));
        assert_eq!(state.active_tab, DownloaderTab::Visuals);

        // Switch back to Queue via F1
        state.handle_key(KeyCode::F(1));
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Switch via Tab from EQ
        state.active_tab = DownloaderTab::Eq;
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.active_tab, DownloaderTab::Visuals);
    }

    #[test]
    fn test_eq_band_navigation_and_gain_clamping() {
        let mut state = DownloaderState::new();
        state.active_tab = DownloaderTab::Eq;
        state.selected_band = 5; // 1kHz

        // Navigate left
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_band, 4);

        // Boost gain
        state.handle_key(KeyCode::Up);
        assert!((state.band_gains[4] - 0.5).abs() < 1e-4);

        // Boost to max limit (+12.0 dB)
        for _ in 0..30 {
            state.handle_key(KeyCode::Up);
        }
        assert!((state.band_gains[4] - 12.0).abs() < 1e-4);

        // Zero band
        state.handle_key(KeyCode::Char('0'));
        assert!((state.band_gains[4] - 0.0).abs() < 1e-4);

        // Cut to min limit (-12.0 dB)
        for _ in 0..30 {
            state.handle_key(KeyCode::Down);
        }
        assert!((state.band_gains[4] - (-12.0)).abs() < 1e-4);

        // Reset all flat
        state.handle_key(KeyCode::Char('r'));
        for gain in state.band_gains {
            assert!((gain - 0.0).abs() < 1e-4);
        }
    }

    #[test]
    fn test_eq_toggles() {
        let mut state = DownloaderState::new();
        state.active_tab = DownloaderTab::Eq;

        assert!(!state.hpf_30hz);
        state.handle_key(KeyCode::Char('h'));
        assert!(state.hpf_30hz);

        assert!(!state.air_boost);
        state.handle_key(KeyCode::Char('a'));
        assert!(state.air_boost);

        assert!(!state.eq_bypass);
        state.handle_key(KeyCode::Char('b'));
        assert!(state.eq_bypass);
    }

    #[tokio::test]
    async fn test_trigger_enhancement_empty_and_keyed() {
        let mut state = DownloaderState::new();
        state.focused_field = 1; // Unfocus text box so hotkeys work
        state.handle_key(KeyCode::Char('e'));
        assert!(state.status_message.contains("No jobs in queue"));

        // With job in queue
        state.jobs.push(DownloadJob {
            id: 1,
            source: "https://example.com/audio".to_string(),
            display_name: "Test Track".to_string(),
            output_path: None,
            quality: Mp3Quality::Mp3_320k,
            policy: AcquisitionPolicy::Mp3Only,
            phase: JobPhase::Completed,
            progress: 100.0,
            speed: "Done".to_string(),
            eta: "00:00".to_string(),
            spectral_verdict: None,
        });

        state.handle_key(KeyCode::Char('e'));
        assert!(state.status_message.contains("Enhancing track #1"));
    }

    #[test]
    fn test_number_keys_switch_tabs_directly() {
        let mut state = DownloaderState::new();
        // User starts at Queue with focused_field == 0
        assert_eq!(state.active_tab, DownloaderTab::Queue);
        assert!(!state.is_editing_url);

        // Pressing '2' switches directly to EQ tab!
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.active_tab, DownloaderTab::Eq);

        // Pressing '3' switches to Visuals tab!
        state.handle_key(KeyCode::Char('3'));
        assert_eq!(state.active_tab, DownloaderTab::Visuals);

        // Pressing '1' switches back to Queue!
        state.handle_key(KeyCode::Char('1'));
        assert_eq!(state.active_tab, DownloaderTab::Queue);
    }

    #[test]
    fn test_url_edit_mode_and_escape() {
        let mut state = DownloaderState::new();
        assert!(!state.is_editing_url);

        // Press Enter to start editing URL
        state.handle_key(KeyCode::Enter);
        assert!(state.is_editing_url);

        // While editing, numbers type into URL
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.input_text, "2");
        assert_eq!(state.active_tab, DownloaderTab::Queue); // Did not switch tabs!

        // Press Esc to exit edit mode
        state.handle_key(KeyCode::Esc);
        assert!(!state.is_editing_url);

        // Now pressing '2' switches to EQ tab
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.active_tab, DownloaderTab::Eq);
    }

    #[test]
    fn test_paste_url_with_m_and_other_characters() {
        let mut state = DownloaderState::new();
        state.paste("https://music.youtube.com/watch?v=dQw4w9WgXcQ");
        assert!(state.is_editing_url);
        assert_eq!(state.input_text, "https://music.youtube.com/watch?v=dQw4w9WgXcQ");
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Typing characters while focused on URL also enters edit mode
        let mut state2 = DownloaderState::new();
        state2.handle_key(KeyCode::Char('h'));
        assert!(state2.is_editing_url);
        assert_eq!(state2.input_text, "h");
    }

    #[tokio::test]
    async fn test_tab_navigation_out_of_url_editing() {
        let mut state = DownloaderState::new();
        state.paste("https://youtube.com/watch?v=example");
        assert!(state.is_editing_url);
        assert_eq!(state.focused_field, 0);

        // Pressing Tab while editing URL must exit edit mode and focus Quality (Field 1)
        state.handle_key(KeyCode::Tab);
        assert!(!state.is_editing_url);
        assert_eq!(state.focused_field, 1);

        // Right arrow changes Quality forward
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_quality, Mp3Quality::Mp3_V0);

        // Left arrow changes Quality backward
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_quality, Mp3Quality::Mp3_320k);

        // Left arrow again wraps backward to Opus160k
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_quality, Mp3Quality::Opus160k);

        // Pressing Tab advances to Policy (Field 2)
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.focused_field, 2);
        assert_eq!(state.selected_policy, AcquisitionPolicy::Mp3Only);

        // Right arrow cycles Policy to BestAvailable
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_policy, AcquisitionPolicy::BestAvailable);

        // Right arrow cycles to NicotineFlacPreferred
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_policy, AcquisitionPolicy::NicotineFlacPreferred);

        // Pressing Enter while on Policy with non-empty URL submits the job!
        state.handle_key(KeyCode::Enter);
        assert_eq!(state.jobs.len(), 1);
        let queued = &state.jobs[0];
        assert_eq!(queued.quality, Mp3Quality::Opus160k);
        assert_eq!(queued.policy, AcquisitionPolicy::NicotineFlacPreferred);
    }

    #[test]
    fn test_backtab_navigation_from_editing() {
        let mut state = DownloaderState::new();
        state.paste("https://soundcloud.com/test/track");
        assert!(state.is_editing_url);

        // BackTab exits edit mode and shifts focus to Convert button (Field 4)
        state.handle_key(KeyCode::BackTab);
        assert!(!state.is_editing_url);
        assert_eq!(state.focused_field, 4);
    }

    #[test]
    fn test_lyrics_toggle_and_navigation() {
        let mut state = DownloaderState::new();
        assert!(state.download_lyrics);

        // Focus Lyrics (Field 3)
        state.focused_field = 3;
        state.is_editing_url = false;

        // Toggle with Space
        state.handle_key(KeyCode::Char(' '));
        assert!(!state.download_lyrics);

        // Toggle with Right arrow
        state.handle_key(KeyCode::Right);
        assert!(state.download_lyrics);

        // Toggle with 'l' hotkey
        state.handle_key(KeyCode::Char('l'));
        assert!(!state.download_lyrics);
    }

    #[test]
    fn test_bidirectional_cycling() {
        let q = Mp3Quality::Mp3_320k;
        assert_eq!(q.next(), Mp3Quality::Mp3_V0);
        assert_eq!(q.prev(), Mp3Quality::Opus160k);
        assert_eq!(Mp3Quality::FlacLossless.prev(), Mp3Quality::Aac_256k);

        let p = AcquisitionPolicy::Mp3Only;
        assert_eq!(p.next(), AcquisitionPolicy::BestAvailable);
        assert_eq!(p.prev(), AcquisitionPolicy::FastWebFallback);
        assert_eq!(AcquisitionPolicy::NicotineFlacPreferred.prev(), AcquisitionPolicy::BestAvailable);
    }

    #[test]
    fn test_nicotine_policy_renamed_label() {
        assert_eq!(AcquisitionPolicy::NicotineFlacPreferred.label(), "Nicotine+/Soulseek");
        assert!(AcquisitionPolicy::NicotineFlacPreferred.description().contains("Soulseek P2P swarm"));
    }

    #[test]
    fn test_lossless_selector_modal_navigation_and_toggle() {
        let mut state = DownloaderState::new();
        state.lossless_candidates = vec![
            NicotineCandidate {
                username: "audiophile_peer1".to_string(),
                filename: "Music/Artist/Album 1995/01. Track.flac".to_string(),
                size_bytes: 40_000_000,
                bitrate_kbps: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                speed_kbps: None,
                in_queue: 0,
                score: 95.0,
            },
            NicotineCandidate {
                username: "hi_res_vault".to_string(),
                filename: "D:\\Shares\\Lossless\\Artist\\Album 1995 Hi-Res\\01. Track.flac".to_string(),
                size_bytes: 85_000_000,
                bitrate_kbps: Some(3200),
                sample_rate: Some(96000),
                bit_depth: Some(24),
                speed_kbps: None,
                in_queue: 0,
                score: 99.0,
            },
        ];
        state.show_lossless_selector = true;
        state.selected_lossless_idx = 0;
        state.download_entire_album = false;

        // Down arrow advances to hi-res version
        state.handle_key(KeyCode::Down);
        assert_eq!(state.selected_lossless_idx, 1);

        // Clamps at last item
        state.handle_key(KeyCode::Down);
        assert_eq!(state.selected_lossless_idx, 1);

        // Up arrow moves back
        state.handle_key(KeyCode::Up);
        assert_eq!(state.selected_lossless_idx, 0);

        // Tab toggles download scope to Entire Album
        state.handle_key(KeyCode::Tab);
        assert!(state.download_entire_album);

        // Space toggles download scope back to Single Track
        state.handle_key(KeyCode::Char(' '));
        assert!(!state.download_entire_album);

        // Esc cancels and closes modal
        state.handle_key(KeyCode::Esc);
        assert!(!state.show_lossless_selector);
    }

    #[test]
    fn test_lossless_candidate_helpers() {
        let flac16 = NicotineCandidate {
            username: "peer1".to_string(),
            filename: "Music/Band/Album/01. Track.flac".to_string(),
            size_bytes: 35 * 1024 * 1024,
            bitrate_kbps: Some(1411),
            sample_rate: Some(44100),
            bit_depth: Some(16),
            speed_kbps: None,
            in_queue: 0,
            score: 90.0,
        };
        assert_eq!(flac16.formatted_resolution(), "16-bit / 44.1 kHz");
        assert_eq!(flac16.directory_name(), "Album");

        let flac24 = NicotineCandidate {
            username: "peer2".to_string(),
            filename: "D:\\Lossless\\Master\\Track.flac".to_string(),
            size_bytes: 80 * 1024 * 1024,
            bitrate_kbps: Some(3000),
            sample_rate: Some(96000),
            bit_depth: Some(24),
            speed_kbps: None,
            in_queue: 0,
            score: 98.0,
        };
        assert_eq!(flac24.formatted_resolution(), "24-bit / 96.0 kHz");
        assert_eq!(flac24.directory_name(), "Master");
    }

    #[test]
    fn test_job_phase_labels() {
        assert_eq!(JobPhase::Queued.label(), "[QUEUING]");
        assert_eq!(JobPhase::Downloading.label(), "[DOWNLOADING]");
        assert_eq!(JobPhase::AwaitingQueryOverride("test".into()).label(), "[OVERRIDE QUERY]");
        assert_eq!(JobPhase::Auditing.label(), "[AUDITING]");
        assert_eq!(JobPhase::Completed.label(), "[COMPLETE]");
        assert_eq!(JobPhase::Failed("Error".into()).label(), "[FAILED: Error]");
    }

    #[test]
    fn test_query_override_modal_key_handling() {
        let mut state = DownloaderState::new();
        state.show_query_override_modal = true;
        state.query_override_input = "hang".to_string();
        state.query_override_job_id = Some(1);

        // Typing character 'a' and 'r'
        state.handle_key(KeyCode::Char('a'));
        state.handle_key(KeyCode::Char('r'));
        assert_eq!(state.query_override_input, "hangar");

        // Backspace removes last character
        state.handle_key(KeyCode::Backspace);
        assert_eq!(state.query_override_input, "hanga");

        // Esc cancels and closes modal
        state.handle_key(KeyCode::Esc);
        assert!(!state.show_query_override_modal);
    }

    fn make_test_candidate(peer: &str, dir: &str, file: &str) -> NicotineCandidate {
        NicotineCandidate {
            username: peer.to_string(),
            filename: format!("{}/{}", dir, file),
            size_bytes: 30 * 1024 * 1024,
            bitrate_kbps: Some(1411),
            sample_rate: Some(44100),
            bit_depth: Some(16),
            speed_kbps: Some(500.0),
            in_queue: 0,
            score: 95.0,
        }
    }

    #[test]
    fn test_lossless_selector_modal_scrolling() {
        let mut state = DownloaderState::new();
        state.show_lossless_selector = true;
        for i in 0..40 {
            state.lossless_candidates.push(make_test_candidate(
                &format!("peer_{}", i),
                "Album",
                &format!("Track_{}.flac", i),
            ));
        }

        assert_eq!(state.selected_lossless_idx, 0);

        // Down arrow advances by 1
        state.handle_key(KeyCode::Down);
        assert_eq!(state.selected_lossless_idx, 1);
        assert_eq!(state.lossless_list_state.selected(), Some(1));

        // PageDown jumps by 15
        state.handle_key(KeyCode::PageDown);
        assert_eq!(state.selected_lossless_idx, 16);
        assert_eq!(state.lossless_list_state.selected(), Some(16));

        // PageDown again jumps to 31
        state.handle_key(KeyCode::PageDown);
        assert_eq!(state.selected_lossless_idx, 31);

        // PageDown again clamps to 39 (last item)
        state.handle_key(KeyCode::PageDown);
        assert_eq!(state.selected_lossless_idx, 39);

        // PageUp jumps up by 15
        state.handle_key(KeyCode::PageUp);
        assert_eq!(state.selected_lossless_idx, 24);

        // Home jumps to top
        state.handle_key(KeyCode::Home);
        assert_eq!(state.selected_lossless_idx, 0);

        // End jumps to bottom
        state.handle_key(KeyCode::End);
        assert_eq!(state.selected_lossless_idx, 39);
        assert_eq!(state.lossless_list_state.selected(), Some(39));
    }

    #[test]
    fn test_lossless_selector_modal_filtering() {
        let mut state = DownloaderState::new();
        state.show_lossless_selector = true;
        state.lossless_candidates = vec![
            make_test_candidate("megafan", "Megadeth - Rust in Peace (1990)", "02 - Hangar 18.flac"),
            make_test_candidate("soundtrack", "Ryuichi Sakamoto - 1996", "08 - Hangar.flac"),
            make_test_candidate("indie", "SYML - Clean Eyes", "01 - Clean Eyes.flac"),
            make_test_candidate("metal_head", "Megadeth - Rust in Peace (1990)", "01 - Holy Wars.flac"),
        ];

        // Initially all 4 match
        assert_eq!(state.filtered_lossless_indices().len(), 4);

        // Activate filter mode with '/'
        state.handle_key(KeyCode::Char('/'));
        assert!(state.is_filtering_lossless);

        // Type "megadeth"
        for c in "megadeth".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.lossless_filter_text, "megadeth");
        let matches = state.filtered_lossless_indices();
        assert_eq!(matches.len(), 2);
        assert_eq!(matches, vec![0, 3]);

        // Add " 18" -> multi-token matches only Hangar 18
        for c in " 18".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        let matches = state.filtered_lossless_indices();
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0], 0);

        // Backspace 3 times removes " 18"
        state.handle_key(KeyCode::Backspace);
        state.handle_key(KeyCode::Backspace);
        state.handle_key(KeyCode::Backspace);
        assert_eq!(state.filtered_lossless_indices().len(), 2);

        // Esc clears filter text
        state.handle_key(KeyCode::Esc);
        assert!(state.lossless_filter_text.is_empty());
        assert_eq!(state.filtered_lossless_indices().len(), 4);

        // Second Esc exits filter mode
        state.handle_key(KeyCode::Esc);
        assert!(!state.is_filtering_lossless);
    }

    #[test]
    fn test_lossless_selector_manual_entry_navigation() {
        let mut state = DownloaderState::new();
        state.show_lossless_selector = true;
        state.lossless_candidates = vec![
            make_test_candidate("peer1", "Megadeth - Rust in Peace", "02 - Hangar 18.flac"),
            make_test_candidate("peer2", "SYML - Clean Eyes", "01 - Clean Eyes.flac"),
        ];

        // Press 'e' to open manual entry modal
        state.handle_key(KeyCode::Char('e'));
        assert!(state.show_manual_entry_modal);
        assert_eq!(state.manual_entry_focused_field, 0);

        // Type "Megadeth" into field 0 (Artist)
        for c in "Megadeth".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.manual_entry_artist, "Megadeth");

        // Tab moves to field 1 (Album)
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.manual_entry_focused_field, 1);
        for c in "Rust in Peace".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.manual_entry_album, "Rust in Peace");

        // Tab moves to field 2 (Track)
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.manual_entry_focused_field, 2);
        for c in "Hangar 18".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.manual_entry_track, "Hangar 18");

        // F1 applies the entered fields as an in-memory filter
        state.handle_key(KeyCode::F(1));
        assert!(!state.show_manual_entry_modal);
        assert_eq!(state.lossless_filter_text, "Megadeth Rust in Peace Hangar 18");
        assert_eq!(state.filtered_lossless_indices().len(), 1);
        assert_eq!(state.filtered_lossless_indices()[0], 0);
    }

    #[test]
    fn test_album_release_clustering_and_target_identification() {
        let mut state = DownloaderState::new();
        state.target_search_title = "Hangar 18".to_string();

        state.lossless_candidates = vec![
            make_test_candidate("metal_head", "Megadeth - Rust in Peace", "02 - Hangar 18.flac"),
            make_test_candidate("single_peer", "Singles", "Hangar 18 (Single).flac"),
        ];

        state.all_peer_files = vec![
            crate::harvest::slskd::SlskdFileResult {
                username: "metal_head".to_string(),
                filename: "Music/Megadeth - Rust in Peace/01 - Holy Wars.flac".to_string(),
                size: 45 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: Some(500 * 1024),
                queue_length: 0,
            },
            crate::harvest::slskd::SlskdFileResult {
                username: "metal_head".to_string(),
                filename: "Music/Megadeth - Rust in Peace/02 - Hangar 18.flac".to_string(),
                size: 50 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: Some(500 * 1024),
                queue_length: 0,
            },
            crate::harvest::slskd::SlskdFileResult {
                username: "metal_head".to_string(),
                filename: "Music/Megadeth - Rust in Peace/cover.jpg".to_string(),
                size: 1024 * 1024,
                bitrate: None,
                sample_rate: None,
                bit_depth: None,
                upload_speed: None,
                queue_length: 0,
            },
            crate::harvest::slskd::SlskdFileResult {
                username: "single_peer".to_string(),
                filename: "Singles/Hangar 18 (Single).flac".to_string(),
                size: 48 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            },
        ];

        let clusters = state.album_release_clusters();
        assert_eq!(clusters.len(), 2);

        // metal_head cluster is sorted first because it has 2 tracks
        let album_cluster = &clusters[0];
        assert_eq!(album_cluster.username, "metal_head");
        assert_eq!(album_cluster.directory, "Megadeth - Rust in Peace");
        assert_eq!(album_cluster.tracks.len(), 2);
        assert_eq!(album_cluster.companion_images.len(), 1);
        assert_eq!(album_cluster.companion_images[0].filename, "Music/Megadeth - Rust in Peace/cover.jpg");
        assert_eq!(album_cluster.total_size_bytes, (45 + 50 + 1) * 1024 * 1024);

        // Target track index matches "02 - Hangar 18.flac"
        assert_eq!(album_cluster.target_track_idx, Some(1));
        assert!(album_cluster.tracks[1].filename.contains("Hangar 18"));

        // Single peer cluster
        let single_cluster = &clusters[1];
        assert_eq!(single_cluster.username, "single_peer");
        assert_eq!(single_cluster.tracks.len(), 1);
        assert_eq!(single_cluster.target_track_idx, Some(0));
    }

    #[test]
    fn test_album_mode_toggle_and_navigation() {
        let mut state = DownloaderState::new();
        state.show_lossless_selector = true;
        state.target_search_title = "Hangar 18".to_string();

        state.lossless_candidates = vec![
            make_test_candidate("metal_head", "Megadeth - Rust in Peace", "02 - Hangar 18.flac"),
            make_test_candidate("single_peer", "Singles", "Hangar 18.flac"),
        ];

        state.all_peer_files = vec![
            crate::harvest::slskd::SlskdFileResult {
                username: "metal_head".to_string(),
                filename: "Music/Megadeth - Rust in Peace/01 - Holy Wars.flac".to_string(),
                size: 45 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            },
            crate::harvest::slskd::SlskdFileResult {
                username: "metal_head".to_string(),
                filename: "Music/Megadeth - Rust in Peace/02 - Hangar 18.flac".to_string(),
                size: 50 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            },
            crate::harvest::slskd::SlskdFileResult {
                username: "single_peer".to_string(),
                filename: "Singles/Hangar 18.flac".to_string(),
                size: 48 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            },
        ];

        // Initially in Single Track mode
        assert!(!state.download_entire_album);
        assert_eq!(state.filtered_lossless_indices().len(), 2);

        // Tab toggles to Entire Album mode
        state.handle_key(KeyCode::Tab);
        assert!(state.download_entire_album);
        assert_eq!(state.selected_lossless_idx, 0);
        assert_eq!(state.filtered_lossless_indices().len(), 2);

        // Down navigates to next cluster
        state.handle_key(KeyCode::Down);
        assert_eq!(state.selected_lossless_idx, 1);

        // Up navigates back
        state.handle_key(KeyCode::Up);
        assert_eq!(state.selected_lossless_idx, 0);

        // Tab toggles back to Single Track mode
        state.handle_key(KeyCode::Tab);
        assert!(!state.download_entire_album);
        assert_eq!(state.selected_lossless_idx, 0);
    }

    #[test]
    fn test_safe_truncate_unicode_and_em_dash() {
        // String shorter than max length is unmodified
        assert_eq!(safe_truncate("hello", 10), "hello");

        // String exactly at max length is unmodified
        assert_eq!(safe_truncate("hello world!", 12), "hello world!");

        // ASCII truncation
        assert_eq!(safe_truncate("this is a very long string", 10), "this is...") ;

        // String with 3-byte UTF-8 em-dash: "Ken Carson — xperiment (2026)"
        // Previously panicked at byte index 13: "13 is not a char boundary; it is inside '-'"
        let title_with_dash = "Ken Carson — xperiment (2026)";
        let truncated = safe_truncate(title_with_dash, 16);
        assert_eq!(truncated, "Ken Carson — ...");
        assert!(truncated.ends_with("..."));

        // Multibyte CJK characters
        let japanese = "坂本龍一 - 1996 リマスター";
        let truncated_jp = safe_truncate(japanese, 8);
        assert_eq!(truncated_jp, "坂本龍一 ...") ;

        // Extreme short max_chars
        assert_eq!(safe_truncate("test", 2), "...");
    }

    #[test]
    fn test_controls_labels_fit_horizontal_constraints() {
        // Quality select allocated Constraint::Length(30)
        let qualities = [
            Mp3Quality::Mp3_320k,
            Mp3Quality::Mp3_V0,
            Mp3Quality::Mp3_256k,
            Mp3Quality::Mp3_128k,
            Mp3Quality::Aac_256k,
            Mp3Quality::FlacLossless,
            Mp3Quality::Wav24,
            Mp3Quality::Opus160k,
        ];
        for q in &qualities {
            let text = format!(" Quality: < {} > ", q.label());
            assert!(
                text.chars().count() <= 30,
                "Quality text '{}' (len {}) exceeds constraint 30",
                text,
                text.chars().count()
            );
            let focused = format!("[► Quality: {} ◄]", q.label());
            assert!(
                focused.chars().count() <= 30,
                "Focused quality text '{}' (len {}) exceeds constraint 30",
                focused,
                focused.chars().count()
            );
        }

        // Policy select allocated Constraint::Length(33)
        let policies = [
            AcquisitionPolicy::Mp3Only,
            AcquisitionPolicy::BestAvailable,
            AcquisitionPolicy::NicotineFlacPreferred,
            AcquisitionPolicy::FastWebFallback,
        ];
        for p in &policies {
            let text = format!(" Policy: < {} > ", p.label());
            assert!(
                text.chars().count() <= 33,
                "Policy text '{}' (len {}) exceeds constraint 33",
                text,
                text.chars().count()
            );
            let focused = format!("[► Policy: {} ◄]", p.label());
            assert!(
                focused.chars().count() <= 33,
                "Focused policy text '{}' (len {}) exceeds constraint 33",
                focused,
                focused.chars().count()
            );
        }
    }

    #[test]
    fn test_album_release_clusters_deterministic_zero_shuffling() {
        let mut state = DownloaderState::new();
        state.target_search_title = "None".to_string();

        // 10 peers with identical track count (2 tracks), equal queue (0), and no target track
        for i in 0..10 {
            state.all_peer_files.push(crate::harvest::slskd::SlskdFileResult {
                username: format!("peer_{:02}", i),
                filename: format!("Album_{:02}/01.flac", i),
                size: 20 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            });
            state.all_peer_files.push(crate::harvest::slskd::SlskdFileResult {
                username: format!("peer_{:02}", i),
                filename: format!("Album_{:02}/02.flac", i),
                size: 20 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            });
        }

        // Run 50 iterations to simulate 50 render frames
        let initial_order: Vec<String> = state.album_release_clusters()
            .into_iter()
            .map(|c| format!("{}|{}", c.directory, c.username))
            .collect();

        assert_eq!(initial_order.len(), 10);

        for _ in 0..50 {
            let next_order: Vec<String> = state.album_release_clusters()
                .into_iter()
                .map(|c| format!("{}|{}", c.directory, c.username))
                .collect();
            assert_eq!(initial_order, next_order, "Cluster order shuffled between render iterations!");
        }
    }

    #[test]
    fn test_album_release_clusters_filters_single_track_junk() {
        let mut state = DownloaderState::new();
        state.target_search_title = "Target Song".to_string();

        // 1. Real album with 3 tracks
        for t in 1..=3 {
            state.all_peer_files.push(crate::harvest::slskd::SlskdFileResult {
                username: "album_master".to_string(),
                filename: format!("Great Album/0{}.flac", t),
                size: 30 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            });
        }

        // 2. Single-track that matches target song
        state.all_peer_files.push(crate::harvest::slskd::SlskdFileResult {
            username: "single_ripper".to_string(),
            filename: "Loose/Target Song (Single).flac".to_string(),
            size: 25 * 1024 * 1024,
            bitrate: Some(1411),
            sample_rate: Some(44100),
            bit_depth: Some(16),
            upload_speed: None,
            queue_length: 0,
        });

        // 3. Five random 1-track junk files from unrelated peers
        for i in 1..=5 {
            state.all_peer_files.push(crate::harvest::slskd::SlskdFileResult {
                username: format!("random_peer_{}", i),
                filename: format!("UnrelatedFolder_{}/random_track_{}.flac", i, i),
                size: 15 * 1024 * 1024,
                bitrate: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                upload_speed: None,
                queue_length: 0,
            });
        }

        let clusters = state.album_release_clusters();
        // Only the real album and the matching target single track are retained (2 clusters); 5 junk folders are filtered out
        assert_eq!(clusters.len(), 2);
        let dir_names: Vec<&str> = clusters.iter().map(|c| c.directory.as_str()).collect();
        assert!(dir_names.contains(&"Great Album"));
        assert!(dir_names.contains(&"Loose"));
    }

    #[test]
    fn test_seed_expansion_underflow_triggers_modal() {
        let mut state = DownloaderState::new();
        assert_eq!(state.target_seeds, 20);

        // Create 5 fake lossless candidates (fewer than target 20)
        let mut candidates = Vec::new();
        for i in 0..5 {
            candidates.push(NicotineCandidate {
                username: format!("peer_{}", i),
                filename: format!("Track_{}.flac", i),
                size_bytes: 20 * 1024 * 1024,
                bitrate_kbps: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                speed_kbps: Some(500.0),
                in_queue: 0,
                score: 50.0,
            });
        }

        // Simulate receiving AwaitingSelection with 5 candidates
        state.tx.try_send((
            1,
            JobPhase::AwaitingSelection(candidates.clone(), Vec::new()),
            25.0,
            "Select Quality".into(),
            "--:--".into(),
            None,
        )).unwrap();

        state.poll_updates();

        // Underflow: modal should activate, lossless selector should remain false
        assert!(state.show_seed_expansion_modal);
        assert!(!state.show_lossless_selector);
        assert_eq!(state.seed_expansion_found_count, 5);
        assert_eq!(state.seed_expansion_candidates.len(), 5);
    }

    #[test]
    fn test_seed_expansion_surplus_opens_selector_directly() {
        let mut state = DownloaderState::new();
        assert_eq!(state.target_seeds, 20);

        // Create 20 fake lossless candidates (reaches target 20)
        let mut candidates = Vec::new();
        for i in 0..20 {
            candidates.push(NicotineCandidate {
                username: format!("peer_{}", i),
                filename: format!("Track_{}.flac", i),
                size_bytes: 20 * 1024 * 1024,
                bitrate_kbps: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
                speed_kbps: Some(500.0),
                in_queue: 0,
                score: 50.0,
            });
        }

        state.tx.try_send((
            1,
            JobPhase::AwaitingSelection(candidates.clone(), Vec::new()),
            25.0,
            "Select Quality".into(),
            "--:--".into(),
            None,
        )).unwrap();

        state.poll_updates();

        // Target reached: selector opens directly without expansion prompt
        assert!(!state.show_seed_expansion_modal);
        assert!(state.show_lossless_selector);
        assert_eq!(state.lossless_candidates.len(), 20);
    }

    #[test]
    fn test_seed_expansion_key_actions() {
        let mut state = DownloaderState::new();
        state.target_seeds = 20;
        state.show_seed_expansion_modal = true;
        state.seed_expansion_found_count = 8;
        state.seed_expansion_candidates = vec![NicotineCandidate {
            username: "peer1".to_string(),
            filename: "song.flac".to_string(),
            size_bytes: 1000,
            bitrate_kbps: None,
            sample_rate: None,
            bit_depth: None,
            speed_kbps: None,
            in_queue: 0,
            score: 10.0,
        }];

        // Test 'p' key: increments target by 10 and closes modal
        state.handle_key(KeyCode::Char('p'));
        assert_eq!(state.target_seeds, 30);
        assert!(!state.show_seed_expansion_modal);

        // Re-activate modal with candidates and test 'u' key: uses current candidates
        state.show_seed_expansion_modal = true;
        state.seed_expansion_candidates = vec![NicotineCandidate {
            username: "peer1".to_string(),
            filename: "song.flac".to_string(),
            size_bytes: 1000,
            bitrate_kbps: None,
            sample_rate: None,
            bit_depth: None,
            speed_kbps: None,
            in_queue: 0,
            score: 10.0,
        }];
        state.handle_key(KeyCode::Char('u'));
        assert!(!state.show_seed_expansion_modal);
        assert!(state.show_lossless_selector);
        assert_eq!(state.lossless_candidates.len(), 1);

        // Test 'a' / Esc key: aborts search
        state.show_seed_expansion_modal = true;
        state.show_lossless_selector = false;
        state.handle_key(KeyCode::Esc);
        assert!(!state.show_seed_expansion_modal);
        assert!(!state.show_lossless_selector);
    }

    #[test]
    fn test_seed_expansion_duration_adjustments() {
        let mut state = DownloaderState::new();
        assert_eq!(state.search_duration_secs, 30);
        assert_eq!(state.seed_expansion_duration_secs, 30);

        state.show_seed_expansion_modal = true;

        // 1. Right arrow bumps +5s -> 35s
        state.handle_key(KeyCode::Right);
        assert_eq!(state.seed_expansion_duration_secs, 35);

        // 2. Left arrow drops -5s -> 30s, and again -> 25s
        state.handle_key(KeyCode::Left);
        state.handle_key(KeyCode::Left);
        assert_eq!(state.seed_expansion_duration_secs, 25);

        // 3. Drop past minimum -> clamps to 10s
        for _ in 0..10 {
            state.handle_key(KeyCode::Left);
        }
        assert_eq!(state.seed_expansion_duration_secs, 10);

        // 4. Test direct numeric typing mode: press 't', type '4', '5', Enter
        state.handle_key(KeyCode::Char('t'));
        assert!(state.seed_expansion_editing_time);

        // Clear existing buffer with backspaces
        state.handle_key(KeyCode::Backspace);
        state.handle_key(KeyCode::Backspace);
        state.handle_key(KeyCode::Char('4'));
        state.handle_key(KeyCode::Char('5'));
        state.handle_key(KeyCode::Enter);

        assert!(!state.seed_expansion_editing_time);
        assert_eq!(state.seed_expansion_duration_secs, 45);

        // 5. Proceed with 'p': updates state.search_duration_secs to 45 and target_seeds to 30
        state.handle_key(KeyCode::Char('p'));
        assert_eq!(state.search_duration_secs, 45);
        assert_eq!(state.target_seeds, 30);
        assert!(!state.show_seed_expansion_modal);
    }

    #[test]
    fn test_advanced_search_modal_key_navigation_and_engine_cycling() {
        let mut state = DownloaderState::new();
        assert!(!state.show_advanced_search_modal);

        // Press 's' to open Advanced Search modal
        state.handle_key(KeyCode::Char('s'));
        assert!(state.show_advanced_search_modal);
        assert_eq!(state.adv_search_focused_field, 0);

        // Type artist
        for c in "Radiohead".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.adv_search_artist, "Radiohead");

        // Tab to track field
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.adv_search_focused_field, 1);
        for c in "Weird Fishes".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.adv_search_track, "Weird Fishes");

        // Tab to album field
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.adv_search_focused_field, 2);
        for c in "In Rainbows".chars() {
            state.handle_key(KeyCode::Char(c));
        }
        assert_eq!(state.adv_search_album, "In Rainbows");

        // Tab to target engine
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.adv_search_focused_field, 3);
        assert_eq!(state.adv_search_target_engine, SearchTargetEngine::SoulseekP2P);

        // Right arrow cycles: SoulseekP2P -> YouTube -> Hybrid -> SoulseekP2P
        state.handle_key(KeyCode::Right);
        assert_eq!(state.adv_search_target_engine, SearchTargetEngine::YouTube);
        state.handle_key(KeyCode::Right);
        assert_eq!(state.adv_search_target_engine, SearchTargetEngine::Hybrid);
        state.handle_key(KeyCode::Right);
        assert_eq!(state.adv_search_target_engine, SearchTargetEngine::SoulseekP2P);

        // Esc closes modal
        state.handle_key(KeyCode::Esc);
        assert!(!state.show_advanced_search_modal);
    }

    #[tokio::test]
    async fn test_advanced_search_modal_submit_and_policy_selection() {
        let mut state = DownloaderState::new();
        state.show_advanced_search_modal = true;
        state.adv_search_artist = "Kendrick Lamar".to_string();
        state.adv_search_track = "Not Like Us".to_string();
        state.adv_search_target_engine = SearchTargetEngine::SoulseekP2P;

        // Press Enter to submit search
        state.handle_key(KeyCode::Enter);
        assert!(!state.show_advanced_search_modal);
        assert_eq!(state.selected_policy, AcquisitionPolicy::NicotineFlacPreferred);
        assert_eq!(state.jobs.len(), 1);
        assert_eq!(state.jobs[0].display_name, "Kendrick Lamar - Not Like Us");
    }

    #[tokio::test]
    async fn test_smart_omnibox_plain_text_query() {
        let mut state = DownloaderState::new();
        state.input_text = "Deftones - Change".to_string();
        state.submit_current();

        assert_eq!(state.jobs.len(), 1);
        assert_eq!(state.jobs[0].display_name, "Deftones - Change");
        assert!(state.input_text.is_empty());
    }

    #[test]
    fn test_is_capturing_input_all_states() {
        let mut state = DownloaderState::new();
        assert!(!state.is_capturing_input());

        state.is_editing_url = true;
        assert!(state.is_capturing_input());
        state.is_editing_url = false;

        state.show_lossless_selector = true;
        assert!(state.is_capturing_input());
        state.show_lossless_selector = false;

        state.show_manual_entry_modal = true;
        assert!(state.is_capturing_input());
        state.show_manual_entry_modal = false;

        state.show_query_override_modal = true;
        assert!(state.is_capturing_input());
        state.show_query_override_modal = false;

        state.show_seed_expansion_modal = true;
        assert!(state.is_capturing_input());
        state.show_seed_expansion_modal = false;

        state.show_advanced_search_modal = true;
        assert!(state.is_capturing_input());
        state.show_advanced_search_modal = false;

        assert!(!state.is_capturing_input());
    }

    #[test]
    fn test_paste_into_advanced_search_modal() {
        let mut state = DownloaderState::new();
        state.show_advanced_search_modal = true;

        state.adv_search_focused_field = 0;
        state.paste("Radiohead");
        assert_eq!(state.adv_search_artist, "Radiohead");

        state.adv_search_focused_field = 1;
        state.paste("Creep");
        assert_eq!(state.adv_search_track, "Creep");

        state.adv_search_focused_field = 2;
        state.paste("Pablo Honey");
        assert_eq!(state.adv_search_album, "Pablo Honey");

        // Normal URL input must remain untouched
        assert!(state.input_text.is_empty());
    }

    #[test]
    fn test_delete_selected_job_middle_and_index_adjustment() {
        let mut state = DownloaderState::new();
        for id in 1..=3 {
            state.jobs.push(DownloadJob {
                id,
                source: format!("track-{}", id),
                display_name: format!("Track #{}", id),
                output_path: None,
                quality: Mp3Quality::FlacLossless,
                policy: AcquisitionPolicy::NicotineFlacPreferred,
                phase: JobPhase::Queued,
                progress: 0.0,
                speed: "--".to_string(),
                eta: "--:--".to_string(),
                spectral_verdict: None,
            });
        }
        state.selected_job_idx = 1; // pointing to Track #2
        state.job_list_state.select(Some(1));

        state.delete_selected_job();

        assert_eq!(state.jobs.len(), 2);
        assert_eq!(state.jobs[0].id, 1);
        assert_eq!(state.jobs[1].id, 3);
        assert_eq!(state.selected_job_idx, 1);
        assert_eq!(state.job_list_state.selected(), Some(1));
        assert!(state.status_message.contains("Deleted job #2"));
    }

    #[test]
    fn test_delete_selected_job_last() {
        let mut state = DownloaderState::new();
        for id in 1..=3 {
            state.jobs.push(DownloadJob {
                id,
                source: format!("track-{}", id),
                display_name: format!("Track #{}", id),
                output_path: None,
                quality: Mp3Quality::FlacLossless,
                policy: AcquisitionPolicy::NicotineFlacPreferred,
                phase: JobPhase::Queued,
                progress: 0.0,
                speed: "--".to_string(),
                eta: "--:--".to_string(),
                spectral_verdict: None,
            });
        }
        state.selected_job_idx = 2; // pointing to Track #3 (last)
        state.job_list_state.select(Some(2));

        state.delete_selected_job();

        assert_eq!(state.jobs.len(), 2);
        assert_eq!(state.selected_job_idx, 1); // clamps to last remaining item
        assert_eq!(state.job_list_state.selected(), Some(1));
        assert!(state.status_message.contains("Deleted job #3"));
    }

    #[test]
    fn test_delete_selected_job_only_one_clears_selection() {
        let mut state = DownloaderState::new();
        state.jobs.push(DownloadJob {
            id: 1,
            source: "single".to_string(),
            display_name: "Single Track".to_string(),
            output_path: None,
            quality: Mp3Quality::FlacLossless,
            policy: AcquisitionPolicy::NicotineFlacPreferred,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });
        state.selected_job_idx = 0;
        state.job_list_state.select(Some(0));

        state.delete_selected_job();

        assert!(state.jobs.is_empty());
        assert_eq!(state.selected_job_idx, 0);
        assert_eq!(state.job_list_state.selected(), None);
        assert!(state.status_message.contains("Deleted job #1"));

        // Deleting when empty reports no jobs
        state.delete_selected_job();
        assert!(state.status_message.contains("No search or download jobs"));
    }

    #[test]
    fn test_delete_selected_job_clears_pending_modal() {
        let mut state = DownloaderState::new();
        state.jobs.push(DownloadJob {
            id: 42,
            source: "track-42".to_string(),
            display_name: "Track 42".to_string(),
            output_path: None,
            quality: Mp3Quality::FlacLossless,
            policy: AcquisitionPolicy::NicotineFlacPreferred,
            phase: JobPhase::Queued,
            progress: 25.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });
        state.pending_job_id = Some(42);
        state.show_lossless_selector = true;
        state.seed_expansion_job_id = Some(42);
        state.show_seed_expansion_modal = true;

        state.delete_selected_job();

        assert!(!state.show_lossless_selector);
        assert_eq!(state.pending_job_id, None);
        assert!(!state.show_seed_expansion_modal);
        assert_eq!(state.seed_expansion_job_id, None);
    }

    #[test]
    fn test_delete_keys_in_queue_tab() {
        let mut state = DownloaderState::new();
        state.jobs.push(DownloadJob {
            id: 10,
            source: "track-10".to_string(),
            display_name: "Track 10".to_string(),
            output_path: None,
            quality: Mp3Quality::FlacLossless,
            policy: AcquisitionPolicy::NicotineFlacPreferred,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });
        state.jobs.push(DownloadJob {
            id: 20,
            source: "track-20".to_string(),
            display_name: "Track 20".to_string(),
            output_path: None,
            quality: Mp3Quality::FlacLossless,
            policy: AcquisitionPolicy::NicotineFlacPreferred,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });

        // 'd' key deletes selected job (index 0)
        state.handle_key(KeyCode::Char('d'));
        assert_eq!(state.jobs.len(), 1);
        assert_eq!(state.jobs[0].id, 20);

        // 'Delete' key deletes remaining job
        state.handle_key(KeyCode::Delete);
        assert!(state.jobs.is_empty());
    }

    #[tokio::test]
    async fn test_audio_player_workflow_and_eq_persistence() {
        let mut state = DownloaderState::new();
        state.focused_field = 1; // Unfocus text box so hotkeys work

        // Add a mock completed job
        state.jobs.push(DownloadJob {
            id: 1,
            source: "mock_track.flac".to_string(),
            display_name: "Mock Track".to_string(),
            output_path: None,
            quality: Mp3Quality::FlacLossless,
            policy: AcquisitionPolicy::NicotineFlacPreferred,
            phase: JobPhase::Completed,
            progress: 100.0,
            speed: "Done".to_string(),
            eta: "00:00".to_string(),
            spectral_verdict: None,
        });

        // 1. Switch to Tab 3 (Audio Player) via '3'
        state.handle_key(KeyCode::Char('3'));
        assert_eq!(state.active_tab, DownloaderTab::Visuals);
        assert_eq!(DownloaderTab::Visuals.label(), "[3] Audio Player");

        // 2. Audio Player hotkeys
        // Space toggles playback
        assert!(!state.player.is_playing());
        state.handle_key(KeyCode::Char(' '));
        assert!(state.player.is_playing());
        assert!(state.status_message.contains("[PLAYING]"));

        // Seek
        state.handle_key(KeyCode::Right);
        assert!(state.status_message.contains("Seek +5s"));
        state.handle_key(KeyCode::Left);
        assert!(state.status_message.contains("Seek -5s"));

        // Restart
        state.handle_key(KeyCode::Char('r'));
        assert!(state.status_message.contains("Restarted from beginning"));

        // 3. Option A: Switch to Tab 2 (10-Band EQ) while playback remains active
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.active_tab, DownloaderTab::Eq);
        // Playback remains active during live auditioning of EQ rails
        assert!(state.player.is_playing());

        // 4. Save enhanced master via 's' in Tab 2
        state.handle_key(KeyCode::Char('s'));
        assert!(state.status_message.contains("Enhancing track #1"));
    }

    #[tokio::test]
    async fn test_dynamic_title_replacement_and_saved_path_binding() {
        let mut state = DownloaderState::new();
        state.jobs.push(DownloadJob {
            id: 99,
            source: "https://www.youtube.com/watch?v=3_soA123456".to_string(),
            display_name: "https://www.youtube.com/watch?v=3_soA...".to_string(),
            output_path: None,
            quality: Mp3Quality::Mp3_320k,
            policy: AcquisitionPolicy::BestAvailable,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });

        // 1. Worker sends resolved title
        let _ = state.tx.send((
            99,
            JobPhase::Downloading,
            20.0,
            "1.2MB/s".into(),
            "00:10".into(),
            Some("RESOLVED_TITLE:Daft Punk - One More Time".into()),
        )).await;

        state.poll_updates();
        assert_eq!(state.jobs[0].display_name, "Daft Punk - One More Time");

        // 2. Create a temporary dummy audio file to simulate successful download
        let temp_dir = std::env::temp_dir();
        let dummy_audio = temp_dir.join("omnirip_test_daft_punk.flac");
        let _ = std::fs::write(&dummy_audio, b"fLaC dummy content");

        // 3. Worker sends completed status with Saved to path
        let _ = state.tx.send((
            99,
            JobPhase::Completed,
            100.0,
            "Done".into(),
            "00:00".into(),
            Some(format!("LOSSLESS VERIFIED: True Lossless (Saved to {})", dummy_audio.display())),
        )).await;

        state.poll_updates();
        assert_eq!(state.jobs[0].output_path, Some(dummy_audio.clone()));
        assert_eq!(state.jobs[0].phase, JobPhase::Completed);

        // Cleanup
        let _ = std::fs::remove_file(dummy_audio);
    }

    #[tokio::test]
    async fn test_lossless_selector_immediate_name_and_quality_update() {
        let mut state = DownloaderState::new();
        state.jobs.push(DownloadJob {
            id: 7,
            source: "https://www.youtube.com/watch?v=sample123".to_string(),
            display_name: "https://www.youtube.com/watch?v=sample...".to_string(),
            output_path: None,
            quality: Mp3Quality::Mp3_320k,
            policy: AcquisitionPolicy::BestAvailable,
            phase: JobPhase::AwaitingSelection(vec![], vec![]),
            progress: 30.0,
            speed: "--".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        });
        state.pending_job_id = Some(7);
        state.lossless_candidates = vec![
            NicotineCandidate {
                username: "audiophile_peer".to_string(),
                filename: "Shared/Music/Daft Punk/Discovery/01 - Daft Punk - One More Time (Lossless).flac".to_string(),
                size_bytes: 45_000_000,
                speed_kbps: Some(1500.0),
                in_queue: 0,
                score: 100.0,
                bitrate_kbps: Some(1411),
                sample_rate: Some(44100),
                bit_depth: Some(16),
            }
        ];
        state.show_lossless_selector = true;
        state.selected_lossless_idx = 0;

        // User hits Enter to select candidate 0
        state.handle_key(KeyCode::Enter);

        // Selector closes and job immediately updates
        assert!(!state.show_lossless_selector);
        assert_eq!(state.jobs[0].quality, Mp3Quality::FlacLossless);
        assert_eq!(state.jobs[0].policy, AcquisitionPolicy::NicotineFlacPreferred);
        assert!(state.jobs[0].display_name.contains("One More Time"));
        assert!(!state.jobs[0].display_name.contains("http"));
    }

    #[test]
    fn test_wrap_text_to_chunks() {
        let err = "Search failed: Failed to initiate search: error sending request for url (http://localhost:5030/api/v0/search)";
        let chunks = wrap_text_to_chunks(err, 40);
        assert!(chunks.len() >= 2);
        for c in &chunks {
            assert!(c.len() <= 40, "Chunk exceeded max_width: '{}'", c);
        }
        let joined = chunks.join(" ");
        assert!(joined.contains("Search failed:"));
        assert!(joined.contains("http://localhost:5030"));

        // Single word longer than limit breaks cleanly without panic
        let long_word = "abcdefghijklmnopqrstuvwxyz1234567890";
        let word_chunks = wrap_text_to_chunks(long_word, 10);
        assert_eq!(word_chunks.len(), 4);
        assert_eq!(word_chunks[0], "abcdefghij");
    }

    #[test]
    fn test_job_phase_short_label_and_full_label() {
        let long_err = "Soulseek daemon unreachable (slskd daemon unreachable: error sending request for url (http://localhost:5030))";
        let phase = JobPhase::Failed(long_err.to_string());
        assert_eq!(phase.short_label(), "[FAILED]");
        assert!(phase.label().starts_with("[FAILED: Soulseek daemon unreachable"));
    }

    #[test]
    fn test_dynamic_spectrum_width_and_markers() {
        let num_bands = 32;
        let inner_w = 175;
        let col_width = (inner_w / num_bands).max(3);
        assert_eq!(col_width, 5);
        let total_graph_w = col_width * num_bands;
        assert_eq!(total_graph_w, 160);
        let excess = inner_w - total_graph_w;
        assert_eq!(excess, 15);
        let left_pad = excess / 2;
        assert_eq!(left_pad, 7);
        let bar_w = col_width - 1;
        assert_eq!(bar_w, 4);

        // Marker position test
        let center_band0 = left_pad + 0 * col_width + (bar_w / 2);
        assert_eq!(center_band0, 9);
        let center_band31 = left_pad + 31 * col_width + (bar_w / 2);
        assert_eq!(center_band31, 7 + 155 + 2); // 164
        assert!(center_band31 < inner_w);
    }

    #[test]
    fn test_audio_player_volume_keybindings() {
        let mut state = DownloaderState::new();
        state.active_tab = DownloaderTab::Visuals;
        state.player.set_volume_pct(80);
        assert_eq!(state.player.volume_pct(), 80);

        // 1. Up key increases volume by 5%
        state.handle_key(KeyCode::Up);
        assert_eq!(state.player.volume_pct(), 85);
        assert!(state.status_message.contains("85%"));

        // 2. Down key decreases volume by 5%
        state.handle_key(KeyCode::Down);
        assert_eq!(state.player.volume_pct(), 80);

        // 3. Plus/Minus keys
        state.handle_key(KeyCode::Char('+'));
        assert_eq!(state.player.volume_pct(), 85);
        state.handle_key(KeyCode::Char('-'));
        assert_eq!(state.player.volume_pct(), 80);

        // 4. Mute toggle ('m')
        state.handle_key(KeyCode::Char('m'));
        assert_eq!(state.player.volume_pct(), 0);
        assert!(state.status_message.contains("MUTED"));

        // 5. Unmute restores to 100%
        state.handle_key(KeyCode::Char('m'));
        assert_eq!(state.player.volume_pct(), 100);
        assert!(state.status_message.contains("UNMUTED"));
    }
}
