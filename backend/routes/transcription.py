"""Route module for audio transcription, OCR, and WebSocket endpoints."""
import asyncio
from lib.audio_upload import transcribe_saved_upload
import json
import logging
import os
import re
import shutil
import subprocess  # nosec B404
import threading
import time
import uuid

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

try:
    from modules.voice.vad_segmenter import VadSegmenter
except ImportError:  # pragma: no cover - path shape differs per entrypoint
    from voice.vad_segmenter import VadSegmenter


_ACKNOWLEDGEMENTS = {
    "ok", "okay", "right", "sure", "great", "thanks", "thank you", "got it",
    "mm-hmm", "uh-huh", "yeah", "yes", "no", "perfect", "exactly", "nice",
    "cool", "alright", "understood", "makes sense", "interesting",
}


def _should_answer(text: str) -> bool:
    """Is this complete utterance worth answering?

    Utterance segmentation makes this simple. We are handed one whole thing
    the interviewer said, so the starter-word detection this replaced — plus
    its backwards fallback scan and competing word-count floors, all of which
    existed only to find a question hiding inside a stream of fragments — is
    unnecessary. Anything substantial gets answered; short acknowledgements
    ("okay", "got it") do not. The 4-word floor keeps the most common real
    question in the corpus, "Tell me about yourself", answerable.
    """
    stripped = text.strip().strip(".?!,").lower()
    if not stripped or stripped in _ACKNOWLEDGEMENTS:
        return False
    return len(stripped.split()) >= 4


# Legacy question-shape check. The live assist no longer uses it — utterance
# segmentation replaced starter-word guessing — but /realtime and the
# characterization suite still reference it.
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
    text = await transcribe_saved_upload(transcribe_audio, file_path, mode=CURRENT_MODE, fast=True)

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
    text = await transcribe_saved_upload(transcribe_audio, file_path, mode=CURRENT_MODE, fast=True)

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
def transcribe_with_speakers(
    file: UploadFile = File(...),
    language: str = Form("en"),
    auto_detect: bool = Form(False),
):
    """Transcribe audio with speaker diarization in FastAPI's worker pool.
    T22: Supports multi-language transcription.
    Returns transcript + speakers — the frontend handles AI response separately."""
    USE_AUTONOMOUS = False
    started_at = time.perf_counter()
    file_path = os.path.join(UPLOAD_DIR, get_secure_filename(file.filename))

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if os.path.getsize(file_path) < 256:
        os.remove(file_path)
        return {"text": "", "speakers": [], "error": "No usable audio was recorded. Check your microphone input and record again."}

    wav_path = file_path + ".decoded.wav"
    ffmpeg_path = get_ffmpeg_path()
    # v2.1.7: Wrap ffmpeg call so missing-binary / timeout / non-zero exit
    # all surface as 200 with an error body the frontend can render,
    # instead of unhandled 500s. Speaker diarization requires the user
    # to have ffmpeg installed (the bundled venv doesn't ship it).
    try:
        result = subprocess.run(  # nosec B603
            [ffmpeg_path, "-hide_banner", "-loglevel", "error", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path, "-y"],
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
            "error": "Audio could not be decoded. The recording may be incomplete; check your microphone and record again.",
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
            temperature=0.0,  # Avoid repeated temperature-fallback decoding of long speech.
            word_timestamps=False  # Only segment start/end times are used below.
        )

        whisper_segments = []
        for seg in segments:
            whisper_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })

        full_text = " ".join(s["text"] for s in whisper_segments)
        transcription_done = time.perf_counter()
        speaker_result = process_transcription_with_speakers(wav_path, whisper_segments)
        logger.info("Audio processing: transcription=%.2fs speaker_detection=%.2fs total=%.2fs",
                    transcription_done - started_at, time.perf_counter() - transcription_done,
                    time.perf_counter() - started_at)

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
        result = await asyncio.to_thread(extract_text_from_image, image_b64)
        return JSONResponse(result)
    except Exception as e:
        logger.error("[OCR] Error: %s", str(e))
        return JSONResponse({"text": "", "method": "none", "error": "An internal error occurred"}, status_code=500)


# Dual-channel live assist (2026-09-11, Cluely-style): when a source="system"
# socket is connected, IT owns suggestion-arming — the interviewer's voice is
# whatever the meeting app plays through the speakers (system audio), and the
# candidate's mic can no longer arm hints (their echo/self-talk polluted the
# question tail in every mock so far).
_DUAL_CHANNEL = {"system": 0, "last_system_speech": 0.0}

