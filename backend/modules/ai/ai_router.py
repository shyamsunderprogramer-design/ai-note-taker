import json
import logging
import os
import re
import threading
import time

from lib.http_client import sync_client
import httpx

from config import AI_TEMPERATURE, AI_TIMEOUT, OLLAMA_URL, get_ai_model, TURBO_MAX_TOKENS, INSTANT_MAX_TOKENS
from utils import clean_ai_output

logger = logging.getLogger("ai_router")

AI_MODE = "adaptive"

CODE_KEYWORDS = (
    "code", "python", "javascript", "typescript", "java", "c#", "golang",
    "go ", "sql", "regex", "function", "class", "bug", "debug", "refactor",
    "api", "json", "yaml", "dockerfile", "algorithm", "stack trace", "exception"
)
TECHNICAL_KEYWORDS = (
    "docker", "kubernetes", "pod", "pods", "container", "ci/cd", "devops", "aws",
    "azure", "gcp", "microservice", "architecture", "database", "ingress",
    "helm", "deployment", "load balancer"
)
INTERVIEW_HINTS = ("interview", "technical round", "tech round", "hiring manager")

# Vision-capable model name patterns (partial match)
VISION_MODEL_NAMES = ("llava", "qwen-vl", "moondream", "minicpm-v", "bakllava")

# Cache for installed vision-capable models
_vision_model_cache = None

# Provider key cache — warmed once, never blocks requests
_provider_key_cache = {}
_provider_key_cache_time = {}  # per-provider timestamps
_PROVIDER_KEY_CACHE_TTL = 10  # 10 seconds


def _warm_provider_keys():
    """Background warmup of provider API keys. Call once at startup."""
    global _provider_key_cache, _provider_key_cache_time
    try:
        import os as _os
        key_secret = _os.getenv("KEY_SERVER_SECRET", "")
        headers = {}
        if key_secret:
            headers["X-Key-Server-Secret"] = key_secret
        providers = ["openai", "anthropic", "google", "xai", "deepseek", "groq", "ollama-cloud", "perplexity"]
        now = time.time()
        for provider in providers:
            try:
                resp = sync_client.post(
                    "http://127.0.0.1:18000/get-key",
                    json={"provider": provider},
                    headers=headers,
                    timeout=1,
                    skip_ssrf_check=True,
                )
                _provider_key_cache[provider] = resp.status_code == 200 and bool(resp.json().get("apiKey"))
            except Exception:
                _provider_key_cache[provider] = False
            _provider_key_cache_time[provider] = now
        logger.info("[ProviderKeys] Warmed %d providers", len(_provider_key_cache))
    except Exception as e:
        logger.warning("[ProviderKeys] Warmup failed: %s", e)


def _has_provider_key_fast(provider: str) -> bool:
    """Check provider key from cache (no HTTP call). Falls back to env var."""
    now = time.time()
    cached_time = _provider_key_cache_time.get(provider, 0)
    if provider in _provider_key_cache and (now - cached_time) < _PROVIDER_KEY_CACHE_TTL:
        return _provider_key_cache[provider]
    # Fallback: check env var directly (zero latency)
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama-cloud": "OLLAMA_CLOUD_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var and os.getenv(env_var, "").strip():
        _provider_key_cache[provider] = True
        _provider_key_cache_time[provider] = now
        return True
    return _provider_key_cache.get(provider, False)


def _discover_vision_model():
    """Background discovery of vision-capable model."""
    global _vision_model_cache
    try:
        resp = sync_client.get(f"{OLLAMA_URL}/api/tags", timeout=3, skip_ssrf_check=True)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            for m in models:
                name = m.get("name", "")
                for vision_name in VISION_MODEL_NAMES:
                    if vision_name in name.lower():
                        _vision_model_cache = name
                        logger.info("[_get_vision_model] Found vision model: %s", name)
                        return
    except Exception as e:
        logger.debug("Vision model discovery: %s", str(e))
    _vision_model_cache = None


