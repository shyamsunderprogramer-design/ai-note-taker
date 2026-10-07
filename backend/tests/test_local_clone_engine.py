import json
from pathlib import Path

import pytest

from modules.voice.local_clone_engine import LocalCloneEngine


def ready_engine(tmp_path):
    engine = LocalCloneEngine(tmp_path)
    engine.python.parent.mkdir(parents=True)
    engine.python.touch()
    engine.model_dir.mkdir(parents=True)
    (engine.model_dir / "config.json").write_text('{}')
    (engine.root / "ready.json").write_text('{}')
    return engine


@pytest.mark.asyncio
async def test_inference_is_offline_and_uses_saved_reference(tmp_path, monkeypatch):
    engine = ready_engine(tmp_path)
    reference = tmp_path / 'reference.wav'
    reference.write_bytes(b'reference')
    async def run(args, timeout, stdin=None, offline=False):
        assert offline is True
        job = json.loads(stdin)
        assert job['reference_audio'] == str(reference)
        assert job['reference_text'] == 'These are my words.'
        assert job['text'] == 'New spoken words.'
        Path(job['output_file']).write_bytes(b'RIFF' + b'\0' * 100)
    monkeypatch.setattr(engine, '_run', run)
    output = await engine.synthesize(str(reference), 'These are my words.', 'New spoken words.', tmp_path / 'audio')
    assert output.exists()


@pytest.mark.asyncio
async def test_missing_engine_does_not_fall_back_to_stock_tts(tmp_path):
    with pytest.raises(ValueError, match='Install the local voice engine'):
        await LocalCloneEngine(tmp_path).synthesize('', '', 'Hello', tmp_path)


@pytest.mark.asyncio
async def test_failed_generation_removes_partial_audio(tmp_path, monkeypatch):
    engine = ready_engine(tmp_path)
    reference = tmp_path / 'ref.wav'
    reference.touch()
    async def fail(args, timeout, stdin=None, offline=False):
        Path(json.loads(stdin)['output_file']).write_bytes(b'partial')
        raise RuntimeError('model failed')
    monkeypatch.setattr(engine, '_run', fail)
    with pytest.raises(RuntimeError, match='model failed'):
        await engine.synthesize(str(reference), 'My words', 'Hello', tmp_path / 'audio')
    assert list((tmp_path / 'audio').glob('*.wav')) == []


@pytest.mark.asyncio
async def test_setup_failure_is_visible(tmp_path, monkeypatch):
    engine = LocalCloneEngine(tmp_path)
    async def fail(*args, **kwargs):
        raise RuntimeError('network unavailable')
    monkeypatch.setattr(engine, '_run', fail)
    await engine.setup()
    assert engine.status()['available'] is False
    assert engine.status()['status'] == 'error'
    assert 'network unavailable' in engine.status()['message']
