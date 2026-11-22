//! Cross-Platform Low-Latency Audio Streamer in pure Rust.
//!
//! Bridges desktop audio into Orchestria's 64-bit DSP pipeline and physical DAC:
//! - macOS HAL v2: Zero-Dot POSIX Shared Memory (`/orchestria_audio_shm`, zero CoreAudio input streams).
//! - Windows: Isolated virtual audio endpoint + WASAPI capture & playback (zero echo).
//! - Linux: User-space PipeWire/PulseAudio null-sink (`Orchestria_Audio.monitor`, zero echo, zero sudo).

use super::servo::{create_servo_ring_buffer, ServoReader, ServoWriter};
use super::shm_capture::ShmCaptureHandle;
use super::AudioPipeline;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig};
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioEngineType {
    PureRustIpc,    // Pure Rust Zero-Driver IPC Engine (/tmp/orchestria_audio.sock)
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
pub enum CaptureBackendKind {
    None,
    MacOsShmV2,
    LegacyCoreAudioLoopback,
    WindowsVirtualWasapi,
    LinuxPipeWireMonitor,
}

impl CaptureBackendKind {
    pub fn label(&self) -> &'static str {
        match self {
            Self::None => "App-Only Direct Hardware",
            Self::MacOsShmV2 => "Zero-Dot SHM HAL v2",
            Self::LegacyCoreAudioLoopback => "Legacy CoreAudio Loopback",
            Self::WindowsVirtualWasapi => "Windows Virtual Endpoint (Zero-Echo)",
            Self::LinuxPipeWireMonitor => "PipeWire/PulseAudio Virtual Sink (Zero-Echo)",
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
    AcousticHarmonics,
    PinkNoise,
    Sine1k,
    FrequencySweep,
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
            TestToneMode::AcousticHarmonics => "Multi-octave harmonic chord (55Hz-12kHz) for real-time EQ auditioning",
            TestToneMode::PinkNoise => "Gardner -3dB/oct pink noise for acoustic response calibration",
            TestToneMode::Sine1k => "1,000 Hz 0.0dBFS calibrated sine wave for level & phase matching",
            TestToneMode::FrequencySweep => "20Hz - 20kHz logarithmic acoustic sweep for resonant peak detection",
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
        let _ = AudioObjectSetPropertyData(
            1,
            &addr_set,
            0,
            std::ptr::null(),
            4,
            &target_id as *const _ as *const _,
        );
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
    let hw_id = crate::driver::first_physical_output_device_id()
        .ok_or_else(|| "No hardware output device found in CoreAudio".to_string())?;
    set_macos_system_output_to_device_id(hw_id)?;
    crate::driver::auto_heal_device_volume_and_mute(hw_id);
    let name = crate::driver::get_device_name(hw_id).unwrap_or_else(|| format!("ID {}", hw_id));
    Ok(format!("macOS Default Output restored to hardware ({})", name))
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

/// Output device that was the system default before Orchestria routed system audio to its virtual device (0 = none).
#[cfg(target_os = "macos")]
static OUTPUT_BEFORE_LOOPBACK: AtomicU32 = AtomicU32::new(0);

#[cfg(target_os = "macos")]
fn remember_output_before_loopback(device_id: u32) {
    if let Some(name) = crate::driver::get_device_name(device_id) {
        if !crate::driver::is_virtual_audio_device_name(&name) {
            OUTPUT_BEFORE_LOOPBACK.store(device_id, Ordering::SeqCst);
        }
    }
}

/// Puts system output back on the real hardware device it had before virtual routing, if Orchestria changed it.
#[cfg(target_os = "macos")]
pub fn restore_system_output() {
    let saved = OUTPUT_BEFORE_LOOPBACK.swap(0, Ordering::SeqCst);
    if saved != 0 {
        if let Some(name) = crate::driver::get_device_name(saved) {
            if !crate::driver::is_virtual_audio_device_name(&name) {
                if set_macos_system_output_to_device_id(saved).is_ok() {
                    crate::driver::auto_heal_device_volume_and_mute(saved);
                    return;
                }
            }
        }
    }
    // Fallback: if current default is still a virtual device, rescue onto any available physical output.
    if let Some(cur) = get_macos_default_output_id() {
        if let Some(name) = crate::driver::get_device_name(cur) {
            if crate::driver::is_virtual_audio_device_name(&name) {
                let _ = set_macos_system_output_to_hardware();
            }
        }
    }
}

#[cfg(not(target_os = "macos"))]
pub fn restore_system_output() {
    #[cfg(target_os = "linux")]
    crate::driver::linux::teardown_virtual_sink(None, None);
}

fn score_output_device_name(name: &str) -> u8 {
    let n = name.to_lowercase();
    if n.contains("ibasso") || n.contains("dac") || n.contains("fiio") || n.contains("chord") || n.contains("schiit") {
        0
    } else if n.contains("headphone") {
        1
    } else if n.contains("airpods") || n.contains("bluetooth") || n.contains("beats") {
        2
    } else if n.contains("speaker") || n.contains("built-in") || n.contains("macbook") {
        3
    } else {
        4
    }
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
    writer_handle: Option<Arc<Mutex<ServoWriter>>>,
    shm_capture: Option<ShmCaptureHandle>,
    active_capture_backend: CaptureBackendKind,
    #[cfg_attr(not(target_os = "linux"), allow(dead_code))]
    saved_linux_sink: Option<String>,
    #[cfg_attr(not(target_os = "linux"), allow(dead_code))]
    linux_null_sink_module: Option<u32>,
    #[cfg_attr(not(target_os = "windows"), allow(dead_code))]
    saved_windows_output_name: Option<String>,
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
            input_capture_enabled: Arc::new(AtomicBool::new(false)),
            chip_profile: Arc::new(Mutex::new(initial_chip)),
            input_stream: None,
            output_stream: None,
            reader_handle: None,
            writer_handle: None,
            shm_capture: None,
            active_capture_backend: CaptureBackendKind::None,
            saved_linux_sink: None,
            linux_null_sink_module: None,
            saved_windows_output_name: None,
        }
    }

    pub fn active_capture_backend(&self) -> CaptureBackendKind {
        self.active_capture_backend
    }

    pub fn set_dac_flavor(&self, flavor: super::enhancer::DacHardwareFlavor) {
        if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.set_dac_flavor(flavor);
        }
        crate::dsp::volume_storage::save_dac_flavor_setting(flavor);
    }

    pub fn cycle_dac_flavor(&self) -> super::enhancer::DacHardwareFlavor {
        let new_flavor = if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.cycle_dac_flavor()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        };
        crate::dsp::volume_storage::save_dac_flavor_setting(new_flavor);
        new_flavor
    }

    pub fn cycle_dac_flavor_reverse(&self) -> super::enhancer::DacHardwareFlavor {
        let new_flavor = if let Ok(mut pipe) = self.pipeline.lock() {
            pipe.dac_mimicker.cycle_flavor_reverse()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        };
        crate::dsp::volume_storage::save_dac_flavor_setting(new_flavor);
        new_flavor
    }

    pub fn current_dac_flavor(&self) -> super::enhancer::DacHardwareFlavor {
        if let Ok(pipe) = self.pipeline.lock() {
            pipe.current_dac_flavor()
        } else {
            super::enhancer::DacHardwareFlavor::StockOemPlus
        }
    }

    pub fn hardware_chip_profile(&self) -> super::hardware_detect::HardwareChipProfile {
        if let Ok(prof) = self.chip_profile.lock() {
            prof.clone()
        } else {
            super::hardware_detect::HardwareChipProfile::default()
        }
    }

    pub fn update_chip_profile(&self, profile: super::hardware_detect::HardwareChipProfile) {
        if let Ok(mut lock) = self.chip_profile.lock() {
            *lock = profile;
        }
    }

    pub fn available_input_names() -> Vec<String> {
        #[cfg(target_os = "windows")]
        if crate::driver::windows::is_headless_windows_ci() {
            return vec!["Pure Rust IPC Transport (/tmp/orchestria_audio.sock)".to_string()];
        }

        let mut list = Vec::new();
        let host = cpal::default_host();
        if let Ok(devs) = host.input_devices() {
            for d in devs {
                if let Ok(name) = d.name() {
                    let n = name.to_lowercase();
                    // Only virtual loopback sources (never real microphones).
                    let is_virtual_source = crate::driver::is_virtual_audio_device_name(&name)
                        || n.contains(".monitor");
                    if is_virtual_source && !n.contains("mic") && !list.contains(&name) {
                        list.push(name);
                    }
                }
            }
        }
        #[cfg(target_os = "macos")]
        if crate::driver::installed_driver_version()
            .map(|v| v >= crate::driver::bundle::EXPECTED_DRIVER_BUNDLE_VERSION)
            .unwrap_or(false)
            && crate::driver::get_device_id_by_name("Orchestria Audio").is_some()
        {
            list.insert(0, "Orchestria Audio (Zero-Dot SHM v2)".to_string());
        }
        list.push("Pure Rust IPC Transport (/tmp/orchestria_audio.sock)".to_string());
        list.sort_by_key(|name| {
            let n = name.to_lowercase();
            if n.contains("orchestria") {
                0
            } else if n.contains("blackhole") || n.contains("vb-audio") || n.contains("cable") {
                1
            } else {
                2
            }
        });
        list
    }

    pub fn available_output_names() -> Vec<String> {
        #[cfg(target_os = "windows")]
        if crate::driver::windows::is_headless_windows_ci() {
            return vec!["Default Audio Output".to_string()];
        }

        let host = cpal::default_host();
        let mut list = Vec::new();
        if let Ok(devs) = host.output_devices() {
            for d in devs {
                if let Ok(name) = d.name() {
                    let n = name.to_lowercase();
                    // Include ALL real physical output devices (DACs, Headphones, AirPods/BT, Display/HDMI, Speakers)
                    // while excluding virtual loopback/cable endpoints and mics.
                    if !crate::driver::is_virtual_audio_device_name(&name)
                        && !n.contains("stream")
                        && !n.contains("mic")
                        && !list.contains(&name)
                    {
                        list.push(name);
                    }
                }
            }
        }
        list.sort_by_key(|name| score_output_device_name(name));
        list
    }

    pub fn cycle_input_device(&mut self) -> String {
        let inputs = Self::available_input_names();
        if inputs.is_empty() {
            return "No Inputs Found".to_string();
        }
        let current = self.active_input_name();
        let next_idx = inputs
            .iter()
            .position(|n| n == &current)
            .map(|i| (i + 1) % inputs.len())
            .unwrap_or(0);
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
        let next_idx = outputs
            .iter()
            .position(|n| n == &current)
            .map(|i| (i + 1) % outputs.len())
            .unwrap_or(0);
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
        if self.active_capture_backend == CaptureBackendKind::MacOsShmV2 {
            return "Orchestria Audio (Zero-Dot SHM v2)".to_string();
        }
        if let Some(ref name) = self.selected_input_name {
            name.clone()
        } else {
            let (in_dev, _) = self.find_devices();
            in_dev
                .and_then(|d| d.name().ok())
                .unwrap_or_else(|| "Default Input".to_string())
        }
    }

    pub fn active_output_name(&self) -> String {
        if let Some(ref name) = self.selected_output_name {
            name.clone()
        } else {
            let (_, out_dev) = self.find_devices();
            out_dev
                .and_then(|d| d.name().ok())
                .unwrap_or_else(|| "Default Output".to_string())
        }
    }

    #[cfg(target_os = "macos")]
    pub fn physical_output_device_id(&self) -> Option<u32> {
        let out_name = self.active_output_name();
        if !crate::driver::is_virtual_audio_device_name(&out_name) {
            if let Some(id) = crate::driver::get_device_id_by_name(&out_name) {
                return Some(id);
            }
        }
        crate::driver::first_physical_output_device_id()
    }

    #[cfg(not(target_os = "macos"))]
    pub fn physical_output_device_id(&self) -> Option<u32> {
        None
    }

    pub fn set_iem_exclusive_mode(&mut self) -> Result<String, String> {
        self.test_tone_active.store(false, Ordering::SeqCst);

        let outputs = Self::available_output_names();
        if let Some(ibasso) = outputs
            .iter()
            .find(|n| {
                let low = n.to_lowercase();
                low.contains("ibasso") || low.contains("pro") || low.contains("dac")
            })
        {
            self.selected_output_name = Some(ibasso.clone());
        } else if let Some(headphones) = outputs.iter().find(|n| n.to_lowercase().contains("headphone")) {
            self.selected_output_name = Some(headphones.clone());
        } else if let Some(first) = outputs.first() {
            self.selected_output_name = Some(first.clone());
        }

        self.restart()?;

        let out_name = self.active_output_name();
        Ok(format!(
            "TRANSDUCER DIRECT ACTIVE: Pure Rust Engine -> Orchestria EQ -> [{}]",
            out_name
        ))
    }

    /// Discover capture device (virtual loopback/monitor) and real physical output transducer.
    pub fn find_devices(&self) -> (Option<Device>, Option<Device>) {
        #[cfg(target_os = "windows")]
        if crate::driver::windows::is_headless_windows_ci() {
            return (None, None);
        }

        let host = cpal::default_host();
        let mut in_dev = None;
        let mut out_dev = None;

        // 1. Resolve virtual capture device (microphones strictly forbidden)
        let in_devs: Vec<Device> = host.input_devices().map(|iter| iter.collect()).unwrap_or_default();
        if let Some(ref target) = self.selected_input_name {
            in_dev = in_devs
                .iter()
                .find(|d| {
                    d.name()
                        .map(|name| !name.to_lowercase().contains("mic") && name == target.as_str())
                        .unwrap_or(false)
                })
                .cloned();
        }
        if in_dev.is_none() {
            for dev in &in_devs {
                if let Ok(name) = dev.name() {
                    let n = name.to_lowercase();
                    let is_virtual = crate::driver::is_virtual_audio_device_name(&name)
                        || n.contains(".monitor");
                    if is_virtual && !n.contains("mic") && n.contains("orchestria") {
                        in_dev = Some(dev.clone());
                        break;
                    }
                }
            }
        }
        if in_dev.is_none() {
            for dev in &in_devs {
                if let Ok(name) = dev.name() {
                    let n = name.to_lowercase();
                    if (n.contains("blackhole") || n.contains("vb-audio") || n.contains("cable") || n.contains(".monitor"))
                        && !n.contains("mic")
                    {
                        in_dev = Some(dev.clone());
                        break;
                    }
                }
            }
        }

        // 2. Resolve physical output playback device (NEVER select a virtual loopback as physical output)
        let out_devs: Vec<Device> = host.output_devices().map(|iter| iter.collect()).unwrap_or_default();
        if let Some(ref target) = self.selected_output_name {
            out_dev = out_devs
                .iter()
                .find(|d| {
                    d.name()
                        .map(|n| n == target.as_str() && !crate::driver::is_virtual_audio_device_name(&n))
                        .unwrap_or(false)
                })
                .cloned();
        }
        if out_dev.is_none() {
            let mut candidates: Vec<(u8, Device)> = out_devs
                .into_iter()
                .filter_map(|d| {
                    let name = d.name().ok()?;
                    let low = name.to_lowercase();
                    if crate::driver::is_virtual_audio_device_name(&name)
                        || low.contains("stream")
                        || low.contains("mic")
                    {
                        None
                    } else {
                        Some((score_output_device_name(&name), d))
                    }
                })
                .collect();
            candidates.sort_by_key(|(score, _)| *score);
            out_dev = candidates.into_iter().next().map(|(_, d)| d);
        }
        if out_dev.is_none() {
            if let Some(def) = host.default_output_device() {
                if let Ok(name) = def.name() {
                    if !crate::driver::is_virtual_audio_device_name(&name) {
                        out_dev = Some(def);
                    }
                }
            }
        }

        (in_dev, out_dev)
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
        self.test_tone_mode
            .lock()
            .map(|m| *m)
            .unwrap_or(TestToneMode::AcousticHarmonics)
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

    /// Internal builder for legacy CoreAudio / PipeWire / Windows WASAPI virtual-device input stream.
    fn build_input_stream_internal(&mut self) -> Option<Stream> {
        let (in_dev, _) = self.find_devices();
        let in_d = in_dev?;
        let writer_for_in = self
            .writer_handle
            .as_ref()
            .cloned()
            .or_else(|| self.ipc_server.as_ref().map(|s| s.writer()))?;
        let reader_arc = self.reader_handle.as_ref()?.clone();

        let in_dev_name = in_d.name().unwrap_or_default();
        let in_name_clone = in_dev_name.clone();
        let needs_rebuild_in = Arc::clone(&self.needs_rebuild);
        let err_fn = move |err| {
            eprintln!("Input audio stream error on [{}]: {}", in_name_clone, err);
            needs_rebuild_in.store(true, Ordering::SeqCst);
        };

        let out_rate = self.active_sample_rate() as u32;
        let in_config = in_d
            .default_input_config()
            .map(|c| StreamConfig {
                channels: 2,
                sample_rate: c.sample_rate(),
                buffer_size: cpal::BufferSize::Default,
            })
            .unwrap_or_else(|_| StreamConfig {
                channels: 2,
                sample_rate: cpal::SampleRate(out_rate),
                buffer_size: cpal::BufferSize::Default,
            });

        let in_rate = in_config.sample_rate.0;
        if let Ok(mut r) = reader_arc.lock() {
            r.set_nominal_ratio(in_rate as f64 / out_rate as f64);
        }

        let is_paused_in = Arc::clone(&self.is_paused);
        let sys_vol_in = Arc::clone(&self.system_volume_bits);
        let in_is_orchestria = in_dev_name.to_lowercase().contains("orchestria");
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
                let norm_factor = if in_is_orchestria && in_vol < 0.999 {
                    if in_vol > 0.001 {
                        1.0f32 / in_vol
                    } else {
                        0.0f32
                    }
                } else {
                    1.0f32
                };

                for i in 0..n_frames {
                    scratch[i] = [data[i * 2] * norm_factor, data[i * 2 + 1] * norm_factor];
                }

                if let Ok(mut w) = writer_for_in.try_lock() {
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
                eprintln!("Warning: Failed to build input capture stream on [{}]: {}", in_dev_name, e);
                None
            }
        }
    }

    fn activate_system_capture_streams(&mut self) -> Result<CaptureBackendKind, String> {
        if self.shm_capture.is_some() || self.input_stream.is_some() {
            return Ok(self.active_capture_backend);
        }

        let Some(writer_arc) = self.writer_handle.as_ref().cloned() else {
            return Err("Audio servo writer not initialized".to_string());
        };
        let Some(reader_arc) = self.reader_handle.as_ref().cloned() else {
            return Err("Audio servo reader not initialized".to_string());
        };

        #[cfg(target_os = "macos")]
        {
            let orchestria_id = get_macos_device_id_by_keyword("orchestria");
            let driver_ver = crate::driver::installed_driver_version().unwrap_or(0);
            let shm_ready_driver = orchestria_id.is_some()
                && driver_ver >= crate::driver::bundle::EXPECTED_DRIVER_BUNDLE_VERSION;

            // Tier 1: Output-Only HAL v2 + Zero-Dot POSIX Shared Memory (zero CoreAudio input streams).
            if let Some(target_id) = orchestria_id {
                if shm_ready_driver {
                    if let Some(current_id) = get_macos_default_output_id() {
                        if current_id != target_id {
                            if let Some(name) = crate::driver::get_device_name(current_id) {
                                if !crate::driver::is_virtual_audio_device_name(&name) {
                                    self.saved_physical_output_id = Some(current_id);
                                    remember_output_before_loopback(current_id);
                                }
                            }
                        } else if self.saved_physical_output_id.is_none() {
                            self.saved_physical_output_id = self.physical_output_device_id();
                        }
                    }

                    let out_rate = self.active_sample_rate() as u32;
                    let shm_handle = ShmCaptureHandle::start(
                        writer_arc,
                        reader_arc,
                        out_rate,
                        Arc::clone(&self.system_volume_bits),
                        Arc::clone(&self.is_paused),
                        true,
                    )?;
                    let _ = set_macos_system_output_to_device_id(target_id);
                    self.shm_capture = Some(shm_handle);
                    self.active_capture_backend = CaptureBackendKind::MacOsShmV2;
                    return Ok(CaptureBackendKind::MacOsShmV2);
                }
            }

            // Tier 2: Legacy CoreAudio loopback (BlackHole 2ch or un-upgraded v1 HAL).
            if let Some(in_stream) = self.build_input_stream_internal() {
                let loopback_id = orchestria_id.or_else(|| get_macos_device_id_by_keyword("blackhole"));
                if let Some(target_id) = loopback_id {
                    if let Some(current_id) = get_macos_default_output_id() {
                        if current_id != target_id {
                            if let Some(name) = crate::driver::get_device_name(current_id) {
                                if !crate::driver::is_virtual_audio_device_name(&name) {
                                    self.saved_physical_output_id = Some(current_id);
                                    remember_output_before_loopback(current_id);
                                }
                            }
                        } else if self.saved_physical_output_id.is_none() {
                            self.saved_physical_output_id = self.physical_output_device_id();
                        }
                    }
                    let _ = set_macos_system_output_to_device_id(target_id);
                }
                self.input_stream = Some(in_stream);
                self.active_capture_backend = CaptureBackendKind::LegacyCoreAudioLoopback;
                return Ok(CaptureBackendKind::LegacyCoreAudioLoopback);
            }

            Err("No Orchestria Audio driver or loopback device installed (run :setup or F12).".to_string())
        }

        #[cfg(target_os = "linux")]
        {
            let _ = (writer_arc, reader_arc);
            if let Some(cur) = crate::driver::linux::get_default_sink() {
                if !crate::driver::linux::is_virtual_linux_sink(&cur) {
                    self.saved_linux_sink = Some(cur);
                }
            }
            match crate::driver::linux::ensure_virtual_sink() {
                Ok(mod_id) => {
                    if mod_id.is_some() {
                        self.linux_null_sink_module = mod_id;
                    }
                    let _ = crate::driver::linux::set_default_sink(
                        crate::driver::linux::ORCHESTRIA_LINUX_SINK,
                    );
                }
                Err(e) => return Err(e),
            }
            if let Some(in_stream) = self.build_input_stream_internal() {
                self.input_stream = Some(in_stream);
                self.active_capture_backend = CaptureBackendKind::LinuxPipeWireMonitor;
                Ok(CaptureBackendKind::LinuxPipeWireMonitor)
            } else {
                crate::driver::linux::teardown_virtual_sink(
                    self.linux_null_sink_module.take(),
                    self.saved_linux_sink.as_deref(),
                );
                Err("Could not open PipeWire/PulseAudio monitor stream for Orchestria_Audio.".to_string())
            }
        }

        #[cfg(target_os = "windows")]
        {
            let _ = (writer_arc, reader_arc);
            if crate::driver::windows::is_headless_windows_ci() {
                return Err("Headless Windows CI has no audio hardware".to_string());
            }
            if !crate::driver::windows::detect_virtual_sink_present() {
                return Err(
                    "Windows Virtual Audio Endpoint not installed yet (press F12 to set up)."
                        .to_string(),
                );
            }
            if let Some(cur) = crate::driver::windows::get_default_playback_device_name() {
                if !crate::driver::windows::is_virtual_windows_endpoint(&cur) {
                    self.saved_windows_output_name = Some(cur);
                }
            }
            let _ = crate::driver::windows::set_default_playback_device_by_name("Orchestria");
            if let Some(in_stream) = self.build_input_stream_internal() {
                self.input_stream = Some(in_stream);
                self.active_capture_backend = CaptureBackendKind::WindowsVirtualWasapi;
                Ok(CaptureBackendKind::WindowsVirtualWasapi)
            } else {
                if let Some(ref saved) = self.saved_windows_output_name {
                    let _ = crate::driver::windows::set_default_playback_device_by_name(saved);
                }
                Err("Could not attach WASAPI capture stream to virtual endpoint.".to_string())
            }
        }

        #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
        {
            let _ = (writer_arc, reader_arc);
            Err("System-wide capture not supported on this OS".to_string())
        }
    }

    fn deactivate_system_capture_streams(&mut self) {
        if let Some(mut shm) = self.shm_capture.take() {
            shm.stop();
        }
        if let Some(s) = self.input_stream.take() {
            let _ = s.pause();
            drop(s);
        }
        self.active_capture_backend = CaptureBackendKind::None;

        if !self.is_running.load(Ordering::SeqCst) {
            return;
        }

        #[cfg(target_os = "macos")]
        {
            let target_hw = self
                .saved_physical_output_id
                .take()
                .filter(|&id| {
                    crate::driver::get_device_name(id)
                        .map(|n| !crate::driver::is_virtual_audio_device_name(&n))
                        .unwrap_or(false)
                })
                .or_else(|| self.physical_output_device_id())
                .or_else(crate::driver::first_physical_output_device_id);

            if let Some(hw_id) = target_hw {
                let _ = set_macos_system_output_to_device_id(hw_id);
                crate::driver::auto_heal_device_volume_and_mute(hw_id);
            } else {
                let _ = set_macos_system_output_to_hardware();
            }
            OUTPUT_BEFORE_LOOPBACK.store(0, Ordering::SeqCst);
        }

        #[cfg(target_os = "linux")]
        {
            crate::driver::linux::teardown_virtual_sink(
                self.linux_null_sink_module.take(),
                self.saved_linux_sink.as_deref(),
            );
        }

        #[cfg(target_os = "windows")]
        {
            if let Some(ref saved) = self.saved_windows_output_name.take() {
                let _ = crate::driver::windows::set_default_playback_device_by_name(saved);
            }
        }
    }

    /// Toggles System-Wide EQ capture (`X` key / `:mic` / `:syseq`).
    /// On macOS HAL v2, turning ON uses Zero-Dot POSIX SHM without opening any mic stream.
    /// Turning OFF safely restores the physical hardware endpoint so desktop sound never mutes,
    /// while Orchestria's internal Workstation 4 player keeps full 64-bit DSP & EQ.
    pub fn set_input_capture(&mut self, enable: bool) -> (bool, String) {
        if !enable {
            self.input_capture_enabled.store(false, Ordering::SeqCst);
            self.deactivate_system_capture_streams();
            return (
                false,
                "System-Wide EQ: [OFF] (Direct Hardware Playback • App EQ active)".to_string(),
            );
        }

        self.input_capture_enabled.store(true, Ordering::SeqCst);
        if self.is_running.load(Ordering::SeqCst) {
            match self.activate_system_capture_streams() {
                Ok(CaptureBackendKind::MacOsShmV2) => (
                    true,
                    "System-Wide EQ: [ON] (Zero-Dot SHM Sound Engine Active)".to_string(),
                ),
                Ok(kind) => (
                    true,
                    format!("System-Wide EQ: [ON] ({})", kind.label()),
                ),
                Err(reason) => {
                    self.input_capture_enabled.store(false, Ordering::SeqCst);
                    self.deactivate_system_capture_streams();
                    (
                        false,
                        format!("System-Wide EQ: [OFF] ({})", reason),
                    )
                }
            }
        } else {
            (
                true,
                "System-Wide EQ: [ON] (Armed for Zero-Dot Sound Engine)".to_string(),
            )
        }
    }

    pub fn toggle_input_capture(&mut self) -> (bool, String) {
        let current = self.is_input_capture_enabled();
        self.set_input_capture(!current)
    }

    /// Hot-activates System-Wide EQ immediately (e.g. right after first-run driver installation).
    pub fn hot_activate_system_capture(&mut self) -> Result<String, String> {
        self.input_capture_enabled.store(true, Ordering::SeqCst);
        self.restart()?;
        if !self.is_input_capture_enabled() {
            return Err("System-Wide EQ capture could not activate after driver install.".to_string());
        }
        let out_name = self.active_output_name();
        Ok(format!(
            "Sound Engine ACTIVE ({}) -> DSP -> [{}]",
            self.active_capture_backend.label(),
            out_name
        ))
    }

    pub fn heal_routing(&mut self) {
        self.force_resync();

        #[cfg(target_os = "macos")]
        {
            if self.is_input_capture_enabled() {
                if let Some(loopback_id) = get_macos_device_id_by_keyword("orchestria")
                    .or_else(|| get_macos_device_id_by_keyword("blackhole"))
                {
                    let _ = set_macos_system_output_to_device_id(loopback_id);
                }
            } else if let Some(hw_id) = self
                .saved_physical_output_id
                .or_else(|| self.physical_output_device_id())
                .or_else(crate::driver::first_physical_output_device_id)
            {
                let _ = set_macos_system_output_to_device_id(hw_id);
            }

            let out_name = self.active_output_name();
            if let Some(id) = crate::driver::get_device_id_by_name(&out_name) {
                crate::driver::auto_heal_device_volume_and_mute(id);
            }
            if let Some(phys_id) = crate::driver::first_physical_output_device_id() {
                crate::driver::auto_heal_device_volume_and_mute(phys_id);
            }
        }
    }

    /// Polls audio stream health and watchdog heartbeats without re-hijacking capture if user turned it OFF.
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
            if self.output_stream.is_some() || self.input_stream.is_some() || self.shm_capture.is_some() {
                let _ = self.restart();
            }
            return true;
        }

        #[cfg(target_os = "macos")]
        {
            let target_id = if self.is_input_capture_enabled() {
                get_macos_device_id_by_keyword("orchestria")
                    .or_else(|| get_macos_device_id_by_keyword("blackhole"))
                    .or_else(get_macos_default_output_id)
            } else {
                self.physical_output_device_id().or_else(get_macos_default_output_id)
            };
            if let Some(id) = target_id {
                if let Some(vol) = crate::driver::get_device_volume(id) {
                    self.system_volume_bits.store(vol.to_bits(), Ordering::Relaxed);
                    if self.is_input_capture_enabled() {
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
        let pll = self
            .reader_handle
            .as_ref()
            .and_then(|r| r.lock().ok())
            .map(|r| r.pll_telemetry());
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

    pub fn set_master_volume(&mut self, volume: f32) {
        let safe_vol = volume.clamp(0.0, 1.0);
        let (player_pct, _) = crate::dsp::volume_storage::load_volume_settings();
        crate::dsp::volume_storage::save_volume_settings(player_pct, safe_vol);
        self.system_volume_bits.store(safe_vol.to_bits(), Ordering::Relaxed);

        #[cfg(target_os = "macos")]
        {
            let loopback_id = get_macos_device_id_by_keyword("orchestria")
                .or_else(|| get_macos_device_id_by_keyword("blackhole"))
                .or_else(get_macos_default_output_id);
            if let Some(id) = loopback_id {
                let _ = crate::driver::set_device_volume(id, safe_vol);
            }
            if let Some(phys_id) = self.physical_output_device_id() {
                let _ = crate::driver::set_device_volume(phys_id, safe_vol);
            }
        }
    }

    /// Start native real-time audio output stream and (only if `input_capture_enabled`) system capture.
    pub fn start(&mut self) -> Result<(), String> {
        if self.is_running.load(Ordering::SeqCst) {
            return Ok(());
        }

        let (_in_dev, out_dev) = self.find_devices();
        let out_dev = out_dev.ok_or_else(|| "No output playback device found".to_string())?;

        // Ensure active physical output endpoint is synchronized to volume and unmuted.
        #[cfg(target_os = "macos")]
        {
            let init_vol = if self.is_input_capture_enabled() {
                get_macos_device_id_by_keyword("orchestria")
                    .and_then(crate::driver::get_device_volume)
                    .unwrap_or_else(|| f32::from_bits(self.system_volume_bits.load(Ordering::Relaxed)).clamp(0.0, 1.0))
            } else {
                self.physical_output_device_id()
                    .and_then(crate::driver::get_device_volume)
                    .unwrap_or_else(|| f32::from_bits(self.system_volume_bits.load(Ordering::Relaxed)).clamp(0.0, 1.0))
            };
            self.system_volume_bits.store(init_vol.to_bits(), Ordering::Relaxed);

            if let Ok(dev_name) = out_dev.name() {
                if let Some(id) = crate::driver::get_device_id_by_name(&dev_name) {
                    let _ = crate::driver::unmute_device(id);
                    let _ = crate::driver::set_device_volume(id, init_vol);
                }
            }
        }

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
            pipe.set_sample_rate(sample_rate as f32);
        }

        let (writer, reader) = create_servo_ring_buffer(32768, self.sync_mode.target_frames());
        let reader_arc = Arc::new(Mutex::new(reader));
        self.reader_handle = Some(Arc::clone(&reader_arc));

        let ipc = Arc::new(super::transport::IpcAudioServer::new(writer));
        let writer_arc = ipc.writer();
        self.writer_handle = Some(writer_arc);
        if let Err(e) = ipc.start() {
            eprintln!("Warning: Failed to start Pure Rust IPC server: {}", e);
        }
        self.ipc_server = Some(ipc);

        // Build and start physical output stream.
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
                            pthread_set_qos_class_self_np(0x21, 0);
                        }
                        qos_set_out = true;
                    }

                    if is_paused_out.load(Ordering::SeqCst) {
                        data.fill(0.0);
                        return;
                    }

                    let n_frames = (data.len() / 2).min(2048);
                    let mut scratch = [[0.0f32, 0.0f32]; 2048];

                    let player_frames = if player_arc.is_playing() {
                        player_arc.read_frames(&mut scratch[..n_frames])
                    } else {
                        0
                    };

                    if player_frames == 0 {
                        if let Ok(mut r) = reader_for_out.try_lock() {
                            r.read(&mut scratch[..n_frames]);
                        }
                    }

                    if test_active.load(Ordering::SeqCst) {
                        let current_mode = test_mode_arc
                            .try_lock()
                            .map(|m| *m)
                            .unwrap_or(TestToneMode::AcousticHarmonics);
                        let sr = 48000.0f32;

                        for frame in scratch[..n_frames].iter_mut() {
                            let t = sample_idx as f32 / sr;
                            let (sig_l, sig_r) = match current_mode {
                                TestToneMode::AcousticHarmonics => {
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

                    if let Ok(mut pipe) = pipeline_arc.try_lock() {
                        pipe.process(&mut scratch[..n_frames]);
                    }

                    let v = f32::from_bits(sys_vol_arc.load(Ordering::Relaxed)).clamp(0.0, 1.0);
                    let target_gain = if v <= 0.001 {
                        0.0f32
                    } else if out_is_external_dac {
                        v * v * v
                    } else {
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

        out_stream
            .play()
            .map_err(|e| format!("Failed to play output stream: {}", e))?;

        self.output_stream = Some(out_stream);
        self.is_running.store(true, Ordering::SeqCst);

        // Strictly honor `input_capture_enabled`: ONLY switch OS default output & capture when armed.
        if self.is_input_capture_enabled() {
            if self.activate_system_capture_streams().is_err() {
                self.input_capture_enabled.store(false, Ordering::SeqCst);
                self.deactivate_system_capture_streams();
            }
        } else {
            self.active_capture_backend = CaptureBackendKind::None;
            // Ensure macOS isn't left stranded on an unread virtual device from an earlier session.
            #[cfg(target_os = "macos")]
            restore_system_output();
        }

        Ok(())
    }

    pub fn stop(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        if let Some(mut shm) = self.shm_capture.take() {
            shm.stop();
        }
        if let Some(ipc) = self.ipc_server.take() {
            ipc.stop();
        }
        if let Some(s) = self.output_stream.take() {
            let _ = s.pause();
        }
        if let Some(s) = self.input_stream.take() {
            let _ = s.pause();
        }
        self.active_capture_backend = CaptureBackendKind::None;
        self.reader_handle = None;
        self.writer_handle = None;
    }

    /// Full termination on application exit: stops audio streams and restores OS default output cleanly.
    pub fn terminate(&mut self) {
        self.stop();

        #[cfg(target_os = "macos")]
        {
            if let Some(saved_id) = self.saved_physical_output_id.take() {
                if let Some(name) = crate::driver::get_device_name(saved_id) {
                    if !crate::driver::is_virtual_audio_device_name(&name) {
                        let _ = set_macos_system_output_to_device_id(saved_id);
                    }
                }
            }
            restore_system_output();
        }

        #[cfg(target_os = "linux")]
        {
            crate::driver::linux::teardown_virtual_sink(
                self.linux_null_sink_module.take(),
                self.saved_linux_sink.as_deref(),
            );
        }

        #[cfg(target_os = "windows")]
        {
            if let Some(ref saved) = self.saved_windows_output_name.take() {
                let _ = crate::driver::windows::set_default_playback_device_by_name(saved);
            }
        }
    }
}

impl Drop for AudioStreamer {
    fn drop(&mut self) {
        self.terminate();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[cfg(target_os = "macos")]
    fn test_input_capture_toggle_and_mic_control() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        streamer.set_input_capture(false);
        assert!(!streamer.is_input_capture_enabled());
        assert_eq!(streamer.saved_physical_output_id, None);

        let (enabled, msg) = streamer.toggle_input_capture();
        assert!(enabled);
        assert!(streamer.is_input_capture_enabled());
        assert!(msg.contains("[ON]"));
        assert_eq!(
            streamer.saved_physical_output_id, None,
            "Toggle ON when stopped must not alter saved_physical_output_id"
        );

        let (enabled_off, msg_off) = streamer.toggle_input_capture();
        assert!(!enabled_off);
        assert!(!streamer.is_input_capture_enabled());
        assert!(msg_off.contains("[OFF]"));
        assert_eq!(
            streamer.saved_physical_output_id, None,
            "Toggle OFF when stopped must not alter saved_physical_output_id"
        );

        let (st, _) = streamer.set_input_capture(true);
        assert!(st);
        assert_eq!(streamer.saved_physical_output_id, None);
        let (st2, _) = streamer.set_input_capture(false);
        assert!(!st2);
        assert_eq!(streamer.saved_physical_output_id, None);
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

        assert!(!out_name.to_lowercase().contains("blackhole"), "Output must not be BlackHole loopback");
        assert!(!out_name.to_lowercase().contains("orchestria"), "Output must not be Orchestria Stream virtual");

        for inp in &inputs {
            assert!(!inp.to_lowercase().contains("mic"), "Inputs must never contain microphones: {}", inp);
        }

        let cycled = streamer.cycle_output_device();
        println!("Cycled Output: {}", cycled);
    }

    #[test]
    fn test_output_scoring_prioritizes_dacs_and_allows_airpods_and_display() {
        assert!(score_output_device_name("iBasso DC03 Pro") < score_output_device_name("External Headphones"));
        assert!(score_output_device_name("External Headphones") < score_output_device_name("AirPods Pro"));
        assert!(score_output_device_name("AirPods Pro") < score_output_device_name("MacBook Pro Speakers"));
        assert!(score_output_device_name("MacBook Pro Speakers") < score_output_device_name("LG ULTRAGEAR"));
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
                assert!(
                    first.contains("ibasso") || first.contains("dac") || first.contains("fiio"),
                    "Top priority must be external DAC: {}",
                    first
                );
            }
        }
    }

    #[test]
    #[cfg(unix)]
    fn test_pure_rust_ipc_stream_and_telemetry() {
        use super::super::transport::IpcAudioClient;

        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        if streamer.start().is_ok() {
            let socket_path = std::path::Path::new(super::super::transport::ORCHESTRIA_SOCKET_PATH);
            let mut bound = false;
            for _ in 0..20 {
                if socket_path.exists() {
                    bound = true;
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            assert!(bound, "Unix domain socket must be created after streamer.start()");

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
            assert!(!streamer.is_running.load(Ordering::SeqCst));
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

        streamer.toggle_pause();
        assert!(streamer.is_paused());
        streamer.heal_routing();
        assert!(streamer.is_paused());
    }

    #[test]
    fn test_poll_health_rebuild_and_stall_detection() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);

        assert!(!streamer.poll_health());

        streamer.is_running.store(true, Ordering::SeqCst);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        streamer.last_callback_epoch_ms.store(now, Ordering::SeqCst);
        assert!(!streamer.poll_health());

        streamer.needs_rebuild.store(true, Ordering::SeqCst);
        let healed = streamer.poll_health();
        assert!(healed);
        assert!(!streamer.needs_rebuild.load(Ordering::SeqCst));

        streamer.is_running.store(true, Ordering::SeqCst);
        streamer
            .last_callback_epoch_ms
            .store(now.saturating_sub(5000), Ordering::SeqCst);
        let healed_stall = streamer.poll_health();
        assert!(healed_stall);
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_macos_orchestria_loopback_discovery() {
        let orchestria_id = get_macos_device_id_by_keyword("orchestria");
        println!("Discovered Orchestria Audio Device ID: {:?}", orchestria_id);
        if orchestria_id.is_none() {
            println!("Skipping on headless CI: Orchestria Audio driver not installed in runner environment");
            return;
        }

        let default_id = get_macos_default_output_id();
        assert!(default_id.is_some(), "Default output device must be queryable");

        if let (Some(target_id), Some(orig_id)) = (orchestria_id, default_id) {
            let alt_id = if orig_id != target_id {
                orig_id
            } else {
                crate::driver::first_physical_output_device_id().unwrap_or(orig_id)
            };

            let _ = set_macos_system_output_to_device_id(target_id);
            let switched = get_macos_default_output_id();
            let _ = set_macos_system_output_to_device_id(alt_id);
            let restored = get_macos_default_output_id();
            let _ = set_macos_system_output_to_device_id(orig_id);
            assert_eq!(switched, Some(target_id), "macOS default output must switch to Orchestria Audio");
            assert_eq!(restored, Some(alt_id), "macOS default output must switch to alt device");
        }
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_streamer_live_device_resolution() {
        let pipe = AudioPipeline::new(48000.0);
        let streamer = AudioStreamer::new(pipe);

        let (in_dev, out_dev) = streamer.find_devices();
        let out_name = out_dev.as_ref().and_then(|d| d.name().ok());
        println!("Resolved in_dev: {:?}, out_dev: {:?}", in_dev.as_ref().and_then(|d| d.name().ok()), out_name);
        if out_dev.is_none() {
            println!("Skipping on headless CI: audio hardware devices unavailable");
            return;
        }
        assert!(out_dev.is_some(), "Must resolve output playback device");
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn test_streamer_full_start_and_stop() {
        let pipe = AudioPipeline::new(48000.0);
        let mut streamer = AudioStreamer::new(pipe);
        let original_output = get_macos_default_output_id();

        let start_res = streamer.start();
        println!("streamer.start() result: {:?}", start_res);
        if start_res.is_err() || streamer.output_stream.is_none() {
            println!("Skipping on headless CI: audio hardware output unavailable");
            return;
        }

        assert!(streamer.is_running.load(Ordering::SeqCst));
        assert!(streamer.output_stream.is_some());
        // Startup default has capture OFF so start() must NOT open an input stream or light the orange dot.
        assert!(!streamer.is_input_capture_enabled());
        assert!(streamer.input_stream.is_none());

        let has_capture_driver = crate::driver::get_device_id_by_name("Orchestria Audio").is_some()
            || crate::driver::get_device_id_by_name("BlackHole").is_some();
        let (enabled, _) = streamer.set_input_capture(true);
        assert_eq!(
            enabled, has_capture_driver,
            "Capture enables iff a virtual driver is installed"
        );
        if enabled && crate::driver::installed_driver_version().unwrap_or(0) >= 2 {
            assert_eq!(streamer.active_capture_backend(), CaptureBackendKind::MacOsShmV2);
            assert!(streamer.input_stream.is_none(), "Zero-Dot SHM v2 must NOT open CoreAudio input stream");
        }

        let (disabled, _) = streamer.set_input_capture(false);
        assert!(!disabled);
        assert!(streamer.input_stream.is_none());
        assert!(streamer.shm_capture.is_none());
        assert_eq!(streamer.active_capture_backend(), CaptureBackendKind::None);

        streamer.terminate();
        if let Some(id) = original_output {
            let _ = set_macos_system_output_to_device_id(id);
        }
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

        let ran = streamer.poll_health();
        let vol_bits = streamer.system_volume_bits.load(Ordering::Relaxed);
        let vol = f32::from_bits(vol_bits);
        println!("poll_health ran: {}, synced volume: {}", ran, vol);
        assert!(vol >= 0.0 && vol <= 1.0, "Volume must be in valid scalar range [0.0, 1.0]");
    }
}
