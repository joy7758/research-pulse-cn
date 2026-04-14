"""Console delivery adapter."""

import logging
from typing import Any

from research_pulse_cn.core.errors import DeliveryDispatchError

logger = logging.getLogger(__name__)


class ConsoleChannelAdapter:
    """Log delivery payloads instead of sending them to an external system."""

    def send(self, payload: dict[str, Any]) -> None:
        if payload.get("simulate_failure"):
            raise DeliveryDispatchError("console adapter simulated failure", retryable=True)
        logger.info("console delivery dispatched", extra={"payload": payload})
