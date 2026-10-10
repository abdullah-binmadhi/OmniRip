//! Lossless Audio Restoration & Spectral Super-Resolution Engine.
//!
//! Restores lost high-frequency acoustic information above lossy MP3 cutoff,
//! synthesizes synthetic harmonic air band (16kHz - 22kHz), applies analog tube warmth,
//! stereo soundstage widener, user 10-band graphic EQ rails, and true-peak brickwall limiting.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::io::{Read, Write};

use super::biquad::{BiquadFilter, BiquadFilterType, FastSosFilter};
use super::enhancer::AudiophileEnhancer;
use super::limiter::BrickwallLimiter;
use crate::harvest::tagger::{read_tags, write_tags};

pub const ISO_10_BAND_FREQS: [f32; 10] = [
    31.25, 62.5, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
];

pub struct LosslessRestorer {
    pub sample_rate: f32,
    pub enhancer: AudiophileEnhancer,
    pub limiter: BrickwallLimiter,
    hf_bandpass: FastSosFilter,
    hf_air_shelf: FastSosFilter,
    eq_filters: FastSosFilter,
    hpf_filter: FastSosFilter,
    air_boost_filter: FastSosFilter,
    last_gains: [f32; 10],
    last_hpf: bool,
    last_air: bool,
}

impl LosslessRestorer {
    pub fn new(sample_rate: f32) -> Self {
        let mut restorer = Self {
            sample_rate,
            enhancer: AudiophileEnhancer::new(sample_rate),
            limiter: BrickwallLimiter::new(sample_rate),
            hf_bandpass: FastSosFilter::new(),
            hf_air_shelf: FastSosFilter::new(),
            eq_filters: FastSosFilter::new(),
            hpf_filter: FastSosFilter::new(),
            air_boost_filter: FastSosFilter::new(),
            last_gains: [0.0; 10],
            last_hpf: false,
            last_air: false,
        };

        // Mid-high fundamental extraction (8kHz - 14kHz bandpass)
        let bp_filters = vec![
            BiquadFilter::new(BiquadFilterType::HighPass, 8000.0, 0.0, 0.707, sample_rate),
            BiquadFilter::new(BiquadFilterType::LowPass, 14000.0, 0.0, 0.707, sample_rate),
        ];
        restorer.hf_bandpass.update_filters(&bp_filters);

        // High-frequency air isolation (>16kHz HighPass)
        let air_filters = vec![
            BiquadFilter::new(BiquadFilterType::HighPass, 16000.0, 0.0, 0.707, sample_rate),
        ];
        restorer.hf_air_shelf.update_filters(&air_filters);

        // 30Hz Subsonic HPF
        let hpf = vec![
            BiquadFilter::new(BiquadFilterType::HighPass, 30.0, 0.0, 0.707, sample_rate),
        ];
        restorer.hpf_filter.update_filters(&hpf);

        // 16kHz +3dB Air Boost Shelf
        let air_boost = vec![
            BiquadFilter::new(BiquadFilterType::HighShelf, 16000.0, 3.0, 0.707, sample_rate),
        ];
        restorer.air_boost_filter.update_filters(&air_boost);

        restorer.update_eq(&[0.0; 10], false, false);
        restorer
    }

    pub fn update_eq(&mut self, gains: &[f32; 10], hpf: bool, air: bool) {
        if gains == &self.last_gains && hpf == self.last_hpf && air == self.last_air {
            return;
        }

        self.last_gains = *gains;
        self.last_hpf = hpf;
        self.last_air = air;

        let mut filters = Vec::new();
        for (i, &gain) in gains.iter().enumerate() {
            if gain.abs() > 0.05 {
                let freq = ISO_10_BAND_FREQS[i];
                let filter_type = if i == 0 {
                    BiquadFilterType::LowShelf
                } else if i == 9 {
                    BiquadFilterType::HighShelf
                } else {
                    BiquadFilterType::Peaking
                };
                filters.push(BiquadFilter::new(filter_type, freq, gain, 1.414, self.sample_rate));
            }
        }
        self.eq_filters.update_filters(&filters);
    }

