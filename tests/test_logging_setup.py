import logging
from pathlib import Path

from harvester.appdirs import AppPaths
from harvester.util.logging_setup import SecretMaskingFilter, configure_logging


def test_secret_filter_redacts_values() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "token=%s", ("secret",), None)
    assert SecretMaskingFilter(["secret"]).filter(record)
    assert record.getMessage() == "token=[REDACTED]"


def test_configured_logger_writes_rotating_file(tmp_path: Path) -> None:
    paths = AppPaths.from_base(tmp_path / "data")
    controller = configure_logging(paths, secret_values=["secret"])
    try:
        logger = logging.getLogger("harvester.test")
        logger.info("hello secret")
        controller.listener.enqueue_sentinel()
        controller.listener.stop()
        content = (paths.logs / "harvester.log").read_text(encoding="utf-8")
        assert "hello [REDACTED]" in content
        assert "secret" not in content
    finally:
        controller.close()
