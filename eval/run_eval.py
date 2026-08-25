"""EKA agent evaluation harness.

Ingests the 3 sample documents under data/test_samples/, then runs every
question in eval/cases.jsonl through the real /agent endpoint (in-process,
via FastAPI's TestClient — real retrieval + real LLM calls, no mocking).

Scoring is deterministic and keyword/trace-based, not an LLM judge: for a
small fixed set of factual lookups over documents we control, exact-keyword
and tool-selection checks are more defensible and reproducible than a judge
model's opinion.

Usage:
    .venv/Scripts/python.exe eval/run_eval.py
Requires OPENAI_API_KEY (or LLM_PROVIDER=ollama with Ollama running) in .env.
Writes eval/results.jsonl and eval/report.md.
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
import time
from pathlib import Path

logging.disable(logging.CRITICAL)

EVAL_DIR = Path(__file__).parent
REPO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
CASES_PATH = EVAL_DIR / "cases.jsonl"
RESULTS_PATH = EVAL_DIR / "results.jsonl"
REPORT_PATH = EVAL_DIR / "report.md"

SAMPLE_DOCS = [
    ("data/test_samples/legal_service_agreement.md", "legal"),
    ("data/test_samples/company_handbook.md", "general"),
    ("data/test_samples/it_incident_runbook.md", "general"),
]


def load_cases() -> list[dict]:
    cases = []
    with open(CASES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def ingest_samples(client) -> None:
    for rel_path, mode in SAMPLE_DOCS:
        abs_path = str((REPO_ROOT / rel_path).resolve())
        r = client.post("/ingest/path", json={"path": abs_path, "mode": mode})
        if r.status_code != 200:
            raise RuntimeError(f"Ingest failed for {rel_path}: {r.status_code} {r.text[:300]}")


def score_case(case: dict, answer: str, trace: list[dict]) -> dict:
    tools_used = [e["name"] for e in trace if e.get("type") == "tool_call"]
    citations_present = any(e.get("type") == "final" and e.get("citations") for e in trace)

    keyword_hit = None
    if case.get("expect_keywords"):
        low = answer.lower()
        keyword_hit = any(kw.lower() in low for kw in case["expect_keywords"])

    tool_hit = None
    if case.get("expect_tool"):
        tool_hit = case["expect_tool"] in tools_used

    flag_hit = None
    if case.get("expect_flag"):
        low = answer.lower()
        flag_hit = any(
            phrase in low
            for phrase in ("not from the document", "not in the document", "outside the knowledge base",
                           "general knowledge", "not from the knowledge base", "no relevant", "isn't in the")
        )

    return {
        "tools_used": tools_used,
        "citations_present": citations_present,
        "keyword_hit": keyword_hit,
        "tool_hit": tool_hit,
        "flag_hit": flag_hit,
    }


def run() -> None:
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app()
    client = TestClient(app)

    print("Ingesting sample documents...")
    ingest_samples(client)

    cases = load_cases()
    results = []

    for case in cases:
        t0 = time.perf_counter()
        r = client.post("/agent", json={"question": case["question"]})
        latency_ms = (time.perf_counter() - t0) * 1000

        body = r.json()
        answer = body.get("answer", "")
        trace = body.get("trace", [])
        is_error = any(e.get("type") == "error" for e in trace) or r.status_code != 200

        scoring = score_case(case, answer, trace)
        result = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "answer": answer,
            "latency_ms": round(latency_ms, 1),
            "is_error": is_error,
            **scoring,
        }
        results.append(result)
        status = "ERR" if is_error else "ok "
        print(f"  [{status}] {case['id']:<16} {latency_ms:6.0f}ms  kw={scoring['keyword_hit']}  tool={scoring['tool_hit']}")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    write_report(cases, results)
    print(f"\nWrote {RESULTS_PATH.name} and {REPORT_PATH.name}")


def write_report(cases: list[dict], results: list[dict]) -> None:
    n = len(results)
    errors = sum(1 for r in results if r["is_error"])

    kw_cases = [r for r in results if r["keyword_hit"] is not None]
    kw_hits = sum(1 for r in kw_cases if r["keyword_hit"])

    tool_cases = [r for r in results if r["tool_hit"] is not None]
    tool_hits = sum(1 for r in tool_cases if r["tool_hit"])

    flag_cases = [r for r in results if r["flag_hit"] is not None]
    flag_hits = sum(1 for r in flag_cases if r["flag_hit"])

    kb_question_results = [r for r in results if r["category"] in ("grounded_fact", "multi_hop")]
    citation_hits = sum(1 for r in kb_question_results if r["citations_present"])

    latencies = sorted(r["latency_ms"] for r in results)
    p50 = statistics.median(latencies) if latencies else 0
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0

    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    lines = [
        "# EKA Agent Evaluation Report",
        "",
        f"- Total cases: {n}",
        f"- Runtime errors: {errors}/{n}",
        f"- Keyword grounding accuracy: {kw_hits}/{len(kw_cases)} ({100*kw_hits/len(kw_cases):.1f}%)" if kw_cases else "- Keyword grounding accuracy: n/a",
        f"- Tool-selection accuracy: {tool_hits}/{len(tool_cases)} ({100*tool_hits/len(tool_cases):.1f}%)" if tool_cases else "- Tool-selection accuracy: n/a",
        f"- Out-of-scope flagging rate: {flag_hits}/{len(flag_cases)} ({100*flag_hits/len(flag_cases):.1f}%)" if flag_cases else "- Out-of-scope flagging rate: n/a",
        f"- Citation presence on KB questions: {citation_hits}/{len(kb_question_results)} ({100*citation_hits/len(kb_question_results):.1f}%)" if kb_question_results else "- Citation presence: n/a",
        f"- Latency: p50 {p50:.0f}ms / p95 {p95:.0f}ms",
        "",
        "## By category",
        "",
        "| Category | Cases | Keyword hit | Tool hit |",
        "|---|---|---|---|",
    ]
    for cat, rs in by_cat.items():
        kw = [r for r in rs if r["keyword_hit"] is not None]
        tl = [r for r in rs if r["tool_hit"] is not None]
        kw_s = f"{sum(1 for r in kw if r['keyword_hit'])}/{len(kw)}" if kw else "-"
        tl_s = f"{sum(1 for r in tl if r['tool_hit'])}/{len(tl)}" if tl else "-"
        lines.append(f"| {cat} | {len(rs)} | {kw_s} | {tl_s} |")

    lines += ["", "## Per-case detail", "", "| ID | Category | Latency | KW | Tool | Flag | Cites | Answer (truncated) |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        ans = r["answer"].replace("|", "\\|").replace("\n", " ")[:80]
        lines.append(
            f"| {r['id']} | {r['category']} | {r['latency_ms']:.0f}ms | {r['keyword_hit']} | "
            f"{r['tool_hit']} | {r['flag_hit']} | {r['citations_present']} | {ans} |"
        )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
