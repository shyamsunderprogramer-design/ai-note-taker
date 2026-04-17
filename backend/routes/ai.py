"""Route module for AI streaming, race, search, and configuration endpoints."""
import asyncio
import json
import logging
import os
import queue
import threading
import time

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse

from ai_router import build_prompt, clean_ai_output, route_ai, route_ai_stream
from security import sanitize_input, rate_limit, ErrorCode, error_response

logger = logging.getLogger("routes.ai")

# Shared state — set by main.py at include time or via module-level defaults
CURRENT_MODE = "auto"
STATE = {"is_streaming": False}

# Race history: {"winner": str, "ms": int, "providers": list, "timestamp": float}
_race_history = []

# Provider key cache (mirrors main.py)
from typing import Dict

_provider_key_cache: Dict[str, bool] = {}
_provider_key_cache_time: float = 0.0
_PROVIDER_KEY_CACHE_TTL = 300  # 5 minutes


def _has_provider_key(provider: str, env_var: str) -> bool:
    """Check if a provider has an API key, using a short-lived cache."""
    global _provider_key_cache, _provider_key_cache_time
    now = time.time()

    if provider in _provider_key_cache and (now - _provider_key_cache_time) < _PROVIDER_KEY_CACHE_TTL:
        return _provider_key_cache[provider]

    if os.getenv(env_var, "").strip():
        _provider_key_cache[provider] = True
        _provider_key_cache_time = now
        return True

    try:
        from lib.http_client import sync_client
        resp = sync_client.post(
            "http://127.0.0.1:18000/get-key",
            json={"provider": provider},
            timeout=1
        )
        if resp.status_code == 200:
            data = resp.json()
            result = bool(data.get("apiKey"))
        else:
            result = False
    except Exception:
        result = False

    _provider_key_cache[provider] = result
    _provider_key_cache_time = now
    return result


router = APIRouter()


@router.get("/stream")
def stream_ai(q: str, mode: str = "fast", style: str = "concise", provider: str = "ollama", context: str = None):
    """SSE stream endpoint — yields event: meta/chunk/done/error"""
    def generator():
        STATE["is_streaming"] = True

        # Parse context messages from JSON
        messages = None
        if context:
            try:
                messages = json.loads(context)
            except Exception:
                pass

        try:
            # Yield provider/mode info as first event
            yield f"event: meta\ndata: {{\"type\":\"meta\",\"provider\":\"{provider}\"}}\n\n"

            for event in route_ai_stream(q, mode, style, provider, messages):
                yield event

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"

        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/stream-race")
