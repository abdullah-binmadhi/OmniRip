//! Cascaded Second-Order Sections (SOS) Biquad Filtering Engine in pure Rust.
//!
//! Implements Transposed Direct Form II filtering with a dual-engine clickless crossfader
//! to eliminate zipper noise and transient pops during filter parameter changes.

use std::f32::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BiquadFilterType {
    Peaking,
    LowShelf,
    HighShelf,
    LowPass,
    HighPass,
    Notch,
    BandPass,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BiquadCoefficients {
    pub b0: f32,
    pub b1: f32,
    pub b2: f32,
    pub a1: f32,
    pub a2: f32,
}

impl Default for BiquadCoefficients {
    fn default() -> Self {
        Self {
            b0: 1.0,
            b1: 0.0,
            b2: 0.0,
            a1: 0.0,
            a2: 0.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct BiquadFilter {
    pub filter_type: BiquadFilterType,
    pub frequency: f32,
    pub gain_db: f32,
    pub q: f32,
    pub sample_rate: f32,
    pub enabled: bool,
}

impl BiquadFilter {
    pub fn new(
        filter_type: BiquadFilterType,
        frequency: f32,
        gain_db: f32,
        q: f32,
        sample_rate: f32,
    ) -> Self {
        Self {
            filter_type,
            frequency,
            gain_db,
            q: if q <= 0.0 { 0.707 } else { q },
            sample_rate,
            enabled: true,
        }
    }

    /// Compute Robert Bristow-Johnson Audio EQ Cookbook coefficients.
    pub fn compute_coefficients(&self) -> BiquadCoefficients {
        let nyquist = self.sample_rate / 2.0;
        let clamped_freq = self.frequency.clamp(10.0, nyquist - 100.0);
        let w0 = 2.0 * PI * clamped_freq / self.sample_rate;
        let cos_w0 = w0.cos();
        let sin_w0 = w0.sin();
        let alpha = sin_w0 / (2.0 * self.q.max(0.01));
        let a = 10.0f32.powf(self.gain_db / 40.0); // sqrt(10^(gain/20))

        let (b0, b1, b2, a0, a1, a2) = match self.filter_type {
            BiquadFilterType::Peaking => {
                let b0 = 1.0 + alpha * a;
                let b1 = -2.0 * cos_w0;
                let b2 = 1.0 - alpha * a;
                let a0 = 1.0 + alpha / a;
                let a1 = -2.0 * cos_w0;
                let a2 = 1.0 - alpha / a;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::LowShelf => {
                let two_sqrt_a_alpha = 2.0 * a.sqrt() * alpha;
                let a_plus_1 = a + 1.0;
                let a_minus_1 = a - 1.0;
                let b0 = a * (a_plus_1 - a_minus_1 * cos_w0 + two_sqrt_a_alpha);
                let b1 = 2.0 * a * (a_minus_1 - a_plus_1 * cos_w0);
                let b2 = a * (a_plus_1 - a_minus_1 * cos_w0 - two_sqrt_a_alpha);
                let a0 = a_plus_1 + a_minus_1 * cos_w0 + two_sqrt_a_alpha;
                let a1 = -2.0 * (a_minus_1 + a_plus_1 * cos_w0);
                let a2 = a_plus_1 + a_minus_1 * cos_w0 - two_sqrt_a_alpha;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::HighShelf => {
                let two_sqrt_a_alpha = 2.0 * a.sqrt() * alpha;
                let a_plus_1 = a + 1.0;
                let a_minus_1 = a - 1.0;
                let b0 = a * (a_plus_1 + a_minus_1 * cos_w0 + two_sqrt_a_alpha);
                let b1 = -2.0 * a * (a_minus_1 + a_plus_1 * cos_w0);
                let b2 = a * (a_plus_1 + a_minus_1 * cos_w0 - two_sqrt_a_alpha);
                let a0 = a_plus_1 - a_minus_1 * cos_w0 + two_sqrt_a_alpha;
                let a1 = 2.0 * (a_minus_1 - a_plus_1 * cos_w0);
                let a2 = a_plus_1 - a_minus_1 * cos_w0 - two_sqrt_a_alpha;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::LowPass => {
                let b0 = (1.0 - cos_w0) / 2.0;
                let b1 = 1.0 - cos_w0;
                let b2 = (1.0 - cos_w0) / 2.0;
                let a0 = 1.0 + alpha;
                let a1 = -2.0 * cos_w0;
                let a2 = 1.0 - alpha;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::HighPass => {
                let b0 = (1.0 + cos_w0) / 2.0;
                let b1 = -(1.0 + cos_w0);
                let b2 = (1.0 + cos_w0) / 2.0;
                let a0 = 1.0 + alpha;
                let a1 = -2.0 * cos_w0;
                let a2 = 1.0 - alpha;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::Notch => {
                let b0 = 1.0;
                let b1 = -2.0 * cos_w0;
                let b2 = 1.0;
                let a0 = 1.0 + alpha;
                let a1 = -2.0 * cos_w0;
                let a2 = 1.0 - alpha;
                (b0, b1, b2, a0, a1, a2)
            }
            BiquadFilterType::BandPass => {
                let b0 = alpha;
                let b1 = 0.0;
                let b2 = -alpha;
                let a0 = 1.0 + alpha;
                let a1 = -2.0 * cos_w0;
                let a2 = 1.0 - alpha;
                (b0, b1, b2, a0, a1, a2)
            }
        };

        let inv_a0 = 1.0 / a0;
        BiquadCoefficients {
            b0: b0 * inv_a0,
            b1: b1 * inv_a0,
            b2: b2 * inv_a0,
            a1: a1 * inv_a0,
            a2: a2 * inv_a0,
        }
    }

    /// Compute frequency response magnitude in dB at `freq` Hz.
    pub fn magnitude_db_at(&self, freq: f32) -> f32 {
        if !self.enabled {
            return 0.0;
        }
        let coeffs = self.compute_coefficients();
        let w = 2.0 * PI * freq / self.sample_rate;
        let phi = (w / 2.0).sin().powi(2);

        // |H(e^jw)|^2 using algebraic formulation
        let num = (coeffs.b0 + coeffs.b1 + coeffs.b2).powi(2)
            - 4.0 * (coeffs.b0 * coeffs.b1 + 4.0 * coeffs.b0 * coeffs.b2 + coeffs.b1 * coeffs.b2) * phi
            + 16.0 * coeffs.b0 * coeffs.b2 * phi * phi;
        let den = (1.0 + coeffs.a1 + coeffs.a2).powi(2)
            - 4.0 * (coeffs.a1 + 4.0 * coeffs.a2 + coeffs.a1 * coeffs.a2) * phi
            + 16.0 * coeffs.a2 * phi * phi;

        if den <= 1e-12 {
            return 0.0;
        }
        let mag_sq = (num / den).max(1e-12);
        10.0 * mag_sq.log10()
    }
}

/// Cascaded Second-Order Sections (SOS) with persistent Direct Form II Transposed states.
#[derive(Debug, Clone)]
pub struct FastSosFilter {
    pub sos: Vec<BiquadCoefficients>,
    // states[section][channel][state_index]
    pub states: Vec<[[f32; 2]; 2]>,
}

impl FastSosFilter {
    pub fn new() -> Self {
        Self {
            sos: Vec::new(),
            states: Vec::new(),
        }
    }

    pub fn update_filters(&mut self, filters: &[BiquadFilter]) {
        let active: Vec<_> = filters.iter().filter(|f| f.enabled).collect();
        let num_sections = active.len();
        self.sos = active.iter().map(|f| f.compute_coefficients()).collect();
        if self.states.len() != num_sections {
            self.states = vec![[[0.0; 2]; 2]; num_sections];
        }
    }

    /// Process a stereo block in-place using Transposed Direct Form II.
    #[inline]
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if self.sos.is_empty() {
            return;
        }

        for (section_idx, coeffs) in self.sos.iter().enumerate() {
            let state = &mut self.states[section_idx];
            let b0 = coeffs.b0;
            let b1 = coeffs.b1;
            let b2 = coeffs.b2;
            let a1 = coeffs.a1;
            let a2 = coeffs.a2;

            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let x = frame[ch];
                    let s = &mut state[ch];
                    let y = b0 * x + s[0];
                    s[0] = b1 * x - a1 * y + s[1];
                    s[1] = b2 * x - a2 * y;
                    frame[ch] = y;
                }
            }
        }
    }
}

/// Dual-Engine Clickless Crossfader: smoothly ramps biquad filter coefficients across 20ms
/// while preserving filter state memory (Transposed Direct Form II) to eliminate clicks, pops, and zipper noise.
#[derive(Debug, Clone)]
pub struct DualEngineCrossfader {
    current_coeffs: Vec<BiquadCoefficients>,
    target_coeffs: Vec<BiquadCoefficients>,
    states: Vec<[[f32; 2]; 2]>,
    ramp_total: usize,
    ramp_remaining: usize,
}

impl DualEngineCrossfader {
    pub fn new() -> Self {
        Self {
            current_coeffs: Vec::new(),
            target_coeffs: Vec::new(),
            states: Vec::new(),
            ramp_total: 0,
            ramp_remaining: 0,
        }
    }

    pub fn update_filters(&mut self, filters: &[BiquadFilter], sample_rate: f32) {
        let active: Vec<_> = filters.iter().filter(|f| f.enabled).collect();
        let new_coeffs: Vec<_> = active.iter().map(|f| f.compute_coefficients()).collect();
        let num_sections = new_coeffs.len();

        if self.current_coeffs.len() == num_sections && !self.current_coeffs.is_empty() {
            self.target_coeffs = new_coeffs;
            let ramp = (sample_rate * 0.020) as usize; // 20 ms ramp
            self.ramp_total = ramp.max(128);
            self.ramp_remaining = self.ramp_total;
        } else {
            self.current_coeffs = new_coeffs.clone();
            self.target_coeffs = new_coeffs;
            self.states.resize(num_sections, [[0.0; 2]; 2]);
            self.ramp_total = 0;
            self.ramp_remaining = 0;
        }
    }

    #[inline]
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if self.current_coeffs.is_empty() || buffer.is_empty() {
            return;
        }

        let n_frames = buffer.len();
        let is_ramping = self.ramp_remaining > 0 && self.ramp_total > 0;

        for (idx, curr) in self.current_coeffs.iter_mut().enumerate() {
            let target = &self.target_coeffs[idx];
            let state = &mut self.states[idx];

            if is_ramping {
                let start_prog = 1.0 - (self.ramp_remaining as f32 / self.ramp_total as f32);
                let rem = self.ramp_remaining.saturating_sub(n_frames);
                let end_prog = 1.0 - (rem as f32 / self.ramp_total as f32);
                let step = if n_frames > 1 {
                    (end_prog - start_prog) / (n_frames - 1) as f32
                } else {
                    0.0
                };

                for (i, frame) in buffer.iter_mut().enumerate() {
                    let p = start_prog + step * i as f32;
                    let b0 = curr.b0 + p * (target.b0 - curr.b0);
                    let b1 = curr.b1 + p * (target.b1 - curr.b1);
                    let b2 = curr.b2 + p * (target.b2 - curr.b2);
                    let a1 = curr.a1 + p * (target.a1 - curr.a1);
                    let a2 = curr.a2 + p * (target.a2 - curr.a2);

                    for ch in 0..2 {
                        let x = frame[ch];
                        let s = &mut state[ch];
                        let y = b0 * x + s[0];
                        s[0] = b1 * x - a1 * y + s[1];
                        s[1] = b2 * x - a2 * y;
                        frame[ch] = y;
                    }
                }
            } else {
                let b0 = curr.b0;
                let b1 = curr.b1;
                let b2 = curr.b2;
                let a1 = curr.a1;
                let a2 = curr.a2;

                for frame in buffer.iter_mut() {
                    for ch in 0..2 {
                        let x = frame[ch];
                        let s = &mut state[ch];
                        let y = b0 * x + s[0];
                        s[0] = b1 * x - a1 * y + s[1];
                        s[1] = b2 * x - a2 * y;
                        frame[ch] = y;
                    }
                }
            }
        }

        if is_ramping {
            self.ramp_remaining = self.ramp_remaining.saturating_sub(n_frames);
            if self.ramp_remaining == 0 {
                self.current_coeffs = self.target_coeffs.clone();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_peaking_filter_boost() {
        let filter = BiquadFilter::new(BiquadFilterType::Peaking, 1000.0, 6.0, 1.414, 48000.0);
        let resp_1k = filter.magnitude_db_at(1000.0);
        assert!((resp_1k - 6.0).abs() < 0.1);

        let resp_100hz = filter.magnitude_db_at(100.0);
        assert!(resp_100hz.abs() < 0.5);
    }

    #[test]
    fn test_filter_stability_and_no_nans() {
        let mut filter = FastSosFilter::new();
        let filters = vec![
            BiquadFilter::new(BiquadFilterType::Peaking, 100.0, 3.0, 1.0, 48000.0),
            BiquadFilter::new(BiquadFilterType::HighShelf, 10000.0, -4.0, 0.707, 48000.0),
        ];
        filter.update_filters(&filters);

        let mut audio = vec![[0.5f32, 0.5f32]; 512];
        filter.process(&mut audio);

        for frame in audio {
            assert!(!frame[0].is_nan());
            assert!(!frame[1].is_nan());
            assert!(frame[0].abs() < 2.0);
        }
    }

    #[test]
    fn test_dual_engine_crossfade() {
        let mut crossfader = DualEngineCrossfader::new();
        let f1 = vec![BiquadFilter::new(BiquadFilterType::Peaking, 1000.0, 6.0, 1.0, 48000.0)];
        crossfader.update_filters(&f1, 48000.0);

        let mut audio = vec![[0.5f32, 0.5f32]; 256];
        crossfader.process(&mut audio);

        // Change filter to -6dB: crossfader should transition smoothly without clipping
        let f2 = vec![BiquadFilter::new(BiquadFilterType::Peaking, 1000.0, -6.0, 1.0, 48000.0)];
        crossfader.update_filters(&f2, 48000.0);

        crossfader.process(&mut audio);
        assert!(!audio[0][0].is_nan());
        assert!(audio[0][0].abs() < 1.0);
    }
}
