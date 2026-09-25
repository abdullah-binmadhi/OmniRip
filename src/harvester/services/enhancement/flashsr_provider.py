"""FlashSR (Distilled Diffusion Air-Band) provider for OmniRip M10.

Runs the real upstream FlashSR pipeline — student LDM + VAE + SR vocoder, three
weight files managed by ``ModelManager`` — over 5.12 s windows at 48 kHz and
extracts the band above ``max(cutoff_hz, 16 kHz)`` as the residual. When any
weight, the code snapshot, or Torch is unavailable the provider degrades to its
deterministic harmonic air-band generator (never a failed run).
"""

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

# Upstream window: 245,760 samples = 5.12 s at 48 kHz.
WINDOW_SAMPLES: int = 245760
WINDOW_OVERLAP: float = 0.5
MODEL_SAMPLE_RATE: int = 48000
_PIPELINE_PARTS: tuple[str, ...] = ("flashsr_ldm", "flashsr_vae", "flashsr")


def _overlap_add(
    accumulated: np.ndarray, weight: np.ndarray, window: np.ndarray, start: int, fade: int, total: int
) -> None:
    """Equal-power overlap-add of one window into the output buffers (in place)."""
    n = window.shape[1]
    w = np.ones(n, dtype=np.float32)
    if start > 0 and fade > 0:
        f = min(fade, n)
        w[:f] = np.sin(np.linspace(0.0, np.pi / 2.0, f, dtype=np.float32)) ** 2
    if start + n < total and fade > 0:
        f = min(fade, n)
        w[-f:] *= np.cos(np.linspace(0.0, np.pi / 2.0, f, dtype=np.float32)) ** 2
    accumulated[:, start : start + n] += window * w[np.newaxis, :]
    weight[start : start + n] += w


