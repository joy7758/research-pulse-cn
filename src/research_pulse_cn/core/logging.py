"""Logging configuration helpers."""

import logging
from logging.config import dictConfig

from research_pulse_cn.core.config import Settings
from research_pulse_cn.core.request_context import current_log_context


class RequestContextFilter(logging.Filter):
    """Inject request and worker correlation ids into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = current_log_context()
        for key, default_value in context.items():
            if not hasattr(record, key):
                setattr(record, key, default_value)
        return True


def configure_logging(settings: Settings) -> None:
    """Apply a consistent console logging configuration."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s %(message)s "
                        "request_id=%(request_id)s pulse_job_id=%(pulse_job_id)s "
                        "delivery_job_id=%(delivery_job_id)s "
                        "digest_issue_id=%(digest_issue_id)s "
                        "mini_grant_id=%(mini_grant_id)s user_id=%(user_id)s "
                        "worker_role=%(worker_role)s "
                        "client_device_id=%(client_device_id)s"
                    ),
                }
            },
            "filters": {
                "request_context": {
                    "()": "research_pulse_cn.core.logging.RequestContextFilter",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                }
            },
            "root": {"handlers": ["default"], "level": settings.app_log_level},
        }
    )
