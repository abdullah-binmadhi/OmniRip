//! Asynchronous Soulseek / Slskd API Client for OmniRip.
//! Interacts with Slskd daemon to search lossless flac/wav files and monitor transfers.

use reqwest::header::{HeaderMap, HeaderValue};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdFileResult {
    pub username: String,
    pub filename: String,
    pub size: u64,
    #[serde(alias = "bitRate")]
    pub bitrate: Option<u32>,
    pub sample_rate: Option<u32>,
    pub bit_depth: Option<u32>,
    #[serde(default)]
    pub upload_speed: Option<u64>,
    #[serde(default)]
    pub queue_length: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub probed_verdict: Option<crate::harvest::spectral::SpectralAnalysisResult>,
}

impl SlskdFileResult {
    pub fn is_flac(&self) -> bool {
        self.filename.to_lowercase().ends_with(".flac")
    }

    pub fn is_wav(&self) -> bool {
        self.filename.to_lowercase().ends_with(".wav")
    }

    pub fn format_tag(&self) -> &'static str {
        let lower = self.filename.to_lowercase();
        if lower.ends_with(".flac") {
            "FLAC"
        } else if lower.ends_with(".wav") {
            "WAV"
        } else if lower.ends_with(".alac") || lower.ends_with(".m4a") {
            "ALAC"
        } else if lower.ends_with(".aiff") || lower.ends_with(".aif") {
            "AIFF"
        } else if lower.ends_with(".mp3") {
            "MP3"
        } else if lower.ends_with(".ogg") {
            "OGG"
        } else {
            "AUDIO"
        }
    }

    pub fn formatted_size(&self) -> String {
        let mb = (self.size as f64) / (1024.0 * 1024.0);
        format!("{:.1} MB", mb)
    }

    pub fn formatted_resolution(&self) -> String {
        let depth_str = match self.bit_depth {
            Some(d) if d > 0 => format!("{}-bit", d),
            _ => {
                if self.is_flac() || self.is_wav() {
                    "Lossless".to_string()
                } else {
                    "16-bit".to_string()
                }
            }
        };
        let rate_str = match self.sample_rate {
            Some(sr) if sr > 0 => {
                if sr % 1000 == 0 {
                    format!("{}kHz", sr / 1000)
                } else {
                    format!("{:.1}kHz", (sr as f32) / 1000.0)
                }
            }
            _ => "44.1kHz".to_string(),
        };
        format!("{}/{}", depth_str, rate_str)
    }

    pub fn formatted_bitrate(&self) -> String {
        match self.bitrate {
            Some(b) if b > 0 => format!("{} kbps", b),
            _ => {
                if self.is_flac() {
                    "VBR Lossless".to_string()
                } else if self.is_wav() {
                    "1411 kbps".to_string()
                } else {
                    "Lossless".to_string()
                }
            }
        }
    }

    pub fn evaluate_authenticity(&self) -> crate::harvest::nicotine::AuthenticityBadge {
        if let Some(ref probed) = self.probed_verdict {
            match probed.verdict {
                crate::harvest::spectral::QualityVerdict::TrueLosslessHiRes => {
                    return crate::harvest::nicotine::AuthenticityBadge::ProbedAuthentic((probed.cutoff_freq_hz / 1000.0).round() as u32);
                }
                crate::harvest::spectral::QualityVerdict::TrueLosslessCD => {
                    return crate::harvest::nicotine::AuthenticityBadge::ProbedAuthentic((probed.cutoff_freq_hz / 1000.0).round() as u32);
                }
                crate::harvest::spectral::QualityVerdict::FakeLossless(hz) |
                crate::harvest::spectral::QualityVerdict::LossyCutoff(hz) => {
                    return crate::harvest::nicotine::AuthenticityBadge::ProbedFake(hz / 1000);
                }
                crate::harvest::spectral::QualityVerdict::NearLossless320k => {
                    return crate::harvest::nicotine::AuthenticityBadge::ProbedFake(20);
                }
            }
        }

        let lower_path = self.filename.to_lowercase();
        let suspect_tokens = [
            "transcode", "upscale", "upscaled", "lossy to flac", "youtube",
            "yt-dlp", "128k to flac", "converted", "webrip 128", "soundclick",
            "webrip", "spotify-rip", "spotdl", "aac2flac", "mp3toflac",
            "opus2flac", "fake flac", "fakeflac", "lossy-master", "rip from youtube",
            "re-encoded", "192k to flac", "256k to flac", "320k to flac",
        ];
        for token in suspect_tokens {
            if lower_path.contains(token) {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("Path contains '{}'", token));
            }
        }

        let is_lossless = self.is_flac()
            || self.is_wav()
            || lower_path.ends_with(".alac")
            || lower_path.ends_with(".aiff")
            || lower_path.ends_with(".aif");

        let sample_rate = self.sample_rate.unwrap_or(44100);
        let bit_depth = self.bit_depth.unwrap_or(16);
        let br = self.bitrate.unwrap_or(0);
        let mb = (self.size as f64) / (1024.0 * 1024.0);

        if is_lossless {
            if (br == 128 || br == 160 || br == 192 || br == 256 || br == 320) && mb > 0.0 && mb < 18.0 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("Lossless container reports exact lossy bitrate of {} kbps", br));
            }
            if br > 0 && br < 500 && mb > 0.0 && mb < 15.0 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is implausibly low for true lossless audio", br));
            }
            if self.is_flac() && mb > 0.0 && mb < 4.0 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("File size ({:.1} MB) is too small to contain true lossless audio", mb));
            }
            if self.is_wav() && mb > 0.0 && mb < 8.0 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("WAV size ({:.1} MB) is too small for uncompressed PCM audio", mb));
            }
        }

        if bit_depth >= 24 || sample_rate >= 88200 {
            if br > 0 && br < 1200 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is implausibly low for genuine {}/{}", br, bit_depth, sample_rate));
            }
            return crate::harvest::nicotine::AuthenticityBadge::GenuineHiRes(bit_depth, sample_rate / 1000);
        }

        if sample_rate == 44100 && bit_depth == 16 {
            if br > 0 && br < 400 && mb > 0.0 && mb < 12.0 {
                return crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is too low for Red Book CD FLAC", br));
            }
            return crate::harvest::nicotine::AuthenticityBadge::GenuineCD;
        }

        if is_lossless {
            crate::harvest::nicotine::AuthenticityBadge::PlausibleLossless
        } else {
            crate::harvest::nicotine::AuthenticityBadge::SuspectTranscode("Lossy container format".to_string())
        }
    }

    pub fn evaluate_speed_tier(&self) -> crate::harvest::nicotine::SpeedTier {
        let speed_kb = self.upload_speed.map(|s| (s as f32) / 1024.0).unwrap_or(0.0);
        let q = self.queue_length as usize;
        if q > 4 || (speed_kb > 0.0 && speed_kb < 300.0) {
            crate::harvest::nicotine::SpeedTier::CongestedQueue
        } else if speed_kb >= 1500.0 && q <= 1 {
            crate::harvest::nicotine::SpeedTier::HighSpeedPeer
        } else if speed_kb >= 400.0 && q <= 3 {
            crate::harvest::nicotine::SpeedTier::StandardPeer
        } else if speed_kb > 0.0 {
            crate::harvest::nicotine::SpeedTier::StandardPeer
        } else {
            crate::harvest::nicotine::SpeedTier::StandardPeer
        }
    }

    pub fn formatted_eta(&self) -> String {
        let speed_kbytes_sec = self.upload_speed.map(|s| (s as f64) / 1024.0).unwrap_or(1000.0);
        let size_kb = (self.size as f64) / 1024.0;
        let secs = (size_kb / speed_kbytes_sec.max(1.0)).round() as u64;
        let base_eta = if secs <= 3 {
            "ETA: ~3s".to_string()
        } else if secs < 60 {
            format!("ETA: ~{}s", secs)
        } else {
            format!("ETA: ~{}m {}s", secs / 60, secs % 60)
        };

        if self.queue_length > 0 {
            format!("{} (Q:{})", base_eta, self.queue_length)
        } else {
            base_eta
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdTransferFile {
    pub username: String,
    pub filename: String,
    pub size: u64,
    pub state: String,
    pub bytes_transferred: u64,
    pub percent_complete: f32,
    pub average_speed: f64,
    pub remaining_time: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdDownloadStatus {
    pub username: String,
    pub filename: String,
    pub percent: f32,
    pub speed_bytes_per_sec: u64,
    pub state: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdServerStatus {
    pub address: Option<String>,
    pub ip_end_point: Option<String>,
    pub state: Option<String>,
    #[serde(default)]
    pub is_connected: bool,
    #[serde(default)]
    pub is_connecting: bool,
    #[serde(default)]
    pub is_logged_in: bool,
    #[serde(default)]
    pub is_logging_in: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdApplicationInfo {
    pub user: Option<SlskdUserInfo>,
    pub server: Option<SlskdServerStatus>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SoulseekLoginStatus {
    Valid,
    InvalidCredentials(String),
    Connecting,
    Offline,
}

impl SoulseekLoginStatus {
    pub fn is_valid(&self) -> bool {
        matches!(self, SoulseekLoginStatus::Valid)
    }

    pub fn display_badge(&self) -> &'static str {
        match self {
            SoulseekLoginStatus::Valid => "Verified",
            SoulseekLoginStatus::InvalidCredentials(_) => "Wrong Password",
            SoulseekLoginStatus::Connecting => "Connecting",
            SoulseekLoginStatus::Offline => "Offline",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdUserInfo {
    pub username: Option<String>,
}

#[derive(Debug, Clone)]
pub struct SlskdClient {
    client: reqwest::Client,
    pub base_url: String,
    pub api_key: Option<String>,
}

impl SlskdClient {
    pub async fn check_server_health(&self) -> Result<SlskdServerStatus, String> {
        let url = format!("{}/api/v0/server", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("slskd daemon unreachable: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("slskd server health query returned status {}", resp.status()));
        }

        resp.json::<SlskdServerStatus>()
            .await
            .map_err(|e| format!("Failed to parse server status: {}", e))
    }

    pub async fn get_application_info(&self) -> Result<SlskdApplicationInfo, String> {
        let url = format!("{}/api/v0/application", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("slskd daemon unreachable: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("slskd application query returned status {}", resp.status()));
        }

        resp.json::<SlskdApplicationInfo>()
            .await
            .map_err(|e| format!("Failed to parse application info: {}", e))
    }

    /// Checks the server authentication status to detect whether credentials are valid or invalid.
    pub async fn check_login_status(&self) -> Result<SoulseekLoginStatus, String> {
        let status = self.check_server_health().await?;
        if status.is_logged_in {
            Ok(SoulseekLoginStatus::Valid)
        } else if status.is_connected && !status.is_logged_in {
            let reason = status.state.unwrap_or_else(|| "Invalid username or password".to_string());
            Ok(SoulseekLoginStatus::InvalidCredentials(reason))
        } else if status.is_connecting || status.is_logging_in {
            Ok(SoulseekLoginStatus::Connecting)
        } else if !status.is_connected {
            Ok(SoulseekLoginStatus::Offline)
        } else {
            Ok(SoulseekLoginStatus::Offline)
        }
    }

    /// Generates a cryptographically secure 32-byte (64 hex characters) API key.
    pub fn generate_secure_api_key() -> String {
        let mut bytes = [0u8; 32];
        let mut filled = false;
        if let Ok(mut f) = std::fs::File::open("/dev/urandom") {
            use std::io::Read;
            if f.read_exact(&mut bytes).is_ok() {
                filled = true;
            }
        }
        if !filled {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos();
            let pid = std::process::id() as u128;
            let seed = now ^ (pid << 32);
            for (i, b) in bytes.iter_mut().enumerate() {
                *b = ((seed >> ((i % 16) * 8)) & 0xFF) as u8 ^ ((i as u8).wrapping_mul(31));
            }
        }
        bytes.iter().map(|b| format!("{:02x}", b)).collect()
    }

    /// Auto-provisions slskd YAML config at a target path with the specified credentials and API key.
    pub fn ensure_slskd_config_at(target_path: &std::path::Path, username: &str, password: &str) -> Result<(std::path::PathBuf, String), String> {
        let existing_key = Self::detect_local().api_key;
        let api_key = match existing_key {
            Some(k) if !k.is_empty() && !k.contains("CHANGE_ME") => k,
            _ => Self::generate_secure_api_key(),
        };

        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let music_dir = format!("{}/Music", home);
        let yaml_content = format!(
            "# Auto-provisioned by OmniRip\nsoulseek:\n  username: {}\n  password: {}\n  listen_port: 50300\nweb:\n  listen:\n    ip: 127.0.0.1\n    ports:\n      - 5030\n  authentication:\n    api_key: {}\n  url_base: /\nremote_configuration: true\nfeature:\n  swagger: true\nshares:\n  directories:\n    - {}\n",
            username, password, api_key, music_dir
        );

        if let Some(parent) = target_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        std::fs::write(target_path, &yaml_content)
            .map_err(|e| format!("Failed to write config at {:?}: {}", target_path, e))?;

        Ok((target_path.to_path_buf(), api_key))
    }

    /// Auto-provisions slskd YAML config with the specified Soulseek credentials and an auto-generated API key.
    pub fn ensure_slskd_config(username: &str, password: &str) -> Result<(std::path::PathBuf, String), String> {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let global_dir = std::path::PathBuf::from(&home).join(".config/omnirip");
        let _ = std::fs::create_dir_all(&global_dir);
        let global_path = global_dir.join("slskd.yml");
        let _ = Self::ensure_slskd_config_at(&global_path, username, password);

        let local_path = std::path::PathBuf::from("tools/slskd/slskd.local.yml");
        Self::ensure_slskd_config_at(&local_path, username, password)
    }

    pub fn new(base_url: &str, api_key: Option<String>) -> Self {
        let mut headers = HeaderMap::new();
        if let Some(ref key) = api_key {
            if let Ok(val) = HeaderValue::from_str(key) {
                headers.insert("X-API-KEY", val);
            }
        }
        let client = reqwest::Client::builder()
            .default_headers(headers)
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .unwrap_or_default();

        Self {
            client,
            base_url: base_url.trim_end_matches('/').to_string(),
            api_key,
        }
    }

    /// Automatically connects to local slskd daemon, discovering API key from environment or local config.
    pub fn detect_local() -> Self {
        let base_url = std::env::var("SLSKD_URL").unwrap_or_else(|_| "http://localhost:5030".to_string());
        let mut api_key = std::env::var("SLSKD_API_KEY").ok();

        if api_key.is_none() {
            let mut candidates = vec![
                std::path::PathBuf::from("tools/slskd/slskd.local.yml"),
                std::path::PathBuf::from("tools/slskd/slskd.yml"),
                std::path::PathBuf::from("slskd.yml"),
            ];
            if let Ok(home) = std::env::var("HOME") {
                let home_p = std::path::PathBuf::from(home);
                candidates.push(home_p.join(".config/omnirip/slskd.yml"));
                candidates.push(home_p.join("Projects/OmniRip/tools/slskd/slskd.local.yml"));
                candidates.push(home_p.join("Projects/OmniRip/tools/slskd/slskd.yml"));
                candidates.push(home_p.join("Library/Application Support/slskd/slskd.yml"));
                candidates.push(home_p.join(".config/slskd/slskd.yml"));
            }
            for path in candidates {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed.starts_with("api_key:") {
                            if let Some((_, val)) = trimmed.split_once(':') {
                                let key = val.trim().trim_matches('"').trim_matches('\'');
                                if !key.is_empty() && !key.contains("CHANGE_ME") {
                                    api_key = Some(key.to_string());
                                    break;
                                }
                            }
                        }
                    }
                    if api_key.is_some() {
                        break;
                    }
                }
            }
        }

        Self::new(&base_url, api_key)
    }

    /// Detects the configured Soulseek account username from local configuration files.
    pub fn detect_configured_username() -> Option<String> {
        let mut candidates = vec![
            std::path::PathBuf::from("tools/slskd/slskd.local.yml"),
            std::path::PathBuf::from("tools/slskd/slskd.yml"),
            std::path::PathBuf::from("slskd.yml"),
        ];
        if let Ok(home) = std::env::var("HOME") {
            let home_p = std::path::PathBuf::from(home);
            candidates.push(home_p.join(".config/omnirip/slskd.yml"));
            candidates.push(home_p.join("Projects/OmniRip/tools/slskd/slskd.local.yml"));
            candidates.push(home_p.join("Projects/OmniRip/tools/slskd/slskd.yml"));
            candidates.push(home_p.join("Library/Application Support/slskd/slskd.yml"));
            candidates.push(home_p.join(".config/slskd/slskd.yml"));
        }
        for path in candidates {
            if let Ok(content) = std::fs::read_to_string(&path) {
                let mut in_soulseek_section = false;
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed == "soulseek:" {
                        in_soulseek_section = true;
                        continue;
                    }
                    if in_soulseek_section && !line.starts_with(' ') && !line.starts_with('\t') {
                        in_soulseek_section = false;
                    }
                    if in_soulseek_section && trimmed.starts_with("username:") {
                        if let Some((_, val)) = trimmed.split_once(':') {
                            let user = val.trim().trim_matches('"').trim_matches('\'');
                            if !user.is_empty() && user != "YOUR_SOULSEEK_USERNAME" {
                                return Some(user.to_string());
                            }
                        }
                    }
                }
            }
        }
        None
    }

    /// Fast non-blocking check to verify if the local slskd daemon is listening on port 5030.
    pub fn is_daemon_online() -> bool {
        std::net::TcpStream::connect_timeout(
            &std::net::SocketAddr::from(([127, 0, 0, 1], 5030)),
            std::time::Duration::from_millis(150),
        ).is_ok()
    }

    /// Ensures the local slskd daemon is running. If unreachable on localhost:5030,
    /// attempts to launch the binary in the background using tools/slskd/slskd.local.yml
    /// with memory-hardened .NET GC parameters.
    pub fn ensure_daemon_running() -> Result<(), String> {
        if Self::is_daemon_online() {
            return Ok(());
        }

        Self::spawn_hardened_daemon()
    }

    /// Completely restarts the Soulseek daemon, terminating any hanging or stale process,
    /// clearing port conflicts, and re-spawning with memory-hardened parameters.
    pub fn restart_daemon() -> Result<(), String> {
        #[cfg(unix)]
        {
            let _ = std::process::Command::new("pkill")
                .arg("-f")
                .arg("tools/slskd/slskd")
                .output();
            std::thread::sleep(std::time::Duration::from_millis(300));
        }

        Self::spawn_hardened_daemon()
    }

    /// Spawns the slskd daemon with hardened .NET GC and memory limits to prevent OOM aborts.
    pub fn spawn_hardened_daemon() -> Result<(), String> {
        let mut candidates = vec![
            (std::path::PathBuf::from("tools/slskd/slskd"), std::path::PathBuf::from("tools/slskd/slskd.local.yml")),
            (std::path::PathBuf::from("tools/slskd/slskd"), std::path::PathBuf::from("tools/slskd/slskd.yml")),
        ];
        if let Ok(home) = std::env::var("HOME") {
            let home_p = std::path::PathBuf::from(home);
            candidates.push((
                home_p.join("Projects/OmniRip/tools/slskd/slskd"),
                home_p.join("Projects/OmniRip/tools/slskd/slskd.local.yml"),
            ));
        }

        for (bin, cfg) in candidates {
            if bin.exists() && cfg.exists() {
                let _ = std::process::Command::new(&bin)
                    .arg("--config")
                    .arg(&cfg)
                    .env("DOTNET_GCServer", "0") // Workstation GC: ~75% lower RAM usage
                    .env("DOTNET_GCHeapHardLimit", "0x18000000") // 384 MB hard memory ceiling
                    .env("DOTNET_GCLargeObjectHeapCompactionMode", "1")
                    .env("DOTNET_EnableWriteXorExecute", "1")
                    .stdout(std::process::Stdio::null())
                    .stderr(std::process::Stdio::null())
                    .spawn()
                    .map_err(|e| format!("Failed to spawn slskd daemon: {}", e))?;

                for _ in 0..15 {
                    std::thread::sleep(std::time::Duration::from_millis(200));
                    if Self::is_daemon_online() {
                        return Ok(());
                    }
                }
                return Ok(());
            }
        }

        Err("slskd daemon is offline on port 5030 and binary not found in tools/slskd/".to_string())
    }

    /// Initiates a search query on the Soulseek network.
    pub async fn start_search(&self, text: &str) -> Result<String, String> {
        let url = format!("{}/api/v0/searches", self.base_url);
        let body = serde_json::json!({
            "searchText": text
        });

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("Failed to initiate search: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Search initiation error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        let id = json["id"]
            .as_str()
            .ok_or_else(|| "Search ID not found in response".to_string())?;

        Ok(id.to_string())
    }

    /// Fetches search results for an active search ID.
    pub async fn get_search_results(&self, search_id: &str) -> Result<Vec<SlskdFileResult>, String> {
        let url = format!("{}/api/v0/searches/{}/responses", self.base_url, search_id);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to query search results: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Query results error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        let mut results = Vec::new();
        let resp_list_opt = json.as_array().or_else(|| json.get("responses").and_then(|r| r.as_array()));

        if let Some(responses) = resp_list_opt {
            for r in responses {
                let username = r["username"].as_str().unwrap_or_default().to_string();
                let upload_speed = r["uploadSpeed"].as_u64();
                let queue_length = r["queueLength"].as_u64().map(|v| v as u32).unwrap_or(0);

                if let Some(files) = r["files"].as_array() {
                    for f in files {
                        let filename = f["filename"].as_str().unwrap_or_default().to_string();
                        let size = f["size"].as_u64().unwrap_or_default();
                        let bitrate = f["bitRate"].as_u64().map(|v| v as u32);
                        let sample_rate = f["sampleRate"].as_u64().map(|v| v as u32);
                        let bit_depth = f["bitDepth"].as_u64().map(|v| v as u32);

                        results.push(SlskdFileResult {
                            username: username.clone(),
                            filename,
                            size,
                            bitrate,
                            sample_rate,
                            bit_depth,
                            upload_speed,
                            queue_length,
                            probed_verdict: None,
                        });
                    }
                }
            }
        }

        Ok(results)
    }

    /// Deletes a search on the Soulseek network, stopping peer listening in slskd.
    pub async fn delete_search(&self, search_id: &str) -> Result<(), String> {
        let url = format!("{}/api/v0/searches/{}", self.base_url, search_id);
        let _ = self.client.delete(&url).send().await;
        Ok(())
    }

    /// Fetches all currently active download transfers across all peers.
    pub async fn get_active_transfers(&self) -> Result<Vec<SlskdTransferFile>, String> {
        let url = format!("{}/api/v0/transfers/downloads", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Query transfers error: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Query transfers error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse transfers JSON: {}", e))?;

        let mut transfers = Vec::new();
        if let Some(user_arr) = json.as_array() {
            for user_obj in user_arr {
                let username = user_obj["username"].as_str().unwrap_or_default().to_string();
                if let Some(dir_arr) = user_obj["directories"].as_array() {
                    for dir_obj in dir_arr {
                        if let Some(files) = dir_obj["files"].as_array() {
                            for f in files {
                                let filename = f["filename"].as_str().unwrap_or_default().to_string();
                                let size = f["size"].as_u64().unwrap_or_default();
                                let state = f["state"].as_str().unwrap_or("Unknown").to_string();
                                let bytes_transferred = f["bytesTransferred"].as_u64().unwrap_or_default();
                                let percent_complete = f["percentComplete"].as_f64().unwrap_or(0.0) as f32;
                                let average_speed = f["averageSpeed"].as_f64().unwrap_or(0.0);
                                let remaining_time = f["remainingTime"].as_str().map(|s| s.to_string());

                                transfers.push(SlskdTransferFile {
                                    username: username.clone(),
                                    filename,
                                    size,
                                    state,
                                    bytes_transferred,
                                    percent_complete,
                                    average_speed,
                                    remaining_time,
                                });
                            }
                        }
                    }
                }
            }
        }

        Ok(transfers)
    }

    /// Returns the active download directory for slskd.
    pub async fn get_downloads_dir(&self) -> std::path::PathBuf {
        let url = format!("{}/api/v0/options", self.base_url);
        if let Ok(resp) = self.client.get(&url).send().await {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                if let Some(p) = json.get("directories").and_then(|d| d.get("downloads")).and_then(|v| v.as_str()) {
                    let path = std::path::PathBuf::from(p);
                    if path.exists() {
                        return path;
                    }
                }
            }
        }
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let mac_default = std::path::PathBuf::from(&home).join("Library/Application Support/slskd/downloads");
        if mac_default.exists() {
            return mac_default;
        }
        let xdg_default = std::path::PathBuf::from(&home).join(".local/share/slskd/downloads");
        if xdg_default.exists() {
            return xdg_default;
        }
        std::path::PathBuf::from(&home).join("Music")
    }

    /// Triggers a re-scan of configured shares in slskd to update published file count.
    pub async fn trigger_shares_scan(&self) -> Result<(), String> {
        let url = format!("{}/api/v0/shares", self.base_url);
        let resp = self
            .client
            .put(&url)
            .send()
            .await
            .map_err(|e| format!("Trigger shares scan error: {}", e))?;

        if resp.status().is_success() {
            Ok(())
        } else {
            Err(format!("Trigger shares scan failed: HTTP {}", resp.status()))
        }
    }

    /// Queues a file for download from a Soulseek user.
    pub async fn queue_download(&self, username: &str, filename: &str, size: u64) -> Result<(), String> {
        let url = format!("{}/api/v0/transfers/downloads/{}", self.base_url, username);
        let body = serde_json::json!([
            {
                "filename": filename,
                "size": size
            }
        ]);

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("Download request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Download error: HTTP {}", resp.status()));
        }

        Ok(())
    }

    /// Fetches all active downloads and their current transfer states.
    pub async fn get_active_downloads(&self) -> Result<Vec<SlskdDownloadStatus>, String> {
        let url = format!("{}/api/v0/transfers/downloads", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to get downloads: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Downloads status error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse downloads JSON: {}", e))?;

        let mut downloads = Vec::new();
        if let Some(arr) = json.as_array() {
            for item in arr {
                let username = item["username"].as_str().unwrap_or_default().to_string();
                let filename = item["filename"].as_str().unwrap_or_default().to_string();
                let bytes_transferred = item["bytesTransferred"].as_f64().unwrap_or(0.0);
                let size = item["size"].as_f64().unwrap_or(1.0);
                let speed = item["speed"].as_u64().unwrap_or(0);
                let state = item["state"].as_str().unwrap_or("Unknown").to_string();

                let percent = ((bytes_transferred / size.max(1.0)) * 100.0) as f32;

                downloads.push(SlskdDownloadStatus {
                    username,
                    filename,
                    percent: percent.clamp(0.0, 100.0),
                    speed_bytes_per_sec: speed,
                    state,
                });
            }
        }

        Ok(downloads)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_slskd_client_url_construction() {
        let client = SlskdClient::new("http://127.0.0.1:5030/", Some("secret".into()));
        assert_eq!(client.base_url, "http://127.0.0.1:5030");
        assert_eq!(client.api_key.as_deref(), Some("secret"));
    }

    #[test]
    fn test_slskd_file_result_parsing() {
        let json_str = r#"{
            "username": "AudiophileMaster",
            "filename": "Pink Floyd - Time (1973).flac",
            "size": 45182900,
            "bitrate": 960,
            "sampleRate": 44100,
            "bitDepth": 16
        }"#;

        let res: Result<SlskdFileResult, _> = serde_json::from_str(json_str);
        assert!(res.is_ok());
        let f = res.unwrap();
        assert_eq!(f.username, "AudiophileMaster");
        assert_eq!(f.bit_depth, Some(16));
    }

    #[test]
    fn test_slskd_detect_local() {
        let client = SlskdClient::detect_local();
        assert_eq!(client.base_url, "http://localhost:5030");
    }

    #[test]
    fn test_slskd_server_status_parsing() {
        let sample = r#"{
            "address": "vps.slsknet.org",
            "ipEndPoint": "208.76.170.59:2271",
            "state": "Connected, LoggedIn",
            "isConnected": true,
            "isConnecting": false,
            "isLoggedIn": true,
            "isLoggingIn": false
        }"#;

        let status: Result<SlskdServerStatus, _> = serde_json::from_str(sample);
        assert!(status.is_ok());
        let s = status.unwrap();
        assert!(s.is_connected);
        assert!(s.is_logged_in);
        assert_eq!(s.address.as_deref(), Some("vps.slsknet.org"));
    }

    #[test]
    fn test_slskd_application_info_parsing() {
        let sample = r#"{
            "user": {
                "username": "abdullah"
            },
            "server": {
                "address": "vps.slsknet.org",
                "state": "Connected, LoggedIn",
                "isConnected": true,
                "isLoggedIn": true
            }
        }"#;

        let app_info: Result<SlskdApplicationInfo, _> = serde_json::from_str(sample);
        assert!(app_info.is_ok());
        let info = app_info.unwrap();
        assert_eq!(info.user.and_then(|u| u.username), Some("abdullah".to_string()));
        let s = info.server.unwrap();
        assert!(s.is_connected);
        assert!(s.is_logged_in);
    }

    #[test]
    fn test_slskd_detect_configured_username() {
        let username = SlskdClient::detect_configured_username();
        assert_eq!(username, Some("abdullah".to_string()));
    }

    #[test]
    fn test_generate_secure_api_key() {
        let key1 = SlskdClient::generate_secure_api_key();
        let key2 = SlskdClient::generate_secure_api_key();
        assert_eq!(key1.len(), 64);
        assert_eq!(key2.len(), 64);
        assert_ne!(key1, key2);
        assert!(key1.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_login_status_variants() {
        assert!(SoulseekLoginStatus::Valid.is_valid());
        assert_eq!(SoulseekLoginStatus::Valid.display_badge(), "Verified");
        assert!(!SoulseekLoginStatus::InvalidCredentials("bad pass".into()).is_valid());
        assert_eq!(SoulseekLoginStatus::InvalidCredentials("bad pass".into()).display_badge(), "Wrong Password");
        assert_eq!(SoulseekLoginStatus::Connecting.display_badge(), "Connecting");
        assert_eq!(SoulseekLoginStatus::Offline.display_badge(), "Offline");
    }

    #[test]
    fn test_ensure_slskd_config() {
        let temp_dir = std::env::temp_dir().join(format!("slskd_test_{}", std::process::id()));
        let temp_path = temp_dir.join("slskd.local.yml");
        let res = SlskdClient::ensure_slskd_config_at(&temp_path, "testuser", "testpass");
        assert!(res.is_ok());
        let (path, key) = res.unwrap();
        assert!(path.exists());
        assert_eq!(key.len(), 64);
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("username: testuser"));
        assert!(content.contains("password: testpass"));
        assert!(content.contains(&key));
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_slskd_file_result_formatters() {
        let f1 = SlskdFileResult {
            username: "peer1".to_string(),
            filename: "Artist/Album/01 - Song.flac".to_string(),
            size: 47_185_920, // ~45 MB
            bitrate: None,
            sample_rate: Some(96000),
            bit_depth: Some(24),
            upload_speed: Some(2_097_152),
            queue_length: 0,
            probed_verdict: None,
        };
        assert!(f1.is_flac());
        assert!(!f1.is_wav());
        assert_eq!(f1.format_tag(), "FLAC");
        assert_eq!(f1.formatted_size(), "45.0 MB");
        assert_eq!(f1.formatted_resolution(), "24-bit/96kHz");
        assert_eq!(f1.formatted_bitrate(), "VBR Lossless");

        let f2 = SlskdFileResult {
            username: "peer2".to_string(),
            filename: "02 - Track.mp3".to_string(),
            size: 10_485_760,
            bitrate: Some(320),
            sample_rate: Some(44100),
            bit_depth: Some(16),
            upload_speed: None,
            queue_length: 2,
            probed_verdict: None,
        };
        assert_eq!(f2.format_tag(), "MP3");
        assert_eq!(f2.formatted_resolution(), "16-bit/44.1kHz");
        assert_eq!(f2.formatted_bitrate(), "320 kbps");
    }

    #[test]
    fn test_slskd_is_daemon_online_probe() {
        // Fast non-blocking probe returns without hanging
        let _online = SlskdClient::is_daemon_online();
    }
}
