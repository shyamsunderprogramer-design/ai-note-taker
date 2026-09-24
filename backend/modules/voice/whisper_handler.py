# ==============================
# IMPORTS
# ==============================

import logging
import re
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import psutil

# Heavy ML packages — lazy-loaded so this module can be imported without them
# (e.g. in CI test environments where torch/faster-whisper/sounddevice are not installed)
_sd = None  # sounddevice module
_sf = None  # soundfile module
_WhisperModel = None  # faster_whisper.WhisperModel class

def _get_sd():
    global _sd
    if _sd is None:
        import sounddevice as mod
        _sd = mod
    return _sd

def _get_sf():
    global _sf
    if _sf is None:
        import soundfile as mod
        _sf = mod
    return _sf

def _get_WhisperModel():
    global _WhisperModel
    if _WhisperModel is None:
        from faster_whisper import WhisperModel as cls
        _WhisperModel = cls
    return _WhisperModel

logger = logging.getLogger("whisper")



# ==============================
# GLOBAL CONFIG
# ==============================

DEVICE = "auto"  # auto-detects GPU (cuda) vs CPU — GPU is ~10-20x faster
SAMPLE_RATE = 16000
RECORD_SECONDS = 4
# Shared thread pool for all whisper transcription tasks — prevents unbounded thread creation
_transcribe_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper")


# ==============================
# MODEL SELECTION
# ==============================

def select_model(mode="adaptive", streaming=False):
    """
    Dynamically select Whisper model based on system resources and mode.
    For streaming (real-time), prefer smaller models for low latency.
    """
    import psutil
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    # Streaming (2026-09-11 mock evidence): "base" on CPU garbled real speech
    # ("greatest strength" → "greatest spread") and hallucinated phrases out of
    # silence ("Thank you.", "Watch.", "See you soon."). 16GB+ machines get
    # "small" — noticeably fewer mis-hears; with 1.5s slices the latency
    # headroom is sufficient (warm e2e was 2.1s with base, gate is 4.0s).
    # NOTE: DEVICE=="auto" resolves to CPU on macOS, so don't gate on it.
    if streaming:
        if ram_gb >= 16:
            return "small"
        if ram_gb >= 8:
            return "base"
        return "tiny"

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
        # Also preload streaming model in background so BrowserTranscriber is fast
        threading.Thread(target=_preload_streaming_model, daemon=True, name="whisper-streaming-warmup").start()
        model_ready.set()
        _warmup_done = True
    except Exception as e:
        logger.warning("[Warmup] Failed: %s", str(e))
        model_ready.set()  # unblock waiters even on failure
        _warmup_done = True


def _preload_streaming_model():
    """Preload the lightweight model used by BrowserTranscriber for real-time streaming."""
    try:
        logger.info("[Warmup] Preloading streaming model...")
        get_model("adaptive", streaming=True)
        logger.info("[Warmup] Streaming model ready")
    except Exception as e:
        logger.debug("[Warmup] Streaming model preload skipped: %s", str(e))


def wait_for_model(timeout=None):
    """Block until the model is ready (or timeout expires). Returns True if ready."""
    return model_ready.wait(timeout=timeout)


def get_model(mode="adaptive", streaming=False):
    """
    Return already-loaded model instance based on selected mode.
    Thread-safe lazy loading.
    """
    selected = select_model(mode, streaming=streaming)

    if selected not in models:
        with _model_lock:
            if selected not in models:
                logger.info("Loading Whisper model: %s", selected)
                models[selected] = _get_WhisperModel()(selected, device=DEVICE)

    return models[selected]


def unload_all_models():
    """Unload all cached Whisper models to free memory."""
    global models  # noqa: F824
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
    sd = _get_sd()

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

# Supported languages for Whisper
def get_supported_languages():
    """Return dict of language code → name."""
    return {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
        "ru": "Russian", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
        "ar": "Arabic", "hi": "Hindi", "tr": "Turkish", "vi": "Vietnamese",
        "th": "Thai", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
        "no": "Norwegian", "cs": "Czech", "el": "Greek", "he": "Hebrew",
        "id": "Indonesian", "ms": "Malay", "uk": "Ukrainian", "ro": "Romanian",
        "hu": "Hungarian", "sk": "Slovak", "bg": "Bulgarian", "hr": "Croatian",
        "sr": "Serbian", "sl": "Slovenian", "lt": "Lithuanian", "lv": "Latvian",
        "et": "Estonian", "is": "Icelandic", "ga": "Irish", "mt": "Maltese",
        "mk": "Macedonian", "sq": "Albanian", "ka": "Georgian", "hy": "Armenian",
        "az": "Azerbaijani", "kk": "Kazakh", "uz": "Uzbek", "mn": "Mongolian",
        "ne": "Nepali", "si": "Sinhala", "ta": "Tamil", "te": "Telugu",
        "ml": "Malayalam", "kn": "Kannada", "gu": "Gujarati", "mr": "Marathi",
        "bn": "Bengali", "pa": "Punjabi", "ur": "Urdu", "fa": "Persian",
    }


