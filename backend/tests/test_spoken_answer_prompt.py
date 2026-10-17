"""Exercise prompt construction without loading any AI providers or models."""
import ast
from pathlib import Path

import pytest


def build_prompt():
    path = Path(__file__).parents[1] / 'modules/ai/ai_router.py'
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'build_prompt')
    scope = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), scope)
    return scope['build_prompt']


@pytest.mark.parametrize('mode', ['adaptive', 'interview', 'cloud', 'universal', 'fast', 'reasoning', 'code'])
def test_spoken_answer_applies_to_every_normal_mode(mode):
    prompt = build_prompt()('How do you manage on call rotations?', mode, 'spoken', include_rag=False)
    assert 'natural spoken answer' in prompt
    assert 'Never invent personal' in prompt
    assert 'No title, tables, numbered sections' in prompt


def test_followup_context_is_retained():
    prompt = build_prompt()('Explain it in simple words', 'interview', 'spoken',
                            messages=[{'role': 'user', 'text': 'What is a Kubernetes cluster?'}], include_rag=False)
    assert 'What is a Kubernetes cluster?' in prompt
    assert 'Explain it in simple words' in prompt


def test_explicit_detailed_and_code_modes_remain_available():
    detailed = build_prompt()('Teach me', 'adaptive', 'detailed', include_rag=False)
    assert 'Use steps, examples' in detailed
    code = build_prompt()('Write Terraform', 'code', 'spoken', include_rag=False)
    assert 'unless the latest question explicitly requests code' in code
