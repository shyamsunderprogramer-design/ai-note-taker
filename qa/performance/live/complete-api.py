"""Synthetic feature and isolation checks against the disposable server on 8046."""
import io
import json
from pathlib import Path
import sys
import time
import uuid
import zipfile
import httpx

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
rows = []
client = httpx.Client(base_url='http://127.0.0.1:8046', timeout=30, trust_env=False)


def check(name, action):
    start = time.monotonic()
    try:
        detail = action()
        row = dict(name=name, status='passed', detail=detail)
    except Exception as exc:
        row = dict(name=name, status='failed', detail=str(exc))
    row['seconds'] = round(time.monotonic()-start, 3)
    rows.append(row)
    (OUT/'api-workflows.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(row), flush=True)


def body(method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    data = response.json()
    assert not isinstance(data, dict) or not data.get('error'), str(data)[:400]
    return data


def account():
    name = 'complete_' + uuid.uuid4().hex[:10]
    body('POST', '/auth/register', data={'username':name,'email':name+'@example.com','password':'TestPass123!'})
    token = body('POST', '/auth/login', data={'username':name,'password':'TestPass123!'})['access_token']
    return name, {'Authorization':'Bearer '+token}


name, auth = account()
other_name, other_auth = account()
client.headers.update(auth)
check('Authenticated account identity', lambda: body('GET','/auth/me')['username'] == name or (_ for _ in ()).throw(AssertionError('Wrong account')))


def conversations():
    messages = [{'role':'user','text':'Synthetic lighthouse question'},{'role':'assistant','text':'Synthetic lighthouse answer'}]
    saved = body('POST','/conversations',json={'title':'QA export round trip','messages':messages})
    identity = saved['id']
    assert body('GET','/conversations/'+identity)['messages'] == messages
    assert client.get('/conversations/'+identity,headers=other_auth).status_code == 404
    assert client.delete('/conversations/'+identity,headers=other_auth).status_code == 404
    exported = body('POST','/conversations/export',json={'messages':messages,'format':'json'})
    imported = body('POST','/conversations/import',files={'file':('export.json',exported['content'],'application/json')})
    assert imported['messages'] == messages
    assert body('DELETE','/conversations/'+identity)['deleted']
    assert client.get('/conversations/'+identity).status_code == 404
    return 'create/read, two-account denial, JSON export/import, deletion verified'


check('Conversation lifecycle and isolation', conversations)
check('Malformed conversation import rejected', lambda: client.post('/conversations/import',files={'file':('bad.json',b'{bad','application/json')}).status_code == 422 or (_ for _ in ()).throw(AssertionError('Invalid import accepted')))


def resume(filename, payload, valid=True):
    response = client.post('/resume/context',files={'file':(filename,payload)})
    assert response.status_code == (200 if valid else 422), f'HTTP {response.status_code}: {response.text[:200]}'
    if valid:
        assert 'Python' in response.json()['text']
    return f'HTTP {response.status_code}'


text = b'Alex Sample built Python APIs and tested Redis cache invalidation at Acme.'
for extension in ['txt','md','json']:
    payload = json.dumps({'experience':text.decode()}).encode() if extension == 'json' else text
    check('Resume '+extension+' extraction',lambda extension=extension,payload=payload:resume('sample.'+extension,payload))
docx = io.BytesIO()
with zipfile.ZipFile(docx,'w') as archive:
    archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text.decode()+'</w:t></w:r></w:p></w:body></w:document>')
check('Resume DOCX extraction',lambda:resume('sample.docx',docx.getvalue()))
for label,filename,payload in [('empty','empty.txt',b''),('corrupt PDF','bad.pdf',b'not a PDF'),('unsupported','bad.exe',text),('oversize','large.txt',b'x'*(5*1024*1024+1))]:
    check('Resume rejects '+label,lambda filename=filename,payload=payload:resume(filename,payload,False))


job_id = None
def jobs():
    global job_id
    saved = body('POST','/job-tracker/application',params={'user_id':name,'company':'Synthetic Lighthouse Labs','role':'Python engineer','status':'saved'})
    job_id = saved['application']['id']
    assert body('GET','/job-tracker/application/'+job_id)['company']=='Synthetic Lighthouse Labs'
    updated = body('POST',f'/job-tracker/application/{job_id}/status',params={'status':'applied','notes':'Synthetic follow-up'})
    assert updated['application']['status']=='applied'
    assert body('GET','/job-tracker/application/'+job_id)['status']=='applied'
    matches = body('GET','/job-tracker/search',params={'user_id':name,'query':'Lighthouse'})
    assert any(row['id']==job_id for row in matches['results'])
    return 'create/read/status/re-read/search verified'


check('Job application API lifecycle',jobs)
def job_isolation():
    assert job_id, 'Prerequisite job creation failed'
    response=client.get('/job-tracker/application/'+job_id,headers=other_auth)
    assert response.status_code in (401,403,404), f'Second synthetic account can read first account job: HTTP {response.status_code}'
check('Job application account isolation',job_isolation)
def bad_status():
    assert job_id, 'Prerequisite job creation failed'
    response=client.post(f'/job-tracker/application/{job_id}/status',params={'status':'not-a-real-stage'})
    assert response.status_code in (400,422), f'Invalid stage accepted: HTTP {response.status_code}'
check('Job application invalid stage rejection',bad_status)
if job_id:
    check('Job application deletion',lambda:body('DELETE','/job-tracker/application/'+job_id))


plan = None
def study():
    global plan
    plan=body('POST','/study-plan/generate',params={'user_id':name,'days':3,'daily_minutes':30,'current_skills':'Python','target_role':'Python engineer'})
    assert len(plan['sessions']) == 3
    assert body('GET','/study-plan/'+name)['sessions'] == plan['sessions']
    return 'Three-day plan generated and retrieved'
check('Study plan creation and retrieval',study)
def complete_task():
    assert plan, 'Prerequisite plan creation failed'
    task=next(task for session in plan['sessions'] for task in session['tasks'])
    result=body('POST',f'/study-plan/{name}/complete-task',params={'task_id':task['id'],'performance_score':0.8})
    assert result['completed']
    retrieved=body('GET','/study-plan/'+name)
    updated=next(item for session in retrieved['sessions'] for item in session['tasks'] if item['id']==task['id'])
    assert updated['completed'], 'API reports completion but reloading the task still shows incomplete'
check('Study task completion persists',complete_task)
def missing_task():
    response=client.post(f'/study-plan/{name}/complete-task',params={'task_id':'does-not-exist'})
    assert response.status_code in (400,404,422), f'Nonexistent task accepted: HTTP {response.status_code}'
check('Study rejects nonexistent task',missing_task)


def interview():
    created=body('POST','/interview-simulator/create',params={'company':'Acme','role':'Python engineer','num_questions':2,'user_id':name})
    sid=created['session_id']
    first=body('GET',f'/interview-simulator/{sid}/question')
    assert first.get('question'), str(first)[:200]
    for _ in range(2):
        result=body('POST',f'/interview-simulator/{sid}/answer',params={'transcript':'I tested the Python API with unit and integration tests, measured latency, and investigated failures with logs.','duration_ms':15000})
        assert result.get('evaluation'), str(result)[:200]
    finished=body('POST',f'/interview-simulator/{sid}/finish')
    return {'session_completed':True,'finish_fields':list(finished)}
check('Interview create/question/answer/finish',interview)


def document():
    saved=body('POST','/documents/upload',files={'file':('lighthouse.txt',text,'text/plain')})
    retrieved=body('POST','/documents/retrieve',data={'query':'Python Redis','top_k':3})
    assert retrieved['results'], 'Upload returned success but retrieval returned no results'
    return {'upload_fields':list(saved),'retrieved':len(retrieved['results'])}
check('Knowledge upload and retrieval',document)


def logout():
    body('POST','/auth/logout')
    response=client.get('/auth/me')
    assert response.status_code in (401,403), f'Logged-out token remains valid: HTTP {response.status_code}'
check('Logout invalidates token',logout)
client.close()
raise SystemExit(1 if any(row['status']=='failed' for row in rows) else 0)
