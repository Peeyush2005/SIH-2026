"""Synthetic software checks. These are not detector accuracy measurements."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import time
from importlib.resources import files
import pytest
import jsonschema
from PIL import Image
from fastapi.testclient import TestClient
from bluecho.engine import Engine, InputError, ModelError, PREPROCESSING_VERSION, read_image, local_path
from bluecho.geometry import crops, render_tile, map_box, merge_nms
from bluecho.export import export, geojson
from bluecho.api import create_app


def fake_engine(manifest=None,device='cpu'):
    engine=Engine.__new__(Engine)
    engine.manifest={'schema_version':'1.0.0','modality':'SSS_LF','model_version':'SYNTHETIC_TEST_FIXTURE',
        'classes':{'0':'Pipeline'},'preprocessing_version':PREPROCESSING_VERSION}
    engine.device=device;engine.backend='native';engine.model_hash='f'*64
    engine.thresholds={'0':.5};engine.protocol={'source_nms_iou':.5}
    engine.tile=lambda image:[{'xyxy':[10.,10.,30.,40.],'score':.75,'class_id':0,'class_name':'Pipeline'}]
    return engine


def test_coordinate_roundtrip_and_padding():
    windows=crops(2500,500)
    assert windows==[(0,0,640,500),(480,0,1120,500),(960,0,1600,500),(1440,0,2080,500),(1860,0,2500,500)]
    original=[490.,15.,1100.,490.];crop=windows[1]
    local=[original[0]-crop[0],original[1]-crop[1],original[2]-crop[0],original[3]-crop[1]]
    assert map_box(local,crop)==original
    assert map_box([0,0,640,640],(0,0,100,200))==[0,0,100,200]
    image=render_tile(Image.new('L',(100,200),37),(0,0,100,200))
    assert image.size==(640,640) and image.getpixel((99,199))==(37,37,37) and image.getpixel((100,200))==(114,114,114)


def test_duplicate_merging_preserves_classes_and_segments():
    boxes=[{'class_id':0,'score':.9,'xyxy':[0,0,100,20]},
           {'class_id':0,'score':.8,'xyxy':[1,0,101,20]},
           {'class_id':0,'score':.7,'xyxy':[100,0,200,20]},
           {'class_id':1,'score':.6,'xyxy':[0,0,100,20]}]
    assert [b['score'] for b in merge_nms(boxes,.5)]==[.9,.7,.6]
    assert merge_nms([],.5)==[]


def test_schema_empty_and_missing_metadata(tmp_path):
    image=tmp_path/'sample.png';Image.new('L',(100,100),0).save(image)
    engine=fake_engine();result=engine.predict(image,modality='SSS_LF')
    schema=json.loads(files('bluecho').joinpath('output_schema.json').read_text())
    jsonschema.validate(result,schema)
    assert result['detections'][0]['coordinates'] is None
    assert result['detections'][0]['material'] is None
    engine.tile=lambda image:[]
    empty=engine.predict(image,modality='SSS_LF');jsonschema.validate(empty,schema)
    export(empty,tmp_path/'empty',source=image)
    assert list(csv.DictReader((tmp_path/'empty/predictions.csv').open()))==[]
    assert (tmp_path/'empty/annotated.png').is_file()
    with pytest.raises(InputError):geojson(result)
    with pytest.raises(InputError):engine.predict(image,modality='FLS_ARIS')


def test_invalid_input_and_model_paths(tmp_path):
    import ultralytics.utils.patches  # Real runtime monkey-patches PIL.Image.open.
    bad=tmp_path/'bad.png';bad.write_bytes(b'not an image')
    with pytest.raises(InputError):read_image(bad)
    high=tmp_path/'16bit.tif';Image.new('I;16',(10,10),4).save(high)
    with pytest.raises(InputError):read_image(high)
    with pytest.raises(ModelError):local_path(tmp_path,'../outside.pt')
    target=tmp_path/'weights.pt';target.write_bytes(b'software fixture')
    m={'schema_version':'1.0.0','modality':'SSS_LF','classes':{'0':'Pipeline'},
       'preprocessing':{'tile_size':640,'stride':480,'padding_rgb':[114,114,114],'mode':'tiles','scale':1.0,'intensity':'Preserve source uint8 RGB /255; no stretching/filtering'},
       'preprocessing_version':PREPROCESSING_VERSION,'inference':{},'thresholds':{'0':.5},
       'native':{'path':'weights.pt','sha256':'0'*64}}
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(m))
    with pytest.raises(ModelError,match='checksum'):Engine(manifest)
    m['classes']={'0':'plastic'};manifest.write_text(json.dumps(m))
    with pytest.raises(ModelError,match='supports only'):Engine(manifest)


def wait_job(client,job):
    for _ in range(100):
        value=client.get(f'/jobs/{job}').json()
        if value['state'] in ('completed','failed'):return value
        time.sleep(.02)
    pytest.fail('Job did not finish')


def test_api_engine_agreement_review_persistence_and_paths(tmp_path):
    image=tmp_path/'sample.png';Image.new('L',(100,100),0).save(image)
    root=tmp_path/'jobs';factory_calls=[]
    def factory(*args,**kwargs):factory_calls.append(1);return fake_engine()
    with TestClient(create_app('synthetic',root,engine_factory=factory)) as client:
        assert client.get('/health').json()['model_status']=='ready'
        assert client.post('/jobs',data={'modality':'FLS_ARIS'},files={'file':('a.png',image.read_bytes())}).status_code==422
        assert client.post('/jobs',data={'modality':'SSS_LF'},files={'file':('a.png',b'bad')}).status_code==422
        response=client.post('/jobs',data={'modality':'SSS_LF'},files={'file':('../../sample.png',image.read_bytes())})
        assert response.status_code==202;job=response.json()['job_id'];assert wait_job(client,job)['state']=='completed'
        result=client.get(f'/jobs/{job}/results').json()['prediction']
        expected=fake_engine().predict(image,modality='SSS_LF')
        result.pop('end_to_end_seconds');expected.pop('end_to_end_seconds');assert result==expected
        original=(root/job/'result/predictions.json').read_bytes();detection=result['detections'][0]['detection_id']
        assert client.put(f'/jobs/{job}/review/{detection}',json={'status':'relabelled','label':'human alternative'}).status_code==200
        assert (root/job/'result/predictions.json').read_bytes()==original
        assert client.get(f'/jobs/{job}/evidence/annotated.png').status_code==200
        assert client.get(f'/jobs/{job}/evidence/%2E%2E/source.png').status_code==404
        assert client.get(f'/jobs/{job}/export/csv').status_code==200
        assert client.get('/jobs/not-an-id').status_code==404
        assert len(factory_calls)==1
    with TestClient(create_app('synthetic',root,engine_factory=factory)) as client:
        assert client.get(f'/jobs/{job}/results').json()['reviews'][detection]['label']=='human alternative'


def test_api_failed_job(tmp_path):
    image=tmp_path/'sample.png';Image.new('L',(10,10),0).save(image)
    engine=fake_engine()
    def fail(*args,**kwargs):raise RuntimeError('SYNTHETIC injected model failure')
    engine.predict=fail
    with TestClient(create_app('synthetic',tmp_path/'jobs',engine_factory=lambda *a,**k:engine)) as client:
        job=client.post('/jobs',data={'modality':'SSS_LF'},files={'file':('a.png',image.read_bytes())}).json()['job_id']
        assert wait_job(client,job)['state']=='failed'
        assert client.get(f'/jobs/{job}/results').status_code==409


def test_api_missing_model(tmp_path):
    with TestClient(create_app(tmp_path/'missing.json',tmp_path/'jobs')) as client:
        assert client.get('/health').json()['model_status']=='failed'
        assert client.get('/capabilities').json()['model'] is None
