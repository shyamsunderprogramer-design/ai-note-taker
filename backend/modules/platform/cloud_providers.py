import json
import logging
import os

logger = logging.getLogger("cloud_providers")

# Use shared httpx client instead of requests to avoid blocking the event loop
from lib.http_client import sync_client

# ==============================
# SECURE API KEY FETCHER (P1 Privacy)
# Fetches encrypted keys from Electron secure storage
# ==============================
_key_cache = {}

# Shared secret for authenticating with the Electron API key server.
# Passed via KEY_SERVER_SECRET env var from Electron on startup.
_KEY_SERVER_SECRET = os.getenv("KEY_SERVER_SECRET", "")

def fetch_key_from_secure_server(provider):
    """Fetch API key from Electron's secure key server (localhost:18000)
    Requires shared secret for authentication."""
    if provider in _key_cache:
        return _key_cache[provider]
    try:
        headers = {}
        if _KEY_SERVER_SECRET:
            headers["X-Key-Server-Secret"] = _KEY_SERVER_SECRET
        response = sync_client.post(
            "http://127.0.0.1:18000/get-key",
            json={"provider": provider},
            headers=headers,
            timeout=2,
            skip_ssrf_check=True,  # internal key server, not user-supplied
        )
        if response.status_code == 403:
            logger.warning(f"[SecureKey] Authentication rejected for {provider}")
            return None
        if response.status_code == 200:
            data = response.json()
            key = data.get("apiKey")
            if key:
                _key_cache[provider] = key
                return key
    except Exception as e:
        logger.debug("[SecureKey] Could not fetch from secure server: %s", str(e))
    return None

def get_key_secure(provider, env_var):
    """Get API key: first try secure server, fallback to env"""
    # Try secure server first
    key = fetch_key_from_secure_server(provider)
    if key:
        return key
    # Fallback to environment variable
    key = os.getenv(env_var, "").strip()
    return key


# Use full build_prompt from ai_router (with RAG + all mode variants) when available
try:
    from ai_router import build_prompt  # noqa: F401
except ImportError:
    # Fallback: minimal version without RAG support
    def build_prompt(user_input, mode="adaptive", style="concise", messages=None, include_rag=False):
        """Build prompt for cloud providers (fallback without RAG)"""
        if style == "concise":
            style_instruction = "2 sentences max."
        elif style == "detailed":
            style_instruction = "2-3 paragraphs. Code if relevant."
        elif style == "bulletpoint":
            style_instruction = "4 bullets max."
        else:
            style_instruction = "Short."

        # Build conversation history context
        history_block = ""
        if messages:
            history_lines = []
            for msg in messages:
                role_label = "You" if msg.get("role") == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg.get('text', '')}")
            history_block = "Chat history:\n" + "\n".join(history_lines) + "\n\n"

        if mode == "race":
            # Minimal prompt for sub-second first-byte
            return f"""{history_block}Q: {user_input}
A:"""

        return f"""Slack message between two senior engineers.

FORBIDDEN:
- No headers/titles (=== or #)
- No tables
- No bullet lists
- No numbered lists
- No emojis
- No code blocks unless asked
- No "Here's" or "Sure" intros

Write like a text message. Plain paragraphs only.

{history_block}Question: {user_input}
Answer:"""

# ==============================
# META STREAM FUNCTIONS
# Yield dicts: {"type": "meta", "model": "...", "provider": "..."}
#             {"type": "content", "content": "..."}
#             {"type": "done", "ms": 1234}
#             {"type": "error", "message": "..."}
# ==============================

def _make_meta(model, provider):
    from lib.sse_helpers import make_meta
    return make_meta(model, provider)

def _make_content(chunk):
    from lib.sse_helpers import make_content
    return make_content(chunk)

def _make_done(ms):
    from lib.sse_helpers import make_done
    return make_done(ms)

def _make_error(msg):
    from lib.sse_helpers import make_error
    return make_error(msg)


# ==============================
# API KEYS & CONFIGS (BYOK)
# ==============================

