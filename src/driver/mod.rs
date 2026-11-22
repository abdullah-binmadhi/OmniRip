//! OmniRip Cross-Platform Audio Driver Management, System Loopback Binding & OS Elevation.

pub mod bundle;
pub mod linux;
pub mod windows;

/// Result of attempting to install or activate the OS System-Wide Sound Engine driver.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DriverInstallOutcome {
    /// Driver installed and active immediately — no OS restart required.
    ActivatedImmediate(String),
    /// Driver installed, but the OS requires a one-time reboot (e.g. Windows 3010) before activation.
    RebootRequired(String),
}

/// Complete cross-platform diagnostic health snapshot for System-Wide EQ & Setup Gate.
#[derive(Debug, Clone)]
pub struct SystemAudioHealth {
    pub driver_installed: bool,
    pub driver_loaded: bool,
    pub driver_version: Option<u32>,
    pub expected_version: u32,
    pub needs_upgrade: bool,
    pub zero_dot_shm_ready: bool,
    pub physical_output_name: Option<String>,
    pub default_output_name: Option<String>,
}

/// Identifies virtual loopback/cable endpoints so OmniRip never mistakes them for physical speakers/DACs.
pub fn is_virtual_audio_device_name(name: &str) -> bool {
    let low = name.to_lowercase();
    low.contains("omnirip")
        || low.contains("blackhole")
        || low.contains("soundflower")
        || low.contains("loopback")
        || low.contains("vb-audio")
        || low.contains("cable input")
        || low.contains("cable output")
        || low.contains("virtual")
        || low.contains("background music")
        || low.contains("zoomaudiodevice")
        || low.contains("teams audio")
}

#[cfg(target_os = "macos")]
mod macos_driver {
    use super::bundle::{
        applescript_escape, locate_driver_source, read_bundle_version, shell_single_quote,
        DriverSource, EXPECTED_DRIVER_BUNDLE_VERSION,
    };
    use super::{is_virtual_audio_device_name, DriverInstallOutcome, SystemAudioHealth};
    use std::path::{Path, PathBuf};
    use std::process::Command;
    use std::thread;
    use std::time::Duration;

    const INSTALLED_DRIVER_PATH: &str = "/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver";

    #[repr(C)]
    #[derive(Debug, Copy, Clone)]
    pub struct AudioObjectPropertyAddress {
        pub m_selector: u32,
        pub m_scope: u32,
        pub m_element: u32,
    }

    pub const K_AUDIO_OBJECT_SYSTEM_OBJECT: u32 = 1;
    pub const K_AUDIO_HARDWARE_PROPERTY_DEFAULT_OUTPUT_DEVICE: u32 = 0x644f7574; // 'dOut'
    pub const K_AUDIO_HARDWARE_PROPERTY_DEVICES: u32 = 0x64657623; // 'dev#'
    pub const K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL: u32 = 0x676c6f62; // 'glob'
    pub const K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT: u32 = 0x6f757470; // 'outp'
    pub const K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN: u32 = 0;
    pub const K_AUDIO_OBJECT_PROPERTY_NAME: u32 = 0x6c6e616d; // 'lnam'
    pub const K_AUDIO_DEVICE_PROPERTY_STREAMS: u32 = 0x73746d23; // 'stm#'
    pub const K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR: u32 = 0x766f6c6d; // 'volm'
    pub const K_AUDIO_DEVICE_PROPERTY_MUTE: u32 = 0x6d757465; // 'mute'

    #[link(name = "CoreAudio", kind = "framework")]
    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        pub fn AudioObjectGetPropertyDataSize(
            in_object_id: u32,
            in_address: *const AudioObjectPropertyAddress,
            in_qualifier_data_size: u32,
            in_qualifier_data: *const std::ffi::c_void,
            out_data_size: *mut u32,
        ) -> i32;

        pub fn AudioObjectGetPropertyData(
            in_object_id: u32,
            in_address: *const AudioObjectPropertyAddress,
            in_qualifier_data_size: u32,
            in_qualifier_data: *const std::ffi::c_void,
            io_data_size: *mut u32,
            out_data: *mut std::ffi::c_void,
        ) -> i32;

        pub fn AudioObjectSetPropertyData(
            in_object_id: u32,
            in_address: *const AudioObjectPropertyAddress,
            in_qualifier_data_size: u32,
            in_qualifier_data: *const std::ffi::c_void,
            in_data_size: u32,
            in_data: *const std::ffi::c_void,
        ) -> i32;

