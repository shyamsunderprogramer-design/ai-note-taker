import asyncio
import concurrent.futures
import json
import logging
import os
import platform
import queue
import re
import requests
import shutil
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from fastapi import FastAPI, File, Form, Query, Request, UploadFile, WebSocket
from fastapi.responses import StreamingResponse

from ai_router import build_prompt, clean_ai_output, route_ai, route_ai_stream
from config import OLLAMA_URL
from whisper_handler import (
    BrowserTranscriber,
    clean_text,
    get_model,
    get_streaming_transcriber,
    is_meaningful,
    is_question,
    is_small_talk,
    is_technical,
    record_audio,
    transcribe,
    transcribe_audio,
    warmup,
)

# Cognitive Graph - Phase 1 Personal Knowledge Graph
try:
    from cognitive_graph import (
        cognitive_graph,
        initialize_graph,
        ingest_conversation,
        query_graph,
        InterviewNode,
        QuestionNode,
        AnswerNode,
        CompanyNode,
        TopicNode,
        SkillNode
    )
    COGNITIVE_GRAPH_AVAILABLE = True
except ImportError:
    COGNITIVE_GRAPH_AVAILABLE = False
    logger = logging.getLogger("main")
    logger.warning("[CognitiveGraph] Module not available. Run: pip install neo4j spacy")

sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI()

logger = logging.getLogger("main")

# Sanitize API keys from uvicorn access logs
class APIKeyFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r"api_key=[^&\s]*", "api_key=***", str(record.msg))
        return True

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(APIKeyFilter())

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_secure_filename(original_filename: str) -> str:
    """Generate a secure filename to prevent path traversal attacks.

    Returns a UUID-based filename with the same extension.
    """
    import uuid
    # Extract extension safely
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1].lower()
        # Only allow safe extensions
        allowed_exts = {"webm", "wav", "mp3", "mp4", "m4a", "ogg", "pdf", "txt", "md", "docx", "json"}
        if ext not in allowed_exts:
            ext = "bin"  # Default to bin for unknown extensions
    else:
        ext = "bin"
    return f"{uuid.uuid4()}.{ext}"


def sanitize_path(filename: str) -> str:
    """Sanitize filename to prevent directory traversal.

    Rejects paths containing .. or absolute paths.
    """
    import re
    # Reject paths with directory traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename or filename.startswith((".", "/", "\\", "~")):
        raise ValueError(f"Invalid filename: {filename}")
    # Only allow alphanumeric, dots, dashes, underscores
    if not re.match(r"^[\w\-\.]+$", filename):
        raise ValueError(f"Invalid filename characters: {filename}")
    return filename

def cleanup_temp_audio():
    """Remove old temp audio files on startup."""
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith((".webm", ".wav")):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except OSError:
                    pass


def get_ffmpeg_path():
    """
    Cross-platform ffmpeg path finder.
    Checks common install locations for each platform.
    """
    system = platform.system()

    # If ffmpeg is in PATH, use it
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    if system == "Windows":
        # Common Windows install locations
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
        ]
    elif system == "Darwin":
        candidates = [
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            "/opt/local/bin/ffmpeg",
        ]
    else:  # Linux
        candidates = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
        ]

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    # Fallback to just "ffmpeg" (will fail with clear error if not installed)
    return "ffmpeg"


last_query_time = 0
CURRENT_MODE = "auto"
COOLDOWN_SECONDS = 5

USE_AUTONOMOUS = False
listener_thread = None
lock = threading.Lock()

STATE = {
    "is_streaming": False
}

always_on_mic_enabled = False


def autonomous_listener():
    global last_query_time, USE_AUTONOMOUS, always_on_mic_enabled

    from whisper_handler import get_streaming_transcriber, clean_text, is_meaningful, is_question, is_small_talk, is_technical, transcribe

    text_buffer = ""
    last_heard_time = time.time()
    silence_threshold = 2.5
    min_words = 3

    def get_silence_threshold():
        return 1.8 if CURRENT_MODE == "interview" else silence_threshold

    transcriber = get_streaming_transcriber()

    def on_transcript(text):
        """Called from streaming transcriber's transcription thread."""
        nonlocal last_heard_time
        cleaned = clean_text(text)
        if cleaned:
            text_buffer += " " + cleaned
            last_heard_time = time.time()

    transcriber.add_callback(on_transcript)
    transcriber.start()

    try:
        while USE_AUTONOMOUS and always_on_mic_enabled:
            try:
                if STATE["is_streaming"]:
                    time.sleep(0.2)
                    continue

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
                logger.error("[ERROR] Listener error: %s", e)
    finally:
        transcriber.stop()


