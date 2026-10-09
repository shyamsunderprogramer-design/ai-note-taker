"""Route module for voice clone agent endpoints."""
import logging
import os
import shutil
import time
from typing import List

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from security import rate_limit, ErrorCode, error_response
from security.auth import User

# Auth helpers (mirrored — will be consolidated)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security import get_current_user

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


from routes.deps import require_authentication


logger = logging.getLogger("routes.voice")

# Voice clone availability
try:
    from voice_clone_agent import (
        voice_manager,
        create_voice_model,
        get_voice_status,
        synthesize_voice,
        list_voice_models
    )
    VOICE_CLONE_AVAILABLE = True
except ImportError as e:
    VOICE_CLONE_AVAILABLE = False

# RVC gallery availability
try:
    from rvc_gallery import list_gallery, get_gallery_voice
    RVC_GALLERY_AVAILABLE = True
except ImportError as e:
    RVC_GALLERY_AVAILABLE = False

router = APIRouter()


@router.get("/voice-clone/local-engine")
async def local_voice_status(user: User = Depends(require_authentication)):
    if not VOICE_CLONE_AVAILABLE:
        raise HTTPException(503, "Voice clone not available")
    from modules.voice.local_clone_engine import get_local_clone_engine
    return get_local_clone_engine(voice_manager.storage_dir).status()


@router.post("/voice-clone/local-engine/setup")
async def setup_local_voice(user: User = Depends(require_authentication)):
    if not VOICE_CLONE_AVAILABLE:
        raise HTTPException(503, "Voice clone not available")
    from modules.voice.local_clone_engine import get_local_clone_engine
    return get_local_clone_engine(voice_manager.storage_dir).start_setup()


