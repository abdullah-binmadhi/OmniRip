"""Tests for CLI --download-models flag in harvester.__main__."""

from __future__ import annotations

from unittest.mock import patch

from harvester.__main__ import build_parser, main


def test_build_parser_has_download_models_flag():
    parser = build_parser()
    args = parser.parse_args(["--download-models"])
    assert args.download_models is True


def test_main_download_models_invokes_model_manager():
    with patch("harvester.services.model_manager.ModelManager") as mock_mm_cls:
        instance = mock_mm_cls.return_value
        instance.is_cached.return_value = True

        exit_code = main(["--download-models"])
        assert exit_code == 0
        instance.is_cached.assert_called()
