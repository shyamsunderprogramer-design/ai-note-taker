import sys

import pytest
import uvicorn

import start_server


@pytest.mark.parametrize('arguments,expected', [
    ([], '127.0.0.1'),
    (['--host', '192.0.2.10'], '192.0.2.10'),
])
def test_server_binding_requires_explicit_remote_host(monkeypatch, arguments, expected):
    calls = []
    monkeypatch.setattr(sys, 'argv', ['start_server.py', *arguments])
    monkeypatch.delenv('HTTPS_REQUIRED', raising=False)
    monkeypatch.setattr(uvicorn, 'run', lambda *args, **kwargs: calls.append(kwargs))
    start_server.main()
    assert len(calls) == 1
    assert calls[0]['host'] == expected
