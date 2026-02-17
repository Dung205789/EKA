import json
from typing import AsyncIterator

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
