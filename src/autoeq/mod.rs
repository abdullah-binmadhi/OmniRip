//! Headphone Preset Profiles and Target Curve Database.

pub mod parser;
pub mod storage;
pub use parser::{parse_parametric_eq, ParametricProfile};
pub use storage::{
    download_raw_preset, load_all_user_mastering_presets, load_all_user_presets,
    save_mastering_preset_to_disk, save_preset_to_disk, OmniRipPreset,
};

/// Return bundled headphone and audiophile reference profiles.
pub fn get_bundled_profiles(sample_rate: f32) -> Vec<ParametricProfile> {
    vec![
        parse_parametric_eq(
            "Flat / Neutral Baseline (Default 0 dB)",
            "
Preamp: 0.0 dB
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Harman Target 2019 (Over-Ear Reference)",
            "
Preamp: -5.5 dB
Filter 1: ON LSC Fc 105 Hz Gain 5.5 dB Q 0.71
Filter 2: ON PK Fc 200 Hz Gain -1.5 dB Q 1.41
Filter 3: ON PK Fc 1200 Hz Gain -2.0 dB Q 2.0
Filter 4: ON PK Fc 3000 Hz Gain 3.0 dB Q 1.41
Filter 5: ON HSC Fc 10000 Hz Gain 1.5 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Crinacle IEF Neutral v2",
            "
Preamp: -3.0 dB
Filter 1: ON LSC Fc 80 Hz Gain 3.0 dB Q 0.71
Filter 2: ON PK Fc 1500 Hz Gain -1.0 dB Q 1.5
Filter 3: ON PK Fc 2800 Hz Gain 2.0 dB Q 2.0
Filter 4: ON HSC Fc 8000 Hz Gain -1.5 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Sennheiser HD 600 (Harman Compensation)",
            "
Preamp: -6.0 dB
Filter 1: ON LSC Fc 80 Hz Gain 6.0 dB Q 0.71
Filter 2: ON PK Fc 45 Hz Gain 2.5 dB Q 1.41
Filter 3: ON PK Fc 3200 Hz Gain -2.0 dB Q 2.5
Filter 4: ON PK Fc 6000 Hz Gain 1.5 dB Q 3.0
Filter 5: ON HSC Fc 11000 Hz Gain 2.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Sennheiser HD 650 / HD 6XX",
            "
Preamp: -5.0 dB
Filter 1: ON LSC Fc 75 Hz Gain 5.0 dB Q 0.71
Filter 2: ON PK Fc 200 Hz Gain -1.0 dB Q 1.2
Filter 3: ON PK Fc 3100 Hz Gain -1.5 dB Q 2.0
Filter 4: ON PK Fc 5800 Hz Gain 2.0 dB Q 2.5
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Sennheiser HD 800 S",
            "
Preamp: -5.5 dB
Filter 1: ON LSC Fc 100 Hz Gain 5.5 dB Q 0.71
Filter 2: ON PK Fc 5800 Hz Gain -4.5 dB Q 4.0
Filter 3: ON PK Fc 9500 Hz Gain -2.0 dB Q 3.0
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Hifiman Sundara (Planar Neutral)",
            "
Preamp: -4.0 dB
Filter 1: ON LSC Fc 70 Hz Gain 4.0 dB Q 0.71
Filter 2: ON PK Fc 2100 Hz Gain 2.0 dB Q 1.5
Filter 3: ON PK Fc 6000 Hz Gain -2.0 dB Q 3.0
Filter 4: ON PK Fc 9000 Hz Gain -3.0 dB Q 3.5
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Hifiman Edition XS",
            "
Preamp: -4.5 dB
Filter 1: ON LSC Fc 85 Hz Gain 4.5 dB Q 0.71
Filter 2: ON PK Fc 1800 Hz Gain 2.5 dB Q 1.8
Filter 3: ON PK Fc 3500 Hz Gain -2.0 dB Q 2.5
Filter 4: ON PK Fc 7000 Hz Gain -3.0 dB Q 4.0
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Moondrop Blessing 2 / Dusk",
            "
Preamp: -3.0 dB
Filter 1: ON LSC Fc 105 Hz Gain 3.0 dB Q 0.71
Filter 2: ON PK Fc 5800 Hz Gain -2.5 dB Q 3.0
Filter 3: ON PK Fc 8000 Hz Gain -2.0 dB Q 2.5
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Sony WH-1000XM5 (Clarity & Tamed Bass)",
            "
Preamp: -2.0 dB
Filter 1: ON PK Fc 150 Hz Gain -4.0 dB Q 1.0
Filter 2: ON PK Fc 1200 Hz Gain 2.5 dB Q 1.5
Filter 3: ON PK Fc 4000 Hz Gain 3.0 dB Q 2.0
Filter 4: ON HSC Fc 10000 Hz Gain 2.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Apple AirPods Max (Audiophile Flattening)",
            "
Preamp: -3.0 dB
Filter 1: ON PK Fc 250 Hz Gain -2.0 dB Q 1.2
Filter 2: ON PK Fc 3000 Hz Gain 2.5 dB Q 2.0
Filter 3: ON PK Fc 6200 Hz Gain -2.0 dB Q 3.0
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Beyerdynamic DT 990 Pro (Treble Tame)",
            "
Preamp: -5.0 dB
Filter 1: ON LSC Fc 90 Hz Gain 5.0 dB Q 0.71
Filter 2: ON PK Fc 5900 Hz Gain -5.5 dB Q 3.5
Filter 3: ON PK Fc 8500 Hz Gain -6.0 dB Q 4.0
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Hip-Hop & Trap (Sub-Bass Precision)",
            "
Preamp: -4.0 dB
Filter 1: ON LSC Fc 60 Hz Gain 4.0 dB Q 0.71
Filter 2: ON PK Fc 250 Hz Gain -1.5 dB Q 1.8
Filter 3: ON PK Fc 1500 Hz Gain 1.0 dB Q 2.0
Filter 4: ON PK Fc 6800 Hz Gain -1.5 dB Q 3.0
Filter 5: ON HSC Fc 12000 Hz Gain 2.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: R&B & Neo-Soul (Velvet Vocal Intimacy)",
            "
Preamp: -3.0 dB
Filter 1: ON LSC Fc 80 Hz Gain 3.0 dB Q 0.71
Filter 2: ON PK Fc 500 Hz Gain 1.0 dB Q 1.5
Filter 3: ON PK Fc 2200 Hz Gain 1.5 dB Q 2.0
Filter 4: ON HSC Fc 10000 Hz Gain 2.5 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Rock & Heavy Metal (Punch & Anti-Fatigue)",
            "
Preamp: -3.5 dB
Filter 1: ON LSC Fc 85 Hz Gain 3.0 dB Q 0.71
Filter 2: ON PK Fc 1200 Hz Gain 1.8 dB Q 1.5
Filter 3: ON PK Fc 3500 Hz Gain -2.0 dB Q 3.0
Filter 4: ON PK Fc 6500 Hz Gain -2.5 dB Q 3.5
Filter 5: ON HSC Fc 11000 Hz Gain 1.5 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Electronic & Club (Subterranean 3D)",
            "
Preamp: -4.5 dB
Filter 1: ON LSC Fc 55 Hz Gain 4.5 dB Q 0.71
Filter 2: ON PK Fc 220 Hz Gain -1.2 dB Q 1.5
Filter 3: ON PK Fc 3500 Hz Gain 1.5 dB Q 2.0
Filter 4: ON HSC Fc 12000 Hz Gain 3.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Pop & Mainstream (Harman 2024 Reference)",
            "
Preamp: -4.0 dB
Filter 1: ON LSC Fc 105 Hz Gain 4.0 dB Q 0.71
Filter 2: ON PK Fc 200 Hz Gain -1.0 dB Q 1.41
Filter 3: ON PK Fc 2500 Hz Gain 2.0 dB Q 2.0
Filter 4: ON HSC Fc 10000 Hz Gain 2.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Classical & Orchestral (Symphonic Hall)",
            "
Preamp: -2.0 dB
Filter 1: ON LSC Fc 60 Hz Gain 1.5 dB Q 0.71
Filter 2: ON PK Fc 3200 Hz Gain -1.5 dB Q 3.0
Filter 3: ON HSC Fc 10000 Hz Gain 2.5 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Jazz & Acoustic Trio (Living Room Hologram)",
            "
Preamp: -2.0 dB
Filter 1: ON LSC Fc 90 Hz Gain 2.0 dB Q 0.71
Filter 2: ON PK Fc 1800 Hz Gain 1.2 dB Q 1.8
Filter 3: ON HSC Fc 10000 Hz Gain 2.0 dB Q 0.71
",
            sample_rate,
        ),
        parse_parametric_eq(
            "Genre: Ambient & Cinematic (Panoramic Drone Space)",
            "
Preamp: -3.5 dB
Filter 1: ON LSC Fc 45 Hz Gain 3.5 dB Q 0.71
Filter 2: ON PK Fc 3600 Hz Gain -1.8 dB Q 2.5
Filter 3: ON HSC Fc 10000 Hz Gain 3.0 dB Q 0.71
",
            sample_rate,
        ),
    ]
}
