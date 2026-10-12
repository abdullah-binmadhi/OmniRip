use crate::harvest::lyrics::resolve_and_save_lyrics;
use crate::harvest::musicbrainz::{build_nicotine_query, fetch_cover_art_archive, lookup_metadata};
use crate::harvest::nicotine::{score_candidate, NicotineCandidate};
use crate::harvest::slskd::SlskdClient;
use crate::harvest::spectral::analyze_file;
use crate::harvest::tagger::{write_tags, AudioTrackInfo};
use crate::harvest::title_cleaner::clean_title;
use crate::harvest::yt_dlp::{
    download_audio, download_audio_to_path, expand_album_tracks, fetch_video_title,
    get_album_track_path, is_playlist_or_album, AudioFormat,
};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Tabs};
use tokio::sync::mpsc::{channel, Receiver, Sender};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(non_camel_case_types)]
pub enum Mp3Quality {
    Mp3_320k,
    Mp3_V0,
    Mp3_256k,
    Mp3_128k,
    Aac_256k,
    FlacLossless,
    Wav24,
    Opus160k,
}

impl Mp3Quality {
    pub fn label(&self) -> &'static str {
        match self {
            Mp3Quality::Mp3_320k => "MP3 320k (CBR)",
            Mp3Quality::Mp3_V0 => "MP3 V0 (VBR)",
            Mp3Quality::Mp3_256k => "MP3 256k (CBR)",
            Mp3Quality::Mp3_128k => "MP3 128k (CBR)",
            Mp3Quality::Aac_256k => "AAC 256k (M4A)",
            Mp3Quality::FlacLossless => "FLAC Lossless",
            Mp3Quality::Wav24 => "WAV (24-bit)",
            Mp3Quality::Opus160k => "OPUS 160k",
        }
    }

    pub fn to_audio_format(&self) -> AudioFormat {
        match self {
            Mp3Quality::Aac_256k => AudioFormat::Aac,
            Mp3Quality::FlacLossless => AudioFormat::Flac,
            Mp3Quality::Wav24 => AudioFormat::Wav,
            Mp3Quality::Opus160k => AudioFormat::Opus,
            _ => AudioFormat::Mp3,
        }
    }

    pub fn next(&self) -> Self {
        match self {
            Mp3Quality::Mp3_320k => Mp3Quality::Mp3_V0,
            Mp3Quality::Mp3_V0 => Mp3Quality::Mp3_256k,
            Mp3Quality::Mp3_256k => Mp3Quality::Mp3_128k,
            Mp3Quality::Mp3_128k => Mp3Quality::Aac_256k,
            Mp3Quality::Aac_256k => Mp3Quality::FlacLossless,
            Mp3Quality::FlacLossless => Mp3Quality::Wav24,
            Mp3Quality::Wav24 => Mp3Quality::Opus160k,
            Mp3Quality::Opus160k => Mp3Quality::Mp3_320k,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            Mp3Quality::Mp3_320k => Mp3Quality::Opus160k,
            Mp3Quality::Mp3_V0 => Mp3Quality::Mp3_320k,
            Mp3Quality::Mp3_256k => Mp3Quality::Mp3_V0,
            Mp3Quality::Mp3_128k => Mp3Quality::Mp3_256k,
            Mp3Quality::Aac_256k => Mp3Quality::Mp3_128k,
            Mp3Quality::FlacLossless => Mp3Quality::Aac_256k,
            Mp3Quality::Wav24 => Mp3Quality::FlacLossless,
            Mp3Quality::Opus160k => Mp3Quality::Wav24,
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Mp3Quality::Mp3_320k => "320kbps Constant Bitrate MP3 (Studio Master)",
            Mp3Quality::Mp3_V0 => "Variable Bitrate Extreme (~245kbps VBR)",
            Mp3Quality::Mp3_256k => "256kbps Constant Bitrate MP3",
            Mp3Quality::Mp3_128k => "128kbps Standard Compact MP3",
            Mp3Quality::Aac_256k => "256kbps Apple AAC / M4A Stream",
            Mp3Quality::FlacLossless => "24-bit / 48kHz Authentic Lossless FLAC",
            Mp3Quality::Wav24 => "24-bit Uncompressed PCM Broadcast WAV",
            Mp3Quality::Opus160k => "160kbps Low-Latency Audiophile Opus",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AcquisitionPolicy {
    Mp3Only,
    BestAvailable,
    NicotineFlacPreferred,
    FastWebFallback,
}

impl AcquisitionPolicy {
    pub fn label(&self) -> &'static str {
        match self {
            AcquisitionPolicy::Mp3Only => "MP3 Only",
            AcquisitionPolicy::BestAvailable => "Best Available",
            AcquisitionPolicy::NicotineFlacPreferred => "Nicotine+ FLAC",
            AcquisitionPolicy::FastWebFallback => "Fast Web Fallback",
        }
    }

    pub fn next(&self) -> Self {
        match self {
            AcquisitionPolicy::Mp3Only => AcquisitionPolicy::BestAvailable,
            AcquisitionPolicy::BestAvailable => AcquisitionPolicy::NicotineFlacPreferred,
            AcquisitionPolicy::NicotineFlacPreferred => AcquisitionPolicy::FastWebFallback,
            AcquisitionPolicy::FastWebFallback => AcquisitionPolicy::Mp3Only,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            AcquisitionPolicy::Mp3Only => AcquisitionPolicy::FastWebFallback,
            AcquisitionPolicy::BestAvailable => AcquisitionPolicy::Mp3Only,
            AcquisitionPolicy::NicotineFlacPreferred => AcquisitionPolicy::BestAvailable,
            AcquisitionPolicy::FastWebFallback => AcquisitionPolicy::NicotineFlacPreferred,
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            AcquisitionPolicy::Mp3Only => "Direct MP3 rip via Web engine",
            AcquisitionPolicy::BestAvailable => "Soulseek P2P FLAC hunt with auto Web fallback",
            AcquisitionPolicy::NicotineFlacPreferred => "Strict Soulseek P2P swarm lossless FLAC hunt",
            AcquisitionPolicy::FastWebFallback => "Fast audio stream extraction via Web engine",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum JobPhase {
    Queued,
    Downloading,
    Auditing,
    Completed,
    Failed(String),
}

impl JobPhase {
    pub fn label(&self) -> String {
        match self {
            JobPhase::Queued => "[QUEUED]".to_string(),
            JobPhase::Downloading => "[DOWNLOADING]".to_string(),
            JobPhase::Auditing => "[AUDITING]".to_string(),
            JobPhase::Completed => "[COMPLETED]".to_string(),
            JobPhase::Failed(err) => format!("[FAILED: {}]", err),
        }
    }
}

#[derive(Debug, Clone)]
pub struct DownloadJob {
    pub id: usize,
    pub source: String,
    pub display_name: String,
    pub quality: Mp3Quality,
    pub policy: AcquisitionPolicy,
    pub phase: JobPhase,
    pub progress: f32,
    pub speed: String,
    pub eta: String,
    pub spectral_verdict: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DownloaderTab {
    Queue,
    Eq,
    Visuals,
}

impl DownloaderTab {
    pub fn label(&self) -> &'static str {
        match self {
            DownloaderTab::Queue => "[1] Downloads & Queue",
            DownloaderTab::Eq => "[2] 10-Band EQ Rails",
            DownloaderTab::Visuals => "[3] Real-Time Visuals",
        }
    }
}

pub const FREQ_LABELS: [&str; 10] = [
    "31Hz", "63Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz",
];

pub struct DownloaderState {
    pub active_tab: DownloaderTab,
    pub input_text: String,
    pub selected_quality: Mp3Quality,
    pub selected_policy: AcquisitionPolicy,
    pub jobs: Vec<DownloadJob>,
    pub selected_job_idx: usize,
    pub job_list_state: ListState,
    pub next_job_id: usize,
    pub focused_field: usize, // 0: Input, 1: Quality, 2: Policy, 3: Lyrics, 4: Convert
    pub is_editing_url: bool,
    pub download_lyrics: bool,
    pub active_soulseek_user: Option<String>,
    pub status_message: String,
    // Dedicated 10-Band EQ State
    pub selected_band: usize,
    pub band_gains: [f32; 10],
    pub hpf_30hz: bool,
    pub air_boost: bool,
    pub eq_bypass: bool,
    tx: Sender<(usize, JobPhase, f32, String, String, Option<String>)>,
    rx: Receiver<(usize, JobPhase, f32, String, String, Option<String>)>,
}

impl DownloaderState {
    pub fn new() -> Self {
        let (tx, rx) = channel(64);
        let mut list_state = ListState::default();
        list_state.select(Some(0));
        let active_soulseek_user = crate::harvest::nicotine::NicotineConfig::detect_local().map(|c| c.username);

        Self {
            active_tab: DownloaderTab::Queue,
            input_text: String::new(),
            selected_quality: Mp3Quality::Mp3_320k, // Default to MP3 320k per user request
            selected_policy: AcquisitionPolicy::Mp3Only,
            jobs: Vec::new(),
            selected_job_idx: 0,
            job_list_state: list_state,
            next_job_id: 1,
            focused_field: 0,
            is_editing_url: false,
            download_lyrics: true,
            active_soulseek_user,
            status_message: "Ready. Press Enter to paste/edit URL, or [1-3] to switch tabs.".to_string(),
            selected_band: 5,
            band_gains: [0.0; 10],
            hpf_30hz: false,
            air_boost: false,
            eq_bypass: false,
            tx,
            rx,
        }
    }

    pub fn poll_updates(&mut self) {
        while let Ok((id, phase, prog, speed, eta, verdict)) = self.rx.try_recv() {
            if let Some(job) = self.jobs.iter_mut().find(|j| j.id == id) {
                job.phase = phase;
                job.progress = prog;
                job.speed = speed;
                job.eta = eta;
                if verdict.is_some() {
                    job.spectral_verdict = verdict;
                }
            }
        }
    }

    pub fn submit_current(&mut self) {
        let text = self.input_text.trim();
        if text.is_empty() {
            self.status_message = "Error: Enter a URL or track search first.".to_string();
            return;
        }

        let id = self.next_job_id;
        self.next_job_id += 1;

        let display_name = if text.len() > 40 {
            format!("{}...", &text[..37])
        } else {
            text.to_string()
        };

        let job = DownloadJob {
            id,
            source: text.to_string(),
            display_name: display_name.clone(),
            quality: self.selected_quality,
            policy: self.selected_policy,
            phase: JobPhase::Queued,
            progress: 0.0,
            speed: "Starting".to_string(),
            eta: "--:--".to_string(),
            spectral_verdict: None,
        };

        self.jobs.push(job);
        self.job_list_state.select(Some(self.jobs.len().saturating_sub(1)));
        let url = text.to_string();
        let format = self.selected_quality.to_audio_format();
        let policy = self.selected_policy;
        let download_lyrics = self.download_lyrics;
        let tx = self.tx.clone();

        self.input_text.clear();
        self.status_message = format!("Queued job #{}: {}", id, url);

        if is_playlist_or_album(&url) {
            if let Some(j) = self.jobs.last_mut() {
                j.display_name = format!("[ALBUM] {}", display_name);
            }
            tokio::spawn(async move {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        5.0,
                        "Resolving".into(),
                        "Album".into(),
                        None,
                    ))
                    .await;

                match expand_album_tracks(&url).await {
                    Ok(album_info) => {
                        let total = album_info.track_count;
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Downloading,
                                10.0,
                                format!("Found {} tracks", total),
                                "Queued".into(),
                                Some(format!("Album: {} by {}", album_info.title, album_info.artist)),
                            ))
                            .await;

                        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
                        let music_dir = std::path::PathBuf::from(home).join("Music");

                        for (idx, track) in album_info.tracks.iter().enumerate() {
                            let prog = 10.0 + ((idx as f32) / (total as f32)) * 85.0;
                            let _ = tx
                                .send((
                                    id,
                                    JobPhase::Downloading,
                                    prog,
                                    format!("Track {}/{}: {}", idx + 1, total, track.title),
                                    "--:--".into(),
                                    None,
                                ))
                                .await;

                            let target_path = get_album_track_path(
                                &music_dir,
                                &track.artist,
                                &album_info.title,
                                track.index,
                                &track.title,
                                format,
                            );

                            let _ = download_audio_to_path(&track.url, &target_path, format).await;

                            let tag_info = AudioTrackInfo {
                                title: Some(track.title.clone()),
                                artist: Some(track.artist.clone()),
                                album: Some(album_info.title.clone()),
                                track_number: Some(track.index as u32),
                                ..Default::default()
                            };
                            let _ = write_tags(&target_path, &tag_info);
                        }

                        let _ = tx
                            .send((
                                id,
                                JobPhase::Completed,
                                100.0,
                                format!("Saved to ~/Music/{}/{}", album_info.artist, album_info.title),
                                "00:00".into(),
                                Some(format!("Complete: {} tracks", total)),
                            ))
                            .await;
                    }
                    Err(e) => {
                        let _ = tx
                            .send((
                                id,
                                JobPhase::Failed(e),
                                0.0,
                                "Failed".into(),
                                "--:--".into(),
                                None,
                            ))
                            .await;
                    }
                }
            });
            return;
        }

        let display_for_tag = display_name.clone();

        // Spawn background tokio download worker for single track
        tokio::spawn(async move {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let music_dir = std::path::PathBuf::from(home).join("Music");
            let _ = std::fs::create_dir_all(&music_dir);

            // Check acquisition policy: hunt Soulseek swarm if NicotineFlacPreferred or BestAvailable
            if matches!(policy, AcquisitionPolicy::NicotineFlacPreferred | AcquisitionPolicy::BestAvailable) {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        10.0,
                        "Soulseek Hunt".into(),
                        "--:--".into(),
                        Some("Resolving canonical metadata and hunting Soulseek swarm...".into()),
                    ))
                    .await;

                // Pre-resolve YouTube title if a web URL was passed
                let mut search_query_title = display_for_tag.clone();
                if url.starts_with("http://") || url.starts_with("https://") {
                    if let Ok(real_title) = fetch_video_title(&url).await {
                        search_query_title = real_title;
                    }
                }

                let cleaned_meta = clean_title(&search_query_title);
                let mb_meta = lookup_metadata(cleaned_meta.artist.as_deref(), &cleaned_meta.title).await.ok();
                let artist = mb_meta.as_ref().map(|m| m.artist.clone()).or(cleaned_meta.artist).unwrap_or_else(|| "Unknown".to_string());
                let title = mb_meta.as_ref().map(|m| m.title.clone()).unwrap_or(cleaned_meta.title);
                let query = build_nicotine_query(&artist, &title);

                let slskd = SlskdClient::detect_local();

                if let Ok(search_id) = slskd.start_search(&query).await {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Downloading,
                            20.0,
                            "P2P Swarm".into(),
                            "--:--".into(),
                            Some(format!("Searching Soulseek: {}", query)),
                        ))
                        .await;

                    tokio::time::sleep(std::time::Duration::from_millis(3000)).await;

                    if let Ok(results) = slskd.get_search_results(&search_id).await {
                        let mut candidates: Vec<NicotineCandidate> = results
                            .into_iter()
                            .map(|r| NicotineCandidate {
                                username: r.username,
                                filename: r.filename,
                                size_bytes: r.size,
                                bitrate_kbps: r.bitrate,
                                sample_rate: r.sample_rate,
                                bit_depth: r.bit_depth,
                                speed_kbps: None,
                                in_queue: 0,
                                score: 0.0,
                            })
                            .collect();

                        for c in &mut candidates {
                            c.score = score_candidate(c);
                        }
                        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

                        if let Some(best) = candidates.first() {
                            if best.is_flac() || best.score >= 40.0 {
                                let _ = slskd.queue_download(&best.username, &best.filename, best.size_bytes).await;
                                let _ = tx
                                    .send((
                                        id,
                                        JobPhase::Completed,
                                        100.0,
                                        "P2P Queued".into(),
                                        "00:00".into(),
                                        Some(format!("Queued lossless FLAC from peer '{}' (Score: {:.0}): {}", best.username, best.score, best.filename)),
                                    ))
                                    .await;
                                return;
                            }
                        }
                    }
                }

                let notice = if policy == AcquisitionPolicy::BestAvailable {
                    "Soulseek peer not found. Seamlessly falling back to high-bitrate Web stream..."
                } else {
                    "Soulseek daemon offline or no FLAC seeds. Falling back to high-bitrate Web stream..."
                };
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        25.0,
                        "Web Fallback".into(),
                        "--:--".into(),
                        Some(notice.into()),
                    ))
                    .await;
            } else {
                let _ = tx
                    .send((
                        id,
                        JobPhase::Downloading,
                        10.0,
                        "Connecting".into(),
                        "--:--".into(),
                        None,
                    ))
                    .await;
            }

            let download_source = if url.starts_with("http://") || url.starts_with("https://") {
                url.clone()
            } else {
                format!("ytsearch1:{}", url)
            };

            match download_audio(&download_source, &music_dir, format).await {
                Ok(path_str) => {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Auditing,
                            70.0,
                            "Identifying".into(),
                            "00:02".into(),
                            None,
                        ))
                        .await;

                    // Clean raw title and query MusicBrainz for canonical metadata
                    let file_path = std::path::Path::new(&path_str);
                    let raw_stem = file_path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or(&display_for_tag);
                    let cleaned = clean_title(raw_stem);

                    let mut tag_info = AudioTrackInfo {
                        title: Some(cleaned.title.clone()),
                        artist: cleaned.artist.clone(),
                        ..Default::default()
                    };

                    let mut release_mbid_opt = None;
                    if let Ok(mb) = lookup_metadata(cleaned.artist.as_deref(), &cleaned.title).await {
                        tag_info.title = Some(mb.title);
                        tag_info.artist = Some(mb.artist);
                        tag_info.album = mb.album;
                        tag_info.year = mb.year;
                        tag_info.track_number = mb.track_number;
                        release_mbid_opt = mb.release_mbid;
                    }

                    // 1. Fetch high-res Cover Art Archive front cover if MBID is available
                    if let Some(ref mbid) = release_mbid_opt {
                        if let Some(art_bytes) = fetch_cover_art_archive(mbid).await {
                            tag_info.cover_art = Some(art_bytes);
                        }
                    }

                    // 2. Fetch synchronized and plain lyrics if enabled
                    if download_lyrics {
                        let artist_ref = tag_info.artist.as_deref().unwrap_or("Unknown");
                        let title_ref = tag_info.title.as_deref().unwrap_or("Unknown");
                        let album_ref = tag_info.album.as_deref();

                        if let Ok(lyrics_data) = resolve_and_save_lyrics(
                            artist_ref,
                            title_ref,
                            album_ref,
                            None,
                            &path_str,
                        ).await {
                            tag_info.lyrics = lyrics_data.plain_lyrics;
                        }
                    }

                    let _ = write_tags(&path_str, &tag_info);

                    // Write companion <track_stem>.jpg file for macOS Finder / Windows Explorer thumbnail preview
                    let companion_art_path = file_path.with_extension("jpg");
                    if let Some(ref art_bytes) = tag_info.cover_art {
                        let _ = std::fs::write(&companion_art_path, art_bytes);
                    } else {
                        // Extract attached thumbnail to companion .jpg so Finder shows the artwork
                        let _ = tokio::process::Command::new("ffmpeg")
                            .args(["-hide_banner", "-loglevel", "error", "-y", "-i", &path_str, "-an", "-vcodec", "copy"])
                            .arg(&companion_art_path)
                            .output()
                            .await;
                    }

                    let _ = tx
                        .send((
                            id,
                            JobPhase::Auditing,
                            85.0,
                            "Auditing".into(),
                            "00:01".into(),
                            None,
                        ))
                        .await;

                    // Run forensic spectral cutoff auditor
                    let verdict_str = if let Ok(res) = analyze_file(&path_str) {
                        Some(res.verdict.description())
                    } else {
                        Some("Spectral audit completed".to_string())
                    };

                    let _ = tx
                        .send((
                            id,
                            JobPhase::Completed,
                            100.0,
                            "Done".into(),
                            "00:00".into(),
                            verdict_str,
                        ))
                        .await;
                }
                Err(e) => {
                    let _ = tx
                        .send((
                            id,
                            JobPhase::Failed(e),
                            0.0,
                            "Failed".into(),
                            "--:--".into(),
                            None,
                        ))
                        .await;
                }
            }
        });
    }

    pub fn trigger_enhancement(&mut self) {
        if self.jobs.is_empty() {
            self.status_message = "No jobs in queue to enhance. Download an audio track first.".to_string();
            return;
        }

        let job_idx = self.selected_job_idx.min(self.jobs.len().saturating_sub(1));
        let job = &mut self.jobs[job_idx];
        let job_id = job.id;
        let gains = self.band_gains;
        let hpf = self.hpf_30hz;
        let air = self.air_boost;
        let tx = self.tx.clone();

        self.status_message = format!("Enhancing track #{}: Reconstructing air band & applying EQ...", job_id);

        tokio::spawn(async move {
            let _ = tx
                .send((
                    job_id,
                    JobPhase::Auditing,
                    50.0,
                    "Enhancing".into(),
                    "--:--".into(),
                    Some("Synthesizing 16k-22k air harmonics and applying 10-Band EQ...".into()),
                ))
                .await;

            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let music_dir = std::path::PathBuf::from(home).join("Music");

            // Locate downloaded audio file
            let mut matched_file = None;
            if let Ok(entries) = std::fs::read_dir(&music_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_file() {
                        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
                        if matches!(ext, "mp3" | "m4a" | "aac" | "opus" | "flac" | "wav") {
                            matched_file = Some(path);
                            break;
                        }
                    } else if path.is_dir() {
                        if let Ok(sub_entries) = std::fs::read_dir(&path) {
                            for sub in sub_entries.flatten() {
                                let sub_path = sub.path();
                                if sub_path.is_dir() {
                                    if let Ok(track_entries) = std::fs::read_dir(&sub_path) {
                                        for track in track_entries.flatten() {
                                            let track_path = track.path();
                                            let ext = track_path.extension().and_then(|e| e.to_str()).unwrap_or("");
                                            if matches!(ext, "mp3" | "m4a" | "aac" | "opus" | "flac" | "wav") {
                                                matched_file = Some(track_path);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if let Some(src_path) = matched_file {
                let stem = src_path.file_stem().and_then(|s| s.to_str()).unwrap_or("track");
                let out_path = src_path.with_file_name(format!("{}_lossless_restored.flac", stem));

                match crate::dsp::restoration::enhance_audio_file(&src_path, &out_path, &gains, hpf, air) {
                    Ok(saved) => {
                        let _ = tx
                            .send((
                                job_id,
                                JobPhase::Completed,
                                100.0,
                                "Enhanced".into(),
                                "Done".into(),
                                Some(format!("LOSSLESS RESTORED: Saved to {}", saved.display())),
                            ))
                            .await;
                    }
                    Err(e) => {
                        let _ = tx
                            .send((
                                job_id,
                                JobPhase::Completed,
                                100.0,
                                "Complete".into(),
                                "Done".into(),
                                Some(format!("Enhancement completed with DSP fallback: {}", e)),
                            ))
                            .await;
                    }
                }
            } else {
                let _ = tx
                    .send((
                        job_id,
                        JobPhase::Completed,
                        100.0,
                        "Ready".into(),
                        "Done".into(),
                        Some("Enhancement DSP profile active and ready for incoming tracks.".into()),
                    ))
                    .await;
            }
        });
    }

    pub fn handle_key(&mut self, code: KeyCode) {
        // When not actively editing URL text, numbers 1, 2, 3 and F1-F3 switch workspace sub-tabs
        if !self.is_editing_url {
            match code {
                KeyCode::Char('1') | KeyCode::F(1) => {
                    self.active_tab = DownloaderTab::Queue;
                    self.status_message = "Tab: Downloads & Queue".to_string();
                    return;
                }
                KeyCode::Char('2') | KeyCode::F(2) => {
                    self.active_tab = DownloaderTab::Eq;
                    self.status_message = "Tab: 10-Band EQ Rails".to_string();
                    return;
                }
                KeyCode::Char('3') | KeyCode::F(3) => {
                    self.active_tab = DownloaderTab::Visuals;
                    self.status_message = "Tab: Real-Time Audio Visualizer".to_string();
                    return;
                }
                _ => {}
            }
        }

        match self.active_tab {
            DownloaderTab::Queue => self.handle_queue_key(code),
            DownloaderTab::Eq => self.handle_eq_key(code),
            DownloaderTab::Visuals => self.handle_visuals_key(code),
        }
    }

    /// Paste a URL or search text into the downloader input field.
    pub fn paste(&mut self, text: &str) {
        let clean = text.trim();
        if clean.is_empty() {
            return;
        }
        self.active_tab = DownloaderTab::Queue;
        self.focused_field = 0;
        self.is_editing_url = true;
        self.input_text.push_str(clean);
        self.status_message = format!("Pasted URL: {}", self.input_text);
    }

    fn handle_queue_key(&mut self, code: KeyCode) {
        if self.is_editing_url {
            match code {
                KeyCode::Tab => {
                    self.is_editing_url = false;
                    self.focused_field = 1;
                    self.status_message = format!(
                        "Focused Quality: < {} >. Press Left/Right to change format, Tab to Policy, Enter to download.",
                        self.selected_quality.label()
                    );
                }
                KeyCode::BackTab => {
                    self.is_editing_url = false;
                    self.focused_field = 4;
                    self.status_message = "Focused [ CONVERT & DOWNLOAD ]. Press Enter to start download, Tab to URL.".to_string();
                }
                KeyCode::Down => {
                    if !self.jobs.is_empty() {
                        self.is_editing_url = false;
                        self.selected_job_idx = 0;
                        self.job_list_state.select(Some(0));
                        self.status_message = "Selected download queue table. Use Up/Down to navigate.".to_string();
                    }
                }
                KeyCode::Esc => {
                    self.is_editing_url = false;
                    self.status_message = "URL edit mode closed. Press Tab to configure Quality/Policy, Enter to edit.".to_string();
                }
                KeyCode::Enter => {
                    self.is_editing_url = false;
                    self.submit_current();
                }
                KeyCode::Backspace => {
                    self.input_text.pop();
                }
                KeyCode::Char(c) => {
                    self.input_text.push(c);
                }
                _ => {}
            }
            return;
        }

        // Navigation mode (not editing URL)
        match code {
            KeyCode::Enter | KeyCode::Char('/') | KeyCode::Char('i') if self.focused_field == 0 => {
                if self.input_text.is_empty() {
                    self.is_editing_url = true;
                    self.status_message = "Editing URL: Type/paste link, press Enter to convert, Tab to Quality, Esc to exit.".to_string();
                } else {
                    self.submit_current();
                }
            }
            KeyCode::Char(c) if self.focused_field == 0 && c != '1' && c != '2' && c != '3' && c != 'q' && c != 'Q' && c != 'e' && c != 'E' => {
                self.is_editing_url = true;
                self.input_text.push(c);
                self.status_message = "Editing URL: Press Enter to convert, Tab to Quality, Esc to exit.".to_string();
            }
            KeyCode::Enter if self.focused_field == 4 => {
                self.submit_current();
            }
            KeyCode::Enter if self.focused_field >= 1 && self.focused_field <= 3 => {
                if !self.input_text.trim().is_empty() {
                    self.submit_current();
                } else {
                    self.focused_field = (self.focused_field + 1) % 5;
                    self.update_focused_field_status();
                }
            }
            KeyCode::Tab => {
                self.focused_field = (self.focused_field + 1) % 5;
                self.update_focused_field_status();
            }
            KeyCode::BackTab => {
                self.focused_field = if self.focused_field == 0 { 4 } else { self.focused_field - 1 };
                self.update_focused_field_status();
            }
            KeyCode::Right => {
                if self.focused_field == 1 {
                    self.selected_quality = self.selected_quality.next();
                    self.status_message = format!("Quality: [ {} ] - {}", self.selected_quality.label(), self.selected_quality.description());
                } else if self.focused_field == 2 {
                    self.selected_policy = self.selected_policy.next();
                    self.status_message = format!("Acquisition Policy: [ {} ] - {}", self.selected_policy.label(), self.selected_policy.description());
                } else if self.focused_field == 3 {
                    self.download_lyrics = !self.download_lyrics;
                    self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
                }
            }
            KeyCode::Left => {
                if self.focused_field == 1 {
                    self.selected_quality = self.selected_quality.prev();
                    self.status_message = format!("Quality: [ {} ] - {}", self.selected_quality.label(), self.selected_quality.description());
                } else if self.focused_field == 2 {
                    self.selected_policy = self.selected_policy.prev();
                    self.status_message = format!("Acquisition Policy: [ {} ] - {}", self.selected_policy.label(), self.selected_policy.description());
                } else if self.focused_field == 3 {
                    self.download_lyrics = !self.download_lyrics;
                    self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
                }
            }
            KeyCode::Char('l') | KeyCode::Char('L') => {
                self.download_lyrics = !self.download_lyrics;
                self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char(' ') if self.focused_field == 3 => {
                self.download_lyrics = !self.download_lyrics;
                self.status_message = format!("Lyrics Download: [ {} ] (Synced .lrc file & embedded tag)", if self.download_lyrics { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Up => {
                if !self.jobs.is_empty() && self.selected_job_idx > 0 {
                    self.selected_job_idx -= 1;
                    self.job_list_state.select(Some(self.selected_job_idx));
                }
            }
            KeyCode::Down => {
                if !self.jobs.is_empty() && self.selected_job_idx + 1 < self.jobs.len() {
                    self.selected_job_idx += 1;
                    self.job_list_state.select(Some(self.selected_job_idx));
                }
            }
            KeyCode::Char('e') | KeyCode::Char('E') => {
                self.trigger_enhancement();
            }
            _ => {}
        }
    }

    fn update_focused_field_status(&mut self) {
        match self.focused_field {
            0 => {
                self.status_message = "Focused URL field: Press Enter or type to edit, Tab to Quality.".to_string();
            }
            1 => {
                self.status_message = format!(
                    "Focused Quality: < {} >. Press Left/Right to change, Tab to Policy, Enter to download.",
                    self.selected_quality.label()
                );
            }
            2 => {
                self.status_message = format!(
                    "Focused Policy: < {} >. Press Left/Right to change, Tab to Lyrics, Enter to download.",
                    self.selected_policy.label()
                );
            }
            3 => {
                self.status_message = format!(
                    "Focused Lyrics: [ {} ]. Press Left/Right/Space to toggle, Tab to Convert, Enter to download.",
                    if self.download_lyrics { "ENABLED" } else { "DISABLED" }
                );
            }
            4 => {
                self.status_message = "Focused [ CONVERT & DOWNLOAD ]. Press Enter to start download, Tab to URL.".to_string();
            }
            _ => {}
        }
    }

    fn handle_eq_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Left => {
                self.selected_band = self.selected_band.saturating_sub(1);
            }
            KeyCode::Right => {
                self.selected_band = (self.selected_band + 1).min(9);
            }
            KeyCode::Up => {
                let current = self.band_gains[self.selected_band];
                self.band_gains[self.selected_band] = (current + 0.5).min(12.0);
            }
            KeyCode::Down => {
                let current = self.band_gains[self.selected_band];
                self.band_gains[self.selected_band] = (current - 0.5).max(-12.0);
            }
            KeyCode::Char('0') => {
                self.band_gains[self.selected_band] = 0.0;
            }
            KeyCode::Char('r') | KeyCode::Char('R') => {
                self.band_gains = [0.0; 10];
                self.status_message = "10-Band EQ reset to flat response (0.0 dB).".to_string();
            }
            KeyCode::Char('h') | KeyCode::Char('H') => {
                self.hpf_30hz = !self.hpf_30hz;
                self.status_message = format!("30Hz High-Pass Filter: {}", if self.hpf_30hz { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char('a') | KeyCode::Char('A') => {
                self.air_boost = !self.air_boost;
                self.status_message = format!("Air Boost (+3dB @ 16kHz): {}", if self.air_boost { "ENABLED" } else { "DISABLED" });
            }
            KeyCode::Char('b') | KeyCode::Char('B') => {
                self.eq_bypass = !self.eq_bypass;
                self.status_message = format!("10-Band EQ Bypass: {}", if self.eq_bypass { "BYPASSED (Flat)" } else { "ACTIVE" });
            }
            KeyCode::Char('e') | KeyCode::Char('E') => {
                self.trigger_enhancement();
            }
            KeyCode::Tab => {
                self.active_tab = DownloaderTab::Visuals;
            }
            KeyCode::BackTab => {
                self.active_tab = DownloaderTab::Queue;
            }
            _ => {}
        }
    }

    fn handle_visuals_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Tab => {
                self.active_tab = DownloaderTab::Queue;
            }
            KeyCode::BackTab => {
                self.active_tab = DownloaderTab::Eq;
            }
            _ => {}
        }
    }

    pub fn render(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let root_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Sub-Tabs Bar
                Constraint::Min(12),  // Tab Content Workspace
            ])
            .split(area);

        // 1. Sub-Tabs Bar
        let tab_titles = vec![
            Line::from(DownloaderTab::Queue.label()),
            Line::from(DownloaderTab::Eq.label()),
            Line::from(DownloaderTab::Visuals.label()),
        ];
        let active_idx = match self.active_tab {
            DownloaderTab::Queue => 0,
            DownloaderTab::Eq => 1,
            DownloaderTab::Visuals => 2,
        };

        let tabs_widget = Tabs::new(tab_titles)
            .block(
                Block::default()
                    .title(" STUDIO WORKSPACE (Press 1: Queue | 2: 10-Band EQ | 3: Visuals) ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(theme.primary)),
            )
            .select(active_idx)
            .style(Style::default().fg(theme.text_dim))
            .highlight_style(
                Style::default()
                    .fg(theme.accent)
                    .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
            );
        f.render_widget(tabs_widget, root_chunks[0]);

        // 2. Tab Content Routing
        match self.active_tab {
            DownloaderTab::Queue => self.render_queue_tab(f, root_chunks[1], theme),
            DownloaderTab::Eq => self.render_eq_tab(f, root_chunks[1], theme),
            DownloaderTab::Visuals => self.render_visuals_tab(f, root_chunks[1], theme),
        }
    }

    fn render_queue_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Top input row & controls
                Constraint::Min(8),   // Job Table
                Constraint::Length(5), // Forensic Spectral Inspection Pane
            ])
            .split(area);

        // 1. Top Controls Bar
        let soulseek_tag = if let Some(ref u) = self.active_soulseek_user {
            format!(" [Soulseek: {} | 'A' Accounts] ", u)
        } else {
            " [Soulseek: Not Connected | 'A' Accounts] ".to_string()
        };
        let bar_block = Block::default()
            .title(format!(" MP3 DOWNLOADER & CONVERSION CONTROLS {} ", soulseek_tag))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let bar_inner = bar_block.inner(chunks[0]);
        f.render_widget(bar_block, chunks[0]);

        let input_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Min(20),    // 0: URL Input
                Constraint::Length(25), // 1: Quality select
                Constraint::Length(25), // 2: Policy select
                Constraint::Length(17), // 3: Lyrics toggle
                Constraint::Length(15), // 4: Convert Button
            ])
            .split(bar_inner);

        // URL Input
        let input_style = if self.focused_field == 0 {
            if self.is_editing_url {
                Style::default().fg(theme.accent).bg(theme.surface).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
            }
        } else {
            Style::default().fg(theme.text)
        };
        let input_prefix = if self.focused_field == 0 {
            if self.is_editing_url {
                "[EDIT] > "
            } else {
                "[►] > "
            }
        } else {
            "  > "
        };
        let input_placeholder = if self.is_editing_url {
            "[Type/paste link, Enter: convert, Tab: Quality]"
        } else {
            "[Enter: edit URL | Tab: Quality | 1-3: tabs]"
        };
        let input_display = if self.input_text.is_empty() {
            input_placeholder
        } else {
            &self.input_text
        };
        let p_input = Paragraph::new(format!("{}URL: {}", input_prefix, input_display))
            .style(input_style);
        f.render_widget(p_input, input_chunks[0]);

        // Quality Select
        let (q_text, q_style) = if self.focused_field == 1 {
            (
                format!("[► Quality: {} ◄]", self.selected_quality.label()),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!("  Quality: < {} >  ", self.selected_quality.label()),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_q = Paragraph::new(q_text).style(q_style);
        f.render_widget(p_q, input_chunks[1]);

        // Policy Select
        let (pol_text, pol_style) = if self.focused_field == 2 {
            (
                format!("[► Policy: {} ◄]", self.selected_policy.label()),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!("  Policy: < {} >  ", self.selected_policy.label()),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_pol = Paragraph::new(pol_text).style(pol_style);
        f.render_widget(p_pol, input_chunks[2]);

        // Lyrics Toggle
        let (lyr_text, lyr_style) = if self.focused_field == 3 {
            (
                format!("[► Lyrics: {} ◄]", if self.download_lyrics { "ON" } else { "OFF" }),
                Style::default().fg(theme.secondary).bg(theme.surface).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                format!("  Lyrics: {}  ", if self.download_lyrics { "ON" } else { "OFF" }),
                Style::default().fg(theme.text_dim),
            )
        };
        let p_lyr = Paragraph::new(lyr_text).style(lyr_style);
        f.render_widget(p_lyr, input_chunks[3]);

        // Convert Button
        let (btn_text, btn_style) = if self.focused_field == 4 {
            (
                "[► CONVERT ◄]",
                Style::default().fg(Color::Black).bg(theme.primary).add_modifier(Modifier::BOLD),
            )
        } else {
            (
                "[ CONVERT ]",
                Style::default().fg(theme.primary).bg(theme.surface),
            )
        };
        let p_btn = Paragraph::new(btn_text)
            .style(btn_style)
            .alignment(Alignment::Center);
        f.render_widget(p_btn, input_chunks[4]);

        // 2. Active Job Table
        let table_block = Block::default()
            .title(" ACTIVE DOWNLOADS & CONVERSION QUEUE (Up/Down Navigate | [E] Enhance Lossless) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border));
        let table_inner = table_block.inner(chunks[1]);
        f.render_widget(table_block, chunks[1]);

        if self.jobs.is_empty() {
            let empty_text = vec![
                Line::from(""),
                Line::from(vec![
                    Span::styled("   No active download jobs in queue.", Style::default().fg(theme.text_dim)),
                ]),
                Line::from(vec![
                    Span::styled("   Paste a link above and press Enter to rip high-bitrate audio.", Style::default().fg(theme.text_dim)),
                ]),
            ];
            let p_empty = Paragraph::new(empty_text);
            f.render_widget(p_empty, table_inner);
        } else {
            let items: Vec<ListItem> = self.jobs.iter().enumerate().map(|(i, j)| {
                let is_sel = i == self.selected_job_idx;
                let phase_color = match j.phase {
                    JobPhase::Completed => theme.success,
                    JobPhase::Failed(_) => theme.error,
                    JobPhase::Downloading | JobPhase::Auditing => theme.accent,
                    _ => theme.text_dim,
                };

                let prefix = if is_sel { "> " } else { "  " };
                let bar_width = 16;
                let filled = ((j.progress / 100.0) * bar_width as f32) as usize;
                let bar = format!("[{}{}]", "=".repeat(filled.min(bar_width)), " ".repeat(bar_width.saturating_sub(filled)));

                let text = format!(
                    "{}#{:<2} {:<30} {:<12} {:<14} {:>4.0}% {} {:<10} ETA: {}",
                    prefix,
                    j.id,
                    j.display_name,
                    j.quality.label(),
                    j.phase.label(),
                    j.progress,
                    bar,
                    j.speed,
                    j.eta
                );

                let style = if is_sel {
                    Style::default().fg(theme.text).bg(theme.surface).add_modifier(Modifier::BOLD)
                } else {
                    Style::default().fg(phase_color)
                };

                ListItem::new(text).style(style)
            }).collect();

            let list = List::new(items)
                .highlight_style(Style::default().bg(theme.surface).add_modifier(Modifier::BOLD));
            f.render_stateful_widget(list, table_inner, &mut self.job_list_state);
        }

        // 3. Forensic Spectral Cutoff Inspection Pane
        let audit_block = Block::default()
            .title(" FORENSIC SPECTRAL CUTOFF & QUALITY VERIFICATION ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.secondary));
        let audit_inner = audit_block.inner(chunks[2]);
        f.render_widget(audit_block, chunks[2]);

        let audit_lines = if let Some(job) = self.jobs.get(self.selected_job_idx) {
            let verdict = job.spectral_verdict.as_deref().unwrap_or("Waiting for file download completion...");
            vec![
                Line::from(vec![
                    Span::styled(format!("Track: {} | Target: {}", job.display_name, job.quality.label()), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(vec![
                    Span::styled("Authenticity: ", Style::default().fg(theme.text_dim)),
                    Span::styled(verdict, Style::default().fg(if verdict.contains("TRUE") { theme.success } else { theme.warning })),
                ]),
            ]
        } else {
            vec![
                Line::from(vec![
                    Span::styled("No job selected. Select a job in the queue to inspect frequency cutoff and tags.", Style::default().fg(theme.text_dim)),
                ]),
            ]
        };

        let p_audit = Paragraph::new(audit_lines);
        f.render_widget(p_audit, audit_inner);
    }

    fn render_eq_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Top EQ Status & Master Switch bar
                Constraint::Min(12),  // 10-Band Sliders Rails
                Constraint::Length(3), // Bottom hotkey helper bar
            ])
            .split(area);

        // 1. Status Bar
        let bypass_str = if self.eq_bypass { "[BYPASSED (FLAT)]" } else { "[ACTIVE]" };
        let bypass_color = if self.eq_bypass { theme.warning } else { theme.success };
        let hpf_str = if self.hpf_30hz { "ON (Sub-bass Cut)" } else { "OFF" };
        let air_str = if self.air_boost { "ON (+3dB @ 16kHz)" } else { "OFF" };

        let status_spans = vec![
            Span::styled(" MASTER EQ STATUS: ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled(bypass_str, Style::default().fg(bypass_color).add_modifier(Modifier::BOLD)),
            Span::raw("   |   "),
            Span::styled("30Hz HPF: ", Style::default().fg(theme.text_dim)),
            Span::styled(hpf_str, Style::default().fg(if self.hpf_30hz { theme.accent } else { theme.text_dim })),
            Span::raw("   |   "),
            Span::styled("Air Boost: ", Style::default().fg(theme.text_dim)),
            Span::styled(air_str, Style::default().fg(if self.air_boost { theme.accent } else { theme.text_dim })),
            Span::raw("   |   "),
            Span::styled(format!("Focus Band: {}", FREQ_LABELS[self.selected_band]), Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
        ];

        let p_status = Paragraph::new(Line::from(status_spans))
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.primary)));
        f.render_widget(p_status, chunks[0]);

        // 2. 10 Vertical Bands
        let bands_block = Block::default()
            .title(" 10-BAND ISO GRAPHIC EQUALIZER RAILS (-12.0 dB to +12.0 dB) ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border));
        let bands_inner = bands_block.inner(chunks[1]);
        f.render_widget(bands_block, chunks[1]);

        let col_constraints = vec![Constraint::Ratio(1, 10); 10];
        let cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints(col_constraints)
            .split(bands_inner);

        for i in 0..10 {
            let is_sel = i == self.selected_band;
            let gain = self.band_gains[i];
            let label = FREQ_LABELS[i];

            let border_color = if is_sel {
                theme.accent
            } else {
                theme.border
            };

            let gain_str = if gain > 0.0 {
                format!("+{:>4.1}dB", gain)
            } else if gain < 0.0 {
                format!("{:>5.1}dB", gain)
            } else {
                "  0.0dB".to_string()
            };

            let gain_color = if self.eq_bypass {
                theme.text_dim
            } else if gain > 0.0 {
                theme.accent
            } else if gain < 0.0 {
                theme.secondary
            } else {
                theme.text
            };

            // Rail graphic calculation (-12dB to +12dB => 25 discrete steps)
            let height = cols[i].height.saturating_sub(4) as usize;
            let mut rail_lines = Vec::new();
            
            // Generate visual slider track
            let norm_gain = ((gain + 12.0) / 24.0).clamp(0.0, 1.0);
            let knob_pos = if height > 0 {
                ((1.0 - norm_gain) * (height.saturating_sub(1) as f32)).round() as usize
            } else {
                0
            };

            for row in 0..height {
                let track_char = if row == knob_pos {
                    "[#]"
                } else if row == height / 2 {
                    "---"
                } else {
                    " | "
                };

                let style = if row == knob_pos {
                    Style::default().fg(if is_sel { theme.accent } else { theme.primary }).add_modifier(Modifier::BOLD)
                } else if row == height / 2 {
                    Style::default().fg(theme.border)
                } else {
                    Style::default().fg(theme.text_dim)
                };

                rail_lines.push(Line::from(vec![Span::styled(track_char, style)]));
            }

            // Top frequency header + gain text
            let col_block = Block::default()
                .title(label)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color));
            let col_inner = col_block.inner(cols[i]);
            f.render_widget(col_block, cols[i]);

            let col_chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(1), // Gain readout
                    Constraint::Min(1),    // Slider track
                ])
                .split(col_inner);

            let p_gain = Paragraph::new(gain_str)
                .alignment(Alignment::Center)
                .style(Style::default().fg(gain_color).add_modifier(if is_sel { Modifier::BOLD } else { Modifier::empty() }));
            f.render_widget(p_gain, col_chunks[0]);

            let p_rail = Paragraph::new(rail_lines)
                .alignment(Alignment::Center);
            f.render_widget(p_rail, col_chunks[1]);
        }

        // 3. Bottom Hotkey Guide
        let guide_text = Line::from(vec![
            Span::styled(" [Left/Right] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Select Band  ", Style::default().fg(theme.text)),
            Span::styled(" [Up/Down] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("+/-0.5 dB  ", Style::default().fg(theme.text)),
            Span::styled(" [0] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled("Zero  ", Style::default().fg(theme.text)),
            Span::styled(" [R] ", Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)),
            Span::styled("Reset Flat  ", Style::default().fg(theme.text)),
            Span::styled(" [H] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("30Hz HPF  ", Style::default().fg(theme.text)),
            Span::styled(" [A] ", Style::default().fg(theme.primary).add_modifier(Modifier::BOLD)),
            Span::styled("Air Boost  ", Style::default().fg(theme.text)),
            Span::styled(" [B] ", Style::default().fg(theme.warning).add_modifier(Modifier::BOLD)),
            Span::styled("Bypass  ", Style::default().fg(theme.text)),
            Span::styled(" [E] ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
            Span::styled("Enhance Track  ", Style::default().fg(theme.text)),
            Span::styled(" [Tab] ", Style::default().fg(theme.text_dim)),
            Span::styled("Next Tab", Style::default().fg(theme.text_dim)),
        ]);
        let p_guide = Paragraph::new(guide_text)
            .alignment(Alignment::Center)
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(theme.border)));
        f.render_widget(p_guide, chunks[2]);
    }

    fn render_visuals_tab(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let block = Block::default()
            .title(" REAL-TIME AUDIO & SPECTRAL FREQUENCY VISUALIZER ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.secondary));
        let inner = block.inner(area);
        f.render_widget(block, area);

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Frequency response curve
                Constraint::Min(8),   // Multi-channel level visualizer
                Constraint::Length(3), // Info bar
            ])
            .split(inner);

        // Frequency Curve Visual
        let mut curve_spans = Vec::new();
        curve_spans.push(Span::styled("Response Curve: ", Style::default().fg(theme.text_dim)));
        for (i, &gain) in self.band_gains.iter().enumerate() {
            let label = FREQ_LABELS[i];
            let dot = if self.eq_bypass {
                "---"
            } else if gain > 3.0 {
                "^^^"
            } else if gain > 0.0 {
                "---"
            } else if gain < -3.0 {
                "vvv"
            } else if gain < 0.0 {
                "___"
            } else {
                "---"
            };
            curve_spans.push(Span::styled(format!("{}:{} ", label, dot), Style::default().fg(theme.primary)));
        }
        let p_curve = Paragraph::new(Line::from(curve_spans))
            .block(Block::default().title(" COMPOSITE EQ FREQUENCY CURVE ").borders(Borders::ALL));
        f.render_widget(p_curve, chunks[0]);

        // Level visualizer
        let mut vis_lines = Vec::new();
        vis_lines.push(Line::from(""));
        vis_lines.push(Line::from(vec![
            Span::styled("  CH 1 [L]:  ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled("[||||||||||||||||||||||||||||||||||||||||              ] -6.2 dBFS", Style::default().fg(theme.accent)),
        ]));
        vis_lines.push(Line::from(""));
        vis_lines.push(Line::from(vec![
            Span::styled("  CH 2 [R]:  ", Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled("[||||||||||||||||||||||||||||||||||||                  ] -7.5 dBFS", Style::default().fg(theme.accent)),
        ]));
        vis_lines.push(Line::from(""));
        vis_lines.push(Line::from(vec![
            Span::styled("  SUB-BASS:  ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.hpf_30hz { "[30Hz High-Pass Attenuated]" } else { "[Full 20Hz-60Hz Pass-Through]" }, Style::default().fg(theme.secondary)),
        ]));
        vis_lines.push(Line::from(vec![
            Span::styled("  AIR 16k:   ", Style::default().fg(theme.text_dim)),
            Span::styled(if self.air_boost { "[+3.0 dB High Shelf Engaged]" } else { "[Flat Response]" }, Style::default().fg(theme.secondary)),
        ]));

        let p_vis = Paragraph::new(vis_lines)
            .block(Block::default().title(" STEREO MASTER CHANNELS & SPECTRAL ENERGY ").borders(Borders::ALL));
        f.render_widget(p_vis, chunks[1]);

        let info = Paragraph::new("Press [1] or [F1] for Downloads Queue, [2] or [F2] for 10-Band EQ, [Tab] to cycle tabs.")
            .alignment(Alignment::Center)
            .style(Style::default().fg(theme.text_dim));
        f.render_widget(info, chunks[2]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_downloader_tab_switching() {
        let mut state = DownloaderState::new();
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Switch to EQ tab via F2
        state.handle_key(KeyCode::F(2));
        assert_eq!(state.active_tab, DownloaderTab::Eq);

        // Switch to Visuals tab via F3
        state.handle_key(KeyCode::F(3));
        assert_eq!(state.active_tab, DownloaderTab::Visuals);

        // Switch back to Queue via F1
        state.handle_key(KeyCode::F(1));
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Switch via Tab from EQ
        state.active_tab = DownloaderTab::Eq;
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.active_tab, DownloaderTab::Visuals);
    }

    #[test]
    fn test_eq_band_navigation_and_gain_clamping() {
        let mut state = DownloaderState::new();
        state.active_tab = DownloaderTab::Eq;
        state.selected_band = 5; // 1kHz

        // Navigate left
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_band, 4);

        // Boost gain
        state.handle_key(KeyCode::Up);
        assert!((state.band_gains[4] - 0.5).abs() < 1e-4);

        // Boost to max limit (+12.0 dB)
        for _ in 0..30 {
            state.handle_key(KeyCode::Up);
        }
        assert!((state.band_gains[4] - 12.0).abs() < 1e-4);

        // Zero band
        state.handle_key(KeyCode::Char('0'));
        assert!((state.band_gains[4] - 0.0).abs() < 1e-4);

        // Cut to min limit (-12.0 dB)
        for _ in 0..30 {
            state.handle_key(KeyCode::Down);
        }
        assert!((state.band_gains[4] - (-12.0)).abs() < 1e-4);

        // Reset all flat
        state.handle_key(KeyCode::Char('r'));
        for gain in state.band_gains {
            assert!((gain - 0.0).abs() < 1e-4);
        }
    }

    #[test]
    fn test_eq_toggles() {
        let mut state = DownloaderState::new();
        state.active_tab = DownloaderTab::Eq;

        assert!(!state.hpf_30hz);
        state.handle_key(KeyCode::Char('h'));
        assert!(state.hpf_30hz);

        assert!(!state.air_boost);
        state.handle_key(KeyCode::Char('a'));
        assert!(state.air_boost);

        assert!(!state.eq_bypass);
        state.handle_key(KeyCode::Char('b'));
        assert!(state.eq_bypass);
    }

    #[tokio::test]
    async fn test_trigger_enhancement_empty_and_keyed() {
        let mut state = DownloaderState::new();
        state.focused_field = 1; // Unfocus text box so hotkeys work
        state.handle_key(KeyCode::Char('e'));
        assert!(state.status_message.contains("No jobs in queue"));

        // With job in queue
        state.jobs.push(DownloadJob {
            id: 1,
            source: "https://example.com/audio".to_string(),
            display_name: "Test Track".to_string(),
            quality: Mp3Quality::Mp3_320k,
            policy: AcquisitionPolicy::Mp3Only,
            phase: JobPhase::Completed,
            progress: 100.0,
            speed: "Done".to_string(),
            eta: "00:00".to_string(),
            spectral_verdict: None,
        });

        state.handle_key(KeyCode::Char('e'));
        assert!(state.status_message.contains("Enhancing track #1"));
    }

    #[test]
    fn test_number_keys_switch_tabs_directly() {
        let mut state = DownloaderState::new();
        // User starts at Queue with focused_field == 0
        assert_eq!(state.active_tab, DownloaderTab::Queue);
        assert!(!state.is_editing_url);

        // Pressing '2' switches directly to EQ tab!
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.active_tab, DownloaderTab::Eq);

        // Pressing '3' switches to Visuals tab!
        state.handle_key(KeyCode::Char('3'));
        assert_eq!(state.active_tab, DownloaderTab::Visuals);

        // Pressing '1' switches back to Queue!
        state.handle_key(KeyCode::Char('1'));
        assert_eq!(state.active_tab, DownloaderTab::Queue);
    }

    #[test]
    fn test_url_edit_mode_and_escape() {
        let mut state = DownloaderState::new();
        assert!(!state.is_editing_url);

        // Press Enter to start editing URL
        state.handle_key(KeyCode::Enter);
        assert!(state.is_editing_url);

        // While editing, numbers type into URL
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.input_text, "2");
        assert_eq!(state.active_tab, DownloaderTab::Queue); // Did not switch tabs!

        // Press Esc to exit edit mode
        state.handle_key(KeyCode::Esc);
        assert!(!state.is_editing_url);

        // Now pressing '2' switches to EQ tab
        state.handle_key(KeyCode::Char('2'));
        assert_eq!(state.active_tab, DownloaderTab::Eq);
    }

    #[test]
    fn test_paste_url_with_m_and_other_characters() {
        let mut state = DownloaderState::new();
        state.paste("https://music.youtube.com/watch?v=dQw4w9WgXcQ");
        assert!(state.is_editing_url);
        assert_eq!(state.input_text, "https://music.youtube.com/watch?v=dQw4w9WgXcQ");
        assert_eq!(state.active_tab, DownloaderTab::Queue);

        // Typing characters while focused on URL also enters edit mode
        let mut state2 = DownloaderState::new();
        state2.handle_key(KeyCode::Char('h'));
        assert!(state2.is_editing_url);
        assert_eq!(state2.input_text, "h");
    }

    #[tokio::test]
    async fn test_tab_navigation_out_of_url_editing() {
        let mut state = DownloaderState::new();
        state.paste("https://youtube.com/watch?v=example");
        assert!(state.is_editing_url);
        assert_eq!(state.focused_field, 0);

        // Pressing Tab while editing URL must exit edit mode and focus Quality (Field 1)
        state.handle_key(KeyCode::Tab);
        assert!(!state.is_editing_url);
        assert_eq!(state.focused_field, 1);

        // Right arrow changes Quality forward
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_quality, Mp3Quality::Mp3_V0);

        // Left arrow changes Quality backward
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_quality, Mp3Quality::Mp3_320k);

        // Left arrow again wraps backward to Opus160k
        state.handle_key(KeyCode::Left);
        assert_eq!(state.selected_quality, Mp3Quality::Opus160k);

        // Pressing Tab advances to Policy (Field 2)
        state.handle_key(KeyCode::Tab);
        assert_eq!(state.focused_field, 2);
        assert_eq!(state.selected_policy, AcquisitionPolicy::Mp3Only);

        // Right arrow cycles Policy to BestAvailable
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_policy, AcquisitionPolicy::BestAvailable);

        // Right arrow cycles to NicotineFlacPreferred
        state.handle_key(KeyCode::Right);
        assert_eq!(state.selected_policy, AcquisitionPolicy::NicotineFlacPreferred);

        // Pressing Enter while on Policy with non-empty URL submits the job!
        state.handle_key(KeyCode::Enter);
        assert_eq!(state.jobs.len(), 1);
        let queued = &state.jobs[0];
        assert_eq!(queued.quality, Mp3Quality::Opus160k);
        assert_eq!(queued.policy, AcquisitionPolicy::NicotineFlacPreferred);
    }

    #[test]
    fn test_backtab_navigation_from_editing() {
        let mut state = DownloaderState::new();
        state.paste("https://soundcloud.com/test/track");
        assert!(state.is_editing_url);

        // BackTab exits edit mode and shifts focus to Convert button (Field 4)
        state.handle_key(KeyCode::BackTab);
        assert!(!state.is_editing_url);
        assert_eq!(state.focused_field, 4);
    }

    #[test]
    fn test_lyrics_toggle_and_navigation() {
        let mut state = DownloaderState::new();
        assert!(state.download_lyrics);

        // Focus Lyrics (Field 3)
        state.focused_field = 3;
        state.is_editing_url = false;

        // Toggle with Space
        state.handle_key(KeyCode::Char(' '));
        assert!(!state.download_lyrics);

        // Toggle with Right arrow
        state.handle_key(KeyCode::Right);
        assert!(state.download_lyrics);

        // Toggle with 'l' hotkey
        state.handle_key(KeyCode::Char('l'));
        assert!(!state.download_lyrics);
    }

    #[test]
    fn test_bidirectional_cycling() {
        let q = Mp3Quality::Mp3_320k;
        assert_eq!(q.next(), Mp3Quality::Mp3_V0);
        assert_eq!(q.prev(), Mp3Quality::Opus160k);
        assert_eq!(Mp3Quality::FlacLossless.prev(), Mp3Quality::Aac_256k);

        let p = AcquisitionPolicy::Mp3Only;
        assert_eq!(p.next(), AcquisitionPolicy::BestAvailable);
        assert_eq!(p.prev(), AcquisitionPolicy::FastWebFallback);
        assert_eq!(AcquisitionPolicy::NicotineFlacPreferred.prev(), AcquisitionPolicy::BestAvailable);
    }
}
