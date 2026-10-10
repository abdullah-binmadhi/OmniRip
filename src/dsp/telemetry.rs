//! Real-time Mastering Telemetry and ITU-R BS.1770 / EBU R128 Loudness Metering.

use super::biquad::{BiquadFilter, BiquadFilterType, FastSosFilter};
use rustfft::{num_complex::Complex, FftPlanner};
use std::sync::Arc;

#[derive(Clone)]
pub struct TelemetryEngine {
    pub peak_left_db: f32,
    pub peak_right_db: f32,
    pub phase_correlation: f32,
    pub lufs_momentary: f32,
    pub lufs_short_term: f32,
    pub crest_factor_db: f32,
    pub spectrum_32: [f32; 32],

    #[allow(dead_code)]
    sample_rate: f32,
    k_filter: FastSosFilter,
    accum_frames: usize,
    fft_planner: Arc<dyn rustfft::Fft<f32>>,
    fft_buffer: Vec<Complex<f32>>,
    hanning_window: Vec<f32>,
    lufs_m_history: Vec<f32>,
    #[allow(dead_code)]
    lufs_s_history: Vec<f32>,
}

impl std::fmt::Debug for TelemetryEngine {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TelemetryEngine")
            .field("peak_left_db", &self.peak_left_db)
            .field("peak_right_db", &self.peak_right_db)
            .field("phase_correlation", &self.phase_correlation)
            .field("lufs_momentary", &self.lufs_momentary)
            .field("lufs_short_term", &self.lufs_short_term)
            .field("crest_factor_db", &self.crest_factor_db)
            .finish()
    }
}

impl TelemetryEngine {
    pub fn new(sample_rate: f32) -> Self {
        // ITU-R BS.1770 K-weighting filter cascade
        // Stage 1: High shelf +4dB at 1500 Hz
        // Stage 2: High pass (RLB) at 100 Hz
        let mut k_filter = FastSosFilter::new();
        let k_coeffs = vec![
            BiquadFilter::new(BiquadFilterType::HighShelf, 1500.0, 4.0, 0.707, sample_rate),
            BiquadFilter::new(BiquadFilterType::HighPass, 100.0, 0.0, 0.707, sample_rate),
        ];
        k_filter.update_filters(&k_coeffs);

        let mut planner = FftPlanner::new();
        let fft = planner.plan_fft_forward(512);

        let hanning: Vec<f32> = (0..512)
            .map(|i| 0.5 * (1.0 - (2.0 * std::f32::consts::PI * i as f32 / 512.0).cos()))
            .collect();

        Self {
            peak_left_db: -96.0,
            peak_right_db: -96.0,
            phase_correlation: 1.0,
            lufs_momentary: -96.0,
            lufs_short_term: -96.0,
            crest_factor_db: 0.0,
            spectrum_32: [0.0; 32],
            sample_rate,
            k_filter,
            accum_frames: 0,
            fft_planner: fft,
            fft_buffer: vec![Complex::new(0.0, 0.0); 512],
            hanning_window: hanning,
            lufs_m_history: Vec::with_capacity(64),
            lufs_s_history: Vec::with_capacity(256),
        }
    }

