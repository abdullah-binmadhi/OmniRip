//! Locating the HAL driver bundle, and quoting values for `sh` and AppleScript.
#![cfg_attr(not(target_os = "macos"), allow(dead_code))]

use std::path::{Path, PathBuf};

/// Where the driver bundle comes from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DriverSource {
    /// A finished `OmniRipAudio.driver` bundle.
    Bundle(PathBuf),
    /// A source checkout (`drivers/omnirip_hal`) that must be built with `make` first.
    SourceTree(PathBuf),
}

/// Finds the driver for a binary running from `exe_dir`, in this order:
/// 1. a bundle shipped next to the binary (release archives);
/// 2. a source checkout with `drivers/omnirip_hal/Makefile`, searched upward from the binary and then
///    from the working directory.
pub fn locate_driver_source(exe_dir: &Path, cwd: &Path) -> Option<DriverSource> {
    let shipped = exe_dir.join("OmniRipAudio.driver");
    if shipped.is_dir() {
        return Some(DriverSource::Bundle(shipped));
    }
    for start in [exe_dir, cwd] {
        let mut dir = Some(start);
        for _ in 0..6 {
            let Some(current) = dir else { break };
            let source = current.join("drivers").join("omnirip_hal");
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
            std::env::temp_dir().join(format!("omnirip-bundle-{}-{}", name, std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("create scratch dir");
        dir
    }

    #[test]
    fn a_shipped_bundle_beside_the_binary_wins() {
        let root = scratch_dir("shipped");
        std::fs::create_dir_all(root.join("OmniRipAudio.driver")).expect("create bundle");
        assert_eq!(
            locate_driver_source(&root, &root),
            Some(DriverSource::Bundle(root.join("OmniRipAudio.driver")))
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn a_source_checkout_is_found_by_walking_up_from_the_binary() {
        let root = scratch_dir("checkout");
        let source = root.join("drivers").join("omnirip_hal");
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
    fn nothing_is_found_when_neither_exists() {
        let root = scratch_dir("missing");
        assert_eq!(locate_driver_source(&root, &root), None);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn shell_quoting_survives_single_quotes() {
        assert_eq!(
            shell_single_quote("/Apps/O'Brien/omnirip"),
            "'/Apps/O'\\''Brien/omnirip'"
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
