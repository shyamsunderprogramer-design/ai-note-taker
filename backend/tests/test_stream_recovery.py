import asyncio
import json
import pytest
from lib.stream_recovery import recover_stream, race_recover_stream, _COOLDOWNS, compact_history
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
async def test_race_ignores_metadata_reuses_fast_answer_and_closes_loser():
    calls, closed = [], set()
    async def factory(model, prompt, history):
        calls.append(model)
        try:
            yield _frame('meta', {'model':model})
            if model == 'google-slow':
                await asyncio.sleep(1)
            yield make_content('A useful answer.')
            yield make_done(1)
        finally:
            closed.add(model)
    events = await collect(race_recover_stream('Question', ['google-slow','groq-fast'], factory))
    assert output(events) == 'A useful answer.'
    assert next(e for e in events if e['type']=='meta')['model']=='groq-fast'
    assert calls.count('groq-fast') == 1
    assert closed == {'google-slow','groq-fast'}
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_race_winner_can_recover_without_losing_partial_answer():
    calls=[]
    async def factory(model, prompt, history):
        calls.append(model)
        if model=='google-backup' and calls.count(model)==1:
            await asyncio.sleep(1)
        if model=='groq-first':
            yield make_content('First point. ')
            yield _frame('error', {'code':'transient'})
        else:
            yield make_content('Second point.')
            yield make_done(1)
    events=await collect(race_recover_stream('Question',['groq-first','google-backup'],factory))
    assert 'First point.' in output(events) and 'Second point.' in output(events)
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_race_preserves_resume_verification_and_refusal():
    async def factory(model, prompt, history):
        if model=='google-slow':
            await asyncio.sleep(1)
        yield _frame('error', {'code':'blocked','message':'Policy refusal'})
    events=await collect(race_recover_stream('Question',['groq-first','google-slow'],factory))
    assert not output(events)
    assert not any(e['type']=='recovery' for e in events)

@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['rate_limit', 'unavailable', 'transient'])
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
async def test_last_local_fallback_can_finish_after_output_limit():
    calls=[]
    async def factory(model,prompt,history):
        calls.append((model,prompt))
        if model != 'local:1b':
            yield _frame('error',{'code':'transient'})
        elif len(calls)==3:
            yield make_content('The root directory is /, ')
            yield _frame('error',{'code':'output_limit'})
        else:
            assert 'Automatic continuation' in prompt
            yield make_content('while /root is the root user’s home directory.')
            yield make_done(1)
    events=await collect(recover_stream('Explain Linux root',['groq-a','google-b','local:1b'],factory))
    assert [m for m,p in calls]==['groq-a','google-b','local:1b','local:1b']
    assert events[-1]['type']=='done'
    assert output(events).count('The root directory')==1
    assert '/root' in output(events)

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

@pytest.mark.parametrize('model', ['qa:cloud', 'qa:123b-cloud', 'ollama-cloud'])
def test_cloud_suffixes_share_cooldown_family(model):
    from lib.stream_recovery import provider_family, remember_failure, available
    assert provider_family(model) == 'ollama-cloud'
    remember_failure(model, {'code':'rate_limit'})
    assert not available('another:cloud')
    assert available('local:small')

@pytest.mark.asyncio
async def test_runtime_limit_metadata_survives_recovery():
    calls=[]
    streams={'local:small':[_frame('limits',{'context_tokens':2048,'output_tokens':300}),make_content('Complete answer.'),make_done(1)]}
    events=await collect(recover_stream('Question',list(streams),factory_for(streams,calls)))
    limits=next(e for e in events if e['type']=='limits')
    assert limits['context_tokens']==2048
    assert limits['output_tokens']==300
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_exhaustion_explains_failures_without_exposing_provider_payload():
    calls = []
    streams = {
        'openai-a': [_frame('error', {'code':'rate_limit', 'message':'secret-provider-payload'})],
        'google-b': [_frame('error', {'code':'unavailable'})],
        'local:small': [_frame('error', {'code':'transient'})],
    }
    events = await collect(recover_stream('q', list(streams), factory_for(streams, calls)))
    final = events[-1]
    assert final['type'] == 'error'
    assert 'No answer was generated' in final['message']
    assert [failure['code'] for failure in final['failures']] == ['rate_limit', 'unavailable', 'transient']
    assert 'quota' in final['message'].lower()
    assert 'secret-provider-payload' not in json.dumps(final)

@pytest.mark.asyncio
async def test_unavailable_cloud_tries_next_cloud_before_local():
    calls=[]
    streams={'groq-a':[_frame('error',{'code':'unavailable'})],
             'openai-b':[make_content('Cloud'),make_done(1)],
             'qwen3.5:9b':[make_content('Local answer'),make_done(1)]}
    events=await collect(recover_stream('q',list(streams),factory_for(streams,calls)))
    assert [c[0] for c in calls]==['groq-a','openai-b']
    assert events[-1]['type']=='done'

@pytest.mark.asyncio
async def test_metadata_cannot_extend_cloud_first_answer_deadline():
    calls = []
    closed = []
    async def factory(model, prompt, history):
        calls.append(model)
        if model == 'google-slow':
            try:
                while True:
                    yield _frame('meta', {'model': model})
                    await asyncio.sleep(.002)
            finally:
                closed.append(model)
        else:
            yield make_content('Useful answer.')
            yield make_done(1)
    frames = [frame async for frame in recover_stream('Question', ['google-slow','groq-fast'], factory,
              first_content_seconds=.02, idle_seconds=.5)]
    assert calls == ['google-slow','groq-fast']
    assert closed == ['google-slow']
    assert 'Useful answer.' in ''.join(frames)
    assert 'event: done' in frames[-1]
