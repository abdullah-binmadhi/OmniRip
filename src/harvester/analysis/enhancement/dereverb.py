"""Neural de-reverb for the vocal stem (anvuew/dereverb_bs_roformer).

Runs the vendored MSST BS-RoFormer architecture (GPL-3.0, ``harvester.vendor.msst``)
over the isolated vocal stem in overlapping chunks and returns the dry (anechoic)
vocal. Falls back to the spectral engine in ``stem_separator._apply_dereverb_isolation``
when the checkpoint, Torch, or the vendored deps are unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Architecture of anvuew/dereverb_bs_roformer (config.yaml, model section).
DEREVERB_CONFIG: dict[str, Any] = {
    "dim": 256,
    "depth": 12,
    "stereo": True,
    "num_stems": 1,
    "time_transformer_depth": 1,
    "freq_transformer_depth": 1,
    "linear_transformer_depth": 0,
    "freqs_per_bands": (
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        4,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        12,
        24,
        24,
        24,
        24,
        24,
        24,
        24,
        24,
        48,
        48,
        48,
        48,
        48,
        48,
        48,
        48,
        128,
        129,
    ),
    "dim_head": 64,
    "heads": 8,
    "attn_dropout": 0.0,
    "ff_dropout": 0.0,
    # Flash-attention kernels are CUDA-only; the vendored Attend falls back to
    # plain attention, so keep the flag off to avoid the optional import.
    "flash_attn": False,
    "dim_freqs_in": 1025,
    "stft_n_fft": 2048,
    "stft_hop_length": 512,
    "stft_win_length": 2048,
    "stft_normalized": False,
    "mask_estimator_depth": 2,
    "mlp_expansion_factor": 4,
    "use_torch_checkpoint": False,
    "skip_connection": False,
}

# anvuew config.yaml audio section: ~10.2 s windows at 44.1 kHz, 2x overlap.
CHUNK_SAMPLES: int = 448000
CHUNK_OVERLAP: float = 0.5


def chunk_windows(total: int, chunk: int = CHUNK_SAMPLES, overlap: float = CHUNK_OVERLAP) -> list[tuple[int, int]]:
    """Sample windows covering ``total`` with the given fractional overlap."""
    if total <= chunk:
        return [(0, total)]
    hop = max(1, int(round(chunk * (1.0 - overlap))))
    windows = []
    start = 0
    while start < total:
        end = min(total, start + chunk)
        windows.append((start, end))
        if end >= total:
            break
        start += hop
    return windows


def _crossfade_merge(
    accumulated: np.ndarray,
    weight: np.ndarray,
    window: np.ndarray,
    start: int,
    fade: int,
    total: int,
) -> None:
    """Equal-power overlap-add of one chunk into the output buffers (in place)."""
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


class NeuralDereverb:
    """Lazy chunked BS-RoFormer de-reverb over a vocal stem."""

    def __init__(self, model_path: Path | None = None, device: str | None = None) -> None:
        if model_path is None:
            from harvester.services.model_manager import ModelManager

            model_path = ModelManager().get_model_path("dereverb")
        self.model_path = model_path
        self._device_str = device
        self._model: Any = None

    @property
    def is_available(self) -> bool:
        if self.model_path is None or not self.model_path.exists():
            return False
        try:
            import torch  # noqa: F401

            from harvester.vendor.msst import BSRoformer  # noqa: F401
        except ImportError:
            return False
        return True

    def _device(self) -> Any:
        import torch

        if self._device_str:
            return torch.device(self._device_str)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        import torch

        from harvester.vendor.msst import BSRoformer

        model = BSRoformer(**DEREVERB_CONFIG)
        state = torch.load(str(self.model_path), map_location="cpu", weights_only=True)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        model.load_state_dict(state)
        model.eval()
        self._model = model.to(self._device())
        logger.info("Neural de-reverb loaded on %s", self._device())
        return self._model

    def enhance(self, audio_2d: np.ndarray, sample_rate: int) -> np.ndarray:
        """Return the dry (anechoic) vocal for a stereo ``(2, n)`` stem."""
        import torch

        model = self._load()
        device = self._device()
        was_mono = audio_2d.shape[0] == 1
        source = np.repeat(audio_2d, 2, axis=0) if was_mono else audio_2d
        n = source.shape[1]

        windows = chunk_windows(n)
        fade = int(round(CHUNK_SAMPLES * CHUNK_OVERLAP))
        accumulated = np.zeros_like(source, dtype=np.float32)
        weight = np.zeros(n, dtype=np.float32)

        for start, end in windows:
            segment = source[:, start:end]
            tensor = torch.from_numpy(np.ascontiguousarray(segment)).unsqueeze(0).to(device)
            with torch.inference_mode():
                out = model(tensor)
            dry = out[0, 0].cpu().numpy().astype(np.float32)
            _crossfade_merge(accumulated, weight, dry, start, fade, n)
            del tensor, out

        weight = np.maximum(weight, 1e-6)
        merged = accumulated / weight[np.newaxis, :]
        return merged[:1] if was_mono else merged


__all__ = ["DEREVERB_CONFIG", "CHUNK_SAMPLES", "CHUNK_OVERLAP", "NeuralDereverb", "chunk_windows"]
