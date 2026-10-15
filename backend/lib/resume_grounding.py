"""Bounded verification of numeric and explicit leadership claims against resume data.

These are targeted consistency checks, not proof that every sentence is factual.
Only the app's explicit JSON resume field is evidence; JD/history are excluded.
"""
import json
import re
from contextlib import aclosing
from lib.sse_helpers import _frame

_MEASUREMENT = re.compile(r'(?<![\w.])(\d+(?:[,.]\d+)*)\s*(milliseconds?|ms|seconds?|minutes?|hours?|years?|percent|%|requests?\s+per\s+second)(?!\w)', re.I)
_PERSONAL_PAST = re.compile(r'\b(?:I|we)\s+(?:\w+\s+){0,3}(?:built|added|reduced|improved|achieved|implemented|led|delivered|measured|tested|increased|decreased|orchestrated|deployed|integrated|used|managed)\b|\b(?:my|our)\s+(?:experience|work|project|team|background|recent roles)\b|\bI\s+have\s+(?:\w+\s+){0,3}experience\b', re.I)
_TECHNOLOGIES = {
    'EKS': r'\bEKS\b|Amazon Elastic Kubernetes Service',
    'AKS': r'\bAKS\b|Azure Kubernetes Service',
    'Argo CD': r'\bArgo\s*CD\b', 'Flux': r'\bFlux(?:CD)?\b',
    'PagerDuty': r'\bPagerDuty\b', 'Terraform': r'\bTerraform\b',
    'Docker': r'\bDocker\b', 'Kubernetes': r'\bKubernetes\b|\bk8s\b',
}


def resume_from_prompt(prompt):
    marker = 'Resume data (JSON string): '
    if marker not in prompt:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(prompt.split(marker, 1)[1])
        return value if isinstance(value, str) else None
    except (ValueError, TypeError):
        return None


def numeric_claims(text):
    values = {match.group(1).replace(',', '') for match in _MEASUREMENT.finditer(text)}
    for match in re.finditer(r'\bfrom\s+(\d+(?:[,.]\d+)*)\s+to\s+\d+(?:[,.]\d+)*\s*(?:milliseconds?|ms|seconds?|percent|%)(?!\w)', text, re.I):
        values.add(match.group(1).replace(',', ''))
    return values


class ResumeGrounding:
    def __init__(self, question):
        self.resume = resume_from_prompt(question)
        self.repairs = 0

    def unsupported(self, answer):
        if not self.resume:
            return set()
        # Compare numeric tokens, allowing a repeated unit to be elided in a range.
        evidence = set(re.findall(r'(?<!\w)\d+(?:[,.]\d+)*', self.resume))
        evidence = {value.replace(',', '') for value in evidence}
        claims = set()
        personal_answer = bool(_PERSONAL_PAST.search(answer))
        for sentence in re.split(r'(?<=[.!?])\s+', answer):
            if personal_answer and not re.search(r'\b(?:would|could|for example|hypothetically)\b', sentence, re.I):
                claims.update(numeric_claims(sentence))
        unsupported = claims - evidence
        for sentence in re.split(r'(?<=[.!?])\s+', answer):
            if not _PERSONAL_PAST.search(sentence) or re.search(r'\b(?:would|could|for example|hypothetically)\b', sentence, re.I):
                continue
            for name, pattern in _TECHNOLOGIES.items():
                if re.search(pattern, sentence, re.I) and not re.search(pattern, self.resume, re.I):
                    unsupported.add('unsupported past experience with ' + name)
        if re.search(r"\bI\s+(?:led|managed|directed|headed)\b", answer, re.I) and not re.search(r"\b(?:led|lead|leader|leadership|managed|manager|directed|headed)\b", self.resume, re.I):
            unsupported.add('leadership responsibility (use contributed or worked on; do not say I led or managed)')
        return unsupported

    async def stream(self, create, prompt, history):
        if not self.resume:
            async with aclosing(create(prompt, history)) as source:
                async for frame in source:
                    yield frame
            return
        yield _frame('verification', {'message': 'Checking resume claims as the answer arrives…'})
        released = ''
        for attempt in range(2):
            frames = []
            text = released
            pending = ''
            held = False
            completed = False
            async with aclosing(create(prompt, history)) as source:
                async for frame in source:
                    handled = False
                    for line in frame.splitlines():
                        if not line.startswith('data:'):
                            continue
                        try:
                            event = json.loads(line[5:])
                        except ValueError:
                            continue
                        if event.get('type') in ('content', 'chunk'):
                            handled = True
                            content = event.get('content', '')
                            text += content
                            pending += content
                            if len(text) > 30000:
                                yield _frame('error', {'code': 'grounding', 'message': 'Resume answer exceeded the verification limit.'})
                                return
                            # Release complete sentences without numbers only after
                            # checking them. Any number holds the remaining draft:
                            # later personal context can turn an earlier metric into
                            # a personal claim, so it must be checked as a whole.
                            while not held:
                                boundary = re.search(r'(?<=[.!?])\s+', pending)
                                if not boundary:
                                    break
                                sentence = pending[:boundary.end()]
                                if re.search(r'\d', sentence) or self.unsupported(released + sentence):
                                    held = True
                                    break
                                released += sentence
                                pending = pending[boundary.end():]
                                yield _frame('chunk', {'content': sentence})
                            yield _frame('verification_tick', {})
                        if event.get('type') == 'done':
                            completed = True
                    if not handled:
                        # Metadata can arrive immediately; terminal frames follow
                        # the verified remainder so completion never precedes text.
                        if completed or 'event: error' in frame:
                            frames.append(frame)
                        else:
                            yield frame
            invalid = self.unsupported(text)
            if not invalid:
                if pending:
                    yield _frame('chunk', {'content': pending})
                for frame in frames:
                    yield frame
                return
            if completed and self.repairs == 0:
                self.repairs += 1
                yield _frame('verification', {'message': 'Checking unsupported resume claims…'})
                prompt += ('\n[Resume verification]\nThe previous draft contained unsupported claims or measured values: '
                           + ', '.join(sorted(invalid))
                           + '. Re-answer using only the responsibilities and exact measurements in Resume data. '
                             'Do not invent or round a measured result. Omit unrelated qualifications. '
                             'Previous assistant drafts are not evidence.')
                if released:
                    prompt += ('\nThe user has already received this verified opening (JSON): '
                               + json.dumps(released)
                               + '. Output only the remaining answer, without repeating this opening.')
                history = [message for message in history if message.get('role') != 'assistant']
                continue
            # Do not stream a claim that failed verification or loop indefinitely.
            yield _frame('error', {'code': 'grounding', 'message': 'The answer contained a claim unsupported by the resume.'})
            return
