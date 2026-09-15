"""Source CLI: one JSON value on stdout; structured diagnostics on stderr."""
import argparse
import contextlib
import json
from pathlib import Path
import sys
from bluecho.engine import InputError,ModelError,read_image
from .adapters import Registry
from .contracts import validate_result
from .download import download,atomic_json,digest
from .engine import RecordingEngine
from .inputs import inspect_input
from .geography import load_sidecar,geotag_box,tracks
from .quality import assess_quality
from .reporting import export_result
from .supervisor import snapshot


class JsonDiagnostics:
    def __init__(self,stream):self.stream=stream;self.buffer=''
    def write(self,text):
        self.buffer+=text.replace('\r','\n')
        while '\n' in self.buffer:
            line,self.buffer=self.buffer.split('\n',1)
            if line.strip():print(json.dumps({'event':'log','message':line}),file=self.stream,flush=True)
        return len(text)
    def flush(self):
        if self.buffer.strip():print(json.dumps({'event':'log','message':self.buffer}),file=self.stream,flush=True)
        self.buffer='';self.stream.flush()
    def isatty(self):return False


def fresh_output(path,inputs=()):
    out=Path(path).resolve()
    if any(Path(p).resolve().is_relative_to(out) for p in inputs):raise InputError('Output must not contain an input or results file')
    if out.exists() and any(out.iterdir()):raise InputError('Choose a fresh empty output directory')
    out.mkdir(parents=True,exist_ok=True);return out


def execute(a,stderr):
    if a.command=='inspect-input':return inspect_input(a.input)
    if a.command=='list-models':return Registry(a.registry).entries()
    if a.command=='download-model':return download(json.loads(Path(a.manifest).read_text()),a.output)
    if a.command in ('predict','batch-predict'):
        engine=RecordingEngine(a.registry,device=a.device)
        callback=(lambda e:print(json.dumps(e),file=stderr,flush=True)) if a.progress_jsonl else None
        opts=dict(model_ids=a.model,modality=a.modality,sidecar=a.sidecar,channel=a.channel,start_ping=a.start_ping,max_pings=a.max_pings,chunk_pings=a.chunk_pings,nav_crs=a.nav_crs,backend=a.backend,progress=callback)
        if a.command=='predict':return engine.predict(a.input,a.output,**opts)
        folder=Path(a.input)
        if not folder.is_dir():raise InputError('Batch input must be a directory')
        paths=sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.png','.jpg','.jpeg','.bmp','.pbm','.tif','.tiff','.xtf'))
        if not paths:raise InputError('No supported files in batch directory')
        if a.sidecar:raise InputError('Batch sidecars require per-file binding; run predict for each located input')
        return engine.batch(paths,a.output,**opts)
    if a.command=='geotag':
        result=json.loads(Path(a.results).read_text());im=read_image(a.source);validate_result(result,im)
        if result['source_sha256']!=digest(a.source):raise InputError('Results are bound to a different source')
        meta=load_sidecar(a.sidecar,a.source,im.width,im.height)
        if meta['modality']!=result['modality']:raise InputError('Metadata modality mismatch')
        for d in result['detections']+result.get('unvalidated_proposals',[]):
            d.update(geotag_box(d['box_xyxy_pixels'],meta))
            d['quality_flags']=[f for f in d['quality_flags'] if f!='geographical_position_unavailable']
            if d['coordinates'] is None:d['quality_flags'].append('geographical_position_unavailable')
        result['tracks']=tracks(meta);result['geotagging_provenance']={'sidecar':Path(a.sidecar).name,'sidecar_sha256':digest(a.sidecar),'original_results_sha256':digest(a.results)}
        result['positioning_scope']=meta.get('positioning_scope','Supplied navigation or transform; accuracy unvalidated')
        out=fresh_output(a.output,[a.results,a.source,a.sidecar]);quality,qview=assess_quality(im,metadata=meta,coverage=result['quality']['coverage']);qview.save(out/'quality.png');result['quality']=quality
        atomic_json(out/'positioning_metadata.json',meta);export_result(result,out,im);return result
    if a.command=='assess-quality':
        im=read_image(a.input);invalid=[int(x) for x in a.invalid_rows.split(',') if x];result,view=assess_quality(im,invalid_rows=invalid);out=fresh_output(a.output,[a.input]);view.save(out/'quality.png');atomic_json(out/'quality.json',result);return result
    if a.command=='export':
        result=json.loads(Path(a.results).read_text());im=read_image(a.image);validate_result(result,im);out=fresh_output(a.output,[a.results,a.image])
        from PIL import ImageDraw
        qview=im.copy();draw=ImageDraw.Draw(qview)
        for region in result['quality']['regions']:draw.rectangle(region['box_xyxy_pixels'],outline='orange',width=2)
        qview.save(out/'quality.png');return export_result(result,out,im)
    return snapshot(a.queue)


def main():
    p=argparse.ArgumentParser(prog='python -m bluecho.phase1.cli');sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('inspect-input');a.add_argument('--input',required=True)
    a=sub.add_parser('list-models');a.add_argument('--registry',required=True)
    a=sub.add_parser('download-model');a.add_argument('--manifest',required=True);a.add_argument('--output',required=True)
    for command in ['predict','batch-predict']:
        a=sub.add_parser(command);a.add_argument('--input',required=True);a.add_argument('--output',required=True);a.add_argument('--registry',required=True);a.add_argument('--model',action='append',required=True);a.add_argument('--modality');a.add_argument('--device',default='cpu');a.add_argument('--backend',default='native',choices=['native','onnx']);a.add_argument('--sidecar');a.add_argument('--channel',type=int);a.add_argument('--start-ping',type=int,default=0);a.add_argument('--max-pings',type=int,default=128);a.add_argument('--chunk-pings',type=int,default=128);a.add_argument('--nav-crs');a.add_argument('--progress-jsonl',action='store_true')
    a=sub.add_parser('geotag');a.add_argument('--results',required=True);a.add_argument('--source',required=True);a.add_argument('--sidecar',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('assess-quality');a.add_argument('--input',required=True);a.add_argument('--output',required=True);a.add_argument('--invalid-rows',default='')
    a=sub.add_parser('export');a.add_argument('--results',required=True);a.add_argument('--image',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('training-status');a.add_argument('--queue',required=True)
    a=p.parse_args();diagnostics=JsonDiagnostics(sys.stderr);stderr=sys.stderr
    try:
        with contextlib.redirect_stdout(diagnostics),contextlib.redirect_stderr(diagnostics):
            result=execute(a,stderr)
        diagnostics.flush();print(json.dumps(result,allow_nan=False))
    except (InputError,ModelError,ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:
        diagnostics.flush();print(json.dumps({'event':'error','type':type(exc).__name__,'message':str(exc)}),file=stderr);return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
