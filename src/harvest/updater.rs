use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

/// GitHub Release API JSON structures.
#[derive(Debug, Deserialize)]
struct GitHubRelease {
    tag_name: String,
    name: Option<String>,
    body: Option<String>,
    assets: Vec<GitHubAsset>,
}

#[derive(Debug, Deserialize)]
struct GitHubAsset {
    name: String,
    browser_download_url: String,
}

/// Information about an available update.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateInfo {
    pub current_version: String,
    pub latest_version: String,
    pub has_update: bool,
    pub download_url: String,
    pub release_name: String,
    pub release_notes: String,
}

/// Parses a semantic version string (e.g., "0.2.1" or "v0.2.1") into (major, minor, patch).
pub fn parse_semver(v: &str) -> (u32, u32, u32) {
    let clean = v.trim().trim_start_matches('v').trim_start_matches('V');
    let mut parts = clean.split('.');
    let major = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let minor = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let patch = parts.next().and_then(|s| s.split('-').next()?.parse().ok()).unwrap_or(0);
    (major, minor, patch)
}

/// Compares two version strings. Returns true if `remote` is strictly newer than `local`.
pub fn is_newer_version(local: &str, remote: &str) -> bool {
    let (l_maj, l_min, l_pat) = parse_semver(local);
    let (r_maj, r_min, r_pat) = parse_semver(remote);

    if r_maj > l_maj {
        return true;
    }
    if r_maj == l_maj && r_min > l_min {
        return true;
    }
    if r_maj == l_maj && r_min == l_min && r_pat > l_pat {
        return true;
    }

    false
}

/// Returns the expected release asset archive name for the current platform.
pub fn expected_asset_name() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "omnirip-macos-arm64.tar.gz";

    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "omnirip-macos-x86_64.tar.gz";

    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "omnirip-linux-x86_64.tar.gz";

    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    return "omnirip-windows-x64.zip";

    #[cfg(not(any(
        all(target_os = "macos", target_arch = "aarch64"),
        all(target_os = "macos", target_arch = "x86_64"),
        all(target_os = "linux", target_arch = "x86_64"),
        all(target_os = "windows", target_arch = "x86_64")
    )))]
    return "omnirip.tar.gz";
}

/// Checks the GitHub Releases API for the latest version.
pub async fn check_latest_release(repo: &str) -> Result<Option<UpdateInfo>, String> {
    let url = format!("https://api.github.com/repos/{}/releases/latest", repo);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .user_agent("OmniRip-SelfUpdater/0.2.0")
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let res = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("GitHub API request failed: {}", e))?;

    if res.status() == reqwest::StatusCode::NOT_FOUND {
        return Ok(None);
    }

    if !res.status().is_success() {
        return Err(format!("GitHub API returned HTTP {}", res.status()));
    }

    let release: GitHubRelease = res
        .json()
        .await
        .map_err(|e| format!("Failed to parse GitHub release JSON: {}", e))?;

    let current_ver = env!("CARGO_PKG_VERSION").to_string();
    let remote_tag = release.tag_name.clone();
    let has_update = is_newer_version(&current_ver, &remote_tag);

    let asset_name = expected_asset_name();
    let download_url = release
        .assets
        .iter()
        .find(|a| a.name == asset_name || a.name.contains(asset_name))
        .map(|a| a.browser_download_url.clone())
        .unwrap_or_else(|| {
            format!(
                "https://github.com/{}/releases/download/{}/{}",
                repo, remote_tag, asset_name
            )
        });

    Ok(Some(UpdateInfo {
        current_version: current_ver,
        latest_version: remote_tag,
        has_update,
        download_url,
        release_name: release.name.unwrap_or_default(),
        release_notes: release.body.unwrap_or_default(),
    }))
}

