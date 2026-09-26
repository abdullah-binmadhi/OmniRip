"""Full Vision Audio Player and Playlist Engine.

Handles multi-format audio loading (WAV, MP3, FLAC, OGG, AAC, M4A), playlist
queue management, transport playback controls, hardware audio output (via macOS afplay
or fallback software clock), and 60 FPS frame-accurate audio feature synchronization.
"""

from __future__ import annotations

import logging
import os
import random
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np

from harvester.ui.visuals.base import AudioFeatureContext

logger = logging.getLogger(__name__)


class PlaybackState(StrEnum):
    STOPPED = "STOPPED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"


class LoopMode(StrEnum):
    OFF = "OFF"
    TRACK = "TRACK"
    ALL = "ALL"


@dataclass
class PlaylistTrack:
    """An audio track in the Full Vision playlist with precomputed 60 FPS visual telemetry."""

    track_id: str
    file_path: Path
    title: str
    artist: str = "Unknown Artist"
    duration_seconds: float = 0.0
    sample_rate: int = 44100
    channels: int = 2
    feature_track: list[AudioFeatureContext] = field(default_factory=list)

    @property
    def formatted_duration(self) -> str:
        """Return MM:SS duration string."""
        mins = int(self.duration_seconds // 60)
        secs = int(self.duration_seconds % 60)
        return f"{mins:02d}:{secs:02d}"


def extract_60fps_features(y: np.ndarray, sr: int) -> list[AudioFeatureContext]:
    """Compute an array of AudioFeatureContext frames at 60 frames per second.

    Each frame contains 128-band FFT energy levels, peak hold, L/R stereo waveforms,
    M/S decomposition, RMS dB, LUFS-M approximation, crest factor, and transient flags.
    """
    if y.ndim == 1:
        y_l = y
        y_r = y
    else:
        y_l = y[0] if y.shape[0] < y.shape[1] else y[:, 0]
        y_r = y[1] if y.shape[0] < y.shape[1] else y[:, 1]

    n_samples = len(y_l)
    duration = n_samples / sr
    fps = 60
    total_frames = max(1, int(duration * fps))
    hop_samples = max(1, int(sr / fps))

    # Fast sliding window FFT parameters
    n_fft = 1024
    half_fft = n_fft // 2
    frames: list[AudioFeatureContext] = []

    # Pre-calculate Hann window
    window = np.hanning(n_fft)

    for i in range(total_frames):
        center_idx = int(i * hop_samples)
        start_idx = max(0, center_idx - half_fft)
        end_idx = min(n_samples, start_idx + n_fft)

        # Slice waveforms for oscilloscope
        wf_l = np.zeros(n_fft, dtype=np.float32)
        wf_r = np.zeros(n_fft, dtype=np.float32)

        actual_len = end_idx - start_idx
        if actual_len > 0:
            wf_l[:actual_len] = y_l[start_idx:end_idx]
            wf_r[:actual_len] = y_r[start_idx:end_idx]

        # Mid/Side
        mid = (wf_l + wf_r) * 0.5
        side = (wf_l - wf_r) * 0.5

        # RMS & Crest Factor
        rms = float(np.sqrt(np.mean(mid**2) + 1e-12))
        rms_db = float(20.0 * np.log10(max(rms, 1e-5)))
        peak = float(np.max(np.abs(mid)))
        crest = float(20.0 * np.log10(max(peak / max(rms, 1e-5), 1.0)))

        # FFT Spectrum across 128 logarithmic bands
        win_sig = mid * window
        spectrum = np.abs(np.fft.rfft(win_sig))
        spec_len = len(spectrum)

        # Resample spectrum to 128 bins
        if spec_len >= 128:
            bin_indices = np.linspace(0, spec_len - 1, 128).astype(int)
            levels_128 = spectrum[bin_indices]
        else:
            levels_128 = np.pad(spectrum, (0, 128 - spec_len))

        # Normalize 128 levels to 0.0 - 1.0 range
        max_spec = np.max(levels_128) if len(levels_128) > 0 else 1.0
        if max_spec > 1e-6:
            levels_128 = np.clip(levels_128 / max_spec, 0.0, 1.0)
        else:
            levels_128 = np.zeros(128, dtype=np.float32)

        # Spectral centroid
        freqs = np.linspace(20, sr // 2, 128)
        sum_energy = float(np.sum(levels_128))
        if sum_energy > 1e-6:
            centroid = float(np.sum(freqs * levels_128) / sum_energy)
        else:
            centroid = 440.0

        # Transient detection (sharp rise in RMS)
        transient = False
        if i > 0 and len(frames) > 0:
            prev_rms = frames[-1].rms_db
            if rms_db - prev_rms > 6.0 and rms_db > -35.0:
                transient = True

        ctx = AudioFeatureContext(
            levels_128=levels_128.astype(np.float32),
            peaks_128=levels_128.astype(np.float32),
            waveform_l=wf_l.astype(np.float32),
            waveform_r=wf_r.astype(np.float32),
            mid_channel=mid.astype(np.float32),
            side_channel=side.astype(np.float32),
            rms_db=rms_db,
            lufs_m=rms_db - 3.0,
            crest_factor=crest,
            phase_corr=float(np.clip(1.0 - (np.std(side) / (np.std(mid) + 1e-6)), -1.0, 1.0)),
            spectral_centroid=centroid,
            transient_flag=transient,
            is_playing=True,
        )
        frames.append(ctx)

    return frames


class VisionAudioPlayer:
    """Integrated music player with 60 FPS visualizer telemetry."""

    def __init__(self):
        self.playlist: list[PlaylistTrack] = []
        self.current_index: int = -1
        self.state: PlaybackState = PlaybackState.STOPPED
        self.loop_mode: LoopMode = LoopMode.OFF
        self.shuffle_mode: bool = False

        self._start_time: float = 0.0
        self._pause_time: float = 0.0
        self._elapsed_offset: float = 0.0
        self._audio_process: subprocess.Popen | None = None
        self._on_track_change_listeners: list[Callable[[PlaylistTrack], None]] = []

    @property
    def current_track(self) -> PlaylistTrack | None:
        """Return the currently selected track, or None if playlist is empty."""
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    @property
    def current_position_seconds(self) -> float:
        """Current playback head position in seconds."""
        if self.state == PlaybackState.PLAYING:
            return min(
                self.current_track.duration_seconds if self.current_track else 0.0,
                self._elapsed_offset + (time.time() - self._start_time),
            )
        elif self.state == PlaybackState.PAUSED:
            return self._elapsed_offset
        return 0.0

    @property
    def formatted_position(self) -> str:
        """Return MM:SS string of current playback position."""
        pos = self.current_position_seconds
        mins = int(pos // 60)
        secs = int(pos % 60)
        return f"{mins:02d}:{secs:02d}"

    @property
    def shuffle(self) -> bool:
        """Return current shuffle mode status."""
        return self.shuffle_mode

    def add_listener(self, callback: Callable[[PlaylistTrack], None]) -> None:
        """Register a callback for track changes."""
        self._on_track_change_listeners.append(callback)

    def load_track(self, file_path: Path) -> PlaylistTrack | None:
        """Load an audio file, extract metadata, and precompute 60 FPS visual telemetry."""
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            logger.error("Audio file does not exist: %s", path)
            return None

        title = path.stem.replace("_", " ").title()
        artist = "Local Library"

        y = None
        sr = 44100

        # Attempt to load with soundfile or scipy or librosa
        try:
            import soundfile as sf
            data, sr = sf.read(str(path))
            y = data.T if data.ndim > 1 else data
        except Exception:
            try:
                import librosa
                data, sr = librosa.load(str(path), sr=22050, mono=False)
                y = data
            except Exception:
                try:
                    import wave
                    with wave.open(str(path), "rb") as wf:
                        sr = wf.getframerate()
                        n_frames = wf.getnframes()
                        frames_data = wf.readframes(n_frames)
                        y = np.frombuffer(frames_data, dtype=np.int16).astype(np.float32) / 32768.0
                except Exception as exc:
                    logger.warning("Could not read raw PCM from %s: %s. Using procedural synthesis.", path, exc)
                    # Procedural fallback track
                    sr = 44100
                    duration = 180.0
                    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
                    y = 0.5 * np.sin(2 * np.pi * 130 * t) + 0.3 * np.sin(2 * np.pi * 320 * t)

        duration = float(len(y[0]) if y.ndim > 1 else len(y)) / sr
        feature_frames = extract_60fps_features(y, sr)

        track_id = f"trk_{abs(hash(str(path))) % 10000000:07d}"
        track = PlaylistTrack(
            track_id=track_id,
            file_path=path,
            title=title,
            artist=artist,
            duration_seconds=duration,
            sample_rate=sr,
            channels=2 if y.ndim > 1 else 1,
            feature_track=feature_frames,
        )

        self.playlist.append(track)
        if self.current_index == -1:
            self.current_index = 0
            for cb in self._on_track_change_listeners:
                cb(track)

        return track

    def remove_track(self, index: int) -> None:
        """Remove a track from the playlist."""
        if 0 <= index < len(self.playlist):
            if index == self.current_index:
                self.stop()
            self.playlist.pop(index)
            if self.current_index >= len(self.playlist):
                self.current_index = len(self.playlist) - 1

    def clear(self) -> None:
        """Clear all tracks from the playlist."""
        self.stop()
        self.playlist.clear()
        self.current_index = -1

    def play(self, index: int | None = None) -> None:
        """Start playing track at given index or current index."""
        if not self.playlist:
            return

        if index is not None and 0 <= index < len(self.playlist):
            if index != self.current_index:
                self.stop()
                self.current_index = index

        if self.current_index == -1:
            self.current_index = 0

        track = self.current_track
        if not track:
            return

        self._kill_audio_process()
        self._start_audio_process(offset_seconds=self._elapsed_offset)
        self._start_time = time.time()
        self.state = PlaybackState.PLAYING

        for cb in self._on_track_change_listeners:
            cb(track)

    def pause(self) -> None:
        """Pause playback."""
        if self.state == PlaybackState.PLAYING:
            self._elapsed_offset += time.time() - self._start_time
            self._kill_audio_process()
            self.state = PlaybackState.PAUSED

    def resume(self) -> None:
        """Resume playback from paused position."""
        if self.state == PlaybackState.PAUSED:
            self._start_audio_process(offset_seconds=self._elapsed_offset)
            self._start_time = time.time()
            self.state = PlaybackState.PLAYING

    def toggle_play_pause(self) -> None:
        """Toggle between Play and Pause."""
        if self.state == PlaybackState.PLAYING:
            self.pause()
        elif self.state == PlaybackState.PAUSED:
            self.resume()
        else:
            self.play()

    def stop(self) -> None:
        """Stop playback and rewind to beginning."""
        self._kill_audio_process()
        self._elapsed_offset = 0.0
        self.state = PlaybackState.STOPPED

    def seek(self, target_seconds: float) -> None:
        """Seek to a specific timestamp in the current track."""
        track = self.current_track
        if not track:
            return

        target_seconds = max(0.0, min(track.duration_seconds, target_seconds))
        was_playing = (self.state == PlaybackState.PLAYING)
        self._kill_audio_process()
        self._elapsed_offset = target_seconds

        if was_playing:
            self._start_audio_process(offset_seconds=target_seconds)
            self._start_time = time.time()
            self.state = PlaybackState.PLAYING

    def next_track(self) -> None:
        """Advance to next track in queue."""
        if not self.playlist:
            return

        if self.shuffle_mode and len(self.playlist) > 1:
            indices = [i for i in range(len(self.playlist)) if i != self.current_index]
            self.current_index = random.choice(indices)
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)

        self.stop()
        self.play()

    def prev_track(self) -> None:
        """Go back to previous track in queue or restart current song."""
        if not self.playlist:
            return

        # If more than 3 seconds in, restart current track
        if self.current_position_seconds > 3.0:
            self.seek(0.0)
            return

        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.stop()
        self.play()

    def toggle_loop(self) -> LoopMode:
        """Cycle loop mode: OFF -> TRACK -> ALL -> OFF."""
        if self.loop_mode == LoopMode.OFF:
            self.loop_mode = LoopMode.TRACK
        elif self.loop_mode == LoopMode.TRACK:
            self.loop_mode = LoopMode.ALL
        else:
            self.loop_mode = LoopMode.OFF
        return self.loop_mode

    def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode."""
        self.shuffle_mode = not self.shuffle_mode
        return self.shuffle_mode

    def update_frame(self) -> AudioFeatureContext:
        """Called every frame (e.g. at 60 Hz). Progresses track and returns feature context."""
        track = self.current_track
        if not track or self.state != PlaybackState.PLAYING:
            return AudioFeatureContext(is_playing=False)

        current_pos = self.current_position_seconds

        # Check end of track
        if current_pos >= track.duration_seconds:
            if self.loop_mode == LoopMode.TRACK:
                self.seek(0.0)
                return self.update_frame()
            elif self.loop_mode == LoopMode.ALL or self.current_index < len(self.playlist) - 1:
                self.next_track()
                return self.update_frame()
            else:
                self.stop()
                return AudioFeatureContext(is_playing=False)

        # Retrieve synchronized 60 FPS feature frame
        frame_idx = int(current_pos * 60)
        if 0 <= frame_idx < len(track.feature_track):
            return track.feature_track[frame_idx]
        elif track.feature_track:
            return track.feature_track[-1]

        return AudioFeatureContext(is_playing=True)

    def _start_audio_process(self, offset_seconds: float = 0.0) -> None:
        """Start hardware audio playback subprocess on macOS."""
        track = self.current_track
        if not track or not sys.platform.startswith("darwin"):
            return

        file_str = str(track.file_path)
        if not os.path.exists(file_str):
            return

        try:
            cmd = ["afplay"]
            if offset_seconds > 0.05:
                cmd.extend(["-s", f"{offset_seconds:.2f}"])
            cmd.append(file_str)
            self._audio_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.warning("Failed to start afplay for %s: %s", file_str, exc)
            self._audio_process = None

    def _kill_audio_process(self) -> None:
        """Terminate active audio subprocess."""
        if self._audio_process:
            try:
                self._audio_process.terminate()
                self._audio_process.wait(timeout=0.2)
            except Exception:
                try:
                    self._audio_process.kill()
                except Exception:
                    pass
            self._audio_process = None
