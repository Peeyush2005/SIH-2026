"""Versioned schemas plus source and geometry invariants shared by every caller."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from jsonschema import Draft202012Validator
from bluecho.engine import InputError


def image_digest(image):
    rgb=image.convert('RGB')
    h=hashlib.sha256(f'RGB:{rgb.width}:{rgb.height}:'.encode());h.update(rgb.tobytes());return h.hexdigest()


@lru_cache(maxsize=4)
def validator(name):
    return Draft202012Validator(json.loads((Path(__file__).parent/'schemas'/name).read_text()))


def validate_schema(value,name):
    try:json.dumps(value,allow_nan=False)
    except (TypeError,ValueError) as exc:raise InputError('JSON contains nonfinite or unsupported values') from exc
    errors=sorted(validator(name).iter_errors(value),key=lambda e:str(list(e.path)))
    if errors:
        error=errors[0];raise InputError(f'Schema violation at {list(error.path)}: {error.message}')


def validate_result(result,image=None):
    version=result.get('schema_version')
    if version not in ('2.0.0','2.1.0'):raise InputError('Unsupported result schema version')
    validate_schema(result,f'result-{version}.schema.json')
    w,h=result['image_dimensions']['width'],result['image_dimensions']['height']
    if image is not None and (image.size!=(w,h) or image_digest(image)!=result['image_pixel_sha256']):
        raise InputError('Image pixels do not match the result binding')
    models={m['id']:m for m in result['models']};seen=set()
    for kind in ['detections','unvalidated_proposals']:
        for d in result[kind]:
            if d['candidate_id'] in seen:raise InputError('Duplicate candidate ID')
            seen.add(d['candidate_id'])
            if d['candidate_type']!=('model_detection' if kind=='detections' else 'unvalidated_proposal'):raise InputError('Candidate category differs from its output list')
            if d['source_sha256']!=result['source_sha256'] or d['source_reference']!=result['source_reference']:raise InputError('Candidate source binding differs from result')
            if d['modality']!=result['modality']:raise InputError('Candidate modality differs from result')
            model=models.get(d['model_id'])
            if not model or d['model_sha256']!=model['sha256'] or model['classes'].get(str(d['class_id']))!=d['original_class']:raise InputError('Candidate class/model binding mismatch')
            a,b,c,e=d['box_xyxy_pixels']
            if not 0<=a<c<=w or not 0<=b<e<=h:raise InputError('Candidate box outside original image')
            if not math.isclose(d['pixel_dimensions']['width'],c-a) or not math.isclose(d['pixel_dimensions']['height'],e-b):raise InputError('Pixel dimensions differ from box')
            if not math.isclose(d['model_score'],d['raw_score']*100,abs_tol=1e-6):raise InputError('Score scaling mismatch')
            if d['coordinates'] is None:
                if d['crs'] is not None or not d['position_reason']:raise InputError('Unlocated candidate requires null CRS and a reason')
            elif d['crs']!='EPSG:4326' or not d['position_method'] or d['position_reason'] is not None:raise InputError('Located candidate needs WGS84 and positioning method')
            if d['mask'] is not None:
                from .masks import decode_binary_mask
                mask=decode_binary_mask(d['mask'])
                if mask.shape!=(h,w):raise InputError('Mask is not in original image coordinates')
    return result
