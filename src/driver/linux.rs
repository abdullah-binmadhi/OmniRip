//! Linux PipeWire / PulseAudio user-space virtual sink routing (`Orchestria_Audio`).
//!
//! Creates an isolated user-space null sink (`Orchestria_Audio`) so desktop audio is routed
//! exclusively into `Orchestria_Audio.monitor` -> Orchestria 64-bit DSP -> physical speakers/DAC
//! with ZERO double-audio echo, ZERO `sudo`, and ZERO reboots.

#![cfg_attr(not(target_os = "linux"), allow(dead_code))]

use super::DriverInstallOutcome;
use std::process::Command;

pub const ORCHESTRIA_LINUX_SINK: &str = "Orchestria_Audio";

/// Parses `pactl list short sinks` output into sink names.
pub fn parse_pactl_sinks(output: &str) -> Vec<String> {
    output
        .lines()
        .filter_map(|line| {
            let mut cols = line.split_whitespace();
            let _idx = cols.next()?;
            let name = cols.next()?.trim();
            if name.is_empty() {
                None
            } else {
                Some(name.to_string())
            }
        })
        .collect()
}

pub fn is_virtual_linux_sink(name: &str) -> bool {
    let low = name.to_lowercase();
    low.contains("orchestria") || low.contains("null")
}

pub fn get_default_sink() -> Option<String> {
    let out = Command::new("pactl").args(["get-default-sink"]).output().ok()?;
    if !out.status.success() {
        return None;
    }
    let name = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if name.is_empty() {
        None
    } else {
        Some(name)
    }
}

pub fn list_physical_sinks() -> Vec<String> {
    let Ok(out) = Command::new("pactl").args(["list", "short", "sinks"]).output() else {
        return Vec::new();
    };
    if !out.status.success() {
        return Vec::new();
    }
    parse_pactl_sinks(&String::from_utf8_lossy(&out.stdout))
        .into_iter()
        .filter(|s| !is_virtual_linux_sink(s))
        .collect()
}

pub fn set_default_sink(sink_name: &str) -> Result<(), String> {
    let status = Command::new("pactl")
        .args(["set-default-sink", sink_name])
        .status()
        .map_err(|e| format!("Failed to invoke pactl: {}", e))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("pactl set-default-sink '{}' failed", sink_name))
    }
}

/// Ensures the user-space `Orchestria_Audio` virtual sink exists, returning its PulseAudio module ID if newly created.
pub fn ensure_virtual_sink() -> Result<Option<u32>, String> {
    if let Ok(out) = Command::new("pactl").args(["list", "short", "sinks"]).output() {
        if out.status.success() {
            let existing = parse_pactl_sinks(&String::from_utf8_lossy(&out.stdout));
            if existing.iter().any(|s| s == ORCHESTRIA_LINUX_SINK) {
                return Ok(None);
            }
        }
    }

    let out = Command::new("pactl")
        .args([
            "load-module",
            "module-null-sink",
            &format!("sink_name={}", ORCHESTRIA_LINUX_SINK),
            "sink_properties=device.description=Orchestria_Audio",
        ])
        .output()
        .map_err(|e| format!("Failed to execute pactl (install pipewire-pulse or pulseaudio-utils): {}", e))?;

    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(format!("Failed to create virtual sink {}: {}", ORCHESTRIA_LINUX_SINK, err.trim()));
    }

    let mod_id = String::from_utf8_lossy(&out.stdout).trim().parse::<u32>().ok();
    Ok(mod_id)
}

pub fn teardown_virtual_sink(module_id: Option<u32>, saved_sink: Option<&str>) {
    if let Some(sink) = saved_sink {
        if !is_virtual_linux_sink(sink) {
            let _ = set_default_sink(sink);
        }
    } else if let Some(first_phys) = list_physical_sinks().first() {
        let _ = set_default_sink(first_phys);
    }

    if let Some(id) = module_id {
        let _ = Command::new("pactl")
            .args(["unload-module", &id.to_string()])
            .status();
    }
}

pub fn is_virtual_sink_ready() -> bool {
    let Ok(out) = Command::new("pactl").args(["list", "short", "sinks"]).output() else {
        return false;
    };
    if !out.status.success() {
        return false;
    }
    parse_pactl_sinks(&String::from_utf8_lossy(&out.stdout))
        .iter()
        .any(|s| s == ORCHESTRIA_LINUX_SINK)
}

pub fn install_driver_gui() -> Result<DriverInstallOutcome, String> {
    ensure_virtual_sink()?;
    Ok(DriverInstallOutcome::ActivatedImmediate(
        "PipeWire/PulseAudio user-space virtual sink (Orchestria_Audio) activated with zero sudo."
            .to_string(),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_pactl_short_sinks() {
        let sample = "\
42\talsa_output.pci-0000_00_1f.3.analog-stereo\tPipeWire\ts32le 2ch 48000Hz\tSUSPENDED
58\tOrchestria_Audio\tPipeWire\tfloat32le 2ch 48000Hz\tRUNNING
";
        let sinks = parse_pactl_sinks(sample);
        assert_eq!(
            sinks,
            vec![
                "alsa_output.pci-0000_00_1f.3.analog-stereo".to_string(),
                "Orchestria_Audio".to_string()
            ]
        );
        assert!(!is_virtual_linux_sink(&sinks[0]));
        assert!(is_virtual_linux_sink(&sinks[1]));
    }
}
