"""Measure ANT's uploaded-audio → local AI notes → SQLite persistence path."""
import argparse
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

async def run(args):
    with tempfile.TemporaryDirectory(prefix='ant-pipeline-benchmark-') as directory:
        os.environ.update(HF_HUB_OFFLINE='1', TESTING='true', USE_SQLITE='true', FORCE_SQLITE='true',
                          ANT_SKIP_ALEMBIC='1', DATABASE_URL=f'sqlite+aiosqlite:///{directory}/notes.db')
        for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
            sys.path.insert(0, str(ROOT / relative))
        speech = load('pipeline_speech_metrics', ROOT / 'qa/performance/voice/speech.py')
        whisper = load('pipeline_whisper', ROOT / 'backend/modules/voice/whisper_handler.py')
        whisper.select_model = lambda *a, **k: 'small'
        await asyncio.to_thread(whisper.get_model, streaming=True)
        whisper.model_ready.set()
        import ai_router
        from lib.async_stream import iterate_sync
        from core import database
        # FORCE_SQLITE replaces the environment URL with the application DB.
        # Override both module URLs before creating any engine.
        database.DATABASE_URL = database.DEFAULT_SQLITE_URL = f'sqlite+aiosqlite:///{directory}/notes.db'
        from core.database import db_manager, UserRepository, ConversationRepository
        original_prompt = ai_router.build_prompt
        ai_router.build_prompt = lambda *a, **k: original_prompt(*a, **{**k, 'include_rag': False})
        await db_manager.initialize()
        rows = []
        try:
            user = await UserRepository.create('pipeline', 'pipeline@example.invalid', 'synthetic-unusable-hash')
            assert user is not None
            for iteration in range(args.runs):
                start = time.perf_counter()
                transcript = await asyncio.to_thread(whisper.transcribe_audio, str(args.audio), fast=True)
                stt_end = time.perf_counter()
                prompt = ('Return three concise action items with owner and deadline. Use only these notes, '
                          'and say unspecified for missing owners or deadlines. Notes: ' + transcript)
                parts = []
                first = None
                async for frame in iterate_sync(ai_router.ask_ollama_stream(prompt, mode='instant', model_name=args.model, temperature=0)):
                    for line in frame.splitlines():
                        if not line.startswith('data:'): continue
                        data = json.loads(line[5:])
                        if data.get('type') == 'error': raise RuntimeError(data.get('message'))
                        if data.get('content'):
                            first = first if first is not None else time.perf_counter()-start
                            parts.append(data['content'])
                ai_end = time.perf_counter()
                notes = ''.join(parts)
                messages = [{'role':'user','text':transcript}, {'role':'assistant','text':notes}]
                saved = await ConversationRepository.create(str(user.id), title='Synthetic meeting', messages=messages)
                assert saved is not None
                restored = await ConversationRepository.get_by_id(str(saved.id))
                end = time.perf_counter()
                rows.append(dict(run=iteration+1, transcription_seconds=stt_end-start,
                                 first_assistance_seconds=first, ai_seconds=ai_end-stt_end,
                                 save_read_seconds=end-ai_end, total_seconds=end-start,
                                 wer=speech.word_error_rate(speech.REFERENCES[0], transcript),
                                 required_facts_present=all(word in notes.lower() for word in ['maya','daniel','friday','budget','summary']),
                                 exact_persistence=restored is not None and restored.messages==messages,
                                 transcript=transcript, notes=notes))
            warm = rows[1:] or rows
            gates = dict(warm_pipeline_under_4s=all(r['total_seconds']<=4 for r in warm),
                         warm_first_assistance_under_3s=all(r['first_assistance_seconds'] is not None and r['first_assistance_seconds']<=3 for r in warm),
                         wer_under_15_percent=all(r['wer']<=.15 for r in rows),
                         factual_coverage=all(r['required_facts_present'] for r in rows),
                         exact_persistence=all(r['exact_persistence'] for r in rows))
            report = dict(profile={'stt':'small','ai':args.model,'mode':'instant'},gates=gates,samples=rows,
                          limits='Three repetitions of one synthetic clean-English recorded meeting; begins after capture ends. No microphone, HTTP, UI, human speech quality, or cloud provider measurement. RAG disabled. First run excluded from warm latency gates.')
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
            return 0 if all(gates.values()) else 1
        finally:
            await db_manager.close()

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio',type=Path,default=Path('/tmp/ant-product-benchmark/speech-0.aiff'))
    parser.add_argument('--model',default='qwen3.5:9b')
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.runs<1 or 'cloud' in args.model: parser.error('Use positive runs and a local model')
    raise SystemExit(asyncio.run(run(args)))
