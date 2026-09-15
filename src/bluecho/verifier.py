"""Small learned SSS candidate verifier; acoustic proxies, not physical residuals."""
import json,hashlib,math
from pathlib import Path
import numpy as np
from PIL import Image
GENERIC=['raw_score','score_logit','width_fraction','height_fraction','log_aspect','area_fraction','boundary_truncation','return_mean','return_std','return_q25','return_q75','context_contrast']
ACOUSTIC=['range_adjacent_dark_contrast','range_dark_asymmetry','range_dark_extent','range_bright_dark_pair','range_vs_alongtrack_gradient','range_vs_alongtrack_profile_variation']
FEATURES=GENERIC+ACOUSTIC


def extract_features(image,boxes,*,modality='SSS_LF',range_axis=None):
    if modality!='SSS_LF':raise ValueError('Pipeline verifier supports SSS_LF only')
    if range_axis not in (None,'x'):raise ValueError('Only explicitly known horizontal range axis is supported')
    gray=image.convert('L');w,h=gray.size;rows=[]
    def patch(box):return np.asarray(gray.crop(tuple(map(int,box))).resize((32,32)),dtype=float)/255.
    for b in boxes:
        a,y,c,d=map(float,b['xyxy']);score=float(b['score'])
        if not (0<=a<c<=w and 0<=y<d<=h and 0<=score<=1):raise ValueError('Invalid original-pixel candidate')
        bw=c-a;bh=d-y;inside=patch((math.floor(a),math.floor(y),math.ceil(c),math.ceil(d)));background=patch((max(0,a-bw/2),max(0,y-bh/2),min(w,c+bw/2),min(h,d+bh/2)))
        clipped=max(1e-6,min(1-1e-6,score));g=[score,math.log(clipped/(1-clipped)),bw/w,bh/h,math.log(bw/bh),bw*bh/(w*h),float(a<=1 or y<=1 or c>=w-1 or d>=h-1),inside.mean(),inside.std(),np.quantile(inside,.25),np.quantile(inside,.75),inside.mean()-background.mean()]
        acoustic=[0.]*6
        if range_axis=='x' and a>=1 and c<=w-1:
            lo=max(0,a-bw);hi=min(w,c+bw);left=patch((lo,y,max(a,lo+1),d));right=patch((min(c,w-1),y,min(w,max(hi,c+1)),d));lm=left.mean();rm=right.mean();center=inside.mean()
            horizontal=np.concatenate([left,inside,right],axis=1);profile=horizontal.mean(axis=0);dark=profile<center-.1*max(inside.std(),.02)
            acoustic=[center-min(lm,rm),abs(lm-rm),dark.mean(),max(0,center-background.mean())*max(0,center-min(lm,rm)),np.abs(np.diff(horizontal,axis=1)).mean()-np.abs(np.diff(horizontal,axis=0)).mean(),horizontal.mean(axis=0).std()-horizontal.mean(axis=1).std()]
        rows.append(g+acoustic)
    return np.asarray(rows,dtype=float).reshape((-1,len(FEATURES)))


class CandidateVerifier:
    def __init__(self,path):
        self.path=Path(path);self.manifest=json.loads(self.path.read_text())
        if self.manifest['feature_names']!=FEATURES or self.manifest['modality']!='SSS_LF':raise ValueError('Incompatible verifier schema/modality')
    def score(self,image,boxes,*,modality='SSS_LF',range_axis=None,family='acoustic'):
        if family not in ('generic','acoustic'):raise ValueError('Unknown verifier family')
        actual='generic' if family=='acoustic' and range_axis is None else family
        x=extract_features(image,boxes,modality=modality,range_axis=range_axis);m=self.manifest['models'][actual];x=x[:,:len(m['mean'])]
        z=((x-np.asarray(m['mean']))/np.asarray(m['scale']))@np.asarray(m['coef'])+m['intercept'];p=1/(1+np.exp(-np.clip(z,-700,700)))
        results=[]
        for i,(b,value) in enumerate(zip(boxes,p)):
            used=actual
            if actual=='acoustic' and (b['xyxy'][0]<1 or b['xyxy'][2]>image.width-1):
                generic=self.manifest['models']['generic'];gx=x[i,:len(generic['mean'])];gz=((gx-np.asarray(generic['mean']))/np.asarray(generic['scale']))@np.asarray(generic['coef'])+generic['intercept'];value=1/(1+np.exp(-np.clip(gz,-700,700)));used='generic'
            results.append({'verifier_score':float(value),'verifier_family':used,'calibrated':False,'feature_fallback':family!=used,'raw_score':b['score'],'box_xyxy_pixels':b['xyxy']})
        return results


def inspect_pipeline(source,manifest,*,mode='baseline',verifier=None,range_axis=None,backend='native',device='cpu',threshold=None,source_nms_iou=.5):
    """Explicit experimental route wrapping the same Engine.original_raw call.

    The default production route is unchanged. Optional scores never replace raw scores.
    """
    from .engine import Engine
    from .geometry import merge_nms,map_box
    if mode not in ('baseline','high_recall','generic','acoustic'):raise ValueError('Unknown pipeline mode')
    engine=Engine(manifest,device=device,backend=backend);raw=engine.original_raw(source);boxes=[]
    for tile in raw['tiles']:
        for p in tile['predictions']:
            box=map_box(p['xyxy'],tile['crop_xyxy'])
            if box[2]>box[0] and box[3]>box[1]:boxes.append({**p,'xyxy':box,'tile_index':tile['tile_index'],'tile_xyxy':p['xyxy'],'crop_xyxy':tile['crop_xyxy']})
    boxes=merge_nms(boxes,source_nms_iou);image=Image.open(source)
    if mode in ('generic','acoustic'):
        if verifier is None:raise ValueError('Explicit verifier artifact required')
        v=CandidateVerifier(verifier)
        if engine.model_hash not in [v.manifest['detector_sha256'],v.manifest.get('compatible_onnx_sha256')]:raise ValueError('Verifier is bound to a different native/ONNX detector; no silent transfer')
        scored=v.score(image,boxes,modality='SSS_LF',range_axis=range_axis,family=mode)
    else:scored=[{'raw_score':b['score'],'verifier_score':None,'box_xyxy_pixels':b['xyxy'],'feature_fallback':False} for b in boxes]
    if threshold is None:
        if mode!='baseline':raise ValueError('Experimental modes require an explicit evaluated threshold')
        threshold=engine.thresholds['0']
    order=sorted(range(len(boxes)),key=lambda i:-(scored[i]['verifier_score'] if scored[i]['verifier_score'] is not None else boxes[i]['score']))
    return {'schema_version':'pipeline-review-1.0','mode':mode,'model_sha256':engine.model_hash,'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'threshold':threshold,'source_nms_iou':source_nms_iou,'preprocessing':'unchanged original engine','candidates':[{'original_prediction':b,**s,'selected':(s['verifier_score'] if s['verifier_score'] is not None else b['score'])>=threshold} for b,s in zip(boxes,scored)],'ranked_indices':order,'ranking_policy':'descending '+('verifier score' if mode in ('generic','acoustic') else 'raw detector score')+'; stable original order on ties','geographic_coordinates':None,'scope':'development-only; no independent survey confirmation'}


def metric_differences(candidate,baseline):
    """Zero-match localization stays unavailable, never zero or a subtraction error."""
    return {k:candidate[k]-baseline[k] if candidate.get(k) is not None and baseline.get(k) is not None else None for k in ('tp','fp','fn','mAP50_95','mean_matched_iou')}
