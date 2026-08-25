"""Agentic endpoint: a tool-calling agent over the RAG stack.

- POST /agent          -> full result {answer, citations, trace, steps}
- POST /agent/stream   -> SSE stream of live trace events (plan/tool_call/
                          observation/...) ending with a `final` event.

The streaming trace is what makes the agent's reasoning observable in the UI.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.agent import run_agent, run_agent_sync, trace_to_sse

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    question: str


@router.post("")
async def agent(req: AgentRequest):
    if not (req.question or "").strip():
        raise HTTPException(status_code=400, detail="question is required")
    result = await run_agent_sync(req.question)
    return {
        "answer": result.answer,
        "citations": result.citations,
        "trace": result.trace,
        "steps": result.steps,
    }


@router.post("/stream")
async def agent_stream(req: AgentRequest):
    if not (req.question or "").strip():
        raise HTTPException(status_code=400, detail="question is required")

    async def event_gen():
        async for ev in run_agent(req.question):
            yield trace_to_sse(ev)
        yield "event: done\ndata: [DONE]\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
