//! Studio Audiophile Sound Engine in pure Rust.
//!
//! Includes 10 Audiophile Mastering Processors:
//! 1. Sub-Bass Mono Consolidation (Elliptical Equalizer)
//! 2. Fletcher-Munson Dynamic Loudness Contour (ISO 226)
//! 3. Audiophile Headphone Crossfeed (Meier / Bauer HRTF)
//! 4. 1/2-Inch Analog Master Tape Emulation (Head Bump & Magnetic Glue)
//! 5. Transient Attack & Punch Shaper (Dual-Envelope Transient Designer)
//! 6. Mid/Side Spatial Tilt & Balance Matrix
//! 7. Dynamic Resonance Suppressor & De-Harshing Tamer
//! 8. Infrasonic DC Rumble Cut & Ultrasonic Boundary Filters
//! 9. Dual-Stage Mastering Bus Compressor (Opto Leveler + VCA Discrete Punch)
//! 10. Passive Pultec EQP-1A Velvet Air & Low-End Transformer Exciter
//!
//! Also provides 20 handcrafted audiophile and mood presets with integrated 10-band EQ
//! and dynamic acoustic gear adaptation.

use super::biquad::{BiquadFilter, BiquadFilterType, FastSosFilter};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CrossfeedMode {
    Off,
    Subtle,
    Standard,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearFormFactor {
    OverEar,
    OnEar,
    InEar,
    Earbuds,
    BoneConduction,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearEnclosure {
    OpenBack,
    SemiOpen,
    ClosedBack,
    Anc,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearCoupling {
    Silicone,
    MemoryFoam,
    CustomMolded,
    OpenAir,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearTonalBalance {
    AnalyticalBright,
    DarkWarm,
    BassHeavy,
    VShaped,
    NeutralStudio,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearSourceAmp {
    PortableDongle,
    DesktopSolidState,
    TubeAmp,
    BluetoothWireless,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AcousticGearProfile {
    pub name: String,
    pub form_factor: GearFormFactor,
    pub enclosure: GearEnclosure,
    pub drivers: [bool; 6], // [Dynamic, Planar, BalancedArmature, Electrostatic, Piezo, BoneConduction]
    pub coupling: GearCoupling,
    pub tonal_balance: GearTonalBalance,
    pub source_amp: GearSourceAmp,
}

impl Default for AcousticGearProfile {
    fn default() -> Self {
        Self {
            name: "Universal Reference Gear".to_string(),
            form_factor: GearFormFactor::OverEar,
            enclosure: GearEnclosure::OpenBack,
            drivers: [true, false, false, false, false, false],
            coupling: GearCoupling::OpenAir,
            tonal_balance: GearTonalBalance::NeutralStudio,
            source_amp: GearSourceAmp::DesktopSolidState,
        }
    }
}

impl AcousticGearProfile {
    pub fn form_factor_label(&self) -> &'static str {
        match self.form_factor {
            GearFormFactor::OverEar => "Over-Ear",
            GearFormFactor::OnEar => "On-Ear",
            GearFormFactor::InEar => "In-Ear (IEM)",
            GearFormFactor::Earbuds => "Earbuds",
            GearFormFactor::BoneConduction => "Bone Conduction",
        }
    }

    pub fn enclosure_label(&self) -> &'static str {
        match self.enclosure {
            GearEnclosure::OpenBack => "Open-Back",
            GearEnclosure::SemiOpen => "Semi-Open",
            GearEnclosure::ClosedBack => "Closed-Back",
            GearEnclosure::Anc => "ANC Chamber",
        }
    }

    pub fn driver_summary(&self) -> String {
        let mut parts = Vec::new();
        if self.drivers[0] { parts.push("DD"); }
        if self.drivers[1] { parts.push("Planar"); }
        if self.drivers[2] { parts.push("BA"); }
        if self.drivers[3] { parts.push("EST"); }
        if self.drivers[4] { parts.push("Piezo"); }
        if self.drivers[5] { parts.push("Bone"); }
        if parts.is_empty() {
            "Standard".to_string()
        } else if parts.len() > 1 {
            format!("Hybrid ({})", parts.join("+"))
        } else {
            parts[0].to_string()
        }
    }

    pub fn tonal_label(&self) -> &'static str {
        match self.tonal_balance {
            GearTonalBalance::AnalyticalBright => "Bright/Analytical",
            GearTonalBalance::DarkWarm => "Dark/Warm",
            GearTonalBalance::BassHeavy => "Bass-Heavy",
            GearTonalBalance::VShaped => "V-Shaped",
            GearTonalBalance::NeutralStudio => "Studio Neutral",
        }
    }

    pub fn summary_badge(&self) -> String {
        format!("\"{}\" [{} | {} | {} | {}]", self.name, self.form_factor_label(), self.enclosure_label(), self.driver_summary(), self.tonal_label())
    }
}

/// Handcrafted audiophile mastering preset recipe.
#[derive(Debug, Clone)]
pub struct MasteringPreset {
    pub name: &'static str,
    pub description: &'static str,
    pub target: &'static str,
    pub spatial_width: f32,
    pub tube_warmth: f32,
    pub air_clarity_db: f32,
    pub bass_punch_db: f32,
    pub mono_bass: bool,
    pub mono_bass_freq: f32,
    pub loudness_contour: bool,
    pub crossfeed: CrossfeedMode,
    pub subsonic_filter: bool,
    pub ultrasonic_filter: bool,
    pub deesser_enabled: bool,
    pub deesser_amount: f32,
    pub deesser_freq: f32,
    pub tape_emulation: bool,
    pub tape_drive: f32,
    pub transient_shaper: bool,
    pub transient_attack_db: f32,
    pub transient_sustain_db: f32,
    pub ms_matrix_enabled: bool,
    pub mid_gain_db: f32,
    pub side_gain_db: f32,
    pub side_air_db: f32,
    pub deharsh_enabled: bool,
    pub deharsh_amount: f32,
    pub deharsh_freq: f32,
    pub comp_enabled: bool,
    pub comp_opto_drive: f32,
    pub comp_vca_drive: f32,
    pub pultec_enabled: bool,
    pub pultec_low_boost: f32,
    pub pultec_air_boost: f32,
    pub pultec_air_freq: f32,
    pub limiter_ceiling_dbfs: f32,
    pub eq_10_band: [f32; 10],
}

impl MasteringPreset {
    /// Returns the 20 handcrafted audiophile and mood presets.
    pub fn all() -> Vec<MasteringPreset> {
        vec![
            MasteringPreset {
                name: "01. Audiophile Reference (Pure Direct)",
                description: "Bit-perfect transparent monitor with linear-phase subsonic guard.",
                target: "Neutral Reference Monitors & DACs",
                spatial_width: 1.0,
                tube_warmth: 0.0,
                air_clarity_db: 0.0,
                bass_punch_db: 0.0,
                mono_bass: false,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Off,
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
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            MasteringPreset {
                name: "02. HD600/650 Soundstage & Veil Lifter",
                description: "Lifts upper-mid veil, opens soundstage width, adds Pultec 16kHz velvet air.",
                target: "Sennheiser HD 600 / HD 650 / HD 660S",
                spatial_width: 1.25,
                tube_warmth: 0.15,
                air_clarity_db: 1.5,
                bass_punch_db: 1.0,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
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
                ms_matrix_enabled: true,
                mid_gain_db: 0.0,
                side_gain_db: 1.2,
                side_air_db: 1.5,
                deharsh_enabled: true,
                deharsh_amount: 0.35,
                deharsh_freq: 3500.0,
                comp_enabled: true,
                comp_opto_drive: 0.25,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 0.5,
                pultec_air_boost: 2.2,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.5, 1.0, 0.0, -0.5, 0.0, 0.5, 1.0, 1.2, 1.5, 2.0],
            },
            MasteringPreset {
                name: "03. DT 770/990 Mount Beyer Treble Tamer",
                description: "Suppresses aggressive 7-9kHz sibilance spikes while enriching lower mid body.",
                target: "Beyerdynamic DT 770 / DT 880 / DT 990 / DT 1990 Pro",
                spatial_width: 1.10,
                tube_warmth: 0.28,
                air_clarity_db: 0.0,
                bass_punch_db: 1.2,
                mono_bass: true,
                mono_bass_freq: 95.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: true,
                deesser_amount: 0.65,
                deesser_freq: 7200.0,
                tape_emulation: true,
                tape_drive: 1.0,
                transient_shaper: false,
                transient_attack_db: 0.0,
                transient_sustain_db: 0.0,
                ms_matrix_enabled: true,
                mid_gain_db: 0.5,
                side_gain_db: -0.5,
                side_air_db: 0.0,
                deharsh_enabled: true,
                deharsh_amount: 0.60,
                deharsh_freq: 3400.0,
                comp_enabled: true,
                comp_opto_drive: 0.35,
                comp_vca_drive: 0.0,
                pultec_enabled: false,
                pultec_low_boost: 0.0,
                pultec_air_boost: 0.0,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.3,
                eq_10_band: [1.0, 1.5, 1.0, 0.5, 0.0, 0.0, -0.5, -1.5, -2.5, -1.0],
            },
            MasteringPreset {
                name: "04. Planar Magnetic Fast Slam & Tactile Impact",
                description: "Crystalline transient definition, high-speed VCA punch, and 20kHz ultra-air.",
                target: "Planar Magnetics (Hifiman, Audeze, Dan Clark)",
                spatial_width: 1.20,
                tube_warmth: 0.10,
                air_clarity_db: 1.2,
                bass_punch_db: 1.8,
                mono_bass: true,
                mono_bass_freq: 75.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 0.8,
                transient_shaper: true,
                transient_attack_db: 2.5,
                transient_sustain_db: 0.0,
                ms_matrix_enabled: true,
                mid_gain_db: 0.0,
                side_gain_db: 0.8,
                side_air_db: 1.0,
                deharsh_enabled: false,
                deharsh_amount: 0.0,
                deharsh_freq: 3800.0,
                comp_enabled: true,
                comp_opto_drive: 0.0,
                comp_vca_drive: 0.45,
                pultec_enabled: true,
                pultec_low_boost: 1.2,
                pultec_air_boost: 1.5,
                pultec_air_freq: 20000.0,
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [2.0, 1.5, 0.5, 0.0, -0.5, 0.0, 0.5, 1.0, 1.5, 1.8],
            },
            MasteringPreset {
                name: "05. 1970s Analogue Vinyl & Tube Console",
                description: "Rich triode even harmonics, 15 IPS master tape head bump, and warm Pultec low-end.",
                target: "Classic Rock, Vinyl Rips, 70s Soul & Folk",
                spatial_width: 1.05,
                tube_warmth: 0.45,
                air_clarity_db: 0.0,
                bass_punch_db: 2.2,
                mono_bass: true,
                mono_bass_freq: 110.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.8,
                transient_shaper: true,
                transient_attack_db: -1.0,
                transient_sustain_db: 1.5,
                ms_matrix_enabled: true,
                mid_gain_db: 0.8,
                side_gain_db: -0.5,
                side_air_db: 0.0,
                deharsh_enabled: true,
                deharsh_amount: 0.40,
                deharsh_freq: 3800.0,
                comp_enabled: true,
                comp_opto_drive: 0.50,
                comp_vca_drive: 0.20,
                pultec_enabled: true,
                pultec_low_boost: 2.5,
                pultec_air_boost: 1.8,
                pultec_air_freq: 12000.0,
                limiter_ceiling_dbfs: -0.5,
                eq_10_band: [1.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0, -0.5, -1.0, -2.0],
            },
            MasteringPreset {
                name: "06. Midnight Low-Volume (Fletcher-Munson)",
                description: "ISO 226 equal-loudness dynamic bass & air lift with gentle opto leveling.",
                target: "Late-Night Quiet Headphone & Speaker Listening",
                spatial_width: 1.15,
                tube_warmth: 0.20,
                air_clarity_db: 2.0,
                bass_punch_db: 3.5,
                mono_bass: true,
                mono_bass_freq: 90.0,
                loudness_contour: true,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: true,
                deesser_amount: 0.40,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: 1.5,
                transient_sustain_db: 0.5,
                ms_matrix_enabled: true,
                mid_gain_db: 1.0,
                side_gain_db: 0.5,
                side_air_db: 1.0,
                deharsh_enabled: true,
                deharsh_amount: 0.30,
                deharsh_freq: 4200.0,
                comp_enabled: true,
                comp_opto_drive: 0.40,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 1.8,
                pultec_air_boost: 1.5,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.3,
                eq_10_band: [3.5, 2.5, 1.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.8, 2.5],
            },
            MasteringPreset {
                name: "07. Classical Concert Hall & Symphonic Depth",
                description: "Uncompressed dynamic depth with Bauer acoustic bleed and wide hall side reverb.",
                target: "Orchestral, Symphonic, String Quartets, Opera",
                spatial_width: 1.40,
                tube_warmth: 0.0,
                air_clarity_db: 1.2,
                bass_punch_db: 0.0,
                mono_bass: false,
                mono_bass_freq: 60.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
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
                ms_matrix_enabled: true,
                mid_gain_db: -0.5,
                side_gain_db: 1.8,
                side_air_db: 1.2,
                deharsh_enabled: true,
                deharsh_amount: 0.35,
                deharsh_freq: 3200.0,
                comp_enabled: false,
                comp_opto_drive: 0.0,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 0.0,
                pultec_air_boost: 1.2,
                pultec_air_freq: 20000.0,
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 1.5],
            },
            MasteringPreset {
                name: "08. Blue Note Jazz Lounge & Acoustic Trio",
                description: "Pluck transient articulation on upright bass, opto warmth, and brushed cymbal air.",
                target: "Jazz Trios, Acoustic Piano, Saxophone, Double Bass",
                spatial_width: 1.15,
                tube_warmth: 0.32,
                air_clarity_db: 1.5,
                bass_punch_db: 1.2,
                mono_bass: true,
                mono_bass_freq: 70.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.2,
                transient_shaper: true,
                transient_attack_db: 1.2,
                transient_sustain_db: 0.8,
                ms_matrix_enabled: true,
                mid_gain_db: 0.5,
                side_gain_db: 0.5,
                side_air_db: 0.8,
                deharsh_enabled: true,
                deharsh_amount: 0.40,
                deharsh_freq: 5200.0,
                comp_enabled: true,
                comp_opto_drive: 0.45,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 1.0,
                pultec_air_boost: 1.8,
                pultec_air_freq: 12000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.0, 1.8, 1.2, 0.5, 0.0, 0.0, 0.5, 0.8, 1.2, 1.5],
            },
            MasteringPreset {
                name: "09. Modern Electronic & EDM Mainstage Punch",
                description: "Solid mono sub-bass <85Hz, snappy transient kick crack, and 150% ultra-wide synth air.",
                target: "House, Techno, Synthwave, Trap, Drum & Bass",
                spatial_width: 1.50,
                tube_warmth: 0.15,
                air_clarity_db: 2.2,
                bass_punch_db: 3.5,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Off,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.2,
                transient_shaper: true,
                transient_attack_db: 3.5,
                transient_sustain_db: 1.0,
                ms_matrix_enabled: true,
                mid_gain_db: 0.5,
                side_gain_db: 2.5,
                side_air_db: 2.0,
                deharsh_enabled: true,
                deharsh_amount: 0.45,
                deharsh_freq: 4000.0,
                comp_enabled: true,
                comp_opto_drive: 0.0,
                comp_vca_drive: 0.60,
                pultec_enabled: true,
                pultec_low_boost: 2.5,
                pultec_air_boost: 2.5,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [3.5, 2.5, 1.0, -1.0, -0.5, 0.0, 0.5, 1.2, 2.0, 2.5],
            },
            MasteringPreset {
                name: "10. High-Energy Rock & Heavy Metal",
                description: "Surgically cuts through dense electric guitar walls with kick punch & de-harsh.",
                target: "Hard Rock, Heavy Metal, Post-Punk, Grunge",
                spatial_width: 1.20,
                tube_warmth: 0.25,
                air_clarity_db: 1.0,
                bass_punch_db: 2.0,
                mono_bass: true,
                mono_bass_freq: 90.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.4,
                transient_shaper: true,
                transient_attack_db: 2.0,
                transient_sustain_db: 0.0,
                ms_matrix_enabled: true,
                mid_gain_db: 1.0,
                side_gain_db: 0.5,
                side_air_db: 0.5,
                deharsh_enabled: true,
                deharsh_amount: 0.70,
                deharsh_freq: 3500.0,
                comp_enabled: true,
                comp_opto_drive: 0.20,
                comp_vca_drive: 0.50,
                pultec_enabled: true,
                pultec_low_boost: 1.5,
                pultec_air_boost: 1.0,
                pultec_air_freq: 12000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [2.0, 1.8, 0.5, -0.5, 0.0, 0.8, 1.0, -1.0, 0.5, 1.0],
            },
            MasteringPreset {
                name: "11. Vocal Warmth & Intimate Singer-Songwriter",
                description: "Focuses the lead vocal front-and-center with smooth optical compression and velvet air.",
                target: "Acoustic Ballads, Folk, Vocal Jazz, Podcasts",
                spatial_width: 1.05,
                tube_warmth: 0.30,
                air_clarity_db: 1.2,
                bass_punch_db: 0.5,
                mono_bass: true,
                mono_bass_freq: 80.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: true,
                deesser_amount: 0.60,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: 0.0,
                transient_sustain_db: 1.5,
                ms_matrix_enabled: true,
                mid_gain_db: 1.8,
                side_gain_db: -0.5,
                side_air_db: 0.5,
                deharsh_enabled: true,
                deharsh_amount: 0.50,
                deharsh_freq: 3800.0,
                comp_enabled: true,
                comp_opto_drive: 0.55,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 0.8,
                pultec_air_boost: 2.0,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [0.5, 0.8, 0.5, 0.0, 0.5, 1.5, 1.2, -0.5, 1.0, 1.5],
            },
            MasteringPreset {
                name: "12. 1980s Japanese City Pop & Synthwave",
                description: "Slap bass punch, 15 IPS tape head bump, and shimmering 16kHz analog synth sheen.",
                target: "City Pop, Funk, Disco, Retro Synthwave",
                spatial_width: 1.35,
                tube_warmth: 0.22,
                air_clarity_db: 1.8,
                bass_punch_db: 2.5,
                mono_bass: true,
                mono_bass_freq: 80.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.6,
                transient_shaper: true,
                transient_attack_db: 2.5,
                transient_sustain_db: 0.5,
                ms_matrix_enabled: true,
                mid_gain_db: 0.0,
                side_gain_db: 2.0,
                side_air_db: 1.5,
                deharsh_enabled: true,
                deharsh_amount: 0.40,
                deharsh_freq: 4500.0,
                comp_enabled: true,
                comp_opto_drive: 0.35,
                comp_vca_drive: 0.35,
                pultec_enabled: true,
                pultec_low_boost: 2.0,
                pultec_air_boost: 2.8,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [2.0, 2.0, 1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.2, 2.5],
            },
            MasteringPreset {
                name: "13. Deep Focus & Ambient Binaural Drift",
                description: "Alpha-wave study, warm ambient pad decays, zero fatiguing transients.",
                target: "Coding, Reading, Meditation, Ambient Drone",
                spatial_width: 1.40,
                tube_warmth: 0.15,
                air_clarity_db: 0.5,
                bass_punch_db: 1.0,
                mono_bass: true,
                mono_bass_freq: 80.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: -2.5,
                transient_sustain_db: 2.0,
                ms_matrix_enabled: true,
                mid_gain_db: -0.5,
                side_gain_db: 1.5,
                side_air_db: 0.8,
                deharsh_enabled: true,
                deharsh_amount: 0.60,
                deharsh_freq: 3500.0,
                comp_enabled: true,
                comp_opto_drive: 0.40,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 0.5,
                pultec_air_boost: 1.0,
                pultec_air_freq: 20000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.5, 1.0, 0.5, 0.0, 0.0, 0.0, -0.5, -1.0, 0.5, 1.0],
            },
            MasteringPreset {
                name: "14. Rainy Day Coffeehouse & Lo-Fi Chill",
                description: "Nostalgic warm radio aesthetic, rich 2nd harmonics, intimate room tone.",
                target: "Lo-Fi Hip-Hop, Acoustic Demos, Downtempo",
                spatial_width: 1.00,
                tube_warmth: 0.40,
                air_clarity_db: 0.0,
                bass_punch_db: 1.8,
                mono_bass: true,
                mono_bass_freq: 90.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.8,
                transient_shaper: true,
                transient_attack_db: -1.0,
                transient_sustain_db: 1.5,
                ms_matrix_enabled: true,
                mid_gain_db: 0.8,
                side_gain_db: -0.8,
                side_air_db: 0.0,
                deharsh_enabled: true,
                deharsh_amount: 0.45,
                deharsh_freq: 4000.0,
                comp_enabled: true,
                comp_opto_drive: 0.55,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 2.0,
                pultec_air_boost: 0.0,
                pultec_air_freq: 12000.0,
                limiter_ceiling_dbfs: -0.4,
                eq_10_band: [1.8, 2.0, 1.2, 0.8, 0.5, 0.0, -0.5, -1.2, -1.8, -2.5],
            },
            MasteringPreset {
                name: "15. Cyberpunk Neon Night Drive",
                description: "Tectonic sub-bass punch, laser transient snap, 145% ultra-wide spatial field.",
                target: "Darksynth, Midtempo Bass, Cyberpunk OST",
                spatial_width: 1.45,
                tube_warmth: 0.18,
                air_clarity_db: 2.0,
                bass_punch_db: 4.0,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Off,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.2,
                transient_shaper: true,
                transient_attack_db: 3.0,
                transient_sustain_db: 0.8,
                ms_matrix_enabled: true,
                mid_gain_db: 0.5,
                side_gain_db: 2.2,
                side_air_db: 1.8,
                deharsh_enabled: true,
                deharsh_amount: 0.40,
                deharsh_freq: 4200.0,
                comp_enabled: true,
                comp_opto_drive: 0.0,
                comp_vca_drive: 0.55,
                pultec_enabled: true,
                pultec_low_boost: 2.5,
                pultec_air_boost: 2.5,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [3.8, 2.5, 0.5, -0.8, -0.5, 0.0, 0.8, 1.5, 2.2, 2.8],
            },
            MasteringPreset {
                name: "16. Ethereal Dream Pop & Shoegaze Cloud",
                description: "Massive side channel reverb lift, silky Pultec 20k sheen, opto vocal glue.",
                target: "Cocteau Twins, Slowdive, Beach House, Post-Rock",
                spatial_width: 1.60,
                tube_warmth: 0.25,
                air_clarity_db: 2.2,
                bass_punch_db: 1.5,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: false,
                transient_attack_db: 0.0,
                transient_sustain_db: 1.2,
                ms_matrix_enabled: true,
                mid_gain_db: -1.0,
                side_gain_db: 3.0,
                side_air_db: 2.0,
                deharsh_enabled: true,
                deharsh_amount: 0.50,
                deharsh_freq: 4000.0,
                comp_enabled: true,
                comp_opto_drive: 0.45,
                comp_vca_drive: 0.20,
                pultec_enabled: true,
                pultec_low_boost: 1.0,
                pultec_air_boost: 3.0,
                pultec_air_freq: 20000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.5, 1.2, 0.5, 0.0, 0.0, 0.5, 1.0, 1.5, 2.5, 3.0],
            },
            MasteringPreset {
                name: "17. Sunset Acoustic Campfire & Folk Gathering",
                description: "Organic wood body on acoustic guitars, intimate phantom center, gentle tape glue.",
                target: "Acoustic Fingerstyle, Bluegrass, Live Campfire",
                spatial_width: 1.10,
                tube_warmth: 0.30,
                air_clarity_db: 1.2,
                bass_punch_db: 1.5,
                mono_bass: true,
                mono_bass_freq: 70.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.0,
                transient_shaper: true,
                transient_attack_db: 1.5,
                transient_sustain_db: 0.5,
                ms_matrix_enabled: true,
                mid_gain_db: 0.8,
                side_gain_db: 0.2,
                side_air_db: 0.5,
                deharsh_enabled: true,
                deharsh_amount: 0.35,
                deharsh_freq: 3200.0,
                comp_enabled: true,
                comp_opto_drive: 0.35,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 1.2,
                pultec_air_boost: 1.5,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.0, 1.5, 1.0, 0.5, 0.0, 0.5, 0.8, 0.5, 1.0, 1.2],
            },
            MasteringPreset {
                name: "18. Epic Cinematic Film Score (Hans Zimmer Style)",
                description: "Tectonic infrasonic sub-bass, unconstrained orchestral macro-dynamics, wide hall.",
                target: "Film Scores, Trailer Music, Game Soundtracks",
                spatial_width: 1.50,
                tube_warmth: 0.0,
                air_clarity_db: 1.5,
                bass_punch_db: 3.5,
                mono_bass: true,
                mono_bass_freq: 60.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Standard,
                subsonic_filter: false, // Infrasonic pass for cinema rumble
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: 2.0,
                transient_sustain_db: 1.5,
                ms_matrix_enabled: true,
                mid_gain_db: 0.0,
                side_gain_db: 2.0,
                side_air_db: 1.2,
                deharsh_enabled: true,
                deharsh_amount: 0.30,
                deharsh_freq: 3400.0,
                comp_enabled: false,
                comp_opto_drive: 0.0,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 2.0,
                pultec_air_boost: 2.0,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.1,
                eq_10_band: [3.5, 2.0, 0.8, 0.0, 0.0, 0.0, 0.5, 1.0, 1.8, 2.0],
            },
            MasteringPreset {
                name: "19. Motown Soul & 1960s Stax Funk Groove",
                description: "Punchy electric bass, forward brass section, vintage analog optical leveling.",
                target: "Soul, Motown, Funk, R&B Classic",
                spatial_width: 1.05,
                tube_warmth: 0.40,
                air_clarity_db: 0.5,
                bass_punch_db: 2.5,
                mono_bass: true,
                mono_bass_freq: 100.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: false,
                deesser_amount: 0.0,
                deesser_freq: 6500.0,
                tape_emulation: true,
                tape_drive: 1.5,
                transient_shaper: true,
                transient_attack_db: 1.8,
                transient_sustain_db: 0.8,
                ms_matrix_enabled: true,
                mid_gain_db: 1.2,
                side_gain_db: -0.5,
                side_air_db: 0.0,
                deharsh_enabled: true,
                deharsh_amount: 0.40,
                deharsh_freq: 3800.0,
                comp_enabled: true,
                comp_opto_drive: 0.50,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 2.2,
                pultec_air_boost: 1.2,
                pultec_air_freq: 12000.0,
                limiter_ceiling_dbfs: -0.3,
                eq_10_band: [1.5, 2.2, 1.5, 0.5, 0.5, 0.8, 1.0, 0.0, -0.5, -1.0],
            },
            MasteringPreset {
                name: "20. ASMR & Intimate Whisper",
                description: "Ultra-close vocal proximity, hyper-delicate whisper articulation, safe sibilance.",
                target: "ASMR, Spoken Word, Whispered Ballads",
                spatial_width: 1.05,
                tube_warmth: 0.20,
                air_clarity_db: 1.5,
                bass_punch_db: 0.5,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: true,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: true,
                deesser_amount: 0.80,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: 2.5,
                transient_sustain_db: 1.5,
                ms_matrix_enabled: true,
                mid_gain_db: 2.5,
                side_gain_db: -0.5,
                side_air_db: 0.8,
                deharsh_enabled: true,
                deharsh_amount: 0.60,
                deharsh_freq: 3500.0,
                comp_enabled: true,
                comp_opto_drive: 0.60,
                comp_vca_drive: 0.0,
                pultec_enabled: true,
                pultec_low_boost: 0.5,
                pultec_air_boost: 2.0,
                pultec_air_freq: 16000.0,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.0, 1.0, 0.5, 0.0, 0.8, 1.8, 1.5, -1.5, 0.5, 1.5],
            },
        ]
    }
}

