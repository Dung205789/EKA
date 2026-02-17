from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.services.ingest_service import (
    ingest_txt_path,
    ingest_docx_path,
    ingest_pdf_path,
    ingest_html_url,
    ingest_youtube,
    ingest_url_auto,
)
from app.services.pipeline_service import ingest_document

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestPathRequest(BaseModel):
    path: str
    mode: str = "auto"  # auto|general|legal


class IngestURLRequest(BaseModel):
    url: str
    mode: str = "auto"
    source: str = "auto"  # auto|html|youtube


@router.post("/path")
async def ingest_path(req: IngestPathRequest):
    path = (req.path or "").lower()
    if path.endswith(".pdf"):
        doc = ingest_pdf_path(req.path)
    elif path.endswith(".docx"):
        doc = ingest_docx_path(req.path)
    else:
        doc = ingest_txt_path(req.path)
    return ingest_document(doc, mode=req.mode or "auto")


@router.post("/url")
async def ingest_url(req: IngestURLRequest):
    from app.core.config import settings

    try:
        if (req.source or "auto") == "youtube":
            doc = ingest_youtube(req.url)
        elif (req.source or "auto") == "html":
            doc = ingest_html_url(req.url)
        else:
            doc = ingest_url_auto(req.url, data_dir=settings.DATA_DIR)
        return ingest_document(doc, mode=req.mode or "auto")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload")
async def ingest_upload(mode: str = "auto", file: UploadFile = File(...)):
    import os
    import uuid
    from pathlib import Path

    from app.core.config import settings

    os.makedirs(settings.DATA_DIR, exist_ok=True)

    # Use the original filename for display, but keep a safe tmp name on disk.
    original_name = Path(file.filename or "upload").name
    suffix = (original_name.split(".")[-1].lower() if "." in original_name else "txt")

    tmp = os.path.join(settings.DATA_DIR, f"upload_{uuid.uuid4()}.{suffix}")
    content = await file.read()
    with open(tmp, "wb") as f:
        f.write(content)

    try:
        if tmp.endswith(".pdf"):
            doc = ingest_pdf_path(tmp, title_override=original_name, meta_extra={"original_name": original_name})
        elif tmp.endswith(".docx"):
            doc = ingest_docx_path(tmp, title_override=original_name, meta_extra={"original_name": original_name})
        else:
            doc = ingest_txt_path(tmp, title_override=original_name, meta_extra={"original_name": original_name})

        # Keep temp path for debugging.
        try:
            doc.meta = dict(doc.meta or {})
            doc.meta["tmp_path"] = tmp
        except Exception:
            pass

        return ingest_document(doc, mode=mode or "auto")
    except Exception as e:
        msg = str(e)
        hint = (
            "Common causes:\n"
            "- Ollama embedding model not pulled (nomic-embed-text).\n"
            "- Qdrant collection dim mismatch after changing EMBED_DIM/model.\n"
            "Fix:\n"
            "- docker compose exec ollama ollama pull $OLLAMA_EMBED_MODEL\n"
            "- Set VECTOR_RECREATE_ON_DIM_MISMATCH=true (default) or delete qdrant volume."
        )
        raise HTTPException(status_code=503, detail={"error": msg, "hint": hint})
