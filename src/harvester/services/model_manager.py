"""Model management and checkpoint downloading service for OmniRip M10."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
    direct_url: str | None = None


# Default registry of supported models
SUPPORTED_MODELS: dict[str, ModelSpec] = {
    # FlashSR is a three-file pipeline (docs/10, M10): the distilled latent
    # diffusion model, the VAE, and the SR vocoder. All three are required for
    # a real FlashSR pass; the provider degrades to its harmonic engine when
    # any file is missing.
    "flashsr_ldm": ModelSpec(
        name="flashsr_ldm",
        repo_id="laion/FlashSR_One-step_Versatile_Audio_Super-resolution",
        filename="weights/student_ldm.pth",
        target_sample_rate=48000,
        expected_sha256=None,
        description="FlashSR distilled latent diffusion model (one-step, 48kHz)",
    ),
    "flashsr_vae": ModelSpec(
        name="flashsr_vae",
        repo_id="laion/FlashSR_One-step_Versatile_Audio_Super-resolution",
        filename="weights/vae.pth",
        target_sample_rate=48000,
        expected_sha256=None,
        description="FlashSR variational autoencoder (mel/latent front-end, 48kHz)",
    ),
    "flashsr": ModelSpec(
        name="flashsr",
        repo_id="laion/FlashSR_One-step_Versatile_Audio_Super-resolution",
        filename="weights/sr_vocoder.pth",
        target_sample_rate=48000,
        expected_sha256=None,
        description="FlashSR super-resolution vocoder (latent -> 48kHz waveform)",
    ),
    "bs_roformer": ModelSpec(
        name="bs_roformer",
        repo_id="HiDolen/Mini-BS-RoFormer-V2-46.8M",
        filename="model.safetensors",
        target_sample_rate=44100,
        expected_sha256=None,
        description="BS-RoFormer Rotary Transformer vocal separation (44.1kHz)",
    ),
    "hdemucs": ModelSpec(
        name="hdemucs",
        repo_id="facebookresearch/demucs",
        filename="hdemucs_high_musdbhq_only.pt",
        target_sample_rate=44100,
        expected_sha256=None,
        description="HDEMUCS deep multi-source rhythm & instrument separation (44.1kHz)",
        direct_url="https://download.pytorch.org/torchaudio/models/hdemucs_high_musdbhq_only.pt",
    ),
    "htdemucs_6s": ModelSpec(
        name="htdemucs_6s",
        repo_id="adefossez/HTDemucs-6s",
        filename="5c90dfd2.safetensors",
        target_sample_rate=44100,
        expected_sha256=None,
        description="HTDemucs 6-source extras — guitar + piano lanes (44.1kHz)",
    ),
    "dereverb": ModelSpec(
        name="dereverb",
        repo_id="anvuew/dereverb_bs_roformer",
        filename="dereverb_bs_roformer_anvuew_sdr_22.5050.ckpt",
        target_sample_rate=44100,
        expected_sha256=None,
        description="BS-RoFormer DeReverb anechoic vocal acoustic isolation (44.1kHz)",
    ),
    # Repo-based model: the filename carries the snapshot directory so the
    # single-file downloader and the CLAP loader agree on one location
    # (``<cache>/clap-htsat-unfused/``).
    "clap": ModelSpec(
        name="clap",
        repo_id="laion/clap-htsat-unfused",
        filename="clap-htsat-unfused/pytorch_model.bin",
        target_sample_rate=48000,
        expected_sha256=None,
        description="CLAP audio-text tagger — advisory instrument/vocal labels (48kHz)",
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
        if model_name.lower() == "hdemucs":
            try:
                import torch

                hub_p = Path(torch.hub.get_dir())
                for cand in [
                    hub_p / "torchaudio" / "models" / spec.filename,
                    hub_p / "checkpoints" / spec.filename,
                    hub_p / spec.filename,
                ]:
                    if cand.exists() and cand.is_file():
                        return cand
            except Exception:
                pass
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
            model_name: Name of supported model ('flashsr', 'flashsr_ldm', 'flashsr_vae',
                'bs_roformer', 'hdemucs', 'htdemucs_6s', 'dereverb', 'clap').
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
            models_list = list(SUPPORTED_MODELS.keys())
            raise KeyError(f"Unknown model '{model_name}'. Supported: {models_list}")

        spec = SUPPORTED_MODELS[key]
        dest_path = self.cache_dir / spec.filename

        cached_existing = self.get_model_path(key)
        if cached_existing and not force_download:
            if spec.expected_sha256:
                if self.verify_checksum(cached_existing, spec.expected_sha256):
                    if progress_callback:
                        progress_callback(1.0)
                    return cached_existing
                logger.warning("Cached model checksum failed; re-downloading %s", spec.name)
            else:
                if progress_callback:
                    progress_callback(1.0)
                return cached_existing

        if key == "hdemucs":
            try:
                import torchaudio
                import torchaudio.utils

                logger.info("Downloading HDEMUCS pipeline weights via torchaudio...")
                if progress_callback:
                    progress_callback(0.2)
                bundle = torchaudio.pipelines.HDEMUCS_HIGH_MUSDB
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                downloaded_file = torchaudio.utils._download_asset(
                    bundle._model_path,
                    path=dest_path,
                )
                if progress_callback:
                    progress_callback(1.0)
                return Path(downloaded_file)
            except Exception as e:
                logger.info(
                    "Torchaudio bundle download failed (%s); falling back to direct HTTP...", e
                )
                if spec.direct_url:
                    return self._download_direct_http(spec, progress_callback=progress_callback)
                raise RuntimeError(f"Failed to download HDEMUCS via torchaudio: {e}") from e

        try:
            from huggingface_hub import hf_hub_download

            logger.info("Downloading %s using huggingface_hub (%s)...", spec.name, spec.repo_id)
            if progress_callback:
                progress_callback(0.1)
            downloaded = hf_hub_download(
                repo_id=spec.repo_id,
                filename=spec.filename,
                local_dir=str(self.cache_dir),
            )
            downloaded_path = Path(downloaded)
            if spec.expected_sha256:
                if not self.verify_checksum(downloaded_path, spec.expected_sha256):
                    downloaded_path.unlink(missing_ok=True)
                    raise RuntimeError(f"Checksum verification failed for {spec.name}")
            if progress_callback:
                progress_callback(1.0)
            return downloaded_path
        except ImportError:
            logger.info("huggingface_hub not installed; using direct HTTP streaming download...")
            return self._download_direct_http(spec, progress_callback=progress_callback)
        except Exception as e:
            logger.error("Failed to download model %s: %s", spec.name, e)
            raise RuntimeError(f"Failed to download model '{spec.name}': {e}") from e

    def _download_direct_http(
        self,
        spec: ModelSpec,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Download model checkpoint directly via streaming HTTP GET."""
        import httpx

        if spec.direct_url:
            url = spec.direct_url
        else:
            url = f"https://huggingface.co/{spec.repo_id}/resolve/main/{spec.filename}"
        dest_path = self.cache_dir / spec.filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

        logger.info("Downloading %s via direct HTTP from %s", spec.name, url)
        if progress_callback:
            progress_callback(0.05)

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", 0))
                downloaded_bytes = 0

                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=1048576):  # 1 MB chunks
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        if total_bytes > 0 and progress_callback:
                            progress_callback(min(0.99, downloaded_bytes / total_bytes))

            if spec.expected_sha256:
                if not self.verify_checksum(temp_path, spec.expected_sha256):
                    temp_path.unlink(missing_ok=True)
                    raise RuntimeError(f"Checksum verification failed for {spec.name}")

            temp_path.replace(dest_path)
            if progress_callback:
                progress_callback(1.0)
            return dest_path
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            logger.error("Direct HTTP download failed for %s: %s", spec.name, e)
            raise RuntimeError(f"Failed to download model '{spec.name}': {e}") from e