        pub fn CFStringGetCString(
            the_string: *const std::ffi::c_void,
            buffer: *mut u8,
            buffer_size: isize,
            encoding: u32,
        ) -> bool;

        pub fn CFRelease(cf: *const std::ffi::c_void);
    }

    extern "C" {
        fn geteuid() -> u32;
        fn isatty(fd: i32) -> i32;
    }

    pub struct DriverStatus {
        pub installed: bool,
        pub loaded: bool,
        pub omnirip_device_id: Option<u32>,
        pub current_default_device_id: Option<u32>,
        pub current_default_device_name: Option<String>,
    }

    /// Returns the CFBundleVersion of `/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver`, if installed.
    pub fn installed_driver_version() -> Option<u32> {
        let p = Path::new(INSTALLED_DRIVER_PATH);
        if !p.exists() {
            return None;
        }
        read_bundle_version(p).or(Some(1))
    }

    /// Check the current status of OmniRipAudio.driver and CoreAudio routing.
    pub fn check_status() -> DriverStatus {
        let installed = Path::new(INSTALLED_DRIVER_PATH).exists();
        let omnirip_id = get_device_id_by_name("OmniRip Audio");
        let loaded = omnirip_id.is_some();
        let default_id = get_default_output_device_id();
        let default_name = default_id.and_then(get_device_name);

        DriverStatus {
            installed,
            loaded,
            omnirip_device_id: omnirip_id,
            current_default_device_id: default_id,
            current_default_device_name: default_name,
        }
    }

    /// Returns full macOS System Audio health (including HAL v2 upgrade check and Zero-Dot SHM readiness).
    pub fn check_system_audio_health() -> SystemAudioHealth {
        let st = check_status();
        let ver = installed_driver_version();
        let needs_upgrade = st.installed && ver.map(|v| v < EXPECTED_DRIVER_BUNDLE_VERSION).unwrap_or(true);
        let shm_ready = crate::dsp::shm_capture::ShmRingReader::is_available();
        let phys_name = first_physical_output_device_id().and_then(get_device_name);

        SystemAudioHealth {
            driver_installed: st.installed,
            driver_loaded: st.loaded,
            driver_version: ver,
            expected_version: EXPECTED_DRIVER_BUNDLE_VERSION,
            needs_upgrade,
            zero_dot_shm_ready: shm_ready,
            physical_output_name: phys_name,
            default_output_name: st.current_default_device_name,
        }
    }

    /// Retrieve the current macOS system default output device ID.
    pub fn get_default_output_device_id() -> Option<u32> {
        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_HARDWARE_PROPERTY_DEFAULT_OUTPUT_DEVICE,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let mut device_id: u32 = 0;
        let mut size = std::mem::size_of::<u32>() as u32;

        let status = unsafe {
            AudioObjectGetPropertyData(
                K_AUDIO_OBJECT_SYSTEM_OBJECT,
                &address,
                0,
                std::ptr::null(),
                &mut size,
                &mut device_id as *mut u32 as *mut std::ffi::c_void,
            )
        };

        if status == 0 && device_id != 0 {
            Some(device_id)
        } else {
            None
        }
    }

    /// Set the macOS system default output device.
    pub fn set_default_output_device_id(device_id: u32) -> Result<(), String> {
        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_HARDWARE_PROPERTY_DEFAULT_OUTPUT_DEVICE,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let size = std::mem::size_of::<u32>() as u32;

        let status = unsafe {
            AudioObjectSetPropertyData(
                K_AUDIO_OBJECT_SYSTEM_OBJECT,
                &address,
                0,
                std::ptr::null(),
                size,
                &device_id as *const u32 as *const std::ffi::c_void,
            )
        };

        if status == 0 {
            Ok(())
        } else {
            Err(format!("AudioObjectSetPropertyData failed with status: {}", status))
        }
    }

    /// Get device name by device ID.
    pub fn get_device_name(device_id: u32) -> Option<String> {
        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_OBJECT_PROPERTY_NAME,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let mut cf_str: *const std::ffi::c_void = std::ptr::null();
        let mut size = std::mem::size_of::<*const std::ffi::c_void>() as u32;

        let status = unsafe {
            AudioObjectGetPropertyData(
                device_id,
                &address,
                0,
                std::ptr::null(),
                &mut size,
                &mut cf_str as *mut *const std::ffi::c_void as *mut std::ffi::c_void,
            )
        };

        if status == 0 && !cf_str.is_null() {
            let mut buffer = [0u8; 256];
            let ok = unsafe { CFStringGetCString(cf_str, buffer.as_mut_ptr(), 256, 0x08000100) };
            unsafe { CFRelease(cf_str) };
            if ok {
                let len = buffer.iter().position(|&c| c == 0).unwrap_or(buffer.len());
                return String::from_utf8(buffer[..len].to_vec()).ok();
            }
        }
        None
    }

    fn device_has_output_streams(device_id: u32) -> bool {
        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_DEVICE_PROPERTY_STREAMS,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let mut size: u32 = 0;
        let status = unsafe {
            AudioObjectGetPropertyDataSize(
                device_id,
                &address,
                0,
                std::ptr::null(),
                &mut size,
            )
        };
        status == 0 && size > 0
    }

    fn all_device_ids() -> Vec<u32> {
        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_HARDWARE_PROPERTY_DEVICES,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let mut size: u32 = 0;

        let status = unsafe {
            AudioObjectGetPropertyDataSize(
                K_AUDIO_OBJECT_SYSTEM_OBJECT,
                &address,
                0,
                std::ptr::null(),
                &mut size,
            )
        };

        if status != 0 || size == 0 {
            return Vec::new();
        }

        let count = size as usize / std::mem::size_of::<u32>();
        let mut devices = vec![0u32; count];

        let status = unsafe {
            AudioObjectGetPropertyData(
                K_AUDIO_OBJECT_SYSTEM_OBJECT,
                &address,
                0,
                std::ptr::null(),
                &mut size,
                devices.as_mut_ptr() as *mut std::ffi::c_void,
            )
        };

        if status != 0 {
            return Vec::new();
        }
        devices
    }

    /// Enumerates all real physical output devices (Speakers, Headphones, AirPods, Bluetooth, USB DAC, HDMI/Display)
    /// while excluding virtual loopback drivers.
    pub fn list_physical_output_devices() -> Vec<(u32, String)> {
        let mut list = Vec::new();
        for id in all_device_ids() {
            if !device_has_output_streams(id) {
                continue;
            }
            if let Some(name) = get_device_name(id) {
                let low = name.to_lowercase();
                if !is_virtual_audio_device_name(&name) && !low.contains("mic") {
                    list.push((id, name));
                }
            }
        }
        list.sort_by_key(|(_, name)| {
            let n = name.to_lowercase();
            if n.contains("ibasso") || n.contains("dac") || n.contains("fiio") || n.contains("chord") || n.contains("schiit") {
                0
            } else if n.contains("headphone") {
                1
            } else if n.contains("airpods") || n.contains("bluetooth") || n.contains("beats") {
                2
            } else if n.contains("speaker") || n.contains("built-in") || n.contains("macbook") {
                3
            } else {
                4
            }
        });
        list
    }

    /// Picks the highest-priority physical output device ID available on this Mac.
    pub fn first_physical_output_device_id() -> Option<u32> {
        list_physical_output_devices().into_iter().next().map(|(id, _)| id)
    }

    /// Find device ID matching a substring.
    pub fn get_device_id_by_name(name_substr: &str) -> Option<u32> {
        let needle = name_substr.to_lowercase();
        for id in all_device_ids() {
            if let Some(name) = get_device_name(id) {
                if name.to_lowercase().contains(&needle) {
                    return Some(id);
                }
            }
        }
        None
    }

    /// Query volume scalar from an output device (0.0 to 1.0).
    pub fn get_device_volume(device_id: u32) -> Option<f32> {
        let mut volume: f32 = 0.0;
        let mut size = std::mem::size_of::<f32>() as u32;

        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let status = unsafe {
            AudioObjectGetPropertyData(
                device_id,
                &address,
                0,
                std::ptr::null(),
                &mut size,
                &mut volume as *mut f32 as *mut std::ffi::c_void,
            )
        };
        if status == 0 {
            return Some(volume.clamp(0.0, 1.0));
        }

        let ch_addr = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
            m_element: 1,
        };
        let ch_status = unsafe {
            AudioObjectGetPropertyData(
                device_id,
                &ch_addr,
                0,
                std::ptr::null(),
                &mut size,
                &mut volume as *mut f32 as *mut std::ffi::c_void,
            )
        };
        if ch_status == 0 {
            Some(volume.clamp(0.0, 1.0))
        } else {
            None
        }
    }

    /// Set hardware volume scalar on an output device (0.0 to 1.0).
    pub fn set_device_volume(device_id: u32, volume: f32) -> Result<(), String> {
        let clamped = volume.clamp(0.0, 1.0);
        let size = std::mem::size_of::<f32>() as u32;
        let mut any_success = false;

        let address = AudioObjectPropertyAddress {
            m_selector: K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR,
            m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
            m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
        };
        let status = unsafe {
            AudioObjectSetPropertyData(
                device_id,
                &address,
                0,
                std::ptr::null(),
                size,
                &clamped as *const f32 as *const std::ffi::c_void,
            )
        };
        if status == 0 {
            any_success = true;
        }

        for elem in [1u32, 2u32] {
            let ch_addr = AudioObjectPropertyAddress {
                m_selector: K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR,
                m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
                m_element: elem,
            };
            let ch_status = unsafe {
                AudioObjectSetPropertyData(
                    device_id,
                    &ch_addr,
                    0,
                    std::ptr::null(),
                    size,
                    &clamped as *const f32 as *const std::ffi::c_void,
                )
            };
            if ch_status == 0 {
                any_success = true;
            }
        }

        if any_success {
            Ok(())
        } else {
            Err(format!("set_device_volume failed on device {}", device_id))
        }
    }

    /// Unmute an output device across main and stereo elements.
    pub fn unmute_device(device_id: u32) -> Result<(), String> {
        let mute_val: u32 = 0;
        let size = std::mem::size_of::<u32>() as u32;
        let mut any_success = false;

        for elem in [K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN, 1, 2] {
            let address = AudioObjectPropertyAddress {
                m_selector: K_AUDIO_DEVICE_PROPERTY_MUTE,
                m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
                m_element: elem,
            };
            let status = unsafe {
                AudioObjectSetPropertyData(
                    device_id,
                    &address,
                    0,
                    std::ptr::null(),
                    size,
                    &mute_val as *const u32 as *const std::ffi::c_void,
                )
            };
            if status == 0 {
                any_success = true;
            }
        }

        if any_success {
            Ok(())
        } else {
            Err(format!("unmute_device failed or not supported on device {}", device_id))
        }
    }

    /// Automatically ensure device is unmuted and at a calibrated safe listening volume.
    pub fn auto_heal_device_volume_and_mute(device_id: u32) {
        let _ = unmute_device(device_id);
        let current_vol = get_device_volume(device_id).unwrap_or(0.0);
        if current_vol < 0.05 {
            let (_, saved_scalar) = crate::dsp::volume_storage::load_volume_settings();
            let _ = set_device_volume(device_id, saved_scalar);
        }
    }

    /// Auto-heal volume and mute for any device matching keyword.
    pub fn auto_heal_physical_output(keyword: &str) {
        if let Some(id) = get_device_id_by_name(keyword) {
            auto_heal_device_volume_and_mute(id);
        }
    }

    /// Locates or compiles `OmniRipAudio.driver` cleanly as the current user BEFORE any elevation.
    fn prepare_driver_bundle() -> Result<PathBuf, String> {
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|d| d.to_path_buf()))
            .unwrap_or_default();
        let cwd = std::env::current_dir().unwrap_or_default();

        match locate_driver_source(&exe_dir, &cwd) {
            Some(DriverSource::Bundle(path)) => Ok(path),
            Some(DriverSource::SourceTree(dir)) => {
                let status = Command::new("make")
                    .arg("-C")
                    .arg(&dir)
                    .status()
                    .map_err(|e| format!("Failed to run make for OmniRipAudio.driver: {}", e))?;
                if !status.success() {
                    return Err("Failed to compile OmniRipAudio.driver bundle.".to_string());
                }
                Ok(dir.join("OmniRipAudio.driver"))
            }
            None => Err(
                "OmniRipAudio.driver was not found next to omnirip, in Homebrew pkgshare, or in a source checkout."
                    .to_string(),
            ),
        }
    }

    fn build_elevated_install_shell_cmd(bundle_path: &Path) -> String {
        let quoted_src = shell_single_quote(&bundle_path.to_string_lossy());
        let quoted_dst = shell_single_quote(INSTALLED_DRIVER_PATH);
        format!(
            "rm -rf {dst} && cp -R {src} {dst} && chown -R root:wheel {dst} && (xattr -dr com.apple.quarantine {dst} 2>/dev/null || true) && (launchctl kickstart -k system/com.apple.audio.coreaudiod || killall coreaudiod)",
            src = quoted_src,
            dst = quoted_dst
        )
    }

    fn wait_for_driver_registration() -> DriverInstallOutcome {
        for _ in 0..12 {
            thread::sleep(Duration::from_millis(500));
            let loaded = get_device_id_by_name("OmniRip Audio").is_some();
            let ver = installed_driver_version().unwrap_or(1);
            if loaded && ver >= EXPECTED_DRIVER_BUNDLE_VERSION {
                return DriverInstallOutcome::ActivatedImmediate(
                    "OmniRip Audio v2 (Zero-Dot HAL) installed and active.".to_string(),
                );
            }
        }
        DriverInstallOutcome::RebootRequired(
            "Driver files installed, but macOS CoreAudio has not switched to the new bundle yet. Please restart once to finish activating."
                .to_string(),
        )
    }

    /// Installs OmniRipAudio.driver into `/Library/Audio/Plug-Ins/HAL/`.
    /// Automatically uses Touch ID / Admin GUI dialog if invoked without a TTY (e.g. `curl | bash`).
    pub fn install_driver() -> Result<(), Box<dyn std::error::Error>> {
        let is_root = unsafe { geteuid() == 0 };
        let has_tty = unsafe { isatty(0) == 1 };

        if !is_root && !has_tty {
            match install_driver_gui() {
                Ok(DriverInstallOutcome::ActivatedImmediate(msg))
                | Ok(DriverInstallOutcome::RebootRequired(msg)) => {
                    println!("[OmniRip] {}", msg);
                    return Ok(());
                }
                Err(e) => return Err(e.into()),
            }
        }

        let bundle_path = prepare_driver_bundle()?;
        let shell_cmd = build_elevated_install_shell_cmd(&bundle_path);
        println!("[OmniRip] Installing OmniRipAudio.driver v{} to /Library/Audio/Plug-Ins/HAL/...", EXPECTED_DRIVER_BUNDLE_VERSION);

        let status = if is_root {
            Command::new("sh").args(["-c", &shell_cmd]).status()?
        } else {
            Command::new("sudo").args(["sh", "-c", &shell_cmd]).status()?
        };

        if !status.success() {
            return Err("Failed to install OmniRipAudio.driver to /Library/Audio/Plug-Ins/HAL/.".into());
        }

        match wait_for_driver_registration() {
            DriverInstallOutcome::ActivatedImmediate(msg)
            | DriverInstallOutcome::RebootRequired(msg) => {
                println!("[OmniRip] {}", msg);
                Ok(())
            }
        }
    }

    /// Install OmniRipAudio.driver via macOS graphical authorization dialog (Touch ID / Apple Watch / Password).
    pub fn install_driver_gui() -> Result<DriverInstallOutcome, String> {
        let bundle_path = prepare_driver_bundle()?;
        let shell_cmd = build_elevated_install_shell_cmd(&bundle_path);
        let prompt = "OmniRip needs administrator permission to install the OmniRip Sound Engine driver into macOS Audio (/Library/Audio/Plug-Ins/HAL) for zero-dot system-wide EQ.";
        let script = format!(
            "do shell script \"{}\" with prompt \"{}\" with administrator privileges",
            applescript_escape(&shell_cmd),
            applescript_escape(prompt)
        );
        let output = Command::new("osascript")
            .arg("-e")
            .arg(script)
            .output()
            .map_err(|e| format!("Failed to launch macOS authorization dialog: {}", e))?;

        if output.status.success() {
            Ok(wait_for_driver_registration())
        } else {
            let err = String::from_utf8_lossy(&output.stderr);
            Err(format!("Authorization canceled or failed: {}", err.trim()))
        }
    }

    /// Uninstall OmniRipAudio.driver via macOS graphical authorization dialog (restores physical output first).
    pub fn uninstall_driver_gui() -> Result<String, String> {
        if let Some(phys_id) = first_physical_output_device_id() {
            let _ = set_default_output_device_id(phys_id);
        }
        if !Path::new(INSTALLED_DRIVER_PATH).exists() {
            return Ok("OmniRip Audio driver is already uninstalled.".to_string());
        }
        let quoted_dst = shell_single_quote(INSTALLED_DRIVER_PATH);
        let shell_cmd = format!(
            "rm -rf {} && (launchctl kickstart -k system/com.apple.audio.coreaudiod || killall coreaudiod)",
            quoted_dst
        );
        let prompt = "OmniRip needs administrator permission to remove the OmniRip Sound Engine driver from macOS Audio.";
        let script = format!(
            "do shell script \"{}\" with prompt \"{}\" with administrator privileges",
            applescript_escape(&shell_cmd),
            applescript_escape(prompt)
        );
        let output = Command::new("osascript")
            .arg("-e")
            .arg(script)
            .output()
            .map_err(|e| format!("Failed to launch authorization dialog: {}", e))?;

        if output.status.success() {
            Ok("OmniRip Audio driver removed cleanly.".to_string())
        } else {
            let err = String::from_utf8_lossy(&output.stderr);
            Err(format!("Uninstall authorization canceled or failed: {}", err.trim()))
        }
    }

    /// Uninstall OmniRipAudio.driver from `/Library/Audio/Plug-Ins/HAL/`.
    pub fn uninstall_driver() -> Result<(), Box<dyn std::error::Error>> {
        if let Some(phys_id) = first_physical_output_device_id() {
            let _ = set_default_output_device_id(phys_id);
        }
        if !Path::new(INSTALLED_DRIVER_PATH).exists() {
            println!("[OmniRip] Driver is not installed.");
            return Ok(());
        }

        let is_root = unsafe { geteuid() == 0 };
        let has_tty = unsafe { isatty(0) == 1 };
        if !is_root && !has_tty {
            let msg = uninstall_driver_gui()?;
            println!("[OmniRip] {}", msg);
            return Ok(());
        }

        let quoted_dst = shell_single_quote(INSTALLED_DRIVER_PATH);
        let shell_cmd = format!(
            "rm -rf {} && (launchctl kickstart -k system/com.apple.audio.coreaudiod || killall coreaudiod)",
            quoted_dst
        );
        let status = if is_root {
            Command::new("sh").args(["-c", &shell_cmd]).status()?
        } else {
            Command::new("sudo").args(["sh", "-c", &shell_cmd]).status()?
        };
        if !status.success() {
            return Err("Failed to remove OmniRipAudio.driver.".into());
        }
        println!("[OmniRip] Driver uninstalled cleanly.");
        Ok(())
    }

    pub fn trigger_system_reboot() -> Result<(), String> {
        let out = Command::new("osascript")
            .args(["-e", "tell application \"System Events\" to restart"])
            .output()
            .map_err(|e| format!("Failed to trigger macOS restart: {}", e))?;
        if out.status.success() {
            Ok(())
        } else {
            Err("macOS restart was canceled or declined.".to_string())
        }
    }
}