def _resample(audio: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    """Polyphase resample of a (channels, samples) array."""
    from harvester.analysis.enhancement.dsp import resample_audio

    return resample_audio(audio, source_sr, target_sr)


class FlashSRProvider:
    """
    FlashSR single-step distilled diffusion super-resolution provider.

    Reconstructs the ultra-high air band (> max(cutoff, 16 kHz)) from the real
    FlashSR pipeline, strictly rejecting any alterations below the cutoff, with
    an anti-sizzle spectral tilt limit. Falls back to a harmonic air-band
    generator when the model is unavailable.
    """

    def __init__(
        self,
        model_manager: ModelManager | None = None,
        device: str | None = None,
        neural_enabled: bool = True,
    ) -> None:
        self.model_manager = model_manager or ModelManager()
        self._device_str = device
        self.neural_enabled = neural_enabled
        self._pipeline: Any = None
        self._load_failed = False

    @property
    def name(self) -> str:
        return "FlashSR (Air Band)"

    def _paths(self) -> dict[str, Path | None]:
        return {name: self.model_manager.get_model_path(name) for name in _PIPELINE_PARTS}

    @property
    def is_available(self) -> bool:
        if not self.neural_enabled or self._load_failed:
            return False
        try:
            import torch  # noqa: F401
        except ImportError:
            return False
        return all(path is not None and path.exists() for path in self._paths().values())

    def _device(self) -> Any:
        import torch

        if self._device_str:
            return torch.device(self._device_str)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        if self._load_failed:
            return None
        from harvester.services.enhancement.flashsr_runtime import load_flashsr_pipeline

        paths = self._paths()
        pipeline = load_flashsr_pipeline(paths["flashsr_ldm"], paths["flashsr"], paths["flashsr_vae"])
        if pipeline is None:
            self._load_failed = True
            return None
        try:
            pipeline = pipeline.to(self._device()).eval()
        except Exception as exc:
            logger.info("FlashSR could not move to %s (%s); using CPU.", self._device(), exc)
            pipeline = pipeline.to("cpu").eval()
        self._pipeline = pipeline
        logger.info("FlashSR pipeline loaded on %s", next(pipeline.parameters()).device)
        return pipeline

    def _neural_air_band(
        self,
        audio_2d: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
        progress_callback: Callable[[float, str], None] | None,
    ) -> np.ndarray | None:
        """Full-band SR through the real pipeline; returns the band > cutoff."""
        import torch

        pipeline = self._load_pipeline()
        if pipeline is None:
            return None

        if progress_callback:
            progress_callback(45.0, "⚡ [FlashSR Diffusion]: Loading distilled LDM + VAE + vocoder...")

        hr = _resample(audio_2d, sample_rate, MODEL_SAMPLE_RATE)
        total = hr.shape[1]
        windows = []
        if total <= WINDOW_SAMPLES:
            windows.append((0, total))
        else:
            hop = max(1, int(round(WINDOW_SAMPLES * (1.0 - WINDOW_OVERLAP))))
            start = 0
            while start < total:
                end = min(total, start + WINDOW_SAMPLES)
                windows.append((start, end))
                if end >= total:
                    break
                start += hop

        fade = int(round(WINDOW_SAMPLES * WINDOW_OVERLAP))
        accumulated = np.zeros_like(hr, dtype=np.float32)
        weight = np.zeros(total, dtype=np.float32)
        device = next(pipeline.parameters()).device

        with torch.inference_mode():
            for idx, (start, end) in enumerate(windows):
                if progress_callback and len(windows) > 1:
                    pct = 46.0 + 6.0 * (idx / len(windows))
                    progress_callback(pct, f"⚡ [FlashSR Diffusion]: window {idx + 1}/{len(windows)}...")
                chunk = hr[:, start:end]
                n = chunk.shape[1]
                out_ch = np.empty_like(chunk)
                for ch in range(chunk.shape[0]):
                    tensor = torch.from_numpy(np.ascontiguousarray(chunk[ch : ch + 1])).to(device)
                    if n < WINDOW_SAMPLES:
                        tensor = torch.nn.functional.pad(tensor, (0, WINDOW_SAMPLES - n))
                    result = pipeline(tensor, lowpass_input=False)
                    out_ch[ch] = result[0, :n].float().cpu().numpy()
                    del tensor, result
                _overlap_add(accumulated, weight, out_ch, start, fade, total)

        weight = np.maximum(weight, 1e-6)
        full_band = accumulated / weight[np.newaxis, :]

        _, air_band = split_bands(full_band, cutoff_hz=cutoff_hz, sample_rate=MODEL_SAMPLE_RATE)
        return _resample(air_band, MODEL_SAMPLE_RATE, sample_rate)

    def _harmonic_air_band(
        self,
        audio_2d: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
        progress_callback: Callable[[float, str], None] | None,
    ) -> np.ndarray:
        if progress_callback:
            progress_callback(
                47.0,
                "⚡ [FlashSR Engine]: Synthesizing ultrasonic air excitation on GPU (MPS)...",
            )
        f_source_low = max(cutoff_hz * 0.6, 10000.0)
        _, source_band = split_bands(audio_2d, cutoff_hz=f_source_low, sample_rate=sample_rate)
        sub_cutoff, _ = split_bands(source_band, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

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
                energy_env = torch.mean(x**2, dim=0, keepdim=True)
                noise_gate = torch.clamp((energy_env - 1e-5) / (2e-4 + 1e-6), 0.0, 1.0)
                air_harmonics_t = (
                    (
                        0.30 * (x**2)
                        + 0.25 * (x**3)
                        + 0.20 * (torch.abs(x) - torch.mean(torch.abs(x), dim=-1, keepdim=True))
                        + 0.15 * (torch.tanh(2.0 * x) - x)
                    )
                    * noise_gate
                    * norm
                )
                air_harmonics = air_harmonics_t.cpu().numpy().astype(np.float32)
            del t_sub, air_harmonics_t
            if device.type == "mps" and hasattr(torch, "mps"):
                torch.mps.empty_cache()
            elif device.type == "cuda" and hasattr(torch, "cuda"):
                torch.cuda.empty_cache()
        except Exception:
            norm = float(np.max(np.abs(sub_cutoff))) + 1e-6
            x = sub_cutoff / norm
            energy_env_np = np.mean(x**2, axis=0, keepdims=True)
            noise_gate_np = np.clip((energy_env_np - 1e-5) / (2e-4 + 1e-6), 0.0, 1.0)
            air_harmonics = (
                (
                    0.30 * (x**2)
                    + 0.25 * (x**3)
                    + 0.20 * (np.abs(x) - np.mean(np.abs(x), axis=-1, keepdims=True))
                    + 0.15 * (np.tanh(2.0 * x) - x)
                )
                * noise_gate_np
                * norm
            )

        if progress_callback:
            progress_callback(51.0, "⚡ [FlashSR Engine]: Filtering ultrasonic air passband...")
        _, air_residual = split_bands(
            air_harmonics, cutoff_hz=cutoff_hz, sample_rate=sample_rate
        )
        return air_residual

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> np.ndarray:
        """
        Generate ultra-high air-band residual (> max(cutoff_hz, 16 kHz)).
        """
        audio_2d, was_1d = ensure_2d_audio(audio)
        effective_cutoff = max(cutoff_hz, 16000.0)

        if progress_callback:
            progress_callback(44.0, "⚡ [FlashSR Core]: Ingesting audio for ultrasonic air band...")

        air_residual = None
        if self.is_available:
            try:
                air_residual = self._neural_air_band(
                    audio_2d, sample_rate, effective_cutoff, progress_callback
                )
                if air_residual is not None and float(np.sqrt(np.mean(air_residual**2))) <= 1e-4:
                    air_residual = None
            except Exception as exc:
                logger.warning(
                    "FlashSR pipeline inference failed (%s); using air harmonic generator",
                    exc,
                )
                self._load_failed = True
                air_residual = None

        if air_residual is None:
            air_residual = self._harmonic_air_band(
                audio_2d, sample_rate, effective_cutoff, progress_callback
            )
        else:
            if progress_callback:
                progress_callback(
                    51.0, "⚡ [FlashSR Diffusion]: Isolating ultrasonic air band (>16kHz)..."
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
