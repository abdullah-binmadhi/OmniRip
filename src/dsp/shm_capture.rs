//! Lock-free POSIX Shared Memory reader for the macOS Output-Only HAL v2 driver.
//!
//! Because `OrchestriaAudio.driver` v2 exposes strictly an output stream and writes desktop
//! PCM into `/orchestria_audio_shm`, Orchestria maps the ring buffer read-only (`O_RDONLY` /
//! `PROT_READ`) and opens ZERO CoreAudio input streams — eliminating the macOS orange
//! microphone indicator dot and microphone TCC prompt while System-Wide EQ is active.

use super::servo::{ServoReader, ServoWriter};
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;

pub const ORCHESTRIA_SHM_NAME: &str = "/orchestria_audio_shm";
pub const ORCHESTRIA_SHM_MAGIC: u32 = 0x4F4D_5348; // "OMSH"
pub const ORCHESTRIA_SHM_VERSION: u32 = 2;
pub const ORCHESTRIA_SHM_FRAMES: usize = 32_768;
pub const ORCHESTRIA_SHM_CHANNELS: usize = 2;

/// Binary ABI shared with `drivers/orchestria_hal/OrchestriaAudio.h` (`OrchestriaShmRing`).
#[repr(C, align(64))]
pub struct OrchestriaShmRing {
    pub magic: u32,
    pub version: u32,
    pub channels: u32,
    pub capacity_frames: u32,
    pub sample_rate_hz: AtomicU32,
    pub volume_bits: AtomicU32,
    pub is_muted: AtomicU32,
    pub io_running: AtomicU32,
    pub write_cursor: AtomicU64,
    pub heartbeat_ns: AtomicU64,
    pub _pad: [u8; 16],
    pub frames: [[f32; 2]; ORCHESTRIA_SHM_FRAMES],
}

impl OrchestriaShmRing {
    /// Creates an initialized ring buffer in memory for unit tests.
    pub fn new_boxed() -> Box<Self> {
        let mut ring = Box::new(Self {
            magic: ORCHESTRIA_SHM_MAGIC,
            version: ORCHESTRIA_SHM_VERSION,
            channels: ORCHESTRIA_SHM_CHANNELS as u32,
            capacity_frames: ORCHESTRIA_SHM_FRAMES as u32,
            sample_rate_hz: AtomicU32::new(48_000),
            volume_bits: AtomicU32::new(1.0f32.to_bits()),
            is_muted: AtomicU32::new(0),
            io_running: AtomicU32::new(1),
            write_cursor: AtomicU64::new(0),
            heartbeat_ns: AtomicU64::new(0),
            _pad: [0u8; 16],
            frames: [[0.0f32; 2]; ORCHESTRIA_SHM_FRAMES],
        });
        ring.magic = ORCHESTRIA_SHM_MAGIC;
        ring
    }
}

#[cfg(unix)]
mod posix_shm {
    use std::ffi::c_void;
    use std::os::raw::{c_char, c_int};

    pub const O_RDONLY: c_int = 0;
    pub const PROT_READ: c_int = 1;
    pub const MAP_SHARED: c_int = 1;
    pub const MAP_FAILED: *mut c_void = !0usize as *mut c_void;

    extern "C" {
        pub fn shm_open(name: *const c_char, oflag: c_int, ...) -> c_int;
        pub fn mmap(
            addr: *mut c_void,
            len: usize,
            prot: c_int,
            flags: c_int,
            fd: c_int,
            offset: i64,
        ) -> *mut c_void;
        pub fn munmap(addr: *mut c_void, len: usize) -> c_int;
        pub fn close(fd: c_int) -> c_int;
    }
}

/// Read-only consumer view over either a real POSIX SHM mapping or an in-memory test ring.
pub struct ShmRingReader {
    ptr: *const OrchestriaShmRing,
    fd: i32,
    mapped_len: usize,
    read_cursor: u64,
}

unsafe impl Send for ShmRingReader {}

