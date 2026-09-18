"""NVSR (Neural Vocoder Super-Resolution) enhancement provider for OmniRip M10."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from harvester.analysis.enhancement.dsp import (
    ensure_2d_audio,
    match_spectral_slope,
    split_bands,
)
from harvester.services.model_manager import ModelManager

logger = logging.getLogger(__name__)


class NVSRProvider:
    """
    NVSR non-diffusion base neural stabilization provider.

    Executes super-resolution inference to reconstruct mid-high frequencies,
    strictly high-passing the output above cutoff_hz to ensure sub-cutoff audio
    is never altered.
    """

    def __init__(
        self,
        model_path: Path | None = None,
        model_manager: ModelManager | None = None,
        device: str | None = None,
    ) -> None:
        self.model_manager = model_manager or ModelManager()
        self.model_path = model_path or self.model_manager.get_model_path("nvsr")
        self._model: Any = None
        self._device_str = device
        self._torch: Any = None

    @property
    def name(self) -> str:
        return "NVSR (Fast Neural)"

    @property
    def is_available(self) -> bool:
        """True if torch is installed and weights are cached."""
        try:
            import torch
            self._torch = torch
            return self.model_path is not None and self.model_path.exists()
        except ImportError:
            return False

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        import torch

        if self.model_path is None or not self.model_path.exists():
            raise RuntimeError(f"NVSR model weights not found at {self.model_path}")

        # Choose accelerator: MPS on Apple Silicon, else CPU
        if self._device_str is None:
            if torch.backends.mps.is_available():
                device = torch.device("mps")
            else:
                device = torch.device("cpu")
        else:
            device = torch.device(self._device_str)

        logger.info("Loading NVSR model on device %s from %s", device, self.model_path)
        try:
            model = torch.jit.load(str(self.model_path), map_location=device)
            model.eval()
            self._model = model
            return self._model
        except Exception as e:
            logger.error("Failed to load NVSR torchscript model: %s", e)
            raise RuntimeError(f"Failed to load NVSR weights: {e}") from e

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
    ) -> np.ndarray:
        """
        Generate high-frequency residual using NVSR, isolating strictly the band > cutoff_hz.
        """
        audio_2d, was_1d = ensure_2d_audio(audio)

        # Run model inference if available, otherwise perform high-order fallback
        raw_sr_output = self._run_inference(audio_2d, sample_rate)

        # STRICT GUARANTEE: Split bands to extract ONLY content above cutoff_hz
        _, residual = split_bands(raw_sr_output, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

        # Scale residual to respect source spectral decay
        scaled = match_spectral_slope(
            source_audio=audio_2d,
            residual_audio=residual,
            cutoff_hz=cutoff_hz,
            sample_rate=sample_rate,
            target_decay_db_per_oct=4.5,
        )

        return scaled[0] if was_1d else scaled

    def _run_inference(self, audio_2d: np.ndarray, sample_rate: int) -> np.ndarray:
        """Internal inference wrapper."""
        if not self.is_available:
            # When model is not loaded (e.g. testing or missing torch), generate synthetic upper band
            f_mid = sample_rate / 4.0
            _, high = split_bands(audio_2d, cutoff_hz=f_mid, sample_rate=sample_rate)
            return (high * 0.8).astype(np.float32)

        import torch

        model = self._load_model()
        device = next(model.parameters()).device if hasattr(model, "parameters") else torch.device("cpu")

        with torch.no_grad():
            tensor = torch.from_numpy(audio_2d).unsqueeze(0).to(device)
            out_tensor = model(tensor)
            if isinstance(out_tensor, tuple):
                out_tensor = out_tensor[0]
            output = out_tensor.squeeze(0).cpu().numpy().astype(np.float32)
            return output