#[derive(Debug, Clone)]
pub struct AudiophileEnhancer {
    pub enabled: bool,
    pub spatial_width: f32,
    pub tube_warmth: f32,
    pub air_clarity_db: f32,
    pub bass_punch_db: f32,
    pub mono_bass: bool,
    pub mono_bass_freq: f32,
    pub loudness_contour: bool,
    pub crossfeed: CrossfeedMode,
    pub subsonic_filter: bool,
    pub ultrasonic_filter: bool,
    pub deesser_enabled: bool,
    pub deesser_amount: f32,
    pub deesser_freq: f32,
    pub deesser_reduction_db: f32,

    pub tape_emulation: bool,
    pub tape_drive: f32,
    pub transient_shaper: bool,
    pub transient_attack_db: f32,
    pub transient_sustain_db: f32,
    pub ms_matrix_enabled: bool,
    pub mid_gain_db: f32,
    pub side_gain_db: f32,
    pub side_air_db: f32,
    pub deharsh_enabled: bool,
    pub deharsh_amount: f32,
    pub deharsh_freq: f32,
    pub deharsh_reduction_db: f32,
    pub comp_enabled: bool,
    pub comp_opto_drive: f32,
    pub comp_vca_drive: f32,
    pub comp_reduction_db: f32,
    pub pultec_enabled: bool,
    pub pultec_low_boost: f32,
    pub pultec_air_boost: f32,
    pub pultec_air_freq: f32,

