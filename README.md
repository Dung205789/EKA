# EKA
### Local-first RAG assistant for grounded Q&A on your internal documents.

EKA is a local-first knowledge assistant that ingests internal documents (PDF/DOCX/TXT/URL/YouTube transcript), indexes them with SQLite + Qdrant, and answers questions with citations via LLMs (default: Ollama). The system is designed for privacy-first workflows while staying modular for future model/retrieval upgrades.

## Diagram (optional)
```text
Next.js UI (:3000) ──► FastAPI (:8000) ──► Ollama (:11434)
                    │
                    ├──► Qdrant (:6333)
                    └──► SQLite (data/eka.sqlite3)
```

## Tech stack
- Backend: FastAPI, Uvicorn
- Frontend: Next.js (App Router), Streamlit (legacy)
- LLM/Embeddings: Ollama (`llama3.1`, `nomic-embed-text`)
- Retrieval: Hybrid BM25 + vector (RRF fusion)
- Vector DB: Qdrant
- Storage: SQLite
- Parsing: pypdf, python-docx, BeautifulSoup, youtube-transcript-api

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
