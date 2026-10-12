//! YouTube Title Cleaning & Artist-Track Parsing Engine for OmniRip.
//! Normalizes noisy titles by removing tags like "[Official Video]", "(Audio)", "[HD]", etc.

use std::sync::LazyLock;
use regex::Regex;

static BRACKETED_NOISE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)[\(\[\{]\s*(?:official\s+(?:music\s+)?video|official\s+audio|official\s+lyric\s+video|lyric\s+video|lyrics|audio|visualizer|mv|pv|hd|1080p|4k|hq|remastered|explicit|clean|prod\.[^\]\)]*|feat\.[^\]\)]*|ft\.[^\]\)]*)\s*[\)\]\}]").expect("valid regex")
});

static UNBRACKETED_NOISE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\s*(?:\||//)\s*(?:official\s+(?:music\s+)?video|music\s+video|audio|lyrics?|visualizer).*$|\s+(?:feat\.|ft\.|featuring|prod\.|produced\s+by)\s+.*$").expect("valid regex")
});

static EXTRA_SPACES_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\s+").expect("valid regex")
});

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanedTrackMeta {
    pub artist: Option<String>,
    pub title: String,
}

/// Normalizes a noisy raw YouTube video or track title into structured artist and title.
pub fn clean_title(raw: &str) -> CleanedTrackMeta {
    // 1. Strip bracketed noise tags
    let without_noise = BRACKETED_NOISE_RE.replace_all(raw, " ").to_string();

    // 2. Strip unbracketed trailing features or video markers
    let without_trailing = UNBRACKETED_NOISE_RE.replace_all(&without_noise, " ").to_string();

    // 3. Normalize whitespace
    let normalized = EXTRA_SPACES_RE.replace_all(without_trailing.trim(), " ").to_string();

    // 4. Try splitting by common artist-title delimiters: " - ", " – ", " — ", " : "
    let delimiters = [" - ", " – ", " — ", " : "];
    for delim in delimiters {
        if let Some((left, right)) = normalized.split_once(delim) {
            let artist = left.trim();
            let mut title = right.trim().to_string();
            // Further clean title of unbracketed noise if present
            title = UNBRACKETED_NOISE_RE.replace_all(&title, "").trim().to_string();
            if !artist.is_empty() && !title.is_empty() {
                return CleanedTrackMeta {
                    artist: Some(artist.to_string()),
                    title,
                };
            }
        }
    }

    // Fallback: title only
    CleanedTrackMeta {
        artist: None,
        title: normalized,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_title_with_artist_and_noise() {
        let meta = clean_title("Radiohead - Karma Police (Official Music Video) [HD]");
        assert_eq!(meta.artist.as_deref(), Some("Radiohead"));
        assert_eq!(meta.title, "Karma Police");
    }

    #[test]
    fn test_clean_title_with_lyric_video_tag() {
        let meta = clean_title("Daft Punk - One More Time (Official Audio) [1080p]");
        assert_eq!(meta.artist.as_deref(), Some("Daft Punk"));
        assert_eq!(meta.title, "One More Time");
    }

    #[test]
    fn test_clean_title_no_artist() {
        let meta = clean_title("Midnight City (Visualizer)");
        assert_eq!(meta.artist, None);
        assert_eq!(meta.title, "Midnight City");
    }

    #[test]
    fn test_clean_title_unicode_dash() {
        let meta = clean_title("Pink Floyd – Comfortably Numb (Live)");
        assert_eq!(meta.artist.as_deref(), Some("Pink Floyd"));
        assert_eq!(meta.title, "Comfortably Numb (Live)");
    }

    #[test]
    fn test_clean_title_unbracketed_feat_and_pipe() {
        let meta = clean_title("Kavinsky - Nightcall feat. Lovefoxxx | Official Video");
        assert_eq!(meta.artist.as_deref(), Some("Kavinsky"));
        assert_eq!(meta.title, "Nightcall");
    }
}
