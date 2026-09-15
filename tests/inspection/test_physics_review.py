import copy
import json
import numpy as np
import pytest
from bluecho.inspection.bottom import BottomConfig,track_bottom,compare_sides
from bluecho.inspection.geometry import position,interpolate_navigation
from bluecho.inspection.review import ReviewQueue

SHA='a'*64

def metadata(rows=4):
 return {'source_sha256':SHA,'image_width':128,'image_height':rows,'modality':'SSS','mapping':'ping_rows','flat_seabed_verified':True,'level_sensor_verified':True,'calibration_verified':True,'timestamp_alignment_verified':True,'pings':[{'row':i,'ping_index':i,'sample_count':128,'range_start':0,'range_end':128,'range_unit':'m','range_geometry':'slant','sample_direction':'near_to_far','timestamp':f'2026-01-01T00:00:0{i}+00:00','side':'starboard','heading_degrees':0,'heading_reference':'true_north','altitude':32,'altitude_unit':'m','altitude_reference':'seabed','altitude_provenance':'measured','sensor_position':{'x':0,'y':0,'crs':'EPSG:4326','reference':'sonar_sensor','valid':True}} for i in range(rows)]}

CFG=BottomConfig(max_vertical_rate_m_s=2,calibration_verified=True,water_column_verified=True,flat_seabed_verified=True,level_sensor_verified=True,support_samples=8,max_time_gap_s=2)

def test_bottom_known_spike_dropout_ambiguous():
 raw=np.zeros((4,128));raw[:,32:]=100;raw[1,12]=1000
 result=track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG)
 assert all(r['altitude_m']==32 for r in result['rows'])
 raw[2]=0
 assert track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG)['rows'][2]['altitude_m'] is None
 raw[0,80:]=300
 assert 'AMBIGUOUS_BOTTOM' in track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG)['rows'][0]['reason_codes']

def test_bottom_invalid_calibration_manual_side():
 raw=np.zeros((4,128));raw[:,32:]=100;m=metadata();m['pings'][0]['range_start']=None
 r=track_bottom(raw,m['pings'],source_sha256=SHA,config=CFG);assert r['rows'][0]['altitude_m'] is None
 r=track_bottom(raw,metadata()['pings'],source_sha256=SHA);assert all(x['altitude_m'] is None for x in r['rows'])
 with pytest.raises(ValueError):track_bottom(raw,m['pings'],source_sha256=SHA,manual={'source_sha256':'b'*64,'corrections':[]})
 p=track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG);s=copy.deepcopy(p)
 for row in p['rows']:row['side']='port'
 for row in s['rows']:row['first_return_range_m']+=5
 assert compare_sides(p,s,tolerance_m=2)==[0,1,2,3]
 assert all(row['altitude_m'] is None for row in p['rows'])

def test_position_and_uncertainty():
 m=metadata();a=position(40,0,m);assert a['coordinates'][0]>0
 m['pings'][0]['side']='port';assert position(40,0,m)['coordinates'][0]<0
 assert position(20,0,m)['coordinates'] is None
 m['pings'][0]['error_bounds']={'navigation_m':1,'heading_degrees':1,'altitude_m':1,'slant_range_m':1}
 assert position(40,0,m)['uncertainty']['radius_m']>1
 assert 'NEAR_NADIR_UNCERTAINTY_DOMAIN' in position(33,0,m)['reason_codes']
 m['modality']='FLS_ARIS';assert position(40,0,m)['coordinates'] is None
 m=metadata();m['pings'][0]['sensor_position']['reference']='vessel';assert position(40,0,m)['coordinates'] is None
 m['pings'][0]['sensor_offset']={'verified':True,'forward_m':-10,'starboard_m':0};assert position(40,0,m)['coordinates'][1]<0
 m['pings'][0]['sensor_position']['crs']='bad';assert position(40,0,m)['coordinates'] is None

def test_heading_gap():
 m=metadata();a,b=m['pings'][:2];a['heading_degrees']=359;b['heading_degrees']=1
 assert interpolate_navigation(a,b,'2026-01-01T00:00:00.5Z',max_gap_s=2)['heading_degrees']==0
 with pytest.raises(ValueError):interpolate_navigation(a,b,'2026-01-01T00:00:00.5Z',max_gap_s=.1)

