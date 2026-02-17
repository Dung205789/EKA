from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

# qdrant-client is optional; REST works across versions and avoids SDK breakages.
try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as qm  # type: ignore
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore
    qm = None  # type: ignore

from app.core.config import settings
from app.adapters.vector.base import VectorStore


def _meta_filter_to_qdrant_filter(meta_filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert simple {key: value} filters into Qdrant REST filter schema."""
    if not meta_filter:
        return None
    must = []
    for k, v in meta_filter.items():
        if v is None:
            continue
        # Qdrant match supports strings, numbers, bools
        must.append({"key": k, "match": {"value": v}})
    return {"must": must} if must else None


class QdrantVectorStore(VectorStore):
    def __init__(self):
        self.collection = settings.VECTOR_COLLECTION
        self.url = settings.VECTOR_DB_URL.rstrip("/")
        # Keep the SDK client when available (useful for create_collection etc.),
        # but don't depend on its search API (it changes between versions).
        self.client = None
        if QdrantClient is not None:
            try:
                self.client = QdrantClient(url=settings.VECTOR_DB_URL)
            except Exception:
                self.client = None

    def _rest_search(self, vector: List[float], top_k: int, meta_filter: Optional[Dict[str, Any]] = None):
        payload: Dict[str, Any] = {
            "vector": vector,
            "limit": top_k,
            "with_payload": True,
        }
        qfilter = _meta_filter_to_qdrant_filter(meta_filter or {})
        if qfilter:
            payload["filter"] = qfilter

        with httpx.Client(timeout=10.0) as c:
            r = c.post(f"{self.url}/collections/{self.collection}/points/search", json=payload)
            r.raise_for_status()
            return r.json().get("result", [])

    @staticmethod
    def _normalize_hit(hit: Any) -> Dict[str, Any]:
        """Normalize Qdrant hits to a stable dict shape.

        Downstream code expects `chunk_id` to exist (used to fetch chunk text from SQLite).
        Our ingestion uses chunk_id as the Qdrant point id, so when payload doesn't contain
        chunk_id we derive it from the point id.
        """
        if isinstance(hit, dict):
            pid = hit.get("id")
            payload = hit.get("payload") or {}
            return {
                "chunk_id": str(payload.get("chunk_id") or pid),
                "id": str(pid) if pid is not None else None,
                "score": float(hit.get("score") or 0.0),
                "payload": payload,
            }

        # qdrant-client ScoredPoint
        pid = getattr(hit, "id", None)
        payload = getattr(hit, "payload", None) or {}
        score = getattr(hit, "score", 0.0)
        return {
            "chunk_id": str(payload.get("chunk_id") or pid),
            "id": str(pid) if pid is not None else None,
            "score": float(score or 0.0),
            "payload": payload,
        }

    def _rest_upsert(self, points: List[Dict[str, Any]]):
        payload = {"points": points}
        with httpx.Client(timeout=20.0) as c:
            r = c.put(
                f"{self.url}/collections/{self.collection}/points?wait=true",
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    def ensure_collection(self, dim: int):
        """Ensure the collection exists AND has the expected embedding dimension.

        Why: Qdrant will hard-fail upserts/searches when vector size mismatches.
        This commonly happens when switching embedding models between runs while
        persisting the qdrant volume.
        """

        def _get_existing_dim() -> Optional[int]:
            # Prefer REST because SDK response shapes can change between versions.
            try:
                with httpx.Client(timeout=5.0) as c:
                    r = c.get(f"{self.url}/collections/{self.collection}")
                    if r.status_code != 200:
                        return None
                    data = r.json().get("result", {})
                    vectors = (
                        data.get("config", {})
                        .get("params", {})
                        .get("vectors")
                    )

                    # Possible shapes:
                    # 1) {"size": 768, "distance": "Cosine"}
                    # 2) {"default": {"size": 768, ...}} (named vectors)
                    if isinstance(vectors, dict) and "size" in vectors:
                        return int(vectors.get("size"))
                    if isinstance(vectors, dict) and "default" in vectors and isinstance(vectors["default"], dict):
                        if "size" in vectors["default"]:
                            return int(vectors["default"].get("size"))
            except Exception:
                return None
            return None

        existing_dim = _get_existing_dim()
        if existing_dim is not None:
            if existing_dim == dim:
                return
            if settings.VECTOR_RECREATE_ON_DIM_MISMATCH:
                # Drop & recreate to unblock ingestion.
                try:
                    with httpx.Client(timeout=10.0) as c:
                        c.delete(f"{self.url}/collections/{self.collection}").raise_for_status()
                except Exception:
                    # If deletion fails, we still attempt create below (may error).
                    pass
            else:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection}' has dim={existing_dim} but expected dim={dim}. "
                    "Set VECTOR_RECREATE_ON_DIM_MISMATCH=true to auto-recreate."
                )

        # Create collection if missing (SDK is stable here; fallback to REST if needed)
        if self.client is not None and hasattr(self.client, "create_collection") and qm is not None:
            try:
                vectors_config = qm.VectorsConfigParams(size=dim, distance=qm.Distance.COSINE)
                self.client.create_collection(collection_name=self.collection, vectors_config=vectors_config)
                return
            except Exception:
                pass

        # REST fallback
        body = {"vectors": {"size": dim, "distance": "Cosine"}}
        with httpx.Client(timeout=10.0) as c:
            r = c.put(f"{self.url}/collections/{self.collection}", json=body)
            r.raise_for_status()

    def upsert(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        points = []
        for i, v, p in zip(ids, vectors, payloads):
            points.append({"id": i, "vector": v, "payload": p})

        # Prefer SDK upsert if available; else REST
        if hasattr(self.client, "upsert"):
            try:
                self.client.upsert(collection_name=self.collection, points=points, wait=True)
                return
            except Exception:
                # fall back to REST
                pass

        self._rest_upsert(points)

    def search(self, vector: List[float], top_k: int, filter: Optional[Dict[str, Any]] = None):
        # Newer SDKs: client.search(...)
        if hasattr(self.client, "search") and qm is not None:
            try:
                qfilter = None
                if filter:
                    qfilter = qm.Filter(
                        must=[qm.FieldCondition(key=k, match=qm.MatchValue(value=v)) for k, v in filter.items()]
                    )
                res = self.client.search(
                    collection_name=self.collection,
                    query_vector=vector,
                    limit=top_k,
                    with_payload=True,
                    query_filter=qfilter,
                )
                return [self._normalize_hit(h) for h in res]
            except Exception:
                pass

        # Older SDKs may not have search; use REST
        return [self._normalize_hit(h) for h in self._rest_search(vector, top_k, meta_filter=filter)]

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points that belong to a document (by payload field `doc_id`)."""
        body = {"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}}
        with httpx.Client(timeout=10.0) as c:
            r = c.post(f"{self.url}/collections/{self.collection}/points/delete?wait=true", json=body)
            r.raise_for_status()
