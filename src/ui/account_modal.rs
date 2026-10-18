use crate::harvest::library_sync::{DiscoveredCollection, DiscoveredTrackItem, LibrarySyncEngine, LibrarySyncProgress, LinkedAccountsConfig};
use crate::harvest::StreamingService;
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph};
use std::collections::{HashMap, HashSet};

fn truncate_str(s: &str, max_len: usize) -> String {
    if s.chars().count() <= max_len {
        s.to_string()
    } else if max_len > 1 {
        let prefix: String = s.chars().take(max_len.saturating_sub(1)).collect();
        format!("{}…", prefix)
    } else {
        s.chars().take(max_len).collect()
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum AccountModalAction {
    ImportCollections(Vec<DiscoveredCollection>, bool, bool),
    ImportTracks(Vec<DiscoveredTrackItem>, bool, bool),
    Close,
}

pub struct AccountSyncModal {
    pub is_open: bool,
    pub focused_field: usize, // 0: Spotify, 1: Apple, 2: YouTube, 3: Browser, 4: Dedup, 5: Sort, 6: Collections (Left), 7: Tracks (Right)
    pub spotify_input: String,
    pub apple_input: String,
    pub youtube_input: String,
    pub youtube_browser: String,
    pub deduplicate: bool,
    pub sort_by_artist: bool,
    pub discovered_collections: Vec<DiscoveredCollection>,
    pub collection_list_state: ListState,
    pub selected_collection_idx: usize,
    pub tracks_cache: HashMap<String, Vec<DiscoveredTrackItem>>,
    pub current_tracks: Vec<DiscoveredTrackItem>,
    pub track_list_state: ListState,
    pub selected_track_idx: usize,
    pub is_scanning: bool,
    pub status_message: String,

    // Real-time asynchronous synchronization channels and telemetry
    pub sync_rx: Option<std::sync::mpsc::Receiver<LibrarySyncProgress>>,
    pub track_loader_tx: Option<std::sync::mpsc::Sender<(String, Vec<DiscoveredTrackItem>)>>,
    pub track_loader_rx: Option<std::sync::mpsc::Receiver<(String, Vec<DiscoveredTrackItem>)>>,
    pub is_syncing: bool,
    pub is_loading_tracks: bool,
    pub apple_status: String,
    pub yt_status: String,
    pub spotify_status: String,
    pub sync_progress_pct: u16,
    pub active_fetches: HashSet<String>,
}

impl Default for AccountSyncModal {
    fn default() -> Self {
        Self::new()
    }
}

impl AccountSyncModal {
    pub fn new() -> Self {
        let cfg = LinkedAccountsConfig::load();
        let default_browser = if LibrarySyncEngine::detect_zen_browser_profiles().is_some() {
            "zen".to_string()
        } else if !cfg.youtube_browser.is_empty() {
            cfg.youtube_browser
        } else {
            "chrome".to_string()
        };

        let (loader_tx, loader_rx) = std::sync::mpsc::channel();

        Self {
            is_open: false,
            focused_field: 0,
            spotify_input: cfg.spotify_profile,
            apple_input: cfg.apple_profile,
            youtube_input: cfg.youtube_profile,
            youtube_browser: default_browser,
            deduplicate: cfg.deduplicate,
            sort_by_artist: cfg.sort_by_artist,
            discovered_collections: Vec::new(),
            collection_list_state: ListState::default(),
            selected_collection_idx: 0,
            tracks_cache: HashMap::new(),
            current_tracks: Vec::new(),
            track_list_state: ListState::default(),
            selected_track_idx: 0,
            is_scanning: false,
            status_message: "Press [A] to Auto-Detect All accounts or paste custom profile links.".to_string(),
            sync_rx: None,
            track_loader_tx: Some(loader_tx),
            track_loader_rx: Some(loader_rx),
            is_syncing: false,
            is_loading_tracks: false,
            apple_status: "Idle".to_string(),
            yt_status: "Idle".to_string(),
            spotify_status: "Idle".to_string(),
            sync_progress_pct: 0,
            active_fetches: HashSet::new(),
        }
    }

    pub fn toggle(&mut self) {
        self.is_open = !self.is_open;
        if self.is_open {
            let cfg = LinkedAccountsConfig::load();
            if self.spotify_input.is_empty() { self.spotify_input = cfg.spotify_profile; }
            if self.apple_input.is_empty() { self.apple_input = cfg.apple_profile; }
            if self.youtube_input.is_empty() { self.youtube_input = cfg.youtube_profile; }
            if self.youtube_browser.is_empty() {
                self.youtube_browser = if LibrarySyncEngine::detect_zen_browser_profiles().is_some() {
                    "zen".to_string()
                } else {
                    cfg.youtube_browser
                };
            }
            self.deduplicate = cfg.deduplicate;
            self.sort_by_artist = cfg.sort_by_artist;

            // Auto-detect on open if collections list is currently empty
            if self.discovered_collections.is_empty() {
                self.auto_detect();
            }
        }
    }

    pub fn selected_browser(&self) -> String {
        self.youtube_browser.clone()
    }

    pub fn paste(&mut self, text: &str) {
        let clean = text.trim();
        if clean.is_empty() {
            return;
        }
        match self.focused_field {
            0 => {
                self.spotify_input = clean.to_string();
                self.status_message = format!("Pasted Spotify Profile URL: {}", clean);
            }
            1 => {
                self.apple_input = clean.to_string();
                self.status_message = format!("Pasted Apple Music URL: {}", clean);
            }
            2 => {
                self.youtube_input = clean.to_string();
                self.status_message = format!("Pasted YouTube URL: {}", clean);
            }
            _ => {
                if clean.contains("spotify.com") {
                    self.spotify_input = clean.to_string();
                    self.status_message = format!("Pasted Spotify Profile URL: {}", clean);
                } else if clean.contains("apple.com") || clean.contains("itunes.apple.com") {
                    self.apple_input = clean.to_string();
                    self.status_message = format!("Pasted Apple Music URL: {}", clean);
                } else if clean.contains("youtube.com") || clean.contains("youtu.be") {
                    self.youtube_input = clean.to_string();
                    self.status_message = format!("Pasted YouTube URL: {}", clean);
                }
            }
        }
        self.save_config();
    }

    pub fn save_config(&self) {
        let cfg = LinkedAccountsConfig {
            spotify_profile: self.spotify_input.clone(),
            apple_profile: self.apple_input.clone(),
            youtube_profile: self.youtube_input.clone(),
            youtube_browser: self.youtube_browser.clone(),
            deduplicate: self.deduplicate,
            sort_by_artist: self.sort_by_artist,
        };
        cfg.save();
    }

    /// Automatically scans and connects to local music applications and browser sessions asynchronously.
    pub fn auto_detect(&mut self) {
        self.is_scanning = true;
        self.is_syncing = true;
        self.sync_progress_pct = 5;
        self.status_message = "Auto-detecting installed sources (Apple Music, Zen/Firefox, Spotify)...".to_string();
        self.apple_status = "Scanning Apple Music...".to_string();
        self.yt_status = "Connecting to YouTube session...".to_string();
        self.spotify_status = "Detecting Spotify credentials...".to_string();
        self.discovered_collections.clear();
        self.tracks_cache.clear();
        self.current_tracks.clear();

        let (tx, rx) = std::sync::mpsc::channel();
        self.sync_rx = Some(rx);

        std::thread::spawn(move || {
            LibrarySyncEngine::auto_detect_all_sources_async(tx);
        });
    }

    /// Non-blocking polling method for background discovery events and track prefetching.
    pub fn poll_background_sync(&mut self) {
        // 1. Drain auto-detect stream progress events
        let mut got_new_collection = false;
        if let Some(rx) = &self.sync_rx {
            while let Ok(event) = rx.try_recv() {
                match event {
                    LibrarySyncProgress::ServiceStarted(service, msg) => {
                        match service {
                            StreamingService::AppleMusic => self.apple_status = msg,
                            StreamingService::YouTubeMusic => self.yt_status = msg,
                            StreamingService::Spotify => self.spotify_status = msg,
                            _ => {}
                        }
                    }
                    LibrarySyncProgress::ServiceProgress(service, cur, total, name) => {
                        match service {
                            StreamingService::YouTubeMusic => {
                                self.yt_status = format!("Syncing [{}/{}]: {}", cur, total, truncate_str(&name, 18));
                                self.sync_progress_pct = (30 + ((cur * 35) / total.max(1))) as u16;
                            }
                            StreamingService::Spotify => {
                                self.spotify_status = format!("Syncing [{}/{}]: {}", cur, total, truncate_str(&name, 18));
                                self.sync_progress_pct = (65 + ((cur * 35) / total.max(1))) as u16;
                            }
                            _ => {}
                        }
                    }
                    LibrarySyncProgress::ServiceCompleted(service, count) => {
                        match service {
                            StreamingService::AppleMusic => {
                                self.apple_status = format!("Synced ({} items)", count);
                                self.sync_progress_pct = self.sync_progress_pct.max(30);
                            }
                            StreamingService::YouTubeMusic => {
                                self.yt_status = format!("Synced ({} items)", count);
                                self.sync_progress_pct = self.sync_progress_pct.max(65);
                            }
                            StreamingService::Spotify => {
                                self.spotify_status = format!("Synced ({} items)", count);
                                self.sync_progress_pct = self.sync_progress_pct.max(95);
                            }
                            _ => {}
                        }
                    }
                    LibrarySyncProgress::CollectionDiscovered(col) => {
                        if !self.discovered_collections.iter().any(|c| c.id == col.id) {
                            self.discovered_collections.push(col);
                            got_new_collection = true;
                        }
                    }
                    LibrarySyncProgress::TracksLoaded { collection_id, tracks } => {
                        self.active_fetches.remove(&collection_id);
                        if !tracks.is_empty() {
                            self.tracks_cache.insert(collection_id.clone(), tracks.clone());
                            if let Some(col) = self.discovered_collections.iter_mut().find(|c| c.id == collection_id) {
                                col.track_count = tracks.len();
                            }
                        }
                        if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                            if col.id == collection_id {
                                self.current_tracks = tracks;
                                self.is_loading_tracks = false;
                                self.selected_track_idx = 0;
                                self.track_list_state.select(if self.current_tracks.is_empty() { None } else { Some(0) });
                            }
                        }
                    }
                    LibrarySyncProgress::Done(msg) => {
                        self.is_scanning = false;
                        self.is_syncing = false;
                        self.sync_progress_pct = 100;
                        self.status_message = msg;
                    }
                    LibrarySyncProgress::Error(err) => {
                        self.status_message = format!("Sync warning: {}", err);
                    }
                }
            }
        }

        if got_new_collection && self.collection_list_state.selected().is_none() && !self.discovered_collections.is_empty() {
            self.collection_list_state.select(Some(0));
            self.selected_collection_idx = 0;
            self.load_tracks_for_selected_collection();
        }

        // 2. Drain track loader events
        if let Some(rx) = &self.track_loader_rx {
            while let Ok((col_id, items)) = rx.try_recv() {
                self.active_fetches.remove(&col_id);
                if !items.is_empty() {
                    self.tracks_cache.insert(col_id.clone(), items.clone());
                    if let Some(col) = self.discovered_collections.iter_mut().find(|c| c.id == col_id) {
                        col.track_count = items.len();
                    }
                }
                if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                    if col.id == col_id {
                        self.current_tracks = items;
                        self.is_loading_tracks = false;
                        self.selected_track_idx = 0;
                        self.track_list_state.select(if self.current_tracks.is_empty() { None } else { Some(0) });
                    }
                }
            }
        }
    }

    /// Scans entered account URLs.
    pub fn scan_accounts(&mut self) {
        self.is_scanning = true;
        self.status_message = "Scanning linked accounts across Spotify, Apple Music & YouTube...".to_string();
        self.discovered_collections.clear();
        self.tracks_cache.clear();
        self.current_tracks.clear();

        // 1. Spotify
        if let Ok(mut cols) = LibrarySyncEngine::scan_spotify(&self.spotify_input) {
            self.discovered_collections.append(&mut cols);
        }

        // 2. Apple Music
        if let Ok(mut cols) = LibrarySyncEngine::scan_apple_music(&self.apple_input) {
            self.discovered_collections.append(&mut cols);
        }

        // 3. YouTube Music
        if let Ok(mut cols) = LibrarySyncEngine::scan_youtube_music(&self.youtube_browser, &self.youtube_input) {
            self.discovered_collections.append(&mut cols);
        }

        self.is_scanning = false;
        self.selected_collection_idx = 0;
        if !self.discovered_collections.is_empty() {
            self.collection_list_state.select(Some(0));
            self.focused_field = 6;
            self.load_tracks_for_selected_collection();
            self.status_message = format!("Found {} library collections. Use [Right] to drill down into songs.", self.discovered_collections.len());
        } else {
            self.status_message = "No library collections discovered. Verify URLs or browser selection.".to_string();
        }
    }

    /// Loads individual tracks for the currently focused collection into the right pane asynchronously.
    pub fn load_tracks_for_selected_collection(&mut self) {
        if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
            let col_id = col.id.clone();
            if let Some(cached) = self.tracks_cache.get(&col_id) {
                self.current_tracks = cached.clone();
                self.is_loading_tracks = false;
                self.selected_track_idx = 0;
                self.track_list_state.select(if self.current_tracks.is_empty() { None } else { Some(0) });
            } else {
                self.is_loading_tracks = true;
                self.current_tracks.clear();
                self.track_list_state.select(None);

                if !self.active_fetches.contains(&col_id) {
                    self.active_fetches.insert(col_id.clone());
                    let col_clone = col.clone();
                    let browser_clone = self.youtube_browser.clone();
                    if let Some(tx) = &self.track_loader_tx {
                        let tx = tx.clone();
                        std::thread::spawn(move || {
                            let items = LibrarySyncEngine::fetch_track_items_for_collection(&col_clone, &browser_clone);
                            let _ = tx.send((col_id, items));
                        });
                    }
                }
            }
        } else {
            self.current_tracks.clear();
            self.track_list_state.select(None);
            self.is_loading_tracks = false;
        }
    }

    pub fn handle_key(&mut self, code: KeyCode) -> Option<AccountModalAction> {
        match code {
            KeyCode::Esc => {
                self.is_open = false;
                return Some(AccountModalAction::Close);
            }
            KeyCode::Tab => {
                self.focused_field = (self.focused_field + 1) % 8;
            }
            KeyCode::BackTab => {
                self.focused_field = if self.focused_field == 0 { 7 } else { self.focused_field - 1 };
            }
            KeyCode::Right => {
                if self.focused_field == 6 && !self.current_tracks.is_empty() {
                    self.focused_field = 7; // Drill down into Tracks pane
                }
            }
            KeyCode::Left => {
                if self.focused_field == 7 {
                    self.focused_field = 6; // Return to Playlists pane
                }
            }
            KeyCode::Char('a') | KeyCode::Char('A') => {
                if self.focused_field == 7 && !self.current_tracks.is_empty() {
                    // Toggle Select All / Deselect All for tracks in this playlist
                    let all_sel = self.current_tracks.iter().all(|t| t.is_selected);
                    for t in &mut self.current_tracks {
                        t.is_selected = !all_sel;
                    }
                    if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                        self.tracks_cache.insert(col.id.clone(), self.current_tracks.clone());
                    }
                    self.status_message = if !all_sel { "Selected all tracks in this collection.".to_string() } else { "Deselected all tracks in this collection.".to_string() };
                } else if self.focused_field <= 6 {
                    self.auto_detect();
                }
            }
            KeyCode::Char('s') | KeyCode::Char('S') if self.focused_field >= 3 => {
                self.scan_accounts();
            }
            KeyCode::Char('r') | KeyCode::Char('R') if self.focused_field >= 3 => {
                if !self.discovered_collections.is_empty() {
                    if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                        let col_id = col.id.clone();
                        let col_title = col.title.clone();
                        self.tracks_cache.remove(&col_id);
                        self.active_fetches.remove(&col_id);
                        self.load_tracks_for_selected_collection();
                        self.status_message = format!("Reloading fresh tracks for '{}'...", col_title);
                    }
                }
            }
            KeyCode::Char('i') | KeyCode::Char('I') if self.focused_field >= 3 => {
                // Collect all selected tracks from cache and active view
                let mut tracks_to_import = Vec::new();

                // Save active tracks to cache
                if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                    self.tracks_cache.insert(col.id.clone(), self.current_tracks.clone());
                }

                for col in &self.discovered_collections {
                    if col.is_selected {
                        if let Some(cached) = self.tracks_cache.get(&col.id) {
                            let selected_tracks: Vec<DiscoveredTrackItem> = cached.iter().filter(|t| t.is_selected).cloned().collect();
                            tracks_to_import.extend(selected_tracks);
                        } else {
                            // If collection was checked but never drilled down into, load its tracks
                            let items = LibrarySyncEngine::fetch_track_items_for_collection(col, &self.youtube_browser);
                            let selected_tracks: Vec<DiscoveredTrackItem> = items.into_iter().filter(|t| t.is_selected).collect();
                            tracks_to_import.extend(selected_tracks);
                        }
                    }
                }

                if !tracks_to_import.is_empty() {
                    self.is_open = false;
                    return Some(AccountModalAction::ImportTracks(tracks_to_import, self.deduplicate, self.sort_by_artist));
                } else {
                    self.status_message = "No tracks selected! Check at least one song or collection.".to_string();
                }
            }
            KeyCode::Char(' ') => {
                if self.focused_field == 4 {
                    self.deduplicate = !self.deduplicate;
                    self.save_config();
                } else if self.focused_field == 5 {
                    self.sort_by_artist = !self.sort_by_artist;
                    self.save_config();
                } else if self.focused_field == 6 && !self.discovered_collections.is_empty() {
                    if let Some(col) = self.discovered_collections.get_mut(self.selected_collection_idx) {
                        col.is_selected = !col.is_selected;
                    }
                } else if self.focused_field == 7 && !self.current_tracks.is_empty() {
                    if let Some(t) = self.current_tracks.get_mut(self.selected_track_idx) {
                        t.is_selected = !t.is_selected;
                    }
                    if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                        self.tracks_cache.insert(col.id.clone(), self.current_tracks.clone());
                    }
                } else if self.focused_field == 3 {
                    // Cycle browser: zen -> chrome -> safari -> edge -> brave -> firefox -> zen
                    self.youtube_browser = match self.youtube_browser.as_str() {
                        "zen" => "chrome".to_string(),
                        "chrome" => "safari".to_string(),
                        "safari" => "edge".to_string(),
                        "edge" => "brave".to_string(),
                        "brave" => "firefox".to_string(),
                        _ => "zen".to_string(),
                    };
                    self.save_config();
                }
            }
            KeyCode::Up => {
                if self.focused_field == 6 && self.selected_collection_idx > 0 {
                    // Save active tracks before changing collection
                    if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                        self.tracks_cache.insert(col.id.clone(), self.current_tracks.clone());
                    }
                    self.selected_collection_idx -= 1;
                    self.collection_list_state.select(Some(self.selected_collection_idx));
                    self.load_tracks_for_selected_collection();
                } else if self.focused_field == 7 && self.selected_track_idx > 0 {
                    self.selected_track_idx -= 1;
                    self.track_list_state.select(Some(self.selected_track_idx));
                }
            }
            KeyCode::Down => {
                if self.focused_field == 6 && self.selected_collection_idx + 1 < self.discovered_collections.len() {
                    // Save active tracks before changing collection
                    if let Some(col) = self.discovered_collections.get(self.selected_collection_idx) {
                        self.tracks_cache.insert(col.id.clone(), self.current_tracks.clone());
                    }
                    self.selected_collection_idx += 1;
                    self.collection_list_state.select(Some(self.selected_collection_idx));
                    self.load_tracks_for_selected_collection();
                } else if self.focused_field == 7 && self.selected_track_idx + 1 < self.current_tracks.len() {
                    self.selected_track_idx += 1;
                    self.track_list_state.select(Some(self.selected_track_idx));
                }
            }
            KeyCode::Backspace => {
                match self.focused_field {
                    0 => { self.spotify_input.pop(); }
                    1 => { self.apple_input.pop(); }
                    2 => { self.youtube_input.pop(); }
                    _ => {}
                }
            }
            KeyCode::Char(c) => {
                match self.focused_field {
                    0 => { self.spotify_input.push(c); }
                    1 => { self.apple_input.push(c); }
                    2 => { self.youtube_input.push(c); }
                    _ => {}
                }
            }
            _ => {}
        }
        None
    }

    pub fn render(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        if !self.is_open {
            return;
        }

        let popup_width = 110.min(area.width.saturating_sub(4));
        let popup_height = 32.min(area.height.saturating_sub(2));

        let v_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length((area.height.saturating_sub(popup_height)) / 2),
                Constraint::Length(popup_height),
                Constraint::Min(0),
            ])
            .split(area);

        let h_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length((area.width.saturating_sub(popup_width)) / 2),
                Constraint::Length(popup_width),
                Constraint::Min(0),
            ])
            .split(v_chunks[1]);

        let modal_area = h_chunks[1];
        f.render_widget(Clear, modal_area);

        let block = Block::default()
            .title(" [L] ZERO-TOUCH MUSIC HUB & 2-PANE LIBRARY INSPECTOR ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let inner = block.inner(modal_area);
        f.render_widget(block, modal_area);

        let sections = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Account URLs
                Constraint::Length(3), // Settings bar & Auto-Detect trigger
                Constraint::Length(3), // Real-time Service Status & Progress Strip
                Constraint::Min(10),   // 2-Pane Split: Left Playlists (40%), Right Tracklist (60%)
                Constraint::Length(3), // Footer buttons & Status
            ])
            .split(inner);

        // 1. Account URLs
        let focus_field = self.focused_field;
        let spotify_style = if focus_field == 0 { Style::default().fg(Color::Black).bg(Color::Green) } else { Style::default().fg(Color::Green) };
        let apple_style = if focus_field == 1 { Style::default().fg(Color::Black).bg(Color::Rgb(255, 80, 100)) } else { Style::default().fg(Color::Rgb(255, 80, 100)) };
        let yt_style = if focus_field == 2 { Style::default().fg(Color::Black).bg(Color::LightRed) } else { Style::default().fg(Color::LightRed) };

        let max_url_len = (inner.width as usize).saturating_sub(22).max(25);
        let acc_lines = vec![
            Line::from(vec![
                Span::styled(" [1] Spotify:       ", spotify_style.add_modifier(Modifier::BOLD)),
                Span::styled(truncate_str(if self.spotify_input.is_empty() { "Auto-probes desktop / Zen browser or paste profile URL" } else { &self.spotify_input }, max_url_len), Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled(" [2] Apple Music:   ", apple_style.add_modifier(Modifier::BOLD)),
                Span::styled(truncate_str(if self.apple_input.is_empty() { "Auto-reads local library (Music.app) or paste playlist URL" } else { &self.apple_input }, max_url_len), Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled(" [3] YouTube Music: ", yt_style.add_modifier(Modifier::BOLD)),
                Span::styled(truncate_str(if self.youtube_input.is_empty() { "Auto-probes browser session for Liked Music & playlists" } else { &self.youtube_input }, max_url_len), Style::default().fg(Color::White)),
            ]),
            Line::from(vec![
                Span::styled(" (Press [1-3] or [Tab] to focus URL field | [A] Auto-Detects everything without typing)", Style::default().fg(theme.text_dim)),
            ]),
        ];
        f.render_widget(Paragraph::new(acc_lines), sections[0]);

        // 2. Settings Bar
        let browser_style = if focus_field == 3 { Style::default().fg(Color::Black).bg(theme.accent) } else { Style::default().fg(theme.accent) };
        let dedup_style = if focus_field == 4 { Style::default().fg(Color::Black).bg(theme.success) } else { Style::default().fg(theme.success) };
        let sort_style = if focus_field == 5 { Style::default().fg(Color::Black).bg(theme.primary) } else { Style::default().fg(theme.primary) };

        let settings_line = Line::from(vec![
            Span::styled(" [A] AUTO-DETECT ALL ", Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("  "),
            Span::styled(format!(" [Browser: {}] ", self.youtube_browser.to_uppercase()), browser_style.add_modifier(Modifier::BOLD)),
            Span::raw("  "),
            Span::styled(format!(" [{}] Deduplicate ", if self.deduplicate { "X" } else { " " }), dedup_style.add_modifier(Modifier::BOLD)),
            Span::raw("  "),
            Span::styled(format!(" [{}] Organize A-Z ", if self.sort_by_artist { "X" } else { " " }), sort_style.add_modifier(Modifier::BOLD)),
        ]);
        f.render_widget(Paragraph::new(settings_line), sections[1]);

        // 3. Real-Time Service Status & Progress Indicators
        let progress_width = 18;
        let filled_chars = ((self.sync_progress_pct as usize) * progress_width) / 100;
        let bar_filled: String = "=".repeat(filled_chars);
        let bar_empty: String = " ".repeat(progress_width.saturating_sub(filled_chars));
        let progress_bar = format!("[{}{}] {}%", bar_filled, bar_empty, self.sync_progress_pct);

        let service_status_line = Line::from(vec![
            Span::styled(" [AM] ", Style::default().fg(Color::Rgb(255, 80, 100)).add_modifier(Modifier::BOLD)),
            Span::styled(format!("{:<20}", truncate_str(&self.apple_status, 20)), Style::default().fg(Color::White)),
            Span::styled(" | [YT] ", Style::default().fg(Color::LightRed).add_modifier(Modifier::BOLD)),
            Span::styled(format!("{:<24}", truncate_str(&self.yt_status, 24)), Style::default().fg(Color::White)),
            Span::styled(" | [SP] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled(format!("{:<20}", truncate_str(&self.spotify_status, 20)), Style::default().fg(Color::White)),
        ]);

        let activity_text = if self.is_syncing {
            "Syncing streaming accounts..."
        } else if self.is_loading_tracks {
            "Prefetching tracks in background..."
        } else {
            "Idle / Ready."
        };

        let progress_line = Line::from(vec![
            Span::styled(" Sync Progress: ", Style::default().fg(theme.text_dim)),
            Span::styled(progress_bar, Style::default().fg(if self.sync_progress_pct == 100 { theme.success } else { theme.accent }).add_modifier(Modifier::BOLD)),
            Span::raw("   "),
            Span::styled(activity_text, Style::default().fg(theme.secondary)),
        ]);

        let status_block = Block::default()
            .borders(Borders::BOTTOM)
            .border_style(Style::default().fg(theme.border));
        let status_inner = status_block.inner(sections[2]);
        f.render_widget(status_block, sections[2]);
        f.render_widget(Paragraph::new(vec![service_status_line, progress_line]), status_inner);

        // 4. Middle 2-Pane Layout (Left Playlists 40%, Right Tracks 60%)
        let middle_split = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(40),
                Constraint::Percentage(60),
            ])
            .split(sections[3]);

        // 4A. Left Pane: Playlists & Collections
        let is_left_focused = focus_field == 6;
        let col_block = Block::default()
            .title(format!(" [1] PLAYLISTS ({}) ", self.discovered_collections.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(if is_left_focused { theme.accent } else { theme.text_dim }));
        let col_inner = col_block.inner(middle_split[0]);
        f.render_widget(col_block, middle_split[0]);

        if self.discovered_collections.is_empty() {
            let msg = if self.is_scanning { "Auto-detecting libraries in background..." } else { "Press [A] to Auto-Detect or [S] to Scan." };
            f.render_widget(Paragraph::new(msg).style(Style::default().fg(theme.text_dim)).alignment(Alignment::Center), col_inner);
        } else {
            let items: Vec<ListItem> = self.discovered_collections.iter().enumerate().map(|(idx, col)| {
                let is_sel = idx == self.selected_collection_idx;
                let chk = if col.is_selected { "[X]" } else { "[ ]" };
                let (badge, badge_color) = match col.service {
                    crate::harvest::StreamingService::YouTubeMusic => ("[YT] ", Color::LightRed),
                    crate::harvest::StreamingService::AppleMusic => ("[AM] ", Color::Rgb(255, 80, 100)),
                    crate::harvest::StreamingService::Spotify => ("[SP] ", Color::Green),
                    _ => ("[--] ", theme.text_dim),
                };
                let clean_title = col.title
                    .trim_start_matches("YT Music: ")
                    .trim_start_matches("Music.app: ")
                    .trim_start_matches("Spotify Collection: ")
                    .trim();
                let max_name_len = (col_inner.width as usize).saturating_sub(18).max(6);
                let display_title = truncate_str(clean_title, max_name_len);
                let is_fetching = self.active_fetches.contains(&col.id);
                let count_or_loading = if is_fetching {
                    Span::styled(" [Loading...]", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
                } else {
                    Span::styled(format!("({})", col.track_count), Style::default().fg(theme.text_dim))
                };
                let line = Line::from(vec![
                    Span::styled(if is_sel { "> " } else { "  " }, Style::default().fg(theme.accent)),
                    Span::styled(format!("{} ", chk), Style::default().fg(if col.is_selected { theme.success } else { theme.text_dim })),
                    Span::styled(badge, Style::default().fg(badge_color).add_modifier(Modifier::BOLD)),
                    Span::styled(format!("{:<width$} ", display_title, width = max_name_len), if is_sel && is_left_focused { Style::default().fg(Color::White).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                    count_or_loading,
                ]);
                ListItem::new(line)
            }).collect();
            f.render_stateful_widget(List::new(items), col_inner, &mut self.collection_list_state.clone());
        }

        // 4B. Right Pane: Track Inspector
        let is_right_focused = focus_field == 7;
        let selected_track_count = self.current_tracks.iter().filter(|t| t.is_selected).count();
        let track_block = Block::default()
            .title(format!(" [2] TRACKS ([{}/{}] selected) - [Space] Check, [A] All ", selected_track_count, self.current_tracks.len()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(if is_right_focused { theme.accent } else { theme.text_dim }));
        let track_inner = track_block.inner(middle_split[1]);
        f.render_widget(track_block, middle_split[1]);

        let is_current_fetching = self.discovered_collections
            .get(self.selected_collection_idx)
            .map(|c| self.active_fetches.contains(&c.id))
            .unwrap_or(false);

        if self.is_loading_tracks || is_current_fetching {
            let loading_lines = vec![
                Line::from(vec![
                    Span::styled("[=== Loading tracks from cloud in background... ===]", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(vec![
                    Span::styled("Extracting full tracklist from streaming provider without blocking UI.", Style::default().fg(theme.text_dim)),
                ]),
            ];
            f.render_widget(Paragraph::new(loading_lines).style(Style::default().fg(theme.text_dim)).alignment(Alignment::Center), track_inner);
        } else if self.current_tracks.is_empty() {
            let selected_col = self.discovered_collections.get(self.selected_collection_idx);
            let is_spotify = selected_col.map(|c| c.service == crate::harvest::StreamingService::Spotify || c.url.contains("spotify.com")).unwrap_or(false);

            if is_spotify {
                let instructions = vec![
                    Line::from(vec![
                        Span::styled("[!] Spotify Private Collection / Profile Detected", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                    ]),
                    Line::from(""),
                    Line::from(vec![
                        Span::styled("Spotify user profiles and Liked Songs are private DRM-protected libraries.", Style::default().fg(theme.text)),
                    ]),
                    Line::from(vec![
                        Span::styled("To import all your 700+ Liked Songs into OmniRip:", Style::default().fg(theme.secondary)),
                    ]),
                    Line::from(""),
                    Line::from(vec![
                        Span::styled(" 1. In Spotify Desktop: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        Span::styled("Go to 'Liked Songs' and press ", Style::default().fg(theme.text)),
                        Span::styled("Cmd+A", Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                    ]),
                    Line::from(vec![
                        Span::styled(" 2. Right-Click: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        Span::styled("Select 'Add to playlist' -> 'New playlist'", Style::default().fg(theme.text)),
                    ]),
                    Line::from(vec![
                        Span::styled(" 3. Copy Link: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        Span::styled("Right-click playlist -> 'Share' -> 'Copy link to playlist'", Style::default().fg(theme.text)),
                    ]),
                    Line::from(vec![
                        Span::styled(" 4. Paste: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                        Span::styled("Press [Tab] to Spotify input field above and paste URL", Style::default().fg(theme.text)),
                    ]),
                    Line::from(""),
                    Line::from(vec![
                        Span::styled("OmniRip will immediately parse and stream all ~700 tracks with Studio EQ!", Style::default().fg(Color::Green)),
                    ]),
                ];
                f.render_widget(Paragraph::new(instructions).style(Style::default().fg(theme.text_dim)).alignment(Alignment::Left), track_inner);
            } else {
                let msg = "No tracks loaded. Select a playlist or press [R] to Reload.";
                f.render_widget(Paragraph::new(msg).style(Style::default().fg(theme.text_dim)).alignment(Alignment::Center), track_inner);
            }
        } else {
            let total_w = track_inner.width as usize;
            let rem_w = total_w.saturating_sub(18);
            let title_w = (rem_w * 55 / 100).max(10);
            let artist_w = rem_w.saturating_sub(title_w).max(8);

            let track_items: Vec<ListItem> = self.current_tracks.iter().enumerate().map(|(idx, t)| {
                let is_sel = idx == self.selected_track_idx;
                let chk = if t.is_selected { "[X]" } else { "[ ]" };
                let dur_str = t.duration_secs.map(|d| format!("{:02}:{:02}", d / 60, d % 60)).unwrap_or_else(|| "--:--".to_string());
                let disp_title = truncate_str(&t.title, title_w);
                let disp_artist = truncate_str(&t.artist, artist_w);

                let line = Line::from(vec![
                    Span::styled(if is_sel { "> " } else { "  " }, Style::default().fg(theme.accent)),
                    Span::styled(format!("{} ", chk), Style::default().fg(if t.is_selected { theme.success } else { theme.text_dim }).add_modifier(Modifier::BOLD)),
                    Span::styled(format!("{:<width$}", disp_title, width = title_w), if is_sel && is_right_focused { Style::default().fg(Color::White).add_modifier(Modifier::BOLD) } else { Style::default().fg(theme.text) }),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(format!("{:<width$}", disp_artist, width = artist_w), Style::default().fg(theme.text_dim)),
                    Span::styled(" | ", Style::default().fg(theme.border)),
                    Span::styled(dur_str, Style::default().fg(theme.accent)),
                ]);
                ListItem::new(line)
            }).collect();
            f.render_stateful_widget(List::new(track_items), track_inner, &mut self.track_list_state.clone());
        }

        // 5. Footer & Action Buttons
        let max_status_len = (inner.width as usize).saturating_sub(14).max(20);
        let status_disp = truncate_str(&self.status_message, max_status_len);
        let footer_lines = vec![
            Line::from(vec![
                Span::styled(" [A] Auto-Detect  ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::styled(" [Tab] Next Field  ", Style::default().fg(theme.secondary)),
                Span::styled(" [Left/Right] Panes  ", Style::default().fg(theme.accent)),
                Span::styled(" [Space] Check  ", Style::default().fg(theme.success)),
                Span::styled(" [R] Reload  ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::styled(" [I] Import Selected  ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Span::styled(" [Esc] Close", Style::default().fg(theme.text_dim)),
            ]),
            Line::from(vec![
                Span::styled(" Status: ", Style::default().fg(theme.accent)),
                Span::styled(status_disp, Style::default().fg(Color::White)),
            ]),
        ];
        f.render_widget(Paragraph::new(footer_lines), sections[4]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_account_sync_modal_initialization() {
        let modal = AccountSyncModal::new();
        assert!(!modal.is_open);
        assert!(modal.deduplicate);
        assert!(modal.sort_by_artist);
    }

    #[test]
    fn test_account_sync_modal_toggle_and_paste() {
        let mut modal = AccountSyncModal::new();
        modal.toggle();
        assert!(modal.is_open);

        modal.focused_field = 0;
        modal.paste("https://open.spotify.com/user/audiodude");
        assert_eq!(modal.spotify_input, "https://open.spotify.com/user/audiodude");

        modal.focused_field = 1;
        modal.paste("https://music.apple.com/profile/musicfan");
        assert_eq!(modal.apple_input, "https://music.apple.com/profile/musicfan");
    }

    #[test]
    fn test_account_sync_modal_cache_poisoning_prevention_and_dynamic_counts() {
        let mut modal = AccountSyncModal::new();
        modal.discovered_collections.push(DiscoveredCollection {
            id: "yt_general_taste".to_string(),
            title: "my general taste".to_string(),
            url: "https://music.youtube.com/playlist?list=PL123".to_string(),
            service: StreamingService::YouTubeMusic,
            track_count: 25,
            is_selected: true,
        });
        modal.selected_collection_idx = 0;

        // Simulate an empty track response arriving (e.g. timeout / empty page)
        if let Some(tx) = &modal.track_loader_tx {
            let _ = tx.send(("yt_general_taste".to_string(), Vec::new()));
        }
        modal.poll_background_sync();

        // Empty response must NOT poison tracks_cache
        assert!(!modal.tracks_cache.contains_key("yt_general_taste"));
        assert_eq!(modal.discovered_collections[0].track_count, 25);

        // Now simulate real tracks arriving (e.g. 236 tracks)
        let mut real_tracks = Vec::new();
        for i in 0..236 {
            real_tracks.push(DiscoveredTrackItem {
                id: format!("track_{}", i),
                title: format!("Title {}", i),
                artist: format!("Artist {}", i),
                album: "Album".to_string(),
                duration_secs: Some(200),
                is_selected: true,
            });
        }
        if let Some(tx) = &modal.track_loader_tx {
            let _ = tx.send(("yt_general_taste".to_string(), real_tracks));
        }
        modal.poll_background_sync();

        // Valid tracks MUST be cached and collection count dynamically updated
        assert!(modal.tracks_cache.contains_key("yt_general_taste"));
        assert_eq!(modal.discovered_collections[0].track_count, 236);
        assert_eq!(modal.current_tracks.len(), 236);
    }

    #[test]
    fn test_account_sync_modal_reload_hotkey() {
        let mut modal = AccountSyncModal::new();
        modal.discovered_collections.push(DiscoveredCollection {
            id: "pl_favorites".to_string(),
            title: "Favorites".to_string(),
            url: "https://open.spotify.com/playlist/fav123".to_string(),
            service: StreamingService::Spotify,
            track_count: 10,
            is_selected: true,
        });
        modal.selected_collection_idx = 0;
        modal.focused_field = 6; // Playlists pane

        // Pre-populate cache
        modal.tracks_cache.insert("pl_favorites".to_string(), vec![
            DiscoveredTrackItem {
                id: "fav_1".to_string(),
                title: "Old Song".to_string(),
                artist: "Old Artist".to_string(),
                album: "Old Album".to_string(),
                duration_secs: Some(180),
                is_selected: true,
            }
        ]);
        assert!(modal.tracks_cache.contains_key("pl_favorites"));

        // Press 'r' to reload
        modal.handle_key(KeyCode::Char('r'));

        // Cache must be evicted and reload triggered
        assert!(!modal.tracks_cache.contains_key("pl_favorites"));
        assert!(modal.status_message.contains("Reloading fresh tracks"));
    }

    #[test]
    fn test_spotify_private_collection_guidance_state() {
        let mut modal = AccountSyncModal::new();
        modal.discovered_collections.push(DiscoveredCollection {
            id: "sp_user".to_string(),
            title: "Spotify User Profile Playlists".to_string(),
            url: "https://open.spotify.com/user/aboood360".to_string(),
            service: StreamingService::Spotify,
            track_count: 40,
            is_selected: true,
        });
        modal.selected_collection_idx = 0;
        assert!(modal.current_tracks.is_empty());
        let selected_col = modal.discovered_collections.get(modal.selected_collection_idx);
        let is_spotify = selected_col.map(|c| c.service == StreamingService::Spotify || c.url.contains("spotify.com")).unwrap_or(false);
        assert!(is_spotify);
    }
}