#[cfg(target_os = "macos")]
pub use macos_driver::*;

#[cfg(not(target_os = "macos"))]
mod fallback_driver {
    use super::bundle::EXPECTED_DRIVER_BUNDLE_VERSION;
    use super::{DriverInstallOutcome, SystemAudioHealth};

    pub struct DriverStatus {
        pub installed: bool,
        pub loaded: bool,
        pub omnirip_device_id: Option<u32>,
        pub current_default_device_id: Option<u32>,
        pub current_default_device_name: Option<String>,
    }

    pub fn check_status() -> DriverStatus {
        #[cfg(target_os = "linux")]
        {
            let loaded = super::linux::is_virtual_sink_ready();
            let default_name = super::linux::get_default_sink();
            return DriverStatus {
                installed: true,
                loaded,
                omnirip_device_id: None,
                current_default_device_id: None,
                current_default_device_name: default_name,
            };
        }
        #[cfg(target_os = "windows")]
        {
            let present = super::windows::detect_virtual_sink_present();
            let default_name = super::windows::get_default_playback_device_name();
            return DriverStatus {
                installed: present,
                loaded: present,
                omnirip_device_id: None,
                current_default_device_id: None,
                current_default_device_name: default_name,
            };
        }
        #[cfg(not(any(target_os = "linux", target_os = "windows")))]
        DriverStatus {
            installed: false,
            loaded: false,
            omnirip_device_id: None,
            current_default_device_id: None,
            current_default_device_name: None,
        }
    }

