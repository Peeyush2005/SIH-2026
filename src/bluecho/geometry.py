"""Phase 2B pixel geometry, preserved from the verified transfer bundle."""
from PIL import Image


def starts(length, tile=640, stride=480):
    if length <= tile:
        return [0]
    return list(range(0, length-tile+1, stride)) + ([length-tile] if (length-tile) % stride else [])


def crops(width, height, tile=640, stride=480):
    return [(x, y, min(x+tile, width), min(y+tile, height))
            for y in starts(height, tile, stride) for x in starts(width, tile, stride)]


def render_tile(image, crop, size=640):
    canvas = Image.new('RGB', (size, size), (114, 114, 114))
    canvas.paste(image.convert('RGB').crop(crop), (0, 0))
    return canvas


def map_box(box, crop):
    x, y, x2, y2 = crop
    a, b, c, d = box
    return [max(x, a+x), max(y, b+y), min(x2, c+x), min(y2, d+y)]


def iou(a, b):
    inter = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.


def merge_nms(boxes, threshold):
    kept = []
    for box in sorted(boxes, key=lambda b: -b['score']):
        if all(box['class_id'] != k['class_id'] or iou(box['xyxy'], k['xyxy']) <= threshold for k in kept):
            kept.append(box)
    return kept
