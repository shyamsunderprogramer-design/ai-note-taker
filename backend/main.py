import asyncio
import concurrent.futures
import json
import logging
import os
import queue
import re
import requests
import shutil
import signal
import sys
import threading
import time

from fastapi import FastAPI, File, Form, Query, UploadFile, WebSocket
from fastapi.responses import StreamingResponse

from ai_router import build_prompt, clean_ai_output, route_ai, route_ai_stream
from config import OLLAMA_URL
from whisper_handler import (
    clean_text,
    is_meaningful,
    is_question,
    is_small_talk,
    is_technical,
    record_audio,
    transcribe,
    transcribe_audio,
)

sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI()

# Sanitize API keys from uvicorn access logs
class APIKeyFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r"api_key=[^&\s]*", "api_key=***", str(record.msg))
        return True

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(APIKeyFilter())

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def cleanup_temp_audio():
    """Remove old temp audio files on startup."""
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith((".webm", ".wav")):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except OSError:
                    pass

last_query_time = 0
CURRENT_MODE = "auto"
COOLDOWN_SECONDS = 5

USE_AUTONOMOUS = False
listener_thread = None
lock = threading.Lock()

STATE = {
    "is_streaming": False
}


def autonomous_listener():
    global last_query_time, USE_AUTONOMOUS

    text_buffer = ""
    last_heard_time = time.time()

    def get_silence_threshold():
        if CURRENT_MODE == "interview":
            return 1.8
        return 2.5

    min_words = 1 if CURRENT_MODE == "interview" else 3

    while USE_AUTONOMOUS:
        try:
            if STATE["is_streaming"]:
                time.sleep(0.2)
                continue

            audio = record_audio(duration=2)
            text = clean_text(transcribe(audio, mode=CURRENT_MODE))

            if text:
                text_buffer += " " + text
                last_heard_time = time.time()

            time.sleep(0.3)

            if time.time() - last_heard_time < get_silence_threshold():
                continue

            final_text = text_buffer.strip()
            text_buffer = ""

            if not final_text:
                continue

            if not is_meaningful(final_text):
                continue

            if len(final_text.split()) < min_words:
                continue

            if not is_question(final_text):
                continue

            if is_small_talk(final_text):
                continue

            if CURRENT_MODE == "interview" and not is_technical(final_text):
                continue

            with lock:
                if time.time() - last_query_time < COOLDOWN_SECONDS:
                    continue
                last_query_time = time.time()

            for _chunk in route_ai_stream(final_text, mode=CURRENT_MODE):
                pass

        except Exception as e:
            print("[ERROR] Listener error:", e)


@app.on_event("startup")
def start_listener():
    global listener_thread

    # Clean up stale temp audio files on startup
    cleanup_temp_audio()

    if USE_AUTONOMOUS and listener_thread is None:
        listener_thread = threading.Thread(target=autonomous_listener, daemon=True)
        listener_thread.start()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "ai-backend",
        "mode": CURRENT_MODE
    }


@app.get("/providers")
def list_providers():
    """Returns which cloud providers have API keys configured"""
    from dotenv import load_dotenv
    import os
    load_dotenv()

    return {
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "google": bool(os.getenv("GOOGLE_API_KEY", "").strip()),
        "xai": bool(os.getenv("XAI_API_KEY", "").strip()),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
        "groq": bool(os.getenv("GROQ_API_KEY", "").strip()),
        "ollama": True  # Ollama is always available if configured
    }


