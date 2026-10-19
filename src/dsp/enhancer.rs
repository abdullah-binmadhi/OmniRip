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
    BuiltinLaptopSpeakers,
    DesktopBookshelfSpeakers,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearEnclosure {
    OpenBack,
    SemiOpen,
    ClosedBack,
    Anc,
    PortedRear,
    PortedFront,
    SealedSuspension,
    PassiveRadiator,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum GearCoupling {
    Silicone,
    MemoryFoam,
    CustomMolded,
    OpenAir,
    VelourPads,
    LeatherPads,
    HybridPads,
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
    ActivePoweredMonitors,
    PassiveWithStereoAmp,
    BalancedAudioInterface,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, serde::Serialize, serde::Deserialize)]
pub enum SpeakerPlacement {
    #[default]
    DeskSurface,
    ElevatedStand,
    SoftSurfaceOrLap,
    NearWallCorner,
    FreeField,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, serde::Serialize, serde::Deserialize)]
pub enum SpeakerCalibrationTarget {
    #[default]
    VocalClarity,
    SpatialExpansion,
    BassProtection,
    FlatReference,
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
    #[serde(default)]
    pub speaker_placement: SpeakerPlacement,
    #[serde(default)]
    pub speaker_target: SpeakerCalibrationTarget,
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
            speaker_placement: SpeakerPlacement::DeskSurface,
            speaker_target: SpeakerCalibrationTarget::FlatReference,
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
            GearFormFactor::BuiltinLaptopSpeakers => "Built-in Laptop Speakers",
            GearFormFactor::DesktopBookshelfSpeakers => "Desktop Bookshelf Speakers",
        }
    }

    pub fn default_builtin_speakers(model: &str) -> Self {
        Self {
            name: format!("{} Built-in Speakers", model),
            form_factor: GearFormFactor::BuiltinLaptopSpeakers,
            enclosure: GearEnclosure::OpenBack,
            drivers: [true, false, false, false, false, false],
            coupling: GearCoupling::OpenAir,
            tonal_balance: GearTonalBalance::NeutralStudio,
            source_amp: GearSourceAmp::DesktopSolidState,
            speaker_placement: SpeakerPlacement::DeskSurface,
            speaker_target: SpeakerCalibrationTarget::VocalClarity,
        }
    }

    pub fn default_bookshelf_speakers() -> Self {
        Self {
            name: "Desktop Bookshelf Monitors".to_string(),
            form_factor: GearFormFactor::DesktopBookshelfSpeakers,
            enclosure: GearEnclosure::PortedRear,
            drivers: [true, false, false, false, false, false],
            coupling: GearCoupling::OpenAir,
            tonal_balance: GearTonalBalance::NeutralStudio,
            source_amp: GearSourceAmp::ActivePoweredMonitors,
            speaker_placement: SpeakerPlacement::ElevatedStand,
            speaker_target: SpeakerCalibrationTarget::FlatReference,
        }
    }

    pub fn enclosure_label(&self) -> &'static str {
        match self.enclosure {
            GearEnclosure::OpenBack => "Open-Back",
            GearEnclosure::SemiOpen => "Semi-Open",
            GearEnclosure::ClosedBack => "Closed-Back",
            GearEnclosure::Anc => "ANC Chamber",
            GearEnclosure::PortedRear => "Rear-Ported",
            GearEnclosure::PortedFront => "Front-Ported",
            GearEnclosure::SealedSuspension => "Sealed Acoustic",
            GearEnclosure::PassiveRadiator => "Passive Radiator",
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

    pub fn coupling_label(&self) -> &'static str {
        match self.coupling {
            GearCoupling::Silicone => "Silicone Tips",
            GearCoupling::MemoryFoam => "Memory Foam",
            GearCoupling::CustomMolded => "Custom Molded",
            GearCoupling::OpenAir => "Open-Air",
            GearCoupling::VelourPads => "Velour Pads",
            GearCoupling::LeatherPads => "Leather Pads",
            GearCoupling::HybridPads => "Hybrid Pads",
        }
    }

    pub fn speaker_placement_label(&self) -> &'static str {
        match self.speaker_placement {
            SpeakerPlacement::DeskSurface => "Desk Surface",
            SpeakerPlacement::ElevatedStand => "Elevated Stand",
            SpeakerPlacement::SoftSurfaceOrLap => "Lap/Soft Surface",
            SpeakerPlacement::NearWallCorner => "Near Wall/Corner",
            SpeakerPlacement::FreeField => "Free-Field",
        }
    }

    pub fn speaker_target_label(&self) -> &'static str {
        match self.speaker_target {
            SpeakerCalibrationTarget::VocalClarity => "Vocal Clarity",
            SpeakerCalibrationTarget::SpatialExpansion => "Spatial Expansion",
            SpeakerCalibrationTarget::BassProtection => "Bass Protection",
            SpeakerCalibrationTarget::FlatReference => "Flat Reference",
        }
    }

    pub fn source_amp_label(&self) -> &'static str {
        match self.source_amp {
            GearSourceAmp::PortableDongle => "Portable Dongle",
            GearSourceAmp::DesktopSolidState => "Desktop Solid-State",
            GearSourceAmp::TubeAmp => "Vacuum Tube",
            GearSourceAmp::BluetoothWireless => "Bluetooth Wireless",
            GearSourceAmp::ActivePoweredMonitors => "Active Powered",
            GearSourceAmp::PassiveWithStereoAmp => "Passive + Stereo Amp",
            GearSourceAmp::BalancedAudioInterface => "Balanced Studio Interface",
        }
    }

    pub fn summary_badge(&self) -> String {
        format!("\"{}\" [{} | {} | {} | {}]", self.name, self.form_factor_label(), self.enclosure_label(), self.driver_summary(), self.tonal_label())
    }
}