def stream_race(q: str, mode: str = "race", style: str = "concise", context: str = None, enabled: str = None):
    """
    Fire all configured providers in parallel. First to emit a meta/chunk event wins.
    Winner's response streams in real-time (word-by-word). Losing providers are
    cancelled to save API tokens. Falls back to Ollama if all clouds fail.
    Only providers specified in 'enabled' param (comma-separated) will be used.
    """
    from cloud_providers import MODEL_DISPLAY_NAMES, PROVIDER_MODEL_MAP, get_stream_fn

    race_start = time.time()
    logger.info("[RACE START] query='%s' mode=%s style=%s", q[:50], mode, style)

    # Parse enabled providers from frontend
    enabled_set = None
    if enabled:
        enabled_set = set(enabled.split(","))
        logger.info("Race mode: only using enabled providers from frontend: %s", enabled_set)

    messages = None
    if context:
        try:
            messages = json.loads(context)
        except json.JSONDecodeError:
            logger.warning("Failed to parse context JSON")

    # Separate cloud and local providers
    cloud_providers = []
    local_providers = []

    # If enabled_set from frontend is provided, only use those providers
    if enabled_set:
        if "openai" in enabled_set and _has_provider_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if "anthropic" in enabled_set and _has_provider_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if "google" in enabled_set and _has_provider_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if "xai" in enabled_set and _has_provider_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if "deepseek" in enabled_set and _has_provider_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if "groq" in enabled_set and _has_provider_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if "ollama-cloud" in enabled_set and _has_provider_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if "perplexity" in enabled_set and _has_provider_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        if "ollama" in enabled_set:
            local_providers.append("ollama")
    else:
        # Legacy: use all cloud providers with API keys, plus ollama as fallback
        if _has_provider_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if _has_provider_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if _has_provider_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if _has_provider_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if _has_provider_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if _has_provider_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if _has_provider_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if _has_provider_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        local_providers.append("ollama")

    # Deduplicate by provider prefix
    def deduplicate(provider_list):
        seen = set()
        result = []
        for pk in provider_list:
            if pk == "ollama-cloud":
                pname = "ollama-cloud"
            elif pk == "ollama":
                pname = "ollama"
            else:
                pname = pk.split("-")[0]
            if pname not in seen:
                seen.add(pname)
                result.append(pk)
        return result

    cloud_providers = deduplicate(cloud_providers)[:4]  # Limit to 4 concurrent
    local_providers = deduplicate(local_providers)

    # Sort for speed
    def sort_for_speed(provider_list):
        SPEED_PRIORITY = {"groq": 0, "google": 1, "openai": 2, "anthropic": 3, "deepseek": 4, "xai": 5, "perplexity": 6, "ollama-cloud": 7}
        def sort_key(pk):
            prefix = pk if pk in ("ollama", "ollama-cloud") else pk.split("-")[0]
            return SPEED_PRIORITY.get(prefix, 99)
        return sorted(provider_list, key=sort_key)

    cloud_providers = sort_for_speed(cloud_providers)
    all_providers = cloud_providers + local_providers
    logger.info("Race mode: clouds=%s, local=%s, combined=%s", cloud_providers, local_providers, all_providers)

    # Single-provider fast path
    if len(all_providers) <= 1:
        single_pk = all_providers[0] if all_providers else "ollama"
        def single_generator():
            STATE["is_streaming"] = True
            try:
                if single_pk == "ollama":
                    from ai_router import ask_ollama_stream
                    for event in ask_ollama_stream(q, mode=mode, style=style, messages=messages):
                        yield event
                else:
                    resolved = PROVIDER_MODEL_MAP.get(single_pk, ("openai", "gpt-4o-mini"))
                    model_name = resolved[1]
                    stream_fn = get_stream_fn(single_pk)
                    if stream_fn:
                        for event in stream_fn(q, model=model_name, mode=mode, style=style, messages=messages):
                            yield event
                    else:
                        yield f'event: error\ndata: {{"type":"error","message":"No stream function for {single_pk}"}}\n\n'
            finally:
                STATE["is_streaming"] = False
        return StreamingResponse(single_generator(), media_type="text/event-stream")

    # === Queue-based first-byte-wins race ===
    race_queue = queue.Queue()
    cancel_flags = {pk: threading.Event() for pk in all_providers}

    def stream_provider(pk):
        """Stream from a provider into the shared queue. Exit early if cancelled."""
        provider_start = time.time()
        logger.info("[PROVIDER START] %s", pk)
        try:
            if pk == "ollama":
                from ai_router import ask_ollama_stream
                stream_iter = ask_ollama_stream(q, mode=mode, style=style, messages=messages)
            else:
                resolved = PROVIDER_MODEL_MAP.get(pk, ("openai", "gpt-4o-mini"))
                model_name = resolved[1]
                stream_fn = get_stream_fn(pk)
                if stream_fn is None:
                    race_queue.put((pk, "ERROR", f"No stream function for {pk}"))
                    race_queue.put((pk, "DONE", None))
                    return
                stream_iter = stream_fn(q, model=model_name, mode=mode, style=style, messages=messages)

            has_error = False
            for event in stream_iter:
                if cancel_flags[pk].is_set():
                    logger.info("[PROVIDER CANCELLED] %s after %.1fs", pk, time.time() - provider_start)
                    race_queue.put((pk, "DONE", None))
                    return
                if "event: error" in event:
                    has_error = True
                    race_queue.put((pk, "ERROR", event))
                else:
                    race_queue.put((pk, "EVENT", event))

            if has_error:
                logger.info("[PROVIDER ERROR DONE] %s in %.1fs", pk, time.time() - provider_start)
            else:
                logger.info("[PROVIDER DONE] %s in %.1fs", pk, time.time() - provider_start)
            race_queue.put((pk, "DONE", None))
        except Exception as e:
            logger.error("[PROVIDER ERROR] %s: %s (%.1fs)", pk, e, time.time() - provider_start)
            race_queue.put((pk, "ERROR", str(e)))
            race_queue.put((pk, "DONE", None))

    # Start all provider threads
    threads = []
    for pk in all_providers:
        t = threading.Thread(target=stream_provider, args=(pk,), daemon=True)
        t.start()
        threads.append(t)

    def race_generator():
        STATE["is_streaming"] = True
        winner = None
        active_count = len(all_providers)
        done_count = 0
        winner_first_chunk_time = None
        winner_done = False

        while not winner_done and done_count < active_count:
            try:
                pk, event_type, event_data = race_queue.get(timeout=30)
            except queue.Empty:
                logger.warning("[RACE] Timeout waiting for providers")
                break

            if event_type == "DONE":
                done_count += 1
                if pk == winner:
                    winner_done = True
                continue

            if event_type == "ERROR":
                logger.warning("[RACE] provider %s error: %s", pk, event_data)
                continue

            if event_type != "EVENT":
                continue

            # First provider to emit a meta event wins the race
            if winner is None:
                if "event: meta" in event_data:
                    winner = pk
                    winner_first_chunk_time = time.time()
                    logger.info("[RACE WINNER] %s (first-byte in %.1fs)", pk, time.time() - race_start)
                    for other_pk in cancel_flags:
                        if other_pk != winner:
                            cancel_flags[other_pk].set()
                    yield event_data
                continue

            # Only stream the winner's events in real-time
            if pk == winner:
                yield event_data

        if winner is None:
            logger.error("[RACE] All providers failed")
            yield f'event: error\ndata: {{"type":"error","message":"All providers failed"}}\n\n'
        else:
            winner_ms = int((winner_first_chunk_time - race_start) * 1000) if winner_first_chunk_time else 0
            elapsed = time.time() - race_start
            logger.info("[RACE COMPLETE] winner=%s first_byte=%dms total=%.1fs", winner, winner_ms, elapsed)
            _race_history.append({
                "winner": winner,
                "ms": winner_ms,
                "providers": list(all_providers),
                "timestamp": time.time(),
            })
            while len(_race_history) > 100:
                _race_history.pop(0)

        STATE["is_streaming"] = False

    return StreamingResponse(race_generator(), media_type="text/event-stream")


