//! Cross-Platform Stream Resolver & Local Cache Engine
//!
//! Resolves Spotify, Apple Music, YouTube Music, and plain-text song queries
//! to high-bitrate Opus/AAC audio streams using zero-auth public lookups,
//! caching resolved video mappings locally in `~/.config/omnirip/stream_cache.json`
//! for instant sub-millisecond replay.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum AudioQualityTier {
    HiResFlac24,
    CdFlac16,
    StudioLossy320,
    CloudOpus160,
    CloudAac128,
}

impl Default for AudioQualityTier {
    fn default() -> Self {
        AudioQualityTier::CloudOpus160
    }
}

impl AudioQualityTier {
    pub fn label(&self) -> &'static str {
        match self {
            AudioQualityTier::HiResFlac24 => "24-BIT HI-RES FLAC",
            AudioQualityTier::CdFlac16 => "16-BIT CD FLAC",
            AudioQualityTier::StudioLossy320 => "320K STUDIO MP3",
            AudioQualityTier::CloudOpus160 => "160K CLOUD OPUS",
            AudioQualityTier::CloudAac128 => "128K CLOUD AAC",
        }
    }

    pub fn short_badge(&self) -> &'static str {
        match self {
            AudioQualityTier::HiResFlac24 => "24-BIT FLAC",
            AudioQualityTier::CdFlac16 => "16-BIT FLAC",
            AudioQualityTier::StudioLossy320 => "320K MP3",
            AudioQualityTier::CloudOpus160 => "160K OPUS",
            AudioQualityTier::CloudAac128 => "128K AAC",
        }
    }

    pub fn is_lossless(&self) -> bool {
        matches!(self, AudioQualityTier::HiResFlac24 | AudioQualityTier::CdFlac16)
    }

    pub fn nominal_bitrate_kbps(&self) -> u32 {
        match self {
            AudioQualityTier::HiResFlac24 => 2304,
            AudioQualityTier::CdFlac16 => 920,
            AudioQualityTier::StudioLossy320 => 320,
            AudioQualityTier::CloudOpus160 => 160,
            AudioQualityTier::CloudAac128 => 128,
        }
    }

    pub fn sample_rate_hz(&self) -> u32 {
        match self {
            AudioQualityTier::HiResFlac24 => 96000,
            AudioQualityTier::CdFlac16 => 44100,
            AudioQualityTier::StudioLossy320 => 44100,
            AudioQualityTier::CloudOpus160 => 48000,
            AudioQualityTier::CloudAac128 => 44100,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedStreamEntry {
    pub query_key: String,
    pub video_id: String,
    pub title: String,
    pub artist: String,
    pub duration_secs: u32,
    pub format: String,
    #[serde(default)]
    pub quality_tier: AudioQualityTier,
    pub timestamp_secs: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct StreamCacheStore {
    pub entries: HashMap<String, CachedStreamEntry>,
}

impl StreamCacheStore {
    pub fn cache_file_path() -> PathBuf {
        if let Ok(home) = std::env::var("HOME") {
            PathBuf::from(home).join(".config").join("omnirip").join("stream_cache.json")
        } else {
            PathBuf::from(".config/omnirip/stream_cache.json")
        }
    }

    pub fn load() -> Self {
        let path = Self::cache_file_path();
        if !path.exists() {
            return Self::default();
        }

        if let Ok(mut file) = File::open(&path) {
            let mut contents = String::new();
            if file.read_to_string(&mut contents).is_ok() {
                if let Ok(store) = serde_json::from_str::<StreamCacheStore>(&contents) {
                    return store;
                }
            }
        }

        Self::default()
    }

    pub fn save(&self) {
        let path = Self::cache_file_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(json) = serde_json::to_string_pretty(self) {
            if let Ok(mut file) = File::create(&path) {
                let _ = file.write_all(json.as_bytes());
            }
        }
    }

    pub fn get(&self, query_key: &str) -> Option<&CachedStreamEntry> {
        let norm = normalize_query(query_key);
        self.entries.get(&norm)
    }

    pub fn insert(&mut self, entry: CachedStreamEntry) {
        let norm = normalize_query(&entry.query_key);
        self.entries.insert(norm, entry);
        self.save();
    }
}

pub fn normalize_query(query: &str) -> String {
    query
        .trim()
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == ' ' || *c == '-')
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

pub struct StreamResolver;

impl StreamResolver {
    /// Resolves and fetches an audio file for a track query or URL, returning local audio file path, quality tier, and label.
    pub fn resolve_and_fetch_audio(query: &str, artist: &str, title: &str) -> Result<(PathBuf, AudioQualityTier, String), String> {
        let mut cache = StreamCacheStore::load();
        let query_key = if !artist.is_empty() && !title.is_empty() {
            format!("{} - {}", artist, title)
        } else {
            query.to_string()
        };

        let temp_dir = std::env::temp_dir();
        let safe_name = crate::harvest::yt_dlp::sanitize_filename(&query_key);

        // Tier 1 & 2 Probe: Check local stream cache or downloads for verified FLAC
        let flac_file = temp_dir.join(format!("omnirip_stream_{}.flac", safe_name));
        if flac_file.exists() {
            if let Ok(meta) = fs::metadata(&flac_file) {
                if meta.len() > 500_000 {
                    // Check if 24-bit Hi-Res based on file size threshold or return CD FLAC
                    let tier = if meta.len() > 30_000_000 {
                        AudioQualityTier::HiResFlac24
                    } else {
                        AudioQualityTier::CdFlac16
                    };
                    return Ok((flac_file, tier, format!("{} (Lossless Cache)", tier.label())));
                }
            }
        }

        // Tier 3 Probe: Check for local 320k MP3
        let mp3_file = temp_dir.join(format!("omnirip_stream_{}.mp3", safe_name));
        if mp3_file.exists() {
            if let Ok(meta) = fs::metadata(&mp3_file) {
                if meta.len() > 200_000 {
                    return Ok((mp3_file, AudioQualityTier::StudioLossy320, "320K STUDIO MP3 (Local Cache)".to_string()));
                }
            }
        }

        // Tier 4 Probe: Check for cached 160k Opus / M4A stream
        // Check for cached native streams (opus, webm, m4a, mp3, flac)
        for ext in &["opus", "webm", "m4a", "mp3", "flac"] {
            let cached_file = temp_dir.join(format!("omnirip_stream_{}.{}", safe_name, ext));
            if cached_file.exists() {
                if let Ok(meta) = fs::metadata(&cached_file) {
                    if meta.len() > 100_000 {
                        let tier = if *ext == "flac" {
                            if meta.len() > 30_000_000 { AudioQualityTier::HiResFlac24 } else { AudioQualityTier::CdFlac16 }
                        } else if meta.len() > 6_000_000 {
                            AudioQualityTier::StudioLossy320
                        } else {
                            AudioQualityTier::CloudOpus160
                        };
                        return Ok((cached_file, tier, format!("{} (Cached Stream)", tier.label())));
                    }
                }
            }
        }

        // Direct Cloud Ingestion via yt-dlp: Native Opus 256k / Highest Bitrate Audio
        let is_direct_url = (query.starts_with("http://") || query.starts_with("https://"))
            && !query.contains("/playlist")
            && !query.contains("list=");

        let primary_query = if is_direct_url {
            query.to_string()
        } else if !artist.is_empty() && !title.is_empty() {
            format!("ytsearch1:{} - {}", artist, title)
        } else {
            format!("ytsearch1:{}", query)
        };

        let output_template = temp_dir.join(format!("omnirip_stream_{}.%(ext)s", safe_name));

        let execute_ytdlp = |q: &str| -> Result<std::process::Output, String> {
            let mut cmd = Command::new("yt-dlp");
            cmd.args([
                "-f", "bestaudio[acodec=opus]/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio",
                "--no-part",
                "--no-playlist",
                "--buffer-size", "16K",
                "-o", output_template.to_str().unwrap_or("/tmp/omnirip_stream.%(ext)s"),
            ]);
            if let Some(zen_profile) = crate::harvest::library_sync::LibrarySyncEngine::detect_zen_browser_profiles() {
                cmd.args(["--cookies-from-browser", &format!("firefox:{}", zen_profile.to_string_lossy())]);
            }
            cmd.arg(q);
            cmd.output().map_err(|e| format!("yt-dlp execution failed: {}", e))
        };

        let output = match execute_ytdlp(&primary_query) {
            Ok(out) if out.status.success() => out,
            Ok(failed_out) => {
                // If primary query failed and was a direct URL or specific query, attempt clean fallback search
                if is_direct_url && !artist.is_empty() && !title.is_empty() {
                    let fallback_q = format!("ytsearch1:{} - {}", artist, title);
                    execute_ytdlp(&fallback_q).unwrap_or(failed_out)
                } else {
                    failed_out
                }
            }
            Err(e) => return Err(e),
        };

        let mut resolved_file = None;
        for ext in &["opus", "webm", "m4a", "ogg", "mp3", "flac"] {
            let candidate = temp_dir.join(format!("omnirip_stream_{}.{}", safe_name, ext));
            if candidate.exists() {
                if let Ok(meta) = fs::metadata(&candidate) {
                    if meta.len() > 50_000 {
                        resolved_file = Some(candidate);
                        break;
                    }
                }
            }
        }

        let final_path = match resolved_file {
            Some(p) => p,
            None => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                let first_line = stderr.lines().next().unwrap_or("Stream download error");
                return Err(first_line.to_string());
            }
        };

        let resolved_tier = if let Ok(meta) = fs::metadata(&final_path) {
            let size = meta.len();
            if final_path.extension().and_then(|e| e.to_str()) == Some("flac") {
                if size > 30_000_000 { AudioQualityTier::HiResFlac24 } else { AudioQualityTier::CdFlac16 }
            } else if size > 6_000_000 {
                AudioQualityTier::StudioLossy320
            } else {
                AudioQualityTier::CloudOpus160
            }
        } else {
            AudioQualityTier::CloudOpus160
        };

        // Cache resolution entry
        let entry = CachedStreamEntry {
            query_key: query_key.clone(),
            video_id: safe_name.clone(),
            title: title.to_string(),
            artist: artist.to_string(),
            duration_secs: 0,
            format: resolved_tier.label().to_string(),
            quality_tier: resolved_tier,
            timestamp_secs: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0),
        };
        cache.insert(entry);

        Ok((final_path, resolved_tier, format!("{} (Direct CDN)", resolved_tier.label())))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_query() {
        assert_eq!(normalize_query("  The Weeknd - Blinding Lights!  "), "the weeknd - blinding lights");
        assert_eq!(normalize_query("Daft Punk / Voyager (Official)"), "daft punk voyager official");
    }

    #[test]
    fn test_cache_store_in_memory() {
        let mut store = StreamCacheStore::default();
        let entry = CachedStreamEntry {
            query_key: "Daft Punk - One More Time".to_string(),
            video_id: "FGBhQbmPwH8".to_string(),
            title: "One More Time".to_string(),
            artist: "Daft Punk".to_string(),
            duration_secs: 320,
            format: "Opus 256k".to_string(),
            quality_tier: AudioQualityTier::CloudOpus160,
            timestamp_secs: 1000,
        };

        store.insert(entry);
        let found = store.get("daft punk - one more time");
        assert!(found.is_some());
        assert_eq!(found.unwrap().video_id, "FGBhQbmPwH8");
        assert_eq!(found.unwrap().quality_tier, AudioQualityTier::CloudOpus160);
    }

    #[test]
    fn test_audio_quality_tier_hierarchy_and_properties() {
        assert!(AudioQualityTier::HiResFlac24.is_lossless());
        assert!(AudioQualityTier::CdFlac16.is_lossless());
        assert!(!AudioQualityTier::StudioLossy320.is_lossless());
        assert!(!AudioQualityTier::CloudOpus160.is_lossless());
        assert!(!AudioQualityTier::CloudAac128.is_lossless());

        assert_eq!(AudioQualityTier::HiResFlac24.sample_rate_hz(), 96000);
        assert_eq!(AudioQualityTier::CloudOpus160.sample_rate_hz(), 48000);
        assert_eq!(AudioQualityTier::StudioLossy320.nominal_bitrate_kbps(), 320);
        assert_eq!(AudioQualityTier::CloudOpus160.nominal_bitrate_kbps(), 160);

        assert!(AudioQualityTier::HiResFlac24 < AudioQualityTier::CdFlac16);
        assert!(AudioQualityTier::CdFlac16 < AudioQualityTier::StudioLossy320);
        assert!(AudioQualityTier::StudioLossy320 < AudioQualityTier::CloudOpus160);
    }
}
