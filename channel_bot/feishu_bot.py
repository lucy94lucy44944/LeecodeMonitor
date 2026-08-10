import json
from typing import Any, Dict

import requests

from .base import BaseChannel


class FeishuChannel(BaseChannel):
    name = "feishu"

    def validate(self) -> bool:
        webhook_url = self.config.get("webhook_url", "")
        return bool(webhook_url)

    def _sign(self, timestamp: int, secret: str) -> str:
        import base64
        import hashlib
        import hmac

        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def send(self, message: str) -> bool:
        if not self.validate():
            print(f"[{self.name}] 配置不完整，跳过发送")
            return False

        webhook_url = self.config["webhook_url"]
        secret = self.config.get("secret", "")
        msg_type = self.config.get("msg_type", "text")

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        payload: Dict[str, Any] = {"msg_type": msg_type}

        if msg_type == "text":
            payload["content"] = {"text": message}
        elif msg_type == "post":
            payload["content"] = {
                "post": {
                    "zh_cn": {
                        "title": "LeetCode 每日监控",
                        "content": [[{"tag": "text", "text": message}]]
                    }
                }
            }

        if secret:
            import time
            timestamp = int(time.time())
            payload["timestamp"] = str(timestamp)
            payload["sign"] = self._sign(timestamp, secret)

        try:
            response = requests.post(
                url=webhook_url,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=15
            )
            result = response.json()
            code = result.get("code", -1)
            if code == 0:
                print(f"[{self.name}] 消息发送成功")
                return True
            else:
                print(f"[{self.name}] 消息发送失败: {result}")
                return False
        except Exception as e:
            print(f"[{self.name}] 发送异常: {e}")
            return False
