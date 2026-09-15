import copy,json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from bluecho.engine import InputError
from bluecho.phase1.geography import tracks,timestamp,load_sidecar
from bluecho.phase1.masks import map_binary_mask,decode_binary_mask
from bluecho.phase1.contracts import image_digest,validate_result
from bluecho.phase1.reporting import export_result
from bluecho.phase1.cli import JsonDiagnostics
from test_geometry_input_quality import metadata


def test_utc_offsets_do_not_reverse_tracks():
    m=metadata();m['pings']=m['pings'][:2]
    m['pings'][0]['timestamp']='2026-01-01T05:30:00+05:30'
    m['pings'][1]['timestamp']='2026-01-01T00:00:01Z'
    assert len([r for r in tracks(m)['features'] if r['geometry']['type']=='LineString'])==1
    m['pings'][1]['timestamp']='2026-01-01T05:29:59+05:30'
    assert not [r for r in tracks(m)['features'] if r['geometry']['type']=='LineString']


def test_mask_holes_survive_encoding_rendering():
    a=np.zeros((20,20),np.uint8);a[2:18,2:18]=1;a[6:14,6:14]=0
    mask=map_binary_mask(a,(20,20),crop_xyxy=(0,0,20,20))
    assert np.array_equal(decode_binary_mask(mask),a)
    bad={**mask,'counts':[400,1]}
    with pytest.raises(ValueError,match='length'):decode_binary_mask(bad)


def test_pixel_hash_catches_same_size_wrong_image():
    a=Image.new('RGB',(30,30),'black');b=a.copy();b.putpixel((2,2),(0,0,1))
    assert image_digest(a)!=image_digest(b)
    assert image_digest(a)==image_digest(a.convert('L'))


def test_diagnostics_each_line_is_json():
    import io
    s=io.StringIO();d=JsonDiagnostics(s);d.write('library warning\rprogress');d.write(' done\n');d.flush()
    assert [json.loads(x)['message'] for x in s.getvalue().splitlines()]==['library warning','progress done']


def test_sidecar_rejects_implicit_sample_rescale(tmp_path):
    from bluecho.phase1.download import digest
    src=tmp_path/'a.png';Image.new('RGB',(100,10)).save(src);m=metadata();m.update(schema_version='1.0',source_sha256=digest(src),image_width=100,image_height=10,modality='SSS');m['pings'][0]['sample_count']=200
    side=tmp_path/'a.json';side.write_text(json.dumps(m))
    with pytest.raises(InputError,match='Sample count'):load_sidecar(side,src,100,10)


def test_mask_adapter_runs_through_shared_report(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from bluecho.phase1.engine import RecordingEngine
    from bluecho.phase1.download import digest
    source=tmp_path/'input.png';Image.new('RGB',(40,40),(25,25,25)).save(source)
    a=np.zeros((40,40),np.uint8);a[4:36,4:36]=1;a[12:28,12:28]=0
    mask=map_binary_mask(a,(40,40),crop_xyxy=(0,0,40,40))
    entry={'id':'synthetic_mask_fixture','version':'software-only','weights':{'sha256':'a'*64},'runtime':'synthetic_test','classes':{'0':'software_fixture'},'calibration':'uncalibrated','evidence_scope':'SYNTHETIC SOFTWARE TEST, not a detector','preprocessing':{'mode':'explicit_mask_mapping'},'terms':{}}
    adapter=SimpleNamespace(predict=lambda path,progress:([{'xyxy':[4,4,36,36],'score':.7,'class_id':0,'class_name':'software_fixture','mask':mask}],None))
    engine=RecordingEngine(tmp_path);monkeypatch.setattr(engine.registry,'load',lambda *args,**kwargs:(entry,adapter))
    window={'image_path':source,'metadata':None,'invalid_rows':[],'coverage':{'complete_input':True,'unassessed':[]},'modality':'SOFTWARE_FIXTURE','source_sha256':digest(source),'reference':{'file':'input.png'},'decoding':{'method':'synthetic fixture'}}
    result=engine.process_window(window,[entry['id']],tmp_path/'report');validate_result(result,Image.open(source))
    overlay=Image.open(tmp_path/'report/annotated.png');assert overlay.getpixel((20,20))==(25,25,25);assert overlay.getpixel((8,20))!=(25,25,25)
    changed=copy.deepcopy(result);changed['detections'][0]['model_sha256']='b'*64
    with pytest.raises(InputError,match='binding'):validate_result(changed)
    with pytest.raises(InputError,match='pixels'):validate_result(result,Image.new('RGB',(40,40)))
