"""Isolated loopback UI/AI smoke server. No auth, database, or user recordings.

Uses production stream routes with local Qwen or configured Groq; run only for QA.
"""
import ast
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ['RAG_ENABLED'] = 'false'
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))

import ai_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Reuse the production adapter without starting the full app or its database.
tree = ast.parse((ROOT / 'backend/core/main.py').read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_patch_to_async_gen')
namespace = {'asyncio': asyncio}
exec(compile(ast.Module(body=[fn], type_ignores=[]), '<production-adapter>', 'exec'), namespace)
ai_router.ask_ollama_stream = namespace['_patch_to_async_gen'](ai_router.ask_ollama_stream)
from modules.platform import cloud_providers
for name in ['ask_groq_stream', 'ask_gpt_stream', 'ask_gemini_stream', 'ask_ollama_cloud_stream']:
    setattr(cloud_providers, name, namespace['_patch_to_async_gen'](getattr(cloud_providers, name)))
from routes.ai import stream_ai, stream_race
from routes.interview import upload_resume_context

app = FastAPI()
from routes.recovery import router as recovery_router
app.include_router(recovery_router)
app.post('/resume/context')(upload_resume_context)
app.get('/stream-race')(stream_race)

@app.get('/providers')
def providers():
    return {provider: bool(os.getenv(env, '').strip()) for provider, env in [
        ('groq', 'GROQ_API_KEY'), ('openai', 'OPENAI_API_KEY'),
        ('google', 'GOOGLE_API_KEY'), ('ollama-cloud', 'OLLAMA_CLOUD_API_KEY')
    ]}

@app.get('/qa/stream')
def stream(q: str, provider: str, mode: str = 'instant', style: str = 'concise'):
    if provider not in {'qwen3.5:9b', 'groq-gpt-oss-120b'}:
        from fastapi import HTTPException
        raise HTTPException(400, 'This QA server only permits Qwen local or Groq GPT-OSS 120B')
    return stream_ai(q=q, provider=provider, mode=mode, style=style, temperature=0)

app.mount('/', StaticFiles(directory=ROOT / 'apps/web/dist', html=True), name='ui')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8041, access_log=False)
