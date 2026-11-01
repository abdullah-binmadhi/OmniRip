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

    /// Convert an OmniRipPreset into a full MasteringPreset for the preset library.
    pub fn to_mastering_preset(&self) -> crate::dsp::enhancer::MasteringPreset {
        crate::dsp::enhancer::MasteringPreset {
            name: Box::leak(self.name.clone().into_boxed_str()),
            description: Box::leak(format!("User custom preset: {}", self.name).into_boxed_str()),
            target: Box::leak("User Customized".to_string().into_boxed_str()),
            spatial_width: self.spatial_width,
            tube_warmth: self.tube_warmth,
            air_clarity_db: 0.0,
            bass_punch_db: 0.0,
            mono_bass: false,
            mono_bass_freq: 85.0,
            loudness_contour: false,
            crossfeed: crate::dsp::enhancer::CrossfeedMode::Off,
            subsonic_filter: true,
            ultrasonic_filter: true,
            deesser_enabled: false,
            deesser_amount: 0.0,
            deesser_freq: 6500.0,
            tape_emulation: false,
            tape_drive: 0.0,
            transient_shaper: false,
            transient_attack_db: 0.0,
            transient_sustain_db: 0.0,
            ms_matrix_enabled: false,
            mid_gain_db: 0.0,
            side_gain_db: 0.0,
            side_air_db: 0.0,
            deharsh_enabled: false,
            deharsh_amount: 0.0,
            deharsh_freq: 3800.0,
            comp_enabled: false,
            comp_opto_drive: 0.0,
            comp_vca_drive: 0.0,
            pultec_enabled: false,
            pultec_low_boost: 0.0,
            pultec_air_boost: 0.0,
            pultec_air_freq: 16000.0,
            limiter_ceiling_dbfs: self.limiter_ceiling_db,
            eq_10_band: self.band_gains,
            game_mode: false,
            radar_eq: false,
            spike_shield: false,
        }
    }
}

/// Retrieve the canonical directory for storing user presets (~/.config/omnirip/presets/ on Unix, %APPDATA%\omnirip\presets on Windows).
pub fn get_presets_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("OMNIRIP_PRESETS_DIR") {
        let p = PathBuf::from(dir);
        let _ = fs::create_dir_all(&p);
        return p;
    }

    let target = if let Ok(home) = std::env::var("HOME") {
        PathBuf::from(home).join(".config").join("omnirip").join("presets")
    } else if let Ok(appdata) = std::env::var("APPDATA") {
        PathBuf::from(appdata).join("omnirip").join("presets")
    } else if let Ok(userprofile) = std::env::var("USERPROFILE") {
        PathBuf::from(userprofile).join(".config").join("omnirip").join("presets")
    } else {
        PathBuf::from("./presets")
    };

    if fs::create_dir_all(&target).is_ok() && fs::write(target.join(".probe"), b"").is_ok() {
        let _ = fs::remove_file(target.join(".probe"));
        target
    } else {
        let fallback = std::env::temp_dir().join("omnirip").join("presets");
        let _ = fs::create_dir_all(&fallback);
        fallback
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

/// Retrieve canonical filename for an acoustic gear profile based on form factor.
pub fn gear_filename_for_form_factor(form_factor: crate::dsp::enhancer::GearFormFactor) -> &'static str {
    match form_factor {
        crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers => "active_gear_speaker.json",
        crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers => "active_gear_bookshelf.json",
        _ => "active_gear_headphone.json",
    }
}

/// Save active acoustic gear profile to disk, routing to transducer-specific file.
pub fn save_gear_for_transducer(gear: &crate::dsp::enhancer::AcousticGearProfile) -> Result<PathBuf, String> {
    let base_dir = get_presets_dir().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    let filename = gear_filename_for_form_factor(gear.form_factor);
    let path = base_dir.join(filename);
    let json = serde_json::to_string_pretty(gear)
        .map_err(|e| format!("Serialization error: {}", e))?;
    fs::write(&path, &json).map_err(|e| format!("File write error: {}", e))?;

    // Also sync to active_gear.json for backward compatibility
    let legacy_path = base_dir.join("active_gear.json");
    let _ = fs::write(&legacy_path, json);
    Ok(path)
}

