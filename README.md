# EKA
### Local-first RAG assistant for grounded Q&A on your internal documents.

EKA is a local-first knowledge assistant that ingests internal documents (PDF/DOCX/TXT/URL/YouTube transcript), indexes them with SQLite + Qdrant, and answers questions with citations via LLMs (default: Ollama). The system is designed for privacy-first workflows while staying modular for future model/retrieval upgrades.
<img width="1919" height="801" alt="image" src="https://github.com/user-attachments/assets/ccc8699e-9942-41fb-b6ba-ecc2b77602b7" />
<img width="1919" height="913" alt="image-1" src="https://github.com/user-attachments/assets/d2f21da2-2ffb-4884-9854-adebcdc0ed00" />

## Diagram
```text
Next.js UI (:3000) ──► FastAPI (:8000) ──► Ollama (:11434)
                    │
                    ├──► Qdrant (:6333)
                    └──► SQLite (data/eka.sqlite3)
```

## Agentic mode
Beyond single-shot RAG, EKA exposes a **tool-calling agent** that decides _how_ to answer:
- **Tools**: `search_knowledge_base` (hybrid retrieval + rerank), `list_documents`, `calculator` — registered in `app/agent/tools.py`.
- **ReAct loop** (`app/agent/agent.py`): the LLM plans → calls tools → observes → repeats, bounded by `AGENT_MAX_STEPS`. Complex questions are decomposed into multiple focused searches; citations are aggregated across calls.
- **Observable reasoning**: every step (plan / tool_call / observation / final) is emitted as a structured trace.
- **Endpoints**:
  - `POST /agent` → `{ answer, citations, trace, steps }`
  - `POST /agent/stream` → SSE stream of live trace events
- **Local-first**: runs on Ollama function-calling models (e.g. `llama3.1`); the same code path works with OpenAI.

```text
question ─► [plan] ─► search_knowledge_base ─► [observe] ─┐
              ▲                                            │
              └──────────── (loop ≤ AGENT_MAX_STEPS) ◄─────┘
                                  └─► grounded answer + citations
```

## Tech stack
- Backend: FastAPI, Uvicorn
- Frontend: Next.js (App Router) is the primary UI; Streamlit is kept as a legacy/debug UI
- LLM/Embeddings: Ollama (`llama3.1`, `nomic-embed-text`), OpenAI-compatible backend also supported
- Retrieval: Hybrid BM25 + vector (RRF fusion), with graceful degradation to BM25-only if embeddings/vector DB are unavailable
- Cross-encoder reranking (`RERANK_BACKEND=st`) is implemented but **off by default** (`none`) to keep the default install light; enable it via `.env` if you install the `local_ml` extra
- Vector DB: Qdrant
- Storage: SQLite
- Parsing: pypdf, python-docx, BeautifulSoup, youtube-transcript-api

## Evaluation
The agent is evaluated end-to-end against a 15-case suite (`eval/cases.jsonl`) spanning grounded factual QA, tool selection, multi-hop questions, and out-of-scope refusal — run with a real OpenAI backend via `python eval/run_eval.py`. Latest results (`eval/report.md`):

| Metric | Result |
|---|---|
| Runtime errors | 0/15 |
| Keyword grounding accuracy | 15/15 (100%) |
| Tool-selection accuracy | 14/14 (100%) |
| Out-of-scope flagging rate | 1/1 (100%) |
| Citation presence on KB questions | 12/12 (100%) |
| Latency (p50 / p95) | 2983ms / 14810ms |

## Installation instructions for users
### Option A: Docker (recommended)
1. Install Docker Desktop (Compose v2).
2. Run:
   ```bash
   cd docker
   docker compose up -d --build
   ```
3. Open:
   - Web UI: http://localhost:3000
   - Streamlit UI: http://localhost:8501
   - API docs: http://localhost:8000/docs
4. Pull required models:
   ```bash
   docker exec docker-ollama-1 ollama pull llama3.1
   docker exec docker-ollama-1 ollama pull nomic-embed-text
   ```

### Option B: Local run
1. Install Python 3.11+ and Node 20+.
2. Install backend dependencies from `pyproject.toml`.
3. Start backend on port 8000.
4. Start frontend in `web/` on port 3000.

## Installation instructions for developers
1. Fork and clone the repo.
2. Create virtual env and install backend deps.
3. Configure environment variables.
4. Start dependencies (Qdrant + Ollama).
5. Run tests:
   ```bash
   pytest -q
   ```
6. Run frontend:
   ```bash
   cd web
   npm install
   npm run dev
   ```

## Contributor expectations
- Keep PRs focused and reviewable.
- Add/update tests for non-trivial changes.
- Preserve local-first and backward-compatible API behavior.
- Document behavioral/config changes in README or PR notes.
