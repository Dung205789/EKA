import json
import uuid
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings
from app.adapters.llm.base import LLM

class OllamaLLM(LLM):
    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": settings.OLLAMA_KEEP_ALIVE,
                    "options": {
                        "num_predict": settings.OLLAMA_NUM_PREDICT,
                        "temperature": settings.OLLAMA_TEMPERATURE,
                        "top_p": settings.OLLAMA_TOP_P,
                    },
                },
            )
            r.raise_for_status()
            return r.json().get("response", "")

    async def stream_generate(self, prompt: str) -> AsyncIterator[str]:
        # Ollama streams newline-delimited JSON objects when stream=true.
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "options": {
                "num_predict": settings.OLLAMA_NUM_PREDICT,
                "temperature": settings.OLLAMA_TEMPERATURE,
                "top_p": settings.OLLAMA_TOP_P,
            },
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("done") is True:
                        break
                    delta = obj.get("response") or ""
                    if delta:
                        yield delta

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        # Ollama's /api/chat speaks the OpenAI-style tools schema and returns
        # structured tool_calls for models that support function calling
        # (e.g. llama3.1). Arguments come back already parsed as objects.
        payload: dict[str, Any] = {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "options": {
                "temperature": settings.OLLAMA_TEMPERATURE,
                "top_p": settings.OLLAMA_TOP_P,
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            r.raise_for_status()
            msg = (r.json() or {}).get("message", {}) or {}

        tool_calls: list[dict[str, Any]] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {}) or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"_raw": args}
            tool_calls.append(
                {
                    "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                    "name": fn.get("name", ""),
                    "arguments": args or {},
                }
            )

        return {"content": msg.get("content") or "", "tool_calls": tool_calls}
