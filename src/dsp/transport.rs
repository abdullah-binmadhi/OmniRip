//! Audio transport into the engine.
//!
//! The engine accepts live stereo float audio on two listeners:
//! - a Unix domain socket at `/tmp/omnirip_audio.sock` for native clients (`omnirip feed`, `omnirip stream`);
//! - TCP on 127.0.0.1:49152, which takes the same packets from native clients and WebSocket binary
//!   messages from the browser bridge scripts.
//!
//! A packet is a 16-byte little-endian header followed by interleaved f32 stereo frames. The header is
//! validated before any payload is read, so a client cannot force a large allocation.

use super::servo::ServoWriter;
use std::fs;
use std::io::{self, Read, Write};
#[cfg(unix)]
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

pub const OMNIRIP_SOCKET_PATH: &str = "/tmp/omnirip_audio.sock";
pub const OMNIRIP_TCP_PORT: u16 = 49152;
pub const OMNIRIP_MAGIC: u32 = 0x4F4D4E49; // "OMNI" in ASCII
/// Most frames one packet may carry. Matches the engine's 2048-frame block size.
pub const MAX_FRAMES_PER_PACKET: u16 = 2048;
pub const MIN_SAMPLE_RATE: u32 = 8_000;
pub const MAX_SAMPLE_RATE: u32 = 384_000;
/// Clients served at the same time, across both listeners.
pub const MAX_CLIENTS: usize = 8;
/// One stereo frame on the wire: two little-endian f32 samples.
const FRAME_BYTES: usize = 8;

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

    /// Reads the header from the first 16 bytes. Returns `None` when the slice is too short or the magic is wrong.
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

    /// Checks every field that came from the network. Run this before reading any payload.
    pub fn validate(&self) -> Result<(), PacketError> {
        if self.magic != OMNIRIP_MAGIC {
            return Err(PacketError::BadMagic);
        }
        if self.channels != 2 {
            return Err(PacketError::BadChannels(self.channels));
        }
        if self.frame_count == 0 || self.frame_count > MAX_FRAMES_PER_PACKET {
            return Err(PacketError::BadFrameCount(self.frame_count));
        }
        if !(MIN_SAMPLE_RATE..=MAX_SAMPLE_RATE).contains(&self.sample_rate) {
            return Err(PacketError::BadSampleRate(self.sample_rate));
        }
        Ok(())
    }
}

/// Why a packet was refused.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PacketError {
    Truncated,
    BadMagic,
    BadChannels(u16),
    BadFrameCount(u16),
    BadSampleRate(u32),
    PayloadLength { expected: usize, actual: usize },
}

impl std::fmt::Display for PacketError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PacketError::Truncated => write!(f, "packet is shorter than its header"),
            PacketError::BadMagic => write!(f, "packet does not start with the OMNI magic"),
            PacketError::BadChannels(channels) => {
                write!(f, "packet has {channels} channels, expected 2")
            }
            PacketError::BadFrameCount(count) => {
                write!(
                    f,
                    "frame count {count} is outside 1..={MAX_FRAMES_PER_PACKET}"
                )
            }
            PacketError::BadSampleRate(rate) => {
                write!(
                    f,
                    "sample rate {rate} Hz is outside {MIN_SAMPLE_RATE}..={MAX_SAMPLE_RATE}"
                )
            }
            PacketError::PayloadLength { expected, actual } => {
                write!(f, "payload is {actual} bytes, expected {expected}")
            }
        }
    }
}

/// Parses and validates the header at the start of `bytes`.
fn parse_header(bytes: &[u8]) -> Result<AudioPacketHeader, PacketError> {
    if bytes.len() < AudioPacketHeader::SIZE {
        return Err(PacketError::Truncated);
    }
    let header = AudioPacketHeader::from_bytes(bytes).ok_or(PacketError::BadMagic)?;
    header.validate()?;
    Ok(header)
}

fn frame_from_bytes(chunk: &[u8; FRAME_BYTES]) -> [f32; 2] {
    [
        f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]),
        f32::from_le_bytes([chunk[4], chunk[5], chunk[6], chunk[7]]),
    ]
}

