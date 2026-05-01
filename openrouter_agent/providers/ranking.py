import json
from datetime import datetime
from .. import config

DEFAULT_METRICS = {
    "attempts": 0,
    "successes": 0,
    "failures": 0,
    "total_latency": 0.0,
    "last_error": "",
    "last_used": None,
}

def load_rankings():
    if not config.MODEL_RANKING_FILE.exists():
        return {}
    try:
        return json.loads(config.MODEL_RANKING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_rankings(data):
    config.MODEL_RANKING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def ensure_route(data, route):
    if route not in data:
        data[route] = DEFAULT_METRICS.copy()
    return data[route]

def record_success(route, latency=0.0):
    data = load_rankings()
    m = ensure_route(data, route)
    m["attempts"] += 1
    m["successes"] += 1
    m["total_latency"] += float(latency or 0.0)
    m["last_error"] = ""
    m["last_used"] = datetime.now().isoformat(timespec="seconds")
    save_rankings(data)

def record_failure(route, error=""):
    data = load_rankings()
    m = ensure_route(data, route)
    m["attempts"] += 1
    m["failures"] += 1
    m["last_error"] = str(error)[:500]
    m["last_used"] = datetime.now().isoformat(timespec="seconds")
    save_rankings(data)

def score_route(route, data=None):
    data = data or load_rankings()
    m = data.get(route, DEFAULT_METRICS.copy())

    attempts = max(1, m.get("attempts", 0))
    successes = m.get("successes", 0)
    failures = m.get("failures", 0)
    latency_total = m.get("total_latency", 0.0)

    success_rate = successes / attempts
    avg_latency = latency_total / max(1, successes)

    # Optimistic default for untested routes.
    if m.get("attempts", 0) == 0:
        return 0.55

    # Higher is better. Penalize failures and latency.
    return round((success_rate * 100) - (failures * 5) - min(avg_latency, 30), 4)

def rank_routes(routes):
    data = load_rankings()
    return sorted(routes, key=lambda r: score_route(r, data), reverse=True)

def ranking_report():
    data = load_rankings()
    if not data:
        return "No model ranking data yet."

    rows = []
    for route in sorted(data, key=lambda r: score_route(r, data), reverse=True):
        m = data[route]
        attempts = max(1, m.get("attempts", 0))
        success_rate = m.get("successes", 0) / attempts
        avg_latency = m.get("total_latency", 0.0) / max(1, m.get("successes", 0))
        rows.append(
            f"{route}\n"
            f"  score={score_route(route, data)} success_rate={success_rate:.2%} "
            f"attempts={m.get('attempts', 0)} failures={m.get('failures', 0)} "
            f"avg_latency={avg_latency:.2f}s\n"
            f"  last_error={m.get('last_error', '') or '-'}"
        )
    return "\n".join(rows)

def reset_rankings():
    if config.MODEL_RANKING_FILE.exists():
        config.MODEL_RANKING_FILE.unlink()
    return "Model ranking data reset."
