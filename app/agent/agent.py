"""A small tool-calling (ReAct-style) agent over the existing RAG stack.

Loop:
    1. Ask the LLM what to do next, exposing the tool schemas.
    2. If it requests tool calls -> execute them, feed observations back, repeat.
    3. If it answers directly -> we have a final answer.
    4. Stop after AGENT_MAX_STEPS to bound cost/latency.

Every step is emitted as a structured trace event, which the API streams to the
UI. Citations are aggregated from every ``search_knowledge_base`` call so the
final answer can be grounded in (and reference) the user's documents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.agent import tools as tool_mod
from app.core.config import settings
from app.services.citation_service import format_citations
from app.services.llm_factory import get_llm

SYSTEM_PROMPT = (
    "You are EKA, an agentic knowledge assistant. You can call tools to gather "
    "evidence before answering.\n"
    "Guidelines:\n"
    "- For anything that might be in the user's documents, call "
    "search_knowledge_base (decompose complex questions into multiple focused "
    "searches).\n"
    "- Use list_documents to discover what is available; use calculator for arithmetic.\n"
    "- Ground your answer in retrieved passages and cite them as [1], [2] matching "
    "the order they were retrieved. If the knowledge base lacks the answer, say so "
    "and answer from general knowledge, clearly flagging that it is not from the documents.\n"
    "- Do not call tools once you have enough evidence; just answer."
)


@dataclass
class AgentResult:
    answer: str
    citations: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    steps: int = 0


def _event(kind: str, **data: Any) -> dict[str, Any]:
    return {"type": kind, **data}


async def run_agent(question: str) -> AsyncIterator[dict[str, Any]]:
    """Run the agent, yielding trace events; the last event is ``final``."""
    llm = get_llm()
    schemas = tool_mod.tool_schemas()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Aggregated retrieved chunks, de-duplicated, preserving first-seen order so
    # citation indices stay stable across multiple searches.
    collected: list[dict] = []
    seen_chunks: set[str] = set()
    trace: list[dict] = []

    def emit(ev: dict[str, Any]) -> dict[str, Any]:
        trace.append(ev)
        return ev

    answer = ""
    steps = 0
    max_steps = max(1, settings.AGENT_MAX_STEPS)

    for step in range(1, max_steps + 1):
        steps = step
        try:
            resp = await llm.chat(messages, tools=schemas)
        except Exception as e:
            yield emit(_event("error", message=str(e)))
            return

        tool_calls = resp.get("tool_calls") or []
        content = resp.get("content") or ""

        if not tool_calls:
            # Model decided to answer.
            answer = content
            yield emit(_event("thought", step=step, text="Enough evidence — answering.", final=True))
            break

        yield emit(
            _event(
                "plan",
                step=step,
                tool_calls=[{"name": tc["name"], "arguments": tc["arguments"]} for tc in tool_calls],
            )
        )

        # Record the assistant's tool-call turn so the model has full history.
        # OpenAI's Chat Completions API requires each tool call to carry a
        # stable "id" + "type": "function" here, and the matching tool-result
        # message below to echo that id back as "tool_call_id" — Ollama is
        # lenient about this shape, which is why the gap went unnoticed until
        # tested against the real OpenAI backend.
        messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            call_id, name, args = tc["id"], tc["name"], tc["arguments"]
            yield emit(_event("tool_call", step=step, name=name, arguments=args))

            result = tool_mod.run_tool(name, args)

            for ch in result.chunks:
                cid = ch.get("chunk_id")
                if cid and cid not in seen_chunks:
                    seen_chunks.add(cid)
                    collected.append(ch)

            yield emit(
                _event(
                    "observation",
                    step=step,
                    name=name,
                    summary=result.observation[:500],
                    n_chunks=len(result.chunks),
                )
            )
            messages.append({"role": "tool", "tool_call_id": call_id, "content": result.observation})

    else:
        # Loop exhausted without a direct answer: force a final answer with no tools.
        try:
            messages.append(
                {
                    "role": "user",
                    "content": "Stop searching and give your best final answer now, with citations.",
                }
            )
            resp = await llm.chat(messages, tools=None)
            answer = resp.get("content") or ""
            yield emit(_event("thought", step=steps, text="Step budget reached — finalizing.", final=True))
        except Exception as e:
            yield emit(_event("error", message=str(e)))
            return

    citations = format_citations(collected)
    yield emit(_event("final", answer=answer, citations=citations, steps=steps))


async def run_agent_sync(question: str) -> AgentResult:
    """Collect the full agent run into a single result (non-streaming)."""
    result = AgentResult(answer="")
    async for ev in run_agent(question):
        if ev["type"] == "final":
            result.answer = ev["answer"]
            result.citations = ev["citations"]
            result.steps = ev["steps"]
        elif ev["type"] == "error":
            result.answer = result.answer or f"[agent error] {ev['message']}"
        result.trace.append(ev)
    return result


def trace_to_sse(ev: dict[str, Any]) -> str:
    """Serialize a trace event as a Server-Sent Event."""
    return f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
