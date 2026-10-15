"""
Regression test for v2.1.5 → v2.1.6: bare-name ``cloud_providers`` imports.

Bug: ``core/main.py:116-121`` patches streaming helpers on the
``modules.platform.cloud_providers`` module (the canonical, fully-qualified
import path). But several lazy imports in the codebase used the bare name
``from cloud_providers import ...``. That bare-name import resolves to a
SECOND module instance of the same file — a fresh ``cloud_providers``
namespace that's NOT patched. So when ``route_ai_stream`` did
``async for event in stream_fn(...)`` with ``stream_fn`` pulled from the
unpatched module, the call returned a sync generator and ``async for``
crashed with ``'async for' requires an object with __aiter__ method,
got generator``. The user saw ``Cloud AI error: 'async for' requires...``
whenever a cloud provider (OpenAI, Anthropic, etc.) was selected.

Fix: every ``from cloud_providers import`` line replaced with
``from modules.platform.cloud_providers import`` so all callers see the
patched module instance.

This test scans all backend/ Python files (excluding venv) and asserts
that no live ``from cloud_providers import`` lines exist. The fix has
sixteen sites across five files; this test catches any future regressions.

Static check only — no Python imports needed. Runs in any environment:
    cd backend && python -m pytest tests/test_no_bare_cloud_providers_import.py -v
or standalone:
    cd backend && python tests/test_no_bare_cloud_providers_import.py
"""
import ast
import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(THIS_DIR)


def _all_py_files():
    """Yield every .py file under backend/, skipping venv and __pycache__."""
    skip_dirs = {"venv", "__pycache__", ".pytest_cache", "node_modules", "data"}
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def _find_bare_cloud_providers_imports(path):
    """Walk an AST and return a list of (lineno, col_offset, names) for
    every ``from cloud_providers import ...`` statement whose module name
    is exactly ``"cloud_providers"`` (not ``modules.platform.cloud_providers``).
    """
    findings = []
    with open(path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=path)
        except SyntaxError:
            return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "cloud_providers":
                names = [n.name for n in node.names]
                findings.append((node.lineno, node.col_offset, names))
    return findings


def test_no_bare_cloud_providers_imports():
    """No file under backend/ may have a bare ``from cloud_providers import ...``."""
    violations = []  # (file, lineno, names)
    for path in _all_py_files():
        for lineno, col, names in _find_bare_cloud_providers_imports(path):
            rel = os.path.relpath(path, BACKEND_DIR)
            violations.append((rel, lineno, names))
    assert not violations, (
        "Bare `from cloud_providers import ...` found — these resolve to "
        "a SECOND (unpatched) module instance and cause "
        "'async for' requires an object with __aiter__ method, got generator' "
        "errors whenever a cloud provider is selected. Use "
        "`from modules.platform.cloud_providers import ...` instead.\n\n"
        "Violations:\n" + "\n".join(
            f"  {rel}:{ln}  imports {names}"
            for rel, ln, names in violations
        )
    )


if __name__ == "__main__":
    # Standalone runner
    import sys
    try:
        test_no_bare_cloud_providers_imports()
        print("PASS  test_no_bare_cloud_providers_imports")
        sys.exit(0)
    except AssertionError as e:
        print(f"FAIL  test_no_bare_cloud_providers_imports\n{e}")
        sys.exit(1)