@app.get("/ollama/models")
def list_ollama_models():
    """Proxy to Ollama's GET /api/tags — returns installed local models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Ollama returned {response.status_code}", "models": []}
    except Exception as e:
        return {"error": str(e), "models": []}


@app.post("/ollama/pull")
def pull_ollama_model(model: str = Query(...)):
    """Trigger a model pull — runs async, returns immediately."""
    import threading
    def background_pull():
        try:
            logger.info("Starting model pull: %s", model)
            pull_resp = requests.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": model},
                stream=True,
                timeout=3600
            )
            # Read the stream to ensure completion (or failure)
            for line in pull_resp.iter_lines():
                if line:
                    logger.info("[Ollama pull] %s", line.decode("utf-8", errors="replace"))
            logger.info("Model pull complete: %s", model)
        except Exception as e:
            logger.error("Model pull failed for %s: %s", model, e)

    threading.Thread(target=background_pull, daemon=True).start()
    return {"status": "pull_started", "model": model}


@app.delete("/ollama/models/{model_name}")
def delete_ollama_model(model_name: str):
    """Delete a local Ollama model."""
    try:
        response = requests.delete(
            f"{OLLAMA_URL}/api/delete",
            json={"name": model_name},
            timeout=30
        )
        if response.status_code == 200:
            return {"status": "deleted", "model": model_name}
        return {"error": f"Failed to delete model: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/ask-with-image")
async def ask_with_image(
    query: str = Form(...),
    mode: str = Form("adaptive"),
    style: str = Form("concise"),
    provider: str = Form("ollama"),
    context: str = Form(None),
    image_b64: str = Form(None)
):
    """Accept text + optional base64 screenshot, stream AI response via SSE."""
    messages = None
    if context:
        try:
            import json
            messages = json.loads(context)
        except Exception:
            pass

    def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream
            for event in ask_ollama_vision_stream(query, image_b64=image_b64, mode=mode, style=style, messages=messages):
                yield event
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/configure")
async def configure_provider(body: dict):
    """Save API key for a cloud provider — accepts JSON body (NOT query params)."""
    from dotenv import load_dotenv
    import os
    load_dotenv()

    provider = body.get("provider")
    api_key = body.get("api_key")

    valid_providers = ["openai", "anthropic", "google", "xai", "deepseek", "groq"]
    if provider not in valid_providers:
        return {"error": "Invalid provider"}

    if not api_key:
        return {"error": "Missing api_key"}

    # Map provider names to env var names
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "groq": "GROQ_API_KEY"
    }

    # Save to .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    existing = {}

    if os.path.exists(env_path):
        load_dotenv(env_path)
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    existing[k] = v

    existing[env_vars[provider]] = api_key

    with open(env_path, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    # Reload env
    load_dotenv()

    return {"status": "configured", "provider": provider}


@app.get("/health")
def health():
    return health_check()


@app.post("/set-mode")
def set_mode(mode: str):
    global CURRENT_MODE

    if mode not in ["auto", "fast", "cloud", "interview", "universal", "adaptive", "reasoning", "code"]:
        return {"error": "Invalid mode"}

    CURRENT_MODE = mode
    return {"status": "mode updated", "mode": CURRENT_MODE}


@app.post("/transcribe")
async def transcribe_api(file: UploadFile = File(...)):
    global USE_AUTONOMOUS

    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    result = subprocess.run(
        ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    # Clean up temp files immediately after use
    for path in (file_path, wav_path):
        try: os.remove(path)
        except OSError: pass

    if not text or not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": ""}

    result = route_ai(text, mode=CURRENT_MODE)
    return {
        "text": text,
        "response": clean_ai_output(result["response"]),
        "mode": result["mode"],
        "model": result["model"]
    }


@app.post("/transcribe-cloud")
async def transcribe_cloud(file: UploadFile = File(...), provider: str = "openai", model: str = "gpt-4o-mini"):
    """Transcribe and route to a cloud AI provider"""
    global USE_AUTONOMOUS

    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    result = subprocess.run(
        ["ffmpeg", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    # Clean up temp files immediately after transcription
    for path in (file_path, wav_path):
        try: os.remove(path)
        except OSError: pass

    if not text:
        return {"text": "", "response": "", "error": "No speech detected"}

    if not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": "", "error": "Not a meaningful question"}

    # Route to cloud provider
    try:
        from cloud_providers import ask_gpt, ask_claude, ask_gemini, ask_grok, ask_deepseek, ask_groq, clean_ai_output as cloud_clean

        prompt = build_prompt(text, CURRENT_MODE)

        if provider == "openai":
            resp = ask_gpt(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "anthropic":
            resp = ask_claude(prompt, model=model)
            response_text = resp.json()["content"][0]["text"]
        elif provider == "google":
            resp = ask_gemini(prompt, model=model)
            response_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "xai":
            resp = ask_grok(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "deepseek":
            resp = ask_deepseek(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        elif provider == "groq":
            resp = ask_groq(prompt, model=model)
            response_text = resp.json()["choices"][0]["message"]["content"]
        else:
            return {"text": text, "response": "", "error": f"Unknown provider: {provider}"}

        return {
            "text": text,
            "response": cloud_clean(response_text),
            "mode": provider,
            "model": model
        }

    except ValueError as e:
        return {"text": text, "response": "", "error": str(e)}
    except Exception as e:
        print("[ERROR cloud transcribe]:", e)
        return {"text": text, "response": "", "error": str(e)}


@app.get("/stream")
def stream_ai(q: str, mode: str = "fast", style: str = "concise", provider: str = "ollama", context: str = None):
    """SSE stream endpoint — yields event: meta/chunk/done/error"""
    def generator():
        STATE["is_streaming"] = True

        # Parse context messages from JSON
        messages = None
        if context:
            try:
                import json
                messages = json.loads(context)
            except Exception:
                pass

        try:
            # Yield provider/mode info as first event
            yield f"event: meta\ndata: {{\"type\":\"meta\",\"provider\":\"{provider}\"}}\n\n"

            for event in route_ai_stream(q, mode, style, provider, messages):
                yield event

        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"

        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/stream-race")
def stream_race(q: str, mode: str = "fast", style: str = "concise", context: str = None, enabled: str = None):
    """
    Fire all configured providers in parallel using ThreadPoolExecutor + as_completed.
    Returns the FIRST successful full response (ignores errors/429s from cloud providers).
    Falls back to Ollama if all clouds fail.
    Only providers specified in 'enabled' param (comma-separated) will be used.
    """
    from cloud_providers import MODEL_DISPLAY_NAMES, PROVIDER_MODEL_MAP, get_stream_fn
    import concurrent.futures
    import logging

    logger = logging.getLogger(__name__)

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
            pass

    from dotenv import load_dotenv
    load_dotenv()

    available = []
    # If enabled_set from frontend is provided, only use those providers
    if enabled_set:
        if "openai" in enabled_set and os.getenv("OPENAI_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if "anthropic" in enabled_set and os.getenv("ANTHROPIC_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if "google" in enabled_set and os.getenv("GOOGLE_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if "xai" in enabled_set and os.getenv("XAI_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if "deepseek" in enabled_set and os.getenv("DEEPSEEK_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if "groq" in enabled_set and os.getenv("GROQ_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
    else:
        # Legacy behavior: use all providers with API keys
        if os.getenv("OPENAI_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if os.getenv("ANTHROPIC_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if os.getenv("GOOGLE_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if os.getenv("XAI_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if os.getenv("DEEPSEEK_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if os.getenv("GROQ_API_KEY", "").strip():
            available.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])

    # Always add ollama
    available.append("ollama")

    # Deduplicate by provider name
    seen = set()
    selected = []
    for pk in available:
        pname = pk.split("-")[0]
        if pname not in seen:
            seen.add(pname)
            selected.append(pk)
    selected = selected[:4]  # Limit to 4 concurrent providers

    logger.info("Race mode: %s providers selected: %s", len(selected), selected)

    def fetch_events(pk):
        """Collect all SSE events from a provider. Returns (pk, events_list, error)."""
        try:
            if pk == "ollama":
                from ai_router import ask_ollama_stream
                events = list(ask_ollama_stream(q, mode=mode, style=style, messages=messages))
            else:
                resolved = PROVIDER_MODEL_MAP.get(pk, ("openai", "gpt-4o-mini"))
                model_name = resolved[1]
                stream_fn = get_stream_fn(pk)
                if stream_fn is None:
                    return (pk, [], f"No stream function for {pk}")
                events = list(stream_fn(q, model=model_name, mode=mode, style=style, messages=messages))
            # Check if events contains an error
            has_error = any("event: error" in e for e in events)
            if has_error:
                # Extract error message
                for e in events:
                    if "event: error" in e:
                        return (pk, [], e)
                return (pk, [], "Unknown error")
            logger.info("Provider %s succeeded with %d events", pk, len(events))
            return (pk, events, None)
        except Exception as e:
            logger.error("Provider %s failed: %s", pk, e)
            return (pk, [], str(e))

    def race_generator():
        from cloud_providers import MODEL_DISPLAY_NAMES
        STATE["is_streaming"] = True
        winner_found = False

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as executor:
                futures = {
                    executor.submit(fetch_events, pk): pk
                    for pk in selected
                }

                for future in concurrent.futures.as_completed(futures, timeout=60.0):
                    pk = futures[future]
                    try:
                        winner_pk, events, err = future.result(timeout=0)
                        if err is None and events and len(events) > 0:
                            # Success! Yield all events with winner info injected into meta
                            logger.info("Winner: %s", winner_pk)
                            winner_display = MODEL_DISPLAY_NAMES.get(winner_pk, winner_pk)
                            for event in events:
                                # Inject winner flag into the first meta event
                                if event.startswith("event: meta\n"):
                                    import re as _re
                                    m = _re.search(r"data: (\{.*\})\n\n", event)
                                    if m:
                                        meta_obj = json.loads(m.group(1))
                                        meta_obj["winner"] = True
                                        meta_obj["winnerName"] = winner_display
                                        event = f"event: meta\ndata: {json.dumps(meta_obj)}\n\n"
                                yield event
                            winner_found = True
                            # Cancel remaining futures and wait for them
                            for f in futures:
                                f.cancel()
                            # Wait for cancellation to complete before exiting with block
                            executor.shutdown(wait=True, cancel_futures=True)
                            break
                        # Error or empty — try next provider
                        logger.debug("Provider %s failed or empty, trying next", pk)
                    except concurrent.futures.CancelledError:
                        break
                    except Exception as e:
                        logger.warning("Exception in race loop: %s", e)

            if not winner_found:
                logger.error("All providers failed in race mode")
                yield f"event: error\ndata: {{\"type\":\"error\",\"message\":\"All providers failed\"}}\n\n"

        except Exception as e:
            logger.error("Race generator error: %s", e)
            yield f"event: error\ndata: {{\"type\":\"error\",\"message\":\"Race mode error: {str(e)}\"}}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(race_generator(), media_type="text/event-stream")


def shutdown_handler(*args):
    global USE_AUTONOMOUS
    USE_AUTONOMOUS = False
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    while True:
        msg = await ws.receive_text()
        result = route_ai(msg, mode=CURRENT_MODE)
        await ws.send_text(clean_ai_output(result["response"]))
