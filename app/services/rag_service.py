from app.services.citation_service import build_context

def build_prompt(question: str, context: str, mode: str = "auto") -> str:
    # Unified assistant so UI doesn't need a mode switch.
    system = (
        "You are a knowledge assistant. Prefer and cite the provided CONTEXT (knowledge base) when it is relevant. "
        "If CONTEXT is empty or insufficient, still answer using your general knowledge (do NOT refuse). "
        "Only ask a clarifying question if the user request is truly ambiguous. "
        "Keep answers clear and practical. Cite sources like [1], [2] when using CONTEXT."
    )
    return f"""{system}

QUESTION:
{question}

CONTEXT:
{context}

ANSWER:"""
