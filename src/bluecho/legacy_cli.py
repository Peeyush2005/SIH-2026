import argparse
import json
from pathlib import Path
import sys
from .engine import Engine, InputError, ModelError
from .export import export, write_csv


def main():
    parser = argparse.ArgumentParser(description='BluEcho offline SSS_LF inference and local API')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('predict', 'batch', 'model-info', 'api'):
        p = sub.add_parser(name); p.add_argument('--manifest', required=True); p.add_argument('--device', default='cpu')
        if name in ('predict', 'batch'):
            p.add_argument('--input', required=True); p.add_argument('--output', required=True)
            p.add_argument('--modality', required=True); p.add_argument('--backend', choices=['native','onnx'], default='native')
        if name == 'api':
            p.add_argument('--jobs', required=True); p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=8000)
    p = sub.add_parser('export'); p.add_argument('--json', required=True); p.add_argument('--csv', required=True)
    a = parser.parse_args()
    try:
        if a.command == 'api':
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(a.manifest, a.jobs, device=a.device),host=a.host,port=a.port,workers=1)
            return
        if a.command == 'export':
            write_csv(a.csv,json.loads(Path(a.json).read_text()));return
        engine = Engine(a.manifest,device=a.device,backend=getattr(a,'backend','native'))
        if a.command == 'model-info':
            print(json.dumps(engine.info(),indent=2));return
        def progress(done,total):print(f'{done}/{total}',file=sys.stderr,flush=True)
        if a.command == 'predict':
            export(engine.predict(a.input,modality=a.modality,progress=progress),a.output,source=a.input)
        else:
            base=Path(a.output);base.mkdir(parents=True,exist_ok=False)
            for index,(path,result) in enumerate(engine.batch(a.input,modality=a.modality,progress=progress)):
                export(result,base/f'{index:05d}_{path.stem}',source=path)
    except (InputError,ModelError,OSError,ValueError) as exc:
        parser.exit(2,f'BluEcho: {exc}\n')


if __name__ == '__main__':
    main()
