"""Behaviour tests for VadSegmenter — the utterance boundary detector that
replaced transcript-settle timing on the live interview path (2026-09-11).

Synthetic audio only: a sine burst is "speech", zeros are "silence". That
keeps every assertion deterministic and hardware-free.
"""

import numpy as np
import pytest

from modules.voice.vad_segmenter import VadSegmenter

SR = 16000


def tone(ms, amp=0.2, freq=220.0):
    n = int(SR * ms / 1000)
    t = np.arange(n, dtype=np.float64) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(ms):
    return np.zeros(int(SR * ms / 1000), dtype=np.float32)


def feed(seg, audio, chunk=1024):
    """Push audio through in arbitrary chunk sizes, collecting utterances."""
    out = []
    for i in range(0, len(audio), chunk):
        out.extend(seg.add_chunk(audio[i : i + chunk]))
    return out


def ms_of(audio):
    return len(audio) / SR * 1000


class TestUtteranceBoundaries:
    def test_speech_at_connection_start_does_not_become_its_own_noise_floor(self):
        seg = VadSegmenter()
        assert feed(seg, tone(6000)) == []
        out = feed(seg, silence(1500))
        assert len(out) == 1
        assert ms_of(out[0]) >= 5900

    def test_one_question_yields_exactly_one_utterance(self):
        seg = VadSegmenter()
        out = feed(seg, np.concatenate([silence(500), tone(1200), silence(1500)]))
        assert len(out) == 1

    def test_nothing_emitted_while_speaker_is_still_talking(self):
        """The whole point: no hint fires mid-question."""
        seg = VadSegmenter()
        out = feed(seg, np.concatenate([silence(300), tone(2000)]))
        assert out == []
        assert seg.is_speaking is True

    def test_mid_sentence_pause_does_not_split_the_question(self):
        """A 500ms breath is not the end of a question (threshold is 1.0s)."""
        seg = VadSegmenter()
        audio = np.concatenate(
            [silence(300), tone(700), silence(500), tone(700), silence(1500)]
        )
        assert len(feed(seg, audio)) == 1

    def test_two_questions_separated_by_real_silence(self):
        seg = VadSegmenter()
        audio = np.concatenate(
            [silence(300), tone(800), silence(1500), tone(800), silence(1500)]
        )
        assert len(feed(seg, audio)) == 2

    def test_pure_silence_emits_nothing(self):
        seg = VadSegmenter()
        assert feed(seg, silence(4000)) == []

    def test_short_blip_is_rejected(self):
        """A door slam clears the speech-start bar but not the length bar."""
        seg = VadSegmenter()
        out = feed(seg, np.concatenate([silence(300), tone(250), silence(1500)]))
        assert out == []


class TestAudioQuality:
    def test_utterance_keeps_its_opening_syllable(self):
        """Preroll: speech is only confirmed after it has already started, so
        the frames that proved it must be prepended or the first word clips."""
        seg = VadSegmenter()
        out = feed(seg, np.concatenate([silence(500), tone(1000), silence(1500)]))
        assert ms_of(out[0]) > 1000

    def test_trailing_silence_is_trimmed(self):
        """~0.9s of proof-of-silence must not reach Whisper as decode work."""
        seg = VadSegmenter()
        out = feed(seg, np.concatenate([silence(500), tone(1000), silence(2000)]))
        assert ms_of(out[0]) < 1600

    def test_long_monologue_is_force_cut_not_buffered_forever(self):
        seg = VadSegmenter(max_utterance_ms=1000)
        out = feed(seg, np.concatenate([silence(200), tone(3000), silence(1500)]))
        assert len(out) >= 2


