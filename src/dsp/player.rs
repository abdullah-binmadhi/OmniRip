//! In-Memory High-Fidelity Audio Track Player in Pure Rust using `symphonia`.
//!
//! Provides gapless, zero-latency playback of downloaded audio files (FLAC, MP3, M4A, WAV, Opus)
//! routed directly through OmniRip's mastering DSP pipeline, 10-Band EQ, and live telemetry engine.

use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::DecoderOptions;
use symphonia::core::errors::Error;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

#[derive(Debug, Clone)]
pub struct TrackInfo {
    pub file_path: PathBuf,
    pub title: String,
    pub artist: String,
    pub duration_secs: f32,
    pub sample_rate: u32,
    pub channels: u32,
    pub format: String,
}

pub struct TrackPlayer {
    samples: Arc<Mutex<Vec<[f32; 2]>>>,
    position: Arc<AtomicUsize>,
    is_playing: Arc<AtomicBool>,
    track_info: Arc<Mutex<Option<TrackInfo>>>,
    volume: Arc<AtomicUsize>,
    target_sample_rate: f32,
    has_finished: Arc<AtomicBool>,
}

impl Default for TrackPlayer {
    fn default() -> Self {
        Self::new(48000.0)
    }
}

impl TrackPlayer {
    pub fn new(target_sample_rate: f32) -> Self {
        let (saved_pct, _) = crate::dsp::volume_storage::load_volume_settings();
        Self {
            samples: Arc::new(Mutex::new(Vec::new())),
            position: Arc::new(AtomicUsize::new(0)),
            is_playing: Arc::new(AtomicBool::new(false)),
            track_info: Arc::new(Mutex::new(None)),
            volume: Arc::new(AtomicUsize::new(saved_pct)),
            target_sample_rate,
            has_finished: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Decodes an audio file using Symphonia (native pure-Rust for MP3, FLAC, WAV, OGG).
    pub fn decode_with_symphonia(&self, path: &Path) -> Result<(Vec<[f32; 2]>, u32), String> {
        let file = std::fs::File::open(path)
            .map_err(|e| format!("Failed to open file: {}", e))?;
        let mss = MediaSourceStream::new(Box::new(file), Default::default());

        let mut hint = Hint::new();
        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
            hint.with_extension(ext);
        }

        let format_opts = FormatOptions::default();
        let metadata_opts = MetadataOptions::default();
        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &format_opts, &metadata_opts)
            .map_err(|e| format!("Failed to probe audio format: {}", e))?;

        let mut format = probed.format;
        let track = format
            .tracks()
            .iter()
            .find(|t| t.codec_params.codec != symphonia::core::codecs::CODEC_TYPE_NULL)
            .ok_or_else(|| "No supported audio track found in file".to_string())?;

        let track_id = track.id;
        let original_rate = track.codec_params.sample_rate.unwrap_or(44100);
        let channels = track.codec_params.channels.map(|c| c.count() as u32).unwrap_or(2);

        let decoder_opts = DecoderOptions::default();
        let mut decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &decoder_opts)
            .map_err(|e| format!("Failed to create audio decoder: {}", e))?;

        let mut decoded_stereo: Vec<[f32; 2]> = Vec::new();

        loop {
            let packet = match format.next_packet() {
                Ok(p) => p,
                Err(Error::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
                Err(Error::ResetRequired) => continue,
                Err(_) => break,
            };

            if packet.track_id() != track_id {
                continue;
            }

            match decoder.decode(&packet) {
                Ok(audio_buf) => {
                    let mut sample_buf = SampleBuffer::<f32>::new(audio_buf.capacity() as u64, *audio_buf.spec());
                    sample_buf.copy_interleaved_ref(audio_buf);
                    let raw_samples = sample_buf.samples();

                    if channels >= 2 {
                        for chunk in raw_samples.chunks_exact(channels as usize) {
                            decoded_stereo.push([chunk[0], chunk[1]]);
                        }
                    } else if channels == 1 {
                        for &s in raw_samples {
                            decoded_stereo.push([s, s]);
                        }
                    }
                }
                Err(Error::DecodeError(_)) => continue,
                Err(Error::ResetRequired) => continue,
                Err(_) => break,
            }
        }

        if decoded_stereo.is_empty() {
            return Err("Decoded zero audio samples from track".to_string());
        }

        Ok((decoded_stereo, original_rate))
    }