/// Decodes one complete packet (header plus payload) into stereo frames.
pub fn decode_packet(bytes: &[u8]) -> Result<Vec<[f32; 2]>, PacketError> {
    let header = parse_header(bytes)?;
    let payload = &bytes[AudioPacketHeader::SIZE..];
    let expected = header.frame_count as usize * FRAME_BYTES;
    if payload.len() != expected {
        return Err(PacketError::PayloadLength {
            expected,
            actual: payload.len(),
        });
    }
    Ok(payload
        .as_chunks::<FRAME_BYTES>()
        .0
        .iter()
        .map(frame_from_bytes)
        .collect())
}

/// Moves every complete stereo frame out of `carry` and keeps a trailing partial frame for the next read.
/// Pipes return any byte count, so a read can end in the middle of a frame.
pub fn take_whole_frames(carry: &mut Vec<u8>) -> Vec<[f32; 2]> {
    let whole = carry.len() / FRAME_BYTES * FRAME_BYTES;
    let frames = carry[..whole]
        .as_chunks::<FRAME_BYTES>()
        .0
        .iter()
        .map(frame_from_bytes)
        .collect();
    carry.drain(..whole);
    frames
}

/// Where decoded frames go. Shared by every client.
#[derive(Clone)]
struct FrameSink {
    writer: Arc<Mutex<ServoWriter>>,
    packets: Arc<AtomicU64>,
    frames: Arc<AtomicU64>,
}

impl FrameSink {
    fn push(&self, frames: &[[f32; 2]]) {
        if let Ok(mut writer) = self.writer.lock() {
            writer.write(frames);
        }
        self.packets.fetch_add(1, Ordering::Relaxed);
        self.frames
            .fetch_add(frames.len() as u64, Ordering::Relaxed);
    }
}

/// Serves native clients: each packet is a header followed by exactly `frame_count` frames.
fn serve_raw<R: Read>(stream: &mut R, running: &AtomicBool, sink: &FrameSink) {
    // Sized for the largest valid packet once, so reading a payload never allocates.
    let mut packet =
        vec![0u8; AudioPacketHeader::SIZE + MAX_FRAMES_PER_PACKET as usize * FRAME_BYTES];
    while running.load(Ordering::SeqCst) {
        if stream
            .read_exact(&mut packet[..AudioPacketHeader::SIZE])
            .is_err()
        {
            break;
        }
        let header = match parse_header(&packet[..AudioPacketHeader::SIZE]) {
            Ok(header) => header,
            Err(_) => break,
        };
        let total = AudioPacketHeader::SIZE + header.frame_count as usize * FRAME_BYTES;
        if stream
            .read_exact(&mut packet[AudioPacketHeader::SIZE..total])
            .is_err()
        {
            break;
        }
        match decode_packet(&packet[..total]) {
            Ok(frames) => sink.push(&frames),
            Err(_) => break,
        }
    }
}

/// Serves a browser bridge: each WebSocket binary message carries one packet.
fn serve_websocket(stream: std::net::TcpStream, running: &AtomicBool, sink: &FrameSink) {
    let mut socket = match tungstenite::accept(stream) {
        Ok(socket) => socket,
        Err(_) => return,
    };
    while running.load(Ordering::SeqCst) {
        match socket.read() {
            Ok(tungstenite::Message::Binary(data)) => match decode_packet(&data) {
                Ok(frames) => sink.push(&frames),
                Err(_) => break,
            },
            Ok(tungstenite::Message::Close(_)) | Err(_) => break,
            Ok(_) => {}
        }
    }
}

/// Sends a TCP connection to the WebSocket or native handler, based on its first bytes.
fn serve_tcp_client(mut stream: std::net::TcpStream, running: &AtomicBool, sink: &FrameSink) {
    let mut probe = [0u8; 4];
    let is_websocket = matches!(stream.peek(&mut probe), Ok(4)) && &probe == b"GET ";
    if is_websocket {
        serve_websocket(stream, running, sink);
    } else {
        serve_raw(&mut stream, running, sink);
    }
}

