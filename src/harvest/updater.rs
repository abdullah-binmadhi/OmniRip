use crate::harvest::integrity;
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Default GitHub repository used for self-update checks.
pub const UPDATE_REPO: &str = "abdullah-binmadhi/Orchestria";

/// Minimum valid size (1 MB) for an extracted Orchestria native executable.
pub const MIN_VALID_BINARY_BYTES: u64 = 1_000_000;

/// Release signing key, in minisign's base64 format.
/// When configured (non-empty), `apply_self_update` enforces Ed25519 signature verification on
/// `SHA256SUMS.minisig` in addition to `SHA256SUMS` digest and native binary magic verification.
pub const UPDATE_PUBLIC_KEY: &str = "";

/// GitHub Release API JSON structures.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GitHubRelease {
    pub tag_name: String,
    pub name: Option<String>,
    pub body: Option<String>,
    #[serde(default)]
    pub assets: Vec<GitHubAsset>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GitHubAsset {
    pub name: String,
    pub browser_download_url: String,
}

/// Information about an available update (SemVer release or rolling commit release).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub current_version: String,
    pub latest_version: String,
    pub has_update: bool,
    pub download_url: String,
    pub release_name: String,
    pub release_notes: String,
    pub remote_sha: Option<String>,
    pub simple_notes: Vec<String>,
    pub is_homebrew: bool,
    pub driver_version: Option<u32>,
}

impl UpdateInfo {
    /// Human-friendly label for the incoming build (e.g. `0.2.0 (a1b2c3d)`).
    pub fn display_version(&self) -> String {
        let clean = self
            .latest_version
            .trim()
            .trim_start_matches('v')
            .trim_start_matches('V')
            .trim_end_matches("-rolling");
        match self.remote_sha.as_deref() {
            Some(sha) if sha != "unknown" && !sha.is_empty() => {
                format!("{} ({})", clean, short_sha(sha))
            }
            _ => clean.to_string(),
        }
    }

    /// Human-friendly label for the currently running build.
    pub fn current_display_version(&self) -> String {
        let clean = self
            .current_version
            .trim()
            .trim_start_matches('v')
            .trim_start_matches('V');
        let sha = current_build_sha();
        if sha != "unknown" && !sha.is_empty() {
            format!("{} ({})", clean, short_sha(sha))
        } else {
            clean.to_string()
        }
    }
}

/// Persisted state tracking the last seen build SHA and any pending Post-Update "What's New" popup.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct LastSeenBuild {
    pub last_seen_sha: String,
    pub last_seen_version: String,
    pub pending_whats_new: Vec<String>,
    pub updated_to_label: Option<String>,
}

/// Returns the compile-time Git SHA baked by `build.rs`, or `"unknown"`.
pub fn current_build_sha() -> &'static str {
    option_env!("ORCHESTRIA_GIT_SHA").unwrap_or("unknown")
}

/// Returns the compile-time Unix commit timestamp baked by `build.rs`, or `0`.
pub fn current_commit_timestamp() -> i64 {
    option_env!("ORCHESTRIA_COMMIT_TS")
        .and_then(|s| s.trim().parse::<i64>().ok())
        .unwrap_or(0)
}

/// Formats a Git SHA down to its 7-character short form.
pub fn short_sha(sha: &str) -> &str {
    let trimmed = sha.trim();
    if trimmed.len() >= 7 {
        &trimmed[..7]
    } else {
        trimmed
    }
}

/// Extracts `<!-- orchestria-sha:40_HEX_CHARS -->` from a GitHub Release body.
pub fn extract_release_sha(body: Option<&str>) -> Option<String> {
    let text = body?;
    let marker = "<!-- orchestria-sha:";
    let start = text.find(marker)? + marker.len();
    let rest = &text[start..];
    let end = rest.find("-->")?;
    let sha = rest[..end].trim().to_ascii_lowercase();
    if sha.len() >= 7 && sha.chars().all(|c| c.is_ascii_hexdigit()) {
        Some(sha)
    } else {
        None
    }
}

/// Extracts `<!-- orchestria-ts:UNIX_EPOCH -->` from a GitHub Release body.
pub fn extract_release_timestamp(body: Option<&str>) -> Option<i64> {
    let text = body?;
    let marker = "<!-- orchestria-ts:";
    let start = text.find(marker)? + marker.len();
    let rest = &text[start..];
    let end = rest.find("-->")?;
    rest[..end].trim().parse::<i64>().ok()
}

/// Extracts `<!-- orchestria-driver-ver:N -->` from a GitHub Release body.
pub fn extract_release_driver_version(body: Option<&str>) -> Option<u32> {
    let text = body?;
    let marker = "<!-- orchestria-driver-ver:";
    let start = text.find(marker)? + marker.len();
    let rest = &text[start..];
    let end = rest.find("-->")?;
    rest[..end].trim().parse::<u32>().ok()
}

/// Checks if a given executable path resides inside a Homebrew prefix or Cellar.
pub fn is_homebrew_binary_path(path: &Path) -> bool {
    let s = path.to_string_lossy();
    s.contains("/Cellar/orchestria/")
        || s.contains("/homebrew/bin/orchestria")
        || s.contains("/linuxbrew/.linuxbrew/bin/orchestria")
}

/// Checks if the currently executing binary is managed by Homebrew.
pub fn is_homebrew_install() -> bool {
    std::env::current_exe()
        .ok()
        .map(|p| {
            let canonical = std::fs::canonicalize(&p).unwrap_or(p.clone());
            is_homebrew_binary_path(&p) || is_homebrew_binary_path(&canonical)
        })
        .unwrap_or(false)
}

