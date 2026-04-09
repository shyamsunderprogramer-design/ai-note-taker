"""
RVC Engine - Manages TTS + RVC voice conversion pipeline.
Uses tts-with-rvc-onnx for CPU/DirectML inference.
Falls back to edge-tts when no RVC model is loaded.
"""

import os
import logging
import time
import asyncio
import concurrent.futures
import re
from typing import Optional, Dict

logger = logging.getLogger("rvc_engine")

# Lazy import — only load when actually needed
_TTS_RVC_CLASS = None
_IMPORT_ATTEMPTED = False


def _get_tts_rvc_class():
    """Lazy import to avoid startup cost when RVC is not used."""
    global _TTS_RVC_CLASS, _IMPORT_ATTEMPTED
    if _IMPORT_ATTEMPTED:
        return _TTS_RVC_CLASS
    _IMPORT_ATTEMPTED = True
    try:
        from tts_with_rvc import TTS_RVC
        _TTS_RVC_CLASS = TTS_RVC
        logger.info("[RVCEngine] tts-with-rvc-onnx loaded successfully")
    except ImportError as e:
        logger.warning(f"[RVCEngine] tts-with-rvc-onnx not available: {e}")
        _TTS_RVC_CLASS = None
    return _TTS_RVC_CLASS


def detect_device() -> str:
    """
    Detect the best available inference device.
    Priority: dml (Intel GPU via DirectML) > cpu
    """
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if 'DmlExecutionProvider' in providers:
            logger.info("[RVCEngine] Using DirectML (GPU acceleration) for inference")
            return "dml"
    except ImportError:
        pass
    logger.info("[RVCEngine] Using CPU for inference")
    return "cpu"


class RVCEngine:
    """
    Wraps tts-with-rvc-onnx TTS_RVC for voice conversion.
    Manages model loading, device selection, and inference.
    """

    def __init__(self, storage_dir: str = "data/voice_models"):
        self.storage_dir = storage_dir
        self.device = detect_device()
        self._loaded_models: Dict[str, object] = {}
        os.makedirs(os.path.join(storage_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, "_tmp"), exist_ok=True)

    def is_available(self) -> bool:
        """Check if RVC engine is functional."""
        return _get_tts_rvc_class() is not None

    def load_model(self, model_id: str, model_file: str,
                   index_file: str = "", f0_method: str = "rmvpe",
                   edge_voice: str = "en-US-AriaNeural") -> bool:
        """
        Load an RVC model for inference.
        Returns True if successful, False otherwise.
        """
        if not self.is_available():
            logger.warning("[RVCEngine] RVC not available, cannot load model")
            return False

        if model_id in self._loaded_models:
            return True  # Already loaded

        TTS_RVC = _get_tts_rvc_class()
        if TTS_RVC is None:
            return False

        if not os.path.exists(model_file):
            logger.error(f"[RVCEngine] Model file not found: {model_file}")
            return False

        try:
            output_dir = os.path.join(self.storage_dir, "audio")
            tmp_dir = os.path.join(self.storage_dir, "_tmp")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(tmp_dir, exist_ok=True)

            instance = TTS_RVC(
                model_path=model_file,
                index_path=index_file if index_file and os.path.exists(index_file) else "",
                f0_method=f0_method,
                device=self.device,
                tmp_directory=tmp_dir,
                output_directory=output_dir,
            )
            instance.set_voice(edge_voice)
            self._loaded_models[model_id] = instance
            logger.info(f"[RVCEngine] Loaded RVC model {model_id} "
                       f"(device={self.device}, f0={f0_method})")
            return True
        except Exception as e:
            logger.error(f"[RVCEngine] Failed to load model {model_id}: {e}")
            return False

    def unload_model(self, model_id: str):
        """Unload a model from memory."""
        self._loaded_models.pop(model_id, None)

    async def synthesize(self, model_id: str, text: str,
                         pitch: int = 0, index_rate: float = 0.75,
                         filter_radius: int = 3, protect: float = 0.33,
                         rms_mix_rate: float = 0.5) -> Optional[str]:
        """
        Run TTS + RVC pipeline.
        Returns the output audio file path, or None on failure.
        """
        instance = self._loaded_models.get(model_id)
        if instance is None:
            logger.error(f"[RVCEngine] Model {model_id} not loaded")
            return None

        try:
            chunks = self._segment_text(text, max_chars=200)

            if len(chunks) == 1:
                output_path = await self._run_in_executor(
                    instance, chunks[0], pitch, index_rate,
                    filter_radius, protect, rms_mix_rate
                )
                return output_path
            else:
                # Long text: process chunks then concatenate
                chunk_paths = []
                for i, chunk in enumerate(chunks):
                    output_path = await self._run_in_executor(
                        instance, chunk, pitch, index_rate,
                        filter_radius, protect, rms_mix_rate,
                        suffix=f"_chunk{i}"
                    )
                    if output_path and os.path.exists(str(output_path)):
                        chunk_paths.append(str(output_path))
                    else:
                        logger.warning(f"[RVCEngine] Chunk {i} failed, skipping")

                if not chunk_paths:
                    return None
                if len(chunk_paths) == 1:
                    return chunk_paths[0]

                return self._concatenate_audio(chunk_paths, model_id)

        except Exception as e:
            logger.error(f"[RVCEngine] Synthesis failed for {model_id}: {e}")
            return None

    async def _run_in_executor(self, instance, text, pitch, index_rate,
                                filter_radius, protect, rms_mix_rate,
                                suffix=""):
        """Run RVC inference in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()

        def _call():
            try:
                result = instance(
                    text=text,
                    pitch=pitch,
                    index_rate=index_rate,
                    filter_radius=filter_radius,
                    protect=protect,
                    rms_mix_rate=rms_mix_rate,
                )
                return result
            except Exception as e:
                logger.error(f"[RVCEngine] Inference call failed: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(pool, _call)

        return result

    @staticmethod
    def _segment_text(text: str, max_chars: int = 200) -> list:
        """
        Split text into sentence-level chunks to stay under ONNX tensor limits.
        Splits on sentence boundaries (. ! ?) first, then commas, then hard-cut.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_chars:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                while len(sentence) > max_chars:
                    chunks.append(sentence[:max_chars])
                    sentence = sentence[max_chars:]
                current = sentence
        if current:
            chunks.append(current)
        return chunks if chunks else [text]

    @staticmethod
    def _concatenate_audio(audio_paths: list, model_id: str) -> Optional[str]:
        """Concatenate multiple audio files using soundfile."""
        try:
            import soundfile as sf
            import numpy as np

            combined = None
            sr = None
            for path in audio_paths:
                data, samplerate = sf.read(path)
                if combined is None:
                    combined = data
                    sr = samplerate
                else:
                    if data.ndim > 1 and combined.ndim == 1:
                        combined = np.column_stack([combined, combined])
                    elif data.ndim == 1 and combined.ndim > 1:
                        data = np.column_stack([data, data])
                    combined = np.concatenate([combined, data])

            if combined is None:
                return audio_paths[0]

            output_dir = os.path.dirname(audio_paths[0])
            output_path = os.path.join(output_dir, f"rvc_concat_{model_id}_{int(time.time())}.wav")
            sf.write(output_path, combined, sr)
            return output_path

        except Exception as e:
            logger.error(f"[RVCEngine] Audio concatenation failed: {e}")
            return audio_paths[0] if audio_paths else None


# Global instance
rvc_engine = RVCEngine()