import os
import json
import time
from typing import Any, Dict, List

import requests
import streamlit as st


API_URL = os.getenv("EKA_API_URL", "http://api:8000").rstrip("/")


def api_get(path: str, **kwargs):
    return requests.get(f"{API_URL}{path}", timeout=30, **kwargs)


def api_post(path: str, **kwargs):
    return requests.post(f"{API_URL}{path}", timeout=300, **kwargs)


def api_delete(path: str, **kwargs):
    return requests.delete(f"{API_URL}{path}", timeout=60, **kwargs)


def list_documents() -> List[Dict[str, Any]]:
    try:
        r = api_get("/documents/")
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def ingest_file(uploaded) -> Dict[str, Any]:
    files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
    # mode omitted; backend routes automatically
    r = api_post("/ingest/upload", files=files)
    r.raise_for_status()
    return r.json()


def delete_doc(doc_id: str) -> None:
    r = api_delete(f"/documents/{doc_id}")
    r.raise_for_status()


def chat_api(question: str) -> Dict[str, Any]:
    payload = {"question": question}
    r = api_post("/chat", json=payload)
    r.raise_for_status()
    return r.json()


st.set_page_config(page_title="EKA", page_icon="💬", layout="wide")

# Hide Streamlit chrome (menu/footer) for a cleaner ChatGPT-like UI
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []  # list[dict(role, content)]


# Header (ChatGPT-like)
left, right = st.columns([8, 2])
with left:
    st.markdown("# 💬 EKA")
st.caption("Chat • Uses your ingested documents when available")

with right:
    uploaded = st.file_uploader(
        "",
        type=["pdf", "txt", "md", "docx"],
        label_visibility="collapsed",
        accept_multiple_files=False,
        help="Upload a document to add it to the knowledge base",
    )
    ingest_clicked = st.button("➕ Ingest", use_container_width=True, disabled=uploaded is None)
    if ingest_clicked and uploaded is not None:
        with st.spinner("Ingesting & indexing..."):
            try:
                out = ingest_file(uploaded)
                st.success(f"Ingested: {uploaded.name}")
                # Optional: show id for debugging
                st.session_state.last_ingest = out
            except Exception as e:
                st.error(f"Ingest failed: {e}")


# Sidebar: Knowledge base management
with st.sidebar:
    st.markdown("## 📚 Knowledge base")
    docs = list_documents()
    if not docs:
        st.caption("No documents ingested yet.")
    else:
        st.caption(f"{len(docs)} document(s)")

    # Compact list with delete actions
    for d in docs[:200]:
        doc_id = d.get("doc_id")
        title = d.get("title") or d.get("source") or doc_id
        row = st.container()
        c1, c2 = row.columns([6, 2])
        with c1:
            st.write(title)
            meta = d.get("meta") or {}
            # show small hints
            if isinstance(meta, dict) and meta.get("mode"):
                st.caption(f"mode: {meta.get('mode')}")
        with c2:
            if st.button("🗑️", key=f"del-{doc_id}"):
                try:
                    delete_doc(doc_id)
                    st.success("Deleted")
                    time.sleep(0.2)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    if st.button("🧹 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Chat area
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


user_text = st.chat_input("Ask anything…")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                out = chat_api(user_text)
                answer = out.get("answer") or out.get("text") or json.dumps(out, ensure_ascii=False)
                st.markdown(answer)

                # Optional: show sources if present
                sources = out.get("sources") or out.get("citations")
                if sources:
                    with st.expander("Sources"):
                        st.json(sources)
            except Exception as e:
                st.error(f"Chat failed: {e}")
                answer = f"(error) {e}"

    st.session_state.messages.append({"role": "assistant", "content": answer})