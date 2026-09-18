"""Enhancement provider protocol and base types for OmniRip M10."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EnhancementProvider(Protocol):
    """Protocol governing high-frequency audio enhancement providers."""

    @property
    def name(self) -> str:
        """Human-readable name of the enhancement provider."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the provider's dependencies and weights are ready for inference."""
        ...

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
    ) -> np.ndarray:
        """
        Generate the high-frequency residual signal strictly above cutoff_hz.

        Args:
            audio: Audio array of shape (samples,) or (channels, samples).
            sample_rate: Audio sample rate in Hz (standard internal rate: 48000).
            cutoff_hz: The detected compression brickwall cutoff frequency in Hz.

        Returns:
            np.ndarray: Residual audio signal matching the shape and sample rate of input.
            Content below cutoff_hz must be zero or heavily attenuated.
        """
        ...
