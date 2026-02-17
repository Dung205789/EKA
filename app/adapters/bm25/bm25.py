from rank_bm25 import BM25Okapi

class BM25Index:
    def __init__(self):
        self._bm25 = None
        self._chunk_ids = []
        self._texts = []

    def build(self, chunks: list[dict]):
        self._chunk_ids = [c["chunk_id"] for c in chunks]
        self._texts = [c["text"] for c in chunks]
        corpus = [t.lower().split() for t in self._texts]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [{"chunk_id": self._chunk_ids[i], "bm25_score": float(scores[i])} for i in ranked]
