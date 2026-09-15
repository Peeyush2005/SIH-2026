"""Reproducible source-test sample check; not an independent survey benchmark.

Download requires the user's approved Hugging Face access via HF_TOKEN. No data
or token is published. The model, threshold and preprocessing are frozen first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time
from urllib.request import Request, urlopen

REV = 'b6a36ec00c9bb0070f30be4c1dd6cbe139423cd4'
BASE = f'https://huggingface.co/datasets/PINGEcosystem/sss-crab-pot-detection-ds/resolve/{REV}/'


def download(root, count):
    def get(name):
        request = Request(BASE + name, headers={'Authorization': 'Bearer ' + os.environ['HF_TOKEN']})
        with urlopen(request, timeout=60) as response:
            return response.read()
    root.mkdir(parents=True, exist_ok=True)
    metadata = get('test/metadata.jsonl')
    (root / 'metadata.jsonl').write_bytes(metadata)
    (root / 'source-README.md').write_bytes(get('README.md'))
    rows = [json.loads(line) for line in metadata.decode().splitlines() if line.strip()]
    eligible = [r for r in rows if set(r['objects']['category']) <= {'Crab-Pot'}]
    selected = random.Random(42).sample(sorted(eligible, key=lambda r:r['file_name']), min(count, len(eligible)))
    manifest = {'revision': REV, 'seed': 42, 'source_split': 'test', 'selection': 'Uniform sample of sorted records; ambiguous labels excluded before sampling', 'total_records': len(rows), 'eligible_records': len(eligible), 'threshold': .25, 'iou': .5, 'records': selected}
    # Persist selection before downloading images or making any prediction.
    (root / 'selection.json').write_text(json.dumps(manifest, indent=2))
    for r in selected:
        name = r['file_name']
        if Path(name).name != name:
            raise ValueError('Unexpected source path')
        target = root / name
        if not target.exists():
            target.write_bytes(get('test/' + name))
    print(f'Downloaded fixed sample: {len(selected)} / {len(rows)} records', flush=True)


def evaluate(root, registry):
    import numpy as np
    from PIL import Image, ImageDraw
    from bluecho.phase1.adapters import Registry
    manifest = json.loads((root / 'selection.json').read_text())
    entry, model = Registry(registry).load('ghost-pot', 'SSS')
    def iou(a,b):
        inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        return inter/max(1e-12,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)
    outputs=[]
    for row in manifest['records']:
        path=root/row['file_name']; im=Image.open(path).convert('RGB'); ground=[]
        for (x,y,w,h),category,area in zip(row['objects']['bbox'],row['objects']['category'],row['objects']['area'],strict=True):
            assert category=='Crab-Pot' and np.isfinite([x,y,w,h]).all()
            assert w>0 and h>0 and x>=0 and y>=0 and x+w<=im.width+1 and y+h<=im.height+1
            assert abs(w*h-area)<1.01
            ground.append([x,y,x+w,y+h])
        start=time.perf_counter(); boxes,_=model.predict(path,threshold=.001); elapsed=time.perf_counter()-start
        outputs.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':im.size,'ground_truth':ground,'predictions':boxes,'seconds':elapsed,'group':re.split(r'_wcp|_Sensor',path.name)[0]})
    def match(cutoff, confidence):
        used=[set() for _ in outputs]; decisions=[]
        flat=sorted([(b['score'],i,b['xyxy']) for i,r in enumerate(outputs) for b in r['predictions'] if b['score']>=confidence],reverse=True)
        for score,i,box in flat:
            options=[(iou(box,g),j) for j,g in enumerate(outputs[i]['ground_truth']) if j not in used[i]]
            best=max(options,default=(0,-1)); hit=best[0]>=cutoff
            if hit: used[i].add(best[1])
            decisions.append((score,int(hit),i))
        return decisions
    labels=sum(len(r['ground_truth']) for r in outputs)
    operational=match(.5,.25); tp=sum(d[1] for d in operational); fp=len(operational)-tp
    aps=[]
    for cutoff in np.arange(.5,.96,.05):
        decisions=match(float(cutoff),.001); hits=np.array([d[1] for d in decisions]); cumulative=np.cumsum(hits)
        recall=cumulative/max(1,labels); precision=cumulative/np.arange(1,len(hits)+1)
        aps.append(float(np.mean([max(precision[recall>=r],default=0) for r in np.linspace(0,1,101)])) if labels else None)
    result={'scope':'Fixed source-test sample. Training overlap and recording independence unaudited; not a new-survey benchmark.', 'model_sha256':entry['weights']['sha256'],'selection_sha256':hashlib.sha256((root/'selection.json').read_bytes()).hexdigest(),'image_count':len(outputs),'label_count':labels,'filename_groups':sorted(set(r['group'] for r in outputs)),'threshold':.25,'iou':.5,'true_positives':tp,'false_positives':fp,'false_negatives':labels-tp,'precision':tp/len(operational) if operational else None,'recall':tp/labels if labels else None,'AP50':aps[0],'mAP50_95':float(np.mean(aps)) if labels else None,'AP_method':'101-point interpolated precision, scores >= .001, class-correct one-to-one matching, IoUs .50:.05:.95','false_positives_per_original_image':fp/len(outputs),'latency_seconds_median_excluding_first':float(np.median([r['seconds'] for r in outputs[1:]])),'records':outputs}
    (root/'metrics.json').write_text(json.dumps(result,indent=2))
    for i,r in enumerate(outputs[:6]):
        im=Image.open(root/r['file']).convert('RGB'); draw=ImageDraw.Draw(im)
        for box in r['ground_truth']:draw.rectangle(box,outline='lime',width=2)
        for b in r['predictions']:
            if b['score']>=.25:draw.rectangle(b['xyxy'],outline='red',width=2)
        draw.text((5,5),'Fixed sample: green label / red prediction',fill='white',stroke_width=1,stroke_fill='black')
        im.save(root/f'overlay-fixed-{i}.png')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['download','evaluate']);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--count',type=int,default=32);parser.add_argument('--registry',type=Path)
    args=parser.parse_args()
    if args.action=='download':download(args.output,args.count)
    else:evaluate(args.output,args.registry)
