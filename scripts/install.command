#!/bin/bash
# Double-clickable macOS Finder installer for Orchestria
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "======================================================="
echo " Orchestria: One-Click macOS Installer                    "
echo "======================================================="

xattr -dr com.apple.quarantine "$DIR" >/dev/null 2>&1 || true
chmod +x "$DIR/install.sh"
"$DIR/install.sh"

echo ""
echo "Press any key to exit this installer window..."
read -n 1 -s
