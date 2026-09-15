import json
from importlib.resources import files
import numpy as np
import pytest
from PIL import Image
from bluecho.verifier import CandidateVerifier,extract_features,FEATURES,GENERIC

def verifier():return CandidateVerifier(files('bluecho').joinpath('experiment/verifier.json'))
def test_learned_parameters_and_save_load(tmp_path):
 v=verifier();assert np.count_nonzero(v.manifest['models']['generic']['coef'])>0
 path=tmp_path/'model.json';path.write_text(json.dumps(v.manifest));other=CandidateVerifier(path)
 image=Image.fromarray(np.tile(np.arange(128,dtype=np.uint8),(128,1)));boxes=[{'xyxy':[20,20,50,70],'score':.7}]
 assert v.score(image,boxes,range_axis='x')==other.score(image,boxes,range_axis='x')
 assert len(v.manifest['models']['acoustic']['coef'])==len(FEATURES)

def test_missing_range_and_edge_fallback():
 v=verifier();im=Image.new('RGB',(100,100));boxes=[{'xyxy':[20,20,50,70],'score':.7}]
 a=v.score(im,boxes);b=v.score(im,boxes,family='generic')
 assert a[0]['verifier_score']==b[0]['verifier_score'] and a[0]['feature_fallback']
 edge=[{'xyxy':[0,20,50,70],'score':.7}];assert v.score(im,edge,range_axis='x')[0]['feature_fallback']

def test_wrong_modality_and_invalid_box():
 v=verifier();im=Image.new('RGB',(100,100));boxes=[{'xyxy':[20,20,50,70],'score':.7}]
 with pytest.raises(ValueError):v.score(im,boxes,modality='FLS_ARIS')
 with pytest.raises(ValueError):extract_features(im,[{'xyxy':[0,0,500,500],'score':.7}])
 assert v.score(im,[])==[]

def test_no_annotation_or_identifier_features():
 assert not any(any(word in name for word in ['filename','truth','split','label','review']) for name in FEATURES)
 assert verifier().manifest['training']['independent_groups']==1

def test_zero_match_localization_is_unavailable():
 from bluecho.verifier import metric_differences
 baseline={'tp':179,'fp':129,'fn':186,'mAP50_95':.18,'mean_matched_iou':.72}
 empty={'tp':0,'fp':0,'fn':365,'mAP50_95':.14,'mean_matched_iou':None}
 result=metric_differences(empty,baseline)
 assert result['tp']==-179 and result['mean_matched_iou'] is None