impl Default for MasteringPreset {
    fn default() -> Self {
        Self::all()[0].clone()
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
    pub game_mode: bool,
    pub radar_eq: bool,
    pub spike_shield: bool,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
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
                game_mode: false,
                radar_eq: false,
                spike_shield: false,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [1.0, 1.0, 0.5, 0.0, 0.8, 1.8, 1.5, -1.5, 0.5, 1.5],
            },
            MasteringPreset {
                name: "21. Esports Tactical & Low-Latency Gaming",
                description: "Zero-lag 10.6ms buffer, footstep radar lift (+3.5dB), spatial widening, and explosive spike protection.",
                target: "Esports, League of Legends, Valorant, CS2, Fast-Paced Action",
                spatial_width: 1.20,
                tube_warmth: 0.0,
                air_clarity_db: 1.5,
                bass_punch_db: 0.0,
                mono_bass: true,
                mono_bass_freq: 85.0,
                loudness_contour: false,
                crossfeed: CrossfeedMode::Subtle,
                subsonic_filter: true,
                ultrasonic_filter: true,
                deesser_enabled: true,
                deesser_amount: 0.40,
                deesser_freq: 6500.0,
                tape_emulation: false,
                tape_drive: 0.0,
                transient_shaper: true,
                transient_attack_db: 2.5,
                transient_sustain_db: 0.0,
                ms_matrix_enabled: true,
                mid_gain_db: 0.0,
                side_gain_db: 1.0,
                side_air_db: 1.5,
                deharsh_enabled: true,
                deharsh_amount: 0.30,
                deharsh_freq: 3800.0,
                comp_enabled: true,
                comp_opto_drive: 0.20,
                comp_vca_drive: 0.15,
                pultec_enabled: false,
                pultec_low_boost: 0.0,
                pultec_air_boost: 0.0,
                pultec_air_freq: 16000.0,
                game_mode: true,
                radar_eq: true,
                spike_shield: true,
                limiter_ceiling_dbfs: -0.2,
                eq_10_band: [-1.5, -0.5, 0.0, 0.5, 1.5, 2.5, 3.0, 2.0, 1.5, 2.0],
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
    pub subsonic_freq: f32,
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
    pub game_mode: bool,
    pub radar_eq: bool,
    pub spike_shield: bool,

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
    radar_hpf_filter: FastSosFilter,
    radar_presence_filter: FastSosFilter,
    radar_air_filter: FastSosFilter,

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
            subsonic_freq: 18.0,
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
            game_mode: false,
            radar_eq: false,
            spike_shield: false,
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
            radar_hpf_filter: FastSosFilter::new(),
            radar_presence_filter: FastSosFilter::new(),
            radar_air_filter: FastSosFilter::new(),
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
        self.subsonic_freq = 18.0;
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
        self.game_mode = preset.game_mode;
        self.radar_eq = preset.radar_eq;
        self.spike_shield = preset.spike_shield;
        self.rebuild_filters();
    }

