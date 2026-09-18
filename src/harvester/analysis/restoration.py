"""Conservative, deterministic audio restoration using NumPy only.

This module deliberately restores presentation characteristics rather than inventing
missing information.  It accepts mono ``(samples,)`` or interleaved stereo
``(samples, 2)`` float audio and never mutates the caller's array.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np


@dataclass(frozen=True, slots=True)
class RestorationConfig:
    """Validated limits and controls for :func:`restore`.

    All gains are deliberately bounded.  ``decorrelate_high_band`` is opt-in because
    changing spatial image is a larger perceptual decision than transient shaping or
    low-frequency mono compatibility.
    """

    transient_gain: float = 0.10
    max_transient_gain: float = 0.25
    transient_time_ms: float = 8.0
    peak_limit: float = 0.98
    crest_limit: float = 12.0
    soft_clip_drive: float = 1.5
    low_frequency_hz: float = 120.0
    mono_compatibility: float = 0.75
    decorrelate_high_band: bool = False
    high_band_hz: float = 4_000.0
    decorrelation_amount: float = 0.25
    decorrelation_delay_ms: float = 0.35
    correlation_threshold: float = 0.85
    correlation_floor: float = 0.20

    def __post_init__(self) -> None:
        _bounded("transient_gain", self.transient_gain, 0.0, self.max_transient_gain)
        _bounded("max_transient_gain", self.max_transient_gain, 0.0, 1.0)
        _positive("transient_time_ms", self.transient_time_ms)
        _bounded("peak_limit", self.peak_limit, 0.0, 1.0, inclusive_low=False)
        _positive("crest_limit", self.crest_limit)
        _bounded("soft_clip_drive", self.soft_clip_drive, 0.0, 100.0)
        _bounded("low_frequency_hz", self.low_frequency_hz, 0.0, 96_000.0)
        _bounded("mono_compatibility", self.mono_compatibility, 0.0, 1.0)
        _bounded("high_band_hz", self.high_band_hz, 0.0, 96_000.0)
        _bounded("decorrelation_amount", self.decorrelation_amount, 0.0, 1.0)
        _bounded("decorrelation_delay_ms", self.decorrelation_delay_ms, 0.0, 100.0)
        _bounded("correlation_threshold", self.correlation_threshold, -1.0, 1.0)
        _bounded("correlation_floor", self.correlation_floor, -1.0, 1.0)
        if self.correlation_floor >= self.correlation_threshold:
            raise ValueError("correlation_floor must be below correlation_threshold")


@dataclass(frozen=True, slots=True)
class AudioMetrics:
    """Level and stereo metrics for one audio buffer."""

    peak: float
    rms: float
    crest_factor: float
    stereo_correlation: float
    clipping: bool


# A descriptive alias keeps callers free to use either terminology.
RestorationMetrics = AudioMetrics


@dataclass(frozen=True, slots=True)
class RestorationResult:
    """Restored audio, measurements, and machine-readable provenance."""

    audio: np.ndarray
    metrics: AudioMetrics
    input_metrics: AudioMetrics
    sample_rate: float
    synthetic_high_band: bool = False
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Results are safe to pass between pipeline stages without accidental edits.
        output = np.asarray(self.audio)
        output.setflags(write=False)
        object.__setattr__(self, "audio", output)
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


def measure_metrics(audio: np.ndarray) -> AudioMetrics:
    """Measure peak, RMS, crest factor, stereo correlation, and clipping."""

    data = _validate_audio(audio)
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(data, dtype=np.float64))))
    crest = peak / rms if rms > np.finfo(np.float64).tiny else float("inf")
    correlation = _stereo_correlation(data)
    return AudioMetrics(
        peak=peak,
        rms=rms,
        crest_factor=float(crest),
        stereo_correlation=correlation,
        clipping=bool(np.any(np.abs(data) >= 1.0)),
    )


# Common spelling for callers that treat metrics as a calculation operation.
calculate_metrics = measure_metrics


def correlation_interlock(
    correlation: float, *, threshold: float = 0.85, floor: float = 0.20
) -> float:
    """Return a smooth [0, 1] side-gain interlock for a correlation value.

    Below ``floor`` the side is closed; above ``threshold`` it is untouched.  A
    smoothstep transition avoids a discontinuity as a track's correlation changes.
    """

    if not np.isfinite(correlation):
        raise ValueError("correlation must be finite")
    _bounded("threshold", threshold, -1.0, 1.0)
    _bounded("floor", floor, -1.0, 1.0)
    if floor >= threshold:
        raise ValueError("floor must be below threshold")
    position = float(np.clip((correlation - floor) / (threshold - floor), 0.0, 1.0))
    return position * position * (3.0 - 2.0 * position)


def restore(
    audio: np.ndarray,
    sample_rate: float,
    *,
    config: RestorationConfig | None = None,
) -> RestorationResult:
    """Apply bounded, deterministic restoration without mutating ``audio``.

    The input must be a finite, non-empty float32/float64 mono or interleaved stereo
    array.  No high-band samples are synthesized; optional decorrelation only changes
    the phase of existing high-band side information.
    """

    _validate_sample_rate(sample_rate)
    source = _validate_audio(audio)
    if not np.any(source != 0.0):
        raise ValueError("silent audio is not restorable")
    settings = config or RestorationConfig()
    original_dtype = source.dtype
    working = np.array(source, dtype=np.float64, copy=True)
    before = measure_metrics(source)

    working = _enhance_transients(working, float(sample_rate), settings)
    if working.ndim == 2:
        working = _stereo_processing(working, float(sample_rate), settings)
    working = _apply_limits(working, settings)
    output = np.asarray(working, dtype=original_dtype)
    output = np.array(output, copy=True)

    after = measure_metrics(output)
    operations = ["bounded_transient_enhancement", "tanh_soft_clip", "peak_limit"]
    if source.ndim == 2 and settings.low_frequency_hz > 0 and settings.mono_compatibility > 0:
        operations.append("low_frequency_mono_compatibility_blend")
    if source.ndim == 2 and settings.decorrelate_high_band:
        operations.append("opt_in_high_band_decorrelation")
    provenance = {
        "method": "numpy_conservative_restoration",
        "version": "1",
        "operations": ",".join(operations),
        "input_dtype": str(original_dtype),
        "output_dtype": str(output.dtype),
        "synthetic_high_band": "false",
    }
    return RestorationResult(
        audio=output,
        metrics=after,
        input_metrics=before,
        sample_rate=float(sample_rate),
        synthetic_high_band=False,
        provenance=provenance,
    )


restore_audio = restore


def _stereo_processing(
    audio: np.ndarray, sample_rate: float, config: RestorationConfig
) -> np.ndarray:
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    length = audio.shape[0]
    frequencies = np.fft.rfftfreq(length, d=1.0 / sample_rate)
    mid_spectrum = np.fft.rfft(mid)
    side_spectrum = np.fft.rfft(side)

    # This is a blend toward mid, not an L+R replacement.  A cosine taper keeps
    # the boundary smooth and leaves high-band stereo untouched.
    if config.low_frequency_hz > 0 and config.mono_compatibility > 0:
        low_edge = config.low_frequency_hz * 0.5
        low_weight = np.clip((config.low_frequency_hz - frequencies) / low_edge, 0.0, 1.0)
        low_weight[frequencies <= low_edge] = 1.0
        side_spectrum *= 1.0 - config.mono_compatibility * low_weight

    if config.decorrelate_high_band and config.high_band_hz < sample_rate * 0.5:
        high_mask = frequencies >= config.high_band_hz
        correlation = _stereo_correlation(audio)
        interlock = correlation_interlock(
            correlation,
            threshold=config.correlation_threshold,
            floor=config.correlation_floor,
        )
        delay = config.decorrelation_delay_ms / 1_000.0
        phase = np.exp(-2j * np.pi * frequencies * delay)
        high_side = side_spectrum * high_mask
        phase_shifted = high_side * phase
        effective_amount = config.decorrelation_amount * interlock
        side_spectrum = side_spectrum + high_mask * effective_amount * (
            phase_shifted - side_spectrum
        )
        # The interlock also tapers high-band side gain, preventing a weakly
        # correlated source from receiving an aggressive spatial change.
        side_spectrum = side_spectrum * np.where(high_mask, interlock, 1.0)

    processed_mid = np.fft.irfft(mid_spectrum, n=length)
    processed_side = np.fft.irfft(side_spectrum, n=length)
    return np.column_stack((processed_mid + processed_side, processed_mid - processed_side))


def _enhance_transients(
    audio: np.ndarray, sample_rate: float, config: RestorationConfig
) -> np.ndarray:
    if config.transient_gain == 0.0:
        return audio
    channels = 1 if audio.ndim == 1 else audio.shape[1]
    shaped = audio[:, None] if audio.ndim == 1 else audio
    alpha = float(np.exp(-1.0 / (sample_rate * config.transient_time_ms / 1_000.0)))
    result = np.empty_like(shaped)
    for channel in range(channels):
        signal = shaped[:, channel]
        low = np.empty_like(signal)
        low[0] = signal[0]
        for index in range(1, len(signal)):
            low[index] = alpha * low[index - 1] + (1.0 - alpha) * signal[index]
        transient = signal - low
        result[:, channel] = signal + config.transient_gain * transient
    return result[:, 0] if audio.ndim == 1 else result


def _apply_limits(audio: np.ndarray, config: RestorationConfig) -> np.ndarray:
    result = np.array(audio, dtype=np.float64, copy=True)
    drive = config.soft_clip_drive
    if drive > 0:
        result = np.tanh(result * drive) / np.tanh(drive)

    # Spread only pathological peaks over a short deterministic window.  This is
    # the only time-domain crest intervention; ordinary program material is left
    # alone.  The cap bounds both CPU work and transient smearing.
    for _ in range(6):
        rms = float(np.sqrt(np.mean(np.square(result))))
        peak = float(np.max(np.abs(result)))
        crest = peak / rms if rms > np.finfo(np.float64).tiny else float("inf")
        if crest <= config.crest_limit or peak == 0.0:
            break
        window = int(np.ceil(4.0 * (crest / config.crest_limit) ** 2))
        window = max(3, min(257, window))
        if window % 2 == 0:
            window += 1
        kernel = np.ones(window, dtype=np.float64) / window
        if result.ndim == 1:
            result = np.convolve(result, kernel, mode="same")
        else:
            result = np.column_stack(
                tuple(
                    np.convolve(result[:, channel], kernel, mode="same")
                    for channel in range(result.shape[1])
                )
            )

    # The tanh stage and crest spread are followed by a linked peak scale.  No
    # hard clipping is used, and the scale keeps stereo channel balance intact.
    peak = float(np.max(np.abs(result)))
    if peak > config.peak_limit:
        result *= config.peak_limit / peak
    return result


def _validate_audio(audio: np.ndarray) -> np.ndarray:
    if not isinstance(audio, np.ndarray):
        raise TypeError("audio must be a NumPy array")
    if audio.dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        raise TypeError("audio must have float32 or float64 dtype")
    if audio.ndim not in (1, 2) or (audio.ndim == 2 and audio.shape[1] != 2):
        raise ValueError("audio must have shape (samples,) or (samples, 2)")
    if audio.shape[0] == 0:
        raise ValueError("audio must not be empty")
    if not np.all(np.isfinite(audio)):
        raise ValueError("audio must contain only finite values")
    return audio


def _validate_sample_rate(sample_rate: float) -> None:
    if not isinstance(sample_rate, (int, float, np.integer, np.floating)):
        raise TypeError("sample_rate must be numeric")
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("sample_rate must be finite and positive")


def _stereo_correlation(audio: np.ndarray) -> float:
    if audio.ndim == 1:
        return 1.0
    left = audio[:, 0].astype(np.float64, copy=False)
    right = audio[:, 1].astype(np.float64, copy=False)
    left_centered = left - np.mean(left)
    right_centered = right - np.mean(right)
    denominator = float(np.linalg.norm(left_centered) * np.linalg.norm(right_centered))
    if denominator <= np.finfo(np.float64).eps:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.clip(np.dot(left_centered, right_centered) / denominator, -1.0, 1.0))


def _bounded(
    name: str, value: float, lower: float, upper: float, *, inclusive_low: bool = True
) -> None:
    if (
        not np.isfinite(value)
        or value < lower
        or (not inclusive_low and value == lower)
        or value > upper
    ):
        bounds = f"[{lower}, {upper}]" if inclusive_low else f"({lower}, {upper}]"
        raise ValueError(f"{name} must be in {bounds}")


def _positive(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


__all__ = [
    "AudioMetrics",
    "RestorationConfig",
    "RestorationMetrics",
    "RestorationResult",
    "calculate_metrics",
    "correlation_interlock",
    "measure_metrics",
    "restore",
    "restore_audio",
]