impl ShmRingReader {
    /// Opens `/orchestria_audio_shm` read-only and validates header magic/version.
    #[cfg(unix)]
    pub fn open_default() -> Result<Self, String> {
        use std::ffi::CString;
        let name = CString::new(ORCHESTRIA_SHM_NAME).map_err(|e| e.to_string())?;
        let fd = unsafe { posix_shm::shm_open(name.as_ptr(), posix_shm::O_RDONLY, 0) };
        if fd < 0 {
            let err = std::io::Error::last_os_error();
            return Err(format!("shm_open({}) failed: {}", ORCHESTRIA_SHM_NAME, err));
        }

        let len = std::mem::size_of::<OrchestriaShmRing>();
        let mapped = unsafe {
            posix_shm::mmap(
                std::ptr::null_mut(),
                len,
                posix_shm::PROT_READ,
                posix_shm::MAP_SHARED,
                fd,
                0,
            )
        };
        if mapped.is_null() || mapped == posix_shm::MAP_FAILED {
            let err = std::io::Error::last_os_error();
            unsafe {
                posix_shm::close(fd);
            }
            return Err(format!("mmap({}) failed: {}", ORCHESTRIA_SHM_NAME, err));
        }

        let ring_ptr = mapped as *const OrchestriaShmRing;
        let ring = unsafe { &*ring_ptr };
        if ring.magic != ORCHESTRIA_SHM_MAGIC
            || ring.version != ORCHESTRIA_SHM_VERSION
            || ring.channels != ORCHESTRIA_SHM_CHANNELS as u32
            || ring.capacity_frames != ORCHESTRIA_SHM_FRAMES as u32
        {
            unsafe {
                posix_shm::munmap(mapped, len);
                posix_shm::close(fd);
            }
            return Err(format!(
                "Invalid SHM header (magic=0x{:08x}, version={})",
                ring.magic, ring.version
            ));
        }

        // Start slightly behind live cursor (up to 512 frames) so startup avoids stale history.
        let wc = ring.write_cursor.load(Ordering::Acquire);
        let initial_cursor = wc.saturating_sub(256);

        Ok(Self {
            ptr: ring_ptr,
            fd,
            mapped_len: len,
            read_cursor: initial_cursor,
        })
    }

    #[cfg(not(unix))]
    pub fn open_default() -> Result<Self, String> {
        Err("POSIX SHM capture is only used on macOS/Unix".to_string())
    }

    /// Creates a reader bound to an existing in-memory ring (for deterministic unit tests).
    #[cfg(test)]
    pub fn from_test_ring(ring: &OrchestriaShmRing) -> Self {
        Self {
            ptr: ring as *const OrchestriaShmRing,
            fd: -1,
            mapped_len: 0,
            read_cursor: 0,
        }
    }

    /// Returns true if `/orchestria_audio_shm` exists, maps cleanly, and reports version 2.
    pub fn is_available() -> bool {
        Self::open_default().is_ok()
    }

    #[inline]
    fn ring(&self) -> &OrchestriaShmRing {
        unsafe { &*self.ptr }
    }

    pub fn sample_rate(&self) -> u32 {
        self.ring().sample_rate_hz.load(Ordering::Relaxed).max(8_000)
    }

    pub fn volume_scalar(&self) -> f32 {
        f32::from_bits(self.ring().volume_bits.load(Ordering::Relaxed)).clamp(0.0, 1.0)
    }

    pub fn is_muted(&self) -> bool {
        self.ring().is_muted.load(Ordering::Relaxed) != 0
    }

    pub fn is_io_running(&self) -> bool {
        self.ring().io_running.load(Ordering::Acquire) != 0
    }