/// Runs `serve` on its own thread and counts it against `MAX_CLIENTS` while it runs.
fn spawn_client<S, F>(clients: &Arc<AtomicUsize>, name: &str, stream: S, serve: F)
where
    S: Send + 'static,
    F: FnOnce(S) + Send + 'static,
{
    clients.fetch_add(1, Ordering::SeqCst);
    let counter = Arc::clone(clients);
    let spawned = thread::Builder::new()
        .name(name.to_string())
        .spawn(move || {
            serve(stream);
            counter.fetch_sub(1, Ordering::SeqCst);
        });
    if spawned.is_err() {
        clients.fetch_sub(1, Ordering::SeqCst);
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

    /// Starts the Unix socket and TCP listeners. Calling this while already running does nothing.
    pub fn start(&self) -> io::Result<()> {
        if self.is_running.swap(true, Ordering::SeqCst) {
            return Ok(());
        }
        let sink = FrameSink {
            writer: Arc::clone(&self.writer),
            packets: Arc::clone(&self.total_packets),
            frames: Arc::clone(&self.total_frames),
        };

        #[cfg(unix)]
        {
            let _ = fs::remove_file(OMNIRIP_SOCKET_PATH);
            if let Ok(listener) = UnixListener::bind(OMNIRIP_SOCKET_PATH) {
                let _ = listener.set_nonblocking(true);
                let running = Arc::clone(&self.is_running);
                let clients = Arc::clone(&self.active_clients);
                let sink = sink.clone();
                thread::Builder::new()
                    .name("omnirip-ipc-transport".to_string())
                    .spawn(move || {
                        while running.load(Ordering::SeqCst) {
                            match listener.accept() {
                                Ok((stream, _)) => {
                                    if clients.load(Ordering::SeqCst) >= MAX_CLIENTS {
                                        continue; // dropping the stream refuses the client
                                    }
                                    let _ = stream.set_nonblocking(false);
                                    let (running, sink) = (Arc::clone(&running), sink.clone());
                                    spawn_client(
                                        &clients,
                                        "omnirip-ipc-client",
                                        stream,
                                        move |mut stream| {
                                            serve_raw(&mut stream, &running, &sink);
                                        },
                                    );
                                }
                                Err(ref e)
                                    if e.kind() == io::ErrorKind::WouldBlock
                                        || e.kind() == io::ErrorKind::Interrupted =>
                                {
                                    thread::sleep(Duration::from_millis(5));
                                }
                                Err(e) => {
                                    eprintln!("omnirip-ipc-transport accept error: {}", e);
                                    break;
                                }
                            }
                        }
                        let _ = fs::remove_file(OMNIRIP_SOCKET_PATH);
                    })?;
            }
        }

        let listener = std::net::TcpListener::bind(("127.0.0.1", OMNIRIP_TCP_PORT))?;
        let _ = listener.set_nonblocking(true);
        let running = Arc::clone(&self.is_running);
        let clients = Arc::clone(&self.active_clients);
        thread::Builder::new()
            .name("omnirip-tcp-transport".to_string())
            .spawn(move || {
                while running.load(Ordering::SeqCst) {
                    match listener.accept() {
                        Ok((stream, _)) => {
                            if clients.load(Ordering::SeqCst) >= MAX_CLIENTS {
                                continue;
                            }
                            let _ = stream.set_nonblocking(false);
                            let (running, sink) = (Arc::clone(&running), sink.clone());
                            spawn_client(&clients, "omnirip-tcp-client", stream, move |stream| {
                                serve_tcp_client(stream, &running, &sink);
                            });
                        }
                        Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                            thread::sleep(Duration::from_millis(10));
                        }
                        Err(_) => break,
                    }
                }
            })?;
        Ok(())
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
        for chunk in frames.chunks(512) {
            let header =
                AudioPacketHeader::new(self.sequence, self.sample_rate, chunk.len() as u16);
            self.sequence = self.sequence.wrapping_add(1);

            let mut packet =
                Vec::with_capacity(AudioPacketHeader::SIZE + chunk.len() * FRAME_BYTES);
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
        let mut buf = [0u8; 512 * FRAME_BYTES];
        let mut carry: Vec<u8> = Vec::with_capacity(512 * FRAME_BYTES);
        let mut total_frames = 0u64;

        loop {
            let bytes_read = match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => n,
                Err(ref e) if e.kind() == io::ErrorKind::Interrupted => continue,
                Err(e) => return Err(e),
            };
            carry.extend_from_slice(&buf[..bytes_read]);
            let frames = take_whole_frames(&mut carry);
            if frames.is_empty() {
                continue;
            }
            self.send_frames(&frames)?;
            total_frames += frames.len() as u64;

            // Pace at ~95% of real time to prevent buffer starvation while avoiding overflow
            let sleep_micros = (frames.len() as u64 * 1_000_000) / (self.sample_rate.max(1) as u64);
            std::thread::sleep(Duration::from_micros(sleep_micros * 95 / 100));
        }
        Ok(total_frames)
    }
}

