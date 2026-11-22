//! Locating the HAL driver bundle, inspecting bundle metadata, and quoting values for `sh` and AppleScript.
#![cfg_attr(not(target_os = "macos"), allow(dead_code))]

use std::path::{Path, PathBuf};

/// Expected CFBundleVersion for the Zero-Dot Output-Only HAL v2 driver.
pub const EXPECTED_DRIVER_BUNDLE_VERSION: u32 = 2;

/// Where the driver bundle comes from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DriverSource {
    /// A finished `OrchestriaAudio.driver` bundle.
    Bundle(PathBuf),
    /// A source checkout (`drivers/orchestria_hal`) that must be built with `make` first.
    SourceTree(PathBuf),
}

/// Directory where Orchestria caches staged driver bundles when the binary directory is read-only.
pub fn user_driver_cache_dir() -> PathBuf {
    if let Ok(appdata) = std::env::var("APPDATA") {
        return PathBuf::from(appdata).join("Orchestria");
    }
    if let Ok(home) = std::env::var("HOME") {
        return PathBuf::from(home).join(".local").join("share").join("orchestria");
    }
    std::env::temp_dir().join("orchestria")
}

/// Parses `CFBundleVersion` from a `.driver/Contents/Info.plist` file.
pub fn read_bundle_version(bundle_dir: &Path) -> Option<u32> {
    let plist_path = bundle_dir.join("Contents").join("Info.plist");
    let content = std::fs::read_to_string(plist_path).ok()?;
    let key_idx = content.find("<key>CFBundleVersion</key>")?;
    let after_key = &content[key_idx..];
    let str_start = after_key.find("<string>")? + "<string>".len();
    let rest = &after_key[str_start..];
    let str_end = rest.find("</string>")?;
    rest[..str_end].trim().parse::<u32>().ok()
}

/// Finds the driver for a binary running from `exe_dir`, in this order:
/// 1. a bundle shipped next to the binary (release archives);
/// 2. canonicalized symlink / Homebrew `pkgshare` / `libexec` locations (`../share/orchestria/`, `../libexec/`);
/// 3. user driver cache (`~/.local/share/orchestria/OrchestriaAudio.driver`);
/// 4. a source checkout with `drivers/orchestria_hal/Makefile`, searched upward from the binary, canonical binary,
///    and working directory.
pub fn locate_driver_source(exe_dir: &Path, cwd: &Path) -> Option<DriverSource> {
    let mut bundle_candidates = vec![exe_dir.join("OrchestriaAudio.driver")];

    if let Ok(exe_path) = std::env::current_exe() {
        if let Ok(canon_exe) = std::fs::canonicalize(&exe_path) {
            if let Some(canon_dir) = canon_exe.parent() {
                bundle_candidates.push(canon_dir.join("OrchestriaAudio.driver"));
                if let Some(prefix) = canon_dir.parent() {
                    bundle_candidates.push(prefix.join("share").join("orchestria").join("OrchestriaAudio.driver"));
                    bundle_candidates.push(prefix.join("libexec").join("OrchestriaAudio.driver"));
                    bundle_candidates.push(prefix.join("OrchestriaAudio.driver"));
                }
            }
        }
    }

    if let Ok(canon_dir) = std::fs::canonicalize(exe_dir) {
        bundle_candidates.push(canon_dir.join("OrchestriaAudio.driver"));
        if let Some(prefix) = canon_dir.parent() {
            bundle_candidates.push(prefix.join("share").join("orchestria").join("OrchestriaAudio.driver"));
            bundle_candidates.push(prefix.join("libexec").join("OrchestriaAudio.driver"));
            bundle_candidates.push(prefix.join("OrchestriaAudio.driver"));
        }
    } else if let Some(prefix) = exe_dir.parent() {
        bundle_candidates.push(prefix.join("share").join("orchestria").join("OrchestriaAudio.driver"));
        bundle_candidates.push(prefix.join("libexec").join("OrchestriaAudio.driver"));
    }

    bundle_candidates.push(user_driver_cache_dir().join("OrchestriaAudio.driver"));

    for candidate in bundle_candidates {
        if candidate.is_dir() {
            return Some(DriverSource::Bundle(candidate));
        }
    }

    let canon_exe_dir = std::fs::canonicalize(exe_dir).ok();
    let mut starts: Vec<&Path> = vec![exe_dir];
    if let Some(ref c) = canon_exe_dir {
        starts.push(c.as_path());
    }
    starts.push(cwd);

    for start in starts {
        let mut dir = Some(start);
        for _ in 0..6 {
            let Some(current) = dir else { break };
            let source = current.join("drivers").join("orchestria_hal");
            if source.join("Makefile").is_file() {
                return Some(DriverSource::SourceTree(source));
            }
            dir = current.parent();
        }
    }
    None
}