/// Parses a semantic version string (e.g., "0.2.1" or "v0.2.1-rolling") into (major, minor, patch).
pub fn parse_semver(v: &str) -> (u32, u32, u32) {
    let clean = v.trim().trim_start_matches('v').trim_start_matches('V');
    let mut parts = clean.split('.');
    let major = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let minor = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let patch = parts
        .next()
        .and_then(|s| s.split('-').next()?.parse().ok())
        .unwrap_or(0);
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

/// Translates raw GitHub Release notes or commit messages into up to 5 plain-English,
/// jargon-free bullet points prefixed with `[NEW]`, `[FIXED]`, or `[IMPROVED]`.
pub fn simplify_release_notes(raw_body: &str) -> Vec<String> {
    let mut bullets: Vec<String> = Vec::new();

    // 1. If the release body contains an explicit <!-- orchestria-notes-start --> block, parse it first.
    if let (Some(start_idx), Some(end_idx)) = (
        raw_body.find("<!-- orchestria-notes-start -->"),
        raw_body.find("<!-- orchestria-notes-end -->"),
    ) {
        let inner_start = start_idx + "<!-- orchestria-notes-start -->".len();
        if inner_start < end_idx {
            for line in raw_body[inner_start..end_idx].lines() {
                if let Some(translated) = translate_single_note_line(line) {
                    push_unique_bullet(&mut bullets, translated);
                }
            }
        }
    }

    // 2. Also scan the rest of the release body if we still need bullets.
    if bullets.is_empty() {
        for line in raw_body.lines() {
            if let Some(translated) = translate_single_note_line(line) {
                push_unique_bullet(&mut bullets, translated);
            }
            if bullets.len() >= 5 {
                break;
            }
        }
    }

    bullets.truncate(5);
    if bullets.is_empty() {
        bullets.push(
            "[IMPROVED] Faster performance, cleaner sound routing, and stability improvements."
                .to_string(),
        );
    }
    bullets
}

fn push_unique_bullet(bullets: &mut Vec<String>, candidate: String) {
    if bullets.len() >= 5 {
        return;
    }
    let norm = candidate.to_ascii_lowercase();
    if !bullets.iter().any(|b| b.to_ascii_lowercase() == norm) {
        bullets.push(candidate);
    }
}

fn translate_single_note_line(raw_line: &str) -> Option<String> {
    let trimmed = raw_line.trim();
    if trimmed.is_empty()
        || trimmed.starts_with("<!--")
        || trimmed.starts_with('#')
        || trimmed.starts_with("Full Changelog")
        || trimmed.starts_with("**Full Changelog**")
    {
        return None;
    }

    // Strip leading markdown list markers (`- `, `* `, `+ `, `• `, `1. `)
    let mut line = trimmed
        .trim_start_matches(|c: char| matches!(c, '-' | '*' | '+' | '•'))
        .trim();
    if let Some((num, rest)) = line.split_once('.') {
        if !num.is_empty() && num.chars().all(|c| c.is_ascii_digit()) {
            line = rest.trim();
        }
    }
    if line.is_empty() {
        return None;
    }

    // Honor explicit `Simple:` or `Note:` override lines from commit messages verbatim.
    for prefix in ["Simple:", "simple:", "Note:", "note:"] {
        if let Some(custom) = line.strip_prefix(prefix) {
            let clean = custom.trim();
            if !clean.is_empty() {
                if clean.starts_with("[NEW]")
                    || clean.starts_with("[FIXED]")
                    || clean.starts_with("[IMPROVED]")
                {
                    return Some(ensure_period(clean));
                }
                return Some(format!("[IMPROVED] {}", ensure_period(clean)));
            }
        }
    }

    // Already formatted with our friendly badge?
    for badge in ["[NEW]", "[FIXED]", "[IMPROVED]"] {
        if let Some(rest) = line.strip_prefix(badge) {
            let cleaned = strip_github_trailers(rest.trim());
            if !cleaned.is_empty() {
                return Some(format!("{} {}", badge, ensure_period(&cleaned)));
            }
        }
    }

    let lower = line.to_ascii_lowercase();

    // Filter out non-user-facing noise (merges, chores, tests, CI, version bumps)
    if lower.starts_with("merge pull request")
        || lower.starts_with("merge branch")
        || lower.starts_with("chore")
        || lower.starts_with("ci:")
        || lower.starts_with("ci(")
        || lower.starts_with("test:")
        || lower.starts_with("test(")
        || lower.starts_with("tests:")
        || lower.starts_with("docs:")
        || lower.starts_with("docs(")
        || lower.starts_with("style:")
        || lower.starts_with("build:")
        || lower.starts_with("bump ")
    {
        return None;
    }

    // Determine category badge from conventional commit prefix or verbs
    let badge = if lower.starts_with("feat")
        || lower.starts_with("add ")
        || lower.starts_with("added ")
        || lower.starts_with("introduce")
    {
        "[NEW]"
    } else if lower.starts_with("fix")
        || lower.starts_with("resolve")
        || lower.starts_with("prevent")
        || lower.starts_with("repair")
        || lower.contains("bug")
        || lower.contains("crash")
    {
        "[FIXED]"
    } else {
        "[IMPROVED]"
    };

    // Strip conventional commit prefix like `feat(audio):` or `fix:`
    let stripped = strip_conventional_prefix(line);
    let stripped = strip_github_trailers(&stripped);
    if stripped.is_empty() {
        return None;
    }

    let s_lower = stripped.to_ascii_lowercase();

    // Domain-aware plain-English translation rules (zero technical jargon)
    if s_lower.contains("orange dot")
        || s_lower.contains("shm")
        || (s_lower.contains("hal") && s_lower.contains("zero"))
    {
        return Some(format!(
            "{} System-wide sound processing now runs silently in the background without triggering the macOS orange microphone indicator.",
            badge
        ));
    }
    if (s_lower.contains("input_capture") || s_lower.contains("x key") || s_lower.contains("airpods") || s_lower.contains("cycle_engine") || s_lower.contains("audio engine"))
        && (s_lower.contains("restore") || s_lower.contains("output") || s_lower.contains("switch") || s_lower.contains("toggle") || s_lower.contains("dac"))
    {
        return Some(format!(
            "{} Switching between the Orchestria Sound Engine and your external DAC or headphones now works smoothly in both directions.",
            badge
        ));
    }
    if (s_lower.contains("hotplug") || s_lower.contains("hot-plug") || s_lower.contains("dac") || s_lower.contains("rescan"))
        && (s_lower.contains("output") || s_lower.contains("switch") || s_lower.contains("detect") || s_lower.contains("recover") || s_lower.contains("unplug"))
    {
        return Some(format!(
            "{} Plugging in headphones or a USB DAC now switches automatically with no app restart needed.",
            badge
        ));
    }
    if s_lower.contains("routing") && (s_lower.contains("redesign") || s_lower.contains("layout") || s_lower.contains("audition") || s_lower.contains("chart")) {
        return Some(format!(
            "{} Upgraded the Audio Routing screen with live sound charts, connected device list, and instant DAC switching.",
            badge
        ));
    }
    if s_lower.contains("wasapi") || s_lower.contains("ipolicyconfig") || (s_lower.contains("windows") && s_lower.contains("eq")) {
        return Some(format!(
            "{} Smoother system-wide sound setup and automatic speaker routing on Windows.",
            badge
        ));
    }
    if s_lower.contains("pipewire") || s_lower.contains("pulseaudio") || s_lower.contains("pactl") {
        return Some(format!(
            "{} Instant system-wide audio routing on Linux with zero password prompts.",
            badge
        ));
    }
    if s_lower.contains("touch id")
        || s_lower.contains("osascript")
        || s_lower.contains("first-run")
        || s_lower.contains("guided setup")
        || s_lower.contains("onboarding")
    {
        return Some(format!(
            "{} Easier one-click sound engine setup with native system permission prompts.",
            badge
        ));
    }
    if s_lower.contains("auto-update")
        || s_lower.contains("autoupdate")
        || s_lower.contains("rolling")
        || s_lower.contains("self-update")
        || s_lower.contains("what's new")
    {
        return Some(format!(
            "{} Automatic background updates with simple summaries of what's new and fixed.",
            badge
        ));
    }
    if s_lower.contains("biquad")
        || s_lower.contains("crossfader")
        || s_lower.contains("pultec")
        || s_lower.contains("enhancer")
        || s_lower.contains("dac")
        || s_lower.contains("autoeq")
    {
        return Some(format!(
            "{} Cleaner, richer sound quality and smoother EQ adjustments across your headphones and speakers.",
            badge
        ));
    }
    if s_lower.contains("slskd")
        || s_lower.contains("soulseek")
        || s_lower.contains("nicotine")
        || s_lower.contains("spectral")
        || s_lower.contains("flac")
    {
        return Some(format!(
            "{} Faster and more reliable high-quality music search and lossless verification.",
            badge
        ));
    }
    if s_lower.contains("yt-dlp") || s_lower.contains("ffmpeg") || s_lower.contains("stream") {
        return Some(format!(
            "{} More reliable music downloading and smoother cloud audio streaming.",
            badge
        ));
    }

    // Generic plain-English cleanup: remove file paths, module names, and code ticks
    let humanized = humanize_free_text(&stripped);
    if humanized.len() < 4 {
        return None;
    }
    Some(format!("{} {}", badge, ensure_period(&humanized)))
}

fn strip_conventional_prefix(line: &str) -> String {
    if let Some((head, tail)) = line.split_once(':') {
        let h = head.trim().to_ascii_lowercase();
        let known = [
            "feat", "fix", "perf", "refactor", "ui", "audio", "dsp", "harvest", "driver",
            "update", "updater", "improve",
        ];
        if known
            .iter()
            .any(|k| h == *k || h.starts_with(&format!("{}(", k)) || h.starts_with(&format!("{}!", k)))
        {
            return tail.trim().to_string();
        }
    }
    line.trim().to_string()
}

fn strip_github_trailers(line: &str) -> String {
    let mut s = line.trim().to_string();
    // Strip ` by @user in https://...`
    if let Some(idx) = s.find(" by @") {
        s.truncate(idx);
    }
    if let Some(idx) = s.find(" in https://") {
        s.truncate(idx);
    }
    // Strip trailing `(#123)` PR reference
    if let Some(open) = s.rfind("(#") {
        if s.ends_with(')') && s[open + 2..s.len() - 1].chars().all(|c| c.is_ascii_digit()) {
            s.truncate(open);
        }
    }
    s.trim().to_string()
}

fn humanize_free_text(input: &str) -> String {
    let mut words = Vec::new();
    for raw_word in input.split_whitespace() {
        let clean = raw_word.trim_matches('`');
        // Skip raw file paths or Rust module paths like `src/dsp/streamer.rs` or `foo::bar`
        if clean.contains("src/")
            || clean.contains(".rs")
            || clean.contains("::")
            || clean.starts_with("0x")
        {
            continue;
        }
        words.push(clean);
    }
    let joined = words.join(" ");
    let mut chars = joined.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}

fn ensure_period(s: &str) -> String {
    let trimmed = s.trim();
    if trimmed.ends_with('.') || trimmed.ends_with('!') || trimmed.ends_with('?') {
        trimmed.to_string()
    } else {
        format!("{}.", trimmed)
    }
}

/// Returns the expected release asset archive name for the current platform.
pub fn expected_asset_name() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "orchestria-macos-arm64.tar.gz";

    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "orchestria-macos-x86_64.tar.gz";

    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    return "orchestria-linux-x86_64.tar.gz";

    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    return "orchestria-windows-x64.zip";

    #[cfg(not(any(
        all(target_os = "macos", target_arch = "aarch64"),
        all(target_os = "macos", target_arch = "x86_64"),
        all(target_os = "linux", target_arch = "x86_64"),
        all(target_os = "windows", target_arch = "x86_64")
    )))]
    return "orchestria.tar.gz";
}

