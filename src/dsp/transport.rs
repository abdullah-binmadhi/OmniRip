//! High-Speed Pure Rust Zero-Copy Unix Domain Socket Audio Transport.
//!
//! Exposes a local stream socket at `/tmp/omnirip_audio.sock` to receive live,
//! uncompressed 32-bit floating-point audio directly from browser bridges or
//! source applications, completely bypassing macOS kernel/HAL driver requirements.

use super::servo::ServoWriter;
use std::fs;
use std::io::{self, Read, Write};
#[cfg(unix)]
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

pub const OMNIRIP_SOCKET_PATH: &str = "/tmp/omnirip_audio.sock";
pub const OMNIRIP_TCP_PORT: u16 = 49152;
pub const OMNIRIP_MAGIC: u32 = 0x4F4D4E49; // "OMNI" in ASCII

#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AudioPacketHeader {
    pub magic: u32,
    pub sequence: u32,
    pub sample_rate: u32,
    pub channels: u16,
    pub frame_count: u16,
}

impl AudioPacketHeader {
    pub const SIZE: usize = std::mem::size_of::<Self>();

    pub fn new(sequence: u32, sample_rate: u32, frame_count: u16) -> Self {
        Self {
            magic: OMNIRIP_MAGIC,
            sequence,
            sample_rate,
            channels: 2,
            frame_count,
        }
    }

    pub fn from_bytes(bytes: &[u8]) -> Option<Self> {
        if bytes.len() < Self::SIZE {
            return None;
        }
        let magic = u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
        if magic != OMNIRIP_MAGIC {
            return None;
        }
        let sequence = u32::from_le_bytes([bytes[4], bytes[5], bytes[6], bytes[7]]);
        let sample_rate = u32::from_le_bytes([bytes[8], bytes[9], bytes[10], bytes[11]]);
        let channels = u16::from_le_bytes([bytes[12], bytes[13]]);
        let frame_count = u16::from_le_bytes([bytes[14], bytes[15]]);
        Some(Self {
            magic,
            sequence,
            sample_rate,
            channels,
            frame_count,
        })
    }
}

#[derive(Debug, Clone, Copy, Default)]
pub struct IpcServerTelemetry {
    pub active_clients: usize,
    pub total_packets: u64,
    pub total_frames: u64,
}

pub struct IpcAudioServer {
    is_running: Arc<AtomicBool>,
    writer: Arc<Mutex<ServoWriter>>,
    active_clients: Arc<AtomicUsize>,
    total_packets: Arc<AtomicU64>,
    total_frames: Arc<AtomicU64>,
}