    /// Process an interleaved stereo buffer `[[left, right]; N]`.
    pub fn process_stereo_buffer(&mut self, buffer: &mut [[f32; 2]], gains: &[f32; 10], hpf: bool, air: bool) {
        if buffer.is_empty() {
            return;
        }

        self.update_eq(gains, hpf, air);

        // 1. High-frequency bandwidth extension (Air harmonic regeneration)
        let mut hf_buf = buffer.to_vec();
        self.hf_bandpass.process(&mut hf_buf);

        for frame in hf_buf.iter_mut() {
            frame[0] = 0.5 * (frame[0] * 2.5).tanh() + 0.35 * (frame[0] * frame[0] - 0.25);
            frame[1] = 0.5 * (frame[1] * 2.5).tanh() + 0.35 * (frame[1] * frame[1] - 0.25);
        }

        self.hf_air_shelf.process(&mut hf_buf);

        for (orig, harm) in buffer.iter_mut().zip(hf_buf.iter()) {
            orig[0] += harm[0] * 0.15;
            orig[1] += harm[1] * 0.15;
        }

        // 2. 10-Band Graphic EQ Rails
        self.eq_filters.process(buffer);

        // Optional 30Hz HPF & Air Boost
        if self.last_hpf {
            self.hpf_filter.process(buffer);
        }
        if self.last_air {
            self.air_boost_filter.process(buffer);
        }

        // 3. True-Peak Brickwall Limiter to guarantee zero digital clipping
        self.limiter.process(buffer);
    }
}