# How long a system channel stays trusted after it last produced speech.
# Ownership must follow WORKING audio, not a connected socket: on 2026-09-12 a
# system channel connected but captured silence (permission not yet granted),
# and because "connected" was the test, the mic — which had transcribed all
# three questions perfectly — was suppressed and no hint was delivered.
_SYSTEM_TRUST_WINDOW_S = 120.0

# How often a rolling preview may fire while someone is still speaking.
# Frequent enough to feel live, spaced enough that previews never queue up
# behind each other or crowd out the committed answer.
_PREVIEW_INTERVAL_S = 2.5
_PREVIEW_MIN_AUDIO_S = 1.5

# Whisper invents these out of silence and near-silence. They are not speech,
# and answering them wastes a generation slot the real question needs.
_NOISE_TEXT = {
    "you", "thank you", "thanks", "thanks for watching", "sigh", "bye",
    "uh", "um", "hmm", "the", "watch", "see you soon", "love", "okay",
    "so", "yeah", ".", "..", "...",
}

# Two cuts closer together than this are a double-tap, not two questions.
_CUT_DEBOUNCE_S = 1.2


def _is_noise_text(text: str) -> bool:
    """Reject hallucinations even on an explicit cut.

    Manual cuts skip the answerability filter on purpose — a short question is
    still a question. But they must not skip THIS: on 2026-09-12 repeated
    presses each generated a full answer to the word "you", queueing on the
    GPU until latency climbed past 14s and the app looked frozen.
    """
    stripped = text.strip().strip(".?!,").lower()
    if not stripped or stripped in _NOISE_TEXT:
        return True
    return len(stripped.split()) < 2


