"""API software fixtures are synthetic; independent live/browser evidence is separate."""
import copy,io,json,sqlite3,zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from bluecho.dashboard.service import create_app,Service,uid,now
from bluecho.phase1.engine import RecordingEngine

@pytest.fixture
def local(tmp_path,monkeypatch):
 source=tmp_path/'synthetic.png';Image.new('RGB',(40,40),(30,30,30)).save(source)
 entry={'id':'synthetic','version':'fixture','weights':{'sha256':'a'*64},'runtime':'fixture','classes':{'0':'fixture'},'evidence_scope':'SYNTHETIC TEST ONLY','calibration':'uncalibrated','preprocessing':{},'terms':{}}
 adapter=SimpleNamespace(predict=lambda *a,**k:([{'xyxy':[4,4,30,30],'score':.8,'class_id':0,'class_name':'fixture'}],None))
 engine=RecordingEngine(tmp_path/'registry');monkeypatch.setattr(engine.registry,'load',lambda *a,**k:(entry,adapter));engine.predict(source,tmp_path/'saved',model_ids=['synthetic'],modality='SSS')
 manifest=tmp_path/'examples.json';manifest.write_text(json.dumps([{'id':'fixture','source':str(source),'saved':str(tmp_path/'saved'),'request':{'models':['synthetic'],'modality':'SSS'}}]))
 app=create_app(tmp_path/'store',tmp_path/'registry',manifest)
 with TestClient(app) as client:
  job=client.post('/api/v1/examples/fixture/saved').json();base=f"/api/v1/jobs/{job['id']}/windows/0";yield client,app.state.service,job,base

def test_review_revision_geometry_and_exports(local):
 c,s,j,b=local;r=c.get(b).json();d=r['detections'][0];original=copy.deepcopy(d)
 result=c.post(b+'/review/'+d['candidate_id'],json={'revision':0,'action':'corrected','box':[5,5,20,20],'label':'reviewer <script>','note':'<img src=x>','reviewer':'Test fixture'})
 assert result.status_code==200,result.text
 assert c.post(b+'/review/'+d['candidate_id'],json={'revision':0,'action':'note'}).status_code==409
 r=c.get(b).json();assert r['review_revision']==1;assert r['detections'][0]['original_prediction']==original;assert r['detections'][0]['coordinates'] is None
 assert r['detections'][0]['pixel_dimensions']=={'width':15,'height':15}
 assert c.post(b+'/review/'+d['candidate_id'],json={'revision':1,'action':'corrected','box':[-1,2,40,40]}).status_code==422
 for kind in ['json','csv','geojson','html','zip']:
  out=c.post(b+'/export',json={'revision':1,'format':kind});assert out.status_code==200,out.text[:500]
  if kind=='json':assert out.json()['detections'][0]['review_history'][0]['reviewer']=='Test fixture'
  if kind=='csv':assert b'review_revision' in out.content and b'Test fixture' in out.content
  if kind=='geojson':assert out.json()['features'][0]['properties']['review_revision']==1
  if kind in ('zip','html'):
   with zipfile.ZipFile(io.BytesIO(out.content)) as z:
    assert 'original.png' in z.namelist();assert b'<script>' not in z.read('report.html');assert json.loads(z.read('original_predictions.json'))['detections'][0]==original
 assert c.post(b+'/export',json={'revision':0}).status_code==409
 out=c.post(b+'/export',json={'revision':1,'format':'json','scope':'displayed','candidate_ids':[]});assert out.json()['detections']==[]
 with s.db() as db:
  with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM reviews')
 restarted=Service(s.root,s.registry);assert restarted.canonical(j['id'],'0')['review_revision']==1

def test_safe_upload_identifiers_and_cross_origin(local):
 c,s,j,b=local
 assert c.post('/api/v1/sources',files={'file':('bad.png',b'not an image')}).status_code==422
 assert c.post('/api/v1/sources',files={'file':('bad.sl2',b'x')}).status_code==422
 assert c.get('/api/v1/jobs/not-an-id').status_code==404
 assert c.get(b+'/evidence/%2e%2e%2frequest.json').status_code==404
 assert c.post('/api/v1/jobs',json={},headers={'Origin':'https://evil.test'}).status_code==403
 assert c.get('/api/v1/health',headers={'Host':'evil.test'}).status_code==403
 assert c.post('/api/v1/jobs',json={'source_id':j['request']['source_id'],'models':['ghost-net-real'],'modality':'SSS'}).status_code==422
 assert c.post('/api/v1/jobs',json={'source_id':j['request']['source_id'],'models':['synthetic'],'modality':'SSS','chunk_pings':513}).status_code==422

def test_rescan_and_restart_preserve_completed_windows(local):
 c,s,j,b=local
 assert c.post(b+'/rescan',json={'revision':0,'region':[0,0,40,40],'reason':'Human fixture; inspect missed objects'}).status_code==200
 r=c.get(b).json();assert r['rescan_requests'][0]['origin']=='human_action';assert len(r['detections'])==1
 with s.db() as db:db.execute("UPDATE jobs SET state='processing' WHERE id=?",(j['id'],))
 restarted=Service(s.root,s.registry);job=restarted.job(j['id']);assert job['state']=='failed';assert len(job['windows'])==1
 assert 'restarted' in job['message']

def test_source_metadata_snapshot_and_queue_bound(local,monkeypatch):
 c,s,j,b=local
 s.stop.set();monkeypatch.setattr(s,'caps',lambda:{'models':[{'id':'synthetic','modalities':['SSS'],'state':'ready'}]})
 source=s.source(j['request']['source_id']);path=Path(source['path']);sidecar=path.parent/'metadata.json';sidecar.write_text('{"immutable":"one"}');source['sidecar']=str(sidecar)
 with s.db() as db:db.execute('UPDATE sources SET payload=? WHERE id=?',(json.dumps(source),source['id']))
 s.queue_limit=1;a=s.create_job({'source_id':source['id'],'models':['synthetic'],'modality':'SSS'});sidecar.write_text('{"changed":true}')
 payload=json.loads((s.path(a['id'])/'request.json').read_text());assert json.loads(Path(payload['sidecar']).read_text())=={'immutable':'one'}
 assert c.post('/api/v1/jobs',json={'source_id':source['id'],'models':['synthetic'],'modality':'SSS'}).status_code==429
 assert c.post('/api/v1/jobs/'+a['id']+'/cancel').json()['state']=='cancelled'
