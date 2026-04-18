"""
vision_describer.py - Two-step vision pipeline: Step 1 (image description)

Streams a concise description of the screenshot from the fastest available
vision provider (cloud race or local Ollama), then hands the description
text to Step 2 (main AI) for the final response.
"""

import json
import logging
import os
import time
import threading
import queue as queue_mod

from lib.sse_helpers import make_vision, make_vision_done, make_error
from lib.http_client import sync_client

logger = logging.getLogger("vision_describer")

VISION_DESCRIPTION_PROMPT = (
    "Describe this screenshot concisely. "
    "Include: visible text, UI elements, data/charts, and key visual context. "
    "Be specific and factual. Omit commentary."
)

# Max tokens for description — keep it short for speed
VISION_MAX_TOKENS = 200


def _has_ollama_cloud_key():
    """Check if Ollama Cloud API key is available."""
    try:
        key_secret = os.getenv("KEY_SERVER_SECRET", "")
        headers = {}
        if key_secret:
            headers["X-Key-Server-Secret"] = key_secret
        resp = sync_client.post(
            "http://127.0.0.1:18000/get-key",
            json={"provider": "ollama-cloud"},
            headers=headers,
            timeout=2,
            skip_ssrf_check=True,  # internal key server, not user-supplied
        )
        return resp.status_code == 200 and bool(resp.json().get("apiKey"))
    except Exception:
        return False


def stream_vision_description(
    image_b64: str,
    vision_providers: list,
    ollama_vision_model: str = None,
    provider_prefix: str = None,
    resolved_model: str = None,
    mode: str = "race",
    style: str = "concise",
):
    """
    Step 1 of the two-step vision pipeline.

    Streams vision description events, then yields vision_done.
    Returns nothing directly — yields SSE event strings via generator.

    Args:
        image_b64: Base64-encoded screenshot
        vision_providers: List of available cloud provider names (e.g. ["google", "groq"])
        ollama_vision_model: Name of local Ollama vision model (e.g. "llava")
        provider_prefix: Specific provider selected by user (e.g. "google")
        resolved_model: Specific model name (e.g. "gemini-2.0-flash")
        mode: AI mode
        style: AI style
    """
    from cloud_providers import VISION_PROVIDER_MAP, get_vision_stream_fn, OLLAMA_CLOUD_VISION_MODELS

    # If no paid cloud vision keys, add free Ollama Cloud vision providers
    if not vision_providers and _has_ollama_cloud_key():
        vision_providers = list(vision_providers)  # Don't mutate caller's list
        vision_providers.append("ollama-cloud")
        logger.info("[VisionDescriber] No paid vision keys, using free Ollama Cloud vision")

    # Single provider path: user selected a specific vision model
    if provider_prefix and provider_prefix in vision_providers:
        stream_fn = get_vision_stream_fn(provider_prefix)
        model = resolved_model or VISION_PROVIDER_MAP.get(provider_prefix, "gpt-4o")
        if stream_fn:
            yield from _single_provider_description(stream_fn, image_b64, model, provider_prefix)
            return

    # Ollama-only: no cloud keys available (not even Ollama Cloud)
    if not vision_providers and ollama_vision_model:
        yield from _ollama_description(image_b64, ollama_vision_model)
        return

    # No vision providers at all
    if not vision_providers:
        yield make_error("No vision providers available. Add an API key or enable Ollama Cloud.")
        return

    # Race mode: all cloud providers + Ollama race, fastest description wins
    yield from _race_description(image_b64, vision_providers, ollama_vision_model)


def _single_provider_description(stream_fn, image_b64, model, provider_prefix):
    """Stream description from a single selected provider."""
    start = time.time()
    full_description = ""
    try:
        for event in stream_fn(
            VISION_DESCRIPTION_PROMPT,
            image_b64=image_b64,
            model=model,
            mode="race",
            style="concise",
        ):
            # Check if this is an error event
            if "event: error" in event:
                yield event
                return
            # Check if this is a meta event — skip it (we'll emit our own)
            if '"type":"meta"' in event or '"type": "meta"' in event:
                continue
            # Check if this is a content chunk — convert to vision event
            if '"type":"chunk"' in event or '"type": "chunk"' in event:
                try:
                    data_line = [l for l in event.split("\n") if l.startswith("data:")][0]
                    data = json.loads(data_line[5:].strip())
                    content = data.get("content", "")
                    if content:
                        full_description += content
                        yield make_vision(content, provider_prefix)
                except (json.JSONDecodeError, IndexError):
                    pass
                continue
            # Check if done event
            if '"type":"done"' in event or '"type": "done"' in event:
                continue

        ms = int((time.time() - start) * 1000)
        yield make_vision_done(ms, provider_prefix)

    except Exception as e:
        logger.error("[VisionDescriber] Single provider %s error: %s", provider_prefix, e)
        yield make_error(f"Vision description failed: {e}")


