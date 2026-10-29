use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Progress information for tool downloading.
#[derive(Debug, Clone)]
pub struct DownloadProgress {
    pub tool_name: String,
    pub downloaded_bytes: u64,
    pub total_bytes: Option<u64>,
    pub is_finished: bool,
    pub error: Option<String>,
}

/// Status of an external dependency tool.
#[derive(Debug, Clone)]
pub struct ToolInfo {
    pub name: String,
    pub is_installed: bool,
    pub resolved_path: Option<PathBuf>,
    pub version: Option<String>,
}

/// Resolver for external media binaries (`yt-dlp`, `ffmpeg`, etc.)
pub struct ToolResolver;

impl ToolResolver {
    /// Return the user-isolated directory for OmniRip external tools (`~/.local/share/omnirip/bin` on Unix, `%APPDATA%\OmniRip\bin` on Windows).
    pub fn user_tools_dir() -> PathBuf {
        if let Ok(appdata) = std::env::var("APPDATA") {
            let p = PathBuf::from(appdata).join("OmniRip").join("bin");
            return p;
        }

        if let Ok(home) = std::env::var("HOME") {
            let p = PathBuf::from(home)
                .join(".local")
                .join("share")
                .join("omnirip")
                .join("bin");
            return p;
        }

        PathBuf::from("/tmp/omnirip_tools")
    }

    /// Return sibling `./bin` directory next to the current running executable.
    pub fn sibling_tools_dir() -> Option<PathBuf> {
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(parent) = exe_path.parent() {
                let sibling_bin = parent.join("bin");
                if sibling_bin.is_dir() {
                    return Some(sibling_bin);
                }
                let sibling_tools = parent.join("tools");
                if sibling_tools.is_dir() {
                    return Some(sibling_tools);
                }
            }
        }
        None
    }

    /// Resolve the executable path of a given tool name using priority:
    /// 1. OmniRip User Tools directory (`~/.local/share/omnirip/bin`)
    /// 2. Sibling directory (`./bin` or `./tools`)
    /// 3. Global system `PATH`
    pub fn resolve_tool(name: &str) -> Option<PathBuf> {
        let exe_name = if cfg!(target_os = "windows") {
            format!("{}.exe", name)
        } else {
            name.to_string()
        };

        // 1. Check user isolated tools directory
        let user_bin = Self::user_tools_dir().join(&exe_name);
        if user_bin.is_file() {
            return Some(user_bin);
        }

        // 2. Check sibling directory
        if let Some(sibling) = Self::sibling_tools_dir() {
            let sibling_bin = sibling.join(&exe_name);
            if sibling_bin.is_file() {
                return Some(sibling_bin);
            }
        }

        // 3. Check system PATH
        if let Ok(path_var) = std::env::var("PATH") {
            let separator = if cfg!(target_os = "windows") { ';' } else { ':' };
            for dir in path_var.split(separator) {
                let candidate = Path::new(dir).join(&exe_name);
                if candidate.is_file() {
                    return Some(candidate);
                }
            }
        }

        None
    }

    /// Check the status and version of a specific tool.
    pub fn probe_tool(name: &str) -> ToolInfo {
        if let Some(path) = Self::resolve_tool(name) {
            let version = Self::fetch_version(&path);
            ToolInfo {
                name: name.to_string(),
                is_installed: true,
                resolved_path: Some(path),
                version,
            }
        } else {
            ToolInfo {
                name: name.to_string(),
                is_installed: false,
                resolved_path: None,
                version: None,
            }
        }
    }

    fn fetch_version(path: &Path) -> Option<String> {
        let output = Command::new(path).arg("--version").output().ok()?;
        if output.status.success() {
            let s = String::from_utf8_lossy(&output.stdout);
            let first_line = s.lines().next().unwrap_or("").trim();
            if !first_line.is_empty() {
                return Some(first_line.to_string());
            }
        }
        None
    }

    /// Prepend the user tools directory to the current process `PATH`.
    pub fn activate_user_tools_path() {
        let tools_dir = Self::user_tools_dir();
        if let Some(tools_str) = tools_dir.to_str() {
            let separator = if cfg!(target_os = "windows") { ";" } else { ":" };
            let current_path = std::env::var("PATH").unwrap_or_default();
            if !current_path.contains(tools_str) {
                let new_path = format!("{}{}{}", tools_str, separator, current_path);
                std::env::set_var("PATH", new_path);
            }
        }
    }
}

/// Official download URL resolver for static release binaries.
pub struct OfficialToolUrls;

