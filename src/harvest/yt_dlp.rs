//! Asynchronous yt-dlp Audio Downloader for OmniRip.
//! Wraps system yt-dlp to download high-resolution audio (FLAC / OPUS) with real-time progress parsing.

use std::path::Path;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioFormat {
    Mp3,
    Aac,
    Flac,
    Wav,
    Opus,
}

impl AudioFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            AudioFormat::Mp3 => "mp3",
            AudioFormat::Aac => "m4a",
            AudioFormat::Flac => "flac",
            AudioFormat::Wav => "wav",
            AudioFormat::Opus => "opus",
        }
    }

    pub fn yt_audio_format(&self) -> &'static str {
        match self {
            AudioFormat::Mp3 => "mp3",
            AudioFormat::Aac => "aac",
            AudioFormat::Flac => "flac",
            AudioFormat::Wav => "wav",
            AudioFormat::Opus => "opus",
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct YtDlpProgress {
    pub percent: f32,
    pub speed: String,
    pub eta: String,
    pub is_finished: bool,
}

/// Checks if yt-dlp is available in PATH and returns its version string.
pub async fn check_installed() -> Result<String, String> {
    let output = Command::new("yt-dlp")
        .arg("--version")
        .output()
        .await
        .map_err(|e| format!("yt-dlp binary not found: {}", e))?;

    if output.status.success() {
        let ver = String::from_utf8_lossy(&output.stdout).trim().to_string();
        Ok(ver)
    } else {
        Err("yt-dlp exited with non-zero status".to_string())
    }
}

/// Parses a single line from yt-dlp stdout into a structured progress state.
pub fn parse_progress_line(line: &str) -> Option<YtDlpProgress> {
    // Example: [download]  42.5% of   15.20MiB at    3.15MiB/s ETA 00:03
    if !line.contains("[download]") {
        if line.contains("100%") || line.contains("Destination:") {
            return Some(YtDlpProgress {
                percent: 100.0,
                speed: "Done".to_string(),
                eta: "00:00".to_string(),
                is_finished: true,
            });
        }
        return None;
    }

    let parts: Vec<&str> = line.split_whitespace().collect();
    let mut percent = 0.0f32;
    let mut speed = String::new();
    let mut eta = String::new();

    for (i, &p) in parts.iter().enumerate() {
        if p.ends_with('%') {
            if let Ok(val) = p.trim_end_matches('%').parse::<f32>() {
                percent = val;
            }
        }
        if p == "at" && i + 1 < parts.len() {
            speed = parts[i + 1].to_string();
        }
        if p == "ETA" && i + 1 < parts.len() {
            eta = parts[i + 1].to_string();
        }
    }

    Some(YtDlpProgress {
        percent,
        speed,
        eta,
        is_finished: percent >= 99.9,
    })
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AlbumInfo {
    pub title: String,
    pub artist: String,
    pub track_count: usize,
    pub tracks: Vec<AlbumTrack>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AlbumTrack {
    pub index: usize,
    pub title: String,
    pub artist: String,
    pub url: String,
    pub duration_secs: Option<u64>,
}

/// Checks if a given URL is a playlist or album.
pub fn is_playlist_or_album(url: &str) -> bool {
    let lower = url.to_lowercase();
    lower.contains("playlist?list=")
        || lower.contains("&list=")
        || lower.contains("?list=")
        || lower.contains("/browse/vl")
        || lower.contains("/album/")
}

/// Sanitizes a string for safe use in file and directory paths.
pub fn sanitize_filename(name: &str) -> String {
    let invalid = ['/', '\\', ':', '*', '?', '"', '<', '>', '|'];
    let mut clean: String = name.chars().filter(|c| !invalid.contains(c)).collect();
    clean = clean.trim().to_string();
    if clean.is_empty() {
        "Untitled".to_string()
    } else {
        clean
    }
}

/// Constructs a hierarchical path: `<base_dir>/<Artist>/<Album>/<TrackNumber:02> - <Title>.<ext>`
pub fn get_album_track_path<P: AsRef<Path>>(
    base_dir: P,
    artist: &str,
    album: &str,
    track_num: usize,
    title: &str,
    format: AudioFormat,
) -> std::path::PathBuf {
    let clean_artist = sanitize_filename(artist);
    let clean_album = sanitize_filename(album);
    let clean_title = sanitize_filename(title);
    base_dir
        .as_ref()
        .join(clean_artist)
        .join(clean_album)
        .join(format!("{:02} - {}.{}", track_num, clean_title, format.as_str()))
}

/// Expands a YouTube Music album or playlist into individual track metadata using yt-dlp.
pub async fn expand_album_tracks(url: &str) -> Result<AlbumInfo, String> {
    let output = Command::new("yt-dlp")
        .arg("--flat-playlist")
        .arg("-J")
        .arg(url)
        .output()
        .await
        .map_err(|e| format!("Failed to execute yt-dlp: {}", e))?;

    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("yt-dlp album expansion failed: {}", err.trim()));
    }

    let json: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|e| format!("Failed to parse playlist JSON: {}", e))?;

    let album_title = json
        .get("title")
        .or_else(|| json.get("playlist_title"))
        .and_then(|v| v.as_str())
        .unwrap_or("Unknown Album")
        .to_string();

    let album_artist = json
        .get("uploader")
        .or_else(|| json.get("channel"))
        .or_else(|| json.get("artist"))
        .and_then(|v| v.as_str())
        .unwrap_or("Unknown Artist")
        .to_string();

    let mut tracks = Vec::new();
    if let Some(entries) = json.get("entries").and_then(|v| v.as_array()) {
        for (idx, entry) in entries.iter().enumerate() {
            let track_title = entry
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("Unknown Track")
                .to_string();

            let track_url = if let Some(u) = entry.get("url").and_then(|v| v.as_str()) {
                if u.starts_with("http") {
                    u.to_string()
                } else {
                    format!("https://www.youtube.com/watch?v={}", u)
                }
            } else if let Some(id) = entry.get("id").and_then(|v| v.as_str()) {
                format!("https://www.youtube.com/watch?v={}", id)
            } else {
                continue;
            };

            let track_artist = entry
                .get("artist")
                .or_else(|| entry.get("uploader"))
                .and_then(|v| v.as_str())
                .unwrap_or(&album_artist)
                .to_string();

            let duration_secs = entry.get("duration").and_then(|v| v.as_u64());

            tracks.push(AlbumTrack {
                index: idx + 1,
                title: track_title,
                artist: track_artist,
                url: track_url,
                duration_secs,
            });
        }
    }

    let track_count = tracks.len();
    Ok(AlbumInfo {
        title: album_title,
        artist: album_artist,
        track_count,
        tracks,
    })
}

