"""Portable JSON/CSV/GeoJSON, evidence images and a static HTML inspection report."""
import csv
import html
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .download import atomic_json
from .contracts import validate_result


def export_result(result,out,image=None):
    validate_result(result,image)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    atomic_json(out/'results.json',result)
    fields=['candidate_id','source_file','channel','ping_index','sample_index','modality','class_name','model_id','model_score','score_type','model_sha256','box_xyxy_pixels','pixel_width','pixel_height','width_m','height_m','longitude','latitude','crs','position_method','position_reason','quality_flags','review_state','material_identity','evidence_status']
    fields+=['source_sha256','model_version','native_class_name','mapped_class_name','score_calibrated','image_width','image_height','evidence_crop','evidence_context']
    fields+=['location_status','metadata_provenance','uncertainty','altitude_provenance','footprint_status','positioning_assumptions','source_reference']
    features=[];rows=[];footprints=[]
    all_candidates=result['detections']+result.get('unvalidated_proposals',[])
    for d in all_candidates:
        ref=d.get('source_location_reference') or {};coords=d.get('coordinates');metric=d.get('metric_dimensions') or {}
        row={'candidate_id':d['candidate_id'],'source_file':d['source_reference']['file'],'channel':d['source_reference'].get('channel'),'ping_index':ref.get('ping_index'),'sample_index':ref.get('sample_index'),'modality':d['modality'],'class_name':d['class_name'],'model_id':d['model_id'],'model_score':d['model_score'],'score_type':d['score_type'],'model_sha256':d['model_sha256'],'box_xyxy_pixels':json.dumps(d['box_xyxy_pixels']),'pixel_width':d['pixel_dimensions']['width'],'pixel_height':d['pixel_dimensions']['height'],'width_m':metric.get('width_m'),'height_m':metric.get('height_m'),'longitude':coords[0] if coords else None,'latitude':coords[1] if coords else None,'crs':d['crs'],'position_method':d['position_method'],'position_reason':d['position_reason'],'quality_flags':json.dumps(d['quality_flags']),'review_state':d['review_state'],'material_identity':d['material_identity'],'evidence_status':d['evidence_status']}
        row.update(source_sha256=d['source_sha256'],model_version=d['model_version'],native_class_name=d['original_class'],mapped_class_name=d.get('mapped_class_name'),score_calibrated=False,image_width=result['image_dimensions']['width'],image_height=result['image_dimensions']['height'],evidence_crop=f"crops/{d['candidate_id']}.png",evidence_context=f"contexts/{d['candidate_id']}.png")
        row.update({k:json.dumps(d.get(k)) if isinstance(d.get(k),(dict,list)) else d.get(k) for k in ['location_status','metadata_provenance','uncertainty','altitude_provenance','footprint_status','positioning_assumptions','source_reference']})
        rows.append(row)
        props={k:v for k,v in row.items() if k not in ['longitude','latitude']}
        features.append({'type':'Feature','geometry':{'type':'Point','coordinates':coords} if coords is not None else None,'properties':props})
        if coords:
            if d.get('geographic_footprint'):footprints.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[d['geographic_footprint']]},'properties':{'candidate_id':d['candidate_id'],'kind':'image_footprint','meaning':'not established physical dimensions'}})
    with (out/'detections.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    atomic_json(out/'detections.geojson',{'type':'FeatureCollection','features':features})
    atomic_json(out/'footprints.geojson',{'type':'FeatureCollection','features':footprints})
    from .geography import geotag_box
    metadata=result.get('positioning_metadata')
    frame=geotag_box([0,0,result['image_dimensions']['width'],result['image_dimensions']['height']],metadata) if metadata else {}
    processed=[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[frame['geographic_footprint']]},'properties':{'kind':'processed_image_window','meaning':'image extent, not independently established seafloor coverage'}}] if frame.get('geographic_footprint') else []
    atomic_json(out/'processed_coverage.geojson',{'type':'FeatureCollection','features':processed})
    atomic_json(out/'unassessed.geojson',{'type':'FeatureCollection','features':[],'unlocated_descriptions':result['quality']['coverage'].get('unassessed',[])})
    atomic_json(out/'tracks.geojson',result.get('tracks',{'type':'FeatureCollection','features':[]}))
    coverage=[]
    for q in result['quality']['regions']:
        if q['position'].get('geographic_footprint'):coverage.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[q['position']['geographic_footprint']]},'properties':{'flag':q['flag'],'assessment':q['assessment'],'recommendation':q['recommendation']}})
    atomic_json(out/'coverage.geojson',{'type':'FeatureCollection','features':coverage})
    atomic_json(out/'coverage_warnings.json',result['quality'])
    if image is not None:
        image.save(out/'original.png');overlay=image.copy();draw=ImageDraw.Draw(overlay)
        cropdir=out/'crops';cropdir.mkdir(exist_ok=True)
        contextdir=out/'contexts';contextdir.mkdir(exist_ok=True)
        font=ImageFont.load_default(size=max(14,min(24,image.width//100)))
        for number,d in enumerate(all_candidates,1):
            if d.get('mask') is not None:
                import numpy as np
                from .masks import decode_binary_mask
                mask=Image.fromarray(decode_binary_mask(d['mask'])*80,'L')
                tint=Image.new('RGB',image.size,'orange' if d['candidate_type']=='unvalidated_proposal' else '#28c8f0')
                overlay.paste(tint,(0,0),mask);draw=ImageDraw.Draw(overlay)
            a,b,c,e=d['box_xyxy_pixels'];color='orange' if d['candidate_type']=='unvalidated_proposal' else '#28c8f0'
            draw.rectangle((a,b,c,e),outline=color,width=3)
            label=f"#{number} {d['class_name']} {d['model_score']:.1f}/100"
            if image.width<120:label=f'#{number}';font=ImageFont.load_default(size=8)
            bounds=draw.textbbox((0,0),label,font=font);tw,th=bounds[2]+8,bounds[3]+6
            lx=max(0,min(a,image.width-tw));ly=max(0,b-th)
            draw.rectangle((lx,ly,lx+tw,ly+th),fill='#071b2a');draw.text((lx+4,ly+1),label,font=font,fill=color)
            margin=max(20,int(max(c-a,e-b)*.2))
            image.crop((max(0,math.floor(a)-margin),max(0,math.floor(b)-margin),min(image.width,math.ceil(c)+margin),min(image.height,math.ceil(e)+margin))).save(contextdir/(d['candidate_id']+'.png'))
            # Floor/ceil retain every pixel intersecting the original float box.
            image.crop((math.floor(a),math.floor(b),math.ceil(c),math.ceil(e))).save(cropdir/(d['candidate_id']+'.png'))
        if not all_candidates:
            draw.rectangle((0,0,min(image.width,360),30),fill='#071b2a');draw.text((5,5),'No detections at this threshold',font=font,fill='white')
        overlay.save(out/'annotated.png')
    from .vector_view import render_vectors
    render_vectors(features,result.get('tracks',{}).get('features',[]),out/'vectors.svg')
    title=html.escape(result['source_reference']['file']);body=[]
    for number,row in enumerate(rows,1):
        cid=html.escape(row['candidate_id']);body.append(f'<tr><td>#{number}</td><td><a href="crops/{cid}.png">Crop</a> · <a href="contexts/{cid}.png">Context</a></td>'+''.join('<td>'+html.escape('' if row[k] is None else str(row[k]))+'</td>' for k in ['class_name','model_score','model_id','evidence_status','longitude','latitude','position_reason','width_m','height_m','uncertainty'])+'</tr>')
    scope=html.escape('; '.join(result['evidence_scopes'])+' | Positioning: '+result.get('positioning_scope','unvalidated'))
    doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>BluEcho inspection — {title}</title>
+<style>body{{font:16px system-ui;max-width:1200px;margin:32px auto;padding:0 20px;color:#193145;background:#f4f8fb}}h1{{font-size:28px}}.views{{display:flex;gap:16px;flex-wrap:wrap}}figure{{margin:0;flex:1;min-width:280px}}img{{max-width:100%;max-height:650px;object-fit:contain;background:#152332}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;border-bottom:1px solid #c5d4df;text-align:left;overflow-wrap:anywhere}}.note{{padding:14px;background:#fff3d4}}a{{color:#006c91}}</style>
+<h1>BluEcho sonar inspection</h1><p>{title} · {html.escape(result['modality'])}</p><p class="note">{scope}. Scores are uncalibrated model scores, not probabilities of correctness. Locations absent from the metadata remain unlocated. Human review has not been fabricated.</p>
+<div class="views"><figure><img src="original.png" alt="Original sonar image"><figcaption>Original decoded view</figcaption></figure><figure><img src="annotated.png" alt="Sonar detections"><figcaption>Model candidates</figcaption></figure><figure><img src="quality.png" alt="Quality observations"><figcaption>Quality observations; shadows are not automatically missing data</figcaption></figure></div>
+<h2>Candidates</h2><p>{len(result['detections'])} detections; {len(result.get('unvalidated_proposals',[]))} unvalidated proposals; {sum(d['coordinates'] is not None for d in all_candidates)} located.</p><p>Automatic predictions only; ground truth and reviewer corrections are separate. Open images for full resolution.</p><table><tr><th>ID</th><th>Evidence</th><th>Class</th><th>Score /100</th><th>Model</th><th>Evidence</th><th>Longitude</th><th>Latitude</th><th>Missing-location reason</th><th>Box span x /m</th><th>Box span y /m</th><th>Uncertainty</th></tr>{''.join(body)}</table>
+<h2>Offline geographic vectors</h2><a href="vectors.svg"><img src="vectors.svg" alt="Located candidates and sensor tracks, no basemap"></a><p>Blue: automatic candidate estimates. Grey: sensor/vessel track samples, not object positions. No basemap or field accuracy implied.</p>
+<h2>Coverage and provenance</h2><pre>{html.escape(json.dumps(result['quality']['coverage'],indent=2))}</pre><p>Metre dimensions describe image footprints. Positioning accuracy and physical object identity require independent verification. Coverage suggestions are not autonomous navigation instructions.</p><p><a href="results.json">JSON</a> · <a href="detections.csv">CSV</a> · <a href="detections.geojson">Located candidates</a> · <a href="tracks.geojson">Sensor tracks</a> · <a href="footprints.geojson">Box footprints</a> · <a href="processed_coverage.geojson">Processed image extent</a> · <a href="unassessed.geojson">Unassessed descriptions</a> · <a href="coverage.geojson">Positioned coverage flags</a> · <a href="coverage_warnings.json">All coverage warnings</a></p></html>'''
    (out/'report.html').write_text(doc.replace('\n+','\n'))
    return {k:str(out/k) for k in ['results.json','detections.csv','detections.geojson','report.html']}
