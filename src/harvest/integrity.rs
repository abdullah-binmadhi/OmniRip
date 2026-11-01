//! Checksum and signature checks for downloaded tools and release archives.

use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::Path;

/// SHA-256 of a file, as lowercase hex.
pub fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file =
        std::fs::File::open(path).map_err(|e| format!("Cannot open {}: {}", path.display(), e))?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|e| format!("Cannot read {}: {}", path.display(), e))?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    let digest = hasher.finalize();
    Ok(digest.iter().map(|byte| format!("{:02x}", byte)).collect())
}

/// The digest that `sums` lists for `file_name`. Accepts `sha256sum` output (`<hex>  <name>`) and the
/// binary-mode form (`<hex> *<name>`).
pub fn expected_sha256_for(sums: &str, file_name: &str) -> Option<String> {
    sums.lines().find_map(|line| {
        let (digest, name) = line.trim().split_once(char::is_whitespace)?;
        let name = name.trim_start().trim_start_matches('*');
        let well_formed = digest.len() == 64 && digest.bytes().all(|b| b.is_ascii_hexdigit());
        (well_formed && name == file_name).then(|| digest.to_ascii_lowercase())
    })
}

/// Verifies `data` against a minisign signature made with the private key that matches `public_key`.
/// An empty key is an error, because nothing can be verified without a configured key.
pub fn verify_minisign(data: &[u8], signature: &str, public_key: &str) -> Result<(), String> {
    let key = public_key.trim();
    if key.is_empty() {
        return Err(
            "No update signing key is configured, so the update cannot be verified.".to_string(),
        );
    }
    let public_key = minisign_verify::PublicKey::from_base64(key)
        .map_err(|e| format!("Invalid update signing key: {}", e))?;
    let signature = minisign_verify::Signature::decode(signature)
        .map_err(|e| format!("Invalid signature file: {}", e))?;
    public_key
        .verify(data, &signature, false)
        .map_err(|e| format!("Signature check failed: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    const ABC: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    const EMPTY: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    #[test]
    fn sha256_matches_the_standard_test_vector() {
        let path = std::env::temp_dir().join(format!("omnirip-sha256-{}", std::process::id()));
        std::fs::write(&path, b"abc").expect("write temp file");
        let digest = sha256_file(&path);
        let _ = std::fs::remove_file(&path);
        assert_eq!(digest.expect("hash temp file"), ABC);
    }

    #[test]
    fn finds_hashes_in_both_sha256sum_formats() {
        let sums = format!("{ABC}  archive.tar.gz\n{EMPTY} *binary.zip\n");
        assert_eq!(
            expected_sha256_for(&sums, "archive.tar.gz").as_deref(),
            Some(ABC)
        );
        assert_eq!(
            expected_sha256_for(&sums, "binary.zip").as_deref(),
            Some(EMPTY)
        );
        assert_eq!(expected_sha256_for(&sums, "missing.zip"), None);
    }

    #[test]
    fn rejects_malformed_digests() {
        assert_eq!(
            expected_sha256_for("deadbeef  archive.tar.gz\n", "archive.tar.gz"),
            None
        );
    }

    #[test]
    fn an_unconfigured_update_key_never_verifies() {
        let err = verify_minisign(b"sums", "signature", "").unwrap_err();
        assert!(err.contains("No update signing key"));
    }

    #[test]
    fn a_bogus_signature_is_rejected() {
        assert!(verify_minisign(
            b"sums",
            "not a signature",
            "RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSCh1CBM0QTaLn73Y7GFO3"
        )
        .is_err());
    }
}
