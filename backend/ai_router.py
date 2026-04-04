import json
import logging
import re

import requests

from config import AI_TEMPERATURE, AI_TIMEOUT, OLLAMA_URL, get_ai_model, MODEL_TURBO, TURBO_MAX_TOKENS, INSTANT_MAX_TOKENS
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


def _get_vision_model():
    """
    Return the name of an available vision-capable Ollama model, or None if none found.
    Caches result for the session lifetime.
    """
    global _vision_model_cache
    if _vision_model_cache is not None:
        logger.info("[_get_vision_model] Using cached vision model: %s", _vision_model_cache)
        return _vision_model_cache

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            logger.info("[_get_vision_model] Available models: %s", [m.get("name") for m in models])
            for m in models:
                name = m.get("name", "")
                for vision_name in VISION_MODEL_NAMES:
                    if vision_name in name.lower():
                        _vision_model_cache = name
                        logger.info("[_get_vision_model] Found vision model: %s", name)
                        return name
    except Exception as e:
        logger.warning("Could not fetch Ollama models to find vision model: %s", e)

    _vision_model_cache = None
    logger.warning("[_get_vision_model] No vision-capable model found")
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

    # Retrieve relevant document context if RAG is enabled
    rag_block = ""
    if include_rag:
        try:
            from document_store import get_document_store
            doc_store = get_document_store()
            rag_context = doc_store.format_context_for_prompt(user_input)
            if rag_context:
                rag_block = rag_context
        except Exception as e:
            logger.debug(f"RAG retrieval failed: {e}")

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

    return base


def ask_ollama(prompt, mode=AI_MODE, model_name=None, style="concise"):
    try:
        final_prompt = build_prompt(prompt, mode, style)

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name or get_ai_model(mode),
                "prompt": final_prompt,
                "stream": False,
                "options": {
                    "temperature": AI_TEMPERATURE
                }
            },
            timeout=AI_TIMEOUT
        )

        if response.status_code != 200:
            return "AI service unavailable."

        data = response.json()
        return data.get("response", "").strip()

    except Exception as e:
        logger.error("ask_ollama error: %s", e)
        return "AI error"


