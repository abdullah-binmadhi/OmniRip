"""Tests for PreviewManager and CurationWorkbenchModal (Milestone 10-E)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import wave

import numpy as np
import pytest
from textual.app import App, ComposeResult

from harvester.analysis.enhancement.presets import PRESETS
from harvester.services.enhancement.preview import PreviewManager
from harvester.ui.screens.curation_workbench import CurationWorkbenchModal


def test_preview_manager_find_energetic_slice():
    """Verify energetic slice detection avoids quiet intro."""
    sr = 48000
    # 30 seconds total: first 10s quiet, next 15s loud, last 5s quiet
    t_quiet = np.zeros((2, 10 * sr), dtype=np.float32)
    t_loud = np.ones((2, 15 * sr), dtype=np.float32) * 0.8
    t_tail = np.zeros((2, 5 * sr), dtype=np.float32)
    audio = np.concatenate([t_quiet, t_loud, t_tail], axis=1)

    start, end = PreviewManager.find_energetic_slice(audio, sample_rate=sr, duration_sec=15.0)
    # The energetic window should be located around 10s (sample index ~ 480000)
    assert abs(start - 10 * sr) < sr  # Within 1s of loud onset
    assert end - start == 15 * sr


def test_preview_manager_write_wav(tmp_path: Path):
    """Verify write_wav writes valid 16-bit PCM WAV."""
    sr = 48000
    audio = np.random.normal(0, 0.3, (2, 2400)).astype(np.float32)
    out_wav = tmp_path / "test.wav"

    PreviewManager.write_wav(out_wav, audio, sample_rate=sr)
    assert out_wav.exists()

    with wave.open(str(out_wav), "rb") as w:
        assert w.getnchannels() == 2
        assert w.getsampwidth() == 2
        assert w.getframerate() == sr
        assert w.getnframes() == 2400


def test_preview_manager_generate_pair(tmp_path: Path):
    """Verify generate_preview_pair creates both original and enhanced WAV files."""
    pm = PreviewManager(cache_dir=tmp_path)
    fake_track = tmp_path / "song.mp3"
    fake_track.write_bytes(b"dummy")

    dummy_audio = np.random.normal(0, 0.2, (2, 48000 * 20)).astype(np.float32)
    with patch.object(pm.exporter, "decode_audio_ffmpeg", return_value=dummy_audio):
        orig_p, enh_p = pm.generate_preview_pair(
            input_path=fake_track,
            preset=PRESETS["conservative"],
            duration_sec=5.0,
        )
        assert orig_p.exists()
        assert enh_p.exists()
        assert "orig_prev" in orig_p.name
        assert "conservative_prev" in enh_p.name


def test_preview_manager_open_in_player(tmp_path: Path):
    """Verify launching default player calls subprocess."""
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFFdummy")

    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        proc = PreviewManager.open_in_system_player(dummy_wav)
        assert proc == mock_proc
        assert mock_popen.called


class _MockApp(App):
    def __init__(self, modal: CurationWorkbenchModal) -> None:
        super().__init__()
        self.modal = modal

    def compose(self) -> ComposeResult:
        yield from ()

    async def on_mount(self) -> None:
        await self.push_screen(self.modal)


@pytest.mark.asyncio
async def test_curation_workbench_modal_ui(tmp_path: Path):
    """Test Textual CurationWorkbenchModal composition and interactions."""
    fake_track = tmp_path / "track.mp3"
    fake_track.write_bytes(b"dummy")

    mock_pm = MagicMock(spec=PreviewManager)
    mock_pm.generate_preview_pair.return_value = (tmp_path / "orig.wav", tmp_path / "enh.wav")

    mock_exporter = MagicMock()
    mock_exporter.export_enhanced_derivative.return_value = tmp_path / "track.enhanced.mp3"

    modal = CurationWorkbenchModal(
        audio_file=fake_track,
        preview_manager=mock_pm,
        exporter=mock_exporter,
    )
    app = _MockApp(modal)

    async with app.run_test() as pilot:
        await pilot.pause()
        # Modal should be mounted
        assert modal.is_mounted
        assert modal.selected_preset_id == "conservative"

        # Press Preview Button
        await pilot.click("#btn-preview")
        await pilot.pause()
        assert mock_pm.generate_preview_pair.called
        assert mock_pm.open_in_system_player.called

        # Press Export Button
        await pilot.click("#btn-export")
        await pilot.pause()
        assert mock_exporter.export_enhanced_derivative.called
