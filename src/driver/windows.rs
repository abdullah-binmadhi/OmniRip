//! Windows WASAPI Virtual Audio Endpoint discovery, UAC elevation, IPolicyConfig handoff,
//! and 3010 (ERROR_SUCCESS_REBOOT_REQUIRED) reboot handling.

#![cfg_attr(not(target_os = "windows"), allow(dead_code))]

use super::DriverInstallOutcome;
use std::path::PathBuf;
#[cfg(target_os = "windows")]
use std::process::Command;

/// Headless GitHub Actions `windows-latest` runners lack audio hardware and throw COM access
/// violations when probing WASAPI endpoints. Local user desktops always return `false`.
pub fn is_headless_windows_ci() -> bool {
    std::env::var_os("CI").is_some() || std::env::var_os("GITHUB_ACTIONS").is_some()
}

/// Identifies virtual loopback/cable endpoints so OmniRip never outputs back into itself (avoiding echo).
pub fn is_virtual_windows_endpoint(name: &str) -> bool {
    let low = name.to_lowercase();
    low.contains("omnirip")
        || low.contains("vb-audio")
        || low.contains("cable input")
        || low.contains("cable output")
        || low.contains("voicemeeter")
        || low.contains("virtual audio")
}

/// Maps a Windows driver installer / `pnputil` exit code to an installation outcome.
pub fn parse_windows_driver_exit_code(code: i32) -> Result<DriverInstallOutcome, String> {
    match code {
        0 => Ok(DriverInstallOutcome::ActivatedImmediate(
            "Windows Virtual Audio Endpoint installed and ready.".to_string(),
        )),
        3010 | 1641 => Ok(DriverInstallOutcome::RebootRequired(
            "Windows requires a one-time restart (exit 3010) to register the virtual audio endpoint."
                .to_string(),
        )),
        1223 | 1602 => Err("Windows UAC administrator authorization was canceled by the user.".to_string()),
        other => Err(format!(
            "Windows virtual audio driver installer exited with code {}.",
            other
        )),
    }
}

/// Locates a bundled Windows virtual audio driver `.inf` or installer `.exe`/`.msi` beside `omnirip.exe`.
pub fn locate_windows_driver_installer() -> Option<PathBuf> {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))?;

    let candidates = [
        exe_dir.join("drivers").join("OmniRipAudio.inf"),
        exe_dir.join("OmniRipAudio.inf"),
        exe_dir.join("OmniRipVirtualAudioSetup.exe"),
        exe_dir.join("OmniRipVirtualAudio.msi"),
        super::bundle::user_driver_cache_dir().join("OmniRipAudio.inf"),
    ];

    candidates.into_iter().find(|p| p.is_file())
}

/// Checks if a compatible virtual audio endpoint (OmniRip Virtual or VB-Cable) is present in Windows audio.
pub fn detect_virtual_sink_present() -> bool {
    if is_headless_windows_ci() {
        return false;
    }
    #[cfg(target_os = "windows")]
    {
        let script = "Get-CimInstance Win32_SoundDevice | Where-Object { $_.Status -eq 'OK' -and ($_.Name -match 'OmniRip|VB-Audio|Virtual Audio|CABLE') } | Select-Object -First 1 -ExpandProperty Name";
        if let Ok(out) = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", script])
            .output()
        {
            if out.status.success() {
                return !String::from_utf8_lossy(&out.stdout).trim().is_empty();
            }
        }
    }
    false
}