def _get_vision_model():
    """
    Return the name of an available vision-capable Ollama model, or None if none found.
    Caches result for the session lifetime. Non-blocking on first call.
    """
    global _vision_model_cache
    if _vision_model_cache is not None:
        return _vision_model_cache
    # If not cached yet, return None immediately and discover in background
    threading.Thread(target=_discover_vision_model, daemon=True).start()
    return None


def resolve_mode(user_input, requested_mode="auto"):
    if requested_mode and requested_mode != "auto":
        return requested_mode

    prompt = (user_input or "").strip().lower()
    word_count = len(prompt.split())

    if any(keyword in prompt for keyword in CODE_KEYWORDS):
        if word_count >= 18:
            return "code"
        return "adaptive"

    if word_count >= 30 or any(keyword in prompt for keyword in ("compare", "tradeoff", "tradeoffs", "trade-off", "design", "deeply")):
        return "reasoning"

    if any(keyword in prompt for keyword in TECHNICAL_KEYWORDS):
        if any(keyword in prompt for keyword in INTERVIEW_HINTS) or word_count >= 12:
            return "interview"
        return "adaptive"


    if word_count <= 8:
        return "fast"

    return "adaptive"


def get_model_candidates(user_input, requested_mode="auto"):
    resolved_mode = resolve_mode(user_input, requested_mode)

    fallback_map = {
        "fast": ["fast", "adaptive", "universal"],
        "adaptive": ["adaptive", "universal", "fast"],
        "universal": ["universal", "adaptive", "reasoning"],
        "interview": ["interview", "universal", "reasoning"],
        "reasoning": ["universal", "reasoning", "adaptive"],
        "code": ["adaptive", "code", "reasoning"],
        "cloud": ["cloud", "reasoning", "adaptive"],
        "summary": ["summary", "universal", "adaptive"],
    }

    seen = set()
    candidates = []

    for mode in fallback_map.get(resolved_mode, [resolved_mode, "adaptive", "fast"]):
        model = get_ai_model(mode)
        if model in seen:
            continue
        seen.add(model)
        candidates.append((mode, model))

    return resolved_mode, candidates


def build_prompt(user_input, mode="adaptive", style="concise", messages=None, include_rag=True):
    # Style-specific instructions
    if style == "concise":
        style_instruction = "2 sentences max."
    elif style == "detailed":
        style_instruction = "2-3 paragraphs. Code if relevant."
    elif style == "bulletpoint":
        style_instruction = "4 bullets max."
    else:
        style_instruction = "Short."

    # Build conversation history context
    history_block = ""
    if messages:
        history_lines = []
        for msg in messages:
            role_label = "You" if msg.get("role") == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg.get('text', '')}")
        history_block = "Chat history:\n" + "\n".join(history_lines) + "\n\n"

    # Retrieve relevant document context if RAG is enabled (lazy, cached)
    rag_block = ""
    if include_rag and mode not in ("race", "fast", "instant", "turbo"):
        try:
            from document_store import get_document_store
            doc_store = get_document_store()
            # Only format context if documents exist (fast check)
            if hasattr(doc_store, '_documents') and doc_store._documents:
                rag_context = doc_store.format_context_for_prompt(user_input)
                if rag_context:
                    rag_block = rag_context
        except Exception:
            pass  # nosec B110

    base = f"""Slack message between two senior engineers.

FORBIDDEN:
- No headers/titles (=== or #)
- No tables
- No bullet lists
- No numbered lists
- No emojis
- No code blocks unless asked
- No "Here's" or "Sure" intros

Write like a text message. Plain paragraphs only.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "code":
        return f"""Senior engineer. Code when asked. Plain text only.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "reasoning":
        return f"""Senior engineer thinking. Plain text.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "fast":
        return f"""Senior engineer. Fast answer. Plain text.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "race":
        # Minimal prompt for sub-second first-byte — no FORBIDDEN list, no style rules
        return f"""{history_block}{rag_block}Q: {user_input}
A:"""

    if mode == "cloud":
        return f"""Senior engineer. Plain text answer.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "interview":
        return f"""Senior engineer. Technical. Plain text.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "universal":
        return f"""Senior engineer. Plain text answer.

{history_block}{rag_block}Question: {user_input}
Answer:"""

    if mode == "summary":
        return f"""You are a meeting notes assistant. Read the conversation transcript below and produce a structured summary.

STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS (use the same markdown formatting):

# [Topic / Title from conversation]

## Overview
[Brief 1-2 sentence overview of what this conversation was about]

## Key Points
[3-5 bullet points of the most important things discussed]
* bullet one
* bullet two
* ...

## Next Steps / Action Items
[Any tasks, follow-ups, or action items mentioned]
* action item one
* action item two
* ...

## Details
[Additional important details, definitions, or context that came up]
- detail one
- detail two

Do not mention that you are an AI or that you received a transcript. Just produce the summary directly.
Conversation transcript:
{user_input}
"""

    if mode == "followup":
        return f"""Write a professional follow-up email based on the meeting summary below.

The email should:
- Have a clear subject line
- Thank the participants for their time
- Summarize key discussion points (2-3 bullets)
- List action items and owners
- Propose next steps or a follow-up meeting
- Be professional but warm

Meeting summary:
{user_input}
"""

    return base


