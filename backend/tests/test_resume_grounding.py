import json
import pytest
from lib.resume_grounding import ResumeGrounding
from lib.sse_helpers import make_content, make_done


def prompt(resume):
    return '[Resume answer context]\nResume data (JSON string): '+json.dumps(resume)+'\nQuestion: Describe your experience.'


def test_evidence_excludes_jd_and_history_and_preserves_hypotheticals():
    gate = ResumeGrounding(prompt('I reduced latency from 900 to 120 milliseconds.')+'\nJob description: 12 milliseconds')
    assert gate.unsupported('I reduced latency from 900 to 12 milliseconds.') == {'12'}
    assert not gate.unsupported('I reduced latency from 900 to 120 milliseconds.')
    assert not gate.unsupported('I would investigate requests taking 12 milliseconds.')


@pytest.mark.asyncio
async def test_bad_measurement_is_withheld_and_repaired_once():
    calls = []
    async def create(query, history):
        calls.append((query, history))
        yield make_content('I reduced latency to '+('12' if len(calls)==1 else '120')+' milliseconds.')
        yield make_done(1)
    gate = ResumeGrounding(prompt('I reduced latency to 120 milliseconds.'))
    frames = [frame async for frame in gate.stream(create, prompt(gate.resume), [{'role':'assistant','text':'12 milliseconds'}])]
    assert len(calls) == 2
    assert calls[1][1] == []
    assert '120 milliseconds' in ''.join(frames)
    assert '12 milliseconds' not in ''.join(frames)


@pytest.mark.asyncio
async def test_repeated_bad_measurement_fails_without_leaking_or_looping():
    calls = []
    async def create(query, history):
        calls.append(query)
        yield make_content('I improved latency to 20 milliseconds.')
        yield make_done(1)
    gate = ResumeGrounding(prompt('I improved latency to 200 milliseconds.'))
    frames = [frame async for frame in gate.stream(create, prompt(gate.resume), [])]
    assert len(calls) == 2
    assert '20 milliseconds' not in ''.join(frames)
    assert 'grounding' in ''.join(frames)


@pytest.mark.parametrize('answer,unsupported', [
    ('I built the API. Latency fell from 90 to 120 milliseconds.', {'90'}),
    ('I improved throughput by 75%.', {'75'}),
    ('I would consider a 30 second timeout.', set()),
    ('I added Redis. For example, a cache could expire in 30 seconds.', set()),
])
def test_numeric_edge_cases(answer, unsupported):
    gate = ResumeGrounding(prompt('I reduced latency from 900 to 120 milliseconds.'))
    assert gate.unsupported(answer) == unsupported


@pytest.mark.asyncio
async def test_cancellation_during_verification_closes_provider():
    import asyncio
    closed = asyncio.Event()
    entered = asyncio.Event()
    async def create(query, history):
        try:
            entered.set()
            await asyncio.sleep(10)
            yield make_content('unused')
        finally:
            closed.set()
    gate = ResumeGrounding(prompt('I reduced latency to 120 milliseconds.'))
    async def consume():
        return [frame async for frame in gate.stream(create, prompt(gate.resume), [])]
    task = asyncio.create_task(consume())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
    assert gate.repairs == 0

def test_collaboration_does_not_support_claiming_leadership():
    import json
    from lib.resume_grounding import ResumeGrounding
    guard=ResumeGrounding('Resume data (JSON string): '+json.dumps('Built Python APIs and collaborated with a four-person team.'))
    assert guard.unsupported('I led efforts to build APIs.')
    assert not guard.unsupported('I built Python APIs and collaborated with the team.')


@pytest.mark.asyncio
async def test_checked_sentence_is_visible_before_provider_finishes():
    import asyncio
    visible = asyncio.Event()
    async def create(query, history):
        yield make_content('A cluster is a group of computers working together. ')
        await asyncio.wait_for(visible.wait(), .2)
        yield make_content('Worker nodes run the applications.')
        yield make_done(1)
    gate = ResumeGrounding(prompt('Built Python APIs.'))
    frames = []
    async for frame in gate.stream(create, prompt(gate.resume), []):
        frames.append(frame)
        if 'event: chunk' in frame:
            visible.set()
    assert visible.is_set()
    assert ''.join(json.loads(line[5:]).get('content', '') for frame in frames
                   for line in frame.splitlines() if line.startswith('data:')) == (
        'A cluster is a group of computers working together. Worker nodes run the applications.')


@pytest.mark.asyncio
async def test_early_number_is_not_released_before_later_personal_context():
    async def create(query, history):
        yield make_content('Latency reached 12 milliseconds. ')
        yield make_content('I built the API.')
        yield make_done(1)
    gate = ResumeGrounding(prompt('Built Python APIs with latency of 120 milliseconds.'))
    frames = [frame async for frame in gate.stream(create, prompt(gate.resume), [])]
    assert '12 milliseconds' not in ''.join(frames)
    assert 'grounding' in ''.join(frames)


@pytest.mark.asyncio
async def test_repair_continues_after_verified_opening_without_replaying_it():
    calls = []
    async def create(query, history):
        calls.append(query)
        if len(calls) == 1:
            yield make_content('I built Python APIs. ')
            yield make_content('I reduced latency to 12 milliseconds.')
        else:
            assert 'Output only the remaining answer' in query
            yield make_content('I reduced latency to 120 milliseconds.')
        yield make_done(1)
    gate = ResumeGrounding(prompt('Built Python APIs. Reduced latency to 120 milliseconds.'))
    frames = [frame async for frame in gate.stream(create, prompt(gate.resume), [])]
    answer = ''.join(json.loads(line[5:]).get('content', '') for frame in frames
                     for line in frame.splitlines() if line.startswith('data:'))
    assert answer == 'I built Python APIs. I reduced latency to 120 milliseconds.'

@pytest.mark.parametrize('answer,invalid', [
    ('In my recent roles, I orchestrated applications using EKS and AKS.', True),
    ('I have extensive experience with Kubernetes and Docker.', True),
    ('I would deploy containers using Kubernetes and Docker.', False),
    ('Kubernetes manages containerized applications.', False),
])
def test_technology_experience_requires_resume_evidence(answer, invalid):
    gate = ResumeGrounding(prompt('Built Python APIs and collaborated with operations.'))
    assert bool(gate.unsupported(answer)) == invalid


def test_technology_aliases_in_resume_support_a_matching_claim():
    gate = ResumeGrounding(prompt('Deployed services using Azure Kubernetes Service and ArgoCD.'))
    assert not gate.unsupported('I deployed services using AKS and Argo CD.')
