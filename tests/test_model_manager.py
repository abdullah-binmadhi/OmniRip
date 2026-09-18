"""Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from harvester.analysis.enhancement import check_enhancement_available
from harvester.analysis.enhancement.provider import EnhancementProvider
from harvester.services.model_manager import SUPPORTED_MODELS, ModelManager


def test_enhancement_provider_protocol_check():
    """Verify that a dummy class adhering to EnhancementProvider satisfies isinstance check."""
    class DummyProvider:
        @property
        def name(self) -> str:
            return "Dummy"

        @property
        def is_available(self) -> bool:
            return True

        def generate_residual(self, audio, sample_rate, cutoff_hz):
            return audio

    provider = DummyProvider()
    assert isinstance(provider, EnhancementProvider)


def test_check_enhancement_available_returns_status():
    """Verify check_enhancement_available returns boolean and descriptive string."""
    avail, msg = check_enhancement_available()
    assert isinstance(avail, bool)
    assert isinstance(msg, str)
    if not avail:
        assert "Optional neural restoration dependencies missing" in msg


def test_model_manager_cache_lookup(tmp_path: Path):
    """Test model path resolution and caching checks in ModelManager."""
    mm = ModelManager(cache_dir=tmp_path)
    assert not mm.is_cached("nvsr")
    assert mm.get_model_path("nvsr") is None

    # Simulate cached file
    nvsr_file = tmp_path / SUPPORTED_MODELS["nvsr"].filename
    nvsr_file.write_bytes(b"dummy_weights")

    assert mm.is_cached("nvsr")
    assert mm.get_model_path("nvsr") == nvsr_file
    assert mm.get_model_path("nonexistent") is None


def test_model_manager_checksum_verification(tmp_path: Path):
    """Verify SHA-256 calculation and verification."""
    data = b"model_test_content_12345"
    expected = hashlib.sha256(data).hexdigest()
    test_file = tmp_path / "test.pt"
    test_file.write_bytes(data)

    assert ModelManager.verify_checksum(test_file, expected)
    assert not ModelManager.verify_checksum(test_file, "wrong_hash")


def test_model_manager_download_mocked(tmp_path: Path):
    """Test downloading a model via mocked huggingface_hub."""
    import sys
    from unittest.mock import MagicMock

    mm = ModelManager(cache_dir=tmp_path)

    fake_file = tmp_path / "nvsr_resunet_48k.pt"
    fake_file.write_bytes(b"downloaded_model_bytes")

    mock_hf = MagicMock()
    mock_hf.hf_hub_download.return_value = str(fake_file)

    with patch.dict(sys.modules, {"huggingface_hub": mock_hf}):
        progress_events = []
        res = mm.download_model("nvsr", progress_callback=lambda p: progress_events.append(p))
        assert res == fake_file
        assert 1.0 in progress_events


def test_model_manager_unknown_model(tmp_path: Path):
    """Test that requesting an unknown model raises KeyError."""
    mm = ModelManager(cache_dir=tmp_path)
    with pytest.raises(KeyError):
        mm.download_model("super_ultra_model_9000")
