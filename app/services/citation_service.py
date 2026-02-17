from __future__ import annotations

from app.services.store_service import get_document


def format_citations(chunks: list[dict]) -> list[dict]:
    """Return UI-friendly citation payloads.

    Important: include `title` so the frontend doesn't fall back to UUIDs.
    """
    cites: list[dict] = []
    doc_cache: dict[str, tuple[str | None, str | None]] = {}

    for i, c in enumerate(chunks, 1):
        doc_id = c.get("doc_id")
        title = None
        source = None
        if doc_id:
            if doc_id in doc_cache:
                title, source = doc_cache[doc_id]
            else:
                d = get_document(doc_id)
                title = getattr(d, "title", None) if d else None
                source = getattr(d, "source", None) if d else None
                doc_cache[doc_id] = (title, source)

        cites.append(
            {
                "ref": i,
                "chunk_id": c.get("chunk_id"),
                "doc_id": doc_id,
                "title": title,
                "source": source,
                "heading_path": c.get("heading_path", []),
                "score": c.get("rerank_score"),
                "snippet": (c.get("text") or "")[:600],
            }
        )
    return cites


def build_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        head = " > ".join(c.get("heading_path") or [])
        if head:
            blocks.append(f"[{i}] ({head})\n{c['text']}")
        else:
            blocks.append(f"[{i}]\n{c['text']}")
    return "\n\n".join(blocks)
