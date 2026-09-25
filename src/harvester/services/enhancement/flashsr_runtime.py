"""FlashSR inference runtime: managed code snapshot + lazy pipeline loader.

The upstream redistribution packages badly — its ``setup.py`` uses
``find_packages()`` while the ``FlashSR``/``TorchJaekwon`` subpackages carry no
``__init__.py`` — so pip-installing it yields an unimportable tree. Instead we
snapshot just the inference code from the HF repo (a few MB; the three weight
files are managed separately by ``ModelManager``) and import the pipeline from
that directory.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FLASHSR_REPO = "laion/FlashSR_One-step_Versatile_Audio_Super-resolution"
CODE_DIR_NAME = "flashsr_repo"
_CODE_PATTERNS = ["FlashSR/**", "TorchJaekwon/**"]


@contextlib.contextmanager
def _cpu_safe_torch_load() -> Iterator[None]:
    """Make upstream ``torch.load`` calls CPU-safe while the pipeline loads.

    The upstream code calls ``torch.load(path)`` with no ``map_location`` and
    the checkpoints were saved from CUDA tensors, so loading them on a
    CUDA-less machine raises. The redistribution is trusted code we downloaded
    ourselves, so ``weights_only=False`` is acceptable here.
    """
    import torch

    original = torch.load

    def patched(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("map_location", "cpu")
        kwargs.setdefault("weights_only", False)
        return original(*args, **kwargs)

    torch.load = patched  # type: ignore[assignment]
    try:
        yield
    finally:
        torch.load = original  # type: ignore[assignment]


def flashsr_code_root(cache_dir: Path | None = None) -> Path:
    """Directory that holds the managed FlashSR code snapshot."""
    if cache_dir is None:
        from harvester.services.model_manager import ModelManager

        cache_dir = ModelManager().cache_dir
    return Path(cache_dir) / CODE_DIR_NAME


def ensure_flashsr_code(cache_dir: Path | None = None) -> Path | None:
    """Return the code snapshot root, downloading it once if needed."""
    root = flashsr_code_root(cache_dir)
    if (root / "FlashSR" / "FlashSR.py").exists():
        return root
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=FLASHSR_REPO,
            local_dir=str(root),
            allow_patterns=_CODE_PATTERNS,
        )
    except Exception as exc:
        logger.info("FlashSR code snapshot unavailable (%s); using harmonic engine.", exc)
        return None
    if not (root / "FlashSR" / "FlashSR.py").exists():
        return None
    return root


def load_flashsr_pipeline(
    ldm_path: Path,
    vocoder_path: Path,
    vae_path: Path,
    cache_dir: Path | None = None,
) -> Any | None:
    """Build the upstream FlashSR pipeline; None when code or weights are unavailable."""
    for path in (ldm_path, vocoder_path, vae_path):
        if not path.exists():
            return None
    root = ensure_flashsr_code(cache_dir)
    if root is None:
        return None
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from FlashSR.FlashSR import FlashSR  # type: ignore[import-not-found]
    except Exception as exc:
        logger.info("FlashSR code import failed (%s); using harmonic engine.", exc)
        return None
    with _cpu_safe_torch_load():
        return FlashSR(
            student_ldm_ckpt_path=str(ldm_path),
            sr_vocoder_ckpt_path=str(vocoder_path),
            autoencoder_ckpt_path=str(vae_path),
        )


__all__ = ["FLASHSR_REPO", "ensure_flashsr_code", "flashsr_code_root", "load_flashsr_pipeline"]
