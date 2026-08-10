from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseChannel(ABC):
    name: str = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def validate(self) -> bool:
        pass

    @abstractmethod
    def send(self, message: str) -> bool:
        pass

    async def send_async(self, message: str) -> bool:
        return self.send(message)
