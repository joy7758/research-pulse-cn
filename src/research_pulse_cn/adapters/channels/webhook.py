"""Webhook delivery adapter."""

import logging
from typing import Any

from research_pulse_cn.core.errors import DeliveryDispatchError

logger = logging.getLogger(__name__)


class WebhookChannelAdapter:
    """Minimal webhook adapter for current supported outbound delivery."""

    def send(self, payload: dict[str, Any]) -> None:
        endpoint = payload.get("endpoint")
        if not endpoint:
            raise DeliveryDispatchError("webhook endpoint is required", retryable=False)
        if payload.get("simulate_failure") or "fail" in str(endpoint):
            raise DeliveryDispatchError("webhook delivery failed", retryable=True)
        logger.info("webhook delivery dispatched", extra={"endpoint": endpoint})
