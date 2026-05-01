import json
import urllib.request
import time
from datetime import datetime, timedelta

from .. import config
from .client import make_route, post_json, headers
from .ranking import rank_routes, record_success, record_failure, load_rankings, score_route

LAST_DISCOVERY_REPORT = None


def is_free_model(model):
    mid = model.get("id", "")
    if mid.endswith(":free"):
        return True

    pricing = model.get("pricing", {}) or {}
    zero = {"0", "0.0", "0.000000", "0.0000000"}
    return str(pricing.get("prompt", "")) in zero and str(pricing.get("completion", "")) in zero


def fetch_openrouter_free_models():
    if not config.OPENROUTER_API_KEY:
        return []

    req = urllib.request.Request(
        config.OPENROUTER_MODELS_URL,
        method="GET",
        headers=headers("openrouter"),
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    models = [
        m.get("id")
        for m in data.get("data", [])
        if m.get("id") and is_free_model(m)
    ]

    priority = ["coder", "code", "instruct", "chat", "qwen", "deepseek", "llama", "mistral", "gemma"]
    models.sort(key=lambda x: (not any(w in x.lower() for w in priority), x))
    return models


def get_hf_candidates():
    if not config.HF_TOKEN:
        return []

    hf_file = config.ROOT / ".hf_models"
    if hf_file.exists():
        return [x.strip() for x in hf_file.read_text(encoding="utf-8").splitlines() if x.strip()]

    return config.load_hf_models()


def fetch_mistral_models():
    if not config.MISTRAL_API_KEY:
        return []

    req = urllib.request.Request(
        config.MISTRAL_MODELS_URL,
        method="GET",
        headers=headers("mistral"),
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    if isinstance(data, dict):
        models_data = data.get("data", [])
    else:
        models_data = data

    models = []
    for model in models_data or []:
        if not isinstance(model, dict):
            continue
        if model.get("archived"):
            continue
        capabilities = model.get("capabilities") or {}
        if capabilities.get("completion_chat") is False:
            continue
        model_id = model.get("id")
        if model_id:
            models.append(model_id)

    priority = ["codestral", "mistral", "medium", "small", "large", "chat", "instruct"]
    models.sort(key=lambda x: (not any(w in x.lower() for w in priority), x))
    return models


def get_mistral_candidates():
    mistral_file = config.ROOT / ".mistral_models"
    if mistral_file.exists():
        return [x.strip() for x in mistral_file.read_text(encoding="utf-8").splitlines() if x.strip()]

    models = fetch_mistral_models()
    if models:
        return models

    return config.load_mistral_models()


def candidate_routes(max_checks_per_provider=None):
    routes = []
    max_checks = config.DISCOVERY_MAX_CHECKS_PER_PROVIDER if max_checks_per_provider is None else max_checks_per_provider

    if config.OPENROUTER_API_KEY:
        openrouter_models = fetch_openrouter_free_models()
        if max_checks > 0:
            openrouter_models = openrouter_models[:max_checks]
        routes += [make_route("openrouter", m) for m in openrouter_models]

    if config.HF_TOKEN:
        hf_models = get_hf_candidates()
        if max_checks > 0:
            hf_models = hf_models[:max_checks]
        routes += [make_route("huggingface", m) for m in hf_models]

    if config.MISTRAL_API_KEY:
        mistral_models = get_mistral_candidates()
        if max_checks > 0:
            mistral_models = mistral_models[:max_checks]
        routes += [make_route("mistral", m) for m in mistral_models]

    return rank_routes(routes)


def _provider_from_route(route):
    return route.split("::", 1)[0] if "::" in route else "unknown"


def _provider_counts(routes):
    counts = {}
    for route in routes:
        provider = _provider_from_route(route)
        counts[provider] = counts.get(provider, 0) + 1
    return counts


def _build_report(source, candidates, tested_routes, working_routes, failures, use_cache, early_stop, max_checks):
    tested_counts = _provider_counts(tested_routes)
    working_counts = _provider_counts(working_routes)
    failed_counts = _provider_counts(list(failures.keys()))
    candidate_counts = _provider_counts(candidates)
    return {
        "source": source,
        "last_checked": datetime.now().isoformat(timespec="seconds"),
        "use_cache": use_cache,
        "early_stop": early_stop,
        "max_checks_per_provider": max_checks,
        "candidate_routes": candidates,
        "candidate_counts": candidate_counts,
        "tested_routes": tested_routes,
        "tested_counts": tested_counts,
        "working_routes": working_routes,
        "working_counts": working_counts,
        "failure_counts": failed_counts,
        "failures": failures,
    }


def _store_last_report(report):
    global LAST_DISCOVERY_REPORT
    LAST_DISCOVERY_REPORT = report


def last_discovery_report():
    return LAST_DISCOVERY_REPORT


def format_discovery_report(report, title="Discovery Report"):
    if not report:
        return "No discovery report available."

    lines = [
        title,
        "=" * len(title),
        f"Source: {report.get('source', '-')}",
        f"Last checked: {report.get('last_checked', '-')}",
        f"Use cache: {report.get('use_cache')}",
        f"Early stop: {report.get('early_stop')}",
        f"Max checks per provider: {report.get('max_checks_per_provider')}",
        "",
        "Counts by provider:",
    ]

    providers = sorted(set(report.get("candidate_counts", {})) | set(report.get("tested_counts", {})) | set(report.get("working_counts", {})) | set(report.get("failure_counts", {})))
    if not providers:
        lines.append("- none")
    else:
        for provider in providers:
            lines.append(
                f"- {provider}: candidates={report.get('candidate_counts', {}).get(provider, 0)} "
                f"tested={report.get('tested_counts', {}).get(provider, 0)} "
                f"working={report.get('working_counts', {}).get(provider, 0)} "
                f"failed={report.get('failure_counts', {}).get(provider, 0)}"
            )

    lines.extend([
        "",
        f"Working routes: {len(report.get('working_routes', []))}",
    ])
    rankings = load_rankings()
    for route in report.get("working_routes", []):
        lines.append(f"- {route} | score={score_route(route, rankings)}")

    lines.append("")
    lines.append("Failures:")
    if report.get("failures"):
        for route, error in report.get("failures", {}).items():
            lines.append(f"- {route}: {error}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def _reply_is_ok(data):
    choices = data.get("choices") or []
    if not choices:
        return False
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        content = "".join(text_parts)
    return str(content).strip().upper() == "OK"


def test_route(route):
    provider, model = route.split("::", 1)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply only with OK."}],
        "temperature": 0,
        "max_tokens": 8,
    }

    try:
        start = time.time()
        data = post_json(provider, payload, timeout=30, attempts=1)
        latency = time.time() - start
        ok = _reply_is_ok(data)

        if ok:
            record_success(route, latency)
        else:
            record_failure(route, "discovery: unexpected response")

        return ok, latency, "" if ok else "unexpected response"

    except Exception as e:
        err = f"discovery: {e}"
        record_failure(route, err)
        return False, 0.0, err


def _cache_valid(cache):
    try:
        checked = datetime.fromisoformat(cache.get("last_checked", ""))
    except Exception:
        return False

    ttl = timedelta(minutes=config.DISCOVERY_CACHE_TTL_MINUTES)
    return datetime.now() - checked < ttl


def load_discovery_cache():
    if not config.DISCOVERY_CACHE_FILE.exists():
        return None

    try:
        cache = json.loads(config.DISCOVERY_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not _cache_valid(cache):
        return None

    routes = cache.get("working_routes") or []
    if len(routes) < config.DISCOVERY_MIN_WORKING_ROUTES:
        return None

    cache.setdefault("source", "cache")
    cache.setdefault("candidate_routes", cache.get("tested_routes", []))
    cache.setdefault("candidate_counts", _provider_counts(cache.get("candidate_routes", [])))
    cache.setdefault("tested_counts", _provider_counts(cache.get("tested_routes", [])))
    cache.setdefault("working_counts", _provider_counts(cache.get("working_routes", [])))
    cache.setdefault("failure_counts", _provider_counts(list((cache.get("failures") or {}).keys())))
    cache.setdefault("use_cache", True)
    cache.setdefault("early_stop", True)
    cache.setdefault("max_checks_per_provider", cache.get("settings", {}).get("max_checks_per_provider"))

    return cache


def save_discovery_cache(working_routes, tested_routes, failures, candidates=None, source="live", use_cache=False, early_stop=True, max_checks=None):
    ranked_working = rank_routes(working_routes)
    data = _build_report(
        source=source,
        candidates=candidates or tested_routes,
        tested_routes=tested_routes,
        working_routes=ranked_working,
        failures=failures,
        use_cache=use_cache,
        early_stop=early_stop,
        max_checks=max_checks,
    )
    data["settings"] = {
        "target_working_routes": config.DISCOVERY_TARGET_WORKING_ROUTES,
        "max_checks_per_provider": config.DISCOVERY_MAX_CHECKS_PER_PROVIDER,
        "cache_ttl_minutes": config.DISCOVERY_CACHE_TTL_MINUTES,
    }

    config.DISCOVERY_CACHE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _store_last_report(data)


def clear_discovery_cache():
    if config.DISCOVERY_CACHE_FILE.exists():
        config.DISCOVERY_CACHE_FILE.unlink()
        return "Discovery cache cleared."
    return "No discovery cache found."


def discovery_report():
    if not config.DISCOVERY_CACHE_FILE.exists():
        return "No discovery cache found."

    try:
        cache = json.loads(config.DISCOVERY_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Could not read discovery cache: {e}"

    return format_discovery_report(cache, title="Smart Discovery Cache")


def discover_routes(max_checks=None, target_working=None, use_cache=True, early_stop=True):
    """
    Smart discovery:
    - Uses cached working routes when still valid.
    - Sorts candidates by historical model ranking.
    - Stops early when enough working routes are found.
    - Persists discovery results in .model_discovery_cache.json.
    """
    if use_cache:
        cached = load_discovery_cache()
        if cached:
            _store_last_report(cached)
            return rank_routes(cached.get("working_routes", []))

    full_scan = max_checks == 0
    max_checks = config.DISCOVERY_MAX_CHECKS_PER_PROVIDER if max_checks is None else max_checks
    target_working = target_working or config.DISCOVERY_TARGET_WORKING_ROUTES

    candidates = candidate_routes(max_checks_per_provider=max_checks)
    if not candidates:
        return config.DEFAULT_ROUTES.copy()

    working = []
    tested = []
    failures = {}

    for route in candidates:
        tested.append(route)
        ok, _latency, error = test_route(route)

        if ok:
            working.append(route)
        else:
            failures[route] = error

        if early_stop and not full_scan and len(working) >= target_working:
            break

    if working:
        ranked_working = rank_routes(working)
        save_discovery_cache(
            ranked_working,
            tested,
            failures,
            candidates=candidates,
            source="live",
            use_cache=use_cache,
            early_stop=early_stop,
            max_checks=max_checks,
        )
        return ranked_working

    save_discovery_cache(
        [],
        tested,
        failures,
        candidates=candidates,
        source="live",
        use_cache=use_cache,
        early_stop=early_stop,
        max_checks=max_checks,
    )
    return config.DEFAULT_ROUTES.copy()
