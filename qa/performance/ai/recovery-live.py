"""Controlled primary failures followed by live backups through production recovery."""
import asyncio
import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[3]
load_dotenv(ROOT/'backend/.env')
for relative in ['backend','backend/core','backend/modules/ai','backend/modules/platform']:
    sys.path.insert(0,str(ROOT/relative))
from lib.stream_recovery import recover_stream, _COOLDOWNS
from lib.sse_helpers import make_content, _frame
from routes.recovery import provider_stream
from modules.platform import cloud_providers as cloud
original=cloud.build_prompt
cloud.build_prompt=lambda *a,**kw:original(*a,**{**kw,'include_rag':False})

async def main():
    rows=[]
    cases=[
      ('quota','rate_limit','', 'Resume: Alex built Python APIs at Acme. JD: Python and AWS certification. No certifications are listed in the resume. Which AWS certifications do I hold? Answer only from resume evidence.'),
      ('partial_disconnect','transient','Cedar is $1,400 over budget.', 'Cedar budget $4800 spent $6200; Maple budget $3000 spent $2700. Give each variance and combined net overrun. Under 80 words.'),
      ('output_limit','output_limit','Cedar is $1,400 over budget.', 'Cedar budget $4800 spent $6200; Maple budget $3000 spent $2700. Give each variance and combined net overrun. Under 80 words.'),
    ]
    for name,code,partial,question in cases:
        _COOLDOWNS.clear(); calls=[]; events=[]; start=time.monotonic()
        async def factory(model,prompt,history):
            calls.append(model)
            if len(calls)==1:
                if partial: yield make_content(partial)
                yield _frame('error',{'code':code,'retry_after':60})
                return
            async for frame in provider_stream(model,prompt,history,mode='instant',style='concise',temperature=.2):
                yield frame
        candidates=['groq-gpt-oss-120b'] if code=='output_limit' else ['qa-primary','groq-gpt-oss-120b']
        async for frame in recover_stream(question,candidates,factory):
            for line in frame.splitlines():
                if line.startswith('data:'): events.append(json.loads(line[5:]))
        text=''.join(e.get('content','') for e in events)
        row={'case':name,'scope':'Injected first failure; real Groq recovery through production controller and provider adapter',
             'seconds':round(time.monotonic()-start,3),'calls':calls,'completed':events[-1]['type']=='done','answer':text,
             'recovery_events':[e for e in events if e['type']=='recovery']}
        rows.append(row);print(json.dumps(row),flush=True)
    output=ROOT/'qa/performance/results/2026-09-25-recovery-live.json'
    output.write_text(json.dumps(rows,indent=2))
    if not all(row['completed'] for row in rows): raise SystemExit(1)
asyncio.run(main())
