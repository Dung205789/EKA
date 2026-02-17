from pydantic import BaseModel, Field
from typing import Any, Literal

class Document(BaseModel):
    doc_id: str
    source: Literal["pdf","docx","html","youtube","txt","other"]
    title: str | None = None
    raw_text: str
    # Optional semantic mode label. Kept for backward/forward compatibility with earlier builds.
    mode: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    start_char: int
    end_char: int
    heading_path: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
