"""Tools the agent can call.

Each tool exposes:
  - an OpenAI/Ollama-style JSON schema (so the LLM knows how to call it), and
  - an executor that runs the tool and returns a ``ToolResult``.

The knowledge-base search tool also surfaces the chunks it retrieved so the
agent loop can aggregate citations across multiple searches.
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.config import settings
from app.services.citation_service import build_context
from app.services.rerank_service import rerank
from app.services.retrieve_service import hybrid_search
from app.services import store_service


@dataclass
class ToolResult:
    # Human/LLM-readable observation fed back into the conversation.
    observation: str
    # Chunks retrieved by this call (only search tools populate this).
    chunks: list[dict] = field(default_factory=list)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: Callable[..., ToolResult]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #

def _search_knowledge_base(query: str, top_k: int | None = None) -> ToolResult:
    top_k = top_k or settings.TOPK_RERANK
    hits = hybrid_search(query, meta_filter=None)
    top = rerank(query, hits, top_k)
    if not top:
        return ToolResult(observation=f"No knowledge-base results for: {query!r}.", chunks=[])
    context = build_context(top)
    return ToolResult(
        observation=f"Top {len(top)} passages for {query!r}:\n{context}",
        chunks=top,
    )


def _list_documents() -> ToolResult:
    docs = store_service.list_documents()
    if not docs:
        return ToolResult(observation="The knowledge base is empty (no documents ingested).")
    lines = [f"- {d.title or d.doc_id} (source={d.source}, id={d.doc_id})" for d in docs[:50]]
    return ToolResult(observation=f"{len(docs)} document(s) in the knowledge base:\n" + "\n".join(lines))


# Safe arithmetic evaluator (no eval/builtins). Supports + - * / // % ** and unary -.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


def _calculator(expression: str) -> ToolResult:
    try:
        value = _eval_node(ast.parse(expression, mode="eval"))
        return ToolResult(observation=f"{expression} = {value}")
    except Exception:
        return ToolResult(observation=f"Could not evaluate expression: {expression!r}.")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

REGISTRY: dict[str, Tool] = {
    "search_knowledge_base": Tool(
        name="search_knowledge_base",
        description=(
            "Search the user's private knowledge base (ingested documents) with a "
            "natural-language query. Use this for any question that may be answered "
            "by the user's documents. Call multiple times with different queries to "
            "gather evidence for multi-part questions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A focused search query.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Optional max passages to return.",
                },
            },
            "required": ["query"],
        },
        run=_search_knowledge_base,
    ),
    "list_documents": Tool(
        name="list_documents",
        description="List the documents currently available in the knowledge base.",
        parameters={"type": "object", "properties": {}},
        run=lambda **_: _list_documents(),
    ),
    "calculator": Tool(
        name="calculator",
        description="Evaluate a basic arithmetic expression (e.g. '1280*0.15').",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate.",
                }
            },
            "required": ["expression"],
        },
        run=lambda expression="", **_: _calculator(expression),
    ),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [t.schema() for t in REGISTRY.values()]


def run_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
    tool = REGISTRY.get(name)
    if tool is None:
        return ToolResult(observation=f"Unknown tool: {name!r}.")
    try:
        return tool.run(**(arguments or {}))
    except TypeError as e:
        return ToolResult(observation=f"Invalid arguments for {name}: {e}")
    except Exception as e:  # never let a tool crash the loop
        return ToolResult(observation=f"Tool {name} failed: {e}")
