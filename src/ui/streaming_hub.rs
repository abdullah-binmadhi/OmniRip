//! Workstation 4: Cloud Streaming Hub & Universal Music Player
//!
//! Provides a unified music player for Spotify, Apple Music, YouTube Music,
//! and freeform search queries, streaming audio via high-bitrate Opus streams,
//! persisting user-calibrated volume levels, and routing audio through OmniRip's
//! 16-module mastering DSP rack and real-time spectrum telemetry engine.

use crate::dsp::player::TrackPlayer;
use crate::harvest::library_sync::LibrarySyncEngine;
use crate::harvest::playlist_parser::{PlaylistParser, StreamingService};
use crate::harvest::stream_resolver::{AudioQualityTier, StreamResolver};
use crate::ui::account_modal::{AccountModalAction, AccountSyncModal};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};
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

pub struct StreamingHubState {
    pub search_input: String,
    pub is_editing_search: bool,
    pub queue: Vec<StreamQueueItem>,
    pub selected_idx: usize,
    pub queue_list_state: ListState,
    pub player: Option<Arc<TrackPlayer>>,
    pub status_message: String,
    pub live_spectrum: [f32; 32],
    pub stream_rx: Option<Receiver<StreamWorkerResult>>,
    pub currently_playing_idx: Option<usize>,
    pub account_modal: AccountSyncModal,
    pub dsp_telemetry: DspTelemetryInfo,
    pub stream_request_id: u64,
    pub jump_input: String,
}

impl Default for StreamingHubState {
    fn default() -> Self {
        Self::new()
    }
}

impl StreamingHubState {
    pub fn new() -> Self {
        Self {
            search_input: String::new(),
            is_editing_search: false,
            queue: Vec::new(),
            selected_idx: 0,
            queue_list_state: ListState::default(),
            player: None,
            status_message: "Universal Streaming Hub ready. [S] Search/Paste  [L] Link Accounts & Import Library".to_string(),
            live_spectrum: [-60.0; 32],
            stream_rx: None,
            currently_playing_idx: None,
            account_modal: AccountSyncModal::new(),
            dsp_telemetry: DspTelemetryInfo::default(),
            stream_request_id: 0,
            jump_input: String::new(),
        }
    }