/// Evaluates a `GitHubRelease` against the running binary's SemVer version, commit SHA, and timestamp.
/// Returns `Some(UpdateInfo)` always so callers can inspect `has_update` or display release metadata.
pub fn evaluate_release_update(
    release: &GitHubRelease,
    current_version: &str,
    local_sha: &str,
    local_ts: i64,
    asset_name: &str,
    is_homebrew: bool,
) -> UpdateInfo {
    let remote_tag = release.tag_name.trim().to_string();
    let remote_sha = extract_release_sha(release.body.as_deref());
    let remote_ts = extract_release_timestamp(release.body.as_deref()).unwrap_or(0);
    let driver_version = extract_release_driver_version(release.body.as_deref());

    let semver_newer = is_newer_version(current_version, &remote_tag);
    let is_rolling_tag = remote_tag.ends_with("-rolling") || remote_tag == "latest";
    let remote_not_older_semver = !is_newer_version(&remote_tag, current_version);

    let sha_differs = match remote_sha.as_deref() {
        Some(r_sha) if local_sha != "unknown" && !local_sha.is_empty() => {
            !r_sha.eq_ignore_ascii_case(local_sha)
        }
        _ => false,
    };
    let timestamp_not_older = remote_ts == 0 || local_ts == 0 || remote_ts >= local_ts;

    let rolling_newer =
        is_rolling_tag && remote_not_older_semver && sha_differs && timestamp_not_older;
    let has_update = semver_newer || rolling_newer;

    let download_url = release
        .assets
        .iter()
        .find(|a| a.name == asset_name || a.name.contains(asset_name))
        .map(|a| a.browser_download_url.clone())
        .unwrap_or_else(|| {
            format!(
                "https://github.com/{}/releases/download/{}/{}",
                UPDATE_REPO, remote_tag, asset_name
            )
        });

    let raw_notes = release.body.clone().unwrap_or_default();
    let simple_notes = simplify_release_notes(&raw_notes);

    UpdateInfo {
        current_version: current_version.to_string(),
        latest_version: remote_tag,
        has_update,
        download_url,
        release_name: release.name.clone().unwrap_or_default(),
        release_notes: raw_notes,
        remote_sha,
        simple_notes,
        is_homebrew,
        driver_version,
    }
}

