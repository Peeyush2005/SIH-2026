"""Independent bounded-window first-return proposals, never implicit altitude."""
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import json
import math
import numpy as np

@dataclass(frozen=True)
class BottomConfig:
    max_vertical_rate_m_s: float | None = None
    max_time_gap_s: float = 1.0
    flat_seabed_verified: bool = False
    level_sensor_verified: bool = False
    calibration_verified: bool = False
    water_column_verified: bool = False
    support_samples: int = 16
    contrast_sigma: float = 6.0


def track_bottom(raw, pings, *, source_sha256, config=BottomConfig(), manual=None):
    """Rows are raw pings, columns original samples. O(samples) working memory.

    Configuration rate is a supplied vehicle bound, not a learned smoothing knob.
    Manual input is source-bound {source_sha256, reviewer, corrections:[{row,sample}]}.
    A corrected first return still needs verified level/flat geometry for altitude.
    """
    a=np.asarray(raw)
    if a.ndim!=2 or not 1<=a.shape[0]<=512 or not 32<=a.shape[1]<=32768:
        raise ValueError('Supported window is 1..512 pings by 32..32768 samples')
    if len(pings)!=len(a):raise ValueError('Explicit metadata for every row required')
    if len(source_sha256)!=64:raise ValueError('SHA256 source identity required')
    if config.support_samples<4 or config.support_samples>a.shape[1]//4 or config.contrast_sigma<=0 or config.max_time_gap_s<=0:
        raise ValueError('Invalid bottom configuration')
    if config.max_vertical_rate_m_s is not None and (not math.isfinite(config.max_vertical_rate_m_s) or config.max_vertical_rate_m_s<=0):raise ValueError('Positive physical vertical-rate bound required')
    raw_hash=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    corrections={}
    if manual:
        if manual.get('source_sha256')!=source_sha256 or manual.get('raw_array_sha256')!=raw_hash:raise ValueError('Manual trace source/window mismatch')
        for c in manual['corrections']:
            row=c['row'];sample=c['sample']
            if type(row)!=int or row in corrections or not 0<=row<len(a) or not isinstance(sample,(int,float)) or not math.isfinite(sample) or not 0<=sample<a.shape[1]:raise ValueError('Invalid manual trace sample')
            corrections[row]=sample
    rows=[];previous=None
    for i,(signal,p) in enumerate(zip(a,pings)):
        reasons=[];chosen=None;distance=None;altitude=None;candidates=[]
        x=signal.astype(float)
        if p.get('sample_direction')=='far_to_near':x=x[::-1]
        if not np.isfinite(x).all():reasons.append('INVALID_SAMPLES')
        elif np.ptp(x)==0 or p.get('invalid',False):reasons.append('DROPOUT_OR_CONSTANT_ROW')
        else:
            k=config.support_samples
            # Median bins reject isolated bright targets; a sustained step is only a proposal.
            n=len(x)//k;bins=np.median(x[:n*k].reshape(n,k),axis=1)
            noise=max(float(np.median(np.abs(np.diff(bins)-np.median(np.diff(bins)))))*1.4826, float(np.ptp(x))*0.002, 1e-9)
            for j in range(2,n-2):
                before=np.median(bins[j-2:j]);after=np.median(bins[j:j+2])
                if after-before>config.contrast_sigma*noise and min(bins[j:j+2])>before+config.contrast_sigma*noise:
                    s=j*k
                    if p.get('sample_direction')=='far_to_near':s=len(x)-1-s
                    if not candidates or abs(s-candidates[-1]['sample'])>=2*k:
                        candidates.append({'sample':int(s),'contrast_sigma':float((after-before)/noise)})
            if len(candidates)==1:chosen=float(candidates[0]['sample'])
            else:reasons.append('AMBIGUOUS_BOTTOM' if candidates else 'BOTTOM_NOT_FOUND')
        if i in corrections:chosen=float(corrections[i]);reasons=[r for r in reasons if r not in ('AMBIGUOUS_BOTTOM','BOTTOM_NOT_FOUND')]
        try:
            lo=float(p['range_start']);hi=float(p['range_end']);count=p['sample_count']
            if p.get('range_unit')!='m' or p.get('range_geometry')!='slant' or count!=len(x) or not math.isfinite(lo+hi) or not 0<=lo<hi or p.get('sample_direction') not in ('near_to_far','far_to_near') or p.get('side') not in ('port','starboard') or (p.get('time_delay_unresolved',False) or (p.get('time_delay_seconds',0) not in (0,None) and not p.get('range_offset_resolved',False))):raise ValueError()
            if chosen is not None:
                fraction=chosen/count
                if p['sample_direction']=='far_to_near':fraction=1-fraction
                distance=lo+fraction*(hi-lo)
        except (KeyError,ValueError,TypeError):reasons.append('INVALID_RANGE_CALIBRATION')
        if not config.calibration_verified:reasons.append('CALIBRATION_UNVERIFIED')
        if not config.water_column_verified:reasons.append('WATER_COLUMN_INTERPRETATION_UNVERIFIED')
        if not config.flat_seabed_verified or not config.level_sensor_verified:reasons.append('ALTITUDE_GEOMETRY_UNVERIFIED')
        if config.max_vertical_rate_m_s is None:reasons.append('MOTION_BOUND_UNAVAILABLE')
        try:
            t=datetime.fromisoformat(p['timestamp'].replace('Z','+00:00'))
            if t.tzinfo is None:raise ValueError()
        except (KeyError,TypeError,ValueError,AttributeError):t=None;reasons.append('TIMESTAMP_UNAVAILABLE')
        if previous and distance is not None and t:
            old,old_t,side=previous;dt=(t-old_t).total_seconds()
            if side!=p.get('side'):reasons.append('SIDE_SEQUENCE_CHANGED')
            elif not 0<dt<=config.max_time_gap_s:reasons.append('TIMESTAMP_GAP')
            elif config.max_vertical_rate_m_s is not None and abs(distance-old)>config.max_vertical_rate_m_s*dt+2*config.support_samples*(hi-lo)/count:
                reasons.append('BOTTOM_CONTINUITY_VIOLATION')
        if distance is not None and t and not reasons:previous=(distance,t,p['side']);altitude=distance
        elif reasons:previous=None
        rows.append({'row':i,'ping_index':p.get('ping_index'),'side':p.get('side'),'candidates':candidates,'accepted_sample':chosen if not any(r in reasons for r in ('DROPOUT_OR_CONSTANT_ROW','INVALID_SAMPLES','BOTTOM_CONTINUITY_VIOLATION')) else None,'first_return_range_m':distance,'altitude_m':altitude,'altitude_provenance':'manually_supplied' if altitude is not None and i in corrections else 'estimated' if altitude is not None else 'unavailable','status':'reliable_under_declared_assumptions' if altitude is not None else 'unreliable','reason_codes':sorted(set(reasons))})
    return {'schema_version':'1.0','source_sha256':source_sha256,'method':'sustained_median_step_with_physical_rate_gate','config':asdict(config),'manual_provenance':manual,'rows':rows,'field_accuracy':'unvalidated','input_shape':list(a.shape),'raw_array_sha256':raw_hash}