    pub fn check_system_audio_health() -> SystemAudioHealth {
        #[cfg(target_os = "linux")]
        {
            let loaded = super::linux::is_virtual_sink_ready();
            let phys = super::linux::list_physical_sinks().into_iter().next();
            let def = super::linux::get_default_sink();
            return SystemAudioHealth {
                driver_installed: true,
                driver_loaded: loaded,
                driver_version: Some(EXPECTED_DRIVER_BUNDLE_VERSION),
                expected_version: EXPECTED_DRIVER_BUNDLE_VERSION,
                needs_upgrade: false,
                zero_dot_shm_ready: true,
                physical_output_name: phys,
                default_output_name: def,
            };
        }
        #[cfg(target_os = "windows")]
        {
            let present = super::windows::detect_virtual_sink_present();
            let def = super::windows::get_default_playback_device_name();
            return SystemAudioHealth {
                driver_installed: present,
                driver_loaded: present,
                driver_version: if present { Some(EXPECTED_DRIVER_BUNDLE_VERSION) } else { None },
                expected_version: EXPECTED_DRIVER_BUNDLE_VERSION,
                needs_upgrade: false,
                zero_dot_shm_ready: present,
                physical_output_name: def.clone(),
                default_output_name: def,
            };
        }
        #[cfg(not(any(target_os = "linux", target_os = "windows")))]
        SystemAudioHealth {
            driver_installed: false,
            driver_loaded: false,
            driver_version: None,
            expected_version: EXPECTED_DRIVER_BUNDLE_VERSION,
            needs_upgrade: false,
            zero_dot_shm_ready: false,
            physical_output_name: None,
            default_output_name: None,
        }
    }

