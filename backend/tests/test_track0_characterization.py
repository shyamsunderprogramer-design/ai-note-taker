"""
Track 0 characterization suite (E1, eng-review 2026-09-06).

Purpose: FREEZE the current live-assist behavior before the T1
LiveAssistService extraction touches it. These tests pin what the pipeline
does today — including its known gaps (documented-bug tests) so the T1
refactor can't silently change behavior the mocks validated (commit 56fb707).

Covers the live path:
  - routes/transcription.py: _looks_like_interview_question (WS-path detector)
  - modules/ai/realtime_suggestions.py: generate_live_suggestion (Ollama gen
    + template fallback)
  - source-level fingerprints for the settle-timer / cooldown / payload
    shape that live as nested functions inside the WS handler

Run: python -m pytest backend/tests/test_track0_characterization.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'ai'))
# modules/ai uses the bare `from config import ...` convention; config.py
# lives in core/ (matches start_server.py's sys.path setup).
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))


# ---------------------------------------------------------------------------
# 1. WS-path question detector (routes/transcription.py)
# ---------------------------------------------------------------------------

class TestLooksLikeInterviewQuestion:
    """Characterizes routes/transcription.py:_looks_like_interview_question.

    Known gap (deliberate T3 deliverable, NOT a bug to fix here): imperative
    design prompts with no '?' are NOT detected. These tests pin today's
    behavior so T1's detector merge changes it consciously.
    """

    def test_question_starters_detected(self):
        from routes.transcription import _looks_like_interview_question
        for text in (
            "What is your biggest weakness?",
            "How do you design a rate limiter for a gateway?",
            "Tell me about a time you led a project",
            "Explain how you handled a conflict",
        ):
            assert _looks_like_interview_question(text) is True, text

    def test_question_mark_anywhere_detected(self):
        from routes.transcription import _looks_like_interview_question
        # >=5 words + '?' anywhere passes even without a starter word.
        assert _looks_like_interview_question("and your experience with that?") is True

    def test_fragments_rejected(self):
        from routes.transcription import _looks_like_interview_question
        # Tiny-whisper fragments (<5 words) must not trigger a suggestion
        # per fragment — this is the documented reason the WS-path detector
        # exists instead of whisper_handler.is_question().
        for text in ("project.", "time.", "yes I did", "okay sure thing"):
            assert _looks_like_interview_question(text) is False, text

    def test_minimum_5_words__known_gap(self):
        from routes.transcription import _looks_like_interview_question
        # DOCUMENTED GAP: a real short question like "Describe your biggest
        # achievement" (4 words) is dropped today. The 5-word minimum is
        # what kills whisper fragments — T3 may revisit the threshold, but
        # it must not shrink silently.
        assert _looks_like_interview_question("Describe your biggest achievement") is False

    def test_imperative_design_prompt_not_detected__known_gap(self):
        from routes.transcription import _looks_like_interview_question
        # DOCUMENTED GAP: no '?' and first word not in starters. T3 adds
        # imperative-prompt detection; do NOT let this start passing silently
        # from an unrelated refactor.
        assert _looks_like_interview_question("Design a URL shortener") is False
        assert _looks_like_interview_question("Build a rate limiter for our gateway") is False

    def test_statement_rejected(self):
        from routes.transcription import _looks_like_interview_question
        assert _looks_like_interview_question(
            "I worked on React for three years and led the migration"
        ) is False

    def test_question_starters_set_contents(self):
        from routes.transcription import _QUESTION_STARTERS
        # The exact starter set the mocks validated — freeze it.
        assert _QUESTION_STARTERS == {
            "what", "why", "how", "when", "where", "who", "which", "can",
            "could", "would", "should", "do", "does", "did", "is", "are",
            "tell", "explain", "describe", "walk",
        }


# ---------------------------------------------------------------------------
# 2. generate_live_suggestion with a MOCKED Ollama (realtime_suggestions.py)
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for httpx.Response used by generate_live_suggestion."""

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"response": "ok"}

    def json(self):
        return self._payload