/// Helper function to handle `omnirip feed` CLI execution.
pub fn run_feed_cli(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    println!(
        "[OmniRip Feeder] Checking for running OmniRip audio engine at {}...",
        OMNIRIP_SOCKET_PATH
    );
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
            streamer
                .start()
                .map_err(|e| format!("Failed to initialize audio engine: {}", e))?;
            std::thread::sleep(Duration::from_millis(100));
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

    println!(
        "[OmniRip Feeder] Stream completed! Total frames fed: {}",
        total
    );
    Ok(())
}

/// Helper function to handle `omnirip stream <url>` CLI execution.
pub fn run_stream_cli(url: &str) -> Result<(), Box<dyn std::error::Error>> {
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return Err("omnirip stream expects an http:// or https:// URL".into());
    }
    println!(
        "[OmniRip Streamer] Checking for running OmniRip audio engine at {}...",
        OMNIRIP_SOCKET_PATH
    );
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
            streamer
                .start()
                .map_err(|e| format!("Failed to initialize audio engine: {}", e))?;
            std::thread::sleep(Duration::from_millis(100));
            let client = IpcAudioClient::connect()?;
            _standalone_streamer = Some(streamer);
            println!("[OmniRip Streamer] Dedicated hardware audio stream initialized!");
            client
        }
    };
    println!(
        "[OmniRip Streamer] Resolving high-res audio stream via yt-dlp for: {}",
        url
    );

    // No shell is involved: each tool gets its arguments as separate argv entries, so the URL cannot be
    // read as shell syntax.
    let mut yt_dlp = Command::new("yt-dlp")
        .args(["-f", "bestaudio", "-o", "-", "--", url])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;
    let yt_out = yt_dlp
        .stdout
        .take()
        .ok_or("Failed to capture yt-dlp output")?;
    let mut ffmpeg = Command::new("ffmpeg")
        .args([
            "-loglevel",
            "error",
            "-i",
            "-",
            "-f",
            "f32le",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-",
        ])
        .stdin(yt_out)
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()?;
    let ff_out = ffmpeg
        .stdout
        .take()
        .ok_or("Failed to capture ffmpeg output")?;

    println!("[OmniRip Streamer] Streaming live audio directly into 64-bit EQ pipeline...");
    let result = client.stream_from_raw_pcm_reader(ff_out);
    let _ = ffmpeg.kill();
    let _ = yt_dlp.kill();
    let _ = ffmpeg.wait();
    let _ = yt_dlp.wait();
    let total = result?;
    println!(
        "[OmniRip Streamer] Stream finished! Total frames played: {}",
        total
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn packet_bytes(sample_rate: u32, frames: &[[f32; 2]]) -> Vec<u8> {
        let header = AudioPacketHeader::new(7, sample_rate, frames.len() as u16);
        let mut bytes = Vec::with_capacity(AudioPacketHeader::SIZE + frames.len() * FRAME_BYTES);
        bytes.extend_from_slice(&header.magic.to_le_bytes());
        bytes.extend_from_slice(&header.sequence.to_le_bytes());
        bytes.extend_from_slice(&header.sample_rate.to_le_bytes());
        bytes.extend_from_slice(&header.channels.to_le_bytes());
        bytes.extend_from_slice(&header.frame_count.to_le_bytes());
        for [left, right] in frames {
            bytes.extend_from_slice(&left.to_le_bytes());
            bytes.extend_from_slice(&right.to_le_bytes());
        }
        bytes
    }

    fn test_sink() -> (FrameSink, Arc<AtomicU64>, Arc<AtomicU64>) {
        let (writer, _reader) = crate::dsp::servo::create_servo_ring_buffer(4096, 256);
        let packets = Arc::new(AtomicU64::new(0));
        let frames = Arc::new(AtomicU64::new(0));
        let sink = FrameSink {
            writer: Arc::new(Mutex::new(writer)),
            packets: Arc::clone(&packets),
            frames: Arc::clone(&frames),
        };
        (sink, packets, frames)
    }

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

    #[test]
    fn decode_round_trips_stereo_frames() {
        let frames = [[0.25f32, -0.5], [1.0, 0.0]];
        let decoded = decode_packet(&packet_bytes(48_000, &frames)).expect("valid packet");
        assert_eq!(decoded, frames.to_vec());
    }

    #[test]
    fn oversized_frame_count_is_rejected_before_any_payload_is_read() {
        let header = AudioPacketHeader::new(0, 48_000, u16::MAX);
        assert_eq!(header.validate(), Err(PacketError::BadFrameCount(u16::MAX)));
    }

    #[test]
    fn empty_and_non_stereo_packets_are_rejected() {
        assert_eq!(
            AudioPacketHeader::new(0, 48_000, 0).validate(),
            Err(PacketError::BadFrameCount(0))
        );
        let mut mono = AudioPacketHeader::new(0, 48_000, 16);
        mono.channels = 1;
        assert_eq!(mono.validate(), Err(PacketError::BadChannels(1)));
    }

    #[test]
    fn implausible_sample_rates_are_rejected() {
        assert_eq!(
            AudioPacketHeader::new(0, 0, 16).validate(),
            Err(PacketError::BadSampleRate(0))
        );
    }

    #[test]
    fn truncated_payload_is_rejected() {
        let mut bytes = packet_bytes(48_000, &[[0.0, 0.0]; 4]);
        bytes.truncate(bytes.len() - 8);
        assert_eq!(
            decode_packet(&bytes),
            Err(PacketError::PayloadLength {
                expected: 32,
                actual: 24
            })
        );
    }

    #[test]
    fn wrong_magic_is_rejected() {
        let mut bytes = packet_bytes(48_000, &[[0.0, 0.0]]);
        bytes[0] ^= 0xFF;
        assert_eq!(decode_packet(&bytes), Err(PacketError::BadMagic));
    }

    #[test]
    fn partial_frames_wait_for_the_rest_of_their_bytes() {
        let mut frame = Vec::new();
        frame.extend_from_slice(&0.25f32.to_le_bytes());
        frame.extend_from_slice(&(-0.5f32).to_le_bytes());

        let mut carry = frame[..5].to_vec(); // a read that ends mid-frame
        assert!(take_whole_frames(&mut carry).is_empty());
        assert_eq!(carry.len(), 5);

        carry.extend_from_slice(&frame[5..]); // the rest arrives with the next read
        assert_eq!(take_whole_frames(&mut carry), vec![[0.25, -0.5]]);
        assert!(carry.is_empty());
    }

    #[test]
    fn native_clients_deliver_packets_until_the_stream_ends() {
        let (sink, packets, frames) = test_sink();
        let mut stream = std::io::Cursor::new(
            [
                packet_bytes(48_000, &[[0.0, 0.0]; 5]),
                packet_bytes(48_000, &[[0.0, 0.0]; 2]),
            ]
            .concat(),
        );
        serve_raw(&mut stream, &AtomicBool::new(true), &sink);
        assert_eq!(packets.load(Ordering::SeqCst), 2);
        assert_eq!(frames.load(Ordering::SeqCst), 7);
    }

    #[test]
    fn websocket_clients_deliver_packets_to_the_engine() {
        let (sink, packets, frames) = test_sink();
        let running = Arc::new(AtomicBool::new(true));
        let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind a test port");
        let port = listener.local_addr().expect("local address").port();
        let server = {
            let running = Arc::clone(&running);
            thread::spawn(move || {
                let (stream, _) = listener.accept().expect("accept browser client");
                serve_tcp_client(stream, &running, &sink);
            })
        };

        let (mut socket, _response) =
            tungstenite::connect(format!("ws://127.0.0.1:{port}")).expect("websocket handshake");
        let payload = packet_bytes(48_000, &[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]);
        socket
            .send(tungstenite::Message::Binary(payload.into()))
            .expect("send packet");
        drop(socket);
        server.join().expect("server thread");

        assert_eq!(packets.load(Ordering::SeqCst), 1);
        assert_eq!(frames.load(Ordering::SeqCst), 3);
    }
}
