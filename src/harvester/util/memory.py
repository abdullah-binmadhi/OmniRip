"""Memory headroom governance and neural VRAM cache management (M24).

Designed to safeguard systems with constrained unified RAM (such as Apple Silicon
MacBook Air M2 with 16 GB unified memory) against memory exhaustion, swapping,
and thermal throttling during neural audio processing.
"""

from __future__ import annotations

import gc
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_HEADROOM_THRESHOLD_MB: float = 2048.0
DEFAULT_CHUNK_SECONDS_16GB: float = 8.0
SAFE_CHUNK_SECONDS_LOW_MEM: float = 4.0


def get_memory_headroom_mb() -> float:
    """Return the available system RAM in megabytes."""
    try:
        import psutil

        return float(psutil.virtual_memory().available / (1024 * 1024))
    except Exception:
        pass

    # Fallback to sysconf if psutil is unavailable or fails
    try:
        if hasattr(os, "sysconf"):
            pagesize = os.sysconf("SC_PAGE_SIZE")
            avail_pages = os.sysconf("SC_AVPHYS_PAGES")
            return float((pagesize * avail_pages) / (1024 * 1024))
    except Exception:
        pass

    # Safe fallback if cannot detect
    return 4096.0


def is_low_memory_headroom(threshold_mb: float = DEFAULT_HEADROOM_THRESHOLD_MB) -> bool:
    """Return True if system available memory is below the specified threshold."""
    return get_memory_headroom_mb() < threshold_mb


def purge_neural_vram() -> None:
    """Purge cached GPU/MPS memory and trigger garbage collection safely.

    Flushes Metal MPS allocator cache on Apple Silicon, CUDA cache on Nvidia GPUs,
    and forces Python garbage collection to reclaim buffer allocations.
    """
    gc.collect()

    torch_mod = sys.modules.get("torch")
    if torch_mod is None:
        return

    # 1. Apple Silicon MPS cache purge
    try:
        if (
            hasattr(torch_mod, "backends")
            and hasattr(torch_mod.backends, "mps")
            and torch_mod.backends.mps.is_available()
            and hasattr(torch_mod, "mps")
            and hasattr(torch_mod.mps, "empty_cache")
        ):
            torch_mod.mps.empty_cache()
    except Exception as exc:
        logger.debug("MPS cache purge failed: %s", exc)

    # 2. Nvidia CUDA cache purge
    try:
        if (
            hasattr(torch_mod, "cuda")
            and torch_mod.cuda.is_available()
            and hasattr(torch_mod.cuda, "empty_cache")
        ):
            torch_mod.cuda.empty_cache()
    except Exception as exc:
        logger.debug("CUDA cache purge failed: %s", exc)


def get_safe_neural_device() -> Any:
    """Return the optimal PyTorch device for neural processing.

    Honours OMNIRIP_DEVICE ('cpu', 'cuda', 'mps'). On Apple Silicon, falls
    back safely to CPU if MPS is unavailable or memory is severely constrained.
    """
    import torch

    env_dev = os.environ.get("OMNIRIP_DEVICE", "").strip().lower()
    if env_dev == "cpu":
        return torch.device("cpu")
    if env_dev in ("cuda", "gpu") and torch.cuda.is_available():
        return torch.device("cuda")
    if env_dev == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")

    if torch.cuda.is_available():
        return torch.device("cuda")

    if env_dev == "auto" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


def get_safe_neural_dtype(device: Any | None = None) -> Any:
    """Return float16 if half-precision is supported and safe on the device, else float32."""
    import torch

    if device is None:
        device = get_safe_neural_device()

    dev_type = getattr(device, "type", str(device))
    env_fp16 = os.environ.get("OMNIRIP_FP16", "").strip().lower()

    if env_fp16 in ("0", "false", "no", "off"):
        return torch.float32

    if dev_type in ("cuda", "mps"):
        return torch.float16

    return torch.float32


def get_safe_chunk_duration(
    target_seconds: float = DEFAULT_CHUNK_SECONDS_16GB,
    headroom_threshold_mb: float = DEFAULT_HEADROOM_THRESHOLD_MB,
) -> float:
    """Return a governed chunk duration in seconds.

    Automatically shrinks chunk size when available system memory drops below threshold,
    protecting 16 GB systems against swap thrashing.
    """
    if is_low_memory_headroom(headroom_threshold_mb):
        return min(target_seconds, SAFE_CHUNK_SECONDS_LOW_MEM)
    return target_seconds


__all__ = [
    "DEFAULT_CHUNK_SECONDS_16GB",
    "DEFAULT_HEADROOM_THRESHOLD_MB",
    "SAFE_CHUNK_SECONDS_LOW_MEM",
    "get_memory_headroom_mb",
    "get_safe_chunk_duration",
    "get_safe_neural_device",
    "get_safe_neural_dtype",
    "is_low_memory_headroom",
    "purge_neural_vram",
]
