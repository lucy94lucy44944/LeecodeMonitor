from .base import BaseChannel


class FacebookChannel(BaseChannel):
    name = "facebook"

    def validate(self) -> bool:
        if not self.config.get("enabled", False):
            return False
        token = self.config.get("page_access_token", "")
        rid = self.config.get("recipient_id", "")
        return bool(token and rid)

    def send(self, message: str) -> bool:
        if not self.validate():
            print(f"[{self.name}] 渠道未启用或配置不完整，跳过发送")
            return False
        print(f"[{self.name}] 渠道待实现，消息内容长度: {len(message)}")
        return False
