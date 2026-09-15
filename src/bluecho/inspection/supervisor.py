"""Physics-aware inspection supervisor. Ranking does not change detector output."""
import copy
import hashlib
import json
from pathlib import Path
from .geometry import position

class InspectionSupervisor:
    def __init__(self,engine=None,*,low_score=0.5,ranking='detector'):
        if not 0<=low_score<=1:raise ValueError('low_score must be 0..1')
        self.engine=engine;self.low_score=low_score
        if ranking not in ('detector','reasons'):raise ValueError('Unknown ranking policy')
        self.ranking=ranking
    def assess(self,result,*,metadata=None,bottom=None,source_group=None):
        from bluecho.phase1.contracts import validate_result
        validate_result(result)
        if metadata and (metadata.get('source_sha256')!=result['source_sha256'] or (metadata.get('image_width'),metadata.get('image_height'))!=(result['image_dimensions']['width'],result['image_dimensions']['height'])):
            raise ValueError('Inspection metadata source binding mismatch')
        if bottom and bottom['source_sha256']!=result['source_sha256']:raise ValueError('Bottom trace source mismatch')
        m=copy.deepcopy(metadata)
        if bottom and m:
            for row in bottom['rows']:
                if row['altitude_m'] is not None:
                    ping=next((p for p in m.get('pings',[]) if p['row']==row['row'] and p.get('ping_index')==row['ping_index'] and p.get('side')==row['side']),None)
                    if ping and ping.get('altitude') is None:
                        ping.update(altitude=row['altitude_m'],altitude_unit='m',altitude_reference='seabed',altitude_provenance=row['altitude_provenance'],altitude_status=row['status'])
        candidates=[]
        for original in result['detections']+result['unvalidated_proposals']:
            c=copy.deepcopy(original);a,b,d,e=c['box_xyxy_pixels'];reasons=[]
            if c['raw_score']<self.low_score:reasons.append('LOW_DETECTOR_SCORE')
            geo=position((a+d)/2,(b+e)/2,m)
            if geo['coordinates'] is None:reasons.append('INCOMPLETE_METADATA')
            if any('missing' in f or 'dropout' in f for f in c['quality_flags']):reasons.append('DROPOUT_OVERLAP')
            w,h=result['image_dimensions']['width'],result['image_dimensions']['height']
            if a<=1 or b<=1 or d>=w-1 or e>=h-1:reasons.append('WINDOW_BOUNDARY')
            if bottom and any(r['status']=='unreliable' for r in bottom['rows'] if b<=r['row']<e):reasons.append('AMBIGUOUS_BOTTOM')
            candidates.append({'candidate_id':c['candidate_id'],'source_sha256':c['source_sha256'],'source_group':source_group or c['source_sha256'],'image_dimensions':result['image_dimensions'],'original_prediction':c,'native_label':c['original_class'],'mapped_label':None,'detector_score':{'value':c['raw_score'],'calibrated':False},'quality':{'flags':c['quality_flags']},'geometry':geo,'positional_uncertainty':geo['uncertainty'],'reason_codes':sorted(set(reasons)),'review_priority':len(set(reasons)),'review_status':'unreviewed','review_history':[],'evidence':{'context':'annotated.png','crop':f"crops/{c['candidate_id']}.png",'source_reference':c['source_reference']}})
        # Only this exact window: correspondence is original pixels, never neighboring pings.
        associations=[]
        for i,left in enumerate(candidates):
            for right in candidates[i+1:]:
                a=left['original_prediction'];b=right['original_prediction']
                if a['modality']!=b['modality'] or a['source_reference']!=b['source_reference']:continue
                x,y,z,t=a['box_xyxy_pixels'];u,v,w,h=b['box_xyxy_pixels'];inter=max(0,min(z,w)-max(x,u))*max(0,min(t,h)-max(y,v));union=(z-x)*(t-y)+(w-u)*(h-v)-inter
                if union and inter/union>=0.7:
                    associations.append({'candidate_ids':[a['candidate_id'],b['candidate_id']],'basis':'same_source_window_original_pixel_iou','iou':inter/union,'independent_objects':False,'identity_confirmed':False})
                    if a['original_class']!=b['original_class']:
                        for c in (left,right):c['reason_codes']=sorted(set(c['reason_codes']+['CONTRADICTORY_LABELS']));c['review_priority']=len(c['reason_codes'])
        # Apparent clear regions are review tasks, never negative ground truth.
        negatives=[];width=result['image_dimensions']['width'];height=result['image_dimensions']['height']
        for yi in range(2):
            for xi in range(2):
                box=[xi*width/2,yi*height/2,(xi+1)*width/2,(yi+1)*height/2]
                if any(min(box[2],c['original_prediction']['box_xyxy_pixels'][2])>max(box[0],c['original_prediction']['box_xyxy_pixels'][0]) and min(box[3],c['original_prediction']['box_xyxy_pixels'][3])>max(box[1],c['original_prediction']['box_xyxy_pixels'][1]) for c in candidates):continue
                identifier=hashlib.sha256(json.dumps([result['source_sha256'],result['source_reference'],box],sort_keys=True).encode()).hexdigest()[:24]
                negatives.append({'candidate_id':identifier,'source_sha256':result['source_sha256'],'source_reference':result['source_reference'],'image_dimensions':result['image_dimensions'],'box_xyxy_pixels':box,'candidate_type':'apparently_clear_region','review_status':'unreviewed','label':None})
        report={'schema_version':'inspection-1.0','source_sha256':result['source_sha256'],'raw_result_sha256':hashlib.sha256(json.dumps(result,sort_keys=True,allow_nan=False).encode()).hexdigest(),'raw_result':copy.deepcopy(result),'candidates':candidates,'associations':associations,'clear_region_tasks':negatives,'ranking_policy':self.ranking+'; model/modality groups kept separate; no filtering','ranked_candidate_ids':[c['candidate_id'] for c in sorted(candidates,key=lambda c:(c['original_prediction']['modality'],c['original_prediction']['model_id'],-c['review_priority'] if self.ranking=='reasons' else -c['detector_score']['value'],c['candidate_id']))],'accuracy_claim':'unchanged raw predictions; review yield requires evaluation'}
        from .contracts import validate_inspection
        validate_inspection(report)
        return report

    def batch(self,inputs,out,**kwargs):
        from bluecho.phase1.download import atomic_json
        results=[];out=Path(out);out.mkdir(parents=True,exist_ok=True)
        try:
            for i,source in enumerate(inputs):
                try:
                    receipt=self.inspect(source,out/f'{i:04d}',**kwargs);results.append({'input':str(source),'status':'PASS','inspection_reports':receipt['inspection_reports']})
                except (ValueError,OSError) as exc:results.append({'input':str(source),'status':'ERROR','detail':str(exc)})
                atomic_json(out/'batch.json',results)
        except KeyboardInterrupt:
            atomic_json(out/'batch.json',results);raise
        return results

    def inspect(self,source,out,*,bottom_config=None,**kwargs):
        from bluecho.phase1.download import atomic_json
        if self.engine is None:raise ValueError('Supply a RecordingEngine')
        result=self.engine.predict(source,out,**kwargs);out=Path(out)
        paths=[out/r['results'] for r in result['windows']] if 'windows' in result else [out/'results.json']
        reports=[]
        for path in paths:
            raw=json.loads(path.read_text());mp=path.parent/'positioning_metadata.json';metadata=json.loads(mp.read_text()) if mp.exists() else None
            bottom=None
            if 'windows' in result:
                import numpy as np
                from .bottom import track_bottom, BottomConfig, render_trace
                raw_path=out/'decoded'/path.parent.name/'raw_samples.npz'
                if raw_path.exists() and metadata:
                    with np.load(raw_path,allow_pickle=False) as archive: samples=archive['samples'] if 'samples' in archive else archive[archive.files[0]]
                    bottom=track_bottom(samples,metadata['pings'],source_sha256=raw['source_sha256'],config=bottom_config or BottomConfig())
                    if bottom_config is not None:
                        metadata['flat_seabed_verified']=bottom_config.flat_seabed_verified
                        metadata['level_sensor_verified']=bottom_config.level_sensor_verified
                    atomic_json(path.parent/'bottom.json',bottom);render_trace(samples,bottom,path.parent/'bottom.png')
            report=self.assess(raw,metadata=metadata,bottom=bottom);atomic_json(path.parent/'inspection.json',report);reports.append(str(path.parent/'inspection.json'))
        return {'status':'PASS','inspection_reports':reports,'raw_result':result}


