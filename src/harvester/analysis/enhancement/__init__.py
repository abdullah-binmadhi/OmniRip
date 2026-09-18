"""OmniRip M10 Enhancement and High-Frequency Reconstruction module."""

from __future__ import annotations

import importlib.util
from harvester.analysis.enhancement.provider import EnhancementProvider

__all__ = [
    "EnhancementProvider",
    "check_enhancement_available",
]


def check_enhancement_available() -> tuple[bool, str]:
    """
    Check if the optional neural restoration dependencies are installed.

    Returns:
        tuple[bool, str]: (is_available, status_message)
    """
    missing = []
    for pkg in ("torch", "torchaudio", "huggingface_hub"):
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)

    if missing:
        msg = (
            f"Optional neural restoration dependencies missing: {', '.join(missing)}. "
            "Install with: pip install 'omnirip[restore]'"
        )
        return False, msg

    return True, "Neural restoration dependencies available."
