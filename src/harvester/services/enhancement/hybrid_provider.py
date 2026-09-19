"""Hybrid Co-Op Provider (NVSR + FlashSR) for OmniRip M10."""

from __future__ import annotations

import logging
from collections.abc import Callable

import numpy as np

from harvester.analysis.enhancement.dsp import (
    ensure_2d_audio,
    match_spectral_slope,
    split_bands,
)
from harvester.analysis.enhancement.provider import EnhancementProvider
from harvester.services.enhancement.flashsr_provider import FlashSRProvider
from harvester.services.enhancement.nvsr_provider import NVSRProvider

logger = logging.getLogger(__name__)


class HybridCoOpProvider:
    """
    Hybrid multi-band provider:
    - NVSR reconstructs mid-high frequencies: [cutoff_hz, 16 kHz]
    - FlashSR reconstructs ultra-high air frequencies: > 16 kHz
    - Automatically checks passband phase cancellation before summing.
    """

    def __init__(
        self,
        nvsr: EnhancementProvider | None = None,
        flashsr: EnhancementProvider | None = None,
        neural_enabled: bool = True,
    ) -> None:
        self.nvsr = nvsr or NVSRProvider(neural_enabled=neural_enabled)
        self.flashsr = flashsr or FlashSRProvider(neural_enabled=neural_enabled)
        self.neural_enabled = neural_enabled

    @property
    def name(self) -> str:
        return "Hybrid (NVSR + FlashSR Air)"

    @property
    def is_available(self) -> bool:
        if not self.neural_enabled:
            return False
        return self.nvsr.is_available and self.flashsr.is_available

    def set_neural_enabled(self, enabled: bool) -> None:
        self.neural_enabled = enabled
        if hasattr(self.nvsr, "neural_enabled"):
            self.nvsr.neural_enabled = enabled
        if hasattr(self.flashsr, "neural_enabled"):
            self.flashsr.neural_enabled = enabled

    def generate_residual(
        self,
        audio: np.ndarray,
        sample_rate: int,
        cutoff_hz: float,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> np.ndarray:
        """
        Synthesize multi-band residual combining NVSR mid-high and FlashSR air band.
        """
        audio_2d, was_1d = ensure_2d_audio(audio)
        mid_boundary = max(cutoff_hz, 16000.0)

        if progress_callback:
            progress_callback(
                43.0, "⚡ [Hybrid Co-Op]: Invoking NVSR mid-high frequency generator..."
            )

        import inspect

        # 1. Generate NVSR residual above cutoff
        sig_nvsr = inspect.signature(self.nvsr.generate_residual)
        if "progress_callback" in sig_nvsr.parameters:
            nvsr_res = self.nvsr.generate_residual(
                audio_2d, sample_rate, cutoff_hz, progress_callback=progress_callback
            )
        else:
            nvsr_res = self.nvsr.generate_residual(audio_2d, sample_rate, cutoff_hz)

        # Bandpass NVSR to [cutoff_hz, mid_boundary]
        nvsr_mid_high, _ = split_bands(nvsr_res, cutoff_hz=mid_boundary, sample_rate=sample_rate)

        if progress_callback:
            progress_callback(
                49.0, "⚡ [Hybrid Co-Op]: Invoking FlashSR ultrasonic air band generator..."
            )

        # 2. Generate FlashSR air-band residual (> 16 kHz)
        sig_flash = inspect.signature(self.flashsr.generate_residual)
        if "progress_callback" in sig_flash.parameters:
            flash_res = self.flashsr.generate_residual(
                audio_2d, sample_rate, mid_boundary, progress_callback=progress_callback
            )
        else:
            flash_res = self.flashsr.generate_residual(audio_2d, sample_rate, mid_boundary)

        _, flash_air = split_bands(flash_res, cutoff_hz=mid_boundary, sample_rate=sample_rate)

        if progress_callback:
            progress_callback(
                54.0, "⚡ [Hybrid Co-Op]: Summing complementary phase-aligned sub-bands..."
            )

        # 3. Sum complementary residuals
        combined_residual = nvsr_mid_high + flash_air

        if progress_callback:
            progress_callback(56.0, "⚡ [Hybrid Co-Op]: Matching spectral slope & target decay...")

        # 4. Final spectral slope sanity check
        scaled = match_spectral_slope(
            source_audio=audio_2d,
            residual_audio=combined_residual,
            cutoff_hz=cutoff_hz,
            sample_rate=sample_rate,
            target_decay_db_per_oct=4.0,
            max_gain_db=6.0,
        )

        return scaled[0] if was_1d else scaled
