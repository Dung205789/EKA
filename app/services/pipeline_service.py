from app.core.models import Document
from app.legal.legal_chunker import chunk_legal
from app.legal.legal_metadata import enrich_legal_metadata
from app.services.chunk_service import chunk_general
from app.services.embed_service import embed_texts
from app.services.retrieve_service import get_vector, rebuild_bm25
from app.services.store_service import save_chunks, save_document
from app.services.title_service import best_title


def _resolve_mode(doc: Document, mode: str) -> str:
    requested = (mode or "auto").strip().lower()
    if requested in {"general", "legal"}:
        return requested

    text_head = (doc.raw_text or "")[:4000].lower()
    legal_signals = ["section", "article", "whereas", "jurisdiction", "court", "plaintiff", "defendant"]
    hits = sum(1 for s in legal_signals if s in text_head)
    return "legal" if hits >= 2 else "general"


def ingest_document(doc: Document, mode: str = "auto") -> dict:
    effective_mode = _resolve_mode(doc, mode)
    warnings: list[str] = []

    doc.meta = dict(doc.meta or {})
    doc.meta["mode"] = effective_mode
    if effective_mode == "legal":
        doc.meta["legal_mode"] = True
        doc.meta = enrich_legal_metadata(doc.meta)

    doc.title = best_title(doc)
    save_document(doc)

    chunks = chunk_legal(doc) if effective_mode == "legal" else chunk_general(doc)
    save_chunks(chunks)

    vectors = []
    if chunks:
        try:
            vectors = embed_texts([c.text for c in chunks])
        except Exception as e:
            warnings.append(f"Embedding unavailable, indexed with BM25 only: {e}")

    if chunks and vectors:
        try:
            vec = get_vector()
            vec.ensure_collection(dim=len(vectors[0]))
            vec.upsert(
                ids=[c.chunk_id for c in chunks],
                vectors=vectors,
                payloads=[{"chunk_id": c.chunk_id, "doc_id": c.doc_id, **(c.meta or {})} for c in chunks],
            )
        except Exception as e:
            warnings.append(f"Vector upsert unavailable, indexed with BM25 only: {e}")

    if chunks:
        rebuild_bm25()

    return {
        "ok": True,
        "doc_id": doc.doc_id,
        "title": doc.title,
        "mode": effective_mode,
        "chunks": len(chunks),
        "warnings": warnings,
    }