    pub fn installed_driver_version() -> Option<u32> {
        Some(EXPECTED_DRIVER_BUNDLE_VERSION)
    }

    pub fn list_physical_output_devices() -> Vec<(u32, String)> {
        Vec::new()
    }

    pub fn first_physical_output_device_id() -> Option<u32> {
        None
    }

    pub fn get_default_output_device_id() -> Option<u32> {
        None
    }

    pub fn set_default_output_device_id(_device_id: u32) -> Result<(), String> {
        Ok(())
    }

    pub fn get_device_name(_device_id: u32) -> Option<String> {
        None
    }

    pub fn get_device_id_by_name(_name_substr: &str) -> Option<u32> {
        None
    }

    pub fn get_device_volume(_device_id: u32) -> Option<f32> {
        None
    }

    pub fn set_device_volume(_device_id: u32, _volume: f32) -> Result<(), String> {
        Ok(())
    }

    pub fn unmute_device(_device_id: u32) -> Result<(), String> {
        Ok(())
    }

    pub fn auto_heal_device_volume_and_mute(_device_id: u32) {}

    pub fn auto_heal_physical_output(_keyword: &str) {}

    pub fn install_driver_gui() -> Result<DriverInstallOutcome, String> {
        #[cfg(target_os = "linux")]
        {
            return super::linux::install_driver_gui();
        }
        #[cfg(target_os = "windows")]
        {
            return super::windows::install_driver_gui();
        }
        #[cfg(not(any(target_os = "linux", target_os = "windows")))]
        Ok(DriverInstallOutcome::ActivatedImmediate(
            "Native system audio routing ready.".to_string(),
        ))
    }

