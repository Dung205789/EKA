import re, uuid
from app.core.models import Document, Chunk

# Identify common legal headings: I., II., A., 1., (a), (1)
LEGAL_HEAD_RE = re.compile(
    r"^(?:\s*)(?P<h>("
    r"(?:[IVXLCDM]+\.)|"
    r"(?:[A-Z]\.)|"
    r"(?:\d+\.)|"
    r"(?:\([a-z]\))|"
    r"(?:\(\d+\))"
    r"))\s+(?P<title>.+)$",
    re.MULTILINE
)

def _level(token: str) -> int:
    token = token.strip()
    if re.fullmatch(r"[IVXLCDM]+\.", token): return 1
    if re.fullmatch(r"[A-Z]\.", token): return 2
    if re.fullmatch(r"\d+\.", token): return 3
    if re.fullmatch(r"\([a-z]\)", token): return 4
    if re.fullmatch(r"\(\d+\)", token): return 5
    return 9

def chunk_legal(doc: Document, max_chars=1400, overlap=200) -> list[Chunk]:
    text = doc.raw_text
    matches = list(LEGAL_HEAD_RE.finditer(text))
    if not matches:
        from app.services.chunk_service import chunk_general
        return chunk_general(doc)

    chunks: list[Chunk] = []
    stack: list[tuple[int,str]] = []  # (level, heading)
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        token = m.group("h").strip()
        title = m.group("title").strip()
        head = f"{token} {title}"
        lvl = _level(token)

        while stack and stack[-1][0] >= lvl:
            stack.pop()
        stack.append((lvl, head))
        heading_path = [h for _, h in stack]

        body = text[m.end():end].strip()
        if not body:
            continue

        j = 0
        while j < len(body):
            k = min(j + max_chars, len(body))
            part = body[j:k].strip()
            if part:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    text=part,
                    start_char=start + j,
                    end_char=start + k,
                    heading_path=heading_path,
                    meta={"legal_mode": True, "source": doc.source, **doc.meta},
                ))
            if k == len(body): break
            j = max(0, k - overlap)
    return chunks