impl OfficialToolUrls {
    /// Get official static binary download URL for `yt-dlp`.
    pub fn yt_dlp_url() -> (&'static str, &'static str) {
        #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
        return (
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
            "yt-dlp",
        );

        #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
        return (
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
            "yt-dlp",
        );

        #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
        return (
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux",
            "yt-dlp",
        );

        #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
        return (
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            "yt-dlp.exe",
        );

        #[cfg(not(any(
            all(target_os = "macos", target_arch = "aarch64"),
            all(target_os = "macos", target_arch = "x86_64"),
            all(target_os = "linux", target_arch = "x86_64"),
            all(target_os = "windows", target_arch = "x86_64")
        )))]
        return (
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
            "yt-dlp",
        );
    }
}

/// Asynchronous bootstrapper that downloads missing tools into OmniRip's isolated user directory.
pub struct ToolBootstrapper;

impl ToolBootstrapper {
    /// Download a file from a URL to destination path with progress updates.
    pub async fn download_file<F>(
        url: &str,
        dest_path: &Path,
        progress_cb: F,
        cancel_signal: Arc<AtomicBool>,
    ) -> Result<(), String>
    where
        F: Fn(u64, Option<u64>) + Send + 'static,
    {
        if let Some(parent) = dest_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

        let res = client
            .get(url)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {}", e))?;

        if !res.status().is_success() {
            return Err(format!("Download failed with HTTP status: {}", res.status()));
        }

        let total_size = res.content_length();
        let mut downloaded: u64 = 0;

        use std::io::Write;
        let temp_dest = dest_path.with_extension("tmp_download");
        let mut file = std::fs::File::create(&temp_dest)
            .map_err(|e| format!("Failed to create destination file: {}", e))?;

        let mut res = res;
        while let Ok(Some(chunk)) = res.chunk().await {
            if cancel_signal.load(Ordering::Relaxed) {
                let _ = std::fs::remove_file(&temp_dest);
                return Err("Download canceled by user.".to_string());
            }

            file.write_all(&chunk)
                .map_err(|e| format!("Failed to write chunk to disk: {}", e))?;
            downloaded += chunk.len() as u64;
            progress_cb(downloaded, total_size);
        }

        file.flush().map_err(|e| format!("Failed to flush file: {}", e))?;
        drop(file);

        // Rename temp file to final destination
        std::fs::rename(&temp_dest, dest_path)
            .map_err(|e| format!("Failed to move downloaded file to destination: {}", e))?;

        // On Unix, apply executable permission (0o755)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if let Ok(metadata) = std::fs::metadata(dest_path) {
                let mut perms = metadata.permissions();
                perms.set_mode(0o755);
                let _ = std::fs::set_permissions(dest_path, perms);
            }
        }

        Ok(())
    }

    /// Automatically bootstrap `yt-dlp` into the user tools directory.
    pub async fn bootstrap_yt_dlp<F>(progress_cb: F, cancel_signal: Arc<AtomicBool>) -> Result<PathBuf, String>
    where
        F: Fn(u64, Option<u64>) + Send + 'static,
    {
        let (url, filename) = OfficialToolUrls::yt_dlp_url();
        let target_path = ToolResolver::user_tools_dir().join(filename);

        Self::download_file(url, &target_path, progress_cb, cancel_signal).await?;
        ToolResolver::activate_user_tools_path();

        Ok(target_path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_tools_dir_is_not_empty() {
        let dir = ToolResolver::user_tools_dir();
        assert!(!dir.as_os_str().is_empty());
        assert!(dir.ends_with("bin"));
    }

    #[test]
    fn test_yt_dlp_url_resolution() {
        let (url, filename) = OfficialToolUrls::yt_dlp_url();
        assert!(url.starts_with("https://github.com/yt-dlp/yt-dlp/releases"));
        assert!(filename.starts_with("yt-dlp"));
    }

    #[test]
    fn test_tool_probe_returns_struct() {
        let probe = ToolResolver::probe_tool("omnirip_nonexistent_tool_xyz");
        assert_eq!(probe.name, "omnirip_nonexistent_tool_xyz");
        assert!(!probe.is_installed);
        assert!(probe.resolved_path.is_none());
    }

    #[test]
    fn test_activate_user_tools_path() {
        ToolResolver::activate_user_tools_path();
        let path = std::env::var("PATH").unwrap();
        let tools_dir = ToolResolver::user_tools_dir();
        assert!(path.contains(tools_dir.to_str().unwrap()));
    }
}
