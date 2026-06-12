"""
Voice Modules - Speech, TTS, Voice Cloning

Uses try/except for each import because some modules depend on heavy
ML packages (faster-whisper, torch, sounddevice) that may not be
installed in lightweight CI environments.
"""

_module_imports = {}

__all__ = [
    "voice_agent",
    "voice_clone_agent",
    "rvc_engine",
    "whisper_handler",
    "speaker_diarization",
    "vibevoice_diarizer",
]

try:
    from . import voice_agent
    _module_imports['voice_agent'] = True
except ImportError:
    _module_imports['voice_agent'] = False

try:
    from . import voice_clone_agent
    _module_imports['voice_clone_agent'] = True
except ImportError:
    _module_imports['voice_clone_agent'] = False

try:
    from . import rvc_engine
    _module_imports['rvc_engine'] = True
except ImportError:
    _module_imports['rvc_engine'] = False

try:
    from . import whisper_handler
    _module_imports['whisper_handler'] = True
except ImportError:
    _module_imports['whisper_handler'] = False

try:
    from . import speaker_diarization
    _module_imports['speaker_diarization'] = True
except ImportError:
    _module_imports['speaker_diarization'] = False

try:
    from . import vibevoice_diarizer
    _module_imports['vibevoice_diarizer'] = True
except ImportError:
    _module_imports['vibevoice_diarizer'] = False