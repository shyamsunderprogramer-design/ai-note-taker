import json
import logging
import re

import requests

from config import AI_TEMPERATURE, AI_TIMEOUT, OLLAMA_URL, get_ai_model
from utils import clean_ai_output

logger = logging.getLogger("ai_router")

AI_MODE = "adaptive"

CODE_KEYWORDS = (
    "code", "python", "javascript", "typescript", "java", "c#", "golang",
    "go ", "sql", "regex", "function", "class", "bug", "debug", "refactor",
    "api", "json", "yaml", "dockerfile", "algorithm", "stack trace", "exception"
)
TECHNICAL_KEYWORDS = (
    "docker", "kubernetes", "pod", "pods", "container", "ci/cd", "devops", "aws",
    "azure", "gcp", "microservice", "architecture", "database", "ingress",
    "helm", "deployment", "load balancer"
)
INTERVIEW_HINTS = ("interview", "technical round", "tech round", "hiring manager")


def resolve_mode(user_input, requested_mode="auto"):
    if requested_mode and requested_mode != "auto":
        return requested_mode

    prompt = (user_input or "").strip().lower()
    word_count = len(prompt.split())

    if any(keyword in prompt for keyword in CODE_KEYWORDS):
        if word_count >= 18:
            return "code"
        return "adaptive"

    if word_count >= 30 or any(keyword in prompt for keyword in ("compare", "tradeoff", "tradeoffs", "trade-off", "design", "deeply")):
        return "reasoning"

    if any(keyword in prompt for keyword in TECHNICAL_KEYWORDS):
        if any(keyword in prompt for keyword in INTERVIEW_HINTS) or word_count >= 12:
            return "interview"
        return "adaptive"
        

    if word_count <= 8:
        return "fast"

    return "adaptive"


def get_model_candidates(user_input, requested_mode="auto"):
    resolved_mode = resolve_mode(user_input, requested_mode)

    fallback_map = {
        "fast": ["fast", "adaptive", "universal"],
        "adaptive": ["adaptive", "universal", "fast"],
        "universal": ["universal", "adaptive", "reasoning"],
        "interview": ["interview", "universal", "reasoning"],
        "reasoning": ["universal", "reasoning", "adaptive"],
        "code": ["adaptive", "code", "reasoning"],
        "cloud": ["cloud", "reasoning", "adaptive"],
        "summary": ["summary", "universal", "adaptive"],
    }

    seen = set()
    candidates = []

    for mode in fallback_map.get(resolved_mode, [resolved_mode, "adaptive", "fast"]):
        model = get_ai_model(mode)
        if model in seen:
            continue
        seen.add(model)
        candidates.append((mode, model))

    return resolved_mode, candidates


def build_prompt(user_input, mode="adaptive", style="concise", messages=None):
    # Style-specific instructions
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

    base = f"""Answer the user's question directly.
{style_instruction}
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "code":
        return f"""Answer the user's coding question directly.
{style_instruction}
Prefer the shortest correct explanation or fix.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "reasoning":
        return f"""Answer the user's question directly.
{style_instruction}
Prefer the clearest correct explanation.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "fast":
        return f"""Answer the user's question directly.
{style_instruction}
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "cloud":
        return f"""Answer the user's question directly.
{style_instruction}
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "interview":
        return f"""Answer only the user's question.
{style_instruction}
Keep it technical.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

{history_block}User question: {user_input}
"""

    if mode == "universal":
        return f"""Answer the user's question clearly and naturally.
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

    return base


def ask_ollama(prompt, mode=AI_MODE, model_name=None, style="concise"):
    try:
        final_prompt = build_prompt(prompt, mode, style)

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name or get_ai_model(mode),
                "prompt": final_prompt,
                "stream": False,
                "options": {
                    "temperature": AI_TEMPERATURE
                }
            },
            timeout=AI_TIMEOUT
        )

        if response.status_code != 200:
            return "AI service unavailable."

        data = response.json()
        return data.get("response", "").strip()

    except Exception as e:
        logger.error("ask_ollama error: %s", e)
        return "AI error"


