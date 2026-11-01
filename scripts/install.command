#!/bin/bash
# Double-clickable macOS Finder installer for OmniRip
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "======================================================="
echo " OmniRip: One-Click macOS Installer                    "
echo "======================================================="

chmod +x "$DIR/install.sh"
"$DIR/install.sh"

echo ""
echo "Press any key to exit this installer window..."
read -n 1 -s
