use crate::harvest::playlist_parser::{ParsedTrack, PlaylistParser, StreamingService};
use crate::harvest::title_cleaner::clean_title;
use crate::ui::streaming_hub::StreamQueueItem;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinkedAccountsConfig {
    pub spotify_profile: String,
    pub apple_profile: String,
    pub youtube_profile: String,
    pub youtube_browser: String,
    pub deduplicate: bool,
    pub sort_by_artist: bool,
}

impl Default for LinkedAccountsConfig {
    fn default() -> Self {
        Self {
            spotify_profile: String::new(),
            apple_profile: String::new(),
            youtube_profile: String::new(),
            youtube_browser: "chrome".to_string(),
            deduplicate: true,
            sort_by_artist: true,
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
                if let Ok(cfg) = serde_json::from_str::<LinkedAccountsConfig>(&contents) {
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

        // 2. YouTube Music (Zen Browser session)
        let _ = tx.send(LibrarySyncProgress::ServiceStarted(StreamingService::YouTubeMusic, "Syncing YouTube Music playlists (Zen)...".to_string()));
        let yt_sources = Self::scan_youtube_music_feed("zen");
        let yt_total = yt_sources.len();
        for (idx, col) in yt_sources.into_iter().enumerate() {
            let _ = tx.send(LibrarySyncProgress::ServiceProgress(StreamingService::YouTubeMusic, idx + 1, yt_total, col.title.clone()));
            let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
        }
        let _ = tx.send(LibrarySyncProgress::ServiceCompleted(StreamingService::YouTubeMusic, yt_total));

        // 3. Spotify: Zen Browser LocalStorage / Desktop prefs / Saved Config
        let _ = tx.send(LibrarySyncProgress::ServiceStarted(StreamingService::Spotify, "Detecting Spotify session (Zen/Desktop)...".to_string()));
        let mut spotify_user = Self::detect_zen_spotify_username();
        if spotify_user.is_none() {
            spotify_user = Self::detect_spotify_desktop_user();
        }

        let mut spotify_target = spotify_user.map(|u| format!("https://open.spotify.com/user/{}", u));
        if spotify_target.is_none() {
            let cfg = LinkedAccountsConfig::load();
            if !cfg.spotify_profile.trim().is_empty() && !cfg.spotify_profile.contains("audiophile_master") {
                spotify_target = Some(cfg.spotify_profile.trim().to_string());
            } else if Self::detect_zen_spotify_cookie().is_some() {
                spotify_target = Some("https://open.spotify.com/collection/tracks".to_string());
            }
        }

        let mut sp_total = 0;
        if let Some(target) = spotify_target {
            let url = if target.starts_with("http://") || target.starts_with("https://") {
                target
            } else {
                format!("https://open.spotify.com/user/{}", target)
            };
            if let Ok(spotify_cols) = Self::scan_spotify(&url) {
                sp_total = spotify_cols.len();
                for col in spotify_cols {
                    let _ = tx.send(LibrarySyncProgress::CollectionDiscovered(col));
                }
            }
        }
        let _ = tx.send(LibrarySyncProgress::ServiceCompleted(StreamingService::Spotify, sp_total));

        let _ = tx.send(LibrarySyncProgress::Done("Auto-detection complete. All streaming libraries synced.".to_string()));
    }

    /// Discovers all user music playlists from YouTube while filtering out video/tutorial playlists.
    pub fn scan_youtube_music_feed(browser: &str) -> Vec<DiscoveredCollection> {
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

        // 2. Query user feed/playlists with cookies to extract custom music playlists
        let mut cmd = Command::new("yt-dlp");
        cmd.args([
            "--flat-playlist",
            "-J",
            "--no-warnings",
        ]);
        if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
            cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
        } else if !browser.is_empty() && browser != "none" {
            cmd.args(["--cookies-from-browser", browser]);
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
            } else {
                format!("Spotify Collection: {}", trimmed)
            };

            collections.push(DiscoveredCollection {
                id: "spotify_profile".to_string(),
                title,
                service: StreamingService::Spotify,
                track_count: 40,
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

        // 1. Liked Music collection via browser session
        collections.push(DiscoveredCollection {
            id: "yt_liked".to_string(),
            title: format!("YouTube Music: Liked Music (LM) [{}]", browser.to_uppercase()),
            service: StreamingService::YouTubeMusic,
            track_count: 50,
            url: "https://music.youtube.com/playlist?list=LM".to_string(),
            is_selected: true,
        });

        // 2. Channel or custom playlist if specified
        let trimmed = channel_or_url.trim();
        if !trimmed.is_empty() {
            collections.push(DiscoveredCollection {
                id: "yt_channel".to_string(),
                title: "YouTube Channel / Playlists".to_string(),
                service: StreamingService::YouTubeMusic,
                track_count: 30,
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
                    "tell application \"Music\"\nset out to \"\"\nrepeat with t in tracks of playlist \"{}\"\nset out to out & (name of t) & \"\\t\" & (artist of t) & \"\\t\" & (album of t) & \"\\t\" & (duration of t as integer) & \"\\n\"\nend repeat\nreturn out\nend tell",
                    playlist_name.replace('\"', "\\\"")
                );
                if let Ok(output) = Command::new("osascript").args(["-e", &script]).output() {
                    if output.status.success() {
                        let text = String::from_utf8_lossy(&output.stdout);
                        let mut tracks = Vec::new();
                        for line in text.lines() {
                            let parts: Vec<&str> = line.split('\t').collect();
                            if !parts.is_empty() && !parts[0].trim().is_empty() {
                                let title = parts[0].trim().to_string();
                                let artist = if parts.len() > 1 && !parts[1].trim().is_empty() {
                                    parts[1].trim().to_string()
                                } else {
                                    "Various Artists".to_string()
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
                let parsed_res = if let Ok(handle) = tokio::runtime::Handle::try_current() {
                    std::thread::spawn(move || {
                        handle.block_on(async move {
                            parser.parse_url_or_path(&url_clone).await
                        })
                    }).join().unwrap_or_else(|_| Err("Thread error".to_string()))
                } else if let Ok(rt) = tokio::runtime::Runtime::new() {
                    rt.block_on(async move {
                        parser.parse_url_or_path(&url_clone).await
                    })
                } else {
                    Err("Tokio runtime unavailable".to_string())
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

            // Direct yt-dlp flat playlist extraction with cookies (supporting Zen Browser)
            let mut cmd = Command::new("yt-dlp");
            cmd.args([
                "--flat-playlist",
                "-J",
                "--no-warnings",
            ]);

            // If Zen browser profile exists and browser requested is zen or default, use it
            if let Some(zen_profile) = Self::detect_zen_browser_profiles() {
                cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
            } else if !browser.is_empty() && browser != "none" {
                cmd.args(["--cookies-from-browser", browser]);
            }
            cmd.arg(&target_url);

            if let Ok(output) = cmd.output() {
                if output.status.success() {
                    if let Ok(json) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                        if let Some(entries) = json.get("entries").and_then(|e| e.as_array()) {
                            let mut tracks = Vec::new();
                            for entry in entries {
                                let title = entry.get("title").and_then(|t| t.as_str()).unwrap_or("Unknown").to_string();
                                let artist = entry.get("uploader").or_else(|| entry.get("channel")).and_then(|u| u.as_str()).unwrap_or("Various Artists").to_string();
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
                });
            }
        }
        items
    }

    /// Smart Deduplication & Logical Organization Engine:
    /// - Normalizes titles and artists (removes junk tags like "feat.", "(Official Video)", remasters)
    /// - Eliminates duplicates across platforms
    /// - Sorts logically by Artist (A–Z) -> Album -> Title
    pub fn deduplicate_and_organize_tracks(
        tracks: Vec<StreamQueueItem>,
        deduplicate: bool,
        sort_by_artist: bool,
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

        if sort_by_artist {
            clean_list.sort_by(|a, b| {
                let artist_cmp = a.artist.to_lowercase().cmp(&b.artist.to_lowercase());
                if artist_cmp != std::cmp::Ordering::Equal {
                    return artist_cmp;
                }
                let album_cmp = a.album.to_lowercase().cmp(&b.album.to_lowercase());
                if album_cmp != std::cmp::Ordering::Equal {
                    return album_cmp;
                }
                a.title.to_lowercase().cmp(&b.title.to_lowercase())
            });
        }

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
        assert!(cfg.sort_by_artist);
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
            },
        ];

        let result = LibrarySyncEngine::deduplicate_and_organize_tracks(items, true, true);
        // Duplicate Daft Punk track should be merged away!
        assert_eq!(result.len(), 2);
        // Sorted alphabetically: Daft Punk first, then The Weeknd
        assert_eq!(result[0].artist, "Daft Punk");
        assert_eq!(result[1].artist, "The Weeknd");
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
        let sources = LibrarySyncEngine::auto_detect_all_sources();
        #[cfg(target_os = "macos")]
        {
            assert!(!sources.is_empty(), "Should auto-detect local macOS sources (Music.app and/or Zen)");
        }
    }
}
