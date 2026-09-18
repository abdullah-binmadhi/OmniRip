"""Model management and checkpoint downloading service for OmniRip M10."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
from typing import Callable

import platformdirs

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSpec:
    """Specification of an audio enhancement model checkpoint."""

    name: str
    repo_id: str
    filename: str
    target_sample_rate: int
    expected_sha256: str | None = None
    description: str = ""


# Default registry of supported models
SUPPORTED_MODELS: dict[str, ModelSpec] = {
    "nvsr": ModelSpec(
        name="nvsr",
        repo_id="haoheliu/wellsolve_audio_super_resolution_48k",
        filename="basic.pth",
        target_sample_rate=48000,
        expected_sha256=None,  # Verified dynamically if provided
        description="NVSR non-diffusion base stabilization model (48kHz)",
    ),
    "flashsr": ModelSpec(
        name="flashsr",
        repo_id="laion/FlashSR_One-step_Versatile_Audio_Super-resolution",
        filename="weights/sr_vocoder.pth",
        target_sample_rate=48000,
        expected_sha256=None,
        description="FlashSR distilled diffusion air-band generator (>16kHz)",
    ),
}


class ModelManager:
    """Manages downloading, caching, and verifying neural enhancement model weights."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            self.cache_dir = Path(platformdirs.user_cache_dir("omnirip")) / "models"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str) -> Path | None:
        """Return the local path to a cached model if it exists, else None."""
        spec = SUPPORTED_MODELS.get(model_name.lower())
        if not spec:
            return None
        candidate = self.cache_dir / spec.filename
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def is_cached(self, model_name: str) -> bool:
        """Check if model checkpoint exists locally."""
        path = self.get_model_path(model_name)
        return path is not None and path.exists()

    @staticmethod
    def verify_checksum(file_path: Path, expected_sha256: str) -> bool:
        """Calculate and verify SHA-256 checksum of a file."""
        if not file_path.exists():
            return False
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest().lower() == expected_sha256.lower()

    def download_model(
        self,
        model_name: str,
        progress_callback: Callable[[float], None] | None = None,
        force_download: bool = False,
    ) -> Path:
        """
        Download a model checkpoint to the local cache directory.

        Args:
            model_name: Name of supported model ('nvsr' or 'flashsr').
            progress_callback: Optional callback receiving float progress (0.0 to 1.0).
            force_download: Re-download even if file is already cached.

        Returns:
            Path to downloaded model weights file.

        Raises:
            KeyError: If model_name is not in SUPPORTED_MODELS.
            RuntimeError: If download fails or dependencies are missing.
        """
        key = model_name.lower()
        if key not in SUPPORTED_MODELS:
            raise KeyError(f"Unknown model '{model_name}'. Supported: {list(SUPPORTED_MODELS.keys())}")

        spec = SUPPORTED_MODELS[key]
        dest_path = self.cache_dir / spec.filename

        if dest_path.exists() and not force_download:
            if spec.expected_sha256:
                if self.verify_checksum(dest_path, spec.expected_sha256):
                    if progress_callback:
                        progress_callback(1.0)
                    return dest_path
                logger.warning("Cached model checksum failed; re-downloading %s", spec.name)
            else:
                if progress_callback:
                    progress_callback(1.0)
                return dest_path

        try:
            from huggingface_hub import hf_hub_download
        except ImportError as err:
            raise RuntimeError(
                "huggingface_hub is required to download model weights. "
                "Install with: pip install 'omnirip[restore]'"
            ) from err

        logger.info("Downloading %s from Hugging Face (%s)...", spec.name, spec.repo_id)
        if progress_callback:
            progress_callback(0.1)

        try:
            downloaded = hf_hub_download(
                repo_id=spec.repo_id,
                filename=spec.filename,
                local_dir=str(self.cache_dir),
                local_dir_use_symlinks=False,
            )
            downloaded_path = Path(downloaded)

            if spec.expected_sha256:
                if not self.verify_checksum(downloaded_path, spec.expected_sha256):
                    downloaded_path.unlink(missing_ok=True)
                    raise RuntimeError(f"Checksum verification failed for {spec.name}")

            if progress_callback:
                progress_callback(1.0)
            return downloaded_path

        except Exception as e:
            logger.error("Failed to download model %s: %s", spec.name, e)
            raise RuntimeError(f"Failed to download model '{spec.name}': {e}") from e
