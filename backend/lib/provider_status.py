"""Shared provider availability checks, independent of the application router."""
import os
import time
from typing import Dict

from lib.http_client import sync_client

# Provider key status cache — avoids flooding the key server on every /providers call
# Per-provider timestamps so one stale entry doesn't invalidate all others
_provider_key_cache: Dict[str, tuple] = {}  # provider -> (result: bool, timestamp: float)
_PROVIDER_KEY_CACHE_TTL = 10  # 10 seconds


def has_provider_key(provider: str, env_var: str) -> bool:
    """Check if a provider has an API key, using a per-provider cache."""
    now = time.monotonic()

    # Return cached result if still fresh
    if provider in _provider_key_cache:
        cached_result, cached_time = _provider_key_cache[provider]
        if (now - cached_time) < _PROVIDER_KEY_CACHE_TTL:
            return cached_result

    # Check env var first (fast, no network)
    if os.getenv(env_var, "").strip():
        _provider_key_cache[provider] = (True, now)
        return True

    # Then check secure key server (with auth secret)
    try:
        headers = {}
        key_secret = os.getenv("KEY_SERVER_SECRET", "")
        if key_secret:
            headers["X-Key-Server-Secret"] = key_secret
        resp = sync_client.post(
            "http://127.0.0.1:18000/get-key",
            json={"provider": provider},
            headers=headers,
            timeout=2,
            skip_ssrf_check=True,  # internal key server, not user-supplied
        )
        if resp.status_code == 200:
            data = resp.json()
            result = bool(data.get("apiKey"))
        else:
            result = False
    except Exception:
        result = False

    _provider_key_cache[provider] = (result, now)
    return result


def batch_check_provider_keys(providers: list) -> Dict[str, bool]:
    """Check multiple provider keys concurrently using threads. Returns {provider: has_key}."""
    if not providers:
        return {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = {}
    with ThreadPoolExecutor(max_workers=min(8, len(providers))) as pool:
        futures = {
            pool.submit(has_provider_key, p, e): p
            for p, e in providers
        }
        for future in as_completed(futures):
            provider = futures[future]
            results[provider] = future.result()
    return results


