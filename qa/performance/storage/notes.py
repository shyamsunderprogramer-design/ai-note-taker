"""Synthetic note persistence benchmark using ANT's real SQLite repositories."""
import argparse
import asyncio
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

async def run(output):
    with tempfile.TemporaryDirectory(prefix='ant-notes-benchmark-') as directory:
        os.environ.update(DATABASE_URL=f'sqlite+aiosqlite:///{directory}/notes.db',
                          USE_SQLITE='true', FORCE_SQLITE='true', TESTING='true', ANT_SKIP_ALEMBIC='1')
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'backend'))
        from core import database
        # FORCE_SQLITE replaces the environment URL with the application DB.
        # Override both module URLs before creating any engine.
        database.DATABASE_URL = database.DEFAULT_SQLITE_URL = f'sqlite+aiosqlite:///{directory}/notes.db'
        from core.database import db_manager, UserRepository, ConversationRepository
        await db_manager.initialize()
        samples = []
        expected = {}
        try:
            user = await UserRepository.create('benchmark_user', 'benchmark@example.invalid', 'synthetic-not-a-login-hash')
            assert user is not None
            user_id = str(user.id)
            for i in range(30):
                messages = [{'role': 'user', 'text': f'Synthetic meeting {i}: Send the summary by Friday. ' * 40},
                            {'role': 'assistant', 'text': 'Maya: review budget. Daniel: schedule next meeting.'}]
                start = time.perf_counter()
                saved = await ConversationRepository.create(user_id, title=f'Benchmark {i}', messages=messages)
                write_ms = (time.perf_counter()-start)*1000
                assert saved is not None
                start = time.perf_counter()
                loaded = await ConversationRepository.get_by_id(str(saved.id))
                read_ms = (time.perf_counter()-start)*1000
                assert loaded is not None and loaded.messages == messages
                expected[str(saved.id)] = messages
                samples.append(dict(write_ms=write_ms, read_ms=read_ms))
            await db_manager.close()
            await db_manager.initialize()
            after_restart = await ConversationRepository.get_by_user(user_id)
            persisted = {str(note.id):note.messages for note in after_restart} == expected
            def p95(key): return sorted(s[key] for s in samples)[math.ceil(.95*len(samples))-1]
            metrics = dict(write_p95_ms=p95('write_ms'), read_p95_ms=p95('read_ms'), notes=len(samples),
                           persisted_after_reopen=persisted)
            gates = dict(write_under_50ms=metrics['write_p95_ms']<=50, read_under_20ms=metrics['read_p95_ms']<=20,
                         exact_roundtrip_after_reopen=persisted)
            report = dict(metrics=metrics, gates=gates, samples=samples,
                          limits='Single user, sequential temporary local SQLite; no network, UI, search ranking, or concurrent writers.')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps({k:v for k,v in report.items() if k!='samples'}, indent=2))
            return 0 if all(gates.values()) else 1
        finally:
            await db_manager.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(asyncio.run(run(parser.parse_args().output)))