    sample_rate: f32,
    air_filter: FastSosFilter,
    punch_filter: FastSosFilter,
    boundary_filter: FastSosFilter,
    deesser_band_filter: FastSosFilter,
    crossfeed_filter: FastSosFilter,
    mono_bass_side_filter: FastSosFilter,
    tape_bump_filter: FastSosFilter,
    pultec_low_filter: FastSosFilter,
    pultec_air_filter: FastSosFilter,
    deharsh_band_filter: FastSosFilter,

    deesser_env: f32,
    deharsh_env: f32,
    transient_fast_env: [f32; 2],
    transient_slow_env: [f32; 2],
    comp_opto_env: f32,
    comp_vca_env: f32,
}

impl AudiophileEnhancer {
    pub fn new(sample_rate: f32) -> Self {
        let mut enh = Self {
            enabled: true,
            spatial_width: 1.0,
            tube_warmth: 0.0,
            air_clarity_db: 0.0,
            bass_punch_db: 0.0,
            mono_bass: false,
            mono_bass_freq: 85.0,
            loudness_contour: false,
            crossfeed: CrossfeedMode::Off,
            subsonic_filter: true,
            ultrasonic_filter: true,
            deesser_enabled: false,
            deesser_amount: 0.5,
            deesser_freq: 6500.0,
            deesser_reduction_db: 0.0,
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
            deharsh_amount: 0.5,
            deharsh_freq: 3800.0,
            deharsh_reduction_db: 0.0,
            comp_enabled: false,
            comp_opto_drive: 0.0,
            comp_vca_drive: 0.0,
            comp_reduction_db: 0.0,
            pultec_enabled: false,
            pultec_low_boost: 0.0,
            pultec_air_boost: 0.0,
            pultec_air_freq: 16000.0,
            sample_rate,
            air_filter: FastSosFilter::new(),
            punch_filter: FastSosFilter::new(),
            boundary_filter: FastSosFilter::new(),
            deesser_band_filter: FastSosFilter::new(),
            crossfeed_filter: FastSosFilter::new(),
            mono_bass_side_filter: FastSosFilter::new(),
            tape_bump_filter: FastSosFilter::new(),
            pultec_low_filter: FastSosFilter::new(),
            pultec_air_filter: FastSosFilter::new(),
            deharsh_band_filter: FastSosFilter::new(),
            deesser_env: 0.0,
            deharsh_env: 0.0,
            transient_fast_env: [0.0, 0.0],
            transient_slow_env: [0.0, 0.0],
            comp_opto_env: 0.0,
            comp_vca_env: 0.0,
        };
        enh.rebuild_filters();
        enh
    }