class TestManualCut:
    """Pressing the key means "the question ends here — answer it now".

    An explicit request must never be second-guessed: no waiting for the
    silence threshold, and no minimum-length gate. Waiting would make the key
    feel broken, and the gate would silently swallow short questions.
    """

    def test_cut_returns_speech_without_waiting_for_silence(self):
        seg = VadSegmenter()
        feed(seg, np.concatenate([silence(300), tone(1200)]))  # still talking
        cut = seg.flush(force=True)
        assert cut is not None and ms_of(cut) > 1000

    def test_cut_keeps_audio_shorter_than_the_minimum(self):
        """"Why?" is a real question and must not be dropped as a blip."""
        seg = VadSegmenter()
        feed(seg, np.concatenate([silence(300), tone(250)]))
        assert seg.flush(force=True) is not None

    def test_cut_with_nothing_buffered_returns_nothing(self):
        seg = VadSegmenter()
        assert seg.flush(force=True) is None

    def test_cut_resets_state_so_the_next_question_starts_clean(self):
        seg = VadSegmenter()
        feed(seg, np.concatenate([silence(300), tone(1200)]))
        seg.flush(force=True)
        assert seg.is_speaking is False
        assert seg.flush(force=True) is None

    def test_audio_after_a_cut_forms_a_new_utterance(self):
        seg = VadSegmenter()
        feed(seg, np.concatenate([silence(300), tone(1000)]))
        seg.flush(force=True)
        out = feed(seg, np.concatenate([tone(1000), silence(1500)]))
        assert len(out) == 1


class TestRoomNoise:
    """A fixed threshold dies in a real room.

    Measured 2026-09-11: with ambient noise above 0.015 the end-of-speech
    condition could never be satisfied, so no hint fired for an entire call
    and nothing anywhere reported a problem. The threshold has to follow the
    room, which is what makes these the highest-value tests in the file.
    """

    @staticmethod
    def _noisy(level, seed=7):
        rng = np.random.default_rng(seed)
        audio = np.concatenate([silence(400), tone(1500), silence(3000)])
        return audio + (rng.standard_normal(len(audio)) * level).astype(np.float32)

    @pytest.mark.parametrize("level", [0.0, 0.002, 0.008, 0.015, 0.02, 0.03, 0.05])
    def test_speech_still_ends_at_every_realistic_noise_level(self, level):
        seg = VadSegmenter()
        out = feed(seg, self._noisy(level))
        assert len(out) == 1, f"no hint would fire at noise {level}"

    def test_threshold_rises_with_the_room(self):
        quiet, loud = VadSegmenter(), VadSegmenter()
        feed(quiet, self._noisy(0.0))
        feed(loud, self._noisy(0.03))
        assert loud.current_threshold > quiet.current_threshold * 3

    def test_quiet_room_keeps_the_absolute_floor(self):
        """Adapting downward forever would make numeric dust read as speech."""
        seg = VadSegmenter()
        feed(seg, silence(4000))
        assert seg.current_threshold == pytest.approx(0.01)


class TestStreamMechanics:
    @pytest.mark.parametrize("chunk", [256, 1024, 1600, 4096, 7777])
    def test_result_is_independent_of_chunk_size(self, chunk):
        """WebSocket frames arrive at arbitrary sizes; re-framing must absorb
        that, or boundaries would drift with the network."""
        audio = np.concatenate([silence(400), tone(1200), silence(1500)])
        out = feed(VadSegmenter(), audio, chunk=chunk)
        assert len(out) == 1

    def test_flush_returns_speech_still_in_progress(self):
        """Recording stopped mid-question — don't silently drop it."""
        seg = VadSegmenter()
        feed(seg, np.concatenate([silence(300), tone(1200)]))
        tail = seg.flush()
        assert tail is not None and ms_of(tail) > 1000

    def test_flush_when_idle_returns_nothing(self):
        seg = VadSegmenter()
        feed(seg, silence(1000))
        assert seg.flush() is None

    def test_empty_chunks_are_harmless(self):
        seg = VadSegmenter()
        assert seg.add_chunk(np.zeros(0, dtype=np.float32)) == []
        assert seg.add_chunk(None) == []
