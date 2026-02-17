from __future__ import annotations

import re
from typing import Optional

from app.core.models import Document

# Titles produced by upload temp files look like: upload_<uuid>.<ext>
_GENERIC_TITLE_RE = re.compile(r"^upload_[0-9a-fA-F\-]{8,}(?:\.[A-Za-z0-9]{1,8})?$")


def is_generic_title(title: str | None) -> bool:
    if not title:
        return True
    t = title.strip()
    if not t:
        return True
    return bool(_GENERIC_TITLE_RE.match(t))


def _clean_line(s: str) -> str:
    s = s.strip()
    # strip common markdown bullets / headings
    s = re.sub(r"^[#>*\-\s]+", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    # drop trailing separators
    s = re.sub(r"[\-|:_]+$", "", s).strip()
    return s


def extract_title_from_text(text: str | None) -> Optional[str]:
    if not text:
        return None
    # Look at the first ~40 non-empty lines.
    lines = []
    for raw in (text or "").splitlines():
        if raw and raw.strip():
            lines.append(raw)
        if len(lines) >= 40:
            break

    if not lines:
        return None

    # Prefer first markdown heading.
    for raw in lines:
        s = raw.strip()
        if s.startswith("#"):
            cand = _clean_line(s)
            if 4 <= len(cand) <= 120:
                return cand

    # Otherwise first decent line.
    for raw in lines:
        cand = _clean_line(raw)
        if 6 <= len(cand) <= 120:
            return cand

    # Fallback: trimmed first line.
    cand = _clean_line(lines[0])
    return cand[:120] if cand else None


def best_title(doc: Document) -> str:
    """Choose the best display title for a document.

    Priority:
      1) meta.original_name (upload)
      2) meta.title (caller-supplied)
      3) doc.title (if not generic)
      4) extracted from doc.raw_text
      5) url / video_id / doc_id fallback
    """
    meta = dict(doc.meta or {})

    original = (meta.get("original_name") or meta.get("original_filename") or "").strip()
    if original:
        return original

    meta_title = (meta.get("title") or "").strip()
    if meta_title:
        return meta_title

    if not is_generic_title(doc.title):
        return (doc.title or "").strip() or doc.doc_id

    extracted = extract_title_from_text(doc.raw_text)
    if extracted:
        return extracted

    url = (meta.get("url") or "").strip()
    if url:
        return url

    vid = (meta.get("video_id") or "").strip()
    if vid:
        return f"YouTube:{vid}"

    return doc.doc_id
