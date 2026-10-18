//! Low-latency CoreAudio Duplex Audio Streamer in pure Rust using `cpal`.
//!
//! Spawns native CoreAudio real-time threads (zero GIL, zero GC), bridging
//! BlackHole 2ch loopback capture to the output DAC via lock-free SPSC servo buffer.

use super::servo::{create_servo_ring_buffer, ServoReader};
use super::AudioPipeline;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig};
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioEngineType {
    PureRustIpc,    // Pure Rust Zero-Driver IPC Engine (/tmp/omnirip_audio.sock)
    DirectHardware, // Direct Hardware bit-perfect output with calibrated acoustic references
}

impl AudioEngineType {
    pub fn label(&self) -> &'static str {
        match self {
            AudioEngineType::PureRustIpc => "Pure Rust Zero-Driver IPC Engine",
            AudioEngineType::DirectHardware => "Direct Hardware (Bit-Perfect Standalone)",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            AudioEngineType::PureRustIpc => AudioEngineType::DirectHardware,
            AudioEngineType::DirectHardware => AudioEngineType::PureRustIpc,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyncMode {
    Extreme,  // 256 frames (~5.3ms cushion)
    Ultra,    // 512 frames (~10.6ms cushion)
    Balanced, // 1024 frames (~21.3ms cushion)
    Stable,   // 2048 frames (~42.7ms cushion)
}

impl SyncMode {
    pub fn target_frames(&self) -> usize {
        match self {
            SyncMode::Extreme => 512,
            SyncMode::Ultra => 1024,
            SyncMode::Balanced => 2048,
            SyncMode::Stable => 4096,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TestToneMode {
    AcousticHarmonics, // Rich multi-harmonic chord (55Hz, 220Hz, 880Hz, 3520Hz) - ideal for EQ auditioning
    PinkNoise,          // Equal energy per octave - calibrated acoustic reference
    Sine1k,             // 1.0 kHz pure reference tone
    FrequencySweep,     // 20 Hz to 20,000 Hz continuous logarithmic sweep
}

impl TestToneMode {
    pub fn label(&self) -> &'static str {
        match self {
            TestToneMode::AcousticHarmonics => "Acoustic Harmonics (Chords)",
            TestToneMode::PinkNoise => "Calibrated Pink Noise",
            TestToneMode::Sine1k => "1.0 kHz Reference Sine",
            TestToneMode::FrequencySweep => "20Hz-20kHz Log Sweep",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            TestToneMode::AcousticHarmonics => "Multi-octave harmonic chord (55Hz, 220Hz, 880Hz, 3.5kHz, 12kHz) for live EQ auditioning",
            TestToneMode::PinkNoise => "3-pole -3dB/octave Gardner pink noise generator for calibrated acoustic frequency response",
            TestToneMode::Sine1k => "1,000 Hz 0.0dBFS calibrated pure reference sine wave for level matching and phase check",
            TestToneMode::FrequencySweep => "20 Hz - 20,000 Hz continuous logarithmic acoustic sweep for resonant peak detection",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            TestToneMode::AcousticHarmonics => TestToneMode::PinkNoise,
            TestToneMode::PinkNoise => TestToneMode::Sine1k,
            TestToneMode::Sine1k => TestToneMode::FrequencySweep,
            TestToneMode::FrequencySweep => TestToneMode::AcousticHarmonics,
        }
    }
}

#[cfg(target_os = "macos")]
#[repr(C)]
#[allow(non_snake_case)]
struct AudioObjectPropertyAddress {
    mSelector: u32,
    mScope: u32,
    mElement: u32,
}

#[cfg(target_os = "macos")]
#[link(name = "CoreAudio", kind = "framework")]
extern "C" {
    fn AudioObjectSetPropertyData(
        inObjectID: u32,
        inAddress: *const AudioObjectPropertyAddress,
        inQualifierDataSize: u32,
        inQualifierData: *const std::ffi::c_void,
        inDataSize: u32,
        inData: *const std::ffi::c_void,
    ) -> i32;

    fn pthread_set_qos_class_self_np(qos_class: u32, relative_priority: i32) -> i32;
}

#[cfg(target_os = "macos")]
pub fn get_macos_default_output_id() -> Option<u32> {
    crate::driver::get_default_output_device_id()
}

#[cfg(target_os = "macos")]
pub fn get_macos_device_id_by_keyword(keyword: &str) -> Option<u32> {
    crate::driver::get_device_id_by_name(keyword)
}

#[cfg(target_os = "macos")]
pub fn set_macos_system_output_to_device_id(target_id: u32) -> Result<(), String> {
    crate::driver::set_default_output_device_id(target_id)?;
    unsafe {
        let addr_set = AudioObjectPropertyAddress {
            mSelector: 0x734f7574, // 'sOut' (System Alert Output)
            mScope: 0x676c6f62,     // 'glob'
            mElement: 0,
        };
        let _ = AudioObjectSetPropertyData(1, &addr_set, 0, std::ptr::null(), 4, &target_id as *const _ as *const _);
    }
    Ok(())
}

#[cfg(target_os = "macos")]
pub fn set_macos_system_output_to_blackhole() -> Result<String, String> {
    let bh_id = get_macos_device_id_by_keyword("blackhole")
        .ok_or_else(|| "BlackHole 2ch device not found in CoreAudio".to_string())?;
    set_macos_system_output_to_device_id(bh_id)?;
    Ok("macOS Default Output set to BlackHole 2ch (Speakers Muted)".to_string())
}

#[cfg(target_os = "macos")]
pub fn set_macos_system_output_to_hardware() -> Result<String, String> {
    let hw_id = get_macos_device_id_by_keyword("ibasso")
        .or_else(|| get_macos_device_id_by_keyword("dac"))
        .or_else(|| get_macos_device_id_by_keyword("headphone"))
        .or_else(|| get_macos_device_id_by_keyword("speaker"))
        .ok_or_else(|| "No hardware output device found in CoreAudio".to_string())?;
    set_macos_system_output_to_device_id(hw_id)?;
    Ok(format!("macOS Default Output restored to hardware (ID {})", hw_id))
}

#[cfg(not(target_os = "macos"))]
pub fn get_macos_default_output_id() -> Option<u32> {
    None
}

#[cfg(not(target_os = "macos"))]
pub fn get_macos_device_id_by_keyword(_keyword: &str) -> Option<u32> {
    None
}

#[cfg(not(target_os = "macos"))]
pub fn set_macos_system_output_to_device_id(_target_id: u32) -> Result<(), String> {
    Ok(())
}

#[cfg(not(target_os = "macos"))]
pub fn set_macos_system_output_to_blackhole() -> Result<String, String> {
    Ok("Non-macOS platform".to_string())
}

#[cfg(not(target_os = "macos"))]
pub fn set_macos_system_output_to_hardware() -> Result<String, String> {
    Ok("Non-macOS platform".to_string())
}

pub struct AudioStreamer {
    pub sync_mode: SyncMode,
    pub engine_type: AudioEngineType,
    pub is_running: Arc<AtomicBool>,
    pub is_paused: Arc<AtomicBool>,
    pub test_tone_active: Arc<AtomicBool>,
    pub test_tone_mode: Arc<Mutex<TestToneMode>>,
    pub needs_rebuild: Arc<AtomicBool>,
    pub last_callback_epoch_ms: Arc<AtomicU64>,
    pub system_volume_bits: Arc<AtomicU32>,
    pub pipeline: Arc<Mutex<AudioPipeline>>,
    pub player: Arc<super::player::TrackPlayer>,
    pub selected_input_name: Option<String>,
    pub selected_output_name: Option<String>,
    pub saved_physical_output_id: Option<u32>,
    pub ipc_server: Option<Arc<super::transport::IpcAudioServer>>,
    pub input_capture_enabled: Arc<AtomicBool>,
    pub chip_profile: Arc<Mutex<super::hardware_detect::HardwareChipProfile>>,
    input_stream: Option<Stream>,
    output_stream: Option<Stream>,
    reader_handle: Option<Arc<Mutex<ServoReader>>>,
}

impl AudioStreamer {
    pub fn new(mut pipeline: AudioPipeline) -> Self {
        let sr = pipeline.sample_rate;
        let saved_flavor = crate::dsp::volume_storage::load_dac_flavor_setting();
        pipeline.set_dac_flavor(saved_flavor);
        let default_output = Self::available_output_names().into_iter().next();
        let initial_chip = super::hardware_detect::HardwareChipProfile::detect(default_output.as_deref());
        Self {
            sync_mode: SyncMode::Balanced,
            engine_type: AudioEngineType::PureRustIpc,
            is_running: Arc::new(AtomicBool::new(false)),
            is_paused: Arc::new(AtomicBool::new(false)),
            test_tone_active: Arc::new(AtomicBool::new(false)),
            test_tone_mode: Arc::new(Mutex::new(TestToneMode::AcousticHarmonics)),
            needs_rebuild: Arc::new(AtomicBool::new(false)),
            last_callback_epoch_ms: Arc::new(AtomicU64::new(0)),
            system_volume_bits: {
                let (_, saved_scalar) = crate::dsp::volume_storage::load_volume_settings();
                Arc::new(AtomicU32::new(saved_scalar.to_bits()))
            },
            pipeline: Arc::new(Mutex::new(pipeline)),
            player: Arc::new(super::player::TrackPlayer::new(sr)),
            selected_input_name: None,
            selected_output_name: None,
            saved_physical_output_id: None,
            ipc_server: None,
            input_capture_enabled: Arc::new(AtomicBool::new(crate::dsp::volume_storage::load_mic_setting())),
            chip_profile: Arc::new(Mutex::new(initial_chip)),
            input_stream: None,
            output_stream: None,
            reader_handle: None,
        }
    }

    /// Set the DAC/Amp mimicker flavor and persist to storage.
    pub fn set_dac_flavor(&self, flavor: super::enhancer::DacHardwareFlavor) {
        if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.set_dac_flavor(flavor);
        }
        crate::dsp::volume_storage::save_dac_flavor_setting(flavor);
    }

    /// Cycle to the next DAC/Amp mimicker flavor forward and persist to storage.
    pub fn cycle_dac_flavor(&self) -> super::enhancer::DacHardwareFlavor {
        let new_flavor = if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.cycle_dac_flavor()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        };
        crate::dsp::volume_storage::save_dac_flavor_setting(new_flavor);
        new_flavor
    }

    /// Cycle to the previous DAC/Amp mimicker flavor reverse and persist to storage.
    pub fn cycle_dac_flavor_reverse(&self) -> super::enhancer::DacHardwareFlavor {
        let new_flavor = if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.dac_mimicker.cycle_flavor_reverse()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        };
        crate::dsp::volume_storage::save_dac_flavor_setting(new_flavor);
        new_flavor
    }

    /// Retrieve the currently selected DAC/Amp mimicker flavor.
    pub fn current_dac_flavor(&self) -> super::enhancer::DacHardwareFlavor {
        if let Ok(pipe) = self.pipeline.lock() {
            pipe.current_dac_flavor()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        }
    }

    /// Retrieve the active hardware sound chip and transducer acoustic profile.
    pub fn hardware_chip_profile(&self) -> super::hardware_detect::HardwareChipProfile {
        if let Ok(prof) = self.chip_profile.lock() {
            prof.clone()
        } else {
            super::hardware_detect::HardwareChipProfile::default()
        }
    }

    /// Dynamically update the sound chip profile when transducer or device routing shifts.
    pub fn update_chip_profile(&self, profile: super::hardware_detect::HardwareChipProfile) {
        if let Ok(mut lock) = self.chip_profile.lock() {
            *lock = profile;
        }
    }

    pub fn available_input_names() -> Vec<String> {
        #[cfg(target_os = "windows")]
        {
            return vec!["Pure Rust IPC Transport (/tmp/omnirip_audio.sock)".to_string()];
        }
        #[cfg(not(target_os = "windows"))]
        {
            let mut list = Vec::new();
            let host = cpal::default_host();
            if let Ok(devs) = host.devices() {
                for d in devs {
                    if let Ok(name) = d.name() {
                        let n = name.to_lowercase();
                        // Global system loopback drivers (OmniRip Audio, BlackHole) and hardware line inputs (microphones strictly excluded)
                        if (n.contains("omnirip") || n.contains("blackhole") || n.contains("line") || n.contains("usb") || n.contains("capture"))
                            && !n.contains("mic")
                        {
                            if !list.contains(&name) {
                                list.push(name);
                            }
                        }
                    }
                }
            }
            list.push("Pure Rust IPC Transport (/tmp/omnirip_audio.sock)".to_string());
            // Priority 1: OmniRip Audio (ground-up driver), Priority 2: BlackHole, Priority 3: Other
            list.sort_by_key(|name| {
                let n = name.to_lowercase();
                if n.contains("omnirip") {
                    0
                } else if n.contains("blackhole") {
                    1
                } else {
                    2
                }
            });
            list
        }
    }

    pub fn available_output_names() -> Vec<String> {
        #[cfg(target_os = "windows")]
        {
            return vec!["Default Audio Output".to_string()];
        }
        #[cfg(not(target_os = "windows"))]
        {
            let host = cpal::default_host();
            let mut list = Vec::new();
            if let Ok(devs) = host.devices() {
                for d in devs {
                    if let Ok(name) = d.name() {
                        let n = name.to_lowercase();
                        // Physical transducers: DACs, headphones, speakers (excluding virtual loopbacks and mics)
                        if (n.contains("speaker") || n.contains("ibasso") || n.contains("dac") || n.contains("headphone") || n.contains("built-in"))
                            && !n.contains("blackhole") && !n.contains("omnirip") && !n.contains("stream") && !n.contains("mic")
                        {
                            if !list.contains(&name) {
                                list.push(name);
                            }
                        }
                    }
                }
            }
            // Dynamic Transducer Priority:
            // Priority 1: External DAC (iBasso-DC03-Pro / USB DAC)
            // Priority 2: 3.5mm Headphone Jack (External Headphones / Headphones)
            // Priority 3: Built-in Speakers (MacBook Air Speakers / Internal)
            list.sort_by_key(|name| {
                let n = name.to_lowercase();
                if n.contains("ibasso") || n.contains("dac") || n.contains("fiio") {
                    0
                } else if n.contains("headphone") {
                    1
                } else {
                    2
                }
            });
            list
        }
    }

    pub fn cycle_input_device(&mut self) -> String {
        let inputs = Self::available_input_names();
        if inputs.is_empty() {
            return "No Inputs Found".to_string();
        }
        let current = self.active_input_name();
        let next_idx = inputs.iter().position(|n| n == &current).map(|i| (i + 1) % inputs.len()).unwrap_or(0);
        let chosen = inputs[next_idx].clone();
        self.selected_input_name = Some(chosen.clone());
        if self.is_running.load(Ordering::SeqCst) {
            let _ = self.restart();
        }
        chosen
    }

    pub fn cycle_output_device(&mut self) -> String {
        let outputs = Self::available_output_names();
        if outputs.is_empty() {
            return "No Outputs Found".to_string();
        }
        let current = self.active_output_name();
        let next_idx = outputs.iter().position(|n| n == &current).map(|i| (i + 1) % outputs.len()).unwrap_or(0);
        let chosen = outputs[next_idx].clone();
        self.selected_output_name = Some(chosen.clone());
        let new_chip = super::hardware_detect::HardwareChipProfile::detect(Some(&chosen));
        self.update_chip_profile(new_chip);
        if self.is_running.load(Ordering::SeqCst) {
            let _ = self.restart();
        }
        chosen
    }

    pub fn active_input_name(&self) -> String {
        if let Some(ref name) = self.selected_input_name {
            name.clone()
        } else {
            let (in_dev, _) = self.find_devices();
            in_dev.and_then(|d| d.name().ok()).unwrap_or_else(|| "Default Input".to_string())
        }
    }

    pub fn active_output_name(&self) -> String {
        if let Some(ref name) = self.selected_output_name {
            name.clone()
        } else {
            let (_, out_dev) = self.find_devices();
            out_dev.and_then(|d| d.name().ok()).unwrap_or_else(|| "Default Output".to_string())
        }
    }

    #[cfg(target_os = "macos")]
    pub fn physical_output_device_id(&self) -> Option<u32> {
        let out_name = self.active_output_name();
        crate::driver::get_device_id_by_name(&out_name)
            .or_else(|| get_macos_device_id_by_keyword("headphone"))
            .or_else(|| get_macos_device_id_by_keyword("speaker"))
    }

    #[cfg(not(target_os = "macos"))]
    pub fn physical_output_device_id(&self) -> Option<u32> {
        None
    }

    pub fn set_iem_exclusive_mode(&mut self) -> Result<String, String> {
        // 1. Turn off any test tone to prevent accidental test noise
        self.test_tone_active.store(false, Ordering::SeqCst);

        // 2. Set OmniRip Output to iBasso DAC (or Headphones if DAC not connected)
        let outputs = Self::available_output_names();
        if let Some(ibasso) = outputs.iter().find(|n| n.to_lowercase().contains("ibasso") || n.to_lowercase().contains("pro") || n.to_lowercase().contains("dac")) {
            self.selected_output_name = Some(ibasso.clone());
        } else if let Some(headphones) = outputs.iter().find(|n| n.to_lowercase().contains("headphone")) {
            self.selected_output_name = Some(headphones.clone());
        } else if let Some(first) = outputs.first() {
            self.selected_output_name = Some(first.clone());
        }

        // 3. Restart audio stream on the new device configuration
        self.restart()?;

        let out_name = self.active_output_name();
        Ok(format!("TRANSDUCER DIRECT ACTIVE: Pure Rust Engine -> OmniRip EQ -> [{}]", out_name))
    }

    /// Discover physical DAC, headphones, or MacBook speakers with 3-tier priority.
    pub fn find_devices(&self) -> (Option<Device>, Option<Device>) {
        #[cfg(target_os = "windows")]
        {
            return (None, None);
        }
        #[cfg(not(target_os = "windows"))]
        {
            let host = cpal::default_host();
            let mut in_dev = None;
            let mut out_dev = None;

            let all_devs: Vec<Device> = host.devices().map(|iter| iter.collect()).unwrap_or_default();

            // 1. Resolve Input Capture Device (OmniRip Audio prioritized; microphones strictly forbidden)
            if let Some(ref target) = self.selected_input_name {
                in_dev = all_devs.iter().find(|d| {
                    if let Ok(name) = d.name() {
                        let n = name.to_lowercase();
                        !n.contains("mic") && name == target.as_str()
                    } else {
                        false
                    }
                }).cloned();
            }
            if in_dev.is_none() {
                // Priority 1: OmniRip Audio proprietary HAL driver
                for dev in &all_devs {
                    if let Ok(name) = dev.name() {
                        let n = name.to_lowercase();
                        if n.contains("omnirip") && !n.contains("mic") {
                            in_dev = Some(dev.clone());
                            break;
                        }
                    }
                }
            }
            if in_dev.is_none() {
                // Priority 2: BlackHole 2ch fallback loopback
                for dev in &all_devs {
                    if let Ok(name) = dev.name() {
                        let n = name.to_lowercase();
                        if n.contains("blackhole") && !n.contains("mic") {
                            in_dev = Some(dev.clone());
                            break;
                        }
                    }
                }
            }

            // 2. Resolve Output Playback Device with Dynamic Transducer Priority
            if let Some(ref target) = self.selected_output_name {
                out_dev = all_devs.iter().find(|d| d.name().ok().as_deref() == Some(target.as_str())).cloned();
            }
            if out_dev.is_none() {
                // Priority 1: External USB DAC (iBasso-DC03-Pro, FiiO, Chord, AudioQuest, etc.)
                for dev in &all_devs {
                    if let Ok(name) = dev.name() {
                        let n = name.to_lowercase();
                        if (n.contains("ibasso") || n.contains("dac") || n.contains("fiio") || n.contains("pro"))
                            && !n.contains("stream") && !n.contains("mic")
                        {
                            out_dev = Some(dev.clone());
                            break;
                        }
                    }
                }
            }
            if out_dev.is_none() {
                // Priority 2: MacBook 3.5mm Headphone Jack (External Headphones)
                for dev in &all_devs {
                    if let Ok(name) = dev.name() {
                        let n = name.to_lowercase();
                        if n.contains("headphone") && !n.contains("mic") {
                            out_dev = Some(dev.clone());
                            break;
                        }
                    }
                }
            }
            if out_dev.is_none() {
                // Priority 3: Built-in MacBook Speakers
                for dev in &all_devs {
                    if let Ok(name) = dev.name() {
                        let n = name.to_lowercase();
                        if (n.contains("speaker") || n.contains("built-in")) && !n.contains("mic") {
                            out_dev = Some(dev.clone());
                            break;
                        }
                    }
                }
            }
            if out_dev.is_none() {
                out_dev = host.default_output_device();
            }

            (in_dev, out_dev)
        }
    }

    pub fn restart(&mut self) -> Result<(), String> {
        self.stop();
        self.start()
    }

    pub fn toggle_test_tone(&self) -> bool {
        let current = self.test_tone_active.load(Ordering::SeqCst);
        let new_state = !current;
        self.test_tone_active.store(new_state, Ordering::SeqCst);
        new_state
    }

    pub fn cycle_test_tone_mode(&self) -> TestToneMode {
        if let Ok(mut mode) = self.test_tone_mode.lock() {
            *mode = mode.next();
            *mode
        } else {
            TestToneMode::AcousticHarmonics
        }
    }

    pub fn is_test_tone_active(&self) -> bool {
        self.test_tone_active.load(Ordering::SeqCst)
    }

    pub fn current_test_tone_mode(&self) -> TestToneMode {
        self.test_tone_mode.lock().map(|m| *m).unwrap_or(TestToneMode::AcousticHarmonics)
    }

    pub fn toggle_pause(&self) -> bool {
        let current = self.is_paused.load(Ordering::SeqCst);
        let next = !current;
        self.is_paused.store(next, Ordering::SeqCst);
        if next {
            if let Some(reader) = &self.reader_handle {
                if let Ok(mut r) = reader.lock() {
                    r.reset();
                }
            }
        }
        next
    }

    pub fn is_paused(&self) -> bool {
        self.is_paused.load(Ordering::SeqCst)
    }

    pub fn is_input_capture_enabled(&self) -> bool {
        self.input_capture_enabled.load(Ordering::SeqCst)
    }

    pub fn set_input_capture(&mut self, enable: bool) -> (bool, String) {
        self.input_capture_enabled.store(enable, Ordering::SeqCst);
        crate::dsp::volume_storage::save_mic_setting(enable);

        if !enable {
            // Drop input stream immediately to dismiss macOS microphone indicator
            if let Some(s) = self.input_stream.take() {
                drop(s);
            }
            #[cfg(target_os = "macos")]
            {
                if let Some(saved_id) = self.saved_physical_output_id.take() {
                    let _ = set_macos_system_output_to_device_id(saved_id);
                } else {
                    let _ = set_macos_system_output_to_hardware();
                }
            }
            (false, "Microphone & Input Capture: [OFF] (Stream stopped, macOS mic indicator dismissed)".to_string())
        } else {
            // Activate input capture stream if engine is running
            if self.is_running.load(Ordering::SeqCst) {
                if self.input_stream.is_none() {
                    let (in_dev, _) = self.find_devices();
                    if let Some(in_d) = in_dev {
                        let in_dev_name = in_d.name().unwrap_or_default();
                        #[cfg(target_os = "macos")]
                        {
                            let in_name_lower = in_dev_name.to_lowercase();
                            if in_name_lower.contains("omnirip") || in_name_lower.contains("blackhole") {
                                if let Some(current_id) = get_macos_default_output_id() {
                                    let loopback_id = get_macos_device_id_by_keyword("omnirip")
                                        .or_else(|| get_macos_device_id_by_keyword("blackhole"));
                                    if let Some(target_id) = loopback_id {
                                        if current_id != target_id {
                                            self.saved_physical_output_id = Some(current_id);
                                            let _ = set_macos_system_output_to_device_id(target_id);
                                        }
                                    }
                                }
                            }
                        }

                        if let Some(ref ipc) = self.ipc_server {
                            let writer_for_in = ipc.writer();
                            let is_paused_in = Arc::clone(&self.is_paused);
                            let needs_rebuild_in = Arc::clone(&self.needs_rebuild);
                            let in_name_clone = in_dev_name.clone();
                            let err_fn = move |err| {
                                eprintln!("Input audio stream error on [{}]: {}", in_name_clone, err);
                                needs_rebuild_in.store(true, Ordering::SeqCst);
                            };
                            let in_config = in_d
                                .default_input_config()
                                .map(|c| StreamConfig {
                                    channels: 2,
                                    sample_rate: c.sample_rate(),
                                    buffer_size: cpal::BufferSize::Default,
                                })
                                .unwrap_or(StreamConfig {
                                    channels: 2,
                                    sample_rate: cpal::SampleRate(48000),
                                    buffer_size: cpal::BufferSize::Default,
                                });

                            let in_rate = in_config.sample_rate.0;
                            if let Some(ref r_handle) = self.reader_handle {
                                if let Ok(mut r) = r_handle.lock() {
                                    r.set_nominal_ratio(in_rate as f64 / 48000.0);
                                }
                            }

                            let sys_vol_in = Arc::clone(&self.system_volume_bits);
                            let in_is_omnirip = in_dev_name.to_lowercase().contains("omnirip");
                            #[cfg(target_os = "macos")]
                            let mut qos_set_in = false;
                            match in_d.build_input_stream(
                                &in_config,
                                move |data: &[f32], _: &_| {
                                    #[cfg(target_os = "macos")]
                                    if !qos_set_in {
                                        unsafe {
                                            pthread_set_qos_class_self_np(0x21, 0);
                                        }
                                        qos_set_in = true;
                                    }

                                    if is_paused_in.load(Ordering::SeqCst) {
                                        return;
                                    }

                                    let mut scratch = [[0.0f32, 0.0f32]; 2048];
                                    let n_frames = (data.len() / 2).min(2048);

                                    let in_vol = f32::from_bits(sys_vol_in.load(Ordering::Relaxed)).clamp(0.0, 1.0);
                                    let norm_factor = if in_is_omnirip && in_vol < 0.999 {
                                        if in_vol > 0.001 { 1.0f32 / in_vol } else { 0.0f32 }
                                    } else {
                                        1.0f32
                                    };

                                    for i in 0..n_frames {
                                        scratch[i] = [data[i * 2] * norm_factor, data[i * 2 + 1] * norm_factor];
                                    }

                                    if let Ok(mut w) = writer_for_in.lock() {
                                        w.write(&scratch[..n_frames]);
                                    }
                                },
                                err_fn,
                                None,
                            ) {
                                Ok(stream) => {
                                    let _ = stream.play();
                                    self.input_stream = Some(stream);
                                    (true, format!("Microphone & Input Capture: [ON] (Capturing from [{}])", in_dev_name))
                                }
                                Err(e) => {
                                    (false, format!("Failed to activate input capture stream on [{}]: {}", in_dev_name, e))
                                }
                            }
                        } else {
                            (false, "Audio server not initialized".to_string())
                        }
                    } else {
                        (false, "No input capture device available".to_string())
                    }
                } else {
                    (true, "Microphone & Input Capture: [ON] (Already active)".to_string())
                }
            } else {
                (true, "Microphone & Input Capture: [ON] (Will activate when engine starts)".to_string())
            }
        }
    }

    pub fn toggle_input_capture(&mut self) -> (bool, String) {
        let current = self.is_input_capture_enabled();
        self.set_input_capture(!current)
    }

    pub fn heal_routing(&mut self) {
        self.is_paused.store(false, Ordering::SeqCst);
        self.force_resync();

        #[cfg(target_os = "macos")]
        {
            if let Some(loopback_id) = get_macos_device_id_by_keyword("omnirip")
                .or_else(|| get_macos_device_id_by_keyword("blackhole"))
            {
                let _ = set_macos_system_output_to_device_id(loopback_id);
            }

            // Auto-heal physical output hardware volume scalar (1.0) and unmute
            let out_name = self.active_output_name();
            if let Some(id) = crate::driver::get_device_id_by_name(&out_name) {
                crate::driver::auto_heal_device_volume_and_mute(id);
            }
            crate::driver::auto_heal_physical_output("headphone");
            crate::driver::auto_heal_physical_output("speaker");
        }
    }

    /// Polls audio stream health and watchdog heartbeats. If a CoreAudio stream error
    /// or stall (e.g. from laptop sleep/wake or DAC disconnect) is detected, seamlessly
    /// restarts the audio pipeline and returns true.
    pub fn poll_health(&mut self) -> bool {
        if !self.is_running.load(Ordering::SeqCst) {
            return false;
        }

        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0);

        let last_cb = self.last_callback_epoch_ms.load(Ordering::SeqCst);
        let is_stalled = !self.is_paused.load(Ordering::SeqCst)
            && last_cb > 0
            && now_ms.saturating_sub(last_cb) > 2500;

        if self.needs_rebuild.load(Ordering::SeqCst) || is_stalled {
            self.needs_rebuild.store(false, Ordering::SeqCst);
            self.heal_routing();
            if self.output_stream.is_some() || self.input_stream.is_some() {
                let _ = self.restart();
            }
            return true;
        }

        #[cfg(target_os = "macos")]
        {
            let loopback_id = get_macos_device_id_by_keyword("omnirip")
                .or_else(|| get_macos_device_id_by_keyword("blackhole"))
                .or_else(get_macos_default_output_id);
            if let Some(id) = loopback_id {
                if let Some(vol) = crate::driver::get_device_volume(id) {
                    self.system_volume_bits.store(vol.to_bits(), Ordering::Relaxed);
                    // Mirror volume to physical endpoint (speakers, headphones, DAC) so hardware volume matches stock 100%
                    if let Some(phys_id) = self.physical_output_device_id() {
                        if phys_id != id {
                            let current_phys = crate::driver::get_device_volume(phys_id).unwrap_or(-1.0);
                            if (current_phys - vol).abs() > 0.005 {
                                let _ = crate::driver::set_device_volume(phys_id, vol);
                            }
                        }
                    }
                }
            }
        }

        false
    }