    /// Analyze an audio buffer and update telemetry metrics (~25-40 Hz throttling).
    #[inline]
    pub fn update(&mut self, buffer: &[[f32; 2]]) {
        if buffer.is_empty() {
            return;
        }

        // 1. Peak levels in dBFS
        let mut max_l = 0.0f32;
        let mut max_r = 0.0f32;
        let mut sum_dot = 0.0f32;
        let mut sum_l_sq = 0.0f32;
        let mut sum_r_sq = 0.0f32;

        for frame in buffer.iter() {
            let l = frame[0];
            let r = frame[1];
            let abs_l = l.abs();
            let abs_r = r.abs();
            if abs_l > max_l {
                max_l = abs_l;
            }
            if abs_r > max_r {
                max_r = abs_r;
            }
            sum_dot += l * r;
            sum_l_sq += l * l;
            sum_r_sq += r * r;
        }

        self.peak_left_db = if max_l > 1e-5 {
            20.0 * max_l.log10()
        } else {
            -96.0
        };
        self.peak_right_db = if max_r > 1e-5 {
            20.0 * max_r.log10()
        } else {
            -96.0
        };

        // 2. Normalized Phase Correlation
        let denom = (sum_l_sq * sum_r_sq).sqrt();
        if denom > 1e-8 {
            self.phase_correlation = (sum_dot / denom).clamp(-1.0, 1.0);
        } else {
            self.phase_correlation = 1.0;
        }

        // Throttling for heavy telemetry: every ~1024 frames (~47 Hz at 48kHz)
        self.accum_frames += buffer.len();
        if self.accum_frames >= 1024 {
            self.accum_frames = 0;

            // 3. EBU R128 LUFS via K-weighting
            let mut k_buf = buffer.to_vec();
            self.k_filter.process(&mut k_buf);

            let mut k_energy = 0.0f32;
            for frame in k_buf.iter() {
                // ITU-R BS.1770 stereo channel weights: 1.0 for L and R
                k_energy += frame[0] * frame[0] + frame[1] * frame[1];
            }
            let mean_sq = k_energy / (k_buf.len() as f32 * 2.0);
            let lufs = if mean_sq > 1e-10 {
                -0.691 + 10.0 * mean_sq.log10()
            } else {
                -96.0
            };

            self.lufs_momentary = lufs;
            self.lufs_m_history.push(lufs);
            if self.lufs_m_history.len() > 16 {
                self.lufs_m_history.remove(0);
            }
            self.lufs_short_term = self.lufs_m_history.iter().sum::<f32>() / self.lufs_m_history.len() as f32;

            // 4. Crest Factor: Peak dBFS - RMS dBFS
            let rms = ((sum_l_sq + sum_r_sq) / (buffer.len() as f32 * 2.0)).sqrt();
            let peak = max_l.max(max_r);
            if rms > 1e-5 && peak > 1e-5 {
                self.crest_factor_db = (20.0 * (peak / rms).log10()).clamp(0.0, 30.0);
            } else {
                self.crest_factor_db = 0.0;
            }

            // 5. 32-Band FFT Live Spectrum
            let n_fft = 512.min(buffer.len());
            for i in 0..n_fft {
                let mono = (buffer[i][0] + buffer[i][1]) * 0.5 * self.hanning_window[i];
                self.fft_buffer[i] = Complex::new(mono, 0.0);
            }
            for i in n_fft..512 {
                self.fft_buffer[i] = Complex::new(0.0, 0.0);
            }

            self.fft_planner.process(&mut self.fft_buffer);

            // Group 256 positive bins into 32 logarithmic bands
            for b in 0..32 {
                let start_bin = (b * 8).min(255);
                let end_bin = ((b + 1) * 8).min(256);
                let mut sum_mag = 0.0f32;
                for k in start_bin..end_bin {
                    let mag = (self.fft_buffer[k].norm() / 256.0).max(1e-5);
                    sum_mag += mag;
                }
                let avg_mag = sum_mag / (end_bin - start_bin) as f32;
                let db = 20.0 * avg_mag.log10();
                // Map [-60dB, 0dB] to [0.0, 1.0]
                self.spectrum_32[b] = ((db + 60.0) / 60.0).clamp(0.0, 1.0);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_telemetry_peak_and_phase() {
        let mut telemetry = TelemetryEngine::new(48000.0);
        let n_samples = 1024;
        let mut sine_stereo = Vec::with_capacity(n_samples);
        for i in 0..n_samples {
            let t = i as f32 / 48000.0;
            let s = 0.707 * (2.0 * std::f32::consts::PI * 1000.0 * t).sin();
            sine_stereo.push([s, s]);
        }

        telemetry.update(&sine_stereo);

        assert!((telemetry.peak_left_db - (-3.0)).abs() < 0.5);
        assert!((telemetry.phase_correlation - 1.0).abs() < 1e-3);
        assert!(telemetry.lufs_momentary > -10.0);
    }
}
