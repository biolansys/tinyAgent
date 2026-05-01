import json, urllib.request, urllib.error, time
from .. import config
from .ranking import record_success, record_failure, rank_routes

def parse_route(route):
    if "::" in route:
        provider, model = route.split("::", 1)
        return provider.strip().lower(), model.strip()
    if route.startswith("hf:"):
        return "huggingface", route[3:].strip()
    return "openrouter", route.strip()

def make_route(provider, model):
    return f"{provider}::{model}"

def provider_url(provider):
    if provider == "huggingface":
        return config.HF_API_URL
    if provider == "mistral":
        return config.MISTRAL_API_URL
    return config.OPENROUTER_API_URL

def headers(provider):
    if provider == "huggingface":
        if not config.HF_TOKEN:
            raise RuntimeError("Missing HF_TOKEN")
        return {
            "Authorization": f"Bearer {config.HF_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": config.APP_TITLE,
        }
    if provider == "mistral":
        if not config.MISTRAL_API_KEY:
            raise RuntimeError("Missing MISTRAL_API_KEY")
        return {
            "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": config.APP_TITLE,
        }
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY")
    return {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": config.APP_TITLE,
    }

def post_json(provider, payload, timeout=90, attempts=3):
    url = provider_url(provider)
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers=headers(provider),
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError:
            raise
        except Exception as e:
            last = e
            time.sleep(1.25 * (i + 1))
    raise RuntimeError(f"Provider call failed: {last}")

class MultiProviderClient:
    def __init__(self, state):
        self.state = state

    def chat(self, messages, tools=None, force_no_tools=False):
        last_error = None
        active = rank_routes([r for r in self.state.routes if self.state.route_allowed(r)] or self.state.routes)
        for route in active:
            provider, model = parse_route(route)
            attempts = [True, False] if tools and not force_no_tools else [False]
            for use_tools in attempts:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": self.state.temperature,
                }
                if use_tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                try:
                    start_time = time.time()
                    data = post_json(provider, payload)
                    latency = time.time() - start_time
                    if "error" in data:
                        last_error = f"{route}: {data['error']}"
                        record_failure(route, last_error)
                        continue
                    if not data.get("choices"):
                        last_error = f"{route}: no choices"
                        record_failure(route, last_error)
                        continue
                    data["_route"] = route
                    data["_provider"] = provider
                    data["_model"] = model
                    data["_tools_enabled"] = use_tools
                    self._usage(route, data)
                    record_success(route, latency)
                    return data
                except Exception as e:
                    last_error = f"{route}: {e}"
                    record_failure(route, last_error)
        raise RuntimeError(f"All routes failed. Last error: {last_error}")

    def _usage(self, route, data):
        usage = data.get("usage") or {}
        if not usage:
            return
        prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total = int(usage.get("total_tokens") or prompt + completion)
        self.state.usage["calls"] += 1
        self.state.usage["prompt_tokens"] += prompt
        self.state.usage["completion_tokens"] += completion
        self.state.usage["total_tokens"] += total
        r = self.state.usage["by_route"].setdefault(route, {"calls": 0, "total_tokens": 0})
        r["calls"] += 1
        r["total_tokens"] += total
