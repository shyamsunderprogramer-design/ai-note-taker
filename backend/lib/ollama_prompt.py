"""Repair known raw-only local chat templates without changing installed models.

Text-only non-thinking framing follows the model publisher's chat template:
https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/chat_template.jinja
https://huggingface.co/google/gemma-4-E4B-it/blob/main/chat_template.jinja
https://huggingface.co/LiquidAI/LFM2.5-8B-A1B/blob/main/chat_template.jinja
"""
import re
import time

_metadata = {}

_GROUNDING = (
    "Answer only the latest question. Use general knowledge for definitions and technical explanations; "
    "no resume is needed to explain a technology. "
    "Only personal biographical claims must be supported by the supplied resume. "
    "If a requested credential or date is unlisted, answer My resume does not specify that detail, then stop. "
    "Never conclude someone lacks a credential merely because it is unlisted. "
    "Never invent owners, deadlines, task ordering, or completed actions. "
    "Prior assistant replies are drafts, not evidence. "
    "Meeting summaries are extraction tasks: do not add agreement, reasons, or implied promises. "
    "Preserve whether each statement is a proposal, decision, pending task, or completed action. "
    "Only explicit requests or commitments are action items. Needing information is not an assigned task. "
    "Do not list completed work as pending. If no explicit actions or decisions exist, say none. "
    "For action items, use a separate entry for each task with its own owner and deadline. "
    "If an owner or deadline is not stated for that task, label it unspecified. "
    "Stop when the requested information has been covered."
)



def prepare_text_payload(payload, client, base_url):
    model = payload.get('model', '')
    expected = {'qwen3.5': 'qwen35', 'gemma4': 'gemma4', 'lfm2.5': 'lfm2moe'}
    family = expected.get(model.split(':')[0])
    if not family or 'cloud' in model or payload.get('images') or payload.get('raw'):
        return payload
    key = (base_url, model)
    cached = _metadata.get(key)
    if cached is None or time.monotonic() - cached[0] > 60:
        try:
            response = client.post(f'{base_url}/api/show', json={'model': model},
                                   timeout=2, skip_ssrf_check=True)
            info = response.json() if response.status_code == 200 else {}
            raw_only = (info.get('details', {}).get('family') == family
                        and re.fullmatch(r'\s*{{\s*\.Prompt\s*}}\s*', info.get('template', '')) is not None)
        except Exception:
            raw_only = False
        cached = (time.monotonic(), raw_only)
        _metadata[key] = cached
    if not cached[1]:
        return payload
    if family == 'gemma4':
        return {**payload, 'raw': True,
                'prompt': '<bos><|turn>system\n' + _GROUNDING
                          + '<turn|>\n<|turn>user\n' + payload['prompt']
                          + '<turn|>\n<|turn>model\n',
                'options': {**payload.get('options', {}),
                            'stop': list(dict.fromkeys(payload.get('options', {}).get('stop', [])
                                                      + ['<turn|>', '<eos>']))}}
    if family == 'lfm2moe':
        # This is a reasoning model. Its thought tokens consume the generation
        # budget too; the public-answer filter keeps them out of the response.
        options = payload.get('options', {})
        return {**payload, 'raw': True,
                'prompt': '<|startoftext|><|im_start|>system\n' + _GROUNDING
                          + '<|im_end|>\n<|im_start|>user\n' + payload['prompt']
                          + '<|im_end|>\n<|im_start|>assistant\n',
                'options': {**options, 'num_predict': max(options.get('num_predict', 300), 1536),
                            'num_ctx': max(options.get('num_ctx', 2048), 4096),
                            'stop': list(dict.fromkeys(options.get('stop', []) + ['<|im_end|>']))}}
    return {**payload, 'raw': True,
            'prompt': '<|im_start|>system\n' + _GROUNDING
                      + '<|im_end|>\n<|im_start|>user\n' + payload['prompt']
                      + '<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'}


class PublicAnswerFilter:
    """Remove a leading reasoning channel even when its tags span chunks.

    Only the start of the response is interpreted; literal tags in an answer
    or code sample are preserved. An unfinished thought never becomes an answer.
    """
    tags = {'<think>': '</think>', '<|channel>thought\n': '<channel|>'}

    def __init__(self):
        self.pending = ''
        self.closing = None
        self.public = False

    def feed(self, text):
        if self.public:
            return text
        self.pending += text
        if self.closing:
            end = self.pending.find(self.closing)
            if end < 0:
                self.pending = self.pending[-(len(self.closing) - 1):]
                return ''
            result = self.pending[end + len(self.closing):].lstrip()
            self.pending = ''
            self.public = True
            return result
        candidate = self.pending.lstrip()
        for opening, closing in self.tags.items():
            if candidate.startswith(opening):
                self.closing = closing
                self.pending = candidate[len(opening):]
                return self.feed('')
        if not candidate or any(tag.startswith(candidate) for tag in self.tags):
            return ''
        self.public = True
        result, self.pending = self.pending, ''
        return result

    def finish(self):
        if self.closing:
            return ''
        result, self.pending = self.pending, ''
        return result
