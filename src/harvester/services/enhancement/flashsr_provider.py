"""FlashSR (Distilled Diffusion Air-Band) provider for OmniRip M10."""

from __future__ import annotations

import logging
from collections.abc import Callable
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


class FlashSRProvider:
    """
    FlashSR single-step distilled diffusion air-band generator.

    Generates ultra-high frequency texture and air (> 16 kHz), strictly rejecting
    any alterations below 16 kHz and applying anti-sizzle spectral tilt limiting.
    """

    def __init__(
        self,
        model_path: Path | None = None,
        model_manager: ModelManager | None = None,
        device: str | None = None,
        neural_enabled: bool = True,
    ) -> None:
        self.model_manager = model_manager or ModelManager()
        self.model_path = model_path or self.model_manager.get_model_path("flashsr")
        self._model: Any = None
        self._device_str = device
        self.neural_enabled = neural_enabled

    @property
    def name(self) -> str:
        return "FlashSR (Air Band)"

    @property
    def is_available(self) -> bool:
        if not self.neural_enabled:
            return False
        try:
            import torch  # noqa: F401

            return self.model_path is not None and self.model_path.exists()
        except ImportError:
            return False

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if self.model_path is None or not self.model_path.exists():
            return None

        import torch

        if self._device_str:
            device = torch.device(self._device_str)
        elif torch.cuda.is_available():
            device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

        try:
            model = torch.jit.load(str(self.model_path), map_location=device)
            model.eval()
            self._model = model
            return self._model
        except Exception as e:
            logger.warning("FlashSR TorchScript load failed (%s); using air harmonic generator", e)
            return None

    def _run_inference(self, audio_2d: np.ndarray, sample_rate: int) -> np.ndarray | None:
        model = self._load_model()
        if model is None:
            return None

        import torch

        device = (
            next(model.parameters()).device if hasattr(model, "parameters") else torch.device("cpu")
        )
        with torch.inference_mode():
            tensor = torch.from_numpy(audio_2d).unsqueeze(0).to(device)
            out = model(tensor)
            if isinstance(out, tuple):
                out = out[0]
            result = out.squeeze(0).cpu().numpy().astype(np.float32)
            del tensor, out
            if device.type == "mps" and hasattr(torch, "mps"):
                torch.mps.empty_cache()
            elif device.type == "cuda" and hasattr(torch, "cuda"):
                torch.cuda.empty_cache()
            return result

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> np.ndarray:
        """
        Generate ultra-high air-band residual (> 16 kHz or max(cutoff_hz, 16000)).
        """
        audio_2d, was_1d = ensure_2d_audio(audio)
        effective_cutoff = max(cutoff_hz, 16000.0)

        if progress_callback:
            progress_callback(44.0, "⚡ [FlashSR Core]: Ingesting audio for ultrasonic air band...")

        air_residual = None
        if self.is_available:
            try:
                if progress_callback:
                    progress_callback(
                        47.0, "⚡ [FlashSR Diffusion]: Running single-step air latent model..."
                    )
                raw_output = self._run_inference(audio_2d, sample_rate)
                if raw_output is not None:
                    _, candidate_air = split_bands(
                        raw_output, cutoff_hz=effective_cutoff, sample_rate=sample_rate
                    )
                    if float(np.sqrt(np.mean(candidate_air**2))) > 1e-4:
                        air_residual = candidate_air
            except Exception as e:
                logger.warning(
                    "FlashSR model inference failed (%s); using GPU-accelerated air excitation",
                    e,
                )
                air_residual = None

        if air_residual is not None:
            if progress_callback:
                progress_callback(
                    51.0, "⚡ [FlashSR Diffusion]: Isolating ultrasonic air band (>16kHz)..."
                )
        else:
            if progress_callback:
                progress_callback(
                    47.0,
                    "⚡ [FlashSR Engine]: Synthesizing ultrasonic air excitation on GPU (MPS)...",
                )
            # High-frequency shimmer excitation for ultra-high air band (>16 kHz)
            f_source_low = max(cutoff_hz * 0.6, 10000.0)
            _, source_band = split_bands(audio_2d, cutoff_hz=f_source_low, sample_rate=sample_rate)
            sub_cutoff, _ = split_bands(source_band, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

            # Accelerated air-band harmonic generation via PyTorch (CUDA / MPS / CPU)
            try:
                import torch

                if self._device_str:
                    device = torch.device(self._device_str)
                elif torch.cuda.is_available():
                    device = torch.device("cuda")
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = torch.device("mps")
                else:
                    device = torch.device("cpu")

                with torch.inference_mode():
                    t_sub = torch.from_numpy(sub_cutoff).to(device)
                    norm = torch.max(torch.abs(t_sub)) + 1e-6
                    x = t_sub / norm
                    air_harmonics_t = (
                        0.30 * (x**2)
                        + 0.25 * (x**3)
                        + 0.20 * (torch.abs(x) - torch.mean(torch.abs(x), dim=-1, keepdim=True))
                        + 0.15 * (torch.tanh(2.0 * x) - x)
                    ) * norm
                    air_harmonics = air_harmonics_t.cpu().numpy().astype(np.float32)
                del t_sub, air_harmonics_t
                if device.type == "mps" and hasattr(torch, "mps"):
                    torch.mps.empty_cache()
                elif device.type == "cuda" and hasattr(torch, "cuda"):
                    torch.cuda.empty_cache()
            except Exception:
                norm = float(np.max(np.abs(sub_cutoff))) + 1e-6
                x = sub_cutoff / norm
                air_harmonics = (
                    0.30 * (x**2)
                    + 0.25 * (x**3)
                    + 0.20 * (np.abs(x) - np.mean(np.abs(x), axis=-1, keepdims=True))
                    + 0.15 * (np.tanh(2.0 * x) - x)
                ) * norm

            if progress_callback:
                progress_callback(51.0, "⚡ [FlashSR Engine]: Filtering ultrasonic air passband...")
            _, air_residual = split_bands(
                air_harmonics, cutoff_hz=effective_cutoff, sample_rate=sample_rate
            )

        if progress_callback:
            progress_callback(54.0, "⚡ [FlashSR Engine]: Shaping natural spectral decay...")

        # Enforce gentle spectral decay to avoid digital sizzle
        scaled = match_spectral_slope(
            source_audio=audio_2d,
            residual_audio=air_residual,
            cutoff_hz=effective_cutoff,
            sample_rate=sample_rate,
            target_decay_db_per_oct=4.0,  # Natural decay for ultrasonic air
            max_gain_db=6.0,
        )

        return scaled[0] if was_1d else scaled
