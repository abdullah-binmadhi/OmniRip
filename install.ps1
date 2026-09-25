# OmniRip Universal One-Command Installer (Windows PowerShell)
# Usage: irm https://raw.githubusercontent.com/abdullah-binmadhi/OmniRip/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "     OMNIRIP - Turnkey Windows Setup                  " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Magenta

# 1. Check / Install uv
Write-Host "[1/3] Checking standalone runner (uv)..." -ForegroundColor Green
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Installing uv..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$HOME\.local\bin;$HOME\.cargo\bin;$env:Path"
}
Write-Host "  ✓ uv ready." -ForegroundColor Green

# 2. Check FFmpeg
Write-Host "[2/3] Checking FFmpeg audio engine..." -ForegroundColor Green
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "  ! ffmpeg not detected in PATH." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  -> Installing ffmpeg via winget..." -ForegroundColor Cyan
        winget install --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "  ! Please install FFmpeg and add it to your PATH: https://ffmpeg.org" -ForegroundColor Red
    }
} else {
    Write-Host "  ✓ ffmpeg detected." -ForegroundColor Green
}

# 3. Install OmniRip
Write-Host "[3/3] Installing OmniRip..." -ForegroundColor Green
$repoUrl = "git+https://github.com/abdullah-binmadhi/OmniRip.git"
uv tool install --force --from $repoUrl omnirip

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "  ✓ OmniRip successfully installed!" -ForegroundColor Green
Write-Host "  Type 'omnirip' in PowerShell anytime to launch." -ForegroundColor Cyan
Write-Host "======================================================`n" -ForegroundColor Green

# Launch
omnirip
