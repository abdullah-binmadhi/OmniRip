#!/usr/bin/env bash
# OmniRip Universal One-Command Installer (macOS & Linux)
# Usage: curl -fsSL https://raw.githubusercontent.com/abdullah-binmadhi/OmniRip/main/install.sh | bash

set -e

CYAN='\033[0;36m'
PINK='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${PINK}"
cat << "EOF"
  ██████╗ ███╗   ███╗███╗   ██╗██╗██████╗ ██╗██████╗ 
 ██╔═══██╗████╗ ████║████╗  ██║██║██╔══██╗██║██╔══██╗
 ██║   ██║██╔████╔██║██╔██╗ ██║██║██████╔╝██║██████╔╝
 ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██╔══██╗██║██╔═══╝ 
 ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║██║  ██║██║██║     
  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝╚═╝     
EOF
echo -e "${CYAN}>> P2P-First Music Acquisition & Curation TUI <<${NC}\n"

# 1. Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "${GREEN}[1/4]${NC} Detecting platform: ${OS} (${ARCH})..."

# 2. Check & Install FFmpeg
echo -e "${GREEN}[2/4]${NC} Checking audio engine dependencies (ffmpeg)..."
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}  -> ffmpeg not found. Attempting installation...${NC}"
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &> /dev/null; then
            echo "  -> Installing ffmpeg via Homebrew..."
            brew install ffmpeg
        else
            echo -e "${RED}  ✗ Homebrew not found. Please install Homebrew or ffmpeg: https://ffmpeg.org/download.html${NC}"
        fi
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            echo "  -> Installing ffmpeg via apt..."
            sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
        elif command -v dnf &> /dev/null; then
            echo "  -> Installing ffmpeg via dnf..."
            sudo dnf install -y ffmpeg
        elif command -v pacman &> /dev/null; then
            echo "  -> Installing ffmpeg via pacman..."
            sudo pacman -S --noconfirm ffmpeg
        else
            echo -e "${YELLOW}  ! Please ensure ffmpeg is installed via your package manager.${NC}"
        fi
    fi
else
    echo -e "  ${GREEN}✓${NC} ffmpeg found: $(ffmpeg -version | head -n 1 | awk '{print $1,$2,$3}')"
fi

# 3. Check & Install standalone 'uv' runner
echo -e "${GREEN}[3/4]${NC} Checking isolated Python environment runner (uv)..."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "  -> Installing standalone uv runner..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo -e "  ${GREEN}✓${NC} uv ready: $(uv --version)"

# 4. Install / Upgrade OmniRip
echo -e "${GREEN}[4/4]${NC} Installing latest OmniRip release..."
REPO_URL="git+https://github.com/abdullah-binmadhi/OmniRip.git"

uv tool install --force --from "${REPO_URL}" omnirip

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  ✓ OmniRip successfully installed!${NC}"
echo -e "  Run ${CYAN}omnirip${NC} anytime from your terminal."
echo -e "${GREEN}======================================================${NC}\n"

# Launch OmniRip if in interactive terminal
if [ -t 0 ]; then
    echo -e "${CYAN}Launching OmniRip...${NC}\n"
    exec "$HOME/.local/bin/omnirip" "$@"
fi