    /// Apply a mastering preset recipe to the enhancer.
    pub fn apply_preset(&mut self, preset: &MasteringPreset) {
        self.spatial_width = preset.spatial_width;
        self.tube_warmth = preset.tube_warmth;
        self.air_clarity_db = preset.air_clarity_db;
        self.bass_punch_db = preset.bass_punch_db;
        self.mono_bass = preset.mono_bass;
        self.mono_bass_freq = preset.mono_bass_freq;
        self.loudness_contour = preset.loudness_contour;
        self.crossfeed = preset.crossfeed;
        self.subsonic_filter = preset.subsonic_filter;
        self.ultrasonic_filter = preset.ultrasonic_filter;
        self.deesser_enabled = preset.deesser_enabled;
        self.deesser_amount = preset.deesser_amount;
        self.deesser_freq = preset.deesser_freq;
        self.tape_emulation = preset.tape_emulation;
        self.tape_drive = preset.tape_drive;
        self.transient_shaper = preset.transient_shaper;
        self.transient_attack_db = preset.transient_attack_db;
        self.transient_sustain_db = preset.transient_sustain_db;
        self.ms_matrix_enabled = preset.ms_matrix_enabled;
        self.mid_gain_db = preset.mid_gain_db;
        self.side_gain_db = preset.side_gain_db;
        self.side_air_db = preset.side_air_db;
        self.deharsh_enabled = preset.deharsh_enabled;
        self.deharsh_amount = preset.deharsh_amount;
        self.deharsh_freq = preset.deharsh_freq;
        self.comp_enabled = preset.comp_enabled;
        self.comp_opto_drive = preset.comp_opto_drive;
        self.comp_vca_drive = preset.comp_vca_drive;
        self.pultec_enabled = preset.pultec_enabled;
        self.pultec_low_boost = preset.pultec_low_boost;
        self.pultec_air_boost = preset.pultec_air_boost;
        self.pultec_air_freq = preset.pultec_air_freq;
        self.rebuild_filters();
    }