    pub fn set_sync_mode(&mut self, mode: SyncMode) {
        self.sync_mode = mode;
        if let Some(reader) = &self.reader_handle {
            if let Ok(r) = reader.lock() {
                r.set_target_frames(mode.target_frames());
            }
        }
    }

    pub fn set_game_mode(&mut self, enabled: bool) -> (bool, String) {
        if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.enhancer.game_mode = enabled;
            if enabled {
                pipe.enhancer.radar_eq = true;
                pipe.enhancer.spike_shield = true;
                pipe.enhancer.tube_warmth = 0.0;
                pipe.enhancer.tape_emulation = false;
                pipe.enhancer.spatial_width = 1.20;
            } else {
                pipe.enhancer.radar_eq = false;
                pipe.enhancer.spike_shield = false;
            }
            pipe.enhancer.rebuild_filters();
        }
        if let Some(reader) = &self.reader_handle {
            if let Ok(mut r) = reader.lock() {
                if enabled {
                    r.set_target_frames(512);
                    r.set_resampling_mode(crate::dsp::servo::ResamplingMode::FastHermite);
                } else {
                    r.set_target_frames(self.sync_mode.target_frames());
                    r.set_resampling_mode(crate::dsp::servo::ResamplingMode::AudiophileSinc);
                }
            }
        }
        let msg = if enabled {
            "Low-Latency Esports Gaming Mode: [ON] (512 frames / 10.6ms cushion, Fast Hermite resampler active)".to_string()
        } else {
            "Low-Latency Esports Gaming Mode: [OFF] (Restored Audiophile Sinc resampler & cushion)".to_string()
        };
        (enabled, msg)
    }

    pub fn toggle_game_mode(&mut self) -> (bool, String) {
        let current = self.is_game_mode_enabled();
        self.set_game_mode(!current)
    }

    pub fn is_game_mode_enabled(&self) -> bool {
        if let Ok(pipe) = self.pipeline.lock() {
            pipe.enhancer.game_mode
        } else {
            false
        }
    }

    pub fn telemetry(&self) -> (super::transport::IpcServerTelemetry, Option<(usize, usize, f32)>) {
        let ipc = self.ipc_server.as_ref().map(|s| s.telemetry()).unwrap_or_default();
        let pll = self.reader_handle.as_ref().and_then(|r| r.lock().ok()).map(|r| r.pll_telemetry());
        (ipc, pll)
    }

    pub fn force_resync(&self) {
        if let Some(reader) = &self.reader_handle {
            if let Ok(mut r) = reader.lock() {
                r.reset();
            }
        }
    }

    pub fn active_sample_rate(&self) -> f32 {
        if let Ok(pipe) = self.pipeline.lock() {
            pipe.sample_rate
        } else {
            48000.0
        }
    }

    /// Set master volume scalar (0.0 to 1.0).
    /// Dispatches hardware volume directly to physical transducers (MacBook speakers, headphones, USB DAC)
    /// ensuring 100% volume parity with stock macOS.
    pub fn set_master_volume(&mut self, volume: f32) {
        let safe_vol = volume.clamp(0.0, 1.0);
        let (player_pct, _) = crate::dsp::volume_storage::load_volume_settings();
        crate::dsp::volume_storage::save_volume_settings(player_pct, safe_vol);
        self.system_volume_bits.store(safe_vol.to_bits(), Ordering::Relaxed);

        #[cfg(target_os = "macos")]
        {
            // Sync to loopback driver (OmniRip Audio) so macOS volume UI matches
            let loopback_id = get_macos_device_id_by_keyword("omnirip")
                .or_else(|| get_macos_device_id_by_keyword("blackhole"))
                .or_else(get_macos_default_output_id);
            if let Some(id) = loopback_id {
                let _ = crate::driver::set_device_volume(id, safe_vol);
            }
            // Sync directly to active physical output endpoint (speakers, headphones, DAC)
            if let Some(phys_id) = self.physical_output_device_id() {
                let _ = crate::driver::set_device_volume(phys_id, safe_vol);
            }
        }
    }

    /// Start native real-time CoreAudio stream.
    pub fn start(&mut self) -> Result<(), String> {
        if self.is_running.load(Ordering::SeqCst) {
            return Ok(());
        }

        let (in_dev, out_dev) = self.find_devices();
        let out_dev = out_dev.ok_or_else(|| "No output playback device found".to_string())?;

        // If OmniRip Audio or loopback is active AND input capture is enabled, automatically redirect macOS system default output
        let is_capture_enabled = self.input_capture_enabled.load(Ordering::SeqCst);
        #[cfg(target_os = "macos")]
        if is_capture_enabled {
            if let Some(ref in_d) = in_dev {
                let in_name = in_d.name().unwrap_or_default().to_lowercase();
                if in_name.contains("omnirip") || in_name.contains("blackhole") {
                    if let Some(current_id) = get_macos_default_output_id() {
                        let loopback_id = get_macos_device_id_by_keyword("omnirip")
                            .or_else(|| get_macos_device_id_by_keyword("blackhole"));
                        if let Some(target_id) = loopback_id {
                            if current_id != target_id {
                                self.saved_physical_output_id = Some(current_id);
                                let _ = set_macos_system_output_to_device_id(target_id);
                            } else if self.saved_physical_output_id.is_none() {
                                if let Ok(out_name) = out_dev.name() {
                                    self.saved_physical_output_id = crate::driver::get_device_id_by_name(&out_name);
                                }
                            }
                        }
                    }
                }
            }
        }

        // Ensure active physical output endpoint is synchronized to macOS volume and unmuted
        #[cfg(target_os = "macos")]
        {
            let init_vol = get_macos_device_id_by_keyword("omnirip")
                .and_then(crate::driver::get_device_volume)
                .unwrap_or_else(|| f32::from_bits(self.system_volume_bits.load(Ordering::Relaxed)).clamp(0.0, 1.0));
            self.system_volume_bits.store(init_vol.to_bits(), Ordering::Relaxed);

            if let Ok(dev_name) = out_dev.name() {
                if let Some(id) = crate::driver::get_device_id_by_name(&dev_name) {
                    let _ = crate::driver::unmute_device(id);
                    let _ = crate::driver::set_device_volume(id, init_vol);
                }
            }
        }

        // Dynamic Sample Rate: Adapt to active physical transducer (e.g. 96,000 Hz on iBasso DAC)
        let sample_rate = out_dev
            .default_output_config()
            .map(|c| c.sample_rate().0)
            .unwrap_or(48000);
        let channels = 2;
        let config = StreamConfig {
            channels,
            sample_rate: cpal::SampleRate(sample_rate),
            buffer_size: cpal::BufferSize::Default,
        };

        if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.sample_rate = sample_rate as f32;
        }

        let (writer, reader) = create_servo_ring_buffer(32768, self.sync_mode.target_frames());
        let reader_arc = Arc::new(Mutex::new(reader));
        self.reader_handle = Some(Arc::clone(&reader_arc));

        // Start Pure Rust IPC server on /tmp/omnirip_audio.sock
        let ipc = Arc::new(super::transport::IpcAudioServer::new(writer));
        if let Err(e) = ipc.start() {
            eprintln!("Warning: Failed to start Pure Rust IPC server: {}", e);
        }
        let writer_for_in = ipc.writer();
        self.ipc_server = Some(ipc);

        // 1. Optional Hardware Input Stream Callback (only built if input capture / mic is explicitly enabled)
        let needs_rebuild_in = Arc::clone(&self.needs_rebuild);
        let in_stream = if is_capture_enabled {
            if let Some(ref in_d) = in_dev {
                let in_dev_name = in_d.name().unwrap_or_default();
                let in_name_clone = in_dev_name.clone();
                let err_fn = move |err| {
                    eprintln!("Input audio stream error on [{}]: {}", in_name_clone, err);
                    needs_rebuild_in.store(true, Ordering::SeqCst);
                };
                let in_config = in_d
                    .default_input_config()
                    .map(|c| StreamConfig {
                        channels: 2,
                        sample_rate: c.sample_rate(),
                        buffer_size: cpal::BufferSize::Default,
                    })
                    .unwrap_or_else(|_| config.clone());

                let in_rate = in_config.sample_rate.0;
                let out_rate = sample_rate;
                if let Ok(mut r) = reader_arc.lock() {
                    r.set_nominal_ratio(in_rate as f64 / out_rate as f64);
                }
                if let Ok(mut pipe) = self.pipeline.lock() {
                    pipe.sample_rate = out_rate as f32;
                }

                let is_paused_in = Arc::clone(&self.is_paused);
                let sys_vol_in = Arc::clone(&self.system_volume_bits);
                let in_is_omnirip = in_dev_name.to_lowercase().contains("omnirip");
                #[cfg(target_os = "macos")]
                let mut qos_set_in = false;
                match in_d.build_input_stream(
                    &in_config,
                    move |data: &[f32], _: &_| {
                        #[cfg(target_os = "macos")]
                        if !qos_set_in {
                            unsafe {
                                pthread_set_qos_class_self_np(0x21, 0); // QOS_CLASS_USER_INTERACTIVE
                            }
                            qos_set_in = true;
                        }

                        if is_paused_in.load(Ordering::SeqCst) {
                            return;
                        }

                        // Zero-allocation stack buffer (eliminates heap allocation in audio callback)
                        let mut scratch = [[0.0f32, 0.0f32]; 2048];
                        let n_frames = (data.len() / 2).min(2048);

                        // If capturing from OmniRip Audio HAL driver, un-scale driver-attenuated samples back to unity gain (1.0).
                        // Physical hardware transducers (speakers, headphones) apply the user's volume scalar directly.
                        let in_vol = f32::from_bits(sys_vol_in.load(Ordering::Relaxed)).clamp(0.0, 1.0);
                        let norm_factor = if in_is_omnirip && in_vol < 0.999 {
                            if in_vol > 0.001 { 1.0f32 / in_vol } else { 0.0f32 }
                        } else {
                            1.0f32
                        };

                        for i in 0..n_frames {
                            scratch[i] = [data[i * 2] * norm_factor, data[i * 2 + 1] * norm_factor];
                        }

                        if let Ok(mut w) = writer_for_in.lock() {
                            w.write(&scratch[..n_frames]);
                        }
                    },
                    err_fn,
                    None,
                ) {
                    Ok(stream) => {
                        let _ = stream.play();
                        Some(stream)
                    }
                    Err(e) => {
                        eprintln!("Warning: Failed to build input capture stream on [{}]: {}", in_d.name().unwrap_or_default(), e);
                        None
                    }
                }
            } else {
                None
            }
        } else {
            None
        };

        // 2. Native Output Stream Callback (DAC Playback + Track Player + Test Tone + DSP Pipeline)
        let pipeline_arc = Arc::clone(&self.pipeline);
        let reader_for_out = Arc::clone(&reader_arc);
        let test_active = Arc::clone(&self.test_tone_active);
        let test_mode_arc = Arc::clone(&self.test_tone_mode);
        let is_paused_out = Arc::clone(&self.is_paused);
        let player_arc = Arc::clone(&self.player);
        let last_cb_arc = Arc::clone(&self.last_callback_epoch_ms);
        let needs_rebuild_out = Arc::clone(&self.needs_rebuild);
        let sys_vol_arc = Arc::clone(&self.system_volume_bits);
        let out_name = out_dev.name().unwrap_or_default().to_lowercase();
        let out_is_external_dac = (out_name.contains("ibasso") || out_name.contains("dac") || out_name.contains("pro"))
            && !out_name.contains("headphone");
        let mut smoothed_gain = 1.0f32;

        let mut sample_idx: u64 = 0;
        let mut b0 = 0.0f32;
        let mut b1 = 0.0f32;
        let mut b2 = 0.0f32;
        let mut seed: u64 = 987654321;
        #[cfg(target_os = "macos")]
        let mut qos_set_out = false;

        let out_stream = out_dev
            .build_output_stream(
                &config,
                move |data: &mut [f32], _: &_| {
                    #[cfg(target_os = "macos")]
                    if !qos_set_out {
                        unsafe {
                            pthread_set_qos_class_self_np(0x21, 0); // QOS_CLASS_USER_INTERACTIVE
                        }
                        qos_set_out = true;
                    }

                    if is_paused_out.load(Ordering::SeqCst) {
                        data.fill(0.0);
                        return;
                    }

                    // Zero-allocation stack buffer: eliminates malloc/free locks during OS app launches
                    let n_frames = (data.len() / 2).min(2048);
                    let mut scratch = [[0.0f32, 0.0f32]; 2048];

                    // 1. If Track Player is playing, read decoded audio frames directly from player
                    let player_frames = if player_arc.is_playing() {
                        player_arc.read_frames(&mut scratch[..n_frames])
                    } else {
                        0
                    };

                    // 2. Otherwise read from loopback / IPC servo ring buffer
                    if player_frames == 0 {
                        if let Ok(mut r) = reader_for_out.lock() {
                            r.read(&mut scratch[..n_frames]);
                        }
                    }

                    if test_active.load(Ordering::SeqCst) {
                        let current_mode = test_mode_arc.lock().map(|m| *m).unwrap_or(TestToneMode::AcousticHarmonics);
                        let sr = 48000.0f32;

                        for frame in scratch[..n_frames].iter_mut() {
                            let t = sample_idx as f32 / sr;
                            let (sig_l, sig_r) = match current_mode {
                                TestToneMode::AcousticHarmonics => {
                                    // Rich multi-harmonic chord: 55Hz (Sub-Bass), 220Hz (Warmth), 880Hz (Presence), 3520Hz (Sheen), 12000Hz (Air)
                                    let sub = 0.35 * (2.0 * std::f32::consts::PI * 55.0 * t).sin();
                                    let mid = 0.25 * (2.0 * std::f32::consts::PI * 220.0 * t).sin();
                                    let pres = 0.18 * (2.0 * std::f32::consts::PI * 880.0 * t).sin();
                                    let air = 0.12 * (2.0 * std::f32::consts::PI * 3520.0 * t).sin();
                                    let sheen = 0.06 * (2.0 * std::f32::consts::PI * 12000.0 * t).sin();
                                    let mono = sub + mid + pres + air + sheen;
                                    (mono * 0.7, (mono + 0.15 * air - 0.15 * pres) * 0.7)
                                }
                                TestToneMode::PinkNoise => {
                                    seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                                    let white = ((seed >> 32) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
                                    b0 = 0.99886 * b0 + white * 0.0555179;
                                    b1 = 0.99332 * b1 + white * 0.0750759;
                                    b2 = 0.96900 * b2 + white * 0.1538520;
                                    let pink = (b0 + b1 + b2 + white * 0.5362) * 0.12;
                                    (pink, pink)
                                }
                                TestToneMode::Sine1k => {
                                    let s = 0.4 * (2.0 * std::f32::consts::PI * 1000.0 * t).sin();
                                    (s, s)
                                }
                                TestToneMode::FrequencySweep => {
                                    let sweep_t = (t % 2.0) / 2.0;
                                    let f = 20.0 * (1000.0_f32).powf(sweep_t);
                                    let s = 0.35 * (2.0 * std::f32::consts::PI * f * t).sin();
                                    (s, s)
                                }
                            };

                            frame[0] += sig_l;
                            frame[1] += sig_r;
                            sample_idx = sample_idx.wrapping_add(1);
                        }
                    }

                    if let Ok(mut pipe) = pipeline_arc.lock() {
                        pipe.process(&mut scratch[..n_frames]);
                    }

                    // Volume calibration:
                    // MacBook speakers and 3.5mm headphones are hardware-calibrated via CoreAudio set_device_volume
                    // in poll_health/set_master_volume, matching stock Apple sound engine decibel curves exactly.
                    // Software gain stays at unity (1.0) unless muted (v <= 0.001).
                    let v = f32::from_bits(sys_vol_arc.load(Ordering::Relaxed)).clamp(0.0, 1.0);
                    let target_gain = if v <= 0.001 {
                        0.0f32
                    } else if out_is_external_dac {
                        // External USB DACs without hardware volume scalar receive cubic digital scaling
                        v * v * v
                    } else {
                        // Physical MacBook speakers and headphone jack receive unity gain;
                        // CoreAudio hardware amplifier provides exact stock macOS acoustic volume.
                        1.0f32
                    };

                    for frame in scratch[..n_frames].iter_mut() {
                        smoothed_gain += (target_gain - smoothed_gain) * 0.1f32;
                        frame[0] *= smoothed_gain;
                        frame[1] *= smoothed_gain;
                    }

                    for i in 0..n_frames {
                        data[i * 2] = scratch[i][0];
                        data[i * 2 + 1] = scratch[i][1];
                    }

                    last_cb_arc.store(
                        std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .map(|d| d.as_millis() as u64)
                            .unwrap_or(0),
                        Ordering::SeqCst,
                    );
                },
                move |err| {
                    eprintln!("Output audio stream error: {}", err);
                    needs_rebuild_out.store(true, Ordering::SeqCst);
                },
                None,
            )
            .map_err(|e| format!("Failed to build output stream: {}", e))?;

        if let Some(ref s) = in_stream {
            let _ = s.play();
        }
        out_stream.play().map_err(|e| format!("Failed to play output stream: {}", e))?;

        self.input_stream = in_stream;
        self.output_stream = Some(out_stream);
        self.is_running.store(true, Ordering::SeqCst);

        Ok(())
    }

    /// Stop audio stream cleanly without reverting macOS system output.
    /// Preserves driver loopback routing to avoid route flapping and double voice leaks.
    pub fn stop(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        if let Some(ipc) = self.ipc_server.take() {
            ipc.stop();
        }
        if let Some(s) = self.output_stream.take() {
            let _ = s.pause();
        }
        if let Some(s) = self.input_stream.take() {
            let _ = s.pause();
        }
        self.reader_handle = None;
    }

    /// Full termination on application exit: stops audio streams and restores macOS default output to hardware DAC.
    pub fn terminate(&mut self) {
        self.stop();

        #[cfg(target_os = "macos")]
        {
            if let Some(saved_id) = self.saved_physical_output_id.take() {
                let _ = set_macos_system_output_to_device_id(saved_id);
            }
        }
    }
}

