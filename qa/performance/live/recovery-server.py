"""Isolated loopback fault-injection server; no user database or microphone."""
import asyncio
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import recovery
from lib.sse_helpers import make_content, make_done, _frame
from lib.stream_recovery import _COOLDOWNS
app = FastAPI()
events=[]

async def fake_provider(model, prompt, history, **kwargs):
    events.append({'event':'start','model':model,'question':next((tag for tag in ['slow question','partial question','quota question','exhausted question'] if tag in prompt),'other')})
    try:
        if 'slow question' in prompt:
            yield make_content('Old partial answer.')
            await asyncio.sleep(20)
            yield make_content('STALE ANSWER MUST NOT APPEAR')
        elif 'exhausted question' in prompt:
            yield make_content('Partial result.' if model.startswith('groq') else '')
            yield _frame('error',{'code':'transient'})
            return
        elif 'quota question' in prompt and model.startswith('groq'):
            yield _frame('error',{'code':'rate_limit','retry_after':60})
            return
        elif 'partial question' in prompt and model.startswith('groq'):
            yield make_content('Cedar is $1,400 over budget.')
            yield _frame('error',{'code':'transient'})
            return
        elif 'partial question' in prompt:
            assert 'Resume data' in prompt and 'Job description data' in prompt
            assert 'Cedar is $1,400' in prompt
            yield make_content('Cedar is $1,400 over budget. Maple is $300 under budget.')
        else:
            yield make_content('New answer complete.')
        yield make_done(1)
    finally:
        events.append({'event':'closed','model':model,'question':next((tag for tag in ['slow question','partial question','quota question','exhausted question'] if tag in prompt),'other')})

recovery.provider_stream = fake_provider
app.include_router(recovery.router)
@app.get('/providers')
def providers(): return {'groq':True,'openai':True}
@app.get('/ollama/models')
def models(): return {'models':[{'name':'qa-local:1b'}]}
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/auth/status')
def auth(): return {'auth_required':False}
@app.get('/qa/events')
def get_events(): return events
@app.post('/qa/reset')
def reset(): events.clear(); _COOLDOWNS.clear(); return {'ok':True}
@app.post('/transcribe')
def transcribe(): return {'text':'partial question from recorded speech'}
app.mount('/',StaticFiles(directory=ROOT/'apps/web/dist',html=True))
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8042,access_log=False)
