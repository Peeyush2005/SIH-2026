"""Build the public demo from real local samples and freshly executed model outputs.

No generated pixels, invented detections, random scores or geographic anchors.
The output directory contains separately licensed data, not detector weights.
"""
import argparse
import copy
import hashlib
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from bluecho.phase1.engine import RecordingEngine


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ['samples', 'noaa', 'registry', 'output', 'work']:
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--append-debris', action='store_true', help='Append six additional verified FLS scenes, preserving existing demo assets')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    a.work.mkdir(parents=True, exist_ok=True)
    engine = RecordingEngine(a.registry)
    manifest = {s['id']:s for s in json.loads((a.samples/'manifest.json').read_text(encoding='utf-8'))['samples']}
    rows = [
        ('pipeline','Pipeline survey','SubPipe · low frequency','pipeline_positive.pbm','sss-pipeline-v3','SSS_LF','SubPipe','CC-BY-4.0','https://zenodo.org/records/12666132'),
        ('seabed','Seabed survey','SubPipe · low frequency','pipeline_empty.pbm','sss-pipeline-v3','SSS_LF','SubPipe','CC-BY-4.0','https://zenodo.org/records/12666132'),
        ('propeller','Propeller sample','ARIS · water tank','fls_4.png','fls11-debris','FLS_ARIS','Marine Debris FLS','CC-BY-NC-SA-4.0','https://zenodo.org/records/15101686'),
        ('bottle','Shampoo-bottle sample','ARIS · water tank','fls_7.png','fls11-debris','FLS_ARIS','Marine Debris FLS','CC-BY-NC-SA-4.0','https://zenodo.org/records/15101686'),
        ('noaa0','Gulf survey · west','NOAA · georeferenced','noaa_window_0.tif','sonarvision-sss','SSS','NOAA H12907','CC0-1.0','https://www.ngdc.noaa.gov/nos/H12001-H14000/H12907.html'),
        ('noaa1','Georeferenced survey','NOAA · real coordinates','noaa_window_1.tif','sonarvision-sss','SSS','NOAA H12907','CC0-1.0','https://www.ngdc.noaa.gov/nos/H12001-H14000/H12907.html'),
    ]
    if a.append_debris:
        rows=[(sid,name,'ARIS · water tank',filename,'fls11-debris','FLS_ARIS','Marine Debris FLS','CC-BY-NC-SA-4.0','https://zenodo.org/records/15101686') for sid,name,filename in [
            ('can','Can sample','fls_0.png'),('chain','Chain sample','fls_1.png'),
            ('carton','Drink-carton sample','fls_2.png'),('valve','Valve sample','fls_3.png'),
            ('standing-bottle','Standing-bottle sample','fls_8.png'),('tire-bottle','Tire & bottle sample','fls_11.png')]]
    catalog=json.loads((a.output/'catalog.json').read_text(encoding='utf-8')) if a.append_debris else []
    if a.append_debris:
        assert not {row[0] for row in rows}.intersection(item['id'] for item in catalog), 'These scenes already exist; use a fresh build directory'

    for sid,name,terrain,filename,model,modality,collection,license_id,url in rows:
        source=(a.noaa if sid.startswith('noaa') else a.samples)/filename
        if source.stem in manifest:
            assert digest(source)==manifest[source.stem]['sha256']
        target=a.output/sid;target.mkdir(exist_ok=True)
        native=engine.predict(source,a.work/sid,model_ids=[model],modality=modality)
        original=a.work/sid/'original.png'
        assert original.exists()
        shutil.copyfile(original,target/'original.png')
        # Decoding only: no repainting, stretching, compositing or enhancement.
        assert np.array_equal(np.asarray(Image.open(source).convert('RGB')),np.asarray(Image.open(original).convert('RGB')))
        image=Image.open(original);thumb=image.copy();thumb.thumbnail((360,170));thumb.save(target/'preview.jpg',quality=85)
        credits = ('OceanScan-MST / REMARO; Álvarez-Tuñón, Ribeiro Marnet, Antal, Aubard, Costa, Brodskiy' if collection=='SubPipe' else 'Matias Valdenegro, Bilal Wehbe, Yvan Petillot' if collection=='Marine Debris FLS' else 'NOAA/NOS, survey H12907, R/V Ocean Explorer, EdgeTech 4125')
        scope=('Correlated development example; not an independent pipeline test.' if collection=='SubPipe' else 'Real water-tank image; source label names the object. Training overlap is not excluded; not an open-ocean accuracy test.' if collection=='Marine Debris FLS' else 'Real NOAA survey mosaic. Object labels are unconfirmed; model alerts may be false positives. Not for navigation.')
        demo={'kind':'real_sonar_saved_inference','scenario':sid,'synthetic':False,'collection':collection,'source_url':url,'license':license_id,'credit':credits,'source_filename':filename,'original_file_sha256':digest(source),'display_png_sha256':digest(original),'image_changes':'Lossless RGB decoding to PNG; pixel array verified identical. Preview only is resized.','inference':'Saved output from an actual local CPU detector run; opening the demo does not run inference again.','inference_utc':datetime.now(timezone.utc).isoformat(),'scope':scope,'location':'Metadata-derived estimates; field accuracy unvalidated' if native.get('positioning_metadata') else 'Unavailable: no verified per-image geographic metadata','disclaimer':'Real sonar image with saved detector output. Model labels are predictions, not field verification.'}
        result=copy.deepcopy(native)
        result.update(schema_version='bluecho-browser/1.0',demo=demo,runtime='Saved Python CPU inference',saved_example=True,review_revision=0,rescan_requests=[],evidence_scope=scope,preprocessing={'source':'Original native inference; see candidate provenance'},merging={'source':'Original native model configuration'})
        for d in result['detections']+result['unvalidated_proposals']:
            d['demo']=True;d['synthetic']=False;d['review_history']=[]
            context=a.work/sid/d['evidence']['context'];dest=target/d['evidence']['context'];dest.parent.mkdir(exist_ok=True);shutil.copyfile(context,dest)
        shutil.copyfile(a.work/sid/'quality.png',target/'quality.png')
        # Keep the full surveyed footprint visible even when inference emits zero boxes.
        result['map_layers']={'processed':[]}
        if result.get('positioning_metadata'):
            from bluecho.phase1.geography import geotag_box
            footprint=geotag_box([0,0,image.width,image.height],result['positioning_metadata'])['geographic_footprint']
            result['map_layers']['processed']=[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[footprint]},'properties':{'source':'Embedded NOAA GeoTIFF georeferencing','not_for_navigation':True}}]
        (target/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        files={str(f.relative_to(target)).replace('\\','/'):digest(f) for f in target.rglob('*') if f.is_file()}
        item={'id':sid,'name':name,'terrain':terrain,'description':scope,'hint':'Select Map for genuine metadata-based locations.' if result.get('positioning_metadata') else 'Review the real image. Geographic position is unavailable for this sample.','model':model,'modality':modality,'preview':'/real-demo/'+sid+'/preview.jpg','source':url,'credit':credits,'license':license_id,'files':files,'detections':len(result['detections']),'proposals':len(result['unvalidated_proposals'])}
        catalog.append(item)
        print(sid, 'actual detections:',item['detections'],'proposals:',item['proposals'],flush=True)
    (a.output/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    (a.output/'ATTRIBUTION.md').write_text('''# Real sonar demo data

These examples contain real acoustic imagery and freshly executed detector outputs. No illustration, fabricated object, random confidence or artificial geographic anchor is included. PNG arrays were checked against decoded source pixels. Small JPEG previews alone are resized. JSON records source/image/model hashes and inference time. These are demonstration examples, not independent benchmarks.

## SubPipe — CC BY 4.0

Source: https://zenodo.org/records/12666132
License: https://creativecommons.org/licenses/by/4.0/
Creators: Olaya Álvarez-Tuñón, Luiza Ribeiro Marnet, László Antal, Martin Aubard, Maria Costa, Yury Brodskiy.

SubPipe is a public dataset of a submarine outfall pipeline, property of Oceanscan-MST. This dataset was acquired with a Light Autonomous Underwater Vehicle by Oceanscan-MST, within the scope of Challenge Camp 1 of the H2020 REMARO project.

Existing BluEcho development samples are decoded losslessly; no independent test or geographic metadata claim is made.

## Marine Debris FLS — CC BY-NC-SA 4.0

Source: https://zenodo.org/records/15101686
Creators: Matias Valdenegro, Bilal Wehbe, Yvan Petillot.
License: https://creativecommons.org/licenses/by-nc-sa/4.0/
The original ARIS water-tank samples (marine-debris-aris3k IDs 0, 1, 2, 3, 4, 7, 8 and 11), their previews and derived annotated displays retain these noncommercial/share-alike terms. Included for this noncommercial SIH research demonstration. They are not relicensed under the software license. No verified geographic metadata is available. Source labels and detector predictions are separate; material identity is not established by a label.

## NOAA H12907 — CC0 1.0

Source and explicit data terms: https://www.ngdc.noaa.gov/nos/H12001-H14000/H12907.html
License: https://creativecommons.org/publicdomain/zero/1.0/
NOAA/NOS, R/V Ocean Explorer, Gulf of Mexico, Louisiana, 2016. EdgeTech 4125 side-scan mosaic H12907_SSSAB_1m_600kHz_2of2.tif. Existing 1024-pixel windows preserve their original NAD83 / UTM zone 15N transform. Pixel-to-geographic conversion uses that real transform; location error and hazard identity have not been independently validated. Not for navigation. No NOAA endorsement is implied.

Model licenses remain separate; candidate provenance and the model catalog retain them. Gated GhostVision data and ambiguous author imagery are excluded.
''',encoding='utf-8')
    print('Built',len(catalog),'real samples;',sum(f.stat().st_size for f in a.output.rglob('*') if f.is_file()),'bytes')


if __name__=='__main__':
    main()
