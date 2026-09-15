"""One CPU job per child process. No user code or model URLs accepted."""
import json,os,signal,sys,time,resource
from pathlib import Path

def main():
    directory=Path(sys.argv[1]);payload=json.loads((directory/'request.json').read_text())
    resource.setrlimit(resource.RLIMIT_AS,(payload.get('memory_mib',8192)*1024**2,)*2)
    from bluecho.phase1.download import atomic_json
    started=time.monotonic()
    def cancel(*a):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,cancel)
    def progress(event):
        if event.get('stage')=='window_complete':
            completed=Path(event['output'])
            if completed.resolve().is_relative_to(directory.resolve()):(completed/'.dashboard-complete').touch()
        public={k:v for k,v in event.items() if k!='output'}
        atomic_json(directory/'progress.json',{**public,'elapsed_seconds':round(time.monotonic()-started,2)})
        # Let the engine append its completed-window manifest before cancellation.
        if (directory/'cancel').exists() and event.get('stage')!='window_complete':raise KeyboardInterrupt
    try:
        progress({'stage':'validating'})
        if payload['kind']=='geotag':
            from bluecho.geotag import geotag_saved
            progress({'stage':'geotagging'})
            geotag_saved(payload['result'],payload['source'],payload['sidecar'],directory/'out')
            (directory/'out'/'.dashboard-complete').touch()
        else:
            from bluecho.phase1.engine import RecordingEngine
            engine=RecordingEngine(payload['registry'],device='cpu',cache_models=1)
            engine.predict(payload['source'],directory/'out',model_ids=payload['models'],modality=payload['modality'],sidecar=payload.get('sidecar'),channel=payload.get('channel'),start_ping=payload.get('start_ping',0),max_pings=payload.get('max_pings',128),chunk_pings=payload.get('chunk_pings',128),progress=progress)
        progress({'stage':'complete'})
        state='completed_with_warnings' # Every route has documented field/class limitations.
        detail='Processing complete. Review model, quality and location limitations.'
    except KeyboardInterrupt:state='cancelled';detail='Cancelled. Only successfully exported windows are available.'
    except Exception as exc:
        state='failed';detail=str(exc)
        for path in [payload.get('registry'),str(directory),payload.get('source'),payload.get('result')]:
            if path:detail=detail.replace(path,'[managed file]')
        detail=detail[:500] or type(exc).__name__
    atomic_json(directory/'finished.json',{'state':state,'message':detail,'elapsed_seconds':time.monotonic()-started,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
if __name__=='__main__':main()
