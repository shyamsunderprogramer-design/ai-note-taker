from dotenv import load_dotenv
import os

# ==============================
# 🔐 LOAD ENV VARIABLES
# ==============================
# Loads variables from .env file into environment
load_dotenv()


# ==============================
# 🌐 OLLAMA CONFIG
# ==============================
# Base URL where Ollama server is running (local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Ollama Cloud URL (ollama.com or custom cloud endpoint)
OLLAMA_CLOUD_URL = os.getenv("OLLAMA_CLOUD_URL", "https://ollama.com")
OLLAMA_CLOUD_API_KEY = os.getenv("OLLAMA_CLOUD_API_KEY", "")

# Default fallback model (must exist in `ollama list`)
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:1.5b")
MODEL_CLOUD = os.getenv("OLLAMA_MODEL_CLOUD", "minimax-m2.7:cloud")
MODEL_REASONING = os.getenv("OLLAMA_MODEL_REASONING", "qwen2.5:1.5b")
MODEL_CODE = os.getenv("OLLAMA_MODEL_CODE", "qwen2.5:1.5b")


# ==============================
# 🧠 MODEL CONFIG (BY MODE)
# ==============================
# You can override these in .env
MODEL_INTERVIEW = os.getenv("OLLAMA_MODEL_INTERVIEW", "llama3:latest")
MODEL_UNIVERSAL = os.getenv("OLLAMA_MODEL_UNIVERSAL", "mistral:latest")
MODEL_ADAPTIVE = os.getenv("OLLAMA_MODEL_ADAPTIVE", DEFAULT_MODEL)
ALLOWED_MODES = ("auto", "fast", "cloud", "interview", "universal", "adaptive", "reasoning", "code", "turbo")


# ==============================
# ⚙️ RUNTIME SETTINGS
# ==============================
# AI behavior tuning (optional but useful)
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.1"))

# Timeout for AI requests (seconds)
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "30"))

# Super-fast mode: tiny model for instant responses
MODEL_TURBO = os.getenv("OLLAMA_MODEL_TURBO", "qwen2.5:1.5b")  # Small fast model
TURBO_MAX_TOKENS = int(os.getenv("TURBO_MAX_TOKENS", "150"))  # Very short responses

# Instant mode: ultra-fast for immediate responses
INSTANT_MAX_TOKENS = int(os.getenv("INSTANT_MAX_TOKENS", "64"))  # Ultra short


# ==============================
# 🎯 MODEL ROUTER
# ==============================
def get_ai_model(mode="adaptive"):
    """
    Returns correct model based on mode

    Modes:
    - interview  → strict, technical answers
    - universal  → general purpose
    - adaptive   → fast + balanced (default)
    """

    if mode == "reasoning":
        return MODEL_REASONING

    if mode == "turbo":
        return MODEL_TURBO

    if mode == "instant":
        return MODEL_TURBO  # Same fast model, fewer tokens

    if mode == "code":
        return MODEL_CODE

    if mode == "fast":
        return MODEL_FAST

    if mode == "cloud":
        return MODEL_CLOUD

    if mode == "interview":
        return MODEL_INTERVIEW

    if mode == "summary":
        return MODEL_UNIVERSAL

    elif mode == "universal":
        return MODEL_UNIVERSAL

    # 🔥 default adaptive mode
    return MODEL_ADAPTIVE


# ==============================
# 🔮 EMBEDDING SERVICE
# ==============================
# Local sentence-transformers embeddings for semantic search
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "auto")
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "10000"))
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")  # local, ollama, hybrid

# Enable/disable embedding service (set to "false" to save ~120MB RAM)
EMBEDDING_ENABLED = os.getenv("EMBEDDING_ENABLED", "true").lower() == "true"

# ==============================
# 🏷️ SMART CLASSIFIER
# ==============================
# Zero-shot classification for question categorization, difficulty, etc.
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
CLASSIFIER_DEVICE = os.getenv("CLASSIFIER_DEVICE", "auto")

# Enable/disable classifier (set to "false" to save ~300MB RAM)
CLASSIFIER_ENABLED = os.getenv("CLASSIFIER_ENABLED", "true").lower() == "true"

# Semantic search similarity threshold (0.0-1.0, higher = stricter matching)
SEMANTIC_SEARCH_THRESHOLD = float(os.getenv("SEMANTIC_SEARCH_THRESHOLD", "0.3"))


# ==============================
# 🧪 DEBUG (OPTIONAL)
# ==============================
def print_config():
    """
    Debug helper to verify loaded configuration
    """
    print("🔧 CONFIG LOADED:")
    print(f"OLLAMA_URL: {OLLAMA_URL}")
    print(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
    print(f"FAST_MODEL: {MODEL_FAST}")
    print(f"CLOUD_MODEL: {MODEL_CLOUD}")
    print(f"REASONING_MODEL: {MODEL_REASONING}")
    print(f"CODE_MODEL: {MODEL_CODE}")
    print(f"INTERVIEW_MODEL: {MODEL_INTERVIEW}")
    print(f"UNIVERSAL_MODEL: {MODEL_UNIVERSAL}")
    print(f"ADAPTIVE_MODEL: {MODEL_ADAPTIVE}")
    print(f"TEMPERATURE: {AI_TEMPERATURE}")
    print(f"TIMEOUT: {AI_TIMEOUT}")
