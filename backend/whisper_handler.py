# ==============================
# IMPORTS
# ==============================

import logging
import re
import threading
import time
import queue

import numpy as np
import psutil
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger("whisper")



# ==============================
# GLOBAL CONFIG
# ==============================

DEVICE = "auto"  # auto-detects GPU (cuda) vs CPU — GPU is ~10-20x faster
SAMPLE_RATE = 16000
RECORD_SECONDS = 4


# ==============================
# MODEL SELECTION
# ==============================

def select_model(mode="adaptive"):
    """
    Dynamically select Whisper model based on system resources and mode.
    """
    import psutil
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    if mode == "interview":
        return "small"   # better accuracy for important content

    if mode == "universal":
        return "small"

    # With 16GB+, use small model — significantly better accuracy, still fast
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
model_ready = threading.Event()   # signals when first model has finished loading
_warmup_done = False             # True once warmup thread has completed


def warmup():
    """Load the default model at startup so first transcription is instant."""
    global _warmup_done
    try:
        logger.info("[Warmup] Loading Whisper model...")
        model = get_model("adaptive")
        logger.info("[Warmup] Whisper ready: %s", model)
        model_ready.set()
        _warmup_done = True
    except Exception as e:
        logger.warning("[Warmup] Failed: %s", e)
        model_ready.set()  # unblock waiters even on failure
        _warmup_done = True


