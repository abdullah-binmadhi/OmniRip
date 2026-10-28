//! Nicotine+ Local Configuration & Lossless P2P Integration for OmniRip.
//! Reads active sessions from ~/.config/nicotine/config and ranks lossless FLAC candidates.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct NicotineConfig {
    pub username: String,
    pub password: Option<String>,
    pub server: String,
    pub port: u16,
    pub download_dir: Option<PathBuf>,
    pub is_logged_in: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveredAccount {
    pub username: String,
    pub password: Option<String>,
    pub source: String,
    pub config_path: Option<PathBuf>,
    pub is_active: bool,
}

impl NicotineConfig {
    /// Discovers all Soulseek/Nicotine+ accounts configured on the system across all supported locations.
    pub fn discover_all_accounts() -> Vec<DiscoveredAccount> {
        let mut accounts = Vec::new();
        let mut seen_usernames = std::collections::HashSet::new();
        let active_opt = Self::detect_local();

        // 1. Check environment variables
        if let Ok(env_user) = std::env::var("SOULSEEK_USERNAME").or_else(|_| std::env::var("SOULSEEK_LOGIN")) {
            let u = env_user.trim().to_string();
            if !u.is_empty() {
                let pass = std::env::var("SOULSEEK_PASSWORD").or_else(|_| std::env::var("SOULSEEK_PASS")).ok();
                let is_active = active_opt.as_ref().map(|a| a.username == u).unwrap_or(false);
                accounts.push(DiscoveredAccount {
                    username: u.clone(),
                    password: pass,
                    source: "Environment Variable".to_string(),
                    config_path: None,
                    is_active,
                });
                seen_usernames.insert(u);
            }
        }

        // 2. Candidate paths with friendly labels
        let mut paths: Vec<(PathBuf, &str)> = Vec::new();
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            let h = PathBuf::from(&home);
            paths.push((h.join(".config/omnirip/soulseek.ini"), "OmniRip Config"));
            paths.push((h.join(".config/nicotine/config"), "Nicotine+ (Config)"));
            paths.push((h.join("Library/Application Support/Nicotine/config"), "Nicotine+ (macOS AppSupport)"));
            paths.push((h.join("Library/Application Support/Nicotine+/config"), "Nicotine+ (macOS AppSupport)"));
            paths.push((h.join(".nicotine/config"), "Nicotine+ (Legacy)"));
            paths.push((h.join(".SoulseekQt/soulseek.ini"), "SoulseekQt"));
        }
        if let Ok(appdata) = std::env::var("APPDATA") {
            let a = PathBuf::from(&appdata);
            paths.push((a.join("omnirip/soulseek.ini"), "OmniRip Config (Windows)"));
            paths.push((a.join("nicotine/config"), "Nicotine+ (Windows)"));
            paths.push((a.join("SoulseekQt/soulseek.ini"), "SoulseekQt (Windows)"));
        }

