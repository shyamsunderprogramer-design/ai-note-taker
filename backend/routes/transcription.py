"""Route module for audio transcription, OCR, and WebSocket endpoints."""
import asyncio
import json
import logging
import os
import shutil
import subprocess  # nosec B404
import threading
import time

import numpy as np

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse

from ocr_service import extract_text_from_image
from security import rate_limit, ErrorCode, error_response
from ai_router import build_prompt, clean_ai_output, route_ai

logger = logging.getLogger("routes.transcription")

# Shared state — set by main.py at include time
CURRENT_MODE = "auto"
UPLOAD_DIR = "temp_audio"
STATE = {"is_streaming": False}
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"

# Whisper availability
try:
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
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def get_secure_filename(original_filename: str) -> str:
    """Generate a secure filename to prevent path traversal attacks."""
    import uuid
    if "." in original_filename:
        ext = original_filename.rsplit(".", 1)[1].lower()
        allowed_exts = {"webm", "wav", "mp3", "mp4", "m4a", "ogg", "pdf", "txt", "md", "docx", "json"}
        if ext not in allowed_exts:
            ext = "bin"
    else:
        ext = "bin"
    return f"{uuid.uuid4()}.{ext}"


def get_ffmpeg_path():
    """Cross-platform ffmpeg path finder."""
    import platform
    system = platform.system()

    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    if system == "Windows":
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
    else:
        candidates = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
        ]

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return "ffmpeg"


# Security import for auth
from security import get_current_user

router = APIRouter()

# Question-shape check for live suggestion triggering. whisper_handler's
# is_question() fires on 1-2 word fragments (tiny whisper emits "project.",
# "time." as standalone segments) which caused a suggestion per fragment;
# this requires a substantial, question-shaped segment instead.
_QUESTION_STARTERS = {
    "what", "why", "how", "when", "where", "who", "which", "can", "could",
    "would", "should", "do", "does", "did", "is", "are", "tell", "explain",
    "describe", "walk",
}


def _looks_like_interview_question(text: str) -> bool:
    words = text.strip().split()
    if len(words) < 5:
        return False
    first = words[0].lower().strip(".,!?'\"")
    return "?" in text or first in _QUESTION_STARTERS


@router.get("/transcribe/languages")
async def list_transcription_languages():
    """T22: List supported transcription languages."""
    try:
        from modules.voice.whisper_handler import get_supported_languages
        return {"languages": get_supported_languages()}
    except ImportError:
        return {"languages": {"en": "English"}, "note": "Whisper handler not available"}


@router.post("/transcribe")
async def transcribe_api(file: UploadFile = File(...)):
    """Fast audio transcription — returns text only. AI response is handled by the frontend."""
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Pass file directly to faster-whisper (it uses ffmpeg internally, supports webm/wav/mp3/etc.)
    # This skips a redundant 300-800ms ffmpeg subprocess call.
    text = transcribe_audio(file_path, mode=CURRENT_MODE, fast=True)

    try:
        os.remove(file_path)
    except OSError:
        pass  # nosec B110

    return {"text": text or ""}


@router.post("/transcribe-cloud")
@rate_limit(requests_per_minute=20)
async def transcribe_cloud(file: UploadFile = File(...), provider: str = "openai", model: str = "gpt-4o-mini"):
    """Transcribe and route to a cloud AI provider."""
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Pass file directly to faster-whisper, skipping redundant ffmpeg subprocess
    text = transcribe_audio(file_path, mode=CURRENT_MODE, fast=True)

    try:
        os.remove(file_path)
    except OSError:
        pass  # nosec B110

    if not text:
        return {"text": "", "response": "", "error": "No speech detected"}

    if not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": "", "error": "Not a meaningful question"}

    try:
        # Absolute import — bare `from cloud_providers` resolves to a
        # second (unpatched) module instance. See modules/ai/ai_router.py:628.
        from modules.platform.cloud_providers import ask_gpt, ask_claude, ask_gemini, ask_grok, ask_deepseek, ask_groq, clean_ai_output as cloud_clean

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
        return {"text": text, "response": "", "error": "An internal error occurred"}
    except Exception as e:
        logger.error("[ERROR cloud transcribe]: %s", str(e))
        return {"text": text, "response": "", "error": "An internal error occurred"}


