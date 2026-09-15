"""Build full-resolution presentation copies and exact-byte model routing hints.

No predictions are stored in the routing hints. Every upload still runs inference.
"""
import hashlib
import json
import shutil
from pathlib import Path
import argparse
from PIL import Image

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-pack',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    public=root/'frontend/public/real-demo'
    catalog=json.loads((public/'catalog.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True,exist_ok=False)
    hints=[]; records=[]
    for sample in catalog:
        for name in ['original.png','preview.jpg']:
            hints.append(dict(sha256=sample['files'][name],model=sample['model'],modality=sample['modality'],name=sample['name'],thumbnail=name=='preview.jpg'))
        if sample['id'] in ['seabed','noaa0','noaa1']:
            continue
        folder=args.output/('FLS_Debris' if sample['modality']=='FLS_ARIS' else 'SSS_Pipeline')
        folder.mkdir(exist_ok=True)
        original=public/sample['id']/'original.png'
        for extension in ['png','jpg']:
            target=folder/(sample['id']+'.'+extension)
            if extension=='png':shutil.copy2(original,target)
            else:
                with Image.open(original) as image:image.convert('RGB').save(target,quality=96,subsampling=0)
            with Image.open(target) as image:width,height=image.size
            record=dict(file=target.relative_to(args.output).as_posix(),sha256=sha(target),model=sample['model'],modality=sample['modality'],name=sample['name'],width=width,height=height)
            records.append(record);hints.append({k:record[k] for k in ['sha256','model','modality','name']})
    private=args.existing_pack/'Private_Crab_Pot/crab-pot-real.jpg'
    if private.exists():
        folder=args.output/'Private_Crab_Pot';folder.mkdir()
        shutil.copytree(private.parent,folder,dirs_exist_ok=True)
        with Image.open(private) as image:width,height=image.size
        record=dict(file='Private_Crab_Pot/crab-pot-real.jpg',sha256=sha(private),model='ghost-pot',modality='SSS',name='Private crab-pot sample',width=width,height=height)
        records.append(record);hints.append({k:record[k] for k in ['sha256','model','modality','name']})
    # Keep the legacy filenames usable, but replace preview-sized derivatives.
    for sid in ['pipeline','seabed','propeller','bottle']:
        with Image.open(public/sid/'original.png') as image:
            target=args.existing_pack/'JPEG_Format_Examples'/(sid+'.jpg')
            image.convert('RGB').save(target,quality=96,subsampling=0)
        sample=next(s for s in catalog if s['id']==sid)
        hints.append(dict(sha256=sha(target),model=sample['model'],modality=sample['modality'],name=sample['name']))
    unique={r['sha256']:r for r in hints}
    (public.parent/'upload-samples.json').write_text(json.dumps(list(unique.values()),indent=2),encoding='utf-8')
    (args.output/'manifest.json').write_text(json.dumps({'images':records,'validation':'Pending live browser inference. No boxes or scores are injected by sample recognition.'},indent=2),encoding='utf-8')
    shutil.copy2(args.existing_pack/'DATA_ATTRIBUTION.md',args.output/'DATA_ATTRIBUTION.md')
    (args.output/'START_HERE.md').write_text('''# BluEcho live presentation images

Upload these full-resolution PNG/JPG files individually. BluEcho recognizes their exact SHA-256 and selects the matching sensor/model. Click Start inspection to run fresh inference; no saved boxes are substituted. Keep the tab open for the initial model download.

PNG/JPG pairs show the same source, not independent scenes. Private_Crab_Pot stays local because source licence statements conflict. No ghost-net detector is supplied. Source coordinates are unavailable for these files.

The intentionally empty seabed example remains in the older pack as a negative-control example. It is excluded here because this folder is for presenting visible detector outputs. Selection does not establish independent model accuracy. See LIVE_RESULTS.json for measured output from the current browser runtime.

Made for SIH 2026 by Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, Aditya Banerjee, and Aditya SS Varma.
''',encoding='utf-8')
    print(json.dumps({'folder':str(args.output),'files':len(records),'routing_hashes':len(unique)}))

if __name__=='__main__':main()
