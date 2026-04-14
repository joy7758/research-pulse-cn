"""WeChat adapter stub."""

from typing import Any

from research_pulse_cn.core.errors import DeliveryDispatchError


class WeChatTemplateAdapter:
    """Stub adapter that reserves the WeChat integration contract."""

    def send(self, payload: dict[str, Any]) -> None:
        raise DeliveryDispatchError(
            f"wechat template delivery is not implemented for endpoint {payload.get('endpoint')}",
            retryable=False,
        )
