import asyncio
from typing import Any, Dict, List, Type

from .base import BaseChannel
from .feishu_bot import FeishuChannel
from .dingding_bot import DingdingChannel
from .telegram_bot import TelegramChannel
from .wechat_bot import WechatChannel
from .facebook_bot import FacebookChannel

CHANNEL_REGISTRY: Dict[str, Type[BaseChannel]] = {
    FeishuChannel.name: FeishuChannel,
    DingdingChannel.name: DingdingChannel,
    TelegramChannel.name: TelegramChannel,
    WechatChannel.name: WechatChannel,
    FacebookChannel.name: FacebookChannel,
}


def register_channel(name: str, channel_cls: Type[BaseChannel]) -> None:
    CHANNEL_REGISTRY[name] = channel_cls


def get_channel(name: str, config: Dict[str, Any]) -> BaseChannel:
    if name not in CHANNEL_REGISTRY:
        raise ValueError(f"不支持的消息渠道: {name}，已注册渠道: {list(CHANNEL_REGISTRY.keys())}")
    return CHANNEL_REGISTRY[name](config)


def build_channels(channels_config: Dict[str, Any]) -> List[BaseChannel]:
    enabled_names = channels_config.get("enabled", [])
    instances: List[BaseChannel] = []
    for name in enabled_names:
        if name not in channels_config:
            print(f"[channels] 启用的渠道 '{name}' 缺少配置节点，跳过")
            continue
        try:
            ch = get_channel(name, channels_config[name])
            instances.append(ch)
        except Exception as e:
            print(f"[channels] 构建渠道 {name} 失败: {e}")
    return instances


def send_message(channels: List[BaseChannel], message: str) -> Dict[str, bool]:
    results: Dict[str, bool] = {}

    def _run_sync():
        for ch in channels:
            try:
                results[ch.name] = ch.send(message)
            except Exception as e:
                print(f"[channels] {ch.name} 发送异常: {e}")
                results[ch.name] = False

    async_channels = [ch for ch in channels if hasattr(ch, "send_async")]

    has_async_only = any(
        ch.name in ("telegram",) for ch in async_channels
    )
    if has_async_only:
        async def _run_async():
            for ch in channels:
                try:
                    results[ch.name] = await ch.send_async(message)
                except Exception as e:
                    print(f"[channels] {ch.name} 发送异常: {e}")
                    results[ch.name] = False
        asyncio.run(_run_async())
    else:
        _run_sync()

    return results
