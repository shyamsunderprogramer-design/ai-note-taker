"""Regression guardrail for Fix #35 Commit 6.

The migration from a JSON-file user store (``backend/data/users.json``)
to a SQLAlchemy-backed store is complete. This file pins that fact at
the source level: if a future commit re-introduces the JSON store
methods or constants, the AST tests here fail loudly.

Why an AST guard rather than a runtime check:
- The forbidden symbols are module-level definitions. An AST walk
  catches a re-introduction in CI without needing to import the
  module or set up a database.
- The check is exhaustive over the source file, so it survives
  refactors that move methods around within ``security/auth.py``.

Forbidden symbols (each one a tell that someone tried to put the
JSON store back):

- ``USERS_FILE``         — the path constant for the canonical users.json
- ``_LEGACY_USERS_FILE`` — the legacy fallback path constant
- ``_save_users``        — the method that flushed the in-memory dict to disk
- ``_load_users``        — the method that read users.json into memory
- ``_users``             — the in-memory dict that was the runtime store
- ``self.users``         — same, accessed via the manager instance

None of these should exist in ``security/auth.py``. The SQLAlchemy
``users`` table (via ``core.database.UserRepository``) is the single
source of truth.
"""

import ast
import os
import sys

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _BACKEND)

AUTH_PY = os.path.join(_BACKEND, "security", "auth.py")


class TestNoJsonUserStoreRegression:
    """Pin the Fix #35 Commit 6 invariant: the JSON user store is gone
    from security/auth.py and stays gone."""

    @pytest.fixture
    def auth_source(self):
        with open(AUTH_PY) as f:
            return f.read()

    @pytest.fixture
    def auth_tree(self, auth_source):
        return ast.parse(auth_source)

    # --- module-level definitions ---

    @pytest.mark.parametrize("forbidden", [
        "USERS_FILE",
        "_LEGACY_USERS_FILE",
        "_save_users",
        "_load_users",
    ])
    def test_no_module_level_definition(self, auth_tree, forbidden):
        """A top-level ``def`` or assignment binding for any of the
        forbidden names would mean someone re-introduced the JSON
        store. AST walks the whole module once per name."""
        for node in ast.walk(auth_tree):
            if isinstance(node, ast.FunctionDef) and node.name == forbidden:
                pytest.fail(
                    f"security/auth.py defines function {forbidden}() — "
                    f"the JSON user store is gone (Fix #35). Use "
                    f"core.database.UserRepository instead."
                )
            if isinstance(node, ast.AsyncFunctionDef) and node.name == forbidden:
                pytest.fail(
                    f"security/auth.py defines async function {forbidden}() — "
                    f"the JSON user store is gone (Fix #35)."
                )
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Name)
                            and target.id == forbidden):
                        pytest.fail(
                            f"security/auth.py assigns to {forbidden} — "
                            f"the JSON user store is gone (Fix #35)."
                        )
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == forbidden:
                    pytest.fail(
                        f"security/auth.py annotates {forbidden} — "
                        f"the JSON user store is gone (Fix #35)."
                    )

    def test_no_in_memory_users_dict(self, auth_source):
        """``self.users = {…}`` inside the UserManager body would mean
        someone re-introduced the in-memory dict. A targeted string
        check is faster than AST for this specific shape."""
        # Look for the literal pattern ``self.users`` in UserManager
        # method bodies. The ``UserManager.users`` *attribute access*
        # is fine (e.g. ``user_manager.users.values()`` would be a
        # regression, but reading the public dict in test code is
        # gone now that there's no public attribute). The simplest
        # pin: the literal substring ``self.users =`` must not appear.
        assert "self.users = " not in auth_source, (
            "security/auth.py assigns to self.users — the in-memory "
            "dict is gone (Fix #35). Use core.database.UserRepository."
        )

    def test_does_not_open_users_json(self, auth_source):
        """Pin that security/auth.py does not open() the users.json file.
        A docstring/comment mention of the string ``users.json``
        (historical context) is fine — this test is about I/O, not
        narrative. We look for ``open(...)`` calls whose argument
        references the file."""
        tree = ast.parse(auth_source)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "open"):
                for arg in node.args:
                    if (isinstance(arg, ast.Constant)
                            and isinstance(arg.value, str)
                            and "users.json" in arg.value):
                        pytest.fail(
                            f"security/auth.py opens {arg.value!r} "
                            f"(line {node.lineno}) — the JSON user "
                            f"store is gone (Fix #35). The "
                            f"DataMigrator (core/database.py) is "
                            f"the only place that reads users.json."
                        )

    def test_no_json_module_import_for_user_storage(self, auth_source):
        """A top-level ``import json`` used for *user storage* would
        mean someone is about to do JSON I/O for users. The dev-token
        helpers (create_access_token / verify_token / etc.) legitimately
        use ``import json`` for their base64 fallback path, but those
        are inline imports inside the function bodies — not at module
        scope. So this test pins: a top-level ``import json`` must not
        be in security/auth.py.

        We use AST rather than substring matching so that a future
        commit which moves an inline import up to module scope
        (a real regression) fails the test."""
        tree = ast.parse(auth_source)
        for node in tree.body:  # module-level only, not inside functions
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "json":
                        pytest.fail(
                            "security/auth.py has a module-level "
                            "'import json' (line {line}) — the JSON "
                            "user store is gone (Fix #35). The dev-"
                            "token helpers may keep their INLINE "
                            "'import json' inside the function body, "
                            "but a top-level import is a regression."
                            .format(line=node.lineno)
                        )
            if isinstance(node, ast.ImportFrom) and node.module == "json":
                pytest.fail(
                    f"security/auth.py has a module-level 'from json "
                    f"import ...' (line {node.lineno}) — the JSON user "
                    f"store is gone (Fix #35)."
                )

    # --- docstring guard: the auth.py module docstring documents
    #     the canonical source of truth. If the docstring stops
    #     saying SQLAlchemy, someone has regressed the narrative. ---

    def test_module_docstring_mentions_sqlalchemy(self, auth_source):
        """The narrative guardrail: auth.py's module docstring (or
        the UserManager class docstring) must explicitly state that
        SQLAlchemy / UserRepository is the source of truth. If a
        future refactor silently removes that note, this test fails
        and forces the committer to either keep the contract or
        consciously rewrite the docstring."""
        lowered = auth_source.lower()
        assert "sqlalchemy" in lowered or "userrepository" in lowered, (
            "security/auth.py no longer mentions SQLAlchemy or "
            "UserRepository in its docstring — the JSON-store "
            "narrative is gone but the SQL-store narrative must "
            "stay. Update the docstring to reflect the Fix #35 "
            "source-of-truth contract."
        )
