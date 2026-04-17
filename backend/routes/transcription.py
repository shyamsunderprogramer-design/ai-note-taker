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


@router.post("/transcribe")
async def transcribe_api(file: UploadFile = File(...)):
    """Transcribe uploaded audio and route to AI if a question is detected."""
    USE_AUTONOMOUS = False
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(  # nosec B603
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    for path in (file_path, wav_path):
        try:
            os.remove(path)
        except OSError:
            pass  # nosec B110

    if not text or not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": ""}

    result = route_ai(text, mode=CURRENT_MODE)
    return {
        "text": text,
        "response": clean_ai_output(result["response"]),
        "mode": result["mode"],
        "model": result["model"]
    }


@router.post("/transcribe-cloud")
@rate_limit(requests_per_minute=20)
async def transcribe_cloud(file: UploadFile = File(...), provider: str = "openai", model: str = "gpt-4o-mini"):
    """Transcribe and route to a cloud AI provider"""
    USE_AUTONOMOUS = False
    secure_name = get_secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.replace(".webm", ".wav")
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(  # nosec B603
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    for path in (file_path, wav_path):
        try:
            os.remove(path)
        except OSError:
            pass  # nosec B110

    if not text:
        return {"text": "", "response": "", "error": "No speech detected"}

    if not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": "", "error": "Not a meaningful question"}

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
        logger.error("[ERROR cloud transcribe]: %s", e)
        return {"text": text, "response": "", "error": str(e)}


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
            logger.error("[transcribe-stream] error: %s", e)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/transcribe-with-speakers")
async def transcribe_with_speakers(file: UploadFile = File(...)):
    """Transcribe audio with speaker diarization.
    Returns transcript + speakers — the frontend handles AI response separately."""
    USE_AUTONOMOUS = False
    file_path = os.path.join(UPLOAD_DIR, get_secure_filename(file.filename))

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    wav_path = file_path.rsplit(".", 1)[0] + ".wav"
    ffmpeg_path = get_ffmpeg_path()
    result = subprocess.run(  # nosec B603
        [ffmpeg_path, "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    try:
        # Speaker diarization using Whisper + speaker clustering
        from modules.voice.speaker_diarization import process_transcription_with_speakers

        model = get_model(CURRENT_MODE)
        # Use faster settings: beam_size=1, VAD filter ON
        segments, _ = model.transcribe(
            wav_path,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            language="en",
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

        return {
            "text": full_text,
            "response": "",
            "speakers": speaker_result["segments"],
            "formatted_transcript": speaker_result["formatted"],
            "speaker_count": speaker_result["speaker_count"]
        }

    except Exception as e:
        logger.error(f"Transcription with speakers failed: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)

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
        logger.error("[OCR] Error: %s", e)
        return JSONResponse({"text": "", "method": "none", "error": str(e)}, status_code=500)


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

    await ws.accept()

    # WebSocket authentication
    token = ws.query_params.get("token")
    user = None

    if AUTH_REQUIRED:
        if token:
            user = get_current_user(token)
        else:
            try:
                first_msg = await asyncio.wait_for(ws.receive(), timeout=10)
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
    partial_texts = []
    msg_queue = asyncio.Queue()
    ws_closed = False

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
                logger.error(f"[WS] Error processing message: {e}")
                try:
                    await ws.send_text(json.dumps({"error": str(e)}))
                except Exception:
                    break
    except Exception:
        pass  # nosec B110  # Client disconnected