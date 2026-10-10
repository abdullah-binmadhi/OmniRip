//! Asynchronous yt-dlp Audio Downloader for OmniRip.
//! Wraps system yt-dlp to download high-resolution audio (FLAC / OPUS) with real-time progress parsing.

use std::path::Path;
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AudioFormat {
    Flac,
    Opus,
    Mp3,
}

impl AudioFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            AudioFormat::Flac => "flac",
            AudioFormat::Opus => "opus",
            AudioFormat::Mp3 => "mp3",
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

/// Downloads audio from `url` into `output_dir` using the chosen `format`.
pub async fn download_audio<P: AsRef<Path>>(
    url: &str,
    output_dir: P,
    format: AudioFormat,
) -> Result<String, String> {
    let out_template = format!("{}/%(title)s.%(ext)s", output_dir.as_ref().display());

    let mut cmd = Command::new("yt-dlp");
    cmd.arg("-x")
        .arg("--audio-format")
        .arg(format.as_str())
        .arg("--audio-quality")
        .arg("0")
        .arg("--embed-metadata")
        .arg("-o")
        .arg(&out_template)
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
        Ok(last_destination)
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
}
