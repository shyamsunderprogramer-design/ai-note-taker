"""Loopback-only backend for the Electron latency probe. Synthetic context only."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in ['backend', 'backend/core', 'backend/modules/ai', 'backend/modules/platform']:
    sys.path.insert(0, str(ROOT / relative))
os.environ['ANT_DISABLE_KEY_SERVER'] = '1'

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.recovery import RecoveryRequest, stream_recover
from routes.ollama import list_providers, model_catalog
from ocr_service import extract_text_from_image
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
app.get('/providers')(list_providers)
app.get('/models/catalog')(model_catalog)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/auth/status')
def auth():
    return {'auth_required': False}

@app.post('/stream-recover')
def answer(body: RecoveryRequest):
    # Bound live spending to the selected model; do not try other paid providers.
    body.candidates = ['groq-qwen3-8-27b']
    return stream_recover(body)

@app.post('/ocr')
async def ocr(request: Request):
    body = await request.json()
    return await asyncio.to_thread(extract_text_from_image, body.get('image_b64', ''))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]), access_log=False, log_level='error')