@router.post("/voice-clone/create")
@rate_limit(requests_per_minute=10)
async def create_voice_clone(
    name: str = Form(..., description="Name for this voice model"),
    audio_files: List[UploadFile] = File(default=[]),
    engine: str = Form("qwen_local"),
    ref_text: str = Form(""),
    user: User = Depends(require_authentication)
):
    """Create a new voice clone model from audio files."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        from voice_clone_agent import voice_manager

        if engine not in ("edge_tts", "qwen_local"):
            raise HTTPException(422, "Unknown voice engine")
        if engine == "qwen_local":
            if len(audio_files) != 1 or not ref_text.strip():
                raise HTTPException(422, "Add one clean recording and type the words spoken in it")
            sample = audio_files[0]
            audio = await sample.read(20 * 1024 * 1024 + 1)
            if not audio or len(audio) > 20 * 1024 * 1024:
                raise HTTPException(422, "Reference audio must be between 1 byte and 20 MB")
            from voice_clone_agent import VoiceModel
            import uuid
            import asyncio
            from pathlib import Path
            model_id = f"voice_{uuid.uuid4().hex}"
            model_path = Path(voice_manager.storage_dir) / model_id
            model_path.mkdir(parents=True)
            extension = Path(sample.filename or "reference.wav").suffix.lower()
            if extension not in (".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".mp4"):
                shutil.rmtree(model_path)
                raise HTTPException(422, "Unsupported reference audio format")
            reference = model_path / "reference.wav"
            uploaded = model_path / ("upload" + extension)
            try:
                uploaded.write_bytes(audio)
                # Decode recordings and uploads into the same mono WAV format.
                ffmpeg = shutil.which("ffmpeg")
                if ffmpeg:
                    process = await asyncio.create_subprocess_exec(
                        ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(uploaded),
                        "-t", "21", "-ac", "1", "-ar", "24000", str(reference),
                        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
                    )
                    try:
                        _, errors = await asyncio.wait_for(process.communicate(), 30)
                    except BaseException:
                        if process.returncode is None:
                            process.kill()
                            await process.wait()
                        raise
                    if process.returncode:
                        raise HTTPException(422, "Could not decode the reference recording")
                else:
                    import soundfile as sf
                    import numpy as np
                    try:
                        def decode():
                            waveform, sample_rate = sf.read(uploaded, dtype="float32", always_2d=True)
                            if len(waveform) > sample_rate * 20:
                                raise ValueError("Reference must be at most 20 seconds")
                            sf.write(reference, np.mean(waveform, axis=1), sample_rate)
                        await asyncio.to_thread(decode)
                    except Exception as exc:
                        raise HTTPException(422, "Use a WAV recording, or install ffmpeg for other formats") from exc
                import soundfile as sf
                info = sf.info(reference)
                if not 3 <= info.duration <= 20:
                    raise HTTPException(422, "Use a recording between 3 and 20 seconds; 3–10 seconds works best")
                if len(ref_text.strip()) > 2000:
                    raise HTTPException(422, "Reference transcript is too long")
                uploaded.unlink(missing_ok=True)
                voice_manager.models[model_id] = VoiceModel(
                    id=model_id, name=name, sample_count=1, created_at=time.time(),
                    model_path=str(model_path), quality_score=0.0, status="ready",
                    source="qwen_local", reference_audio=str(reference), reference_text=ref_text.strip(),
                )
                voice_manager._save_models()
            except BaseException:
                shutil.rmtree(model_path, ignore_errors=True)
                voice_manager.models.pop(model_id, None)
                raise
            return {"model_id": model_id, "status": "ready", "source": "qwen_local",
                    "message": "Reference voice saved. Generate speech below."}

        audio_paths = []
        for audio_file in audio_files:
            if audio_file.filename:
                # SECURITY: Sanitize filename to prevent path traversal
                safe_filename = os.path.basename(audio_file.filename)
                if safe_filename != audio_file.filename or ".." in audio_file.filename:
                    continue  # Skip files with directory traversal attempts
                temp_path = os.path.join("data", "temp_audio", safe_filename)
                os.makedirs("data/temp_audio", exist_ok=True)
                with open(temp_path, "wb") as f:
                    shutil.copyfileobj(audio_file.file, f)
                audio_paths.append(temp_path)

        result = voice_manager.create_model(name, audio_paths)
        model_id = result.get("model_id", "")

        model_path = os.path.join("data/voice_models", model_id)
        if model_id and os.path.exists(model_path):
            for i, src_path in enumerate(audio_paths):
                ext = os.path.splitext(src_path)[1] or ".webm"
                dst_path = os.path.join(model_path, f"sample_{i}{ext}")
                shutil.copy2(src_path, dst_path)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[VoiceClone] Create error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/voice-clone/models")
async def list_voice_clones(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """List all voice models with pagination."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available")

    try:
        all_models = list_voice_models()
        total = len(all_models)
        return {
            "models": all_models[offset:offset + limit],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error("[VoiceClone] List error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred")


@router.delete("/voice-clone/models/{model_id}")
async def delete_voice_clone(model_id: str, user: User = Depends(require_authentication)):
    """Delete a voice model."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        from voice_clone_agent import voice_manager
        success = voice_manager.delete_model(model_id)
        if success:
            return {"status": "deleted", "model_id": model_id}
        else:
            return error_response(ErrorCode.MODEL_NOT_FOUND, "Model not found", status_code=404)
    except Exception as e:
        logger.error("[VoiceClone] Delete error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/voice-clone/{model_id}/status")
async def get_voice_clone_status(model_id: str):
    """Get voice model training status."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        return get_voice_status(model_id)
    except Exception as e:
        logger.error("[VoiceClone] Status error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.post("/voice-clone/{model_id}/synthesize")
async def synthesize_voice_clone(
    model_id: str,
    request: Request
):
    """Synthesize speech using voice model."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        body = await request.json()
        text = body.get("text", "")
        if not text:
            return error_response(ErrorCode.MISSING_PARAMETER, "Text is required", status_code=422)

        result = await synthesize_voice(model_id, text)

        if "error" in result:
            return result

        return {
            "status": result.get("status", "completed"),
            "text": text,
            "model_id": model_id,
            "voice_name": result.get("voice_name", ""),
            "voice_used": result.get("voice_used", ""),
            "output_file": result.get("output_file", ""),
            "audio_url": result.get("audio_url", ""),
            "duration_estimate": result.get("duration_estimate", 0),
            "file_size": result.get("file_size", 0),
            "browser_tts": result.get("browser_tts", False),
        }
    except Exception as e:
        logger.error("[VoiceClone] Synthesis error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)


@router.get("/voice-clone/audio/{filename}")
async def get_voice_audio(filename: str):
    """Serve generated TTS audio files."""
    from fastapi.responses import FileResponse

    # SECURITY: Validate filename before any path operations to prevent path traversal
    # Reject paths with directory separators or parent directory references
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid filename", status_code=400)

    # SECURITY: Sanitize filename to prevent path traversal
    # Strip directory components and validate the result
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename != filename:
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid filename", status_code=400)

    # SECURITY: Resolve absolute paths and ensure the file is within the audio directory
    audio_dir = os.path.abspath(os.path.join(voice_manager.storage_dir, "audio"))
    file_path = os.path.abspath(os.path.join(audio_dir, safe_filename))

    # Ensure the resolved path is still within the audio directory
    if not file_path.startswith(audio_dir + os.sep):
        return error_response(ErrorCode.VALIDATION_ERROR, "Invalid filename", status_code=400)

    if not os.path.exists(file_path):
        return error_response(ErrorCode.NOT_FOUND, "Audio file not found", status_code=404)
    return FileResponse(file_path, media_type="audio/wav" if safe_filename.endswith(".wav") else "audio/mpeg", filename=safe_filename)


@router.get("/voice-clone/gallery")
async def voice_clone_gallery(category: str = None, gender: str = None):
    """List available pre-trained voice gallery models."""
    if not RVC_GALLERY_AVAILABLE:
        return {"voices": [], "error": "Gallery not available"}
    return {"voices": list_gallery(category=category, gender=gender)}


@router.post("/voice-clone/gallery/{gallery_id}/install")
async def install_gallery_voice(gallery_id: str):
    """Install a gallery voice as a voice model."""
    if not RVC_GALLERY_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Gallery not available", status_code=503)

    gallery_voice = get_gallery_voice(gallery_id)
    if not gallery_voice:
        return error_response(ErrorCode.NOT_FOUND, f"Gallery voice '{gallery_id}' not found", status_code=404)

    result = voice_manager.create_model(
        name=gallery_voice.name,
        audio_samples=[],
        source="gallery",
        gallery_id=gallery_voice.id,
        edge_voice=gallery_voice.edge_voice,
    )

    model_id = result.get("model_id")
    if model_id and model_id in voice_manager.models:
        model = voice_manager.models[model_id]
        model.source = "gallery"
        model.quality_score = 0.80
        model.f0_method = gallery_voice.f0_method
        voice_manager._save_models()

    return {
        **result,
        "gallery_id": gallery_voice.id,
        "edge_voice": gallery_voice.edge_voice,
        "category": gallery_voice.category,
        "gender": gallery_voice.gender,
    }


@router.post("/voice-clone/create-rvc")
@rate_limit(requests_per_minute=5)
async def create_rvc_voice_model(
    name: str = Form(..., description="Name for this voice model"),
    model_file: UploadFile = File(..., description="RVC model file (.onnx or .pth)"),
    index_file: UploadFile = File(default=None, description="Optional feature index file (.index)"),
):
    """Create a voice model from an uploaded RVC model file."""
    if not VOICE_CLONE_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "Voice clone not available", status_code=503)

    try:
        from voice_clone_agent import voice_manager

        model_id = f"voice_{int(time.time())}"
        model_dir = os.path.join("data", "voice_models", model_id)
        os.makedirs(model_dir, exist_ok=True)

        # SECURITY: Validate file extension to prevent path traversal
        model_ext = os.path.splitext(os.path.basename(model_file.filename))[1] or ".onnx"
        if model_ext not in (".onnx", ".pth", ".pt"):
            return error_response(ErrorCode.VALIDATION_ERROR, "Invalid model file extension. Only .onnx, .pth, .pt allowed.", status_code=400)
        model_path = os.path.join(model_dir, f"model{model_ext}")
        with open(model_path, "wb") as f:
            shutil.copyfileobj(model_file.file, f)

        index_path = ""
        if index_file and index_file.filename:
            index_path = os.path.join(model_dir, f"model.index")
            with open(index_path, "wb") as f:
                shutil.copyfileobj(index_file.file, f)

        result = voice_manager.create_model(
            name=name,
            audio_samples=[],
            source="uploaded",
            model_file=model_path,
            index_file=index_path,
        )

        return result

    except Exception as e:
        logger.error("[VoiceClone] RVC create error: %s", str(e))
        return error_response(ErrorCode.INTERNAL_ERROR, "An internal error occurred", status_code=500)