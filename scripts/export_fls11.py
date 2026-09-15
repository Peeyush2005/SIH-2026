import argparse
from pathlib import Path
import torch,importlib,json,hashlib
from ultralytics.nn.tasks import DetectionModel
parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,required=True);r=parser.parse_args().artifacts;assert hashlib.sha256((r/'fls11-best.pt').read_bytes()).hexdigest()=='b6d82043f04c24ab66637f04cea0ffc2263a57cea9b01c0a7e15d55149274cff'
names=['torch.nn.modules.activation.SiLU','torch.nn.modules.batchnorm.BatchNorm2d','torch.nn.modules.container.ModuleList','torch.nn.modules.container.Sequential','torch.nn.modules.conv.Conv2d','torch.nn.modules.linear.Identity','torch.nn.modules.pooling.MaxPool2d','torch.nn.modules.upsampling.Upsample','ultralytics.nn.modules.block.Attention','ultralytics.nn.modules.block.Bottleneck','ultralytics.nn.modules.block.C2PSA','ultralytics.nn.modules.block.C3k','ultralytics.nn.modules.block.C3k2','ultralytics.nn.modules.block.DFL','ultralytics.nn.modules.block.PSABlock','ultralytics.nn.modules.block.SPPF','ultralytics.nn.modules.conv.Concat','ultralytics.nn.modules.conv.Conv','ultralytics.nn.modules.conv.DWConv','ultralytics.nn.modules.head.Detect','ultralytics.nn.tasks.DetectionModel']
allow=[set]+[getattr(importlib.import_module(n.rsplit('.',1)[0]),n.rsplit('.',1)[1]) for n in names]
torch.serialization.add_safe_globals(allow)
ck=torch.load(r/'fls11-best.pt',map_location='cpu',weights_only=True)
old=ck['model'];print('classes',old.names,'epoch',ck.get('epoch'));assert len(old.names)==11
for module in old.modules():
 assert not module._forward_hooks and not module._forward_pre_hooks and not module._state_dict_hooks
state=old.state_dict();fresh=DetectionModel('yolo11n.yaml',nc=11,verbose=False);fresh.load_state_dict(state,strict=True);fresh.names=old.names;fresh=fresh.float().eval();fresh.fuse(verbose=False)
for mod in fresh.modules():
 if mod.__class__.__name__=='Detect':mod.export=True;mod.format='onnx';mod.dynamic=False
x=torch.zeros(1,3,640,640);torch.set_num_threads(4)
with torch.inference_mode(): pred=fresh(x);print('output',pred.shape);torch.onnx.export(fresh,x,str(r/'fls11.onnx'),opset_version=17,input_names=['images'],output_names=['output0'],do_constant_folding=True)
(r/'fls11-export.json').write_text(json.dumps({'source_sha256':hashlib.sha256((r/'fls11-best.pt').read_bytes()).hexdigest(),'onnx_sha256':hashlib.sha256((r/'fls11.onnx').read_bytes()).hexdigest(),'classes':old.names,'torch':torch.__version__,'load':'weights_only explicit installed-class allowlist; reconstructed fresh model with strict state dict; no third-party Python executed'},indent=2),encoding='utf-8');print('EXPORTED')

import cv2,numpy as np,onnxruntime as ort
from ultralytics.utils.nms import non_max_suppression
session=ort.InferenceSession(str(r/'fls11.onnx'),providers=['CPUExecutionProvider']);rows=[]
for image in sorted(r.glob('fls-sample-*.png')):
 rgb=cv2.cvtColor(cv2.imread(str(image)),cv2.COLOR_BGR2RGB);h,w=rgb.shape[:2];ratio=min(640/w,640/h);nw,nh=round(w*ratio),round(h*ratio);left,top=(640-nw)//2,(640-nh)//2;canvas=np.full((640,640,3),114,dtype=np.uint8);canvas[top:top+nh,left:left+nw]=cv2.resize(rgb,(nw,nh));x=np.ascontiguousarray(canvas.transpose(2,0,1)[None],dtype=np.float32)/255
 with torch.inference_mode(): native=fresh(torch.from_numpy(x)).numpy()
 exported=session.run(None,{'images':x})[0];delta=float(np.max(np.abs(native-exported)));assert delta<.02
 detections=non_max_suppression(torch.from_numpy(exported.copy()),conf_thres=.25,iou_thres=.5,nc=11)[0].numpy();records=[]
 for d in detections:
  b=d[:4].astype(float);b[[0,2]]=(b[[0,2]]-left)/ratio;b[[1,3]]=(b[[1,3]]-top)/ratio;b[[0,2]]=np.clip(b[[0,2]],0,w);b[[1,3]]=np.clip(b[[1,3]],0,h);records.append({'class':old.names[int(d[5])],'score':float(d[4]),'box':b.tolist()})
 rows.append({'source':image.name,'size':[w,h],'max_raw_delta':delta,'detections':records,'labels':image.with_suffix('.txt').read_text()});print(image.name,records)
(r/'fls11-parity.json').write_text(json.dumps({'scope':'3 public source test images; source training overlap and split independence unaudited; runtime compatibility only','rows':rows},indent=2),encoding='utf-8')
