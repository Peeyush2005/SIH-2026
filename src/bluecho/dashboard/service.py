"""Versioned local API wrapping the installed engine; no network inference."""
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime,timezone
import csv,copy,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,threading,time,uuid,zipfile
from typing import Literal
from fastapi import FastAPI,UploadFile,File,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from starlette.concurrency import run_in_threadpool
from bluecho import __version__
from bluecho.phase1.download import atomic_json,digest
from bluecho.phase1.inputs import inspect_input
from bluecho.phase1.adapters import Registry
from bluecho.phase1.geography import load_sidecar,geotag_box
from bluecho.phase1.reporting import export_result
from PIL import Image,UnidentifiedImageError
import struct

ACTIVE=('queued','validating','processing','exporting')
def now():return datetime.now(timezone.utc).isoformat()
def uid():return uuid.uuid4().hex
class JobRequest(BaseModel):
    source_id:str
    models:list[str]=Field(min_length=1,max_length=4)
    modality:str
    channel:int|None=None
    start_ping:int=Field(default=0,ge=0)
    max_pings:int=Field(default=128,ge=0)
    chunk_pings:int=Field(default=128,ge=1,le=512)
class ReviewRequest(BaseModel):
    revision:int=Field(ge=0)
    action:Literal['retain','false_alert','uncertain','note','corrected']
    label:str|None=Field(default=None,max_length=100)
    box:list[float]|None=Field(default=None,min_length=4,max_length=4)
    note:str=Field(default='',max_length=2000)
    reviewer:str|None=Field(default=None,max_length=100)
class ScanRequest(BaseModel):
    revision:int
    region:list[float]=Field(min_length=4,max_length=4)
    reason:str=Field(min_length=1,max_length=2000)
    reviewer:str|None=Field(default=None,max_length=100)
class ExportRequest(BaseModel):
    revision:int
    format:Literal['json','csv','geojson','html','zip']='zip'
    scope:Literal['all','displayed']='all'
    candidate_ids:list[str]=Field(default_factory=list,max_length=10000)

