import copy,json
import numpy as np
import pytest
from PIL import Image
from pyproj import Transformer,Geod
from bluecho.engine import InputError
from bluecho.phase1.geography import geotag_box,position_pixel,load_sidecar,timestamp,tracks
from bluecho.phase1.quality import assess_quality,corruption
from bluecho.phase1.download import digest
from bluecho.phase1.inputs import xtf_packets
from bluecho.phase1.adapters import Registry


def metadata(side='starboard',unit='m',geometry='ground'):
    factor=1 if unit=='m' else 1/.3048
    pings=[{'row':i,'ping_index':100+i,'timestamp':f'2026-01-01T00:00:{i:02d}+00:00','channel':0,'sensor_position':{'x':0.,'y':0.,'crs':'EPSG:4326','reference':'towfish','valid':True},'heading_degrees':0.,'heading_reference':'true_north','altitude_provenance':'measured','side':side,'range_start':0.,'range_end':100*factor,'range_unit':unit,'range_geometry':geometry,'sample_count':100,'sample_direction':'near_to_far','altitude':30*factor,'altitude_unit':unit,'altitude_reference':'seabed'} for i in range(10)]
    return {'mapping':'ping_rows','pings':pings,'modality':'SSS','flat_seabed_verified':True,'level_sensor_verified':True,'calibration_verified':True,'timestamp_alignment_verified':True,'ground_range_verified':True}


def test_starboard_port_heading_and_feet():
    geo=Geod(ellps='WGS84')
    for side,az in [('starboard',90),('port',-90)]:
        point,method,_=position_pixel(50,2.5,metadata(side=side))
        bearing,_,distance=geo.inv(0,0,*point)
        assert distance==pytest.approx(50,abs=1e-6)
        assert bearing==pytest.approx(az,abs=1e-6)
        ft,_,_=position_pixel(50,2.5,metadata(side=side,unit='ft'))
        assert ft==pytest.approx(point,abs=1e-10)


def test_slant_geometry_altitude_not_depth():
    m=metadata(geometry='slant');p,_,_=position_pixel(50,2.5,m)
    assert Geod(ellps='WGS84').inv(0,0,*p)[2]==pytest.approx(40,abs=1e-6)
    m['pings'][2]['altitude']=None;m['pings'][2]['sensor_depth_below_surface_m']=30
    p,reason,_=position_pixel(50,2.5,m)
    assert p is None and 'altitude' in reason
    m=metadata(geometry='slant');p,reason,_=position_pixel(10,2.5,m)
    assert p is None and 'water_column' in reason


def test_vessel_not_fish_and_unknown_row():
    m=metadata();m['pings'][2]['sensor_position']['reference']='vessel'
    assert position_pixel(50,2.5,m)[0] is None
    m['allow_vessel_approximation']=True
    assert position_pixel(50,2.5,m)[0] is None # old approximation flag cannot bypass verified sensor offset
    assert position_pixel(20,15,m)[0] is None


def test_affine_crs_roundtrip_dimensions():
    t=Transformer.from_crs('EPSG:4326','EPSG:32630',always_xy=True)
    x,y=t.transform(-3,50)
    m={'mapping':'affine','crs':'EPSG:32630','transform':[2,0,x,0,-2,y]}
    p,_,_=position_pixel(30,20,m)
    xx,yy=t.transform(*p)
    assert xx==pytest.approx(x+60,abs=1e-6);assert yy==pytest.approx(y-40,abs=1e-6)
    g=geotag_box([10,10,30,20],m)
    assert g['metric_dimensions']['width_m']==pytest.approx(40,rel=.002)
    assert g['geographic_footprint'][0]==g['geographic_footprint'][-1]


def test_sidecar_binding_units_and_timestamp(tmp_path):
    src=tmp_path/'i.png';Image.new('RGB',(100,10)).save(src)
    m=metadata();m.update(schema_version='1.0',source_sha256=digest(src),image_width=100,image_height=10,modality='SSS')
    p=tmp_path/'meta.json';p.write_text(json.dumps(m));load_sidecar(p,src,100,10)
    m['source_sha256']='0'*64;p.write_text(json.dumps(m))
    with pytest.raises(InputError):load_sidecar(p,src,100,10)
    with pytest.raises(InputError):timestamp('2026-01-01T00:00:00')
    assert timestamp('2026-01-01T00:00:00Z').endswith('+00:00')
    m=metadata();m['pings'][2]['range_unit']='unknown'
    assert position_pixel(10,2.5,m)[0] is None


def test_missing_rows_are_not_dark_shadows():
    a=np.full((100,100,3),80,np.uint8);a[10:12]=0;a[20]=255
    q,_=assess_quality(Image.fromarray(a),invalid_rows=[11])
    assert q['invalid_rows']==1 and q['uncertain_low_signal_rows']==1 and q['saturated_rows']==1
    assert any(r['flag']=='uniform_low_signal_uncertain' for r in q['regions'])
    assert 'No quality-based rejection' in q['policy']


def test_corruption_label_envelope_and_no_geometry_change():
    im=Image.fromarray(np.full((80,120,3),100,np.uint8));truth=[{'class_id':0,'xyxy':[20,10,60,40]}]
    warped,boxes,invalid=corruption(im,truth,'motion')
    assert warped.size==im.size and boxes[0]['xyxy'][0]>=20 and boxes[0]['xyxy'][2]>60
    for name in ['speckle','intensity','resolution','row_dropout']:
        altered,labels,invalid=corruption(im,truth,name)
        assert altered.size==im.size and labels==truth
    assert invalid


def test_tracks_do_not_bridge_gaps():
    m=metadata();m['pings'].pop(4)
    features=tracks(m)['features'];lines=[x for x in features if x['geometry']['type']=='LineString']
    assert len(lines)==2


def test_xtf_truncation_rejected(tmp_path):
    p=tmp_path/'bad.xtf';p.write_bytes(b'bad')
    with pytest.raises(Exception):list(xtf_packets(p))


def test_model_modality_rejected_before_loading(tmp_path):
    p=tmp_path/'x.model.json';p.write_text(json.dumps({'id':'x','modalities':['FLS_UATD'],'status':'tested-local-inference'}))
    with pytest.raises(InputError):Registry(tmp_path).load('x','SSS_LF')