def ask_ollama(prompt, mode=AI_MODE, model_name=None, style="concise"):
    try:
        final_prompt = build_prompt(prompt, mode, style)
        model = model_name or get_ai_model(mode)

        response = sync_client.post(
            f"{OLLAMA_URL}/api/generate",
            skip_ssrf_check=True,  # internal Ollama service
            json={
                "model": model,
                "prompt": final_prompt,
                "stream": False,
                "think": False,  # qwen3.5:9b / lfm2.5 put content in `thinking` field; force `response` field
                "options": {
                    "temperature": AI_TEMPERATURE
                }
            },
            timeout=AI_TIMEOUT
        )

        if response.status_code != 200:
            if response.status_code == 404:
                return f"Model '{model}' not installed. Run: ollama pull {model}"
            return "AI service unavailable."

        data = response.json()
        return data.get("response", "").strip()

    except Exception as e:
        logger.error("ask_ollama error: %s", str(e))
        return "AI error"


def ask_ollama_stream(prompt, mode=AI_MODE, model_name=None, style="concise", messages=None, temperature=None):
    """Yields SSE event strings — meta, content chunks, done, error."""
    import time
    start = time.time()
    try:
        logger.info("Streaming (%s mode, %s style): %s", mode, style, prompt[:100] + "..." if len(prompt) > 100 else prompt)

        final_prompt = build_prompt(prompt, mode, style, messages)

        # Cloud models like qwen3.5:397b-cloud and gpt-oss:20b-cloud are more capable
        # and produce better responses, so give them more tokens
        is_cloud_model = model_name and (":cloud" in str(model_name) or "-cloud" in str(model_name))
        is_turbo = mode == "turbo"
        is_instant = mode == "instant"
        num_predict = INSTANT_MAX_TOKENS if is_instant else (TURBO_MAX_TOKENS if is_turbo else (2000 if is_cloud_model else (300 if style == "concise" else (2000 if style == "detailed" else 500))))

        import os as _os, psutil
        cpu_count = psutil.cpu_count(logical=True) or 4
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        # Low-end systems: small context window + all CPU threads for speed
        num_ctx = 2048 if ram_gb < 8 else 4096

        payload = {
            "model": model_name or get_ai_model(mode),
            "prompt": final_prompt,
            "stream": True,
            "think": False,  # qwen3.5:9b / lfm2.5 put content in `thinking` field; force `response` field
            "options": {
                "temperature": temperature if temperature is not None else AI_TEMPERATURE,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "num_thread": cpu_count,
            }
        }

        with sync_client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload, timeout=AI_TIMEOUT, skip_ssrf_check=True) as response:
            if response.status_code != 200:
                model_display = model_name or get_ai_model(mode)
                # Ollama returns 404 with a JSON body like {"error":"model 'X' not found"} —
                # surface that with a runnable fix instead of the generic HTTP code.
                if response.status_code == 404:
                    err_body = ""
                    try:
                        err_body = response.read().decode("utf-8", errors="ignore")[:200]
                    except Exception:
                        pass
                    logger.error("Ollama 404 for model %s: %s", model_display, err_body)
                    yield _make_error(
                        f"Model '{model_display}' not installed. Run: ollama pull {model_display}"
                    )
                    return
                logger.error("Ollama service returned status %d", response.status_code)
                yield _make_error(f"AI service unavailable (HTTP {response.status_code}).")
                return

            model_display = model_name or get_ai_model(mode)
            yield _make_meta(model_display, "ollama")

            chunk_count = 0
            line_count = 0
            for line in response.iter_lines():
                line_count += 1
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    if "response" in data:
                        chunk = data["response"]
                        if chunk.strip():
                            yield _make_content(chunk)
                            chunk_count += 1

                    if data.get("done", False):
                        break

                except json.JSONDecodeError as e:
                    logger.warning("Stream JSON decode error: %s, line: %s", e, line[:100])
                    continue
                except Exception as e:
                    logger.warning("Stream parse error: %s", str(e))
                    continue

        ms = int((time.time() - start) * 1000)
        logger.info("Stream complete: %d chunks in %dms (%d lines from ollama)", chunk_count, ms, line_count)
        yield _make_done(ms)

    except httpx.TimeoutException:
        logger.error("Ollama streaming timeout after %ds", AI_TIMEOUT)
        yield _make_error("AI response timeout. Please try again.")

    except httpx.ConnectError:
        logger.error("Ollama connection error")
        yield _make_error("Cannot connect to AI service. Is Ollama running?")

    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        yield _make_error("AI error occurred.")


