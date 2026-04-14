"""Logging configuration helpers."""

from logging.config import dictConfig

from research_pulse_cn.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Apply a consistent console logging configuration."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["default"], "level": settings.app_log_level},
        }
    )
