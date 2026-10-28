use crate::harvest::playlist_parser::{ParsedTrack, PlaylistParser, StreamingService};
use crate::harvest::title_cleaner::clean_title;
use crate::ui::streaming_hub::StreamQueueItem;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DividerPlatformPriority {
    #[default]
    SpotifyFirst,
    AppleMusicFirst,
    YouTubeFirst,
}

impl DividerPlatformPriority {
    pub fn label(&self) -> &'static str {
        match self {
            DividerPlatformPriority::SpotifyFirst => "Spotify First (Spotify → Apple → YouTube)",
            DividerPlatformPriority::AppleMusicFirst => "Apple Music First (Apple → Spotify → YouTube)",
            DividerPlatformPriority::YouTubeFirst => "YouTube Music First (YouTube → Spotify → Apple)",
        }
    }

    pub fn short_label(&self) -> &'static str {
        match self {
            DividerPlatformPriority::SpotifyFirst => "Spotify 1st",
            DividerPlatformPriority::AppleMusicFirst => "Apple 1st",
            DividerPlatformPriority::YouTubeFirst => "YouTube 1st",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            DividerPlatformPriority::SpotifyFirst => DividerPlatformPriority::AppleMusicFirst,
            DividerPlatformPriority::AppleMusicFirst => DividerPlatformPriority::YouTubeFirst,
            DividerPlatformPriority::YouTubeFirst => DividerPlatformPriority::SpotifyFirst,
        }
    }

    pub fn rank(&self, service: StreamingService) -> u8 {
        match self {
            DividerPlatformPriority::SpotifyFirst => match service {
                StreamingService::Spotify => 0,
                StreamingService::AppleMusic => 1,
                StreamingService::YouTubeMusic => 2,
                _ => 3,
            },
            DividerPlatformPriority::AppleMusicFirst => match service {
                StreamingService::AppleMusic => 0,
                StreamingService::Spotify => 1,
                StreamingService::YouTubeMusic => 2,
                _ => 3,
            },
            DividerPlatformPriority::YouTubeFirst => match service {
                StreamingService::YouTubeMusic => 0,
                StreamingService::Spotify => 1,
                StreamingService::AppleMusic => 2,
                _ => 3,
            },
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DividerSubSort {
    #[default]
    LatestAdded,
    OldestAdded,
    ArtistAZ,
    TitleAZ,
    DurationShortest,
    DurationLongest,
}

impl DividerSubSort {
    pub fn label(&self) -> &'static str {
        match self {
            DividerSubSort::LatestAdded => "Newest to Oldest (Latest Added)",
            DividerSubSort::OldestAdded => "Oldest to Newest (Playlist Order)",
            DividerSubSort::ArtistAZ => "Artist (A - Z)",
            DividerSubSort::TitleAZ => "Title (A - Z)",
            DividerSubSort::DurationShortest => "Duration (Shortest)",
            DividerSubSort::DurationLongest => "Duration (Longest)",
        }
    }

    pub fn short_label(&self) -> &'static str {
        match self {
            DividerSubSort::LatestAdded => "Newest → Oldest",
            DividerSubSort::OldestAdded => "Oldest → Newest",
            DividerSubSort::ArtistAZ => "Artist A-Z",
            DividerSubSort::TitleAZ => "Title A-Z",
            DividerSubSort::DurationShortest => "Shortest",
            DividerSubSort::DurationLongest => "Longest",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            DividerSubSort::LatestAdded => DividerSubSort::OldestAdded,
            DividerSubSort::OldestAdded => DividerSubSort::ArtistAZ,
            DividerSubSort::ArtistAZ => DividerSubSort::TitleAZ,
            DividerSubSort::TitleAZ => DividerSubSort::DurationShortest,
            DividerSubSort::DurationShortest => DividerSubSort::DurationLongest,
            DividerSubSort::DurationLongest => DividerSubSort::LatestAdded,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TrackSortMode {
    LatestAdded,
    OldestAdded,
    TitleAZ,
    TitleZA,
    ArtistAZ,
    ArtistZA,
    DurationShortest,
    DurationLongest,
    PlatformDividers,
}

impl TrackSortMode {
    pub fn label(&self) -> &'static str {
        match self {
            TrackSortMode::LatestAdded => "Latest Added",
            TrackSortMode::OldestAdded => "Oldest Added",
            TrackSortMode::TitleAZ => "Title A-Z",
            TrackSortMode::TitleZA => "Title Z-A",
            TrackSortMode::ArtistAZ => "Artist A-Z",
            TrackSortMode::ArtistZA => "Artist Z-A",
            TrackSortMode::DurationShortest => "Duration (Shortest)",
            TrackSortMode::DurationLongest => "Duration (Longest)",
            TrackSortMode::PlatformDividers => "Platform & Library Dividers",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            TrackSortMode::LatestAdded => TrackSortMode::OldestAdded,
            TrackSortMode::OldestAdded => TrackSortMode::TitleAZ,
            TrackSortMode::TitleAZ => TrackSortMode::TitleZA,
            TrackSortMode::TitleZA => TrackSortMode::ArtistAZ,
            TrackSortMode::ArtistAZ => TrackSortMode::ArtistZA,
            TrackSortMode::ArtistZA => TrackSortMode::DurationShortest,
            TrackSortMode::DurationShortest => TrackSortMode::DurationLongest,
            TrackSortMode::DurationLongest => TrackSortMode::PlatformDividers,
            TrackSortMode::PlatformDividers => TrackSortMode::LatestAdded,
        }
    }
}

fn default_sort_mode() -> TrackSortMode {
    TrackSortMode::ArtistAZ
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinkedAccountsConfig {
    #[serde(default)]
    pub spotify_profile: String,
    #[serde(default)]
    pub spotify_sources: Vec<String>,
    pub apple_profile: String,
    pub youtube_profile: String,
    pub youtube_browser: String,
    pub deduplicate: bool,
    #[serde(default = "default_sort_mode")]
    pub sort_mode: TrackSortMode,
    #[serde(default)]
    pub sort_by_artist: Option<bool>,
    #[serde(default)]
    pub divider_platform_priority: DividerPlatformPriority,
    #[serde(default)]
    pub divider_sub_sort: DividerSubSort,
}

impl Default for LinkedAccountsConfig {
    fn default() -> Self {
        Self {
            spotify_profile: String::new(),
            spotify_sources: Vec::new(),
            apple_profile: String::new(),
            youtube_profile: String::new(),
            youtube_browser: "chrome".to_string(),
            deduplicate: true,
            sort_mode: TrackSortMode::ArtistAZ,
            sort_by_artist: None,
            divider_platform_priority: DividerPlatformPriority::SpotifyFirst,
            divider_sub_sort: DividerSubSort::LatestAdded,
        }
    }
}

impl LinkedAccountsConfig {
    pub fn config_path() -> PathBuf {
        if let Ok(home) = std::env::var("HOME") {
            PathBuf::from(home).join(".config").join("omnirip").join("accounts.json")
        } else if let Ok(user_profile) = std::env::var("USERPROFILE") {
            PathBuf::from(user_profile).join(".config").join("omnirip").join("accounts.json")
        } else {
            PathBuf::from(".config/omnirip/accounts.json")
        }
    }

    pub fn load() -> Self {
        let path = Self::config_path();
        if !path.exists() {
            return Self::default();
        }

        if let Ok(mut file) = File::open(&path) {
            let mut contents = String::new();
            if file.read_to_string(&mut contents).is_ok() {
                if let Ok(mut cfg) = serde_json::from_str::<LinkedAccountsConfig>(&contents) {
                    if cfg.spotify_sources.is_empty() && !cfg.spotify_profile.trim().is_empty() {
                        cfg.spotify_sources.push(cfg.spotify_profile.trim().to_string());
                    }
                    if let Some(by_artist) = cfg.sort_by_artist {
                        if !by_artist && cfg.sort_mode == TrackSortMode::ArtistAZ {
                            cfg.sort_mode = TrackSortMode::LatestAdded;
                        }
                    }
                    return cfg;
                }
            }
        }
        Self::default()
    }

    pub fn save(&self) {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(json) = serde_json::to_string_pretty(self) {
            if let Ok(mut file) = File::create(&path) {
                let _ = file.write_all(json.as_bytes());
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DiscoveredCollection {
    pub id: String,
    pub title: String,
    pub service: StreamingService,
    pub track_count: usize,
    pub url: String,
    pub is_selected: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DiscoveredTrackItem {
    pub id: String,
    pub title: String,
    pub artist: String,
    pub album: String,
    pub duration_secs: Option<u32>,
    pub is_selected: bool,
    #[serde(default)]
    pub library_name: String,
    #[serde(default)]
    pub service: StreamingService,
    #[serde(default)]
    pub added_order: u64,
}

#[derive(Debug, Clone)]
pub enum LibrarySyncProgress {
    ServiceStarted(StreamingService, String),
    ServiceProgress(StreamingService, usize, usize, String),
    ServiceCompleted(StreamingService, usize),
    CollectionDiscovered(DiscoveredCollection),
    TracksLoaded { collection_id: String, tracks: Vec<DiscoveredTrackItem> },
    Done(String),
    Error(String),
}

pub struct LibrarySyncEngine;

impl LibrarySyncEngine {
    /// Detects the user's active Zen Browser profile on macOS or Windows.
    pub fn detect_zen_browser_profiles() -> Option<PathBuf> {
        let base_dir = if let Ok(home) = std::env::var("HOME") {
            PathBuf::from(home).join("Library").join("Application Support").join("zen").join("Profiles")
        } else if let Ok(appdata) = std::env::var("APPDATA") {
            PathBuf::from(appdata).join("zen").join("Profiles")
        } else {
            return None;
        };

        if !base_dir.exists() {
            return None;
        }

        if let Ok(entries) = fs::read_dir(&base_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let file_name = path.file_name().and_then(|f| f.to_str()).unwrap_or("");
                    if file_name.contains("Default") || file_name.contains("default") {
                        let cookies_db = path.join("cookies.sqlite");
                        if cookies_db.exists() {
                            return Some(path);
                        }
                    }
                }
            }
        }
        None
    }

    /// Detects all installed web browsers on macOS, Windows, and Linux.
    pub fn detect_installed_browsers() -> Vec<String> {
        let mut browsers = Vec::new();

        let home_path = std::env::var("HOME").ok().map(PathBuf::from);
        let local_path = std::env::var("LOCALAPPDATA").ok().map(PathBuf::from);
        let appdata_path = std::env::var("APPDATA").ok().map(PathBuf::from);

        // 1. Zen Browser
        if Self::detect_zen_browser_profiles().is_some() {
            browsers.push("zen".to_string());
        }

        // 2. Google Chrome
        let chrome_exists = if let Some(ref home) = home_path {
            home.join("Library/Application Support/Google/Chrome").exists()
                || home.join(".config/google-chrome").exists()
        } else if let Some(ref local) = local_path {
            local.join("Google/Chrome/User Data").exists()
        } else {
            false
        };
        if chrome_exists {
            browsers.push("chrome".to_string());
        }

        // 3. Brave Browser
        let brave_exists = if let Some(ref home) = home_path {
            home.join("Library/Application Support/BraveSoftware/Brave-Browser").exists()
                || home.join(".config/BraveSoftware/Brave-Browser").exists()
        } else if let Some(ref local) = local_path {
            local.join("BraveSoftware/Brave-Browser/User Data").exists()
        } else {
            false
        };
        if brave_exists {
            browsers.push("brave".to_string());
        }

        // 4. Mozilla Firefox
        let firefox_exists = if let Some(ref home) = home_path {
            home.join("Library/Application Support/Firefox/Profiles").exists()
                || home.join(".mozilla/firefox").exists()
        } else if let Some(ref appdata) = appdata_path {
            appdata.join("Mozilla/Firefox/Profiles").exists()
        } else {
            false
        };
        if firefox_exists {
            browsers.push("firefox".to_string());
        }

        // 5. Apple Safari (macOS)
        #[cfg(target_os = "macos")]
        {
            if let Some(ref home) = home_path {
                if home.join("Library/Safari").exists() {
                    browsers.push("safari".to_string());
                }
            }
        }

        // 6. Microsoft Edge
        let edge_exists = if let Some(ref home) = home_path {
            home.join("Library/Application Support/Microsoft Edge").exists()
                || home.join(".config/microsoft-edge").exists()
        } else if let Some(ref local) = local_path {
            local.join("Microsoft/Edge/User Data").exists()
        } else {
            false
        };
        if edge_exists {
            browsers.push("edge".to_string());
        }

        if browsers.is_empty() {
            browsers.push("chrome".to_string());
        }

        browsers
    }

    /// Reads the Spotify session token (sp_dc) from Zen Browser cookies if available.
    pub fn detect_zen_spotify_cookie() -> Option<String> {
        if let Some(profile_dir) = Self::detect_zen_browser_profiles() {
            let cookies_db = profile_dir.join("cookies.sqlite");
            if cookies_db.exists() {
                let snap_path = std::env::temp_dir().join("omnirip_zen_spotify_snap.sqlite");
                if fs::copy(&cookies_db, &snap_path).is_ok() {
                    let query = "SELECT value FROM moz_cookies WHERE name='sp_dc' AND host LIKE '%spotify%' LIMIT 1;";
                    if let Ok(output) = Command::new("sqlite3").args([snap_path.to_str().unwrap_or(""), query]).output() {
                        let val = String::from_utf8_lossy(&output.stdout).trim().to_string();
                        let _ = fs::remove_file(&snap_path);
                        if !val.is_empty() {
                            return Some(val);
                        }
                    }
                    let _ = fs::remove_file(&snap_path);
                }
            }
        }
        None
    }

    /// Extracts the active Spotify username from Zen Browser localStorage if available.
    pub fn detect_zen_spotify_username() -> Option<String> {
        if let Some(profile_dir) = Self::detect_zen_browser_profiles() {
            let ls_dir = profile_dir.join("storage").join("default").join("https+++open.spotify.com").join("ls");
            let data_sqlite = ls_dir.join("data.sqlite");
            if data_sqlite.exists() {
                let snap_path = std::env::temp_dir().join("omnirip_zen_spotify_ls_snap.sqlite");
                if fs::copy(&data_sqlite, &snap_path).is_ok() {
                    let query = "SELECT key FROM data WHERE key LIKE '%:ylx-active-filter-ids%' LIMIT 1;";
                    if let Ok(output) = Command::new("sqlite3").args([snap_path.to_str().unwrap_or(""), query]).output() {
                        let key_str = String::from_utf8_lossy(&output.stdout).trim().to_string();
                        let _ = fs::remove_file(&snap_path);
                        if let Some((user, _)) = key_str.split_once(':') {
                            if !user.trim().is_empty() {
                                return Some(user.trim().to_string());
                            }
                        }
                    }
                    let _ = fs::remove_file(&snap_path);
                }
            }
        }
        None
    }

    /// Auto-detects all installed streaming sources and accounts without requiring manual link entry.
    pub fn auto_detect_all_sources() -> Vec<DiscoveredCollection> {
        let (tx, rx) = std::sync::mpsc::channel();
        Self::auto_detect_all_sources_async(tx);
        let mut collections = Vec::new();
        while let Ok(event) = rx.recv() {
            match event {
                LibrarySyncProgress::CollectionDiscovered(col) => collections.push(col),
                LibrarySyncProgress::Done(_) | LibrarySyncProgress::Error(_) => break,
                _ => {}
            }
        }
        collections
    }

    /// Asynchronously auto-detects all installed streaming sources and accounts, emitting real-time progress events.
    pub fn auto_detect_all_sources_async(tx: std::sync::mpsc::Sender<LibrarySyncProgress>) {
        // 1. Apple Music (macOS native Music.app or local library)
        let _ = tx.send(LibrarySyncProgress::ServiceStarted(StreamingService::AppleMusic, "Scanning Music.app library...".to_string()));
        let mut apple_total = 0;
        if let Ok(apple_cols) = Self::scan_apple_music("") {
            apple_total = apple_cols.len();
            for col in apple_cols {
                let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
            }
        }
        let _ = tx.send(LibrarySyncProgress::ServiceCompleted(StreamingService::AppleMusic, apple_total));

        let cfg = LinkedAccountsConfig::load();
        let yt_browser = if !cfg.youtube_browser.is_empty() {
            cfg.youtube_browser.clone()
        } else if Self::detect_zen_browser_profiles().is_some() {
            "zen".to_string()
        } else {
            "chrome".to_string()
        };

        // 2. YouTube Music (Using configured or auto-detected browser session and handle discovery)
        let _ = tx.send(LibrarySyncProgress::ServiceStarted(StreamingService::YouTubeMusic, format!("Syncing YouTube Music playlists ({})...", yt_browser)));
        let yt_sources = Self::scan_youtube_music_feed(&yt_browser, Some(&cfg.youtube_profile));
        let yt_total = yt_sources.len();
        for (idx, col) in yt_sources.into_iter().enumerate() {
            let _ = tx.send(LibrarySyncProgress::ServiceProgress(StreamingService::YouTubeMusic, idx + 1, yt_total, col.title.clone()));
            let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
        }
        let _ = tx.send(LibrarySyncProgress::ServiceCompleted(StreamingService::YouTubeMusic, yt_total));

        // 3. Spotify: Saved Sources & Zen Browser / Desktop Detection
        let _ = tx.send(LibrarySyncProgress::ServiceStarted(StreamingService::Spotify, "Scanning configured Spotify playlists & sessions...".to_string()));
        let mut sp_total = 0;
        let mut seen_spotify_urls = HashSet::new();

        // 3a. First, scan all user-saved Spotify sources (playlists and albums)
        for src in &cfg.spotify_sources {
            let trimmed = src.trim();
            if !trimmed.is_empty() && !seen_spotify_urls.contains(trimmed) {
                seen_spotify_urls.insert(trimmed.to_string());
                if let Ok(spotify_cols) = Self::scan_spotify(trimmed) {
                    for col in spotify_cols {
                        sp_total += 1;
                        let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
                    }
                }
            }
        }
        if !cfg.spotify_profile.trim().is_empty() && !seen_spotify_urls.contains(cfg.spotify_profile.trim()) {
            let trimmed = cfg.spotify_profile.trim();
            seen_spotify_urls.insert(trimmed.to_string());
            if let Ok(spotify_cols) = Self::scan_spotify(trimmed) {
                for col in spotify_cols {
                    sp_total += 1;
                    let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
                }
            }
        }

        // 3b. If no saved sources exist, fall back to desktop/zen detection
        if sp_total == 0 {
            let mut spotify_user = Self::detect_zen_spotify_username();
            if spotify_user.is_none() {
                spotify_user = Self::detect_spotify_desktop_user();
            }
            if let Some(u) = spotify_user {
                let target = format!("https://open.spotify.com/user/{}", u);
                if let Ok(spotify_cols) = Self::scan_spotify(&target) {
                    for col in spotify_cols {
                        sp_total += 1;
                        let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
                    }
                }
            } else if Self::detect_zen_spotify_cookie().is_some() {
                let target = "https://open.spotify.com/collection/tracks".to_string();
                if let Ok(spotify_cols) = Self::scan_spotify(&target) {
                    for col in spotify_cols {
                        sp_total += 1;
                        let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
                    }
                }
            }
        }
        let _ = tx.send(LibrarySyncProgress::ServiceCompleted(StreamingService::Spotify, sp_total));

        let _ = tx.send(LibrarySyncProgress::Done("Auto-detection complete. All streaming libraries synced.".to_string()));
    }

    /// Discovers all user music playlists from YouTube while filtering out video/tutorial playlists.
    /// Also queries the user's public handle or channel playlists if provided.
    pub fn scan_youtube_music_feed(browser: &str, user_profile: Option<&str>) -> Vec<DiscoveredCollection> {
        let mut collections = Vec::new();

        // 1. Always include Liked Music (LM)
        collections.push(DiscoveredCollection {
            id: "zen_yt_liked".to_string(),
            title: "YT Music: Liked Music".to_string(),
            service: StreamingService::YouTubeMusic,
            track_count: 50,
            url: "https://music.youtube.com/playlist?list=LM".to_string(),
            is_selected: true,
        });

        // 2. Discover user channel / handle playlists if specified
        if let Some(profile) = user_profile {
            let trimmed = profile.trim();
            if !trimmed.is_empty() {
                let target_url = if trimmed.contains("list=") {
                    trimmed.to_string()
                } else if trimmed.starts_with('@') {
                    format!("https://www.youtube.com/{}/playlists", trimmed)
                } else if trimmed.contains("/@") {
                    let handle = trimmed.split("/@").nth(1).unwrap_or("").split('/').next().unwrap_or("");
                    format!("https://www.youtube.com/@{}/playlists", handle)
                } else if trimmed.contains("/channel/") {
                    let id = trimmed.split("/channel/").nth(1).unwrap_or("").split('/').next().unwrap_or("");
                    format!("https://www.youtube.com/channel/{}/playlists", id)
                } else {
                    trimmed.to_string()
                };

                let mut cmd = Command::new("yt-dlp");
                cmd.args(["--flat-playlist", "-J", "--no-warnings"]);
                if browser == "zen" {
                    if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
                        cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
                    }
                } else if !browser.is_empty() && browser != "none" {
                    cmd.args(["--cookies-from-browser", browser]);
                }
                cmd.arg(&target_url);

                if let Ok(output) = cmd.output() {
                    if output.status.success() {
                        if let Ok(json) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                            if let Some(entries) = json.get("entries").and_then(|e| e.as_array()) {
                                for (idx, entry) in entries.iter().enumerate() {
                                    let title = entry.get("title").and_then(|t| t.as_str()).unwrap_or("").trim().to_string();
                                    let url = entry.get("url").and_then(|u| u.as_str()).unwrap_or("").trim().to_string();
                                    let id = entry.get("id").and_then(|i| i.as_str()).unwrap_or("").trim().to_string();
                                    if !title.is_empty() && !url.is_empty() && !collections.iter().any(|c| c.url == url) {
                                        let count = entry.get("playlist_count").or_else(|| entry.get("n_entries")).and_then(|c| c.as_u64()).unwrap_or(25) as usize;
                                        collections.push(DiscoveredCollection {
                                            id: if !id.is_empty() { format!("yt_user_{}", id) } else { format!("yt_user_{}", idx) },
                                            title: format!("YT: {}", title),
                                            service: StreamingService::YouTubeMusic,
                                            track_count: count,
                                            url,
                                            is_selected: true,
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 3. Query user feed/playlists with cookies to extract custom music playlists
        let mut cmd = Command::new("yt-dlp");
        cmd.args([
            "--flat-playlist",
            "-J",
            "--no-warnings",
        ]);
        if browser == "zen" {
            if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
                cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
            }
        } else if !browser.is_empty() && browser != "none" {
            cmd.args(["--cookies-from-browser", browser]);
        } else if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
            cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
        }
        cmd.arg("https://www.youtube.com/feed/playlists");

        if let Ok(output) = cmd.output() {
            if output.status.success() {
                if let Ok(json) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                    if let Some(entries) = json.get("entries").and_then(|e| e.as_array()) {
                        for (idx, entry) in entries.iter().enumerate() {
                            let title = entry.get("title").and_then(|t| t.as_str()).unwrap_or("").trim().to_string();
                            let url = entry.get("url").and_then(|u| u.as_str()).unwrap_or("").trim().to_string();
                            let id = entry.get("id").and_then(|i| i.as_str()).unwrap_or("").trim().to_string();

                            if title.is_empty() || url.is_empty() || id == "LL" || id == "WL" || id == "LM" {
                                continue; // Skip generic Liked Videos, Watch Later, or duplicate LM
                            }

                            // Filter out non-music video playlists
                            let lower = title.to_lowercase();
                            if lower.contains("tutorial")
                                || lower.contains("bootcamp")
                                || lower.contains("computer")
                                || lower.contains("coding")
                                || lower.contains("python")
                                || lower.contains("pandas")
                                || lower.contains("course")
                                || lower.contains("lecture")
                                || lower.contains("gameplay")
                                || lower.contains("watch later")
                                || lower.contains("recitation")
                                || lower.contains("learn")
                            {
                                continue; // Non-music playlist!
                            }

                            if id.starts_with("RD") || title.starts_with("Mix -") {
                                continue; // Skip algorithmic dynamic mixes
                            }

                            // Keep standard www.youtube.com URL for optimal yt-dlp compatibility
                            let valid_url = if url.contains("music.music.youtube.com") {
                                url.replace("music.music.youtube.com", "www.youtube.com")
                            } else if url.contains("music.youtube.com") {
                                url.replace("music.youtube.com", "www.youtube.com")
                            } else {
                                url
                            };

                            let count = entry.get("playlist_count")
                                .or_else(|| entry.get("n_entries"))
                                .and_then(|c| c.as_u64())
                                .unwrap_or(25) as usize;

                            if !collections.iter().any(|c| c.url == valid_url) {
                                collections.push(DiscoveredCollection {
                                    id: if !id.is_empty() { format!("yt_pl_{}", id) } else { format!("yt_pl_{}", idx) },
                                    title: format!("YT Music: {}", title),
                                    service: StreamingService::YouTubeMusic,
                                    track_count: count,
                                    url: valid_url,
                                    is_selected: true,
                                });
                            }
                        }
                    }
                }
            }
        }

        collections
    }

    /// Detects logged-in Spotify username from local desktop configuration.
    pub fn detect_spotify_desktop_user() -> Option<String> {
        let prefs_path = if let Ok(home) = std::env::var("HOME") {
            PathBuf::from(home).join("Library").join("Application Support").join("Spotify").join("prefs")
        } else if let Ok(appdata) = std::env::var("APPDATA") {
            PathBuf::from(appdata).join("Spotify").join("prefs")
        } else {
            return None;
        };

        if prefs_path.exists() {
            if let Ok(content) = fs::read_to_string(prefs_path) {
                for line in content.lines() {
                    if line.starts_with("autologin.username=") {
                        let user = line.trim_start_matches("autologin.username=").trim_matches('\"').trim();
                        if !user.is_empty() {
                            return Some(user.to_string());
                        }
                    }
                }
            }
        }
        None
    }

    /// Filters out non-music video podcasts, commentary, gameplay, and shorts from YouTube playlists.
    pub fn sanitize_youtube_music_entry(dur: Option<u64>, title: &str, _channel: &str) -> bool {
        // If duration is known, filter out shorts (< 30s) or long podcasts/streams (> 20m / 1200s).
        // If duration is omitted (common in flat playlist JSON), preserve the track.
        if let Some(d) = dur {
            if (1..30).contains(&d) || d > 1200 {
                return false;
            }
        }
        let lower = title.to_lowercase();
        if lower.contains("podcast")
            || lower.contains("gameplay")
            || lower.contains("review")
            || lower.contains("full episode")
            || lower.contains("trailer")
            || lower.contains("reaction")
            || lower.contains("walkthrough")
            || lower.contains("unboxing")
            || lower.contains("audiobook")
        {
            return false;
        }
        true
    }

    /// Scans an Apple Music profile or playlist URL, or probes local Apple Music / iTunes library.
    pub fn scan_apple_music(profile_or_url: &str) -> Result<Vec<DiscoveredCollection>, String> {
        let trimmed = profile_or_url.trim();
        let mut collections = Vec::new();

        if !trimmed.is_empty() {
            // User provided Apple Music profile or playlist URL
            if trimmed.contains("music.apple.com") || trimmed.contains("itunes.apple.com") {
                collections.push(DiscoveredCollection {
                    id: format!("apple_{}", collections.len() + 1),
                    title: if trimmed.contains("/profile/") { "Apple Music Profile Library".to_string() } else { "Apple Music Shared Collection".to_string() },
                    service: StreamingService::AppleMusic,
                    track_count: 50,
                    url: trimmed.to_string(),
                    is_selected: true,
                });
                return Ok(collections);
            }
        }

        // Cross-Platform Local Discovery:
        // 1. macOS: Query Music.app via AppleScript
        #[cfg(target_os = "macos")]
        {
            if let Ok(output) = Command::new("osascript")
                .args(["-e", "tell application \"Music\" to get name of playlists"])
                .output()
            {
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout);
                    for (i, name) in text.split(',').enumerate() {
                        let name = name.trim();
                        if !name.is_empty() && name != "Music" && name != "Downloaded" {
                            // Query actual track count
                            let count_script = format!("tell application \"Music\" to get count of tracks of playlist \"{}\"", name.replace('\"', "\\\""));
                            let count = Command::new("osascript")
                                .args(["-e", &count_script])
                                .output()
                                .ok()
                                .and_then(|o| String::from_utf8_lossy(&o.stdout).trim().parse::<usize>().ok())
                                .unwrap_or(25);

                            collections.push(DiscoveredCollection {
                                id: format!("apple_local_{}", i),
                                title: format!("Music.app: {}", name),
                                service: StreamingService::AppleMusic,
                                track_count: count,
                                url: format!("local://music.app/{}", name),
                                is_selected: true,
                            });
                        }
                    }
                }
            }
        }

        // 2. Windows: Check iTunes Music Library XML in standard user folders
        #[cfg(target_os = "windows")]
        {
            if let Ok(profile) = std::env::var("USERPROFILE") {
                let xml_path = PathBuf::from(profile).join("Music").join("iTunes").join("iTunes Music Library.xml");
                if xml_path.exists() {
                    collections.push(DiscoveredCollection {
                        id: "apple_win_itunes".to_string(),
                        title: "Windows iTunes Library XML".to_string(),
                        service: StreamingService::AppleMusic,
                        track_count: 100,
                        url: xml_path.to_string_lossy().to_string(),
                        is_selected: true,
                    });
                }
            }
        }

        if collections.is_empty() {
            collections.push(DiscoveredCollection {
                id: "apple_default".to_string(),
                title: "Apple Music User Library".to_string(),
                service: StreamingService::AppleMusic,
                track_count: 25,
                url: if trimmed.is_empty() { "https://music.apple.com".to_string() } else { trimmed.to_string() },
                is_selected: true,
            });
        }

        Ok(collections)
    }

    /// Scans a Spotify user profile or playlist URL.
    pub fn scan_spotify(profile_or_url: &str) -> Result<Vec<DiscoveredCollection>, String> {
        let trimmed = profile_or_url.trim();
        let mut collections = Vec::new();

        if !trimmed.is_empty() {
            let title = if trimmed.contains("/user/") {
                "Spotify User Profile Playlists".to_string()
            } else if trimmed.contains("/playlist/") {
                "Spotify Target Playlist".to_string()
            } else if trimmed.contains("/album/") {
                "Spotify Target Album".to_string()
            } else {
                format!("Spotify Collection: {}", trimmed)
            };

            let slug: String = trimmed.chars().filter(|c| c.is_alphanumeric()).take(24).collect();
            let id = format!("spotify_{}", if slug.is_empty() { "default".to_string() } else { slug });

            collections.push(DiscoveredCollection {
                id,
                title,
                service: StreamingService::Spotify,
                track_count: 50,
                url: trimmed.to_string(),
                is_selected: true,
            });
        } else {
            collections.push(DiscoveredCollection {
                id: "spotify_liked".to_string(),
                title: "Spotify Liked Songs & Saved Tracks".to_string(),
                service: StreamingService::Spotify,
                track_count: 35,
                url: "https://open.spotify.com/collection/tracks".to_string(),
                is_selected: true,
            });
        }

        Ok(collections)
    }

    /// Scans YouTube Music using browser session cookies or channel link.
    pub fn scan_youtube_music(browser: &str, channel_or_url: &str) -> Result<Vec<DiscoveredCollection>, String> {
        let mut collections = Vec::new();

        // 1. Fetch real playlists from YouTube Music feed and user profile
        let feed_cols = Self::scan_youtube_music_feed(browser, Some(channel_or_url));
        if !feed_cols.is_empty() {
            collections.extend(feed_cols);
        } else {
            collections.push(DiscoveredCollection {
                id: "yt_liked".to_string(),
                title: format!("YouTube Music: Liked Music (LM) [{}]", browser.to_uppercase()),
                service: StreamingService::YouTubeMusic,
                track_count: 50,
                url: "https://music.youtube.com/playlist?list=LM".to_string(),
                is_selected: true,
            });
        }

        // 2. Channel or custom playlist if specified and not already in collections
        let trimmed = channel_or_url.trim();
        if !trimmed.is_empty() && !collections.iter().any(|c| c.url == trimmed) {
            let slug: String = trimmed.chars().filter(|c| c.is_alphanumeric()).take(24).collect();
            let id = format!("yt_custom_{}", if slug.is_empty() { "default".to_string() } else { slug });
            collections.push(DiscoveredCollection {
                id,
                title: if trimmed.contains("list=") { "YouTube Custom Playlist".to_string() } else { "YouTube Channel / Playlists".to_string() },
                service: StreamingService::YouTubeMusic,
                track_count: 50,
                url: trimmed.to_string(),
                is_selected: true,
            });
        }

        Ok(collections)
    }

    /// Ingests tracks from a collection URL or local library into parsed tracks.
    pub fn fetch_tracks_for_collection(collection: &DiscoveredCollection, browser: &str) -> Result<Vec<ParsedTrack>, String> {
        // 1. Local Apple Music (macOS Music.app IPC)
        #[cfg(target_os = "macos")]
        if collection.url.starts_with("local://music.app/") {
            let playlist_name = collection.url.trim_start_matches("local://music.app/");
            let script = format!(
                    "tell application \"Music\"\nset out to \"\"\nrepeat with t in tracks of playlist \"{}\"\nset art to \"\"\ntry\nset art to (artist of t)\nend try\nif art is \"\" or art is \"missing value\" or art is \"msng\" then\ntry\nset art to (album artist of t)\nend try\nend if\nset nm to \"\"\ntry\nset nm to (name of t)\nend try\nset alb to \"\"\ntry\nset alb to (album of t)\nend try\nset dur to 0\ntry\nset dur to (duration of t as integer)\nend try\nset out to out & nm & \"\\t\" & art & \"\\t\" & alb & \"\\t\" & dur & \"\\n\"\nend repeat\nreturn out\nend tell",
                    playlist_name.replace('\"', "\\\"")
                );
                if let Ok(output) = Command::new("osascript").args(["-e", &script]).output() {
                    if output.status.success() {
                        let text = String::from_utf8_lossy(&output.stdout);
                        let mut tracks = Vec::new();
                        for line in text.lines() {
                            let parts: Vec<&str> = line.split('\t').collect();
                            if !parts.is_empty() && !parts[0].trim().is_empty() {
                                let raw_title = parts[0].trim();
                                let raw_artist = if parts.len() > 1 && !parts[1].trim().is_empty() && parts[1].trim() != "msng" && parts[1].trim() != "missing value" {
                                    parts[1].trim()
                                } else {
                                    ""
                                };
                                let cleaned_meta = clean_title(raw_title);
                                let (artist, title) = if !raw_artist.is_empty() && !raw_artist.eq_ignore_ascii_case("various artists") {
                                    (raw_artist.to_string(), cleaned_meta.title)
                                } else if let Some(ref a) = cleaned_meta.artist {
                                    (a.clone(), cleaned_meta.title)
                                } else if !raw_artist.is_empty() {
                                    (raw_artist.to_string(), cleaned_meta.title)
                                } else {
                                    ("Unknown Artist".to_string(), cleaned_meta.title)
                                };

                                let album = if parts.len() > 2 && !parts[2].trim().is_empty() {
                                    parts[2].trim().to_string()
                                } else {
                                    playlist_name.to_string()
                                };
                                let dur = if parts.len() > 3 {
                                    parts[3].trim().parse::<u64>().ok()
                                } else {
                                    None
                                };
                                tracks.push(ParsedTrack {
                                    artist,
                                    title,
                                    album,
                                    duration_secs: dur,
                                    isrc: None,
                                    track_number: None,
                                    cover_art_url: None,
                                    source_url: None,
                                });
                            }
                        }
                        if !tracks.is_empty() {
                            return Ok(tracks);
                        }
                    }
                }
            }

        // 2. Web URLs (Spotify, Apple Music, YouTube Music)
        if collection.url.starts_with("http://") || collection.url.starts_with("https://") {
            let is_youtube = collection.url.contains("youtube.com") || collection.url.contains("youtu.be");

            if !is_youtube {
                // First attempt PlaylistParser oEmbed / HTML parsing for Spotify / Apple Music
                let parser = PlaylistParser::new();
                let url_clone = collection.url.clone();
                let parsed_res = match tokio::runtime::Builder::new_current_thread().enable_all().build() {
                    Ok(rt) => rt.block_on(async move {
                        parser.parse_url_or_path(&url_clone).await
                    }),
                    Err(e) => Err(format!("Runtime build error: {}", e)),
                };

                if let Ok(pl) = parsed_res {
                    if !pl.tracks.is_empty() {
                        return Ok(pl.tracks);
                    }
                }
            }

            let target_url = if is_youtube {
                collection.url
                    .replace("music.music.youtube.com", "www.youtube.com")
                    .replace("music.youtube.com", "www.youtube.com")
            } else {
                collection.url.clone()
            };

            // Direct yt-dlp flat playlist extraction with cookies (with automatic anonymous fallback)
            let execute_ytdlp = |with_cookies: bool| -> Result<std::process::Output, String> {
                let mut cmd = Command::new("yt-dlp");
                cmd.args([
                    "--flat-playlist",
                    "-J",
                    "--no-warnings",
                ]);

                if with_cookies {
                    if browser == "zen" {
                        if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
                            cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
                        }
                    } else if !browser.is_empty() && browser != "none" {
                        cmd.args(["--cookies-from-browser", browser]);
                    } else if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
                        cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
                    }
                }
                cmd.arg(&target_url);
                cmd.output().map_err(|e| e.to_string())
            };

            // 1. First attempt extraction with cookies if configured
            let mut output = execute_ytdlp(true);
            // 2. If cookie extraction failed or exited with error (e.g. browser cookie database locked), retry anonymously
            if output.is_err() || output.as_ref().map(|o| !o.status.success()).unwrap_or(false) {
                if let Ok(anon_out) = execute_ytdlp(false) {
                    if anon_out.status.success() {
                        output = Ok(anon_out);
                    }
                }
            }

            if let Ok(output) = output {
                if output.status.success() {
                    if let Ok(json) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                        if let Some(entries) = json.get("entries").and_then(|e| e.as_array()) {
                            let mut tracks = Vec::new();
                            for entry in entries {
                                let raw_track = entry.get("track").and_then(|t| t.as_str()).map(|s| s.trim()).filter(|s| !s.is_empty());
                                let raw_artist = entry.get("artist")
                                    .or_else(|| entry.get("creator"))
                                    .or_else(|| entry.get("track_artist"))
                                    .or_else(|| entry.get("album_artist"))
                                    .and_then(|a| a.as_str())
                                    .map(|s| s.trim())
                                    .filter(|s| !s.is_empty() && !s.eq_ignore_ascii_case("various artists"));
                                let raw_title = entry.get("title").and_then(|t| t.as_str()).unwrap_or("Unknown").trim();
                                let cleaned_meta = clean_title(raw_title);

                                let (artist, title) = if let Some(a) = raw_artist {
                                    let t = raw_track.map(|s| s.to_string()).unwrap_or_else(|| cleaned_meta.title.clone());
                                    (a.to_string(), t)
                                } else if let Some(ref a) = cleaned_meta.artist {
                                    (a.clone(), cleaned_meta.title)
                                } else {
                                    let up = entry.get("uploader").or_else(|| entry.get("channel"))
                                        .and_then(|u| u.as_str())
                                        .map(|s| s.trim().trim_end_matches(" - Topic").trim())
                                        .filter(|s| !s.is_empty() && !s.eq_ignore_ascii_case("various artists") && !s.eq_ignore_ascii_case("unknown"));
                                    let a = up.unwrap_or("Unknown Artist").to_string();
                                    (a, cleaned_meta.title)
                                };

                                let dur = entry.get("duration").and_then(|d| d.as_u64());

                                // Apply YouTube Music non-music sanitizer
                                if !Self::sanitize_youtube_music_entry(dur, &title, &artist) {
                                    continue;
                                }

                                let vid_id = entry.get("id").and_then(|i| i.as_str());
                                let vid_url = entry.get("url").and_then(|u| u.as_str()).map(|u| {
                                    if u.starts_with("http://") || u.starts_with("https://") {
                                        u.to_string()
                                    } else {
                                        format!("https://www.youtube.com/watch?v={}", u)
                                    }
                                }).or_else(|| {
                                    vid_id.map(|id| format!("https://www.youtube.com/watch?v={}", id))
                                });

                                tracks.push(ParsedTrack {
                                    artist,
                                    title,
                                    album: collection.title.clone(),
                                    duration_secs: dur,
                                    isrc: None,
                                    track_number: None,
                                    cover_art_url: None,
                                    source_url: vid_url,
                                });
                            }
                            if !tracks.is_empty() {
                                return Ok(tracks);
                            }
                        }
                    }
                }
            }
        }

        Ok(Vec::new())
    }

    /// Fetches and formats individual tracks as selectable items for the 2-pane drill-down UI.
    pub fn fetch_track_items_for_collection(collection: &DiscoveredCollection, browser: &str) -> Vec<DiscoveredTrackItem> {
        let mut items = Vec::new();
        if let Ok(tracks) = Self::fetch_tracks_for_collection(collection, browser) {
            for (idx, t) in tracks.into_iter().enumerate() {
                let track_id = t.source_url.clone().unwrap_or_else(|| format!("{}_{}", collection.id, idx));
                items.push(DiscoveredTrackItem {
                    id: track_id,
                    title: t.title,
                    artist: t.artist,
                    album: t.album,
                    duration_secs: t.duration_secs.map(|d| d as u32),
                    is_selected: true,
                    library_name: collection.title.clone(),
                    service: collection.service,
                    added_order: idx as u64,
                });
            }
        }
        items
    }

    /// In-place sorting for discovered track items in modal with customizable platform priority & section sub-sort
    pub fn sort_track_items_custom(
        items: &mut [DiscoveredTrackItem],
        mode: TrackSortMode,
        platform_priority: DividerPlatformPriority,
        sub_sort: DividerSubSort,
    ) {
        match mode {
            TrackSortMode::LatestAdded => {
                items.sort_by_key(|t| std::cmp::Reverse(t.added_order));
            }
            TrackSortMode::OldestAdded => {
                items.sort_by_key(|t| t.added_order);
            }
            TrackSortMode::TitleAZ => {
                items.sort_by(|a, b| a.title.to_lowercase().cmp(&b.title.to_lowercase()));
            }
            TrackSortMode::TitleZA => {
                items.sort_by(|a, b| b.title.to_lowercase().cmp(&a.title.to_lowercase()));
            }
            TrackSortMode::ArtistAZ => {
                items.sort_by(|a, b| {
                    let cmp = a.artist.to_lowercase().cmp(&b.artist.to_lowercase());
                    if cmp != std::cmp::Ordering::Equal {
                        return cmp;
                    }
                    a.title.to_lowercase().cmp(&b.title.to_lowercase())
                });
            }
            TrackSortMode::ArtistZA => {
                items.sort_by(|a, b| {
                    let cmp = b.artist.to_lowercase().cmp(&a.artist.to_lowercase());
                    if cmp != std::cmp::Ordering::Equal {
                        return cmp;
                    }
                    b.title.to_lowercase().cmp(&a.title.to_lowercase())
                });
            }
            TrackSortMode::DurationShortest => {
                items.sort_by_key(|t| t.duration_secs.unwrap_or(u32::MAX));
            }
            TrackSortMode::DurationLongest => {
                items.sort_by_key(|t| std::cmp::Reverse(t.duration_secs.unwrap_or(0)));
            }
            TrackSortMode::PlatformDividers => {
                items.sort_by(|a, b| {
                    let s_cmp = platform_priority.rank(a.service).cmp(&platform_priority.rank(b.service));
                    if s_cmp != std::cmp::Ordering::Equal {
                        return s_cmp;
                    }
                    let lib_cmp = a.library_name.to_lowercase().cmp(&b.library_name.to_lowercase());
                    if lib_cmp != std::cmp::Ordering::Equal {
                        return lib_cmp;
                    }
                    match sub_sort {
                        DividerSubSort::LatestAdded => std::cmp::Reverse(a.added_order).cmp(&std::cmp::Reverse(b.added_order)),
                        DividerSubSort::OldestAdded => a.added_order.cmp(&b.added_order),
                        DividerSubSort::TitleAZ => a.title.to_lowercase().cmp(&b.title.to_lowercase()),
                        DividerSubSort::ArtistAZ => {
                            let cmp = a.artist.to_lowercase().cmp(&b.artist.to_lowercase());
                            if cmp != std::cmp::Ordering::Equal {
                                cmp
                            } else {
                                a.title.to_lowercase().cmp(&b.title.to_lowercase())
                            }
                        }
                        DividerSubSort::DurationShortest => a.duration_secs.unwrap_or(u32::MAX).cmp(&b.duration_secs.unwrap_or(u32::MAX)),
                        DividerSubSort::DurationLongest => std::cmp::Reverse(a.duration_secs.unwrap_or(0)).cmp(&std::cmp::Reverse(b.duration_secs.unwrap_or(0))),
                    }
                });
            }
        }
    }

    pub fn sort_track_items(items: &mut [DiscoveredTrackItem], mode: TrackSortMode) {
        Self::sort_track_items_custom(items, mode, DividerPlatformPriority::default(), DividerSubSort::default());
    }

    /// In-place sorting for streaming queue items with customizable platform priority & section sub-sort
    pub fn sort_queue_items_custom(
        items: &mut [StreamQueueItem],
        mode: TrackSortMode,
        platform_priority: DividerPlatformPriority,
        sub_sort: DividerSubSort,
    ) {
        match mode {
            TrackSortMode::LatestAdded => {
                items.sort_by_key(|t| std::cmp::Reverse(t.added_order));
            }
            TrackSortMode::OldestAdded => {
                items.sort_by_key(|t| t.added_order);
            }
            TrackSortMode::TitleAZ => {
                items.sort_by(|a, b| a.title.to_lowercase().cmp(&b.title.to_lowercase()));
            }
            TrackSortMode::TitleZA => {
                items.sort_by(|a, b| b.title.to_lowercase().cmp(&a.title.to_lowercase()));
            }
            TrackSortMode::ArtistAZ => {
                items.sort_by(|a, b| {
                    let cmp = a.artist.to_lowercase().cmp(&b.artist.to_lowercase());
                    if cmp != std::cmp::Ordering::Equal {
                        return cmp;
                    }
                    a.album.to_lowercase().cmp(&b.album.to_lowercase())
                        .then_with(|| a.title.to_lowercase().cmp(&b.title.to_lowercase()))
                });
            }
            TrackSortMode::ArtistZA => {
                items.sort_by(|a, b| {
                    let cmp = b.artist.to_lowercase().cmp(&a.artist.to_lowercase());
                    if cmp != std::cmp::Ordering::Equal {
                        return cmp;
                    }
                    b.album.to_lowercase().cmp(&a.album.to_lowercase())
                        .then_with(|| b.title.to_lowercase().cmp(&a.title.to_lowercase()))
                });
            }
            TrackSortMode::DurationShortest => {
                items.sort_by_key(|t| t.duration_secs.unwrap_or(u32::MAX));
            }
            TrackSortMode::DurationLongest => {
                items.sort_by_key(|t| std::cmp::Reverse(t.duration_secs.unwrap_or(0)));
            }
            TrackSortMode::PlatformDividers => {
                items.sort_by(|a, b| {
                    let s_cmp = platform_priority.rank(a.service).cmp(&platform_priority.rank(b.service));
                    if s_cmp != std::cmp::Ordering::Equal {
                        return s_cmp;
                    }
                    let lib_cmp = a.library_name.to_lowercase().cmp(&b.library_name.to_lowercase());
                    if lib_cmp != std::cmp::Ordering::Equal {
                        return lib_cmp;
                    }
                    match sub_sort {
                        DividerSubSort::LatestAdded => std::cmp::Reverse(a.added_order).cmp(&std::cmp::Reverse(b.added_order)),
                        DividerSubSort::OldestAdded => a.added_order.cmp(&b.added_order),
                        DividerSubSort::TitleAZ => a.title.to_lowercase().cmp(&b.title.to_lowercase()),
                        DividerSubSort::ArtistAZ => {
                            let cmp = a.artist.to_lowercase().cmp(&b.artist.to_lowercase());
                            if cmp != std::cmp::Ordering::Equal {
                                cmp
                            } else {
                                a.album.to_lowercase().cmp(&b.album.to_lowercase())
                                    .then_with(|| a.title.to_lowercase().cmp(&b.title.to_lowercase()))
                            }
                        }
                        DividerSubSort::DurationShortest => a.duration_secs.unwrap_or(u32::MAX).cmp(&b.duration_secs.unwrap_or(u32::MAX)),
                        DividerSubSort::DurationLongest => std::cmp::Reverse(a.duration_secs.unwrap_or(0)).cmp(&std::cmp::Reverse(b.duration_secs.unwrap_or(0))),
                    }
                });
            }
        }
    }

    /// In-place sorting for streaming queue items
    pub fn sort_queue_items(items: &mut [StreamQueueItem], mode: TrackSortMode) {
        Self::sort_queue_items_custom(items, mode, DividerPlatformPriority::default(), DividerSubSort::default());
    }

    /// Smart Deduplication & Logical Organization Engine:
    /// - Normalizes titles and artists (removes junk tags like "feat.", "(Official Video)", remasters)
    /// - Eliminates duplicates across platforms
    /// - Sorts logically by selected TrackSortMode
    pub fn deduplicate_and_organize_tracks(
        tracks: Vec<StreamQueueItem>,
        deduplicate: bool,
        sort_mode: TrackSortMode,
    ) -> Vec<StreamQueueItem> {
        let mut seen = HashSet::new();
        let mut clean_list: Vec<StreamQueueItem> = Vec::new();

        for mut item in tracks {
            if deduplicate {
                let norm_artist = clean_title(&item.artist).title.to_lowercase();
                let norm_title = clean_title(&item.title).title.to_lowercase();
                let key = format!("{}::{}", norm_artist, norm_title);

                if seen.contains(&key) {
                    continue; // Skip duplicate song
                }
                seen.insert(key);
            }

            // Clean up titles for intuitive presentation
            let cleaned = clean_title(&item.title).title;
            if !cleaned.is_empty() {
                item.title = cleaned;
            }

            clean_list.push(item);
        }

        Self::sort_queue_items(&mut clean_list, sort_mode);

        clean_list
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::harvest::stream_resolver::AudioQualityTier;
    use crate::ui::streaming_hub::StreamItemStatus;

    #[test]
    fn test_linked_accounts_config_defaults() {
        let cfg = LinkedAccountsConfig::default();
        assert!(cfg.deduplicate);
        assert_eq!(cfg.sort_mode, TrackSortMode::ArtistAZ);
        assert_eq!(cfg.youtube_browser, "chrome");
    }

    #[test]
    fn test_deduplicate_and_organize_tracks() {
        let items = vec![
            StreamQueueItem {
                title: "One More Time (Official Video)".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Discovery".to_string(),
                duration_secs: Some(320),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::YouTubeMusic,
                source_query: "query1".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "YT Favorites".to_string(),
                added_order: 10,
            },
            StreamQueueItem {
                title: "One More Time".to_string(),
                artist: "Daft Punk".to_string(),
                album: "Discovery".to_string(),
                duration_secs: Some(320),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::Spotify,
                source_query: "query2".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Spotify Discovery".to_string(),
                added_order: 20,
            },
            StreamQueueItem {
                title: "Blinding Lights".to_string(),
                artist: "The Weeknd".to_string(),
                album: "After Hours".to_string(),
                duration_secs: Some(200),
                quality_tier: AudioQualityTier::CloudOpus160,
                service: StreamingService::AppleMusic,
                source_query: "query3".to_string(),
                status: StreamItemStatus::Queued,
                audio_file_path: None,
                library_name: "Apple Top Hits".to_string(),
                added_order: 30,
            },
        ];

        let result = LibrarySyncEngine::deduplicate_and_organize_tracks(items, true, TrackSortMode::ArtistAZ);
        // Duplicate Daft Punk track should be merged away!
        assert_eq!(result.len(), 2);
        // Sorted alphabetically: Daft Punk first, then The Weeknd
        assert_eq!(result[0].artist, "Daft Punk");
        assert_eq!(result[1].artist, "The Weeknd");
    }

    #[test]
    fn test_track_sort_mode_ordering() {
        let mut items = vec![
            DiscoveredTrackItem {
                id: "1".to_string(),
                title: "Zebra".to_string(),
                artist: "Bob".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(300),
                is_selected: true,
                library_name: "YT Mix".to_string(),
                service: StreamingService::YouTubeMusic,
                added_order: 10,
            },
            DiscoveredTrackItem {
                id: "2".to_string(),
                title: "Apple".to_string(),
                artist: "Charlie".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(120),
                is_selected: true,
                library_name: "Apple Classics".to_string(),
                service: StreamingService::AppleMusic,
                added_order: 30,
            },
            DiscoveredTrackItem {
                id: "3".to_string(),
                title: "Monkey".to_string(),
                artist: "Alice".to_string(),
                album: "Album".to_string(),
                duration_secs: Some(240),
                is_selected: true,
                library_name: "Spotify Rock".to_string(),
                service: StreamingService::Spotify,
                added_order: 20,
            },
        ];

        // 1. Title A-Z
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::TitleAZ);
        assert_eq!(items[0].title, "Apple");
        assert_eq!(items[1].title, "Monkey");
        assert_eq!(items[2].title, "Zebra");

        // 2. Title Z-A
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::TitleZA);
        assert_eq!(items[0].title, "Zebra");
        assert_eq!(items[1].title, "Monkey");
        assert_eq!(items[2].title, "Apple");

        // 3. Artist A-Z
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::ArtistAZ);
        assert_eq!(items[0].artist, "Alice");
        assert_eq!(items[1].artist, "Bob");
        assert_eq!(items[2].artist, "Charlie");

        // 4. Artist Z-A
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::ArtistZA);
        assert_eq!(items[0].artist, "Charlie");
        assert_eq!(items[1].artist, "Bob");
        assert_eq!(items[2].artist, "Alice");

        // 5. Duration Shortest
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::DurationShortest);
        assert_eq!(items[0].duration_secs, Some(120));
        assert_eq!(items[1].duration_secs, Some(240));
        assert_eq!(items[2].duration_secs, Some(300));

        // 6. Duration Longest
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::DurationLongest);
        assert_eq!(items[0].duration_secs, Some(300));
        assert_eq!(items[1].duration_secs, Some(240));
        assert_eq!(items[2].duration_secs, Some(120));

        // 7. Latest Added (highest added_order first)
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::LatestAdded);
        assert_eq!(items[0].added_order, 30); // Apple (30)
        assert_eq!(items[1].added_order, 20); // Monkey (20)
        assert_eq!(items[2].added_order, 10); // Zebra (10)

        // 8. Oldest Added (lowest added_order first)
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::OldestAdded);
        assert_eq!(items[0].added_order, 10); // Zebra (10)
        assert_eq!(items[1].added_order, 20); // Monkey (20)
        assert_eq!(items[2].added_order, 30); // Apple (30)

        // 9. Platform Dividers (Spotify first, Apple Music second, YouTube Music third)
        LibrarySyncEngine::sort_track_items(&mut items, TrackSortMode::PlatformDividers);
        assert_eq!(items[0].service, StreamingService::Spotify);
        assert_eq!(items[1].service, StreamingService::AppleMusic);
        assert_eq!(items[2].service, StreamingService::YouTubeMusic);
    }

    #[test]
    fn test_browser_detection_returns_available_browsers() {
        let browsers = LibrarySyncEngine::detect_installed_browsers();
        assert!(!browsers.is_empty());
    }

    #[test]
    fn test_sanitize_youtube_music_entry() {
        // Valid track with duration
        assert!(LibrarySyncEngine::sanitize_youtube_music_entry(Some(180), "Song Name", "Artist - Topic"));

        // Valid track with omitted duration (flat playlist entry)
        assert!(LibrarySyncEngine::sanitize_youtube_music_entry(None, "Song Name", "Artist - Topic"));

        // Too short (< 30s, e.g. meme / short)
        assert!(!LibrarySyncEngine::sanitize_youtube_music_entry(Some(20), "Short Intro", "Artist - Topic"));

        // Too long (> 1200s / 20m, e.g. podcast / video essay)
        assert!(!LibrarySyncEngine::sanitize_youtube_music_entry(Some(3600), "Full Live Show", "Artist"));

        // Non-music keywords
        assert!(!LibrarySyncEngine::sanitize_youtube_music_entry(Some(300), "Joe Rogan Podcast #1999", "JRE"));
        assert!(!LibrarySyncEngine::sanitize_youtube_music_entry(Some(240), "Elden Ring Gameplay Part 4", "GamerChannel"));
        assert!(!LibrarySyncEngine::sanitize_youtube_music_entry(Some(200), "Album Review", "MusicCritic"));
    }

    #[test]
    fn test_zen_browser_detection_and_auto_detect() {
        let _sources = LibrarySyncEngine::auto_detect_all_sources();
        #[cfg(target_os = "macos")]
        {
            assert!(!_sources.is_empty(), "Should auto-detect local macOS sources (Music.app and/or Zen)");
        }
    }

    #[test]
    fn test_artist_extraction_prefers_real_artist_over_various_artists_uploader() {
        // Case 1: yt-dlp entry with explicit artist and compilation uploader "Various Artists - Topic"
        let entry: serde_json::Value = serde_json::json!({
            "title": "ALL RED",
            "artist": "Playboi Carti",
            "track": "ALL RED",
            "uploader": "Various Artists - Topic",
            "channel": "Various Artists"
        });

        let raw_track = entry.get("track").and_then(|t| t.as_str()).map(|s| s.trim()).filter(|s| !s.is_empty());
        let raw_artist = entry.get("artist")
            .or_else(|| entry.get("creator"))
            .or_else(|| entry.get("track_artist"))
            .or_else(|| entry.get("album_artist"))
            .and_then(|a| a.as_str())
            .map(|s| s.trim())
            .filter(|s| !s.is_empty() && !s.eq_ignore_ascii_case("various artists"));
        let raw_title = entry.get("title").and_then(|t| t.as_str()).unwrap_or("Unknown").trim();
        let cleaned_meta = clean_title(raw_title);

        let (artist, title) = if let Some(a) = raw_artist {
            let t = raw_track.map(|s| s.to_string()).unwrap_or_else(|| cleaned_meta.title.clone());
            (a.to_string(), t)
        } else if let Some(ref a) = cleaned_meta.artist {
            (a.clone(), cleaned_meta.title)
        } else {
            let up = entry.get("uploader").or_else(|| entry.get("channel"))
                .and_then(|u| u.as_str())
                .map(|s| s.trim().trim_end_matches(" - Topic").trim())
                .filter(|s| !s.is_empty() && !s.eq_ignore_ascii_case("various artists") && !s.eq_ignore_ascii_case("unknown"));
            let a = up.unwrap_or("Unknown Artist").to_string();
            (a, cleaned_meta.title)
        };

        assert_eq!(artist, "Playboi Carti");
        assert_eq!(title, "ALL RED");

        // Case 2: raw title contains "Artist - Title" with "Various Artists" as uploader
        let entry_fallback: serde_json::Value = serde_json::json!({
            "title": "Playboi Carti - ALL RED (Official Video)",
            "uploader": "Various Artists - Topic"
        });

        let raw_title2 = entry_fallback.get("title").and_then(|t| t.as_str()).unwrap_or("Unknown").trim();
        let cleaned_meta2 = clean_title(raw_title2);

        assert_eq!(cleaned_meta2.artist.as_deref(), Some("Playboi Carti"));
        assert_eq!(cleaned_meta2.title, "ALL RED");
    }
}