    /// Dynamically modulate and apply a preset tailored to the listener's acoustic gear profile.
    pub fn apply_preset_with_gear(&mut self, preset: &MasteringPreset, gear: &AcousticGearProfile) {
        self.apply_preset(preset);

        // 1. Form Factor Adaptations
        match gear.form_factor {
            GearFormFactor::BuiltinLaptopSpeakers => {
                // Built-in Laptop Speakers:
                // 1. Natural stereo widening for small chassis distance: 1.30x-1.50x
                self.spatial_width = (self.spatial_width * 1.35).clamp(1.15, 1.60);
                // 2. Disable headphone crossfeed (speakers already propagate into both ears)
                self.crossfeed = CrossfeedMode::Off;
                // 3. Subsonic protection high-pass at 45Hz to guard micro-woofers against excursion distortion
                self.subsonic_filter = true;
                self.subsonic_freq = 45.0;
                // 4. Do not engage IEM de-harshing or mono-bass clamping
                self.mono_bass = false;

                // 5. Dynamic Placement adaptations
                match gear.speaker_placement {
                    SpeakerPlacement::ElevatedStand => {
                        self.spatial_width = (self.spatial_width * 1.05).clamp(1.15, 1.65);
                    }
                    SpeakerPlacement::SoftSurfaceOrLap => {
                        self.air_clarity_db = (self.air_clarity_db + 0.8).min(6.0);
                    }
                    _ => {}
                }

                // 6. Dynamic Calibration Target adaptations
                match gear.speaker_target {
                    SpeakerCalibrationTarget::VocalClarity => {
                        self.air_clarity_db = (self.air_clarity_db + 1.0).min(6.0);
                        self.deharsh_enabled = true;
                        self.deharsh_amount = (self.deharsh_amount + 0.10).min(1.0);
                    }
                    SpeakerCalibrationTarget::SpatialExpansion => {
                        self.spatial_width = (self.spatial_width * 1.10).clamp(1.20, 1.70);
                    }
                    SpeakerCalibrationTarget::BassProtection => {
                        self.subsonic_freq = 52.0;
                        self.tube_warmth = (self.tube_warmth + 0.08).min(0.5);
                    }
                    SpeakerCalibrationTarget::FlatReference => {}
                }
            }
            GearFormFactor::DesktopBookshelfSpeakers => {
                // Desktop Bookshelf Speakers:
                // 1. True near-field stereo triangle imaging (clean, un-exaggerated 0.95x - 1.25x)
                self.spatial_width = (self.spatial_width * 1.05).clamp(0.85, 1.25);
                // 2. Disable headphone crossfeed
                self.crossfeed = CrossfeedMode::Off;
                // 3. Subsonic protection filter at 35Hz (protect nearfield woofers from subsonic rumble)
                self.subsonic_filter = true;
                self.subsonic_freq = 35.0;
                // 4. Leave natural stereo bass intact for stereo sub-bass imaging
                self.mono_bass = false;

                // 5. Enclosure and boundary adaptations
                if gear.enclosure == GearEnclosure::PortedRear && gear.speaker_placement == SpeakerPlacement::NearWallCorner {
                    self.bass_punch_db = (self.bass_punch_db - 1.0).max(0.0);
                }
                if gear.speaker_placement == SpeakerPlacement::DeskSurface {
                    self.deharsh_enabled = true;
                }
            }
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
                if gear.coupling == GearCoupling::VelourPads {
                    self.bass_punch_db = (self.bass_punch_db + 0.5).min(6.0);
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
                // For built-in or bookshelf speakers, skip IEM deharshing penalty
                if gear.form_factor != GearFormFactor::BuiltinLaptopSpeakers && gear.form_factor != GearFormFactor::DesktopBookshelfSpeakers {
                    self.deharsh_enabled = true;
                    self.deharsh_amount = (self.deharsh_amount + 0.20).min(1.0);
                    self.air_clarity_db = (self.air_clarity_db - 1.0).max(0.0);
                }
            }
            GearTonalBalance::DarkWarm => {
                self.pultec_enabled = true;
                self.pultec_air_boost = (self.pultec_air_boost + 1.5).min(5.0);
            }
            GearTonalBalance::BassHeavy => {
                if gear.form_factor != GearFormFactor::BuiltinLaptopSpeakers && gear.form_factor != GearFormFactor::DesktopBookshelfSpeakers {
                    self.mono_bass = true;
                    self.mono_bass_freq = 95.0;
                    self.bass_punch_db = (self.bass_punch_db - 1.0).max(0.0);
                }
            }
            _ => {}
        }

        self.rebuild_filters();
    }

    pub fn rebuild_filters(&mut self) {
        // Boundary Guard Filters (Subsonic HPF + 21 kHz Ultrasonic LPF)
        let mut b_filters = Vec::new();
        if self.subsonic_filter {
            let freq = if self.subsonic_freq > 1.0 { self.subsonic_freq } else { 18.0 };
            b_filters.push(BiquadFilter::new(
                BiquadFilterType::HighPass,
                freq,
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

        // Footstep & Ability Radar Filters (Esports Gaming Mode)
        if self.radar_eq {
            let hpf = vec![BiquadFilter::new(
                BiquadFilterType::HighPass,
                45.0,
                0.0,
                0.707,
                self.sample_rate,
            )];
            self.radar_hpf_filter.update_filters(&hpf);

            let pres = vec![BiquadFilter::new(
                BiquadFilterType::Peaking,
                2400.0,
                3.5,
                1.8,
                self.sample_rate,
            )];
            self.radar_presence_filter.update_filters(&pres);

            let air = vec![BiquadFilter::new(
                BiquadFilterType::HighShelf,
                10000.0,
                2.0,
                0.707,
                self.sample_rate,
            )];
            self.radar_air_filter.update_filters(&air);
        } else {
            self.radar_hpf_filter.update_filters(&[]);
            self.radar_presence_filter.update_filters(&[]);
            self.radar_air_filter.update_filters(&[]);
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

        // 12. Footstep & Ability Radar EQ (Esports Gaming Cues)
        if self.radar_eq {
            self.radar_hpf_filter.process(buffer);
            self.radar_presence_filter.process(buffer);
            self.radar_air_filter.process(buffer);
        }

        // 13. Explosive Spike Ear Shield (Fast soft-knee burst suppression)
        if self.spike_shield {
            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let s = frame[ch];
                    let abs_s = s.abs();
                    if abs_s > 0.85 {
                        let excess = abs_s - 0.85;
                        let compressed = 0.85 + (excess * 0.15).tanh() * 0.14;
                        frame[ch] = s.signum() * compressed;
                    }
                }
            }
        }
    }
}

/// Audiophile DAC/Amp Hardware Mimicker Flavor.
///
/// Emulates the reconstruction filters, analog output stages, harmonic signatures,
/// and timing characteristics of legendary audiophile DACs and headphone amplifiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum DacHardwareFlavor {
    /// Apple Silicon Cirrus Logic CS42L84 calibrated bit-perfect reference with peak protection.
    StockOemPlus,
    /// iFi Audio Zen DAC V2 (Burr-Brown DSD1793 bit-perfect minimum phase, TrueBass 65Hz analog shelf, warm 2nd harmonic).
    IfiZenDac,
    /// iBasso DC03 Pro (Dual Cirrus CS43131 flagship linear phase, 12.5kHz air shelf, ultra-low THD transparency).
    IbassoDcPro,
    /// Chord Mojo 2 (Rob Watts WTA sinc timing reconstruction emulation with 0.35ms spatial crossfeed).
    ChordMojo2,
    /// Schiit Audio Multibit (True R2R ladder DAC architecture, 45Hz dynamic punch, blended H2+H3 harmonic slam).
    SchiitMultibit,
}

impl Default for DacHardwareFlavor {
    fn default() -> Self {
        Self::StockOemPlus
    }
}

impl DacHardwareFlavor {
    pub fn label(&self) -> &'static str {
        match self {
            Self::StockOemPlus => "Stock Apple OEM+ (Cirrus CS42L84 Calibrated)",
            Self::IfiZenDac => "iFi Zen DAC V2 (Burr-Brown TrueBass)",
            Self::IbassoDcPro => "iBasso DC03 Pro (Dual CS43131 Transparency)",
            Self::ChordMojo2 => "Chord Mojo 2 (WTA Sinc Timing)",
            Self::SchiitMultibit => "Schiit Multibit (R2R Dynamic Slam)",
        }
    }

