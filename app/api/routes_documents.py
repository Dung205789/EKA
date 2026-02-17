from fastapi import APIRouter, HTTPException
from app.services.store_service import get_document, get_chunk, list_documents, delete_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
async def list_docs():
    docs = list_documents()
    # Provide an `id` field for frontend convenience (legacy UI expects it).
    out = []
    for d in docs:
        payload = d.model_dump()
        payload["id"] = payload.get("doc_id")
        # raw_text can be large; UI doesn't need it for listing.
        payload.pop("raw_text", None)
        out.append(payload)
    return out

@router.get("/{doc_id}")
async def get_doc(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump()


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    try:
        delete_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "doc_id": doc_id}

@router.get("/chunk/{chunk_id}")
async def get_chunk_api(chunk_id: str):
    c = get_chunk(chunk_id)
    if not c:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return c