def _ollama_description(image_b64, model_name):
    """Stream description from local Ollama vision model."""
    from ai_router import ask_ollama_vision_stream
    start = time.time()
    full_description = ""
    try:
        for event in ask_ollama_vision_stream(
            VISION_DESCRIPTION_PROMPT,
            image_b64=image_b64,
            mode="race",
            style="concise",
            model_name=model_name,
        ):
            if "event: error" in event:
                yield event
                return
            if '"type":"meta"' in event or '"type": "meta"' in event:
                continue
            if '"type":"chunk"' in event or '"type": "chunk"' in event:
                try:
                    data_line = [l for l in event.split("\n") if l.startswith("data:")][0]
                    data = json.loads(data_line[5:].strip())
                    content = data.get("content", "")
                    if content:
                        full_description += content
                        yield make_vision(content, "ollama")
                except (json.JSONDecodeError, IndexError):
                    pass
                continue
            if '"type":"done"' in event or '"type": "done"' in event:
                continue

        ms = int((time.time() - start) * 1000)
        yield make_vision_done(ms, "ollama")

    except Exception as e:
        logger.error("[VisionDescriber] Ollama description error: %s", str(e))
        yield make_error(f"Vision description failed: {e}")


def _race_description(image_b64, vision_providers, ollama_vision_model):
    """Race all available vision providers — first description wins."""
    from cloud_providers import VISION_PROVIDER_MAP, get_vision_stream_fn

    race_start = time.time()

    # Sort by speed: paid cloud first, then free Ollama Cloud, then local Ollama
    SPEED_PRIORITY = {"groq": 0, "google": 1, "openai": 2, "anthropic": 3, "ollama-cloud": 4}
    all_providers = list(vision_providers)
    if ollama_vision_model and "ollama" not in all_providers:
        all_providers.append("ollama")
    all_providers.sort(key=lambda p: SPEED_PRIORITY.get(p, 99))

    logger.info("[VisionDescriber] Race: %s (ollama=%s)", all_providers, ollama_vision_model)

    race_queue = queue_mod.Queue()
    cancel_flags = {p: threading.Event() for p in all_providers}

    def stream_provider(provider_name):
        """Stream from a vision provider into the shared queue."""
        p_start = time.time()
        try:
            if provider_name == "ollama":
                from ai_router import ask_ollama_vision_stream
                stream_iter = ask_ollama_vision_stream(
                    VISION_DESCRIPTION_PROMPT,
                    image_b64=image_b64,
                    mode="race",
                    style="concise",
                    model_name=ollama_vision_model,
                )
            else:
                stream_fn = get_vision_stream_fn(provider_name)
                model = VISION_PROVIDER_MAP.get(provider_name)
                if stream_fn is None:
                    race_queue.put((provider_name, "ERROR", f"No stream fn for {provider_name}"))
                    race_queue.put((provider_name, "DONE", None))
                    return
                stream_iter = stream_fn(
                    VISION_DESCRIPTION_PROMPT,
                    image_b64=image_b64,
                    model=model,
                    mode="race",
                    style="concise",
                )

            for event in stream_iter:
                if cancel_flags[provider_name].is_set():
                    logger.info("[VISION DESC CANCELLED] %s after %.1fs", provider_name, time.time() - p_start)
                    race_queue.put((provider_name, "DONE", None))
                    return
                if "event: error" in event:
                    race_queue.put((provider_name, "ERROR", event))
                elif '"type":"chunk"' in event or '"type": "chunk"' in event:
                    # Extract content from chunk event
                    try:
                        data_line = [l for l in event.split("\n") if l.startswith("data:")][0]
                        data = json.loads(data_line[5:].strip())
                        content = data.get("content", "")
                        if content:
                            race_queue.put((provider_name, "CONTENT", content))
                    except (json.JSONDecodeError, IndexError):
                        pass
                # Skip meta and done events from the provider

            race_queue.put((provider_name, "DONE", None))

        except Exception as e:
            logger.error("[VISION DESC ERROR] %s: %s", provider_name, e)
            race_queue.put((provider_name, "ERROR", "An internal error occurred"))
            race_queue.put((provider_name, "DONE", None))

    # Start all provider threads
    threads = []
    for vp in all_providers:
        t = threading.Thread(target=stream_provider, args=(vp,), daemon=True)
        t.start()
        threads.append(t)

    # Generator: consume from queue, first CONTENT wins
    winner = None
    active_count = len(all_providers)
    done_count = 0
    full_description = ""

    while done_count < active_count:
        try:
            pk, event_type, event_data = race_queue.get(timeout=30)
        except queue_mod.Empty:
            logger.warning("[VISION DESC RACE] Timeout waiting for providers")
            break

        if event_type == "CONTENT":
            if winner is None:
                winner = pk
                logger.info("[VISION DESC RACE WINNER] %s in %.1fs", pk, time.time() - race_start)
                # Cancel all losers
                for other in cancel_flags:
                    if other != pk:
                        cancel_flags[other].set()
            if pk == winner:
                full_description += event_data
                yield make_vision(event_data, winner)

        elif event_type == "ERROR":
            logger.info("[VISION DESC RACE] %s error: %s", pk, str(event_data)[:80])

        elif event_type == "DONE":
            done_count += 1

    # Yield vision_done
    ms = int((time.time() - race_start) * 1000)
    provider_name = winner or "unknown"
    yield make_vision_done(ms, provider_name)

    if not full_description:
        yield make_error("All vision providers failed to describe the image")

    logger.info("[VISION DESC RACE COMPLETE] winner=%s, total=%.1fs, desc_len=%d",
                winner, time.time() - race_start, len(full_description))