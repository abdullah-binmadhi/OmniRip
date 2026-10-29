//! Persistent Volume Safety & Calibration Engine
//!
//! Preserves user-configured audio player volume percentage and system CoreAudio hardware volume
//! across app launches, updates, and mode switches, preventing accidental 100% volume blasts.

use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;

const DEFAULT_PLAYER_VOLUME_PCT: usize = 50;
const DEFAULT_SYSTEM_VOLUME_SCALAR: f32 = 0.5;

fn default_false() -> bool {
    false
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolumeConfig {
    pub player_volume_pct: usize,
    pub system_volume_scalar: f32,
    #[serde(default = "default_false")]
    pub mic_enabled: bool,
    #[serde(default)]
    pub dac_flavor: Option<super::enhancer::DacHardwareFlavor>,
}

impl Default for VolumeConfig {
    fn default() -> Self {
        Self {
            player_volume_pct: DEFAULT_PLAYER_VOLUME_PCT,
            system_volume_scalar: DEFAULT_SYSTEM_VOLUME_SCALAR,
            mic_enabled: false,
            dac_flavor: Some(super::enhancer::DacHardwareFlavor::StockOemPlus),
        }
    }
}

pub fn volume_config_path() -> PathBuf {
    #[cfg(test)]
    {
        return std::env::temp_dir().join(format!("omnirip_test_vol_{}_{:?}.json", std::process::id(), std::thread::current().id()));
    }
    #[allow(unreachable_code)]
    if let Ok(home) = std::env::var("HOME") {
        PathBuf::from(home).join(".config").join("omnirip").join("volume.json")
    } else if let Ok(profile) = std::env::var("USERPROFILE") {
        PathBuf::from(profile).join(".config").join("omnirip").join("volume.json")
    } else {
        PathBuf::from(".config/omnirip/volume.json")
    }
}

/// Loads persistent volume settings from disk. If missing or invalid, falls back to safe 50% defaults.
pub fn load_volume_settings() -> (usize, f32) {
    let path = volume_config_path();
    if !path.exists() {
        return (DEFAULT_PLAYER_VOLUME_PCT, DEFAULT_SYSTEM_VOLUME_SCALAR);
    }

    if let Ok(mut file) = File::open(&path) {
        let mut contents = String::new();
        if file.read_to_string(&mut contents).is_ok() {
            if let Ok(cfg) = serde_json::from_str::<VolumeConfig>(&contents) {
                let safe_pct = cfg.player_volume_pct.clamp(0, 100);
                let safe_scalar = cfg.system_volume_scalar.clamp(0.0, 1.0);
                return (safe_pct, safe_scalar);
            }
        }
    }

    (DEFAULT_PLAYER_VOLUME_PCT, DEFAULT_SYSTEM_VOLUME_SCALAR)
}

/// Loads persistent mic input capture setting from disk. Defaults to false (OFF) to ensure mic hardware is not held on startup.
pub fn load_mic_setting() -> bool {
    let path = volume_config_path();
    if !path.exists() {
        return false;
    }

    if let Ok(mut file) = File::open(&path) {
        let mut contents = String::new();
        if file.read_to_string(&mut contents).is_ok() {
            if let Ok(cfg) = serde_json::from_str::<VolumeConfig>(&contents) {
                return cfg.mic_enabled;
            }
        }
    }

    false
}

/// Loads persistent DAC Mimicker flavor from disk. Defaults to StockOemPlus.
pub fn load_dac_flavor_setting() -> super::enhancer::DacHardwareFlavor {
    let path = volume_config_path();
    if !path.exists() {
        return super::enhancer::DacHardwareFlavor::StockOemPlus;
    }

    if let Ok(mut file) = File::open(&path) {
        let mut contents = String::new();
        if file.read_to_string(&mut contents).is_ok() {
            if let Ok(cfg) = serde_json::from_str::<VolumeConfig>(&contents) {
                return cfg.dac_flavor.unwrap_or(super::enhancer::DacHardwareFlavor::StockOemPlus);
            }
        }
    }

    super::enhancer::DacHardwareFlavor::StockOemPlus
}

/// Saves current volume levels to disk preserving mic setting and DAC flavor.
pub fn save_volume_settings(player_pct: usize, sys_scalar: f32) {
    let current_mic = load_mic_setting();
    let current_flavor = load_dac_flavor_setting();
    let path = volume_config_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let cfg = VolumeConfig {
        player_volume_pct: player_pct.clamp(0, 100),
        system_volume_scalar: sys_scalar.clamp(0.0, 1.0),
        mic_enabled: current_mic,
        dac_flavor: Some(current_flavor),
    };

    if let Ok(json) = serde_json::to_string_pretty(&cfg) {
        if let Ok(mut file) = File::create(&path) {
            let _ = file.write_all(json.as_bytes());
        }
    }
}

/// Saves persistent mic capture setting to disk.
pub fn save_mic_setting(enabled: bool) {
    let (player_pct, sys_scalar) = load_volume_settings();
    let current_flavor = load_dac_flavor_setting();
    let path = volume_config_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let cfg = VolumeConfig {
        player_volume_pct: player_pct.clamp(0, 100),
        system_volume_scalar: sys_scalar.clamp(0.0, 1.0),
        mic_enabled: enabled,
        dac_flavor: Some(current_flavor),
    };

    if let Ok(json) = serde_json::to_string_pretty(&cfg) {
        if let Ok(mut file) = File::create(&path) {
            let _ = file.write_all(json.as_bytes());
        }
    }
}

/// Saves persistent DAC Mimicker flavor to disk.
pub fn save_dac_flavor_setting(flavor: super::enhancer::DacHardwareFlavor) {
    let (player_pct, sys_scalar) = load_volume_settings();
    let current_mic = load_mic_setting();
    let path = volume_config_path();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let cfg = VolumeConfig {
        player_volume_pct: player_pct.clamp(0, 100),
        system_volume_scalar: sys_scalar.clamp(0.0, 1.0),
        mic_enabled: current_mic,
        dac_flavor: Some(flavor),
    };

    if let Ok(json) = serde_json::to_string_pretty(&cfg) {
        if let Ok(mut file) = File::create(&path) {
            let _ = file.write_all(json.as_bytes());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_volume_config_serialization_and_defaults() {
        let default_cfg = VolumeConfig::default();
        assert_eq!(default_cfg.player_volume_pct, 50);
        assert!((default_cfg.system_volume_scalar - 0.5).abs() < 1e-4);
        assert!(!default_cfg.mic_enabled);

        let json = serde_json::to_string(&default_cfg).unwrap();
        let deserialized: VolumeConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.player_volume_pct, 50);
        assert!(!deserialized.mic_enabled);
        assert_eq!(deserialized.dac_flavor, Some(crate::dsp::enhancer::DacHardwareFlavor::StockOemPlus));
    }
}