def compare_sides(port, starboard, *, tolerance_m):
    """Only explicitly identical ping IDs; caller supplies defensible tolerance."""
    if not math.isfinite(tolerance_m) or tolerance_m<0:raise ValueError('Invalid tolerance')
    if port['source_sha256']!=starboard['source_sha256']:raise ValueError('Sides must share source')
    other={r['ping_index']:r for r in starboard['rows']}
    disagreements=[]
    for r in port['rows']:
        s=other.get(r['ping_index'])
        if s and r['side']=='port' and s['side']=='starboard' and r['first_return_range_m'] is not None and s['first_return_range_m'] is not None and abs(r['first_return_range_m']-s['first_return_range_m'])>tolerance_m:
            disagreements.append(r['ping_index'])
            for v in (r,s):
                v['altitude_m']=None;v['altitude_provenance']='unavailable';v['status']='unreliable';v['reason_codes']=sorted(set(v['reason_codes']+['SIDE_DISAGREEMENT']))
    return disagreements


def render_trace(raw, trace, output):
    from PIL import Image,ImageDraw
    x=np.asarray(raw,dtype=float);lo,hi=np.percentile(x,[1,99]);view=Image.fromarray(np.uint8(np.clip((x-lo)/max(hi-lo,1e-9)*255,0,255))).convert('RGB');draw=ImageDraw.Draw(view)
    for row in trace['rows']:
        y=row['row']
        if row['status']=='unreliable':draw.line((0,y,3,y),fill='red')
        for c in row['candidates']:draw.point((c['sample'],y),fill='orange')
        if row['accepted_sample'] is not None:draw.point((int(row['accepted_sample']),y),fill='lime' if row['altitude_m'] is not None else 'magenta')
    view.save(output)
