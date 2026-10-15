//! Zero-Authentication Streaming Playlist & Album Parser
//!
//! Extracts complete tracklists (title, artist, album, duration, ISRC)
//! from public Spotify, Apple Music, YouTube Music, and local M3U/CSV files
//! without requiring developer accounts or user passwords.

use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StreamingService {
    Spotify,
    AppleMusic,
    YouTubeMusic,
    LocalM3u,
    Unknown,
}

impl StreamingService {
    pub fn detect(url: &str) -> Self {
        let trimmed = url.trim().to_lowercase();
        if trimmed.contains("spotify.com/playlist/")
            || trimmed.contains("spotify.com/album/")
            || trimmed.contains("spotify.com/track/")
        {
            StreamingService::Spotify
        } else if trimmed.contains("music.apple.com/") || trimmed.contains("itunes.apple.com/") {
            StreamingService::AppleMusic
        } else if trimmed.contains("music.youtube.com/playlist")
            || trimmed.contains("youtube.com/playlist")
            || trimmed.contains("youtu.be/")
        {
            StreamingService::YouTubeMusic
        } else if trimmed.ends_with(".m3u")
            || trimmed.ends_with(".m3u8")
            || trimmed.ends_with(".csv")
            || trimmed.starts_with("#extm3u")
        {
            StreamingService::LocalM3u
        } else {
            StreamingService::Unknown
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            StreamingService::Spotify => "Spotify",
            StreamingService::AppleMusic => "Apple Music",
            StreamingService::YouTubeMusic => "YouTube Music",
            StreamingService::LocalM3u => "Local M3U / CSV",
            StreamingService::Unknown => "Unknown Source",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParsedTrack {
    pub title: String,
    pub artist: String,
    pub album: String,
    pub duration_secs: Option<u64>,
    pub isrc: Option<String>,
    pub track_number: Option<u32>,
    pub cover_art_url: Option<String>,
    pub source_url: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParsedPlaylist {
    pub name: String,
    pub description: Option<String>,
    pub service: StreamingService,
    pub tracks: Vec<ParsedTrack>,
}

pub struct PlaylistParser {
    client: reqwest::Client,
}

impl Default for PlaylistParser {
    fn default() -> Self {
        Self::new()
    }
}

impl PlaylistParser {
    pub fn new() -> Self {
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(12))
            .user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            .build()
            .unwrap_or_default();
        Self { client }
    }

    /// Extract playlist tracks from any supported public streaming URL or local file path.
    pub async fn parse_url_or_path(&self, input: &str) -> Result<ParsedPlaylist, String> {
        let service = StreamingService::detect(input);
        match service {
            StreamingService::Spotify => self.parse_spotify(input).await,
            StreamingService::AppleMusic => self.parse_apple_music(input).await,
            StreamingService::YouTubeMusic => self.parse_youtube_music(input).await,
            StreamingService::LocalM3u => self.parse_local_file(input),
            StreamingService::Unknown => {
                // If it exists as a local file, try parsing as M3U/CSV
                if Path::new(input.trim()).exists() {
                    self.parse_local_file(input)
                } else {
                    Err(format!("Unrecognized streaming URL or unsupported format: '{}'. Supported: Spotify, Apple Music, YouTube Music playlists, and .m3u8/.csv files.", input))
                }
            }
        }
    }

    /// Parse Spotify public playlist or album via embed endpoint without login.
    pub async fn parse_spotify(&self, url: &str) -> Result<ParsedPlaylist, String> {
        let embed_url = to_spotify_embed_url(url)?;
        let resp = self
            .client
            .get(&embed_url)
            .send()
            .await
            .map_err(|e| format!("Spotify embed request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Spotify returned HTTP error status {}", resp.status()));
        }

        let html = resp.text().await.map_err(|e| format!("Failed to read Spotify response: {}", e))?;
        parse_spotify_embed_html(&html)
    }

    /// Parse Apple Music public playlist or album.
    pub async fn parse_apple_music(&self, url: &str) -> Result<ParsedPlaylist, String> {
        // If URL contains catalog ID, we can query iTunes Lookup API (public, no auth)
        if let Some(id) = extract_apple_music_id(url) {
            let lookup_url = format!("https://itunes.apple.com/lookup?id={}&entity=song", id);
            if let Ok(resp) = self.client.get(&lookup_url).send().await {
                if resp.status().is_success() {
                    if let Ok(text) = resp.text().await {
                        if let Ok(parsed) = parse_itunes_lookup_json(&text) {
                            if !parsed.tracks.is_empty() {
                                return Ok(parsed);
                            }
                        }
                    }
                }
            }
        }

        // Web scraping fallback
        let resp = self
            .client
            .get(url)
            .send()
            .await
            .map_err(|e| format!("Apple Music request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Apple Music returned status {}", resp.status()));
        }

        let html = resp.text().await.map_err(|e| format!("Failed to read Apple Music response: {}", e))?;
        parse_apple_music_html(&html)
    }

    /// Parse YouTube or YouTube Music playlist via yt-dlp --flat-playlist -J.
    pub async fn parse_youtube_music(&self, url: &str) -> Result<ParsedPlaylist, String> {
        let output = tokio::process::Command::new("yt-dlp")
            .arg("--flat-playlist")
            .arg("-J")
            .arg("--no-warnings")
            .arg(url)
            .output()
            .await
            .map_err(|e| format!("Failed to execute yt-dlp: {}", e))?;

        if !output.status.success() {
            let err = String::from_utf8_lossy(&output.stderr);
            return Err(format!("yt-dlp failed to parse playlist: {}", err.trim()));
        }

        let json_text = String::from_utf8_lossy(&output.stdout);
        parse_yt_dlp_json(&json_text)
    }

    /// Parse local M3U / M3U8 or CSV file.
    pub fn parse_local_file(&self, path_or_content: &str) -> Result<ParsedPlaylist, String> {
        let path = Path::new(path_or_content.trim());
        let content = if path.exists() {
            std::fs::read_to_string(path).map_err(|e| format!("Failed to read local playlist file: {}", e))?
        } else {
            path_or_content.to_string()
        };

        if content.contains("#EXTM3U") || path_or_content.ends_with(".m3u") || path_or_content.ends_with(".m3u8") {
            parse_m3u_text(&content, path.file_stem().and_then(|s| s.to_str()).unwrap_or("Local Playlist"))
        } else {
            parse_csv_text(&content, path.file_stem().and_then(|s| s.to_str()).unwrap_or("CSV Playlist"))
        }
    }
}

/// Helper to convert standard Spotify playlist/album URLs into embed URLs.
pub fn to_spotify_embed_url(url: &str) -> Result<String, String> {
    let clean = url.split('?').next().unwrap_or(url).trim();
    if clean.contains("/embed/") {
        return Ok(clean.to_string());
    }

    if let Some((_, rest)) = clean.split_once("spotify.com/") {
        let parts: Vec<&str> = rest.split('/').collect();
        if parts.len() >= 2 {
            let entity_type = parts[0];
            let id = parts[1];
            return Ok(format!("https://open.spotify.com/embed/{}/{}", entity_type, id));
        }
    }

    Err(format!("Could not extract Spotify entity ID from URL: {}", url))
}

/// Parse Spotify embed HTML looking for the `__NEXT_DATA__` script tag.
pub fn parse_spotify_embed_html(html: &str) -> Result<ParsedPlaylist, String> {
    let marker = "<script id=\"__NEXT_DATA__\" type=\"application/json\">";
    let Some((_, rest)) = html.split_once(marker) else {
        return Err("Could not find Spotify embed JSON payload in page.".to_string());
    };
    let Some((json_str, _)) = rest.split_once("</script>") else {
        return Err("Malformed Spotify embed payload (missing closing script tag).".to_string());
    };

    parse_spotify_embed_json(json_str)
}

/// Parse Spotify JSON payload from embed script.
pub fn parse_spotify_embed_json(json_str: &str) -> Result<ParsedPlaylist, String> {
    let v: serde_json::Value = serde_json::from_str(json_str).map_err(|e| format!("Spotify JSON parse error: {}", e))?;

    let entity = v
        .pointer("/props/pageProps/state/data/entity")
        .or_else(|| v.pointer("/props/pageProps/data/entity"))
        .ok_or_else(|| "Missing entity in Spotify payload".to_string())?;

    let name = entity
        .get("name")
        .or_else(|| entity.get("title"))
        .and_then(|s| s.as_str())
        .unwrap_or("Spotify Playlist")
        .to_string();

    let description = entity.get("description").and_then(|s| s.as_str()).map(|s| s.to_string());

    let mut tracks = Vec::new();
    if let Some(track_list) = entity.get("trackList").and_then(|t| t.as_array()) {
        for (i, item) in track_list.iter().enumerate() {
            let title = item.get("title").and_then(|s| s.as_str()).unwrap_or("Unknown Title").to_string();
            let artist = item
                .get("subtitle")
                .or_else(|| item.get("artist"))
                .and_then(|s| s.as_str())
                .unwrap_or("Unknown Artist")
                .to_string();

            let album = item
                .get("album")
                .and_then(|a| a.get("name").or_else(|| a.get("title")))
                .and_then(|s| s.as_str())
                .unwrap_or(&name)
                .to_string();

            let duration_secs = item.get("duration").and_then(|d| d.as_u64()).map(|ms| ms / 1000);
            let isrc = item.get("isrc").and_then(|s| s.as_str()).map(|s| s.to_string());
            let source_url = item.get("uri").and_then(|s| s.as_str()).map(|s| s.to_string());

            tracks.push(ParsedTrack {
                title,
                artist,
                album,
                duration_secs,
                isrc,
                track_number: Some((i + 1) as u32),
                cover_art_url: None,
                source_url,
            });
        }
    }

    Ok(ParsedPlaylist {
        name,
        description,
        service: StreamingService::Spotify,
        tracks,
    })
}

/// Extracts numeric catalog ID from Apple Music URL.
pub fn extract_apple_music_id(url: &str) -> Option<String> {
    let clean = url.split('?').next().unwrap_or(url);
    if let Some((_, id_part)) = clean.rsplit_once("/id") {
        return Some(id_part.chars().take_while(|c| c.is_ascii_digit()).collect());
    }
    if let Some((_, id_part)) = clean.rsplit_once("/i=") {
        return Some(id_part.chars().take_while(|c| c.is_ascii_digit()).collect());
    }
    None
}

/// Parses Apple Music / iTunes lookup JSON.
pub fn parse_itunes_lookup_json(json_str: &str) -> Result<ParsedPlaylist, String> {
    let v: serde_json::Value = serde_json::from_str(json_str).map_err(|e| format!("iTunes lookup JSON error: {}", e))?;

    let results = v.get("results").and_then(|r| r.as_array()).ok_or_else(|| "Missing results array in iTunes response".to_string())?;

    if results.is_empty() {
        return Err("No tracks found in iTunes lookup".to_string());
    }

    let playlist_name = results[0]
        .get("collectionName")
        .and_then(|s| s.as_str())
        .unwrap_or("Apple Music Collection")
        .to_string();

    let mut tracks = Vec::new();
    for (i, item) in results.iter().enumerate() {
        if item.get("wrapperType").and_then(|s| s.as_str()) == Some("collection") {
            continue;
        }

        let title = item.get("trackName").and_then(|s| s.as_str()).unwrap_or("Unknown Title").to_string();
        let artist = item.get("artistName").and_then(|s| s.as_str()).unwrap_or("Unknown Artist").to_string();
        let album = item.get("collectionName").and_then(|s| s.as_str()).unwrap_or(&playlist_name).to_string();
        let duration_secs = item.get("trackTimeMillis").and_then(|m| m.as_u64()).map(|ms| ms / 1000);
        let track_number = item.get("trackNumber").and_then(|n| n.as_u64()).map(|n| n as u32).unwrap_or((i + 1) as u32);
        let cover_art_url = item.get("artworkUrl100").and_then(|s| s.as_str()).map(|s| s.to_string());

        tracks.push(ParsedTrack {
            title,
            artist,
            album,
            duration_secs,
            isrc: None,
            track_number: Some(track_number),
            cover_art_url,
            source_url: None,
        });
    }

    Ok(ParsedPlaylist {
        name: playlist_name,
        description: None,
        service: StreamingService::AppleMusic,
        tracks,
    })
}

/// Basic regex-free Apple Music HTML parser for public playlist pages.
pub fn parse_apple_music_html(html: &str) -> Result<ParsedPlaylist, String> {
    let title = if let Some((_, r)) = html.split_once("<title>") {
        r.split_once("</title>").map(|(t, _)| t.trim().replace(" on Apple Music", "")).unwrap_or_else(|| "Apple Music Playlist".to_string())
    } else {
        "Apple Music Playlist".to_string()
    };

    let mut tracks = Vec::new();
    let song_markers = html.split("class=\"songs-list-row\"");
    for (i, block) in song_markers.skip(1).enumerate() {
        let track_title = if let Some((_, r)) = block.split_once("class=\"songs-list-row__song-name\">") {
            r.split_once('<').map(|(s, _)| s.trim().to_string()).unwrap_or_default()
        } else {
            continue;
        };

        if track_title.is_empty() {
            continue;
        }

        let artist_name = if let Some((_, r)) = block.split_once("class=\"songs-list-row__by-line\">") {
            r.split_once('<').map(|(s, _)| s.trim().to_string()).unwrap_or_else(|| "Unknown Artist".to_string())
        } else {
            "Unknown Artist".to_string()
        };

        tracks.push(ParsedTrack {
            title: track_title,
            artist: artist_name,
            album: title.clone(),
            duration_secs: None,
            isrc: None,
            track_number: Some((i + 1) as u32),
            cover_art_url: None,
            source_url: None,
        });
    }

    if tracks.is_empty() {
        return Err("Could not extract any tracks from Apple Music page.".to_string());
    }

    Ok(ParsedPlaylist {
        name: title,
        description: None,
        service: StreamingService::AppleMusic,
        tracks,
    })
}

/// Parse yt-dlp JSON dump for a playlist or album.
pub fn parse_yt_dlp_json(json_str: &str) -> Result<ParsedPlaylist, String> {
    let v: serde_json::Value = serde_json::from_str(json_str).map_err(|e| format!("yt-dlp JSON parse error: {}", e))?;

    let name = v
        .get("title")
        .and_then(|s| s.as_str())
        .unwrap_or("YouTube Playlist")
        .to_string();

    let description = v.get("description").and_then(|s| s.as_str()).map(|s| s.to_string());

    let mut tracks = Vec::new();
    if let Some(entries) = v.get("entries").and_then(|e| e.as_array()) {
        for (i, entry) in entries.iter().enumerate() {
            let full_title = entry.get("title").and_then(|s| s.as_str()).unwrap_or("Unknown Title");
            let uploader = entry
                .get("uploader")
                .or_else(|| entry.get("channel"))
                .and_then(|s| s.as_str())
                .unwrap_or("Unknown Artist");

            // Split "Artist - Title" if present
            let (artist, title) = if let Some((a, t)) = full_title.split_once(" - ") {
                (a.trim().to_string(), t.trim().to_string())
            } else {
                (uploader.to_string(), full_title.to_string())
            };

            let duration_secs = entry.get("duration").and_then(|d| d.as_u64());
            let source_url = entry.get("url").or_else(|| entry.get("webpage_url")).and_then(|s| s.as_str()).map(|s| s.to_string());

            tracks.push(ParsedTrack {
                title,
                artist,
                album: name.clone(),
                duration_secs,
                isrc: None,
                track_number: Some((i + 1) as u32),
                cover_art_url: None,
                source_url,
            });
        }
    }

    Ok(ParsedPlaylist {
        name,
        description,
        service: StreamingService::YouTubeMusic,
        tracks,
    })
}

/// Parse standard extended M3U text (`#EXTM3U`, `#EXTINF:seconds,Artist - Title`).
pub fn parse_m3u_text(content: &str, playlist_name: &str) -> Result<ParsedPlaylist, String> {
    let mut tracks = Vec::new();
    let mut current_duration = None;
    let mut current_artist = String::new();
    let mut current_title = String::new();

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with("#EXTM3U") {
            continue;
        }

        if let Some(rest) = trimmed.strip_prefix("#EXTINF:") {
            if let Some((dur_str, meta)) = rest.split_once(',') {
                current_duration = dur_str.trim().parse::<i64>().ok().filter(|&d| d > 0).map(|d| d as u64);
                if let Some((artist, title)) = meta.split_once(" - ") {
                    current_artist = artist.trim().to_string();
                    current_title = title.trim().to_string();
                } else {
                    current_artist = "Unknown Artist".to_string();
                    current_title = meta.trim().to_string();
                }
            }
        } else if !trimmed.starts_with('#') {
            // File line
            let title = if current_title.is_empty() {
                Path::new(trimmed).file_stem().and_then(|s| s.to_str()).unwrap_or(trimmed).to_string()
            } else {
                current_title.clone()
            };
            let artist = if current_artist.is_empty() {
                "Unknown Artist".to_string()
            } else {
                current_artist.clone()
            };

            tracks.push(ParsedTrack {
                title,
                artist,
                album: playlist_name.to_string(),
                duration_secs: current_duration,
                isrc: None,
                track_number: Some((tracks.len() + 1) as u32),
                cover_art_url: None,
                source_url: Some(trimmed.to_string()),
            });

            current_duration = None;
            current_artist.clear();
            current_title.clear();
        }
    }

