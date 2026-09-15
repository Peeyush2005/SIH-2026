import hashlib,io,json,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from bluecho.phase1.download import download,atomic_json
from bluecho.phase1.masks import map_binary_mask
from bluecho.phase1.supervisor import charge,initialize

class Response(io.BytesIO):
    def __init__(self,data,status,headers):super().__init__(data);self.status=status;self.headers=headers

def test_range_resume_and_ignored_range_restart(tmp_path):
    data=b'PK-real-test-payload';sha=hashlib.sha256(data).hexdigest()
    for status in [200,206]:
        out=tmp_path/str(status);out.mkdir();spec={'filename':'m.pt','url':'https://example.invalid/pinned/m.pt','bytes':len(data),'sha256':sha}
        (out/'m.pt.part').write_bytes(data[:4]);atomic_json(out/'m.pt.part.json',spec)
        body=data if status==200 else data[4:];headers={'Content-Length':str(len(body))}
        if status==206:headers['Content-Range']=f'bytes 4-{len(data)-1}/{len(data)}'
        with patch('urllib.request.urlopen',return_value=Response(body,status,headers)):
            r=download(spec,out,reserve=0)
        assert r['sha256']==sha and (out/'m.pt').read_bytes()==data
        assert download(spec,out,reserve=0)['status']=='REUSED_VERIFIED'

def test_bad_response_and_budget_rejected(tmp_path):
    data=b'<html>not a model</html>';spec={'filename':'x.pt','url':'https://example.invalid/x','bytes':len(data)}
    with patch('urllib.request.urlopen',return_value=Response(data,200,{'Content-Length':str(len(data))})):
        with pytest.raises(ValueError,match='HTML'):download(spec,tmp_path,reserve=0,retries=1)
    with pytest.raises(ValueError,match='ceiling'):download({**spec,'bytes':1000},tmp_path,ceiling=100,reserve=0)
    with pytest.raises(ValueError,match='basename'):download({**spec,'filename':'../x'},tmp_path,reserve=0)

def test_mask_inverse_padding_resize_and_rle():
    tile=np.zeros((8,8),np.uint8);tile[2:6,2:6]=1
    result=map_binary_mask(tile,(30,20),crop_xyxy=(10,5,18,13),padding_ltrb=(2,2,2,2))
    assert result['foreground_pixels']==64 and sum(result['counts'])==600
    assert result['coordinate_space']=='original_pixels'
    a=np.zeros(600,np.uint8);start=0
    for i,n in enumerate(result['counts']):a[start:start+n]=i%2;start+=n
    a=a.reshape(20,30);assert a[5:13,10:18].all() and a.sum()==64

def test_budget_survives_reload_and_frozen_queue(tmp_path):
    atomic_json(tmp_path/'queue.json',{'training_ceiling_seconds':100,'preflight_training_seconds':12,'jobs':[]})
    plan,s=initialize(tmp_path);assert s['spent_seconds']==12
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip() if Path('/proc/sys/kernel/random/boot_id').exists() else 'system-boot'
    s['jobs']['x']={'spent_seconds':2};s['active']={'job':'x','last_monotonic':time.monotonic()-3,'last_wall':time.time()-3,'boot_id':boot_id}
    charge(s);assert 15<=s['spent_seconds']<16
    atomic_json(tmp_path/'ledger.json',s);_,reloaded=initialize(tmp_path);assert reloaded['spent_seconds']==s['spent_seconds']
    atomic_json(tmp_path/'queue.json',{'training_ceiling_seconds':101,'jobs':[]})
    with pytest.raises(ValueError,match='binding changed'):initialize(tmp_path)

def test_atomic_model_save_preserves_callback_success(tmp_path):
    from types import SimpleNamespace
    from bluecho.phase1.training import atomic_model_save
    trainer=SimpleNamespace(last=tmp_path/'last.pt',best=tmp_path/'best.pt')
    def save():
        trainer.last.write_bytes(b'optimizer-bearing-snapshot');trainer.best.write_bytes(b'best');return True
    callbacks=[]
    if atomic_model_save(trainer,save):callbacks.append('on_model_save')
    assert callbacks==['on_model_save']
    assert trainer.last.name=='last.pt' and trainer.last.read_bytes()==b'optimizer-bearing-snapshot'
    assert not list(tmp_path.glob('*.pending'))