def get_openai_key(user_id: str = None):
    """Get OpenAI key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "openai")
        if key:
            return key
    # Fallback to environment
    key = get_key_secure("openai", "OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API key not configured. Add your key in Settings.")
    return key

def get_anthropic_key(user_id: str = None):
    """Get Anthropic key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "anthropic")
        if key:
            return key
    key = get_key_secure("anthropic", "ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("Anthropic API key not configured. Add your key in Settings.")
    return key

def get_google_key(user_id: str = None):
    """Get Google key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "google")
        if key:
            return key
    key = get_key_secure("google", "GOOGLE_API_KEY")
    if not key:
        raise ValueError("Google API key not configured. Add your key in Settings.")
    return key

def get_xai_key(user_id: str = None):
    """Get xAI key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "xai")
        if key:
            return key
    key = get_key_secure("xai", "XAI_API_KEY")
    if not key:
        raise ValueError("xAI API key not configured. Add your key in Settings.")
    return key

def get_deepseek_key(user_id: str = None):
    """Get DeepSeek key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "deepseek")
        if key:
            return key
    key = get_key_secure("deepseek", "DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DeepSeek API key not configured. Add your key in Settings.")
    return key

def get_groq_key(user_id: str = None):
    """Get Groq key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "groq")
        if key:
            return key
    key = get_key_secure("groq", "GROQ_API_KEY")
    if not key:
        raise ValueError("Groq API key not configured. Add your key in Settings.")
    return key

def get_ollama_cloud_key(user_id: str = None):
    """Get Ollama Cloud key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "ollama_cloud")
        if key:
            return key
    key = get_key_secure("ollama-cloud", "OLLAMA_CLOUD_API_KEY")
    if not key:
        raise ValueError("Ollama Cloud API key not configured. Add your key in Settings.")
    return key

def get_perplexity_key(user_id: str = None):
    """Get Perplexity key - first try user's key, then env"""
    if user_id:
        from user_api_keys import get_user_api_key
        key = get_user_api_key(user_id, "perplexity")
        if key:
            return key
    key = get_key_secure("perplexity", "PERPLEXITY_API_KEY")
    if not key:
        raise ValueError("Perplexity API key not configured. Add your key in Settings.")
    return key


# ==============================
# OLLAMA CLOUD (ollama.com)
# ==============================

def ask_ollama_cloud(prompt, model="minimax-m2", stream=False, mode="adaptive", style="concise", messages=None, image_b64=None):
    """Ollama Cloud - uses https://ollama.com/api/chat endpoint.
    Supports vision models (gemma3, qwen3-vl, etc.) via image_b64 param."""
    import time
    start = time.time()

    api_key = get_ollama_cloud_key()
    url = "https://ollama.com/api/chat"

    # Build conversation for chat endpoint
    chat_messages = []
    if messages:
        for msg in messages:
            chat_messages.append({"role": msg.get("role", "user"), "content": msg.get("text", "")})

    # Build user message — with image for vision models
    user_msg = {"role": "user", "content": prompt}
    if image_b64:
        user_msg["images"] = [image_b64]
    chat_messages.append(user_msg)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "messages": chat_messages,
        "stream": stream
    }

    try:
        if stream:
            with sync_client.stream("POST", url, headers=headers, json=body, timeout=90) as response:
                if response.status_code == 429:
                    yield _make_error(f"Ollama Cloud rate limited (429). Try again in a moment.")
                    return
                if response.status_code != 200:
                    yield _make_error(f"Ollama Cloud error: HTTP {response.status_code}")
                    return
                yield _make_meta(model, "ollama-cloud")
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield _make_content(content)
                        if data.get("done", False):
                            break
                    except Exception:
                        pass  # nosec B110
        else:
            response = sync_client.post(url, headers=headers, json=body, timeout=90)
            if response.status_code == 429:
                yield _make_error(f"Ollama Cloud rate limited (429). Try again in a moment.")
                return
            if response.status_code != 200:
                yield _make_error(f"Ollama Cloud error: HTTP {response.status_code}")
                return
            data = response.json()
            yield _make_meta(model, "ollama-cloud")
            if "message" in data:
                yield _make_content(data["message"].get("content", ""))

    except Exception as e:
        yield _make_error("Ollama Cloud error: An internal error occurred")

    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_ollama_cloud_stream(prompt, model="qwen2.5:1.5b", mode="adaptive", style="concise", messages=None, image_b64=None):
    """Streaming version of Ollama Cloud — supports vision via image_b64."""
    yield from ask_ollama_cloud(prompt, model=model, stream=True, mode=mode, style=style, messages=messages, image_b64=image_b64)