/// Checks the GitHub Releases API for the latest version (SemVer or rolling commit release).
pub async fn check_latest_release(repo: &str) -> Result<Option<UpdateInfo>, String> {
    let url = format!("https://api.github.com/repos/{}/releases/latest", repo);

    let client = reqwest::Client::builder()
        .connect_timeout(std::time::Duration::from_secs(10))
        .timeout(std::time::Duration::from_secs(15))
        .user_agent(format!("Orchestria-SelfUpdater/{}", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let res = client
        .get(&url)
        .header("Accept", "application/vnd.github+json")
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

    let info = evaluate_release_update(
        &release,
        env!("CARGO_PKG_VERSION"),
        current_build_sha(),
        current_commit_timestamp(),
        expected_asset_name(),
        is_homebrew_install(),
    );

    Ok(Some(info))
}

/// Path to `last_seen_build.json` used to trigger the one-time Post-Update "What's New" Welcome popup.
pub fn last_seen_build_path() -> PathBuf {
    crate::driver::bundle::user_driver_cache_dir()
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(crate::driver::bundle::user_driver_cache_dir)
        .join("last_seen_build.json")
}

/// Records the incoming update's plain-English release notes before restarting so the newly launched
/// binary can display the "What's New & Fixed" welcome popup once on startup.
pub fn record_pending_post_update_welcome(info: &UpdateInfo) {
    let _ = record_pending_post_update_welcome_at(&last_seen_build_path(), info);
}

pub fn record_pending_post_update_welcome_at(
    path: &Path,
    info: &UpdateInfo,
) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let state = LastSeenBuild {
        last_seen_sha: info
            .remote_sha
            .clone()
            .unwrap_or_else(|| current_build_sha().to_string()),
        last_seen_version: info.latest_version.clone(),
        pending_whats_new: if info.simple_notes.is_empty() {
            simplify_release_notes(&info.release_notes)
        } else {
            info.simple_notes.clone()
        },
        updated_to_label: Some(info.display_version()),
    };
    let json = serde_json::to_string_pretty(&state)?;
    std::fs::write(path, json)
}

/// Consumes and clears any pending Post-Update Welcome notes stored before restart.
pub fn take_post_update_welcome() -> Option<(String, Vec<String>)> {
    take_post_update_welcome_at(&last_seen_build_path())
}

pub fn take_post_update_welcome_at(path: &Path) -> Option<(String, Vec<String>)> {
    let raw = std::fs::read_to_string(path).ok()?;
    let mut state: LastSeenBuild = serde_json::from_str(&raw).ok()?;
    if state.pending_whats_new.is_empty() {
        return None;
    }
    let notes = std::mem::take(&mut state.pending_whats_new);
    let label = state
        .updated_to_label
        .take()
        .unwrap_or_else(|| state.last_seen_version.clone());
    state.last_seen_sha = current_build_sha().to_string();
    state.last_seen_version = env!("CARGO_PKG_VERSION").to_string();
    if let Ok(json) = serde_json::to_string_pretty(&state) {
        let _ = std::fs::write(path, json);
    }
    Some((label, notes))
}

/// `SHA256SUMS` and its `.minisig` signature, located next to the archive in the same release.
pub fn checksum_urls(archive_url: &str) -> Option<(String, String)> {
    let (dir, _) = archive_url.rsplit_once('/')?;
    Some((format!("{dir}/SHA256SUMS"), format!("{dir}/SHA256SUMS.minisig")))
}

async fn fetch_text(client: &reqwest::Client, url: &str) -> Result<String, String> {
    let response = client
        .get(url)
        .send()
        .await
        .and_then(|response| response.error_for_status())
        .map_err(|e| format!("Could not fetch {}: {}", url, e))?;
    response
        .text()
        .await
        .map_err(|e| format!("Could not read {}: {}", url, e))
}

/// Validates that the first 4 bytes of an extracted executable match the current OS's native
/// binary magic header (Mach-O on macOS, ELF on Linux, PE MZ on Windows).
pub fn has_valid_native_magic(hdr: &[u8]) -> bool {
    if hdr.len() < 4 {
        return false;
    }
    #[cfg(target_os = "macos")]
    {
        matches!(
            [hdr[0], hdr[1], hdr[2], hdr[3]],
            [0xCF, 0xFA, 0xED, 0xFE]
                | [0xFE, 0xED, 0xFA, 0xCF]
                | [0xCA, 0xFE, 0xBA, 0xBE]
                | [0xBE, 0xBA, 0xFE, 0xCA]
        )
    }
    #[cfg(target_os = "linux")]
    {
        hdr[0..4] == [0x7F, b'E', b'L', b'F']
    }
    #[cfg(target_os = "windows")]
    {
        hdr[0..2] == [b'M', b'Z']
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    {
        true
    }
}

/// verifies that `bin_path` is a valid, non-truncated native executable for this OS.
pub fn verify_extracted_binary(bin_path: &Path) -> Result<(), String> {
    let meta = std::fs::metadata(bin_path)
        .map_err(|e| format!("Cannot stat extracted binary {}: {}", bin_path.display(), e))?;
    if meta.len() < MIN_VALID_BINARY_BYTES {
        return Err(format!(
            "Extracted binary is unexpectedly small ({} bytes < {} minimum). Refusing to install.",
            meta.len(),
            MIN_VALID_BINARY_BYTES
        ));
    }
    let mut file = std::fs::File::open(bin_path)
        .map_err(|e| format!("Cannot open extracted binary: {}", e))?;
    let mut hdr = [0u8; 4];
    file.read_exact(&mut hdr)
        .map_err(|e| format!("Cannot read binary magic header: {}", e))?;
    if !has_valid_native_magic(&hdr) {
        return Err(
            "Extracted binary failed native OS executable header check (Mach-O/ELF/PE).".to_string(),
        );
    }
    Ok(())
}

/// Path where the single-generation rollback binary (`orchestria.prev`) is stored before any self-update.
pub fn rollback_binary_path() -> PathBuf {
    let name = if cfg!(target_os = "windows") {
        "orchestria.prev.exe"
    } else {
        "orchestria.prev"
    };
    crate::driver::bundle::user_driver_cache_dir()
        .join("rollback")
        .join(name)
}

/// Saves a backup of `current_exe` to `rollback_binary_path()` so `--rollback` / `:rollback` can
/// restore the previous known-good binary in one command.
pub fn save_rollback_backup(current_exe: &Path) -> Result<PathBuf, String> {
    save_rollback_backup_to(current_exe, &rollback_binary_path())
}

pub fn save_rollback_backup_to(current_exe: &Path, backup_dest: &Path) -> Result<PathBuf, String> {
    if !current_exe.is_file() {
        return Err(format!(
            "Current executable {} does not exist",
            current_exe.display()
        ));
    }
    if let Some(parent) = backup_dest.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create rollback directory: {}", e))?;
    }
    std::fs::copy(current_exe, backup_dest)
        .map_err(|e| format!("Failed to save rollback backup: {}", e))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(backup_dest) {
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = std::fs::set_permissions(backup_dest, perms);
        }
    }
    Ok(backup_dest.to_path_buf())
}

