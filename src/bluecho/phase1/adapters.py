"""Specialist adapters around the existing geometry and Ultralytics runtimes."""
from collections import OrderedDict
from pathlib import Path
import gc
import json
import time
import numpy as np
from PIL import Image
from bluecho.engine import Engine, InputError, ModelError, read_image
from bluecho.geometry import crops, render_tile, map_box, merge_nms
from .download import digest


def lee_clahe(rgb):
    """Pinned DRISHTI Lee(7) + CLAHE(3,8x8) arithmetic, no range correction."""
    import cv2
    gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
    x = gray.astype(np.float64)
    mean = cv2.blur(x, (7,7))
    var = np.maximum(cv2.blur(x*x,(7,7))-mean*mean,0)
    overall = np.var(x)
    filtered = gray if overall == 0 else np.clip(mean+var/(var+overall+1e-10)*(x-mean),0,255).astype(np.uint8)
    return Image.fromarray(cv2.createCLAHE(clipLimit=3.0,tileGridSize=(8,8)).apply(filtered)).convert('RGB')


class Specialist:
    def __init__(self, entry, root, device='cpu'):
        self.entry = entry
        self.device = 'cuda:'+device if str(device).isdigit() else str(device)
        if self.device != 'cpu' and not self.device.startswith('cuda:'):
            raise InputError('Use cpu or cuda:N')
        weight = (root/entry['weights']['path']).resolve()
        if not weight.is_relative_to(root.resolve()):raise ModelError('Weight path escapes registry root')
        if digest(weight) != entry['weights']['sha256']:raise ModelError('Weight checksum mismatch')
        self.names = entry['classes']
        self.runtime = entry['runtime']
        if self.runtime == 'onnx':
            if self.device != 'cpu':raise InputError('This ONNX adapter supports CPU; choose cpu')
            import onnxruntime as ort
            opts=ort.SessionOptions();opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
            self.session=ort.InferenceSession(str(weight),sess_options=opts,providers=['CPUExecutionProvider'])
            self.input=self.session.get_inputs()[0].name
            shape=self.session.get_inputs()[0].shape
            size=entry['preprocessing'].get('size',672 if entry['preprocessing']['mode']=='pad672' else 640)
            if shape != [1,3,size,size]:raise ModelError(f'Unexpected ONNX shape {shape}')
        else:
            import torch
            torch.set_num_threads(4)
            if self.runtime == 'torch_state':
                from ultralytics.nn.tasks import DetectionModel
                data=torch.load(weight,map_location='cpu',weights_only=True)
                if data['architecture']!='yolov8n' or data['nc']!=10:raise ModelError('Unapproved architecture')
                self.model=DetectionModel('yolov8n.yaml',nc=10,verbose=False)
                self.model.load_state_dict(data['state_dict'],strict=True)
                names=data['names']
            elif self.runtime == 'local_ultralytics':
                # Only locally produced or checksum-bound official artifacts are registered here.
                from ultralytics import YOLO
                self.model=YOLO(str(weight)).model
                names=self.model.names
            else:raise ModelError('Unsupported runtime')
            if {str(k):v for k,v in names.items()} != self.names:raise ModelError('Embedded classes differ')
            self.model=self.model.float().to(self.device).eval()
            self.model.fuse(verbose=False)

    def tile(self, rgb, threshold):
        import torch
        from ultralytics.utils.nms import non_max_suppression
        x=np.ascontiguousarray(np.asarray(rgb).transpose(2,0,1)[None],dtype=np.float32)/255.
        if self.entry['preprocessing'].get('color_order')=='BGR':
            x=np.ascontiguousarray(x[:,::-1])
        if self.runtime=='onnx':
            raw=torch.from_numpy(self.session.run(None,{self.input:x})[0])
        else:
            with torch.inference_mode():
                pred=self.model(torch.from_numpy(x).to(self.device))
                raw=(pred[0] if isinstance(pred,(tuple,list)) else pred).cpu()
        if not torch.isfinite(raw).all():raise ModelError('Nonfinite prediction')
        if self.entry['preprocessing'].get('output_layout')=='end2end':
            if raw.ndim!=3 or raw.shape[0]!=1 or raw.shape[2]!=6:raise ModelError('Unexpected end-to-end output shape')
            boxes=[]
            for row in raw[0]:
                if float(row[4])<threshold:continue
                class_id=int(row[5])
                if float(row[5])!=class_id or str(class_id) not in self.names:raise ModelError('Unexpected end-to-end class ID')
                boxes.append({'xyxy':[float(v) for v in row[:4]],'score':float(row[4]),'class_id':class_id,'class_name':self.names[str(class_id)]})
            return merge_nms(boxes,.5)[:300]
        if raw.shape[1] != 4+len(self.names):raise ModelError('Unexpected model output/class count')
        out=non_max_suppression(raw.clone(),conf_thres=threshold,iou_thres=.5,nc=len(self.names),max_det=300,max_time_img=10)[0]
        return [{'xyxy':[float(v) for v in r[:4]],'score':float(r[4]),'class_id':int(r[5]),'class_name':self.names[str(int(r[5]))]} for r in out.numpy()]

    def predict(self, path, progress=None, threshold=None):
        image=read_image(path);w,h=image.size;mode=self.entry['preprocessing']['mode']
        threshold=self.entry['threshold'] if threshold is None else threshold
        if not 0<=threshold<=1:raise InputError('Threshold must be 0..1')
        boxes=[];processed=None
        if mode in ('letterbox640','letterbox256'):
            from ultralytics.data.augment import LetterBox
            size=self.entry['preprocessing'].get('size',640)
            if self.entry['preprocessing'].get('max_aspect_ratio') and max(w/h,h/w)>self.entry['preprocessing']['max_aspect_ratio']:
                raise InputError('Specialist expects cropped frames with aspect ratio at most 4:1')
            rgb=LetterBox((size,size),auto=False,scale_fill=False,scaleup=True)(image=np.asarray(image))
            ratio=min(size/w,size/h);neww,newh=round(w*ratio),round(h*ratio)
            left=round((size-neww)/2-.1);top=round((size-newh)/2-.1)
            for box in self.tile(Image.fromarray(rgb),threshold):
                a,b,c,d=box['xyxy'];box['xyxy']=[(a-left)/ratio,(b-top)/ratio,(c-left)/ratio,(d-top)/ratio];boxes.append(box)
            if progress:progress(1,1)
        elif mode=='pad672':
            if max(w,h)>672:raise InputError('FLS development model accepts full fan images at most 672 pixels per side; no silent resize')
            tile=Image.new('RGB',(672,672),(114,114,114));tile.paste(image,(0,0));boxes=self.tile(tile,threshold)
            if progress:progress(1,1)
        elif mode=='sss_lee640_s320':
            # This specialist uses its own documented geometry; cross-model NMS is never applied.
            def starts(n):
                values=list(range(0,max(1,n-640+1),320))
                if n>640 and values[-1]!=n-640:values.append(n-640)
                return values
            windows=[(x,y,min(x+640,w),min(y+640,h)) for y in starts(h) for x in starts(w)]
            if len(windows)>512:raise InputError('Too many tiles; decode a smaller recording window')
            processed=Image.new('RGB',image.size)
            for k,crop in enumerate(windows):
                rgb=image.crop(crop);tile=Image.new('RGB',(640,640));tile.paste(rgb,(0,0))
                filtered=lee_clahe(tile)
                processed.paste(filtered.crop((0,0,rgb.width,rgb.height)),crop[:2])
                for box in self.tile(filtered,threshold):
                    box['xyxy']=map_box(box['xyxy'],crop);box['tile_index']=k;boxes.append(box)
                if progress:progress(k+1,len(windows))
            boxes=merge_nms(boxes,.5)
        else:raise ModelError('Unknown preprocessing')
        clipped=[]
        for b in boxes:
            a,y,c,d=b['xyxy'];a,c=np.clip([a,c],0,w);y,d=np.clip([y,d],0,h)
            if c>a and d>y:
                b['xyxy']=[float(a),float(y),float(c),float(d)];clipped.append(b)
        return clipped,processed