    /// Decodes an audio file using ffmpeg fallback (seamlessly decodes WebM, Opus, AAC, M4A, ALAC, etc.).
    pub fn decode_with_ffmpeg(&self, path: &Path) -> Result<(Vec<[f32; 2]>, u32), String> {
        let sr_str = format!("{}", self.target_sample_rate as u32);
        let mut decode_proc = Command::new("ffmpeg")
            .args([
                "-v", "error",
                "-i", path.to_str().ok_or("Invalid path")?,
                "-f", "f32le",
                "-acodec", "pcm_f32le",
                "-ar", &sr_str,
                "-ac", "2",
                "pipe:1",
            ])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to spawn ffmpeg decoder: {}", e))?;

        let mut raw_bytes = Vec::new();
        if let Some(mut stdout) = decode_proc.stdout.take() {
            let _ = stdout.read_to_end(&mut raw_bytes);
        }

        let status = decode_proc
            .wait()
            .map_err(|e| format!("ffmpeg decoder failed to exit: {}", e))?;
        if !status.success() || raw_bytes.len() < 8 {
            return Err("ffmpeg decoding returned empty or error exit status".to_string());
        }

        let total_frames = (raw_bytes.len() / 4) / 2;
        let mut buffer: Vec<[f32; 2]> = Vec::with_capacity(total_frames);
        for chunk in raw_bytes.chunks_exact(8) {
            let left = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
            let right = f32::from_le_bytes([chunk[4], chunk[5], chunk[6], chunk[7]]);
            buffer.push([left, right]);
        }

        Ok((buffer, self.target_sample_rate as u32))
    }

    /// Loads and decodes an audio file into in-memory stereo 32-bit floating point frames.
    pub fn load_file(&self, path: &Path) -> Result<TrackInfo, String> {
        if !path.exists() {
            return Err(format!("File does not exist: {:?}", path));
        }

        // Try native Symphonia decoding first, seamlessly fall back to ffmpeg for Opus/WebM/AAC
        let (decoded_stereo, original_rate) = match self.decode_with_symphonia(path) {
            Ok(res) => res,
            Err(sym_err) => {
                self.decode_with_ffmpeg(path).map_err(|ff_err| {
                    format!("Decoder error: Symphonia: {} | ffmpeg: {}", sym_err, ff_err)
                })?
            }
        };

        // Resample to target DAC rate if necessary (e.g. 44.1kHz -> 48kHz)
        let final_samples = if (original_rate as f32 - self.target_sample_rate).abs() > 1.0 {
            let ratio = original_rate as f64 / self.target_sample_rate as f64;
            let out_len = ((decoded_stereo.len() as f64) / ratio) as usize;
            let mut resampled = Vec::with_capacity(out_len);
            for i in 0..out_len {
                let src_pos = i as f64 * ratio;
                let idx0 = src_pos.floor() as usize;
                let frac = (src_pos - idx0 as f64) as f32;
                let idx1 = (idx0 + 1).min(decoded_stereo.len() - 1);
                let idx0_safe = idx0.min(decoded_stereo.len() - 1);

                let s0 = decoded_stereo[idx0_safe];
                let s1 = decoded_stereo[idx1];
                let l = s0[0] + frac * (s1[0] - s0[0]);
                let r = s0[1] + frac * (s1[1] - s0[1]);
                resampled.push([l, r]);
            }
            resampled
        } else {
            decoded_stereo
        };

        let duration_secs = final_samples.len() as f32 / self.target_sample_rate;
        let file_stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("Unknown Track");
        let format_ext = path.extension().and_then(|e| e.to_str()).unwrap_or("audio").to_uppercase();

        let (artist, title) = if let Some((a, t)) = file_stem.split_once(" - ") {
            (a.trim().to_string(), t.trim().to_string())
        } else {
            ("Unknown Artist".to_string(), file_stem.to_string())
        };

        let info = TrackInfo {
            file_path: path.to_path_buf(),
            title,
            artist,
            duration_secs,
            sample_rate: self.target_sample_rate as u32,
            channels: 2,
            format: format_ext,
        };

        // Store samples and reset playback position
        if let Ok(mut s) = self.samples.lock() {
            *s = final_samples;
        }
        self.position.store(0, Ordering::SeqCst);
        self.is_playing.store(false, Ordering::SeqCst);
        self.has_finished.store(false, Ordering::SeqCst);
        if let Ok(mut t) = self.track_info.lock() {
            *t = Some(info.clone());
        }

        Ok(info)
    }

