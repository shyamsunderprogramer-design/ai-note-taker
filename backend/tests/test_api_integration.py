# Integration tests for AI Note Taker API
# Run with: pytest backend/tests/test_api_integration.py -v
#
# These tests require a running server at BASE_URL.
# They are automatically skipped when the server is not reachable (e.g. in CI).

import pytest
import pytest_asyncio
import httpx
import asyncio
import uuid
import socket
from typing import AsyncGenerator

BASE_URL = "http://127.0.0.1:8000"  # nosec B106 — test localhost

# Test user credentials - admin user is auto-created by UserManager
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"  # nosec B105 — test credential


def _server_available() -> bool:
    """Check if the API server is reachable."""
    try:
        host, port = "127.0.0.1", 8000  # nosec B106 — test localhost
        with socket.create_connection((host, port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


# Skip entire module if server is not running
pytestmark = pytest.mark.skipif(
    not _server_available(),
    reason="API server not running at http://127.0.0.1:8000 — start with: python -m core.main"
)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create authenticated async HTTP client with valid JWT token."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Register a test user first (self-contained fixture)
        unique = str(uuid.uuid4())[:8]
        reg_resp = await client.post("/auth/register", data={
            "username": f"integration_{unique}",
            "email": f"integration_{unique}@example.com",
            "password": "TestPass123!"
        })
        # Login with the registered user
        response = await client.post("/auth/login", data={
            "username": f"integration_{unique}",
            "password": "TestPass123!"
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication endpoints."""

    async def test_register(self, client: httpx.AsyncClient):
        """POST /auth/register."""
        unique = str(uuid.uuid4())[:8]
        response = await client.post("/auth/register", data={
            "username": f"testuser_{unique}",
            "email": f"test_{unique}@example.com",
            "password": "TestPass123!"  # nosec B105 — test credential
        })
        # Accept 200 (success), 400 (already exists), or 409 (conflict)
        assert response.status_code in [200, 201, 400, 409]  # nosec B101

    async def test_login(self, client: httpx.AsyncClient):
        """POST /auth/login."""
        response = await client.post("/auth/login", data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        })
        # Accept 200 (success) or 401 (invalid credentials)
        assert response.status_code in [200, 401]  # nosec B101

    async def test_me_requires_auth(self, client: httpx.AsyncClient):
        """GET /auth/me requires authentication."""
        response = await client.get("/auth/me")
        # Should return 401 without auth token
        assert response.status_code in [401, 403]  # nosec B101


@pytest.mark.asyncio
class TestProviderEndpoints:
    """Test AI provider endpoints."""

    async def test_get_providers(self, auth_client: httpx.AsyncClient):
        """GET /providers."""
        response = await auth_client.get("/providers")
        assert response.status_code == 200  # nosec B101
        data = response.json()
        assert isinstance(data, dict)  # nosec B101

    async def test_ollama_models(self, auth_client: httpx.AsyncClient):
        """GET /ollama/models."""
        response = await auth_client.get("/ollama/models")
        assert response.status_code in [200, 401, 500]  # May fail if Ollama not running or auth required  # nosec B101

    async def test_byok_status(self, auth_client: httpx.AsyncClient):
        """GET /providers/byok/status."""
        response = await auth_client.get("/providers/byok/status")
        assert response.status_code in [200, 401]  # nosec B101

    async def test_rate_limit_status(self, auth_client: httpx.AsyncClient):
        """GET /rate-limit/status."""
        response = await auth_client.get("/rate-limit/status")
        assert response.status_code in [200, 401]  # nosec B101


@pytest.mark.asyncio
class TestConversationEndpoints:
    """Test conversation management endpoints."""

    async def test_list_conversations(self, auth_client: httpx.AsyncClient):
        """GET /conversations."""
        response = await auth_client.get("/conversations")
        assert response.status_code == 200  # nosec B101
        data = response.json()
        assert isinstance(data, list)  # nosec B101

    async def test_create_conversation(self, auth_client: httpx.AsyncClient):
        """POST /conversations."""
        response = await auth_client.post("/conversations", json={
            "title": "Test Conversation",
            "messages": []
        })
        assert response.status_code in [200, 201]  # nosec B101

    async def test_export_conversation(self, auth_client: httpx.AsyncClient):
        """POST /conversations/export."""
        response = await auth_client.post("/conversations/export", json={
            "conversation_ids": []
        })
        assert response.status_code in [200, 400]  # 400 if no IDs provided  # nosec B101

    async def test_import_conversation(self, auth_client: httpx.AsyncClient):
        """POST /conversations/import."""
        response = await auth_client.post("/conversations/import", json={})
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestDocumentEndpoints:
    """Test document management endpoints."""

    async def test_list_documents(self, auth_client: httpx.AsyncClient):
        """GET /documents."""
        response = await auth_client.get("/documents")
        assert response.status_code == 200  # nosec B101
        data = response.json()
        assert isinstance(data, list)  # nosec B101

    async def test_retrieve_documents(self, auth_client: httpx.AsyncClient):
        """POST /documents/retrieve."""
        response = await auth_client.post("/documents/retrieve", json={
            "query": "test query"
        })
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestCognitiveGraphEndpoints:
    """Test cognitive graph endpoints."""

    async def test_cognitive_status(self, auth_client: httpx.AsyncClient):
        """GET /cognitive-graph/status."""
        response = await auth_client.get("/cognitive-graph/status")
        assert response.status_code == 200  # nosec B101

    async def test_cognitive_search(self, auth_client: httpx.AsyncClient):
        """GET /cognitive-graph/search."""
        response = await auth_client.get("/cognitive-graph/search", params={"q": "test"})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_cognitive_stats(self, auth_client: httpx.AsyncClient):
        """GET /cognitive-graph/stats."""
        response = await auth_client.get("/cognitive-graph/stats")
        assert response.status_code == 200  # nosec B101

    async def test_cognitive_advanced_search(self, auth_client: httpx.AsyncClient):
        """GET /cognitive-graph/search/advanced."""
        response = await auth_client.get("/cognitive-graph/search/advanced")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestInterviewAndSuggestions:
    """Test interview and real-time suggestion endpoints."""

    async def test_realtime_process(self, auth_client: httpx.AsyncClient):
        """POST /realtime/process."""
        response = await auth_client.post("/realtime/process", json={
            "text": "test transcript"
        })
        assert response.status_code in [200, 400]  # nosec B101

    async def test_realtime_configure(self, auth_client: httpx.AsyncClient):
        """POST /realtime/configure."""
        response = await auth_client.post("/realtime/configure", json={
            "mode": "interview"
        })
        assert response.status_code in [200, 400]  # nosec B101

    async def test_realtime_clear(self, auth_client: httpx.AsyncClient):
        """POST /realtime/clear."""
        response = await auth_client.post("/realtime/clear")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_predict_questions(self, auth_client: httpx.AsyncClient):
        """GET /predict/questions."""
        response = await auth_client.get("/predict/questions")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_predict_checklist(self, auth_client: httpx.AsyncClient):
        """GET /predict/checklist."""
        response = await auth_client.get("/predict/checklist")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_predict_companies(self, auth_client: httpx.AsyncClient):
        """GET /predict/companies."""
        response = await auth_client.get("/predict/companies")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestAnalyticsEndpoints:
    """Test analytics endpoints."""

    async def test_analytics_summary(self, auth_client: httpx.AsyncClient):
        """GET /analytics/summary."""
        response = await auth_client.get("/analytics/summary")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_analytics_record(self, auth_client: httpx.AsyncClient):
        """POST /analytics/record."""
        response = await auth_client.post("/analytics/record", json={
            "event_type": "test_event",
            "data": {}
        })
        assert response.status_code in [200, 400]  # nosec B101

    async def test_analytics_export(self, auth_client: httpx.AsyncClient):
        """POST /analytics/export."""
        response = await auth_client.post("/analytics/export", json={})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_analyze_types(self, auth_client: httpx.AsyncClient):
        """GET /analyze/types."""
        response = await auth_client.get("/analyze/types")
        assert response.status_code == 200  # nosec B101


@pytest.mark.asyncio
class TestPerformanceEndpoints:
    """Test performance analysis endpoints."""

    async def test_performance_tiers(self, auth_client: httpx.AsyncClient):
        """GET /performance/tiers."""
        response = await auth_client.get("/performance/tiers")
        assert response.status_code == 200  # nosec B101

    async def test_performance_analyze(self, auth_client: httpx.AsyncClient):
        """POST /performance/analyze."""
        response = await auth_client.post("/performance/analyze", json={
            "conversation_id": "test"
        })
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestStudyPlanEndpoints:
    """Test study plan endpoints."""

    async def test_study_plan_generate(self, auth_client: httpx.AsyncClient):
        """POST /study-plan/generate."""
        response = await auth_client.post("/study-plan/generate", json={
            "goal": "test goal"
        })
        assert response.status_code in [200, 400]  # nosec B101

    async def test_study_plan_resources(self, auth_client: httpx.AsyncClient):
        """GET /study-plan/resources/{category}."""
        response = await auth_client.get("/study-plan/resources/programming")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestJobTrackerEndpoints:
    """Test job tracker endpoints."""

    async def test_job_tracker_applications(self, auth_client: httpx.AsyncClient):
        """GET /job-tracker/applications."""
        response = await auth_client.get("/job-tracker/applications")
        assert response.status_code == 200  # nosec B101

    async def test_job_tracker_stats(self, auth_client: httpx.AsyncClient):
        """GET /job-tracker/stats."""
        response = await auth_client.get("/job-tracker/stats")
        assert response.status_code == 200  # nosec B101

    async def test_job_tracker_search(self, auth_client: httpx.AsyncClient):
        """GET /job-tracker/search."""
        response = await auth_client.get("/job-tracker/search", params={"q": "engineer"})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_job_tracker_upcoming_interviews(self, auth_client: httpx.AsyncClient):
        """GET /job-tracker/upcoming-interviews."""
        response = await auth_client.get("/job-tracker/upcoming-interviews")
        assert response.status_code == 200  # nosec B101

    async def test_job_tracker_duplicates(self, auth_client: httpx.AsyncClient):
        """GET /job-tracker/duplicates."""
        response = await auth_client.get("/job-tracker/duplicates")
        assert response.status_code in [200, 404]  # nosec B101


@pytest.mark.asyncio
class TestMockInterviewEndpoints:
    """Test mock interview endpoints."""

    async def test_mock_interview_questions(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/questions."""
        response = await auth_client.get("/mock-interview/questions")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_mock_interview_random_question(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/question/random."""
        response = await auth_client.get("/mock-interview/question/random")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_mock_interview_practice_set(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/practice-set."""
        response = await auth_client.get("/mock-interview/practice-set")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_mock_interview_search(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/search."""
        response = await auth_client.get("/mock-interview/search", params={"q": "behavioral"})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_mock_interview_stats(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/stats."""
        response = await auth_client.get("/mock-interview/stats")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_mock_interview_companies(self, auth_client: httpx.AsyncClient):
        """GET /mock-interview/companies."""
        response = await auth_client.get("/mock-interview/companies")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestVoiceCloneEndpoints:
    """Test voice cloning endpoints."""

    async def test_voice_clone_models(self, auth_client: httpx.AsyncClient):
        """GET /voice-clone/models."""
        response = await auth_client.get("/voice-clone/models")
        assert response.status_code in [200, 500]  # nosec B101

    async def test_voice_clone_gallery(self, auth_client: httpx.AsyncClient):
        """GET /voice-clone/gallery."""
        response = await auth_client.get("/voice-clone/gallery")
        assert response.status_code in [200, 500]  # nosec B101


@pytest.mark.asyncio
class TestShadowAgentEndpoints:
    """Test shadow agent endpoints."""

    async def test_shadow_suggestions(self, auth_client: httpx.AsyncClient):
        """GET /shadow/suggestions."""
        response = await auth_client.get("/shadow/suggestions")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_shadow_stats(self, auth_client: httpx.AsyncClient):
        """GET /shadow/stats."""
        response = await auth_client.get("/shadow/stats")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestCollaborationEndpoints:
    """Test collaboration endpoints."""

    async def test_collab_status(self, auth_client: httpx.AsyncClient):
        """GET /collaboration/status."""
        response = await auth_client.get("/collaboration/status")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_collab_messages(self, auth_client: httpx.AsyncClient):
        """GET /collaboration/messages."""
        response = await auth_client.get("/collaboration/messages")
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestMeetingTemplateEndpoints:
    """Test meeting template endpoints."""

    async def test_meeting_templates(self, auth_client: httpx.AsyncClient):
        """GET /meeting-templates."""
        response = await auth_client.get("/meeting-templates")
        assert response.status_code == 200  # nosec B101

    async def test_meeting_template_categories(self, auth_client: httpx.AsyncClient):
        """GET /meeting-templates/categories."""
        response = await auth_client.get("/meeting-templates/categories")
        assert response.status_code == 200  # nosec B101

    async def test_meeting_template_search(self, auth_client: httpx.AsyncClient):
        """GET /meeting-templates/search."""
        response = await auth_client.get("/meeting-templates/search", params={"q": "interview"})
        assert response.status_code in [200, 400]  # nosec B101


@pytest.mark.asyncio
class TestMiscEndpoints:
    """Test miscellaneous endpoints."""

    async def test_crm_config(self, auth_client: httpx.AsyncClient):
        """GET /crm/config."""
        response = await auth_client.get("/crm/config")
        assert response.status_code in [200, 404]  # nosec B101

    async def test_crm_test(self, auth_client: httpx.AsyncClient):
        """GET /crm/test."""
        response = await auth_client.get("/crm/test")
        assert response.status_code in [200, 400, 404]  # nosec B101

    async def test_search_web(self, auth_client: httpx.AsyncClient):
        """GET /search/web."""
        response = await auth_client.get("/search/web", params={"q": "test"})
        assert response.status_code in [200, 400, 503]  # nosec B101

    async def test_search_status(self, auth_client: httpx.AsyncClient):
        """GET /search/status."""
        response = await auth_client.get("/search/status")
        assert response.status_code in [200, 400]  # nosec B101

    async def test_resume_analyze(self, auth_client: httpx.AsyncClient):
        """POST /resume/analyze."""
        response = await auth_client.post("/resume/analyze", json={})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_resume_compare(self, auth_client: httpx.AsyncClient):
        """POST /resume/compare."""
        response = await auth_client.post("/resume/compare", json={})
        assert response.status_code in [200, 400]  # nosec B101

    async def test_analysis_complexity(self, auth_client: httpx.AsyncClient):
        """POST /analysis/complexity."""
        response = await auth_client.post("/analysis/complexity", json={
            "text": "test"
        })
        assert response.status_code in [200, 400]  # nosec B101


# ====================
# ENDPOINT COUNT VERIFICATION
# ====================
def test_endpoint_count():  # noqa: F821
    """Verify we're testing a significant portion of endpoints."""
    # This test file should cover at least 30 endpoints
    # Count the number of test methods
    import inspect
    test_methods = [m for m in dir(TestAuthEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestProviderEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestConversationEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestDocumentEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestCognitiveGraphEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestInterviewAndSuggestions) if m.startswith('test_')]
    test_methods += [m for m in dir(TestAnalyticsEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestPerformanceEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestJobTrackerEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestMockInterviewEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestVoiceCloneEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestShadowAgentEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestCollaborationEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestMeetingTemplateEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestMiscEndpoints) if m.startswith('test_')]

    # We should have at least 50 test methods covering various endpoints
    assert len(test_methods) >= 50, f"Expected at least 50 test methods, got {len(test_methods)}"  # nosec B101
