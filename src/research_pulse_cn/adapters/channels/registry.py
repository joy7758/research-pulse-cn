"""Channel adapter registry."""

from collections.abc import Mapping

from research_pulse_cn.adapters.channels.console import ConsoleChannelAdapter
from research_pulse_cn.adapters.channels.webhook import WebhookChannelAdapter
from research_pulse_cn.core.errors import DeliveryDispatchError
from research_pulse_cn.domain.contracts import ChannelAdapter
from research_pulse_cn.domain.enums import ChannelType


class ChannelAdapterRegistry:
    """Resolve outbound delivery adapters by channel."""

    def __init__(self, adapters: Mapping[ChannelType, ChannelAdapter]) -> None:
        self.adapters = dict(adapters)

    def for_channel(self, channel: ChannelType) -> ChannelAdapter:
        adapter = self.adapters.get(channel)
        if adapter is None:
            raise DeliveryDispatchError(
                f"delivery channel {channel.value} is deprecated or unsupported",
                retryable=False,
            )
        return adapter

    def adapter_name(self, channel: ChannelType) -> str:
        adapter = self.adapters.get(channel)
        if adapter is None:
            return "UnsupportedChannelAdapter"
        return type(adapter).__name__


def build_channel_registry() -> ChannelAdapterRegistry:
    console = ConsoleChannelAdapter()
    return ChannelAdapterRegistry(
        {
            ChannelType.IN_APP: console,
            ChannelType.EMAIL: console,
            ChannelType.WEBHOOK: WebhookChannelAdapter(),
        }
    )
