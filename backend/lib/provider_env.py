"""Load only provider keys from the desktop profile's optional local .env copy."""
import os
from pathlib import Path
from dotenv import dotenv_values

PROVIDER_KEYS = frozenset({"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
    "XAI_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY", "OLLAMA_CLOUD_API_KEY", "PERPLEXITY_API_KEY"})


def load_provider_env(filename):
    if not filename:
        return
    path = Path(filename)
    if not path.exists():
        return
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise ValueError("Invalid local provider .env file")
    # Literal credentials must never expand ${VARIABLE} references.
    for key, value in dotenv_values(path, interpolate=False).items():
        if key in PROVIDER_KEYS and value:
            os.environ.setdefault(key, value)
