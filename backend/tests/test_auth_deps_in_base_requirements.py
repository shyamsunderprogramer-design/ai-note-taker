"""
Regression test for v2.1.4 → v2.1.5: bundled-venv was missing auth deps.

Bug: ``requirements.txt`` (the file the release workflow's
``pip install -r requirements.txt`` step installs from, release.yml:144)
did NOT include ``python-jose`` / ``passlib`` / ``bcrypt`` — those lived
in ``requirements-security.txt``, which the release workflow never
installs. Result: the bundled venv at first boot had ``HAS_JWT=False``,
which silently short-circuited registration to plaintext storage and
crashed login on ``pwd_context.verify`` (None has no ``.verify``).
The user saw "registration failed → still rotating" with no useful
error in the UI.

This test asserts the three auth deps are present in the BASE
``backend/requirements.txt`` (where the bundled venv installer reads
from), so this category of bug fails CI loudly next time.

Static check only — no Python imports needed. Runs in any environment
with Python 3. Run via:

    cd backend && python -m pytest tests/test_auth_deps_in_base_requirements.py -v

or standalone:

    cd backend && python tests/test_auth_deps_in_base_requirements.py
"""
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(THIS_DIR)
REQUIREMENTS_TXT = os.path.join(BACKEND_DIR, "requirements.txt")

# Packages that MUST be in backend/requirements.txt (the file the
# release workflow installs from). If any of these get moved to a
# separate file (e.g. requirements-security.txt, requirements-dev.txt),
# this test fails and surfaces the bug at PR time, not at first boot.
REQUIRED_AUTH_PACKAGES = [
    "python-jose",
    "passlib",
    "bcrypt",
]

# ``cryptography`` is pulled in transitively by ``python-jose[cryptography]``
# but assert it explicitly too — without it, python-jose falls back to
# pure-python and HS256/RS256 verify can fail at runtime.
REQUIRED_TRANSITIVE = ["cryptography"]


def _read_requirements() -> str:
    with open(REQUIREMENTS_TXT, encoding="utf-8") as f:
        return f.read()


def test_auth_deps_in_base_requirements():
    """The three auth deps MUST be in backend/requirements.txt."""
    content = _read_requirements()
    missing = [pkg for pkg in REQUIRED_AUTH_PACKAGES if pkg not in content]
    assert not missing, (
        f"Auth deps missing from backend/requirements.txt: {missing}.\n"
        "These are RUNTIME deps for the bundled installer — they belong "
        "in the base requirements.txt (which release.yml:144 installs), "
        "not in requirements-security.txt (which only the dev test "
        "pipeline installs). See unified-forging-rivest.md (v2.1.5 "
        "hotfix) for the full incident write-up."
    )


def test_cryptography_in_base_requirements():
    """``cryptography`` is the transitive dep that lets python-jose sign/verify."""
    content = _read_requirements()
    missing = [pkg for pkg in REQUIRED_TRANSITIVE if pkg not in content]
    assert not missing, (
        f"Transitive auth deps missing from backend/requirements.txt: {missing}.\n"
        "``cryptography`` is pulled by ``python-jose[cryptography]`` and "
        "needed for HS256/RS256 token verification. Without it the bundled "
        "app signs tokens but fails to verify them."
    )


def test_requirements_file_exists():
    """Sanity check — the file we're auditing exists."""
    assert os.path.isfile(REQUIREMENTS_TXT), (
        f"requirements.txt not found at {REQUIREMENTS_TXT}"
    )


if __name__ == "__main__":
    # Allow running standalone: `python tests/test_auth_deps_in_base_requirements.py`
    failures = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                print(f"FAIL  {name}: {e}")
                failures.append(name)
            except Exception as e:
                print(f"ERROR {name}: {type(e).__name__}: {e}")
                failures.append(name)
    if failures:
        print(f"\n{len(failures)} test(s) failed: {failures}")
        sys.exit(1)
    print(f"\nAll {sum(1 for n in globals() if n.startswith('test_') and callable(globals()[n]))} tests passed.")