//! OmniRip CoreAudio HAL Driver Management & System Loopback Binding.

use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;

#[repr(C)]
#[derive(Debug, Copy, Clone)]
struct AudioObjectPropertyAddress {
    m_selector: u32,
    m_scope: u32,
    m_element: u32,
}

const K_AUDIO_OBJECT_SYSTEM_OBJECT: u32 = 1;
const K_AUDIO_HARDWARE_PROPERTY_DEFAULT_OUTPUT_DEVICE: u32 = 0x644f7574; // 'dOut'
const K_AUDIO_HARDWARE_PROPERTY_DEVICES: u32 = 0x64657623; // 'dev#'
const K_AUDIO_OBJECT_PROPERTY_SCOPE_GLOBAL: u32 = 0x676c6f62; // 'glob'
const K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT: u32 = 0x6f757470; // 'outp'
const K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN: u32 = 0;
const K_AUDIO_OBJECT_PROPERTY_NAME: u32 = 0x6c6e616d; // 'lnam'
const K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR: u32 = 0x766f6c6d; // 'volm'

#[link(name = "CoreAudio", kind = "framework")]
#[link(name = "CoreFoundation", kind = "framework")]
extern "C" {
    fn AudioObjectGetPropertyDataSize(
        in_object_id: u32,
        in_address: *const AudioObjectPropertyAddress,
        in_qualifier_data_size: u32,
        in_qualifier_data: *const std::ffi::c_void,
        out_data_size: *mut u32,
    ) -> i32;

    fn AudioObjectGetPropertyData(
        in_object_id: u32,
        in_address: *const AudioObjectPropertyAddress,
        in_qualifier_data_size: u32,
        in_qualifier_data: *const std::ffi::c_void,
        io_data_size: *mut u32,
        out_data: *mut std::ffi::c_void,
    ) -> i32;

    fn AudioObjectSetPropertyData(
        in_object_id: u32,
        in_address: *const AudioObjectPropertyAddress,
        in_qualifier_data_size: u32,
        in_qualifier_data: *const std::ffi::c_void,
        in_data_size: u32,
        in_data: *const std::ffi::c_void,
    ) -> i32;

    fn CFStringGetCString(
        the_string: *const std::ffi::c_void,
        buffer: *mut u8,
        buffer_size: isize,
        encoding: u32,
    ) -> bool;

    fn CFRelease(cf: *const std::ffi::c_void);
}

pub struct DriverStatus {
    pub installed: bool,
    pub loaded: bool,
    pub omnirip_device_id: Option<u32>,
    pub current_default_device_id: Option<u32>,
    pub current_default_device_name: Option<String>,
}

/// Check the current status of OmniRipAudio.driver and CoreAudio routing
pub fn check_status() -> DriverStatus {
    let installed = Path::new("/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver").exists();
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

/// Retrieve the current macOS system default output device ID
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

/// Set the macOS system default output device
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

/// Get device name by device ID
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
        let ok = unsafe { CFStringGetCString(cf_str, buffer.as_mut_ptr(), 256, 0x08000100) }; // kCFStringEncodingUTF8
        unsafe { CFRelease(cf_str) };
        if ok {
            let len = buffer.iter().position(|&c| c == 0).unwrap_or(buffer.len());
            return String::from_utf8(buffer[..len].to_vec()).ok();
        }
    }
    None
}

/// Find device ID matching a substring
pub fn get_device_id_by_name(name_substr: &str) -> Option<u32> {
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
        return None;
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
        return None;
    }

    for id in devices {
        if let Some(name) = get_device_name(id) {
            if name.to_lowercase().contains(&name_substr.to_lowercase()) {
                return Some(id);
            }
        }
    }
    None
}

/// Set hardware volume scalar on an output device (0.0 to 1.0)
pub fn set_device_volume(device_id: u32, volume: f32) -> Result<(), String> {
    let address = AudioObjectPropertyAddress {
        m_selector: K_AUDIO_DEVICE_PROPERTY_VOLUME_SCALAR,
        m_scope: K_AUDIO_OBJECT_PROPERTY_SCOPE_OUTPUT,
        m_element: K_AUDIO_OBJECT_PROPERTY_ELEMENT_MAIN,
    };
    let clamped = volume.clamp(0.0, 1.0);
    let size = std::mem::size_of::<f32>() as u32;

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
        Ok(())
    } else {
        Err(format!("set_device_volume failed with status: {}", status))
    }
}

