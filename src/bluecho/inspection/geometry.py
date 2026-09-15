"""Strict positioning through Phase 1's pixel and WGS84 coordinate convention."""
import copy
import math
from datetime import datetime


def position(x,y,metadata):
    from bluecho.phase1.geography import _position_pixel as position_pixel, meters, GEOD, lonlat
    m=copy.deepcopy(metadata)
    unavailable=lambda reason: {'coordinates':None,'status':'unavailable','reason_codes':[reason],'uncertainty':{'status':'unknown'},'altitude_provenance':'unavailable'}
    if not m:return unavailable('INCOMPLETE_METADATA')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in [x,y]):return unavailable('INVALID_PIXEL_COORDINATES')
    if m.get('mapping')=='affine':
        try:point,method,reference=position_pixel(x,y,m)
        except Exception:return unavailable('INVALID_CRS_OR_AFFINE')
        uncertainty={'status':'unknown'}
        bound=m.get('horizontal_error_bound_m')
        if bound is not None:
            if not isinstance(bound,(float,int)) or not math.isfinite(bound) or bound<0:return unavailable('INVALID_AFFINE_ERROR_BOUND')
            uncertainty={'status':'bounded_under_declared_model','radius_m':bound,'units':'m','meaning':'supplied horizontal engineering bound; not a statistical confidence interval','provenance':m.get('error_bound_provenance','supplied')}
        return {'coordinates':point,'status':'estimate' if point else 'unavailable','method':method,'reference':reference,'reason_codes':[],'uncertainty':uncertainty,'altitude_provenance':'not_applicable'}
    if not m.get('modality','').startswith('SSS'):return unavailable('SSS_GEOMETRY_NOT_APPLICABLE')
    r=next((p for p in m.get('pings',[]) if p.get('row')==int(math.floor(y))),None)
    if r is None:return unavailable('PING_METADATA_UNAVAILABLE')
    try:
        stamp=datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
    except (ValueError,KeyError,TypeError,AttributeError):return unavailable('TIMESTAMP_UNAVAILABLE')
    if not m.get('calibration_verified'):return unavailable('RANGE_CALIBRATION_UNVERIFIED')
    if not m.get('timestamp_alignment_verified'):return unavailable('TIMESTAMP_ALIGNMENT_UNVERIFIED')
    slant=r.get('range_geometry')=='slant'
    if slant and (not m.get('flat_seabed_verified') or not m.get('level_sensor_verified')):return unavailable('GEOMETRY_ASSUMPTIONS_UNVERIFIED')
    if not slant and not m.get('ground_range_verified'):return unavailable('GROUND_RANGE_MAPPING_UNVERIFIED')
    if r.get('time_delay_seconds',0)!=0 and not r.get('range_origin_verified'):return unavailable('RANGE_OFFSET_UNRESOLVED')
    try:
        heading=float(r['heading_degrees'])
        if not math.isfinite(heading) or abs(heading)>10000:raise ValueError()
        r['heading_degrees']=heading%360
    except (ValueError,KeyError,TypeError):return unavailable('HEADING_INVALID')
    if r.get('heading_reference')!='true_north':return unavailable('HEADING_REFERENCE_UNVERIFIED')
    altitude_provenance=r.get('altitude_provenance','unavailable')
    if not slant:altitude_provenance='not_applicable_ground_range'
    if slant and altitude_provenance not in ('measured','estimated','manually_supplied'):return unavailable('ALTITUDE_PROVENANCE_UNAVAILABLE')
    if slant and altitude_provenance=='estimated' and r.get('altitude_status')!='reliable_under_declared_assumptions':return unavailable('ESTIMATED_ALTITUDE_UNRELIABLE')
    pos=r.get('sensor_position',{})
    if pos.get('reference')=='vessel':
        offset=r.get('sensor_offset')
        if not offset or offset.get('verified') is not True:return unavailable('VESSEL_GPS_IS_NOT_SENSOR_POSITION')
        try:
            forward=float(offset['forward_m']);right=float(offset['starboard_m'])
            if not math.isfinite(forward+right):raise ValueError()
            origin=lonlat(pos['x'],pos['y'],pos['crs']);heading=float(r['heading_degrees'])
            a,b,_=GEOD.fwd(*origin,heading+math.degrees(math.atan2(right,forward)),math.hypot(forward,right))
            r['sensor_position']={**pos,'x':a,'y':b,'crs':'EPSG:4326','reference':'sonar_sensor'}
        except Exception:return unavailable('INVALID_SENSOR_OFFSET')
    try:point,method,ref=position_pixel(x,y,m)
    except Exception:return unavailable('INVALID_CRS_OR_GEOMETRY')
    if point is None:return unavailable(method.upper())
    result={'coordinates':point,'crs':'EPSG:4326','status':'estimate','method':method,'reference':ref,'reason_codes':[],'altitude_provenance':altitude_provenance,'uncertainty':{'status':'unknown'}}
    # Conservative deterministic bound: independent bounded inputs are NOT Gaussian sigmas.
    errors=r.get('error_bounds')
    if not errors:return result
    try:
        keys=('navigation_m','heading_degrees','altitude_m','slant_range_m') if slant else ('navigation_m','heading_degrees','ground_range_m')
        e={k:float(errors[k]) for k in keys}
        if any(not math.isfinite(v) or v<0 for v in e.values()) or e['heading_degrees']>180:raise ValueError()
        if pos.get('reference')=='vessel':
            offset_error=float(errors['sensor_offset_m'])
            if not math.isfinite(offset_error) or offset_error<0:raise ValueError()
            e['navigation_m']+=offset_error
        if not slant:
            g=ref['ground_range_m'];high=g+e['ground_range_m']
            result['uncertainty']={'status':'bounded_under_declared_model','radius_m':e['navigation_m']+e['ground_range_m']+2*high*math.sin(math.radians(e['heading_degrees'])/2),'units':'m','meaning':'conservative engineering bound, not statistical confidence; excludes unmodelled terrain/attitude bias','inputs':e,'model':'ground-range interval plus navigation disk plus heading chord'}
            return result
        h=meters(r['altitude'],r['altitude_unit']);s=meters(r['range_start'],r['range_unit']);end=meters(r['range_end'],r['range_unit']);f=x/r['sample_count']
        if r['sample_direction']=='far_to_near':f=1-f
        slant=s+f*(end-s);g=ref['ground_range_m']
        if r['range_geometry']!='slant':raise ValueError()
        if slant-e['slant_range_m']<=h+e['altitude_m']:
            result['reason_codes'].append('NEAR_NADIR_UNCERTAINTY_DOMAIN');return result
        low=math.sqrt((slant-e['slant_range_m'])**2-(h+e['altitude_m'])**2)
        high=math.sqrt((slant+e['slant_range_m'])**2-max(0,h-e['altitude_m'])**2)
        bound=e['navigation_m']+max(g-low,high-g)+2*high*math.sin(math.radians(e['heading_degrees'])/2)
        result['uncertainty']={'status':'bounded_under_declared_model','radius_m':bound,'meaning':'conservative horizontal worst-case bound; excludes unmodelled terrain, attitude and metadata bias','inputs':e,'model':'range interval plus navigation disk plus heading chord'}
    except (KeyError,ValueError,TypeError):result['reason_codes'].append('UNCERTAINTY_INPUTS_INVALID_OR_INCOMPLETE')
    return result


