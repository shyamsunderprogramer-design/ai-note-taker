import httpx
import pytest
from lib.http_client import SyncHTTPClient


def test_legacy_stream_flag_uses_real_httpx_streaming():
    client = SyncHTTPClient()
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=b'data: {"ok":true}\n\n')))
    try:
        response = client.post('http://localhost/test', stream=True, skip_ssrf_check=True)
        assert list(response.iter_lines())[0] == 'data: {"ok":true}'
        response.close()
        assert client.post('http://localhost/test', stream=False, skip_ssrf_check=True).status_code == 200
    finally:
        client.close()


@pytest.mark.asyncio
async def test_openai_adapter_accepts_httpx_text_lines(monkeypatch):
    from modules.platform import cloud_providers as cloud
    response = httpx.Response(200, content=b'data: {"choices":[{"delta":{"content":"Visible answer"}}]}\n\ndata: [DONE]\n\n')
    monkeypatch.setattr(cloud, 'ask_gpt', lambda *a, **k: response)
    stream = cloud.ask_gpt_stream('question')
    frames = [frame async for frame in stream] if hasattr(stream, '__aiter__') else list(stream)
    assert any('Visible answer' in frame for frame in frames)
    assert not any('event: error' in frame for frame in frames)
    assert response.is_closed


def test_unknown_model_does_not_resolve_to_openai():
    from modules.platform.cloud_providers import get_stream_fn
    assert get_stream_fn('not-a-configured-model') is None
