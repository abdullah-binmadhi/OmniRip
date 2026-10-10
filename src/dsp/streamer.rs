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
pub enum SyncMode {
    Extreme,  // 256 frames (~5.3ms cushion)
    Ultra,    // 512 frames (~10.6ms cushion)
    Balanced, // 1024 frames (~21.3ms cushion)
    Stable,   // 2048 frames (~42.7ms cushion)
}

impl SyncMode {
    pub fn target_frames(&self) -> usize {
        match self {
            SyncMode::Extreme => 256,
            SyncMode::Ultra => 512,
            SyncMode::Balanced => 1024,
            SyncMode::Stable => 2048,
        }
    }
}

pub struct AudioStreamer {
    pub sync_mode: SyncMode,
    pub is_running: Arc<AtomicBool>,
    pub pipeline: Arc<Mutex<AudioPipeline>>,
    input_stream: Option<Stream>,
    output_stream: Option<Stream>,
    reader_handle: Option<Arc<Mutex<ServoReader>>>,
}

impl AudioStreamer {
    pub fn new(pipeline: AudioPipeline) -> Self {
        Self {
            sync_mode: SyncMode::Ultra,
            is_running: Arc::new(AtomicBool::new(false)),
            pipeline: Arc::new(Mutex::new(pipeline)),
            input_stream: None,
            output_stream: None,
            reader_handle: None,
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

    /// Discover available loopback input device (BlackHole 2ch) and DAC output.
    pub fn find_devices() -> (Option<Device>, Option<Device>) {
        let host = cpal::default_host();
        let mut in_dev = None;
        let mut out_dev = None;

        if let Ok(devices) = host.input_devices() {
            for dev in devices {
                if let Ok(name) = dev.name() {
                    let n = name.to_lowercase();
                    if n.contains("blackhole") || n.contains("omnirip") || n.contains("aggregate") {
                        in_dev = Some(dev);
                        break;
                    }
                }
            }
        }

        if let Ok(devices) = host.output_devices() {
            for dev in devices {
                if let Ok(name) = dev.name() {
                    let n = name.to_lowercase();
                    if n.contains("ibasso") || n.contains("dac") || n.contains("pro") {
                        out_dev = Some(dev);
                        break;
                    }
                }
            }
        }

        if out_dev.is_none() {
            out_dev = host.default_output_device();
        }
        if in_dev.is_none() {
            in_dev = host.default_input_device();
        }

        (in_dev, out_dev)
    }

    /// Start native real-time CoreAudio loopback stream.
    pub fn start(&mut self) -> Result<(), String> {
        if self.is_running.load(Ordering::SeqCst) {
            return Ok(());
        }

        let (in_dev, out_dev) = Self::find_devices();
        let in_dev = in_dev.ok_or_else(|| "No input capture device found".to_string())?;
        let out_dev = out_dev.ok_or_else(|| "No output playback device found".to_string())?;

        let sample_rate = 48000;
        let channels = 2;
        let config = StreamConfig {
            channels,
            sample_rate: cpal::SampleRate(sample_rate),
            buffer_size: cpal::BufferSize::Fixed(256),
        };

        let (mut writer, reader) = create_servo_ring_buffer(32768, self.sync_mode.target_frames());
        let reader_arc = Arc::new(Mutex::new(reader));
        self.reader_handle = Some(Arc::clone(&reader_arc));

        // 1. Native Input Stream Callback (BlackHole Capture)
        let err_fn = |err| eprintln!("Input audio stream error: {}", err);
        let in_stream = in_dev
            .build_input_stream(
                &config,
                move |data: &[f32], _: &_| {
                    let mut scratch = Vec::with_capacity(data.len() / 2);
                    for chunk in data.chunks_exact(2) {
                        scratch.push([chunk[0], chunk[1]]);
                    }
                    writer.write(&scratch);
                },
                err_fn,
                None,
            )
            .map_err(|e| format!("Failed to build input stream: {}", e))?;

        // 2. Native Output Stream Callback (DAC Playback + DSP Pipeline)
        let pipeline_arc = Arc::clone(&self.pipeline);
        let reader_for_out = Arc::clone(&reader_arc);
        let out_stream = out_dev
            .build_output_stream(
                &config,
                move |data: &mut [f32], _: &_| {
                    let n_frames = data.len() / 2;
                    let mut scratch = vec![[0.0f32, 0.0f32]; n_frames];

                    if let Ok(mut r) = reader_for_out.lock() {
                        r.read(&mut scratch);
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

        in_stream.play().map_err(|e| format!("Failed to play input stream: {}", e))?;
        out_stream.play().map_err(|e| format!("Failed to play output stream: {}", e))?;

        self.input_stream = Some(in_stream);
        self.output_stream = Some(out_stream);
        self.is_running.store(true, Ordering::SeqCst);

        Ok(())
    }

    /// Stop audio stream cleanly.
    pub fn stop(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        self.input_stream = None;
        self.output_stream = None;
        self.reader_handle = None;
    }
}
