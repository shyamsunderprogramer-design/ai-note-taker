"""
Regression tests for the IDOR fix in the jobs / analytics / study routes.

Before the fix, these routes trusted a client-supplied user_id (or had no
auth at all), so any caller could read and write another user's job
applications, analytics dashboards, and study plans by guessing ids:

    - routes/jobs.py: GET /job-tracker/applications (user_id=Query("default"),
      NO auth), every {app_id} endpoint (no ownership check), etc.
    - routes/analytics.py: GET /analytics/dashboard/{user_id} and the five
      other {user_id} graph-dashboard endpoints.
    - routes/study.py: GET /study-plan/{user_id}, POST /study-plan/generate
      (user_id=Query(...)), POST /study-plan/generate-personalized
      (request.user_id from the body).

The fix follows the Fix #31 pattern: every endpoint requires
authentication (router-level dependency), and the effective user_id is
resolved from the token via routes.deps.resolve_user_id — a client may
supply its own id, the literal "me", or nothing; anyone else's id is 403.
The {app_id} job endpoints additionally enforce ownership and return 404
for another user's ids so they are indistinguishable from missing ones.

Behavioral tests run against the real core.main app via
httpx + ASGITransport (TestClient returns 405 for APIRouter routes with
httpx 0.28+, see notes in tests/conftest.py), with a hermetic per-test
SQLite DB (the ``tmp_db`` conftest fixture) for the user store.
"""

import uuid

import httpx
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def scoped_env(tmp_db):
    """Two real users (Alice, Bob) with jti-stamped tokens.

    Returns (app, alice, alice_headers, bob, bob_headers). Mirrors the
    token-minting flow in conftest.auth_headers: create the user, stamp
    a jti so single-session enforcement (Fix #34) accepts the token.
    """
    from core.main import app
    from security.auth import create_access_token, user_manager
    from core.database import UserRepository

    async def make_user(prefix):
        unique = str(uuid.uuid4())[:8]
        user = await user_manager.create_user(
            username=f"{prefix}_{unique}",
            email=f"{prefix}_{unique}@example.com",
            password="TestPass123!",  # nosec B105 — test credential
        )
        jti = str(uuid.uuid4())
        await UserRepository.auth_headers_set_jti(str(user.id), jti)
        token = create_access_token(
            {"sub": str(user.id), "username": user.username}, jti=jti
        )
        return user, {"Authorization": f"Bearer {token}"}

    alice, alice_headers = await make_user("alice")
    bob, bob_headers = await make_user("bob")
    return app, alice, alice_headers, bob, bob_headers


@pytest_asyncio.fixture
async def client(scoped_env):
    app, *_ = scoped_env
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Auth is now required on all three routers (router-level dependency).
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/job-tracker/applications",
    "/job-tracker/stats",
    "/job-tracker/duplicates",
    "/job-tracker/search?query=x",
    "/job-tracker/upcoming-interviews",
    "/analytics/dashboard/me",
    "/analytics/summary",
    "/study-plan/me",
    "/study-plan/generate",
])
async def test_endpoints_reject_unauthenticated(client, path):
    resp = await client.get(path)
    assert resp.status_code == 401, (
        f"GET {path} without a token should be 401, got {resp.status_code}. "
        "Router-level require_authentication missing — IDOR fix regressed?"
    )


