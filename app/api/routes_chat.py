import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.retrieve_service import hybrid_search
from app.services.rerank_service import rerank
from app.services.citation_service import build_context, format_citations
from app.services.rag_service import build_prompt
from app.services.llm_factory import get_llm
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    question: str
    # Backward-compatible fields (UI no longer needs mode selection)
    mode: str | None = None
    jurisdiction: str | None = None
    status: str | None = None

@router.post("")
async def chat(req: ChatRequest):
    if not (req.question or "").strip():
        raise HTTPException(status_code=400, detail="question is required")

    try:
        hits = hybrid_search(req.question, meta_filter=None)
        top = rerank(req.question, hits, settings.TOPK_RERANK)

        ctx = build_context(top)
        prompt = build_prompt(req.question, ctx, mode="auto")

        llm = get_llm()
        answer = await llm.generate(prompt)
        cites = format_citations(top)
        return {"answer": answer, "citations": cites}
    except Exception as e:
        msg = str(e)
        hint = (
            "If you are running via Docker, ensure dependencies are up and models are pulled:\n"
            "- docker compose up -d\n"
            "- docker compose exec ollama ollama pull $OLLAMA_MODEL\n"
            "- docker compose exec ollama ollama pull $OLLAMA_EMBED_MODEL"
        )
        raise HTTPException(status_code=503, detail={"error": msg, "hint": hint})


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """Server-Sent Events (SSE) token streaming endpoint.

    Emits events:
      - meta: { citations, prompt_info }
      - token: { delta }
      - done: [DONE]
      - error: { error, hint }

    Frontends can read this via fetch() + ReadableStream.
    """
    if not (req.question or "").strip():
        raise HTTPException(status_code=400, detail="question is required")

    try:
        hits = hybrid_search(req.question, meta_filter=None)
        top = rerank(req.question, hits, settings.TOPK_RERANK)
        ctx = build_context(top)
        prompt = build_prompt(req.question, ctx, mode="auto")
        cites = format_citations(top)
        llm = get_llm()
    except Exception as e:
        msg = str(e)
        hint = (
            "Dependency error. If running via Docker, ensure containers are up and models are pulled:\n"
            "- docker compose up -d\n"
            "- docker compose exec ollama ollama pull $OLLAMA_MODEL\n"
            "- docker compose exec ollama ollama pull $OLLAMA_EMBED_MODEL"
        )
        raise HTTPException(status_code=503, detail={"error": msg, "hint": hint})

    async def event_gen():
        # Send citations up-front so UI can show sources immediately.
        meta = {"citations": cites}
        yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # Keep-alive + non-cancelled producer.
        #
        # Why this exists:
        # - Ollama can take a long time before it emits the first token (slow CPU / large prompt).
        # - Next.js' fetch (undici) has a default body timeout (~5 minutes) and will abort the
        #   proxy request if no body bytes are received for too long.
        #
        # Solution:
        # - Read Ollama's stream in a background task into a queue.
        # - While the queue is empty, emit periodic SSE ping events.
        q: asyncio.Queue[str] = asyncio.Queue()
        done = asyncio.Event()
        err: dict[str, str] = {}

        async def producer():
            try:
                async for delta in llm.stream_generate(prompt):
                    if delta:
                        await q.put(delta)
            except Exception as e:
                err["error"] = str(e)
            finally:
                done.set()

        task = asyncio.create_task(producer())

        try:
            while True:
                try:
                    delta = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: token\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Keep connection alive (UI can ignore this).
                    yield "event: ping\ndata: {}\n\n"

                    if done.is_set() and q.empty():
                        break

            if "error" in err:
                yield f"event: error\ndata: {json.dumps({'error': err['error']}, ensure_ascii=False)}\n\n"

            yield "event: done\ndata: [DONE]\n\n"
        finally:
            if not task.done():
                task.cancel()

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # For some reverse proxies; harmless locally.
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
