"""Geotag saved canonical detections without model loading or inference."""
import copy,json
from pathlib import Path
from PIL import Image
from .phase1.download import digest,atomic_json
from .phase1.contracts import validate_result
from .phase1.geography import load_sidecar,geotag_box,tracks
from .phase1.reporting import export_result

def geotag_saved(result_path,source,sidecar,output):
    result_path=Path(result_path);source=Path(source);output=Path(output)
    result=json.loads(result_path.read_text());image=Image.open(result_path.parent/'original.png').convert('RGB');validate_result(result,image)
    if digest(source)!=result['source_sha256']:raise ValueError('Source hash differs from saved detections')
    metadata=load_sidecar(sidecar,source,*image.size)
    if metadata['modality']!=result['modality']:raise ValueError('Metadata modality mismatch')
    if output.exists() and any(output.iterdir()):raise ValueError('Choose an empty output directory')
    original=copy.deepcopy(result)
    for kind in ['detections','unvalidated_proposals']:
        for d in result[kind]:
            old={k:d.get(k) for k in ['coordinates','position_method','position_reason','metric_dimensions','geographic_footprint']}
            d.setdefault('positioning_history',[]).append({'previous':old,'new_metadata_sha256':metadata['metadata_provenance']['sha256']})
            d.update(geotag_box(d['box_xyxy_pixels'],metadata))
            d['quality_flags']=[f for f in d['quality_flags'] if f!='geographical_position_unavailable']
            if d['coordinates'] is None:d['quality_flags'].append('geographical_position_unavailable')
    result.update(positioning_metadata=metadata,tracks=tracks(metadata),positioning_scope='Source-bound supplied metadata; field accuracy unvalidated')
    for q in result['quality']['regions']:q['position']=geotag_box(q['box_xyxy_pixels'],metadata)
    output.mkdir(parents=True,exist_ok=True)
    # Quality imagery is an observation; copy the original unchanged.
    if (result_path.parent/'quality.png').exists():
        import shutil
        shutil.copyfile(result_path.parent/'quality.png',output/'quality.png')
    atomic_json(output/'original_predictions.json',original);export_result(result,output,image);atomic_json(output/'positioning_metadata.json',metadata)
    return result
