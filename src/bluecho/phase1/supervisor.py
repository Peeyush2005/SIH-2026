"""Persistent single-worker queue; cumulative worker time survives supervisor restart."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import psutil
from .download import atomic_json, digest


def read(path):
    return json.loads(Path(path).read_text())


def identity(pid, created):
    try:
        p=psutil.Process(pid)
        return p if abs(p.create_time()-created)<.01 and p.status()!=psutil.STATUS_ZOMBIE else None
    except psutil.Error:return None


def initialize(root):
    root=Path(root).resolve();plan=read(root/'queue.json')
    if not 0<plan['training_ceiling_seconds']<=21600:raise ValueError('Training ceiling must be at most six hours')
    ledger=root/'ledger.json'
    if ledger.exists():
        state=read(ledger)
        if state['plan_sha256']!=digest(root/'queue.json'):raise ValueError('Frozen queue binding changed')
        return plan,state
    state={'schema_version':'1.0','state':'READY','plan_sha256':digest(root/'queue.json'),'spent_seconds':float(plan.get('preflight_training_seconds',0)),'active':None,'events':[],
           'jobs':{j['id']:{'state':'QUEUED','attempts':0,'spent_seconds':0.,'batch':j.get('batch',16)} for j in plan['jobs']}}
    atomic_json(ledger,state);return plan,state


def charge(state):
    a=state.get('active')
    if not a:return
    now=time.monotonic();wall=time.time()
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    # Monotonic continuity on the same boot. Across boots, charge the wall gap
    # conservatively instead of granting a fresh budget after uncertain shutdown.
    delta=max(0,now-a['last_monotonic']) if boot==a['boot_id'] else max(0,wall-a['last_wall'])
    state['spent_seconds']+=delta;state['jobs'][a['job']]['spent_seconds']+=delta
    a.update(last_monotonic=now,last_wall=wall,boot_id=boot)


def snapshot(root):
    plan,state=initialize(root)
    charge(state)
    return {**state,'remaining_seconds':max(0,plan['training_ceiling_seconds']-state['spent_seconds'])}


def run(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    with (root/'supervisor.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('A supervisor already owns this queue')
        plan,state=initialize(root)
        def save():
            state['updated_at']=time.time();state['supervisor_pid']=os.getpid()
            state['remaining_seconds']=max(0,plan['training_ceiling_seconds']-state['spent_seconds'])
            atomic_json(root/'ledger.json',state)
        def stop_signal(*_):
            (root/'STOP').touch()
        signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
        active=state.get('active')
        if active:
            charge(state)
            p=identity(active['pid'],active['create_time'])
            # A recovered supervisor adopts the exact same worker rather than
            # starting another GPU job. If the worker died, retain its last snapshot.
            if p:
                state['events'].append({'event':'adopted_worker','pid':p.pid,'time':time.time()})
            else:
                state['jobs'][active['job']]['state']='INTERRUPTED'
                state['active']=None
        save()
        for job in plan['jobs']:
            js=state['jobs'][job['id']];out=root/job['id'];out.mkdir(exist_ok=True)
            if js['state']=='COMPLETE':continue
            if js['state'] in ('EVALUATING','POST_FAILED'):
                js['state']='TRAINED'  # Retry post-processing only, never retrain.
            if (root/'STOP').exists():state['state']='STOPPED';save();return
            # Validate immutable data/model/config inputs before any new worker.
            for binding in job.get('bindings',[]):
                if digest(binding['path'])!=binding['sha256']:raise ValueError('Job input hash changed: '+binding['path'])
            while js['state'] not in ('TRAINED','COMPLETE'):
                left=min(plan['training_ceiling_seconds']-state['spent_seconds'],job['allocation_seconds']-js['spent_seconds'])
                reserve=min(90,job.get('checkpoint_reserve_seconds',90))
                if left<=reserve:
                    js['state']='BUDGET_EXHAUSTED';state['state']='BUDGET_EXHAUSTED';save();break
                if js['attempts']>=job.get('max_attempts',3) and not state.get('active'):
                    js['state']='FAILED';save();break
                if not state.get('active'):
                    js['attempts']+=1
                    if (out/'worker_result.json').exists():
                        (out/'worker_result.json').replace(out/f'previous_result_{js["attempts"]-1}.json')
                    cfg={**job,'batch':js['batch'],'attempt':js['attempts'],'deadline_monotonic':time.monotonic()+left-reserve,'output':str(out),'stop_file':str(root/'STOP')}
                    atomic_json(out/'worker_config.json',cfg)
                    log=(out/f'attempt_{js["attempts"]}.log').open('a')
                    cmd=[sys.executable,'-m','bluecho.phase1.training','worker','--config',str(out/'worker_config.json')]
                    p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close()
                    state['active']={'job':job['id'],'pid':p.pid,'create_time':psutil.Process(p.pid).create_time(),'last_monotonic':time.monotonic(),'last_wall':time.time(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'started_wall':time.time()}
                    js['state']='RUNNING';state['state']='RUNNING';save()
                else:p=None
                stopping_at=None
                while True:
                    a=state['active'];worker=identity(a['pid'],a['create_time'])
                    charge(state)
                    if worker is None:break
                    try:
                        rss=sum(q.memory_info().rss for q in [worker,*worker.children(recursive=True)] if q.is_running())
                    except psutil.Error:rss=None
                    state['host']={'available_bytes':psutil.virtual_memory().available,'worker_tree_rss_bytes':rss}
                    try:
                        gpu=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3)
                        state['gpu']=gpu.stdout.strip()
                    except Exception:state['gpu']='unavailable'
                    hb=out/'heartbeat.json';age=time.time()-max(hb.stat().st_mtime,a['started_wall']) if hb.exists() else time.time()-a['started_wall']
                    left=min(plan['training_ceiling_seconds']-state['spent_seconds'],job['allocation_seconds']-js['spent_seconds'])
                    stop=(root/'STOP').exists() or left<=reserve or age>job.get('hang_seconds',180) or (rss is not None and rss>12*1024**3)
                    if stop:
                        (out/'STOP_WORKER').touch()
                        if stopping_at is None:stopping_at=time.monotonic()
                        if time.monotonic()-stopping_at>min(reserve or 30,60) or left<=2:
                            # Kill only the worker process group whose identity was checked.
                            os.killpg(worker.pid,signal.SIGKILL)
                            state['events'].append({'event':'watchdog_killed_worker','job':job['id'],'heartbeat_age':age,'time':time.time()})
                    save();time.sleep(.25 if job['kind']=='synthetic' else 2)
                if p is not None:p.wait()
                state['active']=None
                result=read(out/'worker_result.json') if (out/'worker_result.json').exists() else {'state':'INTERRUPTED'}
                js['last_result']=result
                if result.get('state')=='TRAINED':js['state']='TRAINED'
                elif (root/'STOP').exists():js['state']='INTERRUPTED';state['state']='STOPPED';save();return
                elif result.get('state')=='BUDGET_STOP':js['state']='TRAINED' if (out/'resume.pt').exists() else 'BUDGET_EXHAUSTED'
                else:
                    if result.get('oom') or result.get('state')=='INTERRUPTED':
                        js['batch']=max(2,js['batch']//2)
                        state['events'].append({'event':'bounded_retry_batch_reduction','job':job['id'],'batch':js['batch'],'time':time.time()})
                    js['state']='INTERRUPTED'
                if (out/'STOP_WORKER').exists():(out/'STOP_WORKER').unlink()
                save()
                if js['state']=='BUDGET_EXHAUSTED':break
            # Deterministic post-run stages are installed before the queue starts.
            # They run even for a stopped-budget job when a usable checkpoint exists.
            if js['state']=='TRAINED':
                js['state']='EVALUATING';state['state']='EVALUATING';save()
                cmd=[sys.executable,'-m','bluecho.phase1.training','post','--config',str(out/'worker_config.json')]
                with (out/'post.log').open('a') as log:
                    result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
                js['state']='COMPLETE' if result.returncode==0 else 'POST_FAILED'
                save()
        state['state']='COMPLETE' if all(j['state']=='COMPLETE' for j in state['jobs'].values()) else 'COMPLETE_WITH_BLOCKERS'
        save()
        atomic_json(root/'final_status.json',state)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','resume','stop','status']);p.add_argument('--queue',required=True);a=p.parse_args();root=Path(a.queue)
    if a.action=='stop':
        root.mkdir(parents=True,exist_ok=True);(root/'STOP').touch();print('Stop requested; wait for STOPPED and a saved checkpoint')
    elif a.action=='status':print(json.dumps(snapshot(root),indent=2))
    else:
        if a.action=='resume':
            if (root/'STOP').exists():(root/'STOP').unlink()
            for flag in root.glob('*/STOP_WORKER'):flag.unlink()
        run(root)

if __name__=='__main__':main()
