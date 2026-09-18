from harvester.models import DownloadProgress
from harvester.services.ytdlp import YtdlpService
from harvester.util.errors import PermanentSource, RateLimited, TransientNetwork


def test_progress_parser_handles_machine_readable_line() -> None:
    parsed = YtdlpService.parse_progress("download:42.5%|1024|2048|1.5MiB/s|00:01")

    assert parsed is not None
    assert parsed.progress == DownloadProgress(
        bytes_done=1024,
        bytes_total=2048,
        speed_bps=1.5 * 1024 * 1024,
        percent=42.5,
    )


def test_progress_parser_ignores_unrelated_lines() -> None:
    assert YtdlpService.parse_progress("[download] 42%") is None
    assert YtdlpService.parse_progress("download:bad") is None


def test_failure_catalog_classifies_documented_errors() -> None:
    assert YtdlpService.classify_failure("HTTP Error 429: Too Many Requests", 1) is RateLimited
    assert YtdlpService.classify_failure("Private video", 1) is PermanentSource
    assert YtdlpService.classify_failure("network reset", 1) is TransientNetwork
