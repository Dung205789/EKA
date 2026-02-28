import re
import uuid
from typing import Iterator

from app.core.models import Chunk, Document

HEADING_RE = re.compile(r"^(#+)\s+(.*)$", re.M)
ALLCAPS_RE = re.compile(r"^[A-Z][A-Z0-9\s\-_]{6,}$", re.M)


def _iter_headings(text: str) -> Iterator[tuple[int, int, str]]:
    for m in HEADING_RE.finditer(text):
        yield (m.start(), m.end(), m.group(2).strip())
    for m in ALLCAPS_RE.finditer(text):
        yield (m.start(), m.end(), m.group(0).strip())


def chunk_general(doc: Document, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    text = doc.raw_text or ""
    headings = sorted(_iter_headings(text), key=lambda x: x[0])
    segments: list[tuple[str, str, int, int]] = []

    for i, h in enumerate(headings):
        seg_start = h[0]
        seg_end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        head = h[2]
        body = text[h[1] : seg_end]
        segments.append((head, body, seg_start, seg_end))

    if not segments:
        segments = [("BODY", text, 0, len(text))]

    chunks: list[Chunk] = []
    for head, body, seg_start, _ in segments:
        heading_path = [] if head == "BODY" else [head]
        i = 0
        while i < len(body):
            j = min(i + max_chars, len(body))
            chunk_text = body[i:j].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc.doc_id,
                        text=chunk_text,
                        start_char=seg_start + i,
                        end_char=seg_start + j,
                        heading_path=heading_path,
                        meta={"source": doc.source, **(doc.meta or {})},
                    )
                )
            if j == len(body):
                break
            i = max(0, j - overlap)

    return chunks