def diverse_selection(reports,budget):
    """Round-robin source groups, preserving priority within each group."""
    groups={}
    for report in reports:
        for c in report['candidates']:groups.setdefault(c['source_group'],[]).append(c)
    for values in groups.values():values.sort(key=lambda c:(c['original_prediction']['modality'],c['original_prediction']['model_id'],-c['review_priority'] if self.ranking=='reasons' else -c['detector_score']['value'],c['candidate_id']))
    selected=[];seen=set()
    while len(selected)<budget and any(groups.values()):
        for group in sorted(groups):
            if groups[group] and len(selected)<budget:
                c=groups[group].pop(0)
                if c['candidate_id'] not in seen:selected.append(c);seen.add(c['candidate_id'])
    return selected


def associate_aligned(reports, correspondence):
    """Link known common-canvas observations; never suppress or average them.

    correspondence maps source hash + canonical source reference to a verified
    common-frame translation and a bounded registration error in original pixels.
    Only translation-only alignment is supported; unknown/warped geometry is skipped.
    """
    import math
    def key(c):
        return c['source_sha256']+':'+json.dumps(c['original_prediction']['source_reference'],sort_keys=True)
    observations=[]
    for report in reports:
        for c in report['candidates']:
            transform=correspondence.get(key(c))
            if not transform or transform.get('verified') is not True:continue
            if transform.get('kind')!='translation' or not transform.get('frame_id'):continue
            error=transform.get('max_error_pixels');dx=transform.get('dx');dy=transform.get('dy')
            if any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in (error,dx,dy)) or error<0:continue
            x,y,z,t=c['original_prediction']['box_xyxy_pixels']
            if min(z-x,t-y)<=4*error:continue
            observations.append((c,transform,[x+dx,y+dy,z+dx,t+dy]))
    associations=[]
    for i,(a,ta,ba) in enumerate(observations):
        for b,tb,bb in observations[i+1:]:
            if a['candidate_id']==b['candidate_id'] or ta['frame_id']!=tb['frame_id'] or a['original_prediction']['modality']!=b['original_prediction']['modality']:continue
            error=ta['max_error_pixels']+tb['max_error_pixels']
            # Conservative lower intersection under bounded registration error.
            inter=max(0,min(ba[2],bb[2])-max(ba[0],bb[0])-2*error)*max(0,min(ba[3],bb[3])-max(ba[1],bb[1])-2*error)
            area_a=(ba[2]-ba[0])*(ba[3]-ba[1]);area_b=(bb[2]-bb[0])*(bb[3]-bb[1]);lower=inter/(area_a+area_b-inter)
            if lower>=.5:
                same=a['native_label']==b['native_label']
                associations.append({'candidate_ids':[a['candidate_id'],b['candidate_id']],'frame_id':ta['frame_id'],'registration_error_bound_pixels':error,'iou_lower_bound':lower,'independent_detections':False,'identity_confirmed':False,'reason_codes':[] if same else ['INCONSISTENT_ALIGNED_OBSERVATIONS'],'scores_combined':False})
    return associations
