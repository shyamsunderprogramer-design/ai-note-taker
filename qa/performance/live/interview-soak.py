"""Reproducible synthetic interview soak; local model and injected failures only."""
import asyncio, json, math, os, runpy, subprocess, sys, time
from pathlib import Path
import argparse
import hashlib
ROOT=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description='Synthetic interview soak with explicit speech readiness and timing.')
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--duration',type=float,default=1800)
parser.add_argument('--interval',type=float,default=30)
parser.add_argument('--server',action='store_true')
args=parser.parse_args()
if args.duration <= 0 or args.interval <= 0: parser.error('duration and interval must be positive')
OUT=args.output.resolve(); OUT.mkdir(parents=True,exist_ok=True)
os.environ['TESTING']='true'
os.environ['ANT_DATA_DIR']=str(OUT/'data')
os.environ['ANT_DISABLE_KEY_SERVER']='1'
os.environ['RAG_ENABLED']='false'
os.environ['HF_HUB_OFFLINE']='1'
DURATION=args.duration
INTERVAL=args.interval
QUESTIONS=[
'Tell me about your experience building Python APIs.',
'Describe how you improved latency with Redis and how you measured the result.',
'How did you collaborate with Priya when testing the cache change?',
'What AWS certifications do you hold?',
'How would you investigate a slow API endpoint?',
'How would you explain cache invalidation to a teammate?',
'How would you test an API before releasing it?',
'What would you do if a deployment caused errors?',
'How do you handle a requirement you have not worked with before?',
'Why does your experience fit this Python platform engineer role?']
CONTEXT=subprocess.check_output(['node',str(ROOT/'qa/performance/ai/interview-context.mjs')],text=True).strip()

def server():
    os.environ['HF_HUB_OFFLINE']='1'
    for relative in ['backend','backend/core','backend/modules/ai','backend/modules/platform']:
        sys.path.insert(0,str(ROOT/relative))
    sys.path.insert(0,str(ROOT/'backend/modules/voice'))
    import whisper_handler as voice
    voice.select_model=lambda *a,**kw:'small'
    load_start=time.monotonic()
    voice.warmup()
    model_load_seconds=time.monotonic()-load_start
    if not voice.model_ready.is_set(): raise RuntimeError('Speech model warmup did not complete')
    original_wait=voice.wait_for_model
    readiness_waits=[]
    def timed_wait(*a,**kw):
        started=time.monotonic()
        result=original_wait(*a,**kw)
        readiness_waits.append(time.monotonic()-started)
        return result
    voice.wait_for_model=timed_wait
    from routes import recovery
    from lib.sse_helpers import make_content, _frame
    from fastapi import FastAPI
    import psutil, uvicorn
    real=recovery.provider_stream
    async def injected(model,prompt,history,**kw):
        if model.startswith('qaquota'):
            yield _frame('error',{'code':'rate_limit','retry_after':60}); return
        if model.startswith('qadrop'):
            yield make_content('I built Python APIs at Acme. ')
            await asyncio.sleep(.5)
            yield _frame('error',{'code':'transient'}); return
        async for frame in real(model,prompt,history,**kw): yield frame
    recovery.provider_stream=injected
    app=FastAPI(); app.include_router(recovery.router)
    @app.get('/health')
    def health():
        p=psutil.Process()
        return {'speech_model_ready':voice.model_ready.is_set(),'model_load_seconds':model_load_seconds,'rss_mb':p.memory_info().rss/1048576,'threads':p.num_threads(),'cpu_seconds':sum(p.cpu_times()[:2])}
    @app.get('/qa/transcribe/{index}')
    def transcribe(index:int):
        if not 0<=index<len(QUESTIONS): return {'error':'invalid index'}
        if not voice.model_ready.is_set(): raise RuntimeError('Unexpected unready model')
        readiness_waits.clear()
        result=voice.transcribe_audio(str(OUT/f'question-{index}.aiff'),fast=True)
        return {'readiness_wait_seconds':sum(readiness_waits),'text':result.get('text','') if isinstance(result,dict) else result or ''}
    uvicorn.run(app,host='127.0.0.1',port=8044,access_log=False)

def wer(ref,hyp):
    import re
    a=re.findall(r'\w+',ref.lower()); b=re.findall(r'\w+',hyp.lower()); row=list(range(len(b)+1))
    for i,w in enumerate(a,1):
        nxt=[i]
        for j,v in enumerate(b,1): nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(w!=v)))
        row=nxt
    return row[-1]/max(1,len(a))