impl IpcAudioServer {
    pub fn new(writer: ServoWriter) -> Self {
        Self {
            is_running: Arc::new(AtomicBool::new(false)),
            writer: Arc::new(Mutex::new(writer)),
            active_clients: Arc::new(AtomicUsize::new(0)),
            total_packets: Arc::new(AtomicU64::new(0)),
            total_frames: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn writer(&self) -> Arc<Mutex<ServoWriter>> {
        Arc::clone(&self.writer)
    }

    pub fn telemetry(&self) -> IpcServerTelemetry {
        IpcServerTelemetry {
            active_clients: self.active_clients.load(Ordering::Relaxed),
            total_packets: self.total_packets.load(Ordering::Relaxed),
            total_frames: self.total_frames.load(Ordering::Relaxed),
        }
    }

    pub fn start(&self) -> io::Result<()> {
        if self.is_running.load(Ordering::SeqCst) {
            return Ok(());
        }

        self.is_running.store(true, Ordering::SeqCst);

        #[cfg(unix)]
        {
            let socket_path = Path::new(OMNIRIP_SOCKET_PATH);
            let _ = fs::remove_file(socket_path);

            if let Ok(listener) = UnixListener::bind(socket_path) {
                let _ = listener.set_nonblocking(true);
                let running_flag = Arc::clone(&self.is_running);
                let writer_arc = Arc::clone(&self.writer);
                let clients_arc = Arc::clone(&self.active_clients);
                let packets_arc = Arc::clone(&self.total_packets);
                let frames_arc = Arc::clone(&self.total_frames);

                let _ = thread::Builder::new()
                    .name("omnirip-ipc-transport".to_string())
                    .spawn(move || {
                        let mut header_buf = [0u8; AudioPacketHeader::SIZE];
                        let mut payload_buf = vec![0u8; 16384 * 8]; // max buffer for large bursts

                        while running_flag.load(Ordering::SeqCst) {
                            match listener.accept() {
                                Ok((mut stream, _)) => {
                                    let _ = stream.set_nonblocking(false);
                                    clients_arc.fetch_add(1, Ordering::SeqCst);
                                    Self::handle_client(
                                        &mut stream,
                                        &writer_arc,
                                        &running_flag,
                                        &packets_arc,
                                        &frames_arc,
                                        &mut header_buf,
                                        &mut payload_buf,
                                    );
                                    clients_arc.fetch_sub(1, Ordering::SeqCst);
                                }
                                Err(ref e) if e.kind() == io::ErrorKind::WouldBlock || e.kind() == io::ErrorKind::Interrupted => {
                                    thread::sleep(std::time::Duration::from_millis(5));
                                }
                                Err(e) => {
                                    eprintln!("omnirip-ipc-transport accept error: {}", e);
                                    break;
                                }
                            }
                        }

                        let _ = fs::remove_file(OMNIRIP_SOCKET_PATH);
                    });
            }
        }

        // Also bind local TCP listener on 127.0.0.1:49152 for web browser and network bridges
        if let Ok(tcp_listener) = std::net::TcpListener::bind(format!("127.0.0.1:{}", OMNIRIP_TCP_PORT)) {
            let _ = tcp_listener.set_nonblocking(true);
            let running_tcp = Arc::clone(&self.is_running);
            let writer_tcp = Arc::clone(&self.writer);
            let clients_tcp = Arc::clone(&self.active_clients);
            let packets_tcp = Arc::clone(&self.total_packets);
            let frames_tcp = Arc::clone(&self.total_frames);

            thread::Builder::new()
                .name("omnirip-tcp-transport".to_string())
                .spawn(move || {
                    let mut header_buf = [0u8; AudioPacketHeader::SIZE];
                    let mut payload_buf = vec![0u8; 16384 * 8];

                    while running_tcp.load(Ordering::SeqCst) {
                        match tcp_listener.accept() {
                            Ok((mut stream, _)) => {
                                let _ = stream.set_nonblocking(false);
                                clients_tcp.fetch_add(1, Ordering::SeqCst);
                                Self::handle_client(
                                    &mut stream,
                                    &writer_tcp,
                                    &running_tcp,
                                    &packets_tcp,
                                    &frames_tcp,
                                    &mut header_buf,
                                    &mut payload_buf,
                                );
                                clients_tcp.fetch_sub(1, Ordering::SeqCst);
                            }
                            Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                                thread::sleep(std::time::Duration::from_millis(10));
                            }
                            Err(_) => break,
                        }
                    }
                })?;
        }

        Ok(())
    }

    fn handle_client<S: Read>(
        stream: &mut S,
        writer: &Arc<Mutex<ServoWriter>>,
        running: &Arc<AtomicBool>,
        packets: &Arc<AtomicU64>,
        frames: &Arc<AtomicU64>,
        header_buf: &mut [u8],
        payload_buf: &mut Vec<u8>,
    ) {
        while running.load(Ordering::SeqCst) {
            // Read packet header
            if stream.read_exact(header_buf).is_err() {
                break;
            }

            let header = match AudioPacketHeader::from_bytes(header_buf) {
                Some(h) => h,
                None => break,
            };

            let bytes_to_read = header.frame_count as usize * header.channels as usize * 4;
            if payload_buf.len() < bytes_to_read {
                payload_buf.resize(bytes_to_read, 0);
            }

            if stream.read_exact(&mut payload_buf[..bytes_to_read]).is_err() {
                break;
            }

            // Convert Float32 little-endian bytes to stereo frames
            let raw_frames = &payload_buf[..bytes_to_read];
            let mut scratch = Vec::with_capacity(header.frame_count as usize);

            for chunk in raw_frames.chunks_exact(8) {
                let l = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
                let r = f32::from_le_bytes([chunk[4], chunk[5], chunk[6], chunk[7]]);
                scratch.push([l, r]);
            }

            if let Ok(mut w) = writer.lock() {
                w.write(&scratch);
            }

            packets.fetch_add(1, Ordering::Relaxed);
            frames.fetch_add(header.frame_count as u64, Ordering::Relaxed);
        }
    }

    pub fn stop(&self) {
        self.is_running.store(false, Ordering::SeqCst);
        if Path::new(OMNIRIP_SOCKET_PATH).exists() {
            let _ = fs::remove_file(OMNIRIP_SOCKET_PATH);
        }
    }
}

impl Drop for IpcAudioServer {
    fn drop(&mut self) {
        self.stop();
    }
}

pub enum ClientStream {
    #[cfg(unix)]
    Unix(UnixStream),
    Tcp(std::net::TcpStream),
}

impl Write for ClientStream {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        match self {
            #[cfg(unix)]
            ClientStream::Unix(s) => s.write(buf),
            ClientStream::Tcp(s) => s.write(buf),
        }
    }

