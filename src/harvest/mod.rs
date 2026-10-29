//! OmniRip Harvester: Audio Downloader, Tagging & Quality Analysis Subsystem.

pub mod bootstrap;
pub mod library_sync;
pub mod lyrics;
pub mod musicbrainz;
pub mod nicotine;
pub mod playlist_parser;
pub mod slskd;
pub mod spectral;
pub mod stream_resolver;
pub mod tagger;
pub mod title_cleaner;
pub mod updater;
pub mod yt_dlp;

pub use library_sync::{DiscoveredCollection, LibrarySyncEngine, LinkedAccountsConfig};

pub use lyrics::{fetch_lyrics_lrclib, resolve_and_save_lyrics, LyricsData};
pub use musicbrainz::{build_nicotine_query, fetch_cover_art_archive, lookup_metadata, MusicBrainzMetadata};
pub use nicotine::{score_candidate, DiscoveredAccount, NicotineCandidate, NicotineConfig};
pub use playlist_parser::{ParsedPlaylist, ParsedTrack, PlaylistParser, StreamingService};
pub use slskd::{SlskdClient, SlskdDownloadStatus, SlskdFileResult};
pub use spectral::{analyze_file, analyze_samples, QualityVerdict, SpectralAnalysisResult};
pub use tagger::{read_tags, write_tags, AudioTrackInfo};
pub use title_cleaner::{clean_title, CleanedTrackMeta};
pub use updater::{check_latest_release, parse_semver, UpdateInfo};
pub use yt_dlp::{check_installed, download_audio, fetch_video_title, parse_progress_line, AudioFormat, YtDlpProgress};

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
