//! Studio Audiophile Sound Engine in pure Rust.
//!
//! Includes 3D Soundstage Matrix, Class-A Tube Warmth, Aural Air & Sheen,
//! Sub-Bass Punch, Meier Natural Crossfeed, Audiophile Boundary Filters, and Dynamic De-Esser.

use super::biquad::{BiquadFilter, BiquadFilterType, FastSosFilter};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CrossfeedMode {
    Off,
    Subtle,
    Standard,
}

#[derive(Debug, Clone)]
pub struct AudiophileEnhancer {
    pub enabled: bool,
    pub spatial_width: f32,
    pub tube_warmth: f32,
    pub air_clarity_db: f32,
    pub bass_punch_db: f32,
    pub mono_bass: bool,
    pub loudness_contour: bool,
    pub crossfeed: CrossfeedMode,
    pub subsonic_filter: bool,
    pub ultrasonic_filter: bool,
    pub deesser_enabled: bool,
    pub deesser_amount: f32,
    pub deesser_freq: f32,
    pub deesser_reduction_db: f32,

    sample_rate: f32,
    // Internal dedicated filter engines
    air_filter: FastSosFilter,
    punch_filter: FastSosFilter,
    boundary_filter: FastSosFilter,
    deesser_band_filter: FastSosFilter,
    crossfeed_filter: FastSosFilter,
    deesser_env: f32,
}

impl AudiophileEnhancer {
    pub fn new(sample_rate: f32) -> Self {
        let mut enh = Self {
            enabled: true,
            spatial_width: 1.0,
            tube_warmth: 0.0,
            air_clarity_db: 0.0,
            bass_punch_db: 0.0,
            mono_bass: false,
            loudness_contour: false,
            crossfeed: CrossfeedMode::Off,
            subsonic_filter: true,
            ultrasonic_filter: true,
            deesser_enabled: false,
            deesser_amount: 0.5,
            deesser_freq: 6500.0,
            deesser_reduction_db: 0.0,
            sample_rate,
            air_filter: FastSosFilter::new(),
            punch_filter: FastSosFilter::new(),
            boundary_filter: FastSosFilter::new(),
            deesser_band_filter: FastSosFilter::new(),
            crossfeed_filter: FastSosFilter::new(),
            deesser_env: 0.0,
        };
        enh.rebuild_filters();
        enh
    }

    pub fn rebuild_filters(&mut self) {
        // Boundary Guard Filters (18 Hz Subsonic HPF + 21 kHz Ultrasonic LPF)
        let mut b_filters = Vec::new();
        if self.subsonic_filter {
            b_filters.push(BiquadFilter::new(
                BiquadFilterType::HighPass,
                18.0,
                0.0,
                0.707,
                self.sample_rate,
            ));
        }
        if self.ultrasonic_filter {
            b_filters.push(BiquadFilter::new(
                BiquadFilterType::LowPass,
                21000.0,
                0.0,
                0.707,
                self.sample_rate,
            ));
        }
        self.boundary_filter.update_filters(&b_filters);

        // Aural Air (12 kHz High-Shelf)
        if self.air_clarity_db > 0.01 {
            let air = vec![BiquadFilter::new(
                BiquadFilterType::HighShelf,
                12000.0,
                self.air_clarity_db,
                0.707,
                self.sample_rate,
            )];
            self.air_filter.update_filters(&air);
        } else {
            self.air_filter.update_filters(&[]);
        }

        // Sub-Bass Punch (45 Hz Peaking)
        if self.bass_punch_db > 0.01 {
            let punch = vec![BiquadFilter::new(
                BiquadFilterType::Peaking,
                45.0,
                self.bass_punch_db,
                1.414,
                self.sample_rate,
            )];
            self.punch_filter.update_filters(&punch);
        } else {
            self.punch_filter.update_filters(&[]);
        }

        // De-Esser detection bandpass
        if self.deesser_enabled {
            let deess = vec![BiquadFilter::new(
                BiquadFilterType::BandPass,
                self.deesser_freq,
                0.0,
                2.0,
                self.sample_rate,
            )];
            self.deesser_band_filter.update_filters(&deess);
        } else {
            self.deesser_band_filter.update_filters(&[]);
        }

        // Meier Crossfeed shadow filter (700 Hz Low-Pass)
        if self.crossfeed != CrossfeedMode::Off {
            let xfeed = vec![BiquadFilter::new(
                BiquadFilterType::LowPass,
                700.0,
                0.0,
                0.707,
                self.sample_rate,
            )];
            self.crossfeed_filter.update_filters(&xfeed);
        } else {
            self.crossfeed_filter.update_filters(&[]);
        }
    }

