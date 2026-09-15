import json,copy,csv
import pytest
from PIL import Image
from bluecho.phase1.geography import geotag_box,position_pixel,load_sidecar
from bluecho.inspection.geometry import position,interpolate_navigation
from bluecho.phase1.download import digest

def affine(**kw):return {'mapping':'affine','crs':'EPSG:3857','transform':[2,1,0,1,-2,0],**kw}
def ping():
 return {'modality':'SSS','mapping':'ping_rows','calibration_verified':True,'timestamp_alignment_verified':True,'flat_seabed_verified':True,'level_sensor_verified':True,'pings':[{'row':0,'ping_index':12,'channel':1,'timestamp':'2026-01-01T00:00:00Z','heading_degrees':360,'heading_reference':'true_north','sample_count':100,'range_start':0,'range_end':100,'range_unit':'m','range_geometry':'slant','sample_direction':'near_to_far','side':'starboard','altitude':30,'altitude_unit':'m','altitude_reference':'seabed','altitude_provenance':'measured','sensor_position':{'x':0,'y':0,'crs':'EPSG:4326','reference':'auv_sensor','valid':True}}]}

def test_rotated_affine_analytic_and_pixel_center():
 from math import pi,atan,exp
 x,y=10,20;lon=40/6378137*180/pi;lat=(2*atan(exp(-30/6378137))-pi/2)*180/pi
 assert position_pixel(x,y,affine())[0]==pytest.approx([lon,lat],abs=1e-10)
 assert position_pixel(10.5,20.5,affine(pixel_convention='pixel_center'))[0]==pytest.approx([lon,lat])
 box=geotag_box([0,0,10,10],affine());assert len(box['geographic_footprint'])==17
 assert box['metric_dimensions']['width_m']==pytest.approx(22.36,rel=.01)
 assert position_pixel(1,1,affine(pixel_convention='unknown'))[0] is None

def test_affine_bounds_antimeridian_singular_and_unknown():
 m={'mapping':'affine','crs':'EPSG:4326','transform':[.1,0,179,0,.1,0]}
 assert geotag_box([0,0,20,2],m)['geographic_footprint'] is None
 assert position_pixel(1,1,affine(transform=[0,0,0,0,0,0]))[0] is None
 assert position_pixel(1,1,affine(crs='bad'))[0] is None
 r=geotag_box([0,0,10,10],affine(horizontal_error_bound_m=3));assert r['uncertainty']['radius_m']==3

def test_slant_analytic_40m_and_ground_no_double_conversion():
 from pyproj import Geod
 m=ping();p=position(50,0,m);assert Geod(ellps='WGS84').inv(0,0,*p['coordinates'])[2]==pytest.approx(40,abs=1e-6)
 m['pings'][0].update(range_geometry='ground',altitude=None);m['ground_range_verified']=True
 assert Geod(ellps='WGS84').inv(0,0,*position(50,0,m)['coordinates'])[2]==pytest.approx(50,abs=1e-6)
 m['modality']='FLS_UATD';assert position(50,0,m)['coordinates'] is None

def test_raw_blockers_and_near_nadir():
 for field in ['calibration_verified','timestamp_alignment_verified','flat_seabed_verified','level_sensor_verified']:
  m=ping();m[field]=False;assert position(50,0,m)['coordinates'] is None
 for value in [None,float('nan'),-1,0]:
  m=ping();m['pings'][0]['altitude']=value;assert position(50,0,m)['coordinates'] is None
 m=ping();m['pings'][0]['heading_degrees']=99999;assert position(50,0,m)['coordinates'] is None
 m=ping();m['pings'][0]['error_bounds']={'navigation_m':1,'heading_degrees':1,'altitude_m':1,'slant_range_m':1}
 assert 'NEAR_NADIR_UNCERTAINTY_DOMAIN' in position(31,0,m)['reason_codes']
 assert position(20,0,m)['coordinates'] is None

def test_source_dimension_mismatch(tmp_path):
 p=tmp_path/'image.png';Image.new('RGB',(100,10)).save(p)
 m=affine(schema_version='1.0',source_sha256=digest(p),image_width=99,image_height=10,modality='SSS');f=tmp_path/'meta.json';f.write_text(json.dumps(m))
 with pytest.raises(ValueError):load_sidecar(f,p,100,10)

def test_projected_feet_conversion():
 import math
 m={'mapping':'affine','crs':'+proj=merc +a=6378137 +b=6378137 +units=ft +no_defs','transform':[1,0,0,0,1,0]}
 assert position_pixel(100,0,m)[0][0]==pytest.approx(30.48/6378137*180/math.pi,abs=1e-10)

def test_saved_geotag_exports_keep_unlocated_and_original(tmp_path,monkeypatch):
 from types import SimpleNamespace
 from bluecho.phase1.engine import RecordingEngine
 from bluecho.geotag import geotag_saved
 source=tmp_path/'synthetic.png';Image.new('RGB',(40,40),(30,30,30)).save(source)
 entry={'id':'synthetic','version':'fixture','weights':{'sha256':'a'*64},'runtime':'fixture','classes':{'0':'fixture'},'evidence_scope':'SYNTHETIC TEST ONLY','calibration':'uncalibrated','preprocessing':{},'terms':{}}
 adapter=SimpleNamespace(predict=lambda *a,**k:([{'xyxy':[4,4,30,30],'score':.8,'class_id':0,'class_name':'fixture'}],None))
 engine=RecordingEngine(tmp_path/'registry');monkeypatch.setattr(engine.registry,'load',lambda *a,**k:(entry,adapter))
 result=engine.predict(source,tmp_path/'unlocated',model_ids=['synthetic'],modality='SSS')
 features=json.loads((tmp_path/'unlocated/detections.geojson').read_text())['features'];assert len(features)==1 and features[0]['geometry'] is None
 m=affine(schema_version='1.0',source_sha256=digest(source),image_width=40,image_height=40,modality='SSS',input_provenance='synthetic_reference');sidecar=tmp_path/'metadata.json';sidecar.write_text(json.dumps(m))
 located=geotag_saved(tmp_path/'unlocated/results.json',source,sidecar,tmp_path/'located')
 original=result['detections'][0];c=located['detections'][0]
 assert c['coordinates'] is not None and c['candidate_id']==original['candidate_id'] and c['raw_score']==original['raw_score'] and c['box_xyxy_pixels']==original['box_xyxy_pixels']
 row=list(csv.DictReader((tmp_path/'located/detections.csv').open()))[0];feature=json.loads((tmp_path/'located/detections.geojson').read_text())['features'][0]
 assert [float(row['longitude']),float(row['latitude'])]==feature['geometry']['coordinates']==c['coordinates']
 assert json.loads((tmp_path/'located/original_predictions.json').read_text())['detections'][0]['coordinates'] is None


def test_ground_range_error_bounds_without_altitude():
 m=ping();m['ground_range_verified']=True;m['pings'][0].update(range_geometry='ground',altitude=None,error_bounds={'navigation_m':2,'heading_degrees':0,'ground_range_m':3})
 assert position(50,0,m)['uncertainty']['radius_m']==5
