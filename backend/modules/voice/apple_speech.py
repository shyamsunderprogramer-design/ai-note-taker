"""Optional cached Apple GPU speech recognition; never download during a call."""
import importlib.util
import logging
import os
import platform
import threading
from pathlib import Path

REPOSITORY = 'mlx-community/whisper-small-mlx'
_lock = threading.Lock()
_failed = False
_warm_started = threading.Event()
_warm_lock = threading.Lock()
logger = logging.getLogger(__name__)


def cached_model_path():
    if (platform.system() != 'Darwin' or platform.machine() != 'arm64'
            or os.getenv('ANT_SPEECH_ACCELERATOR', 'auto') == 'cpu'
            or importlib.util.find_spec('mlx_whisper') is None):
        return None
    from huggingface_hub import try_to_load_from_cache
    config = try_to_load_from_cache(REPOSITORY, 'config.json')
    if not isinstance(config, str):
        return None
    directory = Path(config).parent
    return str(directory) if (directory / 'weights.npz').is_file() else None


def transcribe_cached(audio, language='en'):
    global _failed
    if _failed:
        return None
    try:
        directory = cached_model_path()
        if directory is None:
            return None
        import mlx_whisper
        # ModelHolder and Metal buffers are shared across both audio sources.
        with _lock:
            result = mlx_whisper.transcribe(
                audio, path_or_hf_repo=directory, language=language,
                temperature=0.0, condition_on_previous_text=False,
                without_timestamps=True, verbose=None)
        segments = [segment for segment in result.get('segments', [])
                    if segment.get('avg_logprob', 0) >= -1.0
                    and segment.get('compression_ratio', 0) <= 2.8
                    and not (segment.get('no_speech_prob', 0) > .8
                             and segment.get('avg_logprob', 0) < -.3)]
        text = ' '.join(segment.get('text', '') for segment in segments).strip()
        return {'text':text, 'raw_text':text, 'language':result.get('language', language),
                'engine':'whisper-small-mlx'}
    except Exception as error:
        _failed = True
        logger.warning('Apple speech unavailable; using CPU fallback (%s)', type(error).__name__)
        return None


def start_warmup():
    """Compile cached GPU kernels while the user begins speaking."""
    if _warm_started.is_set() or cached_model_path() is None:
        return
    with _warm_lock:
        if _warm_started.is_set():
            return
        _warm_started.set()
        def warm():
            import numpy as np
            transcribe_cached(np.zeros(16000, dtype=np.float32))
        threading.Thread(target=warm, daemon=True, name='apple-speech-warmup').start()