# ==============================
# BASE NON-STREAMING
# ==============================

def ask_gpt(prompt, model="gpt-4o-mini", stream=False):
    """OpenAI ChatGPT"""
    api_key = get_openai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=body,
        stream=stream,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"OpenAI error: {response.status_code} - {response.text}")
    return response


def ask_claude(prompt, model="claude-3-5-haiku-20241002", stream=False):
    """Anthropic Claude"""
    api_key = get_anthropic_key()
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=body,
        stream=stream,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"Anthropic error: {response.status_code} - {response.text}")
    return response


def ask_gemini(prompt, model="gemini-2.0-flash", stream=False):
    """Google Gemini"""
    api_key = get_google_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
    }
    if stream:
        url += "&alt=sse"
    response = sync_client.post(url, json=body, timeout=60)
    if response.status_code != 200:
        raise Exception(f"Gemini error: {response.status_code} - {response.text}")
    return response


def ask_grok(prompt, model="grok-2-mini", stream=False):
    """xAI Grok"""
    api_key = get_xai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.x.ai/v1/chat/completions",
        headers=headers,
        json=body,
        stream=stream,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"Grok error: {response.status_code} - {response.text}")
    return response


def ask_deepseek(prompt, model="deepseek-chat", stream=False):
    """DeepSeek"""
    api_key = get_deepseek_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=body,
        stream=stream,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"DeepSeek error: {response.status_code} - {response.text}")
    return response


def ask_groq(prompt, model="llama-3.3-70b-versatile", stream=False):
    """Groq"""
    api_key = get_groq_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=body,
        stream=stream,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"Groq error: {response.status_code} - {response.text}")
    return response


# ==============================
# STREAMING — SSE event format
# ==============================

def ask_gpt_stream(prompt, model="gpt-4o-mini", mode="adaptive", style="concise", messages=None):
    """OpenAI streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    try:
        resp = ask_gpt(final_prompt, model=model, stream=True)
        yield _make_meta(model, "openai")

        chunk_count = 0
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield _make_content(content)
                        chunk_count += 1
                except json.JSONDecodeError:
                    pass

        ms = int((time.time() - start) * 1000)
        logger.debug("OpenAI stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except Exception as e:
        logger.error("OpenAI streaming error: %s", str(e))
        yield _make_error("OpenAI error: An internal error occurred")


def ask_claude_stream(prompt, model="claude-3-5-haiku-20241022", mode="adaptive", style="concise", messages=None):
    """Anthropic streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    try:
        api_key = get_anthropic_key()
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
            "stream": True
        }
        with sync_client.stream("POST", "https://api.anthropic.com/v1/messages",
                                headers=headers, json=body, timeout=60) as resp:
            if resp.status_code != 200:
                raise Exception(f"Claude error: {resp.status_code} - {resp.text}")
            yield _make_meta(model, "anthropic")

            chunk_count = 0
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("delta", {}).get("text", "")
                        if content:
                            yield _make_content(content)
                            chunk_count += 1
                    except json.JSONDecodeError:
                        pass  # nosec B110

        ms = int((time.time() - start) * 1000)
        logger.debug("Claude stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except Exception as e:
        logger.error("Claude streaming error: %s", str(e))
        yield _make_error("Claude error: An internal error occurred")


def ask_gemini_stream(prompt, model="gemini-2.0-flash", mode="adaptive", style="concise", messages=None):
    """Google Gemini streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    api_key = get_google_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse"
    body = {
        "contents": [{"parts": [{"text": final_prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
    }
    with sync_client.stream("POST", url, json=body, timeout=60) as resp:
        if resp.status_code != 200:
            raise Exception(f"Gemini error: {resp.status_code} - {resp.text}")
        yield _make_meta(model, "google")
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line
                if decoded.startswith("data: "):
                    try:
                        obj = json.loads(decoded[6:])
                        content = obj.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110
        except Exception as e:
            yield _make_error("An internal error occurred")
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_grok_stream(prompt, model="grok-2-mini", mode="adaptive", style="concise", messages=None):
    """xAI Grok streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    api_key = get_xai_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3,
        "stream": True
    }
    yield _make_meta(model, "xai")
    try:
        with sync_client.stream("POST", "https://api.x.ai/v1/chat/completions",
                                headers=headers, json=body, timeout=60) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110
    except Exception as e:
        yield _make_error("An internal error occurred")
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_deepseek_stream(prompt, model="deepseek-chat", mode="adaptive", style="concise", messages=None):
    """DeepSeek streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    api_key = get_deepseek_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3,
        "stream": True
    }
    yield _make_meta(model, "deepseek")
    try:
        with sync_client.stream("POST", "https://api.deepseek.com/chat/completions",
                                headers=headers, json=body, timeout=60) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110
    except Exception as e:
        yield _make_error("An internal error occurred")
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_groq_stream(prompt, model="llama-3.3-70b-versatile", mode="adaptive", style="concise", messages=None):
    """Groq streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    api_key = get_groq_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3,
        "stream": True
    }
    yield _make_meta(model, "groq")
    try:
        with sync_client.stream("POST", "https://api.groq.com/openai/v1/chat/completions",
                                headers=headers, json=body, timeout=60) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110
    except Exception as e:
        yield _make_error("An internal error occurred")
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


