"""
Voice Clone Agent
AI-powered voice cloning for interview practice
Uses RVC (Retrieval-based Voice Conversion) + TTS
"""

import os
import json
import time
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

logger = None
try:
    import logging
    logger = logging.getLogger("voice_clone")
except ImportError:
    pass


@dataclass
class VoiceModel:
    id: str
    name: str
    sample_count: int
    created_at: float
    model_path: str
    quality_score: float  # 0-1
    status: str  # "training", "ready", "error"
    # RVC fields (with defaults for backward compatibility)
    model_file: str = ""           # Path to .onnx/.pth RVC model file
    index_file: str = ""           # Path to optional .index feature file
    source: str = "edge_tts"       # "edge_tts", "gallery", "uploaded", "trained"
    f0_method: str = "rmvpe"       # Pitch extraction method
    edge_voice: str = ""           # Edge TTS voice name override
    training_progress: float = 0.0 # 0.0 - 1.0
    training_error: str = ""       # Error message if status == "error"


class VoiceCloneManager:
    """Manages voice cloning for interview practice"""

    def __init__(self, storage_dir: str = "data/voice_models"):
        self.storage_dir = storage_dir
        self.models: Dict[str, VoiceModel] = {}
        self.current_model: Optional[str] = None
        self._rvc_engine = None
        self._rvc_trainer = None

        os.makedirs(storage_dir, exist_ok=True)
        self._load_existing_models()

    @property
    def rvc_engine(self):
        """Lazy-load RVC engine."""
        if self._rvc_engine is None:
            try:
                from rvc_engine import rvc_engine
                self._rvc_engine = rvc_engine
            except ImportError:
                logger.warning("[VoiceClone] RVC engine not available")
        return self._rvc_engine

    @property
    def rvc_trainer(self):
        """Lazy-load RVC trainer."""
        if self._rvc_trainer is None:
            try:
                from rvc_trainer import rvc_trainer
                self._rvc_trainer = rvc_trainer
            except ImportError:
                logger.warning("[VoiceClone] RVC trainer not available")
        return self._rvc_trainer

    def _load_existing_models(self):
        """Load existing voice models from storage"""
        models_file = os.path.join(self.storage_dir, "models.json")
        if os.path.exists(models_file):
            try:
                with open(models_file, 'r') as f:
                    data = json.load(f)
                    for model_data in data.get('models', []):
                        # Handle missing fields from older models.json
                        model_data.setdefault('model_file', '')
                        model_data.setdefault('index_file', '')
                        model_data.setdefault('source', 'edge_tts')
                        model_data.setdefault('f0_method', 'rmvpe')
                        model_data.setdefault('edge_voice', '')
                        model_data.setdefault('training_progress', 0.0)
                        model_data.setdefault('training_error', '')
                        try:
                            model = VoiceModel(**model_data)
                            self.models[model.id] = model
                        except TypeError:
                            # Skip models with unexpected fields
                            if logger:
                                logger.warning(f"Skipping model with incompatible data: {model_data.get('id', 'unknown')}")
            except Exception as e:
                if logger:
                    logger.error("Failed to load voice models: %s", str(e))

    def _save_models(self):
        """Save models metadata to disk"""
        models_file = os.path.join(self.storage_dir, "models.json")
        try:
            data = {'models': [asdict(m) for m in self.models.values()]}
            with open(models_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            if logger:
                logger.error("Failed to save voice models: %s", str(e))

    def _infer_edge_voice(self, name: str) -> str:
        """Map model name keywords to Edge TTS voice."""
        name_lower = name.lower()
        if any(w in name_lower for w in ["male", "guy", "man", "deep"]):
            return "en-US-GuyNeural"
        elif any(w in name_lower for w in ["female", "jen", "woman", "her"]):
            return "en-US-JennyNeural"
        elif any(w in name_lower for w in ["friendly", "casual", "davis", "andrew"]):
            return "en-US-AndrewNeural"
        return "en-US-AriaNeural"

    def create_model(self, name: str, audio_samples: List[str],
                     model_file: Optional[str] = None,
                     index_file: Optional[str] = None,
                     source: str = "edge_tts",
                     gallery_id: Optional[str] = None,
                     edge_voice: Optional[str] = None) -> Dict:
        """
        Create a new voice model.

        Modes:
        - source="edge_tts": No RVC, uses edge-tts only (default)
        - source="uploaded": User provided a pre-trained .onnx file
        - source="gallery": Use a pre-trained gallery voice
        - source="trained": Start background RVC training from audio samples
        """
        model_id = f"voice_{int(time.time())}"
        model_path = os.path.join(self.storage_dir, model_id)
        os.makedirs(model_path, exist_ok=True)

        if not edge_voice:
            edge_voice = self._infer_edge_voice(name)

        # Determine initial status
        if source == "trained" and audio_samples:
            status = "training"
        elif model_file and os.path.exists(model_file):
            status = "ready"
        else:
            status = "ready"  # edge-tts fallback is always ready

        model = VoiceModel(
            id=model_id,
            name=name,
            sample_count=len(audio_samples),
            created_at=time.time(),
            model_path=model_path,
            quality_score=0.70 if status == "ready" else 0.0,
            status=status,
            model_file=model_file or "",
            index_file=index_file or "",
            source=source,
            f0_method="rmvpe",
            edge_voice=edge_voice or self._infer_edge_voice(name),
            training_progress=0.0 if source == "trained" else 1.0,
        )

        self.models[model_id] = model
        self._save_models()

        # Load RVC model immediately if file provided
        if model_file and os.path.exists(model_file) and self.rvc_engine:
            loaded = self.rvc_engine.load_model(
                model_id, model_file,
                index_file=index_file or "",
                f0_method=model.f0_method,
                edge_voice=model.edge_voice,
            )
            if loaded:
                model.quality_score = 0.85
                model.source = "rvc"
                self._save_models()

        # Start background training if requested
        if source == "trained" and audio_samples and self.rvc_trainer:
            return self.rvc_trainer.start_training(
                model_id, name, audio_samples, epochs=200,
                voice_manager=self,
            )

        rvc_available = self.rvc_engine.is_available() if self.rvc_engine else False

        return {
            "model_id": model_id,
            "status": model.status,
            "source": source,
            "rvc_available": rvc_available,
            "message": self._creation_message(source, model_id),
        }

    @staticmethod
    def _creation_message(source: str, model_id: str) -> str:
        messages = {
            "edge_tts": "Voice model created. Using Edge TTS for synthesis.",
            "uploaded": "Voice model created with uploaded RVC model.",
            "gallery": "Voice model created from gallery.",
            "trained": "RVC training started in background. Poll /status for progress.",
        }
        return messages.get(source, "Voice model created.")

    def get_model_status(self, model_id: str) -> Dict:
        """Get training status of a voice model"""
        model = self.models.get(model_id)
        if not model:
            return {"error": "Model not found"}

        # Simulate training completion for edge_tts models
        if model.status == "training" and model.source == "edge_tts":
            elapsed = time.time() - model.created_at
            if elapsed > 60:
                model.status = "ready"
                model.quality_score = 0.75
                model.training_progress = 1.0
                self._save_models()

        # Check RVC trainer status if training
        if model.status == "training" and self.rvc_trainer:
            trainer_status = self.rvc_trainer.get_training_status(model_id)
            if trainer_status:
                model.training_progress = trainer_status["progress"]
                if trainer_status["status"] == "completed":
                    model.status = "ready"
                    model.quality_score = 0.80
                elif trainer_status["status"] == "error":
                    model.status = "error"
                    model.training_error = trainer_status.get("error", "")

        result = {
            "model_id": model_id,
            "name": model.name,
            "status": model.status,
            "quality_score": model.quality_score if model.status == "ready" else None,
            "sample_count": model.sample_count,
            "source": model.source,
            "training_progress": model.training_progress,
            "edge_voice": model.edge_voice,
        }

        # Add RVC availability info
        if self.rvc_engine:
            result["rvc_loaded"] = model_id in self.rvc_engine._loaded_models
            result["rvc_available"] = self.rvc_engine.is_available()
        else:
            result["rvc_loaded"] = False
            result["rvc_available"] = False

        return result

    async def synthesize_speech(self, model_id: str, text: str) -> Dict:
        """
        Synthesize speech using voice model.

        Priority:
        1. If RVC model loaded → edge-tts + RVC conversion (cloned voice)
        2. If no RVC → edge-tts only (natural TTS voice)
        3. If edge-tts unavailable → browser TTS fallback
        """
        model = self.models.get(model_id)
        if not model:
            return {"error": "Model not found"}

        if model.status != "ready":
            return {"error": "Model not ready", "status": model.status}

        # Try RVC pipeline first
        if self.rvc_engine and model_id in self.rvc_engine._loaded_models:
            try:
                rvc_result = await self.rvc_engine.synthesize(
                    model_id, text,
                    pitch=0, index_rate=0.75,
                    filter_radius=3, protect=0.33,
                    rms_mix_rate=0.5,
                )
                if rvc_result and os.path.exists(str(rvc_result)):
                    file_size = os.path.getsize(str(rvc_result))
                    return {
                        "text": text,
                        "model_id": model_id,
                        "voice_name": model.name,
                        "source": "rvc",
                        "output_file": str(rvc_result),
                        "audio_url": f"/voice-clone/audio/{os.path.basename(str(rvc_result))}",
                        "duration_estimate": len(text) * 0.08,
                        "file_size": file_size,
                        "status": "completed",
                    }
            except Exception as e:
                if logger:
                    logger.warning("[VoiceClone] RVC synthesis failed, falling back to edge-tts: %s", str(e))

        # Fall back to edge-tts
        try:
            import edge_tts

            output_dir = os.path.join(self.storage_dir, "audio")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"tts_{model_id}_{int(time.time())}.mp3")

            voice = model.edge_voice or self._infer_edge_voice(model.name)

            # List of voices to try — fall back if primary voice is unavailable
            voices_to_try = [voice, "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural"]
            # Remove duplicates while preserving order
            seen = set()
            voices_to_try = [v for v in voices_to_try if v not in seen and not seen.add(v)]

            last_error = None
            for try_voice in voices_to_try:
                try:
                    communicate = edge_tts.Communicate(text, try_voice)
                    await self._generate_tts(communicate, output_file)

                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        file_size = os.path.getsize(output_file)
                        if logger:
                            logger.info(f"[VoiceClone] Generated audio with voice {try_voice} for model {model_id}")

                        return {
                            "text": text,
                            "model_id": model_id,
                            "voice_name": model.name,
                            "voice_used": try_voice,
                            "source": "edge_tts",
                            "output_file": output_file,
                            "audio_url": f"/voice-clone/audio/{os.path.basename(output_file)}",
                            "duration_estimate": len(text) * 0.08,
                            "file_size": file_size,
                            "status": "completed",
                        }
                    else:
                        last_error = f"Voice {try_voice} produced no output"
                        if logger:
                            logger.warning(f"[VoiceClone] Voice {try_voice} produced no output, trying next")
                        # Clean up empty file
                        if os.path.exists(output_file):
                            try:
                                os.remove(output_file)
                            except OSError:
                                pass  # nosec B110
                except Exception as e:
                    last_error = str(e)
                    if logger:
                        logger.warning("[VoiceClone] Voice {try_voice} failed: %s, trying next", str(e))
                    # Clean up partial file
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except OSError:
                            pass  # nosec B110
                    continue

        except ImportError:
            return {
                "text": text,
                "model_id": model_id,
                "voice_name": model.name,
                "duration_estimate": len(text) * 0.08,
                "status": "completed",
                "browser_tts": True,
                "source": "browser",
                "note": "Edge TTS not installed. Using browser fallback.",
            }
        except Exception as e:
            if logger:
                logger.error("[VoiceClone] TTS synthesis error: %s", str(e))
            return {"error": "An internal error occurred"}

    @staticmethod
    async def _generate_tts(communicate, output_file):
        """Generate TTS audio file using edge-tts."""
        await communicate.save(output_file)

    def list_models(self) -> List[Dict]:
        """List all voice models"""
        return [
            {
                "id": m.id,
                "name": m.name,
                "status": m.status,
                "quality_score": m.quality_score,
                "sample_count": m.sample_count,
                "created_at": m.created_at,
                "source": m.source,
                "edge_voice": m.edge_voice,
            }
            for m in self.models.values()
        ]

    def delete_model(self, model_id: str) -> bool:
        """Delete a voice model"""
        if model_id not in self.models:
            return False

        model = self.models[model_id]

        # Unload RVC model if loaded
        if self.rvc_engine:
            self.rvc_engine.unload_model(model_id)

        try:
            import shutil
            if os.path.exists(model.model_path):
                shutil.rmtree(model.model_path)
        except Exception:
            pass  # nosec B110

        del self.models[model_id]
        self._save_models()
        return True