    pub fn uninstall_driver_gui() -> Result<String, String> {
        #[cfg(target_os = "linux")]
        {
            super::linux::teardown_virtual_sink(None, None);
            return Ok("Removed Linux user-space virtual sink.".to_string());
        }
        #[cfg(not(target_os = "linux"))]
        Ok("No virtual driver removed.".to_string())
    }

    pub fn install_driver() -> Result<(), Box<dyn std::error::Error>> {
        match install_driver_gui() {
            Ok(DriverInstallOutcome::ActivatedImmediate(m))
            | Ok(DriverInstallOutcome::RebootRequired(m)) => {
                println!("[OmniRip] {}", m);
                Ok(())
            }
            Err(e) => Err(e.into()),
        }
    }

    pub fn uninstall_driver() -> Result<(), Box<dyn std::error::Error>> {
        let msg = uninstall_driver_gui()?;
        println!("[OmniRip] {}", msg);
        Ok(())
    }

    pub fn trigger_system_reboot() -> Result<(), String> {
        #[cfg(target_os = "windows")]
        {
            return super::windows::trigger_system_reboot();
        }
        #[cfg(not(target_os = "windows"))]
        Err("System reboot is not required on this platform.".to_string())
    }
}

#[cfg(not(target_os = "macos"))]
pub use fallback_driver::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_driver_status_query() {
        let status = check_status();
        println!("Driver status: installed={}, loaded={}", status.installed, status.loaded);
        if let Some(name) = status.current_default_device_name {
            println!("Default output device: {}", name);
            assert!(!name.is_empty());
        }
    }

    #[test]
    fn virtual_device_filter_rejects_loopbacks_and_keeps_bluetooth_dacs() {
        assert!(is_virtual_audio_device_name("OmniRip Audio"));
        assert!(is_virtual_audio_device_name("BlackHole 2ch"));
        assert!(is_virtual_audio_device_name("CABLE Input (VB-Audio Virtual)"));
        assert!(!is_virtual_audio_device_name("AirPods Pro"));
        assert!(!is_virtual_audio_device_name("LG ULTRAGEAR (DisplayPort)"));
        assert!(!is_virtual_audio_device_name("iBasso DC03 Pro"));
        assert!(!is_virtual_audio_device_name("MacBook Pro Speakers"));
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_get_default_output_device_id() {
        let dev_id = get_default_output_device_id();
        assert!(dev_id.is_some(), "System must have a default output audio device");
        let id = dev_id.unwrap();
        let name = get_device_name(id);
        assert!(name.is_some(), "Default output device must have a name");
        println!("Default audio device ID {}: {}", id, name.unwrap());
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_auto_heal_physical_output_and_volume() {
        if let Some(id) = get_default_output_device_id() {
            let cur_vol = get_device_volume(id);
            println!("Current physical volume on default device {}: {:?}", id, cur_vol);
            assert!(id > 0);
        }
    }

    #[test]
    fn test_volume_cubic_curve_calibration() {
        for tick in 0..=16 {
            let v = tick as f32 / 16.0f32;
            let stock_gain = v * v * v;
            let db = if stock_gain > 0.0001 {
                20.0 * stock_gain.log10()
            } else {
                -96.0
            };
            if tick == 1 {
                assert!((stock_gain - 0.00024414).abs() < 1e-6);
                assert!((db - (-72.24)).abs() < 0.1);
            } else if tick == 8 {
                assert!((stock_gain - 0.125).abs() < 1e-6);
                assert!((db - (-18.06)).abs() < 0.1);
            } else if tick == 16 {
                assert!((stock_gain - 1.0).abs() < 1e-6);
                assert!(db.abs() < 1e-4);
            }
        }
    }
}

/// CLI runner for driver commands.
pub fn run_driver_cli(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let sub = args.first().map(|s| s.as_str()).unwrap_or("status");
    match sub {
        "status" => {
            let health = check_system_audio_health();
            println!("--- OmniRip Audio Driver Status ---");
            println!("Installed: {}", if health.driver_installed { "Yes" } else { "No" });
            println!("Loaded in OS Audio: {}", if health.driver_loaded { "Yes" } else { "No" });
            if let Some(v) = health.driver_version {
                println!("Driver Version: v{} (expected v{})", v, health.expected_version);
            }
            println!(
                "Zero-Dot / Zero-Echo Ready: {}",
                if health.zero_dot_shm_ready { "Yes" } else { "No" }
            );
            if let Some(name) = health.default_output_name {
                println!("Current Default Output: {}", name);
            }
            if let Some(phys) = health.physical_output_name {
                println!("Detected Physical Output: {}", phys);
            }
        }
        "install" => {
            install_driver()?;
        }
        "install-gui" => {
            match install_driver_gui() {
                Ok(DriverInstallOutcome::ActivatedImmediate(msg))
                | Ok(DriverInstallOutcome::RebootRequired(msg)) => println!("[OmniRip] {}", msg),
                Err(e) => return Err(e.into()),
            }
        }
        "uninstall" => {
            uninstall_driver()?;
        }
        "uninstall-gui" => {
            let msg = uninstall_driver_gui()?;
            println!("[OmniRip] {}", msg);
        }
        _ => {
            eprintln!("Usage: omnirip driver [status | install | install-gui | uninstall | uninstall-gui]");
            std::process::exit(1);
        }
    }
    Ok(())
}
