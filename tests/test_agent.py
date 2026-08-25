"""Agent unit tests using a scripted fake LLM (no Ollama/Qdrant needed)."""

import asyncio

import app.agent.agent as agent_mod
from app.agent import tools as tool_mod
from app.agent.agent import run_agent_sync


class FakeLLM:
    """Replays a scripted list of chat responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


def _run(coro):
    return asyncio.run(coro)


def test_calculator_tool_safe_eval():
    assert tool_mod.run_tool("calculator", {"expression": "1280*0.15"}).observation.endswith("= 192.0")
    # Unsupported / malicious expressions never execute.
    assert "Could not evaluate" in tool_mod.run_tool("calculator", {"expression": "__import__('os')"}).observation


def test_unknown_tool_is_handled():
    assert "Unknown tool" in tool_mod.run_tool("nope", {}).observation


def test_agent_uses_tool_then_answers(monkeypatch):
    # Stub retrieval so the search tool returns a known chunk.
    chunk = {
        "chunk_id": "c1",
        "doc_id": "d1",
        "text": "Annual leave is 15 days.",
        "heading_path": ["Leave"],
        "meta": {},
    }
    monkeypatch.setattr(tool_mod, "hybrid_search", lambda *a, **k: [chunk])
    monkeypatch.setattr(tool_mod, "rerank", lambda q, hits, k: hits)
    # Avoid DB lookups while formatting citations.
    monkeypatch.setattr("app.services.citation_service.get_document", lambda _id: None)

    fake = FakeLLM(
        [
            {"content": "", "tool_calls": [{"id": "1", "name": "search_knowledge_base", "arguments": {"query": "leave policy"}}]},
            {"content": "Annual leave is 15 days [1].", "tool_calls": []},
        ]
    )
    monkeypatch.setattr(agent_mod, "get_llm", lambda: fake)

    result = _run(run_agent_sync("How many leave days?"))

    assert result.answer == "Annual leave is 15 days [1]."
    assert result.steps == 2
    assert len(result.citations) == 1 and result.citations[0]["chunk_id"] == "c1"
    # Trace contains the agent's reasoning steps.
    kinds = [e["type"] for e in result.trace]
    assert "tool_call" in kinds and "observation" in kinds and "final" in kinds


def test_tool_history_is_openai_compliant(monkeypatch):
    # Regression test for a real bug found testing against the live OpenAI
    # backend: the replayed assistant/tool messages must carry the fields
    # OpenAI's Chat Completions API requires (id + type="function" on each
    # tool call, matching tool_call_id on the tool-result message) even
    # though Ollama tolerated the abbreviated shape.
    chunk = {"chunk_id": "c1", "doc_id": "d1", "text": "x", "heading_path": [], "meta": {}}
    monkeypatch.setattr(tool_mod, "hybrid_search", lambda *a, **k: [chunk])
    monkeypatch.setattr(tool_mod, "rerank", lambda q, hits, k: hits)
    monkeypatch.setattr("app.services.citation_service.get_document", lambda _id: None)

    fake = FakeLLM(
        [
            {"content": "", "tool_calls": [{"id": "call_abc123", "name": "search_knowledge_base", "arguments": {"query": "q"}}]},
            {"content": "done", "tool_calls": []},
        ]
    )
    monkeypatch.setattr(agent_mod, "get_llm", lambda: fake)

    _run(run_agent_sync("anything"))

    second_call_messages = fake.calls[1]["messages"]
    assistant_msg = next(m for m in second_call_messages if m["role"] == "assistant" and m.get("tool_calls"))
    tc = assistant_msg["tool_calls"][0]
    assert tc["id"] == "call_abc123"
    assert tc["type"] == "function"
    assert isinstance(tc["function"]["arguments"], str)  # JSON-encoded, not a raw dict

    tool_msg = next(m for m in second_call_messages if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "call_abc123"


def test_agent_respects_step_budget(monkeypatch):
    monkeypatch.setattr(tool_mod, "hybrid_search", lambda *a, **k: [])
    monkeypatch.setattr(tool_mod, "rerank", lambda q, hits, k: hits)
    from app.core.config import settings

    monkeypatch.setattr(settings, "AGENT_MAX_STEPS", 2)

    # Always asks for another tool call -> should hit the budget and finalize.
    looping = {"content": "", "tool_calls": [{"id": "x", "name": "list_documents", "arguments": {}}]}
    fake = FakeLLM([looping, looping, {"content": "Final forced answer.", "tool_calls": []}])
    monkeypatch.setattr(tool_mod.store_service, "list_documents", lambda *a, **k: [])
    monkeypatch.setattr(agent_mod, "get_llm", lambda: fake)

    result = _run(run_agent_sync("anything"))
    assert result.steps == 2
    assert result.answer == "Final forced answer."
