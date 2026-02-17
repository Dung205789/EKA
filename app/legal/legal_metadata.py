from typing import Any
from app.legal.legal_validity import validity_score

def enrich_legal_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    # expected optional fields: jurisdiction, case_number, date_filed, date_updated, status
    date_updated = meta.get("date_updated") or meta.get("date_filed")
    meta["validity_score"] = validity_score(date_updated)
    status = meta.get("status")
    if not status:
        # heuristic: low validity => outdated-ish
        meta["status"] = "outdated" if meta["validity_score"] < 0.35 else "active"
    return meta