def test_review_immutable_roundtrip_split(tmp_path):
 item={'candidate_id':'one','source_sha256':SHA,'box_xyxy_pixels':[1,2,3,4],'image_dimensions':{'width':20,'height':20}}
 q=ReviewQueue(tmp_path/'a.db');q.add(item,'recording-A');q.annotate('one',action='corrected',label='bottle',box=[2,3,4,5],reviewer='software-test-fixture')
 b=q.export();r=ReviewQueue(tmp_path/'b.db');r.import_bundle(b);assert r.export()==b
 assert r.export()['items'][0]['original_prediction']==item
 assert not r.development_manifest({'heldout_source_sha256':[],'heldout_source_groups':['recording-A'],'development_source_groups':['recording-A']})['examples']
 with pytest.raises(ValueError):q.add({**item,'box_xyxy_pixels':[0,0,1,1]},'recording-A')
 with pytest.raises(ValueError):q.annotate('one',action='corrected',label='bottle',box=[0,0,999,999])
 q.close();r.close()

def test_manual_trace_is_window_bound():
 raw=np.zeros((4,128));raw[:,32:]=100
 r=track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG)
 correction={'source_sha256':SHA,'raw_array_sha256':r['raw_array_sha256'],'reviewer':'synthetic fixture','corrections':[{'row':0,'sample':33}]}
 revised=track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG,manual=correction)
 assert revised['rows'][0]['altitude_provenance']=='manually_supplied'
 raw[0,0]=1
 with pytest.raises(ValueError):track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG,manual=correction)

def test_review_import_atomic(tmp_path):
 q=ReviewQueue(tmp_path/'review.db');bundle={'schema_version':'1.0','items':[{'source_group':'a','original_prediction':{'candidate_id':'new','source_sha256':SHA}}],'events':[{'event_id':'bad','item':'new','action':'false_alert','reviewer':None,'label':None,'box_xyxy_pixels':None,'timestamp':'2026-01-01T00:00:00Z','annotation_version':1}]}
 with pytest.raises(ValueError):q.import_bundle(bundle)
 assert q.export()['items']==[];q.close()

def test_uncertain_metadata_never_returns_sensor_position():
 assert position(50,0,None)['coordinates'] is None
 m=metadata();m['flat_seabed_verified']=False
 assert position(50,0,m)['coordinates'] is None
 m=metadata();m['pings'][0]['altitude_provenance']='estimated'
 assert position(50,0,m)['coordinates'] is None

def test_motion_jump_and_gap():
 raw=np.zeros((4,128));raw[:,32:]=100;raw[1]=0;raw[1,80:]=100
 trace=track_bottom(raw,metadata()['pings'],source_sha256=SHA,config=CFG)
 assert 'BOTTOM_CONTINUITY_VIOLATION' in trace['rows'][1]['reason_codes']
 m=metadata();m['pings'][1]['timestamp']='2026-01-01T00:01:00Z'
 assert 'TIMESTAMP_GAP' in track_bottom(raw,m['pings'],source_sha256=SHA,config=CFG)['rows'][1]['reason_codes']

def test_unresolved_time_delay():
 raw=np.zeros((4,128));raw[:,32:]=100;m=metadata();m['pings'][0]['time_delay_seconds']=.1
 assert 'INVALID_RANGE_CALIBRATION' in track_bottom(raw,m['pings'],source_sha256=SHA,config=CFG)['rows'][0]['reason_codes']

def test_aligned_observations_require_known_correspondence():
 from bluecho.inspection.supervisor import associate_aligned
 a={'candidate_id':'a','source_sha256':SHA,'native_label':'pipeline','original_prediction':{'source_reference':{'window':0},'modality':'SSS','box_xyxy_pixels':[0,0,100,100]}}
 b=copy.deepcopy(a);b['candidate_id']='b';b['native_label']='wreck';b['original_prediction']['source_reference']={'window':1}
 reports=[{'candidates':[a,b]}];assert associate_aligned(reports,{})==[]
 mapping={SHA+':'+json.dumps(c['original_prediction']['source_reference'],sort_keys=True):{'verified':True,'kind':'translation','frame_id':'known-pixel-frame','dx':0,'dy':0,'max_error_pixels':1} for c in (a,b)}
 r=associate_aligned(reports,mapping);assert r[0]['reason_codes']==['INCONSISTENT_ALIGNED_OBSERVATIONS'] and not r[0]['independent_detections']
 b['original_prediction']['modality']='FLS_ARIS';assert associate_aligned(reports,mapping)==[]
