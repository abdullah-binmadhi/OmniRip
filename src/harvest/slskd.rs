//! Asynchronous Soulseek / Slskd API Client for OmniRip.
//! Interacts with Slskd daemon to search lossless flac/wav files and monitor transfers.

use reqwest::header::{HeaderMap, HeaderValue};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdFileResult {
    pub username: String,
    pub filename: String,
    pub size: u64,
    #[serde(alias = "bitRate")]
    pub bitrate: Option<u32>,
    pub sample_rate: Option<u32>,
    pub bit_depth: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdDownloadStatus {
    pub username: String,
    pub filename: String,
    pub percent: f32,
    pub speed_bytes_per_sec: u64,
    pub state: String,
}

#[derive(Debug, Clone)]
pub struct SlskdClient {
    client: reqwest::Client,
    pub base_url: String,
    pub api_key: Option<String>,
}

impl SlskdClient {
    pub fn new(base_url: &str, api_key: Option<String>) -> Self {
        let mut headers = HeaderMap::new();
        if let Some(ref key) = api_key {
            if let Ok(val) = HeaderValue::from_str(key) {
                headers.insert("X-API-KEY", val);
            }
        }
        let client = reqwest::Client::builder()
            .default_headers(headers)
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .unwrap_or_default();

        Self {
            client,
            base_url: base_url.trim_end_matches('/').to_string(),
            api_key,
        }
    }

    /// Automatically connects to local slskd daemon, discovering API key from environment or local config.
    pub fn detect_local() -> Self {
        let base_url = std::env::var("SLSKD_URL").unwrap_or_else(|_| "http://localhost:5030".to_string());
        let mut api_key = std::env::var("SLSKD_API_KEY").ok();

        if api_key.is_none() {
            let candidates = [
                std::path::PathBuf::from("tools/slskd/slskd.local.yml"),
                std::path::PathBuf::from("tools/slskd/slskd.yml"),
                std::path::PathBuf::from("slskd.yml"),
            ];
            for path in candidates {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    for line in content.lines() {
                        let trimmed = line.trim();
                        if trimmed.starts_with("api_key:") {
                            if let Some((_, val)) = trimmed.split_once(':') {
                                let key = val.trim().trim_matches('"').trim_matches('\'');
                                if !key.is_empty() {
                                    api_key = Some(key.to_string());
                                    break;
                                }
                            }
                        }
                    }
                    if api_key.is_some() {
                        break;
                    }
                }
            }
        }

        Self::new(&base_url, api_key)
    }

    /// Initiates a search query on the Soulseek network.
    pub async fn start_search(&self, text: &str) -> Result<String, String> {
        let url = format!("{}/api/v0/searches", self.base_url);
        let body = serde_json::json!({
            "searchText": text
        });

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("Failed to initiate search: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Search initiation error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        let id = json["id"]
            .as_str()
            .ok_or_else(|| "Search ID not found in response".to_string())?;

        Ok(id.to_string())
    }

    /// Fetches search results for an active search ID.
    pub async fn get_search_results(&self, search_id: &str) -> Result<Vec<SlskdFileResult>, String> {
        let url = format!("{}/api/v0/searches/{}/responses", self.base_url, search_id);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to query search results: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Query results error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        let mut results = Vec::new();
        let resp_list_opt = json.as_array().or_else(|| json.get("responses").and_then(|r| r.as_array()));

        if let Some(responses) = resp_list_opt {
            for r in responses {
                let username = r["username"].as_str().unwrap_or_default().to_string();
                if let Some(files) = r["files"].as_array() {
                    for f in files {
                        let filename = f["filename"].as_str().unwrap_or_default().to_string();
                        let size = f["size"].as_u64().unwrap_or_default();
                        let bitrate = f["bitRate"].as_u64().map(|v| v as u32);
                        let sample_rate = f["sampleRate"].as_u64().map(|v| v as u32);
                        let bit_depth = f["bitDepth"].as_u64().map(|v| v as u32);

                        results.push(SlskdFileResult {
                            username: username.clone(),
                            filename,
                            size,
                            bitrate,
                            sample_rate,
                            bit_depth,
                        });
                    }
                }
            }
        }

        Ok(results)
    }

    /// Queues a file for download from a Soulseek user.
    pub async fn queue_download(&self, username: &str, filename: &str, size: u64) -> Result<(), String> {
        let url = format!("{}/api/v0/transfers/downloads/{}", self.base_url, username);
        let body = serde_json::json!([
            {
                "filename": filename,
                "size": size
            }
        ]);

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("Download request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Download error: HTTP {}", resp.status()));
        }

        Ok(())
    }

    /// Fetches all active downloads and their current transfer states.
    pub async fn get_active_downloads(&self) -> Result<Vec<SlskdDownloadStatus>, String> {
        let url = format!("{}/api/v0/transfers/downloads", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to get downloads: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Downloads status error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse downloads JSON: {}", e))?;

        let mut downloads = Vec::new();
        if let Some(arr) = json.as_array() {
            for item in arr {
                let username = item["username"].as_str().unwrap_or_default().to_string();
                let filename = item["filename"].as_str().unwrap_or_default().to_string();
                let bytes_transferred = item["bytesTransferred"].as_f64().unwrap_or(0.0);
                let size = item["size"].as_f64().unwrap_or(1.0);
                let speed = item["speed"].as_u64().unwrap_or(0);
                let state = item["state"].as_str().unwrap_or("Unknown").to_string();

                let percent = ((bytes_transferred / size.max(1.0)) * 100.0) as f32;

                downloads.push(SlskdDownloadStatus {
                    username,
                    filename,
                    percent: percent.clamp(0.0, 100.0),
                    speed_bytes_per_sec: speed,
                    state,
                });
            }
        }

        Ok(downloads)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_slskd_client_url_construction() {
        let client = SlskdClient::new("http://127.0.0.1:5030/", Some("secret".into()));
        assert_eq!(client.base_url, "http://127.0.0.1:5030");
        assert_eq!(client.api_key.as_deref(), Some("secret"));
    }

    #[test]
    fn test_slskd_file_result_parsing() {
        let json_str = r#"{
            "username": "AudiophileMaster",
            "filename": "Pink Floyd - Time (1973).flac",
            "size": 45182900,
            "bitrate": 960,
            "sampleRate": 44100,
            "bitDepth": 16
        }"#;

        let res: Result<SlskdFileResult, _> = serde_json::from_str(json_str);
        assert!(res.is_ok());
        let f = res.unwrap();
        assert_eq!(f.username, "AudiophileMaster");
        assert_eq!(f.bit_depth, Some(16));
    }

    #[test]
    fn test_slskd_detect_local() {
        let client = SlskdClient::detect_local();
        assert_eq!(client.base_url, "http://localhost:5030");
    }
}
