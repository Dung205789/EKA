from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.store_service import init_db
from app.services.retrieve_service import rebuild_bm25
from app.services.retrieve_service import get_vector

from app.api.routes_ingest import router as ingest_router
from app.api.routes_search import router as search_router
from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as docs_router

def create_app():
    setup_logging()
    init_db()
    # Ensure vector collection exists early (may auto-recreate on dim mismatch)
    try:
        get_vector().ensure_collection(dim=settings.EMBED_DIM)
    except Exception:
        # Don't block startup; /health will expose dependency state.
        pass
    # build bm25 from sqlite on startup (fast for MVP)
    rebuild_bm25()

    app = FastAPI(title=settings.APP_NAME)

    # Allow browser-based UIs (Next.js/Streamlit) to call the API from localhost
    from fastapi.middleware.cors import CORSMiddleware
    origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(ingest_router)
    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(docs_router)

    @app.get("/health")
    async def health():
        import httpx
        checks = {"qdrant": False, "ollama": False}
        # qdrant
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(f"{settings.VECTOR_DB_URL.rstrip('/')}/collections")
                checks["qdrant"] = r.status_code == 200
        except Exception:
            pass
        # ollama
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                checks["ollama"] = r.status_code == 200
        except Exception:
            pass

        ok = all(checks.values())
        return {"ok": ok, "app": settings.APP_NAME, "env": settings.ENV, "deps": checks}

    return app

app = create_app()
