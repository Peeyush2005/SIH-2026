"""Bounded resumable downloads. Network bytes, including retries, share a ledger."""
import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def download_lock(path):
    """Serialize the shared download ledger on POSIX and Windows."""
    with Path(path).open('a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            if lock.tell() == 0:
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            while True:
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (13, 11, 36):
                        raise
                    time.sleep(.1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

GIB = 1024 ** 3


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    # Windows readers may briefly hold a handle without FILE_SHARE_DELETE.
    # Keep atomic promotion; never replace it with an in-place partial write.
    for attempt in range(20):
        try:
            tmp.replace(path)
            break
        except PermissionError:
            if os.name != 'nt' or attempt == 19:
                raise
            time.sleep(.025)


def download(spec, directory, *, ceiling=2*GIB, reserve=10*GIB, retries=3, max_seconds=600):
    """Download a pinned URL with expected bytes and optional SHA256/git blob SHA1."""
    directory = Path(directory).resolve()
    started=time.monotonic()
    directory.mkdir(parents=True, exist_ok=True)
    name = spec['filename']
    if Path(name).name != name or name in ('', '.', '..'):
        raise ValueError('filename must be a basename')
    url = spec['url']
    if not url.startswith('https://'):
        raise ValueError('HTTPS source required')
    expected = int(spec['bytes'])
    if expected <= 0 or expected > ceiling:
        raise ValueError(f'Artifact size {expected} exceeds download ceiling {ceiling}')
    path = directory/name
    partial = directory/(name+'.part')
    binding = directory/(name+'.part.json')
    ledger_path = directory/'DOWNLOAD_LEDGER.json'
    with download_lock(directory/'.download.lock'):
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'network_bytes':0,'artifacts':{},'events':[]}
        ledger.update(ceiling_bytes=ceiling, minimum_free_bytes=reserve)
        def verify(p):
            if p.stat().st_size != expected:
                raise ValueError('Downloaded length mismatch')
            with p.open('rb') as f:
                head=f.read(256)
            if head.lstrip().lower().startswith((b'<!doctype',b'<html',b'version https://git-lfs')):
                raise ValueError('HTML or LFS pointer is not a model')
            sha=digest(p)
            if spec.get('sha256') and sha != spec['sha256']:
                raise ValueError('SHA256 mismatch')
            if spec.get('sha1'):
                with p.open('rb') as f:
                    if hashlib.file_digest(f,'sha1').hexdigest()!=spec['sha1']:raise ValueError('Publisher SHA1 mismatch')
            if spec.get('git_blob_sha1'):
                h=hashlib.sha1(f'blob {expected}\0'.encode())
                with p.open('rb') as f:
                    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
                if h.hexdigest()!=spec['git_blob_sha1']:raise ValueError('Pinned Git blob mismatch')
            return sha
        if path.exists():
            sha=verify(path)
            receipt={**spec,'sha256':sha,'status':'REUSED_VERIFIED','local_path':str(path)}
            ledger['artifacts'][name]=receipt
            atomic_json(ledger_path,ledger)
            return receipt
        if partial.exists() and (not binding.exists() or json.loads(binding.read_text()) != spec):
            raise ValueError('Partial file binding differs; preserve it and choose another destination')
        atomic_json(binding,spec)
        for attempt in range(retries):
            if time.monotonic()-started>=max_seconds:raise TimeoutError('Bounded download time exhausted; partial preserved')
            offset=partial.stat().st_size if partial.exists() else 0
            if offset==expected:
                sha=verify(partial);partial.replace(path)
                break
            if offset>expected:raise ValueError('Oversized partial file')
            if ledger['network_bytes']+expected-offset>ceiling:raise ValueError('Cumulative download cap would be exceeded')
            if shutil.disk_usage(directory).free-(expected-offset)<reserve:raise ValueError('Free space reserve would be violated')
            try:
                headers={'User-Agent':'BluEcho-phase1/1','Accept-Encoding':'identity'}
                if offset:headers['Range']=f'bytes={offset}-'
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25) as r:
                    if r.status==206:
                        match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',r.headers.get('Content-Range',''))
                        if not match or int(match[1])!=offset or int(match[3])!=expected:
                            raise ValueError('Server returned an incompatible byte range')
                    elif r.status==200:
                        offset=0  # Server ignored Range; restart rather than append.
                    else:raise ValueError(f'Unexpected HTTP status {r.status}')
                    if r.headers.get('Content-Length') and int(r.headers['Content-Length']) != expected-offset:
                        raise ValueError('Server length does not match pinned artifact')
                    with partial.open('ab' if offset else 'wb') as f:
                        total=offset
                        while True:
                            if time.monotonic()-started>=max_seconds:raise TimeoutError('Bounded download time exhausted; partial preserved')
                            chunk=r.read(min(256*1024, expected-total+1))
                            if not chunk:break
                            ledger['network_bytes']+=len(chunk)
                            atomic_json(ledger_path,ledger)
                            if ledger['network_bytes']>ceiling or total+len(chunk)>expected:
                                raise ValueError('Download exceeded byte budget or expected size')
                            if shutil.disk_usage(directory).free-len(chunk)<reserve:raise ValueError('Minimum free space reached')
                            f.write(chunk);total+=len(chunk)
                        f.flush();os.fsync(f.fileno())
                sha=verify(partial);partial.replace(path)
                break
            except Exception as exc:
                ledger['events'].append({'file':name,'attempt':attempt+1,'error':str(exc),'time':time.time()})
                atomic_json(ledger_path,ledger)
                if attempt+1==retries:raise
                time.sleep(min(2**attempt,4))
        receipt={**spec,'sha256':sha,'status':'DOWNLOADED_VERIFIED','local_path':str(path)}
        ledger['artifacts'][name]=receipt
        atomic_json(ledger_path,ledger)
        return receipt