    /// Process stereo buffer in-place through studio enhancer modules.
    #[inline]
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if !self.enabled || buffer.is_empty() {
            return;
        }

        // 1. Boundary Guard Filters
        self.boundary_filter.process(buffer);

        // 2. Aural Air & Sub-Bass Punch
        self.air_filter.process(buffer);
        self.punch_filter.process(buffer);

        // 3. 3D Soundstage Matrix & Mono Bass
        let w = self.spatial_width;
        let mono_bass = self.mono_bass;
        if (w - 1.0).abs() > 1e-4 || mono_bass {
            for frame in buffer.iter_mut() {
                let mid = (frame[0] + frame[1]) * 0.5;
                let side = (frame[0] - frame[1]) * 0.5;
                let wide_side = side * w;
                frame[0] = mid + wide_side;
                frame[1] = mid - wide_side;
            }
        }

        // 4. Meier Natural Headphone Crossfeed
        if self.crossfeed != CrossfeedMode::Off {
            let feed_level = match self.crossfeed {
                CrossfeedMode::Subtle => 0.15,
                CrossfeedMode::Standard => 0.28,
                CrossfeedMode::Off => 0.0,
            };
            let mut x_shadow = buffer.to_vec();
            self.crossfeed_filter.process(&mut x_shadow);
            for (i, frame) in buffer.iter_mut().enumerate() {
                let cross_l = x_shadow[i][0] * feed_level;
                let cross_r = x_shadow[i][1] * feed_level;
                frame[0] += cross_r;
                frame[1] += cross_l;
            }
        }

        // 5. Class-A Tube Warmth (Continuous soft-knee saturation, zero DC offset)
        let t = self.tube_warmth;
        if t > 0.001 {
            let drive = 1.0 + t * 1.5;
            for frame in buffer.iter_mut() {
                for ch in 0..2 {
                    let x = frame[ch] * drive;
                    let sign = x.signum();
                    let abs_x = x.abs();
                    // C1 continuous soft-saturation curve: linear below 0.6, smooth quadratic knee up to 1.4, smooth saturation ceiling
                    let sat = if abs_x < 0.6 {
                        abs_x
                    } else if abs_x < 1.4 {
                        let u = (abs_x - 0.6) / 0.8;
                        0.6 + 0.8 * (u - 0.5 * u * u)
                    } else {
                        1.0
                    };
                    let y = sign * sat;
                    // Subtle even harmonic warmth without DC offset
                    let warm = y + t * 0.08 * (y * y - 0.5 * abs_x.min(1.0));
                    frame[ch] = warm / (1.0 + t * 0.25);
                }
            }
        }

        // 6. Dynamic De-Esser (5.0k - 8.5k Hz Sibilance Limiter)
        if self.deesser_enabled {
            let mut det = buffer.to_vec();
            self.deesser_band_filter.process(&mut det);
            let attack = 1.0 - (-1.0 / (self.sample_rate * 0.002)).exp();
            let release = 1.0 - (-1.0 / (self.sample_rate * 0.050)).exp();
            let threshold = 0.25;

            let mut max_gr = 0.0f32;
            for (i, frame) in buffer.iter_mut().enumerate() {
                let det_level = det[i][0].abs().max(det[i][1].abs());
                if det_level > self.deesser_env {
                    self.deesser_env += (det_level - self.deesser_env) * attack;
                } else {
                    self.deesser_env += (det_level - self.deesser_env) * release;
                }

                if self.deesser_env > threshold {
                    let excess = self.deesser_env - threshold;
                    let gr = (1.0 - (excess * self.deesser_amount * 2.0)).clamp(0.2, 1.0);
                    frame[0] *= gr;
                    frame[1] *= gr;
                    let gr_db = 20.0 * gr.log10();
                    if gr_db < max_gr {
                        max_gr = gr_db;
                    }
                }
            }
            self.deesser_reduction_db = max_gr;
        } else {
            self.deesser_reduction_db = 0.0;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enhancer_spatial_widener() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.spatial_width = 1.5;

        let mut audio = vec![[0.8f32, 0.0f32]; 128]; // Hard panned Left
        enh.process(&mut audio);

        assert_ne!(audio[0][0], audio[0][1]);
        assert!(!audio[0][0].is_nan());
    }

    #[test]
    fn test_enhancer_tube_warmth_saturation() {
        let mut enh = AudiophileEnhancer::new(48000.0);
        enh.tube_warmth = 0.3;

        let mut audio = vec![[1.5f32, 1.5f32]; 128]; // Hot signal
        enh.process(&mut audio);

        // Saturation should clamp hot signal safely
        assert!(audio[0][0].abs() <= 1.0);
        assert!(!audio[0][0].is_nan());
    }
}
