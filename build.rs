use std::path::Path;
use std::process::Command;

fn main() {
    // Watch git HEAD and active branch ref so local commits re-trigger build.rs
    let git_dir = resolve_git_dir();
    let head_path = git_dir.join("HEAD");
    if head_path.exists() {
        println!("cargo:rerun-if-changed={}", head_path.display());
        if let Ok(contents) = std::fs::read_to_string(&head_path) {
            if let Some(rel_ref) = contents.strip_prefix("ref:") {
                let ref_path = git_dir.join(rel_ref.trim());
                if ref_path.exists() {
                    println!("cargo:rerun-if-changed={}", ref_path.display());
                }
            }
        }
        let packed = git_dir.join("packed-refs");
        if packed.exists() {
            println!("cargo:rerun-if-changed={}", packed.display());
        }
    }
    println!("cargo:rerun-if-env-changed=GITHUB_SHA");

    // 1. Resolve 40-char Git Commit SHA (prefer GITHUB_SHA in CI, fallback to `git rev-parse HEAD`)
    let sha = std::env::var("GITHUB_SHA")
        .ok()
        .filter(|s| s.len() >= 7)
        .or_else(|| {
            Command::new("git")
                .args(["rev-parse", "HEAD"])
                .output()
                .ok()
                .filter(|o| o.status.success())
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                .filter(|s| s.len() >= 7)
        })
        .unwrap_or_else(|| "unknown".to_string());

    // 2. Resolve Unix Commit Timestamp (`git show -s --format=%ct HEAD`)
    let commit_ts = Command::new("git")
        .args(["show", "-s", "--format=%ct", "HEAD"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .filter(|s| s.chars().all(|c| c.is_ascii_digit()) && !s.is_empty())
        .unwrap_or_else(|| "0".to_string());

    println!("cargo:rustc-env=OMNIRIP_GIT_SHA={}", sha);
    println!("cargo:rustc-env=OMNIRIP_COMMIT_TS={}", commit_ts);
}

fn resolve_git_dir() -> std::path::PathBuf {
    let dot_git = Path::new(".git");
    if dot_git.is_file() {
        if let Ok(content) = std::fs::read_to_string(dot_git) {
            if let Some(gitdir) = content.strip_prefix("gitdir:") {
                return std::path::PathBuf::from(gitdir.trim());
            }
        }
    }
    dot_git.to_path_buf()
}
