from fastapi import APIRouter
from pydantic import BaseModel
from app.services.retrieve_service import hybrid_search
from app.services.rerank_service import rerank
from app.core.config import settings

router = APIRouter(prefix="/search", tags=["search"])

class SearchRequest(BaseModel):
    query: str
    mode: str = "general"
    jurisdiction: str | None = None
    status: str | None = None

@router.post("")
async def search(req: SearchRequest):
    meta_filter = {}
    if req.mode == "legal":
        meta_filter["legal_mode"] = True
        if req.jurisdiction:
            meta_filter["jurisdiction"] = req.jurisdiction
        if req.status:
            meta_filter["status"] = req.status
    hits = hybrid_search(req.query, meta_filter=meta_filter if meta_filter else None)
    top = rerank(req.query, hits, settings.TOPK_RERANK)
    return {"results": top}
