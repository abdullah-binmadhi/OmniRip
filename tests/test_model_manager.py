"""Tests for ModelManager and EnhancementProvider protocol (Milestone 10-A)."""

from __future__ import annotations

import hashlib
import io
import os
import sys
import threading
import time
import types
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


def test_download_model_reports_real_hf_progress(tmp_path: Path):
    """hf_hub_download's tqdm_class must forward byte-level progress to us."""
    mm = ModelManager(cache_dir=tmp_path)
    # Deliberately not the cache target path: this test exercises the download
    # branch, not the cached short-circuit.
    fake_file = tmp_path / "downloads" / "sr_vocoder.pth"

    def fake_hf_hub_download(repo_id, filename, local_dir=None, tqdm_class=None):
        assert tqdm_class is not None, "progress-capable tqdm_class not passed"
        bar = tqdm_class(total=4, disable=False, file=io.StringIO())
        for _ in range(4):
            bar.update(1)
        return str(fake_file)

    module = types.ModuleType("huggingface_hub")
    module.hf_hub_download = fake_hf_hub_download
    progress: list[float] = []
    with patch.dict(sys.modules, {"huggingface_hub": module}):
        mm.download_model("flashsr", progress_callback=progress.append)

    assert 1.0 in progress
    assert any(0.0 < value < 1.0 for value in progress)


def test_download_many_downloads_concurrently(tmp_path: Path):
    """Three models must be in flight at once, not one after another."""
    mm = ModelManager(cache_dir=tmp_path)
    barrier = threading.Barrier(3, timeout=10)

    def fake_download(name, progress_callback=None, force_download=False):
        barrier.wait()
        if progress_callback:
            progress_callback(1.0)
        return tmp_path / f"{name}.bin"

    mm.download_model = fake_download  # type: ignore[method-assign]
    seen: list[tuple[str, float]] = []
    results = mm.download_many(
        ["a", "b", "c"],
        progress_callback=lambda name, fraction: seen.append((name, fraction)),
        max_workers=3,
    )

    assert set(results) == {"a", "b", "c"}
    assert all(path is not None for path in results.values())
    assert ("a", 1.0) in seen


def test_download_many_collects_failures(tmp_path: Path):
    mm = ModelManager(cache_dir=tmp_path)

    def fake_download(name, progress_callback=None, force_download=False):
        if name == "bad":
            raise RuntimeError("boom")
        return tmp_path / f"{name}.bin"

    mm.download_model = fake_download  # type: ignore[method-assign]
    results = mm.download_many(["good", "bad"], max_workers=2)

    assert results["good"] is not None
    assert results["bad"] is None


def test_prune_stale_incomplete_removes_only_old_files(tmp_path: Path):
    mm = ModelManager(cache_dir=tmp_path)
    download_dir = tmp_path / ".cache" / "huggingface" / "download" / "weights"
    download_dir.mkdir(parents=True, exist_ok=True)
    stale = download_dir / "deadbeef.1111.incomplete"
    fresh = download_dir / "deadbeef.2222.incomplete"
    stale.write_bytes(b"stale")
    fresh.write_bytes(b"fresh")
    old = time.time() - 7 * 3600
    os.utime(stale, (old, old))

    removed = mm._prune_stale_incomplete()

    assert removed == 1
    assert not stale.exists()
    assert fresh.exists()

