"""Local provider failures should return the available fallback without crashing."""
from types import SimpleNamespace
from pathlib import Path


def test_live_provider_failure_returns_suggestion_content(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'core'))
    import httpx
    from modules.ai import realtime_suggestions as live

    def unavailable(*args, **kwargs):
        raise httpx.ConnectError('local test provider unavailable')

    monkeypatch.setattr(httpx, 'post', unavailable)
    monkeypatch.setattr(live.realtime_engine, 'process_segment',
                        lambda *args: SimpleNamespace(content='Describe your own example and result.'))
    result = live.generate_live_suggestion('Tell me about a difficult project')
    assert result['text'] == 'Describe your own example and result.'
