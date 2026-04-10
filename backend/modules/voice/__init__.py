"""
Voice Modules - Speech, TTS, Voice Cloning

Uses try/except for each import because some modules depend on heavy
ML packages (faster-whisper, torch, sounddevice) that may not be
installed in lightweight CI environments.
"""

_module_imports = {}

try:
    from .voice_agent import *
    _module_imports['voice_agent'] = True
except ImportError:
    _module_imports['voice_agent'] = False

try:
    from .voice_clone_agent import *
    _module_imports['voice_clone_agent'] = True
except ImportError:
    _module_imports['voice_clone_agent'] = False

try:
    from .rvc_engine import *
    _module_imports['rvc_engine'] = True
except ImportError:
    _module_imports['rvc_engine'] = False

try:
    from .whisper_handler import *
    _module_imports['whisper_handler'] = True
except ImportError:
    _module_imports['whisper_handler'] = False

try:
    from .speaker_diarization import *
    _module_imports['speaker_diarization'] = True
except ImportError:
    _module_imports['speaker_diarization'] = False