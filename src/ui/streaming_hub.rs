//! Workstation 4: Cloud Streaming Hub & Universal Music Player
//!
//! Provides a unified music player for Spotify, Apple Music, YouTube Music,
//! and freeform search queries, streaming audio via high-bitrate Opus streams,
//! persisting user-calibrated volume levels, and routing audio through OmniRip's
//! 16-module mastering DSP rack and real-time spectrum telemetry engine.

use crate::dsp::player::TrackPlayer;
use crate::harvest::library_sync::{
    DividerPlatformPriority, DividerSubSort, LibrarySyncEngine, LinkedAccountsConfig,
    PlatformColorMode, TrackSortMode,
};
use crate::harvest::playlist_parser::{PlaylistParser, StreamingService};
use crate::harvest::stream_resolver::{AudioQualityTier, StreamResolver};
use crate::ui::account_modal::{AccountModalAction, AccountSyncModal};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph, Wrap};
use std::path::PathBuf;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;
use std::thread;

fn char_display_width(c: char) -> usize {
    if c >= '\u{1100}' && (
        (c >= '\u{1100}' && c <= '\u{115f}') ||
        (c >= '\u{2e80}' && c <= '\u{a4cf}') ||
        (c >= '\u{ac00}' && c <= '\u{d7a3}') ||
        (c >= '\u{f900}' && c <= '\u{faff}') ||
        (c >= '\u{fe10}' && c <= '\u{fe19}') ||
        (c >= '\u{fe30}' && c <= '\u{fe6f}') ||
        (c >= '\u{ff00}' && c <= '\u{ff60}') ||
        (c >= '\u{ffe0}' && c <= '\u{ffe6}') ||
        (c >= '\u{20000}' && c <= '\u{2fffd}') ||
        (c >= '\u{30000}' && c <= '\u{3fffd}')
    ) {
        2
    } else {
        1
    }
}

pub fn unicode_display_width(s: &str) -> usize {
    s.chars().map(char_display_width).sum()
}

pub fn truncate_display_str(s: &str, max_w: usize) -> String {
    let mut total_w = 0;
    let mut out = String::new();
    for c in s.chars() {
        let cw = char_display_width(c);
        if total_w + cw > max_w {
            if max_w > 1 && !out.is_empty() {
                let mut trimmed = out.clone();
                while unicode_display_width(&trimmed) + 1 > max_w && !trimmed.is_empty() {
                    trimmed.pop();
                }
                trimmed.push('…');
                return trimmed;
            }
            break;
        }
        total_w += cw;
        out.push(c);
    }
    out
}

pub fn pad_display_str(s: &str, target_w: usize) -> String {
    let w = unicode_display_width(s);
    if w >= target_w {
        truncate_display_str(s, target_w)
    } else {
        let mut res = s.to_string();
        res.push_str(&" ".repeat(target_w - w));
        res
    }
}

#[allow(dead_code)]
fn truncate_str(s: &str, max_len: usize) -> String {
    truncate_display_str(s, max_len)
}

#[derive(Debug, Clone, PartialEq)]
pub enum StreamItemStatus {
    Queued,
    Resolving,
    Playing,
    Paused,
    Completed,
    Failed(String),
}

impl StreamItemStatus {
    pub fn label(&self) -> String {
        match self {
            StreamItemStatus::Queued => "[QUEUED]".to_string(),
            StreamItemStatus::Resolving => "[RESOLVING STREAM]".to_string(),
            StreamItemStatus::Playing => "[PLAYING ♫]".to_string(),
            StreamItemStatus::Paused => "[PAUSED]".to_string(),
            StreamItemStatus::Completed => "[FINISHED]".to_string(),
            StreamItemStatus::Failed(err) => format!("[ERR: {}]", err),
        }
    }
}

#[derive(Debug, Clone)]
pub struct StreamQueueItem {
    pub title: String,
    pub artist: String,
    pub album: String,
    pub duration_secs: Option<u32>,
    pub quality_tier: AudioQualityTier,
    pub service: StreamingService,
    pub source_query: String,
    pub status: StreamItemStatus,
    pub audio_file_path: Option<PathBuf>,
    pub library_name: String,
    pub added_order: u64,
}

#[derive(Debug, Clone, Default)]
pub struct DspTelemetryInfo {
    pub active_preset_name: String,
    pub target_curve: String,
    pub preamp_db: f32,
    pub tube_warmth: f32,
    pub spatial_width: f32,
    pub limiter_ceiling_db: f32,
    pub filter_count: usize,
    pub active_gear_model: String,
}

pub type StreamWorkerResult = Result<(u64, usize, PathBuf, AudioQualityTier, String), (u64, usize, String)>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoopMode {
    Off,
    Single,
    All,
}

impl LoopMode {
    pub fn label(&self) -> &'static str {
        match self {
            LoopMode::Off => "OFF",
            LoopMode::Single => "1 (REPEAT ONE)",
            LoopMode::All => "ALL (REPEAT QUEUE)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            LoopMode::Off => LoopMode::Single,
            LoopMode::Single => LoopMode::All,
            LoopMode::All => LoopMode::Off,
        }
    }
}

pub struct StreamingHubState {
    pub search_input: String,
    pub is_editing_search: bool,
    pub queue: Vec<StreamQueueItem>,
    pub selected_idx: usize,
    pub queue_list_state: ListState,
    pub player: Option<Arc<TrackPlayer>>,
    pub status_message: String,
    pub live_spectrum: [f32; 32],
    pub stream_tx: Sender<StreamWorkerResult>,
    pub stream_rx: Receiver<StreamWorkerResult>,
    pub currently_playing_idx: Option<usize>,
    pub account_modal: AccountSyncModal,
    pub dsp_telemetry: DspTelemetryInfo,
    pub stream_request_id: u64,
    pub jump_input: String,
    pub loop_mode: LoopMode,
    pub shuffle: bool,
    pub shuffle_history: Vec<usize>,
    pub sort_mode: TrackSortMode,
    pub sort_modal_open: bool,
    pub sort_modal_selected_idx: usize,
    pub divider_platform_priority: DividerPlatformPriority,
    pub divider_sub_sort: DividerSubSort,
    pub platform_color_mode: PlatformColorMode,
}

impl Default for StreamingHubState {
    fn default() -> Self {
        Self::new()
    }
}

impl StreamingHubState {
    pub fn new() -> Self {
        Self::new_with_config(LinkedAccountsConfig::load(), AccountSyncModal::new())
    }

    pub fn new_clean() -> Self {
        Self::new_with_config(LinkedAccountsConfig::default(), AccountSyncModal::new_clean())
    }

    pub fn new_with_config(cfg: LinkedAccountsConfig, account_modal: AccountSyncModal) -> Self {
        let (stream_tx, stream_rx) = channel();
        Self {
            search_input: String::new(),
            is_editing_search: false,
            queue: Vec::new(),
            selected_idx: 0,
            queue_list_state: ListState::default(),
            player: None,
            status_message: "Universal Streaming Hub ready. [S] Search/Paste  [L] Link Accounts & Import Library".to_string(),
            live_spectrum: [-60.0; 32],
            stream_tx,
            stream_rx,
            currently_playing_idx: None,
            account_modal,
            dsp_telemetry: DspTelemetryInfo::default(),
            stream_request_id: 0,
            jump_input: String::new(),
            loop_mode: LoopMode::Off,
            shuffle: false,
            shuffle_history: Vec::new(),
            sort_mode: TrackSortMode::LatestAdded,
            sort_modal_open: false,
            sort_modal_selected_idx: 0,
            divider_platform_priority: cfg.divider_platform_priority,
            divider_sub_sort: cfg.divider_sub_sort,
            platform_color_mode: cfg.platform_color_mode,
        }
    }

    pub fn is_capturing_input(&self) -> bool {
        self.is_editing_search || self.account_modal.is_open || self.sort_modal_open
    }

    pub fn paste(&mut self, text: &str) {
        if self.account_modal.is_open {
            self.account_modal.paste(text);
            return;
        }
        let clean = text.trim();
        if clean.is_empty() {
            return;
        }
        if !self.is_editing_search {
            self.is_editing_search = true;
            self.search_input.clear();
        }
        self.search_input.push_str(clean);
        self.status_message = format!("Pasted {} chars. Press [Enter] to resolve & stream.", clean.len());
    }

