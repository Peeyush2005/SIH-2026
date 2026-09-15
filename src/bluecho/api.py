"""Single-worker loopback service. Review events never mutate model predictions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Literal
import uuid
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import run_in_threadpool
from .engine import Engine, InputError, SUFFIXES, read_image
from .export import export, write_csv, write_json

MAX_UPLOAD = 25 * 1024 * 1024


class Review(BaseModel):
    status: Literal['accepted','rejected','relabelled']
    label: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def label_required(self):
        if self.status=='relabelled' and not (self.label and self.label.strip()):
            raise ValueError('Relabelled review requires a nonempty label')
        return self


def create_app(manifest, jobs, *, device='cpu', engine_factory=Engine):
    root=Path(jobs).resolve();root.mkdir(parents=True,exist_ok=True)
    database=root/'jobs.sqlite3';queue_slots=threading.BoundedSemaphore(8)
    def connect():
        connection=sqlite3.connect(database,timeout=30);connection.row_factory=sqlite3.Row
        return connection
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT, progress REAL, source TEXT, modality TEXT, error TEXT, created_at TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS reviews (event INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT, detection TEXT, status TEXT, label TEXT, note TEXT, at TEXT)')
        db.execute("UPDATE jobs SET state='failed',error='Service restarted before completion; submit the image again' WHERE state IN ('queued','running')")
    pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bluecho-inference')
    state={'engine':None,'model_status':'loading','error':None}

    @asynccontextmanager
    async def lifespan(app):
        try:
            state['engine']=await run_in_threadpool(engine_factory,manifest,device=device)
            state['model_status']='ready'
        except Exception as exc:
            state.update(model_status='failed',error=f'{type(exc).__name__}: {exc}')
        yield
        pool.shutdown(wait=True)

    app=FastAPI(title='BluEcho local inference and review',version='0.1.0',lifespan=lifespan,
                description='Loopback development service; not a publicly secured multi-user service. One model and one inference job at a time.')

    def job_record(job_id):
        if not re.fullmatch('[a-f0-9]{32}',job_id):raise HTTPException(404,'Job not found')
        with connect() as db:row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None:raise HTTPException(404,'Job not found')
        return dict(row)

    def done(job_id):
        record=job_record(job_id)
        if record['state']!='completed':raise HTTPException(409,f"Job is {record['state']}; results are unavailable")
        return root/job_id/'result'

    def reviews_for(job_id):
        with connect() as db:rows=db.execute('SELECT detection,status,label,note,at,event FROM reviews WHERE job=? ORDER BY event',(job_id,)).fetchall()
        return {row['detection']:dict(row) for row in rows}

    def process(job_id,source,modality,reference):
        try:
            with connect() as db:db.execute("UPDATE jobs SET state='running' WHERE id=?",(job_id,))
            def progress(n,total):
                with connect() as db:db.execute('UPDATE jobs SET progress=? WHERE id=?',(n/total,job_id))
            prediction=state['engine'].predict(source,modality=modality,progress=progress,source_reference=reference)
            export(prediction,root/job_id/'result',source=source)
            with connect() as db:db.execute("UPDATE jobs SET state='completed',progress=1 WHERE id=?",(job_id,))
        except Exception as exc:
            with connect() as db:db.execute("UPDATE jobs SET state='failed',error=? WHERE id=?",(f'{type(exc).__name__}: {exc}',job_id))
        finally:queue_slots.release()

    @app.get('/health')
    def health():return {'service':'ok','model_status':state['model_status'],'model_error':state['error']}

    @app.get('/capabilities')
    def capabilities():
        return {'model_status':state['model_status'],'model':state['engine'].info() if state['engine'] else None,
                'max_upload_bytes':MAX_UPLOAD,'max_pixels':30_000_000,'concurrent_inference_jobs':1,
                'accepted_extensions':sorted(SUFFIXES),'public_multiuser_security':False,'review_persistence':'SQLite append-only events'}

    @app.post('/jobs',status_code=202)
    async def upload(file:UploadFile=File(...),modality:str=Form(...)):
        if state['model_status']!='ready':raise HTTPException(503,'Model is unavailable; inspect /health')
        if modality!='SSS_LF':raise HTTPException(422,'Unsupported modality; explicitly declare SSS_LF for this model')
        reference=Path((file.filename or '').replace('\\','/')).name[:200]
        suffix=Path(reference).suffix.lower()
        if suffix not in SUFFIXES:raise HTTPException(415,'Unsupported image extension or raw sonar format')
        if not queue_slots.acquire(blocking=False):raise HTTPException(429,'Job queue is full; retry after a job completes')
        job_id=uuid.uuid4().hex;folder=root/job_id;source=folder/('source'+suffix)
        size=0;submitted=False
        try:
            folder.mkdir()
            with source.open('xb') as stream:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_UPLOAD:raise HTTPException(413,'Upload exceeds 25 MiB')
                    stream.write(chunk)
            await run_in_threadpool(read_image,source)
            with connect() as db:
                db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)',(job_id,'queued',0,reference,modality,None,datetime.now(timezone.utc).isoformat()))
            pool.submit(process,job_id,source,modality,reference)
            submitted=True
        except BaseException as exc:
            with suppress(OSError):source.unlink(missing_ok=True)
            with suppress(OSError):folder.rmdir()
            with suppress(sqlite3.Error), connect() as db:
                db.execute("UPDATE jobs SET state='failed',error='Could not queue job; submit again' WHERE id=?",(job_id,))
            if isinstance(exc,InputError):raise HTTPException(422,str(exc)) from exc
            raise
        finally:
            if not submitted:queue_slots.release()
            await file.close()
        return {'job_id':job_id,'state':'queued','status_url':f'/jobs/{job_id}'}

    @app.get('/jobs/{job_id}')
    def status(job_id:str):return job_record(job_id)

    @app.get('/jobs/{job_id}/results')
    def results(job_id:str):
        path=done(job_id)
        return {'prediction':json.loads((path/'predictions.json').read_text()),'reviews':reviews_for(job_id),
                'evidence':json.loads((path/'evidence.json').read_text())}

    @app.get('/jobs/{job_id}/evidence/{name:path}')
    def evidence(job_id:str,name:str):
        path=done(job_id);allowed=json.loads((path/'evidence.json').read_text())
        requested=(path/name).resolve()
        if name not in allowed or not requested.is_relative_to(path.resolve()) or not requested.is_file():
            raise HTTPException(404,'Evidence not found')
        return FileResponse(requested,media_type='image/png')

    @app.put('/jobs/{job_id}/review/{detection_id}')
    def review(job_id:str,detection_id:str,value:Review):
        path=done(job_id);prediction=json.loads((path/'predictions.json').read_text())
        if detection_id not in {d['detection_id'] for d in prediction['detections']}:raise HTTPException(404,'Detection not found')
        now=datetime.now(timezone.utc).isoformat()
        with connect() as db:
            db.execute('INSERT INTO reviews (job,detection,status,label,note,at) VALUES (?,?,?,?,?,?)',
                       (job_id,detection_id,value.status,value.label,value.note,now))
        return {'detection_id':detection_id,**value.model_dump(),'at':now}

    @app.get('/jobs/{job_id}/export/{format}')
    def download(job_id:str,format:Literal['json','csv']):
        path=done(job_id);prediction=json.loads((path/'predictions.json').read_text());reviews=reviews_for(job_id)
        # A unique export snapshot avoids concurrent requests overwriting each other's responses.
        target=root/job_id/f'export_{uuid.uuid4().hex}.{format}'
        if format=='json':write_json(target,{'prediction':prediction,'reviews':reviews})
        else:write_csv(target,prediction,reviews)
        return FileResponse(target,filename=f'{job_id}.{format}',media_type='application/json' if format=='json' else 'text/csv')

    return app
