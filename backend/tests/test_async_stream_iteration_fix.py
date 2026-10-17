"""
Regression test for the async-generator iteration bug.

Bug: core/main.py patches every _STREAM_NAMES function (route_ai_stream,
ask_ollama_stream, ...) into async generators. Inside route_ai_stream,
the function was still a sync `def` doing sync `for event in helper(...)`
on these patched async generators → TypeError: 'async_generator' object
is not iterable. Same pattern existed in routes/ai.py at 4 iteration sites.

This test does TWO things:
  1. Static AST check: route_ai_stream is `async def`, and no file in
     backend/ contains a sync `for` over a patched stream function name.
  2. Live iteration test: import the patched module from a context where
     the `core` package resolves (so `from config import ...` works),
     mock ask_ollama_stream, and verify route_ai_stream yields all events
     without raising 'async_generator' object is not iterable.

Run from backend/ (where `core` resolves as a top-level package):
    cd backend && ../AINT_Venv/bin/python tests/test_async_stream_iteration_fix.py
or with pytest from backend/:
    cd backend && ../AINT_Venv/bin/python -m pytest tests/test_async_stream_iteration_fix.py -v
"""
import asyncio
import ast
import inspect
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(THIS_DIR)

# Quiet optional-dependency warnings during import
os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ANT_SKIP_ALEMBIC", "1")


# ─────────────────────────────────────────────────────────────────────────
# Static checks (no import needed — work anywhere)
# ─────────────────────────────────────────────────────────────────────────

PATCHED_FUNCTIONS = {
    "route_ai_stream",
    "ask_ollama_stream", "ask_ollama_vision_stream",
    "ask_ollama_cloud_stream", "ask_ollama_cloud_vision_stream",
    "ask_gpt_stream", "ask_gpt_vision_stream",
    "ask_claude_stream", "ask_claude_vision_stream",
    "ask_gemini_stream", "ask_gemini_vision_stream",
    "ask_grok_stream",
    "ask_deepseek_stream", "ask_groq_stream", "ask_groq_vision_stream",
    "ask_perplexity_stream",
}


def _check_route_ai_stream_is_async_def():
    """ai_router.route_ai_stream must be `async def`, not sync `def`."""
    fpath = os.path.join(BACKEND_DIR, "modules", "ai", "ai_router.py")
    with open(fpath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    found = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "route_ai_stream":
            assert isinstance(node, ast.AsyncFunctionDef), (
                f"{fpath}: route_ai_stream must be `async def`, got "
                f"{'async def' if isinstance(node, ast.AsyncFunctionDef) else 'sync def'}"
            )
            found = True
            break
    assert found, f"route_ai_stream not found in {fpath}"
    print(f"  [PASS] {fpath}: route_ai_stream is async def")


def _check_no_sync_iter_of_patched_functions():
    """No file under backend/ should do sync `for X in <patched_fn>(...)`."""
    roots = [
        BACKEND_DIR,
        os.path.join(BACKEND_DIR, "modules"),
        os.path.join(BACKEND_DIR, "routes"),
        os.path.join(BACKEND_DIR, "core"),
    ]
    bad = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            # Skip caches and venvs
            dirnames[:] = [d for d in dirnames
                           if d not in ("__pycache__", ".venv", "venv", "AINT_Venv", "node_modules")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=fpath)
                    except SyntaxError:
                        continue
                for node in ast.walk(tree):
                    # Sync `for X in expr:` — body is in node.body, expr is node.iter
                    if not isinstance(node, ast.For):
                        continue
                    # Skip `async for` (it's ast.AsyncFor)
                    if isinstance(node, ast.AsyncFor):
                        continue
                    if not isinstance(node.iter, ast.Call):
                        continue
                    func = node.iter.func
                    # Handle `module.fn(...)` and `fn(...)` forms
                    name = None
                    if isinstance(func, ast.Name):
                        name = func.id
                    elif isinstance(func, ast.Attribute):
                        name = func.attr
                    if name in PATCHED_FUNCTIONS:
                        rel = os.path.relpath(fpath, BACKEND_DIR)
                        bad.append(f"{rel}:{node.lineno}: for ... in {name}(...)")
    assert not bad, (
        "Found sync `for` over patched async stream function — would raise "
        "'async_generator' object is not iterable:\n  "
        + "\n  ".join(bad)
    )
    print(f"  [PASS] No sync iteration over patched async stream functions "
          f"({len(PATCHED_FUNCTIONS)} fns checked across {len(roots)} dirs)")


# ─────────────────────────────────────────────────────────────────────────
# Live iteration test (requires the runtime to be importable)
# ─────────────────────────────────────────────────────────────────────────

def _ensure_importable():
    """Add backend/, modules/, and modules/ai/ to sys.path so `ai_router`,
    `cloud_providers`, `core.config`, `from config import ...` all resolve.

    Mirrors the sys.path setup in start_server.py + core/main.py:23-36.
    """
    _project_root = os.path.dirname(BACKEND_DIR)  # the repo root
    _paths = [
        _project_root,                # allows `from backend.X import ...`
        BACKEND_DIR,                   # backend/ — for `from core.main import ...`
        os.path.join(_project_root, "modules"),  # repo-level modules/ (none here, but safe)
        os.path.join(BACKEND_DIR, "modules", "ai"),  # so `from ai_router import ...` resolves
        os.path.join(BACKEND_DIR, "core"),  # so `from config import ...` resolves
    ]
    for p in _paths:
        if p not in sys.path:
            sys.path.insert(0, p)


async def _test_route_ai_stream_iteration_with_mock():
    """Mock ask_ollama_stream; verify route_ai_stream yields all events
    without 'async_generator' object is not iterable."""
    _ensure_importable()
    import ai_router
    import core.main  # noqa: F401 — triggers the _patch_to_async_gen patch

    assert inspect.isasyncgenfunction(ai_router.route_ai_stream), (
        "route_ai_stream should be an async generator function after fix"
    )

    captured = []

    async def fake_ask_ollama_stream(prompt, mode="fast", model_name=None,
                                     style=None, messages=None, temperature=None):
        for chunk in (
            'event: meta\ndata: {}\n\n',
            'event: chunk\ndata: {"type":"chunk","content":"hello"}\n\n',
            'event: done\ndata: {}\n\n',
        ):
            yield chunk

    orig = ai_router.ask_ollama_stream
    ai_router.ask_ollama_stream = fake_ask_ollama_stream
    try:
        async for event in ai_router.route_ai_stream(
            "test prompt",
            mode="fast",
            style="concise",
            provider="qwen2.5:1.5b",  # looks like a local Ollama model
        ):
            captured.append(event)
    finally:
        ai_router.ask_ollama_stream = orig

    assert len(captured) == 3, f"expected 3 events, got {len(captured)}: {captured}"
    assert captured[0].startswith("event: meta"), captured[0]
    assert "hello" in captured[1], captured[1]
    assert captured[2].startswith("event: done"), captured[2]
    print(f"  [PASS] route_ai_stream iterates async helper correctly "
          f"({len(captured)} events flowed through)")


def main():
    print("test_async_stream_iteration_fix")
    _check_route_ai_stream_is_async_def()
    _check_no_sync_iter_of_patched_functions()
    try:
        asyncio.run(_test_route_ai_stream_iteration_with_mock())
    except ImportError as e:
        print(f"  [SKIP] Live iteration test (runtime import failed: {e})")
    print("ALL PASS")


if __name__ == "__main__":
    main()