# ==============================
# PERPLEXITY
# ==============================

def ask_perplexity(prompt, model="sonar", stream=False):
    """Perplexity AI — uses OpenAI-compatible endpoint"""
    api_key = get_perplexity_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    if stream:
        body["stream"] = True
    response = sync_client.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=body,
        timeout=60
    )
    if response.status_code != 200:
        raise Exception(f"Perplexity error: {response.status_code} - {response.text}")
    return response


def ask_perplexity_stream(prompt, model="sonar", mode="adaptive", style="concise", messages=None):
    """Perplexity streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    api_key = get_perplexity_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3,
        "stream": True
    }
    yield _make_meta(model, "perplexity")
    try:
        with sync_client.stream("POST", "https://api.perplexity.ai/chat/completions",
                                headers=headers, json=body, timeout=60) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110
    except Exception as e:
        yield _make_error("An internal error occurred")
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


# ==============================
# MODEL MAP — shared with ai_router
# ==============================
PROVIDER_MODEL_MAP = {
    # OpenAI
    "openai-gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "openai-gpt-4o": ("openai", "gpt-4o"),
    "openai-gpt-4-turbo": ("openai", "gpt-4-turbo"),
    "openai-o1-mini": ("openai", "o1-mini"),
    "openai-o3-mini": ("openai", "o3-mini"),
    "openai-gpt-3.5-turbo": ("openai", "gpt-3.5-turbo"),
    # Anthropic
    "anthropic-claude-3-5-haiku": ("anthropic", "claude-3-5-haiku-20241022"),
    "anthropic-claude-3-5-sonnet": ("anthropic", "claude-3-5-sonnet-20241022"),
    "anthropic-claude-sonnet-4-20250514": ("anthropic", "claude-sonnet-4-20250514"),
    "anthropic-claude-opus-4-20250514": ("anthropic", "claude-opus-4-20250514"),
    # Google
    "google-gemini-2-0-flash": ("google", "gemini-2.0-flash"),
    "google-gemini-2-0-flash-exp": ("google", "gemini-2.0-flash-exp"),
    "google-gemini-1-5-flash": ("google", "gemini-1.5-flash"),
    "google-gemini-1-5-pro": ("google", "gemini-1.5-pro"),
    "google-gemini-pro": ("google", "gemini-pro"),
    # xAI
    "xai-grok-2-mini": ("xai", "grok-2-mini"),
    "xai-grok-2": ("xai", "grok-2"),
    "xai-grok-beta": ("xai", "grok-beta"),
    # DeepSeek
    "deepseek-deepseek-chat": ("deepseek", "deepseek-chat"),
    "deepseek-deepseek-coder": ("deepseek", "deepseek-coder"),
    "deepseek-deepseek-math": ("deepseek", "deepseek-math"),
    # Groq
    "groq-llama-3-3-70b": ("groq", "llama-3.3-70b-versatile"),
    "groq-llama-3-1-8b": ("groq", "llama-3.1-8b-instant"),
    "groq-llama-3-2-1b": ("groq", "llama-3.2-1b-preview"),
    "groq-llama-3-2-3b": ("groq", "llama-3.2-3b-preview"),
    "groq-mixtral-8x7b": ("groq", "mixtral-8x7b-32768"),
    "groq-qwen-2-5-72b": ("groq", "qwen-2.5-72b-instruct"),
    # Ollama Cloud
    "ollama-cloud": ("ollama-cloud", "minimax-m2"),
    # Perplexity
    "perplexity-sonar": ("perplexity", "sonar"),
    "perplexity-sonar-pro": ("perplexity", "sonar-pro"),
    "perplexity-sonar-reasoning": ("perplexity", "sonar-reasoning"),
    "perplexity-sonar-reasoning-plus": ("perplexity", "sonar-reasoning-plus"),
}

MODEL_DISPLAY_NAMES = {
    # OpenAI
    "openai-gpt-4o-mini": "GPT-4o Mini",
    "openai-gpt-4o": "GPT-4o",
    "openai-gpt-4-turbo": "GPT-4 Turbo",
    "openai-o1-mini": "O1 Mini",
    "openai-o3-mini": "O3 Mini",
    "openai-gpt-3.5-turbo": "GPT-3.5 Turbo",
    # Anthropic
    "anthropic-claude-3-5-haiku": "Claude 3.5 Haiku",
    "anthropic-claude-3-5-sonnet": "Claude 3.5 Sonnet",
    "anthropic-claude-sonnet-4-20250514": "Claude Sonnet 4",
    "anthropic-claude-opus-4-20250514": "Claude Opus 4",
    # Google
    "google-gemini-2-0-flash": "Gemini 2.0 Flash",
    "google-gemini-2-0-flash-exp": "Gemini 2.0 Flash Exp",
    "google-gemini-1-5-flash": "Gemini 1.5 Flash",
    "google-gemini-1-5-pro": "Gemini 1.5 Pro",
    "google-gemini-pro": "Gemini Pro",
    # xAI
    "xai-grok-2-mini": "Grok 2 Mini",
    "xai-grok-2": "Grok 2",
    "xai-grok-beta": "Grok Beta",
    # DeepSeek
    "deepseek-deepseek-chat": "DeepSeek Chat",
    "deepseek-deepseek-coder": "DeepSeek Coder",
    "deepseek-deepseek-math": "DeepSeek Math",
    # Groq
    "groq-llama-3-3-70b": "Llama 3.3 70B",
    "groq-llama-3-1-8b": "Llama 3.1 8B",
    "groq-llama-3-2-1b": "Llama 3.2 1B",
    "groq-llama-3-2-3b": "Llama 3.2 3B",
    "groq-mixtral-8x7b": "Mixtral 8x7B",
    "groq-qwen-2-5-72b": "Qwen 2.5 72B",
    "ollama": "Ollama",
    "ollama-cloud": "Ollama Cloud",
    # Perplexity
    "perplexity-sonar": "Sonar",
    "perplexity-sonar-pro": "Sonar Pro",
    "perplexity-sonar-reasoning": "Sonar Reasoning",
    "perplexity-sonar-reasoning-plus": "Sonar Reasoning+",
}


def get_stream_fn(provider_key):
    """Return the appropriate stream function for a provider key"""
    resolved = PROVIDER_MODEL_MAP.get(provider_key, ("openai", "gpt-4o-mini"))
    provider_name = resolved[0]
    if provider_name == "openai":
        return ask_gpt_stream
    elif provider_name == "anthropic":
        return ask_claude_stream
    elif provider_name == "google":
        return ask_gemini_stream
    elif provider_name == "xai":
        return ask_grok_stream
    elif provider_name == "deepseek":
        return ask_deepseek_stream
    elif provider_name == "groq":
        return ask_groq_stream
    elif provider_name == "ollama-cloud":
        return ask_ollama_cloud_stream
    elif provider_name == "perplexity":
        return ask_perplexity_stream
    return None


# ==============================
# VISION STREAMING — Cloud providers with image support
# ==============================

# Vision-capable models per provider
VISION_PROVIDER_MAP = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-haiku-20241022",
    "google": "gemini-2.0-flash",
    "groq": "llama-3.2-90b-vision-preview",
    "ollama-cloud": "gemma3:cloud",  # Free vision-capable cloud model
}


def ask_gpt_vision_stream(prompt, image_b64=None, model="gpt-4o", mode="race", style="concise", messages=None):
    """OpenAI vision streaming (GPT-4o) — yields SSE event strings."""
    import time
    start = time.time()
    try:
        api_key = get_openai_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Build message content with image
        content_parts = [{"type": "text", "text": prompt}]
        if image_b64:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "low"}
            })

        body = {
            "model": model,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": 0.3,
            "max_tokens": 512,
            "stream": True
        }
        with sync_client.stream("POST", "https://api.openai.com/v1/chat/completions",
                                headers=headers, json=body, timeout=30) as resp:
            if resp.status_code == 429:
                yield _make_error(f"OpenAI rate limited (429). Try again in a moment or select a different model.")
                return
            if resp.status_code != 200:
                err = resp.text
                yield _make_error(f"OpenAI vision error: HTTP {resp.status_code}")
                return
            yield _make_meta(model, "openai")
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8", errors="replace")
                if decoded.startswith("data: "):
                    data = decoded[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield _make_content(content)
                    except json.JSONDecodeError:
                        pass  # nosec B110

        ms = int((time.time() - start) * 1000)
        yield _make_done(ms)

    except ValueError as e:
        yield _make_error(f"OpenAI key not configured: {e}")
    except Exception as e:
        logger.error("OpenAI vision streaming error: %s", str(e))
        yield _make_error("OpenAI vision error: An internal error occurred")


def ask_claude_vision_stream(prompt, image_b64=None, model="claude-3-5-haiku-20241022", mode="race", style="concise", messages=None):
    """Anthropic Claude vision streaming — yields SSE event strings."""
    import time
    start = time.time()
    try:
        api_key = get_anthropic_key()
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        # Build message content with image
        content_parts = []
        if image_b64:
            content_parts.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": image_b64}
            })
        content_parts.append({"type": "text", "text": prompt})

        body = {
            "model": model,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": 0.3,
            "max_tokens": 512,
            "stream": True
        }
        with sync_client.stream("POST", "https://api.anthropic.com/v1/messages",
                                headers=headers, json=body, timeout=30) as resp:
            if resp.status_code == 429:
                yield _make_error(f"Claude rate limited (429). Try again in a moment or select a different model.")
                return
            if resp.status_code != 200:
                yield _make_error(f"Claude vision error: HTTP {resp.status_code}")
                return
            yield _make_meta(model, "anthropic")
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    try:
                        obj = json.loads(data)
                        if obj.get("type") == "content_block_delta":
                            text = obj.get("delta", {}).get("text", "")
                            if text:
                                yield _make_content(text)
                    except json.JSONDecodeError:
                        pass  # nosec B110

        ms = int((time.time() - start) * 1000)
        yield _make_done(ms)

    except ValueError as e:
        yield _make_error(f"Anthropic key not configured: {e}")
    except Exception as e:
        logger.error("Claude vision streaming error: %s", str(e))
        yield _make_error("Claude vision error: An internal error occurred")


def ask_gemini_vision_stream(prompt, image_b64=None, model="gemini-2.0-flash", mode="race", style="concise", messages=None):
    """Google Gemini vision streaming — yields SSE event strings."""
    import time
    start = time.time()
    try:
        api_key = get_google_key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse"
        # Build parts with image
        parts = []
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/png", "data": image_b64}})
        parts.append({"text": prompt})

        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512}
        }
        with sync_client.stream("POST", url, json=body, timeout=30) as resp:
            if resp.status_code == 429:
                yield _make_error(f"Gemini rate limited (429). Try again in a moment or select a different model.")
                return
            if resp.status_code != 200:
                yield _make_error(f"Gemini vision error: HTTP {resp.status_code}")
                return
            yield _make_meta(model, "google")
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line
                if decoded.startswith("data: "):
                    try:
                        obj = json.loads(decoded[6:])
                        content = obj.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110

        ms = int((time.time() - start) * 1000)
        yield _make_done(ms)

    except ValueError as e:
        yield _make_error(f"Google key not configured: {e}")
    except Exception as e:
        logger.error("Gemini vision streaming error: %s", str(e))
        yield _make_error("Gemini vision error: An internal error occurred")


def ask_groq_vision_stream(prompt, image_b64=None, model="llama-3.2-90b-vision-preview", mode="race", style="concise", messages=None):
    """Groq vision streaming (llama-3.2-90b-vision) — yields SSE event strings."""
    import time
    start = time.time()
    try:
        api_key = get_groq_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Build message content with image (OpenAI-compatible format)
        content_parts = [{"type": "text", "text": prompt}]
        if image_b64:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"}
            })

        body = {
            "model": model,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": 0.3,
            "max_tokens": 512,
            "stream": True
        }
        with sync_client.stream("POST", "https://api.groq.com/openai/v1/chat/completions",
                                headers=headers, json=body, timeout=30) as resp:
            if resp.status_code == 429:
                yield _make_error(f"Groq rate limited (429). Try again in a moment or select a different model.")
                return
            if resp.status_code != 200:
                yield _make_error(f"Groq vision error: HTTP {resp.status_code}")
                return
            yield _make_meta(model, "groq")
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield _make_content(content)
                    except Exception:
                        pass  # nosec B110

        ms = int((time.time() - start) * 1000)
        yield _make_done(ms)

    except ValueError as e:
        yield _make_error(f"Groq key not configured: {e}")
    except Exception as e:
        logger.error("Groq vision streaming error: %s", str(e))
        yield _make_error("Groq vision error: An internal error occurred")


def get_vision_stream_fn(provider):
    """Return the vision stream function for a provider name."""
    if provider == "openai":
        return ask_gpt_vision_stream
    elif provider == "anthropic":
        return ask_claude_vision_stream
    elif provider == "google":
        return ask_gemini_vision_stream
    elif provider == "groq":
        return ask_groq_vision_stream
    elif provider == "ollama-cloud":
        return ask_ollama_cloud_vision_stream
    return None


# Ollama Cloud vision-capable models (free, no paid API key needed)
OLLAMA_CLOUD_VISION_MODELS = {
    "gemma3:cloud": "Gemma 3 (Vision)",
    "gemma4:cloud": "Gemma 4 (Vision)",
    "qwen3-vl:235b-cloud": "Qwen3-VL 235B",
}


def ask_ollama_cloud_vision_stream(prompt, image_b64=None, model="gemma3:cloud", mode="race", style="concise", messages=None):
    """Ollama Cloud vision streaming — for free vision-capable cloud models.
    Uses the Ollama /api/chat endpoint with images array."""
    import time
    start = time.time()
    try:
        api_key = get_ollama_cloud_key()
        if not api_key:
            yield _make_error("Ollama Cloud key not configured")
            return

        url = "https://ollama.com/api/chat"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Build user message with image
        user_msg = {"role": "user", "content": prompt}
        if image_b64:
            user_msg["images"] = [image_b64]

        chat_messages = []
        if messages:
            for msg in messages:
                chat_messages.append({"role": msg.get("role", "user"), "content": msg.get("text", "")})
        chat_messages.append(user_msg)

        body = {
            "model": model,
            "messages": chat_messages,
            "stream": True
        }

        with sync_client.stream("POST", url, headers=headers, json=body, timeout=90) as response:
            if response.status_code == 429:
                yield _make_error(f"Ollama Cloud rate limited (429). Try again in a moment.")
                return
            if response.status_code != 200:
                yield _make_error(f"Ollama Cloud vision error: HTTP {response.status_code}")
                return
            yield _make_meta(model, "ollama-cloud")
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content:
                            yield _make_content(content)
                    if data.get("done", False):
                        break
                except Exception:
                    pass  # nosec B110

    except Exception as e:
        logger.error("Ollama Cloud vision streaming error: %s", str(e))
        yield _make_error("Ollama Cloud vision error: An internal error occurred")

    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)
