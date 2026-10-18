//! Digital Signal Processing (DSP) and Audio Pipeline module.

pub mod biquad;
pub mod enhancer;
pub mod hardware_detect;
pub mod limiter;
pub mod player;
pub mod restoration;
pub mod servo;
pub mod streamer;
pub mod telemetry;
pub mod transport;
pub mod volume_storage;

pub use biquad::{BiquadFilter, BiquadFilterType, DualEngineCrossfader, FastSosFilter};
pub use enhancer::{
    AcousticGearProfile, AudiophileEnhancer, CrossfeedMode, DacHardwareFlavor, DacMimickerEngine,
    GearCoupling, GearEnclosure, GearFormFactor, GearSourceAmp, GearTonalBalance, MasteringPreset,
};
pub use hardware_detect::{
    ChassisAcousticTier, HardwareChipProfile, SoundChipArchitecture, TransducerType,
};
pub use limiter::BrickwallLimiter;
pub use player::{TrackInfo, TrackPlayer};
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
    pub dac_mimicker: DacMimickerEngine,
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
            dac_mimicker: DacMimickerEngine::new(sample_rate),
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

        // 1. DAC/Amp Mimicker Stage (Hardware Filter Profile & Analog Stage Emulation)
        self.dac_mimicker.process(buffer);

        // 2. Preamp & Volume Boost Gain
        let preamp_mult = 10.0f32.powf(self.preamp_db / 20.0);
        let boost_mult = 10.0f32.powf(self.volume_boost_db / 20.0);
        let total_gain = preamp_mult * boost_mult;

        if (total_gain - 1.0).abs() > 1e-4 {
            for frame in buffer.iter_mut() {
                frame[0] *= total_gain;
                frame[1] *= total_gain;
            }
        }

        // 3. Stereo Pan Balance
        let bal = self.balance;
        if bal.abs() > 1e-4 {
            let left_mult = if bal > 0.0 { 1.0 - bal } else { 1.0 };
            let right_mult = if bal < 0.0 { 1.0 + bal } else { 1.0 };
            for frame in buffer.iter_mut() {
                frame[0] *= left_mult;
                frame[1] *= right_mult;
            }
        }

        // 4. Cascaded Biquad EQ (with clickless 15ms crossfade)
        self.crossfader.process(buffer);

        // 5. Studio Audiophile Enhancer Suite
        self.enhancer.process(buffer);

        // 6. Brickwall Peak Limiter (-0.2 dBFS ceiling)
        self.limiter.process(buffer);

        // 7. Live Telemetry
        self.telemetry.update(buffer);
    }

    /// Set the DAC/Amp mimicker flavor.
    pub fn set_dac_flavor(&mut self, flavor: DacHardwareFlavor) {
        self.dac_mimicker.set_flavor(flavor);
    }

    /// Cycle to the next DAC/Amp mimicker flavor.
    pub fn cycle_dac_flavor(&mut self) -> DacHardwareFlavor {
        self.dac_mimicker.cycle_flavor()
    }

    /// Get current target DAC/Amp mimicker flavor.
    pub fn current_dac_flavor(&self) -> DacHardwareFlavor {
        self.dac_mimicker.target_flavor
    }

    /// Apply an audiophile mastering preset recipe across enhancer and limiter.
    pub fn apply_mastering_preset(&mut self, preset: &MasteringPreset) {
        self.enhancer.apply_preset(preset);
        self.limiter.threshold = 10.0f32.powf(preset.limiter_ceiling_dbfs / 20.0);
    }

    /// Apply an audiophile mastering preset recipe tailored with the acoustic gear profile.
    pub fn apply_mastering_preset_with_gear(
        &mut self,
        preset: &MasteringPreset,
        gear: &AcousticGearProfile,
    ) {
        self.enhancer.apply_preset_with_gear(preset, gear);
        self.limiter.threshold = 10.0f32.powf(preset.limiter_ceiling_dbfs / 20.0);
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
