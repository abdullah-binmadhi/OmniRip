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
    assert not mm.is_cached("flashsr")
    assert mm.get_model_path("flashsr") is None
    assert not mm.is_cached("dereverb")
    assert mm.get_model_path("dereverb") is None

    # Simulate cached file
    flashsr_file = tmp_path / SUPPORTED_MODELS["flashsr"].filename
    flashsr_file.parent.mkdir(parents=True, exist_ok=True)
    flashsr_file.write_bytes(b"dummy_weights")
    dereverb_file = tmp_path / SUPPORTED_MODELS["dereverb"].filename
    dereverb_file.write_bytes(b"dummy_dereverb_weights")

    assert mm.is_cached("flashsr")
    assert mm.get_model_path("flashsr") == flashsr_file
    assert mm.is_cached("dereverb")
    assert mm.get_model_path("dereverb") == dereverb_file
    assert mm.get_model_path("nonexistent") is None


def test_model_manager_registry_lists_every_supported_model():
    """Verify every supported model is properly registered in SUPPORTED_MODELS."""
    expected = {
        "flashsr",
        "flashsr_ldm",
        "flashsr_vae",
        "bs_roformer",
        "hdemucs",
        "htdemucs_6s",
        "dereverb",
        "clap",
    }
    assert set(SUPPORTED_MODELS.keys()) == expected
    for name, spec in SUPPORTED_MODELS.items():
        assert spec.repo_id, f"{name} missing repo_id"
        assert spec.filename, f"{name} missing filename"
        assert spec.description, f"{name} missing description"


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

    fake_file = tmp_path / "flashsr_vocoder.pt"
    fake_file.write_bytes(b"downloaded_model_bytes")

    mock_hf = MagicMock()
    mock_hf.hf_hub_download.return_value = str(fake_file)

    with patch.dict(sys.modules, {"huggingface_hub": mock_hf}):
        progress_events = []
        res = mm.download_model("flashsr", progress_callback=lambda p: progress_events.append(p))
        assert res == fake_file
        assert 1.0 in progress_events


def test_model_manager_unknown_model(tmp_path: Path):
    """Test that requesting an unknown model raises KeyError."""
    mm = ModelManager(cache_dir=tmp_path)
    with pytest.raises(KeyError):
        mm.download_model("super_ultra_model_9000")


def test_model_manager_download_direct_http(tmp_path: Path):
    """Test downloading a model via direct HTTP streaming fallback
    when huggingface_hub is absent."""
    import sys
    from unittest.mock import MagicMock

    mm = ModelManager(cache_dir=tmp_path)

    mock_resp = MagicMock()
    mock_resp.headers = {"content-length": "100"}
    mock_resp.iter_bytes.return_value = [b"chunk_1_", b"chunk_2"]
    mock_resp.__enter__.return_value = mock_resp

    progress = []

    with (
        patch.dict(sys.modules, {"huggingface_hub": None}),
        patch("httpx.stream", return_value=mock_resp),
    ):
        out = mm.download_model("flashsr", progress_callback=lambda p: progress.append(p))
        assert out.exists()
        assert out.read_bytes() == b"chunk_1_chunk_2"
        assert 1.0 in progress


def test_model_manager_download_hdemucs_direct_url(tmp_path: Path):
    """Test downloading hdemucs using fallback direct_url when torchaudio fails."""
    import sys
    from unittest.mock import MagicMock

    mm = ModelManager(cache_dir=tmp_path)

    mock_resp = MagicMock()
    mock_resp.headers = {"content-length": "100"}
    mock_resp.iter_bytes.return_value = [b"hdemucs_data"]
    mock_resp.__enter__.return_value = mock_resp

    with (
        patch.dict(sys.modules, {"torchaudio": None}),
        patch("httpx.stream", return_value=mock_resp),
    ):
        out = mm.download_model("hdemucs", force_download=True)
        assert out.exists()
        assert out.read_bytes() == b"hdemucs_data"