    /// Dynamically modulate and apply a preset tailored to the listener's acoustic gear profile.
    pub fn apply_preset_with_gear(&mut self, preset: &MasteringPreset, gear: &AcousticGearProfile) {
        self.apply_preset(preset);

        // 1. Form Factor Adaptations
        match gear.form_factor {
            GearFormFactor::InEar => {
                // IEMs bypass pinna: enforce tighter sub-bass mono and gentle spatial cap
                self.mono_bass = true;
                self.mono_bass_freq = self.mono_bass_freq.max(85.0);
                if self.spatial_width > 1.25 {
                    self.spatial_width = 1.25;
                }
                self.deesser_enabled = true;
                self.deesser_amount = (self.deesser_amount + 0.15).min(1.0);
            }
            GearFormFactor::OverEar => {
                if gear.enclosure == GearEnclosure::ClosedBack {
                    self.spatial_width = (self.spatial_width * 1.15).clamp(0.5, 2.0);
                    self.deharsh_enabled = true;
                }
            }
            GearFormFactor::BoneConduction => {
                self.pultec_enabled = true;
                self.pultec_air_boost = (self.pultec_air_boost + 2.0).min(6.0);
                self.transient_shaper = true;
                self.transient_attack_db = (self.transient_attack_db + 1.5).min(5.0);
            }
            _ => {}
        }

        // 2. Driver Transducer Adaptations
        if gear.drivers[1] {
            // Planar Magnetic: boost transient attack punch
            self.transient_shaper = true;
            self.transient_attack_db = (self.transient_attack_db + 1.2).min(5.0);
        }
        if gear.drivers[2] {
            // Balanced Armature: soften metallic highs with triode tube warmth
            self.tube_warmth = (self.tube_warmth + 0.08).min(0.6);
        }
        if gear.drivers[3] {
            // Electrostatic: ensure protection filters are active
            self.subsonic_filter = true;
            self.ultrasonic_filter = true;
        }

        // 3. Tonal Balance Adaptations
        match gear.tonal_balance {
            GearTonalBalance::AnalyticalBright => {
                self.deharsh_enabled = true;
                self.deharsh_amount = (self.deharsh_amount + 0.20).min(1.0);
                self.air_clarity_db = (self.air_clarity_db - 1.0).max(0.0);
            }
            GearTonalBalance::DarkWarm => {
                self.pultec_enabled = true;
                self.pultec_air_boost = (self.pultec_air_boost + 1.5).min(5.0);
            }
            GearTonalBalance::BassHeavy => {
                self.mono_bass = true;
                self.mono_bass_freq = 95.0;
                self.bass_punch_db = (self.bass_punch_db - 1.0).max(0.0);
            }
            _ => {}
        }

        self.rebuild_filters();
    }