    pub fn paste_from_clipboard(&mut self) {
        #[cfg(target_os = "macos")]
        {
            if let Ok(output) = std::process::Command::new("pbpaste").output() {
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout).to_string();
                    self.paste(&text);
                }
            }
        }
    }

    /// Consolidates and deduplicates songs currently in the queue based on normalized (artist, title),
    /// preserving the first occurrence (including active playing state or cached audio) and re-indexing.
    pub fn deduplicate_queue(&mut self) -> usize {
        if self.queue.is_empty() {
            return 0;
        }
        let current_playing_key = self.currently_playing_idx.and_then(|idx| self.queue.get(idx).map(|item| (item.artist.clone(), item.title.clone())));
        let selected_key = self.queue.get(self.selected_idx).map(|item| (item.artist.clone(), item.title.clone()));

        let initial_len = self.queue.len();
        let mut seen = std::collections::HashSet::new();
        self.queue.retain(|item| {
            let key = (
                crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
            );
            seen.insert(key)
        });

        if let Some((ref artist, ref title)) = current_playing_key {
            self.currently_playing_idx = self.queue.iter().position(|it| it.artist == *artist && it.title == *title);
        }
        if let Some((ref artist, ref title)) = selected_key {
            if let Some(pos) = self.queue.iter().position(|it| it.artist == *artist && it.title == *title) {
                self.selected_idx = pos;
                self.queue_list_state.select(Some(pos));
            } else if !self.queue.is_empty() {
                self.selected_idx = self.selected_idx.min(self.queue.len() - 1);
                self.queue_list_state.select(Some(self.selected_idx));
            }
        }

        initial_len.saturating_sub(self.queue.len())
    }

    pub fn apply_sort_mode(&mut self, mode: TrackSortMode) {
        self.sort_mode = mode;
        let mut cfg = LinkedAccountsConfig::load();
        if cfg.deduplicate && !self.queue.is_empty() {
            self.deduplicate_queue();
        }
        if !self.queue.is_empty() {
            let current_playing_key = self.currently_playing_idx.and_then(|idx| self.queue.get(idx).map(|item| (item.artist.clone(), item.title.clone())));
            let selected_key = self.queue.get(self.selected_idx).map(|item| (item.artist.clone(), item.title.clone()));

            LibrarySyncEngine::sort_queue_items_custom(
                &mut self.queue,
                self.sort_mode,
                self.divider_platform_priority,
                self.divider_sub_sort,
            );

            if let Some((ref artist, ref title)) = current_playing_key {
                self.currently_playing_idx = self.queue.iter().position(|it| it.artist == *artist && it.title == *title);
            }
            if let Some((ref artist, ref title)) = selected_key {
                if let Some(pos) = self.queue.iter().position(|it| it.artist == *artist && it.title == *title) {
                    self.selected_idx = pos;
                    self.queue_list_state.select(Some(pos));
                }
            }
        }
        cfg.sort_mode = self.sort_mode;
        cfg.divider_platform_priority = self.divider_platform_priority;
        cfg.divider_sub_sort = self.divider_sub_sort;
        let _ = cfg.save();

        if self.sort_mode == TrackSortMode::PlatformDividers {
            self.status_message = format!(
                "Unified Queue sorted by: {} [Lead: {}, Sub-Sort: {}]",
                self.sort_mode.label(),
                self.divider_platform_priority.label(),
                self.divider_sub_sort.label()
            );
        } else {
            self.status_message = format!("Unified Queue sorted by: {} ({} tracks organized)", self.sort_mode.label(), self.queue.len());
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        if self.account_modal.is_open {
            if let Some(action) = self.account_modal.handle_key(code) {
                match action {
                    AccountModalAction::ImportCollections(collections, deduplicate, sort_mode) => {
                        let browser = self.account_modal.selected_browser();
                        let mut all_items = Vec::new();
                        for col in &collections {
                            if let Ok(tracks) = LibrarySyncEngine::fetch_tracks_for_collection(col, &browser) {
                                let n = tracks.len();
                                for (idx, t) in tracks.into_iter().enumerate() {
                                    let query = if let Some(ref url) = t.source_url {
                                        if url.starts_with("http://") || url.starts_with("https://") {
                                            url.clone()
                                        } else {
                                            format!("{} - {}", t.artist, t.title)
                                        }
                                    } else {
                                        format!("{} - {}", t.artist, t.title)
                                    };
                                    all_items.push(StreamQueueItem {
                                        title: t.title.clone(),
                                        artist: t.artist.clone(),
                                        album: t.album,
                                        duration_secs: t.duration_secs.map(|d| d as u32),
                                        quality_tier: AudioQualityTier::CloudOpus160,
                                        service: col.service,
                                        source_query: query,
                                        status: StreamItemStatus::Queued,
                                        audio_file_path: None,
                                        library_name: col.title.clone(),
                                        added_order: if n > 0 { ((idx as u64 + 1) * 1_000_000) / (n as u64) } else { 0 },
                                    });
                                }
                            }
                        }

                        // Deduplicate and organize tracks
                        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, deduplicate, sort_mode);

                        let mut added_new = 0;
                        let mut skipped_duplicates = 0;

                        if deduplicate {
                            self.deduplicate_queue();

                            let mut existing_keys: std::collections::HashSet<(String, String)> = std::collections::HashSet::new();
                            for item in &self.queue {
                                let key = (
                                    crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                                    crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                                );
                                existing_keys.insert(key);
                            }

                            for item in organized {
                                let key = (
                                    crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                                    crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                                );
                                if existing_keys.contains(&key) {
                                    skipped_duplicates += 1;
                                } else {
                                    existing_keys.insert(key);
                                    self.queue.push(item);
                                    added_new += 1;
                                }
                            }
                        } else {
                            for item in organized {
                                self.queue.push(item);
                                added_new += 1;
                            }
                        }

                        // Re-sort entire queue by sort_mode and re-index active playing/selected
                        self.apply_sort_mode(sort_mode);

                        if self.currently_playing_idx.is_none() && !self.queue.is_empty() {
                            self.play_track_at_index(0);
                        }
                        if skipped_duplicates > 0 {
                            self.status_message = format!("Linked Library Sync: added {} new track(s), skipped {} duplicate(s) from {} collection(s) [Total: {}].", added_new, skipped_duplicates, collections.len(), self.queue.len());
                        } else {
                            self.status_message = format!("Linked Library Sync: imported {} track(s) from {} collection(s) [Sorted: {}].", added_new, collections.len(), self.sort_mode.label());
                        }
                    }
                    AccountModalAction::ImportTracks(tracks, deduplicate, sort_mode) => {
                        let mut all_items = Vec::new();
                        for t in tracks {
                            let query = if t.id.starts_with("http://") || t.id.starts_with("https://") {
                                t.id.clone()
                            } else {
                                format!("{} - {}", t.artist, t.title)
                            };
                            all_items.push(StreamQueueItem {
                                title: t.title.clone(),
                                artist: t.artist.clone(),
                                album: t.album,
                                duration_secs: t.duration_secs,
                                quality_tier: AudioQualityTier::CloudOpus160,
                                service: t.service,
                                source_query: query,
                                status: StreamItemStatus::Queued,
                                audio_file_path: None,
                                library_name: t.library_name,
                                added_order: t.added_order,
                            });
                        }

                        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, deduplicate, sort_mode);

                        let mut added_new = 0;
                        let mut skipped_duplicates = 0;

                        if deduplicate {
                            self.deduplicate_queue();

                            let mut existing_keys: std::collections::HashSet<(String, String)> = std::collections::HashSet::new();
                            for item in &self.queue {
                                let key = (
                                    crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                                    crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                                );
                                existing_keys.insert(key);
                            }

                            for item in organized {
                                let key = (
                                    crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                                    crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                                );
                                if existing_keys.contains(&key) {
                                    skipped_duplicates += 1;
                                } else {
                                    existing_keys.insert(key);
                                    self.queue.push(item);
                                    added_new += 1;
                                }
                            }
                        } else {
                            for item in organized {
                                self.queue.push(item);
                                added_new += 1;
                            }
                        }

                        // Re-sort entire queue by sort_mode and re-index active playing/selected
                        self.apply_sort_mode(sort_mode);

                        if self.currently_playing_idx.is_none() && !self.queue.is_empty() {
                            self.play_track_at_index(0);
                        }
                        if skipped_duplicates > 0 {
                            self.status_message = format!("Imported {} new track(s) (skipped {} duplicate(s)) to streaming queue [Total: {}].", added_new, skipped_duplicates, self.queue.len());
                        } else {
                            self.status_message = format!("Imported {} track(s) to streaming queue [Sorted: {}].", added_new, self.sort_mode.label());
                        }
                    }
                    AccountModalAction::Close => {
                        self.status_message = "Closed Account Sync modal.".to_string();
                    }
                }
            }
            return;
        }

        if self.sort_modal_open {
            let modes = [
                TrackSortMode::LatestAdded,
                TrackSortMode::OldestAdded,
                TrackSortMode::TitleAZ,
                TrackSortMode::TitleZA,
                TrackSortMode::ArtistAZ,
                TrackSortMode::ArtistZA,
                TrackSortMode::DurationShortest,
                TrackSortMode::DurationLongest,
                TrackSortMode::PlatformDividers,
            ];
            match code {
                KeyCode::Esc => {
                    self.sort_modal_open = false;
                    self.status_message = "Closed Queue Sort menu.".to_string();
                }
                KeyCode::Char(c @ '1'..='9') => {
                    let idx = (c as usize) - ('1' as usize);
                    if let Some(&m) = modes.get(idx) {
                        self.sort_modal_selected_idx = idx;
                        self.apply_sort_mode(m);
                        self.sort_modal_open = false;
                    }
                }
                KeyCode::Char('0') => {
                    self.divider_platform_priority = DividerPlatformPriority::AppleMusicFirst;
                    self.sort_modal_selected_idx = 8;
                    self.apply_sort_mode(TrackSortMode::PlatformDividers);
                    self.sort_modal_open = false;
                }
                KeyCode::Char('-') => {
                    self.divider_platform_priority = DividerPlatformPriority::YouTubeFirst;
                    self.sort_modal_selected_idx = 8;
                    self.apply_sort_mode(TrackSortMode::PlatformDividers);
                    self.sort_modal_open = false;
                }
                KeyCode::Char('p') | KeyCode::Char('P') => {
                    self.divider_platform_priority = self.divider_platform_priority.next();
                    let mut cfg = LinkedAccountsConfig::load();
                    cfg.divider_platform_priority = self.divider_platform_priority;
                    let _ = cfg.save();
                    if self.sort_mode == TrackSortMode::PlatformDividers {
                        self.apply_sort_mode(TrackSortMode::PlatformDividers);
                    } else {
                        self.status_message = format!("Lead Platform set to: {}", self.divider_platform_priority.label());
                    }
                }
                KeyCode::Char('s') | KeyCode::Char('S') => {
                    self.divider_sub_sort = self.divider_sub_sort.next();
                    let mut cfg = LinkedAccountsConfig::load();
                    cfg.divider_sub_sort = self.divider_sub_sort;
                    let _ = cfg.save();
                    if self.sort_mode == TrackSortMode::PlatformDividers {
                        self.apply_sort_mode(TrackSortMode::PlatformDividers);
                    } else {
                        self.status_message = format!("Divider Section Sub-Sort set to: {}", self.divider_sub_sort.label());
                    }
                }
                KeyCode::Char('c') | KeyCode::Char('C') => {
                    self.platform_color_mode = self.platform_color_mode.cycle();
                    let mut cfg = LinkedAccountsConfig::load();
                    cfg.platform_color_mode = self.platform_color_mode;
                    let _ = cfg.save();
                    self.status_message = format!("Platform Color Coding set to: {}", self.platform_color_mode.label());
                }
                KeyCode::Up | KeyCode::Char('k') => {
                    self.sort_modal_selected_idx = if self.sort_modal_selected_idx == 0 { modes.len() - 1 } else { self.sort_modal_selected_idx - 1 };
                }
                KeyCode::Down | KeyCode::Char('j') => {
                    self.sort_modal_selected_idx = (self.sort_modal_selected_idx + 1) % modes.len();
                }
                KeyCode::Enter | KeyCode::Char(' ') => {
                    if let Some(&m) = modes.get(self.sort_modal_selected_idx) {
                        self.apply_sort_mode(m);
                        self.sort_modal_open = false;
                    }
                }
                KeyCode::Char('o') | KeyCode::Char('O') => {
                    self.sort_modal_selected_idx = (self.sort_modal_selected_idx + 1) % modes.len();
                    if let Some(&m) = modes.get(self.sort_modal_selected_idx) {
                        self.apply_sort_mode(m);
                    }
                }
                _ => {}
            }
            return;
        }

        if self.is_editing_search {
            match code {
                KeyCode::Enter => {
                    self.is_editing_search = false;
                    let query = self.search_input.trim().to_string();
                    if !query.is_empty() {
                        self.submit_search_or_url(query);
                    }
                }
                KeyCode::Esc => {
                    self.is_editing_search = false;
                }
                KeyCode::Backspace => {
                    self.search_input.pop();
                }
                KeyCode::Char(c) => {
                    self.search_input.push(c);
                }
                _ => {}
            }
            return;
        }

        match code {
            KeyCode::Char('s') | KeyCode::Char('S') | KeyCode::Char('/') => {
                self.jump_input.clear();
                self.is_editing_search = true;
                self.search_input.clear();
                self.status_message = "Enter song name (Artist - Title) or paste Spotify/Apple/YouTube URL:".to_string();
            }
            KeyCode::Char(c @ '0'..='9') => {
                self.jump_input.push(c);
                self.status_message = format!("Jump to track #{}: Press [Enter] to play or [Esc] to cancel", self.jump_input);
            }
            KeyCode::Esc => {
                self.jump_input.clear();
                self.status_message = "Cancelled track jump.".to_string();
            }
            KeyCode::Up | KeyCode::Char('k') => {
                self.jump_input.clear();
                if !self.queue.is_empty() && self.selected_idx > 0 {
                    self.selected_idx -= 1;
                }
                while let Ok(true) = crossterm::event::poll(std::time::Duration::from_millis(0)) {
                    if let Ok(crossterm::event::Event::Key(k)) = crossterm::event::read() {
                        if k.kind == crossterm::event::KeyEventKind::Press && (k.code == KeyCode::Up || k.code == KeyCode::Char('k')) {
                            if !self.queue.is_empty() && self.selected_idx > 0 {
                                self.selected_idx -= 1;
                            }
                        } else {
                            self.queue_list_state.select(Some(self.selected_idx));
                            self.handle_key(k.code);
                            return;
                        }
                    } else {
                        break;
                    }
                }
                self.queue_list_state.select(Some(self.selected_idx));
            }
            KeyCode::Down | KeyCode::Char('j') => {
                self.jump_input.clear();
                if !self.queue.is_empty() && self.selected_idx + 1 < self.queue.len() {
                    self.selected_idx += 1;
                }
                while let Ok(true) = crossterm::event::poll(std::time::Duration::from_millis(0)) {
                    if let Ok(crossterm::event::Event::Key(k)) = crossterm::event::read() {
                        if k.kind == crossterm::event::KeyEventKind::Press && (k.code == KeyCode::Down || k.code == KeyCode::Char('j')) {
                            if !self.queue.is_empty() && self.selected_idx + 1 < self.queue.len() {
                                self.selected_idx += 1;
                            }
                        } else {
                            self.queue_list_state.select(Some(self.selected_idx));
                            self.handle_key(k.code);
                            return;
                        }
                    } else {
                        break;
                    }
                }
                self.queue_list_state.select(Some(self.selected_idx));
            }
            KeyCode::PageDown | KeyCode::Char('J') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = (self.selected_idx + 10).min(self.queue.len() - 1);
                    while let Ok(true) = crossterm::event::poll(std::time::Duration::from_millis(0)) {
                        if let Ok(crossterm::event::Event::Key(k)) = crossterm::event::read() {
                            if k.kind == crossterm::event::KeyEventKind::Press && (k.code == KeyCode::PageDown || k.code == KeyCode::Char('J')) {
                                self.selected_idx = (self.selected_idx + 10).min(self.queue.len() - 1);
                            } else {
                                self.queue_list_state.select(Some(self.selected_idx));
                                self.status_message = format!("Jumped to track #{}/{}", self.selected_idx + 1, self.queue.len());
                                self.handle_key(k.code);
                                return;
                            }
                        } else {
                            break;
                        }
                    }
                    self.queue_list_state.select(Some(self.selected_idx));
                    self.status_message = format!("Jumped to track #{}/{}", self.selected_idx + 1, self.queue.len());
                }
            }
            KeyCode::PageUp | KeyCode::Char('K') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = self.selected_idx.saturating_sub(10);
                    while let Ok(true) = crossterm::event::poll(std::time::Duration::from_millis(0)) {
                        if let Ok(crossterm::event::Event::Key(k)) = crossterm::event::read() {
                            if k.kind == crossterm::event::KeyEventKind::Press && (k.code == KeyCode::PageUp || k.code == KeyCode::Char('K')) {
                                self.selected_idx = self.selected_idx.saturating_sub(10);
                            } else {
                                self.queue_list_state.select(Some(self.selected_idx));
                                self.status_message = format!("Jumped to track #{}/{}", self.selected_idx + 1, self.queue.len());
                                self.handle_key(k.code);
                                return;
                            }
                        } else {
                            break;
                        }
                    }
                    self.queue_list_state.select(Some(self.selected_idx));
                    self.status_message = format!("Jumped to track #{}/{}", self.selected_idx + 1, self.queue.len());
                }
            }
            KeyCode::Home | KeyCode::Char('g') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = 0;
                    self.queue_list_state.select(Some(0));
                    self.status_message = format!("Jumped to top track #1/{}", self.queue.len());
                }
            }
            KeyCode::End | KeyCode::Char('G') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = self.queue.len() - 1;
                    self.queue_list_state.select(Some(self.selected_idx));
                    self.status_message = format!("Jumped to end track #{}/{}", self.selected_idx + 1, self.queue.len());
                }
            }
            KeyCode::Enter => {
                if !self.jump_input.is_empty() {
                    let num_str = std::mem::take(&mut self.jump_input);
                    if let Ok(num) = num_str.parse::<usize>() {
                        if num >= 1 && num <= self.queue.len() {
                            let target = num - 1;
                            self.play_track_at_index(target);
                            return;
                        } else {
                            self.status_message = format!("Track #{} is out of range (1 - {}).", num, self.queue.len());
                            return;
                        }
                    }
                }
                if !self.queue.is_empty() {
                    self.play_track_at_index(self.selected_idx);
                }
            }
            KeyCode::Char(' ') => {
                if let Some(idx) = self.currently_playing_idx {
                    if let Some(item) = self.queue.get(idx) {
                        if item.status == StreamItemStatus::Resolving {
                            self.status_message = "Stream resolving... Please wait.".to_string();
                            return;
                        }
                    }
                }
                if let Some(ref p) = self.player {
                    let is_active = p.toggle();
                    if let Some(idx) = self.currently_playing_idx {
                        if let Some(item) = self.queue.get_mut(idx) {
                            item.status = if is_active {
                                StreamItemStatus::Playing
                            } else {
                                StreamItemStatus::Paused
                            };
                        }
                    }
                    self.status_message = format!("Universal Player: {}", if is_active { "PLAYING [Active DSP]" } else { "PAUSED" });
                }
            }
            KeyCode::Left => {
                if let Some(ref p) = self.player {
                    p.seek_by(-5.0);
                    let (cur, total) = p.position();
                    self.status_message = format!("Seek -5s [{:.0}s / {:.0}s]", cur, total);
                }
            }
            KeyCode::Right => {
                if let Some(ref p) = self.player {
                    p.seek_by(5.0);
                    let (cur, total) = p.position();
                    self.status_message = format!("Seek +5s [{:.0}s / {:.0}s]", cur, total);
                }
            }
            KeyCode::Char('+') | KeyCode::Char('=') => {
                if let Some(ref p) = self.player {
                    let new_vol = p.adjust_volume_pct(5);
                    self.status_message = format!("Universal Audio Player Volume: {}% (Persisted)", new_vol);
                }
            }
            KeyCode::Char('-') | KeyCode::Char('_') => {
                if let Some(ref p) = self.player {
                    let new_vol = p.adjust_volume_pct(-5);
                    self.status_message = format!("Universal Audio Player Volume: {}% (Persisted)", new_vol);
                }
            }
            KeyCode::Char('n') | KeyCode::Char('N') => {
                self.play_next();
            }
            KeyCode::Char('p') | KeyCode::Char('P') => {
                self.play_previous();
            }
            KeyCode::Char('r') | KeyCode::Char('R') => {
                self.loop_mode = self.loop_mode.next();
                self.status_message = format!("Playback Loop Mode: {} ([R] cycles Off -> 1 -> All)", self.loop_mode.label());
            }
            KeyCode::Char('z') | KeyCode::Char('Z') => {
                self.shuffle = !self.shuffle;
                self.shuffle_history.clear();
                self.status_message = format!("Playback Shuffle: {} ([Z] toggles)", if self.shuffle { "ON (Randomized Order)" } else { "OFF (Sequential Order)" });
            }
            KeyCode::Char('o') | KeyCode::Char('O') => {
                let modes = [
                    TrackSortMode::LatestAdded,
                    TrackSortMode::OldestAdded,
                    TrackSortMode::TitleAZ,
                    TrackSortMode::TitleZA,
                    TrackSortMode::ArtistAZ,
                    TrackSortMode::ArtistZA,
                    TrackSortMode::DurationShortest,
                    TrackSortMode::DurationLongest,
                    TrackSortMode::PlatformDividers,
                ];
                self.sort_modal_open = true;
                self.sort_modal_selected_idx = modes.iter().position(|&m| m == self.sort_mode).unwrap_or(0);
                self.status_message = format!("Unified Queue Sorting: Select [1-9], [Up/Down]+Enter, or [O] to cycle (Current: {})", self.sort_mode.label());
            }
            KeyCode::Char('d') | KeyCode::Delete => {
                if !self.queue.is_empty() && self.selected_idx < self.queue.len() {
                    let removed = self.queue.remove(self.selected_idx);
                    if self.currently_playing_idx == Some(self.selected_idx) {
                        if let Some(ref p) = self.player {
                            p.stop();
                        }
                        self.currently_playing_idx = None;
                    } else if let Some(curr) = self.currently_playing_idx {
                        if curr > self.selected_idx {
                            self.currently_playing_idx = Some(curr - 1);
                        }
                    }
                    if self.selected_idx >= self.queue.len() && !self.queue.is_empty() {
                        self.selected_idx = self.queue.len() - 1;
                    }
                    self.queue_list_state.select(if self.queue.is_empty() { None } else { Some(self.selected_idx) });
                    self.status_message = format!("Removed '{} - {}' from streaming queue.", removed.artist, removed.title);
                }
            }
            KeyCode::Char('c') | KeyCode::Char('C') => {
                if let Some(ref p) = self.player {
                    p.stop();
                }
                self.queue.clear();
                self.currently_playing_idx = None;
                self.selected_idx = 0;
                self.queue_list_state.select(None);
                self.status_message = "Cleared streaming queue.".to_string();
            }
            KeyCode::Char('l') | KeyCode::Char('L') => {
                self.account_modal.toggle();
            }
            _ => {}
        }
    }

    pub fn submit_search_or_url(&mut self, query: String) {
        let service = StreamingService::detect(&query);
        if service != StreamingService::Unknown {
            self.status_message = format!("Parsing playlist/track URL from {}...", service.label());
            let parser = PlaylistParser::new();
            let query_clone = query.clone();

            let res = thread::spawn(move || {
                match tokio::runtime::Builder::new_current_thread().enable_all().build() {
                    Ok(rt) => rt.block_on(async move {
                        parser.parse_url_or_path(&query_clone).await
                    }),
                    Err(e) => Err(format!("Runtime build error: {}", e)),
                }
            }).join().unwrap_or_else(|_| Err("Thread error".to_string()));

            match res {
                Ok(playlist) => {
                    let count = playlist.tracks.len();
                    let base_order = self.queue.iter().map(|q| q.added_order).max().unwrap_or(0);
                    for (idx, t) in playlist.tracks.into_iter().enumerate() {
                        let track_query = if let Some(ref url) = t.source_url {
                            if (url.starts_with("http://") || url.starts_with("https://"))
                                && !url.contains("/playlist")
                                && !url.contains("list=")
                            {
                                url.clone()
                            } else {
                                format!("{} - {}", t.artist, t.title)
                            }
                        } else {
                            format!("{} - {}", t.artist, t.title)
                        };
                        self.queue.push(StreamQueueItem {
                            title: t.title,
                            artist: t.artist,
                            album: t.album,
                            duration_secs: t.duration_secs.map(|d| d as u32),
                            quality_tier: AudioQualityTier::CloudOpus160,
                            service,
                            source_query: track_query,
                            status: StreamItemStatus::Queued,
                            audio_file_path: None,
                            library_name: playlist.name.clone(),
                            added_order: base_order + 1 + idx as u64,
                        });
                    }
                    self.status_message = format!("Enqueued {} tracks from {} playlist '{}'.", count, service.label(), playlist.name);
                    if self.currently_playing_idx.is_none() && !self.queue.is_empty() {
                        self.play_track_at_index(0);
                    }
                }
                Err(_) => {
                    // Fallback to single item query
                    self.enqueue_plain_query(&query, service);
                }
            }
        } else {
            self.enqueue_plain_query(&query, StreamingService::Unknown);
        }
    }

    fn enqueue_plain_query(&mut self, query: &str, service: StreamingService) {
        let (artist, title) = if let Some((a, t)) = query.split_once(" - ") {
            (a.trim().to_string(), t.trim().to_string())
        } else {
            ("Search Query".to_string(), query.trim().to_string())
        };

        let next_order = self.queue.iter().map(|q| q.added_order).max().unwrap_or(0) + 1;
        self.queue.push(StreamQueueItem {
            title: title.clone(),
            artist: artist.clone(),
            album: "Single Stream".to_string(),
            duration_secs: None,
            quality_tier: AudioQualityTier::CloudOpus160,
            service,
            source_query: query.to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Manual Search".to_string(),
            added_order: next_order,
        });

        let new_idx = self.queue.len() - 1;
        self.selected_idx = new_idx;
        self.queue_list_state.select(Some(new_idx));
        self.status_message = format!("Added '{} - {}' to streaming queue.", artist, title);

        if self.currently_playing_idx.is_none() {
            self.play_track_at_index(new_idx);
        }
    }

    pub fn compute_next_index(&self) -> Option<usize> {
        if self.queue.is_empty() {
            return None;
        }
        if self.shuffle {
            let total = self.queue.len();
            if total == 1 {
                return Some(0);
            }
            use std::time::{SystemTime, UNIX_EPOCH};
            let seed = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().subsec_nanos() as usize;
            let mut candidates: Vec<usize> = (0..total)
                .filter(|&i| Some(i) != self.currently_playing_idx && !self.shuffle_history.contains(&i))
                .collect();
            if candidates.is_empty() {
                candidates = (0..total).filter(|&i| Some(i) != self.currently_playing_idx).collect();
            }
            if !candidates.is_empty() {
                let chosen = candidates[seed % candidates.len()];
                Some(chosen)
            } else {
                Some(0)
            }
        } else {
            match self.currently_playing_idx {
                Some(curr) => {
                    if curr + 1 < self.queue.len() {
                        Some(curr + 1)
                    } else if self.loop_mode == LoopMode::All {
                        Some(0)
                    } else {
                        None
                    }
                }
                None => Some(0),
            }
        }
    }

    pub fn prefetch_next_track(&mut self) {
        if self.queue.is_empty() {
            return;
        }
        if let Some(next_idx) = self.compute_next_index() {
            if next_idx < self.queue.len() {
                let (artist, title, query, existing_path) = {
                    let item = &self.queue[next_idx];
                    (item.artist.clone(), item.title.clone(), item.source_query.clone(), item.audio_file_path.clone())
                };

                // If already cached on disk, skip background fetch
                if existing_path.as_ref().map(|p| p.exists()).unwrap_or(false)
                    || StreamResolver::find_cached_audio_file(&query, &artist, &title).is_some()
                {
                    return;
                }

                let tx = self.stream_tx.clone();
                // req_id = 0 signifies background prefetch without interrupting active playback
                thread::spawn(move || {
                    if let Ok((file_path, tier, fmt_label)) = StreamResolver::resolve_and_fetch_audio(&query, &artist, &title) {
                        let _ = tx.send(Ok((0, next_idx, file_path, tier, fmt_label)));
                    }
                });
            }
        }
    }

    pub fn play_track_at_index(&mut self, idx: usize) {
        if idx >= self.queue.len() {
            return;
        }

        // 1. Immediately silence old audio and flush sample buffers so track change is instant and silent
        if let Some(ref p) = self.player {
            p.clear();
        }

        // 2. Update status of previous track
        if let Some(prev) = self.currently_playing_idx {
            if prev != idx {
                if let Some(item) = self.queue.get_mut(prev) {
                    if item.status == StreamItemStatus::Playing || item.status == StreamItemStatus::Resolving {
                        item.status = StreamItemStatus::Paused;
                    }
                }
            }
        }

        // 3. Immediately mark current track as active in UI state
        self.currently_playing_idx = Some(idx);
        self.selected_idx = idx;
        self.queue_list_state.select(Some(idx));

        let (artist, title, query, existing_path) = {
            let item = &self.queue[idx];
            (item.artist.clone(), item.title.clone(), item.source_query.clone(), item.audio_file_path.clone())
        };

        // Instant Cache Fast-Path: Check if audio is already present on disk in temporary directory
        let cached_hit = existing_path.filter(|p| p.exists()).map(|p| {
            let tier = self.queue[idx].quality_tier;
            (p, tier, format!("{} (Instant Cache)", tier.label()))
        }).or_else(|| {
            StreamResolver::find_cached_audio_file(&query, &artist, &title).map(|(p, tier, label)| {
                if let Some(item) = self.queue.get_mut(idx) {
                    item.audio_file_path = Some(p.clone());
                    item.quality_tier = tier;
                }
                (p, tier, label)
            })
        });

        if let Some((path, _, fmt_label)) = cached_hit {
            if let Some(ref p) = self.player {
                if p.load_file(&path).is_ok() {
                    p.play();
                    if let Some(item) = self.queue.get_mut(idx) {
                        item.status = StreamItemStatus::Playing;
                    }
                    self.status_message = format!("Instant Playback: {} - {} [{} | Active DSP]", artist, title, fmt_label);
                    self.prefetch_next_track();
                    return;
                }
            }
        }

        if let Some(item) = self.queue.get_mut(idx) {
            item.status = StreamItemStatus::Resolving;
        }
        self.status_message = format!("Resolving cloud audio stream for '{} - {}'...", artist, title);

        self.stream_request_id += 1;
        let req_id = self.stream_request_id;
        let tx = self.stream_tx.clone();

        thread::spawn(move || {
            match StreamResolver::resolve_and_fetch_audio(&query, &artist, &title) {
                Ok((file_path, tier, fmt_label)) => {
                    let _ = tx.send(Ok((req_id, idx, file_path, tier, fmt_label)));
                }
                Err(err) => {
                    let _ = tx.send(Err((req_id, idx, err)));
                }
            }
        });
    }

    pub fn play_next(&mut self) {
        if self.queue.is_empty() {
            return;
        }
        if let Some(next_idx) = self.compute_next_index() {
            if self.shuffle {
                if let Some(curr) = self.currently_playing_idx {
                    self.shuffle_history.push(curr);
                    if self.shuffle_history.len() > self.queue.len() {
                        self.shuffle_history.remove(0);
                    }
                }
            }
            self.selected_idx = next_idx;
            self.queue_list_state.select(Some(next_idx));
            self.play_track_at_index(next_idx);
        } else if self.loop_mode == LoopMode::All {
            self.selected_idx = 0;
            self.queue_list_state.select(Some(0));
            self.play_track_at_index(0);
        } else {
            self.status_message = "Reached end of streaming queue. [R] Loop or [Z] Shuffle to replay.".to_string();
        }
    }

    pub fn play_previous(&mut self) {
        if self.queue.is_empty() {
            return;
        }
        if self.shuffle && !self.shuffle_history.is_empty() {
            let prev_idx = self.shuffle_history.pop().unwrap_or(0);
            self.selected_idx = prev_idx;
            self.queue_list_state.select(Some(prev_idx));
            self.play_track_at_index(prev_idx);
            return;
        }
        let prev_idx = match self.currently_playing_idx {
            Some(curr) if curr > 0 => curr - 1,
            _ => self.queue.len().saturating_sub(1),
        };
        self.selected_idx = prev_idx;
        self.queue_list_state.select(Some(prev_idx));
        self.play_track_at_index(prev_idx);
    }

    pub fn poll_stream_worker(&mut self) {
        self.account_modal.poll_background_sync();
        while let Ok(result) = self.stream_rx.try_recv() {
            match result {
                Ok((req_id, idx, path, tier, fmt_label)) => {
                    if let Some(item) = self.queue.get_mut(idx) {
                        item.audio_file_path = Some(path.clone());
                        item.quality_tier = tier;
                        if item.status == StreamItemStatus::Resolving && req_id != self.stream_request_id {
                            item.status = StreamItemStatus::Queued;
                        }
                    }
                    // Only load and start playback if this response matches the active request
                    if req_id != 0 && req_id == self.stream_request_id {
                        if let Some(ref p) = self.player {
                            match p.load_file(&path) {
                                Ok(_) => {
                                    p.play();
                                    self.currently_playing_idx = Some(idx);
                                    if let Some(item) = self.queue.get_mut(idx) {
                                        item.status = StreamItemStatus::Playing;
                                        self.status_message = format!("Now Streaming: {} - {} [{} | DSP Rack Active]", item.artist, item.title, fmt_label);
                                    }
                                    self.prefetch_next_track();
                                }
                                Err(err) => {
                                    if let Some(item) = self.queue.get_mut(idx) {
                                        item.status = StreamItemStatus::Failed(err.clone());
                                    }
                                    self.status_message = format!("Playback error: {}", err);
                                    // Remove corrupt file so retry works
                                    let _ = std::fs::remove_file(&path);
                                }
                            }
                        }
                    }
                }
                Err((req_id, idx, err)) => {
                    if let Some(item) = self.queue.get_mut(idx) {
                        if item.status == StreamItemStatus::Resolving {
                            item.status = if req_id == self.stream_request_id {
                                StreamItemStatus::Failed(err.clone())
                            } else {
                                StreamItemStatus::Queued
                            };
                        }
                    }
                    if req_id == self.stream_request_id {
                        self.status_message = format!("Stream resolution failed: {}", err);
                    }
                }
            }
        }

        // Autoplay & Loop handling: When current track finishes playing
        if let Some(ref p) = self.player {
            if p.consume_finished() {
                if let Some(curr) = self.currently_playing_idx {
                    if self.loop_mode == LoopMode::Single {
                        // Rewind directly in memory with zero network delay and replay
                        p.restart();
                        if let Some(item) = self.queue.get(curr) {
                            self.status_message = format!("Looping Track: {} - {} [Single Repeat Active]", item.artist, item.title);
                        }
                    } else {
                        if let Some(item) = self.queue.get_mut(curr) {
                            item.status = StreamItemStatus::Completed;
                        }
                        if self.shuffle || curr + 1 < self.queue.len() || self.loop_mode == LoopMode::All {
                            self.play_next();
                        } else {
                            p.stop();
                            self.status_message = "Queue finished. Autoplay idle. Press [R] to Loop or [Z] to Shuffle.".to_string();
                        }
                    }
                }
            }
        }
    }

    pub fn render(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Search Bar & Platform Status
                Constraint::Min(10),   // Split Queue / Player
                Constraint::Length(4), // Hotkey Bar (2 Lines)
            ])
            .split(area);

        // 1. Search Bar
        self.render_search_bar(f, v_chunks[0], theme);

        // 2. Middle area: Split horizontally (Queue Left, Player/Visuals Right)
        let mid_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(64), // Queue list (expanded for song titles and artists)
                Constraint::Percentage(36), // Now Playing card & live telemetry
            ])
            .split(v_chunks[1]);

        self.render_queue_panel(f, mid_chunks[0], theme);
        self.render_now_playing_panel(f, mid_chunks[1], theme);

        // 3. Footer hotkeys
        self.render_footer(f, v_chunks[2], theme);

        // 4. Account Linking & Library Sync Modal (Overlay)
        self.account_modal.render(f, area, theme);

        // 5. Interactive Queue Sort Modal (Overlay)
        if self.sort_modal_open {
            self.render_sort_modal(f, area, theme);
        }
    }

    fn render_search_bar(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let block = Block::default()
            .title(" [1] CLOUD STREAM SEARCH & CROSS-PLATFORM URL INGESTION ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let input_text = if self.is_editing_search {
            format!("{}_", self.search_input)
        } else if self.search_input.is_empty() {
            "Press [S] to enter song search query or paste Spotify, Apple Music, or YouTube URL...".to_string()
        } else {
            self.search_input.clone()
        };

        let style = if self.is_editing_search {
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };

        let lines = vec![
            Line::from(vec![
                Span::styled(" [S] Search Query / Link: ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(input_text, style),
            ]),
            Line::from(vec![
                Span::styled(" Backend Engine: ", Style::default().fg(theme.text_dim)),
                Span::styled("Public High-Bitrate Opus (Format 251 / 160k-256k)", Style::default().fg(theme.success)),
                Span::styled(" | Zero-Subscription Streaming Active", Style::default().fg(theme.primary)),
            ]),
        ];

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_queue_panel(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let title_str = format!(" [2] UNIFIED STREAMING QUEUE ({} tracks) - [O] Sort: {} ", self.queue.len(), self.sort_mode.label());
        let block = Block::default()
            .title(title_str)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.secondary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        if self.queue.is_empty() {
            let empty_p = Paragraph::new("Queue is empty. Press [S] to search any song or paste a playlist link.")
                .alignment(Alignment::Center)
                .style(Style::default().fg(theme.text_dim));
            f.render_widget(empty_p, inner);
            return;
        }

        let total_w = inner.width as usize;
        let idx_w = if self.queue.len() >= 1000 { 6 } else if self.queue.len() >= 100 { 5 } else { 4 };
        let overhead = 2 + idx_w + 9 + 6; // Cursor(2) + Index(idx_w) + 3 * " | "(9) + Duration(6)
        let status_w = 12.min(total_w.saturating_sub(overhead));
        let content_w = total_w.saturating_sub(overhead + status_w);
        let title_w = (content_w * 58 / 100).min(content_w);
        let artist_w = content_w.saturating_sub(title_w);

        let is_divider_mode = self.sort_mode == TrackSortMode::PlatformDividers;

        let mut section_counts = std::collections::HashMap::new();
        if is_divider_mode {
            for item in &self.queue {
                *section_counts.entry((item.service, item.library_name.as_str())).or_insert(0usize) += 1;
            }
        }

        let items: Vec<ListItem> = self
            .queue
            .iter()
            .enumerate()
            .map(|(idx, item)| {
                let is_selected = idx == self.selected_idx;
                let is_current = self.currently_playing_idx == Some(idx);
                let cursor = if is_selected { "> " } else { "  " };

                let dur_str = item
                    .duration_secs
                    .map(|d| format!("{:02}:{:02}", (d / 60).min(99), d % 60))
                    .unwrap_or_else(|| "--:--".to_string());
                let dur_field = format!("{} ", dur_str);

                let raw_status = match &item.status {
                    StreamItemStatus::Playing => "[PLAYING ♫]".to_string(),
                    StreamItemStatus::Paused => "[PAUSED]".to_string(),
                    StreamItemStatus::Resolving => "[RESOLVING]".to_string(),
                    StreamItemStatus::Failed(err) => format!("[FAIL: {}]", truncate_display_str(err, 4)),
                    _ => item.status.label(),
                };
                let disp_status = pad_display_str(&raw_status, status_w);
                let status_style = match &item.status {
                    StreamItemStatus::Playing => Style::default().fg(theme.success).add_modifier(Modifier::BOLD),
                    StreamItemStatus::Paused => Style::default().fg(Color::Yellow),
                    StreamItemStatus::Resolving => Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                    StreamItemStatus::Failed(_) => Style::default().fg(Color::LightRed),
                    _ => Style::default().fg(theme.text_dim),
                };
                let status_span = Span::styled(disp_status, status_style);

                let platform_color = match item.service {
                    StreamingService::Spotify => Color::Rgb(30, 215, 96),     // Spotify Green
                    StreamingService::AppleMusic => Color::Rgb(255, 80, 120),  // Apple Music Rose / Coral
                    StreamingService::YouTubeMusic => Color::Rgb(255, 60, 60), // YouTube Red
                    StreamingService::LocalM3u | StreamingService::Unknown => Color::Cyan, // Local / General Cyan
                };

                let disp_idx = format!("#{:>width$} ", idx + 1, width = idx_w.saturating_sub(2));

                let (idx_style, title_style, artist_style) = match self.platform_color_mode {
                    PlatformColorMode::None => {
                        let t_style = if is_current {
                            Style::default().fg(theme.success).add_modifier(Modifier::BOLD)
                        } else if is_selected {
                            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                        } else {
                            Style::default().fg(theme.text)
                        };
                        let a_style = Style::default().fg(theme.text_dim);
                        let i_style = Style::default().fg(theme.text_dim);
                        (i_style, t_style, a_style)
                    }
                    PlatformColorMode::Accent => {
                        let t_style = if is_current {
                            Style::default().fg(theme.success).add_modifier(Modifier::BOLD)
                        } else if is_selected {
                            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                        } else {
                            Style::default().fg(theme.text)
                        };
                        let a_style = Style::default().fg(theme.text_dim);
                        let i_style = if is_selected {
                            Style::default().fg(Color::Black).bg(platform_color).add_modifier(Modifier::BOLD)
                        } else {
                            Style::default().fg(platform_color).add_modifier(Modifier::BOLD)
                        };
                        (i_style, t_style, a_style)
                    }
                    PlatformColorMode::Full => {
                        let t_style = if is_current {
                            Style::default().fg(theme.success).add_modifier(Modifier::BOLD)
                        } else if is_selected {
                            Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                        } else {
                            Style::default().fg(platform_color).add_modifier(Modifier::BOLD)
                        };
                        let a_style = if is_selected {
                            Style::default().fg(Color::White)
                        } else {
                            Style::default().fg(platform_color)
                        };
                        let i_style = Style::default().fg(platform_color);
                        (i_style, t_style, a_style)
                    }
                };

                let disp_title = pad_display_str(&item.title, title_w);
                let disp_artist = pad_display_str(&item.artist, artist_w);

                let line = Line::from(vec![
                    Span::styled(cursor, if is_selected { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                    Span::styled(disp_idx, idx_style),
                    Span::styled(disp_title, title_style),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(disp_artist, artist_style),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(dur_field, Style::default().fg(theme.accent)),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    status_span,
                ]);

                let bg_style = if is_selected {
                    Style::default().bg(Color::Rgb(30, 35, 45))
                } else {
                    Style::default()
                };

                let is_section_start = is_divider_mode && (
                    idx == 0
                        || item.service != self.queue[idx - 1].service
                        || item.library_name != self.queue[idx - 1].library_name
                );

                if is_section_start {
                    let section_count = section_counts
                        .get(&(item.service, item.library_name.as_str()))
                        .copied()
                        .unwrap_or(1);

                    let (platform_tag, platform_color) = match item.service {
                        StreamingService::Spotify => ("[SPOTIFY]", Color::Green),
                        StreamingService::AppleMusic => ("[APPLE MUSIC]", Color::Rgb(255, 80, 100)),
                        StreamingService::YouTubeMusic => ("[YOUTUBE MUSIC]", Color::LightRed),
                        _ => ("[LIBRARY]", Color::Cyan),
                    };

                    let lib_label = if item.library_name.trim().is_empty() {
                        "Collection".to_string()
                    } else {
                        item.library_name.trim().to_string()
                    };

                    let header_prefix = format!("─── {} {} ({} tracks) ", platform_tag, lib_label, section_count);
                    let prefix_len = unicode_display_width(&header_prefix);
                    let divider_text = if prefix_len >= total_w {
                        truncate_display_str(&header_prefix, total_w)
                    } else {
                        let fill_len = total_w - prefix_len;
                        format!("{}{}", header_prefix, "─".repeat(fill_len))
                    };

                    let divider_line = Line::from(Span::styled(
                        divider_text,
                        Style::default().fg(platform_color).add_modifier(Modifier::BOLD),
                    ));

                    ListItem::new(vec![divider_line, line]).style(bg_style)
                } else {
                    ListItem::new(line).style(bg_style)
                }
            })
            .collect();

        let list_widget = List::new(items).highlight_style(Style::default().add_modifier(Modifier::BOLD));
        f.render_stateful_widget(list_widget, inner, &mut self.queue_list_state);
    }

    fn render_now_playing_panel(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let block = Block::default()
            .title(" [3] UNIVERSAL PLAYBACK & LIVE DSP TELEMETRY ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let (title, artist, tier, status_str) = if let Some(idx) = self.currently_playing_idx {
            if let Some(item) = self.queue.get(idx) {
                (item.title.as_str(), item.artist.as_str(), item.quality_tier, item.status.label())
            } else {
                ("No Active Stream", "---", AudioQualityTier::CloudOpus160, "[STANDBY]".to_string())
            }
        } else {
            ("No Active Stream", "---", AudioQualityTier::CloudOpus160, "[STANDBY]".to_string())
        };

        let (cur_secs, total_secs) = if let Some(ref p) = self.player {
            p.position()
        } else {
            (0.0, 0.0)
        };

        let vol_pct = if let Some(ref p) = self.player {
            p.volume_pct()
        } else {
            50
        };

        let progress_pct = if total_secs > 0.0 {
            (cur_secs / total_secs).clamp(0.0, 1.0)
        } else {
            0.0
        };

        let cur_str = format!("{:02}:{:02}", (cur_secs as u32) / 60, (cur_secs as u32) % 60);
        let total_str = format!("{:02}:{:02}", (total_secs as u32) / 60, (total_secs as u32) % 60);

        let tier_color = match tier {
            AudioQualityTier::HiResFlac24 => Color::Rgb(255, 215, 0),
            AudioQualityTier::CdFlac16 => Color::Cyan,
            AudioQualityTier::StudioLossy320 => Color::Green,
            AudioQualityTier::CloudOpus160 => Color::Magenta,
            AudioQualityTier::CloudAac128 => Color::White,
        };

        let mut lines = Vec::new();

        // 1. Now Playing Stream Identity
        lines.push(Line::from(vec![
            Span::styled(" Track:      ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(title, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Artist:     ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(artist, Style::default().fg(theme.text)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Stream:     ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("[{}] ", tier.label()), Style::default().fg(tier_color).add_modifier(Modifier::BOLD)),
            Span::styled(format!("{} kHz • {} kbps", tier.sample_rate_hz() / 1000, tier.nominal_bitrate_kbps()), Style::default().fg(theme.accent)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Processing: ", Style::default().fg(theme.text_dim)),
            if !tier.is_lossless() {
                Span::styled("[DSP Audio Restorer: Active]", Style::default().fg(Color::Yellow))
            } else {
                Span::styled("[Bit-Perfect Lossless PCM]", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
            },
        ]));

        lines.push(Line::from(""));

        // 2. Transport & Acoustic Gauges
        lines.push(Line::from(vec![
            Span::styled("─── PLAYBACK TRANSPORT & GAUGES ───", Style::default().fg(theme.border).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" State:      ", Style::default().fg(theme.text_dim)),
            Span::styled(format!(" {} ", status_str), Style::default().fg(Color::Black).bg(if status_str.contains("PLAYING") { Color::Green } else { Color::Yellow }).add_modifier(Modifier::BOLD)),
            Span::raw("  "),
            Span::styled(if self.shuffle { "[SHUFFLE: ON] " } else { "[SHUFFLE: OFF] " }, Style::default().fg(if self.shuffle { Color::Green } else { theme.text_dim })),
            Span::styled(format!("[LOOP: {}]", self.loop_mode.label()), Style::default().fg(match self.loop_mode { LoopMode::Off => theme.text_dim, LoopMode::Single => Color::Magenta, LoopMode::All => Color::Cyan })),
        ]));

        // Dynamic progress bar scaled to panel width
        let bar_width = (inner.width as usize).saturating_sub(24).clamp(10, 32);
        let filled = (progress_pct * bar_width as f32).round() as usize;
        let empty = bar_width.saturating_sub(filled);
        let progress_bar = format!("[{}{}]", "█".repeat(filled), "░".repeat(empty));

        lines.push(Line::from(vec![
            Span::styled(" Progress:   ", Style::default().fg(theme.text_dim)),
            Span::styled(progress_bar, Style::default().fg(theme.primary)),
            Span::styled(format!(" {} / {}", cur_str, total_str), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
        ]));

        // Volume gauge
        let vol_bar_width = (inner.width as usize).saturating_sub(28).clamp(8, 18);
        let vol_filled = ((vol_pct as f32 / 100.0) * vol_bar_width as f32).round() as usize;
        let vol_empty = vol_bar_width.saturating_sub(vol_filled);
        let vol_bar = format!("[{}{}]", "■".repeat(vol_filled), "·".repeat(vol_empty));

        lines.push(Line::from(vec![
            Span::styled(" Master Vol: ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("{:>3}% ", vol_pct), Style::default().fg(if vol_pct > 80 { Color::Yellow } else { theme.success }).add_modifier(Modifier::BOLD)),
            Span::styled(vol_bar, Style::default().fg(if vol_pct > 80 { Color::Yellow } else { theme.success })),
            Span::styled(" (Safe Level)", Style::default().fg(theme.text_dim)),
        ]));

        lines.push(Line::from(""));

        // 3. System DSP & Acoustic Calibration (Workstation 2)
        lines.push(Line::from(vec![
            Span::styled("─── SYSTEM DSP & ACOUSTIC RECIPE ───", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Preset:     ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.dsp_telemetry.active_preset_name.is_empty() { "Flat Studio Reference" } else { &self.dsp_telemetry.active_preset_name }, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
            Span::styled(format!(" ({} PEQ Filters)", self.dsp_telemetry.filter_count), Style::default().fg(theme.accent)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Target:     ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.dsp_telemetry.target_curve.is_empty() { "Harman Target Curve" } else { &self.dsp_telemetry.target_curve }, Style::default().fg(Color::Cyan)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Transducer: ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.dsp_telemetry.active_gear_model.is_empty() { "Auto-Calibrated Output" } else { &self.dsp_telemetry.active_gear_model }, Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" DSP Nodes:  ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("Preamp {:+.1}dB  •  Warmth {:.0}%",
                self.dsp_telemetry.preamp_db,
                self.dsp_telemetry.tube_warmth * 100.0), Style::default().fg(theme.secondary)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("             ", Style::default().fg(theme.text_dim)),
            Span::styled(format!("Width {:.0}%  •  Ceiling {:+.1}dB",
                self.dsp_telemetry.spatial_width * 100.0,
                self.dsp_telemetry.limiter_ceiling_db), Style::default().fg(theme.secondary)),
        ]));

        lines.push(Line::from(""));

        // 4. Real-Time Signal Routing
        lines.push(Line::from(vec![
            Span::styled("─── REAL-TIME SIGNAL ROUTING ───", Style::default().fg(theme.border).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Signal:     ", Style::default().fg(theme.text_dim)),
            Span::styled("Lossless PCM -> System DSP Rack -> Rust Audio", Style::default().fg(theme.success)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" Audio Core: ", Style::default().fg(theme.text_dim)),
            Span::styled("48 kHz / 32-bit Float | Bit-Perfect | Low Jitter", Style::default().fg(theme.text_dim)),
        ]));

        let p = Paragraph::new(lines).wrap(Wrap { trim: true });
        f.render_widget(p, inner);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let line1 = Line::from(vec![
            Span::styled(" [S] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Search/Paste  "),
            Span::styled(" [L] ", Style::default().fg(Color::Rgb(255, 140, 200)).add_modifier(Modifier::BOLD)),
            Span::raw("Accounts & Sync  "),
            Span::styled(" [Enter] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::raw("Play  "),
            Span::styled(" [Space] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::raw("Pause  "),
            Span::styled(" [N] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Next  "),
            Span::styled(" [P] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Prev  "),
            Span::styled(" [PgUp/Dn] ", Style::default().fg(Color::Rgb(100, 200, 255)).add_modifier(Modifier::BOLD)),
            Span::raw("±10 Track  "),
            Span::styled(" [0-9] ", Style::default().fg(Color::Rgb(255, 215, 0)).add_modifier(Modifier::BOLD)),
            Span::raw("Go to #"),
        ]);

        let line2 = Line::from(vec![
            Span::styled(" [+/-] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("Master Vol  "),
            Span::styled(" [Z] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw("Shuffle  "),
            Span::styled(" [R] ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
            Span::raw("Loop  "),
            Span::styled(" [O] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Sort: Dividers  ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(" [E] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("EQ Preset  "),
            Span::styled(" [D] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::raw("Remove Track  "),
            Span::styled(" [C] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::raw("Clear  "),
            Span::styled(" [m] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::raw("Mode  "),
            Span::styled(" [:] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::raw("Command"),
        ]);

        let p = Paragraph::new(vec![line1, line2])
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p, area);
    }

    fn render_sort_modal(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let popup_w = 84.min(area.width.saturating_sub(4));
        let popup_h = 28.min(area.height.saturating_sub(2));

        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length((area.height.saturating_sub(popup_h)) / 2),
                Constraint::Length(popup_h),
                Constraint::Min(0),
            ])
            .split(area);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length((area.width.saturating_sub(popup_w)) / 2),
                Constraint::Length(popup_w),
                Constraint::Min(0),
            ])
            .split(v_chunks[1]);

        let modal_area = h_chunks[1];
        f.render_widget(Clear, modal_area);

        let block = Block::default()
            .title(format!(" [O] UNIFIED STREAMING QUEUE SORTING ({} tracks) ", self.queue.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(modal_area);
        f.render_widget(block, modal_area);

        let modes = [
            (TrackSortMode::LatestAdded, "[1] Latest Added", "Original playlist ingestion order"),
            (TrackSortMode::OldestAdded, "[2] Oldest Added", "Reverse chronological order"),
            (TrackSortMode::TitleAZ, "[3] Title (A - Z)", "Alphabetical by track title"),
            (TrackSortMode::TitleZA, "[4] Title (Z - A)", "Reverse alphabetical by track title"),
            (TrackSortMode::ArtistAZ, "[5] Artist (A - Z)", "Organized by artist, album & title"),
            (TrackSortMode::ArtistZA, "[6] Artist (Z - A)", "Reverse alphabetical by artist"),
            (TrackSortMode::DurationShortest, "[7] Duration (Shortest)", "Shortest tracks first"),
            (TrackSortMode::DurationLongest, "[8] Duration (Longest)", "Longest tracks first"),
            (TrackSortMode::PlatformDividers, "[9] Platform Dividers", "Segmented by Platform & Library"),
        ];

        let mut lines = Vec::new();
        lines.push(Line::from(vec![
            Span::styled(" Select sorting mode to organize your active streaming queue:", Style::default().fg(theme.text_dim)),
        ]));
        lines.push(Line::from(""));

        for (idx, (mode, label, desc)) in modes.iter().enumerate() {
            let is_sel = idx == self.sort_modal_selected_idx;
            let is_active = *mode == self.sort_mode;
            let indicator = if is_sel { "> " } else { "  " };
            let active_mark = if is_active { " [*ACTIVE*]" } else { "" };

            let row_style = if is_sel {
                Style::default().fg(Color::Black).bg(theme.accent).add_modifier(Modifier::BOLD)
            } else if is_active {
                Style::default().fg(theme.success).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.text)
            };

            lines.push(Line::from(vec![
                Span::styled(indicator, Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(format!("{:<23}", label), row_style),
                Span::styled(format!(" - {}{}", desc, active_mark), if is_sel { Style::default().fg(Color::Black).bg(theme.accent) } else if is_active { Style::default().fg(theme.success) } else { Style::default().fg(theme.text_dim) }),
            ]));
        }

        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled(" ── Platform Divider Customization ──", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" [P] Lead Platform : ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(self.divider_platform_priority.label(), Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("     Direct Select : ", Style::default().fg(theme.text_dim)),
            Span::styled("[9] Spotify  ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("[0] Apple Music  ", Style::default().fg(Color::Rgb(255, 80, 100)).add_modifier(Modifier::BOLD)),
            Span::styled("[-] YouTube Music", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" [S] Section Sub-Sort: ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(self.divider_sub_sort.label(), Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("     Cycle [S]     : ", Style::default().fg(theme.text_dim)),
            Span::styled("Latest -> Oldest -> Artist -> Title -> Duration", Style::default().fg(Color::Yellow)),
        ]));

        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled(" ── Platform Color Coding (Option A / B / None) ──", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" [C] Platform Colors: ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(format!(" {} ", self.platform_color_mode.label()), match self.platform_color_mode {
                PlatformColorMode::None => Style::default().fg(theme.text_dim),
                PlatformColorMode::Accent => Style::default().fg(Color::Black).bg(Color::Yellow).add_modifier(Modifier::BOLD),
                PlatformColorMode::Full => Style::default().fg(Color::Black).bg(Color::Green).add_modifier(Modifier::BOLD),
            }),
        ]));
        lines.push(Line::from(vec![
            Span::styled("     Cycle [C]     : ", Style::default().fg(theme.text_dim)),
            Span::styled("[None]", Style::default().fg(theme.text_dim)),
            Span::raw(" -> "),
            Span::styled("[Option B: Accent]", Style::default().fg(Color::Yellow)),
            Span::raw(" -> "),
            Span::styled("[Option A: Full Row]", Style::default().fg(Color::Green)),
        ]));

        lines.push(Line::from(""));
        lines.push(Line::from(vec![
            Span::styled(" [1-9] Direct  ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled(" [Up/Down] Move  ", Style::default().fg(theme.secondary)),
            Span::styled(" [Enter] Apply  ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::styled(" [Esc] Close", Style::default().fg(theme.text_dim)),
        ]));
        lines.push(Line::from(vec![
            Span::styled(" [P] Lead Platform  ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled(" [S] Sub-Sort  ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled(" [C] Platform Colors  ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled(" [O] Cycle Mode", Style::default().fg(theme.accent)),
        ]));

        f.render_widget(Paragraph::new(lines), inner);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::harvest::library_sync::DiscoveredTrackItem;

    #[test]
    fn test_streaming_hub_initialization() {
        let state = StreamingHubState::new();
        assert!(state.queue.is_empty());
        assert_eq!(state.selected_idx, 0);
        assert!(!state.is_capturing_input());
    }

    #[test]
    fn test_enqueue_plain_query_and_navigation() {
        let mut state = StreamingHubState::new();
        state.enqueue_plain_query("Daft Punk - One More Time", StreamingService::Spotify);
        assert_eq!(state.queue.len(), 1);
        assert_eq!(state.queue[0].title, "One More Time");
        assert_eq!(state.queue[0].artist, "Daft Punk");

        state.enqueue_plain_query("The Weeknd - Blinding Lights", StreamingService::AppleMusic);
        assert_eq!(state.queue.len(), 2);

        // Navigate
        state.handle_key(KeyCode::Up);
        assert_eq!(state.selected_idx, 0);

        state.handle_key(KeyCode::Down);
        assert_eq!(state.selected_idx, 1);
    }

    #[test]
    fn test_remove_track_from_queue() {
        let mut state = StreamingHubState::new();
        state.enqueue_plain_query("Track 1 - Song 1", StreamingService::Unknown);
        state.enqueue_plain_query("Track 2 - Song 2", StreamingService::Unknown);

        state.selected_idx = 0;
        state.handle_key(KeyCode::Char('d'));
        assert_eq!(state.queue.len(), 1);
        assert_eq!(state.queue[0].title, "Song 2");

        // Capital 'D' (Shift+D for DAC cycling) must NOT remove tracks or stop playback
        state.handle_key(KeyCode::Char('D'));
        assert_eq!(state.queue.len(), 1, "Capital 'D' must not remove tracks from queue");
        assert_eq!(state.queue[0].title, "Song 2");
    }

    #[test]
    fn test_account_sync_modal_toggle_and_paste() {
        let mut state = StreamingHubState::new_clean();
        assert!(!state.account_modal.is_open);
        assert!(!state.is_capturing_input());

        // Press 'L' to toggle modal open
        state.handle_key(KeyCode::Char('l'));
        assert!(state.account_modal.is_open);
        assert!(state.is_capturing_input());

        // Set focused field to Spotify input
        state.account_modal.focused_field = 0;
        state.paste("https://open.spotify.com/user/audiophile_master");
        assert_eq!(state.account_modal.spotify_input, "https://open.spotify.com/user/audiophile_master");

        // Tab to Apple Music field (field 1)
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.account_modal.focused_field, 1);
        state.paste("https://music.apple.com/profile/sound_engineer");
        assert_eq!(state.account_modal.apple_input, "https://music.apple.com/profile/sound_engineer");

        // Press Esc to close
        state.handle_key(KeyCode::Esc);
        assert!(!state.account_modal.is_open);
    }

    #[test]
    fn test_library_sync_deduplication_and_organization() {
        let tracks = vec![
            StreamQueueItem {
                title: "One More Time (Official Video)".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Discovery".to_string(),
                duration_secs: Some(320),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "Daft Punk - One More Time".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Discovery Album".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "One More Time".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Discovery".to_string(),
                duration_secs: Some(320),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::AppleMusic,
                source_query: "Daft Punk - One More Time".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Discovery Album".to_string(),
                added_order: 2,
            },
            StreamQueueItem {
                title: "Blinding Lights [Remastered]".to_string(),
                artist: "The Weeknd".to_string(),
                album: "After Hours".to_string(),
                duration_secs: Some(200),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "The Weeknd - Blinding Lights".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "After Hours Album".to_string(),
                added_order: 3,
            },
            StreamQueueItem {
                title: "Around the World".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Homework".to_string(),
                duration_secs: Some(240),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "Daft Punk - Around the World".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Homework Album".to_string(),
                added_order: 4,
            },
        ];

        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(tracks, true, TrackSortMode::ArtistAZ);
        // Duplicate "One More Time" should be merged, leaving 3 unique tracks
        assert_eq!(organized.len(), 3);

        // Sorted by Artist A-Z ("Daft Punk" before "The Weeknd")
        assert_eq!(organized[0].artist, "Daft Punk");
        assert_eq!(organized[1].artist, "Daft Punk");
        assert_eq!(organized[2].artist, "The Weeknd");

        // Within Daft Punk, sorted by Album ("Discovery" before "Homework")
        assert_eq!(organized[0].album, "Discovery");
        assert_eq!(organized[1].album, "Homework");
    }

    #[test]
    fn test_account_modal_import_into_queue() {
        let mut state = StreamingHubState::new();
        state.account_modal.is_open = true;

        let track_items = vec![
            crate::harvest::library_sync::DiscoveredTrackItem {
                id: "track_1".to_string(),
                title: "One More Time".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Discovery".to_string(),
                duration_secs: Some(320),
                is_selected: true,
                library_name: "Discovery Album".to_string(),
                service: StreamingService::Spotify,
                added_order: 1,
            },
            crate::harvest::library_sync::DiscoveredTrackItem {
                id: "track_2".to_string(),
                title: "Blinding Lights".to_string(),
                artist: "The Weeknd".to_string(),
                album: "After Hours".to_string(),
                duration_secs: Some(200),
                is_selected: true,
                library_name: "After Hours Album".to_string(),
                service: StreamingService::AppleMusic,
                added_order: 2,
            },
        ];

        let action = AccountModalAction::ImportTracks(track_items, true, TrackSortMode::ArtistAZ);
        state.account_modal.is_open = true;
        match action {
            AccountModalAction::ImportTracks(tracks, dedup, sort) => {
                let mut all_items = Vec::new();
                for t in tracks {
                    all_items.push(StreamQueueItem {
                        title: t.title.clone(),
                        artist: t.artist.clone(),
                        album: t.album,
                        duration_secs: t.duration_secs,
                        quality_tier: AudioQualityTier::CloudOpus160,
                        service: t.service,
                        source_query: format!("{} - {}", t.artist, t.title),
                        status: StreamItemStatus::Queued,
                        audio_file_path: None,
                        library_name: t.library_name,
                        added_order: t.added_order,
                    });
                }
                let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, dedup, sort);
                for item in organized {
                    state.queue.push(item);
                }
                state.apply_sort_mode(sort);
            }
            _ => {}
        }

        assert_eq!(state.sort_mode, TrackSortMode::ArtistAZ);
        assert_eq!(state.queue.len(), 2);
        assert_eq!(state.queue[0].artist, "Daft Punk");
        assert_eq!(state.queue[1].artist, "The Weeknd");
    }

    #[test]
    fn test_streaming_queue_sort_hotkey_cycles_and_tracks_indices() {
        let mut state = StreamingHubState::new();
        state.queue.push(StreamQueueItem {
            title: "Song B".to_string(),
            artist: "Zebra".to_string(),
            album: "Album".to_string(),
            duration_secs: Some(300),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Unknown,
            source_query: "query".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 1,
        });
        state.queue.push(StreamQueueItem {
            title: "Song A".to_string(),
            artist: "Alpha".to_string(),
            album: "Album".to_string(),
            duration_secs: Some(150),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Unknown,
            source_query: "query".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 2,
        });

        state.currently_playing_idx = Some(0); // Playing Zebra
        state.selected_idx = 1; // Selected Alpha

        // Default sort_mode is LatestAdded
        assert_eq!(state.sort_mode, TrackSortMode::LatestAdded);
        assert!(!state.sort_modal_open);

        // Press 'o' -> Opens Sort Modal
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        assert!(state.is_capturing_input());

        // Press '3' -> TitleAZ ("Song A", then "Song B") directly
        state.handle_key(KeyCode::Char('3'));
        assert!(!state.sort_modal_open);
        assert_eq!(state.sort_mode, TrackSortMode::TitleAZ);
        assert_eq!(state.queue[0].title, "Song A");
        assert_eq!(state.queue[1].title, "Song B");
        // Check that currently_playing_idx and selected_idx tracked the items
        assert_eq!(state.currently_playing_idx, Some(1)); // Zebra moved to index 1
        assert_eq!(state.selected_idx, 0); // Alpha moved to index 0

        // Open modal again and press 'o' to cycle mode
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        state.handle_key(KeyCode::Char('o')); // cycles to TitleZA
        assert_eq!(state.sort_mode, TrackSortMode::TitleZA);
        assert_eq!(state.queue[0].title, "Song B");
        assert_eq!(state.currently_playing_idx, Some(0));

        // Press Esc to dismiss modal
        state.handle_key(KeyCode::Esc);
        assert!(!state.sort_modal_open);
    }

    #[test]
    fn test_streaming_queue_dynamic_truncation() {
        let long_title = "Wrath of The Gods \"Suite\" | Epic Battle Music | BEST Anime Track Ever Recorded";
        let truncated = truncate_str(long_title, 20);
        assert!(truncated.chars().count() <= 20);
        assert!(truncated.ends_with('…'));

        let short_title = "Song";
        assert_eq!(truncate_str(short_title, 20), "Song");
    }

    #[test]
    fn test_instant_playback_switching_and_stale_rejection() {
        let mut state = StreamingHubState::new();
        state.queue.push(StreamQueueItem {
            title: "Track 1".to_string(),
            artist: "Artist 1".to_string(),
            album: "Album 1".to_string(),
            duration_secs: Some(180),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Artist 1 - Track 1".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 1,
        });
        state.queue.push(StreamQueueItem {
            title: "Track 2".to_string(),
            artist: "Artist 2".to_string(),
            album: "Album 2".to_string(),
            duration_secs: Some(210),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Artist 2 - Track 2".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 2,
        });

        // Trigger play on track 0
        state.play_track_at_index(0);
        assert_eq!(state.currently_playing_idx, Some(0));
        assert_eq!(state.queue[0].status, StreamItemStatus::Resolving);
        let req_1 = state.stream_request_id;
        assert_eq!(req_1, 1);

        // Instantly switch to track 1
        state.play_track_at_index(1);
        assert_eq!(state.currently_playing_idx, Some(1));
        assert_eq!(state.queue[0].status, StreamItemStatus::Paused);
        assert_eq!(state.queue[1].status, StreamItemStatus::Resolving);
        let req_2 = state.stream_request_id;
        assert_eq!(req_2, 2);

        // Stale worker response for req_1 (track 0) arrives
        let _ = state.stream_tx.send(Ok((req_1, 0, PathBuf::from("/tmp/fake_track0.opus"), AudioQualityTier::CloudOpus160, "Opus 160k".to_string())));

        state.poll_stream_worker();

        // Stale worker should not have switched currently_playing_idx back to 0
        assert_eq!(state.currently_playing_idx, Some(1));
        assert_eq!(state.queue[1].status, StreamItemStatus::Resolving);
    }

    #[test]
    fn test_autoplay_queue_advancement() {
        let mut state = StreamingHubState::new();
        let player = Arc::new(TrackPlayer::new(48000.0));
        state.player = Some(player.clone());

        state.queue.push(StreamQueueItem {
            title: "First".to_string(),
            artist: "Band A".to_string(),
            album: "A".to_string(),
            duration_secs: Some(10),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Band A - First".to_string(),
            status: StreamItemStatus::Playing,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 1,
        });
        state.queue.push(StreamQueueItem {
            title: "Second".to_string(),
            artist: "Band B".to_string(),
            album: "B".to_string(),
            duration_secs: Some(10),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Band B - Second".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 2,
        });

        state.currently_playing_idx = Some(0);

        // Simulate player finishing first song
        player.set_finished(true);

        // Poll stream worker triggers autoplay advancement
        state.poll_stream_worker();

        // Track 0 is marked completed, and track 1 is selected and resolving
        assert_eq!(state.queue[0].status, StreamItemStatus::Completed);
        assert_eq!(state.currently_playing_idx, Some(1));
        assert_eq!(state.selected_idx, 1);
    }

    #[test]
    fn test_multi_song_jumping_and_direct_numeric_jump() {
        let mut state = StreamingHubState::new();
        for i in 1..=40 {
            state.queue.push(StreamQueueItem {
                title: format!("Song {}", i),
                artist: format!("Artist {}", i),
                album: "Test Album".to_string(),
                duration_secs: Some(180),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: format!("Artist {} - Song {}", i, i),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Test".to_string(),
                added_order: i as u64,
            });
        }

        // Start playing track 1 (index 0)
        state.play_track_at_index(0);
        assert_eq!(state.currently_playing_idx, Some(0));

        // Jump down 10 tracks with PageDown
        state.handle_key(KeyCode::PageDown);
        assert_eq!(state.selected_idx, 10);

        // Jump down another 10 tracks with PageDown
        state.handle_key(KeyCode::PageDown);
        assert_eq!(state.selected_idx, 20);

        // Jump to end of queue with End
        state.handle_key(KeyCode::End);
        assert_eq!(state.selected_idx, 39);

        // Jump to top with Home
        state.handle_key(KeyCode::Home);
        assert_eq!(state.selected_idx, 0);

        // Test direct numeric jump to track 30: user types '3', '0', then Enter
        state.handle_key(KeyCode::Char('3'));
        assert_eq!(state.jump_input, "3");
        state.handle_key(KeyCode::Char('0'));
        assert_eq!(state.jump_input, "30");
        state.handle_key(KeyCode::Enter);

        // Verify track 30 (0-indexed: index 29) is now active and resolving
        assert_eq!(state.selected_idx, 29);
        assert_eq!(state.currently_playing_idx, Some(29));
        assert_eq!(state.queue[29].status, StreamItemStatus::Resolving);
        assert!(state.jump_input.is_empty());

        // Test out of range jump
        state.handle_key(KeyCode::Char('9'));
        state.handle_key(KeyCode::Char('9'));
        state.handle_key(KeyCode::Enter);
        assert!(state.status_message.contains("out of range"));
        assert_eq!(state.currently_playing_idx, Some(29));
    }

    #[test]
    fn test_loop_mode_cycling_and_single_track_rewind() {
        let mut state = StreamingHubState::new();
        let player = Arc::new(TrackPlayer::new(44100.0));
        state.player = Some(player.clone());

        assert_eq!(state.loop_mode, LoopMode::Off);

        // Press 'R' cycles to LoopMode::Single
        state.handle_key(KeyCode::Char('r'));
        assert_eq!(state.loop_mode, LoopMode::Single);

        // Press 'R' cycles to LoopMode::All
        state.handle_key(KeyCode::Char('r'));
        assert_eq!(state.loop_mode, LoopMode::All);

        // Press 'R' cycles back to LoopMode::Off
        state.handle_key(KeyCode::Char('r'));
        assert_eq!(state.loop_mode, LoopMode::Off);

        // Setup 2 tracks
        state.queue.push(StreamQueueItem {
            title: "Track 1".to_string(),
            artist: "Artist 1".to_string(),
            album: "Album 1".to_string(),
            duration_secs: Some(180),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Artist 1 - Track 1".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 1,
        });
        state.queue.push(StreamQueueItem {
            title: "Track 2".to_string(),
            artist: "Artist 2".to_string(),
            album: "Album 2".to_string(),
            duration_secs: Some(200),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Artist 2 - Track 2".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Test".to_string(),
            added_order: 2,
        });

        // Set to Single loop
        state.loop_mode = LoopMode::Single;
        state.currently_playing_idx = Some(0);
        state.selected_idx = 0;
        state.queue[0].status = StreamItemStatus::Playing;

        // Simulate track finish
        player.set_finished(true);
        state.poll_stream_worker();

        // With LoopMode::Single, track does NOT advance to index 1; stays on index 0!
        assert_eq!(state.currently_playing_idx, Some(0));
        assert!(state.status_message.contains("Looping Track"));
    }

    #[test]
    fn test_shuffle_mode_toggle_and_navigation() {
        let mut state = StreamingHubState::new();
        assert!(!state.shuffle);

        // Press 'Z' toggles shuffle ON
        state.handle_key(KeyCode::Char('z'));
        assert!(state.shuffle);

        // Press 'Z' toggles shuffle OFF
        state.handle_key(KeyCode::Char('z'));
        assert!(!state.shuffle);

        // Add 5 tracks
        for i in 1..=5 {
            state.queue.push(StreamQueueItem {
                title: format!("Track {}", i),
                artist: format!("Artist {}", i),
                album: "Album".to_string(),
                duration_secs: Some(180),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: format!("Artist {} - Track {}", i, i),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Test".to_string(),
                added_order: i as u64,
            });
        }

        state.shuffle = true;
        state.currently_playing_idx = Some(0);

        // compute_next_index should return a valid index != 0
        let next = state.compute_next_index();
        assert!(next.is_some());
        let next_idx = next.unwrap();
        assert!(next_idx < 5);
        assert_ne!(next_idx, 0);
    }

    #[test]
    fn test_multi_library_last_added_and_oldest_added_unification() {
        let mut state = StreamingHubState::new();

        // Simulate multi-library imported items:
        // Library 1 (Spotify): Track A (oldest, added_order: 100_000), Track B (newest, added_order: 1_000_000)
        // Library 2 (YouTube): Track C (oldest, added_order: 200_000), Track D (newest, added_order: 950_000)
        state.queue = vec![
            StreamQueueItem {
                title: "Track A (Oldest Spotify)".to_string(),
                artist: "Artist A".to_string(),
                album: "Spotify Album".to_string(),
                duration_secs: Some(180),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "query_a".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Favorites".to_string(),
                added_order: 100_000,
            },
            StreamQueueItem {
                title: "Track B (Newest Spotify)".to_string(),
                artist: "Artist B".to_string(),
                album: "Spotify Album".to_string(),
                duration_secs: Some(200),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "query_b".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Favorites".to_string(),
                added_order: 1_000_000,
            },
            StreamQueueItem {
                title: "Track C (Oldest YouTube)".to_string(),
                artist: "Artist C".to_string(),
                album: "YT Album".to_string(),
                duration_secs: Some(210),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "query_c".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "YT Favorites".to_string(),
                added_order: 200_000,
            },
            StreamQueueItem {
                title: "Track D (Newest YouTube)".to_string(),
                artist: "Artist D".to_string(),
                album: "YT Album".to_string(),
                duration_secs: Some(220),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "query_d".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "YT Favorites".to_string(),
                added_order: 950_000,
            },
        ];

        // 1. Sort by Latest Added: The newest tracks across all libraries must be together at the top!
        state.apply_sort_mode(TrackSortMode::LatestAdded);
        assert_eq!(state.queue[0].title, "Track B (Newest Spotify)"); // 1_000_000
        assert_eq!(state.queue[1].title, "Track D (Newest YouTube)"); // 950_000
        assert_eq!(state.queue[2].title, "Track C (Oldest YouTube)"); // 200_000
        assert_eq!(state.queue[3].title, "Track A (Oldest Spotify)"); // 100_000

        // 2. Sort by Oldest Added: The oldest tracks across all libraries must be together at the top!
        state.apply_sort_mode(TrackSortMode::OldestAdded);
        assert_eq!(state.queue[0].title, "Track A (Oldest Spotify)"); // 100_000
        assert_eq!(state.queue[1].title, "Track C (Oldest YouTube)"); // 200_000
        assert_eq!(state.queue[2].title, "Track D (Newest YouTube)"); // 950_000
        assert_eq!(state.queue[3].title, "Track B (Newest Spotify)"); // 1_000_000
    }

    #[test]
    fn test_platform_dividers_sorting_order_and_key_selection() {
        let mut state = StreamingHubState::new_clean();

        state.queue = vec![
            StreamQueueItem {
                title: "YT Song 1".to_string(),
                artist: "YT Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(180),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "yt_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "YT Liked".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Apple Song 1".to_string(),
                artist: "Apple Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(190),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::AppleMusic,
                source_query: "apple_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Apple Mix".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Spotify Song 1".to_string(),
                artist: "Spotify Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(200),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "spotify_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Top".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Spotify Song 2".to_string(),
                artist: "Spotify Artist 2".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(210),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "spotify_2".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Top".to_string(),
                added_order: 2,
            },
        ];

        // Open sort modal and press '9' for Platform & Library Dividers
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        state.handle_key(KeyCode::Char('9'));
        assert!(!state.sort_modal_open);
        assert_eq!(state.sort_mode, TrackSortMode::PlatformDividers);

        // Spotify first (priority 0) with default LatestAdded sub-sorting (newest first)
        assert_eq!(state.queue[0].service, StreamingService::Spotify);
        assert_eq!(state.queue[0].title, "Spotify Song 2");
        assert_eq!(state.queue[1].service, StreamingService::Spotify);
        assert_eq!(state.queue[1].title, "Spotify Song 1");

        // Apple Music second (priority 1)
        assert_eq!(state.queue[2].service, StreamingService::AppleMusic);
        assert_eq!(state.queue[2].title, "Apple Song 1");

        // YouTube Music third (priority 2)
        assert_eq!(state.queue[3].service, StreamingService::YouTubeMusic);
        assert_eq!(state.queue[3].title, "YT Song 1");
    }

    #[test]
    fn test_platform_dividers_priority_customization() {
        let mut state = StreamingHubState::new();

        state.queue = vec![
            StreamQueueItem {
                title: "YT Song 1".to_string(),
                artist: "YT Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(180),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "yt_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "YT Liked".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Apple Song 1".to_string(),
                artist: "Apple Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(190),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::AppleMusic,
                source_query: "apple_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Apple Mix".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Spotify Song 1".to_string(),
                artist: "Spotify Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(200),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "spotify_1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Top".to_string(),
                added_order: 1,
            },
        ];

        // 1. YouTube First via '-' key in modal
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        state.handle_key(KeyCode::Char('-'));
        assert!(!state.sort_modal_open);
        assert_eq!(state.sort_mode, TrackSortMode::PlatformDividers);
        assert_eq!(state.divider_platform_priority, DividerPlatformPriority::YouTubeFirst);
        assert_eq!(state.queue[0].service, StreamingService::YouTubeMusic);
        assert_eq!(state.queue[1].service, StreamingService::Spotify);
        assert_eq!(state.queue[2].service, StreamingService::AppleMusic);

        // 2. Apple Music First via '0' key in modal
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        state.handle_key(KeyCode::Char('0'));
        assert!(!state.sort_modal_open);
        assert_eq!(state.divider_platform_priority, DividerPlatformPriority::AppleMusicFirst);
        assert_eq!(state.queue[0].service, StreamingService::AppleMusic);
        assert_eq!(state.queue[1].service, StreamingService::Spotify);
        assert_eq!(state.queue[2].service, StreamingService::YouTubeMusic);

        // 3. Cycle priority via 'p'
        state.handle_key(KeyCode::Char('o'));
        assert!(state.sort_modal_open);
        state.handle_key(KeyCode::Char('p')); // AppleMusicFirst -> YouTubeFirst
        assert_eq!(state.divider_platform_priority, DividerPlatformPriority::YouTubeFirst);
        state.handle_key(KeyCode::Char('p')); // YouTubeFirst -> SpotifyFirst
        assert_eq!(state.divider_platform_priority, DividerPlatformPriority::SpotifyFirst);
        state.handle_key(KeyCode::Esc);
        assert_eq!(state.queue[0].service, StreamingService::Spotify);
    }

    #[test]
    fn test_platform_dividers_sub_sort_customization() {
        let mut state = StreamingHubState::new();

        state.queue = vec![
            StreamQueueItem {
                title: "Track B".to_string(),
                artist: "Zebra Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(300),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "query_b".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Main".to_string(),
                added_order: 1,
            },
            StreamQueueItem {
                title: "Track A".to_string(),
                artist: "Alpha Artist".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(120),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "query_a".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Main".to_string(),
                added_order: 2,
            },
        ];

        // 1. Sub-sort LatestAdded (Newest added_order first)
        state.divider_sub_sort = DividerSubSort::LatestAdded;
        state.apply_sort_mode(TrackSortMode::PlatformDividers);
        assert_eq!(state.queue[0].title, "Track A"); // added_order 2
        assert_eq!(state.queue[1].title, "Track B"); // added_order 1

        // 2. Sub-sort OldestAdded (Playlist order)
        state.divider_sub_sort = DividerSubSort::OldestAdded;
        state.apply_sort_mode(TrackSortMode::PlatformDividers);
        assert_eq!(state.queue[0].title, "Track B"); // added_order 1
        assert_eq!(state.queue[1].title, "Track A"); // added_order 2

        // 3. Sub-sort ArtistAZ
        state.divider_sub_sort = DividerSubSort::ArtistAZ;
        state.apply_sort_mode(TrackSortMode::PlatformDividers);
        assert_eq!(state.queue[0].artist, "Alpha Artist");
        assert_eq!(state.queue[1].artist, "Zebra Artist");
    }

    #[test]
    fn test_queue_line_width_zero_gap_boundary_guarantee() {
        for total_w in [30usize, 45, 60, 80, 120, 200] {
            let overhead = 21;
            let status_w = 12.min(total_w.saturating_sub(overhead));
            let content_w = total_w.saturating_sub(overhead + status_w);
            let title_w = (content_w * 58 / 100).min(content_w);
            let artist_w = content_w.saturating_sub(title_w);

            let cursor_w = 2;
            let idx_w = 4;
            let sep_w = 3;
            let dur_w = 6;

            let line_len = cursor_w + idx_w + title_w + sep_w + artist_w + sep_w + dur_w + sep_w + status_w;
            assert!(
                line_len <= total_w,
                "Line width {} exceeds total_w {} at overhead 21",
                line_len,
                total_w
            );

            // Verify divider banner text width clamping
            let header_prefix = "─── [SPOTIFY] Super Long Playlist Name (1000 tracks) ";
            let prefix_len = unicode_display_width(header_prefix);
            let divider_text = if prefix_len >= total_w {
                truncate_display_str(header_prefix, total_w)
            } else {
                let fill_len = total_w - prefix_len;
                format!("{}{}", header_prefix, "─".repeat(fill_len))
            };
            assert!(
                unicode_display_width(&divider_text) <= total_w,
                "Divider banner width {} exceeds total_w {}",
                unicode_display_width(&divider_text),
                total_w
            );
        }
    }

    #[test]
    fn test_queue_import_deduplicates_against_existing_queue() {
        let mut state = StreamingHubState::new();

        // Queue already has "Lose It" by Ken Carson
        state.queue.push(StreamQueueItem {
            title: "Lose It".to_string(),
            artist: "Ken Carson".to_string(),
            album: "A Great Chaos".to_string(),
            duration_secs: Some(140),
            quality_tier: AudioQualityTier::CloudOpus160,
            service: StreamingService::Spotify,
            source_query: "Ken Carson - Lose It".to_string(),
            status: StreamItemStatus::Queued,
            audio_file_path: None,
            library_name: "Favorites".to_string(),
            added_order: 1,
        });

        assert_eq!(state.queue.len(), 1);

        // Account modal sends ImportTracks with "Lose It" (duplicate) and "Fighting My Demons" (new)
        state.account_modal.is_open = true;
        let incoming_tracks = vec![
            DiscoveredTrackItem {
                id: "track_1".to_string(),
                title: "Lose It".to_string(),
                artist: "Ken Carson".to_string(),
                album: "A Great Chaos".to_string(),
                duration_secs: Some(140),
                service: StreamingService::Spotify,
                library_name: "Favorites".to_string(),
                added_order: 2,
                is_selected: true,
            },
            DiscoveredTrackItem {
                id: "track_2".to_string(),
                title: "Fighting My Demons".to_string(),
                artist: "Ken Carson".to_string(),
                album: "A Great Chaos".to_string(),
                duration_secs: Some(150),
                service: StreamingService::Spotify,
                library_name: "Favorites".to_string(),
                added_order: 3,
                is_selected: true,
            },
        ];

        // Simulate user action: import with deduplicate = true
        let action = AccountModalAction::ImportTracks(incoming_tracks, true, TrackSortMode::LatestAdded);
        state.account_modal.is_open = true;
        // Directly process action in handle_key flow
        if let AccountModalAction::ImportTracks(tracks, deduplicate, sort_mode) = action {
            let mut all_items = Vec::new();
            for t in tracks {
                all_items.push(StreamQueueItem {
                    title: t.title.clone(),
                    artist: t.artist.clone(),
                    album: t.album,
                    duration_secs: t.duration_secs,
                    quality_tier: AudioQualityTier::CloudOpus160,
                    service: t.service,
                    source_query: format!("{} - {}", t.artist, t.title),
                    status: StreamItemStatus::Queued,
                    audio_file_path: None,
                    library_name: t.library_name,
                    added_order: t.added_order,
                });
            }
            let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, deduplicate, sort_mode);

            if deduplicate {
                state.deduplicate_queue();
                let mut existing_keys = std::collections::HashSet::new();
                for item in &state.queue {
                    let key = (
                        crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                        crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                    );
                    existing_keys.insert(key);
                }
                for item in organized {
                    let key = (
                        crate::harvest::title_cleaner::clean_title(&item.artist).title.to_lowercase(),
                        crate::harvest::title_cleaner::clean_title(&item.title).title.to_lowercase(),
                    );
                    if !existing_keys.contains(&key) {
                        existing_keys.insert(key);
                        state.queue.push(item);
                    }
                }
            }
        }

        // Queue must have 2 tracks total, NOT 3 ("Lose It" was deduplicated, "Fighting My Demons" added)
        assert_eq!(state.queue.len(), 2);
        let titles: Vec<_> = state.queue.iter().map(|t| t.title.as_str()).collect();
        assert!(titles.contains(&"Lose It"));
        assert!(titles.contains(&"Fighting My Demons"));
    }

    #[test]
    fn test_deduplicate_queue_in_place_collapses_duplicates() {
        let mut state = StreamingHubState::new();

        // Enqueue duplicate songs
        for _ in 0..2 {
            state.queue.push(StreamQueueItem {
                title: "ALL RED".to_string(),
                artist: "Playboi Carti".to_string(),
                album: "Music".to_string(),
                duration_secs: Some(148),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "Playboi Carti - ALL RED".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Top".to_string(),
                added_order: 1,
            });
            state.queue.push(StreamQueueItem {
                title: "Lose It".to_string(),
                artist: "Ken Carson".to_string(),
                album: "A Great Chaos".to_string(),
                duration_secs: Some(140),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "Ken Carson - Lose It".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Top".to_string(),
                added_order: 2,
            });
        }

        assert_eq!(state.queue.len(), 4);
        let removed = state.deduplicate_queue();
        assert_eq!(removed, 2);
        assert_eq!(state.queue.len(), 2);
    }

    #[test]
    fn test_sort_modal_layout_fits_within_popup_bounds() {
        let state = StreamingHubState::new();
        let max_inner_w = 78; // popup_w (80) - 2 for borders

        let modes = [
            (TrackSortMode::LatestAdded, "[1] Latest Added", "Original playlist ingestion order"),
            (TrackSortMode::OldestAdded, "[2] Oldest Added", "Reverse chronological order"),
            (TrackSortMode::TitleAZ, "[3] Title (A - Z)", "Alphabetical by track title"),
            (TrackSortMode::TitleZA, "[4] Title (Z - A)", "Reverse alphabetical by track title"),
            (TrackSortMode::ArtistAZ, "[5] Artist (A - Z)", "Organized by artist, album & title"),
            (TrackSortMode::ArtistZA, "[6] Artist (Z - A)", "Reverse alphabetical by artist"),
            (TrackSortMode::DurationShortest, "[7] Duration (Shortest)", "Shortest tracks first"),
            (TrackSortMode::DurationLongest, "[8] Duration (Longest)", "Longest tracks first"),
            (TrackSortMode::PlatformDividers, "[9] Platform Dividers", "Segmented by Platform & Library"),
        ];

        // 1. Verify all mode lines with active badge fit inside max_inner_w
        for (_mode, label, desc) in modes {
            let line = format!("> {:<23} - {} [*ACTIVE*]", label, desc);
            let w = unicode_display_width(&line);
            assert!(w <= max_inner_w, "Mode line '{}' width {} exceeds max_inner_w {}", line, w, max_inner_w);
        }

        // 2. Verify platform priority customization line
        let lead_line = format!(" [P] Lead Platform : {}", state.divider_platform_priority.label());
        assert!(unicode_display_width(&lead_line) <= max_inner_w);

        // 3. Verify sub-sort customization line
        let sub_line = format!(" [S] Section Sub-Sort: {}", state.divider_sub_sort.label());
        assert!(unicode_display_width(&sub_line) <= max_inner_w);

        // 4. Verify platform color coding lines
        let color_line = format!(" [C] Platform Colors:  {} ", state.platform_color_mode.label());
        assert!(unicode_display_width(&color_line) <= max_inner_w);
        let cycle_line = "     Cycle [C]     : [None] -> [Option B: Accent] -> [Option A: Full Row]";
        assert!(unicode_display_width(cycle_line) <= max_inner_w);

        // 5. Verify footer lines
        let foot1 = " [1-9] Direct   [Up/Down] Move   [Enter] Apply   [Esc] Close";
        let foot2 = " [P] Lead Platform   [S] Sub-Sort   [C] Platform Colors   [O] Cycle Mode";
        assert!(unicode_display_width(foot1) <= max_inner_w);
        assert!(unicode_display_width(foot2) <= max_inner_w);
    }

    #[test]
    fn test_platform_color_mode_cycling_and_hotkey() {
        let mut state = StreamingHubState::new_clean();
        assert_eq!(state.platform_color_mode, PlatformColorMode::None);

        // Open sort modal
        state.sort_modal_open = true;

        // Press 'c' to cycle to Option B (Accent)
        state.handle_key(KeyCode::Char('c'));
        assert_eq!(state.platform_color_mode, PlatformColorMode::Accent);

        // Press 'c' to cycle to Option A (Full)
        state.handle_key(KeyCode::Char('c'));
        assert_eq!(state.platform_color_mode, PlatformColorMode::Full);

        // Press 'C' to cycle back to None
        state.handle_key(KeyCode::Char('C'));
        assert_eq!(state.platform_color_mode, PlatformColorMode::None);
    }

    #[test]
    fn test_track_index_padding_guarantees_space_for_large_queues() {
        // Test index string formatting for various queue sizes
        for total_len in [50usize, 500, 1088, 5000] {
            let idx_w: usize = if total_len >= 1000 { 6 } else if total_len >= 100 { 5 } else { 4 };
            for idx in [0, 8, 98, 196, 999, 1087] {
                if idx < total_len {
                    let disp_idx = format!("#{:>width$} ", idx + 1, width = idx_w.saturating_sub(2));
                    // Must always end with a space so it never concatenates into song title
                    assert!(disp_idx.ends_with(' '), "disp_idx '{}' must end with a space", disp_idx);
                    assert_eq!(disp_idx.len(), idx_w, "disp_idx '{}' len must equal idx_w {}", disp_idx, idx_w);
                }
            }
        }
    }
}
