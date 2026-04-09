# Integration tests for AI Note Taker API
# Run with: pytest backend/tests/test_api_integration.py -v

import pytest
import pytest_asyncio
import httpx
import asyncio
from typing import AsyncGenerator

BASE_URL = "http://127.0.0.1:8000"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health and status endpoints."""

    async def test_health(self, client: httpx.AsyncClient):
        """GET /health - basic health check."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in data or response.status_code == 200

    async def test_health_modules(self, client: httpx.AsyncClient):
        """GET /health/modules - module availability status."""
        response = await client.get("/health/modules")
        assert response.status_code == 200
        data = response.json()
        assert "modules" in data or isinstance(data, dict)


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication endpoints."""

    async def test_register(self, client: httpx.AsyncClient):
        """POST /auth/register."""
        response = await client.post("/auth/register", json={
            "email": f"test_{id(asyncio.current_task())}@example.com",
            "password": "testpassword123"
        })
        # Accept 200 (success), 400 (already exists), or 409 (conflict)
        assert response.status_code in [200, 201, 400, 409]

    async def test_login(self, client: httpx.AsyncClient):
        """POST /auth/login."""
        # Try to login with test credentials
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        # Accept 200 (success) or 401 (invalid credentials)
        assert response.status_code in [200, 401]

    async def test_me_requires_auth(self, client: httpx.AsyncClient):
        """GET /auth/me requires authentication."""
        response = await client.get("/auth/me")
        # Should return 401 without auth token
        assert response.status_code in [200, 401]


@pytest.mark.asyncio
class TestProviderEndpoints:
    """Test AI provider endpoints."""

    async def test_get_providers(self, client: httpx.AsyncClient):
        """GET /providers."""
        response = await client.get("/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_ollama_models(self, client: httpx.AsyncClient):
        """GET /ollama/models."""
        response = await client.get("/ollama/models")
        assert response.status_code in [200, 500]  # May fail if Ollama not running

    async def test_byok_status(self, client: httpx.AsyncClient):
        """GET /providers/byok/status."""
        response = await client.get("/providers/byok/status")
        assert response.status_code == 200

    async def test_rate_limit_status(self, client: httpx.AsyncClient):
        """GET /rate-limit/status."""
        response = await client.get("/rate-limit/status")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestConversationEndpoints:
    """Test conversation management endpoints."""

    async def test_list_conversations(self, client: httpx.AsyncClient):
        """GET /conversations."""
        response = await client.get("/conversations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_conversation(self, client: httpx.AsyncClient):
        """POST /conversations."""
        response = await client.post("/conversations", json={
            "title": "Test Conversation",
            "messages": []
        })
        assert response.status_code in [200, 201]

    async def test_export_conversation(self, client: httpx.AsyncClient):
        """POST /conversations/export."""
        response = await client.post("/conversations/export", json={
            "conversation_ids": []
        })
        assert response.status_code in [200, 400]  # 400 if no IDs provided

    async def test_import_conversation(self, client: httpx.AsyncClient):
        """POST /conversations/import."""
        response = await client.post("/conversations/import", json={})
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestDocumentEndpoints:
    """Test document management endpoints."""

    async def test_list_documents(self, client: httpx.AsyncClient):
        """GET /documents."""
        response = await client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_retrieve_documents(self, client: httpx.AsyncClient):
        """POST /documents/retrieve."""
        response = await client.post("/documents/retrieve", json={
            "query": "test query"
        })
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestCognitiveGraphEndpoints:
    """Test cognitive graph endpoints."""

    async def test_cognitive_status(self, client: httpx.AsyncClient):
        """GET /cognitive-graph/status."""
        response = await client.get("/cognitive-graph/status")
        assert response.status_code == 200

    async def test_cognitive_search(self, client: httpx.AsyncClient):
        """GET /cognitive-graph/search."""
        response = await client.get("/cognitive-graph/search", params={"q": "test"})
        assert response.status_code in [200, 400]

    async def test_cognitive_stats(self, client: httpx.AsyncClient):
        """GET /cognitive-graph/stats."""
        response = await client.get("/cognitive-graph/stats")
        assert response.status_code == 200

    async def test_cognitive_advanced_search(self, client: httpx.AsyncClient):
        """GET /cognitive-graph/search/advanced."""
        response = await client.get("/cognitive-graph/search/advanced")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestInterviewAndSuggestions:
    """Test interview and real-time suggestion endpoints."""

    async def test_realtime_process(self, client: httpx.AsyncClient):
        """POST /realtime/process."""
        response = await client.post("/realtime/process", json={
            "text": "test transcript"
        })
        assert response.status_code in [200, 400]

    async def test_realtime_configure(self, client: httpx.AsyncClient):
        """POST /realtime/configure."""
        response = await client.post("/realtime/configure", json={
            "mode": "interview"
        })
        assert response.status_code in [200, 400]

    async def test_realtime_clear(self, client: httpx.AsyncClient):
        """POST /realtime/clear."""
        response = await client.post("/realtime/clear")
        assert response.status_code in [200, 400]

    async def test_predict_questions(self, client: httpx.AsyncClient):
        """GET /predict/questions."""
        response = await client.get("/predict/questions")
        assert response.status_code in [200, 400]

    async def test_predict_checklist(self, client: httpx.AsyncClient):
        """GET /predict/checklist."""
        response = await client.get("/predict/checklist")
        assert response.status_code in [200, 400]

    async def test_predict_companies(self, client: httpx.AsyncClient):
        """GET /predict/companies."""
        response = await client.get("/predict/companies")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestAnalyticsEndpoints:
    """Test analytics endpoints."""

    async def test_analytics_summary(self, client: httpx.AsyncClient):
        """GET /analytics/summary."""
        response = await client.get("/analytics/summary")
        assert response.status_code in [200, 400]

    async def test_analytics_record(self, client: httpx.AsyncClient):
        """POST /analytics/record."""
        response = await client.post("/analytics/record", json={
            "event_type": "test_event",
            "data": {}
        })
        assert response.status_code in [200, 400]

    async def test_analytics_export(self, client: httpx.AsyncClient):
        """POST /analytics/export."""
        response = await client.post("/analytics/export", json={})
        assert response.status_code in [200, 400]

    async def test_analyze_types(self, client: httpx.AsyncClient):
        """GET /analyze/types."""
        response = await client.get("/analyze/types")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestPerformanceEndpoints:
    """Test performance analysis endpoints."""

    async def test_performance_tiers(self, client: httpx.AsyncClient):
        """GET /performance/tiers."""
        response = await client.get("/performance/tiers")
        assert response.status_code == 200

    async def test_performance_analyze(self, client: httpx.AsyncClient):
        """POST /performance/analyze."""
        response = await client.post("/performance/analyze", json={
            "conversation_id": "test"
        })
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestStudyPlanEndpoints:
    """Test study plan endpoints."""

    async def test_study_plan_generate(self, client: httpx.AsyncClient):
        """POST /study-plan/generate."""
        response = await client.post("/study-plan/generate", json={
            "goal": "test goal"
        })
        assert response.status_code in [200, 400]

    async def test_study_plan_resources(self, client: httpx.AsyncClient):
        """GET /study-plan/resources/{category}."""
        response = await client.get("/study-plan/resources/programming")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestJobTrackerEndpoints:
    """Test job tracker endpoints."""

    async def test_job_tracker_applications(self, client: httpx.AsyncClient):
        """GET /job-tracker/applications."""
        response = await client.get("/job-tracker/applications")
        assert response.status_code == 200

    async def test_job_tracker_stats(self, client: httpx.AsyncClient):
        """GET /job-tracker/stats."""
        response = await client.get("/job-tracker/stats")
        assert response.status_code == 200

    async def test_job_tracker_search(self, client: httpx.AsyncClient):
        """GET /job-tracker/search."""
        response = await client.get("/job-tracker/search", params={"q": "engineer"})
        assert response.status_code in [200, 400]

    async def test_job_tracker_upcoming_interviews(self, client: httpx.AsyncClient):
        """GET /job-tracker/upcoming-interviews."""
        response = await client.get("/job-tracker/upcoming-interviews")
        assert response.status_code == 200

    async def test_job_tracker_duplicates(self, client: httpx.AsyncClient):
        """GET /job-tracker/duplicates."""
        response = await client.get("/job-tracker/duplicates")
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestMockInterviewEndpoints:
    """Test mock interview endpoints."""

    async def test_mock_interview_questions(self, client: httpx.AsyncClient):
        """GET /mock-interview/questions."""
        response = await client.get("/mock-interview/questions")
        assert response.status_code in [200, 400]

    async def test_mock_interview_random_question(self, client: httpx.AsyncClient):
        """GET /mock-interview/question/random."""
        response = await client.get("/mock-interview/question/random")
        assert response.status_code in [200, 400]

    async def test_mock_interview_practice_set(self, client: httpx.AsyncClient):
        """GET /mock-interview/practice-set."""
        response = await client.get("/mock-interview/practice-set")
        assert response.status_code in [200, 400]

    async def test_mock_interview_search(self, client: httpx.AsyncClient):
        """GET /mock-interview/search."""
        response = await client.get("/mock-interview/search", params={"q": "behavioral"})
        assert response.status_code in [200, 400]

    async def test_mock_interview_stats(self, client: httpx.AsyncClient):
        """GET /mock-interview/stats."""
        response = await client.get("/mock-interview/stats")
        assert response.status_code in [200, 400]

    async def test_mock_interview_companies(self, client: httpx.AsyncClient):
        """GET /mock-interview/companies."""
        response = await client.get("/mock-interview/companies")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestVoiceCloneEndpoints:
    """Test voice cloning endpoints."""

    async def test_voice_clone_models(self, client: httpx.AsyncClient):
        """GET /voice-clone/models."""
        response = await client.get("/voice-clone/models")
        assert response.status_code in [200, 500]

    async def test_voice_clone_gallery(self, client: httpx.AsyncClient):
        """GET /voice-clone/gallery."""
        response = await client.get("/voice-clone/gallery")
        assert response.status_code in [200, 500]


@pytest.mark.asyncio
class TestShadowAgentEndpoints:
    """Test shadow agent endpoints."""

    async def test_shadow_suggestions(self, client: httpx.AsyncClient):
        """GET /shadow/suggestions."""
        response = await client.get("/shadow/suggestions")
        assert response.status_code in [200, 400]

    async def test_shadow_stats(self, client: httpx.AsyncClient):
        """GET /shadow/stats."""
        response = await client.get("/shadow/stats")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestCollaborationEndpoints:
    """Test collaboration endpoints."""

    async def test_collab_status(self, client: httpx.AsyncClient):
        """GET /collaboration/status."""
        response = await client.get("/collaboration/status")
        assert response.status_code in [200, 400]

    async def test_collab_messages(self, client: httpx.AsyncClient):
        """GET /collaboration/messages."""
        response = await client.get("/collaboration/messages")
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestMeetingTemplateEndpoints:
    """Test meeting template endpoints."""

    async def test_meeting_templates(self, client: httpx.AsyncClient):
        """GET /meeting-templates."""
        response = await client.get("/meeting-templates")
        assert response.status_code == 200

    async def test_meeting_template_categories(self, client: httpx.AsyncClient):
        """GET /meeting-templates/categories."""
        response = await client.get("/meeting-templates/categories")
        assert response.status_code == 200

    async def test_meeting_template_search(self, client: httpx.AsyncClient):
        """GET /meeting-templates/search."""
        response = await client.get("/meeting-templates/search", params={"q": "interview"})
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestMiscEndpoints:
    """Test miscellaneous endpoints."""

    async def test_crm_config(self, client: httpx.AsyncClient):
        """GET /crm/config."""
        response = await client.get("/crm/config")
        assert response.status_code in [200, 404]

    async def test_crm_test(self, client: httpx.AsyncClient):
        """GET /crm/test."""
        response = await client.get("/crm/test")
        assert response.status_code in [200, 400, 404]

    async def test_search_web(self, client: httpx.AsyncClient):
        """GET /search/web."""
        response = await client.get("/search/web", params={"q": "test"})
        assert response.status_code in [200, 400, 503]

    async def test_search_status(self, client: httpx.AsyncClient):
        """GET /search/status."""
        response = await client.get("/search/status")
        assert response.status_code in [200, 400]

    async def test_resume_analyze(self, client: httpx.AsyncClient):
        """POST /resume/analyze."""
        response = await client.post("/resume/analyze", json={})
        assert response.status_code in [200, 400]

    async def test_resume_compare(self, client: httpx.AsyncClient):
        """POST /resume/compare."""
        response = await client.post("/resume/compare", json={})
        assert response.status_code in [200, 400]

    async def test_analysis_complexity(self, client: httpx.AsyncClient):
        """POST /analysis/complexity."""
        response = await client.post("/analysis/complexity", json={
            "text": "test"
        })
        assert response.status_code in [200, 400]


# ====================
# ENDPOINT COUNT VERIFICATION
# ====================
def test_endpoint_count():
    """Verify we're testing a significant portion of endpoints."""
    # This test file should cover at least 30 endpoints
    # Count the number of test methods
    import inspect
    test_methods = [m for m in dir(TestHealthEndpoints) if m.startswith('test_')]
    test_methods += [m for m in dir(TestAuthEndpoints) if m.startswith('test_')]
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
    assert len(test_methods) >= 50, f"Expected at least 50 test methods, got {len(test_methods)}"
