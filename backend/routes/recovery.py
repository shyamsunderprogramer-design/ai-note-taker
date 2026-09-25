"""Hands-free streaming endpoint shared by text, voice transcripts and screen context."""
from contextlib import aclosing
from typing import Annotated
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from lib.async_stream import iterate_sync
from lib.stream_recovery import recover_stream, provider_family
from lib.sse_helpers import make_error

router = APIRouter()


class RecoveryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=80000)
    candidates: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=16)
    mode: str = Field(default='instant', max_length=40)
    style: str = Field(default='concise', max_length=40)
    temperature: float = Field(default=0.3, ge=0, le=2)
    messages: list[dict] = Field(default_factory=list, max_length=30)
    image_b64: str | None = Field(default=None, max_length=10000000)


async def provider_stream(model, prompt, history, *, mode='instant', style='concise', temperature=0.3, image_b64=None):
    """Use exact candidates, including installed local models; never hidden auto-routing."""
    from modules.platform import cloud_providers as cloud
    import ai_router
    resolved = cloud.PROVIDER_MODEL_MAP.get(model)
    family = provider_family(model)
    kwargs = dict(mode=mode, style=style, temperature=temperature, messages=history)
    if image_b64:
        if family == 'ollama':
            stream = ai_router.ask_ollama_vision_stream(prompt, image_b64=image_b64, model_name=model, **kwargs)
        else:
            fn = cloud.get_vision_stream_fn(family)
            if fn is None:
                yield make_error('Selected provider is unavailable for screenshots.')
                return
            chosen = resolved[1] if resolved else cloud.VISION_PROVIDER_MAP.get(family)
            stream = fn(prompt, image_b64=image_b64, model=chosen, **kwargs)
    elif family == 'ollama':
        stream = ai_router.ask_ollama_stream(prompt, model_name=model, **kwargs)
    elif resolved:
        fn = cloud.get_stream_fn(model)
        stream = fn(prompt, model=resolved[1], **kwargs)
    elif model.endswith(':cloud'):
        stream = cloud.ask_ollama_cloud_stream(prompt, model=model, **kwargs)
    else:
        yield make_error('Selected model is unavailable.')
        return
    iterator = stream if hasattr(stream, '__aiter__') else iterate_sync(stream)
    async with aclosing(iterator):
        async for frame in iterator:
            yield frame


@router.post('/stream-recover')
def stream_recover(body: RecoveryRequest):
    def factory(model, prompt, history):
        return provider_stream(model, prompt, history, mode=body.mode, style=body.style,
                               temperature=body.temperature, image_b64=body.image_b64)
    return StreamingResponse(recover_stream(body.query, body.candidates, factory, body.messages),
                             media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
