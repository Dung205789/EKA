from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...

    # Optional streaming interface. Adapters can override for true token streaming.
    async def stream_generate(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)
