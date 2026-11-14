import os
from lib.provider_env import load_provider_env


def test_provider_env_loads_only_keys_as_literals(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "explicit-environment-wins")
    filename = tmp_path / ".env"
    filename.write_text('GROQ_API_KEY="literal#key${HOME}"\nOPENAI_API_KEY="file-value"\nJWT_SECRET_KEY="not-allowed"\n')
    load_provider_env(str(filename))
    assert os.environ["GROQ_API_KEY"] == "literal#key${HOME}"
    assert os.environ["OPENAI_API_KEY"] == "explicit-environment-wins"
    assert "JWT_SECRET_KEY" not in os.environ
    monkeypatch.delenv("GROQ_API_KEY")


def test_missing_provider_file_is_optional(tmp_path):
    load_provider_env(None)
    load_provider_env(str(tmp_path / ".env"))