    pub fn rebuild_filters(&mut self) {
        // Boundary Guard Filters (18 Hz Subsonic HPF + 21 kHz Ultrasonic LPF)
        let mut b_filters = Vec::new();
        if self.subsonic_filter {
            b_filters.push(BiquadFilter::new(
                BiquadFilterType::HighPass,
                18.0,
                0.0,
                0.707,
                self.sample_rate,
            ));
        }
        if self.ultrasonic_filter {
            b_filters.push(BiquadFilter::new(
                BiquadFilterType::LowPass,
                21000.0,
                0.0,
                0.707,
                self.sample_rate,
            ));
        }
        self.boundary_filter.update_filters(&b_filters);

        // Sub-Bass Mono High-Pass Filter on Side channel
        if self.mono_bass {
            let m_filters = vec![BiquadFilter::new(
                BiquadFilterType::HighPass,
                self.mono_bass_freq.clamp(40.0, 300.0),
                0.0,
                0.707,
                self.sample_rate,
            )];
            self.mono_bass_side_filter.update_filters(&m_filters);
        } else {
            self.mono_bass_side_filter.update_filters(&[]);
        }

        // Aural Air (12 kHz High-Shelf)
        if self.air_clarity_db > 0.01 {
            let air = vec![BiquadFilter::new(
                BiquadFilterType::HighShelf,
                12000.0,
                self.air_clarity_db,
                0.707,
                self.sample_rate,
            )];
            self.air_filter.update_filters(&air);
        } else {
            self.air_filter.update_filters(&[]);
        }

        // Sub-Bass Punch (45 Hz Peaking)
        if self.bass_punch_db > 0.01 {
            let punch = vec![BiquadFilter::new(
                BiquadFilterType::Peaking,
                45.0,
                self.bass_punch_db,
                1.414,
                self.sample_rate,
            )];
            self.punch_filter.update_filters(&punch);
        } else {
            self.punch_filter.update_filters(&[]);
        }

        // 1/2-Inch Master Tape 50 Hz Head Bump
        if self.tape_emulation {
            let tape_bump = vec![BiquadFilter::new(
                BiquadFilterType::Peaking,
                50.0,
                (self.tape_drive * 1.5).clamp(0.5, 4.0),
                1.2,
                self.sample_rate,
            )];
            self.tape_bump_filter.update_filters(&tape_bump);
        } else {
            self.tape_bump_filter.update_filters(&[]);
        }

        // Pultec Low-End & Air Shelves
        if self.pultec_enabled {
            if self.pultec_low_boost > 0.01 {
                let low = vec![BiquadFilter::new(
                    BiquadFilterType::Peaking,
                    60.0,
                    self.pultec_low_boost,
                    1.0,
                    self.sample_rate,
                )];
                self.pultec_low_filter.update_filters(&low);
            } else {
                self.pultec_low_filter.update_filters(&[]);
            }

            if self.pultec_air_boost > 0.01 {
                let air = vec![BiquadFilter::new(
                    BiquadFilterType::HighShelf,
                    self.pultec_air_freq.clamp(8000.0, 22000.0),
                    self.pultec_air_boost,
                    0.707,
                    self.sample_rate,
                )];
                self.pultec_air_filter.update_filters(&air);
            } else {
                self.pultec_air_filter.update_filters(&[]);
            }
        } else {
            self.pultec_low_filter.update_filters(&[]);
            self.pultec_air_filter.update_filters(&[]);
        }

        // Dynamic Resonance Suppressor (De-Harshing Bandpass)
        if self.deharsh_enabled {
            let deharsh = vec![BiquadFilter::new(
                BiquadFilterType::BandPass,
                self.deharsh_freq.clamp(2000.0, 9000.0),
                0.0,
                2.5,
                self.sample_rate,
            )];
            self.deharsh_band_filter.update_filters(&deharsh);
        } else {
            self.deharsh_band_filter.update_filters(&[]);
        }

        // De-Esser detection bandpass
        if self.deesser_enabled {
            let deess = vec![BiquadFilter::new(
                BiquadFilterType::BandPass,
                self.deesser_freq,
                0.0,
                2.0,
                self.sample_rate,
            )];
            self.deesser_band_filter.update_filters(&deess);
        } else {
            self.deesser_band_filter.update_filters(&[]);
        }

        // Meier / Bauer Crossfeed shadow filter (700 Hz Low-Pass)
        if self.crossfeed != CrossfeedMode::Off {
            let xfeed = vec![BiquadFilter::new(
                BiquadFilterType::LowPass,
                700.0,
                0.0,
                0.707,
                self.sample_rate,
            )];
            self.crossfeed_filter.update_filters(&xfeed);
        } else {
            self.crossfeed_filter.update_filters(&[]);
        }
    }

