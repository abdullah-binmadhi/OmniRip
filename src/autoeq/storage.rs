//! OmniRip Preset Storage and Remote Downloader Engine.
//!
//! Provides JSON persistence for user presets in ~/.config/omnirip/presets/,
//! synthesis of 10-band graphic EQ curves to parametric biquad matrices,
//! and network fetching for remote AutoEQ/EqualizerAPO profiles.

use std::fs;
use std::path::PathBuf;
use std::time::Duration;
use serde::{Deserialize, Serialize};

use crate::autoeq::parser::{parse_parametric_eq, ParametricProfile};
use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};

/// Standard graphic EQ band center frequencies in Hertz.
pub const GRAPHIC_EQ_FREQUENCIES: [f32; 10] = [
    31.0, 63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
];

/// Quality factor for 10-band standard 1-octave graphic EQ filters.
pub const GRAPHIC_EQ_Q: f32 = 1.414;

/// Persisted configuration of an OmniRip audio preset.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct OmniRipPreset {
    pub name: String,
    pub preamp_db: f32,
    pub volume_boost_db: f32,
    pub balance: f32,
    pub tube_warmth: f32,
    pub spatial_width: f32,
    pub limiter_ceiling_db: f32,
    pub band_gains: [f32; 10],
    #[serde(default)]
    pub raw_eq_text: Option<String>,
}

impl OmniRipPreset {
    /// Construct a preset from active audio DSP parameters.
    pub fn from_active_state(
        name: String,
        preamp_db: f32,
        volume_boost_db: f32,
        balance: f32,
        tube_warmth: f32,
        spatial_width: f32,
        limiter_ceiling_db: f32,
        band_gains: [f32; 10],
        raw_eq_text: Option<String>,
    ) -> Self {
        Self {
            name,
            preamp_db,
            volume_boost_db,
            balance,
            tube_warmth,
            spatial_width,
            limiter_ceiling_db,
            band_gains,
            raw_eq_text,
        }
    }

    /// Convert preset into a ParametricProfile for the AutoEQ browser and DSP engine.
    pub fn to_profile(&self, sample_rate: f32) -> ParametricProfile {
        if let Some(ref text) = self.raw_eq_text {
            if !text.trim().is_empty() {
                let mut profile = parse_parametric_eq(&self.name, text, sample_rate);
                profile.preamp_db = self.preamp_db;
                return profile;
            }
        }

        // Synthesize 10 second-order peaking biquads from graphic EQ bands
        let mut filters = Vec::with_capacity(10);
        for (i, &freq) in GRAPHIC_EQ_FREQUENCIES.iter().enumerate() {
            let gain_db = self.band_gains[i];
            let biquad = BiquadFilter::new(BiquadFilterType::Peaking, freq, gain_db, GRAPHIC_EQ_Q, sample_rate);
            filters.push(biquad);
        }

        ParametricProfile {
            name: self.name.clone(),
            preamp_db: self.preamp_db,
            filters,
        }
    }
}

/// Retrieve the canonical directory for storing user presets (~/.config/omnirip/presets/ on Unix, %APPDATA%\omnirip\presets on Windows).
pub fn get_presets_dir() -> PathBuf {
    if let Ok(home) = std::env::var("HOME") {
        let dir = PathBuf::from(home).join(".config").join("omnirip").join("presets");
        let _ = fs::create_dir_all(&dir);
        dir
    } else if let Ok(appdata) = std::env::var("APPDATA") {
        let dir = PathBuf::from(appdata).join("omnirip").join("presets");
        let _ = fs::create_dir_all(&dir);
        dir
    } else if let Ok(userprofile) = std::env::var("USERPROFILE") {
        let dir = PathBuf::from(userprofile).join(".config").join("omnirip").join("presets");
        let _ = fs::create_dir_all(&dir);
        dir
    } else {
        let dir = PathBuf::from("./presets");
        let _ = fs::create_dir_all(&dir);
        dir
    }
}

/// Sanitize preset names for safe filesystem storage.
pub fn sanitize_filename(name: &str) -> String {
    let sanitized: String = name
        .chars()
        .map(|c| match c {
            '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' | '\0' => '_',
            ' ' => '_',
            other => other,
        })
        .collect();

    let trimmed = sanitized.trim_matches('_');
    if trimmed.is_empty() {
        "custom_preset".to_string()
    } else {
        trimmed.to_string()
    }
}

/// Save an OmniRip preset as JSON in ~/.config/omnirip/presets/.
pub fn save_preset_to_disk(preset: &OmniRipPreset) -> Result<PathBuf, String> {
    let dir = get_presets_dir();
    let file_name = format!("{}.json", sanitize_filename(&preset.name));
    let path = dir.join(file_name);

    let json = serde_json::to_string_pretty(preset)
        .map_err(|e| format!("Serialization error: {}", e))?;

    fs::write(&path, json).map_err(|e| format!("File write error: {}", e))?;
    Ok(path)
}