/// Wraps `value` in single quotes for `sh`, escaping any single quote inside it.
pub fn shell_single_quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}

/// Escapes `value` for an AppleScript double-quoted string literal.
pub fn applescript_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch_dir(name: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("orchestria-bundle-{}-{}", name, std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("create scratch dir");
        dir
    }

    #[test]
    fn a_shipped_bundle_beside_the_binary_wins() {
        let root = scratch_dir("shipped");
        std::fs::create_dir_all(root.join("OrchestriaAudio.driver")).expect("create bundle");
        assert_eq!(
            locate_driver_source(&root, &root),
            Some(DriverSource::Bundle(root.join("OrchestriaAudio.driver")))
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn homebrew_pkgshare_bundle_is_found_from_bin_dir() {
        let root = scratch_dir("brew");
        let bin_dir = root.join("bin");
        let pkgshare = root.join("share").join("orchestria").join("OrchestriaAudio.driver");
        std::fs::create_dir_all(&bin_dir).expect("create bin dir");
        std::fs::create_dir_all(&pkgshare).expect("create pkgshare bundle");

        let found = locate_driver_source(&bin_dir, &bin_dir);
        let expected_canon = std::fs::canonicalize(&pkgshare).unwrap_or(pkgshare.clone());
        assert!(
            matches!(found, Some(DriverSource::Bundle(ref p)) if *p == expected_canon || *p == pkgshare),
            "Expected Homebrew pkgshare bundle, got {:?}",
            found
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn a_source_checkout_is_found_by_walking_up_from_the_binary() {
        let root = scratch_dir("checkout");
        let source = root.join("drivers").join("orchestria_hal");
        std::fs::create_dir_all(&source).expect("create source tree");
        std::fs::write(source.join("Makefile"), "all:\n").expect("write Makefile");
        let exe_dir = root.join("target").join("release");
        std::fs::create_dir_all(&exe_dir).expect("create target dir");
        assert_eq!(
            locate_driver_source(&exe_dir, &root),
            Some(DriverSource::SourceTree(source))
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn read_bundle_version_parses_plist_version() {
        let root = scratch_dir("plist");
        let contents = root.join("OrchestriaAudio.driver").join("Contents");
        std::fs::create_dir_all(&contents).expect("create Contents dir");
        std::fs::write(
            contents.join("Info.plist"),
            "<plist><dict><key>CFBundleVersion</key><string>2</string></dict></plist>",
        )
        .expect("write plist");
        assert_eq!(read_bundle_version(&root.join("OrchestriaAudio.driver")), Some(2));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn shell_quoting_survives_single_quotes() {
        assert_eq!(
            shell_single_quote("/Apps/O'Brien/orchestria"),
            "'/Apps/O'\\''Brien/orchestria'"
        );
    }

    #[test]
    fn applescript_escaping_covers_quotes_and_backslashes() {
        assert_eq!(
            applescript_escape(r#"say "hi" \ there"#),
            r#"say \"hi\" \\ there"#
        );
    }
}
