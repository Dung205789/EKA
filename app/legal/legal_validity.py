from datetime import datetime, timezone
import math

def validity_score(date_updated: str | None, half_life_days: int = 730) -> float:
    if not date_updated:
        return 0.5
    try:
        d = datetime.fromisoformat(date_updated)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - d).days
        return float(math.exp(-age_days / max(1, half_life_days)))
    except Exception:
        return 0.5
