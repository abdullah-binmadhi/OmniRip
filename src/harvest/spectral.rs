//! Pure Rust Spectral Cutoff & Fake Lossless Analyzer.
//! Decodes audio streams using Symphonia and analyzes frequency distribution using RustFFT.

use rustfft::num_complex::Complex;
use rustfft::FftPlanner;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Cursor;
use std::path::Path;
use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::DecoderOptions;
use symphonia::core::errors::Error;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum QualityVerdict {
    TrueLosslessHiRes,
    TrueLosslessCD,
    NearLossless320k,
    LossyCutoff(u32),
    FakeLossless(u32),
}

impl QualityVerdict {
    pub fn description(&self) -> String {
        match self {
            QualityVerdict::TrueLosslessHiRes => {
                "TRUE LOSSLESS (Hi-Res Audio: Energy extends beyond 22 kHz)".to_string()
            }
            QualityVerdict::TrueLosslessCD => {
                "TRUE LOSSLESS (Standard CD: Full bandwidth up to ~21 kHz)".to_string()
            }
            QualityVerdict::NearLossless320k => {
                "NEAR-LOSSLESS (High-Bitrate MP3/AAC: Sharp brickwall ~20 kHz)".to_string()
            }
            QualityVerdict::LossyCutoff(hz) => {
                format!("COMPRESSED LOSSY (Cutoff at ~{} Hz, ~128-192 kbps quality)", hz)
            }
            QualityVerdict::FakeLossless(hz) => {
                format!("FAKE LOSSLESS DETECTED (Lossless container with lossy ~{} Hz cutoff)", hz)
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpectralAnalysisResult {
    pub sample_rate: u32,
    pub cutoff_freq_hz: f32,
    pub dynamic_range_db: f32,
    pub verdict: QualityVerdict,
}

/// Analyzes raw PCM floating point samples to determine high-frequency cutoff.
pub fn analyze_samples(samples: &[f32], sample_rate: u32, is_lossless_container: bool) -> SpectralAnalysisResult {
    const FFT_SIZE: usize = 2048;
    if samples.len() < FFT_SIZE {
        return SpectralAnalysisResult {
            sample_rate,
            cutoff_freq_hz: 0.0,
            dynamic_range_db: 0.0,
            verdict: QualityVerdict::LossyCutoff(0),
        };
    }

    let mut planner = FftPlanner::<f32>::new();
    let fft = planner.plan_fft_forward(FFT_SIZE);

    let num_bins = FFT_SIZE / 2;
    let mut power_accum = vec![0.0f32; num_bins];
    let mut frame_count = 0;

    let step = FFT_SIZE / 2; // 50% overlap
    let mut offset = 0;

    let mut buffer = vec![Complex::new(0.0, 0.0); FFT_SIZE];

    while offset + FFT_SIZE <= samples.len() && frame_count < 200 {
        // Apply Hanning window
        for i in 0..FFT_SIZE {
            let window = 0.5 * (1.0 - (2.0 * std::f32::consts::PI * i as f32 / FFT_SIZE as f32).cos());
            buffer[i] = Complex::new(samples[offset + i] * window, 0.0);
        }

        fft.process(&mut buffer);

        for (b, p) in power_accum.iter_mut().enumerate() {
            let mag = buffer[b].norm_sqr();
            *p += mag;
        }

        frame_count += 1;
        offset += step;
    }

    if frame_count == 0 {
        return SpectralAnalysisResult {
            sample_rate,
            cutoff_freq_hz: 0.0,
            dynamic_range_db: 0.0,
            verdict: QualityVerdict::LossyCutoff(0),
        };
    }

    // Convert accumulated power to dB relative to peak
    let mut max_power = 1e-12f32;
    for &p in &power_accum {
        if p > max_power {
            max_power = p;
        }
    }

    let bin_hz = sample_rate as f32 / FFT_SIZE as f32;
    let mut power_db = vec![0.0f32; num_bins];
    for (i, &p) in power_accum.iter().enumerate() {
        let normalized = (p / (frame_count as f32 * max_power)).max(1e-9);
        power_db[i] = 10.0 * normalized.log10();
    }

    // Threshold for spectral cutoff: -55 dB below peak energy
    let threshold_db = -55.0;
    let mut cutoff_bin = 0;

    for (i, &db) in power_db.iter().enumerate().rev() {
        let freq = i as f32 * bin_hz;
        if freq < 10000.0 {
            cutoff_bin = i;
            break;
        }
        if db >= threshold_db {
            cutoff_bin = i;
            break;
        }
    }

    let cutoff_hz = cutoff_bin as f32 * bin_hz;
    let min_db = power_db.iter().cloned().fold(0.0f32, f32::min);
    let dynamic_range_db = -min_db;

    let verdict = if cutoff_hz >= 22500.0 {
        QualityVerdict::TrueLosslessHiRes
    } else if cutoff_hz >= 20200.0 {
        QualityVerdict::TrueLosslessCD
    } else if cutoff_hz >= 19500.0 {
        QualityVerdict::NearLossless320k
    } else if is_lossless_container {
        QualityVerdict::FakeLossless(cutoff_hz as u32)
    } else {
        QualityVerdict::LossyCutoff(cutoff_hz as u32)
    };

    SpectralAnalysisResult {
        sample_rate,
        cutoff_freq_hz: cutoff_hz,
        dynamic_range_db,
        verdict,
    }
}

/// Analyzes an audio stream provided via MediaSourceStream.
pub fn analyze_media_source(mss: MediaSourceStream, hint: &Hint, is_lossless: bool) -> Result<SpectralAnalysisResult, String> {
    let probed = symphonia::default::get_probe()
        .format(hint, mss, &FormatOptions::default(), &MetadataOptions::default())
        .map_err(|e| format!("Unsupported container format: {}", e))?;

    let mut format = probed.format;
    let track = format
        .tracks()
        .iter()
        .find(|t| t.codec_params.codec != symphonia::core::codecs::CODEC_TYPE_NULL)
        .ok_or_else(|| "No supported audio tracks found".to_string())?;

    let track_id = track.id;
    let sample_rate = track.codec_params.sample_rate.unwrap_or(44100);

    let mut decoder = symphonia::default::get_codecs()
        .make(&track.codec_params, &DecoderOptions::default())
        .map_err(|e| format!("Unsupported codec: {}", e))?;

    let mut samples: Vec<f32> = Vec::with_capacity(sample_rate as usize * 15); // Max 15 seconds analysis
    let max_samples = sample_rate as usize * 15;

    while samples.len() < max_samples {
        let packet = match format.next_packet() {
            Ok(p) => p,
            Err(Error::IoError(ref e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
            Err(Error::ResetRequired) => continue,
            Err(e) => return Err(format!("Stream error: {}", e)),
        };

        if packet.track_id() != track_id {
            continue;
        }

        let decoded = match decoder.decode(&packet) {
            Ok(d) => d,
            Err(Error::DecodeError(_)) => continue,
            Err(e) => return Err(format!("Decode failure: {}", e)),
        };

        let channel_count = decoded.spec().channels.count();
        let mut sample_buf = SampleBuffer::<f32>::new(decoded.capacity() as u64, *decoded.spec());
        sample_buf.copy_interleaved_ref(decoded);

        // Downmix to mono for FFT analysis
        let frame_samples = sample_buf.samples();
        for chunk in frame_samples.chunks(channel_count) {
            let mono: f32 = chunk.iter().sum::<f32>() / channel_count as f32;
            samples.push(mono);
            if samples.len() >= max_samples {
                break;
            }
        }
    }

    Ok(analyze_samples(&samples, sample_rate, is_lossless))
}

/// Decodes audio file at `path` and performs spectral analysis.
pub fn analyze_file<P: AsRef<Path>>(path: P) -> Result<SpectralAnalysisResult, String> {
    let path_ref = path.as_ref();
    let file = File::open(path_ref).map_err(|e| format!("Cannot open file: {}", e))?;
    let mss = MediaSourceStream::new(Box::new(file), Default::default());

    let mut hint = Hint::new();
    if let Some(ext) = path_ref.extension().and_then(|e| e.to_str()) {
        hint.with_extension(ext);
    }

    let is_lossless = match path_ref.extension().and_then(|e| e.to_str()).map(|s| s.to_lowercase()) {
        Some(ref ext) if ext == "flac" || ext == "wav" || ext == "aiff" || ext == "alac" => true,
        _ => false,
    };

    analyze_media_source(mss, &hint, is_lossless)
}

/// Decodes an in-memory chunk of audio bytes (e.g. from pre-flight probe) and performs spectral analysis.
pub fn analyze_bytes(bytes: &[u8], extension: &str) -> Result<SpectralAnalysisResult, String> {
    let cursor = Cursor::new(bytes.to_vec());
    let mss = MediaSourceStream::new(Box::new(cursor), Default::default());

    let mut hint = Hint::new();
    hint.with_extension(extension);

    let is_lossless = matches!(
        extension.to_lowercase().as_str(),
        "flac" | "wav" | "aiff" | "aif" | "alac"
    );

    analyze_media_source(mss, &hint, is_lossless)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_analyze_samples_lossless_high_freq() {
        let sample_rate = 48000;
        let mut samples = Vec::new();
        // Generate mix of 1 kHz tone and 21 kHz tone (typical CD / high-res content)
        for i in 0..(sample_rate * 2) {
            let t = i as f32 / sample_rate as f32;
            let s = 0.5 * (2.0 * std::f32::consts::PI * 1000.0 * t).sin()
                  + 0.3 * (2.0 * std::f32::consts::PI * 21000.0 * t).sin();
            samples.push(s);
        }

        let result = analyze_samples(&samples, sample_rate, true);
        assert!(result.cutoff_freq_hz >= 20000.0);
        assert!(matches!(result.verdict, QualityVerdict::TrueLosslessCD | QualityVerdict::TrueLosslessHiRes));
    }

    #[test]
    fn test_analyze_samples_fake_lossless() {
        let sample_rate = 44100;
        let mut samples = Vec::new();
        // Generate content only up to 15 kHz (typical 128kbps MP3 cut)
        for i in 0..(sample_rate * 2) {
            let t = i as f32 / sample_rate as f32;
            let s = 0.8 * (2.0 * std::f32::consts::PI * 14000.0 * t).sin();
            samples.push(s);
        }

        let result = analyze_samples(&samples, sample_rate, true); // container is lossless
        assert!(result.cutoff_freq_hz < 18000.0);
        assert!(matches!(result.verdict, QualityVerdict::FakeLossless(_)));
    }
}
