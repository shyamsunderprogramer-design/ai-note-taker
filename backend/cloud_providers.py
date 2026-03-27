import os
import requests
from dotenv import load_dotenv

load_dotenv()


def build_prompt(user_input, mode="adaptive", style="concise", messages=None):
    """Build prompt for cloud providers"""
    if style == "concise":
        style_instruction = "Answer in 1-2 sentences only. Be direct."
    elif style == "detailed":
        style_instruction = "Answer in detail with clear explanations."
    elif style == "bulletpoint":
        style_instruction = "Use bullet points with asterisk (*). One bullet per line."
    else:
        style_instruction = "Answer concisely."

    # Build conversation history context
    history_block = ""
    if messages:
        history_lines = []
        for msg in messages:
            role_label = "You" if msg.get("role") == "user" else "AI"
            history_lines.append(f"{role_label}: {msg.get('text', '')}")
        history_block = "Conversation:\n" + "\n".join(history_lines) + "\n\n"

    return f"""Instructions:
- {style_instruction}
- Do not repeat the user's question
- Do not echo labels like You: or AI:
- If unclear, say: Please clarify

{history_block}User: {user_input}
AI:"""

# ==============================
# 🌐 API KEYS & CONFIGS
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

# ==============================
# 🤖 CLOUD PROVIDERS
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
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024
        }
    }

    if stream:
        url += "&alt=sse"

    response = requests.post(
        url,
        json=body,
        timeout=60
    )

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


def ask_gpt_stream(prompt, model="gpt-4o-mini", mode="adaptive", style="concise", messages=None):
    """OpenAI streaming"""
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_gpt(final_prompt, model=model, stream=True)
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            try:
                obj = json.loads(data)
                content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except:
                pass


def ask_claude_stream(prompt, model="claude-3-5-haiku-20241022", mode="adaptive", style="concise", messages=None):
    """Anthropic streaming"""
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
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
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            try:
                obj = json.loads(data)
                content = obj.get("delta", {}).get("text", "")
                if content:
                    yield content
            except:
                pass


def ask_gemini_stream(prompt, model="gemini-2.0-flash", mode="adaptive", style="concise", messages=None):
    """Google Gemini streaming"""
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
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            import json
            try:
                obj = json.loads(line[6:])
                content = obj.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if content:
                    yield content
            except:
                pass


def ask_grok_stream(prompt, model="grok-2-mini", mode="adaptive", style="concise", messages=None):
    """xAI Grok streaming"""
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_grok(final_prompt, model=model, stream=True)
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            try:
                obj = json.loads(data)
                content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except:
                pass


def ask_deepseek_stream(prompt, model="deepseek-chat", mode="adaptive", style="concise", messages=None):
    """DeepSeek streaming"""
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_deepseek(final_prompt, model=model, stream=True)
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            try:
                obj = json.loads(data)
                content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except:
                pass


def ask_groq_stream(prompt, model="llama-3.3-70b-versatile", mode="adaptive", style="concise", messages=None):
    """Groq streaming"""
    final_prompt = build_prompt(prompt, mode=mode, style=style, messages=messages)
    resp = ask_groq(final_prompt, model=model, stream=True)
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            try:
                obj = json.loads(data)
                content = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except:
                pass
