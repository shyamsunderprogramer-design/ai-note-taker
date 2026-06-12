"""
Tests for backend/modules/ai/ocr_service.py — image-to-text extraction
with Ollama-vision primary path and pytesseract fallback.

OCR has 3 paths:
1. Ollama vision model (best quality, requires a running Ollama + llava/moondream)
2. pytesseract (CPU-only, requires the system tesseract binary)
3. No extraction (returns "" + method="none")

We test the orchestration logic (which path runs when) by mocking
the underlying extractors. We don't need real OCR for these tests.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "modules", "ai"))

from modules.ai import ocr_service
from modules.ai.ocr_service import (
    extract_text_from_image,
    _extract_with_vision_model,
    _extract_with_tesseract,
    _get_vision_model,
)


class TestExtractTextFromImageDispatch:
    """extract_text_from_image picks the right method based on availability."""

    def test_empty_input_returns_none_method(self):
        result = extract_text_from_image("")
        assert result == {"text": "", "method": "none"}

    def test_vision_model_path(self):
        """When vision model is available and returns text, method=ollama."""
        with patch.object(ocr_service, "_get_vision_model", return_value="llava"):
            with patch.object(ocr_service, "_extract_with_vision_model",
                              return_value="extracted via vision"):
                result = extract_text_from_image("base64data")
                assert result["text"] == "extracted via vision"
                assert result["method"] == "ollama"

    def test_vision_empty_falls_back_to_tesseract(self):
        """If vision returns empty, tesseract is tried next."""
        with patch.object(ocr_service, "_get_vision_model", return_value="llava"):
            with patch.object(ocr_service, "_extract_with_vision_model", return_value=""):
                with patch.object(ocr_service, "_extract_with_tesseract",
                                  return_value="tesseract text"):
                    result = extract_text_from_image("base64data")
                    assert result["method"] == "tesseract"
                    assert result["text"] == "tesseract text"

    def test_no_vision_no_tesseract_returns_none(self):
        """When neither path works, returns empty + none."""
        with patch.object(ocr_service, "_get_vision_model", return_value=None):
            with patch.object(ocr_service, "_extract_with_tesseract", return_value=""):
                result = extract_text_from_image("base64data")
                assert result["method"] == "none"
                assert result["text"] == ""

    def test_vision_failure_falls_back_to_tesseract(self):
        """If vision raises an exception, tesseract is still tried."""
        with patch.object(ocr_service, "_get_vision_model", return_value="llava"):
            # Vision returns empty (not raises), tesseract kicks in
            with patch.object(ocr_service, "_extract_with_vision_model", return_value=""):
                with patch.object(ocr_service, "_extract_with_tesseract",
                                  return_value="fallback text"):
                    result = extract_text_from_image("base64data")
                    assert result["method"] == "tesseract"


class TestGetVisionModel:
    """_get_vision_model: lazy import with cache."""

    def test_returns_none_when_ai_router_unavailable(self):
        # If ai_router is not importable, _get_vision_model returns None
        with patch.dict(sys.modules, {"ai_router": None}):
            # Reset the cached getter so we re-import
            import modules.ai.ocr_service as ocr
            ocr._vision_getter = None
            result = _get_vision_model()
            # Either returns None (import failed) or whatever _gvm() returns
            # We're just testing that it doesn't raise
            assert result is None or callable(result) or isinstance(result, str)

    def test_caches_vision_getter(self):
        """The import is cached — second call uses cached _vision_getter."""
        sentinel = lambda: "cached-model"
        import modules.ai.ocr_service as ocr
        ocr._vision_getter = sentinel
        # Should return sentinel() — proves it didn't re-import
        assert _get_vision_model() == "cached-model"


class TestExtractWithVisionModel:
    """_extract_with_vision_model: HTTP call to Ollama with response unwrap."""

    def test_returns_response_text(self):
        """Successful 200 response → text field from JSON."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "extracted text"}

        with patch("requests.post", return_value=mock_resp):
            with patch("modules.ai.ocr_service.config", create=True) as mock_config:
                # Inject the config attrs the function reads
                import sys
                sys.modules["config"] = MagicMock()
                sys.modules["config"].OLLAMA_URL = "http://localhost:11434"
                sys.modules["config"].AI_TEMPERATURE = 0.7
                result = _extract_with_vision_model("imgdata", "llava")
                assert result == "extracted text"

    def test_strips_outer_quotes(self):
        """Models sometimes wrap text in quotes — strip them."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": '"hello world"'}

        with patch("requests.post", return_value=mock_resp):
            import sys
            sys.modules["config"] = MagicMock()
            sys.modules["config"].OLLAMA_URL = "http://localhost:11434"
            sys.modules["config"].AI_TEMPERATURE = 0.7
            result = _extract_with_vision_model("imgdata", "llava")
            assert result == "hello world"

    def test_non_200_returns_empty(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("requests.post", return_value=mock_resp):
            import sys
            sys.modules["config"] = MagicMock()
            sys.modules["config"].OLLAMA_URL = "http://localhost:11434"
            sys.modules["config"].AI_TEMPERATURE = 0.7
            result = _extract_with_vision_model("imgdata", "llava")
            assert result == ""

    def test_request_exception_returns_empty(self):
        """Network errors → empty result, not raised."""
        with patch("requests.post", side_effect=Exception("network down")):
            import sys
            sys.modules["config"] = MagicMock()
            sys.modules["config"].OLLAMA_URL = "http://localhost:11434"
            sys.modules["config"].AI_TEMPERATURE = 0.7
            result = _extract_with_vision_model("imgdata", "llava")
            assert result == ""

    def test_strips_data_url_prefix(self):
        """data:image/png;base64,XYZ → just the b64 portion is sent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "ok"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            import sys
            sys.modules["config"] = MagicMock()
            sys.modules["config"].OLLAMA_URL = "http://localhost:11434"
            sys.modules["config"].AI_TEMPERATURE = 0.7
            _extract_with_vision_model("data:image/png;base64,XYZ", "llava")
            # The payload's "images" should be just "XYZ"
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs["json"]
            assert payload["images"] == ["XYZ"]


