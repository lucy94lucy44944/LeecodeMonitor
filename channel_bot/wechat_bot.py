from .base import BaseChannel


class WechatChannel(BaseChannel):
    name = "wechat"

    def validate(self) -> bool:
        if not self.config.get("enabled", False):
            return False
        webhook_url = self.config.get("webhook_url", "")
        return bool(webhook_url)

    def send(self, message: str) -> bool:
        if not self.validate():
            print(f"[{self.name}] 渠道未启用或配置不完整，跳过发送")
            return False
        print(f"[{self.name}] 渠道待实现，消息内容长度: {len(message)}")
        return False
