//! Asynchronous MusicBrainz REST API Client for OmniRip.
//! Resolves noisy track and video titles into canonical metadata and formatted Nicotine+ search queries.

use reqwest::header::{ACCEPT, USER_AGENT};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct MusicBrainzMetadata {
    pub title: String,
    pub artist: String,
    pub album: Option<String>,
    pub year: Option<u32>,
    pub track_number: Option<u32>,
    pub release_mbid: Option<String>,
    pub nicotine_query: String,
}

/// Builds a high-confidence, clean Soulseek / Nicotine+ search query from artist and title.
/// Avoids quote characters which break Soulseek peer substring matching.
pub fn build_nicotine_query(artist: &str, title: &str) -> String {
    let clean_artist = artist.trim();
    let clean_title = title.trim();

    if clean_artist.is_empty() || clean_artist.eq_ignore_ascii_case("unknown") {
        clean_title.to_string()
    } else {
        format!("{} {}", clean_artist, clean_title)
    }
}

/// Asynchronously looks up canonical recording metadata on MusicBrainz.
pub async fn lookup_metadata(
    artist: Option<&str>,
    title: &str,
) -> Result<MusicBrainzMetadata, String> {
    let clean_title = title.trim();
    if clean_title.is_empty() {
        return Err("Cannot query MusicBrainz with empty title".to_string());
    }

    let lucene_query = match artist {
        Some(art) if !art.trim().is_empty() => {
            format!("recording:\"{}\" AND artist:\"{}\"", clean_title, art.trim())
        }
        _ => format!("recording:\"{}\"", clean_title),
    };

    let url = "https://musicbrainz.org/ws/2/recording";
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(8))
        .build()
        .map_err(|e| format!("HTTP client init failed: {}", e))?;

    let resp = client
        .get(url)
        .header(USER_AGENT, "OmniRip/0.2.0 ( https://github.com/abdullah-binmadhi/OmniRip )")
        .header(ACCEPT, "application/json")
        .query(&[("query", lucene_query.as_str()), ("fmt", "json"), ("limit", "3")])
        .send()
        .await
        .map_err(|e| format!("MusicBrainz network request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("MusicBrainz HTTP error: status {}", resp.status()));
    }

    let json: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse MusicBrainz JSON: {}", e))?;

    parse_recording_json(&json)
}

/// Parses the top match recording from a MusicBrainz JSON response.
pub fn parse_recording_json(json: &serde_json::Value) -> Result<MusicBrainzMetadata, String> {
    let recordings = json
        .get("recordings")
        .and_then(|r| r.as_array())
        .ok_or_else(|| "Missing 'recordings' array in response".to_string())?;

    if recordings.is_empty() {
        return Err("No matching recordings found on MusicBrainz".to_string());
    }

    let top = &recordings[0];
    let title = top
        .get("title")
        .and_then(|t| t.as_str())
        .unwrap_or("Unknown Title")
        .to_string();

    let artist = top
        .get("artist-credit")
        .and_then(|ac| ac.as_array())
        .and_then(|arr| arr.first())
        .and_then(|c| c.get("name"))
        .and_then(|n| n.as_str())
        .unwrap_or("Unknown Artist")
        .to_string();

    let mut album = None;
    let mut year = None;
    let mut track_number = None;
    let mut release_mbid = None;

    if let Some(releases) = top.get("releases").and_then(|r| r.as_array()) {
        if let Some(rel) = releases.first() {
            album = rel.get("title").and_then(|t| t.as_str()).map(|s| s.to_string());
            release_mbid = rel.get("id").and_then(|id| id.as_str()).map(|s| s.to_string());

            if let Some(date_str) = rel.get("date").and_then(|d| d.as_str()) {
                if date_str.len() >= 4 {
                    year = date_str[..4].parse::<u32>().ok();
                }
            }

            if let Some(media) = rel.get("media").and_then(|m| m.as_array()) {
                if let Some(med) = media.first() {
                    if let Some(track) = med.get("track").and_then(|t| t.as_array()) {
                        if let Some(tr) = track.first() {
                            track_number = tr
                                .get("number")
                                .and_then(|n| n.as_str())
                                .and_then(|s| s.parse::<u32>().ok());
                        }
                    }
                }
            }
        }
    }

    let nicotine_query = build_nicotine_query(&artist, &title);

    Ok(MusicBrainzMetadata {
        title,
        artist,
        album,
        year,
        track_number,
        release_mbid,
        nicotine_query,
    })
}

/// Fetches cover art image bytes from the Cover Art Archive using release MBID.
pub async fn fetch_cover_art_archive(release_mbid: &str) -> Option<Vec<u8>> {
    let url = format!("https://coverartarchive.org/release/{}/front-500", release_mbid.trim());
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(6))
        .build()
        .ok()?;

    let resp = client
        .get(&url)
        .header(USER_AGENT, "OmniRip/0.2.0 ( https://github.com/abdullah-binmadhi/OmniRip )")
        .send()
        .await
        .ok()?;

    if resp.status().is_success() {
        resp.bytes().await.ok().map(|b| b.to_vec())
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_nicotine_query() {
        let q = build_nicotine_query("Radiohead", "Karma Police");
        assert_eq!(q, "Radiohead Karma Police");

        let q_unknown = build_nicotine_query("Unknown", "Track Title");
        assert_eq!(q_unknown, "Track Title");
    }

    #[test]
    fn test_parse_recording_json_valid() {
        let sample = serde_json::json!({
            "recordings": [
                {
                    "title": "Karma Police",
                    "artist-credit": [
                        { "name": "Radiohead" }
                    ],
                    "releases": [
                        {
                            "title": "OK Computer",
                            "date": "1997-05-21",
                            "media": [
                                {
                                    "track": [
                                        { "number": "6" }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        });

        let meta = parse_recording_json(&sample).unwrap();
        assert_eq!(meta.title, "Karma Police");
        assert_eq!(meta.artist, "Radiohead");
        assert_eq!(meta.album.as_deref(), Some("OK Computer"));
        assert_eq!(meta.year, Some(1997));
        assert_eq!(meta.track_number, Some(6));
        assert_eq!(meta.nicotine_query, "Radiohead Karma Police");
    }

    #[test]
    fn test_parse_recording_json_empty() {
        let sample = serde_json::json!({ "recordings": [] });
        assert!(parse_recording_json(&sample).is_err());
    }
}
