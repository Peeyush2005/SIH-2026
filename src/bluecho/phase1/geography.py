"""Explicit source-bound positioning; missing geometry remains null."""
import csv
from datetime import datetime,timezone
import json
import math
from pathlib import Path
from pyproj import CRS,Geod,Transformer
from bluecho.engine import InputError
from .download import digest

GEOD=Geod(ellps='WGS84')


def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)


def timestamp(value):
    if value is None:return None
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError('timezone required')
        return d.astimezone(timezone.utc).isoformat()
    except (ValueError,AttributeError):raise InputError('Timestamps require ISO8601 with an explicit timezone')


def load_sidecar(path,source,width,height):
    path=Path(path)
    if path.stat().st_size>32*1024**2:raise InputError('Sidecar exceeds 32 MiB')
    if path.suffix.lower()=='.csv':
        rows=list(csv.DictReader(path.open(newline='')))
        if not rows:raise InputError('Empty sidecar CSV')
        common=['schema_version','source_sha256','image_width','image_height','modality']
        for k in common:
            if len({r.get(k) for r in rows})!=1:raise InputError('CSV rows disagree on source binding: '+k)
        first=rows[0]
        data={'schema_version':first['schema_version'],'source_sha256':first['source_sha256'],'image_width':int(first['image_width']),'image_height':int(first['image_height']),'modality':first['modality'],'mapping':'ping_rows','pings':[]}
        data['positioning_scope']=first.get('positioning_scope') or 'Supplied navigation, accuracy unvalidated'
        for r in rows:
            def num(k):return float(r[k]) if r.get(k,'').strip() else None
            data['pings'].append({'row':int(r['row']),'ping_index':int(r['ping_index']),'timestamp':r.get('timestamp') or None,'channel':r.get('channel'),'side':r.get('side'),'heading_degrees':num('heading_degrees'),'sensor_position':{'x':num('sensor_x'),'y':num('sensor_y'),'crs':r.get('sensor_crs'),'reference':r.get('position_reference'),'valid':r.get('navigation_valid','').lower()=='true'},'range_start':num('range_start'),'range_end':num('range_end'),'range_unit':r.get('range_unit'),'range_geometry':r.get('range_geometry'),'sample_count':int(r['sample_count']),'sample_direction':r.get('sample_direction'),'altitude':num('altitude'),'altitude_unit':r.get('altitude_unit'),'altitude_reference':r.get('altitude_reference'),'navigation_valid':r.get('navigation_valid','').lower()=='true'})
    else:
        data=json.loads(path.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(InputError('Nonfinite metadata')))
    validate_sidecar(data,source,width,height)
    data['metadata_provenance']={'source':path.name,'sha256':digest(path),'input_provenance':data.get('input_provenance','supplied_unvalidated')}
    return data


def validate_sidecar(data,source,width,height):
    from .contracts import validate_schema
    validate_schema(data,'sidecar-1.0.schema.json')
    if data.get('schema_version')!='1.0':raise InputError('Unsupported sidecar schema')
    if data.get('source_sha256')!=digest(source):raise InputError('Sidecar source checksum does not match input')
    if (data.get('image_width'),data.get('image_height'))!=(width,height):raise InputError('Sidecar image dimensions mismatch')
    if data.get('pixel_convention','pixel_edge') not in ('pixel_edge','pixel_center'):raise InputError('Unsupported pixel convention')
    if data.get('mapping')=='affine':
        a=data.get('transform',[])
        if len(a)!=6 or not all(finite(x) for x in a) or abs(a[0]*a[4]-a[1]*a[3])<1e-18:raise InputError('Invalid affine transform')
        try:CRS.from_user_input(data['crs'])
        except Exception as exc:raise InputError('Invalid affine CRS') from exc
    elif data.get('mapping')=='ping_rows':
        seen=set()
        for r in data.get('pings',[]):
            row=r.get('row')
            if type(row)!=int or not 0<=row<height or row in seen:raise InputError('Ping rows must be unique explicit image rows')
            seen.add(row);r['timestamp']=timestamp(r.get('timestamp'))
            if type(r.get('sample_count'))!=int or r['sample_count']!=width:raise InputError('Sample count must equal image width; supply explicit unresized sample geometry')
            if type(r.get('ping_index'))!=int:raise InputError('Explicit ping index required')
        if not seen:raise InputError('No explicit ping-to-row mapping')
    else:raise InputError('Mapping must be affine or ping_rows')


def meters(value,unit):
    if not finite(value):raise ValueError('missing_or_invalid_range_or_altitude')
    if unit=='m':return value
    if unit=='ft':return value*.3048
    raise ValueError('unknown_distance_units')


def lonlat(x,y,crs):
    if not finite(x) or not finite(y):raise ValueError('invalid_navigation')
    if not crs:raise ValueError('navigation_crs_unavailable')
    tx=Transformer.from_crs(CRS.from_user_input(crs),'EPSG:4326',always_xy=True)
    lon,lat=tx.transform(x,y,errcheck=True)
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:raise ValueError('navigation_out_of_bounds')
    return lon,lat


