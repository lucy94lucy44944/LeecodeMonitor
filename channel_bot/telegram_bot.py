from typing import Any

from .base import BaseChannel


class TelegramChannel(BaseChannel):
    name = "telegram"

    def __init__(self, config: Any):
        super().__init__(config)
        self._bot = None

    def validate(self) -> bool:
        bot_token = self.config.get("bot_token", "")
        chat_id = self.config.get("chat_id", "")
        return bool(bot_token and chat_id and bot_token != "your bot token")

    def _get_bot(self):
        if self._bot is None:
            import telegram
            self._bot = telegram.Bot(token=self.config["bot_token"])
        return self._bot

    def send(self, message: str) -> bool:
        if not self.validate():
            print(f"[{self.name}] 配置不完整，跳过发送")
            return False
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(self.send_async(message))
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"[{self.name}] 同步发送异常: {e}")
            return False

    async def send_async(self, message: str) -> bool:
        if not self.validate():
            print(f"[{self.name}] 配置不完整，跳过发送")
            return False
        try:
            bot = self._get_bot()
            chat_id = self.config["chat_id"]
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"[{self.name}] 消息发送成功")
            return True
        except Exception as e:
            print(f"[{self.name}] 异步发送异常: {e}")
            return False
