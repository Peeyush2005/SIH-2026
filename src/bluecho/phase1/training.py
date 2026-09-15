"""Standalone workers and deterministic post-training evaluation/registration."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
from .download import atomic_json,digest


def read(p):return json.loads(Path(p).read_text())


def should_stop(cfg):
    return Path(cfg['stop_file']).exists() or (Path(cfg['output'])/'STOP_WORKER').exists() or time.monotonic()>=cfg['deadline_monotonic']


def save_torch(path,data):
    import torch
    tmp=path.with_suffix('.pending');torch.save(data,tmp);tmp.replace(path)


def atomic_model_save(trainer,save):
    """Preserve the upstream success flag that gates on_model_save callbacks."""
    last,best=trainer.last,trainer.best
    trainer.last=last.with_suffix('.pending');trainer.best=best.with_suffix('.pending')
    try:
        result=save()
        if trainer.last.exists():trainer.last.replace(last)
        if trainer.best.exists():trainer.best.replace(best)
        return result
    finally:trainer.last,trainer.best=last,best


def worker(cfg):
    os.environ.update(YOLO_OFFLINE='true',YOLO_AUTOINSTALL='false',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
    import torch
    torch.set_num_threads(4)
    out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
    cfg_binding={k:cfg[k] for k in ['id','kind','bindings','parameters'] if k in cfg}
    encoded=json.dumps(cfg_binding,sort_keys=True).encode()
    import hashlib
    binding=hashlib.sha256(encoded).hexdigest()
    snap=out/'resume.pt';resume=None
    if snap.exists():
        meta=read(out/'resume.json')
        if digest(snap)!=meta['sha256'] or meta['binding']!=binding:raise ValueError('Resume checksum/config/model/data binding mismatch')
        resume=torch.load(snap,map_location='cpu',weights_only=cfg['kind']=='synthetic')
        if resume.get('optimizer') is None:raise ValueError('Resume must carry optimizer state')
        atomic_json(out/'resume_verified.json',{'status':'PASS','binding':binding,'epoch':resume['epoch'],'optimizer_states':len(resume['optimizer']['state']),'time':time.time()})
    atomic_json(out/'heartbeat.json',{'stage':'startup','epoch':0,'time':time.time()})
    if cfg['kind']=='synthetic':
        m=torch.nn.Linear(2,1);opt=torch.optim.AdamW(m.parameters(),lr=.001)
        step=0
        if resume:
            m.load_state_dict(resume['model']);opt.load_state_dict(resume['optimizer']);step=resume['epoch']+1
        for step in range(step,cfg.get('steps',30)):
            if should_stop(cfg):
                atomic_json(out/'worker_result.json',{'state':'BUDGET_STOP' if time.monotonic()>=cfg['deadline_monotonic'] else 'INTERRUPTED','completed_steps':step});return
            opt.zero_grad();loss=m(torch.ones(3,2)).square().mean();loss.backward();opt.step()
            save_torch(snap,{'model':m.state_dict(),'optimizer':opt.state_dict(),'epoch':step})
            atomic_json(out/'resume.json',{'sha256':digest(snap),'binding':binding,'epoch':step})
            atomic_json(out/'heartbeat.json',{'epoch':step+1,'time':time.time(),'loss':float(loss.detach())})
            time.sleep(cfg.get('step_seconds',.25))
        atomic_json(out/'worker_result.json',{'state':'TRAINED','completed_steps':step+1,'synthetic_software_test':True});return
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect import DetectionTrainer
    partial=False
    class BoundTrainer(DetectionTrainer):
        def check_resume(self,overrides):
            super().check_resume(overrides)
            if self.resume:
                self.args.data=cfg['data'];self.args.batch=cfg['batch'];self.args.workers=2
                self.args.project=str(out);self.args.name='native';self.args.save_dir=str(out/'native');self.args.exist_ok=True
        def resume_training(self,ckpt):
            super().resume_training(ckpt)
            if self.resume:
                assert self.start_epoch==resume['epoch']+1 and len(self.optimizer.state)>0
                atomic_json(out/'optimizer_resume_verified.json',{'status':'PASS','start_epoch':self.start_epoch,'optimizer_states':len(self.optimizer.state),'binding':binding})
        def save_model(self):
            return atomic_model_save(self,super().save_model)
    def started(t):
        resolved=vars(t.args).copy()
        resolved.update(resolved_optimizer=type(t.optimizer).__name__,optimizer_groups=[{k:v for k,v in g.items() if k!='params'} for g in t.optimizer.param_groups],effective_batch=t.batch_size*t.accumulate,train_images=len(t.train_loader.dataset),fit_diagnostic_images=len(t.test_loader.dataset),evaluation_scope='TRAINING_FIT_ONLY: identical unsplit development pool, no independent validation')
        assert resolved['resolved_optimizer']=='AdamW'
        atomic_json(out/'effective_config.json',resolved)
    last_hb=0.
    def batch(t):
        nonlocal partial,last_hb
        now=time.monotonic()
        if now-last_hb>2:
            atomic_json(out/'heartbeat.json',{'epoch':int(t.epoch),'time':time.time(),'cuda_peak_bytes':torch.cuda.max_memory_allocated()});last_hb=now
        if should_stop(cfg):partial=True;t.stop=True
    def saved(t):
        if partial:return  # Last fully completed epoch remains the recovery point.
        temporary=out/'resume.pending';shutil.copyfile(t.last,temporary);temporary.replace(snap)
        ck=torch.load(snap,map_location='cpu',weights_only=False)
        assert ck.get('optimizer') is not None
        atomic_json(out/'resume.json',{'sha256':digest(snap),'binding':binding,'epoch':int(ck['epoch']),'optimizer_states':len(ck['optimizer']['state'])})
    def epoch(t):
        atomic_json(out/'heartbeat.json',{'epoch':min(int(t.epoch)+1,cfg['parameters']['epochs']),'time':time.time(),'fitness':float(t.fitness),'epoch_seconds':float(t.epoch_time),'cuda_peak_bytes':torch.cuda.max_memory_allocated()})
        if should_stop(cfg) or time.monotonic()+t.epoch_time*1.2>=cfg['deadline_monotonic']:t.stop=True
    model=YOLO(str(snap if resume else cfg['initial_weights']))
    model.add_callback('on_pretrain_routine_end',started);model.add_callback('on_train_batch_end',batch);model.add_callback('on_model_save',saved);model.add_callback('on_fit_epoch_end',epoch)
    params={**cfg['parameters'],'batch':cfg['batch'],'data':cfg['data'],'project':str(out),'name':'native','exist_ok':True,'device':0}
    try:
        model.train(trainer=BoundTrainer,**params,**({'resume':str(snap)} if resume else {}))
        stopped=should_stop(cfg) or (int(model.trainer.epoch)+1 < cfg['parameters']['epochs'] and not model.trainer.stopper.possible_stop)
        state='INTERRUPTED' if Path(cfg['stop_file']).exists() else 'BUDGET_STOP' if partial or stopped else 'TRAINED'
        atomic_json(out/'worker_result.json',{'state':state,'epoch':int(model.trainer.epoch)+1,'partial_final_epoch':partial,'best':str(model.trainer.best),'resume':str(snap),'scope':'DEVELOPMENT_ONLY_TRAINING_FIT'})
    except BaseException as exc:
        atomic_json(out/'worker_result.json',{'state':'FAILED','error':str(exc),'oom':isinstance(exc,torch.cuda.OutOfMemoryError) or 'out of memory' in str(exc).lower()});raise


def post(cfg):
    out=Path(cfg['output'])
    if cfg['kind']=='recovery_test':
        import torch
        ck=torch.load(out/'resume.pt',map_location='cpu',weights_only=False)
        assert ck.get('optimizer',{}).get('state')
        restored=read(out/'optimizer_resume_verified.json')
        assert restored['status']=='PASS'
        atomic_json(out/'post_result.json',{'status':'PASS','stages':['verify_saved_optimizer','verify_actual_trainer_restoration','report'],'scope':'YOLO recovery software test only; no model promotion or accuracy claim','final_saved_epoch':ck['epoch'],'restoration':restored})
        return
    if cfg['kind']=='synthetic':
        import torch
        ck=torch.load(out/'resume.pt',map_location='cpu',weights_only=True)
        assert ck['optimizer']['state']
        atomic_json(out/'post_result.json',{'status':'PASS','stages':['evaluate','register','export','report'],'synthetic_software_only':True,'completed_epoch':ck['epoch']})
        return
    import torch
    from ultralytics import YOLO
    from .adapters import Specialist
    from .metrics import evaluate
    registry=Path(cfg['registry']);registry.mkdir(parents=True,exist_ok=True)
    dst=registry/'fls-development';dst.mkdir(exist_ok=True)
    # For an interrupted budget, use only the verified completed-epoch snapshot.
    result=read(out/'worker_result.json')
    src=out/'native/weights/best.pt' if result['state']=='TRAINED' else out/'resume.pt'
    if not src.exists():src=out/'resume.pt'
    tmp=dst/'native.pending';shutil.copyfile(src,tmp);tmp.replace(dst/'native.pt')
    classes=cfg['classes']
    entry={'id':'fls-debris-development','status':'development-only','version':'phase1-0.1','modalities':['FLS_ARIS'],'output_task':'bounding_box_detection','runtime':'local_ultralytics','architecture':'YOLO11n','weights':{'path':'fls-development/native.pt','sha256':digest(dst/'native.pt')},'classes':classes,'threshold':.25,'preprocessing':{'mode':'pad672','size':672,'intensity':'uint8 RGB /255; preserve fan margins; top-left pad114'},'calibration':'uncalibrated','evidence_scope':'DEVELOPMENT_ONLY_TRAINING_FIT; all 1868 pool images used in training; independent grouping unresolved','material_identity':False,'terms':{'code':'AGPL-3.0-or-later','weights':'Ultralytics AGPL-3.0 conditions; local fit','data':'source Marine Debris FLS terms; see dataset provenance'},'redistribution':'local research handoff only; verify inherited/source terms before public distribution'}
    model=Specialist(entry,registry,device='cuda:0')
    records=read(cfg['fit_records'])['records'];items=[]
    for i,rec in enumerate(records):
        boxes,_=model.predict(rec['image'])
        items.append({'id':rec['id'],'truth':rec['boxes'],'predictions':boxes})
    metrics=evaluate(items,classes)
    metrics.update(scope=entry['evidence_scope'],images=len(items),threshold=.25)
    atomic_json(out/'fit_predictions.json',items);atomic_json(out/'fit_metrics.json',metrics)
    del model;torch.cuda.empty_cache()
    # An export failure never disables the native model. Parity is checked below.
    try:
        m=YOLO(str(dst/'native.pt'));onnx=Path(m.export(format='onnx',imgsz=672,batch=1,dynamic=False,simplify=False,opset=17,device='cpu'))
        import onnxruntime as ort
        import numpy as np
        from PIL import Image
        session=ort.InferenceSession(str(onnx),providers=['CPUExecutionProvider'])
        m.model.float().eval();parity=[]
        for r in records[:8]:
            rgb=Image.open(r['image']).convert('RGB');a=np.full((672,672,3),114,dtype=np.uint8);a[:rgb.height,:rgb.width]=np.asarray(rgb)
            x=np.ascontiguousarray(a.transpose(2,0,1)[None],dtype=np.float32)/255
            with torch.inference_mode():y=m.model(torch.from_numpy(x));y=(y[0] if isinstance(y,(tuple,list)) else y).numpy()
            z=session.run(None,{session.get_inputs()[0].name:x})[0]
            delta=float(np.max(np.abs(y-z)));assert np.allclose(y,z,atol=.01,rtol=.001)
            parity.append({'id':r['id'],'max_abs_difference':delta})
        atomic_json(out/'onnx_parity.json',{'status':'PASS','scope':'eight fixed development-fit examples; raw output parity','samples':parity})
        entry['onnx']={'path':str(onnx.relative_to(registry)),'sha256':digest(onnx),'status':'PASS','shape':[1,3,672,672]}
    except Exception as exc:
        atomic_json(out/'onnx_parity.json',{'status':'FAIL_NATIVE_RETAINED','error':str(exc)})
    entry['fit_metrics']=metrics
    atomic_json(registry/'fls-debris-development.model.json',entry)
    (out/'REPORT.md').write_text('# FLS development fit\n\nAll 1,868 audited full fan images were used as one development pool. Fit diagnostics do not establish independent accuracy. No random adjacent-frame split was created. Generic bottle labels do not establish plastic material.\n\n'+json.dumps(metrics,indent=2)+'\n')
    atomic_json(out/'post_result.json',{'status':'PASS','stages':['fit_evaluation','model_registration','onnx_export_attempt_and_parity','report'],'model_id':entry['id'],'model_sha256':entry['weights']['sha256']})


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['worker','post']);p.add_argument('--config',required=True);a=p.parse_args();cfg=read(a.config)
    worker(cfg) if a.action=='worker' else post(cfg)
if __name__=='__main__':main()