/// Load active acoustic gear profile tailored to the current output transducer.
pub fn load_gear_for_transducer(
    transducer: crate::dsp::hardware_detect::TransducerType,
    bookshelf_preferred: bool,
) -> Option<crate::dsp::enhancer::AcousticGearProfile> {
    let base_dir = get_presets_dir().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));

    match transducer {
        crate::dsp::hardware_detect::TransducerType::BuiltinSpeakers => {
            let path = base_dir.join("active_gear_speaker.json");
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                    return Some(gear);
                }
            }
            Some(crate::dsp::enhancer::AcousticGearProfile::default_builtin_speakers("MacBook Air"))
        }
        crate::dsp::hardware_detect::TransducerType::HeadphoneJack3_5mm
        | crate::dsp::hardware_detect::TransducerType::BluetoothA2dp => {
            let path = base_dir.join("active_gear_headphone.json");
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                    return Some(gear);
                }
            }
            // Backward compatibility fallback to active_gear.json (e.g. KATO IEMs)
            let legacy_path = base_dir.join("active_gear.json");
            if let Ok(content) = fs::read_to_string(&legacy_path) {
                if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                    if gear.form_factor != crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers
                        && gear.form_factor != crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers
                    {
                        return Some(gear);
                    }
                }
            }
            Some(crate::dsp::enhancer::AcousticGearProfile::default())
        }
        crate::dsp::hardware_detect::TransducerType::UsbDacLineOut => {
            if bookshelf_preferred {
                let path = base_dir.join("active_gear_bookshelf.json");
                if let Ok(content) = fs::read_to_string(&path) {
                    if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                        return Some(gear);
                    }
                }
                Some(crate::dsp::enhancer::AcousticGearProfile::default_bookshelf_speakers())
            } else {
                let path = base_dir.join("active_gear_headphone.json");
                if let Ok(content) = fs::read_to_string(&path) {
                    if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                        return Some(gear);
                    }
                }
                let legacy_path = base_dir.join("active_gear.json");
                if let Ok(content) = fs::read_to_string(&legacy_path) {
                    if let Ok(gear) = serde_json::from_str::<crate::dsp::enhancer::AcousticGearProfile>(&content) {
                        if gear.form_factor != crate::dsp::enhancer::GearFormFactor::BuiltinLaptopSpeakers
                            && gear.form_factor != crate::dsp::enhancer::GearFormFactor::DesktopBookshelfSpeakers
                        {
                            return Some(gear);
                        }
                    }
                }
                Some(crate::dsp::enhancer::AcousticGearProfile::default())
            }
        }
        _ => {
            load_active_gear_from_disk().or_else(|| Some(crate::dsp::enhancer::AcousticGearProfile::default()))
        }
    }
}

/// Save active acoustic gear profile to ~/.config/omnirip/active_gear.json (legacy wrapper).
pub fn save_active_gear_to_disk(gear: &crate::dsp::enhancer::AcousticGearProfile) -> Result<PathBuf, String> {
    save_gear_for_transducer(gear)
}

/// Load active acoustic gear profile from ~/.config/omnirip/active_gear.json (legacy wrapper).
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

/// Return the directory for storing user custom mastering presets (~/.config/omnirip/mastering_presets/).
pub fn get_mastering_presets_dir() -> PathBuf {
    let base = get_presets_dir().parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    let dir = base.join("mastering_presets");
    if !dir.exists() {
        let _ = fs::create_dir_all(&dir);
    }
    dir
}

/// Save a user mastering preset as JSON in ~/.config/omnirip/mastering_presets/.
pub fn save_mastering_preset_to_disk(preset: &crate::dsp::enhancer::MasteringPreset) -> Result<PathBuf, String> {
    let dir = get_mastering_presets_dir();
    let file_name = format!("{}.json", sanitize_filename(preset.name));
    let path = dir.join(file_name);

    let saved = crate::dsp::enhancer::SavedMasteringPreset::from_preset(preset);
    let json = serde_json::to_string_pretty(&saved)
        .map_err(|e| format!("Serialization error: {}", e))?;
    fs::write(&path, json).map_err(|e| format!("File write error: {}", e))?;
    Ok(path)
}

