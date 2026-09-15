"""Install exact specialist artifacts; UATD deserializes only inside bwrap."""
import argparse,json,shutil,subprocess,sys,sysconfig,tempfile
from pathlib import Path
from bluecho.phase1.download import download,digest,atomic_json
p=argparse.ArgumentParser();p.add_argument('--registry',required=True,type=Path);p.add_argument('--cache',required=True,type=Path);p.add_argument('--manifests',type=Path,default=Path(__file__).resolve().parents[1]/'download_manifests');p.add_argument('--model',choices=['uatd-fls','sss-wreck-experimental','ghost-pot','sonarvision-sss','fls11-debris'],required=True);a=p.parse_args();root=a.registry.resolve();root.mkdir(parents=True,exist_ok=True)
spec=json.loads((a.manifests/(a.model+'.json')).read_text());receipt=download(spec,a.cache);src=a.cache.resolve()/spec['filename'];entry_path=root/(a.model+'.model.json');entry=json.loads(entry_path.read_text())
destination=(root/entry['weights']['path']).resolve()
if not destination.is_relative_to(root):raise ValueError('Registry weight path escapes its root')
if a.model!='uatd-fls':
    dst=root/entry['weights']['path'];dst.parent.mkdir(parents=True,exist_ok=True)
    if src!=dst:shutil.copyfile(src,dst)
    assert digest(dst)==entry['weights']['sha256']
else:
    if not shutil.which('bwrap'):raise SystemExit('UATD conversion requires Linux bubblewrap; no unsafe fallback is performed')
    assert digest(src)=='cfc2edda7df387aa5d9e23f419915690bec6396c9ebc3c054ae218979334694c'
    with tempfile.TemporaryDirectory(prefix='bluecho-uatd-convert-') as temporary:
        out=Path(temporary);runtime=Path(sys.base_prefix).resolve();env=Path(sys.prefix).resolve();script=Path(__file__).with_name('restrict_uatd.py')
        cmd=['bwrap','--unshare-all','--new-session','--die-with-parent','--tmpfs','/','--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache','--ro-bind',str(runtime),'/runtime','--ro-bind',str(env),'/env','--ro-bind',str(src),'/input.pt','--ro-bind',str(script),'/script.py','--bind',str(out),'/output','--tmpfs','/tmp','--proc','/proc','--dev','/dev','--setenv','HOME','/tmp','--setenv','PYTHONPATH','/env/lib/python3.12/site-packages','--setenv','YOLO_CONFIG_DIR','/tmp/yolo','--chdir','/tmp','/runtime/bin/python3.12','/script.py']
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        if r.returncode:raise RuntimeError('Restricted conversion failed: '+r.stderr[-1200:])
        generated=out/'uatd-safe-state.pt';actual=digest(generated)
        # Serializer bytes may vary. Only this pinned original and strictly reconstructed
        # installed architecture can produce an accepted replacement; preserve receipt.
        dst=root/entry['weights']['path'];shutil.copyfile(generated,dst)
        entry['weights']['sha256']=actual;atomic_json(entry_path,entry)
        atomic_json(root/'uatd-conversion-receipt.json',{'original_sha256':digest(src),'derived_sha256':actual,'restricted_load':json.loads((out/'uatd-restricted-load.json').read_text()),'python':sys.version})
print(json.dumps({'status':'PASS','model':a.model,'original_download':receipt,'installed_sha256':digest(dst),'weight':str(dst)}))