def wait_for_model(timeout=None):
    """Block until the model is ready (or timeout expires). Returns True if ready."""
    return model_ready.wait(timeout=timeout)


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
    Optimized for speed: beam_size=3, vad_filter=False, greedy decoding.
    """

    # Wait for warmup to complete before starting (max 30s)
    if not wait_for_model(timeout=30):
        logger.warning("Whisper model not ready after 30s — proceeding anyway")

    try:
        model = get_model(mode)

        segments, _ = model.transcribe(
            audio,
            beam_size=3,          # reduced from 5 — minimal quality loss, faster
            vad_filter=False,      # disabled — adds ~200ms overhead per call
            condition_on_previous_text=False,
            language="en",
            best_of=3,             # replaces beam_size reduction with non-beam alternatives
            patience=0.3           # less patience = faster
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


# ==============================
# STREAMING TRANSCRIBER
# ==============================

class StreamingTranscriber:
    """
    Continuous background audio capture + transcription.
    Uses a background thread to capture small audio chunks (100ms),
    accumulates them into overlapping segments, then sends each
    complete segment to faster-whisper in a thread pool.
    Callbacks receive transcribed text as segments are processed.
    """

    def __init__(self, segment_duration=2.0, overlap_duration=0.5, samplerate=SAMPLE_RATE):
        self.segment_duration = segment_duration
        self.overlap_duration = overlap_duration
        self.samplerate = samplerate
        self.buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.running = False
        self._capture_thread = None
        self._transcribe_queue = queue.Queue()
        self._callbacks = []
        self._transcriber_thread = None

    def add_callback(self, callback):
        """Add a callback(text) called when a transcription segment is ready."""
        self._callbacks.append(callback)

    def add_queue_output(self, q):
        """Add a thread-safe queue to push transcriptions into (for async integration)."""
        def queue_cb(text):
            try:
                q.put_nowait(text)
            except Exception:
                pass
        self.add_callback(queue_cb)

    def start(self):
        """Start continuous capture + transcription threads."""
        if self.running:
            return
        self.running = True
        self.buffer = np.array([], dtype=np.float32)

        # Transcription worker thread — processes queue items
        self._transcriber_thread = threading.Thread(target=self._transcribe_worker, daemon=True)
        self._transcriber_thread.start()

        # Capture thread — reads small chunks continuously
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        logger.info("[StreamingTranscriber] Started (segment=%.1fs, overlap=%.1fs)", self.segment_duration, self.overlap_duration)

    def stop(self):
        """Stop capture and transcription threads."""
        if not self.running:
            return
        self.running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
        self._transcribe_queue.put(None)  # Sentinel to stop transcriber thread
        if self._transcriber_thread:
            self._transcriber_thread.join(timeout=3)
        logger.info("[StreamingTranscriber] Stopped")

    def _capture_loop(self):
        """Background thread: continuously capture 100ms chunks and build segments."""
        try:
            samples_per_segment = int(self.segment_duration * self.samplerate)
            samples_overlap = int(self.overlap_duration * self.samplerate)
            chunk_size = int(0.1 * self.samplerate)  # 100ms chunks

            stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
                blocksize=chunk_size
            )

            with stream:
                while self.running:
                    try:
                        block, _ = stream.read(chunk_size)
                        block = block.flatten()

                        with self.buffer_lock:
                            self.buffer = np.concatenate([self.buffer, block])

                            # When buffer has a full segment, extract it and keep overlap
                            if len(self.buffer) >= samples_per_segment:
                                segment = self.buffer[:samples_per_segment].copy()
                                # Keep overlap portion for next iteration
                                self.buffer = self.buffer[samples_per_segment - samples_overlap:]

                                # Normalize
                                max_val = np.max(np.abs(segment)) + 1e-6
                                segment = segment / max_val

                                # Queue for transcription (non-blocking)
                                try:
                                    self._transcribe_queue.put_nowait(segment)
                                except queue.Full:
                                    pass  # Skip if queue is full (transcription too slow)

                    except Exception as e:
                        logger.error("[StreamingTranscriber] Capture error: %s", e)
                        time.sleep(0.5)

        except Exception as e:
            logger.error("[StreamingTranscriber] Stream open error: %s", e)

    def _transcribe_worker(self):
        """Thread that pulls segments from queue and transcribes them."""
        while True:
            segment = self._transcribe_queue.get()
            if segment is None:  # Sentinel
                break
            try:
                text = transcribe(segment, mode="adaptive")
                if text and text.strip():
                    for cb in self._callbacks:
                        try:
                            cb(text.strip())
                        except Exception as e:
                            logger.error("[StreamingTranscriber] Callback error: %s", e)
            except Exception as e:
                logger.error("[StreamingTranscriber] Transcription error: %s", e)


# ==============================
# MODULE-LEVEL SINGLETON
# ==============================

_transcriber_instance = None
_transcriber_lock = threading.Lock()


def get_streaming_transcriber():
    """Return the shared StreamingTranscriber singleton."""
    global _transcriber_instance
    if _transcriber_instance is None:
        with _transcriber_lock:
            if _transcriber_instance is None:
                _transcriber_instance = StreamingTranscriber()
    return _transcriber_instance


# ==============================
# BROWSER STREAMING TRANSCRIBER
# ==============================

class BrowserTranscriber:
    """Receives raw PCM Float32 chunks from browser WebSocket, buffers them,
    transcribes on 0.5s segments, returns partial text via callbacks.

    Per-session (not a singleton) — each WebSocket connection gets its own instance.
    Thread-safe: all shared state (buffer) is protected by self.lock.
    """

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.buffer = np.array([], dtype=np.float32)
        self.lock = threading.Lock()
        self.callbacks = []
        self.min_samples = int(0.5 * sample_rate)  # 500ms before triggering transcribe

    def add_callback(self, cb):
        """Add a callback(text) called when a partial transcription is ready."""
        self.callbacks.append(cb)

    def add_chunk(self, chunk: np.ndarray):
        """Add a raw PCM Float32 chunk received from browser."""
        if chunk is None or len(chunk) == 0:
            return
        with self.lock:
            self.buffer = np.concatenate([self.buffer, chunk])

        # When we have at least 500ms of audio, transcribe and keep the rest
        if len(self.buffer) >= self.min_samples:
            segment = self.buffer[:self.min_samples].copy()
            with self.lock:
                self.buffer = self.buffer[self.min_samples:]
            threading.Thread(target=self._transcribe, args=(segment,), daemon=True).start()

    def _transcribe(self, segment):
        """Transcribe a segment on a background thread."""
        try:
            text = transcribe(segment, mode="adaptive")
            if text and text.strip():
                for cb in self.callbacks:
                    try:
                        cb(text.strip())
                    except Exception:
                        pass
        except Exception as e:
            logger.error("[BrowserTranscriber] Transcription error: %s", e)

    def get_final(self) -> str:
        """Transcribe any remaining audio in the buffer. Called when session ends."""
        with self.lock:
            if len(self.buffer) == 0:
                return ""
            segment = self.buffer.copy()
            self.buffer = np.array([], dtype=np.float32)
        # Only transcribe if we have at least 250ms
        if len(segment) < self.min_samples // 2:
            return ""
        try:
            return transcribe(segment, mode="adaptive").strip()
        except Exception as e:
            logger.error("[BrowserTranscriber] Final transcription error: %s", e)
            return ""