def ask_ollama_stream(prompt, mode=AI_MODE, model_name=None, style="concise", messages=None):
    try:
        logger.info("Streaming (%s mode, %s style): %s", mode, style, prompt)

        final_prompt = build_prompt(prompt, mode, style, messages)

        # Use num_predict to limit response length for faster streaming
        num_predict = 80 if style == "concise" else (300 if style == "detailed" else 200)
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name or get_ai_model(mode),
                "prompt": final_prompt,
                "stream": True,
                "options": {
                    "temperature": AI_TEMPERATURE,
                    "num_predict": num_predict
                }
            },
            stream=True,
            timeout=AI_TIMEOUT
        )

        if response.status_code != 200:
            yield "AI service unavailable."
            return

        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))

                if "response" in data:
                    chunk = data["response"]
                    logger.debug("stream chunk: %s", chunk)
                    yield chunk

                if data.get("done", False):
                    break

            except Exception as e:
                logger.warning("Stream parse error: %s", e)

        logger.debug("Stream complete")

    except requests.exceptions.Timeout:
        yield "AI response timeout. Try again."

    except Exception as e:
        logger.error("Streaming error: %s", e)
        yield "AI error occurred."


def route_ai(prompt, mode="adaptive", style="concise"):
    resolved_mode, candidates = get_model_candidates(prompt, mode)
    last_error = None

    for candidate_mode, model_name in candidates:
        try:
            response = ask_ollama(prompt, mode=candidate_mode, model_name=model_name, style=style)
            cleaned = clean_ai_output(response)

            if cleaned and cleaned not in {"AI error", "AI service unavailable."}:
                return {
                    "response": cleaned,
                    "mode": candidate_mode,
                    "model": model_name
                }

            last_error = response
        except Exception as e:
            last_error = str(e)
            logger.error("route_ai error: %s", e)

    return {
        "response": clean_ai_output(last_error or "AI error"),
        "mode": resolved_mode,
        "model": candidates[0][1] if candidates else get_ai_model("adaptive")
    }


def route_ai_stream(prompt, mode="adaptive", style="concise", provider="ollama", messages=None):
    if provider == "cloud":
        # Use cloud provider for streaming
        try:
            from cloud_providers import (
                ask_gpt_stream, ask_claude_stream, ask_gemini_stream,
                ask_grok_stream, ask_deepseek_stream, ask_groq_stream,
                build_prompt as cloud_build_prompt,
                clean_ai_output as cloud_clean
            )
            final_prompt = cloud_build_prompt(prompt, mode or "adaptive", style, messages)
            model_map = {
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
            }
            resolved = model_map.get(mode, ("openai", "gpt-4o-mini"))
            provider_name, model_name = resolved
            if provider_name == "openai":
                for chunk in ask_gpt_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            elif provider_name == "anthropic":
                for chunk in ask_claude_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            elif provider_name == "google":
                for chunk in ask_gemini_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            elif provider_name == "xai":
                for chunk in ask_grok_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            elif provider_name == "deepseek":
                for chunk in ask_deepseek_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            elif provider_name == "groq":
                for chunk in ask_groq_stream(final_prompt, model=model_name, messages=messages):
                    yield chunk
            return
        except Exception as e:
            logger.error("Cloud stream error: %s", e)
            yield "Cloud AI error."
            return

    resolved_mode, candidates = get_model_candidates(prompt, mode)

    for candidate_mode, model_name in candidates:
        try:
            for chunk in ask_ollama_stream(prompt, mode=candidate_mode, model_name=model_name, style=style, messages=messages):
                if chunk and chunk.strip():
                    yield chunk
            return

        except Exception as e:
            logger.error("AI stream error: %s", e)

    yield "AI error"

