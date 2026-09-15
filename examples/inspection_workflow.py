"""Run with an installed wheel, explicit input/model/registry and fresh output."""
import argparse,json
from pathlib import Path
from bluecho import RecordingEngine,InspectionSupervisor
from bluecho.inspection import ReviewQueue
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--registry',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--modality',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
receipt=InspectionSupervisor(RecordingEngine(a.registry)).inspect(a.source,a.output,model_ids=[a.model],modality=a.modality)
report=json.loads(Path(receipt['inspection_reports'][0]).read_text());queue=ReviewQueue(a.output/'review.sqlite')
for item in report['candidates']+report['clear_region_tasks']:queue.add(item,report['source_sha256'])
(a.output/'review.json').write_text(json.dumps(queue.export(),indent=2));queue.close()
print(json.dumps({'reports':receipt['inspection_reports'],'candidate_count':len(report['candidates']),'human_review_events':0}))