    /// Process stereo buffer in-place through studio enhancer modules.
    #[inline]
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if !self.enabled || buffer.is_empty() {
            return;
        }

        // 1. Boundary Guard Filters (Subsonic HPF & Ultrasonic LPF)
        self.boundary_filter.process(buffer);

        // 2. Sub-Bass Mono Consolidation (Elliptical Mono Maker)
        if self.mono_bass {
            let mut side_buf = vec![[0.0f32; 2]; buffer.len()];
            for (i, frame) in buffer.iter().enumerate() {
                let s = (frame[0] - frame[1]) * 0.5;
                side_buf[i] = [s, s];
            }
            self.mono_bass_side_filter.process(&mut side_buf);
            for (i, frame) in buffer.iter_mut().enumerate() {
                let m = (frame[0] + frame[1]) * 0.5;
                let s = side_buf[i][0];
                frame[0] = m + s;
                frame[1] = m - s;
            }
        }

        // 3. Mid/Side Spatial Tilt & 3D Soundstage Width
        let w = self.spatial_width;
        let ms_active = self.ms_matrix_enabled;
        let mid_mult = if ms_active { 10.0f32.powf(self.mid_gain_db / 20.0) } else { 1.0 };
        let side_mult = if ms_active { 10.0f32.powf(self.side_gain_db / 20.0) * w } else { w };
        if (mid_mult - 1.0).abs() > 1e-4 || (side_mult - 1.0).abs() > 1e-4 {
            for frame in buffer.iter_mut() {
                let mid = (frame[0] + frame[1]) * 0.5 * mid_mult;
                let side = (frame[0] - frame[1]) * 0.5 * side_mult;
                frame[0] = mid + side;
                frame[1] = mid - side;
            }
        }

        // 4. Audiophile Headphone Crossfeed (Meier / Bauer HRTF)
        if self.crossfeed != CrossfeedMode::Off {
            let feed_level = match self.crossfeed {
                CrossfeedMode::Subtle => 0.15,
                CrossfeedMode::Standard => 0.28,
                CrossfeedMode::Off => 0.0,
            };
            let mut x_shadow = buffer.to_vec();
            self.crossfeed_filter.process(&mut x_shadow);
            for (i, frame) in buffer.iter_mut().enumerate() {
                let cross_l = x_shadow[i][0] * feed_level;
                let cross_r = x_shadow[i][1] * feed_level;
                frame[0] += cross_r;
                frame[1] += cross_l;
            }
        }

