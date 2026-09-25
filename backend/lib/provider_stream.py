"""Validate OpenAI-compatible streams without exposing provider credentials."""
import json


class ProviderResponseError(ValueError):
    def __init__(self, message, code=None, retry_after=None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


def error_frame(error):
    from lib.sse_helpers import _frame
    payload = {'message': str(error)}
    if isinstance(error, ProviderResponseError):
        if error.code:
            payload['code'] = error.code
        if error.retry_after is not None:
            payload['retry_after'] = error.retry_after
    return _frame('error', payload)


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
    code = 'rate_limit' if status == 429 else ('unavailable' if status in (401, 402, 403, 404, 410) else 'transient')
    if status == 400:
        try:
            response.read()
            detail = json.dumps(response.json()).lower()
            if any(term in detail for term in ('context_length', 'context window', 'context length', 'too many tokens')):
                code = 'context_limit'
        except (ValueError, RuntimeError):
            pass
    retry_after = response.headers.get('retry-after')
    if retry_after:
        try:
            retry_after = float(retry_after)
        except ValueError:
            try:
                from email.utils import parsedate_to_datetime
                import time
                retry_after = max(1, parsedate_to_datetime(retry_after).timestamp() - time.time())
            except (ValueError, TypeError, OverflowError):
                retry_after = None
    raise ProviderResponseError(f'{provider} (HTTP {status}): ' + reasons.get(status, 'The provider is unavailable. Retry later.'), code, retry_after)


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
            detail = json.dumps(event['error']).lower()
            code = 'rate_limit' if any(term in detail for term in ('429', 'rate_limit', 'quota')) else 'transient'
            if any(term in detail for term in ('content_filter', 'safety', 'blocked')):
                code = 'blocked'
            raise ProviderResponseError(f'{provider}: Generation failed.', code)
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
            raise ProviderResponseError(f'{provider}: The answer reached its output limit and is incomplete. Ask a narrower question or choose Detailed.', 'output_limit')
        if reason and reason != 'stop':
            raise ProviderResponseError(f'{provider}: The provider could not complete a text answer ({reason if reason in {"content_filter", "tool_calls", "function_call"} else "interrupted"}).', 'blocked' if reason == 'content_filter' else 'transient')
        if reason == 'stop':
            completed = True
    if not completed:
        raise ProviderResponseError(f'{provider}: The connection ended before the answer completed. Please retry.')
    if not has_text:
        raise ProviderResponseError(f'{provider}: The model returned no answer. Try another model.')


def _events(response, provider):
    check_provider_status(response, provider)
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')
        if not line.startswith('data:'):
            continue
        try:
            yield json.loads(line[5:])
        except ValueError:
            raise ProviderResponseError(f'{provider}: Invalid stream data.', 'transient') from None


def anthropic_content(response, provider='Anthropic'):
    completed = False
    has_text = False
    for event in _events(response, provider):
        if event.get('type') == 'error':
            detail = json.dumps(event.get('error', {})).lower()
            raise ProviderResponseError(f'{provider}: Generation failed.', 'rate_limit' if 'rate_limit' in detail else 'transient')
        delta = event.get('delta') or {}
        if event.get('type') == 'content_block_delta' and delta.get('type') == 'text_delta':
            text = delta.get('text', '')
            has_text = has_text or bool(text.strip())
            yield text
        reason = delta.get('stop_reason')
        if reason == 'max_tokens':
            raise ProviderResponseError(f'{provider}: Output limit reached.', 'output_limit')
        if reason in ('end_turn', 'stop_sequence'):
            completed = True
        elif reason:
            raise ProviderResponseError(f'{provider}: Text answer stopped.', 'blocked' if reason == 'refusal' else 'transient')
    if not completed or not has_text:
        raise ProviderResponseError(f'{provider}: Incomplete answer.', 'transient')


def gemini_content(response, provider='Google'):
    completed = False
    has_text = False
    for event in _events(response, provider):
        if event.get('promptFeedback', {}).get('blockReason'):
            raise ProviderResponseError(f'{provider}: Request blocked.', 'blocked')
        if event.get('error'):
            detail = json.dumps(event['error']).lower()
            raise ProviderResponseError(f'{provider}: Generation failed.', 'rate_limit' if any(x in detail for x in ('429', 'quota', 'resource_exhausted')) else 'transient')
        for candidate in event.get('candidates', []):
            for part in candidate.get('content', {}).get('parts', []):
                if part.get('text') and not part.get('thought'):
                    has_text = has_text or bool(part['text'].strip())
                    yield part['text']
            reason = candidate.get('finishReason')
            if reason == 'MAX_TOKENS':
                raise ProviderResponseError(f'{provider}: Output limit reached.', 'output_limit')
            if reason == 'STOP':
                completed = True
            elif reason:
                code = 'blocked' if reason in ('SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII', 'RECITATION', 'IMAGE_SAFETY') else 'transient'
                raise ProviderResponseError(f'{provider}: Text answer stopped.', code)
    if not completed or not has_text:
        raise ProviderResponseError(f'{provider}: Incomplete answer.', 'transient')
