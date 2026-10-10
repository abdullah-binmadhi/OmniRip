//! OmniRip Harvester: Audio Downloader, Tagging & Quality Analysis Subsystem.

pub mod slskd;
pub mod spectral;
pub mod tagger;
pub mod yt_dlp;

pub use slskd::{SlskdClient, SlskdDownloadStatus, SlskdFileResult};
pub use spectral::{analyze_file, analyze_samples, QualityVerdict, SpectralAnalysisResult};
pub use tagger::{read_tags, write_tags, AudioTrackInfo};
pub use yt_dlp::{check_installed, download_audio, parse_progress_line, AudioFormat, YtDlpProgress};

#[derive(Debug, Clone)]
pub struct HarvesterManager {
    pub slskd: SlskdClient,
    pub download_dir: String,
}

impl Default for HarvesterManager {
    fn default() -> Self {
        Self {
            slskd: SlskdClient::new("http://localhost:5030", None),
            download_dir: "./downloads".to_string(),
        }
    }
}