def transcribe(audio, mode="adaptive", streaming=False, language="en", auto_detect=False):
    """
    Convert audio to text using Whisper.
    T22: Multi-language support with auto-detection.
    """

    # Wait for warmup to complete (max 5s — return error if not ready)
    if not wait_for_model(timeout=5):
        logger.warning("Whisper model not ready after 5s")

    try:
        model = get_model(mode, streaming=streaming)

        # T22: Auto-detect language if requested
        if auto_detect:
            # Whisper auto-detects when language is not specified
            lang = None
        else:
            lang = language

        if streaming:
            # Greedy decoding for real-time — fastest possible path
            segments, info = model.transcribe(
                audio,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
                language=lang,
                best_of=1,
                without_timestamps=True,  # skip timestamp prediction = faster
            )
        else:
            segments, info = model.transcribe(
                audio,
                beam_size=3,          # reduced from 5 — minimal quality loss, faster
                vad_filter=False,      # disabled — adds ~200ms overhead per call
                condition_on_previous_text=False,
                language=lang,
                best_of=3,             # replaces beam_size reduction with non-beam alternatives
                patience=0.3           # less patience = faster
            )

        text = " ".join(seg.text for seg in segments)
        detected = info.language if info else language
        return {"text": text.strip(), "language": detected}

    except Exception as e:
        logger.error("Transcription error: %s", str(e))
        return {"text": "", "language": language}


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

def _decode_audio_file(file_path):
    # PyAV handles mobile AAC/M4A as well as PCM and always resamples to 16 kHz.
    from faster_whisper.audio import decode_audio
    return decode_audio(file_path, sampling_rate=SAMPLE_RATE)


def transcribe_audio(file_path, mode="adaptive", fast=False):
    """Decode an uploaded audio file and return transcript text."""
    try:
        audio = _decode_audio_file(file_path)
        if audio.size == 0 or not np.isfinite(audio).all():
            return ""
        # Do not amplify silence into model input or ask Whisper to invent words.
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-5:
            return ""
        audio = (audio / peak).astype("float32")
        result = transcribe(audio, mode, streaming=fast)
        return result.get("text", "") if isinstance(result, dict) else (result or "")
    except Exception as e:
        logger.error("File transcription error: %s", str(e))
        return ""


def transcribe_fast(file_path):
    """Fastest possible transcription path for uploaded audio files."""
    return transcribe_audio(file_path, mode="adaptive", fast=True)
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
                pass  # nosec B110
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
            sd = _get_sd()
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
                                    pass  # nosec B110  # Skip if queue is full

                    except Exception as e:
                        logger.error("[StreamingTranscriber] Capture error: %s", str(e))
                        time.sleep(0.5)

        except Exception as e:
            logger.error("[StreamingTranscriber] Stream open error: %s", str(e))

    def _transcribe_worker(self):
        """Thread that pulls segments from queue and transcribes them."""
        while True:
            segment = self._transcribe_queue.get()
            if segment is None:  # Sentinel
                break
            try:
                text = transcribe(segment, mode="adaptive", streaming=True)
                if text and text.strip():
                    for cb in self._callbacks:
                        try:
                            cb(text.strip())
                        except Exception as e:
                            logger.error("[StreamingTranscriber] Callback error: %s", str(e))
            except Exception as e:
                logger.error("[StreamingTranscriber] Transcription error: %s", str(e))


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
                # 1.5s segments for lower latency than default 2.0s
                _transcriber_instance = StreamingTranscriber(segment_duration=1.5, overlap_duration=0.3)
    return _transcriber_instance


# ==============================
# BROWSER STREAMING TRANSCRIBER
# ==============================