/// Load all user mastering presets from ~/.config/omnirip/mastering_presets/ and ~/.config/omnirip/presets/.
pub fn load_all_user_mastering_presets() -> Vec<crate::dsp::enhancer::MasteringPreset> {
    let mut results = Vec::new();
    let mut seen_names = std::collections::HashSet::new();

    // 1. Scan primary mastering presets directory (~/.config/omnirip/mastering_presets/)
    let dir = get_mastering_presets_dir();
    if let Ok(entries) = fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) == Some("json") {
                if let Ok(content) = fs::read_to_string(&path) {
                    if let Ok(saved) = serde_json::from_str::<crate::dsp::enhancer::SavedMasteringPreset>(&content) {
                        if seen_names.insert(saved.name.clone()) {
                            results.push(saved.to_mastering_preset());
                        }
                    } else if let Ok(omni) = serde_json::from_str::<OmniRipPreset>(&content) {
                        if seen_names.insert(omni.name.clone()) {
                            results.push(omni.to_mastering_preset());
                        }
                    }
                }
            }
        }
    }

    // 2. Also scan general presets directory (~/.config/omnirip/presets/)
    let presets_dir = get_presets_dir();
    if presets_dir.exists() && presets_dir != dir {
        if let Ok(entries) = fs::read_dir(&presets_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|ext| ext.to_str()) == Some("json") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Ok(saved) = serde_json::from_str::<crate::dsp::enhancer::SavedMasteringPreset>(&content) {
                            if seen_names.insert(saved.name.clone()) {
                                results.push(saved.to_mastering_preset());
                            }
                        } else if let Ok(omni) = serde_json::from_str::<OmniRipPreset>(&content) {
                            if seen_names.insert(omni.name.clone()) {
                                results.push(omni.to_mastering_preset());
                            }
                        }
                    }
                }
            }
        }
    }

    // Sort alphabetically by preset name
    results.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
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

    #[test]
    fn test_gear_transducer_filename_and_routing() {
        use crate::dsp::enhancer::{GearFormFactor, AcousticGearProfile};

        // Filename mapping
        assert_eq!(gear_filename_for_form_factor(GearFormFactor::BuiltinLaptopSpeakers), "active_gear_speaker.json");
        assert_eq!(gear_filename_for_form_factor(GearFormFactor::DesktopBookshelfSpeakers), "active_gear_bookshelf.json");
        assert_eq!(gear_filename_for_form_factor(GearFormFactor::InEar), "active_gear_headphone.json");
        assert_eq!(gear_filename_for_form_factor(GearFormFactor::OverEar), "active_gear_headphone.json");

        // Speaker default profile creation
        let spk = AcousticGearProfile::default_builtin_speakers("MacBook Pro");
        assert_eq!(spk.form_factor, GearFormFactor::BuiltinLaptopSpeakers);
        assert!(spk.name.contains("MacBook Pro"));

        let book = AcousticGearProfile::default_bookshelf_speakers();
        assert_eq!(book.form_factor, GearFormFactor::DesktopBookshelfSpeakers);
    }

    #[test]
    fn test_mastering_preset_roundtrip_and_storage() {
        use crate::dsp::enhancer::{MasteringPreset, SavedMasteringPreset};

        let presets = MasteringPreset::all();
        assert!(!presets.is_empty());
        let original = &presets[0];

        // 1. Serialization to SavedMasteringPreset
        let saved = SavedMasteringPreset::from_preset(original);
        assert_eq!(saved.name, original.name);
        assert_eq!(saved.spatial_width, original.spatial_width);
        assert_eq!(saved.eq_10_band, original.eq_10_band);

        // 2. JSON roundtrip
        let json = serde_json::to_string(&saved).expect("JSON serialization failed");
        let decoded: SavedMasteringPreset = serde_json::from_str(&json).expect("JSON deserialization failed");
        assert_eq!(decoded.name, saved.name);
        assert_eq!(decoded.tube_warmth, saved.tube_warmth);

        // 3. Conversion back to MasteringPreset
        let restored = decoded.to_mastering_preset();
        assert_eq!(restored.name, original.name);
        assert_eq!(restored.spatial_width, original.spatial_width);
        assert_eq!(restored.tube_warmth, original.tube_warmth);
        assert_eq!(restored.eq_10_band, original.eq_10_band);

        // 4. Test disk save
        let mut custom_preset = presets[0].clone();
        custom_preset.name = Box::leak("OmniRip Reference Mastering Test".to_string().into_boxed_str());
        custom_preset.description = Box::leak("Unit test reference mastering preset".to_string().into_boxed_str());
        custom_preset.spatial_width = 1.45;
        custom_preset.tube_warmth = 0.65;
        custom_preset.eq_10_band = [1.0, 1.5, 0.5, 0.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0];

        let saved_path = save_mastering_preset_to_disk(&custom_preset).expect("Failed to save mastering preset to disk");
        assert!(saved_path.exists());

        // Verify loaded user presets contains our saved custom preset
        let user_presets = load_all_user_mastering_presets();
        let found = user_presets.iter().find(|p| p.name == "OmniRip Reference Mastering Test");
        assert!(found.is_some(), "Saved custom preset should be present in loaded user mastering presets");
        let found_preset = found.unwrap();
        assert_eq!(found_preset.spatial_width, 1.45);
        assert_eq!(found_preset.tube_warmth, 0.65);
        assert_eq!(found_preset.eq_10_band[0], 1.0);
        assert_eq!(found_preset.eq_10_band[9], 2.0);

        // Clean up test file so tests don't leave artifacts
        let _ = std::fs::remove_file(saved_path);
    }
}