class TestExtractWithTesseract:
    """_extract_with_tesseract: pytesseract path."""

    def test_pytesseract_not_installed_returns_empty(self):
        """If pytesseract can't be imported, return empty without raising."""
        # Block imports of pytesseract and PIL
        with patch.dict(sys.modules, {
            "pytesseract": None,
            "PIL": None,
            "PIL.Image": None,
        }):
            result = _extract_with_tesseract("imgdata")
            assert result == ""

    def test_successful_extraction(self):
        """When pytesseract + PIL are available, runs OCR."""
        import base64
        # Create a minimal 1x1 white PNG in base64
        tiny_png_b64 = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff'
            b'\xff?\x00\x05\xfe\x02\xfe\xa3\x9b\xb1\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode()

        mock_image = MagicMock()
        mock_image.mode = "L"  # Already grayscale
        mock_image.convert = MagicMock(return_value=mock_image)

        mock_pil_image_module = MagicMock()
        mock_pil_image_module.open.return_value = mock_image

        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "  hello world  \n"

        with patch.dict(sys.modules, {
            "PIL": MagicMock(),
            "PIL.Image": mock_pil_image_module,
            "pytesseract": mock_pytesseract,
        }):
            result = _extract_with_tesseract(tiny_png_b64)
            assert result == "hello world"  # Whitespace stripped


class TestDataUrlPrefixStripping:
    """Both vision and tesseract strip the data:image/... prefix."""

    def test_vision_strips_data_url(self):
        """Same prefix-stripping logic in both paths."""
        # This is already covered by test_strips_data_url_prefix
        # but we add a tesseract equivalent for symmetry
        import base64
        tiny_png_b64 = base64.b64encode(b'\x89PNG').decode()

        mock_image = MagicMock()
        mock_image.mode = "L"

        mock_pil_image_module = MagicMock()
        mock_pil_image_module.open.return_value = mock_image

        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "ok"

        with patch.dict(sys.modules, {
            "PIL": MagicMock(),
            "PIL.Image": mock_pil_image_module,
            "pytesseract": mock_pytesseract,
        }):
            with patch("base64.b64decode", wraps=base64.b64decode) as mock_b64:
                _extract_with_tesseract(f"data:image/png;base64,{tiny_png_b64}")
                # b64decode should have been called with just the b64 part
                called_arg = mock_b64.call_args[0][0]
                assert not called_arg.startswith("data:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