/// Downloads the release archive and atomically replaces the currently executing binary.
pub async fn apply_self_update<F>(
    download_url: &str,
    progress_cb: F,
    cancel_signal: Arc<AtomicBool>,
) -> Result<PathBuf, String>
where
    F: Fn(u64, Option<u64>) + Send + 'static,
{
    let current_exe = std::env::current_exe()
        .map_err(|e| format!("Failed to get current executable path: {}", e))?;

    let temp_dir = std::env::temp_dir().join(format!("omnirip_update_{}", std::process::id()));
    let _ = std::fs::create_dir_all(&temp_dir);

    let is_zip = download_url.ends_with(".zip");
    let archive_path = temp_dir.join(if is_zip { "update.zip" } else { "update.tar.gz" });

    // 1. Download asset archive
    crate::harvest::bootstrap::ToolBootstrapper::download_file(
        download_url,
        &archive_path,
        progress_cb,
        cancel_signal,
    )
    .await?;

    // 2. Unpack archive
    let extract_dir = temp_dir.join("extracted");
    let _ = std::fs::create_dir_all(&extract_dir);

    if is_zip {
        // Windows or zip archive: use tar or powershell
        let status = Command::new("tar")
            .args(["-xf", archive_path.to_str().unwrap(), "-C", extract_dir.to_str().unwrap()])
            .status();

        if status.is_err() || !status.unwrap().success() {
            // Fallback for Windows PowerShell Expand-Archive
            let ps_cmd = format!(
                "Expand-Archive -Path '{}' -DestinationPath '{}' -Force",
                archive_path.to_str().unwrap(),
                extract_dir.to_str().unwrap()
            );
            let ps_status = Command::new("powershell")
                .args(["-Command", &ps_cmd])
                .status()
                .map_err(|e| format!("Failed to unpack zip archive: {}", e))?;

            if !ps_status.success() {
                return Err("Failed to extract update zip archive.".to_string());
            }
        }
    } else {
        // Unix tar.gz: invoke native tar
        let status = Command::new("tar")
            .args(["-xzf", archive_path.to_str().unwrap(), "-C", extract_dir.to_str().unwrap()])
            .status()
            .map_err(|e| format!("Failed to invoke tar: {}", e))?;

        if !status.success() {
            return Err("tar extraction failed with non-zero exit status.".to_string());
        }
    }

    // 3. Locate new omnirip binary inside extracted folder
    let binary_name = if cfg!(target_os = "windows") { "omnirip.exe" } else { "omnirip" };
    let mut new_bin: Option<PathBuf> = None;

    if extract_dir.join(binary_name).is_file() {
        new_bin = Some(extract_dir.join(binary_name));
    } else if extract_dir.join("bin").join(binary_name).is_file() {
        new_bin = Some(extract_dir.join("bin").join(binary_name));
    } else {
        // Search recursively in extract_dir
        if let Ok(entries) = std::fs::read_dir(&extract_dir) {
            for entry in entries.flatten() {
                if entry.path().is_dir() {
                    let candidate = entry.path().join(binary_name);
                    if candidate.is_file() {
                        new_bin = Some(candidate);
                        break;
                    }
                }
            }
        }
    }

    let new_bin_path = new_bin.ok_or("Failed to locate new omnirip binary in extracted release archive.")?;

    // 4. On Unix, ensure 0o755 permissions
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(&new_bin_path) {
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = std::fs::set_permissions(&new_bin_path, perms);
        }
    }

    // 5. Perform atomic swap over current_exe
    atomic_replace_binary(&new_bin_path, &current_exe)?;

    // 6. Cleanup temp archive
    let _ = std::fs::remove_dir_all(&temp_dir);

    Ok(current_exe)
}

/// Atomically replaces target binary file with source binary.
fn atomic_replace_binary(new_binary: &Path, target_exe: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        // On Unix, std::fs::rename atomically unlinks the old file and points the path to the new inode
        let temp_target = target_exe.with_extension("new_version");
        std::fs::copy(new_binary, &temp_target)
            .map_err(|e| format!("Failed to copy new binary to staging: {}", e))?;

        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(&temp_target) {
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = std::fs::set_permissions(&temp_target, perms);
        }

        std::fs::rename(&temp_target, target_exe)
            .map_err(|e| format!("Failed to atomically replace executable: {}", e))?;

        Ok(())
    }

    #[cfg(windows)]
    {
        let old_exe = target_exe.with_extension("old_version");
        let _ = std::fs::remove_file(&old_exe);

        std::fs::rename(target_exe, &old_exe)
            .map_err(|e| format!("Failed to rename running executable: {}", e))?;

        std::fs::copy(new_binary, target_exe)
            .map_err(|e| format!("Failed to copy new executable: {}", e))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_semver_basic() {
        assert_eq!(parse_semver("0.2.0"), (0, 2, 0));
        assert_eq!(parse_semver("v0.2.1"), (0, 2, 1));
        assert_eq!(parse_semver("1.0.0-beta"), (1, 0, 0));
    }

    #[test]
    fn test_is_newer_version_comparisons() {
        assert!(is_newer_version("0.2.0", "0.2.1"));
        assert!(is_newer_version("0.2.0", "v0.3.0"));
        assert!(is_newer_version("0.2.0", "1.0.0"));
        assert!(!is_newer_version("0.2.1", "0.2.0"));
        assert!(!is_newer_version("0.2.0", "0.2.0"));
        assert!(!is_newer_version("1.0.0", "0.9.9"));
    }

    #[test]
    fn test_expected_asset_name_not_empty() {
        let asset = expected_asset_name();
        assert!(!asset.is_empty());
        assert!(asset.contains("omnirip"));
    }
}