def distribution(xs):
    xs=sorted(x for x in xs if x is not None)
    return {} if not xs else {'p50':xs[len(xs)//2],'p95':xs[max(0,math.ceil(len(xs)*.95)-1)],'max':xs[-1]}

async def client():
    import httpx
    for i,q in enumerate(QUESTIONS):
        subprocess.run(['say','-v','Samantha','-r','170','-o',str(OUT/f'question-{i}.aiff'),q],check=True)
    log=(OUT/'server.log').open('w')
    proc=subprocess.Popen([sys.executable,__file__,'--server','--output',str(OUT)],stdout=log,stderr=log,cwd=OUT)
    rows=[]; health=[]; history=[]; start=None
    report={'status':'starting','scope':'Synthetic spoken interview: file transcription + HTTP production recovery endpoint + real local Qwen. No live microphone, meeting platform, frontend, or cloud API calls. Injected provider faults. Small Whisper model; clean Samantha TTS; bounded recent history.'}
    report['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [ROOT/'backend/modules/voice/whisper_handler.py',ROOT/'backend/modules/ai/ai_router.py',ROOT/'backend/lib/stream_recovery.py',ROOT/'backend/lib/resume_grounding.py',ROOT/'apps/web/app.js']}
    def save():
        report.update(samples=rows,health=health,elapsed_seconds=0 if start is None else round(time.monotonic()-start,2))
        report['metrics']={'questions':len(rows),'completed':sum(r.get('completed',False) for r in rows),'recovery_completed':sum(r.get('completed',False) and r['scenario']!='normal' for r in rows),'recovery_attempts':sum(r['scenario']!='normal' for r in rows),'transcription_seconds':distribution([r.get('transcription_seconds') for r in rows]),'first_content_seconds':distribution([r.get('first_content_seconds') for r in rows]),'first_local_content_seconds':distribution([r.get('first_local_content_seconds') for r in rows]),'answer_seconds':distribution([r.get('answer_seconds') for r in rows]),'end_to_end_seconds':distribution([r.get('end_to_end_seconds') for r in rows]),'mean_word_error_rate':sum(r.get('word_error_rate',0) for r in rows)/max(1,len(rows)),'health_failures':sum('error' in h for h in health),'health_latency_seconds':distribution([h.get('seconds') for h in health]),'rss_mb':distribution([h.get('rss_mb') for h in health])}
        temp=OUT/'progress.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(OUT/'report.json')
    save()
    try:
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8044',timeout=70,trust_env=False) as c:
            for _ in range(120):
                try:
                    if (await c.get('/health',timeout=2)).status_code==200: break
                except Exception: pass
                await asyncio.sleep(1)
            else: raise RuntimeError('Server failed to start')
            # Warm the speech model before timing the thirty-minute interview.
            await c.get('/qa/transcribe/0',timeout=120)
            start=time.monotonic(); end=start+DURATION
            report['warmup']=(await c.get('/health')).json()
            report['prompt_source']='apps/web/app.js buildInterviewPrompt; short synthetic resume/JD'
            report.update(status='running',started_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),planned_duration_seconds=DURATION)
            save(); print('STARTED '+report['started_at'],flush=True)
            async def monitor():
                while time.monotonic()<end:
                    t=time.monotonic()
                    try:
                        h=(await c.get('/health',timeout=3)).json();h['seconds']=time.monotonic()-t
                    except Exception as e: h={'error':str(e)}
                    h['at_seconds']=time.monotonic()-start;health.append(h);save()
                    await asyncio.sleep(min(10,max(0,end-time.monotonic())))
            task=asyncio.create_task(monitor())
            try:
                for n in range(math.ceil(DURATION/INTERVAL)):
                    await asyncio.sleep(max(0,start+n*INTERVAL-time.monotonic()))
                    if time.monotonic()>=end: break
                    i=n%len(QUESTIONS); scenario='quota' if n%6==2 else 'partial_disconnect' if n%6==4 else 'normal'
                    row={'cold_ai_request':n==0,'turn':n+1,'scenario':scenario,'question':QUESTIONS[i],'started_seconds':time.monotonic()-start,'completed':False}
                    t=time.monotonic()
                    try:
                        tr=await c.get(f'/qa/transcribe/{i}');tr.raise_for_status(); transcript=tr.json()['text']
                        row.update(readiness_wait_seconds=tr.json()['readiness_wait_seconds'],transcript=transcript,transcription_seconds=time.monotonic()-t,word_error_rate=wer(QUESTIONS[i],transcript))
                        if not transcript.strip(): raise RuntimeError('Empty transcript')
                        candidates=['qwen3.5:9b']
                        if scenario!='normal': candidates.insert(0,'qaquota-primary' if scenario=='quota' else 'qadrop-primary')
                        ai_start=time.monotonic(); events=[]; parts=[]; active=None
                        async with c.stream('POST','/stream-recover',json={'query':CONTEXT.replace('__QA_QUESTION__',transcript),'candidates':candidates,'mode':'instant','style':'concise','temperature':0,'messages':history[-8:]}) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line.startswith('data:'): continue
                                e=json.loads(line[5:]);events.append(e)
                                if e.get('type')=='meta': active=e.get('model')
                                if e.get('content'):
                                    row.setdefault('first_content_seconds',time.monotonic()-ai_start)
                                    if active=='qwen3.5:9b': row.setdefault('first_local_content_seconds',time.monotonic()-ai_start)
                                    parts.append(e['content'])
                        answer=''.join(parts)
                        row.update(answer=answer,answer_seconds=time.monotonic()-ai_start,completed=bool(events and events[-1].get('type')=='done' and answer.strip()),events=[e for e in events if e.get('type')!='content'])
                        if row['completed']: history.extend([{'role':'user','text':transcript},{'role':'assistant','text':answer}])
                    except Exception as e: row['error']=repr(e)
                    row['end_to_end_seconds']=time.monotonic()-t;rows.append(row);save()
                    print(json.dumps({k:row[k] for k in ['turn','scenario','completed','end_to_end_seconds']}),flush=True)
                await asyncio.sleep(max(0,end-time.monotonic()))
            finally:
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
            # Exhaustion must be explicit and must not poison the next question.
            exhausted=(await c.post('/stream-recover',json={'query':'QA exhaustion check','candidates':['qaquota-exhausted']})).text
            following=(await c.post('/stream-recover',json={'query':'Reply with a short acknowledgement.','candidates':['qwen3.5:9b'],'mode':'instant','temperature':0})).text
            report['exhaustion_check']={'explicit_error':'event: error' in exhausted,'false_done':'event: done' in exhausted,'next_question_completed':'event: done' in following and 'event: error' not in following}
            report['status']='complete';save();print('COMPLETE '+json.dumps(report['metrics']),flush=True)
    except BaseException as e:
        report.update(status='interrupted',error=repr(e));save();raise
    finally:
        proc.terminate()
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: proc.kill();proc.wait()
        log.close()

if __name__=='__main__':
    if args.server: server()
    else: asyncio.run(client())