@router.get("/transcribe-stream")
async def transcribe_stream(request: Request):
    """SSE stream of real-time transcription from always-on microphone."""
    import queue as queue_mod

    if not WHISPER_AVAILABLE:
        return JSONResponse({"error": "Whisper not available"}, status_code=503)

    loop = asyncio.get_event_loop()

    async def event_generator():
        transcriber = get_streaming_transcriber()
        client_queue = queue_mod.Queue()

        def sync_queue_callback(text):
            try:
                client_queue.put_nowait(text)
            except Exception:
                pass  # nosec B110
        transcriber.add_callback(sync_queue_callback)
        transcriber.start()

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    text = await loop.run_in_executor(None, lambda: client_queue.get(True, timeout=1))
                    yield f"event: transcript\ndata: {json.dumps({'text': text})}\n\n"
                except queue_mod.Empty:
                    yield f"event: ping\ndata: {json.dumps({'t': int(time.time())})}\n\n"
        except GeneratorExit:
            pass  # nosec B110
        except Exception as e:
            logger.error("[transcribe-stream] error: %s", str(e))

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/transcribe-with-speakers")
async def transcribe_with_speakers(
    file: UploadFile = File(...),
    language: str = Form("en"),
    auto_detect: bool = Form(False),
):
    """Transcribe audio with speaker diarization.
    T22: Supports multi-language transcription.
    Returns transcript + speakers — the frontend handles AI response separately."""
    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, get_secure_filename(file.filename))

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.rsplit(".", 1)[0] + ".wav"
    ffmpeg_path = get_ffmpeg_path()
    # v2.1.7: Wrap ffmpeg call so missing-binary / timeout / non-zero exit
    # all surface as 200 with an error body the frontend can render,
    # instead of unhandled 500s. Speaker diarization requires the user
    # to have ffmpeg installed (the bundled venv doesn't ship it).
    try:
        result = subprocess.run(  # nosec B603
            [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
            capture_output=True, text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return {
            "text": "",
            "speakers": [],
            "error": "ffmpeg not found. Speaker diarization requires ffmpeg installed on this machine — install it via Homebrew (`brew install ffmpeg`) or disable speaker diarization in Settings.",
        }
    except subprocess.TimeoutExpired:
        return {
            "text": "",
            "speakers": [],
            "error": "ffmpeg conversion timed out after 30s.",
        }

    if result.returncode != 0:
        return {
            "text": "",
            "speakers": [],
            "error": f"ffmpeg conversion failed: {result.stderr[:500]}",
        }

    try:
        # Speaker diarization using Whisper + speaker clustering
        from modules.voice.speaker_diarization import process_transcription_with_speakers

        model = get_model(CURRENT_MODE)
        # T22: Use provided language or auto-detect
        lang = None if auto_detect else language
        # Use faster settings: beam_size=1, VAD filter ON
        segments, info = model.transcribe(
            wav_path,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            language=lang,
            word_timestamps=True
        )

        whisper_segments = []
        for seg in segments:
            whisper_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })

        full_text = " ".join(s["text"] for s in whisper_segments)
        speaker_result = process_transcription_with_speakers(wav_path, whisper_segments)

        # NOTE: AI response is handled by the frontend separately via streaming.
        # Do NOT call route_ai() here — it blocks the event loop and doubles latency.

        detected_lang = info.language if info else language
        return {
            "text": full_text,
            "response": "",
            "speakers": speaker_result["segments"],
            "formatted_transcript": speaker_result["formatted"],
            "speaker_count": speaker_result["speaker_count"],
            "language": detected_lang,
            "auto_detected": auto_detect,
        }

    except Exception as e:
        logger.error("Transcription with speakers failed: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)

    finally:
        for path in (file_path, wav_path):
            try:
                os.remove(path)
            except OSError:
                pass  # nosec B110


@router.get("/transcribe/{audio_id}/speakers")
async def get_transcription_speakers(audio_id: str):
    """Get speaker information for a previously transcribed audio."""
    return {"status": "not_implemented", "audio_id": audio_id}


@router.post("/ocr")
@rate_limit(requests_per_minute=30)
async def ocr_image(request: Request):
    """Extract text from a base64-encoded image using OCR."""
    try:
        body = await request.json()
        image_b64 = body.get("image_b64", "")
        if not image_b64:
            return JSONResponse({"text": "", "method": "none", "error": "No image provided"}, status_code=400)
        result = extract_text_from_image(image_b64)
        return JSONResponse(result)
    except Exception as e:
        logger.error("[OCR] Error: %s", str(e))
        return JSONResponse({"text": "", "method": "none", "error": "An internal error occurred"}, status_code=500)


@router.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    """Stream audio from browser and receive real-time transcriptions."""
    if not WHISPER_AVAILABLE:
        await ws.accept()
        await ws.send_text(json.dumps({"error": "Whisper not available"}))
        await ws.close()
        return

    # Extract optional source and meeting_id params
    ws_source = ws.query_params.get("source", "tab")
    ws_meeting_id = ws.query_params.get("meeting_id", "")

    # Interview context for live suggestion generation (from interview-overlay
    # via ?role=&company=&skills=&resume= query params)
    ctx = {
        "role": ws.query_params.get("role", ""),
        "company": ws.query_params.get("company", ""),
        "skills": ws.query_params.get("skills", ""),
        "resume": ws.query_params.get("resume", ""),
    }

    await ws.accept()

    # WebSocket authentication — fast path: token in query param
    token = ws.query_params.get("token")
    user = None

    if AUTH_REQUIRED:
        if token:
            user = get_current_user(token)
        else:
            # Brief wait for auth message (2s), then reject fast
            try:
                first_msg = await asyncio.wait_for(ws.receive(), timeout=2)
                if "text" in first_msg and first_msg["text"]:
                    try:
                        auth_data = json.loads(first_msg["text"])
                        if auth_data.get("type") == "auth":
                            token = auth_data.get("token", "")
                            user = get_current_user(token)
                    except (json.JSONDecodeError, KeyError):
                        pass  # nosec B110
            except asyncio.TimeoutError:
                pass  # nosec B110

        if not user:
            await ws.send_text(json.dumps({"type": "auth_error", "message": "Authentication required."}))
            await ws.close(code=4001)
            return
    else:
        if token:
            user = get_current_user(token)

    await ws.send_text(json.dumps({"type": "auth_ok"}))

    transcriber = BrowserTranscriber()
    transcriber.start_worker()  # was missing — queue segments were never consumed, no transcript ever fired
    partial_texts = []
    msg_queue = asyncio.Queue()
    ws_closed = False
    loop = asyncio.get_running_loop()

    # Live suggestion generation state: per-connection cooldown so one spoken
    # question (which arrives as several 0.5s fragments) triggers one answer.
    _sugg_state = {"last_at": 0.0, "last_text": ""}
    _settle_state = {"timer": None}

    def _fire_suggestion(tail, asked_at):
        """Runs after 1.4s of transcript silence — the interviewer finished."""
        if ws_closed:
            return
        now = time.time()
        t = tail.lower()
        recent = now - _sugg_state["last_at"] < 10.0
        same_q = t in _sugg_state["last_text"] or _sugg_state["last_text"] in t
        if recent and same_q:
            return  # already answered this question
        _sugg_state["last_at"] = now
        _sugg_state["last_text"] = t

        def _generate():
            try:
                from modules.ai.realtime_suggestions import generate_live_suggestion
                result = generate_live_suggestion(
                    tail, role=ctx["role"], company=ctx["company"],
                    skills=ctx["skills"], resume=ctx["resume"],
                )
            except Exception as gen_exc:
                logger.error("[ws/transcribe] suggestion generation failed: %s", gen_exc)
                return
            if ws_closed or not result.get("text"):
                return
            total_ms = int((time.time() - asked_at) * 1000)
            logger.info(
                "[ws/transcribe] suggestion ready: model=%s gen=%sms e2e=%sms q=%r",
                result.get("model"), result.get("gen_ms"), total_ms, tail[:60],
            )
            sugg = {
                "type": "suggestion",
                "text": result["text"],
                "question": tail,
                "model": result.get("model"),
                "gen_ms": result.get("gen_ms"),
                "latency_ms": total_ms,
                "category": "answer",
                "confidence": 0.9,
            }
            try:
                loop.call_soon_threadsafe(msg_queue.put_nowait, sugg)
            except RuntimeError:
                pass  # nosec B110 — loop shut down mid-generation

        threading.Thread(target=_generate, daemon=True).start()

    def _arm_suggestion(tail):
        if _settle_state["timer"] is not None:
            _settle_state["timer"].cancel()
        # Re-arm on every matching segment; fires 1.0s after the LAST one,
        # so generation starts once the question is (mostly) fully spoken.
        timer = threading.Timer(1.0, _fire_suggestion, args=(tail, time.time()))
        timer.daemon = True
        _settle_state["timer"] = timer
        timer.start()

    # StreamingDiarizer
    streaming_diarizer = None
    try:
        from modules.voice.vibevoice_diarizer import get_streaming_diarizer
        streaming_diarizer = get_streaming_diarizer()
        logger.info("[ws/transcribe] StreamingDiarizer initialized for session")
    except ImportError:
        try:
            from voice.vibevoice_diarizer import get_streaming_diarizer
            streaming_diarizer = get_streaming_diarizer()
        except ImportError:
            logger.debug("[ws/transcribe] StreamingDiarizer unavailable")

    _audio_buffer = [np.array([], dtype=np.float32)]  # mutable list to avoid closure scope issue
    _audio_lock = threading.Lock()

    def on_transcript(text):
        if ws_closed:
            return
        partial_texts.append(text)
        combined = " ".join(partial_texts)

        msg = {"type": "partial", "text": combined, "source": ws_source}

        # --- Live suggestion generation -------------------------------------
        # Fragments arrive one per 0.5s segment; when the accumulated tail
        # looks like an interviewer question, arm a settle timer — if no new
        # speech arrives within 1.4s, the question is done and a real answer
        # is generated in a worker thread (never blocking transcription) and
        # pushed as {"type": "suggestion"} over this same socket — the
        # overlay's existing setHint() renders it unchanged.
        tail = " ".join(combined.split()[-45:])
        if _looks_like_interview_question(tail):
            _arm_suggestion(tail)

        if streaming_diarizer is not None:
            with _audio_lock:
                audio_chunk = _audio_buffer[0].copy()
                _audio_buffer[0] = np.array([], dtype=np.float32)

            if len(audio_chunk) > 0:
                result = streaming_diarizer.process_audio_segment(audio_chunk, text)
                msg["speaker"] = result.get("speaker", "Speaker 1")
                msg["semantic_role"] = result.get("semantic_role", "user")
            else:
                msg["speaker"] = "Speaker 1"
                msg["semantic_role"] = "user"

        if ws_meeting_id:
            msg["meeting_id"] = ws_meeting_id
        try:
            msg_queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # nosec B110

    transcriber.add_callback(on_transcript)

    async def background_transcriber():
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
                if streaming_diarizer is not None:
                    with _audio_lock:
                        _audio_buffer[0] = np.concatenate([_audio_buffer[0], chunk])

    except Exception:
        pass  # nosec B110
    finally:
        ws_closed = True
        await transcribe_task
        final_text = transcriber.get_final()
        combined = " ".join(partial_texts).strip() or final_text
        final_msg = {"type": "final", "text": combined, "source": ws_source}
        if ws_meeting_id:
            final_msg["meeting_id"] = ws_meeting_id
        if streaming_diarizer is not None:
            final_msg["speakers"] = list(set(
                entry.get("speaker", "Speaker 1")
                for entry in streaming_diarizer._speaker_history
            )) if streaming_diarizer._speaker_history else ["Speaker 1"]
        try:
            await ws.send_json(final_msg)
        except Exception:
            pass  # nosec B110


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """General-purpose WebSocket for AI queries."""
    token = ws.query_params.get("token")
    if AUTH_REQUIRED:
        if not token:
            await ws.accept()
            await ws.send_text(json.dumps({"error": {"code": "AUTH_REQUIRED", "message": "Authentication required. Pass ?token=xxx in WebSocket URL."}}))
            await ws.close(code=4001)
            return
        user = get_current_user(token)
        if not user:
            await ws.accept()
            await ws.send_text(json.dumps({"error": {"code": "INVALID_TOKEN", "message": "Invalid authentication token"}}))
            await ws.close(code=4001)
            return

    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            try:
                result = route_ai(msg, mode=CURRENT_MODE)
                await ws.send_text(clean_ai_output(result["response"]))
            except Exception as e:
                logger.error("[WS] Error processing message: %s", str(e))
                try:
                    await ws.send_text(json.dumps({"error": "An internal error occurred"}))
                except Exception:
                    break
    except Exception:
        pass  # nosec B110  # Client disconnected