    pub fn play(&self) {
        self.has_finished.store(false, Ordering::SeqCst);
        self.is_playing.store(true, Ordering::SeqCst);
    }

    pub fn pause(&self) {
        self.is_playing.store(false, Ordering::SeqCst);
    }

    pub fn stop(&self) {
        self.pause();
        self.position.store(0, Ordering::SeqCst);
        self.has_finished.store(false, Ordering::SeqCst);
    }

    /// Completely purges loaded audio samples and metadata from memory.
    pub fn clear(&self) {
        self.pause();
        self.position.store(0, Ordering::SeqCst);
        self.has_finished.store(false, Ordering::SeqCst);
        if let Ok(mut s) = self.samples.lock() {
            s.clear();
        }
        if let Ok(mut t) = self.track_info.lock() {
            *t = None;
        }
    }

    pub fn toggle(&self) -> bool {
        let current = self.is_playing.load(Ordering::SeqCst);
        self.is_playing.store(!current, Ordering::SeqCst);
        !current
    }

    pub fn restart(&self) {
        self.position.store(0, Ordering::SeqCst);
        self.has_finished.store(false, Ordering::SeqCst);
        self.is_playing.store(true, Ordering::SeqCst);
    }

    pub fn seek_by(&self, delta_secs: f32) {
        let total = self.samples.lock().map(|s| s.len()).unwrap_or(0);
        if total == 0 {
            self.position.store(0, Ordering::SeqCst);
            return;
        }
        let delta_frames = (delta_secs * self.target_sample_rate) as isize;
        let cur = self.position.load(Ordering::SeqCst) as isize;
        let max_pos = total.saturating_sub(1) as isize;
        let new_pos = (cur + delta_frames).clamp(0, max_pos) as usize;
        self.position.store(new_pos, Ordering::SeqCst);
    }

    pub fn is_playing(&self) -> bool {
        self.is_playing.load(Ordering::SeqCst)
    }

    pub fn is_finished(&self) -> bool {
        self.has_finished.load(Ordering::SeqCst)
    }

    pub fn set_finished(&self, finished: bool) {
        self.has_finished.store(finished, Ordering::SeqCst);
    }

    pub fn consume_finished(&self) -> bool {
        self.has_finished.swap(false, Ordering::SeqCst)
    }

    pub fn has_track(&self) -> bool {
        self.track_info.lock().map(|t| t.is_some()).unwrap_or(false)
    }

    pub fn track_info(&self) -> Option<TrackInfo> {
        self.track_info.lock().ok().and_then(|t| t.clone())
    }

    pub fn progress(&self) -> (f32, f32) {
        let cur = self.position.load(Ordering::SeqCst);
        let total = self.samples.lock().map(|s| s.len()).unwrap_or(0);
        let cur_secs = cur as f32 / self.target_sample_rate;
        let total_secs = total as f32 / self.target_sample_rate;
        (cur_secs, total_secs)
    }

