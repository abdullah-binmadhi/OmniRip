//! Interactive Acoustic Gear Profiling Wizard in pure Rust.
//!
//! Provides a 6-step dynamic questionnaire evaluating:
//! 1. Form Factor & Ear Placement (Over-Ear, On-Ear, IEM, Earbuds, Bone Conduction)
//! 2. Acoustic Enclosure Topology (Open-Back, Semi-Open, Closed-Back, ANC)
//! 3. Driver Transducer Architecture (Dynamic, Planar, BA, EST, Piezo, Bone Conduction - Multi-Select)
//! 4. Ear Coupling & Eartip Material (Silicone, Foam, Custom Molded, Open-Air)
//! 5. Innate Tonal Balance (Analytical/Bright, Dark/Warm, Bass-Heavy, V-Shaped, Neutral Studio)
//! 6. Amplification & Source Hardware (Dongle, Desktop Solid-State, Tube Amp, Bluetooth)

use crate::dsp::enhancer::{
    AcousticGearProfile, GearCoupling, GearEnclosure, GearFormFactor, GearSourceAmp,
    GearTonalBalance,
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
    }

    pub fn close(&mut self) {
        self.is_open = false;
    }

    pub fn default_name_for_config(&self) -> String {
        let ff = match self.form_factor {
            GearFormFactor::OverEar => "Over-Ear",
            GearFormFactor::OnEar => "On-Ear",
            GearFormFactor::InEar => "IEM",
            GearFormFactor::Earbuds => "Earbuds",
            GearFormFactor::BoneConduction => "Bone Conduction",
        };
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
        format!("Custom {} {}", d_str, ff)
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
        }
    }

    /// Handle key events. Returns `Some(AcousticGearProfile)` upon completion.
    pub fn handle_key(&mut self, code: KeyCode) -> Option<AcousticGearProfile> {
        match code {
            KeyCode::Esc => {
                self.close();
                None
            }
            KeyCode::Char(c) if self.current_step == 6 => {
                if self.custom_name.len() < 36 {
                    self.custom_name.push(c);
                }
                None
            }
            KeyCode::Backspace if self.current_step == 6 => {
                self.custom_name.pop();
                None
            }
            KeyCode::Up => {
                if self.current_step < 6 {
                    self.selected_option = self.selected_option.saturating_sub(1);
                }
                None
            }
            KeyCode::Down => {
                if self.current_step < 6 {
                    let max_opts = self.options_for_step(self.current_step).len().saturating_sub(1);
                    if self.selected_option < max_opts {
                        self.selected_option += 1;
                    }
                }
                None
            }
            KeyCode::Char(' ') if self.current_step == 2 => {
                // Multi-select toggle for driver topology
                if self.selected_option < 6 {
                    self.drivers[self.selected_option] = !self.drivers[self.selected_option];
                }
                None
            }
            KeyCode::Enter => {
                // Commit choice and advance to next question
                match self.current_step {
                    0 => {
                        self.form_factor = match self.selected_option {
                            0 => GearFormFactor::OverEar,
                            1 => GearFormFactor::OnEar,
                            2 => GearFormFactor::InEar,
                            3 => GearFormFactor::Earbuds,
                            _ => GearFormFactor::BoneConduction,
                        };
                        self.current_step = 1;
                        self.selected_option = 0;
                        None
                    }
                    1 => {
                        self.enclosure = match self.selected_option {
                            0 => GearEnclosure::OpenBack,
                            1 => GearEnclosure::SemiOpen,
                            2 => GearEnclosure::ClosedBack,
                            _ => GearEnclosure::Anc,
                        };
                        self.current_step = 2;
                        self.selected_option = 0;
                        None
                    }
                    2 => {
                        // Ensure at least one driver is selected
                        if !self.drivers.iter().any(|&d| d) {
                            self.drivers[0] = true;
                        }
                        // Skip coupling question if not IEM
                        if self.form_factor == GearFormFactor::InEar {
                            self.current_step = 3;
                        } else {
                            self.coupling = GearCoupling::OpenAir;
                            self.current_step = 4;
                        }
                        self.selected_option = 0;
                        None
                    }
                    3 => {
                        self.coupling = match self.selected_option {
                            0 => GearCoupling::Silicone,
                            1 => GearCoupling::MemoryFoam,
                            _ => GearCoupling::CustomMolded,
                        };
                        self.current_step = 4;
                        self.selected_option = 0;
                        None
                    }
                    4 => {
                        self.tonal_balance = match self.selected_option {
                            0 => GearTonalBalance::AnalyticalBright,
                            1 => GearTonalBalance::DarkWarm,
                            2 => GearTonalBalance::BassHeavy,
                            3 => GearTonalBalance::VShaped,
                            _ => GearTonalBalance::NeutralStudio,
                        };
                        self.current_step = 5;
                        self.selected_option = 0;
                        None
                    }
                    5 => {
                        self.source_amp = match self.selected_option {
                            0 => GearSourceAmp::PortableDongle,
                            1 => GearSourceAmp::DesktopSolidState,
                            2 => GearSourceAmp::TubeAmp,
                            _ => GearSourceAmp::BluetoothWireless,
                        };
                        if self.custom_name.is_empty() || self.custom_name == "Universal Reference Gear" {
                            self.custom_name = self.default_name_for_config();
                        }
                        self.current_step = 6;
                        self.selected_option = 0;
                        None
                    }
                    6 => {
                        if self.custom_name.trim().is_empty() {
                            self.custom_name = self.default_name_for_config();
                        }
                        self.is_open = false;
                        Some(self.build_profile())
                    }
                    _ => None,
                }
            }
            _ => None,
        }
    }

    fn options_for_step(&self, step: usize) -> Vec<(&'static str, &'static str)> {
        match step {
            0 => vec![
                ("Over-Ear Headphones", "Circumaural earcups enclosing the outer ear."),
                ("On-Ear Headphones", "Supra-aural cushions resting directly on the ear cartilage."),
                ("In-Ear Monitors (IEM)", "Sealed acoustic canal coupling bypassing the pinna."),
                ("Earbuds / Open-Fit", "Rest in concha without deep acoustic ear-canal seal."),
                ("Bone Conduction", "Tactile transducers vibrating the temporal bone."),
            ],
            1 => vec![
                ("Open-Back Enclosure", "Acoustically transparent grilles, zero internal backwave pressure."),
                ("Semi-Open Enclosure", "Damped acoustic vents with partial pressure isolation."),
                ("Closed-Back Enclosure", "Sealed acoustic earcups, high passive isolation & bass pressure."),
                ("Active Noise Cancelling (ANC)", "Internal DSP microphones & sealed acoustic chamber."),
            ],
            2 => vec![
                ("Dynamic Driver (DD)", "Moving-coil diaphragm with natural acoustic mass & punch."),
                ("Planar Magnetic", "Orthodynamic membrane with ultra-low distortion & linear bass."),
                ("Balanced Armature (BA)", "Micro-reed transducer with lightning speed & micro-detail."),
                ("Electrostatic (EST)", "Virtually zero-mass film with holographic upper air."),
                ("Piezoelectric Tweeter", "Ceramic ultra-high frequency acoustic resonant element."),
                ("Bone Conduction Motor", "Low-frequency tactile skull driver."),
            ],
            3 => vec![
                ("Silicone Eartips", "Standard wide/narrow-bore tips with linear treble transfer."),
                ("Memory Foam Tips", "High acoustic isolation, absorbs 8-10 kHz high-frequency glare."),
                ("Custom Molded Acrylic", "Acoustic lock matching ear-canal anatomy perfectly."),
            ],
            4 => vec![
                ("Analytical / Bright / Sibilant", "Forward treble energy, prone to listening fatigue."),
                ("Dark / Warm / Relaxed", "Recessed treble and thick, rich lower midrange."),
                ("Bass-Heavy / Boomy", "Pronounced sub/mid-bass, risk of low-frequency masking."),
                ("V-Shaped Response", "Boosted sub-bass & highs, recessed midrange vocals."),
                ("Neutral / Studio Reference", "Flat target curve with linear acoustic balance."),
            ],
            5 => vec![
                ("Portable Dongle / Phone DAC", "Low-voltage mobile source with limited output current."),
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

        let titles = [
            "QUESTION 1/7: FORM FACTOR & EAR PLACEMENT",
            "QUESTION 2/7: ACOUSTIC ENCLOSURE TOPOLOGY",
            "QUESTION 3/7: DRIVER TRANSDUCER ARCHITECTURE",
            "QUESTION 4/7: EAR CANAL COUPLING & EARTIPS",
            "QUESTION 5/7: INNATE TONAL BALANCE OF GEAR",
            "QUESTION 6/7: AMPLIFICATION & SOURCE HARDWARE",
            "QUESTION 7/7: NAME & RENAME YOUR GEAR PROFILE",
        ];

        let block = Block::default()
            .title(format!(" ACOUSTIC GEAR PROFILING WIZARD | {} ", titles[self.current_step.min(6)]))
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

        let instruction = match self.current_step {
            2 => "Select all driver technologies present in your gear (Press [Space] to toggle, [Enter] to confirm):",
            6 => "Custom Gear Profile Naming (Type custom name, [Backspace] to edit, [Enter] to finish):",
            _ => "Select your listening hardware characteristics (Use [Up/Down] to select, [Enter] to confirm):",
        };
        let p_inst = Paragraph::new(instruction)
            .style(Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD));
        f.render_widget(p_inst, chunks[0]);

        if self.current_step == 6 {
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
                    Span::styled(" Acoustic Summary: ", Style::default().fg(theme.text_dim)),
                    Span::styled(self.default_name_for_config(), Style::default().fg(theme.secondary)),
                ]),
                Line::from(""),
                Line::from(Span::styled(
                    "This gear acoustic profile will automatically harmonize with all 20 Audiophile Mood & Mastering Presets.",
                    Style::default().fg(theme.text_dim),
                )),
            ]);
            f.render_widget(prompt, chunks[1]);
        } else {
            let options = self.options_for_step(self.current_step);
            let mut lines = Vec::new();

            for (i, (label, desc)) in options.iter().enumerate() {
                let is_sel = i == self.selected_option;
                let marker = if self.current_step == 2 {
                    if self.drivers[i] { "[X] " } else { "[ ] " }
                } else {
                    if is_sel { "(*) " } else { "( ) " }
                };

                let line_style = if is_sel {
                    Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(theme.text)
                };

                lines.push(Line::from(vec![
                    Span::styled(format!("  {} {:<28}", marker, label), line_style),
                    Span::styled(format!(" - {}", desc), Style::default().fg(theme.text_dim)),
                ]));
                lines.push(Line::from(""));
            }

            let p_opts = Paragraph::new(lines);
            f.render_widget(p_opts, chunks[1]);
        }

        let footer_text = if self.current_step == 6 {
            " [Type] Custom Name  [Backspace] Delete  [Enter] Save Profile & Calibrate  [Esc] Cancel"
        } else if self.current_step == 2 {
            " [Space] Toggle Driver  [Up/Down] Navigate  [Enter] Confirm & Next  [Esc] Cancel"
        } else {
            " [Up/Down] Navigate  [Enter] Confirm & Next  [Esc] Cancel"
        };
        let p_foot = Paragraph::new(footer_text)
            .alignment(Alignment::Center)
            .style(Style::default().fg(theme.accent));
        f.render_widget(p_foot, chunks[2]);
    }
}