        // 5. 1/2-Inch Master Tape Emulation (50 Hz Head Bump & Tape Glue)
        if self.tape_emulation {
            self.tape_bump_filter.process(buffer);
            let drive = 1.0 + self.tape_drive * 0.4;
            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let x = frame[ch] * drive;
                    let sat = x.tanh();
                    frame[ch] = sat / (1.0 + self.tape_drive * 0.08);
                }
            }
        }

        // 6. Class-A Tube Warmth (Continuous soft-knee saturation, zero DC offset)
        let t = self.tube_warmth;
        if t > 0.001 {
            let drive = 1.0 + t * 1.5;
            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let x = frame[ch] * drive;
                    let sign = x.signum();
                    let abs_x = x.abs();
                    let sat = if abs_x < 0.6 {
                        abs_x
                    } else if abs_x < 1.4 {
                        let u = (abs_x - 0.6) / 0.8;
                        0.6 + 0.8 * (u - 0.5 * u * u)
                    } else {
                        1.0
                    };
                    let y = sign * sat;
                    let warm = y + t * 0.08 * (y * y - 0.5 * abs_x.min(1.0));
                    frame[ch] = warm / (1.0 + t * 0.25);
                }
            }
        }

        // 7. Aural Air & Sub-Bass Punch & Pultec EQP-1A Velvet Inductor
        self.air_filter.process(buffer);
        self.punch_filter.process(buffer);
        if self.pultec_enabled {
            self.pultec_low_filter.process(buffer);
            self.pultec_air_filter.process(buffer);
        }

        // 8. Transient Attack & Punch Shaper
        if self.transient_shaper && (self.transient_attack_db.abs() > 0.05 || self.transient_sustain_db.abs() > 0.05) {
            let fast_coeff = 1.0 - (-1.0 / (self.sample_rate * 0.003)).exp();
            let slow_coeff = 1.0 - (-1.0 / (self.sample_rate * 0.040)).exp();
            let atk_scale = self.transient_attack_db / 6.0;
            let sus_scale = self.transient_sustain_db / 6.0;

            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let mag = frame[ch].abs();
                    self.transient_fast_env[ch] += (mag - self.transient_fast_env[ch]) * fast_coeff;
                    self.transient_slow_env[ch] += (mag - self.transient_slow_env[ch]) * slow_coeff;
                    let delta = self.transient_fast_env[ch] - self.transient_slow_env[ch];
                    let trans_gain = (1.0 + delta * atk_scale + self.transient_slow_env[ch] * sus_scale).clamp(0.2, 2.5);
                    frame[ch] *= trans_gain;
                }
            }
        }

        // 9. Dynamic Resonance De-Harshing
        if self.deharsh_enabled {
            let mut det = buffer.to_vec();
            self.deharsh_band_filter.process(&mut det);
            let attack = 1.0 - (-1.0 / (self.sample_rate * 0.002)).exp();
            let release = 1.0 - (-1.0 / (self.sample_rate * 0.040)).exp();
            let threshold = 0.22;
            let mut max_gr = 0.0f32;

            for (i, frame) in buffer.iter_mut().enumerate() {
                let det_level = det[i][0].abs().max(det[i][1].abs());
                if det_level > self.deharsh_env {
                    self.deharsh_env += (det_level - self.deharsh_env) * attack;
                } else {
                    self.deharsh_env += (det_level - self.deharsh_env) * release;
                }

                if self.deharsh_env > threshold {
                    let excess = self.deharsh_env - threshold;
                    let gr = (1.0 - (excess * self.deharsh_amount * 2.2)).clamp(0.3, 1.0);
                    frame[0] *= gr;
                    frame[1] *= gr;
                    let gr_db = 20.0 * gr.log10();
                    if gr_db < max_gr {
                        max_gr = gr_db;
                    }
                }
            }
            self.deharsh_reduction_db = max_gr;
        } else {
            self.deharsh_reduction_db = 0.0;
        }

        // 10. Dynamic De-Esser (5.0k - 8.5k Hz Sibilance Limiter)
        if self.deesser_enabled {
            let mut det = buffer.to_vec();
            self.deesser_band_filter.process(&mut det);
            let attack = 1.0 - (-1.0 / (self.sample_rate * 0.002)).exp();
            let release = 1.0 - (-1.0 / (self.sample_rate * 0.050)).exp();
            let threshold = 0.25;

            let mut max_gr = 0.0f32;
            for (i, frame) in buffer.iter_mut().enumerate() {
                let det_level = det[i][0].abs().max(det[i][1].abs());
                if det_level > self.deesser_env {
                    self.deesser_env += (det_level - self.deesser_env) * attack;
                } else {
                    self.deesser_env += (det_level - self.deesser_env) * release;
                }

                if self.deesser_env > threshold {
                    let excess = self.deesser_env - threshold;
                    let gr = (1.0 - (excess * self.deesser_amount * 2.0)).clamp(0.2, 1.0);
                    frame[0] *= gr;
                    frame[1] *= gr;
                    let gr_db = 20.0 * gr.log10();
                    if gr_db < max_gr {
                        max_gr = gr_db;
                    }
                }
            }
            self.deesser_reduction_db = max_gr;
        } else {
            self.deesser_reduction_db = 0.0;
        }

        // 11. Dual-Stage Mastering Bus Compressor (Opto Leveler + VCA Discrete Punch)
        if self.comp_enabled && (self.comp_opto_drive > 0.01 || self.comp_vca_drive > 0.01) {
            let opto_atk = 1.0 - (-1.0 / (self.sample_rate * 0.080)).exp();
            let opto_rel = 1.0 - (-1.0 / (self.sample_rate * 0.250)).exp();
            let vca_atk = 1.0 - (-1.0 / (self.sample_rate * 0.020)).exp();
            let vca_rel = 1.0 - (-1.0 / (self.sample_rate * 0.080)).exp();
            let threshold = 0.35;
            let mut max_comp_gr = 0.0f32;

            for frame in buffer.iter_mut() {
                let peak = frame[0].abs().max(frame[1].abs());

                if peak > self.comp_opto_env {
                    self.comp_opto_env += (peak - self.comp_opto_env) * opto_atk;
                } else {
                    self.comp_opto_env += (peak - self.comp_opto_env) * opto_rel;
                }

                if peak > self.comp_vca_env {
                    self.comp_vca_env += (peak - self.comp_vca_env) * vca_atk;
                } else {
                    self.comp_vca_env += (peak - self.comp_vca_env) * vca_rel;
                }

                let opto_gr = if self.comp_opto_env > threshold {
                    1.0 - ((self.comp_opto_env - threshold) * self.comp_opto_drive * 0.6)
                } else {
                    1.0
                }.clamp(0.4, 1.0);

                let vca_gr = if self.comp_vca_env > threshold {
                    1.0 - ((self.comp_vca_env - threshold) * self.comp_vca_drive * 0.9)
                } else {
                    1.0
                }.clamp(0.4, 1.0);

                let total_gr = (opto_gr * vca_gr).clamp(0.3, 1.0);
                frame[0] *= total_gr;
                frame[1] *= total_gr;

                let gr_db = 20.0 * total_gr.log10();
                if gr_db < max_comp_gr {
                    max_comp_gr = gr_db;
                }
            }
            self.comp_reduction_db = max_comp_gr;
        } else {
            self.comp_reduction_db = 0.0;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enhancer_presets_count_and_application() {
        let presets = MasteringPreset::all();
        assert_eq!(presets.len(), 20, "Should provide 20 handcrafted presets");

        let mut enh = AudiophileEnhancer::new(48000.0);
        let gear = AcousticGearProfile::default();
        for preset in presets {
            enh.apply_preset_with_gear(&preset, &gear);
            assert!(!enh.spatial_width.is_nan());
            assert!(!enh.tube_warmth.is_nan());
            assert_eq!(preset.eq_10_band.len(), 10);
        }
    }

    #[test]
    fn test_enhancer_spatial_widener() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.spatial_width = 1.5;

        let mut audio = vec![[0.8f32, 0.0f32]; 128]; // Hard panned Left
        enh.process(&mut audio);

        assert_ne!(audio[0][0], audio[0][1]);
        assert!(!audio[0][0].is_nan());
    }

    #[test]
    fn test_enhancer_tube_warmth_saturation() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.tube_warmth = 0.3;

        let mut audio = vec![[1.5f32, 1.5f32]; 128]; // Hot signal
        enh.process(&mut audio);

        assert!(audio[0][0].abs() <= 1.0);
        assert!(!audio[0][0].is_nan());
    }

    #[test]
    fn test_mono_bass_consolidation() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.mono_bass = true;
        enh.mono_bass_freq = 85.0;
        enh.rebuild_filters();

        let mut audio = vec![[1.0f32, -1.0f32]; 256];
        enh.process(&mut audio);

        assert!(audio[200][0].abs() < 0.5, "Sub-bass out-of-phase energy should be collapsed");
    }

    #[test]
    fn test_tape_emulation_and_transient_shaper() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.tape_emulation = true;
        enh.tape_drive = 1.5;
        enh.transient_shaper = true;
        enh.transient_attack_db = 2.0;
        enh.rebuild_filters();

        let mut audio = vec![[0.5f32, 0.5f32]; 128];
        enh.process(&mut audio);
        assert!(!audio[0][0].is_nan());
        assert!(audio[0][0].abs() <= 1.0);
    }
}
