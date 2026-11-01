//! Universal Link Bank & Multi-Source Library Vault
//!
//! Stores user-saved and friend-shared playlist links across Spotify, Apple Music,
//! YouTube Music, and web M3U playlists in persistent JSON and plain-text formats.
//! Automatically detects and imports saved links into the active streaming library on startup.

use crate::harvest::playlist_parser::StreamingService;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LinkBankEntry {
    pub id: String,
    pub url: String,
    pub title: String,
    pub curator: String,
    pub service: StreamingService,
    pub enabled: bool,
    pub track_count: usize,
    pub added_at: u64,
}

impl LinkBankEntry {
    pub fn new(url: &str, curator: Option<&str>) -> Self {
        let trimmed_url = url.trim().to_string();
        let service = StreamingService::detect(&trimmed_url);
        let id = format!("{:x}", md5_like_hash(&trimmed_url));
        let title = derive_friendly_title(&trimmed_url, service);
        let curator_str = curator
            .map(|c| c.trim().to_string())
            .filter(|c| !c.is_empty())
            .unwrap_or_else(|| "Shared Collection".to_string());
        let added_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        Self {
            id,
            url: trimmed_url,
            title,
            curator: curator_str,
            service,
            enabled: true,
            track_count: 0,
            added_at,
        }
    }