def ask_ollama_vision_stream(prompt, image_b64=None, mode="adaptive", style="concise", messages=None, model_name=None, temperature=None):
    """Ollama streaming with optional image — for multimodal (vision) models like llava.

    If image_b64 is provided but no vision model is available, attempts to pull one.
    """
    import time
    start = time.time()
    try:
        # When image is provided, use raw prompt (build_prompt wrapper breaks vision models)
        # Without image, use the standard wrapped prompt for text-only queries
        if image_b64:
            final_prompt = prompt
        else:
            final_prompt = build_prompt(prompt, mode, style, messages)

        num_predict = 300 if style == "concise" else (2000 if style == "detailed" else 500)

        # When image is provided, try to find a vision-capable model
        vision_model = model_name
        if image_b64 and not vision_model:
            vision_model = _get_vision_model()

        model_to_use = vision_model or get_ai_model(mode)
        logger.info("[ask_ollama_vision_stream] Using model: %s, has_image: %s", model_to_use, bool(image_b64))

        import psutil
        cpu_count = psutil.cpu_count(logical=True) or 4
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        num_ctx = 2048 if ram_gb < 8 else 4096

        payload = {
            "model": model_to_use,
            "prompt": final_prompt,
            "stream": True,
            "think": False,  # disable thinking for vision calls too
            "options": {
                "temperature": temperature if temperature is not None else AI_TEMPERATURE,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "num_thread": cpu_count,
            }
        }
        if image_b64:
            payload["images"] = [image_b64]

        logger.info("Vision stream: model=%s, has_image=%s, prompt=%s",
            model_to_use, bool(image_b64), prompt[:80] + "...")

        with sync_client.stream("POST", f"{OLLAMA_URL}/api/generate", json=payload, timeout=120, skip_ssrf_check=True) as response:
            if response.status_code != 200:
                try:
                    err_data = response.json()
                    err_msg = err_data.get("error", "")
                except Exception:
                    err_msg = response.text

                logger.error("Ollama vision service returned status %d: %s", response.status_code, err_msg)

                if "memory" in err_msg.lower():
                    yield _make_error(f"Vision model '{model_to_use}' ran out of memory. Try a smaller model: ollama pull moondream")
                else:
                    yield _make_error(f"AI service unavailable (HTTP {response.status_code}).")
                return

            model_display = model_to_use
            yield _make_meta(model_display, "ollama")

            chunk_count = 0
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "response" in data:
                        chunk = data["response"]
                        if chunk.strip():
                            yield _make_content(chunk)
                            chunk_count += 1
                    if data.get("done", False):
                        break
                except json.JSONDecodeError as e:
                    logger.warning("Vision stream JSON decode error: %s", str(e))
                    continue
                except Exception as e:
                    logger.warning("Vision stream parse error: %s", str(e))
                    continue

        ms = int((time.time() - start) * 1000)
        logger.debug("Vision stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except httpx.TimeoutException:
        logger.error("Vision stream timeout after %ds", AI_TIMEOUT)
        yield _make_error("AI response timeout. Please try again.")
    except httpx.ConnectError:
        logger.error("Vision stream connection error")
        yield _make_error("Cannot connect to AI service. Is Ollama running?")
    except Exception as e:
        logger.error("Vision stream error: %s", e, exc_info=True)
        yield _make_error("AI error occurred.")


def _make_meta(model, provider):
    from lib.sse_helpers import make_meta
    return make_meta(model, provider)

def _make_content(chunk):
    from lib.sse_helpers import make_content
    return make_content(chunk)

def _make_done(ms):
    from lib.sse_helpers import make_done
    return make_done(ms)

def _make_error(msg):
    from lib.sse_helpers import make_error
    return make_error(msg)


def route_ai(prompt, mode="adaptive", style="concise"):
    resolved_mode, candidates = get_model_candidates(prompt, mode)
    last_error = None

    for candidate_mode, model_name in candidates:
        try:
            response = ask_ollama(prompt, mode=candidate_mode, model_name=model_name, style=style)
            cleaned = clean_ai_output(response)

            if cleaned and cleaned not in {"AI error", "AI service unavailable."}:
                return {
                    "response": cleaned,
                    "mode": candidate_mode,
                    "model": model_name
                }

            last_error = response
        except Exception as e:
            last_error = "An internal error occurred"
            logger.error("route_ai error: %s", str(e))

    return {
        "response": clean_ai_output(last_error or "AI error"),
        "mode": resolved_mode,
        "model": candidates[0][1] if candidates else get_ai_model("adaptive")
    }


async def route_ai_stream(prompt, mode="adaptive", style="concise", provider="ollama", messages=None, temperature=None):
    """
    Async generator that yields SSE event strings (meta, content, done, error).
    Cloud providers yield their own SSE strings directly.
    Ollama falls through to ask_ollama_stream().

    NOTE: This is `async def` because all the inner stream helpers
    (ask_ollama_stream, ask_gpt_stream, ...) are themselves async
    generators (patched in core/main.py:_patch_to_async_gen). Iterating
    them with sync `for` would raise "'async_generator' object is not
    iterable" — every inner `for event in stream_fn(...)` had to be
    converted to `async for` when this was made async.
    """
    # Check if provider is an Ollama Cloud model (has :cloud suffix)
    # e.g. "gpt-oss:20b", "qwen3.5:397b-cloud"
    is_ollama_cloud = provider and provider.endswith(":cloud")

    if is_ollama_cloud:
        # Ollama Cloud model — use cloud_providers module
        if not _has_provider_key_fast("ollama-cloud"):
            logger.info("[route_ai_stream] Ollama Cloud model '%s' selected but no key — falling back to local Ollama", provider)
            # Fall through to local Ollama below
        else:
            try:
                # Use absolute import (modules.platform.cloud_providers).
                # Bare `from cloud_providers import` resolves to a SECOND
                # module instance that's NOT patched by core/main.py:116-121
                # — stream functions stay as sync generators, and the
                # `async for` below crashes with "'async for' requires an
                # object with __aiter__ method, got generator".
                from modules.platform.cloud_providers import ask_ollama_cloud_stream
                async for event in ask_ollama_cloud_stream(prompt, model=provider, mode=mode, style=style, messages=messages, temperature=temperature):
                    yield event
                return
            except Exception as e:
                logger.error("Ollama Cloud stream error: %s", str(e))
                # Fall through to local Ollama instead of hard error

    # Check if provider looks like a local Ollama model name (contains colon)
    # e.g. "qwen2.5:1.5b", "deepseek-r1:8b"
    if provider and ":" in provider and not is_ollama_cloud:
        # This is a local Ollama model — use Ollama streaming directly
        try:
            async for event in ask_ollama_stream(prompt, mode=mode, model_name=provider, style=style, messages=messages, temperature=temperature):
                yield event
            return
        except Exception as e:
            logger.error("Ollama stream error: %s", str(e))
            yield _make_error(f"Ollama error: {e}")
            return

    # "auto" mode — race available cloud providers for fastest response
    if provider == "auto":
        try:
            # Absolute import — see comment at line 628 above. Bare
            # `from cloud_providers import` resolves to a second
            # (unpatched) module instance.
            from modules.platform.cloud_providers import PROVIDER_MODEL_MAP, get_stream_fn
            import os as _os
            # Speed priority: groq > google > openai > anthropic
            SPEED_PRIORITY = [
                "groq-llama-3-3-70b", "google-gemini-2-0-flash",
                "openai-gpt-4o-mini", "anthropic-claude-3-5-haiku",
            ]
            # Find first fast cloud provider that has a stream function and API key (cached, zero HTTP calls)
            for fast_model in SPEED_PRIORITY:
                if fast_model in PROVIDER_MODEL_MAP:
                    provider_prefix, model_name = PROVIDER_MODEL_MAP[fast_model]
                    stream_fn = get_stream_fn(provider_prefix)
                    if stream_fn and _has_provider_key_fast(provider_prefix):
                        logger.info("[route_ai_stream] auto → %s (%s)", fast_model, provider_prefix)
                        async for event in stream_fn(prompt, model=model_name, mode=mode, style=style, messages=messages, temperature=temperature):
                            yield event
                        return
            logger.info("[route_ai_stream] auto → no paid cloud keys found, trying Ollama Cloud")
            # Try free Ollama Cloud (gemma3) as fallback
            if _has_provider_key_fast("ollama-cloud"):
                try:
                    # Absolute import — see comment at line 628.
                    from modules.platform.cloud_providers import ask_ollama_cloud_stream
                    logger.info("[route_ai_stream] auto → Ollama Cloud (gemma3:cloud)")
                    async for event in ask_ollama_cloud_stream(prompt, model="gemma3:cloud", mode=mode, style=style, messages=messages, temperature=temperature):
                        yield event
                    return
                except Exception:
                    pass  # nosec B110
            logger.info("[route_ai_stream] auto → no Ollama Cloud key, falling back to local Ollama")
        except Exception as e:
            logger.error("[route_ai_stream] auto cloud race error: %s", str(e))

    # Cloud providers (OpenAI, Anthropic, Google, etc.) — use cloud_providers module
    if provider and provider != "ollama" and "-" in provider:
        try:
            # Absolute import — see comment at line 628. This is the
            # path the user hit as "Cloud AI error: 'async for' requires
            # an object with __aiter__ method, got generator".
            from modules.platform.cloud_providers import get_stream_fn, PROVIDER_MODEL_MAP
            stream_fn = get_stream_fn(provider)
            if stream_fn:
                resolved = PROVIDER_MODEL_MAP.get(provider, ("openai", "gpt-4o-mini"))
                model_name = resolved[1]
                async for event in stream_fn(prompt, model=model_name, mode=mode, style=style, messages=messages, temperature=temperature):
                    yield event
                return
        except Exception as e:
            logger.error("Cloud stream error: %s", str(e))
            yield _make_error(f"Cloud AI error: {e}")
            return

    # Ollama — iterate candidates until one succeeds
    resolved_mode, candidates = get_model_candidates(prompt, mode)

    for candidate_mode, model_name in candidates:
        try:
            accumulated = []
            async for event in ask_ollama_stream(prompt, mode=candidate_mode, model_name=model_name, style=style, messages=messages, temperature=temperature):
                accumulated.append(event)
                # Check for error early
                if event.startswith("event: error"):
                    accumulated = []
                    break
                yield event

            if accumulated:
                return

        except Exception as e:
            logger.error("AI stream error: %s", str(e))

    yield _make_error("AI error")


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP WARMUP — Non-blocking background tasks
# ═══════════════════════════════════════════════════════════════════════════════

# Warm provider keys in background (avoids per-request HTTP calls)
threading.Thread(target=_warm_provider_keys, daemon=True, name="provider-key-warmup").start()

# Discover vision model in background (avoids 5s blocking call on first use)
threading.Thread(target=_discover_vision_model, daemon=True, name="vision-model-warmup").start()
