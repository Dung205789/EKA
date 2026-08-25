from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

class LLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        ...

    # Optional streaming interface. Adapters can override for true token streaming.
    async def stream_generate(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Multi-turn chat with optional tool (function) calling.

        Returns a normalized dict:
            {"content": str, "tool_calls": [{"id": str, "name": str, "arguments": dict}]}

        Default fallback (for adapters without native tool support): flatten the
        conversation into a single prompt and call ``generate``. ``tool_calls`` is
        always empty in that case, so the agent will simply answer directly.
        """
        prompt_parts: list[str] = []
        for m in messages:
            role = (m.get("role") or "user").upper()
            content = m.get("content") or ""
            prompt_parts.append(f"{role}: {content}")
        prompt_parts.append("ASSISTANT:")
        content = await self.generate("\n".join(prompt_parts))
        return {"content": content, "tool_calls": []}
