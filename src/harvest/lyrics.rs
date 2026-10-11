//! Lyrics Resolver and Synced LRC Generator for OmniRip.
//! Integrates LRCLIB public API for millisecond-synced lyrics with video synopsis fallback.

use reqwest::header::{ACCEPT, USER_AGENT};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct LyricsData {
    pub synced_lyrics: Option<String>,
    pub plain_lyrics: Option<String>,
    pub source: String,
}

/// Asynchronously queries LRCLIB for synced and plain lyrics.
pub async fn fetch_lyrics_lrclib(
    artist: &str,
    title: &str,
    album: Option<&str>,
) -> Result<LyricsData, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(8))
        .build()
        .map_err(|e| format!("HTTP client init failed: {}", e))?;

    // 1. Try exact match query
    let mut query_params = vec![
        ("artist_name", artist.trim()),
        ("track_name", title.trim()),
    ];
    if let Some(alb) = album {
        if !alb.trim().is_empty() {
            query_params.push(("album_name", alb.trim()));
        }
    }

    let url = "https://lrclib.net/api/get";
    let resp = client
        .get(url)
        .header(USER_AGENT, "OmniRip/0.2.0 ( https://github.com/abdullah-binmadhi/OmniRip )")
        .header(ACCEPT, "application/json")
        .query(&query_params)
        .send()
        .await;

    if let Ok(r) = resp {
        if r.status().is_success() {
            if let Ok(json) = r.json::<serde_json::Value>().await {
                let synced = json["syncedLyrics"].as_str().map(|s| s.to_string());
                let plain = json["plainLyrics"].as_str().map(|s| s.to_string());
                if synced.is_some() || plain.is_some() {
                    return Ok(LyricsData {
                        synced_lyrics: synced,
                        plain_lyrics: plain,
                        source: "LRCLIB (Exact Match)".to_string(),
                    });
                }
            }
        }
    }

    // 2. Try search query if exact match yields no entry
    let search_url = "https://lrclib.net/api/search";
    let q = format!("{} {}", artist.trim(), title.trim());
    let search_resp = client
        .get(search_url)
        .header(USER_AGENT, "OmniRip/0.2.0 ( https://github.com/abdullah-binmadhi/OmniRip )")
        .header(ACCEPT, "application/json")
        .query(&[("q", q.as_str())])
        .send()
        .await;

    if let Ok(r) = search_resp {
        if r.status().is_success() {
            if let Ok(json) = r.json::<serde_json::Value>().await {
                if let Some(arr) = json.as_array() {
                    if let Some(first) = arr.first() {
                        let synced = first["syncedLyrics"].as_str().map(|s| s.to_string());
                        let plain = first["plainLyrics"].as_str().map(|s| s.to_string());
                        if synced.is_some() || plain.is_some() {
                            return Ok(LyricsData {
                                synced_lyrics: synced,
                                plain_lyrics: plain,
                                source: "LRCLIB (Fuzzy Search)".to_string(),
                            });
                        }
                    }
                }
            }
        }
    }

    Err("No lyrics found on LRCLIB".to_string())
}

/// Extracts lyrics block from raw video descriptions / synopses.
pub fn extract_lyrics_from_text(text: &str) -> Option<String> {
    let lower = text.to_lowercase();
    let markers = ["lyrics\n", "lyrics:\n", "lyrics/\n", "lyrics -\n"];

    for marker in &markers {
        if let Some(pos) = lower.find(marker) {
            let start = pos + marker.len();
            let sub = &text[start..];
            let mut lines = Vec::new();

            for line in sub.lines() {
                let trimmed = line.trim();
                // Stop if hitting metadata or footer
                if trimmed.starts_with('#')
                    || trimmed.to_lowercase().starts_with("follow ")
                    || trimmed.to_lowercase().starts_with("stream ")
                    || trimmed.starts_with("http://")
                    || trimmed.starts_with("https://")
                {
                    break;
                }
                lines.push(line);
            }

            let result = lines.join("\n").trim().to_string();
            if !result.is_empty() {
                return Some(result);
            }
        }
    }

    None
}

/// Writes synchronized LRC content to a companion `<track_stem>.lrc` file.
pub fn save_lrc_file<P: AsRef<Path>>(audio_path: P, synced_lyrics: &str) -> Result<PathBuf, String> {
    let lrc_path = audio_path.as_ref().with_extension("lrc");
    std::fs::write(&lrc_path, synced_lyrics)
        .map_err(|e| format!("Failed to write LRC file to {}: {}", lrc_path.display(), e))?;
    Ok(lrc_path)
}

/// Resolves lyrics from LRCLIB with description fallback and writes companion .lrc file if synced.
pub async fn resolve_and_save_lyrics<P: AsRef<Path>>(
    artist: &str,
    title: &str,
    album: Option<&str>,
    synopsis: Option<&str>,
    audio_path: P,
) -> Result<LyricsData, String> {
    // 1. Attempt LRCLIB
    if let Ok(data) = fetch_lyrics_lrclib(artist, title, album).await {
        if let Some(ref synced) = data.synced_lyrics {
            let _ = save_lrc_file(audio_path.as_ref(), synced);
        }
        return Ok(data);
    }

    // 2. Fallback to video synopsis
    if let Some(text) = synopsis {
        if let Some(extracted) = extract_lyrics_from_text(text) {
            return Ok(LyricsData {
                synced_lyrics: None,
                plain_lyrics: Some(extracted),
                source: "Video Synopsis Extraction".to_string(),
            });
        }
    }

    Err("Lyrics not found from LRCLIB or video description".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_lyrics_from_text_valid() {
        let text = "Imogen Heap - Headlock\n\nLyrics\nDistant flickering, greener scenery.\nThis weather's bringing it all back again.\n\n#ImogenHeap #Headlock";
        let lyrics = extract_lyrics_from_text(text).expect("Should extract lyrics");
        assert!(lyrics.contains("Distant flickering, greener scenery."));
        assert!(!lyrics.contains("#ImogenHeap"));
    }

    #[test]
    fn test_extract_lyrics_from_text_none() {
        let text = "Just a video description with no song words at all.";
        assert!(extract_lyrics_from_text(text).is_none());
    }

    #[test]
    fn test_save_lrc_file() {
        let temp_dir = std::env::temp_dir();
        let audio_path = temp_dir.join("test_song.flac");
        let lrc_content = "[00:12.00]First line\n[00:15.50]Second line\n";

        let lrc_path = save_lrc_file(&audio_path, lrc_content).expect("Should write LRC file");
        assert_eq!(lrc_path, temp_dir.join("test_song.lrc"));

        let read_back = std::fs::read_to_string(&lrc_path).expect("Should read back");
        assert_eq!(read_back, lrc_content);

        let _ = std::fs::remove_file(lrc_path);
    }
}
