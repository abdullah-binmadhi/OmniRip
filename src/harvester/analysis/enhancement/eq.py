"""10-Band Studio Equalizer & Mastering Tone Sculptor for OmniRip M10."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Standard ISO 10-band octave frequencies (Hz)
EQ_FREQUENCIES: list[int] = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

EQ_TARGETS: dict[str, str] = {
    "master": "MASTER",
    "vocals": "VOCALS",
    "instrumental": "INSTRUMENTAL",
}

EQ_PRESET_BANKS: dict[str, dict[str, dict[int, float]]] = {
    "master": {
        "Flat": {},
        "Warm": {31: 0.5, 63: 2.0, 125: 1.5, 500: -0.5},
        "Air": {4000: 0.5, 8000: 2.0, 16000: 2.5},
        "Smile": {
            31: 1.0,
            63: 1.5,
            125: 1.0,
            500: -0.5,
            1000: -0.5,
            4000: 0.5,
            8000: 1.5,
            16000: 2.0,
        },
        "De-Box": {125: -1.0, 250: -2.0, 500: -1.0, 2000: 0.5},
        "Soft Highs": {4000: -1.0, 8000: -1.5, 16000: -2.0},
    },
    "vocals": {
        "Natural": {},
        "Presence": {250: -1.0, 1000: 1.0, 2000: 2.0, 4000: 1.0},
        "Warm Body": {125: 1.5, 250: 1.0, 500: -0.5},
        "Air": {4000: 0.5, 8000: 1.5, 16000: 2.0},
        "Tame Sibilance": {4000: 0.5, 8000: -2.0, 16000: -1.0},
        "Intimate": {250: -1.5, 500: -0.5, 2000: 0.5, 4000: 1.5, 8000: 1.0},
    },
    "instrumental": {
        "Natural": {},
        "Punch": {31: 1.0, 63: 1.5, 125: 0.5, 250: -1.0, 2000: 0.5},
        "Clarity": {250: -1.0, 500: -1.0, 2000: 1.5, 4000: 1.0},
        "Sparkle": {4000: 0.5, 8000: 1.5, 16000: 2.0},
        "Tight Sub": {31: -2.0, 63: -1.0, 125: 0.5},
    },
}

DEFAULT_EQ_PRESET: dict[str, str] = {
    "master": "Flat",
    "vocals": "Natural",
    "instrumental": "Natural",
}

EQ_PRESETS: dict[str, dict[int, float]] = EQ_PRESET_BANKS["master"]


def eq_bank(target: str) -> dict[str, dict[int, float]]:
    """Preset bank for a target (falls back to the master bank)."""
    return EQ_PRESET_BANKS.get(target, EQ_PRESETS)


@dataclass
class MasteringEQSettings:
    """Settings state for the 10-Band Studio Equalizer."""

    bands: dict[int, float] = field(default_factory=lambda: {f: 0.0 for f in EQ_FREQUENCIES})
    enabled: bool = True
    hpf_30hz: bool = False
    output_trim_db: float = 0.0
    preset_name: str = "Flat"

    def set_band(self, freq: int, gain_db: float) -> None:
        """Set gain in dB for a specific band (-12dB to +12dB)."""
        if freq in self.bands:
            self.bands[freq] = float(np.clip(gain_db, -12.0, 12.0))
            self.preset_name = "Custom"

    def apply_preset(self, name: str, bank: dict[str, dict[int, float]] | None = None) -> bool:
        """Apply a named preset from ``bank`` (default: the master bank)."""
        presets = EQ_PRESETS if bank is None else bank
        if name not in presets:
            return False
        self.bands = {f: float(presets[name].get(f, 0.0)) for f in EQ_FREQUENCIES}
        self.preset_name = name
        return True

    def reset_flat(self) -> None:
        """Reset all bands to 0.0 dB flat and clear HPF / Trim / Bypass."""
        self.bands = {f: 0.0 for f in EQ_FREQUENCIES}
        self.preset_name = "Flat"
        self.output_trim_db = 0.0
        self.hpf_30hz = False
        self.enabled = True

    def cache_tag(self) -> str:
        """Short deterministic tag of this curve for cache names ("" when flat)."""
        if is_flat(self):
            return ""
        import hashlib

        band_str = "_".join(f"{f}:{self.bands.get(f, 0.0):.1f}" for f in EQ_FREQUENCIES)
        key = f"{band_str}_{self.hpf_30hz}_{self.output_trim_db}_{self.enabled}"
        return f"_eq_{hashlib.md5(key.encode()).hexdigest()[:6]}"

    def to_ffmpeg_af(self) -> str:
        """Convert active EQ settings to an FFmpeg audio filter (-af) string
        for real-time playback.
        """
        if not self.enabled and not self.hpf_30hz and abs(self.output_trim_db) <= 0.01:
            return ""

        filters: list[str] = []

        if self.hpf_30hz:
            filters.append("highpass=f=30")

        if self.enabled:
            for freq in EQ_FREQUENCIES:
                gain = float(self.bands.get(freq, 0.0))
                if abs(gain) >= 0.05:
                    filters.append(f"equalizer=f={freq}:width_type=o:w=1:g={gain:.2f}")

        if abs(self.output_trim_db) >= 0.05:
            sign = "+" if self.output_trim_db > 0 else ""
            filters.append(f"volume={sign}{self.output_trim_db:.2f}dB")

        return ",".join(filters)


def is_flat(settings: MasteringEQSettings) -> bool:
    """True when the settings would not change the audio at all."""
    if settings.hpf_30hz or abs(settings.output_trim_db) > 0.01:
        return False
    if not settings.enabled:
        return True
    return all(abs(settings.bands.get(f, 0.0)) < 0.05 for f in EQ_FREQUENCIES)


def apply_mastering_eq(
    audio: np.ndarray,
    settings: MasteringEQSettings,
    sample_rate: int = 48000,
    ceiling_dbfs: float = -0.1,
) -> np.ndarray:
    """
    Apply zero-phase 10-band mastering equalization and acoustic conditioning.

    Parameters:
        audio: 1D (mono) or 2D (channels, samples) float32 audio.
        settings: Active EQ configuration.
        sample_rate: Sampling rate in Hz (default 48000).
        ceiling_dbfs: Headroom limit in dBFS for safety limiter.

    Returns:
        Equalized audio with identical shape and sample count.
    """
    if not settings.enabled and not settings.hpf_30hz and settings.output_trim_db == 0.0:
        return audio

    is_1d = audio.ndim == 1
    audio_2d = audio[np.newaxis, :] if is_1d else audio
    channels, n_samples = audio_2d.shape

    if n_samples < 64:
        return audio

    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
    # Safe frequencies avoiding log2(0)
    safe_freqs = np.maximum(freqs, 1.0)

    # 1. Compute smooth log-frequency Gaussian weighting for each octave center
    total_gain_db = np.zeros_like(freqs, dtype=np.float32)
    weight_sum = np.zeros_like(freqs, dtype=np.float32)
    sigma = 0.65  # Octave bell width

    for f_center in EQ_FREQUENCIES:
        gain = float(settings.bands.get(f_center, 0.0)) if settings.enabled else 0.0
        # Log2 distance in octaves
        dist_oct = np.log2(safe_freqs / float(f_center))
        w = np.exp(-0.5 * (dist_oct / sigma) ** 2).astype(np.float32)
        total_gain_db += gain * w
        weight_sum += w

    # Normalize gain blending across the frequency spectrum
    norm_gain_db = np.where(weight_sum > 1e-4, total_gain_db / (weight_sum + 1e-6), 0.0)

    # Add master output trim
    norm_gain_db += float(settings.output_trim_db)

    # Convert to linear magnitude transfer function
    transfer = (10.0 ** (norm_gain_db / 20.0)).astype(np.float32)

    # 2. Apply 30Hz High-Pass Filter if engaged
    if settings.hpf_30hz:
        f_cutoff = 30.0
        # 2nd-order high-pass magnitude response
        ratio = freqs / f_cutoff
        hpf_mag = (ratio**2) / np.sqrt(1.0 + ratio**4)
        transfer *= hpf_mag.astype(np.float32)

    # DC component zeroed if HPF is active
    if settings.hpf_30hz:
        transfer[0] = 0.0

    # 3. Apply transfer curve in frequency domain
    out_channels = []
    for c in range(channels):
        spec = np.fft.rfft(audio_2d[c])
        spec_eq = spec * transfer
        out_c = np.fft.irfft(spec_eq, n=n_samples).astype(np.float32)
        out_channels.append(out_c)

    eq_audio = np.stack(out_channels, axis=0)

    # 4. Soft True-Peak Limiter Guard
    ceiling_linear = float(10.0 ** (ceiling_dbfs / 20.0))
    peak = float(np.max(np.abs(eq_audio)))
    if peak > ceiling_linear:
        # Transparent tanh soft-knee limiting above ceiling
        knee_start = 0.85 * ceiling_linear
        over = np.abs(eq_audio) > knee_start
        if np.any(over):
            headroom = ceiling_linear - knee_start
            delta = (np.abs(eq_audio) - knee_start) / headroom
            compressed = knee_start + headroom * np.tanh(delta)
            eq_audio = np.where(over, np.sign(eq_audio) * compressed, eq_audio)
        eq_audio = np.clip(eq_audio, -ceiling_linear, ceiling_linear)

    return eq_audio[0] if is_1d else eq_audio