    fn flush(&mut self) -> io::Result<()> {
        match self {
            #[cfg(unix)]
            ClientStream::Unix(s) => s.flush(),
            ClientStream::Tcp(s) => s.flush(),
        }
    }
}

pub struct IpcAudioClient {
    stream: ClientStream,
    sequence: u32,
    sample_rate: u32,
}

impl IpcAudioClient {
    pub fn connect() -> io::Result<Self> {
        #[cfg(unix)]
        {
            if let Ok(stream) = UnixStream::connect(OMNIRIP_SOCKET_PATH) {
                return Ok(Self {
                    stream: ClientStream::Unix(stream),
                    sequence: 0,
                    sample_rate: 48000,
                });
            }
        }
        let tcp = std::net::TcpStream::connect(format!("127.0.0.1:{}", OMNIRIP_TCP_PORT))?;
        Ok(Self {
            stream: ClientStream::Tcp(tcp),
            sequence: 0,
            sample_rate: 48000,
        })
    }

    pub fn set_sample_rate(&mut self, rate: u32) {
        self.sample_rate = rate;
    }

    pub fn send_frames(&mut self, frames: &[[f32; 2]]) -> io::Result<()> {
        use std::io::Write;
        for chunk in frames.chunks(512) {
            let header = AudioPacketHeader::new(self.sequence, self.sample_rate, chunk.len() as u16);
            self.sequence = self.sequence.wrapping_add(1);

            let mut packet = Vec::with_capacity(AudioPacketHeader::SIZE + chunk.len() * 8);
            packet.extend_from_slice(&header.magic.to_le_bytes());
            packet.extend_from_slice(&header.sequence.to_le_bytes());
            packet.extend_from_slice(&header.sample_rate.to_le_bytes());
            packet.extend_from_slice(&header.channels.to_le_bytes());
            packet.extend_from_slice(&header.frame_count.to_le_bytes());

            for frame in chunk {
                packet.extend_from_slice(&frame[0].to_le_bytes());
                packet.extend_from_slice(&frame[1].to_le_bytes());
            }

            self.stream.write_all(&packet)?;
        }
        Ok(())
    }

    pub fn stream_from_raw_pcm_reader<R: Read>(&mut self, mut reader: R) -> io::Result<u64> {
        let mut buf = [0u8; 512 * 8]; // 512 stereo f32 frames
        let mut total_frames = 0u64;

        loop {
            match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(bytes_read) => {
                    let frame_count = bytes_read / 8;
                    if frame_count == 0 {
                        continue;
                    }
                    let mut frames = Vec::with_capacity(frame_count);
                    for chunk in buf[..frame_count * 8].chunks_exact(8) {
                        let l = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
                        let r = f32::from_le_bytes([chunk[4], chunk[5], chunk[6], chunk[7]]);
                        frames.push([l, r]);
                    }
                    self.send_frames(&frames)?;
                    total_frames += frame_count as u64;

                    // Pace at ~95% of real time to prevent buffer starvation while avoiding overflow
                    let sleep_micros = (frame_count as u64 * 1_000_000) / (self.sample_rate as u64);
                    std::thread::sleep(std::time::Duration::from_micros(sleep_micros * 95 / 100));
                }
                Err(ref e) if e.kind() == io::ErrorKind::Interrupted => continue,
                Err(e) => return Err(e),
            }
        }
        Ok(total_frames)
    }
}

