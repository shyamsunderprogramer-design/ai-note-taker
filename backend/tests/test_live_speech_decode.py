"""Regression checks for bounded live decoding and low-confidence noise."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest

@pytest.fixture
def speech(monkeypatch):
    path=Path(__file__).parents[1]/'modules/voice/whisper_handler.py'
    spec=importlib.util.spec_from_file_location('isolated_live_decode',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.model_ready.set()
    monkeypatch.setattr(module, '_accelerated_transcribe', lambda *args: None)
    return module

def test_live_decode_has_no_temperature_retry_loop(speech,monkeypatch):
    calls=[]
    def decode(audio,**options):
        calls.append(options)
        return iter([SimpleNamespace(text='How does Terraform state locking work?',avg_logprob=-.2,no_speech_prob=.01,compression_ratio=1.2)]),SimpleNamespace(language='en')
    monkeypatch.setattr(speech,'get_model',lambda *a,**k:SimpleNamespace(transcribe=decode))
    assert 'Terraform' in speech.transcribe(np.zeros(16000),streaming=True)['text']
    assert calls[0]['temperature']==0.0
    assert calls[0]['beam_size']==1

def test_accelerated_live_decode_does_not_wait_for_cpu_warmup(speech,monkeypatch):
    monkeypatch.setattr(speech, '_accelerated_transcribe', lambda *args:{'text':'How does Terraform work?','engine':'whisper-small-mlx'})
    monkeypatch.setattr(speech, 'wait_for_model', lambda **kwargs:pytest.fail('GPU speech must not wait for CPU'))
    assert speech.transcribe(np.zeros(16000), streaming=True)['engine']=='whisper-small-mlx'

@pytest.mark.parametrize('prob,ratio,silence',[(-2,1,.01),(-.2,4,.01),(-.5,1,.95)])
def test_uncertain_or_repetitive_audio_does_not_become_a_question(speech,monkeypatch,prob,ratio,silence):
    segment=SimpleNamespace(text='Ch-ch-chchatlatatexsss unrelated invented words',avg_logprob=prob,no_speech_prob=silence,compression_ratio=ratio)
    monkeypatch.setattr(speech,'get_model',lambda *a,**k:SimpleNamespace(transcribe=lambda *a,**k:(iter([segment]),SimpleNamespace(language='en'))))
    assert speech.transcribe(np.zeros(16000),streaming=True)['text']==''