@app.on_event("startup")
def start_listener():
    global listener_thread

    # Clean up stale temp audio files on startup
    cleanup_temp_audio()

    # Start Whisper warmup in background — doesn't block uvicorn startup
    # Transcription requests will wait for the model via model_ready.wait()
    threading.Thread(target=warmup, daemon=True).start()

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
    """Returns which cloud providers have API keys configured (secure storage + env fallback)"""
    import requests

    def has_key(provider, env_var):
        # Try secure server first
        try:
            resp = requests.post(
                "http://127.0.0.1:18000/get-key",
                json={"provider": provider},
                timeout=1
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("apiKey"):
                    return True
        except:
            pass
        # Fallback to env
        return bool(os.getenv(env_var, "").strip())

    return {
        "openai": has_key("openai", "OPENAI_API_KEY"),
        "anthropic": has_key("anthropic", "ANTHROPIC_API_KEY"),
        "google": has_key("google", "GOOGLE_API_KEY"),
        "xai": has_key("xai", "XAI_API_KEY"),
        "deepseek": has_key("deepseek", "DEEPSEEK_API_KEY"),
        "groq": has_key("groq", "GROQ_API_KEY"),
        "ollama-cloud": has_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"),
        "perplexity": has_key("perplexity", "PERPLEXITY_API_KEY"),
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
    logger.info("[ask-with-image] received: query=%s, mode=%s, style=%s, image_b64 present=%s", query, mode, style, "Yes" if image_b64 else "No")
    if image_b64:
        logger.info("[ask-with-image] image_b64 length=%d, first 50 chars=%s", len(image_b64), image_b64[:50])
    messages = None
    if context:
        try:
            import json
            messages = json.loads(context)
        except Exception:
            pass

    # When screenshot is provided, find a vision-capable model
    # (ignore non-vision provider selection when image is present)
    model_name = None
    if image_b64:
        from ai_router import _get_vision_model
        model_name = _get_vision_model()
        logger.info("[ask-with-image] Screenshot provided, vision model: %s", model_name)
        if not model_name:
            # No vision model found - return error
            def error_gen():
                import json
                yield f"event: error\ndata: {json.dumps({'type':'error','message':'No vision-capable model found. Please pull a vision model like llava:latest with: ollama pull llava:latest'})}\n\n"
            return StreamingResponse(error_gen(), media_type="text/event-stream")
    else:
        logger.info("[ask-with-image] No screenshot, using provider: %s", provider)

    def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream
            for event in ask_ollama_vision_stream(query, image_b64=image_b64, mode=mode, style=style, messages=messages, model_name=model_name):
                yield event
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/transcribe-stream")
async def transcribe_stream(request: Request):
    """SSE stream of real-time transcription from always-on microphone.

    The StreamingTranscriber runs in a background thread. This endpoint
    bridges it to SSE using a sync queue consumed in a thread executor
    so it never blocks the asyncio event loop.
    """
    loop = asyncio.get_event_loop()

    async def event_generator():
        transcriber = get_streaming_transcriber()

        # Sync queue — transcriber thread puts, async consumer gets
        client_queue = queue.Queue()

        def sync_queue_callback(text):
            try:
                client_queue.put_nowait(text)
            except Exception:
                pass
        transcriber.add_callback(sync_queue_callback)

        # Ensure transcriber is running
        transcriber.start()

        try:
            while True:
                if await request.is_disconnected():
                    break
                # Run blocking queue.get() in a thread with 1s timeout so event loop stays free
                try:
                    text = await loop.run_in_executor(None, lambda: client_queue.get(True, timeout=1))
                    import json
                    yield f"event: transcript\ndata: {json.dumps({'text': text})}\n\n"
                except queue.Empty:
                    # No transcription in queue within timeout — send ping so renderer can check silence
                    import json
                    yield f"event: ping\ndata: {json.dumps({'t': int(time.time())})}\n\n"
        except GeneratorExit:
            pass
        except Exception as e:
            logger.error("[transcribe-stream] error: %s", e)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/overlay-ask")
async def overlay_ask(
    request: Request,
    query: str = Form(...),
    screenshot_b64: str = Form(None)
):
    """Quick Q&A from overlay window with optional screenshot context.

    Uses fast/concise settings for quick responses.
    """
    logger.info("[overlay-ask] query=%s, has_screenshot=%s", query, bool(screenshot_b64))

    async def generator():
        STATE["is_streaming"] = True
        try:
            from ai_router import ask_ollama_vision_stream, _get_vision_model, route_ai_stream

            if screenshot_b64:
                model_name = _get_vision_model()
                logger.info("[overlay-ask] Screenshot present, vision model: %s", model_name)
                if not model_name:
                    import json
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
            import json
            yield f"event: error\ndata: {json.dumps({'type':'error','message': str(e)})}\n\n"
        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/set-always-on-mic")
async def set_always_on_mic(enabled: bool = Form(...)):
    """Enable or disable the always-on microphone.

    When enabled, the StreamingTranscriber runs continuously and
    transcription events are available via /transcribe-stream SSE.
    """
    global always_on_mic_enabled, USE_AUTONOMOUS

    always_on_mic_enabled = enabled
    USE_AUTONOMOUS = enabled
    transcriber = get_streaming_transcriber()

    if enabled:
        transcriber.start()
        logger.info("[AlwaysOnMic] Enabled")
    else:
        transcriber.stop()
        logger.info("[AlwaysOnMic] Disabled")

    return {"enabled": enabled}


@app.post("/configure")
async def configure_provider(body: dict):
    """API key configuration endpoint — DISABLED.

    SECURITY: API keys are no longer accepted over HTTP.
    Use secure IPC: window.api.saveApiKey(provider, apiKey)

    This endpoint returns an error to prevent accidental insecure key transmission.
    """
    # Reject any attempt to configure API keys over HTTP
    # Keys must be saved via secure IPC to encrypted storage
    return {
        "error": "HTTP configuration disabled for security",
        "message": "Use window.api.saveApiKey(provider, apiKey) for secure storage",
        "code": "INSECURE_TRANSPORT"
    }


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
    # Use secure filename to prevent path traversal
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
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
    # Use secure filename to prevent path traversal
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
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
    import time as time_module

    logger = logging.getLogger(__name__)
    race_start = time_module.time()
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
            pass

    # Secure key checking helper
    def has_secure_key(provider, env_var):
        try:
            resp = requests.post(
                "http://127.0.0.1:18000/get-key",
                json={"provider": provider},
                timeout=1
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("apiKey"):
                    return True
        except:
            pass
        return bool(os.getenv(env_var, "").strip())

    # Separate cloud and local providers
    cloud_providers = []
    local_providers = []

    # If enabled_set from frontend is provided, only use those providers
    if enabled_set:
        if "openai" in enabled_set and has_secure_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if "anthropic" in enabled_set and has_secure_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if "google" in enabled_set and has_secure_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if "xai" in enabled_set and has_secure_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if "deepseek" in enabled_set and has_secure_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if "groq" in enabled_set and has_secure_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if "ollama-cloud" in enabled_set and has_secure_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if "perplexity" in enabled_set and has_secure_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        # Only add local ollama if explicitly enabled in frontend
        if "ollama" in enabled_set:
            local_providers.append("ollama")
    else:
        # Legacy: use all cloud providers with API keys, plus ollama as fallback
        if has_secure_key("openai", "OPENAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("openai-")])
        if has_secure_key("anthropic", "ANTHROPIC_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("anthropic-")])
        if has_secure_key("google", "GOOGLE_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("google-")])
        if has_secure_key("xai", "XAI_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("xai-")])
        if has_secure_key("deepseek", "DEEPSEEK_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("deepseek-")])
        if has_secure_key("groq", "GROQ_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("groq-")])
        if has_secure_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"):
            cloud_providers.append("ollama-cloud")
        if has_secure_key("perplexity", "PERPLEXITY_API_KEY"):
            cloud_providers.extend([k for k in PROVIDER_MODEL_MAP if k.startswith("perplexity-")])
        # Add local ollama as fallback (always available)
        local_providers.append("ollama")

    # Deduplicate by provider name
    def deduplicate(provider_list):
        seen = set()
        result = []
        for pk in provider_list:
            pname = pk.split("-")[0]
            if pname not in seen:
                seen.add(pname)
                result.append(pk)
        return result

    cloud_providers = deduplicate(cloud_providers)[:4]  # Limit to 4 concurrent
    local_providers = deduplicate(local_providers)

    # Combine: clouds first, then local as fallback
    all_providers = cloud_providers + local_providers
    logger.info("Race mode: clouds=%s, local=%s, combined=%s", cloud_providers, local_providers, all_providers)

    def fetch_events(pk):
        """Collect all SSE events from a provider. Returns (pk, events_list, error)."""
        import time as fetch_time
        fetch_start = fetch_time.time()
        logger.info("[PROVIDER START] %s", pk)
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
            # Check if events contains an error — but track if any content was yielded first
            content_yielded = any(("event: chunk" in e or "event: meta" in e) and '"content"' in e for e in events)
            has_error = any("event: error" in e for e in events)
            if has_error:
                if content_yielded:
                    # Partial content before error — return it rather than discarding
                    logger.warning("[PROVIDER] %s returned error after content, returning partial (%.1fs)", pk, fetch_time.time() - fetch_start)
                    return (pk, events, None)
                for e in events:
                    if "event: error" in e:
                        return (pk, [], e)
                return (pk, [], "Unknown error")
            logger.info("Provider %s succeeded with %d events (%.1fs)", pk, len(events), fetch_time.time() - fetch_start)
            return (pk, events, None)
        except Exception as e:
            logger.error("Provider %s failed: %s (%.1fs)", pk, e, fetch_time.time() - fetch_start)
            return (pk, [], str(e))

    def race_generator():
        from cloud_providers import MODEL_DISPLAY_NAMES
        STATE["is_streaming"] = True
        winner_found = False

        # Use ThreadPoolExecutor to run providers in parallel
        # First completed provider with a valid response wins
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(all_providers)) as executor:
            # Submit all provider requests
            future_to_pk = {
                executor.submit(fetch_events, pk): pk
                for pk in all_providers
            }

            # Yield events from the first provider that completes successfully
            for future in concurrent.futures.as_completed(future_to_pk):
                pk = future_to_pk[future]
                try:
                    result_pk, events, error = future.result()
                    if error:
                        logger.warning("[RACE] provider %s returned error: %s", pk, error)
                        continue
                    if events:
                        # Found the winner! Stream their events
                        logger.info("[RACE] winner: %s", pk)
                        for event in events:
                            yield event
                        winner_found = True
                        break
                except Exception as e:
                    logger.warning("[RACE] provider %s raised exception: %s", pk, e)
                    continue

        if not winner_found:
            logger.error("All providers failed in race mode")
            yield f"event: error\ndata: {{\"type\":\"error\",\"message\":\"All providers failed\"}}\n\n"

        logger.info("[RACE COMPLETE] total_time=%.1fs", time_module.time() - race_start)
        STATE["is_streaming"] = False

    return StreamingResponse(race_generator(), media_type="text/event-stream")


# ==============================
# DOCUMENT UPLOAD & RAG ENDPOINTS
# ==============================

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for RAG context retrieval."""
    from document_store import get_document_store

    # Save uploaded file temporarily
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_store = get_document_store()
        result = doc_store.add_document(temp_path)

        # Clean up temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass

        return result
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        return {"error": str(e)}


@app.get("/documents")
async def list_documents():
    """List all uploaded documents."""
    from document_store import get_document_store
    doc_store = get_document_store()
    return {"documents": doc_store.list_documents()}


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the store."""
    from document_store import get_document_store
    doc_store = get_document_store()
    success = doc_store.delete_document(doc_id)
    return {"success": success}


@app.post("/documents/retrieve")
async def retrieve_document_context(query: str = Form(...), top_k: int = Form(5)):
    """Retrieve relevant document context for a query."""
    from document_store import get_document_store
    doc_store = get_document_store()
    results = doc_store.retrieve_context(query, top_k)
    return {"results": results}


# ==============================
# SPEAKER DIARIZATION ENDPOINTS
# ==============================

@app.post("/transcribe-with-speakers")
async def transcribe_with_speakers(file: UploadFile = File(...)):
    """
    Transcribe audio with speaker diarization.
    Returns transcription with speaker labels for each segment.
    """
    global USE_AUTONOMOUS
    from speaker_diarization import process_transcription_with_speakers
    from whisper_handler import get_streaming_transcriber

    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    import subprocess
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    try:
        # Get detailed transcription with timestamps from Whisper
        # Note: faster_whisper returns segments with timestamps
        model = get_model(CURRENT_MODE)
        segments, _ = model.transcribe(
            wav_path,
            beam_size=3,
            vad_filter=False,
            condition_on_previous_text=False,
            language="en",
            word_timestamps=True
        )

        # Convert to dict format expected by diarization
        whisper_segments = []
        for seg in segments:
            whisper_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })

        # Get full text for AI processing
        full_text = " ".join(s["text"] for s in whisper_segments)

        # Process with speaker diarization
        speaker_result = process_transcription_with_speakers(wav_path, whisper_segments)

        # Get AI response
        ai_response = ""
        if full_text and is_meaningful(full_text) and is_question(full_text):
            result = route_ai(full_text, mode=CURRENT_MODE)
            ai_response = clean_ai_output(result["response"])

        return {
            "text": full_text,
            "response": ai_response,
            "speakers": speaker_result["segments"],
            "formatted_transcript": speaker_result["formatted"],
            "speaker_count": speaker_result["speaker_count"]
        }

    except Exception as e:
        logger.error(f"Transcription with speakers failed: {e}")
        return {"error": str(e)}

    finally:
        # Clean up temp files
        for path in (file_path, wav_path):
            try:
                os.remove(path)
            except OSError:
                pass


@app.get("/transcribe/{audio_id}/speakers")
async def get_transcription_speakers(audio_id: str):
    """
    Get speaker information for a previously transcribed audio.
    (Placeholder for future persistent storage)
    """
    return {"status": "not_implemented", "audio_id": audio_id}


def shutdown_handler(*args):
    global USE_AUTONOMOUS
    USE_AUTONOMOUS = False
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


@app.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    """Stream audio from browser and receive real-time transcriptions.

    Browser sends raw PCM Float32 audio at 16kHz mono.
    This endpoint accumulates chunks, transcribes on 0.5s segments,
    and sends back partial + final transcription via WebSocket JSON messages.

    Message types sent to browser:
      - {"type": "partial", "text": "..."}  — interim transcription
      - {"type": "final", "text": "..."}   — transcription of remaining buffer
    """
    await ws.accept()
    transcriber = BrowserTranscriber()
    partial_texts = []
    msg_queue = asyncio.Queue()
    ws_closed = False

    def on_transcript(text):
        """Called from transcription thread — put result in queue (non-blocking)."""
        if ws_closed:
            return
        partial_texts.append(text)
        combined = " ".join(partial_texts)
        try:
            msg_queue.put_nowait({"type": "partial", "text": combined})
        except asyncio.QueueFull:
            pass

    transcriber.add_callback(on_transcript)

    async def background_transcriber():
        """Pump the background thread's queue into the WebSocket."""
        while not ws_closed:
            try:
                msg = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                if ws_closed:
                    break
                await ws.send_json(msg)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    transcribe_task = asyncio.create_task(background_transcriber())

    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_bytes(), timeout=60)
            except asyncio.TimeoutError:
                continue

            chunk = np.frombuffer(data, dtype=np.float32)
            if chunk is not None and len(chunk) > 0:
                transcriber.add_chunk(chunk)

    except Exception:
        pass
    finally:
        ws_closed = True
        await transcribe_task
        final_text = transcriber.get_final()
        combined = " ".join(partial_texts).strip() or final_text
        try:
            await ws.send_json({"type": "final", "text": combined})
        except Exception:
            pass


# ==============================
# EXPORT/IMPORT ENDPOINTS
# ==============================

@app.post("/conversations/export")
async def export_conversation(body: dict):
    """
    Export conversation in various formats.

    body: {
        "messages": [...],
        "format": "markdown" | "json" | "txt",
        "includeMetadata": bool,
        "includeTimestamps": bool,
        "metadata": {...}  // optional
    }
    """
    messages = body.get("messages", [])
    fmt = body.get("format", "markdown")
    include_meta = body.get("includeMetadata", True)
    include_timestamps = body.get("includeTimestamps", False)
    metadata = body.get("metadata", {})

    if not messages:
        return {"error": "No messages to export"}

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    date_str = time.strftime("%Y-%m-%d")

    if fmt == "json":
        export_data = {
            "version": "1.0",
            "exported_at": timestamp,
            "messages": messages
        }
        if include_meta:
            export_data["metadata"] = metadata
        return {"content": json.dumps(export_data, indent=2), "filename": f"conversation-{date_str}.json"}

    elif fmt == "markdown":
        lines = []
        if include_meta:
            lines.append(f"# Conversation Export")
            lines.append(f"**Date:** {timestamp}")
            if metadata.get("mode"):
                lines.append(f"**Mode:** {metadata['mode']}")
            if metadata.get("model"):
                lines.append(f"**Model:** {metadata['model']}")
            lines.append("")

        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            header = "## You" if role == "user" else "## AI"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                header += f" ({ts_str})"

            lines.append(header)
            lines.append("")
            lines.append(text)
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.md"}

    else:  # txt
        lines = []
        if include_meta:
            lines.append(f"Conversation Export - {timestamp}")
            lines.append("=" * 50)
            lines.append("")

        for msg in messages:
            role = "You" if msg.get("role") == "user" else "AI"
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")

            prefix = f"[{role}]"
            if include_timestamps and ts:
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else str(ts)
                prefix += f" {ts_str}"

            lines.append(f"{prefix}: {text}")
            lines.append("")

        content = "\n".join(lines)
        return {"content": content, "filename": f"conversation-{date_str}.txt"}


@app.post("/conversations/import")
async def import_conversations(file: UploadFile = File(...)):
    """Import conversations from JSON file."""
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))

        if not isinstance(data, dict) or "messages" not in data:
            return {"error": "Invalid format - expected JSON with 'messages' array"}

        messages = data.get("messages", [])
        metadata = data.get("metadata", {})

        return {
            "success": True,
            "messages": messages,
            "metadata": metadata,
            "count": len(messages)
        }
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


# ==============================
# SALES OBJECTION HANDLING
# ==============================

# Common sales objections and suggested responses
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


@app.post("/detect-objections")
async def detect_objections(body: dict):
    """
    Detect sales objections in text.

    body: {"text": "..."}
    Returns: {"objections": [...], "suggestions": [...]}
    """
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


# ==============================
# ANALYTICS ENDPOINTS
# ==============================

@app.post("/analytics/record")
async def record_analytics(body: dict):
    """Record analytics for a conversation."""
    from analytics import get_analytics_store
    store = get_analytics_store()

    metrics = store.record_conversation(
        conversation_id=body.get("conversation_id"),
        messages=body.get("messages", []),
        start_time=body.get("start_time"),
        end_time=body.get("end_time"),
        models_used=body.get("models_used", [])
    )

    return {"status": "recorded", "metrics": {
        "duration_minutes": metrics.duration_minutes,
        "message_count": metrics.message_count
    }}


@app.get("/analytics/summary")
async def get_analytics_summary(days: int = 30):
    """Get analytics summary for the past N days."""
    from analytics import get_analytics_store
    store = get_analytics_store()
    return store.get_summary(days)


@app.post("/analytics/export")
async def export_analytics(body: dict):
    """Export analytics data."""
    from analytics import get_analytics_store
    store = get_analytics_store()
    fmt = body.get("format", "json")
    return store.get_export_data(fmt)


# ==============================
# CRM INTEGRATION ENDPOINTS
# ==============================

@app.get("/crm/config")
async def get_crm_config():
    """Get CRM configuration."""
    from crm_integration import get_crm
    crm = get_crm()
    return crm.get_config()


@app.post("/crm/config")
async def save_crm_config(body: dict):
    """Save CRM configuration."""
    from crm_integration import get_crm
    crm = get_crm()
    success = crm.configure(body)
    return {"success": success}


@app.post("/crm/webhook/{crm_type}/{event_type}")
async def send_crm_webhook(crm_type: str, event_type: str, body: dict):
    """Send webhook to CRM."""
    from crm_integration import get_crm
    crm = get_crm()
    result = crm.log_event(event_type, body)
    return {"success": result}


@app.get("/crm/test")
async def test_crm_connection():
    """Test CRM connection."""
    from crm_integration import get_crm
    crm = get_crm()
    return crm.test_connection()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    while True:
        msg = await ws.receive_text()
        result = route_ai(msg, mode=CURRENT_MODE)
        await ws.send_text(clean_ai_output(result["response"]))


# ======================================
# COGNITIVE GRAPH API - Phase 1
# Personal Knowledge Graph for Interview History
# ======================================

@app.get("/cognitive-graph/status")
async def cognitive_graph_status():
    """Check if Neo4j cognitive graph is available"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"available": False, "error": "Cognitive graph module not installed"}

    try:
        from cognitive_graph import get_driver
        driver = get_driver()
        if driver:
            return {"available": True, "connected": True}
        else:
            return {"available": True, "connected": False, "error": "Neo4j not connected"}
    except Exception as e:
        return {"available": True, "connected": False, "error": str(e)}


@app.post("/cognitive-graph/initialize")
async def cognitive_graph_initialize():
    """Initialize the cognitive graph schema"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    success = initialize_graph()
    return {"initialized": success}


@app.get("/cognitive-graph/search")
async def cognitive_graph_search(q: str = Query(...), limit: int = Query(10)):
    """Semantic search across interview history"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    results = query_graph(q)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/cognitive-graph/history/{user_id}")
async def cognitive_graph_history(user_id: str, limit: int = Query(100)):
    """Get user's interview history from graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    history = cognitive_graph.get_interview_history(user_id, limit)
    return {"user_id": user_id, "interviews": history}


@app.get("/cognitive-graph/company/{company_name}")
async def cognitive_graph_company_insights(company_name: str):
    """Get insights about a company"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    insights = cognitive_graph.get_company_insights(company_name)
    return {"company": company_name, "insights": insights}


@app.get("/cognitive-graph/skill/{user_id}/{skill_name}")
async def cognitive_graph_skill_progression(user_id: str, skill_name: str):
    """Track user's progression on a specific skill"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    progression = cognitive_graph.get_skill_progression(user_id, skill_name)
    return {"user_id": user_id, "skill": skill_name, "progression": progression}


@app.post("/cognitive-graph/ingest/{conversation_id}")
async def cognitive_graph_ingest(conversation_id: str, body: dict):
    """Ingest a conversation into the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    success = ingest_conversation(conversation_id, body)
    return {"ingested": success, "conversation_id": conversation_id}


@app.post("/cognitive-graph/interview")
async def cognitive_graph_add_interview(body: dict):
    """Add an interview to the cognitive graph"""
    if not COGNITIVE_GRAPH_AVAILABLE:
        return {"error": "Cognitive graph not available"}

    from datetime import datetime

    interview = InterviewNode(
        id=body.get("id", ""),
        title=body.get("title", "Untitled"),
        timestamp=datetime.fromisoformat(body.get("timestamp", datetime.now().isoformat())),
        duration_ms=body.get("duration_ms", 0),
        user_id=body.get("user_id", "default")
    )

    success = cognitive_graph.add_interview(interview)
    return {"added": success, "interview_id": interview.id}


# ======================================
# ENTITY EXTRACTION API - Phase 1
# NLP entity extraction for interview transcripts
# ======================================

try:
    from entity_extraction import extract_entities, process_transcript, entity_extractor
    ENTITY_EXTRACTION_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTION_AVAILABLE = False


@app.post("/extract-entities")
async def extract_entities_api(body: dict):
    """Extract entities (companies, topics, skills) from text"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return {"error": "Entity extraction not available"}

    text = body.get("text", "")
    if not text:
        return {"error": "No text provided"}

    entities = extract_entities(text)
    return {"text": text[:100] + "..." if len(text) > 100 else text, "entities": entities}


@app.post("/process-transcript")
async def process_transcript_api(body: dict):
    """Process a transcript into Q&A pairs with extracted entities"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return {"error": "Entity extraction not available"}

    transcript = body.get("transcript", "")
    if not transcript:
        return {"error": "No transcript provided"}

    qa_pairs = process_transcript(transcript)
    return {
        "qa_pairs": qa_pairs,
        "count": len(qa_pairs),
        "transcript_length": len(transcript)
    }


@app.get("/extract/categorize")
async def categorize_question_api(q: str = Query(...)):
    """Categorize a question (technical, behavioral, system_design, knowledge)"""
    if not ENTITY_EXTRACTION_AVAILABLE:
        return {"error": "Entity extraction not available"}

    category, confidence = entity_extractor.categorize_question(q)
    difficulty, diff_conf = entity_extractor.estimate_difficulty(q)

    return {
        "question": q,
        "category": {"label": category, "confidence": confidence},
        "difficulty": {"label": difficulty, "confidence": diff_conf} if difficulty else None
    }