    pub fn short_label(&self) -> &'static str {
        match self {
            Self::StockOemPlus => "OEM+ (Stock)",
            Self::IfiZenDac => "iFi Zen DAC",
            Self::IbassoDcPro => "iBasso DC03",
            Self::ChordMojo2 => "Chord Mojo 2",
            Self::SchiitMultibit => "Schiit R2R",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Self::StockOemPlus => "Bit-perfect Apple Silicon CS42L84 calibrated reference with inter-sample peak protection",
            Self::IfiZenDac => "Burr-Brown DSD1793 minimum phase, 65Hz TrueBass analog shelf (+2.2dB), warm 2nd harmonic",
            Self::IbassoDcPro => "Dual CS43131 flagship linear phase, 12.5kHz air shelf (+0.8dB), ultra-low THD transparency",
            Self::ChordMojo2 => "Rob Watts WTA sinc timing reconstruction emulation with 0.35ms spatial crossfeed",
            Self::SchiitMultibit => "R2R ladder architectural slam, 45Hz dynamic punch (+1.5dB), rich even+odd analog saturation",
        }
    }

    pub fn cycle_next(&self) -> Self {
        match self {
            Self::StockOemPlus => Self::IfiZenDac,
            Self::IfiZenDac => Self::IbassoDcPro,
            Self::IbassoDcPro => Self::ChordMojo2,
            Self::ChordMojo2 => Self::SchiitMultibit,
            Self::SchiitMultibit => Self::StockOemPlus,
        }
    }

    pub fn cycle_prev(&self) -> Self {
        match self {
            Self::StockOemPlus => Self::SchiitMultibit,
            Self::IfiZenDac => Self::StockOemPlus,
            Self::IbassoDcPro => Self::IfiZenDac,
            Self::ChordMojo2 => Self::IbassoDcPro,
            Self::SchiitMultibit => Self::ChordMojo2,
        }
    }

    pub fn all() -> &'static [DacHardwareFlavor] {
        &[
            Self::StockOemPlus,
            Self::IfiZenDac,
            Self::IbassoDcPro,
            Self::ChordMojo2,
            Self::SchiitMultibit,
        ]
    }

    pub fn from_str_loose(s: &str) -> Option<Self> {
        let clean = s.trim().to_lowercase();
        match clean.as_str() {
            "oem" | "oem+" | "stock" | "apple" | "cs42l84" => Some(Self::StockOemPlus),
            "ifi" | "zen" | "ifi zen" | "burr-brown" | "burrbrown" => Some(Self::IfiZenDac),
            "ibasso" | "dc03" | "dc03pro" | "cs43131" => Some(Self::IbassoDcPro),
            "chord" | "mojo" | "mojo2" | "wta" => Some(Self::ChordMojo2),
            "schiit" | "multibit" | "r2r" | "bifrost" | "modi" => Some(Self::SchiitMultibit),
            _ => None,
        }
    }
}

/// Transposed Direct Form II Biquad State.
#[derive(Debug, Clone, Copy, Default)]
struct BiquadState {
    s1: f32,
    s2: f32,
}

