"""Validate OpenAI-compatible streams without exposing provider credentials."""
import json


class ProviderResponseError(ValueError):
    pass


def check_provider_status(response, provider):
    status = response.status_code
    if status == 200:
        return
    reasons = {
        400: 'The provider rejected the model or request settings.',
        401: 'The provider rejected its API key. Check the configured key.',
        402: 'The provider requires billing or additional credits.',
        403: 'The API key does not have permission for this request.',
        404: 'This model is unavailable. Select a supported model.',
        410: 'This model has been retired. Select a supported model.',
        429: 'The provider rate or quota limit was reached. Retry later or select another provider.',
    }
    # Never include a raw response or URL: some providers echo credentials.
    raise ProviderResponseError(f'{provider} (HTTP {status}): ' + reasons.get(status, 'The provider is unavailable. Retry later.'))


def chat_content(response, provider):
    """Yield only answer text; require a successful terminal event."""
    check_provider_status(response, provider)
    completed = False
    has_text = False
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            completed = True
            break
        try:
            event = json.loads(data)
        except ValueError:
            raise ProviderResponseError(f'{provider}: Invalid response data. Please retry.') from None
        if event.get('error'):
            raise ProviderResponseError(f'{provider}: Generation failed. Please retry or select another provider.')
        choices = event.get('choices') or []
        if not choices:
            continue  # Usage-only frames carry no answer.
        choice = choices[0]
        content = choice.get('delta', {}).get('content')
        if isinstance(content, str) and content:
            has_text = has_text or bool(content.strip())
            yield content
        reason = choice.get('finish_reason')
        if reason == 'length':
            raise ProviderResponseError(f'{provider}: The answer reached its output limit and is incomplete. Ask a narrower question or choose Detailed.')
        if reason and reason != 'stop':
            raise ProviderResponseError(f'{provider}: The provider could not complete a text answer ({reason if reason in {"content_filter", "tool_calls", "function_call"} else "interrupted"}).')
        if reason == 'stop':
            completed = True
    if not completed:
        raise ProviderResponseError(f'{provider}: The connection ended before the answer completed. Please retry.')
    if not has_text:
        raise ProviderResponseError(f'{provider}: The model returned no answer. Try another model.')