@router.get("/race-stats")
def race_stats():
    """Return race performance statistics from recent races."""
    try:
        from cloud_providers import MODEL_DISPLAY_NAMES
    except ImportError:
        MODEL_DISPLAY_NAMES = {}
    recent = _race_history[-20:]
    formatted = []
    for r in recent:
        entry = {
            "winner": r["winner"],
            "ms": r["ms"],
            "providers": r["providers"],
            "display_name": MODEL_DISPLAY_NAMES.get(r["winner"], r["winner"]),
        }
        formatted.append(entry)

    win_counts = {}
    for r in _race_history:
        w = r["winner"]
        win_counts[w] = win_counts.get(w, 0) + 1

    return {
        "total_races": len(_race_history),
        "recent": formatted,
        "win_counts": win_counts,
    }


@router.post("/set-mode")
def set_mode(mode: str):
    global CURRENT_MODE
    if mode not in ["auto", "fast", "cloud", "interview", "universal", "adaptive", "reasoning", "code"]:
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid mode", status_code=400)

    CURRENT_MODE = mode
    return {"status": "mode updated", "mode": CURRENT_MODE}


@router.post("/ask-with-image")
@rate_limit(requests_per_minute=20)
async def ask_with_image(
    request: Request,
    query: str = Form(...),
    mode: str = Form("adaptive"),
    style: str = Form("concise"),
    provider: str = Form("auto"),
    context: str = Form(None),
    image_b64: str = Form(None),
    enabled: str = Form(None)
):
    """Accept text + optional base64 screenshot, stream AI response via SSE.
    When image is present and cloud vision keys are available, races across
    cloud vision providers for fastest response."""
    query = sanitize_input(query, max_length=10000)

    logger.info("[ask-with-image] query=%s, mode=%s, style=%s, has_image=%s, provider=%s",
                query[:100], mode, style, "Yes" if image_b64 else "No", provider)
    messages = None
    if context:
        try:
            messages = json.loads(context)
        except Exception:
            pass

    # No screenshot — regular text streaming
    if not image_b64:
        def text_generator():
            STATE["is_streaming"] = True
            try:
                from ai_router import route_ai_stream
                for event in route_ai_stream(query, mode=mode, style=style, provider=provider, messages=messages):
                    yield event
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
            finally:
                STATE["is_streaming"] = False
        return StreamingResponse(text_generator(), media_type="text/event-stream")

    # === Screenshot provided — use vision-capable providers ===
    from cloud_providers import VISION_PROVIDER_MAP, get_vision_stream_fn

    enabled_set = None
    if enabled:
        enabled_set = set(enabled.split(","))

    _VISION_PROVIDER_ENV = [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("groq", "GROQ_API_KEY"),
    ]
    providers_to_check = [
        (p, e) for p, e in _VISION_PROVIDER_ENV
        if enabled_set is None or p in enabled_set
    ]

    # Use batch key check if available, otherwise check individually
    key_status = {}
    try:
        from core.main import _batch_check_provider_keys
        key_status = _batch_check_provider_keys(providers_to_check)
    except ImportError:
        for p, e in providers_to_check:
            key_status[p] = bool(os.getenv(e, "").strip())

    vision_providers = []
    for provider_name, has_key in key_status.items():
        if has_key and provider_name in VISION_PROVIDER_MAP:
            vision_providers.append(provider_name)

    # Check Ollama vision
    ollama_vision_model = None
    try:
        from ai_router import _get_vision_model
        ollama_vision_model = _get_vision_model()
    except Exception:
        pass
    has_ollama_vision = ollama_vision_model is not None

    if not vision_providers and not has_ollama_vision:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'type':'error','message':'No vision-capable model found. Pull a vision model (ollama pull llava) or configure a cloud API key (GPT-4o, Claude, Gemini, Groq).'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    # Single provider (not race)
    if provider != "auto" and provider != "ollama" and provider in vision_providers and mode != "race":
        stream_fn = get_vision_stream_fn(provider)
        model = VISION_PROVIDER_MAP[provider]
        if stream_fn:
            def single_vision_gen():
                STATE["is_streaming"] = True
                try:
                    for event in stream_fn(query, image_b64=image_b64, model=model, mode=mode, style=style, messages=messages):
                        yield event
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
                finally:
                    STATE["is_streaming"] = False
            return StreamingResponse(single_vision_gen(), media_type="text/event-stream")

    # Single Ollama vision
    if not vision_providers or (provider == "ollama" and has_ollama_vision):
        if has_ollama_vision:
            def ollama_vision_gen():
                STATE["is_streaming"] = True
                try:
                    from ai_router import ask_ollama_vision_stream
                    for event in ask_ollama_vision_stream(query, image_b64=image_b64, mode=mode, style=style, messages=messages, model_name=ollama_vision_model):
                        yield event
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
                finally:
                    STATE["is_streaming"] = False
            return StreamingResponse(ollama_vision_gen(), media_type="text/event-stream")

    # === Vision Race Mode ===
    import queue as queue_mod
    import threading
    import time as time_module

    race_start = time_module.time()
    SPEED_PRIORITY = {"groq": 0, "google": 1, "openai": 2, "anthropic": 3}
    vision_providers.sort(key=lambda p: SPEED_PRIORITY.get(p, 99))

    all_vision = list(vision_providers)
    if has_ollama_vision and "ollama" not in all_vision:
        all_vision.append("ollama")

    race_queue = queue_mod.Queue()
    cancel_flags = {p: threading.Event() for p in all_vision}

    def stream_vision_provider(provider_name):
        p_start = time_module.time()
        try:
            if provider_name == "ollama":
                from ai_router import ask_ollama_vision_stream
                stream_iter = ask_ollama_vision_stream(
                    query, image_b64=image_b64, mode=mode, style=style,
                    messages=messages, model_name=ollama_vision_model
                )
            else:
                stream_fn = get_vision_stream_fn(provider_name)
                model = VISION_PROVIDER_MAP[provider_name]
                if stream_fn is None:
                    race_queue.put((provider_name, "ERROR", f"No vision stream for {provider_name}"))
                    race_queue.put((provider_name, "DONE", None))
                    return
                stream_iter = stream_fn(query, image_b64=image_b64, model=model, mode=mode, style=style, messages=messages)

            has_error = False
            for event in stream_iter:
                if cancel_flags[provider_name].is_set():
                    race_queue.put((provider_name, "DONE", None))
                    return
                if "event: error" in event:
                    has_error = True
                    race_queue.put((provider_name, "ERROR", event))
                else:
                    race_queue.put((provider_name, "EVENT", event))
            race_queue.put((provider_name, "DONE", None))
        except Exception as e:
            race_queue.put((provider_name, "ERROR", str(e)))
            race_queue.put((provider_name, "DONE", None))

    for vp in all_vision:
        t = threading.Thread(target=stream_vision_provider, args=(vp,), daemon=True)
        t.start()

    def vision_race_generator():
        STATE["is_streaming"] = True
        winner = None
        active_count = len(all_vision)
        done_count = 0
        winner_done = False

        while not winner_done and done_count < active_count:
            try:
                pk, event_type, event_data = race_queue.get(timeout=30)
            except queue_mod.Empty:
                break

            if event_type == "EVENT":
                if winner is None:
                    winner = pk
                    for other in cancel_flags:
                        if other != pk:
                            cancel_flags[other].set()
                if pk == winner:
                    yield event_data
            elif event_type == "ERROR":
                if pk == winner:
                    yield event_data
            elif event_type == "DONE":
                done_count += 1

        STATE["is_streaming"] = False

    return StreamingResponse(vision_race_generator(), media_type="text/event-stream")