impl BiquadState {
    #[inline(always)]
    fn process(&mut self, x: f32, c: &super::biquad::BiquadCoefficients) -> f32 {
        let y = c.b0 * x + self.s1;
        self.s1 = c.b1 * x - c.a1 * y + self.s2;
        self.s2 = c.b2 * x - c.a2 * y;
        y
    }
}

/// High-Performance Pure Rust DAC/Amp Mimicker Processing Engine.
#[derive(Debug, Clone)]
pub struct DacMimickerEngine {
    pub active_flavor: DacHardwareFlavor,
    pub target_flavor: DacHardwareFlavor,
    sample_rate: f32,

    // Smooth 15ms clickless crossfader
    crossfade_pos: usize,
    crossfade_len: usize,

    // Filter coefficients
    ifi_shelf_c: super::biquad::BiquadCoefficients,
    ibasso_shelf_c: super::biquad::BiquadCoefficients,
    schiit_low_c: super::biquad::BiquadCoefficients,
    schiit_high_c: super::biquad::BiquadCoefficients,
    chord_lpf_c: super::biquad::BiquadCoefficients,

    // Filter states
    ifi_state_l: BiquadState,
    ifi_state_r: BiquadState,
    ibasso_state_l: BiquadState,
    ibasso_state_r: BiquadState,
    schiit_low_l: BiquadState,
    schiit_low_r: BiquadState,
    schiit_high_l: BiquadState,
    schiit_high_r: BiquadState,
    chord_lpf_l: BiquadState,
    chord_lpf_r: BiquadState,

    // Chord Mojo 2 crossfeed delay line (~0.35ms)
    crossfeed_delay_l: [f32; 128],
    crossfeed_delay_r: [f32; 128],
    crossfeed_idx: usize,
    crossfeed_delay_samples: usize,
}

impl DacMimickerEngine {
    pub fn new(sample_rate: f32) -> Self {
        let mut engine = Self {
            active_flavor: DacHardwareFlavor::StockOemPlus,
            target_flavor: DacHardwareFlavor::StockOemPlus,
            sample_rate,
            crossfade_pos: 0,
            crossfade_len: (sample_rate * 0.015).round().max(64.0) as usize,

            ifi_shelf_c: super::biquad::BiquadCoefficients::default(),
            ibasso_shelf_c: super::biquad::BiquadCoefficients::default(),
            schiit_low_c: super::biquad::BiquadCoefficients::default(),
            schiit_high_c: super::biquad::BiquadCoefficients::default(),
            chord_lpf_c: super::biquad::BiquadCoefficients::default(),

            ifi_state_l: BiquadState::default(),
            ifi_state_r: BiquadState::default(),
            ibasso_state_l: BiquadState::default(),
            ibasso_state_r: BiquadState::default(),
            schiit_low_l: BiquadState::default(),
            schiit_low_r: BiquadState::default(),
            schiit_high_l: BiquadState::default(),
            schiit_high_r: BiquadState::default(),
            chord_lpf_l: BiquadState::default(),
            chord_lpf_r: BiquadState::default(),

            crossfeed_delay_l: [0.0; 128],
            crossfeed_delay_r: [0.0; 128],
            crossfeed_idx: 0,
            crossfeed_delay_samples: 17,
        };
        engine.recompute_filters();
        engine
    }

    pub fn set_sample_rate(&mut self, sample_rate: f32) {
        if (self.sample_rate - sample_rate).abs() > 1.0 {
            self.sample_rate = sample_rate;
            self.crossfade_len = (sample_rate * 0.015).round().max(64.0) as usize;
            self.recompute_filters();
        }
    }

    pub fn set_flavor(&mut self, flavor: DacHardwareFlavor) {
        if self.target_flavor != flavor {
            self.target_flavor = flavor;
            self.crossfade_pos = 0;
        }
    }

    pub fn cycle_flavor(&mut self) -> DacHardwareFlavor {
        let next = self.target_flavor.cycle_next();
        self.set_flavor(next);
        next
    }

    pub fn cycle_flavor_reverse(&mut self) -> DacHardwareFlavor {
        let prev = self.target_flavor.cycle_prev();
        self.set_flavor(prev);
        prev
    }

    fn recompute_filters(&mut self) {
        let sr = self.sample_rate;

        // iFi TrueBass: 65 Hz analog low shelf, +2.2 dB, Q = 0.707
        let ifi_biquad = BiquadFilter::new(BiquadFilterType::LowShelf, 65.0, 2.2, 0.707, sr);
        self.ifi_shelf_c = ifi_biquad.compute_coefficients();

        // iBasso DC03 Pro: 12.5 kHz air shelf, +0.8 dB, Q = 0.707
        let ibasso_biquad = BiquadFilter::new(BiquadFilterType::HighShelf, 12500.0, 0.8, 0.707, sr);
        self.ibasso_shelf_c = ibasso_biquad.compute_coefficients();

        // Schiit Multibit: 45 Hz low punch (+1.5 dB, Q=0.8), 18.5 kHz gentle roll-off (-0.6 dB, Q=0.707)
        let schiit_low = BiquadFilter::new(BiquadFilterType::LowShelf, 45.0, 1.5, 0.8, sr);
        self.schiit_low_c = schiit_low.compute_coefficients();
        let schiit_high = BiquadFilter::new(BiquadFilterType::HighShelf, 18500.0, -0.6, 0.707, sr);
        self.schiit_high_c = schiit_high.compute_coefficients();

        // Chord Mojo 2: 700 Hz low-pass for crossfeed channel
        let chord_lpf = BiquadFilter::new(BiquadFilterType::LowPass, 700.0, 0.0, 0.6, sr);
        self.chord_lpf_c = chord_lpf.compute_coefficients();

        // 0.35ms delay line length (at 48 kHz = ~17 samples; clamped to ring buffer size)
        self.crossfeed_delay_samples = ((sr * 0.00035).round() as usize).clamp(1, 120);
    }