    /// Reads newly written stereo frames into `out`, handling ring wraparound and overruns.
    /// Returns the number of frames copied.
    pub fn read_available(&mut self, out: &mut [[f32; 2]]) -> usize {
        if out.is_empty() {
            return 0;
        }
        // Borrow disjoint `self.ptr` directly so `self.read_cursor` can be updated cleanly.
        let ring: &OrchestriaShmRing = unsafe { &*self.ptr };
        let wc = ring.write_cursor.load(Ordering::Acquire);

        if wc == self.read_cursor {
            return 0;
        }

        // If writer reset cursor backwards, re-anchor cleanly.
        if wc < self.read_cursor {
            self.read_cursor = wc;
            return 0;
        }

        let cap = ORCHESTRIA_SHM_FRAMES as u64;
        let available = wc - self.read_cursor;
        if available > cap {
            // Overrun recovery: snap forward close to live edge.
            self.read_cursor = wc.saturating_sub(512);
        }

        let to_read = ((wc - self.read_cursor) as usize).min(out.len());
        if to_read == 0 {
            return 0;
        }

        if ring.is_muted.load(Ordering::Relaxed) != 0 {
            out[..to_read].fill([0.0, 0.0]);
            self.read_cursor += to_read as u64;
            return to_read;
        }

        let start = (self.read_cursor as usize) % ORCHESTRIA_SHM_FRAMES;
        let first = (ORCHESTRIA_SHM_FRAMES - start).min(to_read);
        let second = to_read - first;

        out[..first].copy_from_slice(&ring.frames[start..start + first]);
        if second > 0 {
            out[first..to_read].copy_from_slice(&ring.frames[..second]);
        }

        self.read_cursor += to_read as u64;
        to_read
    }
}

impl Drop for ShmRingReader {
    fn drop(&mut self) {
        #[cfg(unix)]
        if self.mapped_len > 0 && !self.ptr.is_null() {
            unsafe {
                posix_shm::munmap(self.ptr as *mut std::ffi::c_void, self.mapped_len);
                if self.fd >= 0 {
                    posix_shm::close(self.fd);
                }
            }
        }
    }
}

/// Active background thread bridging `/orchestria_audio_shm` into `ServoWriter` (zero CoreAudio input).
pub struct ShmCaptureHandle {
    stop_flag: Arc<AtomicBool>,
    thread: Option<JoinHandle<()>>,
}

impl ShmCaptureHandle {
    /// Starts the zero-dot POSIX SHM reader thread.
    /// If `/orchestria_audio_shm` does not exist yet (e.g. `coreaudiod` is about to initialize the v2 HAL
    /// plugin on the first audio cycle), `wait_for_shm` lets the thread poll until it appears without
    /// ever opening a CoreAudio input stream.
    pub fn start(
        writer: Arc<Mutex<ServoWriter>>,
        reader_handle: Arc<Mutex<ServoReader>>,
        out_sample_rate: u32,
        system_volume_bits: Arc<AtomicU32>,
        is_paused: Arc<AtomicBool>,
        captured_frames_counter: Arc<AtomicU64>,
        wait_for_shm: bool,
    ) -> Result<Self, String> {
        let initial_shm = match ShmRingReader::open_default() {
            Ok(r) => Some(r),
            Err(_) if wait_for_shm => None,
            Err(e) => return Err(e),
        };
        let stop_flag = Arc::new(AtomicBool::new(false));
        let stop_clone = Arc::clone(&stop_flag);

        let handle = thread::Builder::new()
            .name("orchestria-shm-reader".to_string())
            .spawn(move || {
                let mut shm_opt = initial_shm;
                let mut scratch = [[0.0f32; 2]; 1024];
                let mut last_rate = 0u32;

                while !stop_clone.load(Ordering::Relaxed) {
                    if shm_opt.is_none() {
                        match ShmRingReader::open_default() {
                            Ok(r) => shm_opt = Some(r),
                            Err(_) => {
                                thread::sleep(Duration::from_millis(50));
                                continue;
                            }
                        }
                    }
                    let Some(ref mut shm) = shm_opt else {
                        continue;
                    };

                    let sr = shm.sample_rate();
                    if sr != last_rate && out_sample_rate > 0 {
                        last_rate = sr;
                        if let Ok(mut r) = reader_handle.lock() {
                            r.set_nominal_ratio(sr as f64 / out_sample_rate as f64);
                        }
                    }

                    let vol = shm.volume_scalar();
                    system_volume_bits.store(vol.to_bits(), Ordering::Relaxed);

                    if is_paused.load(Ordering::Relaxed) {
                        // Drain so cursor tracks live time without accumulating lag.
                        let _ = shm.read_available(&mut scratch);
                        thread::sleep(Duration::from_millis(5));
                        continue;
                    }

                    let n = shm.read_available(&mut scratch);
                    if n > 0 {
                        captured_frames_counter.fetch_add(n as u64, Ordering::Relaxed);
                        if let Ok(mut w) = writer.lock() {
                            w.write(&scratch[..n]);
                        }
                    } else {
                        thread::sleep(Duration::from_millis(1));
                    }
                }
            })
            .map_err(|e| format!("Failed to spawn SHM capture thread: {}", e))?;

        Ok(Self {
            stop_flag,
            thread: Some(handle),
        })
    }