/// Restores the previous binary saved at `rollback_binary_path()` over the currently running executable.
pub fn apply_rollback() -> Result<PathBuf, String> {
    let current_exe = std::env::current_exe()
        .map_err(|e| format!("Failed to locate current executable: {}", e))?;
    apply_rollback_from(&rollback_binary_path(), &current_exe)
}

pub fn apply_rollback_from(backup_path: &Path, target_exe: &Path) -> Result<PathBuf, String> {
    if !backup_path.is_file() {
        return Err(format!(
            "No rollback backup found at {}. A backup is created automatically during your first self-update.",
            backup_path.display()
        ));
    }
    verify_extracted_binary(backup_path)?;
    atomic_replace_binary(backup_path, target_exe)?;
    Ok(target_exe.to_path_buf())
}

/// Cleans up any leftover `.old_version` or `.new_version` staging binaries next to `current_exe`.
pub fn cleanup_legacy_update_files() {
    if let Ok(exe) = std::env::current_exe() {
        let _ = std::fs::remove_file(exe.with_extension("old_version"));
        let _ = std::fs::remove_file(exe.with_extension("new_version"));
    }
}

/// Downloads `url` into `dest_path` with HTTP Range resume (`Range: bytes={offset}-`),
/// up to 3 automatic retries, and mandatory SHA-256 verification.
pub async fn download_archive_with_resume<F>(
    url: &str,
    dest_path: &Path,
    progress_cb: &F,
    cancel_signal: &Arc<AtomicBool>,
    expected_sha256: Option<&str>,
) -> Result<(), String>
where
    F: Fn(u64, Option<u64>) + Send + 'static,
{
    if let Some(parent) = dest_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let part_path = dest_path.with_extension("part");
    let client = reqwest::Client::builder()
        .connect_timeout(std::time::Duration::from_secs(10))
        .timeout(std::time::Duration::from_secs(120))
        .user_agent(format!("Orchestria-SelfUpdater/{}", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let mut last_err = String::new();
    for attempt in 1..=3 {
        if cancel_signal.load(Ordering::Relaxed) {
            let _ = std::fs::remove_file(&part_path);
            return Err("Update canceled by user.".to_string());
        }

        let existing_len = std::fs::metadata(&part_path).map(|m| m.len()).unwrap_or(0);
        let mut req = client.get(url);
        if existing_len > 0 {
            req = req.header("Range", format!("bytes={}-", existing_len));
        }

        let res = match req.send().await {
            Ok(r) => r,
            Err(e) => {
                last_err = format!("Download attempt {}/3 failed: {}", attempt, e);
                continue;
            }
        };

        let status = res.status();
        if !status.is_success() {
            last_err = format!("Download failed with HTTP status {}", status);
            if status == reqwest::StatusCode::RANGE_NOT_SATISFIABLE {
                let _ = std::fs::remove_file(&part_path);
            }
            continue;
        }

        let is_partial = status == reqwest::StatusCode::PARTIAL_CONTENT && existing_len > 0;
        let total_size = res
            .content_length()
            .map(|len| if is_partial { existing_len + len } else { len });

        let file_res = if is_partial {
            std::fs::OpenOptions::new().append(true).open(&part_path)
        } else {
            std::fs::File::create(&part_path)
        };
        let mut file =
            file_res.map_err(|e| format!("Cannot open temporary download file: {}", e))?;
        let mut downloaded = if is_partial { existing_len } else { 0 };
        progress_cb(downloaded, total_size);

        let mut stream_ok = true;
        let mut response = res;
        loop {
            if cancel_signal.load(Ordering::Relaxed) {
                let _ = std::fs::remove_file(&part_path);
                return Err("Update canceled by user.".to_string());
            }
            match response.chunk().await {
                Ok(Some(chunk)) => {
                    if let Err(e) = file.write_all(&chunk) {
                        return Err(format!("Failed writing update archive to disk: {}", e));
                    }
                    downloaded += chunk.len() as u64;
                    progress_cb(downloaded, total_size);
                }
                Ok(None) => break,
                Err(e) => {
                    last_err = format!("Stream interrupted on attempt {}/3: {}", attempt, e);
                    stream_ok = false;
                    break;
                }
            }
        }
        let _ = file.flush();
        drop(file);

        if stream_ok {
            if let Err(e) =
                crate::harvest::bootstrap::ToolBootstrapper::check_complete(downloaded, total_size)
            {
                last_err = e;
                let _ = std::fs::remove_file(&part_path);
                continue;
            }
            break;
        }
    }

    if !part_path.is_file() {
        return Err(if last_err.is_empty() {
            "Download failed.".to_string()
        } else {
            last_err
        });
    }

    if let Some(expected) = expected_sha256 {
        let actual = integrity::sha256_file(&part_path)?;
        if !actual.eq_ignore_ascii_case(expected.trim()) {
            let _ = std::fs::remove_file(&part_path);
            return Err(format!(
                "SHA-256 mismatch for {}: expected {}, got {}",
                url,
                expected.trim(),
                actual
            ));
        }
    }

    std::fs::rename(&part_path, dest_path)
        .map_err(|e| format!("Failed to finalize downloaded archive: {}", e))
}

/// Applies a self-update from `UpdateInfo`, recording its plain-English release notes for the
/// post-restart "What's New & Fixed" welcome popup.
pub async fn apply_self_update_with_info<F>(
    info: &UpdateInfo,
    progress_cb: F,
    cancel_signal: Arc<AtomicBool>,
) -> Result<PathBuf, String>
where
    F: Fn(u64, Option<u64>) + Send + 'static,
{
    let path = apply_self_update(&info.download_url, progress_cb, cancel_signal).await?;
    record_pending_post_update_welcome(info);
    Ok(path)
}

/// Downloads the release archive, verifies `SHA256SUMS` (plus `SHA256SUMS.minisig` when
/// `UPDATE_PUBLIC_KEY` is configured), validates the native executable magic and minimum size,
/// saves a rollback backup, and atomically replaces the currently executing binary.
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

    let temp_dir = std::env::temp_dir().join(format!("orchestria_update_{}", std::process::id()));
    let _ = std::fs::create_dir_all(&temp_dir);

    let is_zip = download_url.ends_with(".zip");
    let archive_path = temp_dir.join(if is_zip {
        "update.zip"
    } else {
        "update.tar.gz"
    });

    // 1. Fetch release SHA256SUMS and verify signature if UPDATE_PUBLIC_KEY is configured.
    let archive_name = download_url
        .rsplit('/')
        .next()
        .unwrap_or_default()
        .to_string();
    let (sums_url, sig_url) =
        checksum_urls(download_url).ok_or("Update URL is not a release asset URL")?;
    let client = reqwest::Client::builder()
        .connect_timeout(std::time::Duration::from_secs(10))
        .timeout(std::time::Duration::from_secs(30))
        .user_agent(format!("Orchestria-SelfUpdater/{}", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;
    let sums = fetch_text(&client, &sums_url).await?;
    if !UPDATE_PUBLIC_KEY.trim().is_empty() {
        let signature = fetch_text(&client, &sig_url).await?;
        integrity::verify_minisign(sums.as_bytes(), &signature, UPDATE_PUBLIC_KEY)?;
    }
    let expected = integrity::expected_sha256_for(&sums, &archive_name)
        .ok_or_else(|| format!("{} is missing from SHA256SUMS", archive_name))?;

    // 2. Download archive with HTTP Range resume and SHA-256 verification.
    download_archive_with_resume(
        download_url,
        &archive_path,
        &progress_cb,
        &cancel_signal,
        Some(expected.as_str()),
    )
    .await?;

    // 3. Unpack archive.
    let extract_dir = temp_dir.join("extracted");
    let _ = std::fs::create_dir_all(&extract_dir);

    if is_zip {
        let status = Command::new("tar")
            .args([
                "-xf",
                archive_path.to_str().unwrap(),
                "-C",
                extract_dir.to_str().unwrap(),
            ])
            .status();

        if status.is_err() || !status.unwrap().success() {
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
        let status = Command::new("tar")
            .args([
                "-xzf",
                archive_path.to_str().unwrap(),
                "-C",
                extract_dir.to_str().unwrap(),
            ])
            .status()
            .map_err(|e| format!("Failed to invoke tar: {}", e))?;

        if !status.success() {
            return Err("tar extraction failed with non-zero exit status.".to_string());
        }
    }

    // 4. Locate new orchestria binary inside extracted folder.
    let binary_name = if cfg!(target_os = "windows") {
        "orchestria.exe"
    } else {
        "orchestria"
    };
    let mut new_bin: Option<PathBuf> = None;

    if extract_dir.join(binary_name).is_file() {
        new_bin = Some(extract_dir.join(binary_name));
    } else if extract_dir.join("bin").join(binary_name).is_file() {
        new_bin = Some(extract_dir.join("bin").join(binary_name));
    } else if let Ok(entries) = std::fs::read_dir(&extract_dir) {
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

    let new_bin_path =
        new_bin.ok_or("Failed to locate new orchestria binary in extracted release archive.")?;

    // 5. Verify native executable magic (Mach-O / ELF / PE MZ) and minimum binary size (>= 1 MB).
    verify_extracted_binary(&new_bin_path)?;

    // 6. Save single-generation rollback backup of current_exe before modifying anything.
    let _ = save_rollback_backup(&current_exe);

    // 7. Perform atomic swap over current_exe (with macOS quarantine strip + ad-hoc codesign).
    atomic_replace_binary(&new_bin_path, &current_exe)?;

    // 8. Stage updated HAL driver bundle if present in the archive so next launch offers v2 upgrade.
    let extracted_driver = extract_dir.join("OrchestriaAudio.driver");
    if extracted_driver.is_dir() {
        let sibling_dest = current_exe
            .parent()
            .map(|p| p.join("OrchestriaAudio.driver"));
        let copied_sibling = sibling_dest
            .as_ref()
            .map(|dst| copy_dir_recursive(&extracted_driver, dst).is_ok())
            .unwrap_or(false);
        if !copied_sibling {
            let cache_dest =
                crate::driver::bundle::user_driver_cache_dir().join("OrchestriaAudio.driver");
            let _ = copy_dir_recursive(&extracted_driver, &cache_dest);
        }
    }

    // 9. Cleanup temp archive.
    let _ = std::fs::remove_dir_all(&temp_dir);

    Ok(current_exe)
}

fn copy_dir_recursive(src: &Path, dst: &Path) -> std::io::Result<()> {
    if dst.exists() {
        let _ = std::fs::remove_dir_all(dst);
    }
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let file_type = entry.file_type()?;
        let dst_path = dst.join(entry.file_name());
        if file_type.is_dir() {
            copy_dir_recursive(&entry.path(), &dst_path)?;
        } else {
            std::fs::copy(entry.path(), &dst_path)?;
        }
    }
    Ok(())
}

/// Atomically replaces target binary file with source binary.
fn atomic_replace_binary(new_binary: &Path, target_exe: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        let temp_target = target_exe.with_extension("new_version");
        std::fs::copy(new_binary, &temp_target)
            .map_err(|e| format!("Failed to copy new binary to staging: {}", e))?;

        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(&temp_target) {
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = std::fs::set_permissions(&temp_target, perms);
        }

        // On macOS, strip quarantine attribute and ad-hoc codesign the staged inode BEFORE
        // atomic rename so Apple Silicon kernel signature caches never SIGKILL the new binary.
        #[cfg(target_os = "macos")]
        {
            let _ = Command::new("xattr")
                .args(["-d", "com.apple.quarantine"])
                .arg(&temp_target)
                .output();
            let _ = Command::new("codesign")
                .args(["--force", "--sign", "-"])
                .arg(&temp_target)
                .output();
        }

        std::fs::rename(&temp_target, target_exe)
            .map_err(|e| format!("Failed to atomically replace executable: {}", e))?;

        Ok(())
    }

    #[cfg(windows)]
    {
        let staged = target_exe.with_extension("new_version");
        let old_exe = target_exe.with_extension("old_version");
        let _ = std::fs::remove_file(&staged);
        std::fs::copy(new_binary, &staged)
            .map_err(|e| format!("Failed to stage new executable: {}", e))?;

        let _ = std::fs::remove_file(&old_exe);
        if let Err(e) = std::fs::rename(target_exe, &old_exe) {
            let _ = std::fs::remove_file(&staged);
            return Err(format!(
                "Failed to move the running executable aside: {}",
                e
            ));
        }
        if let Err(e) = std::fs::rename(&staged, target_exe) {
            let _ = std::fs::rename(&old_exe, target_exe);
            let _ = std::fs::remove_file(&staged);
            return Err(format!("Failed to put the new executable in place: {}", e));
        }

        Ok(())
    }
}

/// Replaces the current process in-place with the newly updated binary on disk (Unix `execv`,
/// Windows child spawn + exit). Must be called AFTER `AudioStreamer::terminate()` and `TerminalGuard` drop.
pub fn restart_into_updated_binary() -> Result<(), String> {
    let exe = std::env::current_exe()
        .map_err(|e| format!("Failed to resolve current executable for restart: {}", e))?;
    let args: Vec<String> = std::env::args().skip(1).collect();

    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let err = Command::new(&exe).args(&args).exec();
        Err(format!("Failed to exec updated binary {}: {}", exe.display(), err))
    }

    #[cfg(windows)]
    {
        Command::new(&exe)
            .args(&args)
            .spawn()
            .map_err(|e| format!("Failed to spawn updated binary {}: {}", exe.display(), e))?;
        std::process::exit(0);
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
        assert_eq!(parse_semver("v0.2.0-rolling"), (0, 2, 0));
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
    fn checksum_urls_sit_next_to_the_archive() {
        let (sums, sig) = checksum_urls(
            "https://example.com/releases/download/v1/orchestria-linux-x86_64.tar.gz",
        )
        .expect("release asset URL");
        assert_eq!(
            sums,
            "https://example.com/releases/download/v1/SHA256SUMS"
        );
        assert_eq!(
            sig,
            "https://example.com/releases/download/v1/SHA256SUMS.minisig"
        );
    }

    #[test]
    fn test_expected_asset_name_not_empty() {
        let asset = expected_asset_name();
        assert!(!asset.is_empty());
        assert!(asset.contains("orchestria"));
    }

    #[test]
    fn test_extract_release_markers() {
        let body = "\
<!-- orchestria-sha:005bd19a1b2c3d4e5f60718293a4b5c6d7e8f9a0 -->
<!-- orchestria-ts:1763830000 -->
<!-- orchestria-driver-ver:2 -->
## What's Changed
";
        assert_eq!(
            extract_release_sha(Some(body)).as_deref(),
            Some("005bd19a1b2c3d4e5f60718293a4b5c6d7e8f9a0")
        );
        assert_eq!(extract_release_timestamp(Some(body)), Some(1763830000));
        assert_eq!(extract_release_driver_version(Some(body)), Some(2));
    }

    #[test]
    fn test_evaluate_release_update_detects_rolling_sha_change() {
        let release = GitHubRelease {
            tag_name: "v0.2.0-rolling".to_string(),
            name: Some("Orchestria Rolling Build".to_string()),
            body: Some(
                "<!-- orchestria-sha:bbbbbbb222222233333334444444555555566666 -->\n<!-- orchestria-ts:2000 -->\n- feat(audio): zero-dot SHM capture"
                    .to_string(),
            ),
            assets: vec![],
        };

        // Different SHA + newer timestamp on same SemVer -> has_update = true
        let info = evaluate_release_update(
            &release,
            "0.2.0",
            "aaaaaaa111111122222223333333444444455555",
            1000,
            "orchestria-macos-arm64.tar.gz",
            false,
        );
        assert!(info.has_update);
        assert_eq!(info.display_version(), "0.2.0 (bbbbbbb)");

        // Identical SHA -> has_update = false
        let same = evaluate_release_update(
            &release,
            "0.2.0",
            "bbbbbbb222222233333334444444555555566666",
            2000,
            "orchestria-macos-arm64.tar.gz",
            false,
        );
        assert!(!same.has_update);

        // Older remote timestamp -> anti-downgrade guard keeps has_update = false
        let older_ts = evaluate_release_update(
            &release,
            "0.2.0",
            "aaaaaaa111111122222223333333444444455555",
            3000,
            "orchestria-macos-arm64.tar.gz",
            false,
        );
        assert!(!older_ts.has_update);
    }

    #[test]
    fn test_simplify_release_notes_translates_jargon_into_plain_english() {
        let raw = "\
<!-- orchestria-sha:005bd19a1b2c3d4e5f60718293a4b5c6d7e8f9a0 -->
## What's Changed
* Merge pull request #3 from abdullah-binmadhi/fix/model-download-parallel
* chore(ci): update cache key
* feat(audio): zero-dot SHM HAL v2 without orange dot (#4)
* fix(streamer): restore AirPods output when input_capture is toggled off with X key
* feat(dsp): improve biquad crossfader and DAC enhancer clarity
* Simple: Added a friendly popup showing what changed after every update
";
        let notes = simplify_release_notes(raw);
        assert!(!notes.is_empty());
        assert!(notes.len() <= 5);
        // Should contain no merge/chore lines and no raw jargon like `input_capture` or `SHM`
        for bullet in &notes {
            assert!(
                bullet.starts_with("[NEW]")
                    || bullet.starts_with("[FIXED]")
                    || bullet.starts_with("[IMPROVED]"),
                "Unexpected bullet format: {}",
                bullet
            );
            assert!(!bullet.contains("Merge pull request"));
            assert!(!bullet.contains("input_capture"));
        }
        assert!(notes
            .iter()
            .any(|b| b.contains("orange microphone indicator")));
        assert!(notes
            .iter()
            .any(|b| b.contains("friendly popup showing what changed")));
    }

    #[test]
    fn test_post_update_welcome_persistence_roundtrip() {
        let tmp = std::env::temp_dir().join(format!(
            "orchestria_welcome_test_{}.json",
            std::process::id()
        ));
        let _ = std::fs::remove_file(&tmp);

        let info = UpdateInfo {
            current_version: "0.2.0".to_string(),
            latest_version: "v0.2.0-rolling".to_string(),
            has_update: true,
            download_url: "https://example.com/orchestria.tar.gz".to_string(),
            release_name: "Rolling".to_string(),
            release_notes: String::new(),
            remote_sha: Some("abcdef1234567890".to_string()),
            simple_notes: vec!["[NEW] Cleaner system-wide sound.".to_string()],
            is_homebrew: false,
            driver_version: Some(2),
        };

        record_pending_post_update_welcome_at(&tmp, &info).expect("record welcome");
        let (label, notes) = take_post_update_welcome_at(&tmp).expect("first take returns welcome");
        assert_eq!(label, "0.2.0 (abcdef1)");
        assert_eq!(notes, vec!["[NEW] Cleaner system-wide sound.".to_string()]);

        // Second take returns None so the popup only displays once
        assert!(take_post_update_welcome_at(&tmp).is_none());
        let _ = std::fs::remove_file(&tmp);
    }

    #[test]
    fn test_native_magic_validation() {
        #[cfg(target_os = "macos")]
        {
            assert!(has_valid_native_magic(&[0xCF, 0xFA, 0xED, 0xFE]));
            assert!(has_valid_native_magic(&[0xCA, 0xFE, 0xBA, 0xBE]));
            assert!(!has_valid_native_magic(b"<!DO"));
        }
        #[cfg(target_os = "linux")]
        {
            assert!(has_valid_native_magic(&[0x7F, b'E', b'L', b'F']));
            assert!(!has_valid_native_magic(b"<!DO"));
        }
        #[cfg(target_os = "windows")]
        {
            assert!(has_valid_native_magic(b"MZ\x90\x00"));
            assert!(!has_valid_native_magic(b"<!DO"));
        }
    }
}
