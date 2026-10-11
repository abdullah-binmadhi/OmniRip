//! Low-latency CoreAudio Duplex Audio Streamer in pure Rust using `cpal`.
//!
//! Spawns native CoreAudio real-time threads (zero GIL, zero GC), bridging
//! BlackHole 2ch loopback capture to the output DAC via lock-free SPSC servo buffer.

use super::servo::{create_servo_ring_buffer, ServoReader};
use super::AudioPipeline;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, Stream, StreamConfig};
use std::sync::atomic::{AtomicBool, Ordering};
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
    fn AudioObjectGetPropertyData(
        inObjectID: u32,
        inAddress: *const AudioObjectPropertyAddress,
        inQualifierDataSize: u32,
        inQualifierData: *const std::ffi::c_void,
        ioDataSize: *mut u32,
        outData: *mut std::ffi::c_void,
    ) -> i32;

    fn AudioObjectGetPropertyDataSize(
        inObjectID: u32,
        inAddress: *const AudioObjectPropertyAddress,
        inQualifierDataSize: u32,
        inQualifierData: *const std::ffi::c_void,
        outDataSize: *mut u32,
    ) -> i32;

    fn AudioObjectSetPropertyData(
        inObjectID: u32,
        inAddress: *const AudioObjectPropertyAddress,
        inQualifierDataSize: u32,
        inQualifierData: *const std::ffi::c_void,
        inDataSize: u32,
        inData: *const std::ffi::c_void,
    ) -> i32;
}

#[cfg(target_os = "macos")]
pub fn get_macos_default_output_id() -> Option<u32> {
    unsafe {
        let addr = AudioObjectPropertyAddress {
            mSelector: 0x644f7574, // 'dOut'
            mScope: 0x676c6f62,     // 'glob'
            mElement: 0,
        };
        let mut dev_id = 0u32;
        let mut size = 4u32;
        if AudioObjectGetPropertyData(1, &addr, 0, std::ptr::null(), &mut size, &mut dev_id as *mut _ as *mut _) == 0 {
            Some(dev_id)
        } else {
            None
        }
    }
}

#[cfg(target_os = "macos")]
pub fn get_macos_device_id_by_keyword(keyword: &str) -> Option<u32> {
    unsafe {
        let addr_devs = AudioObjectPropertyAddress {
            mSelector: 0x64657623, // 'dev#'
            mScope: 0x676c6f62,     // 'glob'
            mElement: 0,
        };
        let mut size = 0u32;
        if AudioObjectGetPropertyDataSize(1, &addr_devs, 0, std::ptr::null(), &mut size) != 0 || size == 0 {
            return None;
        }

        let count = (size / 4) as usize;
        let mut dev_ids = vec![0u32; count];
        if AudioObjectGetPropertyData(1, &addr_devs, 0, std::ptr::null(), &mut size, dev_ids.as_mut_ptr() as *mut _) != 0 {
            return None;
        }

        let addr_name = AudioObjectPropertyAddress {
            mSelector: 0x6e616d65, // 'name'
            mScope: 0x676c6f62,
            mElement: 0,
        };

        let kw = keyword.to_lowercase();
        for id in dev_ids {
            let mut name_buf = [0u8; 256];
            let mut name_size = 256u32;
            if AudioObjectGetPropertyData(id, &addr_name, 0, std::ptr::null(), &mut name_size, name_buf.as_mut_ptr() as *mut _) == 0 {
                let name = String::from_utf8_lossy(&name_buf[..name_size.saturating_sub(1) as usize]);
                if name.to_lowercase().contains(&kw) {
                    return Some(id);
                }
            }
        }
        None
    }
}

#[cfg(target_os = "macos")]
pub fn set_macos_system_output_to_device_id(target_id: u32) -> Result<(), String> {
    unsafe {
        // Set DefaultOutput ('dOut') and SystemOutput ('sOut')
        for selector in [0x644f7574, 0x734f7574] {
            let addr_set = AudioObjectPropertyAddress {
                mSelector: selector,
                mScope: 0x676c6f62,
                mElement: 0,
            };
            let set_res = AudioObjectSetPropertyData(1, &addr_set, 0, std::ptr::null(), 4, &target_id as *const _ as *const _);
            if set_res != 0 {
                return Err(format!("Failed to set CoreAudio output selector 0x{:08x}: code {}", selector, set_res));
            }
        }
        Ok(())
    }
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
        .or_else(|| get_macos_device_id_by_keyword("speaker"))
        .ok_or_else(|| "No hardware output device found in CoreAudio".to_string())?;
    set_macos_system_output_to_device_id(hw_id)?;
    Ok(format!("macOS Default Output restored to hardware (ID {})", hw_id))
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
    pub pipeline: Arc<Mutex<AudioPipeline>>,
    pub selected_input_name: Option<String>,
    pub selected_output_name: Option<String>,
    pub saved_physical_output_id: Option<u32>,
    pub ipc_server: Option<Arc<super::transport::IpcAudioServer>>,
    input_stream: Option<Stream>,
    output_stream: Option<Stream>,
    reader_handle: Option<Arc<Mutex<ServoReader>>>,
}

