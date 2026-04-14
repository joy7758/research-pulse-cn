"""DingTalk webhook adapter skeleton."""

import logging
from typing import Any

from research_pulse_cn.core.errors import DeliveryDispatchError

logger = logging.getLogger(__name__)


class DingTalkWebhookAdapter:
    """Skeleton adapter for DingTalk webhook delivery."""

    def send(self, payload: dict[str, Any]) -> None:
        endpoint = payload.get("endpoint")
        if not endpoint:
            raise DeliveryDispatchError("dingtalk endpoint is required", retryable=False)
        if payload.get("simulate_failure") or "fail" in str(endpoint):
            raise DeliveryDispatchError("dingtalk delivery failed", retryable=True)
        logger.info("dingtalk delivery skeleton invoked", extra={"endpoint": endpoint})
