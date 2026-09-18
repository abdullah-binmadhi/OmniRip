"""Deterministic Enhancement Presets for OmniRip M10."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnhancementPreset:
    """Configuration preset for audio enhancement rendering."""

    id: str
    name: str
    description: str
    provider_type: str  # "conservative", "nvsr", "flashsr", "hybrid"
    residual_gain_db: float = 0.0
    target_decay_db_per_oct: float = 4.5
    residual_stereo_width: float = 1.0  # 1.0 = normal stereo, 0.7 = narrowed
    progressive_mono: bool = True
    ceiling_dbfs: float = -0.1


PRESETS: dict[str, EnhancementPreset] = {
    "conservative": EnhancementPreset(
        id="conservative",
        name="Conservative DSP",
        description="Subtle non-neural harmonic excitation (zero AI hallucination).",
        provider_type="conservative",
        residual_gain_db=0.0,
        target_decay_db_per_oct=5.0,
        residual_stereo_width=1.0,
    ),
    "fast_balanced": EnhancementPreset(
        id="fast_balanced",
        name="Fast Neural (Balanced)",
        description="NVSR non-diffusion residual with natural spectral decay tracking.",
        provider_type="nvsr",
        residual_gain_db=0.0,
        target_decay_db_per_oct=4.5,
        residual_stereo_width=1.0,
    ),
    "de_sizzle": EnhancementPreset(
        id="de_sizzle",
        name="Milder Highs (De-Sizzle)",
        description="Attenuated high residual (-2.5 dB) with steep roll-off for harsh recordings.",
        provider_type="nvsr",
        residual_gain_db=-2.5,
        target_decay_db_per_oct=6.0,
        residual_stereo_width=0.85,
    ),
    "extended_air": EnhancementPreset(
        id="extended_air",
        name="Extended Air (Hybrid)",
        description="NVSR mid-highs with FlashSR ultra-high air band (>16 kHz).",
        provider_type="hybrid",
        residual_gain_db=0.8,
        target_decay_db_per_oct=4.0,
        residual_stereo_width=1.0,
    ),
    "narrow_stereo": EnhancementPreset(
        id="narrow_stereo",
        name="Narrow Residual (Headphone Safe)",
        description="Reduced stereo width (65%) on synthetic frequencies to prevent flutter.",
        provider_type="nvsr",
        residual_gain_db=0.0,
        target_decay_db_per_oct=4.5,
        residual_stereo_width=0.65,
    ),
}

DEFAULT_PRESET = PRESETS["conservative"]
