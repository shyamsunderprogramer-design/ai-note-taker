"""Audio turn boundaries, not guessed word counts, determine text ownership."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture
def speech(monkeypatch):
    path = Path(__file__).parents[1] / 'modules/voice/vibevoice_diarizer.py'
    spec = importlib.util.spec_from_file_location('qa_turn_alignment', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    decoded = []
    files = []
    engine = SimpleNamespace(available=False)

    def transcribe(samples, **kwargs):
        decoded.append(samples.copy())
        return {'text': f'turn-{round(float(samples[0]))}'}

    class Detector:
        def identify_speaker(self, samples):
            return f'Speaker {round(float(samples[0]))}'

    monkeypatch.setitem(sys.modules, 'modules.voice.speaker_diarization',
        SimpleNamespace(get_diarizer=lambda: engine, SimpleSpeakerDetector=Detector))
    monkeypatch.setitem(sys.modules, 'modules.voice.whisper_handler',
        SimpleNamespace(transcribe=transcribe))
    monkeypatch.setitem(sys.modules, 'soundfile',
        SimpleNamespace(write=lambda filename, *args: files.append(Path(filename))))
    return module.VibeVoiceDiarizer(), engine, decoded, files, module


def test_acoustic_turns_keep_their_own_words_and_short_tail(speech):
    diarizer, _, decoded, _, _ = speech
    audio = np.concatenate([np.ones(48000), np.full(51200, 2)])
    segments = diarizer._transcribe_pyannote_fallback(audio, 16000)
    assert [(s.speaker_id, s.text) for s in segments] == [
        ('Speaker 1', 'turn-1'), ('Speaker 2', 'turn-2')]
    assert [len(chunk) for chunk in decoded] == [48000, 51200]
    assert [(s.start_time, s.end_time) for s in segments] == [(0, 3), (3, 6.2)]


def test_consecutive_same_speaker_needs_only_one_transcription(speech):
    diarizer, _, decoded, _, _ = speech
    segments = diarizer._transcribe_pyannote_fallback(np.ones(144000), 16000)
    assert len(segments) == len(decoded) == 1
    assert len(decoded[0]) == 144000


def test_pyannote_labels_and_audio_boundaries_are_preserved(speech):
    diarizer, engine, decoded, files, module = speech
    engine.available = True
    engine.diarize_audio = lambda _: [module.SpeakerSegment('Panelist B', 1, 2, ''),
                                      module.SpeakerSegment('Candidate', 0, 1, '')]
    audio = np.concatenate([np.ones(16000), np.full(16000, 2)])
    segments = diarizer._transcribe_pyannote_fallback(audio, 16000)
    assert [(s.speaker_id, s.text) for s in segments] == [
        ('Candidate', 'turn-1'), ('Panelist B', 'turn-2')]
    assert all(len(chunk) == 16000 for chunk in decoded)
    assert files and not files[0].parent.exists()


def test_empty_audio_does_not_run_transcription(speech):
    diarizer, _, decoded, _, _ = speech
    assert diarizer._transcribe_pyannote_fallback(np.array([]), 16000) == []
    assert decoded == []


def test_unavailable_asr_preserves_empty_placeholder_without_claiming_speech(speech, monkeypatch):
    diarizer, _, _, _, _ = speech
    calls = []
    def unavailable(samples, **kwargs):
        calls.append(len(samples))
        return {'text': ''}
    monkeypatch.setitem(sys.modules, 'modules.voice.whisper_handler',
                        SimpleNamespace(transcribe=unavailable))
    segments = diarizer._transcribe_pyannote_fallback(np.ones(16000), 16000)
    assert calls == [16000]
    assert len(segments) == 1
    assert segments[0].text == '' and segments[0].confidence == 0


def test_resampling_preserves_original_turn_timestamps(speech):
    diarizer, _, decoded, _, _ = speech
    segments = diarizer._transcribe_pyannote_fallback(np.ones(24000), 8000)
    assert len(decoded[0]) == 48000
    assert segments[0].start_time == 0 and segments[0].end_time == 3


def test_temporary_audio_cleanup_after_diarizer_error(speech):
    diarizer, engine, _, files, _ = speech
    engine.available = True
    def fail(_):
        raise RuntimeError('synthetic-private-audio-path')
    engine.diarize_audio = fail
    assert diarizer._transcribe_pyannote_fallback(np.ones(16000), 16000) is None
    assert files and not files[0].parent.exists()
