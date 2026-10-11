# OmniRip Windows PowerShell Automated Installer
# Installs OmniRip CLI with native WASAPI loopback support (zero driver required).

$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " OmniRip: Audiophile Studio System EQ & Mastering Suite " -ForegroundColor Cyan
Write-Host " Windows PowerShell Installer                          " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# Ensure 64-bit Windows
if ([IntPtr]::Size -ne 8) {
    Write-Error "Error: OmniRip requires a 64-bit Windows operating system."
    exit 1
}

$InstallDir = "$env:LOCALAPPDATA\Programs\OmniRip"
$BinaryPath = "$InstallDir\omnirip.exe"

# Create target directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
if ((Test-Path "$RepoRoot\Cargo.toml") -and (Get-Command "cargo" -ErrorAction SilentlyContinue)) {
    Write-Host "[1/3] Building from local repository using Cargo..." -ForegroundColor Yellow
    cargo build --release --manifest-path "$RepoRoot\Cargo.toml"
    Copy-Item -Path "$RepoRoot\target\release\omnirip.exe" -Destination $BinaryPath -Force
} else {
    Write-Host "[1/3] Downloading latest release from GitHub..." -ForegroundColor Yellow
    $ReleaseUrl = "https://github.com/abdullah-binmadhi/OmniRip/releases/latest/download/omnirip-windows-x64.zip"
    $TempZip = "$env:TEMP\omnirip-windows-x64.zip"
    
    Invoke-WebRequest -Uri $ReleaseUrl -OutFile $TempZip
    Expand-Archive -Path $TempZip -DestinationPath $InstallDir -Force
    Remove-Item -Path $TempZip -Force
}

Write-Host "[2/3] Binary placed at $BinaryPath" -ForegroundColor Green

# Update User PATH environment variable if not already present
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "[3/3] Adding $InstallDir to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", [EnvironmentVariableTarget]::User)
    $env:Path = "$env:Path;$InstallDir"
} else {
    Write-Host "[3/3] User PATH already configured." -ForegroundColor Green
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " OmniRip successfully installed!                       " -ForegroundColor Green
Write-Host " Open a new terminal and run: omnirip                   " -ForegroundColor Cyan
Write-Host " Note: Windows captures audio natively via WASAPI.      " -ForegroundColor DarkGray
Write-Host " No virtual audio driver or restart is required.       " -ForegroundColor DarkGray
Write-Host "=======================================================" -ForegroundColor Cyan
