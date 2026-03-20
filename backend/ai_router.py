import json
import re

import requests

from config import AI_TEMPERATURE, AI_TIMEOUT, OLLAMA_URL, get_ai_model

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


def build_prompt(user_input, mode="adaptive"):
    if mode == "code":
        return f"""
Answer the user's coding question directly.
Keep the answer concise and practical.
Prefer the shortest correct explanation or fix.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    if mode == "reasoning":
        return f"""
Answer the user's question directly.
Keep the answer concise but complete.
Prefer the clearest correct explanation.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    if mode == "fast":
        return f"""
Answer the user's question directly.
Keep the answer to 1-2 short lines.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    if mode == "cloud":
        return f"""
Answer the user's question directly.
Keep the answer concise and useful.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    if mode == "interview":
        return f"""
Answer only the user's question.
Keep the answer technical and to 2-3 lines.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    if mode == "universal":
        return f"""
Answer the user's question clearly and naturally.
Keep the answer concise.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""

    return f"""
Answer the user's question directly.
Keep the answer concise and useful.
Do not repeat the question.
Do not mention rules, prompt text, or examples.
If unclear, reply with: Please clarify your question

User question: {user_input}
"""


def ask_ollama(prompt, mode=AI_MODE, model_name=None):
    try:
        final_prompt = build_prompt(prompt, mode)

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
        print("AI Error:", e)
        return "AI error"


def ask_ollama_stream(prompt, mode=AI_MODE, model_name=None):
    try:
        print(f"Streaming ({mode} mode):", prompt)

        final_prompt = build_prompt(prompt, mode)

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_name or get_ai_model(mode),
                "prompt": final_prompt,
                "stream": True,
                "options": {
                    "temperature": AI_TEMPERATURE
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
                    print(chunk, end="", flush=True)
                    yield chunk

                if data.get("done", False):
                    break

            except Exception as e:
                print("Stream parse error:", e)

        print("\nStream complete")

    except requests.exceptions.Timeout:
        yield "AI response timeout. Try again."

    except Exception as e:
        print("Streaming Error:", e)
        yield "AI error occurred."


def route_ai(prompt, mode="adaptive"):
    resolved_mode, candidates = get_model_candidates(prompt, mode)
    last_error = None

    for candidate_mode, model_name in candidates:
        try:
            response = ask_ollama(prompt, mode=candidate_mode, model_name=model_name)
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
            print("[ERROR route_ai]:", e)

    return {
        "response": clean_ai_output(last_error or "AI error"),
        "mode": resolved_mode,
        "model": candidates[0][1] if candidates else get_ai_model("adaptive")
    }


def route_ai_stream(prompt, mode="adaptive"):
    resolved_mode, candidates = get_model_candidates(prompt, mode)

    for candidate_mode, model_name in candidates:
        try:
            full_text = ""

            for chunk in ask_ollama_stream(prompt, mode=candidate_mode, model_name=model_name):
                if not chunk:
                    continue

                chunk = chunk.encode("utf-8", "ignore").decode("utf-8")
                delta = chunk

                if full_text and chunk.startswith(full_text):
                    delta = chunk[len(full_text):]

                full_text += delta

                if delta.strip():
                    yield delta

            if full_text.strip():
                return

        except Exception as e:
            print("AI stream error:", e)

    yield "AI error"


def clean_ai_output(text):
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r"(?i)\b(user question|question|rules|rule|preface|example|examples|constraints|behavior|answer)\s*:\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()