    pub fn position(&self) -> (f32, f32) {
        self.progress()
    }

    #[cfg(all(target_os = "macos", not(test)))]
    fn sync_macos_system_volume(pct: usize) {
        let script = format!("set volume output volume {}", pct);
        let _ = std::process::Command::new("osascript")
            .args(["-e", &script])
            .output();
    }

    #[cfg(all(target_os = "macos", not(test)))]
    pub fn get_macos_system_volume() -> Option<usize> {
        let output = std::process::Command::new("osascript")
            .args(["-e", "output volume of (get volume settings)"])
            .output()
            .ok()?;
        if output.status.success() {
            let s = String::from_utf8_lossy(&output.stdout);
            s.trim().parse::<usize>().ok()
        } else {
            None
        }
    }

    pub fn volume(&self) -> f32 {
        self.volume_pct() as f32 / 100.0
    }

    pub fn volume_pct(&self) -> usize {
        #[cfg(all(target_os = "macos", not(test)))]
        {
            static LAST_CHECK: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0);
            let last = LAST_CHECK.load(Ordering::Relaxed);
            if now.saturating_sub(last) > 800 {
                LAST_CHECK.store(now, Ordering::Relaxed);
                if let Some(sys) = Self::get_macos_system_volume() {
                    self.volume.store(sys, Ordering::Relaxed);
                    return sys;
                }
            }
        }
        self.volume.load(Ordering::Relaxed)
    }

    pub fn set_volume(&self, vol: f32) {
        let pct = (vol * 100.0).clamp(0.0, 100.0).round() as usize;
        self.set_volume_pct(pct);
    }

    pub fn set_volume_pct(&self, pct: usize) {
        let safe = pct.min(100);
        self.volume.store(safe, Ordering::Relaxed);
        #[cfg(all(target_os = "macos", not(test)))]
        {
            Self::sync_macos_system_volume(safe);
        }
        let (_, sys) = crate::dsp::volume_storage::load_volume_settings();
        crate::dsp::volume_storage::save_volume_settings(safe, sys);
    }

    pub fn adjust_volume(&self, delta: f32) -> f32 {
        let step = (delta * 100.0).round() as isize;
        let new_pct = self.adjust_volume_pct(step);
        new_pct as f32 / 100.0
    }

    pub fn adjust_volume_pct(&self, delta: isize) -> usize {
        let cur = self.volume_pct();
        let new_pct = (cur as isize + delta).clamp(0, 100) as usize;
        self.set_volume_pct(new_pct);
        new_pct
    }

    /// Read stereo frames into `out` buffer in real time without heap allocations.
    #[inline]
    pub fn read_frames(&self, out: &mut [[f32; 2]]) -> usize {
        if !self.is_playing.load(Ordering::Relaxed) {
            return 0;
        }

        let Ok(samples) = self.samples.lock() else {
            return 0;
        };

        if samples.is_empty() {
            return 0;
        }

        let cur = self.position.load(Ordering::Relaxed);
        let needed = out.len();
        let available = samples.len().saturating_sub(cur);

        if available == 0 {
            // Reached end of track: auto-pause
            self.is_playing.store(false, Ordering::SeqCst);
            self.has_finished.store(true, Ordering::SeqCst);
            return 0;
        }

        let count = needed.min(available);
        out[..count].copy_from_slice(&samples[cur..cur + count]);
        self.position.store(cur + count, Ordering::Relaxed);

        #[cfg(all(target_os = "macos", not(test)))]
        {
            // Hardware DAC volume is in 1:1 control of output. Pass at unity dynamic range.
        }
        #[cfg(any(not(target_os = "macos"), test))]
        {
            let vol = self.volume.load(Ordering::Relaxed) as f32 / 100.0;
            if (vol - 1.0).abs() > 1e-4 {
                for frame in out[..count].iter_mut() {
                    frame[0] *= vol;
                    frame[1] *= vol;
                }
            }
        }

        count
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_track_player_initial_state() {
        let player = TrackPlayer::new(48000.0);
        assert!(!player.is_playing());
        assert!(!player.has_track());
        assert_eq!(player.progress(), (0.0, 0.0));
    }

    #[test]
    fn test_track_player_toggle_and_seek() {
        let player = TrackPlayer::new(48000.0);
        // Put synthetic samples
        if let Ok(mut s) = player.samples.lock() {
            *s = vec![[0.5, -0.5]; 48000 * 10]; // 10 seconds of audio
        }
        assert!(!player.is_playing());
        assert!(player.toggle());
        assert!(player.is_playing());
        assert!(!player.toggle());
        assert!(!player.is_playing());

        // Seek forward 3 seconds
        player.seek_by(3.0);
        assert_eq!(player.position.load(Ordering::SeqCst), 48000 * 3);

        // Read 100 frames with full volume
        let mut buf = [[0.0f32; 2]; 100];
        player.set_volume(1.0);
        player.play();
        let read = player.read_frames(&mut buf);
        assert_eq!(read, 100);
        assert_eq!(buf[0], [0.5, -0.5]);
    }

    #[test]
    fn test_track_player_volume_adjustment() {
        let player = TrackPlayer::new(48000.0);
        player.set_volume(1.0);
        assert_eq!(player.volume(), 1.0);

        // Adjust volume down by 20%
        let v = player.adjust_volume(-0.2);
        assert!((v - 0.8).abs() < 1e-4);
        assert!((player.volume() - 0.8).abs() < 1e-4);

        // Read frames with volume scaling applied
        if let Ok(mut s) = player.samples.lock() {
            *s = vec![[1.0, 1.0]; 100];
        }
        player.play();
        let mut buf = [[0.0f32; 2]; 10];
        let read = player.read_frames(&mut buf);
        assert_eq!(read, 10);
        assert!((buf[0][0] - 0.8).abs() < 1e-4);
        assert!((buf[0][1] - 0.8).abs() < 1e-4);

        // Mute
        player.set_volume(0.0);
        assert_eq!(player.volume(), 0.0);
        let mut mute_buf = [[0.0f32; 2]; 10];
        player.seek_by(-1.0);
        player.read_frames(&mut mute_buf);
        assert_eq!(mute_buf[0], [0.0, 0.0]);
    }

    #[test]
    fn test_track_player_finished_detection() {
        let player = TrackPlayer::new(48000.0);
        assert!(!player.is_finished());

        // Put 50 samples
        if let Ok(mut s) = player.samples.lock() {
            *s = vec![[0.1, 0.1]; 50];
        }

        player.play();
        assert!(!player.is_finished());

        // Read all 50 frames
        let mut buf = [[0.0f32; 2]; 50];
        let read = player.read_frames(&mut buf);
        assert_eq!(read, 50);

        // Next read will trigger auto-pause and mark finished
        let mut extra_buf = [[0.0f32; 2]; 10];
        let extra_read = player.read_frames(&mut extra_buf);
        assert_eq!(extra_read, 0);
        assert!(!player.is_playing());
        assert!(player.is_finished());

        // Test atomic consumption
        assert!(player.consume_finished());
        assert!(!player.is_finished());
        assert!(!player.consume_finished());

        // Stopping resets finished flag
        player.stop();
        assert!(!player.is_finished());
    }

    #[test]
    fn test_probe_real_files() {
        let player = TrackPlayer::new(48000.0);
        let webm_path = std::env::temp_dir().join("omnirip_stream_BriCie - 【BriCie】 White Silence (English Cover).webm");
        if webm_path.exists() {
            let res_webm = player.load_file(&webm_path);
            assert!(res_webm.is_ok(), "BriCie webm should decode successfully via ffmpeg fallback");
            let info = res_webm.unwrap();
            assert!(info.duration_secs > 400.0);
            assert_eq!(info.channels, 2);
        }
    }
}