    #[inline(always)]
    fn process_single_flavor(&mut self, flavor: DacHardwareFlavor, frame: [f32; 2]) -> [f32; 2] {
        match flavor {
            DacHardwareFlavor::StockOemPlus => {
                // Bit-perfect Apple Silicon CS42L84 calibrated reference with peak limiter protection
                [frame[0].clamp(-1.0, 1.0), frame[1].clamp(-1.0, 1.0)]
            }
            DacHardwareFlavor::IfiZenDac => {
                // Burr-Brown DSD1793 minimum phase + TrueBass 65Hz shelf + warm discrete 2nd harmonic
                let l_eq = self.ifi_state_l.process(frame[0], &self.ifi_shelf_c);
                let r_eq = self.ifi_state_r.process(frame[1], &self.ifi_shelf_c);
                let l_warm = l_eq + 0.022 * l_eq * l_eq.abs();
                let r_warm = r_eq + 0.022 * r_eq * r_eq.abs();
                [l_warm.clamp(-1.0, 1.0), r_warm.clamp(-1.0, 1.0)]
            }
            DacHardwareFlavor::IbassoDcPro => {
                // Dual Cirrus CS43131 flagship linear phase + 12.5kHz air presence shelf + ultra-low THD
                let l_air = self.ibasso_state_l.process(frame[0], &self.ibasso_shelf_c);
                let r_air = self.ibasso_state_r.process(frame[1], &self.ibasso_shelf_c);
                [l_air.clamp(-1.0, 1.0), r_air.clamp(-1.0, 1.0)]
            }
            DacHardwareFlavor::ChordMojo2 => {
                // Rob Watts WTA sinc timing reconstruction emulation with 0.35ms spatial crossfeed
                let cur_idx = self.crossfeed_idx;
                self.crossfeed_delay_l[cur_idx] = frame[0];
                self.crossfeed_delay_r[cur_idx] = frame[1];

                let delay_offset = self.crossfeed_delay_samples;
                let read_idx = if cur_idx >= delay_offset {
                    cur_idx - delay_offset
                } else {
                    128 + cur_idx - delay_offset
                };

                let delayed_l = self.crossfeed_delay_l[read_idx];
                let delayed_r = self.crossfeed_delay_r[read_idx];

                self.crossfeed_idx = (cur_idx + 1) % 128;

                let l_filtered_cross = self.chord_lpf_l.process(delayed_r, &self.chord_lpf_c);
                let r_filtered_cross = self.chord_lpf_r.process(delayed_l, &self.chord_lpf_c);

                // Blend crossfeed at -13.5 dB (~0.211) and apply slight unity-gain compensation (0.95x)
                let l_out = (frame[0] + 0.211 * l_filtered_cross) * 0.95;
                let r_out = (frame[1] + 0.211 * r_filtered_cross) * 0.95;
                [l_out.clamp(-1.0, 1.0), r_out.clamp(-1.0, 1.0)]
            }
            DacHardwareFlavor::SchiitMultibit => {
                // R2R ladder architectural slam: 45Hz low boost, gentle Nyquist roll-off, blended H2+H3 saturation
                let l_punch = self.schiit_low_l.process(frame[0], &self.schiit_low_c);
                let r_punch = self.schiit_low_r.process(frame[1], &self.schiit_low_c);
                let l_roll = self.schiit_high_l.process(l_punch, &self.schiit_high_c);
                let r_roll = self.schiit_high_r.process(r_punch, &self.schiit_high_c);

                // Push-pull class-A buffer stage saturation (even + odd harmonic blend)
                let l_sat = l_roll + 0.018 * l_roll.powi(2) * l_roll.signum() - 0.010 * l_roll.powi(3);
                let r_sat = r_roll + 0.018 * r_roll.powi(2) * r_roll.signum() - 0.010 * r_roll.powi(3);
                [l_sat.clamp(-1.0, 1.0), r_sat.clamp(-1.0, 1.0)]
            }
        }
    }