    pub fn is_capturing_input(&self) -> bool {
        self.is_editing_search || self.account_modal.is_open
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
                    return;
                }
            }
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        if self.account_modal.is_open {
            if let Some(action) = self.account_modal.handle_key(code) {
                match action {
                    AccountModalAction::ImportCollections(collections, deduplicate, sort_by_artist) => {
                        let browser = self.account_modal.selected_browser();
                        let mut all_items = Vec::new();
                        for col in &collections {
                            if let Ok(tracks) = LibrarySyncEngine::fetch_tracks_for_collection(col, &browser) {
                                for t in tracks {
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
                                    });
                                }
                            }
                        }

                        // Deduplicate and organize tracks
                        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, deduplicate, sort_by_artist);
                        let total_imported = organized.len();

                        for item in organized {
                            self.queue.push(item);
                        }

                        if self.currently_playing_idx.is_none() && !self.queue.is_empty() {
                            self.play_track_at_index(0);
                        }
                        self.status_message = format!("Linked Library Sync: imported {} unique track(s) from {} collection(s).", total_imported, collections.len());
                    }
                    AccountModalAction::ImportTracks(tracks, deduplicate, sort_by_artist) => {
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
                                service: StreamingService::YouTubeMusic,
                                source_query: query,
                                status: StreamItemStatus::Queued,
                                audio_file_path: None,
                            });
                        }

                        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, deduplicate, sort_by_artist);
                        let total_imported = organized.len();

                        for item in organized {
                            self.queue.push(item);
                        }

                        if self.currently_playing_idx.is_none() && !self.queue.is_empty() {
                            self.play_track_at_index(0);
                        }
                        self.status_message = format!("Imported {} selected track(s) to streaming queue.", total_imported);
                    }
                    AccountModalAction::Close => {
                        self.status_message = "Closed Account Sync modal.".to_string();
                    }
                }
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
                    self.queue_list_state.select(Some(self.selected_idx));
                }
            }
            KeyCode::Down | KeyCode::Char('j') => {
                self.jump_input.clear();
                if !self.queue.is_empty() && self.selected_idx + 1 < self.queue.len() {
                    self.selected_idx += 1;
                    self.queue_list_state.select(Some(self.selected_idx));
                }
            }
            KeyCode::PageDown | KeyCode::Char('J') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = (self.selected_idx + 10).min(self.queue.len() - 1);
                    self.queue_list_state.select(Some(self.selected_idx));
                    self.status_message = format!("Jumped to track #{}/{}", self.selected_idx + 1, self.queue.len());
                }
            }
            KeyCode::PageUp | KeyCode::Char('K') => {
                self.jump_input.clear();
                if !self.queue.is_empty() {
                    self.selected_idx = self.selected_idx.saturating_sub(10);
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
                if let Some(ref p) = self.player {
                    p.restart();
                    self.status_message = "Restarted current stream from 0:00.".to_string();
                }
            }
            KeyCode::Char('d') | KeyCode::Char('D') | KeyCode::Delete => {
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

            let rt = tokio::runtime::Handle::try_current();
            let res = if let Ok(handle) = rt {
                thread::spawn(move || {
                    handle.block_on(async move {
                        parser.parse_url_or_path(&query_clone).await
                    })
                }).join().unwrap_or_else(|_| Err("Thread error".to_string()))
            } else {
                Err("Tokio runtime unavailable".to_string())
            };

            match res {
                Ok(playlist) => {
                    let count = playlist.tracks.len();
                    for t in playlist.tracks {
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
        });

        let new_idx = self.queue.len() - 1;
        self.selected_idx = new_idx;
        self.queue_list_state.select(Some(new_idx));
        self.status_message = format!("Added '{} - {}' to streaming queue.", artist, title);

        if self.currently_playing_idx.is_none() {
            self.play_track_at_index(new_idx);
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

        if let Some(path) = existing_path {
            if path.exists() {
                if let Some(ref p) = self.player {
                    if p.load_file(&path).is_ok() {
                        p.play();
                        if let Some(item) = self.queue.get_mut(idx) {
                            item.status = StreamItemStatus::Playing;
                        }
                        self.status_message = format!("Playing: {} - {} [Instant Cache / Active DSP]", artist, title);
                        return;
                    }
                }
            }
        }

        if let Some(item) = self.queue.get_mut(idx) {
            item.status = StreamItemStatus::Resolving;
        }
        self.status_message = format!("Resolving cloud audio stream for '{} - {}'...", artist, title);

        self.stream_request_id += 1;
        let req_id = self.stream_request_id;
        let (tx, rx): (Sender<StreamWorkerResult>, Receiver<StreamWorkerResult>) = channel();
        self.stream_rx = Some(rx);

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
        let next_idx = match self.currently_playing_idx {
            Some(curr) if curr + 1 < self.queue.len() => curr + 1,
            _ => 0,
        };
        self.selected_idx = next_idx;
        self.queue_list_state.select(Some(next_idx));
        self.play_track_at_index(next_idx);
    }

    pub fn play_previous(&mut self) {
        if self.queue.is_empty() {
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
        if let Some(rx) = &self.stream_rx {
            if let Ok(result) = rx.try_recv() {
                self.stream_rx = None;
                match result {
                    Ok((req_id, idx, path, tier, fmt_label)) => {
                        if let Some(item) = self.queue.get_mut(idx) {
                            item.audio_file_path = Some(path.clone());
                            item.quality_tier = tier;
                        }
                        // Only load and start playback if this response matches the active request
                        if req_id == self.stream_request_id {
                            if let Some(item) = self.queue.get_mut(idx) {
                                item.status = StreamItemStatus::Playing;
                            }
                            if let Some(ref p) = self.player {
                                if p.load_file(&path).is_ok() {
                                    p.play();
                                    self.currently_playing_idx = Some(idx);
                                    if let Some(item) = self.queue.get(idx) {
                                        self.status_message = format!("Now Streaming: {} - {} [{} | DSP Rack Active]", item.artist, item.title, fmt_label);
                                    }
                                }
                            }
                        }
                    }
                    Err((req_id, idx, err)) => {
                        if req_id == self.stream_request_id {
                            if let Some(item) = self.queue.get_mut(idx) {
                                item.status = StreamItemStatus::Failed(err.clone());
                            }
                            self.status_message = format!("Stream resolution failed: {}", err);
                        }
                    }
                }
            }
        }

        // Autoplay: When current track finishes playing, advance to next track
        if let Some(ref p) = self.player {
            if p.consume_finished() {
                if let Some(curr) = self.currently_playing_idx {
                    if let Some(item) = self.queue.get_mut(curr) {
                        item.status = StreamItemStatus::Completed;
                    }
                    if curr + 1 < self.queue.len() {
                        self.play_next();
                    } else {
                        p.stop();
                        self.status_message = "Queue finished. Autoplay idle.".to_string();
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
        let title_str = format!(" [2] UNIFIED STREAMING QUEUE ({} tracks) ", self.queue.len());
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
        let overhead = 32; // Cursor(2) + Index(4) + Dividers(6) + Duration(6) + Status(14)
        let rem_w = total_w.saturating_sub(overhead);
        let title_w = (rem_w * 60 / 100).max(18);
        let artist_w = rem_w.saturating_sub(title_w).max(14);

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
                    .map(|d| format!("{:02}:{:02}", d / 60, d % 60))
                    .unwrap_or_else(|| "--:--".to_string());

                let status_span = match &item.status {
                    StreamItemStatus::Playing => Span::styled("[PLAYING ♫]", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
                    StreamItemStatus::Paused => Span::styled("[PAUSED]", Style::default().fg(Color::Yellow)),
                    StreamItemStatus::Resolving => Span::styled("[RESOLVING...]", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                    StreamItemStatus::Failed(err) => Span::styled(format!("[FAIL: {}]", truncate_str(err, 10)), Style::default().fg(Color::LightRed)),
                    _ => Span::styled(item.status.label(), Style::default().fg(theme.text_dim)),
                };

                let title_style = if is_current {
                    Style::default().fg(theme.success).add_modifier(Modifier::BOLD)
                } else if is_selected {
                    Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(theme.text)
                };

                let disp_title = pad_display_str(&item.title, title_w);
                let disp_artist = pad_display_str(&item.artist, artist_w);

                let line = Line::from(vec![
                    Span::styled(cursor, if is_selected { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                    Span::styled(format!("#{:02} ", idx + 1), Style::default().fg(theme.text_dim)),
                    Span::styled(disp_title, title_style),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(disp_artist, Style::default().fg(theme.text_dim)),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(format!("{} ", dur_str), Style::default().fg(theme.accent)),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    status_span,
                ]);

                let bg_style = if is_selected {
                    Style::default().bg(Color::Rgb(30, 35, 45))
                } else {
                    Style::default()
                };

                ListItem::new(line).style(bg_style)
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

        let bar_width: usize = 24;
        let filled = (progress_pct * bar_width as f32).round() as usize;
        let empty = bar_width.saturating_sub(filled);
        let progress_bar = format!("[{}{}]", "█".repeat(filled), "░".repeat(empty));

        let cur_str = format!("{:02}:{:02}", (cur_secs as u32) / 60, (cur_secs as u32) % 60);
        let total_str = format!("{:02}:{:02}", (total_secs as u32) / 60, (total_secs as u32) % 60);

        let tier_color = match tier {
            AudioQualityTier::HiResFlac24 => Color::Rgb(255, 215, 0),
            AudioQualityTier::CdFlac16 => Color::Cyan,
            AudioQualityTier::StudioLossy320 => Color::Green,
            AudioQualityTier::CloudOpus160 => Color::Magenta,
            AudioQualityTier::CloudAac128 => Color::White,
        };

        let lines = vec![
            Line::from(vec![
                Span::styled(" Track:    ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(title, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" Artist:   ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(artist, Style::default().fg(theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" Quality:  ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("[{}] ", tier.label()), Style::default().fg(tier_color).add_modifier(Modifier::BOLD)),
                Span::styled(format!("{} kHz • {} kbps ", tier.sample_rate_hz() / 1000, tier.nominal_bitrate_kbps()), Style::default().fg(theme.accent)),
                Span::raw("| Status: "),
                Span::styled(status_str, Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
                if !tier.is_lossless() {
                    Span::styled(" [DSP Restorer: Active]", Style::default().fg(Color::Yellow))
                } else {
                    Span::styled(" [Bit-Perfect Lossless PCM]", Style::default().fg(Color::Cyan))
                },
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled(" Progress: ", Style::default().fg(theme.text_dim)),
                Span::styled(progress_bar, Style::default().fg(theme.primary)),
                Span::styled(format!(" {} / {}", cur_str, total_str), Style::default().fg(theme.text)),
            ]),
            Line::from(vec![
                Span::styled(" Volume:   ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("[{:>3}%] (Persisted Safe Level) ", vol_pct), Style::default().fg(if vol_pct > 80 { Color::Yellow } else { theme.success }).add_modifier(Modifier::BOLD)),
                Span::styled("([+] / [-])", Style::default().fg(theme.accent)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("--- SYSTEM EQ (WORKSTATION 2) & DSP RECIPE ---", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" Active Preset: ", Style::default().fg(theme.text_dim)),
                Span::styled(if self.dsp_telemetry.active_preset_name.is_empty() { "Flat Studio Reference" } else { &self.dsp_telemetry.active_preset_name }, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Span::raw(" ("),
                Span::styled(format!("{} Filters", self.dsp_telemetry.filter_count), Style::default().fg(theme.accent)),
                Span::raw(")"),
            ]),
            Line::from(vec![
                Span::styled(" Target Curve:  ", Style::default().fg(theme.text_dim)),
                Span::styled(if self.dsp_telemetry.target_curve.is_empty() { "Harman Target Curve" } else { &self.dsp_telemetry.target_curve }, Style::default().fg(Color::Cyan)),
            ]),
            Line::from(vec![
                Span::styled(" Calibrated Gear: ", Style::default().fg(theme.text_dim)),
                Span::styled(if self.dsp_telemetry.active_gear_model.is_empty() { "Auto-Calibrated Output" } else { &self.dsp_telemetry.active_gear_model }, Style::default().fg(theme.primary)),
            ]),
            Line::from(vec![
                Span::styled(" DSP Recipe:    ", Style::default().fg(theme.text_dim)),
                Span::styled(format!("Preamp {:+.1}dB • Warmth {:.0}% • Width {:.0}% • Ceiling {:+.1}dB",
                    self.dsp_telemetry.preamp_db,
                    self.dsp_telemetry.tube_warmth * 100.0,
                    self.dsp_telemetry.spatial_width * 100.0,
                    self.dsp_telemetry.limiter_ceiling_db), Style::default().fg(theme.secondary)),
            ]),
            Line::from(vec![
                Span::styled(" Signal Chain:  ", Style::default().fg(theme.text_dim)),
                Span::styled("Lossless PCM -> System DSP Rack -> Pure Rust Engine", Style::default().fg(theme.success)),
            ]),
        ];

        let p = Paragraph::new(lines).wrap(Wrap { trim: true });
        f.render_widget(p, inner);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let line1 = Line::from(vec![
            Span::styled(" [S] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Search/Paste  "),
            Span::styled(" [L] ", Style::default().fg(Color::Rgb(255, 140, 200)).add_modifier(Modifier::BOLD)),
            Span::raw("Link Accounts  "),
            Span::styled(" [Enter] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::raw("Play  "),
            Span::styled(" [Space] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::raw("Pause/Resume  "),
            Span::styled(" [PgUp/Dn] ", Style::default().fg(Color::Rgb(100, 200, 255)).add_modifier(Modifier::BOLD)),
            Span::raw("Jump ±10  "),
            Span::styled(" [0-9] ", Style::default().fg(Color::Rgb(255, 215, 0)).add_modifier(Modifier::BOLD)),
            Span::raw("Go to #"),
        ]);

        let line2 = Line::from(vec![
            Span::styled(" [+/-] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("Vol  "),
            Span::styled(" [N] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Next  "),
            Span::styled(" [P] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Prev  "),
            Span::styled(" [E] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("Preset  "),
            Span::styled(" [R] ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
            Span::raw("Restart  "),
            Span::styled(" [D] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::raw("Remove Track  "),
            Span::styled(" [C] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::raw("Clear Queue  "),
            Span::styled(" [M] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::raw("Mode Select"),
        ]);

        let p = Paragraph::new(vec![line1, line2])
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p, area);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
    }

    #[test]
    fn test_account_sync_modal_toggle_and_paste() {
        let mut state = StreamingHubState::new();
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
            },
        ];

        let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(tracks, true, true);
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
            },
            crate::harvest::library_sync::DiscoveredTrackItem {
                id: "track_2".to_string(),
                title: "Blinding Lights".to_string(),
                artist: "The Weeknd".to_string(),
                album: "After Hours".to_string(),
                duration_secs: Some(200),
                is_selected: true,
            },
        ];

        let action = AccountModalAction::ImportTracks(track_items, true, true);
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
                        service: StreamingService::Unknown,
                        source_query: format!("{} - {}", t.artist, t.title),
                        status: StreamItemStatus::Queued,
                        audio_file_path: None,
                    });
                }
                let organized = LibrarySyncEngine::deduplicate_and_organize_tracks(all_items, dedup, sort);
                for item in organized {
                    state.queue.push(item);
                }
            }
            _ => {}
        }

        assert_eq!(state.queue.len(), 2);
        assert_eq!(state.queue[0].artist, "Daft Punk");
        assert_eq!(state.queue[1].artist, "The Weeknd");
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
        let (tx, rx) = channel();
        let _ = tx.send(Ok((req_1, 0, PathBuf::from("/tmp/fake_track0.opus"), AudioQualityTier::CloudOpus160, "Opus 160k".to_string())));
        state.stream_rx = Some(rx);

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
}
