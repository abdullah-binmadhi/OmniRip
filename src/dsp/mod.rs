//! Digital Signal Processing (DSP) and Audio Pipeline module.

pub mod biquad;
pub mod enhancer;
pub mod limiter;
pub mod restoration;
pub mod servo;
pub mod streamer;
pub mod telemetry;
pub mod transport;

pub use biquad::{BiquadFilter, BiquadFilterType, DualEngineCrossfader, FastSosFilter};
pub use enhancer::{AudiophileEnhancer, CrossfeedMode};
pub use limiter::BrickwallLimiter;
pub use servo::{create_servo_ring_buffer, ServoReader, ServoWriter};
pub use streamer::{AudioStreamer, SyncMode};
pub use telemetry::TelemetryEngine;
pub use transport::{AudioPacketHeader, IpcAudioServer, OMNIRIP_SOCKET_PATH};

/// Complete mastering audio DSP pipeline.
#[derive(Debug, Clone)]
pub struct AudioPipeline {
    pub sample_rate: f32,
    pub preamp_db: f32,
    pub volume_boost_db: f32,
    pub balance: f32,
    pub bypass: bool,
    pub crossfader: DualEngineCrossfader,
    pub enhancer: AudiophileEnhancer,
    pub limiter: BrickwallLimiter,
    pub telemetry: TelemetryEngine,
}

impl AudioPipeline {
    pub fn new(sample_rate: f32) -> Self {
        Self {
            sample_rate,
            preamp_db: 0.0,
            volume_boost_db: 0.0,
            balance: 0.0,
            bypass: false,
            crossfader: DualEngineCrossfader::new(),
            enhancer: AudiophileEnhancer::new(sample_rate),
            limiter: BrickwallLimiter::new(sample_rate),
            telemetry: TelemetryEngine::new(sample_rate),
        }
    }

    /// Process a stereo audio buffer in-place through the full mastering chain.
    #[inline]
    pub fn process(&mut self, buffer: &mut [[f32; 2]]) {
        if buffer.is_empty() {
            return;
        }

        if self.bypass {
            self.telemetry.update(buffer);
            return;
        }

        // 1. Preamp & Volume Boost Gain
        let preamp_mult = 10.0f32.powf(self.preamp_db / 20.0);
        let boost_mult = 10.0f32.powf(self.volume_boost_db / 20.0);
        let total_gain = preamp_mult * boost_mult;

        if (total_gain - 1.0).abs() > 1e-4 {
            for frame in buffer.iter_mut() {
                frame[0] *= total_gain;
                frame[1] *= total_gain;
            }
        }

        // 2. Stereo Pan Balance
        let bal = self.balance;
        if bal.abs() > 1e-4 {
            let left_mult = if bal > 0.0 { 1.0 - bal } else { 1.0 };
            let right_mult = if bal < 0.0 { 1.0 + bal } else { 1.0 };
            for frame in buffer.iter_mut() {
                frame[0] *= left_mult;
                frame[1] *= right_mult;
            }
        }

        // 3. Cascaded Biquad EQ (with clickless 15ms crossfade)
        self.crossfader.process(buffer);

        // 4. Studio Audiophile Enhancer Suite
        self.enhancer.process(buffer);

        // 5. Brickwall Peak Limiter (-0.2 dBFS ceiling)
        self.limiter.process(buffer);

        // 6. Live Telemetry
        self.telemetry.update(buffer);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pipeline_passthrough() {
        let mut pipeline = AudioPipeline::new(48000.0);
        let n_samples = 512;
        let mut audio = Vec::with_capacity(n_samples);
        for i in 0..n_samples {
            let t = i as f32 / 48000.0;
            let s = 0.5 * (2.0 * std::f32::consts::PI * 1000.0 * t).sin();
            audio.push([s, s]);
        }

        let input_clone = audio.clone();
        pipeline.process(&mut audio);

        assert_eq!(audio.len(), 512);
        assert!(!audio[0][0].is_nan());
        // Passthrough with flat EQ should preserve signal within 0.05
        let diff = (audio[100][0] - input_clone[100][0]).abs();
        assert!(diff < 0.05);
    }
}
