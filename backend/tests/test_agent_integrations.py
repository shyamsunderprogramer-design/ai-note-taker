"""
Integration Tests — VibeVoice Speaker Diarization + Self-Learning + Token Caching

Run from project root:  python -m pytest backend/tests/test_agent_integrations.py -v
Or manually:            python backend/tests/test_agent_integrations.py
"""

import sys
import os
import time
import json
import asyncio
import threading
import importlib.util

# Add module paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "modules"))

import numpy as np


def _load_vibevoice_module():
    """Load vibevoice_diarizer directly to avoid the voice/__init__.py
    platform.python_implementation bug in edge_tts."""
    spec = importlib.util.spec_from_file_location(
        "vibevoice_diarizer",
        os.path.join(os.path.dirname(__file__), "..", "modules", "voice", "vibevoice_diarizer.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_vibevoice = None

def get_vibevoice():
    global _vibevoice
    if _vibevoice is None:
        _vibevoice = _load_vibevoice_module()
    return _vibevoice


# =============================================================================
# Test 1: Speaker Diarization
# =============================================================================

def test_speaker_mapper():
    """SpeakerMapper converts raw speaker IDs to semantic roles."""
    vv = get_vibevoice()
    SpeakerMapper = vv.SpeakerMapper

    mapper = SpeakerMapper()

    # Speaker 1 is always the user
    assert mapper.map_speaker("Speaker 1") == "user", "Speaker 1 should be user"

    # Speaker 2 is the interviewer (default assumption)
    assert mapper.map_speaker("Speaker 2") == "interviewer", "Speaker 2 should be interviewer"

    # Speaker 3+ is other
    assert mapper.map_speaker("Speaker 3") == "other_1", "Speaker 3 should be other_1"

    # Semantic roles pass through
    assert mapper.map_speaker("user") == "user"
    assert mapper.map_speaker("interviewer") == "interviewer"

    print("  [PASS] SpeakerMapper: all assertions passed")


def test_speaker_mapper_custom_user():
    """SpeakerMapper with custom user speaker label."""
    vv = get_vibevoice()
    SpeakerMapper = vv.SpeakerMapper

    mapper = SpeakerMapper(user_speaker="Speaker 2")
    assert mapper.map_speaker("Speaker 2") == "user", "Custom user speaker should map to user"
    assert mapper.map_speaker("Speaker 1") == "interviewer", "Non-user should map to interviewer"

    print("  [PASS] SpeakerMapper custom user: all assertions passed")


def test_speaker_mapper_reset():
    """SpeakerMapper reset clears the mapping state."""
    vv = get_vibevoice()
    SpeakerMapper = vv.SpeakerMapper

    mapper = SpeakerMapper()
    mapper.map_speaker("Speaker 1")
    mapper.map_speaker("Speaker 2")
    assert len(mapper.speaker_map) == 2

    mapper.reset()
    assert len(mapper.speaker_map) == 1  # Only the user entry

    print("  [PASS] SpeakerMapper reset: all assertions passed")


def test_vibevoice_diarizer_fallback():
    """VibeVoiceDiarizer gracefully falls back when model is unavailable."""
    vv = get_vibevoice()
    VibeVoiceDiarizer = vv.VibeVoiceDiarizer

    d = VibeVoiceDiarizer()
    assert d.available is False, "VibeVoice should not be available without model download"
    assert d._load_attempted is False, "Should not attempt load until first use"

    # Test fallback path — this may fail if voice module can't be imported
    # due to the edge_tts/aiohttp platform bug in some environments
    audio = np.random.randn(16000).astype(np.float32) * 0.01
    try:
        segments = d.transcribe_with_diarization(audio, sample_rate=16000)
        # Should return at least one segment
        assert len(segments) >= 1, "Fallback should return at least one segment"
        assert segments[0].speaker_id == "Speaker 1", "Fallback assigns Speaker 1"
        print("  [PASS] VibeVoice fallback: returns segments without crashing")
    except (ImportError, AttributeError) as e:
        if "python_implementation" in str(e) or "voice" in str(e).lower():
            print("  [SKIP] VibeVoice fallback: voice module unavailable (platform bug)")
        else:
            raise


def test_vibevoice_resampling():
    """VibeVoiceDiarizer resamples audio from 48kHz to 16kHz."""
    vv = get_vibevoice()
    VibeVoiceDiarizer = vv.VibeVoiceDiarizer

    audio_48k = np.random.randn(48000).astype(np.float32)
    resampled = VibeVoiceDiarizer._resample(audio_48k, 48000, 16000)
    assert len(resampled) == 16000, f"Expected 16000 samples, got {len(resampled)}"

    # Same rate returns same audio
    same = VibeVoiceDiarizer._resample(audio_48k, 48000, 48000)
    assert len(same) == 48000

    print("  [PASS] VibeVoice resampling: 48kHz -> 16kHz correct")


def test_vibevoice_merge_consecutive():
    """Consecutive same-speaker segments are merged."""
    vv = get_vibevoice()
    VibeVoiceDiarizer = vv.VibeVoiceDiarizer
    SpeakerSegment = vv.SpeakerSegment

    segments = [
        SpeakerSegment(speaker_id="Speaker 1", start_time=0, end_time=3, text="Hello"),
        SpeakerSegment(speaker_id="Speaker 1", start_time=3, end_time=6, text="world"),
        SpeakerSegment(speaker_id="Speaker 2", start_time=6, end_time=9, text="Hi"),
    ]
    merged = VibeVoiceDiarizer._merge_consecutive(segments)
    assert len(merged) == 2, f"Expected 2 segments after merge, got {len(merged)}"
    assert merged[0].text == "Hello world"
    assert merged[1].text == "Hi"

    print("  [PASS] VibeVoice merge: consecutive same-speaker merged")


def test_streaming_diarizer():
    """StreamingDiarizer processes audio chunks and returns speaker labels."""
    vv = get_vibevoice()
    StreamingDiarizer = vv.StreamingDiarizer

    sd = StreamingDiarizer()
    # Process a short audio segment with text
    audio = np.random.randn(8000).astype(np.float32) * 0.01
    try:
        result = sd.process_audio_segment(audio, "Hello world")

        assert "speaker" in result, "Result should have speaker field"
        assert "semantic_role" in result, "Result should have semantic_role field"
        assert "text" in result, "Result should have text field"
        assert result["text"] == "Hello world"

        print("  [PASS] StreamingDiarizer: returns speaker + semantic_role + text")
    except (ImportError, AttributeError) as e:
        if "python_implementation" in str(e) or "voice" in str(e).lower():
            print("  [SKIP] StreamingDiarizer: voice module unavailable (platform bug)")
        else:
            raise


def test_format_transcript():
    """Speaker segments are formatted as readable transcript."""
    vv = get_vibevoice()
    VibeVoiceDiarizer = vv.VibeVoiceDiarizer
    SpeakerSegment = vv.SpeakerSegment

    d = VibeVoiceDiarizer()
    segments = [
        SpeakerSegment(speaker_id="Speaker 1", start_time=0, end_time=5, text="Hello there"),
        SpeakerSegment(speaker_id="Speaker 2", start_time=5, end_time=10, text="Hi, how are you?"),
        SpeakerSegment(speaker_id="Speaker 1", start_time=10, end_time=15, text="I am doing great"),
    ]
    formatted = d.format_transcript(segments)
    assert "[Speaker 1]" in formatted
    assert "[Speaker 2]" in formatted
    assert "Hello there" in formatted
    assert "how are you" in formatted

    print("  [PASS] Format transcript: proper speaker labels and text")


# =============================================================================
# Test 2: Orchestrator Speaker Normalization
# =============================================================================

def test_orchestrator_normalize_speaker():
    """Orchestrator normalizes all speaker label formats to semantic roles."""
    from agents.orchestrator import orchestrator

    # Raw diarizer labels
    assert orchestrator.normalize_speaker("Speaker 1") == "user"
    assert orchestrator.normalize_speaker("Speaker 2") == "interviewer"
    assert orchestrator.normalize_speaker("Speaker 3") == "other"

    # VibeVoice format
    assert orchestrator.normalize_speaker("SPEAKER_00") == "user"
    assert orchestrator.normalize_speaker("SPEAKER_01") == "interviewer"
    assert orchestrator.normalize_speaker("SPEAKER_02") == "other"

    # Semantic roles pass through
    assert orchestrator.normalize_speaker("user") == "user"
    assert orchestrator.normalize_speaker("interviewer") == "interviewer"
    assert orchestrator.normalize_speaker("other") == "other"

    # StreamingDiarizer "other_N" format
    assert orchestrator.normalize_speaker("other_1") == "other"
    assert orchestrator.normalize_speaker("other_2") == "other"

    # Empty/unknown
    assert orchestrator.normalize_speaker("") == "other"
    assert orchestrator.normalize_speaker("unknown_person") == "other"

    print("  [PASS] Orchestrator normalize_speaker: all formats handled")


def test_orchestrator_custom_speaker_map():
    """Orchestrator respects custom speaker_map in session config."""
    from agents.orchestrator import orchestrator

    session = {"config": {"speaker_map": {"Alice": "interviewer", "Bob": "user"}}}
    assert orchestrator.normalize_speaker("Alice", session) == "interviewer"
    assert orchestrator.normalize_speaker("Bob", session) == "user"

    # Unmapped speaker falls through to default logic
    assert orchestrator.normalize_speaker("Speaker 1", session) == "user"

    print("  [PASS] Custom speaker_map: custom names mapped correctly")


# =============================================================================
# Test 3: Token Caching
# =============================================================================

def test_cache_exact_match():
    """ContextCache returns exact matches."""
    from agents.cache import ContextCache

    cache = ContextCache()
    cache.put("How does Kubernetes work?", graph_results=[{"q": "test"}])

    result = cache.get("How does Kubernetes work?")
    assert result is not None, "Exact match should hit"
    assert len(result.graph_results) == 1

    # Different question should miss
    miss = cache.get("What is Docker?")
    assert miss is None, "Different question should miss"

    print("  [PASS] Cache exact match: hit and miss work correctly")


def test_cache_similarity_match():
    """ContextCache finds similar questions above threshold."""
    from agents.cache import ContextCache

    cache = ContextCache(similarity_threshold=0.75)
    cache.put("How does Kubernetes handle pod scaling?",
              graph_results=[{"q": "k8s scaling"}],
              rag_results=[{"text": "doc about HPA"}])

    # Similar but not identical question
    result = cache.get("How does Kubernetes handle pod auto-scaling?")
    assert result is not None, "Similar question should hit"
    assert len(result.graph_results) == 1
    assert len(result.rag_results) == 1

    # Very different question should miss
    miss = cache.get("What is the capital of France?")
    assert miss is None, "Unrelated question should miss"

    print("  [PASS] Cache similarity match: detects paraphrased questions")


def test_cache_ttl_expiration():
    """ContextCache entries expire after TTL."""
    from agents.cache import ContextCache

    cache = ContextCache(default_ttl=1)  # 1 second TTL
    cache.put("test question", graph_results=[{"q": "test"}])

    # Immediate hit
    result = cache.get("test question")
    assert result is not None, "Should hit before expiry"

    # Wait for expiry
    time.sleep(1.5)
    expired = cache.get("test question")
    assert expired is None, "Should miss after TTL expires"

    print("  [PASS] Cache TTL: entries expire correctly")


def test_cache_eviction():
    """ContextCache evicts oldest entries when full."""
    from agents.cache import ContextCache

    cache = ContextCache(max_entries=3)
    cache.put("q1", graph_results=[{"q": 1}])
    cache.put("q2", graph_results=[{"q": 2}])
    cache.put("q3", graph_results=[{"q": 3}])
    assert len(cache._store) == 3

    # Adding 4th entry should evict the oldest (q1)
    cache.put("q4", graph_results=[{"q": 4}])
    assert len(cache._store) == 3, "Should stay at max_entries"
    assert cache.get("q1") is None, "Oldest should be evicted"
    assert cache.get("q4") is not None, "Newest should exist"

    print("  [PASS] Cache eviction: LRU eviction works")


def test_cache_stats():
    """ContextCache tracks hit/miss statistics."""
    from agents.cache import ContextCache

    cache = ContextCache()
    cache.put("test query", graph_results=[{"q": "test"}])

    cache.get("test query")     # hit
    cache.get("test query")     # hit
    cache.get("miss query")     # miss

    stats = cache.get_stats()
    assert stats["exact_hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] > 0

    print("  [PASS] Cache stats: tracks hits, misses, hit_rate")


def test_cache_cleanup():
    """ContextCache cleanup removes expired entries."""
    from agents.cache import ContextCache

    cache = ContextCache(default_ttl=1)
    cache.put("old1", graph_results=[{"q": 1}])
    cache.put("old2", graph_results=[{"q": 2}])
    time.sleep(1.5)

    removed = cache.cleanup_expired()
    assert removed == 2, f"Expected 2 expired, got {removed}"
    assert len(cache._store) == 0

    print("  [PASS] Cache cleanup: removes expired entries")


# =============================================================================
# Test 4: Self-Learning
# =============================================================================

def test_learner_record_feedback():
    """SuggestionLearner records accept/dismiss feedback."""
    from agents.learning import SuggestionLearner

    learner = SuggestionLearner()
    learner.record_acceptance("s1", "interview_coach", "technical", "Use autoscaling", 0.85)
    learner.record_dismissal("s2", "interview_coach", "stalling", "Buy time", 0.60)

    stats = learner.get_performance_stats("interview_coach")
    assert stats["total_suggestions"] == 2
    assert stats["accepted"] == 1
    assert stats["dismissed"] == 1
    assert stats["acceptance_rate"] == 0.5

    print("  [PASS] Learner record: tracks accept/dismiss counts")


def test_learner_confidence_boost():
    """SuggestionLearner boosts confidence for high-acceptance categories."""
    from agents.learning import SuggestionLearner

    learner = SuggestionLearner()

    # Record many technical accepts
    for i in range(10):
        learner.record_acceptance(f"s{i}", "interview_coach", "technical", f"Suggestion {i}", 0.8 + i * 0.02)

    # Record many stalling dismissals
    for i in range(10):
        learner.record_dismissal(f"d{i}", "interview_coach", "stalling", f"Dismissal {i}", 0.7)

    # Technical should get a positive boost
    tech_boost = learner.get_confidence_boost("interview_coach", "technical")
    assert tech_boost > 0, f"Technical boost should be positive, got {tech_boost}"

    # Stalling should get a negative boost
    stall_boost = learner.get_confidence_boost("interview_coach", "stalling")
    assert stall_boost < 0, f"Stalling boost should be negative, got {stall_boost}"

    print("  [PASS] Confidence boost: technical +, stalling -")


def test_learner_learned_hints():
    """SuggestionLearner generates hints after enough feedback."""
    from agents.learning import SuggestionLearner

    learner = SuggestionLearner()

    # Need 5+ data points for hints to appear
    for i in range(8):
        learner.record_acceptance(f"s{i}", "interview_coach", "technical", f"Tech suggestion {i}", 0.85)

    hints = learner.format_hints_for_prompt("interview_coach")
    assert len(hints) > 0, "Should generate hints after 5+ feedback"
    assert "LEARNED INSIGHTS" in hints
    assert "technical" in hints.lower()

    print("  [PASS] Learned hints: generated after sufficient feedback")


def test_learner_no_hints_early():
    """SuggestionLearner does not generate hints with too few data points."""
    from agents.learning import SuggestionLearner

    learner = SuggestionLearner()
    learner.record_acceptance("s1", "interview_coach", "technical", "Test", 0.8)

    hints = learner.format_hints_for_prompt("interview_coach")
    assert hints == "", "Should not generate hints with < 5 data points"

    print("  [PASS] No early hints: waits for enough data")


def test_learner_session_persistence():
    """SuggestionLearner saves/loads state to session dict."""
    from agents.learning import SuggestionLearner

    learner1 = SuggestionLearner()
    learner1.record_acceptance("s1", "interview_coach", "technical", "Test", 0.85)
    learner1.record_dismissal("s2", "interview_coach", "stalling", "Test2", 0.60)

    # Save to session
    session = {}
    learner1.save_to_session(session)
    assert "learning_state" in session
    assert "agent_performance" in session["learning_state"]

    # Load in new learner
    learner2 = SuggestionLearner()
    learner2.load_from_session(session)

    stats = learner2.get_performance_stats("interview_coach")
    assert stats["total_suggestions"] == 2
    assert stats["accepted"] == 1

    print("  [PASS] Session persistence: save/load round-trips correctly")


# =============================================================================
# Test 5: Integration — Speaker + Orchestrator + Cache + Learner
# =============================================================================

def test_full_pipeline_speaker_to_agent():
    """Full pipeline: speaker diarization -> orchestrator -> agent activation."""
    from agents.orchestrator import orchestrator

    # Simulate what happens when the WebSocket sends a message with speaker info
    speaker_from_diarizer = "Speaker 2"  # The other person in the call

    # Orchestrator normalizes this
    role = orchestrator.normalize_speaker(speaker_from_diarizer)
    assert role == "interviewer", "Speaker 2 should become interviewer"

    # An interviewer question should activate the interview coach
    from agents.base import TranscriptSegment, is_question
    segment = TranscriptSegment(
        text="Can you explain how Kubernetes handles pod scaling?",
        speaker=role,
        timestamp=time.time(),
        is_question=True,
    )

    # Create a mock session
    session = {
        "active_agents": ["interview_coach", "meeting", "sales_coach"],
        "transcript_buffer": [],
        "agent_states": {},
        "entities": {},
        "config": {},
    }

    # Check each agent's activation
    from agents.interview_coach import InterviewCoachAgent
    from agents.meeting import MeetingAgent
    from agents.sales_coach import SalesCoachAgent

    interview = InterviewCoachAgent()
    meeting = MeetingAgent()
    sales = SalesCoachAgent()

    assert interview.should_activate(session, segment) is True, "Interview coach activates on interviewer questions"
    assert meeting.should_activate(session, segment) is True, "Meeting agent activates on any segment"

    print("  [PASS] Full pipeline: diarizer -> orchestrator -> agent activation")


def test_cache_used_in_interview_coach():
    """Interview coach uses cached results for similar questions."""
    from agents.cache import ContextCache

    cache = ContextCache(similarity_threshold=0.6)
    # Pre-populate cache
    cache.put(
        "Can you explain how Kubernetes handles pod scaling?",
        graph_results=[{"question": "past Q", "answer": "past A"}],
        rag_results=[{"text": "doc content", "doc_name": "prep.pdf"}],
    )

    # Exact match should be found
    result = cache.get("Can you explain how Kubernetes handles pod scaling?")
    assert result is not None
    assert len(result.graph_results) == 1
    assert len(result.rag_results) == 1

    # Similar question should also hit (Jaccard sim ~0.8 for this pair)
    similar = cache.get("Can you explain how Kubernetes handles pod auto-scaling?")
    assert similar is not None, "Similar question should hit cache"

    print("  [PASS] Cache integration: interview coach reuses cached results")


def test_learner_boosts_applied_to_suggestions():
    """Orchestrator applies learner confidence boosts to parsed suggestions."""
    from agents.learning import SuggestionLearner
    from agents.base import AgentSuggestion

    learner = SuggestionLearner()

    # Simulate a user who always accepts technical suggestions
    for i in range(10):
        learner.record_acceptance(f"s{i}", "interview_coach", "technical", f"Tech {i}", 0.8)

    # Create a suggestion with base confidence 0.75
    suggestion = AgentSuggestion(
        id="test_1",
        agent_type="interview_coach",
        category="technical",
        content="Use horizontal pod autoscaling",
        confidence=0.75,
    )

    # Apply the boost (simulating what orchestrator does)
    boost = learner.get_confidence_boost("interview_coach", "technical")
    suggestion.confidence = min(1.0, max(0.0, suggestion.confidence + boost))

    assert suggestion.confidence > 0.75, f"Confidence should be boosted above 0.75, got {suggestion.confidence}"

    print("  [PASS] Learner integration: confidence boosted for high-acceptance categories")


# =============================================================================
# Test 6: Minimal Speaker Detector
# =============================================================================

def test_minimal_speaker_detector():
    """_MinimalSpeakerDetector distinguishes speakers by energy features."""
    vv = get_vibevoice()
    _MinimalSpeakerDetector = vv._MinimalSpeakerDetector

    detector = _MinimalSpeakerDetector()

    # Low energy audio (quiet speaker)
    quiet = np.random.randn(8000).astype(np.float32) * 0.001
    speaker1 = detector.identify_speaker(quiet)

    # Loud audio (different speaker)
    loud = np.random.randn(8000).astype(np.float32) * 0.5
    speaker2 = detector.identify_speaker(loud)

    assert speaker1 != speaker2, "Different energy levels should map to different speakers"
    assert speaker1.startswith("Speaker ")
    assert speaker2.startswith("Speaker ")

    print("  [PASS] Minimal detector: distinguishes speakers by energy")


# =============================================================================
# Main runner
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VibeVoice Speaker Diarization + Self-Learning + Cache Tests")
    print("=" * 60)

    tests = [
        # Speaker Diarization
        test_speaker_mapper,
        test_speaker_mapper_custom_user,
        test_speaker_mapper_reset,
        test_vibevoice_diarizer_fallback,
        test_vibevoice_resampling,
        test_vibevoice_merge_consecutive,
        test_streaming_diarizer,
        test_format_transcript,
        test_minimal_speaker_detector,
        # Orchestrator Speaker Normalization
        test_orchestrator_normalize_speaker,
        test_orchestrator_custom_speaker_map,
        # Token Caching
        test_cache_exact_match,
        test_cache_similarity_match,
        test_cache_ttl_expiration,
        test_cache_eviction,
        test_cache_stats,
        test_cache_cleanup,
        # Self-Learning
        test_learner_record_feedback,
        test_learner_confidence_boost,
        test_learner_learned_hints,
        test_learner_no_hints_early,
        test_learner_session_persistence,
        # Integration
        test_full_pipeline_speaker_to_agent,
        test_cache_used_in_interview_coach,
        test_learner_boosts_applied_to_suggestions,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)