def _position_pixel(x,y,metadata):
    if not metadata:return None,'geographical_metadata_unavailable',None
    if metadata['mapping']=='affine':
        a,b,c,d,e,f=metadata['transform']
        if not all(finite(v) for v in [a,b,c,d,e,f]) or abs(a*e-b*d)<1e-18:raise ValueError('invalid_affine_transform')
        convention=metadata.get('pixel_convention','pixel_edge')
        if convention not in ('pixel_edge','pixel_center'):raise ValueError('unsupported_pixel_convention')
        if convention=='pixel_center':x-=.5;y-=.5
        lon,lat=lonlat(a*x+b*y+c,d*x+e*y+f,metadata['crs'])
        return [lon,lat],'supplied_raster_affine',{'source_crs':metadata['crs'],'assumptions':metadata.get('assumptions',[])}
    row=int(math.floor(y));r=next((r for r in metadata['pings'] if r['row']==row),None)
    if r is None:return None,'ping_row_metadata_unavailable',None
    ref={'ping_index':r['ping_index'],'channel':r.get('channel'),'sample_index':int(math.floor(x)),'timestamp':r.get('timestamp'),'row':row}
    if r.get('packet_offset_bytes') is not None:ref['packet_offset_bytes']=r['packet_offset_bytes']
    try:
        pos=r.get('sensor_position',{})
        if not pos.get('valid',False):raise ValueError('navigation_invalid_or_unverified')
        if pos.get('reference') not in ('towfish','auv_sensor','sonar_sensor','vessel'):raise ValueError('sensor_position_reference_unavailable')
        if pos['reference']=='vessel' and not metadata.get('allow_vessel_approximation',False):raise ValueError('vessel_gps_is_not_towfish_position')
        origin=lonlat(pos.get('x'),pos.get('y'),pos.get('crs'))
        heading=r.get('heading_degrees')
        if not finite(heading) or not 0<=heading<360:raise ValueError('heading_unavailable_or_invalid')
        if r.get('heading_reference','true_north')!='true_north':raise ValueError('heading_reference_not_true_north')
        if r.get('side') not in ('port','starboard'):raise ValueError('sonar_side_unavailable')
        if r.get('sample_direction') not in ('near_to_far','far_to_near'):raise ValueError('sample_orientation_unavailable')
        if not 0<=x<=r['sample_count']:raise ValueError('sample_out_of_range')
        lo=meters(r.get('range_start'),r.get('range_unit'));hi=meters(r.get('range_end'),r.get('range_unit'))
        if lo<0 or hi<=lo:raise ValueError('invalid_range_extent')
        fraction=x/r['sample_count']
        if r['sample_direction']=='far_to_near':fraction=1-fraction
        distance=lo+fraction*(hi-lo);assumptions=[]
        if r.get('range_geometry')=='slant':
            if r.get('altitude_reference')!='seabed':raise ValueError('altitude_above_seabed_unavailable')
            altitude=meters(r.get('altitude'),r.get('altitude_unit'))
            if altitude<=0:raise ValueError('altitude_above_seabed_unavailable')
            if distance<altitude:raise ValueError('water_column_sample_no_flat_seabed_intersection')
            distance=math.sqrt(max(0,distance*distance-altitude*altitude));assumptions.append('flat seabed at supplied sensor altitude; no terrain or attitude correction')
        elif r.get('range_geometry')!='ground':raise ValueError('range_geometry_unavailable')
        if pos['reference']=='vessel':assumptions.append('explicit vessel-position approximation; towfish layback unknown')
        bearing=(heading+(-90 if r['side']=='port' else 90))%360
        lon,lat,_=GEOD.fwd(*origin,bearing,distance)
        ref.update(ground_range_m=distance,position_reference=pos['reference'],assumptions=assumptions,sensor_coordinates=list(origin))
        return [lon,lat],'ping_sample_flat_seabed' if r['range_geometry']=='slant' else 'ping_sample_ground_range',ref
    except (ValueError,KeyError,TypeError) as exc:return None,str(exc),ref


def position_pixel(x,y,metadata):
    """Canonical strict position interface; longitude, latitude, never vessel fallback."""
    from bluecho.inspection.geometry import position
    result=position(x,y,metadata)
    return result['coordinates'],result.get('method') if result['coordinates'] is not None else ';'.join(result['reason_codes']).lower(),result.get('reference')


