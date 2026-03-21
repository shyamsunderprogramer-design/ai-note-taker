# ==============================
# IMPORTS
# ==============================

import logging
import re
import threading

import numpy as np
import psutil
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger("whisper")



# ==============================
# GLOBAL CONFIG
# ==============================

DEVICE = "cpu"
SAMPLE_RATE = 16000
RECORD_SECONDS = 4


# ==============================
# MODEL SELECTION
# ==============================

def select_model(mode="adaptive"):
    """
    Dynamically select Whisper model based on system resources and mode.
    """

    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    if mode == "interview":
        return "base"

    if mode == "universal":
        return "base"

    if ram_gb >= 16:
        return "small"
    if ram_gb >= 8:
        return "base"
    return "tiny"


# ==============================
# LOAD MODELS
# ==============================

models = {}
_model_lock = threading.Lock()


def get_model(mode="adaptive"):
    """
    Return already-loaded model instance based on selected mode.
    Thread-safe lazy loading.
    """
    selected = select_model(mode)

    if selected not in models:
        with _model_lock:
            if selected not in models:
                logger.info("Loading Whisper model: %s", selected)
                models[selected] = WhisperModel(selected, device=DEVICE)

    return models[selected]


def unload_all_models():
    """Unload all cached Whisper models to free memory."""
    global models
    with _model_lock:
        for name, model in models.items():
            logger.info("Unloading Whisper model: %s", name)
            del model
        models.clear()


# ==============================
# RECORD AUDIO
# ==============================

def record_audio(duration=RECORD_SECONDS, samplerate=SAMPLE_RATE):
    """
    Capture audio from microphone.
    """

    logger.debug("Listening...")

    audio = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="float32"
    )

    sd.wait()

    max_val = np.max(np.abs(audio)) + 1e-6
    audio = audio / max_val

    return audio.flatten()


# ==============================
# TRANSCRIBE AUDIO
# ==============================

def transcribe(audio, mode="adaptive"):
    """
    Convert audio to text using Whisper.
    """

    try:
        model = get_model(mode)

        segments, _ = model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            language="en"
        )

        text = " ".join(seg.text for seg in segments)
        return text.strip()

    except Exception as e:
        logger.error("Transcription error: %s", e)
        return ""


# ==============================
# CLEAN TEXT
# ==============================

def clean_text(text):
    """
    Remove noise, filler words, invalid input.
    """

    if not text:
        return None

    text = text.strip().lower()

    if re.fullmatch(r"[0-9\.\s]+", text):
        return None

    if len(set(text)) < 3:
        return None

    ignore = ["uh", "um", "...", ".", "ok", "okay", "hmm", "so", "like"]
    if text in ignore:
        return None

    return text


# ==============================
# QUESTION DETECTION
# ==============================

def is_question(text):
    """
    Detect if input is a question.
    """

    text = text.lower().strip()

    question_words = [
        "what", "why", "how", "when", "where",
        "who", "which", "can", "do", "does",
        "is", "are", "should", "explain", "tell"
    ]

    if "?" in text:
        return True

    words = text.split()
    if words and words[0] in question_words:
        return True

    if len(words) <= 8:
        return True

    return False


# ==============================
# SMALL TALK FILTER
# ==============================

def is_small_talk(text):
    """
    Detect casual / non-useful speech.
    """

    text = text.lower().strip()

    ignore_patterns = [
        "what's going on",
        "whats going on",
        "how are you",
        "you good",
        "are you okay",
        "hello",
        "hi",
        "thanks",
        "thank you",
        "okay",
        "alright",
        "cool",
        "got it",
        "see you",
        "bye"
    ]

    return any(p in text for p in ignore_patterns)


# ==============================
# TECHNICAL DETECTION
# ==============================

def is_technical(text):
    """
    Detect technical / interview-related content.
    """

    keywords = [
        "kubernetes", "docker", "terraform", "ci", "cd",
        "pipeline", "aws", "azure", "gcp", "api",
        "microservice", "deployment", "architecture",
        "database", "scaling", "load balancer",
        "devops", "container", "helm", "ingress"
    ]

    text = text.lower()
    return any(k in text for k in keywords)


# ==============================
# MEANINGFUL TEXT FILTER
# ==============================

def is_meaningful(text):
    """
    Filter weak / noisy sentences.
    """

    if not text:
        return False

    words = text.split()
    if len(words) < 2:
        return False

    noise_patterns = ["...", ".", "uh", "um"]
    if any(p in text for p in noise_patterns):
        return False

    return True


# ==============================
# FILE TO TRANSCRIBE
# ==============================

def transcribe_audio(file_path, mode="adaptive"):
    """
    Convert file to numpy to transcription.
    """

    try:
        audio, samplerate = sf.read(file_path)

        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        max_val = abs(audio).max() + 1e-6
        audio = (audio / max_val).astype("float32")

        return transcribe(audio, mode)

    except Exception as e:
        logger.error("File transcription error: %s", e)
        return ""
