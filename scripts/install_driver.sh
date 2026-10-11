#!/bin/bash
set -e

echo "=== OmniRip Audio: Ground-Up HAL Driver Installer ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_SRC="$SCRIPT_DIR/drivers/omnirip_hal"
DRIVER_BUNDLE="$DRIVER_SRC/OmniRipAudio.driver"
TARGET_DIR="/Library/Audio/Plug-Ins/HAL"

echo "[1/3] Building & Code-Signing OmniRipAudio.driver on Apple Silicon..."
make -C "$DRIVER_SRC"

echo "[2/3] Installing OmniRipAudio.driver to $TARGET_DIR (requires administrator password)..."
sudo cp -R "$DRIVER_BUNDLE" "$TARGET_DIR/"

echo "[3/3] Reloading macOS CoreAudio daemon..."
sudo launchctl kickstart -k system/com.apple.audio.coreaudiod || sudo killall coreaudiod

echo ""
echo "OmniRip Audio Driver installed successfully!"
echo "Verifying driver registration in CoreAudio..."
sleep 2

omnirip driver status
