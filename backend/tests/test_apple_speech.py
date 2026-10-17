import sys
from types import SimpleNamespace
import numpy as np
import pytest
from modules.voice import apple_speech as speech


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(speech, '_failed', False)


def test_cpu_platform_does_not_load_or_download_gpu_weights(monkeypatch):
    monkeypatch.setattr(speech.platform, 'system', lambda:'Linux')
    assert speech.transcribe_cached(np.zeros(16000)) is None


def test_cached_gpu_text_rejects_noise_and_uses_local_path(monkeypatch):
    calls=[]
    monkeypatch.setattr(speech, 'cached_model_path', lambda:'/already/cached/model')
    def decode(audio, **options):
        calls.append(options)
        return {'language':'en','segments':[
            {'text':'How does Terraform state locking work?','avg_logprob':-.1},
            {'text':'invented noise','avg_logprob':-2},
        ]}
    monkeypatch.setitem(sys.modules,'mlx_whisper',SimpleNamespace(transcribe=decode))
    result=speech.transcribe_cached(np.zeros(16000))
    assert result['text']=='How does Terraform state locking work?'
    assert result['engine']=='whisper-small-mlx'
    assert calls[0]['path_or_hf_repo']=='/already/cached/model'
    assert calls[0]['temperature']==0


def test_gpu_failure_falls_back_without_repeating_a_broken_runtime(monkeypatch):
    calls=[]
    monkeypatch.setattr(speech, 'cached_model_path', lambda:'/already/cached/model')
    def fail(*args,**kwargs):
        calls.append(1)
        raise RuntimeError('Metal unavailable')
    monkeypatch.setitem(sys.modules,'mlx_whisper',SimpleNamespace(transcribe=fail))
    assert speech.transcribe_cached(np.zeros(16000)) is None
    assert speech.transcribe_cached(np.zeros(16000)) is None
    assert calls==[1]
