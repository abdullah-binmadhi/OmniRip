"""Application error taxonomy used at service and pipeline boundaries."""

from __future__ import annotations

from typing import Any

from harvester.models import ErrorClass


class HarvesterError(Exception):
    """Base error carrying retry and user-facing classification metadata."""

    error_class = ErrorClass.UNKNOWN
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        retryable: bool | None = None,
        user_hint: str | None = None,
        job_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if retryable is not None:
            self.retryable = retryable
        self.user_hint = user_hint
        self.job_id = job_id
        self.details = details or {}


class ConfigError(HarvesterError):
    error_class = ErrorClass.CONFIG


class ServiceUnavailable(HarvesterError):
    error_class = ErrorClass.SERVICE_UNAVAILABLE
    retryable = True


class TransientNetwork(HarvesterError):
    error_class = ErrorClass.TRANSIENT_NETWORK
    retryable = True


class RateLimited(HarvesterError):
    error_class = ErrorClass.RATE_LIMITED
    retryable = True


class PermanentSource(HarvesterError):
    error_class = ErrorClass.PERMANENT_SOURCE


class ValidationError(HarvesterError):
    error_class = ErrorClass.VALIDATION


class DiskError(HarvesterError):
    error_class = ErrorClass.DISK


class JobCancelled(HarvesterError):
    error_class = ErrorClass.CANCELLED


__all__ = [
    "ConfigError",
    "DiskError",
    "HarvesterError",
    "JobCancelled",
    "PermanentSource",
    "RateLimited",
    "ServiceUnavailable",
    "TransientNetwork",
    "ValidationError",
]