@router.post("/overlay-ask")
@rate_limit(requests_per_minute=30)
async def overlay_ask(
    request: Request,
    query: str = Form(...),
    screenshot_b64: str = Form(None)
):
    """Quick Q&A from overlay window with optional screenshot context."""
    query = sanitize_input(query, max_length=5000)
    logger.info("[overlay-ask] query=%s, has_screenshot=%s", query, bool(screenshot_b64))

    async def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream, _get_vision_model, route_ai_stream

            if screenshot_b64:
                model_name = _get_vision_model()
                logger.info("[overlay-ask] Screenshot present, vision model: %s", model_name)
                if not model_name:
                    yield f"event: error\ndata: {json.dumps({'type':'error','message':'No vision model found. Pull one with: ollama pull llava:latest'})}\n\n"
                    return
                for event in ask_ollama_vision_stream(
                    query,
                    image_b64=screenshot_b64,
                    mode="fast",
                    style="concise",
                    model_name=model_name
                ):
                    yield event
            else:
                for event in route_ai_stream(query, mode="fast", style="concise"):
                    yield event
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'type':'error','message': str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.post("/set-always-on-mic")
async def set_always_on_mic(enabled: bool = Form(...)):
    """Enable or disable the always-on microphone."""
    # NOTE: This depends on whisper_handler and the streaming transcriber,
    # which are initialized in main.py. The router relies on those globals.
    try:
        from whisper_handler import get_streaming_transcriber
    except ImportError:
        return {"error": "Whisper not available", "enabled": False}

    transcriber = get_streaming_transcriber()

    if enabled:
        transcriber.start()
        logger.info("[AlwaysOnMic] Enabled")
    else:
        transcriber.stop()
        logger.info("[AlwaysOnMic] Disabled")

    return {"enabled": enabled}


