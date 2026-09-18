"""Queue-based logging fan-out with secret redaction."""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from harvester.appdirs import AppPaths


class SecretMaskingFilter(logging.Filter):
    """Replace configured secret values before a record reaches any handler."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = tuple(secret for secret in secrets if secret)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self._secrets:
            message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


class ContextDefaultsFilter(logging.Filter):
    """Supply structured fields for logs emitted outside a pipeline job."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = getattr(record, "job_id", None) or "-"
        record.phase = getattr(record, "phase", None) or "-"
        return True


class CallbackHandler(logging.Handler):
    """Small adapter for consumers that want formatted log records."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.callback(self.format(record))
        except Exception:
            self.handleError(record)


@dataclass(slots=True)
class LoggingController:
    logger: logging.Logger
    queue_handler: QueueHandler
    listener: QueueListener
    file_handler: RotatingFileHandler

    def close(self) -> None:
        """Stop the listener and detach the queue handler exactly once."""

        if self.listener._thread is not None:  # type: ignore[attr-defined]
            self.listener.stop()
        if self.queue_handler in self.logger.handlers:
            self.logger.removeHandler(self.queue_handler)
        self.file_handler.close()


def _level(value: str) -> int:
    level = getattr(logging, value.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"unknown logging level: {value}")
    return level


def configure_logging(
    paths: AppPaths,
    *,
    file_level: str = "DEBUG",
    ui_level: str = "INFO",
    ui_callback: Callable[[str], None] | None = None,
    secret_values: Iterable[str] = (),
) -> LoggingController:
    """Configure the ``harvester`` logger and return a lifecycle controller."""

    paths.logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("harvester")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    log_path = paths.logs / "harvester.log"
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(_level(file_level))
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s job=%(job_id)s phase=%(phase)s %(message)s"
    )
    file_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [file_handler]
    if ui_callback is not None:
        ui_handler = CallbackHandler(ui_callback)
        ui_handler.setLevel(_level(ui_level))
        ui_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        handlers.append(ui_handler)

    mask = SecretMaskingFilter(secret_values)
    context_defaults = ContextDefaultsFilter()
    for handler in handlers:
        handler.addFilter(context_defaults)
        handler.addFilter(mask)

    log_queue: queue.Queue[logging.LogRecord] = queue.Queue()
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)
    listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    listener.start()
    return LoggingController(logger, queue_handler, listener, file_handler)


__all__ = [
    "CallbackHandler",
    "ContextDefaultsFilter",
    "LoggingController",
    "SecretMaskingFilter",
    "configure_logging",
]
