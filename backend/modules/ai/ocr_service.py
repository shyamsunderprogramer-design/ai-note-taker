"""
OCR Service — Extract text from screenshots/images.

Pipeline:
1. Use native Apple Vision on macOS when available.
2. Retain Ollama vision and pytesseract fallbacks on other installations.
3. Return an empty result if no extractor is available.
"""

import base64
import json
import logging
from lib.native_ocr import extract_native_text
from io import BytesIO

logger = logging.getLogger("ocr_service")

# Lazy imports — only loaded when needed
_vision_getter = None


def _get_vision_model():
    """Lazily import and call ai_router._get_vision_model()."""
    global _vision_getter
    if _vision_getter is not None:
        return _vision_getter()
    try:
        from ai_router import _get_vision_model as _gvm
        _vision_getter = _gvm
        return _gvm()
    except Exception as e:
        logger.warning("[OCR] Could not import ai_router._get_vision_model: %s", str(e))
        return None


def _extract_with_vision_model(image_b64: str, model_name: str) -> str:
    """Use an Ollama vision model to extract text from an image."""
    import requests
    from config import OLLAMA_URL, AI_TEMPERATURE

    prompt = (
        "Extract all visible text from this image. "
        "Output ONLY the extracted text exactly as it appears, "
        "with no commentary, explanation, or additional formatting."
    )

    # Strip data URL prefix if present
    raw_b64 = image_b64.split(",")[-1] if "," in image_b64 else image_b64

    payload = {
        "model": model_name,
        "prompt": prompt,
        "images": [raw_b64],
        "stream": False,
        "think": False,  # OCR output must not contain model deliberation
        "options": {
            "temperature": 0.1,  # Low temp for precise extraction
            "num_predict": 2048,
            "num_ctx": 4096,
        },
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=60,
        )
        if response.status_code == 200:
            data = response.json()
            text = data.get("response", "").strip()
            # Vision models sometimes add quotes or commentary — strip common wrappers
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            if text.startswith("'") and text.endswith("'"):
                text = text[1:-1]
            return text
        else:
            logger.warning("[OCR] Vision model returned HTTP %d", response.status_code)
            return ""
    except Exception as e:
        logger.warning("[OCR] Vision model extraction failed: %s", str(e))
        return ""


def _extract_with_tesseract(image_b64: str) -> str:
    """Use pytesseract for OCR extraction."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        logger.info("[OCR] pytesseract or Pillow not installed, skipping tesseract extraction")
        return ""

    try:
        raw_b64 = image_b64.split(",")[-1] if "," in image_b64 else image_b64
        image_data = base64.b64decode(raw_b64)
        image = Image.open(BytesIO(image_data))

        # Convert to grayscale for better OCR accuracy
        if image.mode != "L":
            image = image.convert("L")

        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.warning("[OCR] Tesseract extraction failed: %s", str(e))
        return ""


def extract_text_from_image(image_b64: str) -> dict:
    """
    Extract text from a base64-encoded image.

    Prefers native macOS text recognition, then tries the existing vision
    model and pytesseract fallbacks when native OCR is unavailable.

    Returns:
        dict: { "text": str, "method": "apple-vision"|"ollama"|"tesseract"|"none" }
    """
    if not image_b64:
        return {"text": "", "method": "none"}

    # Native OCR returns literal text, without asking a language model to describe it.
    native_text = extract_native_text(image_b64)
    if native_text is not None:
        return {"text": native_text, "method": "apple-vision"}

    # Step 1: Try Ollama vision model
    vision_model = _get_vision_model()
    if vision_model:
        logger.info("[OCR] Trying vision model: %s", vision_model)
        text = _extract_with_vision_model(image_b64, vision_model)
        if text:
            logger.info("[OCR] Vision model extracted %d chars", len(text))
            return {"text": text, "method": "ollama"}
        logger.info("[OCR] Vision model returned empty, falling back to tesseract")

    # Step 2: Try pytesseract
    logger.info("[OCR] Trying tesseract extraction")
    text = _extract_with_tesseract(image_b64)
    if text:
        logger.info("[OCR] Tesseract extracted %d chars", len(text))
        return {"text": text, "method": "tesseract"}

    # Step 3: No extraction possible
    logger.warning("[OCR] No text could be extracted from the image")
    return {"text": "", "method": "none"}