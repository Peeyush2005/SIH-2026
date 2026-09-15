import json,os,resource,zipfile,pickletools
resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(90,90))
os.environ.update(YOLO_OFFLINE='true',YOLO_AUTOINSTALL='false',OMP_NUM_THREADS='2')
import torch
from torch import nn
from ultralytics.nn import modules,tasks
allowed_names={'__builtin__ set','collections OrderedDict','torch FloatStorage','torch HalfStorage','torch LongStorage','torch Size','torch._utils _rebuild_parameter','torch._utils _rebuild_tensor_v2','torch.nn.modules.activation SiLU','torch.nn.modules.batchnorm BatchNorm2d','torch.nn.modules.container ModuleList','torch.nn.modules.container Sequential','torch.nn.modules.conv Conv2d','torch.nn.modules.linear Identity','torch.nn.modules.pooling MaxPool2d','torch.nn.modules.upsampling Upsample','ultralytics.nn.modules.block Bottleneck','ultralytics.nn.modules.block C2f','ultralytics.nn.modules.block DFL','ultralytics.nn.modules.block SPPF','ultralytics.nn.modules.conv Concat','ultralytics.nn.modules.conv Conv','ultralytics.nn.modules.head Detect','ultralytics.nn.tasks DetectionModel'}
with zipfile.ZipFile('/input.pt') as z:
 data=z.read(next(n for n in z.namelist() if n.endswith('data.pkl')))
 names={arg for op,arg,pos in pickletools.genops(data) if op.name=='GLOBAL'}
 assert names <= allowed_names, names-allowed_names
 assert all(op.name!='STACK_GLOBAL' for op,arg,pos in pickletools.genops(data))
allowed=[set,nn.SiLU,nn.BatchNorm2d,nn.ModuleList,nn.Sequential,nn.Conv2d,nn.Identity,nn.MaxPool2d,nn.Upsample,modules.Bottleneck,modules.C2f,modules.DFL,modules.SPPF,modules.Concat,modules.Conv,modules.Detect,tasks.DetectionModel]
torch.serialization.add_safe_globals(allowed)
c=torch.load('/input.pt',map_location='cpu',weights_only=True)
m=c['model'].float().eval();names=m.names
expected={0:'ball',1:'circle cage',2:'cube',3:'cylinder',4:'human body',5:'metal bucket',6:'plane',7:'rov',8:'square cage',9:'tyre'}
assert names==expected,(names,expected)
state={k:v.detach().cpu() for k,v in m.state_dict().items()}
assert all(torch.isfinite(v).all() for v in state.values())
# Reconstruct only an installed, known architecture; never trust embedded YAML modules.
n=tasks.DetectionModel('yolov8n.yaml',nc=10,verbose=False)
n.load_state_dict(state,strict=True)
torch.save({'state_dict':state,'names':names,'architecture':'yolov8n','nc':10},'/output/uatd-safe-state.pt')
json.dump({'status':'PASS','weights_only':True,'network':'unshared','filesystem':'user home and drives hidden; output directory only writable persistent location','globals':sorted(names for names in allowed_names),'classes':expected,'embedded_yaml':m.yaml,'torch':torch.__version__},open('/output/uatd-restricted-load.json','w'),indent=2)
print('SAFE_STATE_CONVERSION_PASS')
