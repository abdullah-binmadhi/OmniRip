#!/bin/bash
set -e

echo "=== OmniRip Audio: Ground-Up HAL Driver Uninstaller ==="

TARGET_DRIVER="/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver"

if [ -d "$TARGET_DRIVER" ]; then
    echo "Removing $TARGET_DRIVER..."
    sudo rm -rf "$TARGET_DRIVER"
    echo "Reloading CoreAudio daemon..."
    sudo killall -9 coreaudiod
    echo "OmniRip Audio Driver uninstalled."
else
    echo "OmniRip Audio Driver is not installed."
fi
