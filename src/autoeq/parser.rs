//! AutoEQ and Squiglink Parametric EQ Text Parser in pure Rust.

use crate::dsp::biquad::{BiquadFilter, BiquadFilterType};

#[derive(Debug, Clone, PartialEq)]
pub struct ParametricProfile {
    pub name: String,
    pub preamp_db: f32,
    pub filters: Vec<BiquadFilter>,
}

pub fn parse_parametric_eq(name: &str, text: &str, sample_rate: f32) -> ParametricProfile {
    let mut preamp_db = 0.0f32;
    let mut filters = Vec::new();

    for line in text.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        let lower = trimmed.to_lowercase();
        if lower.starts_with("preamp:") {
            if let Some(val_str) = trimmed.split(':').nth(1) {
                let clean = val_str.replace("db", "").replace("dB", "");
                if let Ok(val) = clean.trim().parse::<f32>() {
                    preamp_db = val;
                }
            }
            continue;
        }

        // e.g.: "Filter 1: ON PK Fc 1000 Hz Gain -3.0 dB Q 1.41"
        if lower.starts_with("filter") {
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            let mut enabled = true;
            let mut filter_type = BiquadFilterType::Peaking;
            let mut freq = 1000.0f32;
            let mut gain_db = 0.0f32;
            let mut q = 1.414f32;

            let mut i = 0;
            while i < parts.len() {
                let p = parts[i];
                let p_up = p.to_uppercase();
                if p_up == "OFF" {
                    enabled = false;
                } else if p_up == "ON" {
                    enabled = true;
                } else if p_up == "PK" {
                    filter_type = BiquadFilterType::Peaking;
                } else if p_up == "LSC" || p_up == "LS" || p_up == "LOW_SHELF" {
                    filter_type = BiquadFilterType::LowShelf;
                } else if p_up == "HSC" || p_up == "HS" || p_up == "HIGH_SHELF" {
                    filter_type = BiquadFilterType::HighShelf;
                } else if p_up == "LP" || p_up == "LOW_PASS" {
                    filter_type = BiquadFilterType::LowPass;
                } else if p_up == "HP" || p_up == "HIGH_PASS" {
                    filter_type = BiquadFilterType::HighPass;
                } else if p_up == "FC" && i + 1 < parts.len() {
                    if let Ok(f) = parts[i + 1].parse::<f32>() {
                        freq = f;
                        i += 1;
                    }
                } else if p_up == "GAIN" && i + 1 < parts.len() {
                    if let Ok(g) = parts[i + 1].parse::<f32>() {
                        gain_db = g;
                        i += 1;
                    }
                } else if p_up == "Q" && i + 1 < parts.len() {
                    if let Ok(q_val) = parts[i + 1].parse::<f32>() {
                        q = q_val;
                        i += 1;
                    }
                }
                i += 1;
            }

            let mut filter = BiquadFilter::new(filter_type, freq, gain_db, q, sample_rate);
            filter.enabled = enabled;
            filters.push(filter);
        }
    }

    ParametricProfile {
        name: name.to_string(),
        preamp_db,
        filters,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_autoeq_profile() {
        let text = "
Preamp: -4.5 dB
Filter 1: ON PK Fc 28 Hz Gain -4.2 dB Q 1.41
Filter 2: ON LSC Fc 105 Hz Gain 5.5 dB Q 0.71
Filter 3: OFF PK Fc 250 Hz Gain -1.0 dB Q 2.0
Filter 4: ON HSC Fc 10000 Hz Gain -2.0 dB Q 0.71
";
        let profile = parse_parametric_eq("HD600", text, 48000.0);
        assert_eq!(profile.name, "HD600");
        assert!((profile.preamp_db - (-4.5)).abs() < 1e-3);
        assert_eq!(profile.filters.len(), 4);
        assert_eq!(profile.filters[0].filter_type, BiquadFilterType::Peaking);
        assert_eq!(profile.filters[1].filter_type, BiquadFilterType::LowShelf);
        assert!(!profile.filters[2].enabled);
        assert_eq!(profile.filters[3].filter_type, BiquadFilterType::HighShelf);
    }
}
