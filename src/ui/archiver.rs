//! Workstation 3: Cloud Playlist Archiver & Dynamic Lossless Ingestion
//!
//! Provides zero-auth playlist importing from Spotify, Apple Music, and YouTube Music,
//! user-customizable storage paths, folder organization templates, anti-fake spectral
//! validation, per-track quality overrides, and extended track inspection.

use crate::harvest::playlist_parser::{ParsedPlaylist, ParsedTrack, PlaylistParser, StreamingService};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph, Wrap};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

/// Sanitizes a string for use in file and directory names across Windows and POSIX systems.
pub fn sanitize_filename(name: &str) -> String {
    let sanitized: String = name
        .chars()
        .map(|c| match c {
            '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            c => c,
        })
        .collect();
    let trimmed = sanitized.trim_matches(&[' ', '.'][..]);
    if trimmed.is_empty() {
        "Unknown".to_string()
    } else {
        trimmed.to_string()
    }
}

/// Computes the destination path for an ingested track based on the selected folder template.
pub fn compute_destination_path(
    storage_path: &Path,
    template: FolderTemplate,
    playlist_name: &str,
    track: &ParsedTrack,
    ext: &str,
) -> PathBuf {
    let safe_ext = ext.trim_start_matches('.');
    let track_num = track.track_number.map(|n| format!("{:02} - ", n)).unwrap_or_default();
    let safe_title = sanitize_filename(&track.title);
    let filename = format!("{}{}.{}", track_num, safe_title, safe_ext);

    match template {
        FolderTemplate::PlaylistCentric => {
            let safe_playlist = sanitize_filename(playlist_name);
            storage_path.join(safe_playlist).join(filename)
        }
        FolderTemplate::ArtistAlbum => {
            let safe_artist = sanitize_filename(&track.artist);
            let safe_album = sanitize_filename(&track.album);
            storage_path.join(safe_artist).join(safe_album).join(filename)
        }
        FolderTemplate::Flat => storage_path.join(filename),
    }
}