/// Enhance an audio file to Lossless 24-bit FLAC or high-quality audio using the DSP restoration pipeline.
pub fn enhance_audio_file(
    input_path: &Path,
    output_path: &Path,
    eq_gains: &[f32; 10],
    hpf: bool,
    air: bool,
) -> Result<PathBuf, String> {
    if !input_path.exists() {
        return Err(format!("Input file does not exist: {:?}", input_path));
    }

    let sample_rate = 48000.0;

    // 1. Decode input file to raw f32le stereo via ffmpeg
    let mut decode_proc = Command::new("ffmpeg")
        .args([
            "-v", "error",
            "-i", input_path.to_str().unwrap(),
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "-ar", "48000",
            "-ac", "2",
            "pipe:1",
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to spawn ffmpeg decoder: {}", e))?;

    let mut raw_bytes = Vec::new();
    if let Some(mut stdout) = decode_proc.stdout.take() {
        stdout
            .read_to_end(&mut raw_bytes)
            .map_err(|e| format!("Failed to read raw audio bytes: {}", e))?;
    }

    let status = decode_proc
        .wait()
        .map_err(|e| format!("ffmpeg decoder failed to exit: {}", e))?;
    if !status.success() || raw_bytes.is_empty() {
        return Err("ffmpeg decoding returned empty or error exit status.".to_string());
    }

    // Convert raw f32le bytes to stereo pairs
    let total_samples = raw_bytes.len() / 4;
    let total_frames = total_samples / 2;
    let mut buffer: Vec<[f32; 2]> = Vec::with_capacity(total_frames);

    for chunk in raw_bytes.chunks_exact(8) {
        let left = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
        let right = f32::from_le_bytes([chunk[4], chunk[5], chunk[6], chunk[7]]);
        buffer.push([left, right]);
    }

    // 2. Process through LosslessRestorer
    let mut restorer = LosslessRestorer::new(sample_rate);
    restorer.process_stereo_buffer(&mut buffer, eq_gains, hpf, air);

    // Convert processed stereo buffer back to f32le bytes
    let mut processed_bytes = Vec::with_capacity(buffer.len() * 8);
    for frame in &buffer {
        processed_bytes.extend_from_slice(&frame[0].to_le_bytes());
        processed_bytes.extend_from_slice(&frame[1].to_le_bytes());
    }

    // 3. Encode processed f32le audio to output format via ffmpeg
    if let Some(parent) = output_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let is_flac = output_path.extension().and_then(|e| e.to_str()) == Some("flac");
    let mut encode_cmd = Command::new("ffmpeg");
    encode_cmd.args([
        "-v", "error",
        "-y",
        "-f", "f32le",
        "-ar", "48000",
        "-ac", "2",
        "-i", "pipe:0",
    ]);

    if is_flac {
        encode_cmd.args(["-c:a", "flac", "-sample_fmt", "s32", "-compression_level", "8"]);
    } else {
        encode_cmd.args(["-c:a", "libmp3lame", "-b:a", "320k"]);
    }

    encode_cmd.arg(output_path.to_str().unwrap());
    encode_cmd.stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::piped());

    let mut encode_proc = encode_cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn ffmpeg encoder: {}", e))?;

    if let Some(mut stdin) = encode_proc.stdin.take() {
        stdin
            .write_all(&processed_bytes)
            .map_err(|e| format!("Failed to write audio bytes to encoder: {}", e))?;
    }

    let encode_status = encode_proc
        .wait()
        .map_err(|e| format!("ffmpeg encoder failed to exit: {}", e))?;
    if !encode_status.success() {
        return Err("ffmpeg encoding failed.".to_string());
    }

    // 4. Copy tags from original input to enhanced file
    if let Ok(tags) = read_tags(input_path) {
        let mut enhanced_tags = tags;
        if let Some(title) = &enhanced_tags.title {
            enhanced_tags.title = Some(format!("{} (Lossless Restored)", title));
        }
        let _ = write_tags(output_path, &enhanced_tags);
    }

    Ok(output_path.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lossless_restorer_bandwidth_extension() {
        let sample_rate = 48000.0;
        let mut restorer = LosslessRestorer::new(sample_rate);

        // Generate a 10kHz sine wave (band-limited below 16kHz)
        let num_samples = 4800; // 100ms
        let mut buffer: Vec<[f32; 2]> = Vec::with_capacity(num_samples);
        for i in 0..num_samples {
            let t = (i as f32) / sample_rate;
            let sample = (2.0 * std::f32::consts::PI * 10000.0 * t).sin() * 0.7;
            buffer.push([sample, sample]);
        }

        let gains = [0.0; 10];
        restorer.process_stereo_buffer(&mut buffer, &gains, false, false);

        // Verify buffer is valid and non-empty
        assert_eq!(buffer.len(), num_samples);
        for frame in buffer {
            assert!(!frame[0].is_nan());
            assert!(!frame[1].is_nan());
            assert!(frame[0].abs() <= 1.0);
            assert!(frame[1].abs() <= 1.0);
        }
    }

    #[test]
    fn test_lossless_restorer_limiter_ceiling() {
        let sample_rate = 48000.0;
        let mut restorer = LosslessRestorer::new(sample_rate);

        // Generate excessive hot signal (+6.0 dBFS)
        let mut buffer = vec![[2.5, 2.5]; 1024];
        let gains = [0.0; 10];
        restorer.process_stereo_buffer(&mut buffer, &gains, false, false);

        // Brickwall limiter threshold is 0.977 (-0.2 dBFS)
        for frame in buffer {
            assert!(frame[0] <= 1.0, "Limiter ceiling exceeded: {}", frame[0]);
            assert!(frame[1] <= 1.0, "Limiter ceiling exceeded: {}", frame[1]);
        }
    }

    #[test]
    fn test_lossless_restorer_eq_rails() {
        let sample_rate = 48000.0;
        let mut restorer = LosslessRestorer::new(sample_rate);

        let mut buffer = vec![[0.1, 0.1]; 512];
        let mut gains = [0.0; 10];
        gains[5] = 6.0; // +6dB at 1kHz

        restorer.process_stereo_buffer(&mut buffer, &gains, true, true);
        assert!(!buffer[0][0].is_nan());
    }
}