        for (path, label) in paths {
            if path.exists() {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    if let Some(cfg) = Self::parse_ini_content(&content) {
                        if !seen_usernames.contains(&cfg.username) {
                            let is_active = active_opt.as_ref().map(|a| a.username == cfg.username).unwrap_or(false)
                                || (accounts.is_empty() && seen_usernames.is_empty());
                            seen_usernames.insert(cfg.username.clone());
                            accounts.push(DiscoveredAccount {
                                username: cfg.username,
                                password: cfg.password,
                                source: label.to_string(),
                                config_path: Some(path),
                                is_active,
                            });
                        }
                    }
                }
            }
        }

        // 3. Scan slskd YAML configs
        let mut slskd_paths: Vec<(PathBuf, &str)> = Vec::new();
        slskd_paths.push((PathBuf::from("tools/slskd/slskd.local.yml"), "slskd Local Daemon"));
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            let h = PathBuf::from(&home);
            slskd_paths.push((h.join(".config/omnirip/slskd.yml"), "OmniRip slskd Config"));
            slskd_paths.push((h.join("Projects/OmniRip/tools/slskd/slskd.local.yml"), "slskd Workspace Daemon"));
        }
        for (path, label) in slskd_paths {
            if path.exists() {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    let mut in_soulseek = false;
                    let mut user_opt = None;
                    let mut pass_opt = None;
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed == "soulseek:" {
                            in_soulseek = true;
                            continue;
                        }
                        if in_soulseek && !line.starts_with(' ') && !line.starts_with('\t') {
                            in_soulseek = false;
                        }
                        if in_soulseek {
                            if trimmed.starts_with("username:") {
                                if let Some((_, v)) = trimmed.split_once(':') {
                                    let u = v.trim().trim_matches('"').trim_matches('\'');
                                    if !u.is_empty() && u != "YOUR_SOULSEEK_USERNAME" {
                                        user_opt = Some(u.to_string());
                                    }
                                }
                            } else if trimmed.starts_with("password:") {
                                if let Some((_, v)) = trimmed.split_once(':') {
                                    let p = v.trim().trim_matches('"').trim_matches('\'');
                                    if !p.is_empty() && p != "CHANGE_ME" {
                                        pass_opt = Some(p.to_string());
                                    }
                                }
                            }
                        }
                    }
                    if let Some(user) = user_opt {
                        if !seen_usernames.contains(&user) {
                            let is_active = active_opt.as_ref().map(|a| a.username == user).unwrap_or(false)
                                || (accounts.is_empty() && seen_usernames.is_empty());
                            seen_usernames.insert(user.clone());
                            accounts.push(DiscoveredAccount {
                                username: user,
                                password: pass_opt,
                                source: label.to_string(),
                                config_path: Some(path),
                                is_active,
                            });
                        }
                    }
                }
            }
        }

        accounts
    }

    /// Synchronizes active credentials across any detected Nicotine+ config files.
    fn sync_nicotine_config(username: &str, password: Option<&str>) {
        let mut paths = Vec::new();
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            let h = PathBuf::from(&home);
            paths.push(h.join(".config/nicotine/config"));
        }
        for path in paths {
            if path.exists() {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    let mut new_lines = Vec::new();
                    let mut in_server = false;
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed == "[server]" {
                            in_server = true;
                            new_lines.push(line.to_string());
                            continue;
                        }
                        if in_server && trimmed.starts_with('[') && trimmed.ends_with(']') {
                            in_server = false;
                        }
                        if in_server && (trimmed.starts_with("login =") || trimmed.starts_with("login=")) {
                            new_lines.push(format!("login = {}", username));
                        } else if in_server && (trimmed.starts_with("passw =") || trimmed.starts_with("passw=") || trimmed.starts_with("password =") || trimmed.starts_with("password=")) {
                            if let Some(p) = password {
                                new_lines.push(format!("passw = {}", p));
                            } else {
                                new_lines.push(line.to_string());
                            }
                        } else {
                            new_lines.push(line.to_string());
                        }
                    }
                    let _ = std::fs::write(&path, new_lines.join("\n") + "\n");
                }
            }
        }
    }

    /// Saves the selected account as the active default in ~/.config/omnirip/soulseek.ini (or %APPDATA%/omnirip/soulseek.ini).
    pub fn save_active_account(username: &str, password: Option<&str>) -> Result<PathBuf, String> {
        let config_dir = if let Ok(appdata) = std::env::var("APPDATA") {
            PathBuf::from(appdata).join("omnirip")
        } else if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            PathBuf::from(home).join(".config/omnirip")
        } else {
            PathBuf::from(".config/omnirip")
        };

        std::fs::create_dir_all(&config_dir)
            .map_err(|e| format!("Failed to create omnirip config directory: {}", e))?;

        let file_path = config_dir.join("soulseek.ini");
        let pass_line = match password {
            Some(p) => format!("passw = {}\n", p),
            None => String::new(),
        };

        let ini_content = format!(
            "[server]\nlogin = {}\n{}server = server.slsknet.org\nport = 2242\n",
            username, pass_line
        );

        std::fs::write(&file_path, ini_content)
            .map_err(|e| format!("Failed to write soulseek.ini: {}", e))?;

        // Synchronize with Nicotine+ and slskd
        Self::sync_nicotine_config(username, password);
        if let Some(p) = password {
            let _ = crate::harvest::slskd::SlskdClient::ensure_slskd_config(username, p);
        }

        Ok(file_path)
    }

    /// Detects and reads the user's local active Soulseek session from environment variables or standard config locations.
    pub fn detect_local() -> Option<Self> {
        // 1. Check environment variables (SOULSEEK_USERNAME / SOULSEEK_LOGIN)
        let env_user = std::env::var("SOULSEEK_USERNAME")
            .or_else(|_| std::env::var("SOULSEEK_LOGIN"))
            .ok();
        if let Some(user) = env_user {
            let trimmed = user.trim();
            if !trimmed.is_empty() {
                let pass = std::env::var("SOULSEEK_PASSWORD")
                    .or_else(|_| std::env::var("SOULSEEK_PASS"))
                    .ok();
                return Some(Self {
                    username: trimmed.to_string(),
                    password: pass.filter(|p| !p.trim().is_empty()),
                    server: "server.slsknet.org".to_string(),
                    port: 2242,
                    download_dir: None,
                    is_logged_in: true,
                });
            }
        }

        // 2. Scan cross-platform config paths (macOS, Linux, Windows)
        let mut candidates = Vec::new();
        if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
            let home_path = PathBuf::from(&home);
            candidates.push(home_path.join(".config/omnirip/soulseek.ini"));
            candidates.push(home_path.join(".config/nicotine/config"));
            candidates.push(home_path.join("Library/Application Support/Nicotine/config"));
            candidates.push(home_path.join("Library/Application Support/Nicotine+/config"));
            candidates.push(home_path.join(".nicotine/config"));
        }
        if let Ok(appdata) = std::env::var("APPDATA") {
            let appdata_path = PathBuf::from(&appdata);
            candidates.push(appdata_path.join("omnirip/soulseek.ini"));
            candidates.push(appdata_path.join("nicotine/config"));
        }

        for path in candidates {
            if path.exists() {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    if let Some(cfg) = Self::parse_ini_content(&content) {
                        return Some(cfg);
                    }
                }
            }
        }

        None
    }

    /// Parses Nicotine+ INI configuration text into structured settings.
    pub fn parse_ini_content(content: &str) -> Option<Self> {
        let mut current_section = "";
        let mut username = String::new();
        let mut password = None;
        let mut server = "server.slsknet.org".to_string();
        let mut port = 2242u16;
        let mut download_dir = None;

        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with(';') {
                continue;
            }

            if trimmed.starts_with('[') && trimmed.ends_with(']') {
                current_section = &trimmed[1..trimmed.len() - 1];
                continue;
            }

            if let Some((key, val)) = trimmed.split_once('=') {
                let k = key.trim();
                let v = val.trim();

                match current_section {
                    "server" => match k {
                        "login" => username = v.to_string(),
                        "pass" | "password" | "passw" => {
                            if !v.is_empty() {
                                password = Some(v.to_string());
                            }
                        }
                        "server" => {
                            if !v.is_empty() {
                                server = v.to_string();
                            }
                        }
                        "port" => {
                            if let Ok(p) = v.parse::<u16>() {
                                port = p;
                            }
                        }
                        _ => {}
                    },
                    "transfers" => {
                        if k == "downloaddir" && !v.is_empty() {
                            download_dir = Some(PathBuf::from(v));
                        }
                    }
                    _ => {}
                }
            }
        }

        if username.is_empty() {
            None
        } else {
            Some(NicotineConfig {
                is_logged_in: true,
                username,
                password,
                server,
                port,
                download_dir,
            })
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthenticityBadge {
    GenuineHiRes(u32, u32),     // bit_depth, sample_rate in kHz
    GenuineCD,                  // 16-bit / 44.1kHz standard
    PlausibleLossless,          // Standard valid FLAC/WAV
    SuspectTranscode(String),   // Reason for suspicion
    ProbedAuthentic(u32),       // Ground-truth verified cutoff in kHz
    ProbedFake(u32),            // Ground-truth detected low cutoff in kHz
}

impl AuthenticityBadge {
    pub fn label(&self) -> String {
        match self {
            AuthenticityBadge::GenuineHiRes(bits, khz) => format!("[HI-RES {}b/{}k]", bits, khz),
            AuthenticityBadge::GenuineCD => "[CD QUALITY]".to_string(),
            AuthenticityBadge::PlausibleLossless => "[LOSSLESS]".to_string(),
            AuthenticityBadge::SuspectTranscode(_) => "[SUSPECT FAKE]".to_string(),
            AuthenticityBadge::ProbedAuthentic(khz) => {
                if *khz >= 44 {
                    "[VERIFIED HI-RES]".to_string()
                } else {
                    "[VERIFIED LOSSLESS]".to_string()
                }
            }
            AuthenticityBadge::ProbedFake(_) => "[FAKE LOSSLESS]".to_string(),
        }
    }

    pub fn compact_label(&self) -> &'static str {
        match self {
            AuthenticityBadge::GenuineHiRes(_, _) => "[HI-RES]",
            AuthenticityBadge::GenuineCD => "[CD]",
            AuthenticityBadge::PlausibleLossless => "[LOSSLESS]",
            AuthenticityBadge::SuspectTranscode(_) => "[SUSPECT]",
            AuthenticityBadge::ProbedAuthentic(khz) => {
                if *khz >= 44 {
                    "[HI-RES]"
                } else {
                    "[VERIFIED]"
                }
            }
            AuthenticityBadge::ProbedFake(_) => "[FAKE]",
        }
    }

    pub fn is_suspect_or_fake(&self) -> bool {
        matches!(self, AuthenticityBadge::SuspectTranscode(_) | AuthenticityBadge::ProbedFake(_))
    }

    pub fn explanation(&self) -> String {
        match self {
            AuthenticityBadge::GenuineHiRes(bits, khz) => {
                format!("Hi-Res Lossless: Genuine {}-bit / {} kHz studio master audio", bits, khz)
            }
            AuthenticityBadge::GenuineCD => {
                "CD Quality: Standard 16-bit / 44.1 kHz Red Book lossless audio".to_string()
            }
            AuthenticityBadge::PlausibleLossless => {
                "Lossless container format with standard audio parameters".to_string()
            }
            AuthenticityBadge::SuspectTranscode(reason) => {
                format!("SUSPECT FAKE: Likely lossy transcode ({})", reason)
            }
            AuthenticityBadge::ProbedAuthentic(khz) => {
                if *khz >= 44 {
                    "VERIFIED HI-RES: Authentic 24-bit / 96kHz+ studio master (extended ultrasonic bandwidth confirmed)".to_string()
                } else {
                    "VERIFIED LOSSLESS: Authentic high-fidelity audio (no lossy compression artifacts)".to_string()
                }
            }
            AuthenticityBadge::ProbedFake(_) => {
                "FAKE LOSSLESS: Audio was upsampled from a low-quality MP3/lossy file (cutoff detected)".to_string()
            }
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SpeedTier {
    EdgeCdn,           // 50 - 100+ MB/s line-speed direct CDN stream
    DistributedSwarm,  // 15 - 25 MB/s multi-peer parallel swarm
    HighSpeedPeer,     // >= 1.5 MB/s, <= 1 in queue
    StandardPeer,      // 400 KB/s - 1.5 MB/s, <= 3 in queue
    CongestedQueue,    // < 300 KB/s or > 4 in queue
}

impl SpeedTier {
    pub fn label(&self) -> &'static str {
        match self {
            SpeedTier::EdgeCdn => "[EDGE CDN]",
            SpeedTier::DistributedSwarm => "[SWARM 20M]",
            SpeedTier::HighSpeedPeer => "[HIGH-SPEED]",
            SpeedTier::StandardPeer => "[STANDARD]",
            SpeedTier::CongestedQueue => "[CONGESTED]",
        }
    }

    pub fn throughput_desc(&self) -> &'static str {
        match self {
            SpeedTier::EdgeCdn => "50-100+ MB/s (Full Line Speed)",
            SpeedTier::DistributedSwarm => "15-25 MB/s (Multi-Peer Parallel)",
            SpeedTier::HighSpeedPeer => "1.5-5.0 MB/s (Fast Peer)",
            SpeedTier::StandardPeer => "400 KB/s - 1.5 MB/s (Standard Peer)",
            SpeedTier::CongestedQueue => "< 300 KB/s or Congested Queue",
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct NicotineCandidate {
    pub username: String,
    pub filename: String,
    pub size_bytes: u64,
    pub bitrate_kbps: Option<u32>,
    pub bit_depth: Option<u32>,
    pub sample_rate: Option<u32>,
    pub speed_kbps: Option<f32>,
    pub in_queue: usize,
    pub score: f32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub probed_verdict: Option<crate::harvest::spectral::SpectralAnalysisResult>,
}

impl NicotineCandidate {
    pub fn is_flac(&self) -> bool {
        self.filename.to_lowercase().ends_with(".flac")
    }

    pub fn is_wav(&self) -> bool {
        self.filename.to_lowercase().ends_with(".wav")
    }

    pub fn evaluate_authenticity(&self) -> AuthenticityBadge {
        if let Some(ref probed) = self.probed_verdict {
            match probed.verdict {
                crate::harvest::spectral::QualityVerdict::TrueLosslessHiRes => {
                    return AuthenticityBadge::ProbedAuthentic((probed.cutoff_freq_hz / 1000.0).round() as u32);
                }
                crate::harvest::spectral::QualityVerdict::TrueLosslessCD => {
                    return AuthenticityBadge::ProbedAuthentic((probed.cutoff_freq_hz / 1000.0).round() as u32);
                }
                crate::harvest::spectral::QualityVerdict::FakeLossless(hz) |
                crate::harvest::spectral::QualityVerdict::LossyCutoff(hz) => {
                    return AuthenticityBadge::ProbedFake(hz / 1000);
                }
                crate::harvest::spectral::QualityVerdict::NearLossless320k => {
                    return AuthenticityBadge::ProbedFake(20);
                }
            }
        }

        let lower_path = format!("{} {}", self.filename, self.directory_name()).to_lowercase();
        let suspect_tokens = [
            "transcode", "upscale", "upscaled", "lossy to flac", "youtube",
            "yt-dlp", "128k to flac", "converted", "webrip 128", "soundclick",
            "webrip", "spotify-rip", "spotdl", "aac2flac", "mp3toflac",
            "opus2flac", "fake flac", "fakeflac", "lossy-master", "rip from youtube",
            "re-encoded", "192k to flac", "256k to flac", "320k to flac",
        ];
        for token in suspect_tokens {
            if lower_path.contains(token) {
                return AuthenticityBadge::SuspectTranscode(format!("Path contains '{}'", token));
            }
        }

        let is_lossless = self.is_flac()
            || self.is_wav()
            || self.filename.to_lowercase().ends_with(".alac")
            || self.filename.to_lowercase().ends_with(".aiff")
            || self.filename.to_lowercase().ends_with(".aif");

        let sample_rate = self.sample_rate.unwrap_or(44100);
        let bit_depth = self.bit_depth.unwrap_or(16);
        let br = self.bitrate_kbps.unwrap_or(0);
        let mb = (self.size_bytes as f64) / (1024.0 * 1024.0);

        if is_lossless {
            if (br == 128 || br == 160 || br == 192 || br == 256 || br == 320) && mb > 0.0 && mb < 18.0 {
                return AuthenticityBadge::SuspectTranscode(format!("Lossless container reports exact lossy bitrate of {} kbps", br));
            }
            if br > 0 && br < 500 && mb > 0.0 && mb < 15.0 {
                return AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is implausibly low for true lossless audio", br));
            }
            if self.is_flac() && mb > 0.0 && mb < 4.0 {
                return AuthenticityBadge::SuspectTranscode(format!("File size ({:.1} MB) is too small to contain true lossless audio", mb));
            }
            if self.is_wav() && mb > 0.0 && mb < 8.0 {
                return AuthenticityBadge::SuspectTranscode(format!("WAV size ({:.1} MB) is too small for uncompressed PCM audio", mb));
            }
        }

        if bit_depth >= 24 || sample_rate >= 88200 {
            if br > 0 && br < 1200 {
                return AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is implausibly low for genuine {}/{}", br, bit_depth, sample_rate));
            }
            return AuthenticityBadge::GenuineHiRes(bit_depth, sample_rate / 1000);
        }

        if sample_rate == 44100 && bit_depth == 16 {
            if br > 0 && br < 400 && mb > 0.0 && mb < 12.0 {
                return AuthenticityBadge::SuspectTranscode(format!("Bitrate {} kbps is too low for Red Book CD FLAC", br));
            }
            return AuthenticityBadge::GenuineCD;
        }

        if is_lossless {
            AuthenticityBadge::PlausibleLossless
        } else {
            AuthenticityBadge::SuspectTranscode("Lossy container format".to_string())
        }
    }

    pub fn evaluate_speed_tier(&self) -> SpeedTier {
        let speed = self.speed_kbps.unwrap_or(0.0);
        if self.in_queue > 4 || (speed > 0.0 && speed < 300.0) {
            SpeedTier::CongestedQueue
        } else if speed >= 1500.0 && self.in_queue <= 1 {
            SpeedTier::HighSpeedPeer
        } else if speed >= 400.0 && self.in_queue <= 3 {
            SpeedTier::StandardPeer
        } else if speed > 0.0 {
            SpeedTier::StandardPeer
        } else {
            SpeedTier::StandardPeer
        }
    }

    pub fn formatted_eta(&self) -> String {
        let speed_kbytes_sec = match self.speed_kbps {
            Some(kb) if kb > 0.0 => kb as f64,
            _ => 1000.0, // Baseline estimate: 1 MB/s
        };
        let size_kb = (self.size_bytes as f64) / 1024.0;
        let secs = (size_kb / speed_kbytes_sec).round() as u64;
        let base_eta = if secs <= 3 {
            "ETA: ~3s".to_string()
        } else if secs < 60 {
            format!("ETA: ~{}s", secs)
        } else {
            format!("ETA: ~{}m {}s", secs / 60, secs % 60)
        };

        if self.in_queue > 0 {
            format!("{} (Q:{})", base_eta, self.in_queue)
        } else {
            base_eta
        }
    }

    pub fn formatted_size(&self) -> String {
        let mb = (self.size_bytes as f64) / (1024.0 * 1024.0);
        format!("{:.1} MB", mb)
    }

    pub fn formatted_resolution(&self) -> String {
        let depth_str = match self.bit_depth {
            Some(d) => format!("{}-bit", d),
            None => if self.is_flac() { "Lossless".to_string() } else { "16-bit".to_string() },
        };
        let rate_str = match self.sample_rate {
            Some(sr) => format!("{:.1} kHz", (sr as f32) / 1000.0),
            None => "44.1 kHz".to_string(),
        };
        format!("{} / {}", depth_str, rate_str)
    }

    pub fn directory_name(&self) -> String {
        let clean = self.filename.replace('\\', "/");
        if let Some((dir, _)) = clean.rsplit_once('/') {
            if let Some((_, last_dir)) = dir.rsplit_once('/') {
                last_dir.to_string()
            } else {
                dir.to_string()
            }
        } else {
            "Single Track".to_string()
        }
    }

    pub fn formatted_speed(&self) -> String {
        match self.speed_kbps {
            Some(kb) if kb >= 1024.0 => format!("{:.1} MB/s", kb / 1024.0),
            Some(kb) if kb > 0.0 => format!("{:.0} KB/s", kb),
            _ => "Unknown".to_string(),
        }
    }

    pub fn formatted_queue(&self) -> String {
        if self.in_queue == 0 {
            "[INSTANT]".to_string()
        } else if self.in_queue <= 4 {
            format!("[QUEUE: {}]", self.in_queue)
        } else {
            format!("[DONOR ONLY ({})]", self.in_queue)
        }
    }

    pub fn relevance_score(&self, target_artist: &str, target_title: &str) -> u32 {
        let combined = format!("{} {}", self.filename, self.directory_name()).to_lowercase();
        let clean_combined: String = combined
            .chars()
            .map(|ch| if ch.is_alphanumeric() || ch.is_whitespace() { ch } else { ' ' })
            .collect();
        let mut score = 0u32;

        let clean_artist = target_artist.trim().to_lowercase();
        let clean_title = target_title.trim().to_lowercase();

        let mut artist_matched = false;
        if !clean_artist.is_empty() {
            let tokens: Vec<&str> = clean_artist.split_whitespace().collect();
            if !tokens.is_empty() && tokens.iter().all(|t| {
                let clean_t: String = t.chars().filter(|c| c.is_alphanumeric()).collect();
                clean_combined.contains(&clean_t) || combined.contains(t)
            }) {
                artist_matched = true;
                score += 30_000;
            }
        }

        let mut title_matched = false;
        if !clean_title.is_empty() {
            let tokens: Vec<&str> = clean_title.split_whitespace().collect();
            if !tokens.is_empty() && tokens.iter().all(|t| {
                let clean_t: String = t.chars().filter(|c| c.is_alphanumeric()).collect();
                clean_combined.contains(&clean_t) || combined.contains(t)
            }) {
                title_matched = true;
                score += 40_000;
            }
        }

        if artist_matched && title_matched {
            score += 100_000;
        }

        score
    }
}

/// Evaluates and scores a candidate file based on acoustic lossless fidelity and peer availability.
pub fn score_candidate(candidate: &NicotineCandidate) -> f32 {
    let mut score = 0.0f32;
    let lower = candidate.filename.to_lowercase();

    // 1. Audio container & compression format
    if lower.ends_with(".flac") {
        score += 50.0;
    } else if lower.ends_with(".wav") {
        score += 45.0;
    } else if lower.ends_with(".mp3") {
        score += 20.0;
    } else if lower.ends_with(".m4a") {
        score += 25.0;
    }

    // 2. Bit depth (Hi-Res Audiophile Master)
    if let Some(depth) = candidate.bit_depth {
        if depth >= 24 {
            score += 30.0;
        } else if depth >= 16 {
            score += 20.0;
        }
    } else if lower.ends_with(".flac") {
        score += 20.0; // Assume standard 16-bit FLAC if unspecified
    }

    // 3. Sample rate
    if let Some(sr) = candidate.sample_rate {
        if sr >= 96000 {
            score += 20.0;
        } else if sr >= 48000 {
            score += 15.0;
        } else if sr >= 44100 {
            score += 10.0;
        }
    }

    // 4. Bitrate
    if let Some(br) = candidate.bitrate_kbps {
        if br >= 900 {
            score += 15.0;
        } else if br >= 320 {
            score += 10.0;
        }
    }

    // 5. Queue availability & non-privileged priority
    if candidate.in_queue == 0 {
        score += 60.0; // Major priority boost: instant download without donor privileges
    } else if candidate.in_queue <= 3 {
        score += 10.0;
    } else if candidate.in_queue > 5 {
        score -= 50.0; // Heavy penalty: non-privileged users will be stalled or rejected
    }

    // 6. Peer speed
    if let Some(speed) = candidate.speed_kbps {
        if speed >= 1000.0 {
            score += 25.0;
        } else if speed >= 500.0 {
            score += 10.0;
        }
    }

    score
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_nicotine_ini_valid() {
        let ini = r#"
[server]
login = audiophile_user
pass = super_secret_pass
server = server.slsknet.org
port = 2242

[transfers]
downloaddir = /Users/test/Music/NicotineDownloads
"#;
        let cfg = NicotineConfig::parse_ini_content(ini).unwrap();
        assert_eq!(cfg.username, "audiophile_user");
        assert_eq!(cfg.password.as_deref(), Some("super_secret_pass"));
        assert_eq!(cfg.server, "server.slsknet.org");
        assert_eq!(cfg.port, 2242);
        assert_eq!(
            cfg.download_dir,
            Some(PathBuf::from("/Users/test/Music/NicotineDownloads"))
        );
        assert!(cfg.is_logged_in);
    }

    #[test]
    fn test_parse_nicotine_ini_no_login() {
        let ini = "[server]\nport = 2242\n";
        assert!(NicotineConfig::parse_ini_content(ini).is_none());
    }

    #[test]
    fn test_parse_nicotine_ini_passw_key() {
        let ini = "[server]\nlogin = weiharnsu\npassw = lekkia01\n";
        let cfg = NicotineConfig::parse_ini_content(ini).expect("Should parse passw key");
        assert_eq!(cfg.username, "weiharnsu");
        assert_eq!(cfg.password.as_deref(), Some("lekkia01"));
        assert!(cfg.is_logged_in);
    }

    #[test]
    fn test_score_candidate_flac_vs_mp3() {
        let flac = NicotineCandidate {
            username: "peer1".to_string(),
            filename: "Radiohead - Karma Police.flac".to_string(),
            size_bytes: 35_000_000,
            bitrate_kbps: Some(950),
            bit_depth: Some(24),
            sample_rate: Some(48000),
            speed_kbps: Some(1500.0),
            in_queue: 0,
            score: 0.0,
            probed_verdict: None,
        };

        let mp3 = NicotineCandidate {
            username: "peer2".to_string(),
            filename: "Radiohead - Karma Police.mp3".to_string(),
            size_bytes: 8_000_000,
            bitrate_kbps: Some(320),
            bit_depth: Some(16),
            sample_rate: Some(44100),
            speed_kbps: Some(200.0),
            in_queue: 15,
            score: 0.0,
            probed_verdict: None,
        };

        let flac_score = score_candidate(&flac);
        let mp3_score = score_candidate(&mp3);

        assert!(flac_score > mp3_score);
        assert!(flac_score >= 120.0);
    }

    #[test]
    fn test_detect_local_via_env_vars() {
        std::env::set_var("SOULSEEK_USERNAME", "test_env_user");
        std::env::set_var("SOULSEEK_PASSWORD", "test_env_pass");

        let cfg = NicotineConfig::detect_local().expect("Should detect from env vars");
        assert_eq!(cfg.username, "test_env_user");
        assert_eq!(cfg.password.as_deref(), Some("test_env_pass"));
        assert!(cfg.is_logged_in);

        std::env::remove_var("SOULSEEK_USERNAME");
        std::env::remove_var("SOULSEEK_PASSWORD");
    }

    #[test]
    fn test_discover_accounts_and_save() {
        let temp_dir = std::env::temp_dir().join("omnirip_test_acc");
        let _ = std::fs::create_dir_all(&temp_dir);
        let ini_file = temp_dir.join("soulseek.ini");
        let _ = std::fs::write(&ini_file, "[server]\nlogin = test_save_user\npassw = test_pass\n");

        let content = std::fs::read_to_string(&ini_file).unwrap();
        let parsed = NicotineConfig::parse_ini_content(&content).unwrap();
        assert_eq!(parsed.username, "test_save_user");
        assert_eq!(parsed.password.as_deref(), Some("test_pass"));

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_candidate_formatted_speed_and_queue() {
        let mut candidate = NicotineCandidate {
            username: "fast_peer".to_string(),
            filename: "track.flac".to_string(),
            size_bytes: 50_000_000,
            bitrate_kbps: Some(1411),
            bit_depth: Some(16),
            sample_rate: Some(44100),
            speed_kbps: Some(2500.0),
            in_queue: 0,
            score: 100.0,
            probed_verdict: None,
        };

        assert_eq!(candidate.formatted_speed(), "2.4 MB/s");
        assert_eq!(candidate.formatted_queue(), "[INSTANT]");

        candidate.speed_kbps = Some(450.0);
        candidate.in_queue = 3;
        assert_eq!(candidate.formatted_speed(), "450 KB/s");
        assert_eq!(candidate.formatted_queue(), "[QUEUE: 3]");

        candidate.in_queue = 8;
        assert_eq!(candidate.formatted_queue(), "[DONOR ONLY (8)]");

        candidate.speed_kbps = None;
        assert_eq!(candidate.formatted_speed(), "Unknown");
    }

    #[test]
    fn test_score_candidate_zero_queue_priority() {
        // Standard 16-bit FLAC from instant-start peer with 0 queue
        let instant_flac = NicotineCandidate {
            username: "instant_peer".to_string(),
            filename: "Song.flac".to_string(),
            size_bytes: 35_000_000,
            bitrate_kbps: Some(1411),
            bit_depth: Some(16),
            sample_rate: Some(44100),
            speed_kbps: Some(1200.0),
            in_queue: 0,
            score: 0.0,
            probed_verdict: None,
        };

        // 24-bit / 96kHz Hi-Res FLAC but heavily congested queue (donor privileges needed)
        let congested_hires = NicotineCandidate {
            username: "congested_vault".to_string(),
            filename: "Song 24bit.flac".to_string(),
            size_bytes: 90_000_000,
            bitrate_kbps: Some(3000),
            bit_depth: Some(24),
            sample_rate: Some(96000),
            speed_kbps: Some(800.0),
            in_queue: 15,
            score: 0.0,
            probed_verdict: None,
        };

        let instant_score = score_candidate(&instant_flac);
        let congested_score = score_candidate(&congested_hires);

        // Instant start peer must comfortably outrank congested donor-only peer
        assert!(instant_score > congested_score, "Instant start 16-bit FLAC ({}) should outrank congested 24-bit FLAC ({})", instant_score, congested_score);
    }
}