class BrowserTranscriber:
    """Receives raw PCM Float32 chunks from browser WebSocket, buffers them,
    transcribes at quiet phrase boundaries, returns provisional text via callbacks.

    Per-session (not a singleton) — each WebSocket connection gets its own instance.
    Thread-safe: all shared state (buffer) is protected by self.lock.

    Optimizations for low latency:
    - Waits at least three seconds, then prefers a quiet boundary (eight-second cap)
    - Uses greedy decoding (beam_size=1) for real-time speed
    - The final recording is transcribed separately using complete audio
    """

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.buffer = np.array([], dtype=np.float32)
        self.lock = threading.Lock()
        self.callbacks = []
        self.min_samples_first = int(3.0 * sample_rate)
        self.min_samples_next = self.min_samples_first
        self.max_samples = int(8.0 * sample_rate)
        self._silence_rms = 0.005
        self._chunk_queue = queue.Queue(maxsize=10)
        self._worker = None
        self._texts = []
        self._stopped = threading.Event()

    def add_callback(self, cb):
        """Add a callback for each provisional phrase."""
        self.callbacks.append(cb)

    def _queue_worker(self):
        while True:
            segment = self._chunk_queue.get()
            try:
                if segment is None:
                    return
                if not self._stopped.is_set():
                    self._transcribe(segment)
            finally:
                self._chunk_queue.task_done()

    def add_chunk(self, chunk: np.ndarray):
        """Wait for a quiet phrase boundary, with an eight-second upper bound."""
        if chunk is None or len(chunk) == 0:
            return
        with self.lock:
            if self._stopped.is_set():
                return
            self.buffer = np.concatenate([self.buffer, chunk])
            frame = max(1, int(0.1 * self.sample_rate))
            while len(self.buffer) >= self.min_samples_first:
                limit = min(len(self.buffer), self.max_samples)
                boundary = None
                # Two quiet frames preserve soft word endings and avoid slicing
                # every third second through a word. Inspect all buffered audio
                # so a large WebSocket packet cannot strand complete phrases.
                for end in range(self.min_samples_first, limit + 1, frame):
                    quiet = self.buffer[end - 2 * frame:end]
                    if float(np.sqrt(np.mean(np.square(quiet)))) < self._silence_rms:
                        boundary = end
                        break
                if boundary is None:
                    if len(self.buffer) < self.max_samples:
                        break
                    boundary = self.max_samples
                segment = self.buffer[:boundary].copy()
                self.buffer = self.buffer[boundary:]
                if float(np.sqrt(np.mean(np.square(segment)))) < self._silence_rms:
                    continue
                try:
                    self._chunk_queue.put_nowait(segment)
                except queue.Full:
                    # Previews may skip stale phrases under overload. The full
                    # recording upload remains authoritative for the answer.
                    try:
                        self._chunk_queue.get_nowait()
                        self._chunk_queue.task_done()
                    except queue.Empty:
                        pass
                    self._chunk_queue.put_nowait(segment)

    def start_worker(self):
        with self.lock:
            if self._worker is None and not self._stopped.is_set():
                self._worker = threading.Thread(target=self._queue_worker, daemon=True,
                                                name="browser-transcriber")
                self._worker.start()
            return self._worker

    def stop(self, wait=True):
        """Release the session worker and discard previews after disconnect."""
        with self.lock:
            self._stopped.set()
            self.buffer = np.array([], dtype=np.float32)
            while True:
                try:
                    self._chunk_queue.get_nowait()
                    self._chunk_queue.task_done()
                except queue.Empty:
                    break
            if self._worker is not None and self._worker.is_alive():
                self._chunk_queue.put_nowait(None)
        if wait and self._worker is not None:
            self._worker.join(timeout=1)

    def _transcribe(self, segment):
        """Transcribe a segment using the shared thread pool."""
        try:
            future = _transcribe_executor.submit(transcribe, segment, "adaptive", True)
            result = future.result(timeout=30)
            text = result.get("text", "") if isinstance(result, dict) else (result or "")
            if text and text.strip() and not self._stopped.is_set():
                self._texts.append(text.strip())
                for cb in self.callbacks:
                    try:
                        cb(text.strip())
                    except Exception:
                        pass  # nosec B110
        except Exception as e:
            logger.error("[BrowserTranscriber] Transcription error: %s", str(e))

    def get_final(self) -> str:
        """Drain queued phrases in order and include the final short tail.

        Call off the event loop. The caller must stop accepting audio first.
        """
        self.start_worker()
        self._chunk_queue.join()
        with self.lock:
            segment = self.buffer.copy()
            self.buffer = np.array([], dtype=np.float32)
        if (len(segment) >= int(0.25 * self.sample_rate)
                and float(np.sqrt(np.mean(np.square(segment)))) >= self._silence_rms):
            self._transcribe(segment)
        return " ".join(self._texts)