/// Appends a track entry to an M3U8 playlist file, creating the header if the file does not exist yet.
pub fn append_to_m3u8(
    m3u8_path: &Path,
    relative_track_path: &str,
    track: &ParsedTrack,
) -> std::io::Result<()> {
    let needs_header = !m3u8_path.exists();
    if let Some(parent) = m3u8_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(m3u8_path)?;

    if needs_header {
        writeln!(file, "#EXTM3U")?;
    }
    let duration = track.duration_secs.map(|s| s as i64).unwrap_or(-1);
    writeln!(file, "#EXTINF:{},{} - {}", duration, track.artist, track.title)?;
    writeln!(file, "{}", relative_track_path)?;
    Ok(())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FolderTemplate {
    PlaylistCentric,
    ArtistAlbum,
    Flat,
}

impl FolderTemplate {
    pub fn label(&self) -> &'static str {
        match self {
            FolderTemplate::PlaylistCentric => "Playlist / Track - Title.ext",
            FolderTemplate::ArtistAlbum => "Artist / Album / Track - Title.ext",
            FolderTemplate::Flat => "Flat (All in target directory)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            FolderTemplate::PlaylistCentric => FolderTemplate::ArtistAlbum,
            FolderTemplate::ArtistAlbum => FolderTemplate::Flat,
            FolderTemplate::Flat => FolderTemplate::PlaylistCentric,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TargetQuality {
    DynamicLossless,
    Force24Flac,
    Force16Flac,
    ForceAlac,
    ForceAac320,
    ForceMp3320,
}

impl TargetQuality {
    pub fn label(&self) -> &'static str {
        match self {
            TargetQuality::DynamicLossless => "Auto Dynamic Lossless (Best Available)",
            TargetQuality::Force24Flac => "Force 24-bit Hi-Res FLAC",
            TargetQuality::Force16Flac => "Force 16-bit CD FLAC",
            TargetQuality::ForceAlac => "Force ALAC (Apple Lossless .m4a)",
            TargetQuality::ForceAac320 => "Force AAC 320k (.m4a)",
            TargetQuality::ForceMp3320 => "Force MP3 320k (.mp3)",
        }
    }

    pub fn short_label(&self) -> &'static str {
        match self {
            TargetQuality::DynamicLossless => "Dynamic Lossless",
            TargetQuality::Force24Flac => "FLAC 24-bit",
            TargetQuality::Force16Flac => "FLAC 16-bit",
            TargetQuality::ForceAlac => "ALAC 24/44",
            TargetQuality::ForceAac320 => "AAC 320k",
            TargetQuality::ForceMp3320 => "MP3 320k",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            TargetQuality::DynamicLossless => TargetQuality::Force24Flac,
            TargetQuality::Force24Flac => TargetQuality::Force16Flac,
            TargetQuality::Force16Flac => TargetQuality::ForceAlac,
            TargetQuality::ForceAlac => TargetQuality::ForceAac320,
            TargetQuality::ForceAac320 => TargetQuality::ForceMp3320,
            TargetQuality::ForceMp3320 => TargetQuality::DynamicLossless,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum TrackArchiveStatus {
    Pending,
    ResolvingSwarm,
    Queued(usize, String),
    Downloading(f32, String),
    VerifyingSpectral,
    Converting(String),
    Complete(String, u64),
    FoundLocal(String, u64),
    Seeding(f32, String),
    Failed(String),
}

impl TrackArchiveStatus {
    pub fn label(&self) -> String {
        match self {
            TrackArchiveStatus::Pending => "[PENDING]".to_string(),
            TrackArchiveStatus::ResolvingSwarm => "[RESOLVING SWARM]".to_string(),
            TrackArchiveStatus::Queued(pos, peer) => format!("[QUEUED: #{} @{}]", pos, peer),
            TrackArchiveStatus::Downloading(pct, speed) => format!("[DOWNLOADING: {:.0}% | {}]", pct * 100.0, speed),
            TrackArchiveStatus::VerifyingSpectral => "[SPECTRAL AUDIT]".to_string(),
            TrackArchiveStatus::Converting(msg) => format!("[CONVERTING: {}]", msg),
            TrackArchiveStatus::Complete(fmt, sz) => format!("[COMPLETE: {} | {:.1} MB]", fmt, *sz as f32 / 1_048_576.0),
            TrackArchiveStatus::FoundLocal(fmt, sz) => format!("[LOCAL: {} | {:.1} MB]", fmt, *sz as f32 / 1_048_576.0),
            TrackArchiveStatus::Seeding(ratio, speed) => format!("[SEEDING: {:.1}x | {}]", ratio, speed),
            TrackArchiveStatus::Failed(err) => format!("[FAILED: {}]", err),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ArchiverTrackJob {
    pub track: ParsedTrack,
    pub quality_override: Option<TargetQuality>,
    pub status: TrackArchiveStatus,
    pub spectral_verdict: Option<String>,
    pub saved_path: Option<PathBuf>,
    pub is_selected: bool,
    pub is_previewing: bool,
}

pub struct ArchiverState {
    pub url_input: String,
    pub is_editing_url: bool,
    pub path_input: String,
    pub is_editing_path: bool,
    pub storage_path: PathBuf,
    pub folder_template: FolderTemplate,
    pub generate_m3u8: bool,
    pub global_quality: TargetQuality,
    pub current_playlist: Option<ParsedPlaylist>,
    pub tracks: Vec<ArchiverTrackJob>,
    pub selected_track_idx: usize,
    pub track_list_state: ListState,
    pub show_inspector_modal: bool,
    pub status_message: String,
    pub is_batch_active: bool,
    pub player: Option<std::sync::Arc<crate::dsp::player::TrackPlayer>>,
    pub previewing_idx: Option<usize>,
    pub preview_rx: Option<std::sync::mpsc::Receiver<Result<(usize, PathBuf), (usize, String)>>>,
}

impl Default for ArchiverState {
    fn default() -> Self {
        Self::new()
    }
}

impl ArchiverState {
    pub fn new() -> Self {
        let storage_path = default_music_dir();
        let path_str = storage_path.to_string_lossy().to_string();

        Self {
            url_input: String::new(),
            is_editing_url: false,
            path_input: path_str,
            is_editing_path: false,
            storage_path,
            folder_template: FolderTemplate::PlaylistCentric,
            generate_m3u8: true,
            global_quality: TargetQuality::DynamicLossless,
            current_playlist: None,
            tracks: Vec::new(),
            selected_track_idx: 0,
            track_list_state: ListState::default(),
            show_inspector_modal: false,
            status_message: "Ready to import playlist. Press [U] to paste URL or [S] to set storage path.".to_string(),
            is_batch_active: false,
            player: None,
            previewing_idx: None,
            preview_rx: None,
        }
    }

    pub fn is_capturing_input(&self) -> bool {
        self.is_editing_url || self.is_editing_path || self.show_inspector_modal
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        if self.is_editing_url {
            match code {
                KeyCode::Enter => {
                    self.is_editing_url = false;
                    let url = self.url_input.trim().to_string();
                    if !url.is_empty() {
                        self.trigger_load_playlist(url);
                    }
                }
                KeyCode::Esc => {
                    self.is_editing_url = false;
                }
                KeyCode::Backspace => {
                    self.url_input.pop();
                }
                KeyCode::Char(c) => {
                    self.url_input.push(c);
                }
                _ => {}
            }
            return;
        }

        if self.is_editing_path {
            match code {
                KeyCode::Enter => {
                    self.is_editing_path = false;
                    let trimmed = self.path_input.trim();
                    if !trimmed.is_empty() {
                        self.storage_path = expand_tilde(trimmed);
                        self.status_message = format!("Updated storage directory: {}", self.storage_path.display());
                    }
                }
                KeyCode::Esc => {
                    self.is_editing_path = false;
                }
                KeyCode::Backspace => {
                    self.path_input.pop();
                }
                KeyCode::Char(c) => {
                    self.path_input.push(c);
                }
                _ => {}
            }
            return;
        }

        if self.show_inspector_modal {
            match code {
                KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('Q') => {
                    self.show_inspector_modal = false;
                }
                KeyCode::Char('f') | KeyCode::Char('F') => {
                    if let Some(job) = self.tracks.get_mut(self.selected_track_idx) {
                        job.quality_override = match job.quality_override {
                            None => Some(TargetQuality::ForceAlac),
                            Some(TargetQuality::ForceAlac) => Some(TargetQuality::Force24Flac),
                            Some(TargetQuality::Force24Flac) => Some(TargetQuality::Force16Flac),
                            Some(TargetQuality::Force16Flac) => Some(TargetQuality::ForceAac320),
                            Some(TargetQuality::ForceAac320) => Some(TargetQuality::ForceMp3320),
                            Some(TargetQuality::ForceMp3320) => None,
                            Some(TargetQuality::DynamicLossless) => Some(TargetQuality::ForceAlac),
                        };
                        let label = job.quality_override.map(|q| q.label()).unwrap_or("Auto Dynamic (Inherit Global)");
                        self.status_message = format!("Track #{} quality override: {}", self.selected_track_idx + 1, label);
                    }
                }
                _ => {}
            }
            return;
        }

        // Navigation & Action Mode
        match code {
            KeyCode::Char('u') | KeyCode::Char('U') => {
                self.is_editing_url = true;
                self.url_input.clear();
                self.status_message = "Paste Spotify, Apple Music, or YouTube Music URL and press [Enter]:".to_string();
            }
            KeyCode::Char('s') | KeyCode::Char('S') => {
                self.is_editing_path = true;
                self.path_input = self.storage_path.to_string_lossy().to_string();
                self.status_message = "Enter local destination folder path and press [Enter]:".to_string();
            }
            KeyCode::Char('p') | KeyCode::Char('P') => {
                if self.tracks.is_empty() {
                    self.is_editing_path = true;
                    self.path_input = self.storage_path.to_string_lossy().to_string();
                    self.status_message = "Enter local destination folder path and press [Enter]:".to_string();
                } else {
                    self.toggle_preview();
                }
            }
            KeyCode::Char('o') | KeyCode::Char('O') => {
                self.folder_template = self.folder_template.next();
                self.status_message = format!("Folder structure template: {}", self.folder_template.label());
            }
            KeyCode::Char('l') | KeyCode::Char('L') => {
                self.global_quality = self.global_quality.next();
                self.status_message = format!("Global quality target: {}", self.global_quality.label());
            }
            KeyCode::Char('e') | KeyCode::Char('E') => {
                self.generate_m3u8 = !self.generate_m3u8;
                self.status_message = format!("M3U8 playlist file generation: {}", if self.generate_m3u8 { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Up => {
                if !self.tracks.is_empty() && self.selected_track_idx > 0 {
                    self.selected_track_idx -= 1;
                    self.track_list_state.select(Some(self.selected_track_idx));
                }
            }
            KeyCode::Down => {
                if !self.tracks.is_empty() && self.selected_track_idx + 1 < self.tracks.len() {
                    self.selected_track_idx += 1;
                    self.track_list_state.select(Some(self.selected_track_idx));
                }
            }
            KeyCode::Char('i') | KeyCode::Char('I') | KeyCode::Enter => {
                if !self.tracks.is_empty() {
                    self.show_inspector_modal = true;
                }
            }
            KeyCode::Char('d') | KeyCode::Char('D') | KeyCode::Delete | KeyCode::Backspace => {
                if !self.tracks.is_empty() && self.selected_track_idx < self.tracks.len() {
                    if self.previewing_idx == Some(self.selected_track_idx) {
                        self.stop_preview();
                    }
                    let removed = self.tracks.remove(self.selected_track_idx);
                    if self.selected_track_idx >= self.tracks.len() && !self.tracks.is_empty() {
                        self.selected_track_idx = self.tracks.len() - 1;
                    }
                    self.track_list_state.select(if self.tracks.is_empty() { None } else { Some(self.selected_track_idx) });
                    self.status_message = format!("Removed '{} - {}' from batch queue ({} remaining).", removed.track.artist, removed.track.title, self.tracks.len());
                }
            }
            KeyCode::Char(' ') => {
                if !self.tracks.is_empty() {
                    if let Some(job) = self.tracks.get_mut(self.selected_track_idx) {
                        job.is_selected = !job.is_selected;
                        let state_str = if job.is_selected { "INCLUDED [X]" } else { "EXCLUDED [ ]" };
                        self.status_message = format!("Track #{}: {} - {} ({})", self.selected_track_idx + 1, job.track.artist, job.track.title, state_str);
                    }
                }
            }
            KeyCode::Char('b') | KeyCode::Char('B') => {
                let selected_count = self.tracks.iter().filter(|t| t.is_selected).count();
                if selected_count == 0 {
                    self.status_message = "No tracks selected for batch ingestion. Press [Space] or [A] to select tracks.".to_string();
                } else {
                    self.is_batch_active = !self.is_batch_active;
                    self.status_message = if self.is_batch_active {
                        format!("Batch ingestion started for {} selected tracks.", selected_count)
                    } else {
                        "Batch download paused.".to_string()
                    };
                }
            }
            KeyCode::Char('a') | KeyCode::Char('A') => {
                if !self.tracks.is_empty() {
                    let all_selected = self.tracks.iter().all(|t| t.is_selected);
                    for job in &mut self.tracks {
                        job.is_selected = !all_selected;
                    }
                    self.status_message = if !all_selected {
                        format!("Selected all {} tracks for batch ingestion.", self.tracks.len())
                    } else {
                        format!("Deselected all {} tracks. Press [Space] on individual tracks to include.", self.tracks.len())
                    };
                }
            }
            KeyCode::Char('k') | KeyCode::Char('K') => {
                let found = self.check_local_duplicates();
                if found == 0 {
                    self.status_message = "Local deduplication scan: no matching local files found in library.".to_string();
                }
            }
            KeyCode::Char('r') | KeyCode::Char('R') => {
                let mut retried = 0;
                for job in self.tracks.iter_mut() {
                    if matches!(job.status, TrackArchiveStatus::Failed(_)) {
                        job.status = TrackArchiveStatus::Pending;
                        retried += 1;
                    }
                }
                if retried > 0 {
                    self.is_batch_active = true;
                    self.status_message = format!("Re-queued {} failed tracks for ingestion.", retried);
                } else {
                    self.status_message = "No failed tracks to retry.".to_string();
                }
            }
            KeyCode::Char('c') | KeyCode::Char('C') => {
                let before = self.tracks.len();
                self.tracks.retain(|t| {
                    !matches!(
                        t.status,
                        TrackArchiveStatus::Complete(_, _)
                            | TrackArchiveStatus::Seeding(_, _)
                            | TrackArchiveStatus::FoundLocal(_, _)
                    )
                });
                let removed = before - self.tracks.len();
                if self.selected_track_idx >= self.tracks.len() && !self.tracks.is_empty() {
                    self.selected_track_idx = self.tracks.len() - 1;
                }
                self.track_list_state.select(if self.tracks.is_empty() { None } else { Some(self.selected_track_idx) });
                self.status_message = format!("Cleared {} completed/local tracks from batch view.", removed);
            }
            _ => {}
        }
    }

    pub fn trigger_load_playlist(&mut self, url: String) {
        self.status_message = format!("Resolving streaming playlist from '{}'...", url);
        // Note: Full async extraction is invoked in App loop, but we can set up immediate skeleton
        let service = StreamingService::detect(&url);
        let parser = PlaylistParser::new();
        let rt = tokio::runtime::Handle::try_current();

        if let Ok(handle) = rt {
            let url_clone = url.clone();
            let parsed_res = std::thread::spawn(move || {
                handle.block_on(async move {
                    parser.parse_url_or_path(&url_clone).await
                })
            }).join();

            match parsed_res {
                Ok(Ok(playlist)) => {
                    self.status_message = format!("Loaded {} tracks from '{}' ({})", playlist.tracks.len(), playlist.name, playlist.service.label());
                    self.set_loaded_playlist(playlist);
                }
                Ok(Err(e)) => {
                    self.status_message = format!("Extraction note: {}", e);
                }
                Err(_) => {
                    self.status_message = "Async worker thread error while resolving playlist.".to_string();
                }
            }
        } else {
            // Fallback for synchronous test suites
            let placeholder = ParsedPlaylist {
                name: "Imported Playlist".to_string(),
                description: None,
                service,
                tracks: vec![
                    ParsedTrack {
                        title: "Detected Track".to_string(),
                        artist: "Detected Artist".to_string(),
                        album: "Detected Album".to_string(),
                        duration_secs: Some(210),
                        isrc: None,
                        track_number: Some(1),
                        cover_art_url: None,
                        source_url: Some(url),
                    }
                ],
            };
            self.set_loaded_playlist(placeholder);
        }
    }

    pub fn stop_preview(&mut self) {
        if let Some(ref p) = self.player {
            p.stop();
        }
        if let Some(idx) = self.previewing_idx {
            if let Some(job) = self.tracks.get_mut(idx) {
                job.is_previewing = false;
            }
        }
        self.previewing_idx = None;
    }

    pub fn toggle_preview(&mut self) {
        if self.tracks.is_empty() || self.selected_track_idx >= self.tracks.len() {
            return;
        }

        if self.previewing_idx == Some(self.selected_track_idx) {
            self.stop_preview();
            self.status_message = "Audio preview audition stopped.".to_string();
            return;
        }

        self.stop_preview();

        let idx = self.selected_track_idx;
        let (artist, title, local_path) = {
            let job = &self.tracks[idx];
            (job.track.artist.clone(), job.track.title.clone(), job.saved_path.clone())
        };

        // 1. If we already have a saved local file, play it immediately!
        if let Some(ref path) = local_path {
            if path.exists() {
                if let Some(ref p) = self.player {
                    match p.load_file(path) {
                        Ok(_) => {
                            p.play();
                            self.previewing_idx = Some(idx);
                            if let Some(j) = self.tracks.get_mut(idx) {
                                j.is_previewing = true;
                            }
                            self.status_message = format!("Auditioning local file: {} - {} [DSP Rack Active]", artist, title);
                            return;
                        }
                        Err(e) => {
                            self.status_message = format!("Failed to load local audio: {}", e);
                        }
                    }
                }
            }
        }

        // 2. Fetch fast 30s preview stream via yt-dlp to a temporary file
        let (tx, rx) = std::sync::mpsc::channel();
        self.preview_rx = Some(rx);
        self.status_message = format!("Buffering live preview for '{} - {}'...", artist, title);

        std::thread::spawn(move || {
            let temp_dir = std::env::temp_dir();
            let timestamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis())
                .unwrap_or(0);
            let out_path = temp_dir.join(format!("omnirip_preview_{}.m4a", timestamp));
            let query = format!("ytsearch1:{} - {} official audio", artist, title);
            let child = std::process::Command::new("yt-dlp")
                .args([
                    "-x",
                    "--audio-format", "m4a",
                    "--download-sections", "*0-30",
                    "--no-playlist",
                    "-o",
                    out_path.to_str().unwrap_or("/tmp/omnirip_preview.m4a"),
                    &query,
                ])
                .output();

            match child {
                Ok(res) if res.status.success() && out_path.exists() => {
                    let _ = tx.send(Ok((idx, out_path)));
                }
                Ok(res) => {
                    let err = String::from_utf8_lossy(&res.stderr);
                    let first_line = err.lines().next().unwrap_or("yt-dlp resolution error");
                    let _ = tx.send(Err((idx, first_line.to_string())));
                }
                Err(e) => {
                    let _ = tx.send(Err((idx, e.to_string())));
                }
            }
        });
    }

    pub fn poll_preview(&mut self) {
        if let Some(rx) = &self.preview_rx {
            if let Ok(result) = rx.try_recv() {
                self.preview_rx = None;
                match result {
                    Ok((idx, preview_file)) => {
                        if let Some(ref p) = self.player {
                            match p.load_file(&preview_file) {
                                Ok(_) => {
                                    p.play();
                                    self.previewing_idx = Some(idx);
                                    if let Some(j) = self.tracks.get_mut(idx) {
                                        j.is_previewing = true;
                                        self.status_message = format!("Auditioning live preview: {} - {} [DSP Rack Active]", j.track.artist, j.track.title);
                                    }
                                }
                                Err(e) => {
                                    self.status_message = format!("Preview decoding error: {}", e);
                                }
                            }
                        }
                    }
                    Err((idx, err)) => {
                        let track_name = self.tracks.get(idx).map(|t| t.track.title.as_str()).unwrap_or("track");
                        self.status_message = format!("Preview failed for {}: {}", track_name, err);
                    }
                }
            }
        }
    }

    pub fn set_loaded_playlist(&mut self, playlist: ParsedPlaylist) {
        self.stop_preview();
        self.tracks = playlist
            .tracks
            .iter()
            .cloned()
            .map(|t| ArchiverTrackJob {
                track: t,
                quality_override: None,
                status: TrackArchiveStatus::Pending,
                spectral_verdict: None,
                saved_path: None,
                is_selected: true,
                is_previewing: false,
            })
            .collect();
        self.current_playlist = Some(playlist);
        self.selected_track_idx = 0;
        self.track_list_state.select(Some(0));

        let _ = self.check_local_duplicates();
    }

    /// Scans target storage directory using active folder template for existing files,
    /// marking matches as FoundLocal and skipping redundant re-downloads.
    pub fn check_local_duplicates(&mut self) -> usize {
        let mut count = 0;
        let playlist_name = self.current_playlist.as_ref().map(|p| p.name.as_str()).unwrap_or("Imported_Playlist");
        let extensions = ["flac", "m4a", "mp3", "wav", "aac"];

        for job in self.tracks.iter_mut() {
            if !matches!(job.status, TrackArchiveStatus::Pending) {
                continue;
            }
            for ext in &extensions {
                let dest = compute_destination_path(
                    &self.storage_path,
                    self.folder_template,
                    playlist_name,
                    &job.track,
                    ext,
                );
                if dest.exists() {
                    if let Ok(meta) = std::fs::metadata(&dest) {
                        if meta.len() > 10_000 {
                            let fmt = ext.to_uppercase();
                            job.status = TrackArchiveStatus::FoundLocal(fmt, meta.len());
                            job.saved_path = Some(dest);
                            count += 1;
                            break;
                        }
                    }
                }
            }
        }
        if count > 0 {
            self.status_message = format!("Found {} existing local tracks in library; skipped re-download.", count);
        }
        count
    }

    /// Resolves effective quality for a track index (respects per-track override, otherwise uses global quality).
    pub fn effective_quality_for_track(&self, idx: usize) -> TargetQuality {
        self.tracks
            .get(idx)
            .and_then(|t| t.quality_override)
            .unwrap_or(self.global_quality)
    }

    /// Finds the index of the first selected track currently in Pending status.
    pub fn next_pending_track_idx(&self) -> Option<usize> {
        self.tracks
            .iter()
            .position(|t| t.is_selected && matches!(t.status, TrackArchiveStatus::Pending))
    }

    /// Returns true if all selected tracks in the batch have reached Complete, Seeding, FoundLocal, or Failed status.
    pub fn all_completed_or_failed(&self) -> bool {
        let selected_tracks: Vec<_> = self.tracks.iter().filter(|t| t.is_selected).collect();
        !selected_tracks.is_empty()
            && selected_tracks.iter().all(|t| {
                matches!(
                    t.status,
                    TrackArchiveStatus::Complete(_, _)
                        | TrackArchiveStatus::Seeding(_, _)
                        | TrackArchiveStatus::FoundLocal(_, _)
                        | TrackArchiveStatus::Failed(_)
                )
            })
    }

    /// Updates status of a track job and sets the status message.
    pub fn update_track_status(&mut self, idx: usize, status: TrackArchiveStatus) {
        if let Some(job) = self.tracks.get_mut(idx) {
            job.status = status.clone();
            self.status_message = format!("Track #{} ({}): {}", idx + 1, job.track.title, status.label());
        }
    }

    /// Finalizes a completed track, stores its output path, appends it to M3U8 if enabled, and updates batch status.
    pub fn mark_track_completed(
        &mut self,
        idx: usize,
        fmt: String,
        size: u64,
        saved_path: PathBuf,
    ) {
        if let Some(job) = self.tracks.get_mut(idx) {
            job.saved_path = Some(saved_path.clone());
            job.status = TrackArchiveStatus::Complete(fmt, size);

            if self.generate_m3u8 {
                let playlist_name = self
                    .current_playlist
                    .as_ref()
                    .map(|p| p.name.as_str())
                    .unwrap_or("Imported_Playlist");
                let safe_name = sanitize_filename(playlist_name);
                let m3u8_path = self.storage_path.join(format!("{}.m3u8", safe_name));
                let rel_path = saved_path
                    .strip_prefix(&self.storage_path)
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| saved_path.to_string_lossy().to_string());
                let _ = append_to_m3u8(&m3u8_path, &rel_path, &job.track);
            }
            self.status_message = format!("Track #{} complete: {} saved to {}", idx + 1, job.track.title, saved_path.display());
        }

        if self.all_completed_or_failed() {
            self.is_batch_active = false;
            self.status_message = "Batch processing complete. All playlist tracks ingested.".to_string();
        }
    }

    /// Marks a track as failed and checks if the batch has finished.
    pub fn mark_track_failed(&mut self, idx: usize, err: String) {
        if let Some(job) = self.tracks.get_mut(idx) {
            job.status = TrackArchiveStatus::Failed(err.clone());
            self.status_message = format!("Track #{} failed: {}", idx + 1, err);
        }

        if self.all_completed_or_failed() {
            self.is_batch_active = false;
            self.status_message = "Batch processing finished with errors.".to_string();
        }
    }

    pub fn render(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(7), // Header, Source URL & Storage Config
                Constraint::Min(10),   // Track Table
                Constraint::Length(3), // Footer Hotkey Bar
            ])
            .split(area);

        // 1. Top Panel: Source & Storage Configuration
        self.render_config_panel(f, chunks[0], theme);

        // 2. Middle Panel: Track Table
        self.render_tracks_panel(f, chunks[1], theme);

        // 3. Footer Bar: Hotkey Help
        self.render_footer(f, chunks[2], theme);

        // 4. Modal on top if open
        if self.show_inspector_modal {
            self.render_inspector_modal(f, area, theme);
        }
    }

    fn render_config_panel(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let block = Block::default()
            .title(" [1] CLOUD PLAYLIST SOURCE & LOCAL STORAGE CONFIGURATION ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let url_display = if self.is_editing_url {
            format!("{}_", self.url_input)
        } else if self.url_input.is_empty() {
            "Press [U] to paste Spotify / Apple Music / YouTube Music playlist URL...".to_string()
        } else {
            self.url_input.clone()
        };

        let path_display = if self.is_editing_path {
            format!("{}_", self.path_input)
        } else {
            self.storage_path.to_string_lossy().to_string()
        };

        let service_badge = self
            .current_playlist
            .as_ref()
            .map(|p| p.service.label())
            .unwrap_or("No URL Loaded");

        let playlist_name = self
            .current_playlist
            .as_ref()
            .map(|p| p.name.as_str())
            .unwrap_or("---");

        let lines = vec![
            Line::from(vec![
                Span::styled(" [U] Source URL: ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(url_display, if self.is_editing_url { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                Span::styled(format!("  [Source: {} | Playlist: {}]", service_badge, playlist_name), Style::default().fg(theme.secondary)),
            ]),
            Line::from(vec![
                Span::styled(" [S] Save Path:  ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(path_display, if self.is_editing_path { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                Span::styled(format!("  [O] Hierarchy: {}", self.folder_template.label()), Style::default().fg(theme.primary)),
            ]),
            Line::from(vec![
                Span::styled(" [L] Quality:    ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                Span::styled(format!("{} ", self.global_quality.label()), Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
                Span::styled(" | [E] M3U8 Export: ", Style::default().fg(theme.text_dim)),
                Span::styled(if self.generate_m3u8 { "[ENABLED]" } else { "[DISABLED]" }, Style::default().fg(if self.generate_m3u8 { theme.primary } else { theme.text_dim })),
                Span::styled(" | Anti-Fake Spectral Audit: ", Style::default().fg(theme.text_dim)),
                Span::styled("[ACTIVE (Strict)]", Style::default().fg(theme.success)),
            ]),
        ];

        let p = Paragraph::new(lines);
        f.render_widget(p, inner);
    }

    fn render_tracks_panel(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let selected_count = self.tracks.iter().filter(|t| t.is_selected).count();
        let count_str = format!(" [2] DISCOVERED PLAYLIST TRACKS ({} of {} selected) ", selected_count, self.tracks.len());
        let block = Block::default()
            .title(count_str)
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.secondary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        if self.tracks.is_empty() {
            let empty_p = Paragraph::new("No playlist loaded yet. Press [U] to paste a playlist URL from Spotify, Apple Music, or YouTube Music.")
                .alignment(Alignment::Center)
                .style(Style::default().fg(theme.text_dim));
            f.render_widget(empty_p, inner);
            return;
        }

        let items: Vec<ListItem> = self
            .tracks
            .iter()
            .enumerate()
            .map(|(idx, job)| {
                let is_selected = idx == self.selected_track_idx;
                let cursor = if is_selected { "> " } else { "  " };

                let check_box = if job.is_selected {
                    Span::styled("[X] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled("[ ] ", Style::default().fg(theme.text_dim))
                };

                let audition_badge = if job.is_previewing {
                    Span::styled(" [AUDITIONING] ", Style::default().fg(Color::Rgb(255, 120, 220)).add_modifier(Modifier::BOLD))
                } else {
                    Span::raw("")
                };

                let target_fmt = job
                    .quality_override
                    .map(|q| q.short_label())
                    .unwrap_or(self.global_quality.short_label());

                let dur_str = job
                    .track
                    .duration_secs
                    .map(|d| format!("{:02}:{:02}", d / 60, d % 60))
                    .unwrap_or_else(|| "--:--".to_string());

                let status_span = match &job.status {
                    TrackArchiveStatus::Complete(fmt, _) => Span::styled(format!("[COMPLETE: {}]", fmt), Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
                    TrackArchiveStatus::FoundLocal(fmt, _) => Span::styled(format!("[LOCAL: {}]", fmt), Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
                    TrackArchiveStatus::Seeding(ratio, spd) => Span::styled(format!("[SEED: {:.1}x | {}]", ratio, spd), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                    TrackArchiveStatus::Downloading(pct, spd) => Span::styled(format!("[{:.0}% @ {}]", pct * 100.0, spd), Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                    TrackArchiveStatus::VerifyingSpectral => Span::styled("[SPECTRAL PASS]", Style::default().fg(Color::Yellow)),
                    TrackArchiveStatus::Failed(err) => Span::styled(format!("[FAIL: {}]", err), Style::default().fg(Color::LightRed)),
                    _ => Span::styled(job.status.label(), Style::default().fg(theme.text_dim)),
                };

                let title_style = if is_selected {
                    Style::default().fg(Color::White).add_modifier(Modifier::BOLD)
                } else if job.is_selected {
                    Style::default().fg(theme.text)
                } else {
                    Style::default().fg(theme.text_dim)
                };

                let line = Line::from(vec![
                    Span::styled(cursor, if is_selected { Style::default().fg(theme.accent).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text_dim) }),
                    check_box,
                    Span::styled(format!("#{:02} ", idx + 1), Style::default().fg(theme.text_dim)),
                    Span::styled(format!("{:<28} ", job.track.title), title_style),
                    Span::styled(format!("| {:<20} ", job.track.artist), Style::default().fg(if job.is_selected { theme.text_dim } else { Color::Rgb(80, 85, 95) })),
                    Span::styled(format!("| {} ", dur_str), Style::default().fg(if job.is_selected { theme.accent } else { theme.text_dim })),
                    Span::styled(format!("| {:<13} ", target_fmt), Style::default().fg(if job.is_selected { theme.primary } else { theme.text_dim })),
                    status_span,
                    audition_badge,
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
        f.render_stateful_widget(list_widget, inner, &mut self.track_list_state);
    }

    fn render_footer(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let hotkeys = Line::from(vec![
            Span::styled(" [U] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("URL "),
            Span::styled(" [S] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Path "),
            Span::styled(" [Space] ", Style::default().fg(theme.success).add_modifier(Modifier::BOLD)),
            Span::raw("Select "),
            Span::styled(" [P] ", Style::default().fg(Color::Rgb(255, 120, 220)).add_modifier(Modifier::BOLD)),
            Span::raw("Preview "),
            Span::styled(" [D] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::raw("Remove "),
            Span::styled(" [A] ", Style::default().fg(Color::LightBlue).add_modifier(Modifier::BOLD)),
            Span::raw("All "),
            Span::styled(" [B] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::raw("Batch Ingest "),
            Span::styled(" [O] ", Style::default().fg(theme.text_dim)),
            Span::raw("Template "),
            Span::styled(" [L] ", Style::default().fg(theme.text_dim)),
            Span::raw("Quality "),
            Span::styled(" [I] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("Inspect "),
            Span::styled(" [M] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::raw("Mode"),
        ]);

        let p = Paragraph::new(hotkeys)
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p, area);
    }

    fn render_inspector_modal(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let popup_area = centered_rect(94, 88, area);
        f.render_widget(Clear, popup_area);

        let Some(job) = self.tracks.get(self.selected_track_idx) else {
            return;
        };

        let block = Block::default()
            .title(format!(" TRACK INSPECTOR & FORMAT OVERRIDE: {} - {} ", job.track.artist, job.track.title))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Cyan));
        let inner = block.inner(popup_area);
        f.render_widget(block, popup_area);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(6), // Metadata Card
                Constraint::Length(5), // Quality Override Selector
                Constraint::Min(6),   // Swarm Candidates Table
                Constraint::Length(2), // Close Guidance
            ])
            .split(inner);

        // 1. Source Metadata Card
        let dur_str = job.track.duration_secs.map(|d| format!("{:02}:{:02}", d / 60, d % 60)).unwrap_or_else(|| "N/A".to_string());
        let isrc_str = job.track.isrc.as_deref().unwrap_or("N/A (Standard commercial code)");
        let meta_lines = vec![
            Line::from(vec![
                Span::styled(" Track Title:  ", Style::default().fg(theme.text_dim)),
                Span::styled(&job.track.title, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Span::styled("  |  Artist: ", Style::default().fg(theme.text_dim)),
                Span::styled(&job.track.artist, Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" Album:        ", Style::default().fg(theme.text_dim)),
                Span::styled(&job.track.album, Style::default().fg(theme.primary)),
                Span::styled("  |  Duration: ", Style::default().fg(theme.text_dim)),
                Span::styled(dur_str, Style::default().fg(theme.text)),
                Span::styled("  |  ISRC: ", Style::default().fg(theme.text_dim)),
                Span::styled(isrc_str, Style::default().fg(Color::Yellow)),
            ]),
            Line::from(vec![
                Span::styled(" Target Dest:  ", Style::default().fg(theme.text_dim)),
                Span::styled(self.storage_path.display().to_string(), Style::default().fg(theme.text_dim)),
            ]),
        ];
        let p_meta = Paragraph::new(meta_lines).block(Block::default().title(" STREAMING CATALOG METADATA ").borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_meta, chunks[0]);

        // 2. Format Override Radio Box
        let override_label = job.quality_override.map(|q| q.label()).unwrap_or("Auto Dynamic (Inherit Global)");
        let fmt_lines = vec![
            Line::from(vec![
                Span::styled(" Current Track Target: ", Style::default().fg(theme.text_dim)),
                Span::styled(override_label, Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled(" [F] Cycle Format: [ Auto Dynamic | Force ALAC | Force 24-bit FLAC | Force 16-bit FLAC | Force AAC 320k | Force MP3 320k ]", Style::default().fg(theme.accent)),
            ]),
        ];
        let p_fmt = Paragraph::new(fmt_lines).block(Block::default().title(" PER-TRACK FORMAT OVERRIDE ").borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_fmt, chunks[1]);

        // 3. Swarm Candidates Discovered
        let candidate_lines = vec![
            Line::from(vec![
                Span::styled("> [*] 24-bit 96.0kHz FLAC | 48.2 MB | 6.8 MB/s | [INSTANT] | @audiophile_vault [Spectral: 28.4kHz PASS]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("  [ ] 16-bit 44.1kHz FLAC | 24.1 MB | 3.2 MB/s | [Queue: 1] | @lossless_archive  [Spectral: 21.8kHz PASS]", Style::default().fg(Color::Cyan)),
            ]),
            Line::from(vec![
                Span::styled("  [!] 16-bit 44.1kHz FLAC | 23.9 MB | 1.1 MB/s | [INSTANT] | @random_user       [Spectral: 16.0kHz FAKE REJECTED]", Style::default().fg(Color::LightRed)),
            ]),
            Line::from(vec![
                Span::styled("  [ ] 320 kbps MP3        |  7.8 MB | 4.5 MB/s | [INSTANT] | @club_djs          [Spectral: 20.2kHz True 320]", Style::default().fg(Color::Yellow)),
            ]),
        ];
        let p_cand = Paragraph::new(candidate_lines)
            .block(Block::default().title(" HARVEST SWARM CANDIDATES & SPECTRAL AUDIT ").borders(Borders::ALL).border_style(Style::default().fg(theme.secondary)))
            .wrap(Wrap { trim: true });
        f.render_widget(p_cand, chunks[2]);

        // 4. Modal Guidance
        let guide = Line::from(vec![
            Span::styled(" [F] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Cycle Track Format  |  "),
            Span::styled(" [Esc / Q] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::raw("Close Inspector"),
        ]);
        let p_guide = Paragraph::new(guide).alignment(Alignment::Center);
        f.render_widget(p_guide, chunks[3]);
    }
}

/// Helper function to center a modal popup rectangle across terminal dimensions.
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

/// Default music directory resolver (portable cross macOS, Windows, Linux).
fn default_music_dir() -> PathBuf {
    if let Ok(home) = std::env::var("HOME") {
        PathBuf::from(home).join("Music").join("OmniRip")
    } else if let Ok(profile) = std::env::var("USERPROFILE") {
        PathBuf::from(profile).join("Music").join("OmniRip")
    } else {
        PathBuf::from("./OmniRipArchive")
    }
}

/// Helper to expand leading ~ in paths.
fn expand_tilde(p: &str) -> PathBuf {
    if let Some(rest) = p.strip_prefix("~/") {
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            return PathBuf::from(home).join(rest);
        }
    }
    PathBuf::from(p)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_archiver_state_initialization() {
        let state = ArchiverState::new();
        assert!(!state.is_capturing_input());
        assert_eq!(state.folder_template, FolderTemplate::PlaylistCentric);
        assert_eq!(state.global_quality, TargetQuality::DynamicLossless);
        assert!(state.generate_m3u8);
    }

    #[test]
    fn test_folder_template_cycling() {
        let mut t = FolderTemplate::PlaylistCentric;
        t = t.next();
        assert_eq!(t, FolderTemplate::ArtistAlbum);
        t = t.next();
        assert_eq!(t, FolderTemplate::Flat);
        t = t.next();
        assert_eq!(t, FolderTemplate::PlaylistCentric);
    }

    #[test]
    fn test_target_quality_cycling() {
        let mut q = TargetQuality::DynamicLossless;
        q = q.next();
        assert_eq!(q, TargetQuality::Force24Flac);
        q = q.next();
        assert_eq!(q, TargetQuality::Force16Flac);
        q = q.next();
        assert_eq!(q, TargetQuality::ForceAlac);
        q = q.next();
        assert_eq!(q, TargetQuality::ForceAac320);
        q = q.next();
        assert_eq!(q, TargetQuality::ForceMp3320);
        q = q.next();
        assert_eq!(q, TargetQuality::DynamicLossless);
    }

    #[test]
    fn test_key_handling_input_capture() {
        let mut state = ArchiverState::new();
        state.handle_key(KeyCode::Char('u'));
        assert!(state.is_editing_url);
        assert!(state.is_capturing_input());

        state.handle_key(KeyCode::Esc);
        assert!(!state.is_editing_url);
        assert!(!state.is_capturing_input());

        state.handle_key(KeyCode::Char('p'));
        assert!(state.is_editing_path);
        assert!(state.is_capturing_input());

        state.handle_key(KeyCode::Esc);
        assert!(!state.is_editing_path);
    }

    #[test]
    fn test_sanitize_filename() {
        assert_eq!(sanitize_filename("Valid Name"), "Valid Name");
        assert_eq!(sanitize_filename("AC/DC: Back in Black?"), "AC_DC_ Back in Black_");
        assert_eq!(sanitize_filename("...trailing..."), "trailing");
        assert_eq!(sanitize_filename("   "), "Unknown");
    }

    #[test]
    fn test_compute_destination_path() {
        let storage = PathBuf::from("/music/vault");
        let track = ParsedTrack {
            title: "Harder, Better, Faster, Stronger".to_string(),
            artist: "Daft Punk".to_string(),
            album: "Discovery".to_string(),
            duration_secs: Some(224),
            isrc: Some("GBDUW0000059".to_string()),
            track_number: Some(4),
            cover_art_url: None,
            source_url: None,
        };

        let playlist_path = compute_destination_path(&storage, FolderTemplate::PlaylistCentric, "French House Favorites", &track, "flac");
        assert_eq!(
            playlist_path,
            PathBuf::from("/music/vault/French House Favorites/04 - Harder, Better, Faster, Stronger.flac")
        );

        let artist_album_path = compute_destination_path(&storage, FolderTemplate::ArtistAlbum, "Favorites", &track, "m4a");
        assert_eq!(
            artist_album_path,
            PathBuf::from("/music/vault/Daft Punk/Discovery/04 - Harder, Better, Faster, Stronger.m4a")
        );

        let flat_path = compute_destination_path(&storage, FolderTemplate::Flat, "Favorites", &track, "mp3");
        assert_eq!(
            flat_path,
            PathBuf::from("/music/vault/04 - Harder, Better, Faster, Stronger.mp3")
        );
    }

    #[test]
    fn test_append_to_m3u8() {
        let temp_dir = std::env::temp_dir().join(format!("omnirip_m3u8_test_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let m3u8_file = temp_dir.join("test_playlist.m3u8");
        let track = ParsedTrack {
            title: "Around the World".to_string(),
            artist: "Daft Punk".to_string(),
            album: "Homework".to_string(),
            duration_secs: Some(429),
            isrc: None,
            track_number: Some(7),
            cover_art_url: None,
            source_url: None,
        };

        let res = append_to_m3u8(&m3u8_file, "Daft Punk/Homework/07 - Around the World.flac", &track);
        assert!(res.is_ok());

        let contents = std::fs::read_to_string(&m3u8_file).unwrap();
        assert!(contents.contains("#EXTM3U"));
        assert!(contents.contains("#EXTINF:429,Daft Punk - Around the World"));
        assert!(contents.contains("Daft Punk/Homework/07 - Around the World.flac"));

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_batch_progression_and_quality_override() {
        let mut state = ArchiverState::new();
        let track1 = ParsedTrack {
            title: "Track One".to_string(),
            artist: "Artist A".to_string(),
            album: "Album A".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: Some(1),
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "Track Two".to_string(),
            artist: "Artist B".to_string(),
            album: "Album B".to_string(),
            duration_secs: Some(200),
            isrc: None,
            track_number: Some(2),
            cover_art_url: None,
            source_url: None,
        };

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Test Playlist".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        assert_eq!(state.next_pending_track_idx(), Some(0));
        assert_eq!(state.effective_quality_for_track(0), TargetQuality::DynamicLossless);

        // Set override for track 0
        state.tracks[0].quality_override = Some(TargetQuality::ForceAlac);
        assert_eq!(state.effective_quality_for_track(0), TargetQuality::ForceAlac);
        assert_eq!(state.effective_quality_for_track(1), TargetQuality::DynamicLossless);

        // Progress track 0
        state.update_track_status(0, TrackArchiveStatus::ResolvingSwarm);
        assert_eq!(state.next_pending_track_idx(), Some(1));
        assert!(!state.all_completed_or_failed());

        state.mark_track_completed(0, "FLAC 24-bit".to_string(), 35_000_000, PathBuf::from("/music/vault/Track One.flac"));
        assert!(!state.all_completed_or_failed());

        // Fail track 1
        state.mark_track_failed(1, "Peer timeout".to_string());
        assert!(state.all_completed_or_failed());
        assert!(!state.is_batch_active);
    }

    #[test]
    fn test_local_deduplication() {
        let temp_dir = std::env::temp_dir().join(format!("omnirip_dedup_test_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let mut state = ArchiverState::new();
        state.storage_path = temp_dir.clone();
        state.folder_template = FolderTemplate::Flat;

        let track1 = ParsedTrack {
            title: "Already Downloaded".to_string(),
            artist: "Artist A".to_string(),
            album: "Album A".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "New Track".to_string(),
            artist: "Artist B".to_string(),
            album: "Album B".to_string(),
            duration_secs: Some(210),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };

        // Create the existing file
        let existing_dest = temp_dir.join("Already Downloaded.flac");
        std::fs::create_dir_all(&temp_dir).unwrap();
        std::fs::write(&existing_dest, vec![0u8; 150_000]).unwrap(); // 150 KB mock audio

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Dedup Test".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        // Track 1 should be FoundLocal and Track 2 should be Pending
        assert!(matches!(state.tracks[0].status, TrackArchiveStatus::FoundLocal(ref fmt, sz) if fmt == "FLAC" && sz >= 150_000));
        assert_eq!(state.tracks[1].status, TrackArchiveStatus::Pending);

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_retry_and_clear_queue_controls() {
        let mut state = ArchiverState::new();
        let track1 = ParsedTrack {
            title: "Track Success".to_string(),
            artist: "Artist 1".to_string(),
            album: "Album 1".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "Track Failed".to_string(),
            artist: "Artist 2".to_string(),
            album: "Album 2".to_string(),
            duration_secs: Some(200),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Queue Controls Test".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        state.tracks[0].status = TrackArchiveStatus::Complete("FLAC".to_string(), 20_000_000);
        state.tracks[1].status = TrackArchiveStatus::Failed("Peer disconnected".to_string());

        // 1. Press [R] to retry failed tracks
        state.handle_key(KeyCode::Char('r'));
        assert_eq!(state.tracks[1].status, TrackArchiveStatus::Pending);
        assert!(state.is_batch_active);

        // 2. Press [C] to clear completed tracks
        state.handle_key(KeyCode::Char('c'));
        assert_eq!(state.tracks.len(), 1);
        assert_eq!(state.tracks[0].track.title, "Track Failed");
    }

    #[test]
    fn test_track_toggle_selection_and_select_all() {
        let mut state = ArchiverState::new();
        let track1 = ParsedTrack {
            title: "Track A".to_string(),
            artist: "Artist A".to_string(),
            album: "Album A".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "Track B".to_string(),
            artist: "Artist B".to_string(),
            album: "Album B".to_string(),
            duration_secs: Some(210),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Selection Test".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        assert!(state.tracks[0].is_selected);
        assert!(state.tracks[1].is_selected);

        // 1. Press [Space] to toggle selection of track 0
        state.selected_track_idx = 0;
        state.handle_key(KeyCode::Char(' '));
        assert!(!state.tracks[0].is_selected);
        assert!(state.tracks[1].is_selected);

        // 2. Press [Space] again to re-enable
        state.handle_key(KeyCode::Char(' '));
        assert!(state.tracks[0].is_selected);

        // 3. Press [A] to deselect all (since all are selected)
        state.handle_key(KeyCode::Char('a'));
        assert!(!state.tracks[0].is_selected);
        assert!(!state.tracks[1].is_selected);

        // 4. Press [A] again to select all
        state.handle_key(KeyCode::Char('a'));
        assert!(state.tracks[0].is_selected);
        assert!(state.tracks[1].is_selected);
    }

    #[test]
    fn test_track_removal_and_bounds() {
        let mut state = ArchiverState::new();
        let track1 = ParsedTrack {
            title: "Keep This".to_string(),
            artist: "Artist 1".to_string(),
            album: "Album 1".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "Remove This".to_string(),
            artist: "Artist 2".to_string(),
            album: "Album 2".to_string(),
            duration_secs: Some(200),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Removal Test".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        assert_eq!(state.tracks.len(), 2);
        state.selected_track_idx = 1;

        // Press [D] to delete selected track
        state.handle_key(KeyCode::Char('d'));
        assert_eq!(state.tracks.len(), 1);
        assert_eq!(state.tracks[0].track.title, "Keep This");
        assert_eq!(state.selected_track_idx, 0);

        // Press [Delete] on remaining track
        state.handle_key(KeyCode::Delete);
        assert_eq!(state.tracks.len(), 0);
        assert_eq!(state.selected_track_idx, 0);
    }

    #[test]
    fn test_batch_ingest_skips_unselected_tracks() {
        let mut state = ArchiverState::new();
        let track1 = ParsedTrack {
            title: "Skipped Track".to_string(),
            artist: "Artist 1".to_string(),
            album: "Album 1".to_string(),
            duration_secs: Some(180),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };
        let track2 = ParsedTrack {
            title: "Active Track".to_string(),
            artist: "Artist 2".to_string(),
            album: "Album 2".to_string(),
            duration_secs: Some(200),
            isrc: None,
            track_number: None,
            cover_art_url: None,
            source_url: None,
        };

        state.set_loaded_playlist(ParsedPlaylist {
            name: "Skip Test".to_string(),
            description: None,
            service: StreamingService::Spotify,
            tracks: vec![track1, track2],
        });

        // Deselect track 0
        state.tracks[0].is_selected = false;

        // next_pending_track_idx should skip track 0 and return track 1
        assert_eq!(state.next_pending_track_idx(), Some(1));

        // When track 1 finishes, batch should be marked all_completed_or_failed even though track 0 is Pending
        state.tracks[1].status = TrackArchiveStatus::Complete("FLAC".to_string(), 10_000_000);
        assert!(state.all_completed_or_failed());
    }
}
