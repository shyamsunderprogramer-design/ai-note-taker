"""Consume an explicitly selected provider through the normal AI router."""
import asyncio
import json


async def collect_selected_model(prompt, model, timeout=12):
    from ai_router import route_ai_stream
    parts = []
    async with asyncio.timeout(timeout):
        async for frame in route_ai_stream(prompt, mode='instant', provider=model):
            for line in frame.splitlines():
                if not line.startswith('data:'):
                    continue
                data = json.loads(line[5:])
                if data.get('type') == 'error':
                    raise RuntimeError(data.get('message', 'Selected model failed'))
                if data.get('content'):
                    parts.append(data['content'])
    return ''.join(parts).strip()
