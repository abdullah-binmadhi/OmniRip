"""Tests for the neural de-reverb path (anvuew/dereverb_bs_roformer + vendored MSST)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from harvester.analysis.enhancement import dereverb as dereverb_module
from harvester.analysis.enhancement.dereverb import (
    CHUNK_SAMPLES,
    NeuralDereverb,
    chunk_windows,
)


def test_chunk_windows_short_audio_single_window():
    assert chunk_windows(1000) == [(0, 1000)]
    assert chunk_windows(CHUNK_SAMPLES) == [(0, CHUNK_SAMPLES)]


def test_chunk_windows_overlap_math():
    total = CHUNK_SAMPLES * 3
    windows = chunk_windows(total)
    hop = CHUNK_SAMPLES // 2
    assert windows[0] == (0, CHUNK_SAMPLES)
    assert windows[1] == (hop, hop + CHUNK_SAMPLES)
    assert windows[-1][1] == total
    # every sample is covered by at least one window
    covered = np.zeros(total, dtype=bool)
    for start, end in windows:
        covered[start:end] = True
    assert covered.all()


def test_neural_dereverb_unavailable_without_checkpoint(tmp_path: Path):
    assert not NeuralDereverb(model_path=tmp_path / "missing.ckpt").is_available


def test_vendored_bs_roformer_builds_and_forwards():
    """The vendored architecture runs a tiny forward pass (no checkpoint needed)."""
    torch = pytest.importorskip("torch")
    from harvester.vendor.msst import BSRoformer

    model = BSRoformer(
        dim=16,
        depth=1,
        stereo=True,
        num_stems=1,
        time_transformer_depth=1,
        freq_transformer_depth=1,
        linear_transformer_depth=0,
        freqs_per_bands=(512, 513),
        dim_head=8,
        heads=2,
        flash_attn=False,
        stft_n_fft=2048,
        stft_hop_length=512,
        stft_win_length=2048,
        mask_estimator_depth=1,
    )
    model.eval()
    audio = torch.zeros(1, 2, 11025)
    with torch.inference_mode():
        out = model(audio)
    assert out.shape == (1, 1, 2, 11025)


def test_dereverb_wiring_blends_neural_dry_vocal():
    """`_apply_dereverb_isolation` blends the neural dry signal by intensity."""
    from harvester.analysis.enhancement.stem_separator import _apply_dereverb_isolation

    wet = np.random.default_rng(0).normal(0, 0.1, (2, 4410)).astype(np.float32)
    neural_dry = wet * 0.25

    with patch.object(NeuralDereverb, "is_available", new_callable=lambda: property(lambda self: True)):
        with patch.object(NeuralDereverb, "enhance", return_value=neural_dry):
            dry, reverb = _apply_dereverb_isolation(wet, sr=44100, intensity=1.0)
            assert np.allclose(dry, neural_dry, atol=1e-6)
            assert np.allclose(dry + reverb, wet, atol=1e-6)

            dry_half, reverb_half = _apply_dereverb_isolation(wet, sr=44100, intensity=0.5)
            assert np.allclose(dry_half, wet + 0.5 * (neural_dry - wet), atol=1e-6)
            assert np.allclose(dry_half + reverb_half, wet, atol=1e-6)


def test_dereverb_falls_back_to_spectral_engine(monkeypatch: pytest.MonkeyPatch):
    """When the neural path is unavailable the spectral engine still runs."""
    from harvester.analysis.enhancement.stem_separator import _apply_dereverb_isolation

    monkeypatch.setattr(dereverb_module.NeuralDereverb, "is_available", property(lambda self: False))
    wet = np.random.default_rng(1).normal(0, 0.1, (2, 4410)).astype(np.float32)
    dry, reverb = _apply_dereverb_isolation(wet, sr=44100, intensity=0.4)
    assert dry.shape == wet.shape and reverb.shape == wet.shape
    assert np.allclose(dry + reverb, wet, atol=1e-5)


def test_dereverb_zero_intensity_is_identity():
    from harvester.analysis.enhancement.stem_separator import _apply_dereverb_isolation

    wet = np.random.default_rng(2).normal(0, 0.1, (2, 4410)).astype(np.float32)
    dry, reverb = _apply_dereverb_isolation(wet, sr=44100, intensity=0.0)
    assert np.array_equal(dry, wet)
    assert not reverb.any()