class Service:
    def __init__(self,storage,registry,examples=None,queue_limit=8,memory_mib=8192):
        self.root=Path(storage).resolve();self.registry=Path(registry).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.database=self.root/'application.sqlite';self.lock=threading.RLock();self.stop=threading.Event();self.child=None;self.queue_limit=queue_limit;self.memory_mib=memory_mib
        self.sessions=None
        self.hosted=False
        self.examples=json.loads(Path(examples).read_text()) if examples else []
        for example in self.examples:
            for key in ('source','saved'):
                if example.get(key):example[key]=str((Path(examples).resolve().parent/Path(example[key])).resolve())
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,state TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,message TEXT);
            CREATE TABLE IF NOT EXISTS reviews(event INTEGER PRIMARY KEY AUTOINCREMENT,job TEXT NOT NULL,window TEXT NOT NULL,candidate TEXT,payload TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS immutable_review_updates BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT,'immutable review event'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_review_deletes BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT,'immutable review event'); END;''')
            db.execute("UPDATE jobs SET state='failed',message='Server restarted during processing. Partial windows retained; start a new inspection to retry.' WHERE state IN ('queued','validating','processing','exporting')")
    def db(self):
        db=sqlite3.connect(self.database,timeout=30);db.row_factory=sqlite3.Row;return db
    def checked(self,identifier):
        if not re.fullmatch('[a-f0-9]{32}',identifier):raise HTTPException(404,'Unknown identifier')
        return identifier
    def source(self,identifier):
        self.checked(identifier)
        if self.sessions:self.sessions.check('source',identifier)
        with self.db() as db:row=db.execute('SELECT payload FROM sources WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'Source not found')
        return json.loads(row[0])
    def path(self,identifier):return self.root/'jobs'/self.checked(identifier)
    def public_source(self,s):return {k:v for k,v in s.items() if k not in ('path','sidecar')}
    def caps(self):
        rows=[]
        for e in Registry(self.registry).entries():
            path=(self.registry/e.get('weights',{}).get('path','missing')).resolve()
            deps=['numpy','PIL','pyproj','psutil','jsonschema','torch','ultralytics']+(['onnxruntime'] if e.get('runtime')=='onnx' else [])
            missing=[d for d in deps if importlib.util.find_spec(d) is None]
            state='unsupported on this runtime' if e.get('status')=='unavailable' else 'weights missing' if not path.is_file() or not path.is_relative_to(self.registry) else 'dependency missing' if missing else 'ready'
            rows.append({'id':e['id'],'version':e.get('version'),'modalities':e.get('modalities',[]),'classes':e.get('classes',{}),'evidence':e.get('evidence_scope'),'state':state,'missing_dependencies':missing,'hash':e.get('weights',{}).get('sha256')})
        return {'version':__version__,'deployment':'hosted' if self.hosted else 'local','max_upload_mib':32 if self.hosted else 2048,'models':rows,'unavailable':['SSS cylinder: no validated SSS specialist','Real entangled nets: no verified detector'],'worker_limit':1,'queue_limit':self.queue_limit,'memory_limit_mib':self.memory_mib,'mode':'CPU, loopback only','setup':'Local administrator: bluecho models verify/fetch/import --model MODEL --registry YOUR_REGISTRY. No automatic downloads.'}
    def record_source(self,path,original_name):
        info=inspect_input(path);identifier=path.parent.name
        info.pop('path',None)
        s={'id':identifier,'filename':original_name,'path':str(path),'info':info,'metadata_available':info.get('format')=='georeferenced_raster','sidecar':None,'created':now()}
        with self.db() as db:db.execute('INSERT INTO sources VALUES(?,?)',(identifier,json.dumps(s)))
        if self.sessions:self.sessions.claim('source',identifier)
        return self.public_source(s)
    def job(self,identifier):
        self.checked(identifier)
        if self.sessions:self.sessions.check('job',identifier)
        with self.db() as db:row=db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()
        if not row:raise HTTPException(404,'Job not found')
        x=dict(row);x['request']=json.loads(x.pop('payload'));x['filename']=self.source(x['request']['source_id'])['filename']
        p=self.path(identifier)/'progress.json';x['progress']=json.loads(p.read_text()) if p.exists() else {'stage':x['state']}
        x['windows']=[{'id':str(i),'label':f'Window {i+1}','reference':json.loads(p.read_text()).get('source_reference',{})} for i,p in enumerate(self.files(identifier))]
        x['saved_example']=x['request'].get('saved_example',False)
        finished=self.path(identifier)/'finished.json';x['runtime']=json.loads(finished.read_text()) if finished.exists() else None
        x['cancellation_requested']=(self.path(identifier)/'cancel').exists()
        recording=self.path(identifier)/'out'/'recording.json';x['recording']=json.loads(recording.read_text()) if recording.exists() else None
        return x
    def files(self,identifier):
        root=self.path(identifier);done=root/'finished.json'
        complete=done.exists() and json.loads(done.read_text()).get('state')=='completed_with_warnings'
        return sorted(p for p in (root/'out').rglob('results.json') if complete or (p.parent/'.dashboard-complete').exists())
    def result_file(self,job,window):
        self.job_exists(job)
        if not str(window).isdigit():raise HTTPException(404,'Window not found')
        files=self.files(job);n=int(window)
        if n>=len(files):raise HTTPException(404,'Window not exported yet')
        return files[n]
    def job_exists(self,job):
        self.checked(job)
        if self.sessions:self.sessions.check('job',job)
        with self.db() as db:exists=db.execute('SELECT 1 FROM jobs WHERE id=?',(job,)).fetchone()
        if not exists:raise HTTPException(404,'Job not found')
    def create_job(self,request,kind='inference',extra=None):
        s=self.source(request['source_id']);caps={e['id']:e for e in self.caps()['models']}
        if kind=='inference':
            if len(set(request['models']))!=len(request['models']):raise HTTPException(422,'Select distinct models')
            for model in request['models']:
                if model not in caps or request['modality'] not in caps[model]['modalities']:raise HTTPException(422,'Model and modality are incompatible')
                if caps[model]['state']!='ready':raise HTTPException(422,model+': '+caps[model]['state'])
            if s['info']['format']=='XTF' and (request['modality']!='SSS' or request.get('channel') is None):raise HTTPException(422,'XTF requires SSS and an explicit channel')
        with self.lock,self.db() as db:
            n=db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','validating','processing','exporting')").fetchone()[0]
            if n>=self.queue_limit:raise HTTPException(429,'Inspection queue is full; wait or cancel a queued job')
            identifier=uid();directory=self.path(identifier);directory.mkdir(parents=True)
            payload={**request,'kind':kind,'registry':str(self.registry),'source':s['path'],'sidecar':s.get('sidecar'),'memory_mib':self.memory_mib,**(extra or {})}
            if payload.get('sidecar'):
                original=Path(payload['sidecar']);target=directory/('sidecar'+original.suffix);shutil.copyfile(original,target);payload['sidecar']=str(target)
            atomic_json(directory/'request.json',payload);db.execute('INSERT INTO jobs(id,state,payload,created,message) VALUES(?,?,?,?,?)',(identifier,'queued',json.dumps({**request,'kind':kind}),now(),'Waiting for CPU worker'))
        if self.sessions:self.sessions.claim('job',identifier)
        return self.job(identifier)
    def work(self):
        while not self.stop.wait(.15):
            with self.lock,self.db() as db:
                row=db.execute("SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
                if not row:continue
                identifier=row[0];db.execute("UPDATE jobs SET state='validating',message='Preparing worker' WHERE id=?",(identifier,))
            directory=self.path(identifier)
            env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'2','PROJ_NETWORK':'OFF'}
            with (directory/'worker.log').open('w') as log:
                self.child=subprocess.Popen([sys.executable,'-m','bluecho.dashboard.worker',str(directory)],stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                cancelled_at=None;worker_started=time.monotonic()
                while self.child.poll() is None:
                    if self.hosted and time.monotonic()-worker_started>180:
                        self.child.kill();self.child.wait()
                        atomic_json(directory/'finished.json',{'state':'failed','message':'Hosted analysis exceeded 180 seconds. Use a smaller input or the local application.'})
                        break
                    if os.name == 'nt':
                        import psutil
                        try:
                            rss=psutil.Process(self.child.pid).memory_info().rss
                            if rss > self.memory_mib * 1024**2:
                                self.child.kill();self.child.wait()
                                atomic_json(directory/'finished.json',{'state':'failed','message':'Worker exceeded the local memory budget. Use a smaller source or recording window.','memory_limit_method':'supervisor RSS sampling'})
                                break
                        except psutil.NoSuchProcess:
                            pass
                    if self.stop.is_set():(directory/'cancel').touch()
                    if (directory/'cancel').exists():
                        cancelled_at=cancelled_at or time.monotonic()
                        if time.monotonic()-cancelled_at>20:self.child.kill()
                        elif time.monotonic()-cancelled_at>10:self.child.terminate()
                    progress=directory/'progress.json'
                    if progress.exists():
                        stage=json.loads(progress.read_text()).get('stage')
                        state='exporting' if stage=='exporting' else 'processing'
                        with self.db() as db:db.execute('UPDATE jobs SET state=? WHERE id=?',(state,identifier))
                    time.sleep(.1)
            finished=directory/'finished.json'
            result=json.loads(finished.read_text()) if finished.exists() else {'state':'cancelled' if (directory/'cancel').exists() else 'failed','message':'Worker stopped; partial exported windows retained'}
            with self.db() as db:db.execute('UPDATE jobs SET state=?,message=? WHERE id=?',(result['state'],result['message'],identifier))
            self.child=None
    def events(self,job,window):
        with self.db() as db:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM reviews WHERE job=? AND window=? ORDER BY event',(job,window))]
    def canonical(self,job,window):
        path=self.result_file(job,window);r=json.loads(path.read_text());events=self.events(job,window)
        for e in events:
            for d in r['detections']+r.get('unvalidated_proposals',[]):
                if d['candidate_id']==e.get('candidate_id'):
                    d.setdefault('original_prediction',copy.deepcopy(d));d.update(e['new']);d.setdefault('review_history',[]).append(e)
        j=self.job(job)
        r['schema_version']='2.1.0';r['review_records']=r.get('review_records',[])+events;r['review_revision']=j['revision'];r['job_state']=j['state'];r['saved_example']=j['saved_example']
        r['processing_extent']={'request':j['request'],'recording':j['recording'],'successfully_exported_windows':len(j['windows'])}
        r['rescan_requests']=[e for e in events if e['action']=='needs_scan']
        frame=geotag_box([0,0,r['image_dimensions']['width'],r['image_dimensions']['height']],r.get('positioning_metadata'))
        r['map_layers']={'processed':[{'geometry':{'type':'Polygon','coordinates':[frame['geographic_footprint']]}}] if frame.get('geographic_footprint') else []}
        return r
    def review(self,job,window,candidate,body):
        with self.lock,self.db() as db:
            db.execute('BEGIN IMMEDIATE');revision=db.execute('SELECT revision FROM jobs WHERE id=?',(job,)).fetchone()
            if not revision:raise HTTPException(404,'Job not found')
            if revision[0]!=body.revision:raise HTTPException(409,'Review changed in another tab. Refresh before saving.')
            r=self.canonical(job,window);d=next((d for d in r['detections']+r['unvalidated_proposals'] if d['candidate_id']==candidate),None)
            if d is None:raise HTTPException(404,'Candidate not found')
            new={'review_state':{'retain':'retained_candidate','false_alert':'false_alert','uncertain':'uncertain','note':d['review_state'],'corrected':'corrected_by_reviewer'}[body.action]}
            if body.label is not None:new['class_name']=body.label
            if body.box is not None:
                import math
                a,b,c,e=body.box;w=r['image_dimensions']['width'];h=r['image_dimensions']['height']
                if not all(math.isfinite(v) for v in body.box) or not 0<=a<c<=w or not 0<=b<e<=h:raise HTTPException(422,'Corrected box must have positive area inside the original image')
                new.update(box_xyxy_pixels=body.box,pixel_dimensions={'width':c-a,'height':e-b},**geotag_box(body.box,r.get('positioning_metadata')))
            event={'revision':revision[0]+1,'candidate_id':candidate,'source_sha256':d['source_sha256'],'action':body.action,'reviewer':body.reviewer,'timestamp':now(),'note':body.note,'old':{k:d.get(k) for k in new},'new':new,'field_verification':False}
            db.execute('INSERT INTO reviews(job,window,candidate,payload) VALUES(?,?,?,?)',(job,window,candidate,json.dumps(event)));db.execute('UPDATE jobs SET revision=revision+1 WHERE id=?',(job,))
        return event
    def rescan(self,job,window,body):
        with self.lock,self.db() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT revision FROM jobs WHERE id=?',(job,)).fetchone()
            if not row or row[0]!=body.revision:raise HTTPException(409,'Refresh before adding a scan request')
            r=self.canonical(job,window);a,b,c,d=body.region;w=r['image_dimensions']['width'];h=r['image_dimensions']['height']
            if not 0<=a<c<=w or not 0<=b<d<=h:raise HTTPException(422,'Region outside image')
            event={'revision':row[0]+1,'action':'needs_scan','origin':'human_action','region':body.region,'reason':body.reason,'reviewer':body.reviewer,'timestamp':now(),'geometry':geotag_box(body.region,r.get('positioning_metadata'))}
            db.execute('INSERT INTO reviews(job,window,payload) VALUES(?,?,?)',(job,window,json.dumps(event)));db.execute('UPDATE jobs SET revision=revision+1 WHERE id=?',(job,))
        return event


def create_app(storage,registry,examples=None,*,queue_limit=8,memory_mib=8192,hosted=False,allowed_hosts=(),allowed_origins=()):
    service=Service(storage,registry,examples,queue_limit,memory_mib)
    if hosted:
        from .sessions import Sessions,owner
        service.hosted=True;service.sessions=Sessions(service)
    @asynccontextmanager
    async def lifespan(app):
        thread=threading.Thread(target=service.work,daemon=True);thread.start()
        yield
        service.stop.set();thread.join(timeout=15)
    app=FastAPI(title='BluEcho local inspection API',version='1.0',lifespan=lifespan);app.state.service=service
    @app.middleware('http')
    async def local_guard(request,call_next):
        host=request.headers.get('host','').split(':')[0]
        if host not in ('127.0.0.1','localhost','testserver','[::1]',*allowed_hosts):return JSONResponse({'detail':'Host is not configured for this service'},status_code=403)
        origin=request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in (str(request.base_url).rstrip('/'),*allowed_origins):
            return JSONResponse({'detail':'Cross-origin writes are disabled'},status_code=403)
        if hosted and request.url.path.startswith('/api/'):
            current=service.sessions.identity(request.cookies.get('bluecho-session'))
            context=owner.set(current)
            try:
                content_length=request.headers.get('content-length','0')
                if not content_length.isdigit() or int(content_length)>33*1024**2:
                    return JSONResponse({'detail':'Hosted uploads are limited to 32 MiB. Use the local app for large recordings.'},status_code=413)
                if request.method=='POST' and request.url.path=='/api/v1/sources' and len(service.sessions.ids('source'))>=20:
                    return JSONResponse({'detail':'This browser session has reached its 20-source limit.'},status_code=429)
                if request.method=='POST' and request.url.path=='/api/v1/jobs':
                    body=await request.json()
                    service.sessions.check('source',body.get('source_id',''))
                    if len(service.sessions.ids('job'))>=40:
                        return JSONResponse({'detail':'This browser session has reached its 40-inspection limit.'},status_code=429)
                    if not 0<int(body.get('max_pings',128))<=512:
                        return JSONResponse({'detail':'Hosted recordings require a ping limit from 1 to 512.'},status_code=422)
                response=await call_next(request)
                if not request.cookies.get('bluecho-session') or service.sessions.identity(request.cookies.get('bluecho-session'))!=current:
                    response.set_cookie('bluecho-session',service.sessions.sign(current),httponly=True,secure=True,samesite='lax',max_age=86400)
                response.headers['Cache-Control']='no-store'
            except HTTPException as exc:
                response=JSONResponse({'detail':exc.detail},status_code=exc.status_code)
            finally:
                owner.reset(context)
        else:
            response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';return response
    @app.exception_handler(UnidentifiedImageError)
    @app.exception_handler(struct.error)
    @app.exception_handler(ValueError)
    async def value_error(request,exc):
        message='Invalid or unsupported image content' if isinstance(exc,UnidentifiedImageError) else str(exc)
        message=message.replace(str(service.root),'[managed storage]').replace(str(service.registry),'[model registry]')
        return JSONResponse({'detail':message[:400]},status_code=422)
    @app.get('/api/v1/health')
    def health():return {'status':'ok','version':__version__,'worker_limit':1,'offline_capable':True}
    @app.get('/api/v1/capabilities')
    def capabilities():return service.caps()
    @app.post('/api/v1/sources')
    async def upload(file:UploadFile=File(...)):
        identifier=uid();name=Path(file.filename or 'unnamed').name;extension=Path(name).suffix.lower()
        if extension not in ('.xtf','.png','.jpg','.jpeg','.bmp','.pbm','.tif','.tiff'):raise HTTPException(422,'Supported images, GeoTIFF or XTF only; raw SL2/ARIS are not supported')
        if shutil.disk_usage(service.root).free<3*1024**3:raise HTTPException(507,'Keep at least 3 GiB free before uploading; archive old inspections locally')
        with service.db() as db:
            if db.execute('SELECT count(*) FROM sources').fetchone()[0]>=500:raise HTTPException(429,'Local source quota reached (500). Archive this storage directory and start a new one.')
        directory=service.root/'sources'/identifier;directory.mkdir(parents=True);path=directory/('source'+extension);size=0
        try:
            with path.open('wb') as out:
                while chunk:=await file.read(1024**2):
                    size+=len(chunk)
                    if size>(32*1024**2 if hosted else 2*1024**3):raise HTTPException(413,'Maximum source size is 32 MiB hosted / 2 GiB locally')
                    out.write(chunk)
            return await run_in_threadpool(service.record_source,path,name)
        except Exception:
            shutil.rmtree(directory);raise
    @app.get('/api/v1/sources/{source_id}')
    def source_info(source_id:str):
        return service.public_source(service.source(source_id))
    @app.post('/api/v1/sources/{source_id}/metadata')
    async def metadata(source_id:str,file:UploadFile=File(...)):
        s=service.source(source_id)
        if 'width' not in s['info']:raise HTTPException(422,'Raw XTF metadata must be bound to a decoded window; use its explicit packet metadata')
        data=await file.read(32*1024**2+1)
        if len(data)>32*1024**2:raise HTTPException(413,'Metadata exceeds 32 MiB')
        suffix='.csv' if Path(file.filename or '').suffix=='.csv' else '.json';p=Path(s['path']).parent/('metadata'+suffix);p.write_bytes(data)
        try:load_sidecar(p,s['path'],s['info']['width'],s['info']['height'])
        except Exception:p.unlink(missing_ok=True);raise
        s['sidecar']=str(p);s['metadata_available']=True
        with service.db() as db:db.execute('UPDATE sources SET payload=? WHERE id=?',(json.dumps(s),source_id))
        return service.public_source(s)
    @app.post('/api/v1/jobs')
    def create(request:JobRequest):return service.create_job(request.model_dump())
    @app.get('/api/v1/jobs')
    def jobs():
        with service.db() as db:ids=[r[0] for r in db.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT 100')]
        if service.sessions:ids=[i for i in ids if i in service.sessions.ids('job')]
        return [service.job(i) for i in ids]
    @app.get('/api/v1/jobs/{job}')
    def job_status(job:str):return service.job(job)
    @app.post('/api/v1/jobs/{job}/cancel')
    def cancel(job:str):
        j=service.job(job)
        if j['state'] not in ACTIVE:return j
        (service.path(job)/'cancel').touch()
        with service.lock,service.db() as db:db.execute("UPDATE jobs SET state='cancelled',message='Cancelled before processing' WHERE id=? AND state='queued'",(job,))
        return service.job(job)
    @app.get('/api/v1/jobs/{job}/windows/{window}')
    def result(job:str,window:str):return service.canonical(job,window)
    @app.get('/api/v1/jobs/{job}/windows/{window}/evidence/{name:path}')
    def evidence(job:str,window:str,name:str):
        base=service.result_file(job,window).parent;path=(base/name).resolve()
        if not path.is_relative_to(base.resolve()) or path.suffix not in ('.png','.jpg','.svg') or not path.is_file():raise HTTPException(404,'Evidence not found')
        return FileResponse(path,headers={'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; sandbox"})
    @app.post('/api/v1/jobs/{job}/windows/{window}/review/{candidate}')
    def review(job:str,window:str,candidate:str,body:ReviewRequest):return service.review(job,window,candidate,body)
    @app.post('/api/v1/jobs/{job}/windows/{window}/rescan')
    def rescan(job:str,window:str,body:ScanRequest):return service.rescan(job,window,body)
    @app.post('/api/v1/jobs/{job}/windows/{window}/geotag')
    async def geotag(job:str,window:str,file:UploadFile=File(...)):
        j=service.job(job);source=service.source(j['request']['source_id']);result=service.result_file(job,window);r=service.canonical(job,window);data=await file.read(32*1024**2+1)
        if len(data)>32*1024**2:raise HTTPException(413,'Metadata exceeds limit')
        path=service.path(job)/('metadata-'+uid()+'.json');path.write_bytes(data)
        try:load_sidecar(path,source['path'],r['image_dimensions']['width'],r['image_dimensions']['height'])
        except Exception:path.unlink(missing_ok=True);raise
        snapshot=service.path(job)/('snapshot-'+uid());snapshot.mkdir();atomic_json(snapshot/'results.json',r)
        for name in ('original.png','quality.png'):
            if (result.parent/name).exists():shutil.copyfile(result.parent/name,snapshot/name)
        return service.create_job({**j['request'],'parent_job':job,'parent_revision':r['review_revision']},kind='geotag',extra={'result':str(snapshot/'results.json'),'sidecar':str(path)})
    @app.post('/api/v1/jobs/{job}/windows/{window}/export')
    def export(job:str,window:str,body:ExportRequest):
        if hosted and shutil.disk_usage(service.root).free<3*1024**3:raise HTTPException(507,'Hosted storage is full. Download existing reports or use the local app.')
        with service.lock:
            r=service.canonical(job,window)
            if r['review_revision']!=body.revision:raise HTTPException(409,'Review changed; refresh export')
            if body.scope=='displayed':
                for kind in ('detections','unvalidated_proposals'):r[kind]=[d for d in r[kind] if d['candidate_id'] in body.candidate_ids]
            r['export_scope']=body.scope;export_id=uid();out=service.root/'exports'/export_id;out.mkdir(parents=True);base=service.result_file(job,window).parent
            image=Image.open(base/'original.png').convert('RGB')
            if (base/'quality.png').exists():shutil.copyfile(base/'quality.png',out/'quality.png')
            export_result(r,out,image);atomic_json(out/'reviews.json',r['review_records']);atomic_json(out/'original_predictions.json',json.loads(service.result_file(job,window).read_text()))
            # CSV and GeoJSON include the current revision and review history.
            csv_path=out/'detections.csv';cs=list(csv.DictReader(csv_path.open()));fields=list(cs[0]) if cs else next(csv.reader(csv_path.open()));fields+=['review_revision','review_history']
            ds={d['candidate_id']:d for d in r['detections']+r['unvalidated_proposals']}
            with csv_path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                for row in cs:w.writerow({**row,'review_revision':body.revision,'review_history':json.dumps(ds[row['candidate_id']].get('review_history',[]))})
            g=json.loads((out/'detections.geojson').read_text())
            for feature in g['features']:feature['properties'].update(review_revision=body.revision,review_history=ds[feature['properties']['candidate_id']].get('review_history',[]))
            atomic_json(out/'detections.geojson',g)
            html_path=out/'report.html';html_path.write_text(html_path.read_text().replace('</html>',f'<p>Review revision {body.revision}; export scope {body.scope}. <a href="reviews.json">Review history</a> Â· <a href="original_predictions.json">Original predictions</a></p></html>'))
            with zipfile.ZipFile(out/'inspection.zip','w',zipfile.ZIP_DEFLATED) as z:
                for p in out.rglob('*'):
                    if p.is_file() and p.name!='inspection.zip':z.write(p,str(p.relative_to(out)))
        name={'json':'results.json','csv':'detections.csv','geojson':'detections.geojson','html':'inspection.zip','zip':'inspection.zip'}[body.format]
        return FileResponse(out/name,filename=f'bluecho-{job[:8]}-r{body.revision}-'+name,media_type='application/zip' if name.endswith('.zip') else None)
    @app.get('/api/v1/examples')
    def examples_list():return [{k:v for k,v in e.items() if k not in ('source','saved')} for e in service.examples]
    @app.post('/api/v1/examples/{example}/{mode}')
    def example(example:str,mode:Literal['run','saved']):
        e=next((x for x in service.examples if x['id']==example),None)
        if not e:raise HTTPException(404,'Example not configured')
        identifier=uid();directory=service.root/'sources'/identifier;directory.mkdir(parents=True);src=Path(e['source']);dest=directory/('source'+src.suffix);shutil.copyfile(src,dest);service.record_source(dest,src.name)
        request={**e['request'],'source_id':identifier}
        if mode=='run':return service.create_job(request)
        if not e.get('saved'):raise HTTPException(404,'No saved output for this example')
        job_id=uid();out=service.path(job_id)/'out';out.mkdir(parents=True)
        for p in Path(e['saved']).rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.json','.png','.jpg','.csv','.geojson','.svg','.html'):
                target=out/p.relative_to(e['saved']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        for result in out.rglob('results.json'):(result.parent/'.dashboard-complete').touch()
        with service.db() as db:db.execute('INSERT INTO jobs(id,state,payload,created,message) VALUES(?,?,?,?,?)',(job_id,'completed_with_warnings',json.dumps({**request,'saved_example':True}),now(),'Saved example opened. No new inference was run.'))
        if service.sessions:service.sessions.claim('job',job_id)
        return service.job(job_id)
    static=Path(__file__).parent/'static'
    if static.exists():app.mount('/',StaticFiles(directory=static,html=True),name='frontend')
    return app

def launch(registry,storage,port=8010,examples=None):
    import uvicorn
    uvicorn.run(create_app(storage,registry,examples),host='127.0.0.1',port=port)
