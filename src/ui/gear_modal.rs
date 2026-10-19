//! Interactive Dynamic Acoustic Gear Profiling Wizard in pure Rust.
//!
//! Provides a dynamic, branch-specific questionnaire evaluating:
//! - Built-in Laptop Speakers: Chassis layout, desk boundary placement, calibration goals.
//! - Desktop Bookshelf Speakers: Monitor size, cabinet porting, desk isolation, room interface.
//! - Over-Ear / On-Ear Headphones: Enclosure topology, driver type, earpad material, tonal balance, amplification.
//! - In-Ear Monitors (IEMs) & Earbuds: Shell venting, driver topology, eartip coupling, tonal target, cable/DAC.
//! - Bone Conduction: Temporal bone placement, frequency compensation, wireless/wired link.

use crate::dsp::enhancer::{
    AcousticGearProfile, GearCoupling, GearEnclosure, GearFormFactor, GearSourceAmp,
    GearTonalBalance, SpeakerCalibrationTarget, SpeakerPlacement,
};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, Paragraph};

#[derive(Debug, Clone)]
pub struct GearWizardModal {
    pub is_open: bool,
    pub current_step: usize,
    pub selected_option: usize,
    pub custom_name: String,
    pub form_factor: GearFormFactor,
    pub enclosure: GearEnclosure,
    pub drivers: [bool; 6],
    pub coupling: GearCoupling,
    pub tonal_balance: GearTonalBalance,
    pub source_amp: GearSourceAmp,
    pub speaker_placement: SpeakerPlacement,
    pub speaker_target: SpeakerCalibrationTarget,
}

