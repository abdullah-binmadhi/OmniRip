"""Deterministic Conservative DSP Provider for OmniRip M10.

Generates synthetic high-frequency harmonics using pure NumPy non-linear
harmonic excitation. Zero external neural dependencies required.
"""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.dsp import (
    ensure_2d_audio,
    match_spectral_slope,
    split_bands,
)


class ConservativeDSPProvider:
    """Non-neural harmonic exciter providing subtle, mathematically bounded high-end restoration."""

    @property
    def name(self) -> str:
        return "Conservative DSP"

    @property
    def is_available(self) -> bool:
        return True

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
    ) -> np.ndarray:
        """
        Generate high-frequency residual harmonics based on the top octave of the source audio.

        Args:
            audio: Input audio array.
            sample_rate: Sampling rate (typically 48000).
            cutoff_hz: Brickwall cutoff frequency in Hz.

        Returns:
            np.ndarray: Residual audio containing only energy above cutoff_hz.
        """
        audio_2d, was_1d = ensure_2d_audio(audio)

        # 1. Isolate top octave [cutoff_hz / 2, cutoff_hz]
        f_mid = cutoff_hz / 2.0
        _, top_band = split_bands(audio_2d, cutoff_hz=f_mid, sample_rate=sample_rate)
        top_octave, _ = split_bands(top_band, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

        # 2. Generate even and odd harmonics via subtle polynomial saturation
        # x_harm = 0.4 * x^2 + 0.1 * x^3 (creates 2nd and 3rd harmonics above cutoff)
        norm_factor = np.max(np.abs(top_octave)) + 1e-6
        normalized = top_octave / norm_factor
        harmonics = (0.35 * (normalized**2) + 0.15 * (normalized**3)) * norm_factor

        # 3. High-pass filter strictly above cutoff_hz to ensure sub-cutoff is empty
        _, high_residual = split_bands(harmonics, cutoff_hz=cutoff_hz, sample_rate=sample_rate)

        # 4. Scale residual to follow natural spectral decay
        scaled = match_spectral_slope(
            source_audio=audio_2d,
            residual_audio=high_residual,
            cutoff_hz=cutoff_hz,
            sample_rate=sample_rate,
            target_decay_db_per_oct=5.0,
            max_gain_db=2.0,
        )

        return scaled[0] if was_1d else scaled
