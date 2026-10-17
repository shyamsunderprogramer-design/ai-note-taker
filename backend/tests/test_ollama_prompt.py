from types import SimpleNamespace
import pytest
from lib import ollama_prompt

@pytest.mark.parametrize('family,template,repair', [
    ('qwen35', '{{ .Prompt }}', True),
    ('qwen35', '{{.Prompt}}\n', True),
    ('qwen35', '<|im_start|>user\n{{ .Prompt }}', False),
    ('llama', '{{ .Prompt }}', False),
])
def test_only_raw_qwen_templates_are_repaired(monkeypatch, family, template, repair):
    monkeypatch.setattr(ollama_prompt, '_metadata', {})
    calls = []
    def post(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(status_code=200, json=lambda: {'details':{'family':family},'template':template})
    client = SimpleNamespace(post=post)
    payload = {'model':'qwen3.5:9b','prompt':'question','think':False,'options':{'num_ctx':2048}}
    result = ollama_prompt.prepare_text_payload(payload,client,'http://localhost:11434')
    assert bool(result.get('raw')) == repair
    assert result['model'] == payload['model']
    assert result['options'] == payload['options']
    assert payload['prompt'] == 'question'
    if repair:
        assert result['prompt'].endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n')
    ollama_prompt.prepare_text_payload(payload,client,'http://localhost:11434')
    assert len(calls) == 1

def test_other_models_and_images_are_unchanged():
    for payload in [{'model':'muse-glimmer:latest'}, {'model':'qwen3.5:cloud'}, {'model':'qwen3.5:9b','images':['image']}]:
        assert ollama_prompt.prepare_text_payload(payload,None,'unused') is payload

@pytest.mark.parametrize('model,family,start,end', [
    ('gemma4:e4b', 'gemma4', '<bos><|turn>system\n', '<|turn>model\n'),
    ('lfm2.5:latest', 'lfm2moe', '<|startoftext|><|im_start|>system\n', '<|im_start|>assistant\n'),
])
def test_other_raw_templates_use_their_own_family(monkeypatch, model, family, start, end):
    monkeypatch.setattr(ollama_prompt, '_metadata', {})
    client = SimpleNamespace(post=lambda *a, **k: SimpleNamespace(status_code=200,
        json=lambda: {'details': {'family': family}, 'template': '{{ .Prompt }}'}))
    payload = {'model': model, 'prompt': 'Question', 'options': {'num_predict': 300, 'stop': ['custom']}}
    result = ollama_prompt.prepare_text_payload(payload, client, 'local')
    assert result['model'] == model
    assert result['prompt'].startswith(start) and result['prompt'].endswith(end)
    assert 'custom' in result['options']['stop']
    assert payload['options'] == {'num_predict': 300, 'stop': ['custom']}
    if family == 'lfm2moe':
        assert result['options']['num_predict'] >= 1536

@pytest.mark.parametrize('text,expected', [
    ('<think>private analysis</think>Final answer.', 'Final answer.'),
    ('  <think>unfinished thought', ''),
    ('<|channel>thought\nprivate analysis<channel|>Answer.', 'Answer.'),
    ('Use `<think>` as a literal in this code.', 'Use `<think>` as a literal in this code.'),
    ('<div>HTML answer</div>', '<div>HTML answer</div>'),
])
def test_reasoning_filter_handles_every_chunk_boundary(text, expected):
    for size in range(1, len(text) + 1):
        parser = ollama_prompt.PublicAnswerFilter()
        actual = ''.join(parser.feed(text[i:i+size]) for i in range(0, len(text), size)) + parser.finish()
        assert actual == expected