@router.post("/configure")
async def configure_provider(body: dict):
    """API key configuration endpoint — DISABLED.

    SECURITY: API keys are no longer accepted over HTTP.
    Use secure IPC: window.api.saveApiKey(provider, apiKey)
    """
    return {
        "error": "HTTP configuration disabled for security",
        "message": "Use window.api.saveApiKey(provider, apiKey) for secure storage",
        "code": "INSECURE_TRANSPORT"
    }


@router.post("/detect-objections")
async def detect_objections(body: dict):
    """Detect sales objections in text."""
    OBJECTION_KEYWORDS = {
        "price": {
            "keywords": ["expensive", "too much", "price", "cost", "budget", "cheap", "cheaper", "afford"],
            "title": "Price Objection",
            "suggestions": [
                "Focus on ROI - our customers see 3x return in 6 months",
                "We offer flexible payment plans",
                "Let's discuss the enterprise tier with volume discounts",
                "Compare total cost of ownership vs alternatives"
            ]
        },
        "competitor": {
            "keywords": ["competitor", "competition", "alternative", "vs", "versus", "compare", "better than", "cheaper than"],
            "title": "Competitor Mention",
            "suggestions": [
                "Our differentiator is local AI - no data leaves your machine",
                "We support 8+ AI providers vs their single model",
                "Open source means no vendor lock-in",
                "Vision capabilities they don't offer"
            ]
        },
        "timing": {
            "keywords": ["not now", "later", "next quarter", "next year", "timing", "not ready", "delay", "postpone"],
            "title": "Timing Objection",
            "suggestions": [
                "Start with a pilot - no commitment",
                "Early adopters get lifetime pricing",
                "Setup takes 5 minutes - try it today",
                "We can schedule a follow-up that works for you"
            ]
        },
        "features": {
            "keywords": ["missing", "need", "feature", "functionality", "doesn't have", "lacks", "require"],
            "title": "Feature Request",
            "suggestions": [
                "We're shipping new features weekly - what's your priority?",
                "Our open API can bridge any gaps",
                "Let me check our roadmap for that feature",
                "Custom development available for enterprise"
            ]
        },
        "security": {
            "keywords": ["security", "privacy", "data", "confidential", "compliance", "soc2", "gdpr", "hipaa"],
            "title": "Security Question",
            "suggestions": [
                "100% local processing - data never leaves your machine",
                "No cloud dependencies for core features",
                "Open source - audit the code yourself",
                "SOC 2 Type II certified infrastructure"
            ]
        }
    }

    text = body.get("text", "").lower()
    if not text:
        return {"objections": []}

    detected = []
    for objection_type, config in OBJECTION_KEYWORDS.items():
        if any(kw in text for kw in config["keywords"]):
            detected.append({
                "type": objection_type,
                "title": config["title"],
                "suggestions": config["suggestions"]
            })

    return {"objections": detected}


