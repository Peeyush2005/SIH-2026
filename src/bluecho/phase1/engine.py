"""One source engine for image/recording → candidates → geography → report."""
import copy
import hashlib
import json
from pathlib import Path
import time
import psutil
from PIL import Image
from bluecho.engine import Engine as LegacyEngine,InputError
from .adapters import Registry
from .download import atomic_json,digest
from .inputs import decoded_input,xtf_windows
from .geography import geotag_box,tracks
from .quality import assess_quality
from .reporting import export_result
from .contracts import image_digest

SCHEMA_VERSION='2.0.0'


def progress_event(callback,stage,**kw):
    if callback:callback({'event':'progress','stage':stage,**kw})


class RecordingEngine:
    def __init__(self,registry,*,device='cpu',cache_models=1):
        self.registry=Registry(registry,cache_models=cache_models);self.device=device

    def process_window(self,window,model_ids,out,*,backend='native',progress=None):
        out=Path(out);out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
        cuda=None
        if self.device!='cpu':
            import torch
            cuda=torch.cuda
            if cuda.is_available():cuda.reset_peak_memory_stats()
        rgb=Image.open(window['image_path']).convert('RGB');metadata=window['metadata']
        qstart=time.perf_counter();quality,qview=assess_quality(rgb,invalid_rows=window['invalid_rows'],metadata=metadata,coverage=window['coverage']);qview.save(out/'quality.png');quality_seconds=time.perf_counter()-qstart
        detections=[];proposals=[];model_info=[];timings={'quality_seconds':quality_seconds,'models':[]};geoseconds=0.
        for model_id in model_ids:
            progress_event(progress,'model_loading',model_id=model_id)
            t=time.perf_counter();entry,model=self.registry.load(model_id,window['modality'],device=self.device,backend=backend);startup=time.perf_counter()-t
            def callback(current,total):progress_event(progress,'predicting',model_id=model_id,current=current,total=total)
            t=time.perf_counter()
            if isinstance(model,LegacyEngine):
                pred=model.predict(window['image_path'],modality=window['modality'],progress=callback)
                boxes=[{'xyxy':d['box_xyxy_pixels'],'score':d['model_score'],'class_id':d['class_id'],'class_name':d['class_name']} for d in pred['detections']]
                atomic_json(out/(model_id+'-inference-provenance.json'),pred.get('inference_provenance',{}))
                processed=None
            else:boxes,processed=model.predict(window['image_path'],progress=callback)
            elapsed=time.perf_counter()-t
            if processed is not None:processed.save(out/(model_id+'-processed.png'))
            timing={'model_id':model_id,'startup_seconds':startup,'prediction_seconds':elapsed,'device':self.device,'backend':backend if isinstance(model,LegacyEngine) else entry['runtime']};timings['models'].append(timing)
            model_info.append({'id':model_id,'version':entry['version'],'sha256':entry['weights']['sha256'],'classes':entry['classes'],'evidence_scope':entry['evidence_scope'],'calibration':entry['calibration']})
            for box in boxes:
                a,b,c,d=box['xyxy'];identity=[window['source_sha256'],window['reference'],entry['weights']['sha256'],box]
                cid=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
                t=time.perf_counter();geo=geotag_box(box['xyxy'],metadata);geoseconds+=time.perf_counter()-t
                flags=[q['flag'] for q in quality['regions'] if min(c,q['box_xyxy_pixels'][2])>max(a,q['box_xyxy_pixels'][0]) and min(d,q['box_xyxy_pixels'][3])>max(b,q['box_xyxy_pixels'][1])]
                if geo['coordinates'] is None:flags.append('geographical_position_unavailable')
                if window['decoding'].get('transfer_evidence'):flags.append('sensor_model_transfer_unvalidated')
                if a<=0 or b<=0 or c>=rgb.width or d>=rgb.height:flags.append('boundary_truncated')
                source_class=box['class_id'];unvalidated=source_class in entry.get('unsupported_as_required_classes',[]) or (model_id=='sss-wreck-experimental' and source_class==0)
                status=entry.get('class_evidence',{}).get(str(source_class),entry['evidence_scope'])
                candidate={'candidate_id':cid,'candidate_type':'unvalidated_proposal' if unvalidated else 'model_detection','source_reference':window['reference'],'source_sha256':window['source_sha256'],'modality':window['modality'],'class_id':source_class,'class_name':box['class_name'],'original_class':box['class_name'],'material_identity':None,'model_id':model_id,'model_version':entry['version'],'model_sha256':entry['weights']['sha256'],'model_score':box['score']*100.,'raw_score':box['score'],'score_type':'uncalibrated_model_score_0_100','box_xyxy_pixels':box['xyxy'],'mask':box.get('mask'),'pixel_dimensions':{'width':c-a,'height':d-b},**geo,'position_accuracy':'unvalidated_against_independent_reference','quality_flags':sorted(set(flags)),'review_state':'unreviewed','evidence_status':status,'provenance':{'preprocessing':entry['preprocessing'],'decoding':window['decoding'],'terms':entry['terms']}}
                candidate.update(source_filename=window['reference']['file'],image_dimensions={'width':rgb.width,'height':rgb.height},native_class_name=box['class_name'],mapped_class_name=None,score_calibrated=False,evidence={'crop':f'crops/{cid}.png','context':f'contexts/{cid}.png','original':'original.png','overlay':'annotated.png'},window_mapping=window['reference'])
                (proposals if unvalidated else detections).append(candidate)
        result={'schema_version':SCHEMA_VERSION,'source_reference':window['reference'],'source_sha256':window['source_sha256'],'image_pixel_sha256':image_digest(rgb),'image_dimensions':{'width':rgb.width,'height':rgb.height},'modality':window['modality'],'models':model_info,'detections':detections,'unvalidated_proposals':proposals,'quality':quality,'tracks':tracks(metadata),'decoding':window['decoding'],'evidence_scopes':[m['evidence_scope'] for m in model_info],'review_records':[],'timings':timings,'memory':{'process_rss_bytes':psutil.Process().memory_info().rss},'geographical_accuracy':'not evaluated against independent references','cross_model_policy':'No score averaging or cross-model duplicate suppression; each original model class and identity is retained'}
        timings['geotagging_seconds']=geoseconds
        result['positioning_metadata']=metadata
        result['positioning_scope']=metadata.get('positioning_scope','Supplied navigation or transform; accuracy unvalidated') if metadata else 'No geographic metadata'
        if cuda and cuda.is_available():
            result['memory']['cuda_peak_allocated_bytes']=cuda.max_memory_allocated()
            result['memory']['cuda_peak_reserved_bytes']=cuda.max_memory_reserved()
        progress_event(progress,'exporting',detections=len(detections),proposals=len(proposals))
        t=time.perf_counter();paths=export_result(result,out,rgb);timings['export_seconds']=time.perf_counter()-t;timings['window_total_seconds']=time.perf_counter()-started
        atomic_json(out/'results.json',result)
        if metadata:atomic_json(out/'positioning_metadata.json',metadata)
        progress_event(progress,'window_complete',output=str(out),detections=len(detections))
        return result

    def predict(self,source,out,*,model_ids,modality=None,sidecar=None,channel=None,start_ping=0,max_pings=128,chunk_pings=128,nav_crs=None,backend='native',progress=None):
        if not model_ids or len(set(model_ids))!=len(model_ids):raise InputError('Select one or more distinct model IDs')
        source=Path(source).resolve();out=Path(out).resolve()
        if source.is_relative_to(out):raise InputError('Output directory must not contain the input path')
        if out.exists() and any(out.iterdir()):raise InputError('Output is not empty; choose a fresh output directory')
        out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
        progress_event(progress,'decoding',source=source.name)
        if source.suffix.lower()=='.xtf':
            if modality not in (None,'SSS'):raise InputError('XTF adapter declares SSS; sensor/frequency transfer remains unvalidated')
            if sidecar:raise InputError('Raw XTF has explicit packet metadata; sidecar override requires a separately decoded image with verified binding')
            results=[]
            windows=xtf_windows(source,out/'decoded',channel=channel,start_ping=start_ping,max_pings=max_pings,chunk_pings=chunk_pings,nav_crs=nav_crs,progress=lambda a,b:progress_event(progress,'decoding',current=a,total=b))
            try:
                for k,window in enumerate(windows):
                    result=self.process_window(window,model_ids,out/f'window_{k:04d}',backend=backend,progress=progress)
                    results.append({'window':k,'report':f'window_{k:04d}/report.html','results':f'window_{k:04d}/results.json','detections':len(result['detections']),'reference':window['reference']})
            except (KeyboardInterrupt,Exception) as exc:
                windows.close()
                atomic_json(out/'recording.json',{'schema_version':SCHEMA_VERSION,'status':'CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'ERROR','source':source.name,'windows':results,'completed_windows':len(results),'unprocessed':'Remaining requested pings and other channels; decoded coverage is separate from successful inference','error':str(exc)})
                raise
            result={'schema_version':SCHEMA_VERSION,'source':source.name,'source_sha256':digest(source),'windows':results,'coverage':json.loads((out/'decoded/recording_coverage.json').read_text()),'total_seconds':time.perf_counter()-start}
            atomic_json(out/'recording.json',result)
            import html
            links=''.join(f'<li><a href="{r["report"]}">Window {r["window"]}: {r["detections"]} detections</a></li>' for r in results)
            (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>BluEcho recording</title><h1>'+html.escape(source.name)+'</h1><p>Selected channel and ping windows only. Unselected coverage remains unassessed. Sensor/model transfer and real positioning accuracy are unvalidated.</p><ul>'+links+'</ul><a href="recording.json">Recording coverage and source references</a>')
        else:
            window=decoded_input(source,out/'decoded',modality,sidecar=sidecar);decode_elapsed=time.perf_counter()-start
            result=self.process_window(window,model_ids,out,backend=backend,progress=progress);result['timings']['decode_seconds']=decode_elapsed;result['timings']['total_seconds']=time.perf_counter()-start;atomic_json(out/'results.json',result)
        progress_event(progress,'complete',output=str(out));return result

    def batch(self,inputs,out,**kwargs):
        out=Path(out);rows=[]
        for i,p in enumerate(inputs):
            p=Path(p);target=out/f'{i:04d}_{p.stem}'
            try:
                result=self.predict(p,target,**kwargs);rows.append({'input':str(p),'status':'PASS','output':str(target)})
            except (InputError,ValueError,OSError) as exc:rows.append({'input':str(p),'status':'ERROR','error':str(exc)})
        atomic_json(out/'batch.json',rows);return rows
