"""Embedding service with pluggable backends.

Why this exists:
- In many Docker/enterprise environments, installing sentence-transformers pulls PyTorch wheels
  that may try to download large CUDA dependencies (nvidia_* packages). This often fails on
  restricted networks.

Default behavior:
- Use Ollama embeddings (local-first, no heavy python deps).

You can switch via env:
- EMBED_BACKEND=ollama|openai|st
"""

from __future__ import annotations

from typing import List

import httpx

from app.core.config import settings


_st_model = None


def _embed_with_sentence_transformers(texts: List[str]) -> list[list[float]]:
    global _st_model
    try:
        from sentence_transformers import SentenceTransformer  # optional dependency
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers is not installed. Install with: pip install .[local_ml]"
        ) from e

    if _st_model is None:
        _st_model = SentenceTransformer(settings.EMBED_MODEL)
    vecs = _st_model.encode(texts, normalize_embeddings=True, batch_size=settings.EMBED_BATCH).tolist()
    return vecs


def _embed_with_ollama(texts: List[str]) -> list[list[float]]:
    """Robust Ollama embeddings.

    Ollama has changed embedding endpoints across versions:
    - Newer: POST /api/embed  {"model": "...", "input": ["...", ...]}
    - Older: POST /api/embeddings {"model": "...", "prompt": "..."}

    We prefer /api/embed (batch) and fall back to /api/embeddings.
    """

    texts = [t if t is not None else "" for t in texts]
    if not texts:
        return []

    base = settings.OLLAMA_BASE_URL.rstrip("/")
    model = settings.OLLAMA_EMBED_MODEL

    with httpx.Client(timeout=120) as client:
        # 1) Try newer batch endpoint first.
        try:
            r = client.post(f"{base}/api/embed", json={"model": model, "input": texts})
            if r.status_code == 200:
                data = r.json()
                embs = data.get("embeddings")
                if isinstance(embs, list) and embs and isinstance(embs[0], list):
                    return embs
        except Exception:
            # Ignore and fallback.
            pass

        # 2) Fallback: older endpoint (one prompt per request).
        out: list[list[float]] = []
        for t in texts:
            r = client.post(
                f"{base}/api/embeddings",
                json={"model": model, "prompt": t},
            )
            r.raise_for_status()
            vec = r.json().get("embedding")
            if not vec:
                raise RuntimeError("Ollama embedding response missing 'embedding'")
            out.append(vec)
        return out


def _embed_with_openai(texts: List[str]) -> list[list[float]]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    # OpenAI supports batching
    resp = client.embeddings.create(model=settings.OPENAI_EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def embed_texts(texts: List[str]) -> list[list[float]]:
    backend = (settings.EMBED_BACKEND or "ollama").lower()
    if backend in {"st", "sentence_transformers", "sentence-transformer"}:
        return _embed_with_sentence_transformers(texts)
    if backend in {"openai"}:
        return _embed_with_openai(texts)
    # default
    return _embed_with_ollama(texts)