impl GearWizardModal {
    pub fn new() -> Self {
        Self {
            is_open: false,
            current_step: 0,
            selected_option: 0,
            custom_name: "Universal Reference Gear".to_string(),
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

    pub fn open(&mut self, current: &AcousticGearProfile) {
        self.is_open = true;
        self.current_step = 0;
        self.selected_option = 0;
        self.custom_name = current.name.clone();
        self.form_factor = current.form_factor;
        self.enclosure = current.enclosure;
        self.drivers = current.drivers;
        self.coupling = current.coupling;
        self.tonal_balance = current.tonal_balance;
        self.source_amp = current.source_amp;
        self.speaker_placement = current.speaker_placement;
        self.speaker_target = current.speaker_target;
    }

    pub fn close(&mut self) {
        self.is_open = false;
    }

    /// Total steps in the questionnaire depends dynamically on the transducer category.
    pub fn total_steps(&self) -> usize {
        match self.form_factor {
            GearFormFactor::BuiltinLaptopSpeakers => 5,
            GearFormFactor::DesktopBookshelfSpeakers => 6,
            GearFormFactor::BoneConduction => 5,
            GearFormFactor::InEar | GearFormFactor::Earbuds => 7,
            GearFormFactor::OverEar | GearFormFactor::OnEar => 7,
        }
    }

    pub fn is_naming_step(&self) -> bool {
        self.current_step >= self.total_steps().saturating_sub(1)
    }

    pub fn is_multi_select_step(&self) -> bool {
        // Multi-select driver selection for headphones and IEMs at step 2
        self.current_step == 2
            && matches!(
                self.form_factor,
                GearFormFactor::InEar
                    | GearFormFactor::Earbuds
                    | GearFormFactor::OverEar
                    | GearFormFactor::OnEar
            )
    }

    pub fn current_step_title(&self) -> String {
        let total = self.total_steps();
        let step_idx = self.current_step + 1;

        let name = match (self.form_factor, self.current_step) {
            (_, 0) => "FORM FACTOR & TRANSDUCER TYPE",

            // Laptop speakers branch
            (GearFormFactor::BuiltinLaptopSpeakers, 1) => "LAPTOP CHASSIS & SPEAKER LAYOUT",
            (GearFormFactor::BuiltinLaptopSpeakers, 2) => "PLACEMENT & DESK BOUNDARY",
            (GearFormFactor::BuiltinLaptopSpeakers, 3) => "PRIMARY ACOUSTIC CORRECTION TARGET",

            // Bookshelf speakers branch
            (GearFormFactor::DesktopBookshelfSpeakers, 1) => "MONITOR SIZE & DRIVER TOPOLOGY",
            (GearFormFactor::DesktopBookshelfSpeakers, 2) => "CABINET PORTING & ENCLOSURE",
            (GearFormFactor::DesktopBookshelfSpeakers, 3) => "DESK COUPLING & WALL PROXIMITY",
            (GearFormFactor::DesktopBookshelfSpeakers, 4) => "AMPLIFICATION & AUDIO INTERFACE",

            // Bone Conduction branch
            (GearFormFactor::BoneConduction, 1) => "TEMPORAL BONE MECHANICAL COUPLING",
            (GearFormFactor::BoneConduction, 2) => "TACTILE COMPENSATION PREFERENCE",
            (GearFormFactor::BoneConduction, 3) => "AUDIO CONNECTION & POWER",

            // IEM / Earbuds branch
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 1) => "IEM SHELL & VENTING ARCHITECTURE",
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 2) => "TRANSDUCER DRIVER TOPOLOGY",
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 3) => "EARTIP COUPLING & MATERIAL",
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 4) => "TARGET SOUND SIGNATURE",
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 5) => "CABLE CONNECTION & DAC/AMP",

            // Over-Ear / On-Ear Headphones branch
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 1) => "ACOUSTIC ENCLOSURE TOPOLOGY",
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 2) => "DRIVER TRANSDUCER ARCHITECTURE",
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 3) => "EARPAD MATERIAL & ACOUSTIC SEAL",
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 4) => "INNATE TONAL BALANCE OF GEAR",
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 5) => "AMPLIFICATION & SOURCE HARDWARE",

            // Naming step for all
            _ => "NAME & RENAME YOUR GEAR PROFILE",
        };

        format!("QUESTION {}/{}: {}", step_idx, total, name)
    }

    pub fn default_name_for_config(&self) -> String {
        match self.form_factor {
            GearFormFactor::BuiltinLaptopSpeakers => {
                let chassis = match self.enclosure {
                    GearEnclosure::SemiOpen => "Multi-Speaker Laptop",
                    GearEnclosure::ClosedBack => "Workstation Laptop",
                    _ => "Ultra-Thin Laptop",
                };
                let place = match self.speaker_placement {
                    SpeakerPlacement::ElevatedStand => "Stand",
                    SpeakerPlacement::SoftSurfaceOrLap => "Lap",
                    _ => "Desk",
                };
                let target = match self.speaker_target {
                    SpeakerCalibrationTarget::VocalClarity => "Vocal",
                    SpeakerCalibrationTarget::SpatialExpansion => "Spatial",
                    SpeakerCalibrationTarget::BassProtection => "Bass Guard",
                    SpeakerCalibrationTarget::FlatReference => "Reference",
                };
                format!("{} ({}, {})", chassis, place, target)
            }
            GearFormFactor::DesktopBookshelfSpeakers => {
                let size = if self.drivers[0] {
                    "3-4\" Compact"
                } else if self.drivers[1] {
                    "5-7\" Studio"
                } else if self.drivers[2] {
                    "8\"+ / Sub"
                } else {
                    "Point-Source"
                };
                let port = match self.enclosure {
                    GearEnclosure::PortedRear => "Rear-Ported",
                    GearEnclosure::PortedFront => "Front-Ported",
                    GearEnclosure::SealedSuspension => "Sealed",
                    _ => "Passive Radiator",
                };
                format!("{} Monitors ({})", size, port)
            }
            GearFormFactor::BoneConduction => {
                let placement = if self.coupling == GearCoupling::CustomMolded {
                    "Mastoid"
                } else {
                    "Zygomatic"
                };
                format!("Bone Conduction ({})", placement)
            }
            GearFormFactor::InEar => {
                let mut d_types = Vec::new();
                if self.drivers[0] { d_types.push("DD"); }
                if self.drivers[1] { d_types.push("Planar"); }
                if self.drivers[2] { d_types.push("BA"); }
                if self.drivers[3] { d_types.push("EST"); }
                if self.drivers[4] { d_types.push("Piezo"); }
                if self.drivers[5] { d_types.push("Bone"); }
                let d_str = if d_types.len() > 1 {
                    format!("Hybrid ({})", d_types.join("+"))
                } else if let Some(first) = d_types.first() {
                    first.to_string()
                } else {
                    "Custom".to_string()
                };
                let tips = match self.coupling {
                    GearCoupling::MemoryFoam => "Foam Tips",
                    GearCoupling::CustomMolded => "Custom Acrylic",
                    _ => "Silicone Tips",
                };
                format!("{} IEM ({})", d_str, tips)
            }
            GearFormFactor::Earbuds => "Open-Fit Earbuds".to_string(),
            GearFormFactor::OverEar | GearFormFactor::OnEar => {
                let enc = match self.enclosure {
                    GearEnclosure::OpenBack => "Open-Back",
                    GearEnclosure::SemiOpen => "Semi-Open",
                    GearEnclosure::ClosedBack => "Closed-Back",
                    GearEnclosure::Anc => "ANC",
                    _ => "Reference",
                };
                let driver = if self.drivers[1] {
                    "Planar"
                } else if self.drivers[3] {
                    "Electrostatic"
                } else {
                    "Dynamic"
                };
                let ff = if self.form_factor == GearFormFactor::OverEar {
                    "Over-Ear"
                } else {
                    "On-Ear"
                };
                format!("{} {} {}", driver, enc, ff)
            }
        }
    }

    pub fn build_profile(&self) -> AcousticGearProfile {
        let final_name = if self.custom_name.trim().is_empty() {
            self.default_name_for_config()
        } else {
            self.custom_name.trim().to_string()
        };
        AcousticGearProfile {
            name: final_name,
            form_factor: self.form_factor,
            enclosure: self.enclosure,
            drivers: self.drivers,
            coupling: self.coupling,
            tonal_balance: self.tonal_balance,
            source_amp: self.source_amp,
            speaker_placement: self.speaker_placement,
            speaker_target: self.speaker_target,
        }
    }

    /// Handle key events. Returns `Some(AcousticGearProfile)` upon completion.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AcousticGearProfile> {
        let last_step = self.total_steps().saturating_sub(1);

        match code {
            KeyCode::Esc => {
                self.close();
                None
            }
            KeyCode::Char(c) if self.current_step == last_step => {
                if self.custom_name.len() < 36 {
                    self.custom_name.push(c);
                }
                None
            }
            KeyCode::Backspace if self.current_step == last_step => {
                self.custom_name.pop();
                None
            }
            KeyCode::Up => {
                if self.current_step < last_step {
                    self.selected_option = self.selected_option.saturating_sub(1);
                }
                None
            }
            KeyCode::Down => {
                if self.current_step < last_step {
                    let max_opts = self.options_for_step(self.current_step).len().saturating_sub(1);
                    if self.selected_option < max_opts {
                        self.selected_option += 1;
                    }
                }
                None
            }
            KeyCode::Char(' ') if self.is_multi_select_step() => {
                // Multi-select toggle for driver topology
                if self.selected_option < 6 {
                    self.drivers[self.selected_option] = !self.drivers[self.selected_option];
                }
                None
            }
            KeyCode::Enter => {
                if self.current_step == last_step {
                    if self.custom_name.trim().is_empty() {
                        self.custom_name = self.default_name_for_config();
                    }
                    self.is_open = false;
                    return Some(self.build_profile());
                }

                // Commit choice based on active branch and step
                match (self.form_factor, self.current_step) {
                    (_, 0) => {
                        self.form_factor = match self.selected_option {
                            0 => GearFormFactor::OverEar,
                            1 => GearFormFactor::OnEar,
                            2 => GearFormFactor::InEar,
                            3 => GearFormFactor::Earbuds,
                            4 => GearFormFactor::BoneConduction,
                            5 => GearFormFactor::BuiltinLaptopSpeakers,
                            _ => GearFormFactor::DesktopBookshelfSpeakers,
                        };
                        // Set sensible defaults for the selected branch
                        match self.form_factor {
                            GearFormFactor::BuiltinLaptopSpeakers => {
                                self.enclosure = GearEnclosure::OpenBack;
                                self.speaker_placement = SpeakerPlacement::DeskSurface;
                                self.speaker_target = SpeakerCalibrationTarget::VocalClarity;
                            }
                            GearFormFactor::DesktopBookshelfSpeakers => {
                                self.enclosure = GearEnclosure::PortedRear;
                                self.drivers = [false, true, false, false, false, false];
                                self.speaker_placement = SpeakerPlacement::ElevatedStand;
                                self.source_amp = GearSourceAmp::ActivePoweredMonitors;
                            }
                            GearFormFactor::BoneConduction => {
                                self.drivers = [false, false, false, false, false, true];
                                self.coupling = GearCoupling::OpenAir;
                                self.source_amp = GearSourceAmp::BluetoothWireless;
                            }
                            _ => {}
                        }
                    }

                    // --- BUILT-IN LAPTOP SPEAKERS ---
                    (GearFormFactor::BuiltinLaptopSpeakers, 1) => {
                        self.enclosure = match self.selected_option {
                            0 => GearEnclosure::OpenBack,   // Ultra-Thin
                            1 => GearEnclosure::SemiOpen,   // Performance Multi-Speaker
                            _ => GearEnclosure::ClosedBack, // Workstation Downward
                        };
                    }
                    (GearFormFactor::BuiltinLaptopSpeakers, 2) => {
                        self.speaker_placement = match self.selected_option {
                            0 => SpeakerPlacement::DeskSurface,
                            1 => SpeakerPlacement::ElevatedStand,
                            _ => SpeakerPlacement::SoftSurfaceOrLap,
                        };
                    }
                    (GearFormFactor::BuiltinLaptopSpeakers, 3) => {
                        self.speaker_target = match self.selected_option {
                            0 => SpeakerCalibrationTarget::VocalClarity,
                            1 => SpeakerCalibrationTarget::SpatialExpansion,
                            2 => SpeakerCalibrationTarget::BassProtection,
                            _ => SpeakerCalibrationTarget::FlatReference,
                        };
                    }

                    // --- DESKTOP BOOKSHELF SPEAKERS ---
                    (GearFormFactor::DesktopBookshelfSpeakers, 1) => {
                        self.drivers = [false, false, false, false, false, false];
                        self.drivers[self.selected_option.min(3)] = true;
                    }
                    (GearFormFactor::DesktopBookshelfSpeakers, 2) => {
                        self.enclosure = match self.selected_option {
                            0 => GearEnclosure::PortedRear,
                            1 => GearEnclosure::PortedFront,
                            2 => GearEnclosure::SealedSuspension,
                            _ => GearEnclosure::PassiveRadiator,
                        };
                    }
                    (GearFormFactor::DesktopBookshelfSpeakers, 3) => {
                        self.speaker_placement = match self.selected_option {
                            0 => SpeakerPlacement::ElevatedStand,
                            1 => SpeakerPlacement::DeskSurface,
                            2 => SpeakerPlacement::NearWallCorner,
                            _ => SpeakerPlacement::FreeField,
                        };
                    }
                    (GearFormFactor::DesktopBookshelfSpeakers, 4) => {
                        self.source_amp = match self.selected_option {
                            0 => GearSourceAmp::ActivePoweredMonitors,
                            1 => GearSourceAmp::PassiveWithStereoAmp,
                            2 => GearSourceAmp::BalancedAudioInterface,
                            _ => GearSourceAmp::BluetoothWireless,
                        };
                    }

                    // --- BONE CONDUCTION ---
                    (GearFormFactor::BoneConduction, 1) => {
                        self.coupling = match self.selected_option {
                            0 => GearCoupling::OpenAir,      // Zygomatic Arch
                            _ => GearCoupling::CustomMolded, // Mastoid Process
                        };
                    }
                    (GearFormFactor::BoneConduction, 2) => {
                        self.tonal_balance = match self.selected_option {
                            0 => GearTonalBalance::NeutralStudio,   // Vocal Clarity
                            1 => GearTonalBalance::AnalyticalBright, // Air Restoration
                            _ => GearTonalBalance::BassHeavy,        // Tactile Bass
                        };
                    }
                    (GearFormFactor::BoneConduction, 3) => {
                        self.source_amp = match self.selected_option {
                            0 => GearSourceAmp::BluetoothWireless,
                            _ => GearSourceAmp::DesktopSolidState,
                        };
                    }

                    // --- HEADPHONES & IEMS ---
                    (_, 1) => {
                        self.enclosure = match self.selected_option {
                            0 => GearEnclosure::OpenBack,
                            1 => GearEnclosure::SemiOpen,
                            2 => GearEnclosure::ClosedBack,
                            _ => GearEnclosure::Anc,
                        };
                    }
                    (_, 2) => {
                        if !self.drivers.iter().any(|&d| d) {
                            self.drivers[0] = true;
                        }
                    }
                    (_, 3) => {
                        if matches!(self.form_factor, GearFormFactor::InEar | GearFormFactor::Earbuds) {
                            self.coupling = match self.selected_option {
                                0 => GearCoupling::Silicone,
                                1 => GearCoupling::MemoryFoam,
                                2 => GearCoupling::CustomMolded,
                                _ => GearCoupling::OpenAir,
                            };
                        } else {
                            self.coupling = match self.selected_option {
                                0 => GearCoupling::VelourPads,
                                1 => GearCoupling::LeatherPads,
                                _ => GearCoupling::HybridPads,
                            };
                        }
                    }
                    (_, 4) => {
                        self.tonal_balance = match self.selected_option {
                            0 => GearTonalBalance::AnalyticalBright,
                            1 => GearTonalBalance::DarkWarm,
                            2 => GearTonalBalance::BassHeavy,
                            3 => GearTonalBalance::VShaped,
                            _ => GearTonalBalance::NeutralStudio,
                        };
                    }
                    (_, 5) => {
                        self.source_amp = match self.selected_option {
                            0 => GearSourceAmp::PortableDongle,
                            1 => GearSourceAmp::DesktopSolidState,
                            2 => GearSourceAmp::TubeAmp,
                            _ => GearSourceAmp::BluetoothWireless,
                        };
                    }

                    _ => {}
                }

                // Advance to next step
                self.current_step += 1;
                self.selected_option = 0;

                // When entering final naming step, pre-fill default name if unset
                if self.current_step == self.total_steps().saturating_sub(1) {
                    if self.custom_name.is_empty() || self.custom_name == "Universal Reference Gear" {
                        self.custom_name = self.default_name_for_config();
                    }
                }
                None
            }
            _ => None,
        }
    }

    pub fn options_for_step(&self, step: usize) -> Vec<(&'static str, &'static str)> {
        if step == 0 {
            return vec![
                ("Over-Ear Headphones", "Circumaural earcups enclosing the outer ear."),
                ("On-Ear Headphones", "Supra-aural cushions resting directly on the ear cartilage."),
                ("In-Ear Monitors (IEM)", "Sealed acoustic canal coupling bypassing the pinna."),
                ("Earbuds / Open-Fit", "Rest in concha without deep acoustic ear-canal seal."),
                ("Bone Conduction", "Tactile transducers vibrating the temporal bone."),
                ("Built-in Laptop Speakers", "Integrated micro-drivers firing upward or via keyboard vents."),
                ("Desktop Bookshelf Speakers", "Near-field 2-way / 3-way stereo active or passive monitors."),
            ];
        }

        match (self.form_factor, step) {
            // BUILT-IN LAPTOP SPEAKERS
            (GearFormFactor::BuiltinLaptopSpeakers, 1) => vec![
                ("Ultra-Thin / Compact Laptop", "Thin unibody enclosure (MacBook Air, XPS 13); prone to 500-800Hz chassis resonance."),
                ("Performance Multi-Speaker Laptop", "Force-cancelling dual woofers + tweeters (MacBook Pro 14/16); clean sub-bass down to 48Hz."),
                ("Workstation / Downward-Firing", "Drivers firing downward into table surface; reflection causes comb filtering."),
            ],
            (GearFormFactor::BuiltinLaptopSpeakers, 2) => vec![
                ("Hard Wooden / Glass Desk Surface", "Firm reflective boundary: boosts 150-300Hz lower-mid warmth and crisp presence."),
                ("Elevated on Laptop Stand", "Free-air dispersion: eliminates desk boundary loading for uncolored midrange."),
                ("On Lap / Soft Bed / Sofa", "Absorptive boundary: chassis vibrations and high frequencies are damped."),
            ],
            (GearFormFactor::BuiltinLaptopSpeakers, 3) => vec![
                ("Dialogue & Vocal Clarity", "Attenuates boxy 600Hz chassis resonances; enhances 2kHz-4kHz speech presence."),
                ("Cinematic Spatial Expansion", "Interaural crosstalk cancellation and gentle phase widening beyond physical chassis."),
                ("Psychoacoustic Bass Protection", "48Hz subsonic protection high-pass and harmonic overtone synthesis."),
                ("Flat / Neutral Reference", "Linearizes frequency balance to provide an uncolored reference for monitoring."),
            ],

            // DESKTOP BOOKSHELF SPEAKERS
            (GearFormFactor::DesktopBookshelfSpeakers, 1) => vec![
                ("Compact 3\" - 4\" Nearfield", "Desktop footprint, rapid roll-off below 65Hz; benefits from excursion limiting."),
                ("Standard 5\" - 7\" Studio Monitors", "2-way bi-amplified active monitors; linear response down to 45Hz."),
                ("8\"+ Midfield or 2.1 Subwoofer", "Full-range 25Hz-20kHz output; requires sub-bass phase alignment and room control."),
                ("Coaxial Point-Source / Full-Range", "Single acoustic point source; symmetrical dispersion and uniform phase coherence."),
            ],
            (GearFormFactor::DesktopBookshelfSpeakers, 2) => vec![
                ("Rear Bass-Reflex Port", "Acoustic port on back of cabinet; sensitive to rear wall proximity and boundary boom."),
                ("Front Bass-Reflex Port", "Port fires forward; allows closer wall placement without excessive boundary boost."),
                ("Sealed Acoustic Suspension", "Airtight cabinet; tight transient decay and smooth 12dB/octave gentle roll-off."),
                ("Passive Radiator", "Drone cone replaces open port; deep bass extension without aerodynamic turbulence."),
            ],
            (GearFormFactor::DesktopBookshelfSpeakers, 3) => vec![
                ("Decoupled on Isolation Pads / Stands", "Isolated from desk surface; tightens transient bass decay and clarifies vocal imaging."),
                ("Direct on Desk Surface (No pads)", "Transfers vibration to desk; causes acoustic reflection comb-filtering at 200-400Hz."),
                ("Corner / Close Wall (< 15 cm)", "Boundary loading introduces +6dB low-frequency shelf boost; requires boundary compensation."),
                ("Free-Field Placement (> 50 cm)", "Minimal acoustic boundary loading; produces natural, unexaggerated low-end response."),
            ],
            (GearFormFactor::DesktopBookshelfSpeakers, 4) => vec![
                ("Active Powered Monitors", "Built-in Class D/AB bi-amplification connected via USB DAC or line out."),
                ("Passive Monitors + Stereo Amp", "External stereo integrated amplifier or receiver."),
                ("Balanced Studio Audio Interface", "Pro audio interface with balanced TRS/XLR connections."),
                ("Bluetooth / Wireless Monitors", "Wireless active studio monitors."),
            ],

            // BONE CONDUCTION
            (GearFormFactor::BoneConduction, 1) => vec![
                ("Zygomatic Arch (In front of tragus)", "Crisp high frequencies and tactile speech vibration."),
                ("Mastoid Process (Behind the ear)", "Deeper tactile low-frequency resonance into skull bone."),
            ],
            (GearFormFactor::BoneConduction, 2) => vec![
                ("Vocal & Speech Intelligibility", "Enhances 1kHz-3.5kHz speech band for clear podcasts and calls."),
                ("High-Frequency Air Restoration", "Pultec air shelf to overcome skull mechanical damping."),
                ("Maximum Tactile Bass Impact", "Enhances sub-harmonic punch for outdoor workouts."),
            ],
            (GearFormFactor::BoneConduction, 3) => vec![
                ("Bluetooth Wireless", "Internal wireless receiver with battery-powered motor driver."),
                ("Wired 3.5mm Connection", "Direct analog cable connection to DAC/Amp."),
            ],

            // IN-EAR MONITORS & EARBUDS
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 1) => vec![
                ("Fully Sealed Acoustic Resin Shell", "Maximum passive isolation, deep sub-bass acoustic pressure."),
                ("Front/Rear Micro-Vented Shell", "Acoustic relief vents: natural dynamic bass decay, reduces ear fatigue."),
                ("Open-Fit Concha Earbud", "Non-sealing flathead earbud resting in outer ear."),
            ],
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 2) => vec![
                ("Dynamic Driver (DD)", "Moving-coil diaphragm with natural acoustic mass & punch."),
                ("Planar Magnetic", "Orthodynamic membrane with ultra-low distortion & linear bass."),
                ("Balanced Armature (BA)", "Micro-reed transducer with lightning speed & micro-detail."),
                ("Electrostatic (EST Tweeter)", "Virtually zero-mass film with holographic upper air."),
                ("Piezoelectric Tweeter", "Ceramic ultra-high frequency acoustic resonant element."),
                ("Bone Conduction Motor", "Low-frequency tactile skull driver."),
            ],
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 3) => vec![
                ("Silicone Eartips", "Standard wide/narrow-bore tips with linear treble transfer."),
                ("Memory Foam Tips", "High acoustic isolation, absorbs 8-10 kHz high-frequency glare."),
                ("Custom Molded Acrylic", "Acoustic lock matching ear-canal anatomy perfectly."),
                ("Open-Air Foam Covers", "Soft cushion covers for non-sealing earbuds."),
            ],
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 4) => vec![
                ("Harman Target 2019", "Sub-bass shelf + 3kHz pinna gain boost for vocal presence."),
                ("Neutral / Diffuse Field", "Flat studio monitor tuning, polite bass, prominent midrange."),
                ("Warm & Mid-Centric", "Lush vocals, smooth non-fatiguing treble, rich mid-bass."),
                ("V-Shaped Response", "Boosted sub-bass & highs, recessed midrange vocals."),
                ("Analytical / Bright", "Forward treble energy, clinical detail extraction."),
            ],
            (GearFormFactor::InEar | GearFormFactor::Earbuds, 5) => vec![
                ("Standard 3.5mm Single-Ended", "Direct laptop / dongle DAC connection."),
                ("Balanced 4.4mm / 2.5mm Pentaconn", "High channel separation, lower crosstalk, high signal-to-noise."),
                ("Bluetooth DAC / TWS Adapter", "Wireless neckband or TWS adapters (LDAC/aptX)."),
            ],

            // OVER-EAR & ON-EAR HEADPHONES
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 1) => vec![
                ("Open-Back Enclosure", "Acoustically transparent grilles, zero internal backwave pressure."),
                ("Semi-Open Enclosure", "Damped acoustic vents with partial pressure isolation."),
                ("Closed-Back Enclosure", "Sealed acoustic earcups, high passive isolation & bass pressure."),
                ("Active Noise Cancelling (ANC)", "Internal DSP microphones & sealed acoustic chamber."),
            ],
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 2) => vec![
                ("Dynamic Driver (DD)", "Moving-coil diaphragm with natural acoustic mass & punch."),
                ("Planar Magnetic", "Orthodynamic membrane with ultra-low distortion & linear bass."),
                ("Electrostatic (EST)", "Virtually zero-mass film with holographic upper air."),
                ("Beryllium / DLC Dynamic", "Ultra-stiff high-rigidity dome; extended treble without breakup."),
            ],
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 3) => vec![
                ("Velour / Alcantara / Suede", "Breathable mesh: absorbs highs, slightly relieves sub-bass seal."),
                ("Leather / Sheepskin / Pleather", "Airtight seal: maximizes acoustic pressure and sub-bass slam."),
                ("Hybrid Perforated", "Perforated inner wall: balances soundstage with linear bass extension."),
            ],
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 4) => vec![
                ("Analytical / Bright / Sibilant", "Forward treble energy, prone to listening fatigue."),
                ("Dark / Warm / Relaxed", "Recessed treble and thick, rich lower midrange."),
                ("Bass-Heavy / Boomy", "Pronounced sub/mid-bass, risk of low-frequency masking."),
                ("V-Shaped Response", "Boosted sub-bass & highs, recessed midrange vocals."),
                ("Neutral / Studio Reference", "Flat target curve with linear acoustic balance."),
            ],
            (GearFormFactor::OverEar | GearFormFactor::OnEar, 5) => vec![
                ("Direct 3.5mm Jack", "Laptop or phone audio output jack."),
                ("Portable Dongle / Phone DAC", "Low-voltage mobile source with clean digital conversion."),
                ("Desktop Solid-State Amp", "High-power amplifier with near-zero output impedance."),
                ("Vacuum Tube / OTL Amp", "High output impedance with natural even harmonics."),
                ("Bluetooth Wireless", "Internal wireless receiver with active hardware DAC."),
            ],

            _ => vec![],
        }
    }

    pub fn render(&self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        if !self.is_open {
            return;
        }

        let modal_w = (area.width * 75 / 100).clamp(65, 95);
        let modal_h = 22.min(area.height.saturating_sub(4));
        let x = (area.width.saturating_sub(modal_w)) / 2;
        let y = (area.height.saturating_sub(modal_h)) / 2;
        let modal_area = Rect::new(x, y, modal_w, modal_h);

        f.render_widget(Clear, modal_area);

        let block = Block::default()
            .title(format!(" ACOUSTIC GEAR PROFILING WIZARD | {} ", self.current_step_title()))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary).add_modifier(Modifier::BOLD));
        let inner = block.inner(modal_area);
        f.render_widget(block, modal_area);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2), // Prompt instruction
                Constraint::Min(8),    // Options list or text input
                Constraint::Length(2), // Helper hotkeys
            ])
            .split(inner);

        let instruction = if self.is_naming_step() {
            "Custom Gear Profile Naming (Type custom name, [Backspace] to edit, [Enter] to finish):"
        } else if self.is_multi_select_step() {
            "Select driver technologies present in your gear (Press [Space] to toggle, [Enter] to confirm):"
        } else {
            "Select your listening hardware characteristics (Use [Up/Down] to select, [Enter] to confirm):"
        };
        let p_inst = Paragraph::new(instruction)
            .style(Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD));
        f.render_widget(p_inst, chunks[0]);

        if self.is_naming_step() {
            let prompt = Paragraph::new(vec![
                Line::from(Span::styled(
                    "Name your calibrated gear profile (or press Enter to accept generated default):",
                    Style::default().fg(theme.text).add_modifier(Modifier::BOLD),
                )),
                Line::from(""),
                Line::from(vec![
                    Span::styled(" Profile Name: ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
                    Span::styled(format!(" [ {}_ ] ", self.custom_name), Style::default().fg(theme.accent).bg(theme.surface).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(""),
                Line::from(vec![
                    Span::styled(" Form Factor: ", Style::default().fg(theme.text_dim)),
                    Span::styled(self.form_factor_display(), Style::default().fg(theme.text)),
                ]),
                Line::from(vec![
                    Span::styled(" Auto Target: ", Style::default().fg(theme.text_dim)),
                    Span::styled(self.default_name_for_config(), Style::default().fg(theme.warning)),
                ]),
            ]);
            f.render_widget(prompt, chunks[1]);
        } else {
            let opts = self.options_for_step(self.current_step);
            let mut lines = Vec::new();

            for (idx, (label, desc)) in opts.iter().enumerate() {
                let is_sel = idx == self.selected_option;
                let is_checked = if self.is_multi_select_step() && idx < 6 {
                    self.drivers[idx]
                } else {
                    false
                };

                let marker = if self.is_multi_select_step() {
                    if is_checked { "[X] " } else { "[ ] " }
                } else if is_sel {
                    " ▸ "
                } else {
                    "   "
                };

                let item_style = if is_sel {
                    Style::default().fg(theme.accent).bg(theme.surface).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(theme.text)
                };

                lines.push(Line::from(vec![
                    Span::styled(marker, item_style),
                    Span::styled(*label, item_style),
                ]));

                let desc_style = if is_sel {
                    Style::default().fg(theme.primary)
                } else {
                    Style::default().fg(theme.text_dim)
                };
                lines.push(Line::from(vec![
                    Span::styled("       └─ ", desc_style),
                    Span::styled(*desc, desc_style),
                ]));
            }

            let p_opts = Paragraph::new(lines);
            f.render_widget(p_opts, chunks[1]);
        }

        let help = if self.is_naming_step() {
            "[Enter] Save Profile & Calibrate | [Backspace] Delete | [Esc] Cancel"
        } else if self.is_multi_select_step() {
            "[Up/Down] Navigate | [Space] Toggle Driver | [Enter] Confirm Drivers | [Esc] Cancel"
        } else {
            "[Up/Down] Navigate Options | [Enter] Select & Next Question | [Esc] Cancel"
        };
        let p_help = Paragraph::new(help)
            .alignment(Alignment::Center)
            .style(Style::default().fg(theme.text_dim));
        f.render_widget(p_help, chunks[2]);
    }

    fn form_factor_display(&self) -> &'static str {
        match self.form_factor {
            GearFormFactor::OverEar => "Over-Ear Headphones",
            GearFormFactor::OnEar => "On-Ear Headphones",
            GearFormFactor::InEar => "In-Ear Monitors (IEM)",
            GearFormFactor::Earbuds => "Earbuds / Open-Fit",
            GearFormFactor::BuiltinLaptopSpeakers => "Built-in Laptop Speakers",
            GearFormFactor::DesktopBookshelfSpeakers => "Desktop Bookshelf Speakers",
            GearFormFactor::BoneConduction => "Bone Conduction",
        }
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gear_wizard_laptop_speakers_branch_flow() {
        let mut wizard = GearWizardModal::new();
        wizard.open(&AcousticGearProfile::default());

        assert_eq!(wizard.current_step, 0);
        assert_eq!(wizard.total_steps(), 7); // Initial Over-Ear default

        // Step 0: Select Built-in Laptop Speakers (option 5)
        wizard.selected_option = 5;
        let res = wizard.handle_key(KeyCode::Enter);
        assert!(res.is_none());
        assert_eq!(wizard.form_factor, GearFormFactor::BuiltinLaptopSpeakers);
        assert_eq!(wizard.current_step, 1);
        assert_eq!(wizard.total_steps(), 5); // Dynamically updated to 5 steps!

        // Step 1: Laptop Chassis (Performance Multi-Speaker, option 1)
        assert_eq!(wizard.current_step_title(), "QUESTION 2/5: LAPTOP CHASSIS & SPEAKER LAYOUT");
        wizard.selected_option = 1;
        let res = wizard.handle_key(KeyCode::Enter);
        assert!(res.is_none());
        assert_eq!(wizard.enclosure, GearEnclosure::SemiOpen);
        assert_eq!(wizard.current_step, 2);

        // Step 2: Placement & Desk Boundary (Elevated Stand, option 1)
        assert_eq!(wizard.current_step_title(), "QUESTION 3/5: PLACEMENT & DESK BOUNDARY");
        wizard.selected_option = 1;
        let res = wizard.handle_key(KeyCode::Enter);
        assert!(res.is_none());
        assert_eq!(wizard.speaker_placement, SpeakerPlacement::ElevatedStand);
        assert_eq!(wizard.current_step, 3);

        // Step 3: Primary Calibration Goal (Dialogue & Vocal Clarity, option 0)
        assert_eq!(wizard.current_step_title(), "QUESTION 4/5: PRIMARY ACOUSTIC CORRECTION TARGET");
        wizard.selected_option = 0;
        let res = wizard.handle_key(KeyCode::Enter);
        assert!(res.is_none());
        assert_eq!(wizard.speaker_target, SpeakerCalibrationTarget::VocalClarity);
        assert_eq!(wizard.current_step, 4);

        // Step 4: Final Naming Step
        assert!(wizard.is_naming_step());
        assert_eq!(wizard.current_step_title(), "QUESTION 5/5: NAME & RENAME YOUR GEAR PROFILE");
        let profile = wizard.handle_key(KeyCode::Enter).expect("Profile should be built");
        assert_eq!(profile.form_factor, GearFormFactor::BuiltinLaptopSpeakers);
        assert_eq!(profile.enclosure, GearEnclosure::SemiOpen);
        assert_eq!(profile.speaker_placement, SpeakerPlacement::ElevatedStand);
        assert_eq!(profile.speaker_target, SpeakerCalibrationTarget::VocalClarity);
        assert!(!profile.name.is_empty());
    }

    #[test]
    fn test_gear_wizard_bookshelf_speakers_branch_flow() {
        let mut wizard = GearWizardModal::new();
        wizard.open(&AcousticGearProfile::default());

        // Step 0: Select Desktop Bookshelf Speakers (option 6)
        wizard.selected_option = 6;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.form_factor, GearFormFactor::DesktopBookshelfSpeakers);
        assert_eq!(wizard.total_steps(), 6);
        assert_eq!(wizard.current_step, 1);

        // Step 1: Monitor Size (Standard 5"-7" Studio Monitors, option 1)
        assert_eq!(wizard.current_step_title(), "QUESTION 2/6: MONITOR SIZE & DRIVER TOPOLOGY");
        wizard.selected_option = 1;
        wizard.handle_key(KeyCode::Enter);
        assert!(wizard.drivers[1]);
        assert_eq!(wizard.current_step, 2);

        // Step 2: Cabinet Porting (Rear Bass-Reflex Port, option 0)
        assert_eq!(wizard.current_step_title(), "QUESTION 3/6: CABINET PORTING & ENCLOSURE");
        wizard.selected_option = 0;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.enclosure, GearEnclosure::PortedRear);
        assert_eq!(wizard.current_step, 3);

        // Step 3: Desk Coupling & Wall Proximity (Decoupled on Isolation Pads, option 0)
        assert_eq!(wizard.current_step_title(), "QUESTION 4/6: DESK COUPLING & WALL PROXIMITY");
        wizard.selected_option = 0;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.speaker_placement, SpeakerPlacement::ElevatedStand);
        assert_eq!(wizard.current_step, 4);

        // Step 4: Amplification & Audio Interface (Balanced Studio Audio Interface, option 2)
        assert_eq!(wizard.current_step_title(), "QUESTION 5/6: AMPLIFICATION & AUDIO INTERFACE");
        wizard.selected_option = 2;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.source_amp, GearSourceAmp::BalancedAudioInterface);
        assert_eq!(wizard.current_step, 5);

        // Step 5: Name and Finish
        assert!(wizard.is_naming_step());
        let profile = wizard.handle_key(KeyCode::Enter).expect("Profile should be built");
        assert_eq!(profile.form_factor, GearFormFactor::DesktopBookshelfSpeakers);
        assert_eq!(profile.enclosure, GearEnclosure::PortedRear);
        assert_eq!(profile.speaker_placement, SpeakerPlacement::ElevatedStand);
        assert_eq!(profile.source_amp, GearSourceAmp::BalancedAudioInterface);
    }

    #[test]
    fn test_gear_wizard_headphones_multi_select_and_pads() {
        let mut wizard = GearWizardModal::new();
        wizard.open(&AcousticGearProfile::default());

        // Step 0: Over-Ear (option 0)
        wizard.selected_option = 0;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.total_steps(), 7);

        // Step 1: Open-Back (option 0)
        wizard.selected_option = 0;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.enclosure, GearEnclosure::OpenBack);

        // Step 2: Driver (Planar Magnetic toggle with Space)
        assert!(wizard.is_multi_select_step());
        wizard.selected_option = 1;
        wizard.handle_key(KeyCode::Char(' ')); // toggle planar
        wizard.handle_key(KeyCode::Enter);
        assert!(wizard.drivers[1]);

        // Step 3: Earpad Material (Velour Pads, option 0)
        assert_eq!(wizard.current_step_title(), "QUESTION 4/7: EARPAD MATERIAL & ACOUSTIC SEAL");
        wizard.selected_option = 0;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.coupling, GearCoupling::VelourPads);

        // Step 4: Tonal Balance (Studio Neutral, option 4)
        wizard.selected_option = 4;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.tonal_balance, GearTonalBalance::NeutralStudio);

        // Step 5: Amp (Desktop Solid-State, option 1)
        wizard.selected_option = 1;
        wizard.handle_key(KeyCode::Enter);
        assert_eq!(wizard.source_amp, GearSourceAmp::DesktopSolidState);

        // Step 6: Custom Name editing
        assert!(wizard.is_naming_step());
        wizard.handle_key(KeyCode::Char('!'));
        let profile = wizard.handle_key(KeyCode::Enter).expect("Profile completed");
        assert_eq!(profile.form_factor, GearFormFactor::OverEar);
        assert_eq!(profile.coupling, GearCoupling::VelourPads);
    }
}