impl AudioStreamer {
    pub fn new(pipeline: AudioPipeline) -> Self {
        Self {
            sync_mode: SyncMode::Ultra,
            engine_type: AudioEngineType::PureRustIpc,
            is_running: Arc::new(AtomicBool::new(false)),
            is_paused: Arc::new(AtomicBool::new(false)),
            test_tone_active: Arc::new(AtomicBool::new(false)),
            test_tone_mode: Arc::new(Mutex::new(TestToneMode::AcousticHarmonics)),
            pipeline: Arc::new(Mutex::new(pipeline)),
            selected_input_name: None,
            selected_output_name: None,
            saved_physical_output_id: None,
            ipc_server: None,
            input_stream: None,
            output_stream: None,
            reader_handle: None,
        }
    }

    pub fn available_input_names() -> Vec<String> {
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

    pub fn available_output_names() -> Vec<String> {
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
        }
    }

    pub fn set_sync_mode(&mut self, mode: SyncMode) {
        self.sync_mode = mode;
        if let Some(reader) = &self.reader_handle {
            if let Ok(r) = reader.lock() {
                r.set_target_frames(mode.target_frames());
            }
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
    /// Dispatches hardware volume to external DACs (iBasso) or 64-bit digital DSP scaling for MacBook headphones/speakers.
    pub fn set_master_volume(&mut self, volume: f32) {
        let out_name = self.active_output_name().to_lowercase();
        if (out_name.contains("ibasso") || out_name.contains("dac") || out_name.contains("pro"))
            && !out_name.contains("headphone")
        {
            #[cfg(target_os = "macos")]
            if let Some(dac_id) = get_macos_device_id_by_keyword("ibasso")
                .or_else(|| get_macos_device_id_by_keyword("dac"))
            {
                let _ = crate::driver::set_device_volume(dac_id, volume);
            }
        } else {
            // Apply 64-bit digital DSP scaling inside OmniRip for MacBook headphones / speakers
            if let Ok(mut pipe) = self.pipeline.lock() {
                if volume <= 0.001 {
                    pipe.preamp_db = -96.0;
                } else {
                    pipe.preamp_db = (20.0 * volume.log10()).clamp(-60.0, 0.0);
                }
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

        // If OmniRip Audio or loopback is active, automatically redirect macOS system default output
        #[cfg(target_os = "macos")]
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
                        }
                    }
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

        // 1. Optional Hardware Input Stream Callback (if external hardware input selected)
        let in_stream = if let Some(in_d) = in_dev {
            let in_dev_name = in_d.name().unwrap_or_default();
            let err_fn = move |err| eprintln!("Input audio stream error on [{}]: {}", in_dev_name, err);
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
            match in_d.build_input_stream(
                &in_config,
                move |data: &[f32], _: &_| {
                    if is_paused_in.load(Ordering::SeqCst) {
                        return;
                    }
                    let mut scratch = Vec::with_capacity(data.len() / 2);
                    for chunk in data.chunks_exact(2) {
                        scratch.push([chunk[0], chunk[1]]);
                    }
                    if let Ok(mut w) = writer_for_in.lock() {
                        w.write(&scratch);
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
        };

        // 2. Native Output Stream Callback (DAC Playback + Test Tone Synthesizer + DSP Pipeline)
        let pipeline_arc = Arc::clone(&self.pipeline);
        let reader_for_out = Arc::clone(&reader_arc);
        let test_active = Arc::clone(&self.test_tone_active);
        let test_mode_arc = Arc::clone(&self.test_tone_mode);
        let is_paused_out = Arc::clone(&self.is_paused);

        let mut sample_idx: u64 = 0;
        let mut b0 = 0.0f32;
        let mut b1 = 0.0f32;
        let mut b2 = 0.0f32;
        let mut seed: u64 = 987654321;

        let out_stream = out_dev
            .build_output_stream(
                &config,
                move |data: &mut [f32], _: &_| {
                    if is_paused_out.load(Ordering::SeqCst) {
                        data.fill(0.0);
                        return;
                    }

                    let n_frames = data.len() / 2;
                    let mut scratch = vec![[0.0f32, 0.0f32]; n_frames];

                    if let Ok(mut r) = reader_for_out.lock() {
                        r.read(&mut scratch);
                    }

                    if test_active.load(Ordering::SeqCst) {
                        let current_mode = test_mode_arc.lock().map(|m| *m).unwrap_or(TestToneMode::AcousticHarmonics);
                        let sr = 48000.0f32;

                        for frame in scratch.iter_mut() {
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
                        pipe.process(&mut scratch);
                    }

                    for (i, frame) in scratch.iter().enumerate() {
                        data[i * 2] = frame[0];
                        data[i * 2 + 1] = frame[1];
                    }
                },
                |err| eprintln!("Output audio stream error: {}", err),
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

#[cfg(test)]
mod tests {
    use super::*;

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
                for _ in 0..30 {
                    let (telem, _) = streamer.telemetry();
                    if telem.total_frames >= 512 || telem.total_packets >= 1 {
                        telem_ok = true;
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(10));
                }
                assert!(telem_ok, "Telemetry must reflect received frames within 300ms");

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
}
