"""Optional reranking service.

Default: disabled (RERANK_BACKEND=none) to keep the base Docker image lightweight.
Enable with optional deps:
  pip install .[local_ml]
and set:
  RERANK_BACKEND=st
"""

from __future__ import annotations

from app.core.config import settings

_reranker = None


def _get_st_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder  # optional
        except Exception as e:
            raise RuntimeError(
                "sentence-transformers is not installed. Install with: pip install .[local_ml]"
            ) from e
        _reranker = CrossEncoder(settings.RERANK_MODEL)
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Return top_k candidates sorted by rerank_score.

    If reranking is disabled or not available, returns the first top_k candidates
    (preserving their current order).
    """
    if not candidates:
        return []

    backend = (settings.RERANK_BACKEND or "none").lower()
    if backend in {"none", "off", "disabled"}:
        return candidates[:top_k]

    if backend in {"st", "sentence_transformers"}:
        pairs = [[query, c.get("text", "")] for c in candidates]
        scores = _get_st_reranker().predict(pairs).tolist()
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)
        return sorted(candidates, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]

    # unknown backend => safe fallback
    return candidates[:top_k]
