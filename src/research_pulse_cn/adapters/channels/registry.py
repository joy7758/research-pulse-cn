"""Channel adapter registry."""

from collections.abc import Mapping

from research_pulse_cn.adapters.channels.console import ConsoleChannelAdapter
from research_pulse_cn.adapters.channels.dingtalk import DingTalkWebhookAdapter
from research_pulse_cn.adapters.channels.wechat import WeChatTemplateAdapter
from research_pulse_cn.domain.contracts import ChannelAdapter
from research_pulse_cn.domain.enums import ChannelType


class ChannelAdapterRegistry:
    """Resolve outbound delivery adapters by channel."""

    def __init__(self, adapters: Mapping[ChannelType, ChannelAdapter]) -> None:
        self.adapters = dict(adapters)

    def for_channel(self, channel: ChannelType) -> ChannelAdapter:
        return self.adapters[channel]


def build_channel_registry() -> ChannelAdapterRegistry:
    console = ConsoleChannelAdapter()
    return ChannelAdapterRegistry(
        {
            ChannelType.IN_APP: console,
            ChannelType.EMAIL: console,
            ChannelType.WEBHOOK: console,
            ChannelType.DINGTALK: DingTalkWebhookAdapter(),
            ChannelType.WECHAT: WeChatTemplateAdapter(),
        }
    )
