"""
Real-time Audio Visualizer Widget for OmniRip TUI.

Provides multi-band logarithmic spectrum analysis, peak hold decay,
linear-phase cutoff markers, and animated oscilloscope waveform modes
using fast NumPy FFT processing and Unicode block rendering.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import numpy as np
from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.timer import Timer
from textual.widget import Widget

VisualizerMode = Literal["spectrum", "oscilloscope"]

# Unicode block elements for 8 fractional vertical steps
_BLOCKS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")
_PEAK_CHAR = "▔"

# Default 24 logarithmic frequency band center points (Hz)
DEFAULT_BANDS_HZ = [
    30, 50, 80, 125, 200, 315, 500, 800,
    1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300,
    8000, 10000, 12500, 15000, 16500, 18000, 20000, 22050,
]


class AudioVisualizer(Widget):
    """
    High-performance audio visualizer widget supporting real-time multi-band
    equalizer spectrum bars and dynamic oscilloscope waveforms.
    """

    DEFAULT_CSS = """
    AudioVisualizer {
        height: 6;
        min-height: 4;
        width: 1fr;
        background: transparent;
        padding: 0;
    }
    """

    mode: reactive[VisualizerMode] = reactive("spectrum")
    is_playing: reactive[bool] = reactive(False)
    cutoff_hz: reactive[float | None] = reactive(None)

    def __init__(
        self,
        num_bands: int = 24,
        mode: VisualizerMode = "spectrum",
        cutoff_hz: float | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.num_bands = num_bands
        self.mode = mode
        self.cutoff_hz = cutoff_hz

        # Level state: [0.0, 1.0] per band
        self._levels = np.zeros(num_bands, dtype=np.float32)
        self._peaks = np.zeros(num_bands, dtype=np.float32)
        self._peak_hold_ticks = np.zeros(num_bands, dtype=np.int32)

        # Oscilloscope buffer
        self._wave_buffer = np.zeros(64, dtype=np.float32)

        # Cached pre-computed FFT frames for loaded audio track
        self._precomputed_frames: list[np.ndarray] = []
        self._current_frame_idx = 0
        self._anim_timer: Timer | None = None
        self._idle_phase = 0.0

    def on_mount(self) -> None:
        # 30 FPS update loop for silky smooth rendering
        self._anim_timer = self.set_interval(0.033, self._on_tick)

    def on_unmount(self) -> None:
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None

    def toggle_mode(self) -> VisualizerMode:
        """Toggle between spectrum and oscilloscope visualization modes."""
        self.mode = "oscilloscope" if self.mode == "spectrum" else "spectrum"
        self.refresh()
        return self.mode

    def set_cutoff(self, cutoff_hz: float | None) -> None:
        """Set or clear the visual cutoff frequency marker (fc)."""
        self.cutoff_hz = cutoff_hz
        self.refresh()

    def feed_levels(self, levels: Sequence[float]) -> None:
        """Manually update the current band energy levels."""
        arr = np.clip(np.asarray(levels, dtype=np.float32), 0.0, 1.0)
        if len(arr) == self.num_bands:
            self._levels = arr
        else:
            self._levels = np.interp(
                np.linspace(0, 1, self.num_bands),
                np.linspace(0, 1, len(arr)),
                arr,
            ).astype(np.float32)
        self._update_peaks()
        self.refresh()

    def feed_pcm(self, pcm_data: np.ndarray, sample_rate: int = 44100) -> None:
        """Compute real-time FFT spectrum from raw PCM audio slice."""
        if len(pcm_data) == 0:
            return
        if pcm_data.ndim > 1:
            pcm_data = np.mean(pcm_data, axis=1)

        # Update oscilloscope buffer
        step = max(1, len(pcm_data) // len(self._wave_buffer))
        sampled_wave = pcm_data[::step][: len(self._wave_buffer)]
        if len(sampled_wave) < len(self._wave_buffer):
            sampled_wave = np.pad(sampled_wave, (0, len(self._wave_buffer) - len(sampled_wave)))
        self._wave_buffer = np.clip(sampled_wave, -1.0, 1.0).astype(np.float32)

        # Windowed FFT for spectrum
        n_fft = min(2048, len(pcm_data))
        window = np.hanning(n_fft)
        segment = pcm_data[:n_fft] * window
        fft_vals = np.abs(np.fft.rfft(segment))
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)

        # Pool into logarithmic bands
        band_freqs = np.geomspace(30, min(sample_rate // 2, 22000), self.num_bands + 1)
        band_levels = np.zeros(self.num_bands, dtype=np.float32)
        for i in range(self.num_bands):
            mask = (freqs >= band_freqs[i]) & (freqs < band_freqs[i + 1])
            if np.any(mask):
                val = np.mean(fft_vals[mask])
                # Log compression: scale from ~dB to [0, 1]
                band_levels[i] = float(np.clip((20 * np.log10(val + 1e-6) + 60) / 60, 0.0, 1.0))

        self._levels = band_levels
        self._update_peaks()
        self.refresh()

    def load_audio_frames(self, audio_file: Path) -> None:
        """
        Fast-parse and pre-compute 50ms FFT frames from an audio file
        using direct FFmpeg PCM decode.
        """
        import subprocess

        cmd = [
            "ffmpeg", "-v", "quiet",
            "-i", str(audio_file),
            "-f", "s16le", "-ac", "1", "-ar", "22050",
            "-"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, check=True)
            raw = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
            frame_size = 1024
            hop_size = 735  # ~33ms at 22050Hz (30 FPS)
            frames = []
            for start in range(0, len(raw) - frame_size, hop_size):
                chunk = raw[start : start + frame_size]
                fft = np.abs(np.fft.rfft(chunk * np.hanning(frame_size)))
                freqs = np.fft.rfftfreq(frame_size, d=1.0 / 22050)
                band_freqs = np.geomspace(30, 11000, self.num_bands + 1)
                b_levels = np.zeros(self.num_bands, dtype=np.float32)
                for b in range(self.num_bands):
                    m = (freqs >= band_freqs[b]) & (freqs < band_freqs[b + 1])
                    if np.any(m):
                        v = np.mean(fft[m])
                        b_levels[b] = float(np.clip((20 * np.log10(v + 1e-5) + 55) / 55, 0.0, 1.0))
                frames.append(b_levels)
            self._precomputed_frames = frames
            self._current_frame_idx = 0
        except Exception:
            self._precomputed_frames = []

    def play(self) -> None:
        """Start active playback visualization."""
        self.is_playing = True
        self.refresh()

    def pause(self) -> None:
        """Pause playback visualization."""
        self.is_playing = False
        self.refresh()

    def stop(self) -> None:
        """Stop playback visualization and reset to idle."""
        self.is_playing = False
        self._current_frame_idx = 0
        self._levels.fill(0.0)
        self._peaks.fill(0.0)
        self.refresh()

    def seek(self, seconds: float) -> None:
        """Seek the visualizer to an audio timestamp in seconds."""
        if not self._precomputed_frames:
            return
        fps = 30.0  # 735 hop at 22050Hz is ~30 fps
        target_idx = int(max(0.0, seconds) * fps)
        self._current_frame_idx = min(target_idx, max(0, len(self._precomputed_frames) - 1))
        if 0 <= self._current_frame_idx < len(self._precomputed_frames):
            self._levels = self._precomputed_frames[self._current_frame_idx].copy()
            self._peaks = np.maximum(self._peaks, self._levels)
        self.refresh()

    def _update_peaks(self) -> None:
        for i in range(self.num_bands):
            if self._levels[i] >= self._peaks[i]:
                self._peaks[i] = self._levels[i]
                self._peak_hold_ticks[i] = 4  # hold for 4 ticks (~130ms)
            else:
                if self._peak_hold_ticks[i] > 0:
                    self._peak_hold_ticks[i] -= 1
                else:
                    # Exponential gravity fall
                    self._peaks[i] = max(0.0, self._peaks[i] - 0.05)

    def _on_tick(self) -> None:
        if self.is_playing and self._precomputed_frames:
            if self._current_frame_idx < len(self._precomputed_frames):
                self._levels = self._precomputed_frames[self._current_frame_idx]
                self._current_frame_idx += 1
                self._update_peaks()
                self.refresh()
            else:
                self.stop()
        elif not self.is_playing:
            # Ambient breathing decay when idle
            self._idle_phase += 0.05
            if np.any(self._levels > 0.01) or np.any(self._peaks > 0.01):
                self._levels = np.maximum(0.0, self._levels - 0.04)
                self._peaks = np.maximum(0.0, self._peaks - 0.03)
                self.refresh()

    def render(self) -> Text:
        """Render the audio visualization to Rich text."""
        height = max(3, self.size.height or 5)
        width = max(20, self.size.width or 60)

        if self.mode == "oscilloscope":
            return self._render_oscilloscope(width, height)
        return self._render_spectrum(width, height)

    def _render_spectrum(self, width: int, height: int) -> Text:
        text = Text()
        n_bands = min(self.num_bands, (width - 4) // 2)
        if n_bands <= 0:
            n_bands = self.num_bands

        # Calculate cutoff column index if fc is set
        cutoff_col = -1
        if self.cutoff_hz is not None:
            log_min = math.log10(30)
            log_max = math.log10(22050)
            log_fc = math.log10(max(30.0, min(22050.0, self.cutoff_hz)))
            norm_fc = (log_fc - log_min) / (log_max - log_min)
            cutoff_col = int(norm_fc * n_bands)

        band_levels = self._levels[:n_bands]
        band_peaks = self._peaks[:n_bands]

        lines: list[list[tuple[str, Style]]] = [[] for _ in range(height)]

        for col_idx in range(n_bands):
            lvl = float(band_levels[col_idx])
            pk = float(band_peaks[col_idx])
            fill_height = lvl * (height - 1)
            peak_row = height - 1 - int(round(pk * (height - 1)))
            peak_row = max(0, min(height - 1, peak_row))

            is_upper_synthetic = (cutoff_col >= 0 and col_idx >= cutoff_col)

            for row in range(height):
                row_from_bottom = height - 1 - row
                char = " "
                style_str = "dim"

                if row == peak_row and pk > 0.05:
                    char = _PEAK_CHAR
                    style_str = "bold #ff3366" if is_upper_synthetic else "bold #00ffcc"
                elif row_from_bottom < int(fill_height):
                    char = "█"
                    style_str = self._level_style(row_from_bottom, height, is_upper_synthetic)
                elif row_from_bottom == int(fill_height):
                    frac = fill_height - int(fill_height)
                    idx = int(round(frac * 8))
                    char = _BLOCKS[idx]
                    style_str = self._level_style(row_from_bottom, height, is_upper_synthetic)

                style = Style.parse(style_str)
                lines[row].append((char + " ", style))

        # Build Rich Text from lines
        for row_idx, line in enumerate(lines):
            for ch, st in line:
                text.append(ch, style=st)
            # Add cutoff label on top row if active
            if row_idx == 0 and self.cutoff_hz is not None and cutoff_col >= 0:
                fc_text = f" ┊ fc: {self.cutoff_hz / 1000:.1f} kHz"
                text.append(fc_text, style="bold #ffe600")
            text.append("\n")

        return text

    def _render_oscilloscope(self, width: int, height: int) -> Text:
        text = Text()
        center_row = height // 2
        buf_len = len(self._wave_buffer)
        step = max(1, buf_len // max(1, width - 2))

        lines = [[" "] * width for _ in range(height)]

        for x in range(min(width - 2, buf_len)):
            sample_val = self._wave_buffer[x * step % buf_len]
            if not self.is_playing:
                # Ambient sine wave
                sample_val = 0.3 * math.sin(x * 0.2 + self._idle_phase)

            row = center_row - int(round(sample_val * (height // 2 - 1)))
            row = max(0, min(height - 1, row))
            lines[row][x] = "─" if abs(sample_val) < 0.1 else "•"

        for row in range(height):
            for col in range(width):
                char = lines[row][col]
                color = "#00f0ff" if char != " " else "dim"
                text.append(char, style=color)
            text.append("\n")

        return text

    @staticmethod
    def _level_style(row_from_bottom: int, max_height: int, is_upper: bool) -> str:
        ratio = row_from_bottom / max(1, max_height)
        if is_upper:
            # Synthetic restored band uses glowing magenta/cyan
            return "#ff007f" if ratio > 0.6 else "#d100d1" if ratio > 0.3 else "#7928ca"
        # Authoritative lower band uses vibrant cyan/emerald/yellow
        if ratio > 0.75:
            return "bold #ff5555"
        if ratio > 0.5:
            return "#ffe600"
        return "#00ff9f"
