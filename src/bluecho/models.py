"""Packaged model catalog and explicit checksum-verified acquisition."""
import json
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path


def capabilities():
    return [json.loads(p.read_text()) for p in sorted(files('bluecho').joinpath('catalog').iterdir(),key=str) if p.name.endswith('.json')]


def acquire(model_id,registry,*,action='verify',local=None):
    from .phase1.download import digest,atomic_json
    entry=next((e for e in capabilities() if e['id']==model_id),None)
    if entry is None or 'weights' not in entry:raise ValueError('Model unavailable or unknown')
    registry=Path(registry).resolve();entry_file=registry/(model_id+'.model.json')
    if entry_file.exists():
        existing=json.loads(entry_file.read_text())
        if existing['id']!=model_id:raise ValueError('Registry identity mismatch')
        entry=existing
    destination=(registry/entry['weights']['path']).resolve()
    if not destination.is_relative_to(registry):raise ValueError('Weight path escapes registry')
    if action=='verify':
        if not destination.is_file():raise ValueError('Weights missing; use models fetch or verified models import --local')
        if digest(destination)!=entry['weights']['sha256']:raise ValueError('Weight checksum mismatch')
        return {'status':'PASS','model':model_id,'sha256':digest(destination),'path':str(destination)}
    if action=='fetch' and destination.is_file() and digest(destination)==entry['weights']['sha256']:
        return acquire(model_id,registry,action='verify')
    registry.mkdir(parents=True,exist_ok=True)
    if not entry_file.exists():atomic_json(entry_file,entry)
    if action=='import':
        if local is None:raise ValueError('--local required')
        local=Path(local)
        if digest(local)!=entry['weights']['sha256']:raise ValueError('Local weight checksum mismatch')
        destination.parent.mkdir(parents=True,exist_ok=True);temporary=destination.with_suffix(destination.suffix+'.importing');shutil.copyfile(local,temporary);temporary.replace(destination)
        if entry.get('runtime')=='bluecho_v3':
            manifest=local.parent/'manifest.json'
            if not manifest.exists():raise ValueError('v3 import requires original manifest.json beside native.pt')
            shutil.copyfile(manifest,registry/entry['manifest'])
    elif action=='fetch':
        if model_id not in ('uatd-fls','sss-wreck-experimental'):raise ValueError('No public redistribution URL authorized: import verified local weights and original manifest')
        script=files('bluecho').joinpath('tools/install_specialists.py')
        result=subprocess.run([sys.executable,str(script),'--registry',str(registry),'--cache',str(registry/'downloads'),'--model',model_id],capture_output=True,text=True)
        if result.returncode:raise ValueError('Verified acquisition failed: '+result.stderr[-1500:])
    else:raise ValueError('Unknown model action')
    return acquire(model_id,registry,action='verify')