    if tracks.is_empty() {
        return Err("No tracks found in M3U content.".to_string());
    }

    Ok(ParsedPlaylist {
        name: playlist_name.to_string(),
        description: None,
        service: StreamingService::LocalM3u,
        tracks,
    })
}

/// Parse basic CSV text (`Title,Artist,Album` or `Track,Artist,Album`).
pub fn parse_csv_text(content: &str, playlist_name: &str) -> Result<ParsedPlaylist, String> {
    let mut tracks = Vec::new();
    let mut lines = content.lines();

    // Check header
    let first_line = lines.next().unwrap_or("");
    let is_header = first_line.to_lowercase().contains("title") || first_line.to_lowercase().contains("artist");

    let data_lines: Box<dyn Iterator<Item = &str>> = if is_header {
        Box::new(lines)
    } else {
        Box::new(std::iter::once(first_line).chain(lines))
    };

    for line in data_lines {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let parts: Vec<&str> = trimmed.split(',').map(|s| s.trim().trim_matches('"')).collect();
        if parts.is_empty() {
            continue;
        }

        let (title, artist, album) = match parts.len() {
            1 => (parts[0].to_string(), "Unknown Artist".to_string(), playlist_name.to_string()),
            2 => (parts[0].to_string(), parts[1].to_string(), playlist_name.to_string()),
            _ => (parts[0].to_string(), parts[1].to_string(), parts[2].to_string()),
        };

        tracks.push(ParsedTrack {
            title,
            artist,
            album,
            duration_secs: None,
            isrc: None,
            track_number: Some((tracks.len() + 1) as u32),
            cover_art_url: None,
            source_url: None,
        });
    }

    if tracks.is_empty() {
        return Err("No tracks found in CSV content.".to_string());
    }

    Ok(ParsedPlaylist {
        name: playlist_name.to_string(),
        description: None,
        service: StreamingService::LocalM3u,
        tracks,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_service_detection() {
        assert_eq!(
            StreamingService::detect("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"),
            StreamingService::Spotify
        );
        assert_eq!(
            StreamingService::detect("https://open.spotify.com/album/4yP0hdKO0Pip5AN2EbtmDp"),
            StreamingService::Spotify
        );
        assert_eq!(
            StreamingService::detect("https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aaacabb233eb5eb"),
            StreamingService::AppleMusic
        );
        assert_eq!(
            StreamingService::detect("https://music.youtube.com/playlist?list=RDCLAK5uy_kfdjh8k7"),
            StreamingService::YouTubeMusic
        );
        assert_eq!(
            StreamingService::detect("/path/to/my_library.m3u8"),
            StreamingService::LocalM3u
        );
        assert_eq!(
            StreamingService::detect("https://example.com/unknown"),
            StreamingService::Unknown
        );
    }

    #[test]
    fn test_to_spotify_embed_url() {
        let input = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=12345";
        let embed = to_spotify_embed_url(input).unwrap();
        assert_eq!(embed, "https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M");
    }

    #[test]
    fn test_parse_spotify_embed_json() {
        let sample_json = r#"{
            "props": {
                "pageProps": {
                    "state": {
                        "data": {
                            "entity": {
                                "name": "Synthwave Chill",
                                "description": "Relaxing retro electronic beats",
                                "trackList": [
                                    {
                                        "title": "Midnight City",
                                        "subtitle": "M83",
                                        "duration": 243000,
                                        "isrc": "FR01A1100360",
                                        "uri": "spotify:track:123"
                                    },
                                    {
                                        "title": "Resonance",
                                        "subtitle": "HOME",
                                        "duration": 212000,
                                        "isrc": "USHM81400010",
                                        "uri": "spotify:track:456"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }"#;

        let parsed = parse_spotify_embed_json(sample_json).unwrap();
        assert_eq!(parsed.name, "Synthwave Chill");
        assert_eq!(parsed.service, StreamingService::Spotify);
        assert_eq!(parsed.tracks.len(), 2);
        assert_eq!(parsed.tracks[0].title, "Midnight City");
        assert_eq!(parsed.tracks[0].artist, "M83");
        assert_eq!(parsed.tracks[0].duration_secs, Some(243));
        assert_eq!(parsed.tracks[0].isrc.as_deref(), Some("FR01A1100360"));
        assert_eq!(parsed.tracks[1].title, "Resonance");
    }

    #[test]
    fn test_parse_m3u_text() {
        let m3u = "#EXTM3U\n#EXTINF:215,Daft Punk - Get Lucky\n/music/daft_punk.mp3\n#EXTINF:180,The Weeknd - Blinding Lights\n/music/blinding_lights.flac\n";
        let parsed = parse_m3u_text(m3u, "French Touch").unwrap();
        assert_eq!(parsed.name, "French Touch");
        assert_eq!(parsed.tracks.len(), 2);
        assert_eq!(parsed.tracks[0].artist, "Daft Punk");
        assert_eq!(parsed.tracks[0].title, "Get Lucky");
        assert_eq!(parsed.tracks[0].duration_secs, Some(215));
        assert_eq!(parsed.tracks[1].artist, "The Weeknd");
        assert_eq!(parsed.tracks[1].title, "Blinding Lights");
    }

    #[test]
    fn test_parse_csv_text() {
        let csv = "Title,Artist,Album\n\"Starboy\",\"The Weeknd\",\"Starboy\"\n\"Get Lucky\",\"Daft Punk\",\"RAM\"";
        let parsed = parse_csv_text(csv, "Top Hits").unwrap();
        assert_eq!(parsed.tracks.len(), 2);
        assert_eq!(parsed.tracks[0].title, "Starboy");
        assert_eq!(parsed.tracks[0].artist, "The Weeknd");
        assert_eq!(parsed.tracks[0].album, "Starboy");
    }
}