class TestGenerateLiveSuggestion:
    """Characterizes modules/ai/realtime_suggestions.py:generate_live_suggestion."""

    def test_payload_shape_and_options(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return _FakeResponse(200, {"response": "I led the migration end to end."})

        monkeypatch.setattr("httpx.post", fake_post)
        from realtime_suggestions import generate_live_suggestion

        result = generate_live_suggestion(
            "What is your biggest weakness?",
            role="software engineer", company="Google",
            skills="python, distributed systems", resume="built ANT",
        )

        # Return-contract shape the WS handler depends on
        assert set(result) == {"text", "gen_ms", "model", "error"}
        assert result["text"] == "I led the migration end to end."
        assert result["error"] is None
        assert isinstance(result["gen_ms"], int)

        # Request-contract: URL, timeout, and every payload field the
        # installed models need (esp. think:false — qwen3.5/lfm2.5 put
        # content in `thinking` otherwise).
        assert captured["json"]["model"] == "qwen3.5:9b"
        assert captured["json"]["stream"] is False
        assert captured["json"]["think"] is False
        assert captured["json"]["options"]["temperature"] == 0.4
        assert captured["json"]["options"]["num_predict"] == 80
        assert captured["json"]["options"]["num_ctx"] == 2048
        assert captured["timeout"] == pytest.approx(12.0)

        # Prompt contains the grounding context pieces
        prompt = captured["json"]["prompt"]
        assert "software engineer" in prompt
        assert "google" in prompt.lower()
        # 'built ANT' appears in the resume highlights section
        assert "ANT" in prompt

    def test_non_200_returns_error_not_exception(self, monkeypatch):
        monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(500, {}))
        from realtime_suggestions import generate_live_suggestion

        result = generate_live_suggestion("Why did you choose that design?")
        assert result["text"] is None
        assert result["error"] == "ollama 500"

    def test_empty_response_returns_error(self, monkeypatch):
        monkeypatch.setattr("httpx.post", lambda *a, **k: _FakeResponse(200, {"response": ""}))
        from realtime_suggestions import generate_live_suggestion

        result = generate_live_suggestion("How do you scale this?")
        assert result["text"] is None
        assert result["error"] == "empty response"

    def test_ollama_down_falls_back_to_template(self, monkeypatch):
        # Without the cognitive graph in tests the template path returns
        # None — the contract is that it NEVER raises, it degrades.
        def boom(*a, **k):
            raise ConnectionError("ollama down")
        monkeypatch.setattr("httpx.post", boom)
        from realtime_suggestions import generate_live_suggestion

        result = generate_live_suggestion("Tell me about a time you led a project")
        assert result["model"] == "template-fallback"
        assert result["error"] is not None
        assert "text" in result  # may be None without the cognitive graph

    def test_model_override(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["json"] = json
            return _FakeResponse(200, {"response": "short answer"})

        monkeypatch.setattr("httpx.post", fake_post)
        from realtime_suggestions import generate_live_suggestion

        generate_live_suggestion("How do you debug prod?", model="gemma4:e4b")
        assert captured["json"]["model"] == "gemma4:e4b"


# ---------------------------------------------------------------------------
# 3. Source-level fingerprints of the nested WS-handler live-assist logic
#    (settle timer / cooldown / suggestion payload) — these functions are
#    nested inside the /ws/transcribe handler and not importable, so the
#    characterization pins the exact mechanics the mocks validated.
# ---------------------------------------------------------------------------

class TestCutFloodGuards:
    """An explicit cut is honoured — a flood of them is not.

    2026-09-12: repeated Enter presses each generated a full answer to the word
    "you" (Whisper's silence hallucination). They queued on the GPU and latency
    climbed 11.7s -> 12.6s -> 13.8s -> 14.4s until the app looked frozen.
    """

    def test_hallucinations_are_rejected_even_on_an_explicit_cut(self):
        from routes.transcription import _is_noise_text
        for junk in ("you", "You.", "Thank you.", "Sigh.", "um", "...", "  "):
            assert _is_noise_text(junk) is True, junk

    def test_a_real_short_question_still_passes_a_cut(self):
        """Cuts must stay generous: short questions are real questions."""
        from routes.transcription import _is_noise_text
        for real in ("Why Acme?", "Your biggest failure?", "Tell me more"):
            assert _is_noise_text(real) is False, real

    def test_double_taps_are_debounced(self):
        from routes.transcription import _CUT_DEBOUNCE_S
        assert 0.5 <= _CUT_DEBOUNCE_S <= 3.0

    def test_superseded_questions_never_reach_the_gpu(self):
        import inspect
        from routes import transcription as rt
        src = inspect.getsource(rt)
        # Dropping the result at delivery is not enough — the work is already
        # queued by then, delaying the answer that will actually be shown.
        assert 'if seq < _utt_state["seq"]:' in src


class TestLiveModelResidency:
    """Only one model may be hot on the live path.

    Previews and answers used different models until 2026-09-12. Both have to
    be resident to be fast, and they did not fit together in 24GB, so Ollama
    evicted and reloaded between every preview and answer: first-sentence
    latency swung between 1.5s and 6.9s with no relation to question length.
    Sharing the model removed the swap and every case came in under the gate.
    """

    def test_preview_reuses_the_committed_answer_model(self):
        from modules.ai import realtime_suggestions as rs
        assert rs._PREVIEW_MODEL == rs._LIVE_MODEL

    def test_preview_model_is_still_overridable(self):
        import inspect
        from modules.ai import realtime_suggestions as rs
        src = inspect.getsource(rs)
        assert 'ANT_PREVIEW_MODEL' in src

    def test_both_paths_hold_the_model_in_memory(self):
        import inspect
        from modules.ai import realtime_suggestions as rs
        src = inspect.getsource(rs)
        # Without keep_alive every pause in an interview costs a reload.
        assert src.count("keep_alive") >= 3


class TestFirstSentenceStreaming:
    """The gate is time-to-first-SPEAKABLE-sentence, not the whole answer."""

    def test_sentence_boundary_detection(self):
        from modules.ai.realtime_suggestions import _SENTENCE_END
        assert _SENTENCE_END.search("I led the migration. Then we scaled.")
        assert _SENTENCE_END.search("Why not? We shipped it.")
        assert not _SENTENCE_END.search("I led the migration of")

    def test_answers_carry_an_id_so_the_stream_updates_one_card(self):
        import inspect
        from routes import transcription as rt
        src = inspect.getsource(rt)
        # Without a shared id the opening sentence and the full answer render
        # as two cards showing the same thing.
        assert '"answer_id": seq' in src
        assert '"partial": True' in src and '"partial": False' in src


class TestChannelOwnership:
    """Which channel is allowed to trigger hints.

    The interviewer arrives as system audio and the candidate as mic, so a
    working system channel must own assist. But 2026-09-12 showed the danger
    of keying that on the socket existing: a system channel connected, caught
    silence (permission not granted), and suppressed the mic that had just
    transcribed all three questions perfectly. Result: no hints at all.
    Ownership follows working audio, never a mere connection.
    """

    def test_silent_system_channel_does_not_own_assist(self):
        import time as _t
        from routes import transcription as rt
        rt._DUAL_CHANNEL["system"] = 1
        rt._DUAL_CHANNEL["last_system_speech"] = 0.0  # connected, never spoke
        try:
            assert rt._system_channel_is_live() is False
        finally:
            rt._DUAL_CHANNEL["system"] = 0

    def test_system_channel_owns_assist_once_it_carries_speech(self):
        import time as _t
        from routes import transcription as rt
        rt._DUAL_CHANNEL["system"] = 1
        rt._DUAL_CHANNEL["last_system_speech"] = _t.time()
        try:
            assert rt._system_channel_is_live() is True
        finally:
            rt._DUAL_CHANNEL["system"] = 0
            rt._DUAL_CHANNEL["last_system_speech"] = 0.0

    def test_trust_expires_so_a_channel_that_dies_hands_back_the_mic(self):
        import time as _t
        from routes import transcription as rt
        rt._DUAL_CHANNEL["system"] = 1
        rt._DUAL_CHANNEL["last_system_speech"] = _t.time() - (rt._SYSTEM_TRUST_WINDOW_S + 5)
        try:
            assert rt._system_channel_is_live() is False
        finally:
            rt._DUAL_CHANNEL["system"] = 0
            rt._DUAL_CHANNEL["last_system_speech"] = 0.0

    def test_no_system_channel_means_the_mic_is_free(self):
        from routes import transcription as rt
        assert rt._DUAL_CHANNEL["system"] == 0
        assert rt._system_channel_is_live() is False


class TestWsLiveAssistSourceFingerprints:
    """Source-level freeze of backend/routes/transcription.py:449-573.

    T1 extracts these into LiveAssistService — these fingerprints make any
    semantic change a visible test failure instead of a silent regression.
    """

    @pytest.fixture(scope="class")
    def source(self):
        import inspect
        import routes.transcription as rt
        return inspect.getsource(rt)

    def test_utterance_boundaries_come_from_audio_not_transcript(self, source):
        """Re-pinned 2026-09-11 (replaces the 1.0s settle-timer fingerprint).

        Timing is taken from silence in the audio via VadSegmenter, because
        the transcript lags the audio by at least one slice — which is what
        fired hints on half-spoken questions. A head-to-head run on identical
        speech had the old path split "What is your greatest strength" into
        "What?" + "is your greatest strength.", emit "Tell me." before "Tell
        me about yourself.", and lose a third question outright.
        """
        assert "VadSegmenter()" in source
        assert "segmenter.add_chunk(chunk)" in source
        assert "target=_on_utterance" in source

    def test_settle_timer_and_cooldown_machinery_stay_deleted(self, source):
        """The repairs that existed only because boundaries were guessed.

        Each of these was a patch for not knowing where a question began and
        ended; utterance segmentation removes the need. Re-introducing any of
        them means the boundary problem came back somewhere else.
        """
        assert "threading.Timer(" not in source, "settle timer is back"
        assert "_sugg_state" not in source, "substring cooldown is back"
        assert "_arm_suggestion" not in source, "re-arming is back"
        assert "_looks_like_interview_question(tail)" not in source, \
            "starter-word guessing is back on the live path"

    def test_newer_question_wins_when_generations_race(self, source):
        """Two questions asked in quick succession can finish out of order.

        This guard is NOT a boundary repair — it is ordering, and it stays.
        """
        assert "_utt_state" in source
        # Gate on what was DELIVERED, not on what is merely known: keying it
        # on "a newer question exists" ate correct answers mid-generation.
        assert "seq <= _utt_state[\"delivered\"]" in source

    def test_generation_runs_off_loop_in_daemon_thread(self, source):
        # Generation must never block the transcription loop
        assert "threading.Thread(target=_generate, daemon=True)" in source

    def test_suggestion_payload_fields(self, source):
        # The overlay's setHint() contract
        for field in ('"type": "suggestion"', '"text"', '"question"',
                      '"model"', '"gen_ms"', '"latency_ms"',
                      '"category": "answer"', '"confidence": 0.9'):
            assert field in source, field

    def test_background_send_loop_shape__known_gap(self, source):
        # DOCUMENTED BUG pinned by eng review: the send loop swallows ALL
        # exceptions and breaks — the overlay gets no error, the pipeline
        # dies silently. T1 replaces this with a supervised send loop.
        assert "except Exception:\n                break" in source or \
            "except Exception:" in source

    def test_generate_failure_is_swallowed_not_fatal(self, source):
        # A failed generation logs and returns; it must not close the socket
        assert "suggestion generation failed" in source

    def test_suggestion_pushed_via_call_soon_threadsafe(self, source):
        # Cross-thread → event-loop handoff uses the msg_queue
        assert "call_soon_threadsafe" in source

    def test_tail_window_is_45_words(self, source):
        # The question tail is the last 45 words of the accumulated transcript
        assert "[-45:]" in source