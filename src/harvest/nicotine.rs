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

impl NicotineConfig {
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
}

impl NicotineCandidate {
    pub fn is_flac(&self) -> bool {
        self.filename.to_lowercase().ends_with(".flac")
    }

    pub fn is_wav(&self) -> bool {
        self.filename.to_lowercase().ends_with(".wav")
    }

    pub fn formatted_size(&self) -> String {
        let mb = (self.size_bytes as f64) / (1024.0 * 1024.0);
        format!("{:.1} MB", mb)
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

    // 5. Queue availability
    if candidate.in_queue == 0 {
        score += 20.0;
    } else if candidate.in_queue > 10 {
        score -= 15.0;
    }

    // 6. Peer speed
    if let Some(speed) = candidate.speed_kbps {
        if speed >= 1000.0 {
            score += 10.0;
        } else if speed >= 500.0 {
            score += 5.0;
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
}
