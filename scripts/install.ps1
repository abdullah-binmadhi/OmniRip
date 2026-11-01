# OmniRip Windows installer.
#
# Uses the source checkout this script sits in when there is one (built with Cargo). Otherwise it
# downloads the latest release and refuses to install unless its SHA-256 matches SHA256SUMS.

$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " OmniRip: Audiophile Studio System EQ & Mastering Suite " -ForegroundColor Cyan
Write-Host " Windows PowerShell Installer                           " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

if ([IntPtr]::Size -ne 8) {
    Write-Error "OmniRip requires a 64-bit Windows operating system."
    exit 1
}

$InstallDir = "$env:LOCALAPPDATA\Programs\OmniRip"
$BinaryPath = "$InstallDir\omnirip.exe"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# `irm ... | iex` runs without a script file, so there may be no script directory.
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "" }
$ReleaseBase = "https://github.com/abdullah-binmadhi/OmniRip/releases/latest/download"

if ($RepoRoot -and (Test-Path "$RepoRoot\Cargo.toml") -and (Get-Command "cargo" -ErrorAction SilentlyContinue)) {
    Write-Host "[1/3] Building from the local repository with Cargo..." -ForegroundColor Yellow
    cargo build --release --manifest-path "$RepoRoot\Cargo.toml"
    Copy-Item -Path "$RepoRoot\target\release\omnirip.exe" -Destination $BinaryPath -Force
} else {
    Write-Host "[1/3] Downloading the latest release..." -ForegroundColor Yellow
    $Archive = "omnirip-windows-x64.zip"
    $TempZip = Join-Path $env:TEMP $Archive
    Invoke-WebRequest -UseBasicParsing -Uri "$ReleaseBase/$Archive" -OutFile $TempZip
    $Sums = (Invoke-WebRequest -UseBasicParsing -Uri "$ReleaseBase/SHA256SUMS").Content
    $Line = ($Sums -split "`n" | Where-Object { $_ -match [regex]::Escape($Archive) } | Select-Object -First 1)
    if (-not $Line) {
        Remove-Item -Path $TempZip -Force
        throw "$Archive is missing from SHA256SUMS. Nothing was installed."
    }
    $Expected = ($Line.Trim() -split '\s+')[0].ToLower()
    $Actual = (Get-FileHash -Algorithm SHA256 -Path $TempZip).Hash.ToLower()
    if ($Expected -ne $Actual) {
        Remove-Item -Path $TempZip -Force
        throw "Checksum mismatch for $Archive. Nothing was installed."
    }
    Expand-Archive -Path $TempZip -DestinationPath $InstallDir -Force
    Remove-Item -Path $TempZip -Force
}

Write-Host "[2/3] Binary placed at $BinaryPath" -ForegroundColor Green

$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "[3/3] Adding $InstallDir to the user PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", [EnvironmentVariableTarget]::User)
    $env:Path = "$env:Path;$InstallDir"
} else {
    Write-Host "[3/3] User PATH already configured." -ForegroundColor Green
}

Write-Host ""
Write-Host "OmniRip is installed. Open a new terminal and run: omnirip" -ForegroundColor Green
Write-Host "Note: Windows audio support is still being finished. See the README for its status." -ForegroundColor DarkGray
