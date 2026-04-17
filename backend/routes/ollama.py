"""Route module for Ollama model management and provider/BYOK endpoints."""
import logging
import os
import time
import threading
from typing import Dict

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from config import OLLAMA_URL
from lib.http_client import sync_client
from security import (
    get_current_user, ErrorCode, error_response,
)
from security.auth import User

# Auth helpers (mirrored from auth.py — will be consolidated in a shared deps module)
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_bearer = HTTPBearer(auto_error=False)


async def get_token_from_request(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> str:
    if credentials:
        return credentials.credentials
    return None


async def require_authentication(token: str = Depends(get_token_from_request)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


# Provider key cache
_provider_key_cache: Dict[str, bool] = {}
_provider_key_cache_time: list = [0.0]  # mutable list to avoid closure scope issue
_PROVIDER_KEY_CACHE_TTL = 300


def _has_provider_key(provider: str, env_var: str) -> bool:
    """Check if a provider has an API key, using a short-lived cache."""
    now = time.time()

    if provider in _provider_key_cache and (now - _provider_key_cache_time[0]) < _PROVIDER_KEY_CACHE_TTL:
        return _provider_key_cache[provider]

    if os.getenv(env_var, "").strip():
        _provider_key_cache[provider] = True
        _provider_key_cache_time[0] = now
        return True

    try:
        resp = sync_client.post(
            "http://127.0.0.1:18000/get-key",
            json={"provider": provider},
            timeout=1
        )
        if resp.status_code == 200:
            data = resp.json()
            result = bool(data.get("apiKey"))
        else:
            result = False
    except Exception:
        result = False

    _provider_key_cache[provider] = result
    _provider_key_cache_time[0] = now
    return result


# User API keys
try:
    from user_api_keys import (
        user_key_manager,
        get_available_providers,
        has_premium_access,
        get_provider_cost_info,
        PROVIDER_COSTS,
    )
    BYOK_AVAILABLE = True
except ImportError:
    BYOK_AVAILABLE = False

logger = logging.getLogger("routes.ollama")

# Import audit logger
from security import log_audit_event

router = APIRouter()


@router.get("/ollama/models")
def list_ollama_models():
    """Proxy to Ollama's GET /api/tags — returns installed local models."""
    try:
        response = sync_client.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            return response.json()
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"Ollama returned {response.status_code}", status_code=502) | {"models": []}
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500) | {"models": []}


@router.post("/ollama/pull")
def pull_ollama_model(model: str = Query(...)):
    """Trigger a model pull — runs async, returns immediately."""
    def background_pull():
        try:
            logger.info("Starting model pull: %s", model)
            pull_resp = sync_client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": model},
                stream=True,
                timeout=3600
            )
            for line in pull_resp.iter_lines():
                if line:
                    logger.info("[Ollama pull] %s", line.decode("utf-8", errors="replace"))
            logger.info("Model pull complete: %s", model)
        except Exception as e:
            logger.error("Model pull failed for %s: %s", model, e)

    threading.Thread(target=background_pull, daemon=True).start()
    return {"status": "pull_started", "model": model}


@router.delete("/ollama/models/{model_name}")
def delete_ollama_model(model_name: str):
    """Delete a local Ollama model."""
    try:
        response = sync_client.delete(
            f"{OLLAMA_URL}/api/delete",
            json={"name": model_name},
            timeout=30
        )
        if response.status_code == 200:
            return {"status": "deleted", "model": model_name}
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"Failed to delete model: {response.status_code}", status_code=502)
    except Exception as e:
        return error_response(ErrorCode.INTERNAL_ERROR, str(e), status_code=500)


@router.get("/providers")
async def list_providers(request=None):
    """Returns which cloud providers have API keys configured"""
    return {
        "openai": _has_provider_key("openai", "OPENAI_API_KEY"),
        "anthropic": _has_provider_key("anthropic", "ANTHROPIC_API_KEY"),
        "google": _has_provider_key("google", "GOOGLE_API_KEY"),
        "xai": _has_provider_key("xai", "XAI_API_KEY"),
        "deepseek": _has_provider_key("deepseek", "DEEPSEEK_API_KEY"),
        "groq": _has_provider_key("groq", "GROQ_API_KEY"),
        "ollama-cloud": _has_provider_key("ollama-cloud", "OLLAMA_CLOUD_API_KEY"),
        "perplexity": _has_provider_key("perplexity", "PERPLEXITY_API_KEY"),
        "ollama": True
    }


@router.get("/providers/byok/status")
async def get_byok_status(user: User = Depends(require_authentication)):
    """Get user's BYOK status - which providers they have configured"""
    if not BYOK_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "BYOK module not available", status_code=503)

    providers = get_available_providers(user.id)
    has_premium = has_premium_access(user.id)

    provider_info = {}
    for provider, has_key in providers.items():
        cost_info = get_provider_cost_info(provider)
        provider_info[provider] = {
            "configured": has_key,
            "name": cost_info["name"],
            "cost_per_1k_input": cost_info["input"],
            "cost_per_1k_output": cost_info["output"],
        }

    return {
        "has_premium_access": has_premium,
        "providers": provider_info,
        "ollama_available": True,
        "message": "Free tier uses Ollama. Add your own API keys for premium providers."
    }