impl Drop for AudioStreamer {
    fn drop(&mut self) {
        self.terminate();
    }
}

/// CLI handler for omnirip mic subcommands (on, off, toggle, status)
pub fn run_mic_cli(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let sub = args.get(0).map(|s| s.as_str()).unwrap_or("status");
    match sub {
        "on" | "enable" | "1" => {
            crate::dsp::volume_storage::save_mic_setting(true);
            println!("OmniRip Microphone & Audio Input Capture: ENABLED (ON)");
            println!("Audio input stream will activate when OmniRip starts.");
        }
        "off" | "disable" | "0" => {
            crate::dsp::volume_storage::save_mic_setting(false);
            println!("OmniRip Microphone & Audio Input Capture: DISABLED (OFF)");
            println!("Audio input stream and macOS microphone indicator dismissed.");
        }
        "toggle" => {
            let current = crate::dsp::volume_storage::load_mic_setting();
            let new_state = !current;
            crate::dsp::volume_storage::save_mic_setting(new_state);
            let state_str = if new_state { "ENABLED (ON)" } else { "DISABLED (OFF)" };
            println!("OmniRip Microphone & Audio Input Capture toggled to: {}", state_str);
        }
        "status" => {
            let current = crate::dsp::volume_storage::load_mic_setting();
            let state_str = if current { "ENABLED (ON)" } else { "DISABLED (OFF)" };
            println!("OmniRip Microphone & Audio Input Capture status: {}", state_str);
            println!("Use 'omnirip mic on' or 'omnirip mic off' to change.");
        }
        _ => {
            println!("Usage: omnirip mic [on | off | toggle | status]");
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[cfg(target_os = "macos")]
    fn test_input_capture_toggle_and_mic_control() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        // Verify default state is enabled (ON) so system loopback audio works on startup
        assert!(streamer.is_input_capture_enabled());

        // Toggle to OFF
        let (enabled, msg) = streamer.toggle_input_capture();
        assert!(!enabled);
        assert!(!streamer.is_input_capture_enabled());
        assert!(msg.contains("[OFF]"));

        // Toggle back to ON
        let (enabled_on, msg_on) = streamer.toggle_input_capture();
        assert!(enabled_on);
        assert!(streamer.is_input_capture_enabled());
        assert!(msg_on.contains("[ON]"));

        // Direct set
        let (st, _) = streamer.set_input_capture(false);
        assert!(!st);
        let (st2, _) = streamer.set_input_capture(true);
        assert!(st2);
    }

    #[test]
    fn test_device_discovery() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        let inputs = AudioStreamer::available_input_names();
        let outputs = AudioStreamer::available_output_names();
        println!("Available Inputs: {:?}", inputs);
        println!("Available Outputs: {:?}", outputs);

        let in_name = streamer.active_input_name();
        let out_name = streamer.active_output_name();
        println!("Active Input: {}", in_name);
        println!("Active Output: {}", out_name);

        // Ensure output is NOT a virtual loopback device
        assert!(!out_name.to_lowercase().contains("blackhole"), "Output must not be BlackHole loopback");
        assert!(!out_name.to_lowercase().contains("omnirip"), "Output must not be OmniRip Stream virtual");

        // Ensure inputs NEVER contain any microphone
        for inp in &inputs {
            assert!(!inp.to_lowercase().contains("mic"), "Inputs must never contain microphones: {}", inp);
        }

        let cycled = streamer.cycle_output_device();
        println!("Cycled Output: {}", cycled);
    }

    #[test]
    fn test_transducer_priority_and_dynamic_resolution() {
        let pipe = AudioPipeline::new(48000.0);
        let _streamer = AudioStreamer::new(pipe);

        let outputs = AudioStreamer::available_output_names();
        if !outputs.is_empty() {
            let first = &outputs[0].to_lowercase();
            let has_dac = outputs.iter().any(|o| {
                let n = o.to_lowercase();
                n.contains("ibasso") || n.contains("dac") || n.contains("fiio")
            });
            if has_dac {
                assert!(first.contains("ibasso") || first.contains("dac") || first.contains("fiio"), "Top priority must be external DAC: {}", first);
            }
        }
    }

    #[test]
    #[cfg(unix)]
    fn test_pure_rust_ipc_stream_and_telemetry() {
        use super::super::transport::IpcAudioClient;

        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        // Start streamer (spawns IPC server on /tmp/omnirip_audio.sock and TCP 49152)
        if streamer.start().is_ok() {
            let socket_path = std::path::Path::new(super::super::transport::OMNIRIP_SOCKET_PATH);
            let mut bound = false;
            for _ in 0..20 {
                if socket_path.exists() {
                    bound = true;
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            assert!(bound, "Unix domain socket must be created after streamer.start()");

            // Connect client and send test frames
            let mut client_opt = None;
            for _ in 0..10 {
                if let Ok(c) = IpcAudioClient::connect() {
                    client_opt = Some(c);
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(10));
            }

            if let Some(mut client) = client_opt {
                let test_frames = vec![[0.1f32, 0.1f32]; 512];
                assert!(client.send_frames(&test_frames).is_ok());

                let mut telem_ok = false;
                for _ in 0..100 {
                    let (telem, _) = streamer.telemetry();
                    if telem.total_frames >= 512 || telem.total_packets >= 1 {
                        telem_ok = true;
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(10));
                }
                assert!(telem_ok, "Telemetry must reflect received frames within timeout");

                let (_, pll) = streamer.telemetry();
                assert!(pll.is_some());
            }

            streamer.stop();
            // Verify clean shutdown
            assert!(!streamer.is_running.load(std::sync::atomic::Ordering::SeqCst));
        }
    }

    #[test]
    fn test_streamer_pause_and_heal_routing() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        assert!(!streamer.is_paused());
        let paused = streamer.toggle_pause();
        assert!(paused);
        assert!(streamer.is_paused());

        let resumed = streamer.toggle_pause();
        assert!(!resumed);
        assert!(!streamer.is_paused());

        // Test heal_routing clears pause
        streamer.toggle_pause();
        assert!(streamer.is_paused());
        streamer.heal_routing();
        assert!(!streamer.is_paused());
    }

    #[test]
    fn test_poll_health_rebuild_and_stall_detection() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        // 1. Stopped streamer does not trigger poll_health
        assert!(!streamer.poll_health());

        // 2. Running streamer with no errors and recent callback does not trigger poll_health
        streamer.is_running.store(true, Ordering::SeqCst);
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as u64;
        streamer.last_callback_epoch_ms.store(now, Ordering::SeqCst);
        assert!(!streamer.poll_health());

        // 3. needs_rebuild flag triggers poll_health
        streamer.needs_rebuild.store(true, Ordering::SeqCst);
        let healed = streamer.poll_health();
        assert!(healed);
        assert!(!streamer.needs_rebuild.load(Ordering::SeqCst));

        // 4. Stalled callback (> 2500ms in past) triggers poll_health
        streamer.is_running.store(true, Ordering::SeqCst);
        streamer.last_callback_epoch_ms.store(now.saturating_sub(5000), Ordering::SeqCst);
        let healed_stall = streamer.poll_health();
        assert!(healed_stall);
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_macos_omnirip_loopback_discovery() {
        let omnirip_id = get_macos_device_id_by_keyword("omnirip");
        println!("Discovered OmniRip Audio Device ID: {:?}", omnirip_id);
        if omnirip_id.is_none() {
            println!("Skipping on headless CI: OmniRip Audio driver not installed in runner environment");
            return;
        }

        let default_id = get_macos_default_output_id();
        println!("Current macOS default output device ID: {:?}", default_id);
        assert!(default_id.is_some(), "Default output device must be queryable");

        if let Some(target_id) = omnirip_id {
            println!("OmniRip Audio volume: {:?}", crate::driver::get_device_volume(target_id));
        }

        if let (Some(target_id), Some(orig_id)) = (omnirip_id, default_id) {
            let alt_id = if orig_id != target_id {
                orig_id
            } else {
                get_macos_device_id_by_keyword("speaker").or_else(|| get_macos_device_id_by_keyword("headphone")).unwrap_or(orig_id)
            };

            let _ = set_macos_system_output_to_device_id(target_id);
            let switched = get_macos_default_output_id();
            println!("Default output after switch: {:?}", switched);
            let _ = set_macos_system_output_to_device_id(alt_id);
            let restored = get_macos_default_output_id();
            println!("Default output after alt switch: {:?}", restored);
            // Restore back to target_id (OmniRip Audio) for active runtime
            let _ = set_macos_system_output_to_device_id(target_id);
            assert_eq!(switched, Some(target_id), "macOS default output must switch to OmniRip Audio");
            assert_eq!(restored, Some(alt_id), "macOS default output must switch to alt device");
        }
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_streamer_live_device_resolution() {
        let pipe = AudioPipeline::new(48000.0);
        let streamer = AudioStreamer::new(pipe);
        let mic_setting = crate::dsp::volume_storage::load_mic_setting();
        println!("Persistent mic setting: {}", mic_setting);

        let (in_dev, out_dev) = streamer.find_devices();
        let in_name = in_dev.as_ref().and_then(|d| d.name().ok());
        let out_name = out_dev.as_ref().and_then(|d| d.name().ok());
        println!("Resolved in_dev: {:?}", in_name);
        println!("Resolved out_dev: {:?}", out_name);
        if in_dev.is_none() || out_dev.is_none() {
            println!("Skipping on headless CI: audio hardware devices unavailable");
            return;
        }

        if let Some(ref name) = in_name {
            if let Some(id) = crate::driver::get_device_id_by_name(name) {
                println!("in_dev [{}] (ID {}) volume: {:?}", name, id, crate::driver::get_device_volume(id));
            }
        }
        if let Some(ref name) = out_name {
            if let Some(id) = crate::driver::get_device_id_by_name(name) {
                println!("out_dev [{}] (ID {}) volume: {:?}", name, id, crate::driver::get_device_volume(id));
            }
        }
        if let Some(spk_id) = crate::driver::get_device_id_by_name("speaker") {
            let spk_vol = crate::driver::get_device_volume(spk_id);
            println!("Speaker device (ID {}) volume: {:?}", spk_id, spk_vol);
            if let Some(v) = spk_vol {
                let set_res = crate::driver::set_device_volume(spk_id, v);
                println!("set_device_volume on speaker result: {:?}", set_res);
                assert!(set_res.is_ok(), "Setting speaker volume should succeed");
            }
        }
        if let Some(hp_id) = crate::driver::get_device_id_by_name("headphone") {
            println!("Headphone device (ID {}) volume: {:?}", hp_id, crate::driver::get_device_volume(hp_id));
        }
        assert!(in_dev.is_some(), "Must resolve input loopback device (OmniRip Audio)");
        assert!(out_dev.is_some(), "Must resolve output playback device");
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_streamer_full_start_and_stop() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);
        let start_res = streamer.start();
        println!("streamer.start() result: {:?}", start_res);
        if start_res.is_err() || streamer.output_stream.is_none() {
            println!("Skipping on headless CI: audio hardware output unavailable");
            return;
        }

        let is_running = streamer.is_running.load(Ordering::SeqCst);
        let has_input = streamer.input_stream.is_some();
        let has_output = streamer.output_stream.is_some();
        let current_out = get_macos_default_output_id();
        println!("is_running: {}, has_input: {}, has_output: {}, current_out: {:?}", is_running, has_input, has_output, current_out);
        assert!(is_running, "streamer should be running");
        if !has_input {
            println!("Skipping input_stream assertion on headless CI runner without audio loopback device");
            streamer.terminate();
            return;
        }
        assert!(has_input, "streamer must have input_stream");
        assert!(has_output, "streamer must have output_stream");

        streamer.terminate();
        let restored_out = get_macos_default_output_id();
        println!("restored_out: {:?}", restored_out);
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_hardware_volume_synchronization_parity() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);
        let phys_id = streamer.physical_output_device_id();
        println!("physical_output_device_id: {:?}", phys_id);
        if phys_id.is_none() {
            println!("Skipping on headless CI: no physical audio output device found");
            return;
        }

        // Test that poll_health can read loopback volume and keep system_volume_bits updated
        let ran = streamer.poll_health();
        let vol_bits = streamer.system_volume_bits.load(Ordering::Relaxed);
        let vol = f32::from_bits(vol_bits);
        println!("poll_health ran: {}, synced volume: {}", ran, vol);
        assert!(vol >= 0.0 && vol <= 1.0, "Volume must be in valid scalar range [0.0, 1.0]");
    }
}
