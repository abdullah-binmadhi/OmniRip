//! Asynchronous Soulseek / Slskd API Client for OmniRip.
//! Interacts with Slskd daemon to search lossless flac/wav files and monitor transfers.

use reqwest::header::{HeaderMap, HeaderValue};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdFileResult {
    pub username: String,
    pub filename: String,
    pub size: u64,
    #[serde(alias = "bitRate")]
    pub bitrate: Option<u32>,
    pub sample_rate: Option<u32>,
    pub bit_depth: Option<u32>,
    #[serde(default)]
    pub upload_speed: Option<u64>,
    #[serde(default)]
    pub queue_length: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdTransferFile {
    pub username: String,
    pub filename: String,
    pub size: u64,
    pub state: String,
    pub bytes_transferred: u64,
    pub percent_complete: f32,
    pub average_speed: f64,
    pub remaining_time: Option<String>,
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

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SlskdServerStatus {
    pub address: Option<String>,
    pub ip_end_point: Option<String>,
    pub state: Option<String>,
    #[serde(default)]
    pub is_connected: bool,
    #[serde(default)]
    pub is_connecting: bool,
    #[serde(default)]
    pub is_logged_in: bool,
    #[serde(default)]
    pub is_logging_in: bool,
}

#[derive(Debug, Clone)]
pub struct SlskdClient {
    client: reqwest::Client,
    pub base_url: String,
    pub api_key: Option<String>,
}

impl SlskdClient {
    pub async fn check_server_health(&self) -> Result<SlskdServerStatus, String> {
        let url = format!("{}/api/v0/server", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("slskd daemon unreachable: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("slskd server health query returned status {}", resp.status()));
        }

        resp.json::<SlskdServerStatus>()
            .await
            .map_err(|e| format!("Failed to parse server status: {}", e))
    }

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
                let upload_speed = r["uploadSpeed"].as_u64();
                let queue_length = r["queueLength"].as_u64().map(|v| v as u32).unwrap_or(0);

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
                            upload_speed,
                            queue_length,
                        });
                    }
                }
            }
        }

        Ok(results)
    }

    /// Fetches all currently active download transfers across all peers.
    pub async fn get_active_transfers(&self) -> Result<Vec<SlskdTransferFile>, String> {
        let url = format!("{}/api/v0/transfers/downloads", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Query transfers error: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Query transfers error: HTTP {}", resp.status()));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse transfers JSON: {}", e))?;

        let mut transfers = Vec::new();
        if let Some(user_arr) = json.as_array() {
            for user_obj in user_arr {
                let username = user_obj["username"].as_str().unwrap_or_default().to_string();
                if let Some(dir_arr) = user_obj["directories"].as_array() {
                    for dir_obj in dir_arr {
                        if let Some(files) = dir_obj["files"].as_array() {
                            for f in files {
                                let filename = f["filename"].as_str().unwrap_or_default().to_string();
                                let size = f["size"].as_u64().unwrap_or_default();
                                let state = f["state"].as_str().unwrap_or("Unknown").to_string();
                                let bytes_transferred = f["bytesTransferred"].as_u64().unwrap_or_default();
                                let percent_complete = f["percentComplete"].as_f64().unwrap_or(0.0) as f32;
                                let average_speed = f["averageSpeed"].as_f64().unwrap_or(0.0);
                                let remaining_time = f["remainingTime"].as_str().map(|s| s.to_string());

                                transfers.push(SlskdTransferFile {
                                    username: username.clone(),
                                    filename,
                                    size,
                                    state,
                                    bytes_transferred,
                                    percent_complete,
                                    average_speed,
                                    remaining_time,
                                });
                            }
                        }
                    }
                }
            }
        }

        Ok(transfers)
    }

    /// Returns the active download directory for slskd.
    pub async fn get_downloads_dir(&self) -> std::path::PathBuf {
        let url = format!("{}/api/v0/options", self.base_url);
        if let Ok(resp) = self.client.get(&url).send().await {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                if let Some(p) = json.get("directories").and_then(|d| d.get("downloads")).and_then(|v| v.as_str()) {
                    let path = std::path::PathBuf::from(p);
                    if path.exists() {
                        return path;
                    }
                }
            }
        }
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let mac_default = std::path::PathBuf::from(&home).join("Library/Application Support/slskd/downloads");
        if mac_default.exists() {
            return mac_default;
        }
        let xdg_default = std::path::PathBuf::from(&home).join(".local/share/slskd/downloads");
        if xdg_default.exists() {
            return xdg_default;
        }
        std::path::PathBuf::from(&home).join("Music")
    }

    /// Triggers a re-scan of configured shares in slskd to update published file count.
    pub async fn trigger_shares_scan(&self) -> Result<(), String> {
        let url = format!("{}/api/v0/shares", self.base_url);
        let resp = self
            .client
            .put(&url)
            .send()
            .await
            .map_err(|e| format!("Trigger shares scan error: {}", e))?;

        if resp.status().is_success() {
            Ok(())
        } else {
            Err(format!("Trigger shares scan failed: HTTP {}", resp.status()))
        }
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

    #[test]
    fn test_slskd_server_status_parsing() {
        let sample = r#"{
            "address": "vps.slsknet.org",
            "ipEndPoint": "208.76.170.59:2271",
            "state": "Connected, LoggedIn",
            "isConnected": true,
            "isConnecting": false,
            "isLoggedIn": true,
            "isLoggingIn": false
        }"#;

        let status: Result<SlskdServerStatus, _> = serde_json::from_str(sample);
        assert!(status.is_ok());
        let s = status.unwrap();
        assert!(s.is_connected);
        assert!(s.is_logged_in);
        assert_eq!(s.address.as_deref(), Some("vps.slsknet.org"));
    }
}