@router.post("/providers/byok/configure")
async def configure_provider_key(
    user: User = Depends(require_authentication),
    provider: str = Form(...),
    api_key: str = Form(...)
):
    """Configure user's own API key for a premium provider"""
    if not BYOK_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "BYOK module not available", status_code=503)

    valid_providers = ["openai", "anthropic", "google", "xai", "deepseek", "groq", "perplexity", "ollama_cloud"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
        )

    is_valid, message = user_key_manager.validate_key(provider, api_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid API key: {message}")

    try:
        key_field = f"{provider}_key"
        user_key_manager.update_keys(user.id, **{key_field: api_key})

        return {
            "status": "success",
            "message": f"{provider.title()} API key configured successfully",
            "provider": provider,
            "note": "Your key is stored securely and will be used for AI requests."
        }
    except Exception as e:
        logger.error(f"[BYOK] Failed to save key: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API key")


@router.delete("/providers/byok/{provider}")
async def delete_provider_key(
    provider: str,
    user: User = Depends(require_authentication)
):
    """Delete a user's API key for a specific provider"""
    if not BYOK_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "BYOK module not available", status_code=503)

    user_key_manager.delete_keys(user.id, provider=provider)

    return {
        "status": "success",
        "message": f"{provider.title()} API key removed"
    }


@router.get("/providers/byok/costs")
async def get_provider_costs():
    """Get cost information for all providers (public endpoint)"""
    if not BYOK_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "BYOK module not available", status_code=503)

    costs = {}
    for provider, info in PROVIDER_COSTS.items():
        costs[provider] = {
            "name": info["name"],
            "input_cost_per_1k": info["input"],
            "output_cost_per_1k": info["output"],
            "is_free": info["input"] == 0 and info["output"] == 0,
        }
    return {
        "providers": costs,
        "note": "Free tier uses Ollama (local). Add your own keys for premium providers.",
        "cost_example": "A typical interview response (~500 tokens) costs $0.001-0.003 with most providers."
    }


@router.get("/providers/byok/test/{provider}")
async def test_provider_key(
    provider: str,
    user: User = Depends(require_authentication)
):
    """Test if a user's API key is working for a provider by making a real API call"""
    if not BYOK_AVAILABLE:
        return error_response(ErrorCode.MODULE_NOT_AVAILABLE, "BYOK module not available", status_code=503)

    key = user_key_manager.get_provider_key(user.id, provider)

    if not key:
        raise HTTPException(status_code=404, detail=f"No API key configured for {provider}")

    is_valid, message = user_key_manager.validate_key(provider, key)
    if not is_valid:
        log_audit_event("byok_test", user.username, "key_test_failed", resource=provider, details={"reason": message}, success=False)
        return {
            "status": "error",
            "provider": provider,
            "message": f"Key validation failed: {message}",
            "suggestion": "Please check your API key and try again."
        }

    import httpx
    test_result = {"status": "success", "provider": provider, "message": "API key format is valid"}

    try:
        if provider == "openai":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully", "models_available": len(resp.json().get("data", []))}
                elif resp.status_code == 401:
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key", "suggestion": "Check your OpenAI API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                )
                if resp.status_code in (200, 201):
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                elif resp.status_code == 401:
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}

        elif provider == "google":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={key}",
                )
                if resp.status_code == 200:
                    test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                elif resp.status_code in (400, 403):
                    test_result = {"status": "error", "provider": provider, "message": "Invalid API key"}
                else:
                    test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}

        elif provider in ("xai", "groq", "deepseek", "perplexity"):
            base_urls = {
                "xai": "https://api.x.ai/v1",
                "groq": "https://api.groq.com/openai/v1",
                "deepseek": "https://api.deepseek.com/v1",
                "perplexity": "https://api.perplexity.ai",
            }
            base_url = base_urls.get(provider, "")
            if base_url:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    if resp.status_code == 200:
                        test_result = {"status": "success", "provider": provider, "message": "API key verified successfully"}
                    elif resp.status_code == 401:
                        test_result = {"status": "error", "provider": provider, "message": "Invalid API key"}
                    else:
                        test_result = {"status": "warning", "provider": provider, "message": f"API returned status {resp.status_code}"}
            else:
                test_result = {"status": "success", "provider": provider, "message": "Key format is valid (provider test not implemented)"}

    except httpx.TimeoutException:
        test_result = {"status": "warning", "provider": provider, "message": "API test timed out", "note": "Key format is valid but could not verify connectivity"}
    except Exception as e:
        test_result = {"status": "warning", "provider": provider, "message": f"API test error: {str(e)}", "note": "Key format is valid but could not verify connectivity"}

    log_audit_event("byok_test", user.username, "key_tested", resource=provider, details=test_result, success=test_result.get("status") == "success")
    return test_result