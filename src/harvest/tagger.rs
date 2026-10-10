//! Universal Audio Metadata Tagger for OmniRip using Lofty.
//! Supports FLAC, MP3, OPUS, OGG, M4A, WAV, and AIFF.

use lofty::config::WriteOptions;
use lofty::prelude::*;
use lofty::probe::Probe;
use lofty::tag::Tag;
use std::path::Path;

#[derive(Debug, Clone, Default, PartialEq)]
pub struct AudioTrackInfo {
    pub title: Option<String>,
    pub artist: Option<String>,
    pub album: Option<String>,
    pub year: Option<u32>,
    pub track_number: Option<u32>,
    pub genre: Option<String>,
    pub duration_secs: u64,
    pub bitrate_kbps: Option<u32>,
    pub sample_rate: Option<u32>,
    pub channels: Option<u8>,
}

/// Reads metadata and audio stream properties from the given file path.
pub fn read_tags<P: AsRef<Path>>(path: P) -> Result<AudioTrackInfo, String> {
    let path_ref = path.as_ref();
    let tagged_file = Probe::open(path_ref)
        .map_err(|e| format!("Failed to open file: {}", e))?
        .read()
        .map_err(|e| format!("Failed to read metadata: {}", e))?;

    let tag = tagged_file.primary_tag().or_else(|| tagged_file.first_tag());
    let props = tagged_file.properties();

    let mut info = AudioTrackInfo {
        duration_secs: props.duration().as_secs(),
        bitrate_kbps: props.audio_bitrate(),
        sample_rate: props.sample_rate(),
        channels: props.channels(),
        ..Default::default()
    };

    if let Some(t) = tag {
        info.title = t.title().map(|s| s.to_string());
        info.artist = t.artist().map(|s| s.to_string());
        info.album = t.album().map(|s| s.to_string());
        info.year = t.year();
        info.track_number = t.track();
        info.genre = t.genre().map(|s| s.to_string());
    }

    Ok(info)
}

/// Writes tag metadata into the given audio file.
pub fn write_tags<P: AsRef<Path>>(path: P, info: &AudioTrackInfo) -> Result<(), String> {
    let path_ref = path.as_ref();
    let mut tagged_file = Probe::open(path_ref)
        .map_err(|e| format!("Failed to open file for writing: {}", e))?
        .read()
        .map_err(|e| format!("Failed to parse file for writing: {}", e))?;

    let tag_type = tagged_file.primary_tag_type();
    let tag = match tagged_file.tag_mut(tag_type) {
        Some(t) => t,
        None => {
            tagged_file.insert_tag(Tag::new(tag_type));
            tagged_file.tag_mut(tag_type).ok_or("Failed to initialize tag")?
        }
    };

    if let Some(ref t) = info.title {
        tag.set_title(t.clone());
    }
    if let Some(ref a) = info.artist {
        tag.set_artist(a.clone());
    }
    if let Some(ref alb) = info.album {
        tag.set_album(alb.clone());
    }
    if let Some(y) = info.year {
        tag.set_year(y);
    }
    if let Some(tr) = info.track_number {
        tag.set_track(tr);
    }
    if let Some(ref g) = info.genre {
        tag.set_genre(g.clone());
    }

    tag.save_to_path(path_ref, WriteOptions::default())
        .map_err(|e| format!("Failed to save tags: {}", e))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_track_info_default() {
        let info = AudioTrackInfo::default();
        assert_eq!(info.duration_secs, 0);
        assert!(info.title.is_none());
        assert!(info.artist.is_none());
    }

    #[test]
    fn test_audio_track_info_builder() {
        let info = AudioTrackInfo {
            title: Some("Master of Puppets".into()),
            artist: Some("Metallica".into()),
            album: Some("Master of Puppets".into()),
            year: Some(1986),
            track_number: Some(2),
            genre: Some("Thrash Metal".into()),
            duration_secs: 515,
            bitrate_kbps: Some(1411),
            sample_rate: Some(44100),
            channels: Some(2),
        };

        assert_eq!(info.title.as_deref(), Some("Master of Puppets"));
        assert_eq!(info.track_number, Some(2));
        assert_eq!(info.year, Some(1986));
    }
}