    pub fn stop(&mut self) {
        self.stop_flag.store(true, Ordering::SeqCst);
        if let Some(h) = self.thread.take() {
            let _ = h.join();
        }
    }
}

impl Drop for ShmCaptureHandle {
    fn drop(&mut self) {
        self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shm_ring_abi_matches_c_header() {
        assert_eq!(std::mem::align_of::<OrchestriaShmRing>(), 64);
        assert_eq!(
            std::mem::size_of::<OrchestriaShmRing>(),
            64 + ORCHESTRIA_SHM_FRAMES * ORCHESTRIA_SHM_CHANNELS * std::mem::size_of::<f32>()
        );
    }

    #[test]
    fn shm_reader_reads_wraparound_and_recovers_from_overrun() {
        let mut ring = OrchestriaShmRing::new_boxed();
        // Write across ring boundary: start at capacity - 4, write 8 frames.
        let start = ORCHESTRIA_SHM_FRAMES - 4;
        for i in 0..8 {
            let idx = (start + i) % ORCHESTRIA_SHM_FRAMES;
            ring.frames[idx] = [(i + 1) as f32 * 0.1, -(i as f32) * 0.1];
        }
        ring.write_cursor.store((start + 8) as u64, Ordering::Release);

        let mut reader = ShmRingReader::from_test_ring(&ring);
        // Set reader cursor right before wraparound.
        reader.read_cursor = start as u64;
        let mut out = [[0.0f32; 2]; 16];
        let got = reader.read_available(&mut out);
        assert_eq!(got, 8);
        assert!((out[0][0] - 0.1).abs() < 1e-6);
        assert!((out[7][0] - 0.8).abs() < 1e-6);

        // Simulate severe writer overrun (> ORCHESTRIA_SHM_FRAMES ahead).
        let huge_cursor = (ORCHESTRIA_SHM_FRAMES as u64) * 3;
        ring.frames[(huge_cursor as usize - 1) % ORCHESTRIA_SHM_FRAMES] = [0.75, -0.75];
        ring.write_cursor.store(huge_cursor, Ordering::Release);

        let mut overrun_buf = [[0.0f32; 2]; 1024];
        let recovered = reader.read_available(&mut overrun_buf);
        assert_eq!(recovered, 512);
        assert!((overrun_buf[511][0] - 0.75).abs() < 1e-6);
    }

    #[test]
    fn shm_reader_emits_zeros_when_muted_and_reports_volume() {
        let mut ring = OrchestriaShmRing::new_boxed();
        ring.frames[0] = [0.5, 0.5];
        ring.frames[1] = [0.6, 0.6];
        ring.is_muted.store(1, Ordering::Relaxed);
        ring.volume_bits.store(0.42f32.to_bits(), Ordering::Relaxed);
        ring.write_cursor.store(2, Ordering::Release);

        let mut reader = ShmRingReader::from_test_ring(&ring);
        let mut out = [[9.0f32; 2]; 4];
        let n = reader.read_available(&mut out);
        assert_eq!(n, 2);
        assert_eq!(out[0], [0.0, 0.0]);
        assert_eq!(out[1], [0.0, 0.0]);
        assert!((reader.volume_scalar() - 0.42).abs() < 1e-5);
        assert!(reader.is_muted());
    }
}