/// Compile and install OmniRipAudio.driver to /Library/Audio/Plug-Ins/HAL/
pub fn install_driver() -> Result<(), Box<dyn std::error::Error>> {
    let fallback_dir = "/Users/abdullahbinmadhi/Projects/OmniRip";
    let bundle_path = if Path::new("drivers/omnirip_hal/OmniRipAudio.driver").exists() {
        std::path::PathBuf::from("drivers/omnirip_hal/OmniRipAudio.driver")
    } else if Path::new(&format!("{}/drivers/omnirip_hal/OmniRipAudio.driver", fallback_dir)).exists() {
        std::path::PathBuf::from(format!("{}/drivers/omnirip_hal/OmniRipAudio.driver", fallback_dir))
    } else {
        println!("[OmniRip] Building OmniRipAudio.driver from source...");
        let make_dir = if Path::new("drivers/omnirip_hal").exists() {
            "drivers/omnirip_hal"
        } else {
            "/Users/abdullahbinmadhi/Projects/OmniRip/drivers/omnirip_hal"
        };
        let build_status = Command::new("make")
            .arg("-C")
            .arg(make_dir)
            .status()?;

        if !build_status.success() {
            return Err("Failed to compile OmniRipAudio.driver bundle.".into());
        }
        std::path::PathBuf::from(format!("{}/OmniRipAudio.driver", make_dir))
    };

    println!("[OmniRip] Installing bundle to /Library/Audio/Plug-Ins/HAL/...");
    let cp_status = Command::new("sudo")
        .args([
            "cp",
            "-R",
            bundle_path.to_str().unwrap_or("drivers/omnirip_hal/OmniRipAudio.driver"),
            "/Library/Audio/Plug-Ins/HAL/",
        ])
        .status()?;

    if !cp_status.success() {
        return Err("Failed to copy driver to /Library/Audio/Plug-Ins/HAL/ (sudo failed).".into());
    }

    println!("[OmniRip] Reloading CoreAudio daemon (coreaudiod)...");
    let kill_status = Command::new("sudo")
        .args(["killall", "-9", "coreaudiod"])
        .status()?;

    if !kill_status.success() {
        eprintln!("[OmniRip] Warning: killall -9 coreaudiod returned non-zero.");
    }

    // Wait up to 5 seconds for coreaudiod to register OmniRip Audio
    println!("[OmniRip] Waiting for CoreAudio to register OmniRip Audio...");
    for _ in 0..10 {
        thread::sleep(Duration::from_millis(500));
        if let Some(id) = get_device_id_by_name("OmniRip Audio") {
            println!("[OmniRip] Driver successfully loaded! Device ID: {}", id);
            return Ok(());
        }
    }

    Err("Driver installed but OmniRip Audio was not detected within timeout.".into())
}

/// Uninstall OmniRipAudio.driver from /Library/Audio/Plug-Ins/HAL/
pub fn uninstall_driver() -> Result<(), Box<dyn std::error::Error>> {
    let driver_path = "/Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver";
    if !Path::new(driver_path).exists() {
        println!("[OmniRip] Driver is not installed.");
        return Ok(());
    }

    println!("[OmniRip] Removing /Library/Audio/Plug-Ins/HAL/OmniRipAudio.driver...");
    let rm_status = Command::new("sudo")
        .args(["rm", "-rf", driver_path])
        .status()?;

    if !rm_status.success() {
        return Err("Failed to remove driver bundle (sudo failed).".into());
    }

    println!("[OmniRip] Reloading CoreAudio daemon...");
    let _ = Command::new("sudo")
        .args(["killall", "-9", "coreaudiod"])
        .status();

    println!("[OmniRip] Driver uninstalled cleanly.");
    Ok(())
}

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
    fn test_get_default_output_device_id() {
        let dev_id = get_default_output_device_id();
        assert!(dev_id.is_some(), "System must have a default output audio device");
        let id = dev_id.unwrap();
        let name = get_device_name(id);
        assert!(name.is_some(), "Default output device must have a name");
        println!("Default audio device ID {}: {}", id, name.unwrap());
    }
}

/// CLI runner for driver commands
pub fn run_driver_cli(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let sub = args.first().map(|s| s.as_str()).unwrap_or("status");
    match sub {
        "status" => {
            let status = check_status();
            println!("--- OmniRip CoreAudio Driver Status ---");
            println!("Installed on disk: {}", if status.installed { "Yes" } else { "No" });
            println!("Loaded in CoreAudio: {}", if status.loaded { "Yes" } else { "No" });
            if let Some(id) = status.omnirip_device_id {
                println!("OmniRip Device ID: {}", id);
            }
            if let Some(name) = status.current_default_device_name {
                println!("Current macOS Default Output: {}", name);
            }
        }
        "install" => {
            install_driver()?;
        }
        "uninstall" => {
            uninstall_driver()?;
        }
        _ => {
            eprintln!("Usage: omnirip driver [status | install | uninstall]");
            std::process::exit(1);
        }
    }
    Ok(())
}
