"""Unit tests for memory governance, VRAM purging, and device/dtype selection (M24)."""

from unittest.mock import patch

import pytest

try:
    import torch
except ImportError:
    torch = None

from harvester.util.memory import (
    DEFAULT_CHUNK_SECONDS_16GB,
    SAFE_CHUNK_SECONDS_LOW_MEM,
    get_memory_headroom_mb,
    get_safe_chunk_duration,
    get_safe_neural_device,
    get_safe_neural_dtype,
    is_low_memory_headroom,
    purge_neural_vram,
)


def test_get_memory_headroom_returns_positive_float():
    headroom = get_memory_headroom_mb()
    assert isinstance(headroom, float)
    assert headroom > 0.0


def test_is_low_memory_headroom_threshold_logic():
    with patch("harvester.util.memory.get_memory_headroom_mb", return_value=1024.0):
        assert is_low_memory_headroom(2048.0) is True
        assert is_low_memory_headroom(512.0) is False


def test_purge_neural_vram_does_not_raise():
    # Should safely succeed on any machine (CPU, MPS, CUDA)
    purge_neural_vram()


@pytest.mark.skipif(torch is None, reason="torch is not installed in lightweight environment")
def test_get_safe_neural_device_respects_env(monkeypatch):
    monkeypatch.setenv("OMNIRIP_DEVICE", "cpu")
    dev = get_safe_neural_device()
    assert dev.type == "cpu"


@pytest.mark.skipif(torch is None, reason="torch is not installed in lightweight environment")
def test_get_safe_neural_dtype_cpu_is_float32():
    cpu_dev = torch.device("cpu")
    assert get_safe_neural_dtype(cpu_dev) == torch.float32


@pytest.mark.skipif(torch is None, reason="torch is not installed in lightweight environment")
def test_get_safe_neural_dtype_respects_disable_env(monkeypatch):
    monkeypatch.setenv("OMNIRIP_FP16", "0")
    mps_dev = (
        torch.device("mps")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        else torch.device("cpu")
    )
    assert get_safe_neural_dtype(mps_dev) == torch.float32


def test_get_safe_chunk_duration_shrinks_under_low_memory():
    with patch("harvester.util.memory.get_memory_headroom_mb", return_value=500.0):
        chunk_sec = get_safe_chunk_duration(DEFAULT_CHUNK_SECONDS_16GB)
        assert chunk_sec == SAFE_CHUNK_SECONDS_LOW_MEM

    with patch("harvester.util.memory.get_memory_headroom_mb", return_value=8000.0):
        chunk_sec = get_safe_chunk_duration(DEFAULT_CHUNK_SECONDS_16GB)
        assert chunk_sec == DEFAULT_CHUNK_SECONDS_16GB
