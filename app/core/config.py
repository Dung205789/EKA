from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "EKA"
    ENV: str = "local"
    DATA_DIR: str = "./data"
    DB_PATH: str = "./data/eka.sqlite3"

    # vector db
    VECTOR_DB_URL: str = "http://localhost:6333"
    VECTOR_COLLECTION: str = "eka_chunks"
    VECTOR_RECREATE_ON_DIM_MISMATCH: bool = True

    # embedding / rerank
    # Backends:
    # - ollama: uses Ollama /api/embeddings (local-first, no heavy python deps)
    # - openai: uses OpenAI embeddings
    # - st: uses sentence-transformers (requires optional deps: pip install .[local_ml])
    EMBED_BACKEND: str = "ollama"  # ollama|openai|st
    EMBED_MODEL: str = "BAAI/bge-m3"  # used for st
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_DIM: int = 768  # must match the chosen embedding model
    EMBED_BATCH: int = 32

    # Reranking is optional. If disabled or deps missing, system skips rerank.
    RERANK_BACKEND: str = "none"  # none|st
    RERANK_MODEL: str = "BAAI/bge-reranker-large"

    # llm
    LLM_PROVIDER: str = "ollama"  # ollama|openai
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    # ollama generation options (tune for speed)
    OLLAMA_NUM_PREDICT: int = 512
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_KEEP_ALIVE: str = "30m"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # retrieval knobs
    TOPK_VECTOR: int = 30
    TOPK_BM25: int = 30
    TOPK_RERANK: int = 10
    RRF_K: int = 60


    # CORS (for browser-based UIs)
    # Comma-separated list of allowed origins.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501,http://127.0.0.1:8501"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