class Registry:
    """Lazy cache, one resident model by default; explicit modality before loading."""
    def __init__(self, directory, cache_models=1):
        self.root=Path(directory).resolve();self.cache=OrderedDict()
        if not 1<=cache_models<=2:raise ValueError('Cache limit is one or two models')
        self.limit=cache_models

    def entries(self):
        entries=[json.loads(p.read_text()) for p in sorted(self.root.glob('*.model.json'))]
        ids=[e['id'] for e in entries]
        if len(ids)!=len(set(ids)):raise ModelError('Duplicate model ID')
        return entries

    def get(self, model_id):
        entry=next((e for e in self.entries() if e['id']==model_id),None)
        if entry is None:raise ModelError(f'Unknown model {model_id}')
        return entry

    def load(self, model_id, modality, device='cpu', backend='native'):
        e=self.get(model_id)
        if backend not in ('native','onnx'):raise InputError('Backend must be native or onnx')
        if e['status']=='unavailable':raise ModelError(e['reason'])
        if modality not in e['modalities']:raise InputError(f'{model_id} requires {e["modalities"]}; received {modality}')
        selected=e
        if backend=='onnx' and e['runtime'] not in ('onnx','bluecho_v3'):
            if e.get('onnx',{}).get('status')!='PASS':raise InputError('No verified ONNX backend for this specialist')
            selected={**e,'runtime':'onnx','weights':e['onnx']}
        if e['runtime']=='bluecho_v3':
            manifest=(self.root/e['manifest']).resolve()
            if not manifest.is_relative_to(self.root):raise ModelError('Manifest escapes registry root')
            bound=json.loads(manifest.read_text())
            artifact=bound[backend]
            selected={**e,'weights':{**artifact,'path':str((manifest.parent/artifact['path']).relative_to(self.root))}}
        key=(model_id,str(device),backend,selected['weights']['sha256'])
        if key not in self.cache:
            while len(self.cache)>=self.limit:
                _,old=self.cache.popitem(last=False);del old;gc.collect()
                import torch
                if torch.cuda.is_available():torch.cuda.empty_cache()
            if e['runtime']=='bluecho_v3':
                manifest=(self.root/e['manifest']).resolve()
                if not manifest.is_relative_to(self.root):raise ModelError('Manifest escapes registry root')
                self.cache[key]=Engine(manifest,device=device,backend=backend)
            else:
                self.cache[key]=Specialist(selected,self.root,device=device)
        self.cache.move_to_end(key)
        return selected,self.cache[key]