def _system_channel_is_live() -> bool:
    """Is a system channel connected AND actually carrying speech?"""
    if _DUAL_CHANNEL["system"] <= 0:
        return False
    return (time.time() - _DUAL_CHANNEL["last_system_speech"]) < _SYSTEM_TRUST_WINDOW_S


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
    live_assistance = ws.query_params.get("assist", "true").lower() != "false"

    # Interview context for live suggestion generation (from interview-overlay
    # via ?role=&company=&skills=&resume= query params)
    ctx = {
        "model": ws.query_params.get("model", "auto"),
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
            user = await get_current_user(token)
        else:
            # Brief wait for auth message (2s), then reject fast
            try:
                first_msg = await asyncio.wait_for(ws.receive(), timeout=2)
                if "text" in first_msg and first_msg["text"]:
                    try:
                        auth_data = json.loads(first_msg["text"])
                        if auth_data.get("type") == "auth":
                            token = auth_data.get("token", "")
                            user = await get_current_user(token)
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
            user = await get_current_user(token)

    await ws.send_text(json.dumps({"type": "auth_ok"}))

    transcriber = BrowserTranscriber()
    # Utterance boundaries come from the audio itself (see VadSegmenter).
    segmenter = VadSegmenter()
    transcriber.start_worker()  # was missing — queue segments were never consumed, no transcript ever fired
    partial_texts = []
    msg_queue = asyncio.Queue()
    ws_closed = False
    loop = asyncio.get_running_loop()

    # Live suggestion state. With utterance segmentation each spoken question
    # arrives exactly once, complete, so the machinery this replaced is gone:
    # the 1.0s transcript settle timer, the 10s substring cooldown, the
    # refinement exception, and the starter-word fallback scan. All of them
    # were repairs for not knowing where a question began and ended.
    # What remains is an ordering guard — two questions asked in quick
    # succession can finish generating out of order, and the newer must win.
    _utt_state = {"seq": 0, "delivered": 0}
    answer_session_id = uuid.uuid4().hex
    # Answered turns, so later answers build on earlier ones instead of
    # re-introducing the candidate for every question.
    _history = []
    _preview_state = {"at": 0.0, "busy": False, "last_text": "", "epoch": 0}
    _cut_state = {"at": 0.0}

    def _fire_suggestion(question, asked_at, seq):
        requested_model = ctx["model"]
        if ws_closed:
            logger.info("[ws/transcribe] suggestion skipped: socket already closed")
            return

        def _generate():
            if seq < _utt_state["seq"]:
                # A newer question arrived before this one reached the GPU.
                # Generating anyway only queues work whose result is already
                # guaranteed to be dropped at delivery.
                logger.info("[ws/transcribe] superseded before generating, skipping")
                return
            try:
                from modules.ai.realtime_suggestions import generate_live_suggestion

                def _first_sentence(sentence, gen_ms):
                    """Ship the opening line the moment it exists.

                    The candidate can start speaking on the first sentence; the
                    rest arrives while they are already talking. Waiting for the
                    full answer is what pushed the gate past 4s.
                    """
                    if ws_closed or ctx["model"] != requested_model or seq <= _utt_state["delivered"]:
                        return
                    first_ms = int((time.time() - asked_at) * 1000)
                    logger.info(
                        "[ws/transcribe] first sentence out at %sms (gen %sms)",
                        first_ms, gen_ms,
                    )
                    try:
                        loop.call_soon_threadsafe(msg_queue.put_nowait, {
                            "type": "suggestion",
                            "answer_id": seq,
                            "session_id": answer_session_id,
                            "partial": True,
                            "text": sentence,
                            "question": question,
                            "latency_ms": first_ms,
                            "category": "answer",
                            "confidence": 0.9,
                        })
                    except RuntimeError:
                        pass  # nosec B110 — loop shut down mid-generation

                result = generate_live_suggestion(
                    question, role=ctx["role"], company=ctx["company"],
                    skills=ctx["skills"], resume=ctx["resume"],
                    model=None if requested_model == "auto" else requested_model,
                    history=list(_history),
                    on_first_sentence=_first_sentence,
                )
            except Exception as gen_exc:
                logger.error("[ws/transcribe] suggestion generation failed: %s", gen_exc)
                return
            if ws_closed or ctx["model"] != requested_model or not result.get("text"):
                if not ws_closed and ctx["model"] == requested_model and result.get("error"):
                    loop.call_soon_threadsafe(msg_queue.put_nowait, {
                        "type": "suggestion_error",
                        "message": "The selected live model could not answer. Check the model/provider or try again.",
                    })
                logger.info(
                    "[ws/transcribe] suggestion discarded: ws_closed=%s empty_text=%s err=%s",
                    ws_closed, not result.get("text"), result.get("error"),
                )
                return
            # Drop only if a NEWER answer already reached the screen. Keying
            # this on "is a newer question known" instead silently ate a
            # correct answer whenever the next question arrived while the
            # first was still generating (e2e run 22:33: both questions
            # transcribed perfectly, only one hint delivered).
            if seq <= _utt_state["delivered"]:
                logger.info(
                    "[ws/transcribe] stale suggestion dropped (seq=%s, delivered=%s) for %r",
                    seq, _utt_state["delivered"], question[:60],
                )
                return
            _utt_state["delivered"] = seq
            _preview_state["last_text"] = ""
            _history.append({"question": question, "answer": result["text"]})
            del _history[:-6]
            total_ms = int((time.time() - asked_at) * 1000)
            logger.info(
                "[ws/transcribe] suggestion ready: model=%s gen=%sms e2e=%sms q=%r",
                result.get("model"), result.get("gen_ms"), total_ms, question[:60],
            )
            sugg = {
                "type": "suggestion",
                "answer_id": seq,
                "session_id": answer_session_id,
                "partial": False,
                "text": result["text"],
                "question": question,
                "model": result.get("model"),
                "gen_ms": result.get("gen_ms"),
                "latency_ms": total_ms,
                "category": "answer",
                "confidence": 0.9,
            }
            try:
                loop.call_soon_threadsafe(msg_queue.put_nowait, sugg)
                logger.info(
                    "[ws/transcribe] suggestion QUEUED to socket (e2e=%sms)", total_ms,
                )
            except RuntimeError:
                pass  # nosec B110 — loop shut down mid-generation

        threading.Thread(target=_generate, daemon=True).start()

    def _on_preview(audio, epoch):
        """A provisional line of direction while the question is still coming.

        Deliberately not a full answer: the question is incomplete, so
        committing early invites drift onto the wrong point. Previews replace
        each other in the UI rather than stacking — repeated hints were what
        made the assist feel messy before.
        """
        try:
            if ws_closed:
                return
            result = transcribe(audio, mode="adaptive", streaming=True)
            text = (
                result.get("text", "") if isinstance(result, dict) else str(result or "")
            ).strip()
            if not text or len(text.split()) < 3:
                return
            if text.lower() == _preview_state["last_text"]:
                return  # nothing new has been said since the last preview
            _preview_state["last_text"] = text.lower()

            from modules.ai.realtime_suggestions import generate_live_preview
            hint = generate_live_preview(
                text, role=ctx["role"], company=ctx["company"],
                skills=ctx["skills"], resume=ctx["resume"],
                history=list(_history),
            )
            if ws_closed or not hint.get("text"):
                return
            if epoch != _preview_state["epoch"]:
                # The question was committed while this was generating. Showing
                # it now would replace a real answer with a guess about a
                # question that is already over.
                logger.info("[ws/transcribe] stale preview dropped")
                return
            logger.info(
                "[ws/transcribe] preview %r -> %r",
                text[:45], hint["text"][:55],
            )
            loop.call_soon_threadsafe(msg_queue.put_nowait, {
                "type": "suggestion",
                "preview": True,
                "text": hint["text"],
                "question": text,
                "model": hint.get("model"),
                "gen_ms": hint.get("gen_ms"),
                "category": "direction",
                "confidence": 0.5,
            })
        except Exception as exc:
            logger.error("[ws/transcribe] preview failed: %s", exc)
        finally:
            _preview_state["busy"] = False

    def _on_utterance(audio, captured_at, manual=False):
        """One complete spoken utterance: transcribe it whole, then answer.

        This is the design change (2026-09-11). The boundary comes from
        silence in the AUDIO, so Whisper receives the entire question instead
        of 1.5s fragments. Measured on identical speech, the slicing path this
        replaced split "What is your greatest strength" into "What?" plus
        "is your greatest strength.", emitted "Tell me." before "Tell me about
        yourself.", and lost a third question entirely; this path returned all
        three verbatim.
        """
        if not live_assistance:
            return
        try:
            result = transcribe(audio, mode="adaptive", streaming=True)
        except Exception as exc:
            logger.error("[ws/transcribe] utterance transcription failed: %s", exc)
            return
        text = (
            result.get("text", "") if isinstance(result, dict) else str(result or "")
        ).strip()
        logger.info(
            "[ws/transcribe] utterance %.1fs -> %r",
            len(audio) / 16000.0, text[:90],
        )
        if not text:
            return
        if manual and _is_noise_text(text):
            # An explicit request is honoured for any real question, however
            # short — but not for a hallucination.
            logger.info("[ws/transcribe] cut ignored, not speech: %r", text[:40])
            return
        if not manual and not _should_answer(text):
            logger.info("[ws/transcribe] not answerable, no hint: %r", text[:60])
            return
        if ws_source == "system":
            # Proof this channel works — it just produced speech.
            _DUAL_CHANNEL["last_system_speech"] = time.time()
        elif _system_channel_is_live():
            # A working interviewer channel owns assist, so the candidate's own
            # voice cannot trigger hints. A merely-connected-but-silent one
            # does not: that would strand the user with no hints at all.
            logger.info(
                "[ws/transcribe] mic utterance suppressed: system channel owns assist",
            )
            return
        _utt_state["seq"] += 1
        _fire_suggestion(text, captured_at, _utt_state["seq"])

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
        # Mock-debug instrumentation (2026-09-11): the suggestion path fired
        # 0 times while sessions ran — log every segment + detector verdict
        # so a dead run is diagnosable from /tmp/ant-backend.log alone.
        # Display only. Suggestion timing now comes from VadSegmenter on the
        # raw audio, not from watching this text settle — transcript lags the
        # audio by at least one slice, which is what fired hints on half-spoken
        # questions.
        logger.info("[ws/transcribe] partial seg=%r", text[-60:])

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
            # Speaker-accuracy evidence for the mock (2026-09-11): before we can
            # gate suggestion-arming on diarizer role, we need to know whether
            # the labels separate interviewer (echo through speakers→mic) from
            # the candidate's own voice at all. Behavior unchanged — logging only.
            logger.info(
                "[ws/transcribe] speaker=%s role=%s seg=%r",
                msg["speaker"], msg["semantic_role"], text[-60:],
            )

        if ws_meeting_id:
            msg["meeting_id"] = ws_meeting_id
        # asyncio queues must be touched on their owning event loop.
        try:
            loop.call_soon_threadsafe(msg_queue.put_nowait, msg)
        except RuntimeError:
            pass  # Event loop already closed during shutdown.

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

    if ws_source == "system":
        _DUAL_CHANNEL["system"] += 1
        logger.info("[ws/transcribe] system-audio (interviewer) channel connected")

    try:
        while True:
            try:
                message = await asyncio.wait_for(ws.receive(), timeout=0.4)
            except asyncio.TimeoutError:
                # Audio stopped arriving. A question spoken right before the
                # recorder stops leaves an utterance buffered with no trailing
                # silence to close it, so without this the last — and most
                # important — question of a session is never answered.
                _pending = segmenter.flush()
                if _pending is not None:
                    logger.info(
                        "[ws/transcribe] audio stalled, flushing %.1fs utterance",
                        len(_pending) / 16000.0,
                    )
                    threading.Thread(
                        target=_on_utterance,
                        args=(_pending, time.time()),
                        daemon=True,
                    ).start()
                continue

            if message.get("type") == "websocket.disconnect":
                break

            control = message.get("text")
            if control:
                # Manual cut: the candidate pressed the key to say "the
                # question ends here, answer it now". Takes whatever audio is
                # buffered without waiting for the silence threshold, which is
                # both faster and more reliable than inferring the boundary.
                try:
                    payload = json.loads(control)
                except (ValueError, TypeError):
                    payload = {}
                if payload.get("type") == "stop":
                    break
                if payload.get("type") == "configure":
                    selected = payload.get("model")
                    if isinstance(selected, str) and 0 < len(selected) <= 200:
                        ctx["model"] = selected
                    continue
                if payload.get("type") == "cut":
                    _now_cut = time.time()
                    if _now_cut - _cut_state["at"] < _CUT_DEBOUNCE_S:
                        logger.info("[ws/transcribe] cut ignored: double-tap")
                        continue
                    _cut_state["at"] = _now_cut
                    # Invalidate previews for the question being committed:
                    # they are guesses about a question that just ended, and
                    # they compete with the real answer for the GPU.
                    _preview_state["epoch"] += 1
                    _preview_state["last_text"] = ""
                    _cut = segmenter.flush(force=True)
                    if _cut is None:
                        logger.info("[ws/transcribe] manual cut: nothing buffered")
                    else:
                        logger.info(
                            "[ws/transcribe] manual cut: %.1fs of audio",
                            len(_cut) / 16000.0,
                        )
                        threading.Thread(
                            target=_on_utterance,
                            args=(_cut, time.time()),
                            kwargs={"manual": True},
                            daemon=True,
                        ).start()
                continue

            data = message.get("bytes")
            if not data:
                continue

            chunk = np.frombuffer(data, dtype=np.float32)
            if chunk is not None and len(chunk) > 0:
                transcriber.add_chunk(chunk)
                for _utt in segmenter.add_chunk(chunk):
                    threading.Thread(
                        target=_on_utterance,
                        args=(_utt, time.time()),
                        daemon=True,
                    ).start()
                _now = time.time()
                if (
                    segmenter.is_speaking
                    and live_assistance
                    and ctx["model"] == "auto"
                    and not _preview_state["busy"]
                    and _now - _preview_state["at"] >= _PREVIEW_INTERVAL_S
                ):
                    _peek = segmenter.peek()
                    if _peek is not None and len(_peek) >= 16000 * _PREVIEW_MIN_AUDIO_S:
                        _preview_state["busy"] = True
                        _preview_state["at"] = _now
                        threading.Thread(
                            target=_on_preview,
                            args=(_peek, _preview_state["epoch"]),
                            daemon=True,
                        ).start()

                if streaming_diarizer is not None:
                    with _audio_lock:
                        _audio_buffer[0] = np.concatenate([_audio_buffer[0], chunk])

    except Exception:
        pass  # nosec B110
    finally:
        ws_closed = True
        if ws_source == "system":
            _DUAL_CHANNEL["system"] = max(0, _DUAL_CHANNEL["system"] - 1)
        # Cleanup must run even if the ASGI task is cancelled at an await.
        from starlette.websockets import WebSocketState
        try:
            await transcribe_task
            final_text = (await asyncio.to_thread(transcriber.get_final)
                          if ws.client_state == WebSocketState.CONNECTED else "")
        finally:
            transcriber.stop(wait=False)
        combined = final_text or " ".join(partial_texts).strip()
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
        user = await get_current_user(token)
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
