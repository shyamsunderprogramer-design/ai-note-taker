import os
import shutil
import signal
import sys
import threading
import time

from fastapi import FastAPI, File, UploadFile, WebSocket
from fastapi.responses import StreamingResponse

from ai_router import clean_ai_output, route_ai, route_ai_stream
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

UPLOAD_DIR = "temp_audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    os.system(f'ffmpeg -i "{file_path}" -ar 16000 -ac 1 "{wav_path}" -y')

    text = transcribe_audio(wav_path, mode=CURRENT_MODE)

    if not text or not is_meaningful(text) or not is_question(text):
        return {"text": text, "response": ""}

    result = route_ai(text, mode=CURRENT_MODE)
    return {
        "text": text,
        "response": clean_ai_output(result["response"]),
        "mode": result["mode"],
        "model": result["model"]
    }


@app.get("/stream")
def stream_ai(q: str, mode: str = "fast"):
    def generator():
        STATE["is_streaming"] = True

        try:
            buffer = ""

            for chunk in route_ai_stream(q, mode):
                if not chunk:
                    continue

                buffer += chunk

                if chunk.endswith((" ", ".", ",", "?", "!", "\n")):
                    cleaned_buffer = clean_ai_output(buffer)
                    if cleaned_buffer:
                        yield cleaned_buffer + " "
                    buffer = ""

            if buffer:
                cleaned_buffer = clean_ai_output(buffer)
                if cleaned_buffer:
                    yield cleaned_buffer

        except Exception as e:
            print("[ERROR] Stream error:", e)
            yield "AI error"

        finally:
            STATE["is_streaming"] = False

    return StreamingResponse(generator(), media_type="text/plain")


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