def geotag_box(box,metadata):
    from bluecho.inspection.geometry import position
    import hashlib
    a,b,c,d=box;cx,cy=(a+c)/2,(b+d)/2
    if not all(finite(v) for v in box) or not a<c or not b<d:raise ValueError('Invalid box')
    result=position(cx,cy,metadata);point=result['coordinates']
    base={'coordinates':point,'crs':'EPSG:4326' if point else None,'position_method':result.get('method') if point else None,'position_reason':None if point else ';'.join(result['reason_codes']),'metric_dimensions':None,'source_location_reference':result.get('reference'),'geographic_footprint':None,'location_status':result['status'],'uncertainty':result['uncertainty'],'altitude_provenance':result.get('altitude_provenance','unavailable'),'position_reason_codes':result['reason_codes'],'positioning_assumptions':(metadata or {}).get('assumptions',[]),'metadata_provenance':(metadata or {}).get('metadata_provenance'),'footprint_status':'unavailable','footprint_reason':'position_unavailable'}
    if metadata:
        base['metadata_canonical_sha256']=hashlib.sha256(json.dumps(metadata,sort_keys=True,allow_nan=False).encode()).hexdigest()
    if point:
        def p(x,y):return position(x,y,metadata)['coordinates']
        try:
            if metadata['mapping']=='ping_rows':
                rows=sorted([r for r in metadata['pings'] if b<=r['row']<d],key=lambda r:r['row'])
                for u,v in zip(rows,rows[1:]):
                    gap=(datetime.fromisoformat(timestamp(v['timestamp']))-datetime.fromisoformat(timestamp(u['timestamp']))).total_seconds()
                    if v['row']!=u['row']+1 or not 0<gap<=metadata.get('max_navigation_gap_s',2):raise ValueError('footprint_navigation_gap')
            # Ping rows use their actual row position; no invented between-row track.
            bottom=d if metadata['mapping']=='affine' else max(b,d-1e-6)
            perimeter=[]
            for start,end in [((a,b),(c,b)),((c,b),(c,bottom)),((c,bottom),(a,bottom)),((a,bottom),(a,b))]:
                for k in range(4):perimeter.append(p(start[0]+(end[0]-start[0])*k/4,start[1]+(end[1]-start[1])*k/4))
            if any(q is None for q in perimeter):raise ValueError('boundary_metadata_incomplete')
            perimeter.append(perimeter[0])
            if any(abs(u[0]-v[0])>180 for u,v in zip(perimeter,perimeter[1:])):raise ValueError('antimeridian_footprint_requires_split')
            def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            edges=list(zip(perimeter,perimeter[1:]))
            for i,(u,v) in enumerate(edges):
                for j,(q,r) in enumerate(edges):
                    if abs(i-j)<=1 or {i,j}=={0,len(edges)-1}:continue
                    if orient(u,v,q)*orient(u,v,r)<0 and orient(q,r,u)*orient(q,r,v)<0:raise ValueError('self_intersecting_footprint')
            area,_=GEOD.polygon_area_perimeter([q[0] for q in perimeter],[q[1] for q in perimeter])
            if abs(area)<1e-8:raise ValueError('degenerate_footprint')
            base.update(geographic_footprint=perimeter,footprint_status='estimated_detection_box_boundary',footprint_reason=None)
            left,right,top,bot=p(a,cy),p(c,cy),p(cx,b),p(cx,bottom)
            if all(q is not None for q in [left,right,top,bot]):
                base['metric_dimensions']={'width_m':abs(GEOD.inv(*left,*right)[2]),'height_m':abs(GEOD.inv(*top,*bot)[2]),'meaning':'detection-box footprint cross-image/along-image midpoint spans; not physical object size or height','method':'WGS84 geodesic between mapped edge midpoints','uncertainty_status':'unknown','units':'m'}
        except (ValueError,KeyError,TypeError) as exc:base['footprint_reason']=str(exc)
    return base


def tracks(metadata):
    features=[]
    if metadata and metadata.get('mapping')=='ping_rows':
        valid=[]
        for r in sorted(metadata['pings'],key=lambda r:r['row']):
            p=r.get('sensor_position',{})
            try:
                if not p.get('valid'):continue
                xy=list(lonlat(p['x'],p['y'],p['crs']))
                props={k:r.get(k) for k in ['ping_index','timestamp','channel']};props.update(kind='sensor_position',position_reference=p.get('reference'),real_accuracy='unvalidated')
                features.append({'type':'Feature','geometry':{'type':'Point','coordinates':xy},'properties':props});valid.append((r,xy))
            except Exception:continue
        # Do not draw connections across missing ping IDs, invalid nav or backwards time.
        lines=[];line=[];last=None
        for r,xy in valid:
            contiguous=last is not None and r['ping_index']==last['ping_index']+1 and r['row']==last['row']+1 and r.get('timestamp') and last.get('timestamp') and 0<(datetime.fromisoformat(timestamp(r['timestamp']))-datetime.fromisoformat(timestamp(last['timestamp']))).total_seconds()<=metadata.get('max_navigation_gap_s',2) and abs(xy[0]-line[-1][0])<=180
            if not contiguous:
                if len(line)>1:lines.append(line)
                line=[]
            line.append(xy);last=r
        if len(line)>1:lines.append(line)
        for line in lines:features.append({'type':'Feature','geometry':{'type':'LineString','coordinates':line},'properties':{'kind':'sensor_track','accuracy':'unvalidated'}})
    return {'type':'FeatureCollection','features':features}
