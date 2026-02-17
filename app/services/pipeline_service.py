from app.core.models import Document
from app.services.title_service import best_title
from app.services.store_service import save_document, save_chunks
from app.services.embed_service import embed_texts
from app.services.retrieve_service import get_vector, rebuild_bm25
from app.services.chunk_service import chunk_general
from app.legal.legal_chunker import chunk_legal
from app.legal.legal_metadata import enrich_legal_metadata


def _auto_mode(text: str) -> str:
    """Heuristic detection between legal vs general.

    Goal: UI has no mode selector, but we still pick the best chunker.
    """
    t = (text or "").lower()
    markers = [
        "điều ", "khoản ", "mục ", "chương ", "luật ", "nghị định", "thông tư",
        "quyết định", "căn cứ", "ban hành", "hiệu lực", "hợp đồng", "phụ lục",
        "tòa án", "bộ luật",
    ]
    score = sum(1 for m in markers if m in t)
    return "legal" if score >= 2 else "general"

def ingest_document(doc: Document, mode: str = "auto") -> dict:
    # Normalize the title early so UI and citations show human-friendly names.
    try:
        doc.title = best_title(doc)
        doc.meta = dict(doc.meta or {})
        doc.meta["display_title"] = doc.title
    except Exception:
        pass

    # 1) decide mode (auto-detect if needed)
    if mode == "auto":
        mode = _auto_mode(doc.raw_text)
    # Store mode hint in metadata (Document model has no `mode` field)
    try:
        doc.meta["mode"] = mode
    except Exception:
        pass
    # keep mode visible in document listing
    try:
        doc.meta = dict(doc.meta or {})
        doc.meta["mode"] = mode
    except Exception:
        pass

    # 2) chunk
    if mode == "legal":
        # enrich doc meta for legal
        doc.meta = enrich_legal_metadata(doc.meta)
        chunks = chunk_legal(doc)
    else:
        chunks = chunk_general(doc)

    # 2) persist document (after meta enrichment)
    save_document(doc)

    # 3) persist chunks
    save_chunks(chunks)

    # 4) embeddings + upsert vector
    vecs = embed_texts([c.text for c in chunks])
    if vecs:
        # Ensure the vector collection exists before upsert.
        # Otherwise Qdrant returns 404 for /collections/<name>/points.
        get_vector().ensure_collection(dim=len(vecs[0]))
    ids = [c.chunk_id for c in chunks]
    payloads = []
    for c in chunks:
        payloads.append({
            "doc_id": c.doc_id,
            "text": c.text,  # helpful for debugging in Qdrant UI
            "heading_path": c.heading_path,
            **(c.meta or {}),
        })
    if vecs:
        get_vector().upsert(ids, vecs, payloads)

    # 5) rebuild bm25 (simple approach). For large corpora, move to incremental update.
    rebuild_bm25()

    # Don't expose internal routing/mode to the UI.
    return {"doc_id": doc.doc_id, "chunks": len(chunks)}
