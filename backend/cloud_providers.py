import os
import requests
from dotenv import load_dotenv

from utils import clean_ai_output

load_dotenv()


def build_prompt(user_input, mode="adaptive", style="concise", messages=None):
    """Build prompt for cloud providers (same logic as ai_router but for cloud)"""
    if style == "concise":
        style_instruction = "Give a very short answer in 1-2 sentences only."
    elif style == "detailed":
        style_instruction = "Give a detailed explanation in paragraph form."
    elif style == "bulletpoint":
        style_instruction = "Respond using ONLY bullet points with asterisk (*) prefix, ONE bullet per line, NO numbered lists.\nFormat:\n* point one here\n* point two here\n* point three here\nEach line MUST start with exactly one asterisk (*) followed by a space, then the text. No numbers, no dashes, no other symbols."
    else:
        style_instruction = "Give a concise answer."

    # Build conversation history context
    history_block = ""
    if messages:
        history_lines = []
        for msg in messages:
            role_label = "You" if msg.get("role") == "user" else "AI"
            history_lines.append(f"{role_label}: {msg.get('text', '')}")
        history_block = "Conversation history:\n" + "\n".join(history_lines) + "\n\n"

    return f"""Answer the user's question directly.
{style_instruction}
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "summary":
        return f"""You are a meeting notes assistant. Read the conversation transcript below and produce a structured summary.

STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS (use the same markdown formatting):

# [Topic / Title from conversation]

## Overview
[Brief 1-2 sentence overview of what this conversation was about]

## Key Points
[3-5 bullet points of the most important things discussed]
* bullet one
* bullet two
* ...

## Next Steps / Action Items
[Any tasks, follow-ups, or action items mentioned]
* action item one
* action item two
* ...

## Details
[Additional important details, definitions, or context that came up]
- detail one
- detail two

Do not mention that you are an AI or that you received a transcript. Just produce the summary directly.
Conversation transcript:
{user_input}
"""

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
        raise Exception(f"Grok error: {response.status_code} - {response.text}")

    return response


def ask_gpt_stream(prompt, model="gpt-4o-mini", messages=None):
    """OpenAI streaming"""
    final_prompt = build_prompt(prompt, messages=messages)
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


def ask_claude_stream(prompt, model="claude-3-5-haiku-20241022", messages=None):
    """Anthropic streaming"""
    final_prompt = build_prompt(prompt, messages=messages)
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


def ask_gemini_stream(prompt, model="gemini-2.0-flash", messages=None):
    """Google Gemini streaming"""
    final_prompt = build_prompt(prompt, messages=messages)
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


def ask_grok_stream(prompt, model="grok-2-mini", messages=None):
    """xAI Grok streaming"""
    final_prompt = build_prompt(prompt, messages=messages)
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