def interpolate_navigation(before,after,when,*,max_gap_s):
    """Interpolate a known sensor track along WGS84 geodesic, never extrapolate."""
    from bluecho.phase1.geography import GEOD,lonlat
    def dt(s):
        d=datetime.fromisoformat(s.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError('Timezone required')
        return d
    a,b,t=dt(before['timestamp']),dt(after['timestamp']),dt(when);gap=(b-a).total_seconds()
    if not 0<gap<=max_gap_s or not a<=t<=b:raise ValueError('TIMESTAMP_GAP_OR_EXTRAPOLATION')
    p,q=before['sensor_position'],after['sensor_position']
    if p['reference']!=q['reference'] or not p['valid'] or not q['valid']:raise ValueError('INCONSISTENT_SENSOR_REFERENCE')
    if before.get('heading_reference')!='true_north' or after.get('heading_reference')!='true_north':raise ValueError('HEADING_REFERENCE_UNVERIFIED')
    first=lonlat(p['x'],p['y'],p['crs']);last=lonlat(q['x'],q['y'],q['crs']);az,_,length=GEOD.inv(*first,*last);f=(t-a).total_seconds()/gap
    x,y,_=GEOD.fwd(*first,az,length*f);h=before['heading_degrees'];delta=(after['heading_degrees']-h+180)%360-180
    return {'timestamp':when,'sensor_position':{'x':x,'y':y,'crs':'EPSG:4326','reference':p['reference'],'valid':True},'heading_degrees':(h+f*delta)%360,'heading_reference':'true_north','interpolation':{'method':'geodesic_position_shortest_heading_arc','gap_s':gap}}
