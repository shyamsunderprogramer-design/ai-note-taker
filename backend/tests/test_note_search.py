"""
test_note_search.py - Tests for the Apple Notes-inspired Note Search Engine.

Verifies:
1. Token parsing (terms, quoted phrases, #tags, role:filters, has:filters, dates)
2. Multi-tier ranking queries (Exact title > Prefix > Exact phrase in body > Keyword frequency)
3. Snippet extraction with word boundary snapping & adjusted match span offsets
4. Sectioned results formatting (Top Hits vs Regular Notes)
5. Integration with FastAPI /conversations/search endpoint with authenticated user scoping
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import httpx
import pytest
import pytest_asyncio

from lib.note_search import (
    NoteSearchEngine,
    NoteSearchRanker,
    SearchResultRegexMatchFinder,
    SearchUserInputParser,
)


class MockConversation:
    def __init__(self, conv_id: str, title: str, messages: List[Dict], updated_at=None, pinned=False):
        self.id = conv_id
        self.title = title
        self.messages = messages
        self.created_at = updated_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.message_count = len(messages)
        self.pinned = pinned


# ---------------------------------------------------------------------------
# Unit Tests: Token Parsing (ICSearchUserInput & ICSearchToken)
# ---------------------------------------------------------------------------
def test_search_user_input_tokenization():
    query = 'system design "distributed consensus" #architecture role:assistant after:2026-01-01'
    tokens = SearchUserInputParser.parse(query)

    kinds = {t.kind: t.value for t in tokens}
    assert "phrase" in kinds
    assert kinds["phrase"] == "distributed consensus"
    assert "tag" in kinds
    assert kinds["tag"] == "architecture"
    assert "role" in kinds
    assert kinds["role"] == "assistant"
    assert "date_after" in kinds
    assert kinds["date_after"] == "2026-01-01"

    terms = [t.value for t in tokens if t.kind == "term"]
    assert "system" in terms
    assert "design" in terms


# ---------------------------------------------------------------------------
# Unit Tests: Regex Match Finder & Snippets (ICSearchResultRegexMatchFinder)
# ---------------------------------------------------------------------------
def test_match_finder_and_snippet_extraction():
    tokens = SearchUserInputParser.parse("raft algorithm")
    regex = SearchResultRegexMatchFinder.build_search_regex(tokens)
    assert regex is not None

    sample_text = (
        "In modern systems engineering, the Raft algorithm provides an understandable "
        "approach to distributed consensus and state machine replication across clusters."
    )
    spans = SearchResultRegexMatchFinder.find_match_spans(sample_text, regex)
    assert len(spans) == 2
    assert spans[0].matched_text.lower() == "raft"
    assert spans[1].matched_text.lower() == "algorithm"

    snippet, adjusted_spans = SearchResultRegexMatchFinder.extract_snippet(sample_text, spans, max_length=60)
    assert "Raft" in snippet
    assert len(adjusted_spans) > 0
    # Match text matches the slice
    for sp in adjusted_spans:
        assert snippet[sp.start:sp.end].lower() in ("raft", "algorithm")


# ---------------------------------------------------------------------------
# Unit Tests: Multi-Tier Ranking (rankingQueries)
# ---------------------------------------------------------------------------
def test_ranking_prefers_exact_title_match():
    now = datetime.now(timezone.utc)
    conv1 = MockConversation(
        "1",
        title="Distributed Systems Notes",
        messages=[{"text": "General notes on distributed systems.", "role": "user"}],
        updated_at=now,
    )
    conv2 = MockConversation(
        "2",
        title="Raft Consensus",
        messages=[{"text": "Discussion about distributed systems in the body.", "role": "assistant"}],
        updated_at=now,
    )
    conv3 = MockConversation(
        "3",
        title="Distributed Systems",  # Exact title match
        messages=[{"text": "Brief overview.", "role": "user"}],
        updated_at=now,
    )

    results = NoteSearchEngine.search_conversations(
        [conv1, conv2, conv3],
        query="Distributed Systems",
        top_hits_threshold=60.0
    )

    # conv3 should be the #1 Top Hit
    assert len(results.top_hits) >= 1
    assert results.top_hits[0]["id"] == "3"
    assert results.top_hits[0]["score"] > results.notes[0]["score"]


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI /conversations/search with Auth Scoping
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def search_test_env(tmp_db):
    from core.main import app
    from security.auth import create_access_token, user_manager
    from core.database import UserRepository, ConversationRepository

    # Create Alice
    alice_name = f"alice_{str(uuid.uuid4())[:6]}"
    alice = await user_manager.create_user(
        username=alice_name, email=f"{alice_name}@example.com", password="Password123!"
    )
    jti_alice = str(uuid.uuid4())
    await UserRepository.auth_headers_set_jti(str(alice.id), jti_alice)
    alice_token = create_access_token({"sub": str(alice.id), "username": alice.username}, jti=jti_alice)
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # Create Bob
    bob_name = f"bob_{str(uuid.uuid4())[:6]}"
    bob = await user_manager.create_user(
        username=bob_name, email=f"{bob_name}@example.com", password="Password123!"
    )
    jti_bob = str(uuid.uuid4())
    await UserRepository.auth_headers_set_jti(str(bob.id), jti_bob)
    bob_token = create_access_token({"sub": str(bob.id), "username": bob.username}, jti=jti_bob)
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Seed Alice notes
    await ConversationRepository.create(
        user_id=str(alice.id),
        title="Kubernetes Pod Architecture",
        messages=[
            {"role": "user", "text": "How do daemonsets differ from deployments?"},
            {"role": "assistant", "text": "Daemonsets guarantee a pod replica runs on every node. #devops"}
        ]
    )
    await ConversationRepository.create(
        user_id=str(alice.id),
        title="Weekly Python Sync",
        messages=[
            {"role": "user", "text": "Let us discuss asyncio event loops."},
            {"role": "assistant", "text": "Asyncio is built on top of cooperative multitasking."}
        ]
    )

    # Seed Bob private note
    await ConversationRepository.create(
        user_id=str(bob.id),
        title="Bob Secret Kubernetes Key",
        messages=[{"role": "user", "text": "Secret cluster token."}]
    )

    return app, alice, alice_headers, bob, bob_headers


@pytest.mark.asyncio
async def test_api_search_endpoint_returns_sectioned_results(search_test_env):
    app, alice, alice_headers, bob, bob_headers = search_test_env
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res = await client.get("/conversations/search?q=Kubernetes")
        assert res.status_code == 401

        # 2. Alice searches "Kubernetes"
        res_alice = await client.get("/conversations/search?q=Kubernetes", headers=alice_headers)
        assert res_alice.status_code == 200
        data = res_alice.json()
        assert data["total_count"] >= 1
        assert "sections" in data
        assert "top_hits" in data["sections"]

        matched_titles = [n["title"] for n in data["sections"]["top_hits"] + data["sections"]["notes"]]
        assert "Kubernetes Pod Architecture" in matched_titles
        assert "Bob Secret Kubernetes Key" not in matched_titles  # Zero data leakage

        # 3. Alice searches with tag `#devops`
        res_tag = await client.get("/conversations/search?q=%23devops", headers=alice_headers)
        assert res_tag.status_code == 200
        tag_data = res_tag.json()
        assert tag_data["total_count"] == 1
        assert tag_data["sections"]["top_hits"][0]["title"] == "Kubernetes Pod Architecture"

        # 4. Bob searches "Kubernetes" -> only sees his own note
        res_bob = await client.get("/conversations/search?q=Kubernetes", headers=bob_headers)
        assert res_bob.status_code == 200
        bob_titles = [n["title"] for n in res_bob.json()["sections"]["top_hits"] + res_bob.json()["sections"]["notes"]]
        assert "Bob Secret Kubernetes Key" in bob_titles
        assert "Kubernetes Pod Architecture" not in bob_titles
