#!/usr/bin/env bash
# OmniRip macOS Universal Installer
# Installs OmniRip CLI and CoreAudio HAL driver with zero Apple Developer certificate requirements.

set -euo pipefail

echo "======================================================="
echo " OmniRip: Audiophile Studio System EQ & Mastering Suite "
echo " macOS Universal Installer                              "
echo "======================================================="

OS="$(uname -s)"
if [ "$OS" != "Darwin" ]; then
    echo "Error: This installer is intended for macOS only. On Windows, use scripts/install.ps1."
    exit 1
fi

ARCH="$(uname -m)"
case "$ARCH" in
    arm64)
        TARGET_ARCH="arm64"
        ;;
    x86_64)
        TARGET_ARCH="x86_64"
        ;;
    *)
        echo "Error: Unsupported CPU architecture: $ARCH"
        exit 1
        ;;
esac

echo "[1/4] Detected macOS ($TARGET_ARCH)..."

# Determine target binary installation directory
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
else
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
    # Ensure INSTALL_DIR is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo "Adding $INSTALL_DIR to PATH in shell profile..."
        SHELL_RC="$HOME/.zshrc"
        [ -f "$HOME/.bash_profile" ] && SHELL_RC="$HOME/.bash_profile"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi
fi

TARGET_BIN="$INSTALL_DIR/omnirip"

# Check if installing from local repo or remote release
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || echo "")"
if [ -n "$REPO_DIR" ] && [ -f "$REPO_DIR/Cargo.toml" ]; then
    echo "[2/4] Installing from local repository..."
    if command -v cargo >/dev/null 2>&1; then
        cargo build --release --manifest-path "$REPO_DIR/Cargo.toml"
        cp -f "$REPO_DIR/target/release/omnirip" "$TARGET_BIN"
    elif [ -f "$REPO_DIR/target/release/omnirip" ]; then
        cp -f "$REPO_DIR/target/release/omnirip" "$TARGET_BIN"
    else
        echo "Error: Cargo not found and no pre-built binary in target/release/."
        exit 1
    fi
else
    echo "[2/4] Downloading latest release from GitHub..."
    RELEASE_URL="https://github.com/abdullah-binmadhi/OmniRip/releases/latest/download/omnirip-macos-${TARGET_ARCH}.tar.gz"
    TEMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TEMP_DIR"' EXIT
    curl -fsSL "$RELEASE_URL" -o "$TEMP_DIR/omnirip.tar.gz"
    tar -xzf "$TEMP_DIR/omnirip.tar.gz" -C "$TEMP_DIR"
    cp -f "$TEMP_DIR/omnirip" "$TARGET_BIN"
fi

chmod +x "$TARGET_BIN"

# Strip Gatekeeper quarantine attribute if present
xattr -cr "$TARGET_BIN" 2>/dev/null || true

echo "[3/4] OmniRip binary installed to $TARGET_BIN"

# Install CoreAudio HAL Driver
echo "[4/4] Installing OmniRip Virtual Audio HAL Driver (requires administrator password)..."
if command -v "$TARGET_BIN" >/dev/null 2>&1 || [ -x "$TARGET_BIN" ]; then
    "$TARGET_BIN" driver install || {
        echo "Warning: Driver install skipped or encountered an error. You can run 'omnirip driver install' later."
    }
fi

echo ""
echo "======================================================="
echo " OmniRip successfully installed!                       "
echo " Run 'omnirip' in your terminal to start.              "
echo "======================================================="
