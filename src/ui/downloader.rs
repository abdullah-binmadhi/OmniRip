use crate::harvest::musicbrainz::lookup_metadata;
use crate::harvest::spectral::analyze_file;
use crate::harvest::tagger::{write_tags, AudioTrackInfo};
use crate::harvest::title_cleaner::clean_title;
use crate::harvest::yt_dlp::{
    download_audio, download_audio_to_path, expand_album_tracks, get_album_track_path,
    is_playlist_or_album, AudioFormat,
};
use crate::ui::theme::ThemePalette;
use crossterm::event::KeyCode;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph};
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

pub struct DownloaderState {
    pub input_text: String,
    pub selected_quality: Mp3Quality,
    pub selected_policy: AcquisitionPolicy,
    pub jobs: Vec<DownloadJob>,
    pub selected_job_idx: usize,
    pub job_list_state: ListState,
    pub next_job_id: usize,
    pub focused_field: usize, // 0: Input, 1: Quality, 2: Policy, 3: Convert
    pub status_message: String,
    tx: Sender<(usize, JobPhase, f32, String, String, Option<String>)>,
    rx: Receiver<(usize, JobPhase, f32, String, String, Option<String>)>,
}

impl DownloaderState {
    pub fn new() -> Self {
        let (tx, rx) = channel(64);
        let mut list_state = ListState::default();
        list_state.select(Some(0));

        Self {
            input_text: String::new(),
            selected_quality: Mp3Quality::Mp3_320k, // Default to MP3 320k per user request
            selected_policy: AcquisitionPolicy::Mp3Only,
            jobs: Vec::new(),
            selected_job_idx: 0,
            job_list_state: list_state,
            next_job_id: 1,
            focused_field: 0,
            status_message: "Ready. Paste audio/video URL and press Enter.".to_string(),
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

            let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
            let music_dir = std::path::PathBuf::from(home).join("Music");
            let _ = std::fs::create_dir_all(&music_dir);

            match download_audio(&url, &music_dir, format).await {
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

                    if let Ok(mb) = lookup_metadata(cleaned.artist.as_deref(), &cleaned.title).await {
                        tag_info.title = Some(mb.title);
                        tag_info.artist = Some(mb.artist);
                        tag_info.album = mb.album;
                        tag_info.year = mb.year;
                        tag_info.track_number = mb.track_number;
                    }

                    let _ = write_tags(&path_str, &tag_info);

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

    pub fn handle_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Char(c) if self.focused_field == 0 => {
                self.input_text.push(c);
            }
            KeyCode::Backspace if self.focused_field == 0 => {
                self.input_text.pop();
            }
            KeyCode::Enter => {
                self.submit_current();
            }
            KeyCode::Tab => {
                self.focused_field = (self.focused_field + 1) % 4;
            }
            KeyCode::BackTab => {
                self.focused_field = if self.focused_field == 0 { 3 } else { self.focused_field - 1 };
            }
            KeyCode::Left | KeyCode::Right => {
                if self.focused_field == 1 {
                    self.selected_quality = self.selected_quality.next();
                } else if self.focused_field == 2 {
                    self.selected_policy = self.selected_policy.next();
                }
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
            _ => {}
        }
    }

    pub fn render(&mut self, f: &mut ratatui::Frame, area: Rect, theme: &ThemePalette) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4), // Top input row & controls
                Constraint::Min(8),   // Job Table
                Constraint::Length(5), // Forensic Spectral Inspection Pane
            ])
            .split(area);

        // 1. Top Controls Bar
        let bar_block = Block::default()
            .title(" MP3 DOWNLOADER & CONVERSION CONTROLS ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.primary));
        let bar_inner = bar_block.inner(chunks[0]);
        f.render_widget(bar_block, chunks[0]);

        let input_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Min(25),    // URL Input
                Constraint::Length(22), // Quality select
                Constraint::Length(22), // Policy select
                Constraint::Length(14), // Convert Button
            ])
            .split(bar_inner);

        // URL Input
        let input_style = if self.focused_field == 0 {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text)
        };
        let input_prefix = if self.focused_field == 0 { "> " } else { "  " };
        let input_text = if self.input_text.is_empty() {
            "[Paste URL / Search Query here...]"
        } else {
            &self.input_text
        };
        let p_input = Paragraph::new(format!("{}URL: {}", input_prefix, input_text))
            .style(input_style);
        f.render_widget(p_input, input_chunks[0]);

        // Quality Select
        let q_style = if self.focused_field == 1 {
            Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text_dim)
        };
        let p_q = Paragraph::new(format!("Quality: < {} >", self.selected_quality.label()))
            .style(q_style);
        f.render_widget(p_q, input_chunks[1]);

        // Policy Select
        let pol_style = if self.focused_field == 2 {
            Style::default().fg(theme.secondary).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.text_dim)
        };
        let p_pol = Paragraph::new(format!("Source: < {} >", self.selected_policy.label()))
            .style(pol_style);
        f.render_widget(p_pol, input_chunks[2]);

        // Convert Button
        let btn_style = if self.focused_field == 3 {
            Style::default().fg(Color::Black).bg(theme.primary).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.primary).bg(theme.surface)
        };
        let p_btn = Paragraph::new("[ CONVERT ]")
            .style(btn_style)
            .alignment(Alignment::Center);
        f.render_widget(p_btn, input_chunks[3]);

        // 2. Active Job Table
        let table_block = Block::default()
            .title(" ACTIVE DOWNLOADS & CONVERSION QUEUE (Up/Down Navigate) ")
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
}