/// Downloads audio from `url` into `output_dir` using the chosen `format`.
pub async fn download_audio<P: AsRef<Path>>(
    url: &str,
    output_dir: P,
    format: AudioFormat,
) -> Result<String, String> {
    let out_template = format!("{}/%(title)s.%(ext)s", output_dir.as_ref().display());
    download_with_template(url, &out_template, format).await
}

/// Downloads audio from `url` targeting an explicit output file path.
pub async fn download_audio_to_path<P: AsRef<Path>>(
    url: &str,
    target_path: P,
    format: AudioFormat,
) -> Result<String, String> {
    if let Some(parent) = target_path.as_ref().parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let out_template = target_path.as_ref().to_string_lossy().to_string();
    download_with_template(url, &out_template, format).await
}

async fn download_with_template(
    url: &str,
    out_template: &str,
    format: AudioFormat,
) -> Result<String, String> {
    let mut cmd = Command::new("yt-dlp");
    cmd.arg("-x")
        .arg("--audio-format")
        .arg(format.yt_audio_format())
        .arg("--audio-quality")
        .arg("0")
        .arg("--embed-metadata")
        .arg("-o")
        .arg(out_template)
        .arg(url)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start yt-dlp: {}", e))?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Failed to capture yt-dlp stdout".to_string())?;

    let mut reader = BufReader::new(stdout).lines();
    let mut last_destination = String::new();

    while let Ok(Some(line)) = reader.next_line().await {
        if line.contains("Destination: ") {
            if let Some(dest) = line.split("Destination: ").nth(1) {
                last_destination = dest.trim().to_string();
            }
        }
    }

    let status = child
        .wait()
        .await
        .map_err(|e| format!("Failed to wait for yt-dlp: {}", e))?;

    if status.success() {
        if last_destination.is_empty() {
            Ok(out_template.to_string())
        } else {
            Ok(last_destination)
        }
    } else {
        Err("yt-dlp download failed with non-zero status".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_progress_line() {
        let line = "[download]  45.0% of 10.00MiB at 2.50MiB/s ETA 00:04";
        let prog = parse_progress_line(line);
        assert!(prog.is_some());
        let p = prog.unwrap();
        assert_eq!(p.percent, 45.0);
        assert_eq!(p.speed, "2.50MiB/s");
        assert_eq!(p.eta, "00:04");
        assert!(!p.is_finished);
    }

    #[test]
    fn test_parse_finished_line() {
        let line = "[download] 100% of 10.00MiB in 00:02";
        let prog = parse_progress_line(line);
        assert!(prog.is_some());
        let p = prog.unwrap();
        assert_eq!(p.percent, 100.0);
        assert!(p.is_finished);
    }

    #[test]
    fn test_is_playlist_or_album() {
        assert!(is_playlist_or_album("https://music.youtube.com/playlist?list=OLAK5uy_foo"));
        assert!(is_playlist_or_album("https://www.youtube.com/playlist?list=PL123456789"));
        assert!(is_playlist_or_album("https://music.youtube.com/browse/VLOLAK5uy_bar"));
        assert!(!is_playlist_or_album("https://www.youtube.com/watch?v=dQw4w9WgXcQ"));
    }

    #[test]
    fn test_sanitize_filename() {
        assert_eq!(sanitize_filename("Radiohead: OK Computer / 1997?"), "Radiohead OK Computer  1997");
        assert_eq!(sanitize_filename(""), "Untitled");
    }

    #[test]
    fn test_get_album_track_path() {
        let path = get_album_track_path(
            "/tmp/Music",
            "Radiohead",
            "OK Computer",
            1,
            "Airbag",
            AudioFormat::Mp3,
        );
        assert_eq!(
            path.to_str().unwrap(),
            "/tmp/Music/Radiohead/OK Computer/01 - Airbag.mp3"
        );
    }

    #[test]
    fn test_audio_formats() {
        assert_eq!(AudioFormat::Mp3.as_str(), "mp3");
        assert_eq!(AudioFormat::Aac.as_str(), "m4a");
        assert_eq!(AudioFormat::Flac.as_str(), "flac");
        assert_eq!(AudioFormat::Wav.as_str(), "wav");
        assert_eq!(AudioFormat::Opus.as_str(), "opus");

        assert_eq!(AudioFormat::Aac.yt_audio_format(), "aac");
    }
}