class PracticeSession:
    """Interview practice session with voice clone"""

    def __init__(self, voice_manager: VoiceCloneManager, model_id: str):
        self.voice_manager = voice_manager
        self.model_id = model_id
        self.messages = []
        self.started_at = time.time()

    async def ask_question(self, question: str) -> Dict:
        """Ask a question using cloned voice"""
        result = await self.voice_manager.synthesize_speech(self.model_id, question)

        self.messages.append({
            "role": "interviewer",
            "text": question,
            "timestamp": time.time()
        })

        return result

    def record_response(self, text: str) -> None:
        """Record user's response"""
        self.messages.append({
            "role": "user",
            "text": text,
            "timestamp": time.time()
        })

    def get_session_summary(self) -> Dict:
        """Get practice session summary"""
        return {
            "duration_minutes": (time.time() - self.started_at) / 60,
            "questions_asked": len([m for m in self.messages if m["role"] == "interviewer"]),
            "user_responses": len([m for m in self.messages if m["role"] == "user"]),
            "messages": self.messages
        }


# Global instance
voice_manager = VoiceCloneManager()


# API convenience functions
def create_voice_model(name: str, audio_samples: List[str], **kwargs) -> Dict:
    return voice_manager.create_model(name, audio_samples, **kwargs)


def get_voice_status(model_id: str) -> Dict:
    return voice_manager.get_model_status(model_id)


async def synthesize_voice(model_id: str, text: str) -> Dict:
    return await voice_manager.synthesize_speech(model_id, text)


def list_voice_models() -> List[Dict]:
    return voice_manager.list_models()


def create_practice_session(model_id: str) -> PracticeSession:
    return PracticeSession(voice_manager, model_id)