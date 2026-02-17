from app.adapters.vector.qdrant import QdrantVectorStore
from app.adapters.bm25.bm25 import BM25Index
from app.services.embed_service import embed_texts
# NOTE: avoid circular import; import store_service lazily inside functions

from app.core.config import settings

_vector = None
_bm25 = BM25Index()

def get_vector():
    global _vector
    if _vector is None:
        _vector = QdrantVectorStore()
    return _vector

def rebuild_bm25():
    from app.services import store_service
    chunks = store_service.list_chunks()
    _bm25.build(chunks)

def rrf_fuse(rank_a: list[str], rank_b: list[str], k: int) -> list[str]:
    score = {}
    for r, cid in enumerate(rank_a):
        score[cid] = score.get(cid, 0.0) + 1.0 / (k + r + 1)
    for r, cid in enumerate(rank_b):
        score[cid] = score.get(cid, 0.0) + 1.0 / (k + r + 1)
    return [cid for cid, _ in sorted(score.items(), key=lambda x: x[1], reverse=True)]

def hybrid_search(query: str, topk_vector: int | None = None, topk_bm25: int | None = None, meta_filter: dict | None = None) -> list[dict]:
    topk_vector = topk_vector or settings.TOPK_VECTOR
    topk_bm25 = topk_bm25 or settings.TOPK_BM25

    # Embeddings or vector DB may be temporarily unavailable (e.g., Ollama model not pulled yet).
    # We degrade gracefully to BM25-only instead of returning 500.
    qvec = None
    vec_hits = []
    bm25_hits = []

    try:
        qvec = embed_texts([query])[0]
    except Exception:
        qvec = None

    if qvec is not None:
        try:
            vec_hits = get_vector().search(qvec, topk_vector, filter=meta_filter)
        except Exception:
            vec_hits = []

    try:
        bm25_hits = _bm25.search(query, topk_bm25)
    except Exception:
        bm25_hits = []

    vec_rank = []
    for h in vec_hits:
        if isinstance(h, dict):
            cid = h.get("chunk_id") or h.get("id") or (h.get("payload") or {}).get("chunk_id") or (h.get("payload") or {}).get("id")
        else:
            payload = getattr(h, "payload", None) or {}
            cid = getattr(h, "chunk_id", None) or getattr(h, "id", None) or payload.get("chunk_id") or payload.get("id")
        if cid is not None:
            vec_rank.append(str(cid))
    bm25_rank = [h["chunk_id"] for h in bm25_hits]
    # If one side is empty, just use the other.
    if vec_rank and bm25_rank:
        fused = rrf_fuse(vec_rank, bm25_rank, settings.RRF_K)
    else:
        fused = vec_rank or bm25_rank

    # hydrate chunks (text + metadata)
    out = []
    seen = set()
    for cid in fused:
        if cid in seen:
            continue
        seen.add(cid)
        from app.services import store_service
        c = store_service.get_chunk(cid)
        if not c:
            continue
        out.append({
            "chunk_id": cid,
            "text": c["text"],
            "doc_id": c["doc_id"],
            "heading_path": c["heading_path"],
            "meta": c["meta"],
        })
        if len(out) >= max(settings.TOPK_VECTOR, settings.TOPK_BM25):
            break
    return out