    pub fn display_label(&self) -> String {
        if self.curator.is_empty() || self.curator == "Shared Collection" {
            self.title.clone()
        } else {
            format!("{}: {}", self.curator, self.title)
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LinkBankStore {
    pub entries: Vec<LinkBankEntry>,
}

impl LinkBankStore {
    pub fn config_dir() -> PathBuf {
        if let Ok(home) = std::env::var("HOME") {
            PathBuf::from(home).join(".config").join("omnirip")
        } else if let Ok(user_profile) = std::env::var("USERPROFILE") {
            PathBuf::from(user_profile).join(".config").join("omnirip")
        } else {
            PathBuf::from(".config/omnirip")
        }
    }

    pub fn json_path() -> PathBuf {
        Self::config_dir().join("link_bank.json")
    }

    pub fn txt_path() -> PathBuf {
        Self::config_dir().join("links.txt")
    }

    /// Loads the Link Bank from disk, checks for plain-text `links.txt` additions,
    /// and auto-persists updates.
    pub fn load() -> Self {
        let mut store = Self::load_raw_json();
        let mut changed = false;

        // Auto-import links from links.txt if it exists
        let txt_path = Self::txt_path();
        if txt_path.exists() {
            if let Ok(content) = fs::read_to_string(&txt_path) {
                for line in content.lines() {
                    let trimmed = line.trim();
                    if trimmed.is_empty() || trimmed.starts_with('#') {
                        continue;
                    }
                    if !store.contains_url(trimmed) {
                        store.entries.push(LinkBankEntry::new(trimmed, Some("Imported from links.txt")));
                        changed = true;
                    }
                }
            }
        }

        if changed {
            let _ = store.save();
        }

        store
    }

    fn load_raw_json() -> Self {
        let path = Self::json_path();
        if path.exists() {
            if let Ok(data) = fs::read_to_string(&path) {
                if let Ok(store) = serde_json::from_str::<Self>(&data) {
                    return store;
                }
                if let Ok(entries) = serde_json::from_str::<Vec<LinkBankEntry>>(&data) {
                    return Self { entries };
                }
            }
        }
        Self::default()
    }

    pub fn save(&self) -> Result<(), std::io::Error> {
        let dir = Self::config_dir();
        if !dir.exists() {
            let _ = fs::create_dir_all(&dir);
        }
        let json = serde_json::to_string_pretty(self).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        fs::write(Self::json_path(), json)
    }

    pub fn reload(&mut self) {
        *self = Self::load();
    }

    pub fn add_link(&mut self, url: &str, curator: Option<&str>, _note: Option<&str>) -> LinkBankEntry {
        let clean = url.trim();
        let entry = LinkBankEntry::new(clean, curator);
        self.entries.push(entry.clone());
        let _ = self.save();
        entry
    }

    pub fn contains_url(&self, url: &str) -> bool {
        let clean = url.trim().to_lowercase();
        self.entries.iter().any(|e| e.url.trim().to_lowercase() == clean)
    }

    pub fn add_url(&mut self, url: &str, curator: Option<&str>) -> Result<String, String> {
        let clean = url.trim();
        if clean.is_empty() {
            return Err("URL cannot be empty".to_string());
        }
        if self.contains_url(clean) {
            return Err("Link is already saved in Link Bank".to_string());
        }
        let entry = LinkBankEntry::new(clean, curator);
        let id = entry.id.clone();
        self.entries.push(entry);
        let _ = self.save();
        Ok(id)
    }

    pub fn remove_at(&mut self, idx: usize) -> Option<LinkBankEntry> {
        if idx < self.entries.len() {
            let entry = self.entries.remove(idx);
            let _ = self.save();
            Some(entry)
        } else {
            None
        }
    }

    pub fn toggle_at(&mut self, idx: usize) -> Option<bool> {
        if let Some(entry) = self.entries.get_mut(idx) {
            entry.enabled = !entry.enabled;
            let res = entry.enabled;
            let _ = self.save();
            Some(res)
        } else {
            None
        }
    }

    pub fn set_curator_at(&mut self, idx: usize, curator: &str) -> bool {
        if let Some(entry) = self.entries.get_mut(idx) {
            entry.curator = curator.trim().to_string();
            let _ = self.save();
            true
        } else {
            false
        }
    }

    pub fn active_entries(&self) -> Vec<&LinkBankEntry> {
        self.entries.iter().filter(|e| e.enabled).collect()
    }
}

fn md5_like_hash(s: &str) -> u64 {
    let mut hash: u64 = 5381;
    for b in s.bytes() {
        hash = hash.wrapping_mul(33).wrapping_add(b as u64);
    }
    hash
}

fn derive_friendly_title(url: &str, service: StreamingService) -> String {
    let lower = url.to_lowercase();
    if service == StreamingService::Spotify {
        if let Some(pos) = lower.find("/playlist/") {
            let rest = &url[pos + 10..];
            let id = rest.split('?').next().unwrap_or(rest);
            return format!("Spotify Playlist ({})", &id[..id.len().min(8)]);
        } else if let Some(pos) = lower.find("/album/") {
            let rest = &url[pos + 7..];
            let id = rest.split('?').next().unwrap_or(rest);
            return format!("Spotify Album ({})", &id[..id.len().min(8)]);
        }
        "Spotify Shared Collection".to_string()
    } else if service == StreamingService::AppleMusic {
        if let Some(pos) = lower.find("/playlist/") {
            let rest = &url[pos + 10..];
            let name_seg = rest.split('/').next().unwrap_or("Playlist");
            let clean_name = name_seg.replace('-', " ");
            return format!("Apple Music: {}", clean_name);
        }
        "Apple Music Shared Collection".to_string()
    } else if service == StreamingService::YouTubeMusic {
        if lower.contains("list=") {
            return "YouTube Music Playlist".to_string();
        }
        "YouTube Music Collection".to_string()
    } else {
        "Shared Audio Stream".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_link_bank_entry_creation_and_service_detect() {
        let entry = LinkBankEntry::new("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=123", Some("Friend: Alex"));
        assert_eq!(entry.service, StreamingService::Spotify);
        assert_eq!(entry.curator, "Friend: Alex");
        assert!(entry.enabled);
        assert!(entry.display_label().starts_with("Friend: Alex:"));
    }

    #[test]
    fn test_link_bank_store_add_toggle_remove() {
        let mut store = LinkBankStore::default();
        assert_eq!(store.entries.len(), 0);

        let res = store.add_url("https://music.youtube.com/playlist?list=PL123", Some("Sarah's Mix"));
        assert!(res.is_ok());
        assert_eq!(store.entries.len(), 1);
        assert_eq!(store.entries[0].curator, "Sarah's Mix");
        assert!(store.entries[0].enabled);

        // Duplicate rejection
        let dup = store.add_url("https://music.youtube.com/playlist?list=PL123", None);
        assert!(dup.is_err());

        // Toggle
        let toggled = store.toggle_at(0);
        assert_eq!(toggled, Some(false));
        assert_eq!(store.active_entries().len(), 0);

        let toggled_back = store.toggle_at(0);
        assert_eq!(toggled_back, Some(true));
        assert_eq!(store.active_entries().len(), 1);

        // Remove
        let removed = store.remove_at(0);
        assert!(removed.is_some());
        assert_eq!(store.entries.len(), 0);
    }
}
