"""Portable predictions and evidence; geographical fields remain explicitly unavailable."""
import csv
import json
import math
from pathlib import Path
from PIL import ImageDraw
from .engine import read_image, InputError


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def write_csv(path, prediction, reviews=None):
    reviews = reviews or {}
    fields = ['detection_id','source_reference','class_id','class_name','material','model_score','score_type',
        'x1','y1','x2','y2','pixel_width','pixel_height','metric_dimensions','coordinates','crs','position_method',
        'uncertainty','quality_flags','review_status','reviewed_class_name','model_version','model_sha256','preprocessing_version']
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for detection in prediction['detections']:
            d = detection; a,b,c,e = d['box_xyxy_pixels']; review = reviews.get(d['detection_id'], {})
            row = {k:d.get(k) for k in fields}
            row.update(x1=a, y1=b, x2=c, y2=e, pixel_width=c-a, pixel_height=e-b,
                       quality_flags=json.dumps(d['quality_flags']),
                       review_status=review.get('status', 'unreviewed'), reviewed_class_name=review.get('label'))
            # CSV blank cells mean unavailable; JSON carries literal nulls.
            writer.writerow(row)


def export(prediction, destination, *, source=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination/'predictions.json', prediction)
    write_csv(destination/'predictions.csv', prediction)
    evidence = []
    if source is not None:
        image = read_image(source); overlay = image.copy(); draw = ImageDraw.Draw(overlay)
        crop_dir = destination/'crops'; crop_dir.mkdir()
        for d in prediction['detections']:
            box = d['box_xyxy_pixels']; draw.rectangle(box, outline=(255,60,80), width=2)
            draw.text((box[0], min(image.height-12,box[1]+3)), f"{d['class_name']} {d['model_score']:.2f}", fill=(255,60,80))
            crop = [math.floor(box[0]),math.floor(box[1]),math.ceil(box[2]),math.ceil(box[3])]
            rel = f"crops/{d['detection_id']}.png"; image.crop(crop).save(destination/rel); evidence.append(rel)
        overlay.save(destination/'annotated.png'); evidence.insert(0, 'annotated.png')
    write_json(destination/'evidence.json', evidence)
    return destination


def geojson(prediction):
    raise InputError('GeoJSON unavailable: this release has no validated image-to-geography adapter. Pixel boxes cannot supply coordinates.')
