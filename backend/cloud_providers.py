import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

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
        raise Exception(f"xAI error: {response.status_code} - {response.text}")

    return response


# ==============================
# 🧹 CLEAN OUTPUT
# ==============================

def clean_ai_output(text):
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r"(?i)\b(user question|question|rules|rule|preface|example|examples|constraints|behavior|answer)\s*:\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()
