"""Per-second issue scanning: the "Suggest spots" engine behind Repair.

Self-contained successor to the Layer Studio issue detector: it loads a file's
1-second windows, flags acoustic defects (vocal_bleed, whisper, sizzle, mud,
sub_rumble), and merges the flagged seconds into ranges the user can accept or
edit in the guided Repair flow (docs/01 D35).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

SEGMENT_SIZE_S: float = 1.0
DEFAULT_SEVERITY: float = 0.30

VOCAL_CORE_BAND: tuple[float, float] = (300.0, 3500.0)
WHISPER_BAND: tuple[float, float] = (1000.0, 2800.0)
SIBILANCE_BAND: tuple[float, float] = (5500.0, 8500.0)
MUD_BAND: tuple[float, float] = (250.0, 350.0)
LOW_END_BAND: tuple[float, float] = (30.0, 120.0)

ISSUE_LABELS: dict[str, str] = {
    "vocal_bleed": "Vocal bleed (instruments leaking voice band)",
    "whisper": "Ghost whispers (side-channel vocal leakage)",
    "sizzle": "Sibilance harshness (5.5-8.5 kHz)",
    "mud": "Low-mid mud (250-350 Hz boxiness)",
    "sub_rumble": "Sub rumble (30-120 Hz energy)",
}

ISSUE_COLORS: dict[str, str] = {
    "vocal_bleed": "#ff3366",
    "whisper": "#ffcc00",
    "sizzle": "#ffffff",
    "mud": "#cc6633",
    "sub_rumble": "#9966ff",
}



@dataclass
class LayerIssue:
    """An acoustically flagged defect at one specific second of one layer."""

    kind: str
    layer: str
    severity: float = 0.0

    @property
    def label(self) -> str:
        return ISSUE_LABELS.get(self.kind, self.kind.replace("_", " ").title())

    @property
    def color(self) -> str:
        return ISSUE_COLORS.get(self.kind, "#ff3366")


def _load_segment(
    path: Path, seg_idx: int, segment_size_s: float, sr: int
) -> tuple[np.ndarray, int] | None:
    """Load one segment window as a 2D (channels, samples) floor-level mono array."""
    import soundfile as sf

    try:
        start = int(seg_idx * segment_size_s * sr)
        seg_len = int(segment_size_s * sr)
        data, file_sr = sf.read(
            str(path), dtype="float32", start=start, frames=seg_len, always_2d=True
        )
        if data.shape[0] == 0:
            return None
        audio = data.T
        return audio, file_sr
    except Exception as exc:
        logger.debug("segment load failed for %s: %s", path, exc)
        return None



def _band_db(mono: np.ndarray, sr: int, band: tuple[float, float]) -> float:
    """Mean spectral energy (dB) of one band using FFT windowing."""
    n = mono.shape[0]
    if n < 128:
        return -60.0
    winsz = min(2048, n)
    window = np.hanning(winsz)
    seg = mono[:winsz]
    mag = np.abs(np.fft.rfft(seg * window))
    freqs = np.fft.rfftfreq(winsz, d=1.0 / sr)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if not np.any(mask):
        return -60.0
    return float(20.0 * np.log10(np.mean(mag[mask]) + 1e-9))



def _detect_segment_issues(
    audio: np.ndarray, sr: int, source_name: str, envelope_db: float
) -> list[LayerIssue]:
    """Detect acoustic defects for one source stem in one second."""
    issues: list[LayerIssue] = []
    if audio.size == 0 or envelope_db < -55.0:
        return issues

    mono_energy_db = 20.0 * np.log10(np.sqrt(np.mean(audio.mean(0) ** 2)) + 1e-9)
    mono = audio.mean(axis=0)

    if source_name in ("drums", "kick", "snare", "hats", "bass", "other"):
        vocal_energy = _band_db(mono, sr, VOCAL_CORE_BAND)
        if vocal_energy > mono_energy_db + 6.0:
            sev = float(np.clip((vocal_energy - mono_energy_db - 6.0) / 18.0, 0.0, 1.0))
            issues.append(LayerIssue("vocal_bleed", source_name, round(sev, 3)))

    if source_name in ("vocals", "other") and audio.shape[0] > 1:
        side = audio[1] - audio[0]
        side_db = float(20.0 * np.log10(np.sqrt(np.mean(side**2)) + 1e-9))
        mid_db = float(20.0 * np.log10(np.sqrt(np.mean(audio.mean(0) ** 2)) + 1e-9))
        if side_db > mid_db + 4.0:
            sev = float(np.clip((side_db - mid_db - 4.0) / 15.0, 0.0, 1.0))
            issues.append(LayerIssue("whisper", source_name, round(sev, 3)))

    if source_name == "vocals":
        sib = _band_db(mono, sr, SIBILANCE_BAND)
        if sib > mono_energy_db + 8.0:
            sev = float(np.clip((sib - mono_energy_db - 8.0) / 18.0, 0.0, 1.0))
            issues.append(LayerIssue("sizzle", source_name, round(sev, 3)))

    if source_name in ("vocals", "other"):
        mud = _band_db(mono, sr, MUD_BAND)
        if mud > mono_energy_db + 8.0:
            sev = float(np.clip((mud - mono_energy_db - 8.0) / 16.0, 0.0, 1.0))
            issues.append(LayerIssue("mud", source_name, round(sev, 3)))

    if source_name in ("bass", "drums"):
        low = _band_db(mono, sr, LOW_END_BAND)
        if low > -24.0:
            sev = float(np.clip((low + 24.0) / 20.0, 0.0, 1.0))
            issues.append(LayerIssue("sub_rumble", source_name, round(sev, 3)))

    return issues



def estimate_duration(path: Path) -> float:
    """Return audio duration in seconds using soundfile, falling back to wav header."""
    try:
        import soundfile as sf

        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception as sf_err:
        logger.debug("soundfile duration failed for %s: %s", path, sf_err)
    try:
        import wave

        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / float(wav.getframerate())
    except Exception as wav_err:
        logger.debug("wave duration failed for %s: %s", path, wav_err)
    return 0.0



def _segment_envelope_db(mono: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2) + 1e-9))
    return float(np.clip(20.0 * np.log10(max(rms, 1e-6)), -60.0, 0.0))



def issue_seconds(
    path: Path,
    issue_kind: str,
    source_name: str,
    *,
    duration_s: float | None = None,
    segment_size_s: float = SEGMENT_SIZE_S,
    severity: float = DEFAULT_SEVERITY,
    sample_rate: int = 44100,
) -> list[int]:
    """Indices of the seconds where ``issue_kind`` fires on this file."""
    duration = duration_s if duration_s is not None else estimate_duration(path)
    if duration <= 0.0:
        return []
    n_segments = max(1, int(math.ceil(duration / segment_size_s)))
    flagged: list[int] = []
    for seg_idx in range(n_segments):
        window = _load_segment(path, seg_idx, segment_size_s, sample_rate)
        if window is None:
            continue
        audio, file_sr = window
        if audio.size == 0 or float(np.max(np.abs(audio))) <= 1e-4:
            continue
        envelope_db = _segment_envelope_db(audio.mean(axis=0))
        for issue in _detect_segment_issues(audio, file_sr, source_name, envelope_db):
            if issue.kind == issue_kind and issue.severity >= severity:
                flagged.append(seg_idx)
                break
    return flagged



def merge_seconds(
    seconds: list[int],
    *,
    segment_size_s: float = SEGMENT_SIZE_S,
    gap_s: float = 1.0,
    pad_s: float = 0.5,
    duration_s: float | None = None,
) -> list[tuple[float, float]]:
    """Merge flagged second indices into padded, gap-tolerant ranges."""
    if not seconds:
        return []
    ordered = sorted(set(int(s) for s in seconds))
    runs: list[list[int]] = [[ordered[0]]]
    for idx in ordered[1:]:
        if idx <= runs[-1][-1] + 1 + int(round(gap_s / segment_size_s)):
            runs[-1].append(idx)
        else:
            runs.append([idx])
    ranges: list[tuple[float, float]] = []
    for run in runs:
        start = max(0.0, run[0] * segment_size_s - pad_s)
        end = (run[-1] + 1) * segment_size_s + pad_s
        if duration_s is not None:
            end = min(float(duration_s), end)
        if end > start:
            ranges.append((start, end))
    return ranges



def suggest_ranges(
    path: Path,
    issue_kind: str,
    source_name: str,
    *,
    duration_s: float | None = None,
    severity: float = DEFAULT_SEVERITY,
    sample_rate: int = 44100,
) -> list[tuple[float, float]]:
    """Time ranges where the detector hears ``issue_kind`` on this file."""
    duration = duration_s if duration_s is not None else estimate_duration(path)
    seconds = issue_seconds(
        path,
        issue_kind,
        source_name,
        duration_s=duration,
        severity=severity,
        sample_rate=sample_rate,
    )
    return merge_seconds(seconds, duration_s=duration)


__all__ = [
    "DEFAULT_SEVERITY",
    "issue_seconds",
    "merge_seconds",
    "suggest_ranges",
]


__all__ = [
    "DEFAULT_SEVERITY",
    "ISSUE_COLORS",
    "ISSUE_LABELS",
    "LAYER_ISSUE_BANDS",
    "LayerIssue",
    "SEGMENT_SIZE_S",
    "estimate_duration",
    "issue_seconds",
    "merge_seconds",
    "suggest_ranges",
]

LAYER_ISSUE_BANDS: dict[str, tuple[float, float]] = {
    "vocal_bleed": VOCAL_CORE_BAND,
    "whisper": WHISPER_BAND,
    "sizzle": SIBILANCE_BAND,
    "mud": MUD_BAND,
    "sub_rumble": LOW_END_BAND,
}
