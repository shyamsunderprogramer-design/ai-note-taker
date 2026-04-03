import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("cloud_providers")


def build_prompt(user_input, mode="adaptive", style="concise", messages=None):
    """Build prompt for cloud providers"""
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
    return f"event: meta\ndata: {{\"type\":\"meta\",\"model\":\"{model}\",\"provider\":\"{provider}\"}}\n\n"

def _make_content(chunk):
    import json
    return f"event: chunk\ndata: {json.dumps({'type':'chunk','content':chunk})}\n\n"

def _make_done(ms):
    return f"event: done\ndata: {{\"type\":\"done\",\"ms\":{ms}}}\n\n"

def _make_error(msg):
    import json
    return f"event: error\ndata: {json.dumps({'type':'error','message':msg})}\n\n"


# ==============================
# API KEYS & CONFIGS
# ==============================

def get_openai_key():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("OpenAI API key not configured")
    return key

def get_anthropic_key():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("Anthropic API key not configured")
    return key

def get_google_key():
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        raise ValueError("Google API key not configured")
    return key

def get_xai_key():
    key = os.getenv("XAI_API_KEY", "").strip()
    if not key:
        raise ValueError("xAI API key not configured")
    return key

def get_deepseek_key():
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("DeepSeek API key not configured")
    return key

def get_groq_key():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError("Groq API key not configured")
    return key

def get_ollama_cloud_key():
    key = os.getenv("OLLAMA_CLOUD_API_KEY", "").strip()
    if not key:
        raise ValueError("Ollama Cloud API key not configured")
    return key

def get_perplexity_key():
    key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not key:
        raise ValueError("Perplexity API key not configured")
    return key


# ==============================
# OLLAMA CLOUD (ollama.com)
# ==============================

def ask_ollama_cloud(prompt, model="minimax-m2", stream=False, mode="adaptive", style="concise", messages=None):
    """Ollama Cloud - uses https://ollama.com/api/chat endpoint"""
    import time
    start = time.time()

    api_key = get_ollama_cloud_key()
    url = "https://ollama.com/api/chat"

    # Build conversation for chat endpoint
    chat_messages = []
    if messages:
        for msg in messages:
            chat_messages.append({"role": msg.get("role", "user"), "content": msg.get("text", "")})
    chat_messages.append({"role": "user", "content": prompt})

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
        response = requests.post(url, headers=headers, json=body, stream=stream, timeout=60)
        if response.status_code != 200:
            yield _make_error(f"Ollama Cloud error: HTTP {response.status_code}")
            return

        if stream:
            # Send meta first so frontend knows which model
            yield _make_meta(model, "ollama-cloud")
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    import json as _json
                    data = _json.loads(line.decode("utf-8"))
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content:
                            yield _make_content(content)
                    if data.get("done", False):
                        break
                except Exception:
                    pass
        else:
            data = response.json()
            yield _make_meta(model, "ollama-cloud")
            if "message" in data:
                yield _make_content(data["message"].get("content", ""))

    except Exception as e:
        yield _make_error(f"Ollama Cloud error: {str(e)}")

    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_ollama_cloud_stream(prompt, model="qwen2.5:1.5b", mode="adaptive", style="concise", messages=None):
    """Streaming version of Ollama Cloud"""
    yield from ask_ollama_cloud(prompt, model=model, stream=True, mode=mode, style=style, messages=messages)


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
    response = requests.post(
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
        "anthropic-dangerous-direct-browser-access": "true"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024
    }
    if stream:
        body["stream"] = True
    response = requests.post(
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
    response = requests.post(url, json=body, timeout=60)
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
    response = requests.post(
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
    response = requests.post(
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
    response = requests.post(
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
        logger.error("OpenAI streaming error: %s", e)
        yield _make_error(f"OpenAI error: {str(e)}")


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
            "anthropic-dangerous-direct-browser-access": "true"
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
            "stream": True
        }
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            stream=True,
            timeout=60
        )
        if resp.status_code != 200:
            raise Exception(f"Claude error: {resp.status_code} - {resp.text}")
        yield _make_meta(model, "anthropic")

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
                    content = obj.get("delta", {}).get("text", "")
                    if content:
                        yield _make_content(content)
                        chunk_count += 1
                except json.JSONDecodeError:
                    pass

        ms = int((time.time() - start) * 1000)
        logger.debug("Claude stream complete: %d chunks in %dms", chunk_count, ms)
        yield _make_done(ms)

    except Exception as e:
        logger.error("Claude streaming error: %s", e)
        yield _make_error(f"Claude error: {str(e)}")


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
    resp = requests.post(url, json=body, stream=True, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"Gemini error: {resp.status_code} - {resp.text}")
    yield _make_meta(model, "google")
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                import json
                try:
                    obj = json.loads(decoded[6:])
                    content = obj.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if content:
                        yield _make_content(content)
                except Exception:
                    pass
    except Exception as e:
        yield _make_error(str(e))
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_grok_stream(prompt, model="grok-2-mini", mode="adaptive", style="concise", messages=None):
    """xAI Grok streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_grok(final_prompt, model=model, stream=True)
    yield _make_meta(model, "xai")
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                import json
                try:
                    obj = json.loads(data)
                    content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield _make_content(content)
                except Exception:
                    pass
    except Exception as e:
        yield _make_error(str(e))
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_deepseek_stream(prompt, model="deepseek-chat", mode="adaptive", style="concise", messages=None):
    """DeepSeek streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_deepseek(final_prompt, model=model, stream=True)
    yield _make_meta(model, "deepseek")
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                import json
                try:
                    obj = json.loads(data)
                    content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield _make_content(content)
                except Exception:
                    pass
    except Exception as e:
        yield _make_error(str(e))
    ms = int((time.time() - start) * 1000)
    yield _make_done(ms)


def ask_groq_stream(prompt, model="llama-3.3-70b-versatile", mode="adaptive", style="concise", messages=None):
    """Groq streaming — yields SSE event strings"""
    import time
    start = time.time()
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_groq(final_prompt, model=model, stream=True)
    yield _make_meta(model, "groq")
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                import json
                try:
                    obj = json.loads(data)
                    content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield _make_content(content)
                except Exception:
                    pass
    except Exception as e:
        yield _make_error(str(e))
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
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=body,
        stream=stream,
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
    resp = ask_perplexity(final_prompt, model=model, stream=True)
    yield _make_meta(model, "perplexity")
    try:
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace")
            if decoded.startswith("data: "):
                data = decoded[6:]
                if data == "[DONE]":
                    break
                import json
                try:
                    obj = json.loads(data)
                    content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield _make_content(content)
                except Exception:
                    pass
    except Exception as e:
        yield _make_error(str(e))
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
