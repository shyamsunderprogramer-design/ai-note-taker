"""Restart the same disposable backend/data directory and check persisted state."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time
import uuid
import httpx

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'qa/performance/results/2026-10-02-complete'
OUT.mkdir(parents=True,exist_ok=True)
prepare=runpy.run_path(str(ROOT/'qa/performance/backend/isolated.py'))['prepare']
work,backend,env=prepare()
command=[sys.executable,'-m','uvicorn','core.main:app','--host','127.0.0.1','--port','8050']
client=httpx.Client(base_url='http://127.0.0.1:8050',timeout=15,trust_env=False)
rows=[]
child=None
log=(OUT/'persistence-server.log').open('w')


def start():
    global child
    child=subprocess.Popen(command,cwd=backend,env=env,stdout=log,stderr=log)
    for _ in range(90):
        if child.poll() is not None:raise RuntimeError('Disposable server failed to start')
        try:
            if client.get('/health',timeout=1).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise RuntimeError('Disposable server did not become ready')


def stop():
    if child and child.poll() is None:
        child.terminate()
        try:child.wait(timeout=15)
        except subprocess.TimeoutExpired:child.kill();child.wait()


def request(method,path,**kwargs):
    r=client.request(method,path,**kwargs);r.raise_for_status();return r.json()


def record(name,passed,detail):
    rows.append({'name':name,'passed':passed,'detail':detail})
    (OUT/'persistence.json').write_text(json.dumps({'scope':'Same disposable source, JWT secret and data directory across restart','checks':rows},indent=2))
    print(json.dumps(rows[-1]),flush=True)


try:
    start()
    name='persist_'+uuid.uuid4().hex[:8]
    request('POST','/auth/register',data={'username':name,'email':name+'@example.com','password':'TestPass123!'})
    token=request('POST','/auth/login',data={'username':name,'password':'TestPass123!'})['access_token']
    client.headers['Authorization']='Bearer '+token
    conversation=request('POST','/conversations',json={'title':'Persistence fixture','messages':[{'role':'user','text':'Synthetic persistence marker'}]})
    job=request('POST','/job-tracker/application',params={'user_id':name,'company':'Persistence fixture','role':'Python engineer'})['application']
    plan=request('POST','/study-plan/generate',params={'user_id':name,'days':3,'daily_minutes':30,'target_role':'Python engineer'})
    retrieved=request('GET','/study-plan/'+name)
    record('Study plan survives immediate retrieval',retrieved.get('duration_days')==3 and retrieved.get('target_role')=='Python engineer',{'created_days':plan.get('duration_days'),'retrieved_days':retrieved.get('duration_days'),'retrieved_role':retrieved.get('target_role')})
    stop();start()
    me=client.get('/auth/me')
    record('Account/token survives server restart',me.status_code==200,'HTTP '+str(me.status_code))
    fetched=client.get('/conversations/'+conversation['id'])
    record('Conversation survives server restart',fetched.status_code==200 and fetched.json().get('messages')==conversation['messages'],'HTTP '+str(fetched.status_code))
    fetched=client.get('/job-tracker/application/'+job['id'])
    record('Job application survives server restart',fetched.status_code==200 and fetched.json().get('id')==job['id'],{'http':fetched.status_code,'body':fetched.json()})
    fetched=request('GET','/study-plan/'+name)
    record('Study plan survives server restart',fetched.get('duration_days')==3 and fetched.get('target_role')=='Python engineer',{'days':fetched.get('duration_days'),'role':fetched.get('target_role')})
    request('POST','/auth/logout')
    response=client.get('/auth/me')
    record('Logged-out token rejected',response.status_code in (401,403),'HTTP '+str(response.status_code))
finally:
    stop();client.close();log.close()
raise SystemExit(0 if all(row['passed'] for row in rows) else 1)
