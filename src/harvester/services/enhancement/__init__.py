"""OmniRip M10 Enhancement services."""

from harvester.services.enhancement.conservative_provider import ConservativeDSPProvider
from harvester.services.enhancement.flashsr_provider import FlashSRProvider
from harvester.services.enhancement.hybrid_provider import HybridCoOpProvider
from harvester.services.enhancement.nvsr_provider import NVSRProvider

__all__ = [
    "ConservativeDSPProvider",
    "NVSRProvider",
    "FlashSRProvider",
    "HybridCoOpProvider",
]
