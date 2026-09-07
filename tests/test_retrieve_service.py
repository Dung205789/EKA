"""Unit tests for hybrid retrieval: RRF fusion and graceful degradation."""

from app.services import retrieve_service


def test_rrf_fuse_basic_order():
    # Two disjoint rankings: item ranked #1 in both lists should win the fusion.
    vec_rank = ["a", "b", "c"]
    bm25_rank = ["a", "c", "b"]
    fused = retrieve_service.rrf_fuse(vec_rank, bm25_rank, k=60)
    assert fused[0] == "a"
    assert set(fused) == {"a", "b", "c"}


def test_rrf_fuse_rewards_items_present_in_both_lists():
    # "shared" appears in both rankings (low in each); "vector_only" is #1 in one
    # list but absent from the other. RRF should still favor consensus.
    vec_rank = ["vector_only", "shared"]
    bm25_rank = ["other", "shared"]
    fused = retrieve_service.rrf_fuse(vec_rank, bm25_rank, k=1)
    assert fused[0] == "shared"


def test_rrf_fuse_empty_inputs():
    assert retrieve_service.rrf_fuse([], [], k=60) == []


def test_hybrid_search_falls_back_to_bm25_when_embedding_unavailable(monkeypatch):
    # Simulate the embedding backend being down (e.g. Ollama model not pulled).
    def _raise(*_a, **_k):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(retrieve_service, "embed_texts", _raise)
    monkeypatch.setattr(
        retrieve_service._bm25, "search", lambda query, topk: [{"chunk_id": "c1"}, {"chunk_id": "c2"}]
    )

    chunk_rows = {
        "c1": {"chunk_id": "c1", "doc_id": "d1", "text": "chunk one", "heading_path": [], "meta": {}},
        "c2": {"chunk_id": "c2", "doc_id": "d1", "text": "chunk two", "heading_path": [], "meta": {}},
    }
    monkeypatch.setattr(
        "app.services.store_service.get_chunk", lambda cid: chunk_rows.get(cid)
    )

    results = retrieve_service.hybrid_search("any query", topk_vector=5, topk_bm25=5)

    assert [r["chunk_id"] for r in results] == ["c1", "c2"]
    assert all(r["text"] for r in results)


def test_hybrid_search_returns_empty_when_both_backends_empty(monkeypatch):
    monkeypatch.setattr(retrieve_service, "embed_texts", lambda *_a, **_k: [[0.0]])
    monkeypatch.setattr(retrieve_service, "get_vector", lambda: type("V", (), {"search": lambda self, *a, **k: []})())
    monkeypatch.setattr(retrieve_service._bm25, "search", lambda query, topk: [])

    assert retrieve_service.hybrid_search("any query") == []