# ---------------------------------------------------------------------------
# user_id query/path params: own id, "me", or omitted → allowed; anyone
# else's id → 403.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_job_applications_scoped_to_caller(client, scoped_env):
    _, alice, alice_headers, bob, bob_headers = scoped_env

    # Alice creates an application (omitting user_id entirely).
    create = await client.post(
        "/job-tracker/application",
        params={"company": "AcmeIDOR", "role": "Engineer"},
        headers=alice_headers,
    )
    assert create.status_code == 200, create.text
    app_id = create.json()["application"]["id"]

    # Alice sees it — with no user_id, her own id, and "me".
    for params in ({}, {"user_id": str(alice.id)}, {"user_id": "me"}):
        resp = await client.get("/job-tracker/applications", params=params, headers=alice_headers)
        assert resp.status_code == 200, resp.text
        companies = [a.get("company") for a in resp.json()["applications"]]
        assert "AcmeIDOR" in companies, f"Alice cannot see her own application: {resp.text}"

    # Bob sees an empty list (nothing of Alice's leaks into it).
    resp = await client.get("/job-tracker/applications", headers=bob_headers)
    assert resp.status_code == 200, resp.text
    assert all(a.get("company") != "AcmeIDOR" for a in resp.json()["applications"])

    # Bob cannot ask for Alice's list by id.
    resp = await client.get(
        "/job-tracker/applications", params={"user_id": str(alice.id)}, headers=bob_headers
    )
    assert resp.status_code == 403, (
        f"Bob listing Alice's applications must be 403, got {resp.status_code} — IDOR."
    )
    # Same for the legacy "default" id and stats/search.
    for path, params in [
        ("/job-tracker/applications", {"user_id": "default"}),
        ("/job-tracker/stats", {"user_id": str(alice.id)}),
        ("/job-tracker/search", {"query": "Acme", "user_id": str(alice.id)}),
        ("/job-tracker/duplicates", {"user_id": str(alice.id)}),
    ]:
        resp = await client.get(path, params=params, headers=bob_headers)
        assert resp.status_code == 403, f"GET {path} as Bob for Alice's id must be 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_job_application_object_level_ownership(client, scoped_env):
    _, alice, alice_headers, bob, bob_headers = scoped_env

    create = await client.post(
        "/job-tracker/application",
        params={"company": "SecretCo", "role": "Engineer"},
        headers=alice_headers,
    )
    assert create.status_code == 200, create.text
    app_id = create.json()["application"]["id"]

    # Alice can read and mutate her own application.
    resp = await client.get(f"/job-tracker/application/{app_id}", headers=alice_headers)
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/job-tracker/application/{app_id}/status", params={"status": "applied"}, headers=alice_headers
    )
    assert resp.status_code == 200, resp.text

    # Bob gets 404 (not 403 — the id must be indistinguishable from
    # missing) on read, write, and delete of Alice's application.
    for method, path in [
        ("GET", f"/job-tracker/application/{app_id}"),
        ("GET", f"/job-tracker/application/{app_id}/details"),
        ("POST", f"/job-tracker/application/{app_id}/status?status=applied"),
        ("POST", f"/job-tracker/application/{app_id}/interview?interview_type=phone&scheduled_date=2026-11-01T10:00:00"),
        ("DELETE", f"/job-tracker/application/{app_id}"),
    ]:
        resp = await client.request(method, path, headers=bob_headers)
        assert resp.status_code == 404, (
            f"{method} {path} as Bob must be 404 (ownership enforced), got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_analytics_dashboard_scoped_to_caller(client, scoped_env):
    _, alice, alice_headers, bob, bob_headers = scoped_env

    # Bob asking for Alice's dashboard by id → 403.
    for path in [
        f"/analytics/dashboard/{alice.id}",
        f"/analytics/skill-progression/{alice.id}?skill=python",
        f"/analytics/topic-network/{alice.id}",
        f"/analytics/interview-calendar/{alice.id}",
        f"/analytics/performance-trends/{alice.id}",
        f"/performance/checklist/{alice.id}",
    ]:
        resp = await client.get(path, headers=bob_headers)
        assert resp.status_code == 403, (
            f"GET {path} as Bob for Alice's id must be 403, got {resp.status_code}"
        )

    # Bob asking for his own data (via "me" or his real id) is not
    # blocked — 200 when the analytics engine is available, 503 when it
    # is not (module availability), but never 401/403.
    for path in ["/analytics/dashboard/me", f"/analytics/dashboard/{bob.id}"]:
        resp = await client.get(path, headers=bob_headers)
        assert resp.status_code in (200, 503), (
            f"GET {path} as Bob for his own id should be 200/503, got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_study_plan_scoped_to_caller(client, scoped_env):
    _, alice, alice_headers, bob, bob_headers = scoped_env

    # Bob asking for Alice's plan by id → 403 (path param, today,
    # export, complete-task).
    for method, path in [
        ("GET", f"/study-plan/{alice.id}"),
        ("GET", f"/study-plan/{alice.id}/today"),
        ("POST", f"/study-plan/{alice.id}/export"),
        ("POST", f"/study-plan/{alice.id}/complete-task?task_id=t1"),
    ]:
        resp = await client.request(method, path, headers=bob_headers)
        assert resp.status_code == 403, (
            f"{method} {path} as Bob for Alice's id must be 403, got {resp.status_code}"
        )

    # generate (query param) with Alice's id as Bob → 403.
    resp = await client.post(
        "/study-plan/generate", params={"user_id": str(alice.id)}, headers=bob_headers
    )
    assert resp.status_code == 403, f"expected 403, got {resp.status_code}"

    # generate-personalized (body user_id) with Alice's id as Bob → 403.
    resp = await client.post(
        "/study-plan/generate-personalized",
        json={"user_id": str(alice.id), "target_role": "software_engineer"},
        headers=bob_headers,
    )
    assert resp.status_code == 403, f"expected 403, got {resp.status_code}"

    # Omitting user_id (or "me") is allowed for Bob — 200/503, never 401/403.
    resp = await client.post(
        "/study-plan/generate-personalized",
        json={"target_role": "software_engineer"},
        headers=bob_headers,
    )
    assert resp.status_code in (200, 503), (
        f"generate-personalized without user_id as Bob should be 200/503, got {resp.status_code}"
    )
    resp = await client.get("/study-plan/me", headers=bob_headers)
    assert resp.status_code in (200, 503), (
        f"GET /study-plan/me as Bob should be 200/503, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Source-shape regression: the routers themselves carry the auth
# dependency, so a new endpoint added to any of the three routers is
# authenticated by default.
# ---------------------------------------------------------------------------
def test_all_three_routers_require_auth_by_default():
    import ast

    router_files = [
        "routes/jobs.py",
        "routes/analytics.py",
        "routes/study.py",
    ]
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in router_files:
        with open(os.path.join(backend_dir, rel)) as f:
            tree = ast.parse(f.read())
        found = False
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if not (isinstance(target, ast.Name) and target.id == "router"):
                continue
            call = node.value
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "APIRouter"):
                continue
            for kw in call.keywords:
                if kw.arg != "dependencies":
                    continue
                # dependencies=[Depends(require_authentication)]
                if (isinstance(kw.value, (ast.List, ast.Tuple)) and kw.value.elts
                        and isinstance(kw.value.elts[0], ast.Call)
                        and isinstance(kw.value.elts[0].func, ast.Name)
                        and kw.value.elts[0].func.id == "Depends"):
                    found = True
        assert found, (
            f"{rel} router is missing router-level "
            "dependencies=[Depends(require_authentication)] — a new endpoint on "
            "this router would be unauthenticated. IDOR fix regressed?"
        )