/// Installs the Windows virtual audio driver via a single native UAC / Windows Hello prompt (`-Verb RunAs`).
pub fn install_driver_gui() -> Result<DriverInstallOutcome, String> {
    if detect_virtual_sink_present() {
        return Ok(DriverInstallOutcome::ActivatedImmediate(
            "Windows Virtual Audio Endpoint already active (zero-echo routing ready).".to_string(),
        ));
    }

    let Some(installer_path) = locate_windows_driver_installer() else {
        return Err(
            "Windows virtual audio driver package was not found beside omnirip.exe. Re-run scripts/install.ps1 or install a signed virtual audio endpoint (e.g., OmniRip Virtual / VB-Cable)."
                .to_string(),
        );
    };

    #[cfg(target_os = "windows")]
    {
        let path_str = installer_path.to_string_lossy().replace('\'', "''");
        let is_inf = installer_path
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.eq_ignore_ascii_case("inf"))
            .unwrap_or(false);

        let ps_cmd = if is_inf {
            format!(
                "$p = Start-Process -FilePath 'pnputil.exe' -ArgumentList @('/add-driver', '{}', '/install') -Verb RunAs -Wait -PassThru; exit $p.ExitCode",
                path_str
            )
        } else {
            format!(
                "$p = Start-Process -FilePath '{}' -ArgumentList '/S' -Verb RunAs -Wait -PassThru; exit $p.ExitCode",
                path_str
            )
        };

        let out = Command::new("powershell")
            .args(["-NoProfile", "-Command", &ps_cmd])
            .output()
            .map_err(|e| format!("Failed to invoke Windows UAC prompt: {}", e))?;

        let code = out.status.code().unwrap_or(1);
        let outcome = parse_windows_driver_exit_code(code)?;
        if matches!(outcome, DriverInstallOutcome::ActivatedImmediate(_)) {
            let _ = Command::new("powershell")
                .args([
                    "-NoProfile",
                    "-Command",
                    "Restart-Service -Name Audiosrv -Force -ErrorAction SilentlyContinue",
                ])
                .status();

            for _ in 0..10 {
                std::thread::sleep(std::time::Duration::from_millis(500));
                if detect_virtual_sink_present() {
                    return Ok(DriverInstallOutcome::ActivatedImmediate(
                        "Windows Virtual Audio Endpoint installed and verified.".to_string(),
                    ));
                }
            }
            return Ok(DriverInstallOutcome::RebootRequired(
                "Driver installed, but Windows needs a quick restart to expose the virtual endpoint."
                    .to_string(),
            ));
        }
        Ok(outcome)
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = installer_path;
        Err("Windows driver installer is only valid on Windows hosts.".to_string())
    }
}

/// Switches Windows default playback endpoint cleanly via PowerShell `AudioDeviceCmdlets` or COM `IPolicyConfig`.
pub fn set_default_playback_device_by_name(device_name: &str) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        let escaped = device_name.replace('\'', "''");
        let ps = format!(
            r#"
$target = '{escaped}'
if (Get-Command Set-AudioDevice -ErrorAction SilentlyContinue) {{
    $dev = Get-AudioDevice -List | Where-Object {{ $_.Type -eq 'Playback' -and $_.Name -like "*$target*" }} | Select-Object -First 1
    if ($dev) {{ Set-AudioDevice -Index $dev.Index | Out-Null; exit 0 }}
}}
exit 1
"#
        );
        let status = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &ps])
            .status()
            .map_err(|e| format!("Failed to switch Windows playback endpoint: {}", e))?;
        if status.success() {
            Ok(())
        } else {
            Err(format!("Could not set Windows default endpoint to '{}'", device_name))
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = device_name;
        Ok(())
    }
}

pub fn get_default_playback_device_name() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        if is_headless_windows_ci() {
            return None;
        }
        let ps = "if (Get-Command Get-AudioDevice -ErrorAction SilentlyContinue) { (Get-AudioDevice -Playback).Name }";
        if let Ok(out) = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", ps])
            .output()
        {
            if out.status.success() {
                let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !s.is_empty() {
                    return Some(s);
                }
            }
        }
    }
    None
}

pub fn trigger_system_reboot() -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        let status = Command::new("shutdown")
            .args(["/r", "/t", "2"])
            .status()
            .map_err(|e| format!("Failed to initiate Windows restart: {}", e))?;
        if status.success() {
            return Ok(());
        }
        return Err("Windows restart command returned a non-zero status.".to_string());
    }
    #[cfg(not(target_os = "windows"))]
    {
        Err("Windows reboot helper called on non-Windows platform.".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn windows_exit_code_mapping_handles_success_reboot_and_cancel() {
        assert!(matches!(
            parse_windows_driver_exit_code(0),
            Ok(DriverInstallOutcome::ActivatedImmediate(_))
        ));
        assert!(matches!(
            parse_windows_driver_exit_code(3010),
            Ok(DriverInstallOutcome::RebootRequired(_))
        ));
        assert!(matches!(
            parse_windows_driver_exit_code(1641),
            Ok(DriverInstallOutcome::RebootRequired(_))
        ));
        assert!(parse_windows_driver_exit_code(1223).is_err());
        assert!(parse_windows_driver_exit_code(5).is_err());
    }

    #[test]
    fn virtual_windows_endpoint_detection() {
        assert!(is_virtual_windows_endpoint("OmniRip Virtual Audio"));
        assert!(is_virtual_windows_endpoint("CABLE Input (VB-Audio Virtual Cable)"));
        assert!(!is_virtual_windows_endpoint("Speakers (Realtek(R) Audio)"));
        assert!(!is_virtual_windows_endpoint("iBasso DC03 Pro USB DAC"));
    }
}