/// Helper function to handle `omnirip feed` CLI execution.
pub fn run_feed_cli(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    println!("[OmniRip Feeder] Checking for running OmniRip audio engine at {}...", OMNIRIP_SOCKET_PATH);
    let mut _standalone_streamer = None;

    let mut client = match IpcAudioClient::connect() {
        Ok(c) => {
            println!("[OmniRip Feeder] Connected to background OmniRip audio engine!");
            c
        }
        Err(_) => {
            println!("[OmniRip Feeder] OmniRip TUI not currently running. Auto-starting dedicated 64-bit EQ Engine...");
            let pipeline = super::AudioPipeline::new(48000.0);
            let mut streamer = super::streamer::AudioStreamer::new(pipeline);
            streamer.start().map_err(|e| format!("Failed to initialize audio engine: {}", e))?;
            std::thread::sleep(std::time::Duration::from_millis(100));
            let client = IpcAudioClient::connect()?;
            _standalone_streamer = Some(streamer);
            println!("[OmniRip Feeder] Dedicated hardware audio stream initialized!");
            client
        }
    };
    println!("[OmniRip Feeder] Ready! Streaming raw 48.0 kHz 32-bit float PCM...");

    // Check if --file was specified
    let mut file_path = None;
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--file" && i + 1 < args.len() {
            file_path = Some(args[i + 1].clone());
            i += 1;
        }
        i += 1;
    }

    let total = if let Some(path) = file_path {
        println!("[OmniRip Feeder] Streaming from file: {}", path);
        let f = std::fs::File::open(path)?;
        client.stream_from_raw_pcm_reader(f)?
    } else {
        println!("[OmniRip Feeder] Streaming from standard input (stdin)...");
        let stdin = std::io::stdin();
        client.stream_from_raw_pcm_reader(stdin.lock())?
    };

    println!("[OmniRip Feeder] Stream completed! Total frames fed: {}", total);
    Ok(())
}

/// Helper function to handle `omnirip stream <url>` CLI execution.
pub fn run_stream_cli(url: &str) -> Result<(), Box<dyn std::error::Error>> {
    println!("[OmniRip Streamer] Checking for running OmniRip audio engine at {}...", OMNIRIP_SOCKET_PATH);
    let mut _standalone_streamer = None;

    let mut client = match IpcAudioClient::connect() {
        Ok(c) => {
            println!("[OmniRip Streamer] Connected to background OmniRip audio engine!");
            c
        }
        Err(_) => {
            println!("[OmniRip Streamer] OmniRip TUI not currently running. Auto-starting dedicated 64-bit EQ Engine...");
            let pipeline = super::AudioPipeline::new(48000.0);
            let mut streamer = super::streamer::AudioStreamer::new(pipeline);
            streamer.start().map_err(|e| format!("Failed to initialize audio engine: {}", e))?;
            std::thread::sleep(std::time::Duration::from_millis(100));
            let client = IpcAudioClient::connect()?;
            _standalone_streamer = Some(streamer);
            println!("[OmniRip Streamer] Dedicated hardware audio stream initialized!");
            client
        }
    };
    println!("[OmniRip Streamer] Resolving high-res audio stream via yt-dlp for: {}", url);

    // Spawn yt-dlp to extract audio and pipe through ffmpeg to Float32 LE stereo PCM
    let mut ffmpeg_child = std::process::Command::new("sh")
        .arg("-c")
        .arg(format!("yt-dlp -f bestaudio -o - \"{}\" 2>/dev/null | ffmpeg -i - -f f32le -ac 2 -ar 48000 -loglevel error -", url))
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::inherit())
        .spawn()?;

    let stdout = ffmpeg_child.stdout.take().ok_or("Failed to capture audio stream pipe")?;
    println!("[OmniRip Streamer] Streaming live audio directly into 64-bit EQ pipeline...");
    let total = client.stream_from_raw_pcm_reader(stdout)?;
    println!("[OmniRip Streamer] Stream finished! Total frames played: {}", total);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_packet_header_serialization() {
        let header = AudioPacketHeader::new(42, 48000, 256);
        assert_eq!(header.magic, OMNIRIP_MAGIC);
        assert_eq!(header.sequence, 42);
        assert_eq!(header.sample_rate, 48000);
        assert_eq!(header.channels, 2);
        assert_eq!(header.frame_count, 256);

        let mut bytes = [0u8; AudioPacketHeader::SIZE];
        bytes[0..4].copy_from_slice(&header.magic.to_le_bytes());
        bytes[4..8].copy_from_slice(&header.sequence.to_le_bytes());
        bytes[8..12].copy_from_slice(&header.sample_rate.to_le_bytes());
        bytes[12..14].copy_from_slice(&header.channels.to_le_bytes());
        bytes[14..16].copy_from_slice(&header.frame_count.to_le_bytes());

        let decoded = AudioPacketHeader::from_bytes(&bytes).expect("Header parsing failed");
        assert_eq!(decoded.magic, OMNIRIP_MAGIC);
        assert_eq!(decoded.sequence, 42);
        assert_eq!(decoded.sample_rate, 48000);
        assert_eq!(decoded.frame_count, 256);
    }
}