@router.get("/search/web")
async def web_search(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Number of results"),
    include_citations: bool = Query(True, description="Include source citations")
):
    """Search the web using Perplexity API for real-time information."""
    from lib.http_client import sync_client

    # Try Perplexity first
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if perplexity_key:
        try:
            headers = {
                "Authorization": f"Bearer {perplexity_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": "Be precise and concise. Return factual information with sources."},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 500
            }
            response = sync_client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                result = {
                    "source": "perplexity",
                    "query": query,
                    "answer": data["choices"][0]["message"]["content"],
                    "citations": data.get("citations", []),
                    "timestamp": time.time()
                }
                return result
        except Exception as e:
            logger.warning(f"[WebSearch] Perplexity error: {e}")

    # Fallback: Brave Search
    brave_key = os.getenv("BRAVE_API_KEY")
    if brave_key:
        try:
            import requests as req
            headers = {"X-Subscription-Token": brave_key}
            response = sync_client.get(
                f"https://api.search.brave.com/res/v1/web/search?q={req.utils.quote(query)}&count={limit}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("web", {}).get("results", [])[:limit]:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "description": item.get("description")
                    })
                return {
                    "source": "brave",
                    "query": query,
                    "results": results,
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.warning(f"[WebSearch] Brave error: {e}")

    return {
        "source": "none",
        "query": query,
        "error": "Web search not configured. Set PERPLEXITY_API_KEY or BRAVE_API_KEY environment variable.",
        "timestamp": time.time()
    }


@router.get("/search/status")
async def search_status():
    """Check if web search is configured and available."""
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    brave_key = os.getenv("BRAVE_API_KEY")

    return {
        "configured": bool(perplexity_key or brave_key),
        "perplexity_available": bool(perplexity_key),
        "brave_available": bool(brave_key),
        "message": "Web search is ready" if (perplexity_key or brave_key) else "Add PERPLEXITY_API_KEY or BRAVE_API_KEY to enable web search"
    }