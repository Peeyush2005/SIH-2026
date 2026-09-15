"""Register verified original-file hashes from an existing BluEcho upload pack."""
import argparse
import hashlib
import json
from pathlib import Path

def register(pack, hints):
    manifest=json.loads((pack/'source_manifest.json').read_text(encoding='utf-8'))
    known={r['sha256']:r for r in hints}
    for row in manifest['images']:
        source=(pack/row['file']).resolve()
        if not source.is_relative_to(pack.resolve()):
            raise ValueError('Manifest path is outside the image folder')
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if digest!=row['sha256']:
            raise ValueError('Image differs from verified manifest: '+row['file'])
        if (row['model'],row['modality']) not in [('fls11-debris','FLS_ARIS'),('sss-pipeline-v3','SSS_LF')]:
            raise ValueError('Unexpected source model/modality')
        known.setdefault(digest,dict(sha256=digest,model=row['model'],modality=row['modality'],name=source.stem.replace('_',' ')))
    return list(known.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path,required=True)
    args=parser.parse_args()
    path=Path(__file__).resolve().parents[1]/'frontend/public/upload-samples.json'
    old=json.loads(path.read_text(encoding='utf-8'))
    new=register(args.pack,old)
    path.write_text(json.dumps(new,indent=2),encoding='utf-8')
    print(f'Registered {len(new)-len(old)} additional original image hashes; {len(new)} total.')

if __name__=='__main__':main()
