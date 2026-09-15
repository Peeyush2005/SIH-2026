"""Free CPU hosted demo; no private datasets or credentials in the image."""
import json,os
from pathlib import Path
from huggingface_hub import snapshot_download
from bluecho.dashboard.service import create_app
from bluecho.phase1.download import digest

model_root=Path('/tmp/bluecho-models');model_root.mkdir(exist_ok=True)
snapshot_download('SharonMelhi/BluEcho-SSS-Pipeline',revision='36055030359ec3c750c4446889c67fe10c5e7271',local_dir=model_root/'sss-v3',allow_patterns=['native.pt','manifest.json','classes.json','preprocessing.json','evaluation.json'])
manifest=json.loads((model_root/'sss-v3'/'manifest.json').read_text())
assert digest(model_root/'sss-v3'/'native.pt')==manifest['native']['sha256']
entry={'id':'sss-pipeline-v3','status':'evaluated-on-stated-data','version':manifest['model_version'],'modalities':['SSS_LF'],'runtime':'bluecho_v3','architecture':'YOLO11n','manifest':'sss-v3/manifest.json','weights':{'path':'sss-v3/native.pt','sha256':manifest['native']['sha256']},'classes':manifest['classes'],'threshold':manifest['thresholds']['0'],'preprocessing':manifest['preprocessing'],'evidence_scope':'Pipeline only. Correlated single-survey development validation; no independent-site benchmark.','calibration':'uncalibrated','terms':{'weights':'AGPL-3.0','data':'SubPipe CC BY 4.0; OceanScan-MST / REMARO'}}
(model_root/'sss-pipeline-v3.model.json').write_text(json.dumps(entry))
origins=[x.strip() for x in os.environ.get('BLUECHO_ALLOWED_ORIGINS','').split(',') if x.strip()]
space_host=os.environ.get('SPACE_HOST','sharonmelhi-bluecho-sonar.hf.space')
origins.append('https://'+space_host)
from urllib.parse import urlparse
hosts=[space_host,*[urlparse(x).hostname for x in origins]]
app=create_app('/tmp/bluecho-sessions',model_root,queue_limit=4,memory_mib=8192,hosted=True,allowed_hosts=hosts,allowed_origins=origins)