/// Save active acoustic gear profile to ~/.config/omnirip/active_gear.json
pub fn save_active_gear_to_disk(gear: &crate::dsp::enhancer::AcousticGearProfile) -> Result<PathBuf, String> {
    let base_dir = get_presets_dir().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    let path = base_dir.join("active_gear.json");
    let json = serde_json::to_string_pretty(gear)
        .map_err(|e| format!("Serialization error: {}", e))?;
    fs::write(&path, json).map_err(|e| format!("File write error: {}", e))?;
    Ok(path)
}

/// Load active acoustic gear profile from ~/.config/omnirip/active_gear.json
pub fn load_active_gear_from_disk() -> Option<crate::dsp::enhancer::AcousticGearProfile> {
    let base_dir = get_presets_dir().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    let path = base_dir.join("active_gear.json");
    if let Ok(content) = fs::read_to_string(&path) {
        if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
            return Some(gear);
        }
    }
    None
}


/// Load all user presets from ~/.config/omnirip/presets/.
pub fn load_all_user_presets(sample_rate: f32) -> Vec<(OmniRipPreset, ParametricProfile)> {
    let dir = get_presets_dir();
    let mut results = Vec::new();

    let entries = match fs::read_dir(&dir) {
        Ok(e) => e,
        Err(_) => return results,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("json") {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(preset) = serde_json::from_str::<OmniRipPreset>(&content) {
                    let profile = preset.to_profile(sample_rate);
                    results.push((preset, profile));
                }
            }
        }
    }

    // Sort alphabetically by preset name
    results.sort_by(|a, b| a.0.name.to_lowercase().cmp(&b.0.name.to_lowercase()));
    results
}

/// Download raw parametric EQ text from a URL with safety bounds (5s timeout, 1MB max).
pub async fn download_raw_preset(url: &str) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| format!("HTTP client initialization failed: {}", e))?;

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Network request failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Server returned HTTP {}", response.status()));
    }

    // Enforce 1MB safety limit
    if let Some(content_length) = response.content_length() {
        if content_length > 1_048_576 {
            return Err("Payload exceeds 1 MB limit".to_string());
        }
    }

    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read response body: {}", e))?;

    if bytes.len() > 1_048_576 {
        return Err("Payload exceeds 1 MB limit".to_string());
    }

    String::from_utf8(bytes.to_vec()).map_err(|e| format!("Invalid UTF-8 payload: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_filename() {
        assert_eq!(sanitize_filename("Sennheiser HD 600 / Harman"), "Sennheiser_HD_600___Harman");
        assert_eq!(sanitize_filename("  My Custom:EQ*Test?  "), "My_Custom_EQ_Test");
        assert_eq!(sanitize_filename("///"), "custom_preset");
    }

    #[test]
    fn test_preset_graphic_synthesis() {
        let mut gains = [0.0f32; 10];
        gains[0] = 3.0; // 31 Hz
        gains[5] = -2.5; // 1000 Hz
        gains[9] = 4.0; // 16000 Hz

        let preset = OmniRipPreset::from_active_state(
            "Test Preset".to_string(),
            -3.0,
            1.2,
            0.0,
            0.25,
            0.5,
            -0.1,
            gains,
            None,
        );

        let profile = preset.to_profile(48000.0);
        assert_eq!(profile.name, "Test Preset");
        assert_eq!(profile.preamp_db, -3.0);
        assert_eq!(profile.filters.len(), 10);
        assert_eq!(profile.filters[0].filter_type, BiquadFilterType::Peaking);
        assert_eq!(profile.filters[0].frequency, 31.0);
        assert_eq!(profile.filters[0].gain_db, 3.0);
        assert_eq!(profile.filters[5].frequency, 1000.0);
        assert_eq!(profile.filters[5].gain_db, -2.5);
    }

    #[test]
    fn test_preset_roundtrip_serialization() {
        let preset = OmniRipPreset::from_active_state(
            "Roundtrip Test".to_string(),
            -4.5,
            0.0,
            -0.1,
            0.8,
            0.4,
            -0.2,
            [1.0, 2.0, 3.0, -1.0, -2.0, 0.0, 1.5, -0.5, 2.5, 3.5],
            Some("Preamp: -4.5 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3.0 dB Q 1.41".to_string()),
        );

        let json = serde_json::to_string(&preset).expect("Serialization failed");
        let decoded: OmniRipPreset = serde_json::from_str(&json).expect("Deserialization failed");

        assert_eq!(preset, decoded);
    }
}