def ask_ollama_stream(prompt, mode=AI_MODE, model_name=None, style="concise", messages=None):
    """Yields SSE event strings — meta, content chunks, done, error."""
    import time
    start = time.time()
    try:
        logger.info("Streaming (%s mode, %s style): %s", mode, style, prompt[:100] + "..." if len(prompt) > 100 else prompt)

        final_prompt = build_prompt(prompt, mode, style, messages)

        # Cloud models like qwen3.5:397b-cloud and minimax-m2.7:cloud are more capable
        # and produce better responses, so give them more tokens
        is_cloud_model = model_name and (":cloud" in str(model_name) or "-cloud" in str(model_name))
        is_turbo = mode == "turbo"
        is_instant = mode == "instant"
        num_predict = INSTANT_MAX_TOKENS if is_instant else (TURBO_MAX_TOKENS if is_turbo else (2000 if is_cloud_model else (300 if style == "concise" else (2000 if style == "detailed" else 500))))
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name or get_ai_model(mode),
                "prompt": final_prompt,
                "stream": True,
                "options": {
                    "temperature": AI_TEMPERATURE,
                    "num_predict": num_predict
                }
            },
            stream=True,
            timeout=AI_TIMEOUT
        )

        if response.status_code != 200:
            logger.error("Ollama service returned status %d", response.status_code)
            yield _make_error(f"AI service unavailable (HTTP {response.status_code}).")
            return

        model_display = model_name or get_ai_model(mode)
        yield _make_meta(model_display, "ollama")

        chunk_count = 0
        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8", errors="replace"))

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
                logger.warning("Stream parse error: %s", e)
                continue

        ms = int((time.time() - start) * 1000)
        logger.debug("Stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except requests.exceptions.Timeout:
        logger.error("Ollama streaming timeout after %ds", AI_TIMEOUT)
        yield _make_error("AI response timeout. Please try again.")

    except requests.exceptions.ConnectionError:
        logger.error("Ollama connection error")
        yield _make_error("Cannot connect to AI service. Is Ollama running?")

    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        yield _make_error("AI error occurred.")


def ask_ollama_vision_stream(prompt, image_b64=None, mode="adaptive", style="concise", messages=None, model_name=None):
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

        payload = {
            "model": model_to_use,
            "prompt": final_prompt,
            "stream": True,
            "options": {
                "temperature": AI_TEMPERATURE,
                "num_predict": num_predict
            }
        }
        if image_b64:
            payload["images"] = [image_b64]

        logger.info("Vision stream: model=%s, has_image=%s, prompt=%s",
            model_to_use, bool(image_b64), prompt[:80] + "...")

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=120
        )

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
                data = json.loads(line.decode("utf-8", errors="replace"))
                if "response" in data:
                    chunk = data["response"]
                    if chunk.strip():
                        yield _make_content(chunk)
                        chunk_count += 1
                if data.get("done", False):
                    break
            except json.JSONDecodeError as e:
                logger.warning("Vision stream JSON decode error: %s", e)
                continue
            except Exception as e:
                logger.warning("Vision stream parse error: %s", e)
                continue

        ms = int((time.time() - start) * 1000)
        logger.debug("Vision stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except requests.exceptions.Timeout:
        logger.error("Vision stream timeout after %ds", AI_TIMEOUT)
        yield _make_error("AI response timeout. Please try again.")
    except requests.exceptions.ConnectionError:
        logger.error("Vision stream connection error")
        yield _make_error("Cannot connect to AI service. Is Ollama running?")
    except Exception as e:
        logger.error("Vision stream error: %s", e, exc_info=True)
        yield _make_error("AI error occurred.")


def _make_meta(model, provider):
    return f"event: meta\ndata: {{\"type\":\"meta\",\"model\":\"{model}\",\"provider\":\"{provider}\"}}\n\n"

def _make_content(chunk):
    import json
    return f"event: chunk\ndata: {json.dumps({'type':'chunk','content':chunk})}\n\n"

def _make_done(ms):
    return f"event: done\ndata: {{\"type\":\"done\",\"ms\":{ms}}}\n\n"

def _make_error(msg):
    import json
    return f"event: error\ndata: {json.dumps({'type':'error','message':msg})}\n\n"


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
            last_error = str(e)
            logger.error("route_ai error: %s", e)

    return {
        "response": clean_ai_output(last_error or "AI error"),
        "mode": resolved_mode,
        "model": candidates[0][1] if candidates else get_ai_model("adaptive")
    }


def route_ai_stream(prompt, mode="adaptive", style="concise", provider="ollama", messages=None):
    """
    Yields SSE event strings (meta, content, done, error).
    Cloud providers yield their own SSE strings directly.
    Ollama falls through to ask_ollama_stream().
    """
    # Check if provider is an Ollama Cloud model (has :cloud suffix)
    # e.g. "minimax-m2.7:cloud", "qwen3.5:397b-cloud"
    is_ollama_cloud = provider and provider.endswith(":cloud")

    if is_ollama_cloud:
        # Ollama Cloud model — use cloud_providers module
        try:
            from cloud_providers import ask_ollama_cloud_stream
            for event in ask_ollama_cloud_stream(prompt, model=provider, mode=mode, style=style, messages=messages):
                yield event
            return
        except Exception as e:
            logger.error("Ollama Cloud stream error: %s", e)
            yield _make_error(f"Ollama Cloud error: {e}")
            return

    # Check if provider looks like a local Ollama model name (contains colon)
    # e.g. "qwen2.5:1.5b", "deepseek-r1:8b"
    if provider and ":" in provider and not is_ollama_cloud:
        # This is a local Ollama model — use Ollama streaming directly
        try:
            for event in ask_ollama_stream(prompt, mode=mode, model_name=provider, style=style, messages=messages):
                yield event
            return
        except Exception as e:
            logger.error("Ollama stream error: %s", e)
            yield _make_error(f"Ollama error: {e}")
            return

    # Cloud providers (OpenAI, Anthropic, Google, etc.) — use cloud_providers module
    if provider and provider != "ollama" and "-" in provider:
        try:
            from cloud_providers import get_stream_fn, PROVIDER_MODEL_MAP
            stream_fn = get_stream_fn(provider)
            if stream_fn:
                resolved = PROVIDER_MODEL_MAP.get(provider, ("openai", "gpt-4o-mini"))
                model_name = resolved[1]
                for event in stream_fn(prompt, model=model_name, mode=mode, style=style, messages=messages):
                    yield event
                return
        except Exception as e:
            logger.error("Cloud stream error: %s", e)
            yield _make_error(f"Cloud AI error: {e}")
            return

    # Ollama — iterate candidates until one succeeds
    resolved_mode, candidates = get_model_candidates(prompt, mode)

    for candidate_mode, model_name in candidates:
        try:
            accumulated = []
            for event in ask_ollama_stream(prompt, mode=candidate_mode, model_name=model_name, style=style, messages=messages):
                accumulated.append(event)
                # Check for error early
                if event.startswith("event: error"):
                    accumulated = []
                    break
                yield event

            if accumulated:
                return

        except Exception as e:
            logger.error("AI stream error: %s", e)

    yield _make_error("AI error")
