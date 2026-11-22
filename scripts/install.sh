#!/usr/bin/env bash
# Orchestria installer for macOS and Linux.
#
# The binary comes from the first source that exists:
#   1. an orchestria binary shipped next to this script (release archive);
#   2. the source checkout this script sits in (built with cargo);
#   3. the latest GitHub release, checked against its SHA256SUMS before anything is installed.
# The in-app updater verifies release signatures. This script verifies SHA-256 only.
set -euo pipefail

REPO="abdullah-binmadhi/Orchestria"
RELEASE_BASE="https://github.com/${REPO}/releases/latest/download"

case "$(uname -s)" in
    Darwin) PLATFORM="macos" ;;
    Linux) PLATFORM="linux" ;;
    *)
        echo "Unsupported OS: $(uname -s). On Windows, run scripts/install.ps1." >&2
        exit 1
        ;;
esac

case "$(uname -m)" in
    arm64 | aarch64) ARCH="arm64" ;;
    x86_64) ARCH="x86_64" ;;
    *)
        echo "Unsupported CPU: $(uname -m)" >&2
        exit 1
        ;;
esac

if [ "$PLATFORM" = "linux" ] && [ "$ARCH" = "arm64" ]; then
    echo "No prebuilt Linux arm64 binary. Build from source with cargo instead." >&2
    exit 1
fi

# Only a script read from disk has a directory. `curl ... | bash` does not.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    else
        shasum -a 256 "$1" | cut -d ' ' -f 1
    fi
}

# Prints the path of an orchestria binary, building or downloading it when needed. Progress messages go to
# stderr, so only the path reaches stdout.
find_binary() {
    if [ -n "$SCRIPT_DIR" ] && [ -x "$SCRIPT_DIR/orchestria" ]; then
        echo "$SCRIPT_DIR/orchestria"
        return
    fi

    local repo_root="$SCRIPT_DIR/.."
    if [ -n "$SCRIPT_DIR" ] && grep -qs '^name = "orchestria"' "$repo_root/Cargo.toml" && command -v cargo >/dev/null 2>&1; then
        echo "Building orchestria from the source checkout..." >&2
        cargo build --release --manifest-path "$repo_root/Cargo.toml" >&2
        echo "$repo_root/target/release/orchestria"
        return
    fi

    local archive="orchestria-${PLATFORM}-${ARCH}.tar.gz"
    echo "Downloading ${archive} from the latest release..." >&2
    curl -fsSL -o "$WORK_DIR/$archive" "$RELEASE_BASE/$archive"
    curl -fsSL -o "$WORK_DIR/SHA256SUMS" "$RELEASE_BASE/SHA256SUMS"

    local expected actual
    expected="$(awk -v name="$archive" '{ file = $2; sub(/^\*/, "", file) } file == name { print $1 }' "$WORK_DIR/SHA256SUMS")"
    actual="$(sha256_of "$WORK_DIR/$archive")"
    if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
        echo "Checksum mismatch for $archive. Nothing was installed." >&2
        exit 1
    fi

    tar -xzf "$WORK_DIR/$archive" -C "$WORK_DIR"
    echo "$WORK_DIR/orchestria"
}

BIN_SRC="$(find_binary)"
BIN_DIR="$(dirname "$BIN_SRC")"

INSTALL_DIR="/usr/local/bin"
if [ ! -w "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

install -m 0755 "$BIN_SRC" "$INSTALL_DIR/orchestria"

# The HAL driver is found next to the installed binary, so the bundle goes there too.
if [ -d "$BIN_DIR/OrchestriaAudio.driver" ]; then
    rm -rf "$INSTALL_DIR/OrchestriaAudio.driver"
    cp -R "$BIN_DIR/OrchestriaAudio.driver" "$INSTALL_DIR/"
fi

if [ "$PLATFORM" = "macos" ]; then
    xattr -dr com.apple.quarantine "$INSTALL_DIR/orchestria" 2>/dev/null || true
    if [ -d "$INSTALL_DIR/OrchestriaAudio.driver" ]; then
        xattr -dr com.apple.quarantine "$INSTALL_DIR/OrchestriaAudio.driver" 2>/dev/null || true
    fi
fi

echo "Installed orchestria to $INSTALL_DIR/orchestria"
case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *) echo "Add $INSTALL_DIR to your PATH to run orchestria from any terminal." ;;
esac

if [ "$PLATFORM" = "macos" ]; then
    if pgrep -qx WindowServer >/dev/null 2>&1; then
        echo "Launching macOS Touch ID / Administrator dialog to enable the Zero-Dot Sound Engine..."
        if ! "$INSTALL_DIR/orchestria" driver install-gui; then
            echo "Driver setup skipped for now. Launch 'orchestria' to finish 1-click guided setup anytime." >&2
        fi
    else
        echo "Run 'orchestria' to finish the guided Sound Engine setup."
    fi
else
    echo "Linux needs no driver: PipeWire/PulseAudio user-space virtual sink activates automatically on launch."
fi