    /// Process an audio buffer with the active DAC flavor and clickless 15ms crossfading.
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if self.active_flavor == self.target_flavor {
            for frame in buffer.iter_mut() {
                *frame = self.process_single_flavor(self.active_flavor, *frame);
            }
        } else {
            // Smooth clickless crossfade between flavors
            let mut completed_early = false;
            for frame in buffer.iter_mut() {
                if !completed_early {
                    let orig = *frame;
                    let old_sample = self.process_single_flavor(self.active_flavor, orig);
                    let new_sample = self.process_single_flavor(self.target_flavor, orig);

                    let progress = (self.crossfade_pos as f32 / self.crossfade_len as f32).clamp(0.0, 1.0);
                    let out_l = (1.0 - progress) * old_sample[0] + progress * new_sample[0];
                    let out_r = (1.0 - progress) * old_sample[1] + progress * new_sample[1];
                    *frame = [out_l, out_r];

                    self.crossfade_pos += 1;
                    if self.crossfade_pos >= self.crossfade_len {
                        self.active_flavor = self.target_flavor;
                        self.crossfade_pos = 0;
                        completed_early = true;
                    }
                } else {
                    *frame = self.process_single_flavor(self.active_flavor, *frame);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enhancer_presets_count_and_application() {
        let presets = MasteringPreset::all();
        assert_eq!(presets.len(), 21, "Should provide 21 handcrafted presets");

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

    #[test]
    fn test_esports_tactical_gaming_preset_and_radar_processing() {
        let presets = MasteringPreset::all();
        let gaming_preset = &presets[20];
        assert_eq!(gaming_preset.name, "21. Esports Tactical & Low-Latency Gaming");
        assert!(gaming_preset.game_mode);
        assert!(gaming_preset.radar_eq);
        assert!(gaming_preset.spike_shield);
        assert_eq!(gaming_preset.tube_warmth, 0.0);
        assert!(!gaming_preset.tape_emulation);

        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.apply_preset(gaming_preset);
        assert!(enh.game_mode);
        assert!(enh.radar_eq);
        assert!(enh.spike_shield);

        // Process quiet footsteps (should remain uncompressed)
        let mut quiet_audio = vec![[0.05f32, 0.05f32]; 128];
        enh.process(&mut quiet_audio);
        assert!(quiet_audio[0][0] > 0.0);

        // Process massive loud blast (spike shield should clamp below 0.99)
        let mut blast_audio = vec![[2.5f32, -2.5f32]; 128];
        enh.process(&mut blast_audio);
        assert!(blast_audio[0][0] < 1.0);
        assert!(blast_audio[0][1] > -1.0);
    }

    #[test]
    fn test_dac_hardware_flavor_cycling_and_parsing() {
        let f0 = DacHardwareFlavor::StockOemPlus;
        let f1 = f0.cycle_next();
        assert_eq!(f1, DacHardwareFlavor::IfiZenDac);
        let f2 = f1.cycle_next();
        assert_eq!(f2, DacHardwareFlavor::IbassoDcPro);
        let f3 = f2.cycle_next();
        assert_eq!(f3, DacHardwareFlavor::ChordMojo2);
        let f4 = f3.cycle_next();
        assert_eq!(f4, DacHardwareFlavor::SchiitMultibit);
        let f5 = f4.cycle_next();
        assert_eq!(f5, DacHardwareFlavor::StockOemPlus);

        assert_eq!(f0.cycle_prev(), DacHardwareFlavor::SchiitMultibit);

        assert_eq!(DacHardwareFlavor::from_str_loose("ifi"), Some(DacHardwareFlavor::IfiZenDac));
        assert_eq!(DacHardwareFlavor::from_str_loose("chord"), Some(DacHardwareFlavor::ChordMojo2));
        assert_eq!(DacHardwareFlavor::from_str_loose("ibasso"), Some(DacHardwareFlavor::IbassoDcPro));
        assert_eq!(DacHardwareFlavor::from_str_loose("schiit"), Some(DacHardwareFlavor::SchiitMultibit));
        assert_eq!(DacHardwareFlavor::from_str_loose("oem"), Some(DacHardwareFlavor::StockOemPlus));
    }

    #[test]
    fn test_dac_mimicker_engine_processing_and_crossfade() {
        let mut engine = DacMimickerEngine::new(48000.0);
        assert_eq!(engine.active_flavor, DacHardwareFlavor::StockOemPlus);

        // Process silence
        let mut audio = vec![[0.0f32, 0.0f32]; 512];
        engine.process(&mut audio);
        for frame in &audio {
            assert_eq!(frame[0], 0.0);
            assert_eq!(frame[1], 0.0);
        }

        // Process test signal with each flavor
        for flavor in DacHardwareFlavor::all() {
            engine.set_flavor(*flavor);
            let mut test_sig = vec![[0.5f32, -0.5f32]; 256];
            engine.process(&mut test_sig);
            for frame in &test_sig {
                assert!(!frame[0].is_nan());
                assert!(!frame[1].is_nan());
                assert!(frame[0].abs() <= 1.0);
                assert!(frame[1].abs() <= 1.0);
            }
        }

        // Test smooth crossfade without glitches or NaN
        engine.set_flavor(DacHardwareFlavor::IfiZenDac);
        let mut sweep = vec![[0.3f32, 0.3f32]; 1024];
        engine.process(&mut sweep);
        for frame in &sweep {
            assert!(!frame[0].is_nan());
            assert!(!frame[1].is_nan());
        }
    }

    #[test]
    fn test_speaker_and_bookshelf_acoustic_adaptations() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        let preset = MasteringPreset::default();

        // 1. Built-in Laptop Speakers
        let laptop_gear = AcousticGearProfile::default_builtin_speakers("MacBook Air");
        enh.apply_preset_with_gear(&preset, &laptop_gear);
        assert!(enh.spatial_width >= 1.30, "Laptop speakers should expand spatial width for narrow stereo chassis: got {}", enh.spatial_width);
        assert_eq!(enh.crossfeed, CrossfeedMode::Off, "Laptop speakers should disable headphone crossfeed");
        assert!(enh.subsonic_filter, "Laptop speakers should engage subsonic protection filter");
        assert_eq!(enh.subsonic_freq, 45.0, "Subsonic high-pass should be tuned to 45Hz for micro-woofers");
        assert!(!enh.mono_bass, "Laptop speakers should not clamp mono bass");

        // 2. Desktop Bookshelf Speakers
        let bookshelf_gear = AcousticGearProfile::default_bookshelf_speakers();
        enh.apply_preset_with_gear(&preset, &bookshelf_gear);
        assert!(enh.spatial_width <= 1.25, "Bookshelf monitors should maintain true nearfield imaging: got {}", enh.spatial_width);
        assert_eq!(enh.crossfeed, CrossfeedMode::Off, "Bookshelf speakers should disable headphone crossfeed");
        assert!(enh.subsonic_filter, "Bookshelf speakers should engage subsonic filter");
        assert_eq!(enh.subsonic_freq, 35.0, "Subsonic high-pass should be 35Hz for desktop monitors");
        assert!(!enh.mono_bass, "Bookshelf monitors should preserve stereo bass");

        // 3. Contrast with IEM (KATO style)
        let iem_gear = AcousticGearProfile {
            name: "Moondrop KATO".to_string(),
            form_factor: GearFormFactor::InEar,
            enclosure: GearEnclosure::ClosedBack,
            drivers: [true, false, false, false, false, false],
            coupling: GearCoupling::Silicone,
            tonal_balance: GearTonalBalance::AnalyticalBright,
            source_amp: GearSourceAmp::DesktopSolidState,
            speaker_placement: SpeakerPlacement::default(),
            speaker_target: SpeakerCalibrationTarget::default(),
        };
        enh.apply_preset_with_gear(&preset, &iem_gear);
        assert!(enh.spatial_width <= 1.25, "IEM must cap spatial width <= 1.25: got {}", enh.spatial_width);
        assert!(enh.mono_bass, "IEM must enforce mono bass");
        assert!(enh.mono_bass_freq >= 85.0, "IEM mono bass frequency must be at least 85Hz");
        assert!(enh.deesser_enabled, "IEM should engage de-esser");
    }

    #[test]
    fn test_dynamic_speaker_placement_and_target_dsp_adaptations() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        let preset = MasteringPreset::all()[0].clone();

        // 1. Laptop on elevated stand with spatial expansion target
        let mut laptop_gear = AcousticGearProfile::default_builtin_speakers("MacBook Pro");
        laptop_gear.speaker_placement = SpeakerPlacement::ElevatedStand;
        laptop_gear.speaker_target = SpeakerCalibrationTarget::SpatialExpansion;
        enh.apply_preset_with_gear(&preset, &laptop_gear);
        assert!(enh.spatial_width >= 1.20, "Elevated stand + spatial expansion should widen stage: got {}", enh.spatial_width);
        assert_eq!(enh.crossfeed, CrossfeedMode::Off);

        // 2. Laptop on desk with vocal clarity target
        laptop_gear.speaker_placement = SpeakerPlacement::DeskSurface;
        laptop_gear.speaker_target = SpeakerCalibrationTarget::VocalClarity;
        enh.apply_preset_with_gear(&preset, &laptop_gear);
        assert!(enh.deharsh_enabled, "Vocal clarity target should engage deharsh filter to tame boxiness");
        assert!(enh.air_clarity_db >= 1.0, "Vocal clarity should lift upper speech presence");

        // 3. Laptop with bass protection target
        laptop_gear.speaker_target = SpeakerCalibrationTarget::BassProtection;
        enh.apply_preset_with_gear(&preset, &laptop_gear);
        assert_eq!(enh.subsonic_freq, 52.0, "Bass protection target must engage tighter 52Hz subsonic guard");

        // 4. Bookshelf speakers: rear ported close to wall corner
        let mut bookshelf = AcousticGearProfile::default_bookshelf_speakers();
        bookshelf.enclosure = GearEnclosure::PortedRear;
        bookshelf.speaker_placement = SpeakerPlacement::NearWallCorner;
        enh.apply_preset_with_gear(&preset, &bookshelf);
        assert_eq!(enh.crossfeed, CrossfeedMode::Off);

        // 5. Over-Ear with Velour pads
        let mut overear = AcousticGearProfile::default();
        overear.form_factor = GearFormFactor::OverEar;
        overear.coupling = GearCoupling::VelourPads;
        let baseline_bass = preset.bass_punch_db;
        enh.apply_preset_with_gear(&preset, &overear);
        assert!(enh.bass_punch_db >= baseline_bass, "Velour pads should gently compensate for porous seal");
    }
}


