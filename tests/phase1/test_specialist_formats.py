"""Synthetic format contracts; accuracy checks live in the model evidence report."""
from types import SimpleNamespace
import numpy as np
from PIL import Image
import pytest
from bluecho.engine import ModelError
from bluecho.phase1.adapters import Specialist


def adapter(output):
    model=Specialist.__new__(Specialist)
    model.entry={'preprocessing':{'output_layout':'end2end','color_order':'RGB'}}
    model.runtime='onnx';model.input='images';model.names={'0':'Crab-Pot'}
    model.session=SimpleNamespace(run=lambda *args: [np.asarray(output,dtype=np.float32)])
    return model


def test_end_to_end_xyxy_keeps_class_and_filters_duplicates():
    model=adapter([[[2,3,20,30,.9,0],[2,3,20,30,.8,0],[30,30,35,35,.1,0]]])
    found=model.tile(Image.new('RGB',(640,640)),.25)
    assert len(found)==1
    assert found[0]['xyxy']==[2,3,20,30]
    assert found[0]['class_name']=='Crab-Pot'


@pytest.mark.parametrize('output', [
    [[[2,3,20,30,.9,1]]],
    [[[2,3,20,30,.9,.5]]],
    [[[2,3,20,30,float('nan'),0]]],
    [[[2,3,20,30,.9]]],
])
def test_rejects_bad_end_to_end_contract(output):
    with pytest.raises(ModelError):
        adapter(output).tile(Image.new('RGB',(640,640)),.25)


def test_small_bgr_letterbox_restores_original_geometry(tmp_path):
    path=tmp_path/'input.png';Image.new('RGB',(200,100),(20,40,80)).save(path)
    model=adapter([[[0,64,256,192,.9,0]]])
    model.entry={'threshold':.25,'preprocessing':{'mode':'letterbox256','size':256,'color_order':'BGR','output_layout':'end2end','max_aspect_ratio':4}}
    def run(_, feed):
        x=feed['images']
        assert x.shape==(1,3,256,256)
        assert np.allclose(x[0,:,128,128],[80/255,40/255,20/255])
        assert np.allclose(x[0,:,0,0],114/255)
        return [np.asarray([[[0,64,256,192,.9,0]]],dtype=np.float32)]
    model.session=SimpleNamespace(run=run)
    found,_=model.predict(path)
    assert found[0]['xyxy']==[0,0,200,100]
