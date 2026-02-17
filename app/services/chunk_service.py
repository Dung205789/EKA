import re, uuid
from app.core.models import Document, Chunk

# markdown-ish headings, plus ALLCAPS headings heuristic
MD_HEAD_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
ALLCAPS_HEAD_RE = re.compile(r"^(?=.{4,80}$)[A-Z0-9][A-Z0-9\s\-,:()]{3,}$", re.MULTILINE)

def _iter_headings(text: str):
    for m in MD_HEAD_RE.finditer(text):
        yield (m.start(), m.end(), m.group(2).strip())
    for m in ALLCAPS_HEAD_RE.finditer(text):
        yield (m.start(), m.end(), m.group(0).strip())

def chunk_general(doc: Document, max_chars=1200, overlap=150) -> list[Chunk]:
    text = doc.raw_text
    headings = sorted(_iter_headings(text), key=lambda x: x[0])
    # Build segments between headings
    segments = []
    if not headings:
        headings = []
    for i, h in enumerate(headings):
        start = h[0]
        end = headings[i+1][0] if i+1 < len(headings) else len(text)
        head = h[2]
        body = text[h[1]:end]
        segments.append((head, body, h[0], end))
    if not segments:
        segments = [("BODY", text, 0, len(text))]

    chunks: list[Chunk] = []
    for head, body, seg_start, seg_end in segments:
        heading_path = [] if head == "BODY" else [head]
        i = 0
        while i < len(body):
            j = min(i + max_chars, len(body))
            chunk_text = body[i:j].strip()
            if chunk_text:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    start_char=seg_start + i,
                    end_char=seg_start + j,
                    heading_path=heading_path,
                    meta={"source": doc.source, **doc.meta},
                ))
            if j == len(body):
                break
            i = max(0, j - overlap)
    return chunks
