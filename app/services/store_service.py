import sqlite3
from typing import Iterable
from app.core.config import settings
from app.core.models import Document, Chunk
# Title backfill utilities
from app.services.title_service import best_title, is_generic_title
# NOTE: avoid circular import; import get_vector lazily when needed


def init_db():
    import os
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents(
        doc_id TEXT PRIMARY KEY,
        source TEXT,
        title TEXT,
        raw_text TEXT,
        meta_json TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks(
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT,
        text TEXT,
        start_char INTEGER,
        end_char INTEGER,
        heading_json TEXT,
        meta_json TEXT,
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);")
    conn.commit()
    conn.close()

def save_document(doc: Document):
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO documents(doc_id, source, title, raw_text, meta_json) VALUES(?,?,?,?,?)",
        (doc.doc_id, doc.source, doc.title, doc.raw_text, __import__("json").dumps(doc.meta)),
    )
    conn.commit()
    conn.close()


def update_document_title(doc_id: str, title: str) -> None:
    """Update a document title without rewriting the whole row."""
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE documents SET title=? WHERE doc_id=?", (title, doc_id))
    conn.commit()
    conn.close()

def save_chunks(chunks: list[Chunk]):
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    import json
    cur.executemany(
        "INSERT OR REPLACE INTO chunks(chunk_id, doc_id, text, start_char, end_char, heading_json, meta_json) VALUES(?,?,?,?,?,?,?)",
        [
            (c.chunk_id, c.doc_id, c.text, c.start_char, c.end_char, json.dumps(c.heading_path), json.dumps(c.meta))
            for c in chunks
        ],
    )
    conn.commit()
    conn.close()

def get_document(doc_id: str) -> Document | None:
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT doc_id, source, title, raw_text, meta_json FROM documents WHERE doc_id=?", (doc_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    import json
    doc = Document(doc_id=row[0], source=row[1], title=row[2], raw_text=row[3], meta=json.loads(row[4] or "{}"))
    # Best-effort backfill: if title is a temp upload name, derive a better one from content/meta.
    try:
        if is_generic_title(doc.title):
            bt = best_title(doc)
            if bt and bt != doc.title:
                doc.title = bt
                update_document_title(doc.doc_id, bt)
    except Exception:
        pass
    return doc

def get_chunk(chunk_id: str) -> dict | None:
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT chunk_id, doc_id, text, start_char, end_char, heading_json, meta_json FROM chunks WHERE chunk_id=?", (chunk_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    import json
    return {
        "chunk_id": row[0],
        "doc_id": row[1],
        "text": row[2],
        "start_char": row[3],
        "end_char": row[4],
        "heading_path": json.loads(row[5] or "[]"),
        "meta": json.loads(row[6] or "{}"),
    }

def list_chunks(where_sql: str = "", params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    sql = "SELECT chunk_id, doc_id, text, start_char, end_char, heading_json, meta_json FROM chunks"
    if where_sql:
        sql += " WHERE " + where_sql
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    import json
    out = []
    for r in rows:
        out.append({
            "chunk_id": r[0],
            "doc_id": r[1],
            "text": r[2],
            "start_char": r[3],
            "end_char": r[4],
            "heading_path": json.loads(r[5] or "[]"),
            "meta": json.loads(r[6] or "{}"),
        })
    return out


def list_documents() -> list[Document]:
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT doc_id, source, title, raw_text, meta_json FROM documents ORDER BY rowid DESC")
    rows = cur.fetchall()
    conn.close()
    import json
    out: list[Document] = []
    for r in rows:
        doc = Document(doc_id=r[0], source=r[1], title=r[2], raw_text=r[3], meta=json.loads(r[4] or "{}"))
        try:
            if is_generic_title(doc.title):
                bt = best_title(doc)
                if bt and bt != doc.title:
                    doc.title = bt
                    update_document_title(doc.doc_id, bt)
        except Exception:
            pass
        out.append(doc)
    return out


def delete_document(doc_id: str) -> None:
    """Delete a document and all related chunks (SQLite + Qdrant)."""
    # Best-effort vector deletion
    try:
        vec = get_vector()
        if hasattr(vec, "delete_by_doc_id"):
            vec.delete_by_doc_id(doc_id)
    except Exception:
        pass

    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    cur.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
    conn.commit()
    conn.close()
