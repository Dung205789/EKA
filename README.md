# EKA — Enterprise AI Knowledge Assistant (Local‑first RAG)
**General + Legal Intelligence • Hybrid Retrieval (BM25 + Vector) • Streaming Chat UI**

EKA là một **knowledge assistant chạy local-first**: ingest tài liệu nội bộ (PDF/DOCX/TXT/URL/YouTube transcript), index vào **SQLite + Qdrant**, truy hồi **hybrid (BM25 + vector) + RRF**, và trả lời bằng **LLM (mặc định: Ollama)** kèm **citations**.

> Mục tiêu dự án: demo một hệ RAG “end‑to‑end” có UI giống ChatGPT, chạy được hoàn toàn local để bảo vệ dữ liệu, đồng thời vẫn đủ modular để thay LLM/embedding/rerank.

---

## Highlights
- **Local-first**: dữ liệu và index nằm trên máy (SQLite + Qdrant).  
- **Hybrid retrieval**: BM25 + Vector, fuse bằng **Reciprocal Rank Fusion (RRF)**.
- **Streaming chat (SSE)**: UI nhận token theo thời gian thực; backend có **keep-alive ping** để tránh timeout khi model trả token chậm.
- **Ingest đa nguồn**: file upload, local path, URL (auto detect), **YouTube transcript**.
- **Auto mode (general vs legal)**: backend tự chọn chunker phù hợp để UI không cần “mode selector”.
- **Graceful degradation**: nếu embeddings/vector tạm lỗi (model chưa pull), hệ vẫn có thể fallback BM25 thay vì “hard fail”.
- **One-command E2E reset**: script tự down volumes → build → up → wait health.

---

## Tech stack
- **Backend**: FastAPI + Uvicorn
- **Vector DB**: Qdrant
- **LLM & Embeddings (default)**: Ollama (`llama3.1`, `nomic-embed-text`)
- **BM25**: `rank-bm25`
- **Parsers**: `pypdf`, `python-docx`, `beautifulsoup4`, `youtube-transcript-api`
- **UI**:
  - **Next.js (App Router)** “ChatGPT-like” + streaming
  - Streamlit UI (legacy)

---

## Kiến trúc (high-level)
```
Next.js UI (:3000)  ──SSE──►  FastAPI (:8000)  ──►  Ollama (:11434)
                            │
                            ├──► Qdrant (:6333)  (vector)
                            └──► SQLite (documents + chunks + BM25 corpus)
```

---

## Quick start (Docker) — chạy end-to-end
**Yêu cầu**: Docker Desktop + Docker Compose v2

### Option A — 1 lệnh (khuyến nghị)
**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_reset.ps1
```

**Linux/macOS**
```bash
./scripts/e2e_reset.sh
```

### Option B — chạy compose thủ công
```bash
cd docker
docker compose up -d --build
```

### Mở UI / Tools
- **Web UI (Next.js):** http://localhost:3000
- **Streamlit UI:** http://localhost:8501
- **API Swagger:** http://localhost:8000/docs
- **Qdrant dashboard:** http://localhost:6333/dashboard

### Health check
```bash
curl http://localhost:8000/health
```

---

## Cách dùng (workflow)
### 1) Ingest tài liệu
Bạn có thể ingest bằng UI (Documents page) hoặc qua API.
<img width="1918" height="913" alt="image" src="https://github.com/user-attachments/assets/89b923ae-0ffc-4b62-92f0-ce2d274a468f" />

**Upload file**
```bash
curl -X POST "http://localhost:8000/ingest/upload?mode=auto" \
  -F "file=@./data/sample.pdf"
```

**Ingest local path (server-side)**
```bash
curl -X POST http://localhost:8000/ingest/path \
  -H "Content-Type: application/json" \
  -d '{"path":"./data/sample.pdf","mode":"auto"}'
```

**Ingest URL (auto detect HTML/PDF/DOCX/TXT/MD/YouTube)**
```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","mode":"auto","source":"auto"}'
```

**Ingest YouTube transcript**
```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEOID","mode":"auto","source":"youtube"}'
```

### 2) Hỏi đáp / Chat
<img width="1919" height="884" alt="image" src="https://github.com/user-attachments/assets/99dae131-a5e3-499e-8f20-6f7d78c6efc7" />

**Chat (non-stream)**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Tóm tắt 5 ý chính trong tài liệu vừa ingest"}'
```

**Chat streaming (SSE)**
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question":"Tạo checklist triển khai dựa trên tài liệu"}'
```

### 3) Search (hybrid retrieval)
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"điều kiện hiệu lực hợp đồng","mode":"legal","jurisdiction":"Illinois"}'
```

---


## Roadmap (ý tưởng mở rộng)
- Incremental BM25 update (thay vì rebuild toàn bộ mỗi lần ingest)
- Metadata extraction mạnh hơn cho legal docs (jurisdiction/date/status)
- Auth/multi-tenant + namespaces per collection
- Better PDF table/layout parsing (quality cho tài liệu scan)
