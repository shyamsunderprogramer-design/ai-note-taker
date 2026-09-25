import asyncio
import json
import pytest
from lib.stream_recovery import recover_stream, _COOLDOWNS, compact_history
from lib.sse_helpers import make_content, make_done, _frame

@pytest.fixture(autouse=True)
def clean():
    _COOLDOWNS.clear()
    yield
    _COOLDOWNS.clear()


def factory_for(streams, calls):
    async def factory(model, prompt, history):
        calls.append((model, prompt, history))
        for event in streams[model]:
            if isinstance(event, Exception):
                raise event
            yield event
    return factory

async def collect(stream):
    return [json.loads(line[5:]) async for frame in stream for line in frame.splitlines() if line.startswith('data:')]

def output(events):
    return ''.join(e.get('content', '') for e in events)

@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['rate_limit', 'transient', 'unavailable'])
@pytest.mark.parametrize('partial', ['', 'Cedar is $1,400 over budget.'])
async def test_failover_preserves_question_resume_jd_and_partial(kind, partial):
    calls=[]
    streams={'groq-first': [make_content(partial), _frame('error',{'code':kind})],
             'openai-backup':[make_content('Maple is $300 under budget.'),make_done(1)]}
    q='Question with Resume: Alex. JD: Python.'
    events=await collect(recover_stream(q,list(streams),factory_for(streams,calls)))
    assert events[-1]['type']=='done'
    assert partial in output(events) and 'Maple' in output(events)
    assert calls[1][1].startswith(q)
    if partial: assert partial in calls[1][1]
    assert any(e['type']=='recovery' for e in events)

@pytest.mark.asyncio
async def test_output_limit_continues_same_model_once_then_local():
    calls=[]
    async def factory(model,prompt,history):
        calls.append(model)
        yield make_content('First sentence. ' if len(calls)==1 else 'More detail. ')
        yield _frame('error',{'code':'output_limit'}) if model!='local:1b' else make_done(1)
    events=await collect(recover_stream('question',['groq-fast','openai-backup','local:1b'],factory))
    assert calls==['groq-fast','groq-fast','local:1b']
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_retry_after_skips_entire_provider_account_on_next_question():
    calls=[]
    streams={'groq-first':[_frame('error',{'code':'rate_limit','retry_after':120})],
             'openai-backup':[make_content('Answer'),make_done(1)]}
    await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    calls.clear()
    events=await collect(recover_stream('q',['groq-other','openai-backup'],factory_for(streams,calls)))
    assert [c[0] for c in calls]==['openai-backup']
    assert events[0]['type']=='recovery' and events[0]['reason']=='cooldown'

@pytest.mark.asyncio
async def test_three_attempts_max_and_partial_survives_all_failures():
    calls=[]
    streams={m:[make_content('Partial.'),_frame('error',{'code':'transient'})] for m in ['groq-a','openai-b','local:1b','google-c']}
    events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    assert len(calls)==3 and calls[-1][0]=='local:1b'
    assert events[-1]['type']=='error' and events[-1]['incomplete']
    assert output(events).startswith('Partial.')
    assert not any(e['type']=='done' for e in events)

@pytest.mark.asyncio
async def test_policy_failure_is_not_retried():
    calls=[]
    streams={'groq-a':[_frame('error',{'code':'blocked'})], 'openai-b':[make_content('bad'),make_done(1)]}
    events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    assert len(calls)==1 and events[-1]['type']=='error'

@pytest.mark.asyncio
async def test_empty_done_cannot_complete_partial_answer():
    calls=[]
    streams={'groq-a':[make_content('Partial'),_frame('error',{'code':'transient'})], 'openai-b':[make_done(1)]}
    events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    assert events[-1]['type']=='error'

@pytest.mark.asyncio
async def test_eof_and_exception_recover():
    for ending in [[],[RuntimeError('secret')]]:
        calls=[]
        streams={'groq-a':[make_content('Partial.'),*ending], 'openai-b':[make_content('Finished.'),make_done(1)]}
        events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
        assert events[-1]['type']=='done' and 'secret' not in str(events)

@pytest.mark.asyncio
async def test_exact_duplicate_opening_split_across_chunks_removed():
    calls=[]
    first='I built Python APIs at Acme.'
    streams={'groq-a':[make_content(first),_frame('error',{'code':'transient'})],
             'openai-b':[make_content('I built Python '),make_content('APIs at Acme. I also used Redis.'),make_done(1)]}
    events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    assert output(events).count(first)==1 and 'Redis' in output(events)

@pytest.mark.asyncio
async def test_context_limit_drops_old_history_not_question():
    calls=[]
    async def factory(model,prompt,history):
        calls.append((prompt,history))
        if len(calls)==1: yield _frame('error',{'code':'context_limit'})
        else:
            yield make_content('Answer')
            yield make_done(1)
    events=await collect(recover_stream('Full resume and JD',['groq-a'],factory,[{'role':'user','text':'Old'}]))
    assert calls[1]==('Full resume and JD',[])
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_idle_timeout_recovers_and_overall_deadline_stops():
    closed=[]
    async def factory(model,prompt,history):
        if model=='groq-a':
            try: await asyncio.sleep(1)
            finally: closed.append(model)
        else:
            yield make_content('Backup')
            yield make_done(1)
    events=await collect(recover_stream('q',['groq-a','openai-b'],factory,idle_seconds=.01))
    assert closed==['groq-a'] and events[-1]['type']=='done'
    events=await collect(recover_stream('q',['groq-a','openai-b'],factory,deadline_seconds=.001))
    assert events[-1]['type']=='error'

@pytest.mark.asyncio
async def test_cancellation_closes_stream_without_starting_backup():
    calls=[]; started=asyncio.Event(); closed=asyncio.Event()
    async def factory(model,prompt,history):
        calls.append(model); started.set()
        try:
            await asyncio.sleep(10)
            yield make_content('Too late')
        finally: closed.set()
    task=asyncio.create_task(collect(recover_stream('q',['groq-a','openai-b'],factory)))
    await started.wait(); task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert closed.is_set() and calls==['groq-a']

def test_history_budget_keeps_recent_correction():
    history=compact_history([{'role':'user','text':'x'*9000},{'role':'user','text':'Actually Tuesday'}])
    assert history==[{'role':'user','text':'Actually Tuesday'}]
