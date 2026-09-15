"""Lazy command dispatch; imports and help never load weights or contact services."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path
from . import __version__


def main():
    if len(sys.argv)>1 and sys.argv[1] in ('predict','batch','model-info','api'):
        from .legacy_cli import main as legacy
        return legacy()
    p=argparse.ArgumentParser(description='BluEcho physics-aware inspection; legacy predict/batch/model-info/api retained')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor');sub.add_parser('capabilities')
    serve=sub.add_parser('serve',help='Start the local inspection dashboard');serve.add_argument('--registry',type=Path,required=True);serve.add_argument('--storage',type=Path,required=True);serve.add_argument('--port',type=int,default=8010);serve.add_argument('--examples',type=Path)
    v=sub.add_parser('pipeline-review');v.add_argument('source',type=Path);v.add_argument('--manifest',type=Path,required=True);v.add_argument('--mode',choices=['baseline','high_recall','generic','acoustic'],default='baseline');v.add_argument('--verifier',type=Path);v.add_argument('--range-axis',choices=['x']);v.add_argument('--threshold',type=float);v.add_argument('--backend',choices=['native','onnx'],default='native');v.add_argument('--output',type=Path,required=True)
    m=sub.add_parser('models');m.add_argument('action',choices=['fetch','verify','import']);m.add_argument('--model',required=True);m.add_argument('--registry',type=Path,required=True);m.add_argument('--local',type=Path)
    i=sub.add_parser('inspect');i.add_argument('source',type=Path);i.add_argument('--output',required=True,type=Path);i.add_argument('--registry',required=True,type=Path);i.add_argument('--model',required=True,action='append');i.add_argument('--modality');i.add_argument('--channel',type=int);i.add_argument('--sidecar',type=Path);i.add_argument('--max-pings',type=int,default=128);i.add_argument('--nav-crs');i.add_argument('--backend',default='native',choices=['native','onnx'])
    box=sub.add_parser('boxes',help='Automatic boxes and portable evidence, no verifier filtering');box.add_argument('source',type=Path);box.add_argument('--output',required=True,type=Path);box.add_argument('--registry',required=True,type=Path);box.add_argument('--model',required=True,action='append');box.add_argument('--modality');box.add_argument('--channel',type=int);box.add_argument('--start-ping',type=int,default=0);box.add_argument('--max-pings',type=int,default=128,help='0 processes all remaining pings on selected channel');box.add_argument('--chunk-pings',type=int,default=128);box.add_argument('--sidecar',type=Path);box.add_argument('--nav-crs');box.add_argument('--backend',choices=['native','onnx'],default='native')
    g=sub.add_parser('geotag');g.add_argument('result',type=Path);g.add_argument('--source',type=Path,required=True);g.add_argument('--sidecar',type=Path,required=True);g.add_argument('--output',type=Path,required=True)
    sc=sub.add_parser('validate-sidecar');sc.add_argument('sidecar',type=Path);sc.add_argument('--source',type=Path,required=True);sc.add_argument('--width',type=int,required=True);sc.add_argument('--height',type=int,required=True)
    a=sub.add_parser('assess');a.add_argument('result',type=Path);a.add_argument('--output',type=Path,required=True);a.add_argument('--metadata',type=Path)
    b=sub.add_parser('bottom');b.add_argument('raw',type=Path);b.add_argument('--metadata',type=Path,required=True);b.add_argument('--output',type=Path,required=True);b.add_argument('--config',type=Path);b.add_argument('--manual',type=Path)
    r=sub.add_parser('review');r.add_argument('action',choices=['seed','export','import','development']);r.add_argument('--database',type=Path,required=True);r.add_argument('--input',type=Path);r.add_argument('--output',type=Path,required=True);r.add_argument('--source-group')
    args=p.parse_args()
    try:
        if args.command=='serve':
            from .dashboard.service import launch
            launch(args.registry,args.storage,args.port,args.examples);return 0
        elif args.command=='doctor':result={'version':__version__,'python':sys.version,'optional_modules':{n:importlib.util.find_spec(n) is not None for n in ('torch','ultralytics','onnxruntime','pyproj','pyxtf','psutil','jsonschema')},'default_device':'cpu','weights_downloaded':False}
        elif args.command in ('capabilities','models'):
            from .models import capabilities,acquire
            result=capabilities() if args.command=='capabilities' else acquire(args.model,args.registry,action=args.action,local=args.local)
        else:
            from .phase1.download import atomic_json
            if args.command=='geotag':
                from .geotag import geotag_saved
                result=geotag_saved(args.result,args.source,args.sidecar,args.output)
            elif args.command=='validate-sidecar':
                from .phase1.geography import load_sidecar
                result=load_sidecar(args.sidecar,args.source,args.width,args.height)
            elif args.command=='pipeline-review':
                from .verifier import inspect_pipeline
                from importlib.resources import files
                from contextlib import redirect_stdout,redirect_stderr
                from .phase1.cli import JsonDiagnostics
                errors=sys.stderr
                with redirect_stdout(JsonDiagnostics(errors)),redirect_stderr(JsonDiagnostics(errors)):
                    result=inspect_pipeline(args.source,args.manifest,mode=args.mode,verifier=args.verifier or files('bluecho').joinpath('experiment/verifier.json'),range_axis=args.range_axis,threshold=args.threshold,backend=args.backend)
                atomic_json(args.output,result)
            elif args.command=='boxes':
                from .phase1.engine import RecordingEngine
                from contextlib import redirect_stdout,redirect_stderr
                from .phase1.cli import JsonDiagnostics
                errors=sys.stderr
                with redirect_stdout(JsonDiagnostics(errors)),redirect_stderr(JsonDiagnostics(errors)):
                    result=RecordingEngine(args.registry).predict(args.source,args.output,model_ids=args.model,modality=args.modality,sidecar=args.sidecar,channel=args.channel,start_ping=args.start_ping,max_pings=args.max_pings,chunk_pings=args.chunk_pings,nav_crs=args.nav_crs,backend=args.backend,progress=lambda e:print(json.dumps(e),file=errors))
            elif args.command=='inspect':
                from .phase1.engine import RecordingEngine
                from .inspection import InspectionSupervisor
                from contextlib import redirect_stdout,redirect_stderr
                from .phase1.cli import JsonDiagnostics
                error_stream=sys.stderr
                with redirect_stdout(JsonDiagnostics(error_stream)),redirect_stderr(JsonDiagnostics(error_stream)):
                    result=InspectionSupervisor(RecordingEngine(args.registry,device='cpu')).inspect(args.source,args.output,model_ids=args.model,modality=args.modality,channel=args.channel,sidecar=args.sidecar,max_pings=args.max_pings,nav_crs=args.nav_crs,backend=args.backend,progress=lambda e:print(json.dumps(e),file=error_stream))
            elif args.command=='assess':
                from .inspection import InspectionSupervisor
                result=InspectionSupervisor().assess(json.loads(args.result.read_text()),metadata=json.loads(args.metadata.read_text()) if args.metadata else None);atomic_json(args.output,result)
            elif args.command=='bottom':
                import numpy as np
                from .inspection.bottom import track_bottom,BottomConfig,render_trace
                metadata=json.loads(args.metadata.read_text())
                if not metadata.get('modality','').startswith('SSS'):raise ValueError('Bottom tracking supports raw SSS only')
                config=BottomConfig(**json.loads(args.config.read_text())) if args.config else BottomConfig()
                with np.load(args.raw,allow_pickle=False) as data:raw=data['samples'] if 'samples' in data else data[data.files[0]]
                result=track_bottom(raw,metadata['pings'],source_sha256=metadata['source_sha256'],config=config,manual=json.loads(args.manual.read_text()) if args.manual else None);atomic_json(args.output,result);render_trace(raw,result,args.output.with_suffix('.png'))
            else:
                from .inspection import ReviewQueue
                q=ReviewQueue(args.database)
                try:
                    if args.action=='seed':
                        report=json.loads(args.input.read_text())
                        if not args.source_group:raise ValueError('--source-group is required for seed')
                        for c in report['candidates']+report['clear_region_tasks']:q.add(c,args.source_group)
                    elif args.action=='import':q.import_bundle(json.loads(args.input.read_text()))
                    result=q.development_manifest(json.loads(args.input.read_text())) if args.action=='development' else q.export();atomic_json(args.output,result)
                finally:q.close()
        print(json.dumps(result,allow_nan=False));return 0
    except ModuleNotFoundError as exc:
        print(json.dumps({'error':'MISSING_OPTIONAL_DEPENDENCY','detail':str(exc),'action':'Install bluecho-sonar[inspection,inference,onnx] as needed; see CPU installation instructions'}),file=sys.stderr);return 2
    except KeyboardInterrupt:
        print(json.dumps({'error':'CANCELLED','completed_outputs_retained':True}),file=sys.stderr);return 130
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'error':type(exc).__name__,'detail':str(exc)}),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
