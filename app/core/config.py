from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EKA"
    ENV: str = "local"

    DATA_DIR: str = "./data"
    DB_PATH: str = "./data/eka.sqlite3"

    VECTOR_DB_URL: str = "http://localhost:6333"
    VECTOR_COLLECTION: str = "eka_chunks"
    VECTOR_RECREATE_ON_DIM_MISMATCH: bool = True

    EMBED_BACKEND: str = "ollama"  # ollama|openai|st
    EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBED_BATCH: int = 16
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    EMBED_DIM: int = 768
    TOPK_VECTOR: int = 8
    TOPK_BM25: int = 6
    TOPK_RERANK: int = 6
    RRF_K: int = 60

    RERANK_BACKEND: str = "none"  # none|st
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    LLM_PROVIDER: str = "ollama"  # ollama|openai
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_KEEP_ALIVE: str = "5m"
    OLLAMA_NUM_PREDICT: int = 512
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_TOP_P: float = 0.9

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501,http://127.0.0.1:8501"


settings = Settings()
